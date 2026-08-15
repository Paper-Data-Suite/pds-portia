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
    / "issue-21"
)


class Issue21ReviewReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.export_validator = validator_for(
            "deliberate_export",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.inventory_validator = validator_for(
            "export_source_inventory",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )

    def test_source_artifact_inventory_does_not_persist_raw_locator(self) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "exports"
            / "export-source-inventory.schema.json"
        )
        props = schema["$defs"]["artifactSource"]["properties"]
        self.assertNotIn("artifact_ref", props)
        self.assertIn("artifact_kind", props)
        self.assertEqual(
            props["artifact_identity_algorithm"]["const"],
            "portia_source_artifact_identity_v1",
        )
        self.assertIn("artifact_identity_digest", props)
        invariants = set(schema["x-portia-application-invariants"])
        self.assertIn(
            "portia.export_source_inventory.artifact_locator_not_persisted",
            invariants,
        )

    def test_privacy_minimal_artifact_identity_fixture_is_valid(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "export-source-inventory"
            / "valid"
            / "artifact-identity-inventory.json"
        )
        errors = list(self.inventory_validator.iter_errors(value))
        self.assertFalse(
            errors,
            "\n".join(error.message for error in errors),
        )
        serialized = str(value)
        self.assertNotIn("external_reference", serialized)
        self.assertNotIn("workspace_relative_path", serialized)
        self.assertNotIn("token=", serialized)

    def test_raw_artifact_locator_fixture_fails_structurally(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "export-source-inventory"
            / "invalid"
            / "raw-source-artifact-locator.json"
        )
        self.assertTrue(list(self.inventory_validator.iter_errors(value)))

    def test_focal_exports_are_work_scoped(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "deliberate-export"
            / "invalid"
            / "focal-purpose-class-scope.json"
        )
        self.assertTrue(list(self.export_validator.iter_errors(value)))

        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "exports"
            / "deliberate-export.schema.json"
        )
        invariants = set(schema["x-portia-application-invariants"])
        self.assertIn(
            "portia.deliberate_export.focal_purposes_require_work_scope",
            invariants,
        )

    def test_focal_subject_must_be_participant_record(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "deliberate-export"
            / "invalid"
            / "focal-subject-nonparticipant.json"
        )
        self.assertTrue(list(self.export_validator.iter_errors(value)))

        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "exports"
            / "deliberate-export.schema.json"
        )
        focal = schema["$defs"]["focalSubjectRef"]
        self.assertEqual(len(focal["oneOf"]), 2)

    def test_explicit_source_set_requires_exact_definition_identity(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "deliberate-export"
            / "invalid"
            / "explicit-source-set-missing-digest.json"
        )
        self.assertTrue(list(self.export_validator.iter_errors(value)))

        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "exports"
            / "deliberate-export.schema.json"
        )
        explicit = schema["$defs"]["exportScope"]["oneOf"][3]
        self.assertEqual(
            explicit["properties"]["scope_algorithm"]["const"],
            "portia_export_scope_set_v1",
        )
        for field in (
            "scope_id",
            "scope_version",
            "scope_algorithm",
            "scope_digest",
        ):
            self.assertIn(field, explicit["required"])

    def test_projection_decision_algorithm_is_required(self) -> None:
        value = load_json(
            FIXTURE_ROOT
            / "deliberate-export"
            / "invalid"
            / "missing-projection-decision-algorithm.json"
        )
        self.assertTrue(list(self.export_validator.iter_errors(value)))

        schema = load_json(
            REPO_ROOT
            / "schemas"
            / "v1"
            / "exports"
            / "deliberate-export.schema.json"
        )
        self.assertIn("projection_decision_algorithm", schema["required"])
        self.assertEqual(
            schema["properties"]["projection_decision_algorithm"]["const"],
            "portia_projection_decision_v1",
        )

    def test_review_findings_are_recorded_in_contract_docs(self) -> None:
        findings = (
            REPO_ROOT
            / "docs"
            / "validation"
            / "issue-21-review-findings.md"
        ).read_text(encoding="utf-8")
        self.assertIn("R1 — High", findings)
        self.assertIn("R2 — High", findings)
        self.assertIn("R3 — Medium-high", findings)
        self.assertIn("R4 — Medium", findings)

        design = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-deliberate-export-and-provenance-contracts.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Post-review reconciliation", design)
        self.assertIn("raw source-artifact locator is not persisted", design)
        self.assertIn("Focal deliberate exports are work-scoped", design)
        self.assertIn("scope_algorithm", design)
        self.assertIn("projection_decision_algorithm", design)


if __name__ == "__main__":
    unittest.main()
