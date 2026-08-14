from __future__ import annotations

import unittest
from copy import deepcopy

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


IMPORT_BATCH = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/imports/import-batch.schema.json"
)
IMPORT_SOURCE_RECORD = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/imports/import-source-record.schema.json"
)
TIMESTAMP = "2026-08-14T11:40:00-04:00"
SYSTEM_AGENT = {
    "type": "system_process",
    "process_id": "structured_import_test",
}
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64


def valid_batch() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "import_batch",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "import_batch_id": "ibat_attempt_01",
        "source_profile": {
            "source_system_id": "student_system",
            "profile_id": "behavior_export",
            "profile_version": "3",
            "display_label": "Synthetic behavior export",
        },
        "source_snapshot": {
            "locator": {
                "kind": "workspace_file",
                "path": "imports/synthetic-behavior.csv",
            },
            "fingerprint": {
                "algorithm": "sha256",
                "digest": SHA_A,
                "byte_length": 2048,
            },
            "observed_at": TIMESTAMP,
        },
        "mapping_profile": {
            "mapping_profile_id": "behavior_csv",
            "mapping_version": "5",
            "mapping_digest": SHA_B,
        },
        "import_identity_digest": SHA_C,
        "status": "open",
        "failure_codes": [],
        "started_at": TIMESTAMP,
        "created_at": TIMESTAMP,
        "created_by": deepcopy(SYSTEM_AGENT),
    }


def valid_source_record() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "import_source_record",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "import_batch_id": "ibat_attempt_01",
        "source_record_id": "isrc_observation_01",
        "source_record_key_origin": "source_provided",
        "source_record_key": "SRC-000042",
        "source_record_digest": SHA_A,
        "source_record_identity_digest": SHA_B,
        "source_fields": [
            {"field_key": "student_external_id", "value": "S-1042"},
            {"field_key": "source_label", "value": "office referral"},
            {"field_key": "points", "value": 2},
            {"field_key": "tags", "value": ["late", "hallway"]},
            {"field_key": "optional_note", "value": None},
        ],
        "observed_at": TIMESTAMP,
        "created_at": TIMESTAMP,
        "created_by": deepcopy(SYSTEM_AGENT),
    }


