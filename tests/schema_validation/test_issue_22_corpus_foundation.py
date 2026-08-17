from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        CORPUS_CONTRACT,
        FIXTURE_VERSION,
        SCENARIO_CONTRACT,
        build_teacher_current_summary,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import (
        REPO_ROOT,
        load_json_object,
        load_validated_catalog_and_store,
    )
except ImportError:
    from issue_22_graph_validation import (
        CORPUS_CONTRACT,
        FIXTURE_VERSION,
        SCENARIO_CONTRACT,
        build_teacher_current_summary,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import (
        REPO_ROOT,
        load_json_object,
        load_validated_catalog_and_store,
    )


class Issue22CorpusFoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus,
            "P22-01",
        )
        cls.records = load_scenario_records(
            cls.scenario_path,
            cls.scenario,
        )
        cls.expected = load_json_object(
            cls.scenario_path.parent / "expected.json"
        )

    def test_corpus_descriptor_is_versioned_synthetic_non_runtime(self) -> None:
        self.assertEqual(
            self.corpus["fixture_contract"],
            CORPUS_CONTRACT,
        )
        self.assertEqual(
            self.corpus["fixture_version"],
            FIXTURE_VERSION,
        )
        self.assertIs(self.corpus["not_runtime_contract"], True)
        self.assertIs(self.corpus["synthetic"], True)
        self.assertEqual(self.corpus["issue"], 22)
        self.assertEqual(
            self.corpus["graph_finding_namespace"],
            "G22",
        )

    def test_corpus_inventory_partitions_required_positive_scenarios(self) -> None:
        implemented_positive = [
            item["scenario_id"]
            for item in self.corpus["scenarios"]
            if item.get("scenario_kind") == "positive"
        ]
        planned_positive = list(
            self.corpus["planned_positive_scenarios"]
        )
        required_positive = {
            f"P22-{number:02d}"
            for number in range(1, 15)
        }

        self.assertTrue(
            required_positive <= set(implemented_positive)
        )
        self.assertEqual(planned_positive, [])
        self.assertEqual(
            set(implemented_positive) & set(planned_positive),
            set(),
        )
        self.assertEqual(
            len(implemented_positive),
            len(set(implemented_positive)),
        )
        self.assertEqual(
            len(planned_positive),
            len(set(planned_positive)),
        )

    def test_p22_01_scenario_descriptor_is_closed_test_metadata(self) -> None:
        self.assertEqual(
            self.scenario["fixture_contract"],
            SCENARIO_CONTRACT,
        )
        self.assertEqual(
            self.scenario["fixture_version"],
            FIXTURE_VERSION,
        )
        self.assertIs(self.scenario["not_runtime_contract"], True)
        self.assertIs(self.scenario["synthetic"], True)
        self.assertEqual(
            self.scenario["expected_graph_result"],
            "valid",
        )
        self.assertEqual(
            self.scenario["expected_finding_ids"],
            [],
        )

    def test_p22_01_uses_exact_current_contract_versions(self) -> None:
        actual = {
            record.contract: record.version
            for record in self.records
        }
        self.assertEqual(
            actual,
            {
                "event": "2",
                "event_participant": "3",
                "event_participant_role": "3",
                "observation": "2",
            },
        )

    def test_p22_01_public_records_are_structurally_valid(self) -> None:
        findings = validate_structural_records(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_01_combined_graph_is_valid(self) -> None:
        findings = validate_graph(
            self.scenario_path,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_01_roster_identity_is_exact_class_plus_student(self) -> None:
        contexts = load_contexts(
            self.scenario_path,
            self.scenario,
        )
        self.assertEqual(len(contexts), 1)
        kind, roster = contexts[0]
        self.assertEqual(kind, "synthetic_core_roster")
        self.assertEqual(roster["class_id"], "eng10_p2_2026")

        participant = next(
            record
            for record in self.records
            if record.contract == "event_participant"
        )
        ref = participant.value["subject"]["roster_student_ref"]
        self.assertEqual(
            ref,
            {
                "class_id": "eng10_p2_2026",
                "student_id": "stu_p22_001",
            },
        )
        self.assertEqual(
            participant.value["subject"]["display_snapshot"],
            {"display_name": "Synthetic Student A"},
        )

    def test_p22_01_canonical_paths_follow_portia_work_layout(self) -> None:
        root = (
            "classes/eng10_p2_2026/modules/portia/work/"
            "evt_p22_positive_001"
        )
        by_contract = {
            record.contract: record.descriptor["canonical_path"]
            for record in self.records
        }
        self.assertEqual(by_contract["event"], f"{root}/work.json")
        self.assertEqual(
            by_contract["event_participant"],
            (
                f"{root}/records/event_participant/"
                "ep_p22_positive_001.json"
            ),
        )
        self.assertEqual(
            by_contract["event_participant_role"],
            (
                f"{root}/records/event_participant_role/"
                "epr_p22_positive_001.json"
            ),
        )
        self.assertEqual(
            by_contract["observation"],
            (
                f"{root}/records/observation/"
                "obs_p22_positive_001.json"
            ),
        )

    def test_p22_01_targets_exact_participant_without_inferring_role(self) -> None:
        participant = next(
            record
            for record in self.records
            if record.contract == "event_participant"
        )
        participant_id = participant.value["participant_id"]

        role = next(
            record
            for record in self.records
            if record.contract == "event_participant_role"
        )
        observation = next(
            record
            for record in self.records
            if record.contract == "observation"
        )

        self.assertEqual(role.value["role_type"], "present")
        self.assertEqual(
            role.value["target"]["record_ref"]["record_id"],
            participant_id,
        )
        self.assertEqual(
            observation.value["target"]["record_ref"]["record_id"],
            participant_id,
        )
        self.assertEqual(
            observation.value["method"],
            "live_direct",
        )

    def test_p22_01_teacher_current_summary_rebuild_is_deterministic(self) -> None:
        first = build_teacher_current_summary(
            self.scenario_path,
            self.scenario,
        )
        second = build_teacher_current_summary(
            self.scenario_path,
            self.scenario,
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            self.expected["expected_teacher_current"],
        )

    def test_p22_01_does_not_fabricate_downstream_judgment_or_response(self) -> None:
        record_types = {
            str(record.value.get("record_type"))
            for record in self.records
        }
        for forbidden in self.expected["forbidden_record_types"]:
            self.assertNotIn(forbidden, record_types)

        observation = next(
            record
            for record in self.records
            if record.contract == "observation"
        )
        narrative = observation.value["content"]["narrative"]
        self.assertIn("raised a hand", narrative)
        self.assertNotIn("guilty", narrative.lower())
        self.assertNotIn("intent", narrative.lower())
        self.assertNotIn("risk", narrative.lower())

    def test_slice_one_documents_no_public_schema_or_adr_delta(self) -> None:
        design = (
            REPO_ROOT
            / "docs"
            / "design"
            / "portia-representative-synthetic-graph-corpus.md"
        ).read_text(encoding="utf-8")
        checkpoint = (
            REPO_ROOT
            / "docs"
            / "validation"
            / "issue-22-initial-repository-checkpoint.md"
        ).read_text(encoding="utf-8")

        self.assertIn("No new public contract by default", design)
        self.assertIn("none", checkpoint)
        self.assertIn("ADR 0018 is not allocated", checkpoint)


if __name__ == "__main__":
    unittest.main()
