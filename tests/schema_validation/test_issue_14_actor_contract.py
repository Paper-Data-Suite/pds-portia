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
    / "actor"
)

ACTOR_SCHEMA_PATH = "schemas/v1/actors/actor.schema.json"

SUPPORTED_ACTOR_CONTRACT_VERSIONS = {"1"}


def parse_timestamp(value: str) -> datetime:
    normalized = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )
    return datetime.fromisoformat(normalized)


def application_errors(actor: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if parse_timestamp(actor["updated_at"]) < parse_timestamp(
        actor["created_at"]
    ):
        errors.append("updated_at precedes created_at")

    creation_source = actor["creation_source"]
    if (
        creation_source["type"] == "import"
        and actor["status"] != "proposed"
    ):
        errors.append(
            "imported current status requires accepted review history"
        )

    supersedes = actor.get("supersedes", [])
    if not supersedes:
        return errors

    current_actor_id = actor["actor_id"]
    predecessor_ids: list[str] = []
    reasons: list[str] = []

    for entry in supersedes:
        predecessor = entry["actor_ref"]
        predecessor_id = predecessor["actor_id"]
        predecessor_ids.append(predecessor_id)
        reasons.append(entry["reason"])

        if (
            predecessor_id == current_actor_id
            and entry["reason"] != "contract_migrated"
        ):
            errors.append("Actor replacement self-reference")

        if (
            predecessor["contract_version"]
            not in SUPPORTED_ACTOR_CONTRACT_VERSIONS
        ):
            errors.append("unsupported predecessor contract version")

    if len(predecessor_ids) != len(set(predecessor_ids)):
        errors.append("predecessor Actor identity repeated")

    reason_set = set(reasons)
    if len(reason_set) > 1:
        errors.append("mixed supersession reasons")

    if reason_set == {"duplicate_consolidated"}:
        if len(set(predecessor_ids)) < 2:
            errors.append(
                "duplicate consolidation needs two predecessors"
            )

    if reason_set == {"identity_corrected"}:
        if len(set(predecessor_ids)) != 1:
            errors.append(
                "identity correction must be one-to-one"
            )

    if reason_set == {"conflated_person_split"}:
        if len(set(predecessor_ids)) != 1:
            errors.append(
                "each split successor has one direct predecessor"
            )

    return errors


class Issue14ActorRootContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "actor",
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
        self.assertEqual(self.manifest["contract"], "actor")
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
        entry = self.catalog["contracts"]["actor"]["1"]
        self.assertEqual(entry["path"], ACTOR_SCHEMA_PATH)
        self.assertEqual(
            entry["schema_id"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/"
                + ACTOR_SCHEMA_PATH
            ),
        )
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        self.assertEqual(schema["$id"], entry["schema_id"])
        self.assertNotIn("/latest/", entry["schema_id"])
        self.assertNotIn("/current/", entry["schema_id"])

    def test_actor_envelope_is_closed_and_workspace_scoped(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version",
                "record_type",
                "module_id",
                "actor_id",
                "status",
                "display",
                "actor_category",
                "creation_source",
                "created_at",
                "created_by",
                "updated_at",
                "updated_by",
            },
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            schema["properties"]["schema_version"]["const"],
            "1",
        )
        self.assertEqual(
            schema["properties"]["record_type"]["const"],
            "actor",
        )
        self.assertEqual(
            schema["properties"]["module_id"]["const"],
            "portia",
        )
        for forbidden in (
            "class_id",
            "work_id",
            "school_year",
            "workspace_id",
            "student_id",
            "student_ids",
            "contact_points",
            "roles",
            "notes",
            "metadata",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_status_vocabulary_is_closed(self) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {
                "proposed",
                "active",
                "inactive",
                "invalidated",
                "superseded",
            },
        )

    def test_display_is_bounded_and_not_identity(self) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        display = schema["$defs"]["display"]
        self.assertEqual(
            set(display["required"]),
            {"display_name"},
        )
        self.assertFalse(display["additionalProperties"])
        self.assertEqual(
            set(display["properties"]),
            {"display_name", "organization", "title"},
        )
        for forbidden in (
            "actor_id",
            "email",
            "phone",
            "address",
            "student_id",
            "authority",
        ):
            self.assertNotIn(forbidden, display["properties"])

    def test_actor_category_separates_broad_kind_from_detail(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        standard = schema["$defs"]["standardActorCategory"]
        other = schema["$defs"]["otherActorCategory"]
        self.assertEqual(
            set(standard["properties"]["kind"]["enum"]),
            {
                "family_or_caregiver",
                "school_staff",
                "external_support_provider",
                "community_collaborator",
            },
        )
        self.assertFalse(standard["additionalProperties"])
        self.assertEqual(
            set(other["required"]),
            {"kind", "detail"},
        )
        self.assertEqual(
            other["properties"]["kind"]["const"],
            "other",
        )
        self.assertFalse(other["additionalProperties"])

    def test_paper_capture_cannot_create_actor_v1(self) -> None:
        value = load_json(
            FIXTURE_ROOT / "invalid" / "paper-capture-source.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_supersession_uses_exact_actor_references(
        self,
    ) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        entry = schema["$defs"]["supersessionEntry"]
        self.assertEqual(
            entry["properties"]["actor_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/exact-actor-ref.schema.json"
            ),
        )
        self.assertEqual(
            set(entry["properties"]["reason"]["enum"]),
            {
                "identity_corrected",
                "duplicate_consolidated",
                "conflated_person_split",
                "contract_migrated",
                "other",
            },
        )
        self.assertFalse(entry["additionalProperties"])

    def test_identity_only_actor_ref_remains_unchanged(self) -> None:
        actor_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/actor-ref.schema.json"
        )
        exact_actor_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/exact-actor-ref.schema.json"
        )
        actor = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        self.assertEqual(
            actor_ref["properties"]["actor_id"],
            exact_actor_ref["properties"]["actor_id"],
        )
        self.assertEqual(
            actor["properties"]["actor_id"],
            actor_ref["properties"]["actor_id"],
        )
        self.assertEqual(set(actor_ref["required"]), {"actor_id"})
        self.assertFalse(actor_ref["additionalProperties"])

    def test_application_invariant_inventory_is_explicit(self) -> None:
        schema = load_json(REPO_ROOT / ACTOR_SCHEMA_PATH)
        self.assertEqual(
            set(schema["x-portia-application-invariants"]),
            {
                "portia.actor.canonical_storage_scope",
                "portia.actor.path_identity_agreement",
                "portia.actor.one_human_person",
                "portia.actor.roster_student_prohibition",
                "portia.actor.timestamp_chronology",
                "portia.actor.creation_provenance_immutable",
                (
                    "portia.actor."
                    "imported_status_requires_review_history"
                ),
                "portia.actor.lifecycle_history_reconciliation",
                "portia.actor.current_use_eligibility",
                "portia.actor.predecessor_resolution",
                "portia.actor.predecessor_contract_supported",
                "portia.actor.self_supersession",
                "portia.actor.predecessor_identity_unique",
                "portia.actor.supersession_reason_uniform",
                "portia.actor.replacement_topology",
                "portia.actor.supersession_cycle",
                "portia.actor.successor_effectiveness",
                "portia.actor.incoming_reference_complete",
                "portia.actor.no_silent_successor_following",
            },
        )


if __name__ == "__main__":
    unittest.main()
