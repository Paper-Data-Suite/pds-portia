"""Support Process Participant workflows with explicit person authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from portia.identity.roster import ResolvedRosterStudent
from portia.models import PortiaRecord, SupportProcessParticipantV1
from portia.models.references import (
    ExactActorRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import (
    WorkflowServiceBase,
    record_target,
    require_current_status,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.support_process_continuation import (
    support_process_continuation_ancestry,
)
from portia.workflows.support_process_initiation import (
    require_support_process_initiation_authority,
    validate_support_process_graph,
)
from portia.workflows.support_process_participant_lifecycle import (
    build_participant_lifecycle_transition,
    require_coordinated_participant_transition,
    require_participant_lifecycle_reconciled,
)
from portia.workflows.support_process_participant_supersession import (
    participant_supersession_ancestry,
    participant_supersession_reason_detail,
    require_exact_participant_correction_predecessor,
    require_material_participant_correction,
    require_participant_supersession_effective,
    superseded_participant_predecessor,
)
from portia.workflows.support_process_supersession import (
    support_process_supersession_ancestry,
)

SUPPORT_PROCESS_VERSION = "1"
SUPPORT_PROCESS_PARTICIPANT_VERSION = "1"
_AUTHORING_WORKFLOW_STATES = frozenset({"planning", "active", "paused"})


@dataclass(frozen=True, slots=True)
class SupportProcessParticipantPersonResolution:
    """Exact participant plus authority for its represented-human branch."""

    participant: StoredRecord
    kind: str
    authority: ResolvedRosterStudent | StoredRecord | None


def support_process_participant_reference(
    work: ExactPortiaWorkRef,
    participant_id: str,
    *,
    version: str = SUPPORT_PROCESS_PARTICIPANT_VERSION,
) -> ExactPortiaWorkRecordRef:
    """Build an exact Support Process Participant reference."""
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="support_process_participant",
            record_id=participant_id,
            contract_version=version,
        ),
    )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Support Process Participant {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Support Process Participant {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"Support Process Participant {field_name} timestamp lacks an "
            "explicit offset"
        )
    return parsed


def _person_kind(record: PortiaRecord) -> str:
    person = record.field("person")
    if not isinstance(person, Mapping):
        raise WorkflowOwnershipError("Support Process Participant person is malformed")
    kind = person.get("kind")
    if not isinstance(kind, str):
        raise WorkflowOwnershipError("Support Process Participant person is malformed")
    return kind


def _strong_person_identity(record: PortiaRecord) -> tuple[object, ...] | None:
    """Return only identities strong enough for deterministic duplicate checks."""
    person = record.field("person")
    if not isinstance(person, Mapping):
        raise WorkflowOwnershipError("Support Process Participant person is malformed")
    kind = _person_kind(record)
    if kind == "roster_student":
        reference = RosterStudentRef.from_dict(person.get("roster_student_ref"))
        return (kind, reference.class_id, reference.student_id)
    if kind == "actor":
        actor_ref = person.get("actor_ref")
        actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
        if not isinstance(actor_id, str):
            raise WorkflowOwnershipError(
                "Support Process Participant Actor reference is malformed"
            )
        return (kind, actor_id)
    if kind == "local_operator":
        return (kind,)
    if kind in {"descriptive_person", "unidentified_person"}:
        return None
    raise WorkflowOwnershipError(
        "Support Process Participant person kind is unsupported"
    )


def _has_context(record: PortiaRecord, context_kind: str) -> bool:
    contexts = record.field("contexts")
    if not isinstance(contexts, Sequence) or isinstance(contexts, (str, bytes)):
        raise WorkflowOwnershipError(
            "Support Process Participant contexts are malformed"
        )
    return any(
        isinstance(context, Mapping) and context.get("kind") == context_kind
        for context in contexts
    )


class SupportProcessParticipantWorkflowService(WorkflowServiceBase):
    """Author and resolve Support Process Participants without identity inference."""

    def _require_owner(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if (
            work.work_kind != "support_process"
            or work.contract_version != SUPPORT_PROCESS_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support Process Participant use requires exact support_process@1 owner"
            )
        return self.repository.load_work(work)

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportProcessParticipantV1:
        self._require_owner(work)
        if not isinstance(record, SupportProcessParticipantV1):
            raise WorkflowOwnershipError(
                "Support Process Participant writes require "
                "support_process_participant@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Support Process Participant does not belong to the selected "
                "Support Process"
            )
        return record

    def _existing_peers(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        return tuple(
            stored
            for stored in self.repository.list_work_records(
                work,
                "support_process_participant",
                version=SUPPORT_PROCESS_PARTICIPANT_VERSION,
            )
            if stored.record.logical_id != candidate.logical_id
        )

    def _write_graph(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
    ) -> tuple[PortiaRecord, ...]:
        owner = self._require_owner(work).record
        owner_ancestry = support_process_supersession_ancestry(
            self.repository,
            owner,
        )
        continuation = support_process_continuation_ancestry(
            self.repository,
            owner,
        )
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        peers = self._existing_peers(work, candidate)
        predecessors = participant_supersession_ancestry(
            self.repository,
            work,
            candidate,
        )
        predecessor_ids = {
            resolution.stored.record.logical_id
            for resolution in predecessors
        }
        return (
            *(stored.record for stored in owner_ancestry),
            *continuation_records,
            owner,
            *(
                stored.record
                for stored in peers
                if stored.record.logical_id not in predecessor_ids
            ),
            *(resolution.stored.record for resolution in predecessors),
            candidate,
        )

    def _require_authoring_owner(self, work: ExactPortiaWorkRef) -> StoredRecord:
        owner = self._require_owner(work)
        require_support_process_initiation_authority(
            self.workspace_root,
            self.repository,
            self.quarantine,
            self.contexts,
            owner.record,
        )
        if owner.record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "Support Process Participant authoring requires proposed or active "
                "canonical Support Process"
            )
        workflow_state = owner.record.field("workflow_state")
        if workflow_state not in _AUTHORING_WORKFLOW_STATES:
            raise WorkflowPrerequisiteError(
                "Support Process Participant authoring requires planning, active, "
                "or paused workflow state"
            )
        return owner

    @staticmethod
    def _require_fresh_digital_candidate(
        candidate: SupportProcessParticipantV1,
    ) -> None:
        if candidate.status != "proposed":
            raise WorkflowPrerequisiteError(
                "new Support Process Participant must begin proposed before activation"
            )
        creation_source = candidate.field("creation_source")
        source_type = (
            creation_source.get("type")
            if isinstance(creation_source, Mapping)
            else None
        )
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Support Process Participant authoring supports digital_entry only"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Support Process Participant creation cannot establish "
                "supersession history"
            )
        created_at = _parse_timestamp(
            candidate.field("created_at"), field_name="created_at"
        )
        updated_at = _parse_timestamp(
            candidate.field("updated_at"), field_name="updated_at"
        )
        if updated_at < created_at:
            raise WorkflowPrerequisiteError(
                "Support Process Participant updated_at cannot precede created_at"
            )

    @staticmethod
    def _require_active_digital_provenance(record: PortiaRecord) -> None:
        creation_source = record.field("creation_source")
        source_type = (
            creation_source.get("type")
            if isinstance(creation_source, Mapping)
            else None
        )
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "Support Process Participant activation currently requires "
                "digital_entry provenance; paper/import review history is deferred"
            )

    def _require_logical_person_unique(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
        *,
        excluded_ids: frozenset[str] = frozenset(),
    ) -> None:
        identity = _strong_person_identity(candidate)
        if identity is None:
            return
        for stored in self._existing_peers(work, candidate):
            if stored.record.logical_id in excluded_ids:
                continue
            if _strong_person_identity(stored.record) == identity:
                raise WorkflowPrerequisiteError(
                    "Support Process cannot contain duplicate logical human identity"
                )

    def _resolve_person_value(
        self,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[str, ResolvedRosterStudent | StoredRecord | None]:
        person = record.field("person")
        if not isinstance(person, Mapping):
            raise WorkflowOwnershipError(
                "Support Process Participant person is malformed"
            )
        kind = _person_kind(record)
        authority: ResolvedRosterStudent | StoredRecord | None
        if kind == "roster_student":
            reference = RosterStudentRef.from_dict(person.get("roster_student_ref"))
            authority = self.contexts.rosters.resolve_reference(reference)
        elif kind == "actor":
            actor_ref = person.get("actor_ref")
            actor_id = (
                actor_ref.get("actor_id")
                if isinstance(actor_ref, Mapping)
                else None
            )
            if not isinstance(actor_id, str):
                raise WorkflowOwnershipError(
                    "Support Process Participant Actor reference is malformed"
                )
            authority = self.contexts.actors.load_actor(
                ExactActorRef(actor_id=actor_id, contract_version="1"),
                require_current_use=require_current_use,
            )
        elif kind in {"local_operator", "descriptive_person"}:
            authority = None
        elif kind == "unidentified_person":
            if require_current_use:
                raise WorkflowPrerequisiteError(
                    "active current-use Support Process Participant cannot be "
                    "unidentified"
                )
            authority = None
        else:
            raise WorkflowOwnershipError(
                "Support Process Participant person kind is unsupported"
            )
        return kind, authority

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        self._require_authoring_owner(work)
        candidate = self._require_write_input(work, record)
        self._require_fresh_digital_candidate(candidate)
        self._require_logical_person_unique(work, candidate)
        self._resolve_person_value(candidate, require_current_use=False)
        validate_support_process_graph(
            self.contexts,
            self._write_graph(work, candidate),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def load_exact(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        work = reference.work_ref
        self._require_owner(work)
        if reference.record_ref.record_kind != "support_process_participant":
            raise WorkflowOwnershipError(
                "reference is not a Support Process Participant"
            )
        return self.repository.load_work_record(
            work,
            "support_process_participant",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        self._require_owner(work)
        return self.repository.list_work_records(
            work,
            "support_process_participant",
            version=SUPPORT_PROCESS_PARTICIPANT_VERSION,
        )

    list_participants = list

    def resolve_person(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        require_current_use: bool = False,
    ) -> SupportProcessParticipantPersonResolution:
        participant = self.load_exact(reference)
        kind, authority = self._resolve_person_value(
            participant.record,
            require_current_use=require_current_use,
        )
        return SupportProcessParticipantPersonResolution(
            participant=participant,
            kind=kind,
            authority=authority,
        )

    def resolve_exact(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> SupportProcessParticipantPersonResolution:
        """Resolve exactly the requested participant without successor following."""
        return self.resolve_person(reference, require_current_use=False)

    def require_activation_candidate(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportProcessParticipantV1:
        """Preflight one proposed->active participant candidate before persistence."""
        self._require_authoring_owner(work)
        candidate = self._require_write_input(work, record)
        if candidate.status != "active":
            raise WorkflowPrerequisiteError(
                "Participant activation candidate must have active canonical status"
            )
        self._require_logical_person_unique(work, candidate)
        self._require_active_digital_provenance(candidate)
        self._resolve_person_value(candidate, require_current_use=True)
        validate_support_process_graph(
            self.contexts,
            self._write_graph(work, candidate),
            require_actor_current_use=True,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_current_use"
        )
        return candidate

    def _require_owner_retains_supported_person(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
        *,
        excluded_ids: frozenset[str] = frozenset(),
    ) -> None:
        owner = self._require_owner(work)
        if owner.record.status != "active":
            return
        if candidate.status == "active" and has_supported_person_context(candidate):
            return
        if any(
            stored.record.logical_id not in excluded_ids
            and stored.record.status == "active"
            and has_supported_person_context(stored.record)
            for stored in self._existing_peers(work, candidate)
        ):
            return
        raise WorkflowPrerequisiteError(
            "active Support Process cannot lose its final active "
            "supported_person Participant"
        )

    def transition_lifecycle(
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
        """Persist one ordinary Participant activation/invalidation."""
        if reference.record_ref.record_kind != "support_process_participant":
            raise WorkflowOwnershipError(
                "reference is not a Support Process Participant"
            )
        work = reference.work_ref

        def validate_transition(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            require_coordinated_participant_transition(prior, value)
            if value.status == "active":
                self.require_activation_candidate(work, value)
                return
            self._require_authoring_owner(work)
            self._require_write_input(work, value)
            self._require_logical_person_unique(work, value)
            self._require_owner_retains_supported_person(work, value)
            validate_support_process_graph(
                self.contexts,
                self._write_graph(work, value),
            )
            self.quarantine.require_allowed(
                work_target(work), "block_work_writes"
            )
            self.quarantine.require_allowed(
                record_target(work, value), "block_work_writes"
            )

        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        result = coordinator.commit(
            reference,
            candidate,
            expected=expected,
            transition_id=transition_id,
            reason_code=reason_code,
            operation_id=operation_id,
            fault_hook=fault_hook,
            candidate_validator=validate_transition,
            transition_factory=lambda prior, value: (
                build_participant_lifecycle_transition(
                    self.repository,
                    work,
                    prior,
                    value,
                    transition_id=transition_id,
                    reason_code=reason_code,
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                )
            ),
        )
        accepted = self.load_exact(reference)
        require_participant_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def _correction_graph(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> tuple[PortiaRecord, ...]:
        owner = self._require_owner(work).record
        owner_ancestry = support_process_supersession_ancestry(
            self.repository,
            owner,
        )
        continuation = support_process_continuation_ancestry(
            self.repository,
            owner,
        )
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        superseded = superseded_participant_predecessor(prior, successor)
        excluded = {prior.logical_id, successor.logical_id}
        peers = tuple(
            stored.record
            for stored in self.repository.list_work_records(
                work,
                "support_process_participant",
                version=SUPPORT_PROCESS_PARTICIPANT_VERSION,
            )
            if stored.record.logical_id not in excluded
        )
        return (
            *(stored.record for stored in owner_ancestry),
            *continuation_records,
            owner,
            *peers,
            superseded,
            successor,
        )

    def _require_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> None:
        value = self._require_write_input(work, successor)
        require_participant_lifecycle_reconciled(self.repository, work, prior)
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            field_name="predecessor updated_at",
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            field_name="successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Participant successor updated_at cannot precede predecessor update"
            )
        require_material_participant_correction(
            prior,
            value,
            supersession_reason,
        )
        prior_id = prior.logical_id
        excluded_ids = (
            frozenset({prior_id})
            if isinstance(prior_id, str)
            else frozenset()
        )
        self._require_logical_person_unique(
            work,
            value,
            excluded_ids=excluded_ids,
        )
        self._require_owner_retains_supported_person(
            work,
            value,
            excluded_ids=excluded_ids,
        )
        self._resolve_person_value(
            value,
            require_current_use=value.status == "active",
        )
        validate_support_process_graph(
            self.contexts,
            self._correction_graph(work, prior, value),
            require_actor_current_use=value.status == "active",
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )
        if value.status == "active":
            owner = self._require_owner(work)
            if owner.record.status != "active":
                raise WorkflowPrerequisiteError(
                    "active corrected Participant requires active Support Process"
                )
            self._require_active_digital_provenance(value)
            self.quarantine.require_allowed(
                work_target(work),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )

    def correct(
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
        """Create a corrected Participant successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind
            != "support_process_participant"
            or predecessor.record_ref.contract_version
            != SUPPORT_PROCESS_PARTICIPANT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Participant correction requires exact "
                "support_process_participant@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_participant_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = participant_supersession_reason_detail(successor)
        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        result = coordinator.commit_correction(
            predecessor,
            successor,
            expected=expected,
            transition_id=transition_id,
            supersession_reason=supersession_reason,
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=lambda prior, value: self._require_successor_candidate(
                work,
                prior,
                value,
                supersession_reason=supersession_reason,
            ),
            predecessor_factory=superseded_participant_predecessor,
            transition_factory=lambda prior, value: (
                build_participant_lifecycle_transition(
                    self.repository,
                    work,
                    prior,
                    value,
                    transition_id=transition_id,
                    reason_code=supersession_reason,
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                    allow_supersession=True,
                )
            ),
        )
        accepted = self.load_exact(predecessor)
        require_participant_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def require_activation_eligibility(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> SupportProcessParticipantPersonResolution:
        """Require an already-active participant under a proposed/active process."""
        if (
            reference.record_ref.contract_version
            != SUPPORT_PROCESS_PARTICIPANT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Participant activation use requires support_process_participant@1"
            )
        owner = self._require_owner(reference.work_ref)
        require_support_process_initiation_authority(
            self.workspace_root,
            self.repository,
            self.quarantine,
            self.contexts,
            owner.record,
        )
        if owner.record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "Participant activation use requires proposed or active Support Process"
            )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        participant = self.load_exact(reference)
        require_participant_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            participant.record,
        )
        predecessors = participant_supersession_ancestry(
            self.repository,
            reference.work_ref,
            participant.record,
        )
        require_participant_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(
                    predecessor.work_ref,
                    predecessor.stored.record,
                ),
                "block_current_use",
            )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, participant.record),
            "block_current_use",
        )
        require_current_status(participant.record)
        self._require_active_digital_provenance(participant.record)
        return self.resolve_person(reference, require_current_use=True)

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> SupportProcessParticipantPersonResolution:
        if (
            reference.record_ref.contract_version
            != SUPPORT_PROCESS_PARTICIPANT_VERSION
        ):
            raise WorkflowOwnershipError(
                "current Participant use requires support_process_participant@1"
            )
        owner = self._require_owner(reference.work_ref)
        if owner.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Support Process Participant use requires active "
                "Support Process"
            )
        return self.require_activation_eligibility(reference)

    resolve_current = require_current_use


def has_supported_person_context(record: PortiaRecord) -> bool:
    """Return whether a participant explicitly carries supported_person context."""
    if not isinstance(record, SupportProcessParticipantV1):
        raise WorkflowOwnershipError(
            "supported-person context check requires support_process_participant@1"
        )
    return _has_context(record, "supported_person")
