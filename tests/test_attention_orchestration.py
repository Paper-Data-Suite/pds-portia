from __future__ import annotations

from pathlib import Path

from pds_core.routes import classes_dir

from portia.attention import (
    AttentionQueryService,
    FollowUpScheduleQuery,
    FollowUpScheduleQueryService,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
from portia.storage.repository import PortiaRepository
from portia.workflows import FollowUpWorkflowService
from tests.workflow_helpers import (
    AGENT,
    event_record,
    event_ref,
    participant_record,
)

AS_OF = ExplicitOffsetTimestamp("2026-09-21T12:00:00-04:00")
CREATED = "2026-09-20T09:00:00-04:00"


def _follow_up(
    *,
    class_id: str,
    event_id: str,
    participant_id: str,
    follow_up_id: str,
) -> PortiaRecord:
    return parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": class_id,
            "work_kind": "event",
            "work_id": event_id,
            "follow_up_id": follow_up_id,
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": participant_id,
                    "contract_version": "3",
                },
            },
            "owner": {
                "kind": "represented_human",
                "person": {
                    "kind": "local_operator",
                    "display_label": "Synthetic teacher",
                },
            },
            "purpose": {"kind": "student_check_in"},
            "planned_timing": {
                "kind": "date_only",
                "date": "2026-09-21",
            },
            "workflow_state": "scheduled",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _seed_due(
    root: Path,
    *,
    class_id: str,
    event_id: str,
    participant_id: str,
    follow_up_id: str,
) -> None:
    repository = PortiaRepository(root)
    work = event_ref(class_id=class_id, event_id=event_id)
    repository.create_work(
        work,
        event_record(class_id=class_id, event_id=event_id, status="active"),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id=participant_id,
            class_id=class_id,
            event_id=event_id,
            subject={
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
            },
        ),
    )
    FollowUpWorkflowService(root, repository=repository).create(
        work,
        _follow_up(
            class_id=class_id,
            event_id=event_id,
            participant_id=participant_id,
            follow_up_id=follow_up_id,
        ),
    )


def _attention(scope: PortiaAttentionScope) -> PortiaAttentionQuery:
    return PortiaAttentionQuery(
        scope=scope,
        as_of=AS_OF,
        attention_codes=("portia_follow_up_due",),
    )


def test_exact_unknown_work_is_unavailable_not_empty(tmp_path: Path) -> None:
    report = AttentionQueryService(tmp_path).query(
        _attention(
            PortiaAttentionScope.work_scope(
                event_ref(event_id="evt_missing")
            )
        )
    )

    assert report.evaluation == "unavailable"
    assert report.items == ()
    assert report.summaries == ()
    assert len(report.notices) == 1
    assert report.notices[0].code == "portia_attention_unavailable"


def test_exact_unknown_class_is_unavailable_not_workspace_fallback(
    tmp_path: Path,
) -> None:
    _seed_due(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        follow_up_id="fup_alpha",
    )

    report = AttentionQueryService(tmp_path).query(
        _attention(PortiaAttentionScope.class_scope("class_missing"))
    )

    assert report.evaluation == "unavailable"
    assert report.items == ()


def test_exact_class_aggregates_supported_work(tmp_path: Path) -> None:
    _seed_due(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        follow_up_id="fup_alpha",
    )

    report = AttentionQueryService(tmp_path).query(
        _attention(PortiaAttentionScope.class_scope("class_a"))
    )

    assert report.evaluation == "evaluated"
    assert len(report.items) == 1
    assert report.items[0].source_ref.record_ref.record_id == "fup_alpha"
    assert report.notices == ()


def test_workspace_aggregates_classes_deterministically(tmp_path: Path) -> None:
    _seed_due(
        tmp_path,
        class_id="class_b",
        event_id="evt_beta",
        participant_id="ep_beta",
        follow_up_id="fup_beta",
    )
    _seed_due(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        follow_up_id="fup_alpha",
    )

    report = AttentionQueryService(tmp_path).query(
        _attention(PortiaAttentionScope.workspace_scope())
    )

    assert report.evaluation == "evaluated"
    assert [
        item.source_ref.record_ref.record_id
        for item in report.items
    ] == ["fup_alpha", "fup_beta"]
    assert report.notices == ()


def test_workspace_malformed_independent_class_is_partial(
    tmp_path: Path,
) -> None:
    _seed_due(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        follow_up_id="fup_alpha",
    )
    (classes_dir(tmp_path) / "bad class!").mkdir(parents=True)

    report = AttentionQueryService(tmp_path).query(
        _attention(PortiaAttentionScope.workspace_scope())
    )

    assert report.evaluation == "evaluated"
    assert len(report.items) == 1
    assert len(report.notices) == 1
    assert report.notices[0].code == "portia_attention_partial"


def test_follow_up_schedule_supports_exact_class_and_workspace(
    tmp_path: Path,
) -> None:
    _seed_due(
        tmp_path,
        class_id="class_a",
        event_id="evt_alpha",
        participant_id="ep_alpha",
        follow_up_id="fup_alpha",
    )
    _seed_due(
        tmp_path,
        class_id="class_b",
        event_id="evt_beta",
        participant_id="ep_beta",
        follow_up_id="fup_beta",
    )
    service = FollowUpScheduleQueryService(tmp_path)

    class_items = service.query(
        FollowUpScheduleQuery(
            scope=PortiaAttentionScope.class_scope("class_a"),
            as_of=AS_OF,
        )
    )
    workspace_items = service.query(
        FollowUpScheduleQuery(
            scope=PortiaAttentionScope.workspace_scope(),
            as_of=AS_OF,
        )
    )

    assert [item.source_ref.record_ref.record_id for item in class_items] == [
        "fup_alpha"
    ]
    assert [item.source_ref.record_ref.record_id for item in workspace_items] == [
        "fup_alpha",
        "fup_beta",
    ]
