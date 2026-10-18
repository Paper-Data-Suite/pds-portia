"""#59 Slice 2: bounded preflight and exact Core custody, not QR/Page Records."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.scan_retention import RetainedSourceScan
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from portia.intake import (
    FileRetainFirstIntakeService,
    IntakeSourceError,
    SourceFormat,
    SourceSafetyLimits,
)
from portia.intake import retention as intake_mod


def _pdf(path: Path, pages: int = 2, *, size: tuple[int, int] = (612, 792)) -> None:
    writer = canvas.Canvas(str(path), pagesize=size)
    for index in range(pages):
        writer.drawString(30, 40, f"Synthetic sheet {index + 1}")
        writer.showPage()
    writer.save()


def _image(path: Path, mode: str = "RGB") -> None:
    Image.new(mode, (80, 100)).save(path)


@pytest.fixture
def service(tmp_path: Path) -> FileRetainFirstIntakeService:
    (tmp_path / "workspace").mkdir()
    return FileRetainFirstIntakeService(tmp_path / "workspace")


@pytest.fixture
def fake_core(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Stub Core only to make tests independent of mutable machine workspaces."""
    calls: list[Path] = []

    def retained(root: str | Path, original: str | Path) -> RetainedSourceScan:
        source = Path(original)
        calls.append(source)
        target = Path(root) / "scans" / "source" / "2026-10-17" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        return RetainedSourceScan(
            source_scan_id="scan_test_source_01",
            source_filename=source.name,
            source_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            retained_source_path=target,
            retained_source_relative_path=target.relative_to(root).as_posix(),
            intake_timestamp=datetime(2026, 10, 17, tzinfo=timezone.utc),
            intake_date=datetime(2026, 10, 17, tzinfo=timezone.utc).date(),
        )

    monkeypatch.setattr(intake_mod, "retain_source_scan", retained)
    return calls


def test_multi_page_pdf_kept_as_one_exact_core_source(
    tmp_path: Path, service: FileRetainFirstIntakeService, fake_core: list[Path]
) -> None:
    original = tmp_path / "ten_pages.pdf"
    _pdf(original, pages=10)
    bytes_before = original.read_bytes()
    result = service.admit_and_retain(original)
    assert result.source_format is SourceFormat.PDF
    assert result.page_count == 10
    assert result.byte_count == len(bytes_before)
    assert result.core_source.retained_source_path.read_bytes() == bytes_before
    assert original.read_bytes() == bytes_before
    assert fake_core == [original]
    assert [result.page_identity(n).source_page_number for n in (1, 5, 10)] == [
        1,
        5,
        10,
    ]
    with pytest.raises(IntakeSourceError):
        result.page_identity(11)
    with pytest.raises(IntakeSourceError):
        result.page_identity(True)  # type: ignore[arg-type]
    # No Page Record, interpretation or domain work was created.
    assert not (service.root / "classes").exists()


