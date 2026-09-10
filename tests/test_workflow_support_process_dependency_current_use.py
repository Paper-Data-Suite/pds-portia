"""Focused Issue #47 Slice 15 tests for Support Process current-use Dependency gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import StoredRecord
from portia.workflows import (
    DependencyWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
)

T0 = "2026-08-31T10:00:00-04:00"
T5 = "2026-08-31T10:05:00-04:00"
T6 = "2026-08-31T10:06:00-04:00"
T10 = "2026-08-31T10:10:00-04:00"
T15 = "2026-08-31T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue47_slice15_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record(*, status: str = "proposed", updated_at: str = T0) -> PortiaRecord:
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
            "status": status,
            "workflow_state": "planning",
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_record(
    participant_id: str,
    *,
    status: str = "proposed",
    updated_at: str = T0,
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
            "participant_id": participant_id,
            "status": status,
            "person": {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic learner {participant_id}",
            },
            "contexts": [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": T0,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def active_root_candidate() -> PortiaRecord:
    return root_record(status="active", updated_at=T10)


def dependency_record(
    *,
    dependency_id: str,
    target_id: str,
    strength: str = "required",
    applies_to: str = "current_use",
) -> PortiaRecord:
    return parse_portia_record(
        "dependency",
        "1",
        {
            "schema_version": "1",
            "record_type": "dependency",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "dependency_id": dependency_id,
            "status": "active",
            "dependent": {
                "kind": "work",
                "work_kind": "support_process",
                "contract_version": "1",
            },
            "dependency": {
                "kind": "portia_record",
                "work_record_ref": {
                    "work_ref": work_ref().to_dict(),
                    "record_ref": {
                        "record_kind": "support_process_participant",
                        "record_id": target_id,
                        "contract_version": "1",
                    },
                },
            },
            "strength": strength,
            "applies_to": applies_to,
            "purpose": "workflow_prerequisite",
            "creation_source": {"type": "digital_entry"},
            "created_at": T6,
            "created_by": AGENT,
            "updated_at": T6,
            "updated_by": AGENT,
        },
    )


def _activate_participant(
    service: SupportProcessParticipantWorkflowService,
    participant_id: str,
    *,
    updated_at: str = T5,
) -> None:
    reference = support_process_participant_reference(work_ref(), participant_id)
    prior = service.load_exact(reference)
    service.transition_lifecycle(
        reference,
        participant_record(participant_id, status="active", updated_at=updated_at),
        expected=prior.fingerprint,
        transition_id=f"lct_{participant_id}_active",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_active",
    )


def _invalidate_participant(
    service: SupportProcessParticipantWorkflowService,
    participant_id: str,
) -> None:
    reference = support_process_participant_reference(work_ref(), participant_id)
    prior = service.load_exact(reference)
    service.transition_lifecycle(
        reference,
        participant_record(participant_id, status="invalidated", updated_at=T15),
        expected=prior.fingerprint,
        transition_id=f"lct_{participant_id}_invalidated",
        reason_code="recording_error",
        operation_id=f"op_{participant_id}_invalidated",
    )


def _ready_root(
    tmp_path: Path,
    *,
    beta_active: bool,
) -> tuple[
    SupportProcessWorkflowService,
    SupportProcessParticipantWorkflowService,
    StoredRecord,
]:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(work_ref(), participant_record("spp_alpha"))
    _activate_participant(participant_service, "spp_alpha")
    participant_service.create(work_ref(), participant_record("spp_beta"))
    if beta_active:
        _activate_participant(participant_service, "spp_beta")
    return root_service, participant_service, root


def _declare(tmp_path: Path, record: PortiaRecord) -> None:
    DependencyWorkflowService(tmp_path).create(work_ref(), record)


def _activate_root(
    service: SupportProcessWorkflowService,
    root: StoredRecord,
    *,
    suffix: str,
) -> None:
    service.transition_lifecycle(
        work_ref(),
        active_root_candidate(),
        expected=root.fingerprint,
        transition_id=f"lct_root_{suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_root_{suffix}",
    )


def _transition_ids(service: SupportProcessWorkflowService) -> tuple[str, ...]:
    return tuple(
        identifier
        for stored in service.repository.list_work_records(
            work_ref(),
            "lifecycle_transition",
            version="1",
        )
        if isinstance((identifier := stored.record.logical_id), str)
    )


def test_required_satisfied_current_use_dependency_allows_current_use(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_root_current_use_satisfied",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="current_use_satisfied")

    current = root_service.require_current_use(work_ref())

    assert current.record.status == "active"


def test_required_review_current_use_dependency_blocks_without_lifecycle_mutation(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root = _ready_root(
        tmp_path,
        beta_active=False,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_root_current_use_review",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="current_use_review")
    before = _transition_ids(root_service)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="required Dependency current-use gate",
    ):
        root_service.require_current_use(work_ref())

    assert root_service.load_exact(work_ref()).record.status == "active"
    assert _transition_ids(root_service) == before


def test_required_unsatisfied_current_use_dependency_blocks_current_use(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_root_current_use_unsatisfied",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="current_use_unsatisfied")
    _invalidate_participant(participant_service, "spp_beta")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="required Dependency current-use gate",
    ):
        root_service.require_current_use(work_ref())

    assert root_service.load_exact(work_ref()).record.status == "active"


def test_advisory_unsatisfied_current_use_dependency_does_not_block(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_root_current_use_advisory",
            target_id="spp_beta",
            strength="advisory",
        ),
    )
    _activate_root(root_service, root, suffix="current_use_advisory")
    _invalidate_participant(participant_service, "spp_beta")

    assert root_service.require_current_use(work_ref()).record.status == "active"


def test_activation_only_dependency_is_not_a_current_use_blocker_after_target_loss(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_root_activation_only",
            target_id="spp_beta",
            applies_to="activation",
        ),
    )
    _activate_root(root_service, root, suffix="activation_only")
    _invalidate_participant(participant_service, "spp_beta")

    assert root_service.require_current_use(work_ref()).record.status == "active"
