from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from pds_core.workspace import ensure_workspace_root

from portia.attention import (
    ATTENTION_DEFINITIONS,
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    OpaqueAttentionSourceRef,
    PortiaAttentionItem,
    PortiaAttentionNotice,
    PortiaAttentionScope,
    TimingDecision,
    build_attention_report,
)
from portia.menu.attention import (
    ATTENTION_ROUTE_BY_CODE,
    attention_query,
    attention_report,
    attention_route,
    report_evaluation_label,
    route_attention_item,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.main import launch_menu
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)


def _clock() -> MenuClock:
    return MenuClock(
        now_source=lambda: datetime.fromisoformat(
            "2026-09-23T22:51:00-04:00"
        )
    )


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )



def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_route_table_is_closed_over_current_native_taxonomy() -> None:
    native_codes = {definition.code for definition in ATTENTION_DEFINITIONS}
    assert set(ATTENTION_ROUTE_BY_CODE) == native_codes
    assert attention_route("portia_follow_up_due") == "complete_follow_up"
    assert attention_route("portia_follow_up_due_future") is None


def test_attention_query_uses_explicit_menu_clock_instant() -> None:
    query = attention_query(
        PortiaAttentionScope.workspace_scope(),
        clock=_clock(),
    )
    assert query.scope.kind == "workspace"
    assert query.as_of.text == "2026-09-23T22:51:00-04:00"


def test_empty_workspace_attention_is_evaluated_and_zero_write(
    tmp_path: Path,
) -> None:
    ensure_workspace_root(tmp_path)
    before = _snapshot(tmp_path)

    report = attention_report(
        tmp_path,
        PortiaAttentionScope.workspace_scope(),
        clock=_clock(),
    )

    assert report.evaluation == "evaluated"
    assert report.items == ()
    assert report.summaries == ()
    assert report.notices == ()
    assert report_evaluation_label(report) == "Evaluated"
    assert _snapshot(tmp_path) == before


def test_partial_and_unavailable_labels_remain_distinct() -> None:
    query = attention_query(
        PortiaAttentionScope.workspace_scope(),
        clock=_clock(),
    )
    partial = build_attention_report(
        query,
        notices=(
            PortiaAttentionNotice(
                code=PORTIA_ATTENTION_PARTIAL_NOTICE,
                message=(
                    "One or more independent Portia attention sources "
                    "could not be evaluated safely."
                ),
            ),
        ),
    )
    unavailable = build_attention_report(
        query,
        notices=(
            PortiaAttentionNotice(
                code=PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
                message=(
                    "The requested Portia attention scope could not "
                    "be evaluated safely."
                ),
            ),
        ),
        evaluation="unavailable",
    )

    assert report_evaluation_label(partial) == "Partial"
    assert report_evaluation_label(unavailable) == "Unavailable"


def test_follow_up_route_remembers_exact_work_and_opens_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = MenuSessionContext()
    called: list[MenuSessionContext] = []
    monkeypatch.setattr(
        "portia.menu.attention.launch_complete_follow_up_menu",
        lambda selected_state: called.append(selected_state),
    )

    item = PortiaAttentionItem(
        code="portia_follow_up_due",
        source_ref=ExactPortiaWorkRecordRef(
            work_ref=_event_ref(),
            record_ref=ExactLocalRecordRef(
                record_kind="follow_up",
                record_id="fup_alpha",
                contract_version="1",
            ),
        ),
        timing=TimingDecision(
            classification="due",
            precision="date",
            start=date(2026, 9, 23),
            end=date(2026, 9, 23),
        ),
    )

    route_attention_item(state, item)

    assert called == [state]
    assert state.selected_class_id == "class_a"
    assert state.selected_work_kind == "event"
    assert state.selected_work_id == "evt_alpha"


def test_advanced_route_does_not_mutate_or_call_workflow_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = MenuSessionContext()
    monkeypatch.setattr("builtins.input", lambda _prompt: "")
    item = PortiaAttentionItem(
        code="portia_quarantine_active",
        source_ref=OpaqueAttentionSourceRef(
            kind="quarantine",
            identifier="qrn_alpha",
        ),
    )

    route_attention_item(state, item)

    assert state.selected_work_id is None


def test_main_menu_routes_to_attention_surface(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("8", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Attention Needed" in output
    assert "Workspace attention" in output
    assert "Exact work attention" in output
