from __future__ import annotations

from datetime import datetime
from pathlib import Path
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


FIXTURES = FIXTURE_ROOT / "event_participant" / "v2"
MIGRATIONS = (
    FIXTURE_ROOT
    / "migrations"
    / "event_participant_v1_to_v2"
)


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def predecessor_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    record_ref = value.get("record_ref")
    if not isinstance(record_ref, dict):
        return ()
    return (
        record_ref.get("record_kind"),
        record_ref.get("record_id"),
    )


def application_issues(record: object) -> set[str]:
    if not isinstance(record, dict):
        return {"not_object"}

    issues: set[str] = set()
    created_at = record.get("created_at")
    updated_at = record.get("updated_at")
    if isinstance(created_at, str) and isinstance(updated_at, str):
        if parse_timestamp(updated_at) < parse_timestamp(created_at):
            issues.add("timestamp_chronology")

    participant_id = record.get("participant_id")
    supersedes = record.get("supersedes", [])
    predecessor_keys: list[tuple[object, ...]] = []
    if isinstance(supersedes, list):
        for entry in supersedes:
            key = predecessor_identity(entry)
            if key:
                predecessor_keys.append(key)
                if key == ("event_participant", participant_id):
                    issues.add("self_supersession")

    if len(predecessor_keys) != len(set(predecessor_keys)):
        issues.add("duplicate_predecessor_identity")

    return issues


def durable_subject_identity(record: object) -> tuple[object, ...] | None:
    if not isinstance(record, dict) or record.get("status") != "active":
        return None
    subject = record.get("subject")
    if not isinstance(subject, dict):
        return None

    kind = subject.get("kind")
    if kind == "roster_student":
        ref = subject.get("roster_student_ref")
        if not isinstance(ref, dict):
            return None
        return (
            "roster_student",
            ref.get("class_id"),
            ref.get("student_id"),
        )
    if kind == "actor":
        ref = subject.get("actor_ref")
        if not isinstance(ref, dict):
            return None
        return ("actor", ref.get("actor_id"))
    return None


def has_duplicate_active_durable_subject(records: object) -> bool:
    if not isinstance(records, list):
        return False
    identities = [
        identity
        for record in records
        if (identity := durable_subject_identity(record)) is not None
    ]
    return len(identities) != len(set(identities))


