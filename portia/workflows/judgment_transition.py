"""Coordinated lifecycle and successor persistence for Event-local judgments."""

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
from portia.storage.repository import StoredRecord
from portia.storage.series import OperationJournalStore
from portia.storage.staging import cleanup_staged
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.coordinated import EventBundleWorkflowService
from portia.workflows.determination_reconsideration import (
    require_determination_reconsideration_topology,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.judgment_common import (
    JUDGMENT_CONTRACTS,
    JUDGMENT_VERSION,
    require_digital_judgment_creation,
    require_judgment_owner_write_eligibility,
    require_judgment_record_owner,
)
from portia.workflows.judgment_lifecycle import (
    build_judgment_lifecycle_transition,
    require_judgment_lifecycle_reconciled,
)
from portia.workflows.judgment_supersession import (
    require_exact_judgment_correction_predecessor,
    require_material_judgment_correction,
    superseded_judgment_predecessor,
)

ActivationValidator = Callable[[PortiaRecord], None]
SuccessorValidator = Callable[[PortiaRecord], None]


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


def _single_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    supersedes = successor.to_dict().get("supersedes")
    if not isinstance(supersedes, list) or len(supersedes) != 1:
        raise WorkflowPrerequisiteError(
            "judgment successor requires exactly one predecessor"
        )
    entry = supersedes[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("judgment supersession entry is malformed")
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "judgment supersession detail must be bounded non-empty text"
        )
    return detail


def _state_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "token", "value": value}


def _expected_state(step: Mapping[str, object]) -> dict[str, object]:
    precondition = step.get("precondition")
    if not isinstance(precondition, Mapping):
        raise PortiaConflictError("judgment lifecycle write step has no precondition")
    presence = precondition.get("presence")
    if presence == "must_be_absent":
        return {"presence": "must_be_absent"}
    if presence != "must_match":
        raise PortiaConflictError(
            "judgment lifecycle write precondition is unsupported"
        )
    fingerprint = precondition.get("fingerprint")
    semantic_checks = precondition.get("semantic_checks")
    if not isinstance(fingerprint, Mapping) or not isinstance(semantic_checks, list):
        raise PortiaConflictError(
            "judgment lifecycle must-match precondition is incomplete"
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
    transition_target: dict[str, object],
    lock_entries: list[dict[str, object]],
    steps: list[dict[str, object]],
    prior_status: str,
    candidate_status: str,
    contract: str,
) -> dict[str, object]:
    preflight: list[dict[str, object]] = []
    for step in steps:
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            raise PortiaConflictError(
                "judgment lifecycle intended result is invalid"
            )
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
            raise PortiaConflictError("judgment lifecycle write step is incomplete")
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
        "operation_kind": "transition_lifecycle",
        "intent_digest": digest,
        "scope": "work",
        "primary_target": primary_target,
        "affected_targets": [transition_target],
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
                "deployment_instance_id": "judgment_lifecycle",
                "process_instance_id": "judgment_lifecycle",
            },
        )
    return entries, records


def _completed_transition_matches(
    journal_data: Mapping[str, object],
    reference: ExactPortiaWorkRecordRef,
    candidate: PortiaRecord,
    transition_id: str,
    reason_code: str,
) -> bool:
    judgment_target = {
        "kind": "work_record",
        "work_record_ref": reference.to_dict(),
    }
    transition_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": reference.work_ref.to_dict(),
            "record_ref": {
                "record_kind": "lifecycle_transition",
                "record_id": transition_id,
                "contract_version": "1",
            },
        },
    }
    candidate_fp = fingerprint_bytes(canonical_json_bytes(candidate.to_dict()))
    saw_candidate = False
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
        if action == "revision_aware_replace" and target == judgment_target:
            try:
                saw_candidate = (
                    ContentFingerprint.from_dict(intended.get("fingerprint"))
                    == candidate_fp
                )
            except ValueError:
                return False
        elif action == "exclusive_create" and target == transition_target:
            saw_transition = step.get("reason_code") == reason_code
    return saw_candidate and saw_transition


def _completed_correction_matches(
    journal_data: Mapping[str, object],
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
    transition_id: str,
) -> bool:
    predecessor_target = {
        "kind": "work_record",
        "work_record_ref": predecessor.to_dict(),
    }
    successor_id = successor.logical_id
    if successor_id is None:
        return False
    successor_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": predecessor.work_ref.to_dict(),
            "record_ref": {
                "record_kind": successor.contract,
                "record_id": successor_id,
                "contract_version": successor.contract_version,
            },
        },
    }
    transition_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": predecessor.work_ref.to_dict(),
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
    return saw_predecessor and saw_successor and saw_transition


