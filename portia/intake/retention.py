"""#59 Slice 2: bounded source preflight and Core-owned retain-first intake.

Source file inspection is NOT per-page QR recognition, evidence review, or a
Page Record write.  Core is the sole writer of retained original scan bytes.
"""

from __future__ import annotations

import hashlib
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from pds_core.scan_retention import RetainedSourceScan, retain_source_scan
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader

from portia.intake.contracts import (
    DEFAULT_SOURCE_LIMITS,
    PDF_HEADER_PROBE_BYTES,
    RetainedPageIdentity,
    SourceFormat,
    SourceSafetyLimits,
    assess_source_signature,
)

_COPY_BLOCK: Final[int] = 1024 * 1024
_REPARSE_POINT: Final[int] = 0x400

IntakeFailureCode = Literal[
    "invalid_path",
    "unsafe_path",
    "source_unavailable",
    "source_changed",
    "source_rejected",
    "unsupported_content",
    "invalid_document",
    "protected_document",
    "too_many_pages",
    "page_too_large",
    "retention_failed",
    "retained_integrity_failure",
]


class IntakeSourceError(RuntimeError):
    """Intake stopped without claiming an accepted retained source."""

    def __init__(self, code: IntakeFailureCode, detail: str) -> None:
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class SourcePreflight:
    """Validated source *candidate*; NOT proof of Core custody or QR routing."""

    original_path: Path
    source_format: SourceFormat
    byte_count: int
    page_count: int
    source_sha256: str


@dataclass(frozen=True, slots=True)
class RetainedIntakeSource:
    """Exact Core-retained original plus structural page count (no Page Records)."""

    core_source: RetainedSourceScan
    source_format: SourceFormat
    byte_count: int
    page_count: int

    def page_identity(self, source_page_number: int) -> RetainedPageIdentity:
        if (
            type(source_page_number) is not int
            or not 1 <= source_page_number <= self.page_count
        ):
            raise IntakeSourceError("invalid_document", "source page is out of range")
        return RetainedPageIdentity.from_core(self.core_source, source_page_number)


