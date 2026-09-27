"""Evidence-preserving recovery mutations for deliberate-export custody."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.deliberate_export_operations import (
    deliberate_export_immutable_plan,
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_committed_reference,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.deliberate_export_recovery import (
    DeliberateExportRecovery,
    DeliberateExportRecoveryAssessment,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create, read_bytes, read_json
from portia.storage.locks import HeldLock, LockStore
from portia.storage.paths import (
    lock_path,
    operation_revision_path,
    resolve_workspace_relative,
)
from portia.storage.recovery import OperationRecovery
from portia.storage.series import OperationJournalStore, SeriesState


@dataclass(frozen=True, slots=True)
class DeliberateExportRecoveryResult:
    """Result of one bounded deliberate-export recovery mutation."""

    action: str
    assessment: DeliberateExportRecoveryAssessment


def _current_export_journal(
    store: OperationJournalStore,
    operation_id: str,
) -> tuple[PortiaRecord, SeriesState]:
    current = store.load_current(operation_id)
    journal = current.revision
    data = journal.to_dict()
    if (
        journal.contract != "operation_journal"
        or journal.contract_version != "4"
        or data.get("operation_kind") != "generate_deliberate_export"
    ):
        raise PortiaConflictError(
            "recovery target is not an operation_journal@4 deliberate-export series"
        )
    return journal, current


def _provenance_path(root: Path, journal: PortiaRecord) -> Path:
    write_set = journal.to_dict().get("write_set")
    if not isinstance(write_set, list):
        raise PortiaCorruptionError("deliberate-export write_set is not an array")
    matches = [
        step
        for step in write_set
        if isinstance(step, dict)
        and step.get("representation_role") == "deliberate_export_provenance"
    ]
    if len(matches) != 1:
        raise PortiaCorruptionError(
            "deliberate-export write_set lacks one exact provenance step"
        )
    relative = matches[0].get("destination_path")
    if not isinstance(relative, str):
        raise PortiaCorruptionError("deliberate-export provenance path is invalid")
    return resolve_workspace_relative(root, relative)


def _validate_existing_provenance_bytes(
    root: Path,
    journal: PortiaRecord,
    export: PortiaRecord,
) -> None:
    expected = canonical_json_bytes(export.to_dict())
    actual = read_bytes(_provenance_path(root, journal))
    if actual != expected:
        raise PortiaConflictError(
            "durable deliberate-export provenance differs from the exact recovery candidate"
        )


def recover_deliberate_export_provenance(
    workspace_root: str | Path,
    operation_id: str,
    *,
    export: PortiaRecord,
) -> DeliberateExportRecoveryResult:
    """Create only missing exact provenance for an already-exact artifact."""
    root = Path(workspace_root).resolve(strict=False)
    store = OperationJournalStore(root)
    journal, _current = _current_export_journal(store, operation_id)
    validate_deliberate_export_candidate_reconciliation(journal, export)

    recovery = DeliberateExportRecovery(root)
    before = recovery.assess(operation_id)

    if before.disposition == "artifact_only":
        candidate = canonical_json_bytes(export.to_dict())
        exclusive_create(_provenance_path(root, journal), candidate)
        after = recovery.assess(operation_id)
        if after.disposition not in {
            "exact_both_committed_journal_missing",
            "committed",
            "completed",
        }:
            raise PortiaRecoveryRequiredError(
                "provenance became durable but export recovery did not reconcile"
            )
        return DeliberateExportRecoveryResult(
            "created_missing_provenance",
            after,
        )

    if before.disposition in {
        "exact_both_committed_journal_missing",
        "committed",
        "completed",
    }:
        _validate_existing_provenance_bytes(root, journal, export)
        return DeliberateExportRecoveryResult("exact_replay", before)

    raise PortiaRecoveryRequiredError(
        "deliberate-export provenance recovery is not safe for the observed state"
    )


def _build_committed_revision(
    journal: PortiaRecord,
    *,
    observed_at: str,
    committed_at: str,
) -> PortiaRecord:
    data = copy.deepcopy(journal.to_dict())
    current_revision = data.get("journal_revision")
    if (
        not isinstance(current_revision, int)
        or isinstance(current_revision, bool)
        or current_revision < 1
    ):
        raise PortiaCorruptionError(
            "deliberate-export journal has invalid current revision"
        )
    committed_revision = planned_deliberate_export_commit_revision(journal)
    if committed_revision != current_revision + 1:
        raise PortiaConflictError(
            "reserved deliberate-export committed revision is not the exact successor"
        )

    write_set = data.get("write_set")
    if not isinstance(write_set, list) or len(write_set) != 2:
        raise PortiaCorruptionError(
            "deliberate-export committed recovery requires exactly two write steps"
        )

    step_ids: list[str] = []
    for step in write_set:
        if not isinstance(step, dict):
            raise PortiaCorruptionError("deliberate-export write step is malformed")
        step_id = step.get("step_id")
        destination = step.get("destination_path")
        intended = step.get("intended_result")
        if (
            not isinstance(step_id, str)
            or not isinstance(destination, str)
            or not isinstance(intended, dict)
        ):
            raise PortiaCorruptionError(
                "deliberate-export write step lacks committed evidence"
            )
        fingerprint = intended.get("fingerprint")
        if not isinstance(fingerprint, dict):
            raise PortiaCorruptionError(
                "deliberate-export intended result lacks fingerprint"
            )
        step["disposition"] = "accepted"
        step["observed_result"] = {
            "kind": "present",
            "workspace_relative_path": destination,
            "fingerprint": copy.deepcopy(fingerprint),
            "observed_at": observed_at,
        }
        step_ids.append(step_id)

    data["journal_revision"] = committed_revision
    data["previous_journal_revision"] = current_revision
    data["state"] = "committed"
    data["commit_point"] = {
        "reached": True,
        "reached_at": committed_at,
    }

    partial = data.get("partial_state")
    if not isinstance(partial, dict):
        raise PortiaCorruptionError(
            "deliberate-export journal lacks partial_state"
        )
    partial["accepted_steps"] = list(step_ids)
    partial["verified_steps"] = list(step_ids)
    partial["durable_unverified_steps"] = []
    partial["indeterminate_steps"] = []
    partial["remaining_canonical_steps"] = []
    partial["remaining_post_commit_steps"] = []
    partial["durability_assessment"] = "confirmed"
    partial["recommended_disposition"] = None

    try:
        return parse_portia_record("operation_journal", "4", data)
    except Exception as exc:
        raise PortiaCorruptionError(
            "reconstructed deliberate-export committed revision is invalid"
        ) from exc


def _load_exact_orphan_committed_revision(
    root: Path,
    current: PortiaRecord,
    operation_id: str,
    committed_revision: int,
    export: PortiaRecord,
) -> PortiaRecord:
    path = operation_revision_path(root, operation_id, committed_revision)
    try:
        raw, _content, _fingerprint = read_json(path)
        orphan = parse_portia_record("operation_journal", "4", raw)
    except Exception as exc:
        raise PortiaRecoveryRequiredError(
            "reserved committed revision is durable but cannot be validated"
        ) from exc

    if deliberate_export_immutable_plan(orphan) != deliberate_export_immutable_plan(
        current
    ):
        raise PortiaRecoveryRequiredError(
            "durable committed revision changes deliberate-export immutable intent"
        )
    try:
        validate_deliberate_export_committed_reference(orphan, export)
    except Exception as exc:
        raise PortiaRecoveryRequiredError(
            "durable committed revision does not reconcile exact export provenance"
        ) from exc
    return orphan


def recover_deliberate_export_committed_revision(
    workspace_root: str | Path,
    operation_id: str,
    *,
    export: PortiaRecord,
    observed_at: str,
    committed_at: str,
) -> DeliberateExportRecoveryResult:
    """Create/select only the exact reserved committed journal revision."""
    root = Path(workspace_root).resolve(strict=False)
    store = OperationJournalStore(root)
    journal, current_state = _current_export_journal(store, operation_id)
    validate_deliberate_export_candidate_reconciliation(journal, export)
    _validate_existing_provenance_bytes(root, journal, export)

    recovery = DeliberateExportRecovery(root)
    before = recovery.assess(operation_id)
    series = store.inspect_recovery(operation_id)
    committed_revision = planned_deliberate_export_commit_revision(journal)

    if series.disposition == "orphan_linear_successor":
        if series.orphan_successors != (committed_revision,):
            raise PortiaRecoveryRequiredError(
                "operation has an unexpected orphan journal successor"
            )
        _load_exact_orphan_committed_revision(
            root,
            journal,
            operation_id,
            committed_revision,
            export,
        )
        selected = OperationRecovery(root).select_exact_orphan_successor(
            operation_id,
            expected_pointer=current_state.pointer_fingerprint,
        )
        validate_deliberate_export_committed_reference(selected.revision, export)
        after = recovery.assess(operation_id)
        if after.disposition != "committed":
            raise PortiaRecoveryRequiredError(
                "committed revision pointer recovery did not reconcile"
            )
        return DeliberateExportRecoveryResult(
            "selected_existing_committed_revision",
            after,
        )

    if before.disposition == "exact_both_committed_journal_missing":
        committed = _build_committed_revision(
            journal,
            observed_at=observed_at,
            committed_at=committed_at,
        )
        pointer_data = current_state.pointer.to_dict()
        pointer_data["journal_revision"] = committed_revision
        try:
            pointer = parse_portia_record(
                "operation_current_pointer",
                "1",
                pointer_data,
            )
        except Exception as exc:
            raise PortiaCorruptionError(
                "reconstructed deliberate-export current pointer is invalid"
            ) from exc

        appended = store.append(
            committed,
            pointer,
            expected_pointer=current_state.pointer_fingerprint,
        )
        validate_deliberate_export_committed_reference(appended.revision, export)
        after = recovery.assess(operation_id)
        if after.disposition != "committed":
            raise PortiaRecoveryRequiredError(
                "reconstructed committed revision did not reconcile"
            )
        return DeliberateExportRecoveryResult(
            "created_missing_committed_revision",
            after,
        )

    if before.disposition in {"committed", "completed"}:
        path = operation_revision_path(root, operation_id, committed_revision)
        try:
            exact_raw, _content, _fingerprint = read_json(path)
            exact_record = parse_portia_record(
                "operation_journal",
                "4",
                exact_raw,
            )
            validate_deliberate_export_committed_reference(exact_record, export)
        except Exception as exc:
            raise PortiaRecoveryRequiredError(
                "referenced deliberate-export committed revision is invalid"
            ) from exc
        return DeliberateExportRecoveryResult("exact_replay", before)

    raise PortiaRecoveryRequiredError(
        "committed-journal recovery is not safe for the observed export state"
    )



def _export_lock_id(journal: PortiaRecord) -> str:
    lock_set = journal.to_dict().get("lock_set")
    if not isinstance(lock_set, list) or len(lock_set) != 1:
        raise PortiaCorruptionError(
            "deliberate-export finalization requires one exact export lock"
        )
    entry = lock_set[0]
    if not isinstance(entry, dict):
        raise PortiaCorruptionError("deliberate-export lock entry is malformed")
    lock_id = entry.get("lock_id")
    if not isinstance(lock_id, str):
        raise PortiaCorruptionError("deliberate-export lock entry lacks lock_id")
    return lock_id


def _release_preserved_export_lock(
    root: Path,
    journal: PortiaRecord,
    lock: PortiaRecord | None,
) -> str:
    lock_id = _export_lock_id(journal)
    path = lock_path(root, lock_id)

    if lock is not None:
        validate_deliberate_export_lock_agreement(journal, lock)

    try:
        value, _content, fingerprint = read_json(path)
    except PortiaNotFoundError:
        return "already_absent"

    if lock is None:
        raise PortiaRecoveryRequiredError(
            "exact deliberate-export lock remains durable but no lock record was supplied"
        )
    if value != lock.to_dict():
        raise PortiaRecoveryRequiredError(
            "durable deliberate-export lock differs from supplied exact lock evidence"
        )

    LockStore(root).release(HeldLock(lock, path, fingerprint))
    return "released"


def _build_completed_revision(committed: PortiaRecord) -> PortiaRecord:
    data = copy.deepcopy(committed.to_dict())
    revision = data.get("journal_revision")
    if (
        not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 1
    ):
        raise PortiaCorruptionError(
            "committed deliberate-export journal has invalid revision"
        )
    reserved = planned_deliberate_export_commit_revision(committed)
    if revision != reserved:
        raise PortiaConflictError(
            "selected deliberate-export journal is not its reserved committed revision"
        )

    data["journal_revision"] = revision + 1
    data["previous_journal_revision"] = revision
    data["state"] = "completed"

    try:
        return parse_portia_record("operation_journal", "4", data)
    except Exception as exc:
        raise PortiaCorruptionError(
            "deliberate-export completed revision candidate is invalid"
        ) from exc


def _load_exact_completed_orphan(
    root: Path,
    committed: PortiaRecord,
    export: PortiaRecord,
    revision: int,
) -> PortiaRecord:
    operation_id = committed.to_dict().get("operation_id")
    if not isinstance(operation_id, str):
        raise PortiaCorruptionError(
            "committed deliberate-export journal lacks operation_id"
        )
    path = operation_revision_path(root, operation_id, revision)
    try:
        raw, _content, _fingerprint = read_json(path)
        completed = parse_portia_record("operation_journal", "4", raw)
    except Exception as exc:
        raise PortiaRecoveryRequiredError(
            "durable completed revision cannot be validated"
        ) from exc

    completed_data = completed.to_dict()
    committed_revision = committed.to_dict().get("journal_revision")
    if (
        completed_data.get("state") != "completed"
        or completed_data.get("journal_revision") != revision
        or completed_data.get("previous_journal_revision") != committed_revision
        or deliberate_export_immutable_plan(completed)
        != deliberate_export_immutable_plan(committed)
    ):
        raise PortiaRecoveryRequiredError(
            "durable completed revision does not exactly extend committed export state"
        )
    try:
        validate_deliberate_export_candidate_reconciliation(completed, export)
    except Exception as exc:
        raise PortiaRecoveryRequiredError(
            "durable completed revision does not reconcile export provenance"
        ) from exc
    return completed


def finalize_deliberate_export(
    workspace_root: str | Path,
    operation_id: str,
    *,
    export: PortiaRecord,
    lock: PortiaRecord | None = None,
) -> DeliberateExportRecoveryResult:
    """Release an exact preserved export lock and select completed state."""
    root = Path(workspace_root).resolve(strict=False)
    store = OperationJournalStore(root)
    journal, current_state = _current_export_journal(store, operation_id)
    recovery = DeliberateExportRecovery(root)
    before = recovery.assess(operation_id)

    if before.disposition == "completed":
        validate_deliberate_export_candidate_reconciliation(journal, export)
        _release_preserved_export_lock(root, journal, lock)
        return DeliberateExportRecoveryResult("exact_replay", before)

    if before.disposition != "committed":
        raise PortiaRecoveryRequiredError(
            "deliberate-export finalization requires exact committed state"
        )

    validate_deliberate_export_committed_reference(journal, export)
    committed_revision = planned_deliberate_export_commit_revision(journal)
    selected_revision = journal.to_dict().get("journal_revision")
    if selected_revision != committed_revision:
        raise PortiaRecoveryRequiredError(
            "selected deliberate-export journal is not the exact committed revision"
        )

    series = store.inspect_recovery(operation_id)
    completed_revision = committed_revision + 1

    _release_preserved_export_lock(root, journal, lock)

    if series.disposition == "orphan_linear_successor":
        if series.orphan_successors != (completed_revision,):
            raise PortiaRecoveryRequiredError(
                "operation has an unexpected post-commit orphan revision"
            )
        _load_exact_completed_orphan(
            root,
            journal,
            export,
            completed_revision,
        )
        selected = OperationRecovery(root).select_exact_orphan_successor(
            operation_id,
            expected_pointer=current_state.pointer_fingerprint,
        )
        if selected.revision.to_dict().get("state") != "completed":
            raise PortiaRecoveryRequiredError(
                "selected post-commit orphan is not completed state"
            )
        after = recovery.assess(operation_id)
        if after.disposition != "completed":
            raise PortiaRecoveryRequiredError(
                "completed pointer recovery did not reconcile"
            )
        return DeliberateExportRecoveryResult(
            "selected_existing_completed_revision",
            after,
        )

    if series.disposition != "current":
        raise PortiaRecoveryRequiredError(
            "operation journal series is not safe for completed finalization"
        )

    completed = _build_completed_revision(journal)
    pointer_data = current_state.pointer.to_dict()
    pointer_data["journal_revision"] = completed_revision
    try:
        pointer = parse_portia_record(
            "operation_current_pointer",
            "1",
            pointer_data,
        )
    except Exception as exc:
        raise PortiaCorruptionError(
            "deliberate-export completed current pointer is invalid"
        ) from exc

    store.append(
        completed,
        pointer,
        expected_pointer=current_state.pointer_fingerprint,
    )
    after = recovery.assess(operation_id)
    if after.disposition != "completed":
        raise PortiaRecoveryRequiredError(
            "completed deliberate-export revision did not reconcile"
        )
    return DeliberateExportRecoveryResult(
        "completed_export_operation",
        after,
    )
