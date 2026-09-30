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

from portia.exports import TeacherReferenceExportHistoryService
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.main import PRIMARY_TASKS, render_main_menu
from portia.menu.selectors import StudentOption
from portia.menu.teacher_reference_export import launch_teacher_reference_work_menu
from portia.menu.timeline import student_timeline_result
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository

CREATED = "2026-09-29T19:00:00-04:00"
FIXED_NOW = datetime(2026, 9, 29, 23, 30, tzinfo=timezone.utc)
AGENT = {"type": "system_process", "process_id": "issue51_slice8_test"}


def _student() -> StudentOption:
    return StudentOption(
        class_id="class_a",
        student_id="student_1",
        display_name="Synthetic Student",
        period="2",
        label="Synthetic Student — Period 2",
    )


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _event() -> PortiaRecord:
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
            "summary": "Synthetic <bounded> Event for export menu testing.",
            "creation_source": {"type": "digital_entry"},
            "created_at": CREATED,
            "created_by": AGENT,
            "updated_at": CREATED,
            "updated_by": AGENT,
        },
    )


def _participant() -> PortiaRecord:
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
    repository = PortiaRepository(root)
    repository.create_work(_event_ref(), _event())
    repository.create_work_record(_event_ref(), _participant())


def _work(root: Path):
    result = student_timeline_result(root, _student(), history=False)
    assert len(result.works) == 1
    return result.works[0]


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def _id_generator() -> PortiaIdGenerator:
    tokens = iter(
        (
            "slice8_export",
            "slice8_operation",
            "slice8_artifact_step",
            "slice8_provenance_step",
        )
    )
    return PortiaIdGenerator(lambda: next(tokens))


def _clock() -> MenuClock:
    return MenuClock(lambda: FIXED_NOW)


def test_main_menu_keeps_eight_routine_tasks_and_no_export_root() -> None:
    assert len(PRIMARY_TASKS) == 8
    assert all(task.label != "Export" for task in PRIMARY_TASKS)
    rendered = render_main_menu()
    assert "View Timeline" in rendered
    assert "\nExport\n" not in rendered


def test_cancel_at_exact_preview_is_zero_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(tmp_path)
    before = _snapshot(tmp_path)
    answers = iter(("2", "Synthetic Teacher", "2", "2", "", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_teacher_reference_work_menu(
        MenuSessionContext(),
        tmp_path,
        _student(),
        _work(tmp_path),
        show_current=lambda: None,
        clock=_clock(),
        id_generator=_id_generator(),
        deployment_instance_id="test_deployment",
        process_instance_id="test_process",
    )

    assert _snapshot(tmp_path) == before


def test_whole_work_menu_export_executes_exact_reviewed_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed(tmp_path)
    answers = iter(
        (
            "2",
            "Synthetic Teacher",
            "2",
            "2",
            "EXPORT",
            "",
            "b",
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_teacher_reference_work_menu(
        MenuSessionContext(),
        tmp_path,
        _student(),
        _work(tmp_path),
        show_current=lambda: None,
        clock=_clock(),
        id_generator=_id_generator(),
        deployment_instance_id="test_deployment",
        process_instance_id="test_process",
    )

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(_event_ref())
    assert len(history) == 1
    assert history[0].projection_purpose == "teacher_current"
    assert history[0].verification_status == "available_verified"
    output = capsys.readouterr().out
    assert "Exact outgoing HTML" in output
    assert "Teacher reference created" in output
    assert "Verification: Available and verified" in output
    assert "sent, shared, filed, delivered, received" in output


def test_participant_specific_menu_export_binds_exact_focal_participant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed(tmp_path)
    answers = iter(
        (
            "3",
            "Synthetic Teacher",
            "2",
            "2",
            "EXPORT",
            "",
            "b",
        )
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_teacher_reference_work_menu(
        MenuSessionContext(),
        tmp_path,
        _student(),
        _work(tmp_path),
        show_current=lambda: None,
        clock=_clock(),
        id_generator=_id_generator(),
        deployment_instance_id="test_deployment",
        process_instance_id="test_process",
    )

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(_event_ref())
    assert len(history) == 1
    assert history[0].projection_purpose == "participant_specific"
    assert history[0].focal_participant is True


def test_history_surface_is_read_only_and_does_not_assign_current_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed(tmp_path)
    before = _snapshot(tmp_path)
    answers = iter(("4", "", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_teacher_reference_work_menu(
        MenuSessionContext(),
        tmp_path,
        _student(),
        _work(tmp_path),
        show_current=lambda: None,
        clock=_clock(),
    )

    assert _snapshot(tmp_path) == before
    output = capsys.readouterr().out
    assert "View prior exports for this work" in output
    assert "does not establish current, official, active, or best" in output or (
        "No prior teacher-reference exports" in output
    )


def test_contextual_help_explains_export_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed(tmp_path)
    answers = iter(("h", "", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_teacher_reference_work_menu(
        MenuSessionContext(),
        tmp_path,
        _student(),
        _work(tmp_path),
        show_current=lambda: None,
        clock=_clock(),
    )

    output = capsys.readouterr().out
    assert "not an official record" in output
    assert "does not by itself authorize disclosure" in output
    assert "does not create a student-global dossier" in output
    assert "type EXPORT exactly" in output
