from __future__ import annotations

import unittest

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


LIFECYCLE_CONTRACTS = {
    "lifecycle_transition": (
        "schemas/v1/lifecycle/"
        "lifecycle-transition.schema.json"
    ),
    "lifecycle_history_correction": (
        "schemas/v1/lifecycle/"
        "lifecycle-history-correction.schema.json"
    ),
}

FIXTURE_DIRECTORY = (
    FIXTURE_ROOT
    / "issue-12"
    / "lifecycle-history"
)
PUBLIC_SCHEMA_PREFIX = (
    "https://paper-data-suite.github.io/pds-portia/"
)


class LifecycleHistorySchemaTests(unittest.TestCase):
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

    def contract_for_path(self, schema_path: str) -> str:
        return next(
            contract
            for contract, path in (
                LIFECYCLE_CONTRACTS.items()
            )
            if path == schema_path
        )

    def schema_for(self, contract_name: str):
        return self.store.schema_for_id(
            schema_id_for(
                contract_name,
                "1",
                self.catalog,
            )
        )

    def test_new_contracts_are_cataloged_with_path_ids(
        self,
    ) -> None:
        for contract_name, relative_path in (
            LIFECYCLE_CONTRACTS.items()
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
            contract_name = self.contract_for_path(
                schema_path
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
                        error.message
                        for error in errors
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
            contract_name = self.contract_for_path(
                schema_path
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

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_DIRECTORY / "manifest.json"
        )
        for fixture_name, metadata in (
            manifest["application_invalid"].items()
        ):
            contract_name = self.contract_for_path(
                metadata["schema_path"]
            )
            with self.subTest(
                fixture=fixture_name,
                rule=metadata["rule_id"],
            ):
                errors = list(
                    self.contract_validator(
                        contract_name
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY
                            / "application-invalid"
                            / fixture_name
                        )
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(
                        error.message
                        for error in errors
                    ),
                )

    def test_lifecycle_transition_envelope_is_exact(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_transition"
        )
        expected = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "transition_id",
            "target",
            "previous_transition",
            "from_status",
            "to_status",
            "reason",
            "effective_at",
            "creation_source",
            "created_at",
            "created_by",
        }
        self.assertEqual(
            set(schema["required"]),
            expected,
        )
        self.assertEqual(
            set(schema["properties"]),
            expected,
        )
        self.assertFalse(
            schema["additionalProperties"]
        )

    def test_history_correction_envelope_is_exact(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_history_correction"
        )
        expected = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "correction_id",
            "target",
            "previous_correction",
            "replaced_head",
            "replacement_head",
            "reason",
            "creation_source",
            "created_at",
            "created_by",
        }
        self.assertEqual(
            set(schema["required"]),
            expected,
        )
        self.assertEqual(
            set(schema["properties"]),
            expected,
        )
        self.assertFalse(
            schema["additionalProperties"]
        )

    def test_transition_predecessor_is_nullable_exact_ref(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_transition"
        )
        predecessor = schema["properties"][
            "previous_transition"
        ]
        self.assertEqual(
            predecessor["oneOf"],
            [
                {"type": "null"},
                {
                    "$ref": (
                        "#/$defs/"
                        "lifecycleTransitionRef"
                    )
                },
            ],
        )
        definition = schema["$defs"][
            "lifecycleTransitionRef"
        ]
        self.assertEqual(
            definition["allOf"][0]["$ref"],
            (
                PUBLIC_SCHEMA_PREFIX
                + "schemas/v1/references/"
                "exact-local-record-ref.schema.json"
            ),
        )
        constraints = definition["allOf"][1][
            "properties"
        ]
        self.assertEqual(
            constraints["record_kind"],
            {"const": "lifecycle_transition"},
        )
        self.assertEqual(
            constraints["contract_version"],
            {"const": "1"},
        )

    def test_correction_links_are_exact_and_nullable(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_history_correction"
        )
        previous = schema["properties"][
            "previous_correction"
        ]
        replacement = schema["properties"][
            "replacement_head"
        ]
        self.assertEqual(
            previous["oneOf"][0],
            {"type": "null"},
        )
        self.assertEqual(
            replacement["oneOf"][0],
            {"type": "null"},
        )
        self.assertEqual(
            schema["properties"]["replaced_head"],
            {
                "$ref": (
                    "#/$defs/"
                    "lifecycleTransitionRef"
                )
            },
        )
        correction_ref = schema["$defs"][
            "lifecycleHistoryCorrectionRef"
        ]["allOf"][1]["properties"]
        self.assertEqual(
            correction_ref["record_kind"],
            {
                "const": (
                    "lifecycle_history_correction"
                )
            },
        )
        self.assertEqual(
            correction_ref["contract_version"],
            {"const": "1"},
        )

    def test_transition_reason_has_closed_shared_categories(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_transition"
        )
        definition = schema["$defs"][
            "recognizedTransitionReason"
        ]
        self.assertEqual(
            set(
                definition["properties"][
                    "category"
                ]["enum"]
            ),
            {
                "workflow",
                "record_validity",
                "correction",
                "dependency",
                "consolidation",
                "migration",
            },
        )
        self.assertFalse(
            definition["additionalProperties"]
        )
        other = schema["$defs"][
            "otherTransitionReason"
        ]
        self.assertEqual(
            set(other["required"]),
            {"category", "code", "detail"},
        )
        self.assertEqual(
            other["properties"]["category"],
            {"const": "other"},
        )
        self.assertEqual(
            other["properties"]["code"],
            {"const": "other"},
        )

    def test_history_correction_reason_has_closed_codes(
        self,
    ) -> None:
        schema = self.schema_for(
            "lifecycle_history_correction"
        )
        recognized = schema["$defs"][
            "recognizedCorrectionReason"
        ]
        self.assertEqual(
            set(
                recognized["properties"][
                    "code"
                ]["enum"]
            ),
            {
                "wrong_target",
                "wrong_predecessor",
                "wrong_from_status",
                "wrong_to_status",
                "wrong_reason",
                "wrong_effective_at",
                "wrong_attribution",
                "duplicate_transition",
                "transition_should_not_exist",
                "multiple_fields_corrected",
            },
        )
        self.assertFalse(
            recognized["additionalProperties"]
        )
        other = schema["$defs"][
            "otherCorrectionReason"
        ]
        self.assertEqual(
            set(other["required"]),
            {"code", "detail"},
        )

    def test_creation_source_is_restricted_to_digital_or_import(
        self,
    ) -> None:
        for contract_name in LIFECYCLE_CONTRACTS:
            schema = self.schema_for(contract_name)
            source = schema["$defs"][
                "digitalOrImportCreationSource"
            ]
            with self.subTest(
                contract=contract_name
            ):
                self.assertEqual(
                    source["allOf"][1][
                        "properties"
                    ]["type"]["enum"],
                    ["digital_entry", "import"],
                )

    def test_immutable_records_exclude_mutable_fields(
        self,
    ) -> None:
        prohibited = {
            "status",
            "updated_at",
            "updated_by",
            "operation_id",
        }
        for contract_name in LIFECYCLE_CONTRACTS:
            schema = self.schema_for(contract_name)
            with self.subTest(
                contract=contract_name
            ):
                self.assertTrue(
                    prohibited.isdisjoint(
                        schema["properties"]
                    )
                )
        transition = self.schema_for(
            "lifecycle_transition"
        )
        correction = self.schema_for(
            "lifecycle_history_correction"
        )
        self.assertNotIn(
            "recorded_at",
            transition["properties"],
        )
        self.assertNotIn(
            "authorized_by",
            transition["properties"],
        )
        self.assertNotIn(
            "effective_at",
            correction["properties"],
        )

    def test_application_invariants_are_documented(
        self,
    ) -> None:
        manifest = load_json(
            FIXTURE_DIRECTORY / "manifest.json"
        )
        rules_by_contract = {
            contract: set(
                self.schema_for(contract)[
                    "x-portia-application-invariants"
                ]
            )
            for contract in LIFECYCLE_CONTRACTS
        }
        for metadata in (
            manifest["application_invalid"].values()
        ):
            contract = self.contract_for_path(
                metadata["schema_path"]
            )
            with self.subTest(
                contract=contract,
                rule=metadata["rule_id"],
            ):
                self.assertIn(
                    metadata["rule_id"],
                    rules_by_contract[contract],
                )

    def test_schemas_preserve_append_only_history(
        self,
    ) -> None:
        transition = self.schema_for(
            "lifecycle_transition"
        )["description"].lower()
        correction = self.schema_for(
            "lifecycle_history_correction"
        )["description"].lower()
        self.assertIn("immutable", transition)
        self.assertIn("append-only", transition)
        self.assertIn(
            "must not",
            transition,
        )
        self.assertIn("immutable", correction)
        self.assertIn("append-only", correction)
        self.assertIn(
            "never edits transitions",
            correction,
        )
        self.assertIn(
            "silently rewrites history",
            correction,
        )


if __name__ == "__main__":
    unittest.main()
