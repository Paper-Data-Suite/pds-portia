"""Bounded workflow recovery over durable Operation Journal evidence."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.integrity import OperationStepEvidence, PersistenceFinding
from portia.storage.io import read_bytes, read_json
from portia.storage.locks import HeldLock, LockStore
from portia.storage.orchestration import FaultHook
from portia.storage.paths import (
    lock_path,
    resolve_workspace_relative,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.recovery import OperationRecovery, OperationRecoveryAssessment
from portia.storage.series import (
    OperationJournalStore,
    RecoveryObservation,
    SeriesState,
)
from portia.storage.staging import (
    StagedArtifact,
    cleanup_staged,
    publish_staged,
    staging_path_for,
)
from portia.workflows.errors import WorkflowPrerequisiteError


@dataclass(frozen=True, slots=True)
class RecoveryWorkflowAssessment:
    """Application-level view of one exact operation recovery assessment."""

    operation_id: str
    state: str | None
    disposition: str
    series: RecoveryObservation
    findings: tuple[PersistenceFinding, ...]
    step_evidence: tuple[OperationStepEvidence, ...] = ()


def _workflow_assessment(
    assessment: OperationRecoveryAssessment,
) -> RecoveryWorkflowAssessment:
    return RecoveryWorkflowAssessment(
        operation_id=assessment.operation_id,
        state=assessment.state,
        disposition=assessment.disposition,
        series=assessment.series,
        findings=assessment.findings,
        step_evidence=assessment.step_evidence,
    )


class RecoveryWorkflowService:
    """Explicit recovery surface over the accepted #38 storage authority."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        quarantine: QuarantineGuard | None = None,
    ) -> None:
        self.root = Path(workspace_root)
        self._recovery = OperationRecovery(self.root)
        self._journals = OperationJournalStore(self.root)
        self.quarantine = quarantine or QuarantineGuard(self.root)

    def assess(self, operation_id: str) -> RecoveryWorkflowAssessment:
        """Inspect one operation without mutating durable recovery state."""
        return _workflow_assessment(self._recovery.assess(operation_id))

    def restore_exact_orphan_pointer(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
    ) -> RecoveryWorkflowAssessment:
        """Select the one exact linear orphan successor and verify the result.

        This is intentionally narrower than generic resume/repair.  The storage
        recovery authority remains responsible for predecessor, intent, pointer,
        and durable-byte validation.  Ambiguous or branched state stays fail-closed.
        """
        assessment = self.assess(operation_id)
        if assessment.disposition != "restore_pointer_candidate":
            raise WorkflowPrerequisiteError(
                "operation is not a restore_pointer_candidate"
            )
        self._recovery.select_exact_orphan_successor(
            operation_id,
            expected_pointer=expected_pointer,
        )
        return self.assess(operation_id)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _pointer(operation_id: str, revision: int) -> PortiaRecord:
        return parse_portia_record(
            "operation_current_pointer",
            "1",
            {
                "schema_version": "1",
                "record_type": "operation_current_pointer",
                "module_id": "portia",
                "operation_id": operation_id,
                "journal_revision": revision,
            },
        )

    def _require_completion_allowed(self, data: Mapping[str, object]) -> None:
        operation_id = data.get("operation_id")
        if not isinstance(operation_id, str):
            raise PortiaCorruptionError("selected journal has no exact operation ID")
        targets: list[object] = [
            {
                "kind": "operation",
                "operation_ref": {"operation_id": operation_id},
            },
            data.get("primary_target"),
        ]
        affected = data.get("affected_targets")
        if isinstance(affected, list):
            targets.extend(affected)
        for target in targets:
            if isinstance(target, dict):
                self.quarantine.require_allowed(target, "block_operation_completion")

        # Integrity governance remains explicit by construction, matching the
        # Slice 31 compatibility boundary.
        from portia.workflows.integrity import IntegrityGuard

        if isinstance(self.quarantine, IntegrityGuard):
            self.quarantine.integrity.require_operation_completion(operation_id)

    def _require_mutation_allowed(self, target: object) -> None:
        if not isinstance(target, dict):
            raise PortiaCorruptionError("journaled recovery target is malformed")
        kind = target.get("kind")
        if kind in {
            "actor_directory_record",
            "actor_set",
            "actor_directory_collection",
        }:
            self.quarantine.require_allowed(target, "block_actor_directory_writes")
        elif kind in {"work", "work_record", "class", "workspace"}:
            self.quarantine.require_allowed(target, "block_work_writes")

    def _load_held_locks(
        self,
        operation_id: str,
        data: Mapping[str, object],
    ) -> tuple[HeldLock, ...]:
        raw_locks = data.get("lock_set")
        if not isinstance(raw_locks, list):
            raise PortiaCorruptionError("recovery journal lock set is unavailable")
        held: list[HeldLock] = []
        for entry in raw_locks:
            if not isinstance(entry, dict):
                raise PortiaCorruptionError("recovery journal lock entry is malformed")
            if entry.get("disposition") == "released":
                continue
            if entry.get("disposition") != "acquired":
                raise WorkflowPrerequisiteError(
                    "recovery cannot infer ownership of a lock that was not journaled acquired"
                )
            lock_id = entry.get("lock_id")
            relative = entry.get("lock_path")
            if not isinstance(lock_id, str) or not isinstance(relative, str):
                raise PortiaCorruptionError("recovery lock identity is malformed")
            path = resolve_workspace_relative(self.root, relative)
            if path != lock_path(self.root, lock_id):
                raise PortiaCorruptionError("recovery lock path disagrees with lock identity")
            raw, _content, observed = read_json(path)
            expected = ContentFingerprint.from_dict(entry.get("fingerprint"))
            if observed != expected:
                raise PortiaConflictError("recovery lock changed after journal observation")
            try:
                record = parse_portia_record("operation_lock", "2", raw)
            except Exception as exc:
                raise PortiaCorruptionError("recovery lock is not operation_lock@2") from exc
            owner = record.to_dict().get("owning_operation")
            if not isinstance(owner, dict) or owner.get("operation_id") != operation_id:
                raise PortiaConflictError("recovery lock belongs to another operation")
            held.append(HeldLock(record, path, observed))
        return tuple(held)

    def _load_staged(
        self,
        operation_id: str,
        data: Mapping[str, object],
    ) -> dict[str, StagedArtifact]:
        raw_artifacts = data.get("staged_artifacts")
        if not isinstance(raw_artifacts, list):
            raise PortiaCorruptionError("recovery staged evidence is unavailable")
        artifacts: dict[str, StagedArtifact] = {}
        for raw in raw_artifacts:
            if not isinstance(raw, dict):
                raise PortiaCorruptionError("recovery staged evidence is malformed")
            step_id = raw.get("step_id")
            staging_relative = raw.get("staging_path")
            destination_relative = raw.get("destination_path")
            if not all(
                isinstance(value, str)
                for value in (step_id, staging_relative, destination_relative)
            ):
                raise PortiaCorruptionError("recovery staged identity is malformed")
            assert isinstance(step_id, str)
            assert isinstance(staging_relative, str)
            assert isinstance(destination_relative, str)
            if step_id in artifacts:
                raise PortiaCorruptionError("duplicate recovery staged step identity")
            staging = resolve_workspace_relative(self.root, staging_relative)
            destination = resolve_workspace_relative(self.root, destination_relative)
            expected_staging = staging_path_for(
                self.root,
                operation_id,
                step_id,
                destination_relative,
            )
            if staging != expected_staging:
                raise PortiaConflictError("staged path is not owned by the exact operation step")
            expected = ContentFingerprint.from_dict(raw.get("fingerprint"))
            observed = fingerprint_bytes(read_bytes(staging))
            if observed != expected:
                raise PortiaConflictError("staged candidate changed after journal observation")
            artifacts[step_id] = StagedArtifact(
                operation_id,
                step_id,
                staging,
                destination,
                observed,
            )
        return artifacts

    def _append_state(
        self,
        current: SeriesState,
        data: dict[str, object],
        *,
        state: str,
    ) -> SeriesState:
        operation_id = data.get("operation_id")
        current_revision = current.revision.to_dict().get("journal_revision")
        if not isinstance(operation_id, str) or not isinstance(current_revision, int):
            raise PortiaCorruptionError("selected recovery journal identity is malformed")
        data["journal_revision"] = current_revision + 1
        data["previous_journal_revision"] = current_revision
        data["state"] = state
        data["updated_at"] = self._now()
        try:
            revision = parse_portia_record(
                "operation_journal",
                current.revision.contract_version,
                data,
            )
        except Exception as exc:
            raise PortiaCorruptionError("recovery journal successor is invalid") from exc
        return self._journals.append(
            revision,
            self._pointer(operation_id, current_revision + 1),
            expected_pointer=current.pointer_fingerprint,
        )

    def _require_current_unchanged(self, expected: SeriesState) -> None:
        operation_id = expected.revision.to_dict().get("operation_id")
        if not isinstance(operation_id, str):
            raise PortiaCorruptionError("selected recovery journal has no operation ID")
        observed = self._journals.load_current(operation_id)
        if (
            observed.pointer_fingerprint != expected.pointer_fingerprint
            or observed.revision_fingerprint != expected.revision_fingerprint
        ):
            raise PortiaConflictError("operation current selection changed during recovery")

    @staticmethod
    def _require_locks_unchanged(held: tuple[HeldLock, ...]) -> None:
        for item in held:
            value, _content, fingerprint = read_json(item.path)
            if fingerprint != item.fingerprint or value != item.record.to_dict():
                raise PortiaConflictError("operation lock changed during recovery")

    def _finalize_committed(
        self,
        current: SeriesState,
        *,
        fault_hook: FaultHook | None = None,
    ) -> RecoveryWorkflowAssessment:
        data = current.revision.to_dict()
        operation_id = data.get("operation_id")
        if not isinstance(operation_id, str) or data.get("state") != "committed":
            raise WorkflowPrerequisiteError("operation is not committed post-commit work")
        self._require_completion_allowed(data)
        assessment = self.assess(operation_id)
        if assessment.disposition != "finalize_post_commit" or assessment.findings:
            raise WorkflowPrerequisiteError(
                "committed operation does not have exact safe finalization evidence"
            )
        if any(
            item.disposition != "accepted" for item in assessment.step_evidence
        ):
            raise WorkflowPrerequisiteError(
                "committed operation canonical gates are not exactly accepted"
            )
        held = self._load_held_locks(operation_id, data)
        if fault_hook is not None:
            fault_hook("before_recovery_lock_release", None)
        lock_store = LockStore(self.root)
        for item in reversed(held):
            lock_store.release(item)
        if fault_hook is not None:
            fault_hook("after_recovery_lock_release", None)

        completed: dict[str, Any] = deepcopy(data)
        timestamp = self._now()
        raw_locks = completed.get("lock_set")
        if not isinstance(raw_locks, list):
            raise PortiaCorruptionError("committed lock set is malformed")
        for entry in raw_locks:
            if isinstance(entry, dict) and entry.get("disposition") == "acquired":
                entry["disposition"] = "released"
                entry["released_at"] = timestamp
        completed["staged_artifacts"] = []
        partial = completed.get("partial_state")
        if not isinstance(partial, dict):
            raise PortiaCorruptionError("committed partial state is malformed")
        partial["held_or_possible_locks"] = []
        partial["remaining_post_commit_steps"] = []
        partial["recommended_disposition"] = None
        if fault_hook is not None:
            fault_hook("before_recovery_completion_journal", None)
        self._append_state(current, completed, state="completed")
        if fault_hook is not None:
            fault_hook("after_recovery_completion_journal", None)

        for artifact in self._load_staged(operation_id, data).values():
            cleanup_staged(self.root, artifact)
        return self.assess(operation_id)

    def _resume(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
        require_all_durable: bool,
        fault_hook: FaultHook | None,
    ) -> RecoveryWorkflowAssessment:
        assessment = self.assess(operation_id)
        if assessment.disposition == "terminal_consistent":
            return assessment
        if assessment.disposition == "finalize_post_commit":
            current = self._journals.load_current(operation_id)
            if current.pointer_fingerprint != expected_pointer:
                raise PortiaConflictError("operation current pointer changed before recovery")
            return self._finalize_committed(current, fault_hook=fault_hook)
        if assessment.disposition != "resume" or assessment.findings:
            raise WorkflowPrerequisiteError("operation does not have exact resumable evidence")
        current = self._journals.load_current(operation_id)
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError("operation current pointer changed before recovery")
        data: dict[str, Any] = current.revision.to_dict()
        if data.get("state") != "recovering":
            raise WorkflowPrerequisiteError(
                "generic recovery execution requires exact recovering journal evidence"
            )
        recovery_plan = data.get("recovery_plan")
        required_disposition = (
            "reconcile_as_complete" if require_all_durable else "resume"
        )
        if not isinstance(recovery_plan, list) or required_disposition not in recovery_plan:
            raise WorkflowPrerequisiteError(
                f"journal recovery plan does not permit {required_disposition}"
            )
        by_step = {item.step_id: item for item in assessment.step_evidence}
        raw_steps = data.get("write_set")
        if not isinstance(raw_steps, list):
            raise PortiaCorruptionError("recovering write set is malformed")
        staged = self._load_staged(operation_id, data)
        held = self._load_held_locks(operation_id, data)
        if not held:
            raise WorkflowPrerequisiteError(
                "missing locks are not proof that interrupted recovery is safe"
            )

        planned_publications: list[
            tuple[dict[str, Any], StagedArtifact, ContentFingerprint | None]
        ] = []
        accepted_fingerprints: dict[str, ContentFingerprint] = {}
        for raw in raw_steps:
            if not isinstance(raw, dict) or raw.get("phase") != "canonical_gate":
                continue
            step_id = raw.get("step_id")
            if not isinstance(step_id, str) or step_id not in by_step:
                raise PortiaCorruptionError("recovering step identity is incomplete")
            evidence = by_step[step_id]
            intended_raw = raw.get("intended_result")
            if not isinstance(intended_raw, dict):
                raise PortiaCorruptionError("recovering intended result is malformed")
            intended = ContentFingerprint.from_dict(intended_raw.get("fingerprint"))
            if evidence.disposition in {"accepted", "verified", "durable_unverified"}:
                if evidence.fingerprint != intended:
                    raise PortiaConflictError("durable recovery result contradicts intent")
                accepted_fingerprints[step_id] = intended
                continue
            if require_all_durable:
                raise WorkflowPrerequisiteError(
                    "reconcile_as_complete requires every canonical result to be durable"
                )
            if evidence.disposition != "not_written":
                raise WorkflowPrerequisiteError(
                    "recovery cannot select an indeterminate canonical result"
                )
            artifact = staged.get(step_id)
            if artifact is None or artifact.fingerprint != intended:
                raise WorkflowPrerequisiteError(
                    "remaining recovery step lacks its exact staged candidate"
                )
            precondition = raw.get("precondition")
            expected_prior = None
            if isinstance(precondition, dict) and precondition.get("presence") == "must_match":
                expected_prior = ContentFingerprint.from_dict(precondition.get("fingerprint"))
            self._require_mutation_allowed(raw.get("target"))
            planned_publications.append((cast(dict[str, Any], raw), artifact, expected_prior))

        for raw, artifact, expected_prior in planned_publications:
            step_id = str(raw["step_id"])
            # Recheck immediately before the guarded canonical mutation.
            self._require_current_unchanged(current)
            self._require_locks_unchanged(held)
            self._require_mutation_allowed(raw.get("target"))
            if fault_hook is not None:
                fault_hook("before_recovery_publish", step_id)
            accepted_fingerprints[step_id] = publish_staged(
                self.root,
                artifact,
                action=str(raw.get("action")),
                expected_prior=expected_prior,
            )
            if fault_hook is not None:
                fault_hook("after_recovery_publish", step_id)

        self._require_current_unchanged(current)
        self._require_locks_unchanged(held)
        for raw in raw_steps:
            if not isinstance(raw, dict) or raw.get("phase") != "canonical_gate":
                continue
            step_id = raw.get("step_id")
            destination = raw.get("destination_path")
            intended_raw = raw.get("intended_result")
            if (
                not isinstance(step_id, str)
                or not isinstance(destination, str)
                or not isinstance(intended_raw, dict)
            ):
                raise PortiaCorruptionError("recovering write identity is malformed")
            intended = ContentFingerprint.from_dict(intended_raw.get("fingerprint"))
            actual = fingerprint_bytes(
                read_bytes(resolve_workspace_relative(self.root, destination))
            )
            if actual != intended:
                raise PortiaConflictError(
                    f"canonical result changed before recovery journal publication: {step_id}"
                )

        committed: dict[str, Any] = deepcopy(data)
        timestamp = self._now()
        committed_steps = committed.get("write_set")
        if not isinstance(committed_steps, list):
            raise PortiaCorruptionError("recovering write set is malformed")
        step_ids: list[str] = []
        for raw in committed_steps:
            if not isinstance(raw, dict) or raw.get("phase") != "canonical_gate":
                continue
            step_id = raw.get("step_id")
            destination = raw.get("destination_path")
            if not isinstance(step_id, str) or not isinstance(destination, str):
                raise PortiaCorruptionError("recovering write identity is malformed")
            fingerprint = accepted_fingerprints.get(step_id)
            if fingerprint is None:
                raise PortiaRecoveryRequiredError(
                    "recovery did not prove every canonical gate"
                )
            raw["disposition"] = "accepted"
            raw["observed_result"] = {
                "workspace_relative_path": destination,
                "fingerprint": fingerprint.to_dict(),
                "observed_at": timestamp,
            }
            step_ids.append(step_id)
        committed["commit_point"] = {"reached": True, "reached_at": timestamp}
        partial = committed.get("partial_state")
        if not isinstance(partial, dict):
            raise PortiaCorruptionError("recovering partial state is malformed")
        partial.update(
            {
                "durability_assessment": "confirmed",
                "accepted_steps": step_ids,
                "verified_steps": [],
                "durable_unverified_steps": [],
                "indeterminate_steps": [],
                "remaining_canonical_steps": [],
                "recommended_disposition": None,
            }
        )
        if fault_hook is not None:
            fault_hook("before_recovery_commit_journal", None)
        committed_state = self._append_state(current, committed, state="committed")
        if fault_hook is not None:
            fault_hook("after_recovery_commit_journal", None)
        return self._finalize_committed(committed_state, fault_hook=fault_hook)

    def resume_incomplete(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
        fault_hook: FaultHook | None = None,
    ) -> RecoveryWorkflowAssessment:
        """Complete only exact remaining writes of a recovering operation."""
        return self._resume(
            operation_id,
            expected_pointer=expected_pointer,
            require_all_durable=False,
            fault_hook=fault_hook,
        )

    def reconcile_as_complete(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
        fault_hook: FaultHook | None = None,
    ) -> RecoveryWorkflowAssessment:
        """Complete journaling only when every canonical result already matches."""
        return self._resume(
            operation_id,
            expected_pointer=expected_pointer,
            require_all_durable=True,
            fault_hook=fault_hook,
        )

    def finalize_post_commit(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
        fault_hook: FaultHook | None = None,
    ) -> RecoveryWorkflowAssessment:
        """Release exact held locks and publish completed post-commit evidence."""
        assessment = self.assess(operation_id)
        if assessment.disposition == "terminal_consistent":
            return assessment
        if assessment.disposition != "finalize_post_commit":
            raise WorkflowPrerequisiteError("operation is not ready for post-commit finalization")
        current = self._journals.load_current(operation_id)
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError("operation current pointer changed before recovery")
        return self._finalize_committed(current, fault_hook=fault_hook)
