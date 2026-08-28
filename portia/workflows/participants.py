"""Event-local Participant workflows with explicit person authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from portia.identity.roster import ResolvedRosterStudent
from portia.models import EventParticipantV3, PortiaRecord
from portia.models.references import (
    ExactActorRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.repository import StoredRecord
from portia.workflows.common import (
    CHILD_STATUS_TRANSITIONS,
    EVENT_VERSION,
    PARTICIPANT_VERSION,
    WorkflowServiceBase,
    participant_id_from_target,
    record_target,
    require_current_status,
    require_owned,
    require_revision_invariants,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


@dataclass(frozen=True, slots=True)
class ParticipantPersonResolution:
    """Exact Participant plus the authority for its explicit subject branch."""

    participant: StoredRecord
    kind: str
    authority: ResolvedRosterStudent | StoredRecord | None


def participant_reference(
    work: ExactPortiaWorkRef, participant_id: str, *, version: str = PARTICIPANT_VERSION
) -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id=participant_id,
            contract_version=version,
        ),
    )


class ParticipantWorkflowService(WorkflowServiceBase):
    """Manage Participants without merging Event-local or person identities."""

    def _require_write_input(
        self, work: ExactPortiaWorkRef, record: PortiaRecord
    ) -> EventParticipantV3:
        if work.work_kind != "event" or work.contract_version != EVENT_VERSION:
            raise WorkflowOwnershipError("Participant writes require an exact event@2 owner")
        if not isinstance(record, EventParticipantV3):
            raise WorkflowOwnershipError(
                "Participant workflow writes require event_participant@3 input"
            )
        require_owned(record, work)
        return record

    def _write_graph(
        self, work: ExactPortiaWorkRef, candidate: PortiaRecord
    ) -> tuple[PortiaRecord, ...]:
        event = self.repository.load_work(work).record
        existing = tuple(
            item.record
            for item in self.repository.list_event_participants(
                work, version=PARTICIPANT_VERSION
            )
            if item.record.logical_id != candidate.logical_id
        )
        return (event, *existing, candidate)

    @staticmethod
    def _subject_identity(record: PortiaRecord) -> tuple[object, ...]:
        subject = record.field("subject")
        if not isinstance(subject, Mapping) or not isinstance(subject.get("kind"), str):
            raise WorkflowOwnershipError("Participant subject is malformed")
        kind = subject["kind"]
        if kind == "roster_student":
            reference = RosterStudentRef.from_dict(subject.get("roster_student_ref"))
            return (kind, reference.class_id, reference.student_id)
        if kind == "actor":
            actor_ref = subject.get("actor_ref")
            actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
            if not isinstance(actor_id, str):
                raise WorkflowOwnershipError("Participant Actor reference is malformed")
            return (kind, actor_id)
        if kind in {"descriptive_person", "unknown_person"}:
            return (kind,)
        raise WorkflowOwnershipError("Participant subject kind is unsupported")

    def create(
        self, work: ExactPortiaWorkRef, record: PortiaRecord
    ) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        graph = self._write_graph(work, candidate)
        self.validate_complete_graph(
            graph, require_actor_current_use=candidate.status == "active"
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, candidate), "block_work_writes")
        return self.repository.create_work_record(work, candidate)

    def load_exact(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        if (
            reference.work_ref.work_kind != "event"
            or reference.work_ref.contract_version != EVENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Participant resolution requires an exact event@2 owner"
            )
        if reference.record_ref.record_kind != "event_participant":
            raise WorkflowOwnershipError("reference is not an Event Participant")
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "event_participant",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )

    def resolve_exact(
        self, reference: ExactPortiaWorkRecordRef
    ) -> ParticipantPersonResolution:
        """Resolve exact historical identity without applying current-use policy."""
        return self.resolve_person(reference, require_current_use=False)

    def replace(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        if candidate.logical_id is None:
            raise WorkflowOwnershipError("Participant has no exact identity")
        prior = self.load_exact(participant_reference(work, candidate.logical_id))
        require_revision_invariants(
            prior.record,
            candidate,
            transitions=CHILD_STATUS_TRANSITIONS,
        )
        if self._subject_identity(prior.record) != self._subject_identity(candidate):
            raise WorkflowOwnershipError(
                "persisted Participant person identity cannot be retargeted in place"
            )
        graph = self._write_graph(work, candidate)
        event = graph[0]
        if event.status in {"active", "closed"} and not any(
            record.contract == "event_participant" and record.status == "active"
            for record in graph[1:]
        ):
            raise WorkflowPrerequisiteError(
                f"{event.status} Event cannot lose its final active Participant"
            )
        if prior.record.status == "active" and candidate.status != "active":
            active_roles = tuple(
                stored.record
                for stored in self.repository.list_event_participant_roles(work)
                if stored.record.status == "active"
                and participant_id_from_target(stored.record) == (
                    candidate.logical_id,
                    PARTICIPANT_VERSION,
                )
            )
            if active_roles:
                raise WorkflowPrerequisiteError(
                    "active Participant cannot transition while active Roles still depend on it"
                )
        self.validate_complete_graph(
            graph, require_actor_current_use=candidate.status == "active"
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, candidate), "block_work_writes")
        return self.repository.replace_work_record(
            work, candidate, expected=expected
        )

    revise = replace

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        if work.work_kind != "event" or work.contract_version != EVENT_VERSION:
            raise WorkflowOwnershipError(
                "Participant listing requires an exact event@2 owner"
            )
        return self.repository.list_event_participants(
            work, version=PARTICIPANT_VERSION
        )

    list_participants = list

    def resolve_person(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        require_current_use: bool = False,
    ) -> ParticipantPersonResolution:
        participant = self.load_exact(reference)
        subject = participant.record.field("subject")
        if not isinstance(subject, Mapping) or not isinstance(subject.get("kind"), str):
            raise WorkflowOwnershipError("Participant subject is malformed")
        kind = subject["kind"]
        authority: ResolvedRosterStudent | StoredRecord | None
        if kind == "roster_student":
            roster_ref = RosterStudentRef.from_dict(subject.get("roster_student_ref"))
            authority = self.contexts.rosters.resolve_reference(roster_ref)
        elif kind == "actor":
            actor_ref = subject.get("actor_ref")
            actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
            if not isinstance(actor_id, str):
                raise WorkflowOwnershipError("Participant Actor reference is malformed")
            authority = self.contexts.actors.load_actor(
                ExactActorRef(actor_id=actor_id, contract_version="1"),
                require_current_use=require_current_use,
            )
        elif kind in {"descriptive_person", "unknown_person"}:
            authority = None
        else:
            raise WorkflowOwnershipError("Participant subject kind is unsupported")
        return ParticipantPersonResolution(participant, kind, authority)

    def require_current_use(
        self, reference: ExactPortiaWorkRecordRef
    ) -> ParticipantPersonResolution:
        if reference.record_ref.contract_version != PARTICIPANT_VERSION:
            raise WorkflowOwnershipError(
                "current Participant use requires event_participant@3"
            )
        return self._require_eligible(reference, allowed_event_statuses={"active"})

    def require_role_eligibility(
        self, reference: ExactPortiaWorkRecordRef
    ) -> ParticipantPersonResolution:
        """Require an active Participant under a draft or active Event for Role use."""
        return self._require_eligible(
            reference,
            allowed_event_statuses={"draft", "active"},
        )

    def _require_eligible(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        allowed_event_statuses: set[str],
    ) -> ParticipantPersonResolution:
        if reference.record_ref.contract_version != PARTICIPANT_VERSION:
            raise WorkflowOwnershipError(
                "current Participant use requires event_participant@3"
            )
        event = self.repository.load_work(reference.work_ref)
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        if event.record.status not in allowed_event_statuses:
            allowed = ", ".join(sorted(allowed_event_statuses))
            raise WorkflowPrerequisiteError(
                f"Participant use requires Event status in {{{allowed}}}"
            )
        participant = self.load_exact(reference)
        self.quarantine.require_allowed(
            record_target(reference.work_ref, participant.record), "block_current_use"
        )
        require_current_status(participant.record)
        return self.resolve_person(reference, require_current_use=True)

    resolve_current = require_current_use
