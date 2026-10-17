"""Synthetic Issue #57 Slice 7 restart, integrity and security regression."""

from __future__ import annotations

import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path, route_registration_path
from pds_core.routing_models import PDS2_SCHEMA, RouteLocator

from portia.capture import FileCapturePreparationService
from portia.capture.contracts import CapturePreparationRequest
from portia.models import CaptureBatchV1, PageTargetV2
from portia.storage.errors import PortiaCorruptionError, PortiaPathError

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}


class Authorized:
    def __init__(self, disallow: str | None = None) -> None:
        self.disallow = disallow
        self.calls: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.calls.append(operation)
        if class_id != CLASS or operation == self.disallow:
            raise PermissionError("authorization denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def fixture(name: str) -> dict[str, object]:
    raw = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(raw, dict)
    return raw


def batch() -> CaptureBatchV1:
    return CaptureBatchV1(
        fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")
    )


def page(index: int) -> PageTargetV2:
    raw = fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    raw.update(
        class_id=CLASS,
        work_id=WORK,
        page_target_id=f"ptgt_classroom_{index:02d}",
        page_index=index,
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    return PageTargetV2(raw)


def setup(tmp_path: Path) -> tuple[FileCapturePreparationService, Authorized]:
    metadata = class_metadata_path(tmp_path, CLASS)
    metadata.parent.mkdir(parents=True)
    write_class_metadata(
        metadata,
        create_class_metadata(
            CLASS, "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    return FileCapturePreparationService(tmp_path), Authorized()


def seed(
    service: FileCapturePreparationService, auth: Authorized, *indices: int
) -> None:
    service.batches.create_or_load(batch(), authorization=auth)
    for index in indices:
        service.pages.create_or_load(page(index), authorization=auth)


def all_files(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*.json")
    }


def prepare(
    service: FileCapturePreparationService, auth: Authorized, index: int
):
    return service.prepare(
        CapturePreparationRequest(batch(), (page(index),)), authorization=auth
    )


def tamper_route(root: Path, result: object, edit: str) -> Path:
    # Caller supplies the actual verified route result, never a guessed path.
    locator = result.pages[0].locator  # type: ignore[attr-defined]
    assert locator is not None
    path = route_registration_path(root, locator)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if edit == "orphan":
        raw["target"]["record_id"] = "ptgt_missing"
    elif edit == "wrong_version":
        raw["target"]["contract_version"] = "1"
    elif edit == "template":
        raw["module_details"]["template_identity"]["layout_version"] = "fake"
    elif edit == "wrong_owner":
        raw["locator"]["work_id"] = "cbat_other_work"
    else:
        raise AssertionError(edit)
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_recover_missing_routes_without_creating_new_target(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1, 2)
    before = all_files(tmp_path)
    assessed = service.inspect(CLASS, WORK, authorization=auth)
    assert [item.status for item in assessed.pages] == ["retryable", "retryable"]
    assert all_files(tmp_path) == before
    resumed = service.recover(CLASS, WORK, authorization=auth)
    assert resumed.ready_for_rendering
    assert all(state.status == "verified" for state in resumed.pages)
    for state in resumed.pages:
        assert state.registration is not None
        assert state.registration.target.contract_version == "2"
    assert len(service.pages.list_targets(CLASS, WORK, authorization=auth)) == 2
    assert not (tmp_path / "portia" / "operations").exists()


def test_recover_exact_idempotent_retry_preserves_route_bytes(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    first = service.recover(CLASS, WORK, authorization=auth)
    assert first.ready_for_rendering
    before = all_files(tmp_path)
    second = service.recover(CLASS, WORK, authorization=auth)
    assert second.ready_for_rendering
    assert second.pages[0].locator == first.pages[0].locator
    assert all_files(tmp_path) == before


def test_recovery_after_normal_prepare_does_not_change_route(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    existing = prepare(service, auth, 1)
    assert existing.ready_for_rendering
    before = all_files(tmp_path)
    assert service.recover(CLASS, WORK, authorization=auth).ready_for_rendering
    assert all_files(tmp_path) == before


def test_recover_cannot_invent_missing_page_targets(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    service.batches.create_or_load(batch(), authorization=auth)
    before = all_files(tmp_path)
    result = service.recover(CLASS, WORK, authorization=auth)
    assert result.pages == ()
    assert not result.ready_for_rendering
    assert all_files(tmp_path) == before


def test_recover_does_not_clear_interrupted_lock(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    lock = service.batches._manifest(CLASS, WORK).parent / (
        ".capture-batch-lifecycle.lock"
    )
    lock.write_bytes(b"interrupted operation")
    before = all_files(tmp_path)
    result = service.recover(CLASS, WORK, authorization=auth)
    assert not result.ready_for_rendering
    assert result.pages[0].status == "conflict"
    assert result.pages[0].diagnostics == ("requires_manual_lock_review",)
    assert lock.read_bytes() == b"interrupted operation"
    assert all_files(tmp_path) == before


@pytest.mark.parametrize(
    "edit", ("orphan", "wrong_version", "template", "wrong_owner")
)
def test_conflicting_registration_blocks_recovery_before_writing(
    tmp_path: Path, edit: str
) -> None:
    service, auth = setup(tmp_path)
    existing = prepare(service, auth, 1)
    seed(service, auth, 2)
    original = tamper_route(tmp_path, existing, edit)
    previous = original.read_bytes()
    before = all_files(tmp_path)
    with pytest.raises(PortiaCorruptionError):
        service.recover(CLASS, WORK, authorization=auth)
    assert original.read_bytes() == previous
    assert all_files(tmp_path) == before


def test_duplicate_routes_cannot_be_arbitrarily_selected(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    existing = prepare(service, auth, 1)
    seed(service, auth, 2)
    locator = existing.pages[0].locator
    assert locator is not None
    first = route_registration_path(tmp_path, locator)
    duplicate = RouteLocator(PDS2_SCHEMA, locator.work, "rt_duplicate_0001")
    second = route_registration_path(tmp_path, duplicate)
    raw = json.loads(first.read_text(encoding="utf-8"))
    raw["locator"]["route_id"] = duplicate.route_id
    second.write_text(json.dumps(raw), encoding="utf-8")
    before = all_files(tmp_path)
    with pytest.raises(PortiaCorruptionError, match="multiple Core routes"):
        service.recover(CLASS, WORK, authorization=auth)
    assert all_files(tmp_path) == before


def test_recovery_requires_permission_before_any_write(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    before = all_files(tmp_path)
    denied = Authorized(disallow="page_route.register")
    with pytest.raises(PermissionError):
        service.recover(CLASS, WORK, authorization=denied)
    assert all_files(tmp_path) == before


def test_cancelled_batch_does_not_generate_missing_route(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    service.batches.transition(CLASS, WORK, "cancelled", authorization=auth)
    before = all_files(tmp_path)
    result = service.recover(CLASS, WORK, authorization=auth)
    assert result.pages[0].status == "rejected"
    assert result.pages[0].payload is None
    assert not result.ready_for_rendering
    assert all_files(tmp_path) == before


def test_closed_batch_does_not_generate_missing_route(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    service.batches.transition(CLASS, WORK, "closed", authorization=auth)
    before = all_files(tmp_path)
    result = service.recover(CLASS, WORK, authorization=auth)
    assert result.pages[0].status == "rejected"
    assert not result.ready_for_rendering
    assert all_files(tmp_path) == before


def test_recovery_stops_after_recoverable_write_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1, 2, 3)
    original = service.routes.register_or_load

    def fails_second(target: PageTargetV2, *, authorization: Authorized):
        if target.field("page_index") == 2:
            from portia.storage.errors import PortiaRecoveryRequiredError
            raise PortiaRecoveryRequiredError("synthetic interrupted lock")
        return original(target, authorization=authorization)

    monkeypatch.setattr(service.routes, "register_or_load", fails_second)
    state = service.recover(CLASS, WORK, authorization=auth)
    assert [p.status for p in state.pages] == [
        "verified", "conflict", "retryable"
    ]
    assert state.pages[2].diagnostics == ("not_attempted",)
    assert len(service.routes._registrations(CLASS, WORK)) == 1


def test_prepare_denies_orphan_route_before_creating_another_page(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    original = prepare(service, auth, 1)
    tamper_route(tmp_path, original, "orphan")
    before = all_files(tmp_path)
    with pytest.raises(PortiaCorruptionError):
        prepare(service, auth, 2)
    assert all_files(tmp_path) == before


def test_concurrent_recovery_creates_at_most_one_registration(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    barrier = Barrier(2)

    def attempt(_: int):
        barrier.wait(timeout=5)
        try:
            return service.recover(CLASS, WORK, authorization=auth)
        except PortiaCorruptionError:
            # A simultaneous read of Core's exclusive writer can observe an
            # incomplete file; the reader must fail closed, not fabricate QR.
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(attempt, range(2)))
    assert len(service.routes._registrations(CLASS, WORK)) == 1
    assert any(r is not None and r.ready_for_rendering for r in outcomes)
    assert all(
        r is None or r.pages[0].status in {"verified", "conflict"}
        for r in outcomes
    )


def test_unsafe_recovery_path_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)

    def denied(target: PageTargetV2, *, authorization: Authorized):
        raise PortiaPathError("unsafe symlink or junction")

    monkeypatch.setattr(service.routes, "register_or_load", denied)
    result = service.recover(CLASS, WORK, authorization=auth)
    assert result.pages[0].status == "conflict"
    assert result.pages[0].diagnostics == ("unsafe_path",)
    assert result.pages[0].payload is None
    assert service.routes._registrations(CLASS, WORK) == ()


def test_unsafe_preparation_path_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, auth = setup(tmp_path)

    def denied(target: PageTargetV2, *, authorization: Authorized):
        raise PortiaPathError("unsafe symlink or junction")

    monkeypatch.setattr(service.routes, "register_or_load", denied)
    result = prepare(service, auth, 1)
    assert result.pages[0].status == "conflict"
    assert result.pages[0].diagnostics == ("unsafe_path",)
    assert result.pages[0].payload is None
    assert service.routes._registrations(CLASS, WORK) == ()


def test_symlinked_route_collection_denied_without_writing_outside(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    outside = tmp_path / "outside"
    outside.mkdir()
    collection = service.routes._collection(CLASS, WORK)
    try:
        collection.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this Windows installation")
    with pytest.raises(PortiaPathError):
        service.recover(CLASS, WORK, authorization=auth)
    assert tuple(outside.iterdir()) == ()


def test_recover_does_not_persist_viewer_alias_identifiers(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed(service, auth, 1)
    resumed = service.recover(CLASS, WORK, authorization=auth)
    assert resumed.ready_for_rendering
    route = resumed.pages[0]
    assert route.registration is not None
    assert "alias" not in json.dumps(route.registration.module_details).lower()
    assert route.payload is not None and route.payload.startswith("PDS2|")
    assert "viewer" not in route.payload
