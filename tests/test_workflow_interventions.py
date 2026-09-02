"""Focused Slice 8a tests for Intervention creation and exact authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    intervention_reference,
    support_process_participant_reference,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-08-31T10:05:00-04:00"
ROOT_UPDATED = "2026-08-31T10:10:00-04:00"
PLAN_CREATED = "2026-08-31T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice8a_test"}


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
    participant_id: str = "spp_alpha",
    *,
    status: str = "proposed",
    person: dict[str, object] | None = None,
    contexts: list[dict[str, object]] | None = None,
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
            "person": person
            or {
                "kind": "descriptive_person",
                "description_type": "outside_student",
                "display_label": f"Synthetic learner {participant_id}",
            },
            "contexts": contexts or [{"kind": "supported_person"}],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def participant_target(participant_id: str = "spp_alpha") -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def need_record(*, status: str = "active") -> PortiaRecord:
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
            "status": status,
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


def goal_record(*, status: str = "active") -> PortiaRecord:
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
            "status": status,
            "target": participant_target(),
            "description": "Synthetic bounded future support objective.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def assigned_provider(provider_id: str = "spp_provider") -> dict[str, object]:
    return {
        "kind": "assigned",
        "participant_refs": [
            {
                "record_kind": "support_process_participant",
                "record_id": provider_id,
                "contract_version": "1",
            }
        ],
    }


def recurring_schedule() -> dict[str, object]:
    return {
        "kind": "recurring",
        "frequency": {
            "occurrences": 1,
            "interval_count": 1,
            "interval_unit": "week",
        },
        "selected_days": ["monday"],
        "planned_duration": {"kind": "minutes", "minutes": 15},
    }


def intervention_record(
    *,
    intervention_id: str = "int_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    need_ids: tuple[str, ...] = ("spn_alpha",),
    goal_ids: tuple[str, ...] = ("spg_alpha",),
    provider_plan: dict[str, object] | None = None,
    schedule: dict[str, object] | None = None,
    plan_state: str = "active",
    source: dict[str, object] | None = None,
    updated_at: str = PLAN_CREATED,
    supersedes: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "intervention",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "intervention_id": intervention_id,
        "status": status,
        "target": target or participant_target(),
        "need_refs": [
            {
                "record_kind": "support_need",
                "record_id": value,
                "contract_version": "1",
            }
            for value in need_ids
        ],
        "goal_refs": [
            {
                "record_kind": "support_goal",
                "record_id": value,
                "contract_version": "1",
            }
            for value in goal_ids
        ],
        "strategy": {
            "kind": "skill_building",
            "procedure": "Use the synthetic structured intervention routine.",
        },
        "provider_plan": provider_plan or assigned_provider(),
        "schedule": schedule or recurring_schedule(),
        "monitoring_approach": (
            "Review the planned synthetic check once each implementation week."
        ),
        "plan_state": plan_state,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": PLAN_CREATED,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if supersedes is not None:
        wire["supersedes"] = supersedes
    return parse_portia_record("intervention", "1", wire)


def _active_process(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participant_service.create(work_ref(), participant_record())
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_alpha"),
        participant_record(status="active", updated_at=PARTICIPANT_UPDATED),
        expected=participant.fingerprint,
        transition_id="lct_spp_slice8a_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice8a_active",
    )
    root_service.transition_lifecycle(
        work_ref(),
        root_record(status="active", updated_at=ROOT_UPDATED),
        expected=root.fingerprint,
        transition_id="lct_sup_slice8a_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice8a_active",
    )


def _active_provider(tmp_path: Path) -> None:
    service = SupportProcessParticipantWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        participant_record(
            "spp_provider",
            contexts=[{"kind": "provider_or_collaborator"}],
            person={"kind": "local_operator", "display_label": "Synthetic provider"},
        ),
    )
    service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_provider"),
        participant_record(
            "spp_provider",
            status="active",
            contexts=[{"kind": "provider_or_collaborator"}],
            person={"kind": "local_operator", "display_label": "Synthetic provider"},
            updated_at=PARTICIPANT_UPDATED,
        ),
        expected=created.fingerprint,
        transition_id="lct_spp_provider_slice8a_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_provider_slice8a_active",
    )


def _active_dependencies(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    _active_provider(tmp_path)


def test_reference_is_exact_support_process_local_intervention() -> None:
    reference = intervention_reference(work_ref(), "int_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "intervention"
    assert reference.record_ref.record_id == "int_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_event_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        intervention_reference(wrong, "int_alpha")


def test_proposed_intervention_can_use_as_needed_and_no_provider(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    created = InterventionWorkflowService(tmp_path).create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Provider assignment remains under planning review.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    assert created.record.status == "proposed"
    assert created.record.field("plan_state") == "planned"


def test_fresh_intervention_cannot_begin_invalidated(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="begin proposed or active"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="invalidated",
                plan_state="planned",
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={"kind": "as_needed"},
            ),
        )


def test_import_candidate_is_not_materialized_by_digital_authoring(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                source={
                    "type": "import",
                    "source_label": "Synthetic historical import",
                },
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={"kind": "as_needed"},
            ),
        )


def test_updated_at_cannot_precede_created_at(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                updated_at="2026-08-31T10:14:00-04:00",
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={"kind": "as_needed"},
            ),
        )


def test_fresh_intervention_rejects_supersession_history(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    supersedes = [
        {
            "work_record_ref": {
                "work_ref": work_ref().to_dict(),
                "record_ref": {
                    "record_kind": "intervention",
                    "record_id": "int_old",
                    "contract_version": "1",
                },
            },
            "reason": "strategy_corrected",
        }
    ]
    with pytest.raises(WorkflowPrerequisiteError, match="supersession history"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                intervention_id="int_new",
                supersedes=supersedes,
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={"kind": "as_needed"},
            ),
        )


def test_active_intervention_requires_current_parent(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical lifecycle"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record()
        )


def test_active_intervention_requires_assigned_provider(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    with pytest.raises(WorkflowPrerequisiteError, match="assigned provider_plan"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "self_directed",
                }
            ),
        )


def test_active_intervention_rejects_as_needed_schedule(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="non-as_needed"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record(schedule={"kind": "as_needed"})
        )


def test_active_intervention_accepts_exact_goal_provider_schedule_and_monitoring(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    created = InterventionWorkflowService(tmp_path).create(
        work_ref(), intervention_record()
    )
    assert created.record.status == "active"
    assert created.record.field("goal_refs")[0]["record_id"] == "spg_alpha"
    assert created.record.field("provider_plan")["kind"] == "assigned"
    assert created.record.field("schedule")["kind"] == "recurring"
    assert "planned synthetic check" in created.record.field("monitoring_approach")


def test_active_intervention_requires_current_need(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    _active_provider(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record()
        )


def test_active_intervention_requires_current_goal(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    _active_provider(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record()
        )


def test_active_intervention_requires_current_provider(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(),
        participant_record(
            "spp_provider",
            contexts=[{"kind": "provider_or_collaborator"}],
            person={"kind": "local_operator", "display_label": "Synthetic provider"},
        ),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record()
        )


def test_unresolved_target_participant_is_rejected(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError, match="Participant reference does not resolve"
    ):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(target=participant_target("spp_missing")),
        )


def test_unresolved_need_is_rejected(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="Need ref does not resolve"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record(need_ids=("spn_missing",))
        )


def test_unresolved_goal_is_rejected(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="Goal ref does not resolve"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(), intervention_record(goal_ids=("spg_missing",))
        )


def test_unresolved_provider_is_rejected(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    with pytest.raises(
        WorkflowPrerequisiteError, match="Participant reference does not resolve"
    ):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(provider_plan=assigned_provider("spp_missing")),
        )


def test_provider_set_rejects_duplicate_logical_person(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(work_ref(), participant_record())
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    same_person = {"kind": "local_operator", "display_label": "Synthetic provider"}
    root_service.repository.create_work_record(
        work_ref(),
        participant_record(
            "spp_provider_a",
            person=same_person,
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    root_service.repository.create_work_record(
        work_ref(),
        participant_record(
            "spp_provider_b",
            person=same_person,
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="repeats a logical"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                provider_plan={
                    "kind": "assigned",
                    "participant_refs": [
                        {
                            "record_kind": "support_process_participant",
                            "record_id": "spp_provider_a",
                            "contract_version": "1",
                        },
                        {
                            "record_kind": "support_process_participant",
                            "record_id": "spp_provider_b",
                            "contract_version": "1",
                        },
                    ],
                },
            ),
        )


def test_schedule_window_chronology_is_application_validated(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="ends_on cannot precede"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={
                    "kind": "custom",
                    "description": "Synthetic bounded schedule.",
                    "window": {
                        "starts_on": "2026-09-10",
                        "ends_on": "2026-09-09",
                    },
                },
            ),
        )


def test_schedule_review_date_cannot_precede_start(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="review_on cannot precede"):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={
                    "kind": "custom",
                    "description": "Synthetic bounded schedule.",
                    "window": {
                        "starts_on": "2026-09-10",
                        "review_on": "2026-09-09",
                    },
                },
            ),
        )


def test_schedule_duration_range_order_is_application_validated(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    with pytest.raises(
        WorkflowPrerequisiteError, match="minimum_minutes cannot exceed"
    ):
        InterventionWorkflowService(tmp_path).create(
            work_ref(),
            intervention_record(
                status="proposed",
                plan_state="planned",
                provider_plan={
                    "kind": "no_assigned_provider",
                    "reason": "other",
                    "detail": "Synthetic planning state.",
                },
                schedule={
                    "kind": "as_needed",
                    "planned_duration": {
                        "kind": "range_minutes",
                        "minimum_minutes": 20,
                        "maximum_minutes": 10,
                    },
                },
            ),
        )


def test_current_use_requires_active_intervention(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    service = InterventionWorkflowService(tmp_path)
    service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Synthetic planning state.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(intervention_reference(work_ref(), "int_alpha"))


def test_active_intervention_qualifies_for_current_use(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    current = service.require_current_use(
        intervention_reference(work_ref(), "int_alpha")
    )
    assert current.fingerprint == created.fingerprint
    assert current.record.status == "active"


def test_exact_read_stays_pinned_to_exact_intervention(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Synthetic planning state.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    exact = service.resolve_exact(intervention_reference(work_ref(), "int_alpha"))
    assert exact.fingerprint == created.fingerprint
    assert exact.record.status == "proposed"


def test_list_interventions_alias_returns_intervention_family(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    service = InterventionWorkflowService(tmp_path)
    service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Synthetic planning state.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    assert [
        item.record.logical_id for item in service.list_interventions(work_ref())
    ] == ["int_alpha"]


# Slice 8b — Intervention canonical lifecycle and ordinary plan-state progression.
PLAN_UPDATE_1 = "2026-08-31T10:20:00-04:00"
PLAN_UPDATE_2 = "2026-08-31T10:25:00-04:00"
PLAN_UPDATE_3 = "2026-08-31T10:30:00-04:00"


def _intervention_revision(
    prior: PortiaRecord,
    *,
    status: str | None = None,
    plan_state: str | None = None,
    updated_at: str,
) -> PortiaRecord:
    wire = prior.to_dict()
    if status is not None:
        wire["status"] = status
    if plan_state is not None:
        wire["plan_state"] = plan_state
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("intervention", "1", wire)


def test_intervention_lifecycle_activation_persists_transition_and_current_use(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(status="proposed", plan_state="planned"),
    )
    candidate = _intervention_revision(
        created.record,
        status="active",
        updated_at=PLAN_UPDATE_1,
    )
    service.transition_lifecycle(
        intervention_reference(work_ref(), "int_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_int_slice8b_active",
        reason_code="planning_confirmed",
        operation_id="op_int_slice8b_active",
    )

    accepted = service.require_current_use(
        intervention_reference(work_ref(), "int_alpha")
    )
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "planned"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_int_slice8b_active",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_intervention_lifecycle_activation_requires_current_need(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())
    _active_provider(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(status="proposed", plan_state="planned"),
    )
    candidate = _intervention_revision(
        created.record,
        status="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        service.transition_lifecycle(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_int_slice8b_need_pending",
            reason_code="planning_confirmed",
            operation_id="op_int_slice8b_need_pending",
        )


def test_intervention_lifecycle_activation_rejects_as_needed_schedule(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            schedule={"kind": "as_needed"},
        ),
    )
    candidate = _intervention_revision(
        created.record,
        status="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="non-as_needed"):
        service.transition_lifecycle(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_int_slice8b_as_needed",
            reason_code="planning_confirmed",
            operation_id="op_int_slice8b_as_needed",
        )


def test_intervention_lifecycle_change_cannot_also_change_plan_state(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(status="proposed", plan_state="planned"),
    )
    candidate = _intervention_revision(
        created.record,
        status="active",
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="plan_state"):
        service.transition_lifecycle(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_int_slice8b_mixed_dimension",
            reason_code="planning_confirmed",
            operation_id="op_int_slice8b_mixed_dimension",
        )


def test_intervention_lifecycle_invalidation_removes_current_use(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    candidate = _intervention_revision(
        created.record,
        status="invalidated",
        updated_at=PLAN_UPDATE_1,
    )
    service.transition_lifecycle(
        intervention_reference(work_ref(), "int_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_int_slice8b_invalidated",
        reason_code="recording_error",
        operation_id="op_int_slice8b_invalidated",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(intervention_reference(work_ref(), "int_alpha"))


def test_intervention_lifecycle_supersession_is_reserved_for_successor_path(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    candidate = _intervention_revision(
        created.record,
        status="superseded",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="correction/adaptation"):
        service.transition_lifecycle(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_int_slice8b_superseded",
            reason_code="planning_confirmed",
            operation_id="op_int_slice8b_superseded",
        )


def test_intervention_plan_state_planned_to_active_preserves_lifecycle(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record(plan_state="planned"))
    candidate = _intervention_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    accepted = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        candidate,
        expected=created.fingerprint,
    )
    assert accepted.record.logical_id == "int_alpha"
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "active"
    intervention_transitions = [
        stored
        for stored in service.repository.list_work_records(
            work_ref(), "lifecycle_transition", version="1"
        )
        if stored.record.field("target")
        == {
            "kind": "local_record",
            "record_ref": {
                "record_kind": "intervention",
                "record_id": "int_alpha",
                "contract_version": "1",
            },
        }
    ]
    assert intervention_transitions == []


def test_intervention_plan_state_active_pause_resume_preserves_identity(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    paused = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            created.record,
            plan_state="paused",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    resumed = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            paused.record,
            plan_state="active",
            updated_at=PLAN_UPDATE_2,
        ),
        expected=paused.fingerprint,
    )
    assert resumed.record.logical_id == created.record.logical_id
    assert resumed.record.field("plan_state") == "active"


def test_intervention_plan_state_completed_is_terminal(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    completed = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            created.record,
            plan_state="completed",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    with pytest.raises(
        WorkflowPrerequisiteError, match="illegal Intervention plan_state"
    ):
        service.transition_plan_state(
            intervention_reference(work_ref(), "int_alpha"),
            _intervention_revision(
                completed.record,
                plan_state="active",
                updated_at=PLAN_UPDATE_2,
            ),
            expected=completed.fingerprint,
        )


def test_intervention_plan_state_planned_to_discontinued_is_terminal(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record(plan_state="planned"))
    discontinued = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            created.record,
            plan_state="discontinued",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    with pytest.raises(
        WorkflowPrerequisiteError, match="illegal Intervention plan_state"
    ):
        service.transition_plan_state(
            intervention_reference(work_ref(), "int_alpha"),
            _intervention_revision(
                discontinued.record,
                plan_state="active",
                updated_at=PLAN_UPDATE_2,
            ),
            expected=discontinued.fingerprint,
        )


def test_intervention_plan_state_rejects_planned_to_paused(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record(plan_state="planned"))
    with pytest.raises(WorkflowPrerequisiteError, match="planned -> paused"):
        service.transition_plan_state(
            intervention_reference(work_ref(), "int_alpha"),
            _intervention_revision(
                created.record,
                plan_state="paused",
                updated_at=PLAN_UPDATE_1,
            ),
            expected=created.fingerprint,
        )


def test_intervention_plan_state_revision_cannot_rewrite_monitoring(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record(plan_state="planned"))
    wire = _intervention_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    ).to_dict()
    wire["monitoring_approach"] = "Materially different monitoring plan."
    candidate = parse_portia_record("intervention", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="field monitoring_approach"):
        service.transition_plan_state(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
        )


def test_intervention_plan_state_progression_requires_active_canonical_status(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(status="proposed", plan_state="planned"),
    )
    candidate = _intervention_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.transition_plan_state(
            intervention_reference(work_ref(), "int_alpha"),
            candidate,
            expected=created.fingerprint,
        )


# Slice 8c — Intervention correction and prospective plan adaptation.
SUCCESSOR_UPDATE_1 = "2026-08-31T10:35:00-04:00"
SUCCESSOR_UPDATE_2 = "2026-08-31T10:40:00-04:00"


def _intervention_successor(
    prior: PortiaRecord,
    *,
    intervention_id: str = "int_beta",
    reason: str,
    detail: str | None = None,
    strategy_procedure: str | None = None,
    monitoring_approach: str | None = None,
    schedule: dict[str, object] | None = None,
    plan_state: str | None = None,
    status: str | None = None,
    updated_at: str = SUCCESSOR_UPDATE_1,
) -> PortiaRecord:
    predecessor_id = prior.logical_id
    assert predecessor_id is not None
    wire = prior.to_dict()
    wire["intervention_id"] = intervention_id
    if status is not None:
        wire["status"] = status
    if plan_state is not None:
        wire["plan_state"] = plan_state
    if strategy_procedure is not None:
        strategy = dict(wire["strategy"])
        strategy["procedure"] = strategy_procedure
        wire["strategy"] = strategy
    if monitoring_approach is not None:
        wire["monitoring_approach"] = monitoring_approach
    if schedule is not None:
        wire["schedule"] = schedule
    entry: dict[str, object] = {
        "work_record_ref": intervention_reference(
            work_ref(), predecessor_id
        ).to_dict(),
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    wire["supersedes"] = [entry]
    wire["created_at"] = updated_at
    wire["created_by"] = AGENT
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("intervention", "1", wire)


def test_intervention_correction_supersedes_exact_predecessor(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Use the corrected structured intervention routine.",
    )
    service.correct(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_int_slice8c_corrected",
        operation_id="op_int_slice8c_corrected",
    )
    predecessor = service.load_exact(
        intervention_reference(work_ref(), "int_alpha")
    )
    accepted = service.require_current_use(
        intervention_reference(work_ref(), "int_beta")
    )
    assert predecessor.record.status == "superseded"
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "active"


def test_intervention_correction_records_reason_on_lifecycle_transition(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="monitoring_corrected",
        monitoring_approach="Use the corrected planned weekly monitoring check.",
    )
    service.correct(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_int_slice8c_monitoring",
        operation_id="op_int_slice8c_monitoring",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_int_slice8c_monitoring",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "monitoring_corrected",
    }


def test_intervention_correction_can_replace_proposed_planning_record(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Still planning provider assignment.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    successor = _intervention_successor(
        created.record,
        reason="monitoring_corrected",
        monitoring_approach="Correct the proposed monitoring approach.",
    )
    service.correct(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_int_slice8c_proposed",
        operation_id="op_int_slice8c_proposed",
    )
    assert service.load_exact(
        intervention_reference(work_ref(), "int_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        intervention_reference(work_ref(), "int_beta")
    ).record.status == "proposed"


def test_intervention_correction_rejects_plan_adapted_reason(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="plan_adapted",
        strategy_procedure="Prospectively adapt the intervention.",
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="requires Intervention adapt",
    ):
        service.correct(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_wrong_api",
            operation_id="op_int_slice8c_wrong_api",
        )


def test_intervention_correction_requires_new_identity(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        intervention_id="int_alpha",
        reason="strategy_corrected",
        strategy_procedure="Correct the intervention strategy.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="new canonical identity"):
        service.correct(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_same_id",
            operation_id="op_int_slice8c_same_id",
        )


def test_intervention_correction_reason_must_match_corrected_fact(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="schedule_corrected",
        monitoring_approach="Only the monitoring approach changed.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_reason_mismatch",
            operation_id="op_int_slice8c_reason_mismatch",
        )


def test_intervention_correction_cannot_smuggle_plan_state_progression(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Correct without changing operational state.",
        plan_state="paused",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="plan_state progression"):
        service.correct(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_plan_state",
            operation_id="op_int_slice8c_plan_state",
        )


def test_intervention_adaptation_creates_plan_adapted_successor(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="plan_adapted",
        strategy_procedure="Use the prospectively adapted intervention routine.",
    )
    service.adapt(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_int_slice8c_adapted",
        operation_id="op_int_slice8c_adapted",
    )
    accepted = service.require_current_use(
        intervention_reference(work_ref(), "int_beta")
    )
    assert accepted.record.field("plan_state") == "active"
    transition = service.repository.load_work_record(
        work_ref(), "lifecycle_transition", "1", "lct_int_slice8c_adapted"
    )
    assert transition.record.field("reason") == {
        "category": "workflow",
        "code": "plan_adapted",
    }


def test_intervention_adaptation_rejects_proposed_predecessor(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    SupportGoalWorkflowService(tmp_path).create(
        work_ref(), goal_record(status="proposed")
    )
    service = InterventionWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        intervention_record(
            status="proposed",
            plan_state="planned",
            provider_plan={
                "kind": "no_assigned_provider",
                "reason": "other",
                "detail": "Still planning provider assignment.",
            },
            schedule={"kind": "as_needed"},
        ),
    )
    successor = _intervention_successor(
        created.record,
        reason="plan_adapted",
        monitoring_approach="Change future monitoring.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active predecessor"):
        service.adapt(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_proposed_adapt",
            operation_id="op_int_slice8c_proposed_adapt",
        )


def test_intervention_adaptation_rejects_terminal_plan_state(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    completed = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            created.record,
            plan_state="completed",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    successor = _intervention_successor(
        completed.record,
        reason="plan_adapted",
        monitoring_approach="Terminal plans cannot be prospectively adapted.",
        updated_at=SUCCESSOR_UPDATE_2,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="terminal Intervention"):
        service.adapt(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=completed.fingerprint,
            transition_id="lct_int_slice8c_terminal_adapt",
            operation_id="op_int_slice8c_terminal_adapt",
        )


def test_intervention_adaptation_requires_material_plan_change(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="plan_adapted",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="material plan change"):
        service.adapt(
            intervention_reference(work_ref(), "int_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_int_slice8c_no_change",
            operation_id="op_int_slice8c_no_change",
        )


def test_paused_intervention_may_be_adapted_without_resuming(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    paused = service.transition_plan_state(
        intervention_reference(work_ref(), "int_alpha"),
        _intervention_revision(
            created.record,
            plan_state="paused",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    successor = _intervention_successor(
        paused.record,
        reason="plan_adapted",
        monitoring_approach="Use an adapted monitoring approach while paused.",
        updated_at=SUCCESSOR_UPDATE_2,
    )
    service.adapt(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=paused.fingerprint,
        transition_id="lct_int_slice8c_paused_adapt",
        operation_id="op_int_slice8c_paused_adapt",
    )
    accepted = service.require_current_use(
        intervention_reference(work_ref(), "int_beta")
    )
    assert accepted.record.field("plan_state") == "paused"


def test_intervention_exact_predecessor_remains_historical_after_supersession(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = InterventionWorkflowService(tmp_path)
    created = service.create(work_ref(), intervention_record())
    successor = _intervention_successor(
        created.record,
        reason="monitoring_corrected",
        monitoring_approach="Correct historical planning metadata.",
    )
    service.correct(
        intervention_reference(work_ref(), "int_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_int_slice8c_exact_history",
        operation_id="op_int_slice8c_exact_history",
    )
    historical = service.load_exact(
        intervention_reference(work_ref(), "int_alpha")
    )
    assert historical.record.status == "superseded"
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(
            intervention_reference(work_ref(), "int_alpha")
        )
