"""Mechanically validate Issue #52 Portia Core module operations."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_RUNTIME = {
    "portia/pds_operations.py",
    "portia/attention_provider.py",
    "portia/readiness_provider.py",
    "portia/attention/actions.py",
}
_REQUIRED_TESTS = {
    "tests/test_issue52_operations_profile.py",
    "tests/test_issue52_attention_provider.py",
    "tests/test_issue52_attention_actions.py",
    "tests/test_issue52_readiness_provider.py",
    "tests/test_issue52_packaging.py",
    "tests/test_issue52_qualification.py",
}
_REQUIRED_DOCS = {
    "docs/module-operations.md",
    "docs/validation/issue-52-portia-module-operations-validation.md",
}
_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue52_package.py",
    "scripts/smoke_test_issue52_module_operations_wheel.py",
    "scripts/verify_core_wheel.py",
}
_EXPECTED_ACTIONS = {
    "portia_follow_up_due": "open_complete_follow_up",
    "portia_follow_up_overdue": "open_complete_follow_up",
    "portia_review_incomplete": "open_add_information",
    "portia_integrity_conflict": "open_advanced_tools",
    "portia_integrity_review_required": "open_advanced_tools",
    "portia_recovery_required": "open_advanced_tools",
    "portia_quarantine_active": "open_advanced_tools",
    "portia_derived_state_stale": "open_advanced_tools",
    "portia_support_process_review_due": "open_manage_support",
    "portia_support_process_review_overdue": "open_manage_support",
    "portia_support_process_dependency_attention": "open_manage_support",
}


def _read(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"required Issue #52 file is unavailable: {relative}"
        ) from exc


def _require_files(root: Path, paths: set[str]) -> None:
    missing = sorted(relative for relative in paths if not (root / relative).is_file())
    if missing:
        raise RuntimeError(f"missing Issue #52 files: {missing}")


def _require_markers(text: str, markers: tuple[str, ...], *, label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise RuntimeError(f"{label} is missing required markers: {missing}")


def _validate_pyproject(root: Path) -> None:
    path = root / "pyproject.toml"
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except OSError as exc:
        raise RuntimeError("pyproject.toml is unavailable") from exc

    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject.toml has no [project] table")

    scripts = project.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("portia") != "portia.cli:main":
        raise RuntimeError("Portia console launcher identity changed")

    entry_points = project.get("entry-points")
    if not isinstance(entry_points, dict):
        raise RuntimeError("Issue #52 module-operations entry points are missing")
    operations = entry_points.get("paper_data_suite.module_operations")
    expected = {"portia": "portia.pds_operations:get_module_operations_profile"}
    if operations != expected:
        raise RuntimeError(
            f"unexpected Portia module-operations registration: {operations!r}"
        )
    for forbidden in (
        "paper_data_suite.modules",
        "paper_data_suite.publication_producers",
    ):
        if forbidden in entry_points:
            raise RuntimeError(f"premature Portia entry-point group present: {forbidden}")

    dependencies = project.get("dependencies")
    if not isinstance(dependencies, list):
        raise RuntimeError("Portia runtime dependencies are unavailable")
    normalized = {str(value).replace(" ", "").lower() for value in dependencies}
    if "pds-core>=0.6.3,<0.7" not in normalized:
        raise RuntimeError("Portia Core compatibility floor changed unexpectedly")
    for sibling in (
        "pds-concord",
        "pds-meridian",
        "pds-quillan",
        "pds-scoreform",
        "pds-vitrine",
        "pds-paper-data-suite",
    ):
        if any(sibling in value for value in normalized):
            raise RuntimeError(f"unexpected Portia runtime dependency: {sibling}")


def _validate_source(root: Path) -> None:
    _require_files(root, _REQUIRED_RUNTIME | _REQUIRED_TESTS | _REQUIRED_DOCS)
    _validate_pyproject(root)

    profile = _read(root, "portia/pds_operations.py")
    _require_markers(
        profile,
        (
            'PORTIA_MODULE_ID: Final[str] = "portia"',
            'import_module("portia.attention_provider")',
            'import_module("portia.readiness_provider")',
            "MODULE_OPERATIONS_CONTRACT_VERSION",
            "readiness_provider=evaluate_portia_readiness",
            "attention_provider=evaluate_portia_attention",
            "validate_module_operations_profile",
        ),
        label="Portia operations profile",
    )
    if "portia.menu" in profile:
        raise RuntimeError("operations profile imports teacher-menu code")

    attention = _read(root, "portia/attention_provider.py")
    _require_markers(
        attention,
        (
            "AttentionQueryService",
            "PortiaAttentionQuery",
            "PortiaAttentionScope",
            "_capture_as_of(clock)",
            "if request.workspace_root is None:",
            "active_school_year=request.active_school_year",
            "PORTIA_ATTENTION_ACTION_ID_BY_CODE",
            "ModuleOwnerActionRef",
            "require_portia_attention_action_id",
        ),
        label="Core attention adapter",
    )
    for forbidden in (
        "portia.menu",
        "ensure_workspace_root",
        "exclusive_create(",
        "guarded_replace(",
        ".mkdir(",
    ):
        if forbidden in attention:
            raise RuntimeError(
                f"attention adapter contains forbidden boundary marker: {forbidden}"
            )

    actions = _read(root, "portia/attention/actions.py")
    for code, action_id in _EXPECTED_ACTIONS.items():
        marker = f'"{code}": "{action_id}"'
        if marker not in actions:
            raise RuntimeError(f"Portia owner-action mapping is missing {marker}")
    _require_markers(
        actions,
        (
            "ATTENTION_DEFINITION_BY_CODE",
            "PORTIA_ATTENTION_ACTION_IDS",
            "require_portia_attention_action_id",
            "must cover the exact native taxonomy",
        ),
        label="Portia owner-action vocabulary",
    )

    readiness = _read(root, "portia/readiness_provider.py")
    _require_markers(
        readiness,
        (
            "inspect_workspace_root",
            "load_class_metadata_for_class",
            "load_class_roster",
            "if request.workspace_root is None:",
            "return _workspace_not_ready()",
            "return _class_not_ready()",
            "return _ready()",
        ),
        label="Portia readiness provider",
    )
    for forbidden in (
        "portia.menu",
        "AttentionQueryService",
        "PortiaRepository",
        "ensure_workspace_root",
        ".mkdir(",
        "write_class_roster",
        "write_class_metadata",
    ):
        if forbidden in readiness:
            raise RuntimeError(
                f"readiness provider contains forbidden boundary marker: {forbidden}"
            )

    docs = _read(root, "docs/module-operations.md")
    _require_markers(
        docs,
        (
            "module-operations v1",
            "paper_data_suite.module_operations",
            "portia.pds_operations:get_module_operations_profile",
            "Portia attention",
            "Portia readiness",
            "open_complete_follow_up",
            "open_add_information",
            "open_manage_support",
            "open_advanced_tools",
            "pds-core>=0.6.3,<0.7",
            "Core 0.6.4",
        ),
        label="module-operations documentation",
    )

    print("Portia Issue #52 source module-operations validation passed")


def _validate_distribution(root: Path) -> None:
    _validate_source(root)
    _require_files(root, _REQUIRED_DISTRIBUTION)

    package_checker = _read(root, "scripts/check_issue52_package.py")
    _require_markers(
        package_checker,
        (
            "portia/pds_operations.py",
            "portia/attention_provider.py",
            "portia/readiness_provider.py",
            "paper_data_suite.module_operations",
            "portia.cli:main",
        ),
        label="Issue #52 package checker",
    )
    verifier = _read(root, "scripts/verify_core_wheel.py")
    _require_markers(
        verifier,
        (
            '"pds_core-0.6.4-py3-none-any.whl"',
            "48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b",
            '"pds_core-0.6.3-py3-none-any.whl"',
            "98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5",
        ),
        label="Core wheel authentication",
    )
    print("Portia Issue #52 distribution module-operations validation passed")


def _validate_repository(root: Path) -> None:
    _validate_distribution(root)
    repository = _read(root, "scripts/validate_repository.py")
    for marker in (
        "scripts/validate_module_operations.py",
        "scripts/check_issue52_package.py",
        "scripts/smoke_test_issue52_module_operations_wheel.py",
        "historical_core_wheel",
        'expected_core_version != "0.6.4"',
        'expected_historical_core_version != "0.6.3"',
        "Portia Issue #52 repository qualification passed",
    ):
        if marker not in repository:
            raise RuntimeError(
                f"repository qualification is missing Issue #52 marker: {marker}"
            )
    print("Portia Issue #52 repository module-operations validation passed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage",
        choices=("source", "distribution", "repository"),
        default="source",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.stage == "source":
            _validate_source(root)
        elif args.stage == "distribution":
            _validate_distribution(root)
        else:
            _validate_repository(root)
    except (OSError, RuntimeError, ValueError, tomllib.TOMLDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
