from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from portia.menu.authoring import (
    HumanAttributionInput,
    SupportAuthoringInput,
    SupportGoalAuthoringInput,
    SupportNeedAuthoringInput,
    SupportParticipantAuthoringInput,
    SupportParticipantContextInput,
    SupportPlanTargetInput,
    SupportProcessAuthoringInput,
    SupportScheduleInput,
    prepare_support,
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
from portia.menu.support import SupportProcessOption, record_support_need_once
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.workflows import (
    SupportGoalWorkflowService,
    SupportNeedWorkflowService,
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    SupportWorkflowService,
    support_process_participant_reference,
)

FIXED_NOW = datetime(2026, 9, 24, 5, 0, tzinfo=timezone.utc)


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


def _work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="sup_root",
        work_kind="support_process",
        contract_version="1",
    )


def _root(clock: MenuClock, ids: PortiaIdGenerator):
    return prepare_support_process(
        SupportProcessAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            summary="Teacher-local reading access planning.",
            initiation_detail="Additional reading access may be useful.",
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=ids,
    )


def _participant(clock: MenuClock, ids: PortiaIdGenerator):
    return prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=_work(),
            person=HumanAttributionInput(
                kind="descriptive_person",
                description_type="outside_student",
                display_label="Synthetic learner",
            ),
            contexts=(SupportParticipantContextInput(kind="supported_person"),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=ids,
    )


def _target() -> SupportPlanTargetInput:
    return SupportPlanTargetInput(
        kind="support_process_participant",
        participant_id="spp_learner",
    )


def _activate_process(tmp_path: Path) -> None:
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(_root(MenuClock(lambda: FIXED_NOW), _tokens("root")))
    participant = _participant(MenuClock(lambda: FIXED_NOW), _tokens("learner"))
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    created_participant = participant_service.create(_work(), participant)
    participant_activation = prepare_support_participant_activation(
        participant,
        local_operator_label="Synthetic Teacher",
        clock=MenuClock(lambda: FIXED_NOW + timedelta(minutes=5)),
        ids=_tokens("participant_transition", "participant_operation"),
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(_work(), "spp_learner"),
        participant_activation.candidate,
        expected=created_participant.fingerprint,
        transition_id=participant_activation.transition_id,
        reason_code="planning_confirmed",
        operation_id=participant_activation.operation_id,
    )
    root_activation = prepare_support_process_activation(
        root.record,
        local_operator_label="Synthetic Teacher",
        clock=MenuClock(lambda: FIXED_NOW + timedelta(minutes=10)),
        ids=_tokens("root_transition", "root_operation"),
    )
    root_service.transition_lifecycle(
        _work(),
        root_activation.candidate,
        expected=root.fingerprint,
        transition_id=root_activation.transition_id,
        reason_code="planning_confirmed",
        operation_id=root_activation.operation_id,
    )


def test_prepare_need_goal_and_support_preserve_planning_boundaries() -> None:
    clock = MenuClock(lambda: FIXED_NOW)
    need = prepare_support_need(
        SupportNeedAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            need_kind="access",
            description="Access to a quieter reading location.",
            kind_detail=None,
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("need"),
    )
    goal = prepare_support_goal(
        SupportGoalAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            description="Use the planned reading location when additional access is needed.",
            planned_criteria="Review use during later teacher check-ins.",
            measurement_approach="Use later direct observations and review notes.",
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("goal"),
    )
    support = prepare_support(
        SupportAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            need_ids=("spn_need",),
            goal_ids=("spg_goal",),
            strategy_kind="access",
            procedure="Offer access to the quieter reading location when requested.",
            strategy_detail=None,
            provider_participant_ids=(),
            no_provider_reason="access_condition",
            no_provider_detail=None,
            schedule=SupportScheduleInput(kind="as_needed", planned_minutes=15),
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("support"),
    )

    assert need.logical_id == "spn_need"
    assert need.field("need_kind") == "access"
    assert goal.logical_id == "spg_goal"
    assert goal.field("planned_criteria") == "Review use during later teacher check-ins."
    assert support.logical_id == "spt_support"
    assert support.field("need_refs") == (
        {
            "record_kind": "support_need",
            "record_id": "spn_need",
            "contract_version": "1",
        },
    )
    assert support.field("goal_refs") == (
        {
            "record_kind": "support_goal",
            "record_id": "spg_goal",
            "contract_version": "1",
        },
    )
    assert support.field("schedule") == {
        "kind": "as_needed",
        "planned_duration": {"kind": "minutes", "minutes": 15},
    }
    for record in (need, goal, support):
        data = record.to_dict()
        for field in ("implementation", "fidelity", "follow_up", "outcome"):
            assert field not in data


