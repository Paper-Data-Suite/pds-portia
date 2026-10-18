"""#59 Slice 5: durable Page Record receipts and bounded partial recovery."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path, safe_module_work_descendant
from pds_core.routing_models import ModuleWorkRef
from PIL import Image
from reportlab.pdfgen import canvas

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.intake import (
    FilePageRouteDispatchService,
    FileRetainFirstIntakeService,
    PageQrDiscovery,
    SourceQrDiscovery,
)
from portia.intake.page_records import FilePageRecordService
from portia.models import CaptureBatchV1, PageTargetV2
from portia.storage.errors import PortiaStorageError

CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}
ROOT = Path(__file__).resolve().parents[1]


class Authorized:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.actions: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.actions.append(operation)
        if not self.allowed or class_id != CLASS:
            raise PermissionError("not authorized")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def _fixture(name: str) -> dict[str, object]:
    result = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def _setup(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    path = class_metadata_path(workspace, CLASS)
    path.parent.mkdir(parents=True)
    write_class_metadata(
        path,
        create_class_metadata(
            CLASS,
            "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(workspace)
    batches.create_or_load(
        CaptureBatchV1(_fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    pages = FilePageTargetService(workspace, batch_service=batches)
    routes = FilePageRouteService(workspace, batch_service=batches, page_service=pages)
    return workspace, auth, batches, pages, routes


def _target(pages, routes, auth, *, ident="ptgt_one", index=1):
    data = _fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    data.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id=ident,
        page_index=index,
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    target = pages.create_or_load(PageTargetV2(data), authorization=auth)
    result = routes.register_or_load(target, authorization=auth)
    assert result.status == "verified"
    assert result.locator is not None
    return result.locator


def _discovery(workspace: Path, source: Path, locators):
    retained = FileRetainFirstIntakeService(workspace).admit_and_retain(source)
    assert retained.page_count == len(locators)
    outcomes = tuple(
        PageQrDiscovery(
            retained.page_identity(i),
            "candidate_unverified" if locator is not None else "missing_qr",
            locator,
        )
        for i, locator in enumerate(locators, 1)
    )
    discovered = SourceQrDiscovery(retained, outcomes)
    routed = FilePageRouteDispatchService(workspace).verify(
        discovered, authorization=Authorized()
    )
    return retained, routed


def _image(path: Path, color: str = "white") -> None:
    Image.new("RGB", (100, 110), color).save(path, format="PNG")


def _pdf(path: Path, pages: int) -> None:
    writer = canvas.Canvas(str(path), pagesize=(612, 792))
    for n in range(pages):
        writer.drawString(50, 700, f"Synthetic page {n + 1}")
        writer.showPage()
    writer.save()


def _receipt_files(root: Path) -> list[Path]:
    coll = safe_module_work_descendant(
        root,
        ModuleWorkRef("portia", CLASS, WORK),
        "records/capture_page_record",
    )
    return sorted(coll.glob("*.json")) if coll.exists() else []


def test_exact_replay_reuses_unchanged_receipt_and_core_bytes(tmp_path: Path) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    original = tmp_path / "scan.png"
    _image(original)
    retained, routed = _discovery(root, original, [locator])
    source = retained.core_source.retained_source_path
    source_bytes = source.read_bytes()
    service = FilePageRecordService(root)
    first = service.record(routed, authorization=auth)
    assert first.accepted == 1 and not first.completed_with_exceptions
    assert first.pages[0].status == "created"
    assert first.pages[0].record is not None
    wire = first.pages[0].record.to_dict()
    assert wire["processing_state"] == "received"
    assert wire["route_id"] == locator.route_id
    assert wire["source_ref"] == retained.page_identity(1).page_record_source_ref()
    assert wire["page_target_id"] == "ptgt_one"
    assert wire["created_by"] == ACTOR
    paths = _receipt_files(root)
    assert len(paths) == 1
    old = paths[0].read_bytes()
    second = service.record(routed, authorization=auth)
    assert second.pages[0].status == "reused"
    assert second.pages[0].record == first.pages[0].record
    assert paths[0].read_bytes() == old
    assert source.read_bytes() == source_bytes
    assert not (root / "portia" / "operations").exists()


def test_multi_page_partial_then_retry_only_missing_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    a = _target(pages, routes, auth, ident="ptgt_one", index=1)
    _target(pages, routes, auth, ident="ptgt_two", index=2)
    c = _target(pages, routes, auth, ident="ptgt_three", index=3)
    source = tmp_path / "three.pdf"
    _pdf(source, 3)
    retained, routed = _discovery(root, source, [c, None, a])
    assert [x.status for x in routed.pages] == ["verified", "missing_qr", "verified"]
    service = FilePageRecordService(root)
    from portia.intake import page_records as records_module

    real = records_module.exclusive_create
    fail_once = True

    def flaky(path: Path, data: bytes):
        nonlocal fail_once
        if fail_once and b'"source_page_number":3' in data:
            fail_once = False
            raise PortiaStorageError("synthetic disk outage")
        return real(path, data)

    monkeypatch.setattr(records_module, "exclusive_create", flaky)
    interrupted = service.record(routed, authorization=auth)
    assert [x.status for x in interrupted.pages] == [
        "created",
        "needs_attention",
        "retryable",
    ]
    assert interrupted.completed_with_exceptions
    one = _receipt_files(root)
    assert len(one) == 1
    before = one[0].read_bytes()
    monkeypatch.setattr(records_module, "exclusive_create", real)
    resumed = service.record(routed, authorization=auth)
    assert [x.status for x in resumed.pages] == ["reused", "needs_attention", "created"]
    assert len(_receipt_files(root)) == 2
    assert one[0].read_bytes() == before
    assert resumed.pages[2].record is not None
    assert resumed.pages[2].record.to_dict()["source_ref"]["source_page_number"] == 3
    assert retained.core_source.retained_source_path.read_bytes() == source.read_bytes()
    # The printed target index, template ordinal and physical source-page
    # number must not silently become the same identifier.
    assert resumed.pages[2].record.to_dict()["page_target_id"] == "ptgt_one"


def test_authorization_revocation_preserves_retention_without_receipt(
    tmp_path: Path,
) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "return.png"
    _image(image)
    retained, routed = _discovery(root, image, [locator])
    result = FilePageRecordService(root).record(
        routed, authorization=Authorized(allowed=False)
    )
    assert result.pages[0].status == "needs_attention"
    assert result.pages[0].reason == "authorization_denied"
    assert _receipt_files(root) == []
    assert retained.core_source.retained_source_path.exists()


def test_cancelled_batch_and_retired_route_cannot_be_replayed_as_verification(
    tmp_path: Path,
) -> None:
    root, auth, batches, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "return.png"
    _image(image)
    _retained, routed = _discovery(root, image, [locator])
    batches.transition(CLASS, WORK, "cancelled", authorization=auth)
    result = FilePageRecordService(root).record(routed, authorization=auth)
    assert result.pages[0].status == "needs_attention"
    assert result.pages[0].reason == "batch_cancelled"
    assert _receipt_files(root) == []


def test_historical_corrupt_record_never_overwritten(tmp_path: Path) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "return.png"
    _image(image)
    _retained, routed = _discovery(root, image, [locator])
    service = FilePageRecordService(root)
    assert service.record(routed, authorization=auth).pages[0].status == "created"
    path = _receipt_files(root)[0]
    raw = path.read_bytes()
    payload = json.loads(raw)
    payload["route_id"] = "route_contradictory"
    changed = json.dumps(payload).encode()
    path.write_bytes(changed)
    result = service.record(routed, authorization=auth)
    assert result.pages[0].status == "conflict"
    assert path.read_bytes() == changed
    path.write_bytes(b'{"unreadable":')
    again = service.record(routed, authorization=auth)
    assert again.pages[0].status == "conflict"
    assert path.read_bytes() == b'{"unreadable":'


def test_existing_lock_is_not_stolen_or_auto_cleared(tmp_path: Path) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "return.png"
    _image(image)
    _retained, routed = _discovery(root, image, [locator])
    lock = safe_module_work_descendant(
        root,
        ModuleWorkRef("portia", CLASS, WORK),
        ".capture-batch-lifecycle.lock",
    )
    lock.write_text("other operation", encoding="utf-8")
    result = FilePageRecordService(root).record(routed, authorization=auth)
    assert result.pages[0].status == "retryable"
    assert result.pages[0].reason == "operation_lock_requires_recovery"
    assert lock.read_text(encoding="utf-8") == "other operation"
    assert _receipt_files(root) == []


def test_distinct_physical_retained_sources_same_printed_route_do_not_collapse(
    tmp_path: Path,
) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    a, b = tmp_path / "a.png", tmp_path / "b.png"
    _image(a, "white")
    _image(b, "gray")
    one, r1 = _discovery(root, a, [locator])
    two, r2 = _discovery(root, b, [locator])
    service = FilePageRecordService(root)
    first = service.record(r1, authorization=auth)
    second = service.record(r2, authorization=auth)
    assert first.pages[0].status == second.pages[0].status == "created"
    assert len(_receipt_files(root)) == 2
    assert first.pages[0].record != second.pages[0].record
    assert one.core_source.source_scan_id != two.core_source.source_scan_id


def test_existing_receipt_does_not_get_replaced_by_processing_state_retry(
    tmp_path: Path,
) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "return.png"
    _image(image)
    _retained, routed = _discovery(root, image, [locator])
    service = FilePageRecordService(root)
    service.record(routed, authorization=auth)
    path = _receipt_files(root)[0]
    original = json.loads(path.read_bytes())
    original["processing_state"] = "failed"
    original["failure_detail"] = "Capture stage interrupted; awaiting operator review"
    path.write_text(json.dumps(original), encoding="utf-8")
    before = path.read_bytes()
    result = service.record(routed, authorization=auth)
    assert result.pages[0].status == "reused"
    assert result.pages[0].reason == "existing_failed"
    assert path.read_bytes() == before


def test_manual_replay_does_not_materialize_domain_facts(tmp_path: Path) -> None:
    root, auth, _batch, pages, routes = _setup(tmp_path)
    locator = _target(pages, routes, auth)
    image = tmp_path / "returned.png"
    _image(image)
    _retained, routed = _discovery(root, image, [locator])
    FilePageRecordService(root).record(routed, authorization=auth)
    records = _receipt_files(root)
    assert len(records) == 1
    assert hashlib.sha256(records[0].read_bytes()).hexdigest()
    work_dir = records[0].parent.parent
    assert sorted(p.name for p in work_dir.iterdir()) == [
        "capture_page_record",
        "capture_page_target",
    ]
