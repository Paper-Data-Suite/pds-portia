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
    / "actor-contact-point"
)

SCHEMA_PATH = (
    "schemas/v1/actors/actor-contact-point.schema.json"
)

SUPPORTED_CONTACT_POINT_VERSIONS = {"1"}


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

    verification = value["verification"]
    if verification["kind"] == "locally_confirmed":
        verified_at = parse_timestamp(verification["verified_at"])
        if verified_at < created_at:
            errors.append("verification predates creation")
        if verified_at > updated_at:
            errors.append("verification postdates current update")

    if (
        value["creation_source"]["type"] == "import"
        and value["status"] != "proposed"
    ):
        errors.append(
            "imported current status requires accepted review history"
        )

    supersedes = value.get("supersedes", [])
    if not supersedes:
        return errors

    current_identity = (
        value["actor_id"],
        value["contact_point_id"],
    )
    predecessor_identities: list[tuple[str, str]] = []
    reasons: list[str] = []

    for entry in supersedes:
        predecessor = entry["contact_point_ref"]
        identity = (
            predecessor["actor_id"],
            predecessor["contact_point_id"],
        )
        predecessor_identities.append(identity)
        reasons.append(entry["reason"])

        if (
            identity == current_identity
            and entry["reason"] != "contract_migrated"
        ):
            errors.append("Contact Point replacement self-reference")

        if (
            predecessor["contract_version"]
            not in SUPPORTED_CONTACT_POINT_VERSIONS
        ):
            errors.append("unsupported predecessor contract version")

    if len(predecessor_identities) != len(
        set(predecessor_identities)
    ):
        errors.append("predecessor Contact Point identity repeated")

    reason_set = set(reasons)
    if len(reason_set) > 1:
        errors.append("mixed supersession reasons")

    if reason_set == {"duplicate_consolidated"}:
        if len(set(predecessor_identities)) < 2:
            errors.append(
                "duplicate consolidation needs two predecessors"
            )

    if reason_set == {"contact_corrected"}:
        if len(set(predecessor_identities)) != 1:
            errors.append(
                "contact correction must be one-to-one"
            )
        elif predecessor_identities[0][0] != value["actor_id"]:
            errors.append(
                "contact correction cannot change Actor owner"
            )

    if reason_set == {"wrong_actor_corrected"}:
        if len(set(predecessor_identities)) != 1:
            errors.append(
                "Actor ownership correction must be one-to-one"
            )
        elif predecessor_identities[0][0] == value["actor_id"]:
            errors.append(
                "wrong_actor_corrected requires different Actor owners"
            )

    return errors


