"""Structural checks for the Issue #48 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue48_wheel.py"


def test_issue48_wheel_smoke_cli_and_public_surface() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    text = SCRIPT.read_text(encoding="utf-8")

    assert result.returncode == 0, result.stderr
    assert "portia_wheel" in result.stdout
    assert "core_wheel" in result.stdout
    for required in (
        "StudentTimelineService",
        "StudentTimelineFilter",
        "StudentTimelineQuery",
        "StudentViewScope",
        "write_class_roster",
        "create_roster",
        "p22_04_correction_supersession_disagreement",
        "smoke import resolved into source checkout",
        '"workspace_unchanged": True',
        '"manual_review_present": True',
        '"deterministic_filtering": True',
        "installed-wheel Issue #48 student-view smoke test passed",
    ):
        assert required in text
