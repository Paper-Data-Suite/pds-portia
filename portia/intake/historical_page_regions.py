"""Issue #60 Slice 2: authorized historical page custody and bounded raster regions.

No incoming filename, QR candidate, or caller-built Page Record is authority.
The only entry point starts from a persisted, exact #59 Page Record. Geometry
cannot be trusted from pixel dimensions alone: until a *measured* registration
provider is qualified, all raster regions remain unregistered, never blank.

There is no OCR/OMR, student matching, staging persistence, or domain writing.
"""

from __future__ import annotations

import hmac
import importlib
import math
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Mapping, cast

from pds_core.routing_models import PDS2_SCHEMA, ModuleWorkRef, RouteLocator
from pds_core.scan_routes import scans_source_dir

from portia.capture.contracts import CaptureAuthorization
from portia.intake.contracts import (
    DEFAULT_SOURCE_LIMITS,
    RetainedPageIdentity,
    SourceFormat,
    SourceSafetyLimits,
)
from portia.intake.dispatch import FilePageRouteDispatchService
from portia.intake.interpretation_profiles import (
    HistoricalInterpretationPlan,
    plan_historical_interpretation,
)
from portia.intake.page_records import FilePageRecordService, _receipt_id
from portia.intake.recognition import PageQrDiscovery
from portia.intake.recovery import (
    FileCoreRetainedSourceRecoveryService,
    RetainedSourceCandidate,
)
from portia.intake.retention import (
    RetainedIntakeSource,
    _assert_safe_path,
)
from portia.models import PageRecordV1

_CORE_STEM = re.compile(r"scan_(\d{8})T\d{12}Z__[A-Za-z0-9_-]+__[a-f0-9]{12}\Z")
_LEAF_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")
_MAX_RASTER_PIXELS = 16_000_000


