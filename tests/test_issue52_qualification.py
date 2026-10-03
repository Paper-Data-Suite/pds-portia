from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_issue52_source_qualification_validator_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_module_operations.py",
            "--stage",
            "source",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Issue #52 source module-operations validation passed" in result.stdout
