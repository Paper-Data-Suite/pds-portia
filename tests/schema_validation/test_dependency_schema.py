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


CONTRACT_NAME = "dependency"
SCHEMA_PATH = "schemas/v1/dependencies/dependency.schema.json"
PUBLIC_SCHEMA_PREFIX = "https://paper-data-suite.github.io/pds-portia/"
FIXTURE_DIRECTORY = FIXTURE_ROOT / "issue-12" / "dependency"


class DependencySchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            CONTRACT_NAME,
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.schema = cls.store.schema_for_id(
            schema_id_for(CONTRACT_NAME, "1", cls.catalog)
        )

    def test_contract_is_cataloged_with_path_id(self) -> None:
        expected_id = PUBLIC_SCHEMA_PREFIX + SCHEMA_PATH
        self.assertEqual(
            schema_id_for(CONTRACT_NAME, "1", self.catalog),
            expected_id,
        )
        self.assertEqual(self.schema["$id"], expected_id)
        self.assertEqual(
            self.schema["$schema"],
            "https://json-schema.org/draft/2020-12/schema",
        )

    def test_valid_manifest_fixtures_pass(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for fixture_name in manifest["valid"]:
            with self.subTest(fixture=fixture_name):
                errors = list(
                    self.validator.iter_errors(
                        load_json(FIXTURE_DIRECTORY / "valid" / fixture_name)
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_invalid_manifest_fixtures_fail(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for fixture_name in manifest["invalid"]:
            with self.subTest(fixture=fixture_name):
                errors = list(
                    self.validator.iter_errors(
                        load_json(FIXTURE_DIRECTORY / "invalid" / fixture_name)
                    )
                )
                self.assertTrue(
                    errors,
                    f"{fixture_name} unexpectedly passed validation",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        manifest = load_json(FIXTURE_DIRECTORY / "manifest.json")
        for fixture_name in manifest["application_invalid"]:
            with self.subTest(fixture=fixture_name):
                errors = list(
                    self.validator.iter_errors(
                        load_json(
                            FIXTURE_DIRECTORY
                            / "application-invalid"
                            / fixture_name
                        )
                    )
                )
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )

    def test_exact_envelope_is_closed(self) -> None:
        required = {
            "schema_version",
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "dependency_id",
            "status",
            "dependent",
            "dependency",
            "strength",
            "applies_to",
            "purpose",
            "creation_source",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        }
        optional = {"detail", "supersedes"}
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(set(self.schema["required"]), required)
        self.assertEqual(
            set(self.schema["properties"]),
            required | optional,
        )

    def test_lifecycle_vocabulary_is_exact(self) -> None:
        self.assertEqual(
            self.schema["properties"]["status"]["enum"],
            ["proposed", "active", "invalidated", "superseded"],
        )

    def test_strength_and_scope_vocabularies_are_exact(self) -> None:
        self.assertEqual(
            self.schema["properties"]["strength"]["enum"],
            ["required", "advisory"],
        )
        self.assertEqual(
            self.schema["properties"]["applies_to"]["enum"],
            ["activation", "current_use", "completion"],
        )

    def test_purpose_vocabulary_is_exact(self) -> None:
        self.assertEqual(
            self.schema["properties"]["purpose"]["enum"],
            [
                "identity_resolution",
                "evidentiary_support",
                "authorization_basis",
                "workflow_prerequisite",
                "implementation_input",
                "contextual_support",
                "other",
            ],
        )

    def test_other_purpose_requires_detail(self) -> None:
        conditional = self.schema["allOf"][0]
        self.assertEqual(
            conditional["if"]["properties"]["purpose"]["const"],
            "other",
        )
        self.assertEqual(conditional["then"]["required"], ["detail"])

    def test_dependent_composes_same_work_target(self) -> None:
        self.assertEqual(
            self.schema["properties"]["dependent"]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/targets/portia-local-work-target.schema.json",
        )

    def test_dependency_target_has_three_closed_branches(self) -> None:
        target = self.schema["$defs"]["dependencyTarget"]
        self.assertEqual(
            target["oneOf"],
            [
                {"$ref": "#/$defs/portiaWorkDependency"},
                {"$ref": "#/$defs/portiaRecordDependency"},
                {"$ref": "#/$defs/moduleRecordDependency"},
            ],
        )
        for name in (
            "portiaWorkDependency",
            "portiaRecordDependency",
            "moduleRecordDependency",
        ):
            self.assertFalse(
                self.schema["$defs"][name]["additionalProperties"]
            )

    def test_portia_dependency_branches_use_complete_references(self) -> None:
        self.assertEqual(
            self.schema["$defs"]["portiaWorkDependency"]["properties"][
                "work_ref"
            ]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/references/portia-work-ref.schema.json",
        )
        self.assertEqual(
            self.schema["$defs"]["portiaRecordDependency"]["properties"][
                "work_record_ref"
            ]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/references/portia-work-record-ref.schema.json",
        )

    def test_module_dependency_uses_module_work_record_ref(self) -> None:
        self.assertEqual(
            self.schema["$defs"]["moduleRecordDependency"]["properties"][
                "module_work_record_ref"
            ]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/references/module-work-record-ref.schema.json",
        )

    def test_supersession_uses_exact_dependency_predecessors(self) -> None:
        record_ref = self.schema["$defs"]["dependencyRecordRef"]
        self.assertEqual(
            record_ref["allOf"][0]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/references/exact-portia-work-record-ref.schema.json",
        )
        overlay = record_ref["allOf"][1]["properties"]["record_ref"][
            "allOf"
        ][1]["properties"]
        self.assertEqual(overlay["record_kind"]["const"], "dependency")
        self.assertEqual(overlay["contract_version"]["const"], "1")

    def test_supersession_reason_vocabulary_is_exact(self) -> None:
        reasons = self.schema["$defs"]["recognizedSupersessionRef"][
            "properties"
        ]["reason"]["enum"]
        self.assertEqual(
            reasons,
            [
                "dependent_corrected",
                "dependency_target_corrected",
                "strength_corrected",
                "evaluation_scope_corrected",
                "purpose_corrected",
                "duplicate_consolidated",
            ],
        )

    def test_creation_source_uses_shared_contract(self) -> None:
        self.assertEqual(
            self.schema["properties"]["creation_source"]["$ref"],
            PUBLIC_SCHEMA_PREFIX
            + "schemas/v1/provenance/creation-source.schema.json",
        )

    def test_derived_dependency_condition_is_not_canonical(self) -> None:
        self.assertNotIn("condition", self.schema["properties"])
        self.assertNotIn("use_disposition", self.schema["properties"])
        self.assertNotIn("dependency_health", self.schema["properties"])

    def test_application_boundaries_are_documented(self) -> None:
        comment = self.schema["$comment"].lower()
        for phrase in (
            "intrinsic-dependency duplication",
            "cycle detection",
            "no silent successor following",
            "no automatic lifecycle cascade",
        ):
            self.assertIn(phrase, comment)


if __name__ == "__main__":
    unittest.main()
