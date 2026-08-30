"""Focused structural checks for the Issue #42 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue42_wheel.py"


def test_issue42_wheel_smoke_cli_and_public_surface() -> None:
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
        "ReviewWorkflowService",
        "ClassificationWorkflowService",
        "HypothesisWorkflowService",
        "DeterminationWorkflowService",
        "review_reference",
        "classification_reference",
        "hypothesis_reference",
        "determination_reference",
        "Core 0.6.3",
        "smoke import resolved into source checkout",
        "insufficient_information",
    ):
        assert required in text
