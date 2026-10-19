"""#60 Slice 2B: independently measured registration and ephemeral field crops.

A QR is necessary but not sufficient to locate paper fields. This deliberately
narrow local-only provider requires a visible, contrasting *whole paper border*
AND agreement with the exact active PDS2 QR's known printed position. White
scanner pages without a measured border remain unregistered; raster dimensions
alone never authorize a source field crop.

No OCR, handwriting, marks, blank decisions, persistence, or review happens here.
"""

from __future__ import annotations

import importlib
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from pds_core.pds2 import serialize_pds2_payload
from pds_core.routing_models import PDS2_SCHEMA, ModuleWorkRef, RouteLocator

from portia.capture.contracts import CaptureAuthorization
from portia.capture.form_catalog import (
    CapturePageSpec,
    CaptureRectangle,
    resolve_capture_page_spec,
)
from portia.intake.contracts import SourceFormat, SourceSafetyLimits
from portia.intake.historical_page_regions import (
    BoundedPageRaster,
    FileHistoricalPageRegionService,
    HistoricalPageError,
    _render_image,
    _render_pdf_page,
)

_PAGE_WIDTH = 612
_PAGE_HEIGHT = 792
_MAX_REGION_PIXELS = 2_000_000
_MAX_PAGE_REGION_PIXELS = 12_000_000
_MAX_REGISTRATION_IMAGE_PIXELS = 16_000_000
_MIN_BORDER_AREA_FRACTION = 0.20
_MAX_QR_RESIDUAL_PIXELS = 12.0

# Both methods are independently measured and explicitly qualified.
QUALIFIED_REGISTRATION_METHODS = frozenset(
    {
        "measured_sheet_boundary_and_exact_qr_v1",
        "measured_fullframe_qr_and_field_frames_v1",
    }
)


@dataclass(frozen=True, slots=True)
class PageRegistration:
    """Measured in pixels; never a claim of source truth or OCR accuracy."""

    method: str
    qr_residual_pixels: float
    page_width_pixels: float
    page_height_pixels: float
    page_quad: tuple[tuple[float, float], ...] = field(repr=False)


@dataclass(frozen=True, slots=True)
class FieldRegionPixels:
    """One unaltered field box (including print, labels, rules and handwriting)."""

    entry_key: str
    field_key: str
    region_key: str
    width: int
    height: int
    pixels: bytes = field(repr=False)

    def __post_init__(self) -> None:
        if (
            not self.entry_key
            or not self.field_key
            or not self.region_key
            or type(self.width) is not int
            or type(self.height) is not int
            or self.width < 1
            or self.height < 1
            or self.width * self.height > _MAX_REGION_PIXELS
            or len(self.pixels) != self.width * self.height
        ):
            raise HistoricalPageError("invalid_extracted_region")


@dataclass(frozen=True, slots=True)
class MeasuredPageRegions:
    """Read-only, field-local pixels. Caller must not persist or log this value."""

    source_page_number: int
    layout_fingerprint: str
    registration: PageRegistration
    fields: tuple[FieldRegionPixels, ...] = field(repr=False)

    @property
    def field_count(self) -> int:
        return len(self.fields)


class FileMeasuredRegionService:
    """Authorize and recheck #59 custody around optional local CV processing."""

    def __init__(
        self, workspace_root: str | Path, *, limits: SourceSafetyLimits | None = None
    ) -> None:
        from portia.intake.contracts import DEFAULT_SOURCE_LIMITS

        selected = DEFAULT_SOURCE_LIMITS if limits is None else limits
        self.pages = FileHistoricalPageRegionService(workspace_root, limits=selected)
        self.limits = selected

    def extract(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
        profile_identity: Mapping[str, object],
    ) -> MeasuredPageRegions:
        """Never accept caller-provided pixels, registration, or source paths."""
        first = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        snapshot = dict(first.plan.layout.layout_identity)
        spec = resolve_capture_page_spec(snapshot)
        route_id = first.receipt.field("route_id")
        if not isinstance(route_id, str):
            raise HistoricalPageError("route_identity_invalid")
        locator = RouteLocator(
            PDS2_SCHEMA, ModuleWorkRef("portia", class_id, work_id), route_id
        )
        payload = serialize_pds2_payload(locator)
        retained = first.retained
        if retained.source_format is SourceFormat.PDF:
            raster = _render_pdf_page(retained, first.source_page_number, self.limits)
        elif retained.source_format in (SourceFormat.PNG, SourceFormat.JPEG):
            raster = _render_image(retained, first.source_page_number, self.limits)
        else:
            raise HistoricalPageError("source_format_unsupported")
        try:
            measured = measure_and_extract(raster, spec, payload)
        except HistoricalPageError:
            raise
        except Exception as exc:
            raise HistoricalPageError("registration_provider_failed") from exc
        # A second complete authorization/receipt/target/route/custody read must
        # succeed before the caller receives ephemeral source-region pixels.
        second = self.pages.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        if (
            first.receipt.to_dict() != second.receipt.to_dict()
            or first.plan != second.plan
            or first.retained.page_identity(first.source_page_number)
            != second.retained.page_identity(second.source_page_number)
        ):
            raise HistoricalPageError("authority_changed_during_region_extraction")
        self.pages.dispatch._verify_custody(
            second.retained.core_source, second.retained.byte_count
        )
        return measured


