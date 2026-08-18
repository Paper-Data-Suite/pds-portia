from __future__ import annotations

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


class Issue22SupportPositiveOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus, "P22-08"
        )
        cls.records = load_scenario_records(
            cls.scenario_path, cls.scenario
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)
        cls.process = cls.by_contract["support_process"][0]
        cls.participants = cls.by_contract["support_process_participant"]
        cls.need = cls.by_contract["support_need"][0]
        cls.goal = cls.by_contract["support_goal"][0]
        cls.support = cls.by_contract["support"][0]
        cls.implementations = cls.by_contract["implementation"]
        cls.fidelity = cls.by_contract["fidelity"][0]
        cls.follow_up = cls.by_contract["follow_up"][0]
        cls.outcome = cls.by_contract["outcome"][0]

    def test_corpus_registers_p22_08_as_implemented(self) -> None:
        implemented = {item["scenario_id"] for item in self.corpus["scenarios"]}
        self.assertIn("P22-08", implemented)
        self.assertNotIn("P22-08", self.corpus["planned_positive_scenarios"])

    def test_p22_08_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_08_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_08_has_two_distinct_event_works_and_one_support_process(self) -> None:
        self.assertEqual(len(self.by_contract["event"]), 2)
        self.assertEqual(len(self.by_contract["support_process"]), 1)
        event_ids = {record.value["work_id"] for record in self.by_contract["event"]}
        self.assertEqual(len(event_ids), 2)
        self.assertNotIn(self.process.value["work_id"], event_ids)

    def test_p22_08_support_process_initiates_from_exact_baseline_event(self) -> None:
        initiation = self.process.value["initiation"]
        self.assertEqual(initiation["kind"], "event_context")
        self.assertEqual(initiation["event_ref"]["work_kind"], "event")
        self.assertEqual(initiation["event_ref"]["contract_version"], "2")
        self.assertIn(
            initiation["event_ref"]["work_id"],
            {record.value["work_id"] for record in self.by_contract["event"]},
        )

    def test_p22_08_support_process_has_supported_person_and_teacher_contexts(self) -> None:
        contexts = {
            record.value["participant_id"]: {
                item["kind"] for item in record.value["contexts"]
            }
            for record in self.participants
        }
        self.assertTrue(any("supported_person" in value for value in contexts.values()))
        self.assertTrue(
            any(
                {"provider_or_collaborator", "coordinator", "observer"} <= value
                for value in contexts.values()
            )
        )

    def test_p22_08_need_is_planning_not_diagnosis(self) -> None:
        self.assertEqual(
            self.need.value["need_kind"], "environmental_or_instructional"
        )
        text = self.need.value["description"].lower()
        for prohibited in ("diagnos", "disability", "risk", "function"):
            self.assertNotIn(prohibited, text)

    def test_p22_08_goal_criteria_are_planning_only(self) -> None:
        self.assertIn("planned_criteria", self.goal.value)
        self.assertIn("measurement_approach", self.goal.value)
        self.assertNotIn("result", self.goal.value)
        self.assertNotIn("attained", self.goal.value)

    def test_p22_08_support_links_exact_need_goal_target_and_provider(self) -> None:
        self.assertEqual(
            self.support.value["need_refs"],
            [{
                "record_kind": "support_need",
                "record_id": self.need.value["need_id"],
                "contract_version": "1",
            }],
        )
        self.assertEqual(
            self.support.value["goal_refs"],
            [{
                "record_kind": "support_goal",
                "record_id": self.goal.value["goal_id"],
                "contract_version": "1",
            }],
        )
        self.assertEqual(self.support.value["provider_plan"]["kind"], "assigned")

    def test_p22_08_schedule_is_planning_not_implementation(self) -> None:
        schedule = self.support.value["schedule"]
        self.assertEqual(schedule["kind"], "recurring")
        self.assertEqual(len(self.implementations), 2)
        self.assertNotIn("implementation_id", schedule)

    def test_p22_08_two_actual_implementations_resolve_same_support(self) -> None:
        self.assertEqual(len(self.implementations), 2)
        refs = {tuple(sorted(record.value["plan_ref"].items())) for record in self.implementations}
        self.assertEqual(len(refs), 1)
        for record in self.implementations:
            self.assertEqual(record.value["plan_ref"]["record_id"], self.support.value["support_id"])
            self.assertEqual(record.value["execution_state"], "completed")

    def test_p22_08_completed_implementation_does_not_claim_fidelity_or_outcome(self) -> None:
        for record in self.implementations:
            self.assertNotIn("fidelity", record.value)
            self.assertNotIn("outcome", record.value)
            self.assertNotIn("effective", record.value["summary"].lower())

    def test_p22_08_fidelity_scopes_both_implementations_and_same_plan(self) -> None:
        self.assertEqual(self.fidelity.value["scope"]["kind"], "implementation_set")
        self.assertEqual(
            {item["record_id"] for item in self.fidelity.value["scope"]["implementation_refs"]},
            {record.value["implementation_id"] for record in self.implementations},
        )
        self.assertEqual(
            self.fidelity.value["plan_ref"]["record_id"],
            self.support.value["support_id"],
        )
        self.assertEqual(self.fidelity.value["result"], "as_planned")

    def test_p22_08_fidelity_does_not_claim_effectiveness(self) -> None:
        text = self.fidelity.value["summary"].lower()
        self.assertIn("does not", text)
        self.assertIn("effectiveness", text)
        self.assertNotIn("outcome_id", self.fidelity.value)

    def test_p22_08_follow_up_completion_is_separate_from_outcome(self) -> None:
        self.assertEqual(self.follow_up.value["workflow_state"], "completed")
        self.assertIn("completed_at", self.follow_up.value)
        self.assertNotIn("result", self.follow_up.value)
        self.assertNotIn("outcome_id", self.follow_up.value)

    def test_p22_08_follow_up_selects_continue_without_auto_transition(self) -> None:
        self.assertEqual(
            self.follow_up.value["disposition"]["kind"],
            "continue_current_support",
        )
        self.assertEqual(self.process.value["workflow_state"], "active")

    def test_p22_08_outcome_is_separately_attributable_human_evaluation(self) -> None:
        self.assertEqual(
            self.outcome.value["evaluator"]["kind"],
            "support_process_participant",
        )
        self.assertEqual(self.outcome.value["result"], "progress_observed")
        self.assertEqual(
            self.outcome.value["scope"]["kind"], "support_response_review"
        )

    def test_p22_08_outcome_basis_spans_both_events_and_support_process(self) -> None:
        refs = [
            entry["locator"]["record_ref"]
            for entry in self.outcome.value["basis"]
            if entry["locator"]["kind"] == "portia_record"
        ]
        work_ids = {ref["work_ref"]["work_id"] for ref in refs}
        event_ids = {record.value["work_id"] for record in self.by_contract["event"]}
        self.assertTrue(event_ids <= work_ids)
        self.assertIn(self.process.value["work_id"], work_ids)

    def test_p22_08_positive_outcome_is_bounded_and_noncausal(self) -> None:
        self.assertEqual(self.outcome.value["timeframe"]["precision"], "range")
        self.assertTrue(self.outcome.value["basis"])
        summary = self.outcome.value["summary"].lower()
        self.assertIn("not a causal-effect estimate", summary)
        self.assertIn("does not claim", summary)

    def test_p22_08_positive_outcome_does_not_complete_support_process(self) -> None:
        self.assertEqual(self.outcome.value["result"], "progress_observed")
        self.assertEqual(self.process.value["workflow_state"], "active")

    def test_p22_08_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(identity=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )


if __name__ == "__main__":
    unittest.main()
