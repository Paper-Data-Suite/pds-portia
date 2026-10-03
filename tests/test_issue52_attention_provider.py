from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pds_core.module_operations import (
    MAX_MODULE_OPERATION_COUNT,
    ModuleOperationsRequest,
    invoke_module_attention,
)

import portia.attention_provider as provider
from portia.attention import (
    ATTENTION_DEFINITION_BY_CODE,
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionNotice,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionSummary,
    build_attention_report,
)
from portia.models.references import ExactPortiaWorkRef
from portia.pds_operations import get_module_operations_profile


def _clock(value: datetime, calls: list[datetime]) -> provider.AttentionClock:
    def now() -> datetime:
        calls.append(value)
        return value

    return now


def _stub_service(
    monkeypatch: pytest.MonkeyPatch,
    factory: Callable[[PortiaAttentionQuery], PortiaAttentionReport],
    captured: dict[str, object],
) -> None:
    class StubAttentionQueryService:
        def __init__(self, root: Path) -> None:
            captured["root"] = root

        def query(self, query: PortiaAttentionQuery) -> PortiaAttentionReport:
            captured["query"] = query
            return factory(query)

    monkeypatch.setattr(provider, "AttentionQueryService", StubAttentionQueryService)


def _event(class_id: str, work_id: str) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="event",
        contract_version="2",
    )


def test_known_shared_attention_codes_match_issue49_taxonomy() -> None:
    assert provider._KNOWN_NATIVE_ATTENTION_CODES == frozenset(
        ATTENTION_DEFINITION_BY_CODE
    )


def test_missing_workspace_is_unavailable_without_context_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForbiddenService:
        def __init__(self, root: Path) -> None:
            raise AssertionError(f"service must not be constructed for {root}")

    monkeypatch.setattr(provider, "AttentionQueryService", ForbiddenService)
    calls: list[datetime] = []
    fixed = datetime(2026, 9, 30, 23, 45, tzinfo=timezone.utc)

    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(),
        clock=_clock(fixed, calls),
    )

    assert calls == [fixed]
    assert report.evaluation == "unavailable"
    assert report.summaries == ()
    assert tuple(notice.code for notice in report.notices) == (
        PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    )
    assert "workspace" not in report.notices[0].summary.casefold()


def test_exact_class_scope_active_year_and_single_as_of_are_preserved(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    _stub_service(
        monkeypatch,
        lambda query: build_attention_report(query),
        captured,
    )
    calls: list[datetime] = []
    fixed = datetime(
        2026,
        9,
        30,
        23,
        59,
        12,
        tzinfo=timezone(timedelta(hours=-4)),
    )
    request = ModuleOperationsRequest(
        workspace_root=tmp_path,
        active_school_year="2026-2027",
        class_id="class_a",
    )

    report = provider._evaluate_portia_attention(
        request,
        clock=_clock(fixed, calls),
    )

    query = captured["query"]
    assert isinstance(query, PortiaAttentionQuery)
    assert captured["root"] == tmp_path
    assert calls == [fixed]
    assert query.scope.kind == "class"
    assert query.scope.class_id == "class_a"
    assert query.active_school_year == "2026-2027"
    assert query.as_of.text == fixed.isoformat()
    assert report.evaluation == "evaluated"
    assert report.summaries == ()
    assert report.notices == ()


def test_workspace_scope_is_exact_and_does_not_invent_a_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    _stub_service(
        monkeypatch,
        lambda query: build_attention_report(query),
        captured,
    )
    fixed = datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc)

    provider._evaluate_portia_attention(
        ModuleOperationsRequest(workspace_root=tmp_path),
        clock=lambda: fixed,
    )

    query = captured["query"]
    assert isinstance(query, PortiaAttentionQuery)
    assert query.scope.kind == "workspace"
    assert query.scope.class_id is None
    assert query.scope.work_ref is None


