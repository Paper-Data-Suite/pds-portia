from __future__ import annotations

import unittest
from copy import deepcopy

try:
    from .schema_support import build_schema_store
except ImportError:
    from schema_support import build_schema_store


BASE = "https://paper-data-suite.github.io/pds-portia/"
PAPER_INTERPRETATION_ID = (
    BASE
    + "schemas/v1/identifiers/portia-paper-interpretation-id.schema.json"
)
PAPER_INTERPRETATION = (
    BASE + "schemas/v1/capture/paper-interpretation.schema.json"
)

TIMESTAMP = "2026-08-13T19:30:00-04:00"
LAYOUT_FINGERPRINT = "a" * 64
AGENT = {"type": "system_process", "process_id": "paper_capture_test"}


def valid_interpretation() -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "paper_interpretation",
        "module_id": "portia",
        "class_id": "class_english10_p2",
        "work_id": "cbat_batch_01",
        "page_target_id": "ptgt_page_01",
        "page_record_id": "prec_returned_01",
        "interpretation_id": "pint_interp_01",
        "generation": 1,
        "layout_snapshot": {
            "template_id": "portia_incident_form",
            "template_version": "1",
            "layout_version": "layout_1",
            "capture_spec_version": "capture_2",
            "layout_fingerprint": LAYOUT_FINGERPRINT,
            "page_role": "incident_form",
            "page_ordinal": 1,
        },
        "interpreter_profile": {
            "interpreter_id": "portia_capture_interpreter",
            "interpreter_version": "1.2.0",
            "mapping_profile_id": "incident_form_mapping",
            "mapping_version": "2",
        },
        "interpretation_status": "complete",
        "limitation_codes": [],
        "entries": {
            "entry": {
                "entry_state": "candidate",
                "mapped_record_kind": "event",
                "fields": {
                    "location_text": {
                        "capture_method": "handwriting_recognition",
                        "recognition_state": "candidate_detected",
                        "candidate_literal": "Room 214",
                        "normalized_value": "Room 214",
                        "confidence": 0.91,
                    },
                    "family_contacted": {
                        "capture_method": "mark_recognition",
                        "recognition_state": "unmarked",
                    },
                },
            }
        },
        "interpreted_at": TIMESTAMP,
        "interpreted_by": deepcopy(AGENT),
        "created_at": TIMESTAMP,
        "created_by": deepcopy(AGENT),
    }


