from __future__ import annotations

import hashlib
import json
import unittest

try:
    from .issue_22_graph_validation import (
        _canonical_path_for_record,
        load_json_object,
        load_scenario_records,
        replacement_frontier,
        validate_graph,
    )
    from .schema_support import (
        REPO_ROOT,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from issue_22_graph_validation import (
        _canonical_path_for_record,
        load_json_object,
        load_scenario_records,
        replacement_frontier,
        validate_graph,
    )
    from schema_support import (
        REPO_ROOT,
        load_validated_catalog_and_store,
        validator_for,
    )


ROOT = REPO_ROOT / "tests" / "fixtures" / "issue_22"
SCENARIO_ROOT = ROOT / "positive" / "p22_14_coordinated_operation_recovery"
SCENARIO_PATH = SCENARIO_ROOT / "scenario.json"
OPERATION_ID = "op_p22_recovery_relationship"
OLD_RELATIONSHIP_ID = "rel_p22_recovery_original"
NEW_RELATIONSHIP_ID = "rel_p22_recovery_corrected"


def canonical_json_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_fingerprint(path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "algorithm": "sha256",
        "digest": hashlib.sha256(data).hexdigest(),
        "byte_length": len(data),
    }


def expected_lock_id(lock: dict[str, object]) -> str:
    payload = {
        "lock_scope": lock["lock_scope"],
        "protected_target": lock["protected_target"],
    }
    return "lock_" + canonical_json_digest(payload)


def lock_application_errors(lock: dict[str, object]) -> list[str]:
    errors: list[str] = []
    if lock["lock_id"] != expected_lock_id(lock):
        errors.append("lock ID does not match canonical key")
    if lock["lock_scope"] == "operation":
        target_operation = lock["protected_target"]["operation_ref"]["operation_id"]
        owner_operation = lock["owning_operation"]["operation_id"]
        if target_operation != owner_operation:
            errors.append("operation lock target and owner disagree")
    return errors


def journal_application_errors(journal: dict[str, object]) -> list[str]:
    """Mirror the accepted Issue #13 bounded application checks."""
    errors: list[str] = []
    revision = journal["journal_revision"]
    previous = journal["previous_journal_revision"]
    if revision == 1:
        if previous is not None:
            errors.append("revision one has a predecessor")
    elif previous != revision - 1:
        errors.append("journal predecessor is not immediate")

    write_set = journal["write_set"]
    sequences = [step["sequence"] for step in write_set]
    if sequences != list(range(1, len(write_set) + 1)):
        errors.append("write-step sequence is not contiguous")
    step_ids = [step["step_id"] for step in write_set]
    if len(step_ids) != len(set(step_ids)):
        errors.append("write-step identifiers are not unique")

    lock_set = journal["lock_set"]
    lock_sequences = [lock["sequence"] for lock in lock_set]
    if lock_sequences != list(range(1, len(lock_set) + 1)):
        errors.append("lock sequence is not contiguous")
    lock_ids = [lock["lock_id"] for lock in lock_set]
    if len(lock_ids) != len(set(lock_ids)):
        errors.append("lock identifiers are not unique")

    steps_by_id = {step["step_id"]: step for step in write_set}
    for artifact in journal["staged_artifacts"]:
        step = steps_by_id.get(artifact["step_id"])
        if step is None:
            errors.append("staged artifact references an unknown step")
            continue
        if artifact["destination_path"] != step["destination_path"]:
            errors.append("staged artifact destination disagrees with step")

    partial = journal["partial_state"]
    classified_fields = (
        "accepted_steps",
        "verified_steps",
        "durable_unverified_steps",
        "indeterminate_steps",
        "remaining_canonical_steps",
        "remaining_post_commit_steps",
    )
    classifications: dict[str, str] = {}
    for field in classified_fields:
        for step_id in partial[field]:
            if step_id not in steps_by_id:
                errors.append(f"{field} references an unknown step")
            prior = classifications.get(step_id)
            if prior is not None:
                errors.append(f"step appears in both {prior} and {field}")
            classifications[step_id] = field

    for step_id in partial["accepted_steps"]:
        step = steps_by_id.get(step_id)
        if step is not None and step["disposition"] != "accepted":
            errors.append("accepted_steps contains a nonaccepted step")

    acquired_lock_ids = {
        lock["lock_id"]
        for lock in lock_set
        if lock["disposition"] == "acquired"
    }
    held_lock_ids = set(partial["held_or_possible_locks"])
    if not held_lock_ids <= set(lock_ids):
        errors.append("partial state references an unknown lock")
    if journal["state"] == "completed":
        if acquired_lock_ids:
            errors.append("completed operation retains acquired locks")
        if held_lock_ids:
            errors.append("completed operation reports held locks")
    return errors


def intent_digest(journal: dict[str, object]) -> str:
    payload = {
        "operation_kind": journal["operation_kind"],
        "scope": journal["scope"],
        "primary_target": journal["primary_target"],
        "affected_targets": journal["affected_targets"],
        "intent_facts": journal["intent_facts"],
    }
    return canonical_json_digest(payload)


class Issue22CoordinatedOperationRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.scenario = load_json_object(SCENARIO_PATH)
        cls.records = load_scenario_records(SCENARIO_PATH, cls.scenario)
        cls.by_contract = {record.contract: [] for record in cls.records}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record.value)
        cls.journals = [
            load_json_object(SCENARIO_ROOT / f"operation-journal-r{revision}.json")
            for revision in range(1, 7)
        ]
        cls.pointer = load_json_object(SCENARIO_ROOT / "operation-current.json")
        cls.operation_lock = load_json_object(SCENARIO_ROOT / "operation-lock.json")
        cls.work_lock = load_json_object(SCENARIO_ROOT / "work-lock.json")
        cls.preflight_old = load_json_object(SCENARIO_ROOT / "preflight-old-active.json")
        cls.recovery = load_json_object(SCENARIO_ROOT / "recovery-expectation.json")

    def test_corpus_registers_p22_14_and_positive_plan_is_complete(self) -> None:
        corpus = load_json_object(ROOT / "corpus.json")
        implemented = {entry["scenario_id"] for entry in corpus["scenarios"]}
        self.assertIn("P22-14", implemented)
        self.assertNotIn("P22-14", corpus["planned_positive_scenarios"])
        self.assertEqual(corpus["planned_positive_scenarios"], [])

    def test_p22_14_public_canonical_records_are_structurally_valid(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                validator = validator_for(
                    record.contract,
                    record.version,
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(record.value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_p22_14_combined_canonical_graph_is_valid(self) -> None:
        findings = validate_graph(
            SCENARIO_PATH,
            self.scenario,
            catalog=self.catalog,
            store=self.store,
        )
        self.assertEqual(findings, ())

    def test_p22_14_uses_current_operation_journal_and_lock_versions(self) -> None:
        descriptors = self.scenario["operational_contract_fixtures"]
        journals = [
            item for item in descriptors
            if item["contract"] == "operation_journal"
        ]
        locks = [
            item for item in descriptors
            if item["contract"] == "operation_lock"
        ]
        self.assertEqual(len(journals), 6)
        self.assertEqual(len(locks), 2)
        self.assertTrue(all(item["version"] == "2" for item in journals))
        self.assertTrue(all(item["version"] == "2" for item in locks))
        self.assertTrue(all(journal["schema_version"] == "2" for journal in self.journals))
        self.assertEqual(self.operation_lock["schema_version"], "2")
        self.assertEqual(self.work_lock["schema_version"], "2")

    def test_p22_14_operational_public_contracts_are_structurally_valid(self) -> None:
        for descriptor in self.scenario["operational_contract_fixtures"]:
            with self.subTest(fixture=descriptor["fixture_path"]):
                value = load_json_object(SCENARIO_ROOT / descriptor["fixture_path"])
                validator = validator_for(
                    descriptor["contract"],
                    descriptor["version"],
                    catalog=self.catalog,
                    store=self.store,
                )
                errors = list(validator.iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_p22_14_all_domain_canonical_paths_match_identity(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                self.assertEqual(
                    _canonical_path_for_record(record),
                    record.descriptor["canonical_path"],
                )

    def test_p22_14_operation_paths_are_identity_derived(self) -> None:
        descriptors = self.scenario["operational_contract_fixtures"]
        by_fixture = {item["fixture_path"]: item for item in descriptors}
        for revision in range(1, 7):
            expected = f"portia/operations/{OPERATION_ID}/revisions/{revision}.json"
            self.assertEqual(
                by_fixture[f"operation-journal-r{revision}.json"]["canonical_path"],
                expected,
            )
        self.assertEqual(
            by_fixture["operation-current.json"]["canonical_path"],
            f"portia/operations/{OPERATION_ID}/current.json",
        )
        for fixture in ("operation-lock.json", "work-lock.json"):
            lock = load_json_object(SCENARIO_ROOT / fixture)
            self.assertEqual(
                by_fixture[fixture]["canonical_path"],
                f"portia/locks/{lock['lock_id']}.json",
            )

    def test_p22_14_correction_topology_is_exact_and_append_preserving(self) -> None:
        relationships = self.by_contract["work_relationship"]
        old = next(value for value in relationships if value["relationship_id"] == OLD_RELATIONSHIP_ID)
        new = next(value for value in relationships if value["relationship_id"] == NEW_RELATIONSHIP_ID)
        self.assertEqual(old["status"], "superseded")
        self.assertEqual(new["status"], "active")
        self.assertEqual(new["supersedes"][0]["reason"], "material_detail_corrected")
        predecessor = new["supersedes"][0]["work_record_ref"]
        self.assertEqual(predecessor["record_ref"]["record_id"], OLD_RELATIONSHIP_ID)
        self.assertEqual(predecessor["record_ref"]["contract_version"], "2")
        self.assertEqual(old["source"], new["source"])
        self.assertEqual(old["target"], new["target"])
        self.assertNotEqual(old["detail"], new["detail"])

    def test_p22_14_final_frontier_has_one_active_successor(self) -> None:
        self.assertEqual(
            replacement_frontier(self.records, "work_relationship"),
            (NEW_RELATIONSHIP_ID,),
        )
        active = [
            value["relationship_id"]
            for value in self.by_contract["work_relationship"]
            if value["status"] == "active"
        ]
        self.assertEqual(active, [NEW_RELATIONSHIP_ID])

    def test_p22_14_preflight_fingerprint_is_exact_prior_representation(self) -> None:
        first = self.journals[0]
        entry = next(
            item
            for item in first["preflight_snapshot"]
            if item["target"]["work_record_ref"]["record_ref"]["record_id"]
            == OLD_RELATIONSHIP_ID
        )
        self.assertEqual(
            entry["expected_state"]["fingerprint"],
            file_fingerprint(SCENARIO_ROOT / "preflight-old-active.json"),
        )
        self.assertEqual(self.preflight_old["status"], "active")

    def test_p22_14_preflight_representation_differs_from_final_predecessor(self) -> None:
        before = file_fingerprint(SCENARIO_ROOT / "preflight-old-active.json")
        after = file_fingerprint(SCENARIO_ROOT / "relationship-original.json")
        self.assertNotEqual(before, after)
        final_old = load_json_object(SCENARIO_ROOT / "relationship-original.json")
        self.assertEqual(final_old["status"], "superseded")

    def test_p22_14_intent_digest_is_exact_and_stable(self) -> None:
        digests = {journal["intent_digest"] for journal in self.journals}
        self.assertEqual(len(digests), 1)
        self.assertEqual(self.journals[0]["intent_digest"], intent_digest(self.journals[0]))

    def test_p22_14_preflight_digest_is_exact_and_stable(self) -> None:
        digests = {journal["preflight_snapshot_digest"] for journal in self.journals}
        self.assertEqual(len(digests), 1)
        self.assertEqual(
            self.journals[0]["preflight_snapshot_digest"],
            canonical_json_digest(self.journals[0]["preflight_snapshot"]),
        )

    def test_p22_14_lock_ids_use_accepted_canonical_key_recipe(self) -> None:
        for lock in (self.operation_lock, self.work_lock):
            with self.subTest(lock=lock["lock_id"]):
                self.assertEqual(lock["lock_id"], expected_lock_id(lock))
                self.assertEqual(lock_application_errors(lock), [])

    def test_p22_14_journal_lock_fingerprints_match_lock_records(self) -> None:
        expected = {
            self.operation_lock["lock_id"]: file_fingerprint(SCENARIO_ROOT / "operation-lock.json"),
            self.work_lock["lock_id"]: file_fingerprint(SCENARIO_ROOT / "work-lock.json"),
        }
        for journal in self.journals[1:]:
            for entry in journal["lock_set"]:
                self.assertEqual(entry["fingerprint"], expected[entry["lock_id"]])

    def test_p22_14_all_journals_pass_issue_13_bounded_application_checks(self) -> None:
        for journal in self.journals:
            with self.subTest(revision=journal["journal_revision"]):
                self.assertEqual(journal_application_errors(journal), [])

    def test_p22_14_journal_revision_chain_is_immediate_and_linear(self) -> None:
        self.assertEqual(
            [journal["journal_revision"] for journal in self.journals],
            [1, 2, 3, 4, 5, 6],
        )
        self.assertEqual(
            [journal["previous_journal_revision"] for journal in self.journals],
            [None, 1, 2, 3, 4, 5],
        )

    def test_p22_14_operation_state_progression_contains_recovery_boundary(self) -> None:
        self.assertEqual(
            [journal["state"] for journal in self.journals],
            ["prepared", "staged", "committing", "recovering", "committed", "completed"],
        )

    def test_p22_14_preflight_occurs_before_any_mutation(self) -> None:
        prepared = self.journals[0]
        self.assertEqual(prepared["state"], "prepared")
        self.assertEqual(prepared["partial_state"]["durability_assessment"], "none")
        self.assertEqual(prepared["partial_state"]["accepted_steps"], [])
        self.assertFalse(prepared["commit_point"]["reached"])
        self.assertTrue(all(step["disposition"] == "pending" for step in prepared["write_set"]))
        self.assertTrue(all(lock["disposition"] == "planned" for lock in prepared["lock_set"]))

    def test_p22_14_staging_precedes_canonical_acceptance(self) -> None:
        staged = self.journals[1]
        self.assertEqual(staged["state"], "staged")
        self.assertEqual(len(staged["staged_artifacts"]), 2)
        self.assertEqual(staged["partial_state"]["accepted_steps"], [])
        self.assertTrue(all(step["disposition"] == "staged" for step in staged["write_set"]))

    def test_p22_14_interruption_records_explicit_partial_success(self) -> None:
        interrupted = self.journals[2]
        self.assertEqual(interrupted["state"], "committing")
        self.assertEqual(interrupted["partial_state"]["durability_assessment"], "confirmed")
        self.assertEqual(interrupted["partial_state"]["accepted_steps"], ["step_create_successor"])
        self.assertEqual(
            interrupted["partial_state"]["remaining_canonical_steps"],
            ["step_supersede_original"],
        )
        self.assertEqual(
            interrupted["partial_state"]["recommended_disposition"],
            "complete_remaining_steps",
        )
        self.assertFalse(interrupted["commit_point"]["reached"])

    def test_p22_14_interruption_accepted_successor_fingerprint_is_truthful(self) -> None:
        interrupted = self.journals[2]
        step = interrupted["write_set"][0]
        expected = file_fingerprint(SCENARIO_ROOT / "relationship-corrected.json")
        self.assertEqual(step["disposition"], "accepted")
        self.assertEqual(step["observed_result"]["fingerprint"], expected)
        self.assertEqual(step["intended_result"]["fingerprint"], expected)

    def test_p22_14_accepted_successor_is_not_deleted_to_simulate_rollback(self) -> None:
        for journal in self.journals[2:]:
            create_step = next(step for step in journal["write_set"] if step["step_id"] == "step_create_successor")
            self.assertEqual(create_step["disposition"], "accepted")
            self.assertNotEqual(create_step["action"], "remove_transient")
        self.assertTrue((SCENARIO_ROOT / "relationship-corrected.json").is_file())

    def test_p22_14_restart_reconciles_before_replaying_writes(self) -> None:
        recovering = self.journals[3]
        create_step = recovering["write_set"][0]
        self.assertEqual(recovering["state"], "recovering")
        self.assertEqual(create_step["disposition"], "accepted")
        self.assertEqual(create_step["reason_code"], "reconciled_exact_replay")
        self.assertEqual(
            create_step["observed_result"]["fingerprint"],
            file_fingerprint(SCENARIO_ROOT / "relationship-corrected.json"),
        )
        self.assertEqual(
            recovering["partial_state"]["remaining_canonical_steps"],
            ["step_supersede_original"],
        )

    def test_p22_14_recovery_does_not_add_duplicate_successor_step_or_identity(self) -> None:
        for journal in self.journals:
            create_steps = [step for step in journal["write_set"] if step["action"] == "exclusive_create"]
            self.assertEqual([step["step_id"] for step in create_steps], ["step_create_successor"])
            target_ids = [
                step["target"]["work_record_ref"]["record_ref"]["record_id"]
                for step in create_steps
            ]
            self.assertEqual(target_ids, [NEW_RELATIONSHIP_ID])
        corrected = [
            value
            for value in self.by_contract["work_relationship"]
            if value["relationship_id"] == NEW_RELATIONSHIP_ID
        ]
        self.assertEqual(len(corrected), 1)

    def test_p22_14_recovery_completes_only_remaining_predecessor_write(self) -> None:
        recovering = self.journals[3]
        committed = self.journals[4]
        before = {step["step_id"]: step["disposition"] for step in recovering["write_set"]}
        after = {step["step_id"]: step["disposition"] for step in committed["write_set"]}
        self.assertEqual(before["step_create_successor"], "accepted")
        self.assertEqual(after["step_create_successor"], "accepted")
        self.assertEqual(before["step_supersede_original"], "staged")
        self.assertEqual(after["step_supersede_original"], "accepted")

    def test_p22_14_commit_point_requires_both_canonical_gates(self) -> None:
        for journal in self.journals[:4]:
            self.assertFalse(journal["commit_point"]["reached"])
        committed = self.journals[4]
        self.assertTrue(committed["commit_point"]["reached"])
        self.assertTrue(all(step["disposition"] == "accepted" for step in committed["write_set"]))
        self.assertEqual(committed["partial_state"]["remaining_canonical_steps"], [])

    def test_p22_14_completed_revision_releases_all_locks(self) -> None:
        completed = self.journals[5]
        self.assertEqual(completed["state"], "completed")
        self.assertTrue(all(lock["disposition"] == "released" for lock in completed["lock_set"]))
        self.assertEqual(completed["partial_state"]["held_or_possible_locks"], [])
        self.assertEqual(completed["partial_state"]["remaining_canonical_steps"], [])
        self.assertEqual(completed["partial_state"]["remaining_post_commit_steps"], [])

    def test_p22_14_operation_current_pointer_selects_terminal_revision_explicitly(self) -> None:
        self.assertEqual(self.pointer["operation_id"], OPERATION_ID)
        self.assertEqual(self.pointer["journal_revision"], 6)
        self.assertEqual(self.journals[self.pointer["journal_revision"] - 1]["state"], "completed")
        for forbidden in ("state", "updated_at", "intent_digest", "operation_kind"):
            self.assertNotIn(forbidden, self.pointer)

    def test_p22_14_journal_is_operational_evidence_not_domain_truth(self) -> None:
        relationships = self.by_contract["work_relationship"]
        narrative = "\n".join(value["detail"] for value in relationships)
        journal_text = "\n".join(
            json.dumps(journal, ensure_ascii=False, sort_keys=True)
            for journal in self.journals
        )
        for detail in (value["detail"] for value in relationships):
            self.assertNotIn(detail, journal_text)
        self.assertIn("bounded", narrative.lower())
        self.assertTrue(all(journal["record_type"] == "operation_journal" for journal in self.journals))
        self.assertTrue(all("relationship_type" not in journal for journal in self.journals))

    def test_p22_14_journal_intent_and_preflight_remain_identical_across_revisions(self) -> None:
        first = self.journals[0]
        for journal in self.journals[1:]:
            self.assertEqual(journal["operation_kind"], first["operation_kind"])
            self.assertEqual(journal["scope"], first["scope"])
            self.assertEqual(journal["primary_target"], first["primary_target"])
            self.assertEqual(journal["affected_targets"], first["affected_targets"])
            self.assertEqual(journal["intent_facts"], first["intent_facts"])
            self.assertEqual(journal["intent_digest"], first["intent_digest"])
            self.assertEqual(journal["preflight_snapshot"], first["preflight_snapshot"])
            self.assertEqual(journal["preflight_snapshot_digest"], first["preflight_snapshot_digest"])

    def test_p22_14_recovery_expectation_matches_terminal_canonical_state(self) -> None:
        final = self.recovery["final_safe_state"]
        self.assertEqual(final["selected_journal_revision"], self.pointer["journal_revision"])
        self.assertEqual(final["active_relationship_ids"], [NEW_RELATIONSHIP_ID])
        self.assertEqual(final["superseded_relationship_ids"], [OLD_RELATIONSHIP_ID])
        self.assertFalse(final["duplicate_semantic_records"])
        self.assertTrue(final["locks_released"])

    def test_p22_14_scenario_preserves_required_ticket_distinctions(self) -> None:
        text = "\n".join(self.scenario["required_distinctions"]).lower()
        for phrase in (
            "preflight",
            "do not replace canonical work relationship domain records",
            "never deleted merely to simulate rollback",
            "reconciles the exact already-accepted successor",
            "partial success",
            "does not create a second successor",
        ):
            self.assertIn(phrase, text)
        self.assertEqual(
            self.recovery["assertions"],
            [
                "preflight_occurs_before_mutation",
                "operation_journal_is_operational_not_domain_truth",
                "accepted_canonical_record_is_not_deleted_as_rollback",
                "restart_reconciles_observed_state_before_replay",
                "partial_success_is_explicit",
                "recovery_does_not_duplicate_committed_semantic_record",
            ],
        )


if __name__ == "__main__":
    unittest.main()
