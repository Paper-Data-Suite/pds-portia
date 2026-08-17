from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        load_contexts,
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
        validator_for,
    )
except ImportError:
    from issue_22_graph_validation import (
        load_contexts,
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
        validator_for,
    )


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(11, 17))


class Issue22GraphInvalidLifecycleCorrectionTests(unittest.TestCase):
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

    def test_corpus_registers_g22_011_through_g22_016(self) -> None:
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

    def test_every_public_domain_record_remains_structurally_valid(
        self,
    ) -> None:
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

    def test_g22_012_derived_pointer_is_structurally_valid(self) -> None:
        path, scenario, _, _, _ = self.loaded["G22-012"]
        descriptor = scenario["derived_contract_fixtures"][0]
        value = load_json_object(
            path.parent / descriptor["fixture_path"]
        )
        validator = validator_for(
            descriptor["contract"],
            descriptor["version"],
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(list(validator.iter_errors(value)), [])

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

    def test_semantic_contexts_are_closed_nonruntime_metadata(
        self,
    ) -> None:
        for scenario_id in (
            "G22-012",
            "G22-013",
            "G22-015",
            "G22-016",
        ):
            _, _, _, contexts, _ = self.loaded[scenario_id]
            semantic = [
                value
                for kind, value in contexts
                if kind.startswith("synthetic_")
                and kind != "synthetic_core_roster"
            ]
            with self.subTest(scenario_id=scenario_id):
                self.assertEqual(len(semantic), 1)
                self.assertIs(semantic[0]["not_runtime_contract"], True)
                self.assertEqual(semantic[0]["fixture_version"], "1")
                self.assertTrue(
                    semantic[0]["fixture_contract"].startswith(
                        "pds-portia.synthetic-"
                    )
                )

    def test_g22_011_supersession_cycle_is_two_node_exact_cycle(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-011"]
        accounts = {
            record.value["account_id"]: record
            for record in records
            if record.contract == "account"
        }
        self.assertEqual(
            set(accounts),
            {"acct_g22_011_a", "acct_g22_011_b"},
        )
        for account_id, other_id in (
            ("acct_g22_011_a", "acct_g22_011_b"),
            ("acct_g22_011_b", "acct_g22_011_a"),
        ):
            account = accounts[account_id]
            predecessor = account.value["supersedes"][0][
                "work_record_ref"
            ]["record_ref"]["record_id"]
            self.assertEqual(predecessor, other_id)
            self.assertEqual(
                account.value["status"],
                "superseded",
            )

    def test_g22_012_stale_selection_excludes_active_frontier(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-012"]
        self.assertEqual(
            replacement_frontier(records, "account"),
            ("acct_g22_012_corrected",),
        )
        selection = next(
            value
            for kind, value in contexts
            if kind == "synthetic_derived_current_selection"
        )
        self.assertEqual(
            selection["selected"]["record_id"],
            "acct_g22_012_original",
        )
        self.assertEqual(
            selection["expected_current"]["record_id"],
            "acct_g22_012_corrected",
        )

    def test_g22_013_disagreement_resolves_wrong_existing_account(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-013"]
        disagreement = next(
            record
            for record in records
            if record.contract == "statement_of_disagreement"
        )
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_disagreement_resolution"
        )
        actual = disagreement.value["target"]["record_ref"]
        self.assertEqual(actual, resolution["actual_target"])
        self.assertNotEqual(
            actual,
            resolution["intended_target"],
        )
        account_ids = {
            record.value["account_id"]
            for record in records
            if record.contract == "account"
        }
        self.assertIn(
            resolution["actual_target"]["record_id"],
            account_ids,
        )
        self.assertIn(
            resolution["intended_target"]["record_id"],
            account_ids,
        )

    def test_g22_014_required_dependency_only_matches_other_work(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-014"]
        dependency = next(
            record for record in records if record.contract == "dependency"
        )
        account = next(
            record for record in records if record.contract == "account"
        )
        ref = dependency.value["dependency"]["work_record_ref"]
        self.assertEqual(
            ref["record_ref"]["record_id"],
            account.value["account_id"],
        )
        self.assertNotEqual(
            ref["work_ref"]["work_id"],
            account.value["work_id"],
        )
        self.assertEqual(dependency.value["strength"], "required")

    def test_g22_015_migration_retargets_after_substantive_change(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-015"]
        versions = {
            record.version: record
            for record in records
            if record.contract == "event"
        }
        self.assertEqual(set(versions), {"1", "2"})
        self.assertNotEqual(
            versions["1"].value["summary"],
            versions["2"].value["summary"],
        )
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_migration_resolution"
        )
        self.assertIs(resolution["semantic_change"], True)
        self.assertIs(resolution["rewrite_exact_reference"], True)
        self.assertNotEqual(
            resolution["historical_reference"],
            resolution["resolved_after_migration"],
        )

    def test_g22_016_new_year_work_uses_migration_not_continues_from(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-016"]
        processes = [
            record
            for record in records
            if record.contract == "support_process"
        ]
        self.assertEqual(len(processes), 2)
        successor = next(
            record
            for record in processes
            if record.value["school_year"] == "2027-2028"
        )
        self.assertNotIn("continues_from", successor.value)
        migration = next(
            record
            for record in records
            if record.contract == "record_migration"
        )
        self.assertNotEqual(
            migration.value["source"]["work_ref"]["class_id"],
            migration.value["destination"]["work_ref"]["class_id"],
        )
        resolution = next(
            value
            for kind, value in contexts
            if kind
            == "synthetic_cross_year_continuation_resolution"
        )
        self.assertEqual(resolution["encoding"], "record_migration")


if __name__ == "__main__":
    unittest.main()
