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


FIXTURES = FIXTURE_ROOT / "event" / "v2"
MIGRATIONS = FIXTURE_ROOT / "migrations" / "event_v1_to_v2"


def parse_timestamp(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def event_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    return (
        value.get("module_id"),
        value.get("class_id"),
        value.get("work_id"),
    )


def predecessor_identity(value: object) -> tuple[object, ...]:
    return event_identity(value)


def module_record_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, dict):
        return ()
    work_ref = value.get("work_ref")
    record_ref = value.get("record_ref")
    if not isinstance(work_ref, dict) or not isinstance(record_ref, dict):
        return ()
    return (
        work_ref.get("module_id"),
        work_ref.get("class_id"),
        work_ref.get("work_id"),
        record_ref.get("record_kind"),
        record_ref.get("record_id"),
    )


def instructional_refs(record: object) -> list[dict]:
    if not isinstance(record, dict):
        return []
    context = record.get("instructional_context")
    if not isinstance(context, dict):
        return []
    refs = context.get("external_refs", [])
    if not isinstance(refs, list):
        return []
    return [value for value in refs if isinstance(value, dict)]


def application_issues(record: object) -> set[str]:
    if not isinstance(record, dict):
        return {"not_object"}

    issues: set[str] = set()
    created_at = record.get("created_at")
    updated_at = record.get("updated_at")
    if isinstance(created_at, str) and isinstance(updated_at, str):
        if parse_timestamp(updated_at) < parse_timestamp(created_at):
            issues.add("timestamp_chronology")

    occurrence = record.get("occurrence")
    if isinstance(occurrence, dict):
        started_at = occurrence.get("started_at")
        ended_at = occurrence.get("ended_at")
        if isinstance(started_at, str) and isinstance(ended_at, str):
            if parse_timestamp(ended_at) < parse_timestamp(started_at):
                issues.add("occurrence_chronology")

    for ref in instructional_refs(record):
        work_ref = ref.get("work_ref")
        record_ref = ref.get("record_ref")
        if isinstance(work_ref, dict) and isinstance(record_ref, dict):
            if work_ref.get("module_id") != record_ref.get("module_id"):
                issues.add("instructional_module_id_mismatch")

    current_identity = event_identity(record)
    predecessor_keys: list[tuple[object, ...]] = []
    predecessors = record.get("supersedes", [])
    if isinstance(predecessors, list):
        for predecessor in predecessors:
            key = predecessor_identity(predecessor)
            if key:
                predecessor_keys.append(key)
                if key == current_identity:
                    issues.add("self_supersession")
    if len(predecessor_keys) != len(set(predecessor_keys)):
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

    available_records = context.get("instructional_records")
    if isinstance(available_records, list):
        for reference in instructional_refs(record):
            identity = module_record_identity(reference)
            match = next(
                (
                    candidate
                    for candidate in available_records
                    if isinstance(candidate, dict)
                    and (
                        candidate.get("module_id"),
                        candidate.get("class_id"),
                        candidate.get("work_id"),
                        candidate.get("record_kind"),
                        candidate.get("record_id"),
                    ) == identity
                ),
                None,
            )
            if match is None:
                issues.add("instructional_reference_missing")
                continue
            contract_version = reference["record_ref"].get(
                "contract_version"
            )
            supported = match.get("supported_contract_versions", [])
            if (
                contract_version is not None
                and isinstance(supported, list)
                and contract_version not in supported
            ):
                issues.add("instructional_contract_unsupported")
            if match.get("available") is False:
                issues.add("instructional_reference_unavailable")
            if match.get("eligible") is False:
                issues.add("instructional_reference_ineligible")

    if record.get("status") == "active":
        count = context.get("active_participant_count")
        if isinstance(count, int) and count < 1:
            issues.add("activation_without_active_participant")

        creation_source = record.get("creation_source")
        if (
            isinstance(creation_source, dict)
            and creation_source.get("type") in {"paper_capture", "import"}
            and context.get("review_completed") is False
        ):
            issues.add("review_required")

    prior_status = context.get("prior_status")
    current_status = record.get("status")
    allowed: dict[str, set[str]] = {
        "draft": {"draft", "active", "cancelled", "invalidated"},
        "active": {"active", "closed", "cancelled", "invalidated", "superseded"},
        "closed": {"closed", "invalidated", "superseded"},
        "cancelled": {"cancelled"},
        "invalidated": {"invalidated"},
        "superseded": {"superseded"},
    }
    if (
        isinstance(prior_status, str)
        and isinstance(current_status, str)
        and current_status not in allowed.get(prior_status, set())
    ):
        issues.add("invalid_lifecycle_transition")

    return issues


