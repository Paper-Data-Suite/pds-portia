"""Issue #58 Slice 3: exact, source-faithful daily/continuation draw plans."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from portia.capture.form_catalog import (
    CaptureRectangle,
    capture_pages_for_form,
    resolve_capture_page_spec,
)
from portia.capture.observation_layout import (
    DRAW_PLAN_VERSION,
    MAX_CONTINUATION_PAGES,
    ObservationLayoutError,
    TextRun,
    _validate_page_drawing,
    plan_daily_classroom_observation,
)
from portia.models import PageTargetV2

ROOT = Path(__file__).resolve().parents[1]


def target(page: Any, *, page_index: int | None = None) -> PageTargetV2:
    page_spec = page.spec
    actual_index = page.page_index if page_index is None else page_index
    path = ROOT / (
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    data["template_identity"] = page_spec.template_identity()
    data["entry_layout"] = page_spec.entry_layout()
    data["page_index"] = actual_index
    data["page_target_id"] = f"ptgt_slice3_page_{actual_index:02d}"
    return PageTargetV2(data)


def test_default_plan_is_one_main_page_without_domain_values() -> None:
    packet = plan_daily_classroom_observation()
    assert packet.page_count == 1
    page = packet.pages[0]
    assert page.drawing_version == DRAW_PLAN_VERSION
    assert (page.page_index, page.total_pages) == (1, 1)
    assert page.spec.page_role == "classroom_observation"
    assert page.footer.text == "Page 1 of 1"
    assert page.qr_area == CaptureRectangle(468, 40, 108, 108)
    assert page.route_text_area == CaptureRectangle(40, 115, 400, 20)
    assert not hasattr(page, "payload")
    assert not hasattr(page, "registration")
    assert not hasattr(page, "class_id")
    assert not hasattr(page, "printed_at")
    assert page.spec.layout_fingerprint == (
        "33483a2543ee50c636415a53dbca611c38b361a1d649f1e5f4533cc00aaa1518"
    )


def test_daily_session_context_is_writable_and_never_a_domain_record() -> None:
    page = plan_daily_classroom_observation().pages[0]
    assert page.entries[0].entry_key == "session_context"
    assert page.entries[0].source_role == "session_context"
    assert page.spec.entries[0].permitted_mapped_record_kinds == ()
    context = page.entries[0]
    assert {field.field_key for field in context.fields} == {
        "session_date", "session_reference", "lesson_objective",
        "lesson_steps", "session_notes",
    }
    assert all(field.field_type == "text" for field in context.fields)
    assert all(field.writing_rules for field in context.fields)
    for field in context.fields:
        assert field.source_role == "session_context"
        assert not field.mark_options


def test_observations_are_independent_and_cues_are_unmarked() -> None:
    packet = plan_daily_classroom_observation()
    page = packet.pages[0]
    assert tuple(entry.entry_key for entry in page.entries) == (
        "session_context", "observation_01", "observation_02"
    )
    for entry in page.entries[1:]:
        assert entry.source_role == "observation"
        assert entry.heading is not None and entry.heading.text.startswith("Observation ")
        assert tuple(field.field_key for field in entry.fields) == (
            "tone", "subject_reference", "observed_time", "description"
        )
        tone = entry.fields[0]
        assert tone.field_type == "choice"
        assert tone.writing_rules == ()
        assert tuple(mark.value for mark in tone.mark_options) == (
            "positive", "general", "concern"
        )
        assert all(not hasattr(mark, "checked") for mark in tone.mark_options)
        assert all(field.writing_rules for field in entry.fields[1:])
        assert all(field.entry_key == entry.entry_key for field in entry.fields)


def test_continuations_repeat_role_with_distinct_page_index_only() -> None:
    packet = plan_daily_classroom_observation(continuation_pages=3)
    assert packet.page_count == 4
    assert [page.page_index for page in packet.pages] == [1, 2, 3, 4]
    assert [page.footer.text for page in packet.pages] == [
        "Page 1 of 4", "Page 2 of 4", "Page 3 of 4", "Page 4 of 4"
    ]
    continuations = packet.pages[1:]
    assert all(page.spec.page_role == "observation_continuation" for page in continuations)
    assert all(page.spec.page_ordinal == 2 for page in continuations)
    assert all(page.spec == continuations[0].spec for page in continuations)
    assert all(page.spec.entry_keys == (
        "session_context", "observation_01", "observation_02", "observation_03"
    ) for page in continuations)
    assert continuations[0].spec.layout_fingerprint == (
        "25fe7682a2ffab06309975194405be8020bd45935357702028f8e810b2908ee9"
    )


@pytest.mark.parametrize("continuations", [-1, 9, 1.0, True, None, "2", 999])
def test_unbounded_or_untyped_continuation_count_rejected(continuations: object) -> None:
    with pytest.raises(ObservationLayoutError):
        plan_daily_classroom_observation(continuation_pages=continuations)  # type: ignore[arg-type]


def test_upper_bound_is_explicit_and_not_a_generic_form_designer() -> None:
    packet = plan_daily_classroom_observation(
        continuation_pages=MAX_CONTINUATION_PAGES
    )
    assert packet.page_count == MAX_CONTINUATION_PAGES + 1
    assert len(packet.pages[0].entries) == 3
    assert all(len(page.entries) == 4 for page in packet.pages[1:])


def test_each_drawn_field_is_an_exact_declared_historical_field() -> None:
    for page in plan_daily_classroom_observation(continuation_pages=2).pages:
        _validate_page_drawing(page)
        spec = resolve_capture_page_spec(page.spec.template_identity())
        assert spec == page.spec
        assert page.spec.canonical_bytes == spec.canonical_bytes
        assert tuple((f.entry_key, f.field_key, f.region_key) for f in page.field_drawings) == tuple(
            (entry.entry_key, field.field_key, field.region_key)
            for entry in spec.entries for field in entry.fields
        )
        for drawing in page.field_drawings:
            rect = drawing.rectangle
            assert rect.x >= 36 and rect.right <= 576
            assert rect.y >= 154 and rect.bottom <= 742
            assert drawing.label.baseline_y < rect.y + 13
            assert drawing.label.x >= rect.x and drawing.label.max_width <= rect.width
            assert all(
                rect.x < rule.x_start < rule.x_end < rect.right
                and rect.y < rule.y < rect.bottom
                for rule in drawing.writing_rules
            )
            for option in drawing.mark_options:
                assert rect.x <= option.checkbox.x < option.checkbox.right < rect.right
                assert rect.y <= option.checkbox.y < option.checkbox.bottom < rect.bottom


def test_no_header_footer_or_qr_collision_and_no_prechecked_content() -> None:
    for page in plan_daily_classroom_observation(continuation_pages=1).pages:
        header, footer, qr = (
            page.spec.header_rectangle,
            page.spec.footer_rectangle,
            page.spec.qr_rectangle,
        )
        for field in page.field_drawings:
            box = field.rectangle
            for reserved in (header, footer, qr):
                assert (
                    box.right <= reserved.x or box.x >= reserved.right
                    or box.bottom <= reserved.y or box.y >= reserved.bottom
                )
        assert page.title.x >= header.x
        assert page.title.baseline_y < header.bottom
        assert all(line.baseline_y < header.bottom for line in page.instructions)
        assert all(field.source_role in ("session_context", "observation")
                   for field in page.field_drawings)


def test_page_target_exactness_cannot_be_inferred_from_layout_alone() -> None:
    packet = plan_daily_classroom_observation(continuation_pages=1)
    for page in packet.pages:
        page.assert_target_exact(target(page))
        with pytest.raises(ObservationLayoutError, match="page_index"):
            page.assert_target_exact(target(page, page_index=100))
        other = packet.pages[1 if page.page_index == 1 else 0]
        with pytest.raises(ObservationLayoutError):
            page.assert_target_exact(target(other))


def test_explicit_layout_tampering_rejected() -> None:
    page = plan_daily_classroom_observation().pages[0]
    with pytest.raises(ObservationLayoutError, match="title/instructions"):
        _validate_page_drawing(replace(page, title=replace(page.title, text="Finding")))
    with pytest.raises(ObservationLayoutError, match="visible page label"):
        _validate_page_drawing(replace(page, footer=replace(page.footer, text="Page 9 of 9")))
    with pytest.raises(ObservationLayoutError, match="route fallback"):
        _validate_page_drawing(
            replace(page, route_text_area=CaptureRectangle(40, 110, 400, 20))
        )
    changed = replace(page.spec, title="Classified Notes")
    with pytest.raises(ObservationLayoutError, match="uninstalled/altered"):
        _validate_page_drawing(replace(page, spec=changed))
    bad = replace(page.entries[1].fields[0], field_key="determination")
    changed_entry = replace(
        page.entries[1], fields=(bad, *page.entries[1].fields[1:])
    )
    with pytest.raises(ObservationLayoutError, match="field meaning/geometry"):
        _validate_page_drawing(
            replace(page, entries=(page.entries[0], changed_entry, page.entries[2]))
        )


def test_frozen_specs_remain_unchanged_and_no_rendering_dependency() -> None:
    assert len(capture_pages_for_form("daily_classroom_observation")) == 2
    one = plan_daily_classroom_observation(continuation_pages=2)
    two = plan_daily_classroom_observation(continuation_pages=2)
    assert one == two
    assert tuple(spec.template_identity() for spec in capture_pages_for_form("daily_classroom_observation")) == (
        one.pages[0].spec.template_identity(), one.pages[1].spec.template_identity()
    )
    assert not hasattr(one, "pdf")
    assert not hasattr(one, "output_path")
    assert not hasattr(one, "route")
    assert not hasattr(one.pages[0], "qr_payload")


def test_all_text_runs_fit_conservative_print_bounds() -> None:
    for page in plan_daily_classroom_observation(continuation_pages=1).pages:
        runs: list[TextRun] = [page.title, *page.instructions, page.footer]
        for entry in page.entries:
            if entry.heading is not None:
                runs.append(entry.heading)
            for field in entry.fields:
                runs.append(field.label)
                runs.extend(mark.label for mark in field.mark_options)
        for run in runs:
            assert len(run.text) * run.font_size * 0.68 <= run.max_width
