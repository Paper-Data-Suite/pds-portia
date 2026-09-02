"""Closeout guards for the Issue #44 repository-wide qualification path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"
ISSUE44_VALIDATION = (
    ROOT
    / "docs"
    / "validation"
    / "issue-44-support-process-support-intervention-workflows-validation.md"
)


def test_issue44_repository_qualification_cli_keeps_exact_core_wheel_input() -> None:
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
    assert "Issue #44 qualification requires the authenticated Core 0.6.3 wheel" in text


def test_issue44_repository_qualification_integrates_issue44_in_order() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")

    validation_steps = (
        "scripts/validate_workflows.py",
        "scripts/validate_issue43_workflows.py",
        "scripts/validate_issue44_workflows.py",
    )
    assert [text.index(step) for step in validation_steps] == sorted(
        text.index(step) for step in validation_steps
    )
    assert text.index("scripts/validate_issue44_workflows.py") < text.index(
        '[sys.executable, "-m", "pytest"]'
    )

    package_steps = (
        "scripts/check_issue41_package.py",
        "scripts/check_issue42_package.py",
        "scripts/check_issue43_package.py",
        "scripts/check_issue44_package.py",
    )
    assert [text.index(step) for step in package_steps] == sorted(
        text.index(step) for step in package_steps
    )

    smoke_steps = (
        "scripts/smoke_test_issue41_wheel.py",
        "scripts/smoke_test_issue42_wheel.py",
        "scripts/smoke_test_issue43_wheel.py",
        "scripts/smoke_test_issue44_wheel.py",
    )
    assert [text.index(step) for step in smoke_steps] == sorted(
        text.index(step) for step in smoke_steps
    )
    assert "Portia Issue #44 repository qualification passed" in text


def test_issue44_repository_qualification_retains_prior_full_repo_gates() -> None:
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


def test_ci_uses_durable_repository_qualification_label() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "- name: Run complete repository qualification" in text
    assert "Run complete Issue 39 qualification" not in text
    assert 'python scripts/validate_repository.py --core-wheel "$env:PDS_CORE_WHEEL"' in text


def test_issue44_validation_record_documents_observed_distribution_checkpoint() -> None:
    text = ISSUE44_VALIDATION.read_text(encoding="utf-8")
    for required in (
        "**Status:** final repository qualification passed",
        "Slice 15b observed distribution qualification",
        "pds_portia-0.2.0-py3-none-any.whl",
        "pds_portia-0.2.0.tar.gz",
        "Portia Issue #44 package inventory validation passed",
        "Portia installed-wheel Issue #44 Support-planning smoke test passed",
        "python scripts/validate_repository.py --core-wheel",
        "2,492 tests",
        "Portia Issue #44 repository qualification passed",
        "final local Issue #44 closeout evidence",
    ):
        assert required in text
