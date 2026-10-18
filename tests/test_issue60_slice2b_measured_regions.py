"""#60 Slice 2B: QR-corroborated measured sheet alignment and ephemeral crops.

All printed pages and payloads are synthetic. No real student paper is stored.
"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake.historical_page_regions import BoundedPageRaster, HistoricalPageError
from portia.intake.measured_regions import measure_and_extract

# No hidden cloud provider or new mandatory Portia install dependency.
cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
qrcode = pytest.importorskip("qrcode")

SYNTHETIC_ROUTE = "PDS2|m=portia|c=class_english10_p2|w=cbat_batch_01|r=rt_synthetic_01"


def _page(
    *,
    payload: str = SYNTHETIC_ROUTE,
    corners: tuple[tuple[int, int], ...] = (
        (100, 100),
        (1240, 75),
        (1215, 1680),
        (85, 1735),
    ),
    background: int = 40,
    ink: bool = False,
) -> BoundedPageRaster:
    spec = installed_capture_page_specs()[0]
    scale = 3
    print_image = Image.new("L", (612 * scale, 792 * scale), 255)
    draw = ImageDraw.Draw(print_image)
    for entry in spec.entries:
        for field in entry.fields:
            box = field.rectangle
            draw.rectangle(
                (box.x * scale, box.y * scale, box.right * scale, box.bottom * scale),
                outline=180,
                width=2,
            )
    if ink:
        first_field = spec.entries[0].fields[0].rectangle
        cx = (first_field.x + first_field.width // 2) * scale
        cy = (first_field.y + first_field.height // 2) * scale
        draw.ellipse((cx - 18, cy - 18, cx + 18, cy + 18), fill=0)
    from qrcode.constants import ERROR_CORRECT_M

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_M, box_size=1, border=4)
    qr.add_data(payload, optimize=0)
    qr.make(fit=True)
    modules = np.asarray(qr.get_matrix(), dtype=np.uint8)
    qr_image = Image.fromarray(np.uint8((1 - modules) * 255)).resize(
        (108 * scale, 108 * scale), Image.Resampling.NEAREST
    )
    print_image.paste(qr_image, (468 * scale, 40 * scale))
    raster = cv2.warpPerspective(
        np.asarray(print_image),
        cv2.getPerspectiveTransform(
            np.float32(
                [[0, 0], [612 * scale, 0], [612 * scale, 792 * scale], [0, 792 * scale]]
            ),
            np.float32(corners),
        ),
        (1400, 1850),
        flags=cv2.INTER_LINEAR,
        borderValue=background,
    )
    return BoundedPageRaster(1400, 1850, 3, raster.tobytes())


def test_measured_qr_and_independent_page_border_expose_only_declared_regions() -> None:
    spec = installed_capture_page_specs()[0]
    result = measure_and_extract(_page(), spec, SYNTHETIC_ROUTE)
    assert result.source_page_number == 3
    assert result.layout_fingerprint == spec.layout_fingerprint
    assert result.registration.method == "measured_sheet_boundary_and_exact_qr_v1"
    assert result.registration.qr_residual_pixels < 8.0
    assert result.field_count == sum(len(entry.fields) for entry in spec.entries)
    expected = [
        (entry.entry_key, field.field_key, field.region_key)
        for entry in spec.entries
        for field in entry.fields
    ]
    observed = [(r.entry_key, r.field_key, r.region_key) for r in result.fields]
    assert observed == expected
    assert all(len(r.pixels) == r.width * r.height for r in result.fields)
    assert "pixels=b" not in repr(result)
    assert "pixels=b" not in repr(result.fields[0])


def test_actual_ink_inside_declared_field_survives_coordinate_warp() -> None:
    spec = installed_capture_page_specs()[0]
    result = measure_and_extract(_page(ink=True), spec, SYNTHETIC_ROUTE)
    first = result.fields[0]
    gray = np.frombuffer(first.pixels, dtype=np.uint8).reshape(
        first.height, first.width
    )
    center = gray[
        first.height // 2 - 5 : first.height // 2 + 6,
        first.width // 2 - 5 : first.width // 2 + 6,
    ]
    assert center.size == 121
    assert float(np.median(center)) < 80


def test_straight_full_page_is_measured_not_inferred_from_raster_size() -> None:
    spec = installed_capture_page_specs()[0]
    raster = _page(corners=((100, 100), (1320, 100), (1320, 1680), (100, 1680)))
    result = measure_and_extract(raster, spec, SYNTHETIC_ROUTE)
    assert result.field_count > 0
    assert result.registration.page_width_pixels > 1000


def test_white_background_full_frame_has_no_measured_paper_boundary() -> None:
    spec = installed_capture_page_specs()[0]
    original = _page()
    no_border = BoundedPageRaster(
        original.width,
        original.height,
        original.source_page_number,
        b"\xff" * (original.width * original.height),
    )
    with pytest.raises(HistoricalPageError, match="page_border_unmeasured"):
        measure_and_extract(no_border, spec, SYNTHETIC_ROUTE)


def test_correct_paper_with_wrong_qr_is_never_registered() -> None:
    spec = installed_capture_page_specs()[0]
    raster = _page(
        payload="PDS2|m=portia|c=class_english10_p2|w=cbat_batch_01|r=rt_other_01"
    )
    with pytest.raises(HistoricalPageError, match="registration_qr_route_mismatch"):
        measure_and_extract(raster, spec, SYNTHETIC_ROUTE)


def test_cropped_page_edges_are_not_reconstructed_speculatively() -> None:
    spec = installed_capture_page_specs()[0]
    raster = _page(corners=((-50, 80), (1250, 75), (1230, 1720), (-40, 1750)))
    with pytest.raises(HistoricalPageError):
        measure_and_extract(raster, spec, SYNTHETIC_ROUTE)


def test_no_region_bytes_ever_enter_repr_and_empty_provider_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from portia.intake import measured_regions as module

    def absent(_name: str) -> object:
        raise ImportError("synthetic unavailable backend")

    synthetic = _page()
    monkeypatch.setattr(module.importlib, "import_module", absent)
    with pytest.raises(
        HistoricalPageError, match="local_registration_backend_unavailable"
    ):
        measure_and_extract(
            synthetic, installed_capture_page_specs()[0], SYNTHETIC_ROUTE
        )


def test_cannot_extract_caller_supplied_layout_or_raster_representation() -> None:
    with pytest.raises(HistoricalPageError, match="invalid_registration_inputs"):
        measure_and_extract(
            object(), installed_capture_page_specs()[0], SYNTHETIC_ROUTE
        )  # type: ignore[arg-type]
    with pytest.raises(HistoricalPageError, match="invalid_expected_pds2"):
        measure_and_extract(
            _page(), installed_capture_page_specs()[0], "invented route"
        )
