from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
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


class Issue22ClassificationHypothesisInterventionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus, "P22-15"
        )
        cls.records = load_scenario_records(
            cls.scenario_path, cls.scenario
        )
        cls.by_contract: dict[str, list[object]] = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)

        cls.event = cls.by_contract["event"][0]
        cls.event_participant = cls.by_contract["event_participant"][0]
        cls.account = cls.by_contract["account"][0]
        cls.observation = cls.by_contract["observation"][0]
        cls.review = cls.by_contract["review"][0]
        cls.classification = cls.by_contract["classification"][0]
        cls.hypothesis = cls.by_contract["hypothesis"][0]
        cls.process = cls.by_contract["support_process"][0]
        cls.support_participants = cls.by_contract[
            "support_process_participant"
        ]
        cls.need = cls.by_contract["support_need"][0]
        cls.goal = cls.by_contract["support_goal"][0]
        cls.intervention = cls.by_contract["intervention"][0]
        cls.implementation = cls.by_contract["implementation"][0]

    def finding_ids(self, findings: tuple[object, ...]) -> set[str]:
        return {finding.code for finding in findings}

    def test_corpus_keeps_required_positive_set_and_adds_p22_15(self) -> None:
        implemented = {
            item["scenario_id"]
            for item in self.corpus["scenarios"]
            if item.get("scenario_kind") == "positive"
        }
        required = {f"P22-{number:02d}" for number in range(1, 15)}
        self.assertTrue(required <= implemented)
        self.assertIn("P22-15", implemented)
        self.assertEqual(self.corpus["planned_positive_scenarios"], [])

    def test_p22_15_exercises_missing_required_public_families(self) -> None:
        self.assertEqual(
            {
                "classification": len(self.by_contract["classification"]),
                "hypothesis": len(self.by_contract["hypothesis"]),
                "intervention": len(self.by_contract["intervention"]),
            },
            {
                "classification": 1,
                "hypothesis": 1,
                "intervention": 1,
            },
        )

    def test_p22_15_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_15_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_15_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(identity=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )

    def test_review_is_completed_participant_scoped_and_exact(self) -> None:
        self.assertEqual(self.review.value["review_state"], "completed")
        self.assertEqual(
            self.review.value["target"],
            self.classification.value["target"],
        )
        self.assertEqual(
            self.review.value["target"],
            self.hypothesis.value["target"],
        )
        self.assertEqual(
            self.review.value["target"]["record_ref"]["record_id"],
            self.event_participant.value["participant_id"],
        )
        evidence_ids = {
            entry["work_record_ref"]["record_ref"]["record_id"]
            for entry in self.review.value["evidence_considered"]
        }
        self.assertEqual(
            evidence_ids,
            {
                self.account.value["account_id"],
                self.observation.value["observation_id"],
            },
        )

    def test_classification_is_human_selected_and_review_bound(self) -> None:
        value = self.classification.value
        self.assertEqual(value["stage"], "reviewer_selected")
        self.assertEqual(value["selector"]["kind"], "local_operator")
        self.assertEqual(
            value["review_ref"]["record_ref"]["record_id"],
            self.review.value["review_id"],
        )
        self.assertEqual(
            value["result"]["kind"],
            "category_selected",
        )
        self.assertEqual(
            value["result"]["definition"]["category_code"],
            "transition_delay",
        )

    def test_classification_basis_is_exact_and_carries_no_weight_claim(self) -> None:
        value = self.classification.value
        basis_ids = {
            item["work_record_ref"]["record_ref"]["record_id"]
            for item in value["basis"]
        }
        self.assertEqual(
            basis_ids,
            {
                self.account.value["account_id"],
                self.observation.value["observation_id"],
            },
        )
        serialized = json.dumps(value, sort_keys=True).lower()
        for prohibited in (
            "credibility_score",
            "risk_score",
            "automatic_classification",
            "finding",
            "determination",
        ):
            self.assertNotIn(prohibited, serialized)

    def test_hypothesis_is_tentative_review_bound_and_not_determination(self) -> None:
        value = self.hypothesis.value
        self.assertEqual(
            value["consideration_state"],
            "under_consideration",
        )
        self.assertEqual(value["author"]["kind"], "local_operator")
        self.assertEqual(
            value["review_ref"]["record_ref"]["record_id"],
            self.review.value["review_id"],
        )
        self.assertIn("may be relevant", value["proposition"])
        self.assertNotIn("determination", self.by_contract)

    def test_hypothesis_evidence_preserves_relation_roles_without_scoring(self) -> None:
        value = self.hypothesis.value
        relations = {
            entry["relation"]:
            entry["evidence_ref"]["work_record_ref"]["record_ref"]["record_id"]
            for entry in value["evidence"]
        }
        self.assertEqual(
            relations,
            {
                "supporting": self.account.value["account_id"],
                "contextual": self.observation.value["observation_id"],
            },
        )
        serialized = json.dumps(value, sort_keys=True).lower()
        for prohibited in (
            "diagnosis",
            "behavioral_function",
            "fba_result",
            "confidence_percent",
            "truth_probability",
            "credibility_score",
            "risk_score",
            "automatic_hypothesis",
        ):
            self.assertNotIn(prohibited, serialized)

    def test_support_process_initiates_from_exact_reviewed_event(self) -> None:
        initiation = self.process.value["initiation"]
        self.assertEqual(initiation["kind"], "event_context")
        self.assertEqual(
            initiation["event_ref"]["work_id"],
            self.event.value["work_id"],
        )
        self.assertEqual(
            initiation["event_ref"]["contract_version"],
            "2",
        )

    def test_intervention_links_exact_need_goal_target_and_provider(self) -> None:
        value = self.intervention.value
        self.assertEqual(value["plan_state"], "active")
        self.assertEqual(
            value["need_refs"],
            [{
                "record_kind": "support_need",
                "record_id": self.need.value["need_id"],
                "contract_version": "1",
            }],
        )
        self.assertEqual(
            value["goal_refs"],
            [{
                "record_kind": "support_goal",
                "record_id": self.goal.value["goal_id"],
                "contract_version": "1",
            }],
        )
        student_ids = {
            record.value["participant_id"]
            for record in self.support_participants
            if any(
                item["kind"] == "supported_person"
                for item in record.value["contexts"]
            )
        }
        provider_ids = {
            record.value["participant_id"]
            for record in self.support_participants
            if any(
                item["kind"] == "provider_or_collaborator"
                for item in record.value["contexts"]
            )
        }
        self.assertIn(
            value["target"]["record_ref"]["record_id"],
            student_ids,
        )
        self.assertEqual(value["provider_plan"]["kind"], "assigned")
        self.assertEqual(
            {
                item["record_id"]
                for item in value["provider_plan"]["participant_refs"]
            },
            provider_ids,
        )

    def test_intervention_schedule_is_plan_not_implementation(self) -> None:
        value = self.intervention.value
        self.assertEqual(value["schedule"]["kind"], "recurring")
        self.assertNotIn("implementation_id", value)
        self.assertNotIn("execution_state", value)
        self.assertNotIn("outcome", value)
        self.assertNotIn("fidelity", value)

    def test_implementation_is_one_actual_occurrence_of_exact_intervention(self) -> None:
        value = self.implementation.value
        self.assertEqual(
            value["plan_ref"],
            {
                "record_kind": "intervention",
                "record_id": self.intervention.value["intervention_id"],
                "contract_version": "1",
            },
        )
        self.assertEqual(value["execution_state"], "completed")
        self.assertIn("started_at", value)
        self.assertIn("ended_at", value)
        self.assertNotIn("fidelity", value)
        self.assertNotIn("outcome", value)

    def _mutated_graph_findings(
        self,
        fixture_name: str,
        mutate,
    ) -> tuple[object, ...]:
        with tempfile.TemporaryDirectory(
            prefix=".p22-15-mutation-",
            dir=self.scenario_path.parent.parent,
        ) as tmp:
            copied = Path(tmp)
            shutil.copytree(
                self.scenario_path.parent,
                copied,
                dirs_exist_ok=True,
            )
            target = copied / fixture_name
            value = json.loads(target.read_text(encoding="utf-8"))
            mutate(value)
            target.write_text(
                json.dumps(value, indent=2) + "\n",
                encoding="utf-8",
            )
            scenario = json.loads(
                (copied / "scenario.json").read_text(encoding="utf-8")
            )
            return validate_graph(
                copied / "scenario.json",
                scenario,
                catalog=self.catalog,
                store=self.store,
            )

    def test_graph_validator_checks_classification_evidence_resolution(self) -> None:
        def mutate(value: dict[str, object]) -> None:
            value["basis"][0]["work_record_ref"]["record_ref"][
                "record_id"
            ] = "acct_p22_missing_001"

        findings = self._mutated_graph_findings(
            "classification.json",
            mutate,
        )
        self.assertIn(
            "G22.EVIDENCE.UNRESOLVED",
            self.finding_ids(findings),
        )

    def test_graph_validator_checks_hypothesis_review_scope(self) -> None:
        def mutate(value: dict[str, object]) -> None:
            value["review_ref"]["work_ref"]["work_id"] = (
                "evt_p22_other_001"
            )

        findings = self._mutated_graph_findings(
            "hypothesis.json",
            mutate,
        )
        self.assertIn(
            "G22.JUDGMENT.REVIEW_WRONG_WORK",
            self.finding_ids(findings),
        )

    def test_graph_validator_checks_intervention_need_resolution(self) -> None:
        def mutate(value: dict[str, object]) -> None:
            value["need_refs"][0]["record_id"] = (
                "spn_p22_missing_001"
            )

        findings = self._mutated_graph_findings(
            "intervention.json",
            mutate,
        )
        self.assertIn(
            "G22.SUPPORT.PLAN_REFERENCE_UNRESOLVED",
            self.finding_ids(findings),
        )


if __name__ == "__main__":
    unittest.main()
