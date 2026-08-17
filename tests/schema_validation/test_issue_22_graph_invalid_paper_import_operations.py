from __future__ import annotations

import unittest

try:
    from .issue_22_graph_validation import (
        _exact_portia_ref_key,
        load_contexts,
        load_corpus,
        load_operational_contract_fixtures,
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
        _exact_portia_ref_key,
        load_contexts,
        load_corpus,
        load_operational_contract_fixtures,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import (
        load_json_object,
        load_validated_catalog_and_store,
    )


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(26, 30))


class Issue22GraphInvalidPaperImportOperationsTests(unittest.TestCase):
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
                load_operational_contract_fixtures(path, scenario),
                load_json_object(path.parent / "expected.json"),
            )

    def test_corpus_registers_g22_026_through_g22_029(self) -> None:
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
        implemented_prefix = {
            f"G22-{number:03d}" for number in range(1, 30)
        }
        self.assertTrue(implemented_prefix <= set(entries))
        self.assertTrue(implemented_prefix.isdisjoint(planned))

    def test_descriptors_preserve_graph_invalid_audit_metadata(self) -> None:
        required = {
            "primary_finding_id",
            "principal_defect",
            "structurally_valid_reason",
            "records_must_remain_unmodified",
            "expected_finding_ids",
        }
        for scenario_id, (_, scenario, _, _, _, expected) in self.loaded.items():
            with self.subTest(scenario_id=scenario_id):
                self.assertTrue(required <= set(scenario))
                self.assertEqual(scenario["expected_graph_result"], "invalid")
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

    def test_every_public_domain_and_operational_fixture_is_structurally_valid(self) -> None:
        for scenario_id, (path, scenario, _, _, _, _) in self.loaded.items():
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

    def test_each_case_fails_for_exact_declared_finding_set(self) -> None:
        for scenario_id, (path, scenario, _, _, _, _) in self.loaded.items():
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
                    any(code.startswith("G22.STRUCTURAL.") for code in actual)
                )

    def test_g22_026_replays_one_accepted_proposal_into_two_domain_ids(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-026"]
        events = [record for record in records if record.contract == "event"]
        self.assertEqual(len(events), 2)
        self.assertEqual(
            {record.value["creation_source"]["external_reference"] for record in events},
            {"retained-row-g22-026"},
        )
        self.assertEqual(len({record.value["work_id"] for record in events}), 2)
        kind, replay = contexts[0]
        self.assertEqual(kind, "synthetic_import_replay_resolution")
        self.assertEqual(
            replay["resolution_kind"],
            "accepted_proposal_replayed_as_new_domain_record",
        )
        self.assertIs(replay["unchanged_source_and_mapping"], True)
        self.assertNotEqual(replay["first_result"], replay["replayed_result"])

    def test_g22_027_isolates_missing_capture_review_gate(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-027"]
        batch = next(record for record in records if record.contract == "capture_batch")
        receipt = next(
            record for record in records if record.contract == "capture_materialization"
        )
        self.assertEqual(batch.value["work_id"], receipt.value["work_id"])
        self.assertFalse(any(record.contract == "capture_review" for record in records))
        kind, resolution = contexts[0]
        self.assertEqual(kind, "synthetic_capture_materialization_resolution")
        self.assertIs(resolution["proposal_resolves"], True)
        self.assertIs(resolution["review_resolves"], False)
        self.assertEqual(resolution["proposal_ref"], receipt.value["proposal_ref"])
        self.assertEqual(resolution["review_ref"], receipt.value["review_ref"])

    def test_g22_028_committed_journal_has_one_missing_accepted_result(self) -> None:
        _, _, records, _, operational, _ = self.loaded["G22-028"]
        self.assertEqual(len(operational), 1)
        descriptor, journal, _ = operational[0]
        self.assertEqual(descriptor["contract"], "operation_journal")
        self.assertEqual(journal["state"], "completed")
        self.assertIs(journal["commit_point"]["reached"], True)
        existing = {
            (
                record.value.get("class_id"),
                record.value.get("work_id"),
                record.contract,
                (
                    record.value.get("work_id")
                    if record.value.get("record_type") == "portia_work"
                    else record.value.get("relationship_id")
                ),
                record.descriptor["version"],
            )
            for record in records
        }
        accepted = [
            step
            for step in journal["write_set"]
            if step["disposition"] == "accepted"
            and step["representation_role"] == "canonical_domain"
        ]
        keys = [
            _exact_portia_ref_key(step["target"]["work_record_ref"])
            for step in accepted
        ]
        self.assertEqual(len(keys), 2)
        self.assertEqual(sum(key in existing for key in keys), 1)

    def test_g22_029_restart_replays_already_accepted_semantic_write(self) -> None:
        _, _, records, contexts, operational, _ = self.loaded["G22-029"]
        descriptor, journal, _ = operational[0]
        self.assertEqual(descriptor["contract"], "operation_journal")
        self.assertEqual(journal["state"], "committed")
        accepted_ids = {
            step["target"]["work_record_ref"]["record_ref"]["record_id"]
            for step in journal["write_set"]
            if step["disposition"] == "accepted"
        }
        relationship_ids = {
            record.value["relationship_id"]
            for record in records
            if record.contract == "work_relationship"
        }
        self.assertTrue(accepted_ids <= relationship_ids)
        kind, restart = contexts[0]
        self.assertEqual(kind, "synthetic_operation_restart_resolution")
        self.assertEqual(restart["prior_disposition"], "accepted")
        self.assertIs(restart["semantic_write_already_durable"], True)
        self.assertEqual(restart["restart_action"], "replay_semantic_write")
        self.assertEqual(
            restart["required_restart_action"],
            "reconcile_exact_readback",
        )

    def test_nonruntime_semantic_contexts_are_closed(self) -> None:
        expected = {
            "G22-026": (
                "pds-portia.synthetic-import-replay-resolution",
                {
                    "fixture_contract", "fixture_version", "not_runtime_contract",
                    "resolution_kind", "retained_source_identity",
                    "proposal_identity_digest", "accepted_review", "first_result",
                    "replayed_result", "unchanged_source_and_mapping",
                },
            ),
            "G22-027": (
                "pds-portia.synthetic-capture-materialization-resolution",
                {
                    "fixture_contract", "fixture_version", "not_runtime_contract",
                    "materialization_operation_id", "proposal_ref",
                    "proposal_resolves", "review_ref", "review_resolves",
                },
            ),
            "G22-029": (
                "pds-portia.synthetic-operation-restart-resolution",
                {
                    "fixture_contract", "fixture_version", "not_runtime_contract",
                    "operation_id", "journal_revision", "journal_state", "step_id",
                    "prior_disposition", "restart_action",
                    "required_restart_action", "semantic_write_already_durable",
                },
            ),
        }
        for scenario_id, (contract, keys) in expected.items():
            with self.subTest(scenario_id=scenario_id):
                _, _, _, contexts, _, _ = self.loaded[scenario_id]
                self.assertEqual(len(contexts), 1)
                _, value = contexts[0]
                self.assertEqual(set(value), keys)
                self.assertEqual(value["fixture_contract"], contract)
                self.assertIs(value["not_runtime_contract"], True)

    def test_operation_journals_remain_operational_not_domain_records(self) -> None:
        for scenario_id in ("G22-028", "G22-029"):
            with self.subTest(scenario_id=scenario_id):
                _, scenario, records, _, operational, _ = self.loaded[scenario_id]
                self.assertFalse(any(record.contract == "operation_journal" for record in records))
                self.assertEqual(len(operational), 1)
                descriptor, _, _ = operational[0]
                self.assertEqual(
                    descriptor["authority"],
                    "durable_operational_not_domain_truth",
                )
                self.assertTrue(
                    descriptor["canonical_path"].startswith("portia/operations/")
                )
                self.assertIn("operational_contract_fixtures", scenario)


if __name__ == "__main__":
    unittest.main()
