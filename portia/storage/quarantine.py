"""Explicit enforcement of active Portia Quarantine effects."""

from __future__ import annotations

from pathlib import Path

from portia.models import PortiaRecord
from portia.storage.errors import (
    PortiaCorruptionError,
    PortiaQuarantinedError,
    PortiaRecoveryRequiredError,
)
from portia.storage.paths import portia_root
from portia.storage.series import QuarantineStore


def _work_identity(target: object) -> tuple[str, str] | None:
    if not isinstance(target, dict):
        return None
    kind = target.get("kind")
    if kind == "work":
        work = target.get("work_ref")
    elif kind == "work_record":
        composite = target.get("work_record_ref")
        work = composite.get("work_ref") if isinstance(composite, dict) else None
    else:
        return None
    if not isinstance(work, dict):
        return None
    class_id = work.get("class_id")
    work_id = work.get("work_id")
    if not isinstance(class_id, str) or not isinstance(work_id, str):
        return None
    return (class_id, work_id)


def _class_identity(target: object) -> str | None:
    if not isinstance(target, dict):
        return None
    if target.get("kind") == "class":
        value = target.get("class_id")
        return value if isinstance(value, str) else None
    work = _work_identity(target)
    return work[0] if work is not None else None


def _actor_ids(target: object) -> frozenset[str]:
    found: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, dict):
            actor_id = value.get("actor_id")
            if isinstance(actor_id, str):
                found.add(actor_id)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(target)
    return frozenset(found)


def quarantine_applies(quarantine_target: object, requested_target: object) -> bool:
    """Return whether one active Quarantine target covers the requested target."""
    if quarantine_target == requested_target:
        return True
    if not isinstance(quarantine_target, dict) or not isinstance(requested_target, dict):
        return False
    kind = quarantine_target.get("kind")
    requested_kind = requested_target.get("kind")

    if kind == "workspace":
        return True
    if kind == "class":
        quarantined_class = quarantine_target.get("class_id")
        return isinstance(quarantined_class, str) and _class_identity(
            requested_target
        ) == quarantined_class
    if kind == "work":
        return _work_identity(quarantine_target) == _work_identity(requested_target)
    if kind == "actor_directory_collection":
        return requested_kind in {
            "actor_directory_collection",
            "actor_directory_record",
            "actor_set",
        }
    if kind == "actor_set" and requested_kind == "actor_directory_record":
        return bool(_actor_ids(quarantine_target) & _actor_ids(requested_target))
    if kind == "derived_projection" and requested_kind == "derived_projection":
        return (
            quarantine_target.get("projection_kind")
            == requested_target.get("projection_kind")
            and quarantine_target.get("projection_scope")
            == requested_target.get("projection_scope")
        )
    return False


class QuarantineGuard:
    """Load explicit current Quarantine state and enforce named effects."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.store = QuarantineStore(self.root)

    def active_records(self) -> tuple[PortiaRecord, ...]:
        collection = portia_root(self.root) / "quarantines"
        if not collection.exists():
            return ()
        if not collection.is_dir():
            raise PortiaCorruptionError("Portia quarantine collection is not a directory")
        records: list[PortiaRecord] = []
        for child in sorted(collection.iterdir(), key=lambda path: path.name):
            if not child.is_dir():
                raise PortiaCorruptionError(
                    f"unexpected artifact in quarantine collection: {child}"
                )
            try:
                state = self.store.load_current(child.name)
            except Exception as exc:
                raise PortiaRecoveryRequiredError(
                    f"quarantine series requires recovery: {child.name}"
                ) from exc
            if state.revision.to_dict().get("state") == "active":
                records.append(state.revision)
        return tuple(records)

    def require_allowed(self, requested_target: object, effect: str) -> None:
        """Raise when an active Quarantine explicitly blocks ``effect``."""
        for record in self.active_records():
            data = record.to_dict()
            effects = data.get("effects")
            if (
                isinstance(effects, list)
                and effect in effects
                and quarantine_applies(data.get("target"), requested_target)
            ):
                quarantine_id = data.get("quarantine_id")
                raise PortiaQuarantinedError(
                    f"active Quarantine {quarantine_id!r} blocks {effect}"
                )
