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


REFERENCE_CASES = {
    "roster_student_ref": (
        "roster-student-ref.schema.json"
    ),
    "actor_ref": "actor-ref.schema.json",
    "local_record_ref": (
        "local-record-ref.schema.json"
    ),
    "portia_work_ref": (
        "portia-work-ref.schema.json"
    ),
    "portia_work_record_ref": (
        "portia-work-record-ref.schema.json"
    ),
}

REFERENCE_FIXTURE_ROOT = (
    FIXTURE_ROOT / "shared" / "references"
)


class ReferenceSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = (
            load_validated_catalog_and_store()
        )

    def reference_validator(self, contract_name: str):
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
                REFERENCE_FIXTURE_ROOT
                / contract_name
                / expected_result
            ).glob("*.json")
        )

    def test_reference_contracts_are_cataloged(self) -> None:
        for contract_name, filename in REFERENCE_CASES.items():
            with self.subTest(contract=contract_name):
                expected_id = (
                    "https://paper-data-suite.github.io/"
                    "pds-portia/schemas/v1/references/"
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

    def test_valid_reference_fixtures(self) -> None:
        for contract_name in REFERENCE_CASES:
            validator = self.reference_validator(
                contract_name
            )
            paths = self.fixture_paths(
                contract_name,
                "valid",
            )
            self.assertTrue(
                paths,
                f"No valid fixtures found for "
                f"{contract_name}",
            )

            for path in paths:
                with self.subTest(
                    contract=contract_name,
                    fixture=path.name,
                ):
                    errors = list(
                        validator.iter_errors(
                            load_json(path)
                        )
                    )
                    self.assertFalse(
                        errors,
                        "\n".join(
                            error.message
                            for error in errors
                        ),
                    )

    def test_invalid_reference_fixtures(self) -> None:
        for contract_name in REFERENCE_CASES:
            validator = self.reference_validator(
                contract_name
            )
            paths = self.fixture_paths(
                contract_name,
                "invalid",
            )
            self.assertTrue(
                paths,
                f"No invalid fixtures found for "
                f"{contract_name}",
            )

            for path in paths:
                with self.subTest(
                    contract=contract_name,
                    fixture=path.name,
                ):
                    errors = list(
                        validator.iter_errors(
                            load_json(path)
                        )
                    )
                    self.assertTrue(
                        errors,
                        f"{path.name} unexpectedly "
                        "passed validation",
                    )

    def test_reference_objects_are_closed(self) -> None:
        expected_properties = {
            "roster_student_ref": {
                "class_id",
                "student_id",
            },
            "actor_ref": {"actor_id"},
            "local_record_ref": {
                "record_kind",
                "record_id",
                "contract_version",
            },
            "portia_work_ref": {
                "module_id",
                "class_id",
                "work_id",
                "work_kind",
                "contract_version",
            },
            "portia_work_record_ref": {
                "work_ref",
                "record_ref",
            },
        }

        for contract_name, property_names in (
            expected_properties.items()
        ):
            schema_id = schema_id_for(
                contract_name,
                "1",
                self.catalog,
            )
            schema = self.store.schema_for_id(
                schema_id
            )
            with self.subTest(
                contract=contract_name
            ):
                self.assertEqual(
                    schema["type"],
                    "object",
                )
                self.assertFalse(
                    schema["additionalProperties"]
                )
                self.assertEqual(
                    set(schema["required"]),
                    property_names,
                )
                self.assertEqual(
                    set(schema["properties"]),
                    property_names,
                )

    def test_nullable_versions_are_still_required(
        self,
    ) -> None:
        for contract_name in (
            "local_record_ref",
            "portia_work_ref",
        ):
            schema_id = schema_id_for(
                contract_name,
                "1",
                self.catalog,
            )
            schema = self.store.schema_for_id(
                schema_id
            )
            with self.subTest(
                contract=contract_name
            ):
                self.assertIn(
                    "contract_version",
                    schema["required"],
                )

    def test_portia_work_ref_has_kind_specific_branches(
        self,
    ) -> None:
        schema_id = schema_id_for(
            "portia_work_ref",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(len(schema["oneOf"]), 2)

        branch_kinds = {
            branch["properties"]["work_kind"]["const"]
            for branch in schema["oneOf"]
        }
        self.assertEqual(
            branch_kinds,
            {"event", "support_process"},
        )


    def test_portia_work_record_ref_composes_public_refs(
        self,
    ) -> None:
        schema_id = schema_id_for(
            "portia_work_record_ref",
            "1",
            self.catalog,
        )
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(
            schema["properties"]["work_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/references/"
                "portia-work-ref.schema.json"
            ),
        )
        self.assertEqual(
            schema["properties"]["record_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/references/"
                "local-record-ref.schema.json"
            ),
        )


if __name__ == "__main__":
    unittest.main()
