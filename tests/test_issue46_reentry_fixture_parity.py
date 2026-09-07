"""Frozen Issue #19 Reentry runtime parity guard for Portia Issue #46."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from portia.models import parse_portia_record

FIXTURE_ROOT = Path(
    "tests/schema_validation/fixtures/issue-19/reentry"
)
WORKFLOW_TEST = Path("tests/test_workflow_reentries.py")

COVERAGE: dict[str, str] = {'event-planned-date-only.json': 'test_create_load_list_and_current_event_reentry', 'event-active-exact-time-response-context.json': 'test_reentry_accepts_exact_response_initiating_context', 'event-date-window-determination-context.json': 'test_reentry_accepts_date_window_determination_context', 'event-external-minimal-context.json': 'test_reentry_accepts_minimal_external_initiating_context', 'event-links-support-plans.json': 'test_event_reentry_accepts_exact_support_and_intervention_links', 'support-planned-own-process-context.json': 'test_active_support_reentry_accepts_coordinator_context', 'support-active-exact-window-communication.json': 'test_support_reentry_accepts_exact_window_communication_context', 'support-completed-event-context.json': 'test_support_reentry_accepts_completed_event_context_without_clearance_inference', 'support-other-context-and-element.json': 'test_support_reentry_accepts_other_context_and_other_planned_element', 'support-proposed-import.json': 'test_proposed_imported_reentry_is_exactly_readable', 'event-timing-correction-successor.json': 'test_reentry_timing_correction_supersedes_exact_predecessor', 'active-event-roster-student-coordinator.json': 'test_active_event_reentry_rejects_roster_student_coordinator', 'active-event-descriptive-coordinator.json': 'test_reentry_activation_revalidates_operational_coordinator', 'active-event-unidentified-coordinator.json': 'test_active_event_reentry_rejects_unidentified_coordinator', 'support-coordinator-without-operational-context.json': 'test_active_support_reentry_requires_operational_coordinator_context', 'active-import-without-review.json': 'test_active_imported_reentry_requires_accepted_review_history', 'updated-before-created.json': 'test_reentry_rejects_updated_before_created', 'date-window-ends-before-start.json': 'test_reentry_rejects_reversed_date_window', 'exact-window-ends-before-start.json': 'test_reentry_rejects_reversed_exact_window', 'initiating-context-other-class.json': 'test_reentry_rejects_initiating_context_other_class', 'support-ref-other-class.json': 'test_reentry_support_plan_rejects_other_class', 'support-owned-plan-other-process.json': 'test_support_owned_reentry_plan_must_share_process', 'self-supersession.json': 'test_reentry_rejects_self_supersession', 'ordinary-correction-cross-work.json': 'test_reentry_rejects_ordinary_correction_cross_work', 'duplicate-consolidation-one-predecessor.json': 'test_reentry_duplicate_consolidation_rejects_one_predecessor'}
EXPECTED_ERRORS: dict[str, str] = {'active-event-roster-student-coordinator.json': 'Reentry coordinator cannot use roster-student identity as operational authority', 'active-event-descriptive-coordinator.json': 'current Reentry coordinator requires an identified operational human', 'active-event-unidentified-coordinator.json': 'current Reentry coordinator requires an identified operational human', 'support-coordinator-without-operational-context.json': 'Reentry coordinator requires Support Process Participant context in \\{coordinator, provider_or_collaborator\\}', 'active-import-without-review.json': 'paper/import activation requires accepted review history', 'updated-before-created.json': 'Reentry updated_at cannot precede Reentry created_at', 'date-window-ends-before-start.json': 'Reentry ends_on cannot precede Reentry starts_on', 'exact-window-ends-before-start.json': 'Reentry ends_at cannot precede Reentry starts_at', 'initiating-context-other-class.json': 'initiating context must remain in the owning class', 'support-ref-other-class.json': 'Reentry support plan must remain in the owning class', 'support-owned-plan-other-process.json': 'Support-Process-owned Reentry plan must share process', 'self-supersession.json': 'reentry cannot supersede itself', 'ordinary-correction-cross-work.json': 'ordinary reentry correction cannot cross work roots', 'duplicate-consolidation-one-predecessor.json': 'duplicate consolidation needs two reentry predecessors'}


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


def test_issue19_reentry_manifest_metadata_and_counts_are_frozen() -> None:
    manifest = _manifest()
    assert manifest["manifest_version"] == "1"
    assert manifest["issue"] == 19
    assert manifest["contract"] == "reentry"
    assert manifest["version"] == "1"
    assert len(_names(manifest["valid"])) == 11
    assert len(_names(manifest["application_invalid"])) == 14
    assert len(_names(manifest["invalid"])) == 16


def test_issue19_reentry_runtime_coverage_is_exactly_25_cases() -> None:
    manifest = _manifest()
    valid = set(_names(manifest["valid"]))
    application_invalid = set(_names(manifest["application_invalid"]))
    assert valid.isdisjoint(application_invalid)
    assert set(COVERAGE) == valid | application_invalid
    assert len(COVERAGE) == 25


def test_issue19_reentry_every_runtime_case_targets_real_workflow_test() -> None:
    functions = _workflow_functions()
    missing = {
        target
        for target in COVERAGE.values()
        if target not in functions
    }
    assert missing == set()


def test_issue19_reentry_application_errors_are_frozen_and_asserted() -> None:
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


def test_issue19_reentry_structural_invalid_is_separate_from_runtime_parity() -> None:
    manifest = _manifest()
    structural = set(_names(manifest["invalid"]))
    runtime = set(COVERAGE)
    assert len(structural) == 16
    assert structural.isdisjoint(runtime)
    assert len(runtime) + len(structural) == 41


def test_issue19_reentry_all_25_runtime_fixture_payloads_reach_runtime_model() -> None:
    manifest = _manifest()
    for bucket in ("valid", "application_invalid"):
        directory = "application-invalid" if bucket == "application_invalid" else bucket
        for filename in _names(manifest[bucket]):
            value = json.loads(
                (FIXTURE_ROOT / directory / filename).read_text(encoding="utf-8")
            )
            record = parse_portia_record("reentry", "1", value)
            assert record.contract == "reentry"
            assert record.to_dict()["schema_version"] == "1"
            assert record.logical_id == value["reentry_id"]
