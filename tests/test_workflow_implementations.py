"""Issue #45 tests through Slice 2 for Implementation occurrence workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.paths import work_storage_history_path
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import StoredRecord
from portia.workflows import (
    ImplementationWorkflowService,
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    implementation_reference,
    support_process_participant_reference,
)
from portia.workflows.implementations import _require_unique_logical_people

TIMESTAMP = "2026-09-02T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-09-02T10:05:00-04:00"
ROOT_UPDATED = "2026-09-02T10:10:00-04:00"
PLAN_CREATED = "2026-09-02T10:15:00-04:00"
STARTED = "2026-09-02T10:30:00-04:00"
ENDED = "2026-09-02T10:40:00-04:00"
RECORDED = "2026-09-02T10:45:00-04:00"
TRANSITIONED = "2026-09-02T10:55:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue45_slice1_test"}


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
            "summary": "Synthetic bounded support process.",
            "initiation": {
                "kind": "teacher_identified_need",
                "detail": "Synthetic planning need.",
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
    contexts: list[dict[str, object]],
    display_label: str,
    description_type: str = "school_staff",
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
                "description_type": description_type,
                "display_label": display_label,
            },
            "contexts": contexts,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_target(participant_id: str = "spp_student") -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def participant_provider(participant_id: str = "spp_provider") -> dict[str, object]:
    return {
        "kind": "participants",
        "participant_refs": [
            {
                "record_kind": "support_process_participant",
                "record_id": participant_id,
                "contract_version": "1",
            }
        ],
    }


def assigned_provider(participant_id: str = "spp_provider") -> dict[str, object]:
    return {
        "kind": "assigned",
        "participant_refs": [
            {
                "record_kind": "support_process_participant",
                "record_id": participant_id,
                "contract_version": "1",
            }
        ],
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
            "description": "Synthetic bounded access need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def goal_record() -> PortiaRecord:
    return parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "goal_id": "spg_alpha",
            "status": "active",
            "target": participant_target(),
            "description": "Synthetic bounded future support objective.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def support_record() -> PortiaRecord:
    return parse_portia_record(
        "support",
        "1",
        {
            "schema_version": "1",
            "record_type": "support",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "support_id": "spt_alpha",
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
                "procedure": "Provide the synthetic classroom access condition.",
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


def intervention_record() -> PortiaRecord:
    return parse_portia_record(
        "intervention",
        "1",
        {
            "schema_version": "1",
            "record_type": "intervention",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "intervention_id": "int_alpha",
            "status": "active",
            "target": participant_target(),
            "need_refs": [
                {
                    "record_kind": "support_need",
                    "record_id": "spn_alpha",
                    "contract_version": "1",
                }
            ],
            "goal_refs": [
                {
                    "record_kind": "support_goal",
                    "record_id": "spg_alpha",
                    "contract_version": "1",
                }
            ],
            "strategy": {
                "kind": "skill_building",
                "procedure": "Use the synthetic structured intervention routine.",
            },
            "provider_plan": assigned_provider(),
            "schedule": {
                "kind": "recurring",
                "frequency": {
                    "occurrences": 1,
                    "interval_count": 1,
                    "interval_unit": "week",
                },
                "selected_days": ["monday"],
                "planned_duration": {"kind": "minutes", "minutes": 10},
            },
            "monitoring_approach": "Review the synthetic occurrence record.",
            "plan_state": "active",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def implementation_record(
    *,
    implementation_id: str = "imp_alpha",
    plan_kind: str = "intervention",
    plan_id: str = "int_alpha",
    actual_target: dict[str, object] | None = None,
    provider: dict[str, object] | None = None,
    execution_state: str = "completed",
    started_at: str = STARTED,
    ended_at: str | None = ENDED,
    created_at: str = RECORDED,
    updated_at: str = RECORDED,
    variation: dict[str, object] | None = None,
    summary: str = "Synthetic documented implementation occurrence.",
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "implementation",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "implementation_id": implementation_id,
        "status": "active",
        "plan_ref": {
            "record_kind": plan_kind,
            "record_id": plan_id,
            "contract_version": "1",
        },
        "actual_target": actual_target or participant_target(),
        "implementation_provider": provider or participant_provider(),
        "execution_state": execution_state,
        "started_at": started_at,
        "summary": summary,
        "creation_source": {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if ended_at is not None:
        wire["ended_at"] = ended_at
    if variation is not None:
        wire["variation"] = variation
    return parse_portia_record("implementation", "1", wire)


def _activate_participant(
    tmp_path: Path,
    participant_id: str,
    *,
    contexts: list[dict[str, object]],
    display_label: str,
    transition_suffix: str,
    description_type: str = "school_staff",
) -> None:
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        participant_record(
            participant_id,
            contexts=contexts,
            display_label=display_label,
            description_type=description_type,
        ),
    )
    service.transition_lifecycle(
        support_process_participant_reference(work_ref(), participant_id),
        participant_record(
            participant_id,
            status="active",
            contexts=contexts,
            display_label=display_label,
            description_type=description_type,
            updated_at=PARTICIPANT_UPDATED,
        ),
        expected=created.fingerprint,
        transition_id=f"lct_{transition_suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_{transition_suffix}",
    )


def _setup_active_plans(tmp_path: Path, *, collaborator: bool = False) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    _activate_participant(
        tmp_path,
        "spp_student",
        contexts=[{"kind": "supported_person"}],
        display_label="Synthetic learner",
        transition_suffix="student_active",
        description_type="outside_student",
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
        "spp_provider",
        contexts=[{"kind": "provider_or_collaborator"}],
        display_label="Synthetic provider",
        transition_suffix="provider_active",
    )
    if collaborator:
        _activate_participant(
            tmp_path,
            "spp_collaborator",
            contexts=[{"kind": "provider_or_collaborator"}],
            display_label="Synthetic collaborator",
            transition_suffix="collaborator_active",
        )
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    SupportWorkflowService(tmp_path).create(work_ref(), support_record())
    InterventionWorkflowService(tmp_path).create(work_ref(), intervention_record())


def test_reference_is_exact_support_process_local_implementation() -> None:
    reference = implementation_reference(work_ref(), "imp_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "implementation"
    assert reference.record_ref.record_id == "imp_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_event_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        implementation_reference(wrong, "imp_alpha")


def test_create_intervention_occurrence_and_load_exact(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())

    exact = implementation_reference(work_ref(), "imp_alpha")
    assert service.load_exact(exact).record == created.record
    assert service.resolve_exact(exact).record == created.record
    assert service.list_implementations(work_ref()) == (created,)


def test_create_support_occurrence_with_no_human_provider(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            plan_kind="support",
            plan_id="spt_alpha",
            provider={
                "kind": "no_human_provider",
                "reason": "environmental_condition",
            },
        ),
    )
    assert created.record.field("plan_ref") == {
        "record_kind": "support",
        "record_id": "spt_alpha",
        "contract_version": "1",
    }


def test_repeated_occurrences_are_distinct_records(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(
        work_ref(), implementation_record(implementation_id="imp_first")
    )
    second = service.create(
        work_ref(), implementation_record(implementation_id="imp_second")
    )
    assert first.record.logical_id == "imp_first"
    assert second.record.logical_id == "imp_second"
    assert {item.record.logical_id for item in service.list(work_ref())} == {
        "imp_first",
        "imp_second",
    }


def test_unresolved_plan_fails_closed(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="plan ref does not resolve in owning Support Process",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(plan_id="int_missing"),
        )


def test_unresolved_actual_target_fails_closed(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="actual target does not resolve in owning Support Process",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(actual_target=participant_target("spp_missing")),
        )


def test_unresolved_actual_provider_fails_closed(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="provider Participant ref does not resolve in owning Support Process",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(provider=participant_provider("spp_missing")),
        )


def test_provider_difference_requires_explicit_variation(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path, collaborator=True)
    service = ImplementationWorkflowService(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="provider variation is required when actual provider differs from plan",
    ):
        service.create(
            work_ref(),
            implementation_record(provider=participant_provider("spp_collaborator")),
        )

    created = service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_provider_variation",
            provider=participant_provider("spp_collaborator"),
            variation={
                "kinds": ["provider"],
                "detail": "A different participant provided this occurrence.",
            },
        ),
    )
    assert created.record.logical_id == "imp_provider_variation"


def test_target_difference_requires_explicit_variation(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path, collaborator=True)
    service = ImplementationWorkflowService(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="target variation is required when actual target differs from plan",
    ):
        service.create(
            work_ref(),
            implementation_record(
                actual_target=participant_target("spp_collaborator")
            ),
        )

    created = service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_target_variation",
            actual_target=participant_target("spp_collaborator"),
            variation={
                "kinds": ["target"],
                "detail": "The actual target differed for this occurrence.",
            },
        ),
    )
    assert created.record.logical_id == "imp_target_variation"


def test_unknown_execution_state_is_not_digitally_authored(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="unknown execution_state is import-only",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(
                execution_state="unknown",
                ended_at=None,
            ),
        )


def test_implementation_chronology_is_validated(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ended_at cannot precede started_at",
    ):
        service.create(
            work_ref(),
            implementation_record(ended_at="2026-09-02T10:29:00-04:00"),
        )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="created_at cannot precede started_at",
    ):
        service.create(
            work_ref(),
            implementation_record(
                created_at="2026-09-02T10:29:00-04:00",
                updated_at="2026-09-02T10:29:00-04:00",
            ),
        )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="updated_at cannot precede created_at",
    ):
        service.create(
            work_ref(),
            implementation_record(updated_at="2026-09-02T10:44:00-04:00"),
        )


@pytest.mark.parametrize(
    "terminal_state",
    ["completed", "partially_completed", "unable_to_complete"],
)
def test_in_progress_occurrence_can_reach_each_ordinary_terminal_state(
    tmp_path: Path,
    terminal_state: str,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")

    accepted = service.transition_execution_state(
        reference,
        implementation_record(
            execution_state=terminal_state,
            ended_at=ENDED,
            updated_at=TRANSITIONED,
        ),
        expected=created.fingerprint,
    )

    assert accepted.record.logical_id == "imp_alpha"
    assert accepted.record.field("execution_state") == terminal_state
    assert accepted.record.field("ended_at") == ENDED
    assert accepted.fingerprint != created.fingerprint
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "implementation",
        "imp_alpha",
        created.fingerprint.digest,
    )
    assert history.is_file()
    assert service.load_exact(reference) == accepted


@pytest.mark.parametrize(
    ("prior_state", "candidate_state"),
    [
        ("attempted", "completed"),
        ("completed", "in_progress"),
        ("partially_completed", "completed"),
        ("unable_to_complete", "completed"),
    ],
)
def test_terminal_or_attempted_states_do_not_use_ordinary_execution_progression(
    tmp_path: Path,
    prior_state: str,
    candidate_state: str,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    prior_ended = None if prior_state == "attempted" else ENDED
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state=prior_state,
            ended_at=prior_ended,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Implementation execution progression requires in_progress",
    ):
        service.transition_execution_state(
            reference,
            implementation_record(
                execution_state=candidate_state,
                ended_at=ENDED,
                updated_at=TRANSITIONED,
            ),
            expected=created.fingerprint,
        )

    unchanged = service.load_exact(reference)
    assert unchanged.fingerprint == created.fingerprint
    assert unchanged.record.field("execution_state") == prior_state
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "implementation",
        "imp_alpha",
        created.fingerprint.digest,
    )
    assert not history.exists()


def test_in_progress_same_state_is_not_an_ordinary_revision(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "illegal Implementation execution_state transition: "
            "in_progress -> in_progress"
        ),
    ):
        service.transition_execution_state(
            reference,
            implementation_record(
                execution_state="in_progress",
                ended_at=None,
                updated_at=TRANSITIONED,
            ),
            expected=created.fingerprint,
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_execution_progression_cannot_rewrite_other_occurrence_facts(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite field summary",
    ):
        service.transition_execution_state(
            reference,
            implementation_record(
                execution_state="completed",
                ended_at=ENDED,
                updated_at=TRANSITIONED,
                summary="Synthetic rewritten occurrence summary.",
            ),
            expected=created.fingerprint,
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_execution_progression_cannot_rewrite_existing_end_time(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=ENDED,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="cannot rewrite an existing ended_at",
    ):
        service.transition_execution_state(
            reference,
            implementation_record(
                execution_state="completed",
                ended_at="2026-09-02T10:41:00-04:00",
                updated_at=TRANSITIONED,
            ),
            expected=created.fingerprint,
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_execution_progression_requires_current_expected_revision(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")
    completed = service.transition_execution_state(
        reference,
        implementation_record(
            execution_state="completed",
            ended_at=ENDED,
            updated_at=TRANSITIONED,
        ),
        expected=created.fingerprint,
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected Implementation state does not match canonical bytes",
    ):
        service.transition_execution_state(
            reference,
            implementation_record(
                execution_state="partially_completed",
                ended_at=ENDED,
                updated_at=TRANSITIONED,
            ),
            expected=created.fingerprint,
        )

    assert service.load_exact(reference).fingerprint == completed.fingerprint
    assert service.load_exact(reference).record.field("execution_state") == "completed"


class _RejectImplementationTransitionWrites(QuarantineGuard):
    def require_allowed(self, target: object, action: str) -> None:
        if action == "block_work_writes":
            raise RuntimeError("synthetic quarantine blocked transition")


def test_execution_progression_checks_quarantine_before_write(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    baseline = ImplementationWorkflowService(tmp_path)
    created = baseline.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")
    guarded = ImplementationWorkflowService(
        tmp_path,
        quarantine=_RejectImplementationTransitionWrites(tmp_path),
    )

    with pytest.raises(RuntimeError, match="synthetic quarantine blocked transition"):
        guarded.transition_execution_state(
            reference,
            implementation_record(
                execution_state="completed",
                ended_at=ENDED,
                updated_at=TRANSITIONED,
            ),
            expected=created.fingerprint,
        )

    unchanged = baseline.load_exact(reference)
    assert unchanged.fingerprint == created.fingerprint
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "implementation",
        "imp_alpha",
        created.fingerprint.digest,
    )
    assert not history.exists()


# Slice 3 — Implementation canonical lifecycle and current-use authority.
LIFECYCLE_UPDATED = "2026-09-02T11:05:00-04:00"


def _implementation_revision(
    prior: PortiaRecord,
    *,
    status: str | None = None,
    execution_state: str | None = None,
    updated_at: str = LIFECYCLE_UPDATED,
) -> PortiaRecord:
    wire = prior.to_dict()
    if status is not None:
        wire["status"] = status
    if execution_state is not None:
        wire["execution_state"] = execution_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("implementation", "1", wire)


def test_completed_active_implementation_qualifies_for_current_use(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())

    current = service.require_current_use(
        implementation_reference(work_ref(), "imp_alpha")
    )
    resolved = service.resolve_current(
        implementation_reference(work_ref(), "imp_alpha")
    )

    assert current.fingerprint == created.fingerprint
    assert resolved.fingerprint == created.fingerprint
    assert current.record.status == "active"
    assert current.record.field("execution_state") == "completed"


def test_implementation_lifecycle_invalidation_removes_current_use(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    reference = implementation_reference(work_ref(), "imp_alpha")

    service.transition_lifecycle(
        reference,
        _implementation_revision(created.record, status="invalidated"),
        expected=created.fingerprint,
        transition_id="lct_imp_slice3_invalidated",
        reason_code="recording_error",
        operation_id="op_imp_slice3_invalidated",
    )

    exact = service.load_exact(reference)
    assert exact.record.status == "invalidated"
    assert exact.record.field("execution_state") == "completed"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_imp_slice3_invalidated",
    )
    assert transition.record.field("target") == {
        "kind": "local_record",
        "record_ref": {
            "record_kind": "implementation",
            "record_id": "imp_alpha",
            "contract_version": "1",
        },
    }
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "invalidated"

    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(reference)


def test_implementation_lifecycle_change_cannot_rewrite_execution_state(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "ordinary Implementation lifecycle replacement cannot rewrite "
            "field execution_state"
        ),
    ):
        service.transition_lifecycle(
            reference,
            _implementation_revision(
                created.record,
                status="invalidated",
                execution_state="partially_completed",
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice3_mixed_dimension",
            reason_code="recording_error",
            operation_id="op_imp_slice3_mixed_dimension",
        )

    unchanged = service.load_exact(reference)
    assert unchanged.fingerprint == created.fingerprint
    assert unchanged.record.status == "active"
    assert unchanged.record.field("execution_state") == "completed"


def test_implementation_lifecycle_same_status_is_not_an_ordinary_revision(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Implementation lifecycle coordination requires a status change",
    ):
        service.transition_lifecycle(
            reference,
            _implementation_revision(created.record, status="active"),
            expected=created.fingerprint,
            transition_id="lct_imp_slice3_same_status",
            reason_code="recording_error",
            operation_id="op_imp_slice3_same_status",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_implementation_lifecycle_supersession_is_reserved_for_correction(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    reference = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        service.transition_lifecycle(
            reference,
            _implementation_revision(created.record, status="superseded"),
            expected=created.fingerprint,
            transition_id="lct_imp_slice3_superseded",
            reason_code="recording_error",
            operation_id="op_imp_slice3_superseded",
        )

    assert service.load_exact(reference).fingerprint == created.fingerprint


def test_implementation_execution_progression_requires_active_canonical_status(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        implementation_record(
            execution_state="in_progress",
            ended_at=None,
        ),
    )
    reference = implementation_reference(work_ref(), "imp_alpha")
    service.transition_lifecycle(
        reference,
        _implementation_revision(created.record, status="invalidated"),
        expected=created.fingerprint,
        transition_id="lct_imp_slice3_invalidated_in_progress",
        reason_code="recording_error",
        operation_id="op_imp_slice3_invalidated_in_progress",
    )
    invalidated = service.load_exact(reference)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match=(
            "ordinary Implementation execution progression requires active "
            "canonical status"
        ),
    ):
        service.transition_execution_state(
            reference,
            _implementation_revision(
                invalidated.record,
                execution_state="completed",
                updated_at="2026-09-02T11:10:00-04:00",
            ),
            expected=invalidated.fingerprint,
        )


# Slice 4A — ordinary one-to-one Implementation correction/supersession.
CORRECTION_UPDATED = "2026-09-02T11:20:00-04:00"


def _implementation_successor(
    prior: PortiaRecord,
    *,
    implementation_id: str = "imp_beta",
    reason: str = "summary_corrected",
    detail: str | None = None,
    summary: str | None = None,
    execution_state: str | None = None,
    started_at: str | None = None,
    ended_at: str | None | object = Ellipsis,
    predecessor_refs: list[dict[str, object]] | None = None,
    updated_at: str = CORRECTION_UPDATED,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["implementation_id"] = implementation_id
    wire["status"] = "active"
    if summary is not None:
        wire["summary"] = summary
    if execution_state is not None:
        wire["execution_state"] = execution_state
    if started_at is not None:
        wire["started_at"] = started_at
    if ended_at is not Ellipsis:
        if ended_at is None:
            wire.pop("ended_at", None)
        else:
            wire["ended_at"] = ended_at
    if predecessor_refs is None:
        predecessor_id = prior.logical_id
        assert predecessor_id is not None
        predecessor_refs = [
            implementation_reference(work_ref(), predecessor_id).to_dict()
        ]
    entries: list[dict[str, object]] = []
    for reference in predecessor_refs:
        entry: dict[str, object] = {
            "work_record_ref": reference,
            "reason": reason,
        }
        if detail is not None:
            entry["detail"] = detail
        entries.append(entry)
    wire["supersedes"] = entries
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("implementation", "1", wire)


def test_implementation_summary_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _implementation_successor(
        created.record,
        reason="summary_corrected",
        summary="Corrected synthetic occurrence summary.",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_imp_slice4a_summary",
        operation_id="op_imp_slice4a_summary",
    )

    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        implementation_reference(work_ref(), "imp_beta")
    )
    assert old_exact.record.logical_id == "imp_alpha"
    assert old_exact.record.status == "superseded"
    assert old_exact.record.field("summary") == created.record.field("summary")
    assert current.record.logical_id == "imp_beta"
    assert current.record.status == "active"
    assert current.record.field("summary") == "Corrected synthetic occurrence summary."

    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_imp_slice4a_summary",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "summary_corrected",
    }


def test_terminal_execution_state_correction_uses_successor_history(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _implementation_successor(
        created.record,
        reason="execution_state_corrected",
        execution_state="partially_completed",
    )

    service.correct(
        predecessor,
        successor,
        expected=created.fingerprint,
        transition_id="lct_imp_slice4a_execution",
        operation_id="op_imp_slice4a_execution",
    )

    old_exact = service.load_exact(predecessor)
    current = service.resolve_current(
        implementation_reference(work_ref(), "imp_beta")
    )
    assert old_exact.record.field("execution_state") == "completed"
    assert old_exact.record.status == "superseded"
    assert current.record.field("execution_state") == "partially_completed"


def test_implementation_correction_preserves_predecessor_storage_history(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")

    service.correct(
        predecessor,
        _implementation_successor(
            created.record,
            summary="Corrected summary preserved through successor history.",
        ),
        expected=created.fingerprint,
        transition_id="lct_imp_slice4a_history",
        operation_id="op_imp_slice4a_history",
    )

    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "implementation",
        "imp_alpha",
        created.fingerprint.digest,
    )
    assert history.exists()


def test_implementation_correction_reason_must_match_changed_fact(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="does not match the corrected occurrence fact",
    ):
        service.correct(
            predecessor,
            _implementation_successor(
                created.record,
                reason="provider_corrected",
                summary="Only the summary changed.",
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_reason_mismatch",
            operation_id="op_imp_slice4a_reason_mismatch",
        )

    assert service.load_exact(predecessor).fingerprint == created.fingerprint


def test_implementation_cannot_supersede_itself(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="Implementation cannot supersede itself",
    ):
        service.correct(
            predecessor,
            _implementation_successor(
                created.record,
                implementation_id="imp_alpha",
                summary="Synthetic self-supersession attempt.",
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_self",
            operation_id="op_imp_slice4a_self",
        )


def test_ordinary_implementation_correction_is_one_to_one(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    second = implementation_reference(work_ref(), "imp_other").to_dict()

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Implementation correction is one-to-one",
    ):
        service.correct(
            predecessor,
            _implementation_successor(
                created.record,
                summary="Synthetic invalid two-predecessor correction.",
                predecessor_refs=[predecessor.to_dict(), second],
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_two",
            operation_id="op_imp_slice4a_two",
        )


def test_mixed_implementation_supersession_reasons_fail_closed(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    wire = _implementation_successor(
        created.record,
        summary="Synthetic mixed reason correction.",
        predecessor_refs=[
            predecessor.to_dict(),
            implementation_reference(work_ref(), "imp_other").to_dict(),
        ],
    ).to_dict()
    wire["supersedes"][1]["reason"] = "provider_corrected"
    successor = parse_portia_record("implementation", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="mixed Implementation supersession reasons",
    ):
        service.correct(
            predecessor,
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_mixed",
            operation_id="op_imp_slice4a_mixed",
        )


def test_duplicate_consolidation_requires_two_predecessors(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation needs two Implementation predecessors",
    ):
        service.correct(
            predecessor,
            _implementation_successor(
                created.record,
                reason="duplicate_consolidated",
                summary="Synthetic duplicate consolidation attempt.",
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_duplicate_one",
            operation_id="op_imp_slice4a_duplicate_one",
        )


def test_ordinary_correction_cannot_cross_support_process_roots(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_other",
        work_kind="support_process",
        contract_version="1",
    )
    cross_ref = implementation_reference(other_work, "imp_old").to_dict()

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="ordinary Implementation correction cannot cross Support Process roots",
    ):
        service.correct(
            predecessor,
            _implementation_successor(
                created.record,
                summary="Synthetic cross-root ordinary correction.",
                predecessor_refs=[cross_ref],
            ),
            expected=created.fingerprint,
            transition_id="lct_imp_slice4a_cross_root",
            operation_id="op_imp_slice4a_cross_root",
        )


# Slice 4B1 — duplicate-consolidation topology and current-resolution semantics.
CONSOLIDATION_UPDATED = "2026-09-02T11:30:00-04:00"


def _seed_superseded_implementation(
    service: ImplementationWorkflowService,
    stored: StoredRecord,
) -> None:
    # This helper seeds an accepted historical graph directly so this slice can
    # qualify read/current topology before the coordinated consolidation writer.
    record = stored.record
    fingerprint = stored.fingerprint
    wire = record.to_dict()
    wire["status"] = "superseded"
    wire["updated_at"] = CONSOLIDATION_UPDATED
    wire["updated_by"] = AGENT
    candidate = parse_portia_record("implementation", "1", wire)
    service.repository.replace_work_record(
        work_ref(),
        candidate,
        expected=fingerprint,
    )


def _seed_duplicate_consolidation_successor(
    service: ImplementationWorkflowService,
    prior: PortiaRecord,
    predecessor_ids: list[str],
) -> PortiaRecord:
    refs = [
        implementation_reference(work_ref(), identifier).to_dict()
        for identifier in predecessor_ids
    ]
    successor = _implementation_successor(
        prior,
        implementation_id="imp_merge",
        reason="duplicate_consolidated",
        summary="Synthetic canonical record after duplicate consolidation.",
        predecessor_refs=refs,
        updated_at=CONSOLIDATION_UPDATED,
    )
    service.repository.create_work_record(work_ref(), successor)
    return successor


def test_duplicate_consolidation_current_use_accepts_all_superseded_predecessors(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_gamma",
            summary="Synthetic duplicate representation of the same occurrence.",
        ),
    )
    _seed_superseded_implementation(service, first)
    _seed_superseded_implementation(service, second)
    _seed_duplicate_consolidation_successor(
        service,
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    current = service.require_current_use(
        implementation_reference(work_ref(), "imp_merge")
    )

    assert current.record.logical_id == "imp_merge"
    assert current.record.status == "active"
    assert service.load_exact(
        implementation_reference(work_ref(), "imp_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        implementation_reference(work_ref(), "imp_gamma")
    ).record.status == "superseded"


def test_duplicate_consolidation_current_use_requires_every_predecessor_superseded(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_gamma",
            summary="Synthetic duplicate representation of the same occurrence.",
        ),
    )
    _seed_superseded_implementation(service, first)
    _seed_duplicate_consolidation_successor(
        service,
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires its exact predecessor superseded",
    ):
        service.require_current_use(
            implementation_reference(work_ref(), "imp_merge")
        )


def test_duplicate_consolidation_cannot_cross_support_process_roots(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    other_work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_other",
        work_kind="support_process",
        contract_version="1",
    )
    successor = _implementation_successor(
        first.record,
        implementation_id="imp_merge",
        reason="duplicate_consolidated",
        summary="Synthetic invalid cross-root consolidation.",
        predecessor_refs=[
            implementation_reference(work_ref(), "imp_alpha").to_dict(),
            implementation_reference(other_work, "imp_gamma").to_dict(),
        ],
        updated_at=CONSOLIDATION_UPDATED,
    )
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="duplicate consolidation cannot cross Support Process roots",
    ):
        service.require_current_use(
            implementation_reference(work_ref(), "imp_merge")
        )


def test_duplicate_consolidation_rejects_repeated_predecessor_identity(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    reference = implementation_reference(work_ref(), "imp_alpha").to_dict()
    distinct_reference = implementation_reference(work_ref(), "imp_beta").to_dict()
    wire = _implementation_successor(
        first.record,
        implementation_id="imp_merge",
        reason="duplicate_consolidated",
        summary="Synthetic invalid repeated-predecessor consolidation.",
        predecessor_refs=[reference, distinct_reference],
        updated_at=CONSOLIDATION_UPDATED,
    ).to_dict()
    wire["supersedes"][1]["work_record_ref"] = reference
    wire["supersedes"][1]["detail"] = "Distinct entry, same exact predecessor."
    successor = parse_portia_record("implementation", "1", wire)
    service.repository.create_work_record(work_ref(), successor)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="repeats a predecessor identity",
    ):
        service.require_current_use(
            implementation_reference(work_ref(), "imp_merge")
        )


# Slice 4B2 — atomic duplicate-consolidation persistence.
CONSOLIDATION_WRITE_UPDATED = "2026-09-02T11:40:00-04:00"


def _consolidation_successor(
    prior: PortiaRecord,
    predecessor_ids: list[str],
) -> PortiaRecord:
    return _implementation_successor(
        prior,
        implementation_id="imp_merge",
        reason="duplicate_consolidated",
        summary="Synthetic canonical duplicate-consolidation successor.",
        predecessor_refs=[
            implementation_reference(work_ref(), identifier).to_dict()
            for identifier in predecessor_ids
        ],
        updated_at=CONSOLIDATION_WRITE_UPDATED,
    )


def _consolidation_transition_ids() -> dict[str, str]:
    return {
        "imp_alpha": "lct_imp_consolidate_alpha",
        "imp_gamma": "lct_imp_consolidate_gamma",
    }


def test_duplicate_consolidation_writer_supersedes_all_predecessors_atomically(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_gamma",
            summary="Synthetic duplicate representation of the same occurrence.",
        ),
    )
    successor = _consolidation_successor(
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    result = service.consolidate_duplicates(
        work_ref(),
        successor,
        expected={
            "imp_alpha": first.fingerprint,
            "imp_gamma": second.fingerprint,
        },
        transition_ids=_consolidation_transition_ids(),
        operation_id="op_imp_consolidate",
    )

    assert result.operation_id == "op_imp_consolidate"
    assert service.load_exact(
        implementation_reference(work_ref(), "imp_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        implementation_reference(work_ref(), "imp_gamma")
    ).record.status == "superseded"
    current = service.require_current_use(
        implementation_reference(work_ref(), "imp_merge")
    )
    assert current.record == successor

    for predecessor_id, transition_id in _consolidation_transition_ids().items():
        transition = service.repository.load_work_record(
            work_ref(),
            "lifecycle_transition",
            "1",
            transition_id,
        )
        assert transition.record.field("target") == {
            "kind": "local_record",
            "record_ref": {
                "record_kind": "implementation",
                "record_id": predecessor_id,
                "contract_version": "1",
            },
        }
        assert transition.record.field("reason") == {
            "category": "consolidation",
            "code": "duplicate_consolidated",
        }

    for predecessor_id, stored in (
        ("imp_alpha", first),
        ("imp_gamma", second),
    ):
        history = work_storage_history_path(
            tmp_path,
            work_ref(),
            "implementation",
            predecessor_id,
            stored.fingerprint.digest,
        )
        assert history.exists()


def test_duplicate_consolidation_stale_predecessor_rejects_zero_graph_writes(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(implementation_id="imp_gamma"),
    )
    second_wire = second.record.to_dict()
    second_wire["summary"] = "Synthetic later canonical edit."
    second_wire["updated_at"] = "2026-09-02T11:35:00-04:00"
    second_wire["updated_by"] = AGENT
    changed_second = parse_portia_record("implementation", "1", second_wire)
    service.repository.replace_work_record(
        work_ref(),
        changed_second,
        expected=second.fingerprint,
    )
    successor = _consolidation_successor(
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    with pytest.raises(
        PortiaConflictError,
        match="expected predecessor action state does not match canonical bytes",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "imp_alpha": first.fingerprint,
                "imp_gamma": second.fingerprint,
            },
            transition_ids=_consolidation_transition_ids(),
            operation_id="op_imp_consolidate_stale",
        )

    assert service.load_exact(
        implementation_reference(work_ref(), "imp_alpha")
    ).record.status == "active"
    assert service.load_exact(
        implementation_reference(work_ref(), "imp_gamma")
    ).record.status == "active"
    assert "imp_merge" not in {
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
    assert not set(_consolidation_transition_ids().values()) & transition_ids


def test_duplicate_consolidation_requires_unique_transition_ids(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(implementation_id="imp_gamma"),
    )
    successor = _consolidation_successor(
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="lifecycle transition IDs must be unique",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "imp_alpha": first.fingerprint,
                "imp_gamma": second.fingerprint,
            },
            transition_ids={
                "imp_alpha": "lct_imp_duplicate",
                "imp_gamma": "lct_imp_duplicate",
            },
            operation_id="op_imp_duplicate_transition",
        )

    assert {item.record.status for item in service.list(work_ref())} == {"active"}
    assert "imp_merge" not in {
        item.record.logical_id for item in service.list(work_ref())
    }


def test_duplicate_consolidation_checks_quarantine_before_graph_write(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    baseline = ImplementationWorkflowService(tmp_path)
    first = baseline.create(work_ref(), implementation_record())
    second = baseline.create(
        work_ref(),
        implementation_record(implementation_id="imp_gamma"),
    )
    guarded = ImplementationWorkflowService(
        tmp_path,
        quarantine=_RejectImplementationTransitionWrites(tmp_path),
    )

    with pytest.raises(RuntimeError, match="synthetic quarantine blocked transition"):
        guarded.consolidate_duplicates(
            work_ref(),
            _consolidation_successor(
                first.record,
                ["imp_alpha", "imp_gamma"],
            ),
            expected={
                "imp_alpha": first.fingerprint,
                "imp_gamma": second.fingerprint,
            },
            transition_ids=_consolidation_transition_ids(),
            operation_id="op_imp_consolidate_quarantine",
        )

    assert {item.record.status for item in baseline.list(work_ref())} == {"active"}
    assert "imp_merge" not in {
        item.record.logical_id for item in baseline.list(work_ref())
    }


def test_duplicate_consolidation_completed_operation_replays_idempotently(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(implementation_id="imp_gamma"),
    )
    successor = _consolidation_successor(
        first.record,
        ["imp_alpha", "imp_gamma"],
    )
    kwargs = {
        "expected": {
            "imp_alpha": first.fingerprint,
            "imp_gamma": second.fingerprint,
        },
        "transition_ids": _consolidation_transition_ids(),
        "operation_id": "op_imp_consolidate_replay",
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
        implementation_reference(work_ref(), "imp_merge")
    ).record == successor


def test_duplicate_consolidation_requires_one_exact_plan(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    first = service.create(work_ref(), implementation_record())
    second = service.create(
        work_ref(),
        implementation_record(
            implementation_id="imp_gamma",
            plan_kind="support",
            plan_id="spt_alpha",
            provider={
                "kind": "no_human_provider",
                "reason": "environmental_condition",
            },
        ),
    )
    successor = _consolidation_successor(
        first.record,
        ["imp_alpha", "imp_gamma"],
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires one exact Implementation plan",
    ):
        service.consolidate_duplicates(
            work_ref(),
            successor,
            expected={
                "imp_alpha": first.fingerprint,
                "imp_gamma": second.fingerprint,
            },
            transition_ids=_consolidation_transition_ids(),
            operation_id="op_imp_consolidate_plan_mismatch",
        )

    assert {item.record.status for item in service.list(work_ref())} == {"active"}
    assert "imp_merge" not in {
        item.record.logical_id for item in service.list(work_ref())
    }


# Slice 4B3 — cross-root Implementation ownership correction.
WORK_ROOT_UPDATED = "2026-09-02T12:30:00-04:00"


def corrected_work_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_b",
        work_id="sup_beta",
        work_kind="support_process",
        contract_version="1",
    )


def _retarget_record(record: PortiaRecord, work: ExactPortiaWorkRef) -> PortiaRecord:
    wire = record.to_dict()
    wire["class_id"] = work.class_id
    wire["work_id"] = work.work_id
    return parse_portia_record(record.contract, record.contract_version, wire)


def _activate_participant_for_work(
    tmp_path: Path,
    work: ExactPortiaWorkRef,
    participant_id: str,
    *,
    contexts: list[dict[str, object]],
    display_label: str,
    transition_suffix: str,
    description_type: str = "school_staff",
) -> None:
    service = SupportProcessParticipantWorkflowService(tmp_path)
    proposed = _retarget_record(
        participant_record(
            participant_id,
            contexts=contexts,
            display_label=display_label,
            description_type=description_type,
        ),
        work,
    )
    active = _retarget_record(
        participant_record(
            participant_id,
            status="active",
            contexts=contexts,
            display_label=display_label,
            description_type=description_type,
            updated_at=PARTICIPANT_UPDATED,
        ),
        work,
    )
    created = service.create(work, proposed)
    service.transition_lifecycle(
        support_process_participant_reference(work, participant_id),
        active,
        expected=created.fingerprint,
        transition_id=f"lct_{transition_suffix}",
        reason_code="planning_confirmed",
        operation_id=f"op_{transition_suffix}",
    )


def _setup_active_plans_for_work(
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
        contexts=[{"kind": "supported_person"}],
        display_label="Synthetic learner in corrected root",
        transition_suffix=f"{suffix}_student_active",
        description_type="outside_student",
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
        "spp_provider",
        contexts=[{"kind": "provider_or_collaborator"}],
        display_label="Synthetic provider in corrected root",
        transition_suffix=f"{suffix}_provider_active",
    )
    SupportNeedWorkflowService(tmp_path).create(
        work,
        _retarget_record(need_record(), work),
    )
    SupportGoalWorkflowService(tmp_path).create(
        work,
        _retarget_record(goal_record(), work),
    )
    SupportWorkflowService(tmp_path).create(
        work,
        _retarget_record(support_record(), work),
    )
    InterventionWorkflowService(tmp_path).create(
        work,
        _retarget_record(intervention_record(), work),
    )


def _work_root_successor(
    prior: PortiaRecord,
    predecessor: ExactPortiaWorkRecordRef,
    destination_work: ExactPortiaWorkRef,
    *,
    summary: str | None = None,
    updated_at: str = WORK_ROOT_UPDATED,
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
    return parse_portia_record("implementation", "1", wire)


def test_work_root_correction_crosses_class_and_preserves_exact_history(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_beta")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
        created.record,
        predecessor,
        destination,
    )

    result = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_imp_work_root_alpha",
        operation_id="op_imp_work_root_alpha",
    )

    assert result.operation_id == "op_imp_work_root_alpha"
    old_exact = service.resolve_exact(predecessor)
    current = service.require_current_use(
        implementation_reference(destination, "imp_alpha")
    )
    assert old_exact.record.status == "superseded"
    assert old_exact.record.class_id == "class_a"
    assert old_exact.record.work_id == "sup_alpha"
    assert current.record.status == "active"
    assert current.record.logical_id == "imp_alpha"
    assert current.record.class_id == "class_b"
    assert current.record.work_id == "sup_beta"
    history = work_storage_history_path(
        tmp_path,
        work_ref(),
        "implementation",
        "imp_alpha",
        created.fingerprint.digest,
    )
    assert history.is_file()


def test_work_root_correction_rejects_occurrence_fact_rewrite(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_fact")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
        created.record,
        predecessor,
        destination,
        summary="Piggybacked synthetic summary rewrite.",
    )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction cannot rewrite occurrence fact summary",
    ):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_work_root_fact",
            operation_id="op_imp_work_root_fact",
        )

    assert service.resolve_exact(predecessor).record.status == "active"
    assert service.list_implementations(destination) == ()


def test_work_root_correction_rejects_stale_predecessor_before_any_write(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_stale")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
        created.record,
        predecessor,
        destination,
    )
    changed_wire = created.record.to_dict()
    changed_wire["summary"] = "Synthetic later source-root edit."
    changed_wire["updated_at"] = "2026-09-02T12:20:00-04:00"
    changed_wire["updated_by"] = AGENT
    service.repository.replace_work_record(
        work_ref(),
        parse_portia_record("implementation", "1", changed_wire),
        expected=created.fingerprint,
    )

    with pytest.raises(PortiaConflictError, match="expected predecessor action state"):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_work_root_stale",
            operation_id="op_imp_work_root_stale",
        )

    assert service.resolve_exact(predecessor).record.status == "active"
    assert service.list_implementations(destination) == ()


def test_work_root_correction_rejects_existing_destination_identity(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_existing")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    service.create(
        destination,
        _retarget_record(implementation_record(), destination),
    )
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
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
            transition_id="lct_imp_work_root_existing",
            operation_id="op_imp_work_root_existing",
        )

    assert service.resolve_exact(predecessor).record.status == "active"


def test_work_root_correction_completed_operation_replays_idempotently(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_replay")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
        created.record,
        predecessor,
        destination,
    )
    first = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_imp_work_root_replay",
        operation_id="op_imp_work_root_replay",
    )
    replay = service.correct_work_root(
        predecessor,
        destination,
        successor,
        expected=created.fingerprint,
        transition_id="lct_imp_work_root_replay",
        operation_id="op_imp_work_root_replay",
    )

    assert replay.operation_id == first.operation_id
    assert service.resolve_exact(predecessor).record.status == "superseded"
    assert (
        service.require_current_use(
            implementation_reference(destination, "imp_alpha")
        ).record.to_dict()
        == successor.to_dict()
    )


def test_work_root_correction_destination_quarantine_blocks_all_writes(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_quarantine")
    baseline = ImplementationWorkflowService(tmp_path)
    created = baseline.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(
        created.record,
        predecessor,
        destination,
    )
    guarded = ImplementationWorkflowService(
        tmp_path,
        quarantine=_RejectImplementationTransitionWrites(tmp_path),
    )

    with pytest.raises(RuntimeError, match="synthetic quarantine blocked transition"):
        guarded.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_work_root_quarantine",
            operation_id="op_imp_work_root_quarantine",
        )

    assert baseline.resolve_exact(predecessor).record.status == "active"
    assert baseline.list_implementations(destination) == ()


# Slice 4C — frozen Issue #18 Implementation fixture parity.


def test_multi_kind_variation_records_multiple_actual_differences(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path, collaborator=True)
    created = ImplementationWorkflowService(tmp_path).create(
        work_ref(),
        implementation_record(
            implementation_id="imp_multi_variation",
            actual_target=participant_target("spp_collaborator"),
            provider=participant_provider("spp_collaborator"),
            variation={
                "kinds": ["provider", "target"],
                "detail": (
                    "Synthetic target and provider both differed for this occurrence."
                ),
            },
        ),
    )
    assert created.record.field("variation") == {
        "kinds": ("provider", "target"),
        "detail": "Synthetic target and provider both differed for this occurrence.",
    }


def test_historical_proposed_import_unknown_resolves_exactly_without_current_use(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    wire = implementation_record(
        implementation_id="imp_imported_unknown",
        execution_state="unknown",
    ).to_dict()
    wire["status"] = "proposed"
    wire["creation_source"] = {
        "type": "import",
        "source_label": "Synthetic historical import",
    }
    historical = parse_portia_record("implementation", "1", wire)
    stored = service.repository.create_work_record(work_ref(), historical)
    exact = implementation_reference(work_ref(), "imp_imported_unknown")

    assert service.resolve_exact(exact).record == stored.record
    with pytest.raises(WorkflowPrerequisiteError):
        service.require_current_use(exact)


@pytest.mark.parametrize(
    "creation_source",
    [
        {"type": "import", "source_label": "Synthetic historical import"},
        {
            "type": "paper_capture",
            "stage": "ingested",
            "route_id": "route_synthetic_1",
            "page_record_id": "page_synthetic_1",
        },
    ],
    ids=["active-import", "active-paper"],
)
def test_active_paper_or_import_implementation_requires_review_history(
    tmp_path: Path,
    creation_source: dict[str, object],
) -> None:
    _setup_active_plans(tmp_path)
    wire = implementation_record().to_dict()
    wire["creation_source"] = creation_source
    record = parse_portia_record("implementation", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="paper/import activation requires accepted review history",
    ):
        ImplementationWorkflowService(tmp_path).create(work_ref(), record)


def test_unknown_paper_execution_state_is_import_only(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    wire = implementation_record(execution_state="unknown").to_dict()
    wire["status"] = "proposed"
    wire["creation_source"] = {
        "type": "paper_capture",
        "stage": "ingested",
        "route_id": "route_synthetic_1",
        "page_record_id": "page_synthetic_1",
    }
    record = parse_portia_record("implementation", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="unknown execution_state is import-only",
    ):
        ImplementationWorkflowService(tmp_path).create(work_ref(), record)


def test_provider_difference_with_wrong_variation_kind_fails_closed(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path, collaborator=True)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="provider variation is required when actual provider differs from plan",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(
                provider=participant_provider("spp_collaborator"),
                variation={
                    "kinds": ["target"],
                    "detail": "Synthetic wrong variation kind.",
                },
            ),
        )


def test_target_difference_with_wrong_variation_kind_fails_closed(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path, collaborator=True)
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="target variation is required when actual target differs from plan",
    ):
        ImplementationWorkflowService(tmp_path).create(
            work_ref(),
            implementation_record(
                actual_target=participant_target("spp_collaborator"),
                variation={
                    "kinds": ["provider"],
                    "detail": "Synthetic wrong variation kind.",
                },
            ),
        )


def test_duplicate_logical_provider_identity_fails_closed(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    stored: list[StoredRecord] = []
    for participant_id in ("spp_duplicate_a", "spp_duplicate_b"):
        wire = participant_record(
            participant_id,
            status="active",
            contexts=[{"kind": "provider_or_collaborator"}],
            display_label="Synthetic duplicate local operator",
        ).to_dict()
        wire["person"] = {
            "kind": "local_operator",
            "display_label": "Synthetic local operator",
        }
        stored.append(
            service.repository.create_work_record(
                work_ref(),
                parse_portia_record("support_process_participant", "1", wire),
            )
        )

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="provider set repeats a logical participant",
    ):
        _require_unique_logical_people(stored, description="provider set")


def test_work_root_correction_requires_different_support_process_root(
    tmp_path: Path,
) -> None:
    _setup_active_plans(tmp_path)
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    successor = _work_root_successor(created.record, predecessor, work_ref())

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction requires a different Support Process root",
    ):
        service.correct_work_root(
            predecessor,
            work_ref(),
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_work_root_same",
            operation_id="op_imp_work_root_same",
        )


def test_work_root_correction_preserves_implementation_id(tmp_path: Path) -> None:
    _setup_active_plans(tmp_path)
    destination = corrected_work_ref()
    _setup_active_plans_for_work(tmp_path, destination, suffix="root_changed_id")
    service = ImplementationWorkflowService(tmp_path)
    created = service.create(work_ref(), implementation_record())
    predecessor = implementation_reference(work_ref(), "imp_alpha")
    wire = _work_root_successor(created.record, predecessor, destination).to_dict()
    wire["implementation_id"] = "imp_changed"
    successor = parse_portia_record("implementation", "1", wire)

    with pytest.raises(
        WorkflowPrerequisiteError,
        match="work-root correction must preserve Implementation ID",
    ):
        service.correct_work_root(
            predecessor,
            destination,
            successor,
            expected=created.fingerprint,
            transition_id="lct_imp_work_root_changed_id",
            operation_id="op_imp_work_root_changed_id",
        )
