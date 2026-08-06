from __future__ import annotations

from pathlib import Path
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
    / "actor-directory-primitives"
)

FAMILIES = (
    "actor-contact-point-id",
    "actor-student-relationship-id",
    "actor-roster-student-collision-id",
    "exact-actor-ref",
    "exact-actor-contact-point-ref",
    "exact-actor-student-relationship-ref",
    "exact-actor-roster-student-collision-ref",
    "exact-actor-directory-record-ref",
    "actor-target",
)

EXPECTED_CONTRACT_PATHS = {
    "portia_actor_contact_point_id": (
        "schemas/v1/identifiers/"
        "portia-actor-contact-point-id.schema.json"
    ),
    "portia_actor_student_relationship_id": (
        "schemas/v1/identifiers/"
        "portia-actor-student-relationship-id.schema.json"
    ),
    "portia_actor_roster_student_collision_id": (
        "schemas/v1/identifiers/"
        "portia-actor-roster-student-collision-id.schema.json"
    ),
    "exact_actor_ref": (
        "schemas/v1/references/exact-actor-ref.schema.json"
    ),
    "exact_actor_contact_point_ref": (
        "schemas/v1/references/"
        "exact-actor-contact-point-ref.schema.json"
    ),
    "exact_actor_student_relationship_ref": (
        "schemas/v1/references/"
        "exact-actor-student-relationship-ref.schema.json"
    ),
    "exact_actor_roster_student_collision_ref": (
        "schemas/v1/references/"
        "exact-actor-roster-student-collision-ref.schema.json"
    ),
    "exact_actor_directory_record_ref": (
        "schemas/v1/references/"
        "exact-actor-directory-record-ref.schema.json"
    ),
    "actor_target": (
        "schemas/v1/targets/actor-target.schema.json"
    ),
}

IDENTIFIER_CASES = {
    "portia_actor_contact_point_id": {
        "valid": (
            "acp_a",
            "acp_0001",
            "acp_Mixed_Case-9",
        ),
        "invalid": (
            "acp_",
            "contact_a",
            "ACP_a",
            "acp_a.b",
            "acp_a/b",
        ),
    },
    "portia_actor_student_relationship_id": {
        "valid": (
            "asrel_a",
            "asrel_0001",
            "asrel_Mixed_Case-9",
        ),
        "invalid": (
            "asrel_",
            "rel_a",
            "ASREL_a",
            "asrel_a.b",
            "asrel_a/b",
        ),
    },
    "portia_actor_roster_student_collision_id": {
        "valid": (
            "arsc_a",
            "arsc_0001",
            "arsc_Mixed_Case-9",
        ),
        "invalid": (
            "arsc_",
            "collision_a",
            "ARSC_a",
            "arsc_a.b",
            "arsc_a/b",
        ),
    },
}

SUPPORTED_CONTRACT_VERSIONS = {
    "actor": {"1"},
    "actor_contact_point": {"1"},
    "actor_student_relationship": {"1"},
    "actor_roster_student_collision": {"1"},
}


def _find_kind_and_version(
    value: Any,
) -> tuple[str | None, str | None]:
    if not isinstance(value, dict):
        return None, None

    kind = value.get("kind")
    if kind == "actor_directory_record":
        return _find_kind_and_version(value.get("record_ref"))

    reference_fields = {
        "actor": "actor_ref",
        "actor_contact_point": "contact_point_ref",
        "actor_student_relationship": "relationship_ref",
        "actor_roster_student_collision": "collision_ref",
    }
    if kind in reference_fields:
        child = value.get(reference_fields[kind])
        if isinstance(child, dict):
            version = child.get("contract_version")
            return kind, version if isinstance(version, str) else None

    if "contact_point_id" in value:
        return "actor_contact_point", value.get("contract_version")
    if "relationship_id" in value:
        return "actor_student_relationship", value.get("contract_version")
    if "collision_id" in value:
        return (
            "actor_roster_student_collision",
            value.get("contract_version"),
        )
    if "actor_id" in value and "contract_version" in value:
        return "actor", value.get("contract_version")

    return None, None


def application_errors(value: Any) -> list[str]:
    kind, version = _find_kind_and_version(value)
    if kind is None or version is None:
        return []
    if version not in SUPPORTED_CONTRACT_VERSIONS[kind]:
        return [
            "referenced Actor-directory contract version is unsupported"
        ]
    return []