def test_native_summary_projects_exact_count_label_class_and_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work = _event("class_a", "evt_attention")

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        item = PortiaAttentionItem(
            code="portia_review_incomplete",
            source_ref=work,
            context=PortiaAttentionContext(
                class_id="class_a",
                work_ref=work,
            ),
            reason_codes=("open",),
        )
        return build_attention_report(query, (item, item))

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    request = ModuleOperationsRequest(
        workspace_root=tmp_path,
        class_id="class_a",
    )

    report = provider._evaluate_portia_attention(
        request,
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    assert report.evaluation == "evaluated"
    assert len(report.summaries) == 1
    summary = report.summaries[0]
    assert summary.code == "portia_review_incomplete"
    assert summary.label == "Reviews incomplete"
    assert summary.count == 2
    assert summary.class_id == "class_a"
    assert summary.work_ref is not None
    assert summary.work_ref.module_id == "portia"
    assert summary.work_ref.class_id == "class_a"
    assert summary.work_ref.work_id == "evt_attention"
    assert summary.action is not None
    assert summary.action.module_id == "portia"
    assert summary.action.action_id == "open_add_information"


def test_workspace_multi_class_summary_omits_false_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    work_a = _event("class_a", "evt_alpha")
    work_b = _event("class_b", "evt_beta")

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        return build_attention_report(
            query,
            (
                PortiaAttentionItem(
                    code="portia_review_incomplete",
                    source_ref=work_a,
                    context=PortiaAttentionContext(
                        class_id="class_a",
                        work_ref=work_a,
                    ),
                ),
                PortiaAttentionItem(
                    code="portia_review_incomplete",
                    source_ref=work_b,
                    context=PortiaAttentionContext(
                        class_id="class_b",
                        work_ref=work_b,
                    ),
                ),
            ),
        )

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(workspace_root=tmp_path),
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    summary = report.summaries[0]
    assert summary.count == 2
    assert summary.class_id is None
    assert summary.work_ref is None


def test_class_scope_may_carry_requested_class_without_representative_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition = ATTENTION_DEFINITION_BY_CODE["portia_integrity_conflict"]

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        return PortiaAttentionReport(
            query=query,
            evaluation="evaluated",
            summaries=(
                PortiaAttentionSummary(
                    code=definition.code,
                    label=definition.label,
                    count=3,
                    count_unit=definition.count_unit,
                    attention_class=definition.attention_class,
                ),
            ),
        )

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(
            workspace_root=tmp_path,
            class_id="class_a",
        ),
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    summary = report.summaries[0]
    assert summary.class_id == "class_a"
    assert summary.work_ref is None


def test_native_partial_notice_is_fixed_and_does_not_leak_message(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = r"PRIVATE C:\teacher\student-record.json"

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        return build_attention_report(
            query,
            notices=(
                PortiaAttentionNotice(
                    code=PORTIA_ATTENTION_PARTIAL_NOTICE,
                    message=sentinel,
                ),
            ),
        )

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(workspace_root=tmp_path),
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    assert tuple(notice.code for notice in report.notices) == (
        PORTIA_ATTENTION_PARTIAL_NOTICE,
    )
    assert sentinel not in repr(report)


def test_native_unavailable_remains_unavailable_and_privacy_bounded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = "PRIVATE-STORAGE-DETAIL"

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        return build_attention_report(
            query,
            notices=(
                PortiaAttentionNotice(
                    code=PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
                    message=sentinel,
                ),
            ),
            evaluation="unavailable",
        )

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(workspace_root=tmp_path),
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    assert report.evaluation == "unavailable"
    assert report.summaries == ()
    assert tuple(notice.code for notice in report.notices) == (
        PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    )
    assert sentinel not in repr(report)


def test_unrepresentable_native_count_becomes_bounded_partial_not_clamped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition = ATTENTION_DEFINITION_BY_CODE["portia_review_incomplete"]

    def native(query: PortiaAttentionQuery) -> PortiaAttentionReport:
        return PortiaAttentionReport(
            query=query,
            evaluation="evaluated",
            summaries=(
                PortiaAttentionSummary(
                    code=definition.code,
                    label=definition.label,
                    count=MAX_MODULE_OPERATION_COUNT + 1,
                    count_unit=definition.count_unit,
                    attention_class=definition.attention_class,
                ),
            ),
        )

    captured: dict[str, object] = {}
    _stub_service(monkeypatch, native, captured)
    report = provider._evaluate_portia_attention(
        ModuleOperationsRequest(workspace_root=tmp_path),
        clock=lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    assert report.evaluation == "evaluated"
    assert report.summaries == ()
    assert tuple(notice.code for notice in report.notices) == (
        PORTIA_ATTENTION_PARTIAL_NOTICE,
    )


def test_unexpected_native_failure_crosses_provider_for_core_isolation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingService:
        def __init__(self, root: Path) -> None:
            self.root = root

        def query(self, query: PortiaAttentionQuery) -> PortiaAttentionReport:
            raise RuntimeError("PRIVATE failure detail")

    monkeypatch.setattr(provider, "AttentionQueryService", FailingService)
    monkeypatch.setattr(
        provider,
        "_system_clock",
        lambda: datetime(2026, 10, 1, 4, 0, tzinfo=timezone.utc),
    )

    result = invoke_module_attention(
        get_module_operations_profile(),
        ModuleOperationsRequest(workspace_root=tmp_path),
    )

    assert result.code == "module_operations.provider_failed"
    assert result.report is None
    assert "PRIVATE" not in result.message
