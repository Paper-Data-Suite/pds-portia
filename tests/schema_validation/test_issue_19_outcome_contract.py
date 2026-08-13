from __future__ import annotations

from datetime import datetime
from typing import Any
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
    REPO_ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-19"
    / "outcome"
)
SCHEMA_PATH = "schemas/v1/outcomes/outcome.schema.json"

EVENT_EVALUATOR_ELIGIBLE_KINDS = {"local_operator", "actor"}
SUPPORT_EVALUATOR_CONTEXTS = {
    "provider_or_collaborator",
    "coordinator",
    "observer",
}


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _work_identity(value: dict[str, Any]) -> tuple[str, str, str]:
    return value["class_id"], value["work_kind"], value["work_id"]


def _ref_work_identity(ref: dict[str, Any]) -> tuple[str, str, str]:
    work = ref["work_ref"]
    return work["class_id"], work["work_kind"], work["work_id"]


def _ref_identity(ref: dict[str, Any]) -> tuple[str, str, str, str, str]:
    work = ref["work_ref"]
    record = ref["record_ref"]
    return (
        work["class_id"],
        work["work_kind"],
        work["work_id"],
        record["record_id"],
        record["contract_version"],
    )


def outcome_application_errors(
    value: dict[str, Any],
    *,
    resolved_support_participants: dict[str, dict[str, Any]] | None = None,
    resolved_local_records: dict[tuple[str, str], dict[str, Any]] | None = None,
    operational_actor_ids: set[str] | None = None,
) -> list[str]:
    errors: list[str] = []

    if _dt(value["updated_at"]) < _dt(value["created_at"]):
        errors.append("updated_at precedes created_at")

    timeframe = value["timeframe"]
    if (
        timeframe["precision"] == "range"
        and _dt(timeframe["ended_at"]) < _dt(timeframe["started_at"])
    ):
        errors.append("Outcome timeframe range is reversed")

    if value["status"] == "active" and timeframe["precision"] == "unknown":
        errors.append("active Outcome timeframe may not be unknown")

    creation = value["creation_source"]
    if (
        creation["type"] in {"paper_capture", "import"}
        and value["status"] == "active"
    ):
        errors.append(
            "paper/import activation requires accepted review history"
        )

    evaluator = value["evaluator"]
    if value["work_kind"] == "event" and value["status"] == "active":
        person = evaluator["person"]
        kind = person["kind"]
        if kind not in EVENT_EVALUATOR_ELIGIBLE_KINDS:
            errors.append("Event Outcome evaluator is not operational")
        elif kind == "actor" and operational_actor_ids is not None:
            actor_id = person["actor_ref"]["actor_id"]
            if actor_id not in operational_actor_ids:
                errors.append("Actor evaluator is not operationally eligible")

    if (
        value["work_kind"] == "support_process"
        and value["status"] == "active"
        and resolved_support_participants is not None
    ):
        participant_id = evaluator["participant_ref"]["record_id"]
        participant = resolved_support_participants.get(participant_id)
        if participant is None:
            errors.append("Support Process evaluator does not resolve")
        else:
            if participant.get("status") != "active":
                errors.append("Support Process evaluator is not active")
            if participant.get("class_id") != value["class_id"]:
                errors.append("Support Process evaluator class mismatch")
            if participant.get("work_id") != value["work_id"]:
                errors.append("Support Process evaluator work mismatch")
            contexts = {
                item["kind"] for item in participant.get("contexts", [])
            }
            if not (contexts & SUPPORT_EVALUATOR_CONTEXTS):
                errors.append(
                    "Support Process evaluator lacks evaluator context"
                )

    basis_seen: set[tuple[Any, ...]] = set()
    for item in value["basis"]:
        locator = item["locator"]
        if locator["kind"] == "portia_record":
            ref = locator["record_ref"]
            record = ref["record_ref"]
            identity = (
                "portia",
                *_ref_identity(ref),
                item["role"],
            )
            if (
                record["record_kind"] == "outcome"
                and record["record_id"] == value["outcome_id"]
                and _ref_work_identity(ref) == _work_identity(value)
            ):
                errors.append("Outcome basis self-reference")

            if (
                item["role"] == "student_or_family_perspective"
                and record["record_kind"] != "account"
            ):
                errors.append(
                    "student/family perspective basis must be Account"
                )
            if (
                item["role"] == "implementation_context"
                and record["record_kind"] != "implementation"
            ):
                errors.append(
                    "implementation_context basis must be Implementation"
                )
            if (
                item["role"] == "fidelity_context"
                and record["record_kind"] != "fidelity"
            ):
                errors.append("fidelity_context basis must be Fidelity")
        else:
            module_ref = locator["module_work_record_ref"]
            work_ref = module_ref["work_ref"]
            record_ref = module_ref["record_ref"]
            identity = (
                "module",
                work_ref["module_id"],
                work_ref["class_id"],
                work_ref["work_id"],
                record_ref["module_id"],
                record_ref["record_kind"],
                record_ref["record_id"],
                record_ref["contract_version"],
                item["role"],
            )
            if work_ref["module_id"] != record_ref["module_id"]:
                errors.append("module basis module_id mismatch")

        if identity in basis_seen:
            errors.append("Outcome basis identity/role repeated")
        basis_seen.add(identity)

    scope = value["scope"]
    if resolved_local_records is not None:
        keys: list[tuple[str, str]] = []
        if scope["kind"] == "goal_status":
            keys.append(
                (scope["goal_ref"]["record_kind"], scope["goal_ref"]["record_id"])
            )
        elif scope["kind"] == "support_response_review":
            keys.extend(
                (ref["record_kind"], ref["record_id"])
                for ref in scope["plan_refs"]
            )
        elif scope["kind"] == "reentry_status":
            keys.append(
                (scope["reentry_ref"]["record_kind"], scope["reentry_ref"]["record_id"])
            )
        elif scope["kind"] == "repair_status":
            keys.append(
                (scope["repair_ref"]["record_kind"], scope["repair_ref"]["record_id"])
            )

        for key in keys:
            resolved = resolved_local_records.get(key)
            if resolved is None:
                errors.append(f"scope reference does not resolve: {key}")
                continue
            if resolved.get("class_id") != value["class_id"]:
                errors.append("scope reference class mismatch")
            if resolved.get("work_id") != value["work_id"]:
                errors.append("scope reference work mismatch")

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [
            _ref_identity(item["work_record_ref"])
            for item in supersedes
        ]
        reasons = [item["reason"] for item in supersedes]
        if len(identities) != len(set(identities)):
            errors.append("predecessor Outcome identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed supersession reasons")

        current_work = _work_identity(value)
        for item in supersedes:
            ref = item["work_record_ref"]
            predecessor_work = _ref_work_identity(ref)
            predecessor_id = ref["record_ref"]["record_id"]
            reason = item["reason"]
            same_work = predecessor_work == current_work
            same_id = predecessor_id == value["outcome_id"]

            if same_work and same_id:
                errors.append("Outcome replacement self-reference")

            if reason == "work_root_corrected":
                if same_work:
                    errors.append(
                        "work-root correction requires different work"
                    )
                if not same_id:
                    errors.append(
                        "work-root correction must preserve Outcome ID"
                    )
            elif reason != "contract_migrated" and not same_work:
                errors.append(
                    "ordinary Outcome correction cannot cross work roots"
                )

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two predecessors"
                    )
            elif len(set(identities)) != 1:
                errors.append(
                    "non-consolidation correction is one-to-one"
                )

    return errors


