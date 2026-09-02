"""Issue #44 guard for the frozen Issue #18 planning runtime oracle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ISSUE18 = Path("tests/schema_validation/fixtures/issue-18")

# Every accepted #44-owned planning scenario is listed explicitly here.
# The guard compares these names against the frozen manifests so newly added,
# removed, or renamed scenarios cannot silently lose runtime traceability.
VALID_COVERAGE: dict[str, dict[str, str]] = {
    "support-process": {
        "active-teacher-identified.json": "tests/test_workflow_support_process_activation.py",
        "planning-process.json": "tests/test_workflow_support_process_bootstrap.py",
        "paused-process.json": "tests/test_workflow_support_process_activation.py",
        "completed-valid-record.json": "tests/test_workflow_support_process_activation.py",
        "event-initiation.json": "tests/test_workflow_support_process_initiation.py",
        "response-handoff-initiation.json": "tests/test_workflow_support_process_initiation.py",
        "represented-account-request.json": "tests/test_workflow_support_process_initiation.py",
        "cross-year-continuation.json": "tests/test_workflow_support_process_continuation.py",
        "proposed-imported-history.json": "tests/test_workflow_support_process_initiation.py",
        "proposed-paper-record.json": "tests/test_workflow_support_process_bootstrap.py",
    },
    "support-process-participant": {
        "supported-roster-student.json": "tests/test_workflow_support_process_participants.py",
        "cross-class-roster-student.json": "tests/test_workflow_support_process_participants.py",
        "actor-collaborator.json": "tests/test_workflow_support_process_participants.py",
        "local-operator-coordinator.json": "tests/test_workflow_support_process_participants.py",
        "descriptive-family-person.json": "tests/test_workflow_support_process_participants.py",
        "observer-context.json": "tests/test_workflow_support_process_participants.py",
        "other-context-with-detail.json": "tests/test_workflow_support_process_participants.py",
        "proposed-unidentified-import.json": "tests/test_workflow_support_process_participants.py",
    },
    "support-need": {
        "participant-access.json": "tests/test_workflow_support_needs.py",
        "whole-process-environmental.json": "tests/test_workflow_support_needs.py",
        "participant-set-organizational.json": "tests/test_workflow_support_needs.py",
        "skill-or-strategy.json": "tests/test_workflow_support_needs.py",
        "relationship.json": "tests/test_workflow_support_needs.py",
        "resource-coordination.json": "tests/test_workflow_support_needs.py",
        "other-with-detail.json": "tests/test_workflow_support_needs.py",
        "proposed-import.json": "tests/test_workflow_support_needs.py",
    },
    "support-goal": {
        "participant-goal-with-planning-fields.json": "tests/test_workflow_support_goals.py",
        "goal-no-criteria.json": "tests/test_workflow_support_goals.py",
        "goal-no-measurement.json": "tests/test_workflow_support_goals.py",
        "whole-process-goal.json": "tests/test_workflow_support_goals.py",
        "participant-set-goal.json": "tests/test_workflow_support_goals.py",
        "proposed-import-goal.json": "tests/test_workflow_support_goals.py",
    },
    "support": {
        "as-needed-access-no-provider.json": "tests/test_workflow_supports.py",
        "assigned-recurring-support.json": "tests/test_workflow_supports.py",
        "goal-linked-support.json": "tests/test_workflow_supports.py",
        "self-directed-no-provider.json": "tests/test_workflow_supports.py",
        "resource-availability-no-provider.json": "tests/test_workflow_supports.py",
        "paused-support.json": "tests/test_workflow_supports.py",
        "completed-valid-history.json": "tests/test_workflow_supports.py",
        "proposed-import-support.json": "tests/test_workflow_supports.py",
    },
    "intervention": {
        "active-recurring-assigned.json": "tests/test_workflow_interventions.py",
        "active-condition-triggered.json": "tests/test_workflow_interventions.py",
        "active-custom-schedule.json": "tests/test_workflow_interventions.py",
        "multiple-needs-goals-providers.json": "tests/test_workflow_interventions.py",
        "paused-intervention.json": "tests/test_workflow_interventions.py",
        "completed-valid-history.json": "tests/test_workflow_interventions.py",
        "proposed-import-no-provider.json": "tests/test_workflow_interventions.py",
        "proposed-as-needed.json": "tests/test_workflow_interventions.py",
    },
    "planned-schedule": {
        "as-needed-access": "tests/test_workflow_supports.py",
        "weekly-selected-days": "tests/test_workflow_interventions.py",
        "every-two-weeks-range": "tests/test_workflow_interventions.py",
        "condition-triggered": "tests/test_workflow_interventions.py",
        "custom": "tests/test_workflow_interventions.py",
    },
}

APPLICATION_INVALID_COVERAGE: dict[str, dict[str, str]] = {
    "support-process": {
        "school-year-not-consecutive.json": "tests/test_workflow_support_process_bootstrap.py",
        "planned-end-before-start.json": "tests/test_workflow_support_process_bootstrap.py",
        "review-before-start.json": "tests/test_workflow_support_process_bootstrap.py",
        "updated-before-created.json": "tests/test_workflow_support_process_bootstrap.py",
        "active-import.json": "tests/test_workflow_support_process_bootstrap.py",
        "active-paper.json": "tests/test_workflow_support_process_bootstrap.py",
        "imported-history-with-digital-source.json": "tests/test_workflow_support_process_initiation.py",
        "continues-from-self.json": "tests/test_workflow_support_process_continuation.py",
        "continuation-also-supersession.json": "tests/test_workflow_support_process_continuation.py",
        "self-supersession.json": "tests/test_workflow_support_process_activation.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_support_process_activation.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_support_process_activation.py",
        "ordinary-correction-two-predecessors.json": "tests/test_workflow_support_process_activation.py",
        "ordinary-correction-cross-class.json": "tests/test_workflow_support_process_activation.py",
        "work-root-correction-same-class.json": "tests/test_workflow_support_process_activation.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_support_process_activation.py",
    },
    "support-process-participant": {
        "updated-before-created.json": "tests/test_workflow_support_process_participants.py",
        "active-import.json": "tests/test_workflow_support_process_participants.py",
        "active-paper.json": "tests/test_workflow_support_process_participants.py",
        "active-unidentified.json": "tests/test_workflow_support_process_participants.py",
        "self-supersession.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "ordinary-correction-two-predecessors.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "ordinary-correction-cross-work.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "work-root-correction-same-work.json": "tests/test_workflow_support_process_participant_lifecycle.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_support_process_participant_lifecycle.py",
    },
    "support-need": {
        "updated-before-created.json": "tests/test_workflow_support_needs.py",
        "active-import.json": "tests/test_workflow_support_needs.py",
        "active-paper.json": "tests/test_workflow_support_needs.py",
        "unresolved-participant-target.json": "tests/test_workflow_support_needs.py",
        "duplicate-logical-targets.json": "tests/test_workflow_support_needs.py",
        "self-supersession.json": "tests/test_workflow_support_needs.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_support_needs.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_support_needs.py",
        "ordinary-correction-two-predecessors.json": "tests/test_workflow_support_needs.py",
        "ordinary-correction-cross-work.json": "tests/test_workflow_support_needs.py",
        "work-root-correction-same-work.json": "tests/test_workflow_support_needs.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_support_needs.py",
    },
    "support-goal": {
        "updated-before-created.json": "tests/test_workflow_support_goals.py",
        "active-import.json": "tests/test_workflow_support_goals.py",
        "active-paper.json": "tests/test_workflow_support_goals.py",
        "unresolved-participant-target.json": "tests/test_workflow_support_goals.py",
        "duplicate-logical-targets.json": "tests/test_workflow_support_goals.py",
        "self-supersession.json": "tests/test_workflow_support_goals.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_support_goals.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_support_goals.py",
        "ordinary-correction-two-predecessors.json": "tests/test_workflow_support_goals.py",
        "ordinary-correction-cross-work.json": "tests/test_workflow_support_goals.py",
        "work-root-correction-same-work.json": "tests/test_workflow_support_goals.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_support_goals.py",
    },
    "support": {
        "updated-before-created.json": "tests/test_workflow_supports.py",
        "active-import.json": "tests/test_workflow_supports.py",
        "active-paper.json": "tests/test_workflow_supports.py",
        "unresolved-need.json": "tests/test_workflow_supports.py",
        "unresolved-goal.json": "tests/test_workflow_supports.py",
        "unresolved-provider.json": "tests/test_workflow_supports.py",
        "duplicate-logical-provider.json": "tests/test_workflow_supports.py",
        "self-supersession.json": "tests/test_workflow_supports.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_supports.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_supports.py",
        "ordinary-correction-cross-work.json": "tests/test_workflow_supports.py",
        "plan-adaptation-cross-work.json": "tests/test_workflow_supports.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_supports.py",
    },
    "intervention": {
        "updated-before-created.json": "tests/test_workflow_interventions.py",
        "active-import.json": "tests/test_workflow_interventions.py",
        "active-paper.json": "tests/test_workflow_interventions.py",
        "active-no-assigned-provider.json": "tests/test_workflow_interventions.py",
        "active-as-needed.json": "tests/test_workflow_interventions.py",
        "unresolved-need.json": "tests/test_workflow_interventions.py",
        "unresolved-goal.json": "tests/test_workflow_interventions.py",
        "unresolved-provider.json": "tests/test_workflow_interventions.py",
        "duplicate-logical-provider.json": "tests/test_workflow_interventions.py",
        "self-supersession.json": "tests/test_workflow_interventions.py",
        "mixed-supersession-reasons.json": "tests/test_workflow_interventions.py",
        "duplicate-consolidation-one-predecessor.json": "tests/test_workflow_interventions.py",
        "ordinary-correction-cross-work.json": "tests/test_workflow_interventions.py",
        "plan-adaptation-cross-work.json": "tests/test_workflow_interventions.py",
        "work-root-correction-changed-id.json": "tests/test_workflow_interventions.py",
    },
    "planned-schedule": {
        "window-ended-before-started": "tests/test_workflow_interventions.py",
        "review-before-start": "tests/test_workflow_interventions.py",
        "duration-range-reversed": "tests/test_workflow_interventions.py",
    },
}

DEFERRED_FAMILIES = {
    "implementation": "#45",
    "fidelity": "#45",
}

EXPECTED_VALID_COUNT = 53
EXPECTED_APPLICATION_INVALID_COUNT = 82


def _manifest(family: str) -> dict[str, Any]:
    path = ISSUE18 / family / "manifest.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _entry_name(value: object) -> str:
    if isinstance(value, str):
        return value
    assert isinstance(value, dict)
    name = value.get("file", value.get("name"))
    assert isinstance(name, str)
    return name


def _valid_names(manifest: dict[str, Any]) -> set[str]:
    values = manifest.get("valid", ())
    assert isinstance(values, list)
    return {_entry_name(value) for value in values}


def _application_invalid(manifest: dict[str, Any]) -> dict[str, str]:
    values = manifest.get("application_invalid", ())
    assert isinstance(values, list)
    result: dict[str, str] = {}
    for value in values:
        assert isinstance(value, dict)
        name = _entry_name(value)
        expected_error = value.get("expected_error")
        assert isinstance(expected_error, str)
        assert expected_error.strip()
        result[name] = expected_error
    return result


def _structural_names(manifest: dict[str, Any]) -> set[str]:
    values = manifest.get("invalid", manifest.get("structural_invalid", ()))
    assert isinstance(values, list)
    return {_entry_name(value) for value in values}


def test_issue18_planning_runtime_coverage_matches_frozen_oracle() -> None:
    valid_count = 0
    application_invalid_count = 0

    assert set(VALID_COVERAGE) == set(APPLICATION_INVALID_COVERAGE)
    for family in sorted(VALID_COVERAGE):
        manifest = _manifest(family)
        valid = _valid_names(manifest)
        application_invalid = _application_invalid(manifest)

        assert valid == set(VALID_COVERAGE[family]), (
            f"{family} frozen valid runtime coverage drifted"
        )
        assert application_invalid.keys() == APPLICATION_INVALID_COVERAGE[
            family
        ].keys(), f"{family} frozen application-invalid runtime coverage drifted"

        valid_count += len(valid)
        application_invalid_count += len(application_invalid)

    assert valid_count == EXPECTED_VALID_COUNT
    assert application_invalid_count == EXPECTED_APPLICATION_INVALID_COUNT


def test_every_planning_scenario_maps_to_existing_workflow_test_module() -> None:
    for coverage in (VALID_COVERAGE, APPLICATION_INVALID_COVERAGE):
        for family, scenarios in coverage.items():
            assert scenarios, f"{family} has no runtime coverage entries"
            for scenario, test_module in scenarios.items():
                path = Path(test_module)
                assert path.is_file(), (
                    f"{family}/{scenario} maps to missing workflow test {test_module}"
                )
                assert path.name.startswith("test_workflow_")
                assert path.suffix == ".py"


def test_application_invalid_scenarios_keep_exact_rejecting_invariant() -> None:
    for family, scenarios in APPLICATION_INVALID_COVERAGE.items():
        manifest = _manifest(family)
        errors = _application_invalid(manifest)
        for scenario in scenarios:
            invariant = errors[scenario]
            assert invariant.strip(), (
                f"{family}/{scenario} has no rejecting application invariant"
            )


def test_structural_invalid_cases_are_not_misclassified_as_runtime_cases() -> None:
    for family in VALID_COVERAGE:
        manifest = _manifest(family)
        structural = _structural_names(manifest)
        runtime = set(VALID_COVERAGE[family]) | set(
            APPLICATION_INVALID_COVERAGE[family]
        )
        assert structural.isdisjoint(runtime), (
            f"{family} structural-invalid cases leaked into runtime parity"
        )


def test_implementation_and_fidelity_are_explicitly_issue45_owned() -> None:
    assert set(DEFERRED_FAMILIES) == {"implementation", "fidelity"}
    assert not (set(DEFERRED_FAMILIES) & set(VALID_COVERAGE))

    for family, owner in DEFERRED_FAMILIES.items():
        manifest = _manifest(family)
        assert manifest.get("contract") == family
        assert owner == "#45"
        assert _valid_names(manifest)
        assert _application_invalid(manifest)
