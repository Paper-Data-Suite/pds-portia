"""Coordinated ordinary Account/Observation lifecycle persistence."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from portia.models import AccountV2, ObservationV2, PortiaRecord, parse_portia_record
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
from portia.workflows.account_relations import (
    account_relation_ancestry,
    account_relation_records,
    require_same_represented_source,
)
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.coordinated import EventBundleWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    ACCOUNT_READ_VERSIONS,
    ACCOUNT_VERSION,
    OBSERVATION_READ_VERSIONS,
    OBSERVATION_VERSION,
    evidence_target_records,
    require_basic_evidence_shape,
    require_digital_entry_creation,
    require_evidence_owner,
    require_evidence_record_owner,
    require_owner_current_eligibility,
    require_owner_write_eligibility,
    require_supported_evidence_version,
    require_targets_current_use,
)
from portia.workflows.evidence_artifacts import (
    evidence_validation_record,
    evidence_validation_records,
    require_source_artifact_authority,
)
from portia.workflows.evidence_lifecycle import (
    build_evidence_lifecycle_transition,
    evidence_lifecycle_state,
)
from portia.workflows.evidence_supersession import (
    correction_lifecycle_reason,
    require_exact_supersession_predecessor,
    require_material_correction,
    require_supersession_effective,
    superseded_predecessor,
    supersession_ancestry,
    supersession_records,
)


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


def _retraction_intent_digest(
    prior: PortiaRecord,
    predecessor_candidate: PortiaRecord,
    retraction: PortiaRecord,
    transition: PortiaRecord,
) -> str:
    payload = b"".join(
        canonical_json_bytes(record.to_dict())
        for record in (prior, predecessor_candidate, retraction, transition)
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


def _unique_stored(
    *groups: tuple[StoredRecord, ...],
) -> tuple[StoredRecord, ...]:
    seen: set[tuple[str, str, str | None]] = set()
    values: list[StoredRecord] = []
    for group in groups:
        for value in group:
            record = value.record
            key = (record.contract, record.contract_version, record.logical_id)
            if key in seen:
                continue
            seen.add(key)
            values.append(value)
    return tuple(values)


def _state_fact(name: str, value: str) -> dict[str, object]:
    return {"name": name, "kind": "token", "value": value}


def _expected_state(step: Mapping[str, object]) -> dict[str, object]:
    precondition = step.get("precondition")
    if not isinstance(precondition, Mapping):
        raise PortiaConflictError("lifecycle write step has no precondition")
    presence = precondition.get("presence")
    if presence == "must_be_absent":
        return {"presence": "must_be_absent"}
    if presence != "must_match":
        raise PortiaConflictError("lifecycle write precondition is unsupported")
    fingerprint = precondition.get("fingerprint")
    semantic_checks = precondition.get("semantic_checks")
    if not isinstance(fingerprint, Mapping) or not isinstance(semantic_checks, list):
        raise PortiaConflictError("lifecycle must-match precondition is incomplete")
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
    operation_kind: str = "transition_lifecycle",
) -> dict[str, object]:
    preflight: list[dict[str, object]] = []
    for step in steps:
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            raise PortiaConflictError("lifecycle intended result is invalid")
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
            raise PortiaConflictError("lifecycle write step is incomplete")
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
    targets = (
        ("operation", operation_target),
        ("work", work_target(work)),
    )
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
                "deployment_instance_id": "evidence_lifecycle",
                "process_instance_id": "evidence_lifecycle",
            },
        )
    return entries, records


def _completed_candidate_matches(
    journal_data: Mapping[str, object],
    reference: ExactPortiaWorkRecordRef,
    candidate: PortiaRecord,
) -> bool:
    target = {
        "kind": "work_record",
        "work_record_ref": reference.to_dict(),
    }
    candidate_fp = fingerprint_bytes(canonical_json_bytes(candidate.to_dict()))
    write_set = journal_data.get("write_set")
    if not isinstance(write_set, list):
        return False
    for step in write_set:
        if not isinstance(step, Mapping):
            continue
        if step.get("action") != "revision_aware_replace" or step.get("target") != target:
            continue
        intended = step.get("intended_result")
        if not isinstance(intended, Mapping):
            return False
        try:
            return ContentFingerprint.from_dict(intended.get("fingerprint")) == candidate_fp
        except ValueError:
            return False
    return False


def _completed_retraction_matches(
    journal_data: Mapping[str, object],
    predecessor: ExactPortiaWorkRecordRef,
    retraction: PortiaRecord,
    transition_id: str,
) -> bool:
    work = predecessor.work_ref
    retraction_target = record_target(work, retraction)
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
    retraction_fp = fingerprint_bytes(canonical_json_bytes(retraction.to_dict()))
    saw_retraction = False
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
        if action == "exclusive_create" and target == retraction_target:
            try:
                saw_retraction = (
                    ContentFingerprint.from_dict(intended.get("fingerprint"))
                    == retraction_fp
                )
            except ValueError:
                return False
        elif action == "exclusive_create" and target == transition_target:
            saw_transition = step.get("reason_code") == "source_retracted"
        elif action == "revision_aware_replace" and target == predecessor_target:
            selected = intended.get("selected_state")
            saw_predecessor = isinstance(selected, list) and _state_fact(
                "status", "retracted"
            ) in selected
    return saw_retraction and saw_transition and saw_predecessor


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


def _require_retraction_relation(
    predecessor: ExactPortiaWorkRecordRef,
    retraction: PortiaRecord,
) -> None:
    relations = retraction.to_dict().get("related_accounts")
    if not isinstance(relations, list) or len(relations) != 1:
        raise WorkflowPrerequisiteError(
            "source-evidenced retraction requires exactly one retracts relation"
        )
    relation = relations[0]
    if not isinstance(relation, dict) or relation.get("relation") != "retracts":
        raise WorkflowPrerequisiteError(
            "source-evidenced retraction requires relation = retracts"
        )
    reference = relation.get("account_ref")
    if not isinstance(reference, dict) or reference != predecessor.record_ref.to_dict():
        raise WorkflowOwnershipError(
            "retraction relation must name the exact selected predecessor Account"
        )


def _retracted_predecessor(
    prior: PortiaRecord,
    retraction: PortiaRecord,
) -> PortiaRecord:
    retraction_data = retraction.to_dict()
    updated_at = retraction_data.get("updated_at")
    updated_by = retraction_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "retraction Account update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "retracted"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record(prior.contract, prior.contract_version, data)


class EvidenceLifecycleCoordinator(WorkflowServiceBase):
    """Commit one ordinary evidence status transition through #38 machinery."""

    def _operation_support(self) -> EventBundleWorkflowService:
        # #40 already owns the shared operation-journal completion/partial-state
        # adapter over #38. Reuse it rather than manufacturing a second journal
        # or recovery implementation for evidence transitions.
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
                    "completed lifecycle operation identity is bound to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state not in {"staged"}:
            raise PortiaRecoveryRequiredError(
                "existing lifecycle operation requires explicit #38 recovery"
            )
        return None

    def _completed_retraction_replay(
        self,
        operation_id: str | None,
        predecessor: ExactPortiaWorkRecordRef,
        retraction: PortiaRecord,
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
            if not _completed_retraction_matches(
                data, predecessor, retraction, transition_id
            ):
                raise PortiaConflictError(
                    "completed retraction operation identity is bound to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state not in {"staged"}:
            raise PortiaRecoveryRequiredError(
                "existing retraction operation requires explicit #38 recovery"
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
                    "completed correction operation identity is bound to different intent"
                )
            return self._operation_support()._completed_result(operation_id, data)
        if state not in {"staged"}:
            raise PortiaRecoveryRequiredError(
                "existing correction operation requires explicit #38 recovery"
            )
        return None

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
    ) -> OperationCommitResult:
        work = reference.work_ref
        replay = self._completed_replay(operation_id, reference, candidate)
        if replay is not None:
            return replay

        if reference.record_ref.record_kind not in {"account", "observation"}:
            raise WorkflowOwnershipError(
                "evidence lifecycle transition requires Account or Observation reference"
            )
        if (
            candidate.contract != reference.record_ref.record_kind
            or candidate.contract_version != reference.record_ref.contract_version
            or candidate.logical_id != reference.record_ref.record_id
        ):
            raise WorkflowOwnershipError(
                "lifecycle candidate does not preserve the selected exact evidence identity"
            )
        prior = self.repository.load_work_record(
            work,
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected evidence state does not match selected canonical bytes"
            )
        require_evidence_record_owner(work, prior.record, contract=candidate.contract)
        require_evidence_record_owner(work, candidate, contract=candidate.contract)
        allow_relations = candidate.contract == "account"
        require_basic_evidence_shape(
            candidate,
            allow_related_accounts=allow_relations,
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        relation_records: tuple[StoredRecord, ...] = ()
        if candidate.contract == "account":
            relation_records = account_relation_ancestry(
                self.repository, work, candidate
            )
        supersession_history = supersession_ancestry(
            self.repository, work, candidate
        )

        owner = self.repository.load_work(work)
        require_owner_write_eligibility(work, owner.record)
        targets = evidence_target_records(self.repository, work, candidate)
        require_supersession_effective(supersession_history)
        if candidate.status == "active":
            require_source_artifact_authority(
                self.workspace_root,
                self.repository,
                candidate,
                require_current_use=True,
            )
            require_owner_current_eligibility(work, owner.record)
            require_targets_current_use(work, targets, quarantine=self.quarantine)
        transition = build_evidence_lifecycle_transition(
            self.repository,
            work,
            prior.record,
            candidate,
            transition_id=transition_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
        )
        lifecycle_history = evidence_lifecycle_state(
            self.repository, work, prior.record
        ).transitions
        graph = evidence_validation_records(
            (
                owner.record,
                *(stored.record for stored in targets),
                *(stored.record for stored in relation_records),
                *(stored.record for stored in supersession_history),
                candidate,
                *(stored.record for stored in lifecycle_history),
                transition,
            )
        )
        if candidate.status == "active":
            self.contexts.assemble(
                (
                    owner.record,
                    *(stored.record for stored in targets),
                    evidence_validation_record(candidate),
                ),
                require_actor_current_use=True,
            )
        self.validate_complete_graph(graph, require_actor_current_use=False)
        evidence_target = record_target(work, candidate)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(evidence_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        candidate_data = candidate.to_dict()
        timestamp = candidate_data.get("updated_at")
        initiated_by = candidate_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "lifecycle candidate update provenance is incomplete"
            )
        digest = _intent_digest(prior.record, candidate, transition)
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError("selected canonical evidence changed during preflight")
        if prior.record.logical_id is None:
            raise WorkflowOwnershipError("selected evidence has no canonical identity")
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            prior.record.contract,
            prior.record.logical_id,
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

        evidence_step = "step_evidence"
        candidate_bytes = canonical_json_bytes(candidate.to_dict())
        candidates[evidence_step] = candidate_bytes
        steps.append(
            {
                "step_id": evidence_step,
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "revision_aware_replace",
                "target": evidence_target,
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
            primary_target=evidence_target,
            affected_targets=[transition_target],
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
                    "operation identity is already bound to different lifecycle intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing lifecycle operation requires explicit #38 recovery"
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

    def commit_evidence_correction(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create a v2 corrected successor and supersede one exact predecessor."""
        work = predecessor.work_ref
        family = predecessor.record_ref.record_kind
        require_evidence_owner(work)
        if family not in {"account", "observation"}:
            raise WorkflowOwnershipError(
                "material evidence correction requires an Account or Observation predecessor"
            )
        supported = (
            ACCOUNT_READ_VERSIONS if family == "account" else OBSERVATION_READ_VERSIONS
        )
        require_supported_evidence_version(
            work,
            contract=family,
            version=predecessor.record_ref.contract_version,
            supported_versions=supported,
        )
        if family == "account":
            if not isinstance(successor, AccountV2):
                raise WorkflowOwnershipError(
                    "corrected Account successor must use account@2"
                )
        elif not isinstance(successor, ObservationV2):
            raise WorkflowOwnershipError(
                "corrected Observation successor must use observation@2"
            )
        require_evidence_record_owner(work, successor, contract=family)
        require_digital_entry_creation(successor)
        require_basic_evidence_shape(
            successor,
            allow_related_accounts=family == "account",
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        if successor.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "corrected successor must begin proposed or active"
            )
        supersession_reason = require_exact_supersession_predecessor(
            work, predecessor, successor
        )
        lifecycle_reason = correction_lifecycle_reason(supersession_reason)

        replay = self._completed_correction_replay(
            operation_id, predecessor, successor, transition_id
        )
        if replay is not None:
            return replay

        prior = self.repository.load_work_record(
            work,
            family,
            predecessor.record_ref.contract_version,
            predecessor.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor evidence state does not match selected canonical bytes"
            )
        if prior.record.status == "superseded":
            raise WorkflowPrerequisiteError(
                "material correction cannot supersede an already-superseded predecessor"
            )
        require_basic_evidence_shape(
            prior.record,
            allow_related_accounts=family == "account",
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        require_material_correction(
            prior.record, successor, supersession_reason
        )
        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError("corrected successor has no canonical identity")
        collection = (
            self.repository.list_accounts(work)
            if family == "account"
            else self.repository.list_observations(work)
        )
        if any(item.record.logical_id == successor_id for item in collection):
            raise PortiaConflictError("corrected successor identity already exists")
        try:
            self.repository.load_work_record(
                work, "lifecycle_transition", "1", transition_id
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "correction lifecycle transition identity already exists"
            )

        resolved_predecessors = supersession_records(
            self.repository, work, successor
        )
        if (
            len(resolved_predecessors) != 1
            or resolved_predecessors[0].record.logical_id
            != prior.record.logical_id
            or resolved_predecessors[0].record.contract_version
            != prior.record.contract_version
        ):
            raise WorkflowOwnershipError(
                "corrected successor did not resolve to the selected exact predecessor"
            )

        predecessor_candidate = superseded_predecessor(prior.record, successor)
        predecessor_ancestry = supersession_ancestry(
            self.repository, work, prior.record
        )
        owner = self.repository.load_work(work)
        require_owner_write_eligibility(work, owner.record)
        predecessor_targets = evidence_target_records(
            self.repository, work, predecessor_candidate
        )
        successor_targets = evidence_target_records(
            self.repository, work, successor
        )
        require_source_artifact_authority(
            self.workspace_root,
            self.repository,
            successor,
            require_current_use=successor.status == "active",
        )
        relation_records: tuple[StoredRecord, ...] = ()
        if family == "account":
            relation_records = account_relation_ancestry(
                self.repository, work, successor
            )
        if successor.status == "active":
            require_owner_current_eligibility(work, owner.record)
            require_targets_current_use(
                work, successor_targets, quarantine=self.quarantine
            )
            # Only the new current successor needs current Actor authority. The
            # historical predecessor and lineage records remain exact history.
            self.contexts.assemble(
                (
                    owner.record,
                    *(item.record for item in successor_targets),
                    evidence_validation_record(successor),
                ),
                require_actor_current_use=True,
            )

        transition = build_evidence_lifecycle_transition(
            self.repository,
            work,
            prior.record,
            predecessor_candidate,
            transition_id=transition_id,
            reason_code=lifecycle_reason,
            effective_at=effective_at,
            _allow_supersession=True,
        )
        lifecycle_history = evidence_lifecycle_state(
            self.repository, work, prior.record
        ).transitions
        target_records = _unique_stored(predecessor_targets, successor_targets)
        graph = evidence_validation_records(
            (
                owner.record,
                *(item.record for item in target_records),
                *(item.record for item in relation_records),
                *(item.record for item in predecessor_ancestry),
                predecessor_candidate,
                successor,
                *(item.record for item in lifecycle_history),
                transition,
            )
        )
        self.validate_complete_graph(graph, require_actor_current_use=False)

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
                "corrected successor update provenance is incomplete"
            )
        digest = _correction_intent_digest(
            prior.record, predecessor_candidate, successor, transition
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor evidence changed during correction preflight"
            )
        predecessor_id = prior.record.logical_id
        if predecessor_id is None:
            raise WorkflowOwnershipError(
                "selected predecessor evidence has no canonical identity"
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
                        self.workspace_root,
                        work,
                        family,
                        successor_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": (
                        ACCOUNT_VERSION if family == "account" else OBSERVATION_VERSION
                    ),
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
                "reason_code": lifecycle_reason,
            }
        )

        predecessor_bytes = canonical_json_bytes(predecessor_candidate.to_dict())
        candidates["step_evidence"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_evidence",
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
                    "contract_version": predecessor_candidate.contract_version,
                    "fingerprint": fingerprint_bytes(predecessor_bytes).to_dict(),
                    "selected_state": [_state_fact("status", "superseded")],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": lifecycle_reason,
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
            contract=family,
            operation_kind="activate_successor",
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
                    "operation identity is already bound to different correction intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing correction operation requires explicit #38 recovery"
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

    def commit_account_retraction(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        retraction: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str = "source_retracted",
        reason_detail: str | None = None,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create a same-source Account and retract its active predecessor."""
        work = predecessor.work_ref
        require_evidence_owner(work)
        require_supported_evidence_version(
            work,
            contract="account",
            version=predecessor.record_ref.contract_version,
            supported_versions=ACCOUNT_READ_VERSIONS,
        )
        if predecessor.record_ref.record_kind != "account":
            raise WorkflowOwnershipError(
                "source-evidenced retraction requires an Account predecessor"
            )
        if not isinstance(retraction, AccountV2):
            raise WorkflowOwnershipError("new retraction evidence must use account@2")
        require_evidence_record_owner(work, retraction, contract="account")
        require_digital_entry_creation(retraction)
        require_basic_evidence_shape(
            retraction,
            allow_related_accounts=True,
            allow_source_artifacts=True,
        )
        if retraction.status != "active":
            raise WorkflowPrerequisiteError(
                "source-evidenced retraction Account must be active"
            )
        if reason_code != "source_retracted":
            raise WorkflowPrerequisiteError(
                "Account retraction lifecycle reason must be source_retracted"
            )
        _require_retraction_relation(predecessor, retraction)

        replay = self._completed_retraction_replay(
            operation_id, predecessor, retraction, transition_id
        )
        if replay is not None:
            return replay

        prior = self.repository.load_work_record(
            work,
            "account",
            predecessor.record_ref.contract_version,
            predecessor.record_ref.record_id,
        )
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected predecessor Account state does not match selected canonical bytes"
            )
        if prior.record.status != "active":
            raise WorkflowPrerequisiteError(
                "Account retraction requires an active predecessor"
            )
        require_basic_evidence_shape(
            prior.record,
            allow_related_accounts=True,
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        predecessor_ancestry = supersession_ancestry(
            self.repository, work, prior.record
        )
        require_supersession_effective(predecessor_ancestry)
        if retraction.logical_id == prior.record.logical_id:
            raise WorkflowPrerequisiteError(
                "Account retraction must use a new canonical Account identity"
            )
        require_same_represented_source(retraction, prior.record)

        retraction_id = retraction.logical_id
        if retraction_id is None:
            raise WorkflowOwnershipError("retraction Account has no canonical identity")
        if any(
            stored.record.logical_id == retraction_id
            for stored in self.repository.list_accounts(work)
        ):
            raise PortiaConflictError("retraction Account identity already exists")
        try:
            self.repository.load_work_record(
                work, "lifecycle_transition", "1", transition_id
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError(
                "retraction lifecycle transition identity already exists"
            )

        # Resolve the direct relation against the still-active predecessor. This
        # proves exact same-work/version lineage and same represented source.
        direct_relations = account_relation_records(
            self.repository, work, retraction
        )
        if (
            len(direct_relations) != 1
            or direct_relations[0].record.logical_id != prior.record.logical_id
            or direct_relations[0].record.contract_version
            != prior.record.contract_version
        ):
            raise WorkflowOwnershipError(
                "retraction relation did not resolve to the selected predecessor"
            )
        relation_records = account_relation_ancestry(
            self.repository, work, retraction
        )

        predecessor_candidate = _retracted_predecessor(prior.record, retraction)
        owner = self.repository.load_work(work)
        require_owner_write_eligibility(work, owner.record)
        require_owner_current_eligibility(work, owner.record)
        predecessor_targets = evidence_target_records(
            self.repository, work, predecessor_candidate
        )
        retraction_targets = evidence_target_records(
            self.repository, work, retraction
        )
        require_source_artifact_authority(
            self.workspace_root,
            self.repository,
            retraction,
            require_current_use=True,
        )
        require_targets_current_use(
            work, retraction_targets, quarantine=self.quarantine
        )
        transition = build_evidence_lifecycle_transition(
            self.repository,
            work,
            prior.record,
            predecessor_candidate,
            transition_id=transition_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
            _allow_account_retraction=True,
        )
        lifecycle_history = evidence_lifecycle_state(
            self.repository, work, prior.record
        ).transitions
        target_records = _unique_stored(predecessor_targets, retraction_targets)
        predecessor_key = (
            predecessor_candidate.contract,
            predecessor_candidate.contract_version,
            predecessor_candidate.logical_id,
        )
        historical_ancestry = tuple(
            stored
            for stored in _unique_stored(relation_records, predecessor_ancestry)
            if (
                stored.record.contract,
                stored.record.contract_version,
                stored.record.logical_id,
            )
            != predecessor_key
        )
        graph = evidence_validation_records(
            (
                owner.record,
                *(stored.record for stored in target_records),
                *(stored.record for stored in historical_ancestry),
                predecessor_candidate,
                retraction,
                *(stored.record for stored in lifecycle_history),
                transition,
            )
        )
        # Only the new active retraction Account needs current Actor authority;
        # exact relation ancestry remains historical evidence.
        self.contexts.assemble(
            (
                owner.record,
                *(stored.record for stored in retraction_targets),
                evidence_validation_record(retraction),
            ),
            require_actor_current_use=True,
        )
        self.validate_complete_graph(graph, require_actor_current_use=False)

        predecessor_target = record_target(work, predecessor_candidate)
        retraction_target = record_target(work, retraction)
        transition_target = record_target(work, transition)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(predecessor_target, "block_work_writes")
        self.quarantine.require_allowed(retraction_target, "block_work_writes")
        self.quarantine.require_allowed(transition_target, "block_work_writes")

        retraction_data = retraction.to_dict()
        timestamp = retraction_data.get("updated_at")
        initiated_by = retraction_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "retraction Account update provenance is incomplete"
            )
        digest = _retraction_intent_digest(
            prior.record, predecessor_candidate, retraction, transition
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        prior_bytes = read_bytes(prior.path)
        if fingerprint_bytes(prior_bytes) != prior.fingerprint:
            raise PortiaConflictError(
                "selected predecessor Account changed during retraction preflight"
            )
        predecessor_id = prior.record.logical_id
        if predecessor_id is None:
            raise WorkflowOwnershipError(
                "selected predecessor Account has no canonical identity"
            )
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            "account",
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
                        "selected_state": [_state_fact("status", "active")],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": "preserve_prior_revision",
                }
            )

        retraction_bytes = canonical_json_bytes(retraction.to_dict())
        candidates["step_retraction"] = retraction_bytes
        steps.append(
            {
                "step_id": "step_retraction",
                "sequence": len(steps) + 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": retraction_target,
                "representation_role": "canonical_domain",
                "destination_path": workspace_relative(
                    self.workspace_root,
                    work_record_path(
                        self.workspace_root,
                        work,
                        "account",
                        retraction_id,
                    ),
                ),
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": ACCOUNT_VERSION,
                    "fingerprint": fingerprint_bytes(retraction_bytes).to_dict(),
                    "selected_state": [_state_fact("status", "active")],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": "source_retracted",
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
                        _state_fact("from_status", "active"),
                        _state_fact("to_status", "retracted"),
                    ],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": "source_retracted",
            }
        )

        predecessor_bytes = canonical_json_bytes(predecessor_candidate.to_dict())
        candidates["step_evidence"] = predecessor_bytes
        steps.append(
            {
                "step_id": "step_evidence",
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
                    "semantic_checks": [_state_fact("status", "active")],
                },
                "intended_result": {
                    "contract_version": predecessor_candidate.contract_version,
                    "fingerprint": fingerprint_bytes(predecessor_bytes).to_dict(),
                    "selected_state": [_state_fact("status", "retracted")],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": "source_retracted",
            }
        )

        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=timestamp,
            initiated_by=initiated_by,
            primary_target=predecessor_target,
            affected_targets=[retraction_target, transition_target],
            lock_entries=lock_entries,
            steps=steps,
            prior_status="active",
            candidate_status="retracted",
            contract="account",
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
                    "operation identity is already bound to different retraction intent"
                )
            if current_data.get("state") == "completed":
                return support._completed_result(op_id, current_data)
            if current_data.get("state") != "staged":
                raise PortiaRecoveryRequiredError(
                    "existing retraction operation requires explicit #38 recovery"
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