class JudgmentLifecycleCoordinator(WorkflowServiceBase):
    """Commit an ordinary judgment status transition through #38 coordination."""

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
        transition_id: str,
        reason_code: str,
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
            if not _completed_transition_matches(
                data,
                reference,
                candidate,
                transition_id,
                reason_code,
            ):
                raise PortiaConflictError(
                    "completed judgment lifecycle operation identity is bound "
                    "to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing judgment lifecycle operation requires explicit #38 recovery"
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
                data, predecessor, successor, transition_id
            ):
                raise PortiaConflictError(
                    "completed judgment correction operation identity is bound "
                    "to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing judgment correction operation requires explicit #38 recovery"
            )
        return None

    def _commit_validated_successor(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        prior: StoredRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
        reason_detail: str | None,
        transition_id: str,
        effective_at: str | None,
        operation_id: str | None,
        fault_hook: FaultHook | None,
    ) -> OperationCommitResult:
        work = predecessor.work_ref
        family = predecessor.record_ref.record_kind
        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError(
                "judgment successor has no canonical identity"
            )

        predecessor_candidate = superseded_judgment_predecessor(
            prior.record, successor
        )
        transition = build_judgment_lifecycle_transition(
            self.repository,
            work,
            prior.record,
            predecessor_candidate,
            transition_id=transition_id,
            reason_code=supersession_reason,
            reason_detail=reason_detail,
            effective_at=effective_at,
            _allow_supersession=True,
        )
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
                "corrected judgment successor update provenance is incomplete"
            )
        digest = _correction_intent_digest(
            prior.record, predecessor_candidate, successor, transition
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor judgment changed during correction preflight"
            )
        predecessor_id = prior.record.logical_id
        if predecessor_id is None:
            raise WorkflowOwnershipError(
                "selected predecessor judgment has no canonical identity"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            family,
            predecessor_id,
            prior.fingerprint.digest,
        )

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        if history_path.exists():
            existing = read_bytes(history_path)
            if existing != prior_bytes or fingerprint_bytes(existing) != prior.fingerprint:
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
                        self.workspace_root, history_path
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": prior.record.contract_version,
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
                        self.workspace_root, work, family, successor_id
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": JUDGMENT_VERSION,
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
        candidates["step_judgment"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_judgment",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": predecessor_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root, prior.path
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": prior.record.contract_version,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": JUDGMENT_VERSION,
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
            transition_target=transition_target,
            lock_entries=lock_entries,
            steps=steps,
            prior_status=str(prior.record.status),
            candidate_status="superseded",
            contract=family,
        )
        plan["operation_kind"] = "activate_successor"
        plan["affected_targets"] = [successor_target, transition_target]
        journal = parse_portia_record("operation_journal", "2", plan)
        store = OperationJournalStore(self.workspace_root)
        support = self._operation_support()
        try:
            current = store.load_current(op_id)
        except PortiaNotFoundError:
            current = store.create(journal, support._pointer(op_id, 1))
        else:
            current_data = current.revision.to_dict()
            if current_data.get("intent_digest") != digest:
                raise PortiaConflictError(
                    "operation identity is already bound to different judgment "
                    "correction intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing judgment correction operation requires explicit #38 recovery"
                )

        staged = stage_journaled_candidates(
            self.workspace_root, plan, candidates, fault_hook=fault_hook
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
                plan, current, exc, lock_records, staged
            )
            raise
        except Exception:
            for artifact in staged:
                cleanup_staged(self.workspace_root, artifact)
            raise
        support._complete_journal(plan, current, result, lock_records)
        for artifact in staged:
            cleanup_staged(self.workspace_root, artifact)

        accepted_predecessor = self.repository.load_work_record(
            work, family, JUDGMENT_VERSION, predecessor.record_ref.record_id
        )
        accepted_successor = self.repository.load_work_record(
            work, family, JUDGMENT_VERSION, successor_id
        )
        accepted_transition = self.repository.load_work_record(
            work, "lifecycle_transition", "1", transition_id
        )
        if accepted_predecessor.record.to_dict() != predecessor_candidate.to_dict():
            raise PortiaCorruptionError(
                "committed judgment correction predecessor does not match exact readback"
            )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaCorruptionError(
                "committed judgment correction successor does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed judgment correction transition does not match exact readback"
            )
        require_judgment_lifecycle_reconciled(
            self.repository, work, accepted_predecessor.record
        )
        return result

    def commit_correction(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
        successor_validator: SuccessorValidator | None = None,
    ) -> OperationCommitResult:
        """Create one active corrected successor and supersede its exact predecessor."""
        replay = self._completed_correction_replay(
            operation_id, predecessor, successor, transition_id
        )
        if replay is not None:
            return replay

        work = predecessor.work_ref
        family = predecessor.record_ref.record_kind
        if family not in JUDGMENT_CONTRACTS:
            raise WorkflowOwnershipError(
                "judgment correction requires a judgment predecessor"
            )
        if predecessor.record_ref.contract_version != JUDGMENT_VERSION:
            raise WorkflowOwnershipError(
                "judgment correction requires an exact v1 predecessor"
            )
        require_judgment_record_owner(work, successor, contract=family)
        require_digital_judgment_creation(successor)
        supersession_reason = require_exact_judgment_correction_predecessor(
            work, predecessor, successor
        )
        reason_detail = _single_supersession_reason_detail(successor)

        prior = self.repository.load_work_record(
            work,
            family,
            JUDGMENT_VERSION,
            predecessor.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor judgment state does not match selected canonical bytes"
            )
        require_judgment_record_owner(work, prior.record, contract=family)
        require_material_judgment_correction(
            prior.record, successor, supersession_reason
        )
        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError(
                "corrected judgment successor has no canonical identity"
            )
        if any(
            stored.record.logical_id == successor_id
            for stored in self.repository.list_work_records(
                work, family, version=JUDGMENT_VERSION
            )
        ):
            raise PortiaConflictError(
                "corrected judgment successor identity already exists"
            )
        try:
            self.repository.load_work_record(
                work, "lifecycle_transition", "1", transition_id
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "judgment correction lifecycle transition identity already exists"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        if successor_validator is None:
            raise WorkflowPrerequisiteError(
                "active corrected judgment successor requires family-specific "
                "current-use validation"
            )
        successor_validator(successor)
        return self._commit_validated_successor(
            predecessor,
            prior,
            successor,
            supersession_reason=supersession_reason,
            reason_detail=reason_detail,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
        )

    def commit_determination_reconsideration(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        review_reference: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
        successor_validator: SuccessorValidator | None = None,
    ) -> OperationCommitResult:
        """Persist one guarded Determination reconsideration or reversal successor."""
        work = predecessor.work_ref
        if (
            predecessor.record_ref.record_kind != "determination"
            or predecessor.record_ref.contract_version != JUDGMENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Determination reconsideration requires an exact determination@1 "
                "predecessor"
            )
        if (
            review_reference.work_ref != work
            or review_reference.record_ref.record_kind != "review"
            or review_reference.record_ref.contract_version != JUDGMENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Determination reconsideration requires an exact Event-local review@1 "
                "reference"
            )
        require_judgment_record_owner(work, successor, contract="determination")
        require_digital_judgment_creation(successor)
        successor_data = successor.to_dict()
        raw_review_ref = successor_data.get("review_ref")
        if not isinstance(raw_review_ref, Mapping):
            raise WorkflowOwnershipError(
                "Determination reconsideration successor review_ref is malformed"
            )
        try:
            selected_review = ExactPortiaWorkRecordRef.from_dict(raw_review_ref)
        except (TypeError, ValueError) as exc:
            raise WorkflowOwnershipError(
                "Determination reconsideration successor review_ref is malformed"
            ) from exc
        if selected_review != review_reference:
            raise WorkflowOwnershipError(
                "Determination reconsideration successor must reference the exact "
                "supplied Review"
            )

        replay = self._completed_correction_replay(
            operation_id, predecessor, successor, transition_id
        )
        if replay is not None:
            return replay

        prior = self.repository.load_work_record(
            work,
            "determination",
            JUDGMENT_VERSION,
            predecessor.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor Determination state does not match selected "
                "canonical bytes"
            )
        require_judgment_record_owner(
            work, prior.record, contract="determination"
        )
        review = self.repository.load_work_record(
            work,
            "review",
            JUDGMENT_VERSION,
            review_reference.record_ref.record_id,
        )
        require_judgment_lifecycle_reconciled(
            self.repository, work, review.record
        )
        supersession_reason = require_determination_reconsideration_topology(
            work,
            predecessor,
            prior.record,
            review.record,
            successor,
        )
        reason_detail = _single_supersession_reason_detail(successor)

        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError(
                "Determination reconsideration successor has no canonical identity"
            )
        if any(
            stored.record.logical_id == successor_id
            for stored in self.repository.list_work_records(
                work, "determination", version=JUDGMENT_VERSION
            )
        ):
            raise PortiaConflictError(
                "Determination reconsideration successor identity already exists"
            )
        try:
            self.repository.load_work_record(
                work, "lifecycle_transition", "1", transition_id
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "Determination reconsideration lifecycle transition identity "
                "already exists"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        if successor_validator is None:
            raise WorkflowPrerequisiteError(
                "active reconsidered Determination successor requires "
                "family-specific current-use validation"
            )
        successor_validator(successor)
        return self._commit_validated_successor(
            predecessor,
            prior,
            successor,
            supersession_reason=supersession_reason,
            reason_detail=reason_detail,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
        )

    def commit(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str,
        reason_detail: str | None = None,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
        activation_validator: ActivationValidator | None = None,
    ) -> OperationCommitResult:
        """Persist one proposed/active -> active/invalidated judgment transition."""
        replay = self._completed_replay(
            operation_id,
            reference,
            candidate,
            transition_id,
            reason_code,
        )
        if replay is not None:
            return replay

        work = reference.work_ref
        family = reference.record_ref.record_kind
        if family not in JUDGMENT_CONTRACTS:
            raise WorkflowOwnershipError(
                "judgment lifecycle transition requires a judgment reference"
            )
        if reference.record_ref.contract_version != JUDGMENT_VERSION:
            raise WorkflowOwnershipError(
                "judgment lifecycle transition requires an exact v1 judgment reference"
            )
        if (
            candidate.contract != family
            or candidate.contract_version != JUDGMENT_VERSION
            or candidate.logical_id != reference.record_ref.record_id
        ):
            raise WorkflowOwnershipError(
                "lifecycle candidate does not preserve the selected exact judgment identity"
            )

        prior = self.repository.load_work_record(
            work,
            family,
            JUDGMENT_VERSION,
            reference.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected judgment state does not match selected canonical bytes"
            )
        require_judgment_record_owner(work, prior.record, contract=family)
        require_judgment_record_owner(work, candidate, contract=family)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)

        if candidate.status == "active":
            if activation_validator is None:
                raise WorkflowPrerequisiteError(
                    "judgment activation requires family-specific current-use validation"
                )
            activation_validator(candidate)

        transition = build_judgment_lifecycle_transition(
            self.repository,
            work,
            prior.record,
            candidate,
            transition_id=transition_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
        )
        judgment_target = record_target(work, candidate)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(judgment_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        candidate_data = candidate.to_dict()
        timestamp = candidate_data.get("updated_at")
        initiated_by = candidate_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "judgment lifecycle candidate update provenance is incomplete"
            )
        digest = _intent_digest(prior.record, candidate, transition)
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected canonical judgment changed during lifecycle preflight"
            )
        prior_id = prior.record.logical_id
        if prior_id is None:
            raise WorkflowOwnershipError("selected judgment has no canonical identity")
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            prior.record.contract,
            prior_id,
            prior.fingerprint.digest,
        )

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        if history_path.exists():
            existing = read_bytes(history_path)
            if existing != prior_bytes or fingerprint_bytes(existing) != prior.fingerprint:
                raise PortiaCorruptionError("technical storage-history collision")
        else:
            history_step = "step_history"
            candidates[history_step] = prior_bytes
            steps.append(
                {
                    "step_id": history_step,
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": {"kind": "workspace"},
                    "representation_role": "operational_revision",
                    "destination_path": workspace_relative(
                        self.workspace_root, history_path
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": prior.record.contract_version,
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

        transition_step = "step_transition"
        transition_bytes = canonical_json_bytes(transition.to_dict())
        candidates[transition_step] = transition_bytes
        steps.append(
            {
                "step_id": transition_step,
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

        judgment_step = "step_judgment"
        candidate_bytes = canonical_json_bytes(candidate.to_dict())
        candidates[judgment_step] = candidate_bytes
        steps.append(
            {
                "step_id": judgment_step,
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": judgment_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root, prior.path
                ),
                "precondition": {
                    "presence": "must_match",
                    "fingerprint": prior.fingerprint.to_dict(),
                    "contract_version": prior.record.contract_version,
                    "semantic_checks": [
                        _state_fact("status", str(prior.record.status))
                    ],
                },
                "intended_result": {
                    "contract_version": candidate.contract_version,
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
            primary_target=judgment_target,
            transition_target=transition_target,
            lock_entries=lock_entries,
            steps=steps,
            prior_status=str(prior.record.status),
            candidate_status=str(candidate.status),
            contract=candidate.contract,
        )
        journal = parse_portia_record("operation_journal", "2", plan)
        store = OperationJournalStore(self.workspace_root)
        support = self._operation_support()
        try:
            current = store.load_current(op_id)
        except PortiaNotFoundError:
            current = store.create(journal, support._pointer(op_id, 1))
        else:
            current_data = current.revision.to_dict()
            if current_data.get("intent_digest") != digest:
                raise PortiaConflictError(
                    "operation identity is already bound to different judgment "
                    "lifecycle intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing judgment lifecycle operation requires explicit #38 recovery"
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

        accepted = self.repository.load_work_record(
            work,
            family,
            JUDGMENT_VERSION,
            reference.record_ref.record_id,
        )
        if accepted.record.to_dict() != candidate.to_dict():
            raise PortiaCorruptionError(
                "committed judgment lifecycle candidate does not match exact readback"
            )
        stored_transition = self.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if stored_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed judgment lifecycle transition does not match exact readback"
            )
        require_judgment_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result
