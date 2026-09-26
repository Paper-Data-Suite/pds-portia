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

from portia.menu.context import MenuSessionContext
from portia.menu.main import launch_menu
from portia.menu.selectors import StudentOption
from portia.menu.timeline import (
    launch_view_timeline_menu,
    student_timeline_query,
    student_timeline_result,
)
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository

CREATED = "2026-09-20T09:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "issue50_slice10_test"}


def _student_option() -> StudentOption:
    return StudentOption(
        class_id="class_a",
        student_id="student_1",
        display_name="Synthetic Student",
        period="2",
        label="Synthetic Student — Period 2",
    )


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
    write_class_metadata_for_class(
        root,
        create_class_metadata(
            "class_a",
            "2026-2027",
            created_at=datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc),
        ),
    )


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _event_record() -> PortiaRecord:
    return parse_portia_record(
        "event",
        "2",
        {
            "schema_version": "2",
            "record_type": "portia_work",
            "work_kind": "event",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "school_year": "2026-2027",
            "status": "active",
            "occurrence": {"precision": "exact", "started_at": CREATED},
            "summary": "Synthetic bounded Event for timeline menu testing.",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _participant_record() -> PortiaRecord:
    return parse_portia_record(
        "event_participant",
        "3",
        {
            "schema_version": "3",
            "record_type": "event_participant",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "participant_id": "ep_alpha",
            "status": "active",
            "subject": {
                "kind": "roster_student",
                "roster_student_ref": {
                    "class_id": "class_a",
                    "student_id": "student_1",
                },
                "display_snapshot": {"display_name": "Synthetic Student"},
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _seed(root: Path) -> None:
    _add_class(root)
    repository = PortiaRepository(root)
    repository.create_work(_event_ref(), _event_record())
    repository.create_work_record(_event_ref(), _participant_record())


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_student_query_uses_exact_roster_identity_and_explicit_history_authority() -> None:
    student = _student_option()

    current = student_timeline_query(student, history=False)
    assert current.mode == "current"
    assert current.scope.history_allowed is False
    assert current.scope.allowed_class_ids == ("class_a",)
    assert current.scope.focal_students[0].class_id == "class_a"
    assert current.scope.focal_students[0].student_id == "student_1"

    history = student_timeline_query(student, history=True)
    assert history.mode == "history"
    assert history.scope.history_allowed is True
    assert history.scope.focal_students == current.scope.focal_students


def test_current_student_view_delegates_to_production_service_and_is_zero_write(
    tmp_path: Path,
) -> None:
    _seed(tmp_path)
    before = _snapshot(tmp_path)

    result = student_timeline_result(
        tmp_path,
        _student_option(),
        history=False,
    )

    assert result.query.mode == "current"
    assert tuple(work.work_ref for work in result.works) == (_event_ref(),)
    assert all(
        entry.history_kind == "current_representation"
        for entry in result.entries
    )
    assert _snapshot(tmp_path) == before


def test_history_read_is_explicit_and_stays_zero_write(tmp_path: Path) -> None:
    _seed(tmp_path)
    before = _snapshot(tmp_path)

    result = student_timeline_result(
        tmp_path,
        _student_option(),
        history=True,
    )

    assert result.query.mode == "history"
    assert result.query.scope.history_allowed is True
    assert _snapshot(tmp_path) == before


def test_interactive_current_timeline_view_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(tmp_path)
    before = _snapshot(tmp_path)
    monkeypatch.setenv("PDS_WORKSPACE_ROOT", str(tmp_path))
    answers = iter(("1", "1", "1", "1", "b", "b", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_view_timeline_menu(MenuSessionContext())

    assert _snapshot(tmp_path) == before


def test_main_menu_routes_to_timeline_surface_without_workspace_read(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("6", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "View Timeline" in output
    assert "Select a student" in output
    assert "B. Back" in output
