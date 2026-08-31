"""Focused structural checks for the Issue #43 installed-wheel smoke script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "smoke_test_issue43_wheel.py"


def test_issue43_wheel_smoke_cli_and_public_surface() -> None:
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
        "ResponseWorkflowService",
        "CommunicationWorkflowService",
        "response_reference",
        "communication_reference",
        "ActorDirectoryService",
        "ExactActorContactPointRef",
        "Core 0.6.3",
        "smoke import resolved into source checkout",
        '"participation": "not_established"',
        '"relation": "relates_to_response"',
        "installed-wheel Issue #43 Response/Communication smoke test passed",
    ):
        assert required in text
