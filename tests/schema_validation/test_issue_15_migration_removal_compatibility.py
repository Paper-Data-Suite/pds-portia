from __future__ import annotations

from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "migration-removal-compatibility"


def _record_identity(record: dict[str, Any]) -> tuple[str, str, str, str, str]:
    rid = record["account_id"] if record["record_type"] == "account" else record["observation_id"]
    return (record["class_id"], record["work_id"], record["record_type"], rid, "1")


def _endpoint_identity(endpoint: dict[str, Any]) -> tuple[str, str, str, str, str]:
    ref = endpoint["work_record_ref"]
    return (ref["work_ref"]["class_id"], ref["work_ref"]["work_id"], ref["record_ref"]["record_kind"], ref["record_ref"]["record_id"], ref["record_ref"]["contract_version"])


def _migration_errors(scenario: dict[str, Any]) -> list[str]:
    record = scenario["target_record"]
    mig = scenario["migration"]
    errors: list[str] = []
    source = _endpoint_identity(mig["source"])
    dest = _endpoint_identity(mig["destination"])
    expected = _record_identity(record)
    if source != expected:
        if source[:4] == expected[:4] and mig["source"]["observed_updated_at"] != record["updated_at"]:
            errors.append("portia.migration.observed_revision_mismatch")
        else:
            errors.append("portia.migration.exact_resolution_required")
    elif mig["source"]["observed_updated_at"] != record["updated_at"]:
        errors.append("portia.migration.observed_revision_mismatch")
    if dest[0] != expected[0] or dest[1] != expected[1]:
        errors.append("portia.migration.work_root_changed")
    if dest[2] != expected[2] or dest[3] != expected[3]:
        errors.append("portia.migration.logical_identity_mismatch")
    if dest[4] == expected[4]:
        errors.append("portia.migration.same_contract_version")
    if not scenario.get("semantic_equivalent", False):
        errors.append("portia.migration.semantic_mismatch")
    if not scenario.get("lifecycle_preserved", False):
        errors.append("portia.migration.lifecycle_not_preserved")
    return errors


def _all_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _all_strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _all_strings(v)


def _sensitive_strings(record: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    if record["record_type"] == "account":
        for segment in record["content"]:
            out.add(segment["text"])
    else:
        narrative = record["content"].get("narrative")
        if narrative:
            out.add(narrative)
    return out


def _removal_errors(scenario: dict[str, Any]) -> list[str]:
    record = scenario["target_record"]
    removal = scenario["removal"]
    errors: list[str] = []
    actual = _endpoint_identity(removal["target"])
    expected = _record_identity(record)
    if actual != expected:
        successor = scenario.get("successor_record")
        if successor is not None and actual == _record_identity(successor):
            errors.append("portia.removal.silent_successor_follow")
        else:
            errors.append("portia.removal.target_not_exactly_resolved")
    snapshot = removal.get("lifecycle_snapshot")
    if snapshot is not None and snapshot["status"] != record["status"]:
        errors.append("portia.removal.lifecycle_snapshot_mismatch")
    cert_strings = set(_all_strings(removal))
    if _sensitive_strings(record) & cert_strings:
        errors.append("portia.removal.substantive_content_retained")
    if not scenario.get("dependency_review_complete", False):
        errors.append("portia.removal.dependency_review_missing")
    return errors


def compatibility_errors(scenario: dict[str, Any]) -> list[str]:
    if scenario["kind"] == "migration":
        return _migration_errors(scenario)
    if scenario["kind"] == "removal":
        return _removal_errors(scenario)
    return ["unsupported compatibility kind"]


class Issue15MigrationRemovalCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validators = {
            "account": validator_for("account", "1", catalog=cls.catalog, store=cls.store),
            "observation": validator_for("observation", "1", catalog=cls.catalog, store=cls.store),
            "record_migration": validator_for("record_migration", "1", catalog=cls.catalog, store=cls.store),
            "exceptional_removal": validator_for("exceptional_removal", "1", catalog=cls.catalog, store=cls.store),
        }
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def _assert_structurally_valid(self, name: str, value: dict[str, Any]) -> None:
        errors = list(self.validators[name].iter_errors(value))
        self.assertFalse(errors, "\n".join(e.message for e in errors))

    def _validate_structure(self, scenario: dict[str, Any]) -> None:
        record = scenario["target_record"]
        self._assert_structurally_valid(record["record_type"], record)
        if "successor_record" in scenario:
            successor = scenario["successor_record"]
            self._assert_structurally_valid(successor["record_type"], successor)
        contract = "record_migration" if scenario["kind"] == "migration" else "exceptional_removal"
        key = "migration" if scenario["kind"] == "migration" else "removal"
        self._assert_structurally_valid(contract, scenario[key])

    def test_manifest_is_compatibility_only(self) -> None:
        self.assertEqual(self.manifest["public_contracts_added"], [])
        self.assertEqual(len(self.manifest["valid"]), 5)
        self.assertEqual(len(self.manifest["application_invalid"]), 12)

    def test_valid_scenarios(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                scenario = load_json(FIXTURE_ROOT / "valid" / filename)
                self._validate_structure(scenario)
                self.assertEqual(compatibility_errors(scenario), [])

    def test_application_invalid_scenarios_are_structurally_valid(self) -> None:
        for entry in self.manifest["application_invalid"]:
            with self.subTest(filename=entry["file"]):
                scenario = load_json(FIXTURE_ROOT / "application-invalid" / entry["file"])
                self._validate_structure(scenario)
                errors = compatibility_errors(scenario)
                self.assertIn(entry["rule_id"], errors)

    def test_shared_contracts_remain_version_one(self) -> None:
        self.assertEqual(set(self.catalog["contracts"]["record_migration"]), {"1"})
        self.assertEqual(set(self.catalog["contracts"]["exceptional_removal"]), {"1"})

    def test_no_parallel_account_observation_contracts_exist(self) -> None:
        forbidden = {
            "account_record_migration", "observation_record_migration",
            "account_exceptional_removal", "observation_exceptional_removal",
        }
        self.assertTrue(forbidden.isdisjoint(self.catalog["contracts"]))

    def test_removal_certificate_does_not_need_source_text(self) -> None:
        for filename in ("removal-account-exact.json", "removal-observation-exact.json"):
            scenario = load_json(FIXTURE_ROOT / "valid" / filename)
            self.assertFalse(_sensitive_strings(scenario["target_record"]) & set(_all_strings(scenario["removal"])))

    def test_exact_predecessor_removal_does_not_follow_successor(self) -> None:
        scenario = load_json(FIXTURE_ROOT / "valid" / "removal-superseded-account-exact-predecessor.json")
        self.assertEqual(compatibility_errors(scenario), [])
        self.assertEqual(_endpoint_identity(scenario["removal"]["target"]), _record_identity(scenario["target_record"]))
        self.assertNotEqual(_endpoint_identity(scenario["removal"]["target"]), _record_identity(scenario["successor_record"]))


if __name__ == "__main__":
    unittest.main()
