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
    "event_participant": {
        "version": "3",
        "path": "schemas/v3/event-participant.schema.json",
    },
    "event_participant_role": {
        "version": "3",
        "path": "schemas/v3/event-participant-role.schema.json",
    },
    "work_relationship": {
        "version": "2",
        "path": "schemas/v2/work-relationship.schema.json",
    },
}
FIXTURE_DIRECTORY = (
    FIXTURE_ROOT / "issue-12" / "record-family-upgrades"
)
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"


class RecordFamilyUpgradeSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(
            contract,
            CONTRACTS[contract]["version"],
            catalog=self.catalog,
            store=self.store,
        )

    def schema(self, contract: str):
        version = CONTRACTS[contract]["version"]
        return self.store.schema_for_id(
            schema_id_for(contract, version, self.catalog)
        )

    def contract_for_path(self, path: str) -> str:
        return next(
            name
            for name, metadata in CONTRACTS.items()
            if metadata["path"] == path
        )

    def test_contracts_are_cataloged_with_canonical_path_ids(self) -> None:
        for contract, metadata in CONTRACTS.items():
            with self.subTest(contract=contract):
                expected = PUBLIC_SCHEMA_PREFIX + metadata["path"]
                self.assertEqual(
                    schema_id_for(
                        contract,
                        metadata["version"],
                        self.catalog,
                    ),
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
        for filename, schema_path in manifest["valid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(
                        self.contract_for_path(schema_path)
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY / "valid" / filename
                        )
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_invalid_manifest_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for filename, schema_path in manifest["invalid"].items():
            with self.subTest(fixture=filename):
                errors = list(
                    self.validator(
                        self.contract_for_path(schema_path)
                    ).iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY / "invalid" / filename
                        )
                    )
                )
                self.assertTrue(
                    errors,
                    f"{filename} unexpectedly passed",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
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

    def test_participant_envelope_preserves_v2_domain_fields(self) -> None:
        schema = self.schema("event_participant")
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "participant_id",
            "status",
            "subject",
            "creation_source",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(
            set(schema["properties"]),
            required | {"supersedes"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_role_envelope_preserves_v2_domain_fields(self) -> None:
        schema = self.schema("event_participant_role")
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "role_id",
            "target",
            "status",
            "role_type",
            "creation_source",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(
            set(schema["properties"]),
            required | {"basis", "detail", "supersedes"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_relationship_envelope_preserves_v1_domain_fields(self) -> None:
        schema = self.schema("work_relationship")
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "relationship_id",
            "status",
            "relationship_type",
            "source",
            "target",
            "creation_source",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(
            set(schema["properties"]),
            required | {"detail", "supersedes"},
        )
        self.assertFalse(schema["additionalProperties"])

    def test_lifecycle_vocabularies_are_unchanged(self) -> None:
        expected = [
            "proposed",
            "active",
            "invalidated",
            "superseded",
        ]
        for contract in CONTRACTS:
            with self.subTest(contract=contract):
                self.assertEqual(
                    self.schema(contract)["properties"]["status"]["enum"],
                    expected,
                )

    def test_participant_subject_union_is_preserved(self) -> None:
        defs = self.schema("event_participant")["$defs"]
        branches = {
            branch["$ref"].split("/")[-1]
            for branch in defs["subject"]["oneOf"]
        }
        self.assertEqual(
            branches,
            {
                "rosterStudentSubject",
                "actorSubject",
                "descriptivePersonSubject",
                "unknownPersonSubject",
            },
        )

    def test_participant_supersession_uses_complete_exact_references(self) -> None:
        ref_schema = self.schema("event_participant")["$defs"][
            "participantWorkRecordRef"
        ]
        self.assertTrue(
            ref_schema["allOf"][0]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )
        entry = self.schema("event_participant")["$defs"][
            "participantSupersessionRef"
        ]
        self.assertEqual(
            set(entry["required"]),
            {"work_record_ref", "reason"},
        )
        self.assertNotIn("record_ref", entry["properties"])

    def test_participant_predecessor_versions_cover_history_and_v3(self) -> None:
        ref_schema = self.schema("event_participant")["$defs"][
            "participantWorkRecordRef"
        ]
        versions = ref_schema["allOf"][1]["properties"][
            "record_ref"
        ]["allOf"][0]["properties"]["contract_version"]["enum"]
        self.assertEqual(versions, ["1", "2", "3"])

    def test_participant_reasons_include_migration_and_ownership(self) -> None:
        reasons = self.schema("event_participant")["$defs"][
            "participantSupersessionRef"
        ]["properties"]["reason"]["enum"]
        self.assertIn("work_root_corrected", reasons)
        self.assertIn("contract_migrated", reasons)

    def test_role_target_remains_one_same_work_participant(self) -> None:
        defs = self.schema("event_participant_role")["$defs"]
        target = defs["singularParticipantTarget"]
        self.assertTrue(
            target["allOf"][0]["$ref"].endswith(
                "portia-target-ref.schema.json"
            )
        )
        overlay = target["allOf"][1]["properties"]
        self.assertEqual(
            overlay["kind"]["const"],
            "event_participant",
        )

    def test_role_target_accepts_participant_versions_1_to_3(self) -> None:
        participant_ref = self.schema(
            "event_participant_role"
        )["$defs"]["participantRecordRef"]
        versions = participant_ref["allOf"][1]["properties"][
            "contract_version"
        ]["enum"]
        self.assertEqual(versions, ["1", "2", "3"])

    def test_role_basis_union_is_preserved(self) -> None:
        defs = self.schema("event_participant_role")["$defs"]
        branches = {
            branch["$ref"].split("/")[-1]
            for branch in defs["basisEntry"]["oneOf"]
        }
        self.assertEqual(
            branches,
            {
                "accountRefBasis",
                "observationRefBasis",
                "paperCaptureBasis",
                "importSourceBasis",
            },
        )

    def test_role_contextual_detail_rule_is_preserved(self) -> None:
        conditional = self.schema("event_participant_role")["allOf"][0]
        self.assertEqual(
            conditional["if"]["properties"]["role_type"]["const"],
            "contextual",
        )
        nested = conditional["then"]["allOf"][0]
        self.assertEqual(nested["then"]["required"], ["detail"])

    def test_role_reported_basis_rules_are_preserved(self) -> None:
        conditionals = self.schema("event_participant_role")["allOf"]
        self.assertEqual(
            conditionals[1]["if"]["properties"]["role_type"]["const"],
            "reported_involved",
        )
        self.assertEqual(
            conditionals[2]["then"]["properties"]["basis"][
                "minContains"
            ],
            1,
        )

    def test_role_supersession_uses_complete_exact_references(self) -> None:
        ref_schema = self.schema("event_participant_role")["$defs"][
            "roleWorkRecordRef"
        ]
        self.assertTrue(
            ref_schema["allOf"][0]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )
        entry = self.schema("event_participant_role")["$defs"][
            "roleSupersessionRef"
        ]
        self.assertIn("work_record_ref", entry["properties"])
        self.assertNotIn("record_ref", entry["properties"])

    def test_role_reasons_include_migration_and_ownership(self) -> None:
        reasons = self.schema("event_participant_role")["$defs"][
            "roleSupersessionRef"
        ]["properties"]["reason"]["enum"]
        self.assertIn("work_root_corrected", reasons)
        self.assertIn("contract_migrated", reasons)

    def test_relationship_endpoints_are_exact_versioned_references(self) -> None:
        schema = self.schema("work_relationship")
        self.assertTrue(
            schema["properties"]["source"]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )
        self.assertTrue(
            schema["properties"]["target"]["allOf"][0]["$ref"].endswith(
                "exact-portia-work-ref.schema.json"
            )
        )

    def test_relationship_target_remains_event_only(self) -> None:
        target = self.schema("work_relationship")["properties"][
            "target"
        ]
        self.assertEqual(
            target["allOf"][1]["properties"]["work_kind"]["const"],
            "event",
        )

    def test_relationship_supersession_uses_complete_exact_references(self) -> None:
        ref_schema = self.schema("work_relationship")["$defs"][
            "relationshipWorkRecordRef"
        ]
        self.assertTrue(
            ref_schema["allOf"][0]["$ref"].endswith(
                "exact-portia-work-record-ref.schema.json"
            )
        )
        versions = ref_schema["allOf"][1]["properties"][
            "record_ref"
        ]["allOf"][0]["properties"]["contract_version"]["enum"]
        self.assertEqual(versions, ["1", "2"])

    def test_relationship_reasons_include_migration_and_ownership(self) -> None:
        reasons = self.schema("work_relationship")["$defs"][
            "supersessionEntry"
        ]["properties"]["reason"]["enum"]
        self.assertIn("work_root_corrected", reasons)
        self.assertIn("contract_migrated", reasons)

    def test_other_supersession_reason_requires_detail(self) -> None:
        locations = (
            ("event_participant", "participantSupersessionRef"),
            ("event_participant_role", "roleSupersessionRef"),
            ("work_relationship", "supersessionEntry"),
        )
        for contract, definition in locations:
            with self.subTest(contract=contract):
                conditional = self.schema(contract)["$defs"][
                    definition
                ]["allOf"][0]
                self.assertEqual(
                    conditional["if"]["properties"]["reason"]["const"],
                    "other",
                )
                self.assertEqual(
                    conditional["then"]["required"],
                    ["detail"],
                )

    def test_creation_provenance_behavior_is_preserved(self) -> None:
        participant = self.schema("event_participant")
        self.assertTrue(
            participant["properties"]["creation_source"]["$ref"].endswith(
                "creation-source.schema.json"
            )
        )
        for contract in (
            "event_participant_role",
            "work_relationship",
        ):
            source = self.schema(contract)["properties"][
                "creation_source"
            ]
            self.assertEqual(
                source["allOf"][1]["not"]["properties"]["stage"][
                    "const"
                ],
                "preallocated",
            )

    def test_application_fixture_rules_are_declared_by_contract(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        invariants = {
            contract: set(
                self.schema(contract)[
                    "x-portia-application-invariants"
                ]
            )
            for contract in CONTRACTS
        }
        for metadata in manifest["application_invalid"].values():
            contract = self.contract_for_path(
                metadata["schema_path"]
            )
            with self.subTest(
                contract=contract,
                rule=metadata["rule_id"],
            ):
                self.assertIn(
                    metadata["rule_id"],
                    invariants[contract],
                )


if __name__ == "__main__":
    unittest.main()
