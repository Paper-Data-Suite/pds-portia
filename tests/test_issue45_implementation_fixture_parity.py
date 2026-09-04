"""Guard Issue #45 Implementation runtime coverage against frozen Issue #18 fixtures."""

from __future__ import annotations

import ast
import json
from pathlib import Path

FIXTURE_ROOT = Path("tests/schema_validation/fixtures/issue-18/implementation")
WORKFLOW_TEST = Path("tests/test_workflow_implementations.py")

COVERAGE: dict[str, str] = {
    "completed-intervention-occurrence.json": (
        "test_create_intervention_occurrence_and_load_exact"
    ),
    "in-progress-occurrence.json": (
        "test_in_progress_occurrence_can_reach_each_ordinary_terminal_state"
    ),
    "attempted-occurrence.json": (
        "test_terminal_or_attempted_states_do_not_use_ordinary_execution_progression"
    ),
    "partially-completed-occurrence.json": (
        "test_terminal_or_attempted_states_do_not_use_ordinary_execution_progression"
    ),
    "unable-to-complete-occurrence.json": (
        "test_terminal_or_attempted_states_do_not_use_ordinary_execution_progression"
    ),
    "support-environmental-no-human-provider.json": (
        "test_create_support_occurrence_with_no_human_provider"
    ),
    "provider-variation-recorded.json": (
        "test_provider_difference_requires_explicit_variation"
    ),
    "target-variation-recorded.json": (
        "test_target_difference_requires_explicit_variation"
    ),
    "multi-kind-variation.json": (
        "test_multi_kind_variation_records_multiple_actual_differences"
    ),
    "proposed-import-unknown.json": (
        "test_historical_proposed_import_unknown_resolves_exactly_without_current_use"
    ),
    "ended-before-started.json": "test_implementation_chronology_is_validated",
    "created-before-started.json": "test_implementation_chronology_is_validated",
    "updated-before-created.json": "test_implementation_chronology_is_validated",
    "active-import.json": (
        "test_active_paper_or_import_implementation_requires_review_history"
    ),
    "active-paper.json": (
        "test_active_paper_or_import_implementation_requires_review_history"
    ),
    "unknown-digital.json": "test_unknown_execution_state_is_not_digitally_authored",
    "unknown-paper.json": "test_unknown_paper_execution_state_is_import_only",
    "unresolved-plan.json": "test_unresolved_plan_fails_closed",
    "unresolved-target.json": "test_unresolved_actual_target_fails_closed",
    "unresolved-provider.json": "test_unresolved_actual_provider_fails_closed",
    "duplicate-logical-provider.json": (
        "test_duplicate_logical_provider_identity_fails_closed"
    ),
    "provider-diff-without-variation.json": (
        "test_provider_difference_requires_explicit_variation"
    ),
    "target-diff-without-variation.json": (
        "test_target_difference_requires_explicit_variation"
    ),
    "provider-diff-wrong-variation-kind.json": (
        "test_provider_difference_with_wrong_variation_kind_fails_closed"
    ),
    "target-diff-wrong-variation-kind.json": (
        "test_target_difference_with_wrong_variation_kind_fails_closed"
    ),
    "self-supersession.json": "test_implementation_cannot_supersede_itself",
    "mixed-supersession-reasons.json": (
        "test_mixed_implementation_supersession_reasons_fail_closed"
    ),
    "duplicate-consolidation-one-predecessor.json": (
        "test_duplicate_consolidation_requires_two_predecessors"
    ),
    "ordinary-correction-two-predecessors.json": (
        "test_ordinary_implementation_correction_is_one_to_one"
    ),
    "ordinary-correction-cross-work.json": (
        "test_ordinary_correction_cannot_cross_support_process_roots"
    ),
    "work-root-correction-same-work.json": (
        "test_work_root_correction_requires_different_support_process_root"
    ),
    "work-root-correction-changed-id.json": (
        "test_work_root_correction_preserves_implementation_id"
    ),
}


def _manifest() -> dict[str, object]:
    return json.loads((FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _workflow_test_names() -> set[str]:
    tree = ast.parse(WORKFLOW_TEST.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def test_issue18_implementation_manifest_has_frozen_runtime_case_counts() -> None:
    manifest = _manifest()
    valid = manifest["valid"]
    application_invalid = manifest["application_invalid"]
    invalid = manifest["invalid"]
    assert isinstance(valid, list) and len(valid) == 10
    assert isinstance(application_invalid, list) and len(application_invalid) == 22
    assert isinstance(invalid, list) and len(invalid) == 17


def test_issue45_implementation_runtime_coverage_matches_every_schema_valid_fixture(
) -> None:
    manifest = _manifest()
    valid = manifest["valid"]
    application_invalid = manifest["application_invalid"]
    assert isinstance(valid, list)
    assert isinstance(application_invalid, list)
    expected = {str(name) for name in valid}
    expected.update(
        str(item["file"])
        for item in application_invalid
        if isinstance(item, dict) and "file" in item
    )
    assert set(COVERAGE) == expected
    test_names = _workflow_test_names()
    assert set(COVERAGE.values()) <= test_names
