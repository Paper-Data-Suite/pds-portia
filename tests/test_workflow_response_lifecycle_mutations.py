"""Focused Slice 4b tests for Response lifecycle mutation and correction."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.paths import work_storage_history_path
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.response_lifecycle import (
    build_response_lifecycle_transition,
    require_coordinated_response_transition,
)
from portia.workflows.response_supersession import (
    require_exact_response_correction_predecessor,
    require_material_response_correction,
    require_response_supersession_effective,
    response_supersession_ancestry,
    response_supersession_records,
    superseded_response_predecessor,
)
from portia.workflows.responses import ResponseWorkflowService, response_reference
from tests.workflow_helpers import event_record

FIXTURES = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "response"
)


def _response(filename: str, *, section: str = "valid") -> PortiaRecord:
    value = json.loads((FIXTURES / section / filename).read_text(encoding="utf-8"))
    return parse_portia_record("response", "1", value)


def _work(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _revision(record: PortiaRecord, *, status: str) -> PortiaRecord:
    wire = record.to_dict()
    wire["status"] = status
    return parse_portia_record("response", "1", wire)


def _selected_predecessor(successor: PortiaRecord) -> ExactPortiaWorkRecordRef:
    values = successor.to_dict().get("supersedes")
    assert isinstance(values, list) and len(values) >= 1
    entry = values[0]
    assert isinstance(entry, dict)
    return ExactPortiaWorkRecordRef.from_dict(entry["work_record_ref"])


def _prior_for_successor(successor: PortiaRecord) -> PortiaRecord:
    predecessor = _selected_predecessor(successor)
    wire = successor.to_dict()
    wire["response_id"] = predecessor.record_ref.record_id
    wire["status"] = "active"
    wire.pop("supersedes", None)
    wire["started_at"] = "2026-08-10T09:14:00-04:00"
    wire["ended_at"] = "2026-08-10T09:15:00-04:00"
    return parse_portia_record("response", "1", wire)


def test_build_activation_transition_targets_exact_response() -> None:
    active = _response("event-classroom-management.json")
    prior = _revision(active, status="proposed")
    work = _work(prior)
    repository = Mock()
    repository.list_work_records.return_value = ()

    transition = build_response_lifecycle_transition(
        repository,
        work,
        prior,
        active,
        transition_id="lct_rsp_activate_001",
        reason_code="other",
        reason_detail="Synthetic activation for focused workflow acceptance.",
    )

    wire = transition.to_dict()
    assert wire["from_status"] == "proposed"
    assert wire["to_status"] == "active"
    assert wire["target"]["record_ref"]["record_id"] == active.logical_id
    assert wire["previous_transition"] is None


def test_build_invalidation_transition_is_record_validity() -> None:
    prior = _response("event-classroom-management.json")
    candidate = _revision(prior, status="invalidated")
    work = _work(prior)
    repository = Mock()
    repository.list_work_records.return_value = ()

    transition = build_response_lifecycle_transition(
        repository,
        work,
        prior,
        candidate,
        transition_id="lct_rsp_invalidate_001",
        reason_code="recording_error",
    )

    assert transition.field("reason") == {
        "category": "record_validity",
        "code": "recording_error",
    }


def test_ordinary_lifecycle_cannot_directly_supersede() -> None:
    prior = _response("event-classroom-management.json")
    candidate = _revision(prior, status="superseded")

    with pytest.raises(WorkflowPrerequisiteError, match="successor/correction"):
        require_coordinated_response_transition(prior, candidate)


def test_ordinary_lifecycle_cannot_rewrite_action_fact() -> None:
    prior = _response("event-classroom-management.json")
    wire = prior.to_dict()
    wire["status"] = "invalidated"
    action = dict(wire["action"])
    action["description"] = "Synthetic changed action that belongs in correction."
    wire["action"] = action
    candidate = parse_portia_record("response", "1", wire)

    with pytest.raises(WorkflowPrerequisiteError, match="cannot rewrite field action"):
        require_coordinated_response_transition(prior, candidate)


def test_lifecycle_other_reason_requires_detail() -> None:
    active = _response("event-classroom-management.json")
    prior = _revision(active, status="proposed")
    work = _work(prior)
    repository = Mock()
    repository.list_work_records.return_value = ()

    with pytest.raises(WorkflowPrerequisiteError, match="requires detail"):
        build_response_lifecycle_transition(
            repository,
            work,
            prior,
            active,
            transition_id="lct_rsp_activate_other",
            reason_code="other",
        )


def test_valid_timing_correction_names_exact_predecessor() -> None:
    successor = _response("successor-correction.json")
    work = _work(successor)
    predecessor = _selected_predecessor(successor)

    assert (
        require_exact_response_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        == "timing_corrected"
    )


def test_valid_timing_correction_requires_actual_timing_change() -> None:
    successor = _response("successor-correction.json")
    prior = _prior_for_successor(successor)

    require_material_response_correction(prior, successor, "timing_corrected")


def test_correction_reason_must_match_changed_fact() -> None:
    successor = _response("successor-correction.json")
    prior = _prior_for_successor(successor)

    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        require_material_response_correction(prior, successor, "provider_corrected")


def test_superseded_predecessor_changes_only_lifecycle_metadata() -> None:
    successor = _response("successor-correction.json")
    prior = _prior_for_successor(successor)

    changed = superseded_response_predecessor(prior, successor)

    assert changed.status == "superseded"
    assert changed.field("supersedes") is None
    for field in (
        "target",
        "provider",
        "action",
        "execution_state",
        "started_at",
        "ended_at",
        "review_ref",
        "determination_ref",
        "created_at",
        "created_by",
        "creation_source",
    ):
        assert changed.field(field) == prior.field(field)


@pytest.mark.parametrize(
    "filename",
    [
        "self-supersession.json",
        "duplicate-predecessor.json",
        "mixed-supersession-reasons.json",
        "ordinary-correction-cross-work.json",
        "work-root-reason-same-work.json",
        "work-root-correction-changes-id.json",
        "duplicate-consolidation-one-predecessor.json",
        "nonconsolidation-multiple-predecessors.json",
    ],
)
def test_frozen_invalid_supersession_topology_cannot_use_material_correct(
    filename: str,
) -> None:
    successor = _response(filename, section="application-invalid")
    work = _work(successor)
    predecessor = _selected_predecessor(successor)

    with pytest.raises(
        (WorkflowOwnershipError, WorkflowPrerequisiteError)
    ) as exc_info:
        require_exact_response_correction_predecessor(
            work,
            predecessor,
            successor,
        )
    assert exc_info.value is not None



@pytest.mark.parametrize(
    "filename",
    [
        "self-supersession.json",
        "duplicate-predecessor.json",
        "mixed-supersession-reasons.json",
        "ordinary-correction-cross-work.json",
        "work-root-reason-same-work.json",
        "work-root-correction-changes-id.json",
        "duplicate-consolidation-one-predecessor.json",
        "nonconsolidation-multiple-predecessors.json",
    ],
)
def test_frozen_invalid_topology_is_rejected_before_predecessor_io(
    filename: str,
) -> None:
    successor = _response(filename, section="application-invalid")
    repository = Mock()

    with pytest.raises((WorkflowOwnershipError, WorkflowPrerequisiteError)):
        response_supersession_records(repository, _work(successor), successor)

    repository.load_work_record.assert_not_called()


def test_contract_migration_keeps_frozen_self_identity_exception() -> None:
    base = _response("successor-correction.json")
    wire = base.to_dict()
    supersedes = wire["supersedes"]
    assert isinstance(supersedes, list) and len(supersedes) == 1
    entry = supersedes[0]
    assert isinstance(entry, dict)
    entry["reason"] = "contract_migrated"
    entry.pop("detail", None)
    composite = entry["work_record_ref"]
    assert isinstance(composite, dict)
    local = composite["record_ref"]
    assert isinstance(local, dict)
    local["record_id"] = wire["response_id"]
    successor = parse_portia_record("response", "1", wire)

    historical_wire = successor.to_dict()
    historical_wire.pop("supersedes", None)
    historical = parse_portia_record("response", "1", historical_wire)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=historical)

    resolved = response_supersession_records(
        repository,
        _work(successor),
        successor,
    )

    assert len(resolved) == 1
    assert resolved[0].stored.record.logical_id == successor.logical_id


def test_current_successor_requires_superseded_exact_predecessor() -> None:
    successor = _response("successor-correction.json")
    prior = _prior_for_successor(successor)
    work = _work(successor)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=prior)

    ancestry = response_supersession_ancestry(repository, work, successor)

    with pytest.raises(WorkflowPrerequisiteError, match="predecessor to be superseded"):
        require_response_supersession_effective(ancestry)


def test_superseded_exact_predecessor_makes_successor_effective() -> None:
    successor = _response("successor-correction.json")
    prior = _prior_for_successor(successor)
    superseded = superseded_response_predecessor(prior, successor)
    work = _work(successor)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=superseded)

    ancestry = response_supersession_ancestry(repository, work, successor)

    require_response_supersession_effective(ancestry)
    assert len(ancestry) == 1
    assert ancestry[0].stored.record.status == "superseded"


def test_public_transition_lifecycle_delegates_to_coordinator(tmp_path: Path) -> None:
    active = _response("event-classroom-management.json")
    prior = _revision(active, status="proposed")
    work = _work(prior)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(record=Mock())
    repository.load_work_record.return_value = SimpleNamespace(record=active)
    repository.list_work_records.return_value = ()
    service = ResponseWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    expected = ContentFingerprint(digest="0" * 64, byte_length=0)

    with (
        patch("portia.workflows.responses.ActionLifecycleCoordinator") as coordinator,
        patch("portia.workflows.responses.require_response_lifecycle_reconciled"),
    ):
        result = service.transition_lifecycle(
            response_reference(work, prior.logical_id or "missing"),
            active,
            expected=expected,
            transition_id="lct_rsp_public_activate",
            reason_code="other",
            reason_detail="Synthetic public lifecycle delegation.",
        )

    assert result is coordinator.return_value.commit.return_value
    coordinator.return_value.commit.assert_called_once()


def test_public_correct_delegates_exact_successor_intent(tmp_path: Path) -> None:
    successor = _response("successor-correction.json")
    predecessor = _selected_predecessor(successor)
    prior = _prior_for_successor(successor)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(record=Mock())
    repository.load_work_record.return_value = SimpleNamespace(record=prior)
    repository.list_work_records.return_value = ()
    service = ResponseWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    expected = ContentFingerprint(digest="1" * 64, byte_length=0)

    with (
        patch("portia.workflows.responses.ActionLifecycleCoordinator") as coordinator,
        patch("portia.workflows.responses.require_response_lifecycle_reconciled"),
    ):
        result = service.correct(
            predecessor,
            successor,
            expected=expected,
            transition_id="lct_rsp_public_correct",
        )

    assert result is coordinator.return_value.commit_correction.return_value
    call = coordinator.return_value.commit_correction.call_args
    assert call.args[:2] == (predecessor, successor)
    assert call.kwargs["supersession_reason"] == "timing_corrected"


def _matching_event(record: PortiaRecord) -> PortiaRecord:
    assert record.class_id is not None
    assert record.work_id is not None
    return event_record(
        class_id=record.class_id,
        event_id=record.work_id,
        status="active",
    )


def test_response_activation_persists_history_transition_and_replacement(
    tmp_path: Path,
) -> None:
    active = _response("event-classroom-management.json")
    proposed = _revision(active, status="proposed")
    work = _work(proposed)
    service = ResponseWorkflowService(tmp_path)
    service.repository.create_work(work, _matching_event(proposed))
    created = service.create(work, proposed)
    prior_bytes = created.path.read_bytes()
    wire = created.record.to_dict()
    wire["status"] = "active"
    wire["updated_at"] = "2026-08-10T09:18:00-04:00"
    candidate = parse_portia_record("response", "1", wire)

    result = service.transition_lifecycle(
        response_reference(work, str(proposed.logical_id)),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_response_activate_001",
        reason_code="review_completed",
        operation_id="op_response_activate_001",
    )

    assert result.accepted_steps == (
        "step_history",
        "step_transition",
        "step_action",
    )
    assert proposed.logical_id is not None
    history = work_storage_history_path(
        tmp_path,
        work,
        "response",
        proposed.logical_id,
        created.fingerprint.digest,
    )
    assert history.read_bytes() == prior_bytes
    current = service.require_current_use(
        response_reference(work, proposed.logical_id)
    )
    assert current.record.status == "active"
    transition = service.repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_response_activate_001",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_response_material_correction_is_coordinated_and_exact(
    tmp_path: Path,
) -> None:
    successor = _response("successor-correction.json")
    predecessor_record = _prior_for_successor(successor)
    work = _work(predecessor_record)
    service = ResponseWorkflowService(tmp_path)
    service.repository.create_work(work, _matching_event(predecessor_record))
    predecessor = service.create(work, predecessor_record)
    prior_bytes = predecessor.path.read_bytes()
    predecessor_ref = response_reference(
        work,
        str(predecessor_record.logical_id),
    )

    result = service.correct(
        predecessor_ref,
        successor,
        expected=predecessor.fingerprint,
        transition_id="lct_response_correct_001",
        operation_id="op_response_correct_001",
    )

    assert result.accepted_steps == (
        "step_history",
        "step_successor",
        "step_transition",
        "step_action",
    )
    historical = service.load_exact(predecessor_ref)
    assert historical.record.status == "superseded"
    assert historical.record.field("supersedes") is None
    assert predecessor_record.logical_id is not None
    history = work_storage_history_path(
        tmp_path,
        work,
        "response",
        predecessor_record.logical_id,
        predecessor.fingerprint.digest,
    )
    assert history.read_bytes() == prior_bytes
    assert successor.logical_id is not None
    current = service.require_current_use(
        response_reference(work, successor.logical_id)
    )
    assert current.record.logical_id == successor.logical_id
    transition = service.repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        "lct_response_correct_001",
    )
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason")["code"] == "timing_corrected"
