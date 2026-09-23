"""Mechanically validate the Issue #49 native attention query surface."""

from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_RUNTIME = {
    "portia/attention/__init__.py",
    "portia/attention/models.py",
    "portia/attention/taxonomy.py",
    "portia/attention/timing.py",
    "portia/attention/workflow_sources.py",
    "portia/attention/operational_sources.py",
    "portia/attention/derived_sources.py",
    "portia/attention/scope.py",
}
_REQUIRED_TESTS = {
    "tests/test_attention_foundation.py",
    "tests/test_attention_follow_up_timing.py",
    "tests/test_attention_follow_up_schedule.py",
    "tests/test_attention_reviews.py",
    "tests/test_attention_support_processes.py",
    "tests/test_attention_operational_sources.py",
    "tests/test_attention_derived_state.py",
    "tests/test_attention_orchestration.py",
    "tests/test_attention_privacy.py",
    "tests/test_attention_acceptance_matrix.py",
}
_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue49_package.py",
    "scripts/smoke_test_issue49_wheel.py",
}
_REQUIRED_DOCS = {
    "docs/due-follow-up-and-attention-queries.md",
    "docs/validation/issue-49-attention-query-validation.md",
}
_REQUIRED_CODES = {
    "portia_follow_up_due",
    "portia_follow_up_overdue",
    "portia_review_incomplete",
    "portia_integrity_conflict",
    "portia_integrity_review_required",
    "portia_recovery_required",
    "portia_quarantine_active",
    "portia_derived_state_stale",
    "portia_support_process_review_due",
    "portia_support_process_review_overdue",
    "portia_support_process_dependency_attention",
}
_FORBIDDEN_IDENTIFIERS = {
    "attention_score",
    "behavior_score",
    "offender_count",
    "priority_score",
    "risk_score",
    "severity_score",
    "student_ranking",
    "urgency_score",
    "raw_record",
    "skip_redaction",
    "trust_requester",
}
_SIBLING_RUNTIME_NAMES = {
    "concord",
    "meridian",
    "quillan",
    "scoreform",
    "vitrine",
}


def _read(root: Path, relative: str) -> str:
    path = root / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"required Issue #49 file is unavailable: {relative}"
        ) from exc


def _require_files(root: Path, paths: set[str]) -> None:
    missing = sorted(
        relative for relative in paths if not (root / relative).is_file()
    )
    if missing:
        raise RuntimeError(f"missing Issue #49 files: {missing}")


def _python_names(root: Path) -> set[str]:
    found: set[str] = set()
    for relative in sorted(_REQUIRED_RUNTIME):
        tree = ast.parse(_read(root, relative), filename=relative)
        for node in ast.walk(tree):
            if isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            ):
                found.add(node.name)
            elif isinstance(node, ast.Name):
                found.add(node.id)
            elif isinstance(node, ast.Attribute):
                found.add(node.attr)
    return found


