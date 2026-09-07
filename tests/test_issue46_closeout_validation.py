"""Source/documentation closeout guards for Portia Issue #46."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_issue46_workflows.py"
VALIDATION_RECORD = (
    ROOT
    / "docs"
    / "validation"
    / "issue-46-follow-up-outcome-reentry-repair-workflows-validation.md"
)


def test_issue46_source_validator_passes_without_runtime_imports() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--stage", "source"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #46 source workflow validation passed" in result.stdout

    text = VALIDATOR.read_text(encoding="utf-8")
    assert "from portia" not in text
    assert "import portia" not in text


def test_issue46_validator_already_defines_later_fail_closed_stages() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    for required in (
        'choices=("source", "distribution", "repository")',
        "scripts/check_issue46_package.py",
        "scripts/smoke_test_issue46_wheel.py",
        "scripts/validate_repository.py",
        "Portia Issue #46 repository qualification passed",
    ):
        assert required in text


def test_issue46_validation_record_claims_only_observed_evidence() -> None:
    text = VALIDATION_RECORD.read_text(encoding="utf-8")
    for observed in (
        "328 passed in 28.58s",
        "331 passed in 33.88s",
        "62 Issue #19 contract tests passed in 10.76s",
        "170 regression tests passed in 121.83s",
        "Portia Issue #46 source workflow validation passed",
        "Ruff: All checks passed!",
        "MyPy: Success: no issues found in 119 source files",
        "Successfully built pds_portia-0.2.0.tar.gz and pds_portia-0.2.0-py3-none-any.whl",
        "Portia Issue #46 package inventory validation passed",
        "Portia installed-wheel Issue #46 downstream workflow smoke test passed",
        "Portia Issue #46 repository qualification passed",
        "source/runtime, distribution, and cumulative repository qualification observed",
        "full-repository pytest summary count is not preserved",
        "no numeric full-repository pytest count is invented",
    ):
        assert observed in text
    for stale in (
        "final repository qualification pending",
        "Final repository integration\n\nPending.",
        "no final cumulative repository pytest/Ruff/MyPy",
        "distribution and final repository qualification pending",
        "has not yet been reported by the user",
        "No package-inventory or installed-wheel pass is claimed",
        "Until later closeout slices add and",
        "those later stages are expected to fail closed",
    ):
        assert stale not in text
