from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for


ISSUE15_SHARED = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "shared-lifecycle-correction-dependency"
ISSUE15_MIGRATION = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "migration-removal-compatibility"
ISSUE15_OPS = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "operational-derived-privacy"
CROSS_ROOT = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-17" / "cross-record"

FAMILY_FIXTURES = {
    "response": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-17" / "response" / "valid" / "event-classroom-management.json",
    "communication": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-17" / "communication" / "valid" / "completed-family-phone.json",
}
ID_FIELDS = {"response": "response_id", "communication": "communication_id"}
ACTIVATION_REASONS = {"response": "action_recorded", "communication": "communication_recorded"}
LIFECYCLE_MATRIX = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}
LIFECYCLE_REASONS = {
    "response": {
        "action_recorded", "recording_error", "wrong_provider", "wrong_target",
        "wrong_event", "wrong_action", "wrong_timing", "wrong_decision_context",
        "invalid_provenance", "duplicate_consolidated", "work_root_corrected",
        "contract_migrated", "other",
    },
    "communication": {
        "communication_recorded", "recording_error", "wrong_sender", "wrong_recipient",
        "wrong_method", "wrong_purpose", "wrong_timing", "wrong_content_summary",
        "wrong_attachment", "communication_did_not_occur", "invalid_provenance",
        "duplicate_consolidated", "work_root_corrected", "contract_migrated", "other",
    },
}
EXPECTED_SHARED = {
    "lifecycle_transition": ("1", "schemas/v1/lifecycle/lifecycle-transition.schema.json"),
    "lifecycle_history_correction": ("1", "schemas/v1/lifecycle/lifecycle-history-correction.schema.json"),
    "amendment": ("1", "schemas/v1/corrections/amendment.schema.json"),
    "statement_of_disagreement": ("1", "schemas/v1/corrections/statement-of-disagreement.schema.json"),
    "dependency": ("1", "schemas/v1/dependencies/dependency.schema.json"),
    "record_migration": ("1", "schemas/v1/migrations/record-migration.schema.json"),
    "exceptional_removal": ("1", "schemas/v1/removals/exceptional-removal.schema.json"),
    "operation_journal": ("2", "schemas/v2/operations/operation-journal.schema.json"),
    "operation_lock": ("2", "schemas/v2/operations/operation-lock.schema.json"),
    "quarantine_record": ("2", "schemas/v2/operations/quarantine-record.schema.json"),
    "integrity_finding": ("2", "schemas/v2/projections/integrity-finding.schema.json"),
    "source_snapshot": ("1", "schemas/v1/projections/source-snapshot.schema.json"),
    "derived_index_metadata": ("1", "schemas/v1/projections/derived-index-metadata.schema.json"),
    "derived_current_pointer": ("1", "schemas/v1/projections/derived-current-pointer.schema.json"),
}


def _rid(record: dict[str, Any]) -> str:
    return record[ID_FIELDS[record["record_type"]]]


def _work_kind(record: dict[str, Any]) -> str:
    return record.get("work_kind", "event")


def _work_ref(record: dict[str, Any], record_version: str = "1") -> dict[str, Any]:
    kind = _work_kind(record)
    return {
        "work_ref": {
            "module_id": "portia",
            "class_id": record["class_id"],
            "work_id": record["work_id"],
            "work_kind": kind,
            "contract_version": "2" if kind == "event" else "1",
        },
        "record_ref": {
            "record_kind": record["record_type"],
            "record_id": _rid(record),
            "contract_version": record_version,
        },
    }


def _local_target(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": record["record_type"],
            "record_id": _rid(record),
            "contract_version": "1",
        },
    }


def _retarget(value: Any, record: dict[str, Any]) -> Any:
    replacements = (
        ("eng10_p2_2026", record["class_id"]),
        ("evt_issue15_ops", record["work_id"]),
        ("evt_alpha", record["work_id"]),
        ("acct_student_report_1", _rid(record)),
        ("acct_dependency_target", _rid(record)),
        ("acct_amendment_forbidden", _rid(record)),
        ("acct_disputed", _rid(record)),
        ("acct_history", _rid(record)),
        ("acct_lifecycle_active", _rid(record)),
        ("acct_ops_1", _rid(record)),
        ("account", record["record_type"]),
    )
    if isinstance(value, str):
        for old, new in replacements:
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_retarget(item, record) for item in value]
    if isinstance(value, dict):
        return {key: _retarget(item, record) for key, item in value.items()}
    return value


