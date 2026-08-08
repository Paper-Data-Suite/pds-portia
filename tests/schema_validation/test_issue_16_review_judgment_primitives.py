from __future__ import annotations

from pathlib import Path
from typing import Any
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


FIXTURE_ROOT = (
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-16"
    / "review-judgment-primitives"
)

FAMILIES = (
    "review-id",
    "classification-id",
    "hypothesis-id",
    "determination-id",
    "judgment-evidence-ref",
)

EXPECTED_CONTRACT_PATHS = {
    "portia_review_id": (
        "schemas/v1/identifiers/portia-review-id.schema.json"
    ),
    "portia_classification_id": (
        "schemas/v1/identifiers/portia-classification-id.schema.json"
    ),
    "portia_hypothesis_id": (
        "schemas/v1/identifiers/portia-hypothesis-id.schema.json"
    ),
    "portia_determination_id": (
        "schemas/v1/identifiers/portia-determination-id.schema.json"
    ),
    "judgment_evidence_ref": (
        "schemas/v1/references/judgment-evidence-ref.schema.json"
    ),
}

IDENTIFIER_CASES = {
    "portia_review_id": {
        "valid": ("rvw_a", "rvw_0001", "rvw_Mixed_Case-9"),
        "invalid": ("rvw_", "review_a", "RVW_a", "rvw_a.b"),
    },
    "portia_classification_id": {
        "valid": ("cls_a", "cls_0001", "cls_Mixed_Case-9"),
        "invalid": ("cls_", "classification_a", "CLS_a", "cls_a.b"),
    },
    "portia_hypothesis_id": {
        "valid": ("hyp_a", "hyp_0001", "hyp_Mixed_Case-9"),
        "invalid": ("hyp_", "hypothesis_a", "HYP_a", "hyp_a.b"),
    },
    "portia_determination_id": {
        "valid": ("det_a", "det_0001", "det_Mixed_Case-9"),
        "invalid": ("det_", "determination_a", "DET_a", "det_a.b"),
    },
}


def application_errors(contract: str, value: Any) -> list[str]:
    if contract == "judgment_evidence_ref" and isinstance(value, dict):
        if value.get("kind") == "module_record":
            reference = value.get("module_work_record_ref")
            if isinstance(reference, dict):
                work_ref = reference.get("work_ref")
                record_ref = reference.get("record_ref")
                if isinstance(work_ref, dict) and isinstance(record_ref, dict):
                    if work_ref.get("module_id") != record_ref.get("module_id"):
                        return ["module work and record module_id values differ"]
    return []


class Issue16ReviewJudgmentPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_manifests_have_expected_metadata(self) -> None:
        for family in FAMILIES:
            with self.subTest(family=family):
                manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 16)
                self.assertEqual(manifest["version"], "1")
                self.assertIn(manifest["contract"], EXPECTED_CONTRACT_PATHS)

    def test_valid_fixtures_pass(self) -> None:
        for family in FAMILIES:
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            contract = manifest["contract"]
            validator = self.validator(contract)
            for filename in manifest["valid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "valid" / filename)
                    errors = list(validator.iter_errors(value))
                    self.assertFalse(
                        errors,
                        "\n".join(error.message for error in errors),
                    )
                    self.assertEqual(application_errors(contract, value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family in FAMILIES:
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            validator = self.validator(manifest["contract"])
            for filename in manifest["invalid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(FIXTURE_ROOT / family / "invalid" / filename)
                    self.assertTrue(list(validator.iter_errors(value)))

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        for family in FAMILIES:
            manifest = load_json(FIXTURE_ROOT / family / "manifest.json")
            contract = manifest["contract"]
            validator = self.validator(contract)
            for filename in manifest["application_invalid"]:
                with self.subTest(family=family, filename=filename):
                    value = load_json(
                        FIXTURE_ROOT / family / "application-invalid" / filename
                    )
                    structural_errors = list(validator.iter_errors(value))
                    self.assertFalse(
                        structural_errors,
                        "\n".join(error.message for error in structural_errors),
                    )
                    self.assertTrue(application_errors(contract, value))

    def test_contracts_are_cataloged_at_immutable_paths(self) -> None:
        for contract, expected_path in EXPECTED_CONTRACT_PATHS.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], expected_path)
                self.assertEqual(entry["schema_id"], (
                    "https://paper-data-suite.github.io/pds-portia/" + expected_path
                ))
                schema = load_json(REPO_ROOT / expected_path)
                self.assertEqual(schema["$id"], entry["schema_id"])
                self.assertNotIn("/latest/", entry["schema_id"])
                self.assertNotIn("/current/", entry["schema_id"])

    def test_identifier_prefix_and_case_contracts(self) -> None:
        for contract, cases in IDENTIFIER_CASES.items():
            validator = self.validator(contract)
            for value in cases["valid"]:
                with self.subTest(contract=contract, valid=value):
                    self.assertFalse(list(validator.iter_errors(value)))
            for value in cases["invalid"]:
                with self.subTest(contract=contract, invalid=value):
                    self.assertTrue(list(validator.iter_errors(value)))

    def test_judgment_evidence_union_is_closed_and_role_free(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas/v1/references/judgment-evidence-ref.schema.json"
        )
        self.assertEqual(len(schema["oneOf"]), 3)
        kinds = {
            branch["properties"]["kind"]["const"]
            for branch in schema["$defs"].values()
        }
        self.assertEqual(kinds, {"portia_work", "portia_record", "module_record"})
        for branch in schema["$defs"].values():
            self.assertFalse(branch["additionalProperties"])
        serialized = str(schema)
        self.assertNotIn("source_artifact_ref", serialized)
        self.assertNotIn("source-artifact-ref", serialized)
        for forbidden in (
            "weight",
            "credibility",
            "truth",
            "corroboration",
            "source_independence",
            "outcome",
            "payload",
            "content",
        ):
            for branch in schema["$defs"].values():
                self.assertNotIn(forbidden, branch["properties"])

    def test_judgment_evidence_uses_existing_reference_contracts(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas/v1/references/judgment-evidence-ref.schema.json"
        )
        portia_work = schema["$defs"]["portiaWork"]["properties"]["work_ref"]
        self.assertTrue(portia_work["$ref"].endswith(
            "/schemas/v1/references/exact-portia-work-ref.schema.json"
        ))
        portia_record = schema["$defs"]["portiaRecord"]["properties"][
            "work_record_ref"
        ]
        self.assertTrue(portia_record["$ref"].endswith(
            "/schemas/v1/references/exact-portia-work-record-ref.schema.json"
        ))
        module_record = schema["$defs"]["moduleRecord"]["properties"][
            "module_work_record_ref"
        ]
        refs = [item.get("$ref") for item in module_record["allOf"]]
        self.assertIn(
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/references/module-work-record-ref.schema.json",
            refs,
        )


if __name__ == "__main__":
    unittest.main()
