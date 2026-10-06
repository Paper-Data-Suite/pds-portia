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

def test_issue53_validation_record_defines_exact_artifact_handoff() -> None:
    validation = (
        ROOT
        / "docs"
        / "validation"
        / "issue-53-representative-installed-end-to-end-validation.md"
    ).read_text(encoding="utf-8")
    for marker in (
        "candidate Portia source commit:",
        "candidate Portia wheel filename:",
        "candidate Portia wheel SHA-256:",
        "pds_core-0.6.4-py3-none-any.whl",
        CORE_064_SHA256,
        "Python version:",
        "host platform:",
        "deep workspace geometry:",
    ):
        assert marker in validation


def test_issue53_validation_record_preserves_scope_and_synthetic_warning() -> None:
    validation = (
        ROOT
        / "docs"
        / "validation"
        / "issue-53-representative-installed-end-to-end-validation.md"
    ).read_text(encoding="utf-8")
    assert (
        "Issue #53 proves representative coherence of the installed v0.2 "
        "application."
    ) in validation
    assert (
        "It does not assert that every possible Portia workflow combination "
        "has been exhaustively explored."
    ) in validation
    assert (
        "The acceptance story uses only synthetic records and must never be "
        "run against or populated from a real teacher workspace."
    ) in validation
    assert "v0.2.0 release approved" in validation
    assert "Issue #54" in validation


def test_issue53_validation_record_documents_final_cumulative_order() -> None:
    validation = (
        ROOT
        / "docs"
        / "validation"
        / "issue-53-representative-installed-end-to-end-validation.md"
    ).read_text(encoding="utf-8")
    ordered = (
        "full pytest",
        "Ruff",
        "strict mypy",
        "pip check",
        "clean build",
        "Twine",
        "Issue #53 package check",
        "Issue #52 Core 0.6.4 provider smoke",
        "Issue #92 deep-workspace smoke",
        "Issue #53 representative installed end-to-end smoke",
        "git diff --check",
    )
    positions = [validation.index(marker) for marker in ordered]
    assert positions == sorted(positions)
    assert "Portia Issue #53 repository qualification passed" in validation


def test_issue53_documentation_index_and_changelog_are_wired() -> None:
    docs_index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (
        "validation/issue-53-representative-installed-end-to-end-validation.md"
        in docs_index
    )
    assert "Issue #53 representative installed end-to-end acceptance harness" in changelog
    assert "final v0.2.0 release approval owned by Issue #54" in changelog

def test_generic_package_checker_carries_issue53_closeout_boundary() -> None:
    generic = _load_script(
        "scripts/check_package.py",
        "generic_package_checker_issue53",
    )
    dedicated = _load_script(
        "scripts/check_issue53_package.py",
        "dedicated_package_checker_issue53",
    )
    assert dedicated._REQUIRED_RUNTIME <= generic.REQUIRED_RUNTIME_FILES
    assert dedicated._REQUIRED_SDIST <= generic.REQUIRED_SDIST_FILES


def test_issue53_repository_qualification_is_authoritative_terminal_boundary() -> None:
    validator = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    assert (
        "Run the complete Portia repository qualification through Issue #53."
        in validator
    )
    assert (
        "Issue #53 qualification requires the authenticated Core 0.6.4 wheel"
        in validator
    )

    package_52 = validator.index("scripts/check_issue52_package.py")
    package_92 = validator.index("scripts/check_issue92_package.py")
    package_53 = validator.index("scripts/check_issue53_package.py")
    assert package_52 < package_92 < package_53

    smoke_52 = validator.index(
        "scripts/smoke_test_issue52_module_operations_wheel.py"
    )
    smoke_92 = validator.index(
        "scripts/smoke_test_issue92_deep_workspace_wheel.py"
    )
    smoke_53 = validator.index(
        "scripts/smoke_test_issue53_end_to_end_wheel.py"
    )
    diff_check = validator.index('["git", "diff", "--check"]')
    assert smoke_52 < smoke_92 < smoke_53 < diff_check

    assert "Portia Issue #53 repository qualification passed" in validator


def test_issue53_repository_qualification_preserves_issue92_markers() -> None:
    validator = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    for marker in (
        "Run the complete Portia repository qualification through Issue #92.",
        "Issue #92 qualification requires the authenticated Core 0.6.4 wheel",
        "Portia Issue #92 repository qualification passed",
    ):
        assert marker in validator


def test_issue53_repository_qualification_has_one_full_pytest_stage() -> None:
    validator = (ROOT / "scripts" / "validate_repository.py").read_text(
        encoding="utf-8"
    )
    smoke = (
        ROOT / "scripts" / "smoke_test_issue53_end_to_end_wheel.py"
    ).read_text(encoding="utf-8")
    assert validator.count('[sys.executable, "-m", "pytest"]') == 1
    assert '"-m", "pytest"' not in smoke


def test_issue53_ci_uses_existing_cross_platform_cumulative_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )
    for marker in (
        "os: ubuntu-latest",
        "os: windows-latest",
        'python: "3.11"',
        'current_core: "0.6.4"',
        'core: "0.6.3"',
        "python scripts/validate_repository.py",
        '--core-wheel "$env:PDS_CORE_WHEEL"',
        '--historical-core-wheel "$env:PDS_HISTORICAL_CORE_WHEEL"',
    ):
        assert marker in workflow
    assert "smoke_test_issue53_end_to_end_wheel.py" not in workflow
