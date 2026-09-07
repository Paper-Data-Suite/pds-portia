"""Production core workflow service for work-local ``follow_up@1`` records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from portia.models import FollowUpV1, PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
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
    DownstreamRelatedRecordResolution,
    DownstreamTargetResolution,
    DownstreamWorkflowAuthority,
    follow_up_reference,
    parse_date_only,
    parse_explicit_timestamp,
    require_date_order,
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
    require_material_follow_up_correction,
    superseded_downstream_predecessor,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_FOLLOW_UP_OWNER_CONTEXTS = frozenset(
    {"provider_or_collaborator", "coordinator"}
)
_FOLLOW_UP_RELATED_ROLES = frozenset(
    {"context", "reviewed", "produced", "follow_up_to"}
)

# ``context``, ``reviewed``, and ``produced`` are intentionally broad exact
# provenance roles. The frozen Issue #19 application contract restricts only
# ``follow_up_to`` to Follow-Up and requires ``produced`` to remain same-work.
# Keep this set aligned with already-published Portia work-local contracts;
# resolution still requires the exact referenced record to exist.
_PORTIA_WORK_RECORD_CONTRACTS = frozenset(
    {
        "event_participant",
        "event_participant_role",
        "work_relationship",
        "account",
        "observation",
        "review",
        "classification",
        "hypothesis",
        "determination",
        "response",
        "communication",
        "support_process_participant",
        "support_need",
        "support_goal",
        "support",
        "intervention",
        "implementation",
        "fidelity",
        "follow_up",
        "outcome",
        "reentry",
        "repair",
        "lifecycle_transition",
        "lifecycle_history_correction",
        "amendment",
        "statement_of_disagreement",
        "dependency",
        "record_migration",
        "ownership_correction",
        "exceptional_removal",
    }
)
_FOLLOW_UP_ROLE_CONTRACTS = {
    "context": _PORTIA_WORK_RECORD_CONTRACTS,
    "reviewed": _PORTIA_WORK_RECORD_CONTRACTS,
    "produced": _PORTIA_WORK_RECORD_CONTRACTS,
    "follow_up_to": frozenset({"follow_up"}),
}

_WORKFLOW_STATE_TRANSITIONS = {
    "scheduled": frozenset(
        {"in_progress", "completed", "cancelled", "unable_to_complete"}
    ),
    "in_progress": frozenset(
        {"completed", "cancelled", "unable_to_complete"}
    ),
    "completed": frozenset(),
    "cancelled": frozenset(),
    "unable_to_complete": frozenset(),
}
_WORKFLOW_STATE_MUTABLE_FIELDS = frozenset(
    {"workflow_state", "completed_at", "updated_at", "updated_by"}
)
_WORK_ROOT_PRESERVED_FACT_FIELDS = (
    "purpose",
    "planned_timing",
    "workflow_state",
    "completed_at",
    "related_records",
    "disposition",
    "creation_source",
)
_COMPLETION_MUTABLE_FIELDS = frozenset({"related_records", "disposition"})
_COMPLETION_LINK_ROLES = frozenset({"reviewed", "produced"})


class FollowUpWorkflowService(ActionReadService):
    """Create and qualify exact teacher-local ``follow_up@1`` records."""

    CONTRACT = "follow_up"

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

    @staticmethod
    def _require_follow_up_record(
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> FollowUpV1:
        require_downstream_record_owner(work, record, contract="follow_up")
        if not isinstance(record, FollowUpV1):
            raise WorkflowOwnershipError(
                "Follow-Up workflow requires follow_up@1 input"
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
            raise WorkflowOwnershipError("Follow-Up creation_source is malformed")
        source_type = source.get("type")
        if fresh_digital_write and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Follow-Up authoring accepts "
                "creation_source=digital_entry only"
            )
        if current_use and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "paper/import activation requires accepted review history"
            )

    @staticmethod
    def _require_chronology(record: PortiaRecord) -> None:
        created = record.field("created_at")
        updated = record.field("updated_at")
        require_timestamp_order(
            created,
            updated,
            earlier_name="Follow-Up created_at",
            later_name="Follow-Up updated_at",
        )

        timing = record.field("planned_timing")
        if not isinstance(timing, Mapping):
            raise WorkflowOwnershipError("Follow-Up planned_timing is malformed")
        kind = timing.get("kind")
        if kind == "date_only":
            parse_date_only(
                timing.get("date"),
                field_name="Follow-Up planned date",
            )
            return
        if kind == "exact_time":
            parse_explicit_timestamp(
                timing.get("at"),
                field_name="Follow-Up planned exact time",
            )
            return
        if kind != "window":
            raise WorkflowOwnershipError(
                f"unsupported Follow-Up planned_timing kind {kind!r}"
            )

        if "starts_on" in timing or "ends_on" in timing:
            if "starts_on" not in timing or "ends_on" not in timing:
                raise WorkflowOwnershipError(
                    "Follow-Up date window is incomplete"
                )
            require_date_order(
                timing.get("starts_on"),
                timing.get("ends_on"),
                earlier_name="Follow-Up starts_on",
                later_name="Follow-Up ends_on",
            )
            return
        if "starts_at" in timing or "ends_at" in timing:
            if "starts_at" not in timing or "ends_at" not in timing:
                raise WorkflowOwnershipError(
                    "Follow-Up exact window is incomplete"
                )
            require_timestamp_order(
                timing.get("starts_at"),
                timing.get("ends_at"),
                earlier_name="Follow-Up starts_at",
                later_name="Follow-Up ends_at",
            )
            return
        raise WorkflowOwnershipError("Follow-Up window timing is malformed")

    def _require_owner_authority(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> None:
        owner = record.field("owner")
        if not isinstance(owner, Mapping):
            raise WorkflowOwnershipError("Follow-Up owner is malformed")
        authority = self._authority()
        if work.work_kind == "event":
            if owner.get("kind") != "represented_human":
                raise WorkflowOwnershipError(
                    "Event Follow-Up owner must be represented_human"
                )
            authority.require_event_operational_human(
                owner.get("person"),
                field_name="Follow-Up owner",
                require_current_use=require_current_use,
            )
            return

        if owner.get("kind") != "support_process_participant":
            raise WorkflowOwnershipError(
                "Support Process Follow-Up owner must be "
                "support_process_participant"
            )
        authority.require_support_process_operational_participant(
            work,
            owner.get("participant_ref"),
            field_name="Follow-Up owner",
            allowed_contexts=_FOLLOW_UP_OWNER_CONTEXTS,
            require_current_use=require_current_use,
        )

    def _resolve_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> DownstreamTargetResolution:
        # Follow-Up is inherently downstream. A currently actionable Follow-Up
        # may legitimately target a historical Participant under a closed Event.
        # Resolve the exact target without requiring the parent/Participant to
        # regain current operational status.
        return self._authority().resolve_target(
            work,
            record.field("target"),
            require_current_use=False,
        )

    def _resolve_related_records(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[DownstreamRelatedRecordResolution, ...]:
        record_id = record.logical_id
        if not isinstance(record_id, str):
            raise WorkflowOwnershipError("Follow-Up has no exact record identity")
        return self._authority().resolve_related_records(
            work,
            record.field("related_records"),
            field_name="Follow-Up related_records",
            allowed_roles=_FOLLOW_UP_RELATED_ROLES,
            role_contracts=_FOLLOW_UP_ROLE_CONTRACTS,
            self_reference=follow_up_reference(work, record_id),
            same_work_roles=frozenset({"produced"}),
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
        FollowUpV1,
        DownstreamTargetResolution,
        tuple[DownstreamRelatedRecordResolution, ...],
    ]:
        candidate = self._require_follow_up_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=require_current_use,
        )
        self._require_chronology(candidate)
        self._require_supersession_topology(candidate)
        self._require_owner_authority(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        target = self._resolve_target(work, candidate)
        related = self._resolve_related_records(work, candidate)
        return candidate, target, related

    def _require_current_dependency_quarantine(
        self,
        work: ExactPortiaWorkRef,
        target: DownstreamTargetResolution,
        related: tuple[DownstreamRelatedRecordResolution, ...],
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
        for relation in related:
            self.quarantine.require_allowed(
                work_target(relation.reference.work_ref),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(
                    relation.reference.work_ref,
                    relation.stored.record,
                ),
                "block_current_use",
            )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one fresh digital Follow-Up identity after exact validation."""
        candidate = self._require_follow_up_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=True,
            current_use=False,
        )
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Follow-Up must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Follow-Up identity cannot establish supersession history"
            )

        self._require_chronology(candidate)
        require_current = candidate.status == "active"
        self._require_owner_authority(
            work,
            candidate,
            require_current_use=require_current,
        )
        target = self._resolve_target(work, candidate)
        related = self._resolve_related_records(work, candidate)

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
                related,
            )
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        return self.repository.create_work_record(work, candidate)

    def list_follow_ups(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> FollowUpV1:
        value = self._require_follow_up_record(work, candidate)
        require_coordinated_downstream_transition(prior, value)
        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=value.status == "active",
        )
        self._require_chronology(value)
        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )

        target = self._resolve_target(work, value)
        related = self._resolve_related_records(work, value)
        self._require_supersession_topology(value)

        if value.status == "active":
            self._require_owner_authority(
                work,
                value,
                require_current_use=True,
            )
            self._require_current_dependency_quarantine(
                work,
                target,
                related,
            )
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )
        else:
            self._require_owner_authority(
                work,
                value,
                require_current_use=False,
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
        """Persist one ordinary Follow-Up activation/invalidation."""
        if (
            reference.record_ref.record_kind != "follow_up"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Follow-Up lifecycle requires exact follow_up@1 reference"
            )
        work = reference.work_ref
        coordinator = ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        def validate_transition(prior: PortiaRecord, value: PortiaRecord) -> None:
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
    ) -> FollowUpV1:
        value = self._require_follow_up_record(work, successor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        if prior.status == "superseded":
            raise WorkflowPrerequisiteError(
                "Follow-Up correction cannot reuse a superseded predecessor"
            )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Follow-Up successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Follow-Up predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Follow-Up successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Follow-Up successor updated_at cannot precede predecessor update"
            )
        require_material_follow_up_correction(
            prior,
            value,
            supersession_reason,
        )
        self._require_supersession_topology(value)

        self._require_owner_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        related = self._resolve_related_records(work, value)

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
            related,
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_current_use",
        )
        return value

    def _require_consolidation_successor(
        self,
        work: ExactPortiaWorkRef,
        priors: tuple[PortiaRecord, ...],
        successor: PortiaRecord,
    ) -> FollowUpV1:
        value = self._require_follow_up_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate Follow-Up consolidation successor must be active"
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
            field_name="Follow-Up consolidation successor updated_at",
        )
        for prior in priors:
            self._require_follow_up_record(work, prior)
            require_downstream_lifecycle_reconciled(
                self.repository,
                work,
                prior,
            )
            if prior.status not in {"active", "invalidated"}:
                raise WorkflowPrerequisiteError(
                    "duplicate Follow-Up consolidation predecessor must be "
                    "active or invalidated"
                )
            prior_updated = parse_explicit_timestamp(
                prior.field("updated_at"),
                field_name="Follow-Up consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Follow-Up consolidation successor updated_at cannot "
                    "precede a predecessor update"
                )

        # Duplicate identity is an explicit human-selected supersession fact.
        # Do not infer or require duplication from content similarity here.
        self._require_owner_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        related = self._resolve_related_records(work, value)

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
            related,
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_current_use",
        )
        return value

    def _require_work_root_successor(
        self,
        source_work: ExactPortiaWorkRef,
        destination_work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> FollowUpV1:
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
                "work-root Follow-Up correction predecessor must be "
                "active or invalidated"
            )

        value, target, related = self._validate_existing(
            destination_work,
            successor,
            require_current_use=True,
        )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "work-root Follow-Up correction successor must be active"
            )
        if prior.logical_id != value.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root Follow-Up correction must preserve Follow-Up ID"
            )

        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Follow-Up work-root predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Follow-Up work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Follow-Up work-root successor updated_at cannot precede "
                "predecessor update"
            )

        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_FACT_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root Follow-Up correction cannot rewrite fact "
                    f"{field}"
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
            related,
        )
        self.quarantine.require_allowed(
            record_target(destination_work, value),
            "block_current_use",
        )
        return value

    @staticmethod
    def _related_items(record: PortiaRecord) -> tuple[Mapping[str, object], ...]:
        raw = record.field("related_records")
        if raw is None:
            return ()
        if not isinstance(raw, Sequence) or isinstance(
            raw, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError(
                "Follow-Up related_records are malformed"
            )
        items: list[Mapping[str, object]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    "Follow-Up related_records entry is malformed"
                )
            items.append(item)
        return tuple(items)

    @classmethod
    def _require_completion_enrichment(
        cls,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        prior_related = cls._related_items(prior)
        candidate_related = cls._related_items(candidate)

        for item in prior_related:
            if item not in candidate_related:
                raise WorkflowPrerequisiteError(
                    "Follow-Up completion cannot remove or rewrite an existing "
                    "related-record relation"
                )

        added = tuple(
            item for item in candidate_related if item not in prior_related
        )
        for item in added:
            role = item.get("role")
            if role not in _COMPLETION_LINK_ROLES:
                raise WorkflowPrerequisiteError(
                    "Follow-Up completion may add only reviewed or produced "
                    "related-record relations"
                )

        if prior.field("disposition") is not None:
            raise WorkflowPrerequisiteError(
                "non-completed Follow-Up cannot carry a prior disposition"
            )

    def _require_workflow_state_candidate(
        self,
        reference: ExactPortiaWorkRecordRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> FollowUpV1:
        """Require one same-identity ordinary Follow-Up workflow progression."""
        work = reference.work_ref
        value = self._require_follow_up_record(work, candidate)

        if prior.logical_id != value.logical_id:
            raise WorkflowOwnershipError(
                "Follow-Up workflow-state candidate changed exact record identity"
            )
        if prior.status != value.status:
            raise WorkflowPrerequisiteError(
                "ordinary Follow-Up workflow-state progression cannot change "
                "canonical lifecycle"
            )
        if prior.status != "active":
            raise WorkflowPrerequisiteError(
                "ordinary Follow-Up workflow-state progression requires active "
                "canonical status"
            )

        prior_state = prior.field("workflow_state")
        candidate_state = value.field("workflow_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowOwnershipError("Follow-Up workflow_state is malformed")
        allowed = _WORKFLOW_STATE_TRANSITIONS.get(prior_state)
        if allowed is None or candidate_state not in allowed:
            raise WorkflowPrerequisiteError(
                "illegal Follow-Up workflow_state transition: "
                f"{prior_state} -> {candidate_state}"
            )

        prior_data = prior.to_dict()
        candidate_data = value.to_dict()
        mutable_fields = _WORKFLOW_STATE_MUTABLE_FIELDS
        if candidate_state == "completed":
            mutable_fields = mutable_fields | _COMPLETION_MUTABLE_FIELDS
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - mutable_fields):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Follow-Up workflow-state progression cannot rewrite "
                    f"field {field}"
                )

        if candidate_state == "completed":
            parse_explicit_timestamp(
                value.field("completed_at"),
                field_name="Follow-Up completed_at",
            )
            self._require_completion_enrichment(prior, value)
        elif value.field("completed_at") is not None:
            raise WorkflowPrerequisiteError(
                "non-completed Follow-Up workflow state cannot carry completed_at"
            )

        require_timestamp_order(
            prior.field("updated_at"),
            value.field("updated_at"),
            earlier_name="Follow-Up prior updated_at",
            later_name="Follow-Up updated_at",
        )

        _, target, related = self._validate_existing(
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
            related,
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
        """Create one corrected Follow-Up successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "follow_up"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Follow-Up correction requires exact follow_up@1 predecessor"
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
        """Create one active canonical Follow-Up from explicit duplicates."""
        predecessors = require_duplicate_downstream_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Follow-Up consolidation requires one expected "
                "fingerprint for every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Follow-Up consolidation requires one lifecycle "
                "transition ID for every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Follow-Up consolidation lifecycle transition IDs "
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
        """Move one corrected Follow-Up representation to its true work root."""
        if (
            predecessor.record_ref.record_kind != "follow_up"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Follow-Up work-root correction requires exact follow_up@1 "
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

    def transition_workflow_state(
        self,
        reference: ExactPortiaWorkRecordRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Persist one bounded ordinary Follow-Up workflow-state progression."""
        if (
            reference.record_ref.record_kind != "follow_up"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Follow-Up workflow progression requires exact follow_up@1 reference"
            )

        prior = self.load_exact(reference)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Follow-Up state does not match canonical bytes"
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
        """Require one exact active Follow-Up without following successors."""
        follow_up = self.load_exact(reference)
        require_downstream_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            follow_up.record,
        )
        candidate, target, related = self._validate_existing(
            reference.work_ref,
            follow_up.record,
            require_current_use=False,
        )
        if candidate.status != "active":
            raise WorkflowPrerequisiteError(
                "current Follow-Up use requires active canonical status"
            )

        # Only an active canonical Follow-Up may demand current operational
        # owner/materialization authority. Historical/proposed records remain
        # exactly readable without upgrading weak preserved identity into
        # operational authority.
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
        self._require_owner_authority(
            reference.work_ref,
            candidate,
            require_current_use=True,
        )
        self._require_current_dependency_quarantine(
            reference.work_ref,
            target,
            related,
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, candidate),
            "block_current_use",
        )
        return follow_up

    resolve_current = require_current_use
