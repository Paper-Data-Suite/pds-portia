from __future__ import annotations

from datetime import datetime
from typing import Any
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
    / "issue-14"
    / "actor-roster-student-collision"
)

SCHEMA_PATH = (
    "schemas/v1/actors/"
    "actor-roster-student-collision.schema.json"
)

SUPPORTED_ACTOR_VERSIONS = {"1"}
SUPPORTED_TRANSITION_VERSIONS = {"1"}


def parse_timestamp(value: str) -> datetime:
    normalized = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )
    return datetime.fromisoformat(normalized)


def application_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if value["actor_ref"]["actor_id"] != value["actor_id"]:
        errors.append("Actor owner and exact Actor reference disagree")

    if (
        value["actor_ref"]["contract_version"]
        not in SUPPORTED_ACTOR_VERSIONS
    ):
        errors.append("unsupported Actor contract version")

    if (
        value["student_ref"]["class_id"] == "missing_class"
        or value["student_ref"]["student_id"] == "missing_student"
    ):
        errors.append("roster student does not resolve")

    if parse_timestamp(value["reviewed_at"]) > parse_timestamp(
        value["created_at"]
    ):
        errors.append("record created before review completed")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    transition = value["actor_invalidation_transition_ref"]
    if transition["actor_id"] != value["actor_id"]:
        errors.append("transition Actor does not match collision Actor")

    if (
        transition["contract_version"]
        not in SUPPORTED_TRANSITION_VERSIONS
    ):
        errors.append("unsupported transition contract version")

    if transition["transition_id"] == "lct_missing":
        errors.append("transition does not resolve")

    if value["collision_id"] == "arsc_duplicate_tuple":
        errors.append("duplicate collision tuple")

    if value["collision_id"] == "arsc_cross_roster_overclaim":
        errors.append("unreviewed cross-roster identity inference")

    return errors


