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


FIXTURES = FIXTURE_ROOT / "event_participant_role" / "v2"
MIGRATIONS = (
    FIXTURE_ROOT
    / "migrations"
    / "event_participant_role_v1_to_v2"
)


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def record_ref_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    record_ref = value.get("record_ref")
    if not isinstance(record_ref, dict):
        return ()
    return (
        record_ref.get("record_kind"),
        record_ref.get("record_id"),
    )


def target_identity(record: object) -> tuple[object, ...]:
    if not isinstance(record, dict):
        return ()
    target = record.get("target")
    if not isinstance(target, dict):
        return ()
    record_ref = target.get("record_ref")
    if not isinstance(record_ref, dict):
        return ()
    return (
        target.get("kind"),
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

    creation_source = record.get("creation_source")
    if (
        isinstance(creation_source, dict)
        and creation_source.get("type") == "paper_capture"
    ):
        expected = (
            creation_source.get("route_id"),
            creation_source.get("page_record_id"),
        )
        basis = record.get("basis", [])
        paper_pairs = {
            (entry.get("route_id"), entry.get("page_record_id"))
            for entry in basis
            if isinstance(entry, dict)
            and entry.get("kind") == "paper_capture"
        }
        if expected not in paper_pairs:
            issues.add("paper_basis_mismatch")

    role_id = record.get("role_id")
    predecessors = record.get("supersedes", [])
    keys: list[tuple[object, ...]] = []
    if isinstance(predecessors, list):
        for entry in predecessors:
            key = record_ref_identity(entry)
            if key:
                keys.append(key)
                if key == ("event_participant_role", role_id):
                    issues.add("self_supersession")
    if len(keys) != len(set(keys)):
        issues.add("duplicate_predecessor_identity")

    return issues


def context_issues(record: object, context: object) -> set[str]:
    issues = application_issues(record)
    if not isinstance(record, dict) or not isinstance(context, dict):
        return issues | {"invalid_context"}

    expected_scope = context.get("expected_storage_scope")
    if isinstance(expected_scope, dict):
        actual_scope = {
            "module_id": record.get("module_id"),
            "class_id": record.get("class_id"),
            "work_id": record.get("work_id"),
        }
        if actual_scope != expected_scope:
            issues.add("storage_scope_mismatch")

    target = record.get("target")
    record_ref = target.get("record_ref") if isinstance(target, dict) else None
    participant_id = (
        record_ref.get("record_id")
        if isinstance(record_ref, dict)
        else None
    )
    participants = context.get("event_participants", [])
    match = next(
        (
            value
            for value in participants
            if isinstance(value, dict)
            and value.get("record_id") == participant_id
        ),
        None,
    )
    if match is None:
        issues.add("target_missing")
    else:
        if (
            match.get("class_id") != record.get("class_id")
            or match.get("work_id") != record.get("work_id")
        ):
            issues.add("target_scope_mismatch")
        if match.get("status") != "active":
            issues.add("target_lifecycle_ineligible")

    if (
        record.get("status") in {"active", "superseded"}
        and record.get("role_type") == "reported_involved"
    ):
        accounts = context.get("accounts", [])
        basis = record.get("basis", [])
        account_ids = [
            entry["record_ref"].get("record_id")
            for entry in basis
            if isinstance(entry, dict)
            and entry.get("kind") == "account_ref"
            and isinstance(entry.get("record_ref"), dict)
        ]
        for account_id in account_ids:
            account = next(
                (
                    value
                    for value in accounts
                    if isinstance(value, dict)
                    and value.get("record_id") == account_id
                ),
                None,
            )
            if account is None:
                issues.add("account_missing")
            elif (
                account.get("class_id") != record.get("class_id")
                or account.get("work_id") != record.get("work_id")
                or account.get("status") != "active"
                or account.get("attributed") is not True
            ):
                issues.add("account_ineligible")

    return issues


def active_role_key(record: object) -> tuple[object, ...] | None:
    if not isinstance(record, dict) or record.get("status") != "active":
        return None
    return (
        record.get("module_id"),
        record.get("class_id"),
        record.get("work_id"),
        *target_identity(record),
        record.get("role_type"),
    )


def has_duplicate_active_role(records: object) -> bool:
    if not isinstance(records, list):
        return False
    keys = [
        key
        for record in records
        if (key := active_role_key(record)) is not None
    ]
    return len(keys) != len(set(keys))


def has_supersession_cycle(records: object) -> bool:
    if not isinstance(records, list):
        return False
    graph: dict[str, set[str]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        role_id = record.get("role_id")
        if not isinstance(role_id, str):
            continue
        graph.setdefault(role_id, set())
        for entry in record.get("supersedes", []):
            key = record_ref_identity(entry)
            if key and key[0] == "event_participant_role":
                predecessor = key[1]
                if isinstance(predecessor, str):
                    graph[role_id].add(predecessor)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, set()):
            if neighbor in graph and visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


class EventParticipantRoleV2SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.v1_validator = validator_for(
            "event_participant_role",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.v2_validator = validator_for(
            "event_participant_role",
            "2",
            catalog=cls.catalog,
            store=cls.store,
        )

    def fixture_paths(self, category: str) -> list[Path]:
        return sorted((FIXTURES / category).glob("*.json"))

    def test_v1_and_v2_are_cataloged_separately(self) -> None:
        self.assertEqual(
            schema_id_for("event_participant_role", "1", self.catalog),
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/event-participant-role.schema.json"
            ),
        )
        self.assertEqual(
            schema_id_for("event_participant_role", "2", self.catalog),
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v2/event-participant-role.schema.json"
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

    def test_application_invalid_contexts(self) -> None:
        paths = self.fixture_paths("application_invalid_contexts")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                fixture = load_json(path)
                self.assertEqual(
                    set(fixture),
                    {"record", "context", "expected_issue"},
                )
                record = fixture["record"]
                errors = list(self.v2_validator.iter_errors(record))
                self.assertFalse(
                    errors,
                    "Contextual application-invalid record must remain "
                    "structurally valid:\n" + "\n".join(
                        error.message for error in errors
                    ),
                )
                self.assertIn(
                    fixture["expected_issue"],
                    context_issues(record, fixture["context"]),
                )

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
                    has_duplicate_active_role(records)
                    or has_supersession_cycle(records)
                )

    def test_v2_composes_public_shared_contracts(self) -> None:
        schema_id = schema_id_for(
            "event_participant_role", "2", self.catalog
        )
        schema = self.store.schema_for_id(schema_id)
        properties = schema["properties"]
        defs = schema["$defs"]

        self.assertEqual(
            defs["singularParticipantTarget"]["allOf"][0]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/targets/portia-target-ref.schema.json"
            ),
        )
        self.assertEqual(
            defs["accountRecordRef"]["allOf"][0]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/local-record-ref.schema.json"
            ),
        )
        self.assertEqual(
            properties["creation_source"]["allOf"][0]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/provenance/creation-source.schema.json"
            ),
        )

    def test_target_is_singular_participant_only(self) -> None:
        schema_id = schema_id_for(
            "event_participant_role", "2", self.catalog
        )
        schema = self.store.schema_for_id(schema_id)
        constraint = schema["$defs"]["singularParticipantTarget"]
        properties = constraint["allOf"][1]["properties"]
        self.assertEqual(properties["kind"]["const"], "event_participant")
        versions = (
            schema["$defs"]["participantRecordRef"]
            ["allOf"][1]["properties"]["contract_version"]["enum"]
        )
        self.assertEqual(versions, ["1", "2"])

    def test_v2_rejects_obsolete_reference_properties(self) -> None:
        names = (
            "obsolete-participant-id.json",
            "flat-account-basis-record-id.json",
            "flat-role-id-supersession.json",
        )
        for name in names:
            with self.subTest(fixture=name):
                value = load_json(FIXTURES / "invalid" / name)
                self.assertTrue(list(self.v2_validator.iter_errors(value)))

    def test_migration_fixtures_preserve_identity_and_creation(self) -> None:
        paths = sorted(MIGRATIONS.glob("*.json"))
        self.assertTrue(paths)
        stable_fields = (
            "record_type",
            "module_id",
            "class_id",
            "work_id",
            "role_id",
            "status",
            "role_type",
        )
        provenance_fields = (
            "creation_source",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        )

        for path in paths:
            with self.subTest(fixture=path.name):
                pair = load_json(path)
                self.assertEqual(set(pair), {"source_v1", "target_v2"})
                source = pair["source_v1"]
                target = pair["target_v2"]

                source_errors = list(self.v1_validator.iter_errors(source))
                target_errors = list(self.v2_validator.iter_errors(target))
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
                for field in stable_fields + provenance_fields:
                    self.assertEqual(source[field], target[field])

                self.assertNotIn("participant_id", target)
                self.assertEqual(
                    target["target"]["record_ref"]["record_id"],
                    source["participant_id"],
                )
                self.assertIn(
                    target["target"]["record_ref"]["contract_version"],
                    {"1", "2"},
                )

                old_basis = source.get("basis", [])
                new_basis = target.get("basis", [])
                self.assertEqual(len(old_basis), len(new_basis))
                for old, new in zip(old_basis, new_basis, strict=True):
                    self.assertEqual(old["kind"], new["kind"])
                    if old["kind"] in {"account_ref", "observation_ref"}:
                        self.assertNotIn("record_id", new)
                        self.assertEqual(
                            new["record_ref"]["record_id"],
                            old["record_id"],
                        )
                        self.assertIsNone(
                            new["record_ref"]["contract_version"]
                        )
                    else:
                        self.assertEqual(old, new)

                old_supersedes = source.get("supersedes", [])
                new_supersedes = target.get("supersedes", [])
                self.assertEqual(len(old_supersedes), len(new_supersedes))
                for old, new in zip(
                    old_supersedes, new_supersedes, strict=True
                ):
                    self.assertNotIn("role_id", new)
                    self.assertEqual(
                        new["record_ref"],
                        {
                            "record_kind": "event_participant_role",
                            "record_id": old["role_id"],
                            "contract_version": "1",
                        },
                    )
                    self.assertEqual(old["reason"], new["reason"])
                    self.assertEqual(old.get("detail"), new.get("detail"))


if __name__ == "__main__":
    unittest.main()
