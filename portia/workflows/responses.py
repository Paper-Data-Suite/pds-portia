"""Production workflow for Event-local ``response@1`` records."""

from __future__ import annotations

from pathlib import Path

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.action_common import ActionReadService, action_reference
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import record_target, work_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.determinations import DeterminationWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.judgment_evidence import ModuleJudgmentEvidenceAuthority
from portia.workflows.response_common import (
    require_digital_response_creation,
    require_response_creation_semantics,
    require_response_current_materialization,
    require_response_owner_current_eligibility,
    require_response_owner_write_eligibility,
    require_response_provider_authority,
    require_response_record_owner,
    require_response_targets_current_use,
    response_context_reference,
    response_is_recorded_institutional,
    response_target_records,
    validate_partial_response_graph,
)
from portia.workflows.response_lifecycle import (
    build_response_lifecycle_transition,
    require_response_lifecycle_reconciled,
)
from portia.workflows.response_supersession import (
    require_exact_response_correction_predecessor,
    require_material_response_correction,
    require_response_supersession_effective,
    response_correction_lifecycle_reason,
    response_correction_reason_detail,
    response_supersession_ancestry,
    superseded_response_predecessor,
)
from portia.workflows.reviews import ReviewWorkflowService


def response_reference(
    work: ExactPortiaWorkRef,
    response_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Event-local ``response@1`` reference."""
    return action_reference(work, "response", response_id)


class ResponseWorkflowService(ActionReadService):
    """Create and resolve bounded Event-local Responses without inferring outcome."""

    CONTRACT = "response"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        module_authority: ModuleJudgmentEvidenceAuthority | None = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )
        self.module_authority = module_authority

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> PortiaRecord:
        candidate = require_response_record_owner(work, record)
        require_digital_response_creation(candidate)
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Response identity must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "Response correction requires the later coordinated successor path"
            )
        require_response_creation_semantics(candidate)
        return candidate

    def _review_service(self) -> ReviewWorkflowService:
        return ReviewWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
            module_authority=self.module_authority,
        )

    def _determination_service(self) -> DeterminationWorkflowService:
        return DeterminationWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
            module_authority=self.module_authority,
        )

    def _resolve_decision_context(
        self,
        work: ExactPortiaWorkRef,
        candidate: PortiaRecord,
    ) -> None:
        review_ref = response_context_reference(
            work,
            candidate,
            field_name="review_ref",
            record_kind="review",
        )
        if review_ref is not None:
            # Context is pinned to the exact historical Review representation.
            self._review_service().load_exact(review_ref)

        determination_ref = response_context_reference(
            work,
            candidate,
            field_name="determination_ref",
            record_kind="determination",
        )
        institutional = response_is_recorded_institutional(candidate)
        if institutional and determination_ref is None:
            raise WorkflowPrerequisiteError(
                "recorded-institutional consequence requires Determination context"
            )
        if determination_ref is None:
            return

        determination_service = self._determination_service()
        if institutional and candidate.status == "active":
            # Acceptance requires current authority once; the Response keeps this
            # exact identity as historical context after later Determination change.
            determination_service.require_current_use(determination_ref)
            return
        determination_service.load_exact(determination_ref)

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one new digital Response after exact application validation."""
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_response_owner_write_eligibility(owner.record)

        targets = response_target_records(self.repository, work, candidate)
        require_response_provider_authority(
            self.contexts,
            candidate,
            require_current_use=candidate.status == "active",
        )
        self._resolve_decision_context(work, candidate)

        if candidate.status == "active":
            require_response_owner_current_eligibility(owner.record)
            require_response_targets_current_use(
                work,
                targets,
                quarantine=self.quarantine,
            )

        validate_partial_response_graph(candidate)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, candidate),
            "block_work_writes",
        )
        return self.repository.create_work_record(work, candidate)

    def _require_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        """Validate lifecycle change without requiring stale facts current."""
        require_response_record_owner(work, prior)
        require_response_record_owner(work, candidate)
        owner = self.repository.load_work(work)
        require_response_owner_write_eligibility(owner.record)
        if candidate.status != "active":
            validate_partial_response_graph(candidate)
            return

        require_response_current_materialization(candidate)
        require_response_creation_semantics(candidate)
        require_response_owner_current_eligibility(owner.record)
        targets = response_target_records(self.repository, work, candidate)
        require_response_targets_current_use(
            work,
            targets,
            quarantine=self.quarantine,
        )
        require_response_provider_authority(
            self.contexts,
            candidate,
            require_current_use=True,
        )
        self._resolve_decision_context(work, candidate)
        validate_partial_response_graph(candidate)

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> None:
        """Validate one active material-correction successor."""
        require_response_record_owner(work, prior)
        require_response_lifecycle_reconciled(self.repository, work, prior)
        require_response_record_owner(work, successor)
        require_digital_response_creation(successor)
        if successor.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Response successor must be active"
            )
        require_response_creation_semantics(successor)
        require_material_response_correction(
            prior,
            successor,
            supersession_reason,
        )

        owner = self.repository.load_work(work)
        require_response_owner_write_eligibility(owner.record)
        require_response_owner_current_eligibility(owner.record)
        targets = response_target_records(self.repository, work, successor)
        require_response_targets_current_use(
            work,
            targets,
            quarantine=self.quarantine,
        )
        require_response_provider_authority(
            self.contexts,
            successor,
            require_current_use=True,
        )
        self._resolve_decision_context(work, successor)
        validate_partial_response_graph(successor)

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
        """Persist one ordinary Response activation/invalidation."""
        if reference.record_ref.record_kind != "response":
            raise WorkflowOwnershipError("reference is not a Response")
        work = reference.work_ref
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
            candidate_validator=lambda prior, value: self._require_transition_candidate(
                work,
                prior,
                value,
            ),
            transition_factory=lambda prior, value: build_response_lifecycle_transition(
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
        require_response_lifecycle_reconciled(
            self.repository,
            work,
            accepted.record,
        )
        return result

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
        """Create a corrected Response successor and supersede its exact predecessor."""
        if predecessor.record_ref.record_kind != "response":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Response"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_response_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = response_correction_reason_detail(successor)
        lifecycle_reason = response_correction_lifecycle_reason(
            supersession_reason
        )
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
            successor_validator=lambda prior, value: self._require_correction_successor(
                work,
                prior,
                value,
                supersession_reason=supersession_reason,
            ),
            predecessor_factory=superseded_response_predecessor,
            transition_factory=lambda prior, value: build_response_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=lifecycle_reason,
                reason_detail=reason_detail,
                effective_at=effective_at,
                allow_supersession=True,
            ),
        )
        accepted_predecessor = self.load_exact(predecessor)
        require_response_lifecycle_reconciled(
            self.repository,
            work,
            accepted_predecessor.record,
        )
        return result

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Qualify one exact active Response for consequential current use."""
        response = self.load_exact(reference)
        require_response_record_owner(reference.work_ref, response.record)
        require_response_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            response.record,
        )
        if response.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Response use requires an active canonical Response"
            )
        require_response_current_materialization(response.record)
        require_response_creation_semantics(response.record)
        predecessors = response_supersession_ancestry(
            self.repository,
            reference.work_ref,
            response.record,
        )
        require_response_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )

        owner = self.repository.load_work(reference.work_ref)
        require_response_owner_current_eligibility(owner.record)
        targets = response_target_records(
            self.repository,
            reference.work_ref,
            response.record,
        )
        require_response_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        require_response_provider_authority(
            self.contexts,
            response.record,
            require_current_use=True,
        )
        self._resolve_decision_context(reference.work_ref, response.record)

        self.quarantine.require_allowed(
            work_target(reference.work_ref),
            "block_current_use",
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, response.record),
            "block_current_use",
        )
        validate_partial_response_graph(response.record)
        return response

    resolve_current = require_current_use

    def list_responses(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)
