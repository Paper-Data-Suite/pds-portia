from __future__ import annotations

import unittest
from copy import deepcopy

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


BASE = "https://paper-data-suite.github.io/pds-portia/schemas/v1/"
IMPORT_PROPOSAL = BASE + "imports/import-proposal.schema.json"
IMPORT_REVIEW = BASE + "imports/import-review.schema.json"
IMPORT_PROPOSAL_ID = BASE + "identifiers/portia-import-proposal-id.schema.json"
IMPORT_REVIEW_ID = BASE + "identifiers/portia-import-review-id.schema.json"
TIMESTAMP = "2026-08-14T13:05:00-04:00"
SHA_A = "a" * 64
SYSTEM_AGENT = {
    "type": "system_process",
    "process_id": "structured_import_mapping_test",
}
HUMAN_REVIEWER = {
    "kind": "local_operator",
    "display_label": "Synthetic Import Reviewer",
}


def valid_proposal() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "import_proposal",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "import_batch_id": "ibat_attempt_01",
        "source_record_id": "isrc_observation_01",
        "proposal_id": "iprp_event_01",
        "proposal_key": "event",
        "proposal_identity_digest": SHA_A,
        "target": {
            "record_kind": "event",
            "contract_version": "2",
            "context": {"kind": "new_work"},
        },
        "field_bindings": [
            {
                "target_path": "/location_text",
                "source_field_key": "location",
                "value_source": "source_value",
            },
            {
                "target_path": "/occurred_at",
                "source_field_key": "occurred_date",
                "value_source": "transformed_candidate",
                "transformed_candidate": "2026-08-13T09:15:00-04:00",
            },
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
        "record_type": "import_review",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "import_batch_id": "ibat_attempt_01",
        "source_record_ref": {
            "contract_version": "1",
            "source_record_id": "isrc_observation_01",
        },
        "review_id": "irev_review_01",
        "review_sequence": 1,
        "proposal_ref": {
            "contract_version": "1",
            "proposal_id": "iprp_event_01",
            "proposal_identity_digest": SHA_A,
        },
        "reviewer": deepcopy(HUMAN_REVIEWER),
        "disposition": "accepted",
        "field_reviews": [],
        "reason_codes": [],
        "reviewed_at": TIMESTAMP,
        "created_at": TIMESTAMP,
        "created_by": deepcopy(SYSTEM_AGENT),
    }


