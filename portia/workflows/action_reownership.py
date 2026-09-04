"""Shared cross-work ownership-correction persistence for action records."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
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
from portia.storage.locks import derive_lock_id
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import (
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.workflows.action_common import ACTION_VERSION, require_action_owner
from portia.workflows.action_transition import (
    ActionLifecycleCoordinator,
    _journal_plan,
    _state_fact,
)
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

OwnershipSuccessorValidator = Callable[[PortiaRecord, PortiaRecord], None]
OwnershipPredecessorFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
OwnershipTransitionFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]


def _ownership_intent_digest(
    source_work: ExactPortiaWorkRef,
    destination_work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    predecessor_candidate: PortiaRecord,
    successor: PortiaRecord,
    transition: PortiaRecord,
) -> str:
    payload = b"".join(
        (
            canonical_json_bytes(source_work.to_dict()),
            canonical_json_bytes(destination_work.to_dict()),
            canonical_json_bytes(prior.to_dict()),
            canonical_json_bytes(predecessor_candidate.to_dict()),
            canonical_json_bytes(successor.to_dict()),
            canonical_json_bytes(transition.to_dict()),
        )
    )
    return hashlib.sha256(payload).hexdigest()


def _work_key(work: ExactPortiaWorkRef) -> tuple[str, str, str, str]:
    return (
        work.class_id,
        work.work_id,
        work.work_kind,
        work.contract_version,
    )


def _cross_work_lock_plan(
    operation_id: str,
    source_work: ExactPortiaWorkRef,
    destination_work: ExactPortiaWorkRef,
    timestamp: str,
) -> tuple[list[dict[str, object]], dict[str, PortiaRecord]]:
    operation_target: dict[str, object] = {
        "kind": "operation",
        "operation_ref": {"operation_id": operation_id},
    }
    work_targets = sorted(
        {source_work, destination_work},
        key=_work_key,
    )
    targets: list[tuple[str, dict[str, object]]] = [
        ("operation", operation_target),
        *(("work", work_target(work)) for work in work_targets),
    ]
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
                "deployment_instance_id": "action_ownership",
                "process_instance_id": "action_ownership",
            },
        )
    return entries, records


def _completed_ownership_matches(
    journal_data: Mapping[str, object],
    predecessor: ExactPortiaWorkRecordRef,
    destination_work: ExactPortiaWorkRef,
    expected: ContentFingerprint,
    successor: PortiaRecord,
    transition_id: str,
    supersession_reason: str,
) -> bool:
    if (
        journal_data.get("operation_kind") != "correct_ownership"
        or journal_data.get("scope") != "graph"
    ):
        return False
    source_work = predecessor.work_ref
    predecessor_target = {
        "kind": "work_record",
        "work_record_ref": predecessor.to_dict(),
    }
    successor_target = record_target(destination_work, successor)
    transition_target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": source_work.to_dict(),
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
        if (
            target != {"kind": "workspace"}
            and step.get("reason_code") != supersession_reason
        ):
            continue
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
            precondition = step.get("precondition")
            if not isinstance(precondition, Mapping):
                return False
            try:
                prior_fp = ContentFingerprint.from_dict(
                    precondition.get("fingerprint")
                )
            except ValueError:
                return False
            selected = intended.get("selected_state")
            saw_predecessor = (
                prior_fp == expected
                and isinstance(selected, list)
                and _state_fact("status", "superseded") in selected
            )
    return saw_predecessor and saw_successor and saw_transition


class ActionOwnershipCorrectionCoordinator(WorkflowServiceBase):
    """Persist one exact action ownership correction across two work roots."""

    def _lifecycle_coordinator(self) -> ActionLifecycleCoordinator:
        return ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _completed_replay(
        self,
        operation_id: str | None,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        expected: ContentFingerprint,
        successor: PortiaRecord,
        transition_id: str,
        supersession_reason: str,
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
            if not _completed_ownership_matches(
                data,
                predecessor,
                destination_work,
                expected,
                successor,
                transition_id,
                supersession_reason,
            ):
                raise PortiaConflictError(
                    "completed action ownership operation identity is bound "
                    "to different intent"
                )
            return self._lifecycle_coordinator()._operation_support()._completed_result(
                operation_id,
                data,
            )
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing action ownership operation requires explicit #38 recovery"
            )
        return None

    def commit(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        supersession_reason: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        successor_validator: OwnershipSuccessorValidator,
        predecessor_factory: OwnershipPredecessorFactory,
        transition_factory: OwnershipTransitionFactory,
    ) -> OperationCommitResult:
        """Create the same logical action in a corrected work root atomically."""
        replay = self._completed_replay(
            operation_id,
            predecessor,
            destination_work,
            expected,
            successor,
            transition_id,
            supersession_reason,
        )
        if replay is not None:
            return replay

        source_work = predecessor.work_ref
        if source_work == destination_work:
            raise WorkflowOwnershipError(
                "action ownership correction requires two distinct work roots"
            )
        contract = predecessor.record_ref.record_kind
        require_action_owner(source_work, contract=contract)
        require_action_owner(destination_work, contract=contract)
        if predecessor.record_ref.contract_version != ACTION_VERSION:
            raise WorkflowOwnershipError(
                "action ownership correction requires an exact v1 predecessor"
            )
        if (
            successor.contract != contract
            or successor.contract_version != ACTION_VERSION
            or successor.class_id != destination_work.class_id
            or successor.work_id != destination_work.work_id
        ):
            raise WorkflowOwnershipError(
                "action ownership successor must belong to the destination work "
                "and preserve the selected family@1"
            )
        if successor.logical_id != predecessor.record_ref.record_id:
            raise WorkflowOwnershipError(
                "action ownership correction must preserve the selected logical ID"
            )

        prior = self.repository.load_work_record(
            source_work,
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
                "action ownership successor has no canonical identity"
            )
        try:
            self.repository.load_work_record(
                destination_work,
                contract,
                ACTION_VERSION,
                successor_id,
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "action ownership successor identity already exists in destination"
            )
        try:
            self.repository.load_work_record(
                source_work,
                "lifecycle_transition",
                "1",
                transition_id,
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "action ownership lifecycle transition identity already exists"
            )

        predecessor_candidate = predecessor_factory(prior.record, successor)
        transition = transition_factory(prior.record, predecessor_candidate)
        predecessor_target = record_target(source_work, predecessor_candidate)
        successor_target = record_target(destination_work, successor)
        transition_target = record_target(source_work, transition)
        for work in (source_work, destination_work):
            self.quarantine.require_allowed(work_target(work), "block_work_writes")
        for target in (
            predecessor_target,
            successor_target,
            transition_target,
        ):
            self.quarantine.require_allowed(target, "block_work_writes")

        successor_data = successor.to_dict()
        timestamp = successor_data.get("updated_at")
        initiated_by = successor_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "action ownership successor update provenance is incomplete"
            )
        digest = _ownership_intent_digest(
            source_work,
            destination_work,
            prior.record,
            predecessor_candidate,
            successor,
            transition,
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _cross_work_lock_plan(
            op_id,
            source_work,
            destination_work,
            timestamp,
        )

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor action changed during ownership preflight"
            )
        predecessor_id = prior.record.logical_id
        if predecessor_id is None:
            raise WorkflowOwnershipError(
                "selected predecessor action has no canonical identity"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            source_work,
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
                        destination_work,
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
                        source_work,
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
        candidates["step_predecessor"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_predecessor",
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
            operation_kind="correct_ownership",
        )
        plan["scope"] = "graph"
        lifecycle = self._lifecycle_coordinator()
        result = lifecycle._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )

        accepted_predecessor = self.repository.load_work_record(
            source_work,
            contract,
            ACTION_VERSION,
            predecessor.record_ref.record_id,
        )
        accepted_successor = self.repository.load_work_record(
            destination_work,
            contract,
            ACTION_VERSION,
            successor_id,
        )
        accepted_transition = self.repository.load_work_record(
            source_work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted_predecessor.record.to_dict() != predecessor_candidate.to_dict():
            raise PortiaCorruptionError(
                "committed action ownership predecessor does not match exact readback"
            )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaCorruptionError(
                "committed action ownership successor does not match exact readback"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "committed action ownership transition does not match exact readback"
            )
        return result
