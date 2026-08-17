from __future__ import annotations

import csv
import hashlib
import unittest

try:
    from .issue_22_graph_validation import (
        CORPUS_ROOT,
        ISSUE22_IMPORT_DIGEST_RECIPE,
        _canonical_path_for_record,
        issue22_fixture_digest,
        issue22_import_batch_identity_payload,
        issue22_import_proposal_identity_payload,
        issue22_import_source_content_payload,
        issue22_import_source_identity_payload,
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
        CORPUS_ROOT,
        ISSUE22_IMPORT_DIGEST_RECIPE,
        _canonical_path_for_record,
        issue22_fixture_digest,
        issue22_import_batch_identity_payload,
        issue22_import_proposal_identity_payload,
        issue22_import_source_content_payload,
        issue22_import_source_identity_payload,
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


class Issue22StructuredImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(
            cls.corpus,
            "P22-06",
        )
        cls.records = load_scenario_records(
            cls.scenario_path,
            cls.scenario,
        )
        cls.expected = load_json_object(
            cls.scenario_path.parent / "expected.json"
        )
        cls.by_contract = {}
        for record in cls.records:
            cls.by_contract.setdefault(
                record.contract,
                [],
            ).append(record)

        cls.original_batch = next(
            record
            for record in cls.by_contract["import_batch"]
            if record.value["import_batch_id"]
            == cls.expected["original_import_batch_id"]
        )
        cls.later_batch = next(
            record
            for record in cls.by_contract["import_batch"]
            if record.value["import_batch_id"]
            == cls.expected["later_import_batch_id"]
        )
        cls.source = cls.by_contract["import_source_record"][0]
        cls.proposal = cls.by_contract["import_proposal"][0]
        cls.review = cls.by_contract["import_review"][0]
        cls.event = cls.by_contract["event"][0]
        cls.receipt = cls.by_contract["import_materialization"][0]

    def test_corpus_registers_p22_06_as_implemented(self) -> None:
        implemented = {
            item["scenario_id"]
            for item in self.corpus["scenarios"]
        }
        self.assertIn("P22-06", implemented)
        self.assertNotIn(
            "P22-06",
            self.corpus["planned_positive_scenarios"],
        )

    def test_p22_06_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(
            validate_structural_records(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_06_combined_graph_is_valid(self) -> None:
        self.assertEqual(
            validate_graph(
                self.scenario_path,
                self.scenario,
                catalog=self.catalog,
                store=self.store,
            ),
            (),
        )

    def test_p22_06_contains_complete_import_contract_chain(self) -> None:
        self.assertEqual(
            set(self.by_contract),
            {
                "import_batch",
                "import_source_record",
                "import_proposal",
                "import_review",
                "event",
                "import_materialization",
            },
        )
        self.assertEqual(
            len(self.by_contract["import_batch"]),
            2,
        )

    def test_p22_06_import_records_are_class_local_not_work_records(self) -> None:
        for contract in (
            "import_batch",
            "import_source_record",
            "import_proposal",
            "import_review",
            "import_materialization",
        ):
            for record in self.by_contract[contract]:
                with self.subTest(
                    contract=contract,
                    identity=record.logical_identity,
                ):
                    self.assertNotIn("work_id", record.value)
                    self.assertEqual(
                        record.descriptor["owner"]["owner_kind"],
                        "import_batch",
                    )
                    self.assertEqual(
                        _canonical_path_for_record(record),
                        record.descriptor["canonical_path"],
                    )

    def test_p22_06_source_snapshots_have_truthful_bytes(self) -> None:
        for prefix in ("source_v1", "source_v2"):
            path = CORPUS_ROOT / self.expected[
                f"{prefix}_fixture_path"
            ].removeprefix("tests/fixtures/issue_22/")
            data = path.read_bytes()
            self.assertEqual(
                hashlib.sha256(data).hexdigest(),
                self.expected[f"{prefix}_sha256"],
            )
            self.assertEqual(
                len(data),
                self.expected[f"{prefix}_byte_length"],
            )

    def test_p22_06_uses_explicit_fixture_digest_recipe(self) -> None:
        self.assertEqual(
            ISSUE22_IMPORT_DIGEST_RECIPE,
            self.expected["fixture_digest_recipe"],
        )

    def test_p22_06_original_batch_identity_digest_recomputes(self) -> None:
        self.assertEqual(
            issue22_fixture_digest(
                issue22_import_batch_identity_payload(
                    self.original_batch.value
                )
            ),
            self.original_batch.value["import_identity_digest"],
        )

    def test_p22_06_later_batch_identity_differs_for_changed_source(self) -> None:
        self.assertNotEqual(
            self.original_batch.value["import_identity_digest"],
            self.later_batch.value["import_identity_digest"],
        )
        self.assertEqual(
            self.later_batch.value["comparison_to_previous"],
            {
                "previous_import_batch_id": (
                    self.expected["original_import_batch_id"]
                ),
                "relationship": (
                    self.expected["later_snapshot_relationship"]
                ),
            },
        )

    def test_p22_06_source_record_content_and_identity_digests_recompute(self) -> None:
        self.assertEqual(
            issue22_fixture_digest(
                issue22_import_source_content_payload(
                    self.source.value
                )
            ),
            self.source.value["source_record_digest"],
        )
        self.assertEqual(
            issue22_fixture_digest(
                issue22_import_source_identity_payload(
                    self.original_batch.value,
                    self.source.value,
                )
            ),
            self.source.value["source_record_identity_digest"],
        )

    def test_p22_06_source_identity_uses_stable_key_not_row_position(self) -> None:
        self.assertEqual(
            self.source.value["source_record_key_origin"],
            "source_provided",
        )
        self.assertEqual(
            self.source.value["source_record_key"],
            self.expected["source_record_key"],
        )
        self.assertNotIn("row_number", self.source.value)

    def test_p22_06_proposal_identity_digest_recomputes(self) -> None:
        self.assertEqual(
            issue22_fixture_digest(
                issue22_import_proposal_identity_payload(
                    self.original_batch.value,
                    self.source.value,
                    self.proposal.value,
                )
            ),
            self.proposal.value["proposal_identity_digest"],
        )

    def test_p22_06_proposal_references_only_event_time_and_summary(self) -> None:
        bindings = self.proposal.value["field_bindings"]
        self.assertEqual(
            {
                binding["source_field_key"]
                for binding in bindings
            },
            {"event_time", "summary"},
        )
        self.assertEqual(
            {
                binding["target_path"]
                for binding in bindings
            },
            {"/occurrence/started_at", "/summary"},
        )
        for binding in bindings:
            self.assertEqual(
                binding["value_source"],
                "source_value",
            )
            self.assertNotIn(
                "transformed_candidate",
                binding,
            )

    def test_p22_06_source_resolved_assertion_is_not_mapped_to_judgment(self) -> None:
        source_values = {
            field["field_key"]: field["value"]
            for field in self.source.value["source_fields"]
        }
        self.assertEqual(
            source_values["source_status"],
            "resolved",
        )
        self.assertNotIn(
            "source_status",
            {
                binding["source_field_key"]
                for binding in self.proposal.value["field_bindings"]
            },
        )
        self.assertTrue(
            {
                "review",
                "classification",
                "hypothesis",
                "determination",
                "outcome",
            }.isdisjoint(self.by_contract)
        )

    def test_p22_06_import_review_is_human_staging_gate(self) -> None:
        self.assertEqual(
            self.review.value["disposition"],
            "accepted",
        )
        self.assertEqual(
            self.review.value["reviewer"]["kind"],
            "local_operator",
        )
        self.assertEqual(
            self.review.value["proposal_ref"][
                "proposal_identity_digest"
            ],
            self.proposal.value["proposal_identity_digest"],
        )
        self.assertEqual(
            self.review.value["field_reviews"],
            [],
        )

    def test_p22_06_event_has_exact_import_provenance(self) -> None:
        self.assertEqual(
            self.event.value["creation_source"],
            self.expected["event_creation_source"],
        )
        self.assertEqual(
            self.event.value["status"],
            "active",
        )

    def test_p22_06_event_domain_time_is_not_import_time(self) -> None:
        domain_time = self.event.value["occurrence"][
            "started_at"
        ]
        self.assertEqual(
            domain_time,
            self.expected["event_occurrence_started_at"],
        )
        self.assertNotEqual(
            domain_time,
            self.original_batch.value[
                "source_snapshot"
            ]["observed_at"],
        )
        self.assertNotEqual(
            domain_time,
            self.review.value["reviewed_at"],
        )
        self.assertNotEqual(
            domain_time,
            self.receipt.value["materialized_at"],
        )

    def test_p22_06_receipt_binds_all_exact_import_identity_digests(self) -> None:
        value = self.receipt.value
        self.assertEqual(
            value["import_batch_ref"]["import_identity_digest"],
            self.original_batch.value["import_identity_digest"],
        )
        self.assertEqual(
            value["source_record_ref"][
                "source_record_identity_digest"
            ],
            self.source.value["source_record_identity_digest"],
        )
        self.assertEqual(
            value["proposal_ref"]["proposal_identity_digest"],
            self.proposal.value["proposal_identity_digest"],
        )
        self.assertEqual(
            value["review_ref"]["review_id"],
            self.review.value["review_id"],
        )
        self.assertEqual(
            value["canonical_results"][0]["target"][
                "work_ref"
            ]["work_id"],
            self.event.value["work_id"],
        )

    def test_p22_06_later_snapshot_has_no_rows_and_does_not_delete_event(self) -> None:
        path = CORPUS_ROOT / self.expected[
            "source_v2_fixture_path"
        ].removeprefix("tests/fixtures/issue_22/")
        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(
            len(rows),
            self.expected["later_snapshot_row_count"],
        )
        self.assertEqual(
            self.event.value["status"],
            self.expected[
                "current_event_status_after_later_snapshot"
            ],
        )

    def test_p22_06_recompute_is_idempotent_for_unchanged_lineage(self) -> None:
        first = issue22_fixture_digest(
            issue22_import_proposal_identity_payload(
                self.original_batch.value,
                self.source.value,
                self.proposal.value,
            )
        )
        second = issue22_fixture_digest(
            issue22_import_proposal_identity_payload(
                self.original_batch.value,
                self.source.value,
                self.proposal.value,
            )
        )
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            self.expected["proposal_identity_digest"],
        )


if __name__ == "__main__":
    unittest.main()
