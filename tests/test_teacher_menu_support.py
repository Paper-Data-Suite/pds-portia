from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.menu.authoring import (
    HumanAttributionInput,
    SupportParticipantAuthoringInput,
    SupportParticipantContextInput,
    SupportProcessAuthoringInput,
    prepare_support_participant,
    prepare_support_participant_activation,
    prepare_support_process,
    prepare_support_process_activation,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.main import launch_menu
from portia.menu.support import create_support_process_once, launch_manage_support_menu
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.workflows import (
    SupportProcessParticipantWorkflowService,
    SupportProcessWorkflowService,
    support_process_participant_reference,
)

FIXED_NOW = datetime(2026, 9, 24, 4, 0, tzinfo=timezone.utc)


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


def _add_class(root: Path, class_id: str, student_id: str, first_name: str) -> None:
    ensure_workspace_root(root)
    write_class_roster(
        root,
        create_roster(
            class_id,
            [
                {
                    "student_id": student_id,
                    "last_name": "Student",
                    "first_name": first_name,
                    "period": "2",
                }
            ],
        ),
    )
    created = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    write_class_metadata_for_class(
        root,
        create_class_metadata(class_id, "2026-2027", created_at=created),
    )


def _work(work_id: str = "sup_root") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id=work_id,
        work_kind="support_process",
        contract_version="1",
    )


def _root(clock: MenuClock, ids: PortiaIdGenerator):
    return prepare_support_process(
        SupportProcessAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            summary="Teacher-local reading support planning.",
            initiation_detail="Student may benefit from additional reading access supports.",
            local_operator_label="Synthetic Teacher",
            planned_start_date="2026-09-25",
            planned_end_date="2026-10-30",
            review_on="2026-10-15",
        ),
        clock=clock,
        ids=ids,
    )


def test_prepare_support_process_starts_proposed_planning_only() -> None:
    record = _root(MenuClock(lambda: FIXED_NOW), _tokens("root"))
    data = record.to_dict()

    assert data["work_id"] == "sup_root"
    assert data["status"] == "proposed"
    assert data["workflow_state"] == "planning"
    assert data["school_year"] == "2026-2027"
    assert data["initiation"] == {
        "kind": "teacher_identified_need",
        "detail": "Student may benefit from additional reading access supports.",
    }
    assert data["planned_start_date"] == "2026-09-25"
    assert data["planned_end_date"] == "2026-10-30"
    assert data["review_on"] == "2026-10-15"
    for field in ("need", "goal", "support", "intervention", "outcome"):
        assert field not in data


def test_prepare_support_participant_preserves_exact_cross_class_roster_identity() -> None:
    participant = prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=_work(),
            person=HumanAttributionInput(
                kind="roster_student",
                class_id="class_b",
                student_id="student_2",
                display_name="Cross Class Student",
            ),
            contexts=(SupportParticipantContextInput(kind="supported_person"),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("participant"),
    )
    data = participant.to_dict()

    assert data["participant_id"] == "spp_participant"
    assert data["class_id"] == "class_a"
    assert data["work_id"] == "sup_root"
    assert data["status"] == "proposed"
    assert data["person"]["roster_student_ref"] == {
        "class_id": "class_b",
        "student_id": "student_2",
    }
    assert data["contexts"] == [{"kind": "supported_person"}]


def test_activation_authoring_preserves_identity_and_uses_opaque_operation_ids() -> None:
    root = _root(MenuClock(lambda: FIXED_NOW), _tokens("root"))
    participant = prepare_support_participant(
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
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("participant"),
    )
    later = MenuClock(lambda: FIXED_NOW + timedelta(minutes=5))
    prepared_participant = prepare_support_participant_activation(
        participant,
        local_operator_label="Synthetic Teacher",
        clock=later,
        ids=_tokens("participant_transition", "participant_operation"),
    )
    prepared_root = prepare_support_process_activation(
        root,
        local_operator_label="Synthetic Teacher",
        clock=later,
        ids=_tokens("root_transition", "root_operation"),
    )

    assert prepared_participant.candidate.logical_id == participant.logical_id
    assert prepared_participant.candidate.status == "active"
    assert prepared_participant.transition_id == "lct_participant_transition"
    assert prepared_participant.operation_id == "op_participant_operation"
    assert prepared_root.candidate.logical_id == root.logical_id
    assert prepared_root.candidate.status == "active"
    assert prepared_root.candidate.field("workflow_state") == "planning"
    assert prepared_root.transition_id == "lct_root_transition"
    assert prepared_root.operation_id == "op_root_operation"


