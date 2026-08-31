"""Closeout guards for the Issue #43 repository-wide qualification path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
ISSUE43_VALIDATION = (
    ROOT
    / "docs"
    / "validation"
    / "issue-43-response-and-communication-workflows-validation.md"
)


def test_issue43_repository_qualification_cli_keeps_exact_core_wheel_input() -> None:
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
    assert "Issue #43 qualification requires the authenticated Core 0.6.3 wheel" in text


def test_issue43_repository_qualification_integrates_issue43_in_order() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")

    assert text.index("scripts/validate_workflows.py") < text.index(
        "scripts/validate_issue43_workflows.py"
    )
    assert text.index("scripts/validate_issue43_workflows.py") < text.index(
        '[sys.executable, "-m", "pytest"]'
    )

    package_steps = (
        "scripts/check_issue41_package.py",
        "scripts/check_issue42_package.py",
        "scripts/check_issue43_package.py",
    )
    assert [text.index(step) for step in package_steps] == sorted(
        text.index(step) for step in package_steps
    )

    smoke_steps = (
        "scripts/smoke_test_issue41_wheel.py",
        "scripts/smoke_test_issue42_wheel.py",
        "scripts/smoke_test_issue43_wheel.py",
    )
    assert [text.index(step) for step in smoke_steps] == sorted(
        text.index(step) for step in smoke_steps
    )
    assert "Portia Issue #43 repository qualification passed" in text


def test_issue43_repository_qualification_retains_prior_full_repo_gates() -> None:
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


def test_issue43_validation_record_documents_distribution_and_closeout() -> None:
    text = ISSUE43_VALIDATION.read_text(encoding="utf-8")
    for required in (
        "**Status:** final repository qualification integrated",
        "Slice 14 distribution qualification",
        "244 Issue #43 tests",
        "installed-wheel Response/Communication smoke",
        "Slice 15 final repository qualification",
        "python scripts/validate_repository.py --core-wheel <pds-core-0.6.3-wheel>",
        "Portia Issue #43 repository qualification passed",
    ):
        assert required in text