@pytest.mark.parametrize(
    "ext,mode", [("png", "RGB"), ("png", "L"), ("jpg", "L"), ("jpg", "RGB")]
)
def test_real_images_decode_and_retain(
    ext: str,
    mode: str,
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / f"photo.{ext}"
    _image(original, mode)
    result = service.admit_and_retain(original)
    assert result.page_count == 1
    assert result.source_format in (SourceFormat.PNG, SourceFormat.JPEG)
    assert result.core_source.retained_source_path.read_bytes() == original.read_bytes()
    assert len(fake_core) == 1


def test_preflight_is_read_only_and_core_is_not_called(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / "paper.pdf"
    _pdf(original)
    preflight = service.preflight(original)
    assert preflight.page_count == 2
    assert preflight.byte_count == original.stat().st_size
    assert preflight.source_sha256 == hashlib.sha256(original.read_bytes()).hexdigest()
    assert fake_core == []
    assert list(service.root.iterdir()) == []


@pytest.mark.parametrize(
    "suffix,content",
    [
        ("pdf", b"%PDF-1.7\nnot a document"),
        ("png", b"bad"),
        ("jpg", b"\xff\xd8\xffgarbage"),
    ],
)
def test_corrupt_sources_fail_before_core(
    suffix: str,
    content: bytes,
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / f"corrupt.{suffix}"
    original.write_bytes(content)
    with pytest.raises(IntakeSourceError):
        service.admit_and_retain(original)
    assert fake_core == []


def test_encrypted_pdf_rejected_before_core(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    source = tmp_path / "plain.pdf"
    _pdf(source)
    reader = PdfReader(source)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("password")
    secret = tmp_path / "secret.pdf"
    with secret.open("wb") as out:
        writer.write(out)
    with pytest.raises(IntakeSourceError, match="encrypted PDF") as failure:
        service.admit_and_retain(secret)
    assert failure.value.code == "protected_document"
    assert fake_core == []


def test_pdf_page_count_ceiling(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / "too_many.pdf"
    _pdf(original, pages=3)
    restricted = FileRetainFirstIntakeService(
        service.root, limits=SourceSafetyLimits(max_pages=2)
    )
    with pytest.raises(IntakeSourceError) as failure:
        restricted.admit_and_retain(original)
    assert failure.value.code == "too_many_pages"
    assert fake_core == []


def test_oversized_pdf_geometry_rejected(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / "huge.pdf"
    _pdf(original, pages=1, size=(1400, 1400))
    limited = FileRetainFirstIntakeService(
        service.root, limits=SourceSafetyLimits(max_page_pixels=1000)
    )
    with pytest.raises(IntakeSourceError) as failure:
        limited.admit_and_retain(original)
    assert failure.value.code == "page_too_large"
    assert fake_core == []


def test_limit_rejects_source_before_core(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    original = tmp_path / "source.pdf"
    _pdf(original)
    limited = FileRetainFirstIntakeService(
        service.root, limits=SourceSafetyLimits(max_source_bytes=25)
    )
    with pytest.raises(IntakeSourceError) as failure:
        limited.admit_and_retain(original)
    assert failure.value.code == "source_rejected"
    assert fake_core == []


def test_symlink_source_and_parent_rejected(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
) -> None:
    real = tmp_path / "real.pdf"
    _pdf(real)
    link = tmp_path / "link.pdf"
    folder = tmp_path / "linkdir"
    try:
        link.symlink_to(real)
        folder.symlink_to(tmp_path, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink privilege unavailable")
    for candidate in (link, folder / real.name):
        with pytest.raises(IntakeSourceError) as failure:
            service.admit_and_retain(candidate)
        assert failure.value.code == "unsafe_path"
    assert fake_core == []


def test_retained_content_tamper_fails_closed_but_core_custody_remains(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tmp_path / "safe.pdf"
    _pdf(original)
    retained_path = service.root / "scans" / "source" / "2026-10-17" / "safe.pdf"

    def corrupted(root: str | Path, source: str | Path) -> RetainedSourceScan:
        retained_path.parent.mkdir(parents=True, exist_ok=True)
        retained_path.write_bytes(b"corrupt")
        return RetainedSourceScan(
            source_scan_id="scan_test_source_01",
            source_filename="safe.pdf",
            source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
            retained_source_path=retained_path,
            retained_source_relative_path=retained_path.relative_to(root).as_posix(),
            intake_timestamp=datetime.now(timezone.utc),
            intake_date=datetime.now(timezone.utc).date(),
        )

    monkeypatch.setattr(intake_mod, "retain_source_scan", corrupted)
    with pytest.raises(IntakeSourceError) as failure:
        service.admit_and_retain(original)
    assert failure.value.code == "retained_integrity_failure"
    assert retained_path.read_bytes() == b"corrupt"  # Portia did not delete custody


def test_core_failure_is_not_paper_success(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tmp_path / "scan.pdf"
    _pdf(original)

    def no_core(root: str | Path, source: str | Path) -> RetainedSourceScan:
        raise RuntimeError("synthetic failure")

    monkeypatch.setattr(intake_mod, "retain_source_scan", no_core)
    with pytest.raises(IntakeSourceError) as failure:
        service.admit_and_retain(original)
    assert failure.value.code == "retention_failed"


def test_preflight_detects_changed_source(
    tmp_path: Path,
    service: FileRetainFirstIntakeService,
    fake_core: list[Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = tmp_path / "scan.pdf"
    _pdf(original)
    original_hash = intake_mod._hash_file

    def changed(source: Path, maximum: int) -> tuple[str, int]:
        result = original_hash(source, maximum)
        source.write_bytes(source.read_bytes() + b"change")
        return result

    monkeypatch.setattr(intake_mod, "_hash_file", changed)
    with pytest.raises(IntakeSourceError) as failure:
        service.admit_and_retain(original)
    assert failure.value.code == "source_changed"
    assert fake_core == []


def test_installed_core_retention_end_to_end(tmp_path: Path) -> None:
    """Exercise the actual installed Core writer, not the synthetic monkeypatch."""
    root = tmp_path / "workspace"
    root.mkdir()
    source = tmp_path / "whole_stack.pdf"
    _pdf(source, pages=2)
    service = FileRetainFirstIntakeService(root)
    before = source.read_bytes()
    result = service.admit_and_retain(source)
    kept = result.core_source.retained_source_path
    assert kept.is_file()
    assert kept.read_bytes() == before
    assert result.core_source.source_sha256 == hashlib.sha256(before).hexdigest()
    assert result.page_identity(2).source_sha256 == result.core_source.source_sha256
    assert source.read_bytes() == before
    assert not (root / "classes").exists()
