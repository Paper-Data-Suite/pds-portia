"""Source/documentation closeout guards for Portia Issue #48."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_student_views.py"
VALIDATION_RECORD = (
    ROOT / "docs" / "validation" / "issue-48-student-timeline-work-view-validation.md"
)


def test_issue48_source_validator_passes_without_runtime_imports() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--stage", "source"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #48 source student-view validation passed" in result.stdout

    text = VALIDATOR.read_text(encoding="utf-8")
    assert "from portia" not in text
    assert "import portia" not in text


def test_issue48_validator_defines_fail_closed_closeout_stages() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    for required in (
        'choices=("source", "distribution", "repository")',
        "scripts/check_issue48_package.py",
        "scripts/smoke_test_issue48_wheel.py",
        "scripts/validate_repository.py",
        "Portia Issue #48 repository qualification passed",
        "behavior_score",
        "risk_score",
        "raw_record",
    ):
        assert required in text


def test_issue48_validation_record_has_observed_evidence_policy() -> None:
    text = VALIDATION_RECORD.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for required in (
        "Issue #48 Validation",
        "Slice 4: 58 passed",
        "Slice 5: 181 passed",
        "Slice 6 focused closeout: 74 passed in 4.31s",
        "Portia Issue #48 distribution student-view validation passed",
        "Portia Issue #48 repository qualification passed",
        "full-repository pytest summary count is not preserved",
        "No numeric full-repository pytest count is invented",
        "observed on Windows",
    ):
        assert required in normalized
    for stale in (
        "Pending execution of the authoritative cumulative repository command",
        "updated only from observed output",
    ):
        assert stale not in normalized
