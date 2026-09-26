from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.menu_navigation import NavigationChoice, QuitPDS, ReturnToMainMenu

from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.main import PRIMARY_TASKS, launch_menu, render_main_menu
from portia.menu.navigation import (
    PortiaMenuChoice,
    navigation_labels_with_help,
    parse_menu_navigation,
)
from portia.menu.ui import page_count, page_items
from portia.models.errors import PortiaLocalValidationError


def test_main_menu_has_required_task_labels_without_main_or_back_navigation() -> None:
    rendered = render_main_menu()
    required = (
        "Record Event",
        "Add Information",
        "Record Response / Communication",
        "Manage Support",
        "Complete Follow-Up",
        "View Timeline",
        "Correct / Retract",
        "Attention Needed",
    )
    assert tuple(task.label for task in PRIMARY_TASKS) == required
    for label in required:
        assert label in rendered
    assert "Advanced Portia tools" in rendered
    assert "H. Help" in rendered
    assert "Q. Quit" in rendered
    assert "B. Back" not in rendered
    assert "M. Main Menu" not in rendered
    assert "[planned]" not in rendered


def test_submenu_navigation_reuses_core_semantics() -> None:
    assert parse_menu_navigation("h") is PortiaMenuChoice.HELP
    assert parse_menu_navigation("b") is NavigationChoice.BACK
    with pytest.raises(ReturnToMainMenu):
        parse_menu_navigation("m")
    with pytest.raises(QuitPDS):
        parse_menu_navigation("q")
    assert navigation_labels_with_help() == (
        "H. Help",
        "B. Back",
        "M. Main Menu",
        "Q. Quit",
    )


def test_menu_routes_to_task_surface_and_back_without_writing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("1", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Record Event" in output
    assert "Record what happened and who was involved." in output
    assert "B. Back" in output
    assert "M. Main Menu" in output


def test_menu_eof_exits_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_eof(_prompt: str) -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    assert launch_menu() == 0


def test_invalid_main_selection_names_only_enabled_navigation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("x", "", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Please choose a listed option, H or Q." in output


def test_pagination_is_deterministic() -> None:
    values = tuple(range(23))
    assert page_count(len(values)) == 3
    assert page_items(values, 0) == tuple(range(10))
    assert page_items(values, 2) == (20, 21, 22)
    with pytest.raises(ValueError):
        page_items(values, 3)


def test_menu_session_context_clears_target_when_workspace_changes(
    tmp_path: Path,
) -> None:
    first = tmp_path / "one"
    second = tmp_path / "two"
    context = MenuSessionContext()
    assert context.resolve_workspace(first) == first.resolve()
    context.remember_work(
        class_id="class_one",
        work_kind="event",
        work_id="evt_example",
    )
    assert context.selected_class_id == "class_one"
    assert context.selected_work_id == "evt_example"

    assert context.resolve_workspace(second) == second.resolve()
    assert context.selected_class_id is None
    assert context.selected_work_kind is None
    assert context.selected_work_id is None


def test_remembering_new_class_clears_remembered_work() -> None:
    context = MenuSessionContext()
    context.remember_work(
        class_id="class_one",
        work_kind="support_process",
        work_id="sup_example",
    )
    context.remember_class("class_two")
    assert context.selected_class_id == "class_two"
    assert context.selected_work_kind is None
    assert context.selected_work_id is None


def test_opaque_id_generator_uses_existing_portia_validation() -> None:
    generator = PortiaIdGenerator(lambda: "fixed_token")
    assert generator.new("evt_") == "evt_fixed_token"
    assert generator.new("fup_") == "fup_fixed_token"

    invalid = PortiaIdGenerator(lambda: "student/name")
    with pytest.raises(PortiaLocalValidationError):
        invalid.new("evt_")


def test_menu_clock_requires_and_preserves_explicit_offset() -> None:
    fixed = datetime(2026, 9, 23, 18, 0, tzinfo=timezone.utc)
    clock = MenuClock(lambda: fixed)
    timestamp = clock.now()
    assert timestamp.text == "2026-09-23T18:00:00+00:00"
    assert timestamp.datetime == fixed

    naive = MenuClock(lambda: datetime(2026, 9, 23, 18, 0))
    with pytest.raises(ValueError):
        naive.now()
