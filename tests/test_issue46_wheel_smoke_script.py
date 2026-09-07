"""Focused structural checks for the Issue #46 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue46_wheel.py"


def test_issue46_wheel_smoke_cli_and_public_surface() -> None:
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
        "FollowUpWorkflowService",
        "OutcomeWorkflowService",
        "ReentryWorkflowService",
        "RepairWorkflowService",
        "follow_up_reference",
        "outcome_reference",
        "reentry_reference",
        "repair_reference",
        "verify_core_wheel.py",
        "pds_core-0.6.3-py3-none-any.whl",
        "smoke import resolved into source checkout",
        "p22_08_support_positive_outcome",
        "p22_10_reentry_repair_without_overclaiming",
        '"p22_10_reentry_state": "completed"',
        '"p22_10_repair_state": "completed"',
        '"p22_10_outcome_fabricated": False',
        "installed-wheel Issue #46 downstream workflow smoke test passed",
    ):
        assert required in text
