"""#59 Slice 3: synthetic physical-page QR decoding, no route or domain writes."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
import qrcode
from pds_core.pds2 import serialize_pds2_payload
from pds_core.routing_models import ModuleWorkRef, RouteLocator
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from portia.intake import (
    FilePageQrDiscoveryService,
    FileRetainFirstIntakeService,
    IntakeSourceError,
    PageQrDiscovery,
    QrDiscoveryError,
    SourceSafetyLimits,
    recognition,
)


def _payload(index: int, *, module: str = "portia") -> str:
    return serialize_pds2_payload(
        RouteLocator(
            "PDS2",
            ModuleWorkRef(module, "class_synthetic", "cbat_batch_synthetic"),
            f"route_synthetic_{index:02d}",
        )
    )


def _qr_image(text: str) -> Image.Image:
    code = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M, border=4, box_size=8
    )
    code.add_data(text)
    code.make(fit=True)
    return code.make_image(fill_color="black", back_color="white").convert("RGB")


def _pdf(path: Path, values: list[list[str]]) -> None:
    writer = canvas.Canvas(str(path), pagesize=(612, 792))
    for index, page in enumerate(values):
        writer.setFont("Helvetica", 14)
        writer.drawString(45, 720, f"Synthetic return sheet {index + 1}")
        for i, value in enumerate(page):
            png = io.BytesIO()
            _qr_image(value).save(png, format="PNG")
            png.seek(0)
            writer.drawImage(ImageReader(png), 50 + i * 220, 470, width=180, height=180)
        writer.showPage()
    writer.save()


def _retained(tmp_path: Path, source_file: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return workspace, FileRetainFirstIntakeService(workspace).admit_and_retain(
        source_file
    )


def test_one_ten_page_pdf_decodes_each_original_source_page(tmp_path: Path) -> None:
    # Includes ordinary target routes, one blank, foreign module, invalid QR,
    # and two conflicting valid QRs. Physical sheet order is arbitrary.
    codes = [[_payload(x)] for x in (8, 3, 1, 9, 2, 5)]
    codes += [[], [_payload(15, module="scoreform")], ["not a PDS2 route"]]
    codes += [[_payload(4), _payload(6)]]
    pdf = tmp_path / "batch.pdf"
    _pdf(pdf, codes)
    workspace, retained = _retained(tmp_path, pdf)
    assert retained.page_count == 10
    before = hashlib.sha256(
        retained.core_source.retained_source_path.read_bytes()
    ).hexdigest()
    results = FilePageQrDiscoveryService(workspace).discover(retained)
    assert len(results.pages) == 10
    assert [item.identity.source_page_number for item in results.pages] == list(
        range(1, 11)
    )
    assert [item.status for item in results.pages] == [
        "candidate_unverified",
        "candidate_unverified",
        "candidate_unverified",
        "candidate_unverified",
        "candidate_unverified",
        "candidate_unverified",
        "missing_qr",
        "foreign_module",
        "invalid_qr",
        "ambiguous_qr",
    ]
    assert results.candidates == 6
    assert [p.candidate_locator.route_id for p in results.pages[:6]] == [
        f"route_synthetic_{i:02d}" for i in (8, 3, 1, 9, 2, 5)
    ]
    assert all(p.candidate_locator is None for p in results.pages[6:])
    assert (
        hashlib.sha256(
            retained.core_source.retained_source_path.read_bytes()
        ).hexdigest()
        == before
    )
    assert all(not (workspace / kind).exists() for kind in ("portia", "captures"))


@pytest.mark.parametrize("extension", ["png", "jpg"])
def test_mobile_style_image_decodes_and_preserves_source_page_one(
    tmp_path: Path, extension: str
) -> None:
    image = Image.new("RGB", (1050, 1100), "white")
    qr = _qr_image(_payload(17)).resize((400, 400))
    image.paste(qr, (100, 90))
    path = tmp_path / f"phone.{extension}"
    image.save(path, format="PNG" if extension == "png" else "JPEG", quality=97)
    workspace, retained = _retained(tmp_path, path)
    result = FilePageQrDiscoveryService(workspace).discover(retained)
    assert result.pages[0].status == "candidate_unverified"
    assert result.pages[0].identity.source_page_number == 1
    assert result.pages[0].candidate_locator.route_id == "route_synthetic_17"


def test_post_retention_tampering_blocks_discovery(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    _pdf(pdf, [[_payload(1)]])
    workspace, retained = _retained(tmp_path, pdf)
    path = retained.core_source.retained_source_path
    original = path.read_bytes()
    path.write_bytes(b"?" + original[1:])
    with pytest.raises(IntakeSourceError, match="Core-retained bytes changed"):
        FilePageQrDiscoveryService(workspace).discover(retained)


def test_no_route_authority_for_foreign_invalid_or_ambiguous(tmp_path: Path) -> None:
    pdf = tmp_path / "a.pdf"
    _pdf(pdf, [[_payload(1)]])
    workspace, retained = _retained(tmp_path, pdf)
    identity = retained.page_identity(1)
    for values, expected in [
        ((_payload(1, module="quillan"),), "foreign_module"),
        (("PDS2|m=portia|c=x|w=y|r=z|extra=bad",), "invalid_qr"),
        ((_payload(1), _payload(2)), "ambiguous_qr"),
        ((), "missing_qr"),
    ]:
        result = recognition._classify(identity, values)
        assert result.status == expected
        assert result.candidate_locator is None
    assert recognition._classify(identity, (), True).status == "unreadable_qr"
    assert (
        recognition._classify(identity, (_payload(1),), True).status == "ambiguous_qr"
    )
    with pytest.raises(ValueError, match="candidate requires"):
        PageQrDiscovery(identity, "candidate_unverified")


def test_backend_missing_is_explicit_failure_not_missing_qr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    image = tmp_path / "sample.png"
    _qr_image(_payload(4)).save(image, format="PNG")
    workspace, retained = _retained(tmp_path, image)
    loader = recognition.importlib.import_module

    def missing(name: str):
        if name == "cv2":
            raise ImportError("unavailable")
        return loader(name)

    monkeypatch.setattr(recognition.importlib, "import_module", missing)
    with pytest.raises(QrDiscoveryError, match="scan extra"):
        FilePageQrDiscoveryService(workspace).discover(retained)


def test_lower_pixel_budget_produces_bounded_per_page_outcome(tmp_path: Path) -> None:
    pdf = tmp_path / "wide.pdf"
    _pdf(pdf, [[_payload(1)], [_payload(2)]])
    workspace, retained = _retained(tmp_path, pdf)
    limits = SourceSafetyLimits(max_page_pixels=1000)
    results = FilePageQrDiscoveryService(workspace, limits=limits).discover(retained)
    assert [p.status for p in results.pages] == ["render_failed", "render_failed"]
    assert all(p.candidate_locator is None for p in results.pages)


def test_injected_single_pdf_page_failure_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf = tmp_path / "batch.pdf"
    _pdf(pdf, [[_payload(1)], [_payload(2)]])
    workspace, retained = _retained(tmp_path, pdf)
    original = recognition._decode
    count = 0

    def partial(gray, cv2, np):
        nonlocal count
        count += 1
        if count == 1:
            raise RuntimeError("injected renderer/QR failure")
        return original(gray, cv2, np)

    monkeypatch.setattr(recognition, "_decode", partial)
    results = FilePageQrDiscoveryService(workspace).discover(retained)
    assert [r.status for r in results.pages] == [
        "render_failed",
        "candidate_unverified",
    ]


def test_requires_retained_source_not_arbitrary_path(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="Core-retained"):
        FilePageQrDiscoveryService(tmp_path).discover(tmp_path)  # type: ignore[arg-type]
