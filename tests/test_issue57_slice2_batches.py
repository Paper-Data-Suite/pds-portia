"""Issue #57 Slice 2 synthetic Capture Batch storage and lifecycle tests."""

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

from portia.capture import FileCaptureBatchService
from portia.capture.contracts import CapturePreparationError
from portia.models import CaptureBatchV1
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.generated_paths import build_work_storage_revision_leaf

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
WORK = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}


class Authorized:
    def __init__(self, classes: tuple[str, ...] = (CLASS,)) -> None:
        self.classes = classes
        self.actions: list[tuple[str, str]] = []

    def require_access(self, class_id: str, operation: str) -> None:
        self.actions.append((class_id, operation))
        if class_id not in self.classes:
            raise PermissionError("class access denied")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def batch() -> CaptureBatchV1:
    data = json.loads(
        (ROOT / "tests/fixtures/issue_20/valid/01-capture_batch.json").read_text(
            encoding="utf-8"
        )
    )
    return CaptureBatchV1(data)


def workspace(tmp_path: Path) -> tuple[FileCaptureBatchService, Authorized]:
    meta_path = class_metadata_path(tmp_path, CLASS)
    meta_path.parent.mkdir(parents=True)
    metadata = create_class_metadata(
        CLASS,
        "2026-2027",
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    write_class_metadata(meta_path, metadata)
    return FileCaptureBatchService(tmp_path), Authorized()


def manifest(root: Path) -> Path:
    return safe_module_work_descendant(
        root, ModuleWorkRef("portia", CLASS, WORK), "work.json"
    )


def test_create_load_list_and_exact_retry(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    original = batch()
    assert store.list_batches(CLASS, authorization=auth) == ()
    assert store.create_or_load(original, authorization=auth) == original
    before = manifest(tmp_path).read_bytes()
    assert store.create_or_load(original, authorization=auth) == original
    assert manifest(tmp_path).read_bytes() == before
    assert store.load(CLASS, WORK, authorization=auth) == original
    assert store.list_batches(CLASS, authorization=auth) == (original,)
    assert (CLASS, "capture_batch.create") in auth.actions
    assert (CLASS, "capture_batch.load") in auth.actions
    assert (CLASS, "capture_batch.list") in auth.actions
    assert not (manifest(tmp_path).parent / "records").exists()
    assert not (manifest(tmp_path).parent / "routes").exists()


def test_conflicting_retry_never_rewrites_canonical_bytes(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    original = batch()
    store.create_or_load(original, authorization=auth)
    before = manifest(tmp_path).read_bytes()
    different = original.to_dict()
    different["label"] = "different batch"
    with pytest.raises(PortiaConflictError):
        store.create_or_load(CaptureBatchV1(different), authorization=auth)
    assert manifest(tmp_path).read_bytes() == before


def test_trusted_attribution_required_and_class_gate_first(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    with pytest.raises(PermissionError):
        store.create_or_load(batch(), authorization=Authorized(()))
    assert not manifest(tmp_path).exists()
    tampered = batch().to_dict()
    tampered["created_by"] = {"type": "system_process", "process_id": "other"}
    with pytest.raises(CapturePreparationError, match="attribution"):
        store.create_or_load(CaptureBatchV1(tampered), authorization=auth)
    assert not manifest(tmp_path).exists()


def test_non_json_trusted_attribution_rejected_before_write(tmp_path: Path) -> None:
    store, _auth = workspace(tmp_path)

    class InvalidAttribution(Authorized):
        def attribution(self) -> Mapping[str, object]:
            return {"type": "system_process", "process_id": object()}

    with pytest.raises(CapturePreparationError, match="attribution"):
        store.create_or_load(batch(), authorization=InvalidAttribution())
    assert not manifest(tmp_path).exists()


def test_core_class_context_must_exist(tmp_path: Path) -> None:
    store, auth = FileCaptureBatchService(tmp_path), Authorized()
    with pytest.raises(CapturePreparationError, match="Core class metadata"):
        store.create_or_load(batch(), authorization=auth)
    assert not manifest(tmp_path).exists()


def test_closed_and_cancelled_are_terminal_and_retryable(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    original = batch()
    store.create_or_load(original, authorization=auth)
    before = manifest(tmp_path).read_bytes()
    closed = store.transition(CLASS, WORK, "closed", authorization=auth)
    assert closed.status == "closed"
    assert store.transition(CLASS, WORK, "closed", authorization=auth) == closed
    assert store.load(CLASS, WORK, authorization=auth) == closed
    with pytest.raises(PortiaConflictError, match="terminal"):
        store.transition(CLASS, WORK, "cancelled", authorization=auth)
    with pytest.raises(PortiaConflictError):
        store.create_or_load(original, authorization=auth)
    history_leaf = build_work_storage_revision_leaf(
        "capture_batch", WORK, fingerprint_bytes(before).digest
    )
    history = manifest(tmp_path).parent / "history" / "storage_revisions" / history_leaf
    assert history.read_bytes() == before
    assert closed.to_dict()["created_at"] == original.to_dict()["created_at"]
    assert closed.to_dict()["created_by"] == original.to_dict()["created_by"]
    assert closed.to_dict()["updated_by"] == ACTOR
    assert "observation" not in closed.to_dict()
    assert not (manifest(tmp_path).parent / ".capture-batch-lifecycle.lock").exists()


def test_cancel_directly_from_open(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    store.create_or_load(batch(), authorization=auth)
    assert store.transition(CLASS, WORK, "cancelled", authorization=auth).status == "cancelled"
    with pytest.raises(CapturePreparationError, match="terminal"):
        store.transition(CLASS, WORK, "open", authorization=auth)  # type: ignore[arg-type]


def test_missing_and_corrupt_manifests_do_not_silently_repair(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    with pytest.raises(PortiaNotFoundError):
        store.load(CLASS, WORK, authorization=auth)
    store.create_or_load(batch(), authorization=auth)
    path = manifest(tmp_path)
    path.write_text('{"schema_version":"1","schema_version":"1"}', encoding="utf-8")
    with pytest.raises(PortiaCorruptionError):
        store.load(CLASS, WORK, authorization=auth)
    with pytest.raises(PortiaCorruptionError):
        store.list_batches(CLASS, authorization=auth)


def test_existing_orphan_root_requires_recovery(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    orphan = manifest(tmp_path).parent
    (orphan / "routes").mkdir(parents=True)
    with pytest.raises(PortiaRecoveryRequiredError, match="without a manifest"):
        store.create_or_load(batch(), authorization=auth)
    assert not manifest(tmp_path).exists()


def test_lifecycle_lock_cannot_be_automatically_cleared(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    store.create_or_load(batch(), authorization=auth)
    lock = manifest(tmp_path).parent / ".capture-batch-lifecycle.lock"
    lock.write_text("possibly interrupted work", encoding="utf-8")
    prior = manifest(tmp_path).read_bytes()
    with pytest.raises(PortiaRecoveryRequiredError, match="lock exists"):
        store.transition(CLASS, WORK, "closed", authorization=auth)
    assert lock.exists()
    assert manifest(tmp_path).read_bytes() == prior


def test_failed_replacement_leaves_original_and_prior_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, auth = workspace(tmp_path)
    store.create_or_load(batch(), authorization=auth)
    prior = manifest(tmp_path).read_bytes()

    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic replacement failure")

    with monkeypatch.context() as patch:
        patch.setattr("portia.capture.batches.guarded_replace", fail_replace)
        with pytest.raises(OSError, match="synthetic"):
            store.transition(CLASS, WORK, "closed", authorization=auth)
    assert manifest(tmp_path).read_bytes() == prior
    assert not (manifest(tmp_path).parent / ".capture-batch-lifecycle.lock").exists()
    assert store.transition(CLASS, WORK, "closed", authorization=auth).status == "closed"


def test_link_like_work_roots_refused_without_outside_writes(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    actual = tmp_path / "outside"
    actual.mkdir()
    work = manifest(tmp_path).parent
    work.parent.mkdir(parents=True)
    try:
        work.symlink_to(actual, target_is_directory=True)
    except (NotImplementedError, OSError):
        pytest.skip("symlinks are unavailable in this environment")
    with pytest.raises(PortiaPathError, match="link-like"):
        store.create_or_load(batch(), authorization=auth)
    assert tuple(actual.iterdir()) == ()


def test_generated_work_root_is_non_domain(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    store.create_or_load(batch(), authorization=auth)
    assert store.list_batches(CLASS, authorization=auth)[0].work_kind == "capture_batch"
    assert not (tmp_path / "portia" / "operations").exists()


def test_concurrent_terminal_transitions_do_not_both_win(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    store.create_or_load(batch(), authorization=auth)
    barrier = Barrier(2)

    def finish(status: str) -> tuple[str, str]:
        barrier.wait()
        try:
            result = store.transition(
                CLASS, WORK, status, authorization=auth  # type: ignore[arg-type]
            )
            return "success", str(result.status)
        except (PortiaConflictError, PortiaRecoveryRequiredError) as exc:
            return "blocked", type(exc).__name__

    with ThreadPoolExecutor(max_workers=2) as workers:
        pending = [workers.submit(finish, status) for status in ("closed", "cancelled")]
        outcomes = [job.result() for job in pending]
    assert sum(outcome[0] == "success" for outcome in outcomes) == 1
    assert sum(outcome[0] == "blocked" for outcome in outcomes) == 1
    assert store.load(CLASS, WORK, authorization=auth).status in {"closed", "cancelled"}
    assert not (manifest(tmp_path).parent / ".capture-batch-lifecycle.lock").exists()


def test_other_portia_work_kinds_not_listed_as_batches(tmp_path: Path) -> None:
    store, auth = workspace(tmp_path)
    module_work = manifest(tmp_path).parent.parent
    (module_work / "evt_valid_external_work").mkdir(parents=True)
    (module_work / "sup_valid_external_work").mkdir(parents=True)
    assert store.list_batches(CLASS, authorization=auth) == ()
