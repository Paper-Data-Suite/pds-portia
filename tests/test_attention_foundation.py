from __future__ import annotations

from pathlib import Path

import pytest

from portia.attention import (
    ATTENTION_DEFINITIONS,
    PORTIA_ATTENTION_PARTIAL_NOTICE,
    PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
    FollowUpScheduleItem,
    OpaqueAttentionSourceRef,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionNotice,
    PortiaAttentionQuery,
    PortiaAttentionReport,
    PortiaAttentionScope,
    build_attention_report,
    classify_follow_up_timing,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class-1",
        work_id="evt_issue49",
        work_kind="event",
        contract_version="2",
    )


def _record_ref(
    *,
    record_kind: str,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=_event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind=record_kind,
            record_id=record_id,
            contract_version="1",
        ),
    )


def _follow_up_ref() -> ExactPortiaWorkRecordRef:
    return _record_ref(
        record_kind="follow_up",
        record_id="fup_due",
    )


def _query(
    *,
    attention_codes: tuple[str, ...] = (),
    attention_classes: tuple[str, ...] = (),
) -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=PortiaAttentionScope.class_scope("class-1"),
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
        attention_codes=attention_codes,
        attention_classes=attention_classes,  # type: ignore[arg-type]
    )


def test_native_definition_registry_freezes_codes_units_classes_and_order() -> None:
    observed = [
        (
            definition.code,
            definition.count_unit,
            definition.attention_class,
            definition.definition_order,
        )
        for definition in ATTENTION_DEFINITIONS
    ]
    assert observed == [
        ("portia_follow_up_due", "follow_ups", "workflow", 0),
        ("portia_follow_up_overdue", "follow_ups", "workflow", 1),
        ("portia_review_incomplete", "reviews", "workflow", 2),
        (
            "portia_integrity_conflict",
            "integrity_findings",
            "integrity",
            3,
        ),
        (
            "portia_integrity_review_required",
            "integrity_findings",
            "integrity",
            4,
        ),
        ("portia_recovery_required", "recovery_scopes", "recovery", 5),
        ("portia_quarantine_active", "quarantines", "integrity", 6),
        (
            "portia_derived_state_stale",
            "derived_projections",
            "recovery",
            7,
        ),
        (
            "portia_support_process_review_due",
            "support_processes",
            "workflow",
            8,
        ),
        (
            "portia_support_process_review_overdue",
            "support_processes",
            "workflow",
            9,
        ),
        (
            "portia_support_process_dependency_attention",
            "support_processes",
            "workflow",
            10,
        ),
    ]


def test_timing_bearing_definitions_freeze_due_overdue_semantics() -> None:
    observed = {
        definition.code: definition.timing_classification
        for definition in ATTENTION_DEFINITIONS
        if definition.timing_classification is not None
    }

    assert observed == {
        "portia_follow_up_due": "due",
        "portia_follow_up_overdue": "overdue",
        "portia_support_process_review_due": "due",
        "portia_support_process_review_overdue": "overdue",
    }


def test_report_builder_orders_definition_timing_then_exact_identity() -> None:
    due = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-21"},
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
    )
    overdue = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-20"},
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
    )

    items = (
        PortiaAttentionItem(
            code="portia_recovery_required",
            source_ref=OpaqueAttentionSourceRef(
                kind="recovery_scope",
                identifier="op_issue49",
            ),
        ),
        PortiaAttentionItem(
            code="portia_follow_up_overdue",
            source_ref=_follow_up_ref(),
            context=PortiaAttentionContext(work_ref=_event_ref()),
            reason_codes=("scheduled_state",),
            timing=overdue,
        ),
        PortiaAttentionItem(
            code="portia_follow_up_due",
            source_ref=_follow_up_ref(),
            context=PortiaAttentionContext(work_ref=_event_ref()),
            reason_codes=("scheduled_state",),
            timing=due,
        ),
    )

    query = _query()
    report = build_attention_report(query, items)

    assert report.scope is query.scope
    assert report.as_of is query.as_of
    assert [item.code for item in report.items] == [
        "portia_follow_up_due",
        "portia_follow_up_overdue",
        "portia_recovery_required",
    ]
    assert [
        (summary.code, summary.count) for summary in report.summaries
    ] == [
        ("portia_follow_up_due", 1),
        ("portia_follow_up_overdue", 1),
        ("portia_recovery_required", 1),
    ]


