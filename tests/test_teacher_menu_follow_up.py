from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.menu.authoring import (
    FollowUpCompletionInput,
    prepare_follow_up_completion,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.follow_up import (
    complete_follow_up_once,
    follow_up_options,
)
from portia.menu.main import launch_menu
from portia.models import FollowUpV1, PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository
from portia.workflows import FollowUpWorkflowService, follow_up_reference

FIXED_NOW = datetime(
    2026,
    9,
    23,
    12,
    0,
    tzinfo=timezone(timedelta(hours=-4)),
)
CREATED = "2026-09-22T09:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue50_slice9_test"}


def _add_class(root: Path) -> None:
    ensure_workspace_root(root)
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            "class_a",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _event_record() -> PortiaRecord:
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {"precision": "exact", "started_at": CREATED},
            "summary": "Synthetic bounded Event for menu Follow-Up testing.",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _participant_record() -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "participant_id": "ep_alpha",
            "status": "active",
            "subject": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _follow_up_record(
    follow_up_id: str,
    planned_date: str,
) -> FollowUpV1:
    record = parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "follow_up_id": follow_up_id,
            "status": "active",
            "target": {
                "kind": "event_participant",
                "record_ref": {
                    "record_kind": "event_participant",
                    "record_id": "ep_alpha",
                    "contract_version": "3",
                },
            },
            "owner": {
                "kind": "represented_human",
                "person": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "purpose": {"kind": "student_check_in"},
            "planned_timing": {"kind": "date_only", "date": planned_date},
            "workflow_state": "scheduled",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )
    assert isinstance(record, FollowUpV1)
    return record


def _support_review_follow_up() -> FollowUpV1:
    record = parse_portia_record(
        "follow_up",
        "1",
        {
            "schema_version": "1",
            "record_type": "follow_up",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "support_process",
            "work_id": "sup_alpha",
            "follow_up_id": "fup_support",
            "status": "active",
            "target": {"kind": "support_process"},
            "owner": {
                "kind": "support_process_participant",
                "participant_ref": {
                    "record_kind": "support_process_participant",
                    "record_id": "spp_coordinator",
                    "contract_version": "1",
                },
            },
            "purpose": {"kind": "support_process_review"},
            "planned_timing": {"kind": "date_only", "date": "2026-09-23"},
            "workflow_state": "scheduled",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )
    assert isinstance(record, FollowUpV1)
    return record


def _seed_event(root: Path) -> FollowUpWorkflowService:
    _add_class(root)
    repository = PortiaRepository(root)
    repository.create_work(_event_ref(), _event_record())
    repository.create_work_record(_event_ref(), _participant_record())
    return FollowUpWorkflowService(root, repository=repository)


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_prepare_completion_preserves_identity_and_changes_only_completion_fields() -> None:
    prior = _follow_up_record("fup_due", "2026-09-23")
    candidate = prepare_follow_up_completion(
        FollowUpCompletionInput(
            prior=prior,
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
    )

    before = prior.to_dict()
    after = candidate.to_dict()
    changed = {
        key
        for key in set(before) | set(after)
        if before.get(key) != after.get(key)
    }
    assert candidate.logical_id == prior.logical_id
    assert candidate.status == "active"
    assert changed == {
        "workflow_state",
        "completed_at",
        "updated_at",
        "updated_by",
    }
    assert after["workflow_state"] == "completed"
    assert after["completed_at"] == FIXED_NOW.isoformat()


def test_support_review_completion_may_add_disposition_without_outcome() -> None:
    candidate = prepare_follow_up_completion(
        FollowUpCompletionInput(
            prior=_support_review_follow_up(),
            local_operator_label="Synthetic Teacher",
            disposition_kind="complete_process",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
    )
    assert candidate.field("disposition") == {"kind": "complete_process"}
    assert candidate.field("workflow_state") == "completed"
    assert candidate.field("work_kind") == "support_process"


def test_workspace_schedule_options_keep_due_overdue_and_future_distinct_and_zero_write(
    tmp_path: Path,
) -> None:
    service = _seed_event(tmp_path)
    for identifier, planned in (
        ("fup_future", "2026-09-24"),
        ("fup_due", "2026-09-23"),
        ("fup_overdue", "2026-09-22"),
    ):
        service.create(_event_ref(), _follow_up_record(identifier, planned))
    before = _snapshot(tmp_path)

    options = follow_up_options(tmp_path, clock=MenuClock(lambda: FIXED_NOW))

    assert [item.classification for item in options] == [
        "due",
        "overdue",
        "scheduled",
    ]
    assert [item.reference.record_ref.record_id for item in options] == [
        "fup_due",
        "fup_overdue",
        "fup_future",
    ]
    assert _snapshot(tmp_path) == before


def test_existing_service_completes_exact_follow_up_without_downstream_records(
    tmp_path: Path,
) -> None:
    service = _seed_event(tmp_path)
    created = service.create(
        _event_ref(),
        _follow_up_record("fup_due", "2026-09-23"),
    )
    reference = follow_up_reference(_event_ref(), "fup_due")
    candidate = prepare_follow_up_completion(
        FollowUpCompletionInput(
            prior=created.record,
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
    )

    accepted = service.transition_workflow_state(
        reference,
        candidate,
        expected=created.fingerprint,
    )

    assert accepted.record.field("workflow_state") == "completed"
    repository = PortiaRepository(tmp_path)
    for kind in ("outcome", "reentry", "repair"):
        assert repository.list_work_records(
            _event_ref(),
            kind,
            version="1",
        ) == ()


def test_cancelled_completion_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _seed_event(tmp_path)
    created = service.create(
        _event_ref(),
        _follow_up_record("fup_due", "2026-09-23"),
    )
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(("1", ""))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    complete_follow_up_once(
        MenuSessionContext(local_operator_label="Synthetic Teacher"),
        clock=MenuClock(lambda: FIXED_NOW),
    )

    reference = follow_up_reference(_event_ref(), "fup_due")
    assert service.load_exact(reference).fingerprint == created.fingerprint
    assert service.load_exact(reference).record.field("workflow_state") == "scheduled"


def test_main_menu_routes_to_complete_follow_up_surface_without_read(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("5", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Complete Follow-Up" in output
    assert "1. Review scheduled Follow-Ups" in output
