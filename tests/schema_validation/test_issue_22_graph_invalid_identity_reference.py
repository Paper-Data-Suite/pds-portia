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


CASE_IDS = tuple(f"G22-{number:03d}" for number in range(1, 11))


class Issue22GraphInvalidIdentityReferenceTests(unittest.TestCase):
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

    def test_corpus_registers_first_ten_graph_invalid_cases(self) -> None:
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

    def test_graph_invalid_descriptors_have_required_audit_metadata(
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
                self.assertEqual(
                    scenario["scenario_kind"],
                    "graph_invalid",
                )
                self.assertEqual(
                    scenario["expected_graph_result"],
                    "invalid",
                )
                self.assertTrue(required <= set(scenario))
                self.assertIn(
                    scenario["primary_finding_id"],
                    scenario["expected_finding_ids"],
                )
                self.assertEqual(
                    expected["primary_finding_id"],
                    scenario["primary_finding_id"],
                )
                self.assertEqual(
                    expected["expected_finding_ids"],
                    scenario["expected_finding_ids"],
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
                findings = validate_structural_records(
                    path,
                    scenario,
                    catalog=self.catalog,
                    store=self.store,
                )
                self.assertEqual(findings, ())

    def test_each_case_fails_for_exact_declared_graph_finding_set(
        self,
    ) -> None:
        for scenario_id, (path, scenario, _, _, _) in (
            self.loaded.items()
        ):
            with self.subTest(scenario_id=scenario_id):
                findings = validate_graph(
                    path,
                    scenario,
                    catalog=self.catalog,
                    store=self.store,
                )
                actual = [finding.code for finding in findings]
                self.assertEqual(
                    actual,
                    sorted(scenario["expected_finding_ids"]),
                )
                self.assertIn(
                    scenario["primary_finding_id"],
                    actual,
                )
                self.assertFalse(
                    any(
                        code.startswith("G22.STRUCTURAL.")
                        for code in actual
                    )
                )

    def test_noncanonical_resolution_contexts_are_test_only(self) -> None:
        for scenario_id in (
            "G22-005",
            "G22-006",
            "G22-007",
            "G22-009",
            "G22-010",
        ):
            _, _, _, contexts, _ = self.loaded[scenario_id]
            semantic_contexts = [
                value
                for kind, value in contexts
                if kind
                in {
                    "synthetic_identity_resolution",
                    "synthetic_reference_resolution",
                }
            ]
            with self.subTest(scenario_id=scenario_id):
                self.assertEqual(len(semantic_contexts), 1)
                context = semantic_contexts[0]
                self.assertIs(
                    context["not_runtime_contract"],
                    True,
                )
                self.assertEqual(
                    context["fixture_version"],
                    "1",
                )
                self.assertTrue(
                    context["fixture_contract"].startswith(
                        "pds-portia.synthetic-"
                    )
                )

    def test_g22_001_same_id_exists_only_in_other_work(self) -> None:
        _, _, records, _, _ = self.loaded["G22-001"]
        role = next(
            record
            for record in records
            if record.contract == "event_participant_role"
        )
        account = next(
            record
            for record in records
            if record.contract == "account"
        )
        basis_id = role.value["basis"][0]["record_ref"]["record_id"]
        self.assertEqual(
            basis_id,
            account.value["account_id"],
        )
        self.assertNotEqual(
            role.value["work_id"],
            account.value["work_id"],
        )

    def test_g22_002_reference_names_wrong_owning_class(self) -> None:
        _, _, records, _, _ = self.loaded["G22-002"]
        review = next(
            record for record in records if record.contract == "review"
        )
        evidence = review.value["evidence_considered"][0][
            "work_record_ref"
        ]
        self.assertNotEqual(
            review.value["class_id"],
            evidence["work_ref"]["class_id"],
        )
        referenced = next(
            record
            for record in records
            if record.contract == "account"
        )
        self.assertEqual(
            evidence["record_ref"]["record_id"],
            referenced.value["account_id"],
        )

    def test_g22_003_only_canonical_path_is_wrong(self) -> None:
        _, _, records, _, _ = self.loaded["G22-003"]
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.contract, "event")
        self.assertNotIn(
            record.value["work_id"],
            record.descriptor["canonical_path"],
        )

    def test_g22_004_version_token_is_supported_but_not_exact(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-004"]
        participant = next(
            record
            for record in records
            if record.contract == "event_participant"
        )
        observation = next(
            record
            for record in records
            if record.contract == "observation"
        )
        requested = observation.value["target"]["record_ref"][
            "contract_version"
        ]
        self.assertEqual(requested, "2")
        self.assertEqual(participant.version, "3")
        self.assertNotEqual(requested, participant.version)

    def test_g22_005_local_student_id_does_not_cross_class_merge(
        self,
    ) -> None:
        _, _, _, contexts, _ = self.loaded["G22-005"]
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_identity_resolution"
        )
        subjects = resolution["subjects"]
        self.assertEqual(
            len({item["student_id"] for item in subjects}),
            1,
        )
        self.assertEqual(
            len({item["class_id"] for item in subjects}),
            2,
        )
        self.assertIs(
            resolution["accepted_explicit_link"],
            False,
        )

    def test_g22_006_display_name_does_not_merge_identity(self) -> None:
        _, _, _, contexts, _ = self.loaded["G22-006"]
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_identity_resolution"
        )
        subjects = resolution["subjects"]
        self.assertEqual(
            len({item["display_name"] for item in subjects}),
            1,
        )
        self.assertEqual(
            len(
                {
                    (item["class_id"], item["student_id"])
                    for item in subjects
                }
            ),
            2,
        )

    def test_g22_007_actor_cannot_replace_roster_identity(self) -> None:
        _, _, records, contexts, _ = self.loaded["G22-007"]
        participant = next(
            record
            for record in records
            if record.contract == "event_participant"
        )
        actor = next(
            record for record in records if record.contract == "actor"
        )
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_identity_resolution"
        )
        self.assertEqual(
            participant.value["subject"]["kind"],
            "actor",
        )
        self.assertEqual(
            participant.value["subject"]["actor_ref"]["actor_id"],
            actor.value["actor_id"],
        )
        self.assertIs(
            resolution["accepted_explicit_link"],
            False,
        )

    def test_g22_008_participant_target_is_outside_owner_work(
        self,
    ) -> None:
        _, _, records, _, _ = self.loaded["G22-008"]
        observation = next(
            record
            for record in records
            if record.contract == "observation"
        )
        participant = next(
            record
            for record in records
            if record.contract == "event_participant"
        )
        self.assertEqual(
            observation.value["target"]["record_ref"]["record_id"],
            participant.value["participant_id"],
        )
        self.assertNotEqual(
            observation.value["work_id"],
            participant.value["work_id"],
        )

    def test_g22_009_foreign_ref_is_substituted_by_local_actor(
        self,
    ) -> None:
        _, _, _, contexts, _ = self.loaded["G22-009"]
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_reference_resolution"
        )
        self.assertEqual(
            resolution["requested"]["authority"],
            "core",
        )
        self.assertEqual(
            resolution["resolved"]["authority"],
            "portia",
        )
        self.assertEqual(
            resolution["resolution_mode"],
            "substitute_local",
        )

    def test_g22_010_historical_ref_is_silently_followed(
        self,
    ) -> None:
        _, _, records, contexts, _ = self.loaded["G22-010"]
        resolution = next(
            value
            for kind, value in contexts
            if kind == "synthetic_reference_resolution"
        )
        original = next(
            record
            for record in records
            if record.logical_identity.endswith(
                "rel_g22_history_original"
            )
        )
        corrected = next(
            record
            for record in records
            if record.logical_identity.endswith(
                "rel_g22_history_corrected"
            )
        )
        self.assertEqual(original.value["status"], "superseded")
        self.assertEqual(corrected.value["status"], "active")
        self.assertEqual(
            resolution["requested"]["record_id"],
            original.value["relationship_id"],
        )
        self.assertEqual(
            resolution["resolved"]["record_id"],
            corrected.value["relationship_id"],
        )
        self.assertNotEqual(
            resolution["requested"],
            resolution["resolved"],
        )


if __name__ == "__main__":
    unittest.main()
