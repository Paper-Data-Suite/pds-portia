"""Production workflow for canonical ``support_goal@1`` planning records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from portia.models import PortiaRecord, SupportGoalV1
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage.errors import PortiaNotFoundError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.support_goal_lifecycle import (
    build_support_goal_lifecycle_transition,
    require_coordinated_support_goal_transition,
    require_support_goal_lifecycle_reconciled,
)
from portia.workflows.support_goal_supersession import (
    require_exact_support_goal_correction_predecessor,
    require_material_support_goal_correction,
    require_support_goal_supersession_effective,
    superseded_support_goal_predecessor,
    support_goal_supersession_ancestry,
    support_goal_supersession_reason_detail,
)
from portia.workflows.support_process_continuation import (
    support_process_continuation_ancestry,
)
from portia.workflows.support_process_initiation import (
    require_support_process_initiation_authority,
    validate_support_process_graph,
)
from portia.workflows.support_process_participants import (
    SupportProcessParticipantWorkflowService,
    support_process_participant_reference,
)
from portia.workflows.support_process_supersession import (
    support_process_supersession_ancestry,
)
from portia.workflows.support_processes import SupportProcessWorkflowService

SUPPORT_GOAL_VERSION = "1"
SUPPORT_PROCESS_VERSION = "1"
_PARTICIPANT_VERSION = "1"
_AUTHORING_WORKFLOW_STATES = frozenset({"planning", "active", "paused"})


def support_goal_reference(
    work: ExactPortiaWorkRef,
    goal_id: str,
    *,
    version: str = SUPPORT_GOAL_VERSION,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Support Process-local Support Goal reference."""
    _require_support_process_owner(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="support_goal",
            record_id=goal_id,
            contract_version=version,
        ),
    )


def _require_support_process_owner(work: ExactPortiaWorkRef) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != SUPPORT_PROCESS_VERSION
    ):
        raise WorkflowOwnershipError(
            "Support Goal workflows require exact support_process@1 ownership"
        )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Support Goal {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Support Goal {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"Support Goal {field_name} timestamp lacks an explicit offset"
        )
    return parsed


def _participant_local_reference(value: object) -> tuple[str, str]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Support Goal participant target is malformed")
    record_ref = value.get("record_ref")
    if not isinstance(record_ref, Mapping):
        raise WorkflowOwnershipError("Support Goal participant target is malformed")
    if record_ref.get("record_kind") != "support_process_participant":
        raise WorkflowOwnershipError(
            "Support Goal target must name a Support Process Participant"
        )
    identifier = record_ref.get("record_id")
    version = record_ref.get("contract_version")
    if not isinstance(identifier, str) or version != _PARTICIPANT_VERSION:
        raise WorkflowOwnershipError(
            "Support Goal target must name an exact support_process_participant@1"
        )
    return identifier, version


def _target_participant_keys(record: PortiaRecord) -> tuple[tuple[str, str], ...]:
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("Support Goal target is malformed")
    kind = target.get("kind")
    if kind == "support_process":
        return ()
    if kind == "support_process_participant":
        return (_participant_local_reference(target),)
    if kind != "support_process_participants":
        raise WorkflowOwnershipError("Support Goal target kind is unsupported")
    targets = target.get("targets")
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes)):
        raise WorkflowOwnershipError("Support Goal participant target set is malformed")
    keys = tuple(_participant_local_reference(value) for value in targets)
    if len(set(keys)) != len(keys):
        raise WorkflowPrerequisiteError(
            "Support Goal target set repeats a logical participant"
        )
    return keys


def _participant_logical_person_identity(
    record: PortiaRecord,
) -> tuple[object, ...] | None:
    person = record.field("person")
    if not isinstance(person, Mapping):
        raise WorkflowOwnershipError(
            "Support Goal target Participant person is malformed"
        )
    kind = person.get("kind")
    if kind == "roster_student":
        reference = RosterStudentRef.from_dict(person.get("roster_student_ref"))
        return (kind, reference.class_id, reference.student_id)
    if kind == "actor":
        actor_ref = person.get("actor_ref")
        actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
        if not isinstance(actor_id, str):
            raise WorkflowOwnershipError(
                "Support Goal target Actor reference is malformed"
            )
        return (kind, actor_id)
    if kind == "local_operator":
        return (kind,)
    if kind in {"descriptive_person", "unidentified_person"}:
        return None
    raise WorkflowOwnershipError(
        "Support Goal target Participant person kind is unsupported"
    )


def _require_logical_target_unique(records: Sequence[StoredRecord]) -> None:
    seen: set[tuple[object, ...]] = set()
    for stored in records:
        identity = _participant_logical_person_identity(stored.record)
        if identity is None:
            continue
        if identity in seen:
            raise WorkflowPrerequisiteError(
                "Support Goal target set repeats a logical participant"
            )
        seen.add(identity)


class SupportGoalWorkflowService(WorkflowServiceBase):
    """Author and resolve bounded Goals without progress or outcome inference."""

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

    def _require_owner(self, work: ExactPortiaWorkRef) -> StoredRecord:
        _require_support_process_owner(work)
        return self.repository.load_work(work)

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
                "Support Goal authoring requires proposed or active Support Process"
            )
        workflow_state = owner.record.field("workflow_state")
        if workflow_state not in _AUTHORING_WORKFLOW_STATES:
            raise WorkflowPrerequisiteError(
                "Support Goal authoring requires planning, active, or paused "
                "Support Process workflow state"
            )
        return owner

    @staticmethod
    def _require_fresh_digital_candidate(candidate: SupportGoalV1) -> None:
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Support Goal must begin proposed or active"
            )
        source = candidate.field("creation_source")
        source_type = source.get("type") if isinstance(source, Mapping) else None
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Support Goal authoring supports digital_entry only"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Support Goal creation cannot establish supersession history"
            )
        created = _parse_timestamp(
            candidate.field("created_at"), field_name="created_at"
        )
        updated = _parse_timestamp(
            candidate.field("updated_at"), field_name="updated_at"
        )
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Support Goal updated_at cannot precede created_at"
            )

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportGoalV1:
        self._require_owner(work)
        if not isinstance(record, SupportGoalV1):
            raise WorkflowOwnershipError(
                "Support Goal writes require support_goal@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Support Goal does not belong to selected Support Process"
            )
        return record

    def _require_existing_revision_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> SupportGoalV1:
        candidate = self._require_write_input(work, record)
        source = candidate.field("creation_source")
        source_type = source.get("type") if isinstance(source, Mapping) else None
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Support Goal revision/current use requires digital_entry "
                "materialization"
            )
        created = _parse_timestamp(
            candidate.field("created_at"), field_name="created_at"
        )
        updated = _parse_timestamp(
            candidate.field("updated_at"), field_name="updated_at"
        )
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Support Goal updated_at cannot precede created_at"
            )
        return candidate

    def _target_records(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord, ...]:
        participant_service = self._participant_service()
        resolved: list[StoredRecord] = []
        for participant_id, version in _target_participant_keys(record):
            reference = support_process_participant_reference(
                work,
                participant_id,
                version=version,
            )
            try:
                if require_current_use:
                    resolution = participant_service.require_current_use(reference)
                    stored = resolution.participant
                else:
                    stored = participant_service.load_exact(reference)
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Support Goal target participant does not resolve in owning "
                    "Support Process"
                ) from exc
            resolved.append(stored)
        result = tuple(resolved)
        _require_logical_target_unique(result)
        return result


    def _graph_records(
        self,
        work: ExactPortiaWorkRef,
        owner: StoredRecord,
        candidate: PortiaRecord,
    ) -> tuple[PortiaRecord, ...]:
        owner_ancestry = support_process_supersession_ancestry(
            self.repository,
            owner.record,
        )
        continuation = support_process_continuation_ancestry(
            self.repository,
            owner.record,
        )
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        participants = self._participant_service().list(work)
        predecessors = support_goal_supersession_ancestry(
            self.repository,
            work,
            candidate,
        )
        return (
            *(stored.record for stored in owner_ancestry),
            *continuation_records,
            owner.record,
            *(stored.record for stored in participants),
            *(resolution.stored.record for resolution in predecessors),
            candidate,
        )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        owner = self._require_authoring_owner(work)
        candidate = self._require_write_input(work, record)
        self._require_fresh_digital_candidate(candidate)
        active = candidate.status == "active"
        if active:
            owner = self._root_service().require_current_use(work)
        self._target_records(
            work,
            candidate,
            require_current_use=active,
        )
        validate_support_process_graph(
            self.contexts,
            self._graph_records(work, owner, candidate),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        if active:
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, candidate), "block_current_use"
            )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        work = reference.work_ref
        self._require_owner(work)
        if (
            reference.record_ref.record_kind != "support_goal"
            or reference.record_ref.contract_version != SUPPORT_GOAL_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support Goal exact read requires support_goal@1 reference"
            )
        return self.repository.load_work_record(
            work,
            "support_goal",
            SUPPORT_GOAL_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        self._require_owner(work)
        return self.repository.list_work_records(
            work,
            "support_goal",
            version=SUPPORT_GOAL_VERSION,
        )

    list_support_goals = list

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
        """Persist one ordinary Support Goal activation/invalidation."""
        if (
            reference.record_ref.record_kind != "support_goal"
            or reference.record_ref.contract_version != SUPPORT_GOAL_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support Goal lifecycle requires exact support_goal@1 reference"
            )
        work = reference.work_ref

        def validate_transition(
            prior: PortiaRecord,
            value: PortiaRecord,
        ) -> None:
            revision = self._require_existing_revision_input(work, value)
            require_coordinated_support_goal_transition(prior, revision)
            self.quarantine.require_allowed(work_target(work), "block_work_writes")
            self.quarantine.require_allowed(
                record_target(work, revision), "block_work_writes"
            )
            if revision.status == "active":
                self._require_authoring_owner(work)
                owner = self._root_service().require_current_use(work)
                self._target_records(
                    work,
                    revision,
                    require_current_use=True,
                )
                self.quarantine.require_allowed(
                    work_target(work), "block_current_use"
                )
                self.quarantine.require_allowed(
                    record_target(work, revision), "block_current_use"
                )
            else:
                owner = self._require_owner(work)
                self._target_records(
                    work,
                    revision,
                    require_current_use=False,
                )
            validate_support_process_graph(
                self.contexts,
                self._graph_records(work, owner, revision),
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
                build_support_goal_lifecycle_transition(
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
        require_support_goal_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def _require_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> None:
        value = self._require_existing_revision_input(work, successor)
        require_support_goal_lifecycle_reconciled(self.repository, work, prior)
        prior_updated = _parse_timestamp(
            prior.field("updated_at"), field_name="predecessor updated_at"
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"), field_name="successor updated_at"
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Support Goal successor updated_at cannot precede predecessor update"
            )
        require_material_support_goal_correction(
            prior,
            value,
            supersession_reason,
        )
        if value.status == "active":
            owner = self._root_service().require_current_use(work)
            self._target_records(work, value, require_current_use=True)
        else:
            owner = self._require_owner(work)
            self._target_records(work, value, require_current_use=False)
        validate_support_process_graph(
            self.contexts,
            self._graph_records(work, owner, value),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        if value.status == "active":
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
        """Create a corrected Goal successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "support_goal"
            or predecessor.record_ref.contract_version != SUPPORT_GOAL_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support Goal correction requires exact support_goal@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_support_goal_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = support_goal_supersession_reason_detail(successor)
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
            predecessor_factory=superseded_support_goal_predecessor,
            transition_factory=lambda prior, value: (
                build_support_goal_lifecycle_transition(
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
        require_support_goal_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        goal = self.load_exact(reference)
        require_support_goal_lifecycle_reconciled(
            self.repository, reference.work_ref, goal.record
        )
        if goal.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Support Goal use requires active canonical status"
            )
        predecessors = support_goal_supersession_ancestry(
            self.repository,
            reference.work_ref,
            goal.record,
        )
        require_support_goal_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(
                    predecessor.work_ref,
                    predecessor.stored.record,
                ),
                "block_current_use",
            )
        source = goal.record.field("creation_source")
        source_type = source.get("type") if isinstance(source, Mapping) else None
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "Support Goal current use currently requires digital_entry "
                "materialization; paper/import review history is deferred"
            )
        owner = self._root_service().require_current_use(reference.work_ref)
        self._target_records(
            reference.work_ref,
            goal.record,
            require_current_use=True,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, goal.record), "block_current_use"
        )
        validate_support_process_graph(
            self.contexts,
            self._graph_records(reference.work_ref, owner, goal.record),
        )
        return goal

    resolve_current = require_current_use
