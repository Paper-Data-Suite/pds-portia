"""Workflow adapter over #38 coordinated staging, locks, and publication."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone

from portia.models import (
    EventParticipantRoleV3,
    EventParticipantV3,
    EventV2,
    PortiaRecord,
    WorkRelationshipV2,
    parse_portia_record,
)
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaConflictError,
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
    resolve_workspace_relative,
    work_manifest_path,
    work_record_path,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore, SeriesState
from portia.storage.staging import StagedArtifact, cleanup_staged
from portia.workflows.common import (
    PARTICIPANT_VERSION,
    WorkflowServiceBase,
    participant_id_from_target,
    record_target,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.events import event_reference
from portia.workflows.relationships import WorkRelationshipService, _endpoint
from portia.workflows.roles import RoleWorkflowService


@dataclass(frozen=True, slots=True)
class EventBundle:
    """One bounded teacher action proposed entirely in memory."""

    event: EventV2
    participants: tuple[EventParticipantV3, ...] = ()
    roles: tuple[EventParticipantRoleV3, ...] = ()
    relationships: tuple[WorkRelationshipV2, ...] = ()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _intent_digest(records: Sequence[PortiaRecord]) -> str:
    content = b"".join(canonical_json_bytes(record.to_dict()) for record in records)
    return hashlib.sha256(content).hexdigest()


class EventBundleWorkflowService(WorkflowServiceBase):
    """Validate a complete Event bundle before any canonical publication."""

    def _records_and_authorities(
        self, bundle: EventBundle, work: ExactPortiaWorkRef
    ) -> tuple[PortiaRecord, ...]:
        records: list[PortiaRecord] = [
            bundle.event,
            *bundle.participants,
            *bundle.roles,
            *bundle.relationships,
        ]
        proposed_work_keys: set[tuple[str, str, str, str]] = {
            (work.class_id, work.work_id, work.work_kind, work.contract_version)
        }
        proposed_record_keys = {
            (record.contract, record.contract_version, record.logical_id)
            for record in records
            if record.logical_id is not None
        }

        for participant in bundle.participants:
            if participant.class_id != work.class_id or participant.work_id != work.work_id:
                raise WorkflowOwnershipError("bundle Participant belongs to another Event")
        for role in bundle.roles:
            if role.class_id != work.class_id or role.work_id != work.work_id:
                raise WorkflowOwnershipError("bundle Role belongs to another Event")
            basis = role.field("basis")
            if isinstance(basis, tuple):
                for entry in basis:
                    if not isinstance(entry, Mapping) or entry.get("kind") not in {
                        "account_ref",
                        "observation_ref",
                    }:
                        continue
                    ref = entry.get("record_ref")
                    if not isinstance(ref, Mapping):
                        continue
                    kind = ref.get("record_kind")
                    identifier = ref.get("record_id")
                    version = ref.get("contract_version")
                    basis_key = (kind, version, identifier)
                    if (
                        basis_key not in proposed_record_keys
                        and isinstance(kind, str)
                        and isinstance(identifier, str)
                        and isinstance(version, str)
                    ):
                        records.append(
                            self.repository.load_work_record(
                                work, kind, version, identifier
                            ).record
                        )

        for relationship in bundle.relationships:
            source = _endpoint(relationship, "source")
            target = _endpoint(relationship, "target")
            if relationship.class_id != source.class_id or relationship.work_id != source.work_id:
                raise WorkflowOwnershipError(
                    "bundle relationship envelope disagrees with its exact source"
                )
            if source == target:
                raise WorkflowPrerequisiteError(
                    "a Work Relationship cannot draw context from itself"
                )
            for endpoint in (source, target):
                endpoint_key = (
                    endpoint.class_id,
                    endpoint.work_id,
                    endpoint.work_kind,
                    endpoint.contract_version,
                )
                if endpoint_key not in proposed_work_keys:
                    records.append(self.repository.load_work(endpoint).record)
                    proposed_work_keys.add(endpoint_key)
        return tuple(records)

    def _preflight_domain(
        self,
        bundle: EventBundle,
        work: ExactPortiaWorkRef,
        records: tuple[PortiaRecord, ...],
    ) -> None:
        self.validate_complete_graph(
            records,
            require_actor_current_use=any(
                record.status == "active" for record in bundle.participants
            ),
        )
        proposed_ids = {record.logical_id for record in bundle.participants}
        proposed_participant_keys = {
            (record.logical_id, record.contract_version)
            for record in bundle.participants
        }
        needs_existing_participants = not any(
            record.status == "active" for record in bundle.participants
        ) or any(
            participant_id_from_target(role) not in proposed_participant_keys
            for role in bundle.roles
            if role.status == "active"
        )
        if needs_existing_participants:
            try:
                existing_participants = self.repository.list_event_participants(
                    work, version=PARTICIPANT_VERSION
                )
            except PortiaNotFoundError:
                existing_participants = ()
        else:
            existing_participants = ()
        post_participants = (
            *(stored.record for stored in existing_participants if stored.record.logical_id not in proposed_ids),
            *bundle.participants,
        )
        if bundle.event.status in {"active", "closed"} and not any(
            record.status == "active" for record in post_participants
        ):
            raise WorkflowPrerequisiteError(
                f"{bundle.event.status} Event requires at least one valid active Participant"
            )
        participants_by_id = {
            (record.logical_id, record.contract_version): record
            for record in post_participants
        }
        for role in bundle.roles:
            if role.status != "active":
                continue
            if bundle.event.status not in {"draft", "active"}:
                raise WorkflowPrerequisiteError(
                    "active Role requires a draft or active parent Event"
                )
            participant_key = participant_id_from_target(role)
            participant = participants_by_id.get(participant_key)
            if participant is None or participant.status != "active":
                raise WorkflowPrerequisiteError(
                    "active Role requires its exact active Participant"
                )
        role_service = RoleWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        for role in bundle.roles:
            role_service._require_reported_involved_account(work, role)
        try:
            self.repository.load_work(work)
        except PortiaNotFoundError:
            pass
        else:
            for role in bundle.roles:
                role_service._require_active_compatibility(work, role)
            relationship_service = WorkRelationshipService(
                self.workspace_root,
                repository=self.repository,
                quarantine=self.quarantine,
                context_assembler=self.contexts,
            )
            for relationship in bundle.relationships:
                relationship_service._require_no_duplicate_edge(
                    _endpoint(relationship, "source"), relationship
                )

        relationship_service = WorkRelationshipService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        endpoint_records = {
            (
                record.class_id,
                record.work_id,
                record.work_kind or ("event" if record.contract == "event" else None),
                record.contract_version,
            ): record
            for record in records
            if record.contract in {"event", "support_process"}
        }
        for relationship in bundle.relationships:
            if relationship.status != "active":
                continue
            source = _endpoint(relationship, "source")
            target = _endpoint(relationship, "target")
            for position, endpoint in (("source", source), ("target", target)):
                endpoint_record = endpoint_records.get(
                    (
                        endpoint.class_id,
                        endpoint.work_id,
                        endpoint.work_kind,
                        endpoint.contract_version,
                    )
                )
                if endpoint_record is None:
                    raise WorkflowPrerequisiteError(
                        f"active Work Relationship {position} is absent"
                    )
                relationship_service._require_endpoint_eligibility(
                    endpoint_record, endpoint, position=position
                )

        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        if bundle.event.status == "active" or any(
            record.status == "active"
            for record in (*bundle.participants, *bundle.roles, *bundle.relationships)
        ):
            self.quarantine.require_allowed(work_target(work), "block_current_use")
        for record in (*bundle.participants, *bundle.roles, *bundle.relationships):
            owner = work if record.contract != "work_relationship" else _endpoint(record, "source")
            self.quarantine.require_allowed(work_target(owner), "block_work_writes")
            self.quarantine.require_allowed(record_target(owner, record), "block_work_writes")
            if record.status == "active":
                self.quarantine.require_allowed(
                    record_target(owner, record), "block_current_use"
                )

    def _journal_data(
        self,
        *,
        operation_id: str,
        intent_digest: str,
        timestamp: str,
        lock_entries: list[dict[str, object]],
        steps: list[dict[str, object]],
    ) -> dict[str, object]:
        targets = [step["target"] for step in steps]
        preflight: list[dict[str, object]] = []
        for step in steps:
            intended = step["intended_result"]
            if not isinstance(intended, dict):
                raise PortiaConflictError("operation intended result is invalid")
            preflight.append(
                {
                    "target": step["target"],
                    "representation_role": "canonical_domain",
                    "expected_state": step["precondition"],
                    "workspace_relative_path": step["destination_path"],
                    "contract_version": intended["contract_version"],
                    "source_basis": "canonical",
                    "source_projection": None,
                    "selected_state": intended["selected_state"],
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
            "operation_kind": "create_work",
            "intent_digest": intent_digest,
            "scope": "graph",
            "primary_target": targets[0],
            "affected_targets": targets[1:],
            "intent_facts": [
                {"name": "record_count", "kind": "integer", "value": len(steps)}
            ],
            "initiated_at": timestamp,
            "initiated_by": {
                "type": "system_process",
                "process_id": "workflow_bundle",
            },
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

    def _complete_journal(
        self,
        data: dict[str, object],
        current: SeriesState,
        result: OperationCommitResult,
        lock_records: Mapping[str, PortiaRecord],
    ) -> None:
        timestamp = _now()
        completed = deepcopy(data)
        current_revision = current.revision.to_dict().get("journal_revision")
        if not isinstance(current_revision, int):
            raise PortiaConflictError("selected operation journal revision is invalid")
        completed["journal_revision"] = current_revision + 1
        completed["previous_journal_revision"] = current_revision
        completed["state"] = "completed"
        accepted = dict(result.accepted_fingerprints)
        write_set = completed["write_set"]
        if not isinstance(write_set, list):
            raise PortiaConflictError("operation write set is invalid")
        for step in write_set:
            if not isinstance(step, dict):
                raise PortiaConflictError("operation write step is invalid")
            step_id = step.get("step_id")
            destination = step.get("destination_path")
            if not isinstance(step_id, str) or not isinstance(destination, str):
                raise PortiaConflictError("operation write step identity is invalid")
            fingerprint = accepted.get(step_id)
            if fingerprint is None:
                intended = step.get("intended_result")
                if not isinstance(intended, dict):
                    raise PortiaConflictError("operation intended result is invalid")
                fingerprint = ContentFingerprint.from_dict(intended.get("fingerprint"))
            step["disposition"] = "accepted"
            step["observed_result"] = {
                "workspace_relative_path": destination,
                "fingerprint": fingerprint.to_dict(),
                "observed_at": timestamp,
            }
        lock_set = completed["lock_set"]
        if not isinstance(lock_set, list):
            raise PortiaConflictError("operation lock set is invalid")
        for entry in lock_set:
            if not isinstance(entry, dict) or not isinstance(entry.get("lock_id"), str):
                raise PortiaConflictError("operation lock entry is invalid")
            lock_id = str(entry["lock_id"])
            lock_record = lock_records[lock_id]
            entry["disposition"] = "released"
            entry["fingerprint"] = fingerprint_bytes(
                canonical_json_bytes(lock_record.to_dict())
            ).to_dict()
            entry["acquired_at"] = timestamp
            entry["released_at"] = timestamp
        step_ids = [str(step["step_id"]) for step in write_set]
        completed["staged_artifacts"] = []
        completed["commit_point"] = {"reached": True, "reached_at": timestamp}
        completed["partial_state"] = {
            "durability_assessment": "confirmed",
            "accepted_steps": step_ids,
            "verified_steps": [],
            "durable_unverified_steps": [],
            "indeterminate_steps": [],
            "remaining_canonical_steps": [],
            "remaining_post_commit_steps": [],
            "current_pointer_changes": [],
            "held_or_possible_locks": [],
            "quarantined_targets": [],
            "active_finding_keys": [],
            "recommended_disposition": None,
        }
        completed["updated_at"] = timestamp
        completed_record = parse_portia_record(
            "operation_journal", "2", completed
        )
        pointer = self._pointer(operation_id=str(completed["operation_id"]), revision=current_revision + 1)
        OperationJournalStore(self.workspace_root).append(
            completed_record,
            pointer,
            expected_pointer=current.pointer_fingerprint,
        )

    def _record_partial_commit(
        self,
        data: dict[str, object],
        current: SeriesState,
        error: PortiaOperationPartialCommitError,
        lock_records: Mapping[str, PortiaRecord],
        staged: Sequence[StagedArtifact],
    ) -> None:
        timestamp = _now()
        partial = deepcopy(data)
        current_revision = current.revision.to_dict().get("journal_revision")
        if not isinstance(current_revision, int):
            raise PortiaRecoveryRequiredError(
                "partial operation journal revision cannot be selected"
            )
        partial["journal_revision"] = current_revision + 1
        partial["previous_journal_revision"] = current_revision
        partial["state"] = "failed"
        write_set = partial.get("write_set")
        if not isinstance(write_set, list):
            raise PortiaRecoveryRequiredError(
                "partial operation has no recoverable write set"
            )
        accepted = set(error.accepted_steps)
        remaining: list[str] = []
        for step in write_set:
            if not isinstance(step, dict):
                raise PortiaRecoveryRequiredError(
                    "partial operation has an invalid write step"
                )
            step_id = step.get("step_id")
            destination = step.get("destination_path")
            if not isinstance(step_id, str) or not isinstance(destination, str):
                raise PortiaRecoveryRequiredError(
                    "partial operation has an invalid write identity"
                )
            if step_id not in accepted:
                remaining.append(step_id)
                continue
            observed = fingerprint_bytes(
                read_bytes(
                    resolve_workspace_relative(self.workspace_root, destination)
                )
            )
            step["disposition"] = "accepted"
            step["observed_result"] = {
                "workspace_relative_path": destination,
                "fingerprint": observed.to_dict(),
                "observed_at": timestamp,
            }
        held = set(error.held_lock_ids)
        lock_set = partial.get("lock_set")
        if not isinstance(lock_set, list):
            raise PortiaRecoveryRequiredError(
                "partial operation has no recoverable lock set"
            )
        for entry in lock_set:
            if not isinstance(entry, dict) or not isinstance(entry.get("lock_id"), str):
                raise PortiaRecoveryRequiredError(
                    "partial operation has an invalid lock entry"
                )
            lock_id = str(entry["lock_id"])
            if lock_id not in held:
                continue
            entry["disposition"] = "acquired"
            entry["fingerprint"] = fingerprint_bytes(
                canonical_json_bytes(lock_records[lock_id].to_dict())
            ).to_dict()
            entry["acquired_at"] = timestamp
        steps_by_id = {
            str(step["step_id"]): step
            for step in write_set
            if isinstance(step, dict) and isinstance(step.get("step_id"), str)
        }
        staged_entries: list[dict[str, object]] = []
        for artifact in staged:
            step = steps_by_id[artifact.step_id]
            intended = step.get("intended_result")
            if not isinstance(intended, dict):
                raise PortiaRecoveryRequiredError(
                    "partial staged artifact has no intended result"
                )
            staged_entries.append(
                {
                    "step_id": artifact.step_id,
                    "staging_path": workspace_relative(
                        self.workspace_root, artifact.staging_path
                    ),
                    "destination_path": workspace_relative(
                        self.workspace_root, artifact.destination_path
                    ),
                    "contract_version": intended["contract_version"],
                    "fingerprint": artifact.fingerprint.to_dict(),
                    "staged_at": timestamp,
                    "validation_disposition": "valid",
                }
            )
        partial["staged_artifacts"] = staged_entries
        partial["commit_point"] = {"reached": True, "reached_at": timestamp}
        partial["partial_state"] = {
            "durability_assessment": "confirmed",
            "accepted_steps": list(error.accepted_steps),
            "verified_steps": list(error.accepted_steps),
            "durable_unverified_steps": [],
            "indeterminate_steps": [],
            "remaining_canonical_steps": remaining,
            "remaining_post_commit_steps": [],
            "current_pointer_changes": [],
            "held_or_possible_locks": list(error.held_lock_ids),
            "quarantined_targets": [],
            "active_finding_keys": [],
            "recommended_disposition": "require_manual_review",
        }
        partial["updated_at"] = timestamp
        partial_record = parse_portia_record("operation_journal", "2", partial)
        OperationJournalStore(self.workspace_root).append(
            partial_record,
            self._pointer(error.operation_id, current_revision + 1),
            expected_pointer=current.pointer_fingerprint,
        )

    def _completed_result(
        self,
        operation_id: str,
        current_data: Mapping[str, object],
    ) -> OperationCommitResult:
        completed_steps = current_data.get("write_set")
        if not isinstance(completed_steps, list):
            raise PortiaRecoveryRequiredError(
                "completed operation has no verifiable write set"
            )
        accepted: list[tuple[str, ContentFingerprint]] = []
        for step in completed_steps:
            if not isinstance(step, dict):
                raise PortiaRecoveryRequiredError(
                    "completed operation has an invalid write step"
                )
            intended = step.get("intended_result")
            destination = step.get("destination_path")
            step_id = step.get("step_id")
            if not isinstance(intended, dict):
                raise PortiaRecoveryRequiredError(
                    "completed operation intended result is invalid"
                )
            if not isinstance(destination, str) or not isinstance(step_id, str):
                raise PortiaRecoveryRequiredError(
                    "completed operation destination identity is invalid"
                )
            expected = ContentFingerprint.from_dict(intended["fingerprint"])
            try:
                observed = fingerprint_bytes(
                    read_bytes(
                        resolve_workspace_relative(self.workspace_root, destination)
                    )
                )
            except OSError as exc:
                raise PortiaRecoveryRequiredError(
                    f"completed operation destination is unavailable: {step_id}"
                ) from exc
            if observed != expected:
                raise PortiaRecoveryRequiredError(
                    f"completed operation destination changed: {step_id}"
                )
            accepted.append((step_id, expected))
        return OperationCommitResult(
            operation_id=operation_id,
            accepted_steps=tuple(step_id for step_id, _fp in accepted),
            accepted_fingerprints=tuple(accepted),
            acquired_lock_ids=(),
        )

    def commit(
        self,
        bundle: EventBundle,
        *,
        expected_event: ContentFingerprint | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Commit an all-create bundle through #38's canonical gate.

        An already-existing, byte-identical Event may anchor child creation when
        its exact expected fingerprint is supplied; the Event is then preflight
        context rather than a write step.
        """
        work = event_reference(bundle.event)
        records = self._records_and_authorities(bundle, work)
        self._preflight_domain(bundle, work, records)

        writes: list[tuple[PortiaRecord, ExactPortiaWorkRef]] = []
        try:
            existing_event = self.repository.load_work(work)
        except PortiaNotFoundError:
            if expected_event is not None:
                raise PortiaConflictError(
                    "expected Event state was supplied but the Event is absent"
                ) from None
            writes.append((bundle.event, work))
        else:
            if expected_event is None:
                replay_records: tuple[PortiaRecord, ...] = (
                    bundle.event,
                    *bundle.participants,
                    *bundle.roles,
                    *bundle.relationships,
                )
                replay_digest = _intent_digest(replay_records)
                replay_id = operation_id or f"op_{replay_digest}"
                try:
                    replay = OperationJournalStore(self.workspace_root).load_current(
                        replay_id
                    )
                except PortiaNotFoundError:
                    raise PortiaConflictError(
                        "existing Event requires an exact expected state"
                    ) from None
                replay_data = replay.revision.to_dict()
                if (
                    replay_data.get("intent_digest") != replay_digest
                    or replay_data.get("state") != "completed"
                ):
                    raise PortiaConflictError(
                        "existing Event does not identify a completed replay"
                    )
                return self._completed_result(replay_id, replay_data)
            if existing_event.fingerprint != expected_event:
                raise PortiaConflictError(
                    "existing Event does not match the bundle's expected state"
                )
            if existing_event.record.to_dict() != bundle.event.to_dict():
                raise PortiaConflictError(
                    "bundle Event bytes differ from the expected canonical Event"
                )
        writes.extend((record, work) for record in bundle.participants)
        writes.extend((record, work) for record in bundle.roles)
        writes.extend(
            (record, _endpoint(record, "source")) for record in bundle.relationships
        )
        if not writes:
            raise WorkflowPrerequisiteError("bundle contains no canonical writes")

        digest = _intent_digest(tuple(record for record, _owner in writes))
        op_id = operation_id or f"op_{digest}"
        operation_target: dict[str, object] = {
            "kind": "operation",
            "operation_ref": {"operation_id": op_id},
        }
        lock_targets: list[tuple[str, dict[str, object]]] = [
            ("operation", operation_target)
        ]
        owners = sorted(
            {owner for _record, owner in writes},
            key=lambda item: (item.class_id, item.work_id),
        )
        lock_targets.extend(("work", work_target(owner)) for owner in owners)

        timestamp = _now()
        lock_entries: list[dict[str, object]] = []
        lock_records: dict[str, PortiaRecord] = {}
        for sequence, (scope, target) in enumerate(lock_targets, start=1):
            lock_id = derive_lock_id(scope, target)
            lock_entries.append(
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
            lock_records[lock_id] = parse_portia_record(
                "operation_lock",
                "2",
                {
                    "schema_version": "2",
                    "record_type": "operation_lock",
                    "module_id": "portia",
                    "lock_id": lock_id,
                    "lock_scope": scope,
                    "protected_target": target,
                    "owning_operation": {"operation_id": op_id},
                    "acquired_at": timestamp,
                    "deployment_instance_id": "workflow_bundle",
                    "process_instance_id": "workflow_bundle",
                },
            )

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}
        for sequence, (record, owner) in enumerate(writes, start=1):
            step_id = f"step_{sequence}"
            content = canonical_json_bytes(record.to_dict())
            candidates[step_id] = content
            if record.contract == "event":
                target = work_target(owner)
                destination = work_manifest_path(self.workspace_root, owner)
            else:
                target = record_target(owner, record)
                if record.logical_id is None:
                    raise WorkflowOwnershipError("bundle record has no exact identity")
                destination = work_record_path(
                    self.workspace_root, owner, record.contract, record.logical_id
                )
            steps.append(
                {
                    "step_id": step_id,
                    "sequence": sequence,
                    "phase": "canonical_gate",
                    "action": "exclusive_create",
                    "target": target,
                    "representation_role": "canonical_domain",
                    "destination_path": workspace_relative(
                        self.workspace_root, destination
                    ),
                    "precondition": {"presence": "must_be_absent"},
                    "intended_result": {
                        "contract_version": record.contract_version,
                        "fingerprint": fingerprint_bytes(content).to_dict(),
                        "selected_state": (
                            [
                                {
                                    "name": "status",
                                    "kind": "token",
                                    "value": record.status,
                                }
                            ]
                            if record.status is not None
                            else []
                        ),
                    },
                    "disposition": "staged",
                    "observed_result": None,
                    "compensation_step_id": None,
                    "reason_code": None,
                }
            )
        journal_plan = self._journal_data(
            operation_id=op_id,
            intent_digest=digest,
            timestamp=timestamp,
            lock_entries=lock_entries,
            steps=steps,
        )
        journal_record = parse_portia_record(
            "operation_journal", "2", journal_plan
        )
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(op_id)
        except PortiaNotFoundError:
            current = store.create(journal_record, self._pointer(op_id, 1))
        else:
            current_data = current.revision.to_dict()
            if current_data.get("intent_digest") != digest:
                raise PortiaConflictError(
                    "operation identity is already bound to different bundle intent"
                )
            if current_data.get("state") == "completed":
                return self._completed_result(op_id, current_data)
            if current_data.get("state") not in {"staged", "recovering"}:
                raise PortiaConflictError(
                    "existing operation journal is not resumable by bundle commit"
                )
        staged = stage_journaled_candidates(
            self.workspace_root,
            journal_plan,
            candidates,
            fault_hook=fault_hook,
        )
        try:
            result = commit_journaled_candidates(
                self.workspace_root,
                journal_plan,
                staged,
                lock_records,
                fault_hook=fault_hook,
            )
        except PortiaOperationPartialCommitError as exc:
            self._record_partial_commit(
                journal_plan,
                current,
                exc,
                lock_records,
                staged,
            )
            raise
        self._complete_journal(journal_plan, current, result, lock_records)
        for artifact in staged:
            cleanup_staged(self.workspace_root, artifact)
        return result
