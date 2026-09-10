"""Focused Issue #47 Slice 17 tests for Support Process Dependency write effects."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

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
T20 = "2026-08-31T10:20:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue47_slice17_test"}


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
) -> None:
    reference = support_process_participant_reference(work_ref(), participant_id)
    prior = service.load_exact(reference)
    service.transition_lifecycle(
        reference,
        participant_record(participant_id, status="active", updated_at=T5),
        expected=prior.fingerprint,
        transition_id=f"lct_{participant_id}_active_slice17",
        reason_code="planning_confirmed",
        operation_id=f"op_{participant_id}_active_slice17",
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
        transition_id=f"lct_{participant_id}_invalidated_slice17",
        reason_code="recording_error",
        operation_id=f"op_{participant_id}_invalidated_slice17",
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
        transition_id=f"lct_root_{suffix}_slice17",
        reason_code="planning_confirmed",
        operation_id=f"op_root_{suffix}_slice17",
    )


def _workflow_active_revision(prior: PortiaRecord) -> PortiaRecord:
    wire = prior.to_dict()
    wire["workflow_state"] = "active"
    wire["updated_at"] = T20
    wire["updated_by"] = AGENT
    return parse_portia_record("support_process", "1", wire)


def _advance_workflow_state(
    service: SupportProcessWorkflowService,
) -> StoredRecord:
    current = service.load_exact(work_ref())
    return service.transition_workflow_state(
        work_ref(),
        _workflow_active_revision(current.record),
        expected=current.fingerprint,
    )


def test_required_satisfied_current_use_dependency_allows_lifecycle_write(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_write_satisfied",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="write_satisfied")

    accepted = _advance_workflow_state(root_service)

    assert accepted.record.status == "active"
    assert accepted.record.field("workflow_state") == "active"


def test_required_review_dependency_flags_current_use_but_does_not_block_write(
    tmp_path: Path,
) -> None:
    root_service, _participant_service, root = _ready_root(
        tmp_path,
        beta_active=False,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_write_review",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="write_review")

    accepted = _advance_workflow_state(root_service)

    assert accepted.record.status == "active"
    assert accepted.record.field("workflow_state") == "active"
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="required Dependency current-use gate",
    ):
        root_service.require_current_use(work_ref())
    assert root_service.load_exact(work_ref()).record.status == "active"


def test_required_indeterminate_current_use_dependency_does_not_block_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root_service, _participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _activate_root(root_service, root, suffix="write_indeterminate")

    condition = SimpleNamespace(
        reference=SimpleNamespace(
            record_ref=SimpleNamespace(record_id="dep_write_indeterminate")
        ),
        strength="required",
        condition="indeterminate",
    )
    gate = SimpleNamespace(
        conditions=(condition,),
        required_gate_satisfied=False,
        required_blockers=("dep_write_indeterminate",),
    )

    def fake_evaluate_gate(
        _service: DependencyWorkflowService,
        _dependent: object,
        *,
        gate: str,
        evaluated_at: str | None = None,
    ) -> object:
        assert gate == "current_use"
        assert evaluated_at is None
        return gate_result

    gate_result = gate
    monkeypatch.setattr(DependencyWorkflowService, "evaluate_gate", fake_evaluate_gate)

    accepted = _advance_workflow_state(root_service)

    assert accepted.record.field("workflow_state") == "active"


def test_required_unsatisfied_current_use_dependency_blocks_lifecycle_write(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_write_unsatisfied",
            target_id="spp_beta",
        ),
    )
    _activate_root(root_service, root, suffix="write_unsatisfied")
    _invalidate_participant(participant_service, "spp_beta")
    before = root_service.load_exact(work_ref())

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Dependency current-use lifecycle-write gate",
    ):
        _advance_workflow_state(root_service)

    after = root_service.load_exact(work_ref())
    assert after.fingerprint == before.fingerprint
    assert after.record.status == "active"
    assert after.record.field("workflow_state") == "planning"


def test_advisory_unsatisfied_current_use_dependency_does_not_block_write(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_write_advisory",
            target_id="spp_beta",
            strength="advisory",
        ),
    )
    _activate_root(root_service, root, suffix="write_advisory")
    _invalidate_participant(participant_service, "spp_beta")

    accepted = _advance_workflow_state(root_service)

    assert accepted.record.field("workflow_state") == "active"


def test_activation_only_dependency_loss_does_not_block_current_use_write_gate(
    tmp_path: Path,
) -> None:
    root_service, participant_service, root = _ready_root(
        tmp_path,
        beta_active=True,
    )
    _declare(
        tmp_path,
        dependency_record(
            dependency_id="dep_write_activation_only",
            target_id="spp_beta",
            applies_to="activation",
        ),
    )
    _activate_root(root_service, root, suffix="write_activation_only")
    _invalidate_participant(participant_service, "spp_beta")

    accepted = _advance_workflow_state(root_service)

    assert accepted.record.field("workflow_state") == "active"
