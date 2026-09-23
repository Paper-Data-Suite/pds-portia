"""Privacy and low-density contract tests for Issue #49 attention."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from portia.attention import (
    AttentionQueryService,
    OpaqueAttentionSourceRef,
    PortiaAttentionItem,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository
from portia.workflows import FollowUpWorkflowService

AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")


def _work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_privacy",
        work_kind="event",
        contract_version="2",
    )


def _event():
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_privacy",
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {
                "precision": "exact",
                "started_at": "2026-09-20T09:00:00-04:00",
            },
            "summary": "Synthetic privacy event.",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-20T09:00:00-04:00",
            "created_by": {
                "type": "local_operator",
                "display_label": "Teacher",
            },
            "updated_at": "2026-09-20T09:00:00-04:00",
            "updated_by": {
                "type": "local_operator",
                "display_label": "Teacher",
            },
        },
    )


def _participant():
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_privacy",
            "participant_id": "ep_privacy",
            "status": "active",
            "subject": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "PRIVATE STUDENT NAME",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-20T09:00:00-04:00",
            "created_by": {
                "type": "local_operator",
                "display_label": "Teacher",
            },
            "updated_at": "2026-09-20T09:00:00-04:00",
            "updated_by": {
                "type": "local_operator",
                "display_label": "Teacher",
            },
        },
    )


def _follow_up():
    return parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_privacy",
            "follow_up_id": "fup_privacy",
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_privacy",
                    "contract_version": "3",
                },
            },
            "owner": {
                "kind": "represented_human",
                "person": {
                    "kind": "local_operator",
                    "display_label": "Teacher",
                },
            },
            "purpose": {"kind": "student_check_in"},
            "planned_timing": {
                "kind": "date_only",
                "date": "2026-09-21",
            },
            "workflow_state": "scheduled",
            "creation_source": {"type": "digital_entry"},
            "created_at": "2026-09-20T09:00:00-04:00",
            "created_by": {
                "type": "system_process",
                "process_id": "issue49_privacy_test",
            },
            "updated_at": "2026-09-20T09:00:00-04:00",
            "updated_by": {
                "type": "system_process",
                "process_id": "issue49_privacy_test",
            },
        },
    )


def test_attention_item_contract_is_low_density() -> None:
    assert {field.name for field in fields(PortiaAttentionItem)} == {
        "code",
        "source_ref",
        "context",
        "reason_codes",
        "timing",
    }
    assert {field.name for field in fields(OpaqueAttentionSourceRef)} == {
        "kind",
        "identifier",
    }


def test_native_attention_does_not_duplicate_student_narrative(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = _work()
    repository.create_work(work, _event())
    repository.create_work_record(work, _participant())
    FollowUpWorkflowService(tmp_path, repository=repository).create(
        work,
        _follow_up(),
    )

    report = AttentionQueryService(
        tmp_path,
        repository=repository,
    ).query(
        PortiaAttentionQuery(
            scope=PortiaAttentionScope.work_scope(work),
            as_of=AS_OF,
        )
    )

    assert len(report.items) == 1
    rendered = repr(report)
    assert "PRIVATE STUDENT NAME" not in rendered
    assert "outside_student" not in rendered
    assert "student_check_in" not in rendered
