from __future__ import annotations

from pathlib import Path
from typing import Any
import hashlib
import json
import re
import unittest

try:
    from .schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )
except ImportError:
    from schema_support import (
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        validator_for,
    )

FIXTURE_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures" /
    "issue-15" / "operational-derived-privacy"
)

EXPECTED_SCHEMA_PATHS = {
    "operation_journal": "schemas/v2/operations/operation-journal.schema.json",
    "operation_lock": "schemas/v2/operations/operation-lock.schema.json",
    "quarantine_record": "schemas/v2/operations/quarantine-record.schema.json",
    "integrity_finding": "schemas/v2/projections/integrity-finding.schema.json",
    "source_snapshot": "schemas/v1/projections/source-snapshot.schema.json",
    "derived_index_metadata": "schemas/v1/projections/derived-index-metadata.schema.json",
    "derived_current_pointer": "schemas/v1/projections/derived-current-pointer.schema.json",
}

FORBIDDEN_OPERATIONAL_NAMES = {
    "account_quote", "account_summary", "source_quote", "source_text",
    "observation_narrative", "observation_text", "student_name",
    "actor_display_name", "contact_value", "email", "phone",
    "credibility_score", "risk_score",
}

SUBSTANTIVE_PATH_MARKERS = (
    "quote_", "summary_", "narrative_", "source_said_", "student_said_",
)


