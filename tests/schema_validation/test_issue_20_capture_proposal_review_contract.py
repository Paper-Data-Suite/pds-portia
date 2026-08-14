from __future__ import annotations

from copy import deepcopy
import unittest

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


BASE = "https://paper-data-suite.github.io/pds-portia/"
CAPTURE_PROPOSAL_ID = (
    BASE + "schemas/v1/identifiers/portia-capture-proposal-id.schema.json"
)
CAPTURE_REVIEW_ID = (
    BASE + "schemas/v1/identifiers/portia-capture-review-id.schema.json"
)
CAPTURE_PROPOSAL = BASE + "schemas/v1/capture/capture-proposal.schema.json"
CAPTURE_REVIEW = BASE + "schemas/v1/capture/capture-review.schema.json"
TIMESTAMP = "2026-08-14T11:30:00-04:00"
SYSTEM_AGENT = {"type": "system_process", "process_id": "paper_capture_test"}
HUMAN_REVIEWER = {"kind": "local_operator", "display_label": "Synthetic Reviewer"}


def valid_proposal() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "capture_proposal",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_record_id": "prec_returned_01",
        "proposal_id": "cprp_proposal_01",
        "interpretation_ref": {
            "contract_version": "1",
            "interpretation_id": "pint_interp_01",
            "generation": 1,
        },
        "entry_key": "entry",
        "target": {
            "record_kind": "event",
            "contract_version": "2",
            "context": {"kind": "new_work"},
        },
        "field_bindings": [
            {
                "target_path": "/location_text",
                "source_field": {
                    "field_key": "location_text",
                    "value_source": "candidate_literal",
                },
            }
        ],
        "review_flags": [],
        "proposed_at": TIMESTAMP,
        "proposed_by": deepcopy(SYSTEM_AGENT),
        "created_at": TIMESTAMP,
        "created_by": deepcopy(SYSTEM_AGENT),
    }


def valid_review() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "capture_review",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_record_id": "prec_returned_01",
        "review_id": "crev_review_01",
        "review_sequence": 1,
        "proposal_ref": {
            "contract_version": "1",
            "proposal_id": "cprp_proposal_01",
        },
        "interpretation_ref": {
            "contract_version": "1",
            "interpretation_id": "pint_interp_01",
            "generation": 1,
        },
        "entry_key": "entry",
        "reviewer": deepcopy(HUMAN_REVIEWER),
        "disposition": "accepted",
        "field_reviews": [],
        "reason_codes": [],
        "reviewed_at": TIMESTAMP,
        "created_at": TIMESTAMP,
        "created_by": deepcopy(SYSTEM_AGENT),
    }


