"""Mechanically validate Issue #51 bounded teacher-reference exports."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_RUNTIME = {
    "portia/exports/__init__.py",
    "portia/exports/policy.py",
    "portia/exports/discovery.py",
    "portia/exports/projection.py",
    "portia/exports/inventory.py",
    "portia/exports/rendering.py",
    "portia/exports/preparation.py",
    "portia/exports/execution.py",
    "portia/exports/recovery.py",
    "portia/exports/history.py",
    "portia/menu/teacher_reference_export.py",
    "portia/menu/timeline.py",
}
_REQUIRED_TESTS = {
    "tests/test_teacher_reference_export_policy.py",
    "tests/test_teacher_reference_export_discovery.py",
    "tests/test_teacher_reference_export_projection.py",
    "tests/test_teacher_reference_export_rendering.py",
    "tests/test_teacher_reference_export_preparation.py",
    "tests/test_teacher_reference_export_execution.py",
    "tests/test_teacher_reference_export_recovery_history.py",
    "tests/test_teacher_menu_teacher_reference_export.py",
    "tests/test_issue51_acceptance_matrix.py",
    "tests/test_issue51_qualification.py",
}
_REQUIRED_DOCS = {
    "docs/README.md",
    "docs/teacher-reference-exports.md",
    "docs/validation/issue-51-acceptance-matrix.md",
    "docs/validation/issue-51-bounded-deliberate-local-exports-validation.md",
}
_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue51_package.py",
    "scripts/smoke_test_issue51_teacher_reference_export_wheel.py",
    "scripts/validate_teacher_reference_exports.py",
}


def _read(root: Path, relative: str) -> str:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"required Issue #51 file is unavailable: {relative}") from exc


def _require_files(root: Path, paths: set[str]) -> None:
    missing = sorted(relative for relative in paths if not (root / relative).is_file())
    if missing:
        raise RuntimeError(f"missing Issue #51 files: {missing}")


def _require_markers(text: str, markers: tuple[str, ...], *, label: str) -> None:
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise RuntimeError(f"{label} is missing required markers: {missing}")


def _validate_acceptance_matrix(root: Path) -> None:
    matrix = _read(root, "docs/validation/issue-51-acceptance-matrix.md")
    numbers = {
        int(value)
        for value in re.findall(r"^\|\s*(\d+)\s*\|", matrix, flags=re.MULTILINE)
    }
    expected = set(range(1, 99))
    if numbers != expected:
        missing = sorted(expected - numbers)
        extra = sorted(numbers - expected)
        raise RuntimeError(
            "Issue #51 acceptance matrix numbering is incomplete: "
            f"missing={missing}, extra={extra}"
        )


def _validate_source(root: Path) -> None:
    _require_files(root, _REQUIRED_RUNTIME | _REQUIRED_TESTS | _REQUIRED_DOCS)

    policy = _read(root, "portia/exports/policy.py")
    _require_markers(
        policy,
        (
            'TEACHER_REFERENCE_EXPORT_PURPOSES',
            '"teacher_current"',
            '"participant_specific"',
            'TeacherReferenceWorkRootContract("event", "2")',
            'TeacherReferenceWorkRootContract("support_process", "1")',
            '"never_export"',
            '"live_actor_directory_enrichment": "forbidden"',
            'require_teacher_reference_generation_authorized',
        ),
        label="teacher-reference policy",
    )

    discovery = _read(root, "portia/exports/discovery.py")
    _require_markers(
        discovery,
        (
            "ExactPortiaWorkRef",
            "ExactPortiaWorkRecordRef",
            "participant_specific",
            "correction_context",
            "disagreement_context",
            "fingerprint",
        ),
        label="teacher-reference discovery",
    )

    projection = _read(root, "portia/exports/projection.py")
    _require_markers(
        projection,
        (
            'PROJECTION_DECISION_ALGORITHM: Final[str] = "portia_projection_decision_v1"',
            '"include_exact"',
            '"omit"',
            '"requires_manual_review"',
            'manual_review',
            'projection_decision_digest',
        ),
        label="teacher-reference projection",
    )

    inventory = _read(root, "portia/exports/inventory.py")
    _require_markers(
        inventory,
        (
            'EXPORT_SOURCE_INVENTORY_ALGORITHM: Final[str] = "portia_export_source_inventory_v1"',
            "contributing_source_refs",
            "source_role",
            "fingerprint",
        ),
        label="teacher-reference source inventory",
    )

    rendering = _read(root, "portia/exports/rendering.py")
    _require_markers(
        rendering,
        (
            'TEACHER_REFERENCE_RENDERER_ID: Final[str] = "portia_deliberate_export_artifact_v1"',
            'TEACHER_REFERENCE_ARTIFACT_FORMAT: Final[str] = "html"',
            'TEACHER_REFERENCE_ARTIFACT_MEDIA_TYPE: Final[str] = "text/html"',
            "teacher-reference",
            "from html import escape",
        ),
        label="teacher-reference renderer",
    )
    if "<script" in rendering.casefold() or "javascript:" in rendering.casefold():
        raise RuntimeError("teacher-reference renderer source contains script markers")

    preparation = _read(root, "portia/exports/preparation.py")
    _require_markers(
        preparation,
        (
            "class TeacherReferenceExportPreparation",
            "preparation_digest",
            "deliberate_export",
            "operation_journal",
            "operation_lock",
            "artifact_relative_path",
            "provenance_relative_path",
        ),
        label="teacher-reference preparation",
    )
    for forbidden in (
        "stage_deliberate_export_candidates",
        "commit_deliberate_export_candidates",
        "OperationJournalStore(",
        "exclusive_create(",
    ):
        if forbidden in preparation:
            raise RuntimeError(
                "zero-write preparation contains persistence marker: " + forbidden
            )

    execution = _read(root, "portia/exports/execution.py")
    _require_markers(
        execution,
        (
            "self.revalidate(preparation)",
            "stage_deliberate_export_candidates",
            "commit_deliberate_export_candidates",
            "recover_deliberate_export_committed_revision",
            "finalize_deliberate_export",
            '"prepared_state_changed"',
            '"recovery_required"',
        ),
        label="teacher-reference execution",
    )
    revalidate_at = execution.index("self.revalidate(preparation)")
    journal_write_at = execution.index("store.create(preparation.operation_journal")
    if revalidate_at >= journal_write_at:
        raise RuntimeError("teacher-reference execution writes before final revalidation")
    execute_body = execution[execution.index("    def execute(") :]
    if "self.prepare(" in execute_body or "PreparationService(" in execute_body:
        raise RuntimeError("teacher-reference execution silently reprepares state")

    recovery = _read(root, "portia/exports/recovery.py")
    _require_markers(
        recovery,
        (
            "recover_deliberate_export_provenance",
            "recover_deliberate_export_committed_revision",
            "finalize_deliberate_export",
            "staging_path_for",
            '"artifact_only"',
            '"recovery_required"',
        ),
        label="teacher-reference recovery",
    )

    history = _read(root, "portia/exports/history.py")
    _require_markers(
        history,
        (
            '"available_verified"',
            '"artifact_missing"',
            '"artifact_mismatch"',
            '"operation_recovery_required"',
            '"provenance_invalid"',
            "validate_deliberate_export_committed_reference",
        ),
        label="teacher-reference history",
    )
    for forbidden in ("exclusive_create(", "guarded_replace(", "stage_bytes("):
        if forbidden in history:
            raise RuntimeError("read-only export history contains write marker: " + forbidden)

    menu = _read(root, "portia/menu/teacher_reference_export.py")
    timeline = _read(root, "portia/menu/timeline.py")
    _require_markers(
        menu,
        (
            "Export this work for teacher reference",
            "Export this student's view of this work",
            "View prior exports for this work",
            "TEACHER_REFERENCE_CONFIRMATION",
            "TeacherReferenceExportPreparationService",
            "TeacherReferenceExportExecutionService",
            "TeacherReferenceExportHistoryService",
            "not an official record",
            "disclosure",
            "delivery",
        ),
        label="teacher-reference menu",
    )
    _require_markers(
        timeline,
        (
            "launch_teacher_reference_work_menu",
            "from portia.menu.teacher_reference_export import (",
            "state.remember_work(",
        ),
        label="timeline contextual export integration",
    )

    main = _read(root, "portia/menu/main.py")
    if "Advanced Portia tools" not in main or "PRIMARY_TASKS" not in main:
        raise RuntimeError("Issue #50 main-menu taxonomy marker changed")
    if 'MenuTask("9", "Export' in main or 'MenuTask("10"' in main:
        raise RuntimeError("teacher-reference export widened the routine root menu")

    pyproject = _read(root, "pyproject.toml")
    runtime = pyproject.split("[project.optional-dependencies]", 1)[0].casefold()
    if "pds-core>=0.6.3,<0.7" not in runtime:
        raise RuntimeError("Issue #51 runtime no longer pins the Core 0.6.3 line")
    for sibling in ("pds-concord", "pds-meridian", "pds-quillan", "pds-scoreform", "pds-vitrine"):
        if sibling in runtime:
            raise RuntimeError(f"Issue #51 added sibling runtime dependency: {sibling}")

    _validate_acceptance_matrix(root)
    print("Portia Issue #51 source teacher-reference export validation passed")


def _validate_distribution(root: Path) -> None:
    _validate_source(root)
    _require_files(root, _REQUIRED_DISTRIBUTION)
    print("Portia Issue #51 distribution teacher-reference export validation passed")


def _validate_repository(root: Path) -> None:
    _validate_distribution(root)
    repository = _read(root, "scripts/validate_repository.py")
    for marker in (
        "scripts/validate_teacher_reference_exports.py",
        "scripts/check_issue51_package.py",
        "scripts/smoke_test_issue51_teacher_reference_export_wheel.py",
        "Portia Issue #51 repository qualification passed",
    ):
        if marker not in repository:
            raise RuntimeError(
                f"repository qualification is missing Issue #51 marker: {marker}"
            )
    print("Portia Issue #51 repository teacher-reference export validation passed")


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
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
