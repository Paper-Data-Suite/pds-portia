"""Focused Issue #50 Slice 8 tests for Intervention / Implementation / Fidelity menu work."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from portia.menu import support as support_menu
from portia.menu.authoring import (
    FidelityAuthoringInput,
    HumanAttributionInput,
    ImplementationAuthoringInput,
    InterventionAuthoringInput,
    SupportGoalAuthoringInput,
    SupportNeedAuthoringInput,
    SupportParticipantAuthoringInput,
    SupportParticipantContextInput,
    SupportPlanTargetInput,
    SupportProcessAuthoringInput,
    SupportScheduleInput,
    prepare_fidelity,
    prepare_implementation,
    prepare_intervention,
    prepare_support_goal,
    prepare_support_need,
    prepare_support_participant,
    prepare_support_participant_activation,
    prepare_support_process,
    prepare_support_process_activation,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    FidelityWorkflowService,
    ImplementationWorkflowService,
    InterventionWorkflowService,
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    fidelity_reference,
    implementation_reference,
    intervention_reference,
    support_process_participant_reference,
)

FIXED_NOW = datetime(2026, 9, 24, 16, 0, tzinfo=timezone.utc)


def _clock() -> MenuClock:
    return MenuClock(lambda: FIXED_NOW)


def _ids() -> PortiaIdGenerator:
    counter = iter(range(1, 100))
    return PortiaIdGenerator(lambda: f"slice8token{next(counter)}")


def _work(
    class_id: str = "class_a",
    work_id: str = "sup_slice8",
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def test_prepare_active_intervention_keeps_plan_distinct_from_delivery() -> None:
    record = prepare_intervention(
        InterventionAuthoringInput(
            work=_work(),
            status="active",
            target=SupportPlanTargetInput(
                kind="support_process_participant",
                participant_id="spp_student",
            ),
            need_ids=("spn_need",),
            goal_ids=("spg_goal",),
            strategy_kind="skill_building",
            procedure="Use a bounded structured practice routine.",
            strategy_detail=None,
            provider_participant_ids=("spp_provider",),
            no_provider_reason=None,
            no_provider_detail=None,
            schedule=SupportScheduleInput(
                kind="recurring",
                planned_minutes=10,
                occurrences=2,
                interval_count=1,
                interval_unit="week",
            ),
            monitoring_approach="Review later implementation records.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=_ids(),
    )

    assert record.status == "active"
    assert record.field("plan_state") == "active"
    assert record.field("provider_plan") == {
        "kind": "assigned",
        "participant_refs": (
            {
                "record_kind": "support_process_participant",
                "record_id": "spp_provider",
                "contract_version": "1",
            },
        ),
    }
    assert record.contract == "intervention"
    assert record.field("monitoring_approach") == "Review later implementation records."


def test_prepare_implementation_records_actual_occurrence_and_variation() -> None:
    record = prepare_implementation(
        ImplementationAuthoringInput(
            work=_work(),
            plan_kind="intervention",
            plan_id="int_plan",
            actual_target=SupportPlanTargetInput(
                kind="support_process_participant",
                participant_id="spp_student",
            ),
            provider_participant_ids=("spp_provider",),
            no_human_provider_reason=None,
            no_human_provider_detail=None,
            execution_state="completed",
            started_at=ExplicitOffsetTimestamp("2026-09-24T11:00:00-04:00"),
            ended_at=ExplicitOffsetTimestamp("2026-09-24T11:10:00-04:00"),
            variation_kinds=("timing_or_duration",),
            variation_detail="The occurrence lasted longer than planned.",
            summary="Completed the bounded planned routine.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=_ids(),
    )

    assert record.status == "active"
    assert record.contract == "implementation"
    assert record.field("execution_state") == "completed"
    assert record.field("variation") == {
        "kinds": ("timing_or_duration",),
        "detail": "The occurrence lasted longer than planned.",
    }
    assert record.field("plan_ref") == {
        "record_kind": "intervention",
        "record_id": "int_plan",
        "contract_version": "1",
    }


def test_prepare_fidelity_is_plan_adherence_not_outcome() -> None:
    record = prepare_fidelity(
        FidelityAuthoringInput(
            work=_work(),
            plan_kind="intervention",
            plan_id="int_plan",
            evaluator_participant_id="spp_evaluator",
            implementation_id="imp_occurrence",
            result="partially_as_planned",
            basis_kind="implementation_records",
            basis_detail=None,
            include_implementation_basis=True,
            evaluated_at=ExplicitOffsetTimestamp("2026-09-24T11:30:00-04:00"),
            summary="Most planned elements were present; one planned step differed.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=_ids(),
    )

    assert record.status == "active"
    assert record.contract == "fidelity"
    assert record.field("result") == "partially_as_planned"
    assert record.field("scope") == {
        "kind": "one_implementation",
        "implementation_ref": {
            "record_kind": "implementation",
            "record_id": "imp_occurrence",
            "contract_version": "1",
        },
    }
    assert record.field("outcome") is None


def _activate_participant(
    tmp_path,
    work,
    *,
    ids: PortiaIdGenerator,
    person_label: str,
    context: str,
):
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    participant = prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=work,
            person=HumanAttributionInput(
                kind="descriptive_person",
                display_label=person_label,
                description_type="school_staff" if context != "supported_person" else "outside_student",
            ),
            contexts=(SupportParticipantContextInput(kind=context),),
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    created = participant_service.create(work, participant)
    prepared = prepare_support_participant_activation(
        participant,
        local_operator_label="Teacher",
        clock=_clock(),
        ids=ids,
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work, participant.logical_id),
        prepared.candidate,
        expected=created.fingerprint,
        transition_id=prepared.transition_id,
        reason_code="planning_confirmed",
        operation_id=prepared.operation_id,
    )
    return participant.logical_id


def test_slice8_candidates_execute_through_canonical_services(tmp_path) -> None:
    ids = _ids()
    root_service = SupportProcessWorkflowService(tmp_path)
    root = prepare_support_process(
        SupportProcessAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            summary="Slice 8 support process",
            initiation_detail="Teacher identified a bounded support-planning need.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    created_root = root_service.create(root)
    work = _work(work_id=root.work_id)

    student_id = _activate_participant(
        tmp_path,
        work,
        ids=ids,
        person_label="Synthetic learner",
        context="supported_person",
    )
    root_activation = prepare_support_process_activation(
        root,
        local_operator_label="Teacher",
        clock=_clock(),
        ids=ids,
    )
    root_service.transition_lifecycle(
        work,
        root_activation.candidate,
        expected=created_root.fingerprint,
        transition_id=root_activation.transition_id,
        reason_code="planning_confirmed",
        operation_id=root_activation.operation_id,
    )
    provider_id = _activate_participant(
        tmp_path,
        work,
        ids=ids,
        person_label="Synthetic provider",
        context="provider_or_collaborator",
    )
    evaluator_id = _activate_participant(
        tmp_path,
        work,
        ids=ids,
        person_label="Synthetic evaluator",
        context="observer",
    )

    target = SupportPlanTargetInput(
        kind="support_process_participant",
        participant_id=student_id,
    )
    need = prepare_support_need(
        SupportNeedAuthoringInput(
            work=work,
            status="active",
            target=target,
            need_kind="skill_or_strategy",
            description="Needs a bounded strategy practice opportunity.",
            kind_detail=None,
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    SupportNeedWorkflowService(tmp_path).create(work, need)
    goal = prepare_support_goal(
        SupportGoalAuthoringInput(
            work=work,
            status="active",
            target=target,
            description="Use the selected strategy during a planned practice.",
            planned_criteria="Teacher will later review whether the strategy was used.",
            measurement_approach="Review a later implementation occurrence.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    SupportGoalWorkflowService(tmp_path).create(work, goal)

    intervention = prepare_intervention(
        InterventionAuthoringInput(
            work=work,
            status="active",
            target=target,
            need_ids=(need.logical_id,),
            goal_ids=(goal.logical_id,),
            strategy_kind="skill_building",
            procedure="Run one structured strategy-practice routine.",
            strategy_detail=None,
            provider_participant_ids=(provider_id,),
            no_provider_reason=None,
            no_provider_detail=None,
            schedule=SupportScheduleInput(
                kind="recurring",
                planned_minutes=10,
                occurrences=1,
                interval_count=1,
                interval_unit="week",
            ),
            monitoring_approach="Review the occurrence record after implementation.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    created_intervention = InterventionWorkflowService(tmp_path).create(
        work, intervention
    )

    implementation = prepare_implementation(
        ImplementationAuthoringInput(
            work=work,
            plan_kind="intervention",
            plan_id=intervention.logical_id,
            actual_target=target,
            provider_participant_ids=(provider_id,),
            no_human_provider_reason=None,
            no_human_provider_detail=None,
            execution_state="completed",
            started_at=ExplicitOffsetTimestamp("2026-09-24T11:00:00-04:00"),
            ended_at=ExplicitOffsetTimestamp("2026-09-24T11:10:00-04:00"),
            variation_kinds=(),
            variation_detail=None,
            summary="Completed one documented strategy-practice occurrence.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    created_implementation = ImplementationWorkflowService(tmp_path).create(
        work, implementation
    )

    fidelity = prepare_fidelity(
        FidelityAuthoringInput(
            work=work,
            plan_kind="intervention",
            plan_id=intervention.logical_id,
            evaluator_participant_id=evaluator_id,
            implementation_id=implementation.logical_id,
            result="as_planned",
            basis_kind="implementation_records",
            basis_detail=None,
            include_implementation_basis=True,
            evaluated_at=ExplicitOffsetTimestamp("2026-09-24T11:30:00-04:00"),
            summary="The documented occurrence matched the selected plan.",
            local_operator_label="Teacher",
        ),
        clock=_clock(),
        ids=ids,
    )
    created_fidelity = FidelityWorkflowService(tmp_path).create(work, fidelity)

    assert InterventionWorkflowService(tmp_path).load_exact(
        intervention_reference(work, intervention.logical_id)
    ).fingerprint == created_intervention.fingerprint
    assert ImplementationWorkflowService(tmp_path).load_exact(
        implementation_reference(work, implementation.logical_id)
    ).fingerprint == created_implementation.fingerprint
    assert FidelityWorkflowService(tmp_path).load_exact(
        fidelity_reference(work, fidelity.logical_id)
    ).fingerprint == created_fidelity.fingerprint


def test_open_process_menu_routes_delivery_actions(monkeypatch) -> None:
    called: list[str] = []
    state = MenuSessionContext()
    process = SimpleNamespace(
        summary="Synthetic process",
        status="active",
        workflow_state="planning",
    )
    choices = iter(("9", "10", "11", "12", "b"))

    monkeypatch.setattr("builtins.input", lambda _prompt="": next(choices))
    monkeypatch.setattr(support_menu, "clear_screen", lambda: None)
    monkeypatch.setattr(support_menu, "print_menu_header", lambda _title: None)
    monkeypatch.setattr(support_menu, "print_navigation", lambda: None)
    monkeypatch.setattr(support_menu, "pause_for_user", lambda: None)
    monkeypatch.setattr(
        support_menu,
        "record_intervention_once",
        lambda _state, _process: called.append("intervention"),
    )
    monkeypatch.setattr(
        support_menu,
        "record_implementation_once",
        lambda _state, _process: called.append("implementation"),
    )
    monkeypatch.setattr(
        support_menu,
        "record_fidelity_once",
        lambda _state, _process: called.append("fidelity"),
    )
    monkeypatch.setattr(
        support_menu,
        "view_delivery_records_once",
        lambda _state, _process: called.append("view"),
    )

    support_menu._open_process_menu(state, process)  # type: ignore[arg-type]

    assert called == ["intervention", "implementation", "fidelity", "view"]
