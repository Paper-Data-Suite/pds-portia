"""Evidence-preserving exclusive Portia operation locks."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from portia.models import PortiaRecord
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaLockError,
)
from portia.storage.fingerprint import ContentFingerprint, canonical_json_bytes
from portia.storage.io import exact_delete, exclusive_create, read_json
from portia.storage.paths import lock_path


@dataclass(frozen=True, slots=True)
class HeldLock:
    record: PortiaRecord
    path: Path
    fingerprint: ContentFingerprint


def derive_lock_id(lock_scope: str, protected_target: object) -> str:
    key = {"lock_scope": lock_scope, "protected_target": protected_target}
    compact = json.dumps(key, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return "lock_" + hashlib.sha256(compact).hexdigest()


def _lock_application_data(
    record: PortiaRecord | Mapping[str, Any],
) -> Mapping[str, Any]:
    if isinstance(record, PortiaRecord):
        if record.contract != "operation_lock":
            raise PortiaCorruptionError("record is not an Operation Lock")
        return cast(Mapping[str, Any], record.to_dict())
    if not isinstance(record, Mapping):
        raise PortiaCorruptionError("operation lock application input is not an object")
    return record


def validate_operation_lock_application(
    record: PortiaRecord | Mapping[str, Any],
) -> None:
    """Validate version-specific lock semantics without acquiring the lock."""
    data = _lock_application_data(record)
    version = (
        record.contract_version
        if isinstance(record, PortiaRecord)
        else data.get("schema_version")
    )
    if version == "2":
        return
    if version == "3":
        from portia.storage.deliberate_export_operations import (
            validate_deliberate_export_lock,
        )

        validate_deliberate_export_lock(data)
        return
    raise PortiaCorruptionError(f"unsupported current lock version: {version}")


def validate_deliberate_export_lock_agreement(
    journal: PortiaRecord | Mapping[str, Any],
    lock: PortiaRecord | Mapping[str, Any],
) -> None:
    """Validate one v3 export lock against one exact journal v4 plan."""
    from portia.storage.deliberate_export_operations import (
        validate_deliberate_export_lock_agreement as validate_agreement,
    )

    validate_agreement(journal, lock)


class LockStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def acquire(self, record: PortiaRecord) -> HeldLock:
        if record.contract != "operation_lock" or record.contract_version != "2":
            raise PortiaLockError("current lock acquisition requires operation_lock@2")
        data = record.to_dict()
        lock_id = data.get("lock_id")
        scope = data.get("lock_scope")
        target = data.get("protected_target")
        if not isinstance(lock_id, str) or not isinstance(scope, str):
            raise PortiaCorruptionError("lock record is missing identity or scope")
        expected_id = derive_lock_id(scope, target)
        if lock_id != expected_id:
            raise PortiaLockError("lock_id does not match the canonical lock key")
        path = lock_path(self.root, lock_id)
        try:
            fingerprint = exclusive_create(path, canonical_json_bytes(data))
        except PortiaConflictError as exc:
            raise PortiaLockError(f"lock is already held: {lock_id}") from exc
        return HeldLock(record, path, fingerprint)

    def release(self, held: HeldLock) -> None:
        value, _bytes, fingerprint = read_json(held.path)
        if fingerprint != held.fingerprint:
            raise PortiaLockError("lock changed after acquisition; refusing to clear it")
        if value != held.record.to_dict():
            raise PortiaLockError("lock readback no longer matches acquired evidence")
        try:
            exact_delete(held.path, expected=held.fingerprint)
        except Exception as exc:
            raise PortiaLockError("could not release exact acquired lock") from exc