def test_report_builder_applies_filters_without_reclassification() -> None:
    items = (
        PortiaAttentionItem(
            code="portia_review_incomplete",
            source_ref=_record_ref(
                record_kind="review",
                record_id="rvw_incomplete",
            ),
            reason_codes=("open",),
        ),
        PortiaAttentionItem(
            code="portia_recovery_required",
            source_ref=OpaqueAttentionSourceRef(
                kind="recovery_scope",
                identifier="op_issue49",
            ),
        ),
    )

    report = build_attention_report(
        _query(attention_classes=("recovery",)),
        items,
    )
    assert [item.code for item in report.items] == [
        "portia_recovery_required"
    ]


def test_future_scheduled_follow_up_is_schedule_not_attention() -> None:
    scheduled = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-22"},
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
    )
    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionItem(
            code="portia_follow_up_due",
            source_ref=_follow_up_ref(),
            timing=scheduled,
        )

    schedule_item = FollowUpScheduleItem(
        source_ref=_follow_up_ref(),
        timing=scheduled,
    )
    assert schedule_item.timing.classification == "scheduled"


def test_timing_bearing_attention_codes_require_matching_timing() -> None:
    due = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-21"},
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
    )
    overdue = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-20"},
        as_of=ExplicitOffsetTimestamp(
            "2026-09-21T19:00:00-04:00"
        ),
    )

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionItem(
            code="portia_follow_up_due",
            source_ref=_follow_up_ref(),
        )

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionItem(
            code="portia_follow_up_due",
            source_ref=_follow_up_ref(),
            timing=overdue,
        )

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionItem(
            code="portia_follow_up_overdue",
            source_ref=_follow_up_ref(),
            timing=due,
        )

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionItem(
            code="portia_review_incomplete",
            source_ref=_record_ref(
                record_kind="review",
                record_id="rvw_incomplete",
            ),
            timing=due,
        )


def test_unavailable_report_differs_from_empty_evaluated_report() -> None:
    evaluated = build_attention_report(_query())
    assert evaluated.evaluation == "evaluated"
    assert evaluated.items == ()
    assert evaluated.summaries == ()

    notice = PortiaAttentionNotice(
        code=PORTIA_ATTENTION_UNAVAILABLE_NOTICE,
        message=(
            "The exact requested Portia scope cannot be inspected safely."
        ),
    )
    unavailable = build_attention_report(
        _query(),
        notices=(notice,),
        evaluation="unavailable",
    )
    assert unavailable.evaluation == "unavailable"
    assert unavailable.items == ()
    assert unavailable.summaries == ()

    with pytest.raises(PortiaLocalValidationError):
        PortiaAttentionReport(
            query=_query(),
            evaluation="unavailable",
        )

    with pytest.raises(PortiaLocalValidationError):
        build_attention_report(
            _query(),
            notices=(notice,),
        )


def test_partial_notice_is_bounded_and_keeps_evaluated_state() -> None:
    report = build_attention_report(
        _query(),
        notices=(
            PortiaAttentionNotice(
                code=PORTIA_ATTENTION_PARTIAL_NOTICE,
                message=(
                    "One independent Portia scope could not be inspected safely."
                ),
            ),
        ),
    )
    assert report.evaluation == "evaluated"
    assert report.notices[0].code == PORTIA_ATTENTION_PARTIAL_NOTICE


def _tree_snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (
                str(path.relative_to(root)),
                path.read_bytes(),
            )
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_slice1_contract_and_timing_helpers_are_zero_write(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sentinel = workspace / "sentinel.txt"
    sentinel.write_text("unchanged\n", encoding="utf-8")
    before = _tree_snapshot(workspace)

    query = _query()
    timing = classify_follow_up_timing(
        {"kind": "date_only", "date": "2026-09-21"},
        as_of=query.as_of,
    )
    item = PortiaAttentionItem(
        code="portia_follow_up_due",
        source_ref=_follow_up_ref(),
        timing=timing,
    )
    report = build_attention_report(query, (item,))

    assert report.items == (item,)
    assert _tree_snapshot(workspace) == before
