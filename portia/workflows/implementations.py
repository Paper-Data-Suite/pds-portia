"""Support Process-local ``implementation@1`` occurrence workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from portia.models import ImplementationV1, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaConflictError, PortiaNotFoundError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.action_consolidation import ActionConsolidationCoordinator
from portia.workflows.action_reownership import ActionOwnershipCorrectionCoordinator
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import (
    WorkflowServiceBase,
    record_target,
    require_revision_invariants,
    work_target,
)
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.implementation_lifecycle import (
    build_implementation_lifecycle_transition,
    require_coordinated_implementation_transition,
    require_implementation_lifecycle_reconciled,
)
from portia.workflows.implementation_supersession import (
    implementation_supersession_ancestry,
    implementation_supersession_reason_detail,
    require_duplicate_implementation_consolidation_predecessors,
    require_exact_implementation_correction_predecessor,
    require_implementation_supersession_effective,
    require_implementation_work_root_correction_predecessor,
    require_material_implementation_correction,
    superseded_implementation_predecessor,
)
from portia.workflows.interventions import (
    InterventionWorkflowService,
    intervention_reference,
)
from portia.workflows.support_process_participants import (
    SupportProcessParticipantWorkflowService,
    support_process_participant_reference,
)
from portia.workflows.support_processes import SupportProcessWorkflowService
from portia.workflows.supports import SupportWorkflowService, support_reference

IMPLEMENTATION_VERSION = "1"
_IMPLEMENTATION_OWNER = ("support_process", "1")
_PLAN_KINDS = frozenset({"support", "intervention"})
_EXECUTION_STATE_TRANSITIONS = {
    "in_progress": frozenset(
        {"completed", "partially_completed", "unable_to_complete"}
    ),
}
_EXECUTION_STATE_MUTABLE_FIELDS = frozenset(
    {"execution_state", "ended_at", "updated_at", "updated_by"}
)
_NO_LIFECYCLE_TRANSITIONS: dict[str, frozenset[str]] = {}
_WORK_ROOT_PRESERVED_FACT_FIELDS = (
    "execution_state",
    "started_at",
    "ended_at",
    "variation",
    "summary",
)


def _require_implementation_owner(work: ExactPortiaWorkRef) -> None:
    if (work.work_kind, work.contract_version) != _IMPLEMENTATION_OWNER:
        raise WorkflowOwnershipError(
            "Implementation workflows require exact support_process@1 ownership"
        )


def implementation_reference(
    work: ExactPortiaWorkRef,
    implementation_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Support Process-local ``implementation@1`` reference."""
    _require_implementation_owner(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="implementation",
            record_id=implementation_id,
            contract_version=IMPLEMENTATION_VERSION,
        ),
    )


def _parse_timestamp(value: object, description: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} is not an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} is not an explicit timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(f"{description} lacks an explicit offset")
    return parsed


def _exact_local_ref(
    value: object,
    *,
    kinds: frozenset[str],
    field_name: str,
) -> ExactLocalRecordRef:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(
            f"Implementation {field_name} reference is malformed"
        )
    reference = ExactLocalRecordRef.from_dict(value)
    if reference.record_kind not in kinds or reference.contract_version != "1":
        allowed = " or ".join(f"{kind}@1" for kind in sorted(kinds))
        raise WorkflowOwnershipError(
            f"Implementation {field_name} must name exact {allowed}"
        )
    return reference


