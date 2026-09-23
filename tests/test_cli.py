from __future__ import annotations

from importlib import metadata

from portia import __version__
from portia.cli import CORE_REQUIREMENT, main, render_menu, render_status


def test_version_matches_installed_distribution() -> None:
    assert __version__ == "0.2.0"
    assert metadata.version("pds-portia") == __version__


def test_status_reports_bounded_core_requirement() -> None:
    status = render_status()
    assert CORE_REQUIREMENT == "pds-core>=0.6.3,<0.7"
    assert "Core requirement: pds-core>=0.6.3,<0.7" in status
    assert "Teacher data access: none" in status
    assert "task-oriented teacher menu" in status


def test_menu_is_task_oriented_production_taxonomy() -> None:
    menu = render_menu()
    assert "Record Event" in menu
    assert "Complete Follow-Up" in menu
    assert "Advanced Portia tools" in menu
    assert "[planned]" not in menu
    assert "B. Back" not in menu
    assert "M. Main Menu" not in menu
    assert "H. Help" in menu
    assert "Q. Quit" in menu


def test_default_command_launches_menu_and_quits(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "q")  # type: ignore[attr-defined]
    assert main([]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Record Event" in captured.out
    assert "Advanced Portia tools" in captured.out


def test_menu_command_launches_same_menu(
    monkeypatch: object,
    capsys: object,
) -> None:
    monkeypatch.setattr("builtins.input", lambda _prompt: "q")  # type: ignore[attr-defined]
    assert main(["menu"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Record Event" in captured.out


def test_status_command(capsys: object) -> None:
    assert main(["status"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Runtime stage: v0.2 task-oriented teacher menu" in captured.out
