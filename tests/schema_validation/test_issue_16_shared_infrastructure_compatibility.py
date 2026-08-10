from __future__ import annotations

from copy import deepcopy
from typing import Any
import hashlib
import json
import unittest

try:
    from .schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for
except ImportError:
    from schema_support import REPO_ROOT, load_json, load_validated_catalog_and_store, validator_for


ISSUE15_SHARED = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "shared-lifecycle-correction-dependency"
ISSUE15_MIGRATION = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "migration-removal-compatibility"
ISSUE15_OPS = REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-15" / "operational-derived-privacy"

FAMILY_FIXTURES = {
    "review": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "review" / "valid" / "completed-without-finding-or-evidence.json",
    "classification": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "classification" / "valid" / "reporter-category.json",
    "hypothesis": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "hypothesis" / "valid" / "event-under-consideration-empty-evidence.json",
    "determination": REPO_ROOT / "tests" / "schema_validation" / "fixtures" / "issue-16" / "determination" / "valid" / "teacher-local-conclusion.json",
}

ID_FIELDS = {
    "review": "review_id",
    "classification": "classification_id",
    "hypothesis": "hypothesis_id",
    "determination": "determination_id",
}

ACTIVATION_REASONS = {
    "review": "review_started",
    "classification": "judgment_recorded",
    "hypothesis": "judgment_recorded",
    "determination": "judgment_recorded",
}

LIFECYCLE_MATRIX = {
    "proposed": {"active", "invalidated", "superseded"},
    "active": {"invalidated", "superseded"},
    "invalidated": {"superseded"},
    "superseded": set(),
}

LIFECYCLE_REASONS = {
    "review": {
        "review_started", "recording_error", "wrong_reviewer", "wrong_target",
        "wrong_question", "invalid_provenance", "prohibited_payload",
        "corrected_by_successor", "duplicate_consolidated", "work_root_corrected",
        "contract_migrated", "other",
    },
    "classification": {
        "judgment_recorded", "recording_error", "wrong_selector", "wrong_target",
        "wrong_definition", "invalid_provenance", "prohibited_payload",
        "corrected_by_successor", "duplicate_consolidated", "work_root_corrected",
        "contract_migrated", "other",
    },
    "hypothesis": {
        "judgment_recorded", "recording_error", "wrong_author", "wrong_target",
        "invalid_provenance", "prohibited_payload", "corrected_by_successor",
        "duplicate_consolidated", "work_root_corrected", "contract_migrated", "other",
    },
    "determination": {
        "judgment_recorded", "recording_error", "wrong_decision_maker",
        "wrong_target", "wrong_authority", "wrong_process_basis",
        "invalid_provenance", "prohibited_payload", "corrected_by_successor",
        "duplicate_consolidated", "work_root_corrected", "contract_migrated", "other",
    },
}