class Issue14ActorRosterStudentCollisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "actor_roster_student_collision",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(
            FIXTURE_ROOT / "manifest.json"
        )

    def test_manifest_has_expected_metadata(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 14)
        self.assertEqual(
            self.manifest["contract"],
            "actor_roster_student_collision",
        )
        self.assertEqual(self.manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "valid" / filename
                )
                structural_errors = list(
                    self.validator.iter_errors(value)
                )
                self.assertFalse(
                    structural_errors,
                    "\n".join(
                        error.message
                        for error in structural_errors
                    ),
                )
                self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "invalid" / filename
                )
                self.assertTrue(
                    list(self.validator.iter_errors(value))
                )

    def test_application_invalid_fixtures_pass_schema_only(
        self,
    ) -> None:
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT
                    / "application-invalid"
                    / filename
                )
                structural_errors = list(
                    self.validator.iter_errors(value)
                )
                self.assertFalse(
                    structural_errors,
                    "\n".join(
                        error.message
                        for error in structural_errors
                    ),
                )
                self.assertTrue(application_errors(value))

    def test_contract_is_cataloged_at_immutable_path(self) -> None:
        entry = self.catalog["contracts"][
            "actor_roster_student_collision"
        ]["1"]
        self.assertEqual(entry["path"], SCHEMA_PATH)
        self.assertEqual(
            entry["schema_id"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/"
                + SCHEMA_PATH
            ),
        )
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertNotIn("/latest/", entry["schema_id"])
        self.assertNotIn("/current/", entry["schema_id"])

    def test_envelope_is_closed_and_immutable(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "actor_id",
                "collision_id",
                "actor_ref",
                "student_ref",
                "resolution",
                "evidence",
                "reviewed_at",
                "reviewed_by",
                "operation_ref",
                "actor_invalidation_transition_ref",
                "created_at",
                "created_by",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("updated_at", schema["properties"])
        self.assertNotIn("updated_by", schema["properties"])
        self.assertNotIn("status", schema["properties"])
        self.assertNotIn("supersedes", schema["properties"])

    def test_resolution_is_confirmed_same_person_only(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            schema["properties"]["resolution"]["const"],
            "confirmed_same_person",
        )

    def test_student_target_is_exact_and_class_qualified(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            schema["properties"]["student_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/"
                "roster-student-ref.schema.json"
            ),
        )
        roster_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/"
            "roster-student-ref.schema.json"
        )
        self.assertEqual(
            set(roster_ref["required"]),
            {"class_id", "student_id"},
        )
        self.assertFalse(roster_ref["additionalProperties"])

    def test_evidence_union_is_bounded_and_privacy_safe(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        evidence = schema["properties"]["evidence"]
        self.assertEqual(evidence["minItems"], 1)
        self.assertEqual(evidence["maxItems"], 20)
        self.assertTrue(evidence["uniqueItems"])
        self.assertEqual(
            len(schema["$defs"]["evidenceItem"]["oneOf"]),
            6,
        )
        for definition in (
            "localOperatorKnowledgeEvidence",
            "actorStatementEvidence",
            "rosterStudentStatementEvidence",
            "schoolRecordEvidence",
            "importIdentityEvidence",
            "otherEvidence",
        ):
            self.assertFalse(
                schema["$defs"][definition]["additionalProperties"]
            )
        schema_text = str(schema["properties"]["evidence"])
        self.assertNotIn("contact_value", schema_text)
        self.assertNotIn("display_name", schema_text)

    def test_transition_link_is_exact_and_actor_owned(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        transition_ref = schema["$defs"][
            "actorInvalidationTransitionRef"
        ]
        self.assertEqual(
            set(transition_ref["required"]),
            {"actor_id", "transition_id", "contract_version"},
        )
        self.assertFalse(transition_ref["additionalProperties"])
        self.assertEqual(
            transition_ref["properties"]["transition_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/identifiers/"
                "portia-lifecycle-transition-id.schema.json"
            ),
        )

    def test_operation_reference_remains_identity_only(self) -> None:
        operation_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/"
            "operation-ref.schema.json"
        )
        self.assertEqual(
            set(operation_ref["required"]),
            {"operation_id"},
        )
        self.assertFalse(operation_ref["additionalProperties"])

    def test_schema_rejects_workspace_person_authority(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        for forbidden in (
            "workspace_person_id",
            "student_name",
            "actor_display_name",
            "contact_value",
            "cross_roster_identity",
            "successor_actor_id",
        ):
            self.assertNotIn(forbidden, schema["properties"])
        description = schema["description"]
        self.assertIn("workspace-wide student identity", description)
        self.assertIn("cross-roster equivalence", description)
        self.assertIn("general person registry", description)

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        expected = {
            "portia.actor_roster_collision.canonical_storage_scope",
            "portia.actor_roster_collision.owner_agreement",
            (
                "portia.actor_roster_collision."
                "actor_ref_owner_agreement"
            ),
            "portia.actor_roster_collision.actor_resolution",
            (
                "portia.actor_roster_collision."
                "actor_contract_supported"
            ),
            "portia.actor_roster_collision.student_resolution",
            (
                "portia.actor_roster_collision."
                "exact_class_qualified_scope"
            ),
            (
                "portia.actor_roster_collision."
                "no_cross_roster_inference"
            ),
            (
                "portia.actor_roster_collision."
                "authorized_human_review"
            ),
            (
                "portia.actor_roster_collision."
                "evidence_sufficiency"
            ),
            (
                "portia.actor_roster_collision."
                "review_creation_chronology"
            ),
            "portia.actor_roster_collision.tuple_uniqueness",
            "portia.actor_roster_collision.operation_resolution",
            "portia.actor_roster_collision.operation_intent",
            "portia.actor_roster_collision.transition_resolution",
            (
                "portia.actor_roster_collision."
                "transition_contract_supported"
            ),
            (
                "portia.actor_roster_collision."
                "transition_actor_agreement"
            ),
            (
                "portia.actor_roster_collision."
                "transition_target_actor"
            ),
            (
                "portia.actor_roster_collision."
                "transition_prior_status"
            ),
            (
                "portia.actor_roster_collision."
                "transition_new_status_invalidated"
            ),
            (
                "portia.actor_roster_collision."
                "transition_reason_roster_student_collision"
            ),
            (
                "portia.actor_roster_collision."
                "coordinated_persistence"
            ),
            (
                "portia.actor_roster_collision."
                "incoming_reference_complete"
            ),
            (
                "portia.actor_roster_collision."
                "child_review_complete"
            ),
            (
                "portia.actor_roster_collision."
                "contact_nonconversion"
            ),
            (
                "portia.actor_roster_collision."
                "historical_reference_stability"
            ),
            (
                "portia.actor_roster_collision."
                "privacy_safe_payload"
            ),
            (
                "portia.actor_roster_collision."
                "no_workspace_person_identity"
            ),
        }
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
