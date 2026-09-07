"""Mechanically validate the Issue #46 downstream workflow surface."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any, Literal

Stage = Literal["source", "distribution", "repository"]

_REQUIRED_EXPORTS = {
    "FollowUpWorkflowService",
    "OutcomeWorkflowService",
    "ReentryWorkflowService",
    "RepairWorkflowService",
    "follow_up_reference",
    "outcome_reference",
    "reentry_reference",
    "repair_reference",
}

_REQUIRED_RUNTIME = {
    "portia/workflows/action_common.py",
    "portia/workflows/action_reownership.py",
    "portia/workflows/downstream_common.py",
    "portia/workflows/downstream_lifecycle.py",
    "portia/workflows/downstream_supersession.py",
    "portia/workflows/follow_ups.py",
    "portia/workflows/outcomes.py",
    "portia/workflows/reentries.py",
    "portia/workflows/repairs.py",
}

_REQUIRED_ACCEPTANCE = {
    "tests/test_workflow_downstream_common.py",
    "tests/test_workflow_downstream_lineage.py",
    "tests/test_workflow_action_reownership.py",
    "tests/test_workflow_follow_ups.py",
    "tests/test_workflow_outcomes.py",
    "tests/test_workflow_reentries.py",
    "tests/test_workflow_repairs.py",
    "tests/test_issue46_follow_up_fixture_parity.py",
    "tests/test_issue46_outcome_fixture_parity.py",
    "tests/test_issue46_reentry_fixture_parity.py",
    "tests/test_issue46_repair_fixture_parity.py",
    "tests/test_issue46_combined_fixture_parity.py",
    "tests/test_issue46_representative_integration.py",
    "tests/test_issue46_closeout_validation.py",
}

_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue46_package.py",
    "scripts/smoke_test_issue46_wheel.py",
    "tests/test_issue46_package_checker.py",
    "tests/test_issue46_wheel_smoke_script.py",
}

_REQUIRED_REPOSITORY = {
    "scripts/validate_repository.py",
    "tests/test_issue46_repository_qualification.py",
}

_FAMILY_CONFIG: dict[str, dict[str, object]] = {
    "follow_up": {
        "manifest": "tests/schema_validation/fixtures/issue-19/follow-up/manifest.json",
        "parity": "tests/test_issue46_follow_up_fixture_parity.py",
        "workflow": "tests/test_workflow_follow_ups.py",
        "service": "FollowUpWorkflowService",
        "service_file": "portia/workflows/follow_ups.py",
        "list_method": "list_follow_ups",
        "valid": 10,
        "application_invalid": 14,
        "structural_invalid": 13,
        "workflow_progression": True,
    },
    "outcome": {
        "manifest": "tests/schema_validation/fixtures/issue-19/outcome/manifest.json",
        "parity": "tests/test_issue46_outcome_fixture_parity.py",
        "workflow": "tests/test_workflow_outcomes.py",
        "service": "OutcomeWorkflowService",
        "service_file": "portia/workflows/outcomes.py",
        "list_method": "list_outcomes",
        "valid": 13,
        "application_invalid": 17,
        "structural_invalid": 18,
        "workflow_progression": False,
    },
    "reentry": {
        "manifest": "tests/schema_validation/fixtures/issue-19/reentry/manifest.json",
        "parity": "tests/test_issue46_reentry_fixture_parity.py",
        "workflow": "tests/test_workflow_reentries.py",
        "service": "ReentryWorkflowService",
        "service_file": "portia/workflows/reentries.py",
        "list_method": "list_reentries",
        "valid": 11,
        "application_invalid": 14,
        "structural_invalid": 16,
        "workflow_progression": True,
    },
    "repair": {
        "manifest": "tests/schema_validation/fixtures/issue-19/repair/manifest.json",
        "parity": "tests/test_issue46_repair_fixture_parity.py",
        "workflow": "tests/test_workflow_repairs.py",
        "service": "RepairWorkflowService",
        "service_file": "portia/workflows/repairs.py",
        "list_method": "list_repairs",
        "valid": 12,
        "application_invalid": 19,
        "structural_invalid": 25,
        "workflow_progression": True,
    },
}

_EXPECTED_VALID = 46
_EXPECTED_APPLICATION_INVALID = 64
_EXPECTED_RUNTIME = 110
_EXPECTED_STRUCTURAL_INVALID = 72


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


def _class(path: Path, class_name: str) -> ast.ClassDef | None:
    for node in _tree(path).body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _method_names(node: ast.ClassDef) -> set[str]:
    return {
        child.name
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _base_names(node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _literal_dict(path: Path, name: str) -> dict[str, str]:
    for node in _tree(path).body:
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == name:
                value = node.value
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                value = node.value
        if value is None:
            continue
        resolved = ast.literal_eval(value)
        if not isinstance(resolved, dict):
            raise ValueError(f"{path} {name} is not a mapping")
        if not all(isinstance(key, str) for key in resolved):
            raise ValueError(f"{path} {name} has non-string keys")
        if not all(isinstance(item, str) for item in resolved.values()):
            raise ValueError(f"{path} {name} has non-string values")
        return resolved
    raise ValueError(f"{path} is missing {name}")


def _manifest(root: Path, relative: str) -> dict[str, Any]:
    value = json.loads((root / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{relative} is not a manifest object")
    return value


def _names(value: object, *, label: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} must be a string list")
    return set(value)


def _test_names(path: Path) -> set[str]:
    return {
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _service_findings(root: Path) -> list[str]:
    errors: list[str] = []
    common = root / "portia/workflows/action_common.py"
    if common.is_file():
        common_text = common.read_text(encoding="utf-8")
        for token in ("class ActionReadService", "def load_exact(", "def list("):
            if token not in common_text:
                errors.append(f"ActionReadService missing exact-read/list authority: {token}")

    for family, config in _FAMILY_CONFIG.items():
        relative = str(config["service_file"])
        service_name = str(config["service"])
        path = root / relative
        if not path.is_file():
            continue
        node = _class(path, service_name)
        if node is None:
            errors.append(f"{relative} is missing class {service_name}")
            continue
        methods = _method_names(node)
        if "ActionReadService" not in _base_names(node):
            errors.append(f"{service_name} must retain shared exact-read/list authority")

        required = {
            "create",
            str(config["list_method"]),
            "require_current_use",
            "transition_lifecycle",
            "correct",
            "correct_work_root",
            "consolidate_duplicates",
        }
        if bool(config["workflow_progression"]):
            required.add("transition_workflow_state")
        missing = sorted(required - methods)
        if missing:
            errors.append(f"{service_name} missing required operations: {missing}")
        if family == "outcome" and "transition_workflow_state" in methods:
            errors.append("OutcomeWorkflowService must not invent mutable workflow state")
        amendment = sorted(name for name in methods if "amend" in name.lower())
        if amendment:
            errors.append(f"{service_name} must not expose v1 Amendment: {amendment}")

        text = path.read_text(encoding="utf-8")
        if "resolve_current = require_current_use" not in text:
            errors.append(f"{service_name} must retain explicit current-use alias")

    token_checks = {
        "portia/workflows/follow_ups.py": (
            '"scheduled"', '"in_progress"', '"completed"',
            '"cancelled"', '"unable_to_complete"',
        ),
        "portia/workflows/reentries.py": (
            '"planned"', '"active"', '"completed"',
            '"cancelled"', '"unable_to_complete"',
        ),
        "portia/workflows/repairs.py": (
            '"planning"', '"active"', '"completed"',
            '"cancelled"', '"unable_to_complete"',
        ),
        "portia/workflows/downstream_supersession.py": (
            '"duplicate_consolidated"', '"work_root_corrected"',
        ),
    }
    for relative, tokens in token_checks.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in tokens:
            if token not in text:
                errors.append(f"{relative} missing accepted Issue #46 token: {token}")
    return errors


def _parity_findings(root: Path) -> list[str]:
    errors: list[str] = []
    valid_total = 0
    application_total = 0
    runtime_total = 0
    structural_total = 0

    for family, config in _FAMILY_CONFIG.items():
        try:
            manifest = _manifest(root, str(config["manifest"]))
            valid = _names(manifest.get("valid"), label=f"{family} valid")
            application_invalid = _names(
                manifest.get("application_invalid"),
                label=f"{family} application_invalid",
            )
            structural = _names(manifest.get("invalid"), label=f"{family} invalid")
            parity_path = root / str(config["parity"])
            workflow_path = root / str(config["workflow"])
            coverage = _literal_dict(parity_path, "COVERAGE")
            expected_errors = _literal_dict(parity_path, "EXPECTED_ERRORS")
            workflow_tests = _test_names(workflow_path)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"{family} parity metadata could not be read: {exc}")
            continue

        expected_counts = (
            int(config["valid"]),
            int(config["application_invalid"]),
            int(config["structural_invalid"]),
        )
        observed_counts = (len(valid), len(application_invalid), len(structural))
        if observed_counts != expected_counts:
            errors.append(
                f"{family} frozen counts drifted: {observed_counts} != {expected_counts}"
            )

        expected_runtime = valid | application_invalid
        if set(coverage) != expected_runtime:
            errors.append(f"{family} runtime COVERAGE no longer matches its manifest")
        missing_tests = sorted(set(coverage.values()) - workflow_tests)
        if missing_tests:
            errors.append(f"{family} COVERAGE maps to missing workflow tests: {missing_tests}")
        if set(expected_errors) != application_invalid:
            errors.append(f"{family} application-invalid error evidence drifted")
        empty_errors = sorted(name for name, value in expected_errors.items() if not value.strip())
        if empty_errors:
            errors.append(f"{family} has empty expected-error evidence: {empty_errors}")
        overlap = structural & set(coverage)
        if overlap:
            errors.append(
                f"{family} structural-invalid cases leaked into runtime parity: {sorted(overlap)}"
            )

        valid_total += len(valid)
        application_total += len(application_invalid)
        runtime_total += len(expected_runtime)
        structural_total += len(structural)

    observed = (valid_total, application_total, runtime_total, structural_total)
    expected = (
        _EXPECTED_VALID,
        _EXPECTED_APPLICATION_INVALID,
        _EXPECTED_RUNTIME,
        _EXPECTED_STRUCTURAL_INVALID,
    )
    if observed != expected:
        errors.append(f"Issue #46 aggregate parity drifted: {observed} != {expected}")
    return errors


def _documentation_findings(root: Path) -> list[str]:
    errors: list[str] = []
    required_docs = {
        "docs/follow-up-outcome-reentry-repair-workflows.md": (
            "FollowUpWorkflowService",
            "OutcomeWorkflowService",
            "ReentryWorkflowService",
            "RepairWorkflowService",
            "46 valid + 64 application-invalid = 110 runtime scenarios",
            "72 structural-invalid fixtures",
            "P22-08",
            "P22-11",
            "Reentry completed != safety/medical clearance",
            "Repair participation != admission != remorse != forgiveness",
            "later Outcome for a later timeframe != correction",
        ),
        "docs/validation/issue-46-follow-up-outcome-reentry-repair-workflows-validation.md": (
            "328 passed in 28.58s",
            "62 Issue #19 contract tests passed",
            "170 regression tests passed",
            "Success: no issues found in 119 source files",
            "source/runtime, distribution, and cumulative repository qualification observed",
            "Portia Issue #46 source workflow validation passed",
            "Portia Issue #46 package inventory validation passed",
            "Portia installed-wheel Issue #46 downstream workflow smoke test passed",
            "Portia Issue #46 repository qualification passed",
            "full-repository pytest summary count is not preserved",
            "--stage source",
            "--stage distribution",
            "--stage repository",
        ),
        "README.md": (
            "### Issue #46 current implementation",
            "110 schema-valid runtime scenarios",
            "FollowUpWorkflowService",
            "RepairWorkflowService",
        ),
        "docs/implementation-and-fidelity-workflows.md": (
            "Issue #46 now supplies the production Follow-Up/Outcome/Reentry/Repair layer",
        ),
        "docs/support-process-support-intervention-workflows.md": (
            "Issue #46 now supplies the production Follow-Up/Outcome/Reentry/Repair layer",
        ),
    }
    for relative, phrases in required_docs.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"missing Issue #46 documentation: {relative}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{relative} missing required phrase: {phrase}")

    stale_checks = {
        "README.md": (
            "Issue #46 remains responsible for Follow-Up/Outcome/Reentry/Repair",
        ),
        "docs/implementation-and-fidelity-workflows.md": (
            "Follow-Up, Outcome, Reentry, and Repair remain Issue #46-owned",
            "Those remain Issue #46 concerns.",
        ),
        "docs/support-process-support-intervention-workflows.md": (
            "Follow-Up, Outcome, Reentry, and Repair remain Issue #46-owned",
        ),
    }
    for relative, stale_phrases in stale_checks.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in stale_phrases:
            if phrase in text:
                errors.append(f"{relative} retains stale pre-Issue #46 wording: {phrase}")
    return errors


def _representative_findings(root: Path) -> list[str]:
    path = root / "tests/test_issue46_representative_integration.py"
    if not path.is_file():
        return []
    try:
        tests = _test_names(path)
    except (OSError, SyntaxError) as exc:
        return [f"representative integration could not be read: {exc}"]

    required = {
        "P22-08": "test_p22_08_",
        "P22-09": "test_p22_09_",
        "P22-10": "test_p22_10_",
        "P22-11": "test_p22_11_",
    }
    errors: list[str] = []
    for scenario, prefix in required.items():
        if not any(name.startswith(prefix) for name in tests):
            errors.append(f"representative integration is missing {scenario}")
    return errors


def _distribution_findings(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(_REQUIRED_DISTRIBUTION):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #46 distribution file: {relative}")
    return errors


def _repository_findings(root: Path) -> list[str]:
    errors: list[str] = []
    for relative in sorted(_REQUIRED_REPOSITORY):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #46 repository file: {relative}")

    validator = root / "scripts/validate_repository.py"
    if validator.is_file():
        text = validator.read_text(encoding="utf-8")
        for phrase in (
            "scripts/validate_issue46_workflows.py",
            "scripts/check_issue46_package.py",
            "scripts/smoke_test_issue46_wheel.py",
            "Portia Issue #46 repository qualification passed",
        ):
            if phrase not in text:
                errors.append(f"scripts/validate_repository.py missing Issue #46 integration: {phrase}")
    return errors


def findings(root: Path, *, stage: Stage = "repository") -> list[str]:
    errors: list[str] = []
    for relative in sorted(_REQUIRED_RUNTIME | _REQUIRED_ACCEPTANCE):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #46 source file: {relative}")

    init_path = root / "portia/workflows/__init__.py"
    if not init_path.is_file():
        errors.append("missing public workflow package: portia/workflows/__init__.py")
    else:
        missing = sorted(_REQUIRED_EXPORTS - _exports(init_path))
        if missing:
            errors.append(f"missing Issue #46 public exports: {missing}")

    errors.extend(_service_findings(root))
    errors.extend(_parity_findings(root))
    errors.extend(_representative_findings(root))
    errors.extend(_documentation_findings(root))

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
        help="qualification layer to require (default: repository)",
    )
    args = parser.parse_args()
    try:
        errors = findings(args.root.resolve(), stage=args.stage)
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"ERROR: Issue #46 validation could not run: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"Portia Issue #46 {args.stage} workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
