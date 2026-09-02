from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRef
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


def _support_process_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def _support_process_relationship_record():
    wire = relationship_record().to_dict()
    wire["work_id"] = "sup_alpha"
    wire["source"] = _support_process_ref().to_dict()
    return parse_portia_record("work_relationship", "2", wire)


def test_active_support_process_source_delegates_to_issue44_current_authority(
    tmp_path: Path,
) -> None:
    candidate = _support_process_relationship_record()
    source = _support_process_ref()
    target = event_ref(event_id="evt_beta")
    source_stored = SimpleNamespace(record=SimpleNamespace(status="active"))
    target_stored = SimpleNamespace(record=event_record(event_id="evt_beta"))
    repository = Mock()
    repository.load_work.side_effect = [
        source_stored,
        target_stored,
        target_stored,
    ]
    repository.list_work_relationships.return_value = ()
    repository.create_work_record.return_value = SimpleNamespace(record=candidate)
    service = WorkRelationshipService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    service.validate_complete_graph = Mock()

    with patch(
        "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use",
        return_value=source_stored,
    ) as require_support_process_current:
        stored = service.create(candidate)

    assert stored.record == candidate
    require_support_process_current.assert_called_once_with(source)
    repository.create_work_record.assert_called_once_with(source, candidate)
    assert repository.load_work.call_args_list[-1].args == (target,)


def test_support_process_relationship_current_use_rechecks_issue44_owner_authority(
    tmp_path: Path,
) -> None:
    candidate = _support_process_relationship_record()
    source = _support_process_ref()
    target = event_ref(event_id="evt_beta")
    source_stored = SimpleNamespace(record=SimpleNamespace(status="active"))
    target_stored = SimpleNamespace(record=event_record(event_id="evt_beta"))
    resolution = SimpleNamespace(
        relationship=SimpleNamespace(record=candidate),
        source=source_stored,
        target=target_stored,
    )
    repository = Mock()
    repository.load_work.return_value = target_stored
    repository.list_work_relationships.return_value = ()
    service = WorkRelationshipService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with (
        patch.object(service, "resolve_exact", return_value=resolution),
        patch(
            "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use",
            return_value=source_stored,
        ) as require_support_process_current,
    ):
        current = service.require_current_use(
            relationship_reference(source, "rel_alpha")
        )

    assert current is resolution
    require_support_process_current.assert_called_once_with(source)
    repository.load_work.assert_called_once_with(target)


def test_support_process_relationship_fails_before_target_use_when_process_not_current(
    tmp_path: Path,
) -> None:
    candidate = _support_process_relationship_record()
    source = _support_process_ref()
    target = event_ref(event_id="evt_beta")
    repository = Mock()
    service = WorkRelationshipService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with (
        patch(
            "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use",
            side_effect=WorkflowPrerequisiteError(
                "synthetic Support Process is not current"
            ),
        ) as require_support_process_current,
        pytest.raises(
            WorkflowPrerequisiteError,
            match="synthetic Support Process is not current",
        ),
    ):
        service._preflight_current(candidate, source, target)

    require_support_process_current.assert_called_once_with(source)
    repository.load_work.assert_not_called()
