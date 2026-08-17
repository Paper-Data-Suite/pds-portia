from __future__ import annotations

import hashlib
import unittest

try:
    from .issue_22_graph_validation import (
        _exact_portia_ref_key,
        load_contexts,
        load_corpus,
        load_derived_contract_fixtures,
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
        _exact_portia_ref_key,
        load_contexts,
        load_corpus,
        load_derived_contract_fixtures,
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


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(30, 38))


class Issue22GraphInvalidPrivacyExportDerivedCustodyTests(unittest.TestCase):
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
                load_derived_contract_fixtures(path, scenario),
                load_json_object(path.parent / "expected.json"),
            )

    def test_corpus_registers_g22_030_through_g22_037(self) -> None:
        entries = {
            entry["scenario_id"]: entry
            for entry in self.corpus["scenarios"]
        }
        for scenario_id in CASE_IDS:
            with self.subTest(scenario_id=scenario_id):
                self.assertIn(scenario_id, entries)
                self.assertEqual(
                    entries[scenario_id]["scenario_kind"],
                    "graph_invalid",
                )
        self.assertEqual(
            self.corpus.get("planned_graph_invalid_scenarios"),
            [],
        )

    def test_all_37_enumerated_graph_invalid_cases_are_registered(self) -> None:
        implemented = {
            entry["scenario_id"]
            for entry in self.corpus["scenarios"]
            if entry["scenario_kind"] == "graph_invalid"
        }
        self.assertEqual(
            implemented,
            {f"G22-{number:03d}" for number in range(1, 38)},
        )

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

    def test_every_public_domain_export_and_derived_fixture_is_structurally_valid(self) -> None:
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

    def test_g22_030_focal_projection_exposes_unrelated_exact_sources(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-030"]
        kind, value = next(
            item for item in contexts
            if item[0] == "synthetic_participant_projection_result"
        )
        self.assertEqual(kind, "synthetic_participant_projection_result")
        self.assertEqual(value["projection_purpose"], "participant_specific")
        self.assertEqual(value["focal_subject"]["record_id"], "ep_p22_privacy_b")
        self.assertEqual(value["emitted_unrelated_stable_id"], "ep_p22_privacy_a")
        self.assertIs(value["unsafe_account_segment_included"], True)
        ids = {
            record.value.get("participant_id") or record.value.get("account_id")
            for record in records
        }
        self.assertIn("ep_p22_privacy_a", ids)
        self.assertIn("acct_p22_privacy_a", ids)

    def test_g22_031_preserves_withheld_and_unavailable_semantics(self) -> None:
        _, _, _, contexts, _, _ = self.loaded["G22-031"]
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_projection_state_serialization"
        )
        by_id = {item["item_id"]: item for item in value["items"]}
        self.assertEqual(
            by_id["third_party_identity"],
            {
                "item_id": "third_party_identity",
                "source_disposition": "withheld",
                "serialized_representation": "absent",
            },
        )
        self.assertEqual(
            by_id["external_context"]["source_disposition"],
            "unavailable",
        )
        self.assertIs(
            by_id["external_context"]["serialized_representation"],
            False,
        )

    def test_g22_032_inventory_fingerprint_is_truthful_for_wrong_successor(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-032"]
        export = next(record for record in records if record.contract == "deliberate_export")
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_export_consumption_resolution"
        )
        consumed = value["consumed_exact_source"]
        bound = value["inventory_bound_source"]
        self.assertNotEqual(consumed, bound)
        entries = export.value["source_inventory"]["entries"]
        bound_entry = next(
            entry for entry in entries
            if entry["source_kind"] == "portia_record"
            and entry["work_record_ref"]["record_ref"]["record_id"]
            == bound["record_id"]
        )
        bound_record = next(
            record for record in records
            if record.contract == bound["record_kind"]
            and record.value.get("account_id") == bound["record_id"]
        )
        payload = bound_record.path.read_bytes()
        self.assertEqual(
            bound_entry["representation_digest"],
            hashlib.sha256(payload).hexdigest(),
        )
        self.assertEqual(bound_entry["byte_length"], len(payload))
        inventory_keys = {
            _exact_portia_ref_key(entry["work_record_ref"])
            for entry in entries
            if entry["source_kind"] == "portia_record"
        }
        consumed_key = (
            consumed["class_id"], consumed["work_id"], consumed["record_kind"],
            consumed["record_id"], consumed["contract_version"],
        )
        self.assertNotIn(consumed_key, inventory_keys)

    def test_g22_033_path_is_id_scoped_but_not_pii_minimized(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-033"]
        export = next(record for record in records if record.contract == "deliberate_export")
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_export_path_privacy_context"
        )
        output_path = export.value["output"]["workspace_relative_path"]
        self.assertTrue(
            output_path.startswith(
                f"portia/exports/{export.value['export_id']}/"
            )
        )
        self.assertEqual(output_path, value["output_path"])
        for label in value["synthetic_sensitive_labels"]:
            with self.subTest(label=label):
                self.assertIn(label, output_path)

    def test_g22_034_incoming_index_contradicts_forward_relationship(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-034"]
        relationship = next(record for record in records if record.contract == "work_relationship")
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_incoming_reference_index"
        )
        self.assertEqual(
            relationship.value["target"]["work_id"],
            value["canonical_target_work"]["work_id"],
        )
        self.assertNotEqual(
            value["canonical_target_work"],
            value["indexed_target_work"],
        )
        self.assertIs(value["accepted_as_authoritative"], True)

    def test_g22_035_current_view_contains_superseded_predecessor(self) -> None:
        _, _, records, contexts, _, _ = self.loaded["G22-035"]
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_derived_current_view"
        )
        self.assertEqual(
            replacement_frontier(records, "account"),
            ("acct_p22_derived_corrected",),
        )
        self.assertEqual(
            set(value["current_record_ids"]),
            {"acct_p22_derived_original", "acct_p22_derived_corrected"},
        )

    def test_g22_036_source_snapshot_is_valid_but_stale_against_current_bytes(self) -> None:
        _, _, records, contexts, derived, _ = self.loaded["G22-036"]
        self.assertEqual(len(derived), 1)
        descriptor, snapshot, _ = derived[0]
        self.assertEqual(descriptor["contract"], "source_snapshot")
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_stale_source_snapshot_acceptance"
        )
        current = next(
            record for record in records
            if record.contract == "account"
            and record.value["account_id"] == value["source_record"]["record_id"]
        )
        current_digest = hashlib.sha256(current.path.read_bytes()).hexdigest()
        self.assertNotEqual(value["snapshot_representation_digest"], current_digest)
        entry = next(
            item for item in snapshot["entries"]
            if item["workspace_relative_path"]
            == value["snapshot_workspace_relative_path"]
        )
        self.assertEqual(entry["sha256_digest"], value["snapshot_representation_digest"])
        self.assertIs(value["stale_derived_result_accepted"], True)

    def test_g22_037_foreign_destruction_claims_have_no_owner_verification(self) -> None:
        _, _, _, contexts, _, _ = self.loaded["G22-037"]
        value = next(
            item for kind, item in contexts
            if kind == "synthetic_disposition_custody_result"
        )
        self.assertEqual(value["portia_local_disposition"], "completed")
        self.assertIs(value["global_completion_reported"], True)
        for owner, claim in value["foreign_destruction_claims"].items():
            with self.subTest(owner=owner):
                self.assertEqual(claim, "destroyed")
                self.assertIs(value["owner_verification"][owner], False)

    def test_nonruntime_semantic_contexts_are_closed(self) -> None:
        expected = {
            "synthetic_participant_projection_result": (
                "pds-portia.synthetic-participant-projection-result",
                {
                    "fixture_contract", "fixture_version", "not_runtime_contract",
                    "projection_purpose", "focal_subject", "emitted_unrelated_refs",
                    "emitted_unrelated_stable_id", "unsafe_account_segment_included",
                },
            ),
            "synthetic_projection_state_serialization": (
                "pds-portia.synthetic-projection-state-serialization",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "items", "accepted_output"},
            ),
            "synthetic_export_consumption_resolution": (
                "pds-portia.synthetic-export-consumption-resolution",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "export_id", "consumed_exact_source", "inventory_bound_source", "successor_relationship", "inventory_fingerprint_truthful_for_bound_source"},
            ),
            "synthetic_export_path_privacy_context": (
                "pds-portia.synthetic-export-path-privacy-context",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "export_id", "output_path", "synthetic_sensitive_labels", "path_is_export_id_scoped", "pii_minimized_path_required"},
            ),
            "synthetic_incoming_reference_index": (
                "pds-portia.synthetic-incoming-reference-index",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "index_kind", "relationship_id", "canonical_target_work", "indexed_target_work", "accepted_as_authoritative"},
            ),
            "synthetic_derived_current_view": (
                "pds-portia.synthetic-derived-current-view",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "record_contract", "current_record_ids", "selection_basis", "accepted_as_current"},
            ),
            "synthetic_stale_source_snapshot_acceptance": (
                "pds-portia.synthetic-stale-source-snapshot-acceptance",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "source_record", "snapshot_workspace_relative_path", "snapshot_representation_digest", "source_changed_after_snapshot", "stale_derived_result_accepted"},
            ),
            "synthetic_disposition_custody_result": (
                "pds-portia.synthetic-disposition-custody-result",
                {"fixture_contract", "fixture_version", "not_runtime_contract", "portia_local_disposition", "foreign_destruction_claims", "owner_verification", "global_completion_reported"},
            ),
        }
        for scenario_id, (_, _, _, contexts, _, _) in self.loaded.items():
            with self.subTest(scenario_id=scenario_id):
                semantic = [item for item in contexts if item[0] != "synthetic_core_roster"]
                self.assertEqual(len(semantic), 1)
                kind, value = semantic[0]
                contract, keys = expected[kind]
                self.assertEqual(set(value), keys)
                self.assertEqual(value["fixture_contract"], contract)
                self.assertIs(value["not_runtime_contract"], True)


if __name__ == "__main__":
    unittest.main()
