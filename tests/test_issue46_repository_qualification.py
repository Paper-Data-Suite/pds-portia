"""Closeout guards for the Issue #46 cumulative repository qualification path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
ISSUE46_VALIDATOR = ROOT / "scripts" / "validate_issue46_workflows.py"
ISSUE45_VALIDATOR = ROOT / "scripts" / "validate_issue45_workflows.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
VALIDATION_RECORD = (
    ROOT
    / "docs"
    / "validation"
    / "issue-46-follow-up-outcome-reentry-repair-workflows-validation.md"
)


def test_issue46_repository_qualification_cli_requires_core_063() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--core-wheel" in result.stdout
    text = VALIDATOR.read_text(encoding="utf-8")
    assert "Run the complete Portia repository qualification through Issue #46." in text
    assert "Issue #46 qualification requires the authenticated Core 0.6.3 wheel" in text


def test_issue46_repository_qualification_integrates_issue46_in_order() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")

    validation_steps = (
        "scripts/validate_workflows.py",
        "scripts/validate_issue43_workflows.py",
        "scripts/validate_issue44_workflows.py",
        "scripts/validate_issue45_workflows.py",
        "scripts/validate_issue46_workflows.py",
    )
    positions = [text.index(step) for step in validation_steps]
    assert positions == sorted(positions)
    assert text.index("scripts/validate_issue46_workflows.py") < text.index(
        '[sys.executable, "-m", "pytest"]'
    )
    assert '"repository"' in text[text.index("scripts/validate_issue46_workflows.py") :]

    package_steps = (
        "scripts/check_issue41_package.py",
        "scripts/check_issue42_package.py",
        "scripts/check_issue43_package.py",
        "scripts/check_issue44_package.py",
        "scripts/check_issue45_package.py",
        "scripts/check_issue46_package.py",
    )
    positions = [text.index(step) for step in package_steps]
    assert positions == sorted(positions)

    smoke_steps = (
        "scripts/smoke_test_issue41_wheel.py",
        "scripts/smoke_test_issue42_wheel.py",
        "scripts/smoke_test_issue43_wheel.py",
        "scripts/smoke_test_issue44_wheel.py",
        "scripts/smoke_test_issue45_wheel.py",
        "scripts/smoke_test_issue46_wheel.py",
    )
    positions = [text.index(step) for step in smoke_steps]
    assert positions == sorted(positions)

    assert "Portia Issue #46 repository qualification passed" in text


def test_issue46_repository_qualification_retains_full_repo_gates() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    for required in (
        "scripts/verify_core_wheel.py",
        "scripts/validate_portia_foundation.py",
        "scripts/validate_runtime_models.py",
        "scripts/validate_storage.py",
        "scripts/validate_identity.py",
        "scripts/validate_workflows.py",
        '[sys.executable, "-m", "pytest"]',
        '[sys.executable, "-m", "ruff", "check", "."]',
        '[sys.executable, "-m", "mypy"]',
        '[sys.executable, "-m", "pip", "check"]',
        '[sys.executable, "-m", "build"]',
        '"-m", "twine", "check"',
        'scripts/check_package.py", "dist"',
        "scripts/smoke_test_wheel.py",
        '["git", "diff", "--check"]',
    ):
        assert required in text


def test_issue46_ci_uses_durable_repository_qualification_path() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "- name: Run complete repository qualification" in text
    assert 'python scripts/validate_repository.py --core-wheel "$env:PDS_CORE_WHEEL"' in text


def test_issue46_repository_stage_validator_accepts_cumulative_path() -> None:
    result = subprocess.run(
        [sys.executable, str(ISSUE46_VALIDATOR), "--stage", "repository"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #46 repository workflow validation passed" in result.stdout

    record = VALIDATION_RECORD.read_text(encoding="utf-8")
    assert (
        "source/runtime, distribution, and cumulative repository qualification observed"
        in record
    )
    assert "Portia Issue #46 repository qualification passed" in record
    assert "final repository qualification pending" not in record

def test_issue46_repository_qualification_preserves_issue45_closeout_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(ISSUE45_VALIDATOR)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #45 workflow validation passed" in result.stdout

