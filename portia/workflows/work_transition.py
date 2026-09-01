"""Coordinated lifecycle persistence for canonical Portia work roots."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.io import read_bytes
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import (
    work_manifest_path,
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.workflows.action_transition import (
    ActionLifecycleCoordinator,
    _correction_intent_digest,
    _intent_digest,
    _journal_plan,
    _lock_plan,
    _state_fact,
)
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

WorkCandidateValidator = Callable[[PortiaRecord, PortiaRecord], None]
WorkTransitionFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
WorkPredecessorFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
WorkSuccessorValidator = Callable[[PortiaRecord, PortiaRecord], None]


def _completed_work_correction_matches(
    journal_data: Mapping[str, object],
    predecessor: ExactPortiaWorkRef,
    successor: PortiaRecord,
    transition_id: str,
) -> bool:
    successor_work = ExactPortiaWorkRef(
        class_id=str(successor.class_id),
        work_id=str(successor.work_id),
        work_kind="support_process",
        contract_version="1",
    )
    predecessor_target = work_target(predecessor)
    successor_target = work_target(successor_work)
    transition_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": predecessor.to_dict(),
            "record_ref": {
                "record_kind": "lifecycle_transition",
                "record_id": transition_id,
                "contract_version": "1",
            },
        },
    }
    successor_fp = fingerprint_bytes(canonical_json_bytes(successor.to_dict()))
    saw_predecessor = False
    saw_successor = False
    saw_transition = False
    write_set = journal_data.get("write_set")
    if not isinstance(write_set, list):
        return False
    for step in write_set:
        if not isinstance(step, Mapping):
            continue
        target = step.get("target")
        action = step.get("action")
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            continue
        if target == predecessor_target and action == "revision_aware_replace":
            selected = intended.get("selected_state")
            saw_predecessor = selected == [_state_fact("status", "superseded")]
        elif target == successor_target and action == "exclusive_create":
            try:
                saw_successor = (
                    ContentFingerprint.from_dict(intended.get("fingerprint"))
                    == successor_fp
                )
            except ValueError:
                return False
        elif target == transition_target and action == "exclusive_create":
            saw_transition = True
    return saw_predecessor and saw_successor and saw_transition


def _correction_lock_plan(
    operation_id: str,
    predecessor: ExactPortiaWorkRef,
    successor: ExactPortiaWorkRef,
    timestamp: str,
) -> tuple[list[dict[str, object]], dict[str, PortiaRecord]]:
    left_entries, left_records = _lock_plan(operation_id, predecessor, timestamp)
    right_entries, right_records = _lock_plan(operation_id, successor, timestamp)
    successor_entry = dict(right_entries[1])
    successor_entry["sequence"] = 3
    records = dict(left_records)
    for lock_id, record in right_records.items():
        records.setdefault(lock_id, record)
    return [*left_entries, successor_entry], records

def _completed_work_candidate_matches(
    journal_data: Mapping[str, object],
    work: ExactPortiaWorkRef,
    candidate: PortiaRecord,
) -> bool:
    target = work_target(work)
    candidate_fp = fingerprint_bytes(canonical_json_bytes(candidate.to_dict()))
    write_set = journal_data.get("write_set")
    if not isinstance(write_set, list):
        return False
    for step in write_set:
        if not isinstance(step, Mapping):
            continue
        if (
            step.get("action") != "revision_aware_replace"
            or step.get("target") != target
        ):
            continue
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            return False
        try:
            return (
                ContentFingerprint.from_dict(intended.get("fingerprint"))
                == candidate_fp
            )
        except ValueError:
            return False
    return False


class WorkLifecycleCoordinator(WorkflowServiceBase):
    """Commit one work-root lifecycle revision through Portia's #38 gate."""

    def _writer(self) -> ActionLifecycleCoordinator:
        return ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _completed_replay(
        self,
        operation_id: str | None,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
    ) -> OperationCommitResult | None:
        if operation_id is None:
            return None
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            return None
        data = current.revision.to_dict()
        state = data.get("state")
        if state == "completed":
            if not _completed_work_candidate_matches(data, work, candidate):
                raise PortiaConflictError(
                    "completed work lifecycle operation identity is bound "
                    "to different intent"
                )
            return self._writer()._operation_support()._completed_result(
                operation_id,
                data,
            )
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing work lifecycle operation requires explicit #38 recovery"
            )
        return None

    @staticmethod
    def _require_exact_candidate(
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
    ) -> None:
        if (
            candidate.contract != work.work_kind
            or candidate.contract_version != work.contract_version
            or candidate.class_id != work.class_id
            or candidate.work_id != work.work_id
        ):
            raise WorkflowOwnershipError(
                "work lifecycle candidate must preserve exact selected identity"
            )

    def commit(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        candidate_validator: WorkCandidateValidator,
        transition_factory: WorkTransitionFactory,
    ) -> OperationCommitResult:
        """Persist one work-root lifecycle revision plus immutable transition."""
        replay = self._completed_replay(operation_id, work, candidate)
        if replay is not None:
            return replay
        self._require_exact_candidate(work, candidate)
        prior = self.repository.load_work(work)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected work state does not match selected canonical bytes"
            )
        candidate_validator(prior.record, candidate)
        transition = transition_factory(prior.record, candidate)
        root_target = work_target(work)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(root_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        candidate_data = candidate.to_dict()
        timestamp = candidate_data.get("updated_at")
        initiated_by = candidate_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "work lifecycle candidate update provenance is incomplete"
            )
        digest = _intent_digest(prior.record, candidate, transition)
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected canonical work changed during lifecycle preflight"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            prior.record.contract,
            work.work_id,
            prior.fingerprint.digest,
        )
        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        if history_path.exists():
            existing = read_bytes(history_path)
            if (
                existing != prior_bytes
                or fingerprint_bytes(existing) != prior.fingerprint
            ):
                raise PortiaCorruptionError("technical storage-history collision")
        else:
            candidates["step_history"] = prior_bytes
            steps.append(
                {
                    "step_id": "step_history",
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": {"kind": "workspace"},
                    "representation_role": "operational_revision",
                    "destination_path": workspace_relative(
                        self.workspace_root,
                        history_path,
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": work.contract_version,
                        "fingerprint": prior.fingerprint.to_dict(),
                        "selected_state": [
                            _state_fact("status", str(prior.record.status))
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": "preserve_prior_revision",
                }
            )

        transition_bytes = canonical_json_bytes(transition.to_dict())
        candidates["step_transition"] = transition_bytes
        steps.append(
            {
                "step_id": "step_transition",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": transition_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_record_path(
                        self.workspace_root,
                        work,
                        "lifecycle_transition",
                        transition_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": "1",
                    "fingerprint": fingerprint_bytes(transition_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("from_status", str(prior.record.status)),
                        _state_fact("to_status", str(candidate.status)),
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": reason_code,
            }
        )

        candidate_bytes = canonical_json_bytes(candidate.to_dict())
        candidates["step_work"] = candidate_bytes
        steps.append(
            {
                "step_id": "step_work",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": root_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_manifest_path(self.workspace_root, work),
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": work.contract_version,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": work.contract_version,
                    "fingerprint": fingerprint_bytes(candidate_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("status", str(candidate.status))
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": reason_code,
            }
        )
        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=timestamp,
            initiated_by=initiated_by,
            primary_target=root_target,
            affected_targets=[transition_target],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=str(prior.record.status),
            candidate_status=str(candidate.status),
            contract=prior.record.contract,
            operation_kind="transition_lifecycle",
        )
        result = self._writer()._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )
        accepted = self.repository.load_work(work)
        accepted_transition = self.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted.record.to_dict() != candidate.to_dict():
            raise PortiaCorruptionError(
                "committed work lifecycle candidate does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed work lifecycle transition does not match exact readback"
            )
        return result


    def commit_correction(
        self,
        predecessor: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        supersession_reason: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        successor_validator: WorkSuccessorValidator,
        predecessor_factory: WorkPredecessorFactory,
        transition_factory: WorkTransitionFactory,
    ) -> OperationCommitResult:
        """Create one corrected work root and supersede its exact predecessor."""
        if successor.class_id is None or successor.work_id is None:
            raise WorkflowOwnershipError(
                "corrected work successor has no exact canonical identity"
            )
        successor_work = ExactPortiaWorkRef(
            class_id=successor.class_id,
            work_id=successor.work_id,
            work_kind=successor.contract,
            contract_version=successor.contract_version,
        )
        if operation_id is not None:
            store = OperationJournalStore(self.workspace_root)
            try:
                current = store.load_current(operation_id)
            except PortiaNotFoundError:
                pass
            else:
                data = current.revision.to_dict()
                state = data.get("state")
                if state == "completed":
                    if not _completed_work_correction_matches(
                        data,
                        predecessor,
                        successor,
                        transition_id,
                    ):
                        raise PortiaConflictError(
                            "completed work correction operation identity is bound "
                            "to different intent"
                        )
                    return self._writer()._operation_support()._completed_result(
                        operation_id,
                        data,
                    )
                if state != "staged":
                    raise PortiaRecoveryRequiredError(
                        "existing work correction operation requires explicit #38 "
                        "recovery"
                    )

        if (
            predecessor.work_kind != "support_process"
            or predecessor.contract_version != "1"
            or successor.contract != "support_process"
            or successor.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "work correction currently requires support_process@1 roots"
            )
        if successor_work == predecessor:
            raise WorkflowOwnershipError(
                "work correction successor must use a new exact work identity"
            )
        prior = self.repository.load_work(predecessor)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor work state does not match canonical bytes"
            )
        successor_validator(prior.record, successor)
        try:
            self.repository.load_work(successor_work)
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "corrected Support Process successor identity already exists"
            )
        try:
            self.repository.load_work_record(
                predecessor,
                "lifecycle_transition",
                "1",
                transition_id,
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "work correction lifecycle transition identity already exists"
            )

        predecessor_candidate = predecessor_factory(prior.record, successor)
        transition = transition_factory(prior.record, predecessor_candidate)
        predecessor_target = work_target(predecessor)
        successor_target = work_target(successor_work)
        transition_target = record_target(predecessor, transition)
        self.quarantine.require_allowed(predecessor_target, "block_work_writes")
        self.quarantine.require_allowed(successor_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        successor_data = successor.to_dict()
        timestamp = successor_data.get("updated_at")
        initiated_by = successor_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "corrected work successor update provenance is incomplete"
            )
        digest = _correction_intent_digest(
            prior.record,
            predecessor_candidate,
            successor,
            transition,
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _correction_lock_plan(
            op_id,
            predecessor,
            successor_work,
            timestamp,
        )

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor work changed during correction preflight"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            predecessor,
            prior.record.contract,
            predecessor.work_id,
            prior.fingerprint.digest,
        )
        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        if history_path.exists():
            existing = read_bytes(history_path)
            if (
                existing != prior_bytes
                or fingerprint_bytes(existing) != prior.fingerprint
            ):
                raise PortiaCorruptionError("technical storage-history collision")
        else:
            candidates["step_history"] = prior_bytes
            steps.append(
                {
                    "step_id": "step_history",
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": {"kind": "workspace"},
                    "representation_role": "operational_revision",
                    "destination_path": workspace_relative(
                        self.workspace_root,
                        history_path,
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": predecessor.contract_version,
                        "fingerprint": prior.fingerprint.to_dict(),
                        "selected_state": [
                            _state_fact("status", str(prior.record.status))
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": "preserve_prior_revision",
                }
            )

        successor_bytes = canonical_json_bytes(successor.to_dict())
        candidates["step_successor"] = successor_bytes
        steps.append(
            {
                "step_id": "step_successor",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": successor_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_manifest_path(self.workspace_root, successor_work),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": successor_work.contract_version,
                    "fingerprint": fingerprint_bytes(successor_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("status", str(successor.status))
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": supersession_reason,
            }
        )

        transition_bytes = canonical_json_bytes(transition.to_dict())
        candidates["step_transition"] = transition_bytes
        steps.append(
            {
                "step_id": "step_transition",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": transition_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_record_path(
                        self.workspace_root,
                        predecessor,
                        "lifecycle_transition",
                        transition_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": "1",
                    "fingerprint": fingerprint_bytes(transition_bytes).to_dict(),
                    "selected_state": [
                        _state_fact("from_status", str(prior.record.status)),
                        _state_fact("to_status", "superseded"),
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": supersession_reason,
            }
        )

        predecessor_bytes = canonical_json_bytes(predecessor_candidate.to_dict())
        candidates["step_work"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_work",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": predecessor_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_manifest_path(self.workspace_root, predecessor),
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": predecessor.contract_version,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": predecessor.contract_version,
                    "fingerprint": fingerprint_bytes(predecessor_bytes).to_dict(),
                    "selected_state": [_state_fact("status", "superseded")],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": supersession_reason,
            }
        )

        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=timestamp,
            initiated_by=initiated_by,
            primary_target=predecessor_target,
            affected_targets=[successor_target, transition_target],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=str(prior.record.status),
            candidate_status="superseded",
            contract="support_process",
            operation_kind="activate_successor",
        )
        result = self._writer()._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )
        accepted_predecessor = self.repository.load_work(predecessor)
        accepted_successor = self.repository.load_work(successor_work)
        accepted_transition = self.repository.load_work_record(
            predecessor,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted_predecessor.record.to_dict() != predecessor_candidate.to_dict():
            raise PortiaCorruptionError(
                "committed work correction predecessor does not match exact readback"
            )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaCorruptionError(
                "committed work correction successor does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed work correction transition does not match exact readback"
            )
        return result
