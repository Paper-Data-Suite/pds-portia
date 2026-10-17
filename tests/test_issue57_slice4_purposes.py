"""Synthetic #57 Slice 4 Page Target purpose and exact-context acceptance."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import create_class_metadata, write_class_metadata
from pds_core.routes import class_metadata_path

from portia.capture import FileCaptureBatchService, FilePageTargetService
from portia.capture.contracts import CapturePreparationError
from portia.capture.purposes import (
    resolve_existing_capture_context,
    validate_page_purpose,
)
from portia.models import CaptureBatchV1, PageTargetV2
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaCorruptionError, PortiaNotFoundError
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.paths import work_manifest_path, work_record_path
from portia.storage.repository import PortiaRepository

ROOT = Path(__file__).resolve().parents[1]
CLASS = "class_english10_p2"
BATCH = "cbat_batch_01"
ACTOR = {"type": "system_process", "process_id": "paper_capture_test"}
EVENT = "evt_p22_positive_001"
SUPPORT = "sup_p22_positive_001"


class Authorized:
    def require_access(self, class_id: str, operation: str) -> None:
        if class_id != CLASS:
            raise PermissionError("unauthorized class")

    def attribution(self) -> Mapping[str, object]:
        return ACTOR


def fixture(path: str) -> dict[str, object]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def setup(root: Path) -> tuple[FilePageTargetService, Authorized]:
    metadata = class_metadata_path(root, CLASS)
    metadata.parent.mkdir(parents=True)
    write_class_metadata(
        metadata,
        create_class_metadata(
            CLASS, "2026-2027", created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        ),
    )
    auth = Authorized()
    batches = FileCaptureBatchService(root)
    batches.create_or_load(
        CaptureBatchV1(fixture("tests/fixtures/issue_20/valid/01-capture_batch.json")),
        authorization=auth,
    )
    return FilePageTargetService(root, batch_service=batches), auth


def page(
    purpose: str = "classroom_observation_capture",
    *,
    index: int = 1,
    context: dict[str, object] | None = None,
    record_context: dict[str, object] | None = None,
) -> PageTargetV2:
    raw = fixture(
        "tests/fixtures/issue_56/slice_2/valid/"
        "page-target-v2-classroom-observation.json"
    )
    raw["class_id"] = CLASS
    raw["work_id"] = BATCH
    raw["page_target_id"] = f"ptgt_slice4_{index}"
    raw["page_index"] = index
    raw["page_purpose"] = purpose
    raw["created_by"] = ACTOR
    raw["updated_by"] = ACTOR
    if purpose != "classroom_observation_capture":
        raw["entry_layout"] = {"mode": "single_entry", "entry_keys": ["entry"]}
    if context is not None:
        raw["existing_work_context"] = context
    if record_context is not None:
        raw["existing_record_context"] = record_context
    return PageTargetV2(raw)


def work_ref(kind: str, version: str = "2") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=CLASS,
        work_id=EVENT if kind == "event" else SUPPORT,
        work_kind=kind,
        contract_version=version,
    )


def seed_work(root: Path, kind: str) -> ExactPortiaWorkRef:
    work = work_ref(kind, "2" if kind == "event" else "1")
    name = (
        "tests/fixtures/issue_22/positive/p22_01_positive_classroom_event/records/event.json"
        if kind == "event"
        else "tests/fixtures/issue_22/positive/"
        "p22_08_support_positive_outcome/support-process.json"
    )
    raw = fixture(name)
    raw["class_id"] = CLASS
    path = work_manifest_path(root, work)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(raw))
    return work


def target_path(root: Path, target: PageTargetV2) -> Path:
    return root / "classes" / CLASS / "modules" / "portia" / "work" / BATCH / (
        "records/capture_page_target/" + str(target.logical_id) + ".json"
    )


def test_classroom_page_preserves_source_only_context(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    target = page()
    validate_page_purpose(target)
    assert service.create_or_load(target, authorization=auth) == target
    assert "existing_work_context" not in target.to_dict()
    assert "existing_record_context" not in target.to_dict()
    assert not (target_path(tmp_path, target).parents[2] / "routes").exists()
    assert not (tmp_path / "portia" / "operations").exists()


@pytest.mark.parametrize("purpose", ["focused_monitoring_capture", "communication_capture"])
def test_unbound_focused_and_communication_are_supported(
    tmp_path: Path, purpose: str
) -> None:
    service, auth = setup(tmp_path)
    target = page(purpose)
    assert service.create_or_load(target, authorization=auth) == target
    assert target_path(tmp_path, target).is_file()


@pytest.mark.parametrize("purpose,kind", [
    ("focused_monitoring_capture", "event"),
    ("focused_monitoring_capture", "support_process"),
    ("communication_capture", "event"),
    ("communication_capture", "support_process"),
    ("event_evidence_capture", "event"),
    ("support_process_evidence_capture", "support_process"),
])
def test_matching_existing_work_is_verified_without_rewriting(
    tmp_path: Path, purpose: str, kind: str
) -> None:
    service, auth = setup(tmp_path)
    work = seed_work(tmp_path, kind)
    before = work_manifest_path(tmp_path, work).read_bytes()
    target = page(purpose, context=work.to_dict())
    assert service.create_or_load(target, authorization=auth) == target
    assert work_manifest_path(tmp_path, work).read_bytes() == before
    assert service.create_or_load(target, authorization=auth) == target
    assert work_manifest_path(tmp_path, work).read_bytes() == before


def test_missing_existing_work_is_rejected_before_page_write(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    target = page("focused_monitoring_capture", context=work_ref("event").to_dict())
    with pytest.raises(PortiaNotFoundError):
        service.create_or_load(target, authorization=auth)
    assert not target_path(tmp_path, target).exists()


def test_context_requires_exact_version_no_substitution(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    seed_work(tmp_path, "event")
    stale = page("communication_capture", context=work_ref("event", "1").to_dict())
    with pytest.raises(PortiaCorruptionError):
        service.create_or_load(stale, authorization=auth)
    assert not target_path(tmp_path, stale).exists()


def test_cross_class_context_denied_before_domain_read(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    work = work_ref("event").to_dict()
    work["class_id"] = "other_class"
    target = page("focused_monitoring_capture", context=work)
    with pytest.raises(CapturePreparationError, match="another class"):
        service.create_or_load(target, authorization=auth)
    assert not target_path(tmp_path, target).exists()


def test_evidence_purpose_requires_context_and_right_work_kind(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    empty = page("event_evidence_capture")
    with pytest.raises(CapturePreparationError, match="requires exact"):
        service.create_or_load(empty, authorization=auth)
    assert not target_path(tmp_path, empty).exists()
    wrong = page("event_evidence_capture", context=work_ref("support_process", "1").to_dict())
    with pytest.raises(CapturePreparationError, match="contradicts"):
        service.create_or_load(wrong, authorization=auth)


def test_matching_exact_child_context_and_conflicting_work_ref(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    work = seed_work(tmp_path, "event")
    child = fixture(
        "tests/fixtures/issue_22/positive/"
        "p22_01_positive_classroom_event/records/observation.json"
    )
    child["class_id"] = CLASS
    path = work_record_path(tmp_path, work, "observation", "obs_p22_positive_001")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(child))
    record_context = {
        "work_ref": work.to_dict(),
        "record_ref": {
            "record_kind": "observation",
            "record_id": "obs_p22_positive_001",
            "contract_version": "2",
        },
    }
    target = page(
        "communication_capture", record_context=record_context,
    )
    result = resolve_existing_capture_context(
        target,
        repository=PortiaRepository(tmp_path),
        path_guard=service.batches._safe,
    )
    assert result is not None and result.record is not None
    assert result.record.record_id == "obs_p22_positive_001"
    assert service.create_or_load(target, authorization=auth) == target

    mismatched = page(
        "communication_capture", index=2,
        context=work_ref("support_process", "1").to_dict(),
        record_context=record_context,
    )
    with pytest.raises(CapturePreparationError, match="conflicting"):
        service.create_or_load(mismatched, authorization=auth)
    assert not target_path(tmp_path, mismatched).exists()


def test_missing_exact_child_is_not_synthesized(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    work = seed_work(tmp_path, "event")
    target = page(
        "communication_capture",
        record_context={
            "work_ref": work.to_dict(),
            "record_ref": {
                "record_kind": "observation",
                "record_id": "obs_nonexistent",
                "contract_version": "2",
            },
        },
    )
    with pytest.raises(PortiaNotFoundError):
        service.create_or_load(target, authorization=auth)
    assert not target_path(tmp_path, target).exists()


def test_exact_retry_remains_valid_after_existing_work_changes(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    work = seed_work(tmp_path, "event")
    target = page("communication_capture", context=work.to_dict())
    assert service.create_or_load(target, authorization=auth) == target
    # Existing domain work may legitimately move to a new version later.
    # Exact retry of an existing Page Target must not silently rebind it.
    work_manifest_path(tmp_path, work).unlink()
    assert service.create_or_load(target, authorization=auth) == target
    assert target_path(tmp_path, target).is_file()


def test_no_page_written_for_missing_or_invalid_context(tmp_path: Path) -> None:
    service, auth = setup(tmp_path)
    target = page("event_evidence_capture", context=work_ref("event").to_dict())
    with pytest.raises(PortiaNotFoundError):
        service.create_or_load(target, authorization=auth)
    assert service.list_targets(CLASS, BATCH, authorization=auth) == ()