def test_existing_services_persist_incremental_support_setup_and_activation(
    tmp_path: Path,
) -> None:
    _add_class(tmp_path, "class_a", "student_1", "Synthetic")
    root_service = SupportProcessWorkflowService(tmp_path)
    root = root_service.create(_root(MenuClock(lambda: FIXED_NOW), _tokens("root")))
    work = _work()

    participant = prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=work,
            person=HumanAttributionInput(
                kind="roster_student",
                class_id="class_a",
                student_id="student_1",
                display_name="Synthetic Student",
            ),
            contexts=(SupportParticipantContextInput(kind="supported_person"),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("participant"),
    )
    participant_service = SupportProcessParticipantWorkflowService(tmp_path)
    created_participant = participant_service.create(work, participant)

    participant_activation = prepare_support_participant_activation(
        participant,
        local_operator_label="Synthetic Teacher",
        clock=MenuClock(lambda: FIXED_NOW + timedelta(minutes=5)),
        ids=_tokens("participant_transition", "participant_operation"),
    )
    participant_service.transition_lifecycle(
        support_process_participant_reference(work, "spp_participant"),
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
        work,
        root_activation.candidate,
        expected=root.fingerprint,
        transition_id=root_activation.transition_id,
        reason_code="planning_confirmed",
        operation_id=root_activation.operation_id,
    )

    assert root_service.require_current_use(work).record.status == "active"
    current_participant = participant_service.require_current_use(
        support_process_participant_reference(work, "spp_participant")
    )
    assert current_participant.participant.record.status == "active"
    repository = PortiaRepository(tmp_path)
    for kind in (
        "support_need",
        "support_goal",
        "support",
        "intervention",
        "implementation",
        "fidelity",
        "follow_up",
        "outcome",
    ):
        assert repository.list_work_records(work, kind, version="1") == ()


def test_cross_class_roster_participant_does_not_change_support_owner(
    tmp_path: Path,
) -> None:
    _add_class(tmp_path, "class_a", "student_1", "Owner")
    _add_class(tmp_path, "class_b", "student_2", "Cross")
    SupportProcessWorkflowService(tmp_path).create(
        _root(MenuClock(lambda: FIXED_NOW), _tokens("root"))
    )
    work = _work()
    participant = prepare_support_participant(
        SupportParticipantAuthoringInput(
            work=work,
            person=HumanAttributionInput(
                kind="roster_student",
                class_id="class_b",
                student_id="student_2",
                display_name="Cross Student",
            ),
            contexts=(SupportParticipantContextInput(kind="supported_person"),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cross"),
    )
    stored = SupportProcessParticipantWorkflowService(tmp_path).create(work, participant)

    assert stored.record.class_id == "class_a"
    assert stored.record.work_id == "sup_root"
    person = stored.record.to_dict()["person"]
    assert person["roster_student_ref"] == {
        "class_id": "class_b",
        "student_id": "student_2",
    }


def test_cancelled_support_root_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(tmp_path, "class_a", "student_1", "Synthetic")
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    state = MenuSessionContext(local_operator_label="Synthetic Teacher")
    answers = iter(
        (
            "1",  # owning class
            "Teacher-local support planning.",
            "Additional access support may be useful.",
            "",  # no start date
            "",  # no end date
            "",  # no review date
            "",  # cancel confirmation
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    create_support_process_once(
        state,
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cancelled"),
    )

    assert SupportProcessWorkflowService(tmp_path).list("class_a") == ()


def test_main_menu_routes_to_manage_support_surface_without_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("4", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "1. Create a Support Process" in output
    assert "2. Open a Support Process" in output


def test_manage_support_submenu_back_is_zero_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(("b",))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    launch_manage_support_menu(MenuSessionContext())
