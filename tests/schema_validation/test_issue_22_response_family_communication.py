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
    from .schema_support import (
        load_validated_catalog_and_store,
    )
except ImportError:
    from issue_22_graph_validation import (
        _canonical_path_for_record,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import (
        load_validated_catalog_and_store,
    )


class Issue22ResponseFamilyCommunicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus,
            "P22-07",
        )
        cls.records = load_scenario_records(
            cls.scenario_path,
            cls.scenario,
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(
                record.contract,
                [],
            ).append(record)

        cls.actor = cls.by_contract["actor"][0]
        cls.contact = cls.by_contract["actor_contact_point"][0]
        cls.relationship = cls.by_contract[
            "actor_student_relationship"
        ][0]
        cls.event = cls.by_contract["event"][0]
        cls.participant = cls.by_contract["event_participant"][0]
        cls.response = cls.by_contract["response"][0]
        cls.communication = cls.by_contract["communication"][0]

    def test_corpus_registers_p22_07_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"]
            for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-07", implemented)
        self.assertNotIn(
            "P22-07",
            self.corpus["planned_positive_scenarios"],
        )

    def test_p22_07_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_07_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_07_uses_expected_contract_chain(self) -> None:
        self.assertEqual(
            set(self.by_contract),
            {
                "actor",
                "actor_contact_point",
                "actor_student_relationship",
                "event",
                "event_participant",
                "response",
                "communication",
            },
        )

    def test_p22_07_actor_storage_is_workspace_scoped(self) -> None:
        for record in (
            self.actor,
            self.contact,
            self.relationship,
        ):
            with self.subTest(
                identity=record.logical_identity,
            ):
                self.assertEqual(
                    record.descriptor["owner"]["owner_kind"],
                    "actor",
                )
                self.assertNotIn(
                    "class_id",
                    record.value,
                )
                self.assertNotIn(
                    "work_id",
                    record.value,
                )
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )
                self.assertTrue(
                    record.descriptor["canonical_path"].startswith(
                        "portia/actors/"
                    )
                )

    def test_p22_07_actor_category_is_not_relationship_or_authority(self) -> None:
        self.assertEqual(
            self.actor.value["actor_category"],
            {"kind": "family_or_caregiver"},
        )
        self.assertNotIn(
            "student_ref",
            self.actor.value,
        )
        self.assertNotIn(
            "relationship",
            self.actor.value,
        )
        self.assertNotIn(
            "authority",
            self.actor.value,
        )

    def test_p22_07_contact_point_is_separate_from_actor_identity(self) -> None:
        self.assertEqual(
            self.contact.value["actor_id"],
            self.actor.value["actor_id"],
        )
        self.assertEqual(
            self.contact.value["contact"]["kind"],
            "email",
        )
        self.assertNotIn(
            "contact",
            self.actor.value,
        )
        self.assertNotIn(
            self.contact.value["contact"]["address"],
            str(self.actor.value),
        )

    def test_p22_07_local_contact_verification_is_not_delivery_or_consent(self) -> None:
        verification = self.contact.value["verification"]
        self.assertEqual(
            verification["kind"],
            "locally_confirmed",
        )
        self.assertNotIn(
            "delivery",
            verification,
        )
        self.assertNotIn(
            "consent",
            verification,
        )
        self.assertNotIn(
            "authorization",
            verification,
        )

    def test_p22_07_relationship_targets_exact_roster_pair(self) -> None:
        self.assertEqual(
            self.relationship.value["student_ref"],
            self.participant.value["subject"][
                "roster_student_ref"
            ],
        )
        self.assertEqual(
            self.relationship.value["relationship"],
            {"type": "family_contact"},
        )
        self.assertEqual(
            self.relationship.value["review"]["kind"],
            "locally_reviewed",
        )

    def test_p22_07_relationship_does_not_encode_legal_authority(self) -> None:
        value = self.relationship.value
        for prohibited in (
            "guardianship",
            "custody",
            "consent",
            "authorization",
            "disclosure_permission",
            "decision_authority",
        ):
            self.assertNotIn(
                prohibited,
                value,
            )

    def test_p22_07_response_is_immediate_non_consequence_action(self) -> None:
        value = self.response.value
        self.assertEqual(
            value["action"]["family"],
            "environmental_or_instructional",
        )
        self.assertEqual(
            value["execution_state"],
            "completed",
        )
        self.assertNotIn(
            "consequence_context",
            value["action"],
        )
        self.assertNotIn(
            "determination_ref",
            value,
        )

    def test_p22_07_response_targets_exact_event_participant(self) -> None:
        target = self.response.value["target"]
        self.assertEqual(
            target["record_ref"],
            {
                "record_kind": "event_participant",
                "record_id": self.participant.value[
                    "participant_id"
                ],
                "contract_version": "3",
            },
        )

    def test_p22_07_communication_recipient_is_actor_not_event_participant(self) -> None:
        recipient = self.communication.value["recipients"][0]
        self.assertEqual(
            recipient["person"]["kind"],
            "actor",
        )
        self.assertEqual(
            recipient["person"]["actor_ref"]["actor_id"],
            self.actor.value["actor_id"],
        )
        self.assertNotEqual(
            recipient["person"]["actor_ref"]["actor_id"],
            self.participant.value["participant_id"],
        )

    def test_p22_07_communication_uses_exact_contact_endpoint(self) -> None:
        endpoint = self.communication.value[
            "recipients"
        ][0]["endpoint_ref"]
        self.assertEqual(
            endpoint,
            {
                "actor_id": self.actor.value["actor_id"],
                "contact_point_id": self.contact.value[
                    "contact_point_id"
                ],
                "contract_version": "1",
            },
        )

    def test_p22_07_completed_act_does_not_establish_recipient_participation(self) -> None:
        value = self.communication.value
        self.assertEqual(
            value["act_state"],
            "completed",
        )
        self.assertEqual(
            value["recipients"][0]["participation"],
            "not_established",
        )
        self.assertNotIn(
            "delivery_status",
            value,
        )
        self.assertNotIn(
            "read_status",
            value,
        )

    def test_p22_07_communication_relates_exactly_to_response(self) -> None:
        relation = self.communication.value["relations"][0]
        self.assertEqual(
            relation["relation"],
            "relates_to_response",
        )
        self.assertEqual(
            relation["record_ref"]["record_ref"],
            {
                "record_kind": "response",
                "record_id": self.response.value[
                    "response_id"
                ],
                "contract_version": "1",
            },
        )
        self.assertEqual(
            relation["record_ref"]["work_ref"]["work_id"],
            self.event.value["work_id"],
        )

    def test_p22_07_communication_is_participant_limited(self) -> None:
        value = self.communication.value
        self.assertEqual(
            value["method"],
            {"kind": "email"},
        )
        self.assertEqual(
            value["purpose"],
            {"kind": "response_coordination"},
        )
        self.assertEqual(
            value["privacy_scope"],
            "participant_limited",
        )

    def test_p22_07_does_not_fabricate_judgment_support_or_outcome(self) -> None:
        contracts = set(self.by_contract)
        for forbidden in (
            "review",
            "classification",
            "hypothesis",
            "determination",
            "support",
            "intervention",
            "outcome",
        ):
            self.assertNotIn(
                forbidden,
                contracts,
            )

    def test_p22_07_response_completion_does_not_claim_effectiveness(self) -> None:
        description = self.response.value[
            "action"
        ]["description"].lower()
        self.assertNotIn(
            "effective",
            description,
        )
        self.assertNotIn(
            "successful",
            description,
        )
        self.assertNotIn(
            "improved",
            description,
        )
        self.assertNotIn(
            "outcome",
            self.response.value,
        )


if __name__ == "__main__":
    unittest.main()
