"""Version-qualified immutable representation storage for explicit migration.

This module is a storage prerequisite for ``RecordMigrationWorkflowService``.
It does not choose a current representation and never migrates during reads.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaOwnershipError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes, read_json
from portia.storage.paths import work_manifest_path, work_record_path, work_root
from portia.storage.repository import PortiaRepository, StoredRecord

_WORK_CONTRACTS = frozenset({"event", "support_process"})


def version_qualified_representation_path(
    workspace_root: str | Path,
    work: ExactPortiaWorkRef,
    contract: str,
    logical_id: str,
    contract_version: str,
) -> Path:
    """Return one immutable exact-version representation path.

    The version namespace is canonical migration evidence.  It is intentionally
    separate from ``history/storage_revisions``, which remains technical storage
    history rather than version-selection authority.
    """
    kind = validate_external_id(contract, "record_kind")
    identifier = validate_external_id(logical_id, "record_id")
    version = validate_external_id(contract_version, "contract_version")
    return (
        work_root(workspace_root, work)
        / "representations"
        / kind
        / identifier
        / f"{version}.json"
    )


def _require_owner(
    record: PortiaRecord,
    work: ExactPortiaWorkRef,
    *,
    contract: str,
    logical_id: str,
) -> None:
    if record.module_id != "portia":
        raise PortiaOwnershipError(
            'version-qualified representation module_id must be "portia"'
        )
    if record.contract != contract:
        raise PortiaOwnershipError(
            "version-qualified representation contract does not match exact identity"
        )
    if record.logical_id != logical_id:
        raise PortiaOwnershipError(
            "version-qualified representation logical identity does not match"
        )
    if record.class_id is not None and record.class_id != work.class_id:
        raise PortiaOwnershipError(
            "version-qualified representation class identity does not match owner"
        )
    if record.work_id is not None and record.work_id != work.work_id:
        raise PortiaOwnershipError(
            "version-qualified representation work identity does not match owner"
        )

    data = record.to_dict()
    if contract in _WORK_CONTRACTS:
        if logical_id != work.work_id or contract != work.work_kind:
            raise PortiaOwnershipError(
                "work representation identity does not match exact work reference"
            )
        if data.get("work_kind") != work.work_kind:
            raise PortiaOwnershipError(
                "work representation kind does not match exact work reference"
            )
        return

    if contract in {"account", "observation"}:
        if record.contract_version == "1" and work.work_kind != "event":
            raise PortiaOwnershipError(
                f"{contract}@1 representation is Event-local"
            )
        declared_work_kind = data.get("work_kind")
        if (
            record.contract_version == "2"
            and declared_work_kind is not None
            and declared_work_kind != work.work_kind
        ):
            raise PortiaOwnershipError(
                "evidence representation work_kind does not match owner"
            )


def _parse_exact(
    contract: str,
    version: str,
    value: object,
    path: Path,
) -> PortiaRecord:
    try:
        return parse_portia_record(contract, version, value)
    except Exception as exc:
        raise PortiaCorruptionError(
            f"persisted representation does not satisfy {contract}@{version}: {path}"
        ) from exc


def _read_exact(
    path: Path,
    work: ExactPortiaWorkRef,
    *,
    contract: str,
    version: str,
    logical_id: str,
) -> StoredRecord:
    value, _content, fingerprint = read_json(path)
    record = _parse_exact(contract, version, value, path)
    _require_owner(record, work, contract=contract, logical_id=logical_id)
    return StoredRecord(record, path, fingerprint)


def _read_current_any_version(
    path: Path,
    work: ExactPortiaWorkRef,
    *,
    contract: str,
    logical_id: str,
) -> StoredRecord:
    value, _content, fingerprint = read_json(path)
    if not isinstance(value, Mapping):
        raise PortiaCorruptionError(
            f"current representation is not a JSON object: {path}"
        )
    declared_version = value.get("schema_version")
    if not isinstance(declared_version, str):
        raise PortiaCorruptionError(
            f"current representation has no explicit schema_version: {path}"
        )
    record = _parse_exact(contract, declared_version, value, path)
    _require_owner(record, work, contract=contract, logical_id=logical_id)
    return StoredRecord(record, path, fingerprint)


class MigrationRepresentationStore:
    """Preserve and exactly resolve migration source/destination representations.

    This store deliberately has no operation that changes the ordinary current
    file.  Current-representation selection belongs to the later journaled
    migration workflow after destination and certificate acceptance.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)

    def _work_version_path(self, work: ExactPortiaWorkRef) -> Path:
        return version_qualified_representation_path(
            self.workspace_root,
            work,
            work.work_kind,
            work.work_id,
            work.contract_version,
        )

    def _record_version_path(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> Path:
        return version_qualified_representation_path(
            self.workspace_root,
            reference.work_ref,
            reference.record_ref.record_kind,
            reference.record_ref.record_id,
            reference.record_ref.contract_version,
        )

    def load_preserved_work_representation(
        self,
        work: ExactPortiaWorkRef,
    ) -> StoredRecord:
        """Load only the immutable version-qualified work representation."""
        return _read_exact(
            self._work_version_path(work),
            work,
            contract=work.work_kind,
            version=work.contract_version,
            logical_id=work.work_id,
        )

    def load_preserved_work_record_representation(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Load only the immutable version-qualified child representation."""
        self.load_work_representation(reference.work_ref)
        return _read_exact(
            self._record_version_path(reference),
            reference.work_ref,
            contract=reference.record_ref.record_kind,
            version=reference.record_ref.contract_version,
            logical_id=reference.record_ref.record_id,
        )

    def load_work_representation(
        self,
        work: ExactPortiaWorkRef,
    ) -> StoredRecord:
        """Resolve exactly the requested work version, never a version winner."""
        current_path = work_manifest_path(self.workspace_root, work)
        try:
            current = _read_current_any_version(
                current_path,
                work,
                contract=work.work_kind,
                logical_id=work.work_id,
            )
        except PortiaNotFoundError:
            return self.load_preserved_work_representation(work)
        if current.record.contract_version == work.contract_version:
            return current
        return self.load_preserved_work_representation(work)

    def load_work_record_representation(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Resolve exactly the requested child version without implicit migration."""
        self.load_work_representation(reference.work_ref)
        current_path = work_record_path(
            self.workspace_root,
            reference.work_ref,
            reference.record_ref.record_kind,
            reference.record_ref.record_id,
        )
        try:
            current = _read_current_any_version(
                current_path,
                reference.work_ref,
                contract=reference.record_ref.record_kind,
                logical_id=reference.record_ref.record_id,
            )
        except PortiaNotFoundError:
            return self.load_preserved_work_record_representation(reference)
        if current.record.contract_version == reference.record_ref.contract_version:
            return current
        return self.load_preserved_work_record_representation(reference)

    def preserve_current_work_representation(
        self,
        source: ExactPortiaWorkRef,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Copy exact current source bytes into the immutable version namespace."""
        current = self.repository.load_work(source)
        if current.fingerprint != expected:
            raise PortiaConflictError(
                "expected migration-source work fingerprint does not match current bytes"
            )
        content = read_bytes(current.path)
        path = self._work_version_path(source)
        fingerprint = exclusive_create(path, content)
        return StoredRecord(current.record, path, fingerprint)

    def preserve_current_work_record_representation(
        self,
        source: ExactPortiaWorkRecordRef,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Copy exact current child bytes into the immutable version namespace."""
        current = self.repository.load_work_record(
            source.work_ref,
            source.record_ref.record_kind,
            source.record_ref.contract_version,
            source.record_ref.record_id,
        )
        if current.fingerprint != expected:
            raise PortiaConflictError(
                "expected migration-source record fingerprint does not match current bytes"
            )
        content = read_bytes(current.path)
        path = self._record_version_path(source)
        fingerprint = exclusive_create(path, content)
        return StoredRecord(current.record, path, fingerprint)

    def create_destination_work_representation(
        self,
        source: ExactPortiaWorkRef,
        destination: PortiaRecord,
    ) -> StoredRecord:
        """Create an immutable same-identity work destination after source preservation."""
        self.load_preserved_work_representation(source)
        if destination.contract != source.work_kind:
            raise PortiaOwnershipError(
                "migration destination must preserve the work semantic family"
            )
        if destination.logical_id != source.work_id:
            raise PortiaOwnershipError(
                "migration destination must preserve the stable work identifier"
            )
        if destination.contract_version == source.contract_version:
            raise PortiaConflictError(
                "migration destination contract version must differ from source"
            )
        destination_ref = ExactPortiaWorkRef(
            module_id=source.module_id,
            class_id=source.class_id,
            work_id=source.work_id,
            work_kind=source.work_kind,
            contract_version=destination.contract_version,
        )
        _require_owner(
            destination,
            destination_ref,
            contract=source.work_kind,
            logical_id=source.work_id,
        )
        path = self._work_version_path(destination_ref)
        fingerprint = exclusive_create(
            path,
            canonical_json_bytes(destination.to_dict()),
        )
        return StoredRecord(destination, path, fingerprint)

    def create_destination_work_record_representation(
        self,
        source: ExactPortiaWorkRecordRef,
        destination: PortiaRecord,
    ) -> StoredRecord:
        """Create an immutable same-identity child destination after source preservation."""
        self.load_preserved_work_record_representation(source)
        if destination.contract != source.record_ref.record_kind:
            raise PortiaOwnershipError(
                "migration destination must preserve the record semantic family"
            )
        if destination.logical_id != source.record_ref.record_id:
            raise PortiaOwnershipError(
                "migration destination must preserve the stable record identifier"
            )
        if destination.contract_version == source.record_ref.contract_version:
            raise PortiaConflictError(
                "migration destination contract version must differ from source"
            )
        _require_owner(
            destination,
            source.work_ref,
            contract=source.record_ref.record_kind,
            logical_id=source.record_ref.record_id,
        )
        destination_ref = ExactPortiaWorkRecordRef(
            work_ref=source.work_ref,
            record_ref=ExactLocalRecordRef(
                record_kind=source.record_ref.record_kind,
                record_id=source.record_ref.record_id,
                contract_version=destination.contract_version,
            ),
        )
        path = self._record_version_path(destination_ref)
        fingerprint = exclusive_create(
            path,
            canonical_json_bytes(destination.to_dict()),
        )
        return StoredRecord(destination, path, fingerprint)
