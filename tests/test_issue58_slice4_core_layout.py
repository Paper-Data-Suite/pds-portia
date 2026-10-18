"""Exact printable drawing geometry without rendering/route side effects."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from portia.capture.core_form_layout import (
    CORE_FORM_DRAW_PLAN_VERSION,
    CoreFormLayoutError,
    _validate_core_form_drawing,
    plan_core_capture_form,
)
from portia.capture.form_catalog import (
    CaptureRectangle,
    UnsupportedCaptureFormError,
    capture_pages_for_form,
    resolve_capture_page_spec,
)
from portia.models import PageTargetV2

FORM_PURPOSES = (
    "focused_monitoring", "communication_log", "event_information",
    "multi_event_information", "event_evidence", "support_implementation",
    "support_process_evidence", "follow_up",
)
BASE_TARGET = Path(__file__).resolve().parents[1] / (
    "tests/fixtures/issue_56/slice_2/valid/"
    "page-target-v2-classroom-observation.json"
)


def target_for(form: str, kind: str | None = None) -> PageTargetV2:
    spec = capture_pages_for_form(form)[0]
    data = json.loads(BASE_TARGET.read_text(encoding="utf-8"))
    data["template_identity"] = spec.template_identity()
    data["entry_layout"] = spec.entry_layout()
    data["page_purpose"] = spec.page_purpose
    data["capture_mode"] = spec.capture_mode
    if kind is not None:
        data["existing_work_context"] = {
            "module_id": "portia", "class_id": data["class_id"],
            "work_kind": kind,
            "work_id": "evt_sample_01" if kind == "event" else "sup_sample_01",
            "contract_version": "2" if kind == "event" else "1",
        }
    return PageTargetV2(data)



def test_each_non_daily_form_has_a_verifiable_drawing_plan() -> None:
    for form in FORM_PURPOSES:
        drawing = plan_core_capture_form(form)
        assert drawing.version == CORE_FORM_DRAW_PLAN_VERSION
        assert drawing.spec.form_id == form
        assert drawing.spec == resolve_capture_page_spec(drawing.spec.template_identity())
        assert drawing.route_text_area == CaptureRectangle(40, 115, 400, 20)
        assert drawing.qr_area == CaptureRectangle(468, 40, 108, 108)
        assert drawing.title.text == drawing.spec.title
        assert drawing.footer.text == "Portia capture form"
        assert len(drawing.instructions) in (1, 2)
        assert tuple(entry.entry_key for entry in drawing.entries) == drawing.spec.entry_keys
        _validate_core_form_drawing(drawing)
        assert not hasattr(drawing, "payload")
        assert not hasattr(drawing, "locator")
        assert not hasattr(drawing, "printed_at")
        assert not hasattr(drawing, "student")


def test_all_writable_regions_and_unchecked_choices_are_exact() -> None:
    for form in FORM_PURPOSES:
        drawing = plan_core_capture_form(form)
        original = {
            (entry.entry_key, field.field_key, field.region_key, field.rectangle)
            for entry in drawing.spec.entries for field in entry.fields
        }
        drawn = {
            (field.entry_key, field.field_key, field.region_key, field.rectangle)
            for field in drawing.field_drawings
        }
        assert original == drawn
        for field in drawing.field_drawings:
            assert field.label.text
            assert field.label.max_width <= field.rectangle.width
            if field.mark_options:
                assert field.writing_rules == ()
                assert all(not hasattr(option, "checked") for option in field.mark_options)
                assert all(option.label.text for option in field.mark_options)
            else:
                assert field.writing_rules
                for rule in field.writing_rules:
                    assert field.rectangle.x < rule.x_start < rule.x_end < field.rectangle.right
                    assert field.rectangle.y < rule.y < field.rectangle.bottom


def test_required_context_and_separate_page_index_respect_exact_target() -> None:
    for form in FORM_PURPOSES:
        drawing = plan_core_capture_form(form)
        target = target_for(
            form,
            "event" if form == "event_evidence"
            else "support_process" if form == "support_process_evidence"
            else None,
        )
        drawing.assert_target_exact(target)
        mutated = target.to_dict()
        mutated["page_index"] = 3
        # Template-local page ordinal != batch logical page_index.
        drawing.assert_target_exact(PageTargetV2(mutated))


def test_no_daily_substitution_and_unavailable_forms_fail_explicitly() -> None:
    with pytest.raises(CoreFormLayoutError, match="multi-role"):
        plan_core_capture_form("daily_classroom_observation")
    for missing in ("fidelity", "reentry", "repair", "other"):
        with pytest.raises(UnsupportedCaptureFormError):
            plan_core_capture_form(missing)


def test_tampering_with_drawing_or_semantics_fails_closed() -> None:
    draw = plan_core_capture_form("communication_log")
    with pytest.raises(CoreFormLayoutError, match="heading"):
        _validate_core_form_drawing(
            replace(draw, title=replace(draw.title, text="Contact was successful"))
        )
    with pytest.raises(CoreFormLayoutError, match="fallback"):
        _validate_core_form_drawing(
            replace(draw, route_text_area=CaptureRectangle(45, 115, 400, 20))
        )
    first = draw.entries[0]
    field = replace(first.fields[0], region_key="wrong_region")
    altered_entry = replace(first, fields=(field, *first.fields[1:]))
    with pytest.raises(CoreFormLayoutError, match="field drawing"):
        _validate_core_form_drawing(replace(draw, entries=(altered_entry, *draw.entries[1:])))
    changed = replace(draw.spec, title="Reinterpreted form")
    with pytest.raises(CoreFormLayoutError, match="frozen installed history"):
        _validate_core_form_drawing(replace(draw, spec=changed))
