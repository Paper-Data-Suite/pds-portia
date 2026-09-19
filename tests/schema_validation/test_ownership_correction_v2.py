from __future__ import annotations

import copy
import hashlib
import json
import unittest
from pathlib import Path
from typing import Any

try:
    from .schema_support import (
        FIXTURE_ROOT,
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )
except ImportError:
    from schema_support import (
        FIXTURE_ROOT,
        REPO_ROOT,
        load_json,
        load_validated_catalog_and_store,
        schema_id_for,
        validator_for,
    )


V1_PATH = REPO_ROOT / "schemas/v1/corrections/ownership-correction.schema.json"
V2_PATH = "schemas/v2/corrections/ownership-correction.schema.json"
CASES_PATH = FIXTURE_ROOT / "issue-47/ownership-correction-v2-cases.json"
V1_FROZEN_SHA256 = "7ffdc29786cede8a294ca58545aa475eb77ccadf70af442946d6b22de4b0a5df"
FAMILY_SCHEMAS = {
    "fidelity": (
        "schemas/v1/support-processes/fidelity.schema.json",
        "fidelityWorkRecordRef",
        ("support_process", "support_process"),
    ),
    "implementation": (
        "schemas/v1/support-processes/implementation.schema.json",
        "implementationWorkRecordRef",
        ("support_process", "support_process"),
    ),
    "follow_up": (
        "schemas/v1/follow-ups/follow-up.schema.json",
        "followUpWorkRecordRef",
        ("event", "support_process"),
    ),
    "outcome": (
        "schemas/v1/outcomes/outcome.schema.json",
        "outcomeWorkRecordRef",
        ("support_process", "event"),
    ),
    "reentry": (
        "schemas/v1/reentries/reentry.schema.json",
        "reentryRef",
        ("event", "support_process"),
    ),
    "repair": (
        "schemas/v1/repairs/repair.schema.json",
        "repairWorkRecordRef",
        ("support_process", "event"),
    ),
}


def _work_ref(kind: str, work_id: str, *, class_id: str) -> dict[str, str]:
    return {
        "module_id": "portia",
        "class_id": class_id,
        "work_id": work_id,
        "work_kind": kind,
        "contract_version": "2" if kind == "event" else "1",
    }


def _record_id(record_kind: str, suffix: str) -> str:
    prefixes = {
        "fidelity": "fid",
        "follow_up": "fup",
        "implementation": "imp",
        "outcome": "out",
        "reentry": "ren",
        "repair": "rpr",
    }
    return f"{prefixes[record_kind]}_{suffix}"


def _certificate(case: dict[str, Any]) -> dict[str, Any]:
    correction_kind = case.get("correction_kind", "child_work_root")
    source_kind = case["source_work_kind"]
    destination_kind = case["destination_work_kind"]
    source_work = _work_ref(source_kind, case["source_work_id"], class_id="class_source")
    destination_work = _work_ref(
        destination_kind,
        case["destination_work_id"],
        class_id="class_destination",
    )
    if correction_kind == "event_class_ownership":
        source = {
            "kind": "event_work",
            "work_ref": source_work,
            "observed_updated_at": "2026-09-18T09:00:00-04:00",
        }
        destination = {
            "kind": "event_work",
            "work_ref": destination_work,
            "observed_updated_at": "2026-09-18T09:05:00-04:00",
        }
        reason = {"code": "wrong_class"}
    else:
        family = case.get("record_kind", "follow_up")
        source = {
            "kind": "work_record",
            "work_record_ref": {
                "work_ref": source_work,
                "record_ref": {
                    "record_kind": family,
                    "record_id": _record_id(family, "source"),
                    "contract_version": "1",
                },
            },
            "observed_updated_at": "2026-09-18T09:00:00-04:00",
        }
        destination = {
            "kind": "work_record",
            "work_record_ref": {
                "work_ref": destination_work,
                "record_ref": {
                    "record_kind": family,
                    "record_id": _record_id(family, "destination"),
                    "contract_version": "1",
                },
            },
            "observed_updated_at": "2026-09-18T09:05:00-04:00",
        }
        reason = {"code": "wrong_work_root"}
    return {
        "schema_version": "2",
        "record_type": "ownership_correction",
        "module_id": "portia",
        "class_id": destination_work["class_id"],
        "work_id": destination_work["work_id"],
        "work_kind": destination_work["work_kind"],
        "correction_id": "owc_v2_fixture",
        "correction_kind": correction_kind,
        "source": source,
        "destination": destination,
        "reason": reason,
        "effective_at": "2026-09-18T09:05:00-04:00",
        "creation_source": {"type": "digital_entry"},
        "created_at": "2026-09-18T09:06:00-04:00",
        "created_by": {"type": "system_process", "process_id": "issue47_slice33_2a"},
    }


