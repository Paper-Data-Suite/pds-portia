"""Exact recovery for teacher-reference deliberate exports.

Issue #51 Slice 7 does not invent a second recovery system.  It classifies one
Issue #88 deliberate-export operation, validates exact preserved evidence, and
then delegates every mutation to the accepted Issue #88 recovery authorities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from portia.models import ExplicitOffsetTimestamp, PortiaRecord, parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.storage import (
    ContentFingerprint,
    OperationJournalStore,
    PortiaNotFoundError,
    PortiaStorageError,
    fingerprint_bytes,
)
from portia.storage.deliberate_export_operations import (
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.deliberate_export_recovery import (
    DeliberateExportRecovery,
    DeliberateExportRecoveryAssessment,
)
from portia.storage.deliberate_export_recovery_actions import (
    finalize_deliberate_export,
    recover_deliberate_export_committed_revision,
    recover_deliberate_export_provenance,
)
from portia.storage.io import read_json
from portia.storage.locks import validate_operation_lock_application
from portia.storage.paths import lock_path, resolve_workspace_relative
from portia.storage.staging import ensure_runtime_containment, staging_path_for

TeacherReferenceRecoveryCode = Literal[
    "recovered",
    "already_completed",
    "nothing_durable",
    "recovery_required",
]


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportRecoveryResult:
    """Teacher-facing translation of one bounded deliberate-export recovery."""

    code: TeacherReferenceRecoveryCode
    operation_id: str
    export_id: str | None
    message: str
    initial_disposition: str
    final_disposition: str
    durable_state_may_exist: bool

    def __post_init__(self) -> None:
        if not self.message:
            raise PortiaLocalValidationError(
                "teacher-reference recovery result requires a message"
            )
        if self.code in {"recovered", "already_completed"}:
            if self.final_disposition != "completed" or self.export_id is None:
                raise PortiaLocalValidationError(
                    "successful teacher-reference recovery must end completed"
                )


def _step_for_role(journal: PortiaRecord, role: str) -> dict[str, object]:
    raw = journal.to_dict().get("write_set")
    if not isinstance(raw, list):
        raise PortiaLocalValidationError(
            "teacher-reference recovery journal write_set is invalid"
        )
    matches: list[dict[str, object]] = []
    for step in raw:
        if not isinstance(step, dict) or step.get("representation_role") != role:
            continue
        candidate: dict[str, object] = {}
        for key, value in step.items():
            if isinstance(key, str):
                candidate[key] = value
        matches.append(candidate)
    if len(matches) != 1:
        raise PortiaLocalValidationError(
            f"teacher-reference recovery requires one exact {role} step"
        )
    return matches[0]


def _intended_fingerprint(step: dict[str, object]) -> ContentFingerprint:
    intended = step.get("intended_result")
    if not isinstance(intended, dict):
        raise PortiaLocalValidationError(
            "teacher-reference recovery step lacks intended_result"
        )
    try:
        return ContentFingerprint.from_dict(intended.get("fingerprint"))
    except ValueError as exc:
        raise PortiaLocalValidationError(
            "teacher-reference recovery step lacks exact fingerprint"
        ) from exc


class TeacherReferenceExportRecoveryService:
    """Recover one exact Issue #88 teacher-reference operation without repreparing."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).resolve(strict=False)
        self.store = OperationJournalStore(self.root)
        self.recovery = DeliberateExportRecovery(self.root)

    def _result(
        self,
        *,
        code: TeacherReferenceRecoveryCode,
        operation_id: str,
        initial: DeliberateExportRecoveryAssessment,
        final: DeliberateExportRecoveryAssessment,
        message: str,
        durable_state_may_exist: bool,
    ) -> TeacherReferenceExportRecoveryResult:
        return TeacherReferenceExportRecoveryResult(
            code=code,
            operation_id=operation_id,
            export_id=final.export_id or initial.export_id,
            message=message,
            initial_disposition=initial.disposition,
            final_disposition=final.disposition,
            durable_state_may_exist=durable_state_may_exist,
        )

    def _current_journal(self, operation_id: str) -> PortiaRecord:
        current = self.store.load_current(operation_id)
        journal = current.revision
        data = journal.to_dict()
        if (
            journal.contract != "operation_journal"
            or journal.contract_version != "4"
            or data.get("operation_kind") != "generate_deliberate_export"
        ):
            raise PortiaLocalValidationError(
                "teacher-reference recovery target is not a deliberate-export operation"
            )
        return journal

    def _load_exact_staged_provenance(
        self,
        operation_id: str,
        journal: PortiaRecord,
    ) -> PortiaRecord:
        step = _step_for_role(journal, "deliberate_export_provenance")
        step_id = step.get("step_id")
        destination = step.get("destination_path")
        if not isinstance(step_id, str) or not isinstance(destination, str):
            raise PortiaLocalValidationError(
                "teacher-reference provenance recovery step is incomplete"
            )
        staged_path = staging_path_for(
            self.root,
            operation_id,
            step_id,
            destination,
        )
        raw, content, observed = read_json(staged_path)
        intended = _intended_fingerprint(step)
        if observed != intended or fingerprint_bytes(content) != intended:
            raise PortiaLocalValidationError(
                "staged teacher-reference provenance fingerprint changed"
            )
        export = parse_portia_record("deliberate_export", "1", raw)
        if content != _canonical_export_bytes(export):
            raise PortiaLocalValidationError(
                "staged teacher-reference provenance is not the exact "
                "canonical candidate"
            )
        validate_deliberate_export_candidate_reconciliation(journal, export)
        return export

    def _load_exact_durable_provenance(self, journal: PortiaRecord) -> PortiaRecord:
        step = _step_for_role(journal, "deliberate_export_provenance")
        destination = step.get("destination_path")
        if not isinstance(destination, str):
            raise PortiaLocalValidationError(
                "teacher-reference provenance destination is invalid"
            )
        path = resolve_workspace_relative(self.root, destination)
        ensure_runtime_containment(self.root, path)
        raw, content, observed = read_json(path)
        intended = _intended_fingerprint(step)
        if observed != intended or fingerprint_bytes(content) != intended:
            raise PortiaLocalValidationError(
                "durable teacher-reference provenance differs from journaled intent"
            )
        export = parse_portia_record("deliberate_export", "1", raw)
        if content != _canonical_export_bytes(export):
            raise PortiaLocalValidationError(
                "durable teacher-reference provenance is not canonical"
            )
        validate_deliberate_export_candidate_reconciliation(journal, export)
        return export

    def _load_optional_exact_lock(self, journal: PortiaRecord) -> PortiaRecord | None:
        raw_locks = journal.to_dict().get("lock_set")
        if not isinstance(raw_locks, list) or len(raw_locks) != 1:
            raise PortiaLocalValidationError(
                "teacher-reference recovery requires one exact export lock"
            )
        entry = raw_locks[0]
        if not isinstance(entry, dict):
            raise PortiaLocalValidationError(
                "teacher-reference recovery lock entry is invalid"
            )
        lock_id = entry.get("lock_id")
        if not isinstance(lock_id, str):
            raise PortiaLocalValidationError(
                "teacher-reference recovery lock identity is missing"
            )
        path = lock_path(self.root, lock_id)
        ensure_runtime_containment(self.root, path)
        try:
            raw, _content, _fingerprint = read_json(path)
        except PortiaNotFoundError:
            return None
        lock = parse_portia_record("operation_lock", "3", raw)
        validate_operation_lock_application(lock)
        validate_deliberate_export_lock_agreement(journal, lock)
        return lock

    def recover(
        self,
        operation_id: str,
        *,
        observed_at: str,
        committed_at: str,
    ) -> TeacherReferenceExportRecoveryResult:
        """Advance only exact recoverable Issue #88 states to completed."""

        ExplicitOffsetTimestamp(observed_at)
        ExplicitOffsetTimestamp(committed_at)
        initial = self.recovery.assess(operation_id)
        if initial.disposition == "nothing_durable":
            return self._result(
                code="nothing_durable",
                operation_id=operation_id,
                initial=initial,
                final=initial,
                message=(
                    "No final teacher-reference artifact is durable for this "
                    "operation; "
                    "no provenance was manufactured during recovery."
                ),
                durable_state_may_exist=False,
            )
        if initial.disposition in {
            "indeterminate",
            "artifact_mismatch",
            "provenance_only",
            "artifact_provenance_mismatch",
        }:
            return self._result(
                code="recovery_required",
                operation_id=operation_id,
                initial=initial,
                final=initial,
                message=(
                    "Teacher-reference export evidence is incomplete or contradictory; "
                    "technical recovery is required."
                ),
                durable_state_may_exist=True,
            )

        try:
            journal = self._current_journal(operation_id)
            if initial.disposition == "artifact_only":
                export = self._load_exact_staged_provenance(operation_id, journal)
                recover_deliberate_export_provenance(
                    self.root,
                    operation_id,
                    export=export,
                )
            else:
                export = self._load_exact_durable_provenance(journal)

            middle = self.recovery.assess(operation_id)
            if middle.disposition == "exact_both_committed_journal_missing":
                recover_deliberate_export_committed_revision(
                    self.root,
                    operation_id,
                    export=export,
                    observed_at=observed_at,
                    committed_at=committed_at,
                )
                middle = self.recovery.assess(operation_id)

            if middle.disposition in {"committed", "completed"}:
                current_journal = self._current_journal(operation_id)
                lock = self._load_optional_exact_lock(current_journal)
                finalize_deliberate_export(
                    self.root,
                    operation_id,
                    export=export,
                    lock=lock,
                )
            final = self.recovery.assess(operation_id)
            if final.disposition != "completed":
                return self._result(
                    code="recovery_required",
                    operation_id=operation_id,
                    initial=initial,
                    final=final,
                    message=(
                        "Teacher-reference recovery did not reconcile to exact "
                        "completed state."
                    ),
                    durable_state_may_exist=True,
                )
            return self._result(
                code=(
                    "already_completed"
                    if initial.disposition == "completed"
                    else "recovered"
                ),
                operation_id=operation_id,
                initial=initial,
                final=final,
                message=(
                    "Teacher-reference export was already complete."
                    if initial.disposition == "completed"
                    else (
                        "Teacher-reference export recovery completed using exact "
                        "preserved evidence."
                    )
                ),
                durable_state_may_exist=True,
            )
        except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError):
            final = self.recovery.assess(operation_id)
            return self._result(
                code="recovery_required",
                operation_id=operation_id,
                initial=initial,
                final=final,
                message=(
                    "Exact teacher-reference recovery evidence is missing or "
                    "contradictory; "
                    "technical recovery is required."
                ),
                durable_state_may_exist=True,
            )


def _canonical_export_bytes(export: PortiaRecord) -> bytes:
    from portia.storage.fingerprint import canonical_json_bytes

    return canonical_json_bytes(export.to_dict())


__all__ = [
    "TeacherReferenceExportRecoveryResult",
    "TeacherReferenceExportRecoveryService",
    "TeacherReferenceRecoveryCode",
]
