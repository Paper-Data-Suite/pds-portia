"""Mechanically validate the final Issue #47 authority and closeout surface."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Literal

Stage = Literal["source", "distribution", "repository"]

_SERVICES: dict[str, tuple[str, frozenset[str]]] = {
    "LifecycleWorkflowService": (
        "portia/workflows/lifecycle.py",
        frozenset({
            "load_history",
            "require_reconciled",
            "load_correction_history",
            "require_corrected_history_reconciled",
            "correct_history",
            "transition",
        }),
    ),
    "AmendmentWorkflowService": (
        "portia/workflows/amendments.py",
        frozenset({"load_history", "require_reconciled", "apply_amendment"}),
    ),
    "StatementOfDisagreementWorkflowService": (
        "portia/workflows/disagreements.py",
        frozenset({
            "create",
            "load_exact",
            "require_current_use",
            "transition_lifecycle",
            "correct",
            "consolidate_duplicates",
        }),
    ),
    "DependencyWorkflowService": (
        "portia/workflows/dependencies.py",
        frozenset({
            "create",
            "load_exact",
            "evaluate_condition",
            "evaluate_gate",
            "require_graph_valid",
        }),
    ),
    "RecordMigrationWorkflowService": (
        "portia/workflows/migrations.py",
        frozenset({
            "register_transformer",
            "can_migrate",
            "plan_migration",
            "commit_migration",
        }),
    ),
    "OwnershipCorrectionWorkflowService": (
        "portia/workflows/ownership_correction.py",
        frozenset({"assess_correction", "correct_work_root", "resolve_correction"}),
    ),
    "ExceptionalRemovalWorkflowService": (
        "portia/workflows/exceptional_removal.py",
        frozenset({
            "assess_removal",
            "exceptionally_remove",
            "recover_operation",
            "resolve_removal_state",
            "require_current_use",
        }),
    ),
    "RecoveryWorkflowService": (
        "portia/workflows/recovery.py",
        frozenset({
            "assess",
            "resume_incomplete",
            "reconcile_as_complete",
            "finalize_post_commit",
            "restore_exact_orphan_pointer",
            "resume_exceptional_removal",
        }),
    ),
    "IntegrityWorkflowService": (
        "portia/workflows/integrity.py",
        frozenset({
            "current_findings",
            "acknowledge_finding",
            "suppress_finding",
            "require_effect_allowed",
            "require_operation_completion",
        }),
    ),
}

_RUNTIME_FILES = {
    *(module for module, _methods in _SERVICES.values()),
    "portia/workflows/lifecycle_history.py",
    "portia/workflows/action_reownership.py",
    "portia/workflows/quarantine.py",
    "portia/storage/actor_directory.py",
    "portia/storage/canonical_removal.py",
    "portia/storage/integrity.py",
    "portia/storage/operation_journal.py",
    "portia/storage/quarantine.py",
    "portia/storage/recovery.py",
    "portia/storage/series.py",
}

_SOURCE_EVIDENCE = {
    "tests/test_workflow_issue47_closeout.py": {
        "test_final_issue47_public_services_are_bounded_and_exported",
        "test_final_issue47_runtime_version_authority_is_explicit",
        "test_final_issue47_repository_validator_accepts_closeout",
    },
    "tests/test_workflow_issue22_judgment_parity.py": {
        "test_p22_04_account_correction_preserves_review_exact_historical_evidence"
    },
    "tests/test_workflow_recovery_p22_14.py": {
        "test_p22_14_production_recovery_preserves_successor_and_finishes_predecessor"
    },
    "tests/test_workflow_ownership_correction.py": set(),
    "tests/test_workflow_exceptional_removal.py": set(),
    "tests/test_workflow_integrity_operators.py": {
        "test_acknowledgement_is_exact_append_only_and_never_clears_blocker",
        "test_error_critical_blocking_and_quarantine_findings_cannot_be_suppressed",
        "test_shared_completion_gate_ignores_acknowledgement_and_rejects_suppression",
    },
    "tests/test_workflow_quarantine.py": {
        "test_active_work_quarantine_blocks_production_lifecycle_transition"
    },
}

_DOC = "docs/validation/issue-47-lifecycle-correction-recovery-services-validation.md"

_CONTRACTS = {
    ("ownership_correction", "1"): "historical_read",
    ("ownership_correction", "2"): "current_v0_2",
    ("operation_journal", "2"): "supporting_v0_2",
    ("operation_journal", "3"): "supporting_v0_2",
    ("exceptional_removal", "1"): "supporting_v0_2",
    ("actor_directory_exceptional_removal", "1"): "supporting_v0_2",
    ("quarantine_record", "2"): "supporting_v0_2",
    ("integrity_finding", "2"): "supporting_v0_2",
    ("finding_acknowledgement", "1"): "supporting_v0_2",
    ("finding_suppression", "1"): "supporting_v0_2",
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
        value = ast.literal_eval(node.value)
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return set(value)
    return set()


def _class_methods(path: Path, name: str) -> set[str] | None:
    for node in _tree(path).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not child.name.startswith("_")
            }
    return None


def _test_names(path: Path) -> set[str]:
    return {
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _literal_string_set(path: Path, name: str) -> set[str]:
    for node in _tree(path).body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is not None:
            resolved = ast.literal_eval(value)
            if isinstance(resolved, set) and all(
                isinstance(item, str) for item in resolved
            ):
                return resolved
            raise ValueError(f"{path} {name} is not a literal string set")
    raise ValueError(f"{path} is missing {name}")


def _source_findings(root: Path) -> list[str]:
    errors: list[str] = []
    public = root / "portia/workflows/__init__.py"
    exports = _exports(public) if public.is_file() else set()
    if not public.is_file():
        errors.append("missing public workflow package")

    for service, (relative, required_methods) in _SERVICES.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing Issue #47 service module: {relative}")
            continue
        methods = _class_methods(path, service)
        if methods is None:
            errors.append(f"{relative} is missing {service}")
            continue
        missing_methods = sorted(required_methods - methods)
        if missing_methods:
            errors.append(f"{service} missing bounded public methods: {missing_methods}")
        forbidden = sorted({"delete", "move", "resolve_latest"} & methods)
        if forbidden:
            errors.append(f"{service} exposes forbidden arbitrary methods: {forbidden}")
        if service not in exports:
            errors.append(f"{service} is not exported from portia.workflows")

    if "ActionOwnershipCorrectionCoordinator" in exports:
        errors.append("internal ownership coordinator leaked into public exports")

    identity = root / "portia/identity/__init__.py"
    if not identity.is_file() or "ActorDirectoryService" not in _exports(identity):
        errors.append("ActorDirectoryService is not publicly exported")

    for relative in sorted(_RUNTIME_FILES):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #47 runtime module: {relative}")

    for relative, required_tests in _SOURCE_EVIDENCE.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing Issue #47 acceptance evidence: {relative}")
            continue
        missing_tests = sorted(required_tests - _test_names(path))
        if missing_tests:
            errors.append(f"{relative} missing acceptance tests: {missing_tests}")

    coverage = json.loads((root / "portia/runtime-coverage.json").read_text("utf-8"))
    observed = {
        (entry["contract"], entry["version"]): entry["disposition"]
        for entry in coverage["contracts"]
        if entry.get("modelled") is True
    }
    for key, disposition in _CONTRACTS.items():
        if observed.get(key) != disposition:
            errors.append(
                f"runtime coverage authority drifted for {key[0]}@{key[1]}: "
                f"{observed.get(key)!r} != {disposition!r}"
            )

    bundle = json.loads((root / "portia/_runtime_contract_bundle.json").read_text("utf-8"))
    contracts = bundle.get("contracts", {})
    for contract, version in _CONTRACTS:
        if version not in contracts.get(contract, {}):
            errors.append(f"runtime bundle missing {contract}@{version}")

    doc = root / _DOC
    if not doc.is_file():
        errors.append(f"missing final Issue #47 validation document: {_DOC}")
    else:
        text = doc.read_text(encoding="utf-8")
        for phrase in (
            "Final responsibility matrix",
            "P22-04",
            "P22-14",
            "Graph-invalid traceability",
            "No-silent-successor audit",
            "Current-use fail-closed audit",
            "Privacy audit",
            "Issue #49",
            "manual-review-only by accepted architecture",
            "deferred by explicit issue boundary",
        ):
            if phrase not in text:
                errors.append(f"{_DOC} missing required section/evidence: {phrase}")
        if "| BLOCKER |" in text:
            errors.append(f"{_DOC} contains an unresolved BLOCKER classification")
    return errors


def _distribution_findings(root: Path) -> list[str]:
    errors: list[str] = []
    checker = root / "scripts/check_package.py"
    smoke = root / "scripts/smoke_test_wheel.py"
    if not checker.is_file():
        return ["missing current package checker"]
    if not smoke.is_file():
        return ["missing installed-wheel smoke"]

    runtime = _literal_string_set(checker, "REQUIRED_RUNTIME_FILES")
    missing_runtime = sorted(_RUNTIME_FILES - runtime)
    if missing_runtime:
        errors.append(f"package inventory missing Issue #47 runtime: {missing_runtime}")

    sdist = _literal_string_set(checker, "REQUIRED_SDIST_FILES")
    required_sdist = {
        _DOC,
        "scripts/validate_issue47_workflows.py",
        "scripts/smoke_test_wheel.py",
        "tests/test_workflow_issue47_closeout.py",
        "docs/decisions/0018-represent-verified-canonical-absence-in-operation-journals.md",
        "docs/decisions/0019-generalize-child-work-root-ownership-correction.md",
    }
    missing_sdist = sorted(required_sdist - sdist)
    if missing_sdist:
        errors.append(f"sdist inventory missing Issue #47 closeout: {missing_sdist}")

    smoke_tree = _tree(smoke)
    smoke_functions = {
        node.name for node in smoke_tree.body if isinstance(node, ast.FunctionDef)
    }
    if "_issue47_authority_smoke" not in smoke_functions:
        errors.append("installed-wheel smoke lacks compact Issue #47 authority coverage")
    smoke_text = smoke.read_text(encoding="utf-8")
    for service in _SERVICES:
        if service not in smoke_text:
            errors.append(f"installed-wheel smoke does not import {service}")
    return errors


def _repository_findings(root: Path) -> list[str]:
    validator = root / "scripts/validate_repository.py"
    if not validator.is_file():
        return ["missing repository qualification script"]
    text = validator.read_text(encoding="utf-8")
    required = (
        "scripts/validate_issue47_workflows.py",
        "--stage",
        "repository",
        "Portia Issue #47 repository qualification passed",
    )
    return [
        f"repository qualification missing Issue #47 integration: {phrase}"
        for phrase in required
        if phrase not in text
    ]


def findings(root: Path, *, stage: Stage = "repository") -> list[str]:
    errors = _source_findings(root)
    if stage in {"distribution", "repository"}:
        errors.extend(_distribution_findings(root))
    if stage == "repository":
        errors.extend(_repository_findings(root))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--stage",
        choices=("source", "distribution", "repository"),
        default="repository",
    )
    args = parser.parse_args()
    try:
        errors = findings(args.root.resolve(), stage=args.stage)
    except (KeyError, OSError, SyntaxError, TypeError, ValueError) as exc:
        print(f"ERROR: Issue #47 validation could not run: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Portia Issue #47 {args.stage} workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
