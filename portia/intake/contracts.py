"""Issue #59: pure admission and retained-page identity contracts.

This module NEVER opens, stores, retains, renders, routes, or interprets a scan.
A 'candidate' result proves only that a bounded source prefix matches the
claimed format. Slice 2 must verify real bytes/content and then call Core's
retained-source writer before any page work is allowed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath, PureWindowsPath
from typing import Literal, Self

from pds_core.scan_retention import RetainedSourceScan

# Resource ceilings, not promises that the PDF/image decoder is safe. The
# actual decoder in #59 Slices 2-3 must enforce page counts, pixel counts,
# deadlines, and decompression limits independently before allocating images.
HARD_MAX_SOURCE_BYTES = 256 * 1024 * 1024
HARD_MAX_PAGES = 128
HARD_MAX_PAGE_PIXELS = 32_000_000
PDF_HEADER_PROBE_BYTES = 1024


class SourceFormat(str, Enum):
    PDF = "pdf"
    JPEG = "jpeg"
    PNG = "png"


SourceAdmissionCode = Literal[
    "candidate_unverified",
    "invalid_source_name",
    "unsupported_format",
    "invalid_source_size",
    "source_too_large",
    "insufficient_header",
    "signature_mismatch",
    "invalid_png_dimensions",
]


class IntakeContractError(ValueError):
    """A pure intake policy or provenance contract has been violated."""


@dataclass(frozen=True, slots=True)
class SourceSafetyLimits:
    """Enforceable upper bounds shared by later, side-effectful stages.

    Defaults are for a teacher's batch-scanned classroom paper. A later slice
    may introduce a *stricter* per-machine profile, never silently exceed the
    hard bounds below or assume a phone image has scanner DPI metadata.
    """

    max_source_bytes: int = 128 * 1024 * 1024
    max_pages: int = 96
    max_page_pixels: int = 24_000_000
    raster_dpi: int = 200

    def __post_init__(self) -> None:
        ceilings = (
            ("max_source_bytes", self.max_source_bytes, HARD_MAX_SOURCE_BYTES),
            ("max_pages", self.max_pages, HARD_MAX_PAGES),
            ("max_page_pixels", self.max_page_pixels, HARD_MAX_PAGE_PIXELS),
        )
        for name, value, ceiling in ceilings:
            if type(value) is not int or not 1 <= value <= ceiling:
                raise IntakeContractError(f"{name} must be within the safety ceiling")
        if type(self.raster_dpi) is not int or not 100 <= self.raster_dpi <= 300:
            raise IntakeContractError("raster_dpi must be between 100 and 300")


DEFAULT_SOURCE_LIMITS = SourceSafetyLimits()


@dataclass(frozen=True, slots=True)
class SourceAdmission:
    """Pure candidate/rejection; never evidence of custody or PDF validity."""

    code: SourceAdmissionCode
    source_format: SourceFormat | None

    @property
    def candidate(self) -> bool:
        return self.code == "candidate_unverified"


def assess_source_signature(
    filename: str,
    byte_count: int,
    first_bytes: bytes,
    *,
    limits: SourceSafetyLimits = DEFAULT_SOURCE_LIMITS,
) -> SourceAdmission:
    """Classify a filename, size and bounded prefix with NO filesystem access.

    The caller must supply the original basename and actual file size, not a
    renamed path. This is just the first gate: a plausible header does not
    prove PDF structure, decoder safety, print readability or Core retention.
    """
    if not isinstance(limits, SourceSafetyLimits):
        raise IntakeContractError("limits must be SourceSafetyLimits")
    if (
        not isinstance(filename, str)
        or not filename
        or filename != filename.strip()
        or "\x00" in filename
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
        or PureWindowsPath(filename).drive
    ):
        return SourceAdmission("invalid_source_name", None)

    extension = PurePosixPath(filename).suffix.casefold()
    formats = {
        ".pdf": SourceFormat.PDF,
        ".jpg": SourceFormat.JPEG,
        ".jpeg": SourceFormat.JPEG,
        ".png": SourceFormat.PNG,
    }
    source_format = formats.get(extension)
    if source_format is None:
        return SourceAdmission("unsupported_format", None)
    if type(byte_count) is not int or byte_count <= 0:
        return SourceAdmission("invalid_source_size", source_format)
    if byte_count > limits.max_source_bytes:
        return SourceAdmission("source_too_large", source_format)
    if not isinstance(first_bytes, bytes) or len(first_bytes) > PDF_HEADER_PROBE_BYTES:
        raise IntakeContractError("first_bytes must be at most 1024 bytes")
    if not first_bytes:
        return SourceAdmission("insufficient_header", source_format)

    if source_format is SourceFormat.PDF:
        # PDF header may occur in the first 1024 bytes. A forged/malformed
        # document can still pass; Slice 2 must parse the full retained bytes.
        if b"%PDF-" not in first_bytes:
            return SourceAdmission("signature_mismatch", source_format)
    elif source_format is SourceFormat.JPEG:
        if len(first_bytes) < 3:
            return SourceAdmission("insufficient_header", source_format)
        if not first_bytes.startswith(b"\xff\xd8\xff"):
            return SourceAdmission("signature_mismatch", source_format)
    else:
        if len(first_bytes) < 8:
            return SourceAdmission("insufficient_header", source_format)
        if not first_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return SourceAdmission("signature_mismatch", source_format)
        if len(first_bytes) < 24:
            return SourceAdmission("insufficient_header", source_format)
        if first_bytes[8:16] != b"\x00\x00\x00\rIHDR":
            return SourceAdmission("signature_mismatch", source_format)
        width = int.from_bytes(first_bytes[16:20], "big")
        height = int.from_bytes(first_bytes[20:24], "big")
        if width < 1 or height < 1 or width * height > limits.max_page_pixels:
            return SourceAdmission("invalid_png_dimensions", source_format)

    return SourceAdmission("candidate_unverified", source_format)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class RetainedPageIdentity:
    """Exactly one page within one *Core-retained source*.

    Repeated print routes do not collapse different physical-source intakes.
    A PDF's source_page_number is independent of the printed Page Target's
    page_index and template-local page_ordinal.
    """

    source_scan_id: str
    source_sha256: str
    source_page_number: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.source_scan_id, str)
            or not self.source_scan_id.startswith("scan_")
            or len(self.source_scan_id) <= 5
            or len(self.source_scan_id) > 128
            or not re.fullmatch(r"[A-Za-z0-9_-]+", self.source_scan_id)
        ):
            raise IntakeContractError("invalid Core source_scan_id")
        if not isinstance(self.source_sha256, str) or not _SHA256.fullmatch(
            self.source_sha256
        ):
            raise IntakeContractError("invalid Core source_sha256")
        if type(self.source_page_number) is not int or self.source_page_number < 1:
            raise IntakeContractError("source_page_number must be positive")

    @classmethod
    def from_core(cls, retained: RetainedSourceScan, source_page_number: int) -> Self:
        if not isinstance(retained, RetainedSourceScan):
            raise IntakeContractError("identity requires Core RetainedSourceScan")
        return cls(
            source_scan_id=retained.source_scan_id,
            source_sha256=retained.source_sha256,
            source_page_number=source_page_number,
        )

    def page_record_source_ref(self) -> dict[str, str | int]:
        """The exact `page_record@1.source_ref` field vocabulary; NO write."""
        return {
            "source_scan_id": self.source_scan_id,
            "source_sha256": self.source_sha256,
            "source_page_number": self.source_page_number,
        }
