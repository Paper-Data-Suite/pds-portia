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
    / "issue-18" / "fidelity"
)
CROSS_ROOT = (
    REPO_ROOT / "tests" / "schema_validation" / "fixtures"
    / "issue-18" / "cross-record"
)
SCHEMA_PATH = "schemas/v1/support-processes/fidelity.schema.json"


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _ref_key(ref: dict[str, Any]) -> tuple[str, str, str]:
    return (
        ref["record_kind"],
        ref["record_id"],
        ref["contract_version"],
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

    evaluated = _dt(value["evaluated_at"])
    created = _dt(value["created_at"])
    if created < evaluated:
        errors.append("created_at precedes evaluated_at")
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

    scope = value["scope"]
    if scope["kind"] == "bounded_plan_interval":
        if _dt(scope["ended_at"]) < _dt(scope["started_at"]):
            errors.append(
                "Fidelity bounded interval ended_at precedes started_at"
            )

    instrument = value.get("instrument_result")
    if instrument is not None:
        minimum = instrument["scale_minimum"]
        maximum = instrument["scale_maximum"]
        score = instrument["value"]
        if minimum >= maximum:
            errors.append(
                "instrument scale_minimum must be less than scale_maximum"
            )
        elif score < minimum or score > maximum:
            errors.append(
                "instrument value must fall within declared scale"
            )

    supersedes = value.get("supersedes", [])
    if supersedes:
        identities = [_supersession_identity(item) for item in supersedes]
        reasons = [item["reason"] for item in supersedes]
        current = (
            value["class_id"],
            value["work_id"],
            value["fidelity_id"],
        )

        if len(set(identities)) != len(identities):
            errors.append("Fidelity predecessor identity repeated")
        if len(set(reasons)) != 1:
            errors.append("mixed Fidelity supersession reasons")
        if current in identities:
            errors.append("Fidelity cannot supersede itself")

        if len(set(reasons)) == 1:
            reason = reasons[0]
            if reason == "duplicate_consolidated":
                if len(set(identities)) < 2:
                    errors.append(
                        "duplicate consolidation needs two Fidelity predecessors"
                    )
            elif reason == "work_root_corrected":
                if len(set(identities)) != 1:
                    errors.append(
                        "Fidelity work-root correction is one-to-one"
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
                    if record["record_id"] != value["fidelity_id"]:
                        errors.append(
                            "work-root correction must preserve Fidelity ID"
                        )
            elif reason != "contract_migrated":
                if len(set(identities)) != 1:
                    errors.append(
                        "ordinary Fidelity correction is one-to-one"
                    )
                else:
                    work = supersedes[0]["work_record_ref"]["work_ref"]
                    if (
                        work["class_id"] != value["class_id"]
                        or work["work_id"] != value["work_id"]
                    ):
                        errors.append(
                            "ordinary Fidelity correction cannot cross Support Process roots"
                        )

    return errors


def graph_errors(
    value: dict[str, Any],
    graph: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    plan_ref = value["plan_ref"]
    plan_key = _ref_key(plan_ref)
    plan = next(
        (
            item for item in graph["plans"]
            if (
                item["record_kind"],
                item["record_id"],
                item["contract_version"],
            ) == plan_key
            and item["status"] == "active"
        ),
        None,
    )
    if plan is None:
        errors.append(
            "Fidelity plan ref does not resolve in owning Support Process"
        )

    evaluator_id = value["evaluator_ref"]["record_id"]
    evaluator_ok = any(
        item["participant_id"] == evaluator_id
        and item["status"] == "active"
        for item in graph["participants"]
    )
    if not evaluator_ok:
        errors.append(
            "Fidelity evaluator Participant ref does not resolve in owning Support Process"
        )

    implementations = {
        item["implementation_id"]: item
        for item in graph["implementations"]
        if item["status"] == "active"
    }

    scope = value["scope"]
    refs: list[dict[str, Any]] = []
    if scope["kind"] == "one_implementation":
        refs = [scope["implementation_ref"]]
    elif scope["kind"] == "implementation_set":
        refs = scope["implementation_refs"]

    for ref in refs:
        rid = ref["record_id"]
        implementation = implementations.get(rid)
        if implementation is None:
            errors.append(
                "Fidelity scope Implementation ref does not resolve in owning Support Process"
            )
            continue
        if _ref_key(implementation["plan_ref"]) != plan_key:
            errors.append(
                "Fidelity scope Implementation must reference the same exact plan"
            )

    known_basis = {
        _ref_key(ref) for ref in graph["basis_records"]
    }
    for ref in value["basis"].get("record_refs", []):
        if _ref_key(ref) not in known_basis:
            errors.append(
                "Fidelity basis record ref does not resolve in owning Support Process"
            )

    return errors


class Issue18FidelityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog, cls.store = load_validated_catalog_and_store()
        cls.validator = validator_for(
            "fidelity", "1",
            catalog=cls.catalog,
            store=cls.store,
        )
        cls.manifest = load_json(ROOT / "manifest.json")
        cls.graph = load_json(CROSS_ROOT / "fidelity-scope.json")

    def test_catalog_entry_and_manifest_metadata(self) -> None:
        base = "https://paper-data-suite.github.io/pds-portia/"
        self.assertEqual(
            self.catalog["contracts"]["fidelity"]["1"],
            {
                "schema_id": base + SCHEMA_PATH,
                "path": SCHEMA_PATH,
            },
        )
        self.assertEqual(self.manifest["contract"], "fidelity")
        self.assertEqual(len(self.manifest["valid"]), 9)
        self.assertEqual(len(self.manifest["invalid"]), 21)
        self.assertEqual(
            len(self.manifest["application_invalid"]), 21
        )

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

    def test_plan_ref_is_exact_support_or_intervention(self) -> None:
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

    def test_evaluator_is_exact_support_process_participant(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        text = json.dumps(schema["$defs"]["exactParticipantRef"])
        self.assertIn(
            '"record_kind": {"const": "support_process_participant"}',
            text,
        )
        self.assertIn('"contract_version": {"const": "1"}', text)

    def test_scope_is_closed_three_branch_union(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        refs = {
            item["$ref"]
            for item in schema["properties"]["scope"]["oneOf"]
        }
        self.assertEqual(
            refs,
            {
                "#/$defs/oneImplementationScope",
                "#/$defs/implementationSetScope",
                "#/$defs/boundedPlanIntervalScope",
            },
        )

    def test_implementation_scopes_require_same_exact_plan(self) -> None:
        valid = load_json(
            ROOT / "valid" / "implementation-set-record-basis.json"
        )
        self.assertEqual(graph_errors(valid, self.graph), [])

        invalid = load_json(
            ROOT / "application-invalid" / "implementation-set-mixed-plans.json"
        )
        self.assertIn(
            "Fidelity scope Implementation must reference the same exact plan",
            graph_errors(invalid, self.graph),
        )

    def test_result_vocabulary_is_categorical_not_effectiveness(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        results = schema["properties"]["result"]["enum"]
        self.assertEqual(
            results,
            [
                "as_planned",
                "partially_as_planned",
                "not_as_planned",
                "unable_to_determine",
                "not_applicable",
            ],
        )
        for forbidden in (
            "effective",
            "ineffective",
            "successful",
            "compliant",
            "noncompliant",
        ):
            self.assertNotIn(forbidden, results)

    def test_basis_vocabulary_matches_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        kinds = schema["$defs"]["basis"]["properties"]["kind"]["enum"]
        self.assertEqual(
            kinds,
            [
                "direct_observation",
                "implementation_records",
                "checklist_or_instrument",
                "record_review",
                "combined",
                "other",
            ],
        )

    def test_scored_instrument_requires_source_defined_result(self) -> None:
        value = load_json(ROOT / "valid" / "scored-instrument.json")
        self.assertEqual(value["basis"]["instrument_use"], "scored")
        self.assertIn("instrument_result", value)
        self.assertFalse(list(self.validator.iter_errors(value)))

    def test_unscored_checklist_does_not_fabricate_numeric_result(self) -> None:
        value = load_json(ROOT / "valid" / "unscored-checklist.json")
        self.assertEqual(value["basis"]["instrument_use"], "unscored")
        self.assertNotIn("instrument_result", value)
        self.assertFalse(list(self.validator.iter_errors(value)))

    def test_instrument_scale_is_source_defined_not_universal(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        instrument = schema["$defs"]["instrumentResult"]["properties"]
        self.assertIn("instrument_name", instrument)
        self.assertIn("instrument_version", instrument)
        self.assertIn("scale_minimum", instrument)
        self.assertIn("scale_maximum", instrument)
        self.assertIn("value", instrument)
        self.assertNotIn("normalized_score", instrument)
        self.assertNotIn("fidelity_percentage", instrument)

    def test_instrument_application_bounds_are_enforced(self) -> None:
        reversed_scale = load_json(
            ROOT / "application-invalid" / "instrument-scale-reversed.json"
        )
        above = load_json(
            ROOT / "application-invalid" / "instrument-value-above-scale.json"
        )
        self.assertIn(
            "instrument scale_minimum must be less than scale_maximum",
            application_errors(reversed_scale),
        )
        self.assertIn(
            "instrument value must fall within declared scale",
            application_errors(above),
        )

    def test_fidelity_does_not_encode_provider_competence_compliance_or_outcome(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        properties = schema["properties"]
        for forbidden in (
            "provider_competence",
            "student_compliance",
            "effectiveness",
            "outcome",
            "successful",
            "goal_attained",
        ):
            self.assertNotIn(forbidden, properties)
        text = json.dumps(schema)
        self.assertIn("no_provider_competence_inference", text)
        self.assertIn("no_student_compliance_inference", text)
        self.assertIn("no_effectiveness_inference", text)
        self.assertIn("no_outcome_inference", text)

    def test_successor_reason_vocabulary_matches_adr(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        reasons = schema["$defs"]["supersessionEntry"]["properties"]["reason"]["enum"]
        self.assertEqual(
            reasons,
            [
                "evaluator_corrected",
                "scope_corrected",
                "basis_corrected",
                "result_corrected",
                "instrument_result_corrected",
                "evaluation_period_corrected",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
                "other",
            ],
        )

    def test_no_v1_amendment_paths_and_exact_refs_stay_exact(self) -> None:
        schema = load_json(REPO_ROOT / SCHEMA_PATH)
        text = json.dumps(schema)
        self.assertIn("amendment_prohibited_v1", text)
        self.assertIn("no_silent_successor_following", text)
        self.assertNotIn('"amendments"', text)
        self.assertNotIn('"amendment_paths"', text)

    def test_preallocated_paper_cannot_create_fidelity(self) -> None:
        value = load_json(ROOT / "invalid" / "preallocated-paper.json")
        self.assertTrue(list(self.validator.iter_errors(value)))


if __name__ == "__main__":
    unittest.main()
