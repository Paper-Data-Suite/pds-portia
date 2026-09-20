"""Focused Issue #47 tests for version-explicit Event work-root lifecycle authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.repository import PortiaRepository
from portia.workflows import EventWorkflowService, ParticipantWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.event_lifecycle import (
    build_event_lifecycle_transition,
    build_event_migration_supersession_transition,
    event_lifecycle_state,
    require_event_lifecycle_reconciled,
)
from tests.workflow_helpers import (
    event_record,
    event_ref,
    event_wire,
    participant_record,
)

T0 = "2026-08-26T12:00:00-04:00"
T1 = "2026-08-26T12:05:00-04:00"
T2 = "2026-08-26T12:10:00-04:00"
T3 = "2026-08-26T12:15:00-04:00"


def _event_v1(*, status: str = "active", updated_at: str = T0) -> PortiaRecord:
    wire = event_wire(status=status, updated_at=updated_at)
    wire["schema_version"] = "1"
    return parse_portia_record("event", "1", wire)


def _revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    wire["updated_at"] = updated_at
    return parse_portia_record(prior.contract, prior.contract_version, wire)


def _active_participant() -> PortiaRecord:
    return participant_record(
        subject={"kind": "unknown_person", "reason": "identity_not_known"}
    )


def _activate_event(tmp_path: Path):
    events = EventWorkflowService(tmp_path)
    draft = events.create(event_record(status="draft", updated_at=T0))
    ParticipantWorkflowService(tmp_path).create(event_ref(), _active_participant())
    candidate = event_record(status="active", updated_at=T1)
    result = events.transition_lifecycle(
        event_ref(),
        candidate,
        expected=draft.fingerprint,
        transition_id="lct_evt_activate_001",
        reason_code="event_confirmed",
        operation_id="op_evt_activate_001",
    )
    return events, draft, candidate, result


def test_event_v2_builder_targets_exact_root_version(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    prior = event_record(status="draft", updated_at=T0)
    repository.create_work(work, prior)

    transition = build_event_lifecycle_transition(
        repository,
        work,
        prior,
        event_record(status="active", updated_at=T1),
        transition_id="lct_evt_activate_001",
        reason_code="event_confirmed",
    )

    assert transition.field("target") == {
        "kind": "work",
        "work_kind": "event",
        "contract_version": "2",
    }
    assert transition.field("previous_transition") is None
    assert transition.field("from_status") == "draft"
    assert transition.field("to_status") == "active"


def test_event_v1_migration_builder_is_version_pinned_and_migration_reasoned(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref(version="1")
    prior = _event_v1(status="active", updated_at=T0)
    repository.create_work(work, prior)
    candidate = _revision(prior, status="superseded", updated_at=T1)

    transition = build_event_migration_supersession_transition(
        repository,
        work,
        prior,
        candidate,
        transition_id="lct_evt_v1_migrated_001",
    )

    assert transition.field("target") == {
        "kind": "work",
        "work_kind": "event",
        "contract_version": "1",
    }
    assert transition.field("reason") == {
        "category": "migration",
        "code": "contract_migrated",
    }
    assert transition.field("to_status") == "superseded"


def test_ordinary_event_builder_never_promotes_event_v1_to_write_authority(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref(version="1")
    prior = _event_v1(status="active", updated_at=T0)
    repository.create_work(work, prior)

    with pytest.raises(WorkflowOwnershipError, match="event@2"):
        build_event_lifecycle_transition(
            repository,
            work,
            prior,
            _revision(prior, status="closed", updated_at=T1),
            transition_id="lct_evt_v1_ordinary_forbidden",
            reason_code="event_completed",
        )


def test_ordinary_event_builder_rejects_direct_supersession(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    prior = event_record(status="active", updated_at=T0)
    repository.create_work(work, prior)

    with pytest.raises(WorkflowPrerequisiteError, match="migration authority"):
        build_event_lifecycle_transition(
            repository,
            work,
            prior,
            event_record(status="superseded", updated_at=T1),
            transition_id="lct_evt_direct_supersede",
            reason_code="contract_migrated",
        )


def test_event_v1_history_reconciles_after_migration_retirement_evidence(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref(version="1")
    prior = _event_v1(status="active", updated_at=T0)
    created = repository.create_work(work, prior)
    candidate = _revision(prior, status="superseded", updated_at=T1)
    transition = build_event_migration_supersession_transition(
        repository,
        work,
        prior,
        candidate,
        transition_id="lct_evt_v1_migrated_001",
    )
    repository.create_work_record(work, transition)
    repository.replace_work(work, candidate, expected=created.fingerprint)

    state = require_event_lifecycle_reconciled(
        repository,
        work,
        repository.load_work(work).record,
    )
    assert state.selected_status == "superseded"
    assert state.head is not None
    assert state.head.record.logical_id == "lct_evt_v1_migrated_001"


def test_journaled_event_v2_activation_persists_history_transition_and_root(
    tmp_path: Path,
) -> None:
    events, _draft, _candidate, result = _activate_event(tmp_path)

    assert result.accepted_steps == (
        "step_history",
        "step_transition",
        "step_work",
    )
    current = events.load_exact(event_ref())
    assert current.record.status == "active"
    transition = events.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_evt_activate_001",
    )
    assert transition.record.field("from_status") == "draft"
    assert transition.record.field("to_status") == "active"
    assert require_event_lifecycle_reconciled(
        events.repository,
        event_ref(),
        current.record,
    ).head == transition


def test_event_v2_second_transition_names_exact_selected_predecessor(
    tmp_path: Path,
) -> None:
    events, _draft, _candidate, _result = _activate_event(tmp_path)
    active = events.load_exact(event_ref())
    closed_candidate = event_record(status="closed", updated_at=T2)

    events.transition_lifecycle(
        event_ref(),
        closed_candidate,
        expected=active.fingerprint,
        transition_id="lct_evt_close_001",
        reason_code="event_completed",
        operation_id="op_evt_close_001",
    )

    closed = events.load_exact(event_ref())
    assert closed.record.status == "closed"
    transition = events.repository.load_work_record(
        event_ref(),
        "lifecycle_transition",
        "1",
        "lct_evt_close_001",
    )
    assert transition.record.field("previous_transition") == {
        "record_kind": "lifecycle_transition",
        "record_id": "lct_evt_activate_001",
        "contract_version": "1",
    }
    assert require_event_lifecycle_reconciled(
        events.repository,
        event_ref(),
        closed.record,
    ).selected_status == "closed"


def test_completed_event_lifecycle_operation_replays_idempotently(
    tmp_path: Path,
) -> None:
    events, draft, candidate, first = _activate_event(tmp_path)

    replay = events.transition_lifecycle(
        event_ref(),
        candidate,
        expected=draft.fingerprint,
        transition_id="lct_evt_activate_001",
        reason_code="event_confirmed",
        operation_id="op_evt_activate_001",
    )

    assert replay.accepted_steps == first.accepted_steps
    assert events.load_exact(event_ref()).record.status == "active"


def test_event_lifecycle_effective_at_cannot_precede_selected_predecessor(
    tmp_path: Path,
) -> None:
    events, _draft, _candidate, _result = _activate_event(tmp_path)
    active = events.load_exact(event_ref())

    with pytest.raises(WorkflowPrerequisiteError, match="selected predecessor"):
        build_event_lifecycle_transition(
            events.repository,
            event_ref(),
            active.record,
            event_record(status="closed", updated_at=T2),
            transition_id="lct_evt_bad_chronology",
            reason_code="event_completed",
            effective_at=T0,
        )


def test_event_lifecycle_reader_fails_closed_on_legacy_status_divergence(
    tmp_path: Path,
) -> None:
    events, _draft, _candidate, _result = _activate_event(tmp_path)
    active = events.load_exact(event_ref())

    # Slice 24 intentionally leaves the Issue #40 replacement surface intact.
    # The new authority must nevertheless detect if that legacy surface changes
    # canonical status without appending lifecycle evidence.
    events.replace(
        event_record(status="invalidated", updated_at=T2),
        expected=active.fingerprint,
    )
    current = events.load_exact(event_ref())
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        require_event_lifecycle_reconciled(
            events.repository,
            event_ref(),
            current.record,
        )


def test_event_lifecycle_reader_rejects_forked_root_history(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    prior = event_record(status="draft", updated_at=T0)
    repository.create_work(work, prior)
    first = build_event_lifecycle_transition(
        repository,
        work,
        prior,
        event_record(status="active", updated_at=T1),
        transition_id="lct_evt_branch_a",
        reason_code="event_confirmed",
    )
    second_wire = first.to_dict()
    second_wire["transition_id"] = "lct_evt_branch_b"
    second_wire["to_status"] = "cancelled"
    second_wire["reason"] = {"category": "workflow", "code": "event_cancelled"}
    second = parse_portia_record("lifecycle_transition", "1", second_wire)
    repository.create_work_record(work, first)
    repository.create_work_record(work, second)

    with pytest.raises(WorkflowPrerequisiteError, match="exactly one root"):
        event_lifecycle_state(repository, work, prior)
