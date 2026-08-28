from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage import PortiaConflictError, PortiaQuarantinedError
from portia.workflows import (
    EventWorkflowService,
    ParticipantWorkflowService,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)
from tests.workflow_helpers import (
    event_record,
    event_ref,
    event_wire,
    participant_record,
)


class _BlockingQuarantine:
    def __init__(self, effect: str) -> None:
        self.effect = effect

    def require_allowed(self, _target: object, effect: str) -> None:
        if effect == self.effect:
            raise PortiaQuarantinedError(f"synthetic block: {effect}")


def test_event_create_load_replace_and_bounded_list(tmp_path: Path) -> None:
    service = EventWorkflowService(tmp_path)
    created = service.create(event_record(status="draft"))
    assert service.load_exact(event_ref()).record.logical_id == "evt_alpha"
    assert [item.record.logical_id for item in service.list("class_a")] == ["evt_alpha"]

    replacement = event_record(
        status="draft", updated_at="2026-08-26T12:05:00-04:00"
    )
    service.replace(replacement, expected=created.fingerprint)
    with pytest.raises(PortiaConflictError):
        service.replace(replacement, expected=created.fingerprint)
    assert not (created.path.parent / "records").exists()


def test_invalid_event_is_rejected_before_canonical_write(tmp_path: Path) -> None:
    wire = event_wire(status="draft")
    wire["updated_at"] = "2026-08-26T11:00:00-04:00"
    candidate = parse_portia_record("event", "2", wire)
    with pytest.raises(WorkflowValidationError):
        EventWorkflowService(tmp_path).create(candidate)
    assert not (tmp_path / "classes").exists()


def test_exact_historical_load_does_not_follow_successor(tmp_path: Path) -> None:
    service = EventWorkflowService(tmp_path)
    service.create(event_record(status="superseded"))
    loaded = service.resolve_exact(event_ref())
    assert loaded.record.status == "superseded"


def test_quarantine_separates_write_and_current_use_from_exact_history(
    tmp_path: Path,
) -> None:
    blocked_write = EventWorkflowService(
        tmp_path,
        quarantine=_BlockingQuarantine("block_work_writes"),  # type: ignore[arg-type]
    )
    with pytest.raises(PortiaQuarantinedError):
        blocked_write.create(event_record(status="draft"))
    assert not (tmp_path / "classes/class_a/modules/portia/work/evt_alpha").exists()

    EventWorkflowService(tmp_path).create(event_record(status="draft"))
    blocked_current = EventWorkflowService(
        tmp_path,
        quarantine=_BlockingQuarantine("block_current_use"),  # type: ignore[arg-type]
    )
    assert blocked_current.load_exact(event_ref()).record.status == "draft"
    with pytest.raises(PortiaQuarantinedError):
        blocked_current.require_current_use(event_ref())


def test_standalone_active_event_is_zero_write(tmp_path: Path) -> None:
    with pytest.raises(WorkflowPrerequisiteError):
        EventWorkflowService(tmp_path).create(event_record())
    assert not (tmp_path / "classes").exists()


def test_event_activation_requires_active_participant(tmp_path: Path) -> None:
    service = EventWorkflowService(tmp_path)
    created = service.create(event_record(status="draft"))
    canonical = created.path.read_bytes()
    active = event_record(updated_at="2026-08-26T12:05:00-04:00")
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(active, expected=created.fingerprint)
    assert created.path.read_bytes() == canonical

    ParticipantWorkflowService(tmp_path).create(
        event_ref(),
        participant_record(
            subject={"kind": "unknown_person", "reason": "identity_not_known"}
        ),
    )
    replaced = service.replace(active, expected=created.fingerprint)
    assert replaced.record.status == "active"


def test_event_terminal_resurrection_and_creation_rewrite_are_zero_write(
    tmp_path: Path,
) -> None:
    service = EventWorkflowService(tmp_path)
    created = service.create(event_record(status="cancelled"))
    canonical = created.path.read_bytes()
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            event_record(
                status="draft", updated_at="2026-08-26T12:05:00-04:00"
            ),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical
    with pytest.raises(WorkflowPrerequisiteError):
        service.replace(
            event_record(
                status="cancelled",
                updated_at="2026-08-26T12:05:00-04:00",
                created_at="2026-08-26T12:00:01-04:00",
            ),
            expected=created.fingerprint,
        )
    assert created.path.read_bytes() == canonical
