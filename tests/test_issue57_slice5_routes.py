"""Synthetic Slice 5 Core PDS2 route registration and durable verification."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.pds2 import parse_pds2_payload
from pds_core.route_registrations import (
    RouteRegistrationReadError,
    RouteRegistrationWriteError,
    load_route_registration,
    write_route_registration,
)
from pds_core.routes import class_metadata_path, route_registration_path
from pds_core.routing_models import (
    PDS2_SCHEMA,
    ModuleRecordRef,
    RouteLocator,
    RouteRegistration,
)

from portia.capture import (
    FileCaptureBatchService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.capture.contracts import CapturePreparationError
from portia.models import CaptureBatchV1, PageTargetV2
from portia.storage.errors import PortiaNotFoundError, PortiaPathError

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
            raise PermissionError("not authorized")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def fixture(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def page(page_id: str = "ptgt_classroom_01", index: int = 1) -> PageTargetV2:
    value = fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    value.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id=page_id,
        page_index=index,
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    return PageTargetV2(value)


def workspace(
    tmp_path: Path,
) -> tuple[
    FileCaptureBatchService, FilePageTargetService, FilePageRouteService, Authorized
]:
    path = class_metadata_path(tmp_path, CLASS)
    path.parent.mkdir(parents=True)
    write_class_metadata(
        path,
        create_class_metadata(
            CLASS, "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(tmp_path)
    batches.create_or_load(
        CaptureBatchV1(fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    pages = FilePageTargetService(tmp_path, batch_service=batches)
    routes = FilePageRouteService(
        tmp_path, batch_service=batches, page_service=pages
    )
    return batches, pages, routes, auth


def persist(
    pages: FilePageTargetService, auth: Authorized,
    page_id: str = "ptgt_classroom_01", index: int = 1,
) -> PageTargetV2:
    item = page(page_id, index)
    return pages.create_or_load(item, authorization=auth)


def route_file(root: Path, result: object) -> Path:
    locator = result.locator  # type: ignore[attr-defined]
    assert locator is not None
    return route_registration_path(root, locator)


def add_other_route(
    root: Path, locator: RouteLocator, *, page_id: str, status: str = "active",
    template: object | None = None,
) -> None:
    work_details = {
        "page_target_contract_version": "2",
        "template_identity": (
            page().to_dict()["template_identity"] if template is None else template
        ),
    }
    registration = RouteRegistration(
        "1", locator,
        ModuleRecordRef("portia", "capture_page_target", page_id, "2"),
        datetime.now(timezone.utc).isoformat(), status, "Portia capture page",
        module_details=work_details,  # type: ignore[arg-type]
    )
    write_route_registration(root, registration)


def test_no_qr_until_core_exclusive_write_and_exact_reload(tmp_path: Path) -> None:
    _batches, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    before = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert before.status == "retryable"
    assert before.payload is None and before.locator is None
    assert not routes._collection(CLASS, WORK).exists()
    ready = routes.register_or_load(item, authorization=auth)
    assert ready.status == "verified" and ready.payload is not None
    assert ready.locator is not None and ready.registration is not None
    assert parse_pds2_payload(ready.payload) == ready.locator
    assert ready.locator.module_id == "portia"
    assert ready.locator.class_id == CLASS and ready.locator.work_id == WORK
    assert ready.registration.target.record_id == item.logical_id
    assert ready.registration.target.record_kind == "capture_page_target"
    assert ready.registration.target.contract_version == "2"
    assert (
        ready.registration.module_details["template_identity"]
        == item.to_dict()["template_identity"]
    )
    assert load_route_registration(tmp_path, ready.locator) == ready.registration
    assert "page_route.register" in auth.actions
    assert "page_route.inspect" in auth.actions


def test_idempotent_retry_no_second_route_or_byte_changes(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    first = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, first)
    original = p.read_bytes()
    second = routes.register_or_load(item, authorization=auth)
    assert second == first
    assert p.read_bytes() == original
    assert len(tuple(routes._collection(CLASS, WORK).iterdir())) == 1


def test_route_requires_persisted_page_and_authorized_class(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    with pytest.raises(PortiaNotFoundError):
        routes.register_or_load(page(), authorization=auth)
    assert not routes._collection(CLASS, WORK).exists()
    item = persist(pages, auth)
    with pytest.raises(PermissionError):
        routes.register_or_load(item, authorization=Authorized(False))
    with pytest.raises(PermissionError):
        routes.inspect(
            CLASS, WORK, item.logical_id or "", authorization=Authorized(False)
        )
    assert not routes._collection(CLASS, WORK).exists()


def test_stale_in_memory_page_does_not_get_a_route(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    persist(pages, auth)
    altered = page().to_dict()
    altered["capture_mode"] = "manual_transcription"
    stale = PageTargetV2(altered)
    result = routes.register_or_load(stale, authorization=auth)
    assert result.status == "conflict" and result.payload is None
    assert not routes._collection(CLASS, WORK).exists()


def test_inactive_core_route_is_not_printable(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, ready)
    value = json.loads(p.read_text(encoding="utf-8"))
    value["status"] = "inactive"
    p.write_text(json.dumps(value))
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "conflict" and blocked.locator is None
    assert routes.register_or_load(item, authorization=auth).status == "conflict"
    assert len(list(routes._collection(CLASS, WORK).iterdir())) == 1


def test_template_snapshot_mismatch_blocks_route(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, ready)
    value = json.loads(p.read_text(encoding="utf-8"))
    value["module_details"]["template_identity"]["layout_version"] = "wrong"
    p.write_text(json.dumps(value))
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "conflict"
    assert blocked.diagnostics == ("template_identity_mismatch",)
    assert blocked.payload is None


def test_incorrect_target_contract_version_is_conflict(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, ready)
    value = json.loads(p.read_text(encoding="utf-8"))
    value["target"]["contract_version"] = "1"
    p.write_text(json.dumps(value))
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "conflict" and blocked.payload is None


def test_corrupt_core_registration_fails_closed_without_repair(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, ready)
    p.write_text('{"broken":')
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "conflict" and blocked.payload is None
    assert p.read_text() == '{"broken":'


def test_duplicate_route_to_same_target_blocks_print(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    assert ready.locator is not None
    duplicate = RouteLocator(PDS2_SCHEMA, ready.locator.work, "rt_other_same_target")
    add_other_route(tmp_path, duplicate, page_id=item.logical_id or "")
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "conflict"
    assert blocked.diagnostics == ("ambiguous_target_routes",)
    assert blocked.payload is None


def test_unrelated_route_cannot_supply_page_target_payload(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    one = persist(pages, auth)
    two = persist(pages, auth, "ptgt_another", 2)
    registered = routes.register_or_load(one, authorization=auth)
    assert registered.status == "verified"
    inspection = routes.inspect(CLASS, WORK, two.logical_id or "", authorization=auth)
    assert inspection.status == "retryable" and inspection.payload is None
    ready = routes.register_or_load(two, authorization=auth)
    assert ready.status == "verified"
    assert ready.locator != registered.locator
    assert len(tuple(routes._collection(CLASS, WORK).iterdir())) == 2


def test_route_id_collision_retries_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.capture import routes as routes_module

    _b, pages, routes, auth = workspace(tmp_path)
    first = persist(pages, auth)
    second = persist(pages, auth, "ptgt_another", 2)
    first_ready = routes.register_or_load(first, authorization=auth)
    assert first_ready.locator is not None
    previous = route_file(tmp_path, first_ready).read_bytes()
    choices = iter((first_ready.locator.route_id, "rt_safe_new_random"))
    monkeypatch.setattr(routes_module, "generate_route_id", lambda: next(choices))
    new_ready = routes.register_or_load(second, authorization=auth)
    assert new_ready.status == "verified"
    assert new_ready.locator is not None
    assert new_ready.locator.route_id == "rt_safe_new_random"
    assert route_file(tmp_path, first_ready).read_bytes() == previous


def test_core_write_failure_never_reports_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.capture import routes as routes_module

    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)

    def fail(_root: Path, _registration: RouteRegistration) -> None:
        raise RouteRegistrationWriteError("synthetic Core write failure")

    monkeypatch.setattr(routes_module, "write_route_registration", fail)
    result = routes.register_or_load(item, authorization=auth)
    assert result.status == "retryable"
    assert result.payload is None and result.registration is None


def test_reload_failure_never_exposes_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from portia.capture import routes as routes_module

    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)

    def fail(_root: Path, _locator: RouteLocator) -> RouteRegistration:
        raise RouteRegistrationReadError("synthetic failed Core read")

    monkeypatch.setattr(routes_module, "load_route_registration", fail)
    result = routes.register_or_load(item, authorization=auth)
    assert result.status == "conflict"
    assert result.payload is None and result.registration is None
    assert len(tuple(routes._collection(CLASS, WORK).iterdir())) == 1


def test_terminal_batches_block_new_routes_but_preserve_old_history(
    tmp_path: Path,
) -> None:
    batches, pages, routes, auth = workspace(tmp_path)
    first = persist(pages, auth)
    second = persist(pages, auth, "ptgt_another", 2)
    ready = routes.register_or_load(first, authorization=auth)
    batches.transition(CLASS, WORK, "closed", authorization=auth)
    assert routes.register_or_load(first, authorization=auth) == ready
    blocked = routes.register_or_load(second, authorization=auth)
    assert blocked.status == "rejected" and blocked.payload is None
    assert len(tuple(routes._collection(CLASS, WORK).iterdir())) == 1


def test_cancelled_batch_never_exposes_old_printable_route(tmp_path: Path) -> None:
    batches, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    ready = routes.register_or_load(item, authorization=auth)
    p = route_file(tmp_path, ready)
    original = p.read_bytes()
    batches.transition(CLASS, WORK, "cancelled", authorization=auth)
    blocked = routes.inspect(CLASS, WORK, item.logical_id or "", authorization=auth)
    assert blocked.status == "rejected" and blocked.payload is None
    assert p.read_bytes() == original


def test_link_like_route_collection_is_not_used(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    other = tmp_path / "outside"
    other.mkdir()
    collection = routes._collection(CLASS, WORK)
    try:
        collection.symlink_to(other, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this Windows environment")
    with pytest.raises(PortiaPathError):
        routes.register_or_load(item, authorization=auth)
    assert tuple(other.iterdir()) == ()


def test_no_domain_artifacts_or_viewer_aliases_from_routing(tmp_path: Path) -> None:
    _b, pages, routes, auth = workspace(tmp_path)
    item = persist(pages, auth)
    result = routes.register_or_load(item, authorization=auth)
    assert result.status == "verified" and result.payload is not None
    routes_root = routes._collection(CLASS, WORK)
    work_root = routes_root.parent
    assert not (work_root / "records" / "event").exists()
    assert not (work_root / "records" / "observation").exists()
    assert not (work_root / "records" / "communication").exists()
    assert "alias" not in result.payload
    assert "viewer" not in result.payload
    assert "alias" not in route_file(tmp_path, result).read_text(encoding="utf-8")


def test_reject_historical_target_registration(tmp_path: Path) -> None:
    _b, _p, routes, auth = workspace(tmp_path)
    with pytest.raises(CapturePreparationError, match="v2"):
        routes.register_or_load(object(), authorization=auth)  # type: ignore[arg-type]
