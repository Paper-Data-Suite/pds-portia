from __future__ import annotations

from datetime import datetime
import unittest

try:
    from .issue_22_graph_validation import (
        _canonical_path_for_record,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import load_validated_catalog_and_store
except ImportError:
    from issue_22_graph_validation import (
        _canonical_path_for_record,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import load_validated_catalog_and_store


class Issue22InconclusiveAdverseOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus, "P22-09"
        )
        cls.records = load_scenario_records(
            cls.scenario_path, cls.scenario
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)

        cls.process = cls.by_contract["support_process"][0]
        cls.support = cls.by_contract["support"][0]
        cls.implementations = {
            record.value["implementation_id"]: record
            for record in cls.by_contract["implementation"]
        }
        cls.outcomes = {
            record.value["outcome_id"]: record
            for record in cls.by_contract["outcome"]
        }
        cls.inconclusive = cls.outcomes["out_p22_inconclusive_001"]
        cls.adverse = cls.outcomes["out_p22_adverse_001"]

    def test_corpus_registers_p22_09_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"] for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-09", implemented)
        self.assertNotIn(
            "P22-09", self.corpus["planned_positive_scenarios"]
        )

    def test_p22_09_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_09_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_09_has_three_event_works_and_one_support_process(self) -> None:
        self.assertEqual(len(self.by_contract["event"]), 3)
        self.assertEqual(len(self.by_contract["support_process"]), 1)
        event_ids = {
            record.value["work_id"] for record in self.by_contract["event"]
        }
        self.assertEqual(len(event_ids), 3)
        self.assertNotIn(self.process.value["work_id"], event_ids)

    def test_p22_09_support_process_initiates_from_baseline_event(self) -> None:
        initiation = self.process.value["initiation"]
        self.assertEqual(initiation["kind"], "event_context")
        self.assertEqual(
            initiation["event_ref"]["work_id"],
            "evt_p22_outcome_baseline_001",
        )
        self.assertEqual(initiation["event_ref"]["contract_version"], "2")

    def test_p22_09_outcomes_share_exact_target_and_evaluator(self) -> None:
        self.assertEqual(
            self.inconclusive.value["target"], self.adverse.value["target"]
        )
        self.assertEqual(
            self.inconclusive.value["evaluator"],
            self.adverse.value["evaluator"],
        )
        self.assertEqual(
            self.inconclusive.value["evaluator"]["kind"],
            "support_process_participant",
        )

    def test_p22_09_inconclusive_outcome_preserves_missingness(self) -> None:
        value = self.inconclusive.value
        self.assertEqual(value["scope"]["kind"], "support_response_review")
        self.assertEqual(value["result"], "unable_to_determine")
        self.assertIn(
            {"kind": "insufficient_observation_opportunity"},
            value["limitations"],
        )
        self.assertNotIn("result_detail", value)
        summary = value["summary"].lower()
        self.assertIn("not a negative result", summary)
        self.assertIn("insufficient to determine", summary)

    def test_p22_09_inconclusive_basis_is_exact_and_bounded(self) -> None:
        basis = self.inconclusive.value["basis"]
        roles = {entry["role"] for entry in basis}
        self.assertEqual(
            roles, {"baseline", "current_period", "implementation_context"}
        )
        refs = [entry["locator"]["record_ref"] for entry in basis]
        self.assertEqual(
            {ref["record_ref"]["record_kind"] for ref in refs},
            {"observation", "implementation"},
        )
        self.assertIn(
            "evt_p22_outcome_limited_001",
            {ref["work_ref"]["work_id"] for ref in refs},
        )

    def test_p22_09_adverse_review_uses_bounded_coverage(self) -> None:
        value = self.adverse.value
        self.assertEqual(
            value["scope"]["kind"],
            "unintended_or_adverse_effect_review",
        )
        self.assertEqual(value["result"], "change_observed")
        self.assertEqual(
            value["scope"]["coverage"]["coverage_kind"],
            "direct_observation",
        )
        self.assertIn(
            "no claim extends beyond that window",
            value["scope"]["coverage"]["coverage_description"].lower(),
        )
        self.assertNotIn("result_detail", value)

    def test_p22_09_adverse_basis_uses_later_event_and_implementation(self) -> None:
        refs = [
            entry["locator"]["record_ref"]
            for entry in self.adverse.value["basis"]
        ]
        work_ids = {ref["work_ref"]["work_id"] for ref in refs}
        self.assertEqual(
            work_ids,
            {
                "evt_p22_outcome_adverse_001",
                "sup_p22_outcome_review_001",
            },
        )
        record_ids = {ref["record_ref"]["record_id"] for ref in refs}
        self.assertIn("obs_p22_outcome_adverse_001", record_ids)
        self.assertIn("imp_p22_outcome_002", record_ids)

    def test_p22_09_later_question_is_new_outcome_not_correction(self) -> None:
        earlier = self.inconclusive.value
        later = self.adverse.value
        self.assertNotEqual(earlier["outcome_id"], later["outcome_id"])
        self.assertNotEqual(
            earlier["scope"]["question"], later["scope"]["question"]
        )
        earlier_end = datetime.fromisoformat(earlier["timeframe"]["ended_at"])
        later_start = datetime.fromisoformat(later["timeframe"]["started_at"])
        self.assertGreater(later_start, earlier_end)
        self.assertEqual(earlier["status"], "active")
        self.assertEqual(later["status"], "active")
        self.assertNotIn("supersedes", earlier)
        self.assertNotIn("supersedes", later)

    def test_p22_09_adverse_temporal_sequence_is_explicitly_noncausal(self) -> None:
        summary = self.adverse.value["summary"].lower()
        self.assertIn("does not establish", summary)
        self.assertIn("caused the change", summary)
        self.assertNotIn("because of the support", summary)

    def test_p22_09_event_count_does_not_prove_deterioration(self) -> None:
        summary = self.adverse.value["summary"].lower()
        self.assertIn(
            "does not infer deterioration from the number of events",
            summary,
        )

    def test_p22_09_outcomes_do_not_complete_support_process(self) -> None:
        self.assertEqual(self.process.value["workflow_state"], "active")
        self.assertEqual(
            {record.value["status"] for record in self.outcomes.values()},
            {"active"},
        )

    def test_p22_09_scenario_preserves_required_ticket_distinctions(self) -> None:
        distinctions = " ".join(
            self.scenario["required_distinctions"]
        ).lower()
        self.assertIn("missing evidence", distinctions)
        self.assertIn("not a correction", distinctions)
        self.assertIn("does not establish causation", distinctions)
        self.assertIn("does not prove improvement or deterioration", distinctions)

    def test_p22_09_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(identity=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )


if __name__ == "__main__":
    unittest.main()