class Issue20ImportSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = build_schema_store()
        cls.batch_validator = cls.store.validator_for_id(IMPORT_BATCH)
        cls.source_validator = cls.store.validator_for_id(IMPORT_SOURCE_RECORD)

    def assert_batch_valid(self, value: object) -> None:
        errors = list(self.batch_validator.iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_batch_invalid(self, value: object) -> None:
        self.assertTrue(list(self.batch_validator.iter_errors(value)))

    def assert_source_valid(self, value: object) -> None:
        errors = list(self.source_validator.iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_source_invalid(self, value: object) -> None:
        self.assertTrue(list(self.source_validator.iter_errors(value)))

    def test_valid_open_import_batch(self) -> None:
        self.assert_batch_valid(valid_batch())

    def test_completed_batch_requires_finished_at_and_no_failure_codes(self) -> None:
        value = valid_batch()
        value["status"] = "completed"
        self.assert_batch_invalid(value)

        value["finished_at"] = TIMESTAMP
        self.assert_batch_valid(value)

        value["failure_codes"] = ["parse_error"]
        self.assert_batch_invalid(value)

    def test_failed_batch_requires_finished_at_and_failure_code(self) -> None:
        value = valid_batch()
        value["status"] = "failed"
        self.assert_batch_invalid(value)

        value["finished_at"] = TIMESTAMP
        self.assert_batch_invalid(value)

        value["failure_codes"] = ["mapping_unavailable"]
        self.assert_batch_valid(value)

    def test_open_batch_forbids_finished_at(self) -> None:
        value = valid_batch()
        value["finished_at"] = TIMESTAMP
        self.assert_batch_invalid(value)

    def test_import_snapshot_supports_external_and_opaque_locators(self) -> None:
        value = valid_batch()
        value["source_snapshot"]["locator"] = {
            "kind": "external_snapshot",
            "source_label": "Synthetic SIS export",
            "external_reference": "export:2026-08-14:1140",
        }
        self.assert_batch_valid(value)

        value = valid_batch()
        value["source_snapshot"]["locator"] = {
            "kind": "opaque_snapshot",
            "source_label": "Synthetic API response",
            "snapshot_key": "snap_20260814_1140",
        }
        self.assert_batch_valid(value)

    def test_source_snapshot_requires_exact_content_fingerprint(self) -> None:
        value = valid_batch()
        value["source_snapshot"]["fingerprint"]["digest"] = "A" * 64
        self.assert_batch_invalid(value)

        value = valid_batch()
        del value["source_snapshot"]["fingerprint"]["byte_length"]
        self.assert_batch_invalid(value)

    def test_mapping_profile_requires_exact_version_and_digest(self) -> None:
        value = valid_batch()
        del value["mapping_profile"]["mapping_digest"]
        self.assert_batch_invalid(value)

        value = valid_batch()
        value["mapping_profile"]["mapping_version"] = None
        self.assert_batch_invalid(value)

    def test_batch_replay_relationship_vocabulary_is_closed(self) -> None:
        value = valid_batch()
        value["comparison_to_previous"] = {
            "previous_import_batch_id": "ibat_attempt_00",
            "relationship": "replay_same_source_same_mapping",
        }
        self.assert_batch_valid(value)

        value["comparison_to_previous"]["relationship"] = "probably_same"
        self.assert_batch_invalid(value)

    def test_import_batch_is_not_paper_or_domain_work(self) -> None:
        value = valid_batch()
        value["work_id"] = "evt_should_not_exist"
        self.assert_batch_invalid(value)

        value = valid_batch()
        value["route_id"] = "route_should_not_exist"
        self.assert_batch_invalid(value)

    def test_valid_import_source_record(self) -> None:
        self.assert_source_valid(valid_source_record())

    def test_source_record_key_origin_is_closed(self) -> None:
        value = valid_source_record()
        value["source_record_key_origin"] = "profile_defined_exact"
        self.assert_source_valid(value)

        value["source_record_key_origin"] = "row_number"
        self.assert_source_invalid(value)

    def test_source_record_key_is_not_required_to_be_path_safe(self) -> None:
        value = valid_source_record()
        value["source_record_key"] = "source key: 42/A"
        self.assert_source_valid(value)

        value["source_record_key"] = "   "
        self.assert_source_invalid(value)

    def test_source_fields_preserve_scalar_array_and_explicit_null(self) -> None:
        value = valid_source_record()
        value["source_fields"] = [
            {"field_key": "text", "value": "synthetic"},
            {"field_key": "number", "value": 2.5},
            {"field_key": "boolean", "value": False},
            {"field_key": "explicit_null", "value": None},
            {"field_key": "values", "value": ["a", 2, True, None]},
        ]
        self.assert_source_valid(value)

    def test_source_fields_reject_nested_source_payloads(self) -> None:
        value = valid_source_record()
        value["source_fields"] = [
            {"field_key": "nested", "value": {"raw": "payload"}},
        ]
        self.assert_source_invalid(value)

        value = valid_source_record()
        value["source_fields"] = [
            {"field_key": "nested_array", "value": [["not", "allowed"]]},
        ]
        self.assert_source_invalid(value)

    def test_source_record_requires_both_content_and_identity_digests(self) -> None:
        value = valid_source_record()
        del value["source_record_digest"]
        self.assert_source_invalid(value)

        value = valid_source_record()
        value["source_record_identity_digest"] = "B" * 64
        self.assert_source_invalid(value)

    def test_source_record_does_not_embed_domain_or_deletion_semantics(self) -> None:
        forbidden = (
            ("event_id", "evt_event_01"),
            ("student_id", "student_01"),
            ("classification", "major"),
            ("proposal_ids", ["proposal_01"]),
            ("row_number", 7),
            ("deleted", True),
            ("creation_source", {"type": "import"}),
            ("raw_payload", {"nested": "source"}),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_source_record()
                value[field] = field_value
                self.assert_source_invalid(value)

    def test_import_identifiers_use_distinct_opaque_families(self) -> None:
        value = valid_batch()
        value["import_batch_id"] = "cbat_paper_batch"
        self.assert_batch_invalid(value)

        value = valid_source_record()
        value["source_record_id"] = "prec_paper_page"
        self.assert_source_invalid(value)

    def test_import_contracts_declare_required_application_invariants(self) -> None:
        batch_schema = self.store.schemas_by_id[IMPORT_BATCH]
        batch_ids = {
            item["id"]
            for item in batch_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "import_batch.operational_not_domain",
                "import_batch.paper_boundary",
                "import_batch.exact_source_snapshot",
                "import_batch.mapping_exactness",
                "import_batch.unchanged_replay_idempotent",
                "import_batch.changed_source_or_mapping_preserves_history",
                "import_batch.missing_later_source_not_deletion",
                "import_batch.no_fuzzy_identity",
                "import_batch.source_assertions_not_judgments",
            }
            <= batch_ids
        )

        source_schema = self.store.schemas_by_id[IMPORT_SOURCE_RECORD]
        source_ids = {
            item["id"]
            for item in source_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "import_source_record.source_side_not_domain",
                "import_source_record.zero_to_many_proposals",
                "import_source_record.stable_key_policy",
                "import_source_record.identity_digest",
                "import_source_record.missing_vs_null",
                "import_source_record.source_assertion_only",
                "import_source_record.no_identity_manufacture",
                "import_source_record.changed_content_preserves_history",
                "import_source_record.later_absence_not_deletion",
            }
            <= source_ids
        )

        for schema in (batch_schema, source_schema):
            for item in schema["x-portia-application-invariants"]:
                self.assertIsInstance(item, dict)
                self.assertTrue(item.get("id"))
                self.assertTrue(item.get("description"))


if __name__ == "__main__":
    unittest.main()
