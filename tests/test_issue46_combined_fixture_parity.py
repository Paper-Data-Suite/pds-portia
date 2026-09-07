"""Combined frozen Issue #19 runtime-parity ledger for Portia Issue #46."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from portia.models import parse_portia_record

FIXTURE_BASE = Path("tests/schema_validation/fixtures/issue-19")

FAMILIES: dict[str, dict[str, object]] = {
    "follow_up": {
        "fixture_dir": "follow-up",
        "parity": Path("tests/test_issue46_follow_up_fixture_parity.py"),
        "valid": 10,
        "application_invalid": 14,
        "invalid": 13,
    },
    "outcome": {
        "fixture_dir": "outcome",
        "parity": Path("tests/test_issue46_outcome_fixture_parity.py"),
        "valid": 13,
        "application_invalid": 17,
        "invalid": 18,
    },
    "reentry": {
        "fixture_dir": "reentry",
        "parity": Path("tests/test_issue46_reentry_fixture_parity.py"),
        "valid": 11,
        "application_invalid": 14,
        "invalid": 16,
    },
    "repair": {
        "fixture_dir": "repair",
        "parity": Path("tests/test_issue46_repair_fixture_parity.py"),
        "valid": 12,
        "application_invalid": 19,
        "invalid": 25,
    },
}


def _manifest(family: str) -> dict[str, object]:
    fixture_dir = str(FAMILIES[family]["fixture_dir"])
    value = json.loads(
        (FIXTURE_BASE / fixture_dir / "manifest.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _names(value: object) -> tuple[str, ...]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return tuple(value)


def _literal_dict(path: Path, name: str) -> dict[str, str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name) or node.target.id != name:
            continue
        value = ast.literal_eval(node.value)
        assert isinstance(value, dict)
        assert all(isinstance(key, str) for key in value)
        assert all(isinstance(item, str) for item in value.values())
        return value
    raise AssertionError(f"{path} does not define literal {name}")


def _runtime_names(family: str) -> set[str]:
    manifest = _manifest(family)
    return set(_names(manifest["valid"])) | set(
        _names(manifest["application_invalid"])
    )


def test_issue46_family_manifest_counts_are_frozen() -> None:
    for family, expected in FAMILIES.items():
        manifest = _manifest(family)
        assert manifest["manifest_version"] == "1"
        assert manifest["issue"] == 19
        assert manifest["contract"] == family
        assert manifest["version"] == "1"
        assert len(_names(manifest["valid"])) == expected["valid"]
        assert len(_names(manifest["application_invalid"])) == expected[
            "application_invalid"
        ]
        assert len(_names(manifest["invalid"])) == expected["invalid"]


def test_issue46_combined_runtime_parity_is_exactly_110_cases() -> None:
    valid = sum(len(_names(_manifest(family)["valid"])) for family in FAMILIES)
    application_invalid = sum(
        len(_names(_manifest(family)["application_invalid"]))
        for family in FAMILIES
    )
    assert valid == 46
    assert application_invalid == 64
    assert valid + application_invalid == 110


def test_issue46_family_parity_guards_exactly_cover_runtime_manifests() -> None:
    qualified: set[tuple[str, str]] = set()
    for family, policy in FAMILIES.items():
        parity = policy["parity"]
        assert isinstance(parity, Path)
        coverage = _literal_dict(parity, "COVERAGE")
        expected_errors = _literal_dict(parity, "EXPECTED_ERRORS")
        manifest = _manifest(family)
        valid = set(_names(manifest["valid"]))
        application_invalid = set(_names(manifest["application_invalid"]))
        assert set(coverage) == valid | application_invalid
        assert all(target.strip() for target in coverage.values())
        assert set(expected_errors) == application_invalid
        qualified.update((family, filename) for filename in coverage)
    assert len(qualified) == 110


def test_issue46_structural_invalid_total_is_exactly_72_and_separate() -> None:
    structural: set[tuple[str, str]] = set()
    runtime: set[tuple[str, str]] = set()
    for family in FAMILIES:
        manifest = _manifest(family)
        structural.update((family, name) for name in _names(manifest["invalid"]))
        runtime.update((family, name) for name in _runtime_names(family))
    assert len(structural) == 72
    assert len(runtime) == 110
    assert structural.isdisjoint(runtime)


def test_issue46_expected_error_evidence_is_exactly_64_cases() -> None:
    qualified: set[tuple[str, str]] = set()
    for family, policy in FAMILIES.items():
        parity = policy["parity"]
        assert isinstance(parity, Path)
        expected_errors = _literal_dict(parity, "EXPECTED_ERRORS")
        assert all(message.strip() for message in expected_errors.values())
        qualified.update((family, filename) for filename in expected_errors)
    assert len(qualified) == 64


def test_issue46_all_110_runtime_payloads_reach_runtime_models() -> None:
    parsed = 0
    for family, policy in FAMILIES.items():
        fixture_dir = str(policy["fixture_dir"])
        manifest = _manifest(family)
        for bucket in ("valid", "application_invalid"):
            directory = (
                "application-invalid"
                if bucket == "application_invalid"
                else bucket
            )
            for filename in _names(manifest[bucket]):
                value = json.loads(
                    (FIXTURE_BASE / fixture_dir / directory / filename).read_text(
                        encoding="utf-8"
                    )
                )
                record = parse_portia_record(family, "1", value)
                assert record.contract == family
                assert record.contract_version == "1"
                parsed += 1
    assert parsed == 110