def _backends() -> tuple[Any, Any, Any]:
    try:
        cv2 = importlib.import_module("cv2")
        np = importlib.import_module("numpy")
        qrcode = importlib.import_module("qrcode")
    except ImportError as exc:
        raise HistoricalPageError("local_registration_backend_unavailable") from exc
    return cv2, np, qrcode


def _order_quad(points: Any, np: Any) -> Any:
    """Consistent clockwise ordering, with all cyclic starts checked via QR."""
    points = np.asarray(points, dtype=np.float64).reshape(4, 2)
    midpoint = points.mean(axis=0)
    angles = np.arctan2(points[:, 1] - midpoint[1], points[:, 0] - midpoint[0])
    return points[np.argsort(angles)]


def _page_quad(gray: Any, cv2: Any, np: Any) -> Any:
    """Only a measured bright sheet against a contrasting surrounding border."""
    height, width = gray.shape
    # Reject full-frame white scans: a media box is not measured page alignment.
    corner_radius = max(2, min(height, width) // 100)
    corner_medians = (
        float(np.median(gray[:corner_radius, :corner_radius])),
        float(np.median(gray[:corner_radius, -corner_radius:])),
        float(np.median(gray[-corner_radius:, :corner_radius])),
        float(np.median(gray[-corner_radius:, -corner_radius:])),
    )
    if max(corner_medians) > 135:
        raise HistoricalPageError("page_border_unmeasured")
    mask = np.uint8(gray >= 180) * 255
    contours, _hierarchy = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    candidates = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < width * height * _MIN_BORDER_AREA_FRACTION:
            continue
        perimeter = float(cv2.arcLength(contour, True))
        poly = cv2.approxPolyDP(contour, 0.012 * perimeter, True)
        if len(poly) == 4 and cv2.isContourConvex(poly):
            candidates.append((area, _order_quad(poly, np)))
    if not candidates:
        raise HistoricalPageError("page_border_unmeasured")
    candidates.sort(key=lambda pair: pair[0], reverse=True)
    if len(candidates) > 1 and candidates[1][0] >= candidates[0][0] * 0.80:
        raise HistoricalPageError("multiple_page_boundaries")
    quad = candidates[0][1]
    if any(
        not (3 <= float(point[0]) < width - 3 and 3 <= float(point[1]) < height - 3)
        for point in quad
    ):
        raise HistoricalPageError("page_edges_cropped")
    if (
        float(
            np.median(
                gray[height // 2 - 2 : height // 2 + 3, width // 2 - 2 : width // 2 + 3]
            )
        )
        < 155
    ):
        raise HistoricalPageError("page_background_not_resolved")
    return quad


def _qr_points(gray: Any, expected_payload: str, cv2: Any, np: Any) -> Any:
    detector = cv2.QRCodeDetector()
    # Multi detection is used for ambiguity screening; require a single QR.
    try:
        success, texts, points, _rectified = detector.detectAndDecodeMulti(gray)
        if points is not None and len(points) > 1:
            raise HistoricalPageError("ambiguous_registration_qr")
        if success and points is not None:
            decoded = [
                (str(t), np.asarray(p, dtype=np.float64).reshape(4, 2))
                for t, p in zip(texts, points)
            ]
            if len(decoded) != 1:
                raise HistoricalPageError("ambiguous_registration_qr")
            if decoded[0][0] != expected_payload:
                raise HistoricalPageError("registration_qr_route_mismatch")
            return decoded[0][1]
        text, points, _straight = detector.detectAndDecode(gray)
    except HistoricalPageError:
        raise
    except (ValueError, RuntimeError, TypeError, MemoryError) as exc:
        raise HistoricalPageError("registration_qr_unreadable") from exc
    if points is None or not text:
        raise HistoricalPageError("registration_qr_unreadable")
    if text != expected_payload:
        raise HistoricalPageError("registration_qr_route_mismatch")
    return np.asarray(points, dtype=np.float64).reshape(4, 2)


def _expected_qr_corners(
    spec: CapturePageSpec, payload: str, qrcode: Any, np: Any
) -> Any:
    code = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4
    )
    code.add_data(payload, optimize=0)
    code.make(fit=True)
    side = len(code.get_matrix())
    box = spec.qr_rectangle
    if side < 9 or box != CaptureRectangle(468, 40, 108, 108):
        raise HistoricalPageError("historical_qr_geometry_unsupported")
    lo = 4.0 / side
    hi = (side - 4.0) / side
    return np.float32(
        [
            (box.x + lo * box.width, box.y + lo * box.height),
            (box.x + hi * box.width, box.y + lo * box.height),
            (box.x + hi * box.width, box.y + hi * box.height),
            (box.x + lo * box.width, box.y + hi * box.height),
        ]
    )


def _registration(
    raster: BoundedPageRaster,
    spec: CapturePageSpec,
    payload: str,
    cv2: Any,
    np: Any,
    qrcode: Any,
) -> tuple[PageRegistration, Any]:
    if (
        raster.registration != "unregistered"
        or len(raster.pixels) != raster.width * raster.height
    ):
        raise HistoricalPageError("untrusted_raster_state")
    if raster.width * raster.height > _MAX_REGISTRATION_IMAGE_PIXELS:
        raise HistoricalPageError("registration_pixel_limit")
    gray = np.frombuffer(raster.pixels, dtype=np.uint8).reshape(
        raster.height, raster.width
    )
    quad = _page_quad(gray, cv2, np)
    observed_qr = _qr_points(gray, payload, cv2, np)
    expected_qr = _expected_qr_corners(spec, payload, qrcode, np)
    corners = np.float32(
        [(0, 0), (_PAGE_WIDTH, 0), (_PAGE_WIDTH, _PAGE_HEIGHT), (0, _PAGE_HEIGHT)]
    )
    candidates: list[tuple[float, Any, Any]] = []
    for rotation in range(4):
        ordered = np.float32(np.roll(quad, rotation, axis=0))
        H = cv2.getPerspectiveTransform(corners, ordered)
        mapped = cv2.perspectiveTransform(expected_qr.reshape(1, 4, 2), H)[0]
        residual = min(
            max(
                float(
                    np.linalg.norm(
                        mapped - np.roll(observed_qr, k, axis=0), axis=1
                    ).max()
                ),
                0.0,
            )
            for k in range(4)
        )
        if math.isfinite(residual):
            candidates.append((residual, H, ordered))
    if not candidates:
        raise HistoricalPageError("registration_not_measurable")
    candidates.sort(key=lambda row: row[0])
    residual, H, corners_px = candidates[0]
    max_residual = min(
        _MAX_QR_RESIDUAL_PIXELS, max(3.5, min(raster.width, raster.height) * 0.005)
    )
    if residual > max_residual:
        raise HistoricalPageError("registration_qr_geometry_conflict")
    if len(candidates) > 1 and candidates[1][0] <= max_residual:
        raise HistoricalPageError("registration_orientation_ambiguous")
    lengths = [
        float(np.linalg.norm(corners_px[(i + 1) % 4] - corners_px[i])) for i in range(4)
    ]
    if min(lengths) < 80 or max(lengths) / min(lengths) > 2.4:
        raise HistoricalPageError("registration_geometry_distorted")
    if (
        max(
            lengths[0] / lengths[2],
            lengths[2] / lengths[0],
            lengths[1] / lengths[3],
            lengths[3] / lengths[1],
        )
        > 1.25
    ):
        raise HistoricalPageError("registration_perspective_excessive")
    reg = PageRegistration(
        method="measured_sheet_boundary_and_exact_qr_v1",
        qr_residual_pixels=round(residual, 4),
        page_width_pixels=(lengths[0] + lengths[2]) / 2,
        page_height_pixels=(lengths[1] + lengths[3]) / 2,
        page_quad=tuple((float(p[0]), float(p[1])) for p in corners_px),
    )
    return reg, H


def measure_and_extract(
    raster: BoundedPageRaster, spec: CapturePageSpec, expected_pds2: str
) -> MeasuredPageRegions:
    """Ephemeral geometry engine, not an authorization API.

    Callers must use FileMeasuredRegionService.extract for verified source
    provenance and class permission before consuming these pixels.
    """
    if not isinstance(raster, BoundedPageRaster) or not isinstance(
        spec, CapturePageSpec
    ):
        raise HistoricalPageError("invalid_registration_inputs")
    # Pin the *entire* seven-element identity to installed immutable resources.
    exact = resolve_capture_page_spec(spec.template_identity())
    if exact != spec:
        raise HistoricalPageError("historical_layout_changed")
    if not isinstance(expected_pds2, str) or not expected_pds2.startswith("PDS2"):
        raise HistoricalPageError("invalid_expected_pds2")
    cv2, np, qr = _backends()
    try:
        registration, H = _registration(raster, exact, expected_pds2, cv2, np, qr)
    except HistoricalPageError as border_error:
        # A missing external paper border is the ONLY condition that
        # enables the independently corroborated full-frame scanner
        # method. Never bypass a bad QR, disagreement, clipped border,
        # distorted geometry or another hard legacy failure.
        if str(border_error) != "page_border_unmeasured":
            raise
        from portia.intake.full_frame_registration import qualify_full_frame

        try:
            evidence = qualify_full_frame(raster, exact, expected_pds2)
        except HistoricalPageError as full_frame_error:
            # Retain the established diagnostic for an all-white
            # source that lacks even a decoded QR.
            if str(full_frame_error) == "registration_qr_unreadable":
                raise border_error from full_frame_error
            raise
        registration, H = evidence.registration, evidence.transform
    gray = np.frombuffer(raster.pixels, dtype=np.uint8).reshape(
        raster.height, raster.width
    )
    scale = min(
        3.0,
        max(
            0.7,
            min(
                registration.page_width_pixels / _PAGE_WIDTH,
                registration.page_height_pixels / _PAGE_HEIGHT,
            ),
        ),
    )
    fields: list[FieldRegionPixels] = []
    total_pixels = 0
    for entry in exact.entries:
        for source in entry.fields:
            rect = source.rectangle
            width = max(1, math.ceil(rect.width * scale))
            height = max(1, math.ceil(rect.height * scale))
            total_pixels += width * height
            if (
                width * height > _MAX_REGION_PIXELS
                or total_pixels > _MAX_PAGE_REGION_PIXELS
            ):
                raise HistoricalPageError("region_pixel_budget_exceeded")
            original = np.float32(
                [
                    (rect.x, rect.y),
                    (rect.right, rect.y),
                    (rect.right, rect.bottom),
                    (rect.x, rect.bottom),
                ]
            )
            mapped = cv2.perspectiveTransform(original.reshape(1, 4, 2), H)[0]
            if not np.all(np.isfinite(mapped)) or any(
                float(p[0]) < 0
                or float(p[0]) >= raster.width
                or float(p[1]) < 0
                or float(p[1]) >= raster.height
                for p in mapped
            ):
                raise HistoricalPageError("region_outside_registered_sheet")
            dest = np.float32(
                [(0, 0), (width - 1, 0), (width - 1, height - 1), (0, height - 1)]
            )
            warp = cv2.getPerspectiveTransform(np.float32(mapped), dest)
            crop = cv2.warpPerspective(
                gray,
                warp,
                (width, height),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=255,
            )
            fields.append(
                FieldRegionPixels(
                    entry.entry_key,
                    source.field_key,
                    source.region_key,
                    width,
                    height,
                    crop.tobytes(),
                )
            )
    return MeasuredPageRegions(
        raster.source_page_number,
        exact.layout_fingerprint,
        registration,
        tuple(fields),
    )
