from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage import PortiaNotFoundError
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkRelationshipService,
    relationship_reference,
)
from tests.workflow_helpers import (
    event_record,
    event_ref,
    participant_record,
    relationship_record,
)


def _seed_target(tmp_path: Path, *, status: str = "active") -> None:
    events = EventWorkflowService(tmp_path)
    events.create(event_record(status="draft"))
    target = events.create(event_record(event_id="evt_beta", status="draft"))
    ParticipantWorkflowService(tmp_path).create(
        event_ref(event_id="evt_beta"),
        participant_record(
            event_id="evt_beta",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    active = events.replace(
        event_record(
            event_id="evt_beta",
            status="active",
            updated_at="2026-08-26T12:05:00-04:00",
        ),
        expected=target.fingerprint,
    )
    if status == "closed":
        events.replace(
            event_record(
                event_id="evt_beta",
                status="closed",
                updated_at="2026-08-26T12:10:00-04:00",
            ),
            expected=active.fingerprint,
        )


def test_relationship_create_exact_resolution_and_bounded_list(tmp_path: Path) -> None:
    _seed_target(tmp_path)
    service = WorkRelationshipService(tmp_path)
    service.create(relationship_record())
    resolved = service.resolve_exact(
        relationship_reference(event_ref(), "rel_alpha")
    )
    assert resolved.source.record.logical_id == "evt_alpha"
    assert resolved.target.record.logical_id == "evt_beta"
    assert len(service.list(event_ref())) == 1


def test_unresolved_relationship_is_zero_write(tmp_path: Path) -> None:
    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    service = WorkRelationshipService(tmp_path)
    collection = (
        tmp_path
        / "classes/class_a/modules/portia/work/evt_alpha/records/work_relationship"
    )
    with pytest.raises(PortiaNotFoundError):
        service.create(relationship_record(target_event="evt_missing"))
    assert not collection.exists()


@pytest.mark.parametrize("target_status", ["active", "closed"])
def test_active_relationship_accepts_current_contextual_target_statuses(
    tmp_path: Path, target_status: str
) -> None:
    _seed_target(tmp_path, status=target_status)
    service = WorkRelationshipService(tmp_path)
    service.create(relationship_record())
    resolution = service.require_current_use(
        relationship_reference(event_ref(), "rel_alpha")
    )
    assert resolution.target.record.status == target_status


def test_active_relationship_rejects_draft_target_with_zero_write(
    tmp_path: Path,
) -> None:
    events = EventWorkflowService(tmp_path)
    events.create(event_record(status="draft"))
    events.create(event_record(event_id="evt_beta", status="draft"))
    service = WorkRelationshipService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError):
        service.create(relationship_record())
    assert service.list(event_ref()) == ()


def test_relationship_target_source_and_provenance_retargeting_are_zero_write(
    tmp_path: Path,
) -> None:
    _seed_target(tmp_path)
    events = EventWorkflowService(tmp_path)
    gamma = events.create(event_record(event_id="evt_gamma", status="draft"))
    ParticipantWorkflowService(tmp_path).create(
        event_ref(event_id="evt_gamma"),
        participant_record(
            event_id="evt_gamma",
            participant_id="ep_gamma",
            subject={"kind": "unknown_person", "reason": "identity_not_known"},
        ),
    )
    events.replace(
        event_record(
            event_id="evt_gamma",
            updated_at="2026-08-26T12:05:00-04:00",
        ),
        expected=gamma.fingerprint,
    )
    service = WorkRelationshipService(tmp_path)
    created = service.create(relationship_record())
    canonical = created.path.read_bytes()

    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            relationship_record(
                target_event="evt_gamma",
                updated_at="2026-08-26T12:10:00-04:00",
            ),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical
    source_wire = relationship_record(
        updated_at="2026-08-26T12:10:00-04:00"
    ).to_dict()
    source_wire["source"] = event_ref(event_id="evt_gamma").to_dict()
    source_candidate = parse_portia_record("work_relationship", "2", source_wire)
    with pytest.raises(WorkflowOwnershipError):
        service.replace(source_candidate, expected=created.fingerprint)
    assert created.path.read_bytes() == canonical


def test_relationship_terminal_state_cannot_be_resurrected(tmp_path: Path) -> None:
    _seed_target(tmp_path)
    service = WorkRelationshipService(tmp_path)
    created = service.create(relationship_record(status="invalidated"))
    canonical = created.path.read_bytes()
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            relationship_record(updated_at="2026-08-26T12:10:00-04:00"),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical

    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            relationship_record(
                created_at="2026-08-26T12:00:01-04:00",
                updated_at="2026-08-26T12:10:00-04:00",
            ),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical
