from __future__ import annotations

import hashlib
import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_064_SHA256 = "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"


def _load_script(relative: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue92_package_checker_requires_path_hardening_runtime_files() -> None:
    checker = _load_script(
        "scripts/check_issue92_package.py",
        "issue92_package_checker",
    )
    assert {
        "portia/storage/generated_paths.py",
        "portia/storage/paths.py",
        "portia/storage/io.py",
        "portia/storage/staging.py",
        "portia/storage/repository.py",
        "portia/storage/derived.py",
        "portia/workflows/integrity.py",
    } <= checker._REQUIRED_RUNTIME


def test_issue92_installed_smoke_pins_exact_released_core_064() -> None:
    smoke = _load_script(
        "scripts/smoke_test_issue92_deep_workspace_wheel.py",
        "issue92_installed_smoke",
    )
    assert smoke.CORE_064_FILENAME == "pds_core-0.6.4-py3-none-any.whl"
    assert smoke.CORE_064_SHA256 == CORE_064_SHA256
    assert smoke.TARGET_DEEP_WORKSPACE_LENGTH == 119
    assert len(CORE_064_SHA256) == 64
    int(CORE_064_SHA256, 16)
    assert hashlib.sha256(b"not-the-release-wheel").hexdigest() != CORE_064_SHA256


def test_issue92_scripts_are_in_strict_mypy_qualification() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    files = set(data["tool"]["mypy"]["files"])
    assert "scripts/check_issue92_package.py" in files
    assert "scripts/smoke_test_issue92_deep_workspace_wheel.py" in files


def test_generic_package_checker_requires_issue92_release_boundary() -> None:
    checker = _load_script("scripts/check_package.py", "generic_package_checker_issue92")
    assert "portia/storage/generated_paths.py" in checker.REQUIRED_RUNTIME_FILES
    assert "docs/path-safety.md" in checker.REQUIRED_SDIST_FILES
    assert "scripts/check_issue92_package.py" in checker.REQUIRED_SDIST_FILES
    assert (
        "scripts/smoke_test_issue92_deep_workspace_wheel.py"
        in checker.REQUIRED_SDIST_FILES
    )
    assert "tests/test_issue92_qualification.py" in checker.REQUIRED_SDIST_FILES


def test_issue92_repository_qualification_is_authoritative_terminal_boundary() -> None:
    validator = (ROOT / "scripts/validate_repository.py").read_text(encoding="utf-8")
    assert (
        "Run the complete Portia repository qualification through Issue #92."
        in validator
    )
    assert (
        "Issue #92 qualification requires the authenticated Core 0.6.4 wheel"
        in validator
    )
    assert "scripts/check_issue52_package.py" in validator
    assert "scripts/check_issue92_package.py" in validator
    assert validator.index("scripts/check_issue52_package.py") < validator.index(
        "scripts/check_issue92_package.py"
    )
    assert "scripts/smoke_test_issue52_module_operations_wheel.py" in validator
    assert "scripts/smoke_test_issue92_deep_workspace_wheel.py" in validator
    assert validator.index(
        "scripts/smoke_test_issue52_module_operations_wheel.py"
    ) < validator.index("scripts/smoke_test_issue92_deep_workspace_wheel.py")
    assert "Portia Issue #92 repository qualification passed" in validator


def test_issue92_repository_qualification_preserves_issue52_markers() -> None:
    validator = (ROOT / "scripts/validate_repository.py").read_text(encoding="utf-8")
    for marker in (
        "Run the complete Portia repository qualification through Issue #52.",
        "Issue #52 qualification requires the authenticated Core 0.6.4 wheel",
        "Portia Issue #52 repository qualification passed",
    ):
        assert marker in validator


def test_issue92_ci_uses_cumulative_repository_qualification_path() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for marker in (
        'current_core: "0.6.4"',
        'core: "0.6.3"',
        "python scripts/validate_repository.py",
        '--core-wheel "$env:PDS_CORE_WHEEL"',
        '--historical-core-wheel "$env:PDS_HISTORICAL_CORE_WHEEL"',
    ):
        assert marker in workflow