def _valid_support_evaluator_resolution() -> dict[str, dict[str, Any]]:
    return {
        "spp_evaluator": {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "participant_id": "spp_evaluator",
            "status": "active",
            "contexts": [{"kind": "observer"}],
        }
    }


def _bad_support_evaluator_resolution() -> dict[str, dict[str, Any]]:
    return {
        "spp_evaluator": {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": "eng10_p2_2026",
            "work_id": "sup_alpha",
            "participant_id": "spp_evaluator",
            "status": "active",
            "contexts": [{"kind": "family_or_support_person"}],
        }
    }


def _resolution_for(value: dict[str, Any], *, force_wrong: bool = False) -> dict[tuple[str, str], dict[str, Any]]:
    work_id = "sup_other" if force_wrong else value["work_id"]
    class_id = value["class_id"]
    scope = value["scope"]
    resolved: dict[tuple[str, str], dict[str, Any]] = {}
    if scope["kind"] == "goal_status":
        ref = scope["goal_ref"]
        resolved[(ref["record_kind"], ref["record_id"])] = {
            "class_id": class_id,
            "work_id": work_id,
        }
    elif scope["kind"] == "support_response_review":
        for ref in scope["plan_refs"]:
            resolved[(ref["record_kind"], ref["record_id"])] = {
                "class_id": class_id,
                "work_id": work_id,
            }
    elif scope["kind"] == "reentry_status":
        ref = scope["reentry_ref"]
        resolved[(ref["record_kind"], ref["record_id"])] = {
            "class_id": class_id,
            "work_id": work_id,
        }
    elif scope["kind"] == "repair_status":
        ref = scope["repair_ref"]
        resolved[(ref["record_kind"], ref["record_id"])] = {
            "class_id": class_id,
            "work_id": work_id,
        }
    return resolved


