"""Shared same-work multi-predecessor action consolidation persistence."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef
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
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.workflows.action_common import ACTION_VERSION, require_action_owner
from portia.workflows.action_transition import (
    ActionLifecycleCoordinator,
    _journal_plan,
    _lock_plan,
    _state_fact,
)
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

ConsolidationSuccessorValidator = Callable[
    [tuple[PortiaRecord, ...], PortiaRecord], None
]
ConsolidationPredecessorFactory = Callable[[PortiaRecord, PortiaRecord], PortiaRecord]
ConsolidationTransitionFactory = Callable[
    [PortiaRecord, PortiaRecord, str], PortiaRecord
]


def _consolidation_intent_digest(
    priors: Sequence[PortiaRecord],
    predecessor_candidates: Sequence[PortiaRecord],
    successor: PortiaRecord,
    transitions: Sequence[PortiaRecord],
) -> str:
    ordered = [*priors, *predecessor_candidates, successor, *transitions]
    payload = b"".join(
        canonical_json_bytes(record.to_dict()) for record in ordered
    )
    return hashlib.sha256(payload).hexdigest()


def _completed_consolidation_matches(
    journal_data: Mapping[str, object],
    predecessors: Sequence[ExactPortiaWorkRecordRef],
    expected: Sequence[ContentFingerprint],
    successor: PortiaRecord,
    transition_ids: Sequence[str],
    supersession_reason: str,
) -> bool:
    if not predecessors or len(predecessors) != len(expected):
        return False
    if len(predecessors) != len(transition_ids):
        return False
    work = predecessors[0].work_ref
    successor_target = record_target(work, successor)
    successor_fp = fingerprint_bytes(canonical_json_bytes(successor.to_dict()))
    predecessor_targets = [
        {
            "kind": "work_record",
            "work_record_ref": reference.to_dict(),
        }
        for reference in predecessors
    ]
    transition_targets = [
        {
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
        for transition_id in transition_ids
    ]
    saw_successor = False
    saw_predecessors = [False] * len(predecessors)
    saw_transitions = [False] * len(transition_ids)
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
        if step.get("reason_code") != supersession_reason:
            if target != {"kind": "workspace"}:
                continue
        if action == "exclusive_create" and target == successor_target:
            try:
                saw_successor = (
                    ContentFingerprint.from_dict(intended.get("fingerprint"))
                    == successor_fp
                )
            except ValueError:
                return False
            continue
        for index, predecessor_target in enumerate(predecessor_targets):
            if action != "revision_aware_replace" or target != predecessor_target:
                continue
            precondition = step.get("precondition")
            if not isinstance(precondition, Mapping):
                return False
            try:
                expected_fp = ContentFingerprint.from_dict(
                    precondition.get("fingerprint")
                )
            except ValueError:
                return False
            selected = intended.get("selected_state")
            saw_predecessors[index] = (
                expected_fp == expected[index]
                and isinstance(selected, list)
                and _state_fact("status", "superseded") in selected
            )
            break
        for index, transition_target in enumerate(transition_targets):
            if action != "exclusive_create" or target != transition_target:
                continue
            selected = intended.get("selected_state")
            saw_transitions[index] = (
                isinstance(selected, list)
                and _state_fact("to_status", "superseded") in selected
            )
            break
    return saw_successor and all(saw_predecessors) and all(saw_transitions)


class ActionConsolidationCoordinator(WorkflowServiceBase):
    """Atomically persist one same-work multi-predecessor consolidation graph."""

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
        predecessors: Sequence[ExactPortiaWorkRecordRef],
        expected: Sequence[ContentFingerprint],
        successor: PortiaRecord,
        transition_ids: Sequence[str],
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
            if not _completed_consolidation_matches(
                data,
                predecessors,
                expected,
                successor,
                transition_ids,
                supersession_reason,
            ):
                raise PortiaConflictError(
                    "completed action consolidation operation identity is bound "
                    "to different intent"
                )
            return self._lifecycle_coordinator()._operation_support()._completed_result(
                operation_id,
                data,
            )
        if state != "staged":
            raise PortiaRecoveryRequiredError(
                "existing action consolidation operation requires explicit #38 recovery"
            )
        return None

    def commit(
        self,
        predecessors: Sequence[ExactPortiaWorkRecordRef],
        successor: PortiaRecord,
        *,
        expected: Sequence[ContentFingerprint],
        transition_ids: Sequence[str],
        supersession_reason: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        successor_validator: ConsolidationSuccessorValidator,
        predecessor_factory: ConsolidationPredecessorFactory,
        transition_factory: ConsolidationTransitionFactory,
    ) -> OperationCommitResult:
        """Create one successor and supersede every same-work predecessor."""
        references = tuple(predecessors)
        fingerprints = tuple(expected)
        transitions_requested = tuple(transition_ids)
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "action consolidation requires at least two predecessors"
            )
        if len(references) > 64:
            raise WorkflowPrerequisiteError(
                "action consolidation exceeds the 64-predecessor operation limit"
            )
        if len(references) != len(fingerprints):
            raise WorkflowPrerequisiteError(
                "action consolidation requires one expected fingerprint per predecessor"
            )
        if len(references) != len(transitions_requested):
            raise WorkflowPrerequisiteError(
                "action consolidation requires one lifecycle transition per predecessor"
            )
        if len(set(references)) != len(references):
            raise WorkflowPrerequisiteError(
                "action consolidation repeats a predecessor identity"
            )
        if len(set(transitions_requested)) != len(transitions_requested):
            raise WorkflowPrerequisiteError(
                "action consolidation lifecycle transition IDs must be unique"
            )

        replay = self._completed_replay(
            operation_id,
            references,
            fingerprints,
            successor,
            transitions_requested,
            supersession_reason,
        )
        if replay is not None:
            return replay

        first = references[0]
        work = first.work_ref
        contract = first.record_ref.record_kind
        require_action_owner(work, contract=contract)
        for reference in references:
            if reference.work_ref != work:
                raise WorkflowOwnershipError(
                    "action consolidation cannot cross owning works"
                )
            if (
                reference.record_ref.record_kind != contract
                or reference.record_ref.contract_version != ACTION_VERSION
            ):
                raise WorkflowOwnershipError(
                    "action consolidation requires one exact v1 record family"
                )
        if (
            successor.contract != contract
            or successor.contract_version != ACTION_VERSION
        ):
            raise WorkflowOwnershipError(
                "action consolidation successor must preserve the selected family@1"
            )

        priors = tuple(
            self.repository.load_work_record(
                work,
                contract,
                ACTION_VERSION,
                reference.record_ref.record_id,
            )
            for reference in references
        )
        for prior, fingerprint in zip(priors, fingerprints, strict=True):
            if prior.fingerprint != fingerprint:
                raise PortiaConflictError(
                    "expected predecessor action state does not match canonical bytes"
                )
        successor_validator(tuple(prior.record for prior in priors), successor)
        successor_id = successor.logical_id
        if successor_id is None:
            raise WorkflowOwnershipError(
                "consolidated action successor has no canonical identity"
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
                "consolidated action successor identity already exists"
            )
        for transition_id in transitions_requested:
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
                    "action consolidation lifecycle transition identity already exists"
                )

        predecessor_candidates = tuple(
            predecessor_factory(prior.record, successor) for prior in priors
        )
        transitions = tuple(
            transition_factory(prior.record, candidate, transition_id)
            for prior, candidate, transition_id in zip(
                priors,
                predecessor_candidates,
                transitions_requested,
                strict=True,
            )
        )
        predecessor_targets = [
            record_target(work, candidate) for candidate in predecessor_candidates
        ]
        successor_target = record_target(work, successor)
        transition_targets = [record_target(work, value) for value in transitions]
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        for target in [
            *predecessor_targets,
            successor_target,
            *transition_targets,
        ]:
            self.quarantine.require_allowed(target, "block_work_writes")

        successor_data = successor.to_dict()
        timestamp = successor_data.get("updated_at")
        initiated_by = successor_data.get("updated_by")
        if not isinstance(timestamp, str) or not isinstance(initiated_by, Mapping):
            raise WorkflowPrerequisiteError(
                "consolidated action successor update provenance is incomplete"
            )
        digest = _consolidation_intent_digest(
            [prior.record for prior in priors],
            predecessor_candidates,
            successor,
            transitions,
        )
        op_id = operation_id or f"op_{digest}"
        lock_entries, lock_records = _lock_plan(op_id, work, timestamp)

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        for index, prior in enumerate(priors, start=1):
            prior_bytes = read_bytes(prior.path)
            if fingerprint_bytes(prior_bytes) != prior.fingerprint:
                raise PortiaConflictError(
                    "selected predecessor action changed during consolidation preflight"
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
            step_id = f"step_history_{index:03d}"
            if history_path.exists():
                existing = read_bytes(history_path)
                if (
                    existing != prior_bytes
                    or fingerprint_bytes(existing) != prior.fingerprint
                ):
                    raise PortiaCorruptionError(
                        "technical storage-history collision"
                    )
            else:
                candidates[step_id] = prior_bytes
                steps.append(
                    {
                        "step_id": step_id,
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
                                _state_fact(
                                    "status",
                                    str(prior.record.status),
                                )
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

        for index, (transition, target, transition_id) in enumerate(
            zip(transitions, transition_targets, transitions_requested, strict=True),
            start=1,
        ):
            step_id = f"step_transition_{index:03d}"
            transition_bytes = canonical_json_bytes(transition.to_dict())
            candidates[step_id] = transition_bytes
            prior = priors[index - 1]
            steps.append(
                {
                    "step_id": step_id,
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": target,
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
                        "fingerprint": fingerprint_bytes(
                            transition_bytes
                        ).to_dict(),
                        "selected_state": [
                            _state_fact(
                                "from_status",
                                str(prior.record.status),
                            ),
                            _state_fact("to_status", "superseded"),
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": supersession_reason,
                }
            )

        for index, (prior, candidate, target) in enumerate(
            zip(priors, predecessor_candidates, predecessor_targets, strict=True),
            start=1,
        ):
            step_id = f"step_predecessor_{index:03d}"
            predecessor_bytes = canonical_json_bytes(candidate.to_dict())
            candidates[step_id] = predecessor_bytes
            steps.append(
                {
                    "step_id": step_id,
                    "sequence": len(steps) + 1,
                    "phase": "canonical_gate",
                    "action": "revision_aware_replace",
                    "target": target,
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
                        "fingerprint": fingerprint_bytes(
                            predecessor_bytes
                        ).to_dict(),
                        "selected_state": [
                            _state_fact("status", "superseded")
                        ],
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": supersession_reason,
                }
            )

        prior_statuses = {str(prior.record.status) for prior in priors}
        prior_status = (
            next(iter(prior_statuses)) if len(prior_statuses) == 1 else "mixed"
        )
        plan = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=timestamp,
            initiated_by=initiated_by,
            primary_target=successor_target,
            affected_targets=[*predecessor_targets, *transition_targets],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=prior_status,
            candidate_status="superseded",
            contract=contract,
            operation_kind="consolidate_duplicates",
        )
        lifecycle = self._lifecycle_coordinator()
        result = lifecycle._write_plan(
            plan=plan,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )

        for reference, candidate in zip(
            references,
            predecessor_candidates,
            strict=True,
        ):
            accepted = self.repository.load_work_record(
                work,
                contract,
                ACTION_VERSION,
                reference.record_ref.record_id,
            )
            if accepted.record.to_dict() != candidate.to_dict():
                raise PortiaCorruptionError(
                    "committed action consolidation predecessor does not match "
                    "exact readback"
                )
        accepted_successor = self.repository.load_work_record(
            work,
            contract,
            ACTION_VERSION,
            successor_id,
        )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaCorruptionError(
                "committed action consolidation successor does not match exact readback"
            )
        for transition, transition_id in zip(
            transitions,
            transitions_requested,
            strict=True,
        ):
            accepted = self.repository.load_work_record(
                work,
                "lifecycle_transition",
                "1",
                transition_id,
            )
            if accepted.record.to_dict() != transition.to_dict():
                raise PortiaCorruptionError(
                    "committed action consolidation transition does not match "
                    "exact readback"
                )
        return result
