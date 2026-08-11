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

ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "implementation"
)
CROSS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "cross-record"
)
SCHEMA_PATH = "schemas/v1/support-processes/implementation.schema.json"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _target_key(target: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    kind = target["kind"]
    if kind == "support_process":
        return (kind, ())
    if kind == "support_process_participant":
        return (kind, (target["record_ref"]["record_id"],))
    return (
        kind,
        tuple(sorted(
            item["record_ref"]["record_id"]
            for item in target["targets"]
        )),
    )


def _provider_key(provider: dict[str, Any]) -> tuple[str, tuple[str, ...] | str]:
    if provider["kind"] == "no_human_provider":
        return ("no_human_provider", provider["reason"])
    return (
        "participants",
        tuple(sorted(
            ref["record_id"] for ref in provider["participant_refs"]
        )),
    )


def _plan_provider_key(provider_plan: dict[str, Any]) -> tuple[str, tuple[str, ...] | str]:
    if provider_plan["kind"] == "no_assigned_provider":
        reason_map = {
            "access_condition": "environmental_condition",
            "self_directed": "self_directed",
            "resource_availability": "resource_access",
            "other": "other",
        }
        return (
            "no_human_provider",
            reason_map[provider_plan["reason"]],
        )
    return (
        "participants",
        tuple(sorted(
            ref["record_id"] for ref in provider_plan["participant_refs"]
        )),
    )


def _supersession_identity(entry: dict[str, Any]) -> tuple[str, str, str]:
    ref = entry["work_record_ref"]
    return (
        ref["work_ref"]["class_id"],
        ref["work_ref"]["work_id"],
        ref["record_ref"]["record_id"],
    )


def application_errors(value: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    started = _dt(value["started_at"])
    ended_raw = value.get("ended_at")
    if ended_raw is not None and _dt(ended_raw) < started:
        errors.append("ended_at precedes started_at")

    created = _dt(value["created_at"])
    if created < started:
        errors.append("created_at precedes started_at")
    if _dt(value["updated_at"]) < created:
        errors.append("updated_at precedes created_at")

    creation = value["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and value["status"] != "proposed"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    if (
        value["execution_state"] == "unknown"
        and creation["type"] != "import"
    ):
        errors.append("unknown execution_state is import-only")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [_supersession_identity(item) for item in supersedes]
        reasons = [item["reason"] for item in supersedes]
        current = (
            value["class_id"],
            value["work_id"],
            value["implementation_id"],
        )

        if len(set(identities)) != len(identities):
            errors.append("Implementation predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed Implementation supersession reasons")
        if current in identities:
            errors.append("Implementation cannot supersede itself")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two Implementation predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append(
                        "Implementation work-root correction is one-to-one"
                    )
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
                    if record["record_id"] != value["implementation_id"]:
                        errors.append(
                            "work-root correction must preserve Implementation ID"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        "ordinary Implementation correction is one-to-one"
                    )
                else:
                    work = supersedes[0]["work_record_ref"]["work_ref"]
                    if (
                        work["class_id"] != value["class_id"]
                        or work["work_id"] != value["work_id"]
                    ):
                        errors.append(
                            "ordinary Implementation correction cannot cross Support Process roots"
                        )

    return errors


def graph_errors(
    value: dict[str, Any],
    graph: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    plan_ref = value["plan_ref"]
    plan = next(
        (
            item
            for item in graph["plans"]
            if item["record_kind"] == plan_ref["record_kind"]
            and item["record_id"] == plan_ref["record_id"]
            and item["contract_version"] == plan_ref["contract_version"]
        ),
        None,
    )
    if plan is None:
        errors.append(
            "Implementation plan ref does not resolve in owning Support Process"
        )
        return errors

    active_participants = {
        item["participant_id"]: item
        for item in graph["participants"]
        if item["status"] == "active"
    }

    target_ids: list[str] = []
    target = value["actual_target"]
    if target["kind"] == "support_process_participant":
        target_ids = [target["record_ref"]["record_id"]]
    elif target["kind"] == "support_process_participants":
        target_ids = [
            item["record_ref"]["record_id"]
            for item in target["targets"]
        ]

    if any(pid not in active_participants for pid in target_ids):
        errors.append(
            "Implementation actual target does not resolve in owning Support Process"
        )

    provider = value["implementation_provider"]
    provider_ids: list[str] = []
    if provider["kind"] == "participants":
        provider_ids = [
            ref["record_id"]
            for ref in provider["participant_refs"]
        ]
        if any(pid not in active_participants for pid in provider_ids):
            errors.append(
                "Implementation provider Participant ref does not resolve in owning Support Process"
            )
        else:
            logical = [
                active_participants[pid]["logical_person_key"]
                for pid in provider_ids
            ]
            if len(logical) != len(set(logical)):
                errors.append(
                    "Implementation provider set repeats a logical participant"
                )

    kinds = set(value.get("variation", {}).get("kinds", []))
    if _provider_key(provider) != _plan_provider_key(plan["provider_plan"]):
        if "provider" not in kinds:
            errors.append(
                "provider variation is required when actual provider differs from plan"
            )

    if _target_key(value["actual_target"]) != _target_key(plan["target"]):
        if "target" not in kinds:
            errors.append(
                "target variation is required when actual target differs from plan"
            )

    return errors


def execution_transition_allowed(before: str, after: str) -> bool:
    if before == after:
        return True
    return (
        before == "in_progress"
        and after in {
            "completed",
            "partially_completed",
            "unable_to_complete",
        }
    )


class Issue18ImplementationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "implementation", "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(ROOT / "manifest.json")
        cls.graph = load_json(
            CROSS_ROOT / "implementation-plan.json"
        )

    def test_catalog_entry_and_manifest_metadata(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        self.assertEqual(
            self.catalog["contracts"]["implementation"]["1"],
            {
                "schema_id": base + SCHEMA_PATH,
                "path": SCHEMA_PATH,
            },
        )
        self.assertEqual(self.manifest["contract"], "implementation")
        self.assertEqual(len(self.manifest["valid"]), 10)
        self.assertEqual(len(self.manifest["invalid"]), 17)
        self.assertEqual(len(self.manifest["application_invalid"]), 22)

    def test_valid_fixtures_pass(self) -> None:
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(ROOT / "valid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(application_errors(value), [])

    def test_structural_invalid_fixtures_fail(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(ROOT / "invalid" / filename)
                self.assertTrue(list(self.validator.iter_errors(value)))

    def test_application_invalid_fixtures_fail(self) -> None:
        for item in self.manifest["application_invalid"]:
            with self.subTest(filename=item["file"]):
                value = load_json(
                    ROOT / "application-invalid" / item["file"]
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                errors = application_errors(value)
                errors.extend(graph_errors(value, self.graph))
                self.assertIn(item["expected_error"], errors)

    def test_plan_ref_is_closed_exact_support_or_intervention_union(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        refs = {
            item["$ref"]
            for item in schema["properties"]["plan_ref"]["oneOf"]
        }
        self.assertEqual(
            refs,
            {
                "#/$defs/exactSupportRef",
                "#/$defs/exactInterventionRef",
            },
        )
        for name, expected_kind in (
            ("exactSupportRef", "support"),
            ("exactInterventionRef", "intervention"),
        ):
            text = json.dumps(schema["$defs"][name])
            self.assertIn(
                f'"record_kind": {{"const": "{expected_kind}"}}',
                text,
            )
            self.assertIn('"contract_version": {"const": "1"}', text)

    def test_valid_support_and_intervention_plan_refs_resolve(self) -> None:
        intervention = load_json(
            ROOT / "valid" / "completed-intervention-occurrence.json"
        )
        support = load_json(
            ROOT / "valid" / "support-environmental-no-human-provider.json"
        )
        self.assertEqual(graph_errors(intervention, self.graph), [])
        self.assertEqual(graph_errors(support, self.graph), [])

    def test_provider_and_target_variations_are_explicit(self) -> None:
        for filename in (
            "provider-variation-recorded.json",
            "target-variation-recorded.json",
            "multi-kind-variation.json",
        ):
            with self.subTest(filename=filename):
                value = load_json(ROOT / "valid" / filename)
                self.assertEqual(graph_errors(value, self.graph), [])

    def test_missing_provider_or_target_variation_is_rejected(self) -> None:
        for filename, expected in (
            (
                "provider-diff-without-variation.json",
                "provider variation is required when actual provider differs from plan",
            ),
            (
                "target-diff-without-variation.json",
                "target variation is required when actual target differs from plan",
            ),
        ):
            with self.subTest(filename=filename):
                value = load_json(
                    ROOT / "application-invalid" / filename
                )
                self.assertIn(
                    expected,
                    graph_errors(value, self.graph),
                )

    def test_unknown_execution_is_import_only(self) -> None:
        valid = load_json(
            ROOT / "valid" / "proposed-import-unknown.json"
        )
        self.assertEqual(application_errors(valid), [])
        invalid = load_json(
            ROOT / "application-invalid" / "unknown-digital.json"
        )
        self.assertIn(
            "unknown execution_state is import-only",
            application_errors(invalid),
        )

    def test_execution_transition_matrix(self) -> None:
        for after in (
            "completed",
            "partially_completed",
            "unable_to_complete",
        ):
            self.assertTrue(
                execution_transition_allowed("in_progress", after)
            )

        for before, after in (
            ("attempted", "completed"),
            ("completed", "in_progress"),
            ("partially_completed", "completed"),
            ("unable_to_complete", "completed"),
            ("unknown", "completed"),
        ):
            with self.subTest(before=before, after=after):
                self.assertFalse(
                    execution_transition_allowed(before, after)
                )

    def test_variation_is_descriptive_not_fidelity(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        variation = schema["$defs"]["variation"]
        kinds = variation["properties"]["kinds"]["items"]["enum"]
        self.assertEqual(
            set(kinds),
            {
                "provider",
                "target",
                "timing_or_duration",
                "procedure",
                "context",
                "other",
            },
        )
        text = json.dumps(variation).lower()
        for forbidden in (
            "fidelity",
            "effective",
            "appropriate",
            "authorized",
            "compliance",
        ):
            self.assertNotIn(forbidden, text)

    def test_execution_state_excludes_success_and_compliance_judgments(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        states = schema["properties"]["execution_state"]["enum"]
        self.assertEqual(
            set(states),
            {
                "attempted",
                "in_progress",
                "completed",
                "partially_completed",
                "unable_to_complete",
                "unknown",
            },
        )
        for forbidden in (
            "successful",
            "effective",
            "compliant",
            "noncompliant",
            "resolved",
        ):
            self.assertNotIn(forbidden, states)

    def test_contract_excludes_fidelity_effectiveness_outcome_and_counters(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        properties = schema["properties"]
        for forbidden in (
            "fidelity",
            "effectiveness",
            "outcome",
            "successful",
            "compliant",
            "resolved",
            "implementation_count",
            "occurrence_count",
            "scheduled_occurrence",
        ):
            self.assertNotIn(forbidden, properties)

    def test_preallocated_paper_cannot_create_implementation(self) -> None:
        value = load_json(
            ROOT / "invalid" / "preallocated-paper.json"
        )
        self.assertTrue(list(self.validator.iter_errors(value)))

    def test_successor_reason_vocabulary_matches_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        reasons = schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]
        self.assertEqual(
            reasons,
            [
                "provider_corrected",
                "target_corrected",
                "timing_corrected",
                "execution_state_corrected",
                "variation_corrected",
                "summary_corrected",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            ],
        )

    def test_no_v1_amendment_paths_and_exact_refs_do_not_follow_successors(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        text = json.dumps(schema)
        self.assertIn("amendment_prohibited_v1", text)
        self.assertIn("no_silent_successor_following", text)
        self.assertNotIn('"amendments"', text)
        self.assertNotIn('"amendment_paths"', text)


if __name__ == "__main__":
    unittest.main()
