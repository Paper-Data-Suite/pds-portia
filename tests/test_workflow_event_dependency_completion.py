from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.workflows import (
    DependencyWorkflowService,
    EventWorkflowService,
    ParticipantWorkflowService,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import AGENT, event_record, event_ref, participant_record

T0 = "2026-08-26T12:00:00-04:00"
T_ACTIVE = "2026-08-26T12:05:00-04:00"
T_DEPENDENCY = "2026-08-26T12:10:00-04:00"
T_TARGET_CHANGE = "2026-08-26T12:15:00-04:00"
T_CLOSE = "2026-08-26T12:20:00-04:00"
T_LATE_TARGET = "2026-08-26T12:25:00-04:00"


def _participant(
    participant_id: str,
    *,
    status: str = "active",
    updated_at: str = T0,
) -> PortiaRecord:
    return participant_record(
        participant_id=participant_id,
        status=status,
        subject={
            "kind": "descriptive_person",
            "description_type": "outside_student",
            "display_label": f"Synthetic {participant_id}",
        },
        created_at=T0,
        updated_at=updated_at,
    )


def _completion_dependency(
    *,
    dependency_id: str = "dep_event_completion",
    strength: str = "required",
    applies_to: str = "completion",
    target_id: str = "ep_beta",
) -> PortiaRecord:
    return parse_portia_record(
        "dependency",
        "1",
        {
            "schema_version": "1",
            "record_type": "dependency",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "dependency_id": dependency_id,
            "status": "active",
            "dependent": {
                "kind": "work",
                "work_kind": "event",
                "contract_version": "2",
            },
            "dependency": {
                "kind": "portia_record",
                "work_record_ref": {
                    "work_ref": event_ref().to_dict(),
                    "record_ref": {
                        "record_kind": "event_participant",
                        "record_id": target_id,
                        "contract_version": "3",
                    },
                },
            },
            "strength": strength,
            "applies_to": applies_to,
            "purpose": "workflow_prerequisite",
            "creation_source": {"type": "digital_entry"},
            "created_at": T_DEPENDENCY,
            "created_by": AGENT,
            "updated_at": T_DEPENDENCY,
            "updated_by": AGENT,
        },
    )


def _active_event(tmp_path: Path):
    events = EventWorkflowService(tmp_path)
    draft = events.create(event_record(status="draft", updated_at=T0))
    participants = ParticipantWorkflowService(tmp_path)
    participants.create(event_ref(), _participant("ep_alpha"))
    beta = participants.create(event_ref(), _participant("ep_beta"))
    active = events.replace(
        event_record(status="active", updated_at=T_ACTIVE),
        expected=draft.fingerprint,
    )
    return events, participants, active, beta


def _declare_dependency(tmp_path: Path, **changes: object) -> None:
    service = DependencyWorkflowService(tmp_path)
    service.create(event_ref(), _completion_dependency(**changes))


def _invalidate_beta(
    participants: ParticipantWorkflowService,
    beta,
) -> None:
    participants.replace(
        event_ref(),
        _participant(
            "ep_beta",
            status="invalidated",
            updated_at=T_TARGET_CHANGE,
        ),
        expected=beta.fingerprint,
    )


def test_required_satisfied_completion_dependency_allows_event_close(
    tmp_path: Path,
) -> None:
    events, _participants, active, _beta = _active_event(tmp_path)
    _declare_dependency(tmp_path)

    closed = events.replace(
        event_record(status="closed", updated_at=T_CLOSE),
        expected=active.fingerprint,
    )

    assert closed.record.status == "closed"


def test_required_unsatisfied_completion_dependency_blocks_event_close_zero_write(
    tmp_path: Path,
) -> None:
    events, participants, active, beta = _active_event(tmp_path)
    _declare_dependency(tmp_path)
    _invalidate_beta(participants, beta)

    with pytest.raises(WorkflowPrerequisiteError, match="completion gate"):
        events.replace(
            event_record(status="closed", updated_at=T_CLOSE),
            expected=active.fingerprint,
        )

    current = events.load_exact(event_ref())
    assert current.fingerprint == active.fingerprint
    assert current.record.status == "active"


def test_advisory_unsatisfied_completion_dependency_does_not_block_close(
    tmp_path: Path,
) -> None:
    events, participants, active, beta = _active_event(tmp_path)
    _declare_dependency(tmp_path, strength="advisory")
    _invalidate_beta(participants, beta)

    closed = events.replace(
        event_record(status="closed", updated_at=T_CLOSE),
        expected=active.fingerprint,
    )

    assert closed.record.status == "closed"


def test_required_current_use_dependency_does_not_become_completion_gate(
    tmp_path: Path,
) -> None:
    events, participants, active, beta = _active_event(tmp_path)
    _declare_dependency(tmp_path, applies_to="current_use")
    _invalidate_beta(participants, beta)

    closed = events.replace(
        event_record(status="closed", updated_at=T_CLOSE),
        expected=active.fingerprint,
    )

    assert closed.record.status == "closed"


def test_event_completion_gate_uses_candidate_update_time_for_temporal_state(
    tmp_path: Path,
) -> None:
    events, participants, active, beta = _active_event(tmp_path)
    _declare_dependency(tmp_path)
    later = participants.replace(
        event_ref(),
        _participant("ep_beta", updated_at=T_LATE_TARGET),
        expected=beta.fingerprint,
    )
    assert later.record.status == "active"

    with pytest.raises(WorkflowPrerequisiteError, match="completion gate"):
        events.replace(
            event_record(status="closed", updated_at=T_CLOSE),
            expected=active.fingerprint,
        )

    current = events.load_exact(event_ref())
    assert current.fingerprint == active.fingerprint
    assert current.record.status == "active"
