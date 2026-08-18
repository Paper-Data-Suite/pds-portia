from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        durable_subject_key,
        load_contexts,
        load_corpus,
        load_scenario_records,
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
        durable_subject_key,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import (
        load_json_object,
        load_validated_catalog_and_store,
    )


class Issue22CrossClassIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus,
            "P22-03",
        )
        cls.records = load_scenario_records(
            cls.scenario_path,
            cls.scenario,
        )
        cls.expected = load_json_object(
            cls.scenario_path.parent / "expected.json"
        )
        cls.participants = [
            record
            for record in cls.records
            if record.contract == "event_participant"
        ]

    def test_corpus_registers_p22_03_as_implemented(self) -> None:
        implemented = [
            item["scenario_id"]
            for item in self.corpus["scenarios"]
        ]
        self.assertIn(
            "P22-03",
            implemented,
        )
        self.assertNotIn(
            "P22-03",
            self.corpus["planned_positive_scenarios"],
        )

    def test_p22_03_public_records_are_structurally_valid(self) -> None:
        findings = validate_structural_records(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_03_combined_graph_is_valid(self) -> None:
        findings = validate_graph(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_03_event_has_one_owning_class(self) -> None:
        event = next(
            record
            for record in self.records
            if record.contract == "event"
        )
        self.assertEqual(
            event.value["class_id"],
            self.expected["event_owner_class_id"],
        )
        self.assertEqual(
            {
                record.value["class_id"]
                for record in self.records
                if record.descriptor["authority"] == "portia"
            },
            {self.expected["event_owner_class_id"]},
        )

    def test_p22_03_context_contains_two_distinct_source_rosters(self) -> None:
        contexts = load_contexts(
            self.scenario_path,
            self.scenario,
        )
        rosters = [
            value
            for kind, value in contexts
            if kind == "synthetic_core_roster"
        ]
        self.assertEqual(
            {roster["class_id"] for roster in rosters},
            {"eng10_p2_2026", "journalism_p6_2026"},
        )

    def test_p22_03_collision_uses_same_student_id_and_display_name(self) -> None:
        refs = [
            record.value["subject"]["roster_student_ref"]
            for record in self.participants
        ]
        snapshots = [
            record.value["subject"]["display_snapshot"]["display_name"]
            for record in self.participants
        ]
        self.assertEqual(
            {ref["student_id"] for ref in refs},
            {self.expected["collision_student_id"]},
        )
        self.assertEqual(
            set(snapshots),
            {self.expected["collision_display_name"]},
        )

    def test_p22_03_durable_subject_keys_remain_distinct(self) -> None:
        keys = {
            durable_subject_key(record.value["subject"])
            for record in self.participants
        }
        self.assertEqual(
            keys,
            {
                (
                    "roster_student",
                    "eng10_p2_2026",
                    "stu_collision_001",
                ),
                (
                    "roster_student",
                    "journalism_p6_2026",
                    "stu_collision_001",
                ),
            },
        )

    def test_p22_03_cross_class_participant_keeps_foreign_source_roster(self) -> None:
        cross = next(
            record
            for record in self.participants
            if record.value["participant_id"]
            == self.expected["cross_class_participant_id"]
        )
        self.assertEqual(
            cross.value["class_id"],
            self.expected["event_owner_class_id"],
        )
        self.assertEqual(
            cross.value["subject"]["roster_student_ref"]["class_id"],
            self.expected["cross_class_source_class_id"],
        )

    def test_p22_03_roles_target_event_participants_not_students(self) -> None:
        roles = [
            record
            for record in self.records
            if record.contract == "event_participant_role"
        ]
        target_ids = {
            record.value["target"]["record_ref"]["record_id"]
            for record in roles
        }
        self.assertEqual(
            target_ids,
            set(self.expected["participant_ids"]),
        )
        for record in roles:
            self.assertEqual(
                record.value["target"]["record_ref"]["record_kind"],
                "event_participant",
            )

    def test_p22_03_observation_targets_exact_cross_class_participant(self) -> None:
        observation = next(
            record
            for record in self.records
            if record.contract == "observation"
        )
        self.assertEqual(
            observation.value["observation_id"],
            self.expected["cross_class_observation_id"],
        )
        self.assertEqual(
            observation.value["target"]["record_ref"]["record_id"],
            self.expected["cross_class_participant_id"],
        )
        self.assertEqual(
            observation.value["target"]["record_ref"]["record_kind"],
            "event_participant",
        )

    def test_p22_03_cross_class_identity_does_not_create_second_event_copy(self) -> None:
        events = [
            record
            for record in self.records
            if record.contract == "event"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(
            {
                record.descriptor["owner"]["work_id"]
                for record in self.records
            },
            {events[0].value["work_id"]},
        )


if __name__ == "__main__":
    unittest.main()
