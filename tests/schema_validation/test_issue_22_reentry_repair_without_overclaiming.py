from __future__ import annotations

from datetime import date, datetime
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


class Issue22ReentryRepairWithoutOverclaimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus, "P22-10"
        )
        cls.records = load_scenario_records(
            cls.scenario_path, cls.scenario
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)
        cls.event = cls.by_contract["event"][0]
        cls.response = cls.by_contract["response"][0]
        cls.communication = cls.by_contract["communication"][0]
        cls.reentry = cls.by_contract["reentry"][0]
        cls.repair = cls.by_contract["repair"][0]
        cls.follow_up = cls.by_contract["follow_up"][0]

    def test_corpus_registers_p22_10_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"] for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-10", implemented)
        self.assertNotIn(
            "P22-10", self.corpus["planned_positive_scenarios"]
        )

    def test_p22_10_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_10_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_10_is_one_event_with_two_exact_participants(self) -> None:
        self.assertEqual(len(self.by_contract["event"]), 1)
        self.assertEqual(len(self.by_contract["event_participant"]), 2)
        self.assertEqual(
            {
                record.value["participant_id"]
                for record in self.by_contract["event_participant"]
            },
            {
                "ep_p22_reentry_repair_a",
                "ep_p22_reentry_repair_b",
            },
        )

    def test_p22_10_participant_accounts_remain_separate_perspectives(self) -> None:
        accounts = {
            record.value["account_id"]: record.value
            for record in self.by_contract["account"]
        }
        self.assertEqual(len(accounts), 2)
        self.assertEqual(
            accounts["acct_p22_reentry_repair_a"]["source"]
            ["roster_student_ref"]["student_id"],
            "stu_p22_001",
        )
        self.assertEqual(
            accounts["acct_p22_reentry_repair_b"]["source"]
            ["roster_student_ref"]["student_id"],
            "stu_p22_002",
        )
        self.assertNotEqual(
            accounts["acct_p22_reentry_repair_a"]["content"],
            accounts["acct_p22_reentry_repair_b"]["content"],
        )
        self.assertNotIn("determination", self.by_contract)

    def test_p22_10_response_and_communication_remain_distinct(self) -> None:
        response = self.response.value
        communication = self.communication.value
        self.assertEqual(response["execution_state"], "completed")
        self.assertEqual(communication["act_state"], "completed")
        self.assertEqual(
            communication["relations"][0]["relation"],
            "relates_to_response",
        )
        ref = communication["relations"][0]["record_ref"]
        self.assertEqual(
            ref["record_ref"]["record_id"], response["response_id"]
        )
        self.assertEqual(ref["work_ref"]["work_id"], self.event.value["work_id"])

    def test_p22_10_reentry_keeps_plan_and_actual_completion_distinct(self) -> None:
        value = self.reentry.value
        self.assertEqual(value["workflow_state"], "completed")
        self.assertEqual(value["planned_return"]["kind"], "date_only")
        planned = date.fromisoformat(value["planned_return"]["date"])
        completed = datetime.fromisoformat(value["completed_at"]).date()
        self.assertEqual(planned, completed)
        self.assertEqual(len(value["planned_elements"]), 2)
        self.assertNotIn("supersedes", value)

    def test_p22_10_reentry_initiates_from_exact_response(self) -> None:
        context = self.reentry.value["initiating_context"]
        self.assertEqual(context["kind"], "response")
        ref = context["record_ref"]
        self.assertEqual(
            ref["record_ref"],
            {
                "record_kind": "response",
                "record_id": "rsp_p22_reentry_repair_001",
                "contract_version": "1",
            },
        )
        self.assertEqual(ref["work_ref"]["work_id"], self.event.value["work_id"])
        self.assertEqual(
            self.reentry.value["target"]["record_ref"]["record_id"],
            "ep_p22_reentry_repair_a",
        )

    def test_p22_10_reentry_completion_does_not_claim_clearance(self) -> None:
        value = self.reentry.value
        text = " ".join(
            item["description"] for item in value["planned_elements"]
        ).lower()
        self.assertIn("without requiring apology", text)
        self.assertIn("proof of readiness", text)
        for forbidden_field in (
            "clearance",
            "safe",
            "rehabilitated",
            "readiness_score",
            "medical_clearance",
            "threat_assessment_clearance",
        ):
            self.assertNotIn(forbidden_field, value)

    def test_p22_10_repair_preserves_offer_participation_and_decline(self) -> None:
        value = self.repair.value
        states = {
            item["participant_key"]: item["participation_state"]
            for item in value["participants"]
        }
        self.assertEqual(states["student_a"], "participated")
        self.assertEqual(states["student_b"], "declined")
        self.assertEqual(value["workflow_state"], "completed")
        self.assertEqual(
            value["target"]["record_ref"]["record_id"],
            "ep_p22_reentry_repair_a",
        )
        self.assertNotIn("supersedes", value)

    def test_p22_10_repair_action_completion_is_not_mutual_agreement(self) -> None:
        action = self.repair.value["actions"][0]
        self.assertEqual(action["completion_state"], "completed")
        self.assertEqual(action["agreed_by"], ["student_a"])
        self.assertEqual(
            action["responsible_participant_keys"], ["student_a"]
        )
        self.assertNotIn("student_b", action["agreed_by"])

    def test_p22_10_repair_uses_accounts_and_communication_as_context(self) -> None:
        refs = [
            item["record_ref"]["record_ref"]
            for item in self.repair.value["context_refs"]
            if item["kind"] == "record"
        ]
        self.assertEqual(
            {(ref["record_kind"], ref["record_id"]) for ref in refs},
            {
                ("account", "acct_p22_reentry_repair_a"),
                ("account", "acct_p22_reentry_repair_b"),
                ("communication", "comm_p22_reentry_repair_001"),
            },
        )

    def test_p22_10_repair_completion_does_not_overclaim(self) -> None:
        value = self.repair.value
        focus = value["focus"].lower()
        self.assertIn("without deciding which account is true", focus)
        self.assertIn("admission", focus)
        self.assertIn("remorse", focus)
        self.assertIn("forgiveness", focus)
        serialized = str(value).lower()
        for prohibited_claim in (
            "relationship_restored",
            "rehabilitated",
            "admitted_wrongdoing",
            "is_remorseful",
            "forgiven",
        ):
            self.assertNotRegex(
                serialized,
                rf"\b{prohibited_claim}\b",
                msg=(
                    f"Repair unexpectedly makes prohibited claim: "
                    f"{prohibited_claim}"
                ),
            )

    def test_p22_10_later_follow_up_reviews_reentry_and_repair_exactly(self) -> None:
        value = self.follow_up.value
        self.assertEqual(value["workflow_state"], "completed")
        self.assertEqual(value["purpose"]["kind"], "repair_check")
        reviewed = {
            (
                item["record_ref"]["record_ref"]["record_kind"],
                item["record_ref"]["record_ref"]["record_id"],
            )
            for item in value["related_records"]
            if item["role"] == "reviewed"
        }
        self.assertEqual(
            reviewed,
            {
                ("reentry", "ren_p22_reentry_repair_001"),
                ("repair", "rpr_p22_reentry_repair_001"),
            },
        )

    def test_p22_10_follow_up_does_not_manufacture_outcome(self) -> None:
        self.assertNotIn("outcome", self.by_contract)
        self.assertNotIn("disposition", self.follow_up.value)
        self.assertEqual(self.follow_up.value["status"], "active")

    def test_p22_10_scenario_preserves_required_ticket_distinctions(self) -> None:
        distinctions = " ".join(
            self.scenario["required_distinctions"]
        ).lower()
        self.assertIn("safety clearance", distinctions)
        self.assertIn("rehabilitation", distinctions)
        self.assertIn("admission of wrongdoing", distinctions)
        self.assertIn("remorse", distinctions)
        self.assertIn("forgiveness", distinctions)
        self.assertIn("restored relationship", distinctions)

    def test_p22_10_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(identity=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )


if __name__ == "__main__":
    unittest.main()
