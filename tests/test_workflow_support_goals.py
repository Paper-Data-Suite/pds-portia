"""Focused Slice 6 tests for Support Goal application authority."""

from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    support_goal_reference,
    support_process_participant_reference,
)

TIMESTAMP = "2026-08-31T10:00:00-04:00"
PARTICIPANT_UPDATED = "2026-08-31T10:05:00-04:00"
ROOT_UPDATED = "2026-08-31T10:10:00-04:00"
GOAL_CREATED = "2026-08-31T10:15:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue44_slice6_test"}


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


def goal_record(
    *,
    goal_id: str = "spg_alpha",
    status: str = "active",
    target: dict[str, object] | None = None,
    source: dict[str, object] | None = None,
    planned_criteria: str | None = "Synthetic criteria for later review.",
    measurement_approach: str | None = "Synthetic later-review approach.",
    updated_at: str = GOAL_CREATED,
) -> PortiaRecord:
    wire: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support_goal",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "sup_alpha",
        "goal_id": goal_id,
        "status": status,
        "target": target or {"kind": "support_process"},
        "description": "Synthetic bounded future support objective.",
        "creation_source": source or {"type": "digital_entry"},
        "created_at": GOAL_CREATED,
        "created_by": AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if planned_criteria is not None:
        wire["planned_criteria"] = planned_criteria
    if measurement_approach is not None:
        wire["measurement_approach"] = measurement_approach
    return parse_portia_record("support_goal", "1", wire)


def participant_target(participant_id: str) -> dict[str, object]:
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": participant_id,
            "contract_version": "1",
        },
    }


def participant_set_target(*participant_ids: str) -> dict[str, object]:
    return {
        "kind": "support_process_participants",
        "targets": [participant_target(value) for value in participant_ids],
    }


def _active_process(tmp_path: Path) -> tuple[SupportProcessWorkflowService, object]:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = participant_service.create(work_ref(), participant_record())
    active_participant = participant_record(
        status="active",
        updated_at=PARTICIPANT_UPDATED,
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work_ref(), "spp_alpha"),
        active_participant,
        expected=participant.fingerprint,
        transition_id="lct_spp_slice6_active",
        reason_code="planning_confirmed",
        operation_id="op_spp_slice6_active",
    )
    active_root = root_record(status="active", updated_at=ROOT_UPDATED)
    root_service.transition_lifecycle(
        work_ref(),
        active_root,
        expected=root.fingerprint,
        transition_id="lct_sup_slice6_active",
        reason_code="planning_confirmed",
        operation_id="op_sup_slice6_active",
    )
    return root_service, participant_service


def test_reference_is_exact_support_process_local_goal() -> None:
    reference = support_goal_reference(work_ref(), "spg_alpha")
    assert reference.work_ref == work_ref()
    assert reference.record_ref.record_kind == "support_goal"
    assert reference.record_ref.record_id == "spg_alpha"
    assert reference.record_ref.contract_version == "1"


def test_reference_rejects_event_owner() -> None:
    wrong = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )
    with pytest.raises(WorkflowOwnershipError, match="support_process@1"):
        support_goal_reference(wrong, "spg_alpha")


def test_proposed_goal_can_be_authored_while_process_is_planning(
    tmp_path: Path,
) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    assert created.record.status == "proposed"
    loaded = service.load_exact(support_goal_reference(work_ref(), "spg_alpha"))
    assert loaded.record == created.record


def test_fresh_goal_cannot_begin_invalidated(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="begin proposed or active"):
        service.create(work_ref(), goal_record(status="invalidated"))


def test_updated_at_cannot_precede_created_at(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="cannot precede created_at"):
        service.create(
            work_ref(),
            goal_record(status="proposed", updated_at="2026-08-31T10:14:00-04:00"),
        )


