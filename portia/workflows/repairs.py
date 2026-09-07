"""Production core workflow service for work-local ``repair@1`` records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, RepairV1
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaConflictError, PortiaNotFoundError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.action_common import ActionReadService
from portia.workflows.action_consolidation import ActionConsolidationCoordinator
from portia.workflows.action_reownership import ActionOwnershipCorrectionCoordinator
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import record_target, work_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.downstream_common import (
    DownstreamExactRecordResolution,
    DownstreamTargetResolution,
    DownstreamWorkflowAuthority,
    parse_explicit_timestamp,
    repair_reference,
    require_downstream_record_owner,
    require_timestamp_order,
)
from portia.workflows.downstream_lifecycle import (
    build_downstream_lifecycle_transition,
    require_coordinated_downstream_transition,
    require_downstream_lifecycle_reconciled,
)
from portia.workflows.downstream_supersession import (
    downstream_supersession_ancestry,
    downstream_supersession_reason_detail,
    downstream_supersession_topology,
    require_downstream_supersession_effective,
    require_downstream_work_root_correction_predecessor,
    require_duplicate_downstream_consolidation_predecessors,
    require_exact_downstream_correction_predecessor,
    require_material_repair_correction,
    superseded_downstream_predecessor,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.support_process_participants import (
    SupportProcessParticipantWorkflowService,
    support_process_participant_reference,
)

_REPAIR_FACILITATOR_CONTEXTS = frozenset(
    {"provider_or_collaborator", "coordinator"}
)
_CURRENT_UNIDENTIFIED_PERSON_KINDS = frozenset(
    {"unknown_person", "unidentified_person"}
)

_WORK_ROOT_PRESERVED_FACT_FIELDS = (
    "focus",
    "context_refs",
    "actions",
    "workflow_state",
    "completed_at",
    "creation_source",
)


_WORKFLOW_STATE_TRANSITIONS = {
    "planning": frozenset(
        {"active", "completed", "cancelled", "unable_to_complete"}
    ),
    "active": frozenset(
        {"completed", "cancelled", "unable_to_complete"}
    ),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "unable_to_complete": frozenset(),
}
_WORKFLOW_STATE_MUTABLE_FIELDS = frozenset(
    {
        "participants",
        "actions",
        "workflow_state",
        "completed_at",
        "updated_at",
        "updated_by",
    }
)
_PARTICIPATION_STATE_TRANSITIONS = {
    "invited": frozenset(
        {
            "agreed_to_participate",
            "participated",
            "declined",
            "unavailable",
            "withdrew",
            "not_applicable",
        }
    ),
    "agreed_to_participate": frozenset(
        {"participated", "unavailable", "withdrew", "not_applicable"}
    ),
    "participated": frozenset(),
    "declined": frozenset(),
    "unavailable": frozenset(),
    "withdrew": frozenset(),
    "not_applicable": frozenset(),
    "unknown": frozenset(
        {
            "invited",
            "agreed_to_participate",
            "participated",
            "declined",
            "unavailable",
            "withdrew",
            "not_applicable",
        }
    ),
}
_ACTION_STATE_TRANSITIONS = {
    "planned": frozenset(
        {"in_progress", "completed", "unable_to_complete", "withdrawn"}
    ),
    "in_progress": frozenset(
        {"completed", "unable_to_complete", "withdrawn"}
    ),
    "completed": frozenset(),
    "unable_to_complete": frozenset(),
    "withdrawn": frozenset(),
}
_PARTICIPANT_IMMUTABLE_FIELDS = frozenset(
    {"participant_key", "person", "roles"}
)
_ACTION_IMMUTABLE_FIELDS = frozenset(
    {
        "action_key",
        "action_type",
        "type_detail",
        "description",
        "agreed_by",
        "responsible_participant_keys",
        "agreed_at",
    }
)


@dataclass(frozen=True, slots=True)
class RepairContextResolution:
    """One exact Repair context dependency."""

    kind: str
    work: ExactPortiaWorkRef | None = None
    record: DownstreamExactRecordResolution | None = None


class RepairWorkflowService(ActionReadService):
    """Create and qualify exact teacher-local ``repair@1`` records."""

    CONTRACT = "repair"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )

    def _authority(self) -> DownstreamWorkflowAuthority:
        return DownstreamWorkflowAuthority(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _support_participant_service(
        self,
    ) -> SupportProcessParticipantWorkflowService:
        return SupportProcessParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    @staticmethod
    def _require_repair_record(
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> RepairV1:
        require_downstream_record_owner(work, record, contract="repair")
        if not isinstance(record, RepairV1):
            raise WorkflowOwnershipError(
                "Repair workflow requires repair@1 input"
            )
        return record

    @staticmethod
    def _require_creation_source(
        record: PortiaRecord,
        *,
        fresh_digital_write: bool,
        current_use: bool,
    ) -> None:
        source = record.field("creation_source")
        if not isinstance(source, Mapping):
            raise WorkflowOwnershipError("Repair creation_source is malformed")
        source_type = source.get("type")
        if fresh_digital_write and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Repair authoring accepts "
                "creation_source=digital_entry only"
            )
        if current_use and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "paper/import activation requires accepted review history"
            )

    @staticmethod
    def _require_chronology(record: PortiaRecord) -> None:
        require_timestamp_order(
            record.field("created_at"),
            record.field("updated_at"),
            earlier_name="Repair created_at",
            later_name="Repair updated_at",
        )

    def _require_facilitator_authority(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> StoredRecord | None:
        facilitator = record.field("facilitator")
        if not isinstance(facilitator, Mapping):
            raise WorkflowOwnershipError("Repair facilitator is malformed")
        authority = self._authority()

        if work.work_kind == "event":
            if facilitator.get("kind") != "represented_human":
                raise WorkflowOwnershipError(
                    "Event Repair facilitator must be represented_human"
                )
            authority.require_event_operational_human(
                facilitator.get("person"),
                field_name="Repair facilitator",
                require_current_use=require_current_use,
            )
            return None

        if facilitator.get("kind") != "support_process_participant":
            raise WorkflowOwnershipError(
                "Support Process Repair facilitator must be "
                "support_process_participant"
            )
        resolution = authority.require_support_process_operational_participant(
            work,
            facilitator.get("participant_ref"),
            field_name="Repair facilitator",
            allowed_contexts=_REPAIR_FACILITATOR_CONTEXTS,
            require_current_use=require_current_use,
        )
        return resolution.participant

    def _resolve_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> DownstreamTargetResolution:
        return self._authority().resolve_target(
            work,
            record.field("target"),
            require_current_use=require_current_use,
        )

    @staticmethod
    def _event_participant_identity(
        work: ExactPortiaWorkRef,
        raw_person: object,
        *,
        require_current_use: bool,
    ) -> tuple[object, ...] | None:
        if not isinstance(raw_person, Mapping):
            raise WorkflowOwnershipError("Repair participant person is malformed")
        if raw_person.get("kind") != "represented_human":
            raise WorkflowOwnershipError(
                "Event Repair participant must be represented_human"
            )
        person = raw_person.get("person")
        if not isinstance(person, Mapping):
            raise WorkflowOwnershipError("Repair participant person is malformed")
        kind = person.get("kind")
        if require_current_use and kind in _CURRENT_UNIDENTIFIED_PERSON_KINDS:
            raise WorkflowPrerequisiteError(
                "active Repair cannot use an unidentified participant"
            )
        if kind == "roster_student":
            roster_ref = person.get("roster_student_ref")
            if not isinstance(roster_ref, Mapping):
                raise WorkflowOwnershipError(
                    "Repair participant roster identity is malformed"
                )
            if roster_ref.get("class_id") != work.class_id:
                raise WorkflowOwnershipError(
                    "Repair participant roster identity must remain in the owning class"
                )
            return (
                "roster_student",
                roster_ref.get("class_id"),
                roster_ref.get("student_id"),
            )
        if kind == "actor":
            actor_ref = person.get("actor_ref")
            if not isinstance(actor_ref, Mapping):
                raise WorkflowOwnershipError(
                    "Repair participant Actor identity is malformed"
                )
            return ("actor", actor_ref.get("actor_id"))
        if kind == "local_operator":
            return None
        if kind in {
            "descriptive_person",
            "unknown_person",
            "unidentified_person",
        }:
            return None
        raise WorkflowOwnershipError(
            f"unsupported Repair participant person kind {kind!r}"
        )

    def _resolve_participants(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[frozenset[str], tuple[StoredRecord, ...]]:
        values = record.field("participants")
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Repair participants are malformed")

        keys: set[str] = set()
        strong_people: set[tuple[object, ...]] = set()
        support_records: list[StoredRecord] = []
        support_refs_seen: set[str] = set()
        support_service = self._support_participant_service()

        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"Repair participants[{index}] is malformed"
                )
            key = item.get("participant_key")
            if not isinstance(key, str):
                raise WorkflowOwnershipError(
                    f"Repair participants[{index}] participant_key is malformed"
                )
            if key in keys:
                raise WorkflowPrerequisiteError(
                    "Repair participant_key values must be unique"
                )
            keys.add(key)

            state = item.get("participation_state")
            if require_current_use and state == "unknown":
                raise WorkflowPrerequisiteError(
                    "active Repair cannot use unknown participation state"
                )

            person = item.get("person")
            if work.work_kind == "event":
                identity = self._event_participant_identity(
                    work,
                    person,
                    require_current_use=require_current_use,
                )
                if identity is not None:
                    if identity in strong_people:
                        raise WorkflowPrerequisiteError(
                            "Repair participants repeat the same logical human identity"
                        )
                    strong_people.add(identity)
                continue

            if not isinstance(person, Mapping):
                raise WorkflowOwnershipError(
                    "Repair participant person is malformed"
                )
            if person.get("kind") != "support_process_participant":
                raise WorkflowOwnershipError(
                    "Support Process Repair participant must reference a "
                    "Support Process Participant"
                )
            participant_ref = person.get("participant_ref")
            if not isinstance(participant_ref, Mapping):
                raise WorkflowOwnershipError(
                    "Repair Support Process Participant reference is malformed"
                )
            if (
                participant_ref.get("record_kind")
                != "support_process_participant"
                or participant_ref.get("contract_version") != "1"
            ):
                raise WorkflowOwnershipError(
                    "Repair participant must name exact "
                    "support_process_participant@1"
                )
            participant_id = participant_ref.get("record_id")
            if not isinstance(participant_id, str):
                raise WorkflowOwnershipError(
                    "Repair Support Process Participant reference is malformed"
                )
            if participant_id in support_refs_seen:
                raise WorkflowPrerequisiteError(
                    "Repair participants repeat the same Support Process Participant"
                )
            support_refs_seen.add(participant_id)
            reference = support_process_participant_reference(
                work,
                participant_id,
                version="1",
            )
            try:
                resolution = (
                    support_service.require_current_use(reference)
                    if require_current_use
                    else support_service.resolve_exact(reference)
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Repair participant Support Process Participant does not "
                    "resolve in the owning Support Process"
                ) from exc
            support_records.append(resolution.participant)

        return frozenset(keys), tuple(support_records)

    def _resolve_context_refs(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[RepairContextResolution, ...]:
        values = record.field("context_refs")
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Repair context_refs are malformed")

        logical_id = record.logical_id
        if not isinstance(logical_id, str):
            raise WorkflowOwnershipError("Repair logical identity is malformed")
        self_reference = repair_reference(work, logical_id)
        authority = self._authority()
        resolved: list[RepairContextResolution] = []

        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"Repair context_refs[{index}] is malformed"
                )
            kind = item.get("kind")
            if kind == "work":
                raw_work = item.get("work_ref")
                if not isinstance(raw_work, Mapping):
                    raise WorkflowOwnershipError(
                        "Repair context work reference is malformed"
                    )
                try:
                    work_reference = ExactPortiaWorkRef.from_dict(raw_work)
                except (TypeError, ValueError) as exc:
                    raise WorkflowOwnershipError(
                        "Repair context work reference is malformed"
                    ) from exc
                if work_reference.class_id != work.class_id:
                    raise WorkflowOwnershipError(
                        "Repair context must remain in the owning class"
                    )
                try:
                    authority.load_owner_exact(work_reference)
                except PortiaNotFoundError as exc:
                    raise WorkflowPrerequisiteError(
                        "Repair context work does not resolve"
                    ) from exc
                resolved.append(
                    RepairContextResolution(kind="work", work=work_reference)
                )
                continue

            if kind != "record":
                raise WorkflowOwnershipError(
                    f"unsupported Repair context kind {kind!r}"
                )
            raw_record = item.get("record_ref")
            if not isinstance(raw_record, Mapping):
                raise WorkflowOwnershipError(
                    "Repair context record reference is malformed"
                )
            try:
                record_reference = ExactPortiaWorkRecordRef.from_dict(raw_record)
            except (TypeError, ValueError) as exc:
                raise WorkflowOwnershipError(
                    "Repair context record reference is malformed"
                ) from exc
            if record_reference == self_reference:
                raise WorkflowPrerequisiteError(
                    "Repair context cannot reference the Repair itself"
                )
            exact = authority.resolve_exact_work_record(
                work,
                raw_record,
                field_name="Repair context",
                require_same_class=True,
                require_same_work=False,
            )
            resolved.append(
                RepairContextResolution(kind="record", record=exact)
            )

        return tuple(resolved)

    @staticmethod
    def _require_actions(
        record: PortiaRecord,
        participant_keys: frozenset[str],
    ) -> None:
        values = record.field("actions")
        if values is None:
            return
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Repair actions are malformed")

        action_keys: set[str] = set()
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"Repair actions[{index}] is malformed"
                )
            action_key = item.get("action_key")
            if not isinstance(action_key, str):
                raise WorkflowOwnershipError(
                    f"Repair actions[{index}] action_key is malformed"
                )
            if action_key in action_keys:
                raise WorkflowPrerequisiteError(
                    "Repair action_key values must be unique"
                )
            action_keys.add(action_key)

            agreed_by = item.get("agreed_by")
            if not isinstance(agreed_by, Sequence) or isinstance(
                agreed_by, (str, bytes, bytearray)
            ):
                raise WorkflowOwnershipError(
                    f"Repair actions[{index}] agreed_by is malformed"
                )
            for key in agreed_by:
                if not isinstance(key, str) or key not in participant_keys:
                    raise WorkflowPrerequisiteError(
                        "Repair action agreed_by must reference an existing "
                        "participant_key"
                    )

            responsible = item.get("responsible_participant_keys")
            if responsible is not None:
                if not isinstance(responsible, Sequence) or isinstance(
                    responsible, (str, bytes, bytearray)
                ):
                    raise WorkflowOwnershipError(
                        "Repair action responsible_participant_keys is malformed"
                    )
                for key in responsible:
                    if not isinstance(key, str) or key not in participant_keys:
                        raise WorkflowPrerequisiteError(
                            "Repair action responsible_participant_keys must "
                            "reference existing participant_key values"
                        )

            agreed_at = item.get("agreed_at")
            completed_at = item.get("completed_at")
            if agreed_at is not None and completed_at is not None:
                require_timestamp_order(
                    agreed_at,
                    completed_at,
                    earlier_name="Repair action agreed_at",
                    later_name="Repair action completed_at",
                )

    @staticmethod
    def _require_supersession_topology(record: PortiaRecord) -> None:
        if record.field("supersedes") is not None:
            downstream_supersession_topology(record)

    def _validate_existing(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[
        RepairV1,
        DownstreamTargetResolution,
        tuple[StoredRecord, ...],
        tuple[RepairContextResolution, ...],
        StoredRecord | None,
    ]:
        candidate = self._require_repair_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=require_current_use,
        )
        self._require_chronology(candidate)
        self._require_supersession_topology(candidate)
        facilitator = self._require_facilitator_authority(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        target = self._resolve_target(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        participant_keys, support_participants = self._resolve_participants(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        contexts = self._resolve_context_refs(work, candidate)
        self._require_actions(candidate, participant_keys)
        return (
            candidate,
            target,
            support_participants,
            contexts,
            facilitator,
        )

    def _require_current_dependency_quarantine(
        self,
        work: ExactPortiaWorkRef,
        target: DownstreamTargetResolution,
        support_participants: tuple[StoredRecord, ...],
        contexts: tuple[RepairContextResolution, ...],
        facilitator: StoredRecord | None,
    ) -> None:
        self.quarantine.require_allowed(
            work_target(work),
            "block_current_use",
        )
        for participant in target.participants:
            self.quarantine.require_allowed(
                record_target(work, participant.record),
                "block_current_use",
            )
        for participant in support_participants:
            self.quarantine.require_allowed(
                record_target(work, participant.record),
                "block_current_use",
            )
        if facilitator is not None:
            self.quarantine.require_allowed(
                record_target(work, facilitator.record),
                "block_current_use",
            )
        for context in contexts:
            if context.work is not None:
                self.quarantine.require_allowed(
                    work_target(context.work),
                    "block_current_use",
                )
            if context.record is not None:
                self.quarantine.require_allowed(
                    record_target(
                        context.record.reference.work_ref,
                        context.record.stored.record,
                    ),
                    "block_current_use",
                )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one fresh digital Repair identity after exact validation."""
        candidate = self._require_repair_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=True,
            current_use=False,
        )
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Repair must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Repair identity cannot establish supersession history"
            )

        self._require_chronology(candidate)
        require_current = candidate.status == "active"
        facilitator = self._require_facilitator_authority(
            work,
            candidate,
            require_current_use=require_current,
        )
        target = self._resolve_target(
            work,
            candidate,
            require_current_use=require_current,
        )
        participant_keys, support_participants = self._resolve_participants(
            work,
            candidate,
            require_current_use=require_current,
        )
        contexts = self._resolve_context_refs(work, candidate)
        self._require_actions(candidate, participant_keys)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, candidate),
            "block_work_writes",
        )
        if require_current:
            self._require_current_dependency_quarantine(
                work,
                target,
                support_participants,
                contexts,
                facilitator,
            )
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        return self.repository.create_work_record(work, candidate)

    def list_repairs(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> RepairV1:
        value = self._require_repair_record(work, candidate)
        require_coordinated_downstream_transition(prior, value)
        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=value.status == "active",
        )
        self._require_chronology(value)
        self._require_supersession_topology(value)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )

        facilitator = self._require_facilitator_authority(
            work,
            value,
            require_current_use=value.status == "active",
        )
        target = self._resolve_target(
            work,
            value,
            require_current_use=value.status == "active",
        )
        participant_keys, support_participants = self._resolve_participants(
            work,
            value,
            require_current_use=value.status == "active",
        )
        contexts = self._resolve_context_refs(work, value)
        self._require_actions(value, participant_keys)

        if value.status == "active":
            self._require_current_dependency_quarantine(
                work,
                target,
                support_participants,
                contexts,
                facilitator,
            )
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )
        return value

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
        """Persist one ordinary Repair activation or invalidation."""
        if (
            reference.record_ref.record_kind != "repair"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Repair lifecycle requires exact repair@1 reference"
            )
        work = reference.work_ref
        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

        def validate_transition(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            self._require_lifecycle_transition_candidate(
                work,
                prior,
                value,
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
                build_downstream_lifecycle_transition(
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
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> RepairV1:
        value = self._require_repair_record(work, successor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        if prior.status == "superseded":
            raise WorkflowPrerequisiteError(
                "Repair correction cannot reuse a superseded predecessor"
            )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Repair successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Repair predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Repair successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Repair successor updated_at cannot precede predecessor update"
            )
        require_material_repair_correction(
            prior,
            value,
            supersession_reason,
        )
        self._require_supersession_topology(value)

        facilitator = self._require_facilitator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(
            work,
            value,
            require_current_use=True,
        )
        participant_keys, support_participants = self._resolve_participants(
            work,
            value,
            require_current_use=True,
        )
        contexts = self._resolve_context_refs(work, value)
        self._require_actions(value, participant_keys)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )
        self._require_current_dependency_quarantine(
            work,
            target,
            support_participants,
            contexts,
            facilitator,
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_current_use",
        )
        return value

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
        """Create one corrected Repair successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "repair"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Repair correction requires exact repair@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_downstream_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = downstream_supersession_reason_detail(successor)

        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

        def validate_successor(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            self._require_correction_successor(
                work,
                prior,
                value,
                supersession_reason=supersession_reason,
            )

        result = coordinator.commit_correction(
            predecessor,
            successor,
            expected=expected,
            transition_id=transition_id,
            supersession_reason=supersession_reason,
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=validate_successor,
            predecessor_factory=superseded_downstream_predecessor,
            transition_factory=lambda prior, value: (
                build_downstream_lifecycle_transition(
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
        accepted_predecessor = self.load_exact(predecessor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            accepted_predecessor.record,
        )
        return result

    def _require_consolidation_successor(
        self,
        work: ExactPortiaWorkRef,
        priors: tuple[PortiaRecord, ...],
        successor: PortiaRecord,
    ) -> RepairV1:
        value = self._require_repair_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate Repair consolidation successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        self._require_supersession_topology(value)

        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Repair consolidation successor updated_at",
        )
        for prior in priors:
            self._require_repair_record(work, prior)
            require_downstream_lifecycle_reconciled(
                self.repository,
                work,
                prior,
            )
            if prior.status not in {"active", "invalidated"}:
                raise WorkflowPrerequisiteError(
                    "duplicate Repair consolidation predecessor must be "
                    "active or invalidated"
                )
            prior_updated = parse_explicit_timestamp(
                prior.field("updated_at"),
                field_name="Repair consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Repair consolidation successor updated_at cannot "
                    "precede a predecessor update"
                )

        # Duplication is an explicit human-selected lineage fact. Repair does
        # not infer duplicate identity from matching people, actions, or focus.
        facilitator = self._require_facilitator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(
            work,
            value,
            require_current_use=True,
        )
        participant_keys, support_participants = self._resolve_participants(
            work,
            value,
            require_current_use=True,
        )
        contexts = self._resolve_context_refs(work, value)
        self._require_actions(value, participant_keys)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )
        self._require_current_dependency_quarantine(
            work,
            target,
            support_participants,
            contexts,
            facilitator,
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_current_use",
        )
        return value

    def consolidate_duplicates(
        self,
        work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: Mapping[str, ContentFingerprint],
        transition_ids: Mapping[str, str],
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create one active canonical Repair from explicit duplicates."""
        predecessors = require_duplicate_downstream_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Repair consolidation requires one expected "
                "fingerprint for every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Repair consolidation requires one lifecycle "
                "transition ID for every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Repair consolidation lifecycle transition IDs "
                "must be unique"
            )

        coordinator = ActionConsolidationCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

        def validate_successor(
            priors: tuple[PortiaRecord, ...],
            value: PortiaRecord,
        ) -> None:
            self._require_consolidation_successor(
                work,
                priors,
                value,
            )

        def build_transition(
            prior: PortiaRecord,
            candidate: PortiaRecord,
            transition_id: str,
        ) -> PortiaRecord:
            return build_downstream_lifecycle_transition(
                self.repository,
                work,
                prior,
                candidate,
                transition_id=transition_id,
                reason_code="duplicate_consolidated",
                reason_detail=None,
                effective_at=effective_at,
                allow_supersession=True,
            )

        result = coordinator.commit(
            predecessors,
            successor,
            expected=tuple(
                expected[identifier] for identifier in predecessor_ids
            ),
            transition_ids=ordered_transition_ids,
            supersession_reason="duplicate_consolidated",
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=validate_successor,
            predecessor_factory=superseded_downstream_predecessor,
            transition_factory=build_transition,
        )
        for predecessor in predecessors:
            accepted = self.load_exact(predecessor)
            require_downstream_lifecycle_reconciled(
                self.repository,
                work,
                accepted.record,
            )
        return result

    @staticmethod
    def _work_root_participant_projection(
        record: PortiaRecord,
    ) -> dict[str, tuple[object, object]]:
        values = record.field("participants")
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Repair participants are malformed")
        projection: dict[str, tuple[object, object]] = {}
        for item in values:
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError("Repair participant is malformed")
            key = item.get("participant_key")
            if not isinstance(key, str):
                raise WorkflowOwnershipError(
                    "Repair participant_key is malformed"
                )
            projection[key] = (
                item.get("roles"),
                item.get("participation_state"),
            )
        return projection

    def _require_work_root_successor(
        self,
        source_work: ExactPortiaWorkRef,
        destination_work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> RepairV1:
        self._validate_existing(
            source_work,
            prior,
            require_current_use=False,
        )
        require_downstream_lifecycle_reconciled(
            self.repository,
            source_work,
            prior,
        )
        if prior.status not in {"active", "invalidated"}:
            raise WorkflowPrerequisiteError(
                "work-root Repair correction predecessor must be "
                "active or invalidated"
            )

        (
            value,
            target,
            support_participants,
            contexts,
            facilitator,
        ) = self._validate_existing(
            destination_work,
            successor,
            require_current_use=True,
        )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "work-root Repair correction successor must be active"
            )
        if prior.logical_id != value.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root Repair correction must preserve Repair ID"
            )

        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Repair work-root predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Repair work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Repair work-root successor updated_at cannot precede "
                "predecessor update"
            )

        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_FACT_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root Repair correction cannot rewrite fact "
                    f"{field}"
                )
        if self._work_root_participant_projection(
            prior
        ) != self._work_root_participant_projection(value):
            raise WorkflowPrerequisiteError(
                "work-root Repair correction cannot rewrite participant "
                "roles or participation state"
            )

        self.quarantine.require_allowed(
            work_target(source_work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(source_work, prior),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            work_target(destination_work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(destination_work, value),
            "block_work_writes",
        )
        self._require_current_dependency_quarantine(
            destination_work,
            target,
            support_participants,
            contexts,
            facilitator,
        )
        self.quarantine.require_allowed(
            record_target(destination_work, value),
            "block_current_use",
        )
        return value

    def correct_work_root(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Move one Repair representation to its corrected owning work root."""
        if (
            predecessor.record_ref.record_kind != "repair"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Repair work-root correction requires exact repair@1 "
                "predecessor"
            )
        source_work = require_downstream_work_root_correction_predecessor(
            destination_work,
            predecessor,
            successor,
        )
        reason_detail = downstream_supersession_reason_detail(successor)

        coordinator = ActionOwnershipCorrectionCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

        def validate_successor(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            self._require_work_root_successor(
                source_work,
                destination_work,
                prior,
                value,
            )

        result = coordinator.commit(
            predecessor,
            destination_work,
            successor,
            expected=expected,
            transition_id=transition_id,
            supersession_reason="work_root_corrected",
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=validate_successor,
            predecessor_factory=superseded_downstream_predecessor,
            transition_factory=lambda prior, candidate: (
                build_downstream_lifecycle_transition(
                    self.repository,
                    source_work,
                    prior,
                    candidate,
                    transition_id=transition_id,
                    reason_code="work_root_corrected",
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                    allow_supersession=True,
                )
            ),
        )
        accepted = self.load_exact(predecessor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            source_work,
            accepted.record,
        )
        return result

    @staticmethod
    def _keyed_progression_entries(
        record: PortiaRecord,
        *,
        field_name: str,
        key_name: str,
    ) -> dict[str, Mapping[str, object]]:
        values = record.field(field_name)
        if values is None:
            return {}
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError(
                f"Repair {field_name} are malformed"
            )
        entries: dict[str, Mapping[str, object]] = {}
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"Repair {field_name}[{index}] is malformed"
                )
            key = item.get(key_name)
            if not isinstance(key, str):
                raise WorkflowOwnershipError(
                    f"Repair {field_name}[{index}] {key_name} is malformed"
                )
            if key in entries:
                raise WorkflowPrerequisiteError(
                    f"Repair {key_name} values must be unique"
                )
            entries[key] = item
        return entries

    def _require_participant_progression(
        self,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        prior_entries = self._keyed_progression_entries(
            prior,
            field_name="participants",
            key_name="participant_key",
        )
        candidate_entries = self._keyed_progression_entries(
            candidate,
            field_name="participants",
            key_name="participant_key",
        )

        for key, prior_entry in prior_entries.items():
            candidate_entry = candidate_entries.get(key)
            if candidate_entry is None:
                raise WorkflowPrerequisiteError(
                    "Repair workflow progression cannot remove an existing "
                    "participant_key"
                )
            for field in _PARTICIPANT_IMMUTABLE_FIELDS:
                if prior_entry.get(field) != candidate_entry.get(field):
                    raise WorkflowPrerequisiteError(
                        "Repair workflow progression cannot rewrite participant "
                        f"field {field}"
                    )

            prior_state = prior_entry.get("participation_state")
            candidate_state = candidate_entry.get("participation_state")
            if not isinstance(prior_state, str) or not isinstance(
                candidate_state, str
            ):
                raise WorkflowOwnershipError(
                    "Repair participant participation_state is malformed"
                )
            if prior_state == candidate_state:
                continue
            allowed = _PARTICIPATION_STATE_TRANSITIONS.get(prior_state)
            if allowed is None or candidate_state not in allowed:
                raise WorkflowPrerequisiteError(
                    "illegal Repair participant-state transition: "
                    f"{prior_state} -> {candidate_state}"
                )

    def _require_action_progression(
        self,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        prior_entries = self._keyed_progression_entries(
            prior,
            field_name="actions",
            key_name="action_key",
        )
        candidate_entries = self._keyed_progression_entries(
            candidate,
            field_name="actions",
            key_name="action_key",
        )

        for key, prior_entry in prior_entries.items():
            candidate_entry = candidate_entries.get(key)
            if candidate_entry is None:
                raise WorkflowPrerequisiteError(
                    "Repair workflow progression cannot remove an existing action_key"
                )
            for field in _ACTION_IMMUTABLE_FIELDS:
                if prior_entry.get(field) != candidate_entry.get(field):
                    raise WorkflowPrerequisiteError(
                        "Repair workflow progression cannot rewrite agreed-action "
                        f"field {field}"
                    )

            prior_state = prior_entry.get("completion_state")
            candidate_state = candidate_entry.get("completion_state")
            if not isinstance(prior_state, str) or not isinstance(
                candidate_state, str
            ):
                raise WorkflowOwnershipError(
                    "Repair action completion_state is malformed"
                )
            if prior_state == candidate_state:
                if prior_entry.get("completed_at") != candidate_entry.get(
                    "completed_at"
                ):
                    raise WorkflowPrerequisiteError(
                        "Repair workflow progression cannot rewrite an existing "
                        "action completed_at fact"
                    )
                continue
            allowed = _ACTION_STATE_TRANSITIONS.get(prior_state)
            if allowed is None or candidate_state not in allowed:
                raise WorkflowPrerequisiteError(
                    "illegal Repair action-state transition: "
                    f"{prior_state} -> {candidate_state}"
                )

    def _require_workflow_state_candidate(
        self,
        reference: ExactPortiaWorkRecordRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> RepairV1:
        """Require one bounded same-identity Repair workflow progression."""
        work = reference.work_ref
        value = self._require_repair_record(work, candidate)

        if prior.logical_id != value.logical_id:
            raise WorkflowOwnershipError(
                "Repair workflow-state candidate changed exact record identity"
            )
        if prior.status != value.status:
            raise WorkflowPrerequisiteError(
                "ordinary Repair workflow-state progression cannot change "
                "canonical lifecycle"
            )
        if prior.status != "active":
            raise WorkflowPrerequisiteError(
                "ordinary Repair workflow-state progression requires active "
                "canonical status"
            )

        prior_state = prior.field("workflow_state")
        candidate_state = value.field("workflow_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowOwnershipError("Repair workflow_state is malformed")
        allowed = _WORKFLOW_STATE_TRANSITIONS.get(prior_state)
        if allowed is None or candidate_state not in allowed:
            raise WorkflowPrerequisiteError(
                "illegal Repair workflow_state transition: "
                f"{prior_state} -> {candidate_state}"
            )

        prior_data = prior.to_dict()
        candidate_data = value.to_dict()
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - _WORKFLOW_STATE_MUTABLE_FIELDS):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Repair workflow-state progression cannot rewrite "
                    f"field {field}"
                )

        self._require_participant_progression(prior, value)
        self._require_action_progression(prior, value)

        if candidate_state == "completed":
            parse_explicit_timestamp(
                value.field("completed_at"),
                field_name="Repair completed_at",
            )
        elif value.field("completed_at") is not None:
            raise WorkflowPrerequisiteError(
                "non-completed Repair workflow state cannot carry completed_at"
            )

        require_timestamp_order(
            prior.field("updated_at"),
            value.field("updated_at"),
            earlier_name="Repair prior updated_at",
            later_name="Repair updated_at",
        )

        (
            _,
            target,
            support_participants,
            contexts,
            facilitator,
        ) = self._validate_existing(
            work,
            value,
            require_current_use=True,
        )
        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )
        self._require_current_dependency_quarantine(
            work,
            target,
            support_participants,
            contexts,
            facilitator,
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_current_use",
        )
        return value

    def transition_workflow_state(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Persist one bounded ordinary Repair workflow-state progression."""
        if (
            reference.record_ref.record_kind != "repair"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Repair workflow progression requires exact repair@1 reference"
            )

        prior = self.load_exact(reference)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Repair state does not match canonical bytes"
            )

        self.require_current_use(reference)
        value = self._require_workflow_state_candidate(
            reference,
            prior.record,
            candidate,
        )
        return self.repository.replace_work_record(
            reference.work_ref,
            value,
            expected=expected,
        )

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Require one exact active Repair without following successors."""
        repair = self.load_exact(reference)
        require_downstream_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            repair.record,
        )
        candidate = self._require_repair_record(
            reference.work_ref,
            repair.record,
        )
        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=False,
        )
        self._require_chronology(candidate)
        self._require_supersession_topology(candidate)
        if candidate.status != "active":
            raise WorkflowPrerequisiteError(
                "current Repair use requires active canonical status"
            )

        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=True,
        )
        predecessors = downstream_supersession_ancestry(
            self.repository,
            reference.work_ref,
            candidate,
        )
        require_downstream_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(
                    predecessor.work_ref,
                    predecessor.stored.record,
                ),
                "block_current_use",
            )
        (
            _,
            target,
            support_participants,
            contexts,
            facilitator,
        ) = self._validate_existing(
            reference.work_ref,
            candidate,
            require_current_use=True,
        )
        self._require_current_dependency_quarantine(
            reference.work_ref,
            target,
            support_participants,
            contexts,
            facilitator,
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, candidate),
            "block_current_use",
        )
        return repair

    resolve_current = require_current_use
