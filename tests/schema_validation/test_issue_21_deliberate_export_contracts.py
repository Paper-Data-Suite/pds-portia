from __future__ import annotations

from datetime import datetime
import hashlib
import json
import unittest

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )

FIXTURE_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-21"

def canonical_inventory_digest(value: dict[str, object]) -> str:
    payload = {
        "inventory_algorithm": value["inventory_algorithm"],
        "entries": value["entries"],
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()

def source_identity(entry: dict[str, object]) -> str:
    if "artifact_identity_digest" in entry:
        return json.dumps(
            {
                "artifact_kind": entry["artifact_kind"],
                "artifact_identity_digest": entry["artifact_identity_digest"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    for key in ("work_ref","work_record_ref","module_work_record_ref"):
        if key in entry:
            return json.dumps(
                entry[key],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
    raise AssertionError("source entry has no reference")

def inventory_sort_key(entry: dict[str, object]) -> tuple[str, str, str]:
    return (str(entry["source_role"]), str(entry["source_kind"]), source_identity(entry))

def inventory_application_errors(value: dict[str, object]) -> list[str]:
    errors: list[str] = []
    entries = value["entries"]
    if value["inventory_digest"] != canonical_inventory_digest(value):
        errors.append("inventory digest mismatch")
    if entries != sorted(entries, key=inventory_sort_key):
        errors.append("entries are not deterministically sorted")
    identities = [(entry["source_kind"], source_identity(entry)) for entry in entries]
    if len(identities) != len(set(identities)):
        errors.append("semantic source identity appears more than once")
    return errors

FOCAL_PURPOSES = {"participant_specific","student_facing","family_facing"}

def export_application_errors(value: dict[str, object]) -> list[str]:
    errors = inventory_application_errors(value["source_inventory"])

    if value["projection_purpose"] in FOCAL_PURPOSES and "focal_subject_ref" not in value:
        errors.append("focal purpose requires focal subject")

    review = value["manual_review"]
    if (
        review["status"] == "resolved"
        and review["reviewed_projection_digest"] != value["projection_decision_digest"]
    ):
        errors.append("manual review digest mismatch")

    requested = datetime.fromisoformat(value["requested_at"].replace("Z", "+00:00"))
    generated = datetime.fromisoformat(value["generated_at"].replace("Z", "+00:00"))
    if generated < requested:
        errors.append("generation predates request")

    expected_prefix = f"portia/exports/{value['export_id']}/"
    if not value["output"]["workspace_relative_path"].startswith(expected_prefix):
        errors.append("output path is not export-id scoped")

    if value["requested_by"]["type"] != "local_operator":
        errors.append("request not attributable to local operator")

    return errors

class Issue21DeliberateExportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(contract, "1", catalog=self.catalog, store=self.store)

    def test_new_contracts_are_cataloged(self) -> None:
        expected = {
            "portia_deliberate_export_id":
                "schemas/v1/identifiers/portia-deliberate-export-id.schema.json",
            "export_source_inventory":
                "schemas/v1/exports/export-source-inventory.schema.json",
            "deliberate_export":
                "schemas/v1/exports/deliberate-export.schema.json",
        }
        for contract, path in expected.items():
            with self.subTest(contract=contract):
                self.assertEqual(self.catalog["contracts"][contract]["1"]["path"], path)

    def test_identifier_prefix_is_exact_and_nondossier(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas" / "v1" / "identifiers"
            / "portia-deliberate-export-id.schema.json"
        )
        self.assertEqual(schema["pattern"], "^pexp_[A-Za-z0-9][A-Za-z0-9_-]*$")
        self.assertIn("does not encode student/person identity", schema["description"])

    def test_manifests_have_expected_contracts(self) -> None:
        expected = {
            "export-source-inventory": "export_source_inventory",
            "deliberate-export": "deliberate_export",
        }
        for family, contract in expected.items():
            with self.subTest(family=family):
                manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
                self.assertEqual(manifest["issue"], 21)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass_structurally(self) -> None:
        for family in ("export-source-inventory","deliberate-export"):
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            validator = self.validator(manifest["contract"])
            for filename in manifest["valid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                    errors = list(validator.iter_errors(value))
                    self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family in ("export-source-inventory","deliberate-export"):
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            validator = self.validator(manifest["contract"])
            for filename in manifest["invalid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "invalid" / filename)
                    self.assertTrue(list(validator.iter_errors(value)))

    def test_application_invalid_inventory_fixtures_are_structurally_valid(self) -> None:
        family = "export-source-inventory"
        manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
        validator = self.validator(manifest["contract"])
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / family / "application-invalid" / filename)
                errors = list(validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                self.assertTrue(inventory_application_errors(value))

    def test_application_invalid_export_fixtures_are_structurally_valid(self) -> None:
        family = "deliberate-export"
        manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
        validator = self.validator(manifest["contract"])
        for filename in manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / family / "application-invalid" / filename)
                errors = list(validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                self.assertTrue(export_application_errors(value))

    def test_valid_inventory_values_pass_application_checks(self) -> None:
        family = "export-source-inventory"
        manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
        for filename in manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                self.assertEqual(inventory_application_errors(value), [])

    def test_valid_exports_pass_application_checks(self) -> None:
        family = "deliberate-export"
        manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
        for filename in manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                self.assertEqual(export_application_errors(value), [])

    def test_source_snapshot_v1_is_not_mutated_into_export_contract(self) -> None:
        source_snapshot = load_json(
            REPO_ROOT / "schemas" / "v1" / "projections" / "source-snapshot.schema.json"
        )
        self.assertEqual(
            source_snapshot["properties"]["snapshot_algorithm"]["const"],
            "portia_source_snapshot_v1",
        )
        kinds = source_snapshot["properties"]["projection_kind"]["enum"]
        self.assertNotIn("student_facing", kinds)
        self.assertNotIn("family_facing", kinds)
        self.assertNotIn("administrative_export", kinds)

    def test_export_is_one_artifact_and_not_disclosure(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas" / "v1" / "exports" / "deliberate-export.schema.json"
        )
        self.assertIn("one deliberately requested", schema["description"])
        self.assertIn("It is not a disclosure", schema["description"])
        self.assertIn("output", schema["required"])
        self.assertNotIn("recipient", schema["properties"])
        self.assertNotIn("delivered_at", schema["properties"])
        self.assertNotIn("received_at", schema["properties"])

    def test_export_reuses_operation_journal_and_keeps_bytes_external(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas" / "v1" / "exports" / "deliberate-export.schema.json"
        )
        self.assertEqual(
            schema["properties"]["operation_journal_ref"]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/references/operation-journal-ref.schema.json",
        )
        invariants = set(schema["x-portia-application-invariants"])
        self.assertIn(
            "portia.deliberate_export.output_bytes_outside_canonical_json",
            invariants,
        )
        self.assertIn(
            "portia.deliberate_export.generation_not_disclosure",
            invariants,
        )

if __name__ == "__main__":
    unittest.main()