def test_import_candidate_is_not_materialized_by_digital_authoring(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    imported = goal_record(
        status="proposed",
        source={"type": "import", "source_label": "Synthetic historical import"},
    )
    with pytest.raises(WorkflowPrerequisiteError, match="digital_entry only"):
        service.create(work_ref(), imported)


def test_fresh_goal_cannot_establish_supersession_history(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    wire = goal_record(status="proposed").to_dict()
    wire["supersedes"] = [
        {
            "work_record_ref": support_goal_reference(
                work_ref(), "spg_predecessor"
            ).to_dict(),
            "reason": "description_corrected",
        }
    ]
    candidate = parse_portia_record("support_goal", "1", wire)
    with pytest.raises(WorkflowPrerequisiteError, match="supersession history"):
        SupportGoalWorkflowService(tmp_path).create(work_ref(), candidate)


def test_active_whole_process_goal_requires_current_process(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.create(work_ref(), goal_record())


def test_active_whole_process_goal_is_current_qualified(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    current = service.require_current_use(
        support_goal_reference(work_ref(), "spg_alpha")
    )
    assert current.fingerprint == created.fingerprint
    assert current.record.field("target") == {"kind": "support_process"}


def test_active_participant_target_resolves_exact_current_participant(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        goal_record(target=participant_target("spp_alpha")),
    )
    assert created.record.field("target") == participant_target("spp_alpha")
    assert service.require_current_use(
        support_goal_reference(work_ref(), "spg_alpha")
    ).record == created.record


def test_unresolved_participant_target_is_rejected(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="does not resolve"):
        service.create(
            work_ref(),
            goal_record(target=participant_target("spp_missing")),
        )


def test_active_goal_rejects_noncurrent_participant_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_planned",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="not active for current use"):
        service.create(
            work_ref(),
            goal_record(target=participant_target("spp_planned")),
        )


def test_proposed_goal_may_pin_existing_proposed_participant(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    SupportProcessParticipantWorkflowService(tmp_path).create(
        work_ref(), participant_record()
    )
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        goal_record(status="proposed", target=participant_target("spp_alpha")),
    )
    assert created.record.status == "proposed"


def test_participant_set_target_accepts_distinct_logical_people(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(work_ref(), participant_record("spp_alpha"))
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_beta",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        goal_record(
            status="proposed",
            target=participant_set_target("spp_alpha", "spp_beta"),
        ),
    )
    assert created.record.logical_id == "spg_alpha"


def test_participant_set_rejects_two_records_for_same_logical_person(
    tmp_path: Path,
) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root_service.create(root_record())
    same_person = {"kind": "local_operator", "display_label": "Synthetic operator"}
    first = participant_record("spp_alpha", person=same_person)
    second = participant_record(
        "spp_alias",
        person=same_person,
        contexts=[{"kind": "provider_or_collaborator"}],
    )
    root_service.repository.create_work_record(work_ref(), first)
    root_service.repository.create_work_record(work_ref(), second)
    service = SupportGoalWorkflowService(tmp_path)
    with pytest.raises(WorkflowPrerequisiteError, match="repeats a logical"):
        service.create(
            work_ref(),
            goal_record(
                status="proposed",
                target=participant_set_target("spp_alpha", "spp_alias"),
            ),
        )


def test_multiple_distinct_goals_may_address_same_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    target = participant_target("spp_alpha")
    service.create(work_ref(), goal_record(goal_id="spg_access", target=target))
    service.create(
        work_ref(),
        goal_record(
            goal_id="spg_routine",
            target=target,
            planned_criteria="Synthetic second-goal review criteria.",
        ),
    )
    assert {item.record.logical_id for item in service.list(work_ref())} == {
        "spg_access",
        "spg_routine",
    }


def test_planning_fields_are_preserved_without_attainment_semantics(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    assert created.record.field("planned_criteria") == (
        "Synthetic criteria for later review."
    )
    assert created.record.field("measurement_approach") == (
        "Synthetic later-review approach."
    )


def test_goal_may_omit_planning_criteria_and_measurement(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        goal_record(
            status="proposed",
            planned_criteria=None,
            measurement_approach=None,
        ),
    )
    assert created.record.field("planned_criteria") is None
    assert created.record.field("measurement_approach") is None


def test_current_use_requires_active_goal(tmp_path: Path) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    service.create(work_ref(), goal_record(status="proposed"))
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical status"):
        service.require_current_use(support_goal_reference(work_ref(), "spg_alpha"))


def test_current_use_rejects_lifecycle_head_disagreement(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    transition = parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "sup_alpha",
            "transition_id": "lct_spg_mismatch",
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": "support_goal",
                    "record_id": "spg_alpha",
                    "contract_version": "1",
                },
            },
            "previous_transition": None,
            "from_status": "proposed",
            "to_status": "invalidated",
            "reason": {"category": "record_validity", "code": "recording_error"},
            "effective_at": GOAL_CREATED,
            "creation_source": {"type": "digital_entry"},
            "created_at": GOAL_CREATED,
            "created_by": AGENT,
        },
    )
    service.repository.create_work_record(work_ref(), transition)
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_current_use(
            support_goal_reference(work_ref(), created.record.logical_id or "missing")
        )


def test_exact_read_does_not_follow_lifecycle_or_successor_state(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    exact = service.resolve_exact(support_goal_reference(work_ref(), "spg_alpha"))
    assert exact.fingerprint == created.fingerprint
    assert exact.record.status == "proposed"


# Slice 9c — Support Goal lifecycle mutation and correction.
GOAL_UPDATE_1 = "2026-08-31T10:20:00-04:00"
GOAL_UPDATE_2 = "2026-08-31T10:25:00-04:00"


def _goal_revision(
    prior: PortiaRecord,
    *,
    status: str,
    updated_at: str = GOAL_UPDATE_1,
    description: str | None = None,
) -> PortiaRecord:
    wire = prior.to_dict()
    wire["status"] = status
    if description is not None:
        wire["description"] = description
    wire["updated_at"] = updated_at
    wire["updated_by"] = AGENT
    return parse_portia_record("support_goal", "1", wire)


def _goal_successor(
    prior: PortiaRecord,
    *,
    goal_id: str = "spg_beta",
    reason: str,
    detail: str | None = None,
    description: str | None = None,
    target: dict[str, object] | None = None,
    planned_criteria: str | None = None,
    measurement_approach: str | None = None,
    updated_at: str = GOAL_UPDATE_1,
) -> PortiaRecord:
    predecessor_id = prior.logical_id
    assert predecessor_id is not None
    wire = prior.to_dict()
    wire["goal_id"] = goal_id
    if description is not None:
        wire["description"] = description
    if target is not None:
        wire["target"] = target
    if planned_criteria is not None:
        wire["planned_criteria"] = planned_criteria
    if measurement_approach is not None:
        wire["measurement_approach"] = measurement_approach
    entry: dict[str, object] = {
        "work_record_ref": support_goal_reference(
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
    return parse_portia_record("support_goal", "1", wire)


def test_goal_lifecycle_activation_persists_transition_and_current_use(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    candidate = _goal_revision(created.record, status="active")
    service.transition_lifecycle(
        support_goal_reference(work_ref(), "spg_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_active",
        reason_code="planning_confirmed",
        operation_id="op_spg_slice9c_active",
    )
    accepted = service.require_current_use(
        support_goal_reference(work_ref(), "spg_alpha")
    )
    assert accepted.record.status == "active"
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spg_slice9c_active",
    )
    assert transition.record.field("from_status") == "proposed"
    assert transition.record.field("to_status") == "active"


def test_goal_lifecycle_activation_requires_current_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_pending",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(
        work_ref(),
        goal_record(
            status="proposed",
            target=participant_target("spp_pending"),
        ),
    )
    candidate = _goal_revision(created.record, status="active")
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="not active for current use",
    ):
        service.transition_lifecycle(
            support_goal_reference(work_ref(), "spg_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_pending_target",
            reason_code="planning_confirmed",
            operation_id="op_spg_slice9c_pending_target",
        )


def test_goal_lifecycle_cannot_rewrite_description(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    candidate = _goal_revision(
        created.record,
        status="active",
        description="This substantive rewrite is not a lifecycle change.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="description"):
        service.transition_lifecycle(
            support_goal_reference(work_ref(), "spg_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_rewrite",
            reason_code="planning_confirmed",
            operation_id="op_spg_slice9c_rewrite",
        )


def test_goal_lifecycle_invalidation_removes_current_use(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    candidate = _goal_revision(created.record, status="invalidated")
    service.transition_lifecycle(
        support_goal_reference(work_ref(), "spg_alpha"),
        candidate,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_invalidated",
        reason_code="recording_error",
        operation_id="op_spg_slice9c_invalidated",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(
            support_goal_reference(work_ref(), "spg_alpha")
        )


def test_goal_lifecycle_supersession_is_reserved_for_correction(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    candidate = _goal_revision(created.record, status="superseded")
    with pytest.raises(WorkflowPrerequisiteError, match="correction workflow"):
        service.transition_lifecycle(
            support_goal_reference(work_ref(), "spg_alpha"),
            candidate,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_superseded",
            reason_code="recording_error",
            operation_id="op_spg_slice9c_superseded",
        )


def test_goal_correction_supersedes_exact_predecessor_and_qualifies_successor(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="description_corrected",
        description="Corrected bounded future support objective.",
    )
    service.correct(
        support_goal_reference(work_ref(), "spg_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_corrected",
        operation_id="op_spg_slice9c_corrected",
    )
    predecessor = service.load_exact(
        support_goal_reference(work_ref(), "spg_alpha")
    )
    accepted = service.require_current_use(
        support_goal_reference(work_ref(), "spg_beta")
    )
    assert predecessor.record.status == "superseded"
    assert accepted.record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="active canonical"):
        service.require_current_use(
            support_goal_reference(work_ref(), "spg_alpha")
        )


def test_goal_correction_records_criteria_reason_on_transition(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="criteria_corrected",
        planned_criteria="Corrected criteria for a later review.",
    )
    service.correct(
        support_goal_reference(work_ref(), "spg_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_criteria",
        operation_id="op_spg_slice9c_criteria",
    )
    transition = service.repository.load_work_record(
        work_ref(),
        "lifecycle_transition",
        "1",
        "lct_spg_slice9c_criteria",
    )
    assert transition.record.field("reason") == {
        "category": "correction",
        "code": "criteria_corrected",
    }


def test_goal_measurement_approach_correction_is_planning_only(
    tmp_path: Path,
) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="measurement_approach_corrected",
        measurement_approach="Corrected planned later-review observation approach.",
    )
    service.correct(
        support_goal_reference(work_ref(), "spg_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_measurement",
        operation_id="op_spg_slice9c_measurement",
    )
    accepted = service.require_current_use(
        support_goal_reference(work_ref(), "spg_beta")
    )
    assert accepted.record.field("measurement_approach") == (
        "Corrected planned later-review observation approach."
    )


def test_goal_correction_can_replace_proposed_planning_record(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(root_record())
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record(status="proposed"))
    successor = _goal_successor(
        created.record,
        reason="description_corrected",
        description="Corrected proposed Goal description.",
    )
    service.correct(
        support_goal_reference(work_ref(), "spg_alpha"),
        successor,
        expected=created.fingerprint,
        transition_id="lct_spg_slice9c_proposed",
        operation_id="op_spg_slice9c_proposed",
    )
    assert service.load_exact(
        support_goal_reference(work_ref(), "spg_alpha")
    ).record.status == "superseded"
    assert service.load_exact(
        support_goal_reference(work_ref(), "spg_beta")
    ).record.status == "proposed"


def test_goal_correction_requires_new_identity(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        goal_id="spg_alpha",
        reason="description_corrected",
        description="Corrected Goal under an invalid reused identity.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="new canonical identity"):
        service.correct(
            support_goal_reference(work_ref(), "spg_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_same_id",
            operation_id="op_spg_slice9c_same_id",
        )


def test_goal_correction_reason_must_match_corrected_fact(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="criteria_corrected",
        description="Only the description actually changed.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        service.correct(
            support_goal_reference(work_ref(), "spg_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_reason_mismatch",
            operation_id="op_spg_slice9c_reason_mismatch",
        )


def test_active_goal_correction_revalidates_current_target(tmp_path: Path) -> None:
    _active_process(tmp_path)
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant_service.create(
        work_ref(),
        participant_record(
            "spp_pending",
            contexts=[{"kind": "provider_or_collaborator"}],
        ),
    )
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="target_corrected",
        target=participant_target("spp_pending"),
    )
    with pytest.raises(
        WorkflowPrerequisiteError,
        match="not active for current use",
    ):
        service.correct(
            support_goal_reference(work_ref(), "spg_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_stale_target",
            operation_id="op_spg_slice9c_stale_target",
        )


def test_goal_reserved_topology_reason_fails_closed(tmp_path: Path) -> None:
    _active_process(tmp_path)
    service = SupportGoalWorkflowService(tmp_path)
    created = service.create(work_ref(), goal_record())
    successor = _goal_successor(
        created.record,
        reason="duplicate_consolidated",
        description="A topology-heavy reason must use its dedicated path.",
    )
    with pytest.raises(WorkflowPrerequisiteError, match="dedicated topology path"):
        service.correct(
            support_goal_reference(work_ref(), "spg_alpha"),
            successor,
            expected=created.fingerprint,
            transition_id="lct_spg_slice9c_reserved",
            operation_id="op_spg_slice9c_reserved",
        )
