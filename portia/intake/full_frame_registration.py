"""#60 Slice 7A: conservative, source-independent full-frame registration evidence.

This is a PURE, read-only qualification engine, not an authorized source reader.
Only FileMeasuredRegionService will later be allowed to call it after Core
custody, saved Page Record and historical layout verification. QR-only geometry
is never sufficient: distant, independently printed field frames must agree.

Do not silently substitute this profile for a historical border registration,
or call it a completed crop provider before Slice 7B integration.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from portia.capture.form_catalog import CapturePageSpec, resolve_capture_page_spec
from portia.intake.historical_page_regions import BoundedPageRaster, HistoricalPageError
from portia.intake.measured_regions import (
    PageRegistration,
    _backends,
    _expected_qr_corners,
    _qr_points,
)

_PAGE_CORNERS = ((0, 0), (612, 0), (612, 792), (0, 792))
_MAX_PIXELS = 16_000_000
_MAX_EDGE_ERROR = 0.055
_MIN_QR_SIZE = 38.0
_MAX_ANCHOR_TOLERANCE = 8
_MIN_BORDER_COVERAGE = 0.67
_MIN_FRAME_SEPARATION = 180.0


@dataclass(frozen=True, slots=True)
class FullFrameRegistrationEvidence:
    """Measured, never authoritative by itself; no image or recognized content."""

    registration: PageRegistration
    transform: Any  # ephemeral cv2 homography, must not be serialized
    qualified_frames: tuple[str, ...]


def _point_is_dark(gray: Any, x: float, y: float, tolerance: int) -> bool:
    height, width = gray.shape
    px, py = round(x), round(y)
    if not (
        tolerance <= px < width - tolerance and tolerance <= py < height - tolerance
    ):
        return False
    # The historical vector field border is faint gray, not black.
    region = gray[
        py - tolerance : py + tolerance + 1, px - tolerance : px + tolerance + 1
    ]
    return bool((region < 215).any())


def _segment_coverage(gray: Any, a: Any, b: Any, *, tolerance: int) -> float:
    # Sample away from the corners (they also contain labels/handwriting).
    points = 36
    present = 0
    for index in range(points):
        t = 0.09 + index * (0.82 / (points - 1))
        x = float(a[0] * (1 - t) + b[0] * t)
        y = float(a[1] * (1 - t) + b[1] * t)
        present += _point_is_dark(gray, x, y, tolerance)
    return present / points


def _frame_strength(gray: Any, mapped: Any, tolerance: int) -> float:
    # Two long orthogonal printable borders must actually be present.
    top = _segment_coverage(gray, mapped[0], mapped[1], tolerance=tolerance)
    side = _segment_coverage(gray, mapped[0], mapped[3], tolerance=tolerance)
    return min(top, side)


def _candidate_frames(
    gray: Any, H: Any, spec: CapturePageSpec, cv2: Any, np: Any, tolerance: int
) -> tuple[tuple[str, float, float], ...]:
    frames: list[tuple[str, float, float]] = []
    for entry in spec.entries:
        for source in entry.fields:
            rect = source.rectangle
            corners = np.float32(
                [
                    (rect.x, rect.y),
                    (rect.right, rect.y),
                    (rect.right, rect.bottom),
                    (rect.x, rect.bottom),
                ]
            )
            mapped = cv2.perspectiveTransform(corners.reshape(1, 4, 2), H)[0]
            if not np.all(np.isfinite(mapped)):
                continue
            strength = _frame_strength(gray, mapped, tolerance)
            if strength >= _MIN_BORDER_COVERAGE:
                frames.append((source.region_key, float(rect.y), strength))
    return tuple(frames)


def qualify_full_frame(
    raster: BoundedPageRaster, spec: CapturePageSpec, expected_pds2: str
) -> FullFrameRegistrationEvidence:
    """Corroborate QR-derived flatbed geometry using independent printed frames.

    This function must NEVER be used as a substitute for an authorization or
    retained-source digest check. A full-frame white image alone is not proof
    of a registration; a readable QR alone is equally insufficient.
    """
    if not isinstance(raster, BoundedPageRaster) or not isinstance(
        spec, CapturePageSpec
    ):
        raise HistoricalPageError("fullframe_invalid_inputs")
    if resolve_capture_page_spec(spec.template_identity()) != spec:
        raise HistoricalPageError("fullframe_historical_layout_changed")
    if not isinstance(expected_pds2, str) or not expected_pds2.startswith("PDS2"):
        raise HistoricalPageError("fullframe_invalid_qr_expectation")
    if (
        raster.registration != "unregistered"
        or raster.width * raster.height > _MAX_PIXELS
    ):
        raise HistoricalPageError("fullframe_untrusted_raster")
    cv2, np, qrcode = _backends()
    gray = np.frombuffer(raster.pixels, dtype=np.uint8).reshape(
        raster.height, raster.width
    )
    radius = max(3, min(gray.shape) // 90)
    corners = (
        gray[:radius, :radius],
        gray[:radius, -radius:],
        gray[-radius:, -radius:],
        gray[-radius:, :radius],
    )
    if min(float(np.median(corner)) for corner in corners) < 225:
        raise HistoricalPageError("fullframe_white_corners_unavailable")
    # QR coordinates are observed in the original, Core-retained grayscale bytes.
    observed = np.float32(_qr_points(gray, expected_pds2, cv2, np))
    if (
        min(
            float(np.linalg.norm(observed[(i + 1) % 4] - observed[i])) for i in range(4)
        )
        < _MIN_QR_SIZE
    ):
        raise HistoricalPageError("fullframe_qr_too_small")
    expected = np.float32(_expected_qr_corners(spec, expected_pds2, qrcode, np))
    page = np.float32(_PAGE_CORNERS)
    height, width = gray.shape
    variants: list[
        tuple[float, Any, Any, tuple[tuple[str, float, float], ...], int]
    ] = []
    for rotation in range(4):
        ordered_qr = np.float32(np.roll(observed, rotation, axis=0))
        H = cv2.getPerspectiveTransform(expected, ordered_qr)
        mapped_page = cv2.perspectiveTransform(page.reshape(1, 4, 2), H)[0]
        if not np.all(np.isfinite(mapped_page)):
            continue
        # A full-frame flatbed scan must contain substantially the whole page.
        edge_error_x = width * _MAX_EDGE_ERROR
        edge_error_y = height * _MAX_EDGE_ERROR
        if any(
            not (
                -edge_error_x <= float(p[0]) <= width + edge_error_x
                and -edge_error_y <= float(p[1]) <= height + edge_error_y
            )
            for p in mapped_page
        ):
            continue
        segments = [
            float(np.linalg.norm(mapped_page[(i + 1) % 4] - mapped_page[i]))
            for i in range(4)
        ]
        if min(segments) < 250 or max(segments) / min(segments) > 2.4:
            continue
        if (
            max(
                segments[0] / segments[2],
                segments[2] / segments[0],
                segments[1] / segments[3],
                segments[3] / segments[1],
            )
            > 1.12
        ):
            continue
        tolerance = min(
            _MAX_ANCHOR_TOLERANCE, max(3, round(min(width, height) * 0.004))
        )
        frames = _candidate_frames(gray, H, spec, cv2, np, tolerance)
        if (
            len(frames) < 3
            or max(f[1] for f in frames) - min(f[1] for f in frames)
            < _MIN_FRAME_SEPARATION
        ):
            continue
        # Two separated anchors must be in the lower half; QR is near the top.
        if sum(y > 400 for _, y, _ in frames) < 2:
            continue
        score = sum(f[2] for f in frames)
        variants.append((score, H, mapped_page, frames, tolerance))
    if not variants:
        raise HistoricalPageError("fullframe_independent_landmarks_unmeasured")
    variants.sort(key=lambda item: item[0], reverse=True)
    if len(variants) > 1 and variants[1][0] >= variants[0][0] * 0.85:
        raise HistoricalPageError("fullframe_orientation_ambiguous")
    _, H, mapped_page, frames, _tol = variants[0]
    lengths = [
        float(np.linalg.norm(mapped_page[(i + 1) % 4] - mapped_page[i]))
        for i in range(4)
    ]
    if not all(math.isfinite(value) for value in lengths):
        raise HistoricalPageError("fullframe_geometry_invalid")
    return FullFrameRegistrationEvidence(
        PageRegistration(
            method="measured_fullframe_qr_and_field_frames_v1",
            qr_residual_pixels=0.0,  # QR anchors define the transform, NOT independent residual
            page_width_pixels=(lengths[0] + lengths[2]) / 2,
            page_height_pixels=(lengths[1] + lengths[3]) / 2,
            page_quad=tuple((float(p[0]), float(p[1])) for p in mapped_page),
        ),
        H,
        tuple(f[0] for f in frames),
    )
