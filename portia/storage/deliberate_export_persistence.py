"""Exact persistence execution for one deliberate-export operation.

This module is the Issue #88 execution boundary. It binds already-rendered
artifact bytes and an already-authoritative deliberate_export@1 provenance
record to one accepted operation_journal@4 plan, stages those exact candidates,
acquires the exact operation_lock@3 export lock, and publishes artifact then
provenance with the generic exact-byte coordinator.

It does not render exports, select sources, decide disclosure policy, author
provenance, advance journal revisions, or perform recovery mutation.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from portia.models import PortiaRecord
from portia.storage.deliberate_export_operations import (
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.orchestration import (
    FaultHook,
    OperationCommitResult,
    commit_journaled_candidates,
    stage_journaled_candidates,
)
from portia.storage.staging import StagedArtifact


def _require_export_records(
    journal: PortiaRecord,
    export: PortiaRecord,
) -> None:
    if journal.contract != "operation_journal" or journal.contract_version != "4":
        raise PortiaCorruptionError(
            "deliberate-export persistence requires operation_journal@4"
        )
    if export.contract != "deliberate_export" or export.contract_version != "1":
        raise PortiaCorruptionError(
            "deliberate-export persistence requires deliberate_export@1 provenance"
        )
    validate_deliberate_export_candidate_reconciliation(journal, export)


def _candidate_bytes(
    journal: PortiaRecord,
    artifact_bytes: bytes,
    export: PortiaRecord,
) -> dict[str, bytes]:
    if not isinstance(artifact_bytes, bytes):
        raise PortiaConflictError("deliberate-export artifact candidate must be bytes")
    data = journal.to_dict()
    write_set = data.get("write_set")
    if not isinstance(write_set, list) or len(write_set) != 2:
        raise PortiaCorruptionError(
            "deliberate-export persistence requires exactly two final writes"
        )
    artifact_step = write_set[0]
    provenance_step = write_set[1]
    if not isinstance(artifact_step, dict) or not isinstance(provenance_step, dict):
        raise PortiaCorruptionError("deliberate-export write plan is malformed")
    artifact_id = artifact_step.get("step_id")
    provenance_id = provenance_step.get("step_id")
    if not isinstance(artifact_id, str) or not isinstance(provenance_id, str):
        raise PortiaCorruptionError("deliberate-export write identities are incomplete")
    return {
        artifact_id: artifact_bytes,
        provenance_id: canonical_json_bytes(export.to_dict()),
    }


def stage_deliberate_export_candidates(
    workspace_root: str | Path,
    journal: PortiaRecord,
    *,
    artifact_bytes: bytes,
    export: PortiaRecord,
    fault_hook: FaultHook | None = None,
) -> tuple[StagedArtifact, ...]:
    """Stage the exact artifact and immutable provenance candidates."""
    _require_export_records(journal, export)
    candidates = _candidate_bytes(journal, artifact_bytes, export)
    return stage_journaled_candidates(
        workspace_root,
        journal,
        candidates,
        fault_hook=fault_hook,
    )


def commit_deliberate_export_candidates(
    workspace_root: str | Path,
    journal: PortiaRecord,
    staged: Sequence[StagedArtifact],
    *,
    artifact_bytes: bytes,
    export: PortiaRecord,
    lock: PortiaRecord,
    fault_hook: FaultHook | None = None,
) -> OperationCommitResult:
    """Publish artifact then provenance under one exact v3 export lock."""
    _require_export_records(journal, export)
    validate_deliberate_export_lock_agreement(journal, lock)

    candidates = _candidate_bytes(journal, artifact_bytes, export)
    ordered_candidates = tuple(candidates.values())
    if len(staged) != 2:
        raise PortiaConflictError(
            "deliberate-export commit requires exactly two staged candidates"
        )
    for staged_item, candidate in zip(staged, ordered_candidates, strict=True):
        if staged_item.fingerprint != fingerprint_bytes(candidate):
            raise PortiaConflictError(
                "staged deliberate-export candidate differs from revalidated bytes"
            )

    lock_id = lock.to_dict().get("lock_id")
    if not isinstance(lock_id, str):
        raise PortiaCorruptionError("deliberate-export lock lacks lock_id")

    return commit_journaled_candidates(
        workspace_root,
        journal,
        staged,
        {lock_id: lock},
        fault_hook=fault_hook,
        _allow_deliberate_export_execution=True,
    )
