"""Focused structural checks for the Issue #45 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue45_wheel.py"


def test_issue45_wheel_smoke_cli_and_public_surface() -> None:
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
        "ImplementationWorkflowService",
        "FidelityWorkflowService",
        "implementation_reference",
        "fidelity_reference",
        "verify_core_wheel.py",
        "pds_core-0.6.3-py3-none-any.whl",
        "smoke import resolved into source checkout",
        '"execution_state": "completed"',
        '"result": "as_planned"',
        '"outcome_fabricated": False',
        '"follow_up_fabricated": False',
        "installed-wheel Issue #45 Implementation/Fidelity smoke test passed",
    ):
        assert required in text
