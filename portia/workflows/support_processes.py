"""Production bootstrap workflow for canonical ``support_process@1`` roots."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import TYPE_CHECKING

from portia.models import PortiaRecord, SupportProcessV1
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaConflictError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import work_root
from portia.storage.repository import StoredRecord
from portia.workflows.common import WorkflowServiceBase, work_target
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
from portia.workflows.support_process_lifecycle import (
    build_support_process_lifecycle_transition,
    require_coordinated_support_process_transition,
    require_support_process_lifecycle_reconciled,
)
from portia.workflows.support_process_supersession import (
    require_exact_support_process_correction_predecessor,
    require_material_support_process_correction,
    superseded_support_process_predecessor,
    support_process_supersession_ancestry,
    support_process_supersession_reason_detail,
)
from portia.workflows.work_transition import WorkLifecycleCoordinator

if TYPE_CHECKING:
    from portia.workflows.support_process_participants import (
        SupportProcessParticipantWorkflowService,
    )

SUPPORT_PROCESS_VERSION = "1"

_WORKFLOW_STATE_TRANSITIONS = {
    "planning": frozenset({"active", "cancelled"}),
    "active": frozenset({"paused", "completed", "discontinued"}),
    "paused": frozenset({"active", "completed", "discontinued"}),
    "completed": frozenset(),
    "discontinued": frozenset(),
    "cancelled": frozenset(),
}
_WORKFLOW_STATE_MUTABLE_FIELDS = frozenset(
    {"workflow_state", "updated_at", "updated_by"}
)

_REFERENCE_INITIATION_KINDS = frozenset(
    {
        "event_context",
        "review_context",
        "determination_context",
        "response_handoff",
        "represented_request",
    }
)
_LOCAL_BOOTSTRAP_INITIATION_KINDS = frozenset(
    {"teacher_identified_need", "other"}
)


def support_process_reference(record: PortiaRecord) -> ExactPortiaWorkRef:
    """Construct the exact ``support_process@1`` work reference for one root."""
    if (
        not isinstance(record, SupportProcessV1)
        or record.class_id is None
        or record.work_id is None
    ):
        raise WorkflowOwnershipError(
            "Support Process workflow writes require support_process@1 input"
        )
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="support_process",
        contract_version=SUPPORT_PROCESS_VERSION,
    )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp lacks an explicit offset"
        )
    return parsed


def _parse_date(value: object, *, field_name: str) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} date is malformed"
        )
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} date is malformed"
        ) from exc


def _require_consecutive_school_year(record: SupportProcessV1) -> None:
    value = record.field("school_year")
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError("Support Process school_year is malformed")
    try:
        start_text, end_text = value.split("-", maxsplit=1)
        start = int(start_text)
        end = int(end_text)
    except (TypeError, ValueError) as exc:
        raise WorkflowPrerequisiteError(
            "Support Process school_year is malformed"
        ) from exc
    if end != start + 1:
        raise WorkflowPrerequisiteError(
            "Support Process school_year must name consecutive academic years"
        )


def _require_planned_date_chronology(record: SupportProcessV1) -> None:
    planned_start = _parse_date(
        record.field("planned_start_date"),
        field_name="planned_start_date",
    )
    planned_end = _parse_date(
        record.field("planned_end_date"),
        field_name="planned_end_date",
    )
    review_on = _parse_date(record.field("review_on"), field_name="review_on")
    if (
        planned_start is not None
        and planned_end is not None
        and planned_end < planned_start
    ):
        raise WorkflowPrerequisiteError(
            "Support Process planned_end_date cannot precede planned_start_date"
        )
    if (
        planned_start is not None
        and review_on is not None
        and review_on < planned_start
    ):
        raise WorkflowPrerequisiteError(
            "Support Process review_on cannot precede planned_start_date"
        )


def _require_digital_bootstrap(record: SupportProcessV1) -> None:
    if record.status != "proposed":
        raise WorkflowPrerequisiteError(
            "standalone Support Process creation must begin proposed so Participants "
            "can establish current-use authority before activation"
        )
    if record.field("workflow_state") != "planning":
        raise WorkflowPrerequisiteError(
            "new proposed Support Process must begin in planning workflow state"
        )

    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "v0.2 Support Process authoring supports digital_entry only"
        )

    created_at = _parse_timestamp(record.field("created_at"), field_name="created_at")
    updated_at = _parse_timestamp(record.field("updated_at"), field_name="updated_at")
    if updated_at < created_at:
        raise WorkflowPrerequisiteError(
            "Support Process updated_at cannot precede created_at"
        )

    _require_consecutive_school_year(record)
    _require_planned_date_chronology(record)

    if record.field("supersedes") is not None:
        raise WorkflowPrerequisiteError(
            "fresh Support Process bootstrap cannot create correction/supersession "
            "history; use the coordinated successor path in a later Issue #44 slice"
        )

    initiation = record.field("initiation")
    if not isinstance(initiation, Mapping):
        raise WorkflowOwnershipError("Support Process initiation is malformed")
    kind = initiation.get("kind")
    if kind in _LOCAL_BOOTSTRAP_INITIATION_KINDS:
        return
    if kind == "imported_history":
        raise WorkflowPrerequisiteError(
            "imported_history initiation requires import provenance and is not a "
            "digital-entry bootstrap"
        )
    if kind in _REFERENCE_INITIATION_KINDS:
        return
    raise WorkflowOwnershipError(
        f"unsupported Support Process initiation kind {kind!r}"
    )


def _require_active_digital_materialization(record: SupportProcessV1) -> None:
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "Support Process current activation currently requires digital_entry "
            "provenance; paper/import review history is deferred"
        )
    created_at = _parse_timestamp(record.field("created_at"), field_name="created_at")
    updated_at = _parse_timestamp(record.field("updated_at"), field_name="updated_at")
    if updated_at < created_at:
        raise WorkflowPrerequisiteError(
            "Support Process updated_at cannot precede created_at"
        )
    _require_consecutive_school_year(record)
    _require_planned_date_chronology(record)


class SupportProcessWorkflowService(WorkflowServiceBase):
    """Create, enumerate, and resolve proposed Support Process bootstrap roots."""

    def _require_initiation_authority(
        self,
        record: SupportProcessV1,
    ) -> None:
        require_support_process_initiation_authority(
            self.workspace_root,
            self.repository,
            self.quarantine,
            self.contexts,
            record,
        )

    def _continuation_ancestry(
        self,
        record: SupportProcessV1,
    ) -> tuple[StoredRecord, ...]:
        return support_process_continuation_ancestry(
            self.repository,
            record,
        )

    def _validate_support_process_graph(
        self,
        root: SupportProcessV1,
        records: tuple[PortiaRecord, ...],
        *,
        require_actor_current_use: bool = False,
    ) -> None:
        del root
        validate_support_process_graph(
            self.contexts,
            records,
            require_actor_current_use=require_actor_current_use,
        )

    def create(self, record: PortiaRecord) -> StoredRecord:
        work = support_process_reference(record)
        candidate = record
        if not isinstance(candidate, SupportProcessV1):
            raise WorkflowOwnershipError(
                "Support Process workflow writes require support_process@1 input"
            )
        _require_digital_bootstrap(candidate)
        self._require_initiation_authority(candidate)
        continuation = self._continuation_ancestry(candidate)
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        self._validate_support_process_graph(
            candidate,
            (*continuation_records, candidate),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        return self.repository.create_work(work, candidate)

    def load_exact(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if (
            work.work_kind != "support_process"
            or work.contract_version != SUPPORT_PROCESS_VERSION
        ):
            raise WorkflowOwnershipError(
                "Support Process load requires an exact support_process@1 "
                "work reference"
            )
        return self.repository.load_work(work)

    def resolve_exact(self, work: ExactPortiaWorkRef) -> StoredRecord:
        """Resolve exactly the requested root without successor following."""
        return self.load_exact(work)

    def list(self, class_id: str) -> tuple[StoredRecord, ...]:
        return self.repository.list_works(
            class_id,
            work_kind="support_process",
            version=SUPPORT_PROCESS_VERSION,
        )

    list_support_processes = list

    def _participant_service(
        self,
    ) -> SupportProcessParticipantWorkflowService:
        from portia.workflows.support_process_participants import (
            SupportProcessParticipantWorkflowService,
        )

        return SupportProcessParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _active_supported_participants(
        self,
        work: ExactPortiaWorkRef,
        *,
        for_activation: bool,
    ) -> tuple[StoredRecord, ...]:
        from portia.workflows.support_process_participants import (
            has_supported_person_context,
            support_process_participant_reference,
        )

        participant_service = self._participant_service()
        active = tuple(
            stored
            for stored in participant_service.list(work)
            if stored.record.status == "active"
        )
        supported = False
        for stored in active:
            if stored.record.logical_id is None:
                raise WorkflowOwnershipError(
                    "Support Process Participant has no exact logical identity"
                )
            reference = support_process_participant_reference(
                work,
                stored.record.logical_id,
            )
            if for_activation:
                participant_service.require_activation_eligibility(reference)
            else:
                participant_service.require_current_use(reference)
            supported = supported or has_supported_person_context(stored.record)
        if not supported:
            raise WorkflowPrerequisiteError(
                "Support Process requires at least one eligible active "
                "supported_person Participant"
            )
        return active

    def _supersession_ancestry(
        self,
        record: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        if not isinstance(record, SupportProcessV1):
            raise WorkflowOwnershipError(
                "Support Process supersession ancestry requires support_process@1"
            )
        ancestry = support_process_supersession_ancestry(
            self.repository,
            record,
        )
        for predecessor in ancestry:
            predecessor_work = support_process_reference(predecessor.record)
            self.quarantine.require_allowed(
                work_target(predecessor_work),
                "block_current_use",
            )
        return ancestry

    def _require_no_canonical_children(
        self,
        work: ExactPortiaWorkRef,
    ) -> None:
        records_root = work_root(self.workspace_root, work) / "records"
        if not records_root.exists():
            return
        if not records_root.is_dir():
            raise WorkflowPrerequisiteError(
                "Support Process records boundary is not a directory"
            )
        canonical = tuple(
            path
            for path in records_root.rglob("*.json")
            if ".portia-staging" not in path.parts
        )
        if canonical:
            raise WorkflowPrerequisiteError(
                "proposed Support Process correction requires a root with no "
                "canonical child records; child reconciliation belongs to the "
                "later work_root_corrected topology workflow"
            )

    def require_activation_eligibility(
        self, work: ExactPortiaWorkRef
    ) -> StoredRecord:
        """Require active supported-person authority before root activation."""
        root = self.load_exact(work)
        if root.record.status != "proposed":
            raise WorkflowPrerequisiteError(
                "Support Process activation eligibility requires proposed lifecycle"
            )
        if root.record.field("workflow_state") != "planning":
            raise WorkflowPrerequisiteError(
                "Support Process activation eligibility requires planning "
                "workflow state"
            )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        ancestry = self._supersession_ancestry(root.record)
        active = self._active_supported_participants(work, for_activation=True)
        assert isinstance(root.record, SupportProcessV1)
        self._require_initiation_authority(root.record)
        continuation = self._continuation_ancestry(root.record)
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        self._validate_support_process_graph(
            root.record,
            (
                *(stored.record for stored in ancestry),
                *continuation_records,
                root.record,
                *(stored.record for stored in active),
            ),
            require_actor_current_use=True,
        )
        return root

    def _require_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        if not isinstance(prior, SupportProcessV1) or not isinstance(
            candidate, SupportProcessV1
        ):
            raise WorkflowOwnershipError(
                "Support Process lifecycle requires support_process@1 records"
            )
        if support_process_reference(candidate) != work:
            raise WorkflowOwnershipError(
                "Support Process lifecycle candidate does not match selected work"
            )
        require_coordinated_support_process_transition(prior, candidate)
        _require_active_digital_materialization(candidate)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        if candidate.status == "active":
            self.require_activation_eligibility(work)
            ancestry = self._supersession_ancestry(candidate)
            continuation = self._continuation_ancestry(candidate)
            continuation_records = tuple(
                stored.record for stored in continuation
            )
            active = self._active_supported_participants(
                work,
                for_activation=True,
            )
            self._validate_support_process_graph(
                candidate,
                (
                    *(stored.record for stored in ancestry),
                    *continuation_records,
                    candidate,
                    *(stored.record for stored in active),
                ),
                require_actor_current_use=True,
            )
            return
        ancestry = self._supersession_ancestry(candidate)
        continuation = self._continuation_ancestry(candidate)
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        self._validate_support_process_graph(
            candidate,
            (
                *(stored.record for stored in ancestry),
                *continuation_records,
                candidate,
            ),
        )

    def transition_lifecycle(
        self,
        work: ExactPortiaWorkRef,
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
        """Persist one ordinary Support Process activation/invalidation."""
        coordinator = WorkLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        result = coordinator.commit(
            work,
            candidate,
            expected=expected,
            transition_id=transition_id,
            reason_code=reason_code,
            operation_id=operation_id,
            fault_hook=fault_hook,
            candidate_validator=lambda prior, value: self._require_transition_candidate(
                work,
                prior,
                value,
            ),
            transition_factory=lambda prior, value: (
                build_support_process_lifecycle_transition(
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
        accepted = self.load_exact(work)
        require_support_process_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

    def _require_correction_candidate(
        self,
        predecessor: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
    ) -> None:
        if not isinstance(prior, SupportProcessV1) or not isinstance(
            successor, SupportProcessV1
        ):
            raise WorkflowOwnershipError(
                "Support Process correction requires support_process@1 roots"
            )
        if prior.status != "proposed" or prior.field("workflow_state") != "planning":
            raise WorkflowPrerequisiteError(
                "active or progressed Support Process correction requires the later "
                "work-root child-reconciliation workflow"
            )
        reason = require_exact_support_process_correction_predecessor(
            predecessor,
            successor,
        )
        require_material_support_process_correction(
            prior,
            successor,
            reason=reason,
        )
        self._require_no_canonical_children(predecessor)
        _require_active_digital_materialization(successor)
        if prior.to_dict().get("initiation") != successor.to_dict().get(
            "initiation"
        ):
            self._require_initiation_authority(successor)
        predecessor_candidate = superseded_support_process_predecessor(
            prior,
            successor,
        )
        ancestry = self._supersession_ancestry(prior)
        continuation = self._continuation_ancestry(successor)
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        self._validate_support_process_graph(
            successor,
            (
                *(stored.record for stored in ancestry),
                *continuation_records,
                predecessor_candidate,
                successor,
            ),
        )

    def correct(
        self,
        predecessor: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Correct one untouched proposed/planning Support Process root."""
        reason = require_exact_support_process_correction_predecessor(
            predecessor,
            successor,
        )
        reason_check, reason_detail = support_process_supersession_reason_detail(
            successor
        )
        if reason_check != reason:
            raise WorkflowPrerequisiteError(
                "Support Process correction reason changed during preflight"
            )
        coordinator = WorkLifecycleCoordinator(
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
            supersession_reason=reason,
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=lambda old, value: self._require_correction_candidate(
                predecessor,
                old,
                value,
            ),
            predecessor_factory=superseded_support_process_predecessor,
            transition_factory=lambda old, predecessor_candidate: (
                build_support_process_lifecycle_transition(
                    self.repository,
                    predecessor,
                    old,
                    predecessor_candidate,
                    transition_id=transition_id,
                    reason_code=reason,
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                    allow_supersession=True,
                )
            ),
        )
        accepted_predecessor = self.load_exact(predecessor)
        require_support_process_lifecycle_reconciled(
            self.repository,
            predecessor,
            accepted_predecessor.record,
        )
        support_process_supersession_ancestry(self.repository, successor)
        return result

    def _require_workflow_state_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> SupportProcessV1:
        """Require one same-identity ordinary workflow-state revision."""
        if not isinstance(prior, SupportProcessV1) or not isinstance(
            candidate, SupportProcessV1
        ):
            raise WorkflowOwnershipError(
                "Support Process workflow-state progression requires "
                "support_process@1 records"
            )
        if support_process_reference(candidate) != work:
            raise WorkflowOwnershipError(
                "Support Process workflow-state candidate does not match selected work"
            )
        if prior.status != candidate.status:
            raise WorkflowPrerequisiteError(
                "ordinary Support Process workflow-state progression cannot change "
                "canonical lifecycle"
            )
        if prior.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "ordinary Support Process workflow-state progression requires a "
                "proposed or active canonical lifecycle"
            )

        prior_state = prior.field("workflow_state")
        candidate_state = candidate.field("workflow_state")
        if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
            raise WorkflowPrerequisiteError(
                "Support Process workflow_state is incomplete"
            )
        allowed = _WORKFLOW_STATE_TRANSITIONS.get(prior_state)
        if allowed is None or candidate_state not in allowed:
            raise WorkflowPrerequisiteError(
                f"illegal Support Process workflow_state transition "
                f"{prior_state!r} -> {candidate_state!r}"
            )
        if prior.status == "proposed" and candidate_state != "cancelled":
            raise WorkflowPrerequisiteError(
                "Support Process must activate canonical lifecycle before entering "
                "an active workflow_state"
            )

        prior_data = prior.to_dict()
        candidate_data = candidate.to_dict()
        fields = set(prior_data) | set(candidate_data)
        for field in sorted(fields - _WORKFLOW_STATE_MUTABLE_FIELDS):
            if prior_data.get(field) != candidate_data.get(field):
                raise WorkflowPrerequisiteError(
                    "ordinary Support Process workflow-state revision cannot rewrite "
                    f"field {field}"
                )

        _require_active_digital_materialization(candidate)
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            field_name="prior updated_at",
        )
        candidate_updated = _parse_timestamp(
            candidate.field("updated_at"),
            field_name="updated_at",
        )
        if candidate_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Support Process workflow-state updated_at cannot precede "
                "the prior revision"
            )

        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        if prior.status == "active":
            self.require_current_use(work)
            active = self._active_supported_participants(
                work,
                for_activation=False,
            )
            continuation = self._continuation_ancestry(candidate)
            continuation_records = tuple(
                stored.record for stored in continuation
            )
            self._validate_support_process_graph(
                candidate,
                (
                    *continuation_records,
                    candidate,
                    *(stored.record for stored in active),
                ),
                require_actor_current_use=True,
            )
        else:
            continuation = self._continuation_ancestry(candidate)
            continuation_records = tuple(
                stored.record for stored in continuation
            )
            self._validate_support_process_graph(
                candidate,
                (*continuation_records, candidate),
            )
        return candidate

    def transition_workflow_state(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Persist one ordinary Support Process workflow-state progression."""
        prior = self.load_exact(work)
        if prior.fingerprint != expected:
            raise PortiaConflictError(
                "expected Support Process state does not match canonical bytes"
            )
        accepted = self._require_workflow_state_candidate(
            work,
            prior.record,
            candidate,
        )
        return self.repository.replace_work(
            work,
            accepted,
            expected=expected,
        )

    def require_current_use(self, work: ExactPortiaWorkRef) -> StoredRecord:
        """Qualify one exact active Support Process for consequential use."""
        root = self.load_exact(work)
        require_support_process_lifecycle_reconciled(
            self.repository,
            work,
            root.record,
        )
        if root.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Support Process use requires active canonical lifecycle"
            )
        if not isinstance(root.record, SupportProcessV1):
            raise WorkflowOwnershipError(
                "current Support Process use requires support_process@1"
            )
        _require_active_digital_materialization(root.record)
        self.quarantine.require_allowed(work_target(work), "block_current_use")
        ancestry = self._supersession_ancestry(root.record)
        active = self._active_supported_participants(work, for_activation=False)
        self._require_initiation_authority(root.record)
        continuation = self._continuation_ancestry(root.record)
        continuation_records = tuple(
            stored.record for stored in continuation
        )
        self._validate_support_process_graph(
            root.record,
            (
                *(stored.record for stored in ancestry),
                *continuation_records,
                root.record,
                *(stored.record for stored in active),
            ),
            require_actor_current_use=True,
        )
        return root

    resolve_current = require_current_use
