"""Combined Issue #45 guard for the frozen Issue #18 runtime oracle."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

ISSUE18 = Path("tests/schema_validation/fixtures/issue-18")

FAMILY_CONFIG = {
    "implementation": {
        "parity": Path("tests/test_issue45_implementation_fixture_parity.py"),
        "workflow": Path("tests/test_workflow_implementations.py"),
        "valid": 10,
        "application_invalid": 22,
        "structural_invalid": 17,
    },
    "fidelity": {
        "parity": Path("tests/test_issue45_fidelity_fixture_parity.py"),
        "workflow": Path("tests/test_workflow_fidelity.py"),
        "valid": 9,
        "application_invalid": 21,
        "structural_invalid": 21,
    },
}

EXPECTED_RUNTIME_COUNT = 62
EXPECTED_STRUCTURAL_INVALID_COUNT = 38


def _manifest(family: str) -> dict[str, Any]:
    value = json.loads(
        (ISSUE18 / family / "manifest.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _entry_name(value: object) -> str:
    if isinstance(value, str):
        return value
    assert isinstance(value, dict)
    name = value.get("file", value.get("name"))
    assert isinstance(name, str)
    return name


def _names(manifest: dict[str, Any], key: str) -> set[str]:
    values = manifest.get(key, ())
    assert isinstance(values, list)
    return {_entry_name(value) for value in values}


def _application_invalid(manifest: dict[str, Any]) -> dict[str, str]:
    values = manifest.get("application_invalid", ())
    assert isinstance(values, list)
    result: dict[str, str] = {}
    for value in values:
        assert isinstance(value, dict)
        name = _entry_name(value)
        expected_error = value.get("expected_error")
        assert isinstance(expected_error, str)
        assert expected_error.strip()
        result[name] = expected_error
    return result


def _coverage(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
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
        if value is not None:
            result = ast.literal_eval(value)
            assert isinstance(result, dict)
            assert all(isinstance(key, str) for key in result)
            assert all(isinstance(item, str) for item in result.values())
            return result
    raise AssertionError(f"{path} has no COVERAGE mapping")


def _workflow_test_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def test_issue45_runtime_oracle_is_exactly_62_schema_valid_scenarios() -> None:
    runtime_count = 0
    for family, config in FAMILY_CONFIG.items():
        manifest = _manifest(family)
        valid = _names(manifest, "valid")
        application_invalid = _application_invalid(manifest)
        coverage = _coverage(config["parity"])

        assert len(valid) == config["valid"]
        assert len(application_invalid) == config["application_invalid"]
        assert set(coverage) == valid | set(application_invalid)
        runtime_count += len(coverage)

    assert runtime_count == EXPECTED_RUNTIME_COUNT


def test_every_issue45_runtime_scenario_maps_to_existing_workflow_test() -> None:
    for config in FAMILY_CONFIG.values():
        coverage = _coverage(config["parity"])
        test_names = _workflow_test_names(config["workflow"])
        assert set(coverage.values()) <= test_names


def test_application_invalid_scenarios_keep_frozen_rejecting_invariants() -> None:
    for family, config in FAMILY_CONFIG.items():
        manifest = _manifest(family)
        errors = _application_invalid(manifest)
        coverage = _coverage(config["parity"])
        valid = _names(manifest, "valid")

        for scenario in set(coverage) - valid:
            invariant = errors[scenario]
            assert invariant.strip(), (
                f"{family}/{scenario} has no rejecting application invariant"
            )


def test_structural_invalid_cases_remain_outside_issue45_runtime_parity() -> None:
    structural_count = 0
    for family, config in FAMILY_CONFIG.items():
        manifest = _manifest(family)
        structural = _names(manifest, "invalid")
        coverage = set(_coverage(config["parity"]))

        assert len(structural) == config["structural_invalid"]
        assert structural.isdisjoint(coverage)
        structural_count += len(structural)

    assert structural_count == EXPECTED_STRUCTURAL_INVALID_COUNT
