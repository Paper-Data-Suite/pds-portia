"""Production workflows for Portia-work-local ``communication@1`` records."""

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
from portia.workflows.communication_attachments import (
    CommunicationAttachmentResolution,
    ModuleCommunicationAttachmentAuthority,
    communication_attachments,
    require_communication_attachment_authority,
)
from portia.workflows.communication_common import (
    require_communication_contact_point_authority,
    require_communication_creation_semantics,
    require_communication_current_materialization,
    require_communication_current_owner,
    require_communication_owner_current_eligibility,
    require_communication_owner_write_eligibility,
    require_communication_people_authority,
    require_communication_record_owner,
    require_communication_write_owner,
    require_current_communication_record_owner,
    require_digital_communication_creation,
    require_initial_communication_no_supersession,
    validate_partial_communication_graph,
)
from portia.workflows.communication_lifecycle import (
    build_communication_lifecycle_transition,
    require_communication_lifecycle_reconciled,
)
from portia.workflows.communication_relations import (
    communication_relations,
    require_communication_relation_authority,
)
from portia.workflows.communication_supersession import (
    communication_correction_lifecycle_reason,
    communication_correction_reason_detail,
    communication_supersession_ancestry,
    require_communication_supersession_effective,
    require_exact_communication_correction_predecessor,
    require_material_communication_correction,
    superseded_communication_predecessor,
)
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


