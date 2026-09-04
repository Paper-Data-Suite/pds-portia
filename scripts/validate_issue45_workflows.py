"""Mechanically validate the Issue #45 Implementation/Fidelity workflow surface."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

_REQUIRED_EXPORTS = {
    "FidelityWorkflowService",
    "ImplementationWorkflowService",
    "fidelity_reference",
    "implementation_reference",
}

_REQUIRED_RUNTIME = {
    "portia/workflows/action_common.py",
    "portia/workflows/action_consolidation.py",
    "portia/workflows/action_reownership.py",
    "portia/workflows/fidelity.py",
    "portia/workflows/fidelity_lifecycle.py",
    "portia/workflows/fidelity_supersession.py",
    "portia/workflows/implementation_lifecycle.py",
    "portia/workflows/implementation_supersession.py",
    "portia/workflows/implementations.py",
}

_REQUIRED_ACCEPTANCE = {
    "tests/test_issue45_cross_family_integration.py",
    "tests/test_issue45_fidelity_fixture_parity.py",
    "tests/test_issue45_implementation_fixture_parity.py",
    "tests/test_issue45_issue18_runtime_parity_guard.py",
    "tests/test_issue45_issue22_representative_acceptance.py",
    "tests/test_workflow_fidelity.py",
    "tests/test_workflow_implementations.py",
}

_REQUIRED_DISTRIBUTION = {
    "scripts/check_issue45_package.py",
    "scripts/smoke_test_issue45_wheel.py",
    "tests/test_issue45_package_checker.py",
    "tests/test_issue45_wheel_smoke_script.py",
}

_REQUIRED_REPOSITORY = {
    "scripts/validate_repository.py",
    "tests/test_issue45_repository_qualification.py",
}

_FAMILY_CONFIG = {
    "implementation": {
        "parity": "tests/test_issue45_implementation_fixture_parity.py",
        "workflow": "tests/test_workflow_implementations.py",
        "valid": 10,
        "application_invalid": 22,
        "structural_invalid": 17,
    },
    "fidelity": {
        "parity": "tests/test_issue45_fidelity_fixture_parity.py",
        "workflow": "tests/test_workflow_fidelity.py",
        "valid": 9,
        "application_invalid": 21,
        "structural_invalid": 21,
    },
}

_SERVICE_FILES = {
    "ImplementationWorkflowService": "portia/workflows/implementations.py",
    "FidelityWorkflowService": "portia/workflows/fidelity.py",
}

_REQUIRED_SOURCE_TOKENS = {
    "ImplementationWorkflowService": {
        "def create(",
        "def load_exact(",
        "resolve_exact = load_exact",
        "def list(",
        "list_implementations = list",
        "def require_current_use(",
        "resolve_current = require_current_use",
        "def transition_lifecycle(",
        "def transition_execution_state(",
        "def correct(",
        "def correct_work_root(",
        "def consolidate_duplicates(",
    },
    "FidelityWorkflowService": {
        "def create(",
        "def load_exact(",
        "resolve_exact = load_exact",
        "def list(",
        "list_fidelity_records = list",
        "def require_current_use(",
        "resolve_current = require_current_use",
        "def transition_lifecycle(",
        "def correct(",
        "def correct_work_root(",
        "def consolidate_duplicates(",
    },
}

_EXPECTED_RUNTIME_COUNT = 62
_EXPECTED_STRUCTURAL_INVALID_COUNT = 38


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


def _class_methods(path: Path, class_name: str) -> set[str]:
    for node in _tree(path).body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                child.name
                for child in node.body
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    return set()


def _manifest(root: Path, family: str) -> dict[str, Any]:
    path = root / "tests/schema_validation/fixtures/issue-18" / family / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(root)} is not a manifest object")
    return value


def _entry_name(value: object) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        raise ValueError("fixture manifest entry is not a string or object")
    name = value.get("file", value.get("name"))
    if not isinstance(name, str):
        raise ValueError("fixture manifest entry has no string file/name")
    return name


def _manifest_names(manifest: dict[str, Any], key: str) -> set[str]:
    values = manifest.get(key, ())
    if not isinstance(values, list):
        raise ValueError(f"manifest {key} must be a list")
    return {_entry_name(value) for value in values}


def _application_invalid(manifest: dict[str, Any]) -> dict[str, str]:
    values = manifest.get("application_invalid", ())
    if not isinstance(values, list):
        raise ValueError("manifest application_invalid must be a list")
    result: dict[str, str] = {}
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("application-invalid entry must be an object")
        name = _entry_name(value)
        expected_error = value.get("expected_error")
        if not isinstance(expected_error, str) or not expected_error.strip():
            raise ValueError(f"{name} has no frozen expected_error")
        result[name] = expected_error
    return result


def _coverage(path: Path) -> dict[str, str]:
    for node in _tree(path).body:
        value: ast.expr | None = None
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "COVERAGE":
                value = node.value
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "COVERAGE"
                for target in node.targets
            ):
                value = node.value
        if value is None:
            continue
        resolved = ast.literal_eval(value)
        if not isinstance(resolved, dict):
            raise ValueError(f"{path} COVERAGE is not a mapping")
        if not all(isinstance(key, str) for key in resolved):
            raise ValueError(f"{path} COVERAGE contains a non-string key")
        if not all(isinstance(item, str) for item in resolved.values()):
            raise ValueError(f"{path} COVERAGE contains a non-string test name")
        return resolved
    raise ValueError(f"{path} is missing COVERAGE")


def _test_names(path: Path) -> set[str]:
    return {
        node.name
        for node in _tree(path).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _parity_findings(root: Path) -> list[str]:
    errors: list[str] = []
    runtime_count = 0
    structural_count = 0

    for family, config in _FAMILY_CONFIG.items():
        try:
            manifest = _manifest(root, family)
            valid = _manifest_names(manifest, "valid")
            application_invalid = _application_invalid(manifest)
            structural = _manifest_names(manifest, "invalid")
            parity_path = root / str(config["parity"])
            workflow_path = root / str(config["workflow"])
            coverage = _coverage(parity_path)
            workflow_tests = _test_names(workflow_path)
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"{family} parity metadata could not be read: {exc}")
            continue

        expected_valid = int(config["valid"])
        expected_application_invalid = int(config["application_invalid"])
        expected_structural = int(config["structural_invalid"])
        if len(valid) != expected_valid:
            errors.append(
                f"{family} valid count drifted: {len(valid)} != {expected_valid}"
            )
        if len(application_invalid) != expected_application_invalid:
            errors.append(
                f"{family} application-invalid count drifted: "
                f"{len(application_invalid)} != {expected_application_invalid}"
            )
        if len(structural) != expected_structural:
            errors.append(
                f"{family} structural-invalid count drifted: "
                f"{len(structural)} != {expected_structural}"
            )

        expected_runtime = valid | set(application_invalid)
        if set(coverage) != expected_runtime:
            errors.append(f"{family} runtime COVERAGE no longer matches its manifest")
        missing_tests = sorted(set(coverage.values()) - workflow_tests)
        if missing_tests:
            errors.append(
                f"{family} COVERAGE maps to missing workflow tests: {missing_tests}"
            )
        overlap = structural & set(coverage)
        if overlap:
            errors.append(
                f"{family} structural-invalid cases leaked into runtime parity: "
                f"{sorted(overlap)}"
            )

        runtime_count += len(expected_runtime)
        structural_count += len(structural)

    if runtime_count != _EXPECTED_RUNTIME_COUNT:
        errors.append(
            f"Issue #45 runtime oracle count drifted: "
            f"{runtime_count} != {_EXPECTED_RUNTIME_COUNT}"
        )
    if structural_count != _EXPECTED_STRUCTURAL_INVALID_COUNT:
        errors.append(
            "Issue #45 structural-invalid count drifted: "
            f"{structural_count} != {_EXPECTED_STRUCTURAL_INVALID_COUNT}"
        )
    return errors


def findings(root: Path) -> list[str]:
    errors: list[str] = []

    required_files = (
        _REQUIRED_RUNTIME
        | _REQUIRED_ACCEPTANCE
        | _REQUIRED_DISTRIBUTION
        | _REQUIRED_REPOSITORY
    )
    for relative in sorted(required_files):
        if not (root / relative).is_file():
            errors.append(f"missing Issue #45 file: {relative}")

    init_path = root / "portia/workflows/__init__.py"
    if not init_path.is_file():
        errors.append("missing public workflow package: portia/workflows/__init__.py")
    else:
        missing = sorted(_REQUIRED_EXPORTS - _exports(init_path))
        if missing:
            errors.append(f"missing Issue #45 public exports: {missing}")

    for service, relative in _SERVICE_FILES.items():
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        methods = _class_methods(path, service)
        if not methods:
            errors.append(f"{relative} is missing class {service}")
            continue
        amendment = {name for name in methods if "amend" in name.lower()}
        if amendment:
            errors.append(
                f"{service} must not expose v1 Amendment: {sorted(amendment)}"
            )
        for token in sorted(_REQUIRED_SOURCE_TOKENS[service]):
            if token not in text:
                errors.append(
                    f"{service} missing required workflow surface token: {token}"
                )

    errors.extend(_parity_findings(root))

    docs = root / "docs/implementation-and-fidelity-workflows.md"
    validation = (
        root
        / "docs"
        / "validation"
        / "issue-45-implementation-and-fidelity-workflows-validation.md"
    )
    readme = root / "README.md"
    planning_doc = root / "docs/support-process-support-intervention-workflows.md"

    required_docs = {
        docs: (
            "ImplementationWorkflowService",
            "FidelityWorkflowService",
            "62 schema-valid runtime scenarios",
            "Implementation != Fidelity",
            "Fidelity != Outcome",
            "P22-08",
            "P22-11",
            "Issue #46",
        ),
        validation: (
            "e5f98f81add586de1a91cc361f5ded7355a6cddd",
            "10 valid Implementation fixtures",
            "22 application-invalid Implementation fixtures",
            "9 valid Fidelity fixtures",
            "21 application-invalid Fidelity fixtures",
            "238 passed",
            "validate_issue45_workflows.py",
            "Slice 9 observed distribution qualification",
            "Portia Issue #45 package inventory validation passed",
            "Portia installed-wheel Issue #45 Implementation/Fidelity smoke test passed",
            "Final repository integration",
            "**Status:** final repository qualification passed",
            "2,646 tests passed",
            "Portia Issue #45 repository qualification passed",
            "final local Issue #45 closeout evidence",
        ),
        readme: (
            "### Issue #45 current implementation",
            "ImplementationWorkflowService",
            "FidelityWorkflowService",
            "62 schema-valid runtime scenarios",
        ),
        planning_doc: (
            "Issue #45 now supplies the production application/workflow layer",
            "Implementation and Fidelity runtime parity is qualified separately",
        ),
    }
    for path, phrases in required_docs.items():
        if not path.is_file():
            errors.append(f"missing Issue #45 documentation: {path.relative_to(root)}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                errors.append(
                    f"{path.relative_to(root)} missing required phrase: {phrase}"
                )

    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        stale = (
            "fails closed until Issue #44 supplies production Support Process "
            "authority"
        )
        if stale in text:
            errors.append(
                "README retains the stale pre-Issue #44 Communication deferral"
            )
        if "Issue #45 remains responsible for Implementation/Fidelity" in text:
            errors.append("README still describes implemented Issue #45 work as future")

    if planning_doc.is_file():
        text = planning_doc.read_text(encoding="utf-8")
        if "`implementation@1` and `fidelity@1` remain Issue #45-owned" in text:
            errors.append("Issue #44 guide still describes Issue #45 as pending")

    repository_validator = root / "scripts/validate_repository.py"
    if repository_validator.is_file():
        text = repository_validator.read_text(encoding="utf-8")
        required = (
            "Run the complete Portia repository qualification through Issue #45.",
            "Issue #45 qualification requires the authenticated Core 0.6.3 wheel",
            "scripts/validate_issue45_workflows.py",
            "scripts/check_issue45_package.py",
            "scripts/smoke_test_issue45_wheel.py",
            "Portia Issue #45 repository qualification passed",
        )
        for phrase in required:
            if phrase not in text:
                errors.append(
                    "scripts/validate_repository.py missing Issue #45 integration: "
                    f"{phrase}"
                )
        ordered = (
            "scripts/validate_issue44_workflows.py",
            "scripts/validate_issue45_workflows.py",
            '[sys.executable, "-m", "pytest"]',
        )
        if all(value in text for value in ordered):
            positions = [text.index(value) for value in ordered]
            if positions != sorted(positions):
                errors.append(
                    "scripts/validate_repository.py has Issue #45 validator out of order"
                )
        package_order = (
            "scripts/check_issue44_package.py",
            "scripts/check_issue45_package.py",
        )
        if all(value in text for value in package_order):
            positions = [text.index(value) for value in package_order]
            if positions != sorted(positions):
                errors.append(
                    "scripts/validate_repository.py has Issue #45 package check out of order"
                )
        smoke_order = (
            "scripts/smoke_test_issue44_wheel.py",
            "scripts/smoke_test_issue45_wheel.py",
        )
        if all(value in text for value in smoke_order):
            positions = [text.index(value) for value in smoke_order]
            if positions != sorted(positions):
                errors.append(
                    "scripts/validate_repository.py has Issue #45 wheel smoke out of order"
                )

    ci = root / ".github/workflows/ci.yml"
    if not ci.is_file():
        errors.append("missing CI workflow: .github/workflows/ci.yml")
    else:
        text = ci.read_text(encoding="utf-8")
        for phrase in (
            "- name: Run complete repository qualification",
            'python scripts/validate_repository.py --core-wheel "$env:PDS_CORE_WHEEL"',
        ):
            if phrase not in text:
                errors.append(f"CI missing durable repository qualification path: {phrase}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(__file__).resolve().parents[1]
    parser.add_argument("--root", type=Path, default=default_root)
    args = parser.parse_args()
    try:
        errors = findings(args.root.resolve())
    except (OSError, SyntaxError, ValueError) as exc:
        print(f"ERROR: Issue #45 validation could not run: {exc}")
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Portia Issue #45 workflow validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
