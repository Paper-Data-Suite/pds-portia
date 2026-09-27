"""Mechanically validate Issue #88 deliberate-export coordinated operations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_RUNTIME = {
    "portia/storage/deliberate_export_operations.py",
    "portia/storage/deliberate_export_persistence.py",
    "portia/storage/deliberate_export_recovery.py",
    "portia/storage/deliberate_export_recovery_actions.py",
}
_REQUIRED_TESTS = {
    "tests/schema_validation/test_issue_88_export_operation_contracts.py",
    "tests/test_issue88_export_operation_validation.py",
    "tests/test_issue88_export_execution.py",
    "tests/test_issue88_qualification.py",
}
_REQUIRED_DOCS = {
    "docs/decisions/0020-extend-coordinated-operations-for-deliberate-export.md",
    "docs/validation/issue-88-deliberate-export-coordinated-operations-validation.md",
}
_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue88_package.py",
    "scripts/smoke_test_issue88_deliberate_export_wheel.py",
    "scripts/validate_issue88_deliberate_export.py",
}


def _read(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"required Issue #88 file is unavailable: {relative}") from exc


def _require_files(root: Path, paths: set[str]) -> None:
    missing = sorted(relative for relative in paths if not (root / relative).is_file())
    if missing:
        raise RuntimeError(f"missing Issue #88 files: {missing}")


def _validate_source(root: Path) -> None:
    _require_files(root, _REQUIRED_RUNTIME | _REQUIRED_TESTS | _REQUIRED_DOCS)

    catalog = json.loads(_read(root, "schemas/schema-catalog.json"))
    contracts = catalog.get("contracts")
    if not isinstance(contracts, dict):
        raise RuntimeError("schema catalog contracts is not an object")
    for contract, version in (
        ("deliberate_export_ref", "1"),
        ("deliberate_export_target", "1"),
        ("operation_journal", "4"),
        ("operation_lock", "3"),
    ):
        versions = contracts.get(contract)
        if not isinstance(versions, dict) or version not in versions:
            raise RuntimeError(f"schema catalog is missing {contract}@{version}")

    actions = _read(root, "portia/storage/deliberate_export_recovery_actions.py")
    for api in (
        "recover_deliberate_export_provenance",
        "recover_deliberate_export_committed_revision",
        "finalize_deliberate_export",
    ):
        if f"def {api}(" not in actions:
            raise RuntimeError(f"recovery API is missing: {api}")
    for marker in (
        "PortiaConflictError",
        "validate_deliberate_export_journal",
        "LockStore(root).release",
        '"completed"',
    ):
        if marker not in actions:
            raise RuntimeError(f"recovery/finalization marker is missing: {marker}")

    recovery = _read(root, "portia/storage/deliberate_export_recovery.py")
    for state in (
        "nothing_durable",
        "artifact_only",
        "artifact_mismatch",
        "provenance_only",
        "exact_both_committed_journal_missing",
        "committed",
        "completed",
        "indeterminate",
    ):
        if state not in recovery:
            raise RuntimeError(f"recovery classifier state is missing: {state}")

    policy = _read(root, "portia/views/policy.py")
    if '"operation_journal", ("1", "2", "3", "4"), "operational_excluded"' not in policy:
        raise RuntimeError("operation_journal@4 is not explicitly student-view excluded")
    if '"operation_lock", ("1", "2", "3"), "operational_excluded"' not in policy:
        raise RuntimeError("operation_lock@3 is not explicitly student-view excluded")

    adr = _read(
        root,
        "docs/decisions/0020-extend-coordinated-operations-for-deliberate-export.md",
    )
    for heading in (
        "## Evidence-preserving recovery mutations",
        "## Post-commit export finalization",
        "## Adversarial replay and conflict guarantees",
    ):
        if heading not in adr:
            raise RuntimeError(f"ADR 0020 is missing accepted heading: {heading}")

    tests = _read(root, "tests/test_issue88_export_execution.py")
    for marker in (
        "test_artifact_only_recovery_creates_only_missing_provenance",
        "test_export_finalization_appends_completed_revision_without_rewriting_export",
        "test_contradictory_export_candidate_reuse_fails_without_mutation",
        "test_exact_replay_across_recovery_apis_creates_no_duplicates",
    ):
        if marker not in tests:
            raise RuntimeError(f"Issue #88 acceptance coverage is missing: {marker}")

    print("Portia Issue #88 source deliberate-export validation passed")


def _validate_distribution(root: Path) -> None:
    _validate_source(root)
    _require_files(root, _REQUIRED_DISTRIBUTION)
    print("Portia Issue #88 distribution deliberate-export validation passed")


def _validate_repository(root: Path) -> None:
    _validate_distribution(root)
    repository = _read(root, "scripts/validate_repository.py")
    for marker in (
        "scripts/validate_issue88_deliberate_export.py",
        "scripts/check_issue88_package.py",
        "scripts/smoke_test_issue88_deliberate_export_wheel.py",
        "Portia Issue #88 repository qualification passed",
    ):
        if marker not in repository:
            raise RuntimeError(
                f"repository qualification is missing Issue #88 marker: {marker}"
            )
    print("Portia Issue #88 repository deliberate-export validation passed")


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
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
