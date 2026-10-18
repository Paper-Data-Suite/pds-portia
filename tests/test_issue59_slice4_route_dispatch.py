"""#59 Slice 4: real Core route dispatch with no Page Record writes."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.route_registrations import write_route_registration
from pds_core.routes import class_metadata_path, route_registration_path
from pds_core.routing_models import (
    ModuleRecordRef,
    ModuleWorkRef,
    RouteLocator,
    RouteRegistration,
)
from pds_core.scan_retention import retain_source_scan

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.intake import (
    PageQrDiscovery,
    RetainedIntakeSource,
    SourceFormat,
    SourceQrDiscovery,
)
from portia.intake.dispatch import FilePageRouteDispatchService
from portia.models import CaptureBatchV1, PageTargetV2

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}


class Authorized:
    def __init__(self, permitted: bool = True) -> None:
        self.permitted = permitted
        self.actions: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.actions.append(operation)
        if not self.permitted or class_id != CLASS:
            raise PermissionError("permission denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def fixture(name: str) -> dict[str, object]:
    raw = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def setup(tmp_path: Path):
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
        CaptureBatchV1(fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    targets = FilePageTargetService(root, batch_service=batches)
    routes = FilePageRouteService(root, batch_service=batches, page_service=targets)
    return root, batches, targets, routes, auth


def add_target(
    targets: FilePageTargetService,
    auth: Authorized,
    *,
    name: str = "ptgt_classroom_01",
    index: int = 1,
) -> PageTargetV2:
    data = fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    data.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id=name,
        page_index=index,
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    return targets.create_or_load(PageTargetV2(data), authorization=auth)


def source(root: Path, *, pages: int = 1) -> RetainedIntakeSource:
    # Source custody is real Core; route tests do not need a PDF rasterizer.
    incoming = root.parent / "returned.pdf"
    incoming.write_bytes(b"%PDF-1.7\n synthetic retained return")
    retained = retain_source_scan(root, incoming)
    return RetainedIntakeSource(
        retained, SourceFormat.PDF, incoming.stat().st_size, pages
    )


def discovery(
    src: RetainedIntakeSource, *locators: RouteLocator | str
) -> SourceQrDiscovery:
    values = []
    for number, value in enumerate(locators, 1):
        identity = src.page_identity(number)
        if isinstance(value, RouteLocator):
            values.append(PageQrDiscovery(identity, "candidate_unverified", value))
        else:
            values.append(PageQrDiscovery(identity, value))  # type: ignore[arg-type]
    return SourceQrDiscovery(src, tuple(values))


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def test_real_core_dispatch_verifies_route_target_and_is_read_only(
    tmp_path: Path,
) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    item = add_target(targets, auth)
    ready = routes.register_or_load(item, authorization=auth)
    assert ready.locator is not None
    src = source(root)
    original = tree_bytes(root)
    found = discovery(src, ready.locator)
    service = FilePageRouteDispatchService(root)
    result = service.verify(found, authorization=auth)
    assert result.verified_count == 1
    page = result.pages[0]
    assert page.status == "verified"
    assert page.verified is not None
    assert page.verified.locator == ready.locator
    assert page.verified.target.to_dict() == item.to_dict()
    assert page.verified.resolution.registration == ready.registration
    assert "capture_intake.route" in auth.actions
    assert tree_bytes(root) == original
    assert service.verify(found, authorization=auth) == result
    assert not any("capture_page_record" in name for name in original)


def test_unrecognized_and_missing_routes_are_independent(tmp_path: Path) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    page = add_target(targets, auth)
    ready = routes.register_or_load(page, authorization=auth)
    assert ready.locator is not None
    nonexistent = RouteLocator(
        "PDS2", ModuleWorkRef("portia", CLASS, WORK), "rt_unknown_000"
    )
    src = source(root, pages=5)
    found = discovery(
        src, ready.locator, "missing_qr", nonexistent, "foreign_module", "ambiguous_qr"
    )
    result = FilePageRouteDispatchService(root).verify(found, authorization=auth)
    assert [item.status for item in result.pages] == [
        "verified",
        "missing_qr",
        "route_unavailable",
        "foreign_module",
        "ambiguous_qr",
    ]
    assert [r.identity.source_page_number for r in result.pages] == [1, 2, 3, 4, 5]
    assert all(page.verified is None for page in result.pages[1:])


def test_permission_denial_precedes_core_route_lookup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.intake import dispatch as module

    root, _b, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    src = source(root)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Core dispatch was called despite access denial")

    monkeypatch.setattr(module, "dispatch_route", forbidden)
    unauthorized = Authorized(False)
    result = FilePageRouteDispatchService(root).verify(
        discovery(src, ready.locator), authorization=unauthorized
    )
    assert result.pages[0].status == "authorization_denied"
    assert result.pages[0].verified is None
    assert unauthorized.actions == ["capture_intake.route"]


def test_inactive_core_registration_is_not_dispatchable(tmp_path: Path) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    path = route_registration_path(root, ready.locator)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["status"] = "retired"
    path.write_text(json.dumps(raw), encoding="utf-8")
    out = FilePageRouteDispatchService(root).verify(
        discovery(source(root), ready.locator), authorization=auth
    )
    assert out.pages[0].status == "route_inactive"
    assert out.pages[0].verified is None


def test_historical_template_mismatch_is_not_a_verified_route(
    tmp_path: Path,
) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    path = route_registration_path(root, ready.locator)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["module_details"]["template_identity"]["layout_version"] = "tampered"
    path.write_text(json.dumps(raw), encoding="utf-8")
    out = FilePageRouteDispatchService(root).verify(
        discovery(source(root), ready.locator), authorization=auth
    )
    assert out.pages[0].status == "target_conflict"
    assert out.pages[0].verified is None


def test_wrong_registration_target_cannot_be_accepted(tmp_path: Path) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None and ready.registration is not None
    old = ready.registration
    locator = RouteLocator("PDS2", old.locator.work, "rt_invalid_target")
    bad = RouteRegistration(
        "1",
        locator,
        ModuleRecordRef("portia", "capture_page_target", "ptgt_missing", "2"),
        old.created_at,
        "active",
        old.human_fallback,
        module_details=old.module_details,
    )
    write_route_registration(root, bad)
    out = FilePageRouteDispatchService(root).verify(
        discovery(source(root), locator), authorization=auth
    )
    assert out.pages[0].status == "target_unavailable"


def test_cancelled_batch_blocks_route_even_if_registration_exists(
    tmp_path: Path,
) -> None:
    root, batches, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    batches.transition(CLASS, WORK, "cancelled", authorization=auth)
    out = FilePageRouteDispatchService(root).verify(
        discovery(source(root), ready.locator), authorization=auth
    )
    assert out.pages[0].status == "batch_cancelled"


def test_closed_batch_allows_existing_active_return(tmp_path: Path) -> None:
    root, batches, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    batches.transition(CLASS, WORK, "closed", authorization=auth)
    out = FilePageRouteDispatchService(root).verify(
        discovery(source(root), ready.locator), authorization=auth
    )
    assert out.pages[0].status == "verified"


def test_source_tampering_fails_before_protected_reads(tmp_path: Path) -> None:
    root, _b, targets, routes, auth = setup(tmp_path)
    ready = routes.register_or_load(add_target(targets, auth), authorization=auth)
    assert ready.locator is not None
    src = source(root)
    src.core_source.retained_source_path.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="integrity"):
        FilePageRouteDispatchService(root).verify(
            discovery(src, ready.locator), authorization=auth
        )


def test_unroutable_page_never_needs_authorization(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    src = source(root, pages=3)
    auth = Authorized(False)
    found = discovery(src, "invalid_qr", "render_failed", "unreadable_qr")
    result = FilePageRouteDispatchService(root).verify(found, authorization=auth)
    assert [item.status for item in result.pages] == [
        "invalid_qr",
        "render_failed",
        "unreadable_qr",
    ]
    assert auth.actions == []
