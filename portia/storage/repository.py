"""Canonical Portia record repository over the accepted filesystem topology."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef, PortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaOwnershipError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import exclusive_create, guarded_replace, read_json
from portia.storage.paths import (
    actor_child_path,
    actor_directory_removal_path,
    actor_record_path,
    actor_storage_history_path,
    work_manifest_path,
    work_record_path,
    work_storage_history_path,
)


@dataclass(frozen=True, slots=True)
class StoredRecord:
    record: PortiaRecord
    path: Path
    fingerprint: ContentFingerprint


_WORK_CONTRACTS = {"event", "support_process"}
HistoryPathBuilder = Callable[[str], Path]


def _parse_exact(contract: str, version: str, value: object, path: Path) -> PortiaRecord:
    try:
        return parse_portia_record(contract, version, value)
    except Exception as exc:
        raise PortiaCorruptionError(
            f"persisted artifact does not satisfy {contract}@{version}: {path}"
        ) from exc


def _validate_work_owner(record: PortiaRecord, work: PortiaWorkRef | ExactPortiaWorkRef) -> None:
    data = record.to_dict()
    if record.module_id != "portia":
        raise PortiaOwnershipError('persisted record module_id must be "portia"')
    if record.contract in _WORK_CONTRACTS:
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise PortiaOwnershipError("work root identity does not agree with canonical path")
        if record.work_kind != work.work_kind:
            raise PortiaOwnershipError("work root kind does not agree with canonical path")
        return
    declared_work_id = record.work_id
    if declared_work_id is not None and declared_work_id != work.work_id:
        raise PortiaOwnershipError("child record work identity does not agree with canonical path")
    class_id = record.class_id
    if class_id is not None and class_id != work.class_id:
        raise PortiaOwnershipError("child record class identity does not agree with canonical path")
    work_ref = data.get("work_ref")
    if isinstance(work_ref, dict):
        if work_ref.get("module_id") not in {None, "portia"}:
            raise PortiaOwnershipError("child record work_ref names another module")
        if work_ref.get("class_id") != work.class_id or work_ref.get("work_id") != work.work_id:
            raise PortiaOwnershipError("child record work_ref does not agree with canonical path")


def _validate_actor_owner(record: PortiaRecord, actor_id: str) -> None:
    if record.module_id != "portia":
        raise PortiaOwnershipError('persisted record module_id must be "portia"')
    data = record.to_dict()
    declared = data.get("actor_id")
    if declared is not None and declared != actor_id:
        raise PortiaOwnershipError("Actor-directory record owner disagrees with canonical path")
    actor_ref = data.get("actor_ref")
    if isinstance(actor_ref, dict) and actor_ref.get("actor_id") != actor_id:
        raise PortiaOwnershipError("Actor-directory record actor_ref disagrees with canonical path")


def _preserve_prior(
    path: Path,
    *,
    contract: str,
    version: str,
    expected: ContentFingerprint,
    history_path: HistoryPathBuilder,
) -> None:
    prior_value, prior_bytes, prior_fingerprint = read_json(path)
    if prior_fingerprint != expected:
        raise PortiaConflictError("expected prior state does not match current record")
    _parse_exact(contract, version, prior_value, path)
    history = history_path(prior_fingerprint.digest)
    try:
        exclusive_create(history, prior_bytes)
    except PortiaConflictError as exc:
        existing_value, existing_bytes, existing_fingerprint = read_json(history)
        if existing_fingerprint != prior_fingerprint or existing_bytes != prior_bytes:
            raise PortiaCorruptionError("technical storage-history collision") from exc
        _parse_exact(contract, version, existing_value, history)


class PortiaRepository:
    """Strict canonical persistence facade used by later Portia services."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.workspace_root = Path(workspace_root)

    def load_work(self, work: ExactPortiaWorkRef) -> StoredRecord:
        path = work_manifest_path(self.workspace_root, work)
        value, _bytes, fingerprint = read_json(path)
        record = _parse_exact(work.work_kind, work.contract_version, value, path)
        _validate_work_owner(record, work)
        return StoredRecord(record, path, fingerprint)

    def create_work(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        if record.contract != work.work_kind or record.contract_version != work.contract_version:
            raise PortiaOwnershipError("work model does not match exact work reference")
        _validate_work_owner(record, work)
        path = work_manifest_path(self.workspace_root, work)
        content = canonical_json_bytes(record.to_dict())
        fingerprint = exclusive_create(path, content)
        return StoredRecord(record, path, fingerprint)

    def replace_work(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        if record.contract != work.work_kind or record.contract_version != work.contract_version:
            raise PortiaOwnershipError("work model does not match exact work reference")
        _validate_work_owner(record, work)
        path = work_manifest_path(self.workspace_root, work)
        _preserve_prior(
            path,
            contract=record.contract,
            version=record.contract_version,
            expected=expected,
            history_path=lambda digest: work_storage_history_path(
                self.workspace_root,
                work,
                record.contract,
                work.work_id,
                digest,
            ),
        )
        fingerprint = guarded_replace(
            path,
            canonical_json_bytes(record.to_dict()),
            expected=expected,
        )
        return StoredRecord(record, path, fingerprint)

    def load_work_record(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        version: str,
        record_id: str,
    ) -> StoredRecord:
        path = work_record_path(self.workspace_root, work, contract, record_id)
        value, _bytes, fingerprint = read_json(path)
        record = _parse_exact(contract, version, value, path)
        _validate_work_owner(record, work)
        if record.logical_id != record_id:
            raise PortiaOwnershipError("record identity does not agree with canonical filename")
        return StoredRecord(record, path, fingerprint)

    def create_work_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        if record.contract in _WORK_CONTRACTS or record.logical_id is None:
            raise PortiaOwnershipError("record is not a canonical work child")
        _validate_work_owner(record, work)
        # A child write is never accepted into a missing or contradictory work root.
        self.load_work(work)
        path = work_record_path(
            self.workspace_root, work, record.contract, record.logical_id
        )
        content = canonical_json_bytes(record.to_dict())
        fingerprint = exclusive_create(path, content)
        return StoredRecord(record, path, fingerprint)

    def replace_work_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        if record.logical_id is None:
            raise PortiaOwnershipError("record has no canonical logical identifier")
        record_id = record.logical_id
        _validate_work_owner(record, work)
        self.load_work(work)
        path = work_record_path(
            self.workspace_root, work, record.contract, record_id
        )
        _preserve_prior(
            path,
            contract=record.contract,
            version=record.contract_version,
            expected=expected,
            history_path=lambda digest: work_storage_history_path(
                self.workspace_root,
                work,
                record.contract,
                record_id,
                digest,
            ),
        )
        fingerprint = guarded_replace(
            path,
            canonical_json_bytes(record.to_dict()),
            expected=expected,
        )
        return StoredRecord(record, path, fingerprint)

    def load_actor(self, actor_id: str, *, version: str = "1") -> StoredRecord:
        path = actor_record_path(self.workspace_root, actor_id)
        value, _bytes, fingerprint = read_json(path)
        record = _parse_exact("actor", version, value, path)
        _validate_actor_owner(record, actor_id)
        if record.logical_id != actor_id:
            raise PortiaOwnershipError("Actor identity does not agree with canonical filename")
        return StoredRecord(record, path, fingerprint)

    def create_actor(self, record: PortiaRecord) -> StoredRecord:
        if record.contract != "actor" or record.logical_id is None:
            raise PortiaOwnershipError("record must be an Actor root")
        actor_id = record.logical_id
        _validate_actor_owner(record, actor_id)
        path = actor_record_path(self.workspace_root, actor_id)
        fingerprint = exclusive_create(path, canonical_json_bytes(record.to_dict()))
        return StoredRecord(record, path, fingerprint)

    def replace_actor(
        self,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        if record.contract != "actor" or record.logical_id is None:
            raise PortiaOwnershipError("record must be an Actor root")
        actor_id = record.logical_id
        _validate_actor_owner(record, actor_id)
        path = actor_record_path(self.workspace_root, actor_id)
        _preserve_prior(
            path,
            contract="actor",
            version=record.contract_version,
            expected=expected,
            history_path=lambda digest: actor_storage_history_path(
                self.workspace_root,
                actor_id,
                "actor",
                actor_id,
                digest,
            ),
        )
        fingerprint = guarded_replace(
            path,
            canonical_json_bytes(record.to_dict()),
            expected=expected,
        )
        return StoredRecord(record, path, fingerprint)

    def load_actor_child(
        self,
        actor_id: str,
        contract: str,
        version: str,
        record_id: str,
    ) -> StoredRecord:
        path = actor_child_path(self.workspace_root, actor_id, contract, record_id)
        value, _bytes, fingerprint = read_json(path)
        record = _parse_exact(contract, version, value, path)
        _validate_actor_owner(record, actor_id)
        if record.logical_id != record_id:
            raise PortiaOwnershipError(
                "Actor-directory record identity disagrees with canonical filename"
            )
        return StoredRecord(record, path, fingerprint)

    def create_actor_child(self, actor_id: str, record: PortiaRecord) -> StoredRecord:
        if record.logical_id is None or record.contract == "actor":
            raise PortiaOwnershipError("record must be an Actor-directory child")
        self.load_actor(actor_id)
        _validate_actor_owner(record, actor_id)
        path = actor_child_path(
            self.workspace_root, actor_id, record.contract, record.logical_id
        )
        fingerprint = exclusive_create(path, canonical_json_bytes(record.to_dict()))
        return StoredRecord(record, path, fingerprint)

    def replace_actor_child(
        self,
        actor_id: str,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        if record.logical_id is None or record.contract == "actor":
            raise PortiaOwnershipError("record must be an Actor-directory child")
        self.load_actor(actor_id)
        _validate_actor_owner(record, actor_id)
        record_id = record.logical_id
        path = actor_child_path(self.workspace_root, actor_id, record.contract, record_id)
        _preserve_prior(
            path,
            contract=record.contract,
            version=record.contract_version,
            expected=expected,
            history_path=lambda digest: actor_storage_history_path(
                self.workspace_root,
                actor_id,
                record.contract,
                record_id,
                digest,
            ),
        )
        fingerprint = guarded_replace(
            path,
            canonical_json_bytes(record.to_dict()),
            expected=expected,
        )
        return StoredRecord(record, path, fingerprint)

    def create_actor_directory_removal(self, record: PortiaRecord) -> StoredRecord:
        if record.contract != "actor_directory_exceptional_removal" or record.logical_id is None:
            raise PortiaOwnershipError("record must be an Actor-directory removal certificate")
        path = actor_directory_removal_path(self.workspace_root, record.logical_id)
        fingerprint = exclusive_create(path, canonical_json_bytes(record.to_dict()))
        return StoredRecord(record, path, fingerprint)