def _participant_refs_from_target(
    value: object,
    *,
    field_name: str,
) -> tuple[ExactLocalRecordRef, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"Implementation {field_name} is malformed")
    kind = value.get("kind")
    if kind == "support_process":
        return ()
    if kind == "support_process_participant":
        return (
            _exact_local_ref(
                value.get("record_ref"),
                kinds=frozenset({"support_process_participant"}),
                field_name=field_name,
            ),
        )
    if kind == "support_process_participants":
        targets = value.get("targets")
        if not isinstance(targets, Sequence) or isinstance(
            targets, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError(
                f"Implementation {field_name} participant set is malformed"
            )
        refs: list[ExactLocalRecordRef] = []
        for target in targets:
            if not isinstance(target, Mapping):
                raise WorkflowOwnershipError(
                    f"Implementation {field_name} participant entry is malformed"
                )
            refs.append(
                _exact_local_ref(
                    target.get("record_ref"),
                    kinds=frozenset({"support_process_participant"}),
                    field_name=field_name,
                )
            )
        return tuple(refs)
    raise WorkflowOwnershipError(
        f"unsupported Implementation {field_name} kind {kind!r}"
    )


def _participant_refs_from_provider(
    value: object,
) -> tuple[ExactLocalRecordRef, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Implementation provider is malformed")
    kind = value.get("kind")
    if kind == "no_human_provider":
        return ()
    if kind != "participants":
        raise WorkflowOwnershipError(
            f"unsupported Implementation provider kind {kind!r}"
        )
    refs = value.get("participant_refs")
    if not isinstance(refs, Sequence) or isinstance(
        refs, (str, bytes, bytearray)
    ):
        raise WorkflowOwnershipError(
            "Implementation provider participant_refs are malformed"
        )
    return tuple(
        _exact_local_ref(
            item,
            kinds=frozenset({"support_process_participant"}),
            field_name="provider participant",
        )
        for item in refs
    )


def _strong_person_identity(record: PortiaRecord) -> tuple[object, ...] | None:
    person = record.field("person")
    if not isinstance(person, Mapping):
        raise WorkflowOwnershipError(
            "Support Process Participant person is malformed"
        )
    kind = person.get("kind")
    if kind == "roster_student":
        reference = person.get("roster_student_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError(
                "Implementation roster participant is malformed"
            )
        return (kind, reference.get("class_id"), reference.get("student_id"))
    if kind == "actor":
        reference = person.get("actor_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError(
                "Implementation Actor participant is malformed"
            )
        return (kind, reference.get("actor_id"))
    if kind == "local_operator":
        return (kind,)
    if kind in {"descriptive_person", "unidentified_person"}:
        return None
    raise WorkflowOwnershipError(
        f"unsupported Implementation participant person kind {kind!r}"
    )


def _participant_identity(record: PortiaRecord) -> tuple[object, ...]:
    strong = _strong_person_identity(record)
    if strong is not None:
        return strong
    return ("participant_record", record.logical_id)


def _require_unique_logical_people(
    participants: Sequence[StoredRecord],
    *,
    description: str,
) -> None:
    identities = [_participant_identity(item.record) for item in participants]
    if len(identities) != len(set(identities)):
        raise WorkflowPrerequisiteError(
            f"Implementation {description} repeats a logical participant"
        )


def _has_variation_kind(record: PortiaRecord, kind: str) -> bool:
    variation = record.field("variation")
    if not isinstance(variation, Mapping):
        return False
    kinds = variation.get("kinds")
    if not isinstance(kinds, Sequence) or isinstance(
        kinds, (str, bytes, bytearray)
    ):
        raise WorkflowOwnershipError("Implementation variation is malformed")
    return kind in kinds


class ImplementationWorkflowService(WorkflowServiceBase):
    """Create and resolve exact teacher-local ``implementation@1`` occurrences."""

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

    def _root_service(self) -> SupportProcessWorkflowService:
        return SupportProcessWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _participant_service(self) -> SupportProcessParticipantWorkflowService:
        return SupportProcessParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _support_service(self) -> SupportWorkflowService:
        return SupportWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _intervention_service(self) -> InterventionWorkflowService:
        return InterventionWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> ImplementationV1:
        _require_implementation_owner(work)
        if not isinstance(record, ImplementationV1):
            raise WorkflowOwnershipError(
                "new Implementation writes require implementation@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Implementation does not belong to the explicitly selected "
                "Support Process"
            )
        source = record.field("creation_source")
        if not isinstance(source, Mapping):
            raise WorkflowOwnershipError("Implementation creation_source is malformed")
        source_type = source.get("type")
        if record.field("execution_state") == "unknown" and source_type != "import":
            raise WorkflowPrerequisiteError(
                "unknown execution_state is import-only"
            )
        if source_type in {"paper_capture", "import"} and record.status == "active":
            raise WorkflowPrerequisiteError(
                "paper/import activation requires accepted review history"
            )
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Implementation authoring accepts "
                "creation_source=digital_entry only"
            )
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "new digital Implementation identity must begin active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Implementation identity cannot establish supersession history"
            )

        started = _parse_timestamp(
            record.field("started_at"), "Implementation started_at"
        )
        ended_value = record.field("ended_at")
        if ended_value is not None:
            ended = _parse_timestamp(ended_value, "Implementation ended_at")
            if ended < started:
                raise WorkflowPrerequisiteError(
                    "Implementation ended_at cannot precede started_at"
                )
        created = _parse_timestamp(
            record.field("created_at"), "Implementation created_at"
        )
        if created < started:
            raise WorkflowPrerequisiteError(
                "Implementation created_at cannot precede started_at"
            )
        updated = _parse_timestamp(
            record.field("updated_at"), "Implementation updated_at"
        )
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Implementation updated_at cannot precede created_at"
            )
        return record

    def _resolve_plan(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        plan_ref = _exact_local_ref(
            record.field("plan_ref"),
            kinds=_PLAN_KINDS,
            field_name="plan_ref",
        )
        try:
            if plan_ref.record_kind == "support":
                return self._support_service().load_exact(
                    support_reference(work, plan_ref.record_id)
                )
            return self._intervention_service().load_exact(
                intervention_reference(work, plan_ref.record_id)
            )
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                "Implementation plan ref does not resolve in owning Support Process"
            ) from exc

    def _resolve_participants(
        self,
        work: ExactPortiaWorkRef,
        refs: Sequence[ExactLocalRecordRef],
        *,
        current: bool,
        description: str,
    ) -> tuple[StoredRecord, ...]:
        service = self._participant_service()
        resolved: list[StoredRecord] = []
        for ref in refs:
            exact = support_process_participant_reference(work, ref.record_id)
            try:
                if current:
                    stored = service.require_current_use(exact).participant
                else:
                    stored = service.load_exact(exact)
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    f"Implementation {description} does not resolve in owning "
                    "Support Process"
                ) from exc
            resolved.append(stored)
        return tuple(resolved)

    def _resolve_actual_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        current: bool,
    ) -> tuple[StoredRecord, ...]:
        refs = _participant_refs_from_target(
            record.field("actual_target"),
            field_name="actual target",
        )
        participants = self._resolve_participants(
            work,
            refs,
            current=current,
            description="actual target",
        )
        _require_unique_logical_people(participants, description="actual target set")
        return participants

    def _resolve_actual_provider(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        current: bool,
    ) -> tuple[StoredRecord, ...]:
        refs = _participant_refs_from_provider(
            record.field("implementation_provider")
        )
        participants = self._resolve_participants(
            work,
            refs,
            current=current,
            description="provider Participant ref",
        )
        _require_unique_logical_people(participants, description="provider set")
        return participants

    def _resolve_plan_target(
        self,
        work: ExactPortiaWorkRef,
        plan: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        refs = _participant_refs_from_target(
            plan.field("target"),
            field_name="plan target",
        )
        participants = self._resolve_participants(
            work,
            refs,
            current=False,
            description="plan target",
        )
        _require_unique_logical_people(participants, description="plan target set")
        return participants

    def _resolve_plan_provider(
        self,
        work: ExactPortiaWorkRef,
        plan: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        provider = plan.field("provider_plan")
        if not isinstance(provider, Mapping):
            raise WorkflowOwnershipError("Implementation plan provider is malformed")
        kind = provider.get("kind")
        if kind == "no_assigned_provider":
            return ()
        if kind != "assigned":
            raise WorkflowOwnershipError(
                f"unsupported Implementation plan provider kind {kind!r}"
            )
        refs = provider.get("participant_refs")
        if not isinstance(refs, Sequence) or isinstance(
            refs, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError(
                "Implementation plan provider participant_refs are malformed"
            )
        parsed = tuple(
            _exact_local_ref(
                item,
                kinds=frozenset({"support_process_participant"}),
                field_name="plan provider participant",
            )
            for item in refs
        )
        participants = self._resolve_participants(
            work,
            parsed,
            current=False,
            description="plan provider Participant ref",
        )
        _require_unique_logical_people(participants, description="plan provider set")
        return participants

    @staticmethod
    def _target_signature(
        target: object,
        participants: Sequence[StoredRecord],
    ) -> tuple[object, ...]:
        if not isinstance(target, Mapping):
            raise WorkflowOwnershipError("Implementation target is malformed")
        if target.get("kind") == "support_process":
            return ("support_process",)
        identities = frozenset(
            _participant_identity(item.record) for item in participants
        )
        return ("participants", identities)

    @staticmethod
    def _provider_signature(
        provider: object,
        participants: Sequence[StoredRecord],
        *,
        plan: bool,
    ) -> tuple[object, ...]:
        if not isinstance(provider, Mapping):
            raise WorkflowOwnershipError("Implementation provider is malformed")
        kind = provider.get("kind")
        no_provider_kind = "no_assigned_provider" if plan else "no_human_provider"
        if kind == no_provider_kind:
            return ("no_human_provider",)
        expected_kind = "assigned" if plan else "participants"
        if kind != expected_kind:
            raise WorkflowOwnershipError(
                f"unsupported Implementation provider kind {kind!r}"
            )
        identities = frozenset(
            _participant_identity(item.record) for item in participants
        )
        return ("participants", identities)

    def _require_plan_actual_alignment(
        self,
        record: PortiaRecord,
        plan: PortiaRecord,
        *,
        actual_target: Sequence[StoredRecord],
        actual_provider: Sequence[StoredRecord],
        plan_target: Sequence[StoredRecord],
        plan_provider: Sequence[StoredRecord],
    ) -> None:
        actual_target_signature = self._target_signature(
            record.field("actual_target"), actual_target
        )
        plan_target_signature = self._target_signature(
            plan.field("target"), plan_target
        )
        if (
            actual_target_signature != plan_target_signature
            and not _has_variation_kind(record, "target")
        ):
            raise WorkflowPrerequisiteError(
                "target variation is required when actual target differs from plan"
            )

        actual_provider_signature = self._provider_signature(
            record.field("implementation_provider"),
            actual_provider,
            plan=False,
        )
        plan_provider_signature = self._provider_signature(
            plan.field("provider_plan"),
            plan_provider,
            plan=True,
        )
        if (
            actual_provider_signature != plan_provider_signature
            and not _has_variation_kind(record, "provider")
        ):
            raise WorkflowPrerequisiteError(
                "provider variation is required when actual provider differs from plan"
            )

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        """Record one explicit actual occurrence without mutating its exact plan."""
        candidate = self._require_write_input(work, record)
        self._root_service().require_current_use(work)
        plan = self._resolve_plan(work, candidate)
        actual_target = self._resolve_actual_target(
            work, candidate, current=True
        )
        actual_provider = self._resolve_actual_provider(
            work, candidate, current=True
        )
        plan_target = self._resolve_plan_target(work, plan.record)
        plan_provider = self._resolve_plan_provider(work, plan.record)
        self._require_plan_actual_alignment(
            candidate,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def _require_existing_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> ImplementationV1:
        _require_implementation_owner(work)
        if not isinstance(record, ImplementationV1):
            raise WorkflowOwnershipError(
                "Implementation current authority requires implementation@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Implementation does not belong to the selected Support Process"
            )
        source = record.field("creation_source")
        if not isinstance(source, Mapping) or source.get("type") != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Implementation current authority requires "
                "digital_entry materialization"
            )
        started = _parse_timestamp(
            record.field("started_at"), "Implementation started_at"
        )
        ended_value = record.field("ended_at")
        if ended_value is not None:
            ended = _parse_timestamp(ended_value, "Implementation ended_at")
            if ended < started:
                raise WorkflowPrerequisiteError(
                    "Implementation ended_at cannot precede started_at"
                )
        created = _parse_timestamp(
            record.field("created_at"), "Implementation created_at"
        )
        if created < started:
            raise WorkflowPrerequisiteError(
                "Implementation created_at cannot precede started_at"
            )
        updated = _parse_timestamp(
            record.field("updated_at"), "Implementation updated_at"
        )
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Implementation updated_at cannot precede created_at"
            )
        return record

    def _require_existing_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> ImplementationV1:
        value = self._require_existing_record(work, record)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "ordinary Implementation execution progression requires active "
                "canonical status"
            )
        return value

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> ImplementationV1:
        value = self._require_existing_record(work, candidate)
        require_coordinated_implementation_transition(prior, value)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        if value.status == "active":
            self._root_service().require_current_use(work)
            plan = self._resolve_plan(work, value)
            actual_target = self._resolve_actual_target(work, value, current=True)
            actual_provider = self._resolve_actual_provider(work, value, current=True)
            plan_target = self._resolve_plan_target(work, plan.record)
            plan_provider = self._resolve_plan_provider(work, plan.record)
            self._require_plan_actual_alignment(
                value,
                plan.record,
                actual_target=actual_target,
                actual_provider=actual_provider,
                plan_target=plan_target,
                plan_provider=plan_provider,
            )
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value), "block_current_use"
            )
        else:
            self.repository.load_work(work)
            plan = self._resolve_plan(work, value)
            actual_target = self._resolve_actual_target(work, value, current=False)
            actual_provider = self._resolve_actual_provider(work, value, current=False)
            plan_target = self._resolve_plan_target(work, plan.record)
            plan_provider = self._resolve_plan_provider(work, plan.record)
            self._require_plan_actual_alignment(
                value,
                plan.record,
                actual_target=actual_target,
                actual_provider=actual_provider,
                plan_target=plan_target,
                plan_provider=plan_provider,
            )
        return value

    def _require_execution_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> ImplementationV1:
        value = self._require_existing_input(work, candidate)
        require_revision_invariants(
            prior,
            value,
            transitions=_NO_LIFECYCLE_TRANSITIONS,
        )
        prior_state = prior.field("execution_state")
        candidate_state = value.field("execution_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowOwnershipError(
                "Implementation execution_state is malformed"
            )
        if prior_state != "in_progress":
            raise WorkflowPrerequisiteError(
                "ordinary Implementation execution progression requires "
                "in_progress prior state"
            )
        if candidate_state not in _EXECUTION_STATE_TRANSITIONS[prior_state]:
            raise WorkflowPrerequisiteError(
                "illegal Implementation execution_state transition: "
                f"{prior_state} -> {candidate_state}"
            )

        prior_data = prior.to_dict()
        candidate_data = value.to_dict()
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - _EXECUTION_STATE_MUTABLE_FIELDS):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Implementation execution progression cannot rewrite "
                    f"field {field}"
                )

        prior_ended = prior.field("ended_at")
        candidate_ended = value.field("ended_at")
        if prior_ended is not None and candidate_ended != prior_ended:
            raise WorkflowPrerequisiteError(
                "ordinary Implementation execution progression cannot rewrite "
                "an existing ended_at"
            )

        self._root_service().require_current_use(work)
        plan = self._resolve_plan(work, value)
        actual_target = self._resolve_actual_target(
            work, value, current=False
        )
        actual_provider = self._resolve_actual_provider(
            work, value, current=False
        )
        plan_target = self._resolve_plan_target(work, plan.record)
        plan_provider = self._resolve_plan_provider(work, plan.record)
        self._require_plan_actual_alignment(
            value,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        self.quarantine.require_allowed(
            record_target(work, value), "block_current_use"
        )
        return value

    def _require_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> ImplementationV1:
        value = self._require_existing_record(work, successor)
        require_implementation_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Implementation predecessor updated_at",
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Implementation successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Implementation successor updated_at cannot precede predecessor update"
            )
        require_material_implementation_correction(
            prior,
            value,
            supersession_reason,
        )

        self._root_service().require_current_use(work)
        plan = self._resolve_plan(work, value)
        actual_target = self._resolve_actual_target(work, value, current=True)
        actual_provider = self._resolve_actual_provider(work, value, current=True)
        plan_target = self._resolve_plan_target(work, plan.record)
        plan_provider = self._resolve_plan_provider(work, plan.record)
        self._require_plan_actual_alignment(
            value,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        self.quarantine.require_allowed(work_target(work), "block_current_use")
        self.quarantine.require_allowed(
            record_target(work, value), "block_current_use"
        )
        return value

    def _require_work_root_successor_candidate(
        self,
        source_work: ExactPortiaWorkRef,
        destination_work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> ImplementationV1:
        value = self._require_existing_record(destination_work, successor)
        require_implementation_lifecycle_reconciled(
            self.repository,
            source_work,
            prior,
        )
        if prior.status not in {"active", "invalidated"}:
            raise WorkflowPrerequisiteError(
                "work-root correction predecessor must be active or invalidated"
            )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "work-root correction successor must be canonically active"
            )
        if prior.logical_id != value.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root correction must preserve Implementation ID"
            )
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Implementation work-root predecessor updated_at",
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Implementation work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Implementation work-root successor updated_at cannot precede "
                "predecessor update"
            )
        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_FACT_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root correction cannot rewrite occurrence fact "
                    f"{field}"
                )

        self.repository.load_work(source_work)
        self._root_service().require_current_use(destination_work)
        plan = self._resolve_plan(destination_work, value)
        actual_target = self._resolve_actual_target(
            destination_work,
            value,
            current=True,
        )
        actual_provider = self._resolve_actual_provider(
            destination_work,
            value,
            current=True,
        )
        plan_target = self._resolve_plan_target(destination_work, plan.record)
        plan_provider = self._resolve_plan_provider(destination_work, plan.record)
        self._require_plan_actual_alignment(
            value,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
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
        self.quarantine.require_allowed(
            work_target(destination_work),
            "block_current_use",
        )
        self.quarantine.require_allowed(
            record_target(destination_work, value),
            "block_current_use",
        )
        return value

    def _require_consolidation_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        priors: Sequence[PortiaRecord],
        successor: PortiaRecord,
    ) -> ImplementationV1:
        value = self._require_existing_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate consolidation successor must be canonically active"
            )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Implementation consolidation successor updated_at",
        )
        successor_plan = value.field("plan_ref")
        for prior in priors:
            require_implementation_lifecycle_reconciled(
                self.repository,
                work,
                prior,
            )
            if prior.status not in {"active", "invalidated"}:
                raise WorkflowPrerequisiteError(
                    "duplicate consolidation predecessor must be active or "
                    "invalidated"
                )
            prior_updated = _parse_timestamp(
                prior.field("updated_at"),
                "Implementation consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Implementation consolidation successor updated_at cannot "
                    "precede a predecessor update"
                )
            if prior.field("plan_ref") != successor_plan:
                raise WorkflowPrerequisiteError(
                    "duplicate consolidation requires one exact Implementation plan"
                )

        self._root_service().require_current_use(work)
        plan = self._resolve_plan(work, value)
        actual_target = self._resolve_actual_target(work, value, current=True)
        actual_provider = self._resolve_actual_provider(work, value, current=True)
        plan_target = self._resolve_plan_target(work, plan.record)
        plan_provider = self._resolve_plan_provider(work, plan.record)
        self._require_plan_actual_alignment(
            value,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        self.quarantine.require_allowed(work_target(work), "block_current_use")
        self.quarantine.require_allowed(
            record_target(work, value), "block_current_use"
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
        """Persist one ordinary Implementation activation/invalidation."""
        if (
            reference.record_ref.record_kind != "implementation"
            or reference.record_ref.contract_version != IMPLEMENTATION_VERSION
        ):
            raise WorkflowOwnershipError(
                "Implementation lifecycle requires exact implementation@1 reference"
            )
        work = reference.work_ref

        def validate_transition(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            self._require_lifecycle_transition_candidate(work, prior, value)

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
                build_implementation_lifecycle_transition(
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
        require_implementation_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def transition_execution_state(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Complete one in-progress occurrence through the frozen ordinary matrix."""
        if (
            reference.record_ref.record_kind != "implementation"
            or reference.record_ref.contract_version != IMPLEMENTATION_VERSION
        ):
            raise WorkflowOwnershipError(
                "Implementation execution progression requires exact "
                "implementation@1 reference"
            )
        prior = self.load_exact(reference)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Implementation state does not match canonical bytes"
            )
        value = self._require_execution_transition_candidate(
            reference.work_ref,
            prior.record,
            candidate,
        )
        return self.repository.replace_work_record(
            reference.work_ref,
            value,
            expected=expected,
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
        """Create a corrected Implementation successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "implementation"
            or predecessor.record_ref.contract_version != IMPLEMENTATION_VERSION
        ):
            raise WorkflowOwnershipError(
                "Implementation correction requires exact implementation@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_implementation_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = implementation_supersession_reason_detail(successor)
        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        def validate_successor(prior: PortiaRecord, value: PortiaRecord) -> None:
            self._require_successor_candidate(
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
            predecessor_factory=superseded_implementation_predecessor,
            transition_factory=lambda prior, value: (
                build_implementation_lifecycle_transition(
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
        require_implementation_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

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
        """Move one corrected Implementation representation to its true root."""
        _require_implementation_owner(destination_work)
        source_work = require_implementation_work_root_correction_predecessor(
            destination_work,
            predecessor,
            successor,
        )
        reason_detail = implementation_supersession_reason_detail(successor)
        coordinator = ActionOwnershipCorrectionCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

        def validate_successor(prior: PortiaRecord, value: PortiaRecord) -> None:
            self._require_work_root_successor_candidate(
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
            predecessor_factory=superseded_implementation_predecessor,
            transition_factory=lambda prior, value: (
                build_implementation_lifecycle_transition(
                    self.repository,
                    source_work,
                    prior,
                    value,
                    transition_id=transition_id,
                    reason_code="work_root_corrected",
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                    allow_supersession=True,
                )
            ),
        )
        accepted = self.load_exact(predecessor)
        require_implementation_lifecycle_reconciled(
            self.repository,
            source_work,
            accepted.record,
        )
        return result

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
        """Create one canonical successor for duplicate Implementation records."""
        _require_implementation_owner(work)
        predecessors = require_duplicate_implementation_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate consolidation requires one expected fingerprint for "
                "every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate consolidation requires one lifecycle transition ID for "
                "every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "duplicate consolidation lifecycle transition IDs must be unique"
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
            self._require_consolidation_successor_candidate(
                work,
                priors,
                value,
            )

        def build_transition(
            prior: PortiaRecord,
            candidate: PortiaRecord,
            transition_id: str,
        ) -> PortiaRecord:
            return build_implementation_lifecycle_transition(
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
            expected=tuple(expected[identifier] for identifier in predecessor_ids),
            transition_ids=ordered_transition_ids,
            supersession_reason="duplicate_consolidated",
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=validate_successor,
            predecessor_factory=superseded_implementation_predecessor,
            transition_factory=build_transition,
        )
        for predecessor in predecessors:
            accepted = self.load_exact(predecessor)
            require_implementation_lifecycle_reconciled(
                self.repository,
                work,
                accepted.record,
            )
        return result

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        """Load exactly the requested Implementation without successor following."""
        _require_implementation_owner(reference.work_ref)
        if reference.record_ref.record_kind != "implementation":
            raise WorkflowOwnershipError("reference is not an Implementation")
        if reference.record_ref.contract_version != IMPLEMENTATION_VERSION:
            raise WorkflowOwnershipError(
                "unsupported exact Implementation contract version "
                f"{reference.record_ref.contract_version!r}"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "implementation",
            IMPLEMENTATION_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        """List exact canonical Implementation identities for one Support Process."""
        _require_implementation_owner(work)
        return self.repository.list_work_records(
            work,
            "implementation",
            version=IMPLEMENTATION_VERSION,
        )

    list_implementations = list

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Require one canonically active Implementation without judging outcome."""
        implementation = self.load_exact(reference)
        require_implementation_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            implementation.record,
        )
        self._require_existing_record(reference.work_ref, implementation.record)
        if implementation.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Implementation use requires active canonical status"
            )

        predecessors = implementation_supersession_ancestry(
            self.repository,
            reference.work_ref,
            implementation.record,
        )
        require_implementation_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )

        self._root_service().require_current_use(reference.work_ref)
        plan = self._resolve_plan(reference.work_ref, implementation.record)
        actual_target = self._resolve_actual_target(
            reference.work_ref,
            implementation.record,
            current=True,
        )
        actual_provider = self._resolve_actual_provider(
            reference.work_ref,
            implementation.record,
            current=True,
        )
        plan_target = self._resolve_plan_target(reference.work_ref, plan.record)
        plan_provider = self._resolve_plan_provider(reference.work_ref, plan.record)
        self._require_plan_actual_alignment(
            implementation.record,
            plan.record,
            actual_target=actual_target,
            actual_provider=actual_provider,
            plan_target=plan_target,
            plan_provider=plan_provider,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, implementation.record),
            "block_current_use",
        )
        return implementation

    resolve_current = require_current_use
