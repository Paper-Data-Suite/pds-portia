"""Deterministic persistence-level integrity evaluation for Portia durable state."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaPathError
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes
from portia.storage.paths import (
    actor_child_path,
    actor_record_path,
    resolve_workspace_relative,
    work_manifest_path,
    work_record_path,
    workspace_relative,
)
from portia.storage.staging import ensure_runtime_containment


@dataclass(frozen=True, slots=True, order=True)
class PersistenceFinding:
    """Privacy-minimized diagnostic about persisted operational evidence."""

    code: str
    relative_path: str
    detail: str


def _fingerprint(value: object) -> ContentFingerprint | None:
    if value is None:
        return None
    try:
        return ContentFingerprint.from_dict(value)
    except ValueError:
        return None


def _work_ref(value: object) -> ExactPortiaWorkRef | None:
    if not isinstance(value, dict):
        return None
    try:
        return ExactPortiaWorkRef(
            class_id=str(value["class_id"]),
            work_id=str(value["work_id"]),
            work_kind=str(value["work_kind"]),
            contract_version=str(value["contract_version"]),
            module_id=str(value.get("module_id", "portia")),
        )
    except (KeyError, ValueError, TypeError):
        return None


def expected_target_relative_path(root: str | Path, target: object) -> str | None:
    """Return an exact canonical path for target branches whose storage is #38-owned."""
    if not isinstance(target, dict):
        return None
    kind = target.get("kind")
    workspace = Path(root).resolve(strict=False)

    if kind == "work":
        work = _work_ref(target.get("work_ref"))
        if work is None:
            return None
        return workspace_relative(workspace, work_manifest_path(workspace, work))

    if kind == "work_record":
        composite = target.get("work_record_ref")
        if not isinstance(composite, dict):
            return None
        work = _work_ref(composite.get("work_ref"))
        record_ref = composite.get("record_ref")
        if work is None or not isinstance(record_ref, dict):
            return None
        record_kind = record_ref.get("record_kind")
        record_id = record_ref.get("record_id")
        if not isinstance(record_kind, str) or not isinstance(record_id, str):
            return None
        return workspace_relative(
            workspace,
            work_record_path(workspace, work, record_kind, record_id),
        )

    if kind == "actor_directory_record":
        reference = target.get("actor_directory_record_ref")
        if not isinstance(reference, dict):
            return None
        record_kind = reference.get("kind")
        if record_kind == "actor":
            actor_ref = reference.get("actor_ref")
            if not isinstance(actor_ref, dict):
                return None
            actor_id = actor_ref.get("actor_id")
            if not isinstance(actor_id, str):
                return None
            return workspace_relative(workspace, actor_record_path(workspace, actor_id))

        reference_field = {
            "actor_contact_point": "contact_point_ref",
            "actor_student_relationship": "relationship_ref",
            "actor_roster_student_collision": "collision_ref",
        }.get(str(record_kind))
        id_field = {
            "actor_contact_point": "contact_point_id",
            "actor_student_relationship": "relationship_id",
            "actor_roster_student_collision": "collision_id",
        }.get(str(record_kind))
        if reference_field is None or id_field is None:
            return None
        child_ref = reference.get(reference_field)
        if not isinstance(child_ref, dict):
            return None
        actor_ref = child_ref.get("actor_ref")
        if not isinstance(actor_ref, dict):
            return None
        actor_id = actor_ref.get("actor_id")
        record_id = child_ref.get(id_field)
        if not isinstance(actor_id, str) or not isinstance(record_id, str):
            return None
        return workspace_relative(
            workspace,
            actor_child_path(workspace, actor_id, str(record_kind), record_id),
        )

    return None


def validate_operation_durable_state(
    workspace_root: str | Path,
    journal: PortiaRecord,
) -> tuple[PersistenceFinding, ...]:
    """Reconcile durable/accepted journal evidence with exact filesystem bytes."""
    if journal.contract != "operation_journal" or journal.contract_version != "2":
        raise ValueError("journal must be operation_journal@2")
    root = Path(workspace_root).resolve(strict=False)
    data = journal.to_dict()
    findings: list[PersistenceFinding] = []

    write_set = data.get("write_set")
    if not isinstance(write_set, list):
        return (
            PersistenceFinding(
                "PORTIA.STORAGE.OPERATION_WRITE_SET_INVALID",
                "portia/operations",
                "operation journal write_set is unavailable",
            ),
        )

    for step in write_set:
        if not isinstance(step, dict):
            continue
        relative = step.get("destination_path")
        if not isinstance(relative, str):
            continue
        try:
            destination = resolve_workspace_relative(root, relative)
            ensure_runtime_containment(root, destination)
        except PortiaPathError:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.UNSAFE_OPERATION_PATH",
                    relative,
                    "journaled destination path is not safely contained in the workspace",
                )
            )
            continue

        expected_relative = expected_target_relative_path(root, step.get("target"))
        if expected_relative is not None and expected_relative != relative:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH",
                    relative,
                    "journaled target identity does not agree with destination path",
                )
            )

        if step.get("disposition") not in {"durable", "verified", "accepted"}:
            continue
        intended_result = step.get("intended_result")
        intended_fp = (
            _fingerprint(intended_result.get("fingerprint"))
            if isinstance(intended_result, dict)
            else None
        )
        observed_result = step.get("observed_result")
        observed_fp = (
            _fingerprint(observed_result.get("fingerprint"))
            if isinstance(observed_result, dict)
            else None
        )

        try:
            actual = fingerprint_bytes(read_bytes(destination))
        except Exception:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.DURABLE_RESULT_MISSING",
                    relative,
                    "journal reports durable state but destination bytes are unavailable",
                )
            )
            continue

        if intended_fp is not None and actual != intended_fp:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH",
                    relative,
                    "persisted bytes do not match the journaled intended fingerprint",
                )
            )
        if observed_fp is not None and actual != observed_fp:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.READBACK_RESULT_MISMATCH",
                    relative,
                    "persisted bytes do not match the journaled observed fingerprint",
                )
            )

    return tuple(sorted(findings))


