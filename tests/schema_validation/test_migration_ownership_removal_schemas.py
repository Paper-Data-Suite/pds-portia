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


CONTRACTS = {
    "record_migration": "schemas/v1/migrations/record-migration.schema.json",
    "ownership_correction": (
        "schemas/v1/corrections/ownership-correction.schema.json"
    ),
    "exceptional_removal": (
        "schemas/v1/removals/exceptional-removal.schema.json"
    ),
}
FIXTURE_DIRECTORY = (
    FIXTURE_ROOT / "issue-12" / "migration-ownership-removal"
)
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"


class MigrationOwnershipRemovalSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, name: str):
        return validator_for(
            name, "1", catalog=self.catalog, store=self.store
        )

    def schema(self, name: str):
        return self.store.schema_for_id(
            schema_id_for(name, "1", self.catalog)
        )

    def contract_for_path(self, path: str) -> str:
        return next(
            name for name, value in CONTRACTS.items() if value == path
        )

    def test_contracts_are_cataloged_with_canonical_path_ids(self) -> None:
        for name, path in CONTRACTS.items():
            with self.subTest(contract=name):
                expected = PUBLIC_SCHEMA_PREFIX + path
                self.assertEqual(
                    schema_id_for(name, "1", self.catalog),
                    expected,
                )
                schema = self.store.schema_for_id(expected)
                self.assertEqual(schema["$id"], expected)
                self.assertEqual(
                    schema["$schema"],
                    "https://json-schema.org/draft/2020-12/schema",
                )

    def test_valid_manifest_fixtures_pass(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, path in manifest["valid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(
                        self.contract_for_path(path)
                    ).iter_errors(
                        load_json(FIXTURE_DIRECTORY / "valid" / filename)
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_invalid_manifest_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, path in manifest["invalid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(
                        self.contract_for_path(path)
                    ).iter_errors(
                        load_json(FIXTURE_DIRECTORY / "invalid" / filename)
                    )
                )
                self.assertTrue(
                    errors,
                    f"{filename} unexpectedly passed validation",
                )

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, metadata in manifest[
            "application_invalid"
        ].items():
            with self.subTest(
                fixture=filename,
                rule=metadata["rule_id"],
            ):
                errors = list(
                    self.validator(
                        self.contract_for_path(
                            metadata["schema_path"]
                        )
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY
                            / "application-invalid"
                            / filename
                        )
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_application_fixture_rules_are_declared_by_schemas(
        self,
    ) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        rules_by_contract = {
            name: set(
                self.schema(name)["x-portia-application-invariants"]
            )
            for name in CONTRACTS
        }
        for metadata in manifest["application_invalid"].values():
            contract = self.contract_for_path(metadata["schema_path"])
            with self.subTest(
                contract=contract,
                rule=metadata["rule_id"],
            ):
                self.assertIn(
                    metadata["rule_id"],
                    rules_by_contract[contract],
                )

    def test_migration_envelope_is_exact_and_immutable(self) -> None:
        schema = self.schema("record_migration")
        expected = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "migration_id",
            "source",
            "destination",
            "reason",
            "transformation",
            "effective_at",
            "creation_source",
            "created_at",
            "created_by",
        }
        self.assertEqual(set(schema["required"]), expected)
        self.assertEqual(set(schema["properties"]), expected)
        self.assertFalse(schema["additionalProperties"])

    def test_migration_excludes_job_and_mutable_fields(self) -> None:
        properties = self.schema("record_migration")["properties"]
        prohibited = {
            "status",
            "updated_at",
            "updated_by",
            "previous_migration",
            "operation_id",
            "authorized_by",
            "reviewed_by",
        }
        self.assertTrue(prohibited.isdisjoint(properties))

    def test_migration_endpoint_union_has_two_closed_branches(self) -> None:
        defs = self.schema("record_migration")["$defs"]
        self.assertEqual(
            defs["migrationEndpoint"]["oneOf"],
            [
                {"$ref": "#/$defs/workEndpoint"},
                {"$ref": "#/$defs/workRecordEndpoint"},
            ],
        )
        self.assertFalse(defs["workEndpoint"]["additionalProperties"])
        self.assertFalse(
            defs["workRecordEndpoint"]["additionalProperties"]
        )

    def test_migration_endpoints_use_exact_references(self) -> None:
        defs = self.schema("record_migration")["$defs"]
        self.assertTrue(
            defs["workEndpoint"]["properties"]["work_ref"]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )
        self.assertTrue(
            defs["workRecordEndpoint"]["properties"][
                "work_record_ref"
            ]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )

    def test_migration_structurally_requires_matching_endpoint_kinds(
        self,
    ) -> None:
        schema = self.schema("record_migration")
        self.assertEqual(len(schema["allOf"]), 2)
        destination_kinds = {
            conditional["then"]["properties"]["destination"][
                "properties"
            ]["kind"]["const"]
            for conditional in schema["allOf"]
        }
        self.assertEqual(destination_kinds, {"work", "work_record"})

    def test_migration_reason_categories_are_closed(self) -> None:
        defs = self.schema("record_migration")["$defs"]
        categories = set(
            defs["recognizedMigrationReason"]["properties"][
                "category"
            ]["enum"]
        )
        self.assertEqual(
            categories,
            {
                "contract_upgrade",
                "contract_normalization",
                "canonical_representation_change",
            },
        )
        self.assertEqual(
            set(defs["otherMigrationReason"]["required"]),
            {"category", "code", "detail"},
        )

    def test_migration_transformation_is_closed_and_versioned(
        self,
    ) -> None:
        transformation = self.schema("record_migration")["$defs"][
            "transformation"
        ]
        self.assertEqual(
            set(transformation["required"]),
            {"transformer_id", "transformer_version"},
        )
        self.assertFalse(transformation["additionalProperties"])

    def test_migration_creation_source_is_digital_only(self) -> None:
        source = self.schema("record_migration")["$defs"][
            "digitalCreationSource"
        ]
        self.assertEqual(
            source["properties"]["type"]["const"],
            "digital_entry",
        )
        self.assertFalse(source["additionalProperties"])

    def test_ownership_envelope_is_exact_and_immutable(self) -> None:
        schema = self.schema("ownership_correction")
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "correction_id",
            "correction_kind",
            "source",
            "destination",
            "reason",
            "effective_at",
            "creation_source",
            "created_at",
            "created_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(
            set(schema["properties"]),
            required | {"parent_correction"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_ownership_correction_kinds_are_exact(self) -> None:
        kinds = self.schema("ownership_correction")["properties"][
            "correction_kind"
        ]["enum"]
        self.assertEqual(
            kinds,
            ["event_class_ownership", "child_work_root"],
        )

    def test_ownership_kind_selects_matching_endpoint_branch(
        self,
    ) -> None:
        conditionals = self.schema("ownership_correction")["allOf"]
        by_kind = {
            item["if"]["properties"]["correction_kind"]["const"]: item
            for item in conditionals
        }
        self.assertEqual(
            by_kind["event_class_ownership"]["then"]["properties"][
                "source"
            ]["$ref"],
            "#/$defs/eventWorkEndpoint",
        )
        self.assertEqual(
            by_kind["child_work_root"]["then"]["properties"][
                "source"
            ]["$ref"],
            "#/$defs/workRecordEndpoint",
        )

    def test_ownership_endpoints_are_event_scoped_and_exact(
        self,
    ) -> None:
        defs = self.schema("ownership_correction")["$defs"]
        self.assertTrue(
            defs["eventWorkRef"]["allOf"][0]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )
        self.assertEqual(
            defs["eventWorkRef"]["allOf"][1]["properties"][
                "work_kind"
            ]["const"],
            "event",
        )
        self.assertTrue(
            defs["eventWorkRecordRef"]["allOf"][0]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )

    def test_ownership_parent_reference_is_exact_and_typed(
        self,
    ) -> None:
        ref = self.schema("ownership_correction")["$defs"][
            "ownershipCorrectionRef"
        ]
        self.assertTrue(
            ref["allOf"][0]["$ref"].endswith(
                "exact-local-record-ref.schema.json"
            )
        )
        constrained = ref["allOf"][1]["properties"]
        self.assertEqual(
            constrained["record_kind"]["const"],
            "ownership_correction",
        )
        self.assertEqual(
            constrained["contract_version"]["const"],
            "1",
        )

    def test_ownership_reason_vocabulary_is_closed(self) -> None:
        defs = self.schema("ownership_correction")["$defs"]
        recognized = set(
            defs["recognizedOwnershipReason"]["properties"]["code"][
                "enum"
            ]
        )
        self.assertEqual(
            recognized,
            {
                "wrong_class",
                "wrong_event_root",
                "incorrect_initial_routing",
            },
        )
        self.assertEqual(
            set(defs["otherOwnershipReason"]["required"]),
            {"code", "detail"},
        )

    def test_ownership_creation_source_is_digital_only(self) -> None:
        source = self.schema("ownership_correction")["$defs"][
            "digitalCreationSource"
        ]
        self.assertEqual(
            source["properties"]["type"]["const"],
            "digital_entry",
        )

    def test_removal_envelope_is_exact_and_immutable(self) -> None:
        schema = self.schema("exceptional_removal")
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "removal_id",
            "target",
            "reason",
            "authorization",
            "content_evidence",
            "effective_at",
            "creation_source",
            "created_at",
            "created_by",
        }
        optional = {"parent_removal", "lifecycle_snapshot"}
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(
            set(schema["properties"]),
            required | optional,
        )
        self.assertFalse(schema["additionalProperties"])

    def test_removal_excludes_lifecycle_and_replacement_fields(
        self,
    ) -> None:
        properties = self.schema("exceptional_removal")["properties"]
        prohibited = {
            "status",
            "updated_at",
            "updated_by",
            "supersedes",
            "operation_id",
            "replacement",
        }
        self.assertTrue(prohibited.isdisjoint(properties))

    def test_removal_target_union_uses_exact_references(self) -> None:
        defs = self.schema("exceptional_removal")["$defs"]
        self.assertEqual(
            defs["removalTarget"]["oneOf"],
            [
                {"$ref": "#/$defs/workTarget"},
                {"$ref": "#/$defs/workRecordTarget"},
            ],
        )
        self.assertTrue(
            defs["workTarget"]["properties"]["work_ref"]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )
        self.assertTrue(
            defs["workRecordTarget"]["properties"][
                "work_record_ref"
            ]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )

    def test_removal_parent_uses_class_scoped_exact_reference(
        self,
    ) -> None:
        ref = self.schema("exceptional_removal")["properties"][
            "parent_removal"
        ]["$ref"]
        self.assertTrue(
            ref.endswith("exceptional-removal-ref.schema.json")
        )

    def test_removal_reason_categories_are_closed(self) -> None:
        defs = self.schema("exceptional_removal")["$defs"]
        categories = set(
            defs["recognizedRemovalReason"]["properties"]["category"][
                "enum"
            ]
        )
        self.assertEqual(
            categories,
            {
                "legal_requirement",
                "privacy_requirement",
                "security_containment",
                "administrative_test_data",
                "unrecoverable_corruption",
            },
        )
        self.assertEqual(
            set(defs["otherRemovalReason"]["required"]),
            {"category", "code", "detail"},
        )

    def test_removal_authorization_requires_local_operator(self) -> None:
        defs = self.schema("exceptional_removal")["$defs"]
        authorization = defs["authorization"]
        self.assertEqual(
            set(authorization["required"]),
            {"decision_reference", "authorized_by"},
        )
        self.assertEqual(
            defs["localOperator"]["properties"]["type"]["const"],
            "local_operator",
        )
        self.assertNotIn("systemProcess", defs)

    def test_removal_content_evidence_has_two_closed_branches(
        self,
    ) -> None:
        defs = self.schema("exceptional_removal")["$defs"]
        self.assertEqual(
            defs["contentEvidence"]["oneOf"],
            [
                {"$ref": "#/$defs/saltedSha256Evidence"},
                {"$ref": "#/$defs/unavailableEvidence"},
            ],
        )
        salted = defs["saltedSha256Evidence"]
        self.assertEqual(
            salted["properties"]["digest"]["pattern"],
            "^[0-9a-f]{64}$",
        )
        self.assertFalse(salted["additionalProperties"])
        self.assertFalse(
            defs["unavailableEvidence"]["additionalProperties"]
        )

    def test_unavailable_evidence_requires_corruption_category(
        self,
    ) -> None:
        conditional = self.schema("exceptional_removal")["allOf"][1]
        self.assertEqual(
            conditional["if"]["properties"]["content_evidence"][
                "properties"
            ]["kind"]["const"],
            "unavailable",
        )
        self.assertEqual(
            conditional["then"]["properties"]["reason"]["properties"][
                "category"
            ]["const"],
            "unrecoverable_corruption",
        )

    def test_lifecycle_snapshot_is_minimal_and_transition_typed(
        self,
    ) -> None:
        defs = self.schema("exceptional_removal")["$defs"]
        snapshot = defs["lifecycleSnapshot"]
        self.assertEqual(set(snapshot["required"]), {"status"})
        self.assertEqual(
            set(snapshot["properties"]),
            {"status", "selected_transition"},
        )
        self.assertFalse(snapshot["additionalProperties"])
        transition = defs["lifecycleTransitionWorkRecordRef"]
        nested = transition["allOf"][1]["properties"]["record_ref"][
            "allOf"
        ][1]["properties"]
        self.assertEqual(
            nested["record_kind"]["const"],
            "lifecycle_transition",
        )
        self.assertEqual(nested["contract_version"]["const"], "1")

    def test_removal_creation_source_is_digital_only(self) -> None:
        source = self.schema("exceptional_removal")["$defs"][
            "digitalCreationSource"
        ]
        self.assertEqual(
            source["properties"]["type"]["const"],
            "digital_entry",
        )

    def test_descriptions_preserve_operation_boundaries(self) -> None:
        migration = self.schema("record_migration")["description"].lower()
        ownership = self.schema("ownership_correction")[
            "description"
        ].lower()
        removal = self.schema("exceptional_removal")[
            "description"
        ].lower()
        self.assertIn("representation-only", migration)
        self.assertIn("immutable", migration)
        self.assertIn("incorrectly owned", ownership)
        self.assertIn("destination", ownership)
        self.assertIn("minimal immutable", removal)
        self.assertIn("exceptional", removal)


if __name__ == "__main__":
    unittest.main()
