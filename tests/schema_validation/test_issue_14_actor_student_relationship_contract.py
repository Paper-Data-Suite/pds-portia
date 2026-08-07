from __future__ import annotations

from datetime import date, datetime
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
    / "actor-student-relationship"
)

SCHEMA_PATH = (
    "schemas/v1/actors/actor-student-relationship.schema.json"
)

SUPPORTED_RELATIONSHIP_VERSIONS = {"1"}


def parse_timestamp(value: str) -> datetime:
    normalized = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )
    return datetime.fromisoformat(normalized)


def application_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    created_at = parse_timestamp(value["created_at"])
    updated_at = parse_timestamp(value["updated_at"])

    if updated_at < created_at:
        errors.append("updated_at precedes created_at")

    review = value["review"]
    if review["kind"] == "locally_reviewed":
        reviewed_at = parse_timestamp(review["reviewed_at"])
        if reviewed_at < created_at:
            errors.append("review predates creation")
        if reviewed_at > updated_at:
            errors.append("review postdates current update")

    if value["status"] == "active" and review["kind"] != "locally_reviewed":
        errors.append("active relationship is unreviewed")

    if (
        value["creation_source"]["type"] == "import"
        and value["status"] != "proposed"
    ):
        errors.append(
            "imported current status requires accepted review history"
        )

    period = value.get("effective_period")
    if (
        period is not None
        and "starts_on" in period
        and "ends_on" in period
        and date.fromisoformat(period["ends_on"])
        < date.fromisoformat(period["starts_on"])
    ):
        errors.append("effective period is reversed")

    supersedes = value.get("supersedes", [])
    if not supersedes:
        return errors

    current_identity = (
        value["actor_id"],
        value["relationship_id"],
    )
    predecessor_identities: list[tuple[str, str]] = []
    reasons: list[str] = []

    for entry in supersedes:
        predecessor = entry["relationship_ref"]
        identity = (
            predecessor["actor_id"],
            predecessor["relationship_id"],
        )
        predecessor_identities.append(identity)
        reasons.append(entry["reason"])

        if (
            identity == current_identity
            and entry["reason"] != "contract_migrated"
        ):
            errors.append("Relationship replacement self-reference")

        if (
            predecessor["contract_version"]
            not in SUPPORTED_RELATIONSHIP_VERSIONS
        ):
            errors.append("unsupported predecessor contract version")

    if len(predecessor_identities) != len(
        set(predecessor_identities)
    ):
        errors.append("predecessor Relationship identity repeated")

    reason_set = set(reasons)
    if len(reason_set) > 1:
        errors.append("mixed supersession reasons")

    if reason_set == {"duplicate_consolidated"}:
        if len(set(predecessor_identities)) < 2:
            errors.append(
                "duplicate consolidation needs two predecessors"
            )

    if reason_set in (
        {"relationship_corrected"},
        {"basis_corrected"},
        {"wrong_actor_corrected"},
        {"wrong_student_corrected"},
    ):
        if len(set(predecessor_identities)) != 1:
            errors.append("ordinary correction must be one-to-one")

    if reason_set in (
        {"relationship_corrected"},
        {"basis_corrected"},
    ):
        if (
            len(set(predecessor_identities)) == 1
            and predecessor_identities[0][0] != value["actor_id"]
        ):
            errors.append(
                "ordinary correction cannot change Actor owner"
            )

    if reason_set == {"wrong_actor_corrected"}:
        if (
            len(set(predecessor_identities)) == 1
            and predecessor_identities[0][0] == value["actor_id"]
        ):
            errors.append(
                "wrong_actor_corrected requires a different Actor owner"
            )

    if reason_set == {"wrong_student_corrected"}:
        if (
            len(set(predecessor_identities)) == 1
            and predecessor_identities[0][0] != value["actor_id"]
        ):
            errors.append(
                "wrong_student_corrected cannot also change Actor owner"
            )

    return errors


