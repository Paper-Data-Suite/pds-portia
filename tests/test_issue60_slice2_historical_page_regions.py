"""Issue #60 Slice 2: guarded historical source-page authority (synthetic only)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path
from PIL import Image
from reportlab.pdfgen import canvas

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.capture.form_catalog import installed_capture_page_specs
from portia.intake import (
    FilePageRouteDispatchService,
    FileRetainFirstIntakeService,
    PageQrDiscovery,
    SourceQrDiscovery,
)
from portia.intake.historical_page_regions import (
    BoundedPageRaster,
    FileHistoricalPageRegionService,
    HistoricalPageError,
)
from portia.intake.interpretation_profiles import LOCAL_CANDIDATES_V1
from portia.intake.page_records import FilePageRecordService
from portia.models import CaptureBatchV1, PageTargetV2

CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}
ROOT = Path(__file__).resolve().parents[1]
PROFILE = LOCAL_CANDIDATES_V1.wire_identity()


class Authorized:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.operations: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.operations.append(operation)
        if not self.allowed or class_id != CLASS:
            raise PermissionError("denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def _fixture(name: str) -> dict[str, object]:
    raw = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def _setup(tmp_path: Path, *, pdf: bool = True, count: int = 2):
    root = tmp_path / "workspace"
    root.mkdir()
    metadata = class_metadata_path(root, CLASS)
    metadata.parent.mkdir(parents=True)
    write_class_metadata(
        metadata,
        create_class_metadata(
            CLASS, "2026-2027", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc)
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(root)
    batches.create_or_load(
        CaptureBatchV1(_fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    pages = FilePageTargetService(root, batch_service=batches)
    routes = FilePageRouteService(root, batch_service=batches, page_service=pages)
    spec = installed_capture_page_specs()[0]
    raw = _fixture(
        "tests/fixtures/issue_56/slice_2/valid/page-target-v2-classroom-observation.json"
    )
    raw.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id="ptgt_first",
        page_index=7,
        template_identity=spec.template_identity(),
        entry_layout=spec.entry_layout(),
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    target = pages.create_or_load(PageTargetV2(raw), authorization=auth)
    ready = routes.register_or_load(target, authorization=auth)
    assert ready.status == "verified" and ready.locator is not None
    original = tmp_path / ("source.pdf" if pdf else "source.png")
    if pdf:
        printer = canvas.Canvas(str(original), pagesize=(612, 792))
        for index in range(count):
            printer.drawString(80, 730, f"Synthetic page {index + 1}")
            printer.showPage()
        printer.save()
    else:
        Image.new("RGB", (800, 1000), "white").save(original)
        count = 1
    retained = FileRetainFirstIntakeService(root).admit_and_retain(original)
    assert retained.page_count == count
    found = SourceQrDiscovery(
        retained,
        tuple(
            PageQrDiscovery(
                retained.page_identity(i), "candidate_unverified", ready.locator
            )
            for i in range(1, count + 1)
        ),
    )
    routed = FilePageRouteDispatchService(root).verify(found, authorization=auth)
    received = FilePageRecordService(root).record(routed, authorization=auth)
    assert received.accepted == count
    ids = tuple(
        item.record.logical_id for item in received.pages if item.record is not None
    )
    assert len(ids) == count
    return root, auth, retained, ids


def _inventory(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_exact_persisted_receipt_and_second_physical_page_resolve_read_only(
    tmp_path: Path,
) -> None:
    root, auth, retained, ids = _setup(tmp_path)
    before = _inventory(root)
    service = FileHistoricalPageRegionService(root)
    resolved = service.resolve(
        CLASS, WORK, ids[1], authorization=auth, profile_identity=PROFILE
    )
    assert resolved.source_page_number == 2
    assert resolved.plan.layout.page_ordinal == 1  # NOT physical PDF page number
    assert resolved.receipt.field("page_target_id") == "ptgt_first"
    assert (
        resolved.retained.core_source.source_sha256
        == retained.core_source.source_sha256
    )
    assert (
        resolved.plan.layout.entries[1].mapping_disposition == "requires_target_choice"
    )
    assert _inventory(root) == before
    assert "capture_interpretation.resolve" in auth.operations


def test_pdf_page_raster_is_ephemeral_and_unregistered(tmp_path: Path) -> None:
    pytest.importorskip("pymupdf")
    root, auth, _retained, ids = _setup(tmp_path)
    raster = FileHistoricalPageRegionService(root).rasterize(
        CLASS, WORK, ids[1], authorization=auth, profile_identity=PROFILE
    )
    assert raster.source_page_number == 2
    assert raster.registration == "unregistered"
    assert raster.width > 0 and raster.height > 0
    assert len(raster.pixels) == raster.width * raster.height
    assert b"pixels=" not in repr(raster).encode("utf-8")


def test_image_source_can_render_without_invented_page_registration(
    tmp_path: Path,
) -> None:
    root, auth, _retained, ids = _setup(tmp_path, pdf=False)
    raster = FileHistoricalPageRegionService(root).rasterize(
        CLASS, WORK, ids[0], authorization=auth, profile_identity=PROFILE
    )
    assert (raster.width, raster.height, raster.source_page_number) == (800, 1000, 1)
    assert raster.registration == "unregistered"


def test_denied_authorization_stops_before_source_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _auth, _retained, ids = _setup(tmp_path)
    service = FileHistoricalPageRegionService(root)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("cannot access source before class authorization")

    monkeypatch.setattr(service, "_recover_exact", forbidden)
    denied = Authorized(False)
    with pytest.raises(PermissionError):
        service.resolve(
            CLASS, WORK, ids[0], authorization=denied, profile_identity=PROFILE
        )
    assert denied.operations == ["capture_interpretation.resolve"]


def test_tampered_core_source_fails_closed_without_retain_or_write(
    tmp_path: Path,
) -> None:
    root, auth, retained, ids = _setup(tmp_path)
    source = retained.core_source.retained_source_path
    original = source.read_bytes()
    source.write_bytes(original + b"% synthetic mutation after intake\n")
    before = _inventory(root)
    with pytest.raises((HistoricalPageError, RuntimeError, ValueError)):
        FileHistoricalPageRegionService(root).resolve(
            CLASS, WORK, ids[0], authorization=auth, profile_identity=PROFILE
        )
    assert _inventory(root) == before
    assert source.read_bytes() != original


def test_wrong_receipt_id_or_unknown_profile_never_uses_fallback(
    tmp_path: Path,
) -> None:
    root, auth, _retained, ids = _setup(tmp_path)
    service = FileHistoricalPageRegionService(root)
    with pytest.raises(HistoricalPageError, match="page_record_unavailable"):
        service.resolve(
            CLASS,
            WORK,
            "prec_nonexistent",
            authorization=auth,
            profile_identity=PROFILE,
        )
    with pytest.raises(ValueError, match="unsupported_interpreter_or_mapping_profile"):
        service.resolve(
            CLASS,
            WORK,
            ids[0],
            authorization=auth,
            profile_identity={**PROFILE, "interpreter_version": "latest"},
        )


def test_raster_rejects_bad_dimensions_without_retaining_bytes() -> None:
    with pytest.raises(HistoricalPageError, match="invalid_page_raster"):
        BoundedPageRaster(10, 10, 1, b"short")
    with pytest.raises(HistoricalPageError, match="invalid_page_raster"):
        BoundedPageRaster(10, 10, 0, b"x" * 100)
