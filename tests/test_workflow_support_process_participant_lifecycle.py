from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)
from portia.workflows.action_common import action_reference
from portia.workflows.errors import WorkflowOwnershipError
from portia.workflows.support_process_participant_lifecycle import (
    build_participant_lifecycle_transition,
    require_coordinated_participant_transition,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
UPDATED = "2026-08-31T10:05:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice3_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record() -> PortiaRecord:
    return parse_portia_record(
        "support_process",
        "1",
        {
            "schema_version": "1",
            "record_type": "portia_work",
            "work_kind": "support_process",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "school_year": "2026-2027",
            "status": "proposed",
            "workflow_state": "planning",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def participant_record(
    *,
    status: str = "proposed",
    updated_at: str = TIMESTAMP,
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "participant_id": "spp_alpha",
            "status": status,
            "person": person
            or {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": "Synthetic learner",
            },
            "contexts": contexts or [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def create_proposed_participant(tmp_path: Path):
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(work_ref(), participant_record())
    return service, created


def active_candidate(**changes: object) -> PortiaRecord:
    wire = participant_record().to_dict()
    wire["status"] = "active"
    wire["updated_at"] = UPDATED
    wire.update(changes)
    return parse_portia_record("support_process_participant", "1", wire)


def test_action_reference_does_not_become_public_participant_builder() -> None:
    with pytest.raises(WorkflowOwnershipError):
        action_reference(work_ref(), "support_process_participant", "spp_alpha")


def test_build_activation_transition_targets_exact_participant() -> None:
    prior = participant_record()
    candidate = active_candidate()
    repository = Mock()
    repository.list_work_records.return_value = ()
    transition = build_participant_lifecycle_transition(
        repository,
        work_ref(),
        prior,
        candidate,
        transition_id="lct_spp_activate_001",
        reason_code="planning_confirmed",
    )
    assert transition.field("from_status") == "proposed"
    assert transition.field("to_status") == "active"
    target = transition.field("target")
    assert isinstance(target, Mapping)
    record_ref = target["record_ref"]
    assert isinstance(record_ref, Mapping)
    assert record_ref["record_id"] == "spp_alpha"


def test_ordinary_transition_cannot_rewrite_person() -> None:
    prior = participant_record()
    changed = active_candidate(
        person={
            "kind": "descriptive_person",
            "description_type": "outside_student",
            "display_label": "Different synthetic person",
        }
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot rewrite field person"):
        require_coordinated_participant_transition(prior, changed)


def test_ordinary_transition_cannot_rewrite_contexts() -> None:
    prior = participant_record()
    changed = active_candidate(contexts=[{"kind": "observer"}])
    with pytest.raises(
        WorkflowPrerequisiteError, match="cannot rewrite field contexts"
    ):
        require_coordinated_participant_transition(prior, changed)


def test_ordinary_transition_cannot_supersede() -> None:
    wire = participant_record().to_dict()
    wire["status"] = "superseded"
    wire["updated_at"] = UPDATED
    candidate = parse_portia_record("support_process_participant", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        require_coordinated_participant_transition(participant_record(), candidate)


def test_activation_persists_transition_and_canonical_replacement(
    tmp_path: Path,
) -> None:
    service, created = create_proposed_participant(tmp_path)
    reference = support_process_participant_reference(work_ref(), "spp_alpha")
    result = service.transition_lifecycle(
        reference,
        active_candidate(),
        expected=created.fingerprint,
        transition_id="lct_spp_activate_001",
        reason_code="planning_confirmed",
        operation_id="op_spp_activate_001",
    )
    assert result.accepted_steps == (
        "step_history",
        "step_transition",
        "step_action",
    )
    current = service.require_activation_eligibility(reference)
    assert current.participant.record.status == "active"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spp_activate_001",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_failed_unidentified_activation_writes_nothing(tmp_path: Path) -> None:
    unidentified = {
        "kind": "unidentified_person",
        "identity_status": "not_recorded",
    }
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(
        work_ref(), participant_record(person=unidentified)
    )
    reference = support_process_participant_reference(work_ref(), "spp_alpha")
    with pytest.raises(WorkflowPrerequisiteError, match="cannot be unidentified"):
        service.transition_lifecycle(
            reference,
            active_candidate(person=unidentified),
            expected=created.fingerprint,
            transition_id="lct_spp_rejected_001",
            reason_code="planning_confirmed",
            operation_id="op_spp_rejected_001",
        )
    assert service.load_exact(reference).record.status == "proposed"
    assert service.repository.list_work_records(
        work_ref(), "lifecycle_transition", version="1"
    ) == ()


def test_activation_effective_at_cannot_precede_creation(tmp_path: Path) -> None:
    service, created = create_proposed_participant(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede"):
        service.transition_lifecycle(
            support_process_participant_reference(work_ref(), "spp_alpha"),
            active_candidate(),
            expected=created.fingerprint,
            transition_id="lct_spp_bad_time_001",
            reason_code="planning_confirmed",
            effective_at="2026-08-31T09:59:00-04:00",
        )


def test_invalidation_uses_record_validity_reason(tmp_path: Path) -> None:
    service, created = create_proposed_participant(tmp_path)
    wire = participant_record().to_dict()
    wire["status"] = "invalidated"
    wire["updated_at"] = UPDATED
    candidate = parse_portia_record("support_process_participant", "1", wire)
    reference = support_process_participant_reference(work_ref(), "spp_alpha")
    service.transition_lifecycle(
        reference,
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spp_invalidate_001",
        reason_code="recording_error",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spp_invalidate_001",
    )
    assert transition.record.field("reason") == {
        "category": "record_validity",
        "code": "recording_error",
    }


def test_root_activation_preflight_accepts_transitioned_supported_person(
    tmp_path: Path,
) -> None:
    service, created = create_proposed_participant(tmp_path)
    reference = support_process_participant_reference(work_ref(), "spp_alpha")
    service.transition_lifecycle(
        reference,
        active_candidate(),
        expected=created.fingerprint,
        transition_id="lct_spp_activate_for_root",
        reason_code="planning_confirmed",
    )
    root = SupportProcessWorkflowService(tmp_path).require_activation_eligibility(
        work_ref()
    )
    assert root.record.status == "proposed"
