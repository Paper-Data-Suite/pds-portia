"""Frozen Issue #19 Outcome runtime parity guard for Portia Issue #46."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from portia.models import parse_portia_record

FIXTURE_ROOT = Path(
    "tests/schema_validation/fixtures/issue-19/outcome"
)
WORKFLOW_TEST = Path("tests/test_workflow_outcomes.py")

COVERAGE: dict[str, str] = {'event-observed-change-improved.json': 'test_create_load_list_and_current_event_outcome', 'event-recurrence-observed.json': 'test_outcome_accepts_recurrence_observed_with_bounded_coverage', 'event-no-recurrence-with-coverage.json': 'test_outcome_accepts_no_recurrence_only_with_defined_coverage', 'support-goal-met.json': 'test_outcome_accepts_support_goal_status_scope', 'support-response-progress.json': 'test_outcome_accepts_support_response_with_implementation_and_fidelity_context', 'support-response-unable-with-limitation.json': 'test_outcome_accepts_support_response_unable_with_limitation', 'support-adverse-no-change-with-coverage.json': 'test_outcome_accepts_adverse_review_no_change_with_coverage', 'support-other-conclusion.json': 'test_outcome_accepts_other_scope_conclusion_with_detail', 'event-reentry-status.json': 'test_outcome_accepts_event_reentry_status_without_clearance_inference', 'support-repair-status.json': 'test_outcome_accepts_support_repair_status_with_account_perspective', 'support-proposed-import-unknown-time.json': 'test_proposed_imported_outcome_with_unknown_timeframe_is_exactly_readable', 'event-module-basis.json': 'test_active_outcome_module_basis_resolves_exact_reference_through_authority', 'event-basis-correction-successor.json': 'test_outcome_basis_correction_supersedes_exact_predecessor', 'active-event-roster-student-evaluator.json': 'test_active_event_outcome_rejects_roster_student_evaluator', 'active-event-descriptive-evaluator.json': 'test_active_event_outcome_rejects_descriptive_evaluator', 'active-event-unidentified-evaluator.json': 'test_active_event_outcome_rejects_unidentified_evaluator', 'support-evaluator-without-evaluator-context.json': 'test_active_support_outcome_requires_evaluator_context', 'active-import-without-review.json': 'test_active_imported_outcome_requires_accepted_review_history', 'updated-before-created.json': 'test_outcome_rejects_updated_before_created', 'timeframe-range-reversed.json': 'test_outcome_rejects_reversed_timeframe_range', 'active-unknown-timeframe.json': 'test_active_outcome_rejects_unknown_timeframe', 'student-perspective-role-non-account.json': 'test_outcome_student_perspective_basis_requires_account', 'implementation-context-non-implementation.json': 'test_outcome_implementation_context_basis_requires_implementation', 'fidelity-context-non-fidelity.json': 'test_outcome_fidelity_context_basis_requires_fidelity', 'self-basis-reference.json': 'test_outcome_basis_cannot_reference_itself', 'goal-ref-other-support-process.json': 'test_outcome_goal_scope_rejects_other_support_process', 'plan-ref-other-support-process.json': 'test_outcome_plan_scope_rejects_other_support_process', 'self-supersession.json': 'test_outcome_rejects_self_supersession', 'ordinary-correction-cross-work.json': 'test_outcome_rejects_ordinary_correction_cross_work', 'duplicate-consolidation-one-predecessor.json': 'test_outcome_duplicate_consolidation_rejects_one_predecessor'}
EXPECTED_ERRORS: dict[str, str] = {'active-event-roster-student-evaluator.json': 'Outcome evaluator cannot use roster-student identity as operational authority', 'active-event-descriptive-evaluator.json': 'current Outcome evaluator requires an identified operational human', 'active-event-unidentified-evaluator.json': 'current Outcome evaluator requires an identified operational human', 'support-evaluator-without-evaluator-context.json': 'Outcome evaluator requires Support Process Participant context in \\{coordinator, observer, provider_or_collaborator\\}', 'active-import-without-review.json': 'paper/import activation requires accepted review history', 'updated-before-created.json': 'Outcome updated_at cannot precede Outcome created_at', 'timeframe-range-reversed.json': 'Outcome timeframe ended_at cannot precede Outcome timeframe started_at', 'active-unknown-timeframe.json': 'active Outcome timeframe may not be unknown', 'student-perspective-role-non-account.json': "Outcome basis role 'student_or_family_perspective' requires 'account'", 'implementation-context-non-implementation.json': "Outcome basis role 'implementation_context' requires 'implementation'", 'fidelity-context-non-fidelity.json': "Outcome basis role 'fidelity_context' requires 'fidelity'", 'self-basis-reference.json': 'Outcome basis cannot reference the current Outcome itself', 'goal-ref-other-support-process.json': 'Outcome scope goal_ref does not resolve in the owning support_process', 'plan-ref-other-support-process.json': 'Outcome scope plan_refs\\[0\\] does not resolve in the owning support_process', 'self-supersession.json': 'outcome cannot supersede itself', 'ordinary-correction-cross-work.json': 'ordinary outcome correction cannot cross work roots', 'duplicate-consolidation-one-predecessor.json': 'duplicate consolidation needs two outcome predecessors'}


def _manifest() -> dict[str, object]:
    value = json.loads(
        (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _names(value: object) -> tuple[str, ...]:
    assert isinstance(value, list)
    assert all(isinstance(item, str) for item in value)
    return tuple(value)


def _workflow_functions() -> dict[str, ast.FunctionDef]:
    module = ast.parse(WORKFLOW_TEST.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in module.body
        if isinstance(node, ast.FunctionDef)
    }


def _literal_matches(function: ast.FunctionDef) -> set[str]:
    matches: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        for keyword in node.keywords:
            if keyword.arg != "match":
                continue
            value = keyword.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                matches.add(value.value)
    return matches


def test_issue19_outcome_manifest_metadata_and_counts_are_frozen() -> None:
    manifest = _manifest()
    assert manifest["manifest_version"] == "1"
    assert manifest["issue"] == 19
    assert manifest["contract"] == "outcome"
    assert manifest["version"] == "1"
    assert len(_names(manifest["valid"])) == 13
    assert len(_names(manifest["application_invalid"])) == 17
    assert len(_names(manifest["invalid"])) == 18


def test_issue19_outcome_runtime_coverage_is_exactly_30_cases() -> None:
    manifest = _manifest()
    valid = set(_names(manifest["valid"]))
    application_invalid = set(_names(manifest["application_invalid"]))
    assert valid.isdisjoint(application_invalid)
    assert set(COVERAGE) == valid | application_invalid
    assert len(COVERAGE) == 30


def test_issue19_outcome_every_runtime_case_targets_real_workflow_test() -> None:
    functions = _workflow_functions()
    missing = {
        target
        for target in COVERAGE.values()
        if target not in functions
    }
    assert missing == set()


def test_issue19_outcome_application_errors_are_frozen_and_asserted() -> None:
    manifest = _manifest()
    application_invalid = set(_names(manifest["application_invalid"]))
    assert set(EXPECTED_ERRORS) == application_invalid
    functions = _workflow_functions()
    for fixture, expected_error in EXPECTED_ERRORS.items():
        target = COVERAGE[fixture]
        assert expected_error in _literal_matches(functions[target]), (
            fixture,
            target,
            expected_error,
        )


def test_issue19_outcome_structural_invalid_is_separate_from_runtime_parity() -> None:
    manifest = _manifest()
    structural = set(_names(manifest["invalid"]))
    runtime = set(COVERAGE)
    assert len(structural) == 18
    assert structural.isdisjoint(runtime)
    assert len(runtime) + len(structural) == 48


def test_issue19_outcome_all_30_runtime_fixture_payloads_reach_runtime_model() -> None:
    manifest = _manifest()
    for bucket in ("valid", "application_invalid"):
        for filename in _names(manifest[bucket]):
            value = json.loads(
                (FIXTURE_ROOT / bucket.replace("_", "-") / filename).read_text(
                    encoding="utf-8"
                )
            )
            record = parse_portia_record("outcome", "1", value)
            assert record.contract == "outcome"
            assert record.to_dict()["schema_version"] == "1"
            assert record.logical_id == value["outcome_id"]
