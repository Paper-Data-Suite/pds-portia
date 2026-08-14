from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


BASE = "https://paper-data-suite.github.io/pds-portia/schemas/v1"
CAPTURE_BATCH_ID = f"{BASE}/identifiers/portia-capture-batch-id.schema.json"
PAGE_TARGET_ID = f"{BASE}/identifiers/portia-page-target-id.schema.json"
PAGE_RECORD_ID = f"{BASE}/identifiers/portia-page-record-id.schema.json"
CAPTURE_BATCH = f"{BASE}/capture/capture-batch.schema.json"
PAGE_TARGET = f"{BASE}/capture/page-target.schema.json"
PAGE_RECORD = f"{BASE}/capture/page-record.schema.json"

ROOT = Path(__file__).resolve().parents[2]
AGENT = {
    "type": "system_process",
    "process_id": "paper_capture_test",
}
TIMESTAMP = "2026-08-13T16:00:00-04:00"
SOURCE_SHA256 = "a" * 64
LAYOUT_FINGERPRINT = "b" * 64


def valid_capture_batch() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "capture_batch",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "status": "open",
        "created_at": TIMESTAMP,
        "created_by": deepcopy(AGENT),
        "updated_at": TIMESTAMP,
        "updated_by": deepcopy(AGENT),
    }


def valid_page_target() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "capture_page_target",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_index": 1,
        "page_purpose": "new_event_capture",
        "template_identity": {
            "template_id": "portia_event_intake",
            "template_version": "1.2.0",
            "layout_version": "layout_3",
            "capture_spec_version": "capture_2",
            "layout_fingerprint": LAYOUT_FINGERPRINT,
            "page_role": "incident_form",
            "page_ordinal": 1,
        },
        "capture_mode": "mixed_recognition",
        "entry_layout": {
            "mode": "single_entry",
            "entry_keys": ["entry"],
        },
        "status": "active",
        "created_at": TIMESTAMP,
        "created_by": deepcopy(AGENT),
        "updated_at": TIMESTAMP,
        "updated_by": deepcopy(AGENT),
    }


def exact_event_context() -> dict[str, object]:
    return {
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "evt_event_01",
        "work_kind": "event",
        "contract_version": "2",
    }


def exact_support_process_context() -> dict[str, object]:
    return {
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "sup_support_01",
        "work_kind": "support_process",
        "contract_version": "1",
    }


def valid_page_record() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "capture_page_record",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_record_id": "prec_returned_01",
        "route_id": "route_portia_capture_01",
        "source_ref": {
            "source_scan_id": "scan_portia_capture_01",
            "source_sha256": SOURCE_SHA256,
            "source_page_number": 1,
        },
        "processing_state": "received",
        "created_at": TIMESTAMP,
        "created_by": deepcopy(AGENT),
        "updated_at": TIMESTAMP,
        "updated_by": deepcopy(AGENT),
    }


