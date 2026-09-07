"""Production core workflow service for work-local ``reentry@1`` records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, ReentryV1
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
    require_material_reentry_correction,
    superseded_downstream_predecessor,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_REENTRY_COORDINATOR_CONTEXTS = frozenset(
    {"provider_or_collaborator", "coordinator"}
)
_REENTRY_RECORD_CONTEXTS = frozenset(
    {"determination", "response", "communication"}
)
_REENTRY_WORK_CONTEXTS = frozenset({"event", "support_process"})
_REENTRY_INERT_CONTEXTS = frozenset(
    {"external_or_restricted_process", "other"}
)
_REENTRY_SUPPORT_PLAN_CONTRACTS = frozenset({"support", "intervention"})


_WORKFLOW_STATE_TRANSITIONS = {
    "planned": frozenset(
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
    {"workflow_state", "completed_at", "updated_at", "updated_by"}
)


_WORK_ROOT_PRESERVED_FACT_FIELDS = (
    "initiating_context",
    "planned_return",
    "planned_elements",
    "support_refs",
    "workflow_state",
    "completed_at",
    "creation_source",
)


@dataclass(frozen=True, slots=True)
class ReentryContextResolution:
    """One exact initiating-context dependency, if the context is Portia-local."""

    kind: str
    work: ExactPortiaWorkRef | None = None
    record: DownstreamExactRecordResolution | None = None


class ReentryWorkflowService(ActionReadService):
    """Create and qualify exact teacher-local ``reentry@1`` records."""

    CONTRACT = "reentry"

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
    def _require_reentry_record(
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> ReentryV1:
        require_downstream_record_owner(work, record, contract="reentry")
        if not isinstance(record, ReentryV1):
            raise WorkflowOwnershipError(
                "Reentry workflow requires reentry@1 input"
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
            raise WorkflowOwnershipError("Reentry creation_source is malformed")
        source_type = source.get("type")
        if fresh_digital_write and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Reentry authoring accepts "
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
            earlier_name="Reentry created_at",
            later_name="Reentry updated_at",
        )

        planned = record.field("planned_return")
        if not isinstance(planned, Mapping):
            raise WorkflowOwnershipError("Reentry planned_return is malformed")
        kind = planned.get("kind")
        if kind == "date_only":
            parse_date_only(
                planned.get("date"),
                field_name="Reentry planned return date",
            )
            return
        if kind == "exact_time":
            parse_explicit_timestamp(
                planned.get("at"),
                field_name="Reentry planned return exact time",
            )
            return
        if kind != "window":
            raise WorkflowOwnershipError(
                f"unsupported Reentry planned_return kind {kind!r}"
            )

        if "starts_on" in planned or "ends_on" in planned:
            if "starts_on" not in planned or "ends_on" not in planned:
                raise WorkflowOwnershipError(
                    "Reentry planned return date window is incomplete"
                )
            require_date_order(
                planned.get("starts_on"),
                planned.get("ends_on"),
                earlier_name="Reentry starts_on",
                later_name="Reentry ends_on",
            )
            return
        if "starts_at" in planned or "ends_at" in planned:
            if "starts_at" not in planned or "ends_at" not in planned:
                raise WorkflowOwnershipError(
                    "Reentry planned return exact window is incomplete"
                )
            require_timestamp_order(
                planned.get("starts_at"),
                planned.get("ends_at"),
                earlier_name="Reentry starts_at",
                later_name="Reentry ends_at",
            )
            return
        raise WorkflowOwnershipError(
            "Reentry planned return window is malformed"
        )

    def _require_coordinator_authority(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> None:
        coordinator = record.field("coordinator")
        if not isinstance(coordinator, Mapping):
            raise WorkflowOwnershipError("Reentry coordinator is malformed")
        authority = self._authority()

        if work.work_kind == "event":
            if coordinator.get("kind") != "represented_human":
                raise WorkflowOwnershipError(
                    "Event Reentry coordinator must be represented_human"
                )
            authority.require_event_operational_human(
                coordinator.get("person"),
                field_name="Reentry coordinator",
                require_current_use=require_current_use,
            )
            return

        if coordinator.get("kind") != "support_process_participant":
            raise WorkflowOwnershipError(
                "Support Process Reentry coordinator must be "
                "support_process_participant"
            )
        authority.require_support_process_operational_participant(
            work,
            coordinator.get("participant_ref"),
            field_name="Reentry coordinator",
            allowed_contexts=_REENTRY_COORDINATOR_CONTEXTS,
            require_current_use=require_current_use,
        )

    def _resolve_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> DownstreamTargetResolution:
        # Reentry is downstream of an interruption/context. Its target may be
        # historical exact evidence even when the parent Event has closed.
        return self._authority().resolve_target(
            work,
            record.field("target"),
            require_current_use=False,
        )

    def _resolve_work_context(
        self,
        owner_work: ExactPortiaWorkRef,
        raw_work: object,
        *,
        kind: str,
    ) -> ReentryContextResolution:
        if not isinstance(raw_work, Mapping):
            raise WorkflowOwnershipError(
                "Reentry initiating context work reference is malformed"
            )
        try:
            reference = ExactPortiaWorkRef.from_dict(raw_work)
        except (TypeError, ValueError) as exc:
            raise WorkflowOwnershipError(
                "Reentry initiating context work reference is malformed"
            ) from exc
        if reference.work_kind != kind:
            raise WorkflowOwnershipError(
                "Reentry initiating context kind and work reference disagree"
            )
        if reference.class_id != owner_work.class_id:
            raise WorkflowOwnershipError(
                "Reentry initiating context must remain in the owning class"
            )
        try:
            self._authority().load_owner_exact(reference)
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                "Reentry initiating context work does not resolve"
            ) from exc
        return ReentryContextResolution(kind=kind, work=reference)

    def _resolve_initiating_context(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> ReentryContextResolution:
        context = record.field("initiating_context")
        if not isinstance(context, Mapping):
            raise WorkflowOwnershipError(
                "Reentry initiating_context is malformed"
            )
        kind = context.get("kind")
        if not isinstance(kind, str):
            raise WorkflowOwnershipError(
                "Reentry initiating_context kind is malformed"
            )
        if kind in _REENTRY_WORK_CONTEXTS:
            return self._resolve_work_context(
                work,
                context.get("work_ref"),
                kind=kind,
            )
        if kind in _REENTRY_RECORD_CONTEXTS:
            exact = self._authority().resolve_exact_work_record(
                work,
                context.get("record_ref"),
                field_name="Reentry initiating context",
                require_same_class=True,
                require_same_work=False,
            )
            if exact.reference.record_ref.record_kind != kind:
                raise WorkflowOwnershipError(
                    "Reentry initiating context kind and record reference disagree"
                )
            return ReentryContextResolution(
                kind=kind,
                work=exact.reference.work_ref,
                record=exact,
            )
        if kind in _REENTRY_INERT_CONTEXTS:
            return ReentryContextResolution(kind=kind)
        raise WorkflowOwnershipError(
            f"unsupported Reentry initiating_context kind {kind!r}"
        )

    def _resolve_support_refs(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[DownstreamExactRecordResolution, ...]:
        raw_values = record.field("support_refs")
        if raw_values is None:
            return ()
        if not isinstance(raw_values, Sequence) or isinstance(
            raw_values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Reentry support_refs are malformed")

        resolved: list[DownstreamExactRecordResolution] = []
        seen: set[ExactPortiaWorkRecordRef] = set()
        for index, value in enumerate(raw_values):
            if not isinstance(value, Mapping):
                raise WorkflowOwnershipError(
                    f"Reentry support_refs[{index}] is malformed"
                )
            try:
                reference = ExactPortiaWorkRecordRef.from_dict(value)
            except (TypeError, ValueError) as exc:
                raise WorkflowOwnershipError(
                    f"Reentry support_refs[{index}] is malformed"
                ) from exc
            if reference in seen:
                raise WorkflowPrerequisiteError(
                    "Reentry support_refs cannot repeat one exact plan reference"
                )
            if (
                reference.work_ref.work_kind != "support_process"
                or reference.work_ref.contract_version != "1"
                or reference.record_ref.record_kind
                not in _REENTRY_SUPPORT_PLAN_CONTRACTS
                or reference.record_ref.contract_version != "1"
            ):
                raise WorkflowOwnershipError(
                    "Reentry support_refs require exact support/intervention@1 "
                    "records under support_process@1"
                )
            if reference.work_ref.class_id != work.class_id:
                raise WorkflowOwnershipError(
                    "Reentry support plan must remain in the owning class"
                )
            if (
                work.work_kind == "support_process"
                and reference.work_ref != work
            ):
                raise WorkflowOwnershipError(
                    "Support-Process-owned Reentry plan must share process"
                )

            exact = self._authority().resolve_exact_work_record(
                work,
                reference.to_dict(),
                field_name=f"Reentry support_refs[{index}]",
                require_same_class=True,
                require_same_work=work.work_kind == "support_process",
            )
            seen.add(reference)
            resolved.append(exact)
        return tuple(resolved)

    @staticmethod
    def _require_planned_elements(record: PortiaRecord) -> None:
        elements = record.field("planned_elements")
        if not isinstance(elements, Sequence) or isinstance(
            elements, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Reentry planned_elements are malformed")
        if not elements:
            raise WorkflowPrerequisiteError(
                "Reentry requires at least one bounded planned element"
            )
        for index, element in enumerate(elements):
            if not isinstance(element, Mapping):
                raise WorkflowOwnershipError(
                    f"Reentry planned_elements[{index}] is malformed"
                )
            kind = element.get("kind")
            description = element.get("description")
            if not isinstance(kind, str) or not isinstance(description, str):
                raise WorkflowOwnershipError(
                    f"Reentry planned_elements[{index}] is malformed"
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
        ReentryV1,
        DownstreamTargetResolution,
        ReentryContextResolution,
        tuple[DownstreamExactRecordResolution, ...],
    ]:
        candidate = self._require_reentry_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=require_current_use,
        )
        self._require_chronology(candidate)
        self._require_planned_elements(candidate)
        self._require_supersession_topology(candidate)
        self._require_coordinator_authority(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        target = self._resolve_target(work, candidate)
        context = self._resolve_initiating_context(work, candidate)
        support_refs = self._resolve_support_refs(work, candidate)
        return candidate, target, context, support_refs

    def _require_current_dependency_quarantine(
        self,
        work: ExactPortiaWorkRef,
        target: DownstreamTargetResolution,
        context: ReentryContextResolution,
        support_refs: tuple[DownstreamExactRecordResolution, ...],
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

        for exact in support_refs:
            self.quarantine.require_allowed(
                work_target(exact.reference.work_ref),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(
                    exact.reference.work_ref,
                    exact.stored.record,
                ),
                "block_current_use",
            )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one fresh digital Reentry identity after exact validation."""
        candidate = self._require_reentry_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=True,
            current_use=False,
        )
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Reentry must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Reentry identity cannot establish supersession history"
            )

        self._require_chronology(candidate)
        self._require_planned_elements(candidate)
        require_current = candidate.status == "active"
        self._require_coordinator_authority(
            work,
            candidate,
            require_current_use=require_current,
        )
        target = self._resolve_target(work, candidate)
        context = self._resolve_initiating_context(work, candidate)
        support_refs = self._resolve_support_refs(work, candidate)

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
                context,
                support_refs,
            )
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        return self.repository.create_work_record(work, candidate)

    def list_reentries(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> ReentryV1:
        value = self._require_reentry_record(work, candidate)
        require_coordinated_downstream_transition(prior, value)
        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=value.status == "active",
        )
        self._require_chronology(value)
        self._require_planned_elements(value)
        self._require_supersession_topology(value)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, value),
            "block_work_writes",
        )

        target = self._resolve_target(work, value)
        context = self._resolve_initiating_context(work, value)
        support_refs = self._resolve_support_refs(work, value)

        if value.status == "active":
            self._require_coordinator_authority(
                work,
                value,
                require_current_use=True,
            )
            self._require_current_dependency_quarantine(
                work,
                target,
                context,
                support_refs,
            )
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )
        else:
            self._require_coordinator_authority(
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
        """Persist one ordinary Reentry activation/invalidation."""
        if (
            reference.record_ref.record_kind != "reentry"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Reentry lifecycle requires exact reentry@1 reference"
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
    ) -> ReentryV1:
        value = self._require_reentry_record(work, successor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        if prior.status == "superseded":
            raise WorkflowPrerequisiteError(
                "Reentry correction cannot reuse a superseded predecessor"
            )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Reentry successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        self._require_planned_elements(value)
        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Reentry predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Reentry successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Reentry successor updated_at cannot precede predecessor update"
            )
        require_material_reentry_correction(
            prior,
            value,
            supersession_reason,
        )
        self._require_supersession_topology(value)

        self._require_coordinator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        context = self._resolve_initiating_context(work, value)
        support_refs = self._resolve_support_refs(work, value)

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
            context,
            support_refs,
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
        """Create one corrected Reentry successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "reentry"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Reentry correction requires exact reentry@1 predecessor"
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
    ) -> ReentryV1:
        value = self._require_reentry_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate Reentry consolidation successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        self._require_planned_elements(value)
        self._require_supersession_topology(value)

        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Reentry consolidation successor updated_at",
        )
        for prior in priors:
            self._require_reentry_record(work, prior)
            require_downstream_lifecycle_reconciled(
                self.repository,
                work,
                prior,
            )
            if prior.status not in {"active", "invalidated"}:
                raise WorkflowPrerequisiteError(
                    "duplicate Reentry consolidation predecessor must be "
                    "active or invalidated"
                )
            prior_updated = parse_explicit_timestamp(
                prior.field("updated_at"),
                field_name="Reentry consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Reentry consolidation successor updated_at cannot "
                    "precede a predecessor update"
                )

        # Duplication is an explicit human-selected supersession fact.
        # Portia does not infer duplicate Reentry identity from content.
        self._require_coordinator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        context = self._resolve_initiating_context(work, value)
        support_refs = self._resolve_support_refs(work, value)

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
            context,
            support_refs,
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
        """Create one active canonical Reentry from explicit duplicates."""
        predecessors = require_duplicate_downstream_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Reentry consolidation requires one expected "
                "fingerprint for every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Reentry consolidation requires one lifecycle "
                "transition ID for every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Reentry consolidation lifecycle transition IDs "
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

    def _require_work_root_successor(
        self,
        source_work: ExactPortiaWorkRef,
        destination_work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> ReentryV1:
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
                "work-root Reentry correction predecessor must be "
                "active or invalidated"
            )

        value, target, context, support_refs = self._validate_existing(
            destination_work,
            successor,
            require_current_use=True,
        )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "work-root Reentry correction successor must be active"
            )
        if prior.logical_id != value.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root Reentry correction must preserve Reentry ID"
            )

        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Reentry work-root predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Reentry work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Reentry work-root successor updated_at cannot precede "
                "predecessor update"
            )

        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_FACT_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root Reentry correction cannot rewrite fact "
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
            context,
            support_refs,
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
        """Move one Reentry representation to its corrected owning work root."""
        if (
            predecessor.record_ref.record_kind != "reentry"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Reentry work-root correction requires exact reentry@1 "
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

    def _require_workflow_state_candidate(
        self,
        reference: ExactPortiaWorkRecordRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> ReentryV1:
        """Require one same-identity ordinary Reentry workflow progression."""
        work = reference.work_ref
        value = self._require_reentry_record(work, candidate)

        if prior.logical_id != value.logical_id:
            raise WorkflowOwnershipError(
                "Reentry workflow-state candidate changed exact record identity"
            )
        if prior.status != value.status:
            raise WorkflowPrerequisiteError(
                "ordinary Reentry workflow-state progression cannot change "
                "canonical lifecycle"
            )
        if prior.status != "active":
            raise WorkflowPrerequisiteError(
                "ordinary Reentry workflow-state progression requires active "
                "canonical status"
            )

        prior_state = prior.field("workflow_state")
        candidate_state = value.field("workflow_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowOwnershipError("Reentry workflow_state is malformed")
        allowed = _WORKFLOW_STATE_TRANSITIONS.get(prior_state)
        if allowed is None or candidate_state not in allowed:
            raise WorkflowPrerequisiteError(
                "illegal Reentry workflow_state transition: "
                f"{prior_state} -> {candidate_state}"
            )

        prior_data = prior.to_dict()
        candidate_data = value.to_dict()
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - _WORKFLOW_STATE_MUTABLE_FIELDS):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Reentry workflow-state progression cannot rewrite "
                    f"field {field}"
                )

        if candidate_state == "completed":
            parse_explicit_timestamp(
                value.field("completed_at"),
                field_name="Reentry completed_at",
            )
        elif value.field("completed_at") is not None:
            raise WorkflowPrerequisiteError(
                "non-completed Reentry workflow state cannot carry completed_at"
            )

        require_timestamp_order(
            prior.field("updated_at"),
            value.field("updated_at"),
            earlier_name="Reentry prior updated_at",
            later_name="Reentry updated_at",
        )

        _, target, context, support_refs = self._validate_existing(
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
            context,
            support_refs,
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
        """Persist one bounded ordinary Reentry workflow-state progression."""
        if (
            reference.record_ref.record_kind != "reentry"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Reentry workflow progression requires exact reentry@1 reference"
            )

        prior = self.load_exact(reference)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Reentry state does not match canonical bytes"
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
        """Require one exact active Reentry without following successors."""
        reentry = self.load_exact(reference)
        require_downstream_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            reentry.record,
        )
        candidate, target, context, support_refs = self._validate_existing(
            reference.work_ref,
            reentry.record,
            require_current_use=False,
        )
        if candidate.status != "active":
            raise WorkflowPrerequisiteError(
                "current Reentry use requires active canonical status"
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
        self._require_coordinator_authority(
            reference.work_ref,
            candidate,
            require_current_use=True,
        )
        self._require_current_dependency_quarantine(
            reference.work_ref,
            target,
            context,
            support_refs,
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, candidate),
            "block_current_use",
        )
        return reentry

    resolve_current = require_current_use
