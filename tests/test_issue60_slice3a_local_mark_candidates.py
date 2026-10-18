"""#60 Slice 3A: source-faithful checkbox candidates; synthetic pages only."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image, ImageDraw

from portia.capture.form_catalog import CaptureField, installed_capture_page_specs
from portia.intake.interpretation_profiles import (
    LOCAL_CANDIDATES_V1,
    LOCAL_MARKS_V1,
    InterpretationProfileError,
    resolve_interpretation_profile,
)
from portia.intake.local_mark_candidates import (
    FieldCandidate,
    FileLocalMarkCandidateService,
    LocalRecognitionError,
    interpret_registered_fields,
)
from portia.intake.measured_regions import (
    FieldRegionPixels,
    MeasuredPageRegions,
    PageRegistration,
)


def _choice_field() -> CaptureField:
    spec = installed_capture_page_specs()[0]
    return next(
        field
        for entry in spec.entries
        for field in entry.fields
        if field.field_type == "choice"
    )


def _region(
    entry_key: str,
    field: CaptureField,
    marks: tuple[int, ...] = (),
    *,
    missing_frame: bool = False,
    faint: tuple[int, ...] = (),
    scale: int = 2,
) -> FieldRegionPixels:
    rect = field.rectangle
    image = Image.new("L", (rect.width * scale, rect.height * scale), 255)
    draw = ImageDraw.Draw(image)
    if field.field_type == "choice":
        unit = (rect.width - 12) // len(field.choices)
        for index, _ in enumerate(field.choices):
            x0, y0 = (6 + index * unit) * scale, 13 * scale
            x1, y1 = x0 + 8 * scale, y0 + 8 * scale
            if not missing_frame:
                draw.rectangle((x0, y0, x1, y1), outline=50, width=2)
            if index in marks:
                draw.line((x0 + 3, y0 + 3, x1 - 3, y1 - 3), fill=25, width=3)
                draw.line((x0 + 3, y1 - 3, x1 - 3, y0 + 3), fill=25, width=3)
            if index in faint:
                draw.line((x0 + 4, y0 + 4, x1 - 4, y1 - 4), fill=176, width=3)
    return FieldRegionPixels(
        entry_key,
        field.field_key,
        field.region_key,
        image.width,
        image.height,
        image.tobytes(),
    )


def _page(
    marks: tuple[int, ...] = (),
    *,
    missing_frame: bool = False,
    faint: tuple[int, ...] = (),
    scale: int = 2,
) -> MeasuredPageRegions:
    spec = installed_capture_page_specs()[0]
    fields = tuple(
        _region(
            entry.entry_key,
            field,
            marks=marks,
            missing_frame=missing_frame,
            faint=faint,
            scale=scale,
        )
        for entry in spec.entries
        for field in entry.fields
    )
    return MeasuredPageRegions(
        2,
        spec.layout_fingerprint,
        PageRegistration(
            method="measured_sheet_boundary_and_exact_qr_v1",
            qr_residual_pixels=0.9,
            page_width_pixels=1200.0,
            page_height_pixels=1550.0,
            page_quad=((20.0, 20.0), (1220.0, 20.0), (1220.0, 1570.0), (20.0, 1570.0)),
        ),
        fields,
    )


def _mark_result(page: MeasuredPageRegions) -> FieldCandidate:
    spec = installed_capture_page_specs()[0]
    return next(
        field
        for entry in interpret_registered_fields(page, spec).entries
        for field in entry.fields
        if field.capture_method == "mark_recognition"
    )


def test_versioned_local_mark_profile_is_explicit_and_old_profile_is_frozen() -> None:
    assert LOCAL_CANDIDATES_V1.mark_provider == "none"
    assert LOCAL_MARKS_V1.mark_provider == "local_checkbox_v1"
    assert LOCAL_MARKS_V1.text_provider == "none"
    assert not LOCAL_MARKS_V1.external_network_allowed
    assert (
        resolve_interpretation_profile(LOCAL_MARKS_V1.wire_identity()) is LOCAL_MARKS_V1
    )
    assert (
        resolve_interpretation_profile(LOCAL_CANDIDATES_V1.wire_identity())
        is LOCAL_CANDIDATES_V1
    )
    with pytest.raises(InterpretationProfileError):
        resolve_interpretation_profile(
            {**LOCAL_MARKS_V1.wire_identity(), "interpreter_version": "latest"}
        )


def test_one_printed_mark_returns_only_the_exact_choice_token() -> None:
    field = _choice_field()
    observed = _mark_result(_page((1,)))
    assert observed.state == "candidate_detected"
    assert observed.literal == field.choices[1]
    assert observed.to_wire() == {
        "capture_method": "mark_recognition",
        "region_key": field.region_key,
        "recognition_state": "candidate_detected",
        "candidate_literal": field.choices[1],
    }


def test_two_marks_require_explicit_ambiguous_alternatives_not_a_winner() -> None:
    field = _choice_field()
    detected = _mark_result(_page((0, 1)))
    assert detected.state == "ambiguous"
    assert detected.literal is None
    assert detected.alternatives == field.choices[:2]
    assert detected.to_wire()["alternatives"] == [
        {"candidate_literal": value} for value in field.choices[:2]
    ]


def test_unmarked_requires_all_checkbox_frames_and_clean_interiors() -> None:
    observed = _mark_result(_page())
    assert observed.state == "unmarked"
    assert observed.literal is None
    assert "candidate_literal" not in observed.to_wire()
    assert "normalized_value" not in observed.to_wire()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"missing_frame": True},
        {"faint": (0,)},
        {"scale": 1},
        {"marks": (1,), "faint": (2,)},
    ],
)
def test_no_guess_on_missing_frame_faint_marks_or_low_resolution(
    kwargs: dict[str, Any],
) -> None:
    assert _mark_result(_page(**kwargs)).state == "unreadable"


def test_text_is_never_auto_transcribed_or_called_blank() -> None:
    spec = installed_capture_page_specs()[0]
    result = interpret_registered_fields(_page((0,)), spec)
    assert result.profile is LOCAL_MARKS_V1
    assert result.interpretation_status == "partial"
    assert result.limitation_codes == ("text_provider_unavailable",)
    assert [entry.entry_key for entry in result.entries] == [
        entry.entry_key for entry in spec.entries
    ]
    for entry in result.entries:
        for field in entry.fields:
            if field.capture_method != "mark_recognition":
                assert field.state == "unreadable"
                assert "candidate_literal" not in field.to_wire()
    assert not any("mapped_record_kind" in item for item in result.entry_map().values())
    assert not any(
        "confidence" in field.to_wire()
        for entry in result.entries
        for field in entry.fields
    )


def test_every_installed_layout_has_all_declared_slots_with_no_name_guessing() -> None:
    for spec in installed_capture_page_specs():
        fields = tuple(_region(e.entry_key, f) for e in spec.entries for f in e.fields)
        page = replace(
            _page(), layout_fingerprint=spec.layout_fingerprint, fields=fields
        )
        readout = interpret_registered_fields(page, spec)
        assert tuple(readout.entry_map()) == tuple(e.entry_key for e in spec.entries)
        assert sum(len(entry.fields) for entry in readout.entries) == len(fields)
        assert all(
            item.state in {"candidate", "unreadable", "blank"}
            for item in readout.entries
        )


def test_mismatched_historical_or_duplicate_field_inventory_fails_closed() -> None:
    spec = installed_capture_page_specs()[0]
    page = _page()
    with pytest.raises(LocalRecognitionError, match="layout_fingerprint_conflict"):
        interpret_registered_fields(replace(page, layout_fingerprint="a" * 64), spec)
    with pytest.raises(LocalRecognitionError, match="field_identity_conflict"):
        interpret_registered_fields(
            replace(page, fields=page.fields[:-1] + (page.fields[0],)), spec
        )
    with pytest.raises(
        LocalRecognitionError, match="unqualified_registration_provider"
    ):
        interpret_registered_fields(
            replace(
                page,
                registration=replace(
                    page.registration, method="guessed_from_dimensions"
                ),
            ),
            spec,
        )


def test_invalid_confidence_free_field_status_cannot_carry_wrong_literal() -> None:
    with pytest.raises(LocalRecognitionError):
        FieldCandidate("cue", "region", "mark_recognition", "unmarked", literal="false")
    with pytest.raises(LocalRecognitionError):
        FieldCandidate(
            "cue", "region", "mark_recognition", "ambiguous", alternatives=("x", "x")
        )


def test_production_service_uses_authorized_reader_and_rechecks_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from portia.intake import local_mark_candidates as module

    spec = installed_capture_page_specs()[0]
    auth = object()
    page = _page((1,))
    calls: list[tuple[str, object]] = []
    receipt = SimpleNamespace(to_dict=lambda: {"page_record_id": "prec_test"})
    retained = SimpleNamespace(page_identity=lambda n: ("scan_test", n))
    source = SimpleNamespace(
        plan=SimpleNamespace(
            layout=SimpleNamespace(
                layout_identity=tuple(spec.template_identity().items())
            )
        ),
        receipt=receipt,
        retained=retained,
        source_page_number=2,
    )

    class FakePages:
        def resolve(self, *args: object, **kwargs: object) -> object:
            calls.append(("authorize_and_resolve", kwargs["authorization"]))
            return source

    class FakeMeasured:
        def __init__(self, root: object) -> None:
            self.pages = FakePages()

        def extract(self, *args: object, **kwargs: object) -> MeasuredPageRegions:
            calls.append(("extract", kwargs["authorization"]))
            return page

    monkeypatch.setattr(module, "FileMeasuredRegionService", FakeMeasured)
    service = FileLocalMarkCandidateService("synthetic_unused_root")
    answer = service.interpret(
        "class_test",
        "cbat_test",
        "prec_test",
        authorization=auth,
        profile_identity=LOCAL_MARKS_V1.wire_identity(),
    )
    assert answer.profile is LOCAL_MARKS_V1
    assert [name for name, _ in calls] == [
        "authorize_and_resolve",
        "extract",
        "authorize_and_resolve",
    ]
    assert all(actor is auth for _name, actor in calls)
    with pytest.raises(
        LocalRecognitionError, match="unsupported_mark_interpreter_profile"
    ):
        service.interpret(
            "class_test",
            "cbat_test",
            "prec_test",
            authorization=auth,
            profile_identity=LOCAL_CANDIDATES_V1.wire_identity(),
        )