def source_snapshot_digest(snapshot: PortiaRecord | dict[str, Any]) -> str:
    """Recompute the accepted ``portia_source_snapshot_v1`` logical digest."""
    data = snapshot.to_dict() if isinstance(snapshot, PortiaRecord) else dict(snapshot)
    digest_value = {
        "snapshot_algorithm": data.get("snapshot_algorithm"),
        "projection_kind": data.get("projection_kind"),
        "projection_scope": data.get("projection_scope"),
        "authorization_scope": data.get("authorization_scope"),
        "discovery_roots": data.get("discovery_roots"),
        "source_contracts": data.get("source_contracts"),
        "entries": data.get("entries"),
    }
    encoded = json.dumps(
        digest_value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_contract_sort_key(value: object) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (str(value.get("contract_name", "")), str(value.get("contract_version", "")))


def _source_entry_sort_key(value: object) -> tuple[str, str, str, str, int]:
    if not isinstance(value, dict):
        return ("", "", "", "", -1)
    length = value.get("byte_length")
    return (
        str(value.get("workspace_relative_path", "")),
        str(value.get("source_role", "")),
        str(value.get("contract_or_artifact_kind", "")),
        str(value.get("sha256_digest", "")),
        length if isinstance(length, int) and not isinstance(length, bool) else -1,
    )


def validate_source_snapshot(
    workspace_root: str | Path,
    snapshot: PortiaRecord,
) -> tuple[PersistenceFinding, ...]:
    """Verify Source Snapshot v1 logical digest, ordering, and exact source bytes."""
    if snapshot.contract != "source_snapshot" or snapshot.contract_version != "1":
        raise ValueError("snapshot must be source_snapshot@1")
    root = Path(workspace_root).resolve(strict=False)
    data = snapshot.to_dict()
    entries = data.get("entries")
    contracts = data.get("source_contracts")
    findings: list[PersistenceFinding] = []

    recorded_digest = data.get("source_snapshot_digest")
    if not isinstance(recorded_digest, str) or source_snapshot_digest(snapshot) != recorded_digest:
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_SNAPSHOT_DIGEST_MISMATCH",
                "portia/derived",
                "source snapshot logical digest does not match its recorded digest",
            )
        )

    if isinstance(contracts, list) and contracts != sorted(contracts, key=_source_contract_sort_key):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_CONTRACT_ORDER_INVALID",
                "portia/derived",
                "source contracts are not in deterministic order",
            )
        )

    if not isinstance(entries, list):
        return tuple(sorted(findings))
    if entries != sorted(entries, key=_source_entry_sort_key):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_ENTRY_ORDER_INVALID",
                "portia/derived",
                "source snapshot entries are not in deterministic order",
            )
        )
    paths = [
        entry.get("workspace_relative_path")
        for entry in entries
        if isinstance(entry, dict)
    ]
    if len(paths) != len(set(paths)):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_PATH_DUPLICATE",
                "portia/derived",
                "source snapshot contains duplicate workspace-relative paths",
            )
        )

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        relative = entry.get("workspace_relative_path")
        digest = entry.get("sha256_digest")
        byte_length = entry.get("byte_length")
        if not isinstance(relative, str):
            continue
        try:
            path = resolve_workspace_relative(root, relative)
            ensure_runtime_containment(root, path)
        except PortiaPathError:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_PATH_UNSAFE",
                    relative,
                    "source snapshot path is not safely contained in the workspace",
                )
            )
            continue
        try:
            actual = fingerprint_bytes(read_bytes(path))
        except Exception:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_SNAPSHOT_MISSING",
                    relative,
                    "source snapshot entry no longer resolves to persisted bytes",
                )
            )
            continue
        if actual.digest != digest or actual.byte_length != byte_length:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_SNAPSHOT_STALE",
                    relative,
                    "source bytes changed after the recorded source snapshot",
                )
            )
    return tuple(sorted(findings))
