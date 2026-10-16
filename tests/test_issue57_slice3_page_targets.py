"""Synthetic Issue #57 Slice 3 Page Target ownership and persistence tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path, safe_module_work_descendant
from pds_core.routing_models import ModuleWorkRef

from portia.capture import FileCaptureBatchService, FilePageTargetService
from portia.capture.contracts import CapturePreparationError
from portia.models import CaptureBatchV1, PageTargetV1, PageTargetV2
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}


class Authorized:
    def __init__(self, permitted: tuple[str, ...] = (CLASS,)) -> None:
        self.permitted = permitted
        self.actions: list[tuple[str, str]] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.actions.append((class_id, operation))
        if class_id not in self.permitted:
            raise PermissionError("class not authorized")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def wire(name: str) -> dict[str, object]:
    value = json.loads((ROOT / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def batch() -> CaptureBatchV1:
    return CaptureBatchV1(wire("tests/fixtures/issue_20/valid/01-capture_batch.json"))


def page(
    *, page_id: str = "ptgt_classroom_01", index: int = 1
) -> PageTargetV2:
    data = wire(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    data["class_id"] = CLASS
    data["work_id"] = WORK
    data["page_target_id"] = page_id
    data["page_index"] = index
    data["created_by"] = ACTOR
    data["updated_by"] = ACTOR
    return PageTargetV2(data)


def target_path(root: Path, page_id: str = "ptgt_classroom_01") -> Path:
    return safe_module_work_descendant(
        root,
        ModuleWorkRef("portia", CLASS, WORK),
        f"records/capture_page_target/{page_id}.json",
    )


def workspace(
    tmp_path: Path,
) -> tuple[FileCaptureBatchService, FilePageTargetService, Authorized]:
    meta = class_metadata_path(tmp_path, CLASS)
    meta.parent.mkdir(parents=True)
    write_class_metadata(
        meta,
        create_class_metadata(
            CLASS,
            "2026-2027",
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(tmp_path)
    batches.create_or_load(batch(), authorization=auth)
    return batches, FilePageTargetService(tmp_path, batch_service=batches), auth


def test_create_load_list_and_idempotent_retry(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    original = page()
    assert pages.list_targets(CLASS, WORK, authorization=auth) == ()
    assert pages.create_or_load(original, authorization=auth) == original
    content = target_path(tmp_path).read_bytes()
    assert pages.create_or_load(original, authorization=auth) == original
    assert target_path(tmp_path).read_bytes() == content
    assert (
        pages.load(CLASS, WORK, original.logical_id or "", authorization=auth)
        == original
    )
    assert pages.list_targets(CLASS, WORK, authorization=auth) == (original,)
    assert (CLASS, "page_target.create") in auth.actions
    assert (CLASS, "page_target.load") in auth.actions
    assert (CLASS, "page_target.list") in auth.actions
    assert not (target_path(tmp_path).parents[2] / "routes").exists()
    assert not (tmp_path / "portia" / "operations").exists()


def test_multi_page_ordering_and_page_indices(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    second = page(page_id="ptgt_classroom_02", index=2)
    first = page()
    pages.create_or_load(second, authorization=auth)
    pages.create_or_load(first, authorization=auth)
    assert pages.list_targets(CLASS, WORK, authorization=auth) == (first, second)


def test_same_page_id_conflict_preserves_exact_bytes(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    pages.create_or_load(page(), authorization=auth)
    before = target_path(tmp_path).read_bytes()
    revised = page().to_dict()
    revised["capture_mode"] = "manual_transcription"
    with pytest.raises(PortiaConflictError, match="historical state"):
        pages.create_or_load(PageTargetV2(revised), authorization=auth)
    assert target_path(tmp_path).read_bytes() == before


def test_same_index_is_rejected_even_with_other_id(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    pages.create_or_load(page(), authorization=auth)
    with pytest.raises(PortiaConflictError, match="index"):
        pages.create_or_load(
            page(page_id="ptgt_different", index=1), authorization=auth
        )
    assert not target_path(tmp_path, "ptgt_different").exists()


def test_casefold_id_collision_is_rejected(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    pages.create_or_load(page(page_id="ptgt_Case"), authorization=auth)
    with pytest.raises(PortiaConflictError, match="case collision"):
        pages.create_or_load(
            page(page_id="ptgt_case", index=2), authorization=auth
        )


def test_closed_batch_blocks_new_pages_but_allows_exact_retry(tmp_path: Path) -> None:
    batches, pages, auth = workspace(tmp_path)
    existing = page()
    pages.create_or_load(existing, authorization=auth)
    batches.transition(CLASS, WORK, "closed", authorization=auth)
    assert pages.create_or_load(existing, authorization=auth) == existing
    with pytest.raises(PortiaConflictError, match="open"):
        pages.create_or_load(
            page(page_id="ptgt_after_close", index=2), authorization=auth
        )
    assert (
        pages.load(CLASS, WORK, existing.logical_id or "", authorization=auth)
        == existing
    )


def test_cancelled_batch_blocks_new_pages(tmp_path: Path) -> None:
    batches, pages, auth = workspace(tmp_path)
    batches.transition(CLASS, WORK, "cancelled", authorization=auth)
    with pytest.raises(PortiaConflictError, match="open"):
        pages.create_or_load(page(), authorization=auth)
    assert not target_path(tmp_path).exists()


def test_authorization_rejects_cross_class_before_any_write(tmp_path: Path) -> None:
    _batches, pages, _auth = workspace(tmp_path)
    with pytest.raises(PermissionError):
        pages.create_or_load(page(), authorization=Authorized(()))
    assert not target_path(tmp_path).exists()
    with pytest.raises(PermissionError):
        pages.list_targets(CLASS, WORK, authorization=Authorized(()))


def test_creation_attribution_cannot_be_self_asserted(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    tampered = page().to_dict()
    tampered["created_by"] = {
        "type": "system_process",
        "process_id": "another_actor",
    }
    with pytest.raises(CapturePreparationError, match="attribution"):
        pages.create_or_load(PageTargetV2(tampered), authorization=auth)
    assert not target_path(tmp_path).exists()


def test_historical_v1_exact_read_no_migration(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    raw = wire("tests/fixtures/issue_20/valid/02-page_target.json")
    prior_bytes = (
        ROOT / "tests/fixtures/issue_20/valid/02-page_target.json"
    ).read_bytes()
    path = target_path(tmp_path, "ptgt_page_01")
    path.parent.mkdir(parents=True)
    path.write_bytes(prior_bytes)
    loaded = pages.load(CLASS, WORK, "ptgt_page_01", authorization=auth)
    assert isinstance(loaded, PageTargetV1)
    assert loaded.to_dict() == raw
    assert pages.list_targets(CLASS, WORK, authorization=auth) == (loaded,)
    assert path.read_bytes() == prior_bytes
    with pytest.raises(CapturePreparationError, match="only page_target@2"):
        pages.create_or_load(loaded, authorization=auth)  # type: ignore[arg-type]


def test_malformed_and_mismatched_files_are_not_repaired(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    path = target_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":"2","schema_version":"2"}')
    with pytest.raises(PortiaCorruptionError):
        pages.list_targets(CLASS, WORK, authorization=auth)
    path.write_bytes(json.dumps(page(page_id="ptgt_wrong_owner").to_dict()).encode())
    with pytest.raises(PortiaCorruptionError, match="ownership"):
        pages.load(CLASS, WORK, "ptgt_classroom_01", authorization=auth)
    assert path.exists()


def test_unsupported_version_fails_closed(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    path = target_path(tmp_path)
    path.parent.mkdir(parents=True)
    data = page().to_dict()
    data["schema_version"] = "3"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(PortiaCorruptionError, match="unknown version"):
        pages.load(CLASS, WORK, "ptgt_classroom_01", authorization=auth)


def test_missing_batch_or_missing_target_is_not_synthesized(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    with pytest.raises(PortiaNotFoundError):
        pages.load(CLASS, WORK, "ptgt_nonexistent", authorization=auth)
    with pytest.raises(PortiaNotFoundError):
        pages.load(CLASS, "cbat_nonexistent", "ptgt_nonexistent", authorization=auth)
    assert not target_path(tmp_path).exists()


def test_existing_lock_is_not_cleared_by_page_writer(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    lock = target_path(tmp_path).parents[2] / ".capture-batch-lifecycle.lock"
    lock.write_text("interrupted operation", encoding="utf-8")
    with pytest.raises(PortiaRecoveryRequiredError, match="lock exists"):
        pages.create_or_load(page(), authorization=auth)
    assert lock.exists()
    assert not target_path(tmp_path).exists()


def test_corrupt_competing_index_prevents_new_page(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    path = target_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(json.dumps(page().to_dict()).encode())
    other = target_path(tmp_path, "ptgt_other")
    other.write_bytes(
        json.dumps(page(page_id="ptgt_other", index=1).to_dict()).encode()
    )
    with pytest.raises(PortiaCorruptionError, match="index collision"):
        pages.create_or_load(page(page_id="ptgt_new", index=3), authorization=auth)
    assert not target_path(tmp_path, "ptgt_new").exists()


def test_link_like_target_collection_denied(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    collection = target_path(tmp_path).parent
    collection.parent.mkdir(parents=True)
    try:
        collection.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable in this Windows environment")
    with pytest.raises(PortiaPathError, match="link-like"):
        pages.create_or_load(page(), authorization=auth)
    assert tuple(outside.iterdir()) == ()


def test_concurrent_different_ids_same_index_cannot_both_commit(tmp_path: Path) -> None:
    _batches, pages, auth = workspace(tmp_path)
    barrier = Barrier(2)

    def attempt(page_id: str) -> str:
        barrier.wait()
        try:
            pages.create_or_load(page(page_id=page_id), authorization=auth)
            return "success"
        except (PortiaConflictError, PortiaRecoveryRequiredError):
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = tuple(pool.map(attempt, ("ptgt_race_a", "ptgt_race_b")))
    assert sorted(outcomes) == ["blocked", "success"]
    assert len(pages.list_targets(CLASS, WORK, authorization=auth)) == 1


def test_invalid_schema_rules_covered_without_public_contract_changes() -> None:
    bad = page().to_dict()
    bad["page_index"] = 0
    with pytest.raises(ValueError):
        PageTargetV2(bad)
    invalid = page().to_dict()
    invalid["entry_layout"] = {
        "mode": "multi_entry",
        "entry_keys": ["observation_01", "observation_02"],
        "context_entry_key": "missing_entry",
    }
    with pytest.raises(ValueError):
        PageTargetV2(invalid)