class Issue20CaptureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = build_schema_store()

    def validator(self, schema_id: str):
        return self.store.validator_for_id(schema_id)

    def assert_valid(self, schema_id: str, value: object) -> None:
        errors = list(self.validator(schema_id).iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_invalid(self, schema_id: str, value: object) -> None:
        self.assertTrue(list(self.validator(schema_id).iter_errors(value)))

    def test_capture_identifiers_are_opaque_and_prefix_scoped(self) -> None:
        cases = (
            (CAPTURE_BATCH_ID, "cbat_batch_01", "ptgt_batch_01"),
            (PAGE_TARGET_ID, "ptgt_page_01", "prec_page_01"),
            (PAGE_RECORD_ID, "prec_returned_01", "cbat_returned_01"),
        )
        for schema_id, valid, invalid in cases:
            with self.subTest(schema_id=schema_id):
                self.assert_valid(schema_id, valid)
                self.assert_invalid(schema_id, invalid)

    def test_capture_batch_is_a_non_domain_portia_work_root(self) -> None:
        value = valid_capture_batch()
        self.assert_valid(CAPTURE_BATCH, value)

        for field, invalid_value in (
            ("record_type", "event"),
            ("work_kind", "event"),
            ("module_id", "core"),
        ):
            with self.subTest(field=field):
                candidate = deepcopy(value)
                candidate[field] = invalid_value
                self.assert_invalid(CAPTURE_BATCH, candidate)

    def test_capture_batch_does_not_accept_domain_record_fields(self) -> None:
        value = valid_capture_batch()
        value["event_id"] = "evt_fabricated"
        self.assert_invalid(CAPTURE_BATCH, value)

    def test_page_target_exists_without_route_or_domain_identity(self) -> None:
        value = valid_page_target()
        self.assert_valid(PAGE_TARGET, value)

        for forbidden_field, forbidden_value in (
            ("route_id", "route_early"),
            ("page_record_id", "prec_early"),
            ("event_id", "evt_early"),
        ):
            with self.subTest(field=forbidden_field):
                candidate = deepcopy(value)
                candidate[forbidden_field] = forbidden_value
                self.assert_invalid(PAGE_TARGET, candidate)

    def test_page_target_requires_positive_logical_page_index(self) -> None:
        value = valid_page_target()
        value["page_index"] = 0
        self.assert_invalid(PAGE_TARGET, value)

    def test_page_target_requires_durable_template_and_capture_identity(self) -> None:
        value = valid_page_target()
        self.assert_valid(PAGE_TARGET, value)

        for missing in (
            "template_id",
            "template_version",
            "layout_version",
            "capture_spec_version",
            "layout_fingerprint",
            "page_role",
            "page_ordinal",
        ):
            with self.subTest(missing=missing):
                candidate = valid_page_target()
                del candidate["template_identity"][missing]
                self.assert_invalid(PAGE_TARGET, candidate)

        candidate = valid_page_target()
        candidate["template_identity"]["layout_fingerprint"] = "B" * 64
        self.assert_invalid(PAGE_TARGET, candidate)

    def test_page_target_uses_closed_purpose_vocabulary_and_other_detail(self) -> None:
        value = valid_page_target()
        value["page_purpose"] = "invented_success_capture"
        self.assert_invalid(PAGE_TARGET, value)

        value = valid_page_target()
        value["page_purpose"] = "other"
        self.assert_invalid(PAGE_TARGET, value)
        value["purpose_detail"] = "bounded locally defined capture purpose"
        self.assert_valid(PAGE_TARGET, value)

        value = valid_page_target()
        value["purpose_detail"] = "detail is not allowed for a registered purpose"
        self.assert_invalid(PAGE_TARGET, value)

    def test_new_event_and_multi_entry_targets_do_not_prebind_existing_work(self) -> None:
        for purpose in ("new_event_capture", "multi_entry_event_capture"):
            with self.subTest(purpose=purpose):
                value = valid_page_target()
                value["page_purpose"] = purpose
                if purpose == "multi_entry_event_capture":
                    value["entry_layout"] = {
                        "mode": "multi_entry",
                        "entry_keys": ["row_01", "row_02"],
                    }
                self.assert_valid(PAGE_TARGET, value)
                value["existing_work_context"] = exact_event_context()
                self.assert_invalid(PAGE_TARGET, value)

    def test_page_target_preserves_exact_existing_event_context(self) -> None:
        value = valid_page_target()
        value["page_purpose"] = "event_evidence_capture"
        value["existing_work_context"] = exact_event_context()
        self.assert_valid(PAGE_TARGET, value)

        value["existing_work_context"]["contract_version"] = None
        self.assert_invalid(PAGE_TARGET, value)

    def test_page_target_preserves_exact_existing_support_process_context(self) -> None:
        value = valid_page_target()
        value["page_purpose"] = "support_process_evidence_capture"
        value["existing_work_context"] = exact_support_process_context()
        self.assert_valid(PAGE_TARGET, value)

    def test_page_target_entry_layout_uses_stable_page_local_keys(self) -> None:
        single = valid_page_target()
        single["entry_layout"]["entry_keys"] = ["row_01", "row_02"]
        self.assert_invalid(PAGE_TARGET, single)

        multi = valid_page_target()
        multi["page_purpose"] = "multi_entry_event_capture"
        multi["entry_layout"] = {
            "mode": "multi_entry",
            "entry_keys": ["row_01", "row_02", "row_03"],
        }
        self.assert_valid(PAGE_TARGET, multi)

        duplicate = deepcopy(multi)
        duplicate["entry_layout"]["entry_keys"] = ["row_01", "row_01"]
        self.assert_invalid(PAGE_TARGET, duplicate)

        too_small = deepcopy(multi)
        too_small["entry_layout"]["entry_keys"] = ["row_01"]
        self.assert_invalid(PAGE_TARGET, too_small)

    def test_multi_entry_event_purpose_requires_multi_entry_layout(self) -> None:
        value = valid_page_target()
        value["page_purpose"] = "multi_entry_event_capture"
        self.assert_invalid(PAGE_TARGET, value)

        value["entry_layout"] = {
            "mode": "multi_entry",
            "entry_keys": ["row_01", "row_02"],
        }
        self.assert_valid(PAGE_TARGET, value)

    def test_page_target_capture_mode_is_closed_and_mechanical(self) -> None:
        value = valid_page_target()
        for mode in (
            "text_recognition",
            "handwriting_recognition",
            "mark_recognition",
            "mixed_recognition",
            "manual_transcription",
        ):
            with self.subTest(mode=mode):
                candidate = deepcopy(value)
                candidate["capture_mode"] = mode
                self.assert_valid(PAGE_TARGET, candidate)

        value["capture_mode"] = "automatic_judgment"
        self.assert_invalid(PAGE_TARGET, value)

    def test_capture_schemas_declare_named_application_invariants(self) -> None:
        required = {
            "schemas/v1/capture/capture-batch.schema.json": {
                "capture_batch.canonical_owner_path",
                "capture_batch.non_domain_work_root",
            },
            "schemas/v1/capture/page-target.schema.json": {
                "page_target.core_route_exact_target",
                "page_target.registration_before_render",
                "page_target.semantic_immutability_after_registration",
                "page_target.no_domain_preallocation",
            },
            "schemas/v1/capture/page-record.schema.json": {
                "page_record.core_route_exact_target",
                "page_record.retained_source_exactness",
                "page_record.idempotent_same_source_same_route",
                "page_record.no_automatic_domain_materialization",
            },
        }
        for relative_path, required_ids in required.items():
            with self.subTest(path=relative_path):
                schema = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
                invariants = schema.get("x-portia-application-invariants")
                self.assertIsInstance(invariants, list)
                ids = {
                    invariant.get("id")
                    for invariant in invariants
                    if isinstance(invariant, dict)
                }
                self.assertTrue(required_ids.issubset(ids))
                for invariant in invariants:
                    self.assertIsInstance(invariant, dict)
                    self.assertIsInstance(invariant.get("id"), str)
                    self.assertTrue(invariant.get("id"))
                    self.assertIsInstance(invariant.get("description"), str)
                    self.assertTrue(invariant.get("description"))

    def test_page_record_binds_route_and_retained_physical_page(self) -> None:
        self.assert_valid(PAGE_RECORD, valid_page_record())

        for missing in ("route_id", "source_ref", "page_target_id"):
            with self.subTest(missing=missing):
                candidate = valid_page_record()
                del candidate[missing]
                self.assert_invalid(PAGE_RECORD, candidate)

    def test_page_record_requires_positive_physical_source_page(self) -> None:
        value = valid_page_record()
        value["source_ref"]["source_page_number"] = 0
        self.assert_invalid(PAGE_RECORD, value)

    def test_page_record_requires_lowercase_sha256(self) -> None:
        value = valid_page_record()
        value["source_ref"]["source_sha256"] = "A" * 64
        self.assert_invalid(PAGE_RECORD, value)

        value = valid_page_record()
        value["source_ref"]["source_sha256"] = "a" * 63
        self.assert_invalid(PAGE_RECORD, value)

    def test_page_record_failure_detail_is_state_bound(self) -> None:
        failed = valid_page_record()
        failed["processing_state"] = "failed"
        self.assert_invalid(PAGE_RECORD, failed)

        failed["failure_detail"] = "decoder could not read the page image"
        self.assert_valid(PAGE_RECORD, failed)

        received = valid_page_record()
        received["failure_detail"] = "not allowed outside failed state"
        self.assert_invalid(PAGE_RECORD, received)

    def test_page_record_cannot_embed_interpretation_or_domain_truth(self) -> None:
        value = valid_page_record()
        for forbidden_field, forbidden_value in (
            ("interpretation", {"answer": "yes"}),
            ("proposal", {"record_type": "observation"}),
            ("materialized_record_id", "obs_too_early"),
        ):
            with self.subTest(field=forbidden_field):
                candidate = deepcopy(value)
                candidate[forbidden_field] = forbidden_value
                self.assert_invalid(PAGE_RECORD, candidate)


if __name__ == "__main__":
    unittest.main()