def communication_reference(
    work: ExactPortiaWorkRef,
    communication_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact ``communication@1`` reference without owner narrowing."""
    return action_reference(work, "communication", communication_id)


class CommunicationWorkflowService(ActionReadService):
    """Create, qualify, transition, and correct bounded Communications."""

    CONTRACT = "communication"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        module_attachment_authority: (
            ModuleCommunicationAttachmentAuthority | None
        ) = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )
        self.module_attachment_authority = module_attachment_authority

    def _require_support_process_owner_current_use(
        self,
        work: ExactPortiaWorkRef,
    ) -> None:
        if work.work_kind != "support_process":
            return
        from portia.workflows.support_processes import SupportProcessWorkflowService

        SupportProcessWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        ).require_current_use(work)

    def _require_owner_write_eligibility(
        self,
        work: ExactPortiaWorkRef,
        owner: PortiaRecord,
    ) -> None:
        require_communication_owner_write_eligibility(owner)
        self._require_support_process_owner_current_use(work)

    def _require_owner_current_eligibility(
        self,
        work: ExactPortiaWorkRef,
        owner: PortiaRecord,
    ) -> None:
        require_communication_owner_current_eligibility(owner)
        self._require_support_process_owner_current_use(work)

    def list_communications(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)

    @staticmethod
    def _require_write_input(
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> PortiaRecord:
        candidate = require_communication_record_owner(work, record)
        require_digital_communication_creation(candidate)
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Communication must begin proposed or active"
            )
        require_communication_creation_semantics(candidate)
        return candidate

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one new Event-owned digital Communication after validation."""
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        self._require_owner_write_eligibility(work, owner.record)

        if candidate.status == "active":
            require_communication_owner_current_eligibility(owner.record)

        require_current_use = candidate.status == "active"
        require_communication_people_authority(
            self.contexts,
            candidate,
            require_current_use=require_current_use,
        )
        require_communication_contact_point_authority(
            self.contexts,
            candidate,
            require_current_use=require_current_use,
        )
        require_communication_relation_authority(self.repository, candidate)
        require_communication_attachment_authority(
            self.workspace_root,
            self.repository,
            candidate,
            module_authority=self.module_attachment_authority,
        )
        # New attempts are new identities. Supersession belongs only to correct().
        require_initial_communication_no_supersession(candidate)

        validate_partial_communication_graph(candidate)

        self.quarantine.require_allowed(
            work_target(work),
            "block_work_writes",
        )
        self.quarantine.require_allowed(
            record_target(work, candidate),
            "block_work_writes",
        )
        return self.repository.create_work_record(work, candidate)

    def _quarantine_relation_dependencies(
        self,
        record: PortiaRecord,
        resolved: tuple[StoredRecord, ...],
    ) -> None:
        relations = communication_relations(record)
        if len(relations) != len(resolved):
            raise WorkflowPrerequisiteError(
                "Communication relation authority returned inconsistent results"
            )
        for relation, stored in zip(relations, resolved, strict=True):
            reference = ExactPortiaWorkRecordRef.from_dict(relation["record_ref"])
            self.quarantine.require_allowed(
                work_target(reference.work_ref),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(reference.work_ref, stored.record),
                "block_current_use",
            )

    def _quarantine_attachment_dependencies(
        self,
        record: PortiaRecord,
        resolutions: tuple[CommunicationAttachmentResolution, ...],
    ) -> None:
        attachments = communication_attachments(record)
        if len(attachments) != len(resolutions):
            raise WorkflowPrerequisiteError(
                "Communication attachment authority returned inconsistent results"
            )
        for attachment, resolution in zip(attachments, resolutions, strict=True):
            if attachment.get("kind") != "portia_record":
                continue
            if resolution.stored is None:
                raise WorkflowPrerequisiteError(
                    "Communication portia_record attachment did not resolve exactly"
                )
            reference = ExactPortiaWorkRecordRef.from_dict(
                attachment["record_ref"]
            )
            self.quarantine.require_allowed(
                work_target(reference.work_ref),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(reference.work_ref, resolution.stored.record),
                "block_current_use",
            )

    def _require_active_dependencies(self, candidate: PortiaRecord) -> None:
        """Resolve current human authority and exact historical dependencies."""
        require_communication_people_authority(
            self.contexts,
            candidate,
            require_current_use=True,
        )
        require_communication_contact_point_authority(
            self.contexts,
            candidate,
            require_current_use=True,
        )
        relations = require_communication_relation_authority(
            self.repository,
            candidate,
        )
        attachments = require_communication_attachment_authority(
            self.workspace_root,
            self.repository,
            candidate,
            module_authority=self.module_attachment_authority,
        )
        self._quarantine_relation_dependencies(candidate, relations)
        self._quarantine_attachment_dependencies(candidate, attachments)

    def _require_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        """Validate a lifecycle change without requiring stale facts current."""
        require_current_communication_record_owner(work, prior)
        require_current_communication_record_owner(work, candidate)
        owner = self.repository.load_work(work)
        self._require_owner_write_eligibility(work, owner.record)
        if candidate.status != "active":
            validate_partial_communication_graph(candidate)
            return

        require_communication_current_materialization(candidate)
        require_communication_creation_semantics(candidate)
        require_communication_owner_current_eligibility(owner.record)
        self._require_active_dependencies(candidate)
        validate_partial_communication_graph(candidate)

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> None:
        """Validate one active material-correction successor."""
        require_current_communication_record_owner(work, prior)
        require_communication_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        require_current_communication_record_owner(work, successor)
        require_digital_communication_creation(successor)
        if successor.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Communication successor must be active"
            )
        require_communication_creation_semantics(successor)
        require_material_communication_correction(
            prior,
            successor,
            supersession_reason,
        )

        owner = self.repository.load_work(work)
        self._require_owner_write_eligibility(work, owner.record)
        require_communication_owner_current_eligibility(owner.record)
        self._require_active_dependencies(successor)
        validate_partial_communication_graph(successor)

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
        """Persist one ordinary Communication activation/invalidation."""
        if reference.record_ref.record_kind != "communication":
            raise WorkflowOwnershipError("reference is not a Communication")
        require_communication_write_owner(reference.work_ref)
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
            transition_factory=lambda prior, value: (
                build_communication_lifecycle_transition(
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
        require_communication_lifecycle_reconciled(
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
        """Create a corrected successor and supersede its exact predecessor."""
        if predecessor.record_ref.record_kind != "communication":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Communication"
            )
        require_communication_write_owner(predecessor.work_ref)
        work = predecessor.work_ref
        supersession_reason = require_exact_communication_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = communication_correction_reason_detail(successor)
        lifecycle_reason = communication_correction_lifecycle_reason(
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
            predecessor_factory=superseded_communication_predecessor,
            transition_factory=lambda prior, value: (
                build_communication_lifecycle_transition(
                    self.repository,
                    work,
                    prior,
                    value,
                    transition_id=transition_id,
                    reason_code=lifecycle_reason,
                    reason_detail=reason_detail,
                    effective_at=effective_at,
                    allow_supersession=True,
                )
            ),
        )
        accepted_predecessor = self.load_exact(predecessor)
        require_communication_lifecycle_reconciled(
            self.repository,
            work,
            accepted_predecessor.record,
        )
        return result

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Qualify one exact active Communication under its frozen owner union."""
        require_communication_current_owner(reference.work_ref)
        communication = self.load_exact(reference)
        require_current_communication_record_owner(
            reference.work_ref,
            communication.record,
        )
        require_communication_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            communication.record,
        )
        if communication.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Communication use requires an active canonical Communication"
            )
        require_communication_current_materialization(communication.record)
        require_communication_creation_semantics(communication.record)
        predecessors = communication_supersession_ancestry(
            self.repository,
            reference.work_ref,
            communication.record,
        )
        require_communication_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )

        owner = self.repository.load_work(reference.work_ref)
        self._require_owner_current_eligibility(reference.work_ref, owner.record)
        self._require_active_dependencies(communication.record)

        self.quarantine.require_allowed(
            work_target(reference.work_ref),
            "block_current_use",
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, communication.record),
            "block_current_use",
        )
        validate_partial_communication_graph(communication.record)
        return communication

    resolve_current = require_current_use
