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


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(17, 21))


class Issue22GraphInvalidEvidenceJudgmentTests(unittest.TestCase):
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

    def test_corpus_registers_g22_017_through_g22_020(self) -> None:
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

    def test_g22_017_reported_role_has_unresolved_account_basis(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-017"]
        role = next(
            record
            for record in records
            if record.contract == "event_participant_role"
        )
        self.assertEqual(role.value["status"], "active")
        self.assertEqual(role.value["role_type"], "reported_involved")
        account_basis = [
            entry
            for entry in role.value["basis"]
            if entry["kind"] == "account_ref"
        ]
        self.assertEqual(len(account_basis), 1)
        ref = account_basis[0]["record_ref"]
        self.assertEqual(
            ref["record_id"],
            "acct_g22_017_missing",
        )
        self.assertFalse(
            any(
                record.contract == "account"
                and record.value.get("account_id") == ref["record_id"]
                for record in records
            )
        )

    def test_g22_018_evidence_exists_but_in_wrong_event(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-018"]
        determination = next(
            record for record in records if record.contract == "determination"
        )
        observation = next(
            record for record in records if record.contract == "observation"
        )
        evidence = determination.value["basis"][0][
            "evidence_ref"
        ]["work_record_ref"]
        self.assertEqual(
            evidence["record_ref"]["record_id"],
            observation.value["observation_id"],
        )
        self.assertEqual(
            evidence["work_ref"]["work_id"],
            observation.value["work_id"],
        )
        self.assertNotEqual(
            determination.value["work_id"],
            observation.value["work_id"],
        )

    def test_g22_019_isolates_missing_review_gate(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-019"]
        determination = next(
            record for record in records if record.contract == "determination"
        )
        self.assertEqual(determination.value["status"], "active")
        self.assertEqual(
            determination.value["creation_source"]["type"],
            "import",
        )
        self.assertEqual(
            determination.value["decision_maker"]["kind"],
            "local_operator",
        )
        self.assertNotIn("review_ref", determination.value)

    def test_g22_020_has_completed_review_but_no_human_decision(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-020"]
        review = next(
            record for record in records if record.contract == "review"
        )
        determination = next(
            record for record in records if record.contract == "determination"
        )
        self.assertEqual(review.value["review_state"], "completed")
        self.assertEqual(
            determination.value["review_ref"]["record_ref"]["record_id"],
            review.value["review_id"],
        )
        semantic = next(
            value
            for kind, value in contexts
            if kind == "synthetic_import_assertion_judgment_resolution"
        )
        self.assertEqual(semantic["review_scope"], "source_mapping_only")
        self.assertIs(
            semantic["source_assertion_used_as_determination"],
            True,
        )
        self.assertIs(semantic["human_decision_occurred"], False)

    def test_g22_020_semantic_context_is_closed_nonruntime_metadata(
        self,
    ) -> None:
        _, _, _, contexts, _ = self.loaded["G22-020"]
        kind, semantic = next(
            item
            for item in contexts
            if item[0] == "synthetic_import_assertion_judgment_resolution"
        )
        self.assertEqual(
            kind,
            "synthetic_import_assertion_judgment_resolution",
        )
        self.assertEqual(
            set(semantic),
            {
                "fixture_contract",
                "fixture_version",
                "not_runtime_contract",
                "source_assertion",
                "determination_ref",
                "review_ref",
                "review_scope",
                "source_assertion_used_as_determination",
                "human_decision_occurred",
            },
        )
        self.assertEqual(
            semantic["fixture_contract"],
            "pds-portia.synthetic-import-assertion-judgment-resolution",
        )
        self.assertEqual(semantic["fixture_version"], "1")
        self.assertIs(semantic["not_runtime_contract"], True)


if __name__ == "__main__":
    unittest.main()
