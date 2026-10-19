"""#60 Slice 7A: synthetic scanner-full-frame landmark qualification only."""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake.full_frame_registration import qualify_full_frame
from portia.intake.historical_page_regions import BoundedPageRaster, HistoricalPageError

cv2 = pytest.importorskip("cv2")
pytest.importorskip("numpy")
qrcode = pytest.importorskip("qrcode")

QR = "PDS2|m=portia|c=class_english10_p2|w=cbat_batch_01|r=rt_synthetic_01"


def _scan(
    *, frames: bool = True, qr_value: str = QR, rotate: bool = False
) -> BoundedPageRaster:
    """Synthetic 200%-scale flatbed raster without any surrounding dark border."""
    spec = installed_capture_page_specs()[0]
    picture = Image.new("L", (1224, 1584), 255)
    pen = ImageDraw.Draw(picture)
    if frames:
        for entry in spec.entries:
            for f in entry.fields:
                b = f.rectangle
                pen.rectangle(
                    (b.x * 2, b.y * 2, b.right * 2, b.bottom * 2),
                    outline=182,
                    width=2,
                )
    code = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4
    )
    code.add_data(qr_value, optimize=0)
    code.make(fit=True)
    qr = code.make_image(fill_color="black", back_color="white").convert("L")
    qr = qr.resize((216, 216), resample=Image.Resampling.NEAREST)
    picture.paste(qr, (936, 80))
    if rotate:
        picture = picture.transpose(Image.Transpose.ROTATE_90)
    return BoundedPageRaster(picture.width, picture.height, 1, picture.tobytes())


def test_white_office_scan_with_printed_frames_is_measurable() -> None:
    evidence = qualify_full_frame(_scan(), installed_capture_page_specs()[0], QR)
    assert evidence.registration.method == "measured_fullframe_qr_and_field_frames_v1"
    assert len(evidence.qualified_frames) >= 3
    assert evidence.registration.page_width_pixels > 800
    assert evidence.registration.page_height_pixels > 1200


def test_qr_only_white_page_is_not_registered() -> None:
    with pytest.raises(HistoricalPageError, match="independent_landmarks_unmeasured"):
        qualify_full_frame(_scan(frames=False), installed_capture_page_specs()[0], QR)


def test_wrong_qr_never_registers_as_an_exact_target() -> None:
    with pytest.raises(HistoricalPageError, match="registration_qr_route_mismatch"):
        qualify_full_frame(
            _scan(qr_value=QR.replace("rt_synthetic_01", "rt_different")),
            installed_capture_page_specs()[0],
            QR,
        )


def test_white_page_cannot_claim_history_from_different_layout() -> None:
    first, second = installed_capture_page_specs()[:2]
    if first.layout_fingerprint == second.layout_fingerprint:
        pytest.skip("installed historical fingerprints should differ")
    with pytest.raises(HistoricalPageError):
        qualify_full_frame(_scan(), second, QR)


def test_rotated_fullframe_scan_is_independently_registered() -> None:
    evidence = qualify_full_frame(
        _scan(rotate=True), installed_capture_page_specs()[0], QR
    )
    assert len(evidence.qualified_frames) >= 3
