"""#59 Slice 3: read-only page rasterization and untrusted QR discovery.

Only a fully Core-retained Slice 2 source may enter. This layer NEVER routes,
reads class records, persists a Page Record, or interprets marked fields.
"""

from __future__ import annotations

import hmac
import importlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

from pds_core.pds2 import Pds2PayloadError, parse_pds2_payload, serialize_pds2_payload
from pds_core.routing_models import RouteLocator, RoutingModelError
from PIL import Image

from portia.intake.contracts import (
    DEFAULT_SOURCE_LIMITS,
    RetainedPageIdentity,
    SourceFormat,
    SourceSafetyLimits,
)
from portia.intake.retention import (
    IntakeSourceError,
    RetainedIntakeSource,
    _assert_retained_under_root,
    _hash_file,
)

PageQrStatus = Literal[
    "candidate_unverified",
    "missing_qr",
    "unreadable_qr",
    "ambiguous_qr",
    "invalid_qr",
    "foreign_module",
    "render_failed",
]
_MAX_DECODE_DIMENSION = 2400


class QrDiscoveryError(RuntimeError):
    """Backend unavailable or retained source cannot be safely inspected."""


@dataclass(frozen=True, slots=True)
class PageQrDiscovery:
    """Source-position-bound QR result; locator is NOT a verified registration.

    Raw decoded text and the scanned page image are never retained here.
    """

    identity: RetainedPageIdentity
    status: PageQrStatus
    candidate_locator: RouteLocator | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.identity, RetainedPageIdentity):
            raise ValueError("result requires retained-source page identity")
        if self.status not in {
            "candidate_unverified",
            "missing_qr",
            "unreadable_qr",
            "ambiguous_qr",
            "invalid_qr",
            "foreign_module",
            "render_failed",
        }:
            raise ValueError("unknown page QR status")
        if self.status == "candidate_unverified":
            if not isinstance(self.candidate_locator, RouteLocator):
                raise ValueError("QR candidate requires a typed locator")
            if self.candidate_locator.module_id != "portia":
                raise ValueError("only Portia candidates may be exposed")
        elif self.candidate_locator is not None:
            raise ValueError("noncandidate pages must not expose a locator")


@dataclass(frozen=True, slots=True)
class SourceQrDiscovery:
    """One result per physical page of one already Core-retained source."""

    source: RetainedIntakeSource
    pages: tuple[PageQrDiscovery, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source, RetainedIntakeSource):
            raise ValueError("source must be retained by Core")
        if len(self.pages) != self.source.page_count:
            raise ValueError("source page outcomes must be complete")
        for index, page in enumerate(self.pages, 1):
            if page.identity != self.source.page_identity(index):
                raise ValueError("source page results must preserve original order")

    @property
    def candidates(self) -> int:
        return sum(page.status == "candidate_unverified" for page in self.pages)


