"""Freeze Issue #46 Follow-Up production parity against Issue #19 fixtures."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from portia.models import parse_portia_record

FIXTURE_ROOT = Path("tests/schema_validation/fixtures/issue-19/follow-up")
WORKFLOW_TEST = Path("tests/test_workflow_follow_ups.py")
# Coverage is not a second fixture oracle: its key set is mechanically required
# to equal manifest["valid"] U manifest["application_invalid"] below.
COVERAGE: dict[str, str] = {
    "event-scheduled-date-only.json": (
        "test_create_load_list_and_current_event_follow_up"
    ),
    "event-scheduled-exact-time.json": (
        "test_follow_up_accepts_frozen_planned_timing_forms"
    ),
    "event-completed-produced-communication.json": (
        "test_completion_can_append_reviewed_and_produced_exact_relations"
    ),
    "support-scheduled-date-window.json": (
        "test_follow_up_accepts_frozen_planned_timing_forms"
    ),
    "support-scheduled-exact-window.json": (
        "test_follow_up_accepts_frozen_planned_timing_forms"
    ),
    "support-completed-review-disposition.json": (
        "test_support_review_completion_can_attach_disposition_without_mutating_root"
    ),
    "support-completed-reviewed-and-produced.json": (
        "test_completion_can_append_reviewed_and_produced_exact_relations"
    ),
    "support-other-purpose-with-detail.json": (
        "test_support_other_purpose_with_detail_is_accepted"
    ),
    "support-proposed-import.json": (
        "test_proposed_imported_support_follow_up_remains_exactly_readable"
    ),
    "event-timing-correction-successor.json": (
        "test_follow_up_timing_correction_supersedes_exact_predecessor"
    ),
    "active-event-roster-student-owner.json": (
        "test_active_event_follow_up_rejects_roster_student_owner"
    ),
    "active-event-descriptive-owner.json": (
        "test_active_event_follow_up_rejects_descriptive_owner"
    ),
    "active-event-unidentified-owner.json": (
        "test_active_event_follow_up_rejects_unidentified_owner"
    ),
    "active-import-without-review.json": (
        "test_active_imported_follow_up_requires_accepted_review_history"
    ),
    "updated-before-created.json": (
        "test_follow_up_rejects_updated_before_created"
    ),
    "date-window-ends-before-start.json": (
        "test_follow_up_rejects_reversed_date_window"
    ),
    "exact-window-ends-before-start.json": (
        "test_follow_up_rejects_reversed_exact_window"
    ),
    "produced-record-cross-work.json": (
        "test_produced_relation_must_remain_same_work"
    ),
    "follow-up-to-non-follow-up.json": (
        "test_follow_up_to_role_requires_follow_up_contract"
    ),
    "self-related-record.json": (
        "test_follow_up_rejects_self_related_record"
    ),
    "support-owner-without-operational-context.json": (
        "test_supported_person_context_does_not_become_follow_up_owner"
    ),
    "self-supersession.json": (
        "test_current_use_revalidates_bad_preexisting_supersession_topology"
    ),
    "ordinary-correction-cross-work.json": (
        "test_follow_up_ordinary_correction_cannot_cross_work_roots"
    ),
    "duplicate-consolidation-one-predecessor.json": (
        "test_follow_up_duplicate_consolidation_rejects_one_predecessor"
    ),
}

# These are the production regexes asserted by the mapped runtime tests.
# The combined Issue #19 guard can later read this mapping without copying the
# Issue #19 fixture lists.
EXPECTED_ERRORS: dict[str, str] = {
    "active-event-roster-student-owner.json": (
        "Follow-Up owner cannot use roster-student identity as operational authority"
    ),
    "active-event-descriptive-owner.json": (
        "current Follow-Up owner requires an identified operational human"
    ),
    "active-event-unidentified-owner.json": (
        "current Follow-Up owner requires an identified operational human"
    ),
    "active-import-without-review.json": (
        "paper/import activation requires accepted review history"
    ),
    "updated-before-created.json": (
        "Follow-Up updated_at cannot precede Follow-Up created_at"
    ),
    "date-window-ends-before-start.json": (
        "Follow-Up ends_on cannot precede Follow-Up starts_on"
    ),
    "exact-window-ends-before-start.json": (
        "Follow-Up ends_at cannot precede Follow-Up starts_at"
    ),
    "produced-record-cross-work.json": (
        "Follow-Up related_records role 'produced' must remain in the owning work"
    ),
    "follow-up-to-non-follow-up.json": (
        "Follow-Up related_records role 'follow_up_to' is incompatible"
    ),
    "self-related-record.json": (
        "Follow-Up related_records cannot reference the current record itself"
    ),
    "support-owner-without-operational-context.json": (
        r"Follow-Up owner requires Support Process Participant context "
        r"in \{coordinator, provider_or_collaborator\}"
    ),
    "self-supersession.json": "follow_up cannot supersede itself",
    "ordinary-correction-cross-work.json": (
        "ordinary follow_up correction cannot cross work roots"
    ),
    "duplicate-consolidation-one-predecessor.json": (
        "duplicate consolidation needs two follow_up predecessors"
    ),
}


def _manifest() -> dict[str, object]:
    value = json.loads(
        (FIXTURE_ROOT / "manifest.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def _names(manifest: dict[str, object], key: str) -> set[str]:
    values = manifest.get(key)
    assert isinstance(values, list)
    assert all(isinstance(item, str) for item in values)
    return set(values)


def _workflow_test_nodes() -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    source = WORKFLOW_TEST.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(WORKFLOW_TEST))
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    }


def _raises_match_values(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    values: set[str] = set()
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.Call):
            continue
        function = candidate.func
        is_raises = (
            isinstance(function, ast.Attribute)
            and function.attr == "raises"
        ) or (
            isinstance(function, ast.Name)
            and function.id == "raises"
        )
        if not is_raises:
            continue
        for keyword in candidate.keywords:
            if (
                keyword.arg == "match"
                and isinstance(keyword.value, ast.Constant)
                and isinstance(keyword.value.value, str)
            ):
                values.add(keyword.value.value)
    return values


def _load_fixture(folder: str, filename: str) -> dict[str, object]:
    value = json.loads(
        (FIXTURE_ROOT / folder / filename).read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_issue19_follow_up_manifest_is_the_exact_frozen_case_oracle() -> None:
    manifest = _manifest()
    assert manifest["manifest_version"] == "1"
    assert manifest["issue"] == 19
    assert manifest["contract"] == "follow_up"
    assert manifest["version"] == "1"

    valid = _names(manifest, "valid")
    application_invalid = _names(manifest, "application_invalid")
    structural_invalid = _names(manifest, "invalid")

    assert len(valid) == 10
    assert len(application_invalid) == 14
    assert len(structural_invalid) == 13


def test_issue46_follow_up_runtime_coverage_is_exactly_24_schema_valid_cases() -> None:
    manifest = _manifest()
    valid = _names(manifest, "valid")
    application_invalid = _names(manifest, "application_invalid")

    assert set(COVERAGE) == valid | application_invalid
    assert len(COVERAGE) == 24


def test_every_follow_up_runtime_case_maps_to_a_real_production_test() -> None:
    test_names = set(_workflow_test_nodes())
    assert set(COVERAGE.values()) <= test_names


def test_follow_up_application_invalid_cases_freeze_semantic_runtime_errors() -> None:
    manifest = _manifest()
    application_invalid = _names(manifest, "application_invalid")
    nodes = _workflow_test_nodes()

    assert set(EXPECTED_ERRORS) == application_invalid
    for scenario, expected_error in EXPECTED_ERRORS.items():
        assert expected_error.strip()
        target = COVERAGE[scenario]
        asserted_matches = _raises_match_values(nodes[target])
        assert expected_error in asserted_matches, (
            f"{scenario} maps to {target}, but that production test does not "
            f"assert the frozen error regex {expected_error!r}"
        )


def test_structural_invalid_follow_up_fixtures_stay_outside_runtime_parity() -> None:
    manifest = _manifest()
    structural_invalid = _names(manifest, "invalid")
    assert structural_invalid.isdisjoint(COVERAGE)
    assert len(structural_invalid) == 13


def test_all_24_schema_valid_follow_up_fixtures_reach_the_runtime_model() -> None:
    manifest = _manifest()
    for folder, key in (
        ("valid", "valid"),
        ("application-invalid", "application_invalid"),
    ):
        for filename in sorted(_names(manifest, key)):
            value = _load_fixture(folder, filename)
            record = parse_portia_record("follow_up", "1", value)
            assert record.contract == "follow_up"
            assert record.to_dict()["schema_version"] == "1"
            assert record.logical_id == value["follow_up_id"]
