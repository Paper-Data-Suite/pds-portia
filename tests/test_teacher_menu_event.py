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
    EventAuthoringInput,
    RosterParticipantInput,
    prepare_event_bundle,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.event import commit_prepared_event, launch_record_event_menu
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.selectors import class_options, student_options
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository

FIXED_NOW = datetime(2026, 9, 23, 22, 0, tzinfo=timezone.utc)


def _add_class(
    root: Path,
    class_id: str,
    school_year: str,
    students: list[dict[str, str]],
) -> None:
    ensure_workspace_root(root)
    write_class_roster(root, create_roster(class_id, students))
    created = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            class_id,
            school_year,
            created_at=created,
        ),
    )


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


def test_prepare_event_bundle_preserves_event_and_participant_boundaries() -> None:
    prepared = prepare_event_bundle(
        EventAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            occurrence=ExplicitOffsetTimestamp("2026-09-23T14:30:00-04:00"),
            summary="  A neutral   classroom event. ",
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
        ids=_tokens("event", "participant", "operation"),
    )

    event = prepared.bundle.event.to_dict()
    participant = prepared.bundle.participants[0].to_dict()
    assert event["work_id"] == "evt_event"
    assert event["summary"] == "A neutral classroom event."
    assert event["created_at"] == "2026-09-23T22:00:00+00:00"
    assert event["created_by"] == {
        "type": "local_operator",
        "display_label": "Synthetic Teacher",
    }
    assert participant["participant_id"] == "ep_participant"
    assert participant["subject"]["roster_student_ref"] == {
        "class_id": "class_a",
        "student_id": "student_1",
    }
    assert prepared.bundle.roles == ()
    assert prepared.bundle.relationships == ()
    assert prepared.operation_id == "op_operation"


