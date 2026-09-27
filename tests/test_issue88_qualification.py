from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_issue88_source_qualification_validator_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_issue88_deliberate_export.py",
            "--stage",
            "source",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Issue #88 source deliberate-export validation passed" in result.stdout