class Issue20PaperInterpretationContractTests(unittest.TestCase):
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

    def test_interpretation_identifier_is_opaque_and_prefix_scoped(self) -> None:
        self.assert_valid(PAPER_INTERPRETATION_ID, "pint_interp_01")
        self.assert_invalid(PAPER_INTERPRETATION_ID, "prec_interp_01")
        self.assert_invalid(PAPER_INTERPRETATION_ID, "pint_event/01")

    def test_valid_interpretation_preserves_candidates_without_confirmation(self) -> None:
        self.assert_valid(PAPER_INTERPRETATION, valid_interpretation())

    def test_complete_and_partial_processing_preserve_coverage_limits(self) -> None:
        value = valid_interpretation()
        value["limitation_codes"] = ["region_unreadable"]
        self.assert_invalid(PAPER_INTERPRETATION, value)

        value["interpretation_status"] = "partial"
        self.assert_valid(PAPER_INTERPRETATION, value)

        value["limitation_codes"] = []
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_blank_unreadable_and_candidate_entries_are_distinct(self) -> None:
        value = valid_interpretation()
        value["entries"] = {
            "row_01": {"entry_state": "blank"},
            "row_02": {"entry_state": "unreadable"},
            "row_03": {
                "entry_state": "candidate",
                "mapped_record_kind": "event",
                "fields": {
                    "student_name": {
                        "capture_method": "handwriting_recognition",
                        "recognition_state": "unreadable",
                    }
                },
            },
        }
        self.assert_valid(PAPER_INTERPRETATION, value)

        value["entries"]["row_01"]["fields"] = {
            "field": {
                "capture_method": "text_recognition",
                "recognition_state": "blank",
            }
        }
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_field_states_preserve_blank_unmarked_unreadable_and_candidate(self) -> None:
        for state in ("blank", "unmarked", "unreadable"):
            with self.subTest(state=state):
                value = valid_interpretation()
                value["entries"]["entry"]["fields"]["location_text"] = {
                    "capture_method": "text_recognition",
                    "recognition_state": state,
                }
                self.assert_valid(PAPER_INTERPRETATION, value)

                value["entries"]["entry"]["fields"]["location_text"][
                    "candidate_literal"
                ] = "fabricated"
                self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_candidate_detected_requires_literal_and_keeps_normalization_optional(self) -> None:
        value = valid_interpretation()
        field = value["entries"]["entry"]["fields"]["location_text"]
        del field["candidate_literal"]
        self.assert_invalid(PAPER_INTERPRETATION, value)

        field["candidate_literal"] = "18"
        field["normalized_value"] = 18
        self.assert_valid(PAPER_INTERPRETATION, value)

    def test_ambiguous_field_requires_alternatives_and_no_winner(self) -> None:
        value = valid_interpretation()
        value["entries"]["entry"]["fields"]["location_text"] = {
            "capture_method": "handwriting_recognition",
            "recognition_state": "ambiguous",
            "alternatives": [
                {"candidate_literal": "Room 214", "confidence": 0.51},
                {"candidate_literal": "Room 217", "confidence": 0.47},
            ],
        }
        self.assert_valid(PAPER_INTERPRETATION, value)

        value["entries"]["entry"]["fields"]["location_text"][
            "candidate_literal"
        ] = "Room 214"
        self.assert_invalid(PAPER_INTERPRETATION, value)

        value = valid_interpretation()
        value["entries"]["entry"]["fields"]["location_text"] = {
            "capture_method": "handwriting_recognition",
            "recognition_state": "ambiguous",
            "alternatives": [{"candidate_literal": "Room 214"}],
        }
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_confidence_is_bounded(self) -> None:
        value = valid_interpretation()
        value["entries"]["entry"]["fields"]["location_text"]["confidence"] = 1.01
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_mapping_target_kind_is_closed_but_does_not_materialize(self) -> None:
        value = valid_interpretation()
        for kind in ("account", "observation", "fidelity", "repair"):
            with self.subTest(kind=kind):
                candidate = deepcopy(value)
                candidate["entries"]["entry"]["mapped_record_kind"] = kind
                self.assert_valid(PAPER_INTERPRETATION, candidate)

        value["entries"]["entry"]["mapped_record_kind"] = "automatic_finding"
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_interpretation_rejects_review_and_canonical_materialization_fields(self) -> None:
        forbidden = (
            ("reviewer", {"type": "local_operator", "display_label": "Reviewer"}),
            ("review_disposition", "accepted"),
            ("confirmed_value", "Room 214"),
            ("canonical_record_id", "evt_fabricated"),
            ("materialized_records", []),
            ("source_bytes", "base64-not-allowed"),
        )
        for field, field_value in forbidden:
            with self.subTest(field=field):
                value = valid_interpretation()
                value[field] = field_value
                self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_interpretation_requires_positive_immutable_generation_identity(self) -> None:
        value = valid_interpretation()
        value["generation"] = 0
        self.assert_invalid(PAPER_INTERPRETATION, value)

        value = valid_interpretation()
        del value["interpreter_profile"]["mapping_version"]
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_layout_snapshot_is_structurally_exact(self) -> None:
        value = valid_interpretation()
        value["layout_snapshot"]["layout_fingerprint"] = "B" * 64
        self.assert_invalid(PAPER_INTERPRETATION, value)

        value = valid_interpretation()
        del value["layout_snapshot"]["capture_spec_version"]
        self.assert_invalid(PAPER_INTERPRETATION, value)

    def test_interpretation_declares_named_application_invariants(self) -> None:
        schema = self.store.schemas_by_id[PAPER_INTERPRETATION]
        invariants = schema.get("x-portia-application-invariants", [])
        ids = {
            invariant["id"]
            for invariant in invariants
            if isinstance(invariant, dict) and "id" in invariant
        }
        required = {
            "paper_interpretation.page_record_exactness",
            "paper_interpretation.layout_snapshot_exactness",
            "paper_interpretation.same_profile_replay_idempotent",
            "paper_interpretation.uncertainty_is_not_negative",
            "paper_interpretation.candidate_not_confirmed",
            "paper_interpretation.no_identity_or_judgment_inference",
            "paper_interpretation.no_automatic_materialization",
        }
        self.assertTrue(required <= ids)


if __name__ == "__main__":
    unittest.main()