class Issue14ActorContactPointContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "actor_contact_point",
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
            "actor_contact_point",
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
            "actor_contact_point"
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
                "contact_point_id",
                "status",
                "contact",
                "use_preference",
                "source",
                "verification",
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
            "actor_contact_point",
        )
        for forbidden in (
            "class_id",
            "work_id",
            "student_id",
            "display_name",
            "consent",
            "authorization",
            "notes",
            "metadata",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_contact_union_is_email_or_phone_only(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        contact = schema["$defs"]["contact"]
        self.assertEqual(len(contact["oneOf"]), 2)
        self.assertEqual(
            schema["$defs"]["emailContact"]["properties"][
                "kind"
            ]["const"],
            "email",
        )
        self.assertEqual(
            schema["$defs"]["phoneContact"]["properties"][
                "kind"
            ]["const"],
            "phone",
        )
        self.assertFalse(
            schema["$defs"]["emailContact"][
                "additionalProperties"
            ]
        )
        self.assertFalse(
            schema["$defs"]["phoneContact"][
                "additionalProperties"
            ]
        )

    def test_use_preference_does_not_claim_authorization(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(
                schema["properties"]["use_preference"]["enum"]
            ),
            {"preferred", "alternate", "unspecified"},
        )
        description = schema["properties"][
            "use_preference"
        ]["description"]
        self.assertIn("not communication consent", description)
        self.assertIn("authorization", description)

    def test_source_vocabulary_is_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        source_defs = {
            ref["$ref"].rsplit("/", 1)[-1]
            for ref in schema["$defs"]["source"]["oneOf"]
        }
        self.assertEqual(
            source_defs,
            {
                "localOperatorKnowledgeSource",
                "actorStatementSource",
                "rosterStudentStatementSource",
                "schoolRecordSource",
                "importSource",
                "otherSource",
            },
        )

    def test_verification_is_local_and_noninstitutional(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        locally_confirmed = schema["$defs"]["locallyConfirmed"]
        self.assertEqual(
            set(locally_confirmed["required"]),
            {"kind", "verified_at", "verified_by"},
        )
        description = locally_confirmed["description"]
        self.assertIn("does not establish institutional", description)
        self.assertIn("exclusive control", description)
        self.assertIn("consent", description)

    def test_paper_capture_cannot_create_contact_point_v1(
        self,
    ) -> None:
        value = load_json(
            FIXTURE_ROOT / "invalid" / "paper-capture-source.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_supersession_uses_exact_contact_references(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        entry = schema["$defs"]["supersessionEntry"]
        self.assertEqual(
            entry["properties"]["contact_point_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/"
                "exact-actor-contact-point-ref.schema.json"
            ),
        )
        self.assertEqual(
            set(entry["properties"]["reason"]["enum"]),
            {
                "contact_corrected",
                "duplicate_consolidated",
                "wrong_actor_corrected",
                "contract_migrated",
                "other",
            },
        )

    def test_contact_values_are_not_reference_identity(self) -> None:
        exact_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/"
            "exact-actor-contact-point-ref.schema.json"
        )
        self.assertEqual(
            set(exact_ref["required"]),
            {"actor_id", "contact_point_id", "contract_version"},
        )
        for forbidden in (
            "contact",
            "address",
            "number",
            "label",
            "source",
            "verification",
            "use_preference",
        ):
            self.assertNotIn(
                forbidden,
                exact_ref["properties"],
            )

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        expected = {
            "portia.actor_contact_point.canonical_storage_scope",
            "portia.actor_contact_point.owner_agreement",
            "portia.actor_contact_point.actor_resolution",
            (
                "portia.actor_contact_point."
                "actor_lifecycle_eligibility"
            ),
            "portia.actor_contact_point.timestamp_chronology",
            "portia.actor_contact_point.verification_chronology",
            "portia.actor_contact_point.contact_syntax",
            "portia.actor_contact_point.contact_normalization",
            (
                "portia.actor_contact_point."
                "active_assertion_uniqueness"
            ),
            (
                "portia.actor_contact_point."
                "preferred_current_uniqueness"
            ),
            (
                "portia.actor_contact_point."
                "creation_provenance_immutable"
            ),
            (
                "portia.actor_contact_point."
                "imported_status_requires_review_history"
            ),
            (
                "portia.actor_contact_point."
                "lifecycle_history_reconciliation"
            ),
            "portia.actor_contact_point.source_semantics",
            (
                "portia.actor_contact_point."
                "purpose_authorization_eligibility"
            ),
            "portia.actor_contact_point.predecessor_resolution",
            (
                "portia.actor_contact_point."
                "predecessor_contract_supported"
            ),
            "portia.actor_contact_point.self_supersession",
            (
                "portia.actor_contact_point."
                "predecessor_identity_unique"
            ),
            (
                "portia.actor_contact_point."
                "supersession_reason_uniform"
            ),
            "portia.actor_contact_point.replacement_topology",
            "portia.actor_contact_point.ownership_correction",
            "portia.actor_contact_point.supersession_cycle",
            "portia.actor_contact_point.successor_effectiveness",
            (
                "portia.actor_contact_point."
                "privacy_sensitive_payload"
            ),
            (
                "portia.actor_contact_point."
                "no_silent_successor_following"
            ),
        }
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
