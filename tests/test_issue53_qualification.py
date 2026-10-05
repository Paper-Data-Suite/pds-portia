from __future__ import annotations

import hashlib
import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE_064_SHA256 = (
    "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b"
)


def _load_script(relative: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_issue53_package_checker_covers_required_runtime_capabilities() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker",
    )
    expected = {
        "event_evidence_judgment",
        "response_communication",
        "support_follow_up",
        "actor_directory",
        "recovery_integrity",
        "student_view",
        "attention_provider",
        "teacher_reference_export",
        "path_hardening",
        "launcher",
    }
    assert set(checker._REQUIRED_RUNTIME_BY_CAPABILITY) == expected
    assert {
        "portia/workflows/events.py",
        "portia/workflows/accounts.py",
        "portia/workflows/reviews.py",
        "portia/workflows/responses.py",
        "portia/workflows/support_processes.py",
        "portia/workflows/implementations.py",
        "portia/workflows/follow_ups.py",
        "portia/storage/actor_directory.py",
        "portia/workflows/recovery.py",
        "portia/workflows/integrity.py",
        "portia/views/student.py",
        "portia/pds_operations.py",
        "portia/exports/execution.py",
        "portia/storage/generated_paths.py",
        "portia/cli.py",
    } <= checker._REQUIRED_RUNTIME


def test_issue53_package_checker_requires_closeout_sdist_evidence() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker_sdist",
    )
    assert {
        "CHANGELOG.md",
        "docs/README.md",
        "docs/validation/issue-53-representative-installed-end-to-end-validation.md",
        "pyproject.toml",
        "scripts/check_issue53_package.py",
        "scripts/smoke_test_issue53_end_to_end_wheel.py",
        "scripts/validate_repository.py",
        "tests/test_issue53_end_to_end_acceptance.py",
        "tests/test_issue53_qualification.py",
    } <= checker._REQUIRED_SDIST


def test_issue53_package_checker_preserves_v02_metadata_boundary() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker_metadata",
    )
    metadata = b"\n".join(
        (
            b"Metadata-Version: 2.4",
            b"Name: pds-portia",
            b"Version: 0.2.0",
            b"Requires-Python: >=3.11",
            b"Requires-Dist: pds-core<0.7,>=0.6.3",
            b"",
        )
    )
    assert checker._metadata_findings(metadata) == []


def test_issue53_package_checker_rejects_sibling_runtime_dependency() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker_sibling",
    )
    metadata = b"\n".join(
        (
            b"Metadata-Version: 2.4",
            b"Name: pds-portia",
            b"Version: 0.2.0",
            b"Requires-Python: >=3.11",
            b"Requires-Dist: pds-core<0.7,>=0.6.3",
            b"Requires-Dist: pds-scoreform>=0.11",
            b"",
        )
    )
    findings = checker._metadata_findings(metadata)
    assert any(
        "unexpected sibling runtime dependency" in item
        for item in findings
    )


def test_issue53_package_checker_requires_exact_entry_points() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker_entry_points",
    )
    content = "\n".join(
        (
            "[console_scripts]",
            "portia = portia.cli:main",
            "",
            "[paper_data_suite.module_operations]",
            "portia = portia.pds_operations:get_module_operations_profile",
            "",
        )
    )
    assert checker._entry_point_findings(content) == []


def test_issue53_installed_smoke_pins_exact_released_core_064() -> None:
    smoke = _load_script(
        "scripts/smoke_test_issue53_end_to_end_wheel.py",
        "issue53_installed_smoke",
    )
    assert smoke.CORE_064_FILENAME == "pds_core-0.6.4-py3-none-any.whl"
    assert smoke.CORE_064_SHA256 == CORE_064_SHA256
    assert smoke.EXPECTED_PORTIA_VERSION == "0.2.0"
    assert smoke.TARGET_DEEP_WORKSPACE_LENGTH == 119
    assert len(CORE_064_SHA256) == 64
    int(CORE_064_SHA256, 16)
    assert hashlib.sha256(b"not-the-release-wheel").hexdigest() != CORE_064_SHA256


def test_issue53_closeout_scripts_are_in_strict_mypy_qualification() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)
    files = set(data["tool"]["mypy"]["files"])
    assert "scripts/check_issue53_package.py" in files
    assert "scripts/smoke_test_issue53_end_to_end_wheel.py" in files


def test_issue53_package_checker_forbids_source_fixture_runtime_packaging() -> None:
    checker = _load_script(
        "scripts/check_issue53_package.py",
        "issue53_package_checker_fixture_boundary",
    )
    assert "tests/" in checker._FORBIDDEN_WHEEL_PREFIXES
    assert "scripts/" in checker._FORBIDDEN_WHEEL_PREFIXES
