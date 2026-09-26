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
    AccountAuthoringInput,
    EventAuthoringInput,
    EventEvidenceTargetInput,
    HumanAttributionInput,
    ObservationAuthoringInput,
    RosterParticipantInput,
    prepare_account,
    prepare_direct_observation,
    prepare_event_bundle,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.event import commit_prepared_event
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.information import launch_add_information_menu
from portia.menu.main import launch_menu
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository

FIXED_NOW = datetime(2026, 9, 24, 1, 0, tzinfo=timezone.utc)


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
        create_class_metadata(
            "class_a",
            "2026-2027",
            created_at=created,
        ),
    )


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


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


def test_prepare_account_preserves_source_target_and_epistemic_boundary() -> None:
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_seed",
        work_kind="event",
        contract_version="2",
    )
    account = prepare_account(
        AccountAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(
                kind="event_participant",
                participant_id="ep_participant",
            ),
            source=HumanAttributionInput(
                kind="roster_student",
                class_id="class_a",
                student_id="student_1",
                display_name="Synthetic Student",
            ),
            information_origin="firsthand",
            source_certainty="stated_uncertain",
            representation="recorded_summary",
            text="  Student   reported a bounded detail. ",
            provided_time=ExplicitOffsetTimestamp("2026-09-23T15:00:00-04:00"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("reported"),
    )
    data = account.to_dict()
    assert data["account_id"] == "acct_reported"
    assert data["target"]["record_ref"]["record_id"] == "ep_participant"
    assert data["source"]["roster_student_ref"] == {
        "class_id": "class_a",
        "student_id": "student_1",
    }
    assert data["content"] == [
        {
            "representation": "recorded_summary",
            "text": "Student reported a bounded detail.",
        }
    ]
    assert data["created_by"] == {
        "type": "local_operator",
        "display_label": "Synthetic Teacher",
    }
    assert "determination" not in data
    assert "classification" not in data


def test_prepare_direct_observation_is_live_direct_and_noninterpretive() -> None:
    work = ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_seed",
        work_kind="event",
        contract_version="2",
    )
    observation = prepare_direct_observation(
        ObservationAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            narrative="  Student moved   to the second table. ",
            observation_time=ExplicitOffsetTimestamp(
                "2026-09-23T15:05:00-04:00"
            ),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("direct"),
    )
    data = observation.to_dict()
    assert data["observation_id"] == "obs_direct"
    assert data["method"] == "live_direct"
    assert data["target"] == {"kind": "event"}
    assert data["observer"] == {
        "kind": "human",
        "human_attribution": {
            "kind": "local_operator",
            "display_label": "Synthetic Teacher",
        },
    }
    assert data["content"] == {"narrative": "Student moved to the second table."}
    assert "hypothesis" not in data
    assert "outcome" not in data


def test_account_menu_cancel_at_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(
        (
            "1",  # report
            "1",  # class
            "1",  # event
            "Synthetic Teacher",
            "2",  # participant target
            "1",  # local operator source
            "1",  # firsthand
            "2",  # stated uncertain
            "1",  # recorded summary
            "Synthetic report.",
            "",  # current provided time
            "",  # cancel RECORD
            "b",  # leave Add Information
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_add_information_menu(
        MenuSessionContext(),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("cancelled"),
    )

    repository = PortiaRepository(tmp_path)
    assert repository.list_accounts(work) == ()
    assert repository.list_observations(work) == ()


def test_account_menu_commits_roster_attribution_without_downstream_inference(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(
        (
            "1",  # report
            "1",  # event class
            "1",  # event
            "Synthetic Teacher",
            "1",  # whole Event target
            "2",  # roster source
            "1",  # source class
            "1",  # source student
            "1",  # firsthand
            "1",  # certain
            "1",  # recorded summary
            "Synthetic student report.",
            "",  # current provided time
            "RECORD",
            "",  # result pause
            "b",  # leave Add Information
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_add_information_menu(
        MenuSessionContext(),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("menuaccount"),
    )

    repository = PortiaRepository(tmp_path)
    accounts = repository.list_accounts(work)
    assert len(accounts) == 1
    data = accounts[0].record.to_dict()
    assert data["source"]["kind"] == "roster_student"
    assert data["target"] == {"kind": "event"}
    assert repository.list_observations(work) == ()
    assert repository.list_work_records(work, "determination", version="1") == ()
    assert repository.list_work_records(work, "response", version="1") == ()


def test_observation_menu_commits_direct_observation_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(
        (
            "2",  # direct observation
            "1",  # event class
            "1",  # event
            "Synthetic Teacher",
            "2",  # participant target
            "Student moved to the second table.",
            "",  # current observation time
            "RECORD",
            "",  # result pause
            "b",  # leave Add Information
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_add_information_menu(
        MenuSessionContext(),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("menuobservation"),
    )

    repository = PortiaRepository(tmp_path)
    observations = repository.list_observations(work)
    assert len(observations) == 1
    data = observations[0].record.to_dict()
    assert data["method"] == "live_direct"
    assert data["target"]["record_ref"]["record_id"] == "ep_participant"
    assert repository.list_accounts(work) == ()
    assert repository.list_work_records(work, "classification", version="1") == ()
    assert repository.list_work_records(work, "outcome", version="1") == ()


def test_review_information_is_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    account = prepare_account(
        AccountAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            source=HumanAttributionInput(
                kind="local_operator",
                display_label="Synthetic Teacher",
            ),
            information_origin="firsthand",
            source_certainty="stated_certain",
            representation="recorded_summary",
            text="Synthetic existing report.",
            provided_time=ExplicitOffsetTimestamp("2026-09-23T15:00:00-04:00"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("existing"),
    )
    from portia.workflows import AccountWorkflowService

    AccountWorkflowService(tmp_path).create(work, account)
    before = tuple(item.fingerprint for item in PortiaRepository(tmp_path).list_accounts(work))
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(("3", "1", "1", "b", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_add_information_menu(MenuSessionContext())

    after = tuple(item.fingerprint for item in PortiaRepository(tmp_path).list_accounts(work))
    assert after == before
    output = capsys.readouterr().out
    assert "Account — Synthetic Teacher — Event as a whole" in output
    assert "Synthetic existing report." in output


def test_main_menu_routes_to_add_information_surface_without_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("2", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Record what someone reported" in output
    assert "Record what I directly observed" in output
