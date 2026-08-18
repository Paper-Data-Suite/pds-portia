from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        _canonical_path_for_record,
        load_contexts,
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
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import load_validated_catalog_and_store


class Issue22CrossYearSupportContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus, "P22-11"
        )
        cls.records = load_scenario_records(
            cls.scenario_path, cls.scenario
        )
        cls.contexts = load_contexts(
            cls.scenario_path, cls.scenario
        )
        cls.by_contract: dict[str, list] = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)

        processes = {
            record.value["school_year"]: record
            for record in cls.by_contract["support_process"]
        }
        cls.predecessor = processes["2026-2027"]
        cls.successor = processes["2027-2028"]

    def test_corpus_registers_p22_11_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"] for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-11", implemented)
        self.assertNotIn(
            "P22-11", self.corpus["planned_positive_scenarios"]
        )

    def test_p22_11_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_11_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_11_has_two_distinct_process_roots(self) -> None:
        self.assertEqual(len(self.by_contract["support_process"]), 2)
        self.assertNotEqual(
            self.predecessor.value["class_id"],
            self.successor.value["class_id"],
        )
        self.assertNotEqual(
            self.predecessor.value["work_id"],
            self.successor.value["work_id"],
        )
        self.assertEqual(
            self.predecessor.value["school_year"], "2026-2027"
        )
        self.assertEqual(
            self.successor.value["school_year"], "2027-2028"
        )

    def test_p22_11_successor_exactly_continues_from_predecessor(self) -> None:
        self.assertEqual(
            self.successor.value["continues_from"],
            {
                "module_id": "portia",
                "class_id": self.predecessor.value["class_id"],
                "work_id": self.predecessor.value["work_id"],
                "work_kind": "support_process",
                "contract_version": "1",
            },
        )

    def test_p22_11_continuation_is_not_supersession(self) -> None:
        self.assertNotIn("supersedes", self.predecessor.value)
        self.assertNotIn("supersedes", self.successor.value)
        self.assertEqual(self.predecessor.value["status"], "active")
        self.assertEqual(self.successor.value["status"], "active")
        self.assertEqual(
            self.predecessor.value["workflow_state"], "completed"
        )
        self.assertEqual(
            self.successor.value["workflow_state"], "active"
        )

    def test_p22_11_uses_no_migration_or_ownership_correction(self) -> None:
        self.assertTrue(
            {"record_migration", "ownership_correction"}.isdisjoint(
                self.by_contract
            )
        )

    def test_p22_11_new_year_uses_new_participant_instances(self) -> None:
        by_work: dict[str, set[str]] = {}
        for record in self.by_contract["support_process_participant"]:
            by_work.setdefault(record.value["work_id"], set()).add(
                record.value["participant_id"]
            )
        old_ids = by_work[self.predecessor.value["work_id"]]
        new_ids = by_work[self.successor.value["work_id"]]
        self.assertEqual(len(old_ids), 2)
        self.assertEqual(len(new_ids), 2)
        self.assertTrue(old_ids.isdisjoint(new_ids))

    def test_p22_11_roster_identity_remains_class_qualified(self) -> None:
        student_records = [
            record
            for record in self.by_contract["support_process_participant"]
            if record.value["person"]["kind"] == "roster_student"
        ]
        self.assertEqual(len(student_records), 2)
        refs = [
            record.value["person"]["roster_student_ref"]
            for record in student_records
        ]
        self.assertEqual(
            {ref["student_id"] for ref in refs},
            {"stu_p22_crossyear_001"},
        )
        self.assertEqual(
            {ref["class_id"] for ref in refs},
            {"eng10_p2_2026", "eng11_p3_2027"},
        )
        self.assertNotEqual(
            (refs[0]["class_id"], refs[0]["student_id"]),
            (refs[1]["class_id"], refs[1]["student_id"]),
        )

    def test_p22_11_context_contains_two_distinct_rosters(self) -> None:
        rosters = [
            value
            for kind, value in self.contexts
            if kind == "synthetic_core_roster"
        ]
        self.assertEqual(len(rosters), 2)
        self.assertEqual(
            {(r["class_id"], r["school_year"]) for r in rosters},
            {
                ("eng10_p2_2026", "2026-2027"),
                ("eng11_p3_2027", "2027-2028"),
            },
        )

    def test_p22_11_child_identities_are_not_cloned(self) -> None:
        identity_fields = {
            "support_need": "need_id",
            "support_goal": "goal_id",
            "support": "support_id",
            "implementation": "implementation_id",
            "observation": "observation_id",
            "outcome": "outcome_id",
        }
        for contract, field in identity_fields.items():
            with self.subTest(contract=contract):
                old_ids = {
                    record.value[field]
                    for record in self.by_contract[contract]
                    if record.value["work_id"]
                    == self.predecessor.value["work_id"]
                }
                new_ids = {
                    record.value[field]
                    for record in self.by_contract[contract]
                    if record.value["work_id"]
                    == self.successor.value["work_id"]
                }
                self.assertEqual(len(old_ids), 1)
                self.assertEqual(len(new_ids), 1)
                self.assertTrue(old_ids.isdisjoint(new_ids))

    def test_p22_11_selected_context_is_reviewed_not_plan_cloned(self) -> None:
        supports = {
            record.value["work_id"]: record.value
            for record in self.by_contract["support"]
        }
        old_support = supports[self.predecessor.value["work_id"]]
        new_support = supports[self.successor.value["work_id"]]
        self.assertNotEqual(
            old_support["strategy"]["procedure"],
            new_support["strategy"]["procedure"],
        )
        self.assertNotEqual(
            old_support["schedule"]["window"],
            new_support["schedule"]["window"],
        )
        self.assertEqual(old_support["plan_state"], "completed")
        self.assertEqual(new_support["plan_state"], "active")

    def test_p22_11_implementations_resolve_only_same_year_plans(self) -> None:
        supports = {
            record.value["work_id"]: record.value["support_id"]
            for record in self.by_contract["support"]
        }
        for implementation in self.by_contract["implementation"]:
            with self.subTest(
                implementation=implementation.value["implementation_id"]
            ):
                self.assertEqual(
                    implementation.value["plan_ref"]["record_id"],
                    supports[implementation.value["work_id"]],
                )

    @staticmethod
    def _basis_work_ids(outcome: dict) -> set[str]:
        result: set[str] = set()
        for entry in outcome["basis"]:
            locator = entry["locator"]
            if locator["kind"] != "portia_record":
                continue
            result.add(locator["record_ref"]["work_ref"]["work_id"])
        return result

    def test_p22_11_historical_exact_refs_remain_on_predecessor(self) -> None:
        outcomes = {
            record.value["work_id"]: record.value
            for record in self.by_contract["outcome"]
        }
        old_outcome = outcomes[self.predecessor.value["work_id"]]
        self.assertEqual(
            self._basis_work_ids(old_outcome),
            {self.predecessor.value["work_id"]},
        )
        self.assertNotIn(
            self.successor.value["work_id"],
            self._basis_work_ids(old_outcome),
        )

    def test_p22_11_new_year_outcome_uses_new_year_evidence(self) -> None:
        outcomes = {
            record.value["work_id"]: record.value
            for record in self.by_contract["outcome"]
        }
        new_outcome = outcomes[self.successor.value["work_id"]]
        self.assertEqual(
            self._basis_work_ids(new_outcome),
            {self.successor.value["work_id"]},
        )
        self.assertNotIn(
            self.predecessor.value["work_id"],
            self._basis_work_ids(new_outcome),
        )
        self.assertNotIn("supersedes", new_outcome)

    def test_p22_11_outcomes_are_new_bounded_evaluations(self) -> None:
        outcomes = {
            record.value["work_id"]: record.value
            for record in self.by_contract["outcome"]
        }
        old_outcome = outcomes[self.predecessor.value["work_id"]]
        new_outcome = outcomes[self.successor.value["work_id"]]
        self.assertNotEqual(
            old_outcome["outcome_id"], new_outcome["outcome_id"]
        )
        self.assertNotEqual(
            old_outcome["timeframe"], new_outcome["timeframe"]
        )
        self.assertNotEqual(
            old_outcome["scope"]["plan_refs"],
            new_outcome["scope"]["plan_refs"],
        )

    def test_p22_11_no_child_uses_cross_root_supersession(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                self.assertNotIn("supersedes", record.value)

    def test_p22_11_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                self.assertEqual(
                    record.descriptor["canonical_path"],
                    _canonical_path_for_record(record),
                )

    def test_p22_11_scenario_preserves_required_ticket_distinctions(self) -> None:
        distinctions = " ".join(
            self.scenario["required_distinctions"]
        ).lower()
        for phrase in (
            "not migration",
            "not migration or ownership correction",
            "new support process work identity",
            "not moved",
            "new support process participant identities",
            "not establish a workspace-global student identity",
            "without cloning predecessor child records",
            "identities are disjoint",
            "remain pinned to the predecessor",
            "does not retarget old exact references",
            "require new canonical records",
            "neither support process uses supersession",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, distinctions)


if __name__ == "__main__":
    unittest.main()
