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

def test_issue52_ci_qualifies_current_and_historical_core() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for marker in (
        'current_core: "0.6.4"',
        'core: "0.6.3"',
        "PDS_CORE_WHEEL",
        "PDS_HISTORICAL_CORE_WHEEL",
        '--core-wheel "$env:PDS_CORE_WHEEL"',
        '--historical-core-wheel "$env:PDS_HISTORICAL_CORE_WHEEL"',
    ):
        assert marker in workflow