EXPECTED_SHARED_CONTRACTS = {
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


def _record_id(record: dict[str, Any]) -> str:
    return record[ID_FIELDS[record["record_type"]]]


def _local_record_target(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "local_record",
        "record_ref": {
            "record_kind": record["record_type"],
            "record_id": _record_id(record),
            "contract_version": "1",
        },
    }


def _work_record_ref(record: dict[str, Any], *, record_contract_version: str = "1") -> dict[str, Any]:
    return {
        "work_ref": {
            "module_id": "portia",
            "class_id": record["class_id"],
            "work_id": record["work_id"],
            "work_kind": "event",
            "contract_version": "2",
        },
        "record_ref": {
            "record_kind": record["record_type"],
            "record_id": _record_id(record),
            "contract_version": record_contract_version,
        },
    }


def _retarget_account_template(value: Any, record: dict[str, Any]) -> Any:
    family = record["record_type"]
    rid = _record_id(record)
    replacements = (
        ("eng10_p2_2026", record["class_id"]),
        ("evt_issue15_ops", record["work_id"]),
        ("evt_alpha", record["work_id"]),
        ("acct_student_report_1", rid),
        ("acct_dependency_target", rid),
        ("acct_amendment_forbidden", rid),
        ("acct_disputed", rid),
        ("acct_history", rid),
        ("acct_lifecycle_active", rid),
        ("acct_ops_1", rid),
        ("account", family),
    )
    if isinstance(value, str):
        out = value
        for old, new in replacements:
            out = out.replace(old, new)
        return out
    if isinstance(value, list):
        return [_retarget_account_template(item, record) for item in value]
    if isinstance(value, dict):
        return {key: _retarget_account_template(item, record) for key, item in value.items()}
    return value


def _canonical_snapshot_digest(snapshot: dict[str, Any]) -> str:
    payload = {
        key: snapshot[key]
        for key in (
            "snapshot_algorithm", "projection_kind", "projection_scope",
            "authorization_scope", "discovery_roots", "source_contracts", "entries",
        )
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _substantive_strings(record: dict[str, Any]) -> set[str]:
    family = record["record_type"]
    values: set[str] = set()
    if family == "review":
        question = record.get("question")
        if isinstance(question, dict) and isinstance(question.get("text"), str):
            values.add(question["text"])
    elif family == "classification":
        result = record.get("result")
        if isinstance(result, dict):
            definition = result.get("definition")
            if isinstance(definition, dict):
                for key in ("category_label", "definition_text"):
                    if isinstance(definition.get(key), str):
                        values.add(definition[key])
            if isinstance(result.get("rationale"), str):
                values.add(result["rationale"])
    elif family == "hypothesis":
        for key in ("proposition", "rationale"):
            if isinstance(record.get(key), str):
                values.add(record[key])
    elif family == "determination":
        question = record.get("question")
        if isinstance(question, str):
            values.add(question)
        outcome = record.get("outcome")
        if isinstance(outcome, dict):
            for key in ("text", "label", "definition_text", "rationale"):
                if isinstance(outcome.get(key), str):
                    values.add(outcome[key])
        if isinstance(record.get("rationale"), str):
            values.add(record["rationale"])
    return {value for value in values if value}


class Issue16SharedInfrastructureCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.records = {family: load_json(path) for family, path in FAMILY_FIXTURES.items()}
        cls.validators = {
            family: validator_for(family, "1", catalog=cls.catalog, store=cls.store)
            for family in FAMILY_FIXTURES
        }
        for contract, (version, _path) in EXPECTED_SHARED_CONTRACTS.items():
            cls.validators[contract] = validator_for(
                contract, version, catalog=cls.catalog, store=cls.store
            )

    def _assert_structurally_valid(self, contract: str, value: dict[str, Any]) -> None:
        errors = list(self.validators[contract].iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_judgment_roots_used_by_compatibility_probes_are_valid(self) -> None:
        for family, record in self.records.items():
            with self.subTest(family=family):
                self._assert_structurally_valid(family, record)
                self.assertEqual(record["status"], "active")

    def test_shared_contract_versions_are_reused_without_forks(self) -> None:
        contracts = self.catalog["contracts"]
        for contract, (version, path) in EXPECTED_SHARED_CONTRACTS.items():
            with self.subTest(contract=contract):
                self.assertIn(version, contracts[contract])
                self.assertEqual(contracts[contract][version]["path"], path)
        forbidden: set[str] = set()
        for family in FAMILY_FIXTURES:
            for suffix in (
                "lifecycle_transition", "lifecycle_history_correction", "amendment",
                "statement_of_disagreement", "dependency", "record_migration",
                "exceptional_removal", "operation_journal", "operation_lock",
                "quarantine_record", "integrity_finding", "source_snapshot",
                "derived_index_metadata", "derived_current_pointer",
            ):
                forbidden.add(f"{family}_{suffix}")
        self.assertTrue(forbidden.isdisjoint(contracts))

    def test_lifecycle_transition_reuses_common_matrix_and_family_reasons(self) -> None:
        for family, record in self.records.items():
            transition = {
                "schema_version": "1",
                "record_type": "lifecycle_transition",
                "module_id": "portia",
                "class_id": record["class_id"],
                "work_id": record["work_id"],
                "transition_id": f"lct_issue16_{family}_activate",
                "target": _local_record_target(record),
                "previous_transition": None,
                "from_status": "proposed",
                "to_status": "active",
                "reason": {"category": "workflow", "code": ACTIVATION_REASONS[family]},
                "effective_at": record["created_at"],
                "creation_source": {"type": "digital_entry"},
                "created_at": record["updated_at"],
                "created_by": {"type": "local_operator", "display_label": "Synthetic Teacher"},
            }
            with self.subTest(family=family):
                self._assert_structurally_valid("lifecycle_transition", transition)
                self.assertIn(transition["to_status"], LIFECYCLE_MATRIX[transition["from_status"]])
                self.assertIn(transition["reason"]["code"], LIFECYCLE_REASONS[family])

    def test_lifecycle_history_correction_targets_each_family_exactly(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "history-account-select-replacement.json")
        for family, record in self.records.items():
            scenario = _retarget_account_template(deepcopy(template), record)
            scenario["record"] = record
            scenario["replacement_transition"]["reason"] = {
                "category": "workflow",
                "code": ACTIVATION_REASONS[family],
            }
            with self.subTest(family=family):
                self._assert_structurally_valid("lifecycle_transition", scenario["replaced_transition"])
                self._assert_structurally_valid("lifecycle_transition", scenario["replacement_transition"])
                self._assert_structurally_valid("lifecycle_history_correction", scenario["correction"])
                target = scenario["correction"]["target"]["record_ref"]
                self.assertEqual(
                    (target["record_kind"], target["record_id"], target["contract_version"]),
                    (family, _record_id(record), "1"),
                )

    def test_statement_of_disagreement_reuses_generic_exact_target(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "disagreement-targets-account.json")
        for family in ("classification", "hypothesis", "determination"):
            record = self.records[family]
            scenario = _retarget_account_template(deepcopy(template), record)
            scenario["target_record"] = record
            with self.subTest(family=family):
                self._assert_structurally_valid("statement_of_disagreement", scenario["disagreement"])
                target = scenario["disagreement"]["target"]["record_ref"]
                self.assertEqual(
                    (target["record_kind"], target["record_id"], target["contract_version"]),
                    (family, _record_id(record), "1"),
                )
                self.assertEqual(record["status"], "active")

    def test_v1_amendment_is_structurally_reusable_but_application_prohibited(self) -> None:
        template = load_json(
            ISSUE15_SHARED / "application-invalid" / "amendment-account-prohibited.json"
        )
        material_paths = {
            "review": "/question",
            "classification": "/result",
            "hypothesis": "/proposition",
            "determination": "/outcome",
        }
        for family, record in self.records.items():
            scenario = _retarget_account_template(deepcopy(template), record)
            scenario["target_record"] = record
            scenario["amendment"]["changes"][0]["path"] = material_paths[family]
            with self.subTest(family=family):
                self._assert_structurally_valid("amendment", scenario["amendment"])
                target = scenario["amendment"]["target"]["record_ref"]
                self.assertEqual(target["record_kind"], family)
                self.assertEqual(target["record_id"], _record_id(record))
                self.assertEqual(
                    f"portia.{family}.amendment_prohibited_v1",
                    f"portia.{record['record_type']}.amendment_prohibited_v1",
                )

    def test_dependency_reuses_exact_record_references_for_all_families(self) -> None:
        template = load_json(ISSUE15_SHARED / "valid" / "dependency-references-account.json")
        for family, record in self.records.items():
            scenario = _retarget_account_template(deepcopy(template), record)
            scenario["dependency_record"] = record
            dependency = scenario["dependency"]
            with self.subTest(family=family):
                self._assert_structurally_valid("dependency", dependency)
                self.assertEqual(dependency["dependency"]["work_record_ref"], _work_record_ref(record))

    def test_dependency_does_not_silently_follow_a_successor(self) -> None:
        record = self.records["classification"]
        template = load_json(ISSUE15_SHARED / "valid" / "dependency-references-account.json")
        scenario = _retarget_account_template(deepcopy(template), record)
        dependency = scenario["dependency"]
        original_ref = deepcopy(dependency["dependency"]["work_record_ref"])
        successor = deepcopy(record)
        successor["classification_id"] = "cls_issue16_infra_successor"
        self._assert_structurally_valid("dependency", dependency)
        self.assertEqual(original_ref, dependency["dependency"]["work_record_ref"])
        self.assertNotEqual(dependency["dependency"]["work_record_ref"], _work_record_ref(successor))

    def test_record_migration_reuses_generic_exact_endpoints(self) -> None:
        template = load_json(ISSUE15_MIGRATION / "valid" / "migration-account-v1-v2.json")
        for family, record in self.records.items():
            scenario = _retarget_account_template(deepcopy(template), record)
            migration = scenario["migration"]
            migration["source"]["work_record_ref"] = _work_record_ref(record)
            migration["source"]["observed_updated_at"] = record["updated_at"]
            migration["destination"]["work_record_ref"] = _work_record_ref(
                record, record_contract_version="2"
            )
            with self.subTest(family=family):
                self._assert_structurally_valid("record_migration", migration)
                self.assertEqual(migration["source"]["work_record_ref"], _work_record_ref(record))
                self.assertEqual(
                    migration["destination"]["work_record_ref"]["record_ref"]["contract_version"],
                    "2",
                )
                self.assertTrue(scenario["semantic_equivalent"])
                self.assertTrue(scenario["lifecycle_preserved"])

    def test_exceptional_removal_reuses_exact_targets_without_domain_text(self) -> None:
        template = load_json(ISSUE15_MIGRATION / "valid" / "removal-account-exact.json")
        for family, record in self.records.items():
            scenario = _retarget_account_template(deepcopy(template), record)
            removal = scenario["removal"]
            removal["target"]["work_record_ref"] = _work_record_ref(record)
            removal["lifecycle_snapshot"]["status"] = record["status"]
            with self.subTest(family=family):
                self._assert_structurally_valid("exceptional_removal", removal)
                self.assertEqual(removal["target"]["work_record_ref"], _work_record_ref(record))
                serialized = json.dumps(removal, ensure_ascii=False)
                for text in _substantive_strings(record):
                    self.assertNotIn(text, serialized)

    def test_operation_journal_and_lock_target_each_family_without_version_bump(self) -> None:
        journal_template = load_json(ISSUE15_OPS / "valid" / "operation-journal-account.json")
        lock_template = load_json(ISSUE15_OPS / "valid" / "operation-lock-account.json")
        for family, record in self.records.items():
            journal = _retarget_account_template(deepcopy(journal_template), record)
            lock = _retarget_account_template(deepcopy(lock_template), record)
            with self.subTest(family=family, contract="operation_journal"):
                self._assert_structurally_valid("operation_journal", journal)
                self.assertEqual(journal["primary_target"]["work_record_ref"], _work_record_ref(record))
            with self.subTest(family=family, contract="operation_lock"):
                self._assert_structurally_valid("operation_lock", lock)
                self.assertEqual(lock["protected_target"]["work_record_ref"], _work_record_ref(record))
            serialized = json.dumps({"journal": journal, "lock": lock}, ensure_ascii=False)
            for text in _substantive_strings(record):
                self.assertNotIn(text, serialized)

    def test_quarantine_and_integrity_remain_diagnostics_for_each_family(self) -> None:
        quarantine_template = load_json(ISSUE15_OPS / "valid" / "quarantine-account.json")
        integrity_template = load_json(ISSUE15_OPS / "valid" / "integrity-account.json")
        for family, record in self.records.items():
            quarantine = _retarget_account_template(deepcopy(quarantine_template), record)
            finding = _retarget_account_template(deepcopy(integrity_template), record)
            with self.subTest(family=family, contract="quarantine_record"):
                self._assert_structurally_valid("quarantine_record", quarantine)
                self.assertEqual(quarantine["target"]["work_record_ref"], _work_record_ref(record))
            with self.subTest(family=family, contract="integrity_finding"):
                self._assert_structurally_valid("integrity_finding", finding)
                self.assertEqual(finding["primary_target"]["work_record_ref"], _work_record_ref(record))
                self.assertNotIn(
                    finding["code"],
                    {"credible_report", "student_risk", "policy_violation", "substantiated_determination"},
                )
            serialized = json.dumps({"quarantine": quarantine, "finding": finding}, ensure_ascii=False)
            for text in _substantive_strings(record):
                self.assertNotIn(text, serialized)

    def test_source_snapshot_and_derived_metadata_include_judgment_contracts_metadata_only(self) -> None:
        snapshot = load_json(ISSUE15_OPS / "valid" / "source-snapshot.json")
        work_id = "evt_issue16_infra_derived"
        class_id = "eng10_p2_2026"
        snapshot["projection_scope"]["work_ref"]["work_id"] = work_id
        snapshot["discovery_roots"] = [f"classes/{class_id}/modules/portia/work/{work_id}"]
        snapshot["source_contracts"] = [
            {"contract_name": family, "contract_version": "1"}
            for family in sorted(FAMILY_FIXTURES)
        ]
        synthetic_ids = {
            "classification": "cls_issue16_derived",
            "determination": "det_issue16_derived",
            "hypothesis": "hyp_issue16_derived",
            "review": "rvw_issue16_derived",
        }
        snapshot["entries"] = []
        for index, family in enumerate(sorted(FAMILY_FIXTURES), start=1):
            rid = synthetic_ids[family]
            snapshot["entries"].append(
                {
                    "workspace_relative_path": (
                        f"classes/{class_id}/modules/portia/work/{work_id}/"
                        f"records/{family}/{rid}.json"
                    ),
                    "byte_length": 700 + index,
                    "sha256_digest": str(index) * 64,
                    "source_role": "canonical_domain",
                    "contract_or_artifact_kind": family,
                }
            )
        snapshot["entries"].sort(key=lambda item: item["workspace_relative_path"])
        snapshot["source_snapshot_digest"] = _canonical_snapshot_digest(snapshot)

        self._assert_structurally_valid("source_snapshot", snapshot)
        serialized = json.dumps(snapshot, ensure_ascii=False)
        for record in self.records.values():
            for text in _substantive_strings(record):
                self.assertNotIn(text, serialized)

        metadata = load_json(ISSUE15_OPS / "valid" / "derived-index-metadata.json")
        metadata["generation_id"] = "dgen_issue16_judgment_01"
        metadata["projection_scope"] = deepcopy(snapshot["projection_scope"])
        metadata["authorization_scope"] = deepcopy(snapshot["authorization_scope"])
        metadata["source_snapshot"] = deepcopy(snapshot)
        metadata["data_artifact"]["workspace_relative_path"] = (
            "portia/derived/current_state_view/"
            f"{work_id}/generations/dgen_issue16_judgment_01/data.json"
        )
        metadata["generating_operation"]["operation_id"] = "op_rebuild_issue16_judgment_current_state"
        self._assert_structurally_valid("derived_index_metadata", metadata)

        pointer = load_json(ISSUE15_OPS / "valid" / "derived-current-pointer.json")
        pointer["projection_scope"] = deepcopy(snapshot["projection_scope"])
        pointer["generation_ref"]["generation_id"] = metadata["generation_id"]
        self._assert_structurally_valid("derived_current_pointer", pointer)

    def test_current_pointer_is_navigation_not_canonical_judgment(self) -> None:
        pointer = load_json(ISSUE15_OPS / "valid" / "derived-current-pointer.json")
        self._assert_structurally_valid("derived_current_pointer", pointer)
        serialized = json.dumps(pointer, ensure_ascii=False).lower()
        for forbidden in (
            "question", "category_label", "proposition", "outcome",
            "authority_context", "policy_violation", "risk_score",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
