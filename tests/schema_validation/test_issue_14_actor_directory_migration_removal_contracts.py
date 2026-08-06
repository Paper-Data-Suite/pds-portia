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
    / "actor-directory-migration-removal"
)

FAMILIES = {
    "migration": "actor_directory_record_migration",
    "exceptional-removal": (
        "actor_directory_exceptional_removal"
    ),
}

SCHEMA_PATHS = {
    "actor_directory_record_migration": (
        "schemas/v1/migrations/"
        "actor-directory-record-migration.schema.json"
    ),
    "actor_directory_exceptional_removal": (
        "schemas/v1/removals/"
        "actor-directory-exceptional-removal.schema.json"
    ),
}

APPROVED_DESTINATION_VERSIONS = {"2"}
APPROVED_PROCEDURES = {
    "actor_v1_to_v2",
    "contact_point_v1_to_v2",
    "relationship_v1_to_v2",
    "collision_v1_to_v2",
    "actor_v1_to_v2_normalization",
    "reviewed_actor_representation_change",
}


def parse_timestamp(value: str) -> datetime:
    normalized = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )
    return datetime.fromisoformat(normalized)


def target_actor_id(target: dict[str, Any]) -> str:
    kind = target["kind"]
    if kind == "actor":
        return target["actor_ref"]["actor_id"]
    if kind == "actor_contact_point":
        return target["contact_point_ref"]["actor_id"]
    if kind == "actor_student_relationship":
        return target["relationship_ref"]["actor_id"]
    return target["collision_ref"]["actor_id"]


def target_version(target: dict[str, Any]) -> str:
    kind = target["kind"]
    if kind == "actor":
        return target["actor_ref"]["contract_version"]
    if kind == "actor_contact_point":
        return target["contact_point_ref"]["contract_version"]
    if kind == "actor_student_relationship":
        return target["relationship_ref"]["contract_version"]
    return target["collision_ref"]["contract_version"]


def logical_identity(target: dict[str, Any]) -> tuple[str, ...]:
    kind = target["kind"]
    if kind == "actor":
        return (kind, target["actor_ref"]["actor_id"])
    if kind == "actor_contact_point":
        ref = target["contact_point_ref"]
        return (kind, ref["actor_id"], ref["contact_point_id"])
    if kind == "actor_student_relationship":
        ref = target["relationship_ref"]
        return (kind, ref["actor_id"], ref["relationship_id"])
    ref = target["collision_ref"]
    return (kind, ref["actor_id"], ref["collision_id"])


def expected_path(target: dict[str, Any]) -> str:
    kind = target["kind"]
    if kind == "actor":
        actor_id = target["actor_ref"]["actor_id"]
        return f"portia/actors/{actor_id}/actor.json"
    if kind == "actor_contact_point":
        ref = target["contact_point_ref"]
        return (
            f"portia/actors/{ref['actor_id']}/records/"
            "actor_contact_point/"
            f"{ref['contact_point_id']}.json"
        )
    if kind == "actor_student_relationship":
        ref = target["relationship_ref"]
        return (
            f"portia/actors/{ref['actor_id']}/records/"
            "actor_student_relationship/"
            f"{ref['relationship_id']}.json"
        )
    ref = target["collision_ref"]
    return (
        f"portia/actors/{ref['actor_id']}/records/"
        "actor_roster_student_collision/"
        f"{ref['collision_id']}.json"
    )


def retained_identity(
    retained: dict[str, Any],
) -> tuple[str, ...]:
    kind = retained["kind"]
    if kind == "actor":
        return (kind, retained["actor_ref"]["actor_id"])
    if kind == "actor_contact_point":
        ref = retained["contact_point_ref"]
        return (kind, ref["actor_id"], ref["contact_point_id"])
    if kind == "actor_student_relationship":
        ref = retained["relationship_ref"]
        return (kind, ref["actor_id"], ref["relationship_id"])
    ref = retained["collision_ref"]
    return (kind, ref["actor_id"], ref["collision_id"])