def _validate_source(root: Path) -> None:
    _require_files(root, _REQUIRED_RUNTIME | _REQUIRED_TESTS | _REQUIRED_DOCS)

    public = _read(root, "portia/attention/__init__.py")
    for required in (
        "AttentionQueryService",
        "FollowUpScheduleQueryService",
        "PortiaAttentionQuery",
        "FollowUpScheduleQuery",
        "PortiaAttentionScope",
        "ATTENTION_DEFINITIONS",
    ):
        if required not in public:
            raise RuntimeError(
                f"native attention public surface is missing {required}"
            )

    models = _read(root, "portia/attention/models.py")
    for marker in (
        "as_of: ExplicitOffsetTimestamp",
        'AttentionScopeKind: TypeAlias = Literal["workspace", "class", "work"]',
        'AttentionEvaluation: TypeAlias = Literal["evaluated", "unavailable"]',
        "PORTIA_ATTENTION_PARTIAL_NOTICE",
        "PORTIA_ATTENTION_UNAVAILABLE_NOTICE",
    ):
        if marker not in models:
            raise RuntimeError(f"attention contract marker is missing: {marker}")

    taxonomy = _read(root, "portia/attention/taxonomy.py")
    missing_codes = sorted(
        code for code in _REQUIRED_CODES if code not in taxonomy
    )
    if missing_codes:
        raise RuntimeError(
            f"attention taxonomy is missing codes: {missing_codes}"
        )

    timing = _read(root, "portia/attention/timing.py")
    for forbidden in (
        "datetime.now(",
        "datetime.utcnow(",
        "date.today(",
        "time.time(",
    ):
        if forbidden in timing:
            raise RuntimeError(
                "attention timing classifier uses an implicit wall clock"
            )
    if "classify_follow_up_timing" not in timing:
        raise RuntimeError("Follow-Up timing classifier is missing")

    sources = "\n".join(
        _read(root, relative)
        for relative in sorted(_REQUIRED_RUNTIME)
    )
    names = _python_names(root)
    present_forbidden = sorted(_FORBIDDEN_IDENTIFIERS & names)
    if present_forbidden:
        raise RuntimeError(
            "forbidden attention API identifiers are present: "
            f"{present_forbidden}"
        )
    if re.search(r"\b(name|display_name)\s*==", sources):
        raise RuntimeError("attention source contains name/display-name matching")
    if "fuzzy" in sources.lower():
        raise RuntimeError("attention source contains fuzzy-resolution language")

    workflow = _read(root, "portia/attention/workflow_sources.py")
    operational = _read(root, "portia/attention/operational_sources.py")
    derived = _read(root, "portia/attention/derived_sources.py")
    combined = workflow + operational + derived
    for forbidden in (
        "restore_exact_orphan_pointer(",
        "release_quarantine(",
        "acknowledge_finding(",
        "suppress_finding(",
        ".install(",
    ):
        if forbidden in combined:
            raise RuntimeError(
                f"attention read surface contains mutation/rebuild call: {forbidden}"
            )

    if "DERIVED_ATTENTION_PROJECTIONS" not in derived:
        raise RuntimeError("closed derived attention registry is missing")
    if "active_integrity_finding_index" not in derived:
        raise RuntimeError(
            "required production derived projection is unregistered"
        )
    if "st_mtime" in derived or ".stat(" in derived:
        raise RuntimeError("derived attention uses filesystem age/mtime semantics")

    schemas = root / "schemas"
    if schemas.is_dir():
        for path in schemas.rglob("*.json"):
            if "attention" in path.name.lower():
                raise RuntimeError(
                    "Issue #49 must not add a canonical attention schema"
                )

    pyproject = _read(root, "pyproject.toml").lower()
    runtime_section = pyproject.split("[project]", 1)[1].split(
        "[project.scripts]", 1
    )[0]
    for sibling in _SIBLING_RUNTIME_NAMES:
        if sibling in runtime_section:
            raise RuntimeError(
                f"unexpected sibling runtime dependency in Issue #49: {sibling}"
            )
    if "paper_data_suite.modules" in pyproject:
        raise RuntimeError(
            "#52 Core module-operations provider is registered early"
        )

    docs = _read(root, "docs/due-follow-up-and-attention-queries.md")
    for required in (
        "Follow-Up schedule",
        "portia_follow_up_due",
        "portia_integrity_conflict",
        "portia_derived_state_stale",
        "partial",
        "unavailable",
        "Issue #50",
        "Issue #52",
        "No behavior/risk/urgency/priority score",
    ):
        if required not in docs:
            raise RuntimeError(
                f"Issue #49 documentation is missing: {required}"
            )

    print("Portia Issue #49 source attention-query validation passed")


def _validate_distribution(root: Path) -> None:
    _validate_source(root)
    _require_files(root, _REQUIRED_DISTRIBUTION)
    print("Portia Issue #49 distribution attention-query validation passed")


def _validate_repository(root: Path) -> None:
    _validate_distribution(root)
    repository = _read(root, "scripts/validate_repository.py")
    for required in (
        "scripts/validate_attention_queries.py",
        "scripts/check_issue49_package.py",
        "scripts/smoke_test_issue49_wheel.py",
        "Portia Issue #49 repository qualification passed",
    ):
        if required not in repository:
            raise RuntimeError(
                "repository qualification is missing Issue #49 marker: "
                f"{required}"
            )
    ci = _read(root, ".github/workflows/ci.yml")
    if "ubuntu-latest" not in ci or "windows-latest" not in ci:
        raise RuntimeError("durable CI no longer covers Windows and Ubuntu")
    if 'core: "0.6.3"' not in ci:
        raise RuntimeError("durable CI no longer authenticates Core 0.6.3")
    print("Portia Issue #49 repository attention-query validation passed")


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
    except (OSError, RuntimeError, SyntaxError) as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
