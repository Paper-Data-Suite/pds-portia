"""Issue #45 Slice 5A tests for Fidelity creation and exact authority."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.paths import work_storage_history_path
from portia.storage.quarantine import QuarantineGuard
from portia.workflows import (
    FidelityWorkflowService,
    ImplementationWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    fidelity_reference,
    support_process_participant_reference,
)

TIMESTAMP = "2026-09-02T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-09-02T10:05:00-04:00"
ROOT_UPDATED = "2026-09-02T10:10:00-04:00"
PLAN_CREATED = "2026-09-02T10:15:00-04:00"
IMPLEMENTATION_STARTED = "2026-09-02T10:30:00-04:00"
IMPLEMENTATION_ENDED = "2026-09-02T10:40:00-04:00"
IMPLEMENTATION_RECORDED = "2026-09-02T10:45:00-04:00"
EVALUATED = "2026-09-02T11:00:00-04:00"
RECORDED = "2026-09-02T11:05:00-04:00"
UPDATED = "2026-09-02T11:10:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue45_fidelity_test"}


def work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_alpha",
        work_kind="support_process",
        contract_version="1",
    )


def root_record(
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
            "summary": "Synthetic Fidelity test support process.",
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


def participant_record(
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
                "description_type": "school_staff"
                if participant_id == "spp_evaluator"
                else "outside_student",
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


def participant_target() -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": "spp_student",
            "contract_version": "1",
        },
    }


def need_record() -> PortiaRecord:
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
            "target": participant_target(),
            "need_kind": "access",
            "description": "Synthetic Fidelity test need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def support_record(support_id: str = "spt_alpha") -> PortiaRecord:
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
            "target": participant_target(),
            "need_refs": [
                {
                    "record_kind": "support_need",
                    "record_id": "spn_alpha",
                    "contract_version": "1",
                }
            ],
            "strategy": {
                "kind": "access",
                "procedure": f"Provide synthetic support {support_id}.",
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


def implementation_record(
    implementation_id: str = "imp_alpha",
    *,
    support_id: str = "spt_alpha",
) -> PortiaRecord:
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
            "plan_ref": {
                "record_kind": "support",
                "record_id": support_id,
                "contract_version": "1",
            },
            "actual_target": participant_target(),
            "implementation_provider": {
                "kind": "no_human_provider",
                "reason": "environmental_condition",
            },
            "execution_state": "completed",
            "started_at": IMPLEMENTATION_STARTED,
            "ended_at": IMPLEMENTATION_ENDED,
            "summary": "Synthetic implementation for Fidelity evaluation.",
            "creation_source": {"type": "digital_entry"},
            "created_at": IMPLEMENTATION_RECORDED,
            "created_by": AGENT,
            "updated_at": IMPLEMENTATION_RECORDED,
            "updated_by": AGENT,
        },
    )


def exact_ref(kind: str, record_id: str) -> dict[str, object]:
    return {
        "record_kind": kind,
        "record_id": record_id,
        "contract_version": "1",
    }


def fidelity_record(
    fidelity_id: str = "fid_alpha",
    *,
    plan_id: str = "spt_alpha",
    evaluator_id: str = "spp_evaluator",
    scope: dict[str, object] | None = None,
    basis: dict[str, object] | None = None,
    instrument_result: dict[str, object] | None = None,
    evaluated_at: str = EVALUATED,
    created_at: str = RECORDED,
    updated_at: str = UPDATED,
    status: str = "active",
    creation_source: dict[str, object] | None = None,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "fidelity",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "fidelity_id": fidelity_id,
        "status": status,
        "plan_ref": exact_ref("support", plan_id),
        "evaluator_ref": exact_ref("support_process_participant", evaluator_id),
        "scope": scope
        or {
            "kind": "one_implementation",
            "implementation_ref": exact_ref("implementation", "imp_alpha"),
        },
        "result": "as_planned",
        "basis": basis or {"kind": "direct_observation"},
        "evaluated_at": evaluated_at,
        "summary": "Synthetic Fidelity evaluation.",
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if instrument_result is not None:
        wire["instrument_result"] = instrument_result
    return parse_portia_record("fidelity", "1", wire)


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
        participant_record(
            participant_id,
            context=context,
            display_label=display_label,
        ),
    )
    service.transition_lifecycle(
        support_process_participant_reference(work_ref(), participant_id),
        participant_record(
            participant_id,
            status="active",
            context=context,
            display_label=display_label,
            updated_at=PARTICIPANT_UPDATED,
        ),
        expected=created.fingerprint,
        transition_id=f"lct_{suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_{suffix}",
    )


def setup_authority(tmp_path: Path, *, second_plan: bool = False) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    _activate_participant(
        tmp_path,
        "spp_student",
        context="supported_person",
        display_label="Synthetic learner",
        suffix="student_active",
    )
    root_service.transition_lifecycle(
        work_ref(),
        root_record(status="active", updated_at=ROOT_UPDATED),
        expected=root.fingerprint,
        transition_id="lct_root_active",
        reason_code="planning_confirmed",
        operation_id="op_root_active",
    )
    _activate_participant(
        tmp_path,
        "spp_evaluator",
        context="observer",
        display_label="Synthetic evaluator",
        suffix="evaluator_active",
    )
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportWorkflowService(tmp_path).create(work_ref(), support_record())
    if second_plan:
        SupportWorkflowService(tmp_path).create(work_ref(), support_record("spt_beta"))


def seed_implementation(
    tmp_path: Path,
    implementation_id: str = "imp_alpha",
    *,
    support_id: str = "spt_alpha",
) -> None:
    ImplementationWorkflowService(tmp_path).create(
        work_ref(),
        implementation_record(implementation_id, support_id=support_id),
    )


def test_reference_is_exact_support_process_local_fidelity() -> None:
    reference = fidelity_reference(work_ref(), "fid_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "fidelity"
    assert reference.record_ref.record_id == "fid_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_non_support_process_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        fidelity_reference(wrong, "fid_alpha")


def test_create_one_implementation_fidelity_and_load_exact(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())

    exact = fidelity_reference(work_ref(), "fid_alpha")
    assert service.load_exact(exact).record == created.record
    assert service.resolve_exact(exact).record == created.record
    assert service.list_fidelity_records(work_ref()) == (created,)


def test_create_implementation_set_with_exact_record_basis(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path, "imp_alpha")
    seed_implementation(tmp_path, "imp_beta")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_set",
            scope={
                "kind": "implementation_set",
                "implementation_refs": [
                    exact_ref("implementation", "imp_alpha"),
                    exact_ref("implementation", "imp_beta"),
                ],
            },
            basis={
                "kind": "implementation_records",
                "record_refs": [
                    exact_ref("implementation", "imp_alpha"),
                    exact_ref("implementation", "imp_beta"),
                ],
            },
        ),
    )
    assert created.record.logical_id == "fid_set"


def test_create_bounded_plan_interval_fidelity(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_interval",
            scope={
                "kind": "bounded_plan_interval",
                "started_at": IMPLEMENTATION_STARTED,
                "ended_at": IMPLEMENTATION_ENDED,
            },
            basis={"kind": "record_review"},
        ),
    )
    assert created.record.logical_id == "fid_interval"


def test_create_scored_instrument_preserves_source_scale(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    result = {
        "instrument_name": "Synthetic fidelity checklist",
        "instrument_version": "1",
        "scale_minimum": 0,
        "scale_maximum": 12,
        "value": 9,
        "scale_label": "Synthetic source-defined scale",
    }
    created = FidelityWorkflowService(tmp_path).create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_scored",
            basis={
                "kind": "checklist_or_instrument",
                "instrument_use": "scored",
            },
            instrument_result=result,
        ),
    )
    assert created.record.field("instrument_result") == result


def test_unresolved_plan_fails_closed(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="plan ref does not resolve in owning Support Process",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(), fidelity_record(plan_id="spt_missing")
        )


def test_unresolved_evaluator_fails_closed(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="evaluator Participant ref does not resolve in owning Support Process",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(), fidelity_record(evaluator_id="spp_missing")
        )


def test_unresolved_scope_implementation_fails_closed(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="scope Implementation ref does not resolve in owning Support Process",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(
                scope={
                    "kind": "one_implementation",
                    "implementation_ref": exact_ref("implementation", "imp_missing"),
                }
            ),
        )


def test_scope_implementation_requires_same_exact_plan(tmp_path: Path) -> None:
    setup_authority(tmp_path, second_plan=True)
    seed_implementation(tmp_path, support_id="spt_beta")
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="scope Implementation must reference the same exact plan",
    ):
        FidelityWorkflowService(tmp_path).create(work_ref(), fidelity_record())


def test_implementation_set_cannot_mix_exact_plans(tmp_path: Path) -> None:
    setup_authority(tmp_path, second_plan=True)
    seed_implementation(tmp_path, "imp_alpha", support_id="spt_alpha")
    seed_implementation(tmp_path, "imp_beta", support_id="spt_beta")
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="scope Implementation must reference the same exact plan",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(
                scope={
                    "kind": "implementation_set",
                    "implementation_refs": [
                        exact_ref("implementation", "imp_alpha"),
                        exact_ref("implementation", "imp_beta"),
                    ],
                }
            ),
        )


def test_unresolved_basis_record_fails_closed(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="basis record ref does not resolve in owning Support Process",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(
                basis={
                    "kind": "record_review",
                    "record_refs": [exact_ref("implementation", "imp_missing")],
                }
            ),
        )


def test_bounded_interval_rejects_reversed_chronology(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="bounded interval ended_at cannot precede started_at",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(
                scope={
                    "kind": "bounded_plan_interval",
                    "started_at": IMPLEMENTATION_ENDED,
                    "ended_at": IMPLEMENTATION_STARTED,
                }
            ),
        )


@pytest.mark.parametrize(
    ("minimum", "maximum", "value", "message"),
    [
        (10, 0, 5, "scale_minimum must be less than scale_maximum"),
        (0, 10, -1, "instrument value must fall within declared scale"),
        (0, 10, 11, "instrument value must fall within declared scale"),
    ],
)
def test_instrument_scale_validation(
    tmp_path: Path,
    minimum: int,
    maximum: int,
    value: int,
    message: str,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match=message):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(
                basis={
                    "kind": "checklist_or_instrument",
                    "instrument_use": "scored",
                },
                instrument_result={
                    "instrument_name": "Synthetic checklist",
                    "instrument_version": "1",
                    "scale_minimum": minimum,
                    "scale_maximum": maximum,
                    "value": value,
                },
            ),
        )


def test_fidelity_recording_chronology(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="created_at cannot precede evaluated_at",
    ):
        service.create(
            work_ref(),
            fidelity_record(created_at="2026-09-02T10:59:00-04:00"),
        )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="updated_at cannot precede created_at",
    ):
        service.create(
            work_ref(),
            fidelity_record(updated_at="2026-09-02T11:04:00-04:00"),
        )


@pytest.mark.parametrize(
    "creation_source",
    [
        {"type": "import", "source_label": "Synthetic historical import"},
        {
            "type": "paper_capture",
            "stage": "ingested",
            "route_id": "route_synthetic",
            "page_record_id": "page_synthetic",
        },
    ],
)
def test_active_paper_or_import_requires_review_history(
    tmp_path: Path,
    creation_source: dict[str, object],
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="paper/import activation requires accepted review history",
    ):
        FidelityWorkflowService(tmp_path).create(
            work_ref(),
            fidelity_record(creation_source=creation_source),
        )


# Slice 5B — Fidelity canonical lifecycle and current-use authority.
FIDELITY_LIFECYCLE_UPDATED = "2026-09-02T11:20:00-04:00"


def _fidelity_revision(
    prior: PortiaRecord,
    *,
    status: str | None = None,
    result: str | None = None,
    updated_at: str = FIDELITY_LIFECYCLE_UPDATED,
) -> PortiaRecord:
    wire = prior.to_dict()
    if status is not None:
        wire["status"] = status
    if result is not None:
        wire["result"] = result
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("fidelity", "1", wire)


def test_active_fidelity_qualifies_for_current_use(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    current = service.require_current_use(reference)
    resolved = service.resolve_current(reference)

    assert current.fingerprint == created.fingerprint
    assert resolved.fingerprint == created.fingerprint
    assert current.record.status == "active"
    assert current.record.field("result") == "as_planned"


def test_fidelity_lifecycle_invalidation_removes_current_use(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    service.transition_lifecycle(
        reference,
        _fidelity_revision(created.record, status="invalidated"),
        expected=created.fingerprint,
        transition_id="lct_fid_slice5b_invalidated",
        reason_code="recording_error",
        operation_id="op_fid_slice5b_invalidated",
    )

    exact = service.load_exact(reference)
    assert exact.record.status == "invalidated"
    assert exact.record.field("result") == "as_planned"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_fid_slice5b_invalidated",
    )
    assert transition.record.field("target") == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "fidelity",
            "record_id": "fid_alpha",
            "contract_version": "1",
        },
    }
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "invalidated"

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(reference)


def test_fidelity_lifecycle_change_cannot_rewrite_result(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Fidelity lifecycle replacement cannot rewrite field result",
    ):
        service.transition_lifecycle(
            reference,
            _fidelity_revision(
                created.record,
                status="invalidated",
                result="partially_as_planned",
            ),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5b_mixed_dimension",
            reason_code="recording_error",
            operation_id="op_fid_slice5b_mixed_dimension",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_fidelity_lifecycle_same_status_is_not_an_ordinary_revision(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Fidelity lifecycle coordination requires a status change",
    ):
        service.transition_lifecycle(
            reference,
            _fidelity_revision(created.record, status="active"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5b_same_status",
            reason_code="recording_error",
            operation_id="op_fid_slice5b_same_status",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_fidelity_lifecycle_supersession_is_reserved_for_correction(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        service.transition_lifecycle(
            reference,
            _fidelity_revision(created.record, status="superseded"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5b_superseded",
            reason_code="recording_error",
            operation_id="op_fid_slice5b_superseded",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_fidelity_lifecycle_effective_at_cannot_precede_creation(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="effective_at cannot precede Fidelity creation",
    ):
        service.transition_lifecycle(
            reference,
            _fidelity_revision(created.record, status="invalidated"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5b_bad_effective",
            reason_code="recording_error",
            effective_at="2026-09-02T11:04:00-04:00",
            operation_id="op_fid_slice5b_bad_effective",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_proposed_digital_fidelity_can_activate_through_coordinated_lifecycle(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    proposed = fidelity_record(status="proposed")
    stored = service.repository.create_work_record(work_ref(), proposed)
    reference = fidelity_reference(work_ref(), "fid_alpha")

    service.transition_lifecycle(
        reference,
        _fidelity_revision(stored.record, status="active"),
        expected=stored.fingerprint,
        transition_id="lct_fid_slice5b_active",
        reason_code="review_confirmed",
        operation_id="op_fid_slice5b_active",
    )

    current = service.require_current_use(reference)
    assert current.record.status == "active"


def test_current_fidelity_requires_current_evaluator_but_invalidation_uses_exact_history(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    reference = fidelity_reference(work_ref(), "fid_alpha")

    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    evaluator_ref = support_process_participant_reference(work_ref(), "spp_evaluator")
    evaluator = participant_service.load_exact(evaluator_ref)
    evaluator_wire = evaluator.record.to_dict()
    evaluator_wire["status"] = "invalidated"
    evaluator_wire["updated_at"] = "2026-09-02T11:15:00-04:00"
    evaluator_wire["updated_by"] = AGENT
    evaluator_candidate = parse_portia_record(
        "support_process_participant",
        "1",
        evaluator_wire,
    )
    participant_service.transition_lifecycle(
        evaluator_ref,
        evaluator_candidate,
        expected=evaluator.fingerprint,
        transition_id="lct_fid_slice5b_evaluator_invalidated",
        reason_code="recording_error",
        operation_id="op_fid_slice5b_evaluator_invalidated",
    )

    with pytest.raises(WorkflowPrerequisiteError):
        service.require_current_use(reference)

    service.transition_lifecycle(
        reference,
        _fidelity_revision(created.record, status="invalidated"),
        expected=created.fingerprint,
        transition_id="lct_fid_slice5b_after_evaluator",
        reason_code="recording_error",
        operation_id="op_fid_slice5b_after_evaluator",
    )
    assert service.load_exact(reference).record.status == "invalidated"


# Slice 5C — ordinary one-to-one Fidelity correction/supersession.
FIDELITY_CORRECTION_UPDATED = "2026-09-02T11:30:00-04:00"


def _fidelity_supersession_entry(
    reference: ExactPortiaWorkRecordRef,
    reason: str,
    *,
    detail: str | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "work_record_ref": reference.to_dict(),
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    return entry


def _fidelity_successor(
    prior: PortiaRecord,
    *,
    fidelity_id: str = "fid_beta",
    reason: str = "result_corrected",
    result: str | None = "partially_as_planned",
    summary: str | None = None,
    evaluated_at: str | None = None,
    predecessor_refs: list[ExactPortiaWorkRecordRef] | None = None,
    reasons: list[str] | None = None,
    detail: str | None = None,
    plan_id: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["fidelity_id"] = fidelity_id
    wire["status"] = "active"
    if result is not None:
        wire["result"] = result
    if summary is not None:
        wire["summary"] = summary
    if evaluated_at is not None:
        wire["evaluated_at"] = evaluated_at
    if plan_id is not None:
        wire["plan_ref"] = exact_ref("support", plan_id)
    wire["created_at"] = FIDELITY_CORRECTION_UPDATED
    wire["created_by"] = AGENT
    wire["updated_at"] = FIDELITY_CORRECTION_UPDATED
    wire["updated_by"] = AGENT
    references = predecessor_refs or [fidelity_reference(work_ref(), "fid_alpha")]
    selected_reasons = reasons or [reason] * len(references)
    wire["supersedes"] = [
        _fidelity_supersession_entry(
            reference,
            selected_reason,
            detail=detail if selected_reason == "other" else None,
        )
        for reference, selected_reason in zip(references, selected_reasons, strict=True)
    ]
    return parse_portia_record("fidelity", "1", wire)


def test_fidelity_result_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_successor(created.record)

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_slice5c_result",
        operation_id="op_fid_slice5c_result",
    )

    exact_old = service.resolve_exact(predecessor)
    exact_new = service.resolve_exact(fidelity_reference(work_ref(), "fid_beta"))
    assert exact_old.record.status == "superseded"
    assert exact_old.record.field("result") == "as_planned"
    assert exact_new.record.status == "active"
    assert exact_new.record.field("result") == "partially_as_planned"
    assert service.require_current_use(
        fidelity_reference(work_ref(), "fid_beta")
    ).record == exact_new.record

    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_fid_slice5c_result",
    )
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "result_corrected",
    }
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"


def test_fidelity_correction_preserves_predecessor_storage_history(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    service.correct(
        predecessor,
        _fidelity_successor(created.record),
        expected=created.fingerprint,
        transition_id="lct_fid_slice5c_history",
        operation_id="op_fid_slice5c_history",
    )

    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "fidelity",
        "fid_alpha",
        created.fingerprint.digest,
    )
    assert history.is_file()
    assert json.loads(history.read_text(encoding="utf-8"))["status"] == "active"


def test_fidelity_correction_reason_must_match_changed_fact(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected evaluation fact",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(created.record, reason="evaluator_corrected"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_reason_mismatch",
            operation_id="op_fid_slice5c_reason_mismatch",
        )

    assert service.load_exact(predecessor).fingerprint == created.fingerprint


def test_fidelity_evaluation_period_correction_accepts_evaluated_at_change(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_successor(
        created.record,
        reason="evaluation_period_corrected",
        result="as_planned",
        evaluated_at="2026-09-02T10:59:00-04:00",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_slice5c_period",
        operation_id="op_fid_slice5c_period",
    )
    assert service.require_current_use(
        fidelity_reference(work_ref(), "fid_beta")
    ).record.field("evaluated_at") == "2026-09-02T10:59:00-04:00"


def test_fidelity_other_correction_can_correct_summary(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_successor(
        created.record,
        reason="other",
        result="as_planned",
        summary="Corrected synthetic Fidelity summary.",
        detail="Synthetic summary recording correction.",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_slice5c_summary",
        operation_id="op_fid_slice5c_summary",
    )
    assert service.require_current_use(
        fidelity_reference(work_ref(), "fid_beta")
    ).record.field("summary") == "Corrected synthetic Fidelity summary."


def test_fidelity_self_supersession_is_rejected(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(WorkflowPrerequisiteError, match="Fidelity cannot supersede itself"):
        service.correct(
            predecessor,
            _fidelity_successor(created.record, fidelity_id="fid_alpha"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_self",
            operation_id="op_fid_slice5c_self",
        )


def test_ordinary_fidelity_correction_is_one_to_one(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Fidelity correction is one-to-one",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(
                created.record,
                predecessor_refs=[
                    predecessor,
                    fidelity_reference(work_ref(), "fid_other"),
                ],
            ),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_two",
            operation_id="op_fid_slice5c_two",
        )


def test_mixed_fidelity_supersession_reasons_are_rejected(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="mixed Fidelity supersession reasons",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(
                created.record,
                predecessor_refs=[
                    predecessor,
                    fidelity_reference(work_ref(), "fid_other"),
                ],
                reasons=["result_corrected", "scope_corrected"],
            ),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_mixed",
            operation_id="op_fid_slice5c_mixed",
        )


def test_duplicate_fidelity_consolidation_needs_two_predecessors(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two Fidelity predecessors",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(
                created.record,
                reason="duplicate_consolidated",
            ),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_duplicate",
            operation_id="op_fid_slice5c_duplicate",
        )


def test_ordinary_fidelity_correction_cannot_cross_support_process_roots(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_other",
        work_kind="support_process",
        contract_version="1",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Fidelity correction cannot cross Support Process roots",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(
                created.record,
                predecessor_refs=[fidelity_reference(other_work, "fid_alpha")],
            ),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_cross_root",
            operation_id="op_fid_slice5c_cross_root",
        )


def test_ordinary_fidelity_correction_cannot_rewrite_plan_ref(tmp_path: Path) -> None:
    setup_authority(tmp_path, second_plan=True)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Fidelity correction cannot rewrite plan_ref",
    ):
        service.correct(
            predecessor,
            _fidelity_successor(created.record, plan_id="spt_beta"),
            expected=created.fingerprint,
            transition_id="lct_fid_slice5c_plan",
            operation_id="op_fid_slice5c_plan",
        )


def test_current_fidelity_successor_requires_exact_predecessor_superseded(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    successor = _fidelity_successor(created.record)
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="exact predecessor superseded",
    ):
        service.require_current_use(fidelity_reference(work_ref(), "fid_beta"))


# Slice 5D1 — duplicate-consolidation topology/current-use semantics.


def _stored_fidelity_with_status(
    service: FidelityWorkflowService,
    fidelity_id: str,
    status: str,
) -> PortiaRecord:
    wire = fidelity_record(fidelity_id).to_dict()
    wire["status"] = status
    record = parse_portia_record("fidelity", "1", wire)
    return service.repository.create_work_record(work_ref(), record).record


def test_duplicate_fidelity_consolidation_current_use_accepts_all_superseded_predecessors(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = _stored_fidelity_with_status(service, "fid_alpha", "superseded")
    _stored_fidelity_with_status(service, "fid_other", "superseded")
    successor = _fidelity_successor(
        first,
        fidelity_id="fid_merge",
        reason="duplicate_consolidated",
        result="as_planned",
        predecessor_refs=[
            fidelity_reference(work_ref(), "fid_alpha"),
            fidelity_reference(work_ref(), "fid_other"),
        ],
    )
    service.repository.create_work_record(work_ref(), successor)

    current = service.require_current_use(fidelity_reference(work_ref(), "fid_merge"))

    assert current.record.logical_id == "fid_merge"
    assert service.resolve_exact(
        fidelity_reference(work_ref(), "fid_alpha")
    ).record.status == "superseded"
    assert service.resolve_exact(
        fidelity_reference(work_ref(), "fid_other")
    ).record.status == "superseded"


def test_duplicate_fidelity_consolidation_current_use_requires_every_predecessor_superseded(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = _stored_fidelity_with_status(service, "fid_alpha", "superseded")
    _stored_fidelity_with_status(service, "fid_other", "active")
    successor = _fidelity_successor(
        first,
        fidelity_id="fid_merge",
        reason="duplicate_consolidated",
        result="as_planned",
        predecessor_refs=[
            fidelity_reference(work_ref(), "fid_alpha"),
            fidelity_reference(work_ref(), "fid_other"),
        ],
    )
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="exact predecessor superseded",
    ):
        service.require_current_use(fidelity_reference(work_ref(), "fid_merge"))


def test_duplicate_fidelity_consolidation_cannot_cross_support_process_roots(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = _stored_fidelity_with_status(service, "fid_alpha", "superseded")
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_other",
        work_kind="support_process",
        contract_version="1",
    )
    successor = _fidelity_successor(
        first,
        fidelity_id="fid_merge",
        reason="duplicate_consolidated",
        result="as_planned",
        predecessor_refs=[
            fidelity_reference(work_ref(), "fid_alpha"),
            fidelity_reference(other_work, "fid_other"),
        ],
    )
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Fidelity duplicate consolidation cannot cross Support Process roots",
    ):
        service.require_current_use(fidelity_reference(work_ref(), "fid_merge"))


def test_duplicate_fidelity_consolidation_rejects_repeated_predecessor_identity(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = _stored_fidelity_with_status(service, "fid_alpha", "superseded")
    alpha = fidelity_reference(work_ref(), "fid_alpha")
    distinct = fidelity_reference(work_ref(), "fid_other")
    wire = _fidelity_successor(
        first,
        fidelity_id="fid_merge",
        reason="duplicate_consolidated",
        result="as_planned",
        predecessor_refs=[alpha, distinct],
    ).to_dict()
    supersedes = wire["supersedes"]
    assert isinstance(supersedes, list)
    assert isinstance(supersedes[1], dict)
    supersedes[1]["work_record_ref"] = alpha.to_dict()
    supersedes[1]["detail"] = "Distinct entry, same exact Fidelity predecessor."
    successor = parse_portia_record("fidelity", "1", wire)
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Fidelity supersession repeats a predecessor identity",
    ):
        service.require_current_use(fidelity_reference(work_ref(), "fid_merge"))


# Slice 5D2 — atomic duplicate-consolidation writer.


def _fidelity_consolidation_successor(
    prior: PortiaRecord,
    predecessor_ids: list[str],
) -> PortiaRecord:
    return _fidelity_successor(
        prior,
        fidelity_id="fid_merge",
        reason="duplicate_consolidated",
        result="as_planned",
        predecessor_refs=[
            fidelity_reference(work_ref(), fidelity_id)
            for fidelity_id in predecessor_ids
        ],
    )


def _fidelity_consolidation_transition_ids() -> dict[str, str]:
    return {
        "fid_alpha": "lct_fid_consolidate_alpha",
        "fid_other": "lct_fid_consolidate_other",
    }


class _RejectFidelityTransitionWrites(QuarantineGuard):
    def require_allowed(self, target: object, action: str) -> None:
        if action == "block_work_writes":
            raise RuntimeError("synthetic quarantine blocked Fidelity transition")


def test_duplicate_fidelity_consolidation_writer_supersedes_all_predecessors_atomically(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = service.create(work_ref(), fidelity_record())
    second = service.create(work_ref(), fidelity_record("fid_other"))
    successor = _fidelity_consolidation_successor(
        first.record,
        ["fid_alpha", "fid_other"],
    )

    result = service.consolidate_duplicates(
        work_ref(),
        successor,
        expected={
            "fid_alpha": first.fingerprint,
            "fid_other": second.fingerprint,
        },
        transition_ids=_fidelity_consolidation_transition_ids(),
        operation_id="op_fid_consolidate",
    )

    assert result.operation_id == "op_fid_consolidate"
    assert service.load_exact(
        fidelity_reference(work_ref(), "fid_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        fidelity_reference(work_ref(), "fid_other")
    ).record.status == "superseded"
    current = service.require_current_use(
        fidelity_reference(work_ref(), "fid_merge")
    )
    assert current.record == successor

    for predecessor_id, transition_id in (
        _fidelity_consolidation_transition_ids().items()
    ):
        transition = service.repository.load_work_record(
            work_ref(),
            "lifecycle_transition",
            "1",
            transition_id,
        )
        assert transition.record.field("target") == {
            "kind": "local_record",
            "record_ref": {
                "record_kind": "fidelity",
                "record_id": predecessor_id,
                "contract_version": "1",
            },
        }
        assert transition.record.field("reason") == {
            "category": "consolidation",
            "code": "duplicate_consolidated",
        }

    for predecessor_id, stored in (
        ("fid_alpha", first),
        ("fid_other", second),
    ):
        history = work_storage_history_path(
            tmp_path,
            work_ref(),
            "fidelity",
            predecessor_id,
            stored.fingerprint.digest,
        )
        assert history.exists()


def test_duplicate_fidelity_consolidation_stale_predecessor_rejects_zero_graph_writes(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = service.create(work_ref(), fidelity_record())
    second = service.create(work_ref(), fidelity_record("fid_other"))
    second_wire = second.record.to_dict()
    second_wire["summary"] = "Synthetic later canonical Fidelity edit."
    second_wire["updated_at"] = "2026-09-02T11:20:00-04:00"
    second_wire["updated_by"] = AGENT
    changed_second = parse_portia_record("fidelity", "1", second_wire)
    service.repository.replace_work_record(
        work_ref(),
        changed_second,
        expected=second.fingerprint,
    )
    successor = _fidelity_consolidation_successor(
        first.record,
        ["fid_alpha", "fid_other"],
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected predecessor action state does not match canonical bytes",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "fid_alpha": first.fingerprint,
                "fid_other": second.fingerprint,
            },
            transition_ids=_fidelity_consolidation_transition_ids(),
            operation_id="op_fid_consolidate_stale",
        )

    assert service.load_exact(
        fidelity_reference(work_ref(), "fid_alpha")
    ).record.status == "active"
    assert service.load_exact(
        fidelity_reference(work_ref(), "fid_other")
    ).record.status == "active"
    assert "fid_merge" not in {
        item.record.logical_id for item in service.list(work_ref())
    }
    transition_ids = {
        item.record.logical_id
        for item in service.repository.list_work_records(
            work_ref(),
            "lifecycle_transition",
            version="1",
        )
    }
    assert not set(_fidelity_consolidation_transition_ids().values()) & transition_ids


def test_duplicate_fidelity_consolidation_requires_unique_transition_ids(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = service.create(work_ref(), fidelity_record())
    second = service.create(work_ref(), fidelity_record("fid_other"))
    successor = _fidelity_consolidation_successor(
        first.record,
        ["fid_alpha", "fid_other"],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="lifecycle transition IDs must be unique",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "fid_alpha": first.fingerprint,
                "fid_other": second.fingerprint,
            },
            transition_ids={
                "fid_alpha": "lct_fid_duplicate",
                "fid_other": "lct_fid_duplicate",
            },
            operation_id="op_fid_duplicate_transition",
        )

    assert {item.record.status for item in service.list(work_ref())} == {"active"}
    assert "fid_merge" not in {
        item.record.logical_id for item in service.list(work_ref())
    }


def test_duplicate_fidelity_consolidation_checks_quarantine_before_graph_write(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    baseline = FidelityWorkflowService(tmp_path)
    first = baseline.create(work_ref(), fidelity_record())
    second = baseline.create(work_ref(), fidelity_record("fid_other"))
    guarded = FidelityWorkflowService(
        tmp_path,
        quarantine=_RejectFidelityTransitionWrites(tmp_path),
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic quarantine blocked Fidelity transition",
    ):
        guarded.consolidate_duplicates(
            work_ref(),
            _fidelity_consolidation_successor(
                first.record,
                ["fid_alpha", "fid_other"],
            ),
            expected={
                "fid_alpha": first.fingerprint,
                "fid_other": second.fingerprint,
            },
            transition_ids=_fidelity_consolidation_transition_ids(),
            operation_id="op_fid_consolidate_quarantine",
        )

    assert {item.record.status for item in baseline.list(work_ref())} == {"active"}
    assert "fid_merge" not in {
        item.record.logical_id for item in baseline.list(work_ref())
    }


def test_duplicate_fidelity_consolidation_completed_operation_replays_idempotently(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    first = service.create(work_ref(), fidelity_record())
    second = service.create(work_ref(), fidelity_record("fid_other"))
    successor = _fidelity_consolidation_successor(
        first.record,
        ["fid_alpha", "fid_other"],
    )
    kwargs = {
        "expected": {
            "fid_alpha": first.fingerprint,
            "fid_other": second.fingerprint,
        },
        "transition_ids": _fidelity_consolidation_transition_ids(),
        "operation_id": "op_fid_consolidate_replay",
    }

    first_result = service.consolidate_duplicates(
        work_ref(),
        successor,
        **kwargs,
    )
    replay = service.consolidate_duplicates(
        work_ref(),
        successor,
        **kwargs,
    )

    assert replay.operation_id == first_result.operation_id
    assert replay.accepted_steps == first_result.accepted_steps
    assert service.require_current_use(
        fidelity_reference(work_ref(), "fid_merge")
    ).record == successor


def test_duplicate_fidelity_consolidation_requires_one_exact_plan(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path, second_plan=True)
    seed_implementation(tmp_path, "imp_alpha", support_id="spt_alpha")
    seed_implementation(tmp_path, "imp_beta", support_id="spt_beta")
    service = FidelityWorkflowService(tmp_path)
    first = service.create(work_ref(), fidelity_record())
    second = service.create(
        work_ref(),
        fidelity_record(
            "fid_other",
            plan_id="spt_beta",
            scope={
                "kind": "one_implementation",
                "implementation_ref": exact_ref("implementation", "imp_beta"),
            },
        ),
    )
    successor = _fidelity_consolidation_successor(
        first.record,
        ["fid_alpha", "fid_other"],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires one exact Fidelity plan",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "fid_alpha": first.fingerprint,
                "fid_other": second.fingerprint,
            },
            transition_ids=_fidelity_consolidation_transition_ids(),
            operation_id="op_fid_consolidate_plan_mismatch",
        )

    assert {item.record.status for item in service.list(work_ref())} == {"active"}
    assert "fid_merge" not in {
        item.record.logical_id for item in service.list(work_ref())
    }


# Slice 5E — cross-root Fidelity ownership correction.

FIDELITY_WORK_ROOT_UPDATED = "2026-09-02T11:30:00-04:00"


def corrected_work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_b",
        work_id="sup_beta",
        work_kind="support_process",
        contract_version="1",
    )


def _retarget_record(
    record: PortiaRecord,
    work: ExactPortiaWorkRef,
) -> PortiaRecord:
    wire = record.to_dict()
    wire["class_id"] = work.class_id
    wire["work_id"] = work.work_id
    return parse_portia_record(record.contract, record.contract_version, wire)


def _activate_participant_for_work(
    tmp_path: Path,
    work: ExactPortiaWorkRef,
    participant_id: str,
    *,
    context: str,
    display_label: str,
    suffix: str,
) -> None:
    service = SupportProcessParticipantWorkflowService(tmp_path)
    proposed = _retarget_record(
        participant_record(
            participant_id,
            context=context,
            display_label=display_label,
        ),
        work,
    )
    active = _retarget_record(
        participant_record(
            participant_id,
            status="active",
            context=context,
            display_label=display_label,
            updated_at=PARTICIPANT_UPDATED,
        ),
        work,
    )
    created = service.create(work, proposed)
    service.transition_lifecycle(
        support_process_participant_reference(work, participant_id),
        active,
        expected=created.fingerprint,
        transition_id=f"lct_{suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_{suffix}",
    )


def _setup_authority_for_work(
    tmp_path: Path,
    work: ExactPortiaWorkRef,
    *,
    suffix: str,
) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(_retarget_record(root_record(), work))
    _activate_participant_for_work(
        tmp_path,
        work,
        "spp_student",
        context="supported_person",
        display_label="Synthetic learner in corrected root",
        suffix=f"{suffix}_student_active",
    )
    root_service.transition_lifecycle(
        work,
        _retarget_record(root_record(status="active", updated_at=ROOT_UPDATED), work),
        expected=root.fingerprint,
        transition_id=f"lct_{suffix}_root_active",
        reason_code="planning_confirmed",
        operation_id=f"op_{suffix}_root_active",
    )
    _activate_participant_for_work(
        tmp_path,
        work,
        "spp_evaluator",
        context="observer",
        display_label="Synthetic evaluator in corrected root",
        suffix=f"{suffix}_evaluator_active",
    )
    SupportNeedWorkflowService(tmp_path).create(
        work,
        _retarget_record(need_record(), work),
    )
    SupportWorkflowService(tmp_path).create(
        work,
        _retarget_record(support_record(), work),
    )
    ImplementationWorkflowService(tmp_path).create(
        work,
        _retarget_record(implementation_record(), work),
    )


def _fidelity_work_root_successor(
    prior: PortiaRecord,
    predecessor: ExactPortiaWorkRecordRef,
    destination_work: ExactPortiaWorkRef,
    *,
    summary: str | None = None,
    updated_at: str = FIDELITY_WORK_ROOT_UPDATED,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["class_id"] = destination_work.class_id
    wire["work_id"] = destination_work.work_id
    wire["status"] = "active"
    if summary is not None:
        wire["summary"] = summary
    wire["supersedes"] = [
        {
            "work_record_ref": predecessor.to_dict(),
            "reason": "work_root_corrected",
        }
    ]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("fidelity", "1", wire)


def test_fidelity_work_root_correction_crosses_class_and_preserves_exact_history(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_beta")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    )

    result = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_work_root_alpha",
        operation_id="op_fid_work_root_alpha",
    )

    assert result.operation_id == "op_fid_work_root_alpha"
    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        fidelity_reference(destination, "fid_alpha")
    )
    assert old_exact.record.status == "superseded"
    assert old_exact.record.class_id == "class_a"
    assert old_exact.record.work_id == "sup_alpha"
    assert current.record.status == "active"
    assert current.record.logical_id == "fid_alpha"
    assert current.record.class_id == "class_b"
    assert current.record.work_id == "sup_beta"
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "fidelity",
        "fid_alpha",
        created.fingerprint.digest,
    )
    assert history.is_file()


def test_fidelity_work_root_correction_rejects_evaluation_fact_rewrite(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_fact")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
        summary="Piggybacked synthetic Fidelity summary rewrite.",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction cannot rewrite Fidelity evaluation fact summary",
    ):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_work_root_fact",
            operation_id="op_fid_work_root_fact",
        )

    assert service.resolve_exact(predecessor).record.status == "active"
    assert service.list_fidelity_records(destination) == ()


def test_fidelity_work_root_correction_rejects_stale_predecessor_before_any_write(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_stale")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    )
    changed_wire = created.record.to_dict()
    changed_wire["summary"] = "Synthetic later source-root Fidelity edit."
    changed_wire["updated_at"] = "2026-09-02T11:20:00-04:00"
    changed_wire["updated_by"] = AGENT
    service.repository.replace_work_record(
        work_ref(),
        parse_portia_record("fidelity", "1", changed_wire),
        expected=created.fingerprint,
    )

    with pytest.raises(PortiaConflictError, match="expected predecessor action state"):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_work_root_stale",
            operation_id="op_fid_work_root_stale",
        )

    assert service.resolve_exact(predecessor).record.status == "active"
    assert service.list_fidelity_records(destination) == ()


def test_fidelity_work_root_correction_rejects_existing_destination_identity(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_existing")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    service.create(destination, _retarget_record(fidelity_record(), destination))
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    )

    with pytest.raises(
        PortiaConflictError,
        match="successor identity already exists in destination",
    ):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_work_root_existing",
            operation_id="op_fid_work_root_existing",
        )

    assert service.resolve_exact(predecessor).record.status == "active"


def test_fidelity_work_root_correction_completed_operation_replays_idempotently(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_replay")
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    )

    first = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_work_root_replay",
        operation_id="op_fid_work_root_replay",
    )
    replay = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_fid_work_root_replay",
        operation_id="op_fid_work_root_replay",
    )

    assert replay.operation_id == first.operation_id
    assert service.resolve_exact(predecessor).record.status == "superseded"
    assert (
        service.require_current_use(
            fidelity_reference(destination, "fid_alpha")
        ).record.to_dict()
        == successor.to_dict()
    )


def test_fidelity_work_root_correction_destination_quarantine_blocks_all_writes(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    destination = corrected_work_ref()
    _setup_authority_for_work(tmp_path, destination, suffix="fid_root_quarantine")
    baseline = FidelityWorkflowService(tmp_path)
    created = baseline.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    )
    guarded = FidelityWorkflowService(
        tmp_path,
        quarantine=_RejectFidelityTransitionWrites(tmp_path),
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic quarantine blocked Fidelity transition",
    ):
        guarded.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_work_root_quarantine",
            operation_id="op_fid_work_root_quarantine",
        )

    assert baseline.resolve_exact(predecessor).record.status == "active"
    assert baseline.list_fidelity_records(destination) == ()

# Slice 5F — frozen Issue #18 Fidelity runtime fixture parity.


def test_create_unscored_checklist_fidelity(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    created = FidelityWorkflowService(tmp_path).create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_unscored",
            basis={
                "kind": "checklist_or_instrument",
                "detail": "Synthetic unscored checklist.",
                "instrument_use": "unscored",
            },
        ),
    )

    assert created.record.field("basis")["instrument_use"] == "unscored"
    assert created.record.field("instrument_result") is None


def test_create_combined_scored_fidelity_basis(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path, "imp_alpha")
    seed_implementation(tmp_path, "imp_beta")
    instrument_result = {
        "instrument_name": "Synthetic Fidelity Checklist",
        "instrument_version": "1.0",
        "scale_minimum": 0,
        "scale_maximum": 5,
        "value": 3,
        "scale_label": "Synthetic source-defined scale",
    }
    created = FidelityWorkflowService(tmp_path).create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_combined",
            scope={
                "kind": "implementation_set",
                "implementation_refs": [
                    exact_ref("implementation", "imp_alpha"),
                    exact_ref("implementation", "imp_beta"),
                ],
            },
            basis={
                "kind": "combined",
                "detail": "Direct observation plus a source-defined instrument.",
                "record_refs": [exact_ref("implementation", "imp_alpha")],
                "instrument_use": "scored",
            },
            instrument_result=instrument_result,
        ),
    )

    assert created.record.field("basis")["kind"] == "combined"
    assert created.record.field("instrument_result") == instrument_result


def test_create_other_fidelity_basis_with_detail(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    created = FidelityWorkflowService(tmp_path).create(
        work_ref(),
        fidelity_record(
            fidelity_id="fid_other_basis",
            basis={
                "kind": "other",
                "detail": "Synthetic bounded other evaluation basis.",
            },
        ),
    )

    assert created.record.field("basis")["kind"] == "other"


def test_historical_proposed_import_fidelity_resolves_exactly_without_current_use(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    wire = fidelity_record(fidelity_id="fid_imported").to_dict()
    wire["status"] = "proposed"
    wire["creation_source"] = {
        "type": "import",
        "source_label": "Synthetic historical import",
    }
    historical = parse_portia_record("fidelity", "1", wire)
    stored = service.repository.create_work_record(work_ref(), historical)
    exact = fidelity_reference(work_ref(), "fid_imported")

    assert service.resolve_exact(exact).record == stored.record
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry materialization"):
        service.require_current_use(exact)


def test_fidelity_work_root_correction_requires_different_support_process_root(
    tmp_path: Path,
) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    successor = _fidelity_work_root_successor(
        created.record,
        predecessor,
        work_ref(),
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction requires a different Support Process root",
    ):
        service.correct_work_root(
            predecessor,
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_same_root_rejected",
            operation_id="op_fid_same_root_rejected",
        )


def test_fidelity_work_root_correction_preserves_fidelity_id(tmp_path: Path) -> None:
    setup_authority(tmp_path)
    seed_implementation(tmp_path)
    service = FidelityWorkflowService(tmp_path)
    created = service.create(work_ref(), fidelity_record())
    predecessor = fidelity_reference(work_ref(), "fid_alpha")
    destination = corrected_work_ref()
    wire = _fidelity_work_root_successor(
        created.record,
        predecessor,
        destination,
    ).to_dict()
    wire["fidelity_id"] = "fid_changed_id"
    successor = parse_portia_record("fidelity", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction must preserve Fidelity ID",
    ):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_fid_changed_id_rejected",
            operation_id="op_fid_changed_id_rejected",
        )

