"""Closeout acceptance matrix for Portia Issue #49 native attention."""

from __future__ import annotations

import hashlib
from dataclasses import fields
from pathlib import Path

import portia.views as views
from portia.attention import (
    ATTENTION_CLASSES,
    ATTENTION_DEFINITIONS,
    AttentionQueryService,
    FollowUpScheduleQueryService,
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


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _seed_due(root: Path) -> ExactPortiaWorkRef:
    repository = PortiaRepository(root)
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_closeout",
        work_kind="event",
        contract_version="2",
    )
    event = parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_closeout",
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {
                "precision": "exact",
                "started_at": "2026-09-20T09:00:00-04:00",
            },
            "summary": "Synthetic Issue #49 closeout event.",
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
    participant = parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_closeout",
            "participant_id": "ep_closeout",
            "status": "active",
            "subject": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
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
    follow_up = parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_closeout",
            "follow_up_id": "fup_closeout",
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_closeout",
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
                "process_id": "issue49_closeout_test",
            },
            "updated_at": "2026-09-20T09:00:00-04:00",
            "updated_by": {
                "type": "system_process",
                "process_id": "issue49_closeout_test",
            },
        },
    )
    repository.create_work(work, event)
    repository.create_work_record(work, participant)
    FollowUpWorkflowService(root, repository=repository).create(
        work,
        follow_up,
    )
    return work


def test_issue49_taxonomy_is_closed_and_workflow_counted() -> None:
    expected = {
        "portia_follow_up_due": ("workflow", "follow_ups"),
        "portia_follow_up_overdue": ("workflow", "follow_ups"),
        "portia_review_incomplete": ("workflow", "reviews"),
        "portia_integrity_conflict": ("integrity", "integrity_findings"),
        "portia_integrity_review_required": (
            "integrity",
            "integrity_findings",
        ),
        "portia_recovery_required": ("recovery", "recovery_scopes"),
        "portia_quarantine_active": ("integrity", "quarantines"),
        "portia_derived_state_stale": ("recovery", "derived_projections"),
        "portia_support_process_review_due": (
            "workflow",
            "support_processes",
        ),
        "portia_support_process_review_overdue": (
            "workflow",
            "support_processes",
        ),
        "portia_support_process_dependency_attention": (
            "workflow",
            "support_processes",
        ),
    }
    observed = {
        definition.code: (
            definition.attention_class,
            definition.count_unit,
        )
        for definition in ATTENTION_DEFINITIONS
    }
    assert observed == expected
    assert ATTENTION_CLASSES == ("workflow", "recovery", "integrity")


def test_issue49_contract_has_no_risk_priority_surface() -> None:
    names = {field.name for field in fields(PortiaAttentionItem)}
    assert names.isdisjoint(
        {
            "risk",
            "risk_score",
            "behavior_score",
            "urgency",
            "urgency_score",
            "priority",
            "priority_score",
            "student_ranking",
        }
    )


def test_issue49_native_query_is_deterministic_and_zero_write(
    tmp_path: Path,
) -> None:
    work = _seed_due(tmp_path)
    query = PortiaAttentionQuery(
        scope=PortiaAttentionScope.work_scope(work),
        as_of=AS_OF,
    )
    service = AttentionQueryService(tmp_path)
    before = _snapshot(tmp_path)

    first = service.query(query)
    second = service.query(query)

    after = _snapshot(tmp_path)
    assert first == second
    assert [item.code for item in first.items] == ["portia_follow_up_due"]
    assert before == after


def test_issue49_preserves_separate_schedule_and_attention_services() -> None:
    assert AttentionQueryService is not FollowUpScheduleQueryService


def test_issue49_preserves_issue48_student_view_public_surface() -> None:
    assert hasattr(views, "StudentTimelineService")
    assert hasattr(views, "StudentTimelineQuery")
    assert hasattr(views, "StudentViewScope")
