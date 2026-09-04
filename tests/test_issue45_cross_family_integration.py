"""Issue #45 cross-family exact-history and no-fabrication integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.quarantine import QuarantineGuard
from portia.workflows import (
    FidelityWorkflowService,
    ImplementationWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    fidelity_reference,
    implementation_reference,
    support_process_participant_reference,
    support_reference,
)

TIMESTAMP = "2026-09-02T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-09-02T10:05:00-04:00"
ROOT_UPDATED = "2026-09-02T10:10:00-04:00"
PLAN_CREATED = "2026-09-02T10:15:00-04:00"
IMPLEMENTATION_STARTED = "2026-09-02T10:30:00-04:00"
IMPLEMENTATION_ENDED = "2026-09-02T10:40:00-04:00"
IMPLEMENTATION_RECORDED = "2026-09-02T10:45:00-04:00"
EVALUATED = "2026-09-02T11:00:00-04:00"
FIDELITY_RECORDED = "2026-09-02T11:05:00-04:00"
PLAN_SUCCESSOR_AT = "2026-09-02T11:10:00-04:00"
IMPLEMENTATION_CORRECTED_AT = "2026-09-02T11:20:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue45_cross_family_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def _exact_ref(kind: str, record_id: str) -> dict[str, object]:
    return {
        "record_kind": kind,
        "record_id": record_id,
        "contract_version": "1",
    }


def _root_record(
    *, status: str = "proposed", updated_at: str = TIMESTAMP
) -> PortiaRecord:
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
            "summary": "Synthetic cross-family Support Process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic bounded support need.",
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _participant_record(
    participant_id: str,
    *,
    status: str = "proposed",
    context: str,
    display_label: str,
    updated_at: str = TIMESTAMP,
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
                "description_type": (
                    "school_staff"
                    if participant_id == "spp_evaluator"
                    else "outside_student"
                ),
                "display_label": display_label,
            },
            "contexts": [{"kind": context}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def _participant_target() -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": _exact_ref("support_process_participant", "spp_student"),
    }


def _need_record() -> PortiaRecord:
    return parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "need_id": "spn_alpha",
            "status": "active",
            "target": _participant_target(),
            "need_kind": "access",
            "description": "Synthetic cross-family access need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def _support_record(support_id: str = "spt_alpha") -> PortiaRecord:
    return parse_portia_record(
        "support",
        "1",
        {
            "schema_version": "1",
            "record_type": "support",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "support_id": support_id,
            "status": "active",
            "target": _participant_target(),
            "need_refs": [_exact_ref("support_need", "spn_alpha")],
            "strategy": {
                "kind": "access",
                "procedure": "Provide the original synthetic access condition.",
            },
            "provider_plan": {
                "kind": "no_assigned_provider",
                "reason": "access_condition",
            },
            "schedule": {
                "kind": "as_needed",
                "planned_duration": {"kind": "minutes", "minutes": 5},
            },
            "plan_state": "active",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def _implementation_record(implementation_id: str = "imp_alpha") -> PortiaRecord:
    return parse_portia_record(
        "implementation",
        "1",
        {
            "schema_version": "1",
            "record_type": "implementation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "implementation_id": implementation_id,
            "status": "active",
            "plan_ref": _exact_ref("support", "spt_alpha"),
            "actual_target": _participant_target(),
            "implementation_provider": {
                "kind": "no_human_provider",
                "reason": "environmental_condition",
            },
            "execution_state": "completed",
            "started_at": IMPLEMENTATION_STARTED,
            "ended_at": IMPLEMENTATION_ENDED,
            "summary": "Synthetic cross-family implementation.",
            "creation_source": {"type": "digital_entry"},
            "created_at": IMPLEMENTATION_RECORDED,
            "created_by": AGENT,
            "updated_at": IMPLEMENTATION_RECORDED,
            "updated_by": AGENT,
        },
    )


def _fidelity_record() -> PortiaRecord:
    return parse_portia_record(
        "fidelity",
        "1",
        {
            "schema_version": "1",
            "record_type": "fidelity",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "fidelity_id": "fid_alpha",
            "status": "active",
            "plan_ref": _exact_ref("support", "spt_alpha"),
            "evaluator_ref": _exact_ref(
                "support_process_participant", "spp_evaluator"
            ),
            "scope": {
                "kind": "one_implementation",
                "implementation_ref": _exact_ref("implementation", "imp_alpha"),
            },
            "result": "as_planned",
            "basis": {
                "kind": "implementation_records",
                "record_refs": [_exact_ref("implementation", "imp_alpha")],
            },
            "evaluated_at": EVALUATED,
            "summary": "Synthetic cross-family Fidelity judgment.",
            "creation_source": {"type": "digital_entry"},
            "created_at": FIDELITY_RECORDED,
            "created_by": AGENT,
            "updated_at": FIDELITY_RECORDED,
            "updated_by": AGENT,
        },
    )


def _activate_participant(
    tmp_path: Path,
    participant_id: str,
    *,
    context: str,
    display_label: str,
    suffix: str,
) -> None:
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        _participant_record(
            participant_id,
            context=context,
            display_label=display_label,
        ),
    )
    service.transition_lifecycle(
        support_process_participant_reference(work_ref(), participant_id),
        _participant_record(
            participant_id,
            status="active",
            context=context,
            display_label=display_label,
            updated_at=PARTICIPANT_UPDATED,
        ),
        expected=created.fingerprint,
        transition_id=f"lct_cross_{suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_cross_{suffix}",
    )


def _setup_authority(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(_root_record())
    _activate_participant(
        tmp_path,
        "spp_student",
        context="supported_person",
        display_label="Synthetic learner",
        suffix="student_active",
    )
    root_service.transition_lifecycle(
        work_ref(),
        _root_record(status="active", updated_at=ROOT_UPDATED),
        expected=root.fingerprint,
        transition_id="lct_cross_root_active",
        reason_code="planning_confirmed",
        operation_id="op_cross_root_active",
    )
    _activate_participant(
        tmp_path,
        "spp_evaluator",
        context="observer",
        display_label="Synthetic evaluator",
        suffix="evaluator_active",
    )
    SupportNeedWorkflowService(tmp_path).create(work_ref(), _need_record())


def _seed_plan_and_implementation(tmp_path: Path) -> tuple[object, object]:
    support = SupportWorkflowService(tmp_path).create(work_ref(), _support_record())
    implementation = ImplementationWorkflowService(tmp_path).create(
        work_ref(), _implementation_record()
    )
    return support, implementation


def _support_successor(
    prior: PortiaRecord,
    *,
    reason: str,
    adapted: bool,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["support_id"] = "spt_beta"
    if adapted:
        wire["schedule"] = {
            "kind": "recurring",
            "frequency": {
                "occurrences": 1,
                "interval_count": 1,
                "interval_unit": "day",
            },
            "planned_duration": {"kind": "minutes", "minutes": 10},
        }
    else:
        strategy = dict(wire["strategy"])
        strategy["procedure"] = "Provide the corrected synthetic access condition."
        wire["strategy"] = strategy
    wire["supersedes"] = [
        {
            "work_record_ref": support_reference(work_ref(), "spt_alpha").to_dict(),
            "reason": reason,
        }
    ]
    wire["created_at"] = PLAN_SUCCESSOR_AT
    wire["created_by"] = AGENT
    wire["updated_at"] = PLAN_SUCCESSOR_AT
    wire["updated_by"] = AGENT
    return parse_portia_record("support", "1", wire)


def _implementation_successor(prior: PortiaRecord) -> PortiaRecord:
    wire = prior.to_dict()
    wire["implementation_id"] = "imp_beta"
    wire["summary"] = "Corrected synthetic implementation summary."
    wire["supersedes"] = [
        {
            "work_record_ref": implementation_reference(
                work_ref(), "imp_alpha"
            ).to_dict(),
            "reason": "summary_corrected",
        }
    ]
    wire["created_at"] = IMPLEMENTATION_CORRECTED_AT
    wire["created_by"] = AGENT
    wire["updated_at"] = IMPLEMENTATION_CORRECTED_AT
    wire["updated_by"] = AGENT
    return parse_portia_record("implementation", "1", wire)


def test_support_adaptation_does_not_retarget_existing_implementation(
    tmp_path: Path,
) -> None:
    _setup_authority(tmp_path)
    support, implementation = _seed_plan_and_implementation(tmp_path)
    support_service = SupportWorkflowService(tmp_path)
    support_service.adapt(
        support_reference(work_ref(), "spt_alpha"),
        _support_successor(support.record, reason="plan_adapted", adapted=True),
        expected=support.fingerprint,
        transition_id="lct_cross_support_adapted",
        operation_id="op_cross_support_adapted",
    )

    exact = ImplementationWorkflowService(tmp_path).require_current_use(
        implementation_reference(work_ref(), "imp_alpha")
    )
    assert exact.record.field("plan_ref") == _exact_ref("support", "spt_alpha")
    assert support_service.load_exact(
        support_reference(work_ref(), "spt_alpha")
    ).record.status == "superseded"
    assert support_service.require_current_use(
        support_reference(work_ref(), "spt_beta")
    ).record.status == "active"
    assert exact.fingerprint == implementation.fingerprint


def test_support_correction_does_not_retarget_existing_implementation(
    tmp_path: Path,
) -> None:
    _setup_authority(tmp_path)
    support, implementation = _seed_plan_and_implementation(tmp_path)
    SupportWorkflowService(tmp_path).correct(
        support_reference(work_ref(), "spt_alpha"),
        _support_successor(
            support.record,
            reason="strategy_corrected",
            adapted=False,
        ),
        expected=support.fingerprint,
        transition_id="lct_cross_support_corrected",
        operation_id="op_cross_support_corrected",
    )

    exact = ImplementationWorkflowService(tmp_path).require_current_use(
        implementation_reference(work_ref(), "imp_alpha")
    )
    assert exact.record.field("plan_ref") == _exact_ref("support", "spt_alpha")
    assert exact.fingerprint == implementation.fingerprint


def test_implementation_correction_does_not_retarget_existing_fidelity(
    tmp_path: Path,
) -> None:
    _setup_authority(tmp_path)
    _support, implementation = _seed_plan_and_implementation(tmp_path)
    fidelity_service = FidelityWorkflowService(tmp_path)
    fidelity = fidelity_service.create(work_ref(), _fidelity_record())
    implementation_service = ImplementationWorkflowService(tmp_path)
    implementation_service.correct(
        implementation_reference(work_ref(), "imp_alpha"),
        _implementation_successor(implementation.record),
        expected=implementation.fingerprint,
        transition_id="lct_cross_implementation_corrected",
        operation_id="op_cross_implementation_corrected",
    )

    exact_fidelity = fidelity_service.require_current_use(
        fidelity_reference(work_ref(), "fid_alpha")
    )
    assert exact_fidelity.fingerprint == fidelity.fingerprint
    fidelity_wire = exact_fidelity.record.to_dict()
    assert fidelity_wire["scope"] == {
        "kind": "one_implementation",
        "implementation_ref": _exact_ref("implementation", "imp_alpha"),
    }
    assert fidelity_wire["basis"] == {
        "kind": "implementation_records",
        "record_refs": [_exact_ref("implementation", "imp_alpha")],
    }
    assert implementation_service.load_exact(
        implementation_reference(work_ref(), "imp_alpha")
    ).record.status == "superseded"
    assert implementation_service.require_current_use(
        implementation_reference(work_ref(), "imp_beta")
    ).record.status == "active"


class _RejectCurrentUse(QuarantineGuard):
    def require_allowed(self, target: object, action: str) -> None:
        if action == "block_current_use":
            raise RuntimeError("synthetic quarantine blocked cross-family current use")


def test_quarantine_blocks_cross_family_current_use_without_rewriting_history(
    tmp_path: Path,
) -> None:
    _setup_authority(tmp_path)
    _support, implementation = _seed_plan_and_implementation(tmp_path)
    fidelity = FidelityWorkflowService(tmp_path).create(work_ref(), _fidelity_record())
    quarantine = _RejectCurrentUse(tmp_path)

    with pytest.raises(RuntimeError, match="synthetic quarantine blocked"):
        ImplementationWorkflowService(
            tmp_path, quarantine=quarantine
        ).require_current_use(implementation_reference(work_ref(), "imp_alpha"))
    with pytest.raises(RuntimeError, match="synthetic quarantine blocked"):
        FidelityWorkflowService(
            tmp_path, quarantine=quarantine
        ).require_current_use(fidelity_reference(work_ref(), "fid_alpha"))

    assert ImplementationWorkflowService(tmp_path).load_exact(
        implementation_reference(work_ref(), "imp_alpha")
    ).fingerprint == implementation.fingerprint
    assert FidelityWorkflowService(tmp_path).load_exact(
        fidelity_reference(work_ref(), "fid_alpha")
    ).fingerprint == fidelity.fingerprint


def test_plan_and_implementation_successors_do_not_fabricate_downstream_records(
    tmp_path: Path,
) -> None:
    _setup_authority(tmp_path)
    support, implementation = _seed_plan_and_implementation(tmp_path)
    support_service = SupportWorkflowService(tmp_path)
    support_service.adapt(
        support_reference(work_ref(), "spt_alpha"),
        _support_successor(support.record, reason="plan_adapted", adapted=True),
        expected=support.fingerprint,
        transition_id="lct_cross_no_fabrication_plan",
        operation_id="op_cross_no_fabrication_plan",
    )
    ImplementationWorkflowService(tmp_path).correct(
        implementation_reference(work_ref(), "imp_alpha"),
        _implementation_successor(implementation.record),
        expected=implementation.fingerprint,
        transition_id="lct_cross_no_fabrication_implementation",
        operation_id="op_cross_no_fabrication_implementation",
    )

    repository = ImplementationWorkflowService(tmp_path).repository
    assert repository.list_work_records(work_ref(), "fidelity", version="1") == ()
    assert repository.list_work_records(work_ref(), "follow_up", version="1") == ()
    assert repository.list_work_records(work_ref(), "outcome", version="1") == ()
