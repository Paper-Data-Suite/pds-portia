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

SUPPORT_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "support"
)
INTERVENTION_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "intervention"
)
CROSS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "cross-record"
)
SUPPORT_SCHEMA_PATH = "schemas/v1/support-processes/support.schema.json"
INTERVENTION_SCHEMA_PATH = "schemas/v1/support-processes/intervention.schema.json"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _record_ids(values: list[dict[str, Any]]) -> set[str]:
    return {
        next(
            item[key]
            for key in ("participant_id", "need_id", "goal_id")
            if key in item
        )
        for item in values
        if item["status"] == "active"
    }


def _provider_ids(value: dict[str, Any]) -> list[str]:
    plan = value["provider_plan"]
    if plan["kind"] != "assigned":
        return []
    return [ref["record_id"] for ref in plan["participant_refs"]]


def _ref_ids(value: dict[str, Any], field: str) -> list[str]:
    return [ref["record_id"] for ref in value.get(field, [])]


def _supersession_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    ref = entry["work_record_ref"]
    return (
        ref["work_ref"]["class_id"],
        ref["work_ref"]["work_id"],
        ref["record_ref"]["record_id"],
    )


def plan_application_errors(
    value: dict[str, Any],
    *,
    family: str,
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

    if (
        family == "Intervention"
        and value["status"] == "active"
        and value["plan_state"] == "active"
    ):
        if value["provider_plan"]["kind"] != "assigned":
            errors.append("active Intervention requires assigned provider_plan")
        if value["schedule"]["kind"] == "as_needed":
            errors.append("active Intervention rejects as_needed schedule")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [_supersession_identity(item) for item in supersedes]
        reasons = [item["reason"] for item in supersedes]
        current = (value["class_id"], value["work_id"], value[id_field])

        if len(set(identities)) != len(identities):
            errors.append(f"{family} predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append(f"mixed {family} supersession reasons")
        if current in identities:
            errors.append(f"{family} cannot supersede itself")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        f"duplicate consolidation needs two {family} predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append(f"{family} work-root correction is one-to-one")
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
                            f"work-root correction must preserve {family} ID"
                        )
            elif reason == "plan_adapted":
                if len(set(identities)) != 1:
                    errors.append(f"{family} plan adaptation is one-to-one")
                else:
                    work = supersedes[0]["work_record_ref"]["work_ref"]
                    if (
                        work["class_id"] != value["class_id"]
                        or work["work_id"] != value["work_id"]
                    ):
                        errors.append(
                            "plan adaptation cannot cross Support Process roots"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        f"ordinary {family} correction is one-to-one"
                    )
                else:
                    work = supersedes[0]["work_record_ref"]["work_ref"]
                    if (
                        work["class_id"] != value["class_id"]
                        or work["work_id"] != value["work_id"]
                    ):
                        errors.append(
                            f"ordinary {family} correction cannot cross Support Process roots"
                        )

    return errors


def graph_errors(
    value: dict[str, Any],
    graph: dict[str, Any],
    *,
    family: str,
) -> list[str]:
    errors: list[str] = []

    need_ids = _record_ids(graph["needs"])
    goal_ids = _record_ids(graph["goals"])
    participant_ids = _record_ids(graph["participants"])

    if any(rid not in need_ids for rid in _ref_ids(value, "need_refs")):
        errors.append(
            f"{family} Need ref does not resolve in owning Support Process"
        )
    if any(rid not in goal_ids for rid in _ref_ids(value, "goal_refs")):
        errors.append(
            f"{family} Goal ref does not resolve in owning Support Process"
        )

    provider_ids = _provider_ids(value)
    if any(rid not in participant_ids for rid in provider_ids):
        errors.append(
            f"{family} provider Participant ref does not resolve in owning Support Process"
        )
    elif provider_ids:
        by_id = {
            item["participant_id"]: item
            for item in graph["participants"]
            if item["status"] == "active"
        }
        logical = [by_id[rid]["logical_person_key"] for rid in provider_ids]
        if len(logical) != len(set(logical)):
            errors.append(
                f"{family} provider set repeats a logical participant"
            )

    return errors


class Issue18SupportInterventionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.support_validator = validator_for(
            "support", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.intervention_validator = validator_for(
            "intervention", "1",
            catalog=cls.catalog, store=cls.store,
        )
        cls.support_manifest = load_json(SUPPORT_ROOT / "manifest.json")
        cls.intervention_manifest = load_json(
            INTERVENTION_ROOT / "manifest.json"
        )
        cls.graph = load_json(
            CROSS_ROOT / "support-intervention.json"
        )

    def test_catalog_entries_and_manifest_metadata(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        self.assertEqual(
            self.catalog["contracts"]["support"]["1"],
            {
                "schema_id": base + SUPPORT_SCHEMA_PATH,
                "path": SUPPORT_SCHEMA_PATH,
            },
        )
        self.assertEqual(
            self.catalog["contracts"]["intervention"]["1"],
            {
                "schema_id": base + INTERVENTION_SCHEMA_PATH,
                "path": INTERVENTION_SCHEMA_PATH,
            },
        )
        self.assertEqual(len(self.support_manifest["valid"]), 8)
        self.assertEqual(len(self.support_manifest["invalid"]), 14)
        self.assertEqual(
            len(self.support_manifest["application_invalid"]), 13
        )
        self.assertEqual(len(self.intervention_manifest["valid"]), 8)
        self.assertEqual(len(self.intervention_manifest["invalid"]), 14)
        self.assertEqual(
            len(self.intervention_manifest["application_invalid"]), 15
        )

    def test_support_valid_fixtures_pass(self) -> None:
        for filename in self.support_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(SUPPORT_ROOT / "valid" / filename)
                structural = list(self.support_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    plan_application_errors(
                        value, family="Support", id_field="support_id"
                    ),
                    [],
                )

    def test_support_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.support_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(SUPPORT_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.support_validator.iter_errors(value))
                )

    def test_support_application_invalid_fixtures_fail(self) -> None:
        for item in self.support_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    SUPPORT_ROOT / "application-invalid" / item["file"]
                )
                structural = list(self.support_validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                errors = plan_application_errors(
                    value, family="Support", id_field="support_id"
                )
                errors.extend(
                    graph_errors(value, self.graph, family="Support")
                )
                self.assertIn(item["expected_error"], errors)

    def test_intervention_valid_fixtures_pass(self) -> None:
        for filename in self.intervention_manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(INTERVENTION_ROOT / "valid" / filename)
                structural = list(
                    self.intervention_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    plan_application_errors(
                        value,
                        family="Intervention",
                        id_field="intervention_id",
                    ),
                    [],
                )

    def test_intervention_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.intervention_manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(INTERVENTION_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.intervention_validator.iter_errors(value))
                )

    def test_intervention_application_invalid_fixtures_fail(self) -> None:
        for item in self.intervention_manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    INTERVENTION_ROOT
                    / "application-invalid"
                    / item["file"]
                )
                structural = list(
                    self.intervention_validator.iter_errors(value)
                )
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                errors = plan_application_errors(
                    value,
                    family="Intervention",
                    id_field="intervention_id",
                )
                errors.extend(
                    graph_errors(
                        value, self.graph, family="Intervention"
                    )
                )
                self.assertIn(item["expected_error"], errors)

    def test_valid_plan_links_resolve_in_same_support_process(self) -> None:
        for family, value in (
            ("Support", self.graph["support"]),
            ("Intervention", self.graph["intervention"]),
        ):
            with self.subTest(family=family):
                self.assertEqual(
                    graph_errors(value, self.graph, family=family),
                    [],
                )

    def test_support_allows_as_needed_and_no_assigned_provider(self) -> None:
        value = load_json(
            SUPPORT_ROOT / "valid" / "as-needed-access-no-provider.json"
        )
        self.assertEqual(value["schedule"]["kind"], "as_needed")
        self.assertEqual(
            value["provider_plan"]["kind"], "no_assigned_provider"
        )
        self.assertFalse(list(self.support_validator.iter_errors(value)))

    def test_active_intervention_requires_assignment_and_non_as_needed(self) -> None:
        no_provider = load_json(
            INTERVENTION_ROOT
            / "application-invalid"
            / "active-no-assigned-provider.json"
        )
        as_needed_value = load_json(
            INTERVENTION_ROOT
            / "application-invalid"
            / "active-as-needed.json"
        )
        self.assertIn(
            "active Intervention requires assigned provider_plan",
            plan_application_errors(
                no_provider,
                family="Intervention",
                id_field="intervention_id",
            ),
        )
        self.assertIn(
            "active Intervention rejects as_needed schedule",
            plan_application_errors(
                as_needed_value,
                family="Intervention",
                id_field="intervention_id",
            ),
        )

    def test_proposed_intervention_can_preserve_uncertainty(self) -> None:
        no_provider = load_json(
            INTERVENTION_ROOT / "valid" / "proposed-import-no-provider.json"
        )
        as_needed_value = load_json(
            INTERVENTION_ROOT / "valid" / "proposed-as-needed.json"
        )
        self.assertEqual(no_provider["status"], "proposed")
        self.assertEqual(
            no_provider["provider_plan"]["kind"],
            "no_assigned_provider",
        )
        self.assertEqual(as_needed_value["status"], "proposed")
        self.assertEqual(as_needed_value["schedule"]["kind"], "as_needed")
        self.assertEqual(
            plan_application_errors(
                no_provider,
                family="Intervention",
                id_field="intervention_id",
            ),
            [],
        )
        self.assertEqual(
            plan_application_errors(
                as_needed_value,
                family="Intervention",
                id_field="intervention_id",
            ),
            [],
        )

    def test_strategy_vocabulary_is_shared_and_neutral(self) -> None:
        support = load_json(REPO_ROOT / SUPPORT_SCHEMA_PATH)
        intervention = load_json(REPO_ROOT / INTERVENTION_SCHEMA_PATH)
        self.assertEqual(
            support["$defs"]["strategy"]["properties"]["kind"]["enum"],
            intervention["$defs"]["strategy"]["properties"]["kind"]["enum"],
        )
        text = json.dumps(
            support["$defs"]["strategy"]["properties"]["kind"]["enum"]
        )
        for forbidden in (
            "punishment", "risk", "diagnosis", "severity", "tier"
        ):
            self.assertNotIn(forbidden, text)

    def test_provider_assignment_does_not_encode_authority(self) -> None:
        for path in (SUPPORT_SCHEMA_PATH, INTERVENTION_SCHEMA_PATH):
            with self.subTest(path=path):
                schema = load_json(REPO_ROOT / path)
                provider = json.dumps(schema["$defs"]["providerPlan"]).lower()
                self.assertNotIn("authorized", provider)
                self.assertNotIn("licensed", provider)
                self.assertNotIn("employment", provider)
                self.assertNotIn("guardian", provider)

    def test_plan_state_is_distinct_from_lifecycle_and_outcome(self) -> None:
        for path in (SUPPORT_SCHEMA_PATH, INTERVENTION_SCHEMA_PATH):
            with self.subTest(path=path):
                schema = load_json(REPO_ROOT / path)
                properties = schema["properties"]
                self.assertEqual(
                    set(properties["status"]["enum"]),
                    {"proposed", "active", "invalidated", "superseded"},
                )
                self.assertEqual(
                    set(properties["plan_state"]["enum"]),
                    {"planned", "active", "paused", "completed", "discontinued"},
                )
                for forbidden in (
                    "effective", "successful", "goal_attained", "outcome"
                ):
                    self.assertNotIn(forbidden, properties)

    def test_plan_contracts_do_not_claim_implementation_or_outcome(self) -> None:
        for path in (SUPPORT_SCHEMA_PATH, INTERVENTION_SCHEMA_PATH):
            with self.subTest(path=path):
                schema = load_json(REPO_ROOT / path)
                properties = schema["properties"]
                for forbidden in (
                    "implementation_count",
                    "implemented_count",
                    "actual_frequency",
                    "actual_duration",
                    "progress",
                    "effectiveness",
                    "outcome",
                    "fidelity",
                    "adaptation",
                    "amendments",
                ):
                    self.assertNotIn(forbidden, properties)
                text = json.dumps(schema)
                self.assertIn("amendment_prohibited_v1", text)
                self.assertIn("no_implementation_claim", text)
                self.assertIn("no_outcome_or_effectiveness", text)


if __name__ == "__main__":
    unittest.main()
