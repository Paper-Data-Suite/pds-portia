from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.identity import ActorDirectoryService, RosterNotFoundError
from portia.models import parse_portia_record
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    participant_reference,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
)


def _write_roster(root: Path, class_id: str = "class_a") -> None:
    write_class_roster(
        root,
        create_roster(
            class_id,
            [
                {
                    "student_id": "student_1",
                    "last_name": "Same",
                    "first_name": "Display",
                    "period": "2",
                }
            ],
        ),
    )


def _actor() -> object:
    return parse_portia_record(
        "actor",
        "1",
        {
            "schema_version": "1",
            "record_type": "actor",
            "module_id": "portia",
            "actor_id": "actr_alpha",
            "status": "active",
            "display": {"display_name": "Same Display"},
            "actor_category": {"kind": "other", "detail": "Synthetic visitor"},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_all_four_subject_forms_preserve_explicit_identity(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    ActorDirectoryService(tmp_path).create_actor(_actor())  # type: ignore[arg-type]
    service = ParticipantWorkflowService(tmp_path)
    records = (
        participant_record(),
        participant_record(
            participant_id="ep_actor",
            subject={
                "kind": "actor",
                "actor_ref": {"actor_id": "actr_alpha"},
                "display_snapshot": {"display_name": "Same Display"},
            },
        ),
        participant_record(
            participant_id="ep_descriptive",
            subject={
                "kind": "descriptive_person",
                "description_type": "visitor",
                "display_label": "Same Display",
            },
        ),
        participant_record(
            participant_id="ep_unknown",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    for record in records:
        service.create(event_ref(), record)
    kinds = {
        service.resolve_person(
            participant_reference(event_ref(), record.logical_id or "")
        ).kind
        for record in records
    }
    assert kinds == {"roster_student", "actor", "descriptive_person", "unknown_person"}
    assert len(service.list(event_ref())) == 4


def test_exact_roster_identity_remains_class_qualified(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    _write_roster(tmp_path, "class_b")
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ParticipantWorkflowService(tmp_path)
    first = participant_record(participant_id="ep_first")
    second = participant_record(
        participant_id="ep_second",
        subject={
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_b",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Same Display"},
        },
    )
    service.create(event_ref(), first)
    service.create(event_ref(), second)
    one = service.resolve_person(participant_reference(event_ref(), "ep_first"))
    two = service.resolve_person(participant_reference(event_ref(), "ep_second"))
    assert one.authority != two.authority
    assert one.authority.reference.class_id == "class_a"  # type: ignore[union-attr]
    assert two.authority.reference.class_id == "class_b"  # type: ignore[union-attr]


def test_snapshot_revision_does_not_retarget_roster_identity(tmp_path: Path) -> None:
    _write_roster(tmp_path, "class_a")
    _write_roster(tmp_path, "class_b")
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ParticipantWorkflowService(tmp_path)
    created = service.create(event_ref(), participant_record())
    changed_snapshot = participant_record(
        subject={
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_a",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Updated Snapshot"},
        }
    )
    revised = service.replace(
        event_ref(), changed_snapshot, expected=created.fingerprint
    )
    assert revised.record.field("subject")["display_snapshot"]["display_name"] == (
        "Updated Snapshot"
    )

    retargeted = participant_record(
        subject={
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": "class_b",
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Same Display"},
        }
    )
    with pytest.raises(WorkflowOwnershipError):
        service.replace(event_ref(), retargeted, expected=revised.fingerprint)
    assert service.resolve_person(
        participant_reference(event_ref(), "ep_alpha")
    ).authority.reference.class_id == "class_a"  # type: ignore[union-attr]


def test_roster_resolution_failure_retains_typed_identity_error_and_zero_write(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    with pytest.raises(RosterNotFoundError):
        ParticipantWorkflowService(tmp_path).create(
            event_ref(), participant_record()
        )
    assert not (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/event_participant"
    ).exists()


def test_final_active_participant_transition_is_zero_write(tmp_path: Path) -> None:
    _write_roster(tmp_path)
    events = EventWorkflowService(tmp_path)
    draft = events.create(event_record(status="draft"))
    participants = ParticipantWorkflowService(tmp_path)
    created = participants.create(event_ref(), participant_record())
    events.replace(
        event_record(updated_at="2026-08-26T12:05:00-04:00"),
        expected=draft.fingerprint,
    )
    canonical = created.path.read_bytes()
    invalidated = participant_record(
        status="invalidated", updated_at="2026-08-26T12:10:00-04:00"
    )
    with pytest.raises(WorkflowPrerequisiteError):
        participants.replace(event_ref(), invalidated, expected=created.fingerprint)
    assert created.path.read_bytes() == canonical

    participants.create(
        event_ref(),
        participant_record(
            participant_id="ep_other",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    replaced = participants.replace(
        event_ref(), invalidated, expected=created.fingerprint
    )
    assert replaced.record.status == "invalidated"


def test_participant_terminal_resurrection_and_creation_rewrite_are_zero_write(
    tmp_path: Path,
) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = ParticipantWorkflowService(tmp_path)
    created = service.create(
        event_ref(),
        participant_record(
            status="invalidated",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    canonical = created.path.read_bytes()
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            event_ref(),
            participant_record(
                status="active",
                updated_at="2026-08-26T12:05:00-04:00",
                subject={"kind": "unknown_person", "reason": "identity_not_known"},
            ),
            expected=created.fingerprint,
        )
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            event_ref(),
            participant_record(
                status="invalidated",
                created_at="2026-08-26T12:00:01-04:00",
                updated_at="2026-08-26T12:05:00-04:00",
                subject={"kind": "unknown_person", "reason": "identity_not_known"},
            ),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical
