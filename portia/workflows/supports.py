"""Support Process-local ``support@1`` planning creation and exact-use workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from pathlib import Path

from portia.models import PortiaRecord, SupportV1
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaNotFoundError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
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
from portia.workflows.support_goals import (
    SupportGoalWorkflowService,
    support_goal_reference,
)
from portia.workflows.support_lifecycle import (
    build_support_lifecycle_transition,
    require_coordinated_support_transition,
    require_support_lifecycle_reconciled,
)
from portia.workflows.support_needs import (
    SupportNeedWorkflowService,
    support_need_reference,
)
from portia.workflows.support_process_participants import (
    SupportProcessParticipantWorkflowService,
    support_process_participant_reference,
)
from portia.workflows.support_processes import SupportProcessWorkflowService
from portia.workflows.support_supersession import (
    require_exact_support_adaptation_predecessor,
    require_exact_support_correction_predecessor,
    require_material_support_adaptation,
    require_material_support_correction,
    require_support_supersession_effective,
    superseded_support_predecessor,
    support_supersession_ancestry,
    support_supersession_reason_detail,
)

SUPPORT_VERSION = "1"
_SUPPORT_OWNER = ("support_process", "1")
_PLAN_STATE_TRANSITIONS = {
    "planned": frozenset({"active", "discontinued"}),
    "active": frozenset({"paused", "completed", "discontinued"}),
    "paused": frozenset({"active", "completed", "discontinued"}),
    "completed": frozenset(),
    "discontinued": frozenset(),
}
_PLAN_STATE_MUTABLE_FIELDS = frozenset({"plan_state", "updated_at", "updated_by"})
_NO_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {}


def _require_support_owner(work: ExactPortiaWorkRef) -> None:
    if (work.work_kind, work.contract_version) != _SUPPORT_OWNER:
        raise WorkflowOwnershipError(
            "Support workflows require exact support_process@1 ownership"
        )


def support_reference(
    work: ExactPortiaWorkRef,
    support_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Support Process-local ``support@1`` reference."""
    _require_support_owner(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="support",
            record_id=support_id,
            contract_version=SUPPORT_VERSION,
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


def _parse_date(value: object, description: str) -> date:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} is not an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(f"{description} is not an ISO date") from exc


def _require_schedule_application_valid(record: PortiaRecord) -> None:
    schedule = record.field("schedule")
    if not isinstance(schedule, Mapping):
        raise WorkflowOwnershipError("Support planned schedule is malformed")

    window = schedule.get("window")
    if window is not None:
        if not isinstance(window, Mapping):
            raise WorkflowOwnershipError("Support planned schedule window is malformed")
        starts = (
            _parse_date(window.get("starts_on"), "Support schedule starts_on")
            if window.get("starts_on") is not None
            else None
        )
        ends = (
            _parse_date(window.get("ends_on"), "Support schedule ends_on")
            if window.get("ends_on") is not None
            else None
        )
        review = (
            _parse_date(window.get("review_on"), "Support schedule review_on")
            if window.get("review_on") is not None
            else None
        )
        if starts is not None and ends is not None and ends < starts:
            raise WorkflowPrerequisiteError(
                "Support schedule ends_on cannot precede starts_on"
            )
        if starts is not None and review is not None and review < starts:
            raise WorkflowPrerequisiteError(
                "Support schedule review_on cannot precede starts_on"
            )

    duration = schedule.get("planned_duration")
    if isinstance(duration, Mapping) and duration.get("kind") == "range_minutes":
        minimum = duration.get("minimum_minutes")
        maximum = duration.get("maximum_minutes")
        if (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or not isinstance(maximum, int)
            or isinstance(maximum, bool)
        ):
            raise WorkflowOwnershipError("Support planned-duration range is malformed")
        if minimum > maximum:
            raise WorkflowPrerequisiteError(
                "Support planned duration minimum_minutes cannot exceed maximum_minutes"
            )


def _exact_local_ref(
    value: object,
    *,
    kind: str,
    field_name: str,
) -> ExactLocalRecordRef:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"Support {field_name} reference is malformed")
    reference = ExactLocalRecordRef.from_dict(value)
    if reference.record_kind != kind or reference.contract_version != "1":
        raise WorkflowOwnershipError(
            f"Support {field_name} must name exact {kind}@1"
        )
    return reference


def _record_ref_sequence(
    value: object,
    *,
    kind: str,
    field_name: str,
) -> tuple[ExactLocalRecordRef, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise WorkflowOwnershipError(f"Support {field_name} is malformed")
    return tuple(
        _exact_local_ref(item, kind=kind, field_name=field_name)
        for item in value
    )


def _target_participant_refs(record: PortiaRecord) -> tuple[ExactLocalRecordRef, ...]:
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("Support target is malformed")
    kind = target.get("kind")
    if kind == "support_process":
        return ()
    if kind == "support_process_participant":
        return (
            _exact_local_ref(
                target.get("record_ref"),
                kind="support_process_participant",
                field_name="target",
            ),
        )
    if kind == "support_process_participants":
        targets = target.get("targets")
        if not isinstance(targets, Sequence) or isinstance(
            targets, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Support participant-set target is malformed")
        refs: list[ExactLocalRecordRef] = []
        for item in targets:
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    "Support participant-set target entry is malformed"
                )
            refs.append(
                _exact_local_ref(
                    item.get("record_ref"),
                    kind="support_process_participant",
                    field_name="target",
                )
            )
        return tuple(refs)
    raise WorkflowOwnershipError(f"unsupported Support target kind {kind!r}")


def _logical_person_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Support Process Participant person is malformed")
    kind = value.get("kind")
    if kind == "roster_student":
        reference = value.get("roster_student_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Support roster person is malformed")
        return (kind, reference.get("class_id"), reference.get("student_id"))
    if kind == "actor":
        reference = value.get("actor_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Support Actor person is malformed")
        return (kind, reference.get("actor_id"))
    if kind == "local_operator":
        return (kind, value.get("display_label"))
    if kind == "descriptive_person":
        return (kind, value.get("description_type"), value.get("display_label"))
    if kind == "unidentified_person":
        return (kind, value.get("identity_status"), value.get("display_label"))
    raise WorkflowOwnershipError(
        f"unsupported Support participant person kind {kind!r}"
    )


def _require_unique_logical_people(
    participants: Sequence[StoredRecord],
    *,
    description: str,
) -> None:
    identities = [
        _logical_person_identity(item.record.field("person")) for item in participants
    ]
    if len(identities) != len(set(identities)):
        raise WorkflowPrerequisiteError(
            f"Support {description} repeats a logical Support Process Participant"
        )


class SupportWorkflowService(WorkflowServiceBase):
    """Create and resolve exact teacher-local ``support@1`` plans."""

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

    def _participant_service(self) -> SupportProcessParticipantWorkflowService:
        return SupportProcessParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _need_service(self) -> SupportNeedWorkflowService:
        return SupportNeedWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _goal_service(self) -> SupportGoalWorkflowService:
        return SupportGoalWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _root_service(self) -> SupportProcessWorkflowService:
        return SupportProcessWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportV1:
        _require_support_owner(work)
        if not isinstance(record, SupportV1):
            raise WorkflowOwnershipError("new Support writes require support@1 input")
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Support does not belong to the explicitly selected Support Process"
            )
        source = record.field("creation_source")
        if not isinstance(source, Mapping) or source.get("type") != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Support authoring accepts "
                "creation_source=digital_entry only"
            )
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Support identity must begin proposed or active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Support identity cannot establish supersession history"
            )
        created = _parse_timestamp(record.field("created_at"), "Support created_at")
        updated = _parse_timestamp(record.field("updated_at"), "Support updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Support updated_at cannot precede created_at"
            )
        _require_schedule_application_valid(record)
        return record

    def _require_existing_revision_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportV1:
        _require_support_owner(work)
        if not isinstance(record, SupportV1):
            raise WorkflowOwnershipError("Support revisions require support@1 input")
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Support revision does not belong to the selected Support Process"
            )
        source = record.field("creation_source")
        if not isinstance(source, Mapping) or source.get("type") != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Support revision/current use requires digital_entry "
                "materialization"
            )
        created = _parse_timestamp(record.field("created_at"), "Support created_at")
        updated = _parse_timestamp(record.field("updated_at"), "Support updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Support updated_at cannot precede created_at"
            )
        _require_schedule_application_valid(record)
        return record

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        value = self._require_existing_revision_input(work, candidate)
        require_coordinated_support_transition(prior, value)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        if value.status == "active":
            self._root_service().require_current_use(work)
            self._resolve_dependencies(work, value, require_current_use=True)
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value), "block_current_use"
            )
        else:
            self.repository.load_work(work)
            self._resolve_dependencies(work, value, require_current_use=False)

    def _require_plan_state_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> SupportV1:
        value = self._require_existing_revision_input(work, candidate)
        require_support_lifecycle_reconciled(self.repository, work, prior)
        require_revision_invariants(prior, value, transitions=_NO_STATUS_TRANSITIONS)
        if prior.status != "active" or value.status != "active":
            raise WorkflowPrerequisiteError(
                "ordinary Support plan_state progression requires active canonical "
                "status"
            )
        prior_state = prior.field("plan_state")
        candidate_state = value.field("plan_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowOwnershipError("Support plan_state is malformed")
        if prior_state == candidate_state:
            raise WorkflowPrerequisiteError(
                "Support plan_state progression requires a state change"
            )
        if candidate_state not in _PLAN_STATE_TRANSITIONS.get(
            prior_state, frozenset()
        ):
            raise WorkflowPrerequisiteError(
                "illegal Support plan_state transition: "
                f"{prior_state} -> {candidate_state}"
            )
        prior_data = prior.to_dict()
        candidate_data = value.to_dict()
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - _PLAN_STATE_MUTABLE_FIELDS):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Support plan_state replacement cannot rewrite "
                    f"field {field}"
                )
        self._root_service().require_current_use(work)
        self._resolve_dependencies(work, value, require_current_use=True)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        self.quarantine.require_allowed(work_target(work), "block_current_use")
        self.quarantine.require_allowed(
            record_target(work, value), "block_current_use"
        )
        return value

    def _resolve_participants(
        self,
        work: ExactPortiaWorkRef,
        refs: Sequence[ExactLocalRecordRef],
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        service = self._participant_service()
        resolved: list[StoredRecord] = []
        for ref in refs:
            exact = support_process_participant_reference(work, ref.record_id)
            try:
                if require_current_use:
                    stored = service.require_current_use(exact).participant
                else:
                    stored = service.load_exact(exact)
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Support Participant reference does not resolve in the owning "
                    "Support Process"
                ) from exc
            resolved.append(stored)
        return tuple(resolved)

    def _resolve_needs(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        refs = _record_ref_sequence(
            record.field("need_refs"),
            kind="support_need",
            field_name="need_refs",
        )
        service = self._need_service()
        resolved: list[StoredRecord] = []
        for ref in refs:
            exact = support_need_reference(work, ref.record_id)
            try:
                stored = (
                    service.require_current_use(exact)
                    if require_current_use
                    else service.load_exact(exact)
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Support Need ref does not resolve in the owning Support Process"
                ) from exc
            resolved.append(stored)
        return tuple(resolved)

    def _resolve_goals(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        raw = record.field("goal_refs")
        if raw is None:
            return ()
        refs = _record_ref_sequence(
            raw,
            kind="support_goal",
            field_name="goal_refs",
        )
        service = self._goal_service()
        resolved: list[StoredRecord] = []
        for ref in refs:
            exact = support_goal_reference(work, ref.record_id)
            try:
                stored = (
                    service.require_current_use(exact)
                    if require_current_use
                    else service.load_exact(exact)
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Support Goal ref does not resolve in the owning Support Process"
                ) from exc
            resolved.append(stored)
        return tuple(resolved)

    def _resolve_provider_participants(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        plan = record.field("provider_plan")
        if not isinstance(plan, Mapping):
            raise WorkflowOwnershipError("Support provider_plan is malformed")
        if plan.get("kind") == "no_assigned_provider":
            return ()
        if plan.get("kind") != "assigned":
            raise WorkflowOwnershipError("Support provider_plan kind is unsupported")
        refs = _record_ref_sequence(
            plan.get("participant_refs"),
            kind="support_process_participant",
            field_name="provider participant_refs",
        )
        participants = self._resolve_participants(
            work,
            refs,
            require_current_use=require_current_use,
        )
        _require_unique_logical_people(participants, description="provider assignment")
        return participants

    def _resolve_target_participants(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        participants = self._resolve_participants(
            work,
            _target_participant_refs(record),
            require_current_use=require_current_use,
        )
        _require_unique_logical_people(participants, description="target set")
        return participants

    def _resolve_dependencies(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        target_participants = self._resolve_target_participants(
            work, record, require_current_use=require_current_use
        )
        needs = self._resolve_needs(
            work, record, require_current_use=require_current_use
        )
        goals = self._resolve_goals(
            work, record, require_current_use=require_current_use
        )
        providers = self._resolve_provider_participants(
            work, record, require_current_use=require_current_use
        )
        return (*target_participants, *needs, *goals, *providers)

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        self.repository.load_work(work)
        require_current = candidate.status == "active"
        if require_current:
            self._root_service().require_current_use(work)
        self._resolve_dependencies(
            work,
            candidate,
            require_current_use=require_current,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        _require_support_owner(reference.work_ref)
        if reference.record_ref.record_kind != "support":
            raise WorkflowOwnershipError("reference is not a Support")
        if reference.record_ref.contract_version != SUPPORT_VERSION:
            raise WorkflowOwnershipError(
                f"unsupported exact Support contract version "
                f"{reference.record_ref.contract_version!r}"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "support",
            SUPPORT_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        _require_support_owner(work)
        return self.repository.list_work_records(
            work,
            "support",
            version=SUPPORT_VERSION,
        )

    list_supports = list

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
        """Persist one ordinary Support activation/invalidation."""
        if (
            reference.record_ref.record_kind != "support"
            or reference.record_ref.contract_version != SUPPORT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support lifecycle requires exact support@1 reference"
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
            transition_factory=lambda prior, value: build_support_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=reason_code,
                reason_detail=reason_detail,
                effective_at=effective_at,
            ),
        )
        accepted = self.load_exact(reference)
        require_support_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def transition_plan_state(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Persist one ordinary plan-state revision without lifecycle mutation."""
        prior = self.load_exact(reference)
        value = self._require_plan_state_transition_candidate(
            reference.work_ref,
            prior.record,
            candidate,
        )
        return self.repository.replace_work_record(
            reference.work_ref,
            value,
            expected=expected,
        )

    def _require_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
        adaptation: bool,
    ) -> None:
        value = self._require_existing_revision_input(work, successor)
        require_support_lifecycle_reconciled(self.repository, work, prior)
        prior_updated = _parse_timestamp(
            prior.field("updated_at"), "Support predecessor updated_at"
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"), "Support successor updated_at"
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Support successor updated_at cannot precede predecessor update"
            )
        if adaptation:
            require_material_support_adaptation(prior, value)
        else:
            require_material_support_correction(
                prior,
                value,
                supersession_reason,
            )

        require_current = value.status == "active"
        if require_current:
            self._root_service().require_current_use(work)
        else:
            self.repository.load_work(work)
        self._resolve_dependencies(
            work,
            value,
            require_current_use=require_current,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        if require_current:
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value), "block_current_use"
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
        """Create a corrected Support successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "support"
            or predecessor.record_ref.contract_version != SUPPORT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support correction requires exact support@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_support_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = support_supersession_reason_detail(successor)
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
                adaptation=False,
            ),
            predecessor_factory=superseded_support_predecessor,
            transition_factory=lambda prior, value: build_support_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=supersession_reason,
                reason_detail=reason_detail,
                effective_at=effective_at,
                allow_supersession=True,
            ),
        )
        accepted = self.load_exact(predecessor)
        require_support_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def adapt(
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
        """Create one prospective material plan_adapted Support successor."""
        if (
            predecessor.record_ref.record_kind != "support"
            or predecessor.record_ref.contract_version != SUPPORT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support adaptation requires exact support@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_support_adaptation_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = support_supersession_reason_detail(successor)
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
                adaptation=True,
            ),
            predecessor_factory=superseded_support_predecessor,
            transition_factory=lambda prior, value: build_support_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=supersession_reason,
                reason_detail=reason_detail,
                effective_at=effective_at,
                allow_supersession=True,
            ),
        )
        accepted = self.load_exact(predecessor)
        require_support_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        support = self.load_exact(reference)
        require_support_lifecycle_reconciled(
            self.repository, reference.work_ref, support.record
        )
        self._require_existing_revision_input(reference.work_ref, support.record)
        if support.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Support use requires active canonical status"
            )
        _require_schedule_application_valid(support.record)
        predecessors = support_supersession_ancestry(
            self.repository,
            reference.work_ref,
            support.record,
        )
        require_support_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )
        self._root_service().require_current_use(reference.work_ref)
        self._resolve_dependencies(
            reference.work_ref,
            support.record,
            require_current_use=True,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, support.record), "block_current_use"
        )
        return support

    resolve_current = require_current_use
