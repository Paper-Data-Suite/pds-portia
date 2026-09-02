"""Focused Slice 7a tests for Support planning creation and dependency authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    support_process_participant_reference,
    support_reference,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-08-31T10:05:00-04:00"
ROOT_UPDATED = "2026-08-31T10:10:00-04:00"
PLAN_CREATED = "2026-08-31T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice7a_test"}


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


def need_record(
    *,
    need_id: str = "spn_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "support_need",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_need",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "need_id": need_id,
            "status": status,
            "target": target or participant_target(),
            "need_kind": "access",
            "description": "Synthetic bounded access need.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def goal_record(
    *,
    goal_id: str = "spg_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "support_goal",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_goal",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "goal_id": goal_id,
            "status": status,
            "target": target or participant_target(),
            "description": "Synthetic bounded future support objective.",
            "creation_source": {"type": "digital_entry"},
            "created_at": PLAN_CREATED,
            "created_by": AGENT,
            "updated_at": PLAN_CREATED,
            "updated_by": AGENT,
        },
    )


def support_record(
    *,
    support_id: str = "spt_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    need_ids: tuple[str, ...] = ("spn_alpha",),
    goal_ids: tuple[str, ...] = (),
    provider_plan: dict[str, object] | None = None,
    schedule: dict[str, object] | None = None,
    plan_state: str = "active",
    source: dict[str, object] | None = None,
    updated_at: str = PLAN_CREATED,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "support_id": support_id,
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
        "strategy": {
            "kind": "access",
            "procedure": "Provide the synthetic planned classroom access condition.",
        },
        "provider_plan": provider_plan
        or {
            "kind": "no_assigned_provider",
            "reason": "access_condition",
        },
        "schedule": schedule
        or {
            "kind": "as_needed",
            "planned_duration": {"kind": "minutes", "minutes": 5},
        },
        "plan_state": plan_state,
        "creation_source": source or {"type": "digital_entry"},
        "created_at": PLAN_CREATED,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if goal_ids:
        wire["goal_refs"] = [
            {
                "record_kind": "support_goal",
                "record_id": value,
                "contract_version": "1",
            }
            for value in goal_ids
        ]
    return parse_portia_record("support", "1", wire)


def _active_process(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participant_service.create(work_ref(), participant_record())
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_alpha"),
        participant_record(status="active", updated_at=PARTICIPANT_UPDATED),
        expected=participant.fingerprint,
        transition_id="lct_spp_slice7a_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice7a_active",
    )
    root_service.transition_lifecycle(
        work_ref(),
        root_record(status="active", updated_at=ROOT_UPDATED),
        expected=root.fingerprint,
        transition_id="lct_sup_slice7a_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice7a_active",
    )


def _active_dependencies(tmp_path: Path, *, include_goal: bool = False) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(work_ref(), need_record())
    if include_goal:
        SupportGoalWorkflowService(tmp_path).create(work_ref(), goal_record())


def test_reference_is_exact_support_process_local_support() -> None:
    reference = support_reference(work_ref(), "spt_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "support"
    assert reference.record_ref.record_id == "spt_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_event_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        support_reference(wrong, "spt_alpha")


def test_proposed_support_can_be_authored_while_process_is_planning(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    assert created.record.status == "proposed"
    assert service.load_exact(support_reference(work_ref(), "spt_alpha")).record == (
        created.record
    )


def test_fresh_support_cannot_begin_invalidated(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="begin proposed or active"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="invalidated",
                plan_state="planned",
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
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
                updated_at="2026-08-31T10:14:00-04:00",
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
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
                source={
                    "type": "import",
                    "source_label": "Synthetic historical import",
                },
            ),
        )


def test_fresh_support_cannot_establish_supersession_history(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    wire = support_record(status="proposed", plan_state="planned").to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": support_reference(
                work_ref(), "spt_predecessor"
            ).to_dict(),
            "reason": "plan_adapted",
        }
    ]
    candidate = parse_portia_record("support", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="supersession history"):
        SupportWorkflowService(tmp_path).create(work_ref(), candidate)


def test_active_support_requires_current_parent(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        SupportWorkflowService(tmp_path).create(work_ref(), support_record())



def test_active_support_rejects_noncurrent_need(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        SupportWorkflowService(tmp_path).create(work_ref(), support_record())

def test_active_as_needed_support_may_have_no_assigned_provider(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    assert created.record.field("provider_plan") == {
        "kind": "no_assigned_provider",
        "reason": "access_condition",
    }
    assert created.record.field("schedule") == {
        "kind": "as_needed",
        "planned_duration": {"kind": "minutes", "minutes": 5},
    }
    assert service.require_current_use(
        support_reference(work_ref(), "spt_alpha")
    ).record == created.record


def test_optional_goal_linkage_resolves_exact_current_goal(tmp_path: Path) -> None:
    _active_dependencies(tmp_path, include_goal=True)
    created = SupportWorkflowService(tmp_path).create(
        work_ref(),
        support_record(goal_ids=("spg_alpha",)),
    )
    assert created.record.field("goal_refs") == (
        {
            "record_kind": "support_goal",
            "record_id": "spg_alpha",
            "contract_version": "1",
        },
    )



def test_unresolved_target_participant_is_rejected(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(),
        need_record(status="proposed", target={"kind": "support_process"}),
    )
    with pytest.raises(
        WorkflowPrerequisiteError, match="Participant reference does not resolve"
    ):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
                target=participant_target("spp_missing"),
            ),
        )

def test_unresolved_need_is_rejected(tmp_path: Path) -> None:
    _active_process(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="Need ref does not resolve"):
        SupportWorkflowService(tmp_path).create(
            work_ref(), support_record(need_ids=("spn_missing",))
        )


def test_unresolved_goal_is_rejected(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="Goal ref does not resolve"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(goal_ids=("spg_missing",)),
        )


def test_assigned_provider_resolves_exact_current_participant(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    created_provider = participant_service.create(
        work_ref(),
        participant_record(
            "spp_provider",
            contexts=[{"kind": "provider_or_collaborator"}],
            person={"kind": "local_operator", "display_label": "Synthetic provider"},
        ),
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_provider"),
        participant_record(
            "spp_provider",
            status="active",
            contexts=[{"kind": "provider_or_collaborator"}],
            person={"kind": "local_operator", "display_label": "Synthetic provider"},
            updated_at=PARTICIPANT_UPDATED,
        ),
        expected=created_provider.fingerprint,
        transition_id="lct_spp_provider_slice7a_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_provider_slice7a_active",
    )
    support = SupportWorkflowService(tmp_path).create(
        work_ref(),
        support_record(
            provider_plan={
                "kind": "assigned",
                "participant_refs": [
                    {
                        "record_kind": "support_process_participant",
                        "record_id": "spp_provider",
                        "contract_version": "1",
                    }
                ],
            }
        ),
    )
    assert support.record.field("provider_plan") == {
        "kind": "assigned",
        "participant_refs": (
            {
                "record_kind": "support_process_participant",
                "record_id": "spp_provider",
                "contract_version": "1",
            },
        ),
    }


def test_unresolved_provider_is_rejected(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    with pytest.raises(
        WorkflowPrerequisiteError, match="Participant reference does not resolve"
    ):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                provider_plan={
                    "kind": "assigned",
                    "participant_refs": [
                        {
                            "record_kind": "support_process_participant",
                            "record_id": "spp_missing",
                            "contract_version": "1",
                        }
                    ],
                }
            ),
        )


def test_provider_set_rejects_duplicate_logical_person(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(work_ref(), participant_record())
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
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
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
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
    with pytest.raises(WorkflowPrerequisiteError, match="ends_on cannot precede"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
                schedule={
                    "kind": "as_needed",
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
    with pytest.raises(WorkflowPrerequisiteError, match="review_on cannot precede"):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
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
    with pytest.raises(
        WorkflowPrerequisiteError, match="minimum_minutes cannot exceed"
    ):
        SupportWorkflowService(tmp_path).create(
            work_ref(),
            support_record(
                status="proposed",
                plan_state="planned",
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


def test_current_use_requires_active_support(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(support_reference(work_ref(), "spt_alpha"))


def test_exact_read_stays_pinned_to_exact_support(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    exact = service.resolve_exact(support_reference(work_ref(), "spt_alpha"))
    assert exact.fingerprint == created.fingerprint
    assert exact.record.status == "proposed"


def test_list_supports_alias_returns_support_family(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    assert [item.record.logical_id for item in service.list_supports(work_ref())] == [
        "spt_alpha"
    ]


# Slice 7b — Support canonical lifecycle and ordinary plan-state progression.
PLAN_UPDATE_1 = "2026-08-31T10:20:00-04:00"
PLAN_UPDATE_2 = "2026-08-31T10:25:00-04:00"
PLAN_UPDATE_3 = "2026-08-31T10:30:00-04:00"


def _support_revision(
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
    return parse_portia_record("support", "1", wire)


def test_support_lifecycle_activation_persists_transition_and_qualifies_current_use(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    candidate = _support_revision(
        created.record,
        status="active",
        updated_at=PLAN_UPDATE_1,
    )
    service.transition_lifecycle(
        support_reference(work_ref(), "spt_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7b_active",
        reason_code="planning_confirmed",
        operation_id="op_spt_slice7b_active",
    )

    accepted = service.require_current_use(
        support_reference(work_ref(), "spt_alpha")
    )
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "planned"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spt_slice7b_active",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_support_lifecycle_activation_requires_current_need(tmp_path: Path) -> None:
    _active_process(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(),
        need_record(status="proposed"),
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    candidate = _support_revision(
        created.record,
        status="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        service.transition_lifecycle(
            support_reference(work_ref(), "spt_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7b_need_pending",
            reason_code="planning_confirmed",
            operation_id="op_spt_slice7b_need_pending",
        )


def test_support_lifecycle_change_cannot_also_change_plan_state(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    candidate = _support_revision(
        created.record,
        status="active",
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="plan_state"):
        service.transition_lifecycle(
            support_reference(work_ref(), "spt_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7b_mixed_dimension",
            reason_code="planning_confirmed",
            operation_id="op_spt_slice7b_mixed_dimension",
        )


def test_support_lifecycle_invalidation_removes_current_use(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    candidate = _support_revision(
        created.record,
        status="invalidated",
        updated_at=PLAN_UPDATE_1,
    )
    service.transition_lifecycle(
        support_reference(work_ref(), "spt_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7b_invalidated",
        reason_code="recording_error",
        operation_id="op_spt_slice7b_invalidated",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(support_reference(work_ref(), "spt_alpha"))


def test_support_lifecycle_supersession_is_reserved_for_later_successor_path(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    candidate = _support_revision(
        created.record,
        status="superseded",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="correction/adaptation"):
        service.transition_lifecycle(
            support_reference(work_ref(), "spt_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7b_superseded",
            reason_code="planning_confirmed",
            operation_id="op_spt_slice7b_superseded",
        )


def test_support_plan_state_planned_to_active_preserves_identity_and_lifecycle(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record(plan_state="planned"))
    candidate = _support_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    accepted = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        candidate,
        expected=created.fingerprint,
    )
    assert accepted.record.logical_id == "spt_alpha"
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "active"
    support_transitions = [
        stored
        for stored in service.repository.list_work_records(
            work_ref(), "lifecycle_transition", version="1"
        )
        if stored.record.field("target")
        == {
            "kind": "local_record",
            "record_ref": {
                "record_kind": "support",
                "record_id": "spt_alpha",
                "contract_version": "1",
            },
        }
    ]
    assert support_transitions == []


def test_support_plan_state_active_pause_resume_preserves_same_identity(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    paused = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            created.record,
            plan_state="paused",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    resumed = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            paused.record,
            plan_state="active",
            updated_at=PLAN_UPDATE_2,
        ),
        expected=paused.fingerprint,
    )
    assert resumed.record.logical_id == created.record.logical_id
    assert resumed.record.field("plan_state") == "active"


def test_support_plan_state_completed_is_terminal(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    completed = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            created.record,
            plan_state="completed",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="illegal Support plan_state"):
        service.transition_plan_state(
            support_reference(work_ref(), "spt_alpha"),
            _support_revision(
                completed.record,
                plan_state="active",
                updated_at=PLAN_UPDATE_2,
            ),
            expected=completed.fingerprint,
        )


def test_support_plan_state_planned_to_discontinued_is_terminal(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record(plan_state="planned"))
    discontinued = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            created.record,
            plan_state="discontinued",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="illegal Support plan_state"):
        service.transition_plan_state(
            support_reference(work_ref(), "spt_alpha"),
            _support_revision(
                discontinued.record,
                plan_state="active",
                updated_at=PLAN_UPDATE_2,
            ),
            expected=discontinued.fingerprint,
        )


def test_support_plan_state_rejects_planned_to_paused(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record(plan_state="planned"))
    with pytest.raises(WorkflowPrerequisiteError, match="planned -> paused"):
        service.transition_plan_state(
            support_reference(work_ref(), "spt_alpha"),
            _support_revision(
                created.record,
                plan_state="paused",
                updated_at=PLAN_UPDATE_1,
            ),
            expected=created.fingerprint,
        )


def test_support_plan_state_revision_cannot_rewrite_strategy(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record(plan_state="planned"))
    wire = _support_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    ).to_dict()
    wire["strategy"] = {
        "kind": "access",
        "procedure": "Materially different synthetic strategy.",
    }
    candidate = parse_portia_record("support", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="field strategy"):
        service.transition_plan_state(
            support_reference(work_ref(), "spt_alpha"),
            candidate,
            expected=created.fingerprint,
        )


def test_support_plan_state_progression_requires_active_canonical_status(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    candidate = _support_revision(
        created.record,
        plan_state="active",
        updated_at=PLAN_UPDATE_1,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.transition_plan_state(
            support_reference(work_ref(), "spt_alpha"),
            candidate,
            expected=created.fingerprint,
        )


# Slice 7c — Support correction and prospective material adaptation successors.
SUCCESSOR_UPDATE_1 = "2026-08-31T10:35:00-04:00"
SUCCESSOR_UPDATE_2 = "2026-08-31T10:40:00-04:00"


def _support_successor(
    prior: PortiaRecord,
    *,
    support_id: str = "spt_beta",
    reason: str,
    detail: str | None = None,
    strategy_procedure: str | None = None,
    schedule: dict[str, object] | None = None,
    need_ids: tuple[str, ...] | None = None,
    plan_state: str | None = None,
    status: str | None = None,
    updated_at: str = SUCCESSOR_UPDATE_1,
) -> PortiaRecord:
    predecessor_id = prior.logical_id
    assert predecessor_id is not None
    wire = prior.to_dict()
    wire["support_id"] = support_id
    if status is not None:
        wire["status"] = status
    if plan_state is not None:
        wire["plan_state"] = plan_state
    if strategy_procedure is not None:
        strategy = dict(wire["strategy"])
        strategy["procedure"] = strategy_procedure
        wire["strategy"] = strategy
    if schedule is not None:
        wire["schedule"] = schedule
    if need_ids is not None:
        wire["need_refs"] = [
            {
                "record_kind": "support_need",
                "record_id": value,
                "contract_version": "1",
            }
            for value in need_ids
        ]
    entry: dict[str, object] = {
        "work_record_ref": support_reference(
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
    return parse_portia_record("support", "1", wire)


def test_support_correction_supersedes_exact_predecessor_and_qualifies_successor(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Provide the corrected planned access condition.",
    )
    service.correct(
        support_reference(work_ref(), "spt_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7c_corrected",
        operation_id="op_spt_slice7c_corrected",
    )

    predecessor = service.load_exact(support_reference(work_ref(), "spt_alpha"))
    accepted = service.require_current_use(
        support_reference(work_ref(), "spt_beta")
    )
    assert predecessor.record.status == "superseded"
    assert accepted.record.status == "active"
    assert accepted.record.field("plan_state") == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(support_reference(work_ref(), "spt_alpha"))


def test_support_correction_records_reason_on_supersession_transition(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Use the corrected planned strategy.",
    )
    service.correct(
        support_reference(work_ref(), "spt_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7c_reason",
        operation_id="op_spt_slice7c_reason",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spt_slice7c_reason",
    )
    assert transition.record.field("from_status") == "active"
    assert transition.record.field("to_status") == "superseded"
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "strategy_corrected",
    }


def test_support_correction_can_replace_proposed_planning_record(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    successor = _support_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Correct the proposed planning strategy.",
    )
    service.correct(
        support_reference(work_ref(), "spt_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7c_proposed",
        operation_id="op_spt_slice7c_proposed",
    )
    assert service.load_exact(
        support_reference(work_ref(), "spt_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        support_reference(work_ref(), "spt_beta")
    ).record.status == "proposed"


def test_support_correction_rejects_plan_adapted_reason(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="plan_adapted",
        strategy_procedure="Prospectively adapt the strategy.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="requires Support adapt"):
        service.correct(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_wrong_api",
            operation_id="op_spt_slice7c_wrong_api",
        )


def test_support_correction_requires_new_identity(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        support_id="spt_alpha",
        reason="strategy_corrected",
        strategy_procedure="Correct the strategy under a new identity.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="new canonical identity"):
        service.correct(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_same_id",
            operation_id="op_spt_slice7c_same_id",
        )


def test_support_correction_reason_must_match_corrected_fact(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="schedule_corrected",
        strategy_procedure="Only the strategy actually changed.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_reason_mismatch",
            operation_id="op_spt_slice7c_reason_mismatch",
        )


def test_support_correction_cannot_smuggle_plan_state_progression(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="strategy_corrected",
        strategy_procedure="Correct the strategy without state progression.",
        plan_state="paused",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="plan_state progression"):
        service.correct(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_plan_state",
            operation_id="op_spt_slice7c_plan_state",
        )


def test_active_support_correction_revalidates_current_dependencies(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(),
        need_record(need_id="spn_pending", status="proposed"),
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="need_link_corrected",
        need_ids=("spn_pending",),
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active"):
        service.correct(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_stale_need",
            operation_id="op_spt_slice7c_stale_need",
        )


def test_support_adaptation_creates_plan_adapted_successor(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="plan_adapted",
        schedule={
            "kind": "recurring",
            "frequency": {
                "occurrences": 1,
                "interval_count": 1,
                "interval_unit": "day",
            },
            "planned_duration": {"kind": "minutes", "minutes": 10},
        },
    )
    service.adapt(
        support_reference(work_ref(), "spt_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spt_slice7c_adapted",
        operation_id="op_spt_slice7c_adapted",
    )
    current = service.require_current_use(support_reference(work_ref(), "spt_beta"))
    assert current.record.status == "active"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spt_slice7c_adapted",
    )
    assert transition.record.field("reason") == {
        "category": "workflow",
        "code": "plan_adapted",
    }


def test_support_adaptation_rejects_proposed_predecessor(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    SupportNeedWorkflowService(tmp_path).create(
        work_ref(), need_record(status="proposed")
    )
    service = SupportWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        support_record(status="proposed", plan_state="planned"),
    )
    successor = _support_successor(
        created.record,
        reason="plan_adapted",
        strategy_procedure="Prospectively change the proposed plan.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active predecessor"):
        service.adapt(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_proposed_adapt",
            operation_id="op_spt_slice7c_proposed_adapt",
        )


def test_support_adaptation_rejects_terminal_plan_state(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    completed = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            created.record,
            plan_state="completed",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    successor = _support_successor(
        completed.record,
        reason="plan_adapted",
        strategy_procedure="This terminal plan must not be adapted.",
        updated_at=SUCCESSOR_UPDATE_2,
    )
    with pytest.raises(WorkflowPrerequisiteError, match="terminal Support plan_state"):
        service.adapt(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=completed.fingerprint,
            transition_id="lct_spt_slice7c_terminal",
            operation_id="op_spt_slice7c_terminal",
        )


def test_support_adaptation_requires_material_plan_change(tmp_path: Path) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    successor = _support_successor(
        created.record,
        reason="plan_adapted",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="material plan change"):
        service.adapt(
            support_reference(work_ref(), "spt_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spt_slice7c_no_change",
            operation_id="op_spt_slice7c_no_change",
        )


def test_paused_support_may_be_materially_adapted_without_resuming(
    tmp_path: Path,
) -> None:
    _active_dependencies(tmp_path)
    service = SupportWorkflowService(tmp_path)
    created = service.create(work_ref(), support_record())
    paused = service.transition_plan_state(
        support_reference(work_ref(), "spt_alpha"),
        _support_revision(
            created.record,
            plan_state="paused",
            updated_at=PLAN_UPDATE_1,
        ),
        expected=created.fingerprint,
    )
    successor = _support_successor(
        paused.record,
        reason="plan_adapted",
        strategy_procedure="Adapt the paused plan prospectively.",
        updated_at=SUCCESSOR_UPDATE_2,
    )
    service.adapt(
        support_reference(work_ref(), "spt_alpha"),
        successor,
        expected=paused.fingerprint,
        transition_id="lct_spt_slice7c_paused",
        operation_id="op_spt_slice7c_paused",
    )
    accepted = service.require_current_use(support_reference(work_ref(), "spt_beta"))
    assert accepted.record.field("plan_state") == "paused"