class EventParticipantV2SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.v1_validator = validator_for(
            "event_participant",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.v2_validator = validator_for(
            "event_participant",
            "2",
            catalog=cls.catalog,
            store=cls.store,
        )

    def fixture_paths(self, category: str) -> list[Path]:
        return sorted((FIXTURES / category).glob("*.json"))

    def test_v1_and_v2_are_cataloged_separately(self) -> None:
        self.assertEqual(
            schema_id_for("event_participant", "1", self.catalog),
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/event-participant.schema.json"
            ),
        )
        self.assertEqual(
            schema_id_for("event_participant", "2", self.catalog),
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v2/event-participant.schema.json"
            ),
        )

    def test_valid_fixtures(self) -> None:
        paths = self.fixture_paths("valid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.v2_validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "\n".join(error.message for error in errors),
                )
                self.assertFalse(application_issues(value))

    def test_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                errors = list(
                    self.v2_validator.iter_errors(load_json(path))
                )
                self.assertTrue(
                    errors,
                    f"{path.name} unexpectedly passed validation",
                )

    def test_application_invalid_fixtures(self) -> None:
        paths = self.fixture_paths("application_invalid")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                value = load_json(path)
                errors = list(self.v2_validator.iter_errors(value))
                self.assertFalse(
                    errors,
                    "Application-invalid fixture must remain structurally "
                    "valid:\n" + "\n".join(
                        error.message for error in errors
                    ),
                )
                self.assertTrue(application_issues(value))

    def test_application_invalid_fixture_sets(self) -> None:
        paths = self.fixture_paths("application_invalid_sets")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                records = load_json(path)
                self.assertIsInstance(records, list)
                self.assertGreaterEqual(len(records), 2)
                for index, record in enumerate(records):
                    errors = list(self.v2_validator.iter_errors(record))
                    self.assertFalse(
                        errors,
                        f"Record {index} in {path.name} must be "
                        "structurally valid:\n" + "\n".join(
                            error.message for error in errors
                        ),
                    )
                    self.assertFalse(application_issues(record))
                self.assertTrue(
                    has_duplicate_active_durable_subject(records)
                )

    def test_v2_composes_public_shared_contracts(self) -> None:
        schema_id = schema_id_for(
            "event_participant", "2", self.catalog
        )
        schema = self.store.schema_for_id(schema_id)
        properties = schema["properties"]
        defs = schema["$defs"]

        self.assertEqual(
            properties["work_id"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/identifiers/portia-event-id.schema.json"
            ),
        )
        self.assertEqual(
            defs["rosterStudentSubject"]["properties"]
            ["roster_student_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/roster-student-ref.schema.json"
            ),
        )
        self.assertEqual(
            defs["actorSubject"]["properties"]["actor_ref"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/actor-ref.schema.json"
            ),
        )
        self.assertEqual(
            properties["creation_source"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/provenance/creation-source.schema.json"
            ),
        )

    def test_v2_rejects_obsolete_subject_property_names(self) -> None:
        roster = load_json(
            FIXTURES / "invalid" / "v1-student-ref-property.json"
        )
        actor = load_json(
            FIXTURES / "invalid" / "v1-bare-actor-id.json"
        )
        self.assertTrue(list(self.v2_validator.iter_errors(roster)))
        self.assertTrue(list(self.v2_validator.iter_errors(actor)))

    def test_migration_fixtures_preserve_identity_and_creation(self) -> None:
        paths = sorted(MIGRATIONS.glob("*.json"))
        self.assertTrue(paths)
        stable_fields = (
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "participant_id",
        )
        creation_fields = (
            "creation_source",
            "created_at",
            "created_by",
        )

        for path in paths:
            with self.subTest(fixture=path.name):
                pair = load_json(path)
                self.assertEqual(set(pair), {"source_v1", "target_v2"})
                source = pair["source_v1"]
                target = pair["target_v2"]

                source_errors = list(
                    self.v1_validator.iter_errors(source)
                )
                target_errors = list(
                    self.v2_validator.iter_errors(target)
                )
                self.assertFalse(
                    source_errors,
                    "\n".join(error.message for error in source_errors),
                )
                self.assertFalse(
                    target_errors,
                    "\n".join(error.message for error in target_errors),
                )

                self.assertEqual(source["schema_version"], "1")
                self.assertEqual(target["schema_version"], "2")
                for field in stable_fields + creation_fields:
                    self.assertEqual(source[field], target[field])

                source_subject = source["subject"]
                target_subject = target["subject"]
                self.assertEqual(
                    source_subject["kind"], target_subject["kind"]
                )
                if source_subject["kind"] == "roster_student":
                    self.assertEqual(
                        source_subject["student_ref"],
                        target_subject["roster_student_ref"],
                    )
                    self.assertNotIn("student_ref", target_subject)
                elif source_subject["kind"] == "actor":
                    self.assertEqual(
                        source_subject["actor_id"],
                        target_subject["actor_ref"]["actor_id"],
                    )
                    self.assertNotIn("actor_id", target_subject)
                else:
                    self.assertEqual(source_subject, target_subject)

                if "display_snapshot" in source_subject:
                    self.assertEqual(
                        source_subject["display_snapshot"],
                        target_subject["display_snapshot"],
                    )

                source_supersedes = source.get("supersedes", [])
                target_supersedes = target.get("supersedes", [])
                self.assertEqual(
                    len(source_supersedes), len(target_supersedes)
                )
                for old, new in zip(
                    source_supersedes, target_supersedes, strict=True
                ):
                    self.assertEqual(
                        new["record_ref"],
                        {
                            "record_kind": "event_participant",
                            "record_id": old["participant_id"],
                            "contract_version": "1",
                        },
                    )
                    self.assertEqual(old["reason"], new["reason"])
                    self.assertEqual(
                        old.get("detail"), new.get("detail")
                    )


if __name__ == "__main__":
    unittest.main()
