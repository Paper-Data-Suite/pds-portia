"""Synthetic multi-page preparation and durable partial-result acceptance."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path, route_registration_path

from portia.capture import (
    FileCaptureBatchService,
    FileCapturePreparationService,
    FilePageRouteService,
    FilePageTargetService,
)
from portia.capture.contracts import (
    CapturePreparationError,
    CapturePreparationRequest,
    PagePreparationResult,
)
from portia.models import CaptureBatchV1, PageTargetV2
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}


class Authorized:
    def __init__(self, actions: tuple[str, ...] | None = None) -> None:
        self.permitted = actions
        self.actions: list[str] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.actions.append(operation)
        if class_id != CLASS or (
            self.permitted is not None and operation not in self.permitted
        ):
            raise PermissionError("authorization denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def fixture(relative: str) -> dict[str, object]:
    result = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    assert isinstance(result, dict)
    return result


def batch() -> CaptureBatchV1:
    return CaptureBatchV1(
        fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")
    )


def page(number: int) -> PageTargetV2:
    data = fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    data.update(
        class_id=CLASS,
        work_id=WORK,
        page_index=number,
        page_target_id=f"ptgt_classroom_{number:02d}",
        created_by=ACTOR,
        updated_by=ACTOR,
    )
    return PageTargetV2(data)


def setup(tmp_path: Path) -> tuple[FileCapturePreparationService, Authorized]:
    path = class_metadata_path(tmp_path, CLASS)
    path.parent.mkdir(parents=True)
    write_class_metadata(
        path,
        create_class_metadata(
            CLASS, "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    return FileCapturePreparationService(tmp_path), Authorized()


def prepare(
    service: FileCapturePreparationService, auth: Authorized, *indices: int
):
    return service.prepare(
        CapturePreparationRequest(batch(), tuple(page(index) for index in indices)),
        authorization=auth,
    )


def files(root: Path) -> tuple[str, ...]:
    return tuple(sorted(str(p.relative_to(root)) for p in root.rglob("*.json")))


def test_multi_page_preparation_is_ordered_and_verified(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    result = prepare(service, auth, 3, 1, 2)
    assert result.ready_for_rendering
    assert [r.target.field("page_index") for r in result.pages] == [1, 2, 3]
    assert all(r.status == "verified" for r in result.pages)
    for result_page in result.pages:
        assert result_page.payload is not None
        assert result_page.locator is not None
        assert result_page.registration is not None
        assert route_registration_path(tmp_path, result_page.locator).is_file()
        assert (
            result_page.registration.target.record_id == result_page.target.logical_id
        )
    assert service.inspect(CLASS, WORK, authorization=auth).ready_for_rendering
    assert not (tmp_path / "portia" / "operations").exists()


def test_exact_replay_is_idempotent_and_does_not_rewrite_routes(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    initial = prepare(service, auth, 1, 2)
    registrations = {
        r.target.logical_id: (
            r.locator,
            route_registration_path(tmp_path, r.locator).read_bytes(),
        )
        for r in initial.pages
        if r.locator is not None
    }
    before = files(tmp_path)
    replay = prepare(service, auth, 2, 1)
    assert replay.ready_for_rendering
    assert files(tmp_path) == before
    for r in replay.pages:
        assert r.locator is not None
        old_locator, old_bytes = registrations[r.target.logical_id]
        assert r.locator == old_locator
        assert route_registration_path(tmp_path, r.locator).read_bytes() == old_bytes


def test_partial_result_stops_later_pages_and_retry_resumes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, auth = setup(tmp_path)
    original = service.routes.register_or_load

    def interrupted(target: PageTargetV2, *, authorization: Authorized):
        if target.field("page_index") == 2:
            return PagePreparationResult(
                "retryable", target, diagnostics=("route_write_incomplete",)
            )
        return original(target, authorization=authorization)

    monkeypatch.setattr(service.routes, "register_or_load", interrupted)
    first = prepare(service, auth, 1, 2, 3)
    assert [p.status for p in first.pages] == [
        "verified", "retryable", "retryable"
    ]
    assert first.pages[1].payload is None and first.pages[2].locator is None
    assert first.pages[2].diagnostics == ("not_attempted",)
    assert [p.logical_id for p in service.pages.list_targets(
        CLASS, WORK, authorization=auth
    )] == ["ptgt_classroom_01", "ptgt_classroom_02"]
    first_locator = first.pages[0].locator
    monkeypatch.setattr(service.routes, "register_or_load", original)
    replay = prepare(service, auth, 1, 2, 3)
    assert replay.ready_for_rendering
    assert replay.pages[0].locator == first_locator
    assert len(service.pages.list_targets(CLASS, WORK, authorization=auth)) == 3


def test_storage_conflict_is_reported_not_printable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    service, auth = setup(tmp_path)
    original = service.pages.create_or_load

    def conflicting(target: PageTargetV2, *, authorization: Authorized):
        if target.field("page_index") == 2:
            raise PortiaConflictError("synthetic page conflict")
        return original(target, authorization=authorization)

    monkeypatch.setattr(service.pages, "create_or_load", conflicting)
    result = prepare(service, auth, 1, 2, 3)
    assert [p.status for p in result.pages] == ["verified", "conflict", "retryable"]
    assert result.pages[1].registration is None
    assert result.pages[1].diagnostics == ("durable_state_conflict",)
    assert not result.ready_for_rendering
    assert len(service.pages.list_targets(CLASS, WORK, authorization=auth)) == 1


def test_preflight_denies_case_insensitive_duplicate_before_batch_created(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    raw = page(2).to_dict()
    raw["page_target_id"] = "ptgt_CLASSROOM_01"
    with pytest.raises(CapturePreparationError, match="case-insensitive"):
        service.prepare(
            CapturePreparationRequest(batch(), (page(1), PageTargetV2(raw))),
            authorization=auth,
        )
    assert service.batches.list_batches(CLASS, authorization=auth) == ()


def test_preflight_checks_all_authorization_before_first_write(tmp_path: Path) -> None:
    service, _auth = setup(tmp_path)
    denied = Authorized(("capture_batch.create", "page_target.create"))
    with pytest.raises(PermissionError):
        prepare(service, denied, 1, 2)
    assert not service.batches._manifest(CLASS, WORK).exists()


def test_preflight_checks_existing_page_indices_before_new_page_writes(
    tmp_path: Path,
) -> None:
    service, auth = setup(tmp_path)
    prepare(service, auth, 1)
    existing_files = files(tmp_path)
    raw = page(2).to_dict()
    raw["page_index"] = 1
    conflict = PageTargetV2(raw)
    with pytest.raises(PortiaConflictError, match="index"):
        service.prepare(
            CapturePreparationRequest(batch(), (page(3), conflict)),
            authorization=auth,
        )
    assert files(tmp_path) == existing_files


def test_inspect_read_only_and_explicit_recover_resumes_route(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    service.batches.create_or_load(batch(), authorization=auth)
    service.pages.create_or_load(page(1), authorization=auth)
    before = files(tmp_path)
    state = service.inspect(CLASS, WORK, authorization=auth)
    assert len(state.pages) == 1
    assert state.pages[0].status == "retryable"
    assert state.pages[0].diagnostics == ("route_not_registered",)
    assert state.pages[0].payload is None
    assert files(tmp_path) == before
    # Slice 7 explicitly resumes only a durable Page Target lacking a route.
    resumed = service.recover(CLASS, WORK, authorization=auth)
    assert resumed.ready_for_rendering
    assert resumed.pages[0].registration is not None
    assert service.inspect(CLASS, WORK, authorization=auth).ready_for_rendering


def test_closed_batch_is_not_ready_for_new_printing(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    assert prepare(service, auth, 1).ready_for_rendering
    service.batches.transition(CLASS, WORK, "closed", authorization=auth)
    inspected = service.inspect(CLASS, WORK, authorization=auth)
    assert inspected.pages[0].status == "verified"
    assert not inspected.ready_for_rendering


def test_corrupted_routes_block_new_page_preparation(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    first = prepare(service, auth, 1)
    assert first.pages[0].locator is not None
    route = route_registration_path(tmp_path, first.pages[0].locator)
    route.write_bytes(b"{\"bad\":")
    existing = files(tmp_path)
    with pytest.raises(PortiaCorruptionError):
        prepare(service, auth, 2)
    assert files(tmp_path) == existing


def test_partial_retry_never_creates_behavior_domain_work(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    assert prepare(service, auth, 1, 2).ready_for_rendering
    assert prepare(service, auth, 1, 2).ready_for_rendering
    root = service.batches._manifest(CLASS, WORK).parent.parent
    assert all(path.name.startswith("cbat_") for path in root.iterdir())
    assert not (tmp_path / "portia" / "actors").exists()


def test_wrong_service_workspace_is_denied(tmp_path: Path) -> None:
    other = FileCaptureBatchService(tmp_path / "other")
    with pytest.raises(CapturePreparationError, match="workspace mismatch"):
        FileCapturePreparationService(tmp_path, batch_service=other)
    other_page = FilePageTargetService(tmp_path / "other")
    with pytest.raises(CapturePreparationError, match="workspace mismatch"):
        FileCapturePreparationService(tmp_path, page_service=other_page)
    other_route = FilePageRouteService(tmp_path / "other")
    with pytest.raises(CapturePreparationError, match="workspace mismatch"):
        FileCapturePreparationService(tmp_path, route_service=other_route)
