from __future__ import annotations

import unittest
from pathlib import Path

try:
    from .schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )


IDENTIFIER_CASES = {
    "portia_event_id": "portia-event-id.schema.json",
    "portia_support_process_id": (
        "portia-support-process-id.schema.json"
    ),
    "portia_actor_id": "portia-actor-id.schema.json",
    "portia_event_participant_id": (
        "portia-event-participant-id.schema.json"
    ),
    "portia_event_participant_role_id": (
        "portia-event-participant-role-id.schema.json"
    ),
    "portia_work_relationship_id": (
        "portia-work-relationship-id.schema.json"
    ),
    "structurally_safe_external_id": (
        "structurally-safe-external-id.schema.json"
    ),
}

IDENTIFIER_FIXTURE_ROOT = (
    FIXTURE_ROOT / "shared" / "identifiers"
)


class IdentifierSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def identifier_validator(self, contract_name: str):
        return validator_for(
            contract_name,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def fixture_paths(
        self,
        contract_name: str,
        expected_result: str,
    ) -> list[Path]:
        return sorted(
            (
                IDENTIFIER_FIXTURE_ROOT
                / contract_name
                / expected_result
            ).glob("*.json")
        )

    def test_identifier_contracts_are_cataloged(self) -> None:
        for contract_name, filename in IDENTIFIER_CASES.items():
            with self.subTest(contract=contract_name):
                expected_id = (
                    "https://paper-data-suite.github.io/"
                    "pds-portia/schemas/v1/identifiers/"
                    f"{filename}"
                )
                self.assertEqual(
                    schema_id_for(
                        contract_name,
                        "1",
                        self.catalog,
                    ),
                    expected_id,
                )

    def test_valid_identifier_fixtures(self) -> None:
        for contract_name in IDENTIFIER_CASES:
            validator = self.identifier_validator(contract_name)
            paths = self.fixture_paths(contract_name, "valid")
            self.assertTrue(
                paths,
                f"No valid fixtures found for {contract_name}",
            )
            for path in paths:
                with self.subTest(
                    contract=contract_name,
                    fixture=path.name,
                ):
                    errors = list(
                        validator.iter_errors(load_json(path))
                    )
                    self.assertFalse(
                        errors,
                        "\n".join(
                            error.message for error in errors
                        ),
                    )

    def test_invalid_identifier_fixtures(self) -> None:
        for contract_name in IDENTIFIER_CASES:
            validator = self.identifier_validator(contract_name)
            paths = self.fixture_paths(contract_name, "invalid")
            self.assertTrue(
                paths,
                f"No invalid fixtures found for {contract_name}",
            )
            for path in paths:
                with self.subTest(
                    contract=contract_name,
                    fixture=path.name,
                ):
                    errors = list(
                        validator.iter_errors(load_json(path))
                    )
                    self.assertTrue(
                        errors,
                        f"{path.name} unexpectedly passed validation",
                    )

    def test_all_identifier_contracts_are_bounded_strings(self) -> None:
        for contract_name in IDENTIFIER_CASES:
            schema_id = schema_id_for(
                contract_name,
                "1",
                self.catalog,
            )
            schema = self.store.schema_for_id(schema_id)
            with self.subTest(contract=contract_name):
                self.assertEqual(schema["type"], "string")
                self.assertEqual(schema["minLength"], 1)
                self.assertEqual(schema["maxLength"], 128)
                self.assertIsInstance(schema["pattern"], str)

    def test_external_fallback_is_explicitly_nonauthoritative(
        self,
    ) -> None:
        schema_id = schema_id_for(
            "structurally_safe_external_id",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        description = schema["description"].lower()
        comment = schema["$comment"].lower()
        self.assertIn("structural", description)
        self.assertIn("path-safety", description)
        self.assertIn("does not establish", description)
        self.assertIn("nonauthoritative", comment)


if __name__ == "__main__":
    unittest.main()
