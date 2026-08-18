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
    from .schema_support import (
        load_json_object,
        load_validated_catalog_and_store,
    )
except ImportError:
    from issue_22_graph_validation import (
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


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(21, 26))


class Issue22GraphInvalidResponseSupportOutcomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.loaded = {}
        for scenario_id in CASE_IDS:
            path, scenario = scenario_by_id(cls.corpus, scenario_id)
            cls.loaded[scenario_id] = (
                path,
                scenario,
                load_scenario_records(path, scenario),
                load_contexts(path, scenario),
                load_json_object(path.parent / "expected.json"),
            )

    def test_corpus_registers_g22_021_through_g22_025(self) -> None:
        entries = {
            entry["scenario_id"]: entry
            for entry in self.corpus["scenarios"]
        }
        planned = set(
            self.corpus.get("planned_graph_invalid_scenarios", [])
        )
        for scenario_id in CASE_IDS:
            with self.subTest(scenario_id=scenario_id):
                self.assertIn(scenario_id, entries)
                self.assertEqual(
                    entries[scenario_id]["scenario_kind"],
                    "graph_invalid",
                )
                self.assertNotIn(scenario_id, planned)

    def test_descriptors_preserve_graph_invalid_audit_metadata(
        self,
    ) -> None:
        required = {
            "primary_finding_id",
            "principal_defect",
            "structurally_valid_reason",
            "records_must_remain_unmodified",
            "expected_finding_ids",
        }
        for scenario_id, (_, scenario, _, _, expected) in (
            self.loaded.items()
        ):
            with self.subTest(scenario_id=scenario_id):
                self.assertTrue(required <= set(scenario))
                self.assertEqual(
                    scenario["expected_graph_result"],
                    "invalid",
                )
                self.assertEqual(
                    expected["expected_finding_ids"],
                    scenario["expected_finding_ids"],
                )
                self.assertEqual(
                    expected["primary_finding_id"],
                    scenario["primary_finding_id"],
                )
                self.assertIs(
                    expected["structurally_valid_public_records"],
                    True,
                )

    def test_every_public_record_remains_structurally_valid(self) -> None:
        for scenario_id, (path, scenario, _, _, _) in (
            self.loaded.items()
        ):
            with self.subTest(scenario_id=scenario_id):
                self.assertEqual(
                    validate_structural_records(
                        path,
                        scenario,
                        catalog=self.catalog,
                        store=self.store,
                    ),
                    (),
                )

    def test_each_case_fails_for_exact_declared_finding_set(
        self,
    ) -> None:
        for scenario_id, (path, scenario, _, _, _) in (
            self.loaded.items()
        ):
            with self.subTest(scenario_id=scenario_id):
                actual = [
                    finding.code
                    for finding in validate_graph(
                        path,
                        scenario,
                        catalog=self.catalog,
                        store=self.store,
                    )
                ]
                self.assertEqual(
                    actual,
                    sorted(scenario["expected_finding_ids"]),
                )
                self.assertFalse(
                    any(
                        code.startswith("G22.STRUCTURAL.")
                        for code in actual
                    )
                )

    def test_g22_021_plan_exists_only_in_other_process(self) -> None:
        _, _, records, _, _ = self.loaded["G22-021"]
        implementation = next(
            record for record in records if record.contract == "implementation"
        )
        plan_ref = implementation.value["plan_ref"]
        matches = [
            record
            for record in records
            if (
                record.contract == plan_ref["record_kind"]
                and record.value.get("support_id") == plan_ref["record_id"]
            )
        ]
        self.assertEqual(len(matches), 1)
        self.assertNotEqual(
            matches[0].value["work_id"],
            implementation.value["work_id"],
        )

    def test_g22_022_fidelity_scopes_foreign_implementation(self) -> None:
        _, _, records, _, _ = self.loaded["G22-022"]
        fidelity = next(
            record for record in records if record.contract == "fidelity"
        )
        self.assertEqual(
            fidelity.value["scope"]["kind"],
            "one_implementation",
        )
        scoped_id = fidelity.value["scope"]["implementation_ref"][
            "record_id"
        ]
        implementation = next(
            record
            for record in records
            if (
                record.contract == "implementation"
                and record.value["implementation_id"] == scoped_id
            )
        )
        self.assertNotEqual(
            fidelity.value["work_id"],
            implementation.value["work_id"],
        )
        local_plan = fidelity.value["plan_ref"]
        self.assertTrue(
            any(
                record.contract == local_plan["record_kind"]
                and record.value.get("support_id")
                == local_plan["record_id"]
                and record.value["work_id"] == fidelity.value["work_id"]
                for record in records
            )
        )

    def test_g22_023_outcome_target_is_foreign_participant(self) -> None:
        _, _, records, _, _ = self.loaded["G22-023"]
        outcome = next(
            record for record in records if record.contract == "outcome"
        )
        target_id = outcome.value["target"]["record_ref"]["record_id"]
        participant = next(
            record
            for record in records
            if (
                record.contract == "support_process_participant"
                and record.value["participant_id"] == target_id
            )
        )
        self.assertNotEqual(
            outcome.value["work_id"],
            participant.value["work_id"],
        )
        evaluator_id = outcome.value["evaluator"]["participant_ref"][
            "record_id"
        ]
        evaluator = next(
            record
            for record in records
            if (
                record.contract == "support_process_participant"
                and record.value["participant_id"] == evaluator_id
            )
        )
        self.assertEqual(outcome.value["work_id"], evaluator.value["work_id"])

    def test_g22_024_distinct_later_evaluation_reuses_identity(self) -> None:
        _, _, records, contexts, _ = self.loaded["G22-024"]
        outcome = next(
            record for record in records if record.contract == "outcome"
        )
        kind, context = next(
            item
            for item in contexts
            if item[0] == "synthetic_outcome_identity_write"
        )
        self.assertEqual(kind, "synthetic_outcome_identity_write")
        self.assertEqual(context["operation"], "overwrite_existing_identity")
        self.assertEqual(
            context["semantic_relationship"],
            "distinct_later_timeframe_evaluation",
        )
        self.assertIs(context["timeframe_changed"], True)
        self.assertEqual(
            context["existing_outcome"]["record_id"],
            outcome.value["outcome_id"],
        )
        self.assertEqual(
            context["attempted_later_evaluation"]["record_id"],
            outcome.value["outcome_id"],
        )
        self.assertNotEqual(
            context["existing_timeframe"],
            context["attempted_timeframe"],
        )

    def test_g22_025_historical_process_ref_follows_successor(self) -> None:
        _, _, records, contexts, _ = self.loaded["G22-025"]
        processes = [
            record for record in records if record.contract == "support_process"
        ]
        self.assertEqual(len(processes), 2)
        successor = next(
            record
            for record in processes
            if isinstance(record.value.get("continues_from"), dict)
        )
        predecessor_ref = successor.value["continues_from"]
        predecessor = next(
            record
            for record in processes
            if record.value["work_id"] == predecessor_ref["work_id"]
        )
        _, context = next(
            item
            for item in contexts
            if item[0] == "synthetic_support_process_reference_resolution"
        )
        self.assertEqual(
            context["requested"]["record_id"],
            predecessor.value["work_id"],
        )
        self.assertEqual(
            context["resolved"]["record_id"],
            successor.value["work_id"],
        )
        self.assertEqual(context["resolution_mode"], "follow_current")

    def test_nonruntime_semantic_contexts_are_closed(self) -> None:
        _, _, _, contexts_024, _ = self.loaded["G22-024"]
        _, write = contexts_024[0]
        self.assertEqual(
            set(write),
            {
                "fixture_contract",
                "fixture_version",
                "not_runtime_contract",
                "operation",
                "semantic_relationship",
                "timeframe_changed",
                "existing_outcome",
                "attempted_later_evaluation",
                "existing_timeframe",
                "attempted_timeframe",
            },
        )
        self.assertEqual(
            write["fixture_contract"],
            "pds-portia.synthetic-outcome-identity-write",
        )
        self.assertIs(write["not_runtime_contract"], True)

        _, _, _, contexts_025, _ = self.loaded["G22-025"]
        _, resolution = contexts_025[0]
        self.assertEqual(
            set(resolution),
            {
                "fixture_contract",
                "fixture_version",
                "not_runtime_contract",
                "resolution_kind",
                "requested",
                "resolved",
                "resolution_mode",
            },
        )
        self.assertEqual(
            resolution["fixture_contract"],
            "pds-portia.synthetic-support-process-reference-resolution",
        )
        self.assertIs(resolution["not_runtime_contract"], True)


if __name__ == "__main__":
    unittest.main()