class Issue20CaptureProposalReviewContractTests(unittest.TestCase):
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

    def test_identifiers_are_distinct_opaque_capture_families(self) -> None:
        self.assert_valid(CAPTURE_PROPOSAL_ID, "cprp_proposal_01")
        self.assert_invalid(CAPTURE_PROPOSAL_ID, "crev_proposal_01")
        self.assert_valid(CAPTURE_REVIEW_ID, "crev_review_01")
        self.assert_invalid(CAPTURE_REVIEW_ID, "rvw_review_01")

    def test_valid_proposal_references_candidate_without_copying_value(self) -> None:
        self.assert_valid(CAPTURE_PROPOSAL, valid_proposal())

    def test_proposal_target_supports_exact_existing_work_and_record_context(self) -> None:
        value = valid_proposal()
        value["target"]["record_kind"] = "account"
        value["target"]["contract_version"] = "2"
        value["target"]["context"] = {
            "kind": "existing_work",
            "work_ref": {
                "module_id": "portia",
                "class_id": "class_english10_p2",
                "work_id": "evt_event_01",
                "work_kind": "event",
                "contract_version": "2",
            },
        }
        self.assert_valid(CAPTURE_PROPOSAL, value)

        value["target"]["context"] = {
            "kind": "existing_record",
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
        }
        self.assert_valid(CAPTURE_PROPOSAL, value)

    def test_proposal_record_kind_is_closed(self) -> None:
        value = valid_proposal()
        value["target"]["record_kind"] = "automatic_finding"
        self.assert_invalid(CAPTURE_PROPOSAL, value)

    def test_new_work_context_is_only_for_portia_work_root_families(self) -> None:
        value = valid_proposal()
        value["target"]["record_kind"] = "account"
        self.assert_invalid(CAPTURE_PROPOSAL, value)

        value["target"]["record_kind"] = "support_process"
        self.assert_valid(CAPTURE_PROPOSAL, value)

    def test_proposal_binding_requires_target_path_and_source_reference(self) -> None:
        value = valid_proposal()
        del value["field_bindings"][0]["target_path"]
        self.assert_invalid(CAPTURE_PROPOSAL, value)

        value = valid_proposal()
        value["field_bindings"][0]["source_field"]["value_source"] = "truth"
        self.assert_invalid(CAPTURE_PROPOSAL, value)

    def test_proposal_rejects_copied_candidate_review_and_materialization_payload(self) -> None:
        forbidden = (
            ("candidate_literal", "Room 214"),
            ("confirmed_value", "Room 214"),
            ("reviewer", deepcopy(HUMAN_REVIEWER)),
            ("review_disposition", "accepted"),
            ("canonical_record_id", "evt_fabricated"),
            ("source_bytes", "base64-not-allowed"),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_proposal()
                value[field] = field_value
                self.assert_invalid(CAPTURE_PROPOSAL, value)

    def test_human_resolution_required_is_explicit_binding_mode(self) -> None:
        value = valid_proposal()
        value["field_bindings"][0]["source_field"]["value_source"] = (
            "human_resolution_required"
        )
        value["review_flags"] = ["ambiguous_source"]
        self.assert_valid(CAPTURE_PROPOSAL, value)

    def test_accepted_review_is_attributable_and_contains_no_correction(self) -> None:
        self.assert_valid(CAPTURE_REVIEW, valid_review())

        value = valid_review()
        value["reviewer"] = deepcopy(SYSTEM_AGENT)
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_accepted_review_forbids_field_reviews_and_reason_codes(self) -> None:
        value = valid_review()
        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "accept_candidate"}
        ]
        self.assert_invalid(CAPTURE_REVIEW, value)

        value = valid_review()
        value["reason_codes"] = ["manual_check"]
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_corrected_and_accepted_requires_human_correction_or_selection(self) -> None:
        value = valid_review()
        value["disposition"] = "corrected_and_accepted"
        value["field_reviews"] = [
            {
                "target_path": "/location_text",
                "decision": "correct",
                "confirmed_value": "Room 217",
            }
        ]
        self.assert_valid(CAPTURE_REVIEW, value)

        del value["field_reviews"][0]["confirmed_value"]
        self.assert_invalid(CAPTURE_REVIEW, value)

        value = valid_review()
        value["disposition"] = "corrected_and_accepted"
        value["field_reviews"] = [
            {
                "target_path": "/location_text",
                "decision": "select_alternative",
                "alternative_index": 1,
            }
        ]
        self.assert_valid(CAPTURE_REVIEW, value)

    def test_selected_alternative_and_corrected_value_remain_mutually_exclusive(self) -> None:
        value = valid_review()
        value["disposition"] = "corrected_and_accepted"
        value["field_reviews"] = [
            {
                "target_path": "/location_text",
                "decision": "select_alternative",
                "alternative_index": 0,
                "confirmed_value": "Room 214",
            }
        ]
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_rejected_review_requires_reason_and_no_field_decisions(self) -> None:
        value = valid_review()
        value["disposition"] = "rejected"
        value["reason_codes"] = ["not_semantically_valid"]
        self.assert_valid(CAPTURE_REVIEW, value)

        value["reason_codes"] = []
        self.assert_invalid(CAPTURE_REVIEW, value)

        value["reason_codes"] = ["not_semantically_valid"]
        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "leave_unresolved"}
        ]
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_unresolved_review_requires_unreadable_or_unresolved_field(self) -> None:
        value = valid_review()
        value["disposition"] = "unresolved"
        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "mark_unreadable"}
        ]
        value["reason_codes"] = ["source_unclear"]
        self.assert_valid(CAPTURE_REVIEW, value)

        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "accept_candidate"}
        ]
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_review_history_is_immutable_sequence_not_mutable_latest_state(self) -> None:
        value = valid_review()
        value["review_sequence"] = 2
        value["review_id"] = "crev_review_02"
        self.assert_invalid(CAPTURE_REVIEW, value)

        value["predecessor_review_id"] = "crev_review_01"
        self.assert_valid(CAPTURE_REVIEW, value)

        value = valid_review()
        value["predecessor_review_id"] = "crev_review_00"
        self.assert_invalid(CAPTURE_REVIEW, value)

    def test_review_rejects_canonical_materialization_and_queue_mutation_fields(self) -> None:
        forbidden = (
            ("canonical_record_id", "evt_fabricated"),
            ("materialized_records", []),
            ("materialization_state", "complete"),
            ("latest", True),
            ("quarantined", True),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_review()
                value[field] = field_value
                self.assert_invalid(CAPTURE_REVIEW, value)

    def test_proposal_and_review_declare_named_application_invariants(self) -> None:
        proposal_schema = self.store.schemas_by_id[CAPTURE_PROPOSAL]
        proposal_ids = {
            item["id"]
            for item in proposal_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "capture_proposal.lineage_exactness",
                "capture_proposal.no_candidate_value_duplication",
                "capture_proposal.no_identity_or_judgment_inference",
                "capture_proposal.review_required_before_materialization",
            }
            <= proposal_ids
        )

        review_schema = self.store.schemas_by_id[CAPTURE_REVIEW]
        review_ids = {
            item["id"]
            for item in review_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "capture_review.reviewer_human_and_eligible",
                "capture_review.correction_preserves_candidate",
                "capture_review.disposition_not_truth",
                "capture_review.no_automatic_materialization",
            }
            <= review_ids
        )


if __name__ == "__main__":
    unittest.main()
