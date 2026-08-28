"""Canonical Portia record repository over the accepted filesystem topology."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from portia.models import PortiaRecord, parse_portia_record
from portia.models.identifiers import validate_external_id, validate_portia_id
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
    work_collection_root,
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


def _validate_evidence_work_owner(
    record: PortiaRecord, work: PortiaWorkRef | ExactPortiaWorkRef
) -> None:
    """Apply Account/Observation owner-version rules in addition to path ownership."""
    _validate_work_owner(record, work)
    if record.contract not in {"account", "observation"}:
        raise PortiaOwnershipError("record is not Account or Observation evidence")
    if record.contract_version == "1":
        if work.work_kind != "event":
            raise PortiaOwnershipError(
                f"{record.contract}@1 is Event-local and cannot belong to {work.work_kind}"
            )
        return
    if record.contract_version == "2" and record.work_kind != work.work_kind:
        raise PortiaOwnershipError(
            "evidence work_kind does not agree with canonical work ownership"
        )


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

    def list_works(
        self,
        class_id: str,
        *,
        work_kind: str = "event",
        version: str = "2",
    ) -> tuple[StoredRecord, ...]:
        """Strictly enumerate one contract in one class's Portia work collection."""
        validate_external_id(class_id, "class_id")
        kind = validate_external_id(work_kind, "work_kind")
        requested_version = validate_external_id(version, "contract_version")
        if kind not in _WORK_CONTRACTS:
            raise PortiaOwnershipError("unsupported Portia work-root contract")
        collection = work_collection_root(self.workspace_root, class_id)
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError(
                f"Portia work collection is not a directory: {collection}"
            )

        records: list[StoredRecord] = []
        for child in sorted(collection.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                raise PortiaCorruptionError(
                    f"unexpected artifact in Portia work collection: {child}"
                )
            manifest = child / "work.json"
            try:
                value, _bytes, _fingerprint = read_json(manifest)
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"Portia work root lacks a readable canonical manifest: {child}"
                ) from exc
            if not isinstance(value, Mapping):
                raise PortiaCorruptionError(
                    f"Portia work manifest is not an object: {manifest}"
                )
            declared_kind = value.get("work_kind")
            declared_version = value.get("schema_version")
            work_id = value.get("work_id")
            if (
                declared_kind not in _WORK_CONTRACTS
                or not isinstance(declared_version, str)
                or not isinstance(work_id, str)
            ):
                raise PortiaCorruptionError(
                    f"Portia work manifest has incomplete canonical identity: {manifest}"
                )
            try:
                if declared_kind == "event":
                    validate_portia_id(work_id, "evt_", "work_id")
                else:
                    validate_portia_id(work_id, "sup_", "work_id")
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"Portia work directory has invalid identity: {child}"
                ) from exc
            if child.name != work_id:
                raise PortiaOwnershipError(
                    "work identity does not agree with canonical directory name"
                )
            exact = ExactPortiaWorkRef(
                class_id=class_id,
                work_id=work_id,
                work_kind=declared_kind,
                contract_version=declared_version,
            )
            stored = self.load_work(exact)
            if declared_kind == kind and declared_version == requested_version:
                records.append(stored)
        return tuple(records)

    def list_events(
        self, class_id: str, *, version: str = "2"
    ) -> tuple[StoredRecord, ...]:
        """Strictly enumerate Event roots in one explicit class scope."""
        return self.list_works(class_id, work_kind="event", version=version)

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
        if contract in {"account", "observation"}:
            _validate_evidence_work_owner(record, work)
        else:
            _validate_work_owner(record, work)
        if record.logical_id != record_id:
            raise PortiaOwnershipError("record identity does not agree with canonical filename")
        return StoredRecord(record, path, fingerprint)

    def list_work_records(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        *,
        version: str,
    ) -> tuple[StoredRecord, ...]:
        """Strictly enumerate one exact child collection beneath one exact work."""
        self.load_work(work)
        kind = validate_external_id(contract, "record_kind")
        requested_version = validate_external_id(version, "contract_version")
        collection = work_record_path(
            self.workspace_root, work, kind, "bounded_collection_probe"
        ).parent
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError(
                f"work-record collection is not a directory: {collection}"
            )
        records: list[StoredRecord] = []
        for path in sorted(collection.iterdir(), key=lambda item: item.name):
            if (
                path.name == ".portia-staging"
                and path.is_dir()
                and not path.is_symlink()
            ):
                continue
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError(
                    f"unexpected artifact in work-record collection: {path}"
                )
            try:
                record_id = validate_external_id(path.stem, "record_id")
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"work-record filename has invalid identity: {path}"
                ) from exc
            records.append(
                self.load_work_record(
                    work,
                    kind,
                    requested_version,
                    record_id,
                )
            )
        return tuple(records)

    def list_work_records_mixed_versions(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        *,
        supported_versions: frozenset[str],
    ) -> tuple[StoredRecord, ...]:
        """Strictly enumerate a bounded child collection with explicit versions."""
        self.load_work(work)
        kind = validate_external_id(contract, "record_kind")
        versions = frozenset(
            validate_external_id(version, "contract_version")
            for version in supported_versions
        )
        if not versions:
            raise PortiaOwnershipError(
                "mixed-version enumeration requires at least one supported version"
            )
        collection = work_record_path(
            self.workspace_root, work, kind, "bounded_collection_probe"
        ).parent
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError(
                f"work-record collection is not a directory: {collection}"
            )

        records: list[StoredRecord] = []
        for path in sorted(collection.iterdir(), key=lambda item: item.name):
            if (
                path.name == ".portia-staging"
                and path.is_dir()
                and not path.is_symlink()
            ):
                continue
            if not path.is_file() or path.suffix != ".json":
                raise PortiaCorruptionError(
                    f"unexpected artifact in work-record collection: {path}"
                )
            try:
                record_id = validate_external_id(path.stem, "record_id")
            except Exception as exc:
                raise PortiaCorruptionError(
                    f"work-record filename has invalid identity: {path}"
                ) from exc
            value, _bytes, fingerprint = read_json(path)
            if not isinstance(value, Mapping):
                raise PortiaCorruptionError(
                    f"work-record collection member is not an object: {path}"
                )
            declared_kind = value.get("record_type")
            declared_version = value.get("schema_version")
            if declared_kind != kind:
                raise PortiaCorruptionError(
                    f"work-record collection member declares wrong contract: {path}"
                )
            if not isinstance(declared_version, str) or declared_version not in versions:
                raise PortiaCorruptionError(
                    f"work-record collection member declares unsupported version: {path}"
                )
            record = _parse_exact(kind, declared_version, value, path)
            if kind in {"account", "observation"}:
                _validate_evidence_work_owner(record, work)
            else:
                _validate_work_owner(record, work)
            if record.logical_id != record_id:
                raise PortiaOwnershipError(
                    "record identity does not agree with canonical filename"
                )
            records.append(StoredRecord(record, path, fingerprint))
        return tuple(records)

    def list_accounts(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        return self.list_work_records_mixed_versions(
            work, "account", supported_versions=frozenset({"1", "2"})
        )

    def list_observations(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        return self.list_work_records_mixed_versions(
            work, "observation", supported_versions=frozenset({"1", "2"})
        )

    def list_event_participants(
        self, work: ExactPortiaWorkRef, *, version: str = "3"
    ) -> tuple[StoredRecord, ...]:
        return self.list_work_records(work, "event_participant", version=version)

    def list_event_participant_roles(
        self, work: ExactPortiaWorkRef, *, version: str = "3"
    ) -> tuple[StoredRecord, ...]:
        return self.list_work_records(
            work, "event_participant_role", version=version
        )

    def list_work_relationships(
        self, work: ExactPortiaWorkRef, *, version: str = "2"
    ) -> tuple[StoredRecord, ...]:
        return self.list_work_records(work, "work_relationship", version=version)

    def create_work_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        if record.contract in _WORK_CONTRACTS or record.logical_id is None:
            raise PortiaOwnershipError("record is not a canonical work child")
        if record.contract in {"account", "observation"}:
            _validate_evidence_work_owner(record, work)
        else:
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
        if record.contract in {"account", "observation"}:
            _validate_evidence_work_owner(record, work)
        else:
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
