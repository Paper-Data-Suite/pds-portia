from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.workspace import ensure_workspace_root

from portia.menu.advanced import (
    _integrity_lines,
    _quarantine_lines,
    _recovery_lines,
    launch_advanced_menu,
)
from portia.menu.context import MenuSessionContext
from portia.menu.main import launch_menu


def _snapshot(root: Path) -> tuple[tuple[str, bytes], ...]:
    return tuple(
        sorted(
            (str(path.relative_to(root)), path.read_bytes())
            for path in root.rglob("*")
            if path.is_file()
        )
    )


def test_empty_technical_inspection_is_read_only(tmp_path: Path) -> None:
    ensure_workspace_root(tmp_path)
    before = _snapshot(tmp_path)

    assert _quarantine_lines(tmp_path) == ("No active Quarantine records.",)
    assert _recovery_lines(tmp_path) == ("No Operation Journal series.",)
    assert _integrity_lines(tmp_path) == (
        "No operation-scoped Integrity projections.",
    )
    assert _snapshot(tmp_path) == before


def test_advanced_entry_back_is_zero_read_and_zero_write(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("b",))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_advanced_menu(MenuSessionContext())

    output = capsys.readouterr().out
    assert "Advanced Portia tools" in output
    assert "Integrity / Quarantine / Recovery inspection" in output
    assert "Exceptional operations" in output


def test_main_menu_routes_to_advanced_surface(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("9", "b", "q"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    assert launch_menu() == 0
    output = capsys.readouterr().out
    assert "Advanced Portia tools" in output
    assert "Actor Directory exact lookup" in output


def test_advanced_help_rejects_generic_mutation_language(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(("h", "", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_advanced_menu(MenuSessionContext())

    output = capsys.readouterr().out
    assert "arbitrary JSON editing" in output
    assert "generic pointer rewriting" in output
    assert "Quarantine release" in output
    assert "generic delete" not in output.lower()
