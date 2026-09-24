from __future__ import annotations

from datetime import datetime, timezone
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
    CommunicationAuthoringInput,
    CommunicationRecipientInput,
    EventAuthoringInput,
    EventEvidenceTargetInput,
    HumanAttributionInput,
    ResponseAuthoringInput,
    RosterParticipantInput,
    prepare_communication,
    prepare_event_bundle,
    prepare_response,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.event import commit_prepared_event
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.main import launch_menu
from portia.menu.response_communication import (
    launch_response_communication_menu,
    record_response_once,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.workflows import CommunicationWorkflowService, ResponseWorkflowService

FIXED_NOW = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


def _add_class(root: Path) -> None:
    ensure_workspace_root(root)
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    created = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    write_class_metadata_for_class(
        root,
        create_class_metadata("class_a", "2026-2027", created_at=created),
    )


def _seed_event(root: Path) -> ExactPortiaWorkRef:
    prepared = prepare_event_bundle(
        EventAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            occurrence=ExplicitOffsetTimestamp("2026-09-23T14:30:00-04:00"),
            summary="Synthetic Event context.",
            location_type="classroom",
            location_detail=None,
            local_operator_label="Synthetic Teacher",
            participants=(
                RosterParticipantInput(
                    class_id="class_a",
                    student_id="student_1",
                    display_name="Synthetic Student",
                ),
            ),
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("seed", "participant", "seedop"),
    )
    commit_prepared_event(root, prepared)
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_seed",
        work_kind="event",
        contract_version="2",
    )


def test_prepare_response_is_bounded_and_does_not_encode_outcome() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    response = prepare_response(
        ResponseAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            action_family="classroom_management",
            description="Redirected the class to the posted task.",
            execution_state="completed",
            started_at=ExplicitOffsetTimestamp("2026-09-23T15:00:00-04:00"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("response"),
    )
    data = response.to_dict()
    assert data["response_id"] == "rsp_response"
    assert data["provider"] == {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    }
    assert data["action"] == {
        "family": "classroom_management",
        "description": "Redirected the class to the posted task.",
    }
    assert data["execution_state"] == "completed"
    assert "outcome" not in data
    assert "effectiveness" not in data


def test_teacher_consequence_stays_teacher_local() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    response = prepare_response(
        ResponseAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            action_family="consequence",
            description="Assigned a teacher-local classroom consequence.",
            execution_state="completed",
            started_at=ExplicitOffsetTimestamp("2026-09-23T15:05:00-04:00"),
            local_operator_label="Synthetic Teacher",
            consequence_context="teacher_local",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("consequence"),
    )
    assert response.to_dict()["action"]["consequence_context"] == "teacher_local"
    assert "determination_ref" not in response.to_dict()


def test_prepare_communication_preserves_attempt_without_delivery_claims() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    communication = prepare_communication(
        CommunicationAuthoringInput(
            work=work,
            recipients=(
                CommunicationRecipientInput(
                    person=HumanAttributionInput(
                        kind="descriptive_person",
                        description_type="family_member",
                        display_label="Family member",
                    ),
                    participation="not_established",
                ),
            ),
            method_kind="phone_call",
            method_detail=None,
            purpose_kind="information_sharing",
            purpose_detail=None,
            act_state="recipient_unavailable",
            privacy_scope="ordinary",
            started_at=ExplicitOffsetTimestamp("2026-09-23T15:10:00-04:00"),
            summary="Attempted phone contact regarding the Event.",
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("communication"),
    )
    data = communication.to_dict()
    assert data["communication_id"] == "comm_communication"
    assert data["act_state"] == "recipient_unavailable"
    assert data["recipients"][0]["participation"] == "not_established"
    assert "delivery" not in data
    assert "read" not in data
    assert "agreement" not in data


def test_response_and_communication_create_through_existing_services(
    tmp_path: Path,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    clock = MenuClock(lambda: FIXED_NOW)

    response = prepare_response(
        ResponseAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            action_family="de_escalation",
            description="Reduced verbal demands and provided space.",
            execution_state="completed",
            started_at=ExplicitOffsetTimestamp("2026-09-23T15:00:00-04:00"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("service_response"),
    )
    ResponseWorkflowService(tmp_path).create(work, response)

    communication = prepare_communication(
        CommunicationAuthoringInput(
            work=work,
            recipients=(
                CommunicationRecipientInput(
                    person=HumanAttributionInput(
                        kind="roster_student",
                        class_id="class_a",
                        student_id="student_1",
                        display_name="Synthetic Student",
                    ),
                    participation="participated",
                ),
            ),
            method_kind="in_person",
            method_detail=None,
            purpose_kind="information_sharing",
            purpose_detail=None,
            act_state="completed",
            privacy_scope="ordinary",
            started_at=ExplicitOffsetTimestamp("2026-09-23T15:05:00-04:00"),
            summary="Brief in-person communication.",
            local_operator_label="Synthetic Teacher",
        ),
        clock=clock,
        ids=_tokens("service_communication"),
    )
    CommunicationWorkflowService(tmp_path).create(work, communication)

    repository = PortiaRepository(tmp_path)
    assert len(ResponseWorkflowService(tmp_path).list(work)) == 1
    assert len(CommunicationWorkflowService(tmp_path).list(work)) == 1
    assert repository.list_work_records(work, "follow_up", version="1") == ()
    assert repository.list_work_records(work, "outcome", version="1") == ()


def test_cancelled_response_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    state = MenuSessionContext(local_operator_label="Synthetic Teacher")
    answers = iter(
        (
            "1",  # class
            "1",  # event
            "1",  # Event target
            "1",  # classroom management
            "Redirected to the posted task.",
            "1",  # attempted
            "",  # current time
            "",  # cancel at confirmation
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    record_response_once(
        state,
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cancelled"),
    )

    assert ResponseWorkflowService(tmp_path).list(work) == ()


def test_main_menu_routes_to_response_communication_surface_without_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("3", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "1. Record a Response" in output
    assert "2. Record a Communication" in output
    assert "3. View recent Responses / Communications" in output


def test_response_communication_submenu_back_is_zero_read(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(("b",))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    launch_response_communication_menu(MenuSessionContext())