class Issue14ActorDirectoryPrimitiveTests(unittest.TestCase):
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
        for family in FAMILIES:
            with self.subTest(family=family):
                manifest = load_json(
                    FIXTURE_ROOT / family / "manifest.json"
                )
                self.assertEqual(manifest["manifest_version"], "1")
                self.assertEqual(manifest["issue"], 14)
                self.assertEqual(manifest["version"], "1")
                self.assertIn(
                    manifest["contract"],
                    EXPECTED_CONTRACT_PATHS,
                )

    def test_valid_fixtures_pass(self) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(manifest["contract"])
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
                    errors = list(validator.iter_errors(value))
                    self.assertFalse(
                        errors,
                        "\n".join(
                            error.message for error in errors
                        ),
                    )
                    self.assertEqual(application_errors(value), [])

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(manifest["contract"])
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

    def test_application_invalid_fixtures_are_structurally_valid(
        self,
    ) -> None:
        for family in FAMILIES:
            manifest = load_json(
                FIXTURE_ROOT / family / "manifest.json"
            )
            validator = self.validator(manifest["contract"])
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
                    structural_errors = list(
                        validator.iter_errors(value)
                    )
                    self.assertFalse(
                        structural_errors,
                        "\n".join(
                            error.message
                            for error in structural_errors
                        ),
                    )
                    self.assertTrue(application_errors(value))

    def test_contracts_are_cataloged_at_immutable_paths(self) -> None:
        for contract, expected_path in (
            EXPECTED_CONTRACT_PATHS.items()
        ):
            with self.subTest(contract=contract):
                entry = self.catalog["contracts"][contract]["1"]
                self.assertEqual(entry["path"], expected_path)
                self.assertEqual(
                    entry["schema_id"],
                    (
                        "https://paper-data-suite.github.io/"
                        "pds-portia/"
                        + expected_path
                    ),
                )
                schema = load_json(REPO_ROOT / expected_path)
                self.assertEqual(schema["$id"], entry["schema_id"])
                self.assertNotIn("/latest/", entry["schema_id"])
                self.assertNotIn("/current/", entry["schema_id"])

    def test_identifier_prefix_and_case_contracts(self) -> None:
        for contract, cases in IDENTIFIER_CASES.items():
            validator = self.validator(contract)
            for value in cases["valid"]:
                with self.subTest(
                    contract=contract,
                    valid=value,
                ):
                    self.assertFalse(
                        list(validator.iter_errors(value))
                    )
            for value in cases["invalid"]:
                with self.subTest(
                    contract=contract,
                    invalid=value,
                ):
                    self.assertTrue(
                        list(validator.iter_errors(value))
                    )

    def test_exact_actor_reference_preserves_actor_ref_identity(
        self,
    ) -> None:
        actor_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/actor-ref.schema.json"
        )
        exact_actor_ref = load_json(
            REPO_ROOT
            / "schemas/v1/references/exact-actor-ref.schema.json"
        )
        self.assertEqual(
            actor_ref["properties"]["actor_id"],
            exact_actor_ref["properties"]["actor_id"],
        )
        self.assertEqual(
            set(actor_ref["required"]),
            {"actor_id"},
        )
        self.assertEqual(
            set(exact_actor_ref["required"]),
            {"actor_id", "contract_version"},
        )
        for forbidden in (
            "display_name",
            "organization",
            "title",
            "status",
            "path",
            "fingerprint",
            "class_id",
            "work_id",
            "student_id",
        ):
            self.assertNotIn(
                forbidden,
                exact_actor_ref["properties"],
            )

    def test_exact_child_references_include_actor_ownership(
        self,
    ) -> None:
        expected_identifiers = {
            "exact-actor-contact-point-ref.schema.json": (
                "contact_point_id"
            ),
            "exact-actor-student-relationship-ref.schema.json": (
                "relationship_id"
            ),
            "exact-actor-roster-student-collision-ref.schema.json": (
                "collision_id"
            ),
        }
        for filename, child_id in expected_identifiers.items():
            with self.subTest(filename=filename):
                schema = load_json(
                    REPO_ROOT
                    / "schemas/v1/references"
                    / filename
                )
                self.assertEqual(
                    set(schema["required"]),
                    {
                        "actor_id",
                        child_id,
                        "contract_version",
                    },
                )
                self.assertFalse(schema["additionalProperties"])
                for forbidden in (
                    "class_id",
                    "work_id",
                    "student_id",
                    "display_name",
                    "contact_value",
                    "path",
                    "fingerprint",
                ):
                    self.assertNotIn(
                        forbidden,
                        schema["properties"],
                    )

    def test_directory_record_union_is_closed_and_discriminated(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/references/"
            "exact-actor-directory-record-ref.schema.json"
        )
        self.assertEqual(
            len(schema["oneOf"]),
            4,
        )
        kinds = {
            branch["properties"]["kind"]["const"]
            for branch in schema["$defs"].values()
        }
        self.assertEqual(
            kinds,
            {
                "actor",
                "actor_contact_point",
                "actor_student_relationship",
                "actor_roster_student_collision",
            },
        )
        for branch in schema["$defs"].values():
            self.assertFalse(branch["additionalProperties"])

    def test_actor_target_wraps_one_exact_directory_record(
        self,
    ) -> None:
        schema = load_json(
            REPO_ROOT
            / "schemas/v1/targets/actor-target.schema.json"
        )
        self.assertEqual(
            set(schema["required"]),
            {"kind", "record_ref"},
        )
        self.assertEqual(
            schema["properties"]["kind"]["const"],
            "actor_directory_record",
        )
        self.assertEqual(
            schema["properties"]["record_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/"
                "exact-actor-directory-record-ref.schema.json"
            ),
        )
        self.assertFalse(schema["additionalProperties"])
        for forbidden in (
            "workspace",
            "class_id",
            "work_id",
            "path",
            "fingerprint",
            "display_name",
            "contact_value",
        ):
            self.assertNotIn(forbidden, schema["properties"])


if __name__ == "__main__":
    unittest.main()