def test_active_process_persists_need_goal_support_without_downstream_inference(
    tmp_path: Path,
) -> None:
    _activate_process(tmp_path)
    clock = MenuClock(lambda: FIXED_NOW + timedelta(minutes=15))
    need = prepare_support_need(
        SupportNeedAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            need_kind="access",
            description="Access to a quieter reading location.",
            kind_detail=None,
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("need"),
    )
    goal = prepare_support_goal(
        SupportGoalAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            description="Use the planned reading location when useful.",
            planned_criteria=None,
            measurement_approach=None,
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("goal"),
    )
    SupportNeedWorkflowService(tmp_path).create(_work(), need)
    SupportGoalWorkflowService(tmp_path).create(_work(), goal)
    support = prepare_support(
        SupportAuthoringInput(
            work=_work(),
            status="active",
            target=_target(),
            need_ids=("spn_need",),
            goal_ids=("spg_goal",),
            strategy_kind="access",
            procedure="Offer the quieter reading location when requested.",
            strategy_detail=None,
            provider_participant_ids=(),
            no_provider_reason="access_condition",
            no_provider_detail=None,
            schedule=SupportScheduleInput(kind="as_needed"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("support"),
    )
    SupportWorkflowService(tmp_path).create(_work(), support)

    repository = PortiaRepository(tmp_path)
    assert len(repository.list_work_records(_work(), "support_need", version="1")) == 1
    assert len(repository.list_work_records(_work(), "support_goal", version="1")) == 1
    assert len(repository.list_work_records(_work(), "support", version="1")) == 1
    for kind in ("intervention", "implementation", "fidelity", "follow_up", "outcome"):
        assert repository.list_work_records(_work(), kind, version="1") == ()


def test_proposed_process_can_hold_proposed_planning_without_activation(
    tmp_path: Path,
) -> None:
    SupportProcessWorkflowService(tmp_path).create(
        _root(MenuClock(lambda: FIXED_NOW), _tokens("root"))
    )
    participant = _participant(MenuClock(lambda: FIXED_NOW), _tokens("learner"))
    SupportProcessParticipantWorkflowService(tmp_path).create(_work(), participant)
    clock = MenuClock(lambda: FIXED_NOW + timedelta(minutes=5))
    need = prepare_support_need(
        SupportNeedAuthoringInput(
            work=_work(),
            status="proposed",
            target=_target(),
            need_kind="organizational_or_routine",
            description="A consistent reading-start routine may be useful.",
            kind_detail=None,
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("need"),
    )
    goal = prepare_support_goal(
        SupportGoalAuthoringInput(
            work=_work(),
            status="proposed",
            target=_target(),
            description="Begin the reading routine with the planned materials available.",
            planned_criteria=None,
            measurement_approach=None,
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("goal"),
    )
    SupportNeedWorkflowService(tmp_path).create(_work(), need)
    SupportGoalWorkflowService(tmp_path).create(_work(), goal)
    support = prepare_support(
        SupportAuthoringInput(
            work=_work(),
            status="proposed",
            target=_target(),
            need_ids=("spn_need",),
            goal_ids=("spg_goal",),
            strategy_kind="routine_or_structure",
            procedure="Prepare the reading materials before the routine begins.",
            strategy_detail=None,
            provider_participant_ids=(),
            no_provider_reason="self_directed",
            no_provider_detail=None,
            schedule=SupportScheduleInput(
                kind="recurring",
                occurrences=5,
                interval_count=1,
                interval_unit="day",
            ),
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("support"),
    )
    stored = SupportWorkflowService(tmp_path).create(_work(), support)

    assert stored.record.status == "proposed"
    assert stored.record.field("plan_state") == "planned"
    assert SupportProcessWorkflowService(tmp_path).load_exact(_work()).record.status == "proposed"


def test_cancelled_need_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored_root = SupportProcessWorkflowService(tmp_path).create(
        _root(MenuClock(lambda: FIXED_NOW), _tokens("root"))
    )
    process = SupportProcessOption(
        work=_work(),
        stored=stored_root,
        summary="Teacher-local reading access planning.",
        status="proposed",
        workflow_state="planning",
        label="Synthetic",
    )
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    state = MenuSessionContext(local_operator_label="Synthetic Teacher")
    answers = iter(
        (
            "1",  # whole Support Process target
            "1",  # access Need
            "Quieter reading access may be useful.",
            "",  # cancel RECORD confirmation
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    record_support_need_once(
        state,
        process,
        clock=MenuClock(lambda: FIXED_NOW + timedelta(minutes=5)),
        ids=_tokens("cancelled"),
    )

    assert SupportNeedWorkflowService(tmp_path).list(_work()) == ()
