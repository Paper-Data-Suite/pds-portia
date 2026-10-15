from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.validate_issue56_reconciliation_baseline import validate

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_issue56_slice1_reconciliation_baseline_has_no_findings() -> None:
    assert validate(REPO_ROOT) == ()


def test_issue56_slice1_validator_cli_passes() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_issue56_reconciliation_baseline.py",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (
        "Portia Issue #56 Slice 1 reconciliation baseline validation passed"
        in result.stdout
    )
