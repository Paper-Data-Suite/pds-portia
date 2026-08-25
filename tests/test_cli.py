from __future__ import annotations

from importlib import metadata

from portia import __version__
from portia.cli import CORE_REQUIREMENT, main, render_menu, render_status


def test_version_matches_installed_distribution() -> None:
    assert __version__ == "0.2.0"
    assert metadata.version("pds-portia") == __version__


def test_status_reports_bounded_core_requirement() -> None:
    status = render_status()
    assert CORE_REQUIREMENT == "pds-core>=0.6,<0.7"
    assert "Core requirement: pds-core>=0.6,<0.7" in status
    assert "Teacher data access: none" in status


def test_menu_is_explicitly_bootstrap_only() -> None:
    menu = render_menu()
    assert "bootstrap only" in menu
    assert "Record Event [planned]" in menu
    assert "Complete Follow-Up [planned]" in menu
    assert "No Event, Response, Support, Follow-Up" in menu


def test_default_command_prints_menu(capsys: object) -> None:
    assert main([]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "bootstrap only" in captured.out


def test_status_command(capsys: object) -> None:
    assert main(["status"]) == 0
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "Runtime stage: v0.2 bootstrap chassis" in captured.out
