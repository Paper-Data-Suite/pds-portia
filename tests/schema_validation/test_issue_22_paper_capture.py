from __future__ import annotations

import hashlib
import unittest

try:
    from .issue_22_graph_validation import (
        CORPUS_ROOT,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        _canonical_path_for_record,
        _id_for_record,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import load_json_object, load_validated_catalog_and_store
except ImportError:
    from issue_22_graph_validation import (
        CORPUS_ROOT,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        _canonical_path_for_record,
        _id_for_record,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import load_json_object, load_validated_catalog_and_store


class Issue22PaperCaptureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(cls.corpus, "P22-05")
        cls.records = load_scenario_records(cls.scenario_path, cls.scenario)
        cls.expected = load_json_object(cls.scenario_path.parent / "expected.json")
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)

    def test_corpus_registers_p22_05_as_implemented(self) -> None:
        implemented = {item["scenario_id"] for item in self.corpus["scenarios"]}
        self.assertIn("P22-05", implemented)
        self.assertNotIn("P22-05", self.corpus["planned_positive_scenarios"])

    def test_p22_05_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_05_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_05_capture_identity_is_not_shadowed_by_lineage_ids(self) -> None:
        expected_ids = {
            "page_target": "ptgt_p22_paper_001",
            "page_record": "prec_p22_paper_001",
            "paper_interpretation": "pint_p22_paper_001",
            "capture_proposal": "cprp_p22_paper_001",
            "capture_review": "crev_p22_paper_001",
            "capture_materialization": (
                "op_p22_paper_create_event_001--r3--"
                "crev_p22_paper_001--s1"
            ),
        }
        for contract, expected_id in expected_ids.items():
            with self.subTest(contract=contract):
                record = self.by_contract[contract][0]
                self.assertEqual(_id_for_record(record), expected_id)
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )

    def test_p22_05_contains_complete_capture_contract_chain(self) -> None:
        self.assertEqual(
            set(self.by_contract),
            {
                "capture_batch",
                "page_target",
                "page_record",
                "paper_interpretation",
                "capture_proposal",
                "capture_review",
                "event",
                "capture_materialization",
            },
        )

    def test_p22_05_retained_source_bytes_have_truthful_digest_and_length(self) -> None:
        source = CORPUS_ROOT / "shared/source-bytes/p22-05-returned-page.bmp"
        data = source.read_bytes()
        self.assertTrue(data.startswith(b"BM"))
        self.assertEqual(hashlib.sha256(data).hexdigest(), self.expected["source_sha256"])
        self.assertEqual(len(data), self.expected["source_byte_length"])

    def test_p22_05_page_record_matches_core_route_and_source(self) -> None:
        contexts = load_contexts(self.scenario_path, self.scenario)
        core = next(v for k, v in contexts if k == "synthetic_core_pds2")
        page = self.by_contract["page_record"][0].value
        self.assertEqual(page["route_id"], core["route"]["route_id"])
        self.assertEqual(core["route"]["target"]["record_id"], page["page_target_id"])
        self.assertEqual(
            page["source_ref"]["source_sha256"],
            core["retained_source"]["source_sha256"],
        )

    def test_p22_05_interpretation_is_candidate_staging(self) -> None:
        interpretation = self.by_contract["paper_interpretation"][0].value
        entry = interpretation["entries"]["entry"]
        self.assertEqual(interpretation["interpretation_status"], "complete")
        self.assertEqual(entry["entry_state"], "candidate")
        self.assertEqual(entry["mapped_record_kind"], "event")
        self.assertEqual(
            {f["recognition_state"] for f in entry["fields"].values()},
            {"candidate_detected"},
        )

    def test_p22_05_layout_snapshot_matches_page_target_exactly(self) -> None:
        target = self.by_contract["page_target"][0].value
        interpretation = self.by_contract["paper_interpretation"][0].value
        self.assertEqual(interpretation["layout_snapshot"], target["template_identity"])
        self.assertEqual(
            target["template_identity"]["layout_fingerprint"],
            self.expected["layout_sha256"],
        )

    def test_p22_05_proposal_binds_fields_without_copying_values(self) -> None:
        proposal = self.by_contract["capture_proposal"][0].value
        self.assertEqual(
            {b["target_path"] for b in proposal["field_bindings"]},
            {"/occurrence/started_at", "/summary"},
        )
        self.assertNotIn(self.expected["event_summary"], str(proposal))

    def test_p22_05_teacher_review_is_capture_gate_not_domain_judgment(self) -> None:
        review = self.by_contract["capture_review"][0].value
        self.assertEqual(review["disposition"], "accepted")
        self.assertEqual(review["reviewer"]["kind"], "local_operator")
        self.assertEqual(review["field_reviews"], [])
        self.assertTrue(
            {"classification", "hypothesis", "determination"}.isdisjoint(
                self.by_contract
            )
        )

    def test_p22_05_event_has_exact_ingested_paper_provenance(self) -> None:
        event = self.by_contract["event"][0].value
        self.assertEqual(event["work_id"], self.expected["materialized_event_id"])
        self.assertEqual(
            event["creation_source"],
            self.expected["paper_creation_source"],
        )

    def test_p22_05_event_domain_time_is_not_pipeline_time(self) -> None:
        event = self.by_contract["event"][0].value
        page = self.by_contract["page_record"][0].value
        interpretation = self.by_contract["paper_interpretation"][0].value
        review = self.by_contract["capture_review"][0].value
        domain_time = event["occurrence"]["started_at"]
        self.assertEqual(domain_time, self.expected["event_occurrence_started_at"])
        self.assertNotEqual(domain_time, page["created_at"])
        self.assertNotEqual(domain_time, interpretation["interpreted_at"])
        self.assertNotEqual(domain_time, review["reviewed_at"])

    def test_p22_05_accepted_candidates_match_event_fields(self) -> None:
        event = self.by_contract["event"][0].value
        fields = self.by_contract["paper_interpretation"][0].value[
            "entries"
        ]["entry"]["fields"]
        self.assertEqual(
            event["occurrence"]["started_at"],
            fields["event_time"]["candidate_literal"],
        )
        self.assertEqual(event["summary"], fields["summary"]["candidate_literal"])

    def test_p22_05_receipt_resolves_review_operation_and_event(self) -> None:
        receipt = self.by_contract["capture_materialization"][0].value
        contexts = load_contexts(self.scenario_path, self.scenario)
        operation = next(
            v for k, v in contexts if k == "synthetic_operation_acceptance"
        )
        self.assertEqual(receipt["review_ref"]["review_id"], self.expected["review_id"])
        self.assertEqual(
            receipt["operation_journal_ref"]["operation_id"],
            operation["operation_id"],
        )
        self.assertEqual(
            receipt["canonical_results"][0]["target"]["work_ref"]["work_id"],
            self.expected["materialized_event_id"],
        )

    def test_p22_05_receipt_follows_canonical_creation(self) -> None:
        receipt = self.by_contract["capture_materialization"][0].value
        event = self.by_contract["event"][0].value
        self.assertLess(event["created_at"], receipt["materialized_at"])
        self.assertLessEqual(receipt["materialized_at"], receipt["recorded_at"])

    def test_p22_05_physical_page_idempotency_tuple_is_explicit(self) -> None:
        page = self.by_contract["page_record"][0].value
        self.assertEqual(
            [
                page["route_id"],
                page["source_ref"]["source_scan_id"],
                page["source_ref"]["source_page_number"],
            ],
            self.expected["idempotency_tuple"],
        )


if __name__ == "__main__":
    unittest.main()