class FileRetainFirstIntakeService:
    """Admit one PDF/image and use Core exclusively for original-byte custody.

    Does not create any Page Record, PDS2 route, interpretation, or domain fact.
    It must be invoked from an authorized teacher operation before class-specific
    metadata is accessed; this class cannot itself infer ownership from a scan.
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

    def preflight(self, source_file: str | Path) -> SourcePreflight:
        """Check source path and structure before calling any Core writer."""
        source = _safe_regular_source(source_file)
        before = _stat_source(source)
        if before.st_size < 1 or before.st_size > self.limits.max_source_bytes:
            raise IntakeSourceError("source_rejected", "source size is outside limits")
        try:
            with source.open("rb") as handle:
                prefix = handle.read(PDF_HEADER_PROBE_BYTES)
        except OSError as exc:
            raise IntakeSourceError("source_unavailable", "cannot read source") from exc
        admission = assess_source_signature(
            source.name, before.st_size, prefix, limits=self.limits
        )
        if not admission.candidate or admission.source_format is None:
            raise IntakeSourceError(
                "source_rejected", f"source admission rejected: {admission.code}"
            )
        kind = admission.source_format
        if kind is SourceFormat.PDF:
            count = _inspect_pdf(source, self.limits)
        else:
            count = _inspect_image(source, self.limits)
        checksum, byte_count = _hash_file(source, self.limits.max_source_bytes)
        after = _stat_source(source)
        _assert_unchanged(before, after)
        _assert_safe_path(source)
        if byte_count != before.st_size:
            raise IntakeSourceError("source_changed", "source size changed")
        return SourcePreflight(source, kind, byte_count, count, checksum)

    def admit_and_retain(self, source_file: str | Path) -> RetainedIntakeSource:
        """Preserve exact original Core bytes before any per-page work is possible.

        A failed post-retention check intentionally leaves any Core-retained
        source in place for recovery/audit.  Portia never deletes Core custody.
        """
        candidate = self.preflight(source_file)
        _assert_safe_path(candidate.original_path)
        try:
            retained = retain_source_scan(self.root, candidate.original_path)
        except (OSError, ValueError, RuntimeError) as exc:
            raise IntakeSourceError(
                "retention_failed", "Core could not retain original source"
            ) from exc
        if not isinstance(retained, RetainedSourceScan):
            raise IntakeSourceError(
                "retained_integrity_failure", "invalid Core retained-source result"
            )
        _assert_safe_path(candidate.original_path)
        if retained.source_sha256 != candidate.source_sha256:
            raise IntakeSourceError(
                "retained_integrity_failure",
                "Core retained an unexpected source digest",
            )
        # Verify exact bytes actually on disk: do not trust only Core's returned
        # metadata or reread a now-changed external original for later work.
        _assert_retained_under_root(self.root, retained)
        digest, count = _hash_file(
            retained.retained_source_path, self.limits.max_source_bytes
        )
        if digest != candidate.source_sha256 or count != candidate.byte_count:
            raise IntakeSourceError(
                "retained_integrity_failure", "retained source readback differs"
            )
        return RetainedIntakeSource(
            core_source=retained,
            source_format=candidate.source_format,
            byte_count=count,
            page_count=candidate.page_count,
        )


def _assert_safe_path(path: Path) -> None:
    """Reject link/junction components, including source-file reparse points."""
    for component in (path, *path.parents):
        try:
            mode = component.lstat()
        except OSError as exc:
            raise IntakeSourceError(
                "source_unavailable", "source path vanished"
            ) from exc
        if stat.S_ISLNK(mode.st_mode) or (
            getattr(mode, "st_file_attributes", 0) & _REPARSE_POINT
        ):
            raise IntakeSourceError("unsafe_path", "source path contains a link")


def _safe_regular_source(value: str | Path) -> Path:
    if not isinstance(value, (str, Path)):
        raise IntakeSourceError("invalid_path", "source must be a file path")
    try:
        raw = Path(value)
        if any(part == ".." for part in raw.parts):
            raise IntakeSourceError("unsafe_path", "source path contains traversal")
        path = raw.absolute()
        _assert_safe_path(path)
        if not path.is_file():
            raise IntakeSourceError("source_unavailable", "source is not a file")
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        if isinstance(exc, IntakeSourceError):
            raise
        raise IntakeSourceError("invalid_path", "invalid source path") from exc
    return path


def _stat_source(path: Path) -> os.stat_result:
    try:
        status = path.stat()
    except OSError as exc:
        raise IntakeSourceError("source_unavailable", "source is unavailable") from exc
    if not stat.S_ISREG(status.st_mode):
        raise IntakeSourceError("source_unavailable", "source is not regular")
    return status


def _assert_unchanged(before: os.stat_result, after: os.stat_result) -> None:
    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ctime_ns != after.st_ctime_ns
    ):
        raise IntakeSourceError("source_changed", "source changed during preflight")


def _hash_file(path: Path, maximum: int) -> tuple[str, int]:
    checksum = hashlib.sha256()
    count = 0
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(_COPY_BLOCK), b""):
                count += len(block)
                if count > maximum:
                    raise IntakeSourceError(
                        "source_rejected", "source exceeds size limit"
                    )
                checksum.update(block)
    except OSError as exc:
        raise IntakeSourceError("source_unavailable", "cannot read source") from exc
    return checksum.hexdigest(), count


def _inspect_pdf(path: Path, limits: SourceSafetyLimits) -> int:
    """Validate PDF structure/page geometry; raster decoding belongs to Slice 3."""
    try:
        with path.open("rb") as handle:
            reader = PdfReader(handle, strict=True)
            if reader.is_encrypted:
                raise IntakeSourceError(
                    "protected_document", "encrypted PDF unsupported"
                )
            count = len(reader.pages)
            if not 1 <= count <= limits.max_pages:
                raise IntakeSourceError(
                    "too_many_pages", "PDF page count outside limits"
                )
            for page in reader.pages:
                width_pt = float(page.mediabox.width)
                height_pt = float(page.mediabox.height)
                if (
                    not math.isfinite(width_pt)
                    or not math.isfinite(height_pt)
                    or width_pt <= 0
                    or height_pt <= 0
                ):
                    raise IntakeSourceError("invalid_document", "invalid PDF page size")
                width_pixels = math.ceil(width_pt * limits.raster_dpi / 72)
                height_pixels = math.ceil(height_pt * limits.raster_dpi / 72)
                if width_pixels * height_pixels > limits.max_page_pixels:
                    raise IntakeSourceError(
                        "page_too_large", "PDF page exceeds raster pixel budget"
                    )
            return count
    except IntakeSourceError:
        raise
    except Exception as exc:  # untrusted decoder errors must fail closed
        raise IntakeSourceError(
            "invalid_document", "PDF is not safely readable"
        ) from exc


def _inspect_image(path: Path, limits: SourceSafetyLimits) -> int:
    """Verify image bytes with ReportLab's installed raster backend.

    JPEG/PNG image decoding is deliberately bounded by size and total pixels;
    no OCR or QR reading occurs. ReportLab's ImageReader uses its Pillow image
    backend, already a required dependency of the existing PDF renderer.
    """
    try:
        reader = ImageReader(str(path))
        width, height = reader.getSize()
        if type(width) is not int or type(height) is not int or width < 1 or height < 1:
            raise IntakeSourceError("invalid_document", "invalid image dimensions")
        if width * height > limits.max_page_pixels:
            raise IntakeSourceError("page_too_large", "image exceeds pixel budget")
        # Structural metadata is not enough; force decode so truncated files
        # cannot be accepted just because their JPEG/PNG header is plausible.
        pixels = reader.getRGBData()
        if len(pixels) not in {width * height, width * height * 3, width * height * 4}:
            raise IntakeSourceError("invalid_document", "unexpected decoded image size")
    except IntakeSourceError:
        raise
    except Exception as exc:  # untrusted decoder errors must fail closed
        raise IntakeSourceError("invalid_document", "image cannot be decoded") from exc
    return 1


def _assert_retained_under_root(root: Path, retained: RetainedSourceScan) -> None:
    try:
        workspace = root.resolve(strict=True)
        relative = retained.retained_source_path.resolve(strict=True).relative_to(
            workspace
        )
        expected = Path(retained.retained_source_relative_path)
        if expected.is_absolute() or ".." in expected.parts or relative != expected:
            raise IntakeSourceError(
                "retained_integrity_failure", "Core retained source path disagrees"
            )
        _assert_safe_path(retained.retained_source_path)
    except IntakeSourceError:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        raise IntakeSourceError(
            "retained_integrity_failure", "Core retained source is not available"
        ) from exc
