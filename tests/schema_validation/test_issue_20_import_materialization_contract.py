from __future__ import annotations

import unittest
from copy import deepcopy

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


IMPORT_MATERIALIZATION = (
    "https://paper-data-suite.github.io/pds-portia/"
    "schemas/v1/imports/import-materialization.schema.json"
)
TIMESTAMP = "2026-08-14T13:45:00-04:00"
SYSTEM_AGENT = {
    "type": "system_process",
    "process_id": "import_materializer",
}
DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def valid_materialization() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "import_materialization",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "import_batch_ref": {
            "contract_version": "1",
            "import_batch_id": "ibat_batch_01",
            "import_identity_digest": DIGEST_A,
        },
        "source_record_ref": {
            "contract_version": "1",
            "source_record_id": "isrc_record_01",
            "source_record_identity_digest": DIGEST_B,
        },
        "proposal_ref": {
            "contract_version": "1",
            "proposal_id": "iprp_proposal_01",
            "proposal_identity_digest": DIGEST_C,
        },
        "review_ref": {
            "contract_version": "1",
            "review_id": "irev_review_01",
            "review_sequence": 1,
        },
        "operation_journal_ref": {
            "operation_id": "op_import_materialize_01",
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


class Issue20ImportMaterializationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = build_schema_store()
        cls.validator = cls.store.validator_for_id(IMPORT_MATERIALIZATION)

    def assert_valid(self, value: object) -> None:
        errors = list(self.validator.iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def assert_invalid(self, value: object) -> None:
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_valid_completed_import_materialization_receipt(self) -> None:
        self.assert_valid(valid_materialization())

    def test_materialization_reuses_operation_identity_without_new_import_id(self) -> None:
        value = valid_materialization()
        value["materialization_id"] = "imat_should_not_exist"
        self.assert_invalid(value)

    def test_import_batch_ref_is_exact_and_digest_bound(self) -> None:
        value = valid_materialization()
        value["import_batch_ref"]["contract_version"] = "latest"
        self.assert_invalid(value)

        value = valid_materialization()
        value["import_batch_ref"]["import_identity_digest"] = "A" * 64
        self.assert_invalid(value)

        value = valid_materialization()
        value["import_batch_ref"]["import_batch_id"] = "cbat_paper_batch"
        self.assert_invalid(value)

    def test_source_record_ref_is_exact_and_digest_bound(self) -> None:
        value = valid_materialization()
        value["source_record_ref"]["contract_version"] = "2"
        self.assert_invalid(value)

        value = valid_materialization()
        value["source_record_ref"]["source_record_identity_digest"] = "short"
        self.assert_invalid(value)

        value = valid_materialization()
        value["source_record_ref"]["source_record_id"] = "prec_paper_page"
        self.assert_invalid(value)

    def test_proposal_ref_preserves_exact_replay_identity(self) -> None:
        value = valid_materialization()
        value["proposal_ref"]["contract_version"] = None
        self.assert_invalid(value)

        value = valid_materialization()
        value["proposal_ref"]["proposal_id"] = "cprp_paper_proposal"
        self.assert_invalid(value)

        value = valid_materialization()
        value["proposal_ref"]["proposal_identity_digest"] = "d" * 63
        self.assert_invalid(value)

    def test_review_ref_is_exact_import_review_and_sequence(self) -> None:
        value = valid_materialization()
        value["review_ref"]["contract_version"] = "2"
        self.assert_invalid(value)

        value = valid_materialization()
        value["review_ref"]["review_sequence"] = 0
        self.assert_invalid(value)

        value = valid_materialization()
        value["review_ref"]["review_id"] = "crev_paper_review"
        self.assert_invalid(value)

        value = valid_materialization()
        value["review_ref"]["review_id"] = "rvw_domain_review"
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

    def test_receipt_rejects_paper_source_and_copied_import_payloads(self) -> None:
        forbidden = (
            ("route_id", "route_01"),
            ("page_record_id", "prec_page_01"),
            ("source_record_key", "student-1001"),
            ("source_fields", {"student_name": "Synthetic Student"}),
            ("candidate_value", "Room 214"),
            ("confirmed_value", "Room 217"),
            ("review_disposition", "accepted"),
            ("creation_source", {"type": "import", "source_label": "sis"}),
            ("canonical_payload", {"event_id": "evt_event_01"}),
            ("temporary_path", "tmp/import.csv"),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_materialization()
                value[field] = field_value
                self.assert_invalid(value)

    def test_materialization_declares_required_application_invariants(self) -> None:
        schema = self.store.schemas_by_id[IMPORT_MATERIALIZATION]
        invariant_ids = {
            item["id"]
            for item in schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "import_materialization.lineage_exactness",
                "import_materialization.batch_identity_exactness",
                "import_materialization.source_record_identity_exactness",
                "import_materialization.review_must_authorize_next_step",
                "import_materialization.review_is_not_domain_judgment",
                "import_materialization.operation_reuse",
                "import_materialization.operation_journal_exactness",
                "import_materialization.lock_and_preflight_reuse",
                "import_materialization.import_creation_source",
                "import_materialization.source_artifact_alignment",
                "import_materialization.no_duplicate_canonical_records",
                "import_materialization.unchanged_replay_idempotent",
                "import_materialization.missing_later_source_not_deletion",
                "import_materialization.receipt_after_canonical_acceptance",
                "import_materialization.no_import_time_as_domain_time",
                "import_materialization.no_raw_source_payload",
            }
            <= invariant_ids
        )
        for item in schema["x-portia-application-invariants"]:
            self.assertIsInstance(item, dict)
            self.assertTrue(item.get("id"))
            self.assertTrue(item.get("description"))


if __name__ == "__main__":
    unittest.main()
