"""Mechanically validate the Issue #48 student timeline/work-view surface."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_EXPORTS = {
    "STUDENT_VIEW_POLICY",
    "StudentChronologyService",
    "StudentHistoryResult",
    "StudentPrivacyProjectionService",
    "StudentTimelineFilter",
    "StudentTimelineQuery",
    "StudentTimelineService",
    "StudentTimelineViewResult",
    "StudentViewCurrentnessResolver",
    "StudentViewEntry",
    "StudentViewNavigationRef",
    "StudentViewScope",
    "StudentWorkDiscoveryService",
    "StudentWorkTimelineView",
}

_REQUIRED_RUNTIME = {
    "portia/views/__init__.py",
    "portia/views/chronology.py",
    "portia/views/currentness.py",
    "portia/views/discovery.py",
    "portia/views/filters.py",
    "portia/views/history.py",
    "portia/views/models.py",
    "portia/views/policy.py",
    "portia/views/projection.py",
    "portia/views/student.py",
}

_REQUIRED_ACCEPTANCE = {
    "tests/test_student_view_foundation.py",
    "tests/test_student_view_discovery.py",
    "tests/test_student_view_privacy_currentness.py",
    "tests/test_student_view_chronology_filters.py",
    "tests/test_student_view_work_history.py",
    "tests/test_issue48_acceptance_matrix.py",
    "tests/test_issue48_closeout_validation.py",
}

_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue48_package.py",
    "scripts/smoke_test_issue48_wheel.py",
    "tests/test_issue48_package_checker.py",
    "tests/test_issue48_wheel_smoke_script.py",
}

_REQUIRED_REPOSITORY = {
    ".github/workflows/ci.yml",
    "scripts/validate_repository.py",
    "tests/test_issue48_repository_qualification.py",
}

_FORBIDDEN_IDENTIFIERS = {
    "admin_mode",
    "behavior_score",
    "include_all",
    "include_private",
    "offender_count",
    "raw_record",
    "risk_score",
    "severity_score",
    "skip_redaction",
    "trust_requester",
}

_SIBLING_MODULES = {
    "concord",
    "meridian",
    "pds_concord",
    "pds_meridian",
    "pds_quillan",
    "pds_scoreform",
    "pds_vitrine",
    "quillan",
    "scoreform",
    "vitrine",
}

_REQUIRED_TESTS = {
    "test_scope_preserves_class_qualified_roster_identity",
    "test_same_local_student_id_in_two_classes_is_never_merged",
    "test_same_display_name_or_actor_identity_does_not_create_focal_match",
    "test_cross_class_event_requires_deliberate_work_owner_scope",
    "test_related_work_target_outside_scope_is_never_loaded_or_traversed",
    "test_multi_participant_event_omits_unrelated_participant_source_refs",
    "test_third_party_account_targeting_focal_student_requires_manual_review",
    "test_structured_observation_can_project_without_narrative",
    "test_restricted_communication_is_withheld_without_recipient_leak",
    "test_unavailable_is_distinct_from_absent_and_preserves_no_raw_guard_detail",
    "test_event_date_only_occurrence_stays_date_only",
    "test_account_range_preserves_source_offsets_and_range",
    "test_audit_timestamp_is_not_participant_occurrence_fallback",
    "test_filter_combines_date_family_category_status_and_safe_state",
    "test_history_keeps_current_frontier_and_exact_correction_context",
    "test_exceptional_removal_is_unavailable_not_reconstructed",
    "test_migration_context_does_not_follow_out_of_scope_legacy_source",
    "test_issue48_registry_preserves_semantic_families_and_no_score_surface",
    "test_issue48_exact_identity_ignores_equal_roster_names",
    "test_issue48_generation_is_read_only_and_groups_event_and_support",
    "test_issue48_foreign_sources_and_sibling_payloads_remain_separate",
    "test_issue48_history_inventory_keeps_correction_families_explicit",
}


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _exports(path: Path) -> set[str]:
    for node in _tree(path).body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if isinstance(node.value, (ast.List, ast.Tuple)):
            return {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            }
    return set()


def _test_names(path: Path) -> set[str]:
    return {
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _public_identifiers(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
    return names


def _imports(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(_tree(path)):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


def _source_findings(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(_REQUIRED_RUNTIME | _REQUIRED_ACCEPTANCE):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #48 source file: {relative}")

    init_path = root / "portia/views/__init__.py"
    if init_path.is_file():
        missing = sorted(_REQUIRED_EXPORTS - _exports(init_path))
        if missing:
            errors.append(f"missing Issue #48 public exports: {missing}")

    tests: set[str] = set()
    for relative in sorted(_REQUIRED_ACCEPTANCE):
        path = root / relative
        if path.is_file():
            tests.update(_test_names(path))
    missing_tests = sorted(_REQUIRED_TESTS - tests)
    if missing_tests:
        errors.append(f"missing Issue #48 acceptance tests: {missing_tests}")

    identifiers: set[str] = set()
    imported: set[str] = set()
    for relative in sorted(_REQUIRED_RUNTIME):
        path = root / relative
        if not path.is_file():
            continue
        identifiers.update(_public_identifiers(path))
        imported.update(_imports(path))
    forbidden = sorted(_FORBIDDEN_IDENTIFIERS & identifiers)
    if forbidden:
        errors.append(f"student view exposes forbidden identifiers: {forbidden}")
    sibling_imports = sorted(_SIBLING_MODULES & imported)
    if sibling_imports:
        errors.append(
            "student view imports sibling runtime modules: "
            f"{sibling_imports}"
        )

    policy = root / "portia/views/policy.py"
    if policy.is_file():
        text = policy.read_text(encoding="utf-8")
        for phrase in (
            '"student_timeline_work_view"',
            '_POLICY_VERSION: Final[str] = "1"',
            '"unknown_contract_behavior": "fail_closed"',
            "STUDENT_VIEW_PROJECTION_INVENTORY",
            "STUDENT_VIEW_CONTRACT_INVENTORY",
        ):
            if phrase not in text:
                errors.append(f"student-view policy missing frozen marker: {phrase}")

    chronology = root / "portia/views/chronology.py"
    if chronology.is_file():
        text = chronology.read_text(encoding="utf-8")
        for phrase in (
            "STUDENT_VIEW_CHRONOLOGY_INVENTORY",
            "STUDENT_VIEW_PROJECTION_INVENTORY",
            "student-view chronology inventory drift",
        ):
            if phrase not in text:
                errors.append(f"chronology registry missing marker: {phrase}")

    schemas = root / "schemas"
    forbidden_schema_tokens = (
        "student_timeline",
        "student-history",
        "student_history",
        "student_profile",
        "student-profile",
        "student_case",
        "student-case",
        "behavior_score",
        "risk_score",
    )
    for path in schemas.rglob("*.json") if schemas.is_dir() else ():
        lowered = path.relative_to(schemas).as_posix().lower()
        if any(token in lowered for token in forbidden_schema_tokens):
            errors.append(f"canonical student-view schema introduced: {lowered}")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8").lower()
        for dependency in (
            "pds-meridian",
            "pds-vitrine",
            "pds-concord",
            "pds-scoreform",
            "pds-quillan",
        ):
            if dependency in text:
                errors.append(f"Issue #48 added sibling dependency: {dependency}")
        if "pds-core>=0.6.3,<0.7" not in text:
            errors.append("Issue #48 runtime dependency no longer pins Core 0.6.x")

    errors.extend(_documentation_findings(root))
    return errors


def _documentation_findings(root: Path) -> list[str]:
    errors: list[str] = []
    required = {
        "docs/student-timeline-and-work-view.md": (
            "Exact focal identity and bounded scope",
            "Current and history modes",
            "Projection policy and privacy dispositions",
            "Record categories and semantic distinctions",
            "Chronology",
            "Filters",
            "Quarantine and Exceptional Removal",
            "Foreign-source boundary",
            "Read-only and noncanonical behavior",
            "Issue boundaries",
            "#49 owns teacher-facing attention",
            "#50 owns teacher-menu",
            "#51 owns deliberate export",
            "#52 owns suite readiness",
        ),
        "docs/validation/issue-48-student-timeline-work-view-validation.md": (
            "Issue #48 Validation",
            "2d7d41d3a391bbbfdbeb15b266c0caf693373255",
            "scripts/validate_student_views.py",
            "scripts/check_issue48_package.py",
            "scripts/smoke_test_issue48_wheel.py",
            "Final Slice 6 cumulative qualification",
        ),
        "README.md": (
            "### Issue #48 current implementation",
            "StudentTimelineService",
            "privacy-minimized student timeline and work view",
        ),
    }
    for relative, phrases in required.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing Issue #48 documentation: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{relative} missing required phrase: {phrase}")
    return errors


def _distribution_findings(root: Path) -> list[str]:
    return [
        f"missing Issue #48 distribution file: {relative}"
        for relative in sorted(_REQUIRED_DISTRIBUTION)
        if not (root / relative).is_file()
    ]


def _repository_findings(root: Path) -> list[str]:
    errors = [
        f"missing Issue #48 repository file: {relative}"
        for relative in sorted(_REQUIRED_REPOSITORY)
        if not (root / relative).is_file()
    ]
    validator = root / "scripts/validate_repository.py"
    if validator.is_file():
        text = validator.read_text(encoding="utf-8")
        for phrase in (
            "scripts/validate_student_views.py",
            "scripts/check_issue48_package.py",
            "scripts/smoke_test_issue48_wheel.py",
            "Portia Issue #48 repository qualification passed",
        ):
            if phrase not in text:
                errors.append(
                    "scripts/validate_repository.py missing Issue #48 integration: "
                    f"{phrase}"
                )
    ci = root / ".github/workflows/ci.yml"
    if ci.is_file():
        text = ci.read_text(encoding="utf-8")
        for phrase in (
            "ubuntu-latest",
            "windows-latest",
            'python: "3.11"',
            'core: "0.6.3"',
            "python scripts/validate_repository.py --core-wheel",
        ):
            if phrase not in text:
                errors.append(f"CI missing Issue #48 qualification marker: {phrase}")
    return errors


def findings(root: Path, *, stage: Stage = "repository") -> list[str]:
    errors = _source_findings(root)
    if stage in {"distribution", "repository"}:
        errors.extend(_distribution_findings(root))
    if stage == "repository":
        errors.extend(_repository_findings(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument(
        "--stage",
        choices=("source", "distribution", "repository"),
        default="repository",
    )
    args = parser.parse_args()
    try:
        errors = findings(args.root.resolve(), stage=args.stage)
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"Issue #48 validation failed: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Portia Issue #48 {args.stage} student-view validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
