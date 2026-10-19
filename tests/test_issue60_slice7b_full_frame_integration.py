"""#60 Slice 7B: full-frame crops are verified and consume existing providers."""

from __future__ import annotations

from dataclasses import replace

import pytest
from test_issue60_slice2b_measured_regions import SYNTHETIC_ROUTE, _page
from test_issue60_slice7a_full_frame_registration import QR, _scan

from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake.historical_page_regions import HistoricalPageError
from portia.intake.interpretation_generations import _check_fields
from portia.intake.interpretation_profiles import (
    LOCAL_ASSISTED_MARKS_V1,
    LOCAL_MARKS_V1,
)
from portia.intake.local_mark_candidates import (
    LocalRecognitionError,
    interpret_registered_fields,
)
from portia.intake.manual_text_candidates import (
    ManualTextSelection,
    add_one_manual_text,
)
from portia.intake.measured_regions import (
    QUALIFIED_REGISTRATION_METHODS,
    measure_and_extract,
)

cv2 = pytest.importorskip("cv2")
pytest.importorskip("numpy")
pytest.importorskip("qrcode")


def test_fullframe_office_scan_reaches_exact_crops_and_mark_classifier() -> None:
    spec = installed_capture_page_specs()[0]
    regions = measure_and_extract(_scan(), spec, QR)
    assert regions.registration.method == "measured_fullframe_qr_and_field_frames_v1"
    expected = [
        (entry.entry_key, field.field_key, field.region_key)
        for entry in spec.entries
        for field in entry.fields
    ]
    assert [
        (r.entry_key, r.field_key, r.region_key) for r in regions.fields
    ] == expected
    assert all(len(r.pixels) == r.width * r.height for r in regions.fields)
    marks = interpret_registered_fields(regions, spec)
    assert marks.profile is LOCAL_MARKS_V1
    assert marks.registration_method == regions.registration.method
    assert marks.source_page_number == 1
    assert marks.interpretation_status == "partial"  # no handwriting OCR
    _check_fields(marks, spec, LOCAL_MARKS_V1)


def test_assisted_transcription_accepts_qualified_fullframe_baseline() -> None:
    spec = installed_capture_page_specs()[0]
    marks = interpret_registered_fields(measure_and_extract(_scan(), spec, QR), spec)
    selected = ManualTextSelection(
        "session_context", "session_date", "Unconfirmed notes"
    )
    assisted = add_one_manual_text(marks, spec, selected)
    assert assisted.profile is LOCAL_ASSISTED_MARKS_V1
    assert assisted.registration_method == "measured_fullframe_qr_and_field_frames_v1"
    _check_fields(assisted, spec, LOCAL_ASSISTED_MARKS_V1)


def test_legacy_border_registration_stays_unchanged() -> None:
    spec = installed_capture_page_specs()[0]
    regions = measure_and_extract(_page(), spec, SYNTHETIC_ROUTE)
    assert regions.registration.method == "measured_sheet_boundary_and_exact_qr_v1"
    assert regions.registration.method in QUALIFIED_REGISTRATION_METHODS


def test_qr_only_fullframe_cannot_produce_field_crops() -> None:
    with pytest.raises(
        HistoricalPageError, match="fullframe_independent_landmarks_unmeasured"
    ):
        measure_and_extract(_scan(frames=False), installed_capture_page_specs()[0], QR)


def test_wrong_route_fullframe_never_produces_crops() -> None:
    with pytest.raises(HistoricalPageError, match="registration_qr_route_mismatch"):
        measure_and_extract(
            _scan(qr_value=QR.replace("rt_synthetic_01", "rt_wrong")),
            installed_capture_page_specs()[0],
            QR,
        )


def test_old_blank_page_diagnostic_is_preserved() -> None:
    from portia.intake.historical_page_regions import BoundedPageRaster

    white = BoundedPageRaster(640, 880, 1, b"\xff" * (640 * 880))
    with pytest.raises(HistoricalPageError, match="page_border_unmeasured"):
        measure_and_extract(white, installed_capture_page_specs()[0], QR)


def test_unqualified_registration_is_rejected_by_mark_classifier() -> None:
    spec = installed_capture_page_specs()[0]
    regions = measure_and_extract(_scan(), spec, QR)
    damaged = replace(
        regions, registration=replace(regions.registration, method="guess")
    )
    with pytest.raises(
        LocalRecognitionError, match="unqualified_registration_provider"
    ):
        interpret_registered_fields(damaged, spec)