class OwnershipCorrectionV2SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "ownership_correction", "2", catalog=cls.catalog, store=cls.store
        )
        cls.schema = cls.store.schema_for_id(
            schema_id_for("ownership_correction", "2", cls.catalog)
        )
        cls.cases = load_json(CASES_PATH)

    def assert_valid(self, value: object) -> None:
        errors = list(self.validator.iter_errors(value))
        self.assertFalse(errors, "\n".join(error.message for error in errors))

    def test_v1_public_schema_is_byte_for_byte_frozen(self) -> None:
        digest = hashlib.sha256(V1_PATH.read_bytes()).hexdigest()
        self.assertEqual(digest, V1_FROZEN_SHA256)

    def test_v2_is_cataloged_at_immutable_matching_path(self) -> None:
        expected = "https://paper-data-suite.github.io/pds-portia/" + V2_PATH
        self.assertEqual(schema_id_for("ownership_correction", "2", self.catalog), expected)
        self.assertEqual(self.schema["$id"], expected)

    def test_representative_work_kind_combinations_are_valid(self) -> None:
        for case in self.cases["valid"]:
            with self.subTest(case=case["name"]):
                self.assert_valid(_certificate(case))

    def test_v2_child_endpoints_use_unrestricted_exact_work_record_refs(self) -> None:
        ref = self.schema["$defs"]["workRecordEndpoint"]["properties"][
            "work_record_ref"
        ]["$ref"]
        self.assertTrue(ref.endswith("exact-portia-work-record-ref.schema.json"))
        self.assertNotIn("eventWorkRecordRef", self.schema["$defs"])

    def test_event_class_ownership_remains_event_only(self) -> None:
        invalid = _certificate(
            {
                "correction_kind": "event_class_ownership",
                "source_work_kind": "event",
                "source_work_id": "evt_source",
                "destination_work_kind": "support_process",
                "destination_work_id": "sup_destination",
            }
        )
        self.assertTrue(list(self.validator.iter_errors(invalid)))

    def test_structural_invalid_fixture_matrix_fails(self) -> None:
        base_case = self.cases["valid"][1]
        for name in self.cases["structural_invalid"]:
            value = _certificate(base_case)
            if name == "wrong_schema_version":
                value["schema_version"] = "1"
            elif name == "event_scope_with_support_process_id":
                value["work_kind"] = "event"
            elif name == "support_process_scope_with_event_id":
                value["work_id"] = "evt_destination"
            elif name == "event_class_with_support_process_destination":
                value = _certificate(
                    {
                        "correction_kind": "event_class_ownership",
                        "source_work_kind": "event",
                        "source_work_id": "evt_source",
                        "destination_work_kind": "support_process",
                        "destination_work_id": "sup_destination",
                    }
                )
            elif name == "mixed_endpoint_kinds":
                value["destination"] = {
                    "kind": "event_work",
                    "work_ref": _work_ref("event", "evt_destination", class_id="class_destination"),
                    "observed_updated_at": "2026-09-18T09:05:00-04:00",
                }
            elif name == "malformed_parent_reference":
                value["parent_correction"] = {
                    "record_kind": "ownership_correction",
                    "record_id": "owc_parent",
                    "contract_version": "1",
                }
            elif name == "unknown_reason":
                value["reason"] = {"code": "wrong_plan"}
            else:  # pragma: no cover - fixture/test drift guard
                self.fail(f"unknown structural fixture {name}")
            with self.subTest(case=name):
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixture_matrix_is_structurally_valid(self) -> None:
        declared = set(self.schema["x-portia-application-invariants"])
        base = _certificate(self.cases["valid"][1])
        for case in self.cases["application_invalid"]:
            with self.subTest(case=case["name"]):
                self.assert_valid(copy.deepcopy(base))
                self.assertIn(case["rule_id"], declared)

    def test_parent_reference_is_exact_v2_local_reference(self) -> None:
        parent = self.schema["$defs"]["ownershipCorrectionRef"]
        self.assertTrue(parent["allOf"][0]["$ref"].endswith("exact-local-record-ref.schema.json"))
        constrained = parent["allOf"][1]["properties"]
        self.assertEqual(constrained["record_kind"]["const"], "ownership_correction")
        self.assertEqual(constrained["contract_version"]["const"], "2")

    def test_all_correct_work_root_families_are_successor_compatible(self) -> None:
        for family, (relative_path, ref_def, kinds) in FAMILY_SCHEMAS.items():
            schema = load_json(REPO_ROOT / relative_path)
            reference = schema["$defs"][ref_def]
            self.assertTrue(
                reference["allOf"][0]["$ref"].endswith(
                    "exact-portia-work-record-ref.schema.json"
                )
            )
            reasons = schema["$defs"]["supersessionEntry"]["properties"][
                "reason"
            ]["enum"]
            self.assertIn("work_root_corrected", reasons)
            source_kind, destination_kind = kinds
            case = {
                "source_work_kind": source_kind,
                "source_work_id": (
                    "evt_source" if source_kind == "event" else "sup_source"
                ),
                "destination_work_kind": destination_kind,
                "destination_work_id": (
                    "evt_destination"
                    if destination_kind == "event"
                    else "sup_destination"
                ),
                "record_kind": family,
            }
            with self.subTest(family=family):
                self.assert_valid(_certificate(case))

    def test_fixture_file_is_stable_json_data(self) -> None:
        reloaded = json.loads(Path(CASES_PATH).read_text(encoding="utf-8"))
        self.assertEqual(reloaded, self.cases)


if __name__ == "__main__":
    unittest.main()
