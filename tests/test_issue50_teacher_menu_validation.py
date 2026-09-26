from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

from portia.cli import render_menu
from portia.menu import main as menu_main

ROOT = Path(__file__).resolve().parents[1]


def test_production_menu_has_no_foundation_fallback() -> None:
    source = inspect.getsource(menu_main)
    assert "_launch_foundation_task" not in source
    assert "Task-specific actions are not wired" not in source


def test_production_cli_menu_has_all_nine_surfaces() -> None:
    text = render_menu()
    for label in (
        "Record Event",
        "Add Information",
        "Record Response / Communication",
        "Manage Support",
        "Complete Follow-Up",
        "View Timeline",
        "Correct / Retract",
        "Attention Needed",
        "Advanced Portia tools",
    ):
        assert label in text
    assert "[planned]" not in text


def test_issue50_source_validator_passes() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/validate_teacher_menu.py",
            "--stage",
            "source",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