def _substantive(record: dict[str, Any]) -> set[str]:
    if record["record_type"] == "response":
        return {record["action"]["description"]}
    summary = record.get("summary")
    return {summary} if summary else set()


def _snapshot_digest(snapshot: dict[str, Any]) -> str:
    payload = {
        key: snapshot[key]
        for key in (
            "snapshot_algorithm", "projection_kind", "projection_scope",
            "authorization_scope", "discovery_roots", "source_contracts", "entries",
        )
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _relation(communication: dict[str, Any], name: str) -> dict[str, Any]:
    for item in communication.get("relations", []):
        if item["relation"] == name:
            return item["record_ref"]
    raise AssertionError(f"missing relation {name}")


class Issue17SharedInfrastructureCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.records = {name: load_json(path) for name, path in FAMILY_FIXTURES.items()}
        cls.validators = {
            name: validator_for(name, "1", catalog=cls.catalog, store=cls.store)
            for name in FAMILY_FIXTURES
        }
        for name, (version, _path) in EXPECTED_SHARED.items():
            cls.validators[name] = validator_for(name, version, catalog=cls.catalog, store=cls.store)
        cls.manifest = load_json(CROSS_ROOT / "manifest.json")

    def _valid(self, contract: str, value: dict[str, Any]) -> None:
        errors = list(self.validators[contract].iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_roots_are_valid(self) -> None:
        for family, record in self.records.items():
            with self.subTest(family=family):
                self._valid(family, record)
                self.assertEqual(record["status"], "active")

    def test_shared_versions_are_reused_without_forks(self) -> None:
        contracts = self.catalog["contracts"]
        for name, (version, path) in EXPECTED_SHARED.items():
            self.assertEqual(contracts[name][version]["path"], path)
        forbidden = {
            f"{family}_{suffix}"
            for family in FAMILY_FIXTURES
            for suffix in (
                "lifecycle_transition", "lifecycle_history_correction", "amendment",
                "statement_of_disagreement", "dependency", "record_migration",
                "exceptional_removal", "operation_journal", "operation_lock",
                "quarantine_record", "integrity_finding", "source_snapshot",
                "derived_index_metadata", "derived_current_pointer",
            )
        }
        self.assertTrue(forbidden.isdisjoint(contracts))

    def test_lifecycle_transition_reuses_common_matrix(self) -> None:
        for family, record in self.records.items():
            transition = {
                "schema_version": "1", "record_type": "lifecycle_transition",
                "module_id": "portia", "class_id": record["class_id"], "work_id": record["work_id"],
                "transition_id": f"lct_issue17_{family}_activate",
                "target": _local_target(record), "previous_transition": None,
                "from_status": "proposed", "to_status": "active",
                "reason": {"category": "workflow", "code": ACTIVATION_REASONS[family]},
                "effective_at": record["created_at"], "creation_source": {"type": "digital_entry"},
                "created_at": record["updated_at"],
                "created_by": {"type": "local_operator", "display_label": "Synthetic Teacher"},
            }
            self._valid("lifecycle_transition", transition)
            self.assertIn(transition["to_status"], LIFECYCLE_MATRIX[transition["from_status"]])
            self.assertIn(transition["reason"]["code"], LIFECYCLE_REASONS[family])

    def test_lifecycle_history_correction_targets_exactly(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "history-account-select-replacement.json")
        for family, record in self.records.items():
            scenario = _retarget(deepcopy(template), record)
            scenario["replacement_transition"]["reason"] = {"category": "workflow", "code": ACTIVATION_REASONS[family]}
            self._valid("lifecycle_transition", scenario["replaced_transition"])
            self._valid("lifecycle_transition", scenario["replacement_transition"])
            self._valid("lifecycle_history_correction", scenario["correction"])
            target = scenario["correction"]["target"]["record_ref"]
            self.assertEqual((target["record_kind"], target["record_id"], target["contract_version"]), (family, _rid(record), "1"))

    def test_disagreement_targets_both_families(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "disagreement-targets-account.json")
        for family, record in self.records.items():
            scenario = _retarget(deepcopy(template), record)
            self._valid("statement_of_disagreement", scenario["disagreement"])
            target = scenario["disagreement"]["target"]["record_ref"]
            self.assertEqual((target["record_kind"], target["record_id"]), (family, _rid(record)))
            self.assertEqual(record["status"], "active")

    def test_amendment_is_structural_but_application_prohibited(self) -> None:
        template = load_json(ISSUE15_SHARED / "application-invalid" / "amendment-account-prohibited.json")
        paths = {"response": "/action", "communication": "/summary"}
        schema_paths = {
            "response": "schemas/v1/responses/response.schema.json",
            "communication": "schemas/v1/communications/communication.schema.json",
        }
        for family, record in self.records.items():
            scenario = _retarget(deepcopy(template), record)
            scenario["amendment"]["changes"][0]["path"] = paths[family]
            self._valid("amendment", scenario["amendment"])
            invariants = load_json(REPO_ROOT / schema_paths[family])["x-portia-application-invariants"]
            self.assertIn(f"portia.{family}.amendment_prohibited_v1", invariants)

    def test_dependency_reuses_exact_refs_and_never_follows_successor(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "dependency-references-account.json")
        for family, record in self.records.items():
            scenario = _retarget(deepcopy(template), record)
            dependency = scenario["dependency"]
            self._valid("dependency", dependency)
            self.assertEqual(dependency["dependency"]["work_record_ref"], _work_ref(record))
        record = self.records["communication"]
        scenario = _retarget(deepcopy(template), record)
        original = deepcopy(scenario["dependency"]["dependency"]["work_record_ref"])
        successor = deepcopy(record)
        successor["communication_id"] = "comm_issue17_infra_successor"
        self.assertEqual(original, scenario["dependency"]["dependency"]["work_record_ref"])
        self.assertNotEqual(original, _work_ref(successor))

    def test_record_migration_reuses_generic_endpoints(self) -> None:
        template = load_json(ISSUE15_MIGRATION / "valid" / "migration-account-v1-v2.json")
        for family, record in self.records.items():
            scenario = _retarget(deepcopy(template), record)
            migration = scenario["migration"]
            migration["source"]["work_record_ref"] = _work_ref(record)
            migration["source"]["observed_updated_at"] = record["updated_at"]
            migration["destination"]["work_record_ref"] = _work_ref(record, "2")
            self._valid("record_migration", migration)
            self.assertEqual(migration["destination"]["work_record_ref"]["record_ref"]["contract_version"], "2")

    def test_removal_operation_and_diagnostics_are_metadata_only(self) -> None:
        removal_t = load_json(ISSUE15_MIGRATION / "valid" / "removal-account-exact.json")
        journal_t = load_json(ISSUE15_OPS / "valid" / "operation-journal-account.json")
        lock_t = load_json(ISSUE15_OPS / "valid" / "operation-lock-account.json")
        quarantine_t = load_json(ISSUE15_OPS / "valid" / "quarantine-account.json")
        integrity_t = load_json(ISSUE15_OPS / "valid" / "integrity-account.json")
        for family, record in self.records.items():
            removal = _retarget(deepcopy(removal_t), record)
            removal["removal"]["target"]["work_record_ref"] = _work_ref(record)
            removal["removal"]["lifecycle_snapshot"]["status"] = record["status"]
            journal = _retarget(deepcopy(journal_t), record)
            lock = _retarget(deepcopy(lock_t), record)
            quarantine = _retarget(deepcopy(quarantine_t), record)
            finding = _retarget(deepcopy(integrity_t), record)
            self._valid("exceptional_removal", removal["removal"])
            self._valid("operation_journal", journal)
            self._valid("operation_lock", lock)
            self._valid("quarantine_record", quarantine)
            self._valid("integrity_finding", finding)
            serialized = json.dumps(
                {"removal": removal, "journal": journal, "lock": lock, "quarantine": quarantine, "finding": finding},
                ensure_ascii=False,
            )
            for text in _substantive(record):
                self.assertNotIn(text, serialized)
            self.assertNotIn(finding["code"], {"response_effective", "family_uncooperative", "student_risk", "legal_notice_satisfied"})

    def test_source_snapshot_and_derived_metadata_are_metadata_only(self) -> None:
        snapshot = load_json(ISSUE15_OPS / "valid" / "source-snapshot.json")
        work_id = "evt_issue17_infra_derived"
        class_id = "eng10_p2_2026"
        snapshot["projection_scope"]["work_ref"]["work_id"] = work_id
        snapshot["discovery_roots"] = [f"classes/{class_id}/modules/portia/work/{work_id}"]
        snapshot["source_contracts"] = [
            {"contract_name": family, "contract_version": "1"}
            for family in sorted(FAMILY_FIXTURES)
        ]
        ids = {"communication": "comm_issue17_derived", "response": "rsp_issue17_derived"}
        snapshot["entries"] = [
            {
                "workspace_relative_path": f"classes/{class_id}/modules/portia/work/{work_id}/records/{family}/{ids[family]}.json",
                "byte_length": 800 + index,
                "sha256_digest": str(index) * 64,
                "source_role": "canonical_domain",
                "contract_or_artifact_kind": family,
            }
            for index, family in enumerate(sorted(FAMILY_FIXTURES), start=1)
        ]
        snapshot["entries"].sort(key=lambda item: item["workspace_relative_path"])
        snapshot["source_snapshot_digest"] = _snapshot_digest(snapshot)
        self._valid("source_snapshot", snapshot)
        serialized = json.dumps(snapshot, ensure_ascii=False)
        for record in self.records.values():
            for text in _substantive(record):
                self.assertNotIn(text, serialized)

        metadata = load_json(ISSUE15_OPS / "valid" / "derived-index-metadata.json")
        metadata["generation_id"] = "dgen_issue17_response_communication_01"
        metadata["projection_scope"] = deepcopy(snapshot["projection_scope"])
        metadata["authorization_scope"] = deepcopy(snapshot["authorization_scope"])
        metadata["source_snapshot"] = deepcopy(snapshot)
        metadata["data_artifact"]["workspace_relative_path"] = (
            f"portia/derived/current_state_view/{work_id}/generations/"
            "dgen_issue17_response_communication_01/data.json"
        )
        metadata["generating_operation"]["operation_id"] = "op_rebuild_issue17_response_communication_current_state"
        self._valid("derived_index_metadata", metadata)

        pointer = load_json(ISSUE15_OPS / "valid" / "derived-current-pointer.json")
        pointer["projection_scope"] = deepcopy(snapshot["projection_scope"])
        pointer["generation_ref"]["generation_id"] = metadata["generation_id"]
        self._valid("derived_current_pointer", pointer)

    def test_cross_record_manifest_is_complete(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 17)
        self.assertEqual(self.manifest["group"], "cross_record")
        self.assertEqual(len(self.manifest["valid"]), 4)

    def test_response_and_communication_remain_distinct(self) -> None:
        scenario = load_json(CROSS_ROOT / "response-and-communication-distinct.json")
        response = scenario["response"]
        communication = scenario["communication"]
        self._valid("response", response)
        self._valid("communication", communication)
        self.assertEqual(response["work_id"], communication["work_id"])
        self.assertEqual(_relation(communication, "relates_to_response"), _work_ref(response))
        self.assertNotIn("sender", response)
        self.assertNotIn("recipients", response)
        self.assertNotIn("provider", communication)
        self.assertNotIn("action", communication)

    def test_failed_then_completed_contact_preserves_both_records(self) -> None:
        first, second = load_json(CROSS_ROOT / "failed-then-completed-contact.json")["communications"]
        self._valid("communication", first)
        self._valid("communication", second)
        self.assertNotEqual(first["communication_id"], second["communication_id"])
        self.assertEqual(first["act_state"], "recipient_unavailable")
        self.assertEqual(second["act_state"], "completed")
        self.assertNotIn("supersedes", second)
        self.assertLess(first["started_at"], second["started_at"])

    def test_determination_notice_and_response_share_exact_context(self) -> None:
        scenario = load_json(CROSS_ROOT / "determination-communication-response.json")
        communication = scenario["communication"]
        response = scenario["response"]
        expected = scenario["determination_ref"]
        self._valid("communication", communication)
        self._valid("response", response)
        self.assertEqual(response["determination_ref"], expected)
        self.assertEqual(_relation(communication, "conveys_determination"), expected)
        self.assertEqual(response["action"]["family"], "consequence")
        self.assertEqual(communication["purpose"]["kind"], "determination_notice")

    def test_communication_account_relation_preserves_source_boundary(self) -> None:
        scenario = load_json(CROSS_ROOT / "communication-account-boundary.json")
        communication = scenario["communication"]
        account_ref = scenario["source_evidence_record_ref"]
        self._valid("communication", communication)
        self.assertEqual(_relation(communication, "account_from_communication"), account_ref)
        qualifying_source_kinds = {"account", "observation"}
        self.assertNotIn(communication["record_type"], qualifying_source_kinds)
        self.assertIn(account_ref["record_ref"]["record_kind"], qualifying_source_kinds)

    def test_exact_contact_point_never_silently_follows_successor(self) -> None:
        communication = self.records["communication"]
        endpoint = deepcopy(communication["recipients"][0]["endpoint_ref"])
        successor = deepcopy(endpoint)
        successor["contact_point_id"] = "acp_family_phone_successor"
        self.assertEqual(communication["recipients"][0]["endpoint_ref"], endpoint)
        self.assertNotEqual(communication["recipients"][0]["endpoint_ref"], successor)


if __name__ == "__main__":
    unittest.main()
