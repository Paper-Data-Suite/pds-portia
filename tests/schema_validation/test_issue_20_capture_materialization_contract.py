from __future__ import annotations

import unittest
from copy import deepcopy

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


CAPTURE_MATERIALIZATION = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/capture/capture-materialization.schema.json"
)
TIMESTAMP = "2026-08-14T10:30:00-04:00"
SYSTEM_AGENT = {
    "type": "system_process",
    "process_id": "paper_capture_materializer",
}


def valid_materialization() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "capture_materialization",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_record_id": "prec_returned_01",
        "proposal_ref": {
            "contract_version": "1",
            "proposal_id": "cprp_proposal_01",
        },
        "review_ref": {
            "contract_version": "1",
            "review_id": "crev_review_01",
            "review_sequence": 1,
        },
        "operation_journal_ref": {
            "operation_id": "op_materialize_01",
            "journal_revision": 4,
            "contract_version": "1",
        },
        "canonical_results": [
            {
                "result_relation": "produced",
                "target": {
                    "kind": "work",
                    "work_ref": {
                        "module_id": "portia",
                        "class_id": "class_english10_p2",
                        "work_id": "evt_event_01",
                        "work_kind": "event",
                        "contract_version": "2",
                    },
                },
            }
        ],
        "materialized_at": TIMESTAMP,
        "recorded_at": TIMESTAMP,
        "recorded_by": deepcopy(SYSTEM_AGENT),
    }


class Issue20CaptureMaterializationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = build_schema_store()
        cls.validator = cls.store.validator_for_id(CAPTURE_MATERIALIZATION)

    def assert_valid(self, value: object) -> None:
        errors = list(self.validator.iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_invalid(self, value: object) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_valid_completed_materialization_receipt(self) -> None:
        self.assert_valid(valid_materialization())

    def test_materialization_reuses_operation_identity_without_new_capture_id(self) -> None:
        value = valid_materialization()
        value["materialization_id"] = "cmat_should_not_exist"
        self.assert_invalid(value)

    def test_review_ref_is_exact_contract_and_sequence(self) -> None:
        value = valid_materialization()
        value["review_ref"]["contract_version"] = "2"
        self.assert_invalid(value)

        value = valid_materialization()
        value["review_ref"]["review_sequence"] = 0
        self.assert_invalid(value)

        value = valid_materialization()
        value["review_ref"]["review_id"] = "rvw_domain_review"
        self.assert_invalid(value)

    def test_proposal_ref_is_exact_capture_proposal(self) -> None:
        value = valid_materialization()
        value["proposal_ref"]["contract_version"] = "latest"
        self.assert_invalid(value)

        value = valid_materialization()
        value["proposal_ref"]["proposal_id"] = "crev_wrong_family"
        self.assert_invalid(value)

    def test_operation_journal_ref_is_required_and_exact(self) -> None:
        value = valid_materialization()
        del value["operation_journal_ref"]
        self.assert_invalid(value)

        value = valid_materialization()
        value["operation_journal_ref"]["journal_revision"] = 0
        self.assert_invalid(value)

        value = valid_materialization()
        value["operation_journal_ref"]["contract_version"] = None
        self.assert_invalid(value)

    def test_materialization_requires_at_least_one_exact_canonical_result(self) -> None:
        value = valid_materialization()
        value["canonical_results"] = []
        self.assert_invalid(value)

    def test_canonical_result_supports_exact_work_record(self) -> None:
        value = valid_materialization()
        value["canonical_results"] = [
            {
                "result_relation": "produced",
                "target": {
                    "kind": "work_record",
                    "work_record_ref": {
                        "work_ref": {
                            "module_id": "portia",
                            "class_id": "class_english10_p2",
                            "work_id": "evt_event_01",
                            "work_kind": "event",
                            "contract_version": "2",
                        },
                        "record_ref": {
                            "record_kind": "account",
                            "record_id": "acct_account_01",
                            "contract_version": "2",
                        },
                    },
                },
            }
        ]
        self.assert_valid(value)

    def test_canonical_result_supports_affected_existing_representation(self) -> None:
        value = valid_materialization()
        value["canonical_results"][0]["result_relation"] = "affected"
        self.assert_valid(value)

    def test_canonical_result_relation_is_closed(self) -> None:
        value = valid_materialization()
        value["canonical_results"][0]["result_relation"] = "silently_updated"
        self.assert_invalid(value)

    def test_exact_result_contract_version_cannot_be_null(self) -> None:
        value = valid_materialization()
        value["canonical_results"][0]["target"]["work_ref"][
            "contract_version"
        ] = None
        self.assert_invalid(value)

    def test_identical_duplicate_results_are_structurally_rejected(self) -> None:
        value = valid_materialization()
        value["canonical_results"].append(deepcopy(value["canonical_results"][0]))
        self.assert_invalid(value)

    def test_receipt_rejects_copied_source_review_and_domain_payloads(self) -> None:
        forbidden = (
            ("source_bytes", "base64-not-allowed"),
            ("candidate_literal", "Room 214"),
            ("confirmed_value", "Room 217"),
            ("review_disposition", "accepted"),
            ("creation_source", {"type": "paper_capture"}),
            ("canonical_payload", {"event_id": "evt_event_01"}),
            ("temporary_path", "tmp/scan.png"),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_materialization()
                value[field] = field_value
                self.assert_invalid(value)

    def test_capture_batch_lineage_remains_non_domain_work_id(self) -> None:
        value = valid_materialization()
        value["work_id"] = "evt_event_01"
        self.assert_invalid(value)

    def test_materialization_declares_required_application_invariants(self) -> None:
        schema = self.store.schemas_by_id[CAPTURE_MATERIALIZATION]
        invariant_ids = {
            item["id"]
            for item in schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "capture_materialization.review_must_authorize_next_step",
                "capture_materialization.review_is_not_domain_judgment",
                "capture_materialization.operation_reuse",
                "capture_materialization.operation_journal_exactness",
                "capture_materialization.lock_and_preflight_reuse",
                "capture_materialization.paper_creation_source",
                "capture_materialization.paper_source_artifact",
                "capture_materialization.no_duplicate_canonical_records",
                "capture_materialization.receipt_after_canonical_acceptance",
                "capture_materialization.no_scan_time_as_domain_time",
                "capture_materialization.no_raw_source_payload",
            }
            <= invariant_ids
        )
        for item in schema["x-portia-application-invariants"]:
            self.assertIsInstance(item, dict)
            self.assertTrue(item.get("id"))
            self.assertTrue(item.get("description"))


if __name__ == "__main__":
    unittest.main()
