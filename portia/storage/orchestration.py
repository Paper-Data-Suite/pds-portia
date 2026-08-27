"""Bounded coordinated execution for already-journaled Portia operations.

This module executes only the filesystem mechanics that Issue #38 owns.  It does
not manufacture domain intent or silently edit Operation Journal snapshots.  A
caller first persists the accepted journal revision, then uses this coordinator
to acquire the journaled locks, stage exact candidates, and publish the bounded
write set.  Partial durable success is surfaced for explicit recovery; accepted
canonical bytes are never deleted to imitate rollback.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaLockError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.integrity import expected_target_relative_path
from portia.storage.io import read_bytes
from portia.storage.locks import HeldLock, LockStore, derive_lock_id
from portia.storage.paths import lock_path, workspace_relative
from portia.storage.staging import StagedArtifact, publish_staged, stage_bytes

FaultHook = Callable[[str, str | None], None]

_BYTE_ACTIONS = frozenset(
    {
        "exclusive_create",
        "revision_aware_replace",
        "atomic_pointer_replace",
    }
)


@dataclass(frozen=True, slots=True)
class PlannedWrite:
    """One exact byte-producing write step from an accepted journal snapshot."""

    step_id: str
    sequence: int
    phase: str
    action: str
    target: object
    destination_path: str
    precondition: Mapping[str, Any]
    intended_fingerprint: ContentFingerprint

    @property
    def expected_prior(self) -> ContentFingerprint | None:
        presence = self.precondition.get("presence")
        if presence == "must_be_absent":
            return None
        if presence != "must_match":
            raise PortiaCorruptionError(
                f"unsupported expected-state branch for {self.step_id}"
            )
        try:
            return ContentFingerprint.from_dict(self.precondition.get("fingerprint"))
        except ValueError as exc:
            raise PortiaCorruptionError(
                f"must_match step lacks an exact fingerprint: {self.step_id}"
            ) from exc


@dataclass(frozen=True, slots=True)
class OperationCommitResult:
    """Exact accepted results from one bounded canonical-gate commit attempt."""

    operation_id: str
    accepted_steps: tuple[str, ...]
    accepted_fingerprints: tuple[tuple[str, ContentFingerprint], ...]
    acquired_lock_ids: tuple[str, ...]


def _journal_data(journal: PortiaRecord | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(journal, PortiaRecord):
        if journal.contract != "operation_journal":
            raise PortiaCorruptionError("coordinated execution requires an Operation Journal")
        return journal.to_dict()
    return journal


def _as_int(value: object, description: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise PortiaCorruptionError(f"{description} must be a positive integer")
    return value


def _held_lock_id(held: HeldLock) -> str:
    lock_id = held.record.to_dict().get("lock_id")
    if not isinstance(lock_id, str):
        raise PortiaCorruptionError("acquired lock record is missing lock_id")
    return lock_id


def _compact_target_key(target: object) -> str:
    try:
        return json.dumps(
            target,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise PortiaCorruptionError("lock target is not deterministic JSON") from exc


def planned_writes(journal: PortiaRecord | Mapping[str, Any]) -> tuple[PlannedWrite, ...]:
    """Parse and validate the deterministic byte-producing write plan."""
    data = _journal_data(journal)
    raw_steps = data.get("write_set")
    if not isinstance(raw_steps, list):
        raise PortiaCorruptionError("operation journal write_set is not an array")

    all_sequences: list[int] = []
    all_ids: set[str] = set()
    writes: list[PlannedWrite] = []
    for index, raw in enumerate(raw_steps, start=1):
        if not isinstance(raw, dict):
            raise PortiaCorruptionError("operation write step is not an object")
        sequence = _as_int(raw.get("sequence"), "write-step sequence")
        if sequence != index:
            raise PortiaCorruptionError(
                "operation write-step sequences must be contiguous and agree with array order"
            )
        all_sequences.append(sequence)
        step_id = raw.get("step_id")
        if not isinstance(step_id, str) or step_id in all_ids:
            raise PortiaCorruptionError("operation write-step IDs must be unique strings")
        all_ids.add(step_id)

        action = raw.get("action")
        if action not in _BYTE_ACTIONS:
            continue
        phase = raw.get("phase")
        destination = raw.get("destination_path")
        precondition = raw.get("precondition")
        intended = raw.get("intended_result")
        if (
            not isinstance(action, str)
            or not isinstance(phase, str)
            or not isinstance(destination, str)
            or not isinstance(precondition, dict)
            or not isinstance(intended, dict)
        ):
            raise PortiaCorruptionError(
                f"byte-producing write step is incomplete: {step_id}"
            )
        try:
            intended_fp = ContentFingerprint.from_dict(intended.get("fingerprint"))
        except ValueError as exc:
            raise PortiaCorruptionError(
                f"write step lacks a valid intended fingerprint: {step_id}"
            ) from exc
        writes.append(
            PlannedWrite(
                step_id=step_id,
                sequence=sequence,
                phase=phase,
                action=action,
                target=raw.get("target"),
                destination_path=destination,
                precondition=precondition,
                intended_fingerprint=intended_fp,
            )
        )

    if all_sequences != list(range(1, len(all_sequences) + 1)):
        raise PortiaCorruptionError("operation write-step sequence is not contiguous")
    return tuple(writes)


def _actor_record_key(target: object) -> tuple[str, str, str]:
    if not isinstance(target, dict):
        return ("", "", "")
    reference = target.get("actor_directory_record_ref")
    if not isinstance(reference, dict):
        return ("", "", "")
    kind = reference.get("kind")
    kind_name = kind if isinstance(kind, str) else ""
    field_by_kind = {
        "actor": ("actor_ref", "actor_id"),
        "actor_contact_point": ("contact_point_ref", "contact_point_id"),
        "actor_student_relationship": ("relationship_ref", "relationship_id"),
        "actor_roster_student_collision": ("collision_ref", "collision_id"),
    }
    ref_field, id_field = field_by_kind.get(kind_name, ("", ""))
    nested = reference.get(ref_field) if ref_field else None
    if not isinstance(nested, dict):
        return (kind_name, "", "")

    actor_id = ""
    actor_ref = nested.get("actor_ref")
    if isinstance(actor_ref, dict):
        actor_id_value = actor_ref.get("actor_id")
        if isinstance(actor_id_value, str):
            actor_id = actor_id_value
    else:
        actor_id_value = nested.get("actor_id")
        if isinstance(actor_id_value, str):
            actor_id = actor_id_value

    local_id_value = nested.get(id_field) if id_field else None
    local_id = local_id_value if isinstance(local_id_value, str) else actor_id
    kind_rank = {
        "actor": "1",
        "actor_contact_point": "2",
        "actor_student_relationship": "3",
        "actor_roster_student_collision": "4",
    }.get(kind_name, "9")
    return (kind_rank, actor_id, local_id)


def _generic_lock_rank(scope: str) -> int:
    ranks = {
        "operation": 1,
        "workspace": 2,
        "class": 3,
        "work": 4,
        "record": 5,
        "derived_projection": 6,
    }
    try:
        return ranks[scope]
    except KeyError as exc:
        raise PortiaCorruptionError(f"unsupported generic lock scope: {scope}") from exc


def _actor_lock_sort_key(entry: Mapping[str, Any]) -> tuple[object, ...]:
    scope = entry.get("lock_scope")
    target = entry.get("protected_target")
    lock_id = entry.get("lock_id")
    if not isinstance(scope, str) or not isinstance(lock_id, str):
        raise PortiaCorruptionError("operation lock entry lacks scope or identity")
    if scope == "actor_directory_collection":
        return (1, "", "", "", lock_id)
    if scope == "actor_directory_record":
        kind_rank, actor_id, local_id = _actor_record_key(target)
        return (2, kind_rank, actor_id, local_id, lock_id)
    ranks = {
        "workspace": 3,
        "class": 4,
        "work": 5,
        "record": 6,
        "derived_projection": 7,
        "operation": 8,
    }
    if scope not in ranks:
        raise PortiaCorruptionError(f"unsupported Actor-aware lock scope: {scope}")
    return (ranks[scope], _compact_target_key(target), "", "", lock_id)


def validate_lock_plan(
    journal: PortiaRecord | Mapping[str, Any],
) -> tuple[Mapping[str, Any], ...]:
    """Validate contiguous lock sequencing and the accepted total acquisition order."""
    data = _journal_data(journal)
    raw_locks = data.get("lock_set")
    if not isinstance(raw_locks, list) or not raw_locks:
        raise PortiaCorruptionError("operation journal lock_set must be nonempty")
    entries: list[Mapping[str, Any]] = []
    seen_ids: set[str] = set()
    for index, raw in enumerate(raw_locks, start=1):
        if not isinstance(raw, dict):
            raise PortiaCorruptionError("operation lock entry is not an object")
        sequence = _as_int(raw.get("sequence"), "lock sequence")
        if sequence != index:
            raise PortiaCorruptionError(
                "operation lock sequences must be contiguous and agree with array order"
            )
        lock_id = raw.get("lock_id")
        if not isinstance(lock_id, str) or lock_id in seen_ids:
            raise PortiaCorruptionError("operation lock IDs must be unique strings")
        seen_ids.add(lock_id)
        entries.append(raw)

    actor_aware = any(
        entry.get("lock_scope") in {"actor_directory_collection", "actor_directory_record"}
        for entry in entries
    )
    if actor_aware:
        expected = sorted(entries, key=_actor_lock_sort_key)
    else:
        expected = sorted(
            entries,
            key=lambda entry: (
                _generic_lock_rank(str(entry.get("lock_scope"))),
                _compact_target_key(entry.get("protected_target")),
                str(entry.get("lock_id")),
            ),
        )
    if entries != expected:
        raise PortiaCorruptionError(
            "journal lock_set does not follow the accepted deterministic acquisition order"
        )
    return tuple(entries)


def _candidate_for_step(
    candidates: Mapping[str, bytes], step: PlannedWrite
) -> bytes:
    try:
        content = candidates[step.step_id]
    except KeyError as exc:
        raise PortiaConflictError(
            f"missing candidate bytes for operation step: {step.step_id}"
        ) from exc
    if not isinstance(content, bytes):
        raise PortiaConflictError(f"candidate is not bytes: {step.step_id}")
    if fingerprint_bytes(content) != step.intended_fingerprint:
        raise PortiaConflictError(
            f"candidate does not match journaled intended result: {step.step_id}"
        )
    return content


def stage_journaled_candidates(
    workspace_root: str | Path,
    journal: PortiaRecord | Mapping[str, Any],
    candidates: Mapping[str, bytes],
    *,
    fault_hook: FaultHook | None = None,
) -> tuple[StagedArtifact, ...]:
    """Stage every byte-producing canonical-gate candidate in journal sequence."""
    data = _journal_data(journal)
    operation_id = data.get("operation_id")
    if not isinstance(operation_id, str):
        raise PortiaCorruptionError("operation journal is missing operation_id")
    staged: list[StagedArtifact] = []
    for step in planned_writes(journal):
        if step.phase != "canonical_gate":
            continue
        expected_path = expected_target_relative_path(workspace_root, step.target)
        if expected_path is not None and expected_path != step.destination_path:
            raise PortiaConflictError(
                f"journal destination disagrees with canonical target path: {step.step_id}"
            )
        if fault_hook is not None:
            fault_hook("before_stage", step.step_id)
        artifact = stage_bytes(
            workspace_root,
            operation_id,
            step.step_id,
            step.destination_path,
            _candidate_for_step(candidates, step),
            intended=step.intended_fingerprint,
        )
        staged.append(artifact)
        if fault_hook is not None:
            fault_hook("after_stage", step.step_id)
    return tuple(staged)


def _validate_lock_record(
    root: Path,
    operation_id: str,
    entry: Mapping[str, Any],
    record: PortiaRecord,
) -> None:
    if record.contract != "operation_lock" or record.contract_version != "2":
        raise PortiaLockError("coordinated execution requires operation_lock@2")
    data = record.to_dict()
    scope = entry.get("lock_scope")
    target = entry.get("protected_target")
    expected_id = derive_lock_id(str(scope), target)
    expected_path = workspace_relative(root, lock_path(root, expected_id))
    if data.get("lock_id") != expected_id or entry.get("lock_id") != expected_id:
        raise PortiaLockError("journal and lock record do not use the canonical lock identity")
    if entry.get("lock_path") != expected_path:
        raise PortiaLockError("journal lock path disagrees with canonical lock identity")
    if data.get("lock_scope") != scope or data.get("protected_target") != target:
        raise PortiaLockError("lock record does not match the journaled protected target")
    owner = data.get("owning_operation")
    if not isinstance(owner, dict) or owner.get("operation_id") != operation_id:
        raise PortiaLockError("lock record is not owned by the executing operation")


def acquire_journaled_locks(
    workspace_root: str | Path,
    journal: PortiaRecord | Mapping[str, Any],
    lock_records: Mapping[str, PortiaRecord],
    *,
    fault_hook: FaultHook | None = None,
) -> tuple[HeldLock, ...]:
    """Acquire the exact accepted lock plan, releasing partial acquisition on conflict."""
    root = Path(workspace_root).resolve(strict=False)
    data = _journal_data(journal)
    operation_id = data.get("operation_id")
    if not isinstance(operation_id, str):
        raise PortiaCorruptionError("operation journal is missing operation_id")
    entries = validate_lock_plan(journal)
    store = LockStore(root)
    held: list[HeldLock] = []
    try:
        for entry in entries:
            lock_id = entry.get("lock_id")
            if not isinstance(lock_id, str) or lock_id not in lock_records:
                raise PortiaLockError("journaled lock record was not supplied")
            record = lock_records[lock_id]
            _validate_lock_record(root, operation_id, entry, record)
            if fault_hook is not None:
                fault_hook("before_lock_acquire", lock_id)
            held_lock = store.acquire(record)
            held.append(held_lock)
            if fault_hook is not None:
                fault_hook("after_lock_acquire", lock_id)
    except Exception:
        _release_all(store, tuple(held))
        raise
    return tuple(held)


def _release_all(store: LockStore, held: Sequence[HeldLock]) -> None:
    first_error: Exception | None = None
    for item in reversed(held):
        try:
            store.release(item)
        except Exception as exc:  # preserve best-effort release of unrelated exact locks
            if first_error is None:
                first_error = exc
    if first_error is not None:
        if isinstance(first_error, PortiaLockError):
            raise first_error
        raise PortiaLockError(
            "one or more exact operation locks could not be released"
        ) from first_error


def commit_journaled_candidates(
    workspace_root: str | Path,
    journal: PortiaRecord | Mapping[str, Any],
    staged: Sequence[StagedArtifact],
    lock_records: Mapping[str, PortiaRecord],
    *,
    fault_hook: FaultHook | None = None,
) -> OperationCommitResult:
    """Publish the bounded canonical-gate write set without fictitious rollback.

    A failure before the first accepted canonical step releases locks normally.  A
    failure after any canonical step is accepted preserves the locks and exact
    staged evidence and raises ``PortiaOperationPartialCommitError`` so explicit
    recovery can reconcile the durable state.
    """
    root = Path(workspace_root).resolve(strict=False)
    data = _journal_data(journal)
    operation_id = data.get("operation_id")
    state = data.get("state")
    if not isinstance(operation_id, str):
        raise PortiaCorruptionError("operation journal is missing operation_id")
    if state not in {"staged", "committing", "recovering"}:
        raise PortiaConflictError(
            "canonical publication requires a selected "
            "staged/committing/recovering journal revision"
        )

    raw_steps = data.get("write_set")
    if not isinstance(raw_steps, list):
        raise PortiaCorruptionError("operation journal write_set is not an array")
    unsupported = [
        raw.get("step_id")
        for raw in raw_steps
        if isinstance(raw, dict)
        and raw.get("phase") == "canonical_gate"
        and raw.get("action") not in _BYTE_ACTIONS
    ]
    if unsupported:
        raise PortiaConflictError(
            "canonical-gate write set contains actions that require a specialized "
            "persistence service: " + ", ".join(str(item) for item in unsupported)
        )
    steps = tuple(
        step for step in planned_writes(journal) if step.phase == "canonical_gate"
    )
    staged_by_id = {item.step_id: item for item in staged}
    if len(staged_by_id) != len(staged):
        raise PortiaConflictError("duplicate staged step identity")
    if tuple(step.step_id for step in steps) != tuple(item.step_id for item in staged):
        raise PortiaConflictError(
            "staged candidate order/set does not equal the journaled canonical-gate write set"
        )

    held = acquire_journaled_locks(root, journal, lock_records, fault_hook=fault_hook)
    store = LockStore(root)
    accepted: list[tuple[str, ContentFingerprint]] = []
    try:
        for step in steps:
            artifact = staged_by_id[step.step_id]
            if workspace_relative(root, artifact.destination_path) != step.destination_path:
                raise PortiaConflictError(
                    f"staged destination changed from journaled destination: {step.step_id}"
                )
            if artifact.fingerprint != step.intended_fingerprint:
                raise PortiaConflictError(
                    f"staged fingerprint differs from intended result: {step.step_id}"
                )
            if fault_hook is not None:
                fault_hook("before_publish", step.step_id)
            result = publish_staged(
                root,
                artifact,
                action=step.action,
                expected_prior=step.expected_prior,
            )
            # Re-read exact destination after publication; existence alone is not acceptance.
            if fingerprint_bytes(read_bytes(artifact.destination_path)) != result:
                raise PortiaCorruptionError(
                    f"accepted readback changed after publication: {step.step_id}"
                )
            accepted.append((step.step_id, result))
            if fault_hook is not None:
                fault_hook("after_publish", step.step_id)
    except Exception as exc:
        if accepted:
            raise PortiaOperationPartialCommitError(
                operation_id=operation_id,
                accepted_steps=tuple(step_id for step_id, _fp in accepted),
                held_lock_ids=tuple(_held_lock_id(item) for item in held),
            ) from exc
        _release_all(store, held)
        raise

    if fault_hook is not None:
        try:
            fault_hook("before_lock_release", None)
        except Exception as exc:
            raise PortiaOperationPartialCommitError(
                operation_id=operation_id,
                accepted_steps=tuple(step_id for step_id, _fp in accepted),
                held_lock_ids=tuple(_held_lock_id(item) for item in held),
            ) from exc
    try:
        _release_all(store, held)
    except Exception as exc:
        raise PortiaOperationPartialCommitError(
            operation_id=operation_id,
            accepted_steps=tuple(step_id for step_id, _fp in accepted),
            held_lock_ids=tuple(_held_lock_id(item) for item in held),
        ) from exc
    if fault_hook is not None:
        fault_hook("after_lock_release", None)

    return OperationCommitResult(
        operation_id=operation_id,
        accepted_steps=tuple(step_id for step_id, _fp in accepted),
        accepted_fingerprints=tuple(accepted),
        acquired_lock_ids=tuple(_held_lock_id(item) for item in held),
    )
