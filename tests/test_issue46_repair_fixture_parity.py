"""Frozen Issue #19 Repair runtime parity guard for Portia Issue #46."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from portia.models import parse_portia_record

FIXTURE_ROOT = Path("tests/schema_validation/fixtures/issue-19/repair")
WORKFLOW_TEST = Path("tests/test_workflow_repairs.py")

COVERAGE: dict[str, str] = {
    "event-planning-invited-only.json": (
        'test_create_load_list_and_current_event_repair'
    ),
    "event-declined-without-agreement.json": (
        'test_repair_workflow_can_cancel_without_agreed_actions'
    ),
    "event-active-agreed-action.json": (
        'test_repair_workflow_progresses_planning_active_completed_without_inference'
    ),
    "event-completed-action.json": (
        'test_repair_accepts_completed_event_action_fixture_shape'
    ),
    "event-unable-no-actions.json": (
        'test_repair_workflow_can_end_unable_to_complete_without_actions'
    ),
    "event-other-role-and-action.json": (
        'test_repair_accepts_other_role_and_other_action_fixture_shape'
    ),
    "support-planning-participant-refs.json": (
        'test_create_load_list_and_current_support_repair'
    ),
    "support-active-cross-context.json": (
        'test_support_repair_accepts_cross_work_context_fixture_shape'
    ),
    "support-action-withdrawn.json": (
        'test_support_repair_accepts_withdrawn_action_fixture_shape'
    ),
    "support-completed-nonfinancial-action.json": (
        'test_support_repair_accepts_completed_nonfinancial_action_fixture_shape'
    ),
    "support-proposed-import-unknown-participation.json": (
        'test_proposed_imported_support_repair_unknown_participation_is_readable'
    ),
    "event-focus-correction-successor.json": (
        'test_repair_focus_correction_supersedes_exact_predecessor'
    ),
    "active-event-roster-student-facilitator.json": (
        'test_active_event_repair_rejects_roster_student_facilitator'
    ),
    "active-event-descriptive-facilitator.json": (
        'test_active_event_repair_rejects_descriptive_facilitator'
    ),
    "active-event-unidentified-facilitator.json": (
        'test_active_event_repair_rejects_unidentified_facilitator'
    ),
    "support-facilitator-without-operational-context.json": (
        'test_support_repair_requires_operational_facilitator_context'
    ),
    "active-event-unidentified-participant.json": (
        'test_active_event_repair_rejects_unidentified_participant'
    ),
    "active-unknown-participation-state.json": (
        'test_active_repair_rejects_unknown_participation_state'
    ),
    "support-participant-other-process.json": (
        'test_support_repair_participant_other_process_fixture_is_rejected'
    ),
    "duplicate-participant-key.json": 'test_repair_rejects_duplicate_participant_key',
    "action-agreed-by-unknown-key.json": (
        'test_repair_action_agreed_by_must_name_participant_key'
    ),
    "action-responsible-unknown-key.json": (
        'test_repair_action_responsible_keys_must_name_participants'
    ),
    "duplicate-action-key.json": 'test_repair_rejects_duplicate_action_key',
    "context-other-class.json": 'test_repair_context_must_remain_in_owning_class',
    "self-context-reference.json": 'test_repair_context_cannot_reference_itself',
    "active-import-without-review.json": (
        'test_active_imported_repair_requires_accepted_review_history'
    ),
    "updated-before-created.json": 'test_repair_rejects_updated_before_created',
    "action-completed-before-agreed.json": (
        'test_repair_rejects_action_completed_before_agreed'
    ),
    "self-supersession.json": 'test_repair_correction_rejects_self_supersession',
    "ordinary-correction-cross-work.json": (
        'test_repair_runtime_fixture_rejects_ordinary_correction_cross_work'
    ),
    "duplicate-consolidation-one-predecessor.json": (
        'test_repair_duplicate_consolidation_rejects_one_predecessor'
    ),
}
EXPECTED_ERRORS: dict[str, str] = {
    "active-event-roster-student-facilitator.json": (
        'Repair facilitator cannot use roster-student identity as operational authority'
    ),
    "active-event-descriptive-facilitator.json": (
        'current Repair facilitator requires an identified operational human'
    ),
    "active-event-unidentified-facilitator.json": (
        'current Repair facilitator requires an identified operational human'
    ),
    "support-facilitator-without-operational-context.json": (
        'Repair facilitator requires Support Process Participant context in \\{coordinator, provider_or_collaborator\\}'
    ),
    "active-event-unidentified-participant.json": (
        'active Repair cannot use an unidentified participant'
    ),
    "active-unknown-participation-state.json": (
        'active Repair cannot use unknown participation state'
    ),
    "support-participant-other-process.json": (
        'Repair participant Support Process Participant does not resolve in the owning Support Process'
    ),
    "duplicate-participant-key.json": 'Repair participant_key values must be unique',
    "action-agreed-by-unknown-key.json": (
        'Repair action agreed_by must reference an existing participant_key'
    ),
    "action-responsible-unknown-key.json": (
        'Repair action responsible_participant_keys must reference existing participant_key values'
    ),
    "duplicate-action-key.json": 'Repair action_key values must be unique',
    "context-other-class.json": 'Repair context must remain in the owning class',
    "self-context-reference.json": 'Repair context cannot reference the Repair itself',
    "active-import-without-review.json": (
        'paper/import activation requires accepted review history'
    ),
    "updated-before-created.json": (
        'Repair updated_at cannot precede Repair created_at'
    ),
    "action-completed-before-agreed.json": (
        'Repair action completed_at cannot precede Repair action agreed_at'
    ),
    "self-supersession.json": 'repair cannot supersede itself',
    "ordinary-correction-cross-work.json": (
        'ordinary repair correction cannot cross work roots'
    ),
    "duplicate-consolidation-one-predecessor.json": (
        'duplicate consolidation needs two repair predecessors'
    ),
}


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


def test_issue19_repair_manifest_metadata_and_counts_are_frozen() -> None:
    manifest = _manifest()
    assert manifest["manifest_version"] == "1"
    assert manifest["issue"] == 19
    assert manifest["contract"] == "repair"
    assert manifest["version"] == "1"
    assert len(_names(manifest["valid"])) == 12
    assert len(_names(manifest["application_invalid"])) == 19
    assert len(_names(manifest["invalid"])) == 25


def test_issue19_repair_runtime_coverage_is_exactly_31_cases() -> None:
    manifest = _manifest()
    valid = set(_names(manifest["valid"]))
    application_invalid = set(_names(manifest["application_invalid"]))
    assert valid.isdisjoint(application_invalid)
    assert set(COVERAGE) == valid | application_invalid
    assert len(COVERAGE) == 31
    assert len(set(COVERAGE.values())) == 31


def test_issue19_repair_every_runtime_case_targets_real_workflow_test() -> None:
    functions = _workflow_functions()
    missing = {
        target
        for target in COVERAGE.values()
        if target not in functions
    }
    assert missing == set()


def test_issue19_repair_application_errors_are_frozen_and_asserted() -> None:
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


def test_issue19_repair_structural_invalid_is_separate_from_runtime_parity() -> None:
    manifest = _manifest()
    structural = set(_names(manifest["invalid"]))
    runtime = set(COVERAGE)
    assert len(structural) == 25
    assert structural.isdisjoint(runtime)
    assert len(runtime) + len(structural) == 56


def test_issue19_repair_all_31_runtime_fixture_payloads_reach_runtime_model() -> None:
    manifest = _manifest()
    for bucket in ("valid", "application_invalid"):
        directory = "application-invalid" if bucket == "application_invalid" else bucket
        for filename in _names(manifest[bucket]):
            value = json.loads(
                (FIXTURE_ROOT / directory / filename).read_text(encoding="utf-8")
            )
            record = parse_portia_record("repair", "1", value)
            assert record.contract == "repair"
            assert record.to_dict()["schema_version"] == "1"
            assert record.logical_id == value["repair_id"]
