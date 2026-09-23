"""Structural checks for the Issue #49 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue49_wheel.py"


def test_issue49_wheel_smoke_cli_and_native_surface() -> None:
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
        "AttentionQueryService",
        "FollowUpScheduleQueryService",
        "SupportProcessWorkflowService",
        "DependencyWorkflowService",
        "QuarantineStore",
        "IntegrityWorkflowService",
        "acknowledge_finding",
        "suppress_finding",
        "active_integrity_finding_index",
        "portia_derived_state_stale",
        "portia_recovery_required",
        "smoke import resolved into source checkout",
        '"workspace_unchanged"',
        '"privacy_minimal"',
        "installed-wheel Issue #49 attention smoke test passed",
    ):
        assert required in text
    assert "from tests" not in text
    assert "import tests" not in text
