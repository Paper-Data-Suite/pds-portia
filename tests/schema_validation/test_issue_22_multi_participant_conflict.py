from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import load_json_object, load_validated_catalog_and_store
except ImportError:
    from issue_22_graph_validation import (
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import load_json_object, load_validated_catalog_and_store


class Issue22MultiParticipantConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(cls.corpus, "P22-02")
        cls.records = load_scenario_records(cls.scenario_path, cls.scenario)
        cls.expected = load_json_object(cls.scenario_path.parent / "expected.json")
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)

    def test_corpus_registers_p22_02_as_implemented_positive_scenario(self) -> None:
        scenarios = [item["scenario_id"] for item in self.corpus["scenarios"]]
        self.assertIn("P22-02", scenarios)
        self.assertNotIn("P22-02", self.corpus["planned_positive_scenarios"])

    def test_p22_02_has_twelve_canonical_portia_records(self) -> None:
        self.assertEqual(len(self.records), 12)
        self.assertEqual(len(self.by_contract["event"]), 1)
        self.assertEqual(len(self.by_contract["event_participant"]), 3)
        self.assertEqual(len(self.by_contract["event_participant_role"]), 3)
        self.assertEqual(len(self.by_contract["account"]), 2)
        self.assertEqual(len(self.by_contract["observation"]), 1)
        self.assertEqual(len(self.by_contract["review"]), 1)
        self.assertEqual(len(self.by_contract["determination"]), 1)

    def test_p22_02_uses_current_account_and_observation_contracts(self) -> None:
        self.assertEqual(
            {record.version for record in self.by_contract["account"]},
            {"2"},
        )
        self.assertEqual(
            {record.version for record in self.by_contract["observation"]},
            {"2"},
        )
        self.assertEqual(
            {record.version for record in self.by_contract["event_participant"]},
            {"3"},
        )
        self.assertEqual(
            {record.version for record in self.by_contract["event_participant_role"]},
            {"3"},
        )

    def test_p22_02_public_records_are_structurally_valid(self) -> None:
        findings = validate_structural_records(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_02_combined_graph_is_valid(self) -> None:
        findings = validate_graph(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_02_all_three_roster_subjects_resolve_exactly(self) -> None:
        contexts = load_contexts(self.scenario_path, self.scenario)
        self.assertEqual(len(contexts), 1)
        _, roster = contexts[0]
        roster_ids = {
            student["student_id"] for student in roster["students"]
        }
        participant_refs = {
            record.value["subject"]["roster_student_ref"]["student_id"]
            for record in self.by_contract["event_participant"]
        }
        self.assertEqual(
            participant_refs,
            {"stu_p22_001", "stu_p22_002", "stu_p22_003"},
        )
        self.assertTrue(participant_refs.issubset(roster_ids))

    def test_p22_02_roles_preserve_distinct_relationship_semantics(self) -> None:
        role_types = {
            record.value["role_type"]
            for record in self.by_contract["event_participant_role"]
        }
        self.assertEqual(
            role_types,
            {"directly_involved", "reported_involved", "present"},
        )
        reported = next(
            record
            for record in self.by_contract["event_participant_role"]
            if record.value["role_type"] == "reported_involved"
        )
        self.assertEqual(
            reported.value["basis"],
            [{
                "kind": "account_ref",
                "record_ref": {
                    "record_kind": "account",
                    "record_id": self.expected["reported_role_basis_account_id"],
                    "contract_version": "2",
                },
            }],
        )

    def test_p22_02_accounts_conflict_but_remain_separate_firsthand_evidence(self) -> None:
        accounts = self.by_contract["account"]
        self.assertEqual(
            {record.value["account_id"] for record in accounts},
            set(self.expected["account_ids"]),
        )
        self.assertEqual(
            {record.value["information_origin"] for record in accounts},
            {"firsthand"},
        )
        self.assertEqual(
            {
                record.value["target"]["record_ref"]["record_id"]
                for record in accounts
            },
            {self.expected["account_target_participant_id"]},
        )
        texts = [record.value["content"][0]["text"] for record in accounts]
        self.assertTrue(any("moved the blue folder" in text for text in texts))
        self.assertTrue(any("did not touch the blue folder" in text for text in texts))

    def test_p22_02_direct_observation_does_not_claim_disputed_handling(self) -> None:
        observation = self.by_contract["observation"][0]
        self.assertEqual(observation.value["method"], "live_direct")
        self.assertEqual(
            observation.value["target"]["record_ref"]["record_id"],
            self.expected["observation_target_participant_id"],
        )
        narrative = observation.value["content"]["narrative"].lower()
        self.assertIn("folder was on the floor", narrative)
        self.assertNotIn("handled the folder", narrative)
        self.assertNotIn("caused", narrative)
        self.assertNotIn("guilty", narrative)

    def test_p22_02_completed_review_considers_both_accounts_and_observation(self) -> None:
        review = self.by_contract["review"][0]
        self.assertEqual(review.value["review_state"], "completed")
        evidence_ids = {
            entry["work_record_ref"]["record_ref"]["record_id"]
            for entry in review.value["evidence_considered"]
        }
        self.assertEqual(
            evidence_ids,
            set(self.expected["review_evidence_record_ids"]),
        )

    def test_p22_02_determination_preserves_uncertainty_and_exact_review_link(self) -> None:
        determination = self.by_contract["determination"][0]
        self.assertEqual(
            determination.value["outcome"]["kind"],
            "insufficient_information",
        )
        self.assertEqual(
            determination.value["review_ref"]["record_ref"]["record_id"],
            self.expected["determination_review_id"],
        )
        by_relation = {}
        for entry in determination.value["basis"]:
            by_relation.setdefault(entry["relation"], []).append(
                entry["evidence_ref"]["work_record_ref"]["record_ref"]["record_id"]
            )
        self.assertEqual(
            {key: sorted(value) for key, value in by_relation.items()},
            {
                key: sorted(value)
                for key, value in self.expected["determination_basis"].items()
            },
        )
        rationale = determination.value["rationale"].lower()
        self.assertIn("accounts conflict", rationale)
        self.assertIn("after the disputed", rationale)

    def test_p22_02_does_not_fabricate_classification_or_hypothesis(self) -> None:
        contracts = {record.contract for record in self.records}
        for forbidden in self.expected["forbidden_contracts"]:
            self.assertNotIn(forbidden, contracts)


if __name__ == "__main__":
    unittest.main()