def has_supersession_cycle(records: object) -> bool:
    if not isinstance(records, list):
        return False
    graph: dict[tuple[object, ...], set[tuple[object, ...]]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        source = event_identity(record)
        if not source:
            continue
        graph.setdefault(source, set())
        for predecessor in record.get("supersedes", []):
            key = predecessor_identity(predecessor)
            if key:
                graph[source].add(key)

    visiting: set[tuple[object, ...]] = set()
    visited: set[tuple[object, ...]] = set()

    def visit(node: tuple[object, ...]) -> bool:
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


class EventV2SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.v1_validator = validator_for(
            "event", "1", catalog=cls.catalog, store=cls.store
        )
        cls.v2_validator = validator_for(
            "event", "2", catalog=cls.catalog, store=cls.store
        )

    def fixture_paths(self, category: str) -> list[Path]:
        return sorted((FIXTURES / category).glob("*.json"))

    def test_v1_and_v2_are_cataloged_separately(self) -> None:
        self.assertEqual(
            schema_id_for("event", "1", self.catalog),
            "https://paper-data-suite.github.io/pds-portia/schemas/event.schema.json",
        )
        self.assertEqual(
            schema_id_for("event", "2", self.catalog),
            "https://paper-data-suite.github.io/pds-portia/schemas/v2/event.schema.json",
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
                    f"{path.name} unexpectedly passed structural validation",
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
                    "Application-invalid fixture must remain structurally valid:\n"
                    + "\n".join(error.message for error in errors),
                )
                self.assertTrue(application_issues(value))

    def test_application_invalid_context_fixtures(self) -> None:
        paths = self.fixture_paths("application_invalid_contexts")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                pair = load_json(path)
                record = pair["record"]
                self.v2_validator.validate(record)
                self.assertTrue(context_issues(record, pair["context"]))

    def test_application_invalid_record_sets(self) -> None:
        paths = self.fixture_paths("application_invalid_sets")
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(fixture=path.name):
                records = load_json(path)
                for record in records:
                    self.v2_validator.validate(record)
                self.assertTrue(has_supersession_cycle(records))

    def test_instructional_refs_compose_shared_contract(self) -> None:
        schema_id = schema_id_for("event", "2", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        external_refs = (
            schema["$defs"]["instructionalContext"]
            ["properties"]["external_refs"]
        )
        self.assertEqual(
            external_refs["items"]["$ref"],
            (
                "https://paper-data-suite.github.io/pds-portia/"
                "schemas/v1/references/module-work-record-ref.schema.json"
            ),
        )

    def test_supersedes_is_event_only_and_versioned(self) -> None:
        schema_id = schema_id_for("event", "2", self.catalog)
        schema = self.store.schema_for_id(schema_id)
        constraints = schema["$defs"]["eventWorkRef"]["allOf"][1]
        properties = constraints["properties"]
        self.assertEqual(properties["work_kind"]["const"], "event")
        self.assertEqual(
            properties["contract_version"]["enum"], ["1", "2"]
        )

    def test_v2_rejects_obsolete_reference_shapes(self) -> None:
        names = (
            "obsolete-flat-external-ref.json",
            "obsolete-flat-event-supersession.json",
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
            "work_kind",
            "module_id",
            "class_id",
            "work_id",
            "school_year",
            "status",
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

                old_refs = source.get("instructional_context", {}).get(
                    "external_refs", []
                )
                new_refs = target.get("instructional_context", {}).get(
                    "external_refs", []
                )
                self.assertEqual(len(old_refs), len(new_refs))
                for old, new in zip(old_refs, new_refs, strict=True):
                    self.assertEqual(
                        new["work_ref"],
                        {
                            "module_id": old["module_id"],
                            "class_id": old["class_id"],
                            "work_id": old["work_id"],
                        },
                    )
                    self.assertEqual(
                        new["record_ref"],
                        {
                            "module_id": old["module_id"],
                            "record_kind": old["record_kind"],
                            "record_id": old["record_id"],
                            "contract_version": None,
                        },
                    )

                old_supersedes = source.get("supersedes", [])
                new_supersedes = target.get("supersedes", [])
                self.assertEqual(len(old_supersedes), len(new_supersedes))
                for old, new in zip(
                    old_supersedes, new_supersedes, strict=True
                ):
                    self.assertEqual(
                        new,
                        {
                            "module_id": "portia",
                            "class_id": old["class_id"],
                            "work_id": old["work_id"],
                            "work_kind": "event",
                            "contract_version": "1",
                        },
                    )


if __name__ == "__main__":
    unittest.main()