class Issue14ActorStudentRelationshipContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "actor_student_relationship",
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
            "actor_student_relationship",
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
            "actor_student_relationship"
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

    def test_envelope_is_closed_and_actor_owned(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "actor_id",
                "relationship_id",
                "status",
                "student_ref",
                "relationship",
                "basis",
                "review",
                "creation_source",
                "created_at",
                "created_by",
                "updated_at",
                "updated_by",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["record_type"]["const"],
            "actor_student_relationship",
        )
        for forbidden in (
            "work_id",
            "student_name",
            "household_id",
            "contact",
            "consent",
            "authority",
            "notes",
            "metadata",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_student_target_is_exact_core_roster_reference(
        self,
    ) -> None:
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
            / "schemas/v1/references/roster-student-ref.schema.json"
        )
        self.assertEqual(
            set(roster_ref["required"]),
            {"class_id", "student_id"},
        )
        self.assertFalse(roster_ref["additionalProperties"])

    def test_relationship_vocabulary_is_descriptive_only(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        standard = schema["$defs"]["standardRelationship"]
        self.assertEqual(
            set(standard["properties"]["type"]["enum"]),
            {
                "parent",
                "guardian",
                "caregiver",
                "family_contact",
                "counselor",
                "case_manager",
                "administrator",
                "support_staff",
                "external_support_provider",
            },
        )
        description = schema["description"]
        for term in (
            "guardianship",
            "custody",
            "disclosure permission",
            "consent",
            "decision authority",
        ):
            self.assertIn(term, description)

    def test_basis_vocabulary_is_closed_and_typed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        basis_refs = {
            ref["$ref"].rsplit("/", 1)[-1]
            for ref in schema["$defs"]["basis"]["oneOf"]
        }
        self.assertEqual(
            basis_refs,
            {
                "localOperatorKnowledgeBasis",
                "actorStatementBasis",
                "rosterStudentStatementBasis",
                "schoolRecordBasis",
                "importBasis",
                "otherBasis",
            },
        )
        self.assertEqual(
            schema["$defs"]["actorStatementBasis"][
                "properties"
            ]["source_actor_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/exact-actor-ref.schema.json"
            ),
        )
        self.assertEqual(
            schema["$defs"]["rosterStudentStatementBasis"][
                "properties"
            ]["source_student_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/"
                "roster-student-ref.schema.json"
            ),
        )

    def test_review_is_local_and_nonauthoritative(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        review = schema["$defs"]["locallyReviewed"]
        self.assertEqual(
            set(review["required"]),
            {"kind", "reviewed_at", "reviewed_by"},
        )
        description = review["description"]
        for phrase in (
            "does not establish legal",
            "institutional verification",
            "disclosure permission",
            "consent",
            "custody",
            "decision authority",
        ):
            self.assertIn(phrase, description)

    def test_effective_period_is_optional_and_nonautomatic(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        period = schema["$defs"]["effectivePeriod"]
        self.assertFalse(period["additionalProperties"])
        self.assertEqual(
            set(period["properties"]),
            {"starts_on", "ends_on"},
        )
        self.assertNotIn(
            "effective_period",
            schema["required"],
        )
        self.assertIn(
            "do not automatically change lifecycle",
            schema["properties"]["effective_period"]["description"],
        )

    def test_paper_capture_cannot_create_relationship_v1(
        self,
    ) -> None:
        value = load_json(
            FIXTURE_ROOT / "invalid" / "paper-capture-source.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_supersession_uses_exact_relationship_references(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        entry = schema["$defs"]["supersessionEntry"]
        self.assertEqual(
            entry["properties"]["relationship_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/"
                "exact-actor-student-relationship-ref.schema.json"
            ),
        )
        self.assertEqual(
            set(entry["properties"]["reason"]["enum"]),
            {
                "relationship_corrected",
                "wrong_actor_corrected",
                "wrong_student_corrected",
                "basis_corrected",
                "duplicate_consolidated",
                "contract_migrated",
                "other",
            },
        )

    def test_exact_relationship_reference_excludes_student_payload(
        self,
    ) -> None:
        exact_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/"
            "exact-actor-student-relationship-ref.schema.json"
        )
        self.assertEqual(
            set(exact_ref["required"]),
            {"actor_id", "relationship_id", "contract_version"},
        )
        for forbidden in (
            "student_ref",
            "class_id",
            "student_id",
            "relationship",
            "basis",
            "review",
            "authority",
        ):
            self.assertNotIn(
                forbidden,
                exact_ref["properties"],
            )

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        required_invariants = {
            "portia.actor_student_relationship.canonical_storage_scope",
            "portia.actor_student_relationship.owner_agreement",
            "portia.actor_student_relationship.actor_resolution",
            (
                "portia.actor_student_relationship."
                "actor_lifecycle_eligibility"
            ),
            "portia.actor_student_relationship.student_resolution",
            (
                "portia.actor_student_relationship."
                "historical_student_resolution"
            ),
            (
                "portia.actor_student_relationship."
                "no_cross_roster_inference"
            ),
            "portia.actor_student_relationship.timestamp_chronology",
            "portia.actor_student_relationship.review_chronology",
            (
                "portia.actor_student_relationship."
                "active_requires_review"
            ),
            (
                "portia.actor_student_relationship."
                "effective_period_chronology"
            ),
            (
                "portia.actor_student_relationship."
                "creation_provenance_immutable"
            ),
            (
                "portia.actor_student_relationship."
                "imported_status_requires_review_history"
            ),
            (
                "portia.actor_student_relationship."
                "source_actor_resolution"
            ),
            (
                "portia.actor_student_relationship."
                "source_student_resolution"
            ),
            "portia.actor_student_relationship.basis_semantics",
            (
                "portia.actor_student_relationship."
                "lifecycle_history_reconciliation"
            ),
            (
                "portia.actor_student_relationship."
                "active_tuple_uniqueness"
            ),
            (
                "portia.actor_student_relationship."
                "independent_source_assertion"
            ),
            (
                "portia.actor_student_relationship."
                "material_field_replacement"
            ),
            (
                "portia.actor_student_relationship."
                "predecessor_resolution"
            ),
            (
                "portia.actor_student_relationship."
                "predecessor_contract_supported"
            ),
            "portia.actor_student_relationship.self_supersession",
            (
                "portia.actor_student_relationship."
                "predecessor_identity_unique"
            ),
            (
                "portia.actor_student_relationship."
                "supersession_reason_uniform"
            ),
            (
                "portia.actor_student_relationship."
                "replacement_topology"
            ),
            "portia.actor_student_relationship.actor_correction",
            "portia.actor_student_relationship.student_correction",
            (
                "portia.actor_student_relationship."
                "supersession_cycle"
            ),
            (
                "portia.actor_student_relationship."
                "successor_effectiveness"
            ),
            (
                "portia.actor_student_relationship."
                "authority_limitation"
            ),
            (
                "portia.actor_student_relationship."
                "privacy_safe_diagnostics"
            ),
            (
                "portia.actor_student_relationship."
                "no_silent_successor_following"
            ),
        }
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            required_invariants,
        )


if __name__ == "__main__":
    unittest.main()
