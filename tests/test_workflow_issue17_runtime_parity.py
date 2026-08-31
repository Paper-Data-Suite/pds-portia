"""Acceptance guard for frozen Issue #17 Response/Communication runtime parity."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

TESTS_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = TESTS_ROOT.parent
ISSUE17_FIXTURES = TESTS_ROOT / "schema_validation" / "fixtures" / "issue-17"
APPLICATION_MATRIX = (
    REPOSITORY_ROOT
    / "docs"
    / "validation"
    / "issue-17-application-invalid-matrix.json"
)

RESPONSE_RUNTIME_TESTS = (
    "test_workflow_response_creation.py",
    "test_workflow_response_decision_context.py",
    "test_workflow_response_current_use.py",
    "test_workflow_response_lifecycle_mutations.py",
)

COMMUNICATION_RUNTIME_TESTS = (
    "test_workflow_communication_creation.py",
    "test_workflow_communication_contact_points.py",
    "test_workflow_communication_relations.py",
    "test_workflow_communication_attachments.py",
    "test_workflow_communication_current_use.py",
    "test_workflow_communication_lifecycle_mutations.py",
)


def _manifest(contract: str) -> dict[str, object]:
    path = ISSUE17_FIXTURES / contract / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _fixture_names(value: object, *, field: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssertionError(f"Issue #17 manifest field {field!r} is malformed")
    return set(value)


def _string_literals(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(node.value)
    return values


def _runtime_fixture_mentions(test_files: tuple[str, ...]) -> set[str]:
    mentions: set[str] = set()
    for filename in test_files:
        path = TESTS_ROOT / filename
        if not path.is_file():
            raise AssertionError(f"Issue #43 runtime parity test is missing {filename}")
        for value in _string_literals(path):
            if value.endswith(".json"):
                mentions.add(Path(value).name)
    return mentions


@pytest.mark.parametrize(
    ("contract", "test_files"),
    [
        ("response", RESPONSE_RUNTIME_TESTS),
        ("communication", COMMUNICATION_RUNTIME_TESTS),
    ],
)
def test_every_frozen_valid_fixture_has_runtime_workflow_coverage(
    contract: str,
    test_files: tuple[str, ...],
) -> None:
    manifest = _manifest(contract)
    expected = _fixture_names(manifest.get("valid"), field="valid")
    observed = _runtime_fixture_mentions(test_files)

    assert expected <= observed, (
        f"Issue #43 runtime parity lost frozen {contract} valid fixtures: "
        f"{sorted(expected - observed)}"
    )


@pytest.mark.parametrize(
    ("contract", "test_files"),
    [
        ("response", RESPONSE_RUNTIME_TESTS),
        ("communication", COMMUNICATION_RUNTIME_TESTS),
    ],
)
def test_every_frozen_application_invalid_fixture_has_runtime_workflow_coverage(
    contract: str,
    test_files: tuple[str, ...],
) -> None:
    manifest = _manifest(contract)
    expected = _fixture_names(
        manifest.get("application_invalid"),
        field="application_invalid",
    )
    observed = _runtime_fixture_mentions(test_files)

    assert expected <= observed, (
        f"Issue #43 runtime parity lost frozen {contract} application-invalid "
        f"fixtures: {sorted(expected - observed)}"
    )


def test_runtime_parity_matches_frozen_issue17_application_matrix() -> None:
    matrix = json.loads(APPLICATION_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(matrix, dict)
    entries = matrix.get("entries")
    assert isinstance(entries, list)

    matrix_by_group: dict[str, set[str]] = {"response": set(), "communication": set()}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        group = entry.get("group")
        fixture = entry.get("fixture")
        if group in matrix_by_group and isinstance(fixture, str):
            matrix_by_group[group].add(Path(fixture).name)

    frozen_total = 0
    for contract in ("response", "communication"):
        manifest = _manifest(contract)
        expected = _fixture_names(
            manifest.get("application_invalid"),
            field="application_invalid",
        )
        frozen_total += len(expected)
        assert expected <= matrix_by_group[contract], (
            f"Issue #17 application-invalid matrix lost frozen {contract} fixtures: "
            f"{sorted(expected - matrix_by_group[contract])}"
        )

    assert frozen_total == 52
    assert matrix.get("fixture_application_invalid_scenarios") == 52


def test_runtime_parity_scope_is_valid_plus_application_invalid() -> None:
    """Keep schema-invalid input at the model boundary rather than duplicating it."""
    expected_counts = {
        "response": (10, 19, 13),
        "communication": (14, 33, 22),
    }
    for contract, counts in expected_counts.items():
        manifest = _manifest(contract)
        valid = _fixture_names(manifest.get("valid"), field="valid")
        application_invalid = _fixture_names(
            manifest.get("application_invalid"),
            field="application_invalid",
        )
        structural_invalid = _fixture_names(manifest.get("invalid"), field="invalid")

        assert (len(valid), len(application_invalid), len(structural_invalid)) == counts
        assert valid.isdisjoint(application_invalid)
        assert valid.isdisjoint(structural_invalid)
        assert application_invalid.isdisjoint(structural_invalid)