class Issue19OutcomeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "outcome",
            "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(FIXTURE_ROOT / "manifest.json")

    def test_manifest_and_catalog(self) -> None:
        self.assertEqual(self.manifest["manifest_version"], "1")
        self.assertEqual(self.manifest["issue"], 19)
        self.assertEqual(self.manifest["contract"], "outcome")
        self.assertEqual(self.manifest["version"], "1")
        expected = {
            "schema_id": (
                "https://paper-data-suite.github.io/pds-portia/"
                + SCHEMA_PATH
            ),
            "path": SCHEMA_PATH,
        }
        self.assertEqual(
            self.catalog["contracts"]["outcome"]["1"],
            expected,
        )

    def test_valid_fixtures_pass(self) -> None:
        support_resolution = _valid_support_evaluator_resolution()
        for filename in self.manifest["valid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "valid" / filename)
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                self.assertEqual(
                    outcome_application_errors(
                        value,
                        resolved_support_participants=support_resolution,
                        resolved_local_records=_resolution_for(value),
                    ),
                    [],
                )

    def test_invalid_fixtures_fail_structurally(self) -> None:
        for filename in self.manifest["invalid"]:
            with self.subTest(filename=filename):
                value = load_json(FIXTURE_ROOT / "invalid" / filename)
                self.assertTrue(
                    list(self.validator.iter_errors(value)),
                    f"{filename} unexpectedly passed structural validation",
                )

    def test_application_invalid_fixtures_are_structurally_valid(self) -> None:
        good_support = _valid_support_evaluator_resolution()
        bad_support = _bad_support_evaluator_resolution()
        wrong_scope_files = {
            "goal-ref-other-support-process.json",
            "plan-ref-other-support-process.json",
        }
        for filename in self.manifest["application_invalid"]:
            with self.subTest(filename=filename):
                value = load_json(
                    FIXTURE_ROOT / "application-invalid" / filename
                )
                structural = list(self.validator.iter_errors(value))
                self.assertFalse(
                    structural,
                    "\n".join(error.message for error in structural),
                )
                support_resolution = (
                    bad_support
                    if filename
                    == "support-evaluator-without-evaluator-context.json"
                    else good_support
                )
                resolved = _resolution_for(
                    value,
                    force_wrong=filename in wrong_scope_files,
                )
                self.assertTrue(
                    outcome_application_errors(
                        value,
                        resolved_support_participants=support_resolution,
                        resolved_local_records=resolved,
                    )
                )

    def test_scope_vocabulary_is_closed(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        refs = schema["$defs"]["scope"]["oneOf"]
        self.assertEqual(len(refs), 8)
        expected = {
            "goal_status",
            "observed_change",
            "recurrence_review",
            "support_response_review",
            "unintended_or_adverse_effect_review",
            "reentry_status",
            "repair_status",
            "other",
        }
        found = set()
        for ref in refs:
            name = ref["$ref"].split("/")[-1]
            found.add(schema["$defs"][name]["properties"]["kind"]["const"])
        self.assertEqual(found, expected)

    def test_scope_specific_result_vocabularies_are_exact(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        mapping = {}
        for rule in schema["allOf"]:
            if_rule = rule.get("if", {})
            try:
                kind = (
                    if_rule["properties"]["scope"]["properties"]["kind"]["const"]
                )
                result_enum = rule["then"]["properties"]["result"]["enum"]
            except (KeyError, TypeError):
                continue
            mapping[kind] = set(result_enum)
        self.assertEqual(
            mapping["recurrence_review"],
            {
                "recurrence_observed",
                "no_recurrence_observed_within_defined_coverage",
                "unable_to_determine",
                "not_applicable",
            },
        )
        self.assertEqual(
            mapping["support_response_review"],
            {
                "progress_observed",
                "no_clear_progress",
                "mixed",
                "worsening_observed",
                "unable_to_determine",
                "not_applicable",
            },
        )

    def test_timeframe_reuses_evidence_time(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            schema["properties"]["timeframe"]["$ref"],
            "https://paper-data-suite.github.io/pds-portia/"
            "schemas/v1/common/evidence-time.schema.json",
        )

    def test_unable_to_determine_requires_limitation(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        matching = [
            rule
            for rule in schema["allOf"]
            if rule.get("if", {}).get("properties", {}).get("result", {}).get("const")
            == "unable_to_determine"
        ]
        self.assertEqual(len(matching), 1)
        self.assertIn("limitations", matching[0]["then"]["required"])

    def test_basis_roles_are_closed_and_weightless(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        basis_entry = schema["$defs"]["basisEntry"]
        self.assertEqual(
            set(basis_entry["properties"]["role"]["enum"]),
            {
                "baseline",
                "current_period",
                "supporting",
                "contrary",
                "contextual",
                "student_or_family_perspective",
                "implementation_context",
                "fidelity_context",
            },
        )
        for forbidden in ("weight", "credibility", "truth", "causal_weight"):
            self.assertNotIn(forbidden, basis_entry["properties"])

    def test_basis_locator_preserves_exact_native_and_module_context(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        locator = schema["$defs"]["basisLocator"]["oneOf"]
        self.assertEqual(len(locator), 2)
        native = schema["$defs"]["portiaBasisLocator"]["properties"]["record_ref"]
        self.assertTrue(
            native["$ref"].endswith(
                "/references/exact-portia-work-record-ref.schema.json"
            )
        )
        module = schema["$defs"]["moduleBasisLocator"]
        serialized = str(module)
        self.assertIn("module-work-record-ref.schema.json", serialized)
        self.assertIn("contract_version", serialized)

    def test_recurrence_scope_requires_explicit_coverage(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        recurrence = schema["$defs"]["recurrenceReviewScope"]
        self.assertIn("coverage", recurrence["required"])
        coverage = schema["$defs"]["coverage"]
        self.assertEqual(
            set(coverage["properties"]["coverage_kind"]["enum"]),
            {
                "direct_observation",
                "event_record_review",
                "combined",
                "other",
            },
        )

    def test_goal_and_support_response_are_support_process_owned(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        found = False
        for rule in schema["allOf"]:
            try:
                kinds = set(
                    rule["if"]["properties"]["scope"]["properties"]["kind"]["enum"]
                )
                owner = rule["then"]["properties"]["work_kind"]["const"]
            except (KeyError, TypeError):
                continue
            if kinds == {"goal_status", "support_response_review"}:
                self.assertEqual(owner, "support_process")
                found = True
        self.assertTrue(found)

    def test_lifecycle_is_separate_from_result(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        self.assertEqual(
            set(schema["properties"]["status"]["enum"]),
            {"proposed", "active", "invalidated", "superseded"},
        )
        self.assertNotIn("completed", schema["properties"]["status"]["enum"])
        self.assertNotIn("resolved", schema["properties"]["status"]["enum"])

    def test_successor_reason_vocabulary_matches_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        reasons = set(
            schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]
        )
        self.assertEqual(
            reasons,
            {
                "evaluator_corrected",
                "scope_corrected",
                "target_corrected",
                "timeframe_corrected",
                "basis_corrected",
                "result_corrected",
                "limitation_corrected",
                "summary_corrected",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            },
        )

    def test_outcome_has_no_causal_effectiveness_grade_or_risk_fields(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        forbidden = {
            "caused_by",
            "causal_effect",
            "treatment_effect",
            "percent_effective",
            "effectiveness",
            "intervention_caused_improvement",
            "response_prevented_recurrence",
            "grade",
            "proficiency",
            "risk_score",
            "compliance",
            "remorse",
            "forgiveness",
        }
        self.assertTrue(forbidden.isdisjoint(schema["properties"]))

    def test_raw_measurement_and_account_payload_do_not_live_in_outcome(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        for forbidden in (
            "measurement",
            "numerator",
            "denominator",
            "duration_seconds",
            "account_content",
            "statement_text",
            "observation_value",
        ):
            self.assertNotIn(forbidden, schema["properties"])

    def test_current_use_evaluator_restriction_is_application_level(self) -> None:
        roster = load_json(
            FIXTURE_ROOT
            / "application-invalid"
            / "active-event-roster-student-evaluator.json"
        )
        self.assertFalse(list(self.validator.iter_errors(roster)))
        self.assertIn(
            "Event Outcome evaluator is not operational",
            outcome_application_errors(roster),
        )


if __name__ == "__main__":
    unittest.main()
