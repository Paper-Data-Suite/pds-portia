"""Shared coordinated persistence for Response/Communication lifecycle changes."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.io import read_bytes
from portia.storage.locks import derive_lock_id
from portia.storage.orchestration import (
    FaultHook,
    OperationCommitResult,
    commit_journaled_candidates,
    stage_journaled_candidates,
)
from portia.storage.paths import (
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.storage.staging import cleanup_staged
from portia.workflows.action_common import ACTION_VERSION, require_action_owner
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.coordinated import EventBundleWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

CandidateValidator = Callable[[PortiaRecord, PortiaRecord], None]
TransitionFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
PredecessorFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
SuccessorValidator = Callable[[PortiaRecord, PortiaRecord], None]


def _state_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "token", "value": value}


def _intent_digest(
    prior: PortiaRecord,
    candidate: PortiaRecord,
    transition: PortiaRecord,
) -> str:
    payload = b"".join(
        canonical_json_bytes(record.to_dict())
        for record in (prior, candidate, transition)
    )
    return hashlib.sha256(payload).hexdigest()


def _correction_intent_digest(
    prior: PortiaRecord,
    predecessor_candidate: PortiaRecord,
    successor: PortiaRecord,
    transition: PortiaRecord,
) -> str:
    payload = b"".join(
        canonical_json_bytes(record.to_dict())
        for record in (prior, predecessor_candidate, successor, transition)
    )
    return hashlib.sha256(payload).hexdigest()


def _expected_state(step: Mapping[str, object]) -> dict[str, object]:
    precondition = step.get("precondition")
    if not isinstance(precondition, Mapping):
        raise PortiaConflictError("action lifecycle write step has no precondition")
    presence = precondition.get("presence")
    if presence == "must_be_absent":
        return {"presence": "must_be_absent"}
    if presence != "must_match":
        raise PortiaConflictError(
            "action lifecycle write precondition is unsupported"
        )
    fingerprint = precondition.get("fingerprint")
    semantic_checks = precondition.get("semantic_checks")
    if not isinstance(fingerprint, Mapping) or not isinstance(semantic_checks, list):
        raise PortiaConflictError(
            "action lifecycle must-match precondition is incomplete"
        )
    return {
        "presence": "must_match",
        "fingerprint": dict(fingerprint),
        "semantic_checks": semantic_checks,
    }


def _journal_plan(
    *,
    operation_id: str,
    digest: str,
    timestamp: str,
    initiated_by: Mapping[str, object],
    primary_target: dict[str, object],
    affected_targets: list[dict[str, object]],
    lock_entries: list[dict[str, object]],
    steps: list[dict[str, object]],
    prior_status: str,
    candidate_status: str,
    contract: str,
    operation_kind: str,
) -> dict[str, object]:
    preflight: list[dict[str, object]] = []
    for step in steps:
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            raise PortiaConflictError("action lifecycle intended result is invalid")
        contract_version = intended.get("contract_version")
        selected_state = intended.get("selected_state")
        destination = step.get("destination_path")
        role = step.get("representation_role")
        target = step.get("target")
        if (
            not isinstance(contract_version, str)
            or not isinstance(selected_state, list)
            or not isinstance(destination, str)
            or not isinstance(role, str)
            or not isinstance(target, dict)
        ):
            raise PortiaConflictError("action lifecycle write step is incomplete")
        preflight.append(
            {
                "target": target,
                "representation_role": role,
                "expected_state": _expected_state(step),
                "workspace_relative_path": destination,
                "contract_version": contract_version,
                "source_basis": "canonical",
                "source_projection": None,
                "selected_state": selected_state,
                "observed_at": timestamp,
            }
        )
    preflight_digest = fingerprint_bytes(
        canonical_json_bytes({"entries": preflight})
    ).digest
    step_ids = [str(step["step_id"]) for step in steps]
    return {
        "schema_version": "2",
        "record_type": "operation_journal",
        "module_id": "portia",
        "operation_id": operation_id,
        "operation_kind": operation_kind,
        "intent_digest": digest,
        "scope": "work",
        "primary_target": primary_target,
        "affected_targets": affected_targets,
        "intent_facts": [
            _state_fact("record_kind", contract),
            _state_fact("from_status", prior_status),
            _state_fact("to_status", candidate_status),
        ],
        "initiated_at": timestamp,
        "initiated_by": dict(initiated_by),
        "authorization_references": [],
        "journal_revision": 1,
        "previous_journal_revision": None,
        "state": "staged",
        "preflight_snapshot_digest": preflight_digest,
        "preflight_snapshot": preflight,
        "lock_set": lock_entries,
        "write_set": steps,
        "staged_artifacts": [],
        "commit_point": {"reached": False, "reached_at": None},
        "compensation_plan": [],
        "recovery_plan": [
            "resume",
            "abandon_preacceptance_artifacts",
            "require_manual_review",
        ],
        "partial_state": {
            "durability_assessment": "none",
            "accepted_steps": [],
            "verified_steps": [],
            "durable_unverified_steps": [],
            "indeterminate_steps": [],
            "remaining_canonical_steps": step_ids,
            "remaining_post_commit_steps": [],
            "current_pointer_changes": [],
            "held_or_possible_locks": [],
            "quarantined_targets": [],
            "active_finding_keys": [],
            "recommended_disposition": "resume",
        },
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def _lock_plan(
    operation_id: str,
    work: ExactPortiaWorkRef,
    timestamp: str,
) -> tuple[list[dict[str, object]], dict[str, PortiaRecord]]:
    operation_target: dict[str, object] = {
        "kind": "operation",
        "operation_ref": {"operation_id": operation_id},
    }
    targets = (("operation", operation_target), ("work", work_target(work)))
    entries: list[dict[str, object]] = []
    records: dict[str, PortiaRecord] = {}
    for sequence, (scope, target) in enumerate(targets, start=1):
        lock_id = derive_lock_id(scope, target)
        entries.append(
            {
                "lock_id": lock_id,
                "sequence": sequence,
                "lock_scope": scope,
                "protected_target": target,
                "lock_path": f"portia/locks/{lock_id}.json",
                "disposition": "planned",
                "fingerprint": None,
                "acquired_at": None,
                "released_at": None,
            }
        )
        records[lock_id] = parse_portia_record(
            "operation_lock",
            "2",
            {
                "schema_version": "2",
                "record_type": "operation_lock",
                "module_id": "portia",
                "lock_id": lock_id,
                "lock_scope": scope,
                "protected_target": target,
                "owning_operation": {"operation_id": operation_id},
                "acquired_at": timestamp,
                "deployment_instance_id": "action_lifecycle",
                "process_instance_id": "action_lifecycle",
            },
        )
    return entries, records


def _completed_candidate_matches(
    journal_data: Mapping[str, object],
    reference: ExactPortiaWorkRecordRef,
    candidate: PortiaRecord,
) -> bool:
    target = {"kind": "work_record", "work_record_ref": reference.to_dict()}
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


def _completed_correction_matches(
    journal_data: Mapping[str, object],
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
    transition_id: str,
) -> bool:
    work = predecessor.work_ref
    successor_target = record_target(work, successor)
    predecessor_target = {
        "kind": "work_record",
        "work_record_ref": predecessor.to_dict(),
    }
    transition_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": work.to_dict(),
            "record_ref": {
                "record_kind": "lifecycle_transition",
                "record_id": transition_id,
                "contract_version": "1",
            },
        },
    }
    successor_fp = fingerprint_bytes(canonical_json_bytes(successor.to_dict()))
    saw_successor = False
    saw_transition = False
    saw_predecessor = False
    write_set = journal_data.get("write_set")
    if not isinstance(write_set, list):
        return False
    for step in write_set:
        if not isinstance(step, Mapping):
            continue
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            continue
        target = step.get("target")
        action = step.get("action")
        if action == "exclusive_create" and target == successor_target:
            try:
                saw_successor = (
                    ContentFingerprint.from_dict(intended.get("fingerprint"))
                    == successor_fp
                )
            except ValueError:
                return False
        elif action == "exclusive_create" and target == transition_target:
            selected = intended.get("selected_state")
            saw_transition = (
                isinstance(selected, list)
                and _state_fact("to_status", "superseded") in selected
            )
        elif action == "revision_aware_replace" and target == predecessor_target:
            selected = intended.get("selected_state")
            saw_predecessor = (
                isinstance(selected, list)
                and _state_fact("status", "superseded") in selected
            )
    return saw_successor and saw_transition and saw_predecessor


class ActionLifecycleCoordinator(WorkflowServiceBase):
    """Commit validated action-layer lifecycle changes through #38 machinery."""

    def _operation_support(self) -> EventBundleWorkflowService:
        return EventBundleWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _completed_replay(
        self,
        operation_id: str | None,
        reference: ExactPortiaWorkRecordRef,
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
            if not _completed_candidate_matches(data, reference, candidate):
                raise PortiaConflictError(
                    "completed action lifecycle operation identity is bound "
                    "to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing action lifecycle operation requires explicit #38 recovery"
            )
        return None

    def _completed_correction_replay(
        self,
        operation_id: str | None,
        predecessor: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        transition_id: str,
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
            if not _completed_correction_matches(
                data,
                predecessor,
                successor,
                transition_id,
            ):
                raise PortiaConflictError(
                    "completed action correction operation identity is bound "
                    "to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing action correction operation requires explicit #38 recovery"
            )
        return None

    def _write_plan(
        self,
        *,
        plan: dict[str, object],
        candidates: dict[str, bytes],
        lock_records: dict[str, PortiaRecord],
        operation_id: str,
        digest: str,
        fault_hook: FaultHook | None,
    ) -> OperationCommitResult:
        journal = parse_portia_record("operation_journal", "2", plan)
        store = OperationJournalStore(self.workspace_root)
        support = self._operation_support()
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            current = store.create(journal, support._pointer(operation_id, 1))
        else:
            current_data = current.revision.to_dict()
            if current_data.get("intent_digest") != digest:
                raise PortiaConflictError(
                    "operation identity is already bound to different action intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(operation_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing action operation requires explicit #38 recovery"
                )

        staged = stage_journaled_candidates(
            self.workspace_root,
            plan,
            candidates,
            fault_hook=fault_hook,
        )
        try:
            result = commit_journaled_candidates(
                self.workspace_root,
                plan,
                staged,
                lock_records,
                fault_hook=fault_hook,
            )
        except PortiaOperationPartialCommitError as exc:
            support._record_partial_commit(
                plan,
                current,
                exc,
                lock_records,
                staged,
            )
            raise
        except Exception:
            for artifact in staged:
                cleanup_staged(self.workspace_root, artifact)
            raise
        support._complete_journal(plan, current, result, lock_records)
        for artifact in staged:
            cleanup_staged(self.workspace_root, artifact)
        return result

    def commit(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        candidate_validator: CandidateValidator,
        transition_factory: TransitionFactory,
    ) -> OperationCommitResult:
        """Persist one already-family-scoped ordinary lifecycle transition."""
        replay = self._completed_replay(operation_id, reference, candidate)
        if replay is not None:
            return replay
        work = reference.work_ref
        contract = reference.record_ref.record_kind
        require_action_owner(work, contract=contract)
        if reference.record_ref.contract_version != ACTION_VERSION:
            raise WorkflowOwnershipError(
                "action lifecycle transition requires an exact v1 reference"
            )
        if (
            candidate.contract != contract
            or candidate.contract_version != ACTION_VERSION
            or candidate.logical_id != reference.record_ref.record_id
        ):
            raise WorkflowOwnershipError(
                "action lifecycle candidate must preserve exact selected identity"
            )
        prior = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            reference.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected action state does not match selected canonical bytes"
            )
        candidate_validator(prior.record, candidate)
        transition = transition_factory(prior.record, candidate)
        action_target = record_target(work, candidate)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(action_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        candidate_data = candidate.to_dict()
        timestamp = candidate_data.get("updated_at")
        initiated_by = candidate_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "action lifecycle candidate update provenance is incomplete"
            )
        digest = _intent_digest(prior.record, candidate, transition)
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected canonical action changed during lifecycle preflight"
            )
        prior_id = prior.record.logical_id
        if prior_id is None:
            raise WorkflowOwnershipError("selected action has no canonical identity")
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            contract,
            prior_id,
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
                        "contract_version": ACTION_VERSION,
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
        candidates["step_action"] = candidate_bytes
        steps.append(
            {
                "step_id": "step_action",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": action_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    prior.path,
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": ACTION_VERSION,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": ACTION_VERSION,
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
            primary_target=action_target,
            affected_targets=[transition_target],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=str(prior.record.status),
            candidate_status=str(candidate.status),
            contract=contract,
            operation_kind="transition_lifecycle",
        )
        result = self._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )
        accepted = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            reference.record_ref.record_id,
        )
        accepted_transition = self.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted.record.to_dict() != candidate.to_dict():
            raise PortiaCorruptionError(
                "committed action lifecycle candidate does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed action lifecycle transition does not match exact readback"
            )
        return result

    def commit_correction(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        supersession_reason: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        successor_validator: SuccessorValidator,
        predecessor_factory: PredecessorFactory,
        transition_factory: TransitionFactory,
    ) -> OperationCommitResult:
        """Create one corrected successor and supersede its exact predecessor."""
        replay = self._completed_correction_replay(
            operation_id,
            predecessor,
            successor,
            transition_id,
        )
        if replay is not None:
            return replay
        work = predecessor.work_ref
        contract = predecessor.record_ref.record_kind
        require_action_owner(work, contract=contract)
        if predecessor.record_ref.contract_version != ACTION_VERSION:
            raise WorkflowOwnershipError(
                "action correction requires an exact v1 predecessor"
            )
        if (
            successor.contract != contract
            or successor.contract_version != ACTION_VERSION
        ):
            raise WorkflowOwnershipError(
                "corrected action successor must preserve the selected family@1"
            )
        prior = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            predecessor.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor action state does not match canonical bytes"
            )
        successor_validator(prior.record, successor)
        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError(
                "corrected action successor has no canonical identity"
            )
        if any(
            item.record.logical_id == successor_id
            for item in self.repository.list_work_records(
                work,
                contract,
                version=ACTION_VERSION,
            )
        ):
            raise PortiaConflictError(
                "corrected action successor identity already exists"
            )
        try:
            self.repository.load_work_record(
                work,
                "lifecycle_transition",
                "1",
                transition_id,
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "action correction lifecycle transition identity already exists"
            )

        predecessor_candidate = predecessor_factory(prior.record, successor)
        transition = transition_factory(prior.record, predecessor_candidate)
        predecessor_target = record_target(work, predecessor_candidate)
        successor_target = record_target(work, successor)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(predecessor_target, "block_work_writes")
        self.quarantine.require_allowed(successor_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        successor_data = successor.to_dict()
        timestamp = successor_data.get("updated_at")
        initiated_by = successor_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "corrected action successor update provenance is incomplete"
            )
        digest = _correction_intent_digest(
            prior.record,
            predecessor_candidate,
            successor,
            transition,
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor action changed during correction preflight"
            )
        predecessor_id = prior.record.logical_id
        if predecessor_id is None:
            raise WorkflowOwnershipError(
                "selected predecessor action has no canonical identity"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            contract,
            predecessor_id,
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
                        "contract_version": ACTION_VERSION,
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
                    work_record_path(
                        self.workspace_root,
                        work,
                        contract,
                        successor_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": ACTION_VERSION,
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
        candidates["step_action"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_action",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": predecessor_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    prior.path,
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": ACTION_VERSION,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": ACTION_VERSION,
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
            contract=contract,
            operation_kind="activate_successor",
        )
        result = self._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )
        accepted_predecessor = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            predecessor.record_ref.record_id,
        )
        accepted_successor = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            successor_id,
        )
        accepted_transition = self.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted_predecessor.record.to_dict() != predecessor_candidate.to_dict():
            raise PortiaCorruptionError(
                "committed action correction predecessor does not match exact readback"
            )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaCorruptionError(
                "committed action correction successor does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed action correction transition does not match exact readback"
            )
        return result