def test_cross_class_event_commit_preserves_owner_and_roster_identity(
    tmp_path: Path,
) -> None:
    _add_class(
        tmp_path,
        "class_a_owner",
        "2026-2027",
        [
            {
                "student_id": "student_owner",
                "last_name": "Owner",
                "first_name": "Student",
                "period": "1",
            }
        ],
    )
    _add_class(
        tmp_path,
        "class_b_other",
        "2026-2027",
        [
            {
                "student_id": "student_other",
                "last_name": "Other",
                "first_name": "Student",
                "period": "2",
            }
        ],
    )
    prepared = prepare_event_bundle(
        EventAuthoringInput(
            owner_class_id="class_a_owner",
            school_year="2026-2027",
            occurrence=ExplicitOffsetTimestamp("2026-09-23T14:30:00-04:00"),
            summary="Synthetic cross-class context.",
            location_type="hallway",
            location_detail=None,
            local_operator_label="Synthetic Teacher",
            participants=(
                RosterParticipantInput(
                    class_id="class_b_other",
                    student_id="student_other",
                    display_name="Student Other",
                ),
            ),
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cross", "other", "crossop"),
    )
    work_id = commit_prepared_event(tmp_path, prepared)
    work = ExactPortiaWorkRef(
        class_id="class_a_owner",
        work_id=work_id,
        work_kind="event",
        contract_version="2",
    )
    repository = PortiaRepository(tmp_path)
    event = repository.load_work(work).record
    participant = repository.list_event_participants(work)[0].record

    assert event.class_id == "class_a_owner"
    assert participant.class_id == "class_a_owner"
    assert participant.to_dict()["subject"]["roster_student_ref"] == {
        "class_id": "class_b_other",
        "student_id": "student_other",
    }
    assert repository.list_accounts(work) == ()
    assert repository.list_observations(work) == ()
    assert repository.list_work_records(work, "determination", version="1") == ()
    assert repository.list_work_records(work, "response", version="1") == ()
    assert repository.list_work_records(work, "follow_up", version="1") == ()


def test_event_menu_cancel_at_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _add_class(
        tmp_path,
        "class_a",
        "2026-2027",
        [
            {
                "student_id": "student_1",
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": "2",
            }
        ],
    )
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(
        (
            "1",  # Record a new Event
            "1",  # owning class
            "Synthetic Teacher",
            "",  # current time
            "Neutral classroom context.",
            "1",  # classroom
            "1",  # add owning-class student
            "1",  # exact student
            "3",  # review
            "",  # cancel CREATE
            "b",  # leave Record Event
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_record_event_menu(
        MenuSessionContext(),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cancelled", "participant", "operation"),
    )

    assert PortiaRepository(tmp_path).list_events("class_a") == ()
    output = capsys.readouterr().out
    assert "This records Event context and participation only." in output
    assert "evt_cancelled" not in output
    assert "op_operation" not in output


def test_event_menu_commits_cross_class_participant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(
        tmp_path,
        "class_a_owner",
        "2026-2027",
        [
            {
                "student_id": "student_owner",
                "last_name": "Owner",
                "first_name": "Student",
                "period": "1",
            }
        ],
    )
    _add_class(
        tmp_path,
        "class_b_other",
        "2026-2027",
        [
            {
                "student_id": "student_other",
                "last_name": "Other",
                "first_name": "Student",
                "period": "2",
            }
        ],
    )
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(
        (
            "1",  # Record a new Event
            "1",  # class_a_owner
            "Synthetic Teacher",
            "",  # current time, intentionally in 2026
            "Cross-class synthetic context.",
            "2",  # hallway
            "2",  # add student from another class
            "2",  # class_b_other
            "1",  # student_other
            "3",  # review
            "CREATE",
            "",  # result pause
            "b",  # leave Record Event
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    state = MenuSessionContext()

    launch_record_event_menu(
        state,
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("menu", "participant", "operation"),
    )

    work = ExactPortiaWorkRef(
        class_id="class_a_owner",
        work_id="evt_menu",
        work_kind="event",
        contract_version="2",
    )
    repository = PortiaRepository(tmp_path)
    event = repository.load_work(work).record.to_dict()
    participant = repository.list_event_participants(work)[0].record.to_dict()
    assert event["school_year"] == "2026-2027"
    assert participant["class_id"] == "class_a_owner"
    assert participant["subject"]["roster_student_ref"] == {
        "class_id": "class_b_other",
        "student_id": "student_other",
    }
    assert state.selected_class_id == "class_a_owner"
    assert state.selected_work_kind == "event"
    assert state.selected_work_id == "evt_menu"
    assert state.local_operator_label == "Synthetic Teacher"



def test_class_options_take_school_year_from_core_metadata(tmp_path: Path) -> None:
    _add_class(
        tmp_path,
        "class_historical",
        "2024-2025",
        [
            {
                "student_id": "student_1",
                "last_name": "Student",
                "first_name": "Synthetic",
                "period": "2",
            }
        ],
    )

    options = class_options(tmp_path)
    assert len(options) == 1
    assert options[0].class_id == "class_historical"
    assert options[0].school_year == "2024-2025"

def test_duplicate_roster_names_are_disambiguated_without_name_matching(
    tmp_path: Path,
) -> None:
    _add_class(
        tmp_path,
        "class_a",
        "2026-2027",
        [
            {
                "student_id": "student_1",
                "last_name": "Same",
                "first_name": "Name",
                "period": "2",
            },
            {
                "student_id": "student_2",
                "last_name": "Same",
                "first_name": "Name",
                "period": "2",
            },
        ],
    )

    options = student_options(tmp_path, "class_a")
    assert {item.student_id for item in options} == {"student_1", "student_2"}
    assert all(item.display_name == "Name Same" for item in options)
    assert any("student_1" in item.label for item in options)
    assert any("student_2" in item.label for item in options)


def test_local_operator_context_is_process_local_provenance() -> None:
    state = MenuSessionContext()
    state.remember_local_operator("  Synthetic   Teacher  ")
    assert state.local_operator_label == "Synthetic Teacher"
    state.clear_target_context()
    assert state.local_operator_label == "Synthetic Teacher"