class FilePageQrDiscoveryService:
    """Discover each page QR in a retained PDF/JPEG/PNG, without side effects.

    Dependencies PyMuPDF/OpenCV/NumPy belong to the optional ``scan`` extra
    until the final intake packaging/release qualification. Missing providers
    fail explicitly; they never turn into a misleading 'no QR' result.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        limits: SourceSafetyLimits = DEFAULT_SOURCE_LIMITS,
    ) -> None:
        if not isinstance(limits, SourceSafetyLimits):
            raise TypeError("limits must be SourceSafetyLimits")
        self.root = Path(workspace_root)
        self.limits = limits

    def discover(self, source: RetainedIntakeSource) -> SourceQrDiscovery:
        if not isinstance(source, RetainedIntakeSource):
            raise TypeError("discovery requires Core-retained intake source")
        if not 1 <= source.page_count <= self.limits.max_pages:
            raise QrDiscoveryError("retained source page count exceeds policy")
        if source.byte_count > self.limits.max_source_bytes:
            raise QrDiscoveryError("retained source byte count exceeds policy")
        _verify_retained(self.root, source, self.limits)
        cv2, np = _load_qr_backends()
        if source.source_format is SourceFormat.PDF:
            pages = self._pdf_pages(source, cv2, np)
        elif source.source_format in (SourceFormat.JPEG, SourceFormat.PNG):
            pages = self._image_pages(source, cv2, np)
        else:
            raise QrDiscoveryError("unsupported retained-source format")
        # A source changed while page decoding must not yield authoritative
        # candidates or a misleading complete result.
        _verify_retained(self.root, source, self.limits)
        return SourceQrDiscovery(source, tuple(pages))

    def _pdf_pages(
        self, source: RetainedIntakeSource, cv2: Any, np: Any
    ) -> list[PageQrDiscovery]:
        fitz = cast(Any, _load_pdf_backend())
        results: list[PageQrDiscovery] = []
        try:
            with fitz.open(str(source.core_source.retained_source_path)) as document:
                if document.needs_pass or document.page_count != source.page_count:
                    raise QrDiscoveryError("retained PDF protection/page count changed")
                for index in range(source.page_count):
                    identity = source.page_identity(index + 1)
                    try:
                        page = document.load_page(index)
                        width = math.ceil(
                            float(page.rect.width) * self.limits.raster_dpi / 72
                        )
                        height = math.ceil(
                            float(page.rect.height) * self.limits.raster_dpi / 72
                        )
                        _check_dimensions(width, height, self.limits)
                        # Grayscale; one page at a time, no extracted disk files.
                        matrix = fitz.Matrix(
                            self.limits.raster_dpi / 72, self.limits.raster_dpi / 72
                        )
                        pix = page.get_pixmap(
                            matrix=matrix, colorspace=fitz.csGRAY, alpha=False
                        )
                        _check_dimensions(pix.width, pix.height, self.limits)
                        if pix.n != 1:
                            raise ValueError("unexpected grayscale raster")
                        gray = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                            (pix.height, pix.width)
                        )
                        texts, unreadable = _decode(gray, cv2, np)
                        results.append(_classify(identity, texts, unreadable))
                    except Exception:  # per-page untrusted renderer/decoder errors
                        results.append(PageQrDiscovery(identity, "render_failed"))
        except QrDiscoveryError:
            raise
        except Exception as exc:
            raise QrDiscoveryError(
                "retained PDF cannot be opened for page discovery"
            ) from exc
        return results

    def _image_pages(
        self, source: RetainedIntakeSource, cv2: Any, np: Any
    ) -> list[PageQrDiscovery]:
        identity = source.page_identity(1)
        try:
            with Image.open(source.core_source.retained_source_path) as image:
                if source.page_count != 1 or getattr(image, "n_frames", 1) != 1:
                    raise QrDiscoveryError("unexpected image page count")
                if image.format != (
                    "JPEG" if source.source_format is SourceFormat.JPEG else "PNG"
                ):
                    raise QrDiscoveryError("retained image format changed")
                _check_dimensions(*image.size, self.limits)
                gray = np.array(image.convert("L"), dtype=np.uint8)
            texts, unreadable = _decode(gray, cv2, np)
            return [_classify(identity, texts, unreadable)]
        except Exception:  # malformed image/QR decoder; never misreport as a candidate
            return [PageQrDiscovery(identity, "render_failed")]


def _verify_retained(
    root: Path, source: RetainedIntakeSource, limits: SourceSafetyLimits
) -> None:
    _assert_retained_under_root(root, source.core_source)
    digest, size = _hash_file(
        source.core_source.retained_source_path, limits.max_source_bytes
    )
    if size != source.byte_count or not hmac.compare_digest(
        digest, source.core_source.source_sha256
    ):
        raise IntakeSourceError(
            "retained_integrity_failure", "Core-retained bytes changed"
        )


def _check_dimensions(width: int, height: int, limits: SourceSafetyLimits) -> None:
    if (
        type(width) is not int
        or type(height) is not int
        or width < 1
        or height < 1
        or width * height > limits.max_page_pixels
    ):
        raise QrDiscoveryError("page exceeds the bounded raster pixel budget")


def _load_pdf_backend() -> object:
    try:
        return importlib.import_module("pymupdf")
    except ImportError as exc:
        raise QrDiscoveryError(
            "PDF rasterizer unavailable: install the scan extra"
        ) from exc


def _load_qr_backends() -> tuple[object, object]:
    try:
        cv2 = importlib.import_module("cv2")
        numpy = importlib.import_module("numpy")
    except ImportError as exc:
        raise QrDiscoveryError(
            "QR decoder unavailable: install the scan extra"
        ) from exc
    return cast(Any, cv2), cast(Any, numpy)


def _decode(gray: Any, cv2: Any, np: Any) -> tuple[tuple[str, ...], bool]:
    """Probe a bounded in-memory raster; never choose among conflicting codes."""
    height, width = gray.shape
    if max(height, width) > _MAX_DECODE_DIMENSION:
        scale = _MAX_DECODE_DIMENSION / max(height, width)
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    decoded: set[str] = set()
    unreadable = False
    failures = 0
    detector = cv2.QRCodeDetector()
    for orientation in range(4):
        if orientation:
            gray = np.ascontiguousarray(np.rot90(gray, 1))
        try:
            success, values, points, _ = detector.detectAndDecodeMulti(gray)
            if points is not None:
                unreadable = unreadable or any(not item for item in values)
            if success:
                decoded.update(
                    text for text in values if isinstance(text, str) and text
                )
            if not success and points is None:
                single, points_one, _ = detector.detectAndDecode(gray)
                if single:
                    decoded.add(single)
                elif points_one is not None:
                    unreadable = True
        except (ValueError, RuntimeError, TypeError, MemoryError):
            failures += 1
            continue
        if decoded:
            break
    if failures == 4:
        raise QrDiscoveryError("QR decoder failed on every orientation")
    return tuple(sorted(decoded)), unreadable


def _classify(
    identity: RetainedPageIdentity, values: tuple[str, ...], unreadable: bool = False
) -> PageQrDiscovery:
    if unreadable and values or len(values) > 1:
        return PageQrDiscovery(identity, "ambiguous_qr")
    if not values:
        return PageQrDiscovery(
            identity, "unreadable_qr" if unreadable else "missing_qr"
        )
    try:
        locator = parse_pds2_payload(values[0])
        if serialize_pds2_payload(locator) != values[0]:
            return PageQrDiscovery(identity, "invalid_qr")
    except (Pds2PayloadError, RoutingModelError):
        return PageQrDiscovery(identity, "invalid_qr")
    if locator.module_id != "portia":
        return PageQrDiscovery(identity, "foreign_module")
    return PageQrDiscovery(identity, "candidate_unverified", locator)
