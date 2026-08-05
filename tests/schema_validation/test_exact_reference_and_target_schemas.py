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


EXACT_CONTRACTS = {
    "exact_portia_work_ref": (
        "schemas/v1/references/"
        "exact-portia-work-ref.schema.json"
    ),
    "exact_local_record_ref": (
        "schemas/v1/references/"
        "exact-local-record-ref.schema.json"
    ),
    "exact_portia_work_record_ref": (
        "schemas/v1/references/"
        "exact-portia-work-record-ref.schema.json"
    ),
    "exceptional_removal_ref": (
        "schemas/v1/references/"
        "exceptional-removal-ref.schema.json"
    ),
    "portia_local_work_target": (
        "schemas/v1/targets/"
        "portia-local-work-target.schema.json"
    ),
    "exact_portia_work_or_record_target": (
        "schemas/v1/targets/"
        "exact-portia-work-or-record-target.schema.json"
    ),
}

FIXTURE_DIRECTORY = (
    FIXTURE_ROOT
    / "issue-12"
    / "exact-references-and-targets"
)
PUBLIC_SCHEMA_PREFIX = (
    "https://paper-data-suite.github.io/pds-portia/"
)


class ExactReferenceAndTargetSchemaTests(
    unittest.TestCase
):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def contract_validator(self, contract_name: str):
        return validator_for(
            contract_name,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_new_contracts_are_cataloged_with_path_ids(
        self,
    ) -> None:
        for contract_name, relative_path in (
            EXACT_CONTRACTS.items()
        ):
            with self.subTest(contract=contract_name):
                expected_id = (
                    PUBLIC_SCHEMA_PREFIX + relative_path
                )
                self.assertEqual(
                    schema_id_for(
                        contract_name,
                        "1",
                        self.catalog,
                    ),
                    expected_id,
                )
                schema = self.store.schema_for_id(
                    expected_id
                )
                self.assertEqual(
                    schema["$schema"],
                    (
                        "https://json-schema.org/"
                        "draft/2020-12/schema"
                    ),
                )
                self.assertEqual(
                    schema["$id"],
                    expected_id,
                )

    def test_valid_manifest_fixtures_pass(self) -> None:
        manifest = load_json(
            FIXTURE_DIRECTORY / "manifest.json"
        )
        for fixture_name, schema_path in (
            manifest["valid"].items()
        ):
            contract_name = next(
                name
                for name, path in EXACT_CONTRACTS.items()
                if path == schema_path
            )
            with self.subTest(
                fixture=fixture_name,
                contract=contract_name,
            ):
                errors = list(
                    self.contract_validator(
                        contract_name
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY
                            / "valid"
                            / fixture_name
                        )
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message for error in errors
                    ),
                )

    def test_invalid_manifest_fixtures_fail(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_DIRECTORY / "manifest.json"
        )
        for fixture_name, schema_path in (
            manifest["invalid"].items()
        ):
            contract_name = next(
                name
                for name, path in EXACT_CONTRACTS.items()
                if path == schema_path
            )
            with self.subTest(
                fixture=fixture_name,
                contract=contract_name,
            ):
                errors = list(
                    self.contract_validator(
                        contract_name
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY
                            / "invalid"
                            / fixture_name
                        )
                    )
                )
                self.assertTrue(
                    errors,
                    (
                        f"{fixture_name} unexpectedly "
                        "passed validation"
                    ),
                )

    def test_exact_reference_objects_are_closed(
        self,
    ) -> None:
        expected_properties = {
            "exact_portia_work_ref": {
                "module_id",
                "class_id",
                "work_id",
                "work_kind",
                "contract_version",
            },
            "exact_local_record_ref": {
                "record_kind",
                "record_id",
                "contract_version",
            },
            "exact_portia_work_record_ref": {
                "work_ref",
                "record_ref",
            },
            "exceptional_removal_ref": {
                "module_id",
                "class_id",
                "removal_id",
                "contract_version",
            },
        }

        for contract_name, properties in (
            expected_properties.items()
        ):
            schema = self.store.schema_for_id(
                schema_id_for(
                    contract_name,
                    "1",
                    self.catalog,
                )
            )
            with self.subTest(contract=contract_name):
                self.assertEqual(
                    schema["type"],
                    "object",
                )
                self.assertFalse(
                    schema["additionalProperties"]
                )
                self.assertEqual(
                    set(schema["required"]),
                    properties,
                )
                self.assertEqual(
                    set(schema["properties"]),
                    properties,
                )

    def test_exact_contract_versions_are_non_nullable(
        self,
    ) -> None:
        for contract_name in (
            "exact_portia_work_ref",
            "exact_local_record_ref",
            "exceptional_removal_ref",
        ):
            schema = self.store.schema_for_id(
                schema_id_for(
                    contract_name,
                    "1",
                    self.catalog,
                )
            )
            contract_version = schema["properties"][
                "contract_version"
            ]
            with self.subTest(contract=contract_name):
                self.assertIn(
                    "contract_version",
                    schema["required"],
                )
                self.assertEqual(
                    set(contract_version),
                    {"$ref"},
                )

    def test_exact_work_record_composes_exact_refs(
        self,
    ) -> None:
        schema = self.store.schema_for_id(
            schema_id_for(
                "exact_portia_work_record_ref",
                "1",
                self.catalog,
            )
        )
        self.assertEqual(
            schema["properties"]["work_ref"]["$ref"],
            (
                PUBLIC_SCHEMA_PREFIX
                + EXACT_CONTRACTS[
                    "exact_portia_work_ref"
                ]
            ),
        )
        self.assertEqual(
            schema["properties"]["record_ref"]["$ref"],
            (
                PUBLIC_SCHEMA_PREFIX
                + EXACT_CONTRACTS[
                    "exact_local_record_ref"
                ]
            ),
        )

    def test_local_target_has_two_closed_branches(
        self,
    ) -> None:
        schema = self.store.schema_for_id(
            schema_id_for(
                "portia_local_work_target",
                "1",
                self.catalog,
            )
        )
        self.assertEqual(
            schema["oneOf"],
            [
                {"$ref": "#/$defs/workTarget"},
                {"$ref": "#/$defs/localRecordTarget"},
            ],
        )
        for definition in schema["$defs"].values():
            self.assertFalse(
                definition["additionalProperties"]
            )

    def test_exact_target_has_two_closed_branches(
        self,
    ) -> None:
        schema = self.store.schema_for_id(
            schema_id_for(
                "exact_portia_work_or_record_target",
                "1",
                self.catalog,
            )
        )
        self.assertEqual(
            schema["oneOf"],
            [
                {"$ref": "#/$defs/workTarget"},
                {"$ref": "#/$defs/workRecordTarget"},
            ],
        )
        for definition in schema["$defs"].values():
            self.assertFalse(
                definition["additionalProperties"]
            )

    def test_general_references_remain_nullable(
        self,
    ) -> None:
        general_work_ref = {
            "module_id": "portia",
            "class_id": "eng10_p2_2026",
            "work_id": "evt_example",
            "work_kind": "event",
            "contract_version": None,
        }
        general_local_ref = {
            "record_kind": "event_participant",
            "record_id": "ept_example",
            "contract_version": None,
        }

        for contract_name, instance in (
            ("portia_work_ref", general_work_ref),
            ("local_record_ref", general_local_ref),
        ):
            with self.subTest(contract=contract_name):
                errors = list(
                    validator_for(
                        contract_name,
                        "1",
                        catalog=self.catalog,
                        store=self.store,
                    ).iter_errors(instance)
                )
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message for error in errors
                    ),
                )

    def test_exact_contracts_document_resolution_rules(
        self,
    ) -> None:
        for contract_name in EXACT_CONTRACTS:
            schema = self.store.schema_for_id(
                schema_id_for(
                    contract_name,
                    "1",
                    self.catalog,
                )
            )
            description = schema["description"].lower()
            with self.subTest(contract=contract_name):
                self.assertIn("exact", description)
                self.assertIn(
                    "not",
                    description,
                )
                self.assertTrue(
                    (
                        "silently follow" in description
                        or "another version" in description
                    ),
                    description,
                )


if __name__ == "__main__":
    unittest.main()