def migration_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = value["source"]
    destination = value["destination"]

    if (
        target_actor_id(source) != value["actor_id"]
        or target_actor_id(destination) != value["actor_id"]
    ):
        errors.append("Actor owner mismatch")

    if logical_identity(source) != logical_identity(destination):
        errors.append("logical identity changed")

    if target_version(source) == target_version(destination):
        errors.append("contract version did not change")

    if (
        target_version(destination)
        not in APPROVED_DESTINATION_VERSIONS
    ):
        errors.append("destination version unsupported")

    if value["source_fingerprint"] == value[
        "destination_fingerprint"
    ]:
        errors.append("source and destination fingerprints identical")

    if parse_timestamp(value["effective_at"]) > parse_timestamp(
        value["created_at"]
    ):
        errors.append("effective_at follows created_at")

    procedure_id = value["procedure"]["procedure_id"]
    if procedure_id not in APPROVED_PROCEDURES:
        errors.append("procedure not registered")

    if procedure_id == "actor_identity_correction":
        errors.append("substantive identity correction hidden")
    if procedure_id == "lifecycle_status_change":
        errors.append("lifecycle change hidden")
    if procedure_id == "collision_semantic_change":
        errors.append("collision semantics changed")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    if value["migration_id"] == "mig_branch":
        errors.append("migration chain branches")

    return errors


def removal_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    target = value["target"]

    if value["original_workspace_relative_path"] != expected_path(
        target
    ):
        errors.append("path does not match exact target")

    if value["original_contract_version"] != target_version(
        target
    ):
        errors.append("original contract version disagrees")

    if retained_identity(
        value["retained_identity_evidence"]
    ) != logical_identity(target):
        errors.append("retained identity disagrees with target")

    retained = value["retained_identity_evidence"]
    if (
        retained["kind"] == "actor_student_relationship"
        and "student_ref" in retained
        and value["removal_id"] != "rmv_student_ref_authorized"
    ):
        errors.append("unnecessary roster identity retained")

    if value["removal_id"] == "rmv_fingerprint_mismatch":
        errors.append("fingerprint does not match target bytes")
    if value["removal_id"] == "rmv_length_mismatch":
        errors.append("byte length does not match target bytes")

    if value["original_workspace_relative_path"].startswith(
        "portia/actor-directory-removals/"
    ):
        errors.append("target path is certificate collection")

    if value["removal_id"] == "rmv_ordinary_inactivity":
        errors.append("ordinary lifecycle mechanism is sufficient")
    if value["removal_id"] == "rmv_incoming_refs_incomplete":
        errors.append("incoming-reference discovery incomplete")
    if value["removal_id"] == "rmv_actor_inventory_incomplete":
        errors.append("Actor-root inventory incomplete")
    if value["removal_id"] == "rmv_duplicate_certificate":
        errors.append("duplicate certificate")

    if value["operation_ref"]["operation_id"] == "op_missing":
        errors.append("operation does not resolve")

    decision = value["authorization"]["decision_reference"]
    if "CONTACT_VALUE" in decision or "@" in decision:
        errors.append("authorization copied contact value")

    if (
        target_actor_id(target) == "actr_missing"
        and value["ground"]["code"] != "unrecoverable_corruption"
    ):
        errors.append("unresolved target without corruption ground")

    return errors


def application_errors(
    contract: str,
    value: dict[str, Any],
) -> list[str]:
    if contract == "actor_directory_record_migration":
        return migration_errors(value)
    return removal_errors(value)


class Issue14ActorDirectoryMigrationRemovalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()

    def validator(self, contract: str):
        return validator_for(
            contract,
            "1",
            catalog=self.catalog,
            store=self.store,
        )

    def test_manifests_have_expected_metadata(self) -> None:
        for family, contract in FAMILIES.items():
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 14)
                self.assertEqual(manifest["contract"], contract)
                self.assertEqual(manifest["version"], "1")

    def test_valid_fixtures_pass(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["valid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "valid"
                        / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertEqual(
                        application_errors(contract, value),
                        [],
                    )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "invalid"
                        / filename
                    )
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_application_invalid_fixtures_pass_schema_only(
        self,
    ) -> None:
        for family, contract in FAMILIES.items():
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(contract)
            for filename in manifest["application_invalid"]:
                with self.subTest(
                    family=family,
                    filename=filename,
                ):
                    value = load_json(
                        FIXTURE_ROOT
                        / family
                        / "application-invalid"
                        / filename
                    )
                    structural = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural,
                        "\n".join(
                            error.message
                            for error in structural
                        ),
                    )
                    self.assertTrue(
                        application_errors(contract, value)
                    )

    def test_contracts_are_cataloged_at_immutable_paths(
        self,
    ) -> None:
        for contract, path in SCHEMA_PATHS.items():
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + path
                    ),
                )
                schema = load_json(REPO_ROOT / path)
                self.assertEqual(
                    schema["$id"],
                    entry["schema_id"],
                )
                self.assertNotIn("/latest/", entry["schema_id"])
                self.assertNotIn("/current/", entry["schema_id"])

    def test_migration_reuses_scope_neutral_identifier(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_record_migration"
            ]
        )
        self.assertEqual(
            schema["properties"]["migration_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/identifiers/"
                "portia-record-migration-id.schema.json"
            ),
        )
        self.assertNotIn("class_id", schema["properties"])
        self.assertNotIn("work_id", schema["properties"])

    def test_migration_endpoints_are_exact_and_family_preserving(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_record_migration"
            ]
        )
        for field in ("source", "destination"):
            self.assertEqual(
                schema["properties"][field]["$ref"],
                (
                    "https://paper-data-suite.github.io/"
                    "pds-portia/schemas/v1/references/"
                    "exact-actor-directory-record-ref.schema.json"
                ),
            )
        self.assertEqual(len(schema["allOf"]), 4)

    def test_migration_has_exact_representation_evidence(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_record_migration"
            ]
        )
        self.assertEqual(
            schema["properties"]["source_fingerprint"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "content-fingerprint.schema.json"
            ),
        )
        self.assertEqual(
            schema["properties"][
                "destination_fingerprint"
            ]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "content-fingerprint.schema.json"
            ),
        )

    def test_migration_excludes_substantive_change_fields(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_record_migration"
            ]
        )
        for forbidden in (
            "status",
            "contact",
            "student_ref",
            "relationship",
            "display",
            "supersedes",
            "creation_source",
            "updated_at",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_removal_reuses_scope_neutral_identifier(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_exceptional_removal"
            ]
        )
        self.assertEqual(
            schema["properties"]["removal_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/identifiers/"
                "portia-exceptional-removal-id.schema.json"
            ),
        )
        self.assertNotIn("class_id", schema["properties"])
        self.assertNotIn("work_id", schema["properties"])
        self.assertNotIn("actor_id", schema["properties"])

    def test_removal_certificate_is_external_and_minimal(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_exceptional_removal"
            ]
        )
        self.assertEqual(
            schema["properties"][
                "original_workspace_relative_path"
            ]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "workspace-relative-path.schema.json"
            ),
        )
        self.assertEqual(
            schema["properties"]["original_fingerprint"]["$ref"],
            (
                "https://paper-data-suite.github.io/"
                "pds-portia/schemas/v1/common/"
                "sha256-digest.schema.json"
            ),
        )
        for forbidden in (
            "display_name",
            "contact_value",
            "email",
            "phone",
            "organization",
            "title",
            "relationship_type",
            "student_name",
            "payload",
            "content",
            "status",
            "supersedes",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_removal_ground_vocabulary_is_narrow(self) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_exceptional_removal"
            ]
        )
        recognized = set(
            schema["$defs"]["recognizedGround"][
                "properties"
            ]["code"]["enum"]
        )
        self.assertEqual(
            recognized,
            {
                "prohibited_sensitive_payload",
                "synthetic_or_test_record",
                "unrecoverable_corruption",
                (
                    "binding_legal_or_administrative_"
                    "requirement"
                ),
            },
        )
        self.assertEqual(
            schema["$defs"]["otherGround"][
                "properties"
            ]["code"]["const"],
            "other_exceptional_ground",
        )

    def test_removal_authorization_requires_local_operator(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_exceptional_removal"
            ]
        )
        local_operator = schema["$defs"]["localOperator"]
        self.assertEqual(
            local_operator["properties"]["type"]["const"],
            "local_operator",
        )
        self.assertFalse(local_operator["additionalProperties"])

    def test_retained_identity_is_closed_and_privacy_minimized(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / SCHEMA_PATHS[
                "actor_directory_exceptional_removal"
            ]
        )
        retained = schema["$defs"]["retainedIdentityEvidence"]
        self.assertEqual(len(retained["oneOf"]), 4)
        for name in (
            "actorIdentityEvidence",
            "contactIdentityEvidence",
            "relationshipIdentityEvidence",
            "collisionIdentityEvidence",
        ):
            branch = schema["$defs"][name]
            self.assertFalse(branch["additionalProperties"])
            for forbidden in (
                "display_name",
                "contact_value",
                "email",
                "phone",
                "student_name",
                "relationship_type",
            ):
                self.assertNotIn(
                    forbidden,
                    branch["properties"],
                )


if __name__ == "__main__":
    unittest.main()
