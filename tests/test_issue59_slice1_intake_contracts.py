"""#59 Slice 1: read-only intake contracts, never ingestion claims."""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.scan_retention import RetainedSourceScan

from portia.intake import (
    DEFAULT_SOURCE_LIMITS,
    IntakeContractError,
    RetainedPageIdentity,
    SourceFormat,
    SourceSafetyLimits,
    assess_source_signature,
)

PDF = b"%PDF-1.7\n1 0 obj\n"
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF"
PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    + (2550).to_bytes(4, "big")
    + (3300).to_bytes(4, "big")
)


@pytest.mark.parametrize(
    ("name", "header", "format_"),
    [
        ("batch.PDF", PDF, SourceFormat.PDF),
        ("photo.jpg", JPEG, SourceFormat.JPEG),
        ("photo.JPEG", JPEG, SourceFormat.JPEG),
        ("scan.png", PNG, SourceFormat.PNG),
    ],
)
def test_supported_source_headers_are_candidates_not_verified(
    name: str, header: bytes, format_: SourceFormat
) -> None:
    result = assess_source_signature(name, 5000, header)
    assert result.candidate
    assert result.code == "candidate_unverified"
    assert result.source_format is format_


@pytest.mark.parametrize(
    "name", ["pages.tif", "pages.tiff", "paper.gif", "archive.zip"]
)
def test_unsupported_formats_are_explicit(name: str) -> None:
    result = assess_source_signature(name, 1000, PDF)
    assert result.code == "unsupported_format"
    assert not result.candidate


@pytest.mark.parametrize(
    "name", ["", " ", "../page.pdf", r"C:\page.pdf", "x/y.png", "a\x00.pdf", ".", ".."]
)
def test_filename_must_be_safe_basename(name: str) -> None:
    assert assess_source_signature(name, 100, PDF).code == "invalid_source_name"


def test_misnamed_jpeg_and_pdfs_never_pass_signature_gate() -> None:
    assert assess_source_signature("image.jpg", 100, PDF).code == "signature_mismatch"
    assert assess_source_signature("image.pdf", 100, JPEG).code == "signature_mismatch"
    assert assess_source_signature("image.png", 100, JPEG).code == "signature_mismatch"


def test_short_prefix_is_not_claimed_as_valid_image() -> None:
    assert assess_source_signature("x.jpg", 100, b"\xff").code == "insufficient_header"
    assert assess_source_signature("x.png", 100, PNG[:12]).code == "insufficient_header"
    assert assess_source_signature("x.pdf", 100, b"").code == "insufficient_header"


def test_bounded_pdf_header_is_only_a_candidate() -> None:
    result = assess_source_signature("a.pdf", 100, b"%trash" + PDF)
    assert result.candidate
    assert (
        assess_source_signature("a.pdf", 100, b"garbage").code == "signature_mismatch"
    )


def test_png_zero_or_overlarge_dimensions_rejected_without_decoder() -> None:
    def png_with_dimensions(w: int, h: int) -> bytes:
        return PNG[:16] + w.to_bytes(4, "big") + h.to_bytes(4, "big")

    assert (
        assess_source_signature("a.png", 100, png_with_dimensions(0, 10)).code
        == "invalid_png_dimensions"
    )
    assert (
        assess_source_signature("a.png", 100, png_with_dimensions(9000, 9000)).code
        == "invalid_png_dimensions"
    )


def test_invalid_and_oversized_sources_rejected() -> None:
    assert assess_source_signature("x.pdf", 0, PDF).code == "invalid_source_size"
    assert assess_source_signature("x.pdf", True, PDF).code == "invalid_source_size"
    assert (
        assess_source_signature(
            "x.pdf", DEFAULT_SOURCE_LIMITS.max_source_bytes + 1, PDF
        ).code
        == "source_too_large"
    )


def test_misused_unbounded_header_or_policy_rejected() -> None:
    with pytest.raises(IntakeContractError):
        assess_source_signature("x.pdf", 100, b"x" * 1025)
    with pytest.raises(IntakeContractError):
        assess_source_signature("x.pdf", 100, PDF, limits=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_pages": 0},
        {"max_pages": 129},
        {"max_source_bytes": -1},
        {"max_source_bytes": 256 * 1024 * 1024 + 1},
        {"max_page_pixels": 32_000_001},
        {"max_page_pixels": True},
        {"raster_dpi": 99},
        {"raster_dpi": 301},
        {"raster_dpi": True},
    ],
)
def test_hard_security_boundaries(kwargs: dict[str, int | bool]) -> None:
    with pytest.raises(IntakeContractError):
        SourceSafetyLimits(**kwargs)


def _core_source(scan_id: str) -> RetainedSourceScan:
    return RetainedSourceScan(
        source_scan_id=scan_id,
        source_filename="returned.pdf",
        source_sha256=hashlib.sha256(b"test-pdf-content").hexdigest(),
        retained_source_path=Path("/synthetic/nonexistent/returned.pdf"),
        retained_source_relative_path="scans/source/synthetic/returned.pdf",
        intake_timestamp=datetime(2026, 10, 17, tzinfo=timezone.utc),
        intake_date=datetime(2026, 10, 17, tzinfo=timezone.utc).date(),
    )


def test_physical_source_identity_is_not_a_print_route() -> None:
    a = RetainedPageIdentity.from_core(_core_source("scan_one"), 1)
    b = RetainedPageIdentity.from_core(_core_source("scan_two"), 1)
    c = RetainedPageIdentity.from_core(_core_source("scan_one"), 2)
    assert len({a, b, c}) == 3
    assert a.page_record_source_ref() == {
        "source_scan_id": "scan_one",
        "source_sha256": hashlib.sha256(b"test-pdf-content").hexdigest(),
        "source_page_number": 1,
    }
    with pytest.raises(FrozenInstanceError):
        a.source_scan_id = "changed"  # type: ignore[misc]


def test_page_identity_rejects_non_core_and_bad_provenance() -> None:
    with pytest.raises(IntakeContractError):
        RetainedPageIdentity.from_core(object(), 1)  # type: ignore[arg-type]
    with pytest.raises(IntakeContractError):
        RetainedPageIdentity.from_core(_core_source("scan_one"), 0)
    with pytest.raises(IntakeContractError):
        RetainedPageIdentity.from_core(_core_source("scan_one"), True)  # type: ignore[arg-type]
    with pytest.raises(IntakeContractError):
        RetainedPageIdentity("scan_one", "A" * 64, 1)
    with pytest.raises(IntakeContractError):
        RetainedPageIdentity("not_core", "a" * 64, 1)


def test_intake_contract_functions_have_no_filesystem_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("intake contract attempted filesystem I/O")

    monkeypatch.setattr("builtins.open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert assess_source_signature("test.pdf", 100, PDF).candidate
    ref = RetainedPageIdentity.from_core(_core_source("scan_one"), 1)
    assert ref.source_page_number == 1
