from __future__ import annotations

from datetime import datetime
import unittest
from pathlib import Path

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

FIXTURES = FIXTURE_ROOT / "work_relationship" / "v1"


def work_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    return (value.get("module_id"), value.get("class_id"), value.get("work_id"))


def relationship_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    return (
        value.get("module_id"), value.get("class_id"),
        value.get("work_id"), value.get("relationship_id"),
    )


def predecessor_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    wrapper = value.get("work_record_ref")
    if not isinstance(wrapper, dict):
        return ()
    work_ref = wrapper.get("work_ref")
    record_ref = wrapper.get("record_ref")
    if not isinstance(work_ref, dict) or not isinstance(record_ref, dict):
        return ()
    return (
        work_ref.get("module_id"), work_ref.get("class_id"), work_ref.get("work_id"),
        record_ref.get("record_kind"), record_ref.get("record_id"),
    )


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def application_issues(relationship: object) -> set[str]:
    if not isinstance(relationship, dict):
        return {"not_object"}
    issues: set[str] = set()
    source = relationship.get("source")
    target = relationship.get("target")
    top = {
        "module_id": relationship.get("module_id"),
        "class_id": relationship.get("class_id"),
        "work_id": relationship.get("work_id"),
    }
    if work_identity(top) != work_identity(source):
        issues.add("source_scope_mismatch")
    if work_identity(source) == work_identity(target):
        issues.add("self_reference")
    created_at = relationship.get("created_at")
    updated_at = relationship.get("updated_at")
    if isinstance(created_at, str) and isinstance(updated_at, str):
        if parse_timestamp(updated_at) < parse_timestamp(created_at):
            issues.add("timestamp_chronology")
    current = relationship_identity(relationship)
    keys: list[tuple[object, ...]] = []
    supersedes = relationship.get("supersedes", [])
    if isinstance(supersedes, list):
        for entry in supersedes:
            key = predecessor_identity(entry)
            if key:
                keys.append(key)
                predecessor_relationship = (key[0], key[1], key[2], key[4])
                if predecessor_relationship == current:
                    issues.add("self_supersession")
    if len(keys) != len(set(keys)):
        issues.add("duplicate_predecessor_identity")
    return issues


def active_edge_key(value: object) -> tuple[object, ...] | None:
    if not isinstance(value, dict) or value.get("status") != "active":
        return None
    return (*work_identity(value.get("source")), value.get("relationship_type"), *work_identity(value.get("target")))


def has_duplicate_active_edge(values: object) -> bool:
    if not isinstance(values, list):
        return False
    keys = [key for value in values if (key := active_edge_key(value)) is not None]
    return len(keys) != len(set(keys))


class WorkRelationshipSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "work_relationship", "1", catalog=cls.catalog, store=cls.store
        )

    def fixture_paths(self, category: str) -> list[Path]:
        return sorted((FIXTURES / category).glob("*.json"))

    def test_contract_is_cataloged(self) -> None:
        self.assertEqual(
            schema_id_for("work_relationship", "1", self.catalog),
            "https://paper-data-suite.github.io/pds-portia/schemas/v1/work-relationship.schema.json",
        )

    def test_valid_fixtures(self) -> None:
        paths = self.fixture_paths("valid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                self.assertFalse(application_issues(value))

    def test_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                errors = list(self.validator.iter_errors(load_json(path)))
                self.assertTrue(errors, f"{path.name} unexpectedly passed structural validation")

    def test_application_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("application_invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "Application-invalid fixture must remain structurally valid:\n"
                    + "\n".join(error.message for error in errors),
                )
                self.assertTrue(application_issues(value))

    def test_application_invalid_fixture_sets(self) -> None:
        paths = self.fixture_paths("application_invalid_sets")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                values = load_json(path)
                self.assertIsInstance(values, list)
                self.assertGreaterEqual(len(values), 2)
                for index, value in enumerate(values):
                    errors = list(self.validator.iter_errors(value))
                    self.assertFalse(
                        errors,
                        f"Record {index} in {path.name} must be structurally valid:\n"
                        + "\n".join(error.message for error in errors),
                    )
                    self.assertFalse(application_issues(value))
                self.assertTrue(has_duplicate_active_edge(values))

    def test_required_envelope_and_optional_fields(self) -> None:
        schema_id = schema_id_for("work_relationship", "1", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        required = {
            "schema_version", "record_type", "module_id", "class_id", "work_id",
            "relationship_id", "status", "relationship_type", "source", "target",
            "creation_source", "created_at", "created_by", "updated_at", "updated_by",
        }
        self.assertEqual(set(schema["required"]), required)
        self.assertEqual(set(schema["properties"]) - required, {"detail", "supersedes"})
        self.assertFalse(schema["additionalProperties"])

    def test_public_contract_composition(self) -> None:
        schema_id = schema_id_for("work_relationship", "1", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        props = schema["properties"]
        self.assertEqual(
            props["source"]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/schemas/v1/references/portia-work-ref.schema.json",
        )
        self.assertEqual(
            props["creation_source"]["allOf"][0]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/schemas/v1/provenance/creation-source.schema.json",
        )
        self.assertEqual(
            props["created_at"]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/schemas/v1/common/explicit-offset-timestamp.schema.json",
        )

    def test_initial_directional_vocabulary(self) -> None:
        schema_id = schema_id_for("work_relationship", "1", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        self.assertEqual(schema["properties"]["relationship_type"]["const"], "draws_context_from")
        constraint = schema["properties"]["target"]["allOf"][1]
        self.assertEqual(constraint["properties"]["work_kind"]["const"], "event")

    def test_paper_preallocation_is_prohibited(self) -> None:
        schema_id = schema_id_for("work_relationship", "1", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        restriction = schema["properties"]["creation_source"]["allOf"][1]["not"]
        self.assertEqual(restriction["properties"]["stage"]["const"], "preallocated")


if __name__ == "__main__":
    unittest.main()
