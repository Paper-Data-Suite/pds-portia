from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        lifecycle_heads,
        load_corpus,
        load_scenario_records,
        replacement_frontier,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import (
        load_json_object,
        load_validated_catalog_and_store,
    )
except ImportError:
    from issue_22_graph_validation import (
        lifecycle_heads,
        load_corpus,
        load_scenario_records,
        replacement_frontier,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import (
        load_json_object,
        load_validated_catalog_and_store,
    )


class Issue22CorrectionHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus,
            "P22-04",
        )
        cls.records = load_scenario_records(
            cls.scenario_path,
            cls.scenario,
        )
        cls.expected = load_json_object(
            cls.scenario_path.parent / "expected.json"
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(
                record.contract,
                [],
            ).append(record)

    def test_corpus_registers_p22_04_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"]
            for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-04", implemented)
        self.assertNotIn(
            "P22-04",
            self.corpus["planned_positive_scenarios"],
        )

    def test_p22_04_public_records_are_structurally_valid(self) -> None:
        findings = validate_structural_records(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_04_combined_graph_is_valid(self) -> None:
        findings = validate_graph(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_04_preserves_predecessor_and_distinct_successor(self) -> None:
        accounts = {
            record.value["account_id"]: record
            for record in self.by_contract["account"]
        }
        predecessor = accounts[
            self.expected["predecessor_account_id"]
        ]
        successor = accounts[
            self.expected["successor_account_id"]
        ]

        self.assertEqual(
            predecessor.value["status"],
            self.expected["predecessor_status"],
        )
        self.assertEqual(
            successor.value["status"],
            self.expected["successor_status"],
        )
        self.assertNotEqual(
            predecessor.value["account_id"],
            successor.value["account_id"],
        )

    def test_p22_04_successor_exactly_supersedes_predecessor(self) -> None:
        successor = next(
            record
            for record in self.by_contract["account"]
            if record.value["account_id"]
            == self.expected["successor_account_id"]
        )
        supersession = successor.value["supersedes"][0]
        self.assertEqual(
            supersession["work_record_ref"]["record_ref"],
            {
                "record_kind": "account",
                "record_id": self.expected["predecessor_account_id"],
                "contract_version": "2",
            },
        )
        self.assertEqual(
            supersession["reason"],
            self.expected["supersession_reason"],
        )

    def test_p22_04_disagreement_targets_exact_predecessor(self) -> None:
        disagreement = self.by_contract[
            "statement_of_disagreement"
        ][0]
        self.assertEqual(
            disagreement.value["disagreement_id"],
            self.expected["disagreement_id"],
        )
        self.assertEqual(
            disagreement.value["target"]["record_ref"],
            {
                "record_kind": "account",
                "record_id": self.expected["disagreement_target_id"],
                "contract_version": "2",
            },
        )
        self.assertEqual(
            disagreement.value["positions"],
            ["disputes_accuracy"],
        )
        self.assertIn(
            "blue, not red",
            disagreement.value["statement"]["text"],
        )

    def test_p22_04_historical_review_remains_pinned_to_predecessor(self) -> None:
        review = self.by_contract["review"][0]
        evidence_ref = review.value[
            "evidence_considered"
        ][0]["work_record_ref"]["record_ref"]

        self.assertEqual(
            review.value["review_id"],
            self.expected["historical_review_id"],
        )
        self.assertEqual(
            evidence_ref["record_id"],
            self.expected["historical_review_evidence_id"],
        )
        self.assertNotEqual(
            evidence_ref["record_id"],
            self.expected["successor_account_id"],
        )

    def test_p22_04_replacement_frontier_selects_active_successor(self) -> None:
        self.assertEqual(
            list(
                replacement_frontier(
                    self.records,
                    "account",
                )
            ),
            self.expected["current_account_frontier"],
        )

    def test_p22_04_lifecycle_histories_have_expected_heads(self) -> None:
        heads = lifecycle_heads(self.records)
        actual = {}

        for key, transition in heads.items():
            _, _, record_kind, record_id, version = key
            if record_kind != "account" or version != "2":
                continue
            actual[record_id] = {
                "transition_id": (
                    transition.value["transition_id"]
                ),
                "to_status": transition.value["to_status"],
            }

        self.assertEqual(
            actual,
            self.expected["lifecycle_heads"],
        )

    def test_p22_04_predecessor_lifecycle_is_append_only(self) -> None:
        transitions = {
            record.value["transition_id"]: record.value
            for record in self.by_contract[
                "lifecycle_transition"
            ]
        }
        active = transitions["lct_p22_original_active"]
        superseded = transitions[
            "lct_p22_original_superseded"
        ]

        self.assertIsNone(active["previous_transition"])
        self.assertEqual(
            (active["from_status"], active["to_status"]),
            ("proposed", "active"),
        )
        self.assertEqual(
            superseded["previous_transition"]["record_id"],
            active["transition_id"],
        )
        self.assertEqual(
            (
                superseded["from_status"],
                superseded["to_status"],
            ),
            ("active", "superseded"),
        )

    def test_p22_04_successor_has_independent_lifecycle_identity(self) -> None:
        transition = next(
            record.value
            for record in self.by_contract[
                "lifecycle_transition"
            ]
            if record.value["transition_id"]
            == "lct_p22_corrected_active"
        )
        self.assertIsNone(
            transition["previous_transition"]
        )
        self.assertEqual(
            transition["target"]["record_ref"]["record_id"],
            self.expected["successor_account_id"],
        )
        self.assertEqual(
            (
                transition["from_status"],
                transition["to_status"],
            ),
            ("proposed", "active"),
        )

    def test_p22_04_correction_does_not_rewrite_original_content(self) -> None:
        accounts = {
            record.value["account_id"]: record.value
            for record in self.by_contract["account"]
        }
        original_text = accounts[
            self.expected["predecessor_account_id"]
        ]["content"][0]["text"]
        corrected_text = accounts[
            self.expected["successor_account_id"]
        ]["content"][0]["text"]

        self.assertIn("was red", original_text)
        self.assertIn("was blue", corrected_text)
        self.assertNotEqual(
            original_text,
            corrected_text,
        )


if __name__ == "__main__":
    unittest.main()
