from __future__ import annotations

from datetime import datetime
import json
import unittest
from typing import Any

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

NEED_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "support-need"
)
GOAL_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "support-goal"
)
CROSS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "cross-record"
)
NEED_SCHEMA_PATH = "schemas/v1/support-processes/support-need.schema.json"
GOAL_SCHEMA_PATH = "schemas/v1/support-processes/support-goal.schema.json"

def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)

def _target_ids(target: dict[str, Any]) -> list[str]:
    kind = target["kind"]
    if kind == "support_process":
        return []
    if kind == "support_process_participant":
        return [target["record_ref"]["record_id"]]
    return [
        item["record_ref"]["record_id"]
        for item in target["targets"]
    ]

def _ref_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    ref = entry["work_record_ref"]
    return (
        ref["work_ref"]["class_id"],
        ref["work_ref"]["work_id"],
        ref["record_ref"]["record_id"],
    )

def _record_application_errors(
    value: dict[str, Any],
    *,
    family_label: str,
    id_field: str,
) -> list[str]:
    errors: list[str] = []

    if _dt(value["updated_at"]) < _dt(value["created_at"]):
        errors.append("updated_at precedes created_at")

    creation = value["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and value["status"] != "proposed"
    ):
        errors.append("paper/import activation requires accepted review history")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [_ref_identity(entry) for entry in supersedes]
        reasons = [entry["reason"] for entry in supersedes]
        current = (
            value["class_id"],
            value["work_id"],
            value[id_field],
        )

        if len(set(identities)) != len(identities):
            errors.append(f"{family_label} predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append(f"mixed {family_label} supersession reasons")

        for identity in identities:
            if identity == current:
                errors.append(f"{family_label} cannot supersede itself")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        f"duplicate consolidation needs two {family_label} predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append(f"{family_label} work-root correction is one-to-one")
                else:
                    ref = supersedes[0]["work_record_ref"]
                    work = ref["work_ref"]
                    record = ref["record_ref"]
                    if (
                        work["class_id"] == value["class_id"]
                        and work["work_id"] == value["work_id"]
                    ):
                        errors.append(
                            "work-root correction requires a different Support Process root"
                        )
                    if record["record_id"] != value[id_field]:
                        errors.append(
                            f"work-root correction must preserve {family_label} ID"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        f"ordinary {family_label} correction is one-to-one"
                    )
                else:
                    ref = supersedes[0]["work_record_ref"]["work_ref"]
                    if (
                        ref["class_id"] != value["class_id"]
                        or ref["work_id"] != value["work_id"]
                    ):
                        errors.append(
                            f"ordinary {family_label} correction cannot cross Support Process roots"
                        )
    return errors

def need_application_errors(value: dict[str, Any]) -> list[str]:
    return _record_application_errors(
        value, family_label="Support Need", id_field="need_id"
    )

def goal_application_errors(value: dict[str, Any]) -> list[str]:
    return _record_application_errors(
        value, family_label="Support Goal", id_field="goal_id"
    )

def target_graph_errors(
    value: dict[str, Any],
    participants: list[dict[str, Any]],
    *,
    family_label: str,
) -> list[str]:
    errors: list[str] = []
    ids = _target_ids(value["target"])
    if not ids:
        return errors

    by_id = {
        item["participant_id"]: item
        for item in participants
        if item["status"] == "active"
    }
    if any(pid not in by_id for pid in ids):
        errors.append(
            f"{family_label} target participant does not resolve in owning Support Process"
        )
        return errors

    logical = [by_id[pid]["logical_person_key"] for pid in ids]
    if len(logical) != len(set(logical)):
        errors.append(
            f"{family_label} target set repeats a logical participant"
        )
    return errors


class Issue18NeedGoalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.need_validator = validator_for(
            "support_need", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.goal_validator = validator_for(
            "support_goal", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.need_manifest = load_json(NEED_ROOT / "manifest.json")
        cls.goal_manifest = load_json(GOAL_ROOT / "manifest.json")
        cls.cross = load_json(CROSS_ROOT / "support-need-goal.json")

    def test_catalog_entries_and_manifest_metadata(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        self.assertEqual(
            self.catalog["contracts"]["support_need"]["1"],
            {"schema_id": base + NEED_SCHEMA_PATH, "path": NEED_SCHEMA_PATH},
        )
        self.assertEqual(
            self.catalog["contracts"]["support_goal"]["1"],
            {"schema_id": base + GOAL_SCHEMA_PATH, "path": GOAL_SCHEMA_PATH},
        )
        self.assertEqual(self.need_manifest["contract"], "support_need")
        self.assertEqual(len(self.need_manifest["valid"]), 8)
        self.assertEqual(len(self.need_manifest["invalid"]), 13)
        self.assertEqual(len(self.need_manifest["application_invalid"]), 12)
        self.assertEqual(self.goal_manifest["contract"], "support_goal")
        self.assertEqual(len(self.goal_manifest["valid"]), 6)
        self.assertEqual(len(self.goal_manifest["invalid"]), 12)
        self.assertEqual(len(self.goal_manifest["application_invalid"]), 12)

    def test_support_need_valid_fixtures_pass(self) -> None:
        for filename in self.need_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(NEED_ROOT / "valid" / filename)
                structural = list(self.need_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(need_application_errors(value), [])

    def test_support_need_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.need_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(NEED_ROOT / "invalid" / filename)
                self.assertTrue(list(self.need_validator.iter_errors(value)))

    def test_support_need_application_invalid_fixtures_fail(self) -> None:
        for item in self.need_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    NEED_ROOT / "application-invalid" / item["file"]
                )
                structural = list(self.need_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                errors = need_application_errors(value)
                errors.extend(
                    target_graph_errors(
                        value, self.cross["participants"],
                        family_label="Support Need",
                    )
                )
                self.assertIn(item["expected_error"], errors)

    def test_support_goal_valid_fixtures_pass(self) -> None:
        for filename in self.goal_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(GOAL_ROOT / "valid" / filename)
                structural = list(self.goal_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(goal_application_errors(value), [])

    def test_support_goal_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.goal_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(GOAL_ROOT / "invalid" / filename)
                self.assertTrue(list(self.goal_validator.iter_errors(value)))

    def test_support_goal_application_invalid_fixtures_fail(self) -> None:
        for item in self.goal_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    GOAL_ROOT / "application-invalid" / item["file"]
                )
                structural = list(self.goal_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                errors = goal_application_errors(value)
                errors.extend(
                    target_graph_errors(
                        value, self.cross["participants"],
                        family_label="Support Goal",
                    )
                )
                self.assertIn(item["expected_error"], errors)

    def test_valid_targets_resolve_against_support_process_participants(self) -> None:
        for family, value in (
            ("Support Need", self.cross["need"]),
            ("Support Goal", self.cross["goal"]),
        ):
            with self.subTest(family=family):
                self.assertEqual(
                    target_graph_errors(
                        value, self.cross["participants"],
                        family_label=family,
                    ),
                    [],
                )

    def test_need_contract_excludes_diagnosis_risk_function_and_outcome(self) -> None:
        schema = load_json(REPO_ROOT / NEED_SCHEMA_PATH)
        properties = schema["properties"]
        for forbidden in (
            "diagnosis", "disability", "function", "risk_score",
            "eligibility", "progress", "outcome", "effectiveness",
        ):
            self.assertNotIn(forbidden, properties)
        text = json.dumps(schema).lower()
        self.assertIn("no_diagnosis_inference", text)
        self.assertIn("no_risk_or_function_inference", text)
        self.assertIn("no_outcome_or_effectiveness", text)

    def test_goal_contract_keeps_criteria_and_measurement_planning_only(self) -> None:
        schema = load_json(REPO_ROOT / GOAL_SCHEMA_PATH)
        properties = schema["properties"]
        self.assertIn("planned_criteria", properties)
        self.assertIn("measurement_approach", properties)
        for forbidden in (
            "progress", "attained", "attainment", "outcome",
            "effectiveness", "grade", "proficiency_level", "compliance",
        ):
            self.assertNotIn(forbidden, properties)
        text = json.dumps(schema).lower()
        self.assertIn("criteria_are_planning_only", text)
        self.assertIn("measurement_approach_is_planning_only", text)
        self.assertIn("no_progress_or_attainment", text)
        self.assertIn("no_grade_or_proficiency", text)

    def test_need_and_goal_reuse_existing_target_contract(self) -> None:
        need = load_json(REPO_ROOT / NEED_SCHEMA_PATH)
        goal = load_json(REPO_ROOT / GOAL_SCHEMA_PATH)
        expected = (
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/targets/support-process-target-ref.schema.json"
        )
        self.assertEqual(need["properties"]["target"]["$ref"], expected)
        self.assertEqual(goal["properties"]["target"]["$ref"], expected)

    def test_need_and_goal_have_no_v1_amendment_paths(self) -> None:
        for path in (NEED_SCHEMA_PATH, GOAL_SCHEMA_PATH):
            with self.subTest(path=path):
                schema = load_json(REPO_ROOT / path)
                text = json.dumps(schema)
                self.assertIn("amendment_prohibited_v1", text)
                self.assertNotIn('"amendments"', text)
                self.assertNotIn('"amendment_paths"', text)


if __name__ == "__main__":
    unittest.main()
