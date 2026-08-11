from __future__ import annotations

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
    / "issue-17"
    / "identifiers"
)

EXPECTED_CATALOG = {
    "portia_response_id": {
        "schema_id": (
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/identifiers/portia-response-id.schema.json"
        ),
        "path": "schemas/v1/identifiers/portia-response-id.schema.json",
    },
    "portia_communication_id": {
        "schema_id": (
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/identifiers/portia-communication-id.schema.json"
        ),
        "path": "schemas/v1/identifiers/portia-communication-id.schema.json",
    },
}


class Issue17IdentifierPrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")
        cls.response_validator = validator_for(
            "portia_response_id",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.communication_validator = validator_for(
            "portia_communication_id",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )

    def test_manifest_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 17)
        self.assertEqual(
            set(self.manifest["contracts"]),
            {"portia_response_id", "portia_communication_id"},
        )

    def test_catalog_entries_are_exact(self) -> None:
        contracts = self.catalog["contracts"]
        for contract_name, expected in EXPECTED_CATALOG.items():
            with self.subTest(contract=contract_name):
                self.assertIn(contract_name, contracts)
                self.assertEqual(contracts[contract_name]["1"], expected)

    def test_response_identifier_fixtures(self) -> None:
        contract = self.manifest["contracts"]["portia_response_id"]
        self.assertEqual(contract["version"], "1")

        for value in contract["valid"]:
            with self.subTest(value=value, expected="valid"):
                self.assertFalse(list(self.response_validator.iter_errors(value)))

        for value in contract["invalid"]:
            with self.subTest(value=value, expected="invalid"):
                self.assertTrue(list(self.response_validator.iter_errors(value)))

    def test_communication_identifier_fixtures(self) -> None:
        contract = self.manifest["contracts"]["portia_communication_id"]
        self.assertEqual(contract["version"], "1")

        for value in contract["valid"]:
            with self.subTest(value=value, expected="valid"):
                self.assertFalse(
                    list(self.communication_validator.iter_errors(value))
                )

        for value in contract["invalid"]:
            with self.subTest(value=value, expected="invalid"):
                self.assertTrue(
                    list(self.communication_validator.iter_errors(value))
                )

    def test_identifier_length_boundaries(self) -> None:
        response_at_limit = "rsp_" + ("a" * 124)
        response_too_long = "rsp_" + ("a" * 125)
        communication_at_limit = "comm_" + ("a" * 123)
        communication_too_long = "comm_" + ("a" * 124)

        self.assertEqual(len(response_at_limit), 128)
        self.assertEqual(len(communication_at_limit), 128)

        self.assertFalse(
            list(self.response_validator.iter_errors(response_at_limit))
        )
        self.assertTrue(
            list(self.response_validator.iter_errors(response_too_long))
        )
        self.assertFalse(
            list(self.communication_validator.iter_errors(communication_at_limit))
        )
        self.assertTrue(
            list(self.communication_validator.iter_errors(communication_too_long))
        )

    def test_identifier_families_do_not_cross_validate(self) -> None:
        self.assertTrue(list(self.response_validator.iter_errors("comm_example")))
        self.assertTrue(
            list(self.communication_validator.iter_errors("rsp_example"))
        )


if __name__ == "__main__":
    unittest.main()
