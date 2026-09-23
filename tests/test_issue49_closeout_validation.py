"""Source/documentation closeout guards for Portia Issue #49."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_attention_queries.py"
VALIDATION_RECORD = (
    ROOT / "docs" / "validation" / "issue-49-attention-query-validation.md"
)


def test_issue49_source_validator_passes_without_runtime_imports() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--stage", "source"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Issue #49 source attention-query validation passed" in result.stdout

    text = VALIDATOR.read_text(encoding="utf-8")
    assert "from portia" not in text
    assert "import portia" not in text


def test_issue49_validator_defines_fail_closed_closeout_stages() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    for required in (
        'choices=("source", "distribution", "repository")',
        "scripts/check_issue49_package.py",
        "scripts/smoke_test_issue49_wheel.py",
        "scripts/validate_repository.py",
        "behavior_score",
        "risk_score",
        "urgency_score",
        "raw_record",
        "paper_data_suite.modules",
    ):
        assert required in text


def test_issue49_validation_record_uses_observed_evidence_policy() -> None:
    text = VALIDATION_RECORD.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for required in (
        "Issue #49 Validation",
        "Slice 5 focused attention gate: 85 passed",
        "Slice 5 full repository gate: 3561 passed, 7385 subtests passed",
        "corrected wheel + sdist build: passed",
        "Issue #49 isolated installed-wheel attention smoke: passed",
        "cumulative scripts/validate_repository.py qualification: passed",
        "no exact cumulative pytest count is invented here",
        "Remote CI for the final Slice 6 commit is not claimed",
    ):
        assert required in normalized