def canonical_snapshot_digest(snapshot: dict[str, Any]) -> str:
    payload = {
        key: snapshot[key]
        for key in (
            "snapshot_algorithm", "projection_kind", "projection_scope",
            "authorization_scope", "discovery_roots", "source_contracts",
            "entries",
        )
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def exact_record_identity(target: dict[str, Any]) -> tuple[str, str, str, str]:
    if target.get("kind") in {"work_record", "record", "portia_work_record"}:
        exact = target["work_record_ref"]
    else:
        raise ValueError(f"Unsupported exact record target: {target!r}")
    work = exact["work_ref"]
    record = exact["record_ref"]
    return (
        work["work_id"], record["record_kind"], record["record_id"],
        record["contract_version"],
    )


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def privacy_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for node in iter_dicts(value):
        name = node.get("name")
        if isinstance(name, str):
            lowered = name.lower()
            if lowered in FORBIDDEN_OPERATIONAL_NAMES or any(
                token in lowered
                for token in ("quote", "summary", "narrative", "student_name")
            ):
                errors.append(f"sensitive evidence/fact name: {name}")
        path = node.get("workspace_relative_path")
        if isinstance(path, str) and any(
            marker in path.lower() for marker in SUBSTANTIVE_PATH_MARKERS
        ):
            errors.append("substantive evidence encoded in path")
    # Quarantine is the one shared operational contract with free-text reason detail.
    if value.get("record_type") == "quarantine_record":
        detail = value.get("reason_detail")
        if isinstance(detail, str):
            lowered = detail.lower()
            if "source said:" in lowered or "observation narrative:" in lowered:
                errors.append("quarantine reason copied substantive evidence")
    return errors


def application_errors(value: dict[str, Any]) -> list[str]:
    errors = privacy_errors(value)
    if value.get("record_type") == "operation_journal":
        predecessor_ids = [
            fact["value"] for fact in value.get("intent_facts", [])
            if fact.get("name") in {"predecessor_account_id", "predecessor_observation_id"}
            and fact.get("kind") == "identifier"
        ]
        if predecessor_ids and value["primary_target"].get("kind") == "work_record":
            current_id = value["primary_target"]["work_record_ref"]["record_ref"]["record_id"]
            if current_id not in predecessor_ids and value.get("operation_kind") == "update_record":
                errors.append("operation silently retargets exact predecessor to successor")
    if value.get("record_type") == "source_snapshot":
        if value["source_snapshot_digest"] != canonical_snapshot_digest(value):
            errors.append("source snapshot digest mismatch")
        contracts = [
            (item["contract_name"], item["contract_version"])
            for item in value["source_contracts"]
        ]
        if contracts != sorted(contracts):
            errors.append("source contracts are not sorted")
        paths = [entry["workspace_relative_path"] for entry in value["entries"]]
        if paths != sorted(paths):
            errors.append("source entries are not sorted")
    if value.get("record_type") == "derived_index_metadata":
        snap = value["source_snapshot"]
        if value["projection_kind"] != snap["projection_kind"]:
            errors.append("metadata projection kind disagrees with snapshot")
        if value["projection_scope"] != snap["projection_scope"]:
            errors.append("metadata projection scope disagrees with snapshot")
        if value["authorization_scope"] != snap["authorization_scope"]:
            errors.append("metadata authorization disagrees with snapshot")
        errors.extend(application_errors(snap))
    return errors


class Issue15OperationalDerivedPrivacyCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def validator(self, contract: str, version: str):
        return validator_for(
            contract, version, catalog=self.catalog, store=self.store
        )

    def test_reuses_existing_public_contract_versions(self) -> None:
        contracts = self.catalog["contracts"]
        for contract, path in EXPECTED_SCHEMA_PATHS.items():
            with self.subTest(contract=contract):
                version = "2" if contract in {
                    "operation_journal", "operation_lock",
                    "quarantine_record", "integrity_finding",
                } else "1"
                self.assertEqual(contracts[contract][version]["path"], path)
        for forbidden in (
            "account_operation_journal", "observation_operation_journal",
            "account_operation_lock", "observation_operation_lock",
            "account_quarantine_record", "observation_quarantine_record",
            "account_integrity_finding", "observation_integrity_finding",
            "account_source_snapshot", "observation_source_snapshot",
        ):
            self.assertNotIn(forbidden, contracts)

    def test_valid_scenarios_are_structurally_and_application_valid(self) -> None:
        for item in self.manifest["valid"]:
            value = load_json(FIXTURE_ROOT / "valid" / item["filename"])
            with self.subTest(filename=item["filename"]):
                errors = list(self.validator(item["contract"], item["version"]).iter_errors(value))
                self.assertFalse(errors, "\n".join(error.message for error in errors))
                self.assertFalse(application_errors(value))

    def test_structural_invalid_scenarios_fail_schema(self) -> None:
        for item in self.manifest["invalid"]:
            value = load_json(FIXTURE_ROOT / "invalid" / item["filename"])
            with self.subTest(filename=item["filename"]):
                errors = list(self.validator(item["contract"], item["version"]).iter_errors(value))
                self.assertTrue(errors)

    def test_application_invalid_scenarios_remain_structurally_valid(self) -> None:
        for item in self.manifest["application_invalid"]:
            value = load_json(FIXTURE_ROOT / "application-invalid" / item["filename"])
            with self.subTest(filename=item["filename"]):
                structural = list(self.validator(item["contract"], item["version"]).iter_errors(value))
                self.assertFalse(structural, "\n".join(error.message for error in structural))
                self.assertTrue(application_errors(value))

    def test_operational_targets_preserve_exact_account_observation_identity(self) -> None:
        expected = {
            ("evt_issue15_ops", "account", "acct_ops_1", "1"),
            ("evt_issue15_ops", "observation", "obs_ops_1", "1"),
        }
        seen: set[tuple[str, str, str, str]] = set()
        for filename in (
            "operation-journal-account.json", "operation-journal-observation.json",
            "operation-lock-account.json", "operation-lock-observation.json",
            "quarantine-account.json", "quarantine-observation.json",
            "integrity-account.json", "integrity-observation.json",
        ):
            value = load_json(FIXTURE_ROOT / "valid" / filename)
            if value.get("record_type") == "operation_journal":
                target = value["primary_target"]
            elif value.get("record_type") == "operation_lock":
                target = value["protected_target"]
            elif value.get("record_type") == "quarantine_record":
                target = value["target"]
            else:
                target = value["primary_target"]
            seen.add(exact_record_identity(target))
        self.assertEqual(seen, expected)

    def test_derived_snapshot_is_metadata_only(self) -> None:
        snapshot = load_json(FIXTURE_ROOT / "valid" / "source-snapshot.json")
        self.assertEqual(
            snapshot["source_contracts"],
            [
                {"contract_name": "account", "contract_version": "1"},
                {"contract_name": "observation", "contract_version": "1"},
            ],
        )
        serialized = json.dumps(snapshot, ensure_ascii=False).lower()
        for forbidden in (
            "verbatim_quote", "recorded_summary", "observation narrative",
            "source said:", "credibility_score", "risk_score",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_integrity_findings_remain_diagnostics_not_domain_findings(self) -> None:
        for filename in ("integrity-account.json", "integrity-observation.json"):
            finding = load_json(FIXTURE_ROOT / "valid" / filename)
            self.assertIn(
                finding["category"],
                {"structure", "chronology_provenance"},
            )
            self.assertNotIn(
                finding["code"],
                {"credible_report", "concerning_student", "policy_violation"},
            )
            self.assertFalse(privacy_errors(finding))

    def test_no_issue15_schema_or_catalog_files_in_fixture_slice(self) -> None:
        # This test intentionally asserts the integration result: Issue #15
        # must not version the shared operational/derived contracts merely to
        # target Account or Observation.
        issue15_paths = [
            path.relative_to(REPO_ROOT).as_posix()
            for path in REPO_ROOT.glob("schemas/**/*account*operation*.json")
        ] + [
            path.relative_to(REPO_ROOT).as_posix()
            for path in REPO_ROOT.glob("schemas/**/*observation*operation*.json")
        ]
        self.assertEqual(issue15_paths, [])


if __name__ == "__main__":
    unittest.main()
