from __future__ import annotations

import unittest
from pathlib import Path

try:
    from .schema_support import (
        FIXTURE_ROOT,
        PORTIA_FORMAT_CHECKER,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        PORTIA_FORMAT_CHECKER,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )


CONTRACT_CASES = {
    "non_empty_text": (
        "common",
        "non-empty-text.schema.json",
        "common/non_empty_text",
    ),
    "explicit_offset_timestamp": (
        "common",
        "explicit-offset-timestamp.schema.json",
        "common/explicit_offset_timestamp",
    ),
    "creation_source": (
        "provenance",
        "creation-source.schema.json",
        "provenance/creation_source",
    ),
    "attribution_agent": (
        "attribution",
        "attribution-agent.schema.json",
        "attribution/attribution_agent",
    ),
}

SHARED_FIXTURE_ROOT = FIXTURE_ROOT / "shared"


class SharedEnvelopePrimitiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def contract_validator(self, contract_name: str):
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
        fixture_subpath = CONTRACT_CASES[contract_name][2]
        return sorted(
            (
                SHARED_FIXTURE_ROOT
                / fixture_subpath
                / expected_result
            ).glob("*.json")
        )

    def test_contracts_are_cataloged(self) -> None:
        for contract_name, (
            schema_group,
            filename,
            _fixture_subpath,
        ) in CONTRACT_CASES.items():
            with self.subTest(contract=contract_name):
                expected_id = (
                    "https://paper-data-suite.github.io/"
                    "pds-portia/schemas/v1/"
                    f"{schema_group}/{filename}"
                )
                self.assertEqual(
                    schema_id_for(
                        contract_name,
                        "1",
                        self.catalog,
                    ),
                    expected_id,
                )

    def test_valid_fixtures(self) -> None:
        for contract_name in CONTRACT_CASES:
            validator = self.contract_validator(contract_name)
            paths = self.fixture_paths(contract_name, "valid")
            self.assertTrue(paths, f"No valid fixtures for {contract_name}")
            for path in paths:
                with self.subTest(contract=contract_name, fixture=path.name):
                    errors = list(validator.iter_errors(load_json(path)))
                    self.assertFalse(
                        errors,
                        "\n".join(error.message for error in errors),
                    )

    def test_invalid_fixtures(self) -> None:
        for contract_name in CONTRACT_CASES:
            validator = self.contract_validator(contract_name)
            paths = self.fixture_paths(contract_name, "invalid")
            self.assertTrue(paths, f"No invalid fixtures for {contract_name}")
            for path in paths:
                with self.subTest(contract=contract_name, fixture=path.name):
                    errors = list(validator.iter_errors(load_json(path)))
                    self.assertTrue(
                        errors,
                        f"{path.name} unexpectedly passed validation",
                    )

    def test_format_checker_is_portia_owned_and_deterministic(
        self,
    ) -> None:
        validator = self.contract_validator(
            "explicit_offset_timestamp"
        )
        self.assertIs(
            validator.format_checker,
            PORTIA_FORMAT_CHECKER,
        )
        self.assertTrue(
            PORTIA_FORMAT_CHECKER.conforms(
                "2026-07-31T22:30:00Z",
                "date-time",
            )
        )
        self.assertFalse(
            PORTIA_FORMAT_CHECKER.conforms(
                "2026-02-30T22:30:00Z",
                "date-time",
            )
        )
        self.assertFalse(
            PORTIA_FORMAT_CHECKER.conforms(
                "2026-02-30",
                "date",
            )
        )

    def test_timestamp_requires_explicit_offset(self) -> None:
        schema_id = schema_id_for(
            "explicit_offset_timestamp",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(schema["format"], "date-time")
        self.assertEqual(
            schema["pattern"],
            r"(?:Z|[+-][0-9]{2}:[0-9]{2})$",
        )

    def test_creation_source_has_three_closed_branches(self) -> None:
        schema_id = schema_id_for(
            "creation_source",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(len(schema["oneOf"]), 3)
        defs = schema["$defs"]
        expected = {
            "digitalEntrySource": "digital_entry",
            "paperCaptureSource": "paper_capture",
            "importSource": "import",
        }
        for definition_name, type_value in expected.items():
            with self.subTest(definition=definition_name):
                definition = defs[definition_name]
                self.assertFalse(definition["additionalProperties"])
                self.assertEqual(
                    definition["properties"]["type"]["const"],
                    type_value,
                )

    def test_attribution_has_two_closed_branches(self) -> None:
        schema_id = schema_id_for(
            "attribution_agent",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(len(schema["oneOf"]), 2)
        defs = schema["$defs"]
        expected = {
            "localOperator": "local_operator",
            "systemProcess": "system_process",
        }
        for definition_name, type_value in expected.items():
            with self.subTest(definition=definition_name):
                definition = defs[definition_name]
                self.assertFalse(definition["additionalProperties"])
                self.assertEqual(
                    definition["properties"]["type"]["const"],
                    type_value,
                )

    def test_shared_schemas_use_absolute_public_refs(self) -> None:
        creation_id = schema_id_for(
            "creation_source", "1", self.catalog
        )
        creation = self.store.schema_for_id(creation_id)
        paper = creation["$defs"]["paperCaptureSource"]
        imported = creation["$defs"]["importSource"]
        self.assertTrue(
            paper["properties"]["route_id"]["$ref"].startswith("https://")
        )
        self.assertTrue(
            paper["properties"]["page_record_id"]["$ref"].startswith("https://")
        )
        self.assertTrue(
            imported["properties"]["source_label"]["$ref"].startswith("https://")
        )


if __name__ == "__main__":
    unittest.main()
