"""Closeout guards for the Issue #48 repository qualification path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"
ISSUE48_VALIDATOR = ROOT / "scripts" / "validate_student_views.py"
ISSUE47_VALIDATOR = ROOT / "scripts" / "validate_issue47_workflows.py"
CI = ROOT / ".github" / "workflows" / "ci.yml"


def test_issue48_repository_qualification_cli_requires_core_063() -> None:
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
    assert "Run the complete Portia repository qualification through Issue #48." in text
    assert "Issue #48 qualification requires the authenticated Core 0.6.3 wheel" in text


def test_issue48_repository_qualification_integrates_issue48_in_order() -> None:
    text = VALIDATOR.read_text(encoding="utf-8")
    assert text.index("scripts/validate_issue47_workflows.py") < text.index(
        "scripts/validate_student_views.py"
    )
    assert text.index("scripts/validate_student_views.py") < text.index(
        '[sys.executable, "-m", "pytest"]'
    )
    assert text.index("scripts/check_issue46_package.py") < text.index(
        "scripts/check_issue48_package.py"
    )
    assert text.index("scripts/smoke_test_issue46_wheel.py") < text.index(
        "scripts/smoke_test_issue48_wheel.py"
    )
    assert "Portia Issue #48 repository qualification passed" in text


def test_issue48_repository_qualification_retains_full_repo_gates() -> None:
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


def test_issue48_ci_qualifies_windows_and_ubuntu_through_durable_path() -> None:
    text = CI.read_text(encoding="utf-8")
    assert "ubuntu-latest" in text
    assert "windows-latest" in text
    assert 'python: "3.11"' in text
    assert 'core: "0.6.3"' in text
    assert (
        'python scripts/validate_repository.py --core-wheel "$env:PDS_CORE_WHEEL"'
        in text
    )


def test_issue48_repository_stage_validator_accepts_cumulative_path() -> None:
    result = subprocess.run(
        [sys.executable, str(ISSUE48_VALIDATOR), "--stage", "repository"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #48 repository student-view validation passed" in result.stdout


def test_issue48_repository_qualification_preserves_issue47_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(ISSUE47_VALIDATOR), "--stage", "repository"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Portia Issue #47 repository workflow validation passed" in result.stdout
