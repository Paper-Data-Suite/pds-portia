"""#60 Slice 1: profile, layout and missing-provider authority tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.capture.form_catalog import (
    UnsupportedCaptureFormError,
    installed_capture_page_specs,
    resolve_capture_page_spec,
)
from portia.intake.interpretation_profiles import (
    LOCAL_CANDIDATES_V1,
    InterpretationProfileError,
    inventory_historical_layout_support,
    plan_historical_interpretation,
    resolve_interpretation_profile,
    support_for_capture_spec,
)
from portia.models import PageTargetV1, PageTargetV2

ROOT = Path(__file__).resolve().parents[1]
V2_FIXTURE = ROOT / (
    "tests/fixtures/issue_56/slice_2/valid/page-target-v2-classroom-observation.json"
)
V1_FIXTURE = ROOT / "tests/fixtures/issue_20/valid/02-page_target.json"


def _v2_for(spec_index: int) -> PageTargetV2:
    raw = json.loads(V2_FIXTURE.read_text(encoding="utf-8"))
    spec = installed_capture_page_specs()[spec_index]
    raw["template_identity"] = spec.template_identity()
    raw["entry_layout"] = spec.entry_layout()
    # Only use the Daily layouts in this helper: they share page purpose.
    return PageTargetV2(raw)


def test_profiles_are_exact_local_and_do_not_claim_unbuilt_capabilities() -> None:
    identity = LOCAL_CANDIDATES_V1.wire_identity()
    assert set(identity) == {
        "interpreter_id",
        "interpreter_version",
        "mapping_profile_id",
        "mapping_version",
    }
    assert resolve_interpretation_profile(identity) is LOCAL_CANDIDATES_V1
    assert LOCAL_CANDIDATES_V1.external_network_allowed is False
    assert LOCAL_CANDIDATES_V1.text_provider == "none"
    assert LOCAL_CANDIDATES_V1.mark_provider == "none"
    assert LOCAL_CANDIDATES_V1.manual_provider == "not_yet_implemented"
    for alteration in (
        {**identity, "interpreter_version": "latest"},
        {**identity, "interpreter_version": "2"},
        {**identity, "mapping_version": "2"},
        {**identity, "surprise": "allowed"},
        {"interpreter_id": identity["interpreter_id"]},
    ):
        with pytest.raises(InterpretationProfileError):
            resolve_interpretation_profile(alteration)


def test_all_ten_frozen_layouts_have_complete_field_support_inventory() -> None:
    specs = installed_capture_page_specs()
    matrix = inventory_historical_layout_support()
    assert len(specs) == len(matrix) == 10
    assert len({layout.form_id for layout in matrix}) == 9
    assert sum(layout.entry_count for layout in matrix) == sum(
        len(spec.entries) for spec in specs
    )
    for spec, layout in zip(specs, matrix, strict=True):
        assert dict(layout.layout_identity) == spec.template_identity()
        assert layout.context_entry_key == spec.context_entry_key
        assert tuple(e.entry_key for e in layout.entries) == spec.entry_keys
        assert layout.field_count == sum(len(e.fields) for e in spec.entries)
        for actual_entry, source_entry in zip(
            layout.entries, spec.entries, strict=True
        ):
            assert actual_entry.source_role == source_entry.source_role
            assert (
                actual_entry.permitted_mapped_record_kinds
                == source_entry.permitted_mapped_record_kinds
            )
            assert tuple(f.field_key for f in actual_entry.fields) == tuple(
                f.field_key for f in source_entry.fields
            )
            for field, source_field in zip(
                actual_entry.fields, source_entry.fields, strict=True
            ):
                assert field.rectangle == source_field.rectangle
                assert field.choices == source_field.choices
                assert field.declared_method == source_field.capture_method
                assert field.max_characters == source_field.max_characters
                assert field.automatic_availability == "unavailable"
                assert field.manual_availability == "not_yet_implemented"


def test_page_local_context_and_ambiguous_mappings_stay_noncanonical() -> None:
    matrix = inventory_historical_layout_support()
    for layout in matrix:
        context = layout.entries[0]
        assert context.entry_key == layout.context_entry_key
        assert context.mapping_disposition == "context_only"
        assert context.permitted_mapped_record_kinds == ()
    main = matrix[0]
    assert main.page_ordinal == 1
    assert main.entries[1].entry_key == "observation_01"
    assert main.entries[1].mapping_disposition == "requires_target_choice"
    assert main.entries[1].permitted_mapped_record_kinds == ("observation", "event")
    continuation = matrix[1]
    assert continuation.page_ordinal == 2
    assert continuation.entry_count == 4
    assert continuation.entries[3].entry_key == "observation_03"
    monitoring = next(
        layout for layout in matrix if layout.form_id == "focused_monitoring"
    )
    assert monitoring.entries[1].mapping_disposition == "mapping_not_yet_implemented"
    assert all(
        field.automatic_availability == "unavailable"
        for layout in matrix
        for entry in layout.entries
        for field in entry.fields
    )


def test_planning_only_exact_page_target_v2_and_historical_profile() -> None:
    plan = plan_historical_interpretation(
        _v2_for(0), profile_identity=LOCAL_CANDIDATES_V1.wire_identity()
    )
    assert plan.layout.form_id == "daily_classroom_observation"
    assert plan.layout.page_ordinal == 1
    continuation = plan_historical_interpretation(
        _v2_for(1), profile_identity=LOCAL_CANDIDATES_V1.wire_identity()
    )
    assert continuation.layout.page_ordinal == 2
    assert continuation.layout.layout_identity != plan.layout.layout_identity


def test_legacy_or_forged_layout_must_not_fall_forward() -> None:
    with pytest.raises(
        InterpretationProfileError, match="page_target_v1_not_interpretable"
    ):
        plan_historical_interpretation(
            object(), profile_identity=LOCAL_CANDIDATES_V1.wire_identity()
        )
    legacy = PageTargetV1(json.loads(V1_FIXTURE.read_text(encoding="utf-8")))
    with pytest.raises(
        InterpretationProfileError, match="page_target_v1_not_interpretable"
    ):
        plan_historical_interpretation(
            legacy, profile_identity=LOCAL_CANDIDATES_V1.wire_identity()
        )
    tampered = _v2_for(0).to_dict()
    identity = tampered["template_identity"]
    assert isinstance(identity, dict)
    identity["layout_fingerprint"] = "a" * 64
    with pytest.raises(UnsupportedCaptureFormError):
        plan_historical_interpretation(
            PageTargetV2(tampered),
            profile_identity=LOCAL_CANDIDATES_V1.wire_identity(),
        )
    with pytest.raises(UnsupportedCaptureFormError):
        resolve_capture_page_spec({"template_id": "latest"})


def test_unknown_capture_spec_object_is_rejected() -> None:
    assert support_for_capture_spec(installed_capture_page_specs()[0]).field_count > 0
    with pytest.raises(InterpretationProfileError):
        support_for_capture_spec(None)  # type: ignore[arg-type]
