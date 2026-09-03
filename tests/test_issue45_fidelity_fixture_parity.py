"""Guard Issue #45 Fidelity runtime coverage against frozen Issue #18 fixtures."""

from __future__ import annotations

import ast
import json
from pathlib import Path

FIXTURE_ROOT = Path("tests/schema_validation/fixtures/issue-18/fidelity")
WORKFLOW_TEST = Path("tests/test_workflow_fidelity.py")

COVERAGE: dict[str, str] = {
    "one-implementation-direct-observation.json": (
        "test_create_one_implementation_fidelity_and_load_exact"
    ),
    "implementation-set-record-basis.json": (
        "test_create_implementation_set_with_exact_record_basis"
    ),
    "bounded-plan-interval-review.json": "test_create_bounded_plan_interval_fidelity",
    "unscored-checklist.json": "test_create_unscored_checklist_fidelity",
    "scored-instrument.json": "test_create_scored_instrument_preserves_source_scale",
    "combined-scored-basis.json": "test_create_combined_scored_fidelity_basis",
    "support-plan-fidelity.json": "test_create_one_implementation_fidelity_and_load_exact",
    "other-basis-with-detail.json": "test_create_other_fidelity_basis_with_detail",
    "proposed-import-fidelity.json": (
        "test_historical_proposed_import_fidelity_resolves_exactly_without_current_use"
    ),
    "created-before-evaluated.json": "test_fidelity_recording_chronology",
    "updated-before-created.json": "test_fidelity_recording_chronology",
    "active-import.json": "test_active_paper_or_import_requires_review_history",
    "active-paper.json": "test_active_paper_or_import_requires_review_history",
    "unresolved-plan.json": "test_unresolved_plan_fails_closed",
    "unresolved-evaluator.json": "test_unresolved_evaluator_fails_closed",
    "unresolved-scope-implementation.json": (
        "test_unresolved_scope_implementation_fails_closed"
    ),
    "scope-implementation-wrong-plan.json": (
        "test_scope_implementation_requires_same_exact_plan"
    ),
    "implementation-set-mixed-plans.json": (
        "test_implementation_set_cannot_mix_exact_plans"
    ),
    "interval-ended-before-started.json": (
        "test_bounded_interval_rejects_reversed_chronology"
    ),
    "unresolved-basis-record.json": "test_unresolved_basis_record_fails_closed",
    "instrument-scale-reversed.json": "test_instrument_scale_validation",
    "instrument-value-below-scale.json": "test_instrument_scale_validation",
    "instrument-value-above-scale.json": "test_instrument_scale_validation",
    "self-supersession.json": "test_fidelity_self_supersession_is_rejected",
    "mixed-supersession-reasons.json": (
        "test_mixed_fidelity_supersession_reasons_are_rejected"
    ),
    "duplicate-consolidation-one-predecessor.json": (
        "test_duplicate_fidelity_consolidation_needs_two_predecessors"
    ),
    "ordinary-correction-two-predecessors.json": (
        "test_ordinary_fidelity_correction_is_one_to_one"
    ),
    "ordinary-correction-cross-work.json": (
        "test_ordinary_fidelity_correction_cannot_cross_support_process_roots"
    ),
    "work-root-correction-same-work.json": (
        "test_fidelity_work_root_correction_requires_different_support_process_root"
    ),
    "work-root-correction-changed-id.json": (
        "test_fidelity_work_root_correction_preserves_fidelity_id"
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


def test_issue18_fidelity_manifest_has_frozen_runtime_case_counts() -> None:
    manifest = _manifest()
    valid = manifest["valid"]
    application_invalid = manifest["application_invalid"]
    invalid = manifest["invalid"]
    assert isinstance(valid, list) and len(valid) == 9
    assert isinstance(application_invalid, list) and len(application_invalid) == 21
    assert isinstance(invalid, list) and len(invalid) == 21


def test_issue45_fidelity_runtime_coverage_matches_every_schema_valid_fixture() -> None:
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
