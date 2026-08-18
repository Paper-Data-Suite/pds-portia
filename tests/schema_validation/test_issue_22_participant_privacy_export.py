from __future__ import annotations

import hashlib
import json
import unittest

try:
    from .issue_22_graph_validation import (
        _canonical_path_for_record,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from .schema_support import load_validated_catalog_and_store
    from .test_issue_21_deliberate_export_contracts import (
        export_application_errors,
        inventory_application_errors,
    )
except ImportError:
    from issue_22_graph_validation import (
        _canonical_path_for_record,
        load_contexts,
        load_corpus,
        load_scenario_records,
        scenario_by_id,
        validate_graph,
        validate_structural_records,
    )
    from schema_support import load_validated_catalog_and_store
    from test_issue_21_deliberate_export_contracts import (
        export_application_errors,
        inventory_application_errors,
    )


class Issue22ParticipantPrivacyExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.corpus = load_corpus()
        cls.scenario_path, cls.scenario = scenario_by_id(cls.corpus, "P22-12")
        cls.records = load_scenario_records(cls.scenario_path, cls.scenario)
        cls.contexts = load_contexts(cls.scenario_path, cls.scenario)
        cls.by_contract: dict[str, list] = {}
        for record in cls.records:
            cls.by_contract.setdefault(record.contract, []).append(record)
        cls.export_record = cls.by_contract["deliberate_export"][0]
        cls.export = cls.export_record.value
        cls.projection_path = cls.scenario_path.parent / cls.scenario["projection_expectation"]["fixture_path"]
        cls.projection = json.loads(cls.projection_path.read_text(encoding="utf-8"))
        cls.expected = json.loads((cls.scenario_path.parent / "expected.json").read_text(encoding="utf-8"))
        cls.artifact_path = cls.scenario_path.parent / "artifact.csv"
        cls.artifact_bytes = cls.artifact_path.read_bytes()

    def test_corpus_registers_p22_12_as_implemented(self) -> None:
        self.assertIn("P22-12", {item["scenario_id"] for item in self.corpus["scenarios"]})
        self.assertNotIn("P22-12", self.corpus["planned_positive_scenarios"])

    def test_p22_12_public_records_are_structurally_valid(self) -> None:
        self.assertEqual(validate_structural_records(self.scenario_path, self.scenario, catalog=self.catalog, store=self.store), ())

    def test_p22_12_combined_graph_is_valid(self) -> None:
        self.assertEqual(validate_graph(self.scenario_path, self.scenario, catalog=self.catalog, store=self.store), ())

    def test_p22_12_source_graph_is_one_event_with_two_exact_participants(self) -> None:
        self.assertEqual(len(self.by_contract["event"]), 1)
        self.assertEqual(len(self.by_contract["event_participant"]), 2)
        self.assertEqual({r.value["participant_id"] for r in self.by_contract["event_participant"]}, {"ep_p22_privacy_a", "ep_p22_privacy_b"})

    def test_p22_12_focal_subject_is_exact_participant_b(self) -> None:
        self.assertEqual(self.export["focal_subject_ref"]["record_ref"], {"record_kind":"event_participant","record_id":"ep_p22_privacy_b","contract_version":"3"})
        self.assertEqual(self.projection["focal_subject_ref"], self.export["focal_subject_ref"])

    def test_p22_12_student_facing_purpose_is_not_authorization(self) -> None:
        contexts = {kind:value for kind,value in self.contexts}
        auth = contexts["synthetic_authorization_context"]
        self.assertEqual(self.export["projection_purpose"], "student_facing")
        self.assertTrue(auth["export_authorized"])
        self.assertFalse(auth["source_artifact_authorized"])
        self.assertEqual(self.export["authorization"]["authorization_scope_id"], auth["authorization_scope_id"])
        self.assertEqual(self.export["authorization"]["policy_rule_id"], auth["policy_rule_id"])

    def test_p22_12_projection_policy_digest_is_exact(self) -> None:
        policy_path = self.scenario_path.parent / "projection-policy.json"
        digest = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        self.assertEqual(self.export["projection_policy"]["policy_digest"], digest)
        self.assertEqual(self.projection["policy"]["policy_digest"], digest)

    def test_p22_12_authorization_rule_digest_is_exact(self) -> None:
        rule_path = self.scenario_path.parent / "authorization-rule.txt"
        digest = hashlib.sha256(rule_path.read_bytes()).hexdigest()
        self.assertEqual(self.export["authorization"]["policy_rule_digest"], digest)

    def test_p22_12_projection_decision_digest_is_exact(self) -> None:
        digest = hashlib.sha256(self.projection_path.read_bytes()).hexdigest()
        self.assertEqual(self.export["projection_decision_digest"], digest)
        self.assertEqual(self.export["manual_review"]["reviewed_projection_digest"], digest)

    def test_p22_12_all_five_projection_dispositions_are_distinct(self) -> None:
        items = self.projection["items"]
        dispositions = {item["disposition"] for item in items}
        self.assertEqual(dispositions, {"included","withheld","absent","unavailable","requires_manual_review"})
        self.assertEqual(self.export["disposition_summary"], self.expected["disposition_summary"])

    def test_p22_12_third_party_free_text_requires_review_not_paraphrase(self) -> None:
        item = next(item for item in self.projection["items"] if item["projection_key"] == "third_party_account_text")
        self.assertEqual(item["disposition"], "requires_manual_review")
        self.assertEqual(item["manual_review_resolution"], "withheld")
        self.assertIs(item["paraphrased"], False)
        self.assertEqual(self.projection["manual_review"]["resolution"], "withhold_without_paraphrase")

    def test_p22_12_stable_ids_are_not_safe_pseudonyms(self) -> None:
        text = self.artifact_bytes.decode("utf-8")
        for token in ("ep_p22_privacy_b", "stu_p22_002", "acct_p22_privacy_b", "obs_p22_privacy_001"):
            self.assertNotIn(token, text)
        item = next(item for item in self.projection["items"] if item["projection_key"] == "focal_native_ids")
        self.assertEqual(item["disposition"], "withheld")

    def test_p22_12_third_party_identity_and_content_do_not_leak(self) -> None:
        text = self.artifact_bytes.decode("utf-8")
        third = self.by_contract["account"][0].value if self.by_contract["account"][0].value["account_id"] == "acct_p22_privacy_a" else self.by_contract["account"][1].value
        self.assertNotIn("Synthetic Student A", text)
        self.assertNotIn("stu_p22_001", text)
        self.assertNotIn("Student A stated", text)
        self.assertNotIn(third["content"][0]["text"], text)

    def test_p22_12_source_artifact_authorization_is_independent(self) -> None:
        contexts = {kind:value for kind,value in self.contexts}
        self.assertFalse(contexts["synthetic_authorization_context"]["source_artifact_authorized"])
        inventory = json.dumps(self.export["source_inventory"], sort_keys=True)
        self.assertNotIn("focal-source-note", inventory)
        self.assertNotIn(self.expected["source_artifact"]["sha256_digest"], inventory)
        self.assertNotIn((self.scenario_path.parent / "focal-source-note.txt").read_text(encoding="utf-8").strip(), self.artifact_bytes.decode("utf-8"))

    def test_p22_12_source_artifact_fingerprint_is_truthful(self) -> None:
        focal_account = next(r.value for r in self.by_contract["account"] if r.value["account_id"] == "acct_p22_privacy_b")
        fp = focal_account["source_artifacts"][0]["fingerprint"]
        payload = (self.scenario_path.parent / "focal-source-note.txt").read_bytes()
        self.assertEqual(fp["digest"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(fp["byte_length"], len(payload))

    def test_p22_12_inventory_contains_only_contributing_exact_sources(self) -> None:
        inventory = self.export["source_inventory"]
        self.assertEqual(len(inventory["entries"]), 4)
        serialized = json.dumps(inventory, sort_keys=True)
        self.assertIn("acct_p22_privacy_b", serialized)
        self.assertIn("ep_p22_privacy_b", serialized)
        self.assertIn("obs_p22_privacy_001", serialized)
        self.assertNotIn("acct_p22_privacy_a", serialized)
        self.assertNotIn("ep_p22_privacy_a", serialized)
        self.assertEqual(inventory_application_errors(inventory), [])

    def test_p22_12_inventory_representation_fingerprints_are_truthful(self) -> None:
        files = {
            "acct_p22_privacy_b": "account-b.json",
            "ep_p22_privacy_b": "participant-b.json",
            "obs_p22_privacy_001": "observation.json",
            "evt_p22_privacy_001": "event.json",
        }
        for entry in self.export["source_inventory"]["entries"]:
            ref = entry.get("work_record_ref", entry.get("work_ref"))
            rid = ref.get("record_ref", {}).get("record_id") if "record_ref" in ref else ref["work_id"]
            payload = (self.scenario_path.parent / files[rid]).read_bytes()
            self.assertEqual(entry["representation_digest"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(entry["byte_length"], len(payload))

    def test_p22_12_deliberate_export_passes_issue_21_application_checks(self) -> None:
        self.assertEqual(export_application_errors(self.export), [])
        self.assertEqual(self.export["projection_decision_algorithm"], "portia_projection_decision_v1")

    def test_p22_12_output_digest_length_and_path_are_truthful(self) -> None:
        output = self.export["output"]
        self.assertEqual(output["workspace_relative_path"], self.expected["output"]["workspace_relative_path"])
        self.assertEqual(output["sha256_digest"], hashlib.sha256(self.artifact_bytes).hexdigest())
        self.assertEqual(output["byte_length"], len(self.artifact_bytes))

    def test_p22_12_export_generation_does_not_claim_disclosure(self) -> None:
        for forbidden in ("recipient","delivered_at","received_at","read_at","consent","disclosure"):
            self.assertNotIn(forbidden, self.export)
        assertions = " ".join(self.projection["assertions"]).lower()
        self.assertIn("does not establish disclosure", assertions)

    def test_p22_12_unavailable_is_not_absent_or_false(self) -> None:
        contexts = {kind:value for kind,value in self.contexts}
        availability = contexts["synthetic_projection_source_availability"]
        self.assertEqual(availability["availability"], "unavailable")
        self.assertIn("not false/no", availability["semantic_assertion"])
        dispositions = {item["projection_key"]:item["disposition"] for item in self.projection["items"]}
        self.assertEqual(dispositions["external_context"], "unavailable")
        self.assertEqual(dispositions["participant_role"], "absent")

    def test_p22_12_all_canonical_paths_match_persisted_identity(self) -> None:
        for record in self.records:
            with self.subTest(record=record.logical_identity):
                self.assertEqual(record.descriptor["canonical_path"], _canonical_path_for_record(record))

    def test_p22_12_scenario_preserves_required_ticket_distinctions(self) -> None:
        text = " ".join(self.scenario["required_distinctions"]).lower()
        for phrase in (
            "noncanonical", "does not itself authorize", "withheld is not absent",
            "unavailable is not false/no", "not emitted as safe pseudonyms",
            "withheld without paraphrase", "does not authorize its raw source-artifact bytes",
            "only exact representations that materially contributed",
            "exact policy, authorization, decision, source-inventory, and output digest/length",
            "export generation is not disclosure",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