class HistoricalPageError(RuntimeError):
    """Bounded, safe diagnostic; never include source text or local paths."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class AuthorizedHistoricalPage:
    """Ephemeral, authorization-scoped snapshot; never persist or log this object."""

    class_id: str
    work_id: str
    page_record_id: str
    source_page_number: int
    plan: HistoricalInterpretationPlan = field(repr=False)
    receipt: PageRecordV1 = field(repr=False)
    retained: RetainedIntakeSource = field(repr=False)


@dataclass(frozen=True, slots=True)
class BoundedPageRaster:
    """One ephemeral grayscale physical page, with no assumed field alignment."""

    width: int
    height: int
    source_page_number: int
    pixels: bytes = field(repr=False)
    registration: Literal["unregistered"] = "unregistered"

    def __post_init__(self) -> None:
        if (
            type(self.width) is not int
            or type(self.height) is not int
            or type(self.source_page_number) is not int
            or self.source_page_number < 1
            or self.width < 1
            or self.height < 1
            or self.width * self.height > _MAX_RASTER_PIXELS
            or len(self.pixels) != self.width * self.height
        ):
            raise HistoricalPageError("invalid_page_raster")


class FileHistoricalPageRegionService:
    """Restart-safe read-only authority for one printed physical page.

    Uses #59's bounded receipt parser, Core custody/recovery, Core dispatch,
    and the Slice 1 exact template/version registry. It never calls retention.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        limits: SourceSafetyLimits = DEFAULT_SOURCE_LIMITS,
    ) -> None:
        if not isinstance(limits, SourceSafetyLimits):
            raise TypeError("limits must be SourceSafetyLimits")
        self.root = Path(workspace_root).absolute()
        self.limits = limits
        self.receipts = FilePageRecordService(self.root)
        self.recovery = FileCoreRetainedSourceRecoveryService(self.root, limits=limits)
        self.dispatch = FilePageRouteDispatchService(self.root, limits=limits)

    def resolve(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
        profile_identity: Mapping[str, object],
    ) -> AuthorizedHistoricalPage:
        """Read *only* exact persisted evidence after a trusted class-access gate."""
        if authorization is None or not callable(
            getattr(authorization, "require_access", None)
        ):
            raise TypeError("trusted CaptureAuthorization is required")
        # Must happen before any class-sensitive Core/Portia disk access.
        authorization.require_access(class_id, "capture_interpretation.resolve")
        batch = self.receipts.batches.load(
            class_id, work_id, authorization=authorization
        )
        if batch.status == "cancelled":
            raise HistoricalPageError("batch_cancelled")
        collection = self.receipts._collection(class_id, work_id)
        matching = [
            item
            for item in self.receipts._scan_receipts(collection)
            if item.logical_id == page_record_id
        ]
        if len(matching) != 1:
            raise HistoricalPageError("page_record_unavailable")
        receipt = matching[0]
        data = receipt.to_dict()
        source_ref = data.get("source_ref")
        if not isinstance(source_ref, dict):
            raise HistoricalPageError("page_record_source_invalid")
        try:
            identity = RetainedPageIdentity(
                source_scan_id=cast(str, source_ref["source_scan_id"]),
                source_sha256=cast(str, source_ref["source_sha256"]),
                source_page_number=cast(int, source_ref["source_page_number"]),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise HistoricalPageError("page_record_source_invalid") from exc
        if _receipt_id(identity) != receipt.logical_id:
            raise HistoricalPageError("page_record_identity_conflict")
        retained = self._recover_exact(identity)
        if identity.source_page_number > retained.page_count:
            raise HistoricalPageError("physical_page_out_of_range")
        if retained.page_identity(identity.source_page_number) != identity:
            raise HistoricalPageError("retained_source_lineage_conflict")
        locator = RouteLocator(
            PDS2_SCHEMA,
            ModuleWorkRef("portia", class_id, work_id),
            cast(str, data["route_id"]),
        )
        # This candidate is NOT a new QR claim. The *persisted* #59 receipt
        # establishes the original verified route; Core dispatch revalidates
        # the current durable registration + exact Page Target for inspection.
        routed = self.dispatch._one(
            PageQrDiscovery(identity, "candidate_unverified", locator),
            retained.core_source,
            authorization,
        )
        if routed.status != "verified" or routed.verified is None:
            raise HistoricalPageError("core_route_" + routed.status)
        target = routed.verified.target
        if target.logical_id != receipt.field("page_target_id"):
            raise HistoricalPageError("page_target_lineage_conflict")
        plan = plan_historical_interpretation(target, profile_identity=profile_identity)
        # A second custody hash prevents returning a plan after a file changed
        # while the Core registration and historical target were inspected.
        self.dispatch._verify_custody(retained.core_source, retained.byte_count)
        return AuthorizedHistoricalPage(
            class_id=class_id,
            work_id=work_id,
            page_record_id=page_record_id,
            source_page_number=identity.source_page_number,
            plan=plan,
            receipt=receipt,
            retained=retained,
        )

    def _recover_exact(self, identity: RetainedPageIdentity) -> RetainedIntakeSource:
        """Find exactly one canonical Core leaf by *saved* source_scan_id.

        No recent-64 cutoff: older returned paper remains findable. The Core
        date is derived from its canonical scan ID, not scanned folder contents.
        """
        match = _CORE_STEM.fullmatch(identity.source_scan_id)
        if match is None:
            raise HistoricalPageError("unrecognized_core_scan_identity")
        try:
            day = datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
        except ValueError as exc:
            raise HistoricalPageError("unrecognized_core_scan_identity") from exc
        stem = identity.source_scan_id[len("scan_") :]
        folder = scans_source_dir(self.root) / day
        _assert_safe_path(self.root)
        _assert_safe_path(scans_source_dir(self.root))
        _assert_safe_path(folder)
        candidates: list[RetainedSourceCandidate] = []
        for extension in _LEAF_EXTENSIONS:
            path = folder / (stem + extension)
            # Detect symlink/junction leaves even if Path.exists returns False.
            if not path.exists() and not path.is_symlink():
                continue
            _assert_safe_path(path)
            if not path.is_file():
                raise HistoricalPageError("core_source_not_regular")
            candidate = self.recovery._candidate(path)
            if candidate is None or candidate.source_scan_id != identity.source_scan_id:
                raise HistoricalPageError("core_source_name_invalid")
            candidates.append(candidate)
        if len(candidates) != 1:
            raise HistoricalPageError(
                "core_source_missing"
                if not candidates
                else "core_source_identity_collision"
            )
        retained = self.recovery.load(candidates[0])
        if not hmac.compare_digest(
            retained.core_source.source_sha256, identity.source_sha256
        ):
            raise HistoricalPageError("core_source_digest_conflict")
        return retained

    def rasterize(
        self,
        class_id: str,
        work_id: str,
        page_record_id: str,
        *,
        authorization: CaptureAuthorization,
        profile_identity: Mapping[str, object],
    ) -> BoundedPageRaster:
        """Verify custody again and render exactly one page, never fields.

        Pixel dimensions and an intact PDF are *not* evidence of alignment.
        No crop is emitted until a later measured registration provider exists.
        """
        verified = self.resolve(
            class_id,
            work_id,
            page_record_id,
            authorization=authorization,
            profile_identity=profile_identity,
        )
        retained = verified.retained
        if retained.source_format is SourceFormat.PDF:
            raster = _render_pdf_page(
                retained, verified.source_page_number, self.limits
            )
        elif retained.source_format in (SourceFormat.JPEG, SourceFormat.PNG):
            raster = _render_image(retained, verified.source_page_number, self.limits)
        else:
            raise HistoricalPageError("source_format_unsupported")
        self.dispatch._verify_custody(retained.core_source, retained.byte_count)
        return raster


def _size_ok(width: int, height: int, limits: SourceSafetyLimits) -> None:
    if (
        type(width) is not int
        or type(height) is not int
        or width < 1
        or height < 1
        or width * height > min(limits.max_page_pixels, _MAX_RASTER_PIXELS)
    ):
        raise HistoricalPageError("raster_pixel_limit")


def _render_pdf_page(
    retained: RetainedIntakeSource, number: int, limits: SourceSafetyLimits
) -> BoundedPageRaster:
    try:
        fitz = cast(Any, importlib.import_module("pymupdf"))
    except ImportError as exc:
        raise HistoricalPageError("pdf_rasterizer_unavailable") from exc
    try:
        with fitz.open(str(retained.core_source.retained_source_path)) as doc:
            if doc.needs_pass or doc.page_count != retained.page_count:
                raise HistoricalPageError("pdf_page_count_or_protection_conflict")
            page = doc.load_page(number - 1)
            dpi = min(limits.raster_dpi, 144)
            scale = dpi / 72
            width = math.ceil(float(page.rect.width) * scale)
            height = math.ceil(float(page.rect.height) * scale)
            _size_ok(width, height, limits)
            pix = page.get_pixmap(
                matrix=fitz.Matrix(scale, scale),
                colorspace=fitz.csGRAY,
                alpha=False,
            )
            _size_ok(pix.width, pix.height, limits)
            if pix.n != 1:
                raise HistoricalPageError("unexpected_raster_channels")
            return BoundedPageRaster(pix.width, pix.height, number, bytes(pix.samples))
    except HistoricalPageError:
        raise
    except Exception as exc:
        raise HistoricalPageError("pdf_page_render_failed") from exc


def _render_image(
    retained: RetainedIntakeSource, number: int, limits: SourceSafetyLimits
) -> BoundedPageRaster:
    if number != 1 or retained.page_count != 1:
        raise HistoricalPageError("image_physical_page_conflict")
    try:
        from PIL import Image

        with Image.open(retained.core_source.retained_source_path) as image:
            if getattr(image, "n_frames", 1) != 1:
                raise HistoricalPageError("image_page_count_conflict")
            expected = "JPEG" if retained.source_format is SourceFormat.JPEG else "PNG"
            if image.format != expected:
                raise HistoricalPageError("image_source_format_conflict")
            width, height = image.size
            _size_ok(width, height, limits)
            pixels = image.convert("L").tobytes()
        return BoundedPageRaster(width, height, number, pixels)
    except HistoricalPageError:
        raise
    except Exception as exc:
        raise HistoricalPageError("image_page_render_failed") from exc