class Issue20ImportProposalReviewContractTests(unittest.TestCase):
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

    def test_identifiers_are_distinct_import_staging_families(self) -> None:
        self.assert_valid(IMPORT_PROPOSAL_ID, "iprp_proposal_01")
        self.assert_invalid(IMPORT_PROPOSAL_ID, "cprp_proposal_01")
        self.assert_valid(IMPORT_REVIEW_ID, "irev_review_01")
        self.assert_invalid(IMPORT_REVIEW_ID, "rvw_review_01")
        self.assert_invalid(IMPORT_REVIEW_ID, "crev_review_01")

    def test_valid_import_proposal(self) -> None:
        self.assert_valid(IMPORT_PROPOSAL, valid_proposal())

    def test_proposal_supports_zero_to_many_stable_proposal_keys(self) -> None:
        value = valid_proposal()
        value["proposal_key"] = "account_statement"
        value["proposal_id"] = "iprp_account_01"
        value["target"]["record_kind"] = "account"
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
        self.assert_valid(IMPORT_PROPOSAL, value)

    def test_proposal_key_is_closed_lowercase_token_not_row_position(self) -> None:
        value = valid_proposal()
        value["proposal_key"] = "Row 7"
        self.assert_invalid(IMPORT_PROPOSAL, value)

        value = valid_proposal()
        value["row_number"] = 7
        self.assert_invalid(IMPORT_PROPOSAL, value)

    def test_new_work_context_only_allows_event_or_support_process(self) -> None:
        value = valid_proposal()
        value["target"]["record_kind"] = "account"
        self.assert_invalid(IMPORT_PROPOSAL, value)

        value["target"]["record_kind"] = "support_process"
        self.assert_valid(IMPORT_PROPOSAL, value)

    def test_existing_record_context_preserves_exact_reference(self) -> None:
        value = valid_proposal()
        value["target"] = {
            "record_kind": "observation",
            "contract_version": "2",
            "context": {
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
                        "record_kind": "observation",
                        "record_id": "obs_observation_01",
                        "contract_version": "2",
                    },
                },
            },
        }
        self.assert_valid(IMPORT_PROPOSAL, value)

    def test_source_value_binding_references_source_without_copy(self) -> None:
        value = valid_proposal()
        value["field_bindings"] = [
            {
                "target_path": "/location_text",
                "source_field_key": "location",
                "value_source": "source_value",
            }
        ]
        self.assert_valid(IMPORT_PROPOSAL, value)

        value["field_bindings"][0]["transformed_candidate"] = "Room 214"
        self.assert_invalid(IMPORT_PROPOSAL, value)

    def test_transformed_candidate_required_only_for_transformed_mode(self) -> None:
        value = valid_proposal()
        del value["field_bindings"][1]["transformed_candidate"]
        self.assert_invalid(IMPORT_PROPOSAL, value)

        value["field_bindings"][1]["transformed_candidate"] = None
        self.assert_valid(IMPORT_PROPOSAL, value)

    def test_human_resolution_required_carries_no_candidate_value(self) -> None:
        value = valid_proposal()
        value["field_bindings"] = [
            {
                "target_path": "/participants/0/person_ref",
                "source_field_key": "student_name",
                "value_source": "human_resolution_required",
            }
        ]
        value["review_flags"] = ["ambiguous_identity"]
        self.assert_valid(IMPORT_PROPOSAL, value)

        value["field_bindings"][0]["transformed_candidate"] = "student_01"
        self.assert_invalid(IMPORT_PROPOSAL, value)

    def test_proposal_rejects_paper_review_and_materialization_fields(self) -> None:
        forbidden = (
            ("route_id", "route_01"),
            ("page_record_id", "prec_page_01"),
            ("paper_interpretation_id", "pint_01"),
            ("reviewer", deepcopy(HUMAN_REVIEWER)),
            ("review_disposition", "accepted"),
            ("canonical_record_id", "evt_fabricated"),
            ("creation_source", {"type": "import"}),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_proposal()
                value[field] = field_value
                self.assert_invalid(IMPORT_PROPOSAL, value)

    def test_accepted_import_review_is_human_attributable(self) -> None:
        self.assert_valid(IMPORT_REVIEW, valid_review())

        value = valid_review()
        value["reviewer"] = deepcopy(SYSTEM_AGENT)
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_accepted_review_forbids_field_decisions_and_reasons(self) -> None:
        value = valid_review()
        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "accept_candidate"}
        ]
        self.assert_invalid(IMPORT_REVIEW, value)

        value = valid_review()
        value["reason_codes"] = ["manual_check"]
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_corrected_and_accepted_requires_confirmed_human_value(self) -> None:
        value = valid_review()
        value["disposition"] = "corrected_and_accepted"
        value["field_reviews"] = [
            {
                "target_path": "/occurred_at",
                "decision": "correct",
                "confirmed_value": "2026-08-13T09:20:00-04:00",
            },
            {
                "target_path": "/location_text",
                "decision": "accept_candidate",
            },
        ]
        self.assert_valid(IMPORT_REVIEW, value)

        del value["field_reviews"][0]["confirmed_value"]
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_unresolved_review_requires_explicit_unresolved_field(self) -> None:
        value = valid_review()
        value["disposition"] = "unresolved"
        value["field_reviews"] = [
            {
                "target_path": "/participants/0/person_ref",
                "decision": "leave_unresolved",
            }
        ]
        value["reason_codes"] = ["ambiguous_identity"]
        self.assert_valid(IMPORT_REVIEW, value)

        value["field_reviews"] = [
            {"target_path": "/location_text", "decision": "accept_candidate"}
        ]
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_rejected_review_requires_reason_and_no_field_decisions(self) -> None:
        value = valid_review()
        value["disposition"] = "rejected"
        value["reason_codes"] = ["mapping_not_semantically_valid"]
        self.assert_valid(IMPORT_REVIEW, value)

        value["reason_codes"] = []
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_review_sequence_preserves_corrections_without_mutable_latest(self) -> None:
        value = valid_review()
        value["review_sequence"] = 2
        value["review_id"] = "irev_review_02"
        self.assert_invalid(IMPORT_REVIEW, value)

        value["predecessor_review_id"] = "irev_review_01"
        self.assert_valid(IMPORT_REVIEW, value)

        value = valid_review()
        value["predecessor_review_id"] = "irev_review_00"
        self.assert_invalid(IMPORT_REVIEW, value)

    def test_review_rejects_paper_and_canonical_materialization_fields(self) -> None:
        forbidden = (
            ("page_record_id", "prec_page_01"),
            ("capture_review_id", "crev_review_01"),
            ("canonical_record_id", "evt_fabricated"),
            ("materialized_records", []),
            ("latest", True),
            ("deleted", True),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_review()
                value[field] = field_value
                self.assert_invalid(IMPORT_REVIEW, value)

    def test_import_proposal_and_review_declare_required_invariants(self) -> None:
        proposal_schema = self.store.schemas_by_id[IMPORT_PROPOSAL]
        proposal_ids = {
            item["id"]
            for item in proposal_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "import_proposal.lineage_exactness",
                "import_proposal.identity_digest",
                "import_proposal.no_fuzzy_identity",
                "import_proposal.review_required_before_materialization",
            }
            <= proposal_ids
        )

        review_schema = self.store.schemas_by_id[IMPORT_REVIEW]
        review_ids = {
            item["id"]
            for item in review_schema.get("x-portia-application-invariants", [])
            if isinstance(item, dict) and "id" in item
        }
        self.assertTrue(
            {
                "import_review.reviewer_human_and_eligible",
                "import_review.correction_preserves_source_and_candidate",
                "import_review.disposition_not_truth",
                "import_review.no_automatic_materialization",
            }
            <= review_ids
        )


if __name__ == "__main__":
    unittest.main()
