"""Focused Slice 10 tests for Communication lifecycle and correction semantics."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint
from portia.workflows.communication_lifecycle import (
    build_communication_lifecycle_transition,
    require_coordinated_communication_transition,
)
from portia.workflows.communication_supersession import (
    communication_supersession_ancestry,
    communication_supersession_records,
    require_communication_supersession_effective,
    require_exact_communication_correction_predecessor,
    require_material_communication_correction,
    superseded_communication_predecessor,
)
from portia.workflows.communications import (
    CommunicationWorkflowService,
    communication_reference,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

FIXTURES = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "communication"
)


def _communication(filename: str, *, section: str = "valid") -> PortiaRecord:
    value = json.loads((FIXTURES / section / filename).read_text(encoding="utf-8"))
    return parse_portia_record("communication", "1", value)


def _work(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    assert record.work_kind in {"event", "support_process"}
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind=record.work_kind,
        contract_version="2" if record.work_kind == "event" else "1",
    )


def _revision(record: PortiaRecord, *, status: str) -> PortiaRecord:
    wire = record.to_dict()
    wire["status"] = status
    return parse_portia_record("communication", "1", wire)


def _selected_predecessor(successor: PortiaRecord) -> ExactPortiaWorkRecordRef:
    values = successor.to_dict().get("supersedes")
    assert isinstance(values, list) and values
    entry = values[0]
    assert isinstance(entry, dict)
    return ExactPortiaWorkRecordRef.from_dict(entry["work_record_ref"])


def _prior_for_successor(successor: PortiaRecord) -> PortiaRecord:
    predecessor = _selected_predecessor(successor)
    wire = successor.to_dict()
    wire["communication_id"] = predecessor.record_ref.record_id
    wire["status"] = "active"
    wire.pop("supersedes", None)
    wire["started_at"] = "2026-08-10T09:20:00-04:00"
    wire["ended_at"] = "2026-08-10T09:25:00-04:00"
    return parse_portia_record("communication", "1", wire)


def test_build_activation_transition_targets_exact_communication() -> None:
    active = _communication("student-in-person.json")
    prior = _revision(active, status="proposed")
    repository = Mock()
    repository.list_work_records.return_value = ()

    transition = build_communication_lifecycle_transition(
        repository,
        _work(prior),
        prior,
        active,
        transition_id="lct_comm_activate_001",
        reason_code="other",
        reason_detail="Synthetic activation for focused workflow acceptance.",
    )

    wire = transition.to_dict()
    assert wire["from_status"] == "proposed"
    assert wire["to_status"] == "active"
    assert wire["target"]["record_ref"]["record_id"] == active.logical_id
    assert wire["previous_transition"] is None


def test_build_invalidation_transition_is_record_validity() -> None:
    prior = _communication("student-in-person.json")
    candidate = _revision(prior, status="invalidated")
    repository = Mock()
    repository.list_work_records.return_value = ()

    transition = build_communication_lifecycle_transition(
        repository,
        _work(prior),
        prior,
        candidate,
        transition_id="lct_comm_invalidate_001",
        reason_code="recording_error",
    )

    assert transition.field("reason") == {
        "category": "record_validity",
        "code": "recording_error",
    }


def test_ordinary_lifecycle_cannot_directly_supersede() -> None:
    prior = _communication("student-in-person.json")
    candidate = _revision(prior, status="superseded")

    with pytest.raises(WorkflowPrerequisiteError, match="successor/correction"):
        require_coordinated_communication_transition(prior, candidate)


def test_ordinary_lifecycle_cannot_rewrite_summary() -> None:
    prior = _communication("student-in-person.json")
    wire = prior.to_dict()
    wire["status"] = "invalidated"
    wire["summary"] = "Synthetic changed summary that belongs in correction."
    candidate = parse_portia_record("communication", "1", wire)

    with pytest.raises(WorkflowPrerequisiteError, match="cannot rewrite field summary"):
        require_coordinated_communication_transition(prior, candidate)


def test_lifecycle_other_reason_requires_detail() -> None:
    active = _communication("student-in-person.json")
    prior = _revision(active, status="proposed")
    repository = Mock()
    repository.list_work_records.return_value = ()

    with pytest.raises(WorkflowPrerequisiteError, match="requires detail"):
        build_communication_lifecycle_transition(
            repository,
            _work(prior),
            prior,
            active,
            transition_id="lct_comm_activate_other",
            reason_code="other",
        )


def test_valid_timing_correction_names_exact_predecessor() -> None:
    successor = _communication("successor-correction.json")
    predecessor = _selected_predecessor(successor)

    assert (
        require_exact_communication_correction_predecessor(
            _work(successor),
            predecessor,
            successor,
        )
        == "timing_corrected"
    )


def test_valid_timing_correction_requires_actual_timing_change() -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)

    require_material_communication_correction(prior, successor, "timing_corrected")


def test_correction_reason_must_match_changed_fact() -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)

    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        require_material_communication_correction(
            prior,
            successor,
            "sender_corrected",
        )


def test_summary_correction_reason_matches_summary_change() -> None:
    prior = _communication("student-in-person.json")
    wire = prior.to_dict()
    wire["communication_id"] = "comm_summary_corrected_002"
    wire["summary"] = "Synthetic corrected bounded summary."
    wire["supersedes"] = [
        {
            "work_record_ref": communication_reference(
                _work(prior),
                prior.logical_id or "missing",
            ).to_dict(),
            "reason": "content_summary_corrected",
        }
    ]
    successor = parse_portia_record("communication", "1", wire)

    require_material_communication_correction(
        prior,
        successor,
        "content_summary_corrected",
    )


def test_superseded_predecessor_changes_only_lifecycle_metadata() -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)

    changed = superseded_communication_predecessor(prior, successor)

    assert changed.status == "superseded"
    assert changed.field("supersedes") is None
    for field in (
        "sender",
        "recipients",
        "method",
        "purpose",
        "act_state",
        "privacy_scope",
        "started_at",
        "ended_at",
        "summary",
        "attachments",
        "relations",
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
def test_frozen_invalid_topology_cannot_use_material_correct(filename: str) -> None:
    successor = _communication(filename, section="application-invalid")
    predecessor = _selected_predecessor(successor)

    with pytest.raises((WorkflowOwnershipError, WorkflowPrerequisiteError)):
        require_exact_communication_correction_predecessor(
            _work(successor),
            predecessor,
            successor,
        )


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
    successor = _communication(filename, section="application-invalid")
    repository = Mock()

    with pytest.raises((WorkflowOwnershipError, WorkflowPrerequisiteError)):
        communication_supersession_records(
            repository,
            _work(successor),
            successor,
        )

    repository.load_work_record.assert_not_called()


def test_contract_migration_keeps_frozen_self_identity_exception() -> None:
    base = _communication("successor-correction.json")
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
    local["record_id"] = wire["communication_id"]
    successor = parse_portia_record("communication", "1", wire)

    historical_wire = successor.to_dict()
    historical_wire.pop("supersedes", None)
    historical = parse_portia_record("communication", "1", historical_wire)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=historical)

    resolved = communication_supersession_records(
        repository,
        _work(successor),
        successor,
    )

    assert len(resolved) == 1
    assert resolved[0].stored.record.logical_id == successor.logical_id


def test_current_successor_requires_superseded_exact_predecessor() -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=prior)

    ancestry = communication_supersession_ancestry(
        repository,
        _work(successor),
        successor,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="predecessor to be superseded"):
        require_communication_supersession_effective(ancestry)


def test_superseded_exact_predecessor_makes_successor_effective() -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)
    superseded = superseded_communication_predecessor(prior, successor)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=superseded)

    ancestry = communication_supersession_ancestry(
        repository,
        _work(successor),
        successor,
    )

    require_communication_supersession_effective(ancestry)
    assert len(ancestry) == 1
    assert ancestry[0].stored.record.status == "superseded"


def test_public_transition_lifecycle_delegates_to_coordinator(tmp_path: Path) -> None:
    active = _communication("student-in-person.json")
    prior = _revision(active, status="proposed")
    work = _work(prior)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=active)
    repository.list_work_records.return_value = ()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    expected = ContentFingerprint(digest="0" * 64, byte_length=0)

    with (
        patch(
            "portia.workflows.communications.ActionLifecycleCoordinator"
        ) as coordinator,
        patch(
            "portia.workflows.communications.require_communication_lifecycle_reconciled"
        ),
    ):
        result = service.transition_lifecycle(
            communication_reference(work, prior.logical_id or "missing"),
            active,
            expected=expected,
            transition_id="lct_comm_public_activate",
            reason_code="other",
            reason_detail="Synthetic public lifecycle delegation.",
        )

    assert result is coordinator.return_value.commit.return_value
    coordinator.return_value.commit.assert_called_once()


def test_public_correct_delegates_exact_successor_intent(tmp_path: Path) -> None:
    successor = _communication("successor-correction.json")
    predecessor = _selected_predecessor(successor)
    prior = _prior_for_successor(successor)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=prior)
    repository.list_work_records.return_value = ()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )
    expected = ContentFingerprint(digest="1" * 64, byte_length=0)

    with (
        patch(
            "portia.workflows.communications.ActionLifecycleCoordinator"
        ) as coordinator,
        patch(
            "portia.workflows.communications.require_communication_lifecycle_reconciled"
        ),
    ):
        result = service.correct(
            predecessor,
            successor,
            expected=expected,
            transition_id="lct_comm_public_correct",
        )

    assert result is coordinator.return_value.commit_correction.return_value
    call = coordinator.return_value.commit_correction.call_args
    assert call.args[:2] == (predecessor, successor)
    assert call.kwargs["supersession_reason"] == "timing_corrected"


def _support_process_communication() -> PortiaRecord:
    return _communication(
        "support-process-owner-before-issue18.json",
        section="application-invalid",
    )


def _support_process_owner() -> SimpleNamespace:
    return SimpleNamespace(
        contract="support_process",
        contract_version="1",
        status="active",
    )


def _support_process_summary_correction(
    prior: PortiaRecord,
) -> PortiaRecord:
    work = _work(prior)
    wire = prior.to_dict()
    wire["communication_id"] = "comm_family_call_corrected_002"
    wire["summary"] = "Corrected synthetic Support Process Communication summary."
    wire["updated_at"] = "2026-08-10T09:40:00-04:00"
    wire["supersedes"] = [
        {
            "work_record_ref": communication_reference(
                work,
                prior.logical_id or "missing",
            ).to_dict(),
            "reason": "content_summary_corrected",
        }
    ]
    return parse_portia_record("communication", "1", wire)


def test_support_process_lifecycle_mutation_delegates_under_issue44(
    tmp_path: Path,
) -> None:
    prior = _support_process_communication()
    candidate = _revision(prior, status="invalidated")
    work = _work(prior)
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=candidate)
    repository.list_work_records.return_value = ()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with (
        patch(
            "portia.workflows.communications.ActionLifecycleCoordinator"
        ) as coordinator,
        patch(
            "portia.workflows.communications.require_communication_lifecycle_reconciled"
        ),
    ):
        result = service.transition_lifecycle(
            communication_reference(
                work,
                prior.logical_id or "missing",
            ),
            candidate,
            expected=ContentFingerprint(digest="2" * 64, byte_length=0),
            transition_id="lct_support_process_invalidate",
            reason_code="recording_error",
        )

    assert result is coordinator.return_value.commit.return_value
    coordinator.return_value.commit.assert_called_once()


def test_support_process_transition_candidate_uses_current_process_authority_once(
    tmp_path: Path,
) -> None:
    prior = _support_process_communication()
    candidate = _revision(prior, status="invalidated")
    work = _work(prior)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=_support_process_owner()
    )
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with patch(
        "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use"
    ) as require_support_process_current:
        service._require_transition_candidate(work, prior, candidate)

    require_support_process_current.assert_called_once_with(work)


def test_support_process_correction_delegates_under_issue44(
    tmp_path: Path,
) -> None:
    prior = _support_process_communication()
    successor = _support_process_summary_correction(prior)
    work = _work(prior)
    predecessor = communication_reference(
        work,
        prior.logical_id or "missing",
    )
    repository = Mock()
    repository.load_work_record.return_value = SimpleNamespace(record=prior)
    repository.list_work_records.return_value = ()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with (
        patch(
            "portia.workflows.communications.ActionLifecycleCoordinator"
        ) as coordinator,
        patch(
            "portia.workflows.communications.require_communication_lifecycle_reconciled"
        ),
    ):
        result = service.correct(
            predecessor,
            successor,
            expected=ContentFingerprint(digest="3" * 64, byte_length=0),
            transition_id="lct_support_process_correct",
        )

    assert result is coordinator.return_value.commit_correction.return_value
    call = coordinator.return_value.commit_correction.call_args
    assert call.args[:2] == (predecessor, successor)
    assert call.kwargs["supersession_reason"] == "content_summary_corrected"


def test_support_process_correction_candidate_uses_current_process_authority_once(
    tmp_path: Path,
) -> None:
    prior = _support_process_communication()
    successor = _support_process_summary_correction(prior)
    work = _work(prior)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=_support_process_owner()
    )
    repository.list_work_records.return_value = ()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    with (
        patch(
            "portia.workflows.support_processes.SupportProcessWorkflowService.require_current_use"
        ) as require_support_process_current,
        patch(
            "portia.workflows.communications.require_communication_lifecycle_reconciled"
        ),
    ):
        service._require_correction_successor(
            work,
            prior,
            successor,
            supersession_reason="content_summary_corrected",
        )

    require_support_process_current.assert_called_once_with(work)


def test_later_attempt_without_supersedes_is_not_a_correction() -> None:
    earlier = _communication("recipient-unavailable-phone.json")
    wire = earlier.to_dict()
    wire["communication_id"] = "comm_family_call_later_002"
    wire["act_state"] = "completed"
    wire["recipients"][0]["participation"] = "participated"
    wire["started_at"] = "2026-08-10T10:00:00-04:00"
    wire["ended_at"] = "2026-08-10T10:05:00-04:00"
    wire["created_at"] = "2026-08-10T10:06:00-04:00"
    wire["updated_at"] = "2026-08-10T10:06:00-04:00"
    later = parse_portia_record("communication", "1", wire)

    assert earlier.logical_id != later.logical_id
    assert earlier.field("supersedes") is None
    assert later.field("supersedes") is None
    assert earlier.field("act_state") == "recipient_unavailable"
    assert later.field("act_state") == "completed"


def test_two_separate_attempts_create_without_implicit_supersession(
    tmp_path: Path,
) -> None:
    first = _communication("student-in-person.json")
    wire = first.to_dict()
    wire["communication_id"] = "comm_student_in_person_002"
    wire["started_at"] = "2026-08-10T10:00:00-04:00"
    wire["ended_at"] = "2026-08-10T10:01:00-04:00"
    wire["created_at"] = "2026-08-10T10:02:00-04:00"
    wire["updated_at"] = "2026-08-10T10:02:00-04:00"
    second = parse_portia_record("communication", "1", wire)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="event",
            contract_version="2",
            status="active",
        )
    )
    repository.create_work_record.side_effect = (
        lambda _work_ref, record: SimpleNamespace(record=record)
    )
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    service.create(_work(first), first)
    service.create(_work(second), second)

    assert repository.create_work_record.call_count == 2
    assert first.logical_id != second.logical_id


def test_exact_predecessor_readback_does_not_follow_successor(tmp_path: Path) -> None:
    successor = _communication("successor-correction.json")
    prior = _prior_for_successor(successor)
    predecessor = _selected_predecessor(successor)
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(record=Mock())
    repository.load_work_record.return_value = SimpleNamespace(record=prior)
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=Mock(),
    )

    stored = service.load_exact(predecessor)

    assert stored.record is prior
    repository.load_work_record.assert_called_once_with(
        predecessor.work_ref,
        "communication",
        "1",
        predecessor.record_ref.record_id,
    )
