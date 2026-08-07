from __future__ import annotations

from datetime import datetime
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
    / "issue-15"
    / "account-observation-primitives"
)

FAMILIES = (
    "account-id",
    "observation-id",
    "represented-human-attribution",
    "evidence-time",
    "source-artifact-ref",
)

EXPECTED_CONTRACT_PATHS = {
    "portia_account_id": (
        "schemas/v1/identifiers/portia-account-id.schema.json"
    ),
    "portia_observation_id": (
        "schemas/v1/identifiers/portia-observation-id.schema.json"
    ),
    "represented_human_attribution": (
        "schemas/v1/attribution/represented-human-attribution.schema.json"
    ),
    "evidence_time": "schemas/v1/common/evidence-time.schema.json",
    "source_artifact_ref": (
        "schemas/v1/provenance/source-artifact-ref.schema.json"
    ),
}

IDENTIFIER_CASES = {
    "portia_account_id": {
        "valid": ("acct_a", "acct_0001", "acct_Mixed_Case-9"),
        "invalid": ("acct_", "account_a", "ACCT_a", "acct_a.b"),
    },
    "portia_observation_id": {
        "valid": ("obs_a", "obs_0001", "obs_Mixed_Case-9"),
        "invalid": ("obs_", "observation_a", "OBS_a", "obs_a.b"),
    },
}


def _parse_offset(value: str) -> datetime:
    return datetime.fromisoformat(value)


def application_errors(contract: str, value: Any) -> list[str]:
    if contract == "evidence_time" and isinstance(value, dict):
        if value.get("precision") == "range":
            started_at = value.get("started_at")
            ended_at = value.get("ended_at")
            if isinstance(started_at, str) and isinstance(ended_at, str):
                if _parse_offset(started_at) > _parse_offset(ended_at):
                    return ["evidence time range is reversed"]
    return []


class Issue15AccountObservationPrimitiveTests(unittest.TestCase):
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
                self.assertEqual(manifest["issue"], 15)
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

    def test_represented_human_union_is_closed_and_privacy_bounded(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/attribution/represented-human-attribution.schema.json"
        )
        self.assertEqual(len(schema["oneOf"]), 5)
        kinds = {
            branch["properties"]["kind"]["const"]
            for branch in schema["$defs"].values()
        }
        self.assertEqual(kinds, {
            "roster_student",
            "actor",
            "local_operator",
            "descriptive_person",
            "unidentified_person",
        })
        for branch in schema["$defs"].values():
            self.assertFalse(branch["additionalProperties"])
            properties = branch["properties"]
            for forbidden in (
                "email",
                "phone",
                "contact_value",
                "credibility",
                "reliability",
                "authority",
            ):
                self.assertNotIn(forbidden, properties)

    def test_evidence_time_has_exactly_five_closed_precision_branches(self) -> None:
        schema = load_json(REPO_ROOT / "schemas/v1/common/evidence-time.schema.json")
        self.assertEqual(len(schema["oneOf"]), 5)
        precisions = {
            branch["properties"]["precision"]["const"]
            for branch in schema["$defs"].values()
        }
        self.assertEqual(precisions, {
            "exact", "approximate", "date_only", "range", "unknown"
        })
        for branch in schema["$defs"].values():
            self.assertFalse(branch["additionalProperties"])

    def test_source_artifact_union_is_closed_and_payload_free(self) -> None:
        schema = load_json(
            REPO_ROOT / "schemas/v1/provenance/source-artifact-ref.schema.json"
        )
        self.assertEqual(len(schema["oneOf"]), 5)
        kinds = {
            branch["properties"]["kind"]["const"]
            for branch in schema["$defs"].values()
        }
        self.assertEqual(kinds, {
            "paper_capture",
            "workspace_file",
            "portia_work_record",
            "module_work_record",
            "external_record",
        })
        for branch in schema["$defs"].values():
            self.assertFalse(branch["additionalProperties"])
            for forbidden in ("payload", "bytes", "base64", "content"):
                self.assertNotIn(forbidden, branch["properties"])


if __name__ == "__main__":
    unittest.main()
