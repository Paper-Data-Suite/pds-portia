"""Account creation, exact history, and bounded current-use workflows."""

from __future__ import annotations

from portia.models import AccountV2, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.account_relations import account_relation_ancestry
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    ACCOUNT_READ_VERSIONS,
    ACCOUNT_VERSION,
    evidence_target_records,
    require_basic_evidence_shape,
    require_digital_entry_creation,
    require_evidence_owner,
    require_evidence_record_owner,
    require_owner_current_eligibility,
    require_owner_write_eligibility,
    require_supported_evidence_version,
    require_targets_current_use,
    require_work_current_use_quarantine,
)
from portia.workflows.evidence_artifacts import (
    evidence_validation_record,
    evidence_validation_records,
    require_source_artifact_authority,
)
from portia.workflows.evidence_lifecycle import (
    require_evidence_lifecycle_reconciled,
)
from portia.workflows.evidence_supersession import (
    require_supersession_effective,
    supersession_ancestry,
)
from portia.workflows.evidence_transition import EvidenceLifecycleCoordinator


def account_reference(
    work: ExactPortiaWorkRef,
    account_id: str,
    *,
    version: str = ACCOUNT_VERSION,
) -> ExactPortiaWorkRecordRef:
    require_supported_evidence_version(
        work,
        contract="account",
        version=version,
        supported_versions=ACCOUNT_READ_VERSIONS,
    )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="account",
            record_id=account_id,
            contract_version=version,
        ),
    )


class AccountWorkflowService(WorkflowServiceBase):
    """Create v2 digital Accounts and resolve exact v1/v2 evidence."""

    def _require_write_input(
        self, work: ExactPortiaWorkRef, record: PortiaRecord
    ) -> AccountV2:
        require_evidence_owner(work)
        if not isinstance(record, AccountV2):
            raise WorkflowOwnershipError("new Account writes require account@2 input")
        require_evidence_record_owner(work, record, contract="account")
        require_digital_entry_creation(record)
        require_basic_evidence_shape(
            record,
            allow_related_accounts=True,
            allow_source_artifacts=True,
        )
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Account identity must begin proposed or active"
            )
        return record

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_owner_write_eligibility(work, owner.record)
        targets = evidence_target_records(self.repository, work, candidate)
        relations = account_relation_ancestry(
            self.repository,
            work,
            candidate,
            allow_root_retracts=False,
        )
        require_source_artifact_authority(
            self.workspace_root,
            self.repository,
            candidate,
            require_current_use=candidate.status == "active",
        )
        validation_candidate = evidence_validation_record(candidate)
        if candidate.status == "active":
            require_owner_current_eligibility(work, owner.record)
            require_targets_current_use(work, targets, quarantine=self.quarantine)
            # Historical relation targets remain exact evidence; only the new
            # current Account needs current Actor authority.
            self.contexts.assemble(
                (
                    owner.record,
                    *(item.record for item in targets),
                    validation_candidate,
                ),
                require_actor_current_use=True,
            )
        graph = evidence_validation_records(
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in relations),
                candidate,
            )
        )
        self.validate_complete_graph(graph, require_actor_current_use=False)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        if reference.record_ref.record_kind != "account":
            raise WorkflowOwnershipError("reference is not an Account")
        require_supported_evidence_version(
            reference.work_ref,
            contract="account",
            version=reference.record_ref.contract_version,
            supported_versions=ACCOUNT_READ_VERSIONS,
        )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "account",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        require_evidence_owner(work)
        return self.repository.list_accounts(work)

    list_accounts = list

    def require_current_use(
        self, reference: ExactPortiaWorkRecordRef
    ) -> StoredRecord:
        account = self.load_exact(reference)
        require_evidence_lifecycle_reconciled(
            self.repository, reference.work_ref, account.record
        )
        require_basic_evidence_shape(
            account.record,
            allow_related_accounts=True,
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        if account.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Account use requires active evidence"
            )
        require_source_artifact_authority(
            self.workspace_root,
            self.repository,
            account.record,
            require_current_use=True,
        )
        owner = self.repository.load_work(reference.work_ref)
        require_owner_current_eligibility(reference.work_ref, owner.record)
        targets = evidence_target_records(
            self.repository, reference.work_ref, account.record
        )
        relations = account_relation_ancestry(
            self.repository, reference.work_ref, account.record
        )
        predecessors = supersession_ancestry(
            self.repository, reference.work_ref, account.record
        )
        require_supersession_effective(predecessors)
        require_work_current_use_quarantine(
            reference.work_ref,
            account.record,
            quarantine=self.quarantine,
        )
        require_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        graph = evidence_validation_records(
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in relations),
                *(item.record for item in predecessors),
                account.record,
            )
        )
        self.contexts.assemble(
            (evidence_validation_record(account.record),),
            require_actor_current_use=True,
        )
        self.validate_complete_graph(graph, require_actor_current_use=False)
        return account

    resolve_current = require_current_use

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
        """Persist one ordinary Account status transition through #38 coordination."""
        if reference.record_ref.record_kind != "account":
            raise WorkflowOwnershipError("reference is not an Account")
        coordinator = EvidenceLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit(
            reference,
            candidate,
            expected=expected,
            transition_id=transition_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
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
        """Create a corrected account@2 successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "account":
            raise WorkflowOwnershipError("correction predecessor is not an Account")
        coordinator = EvidenceLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit_evidence_correction(
            predecessor,
            successor,
            expected=expected,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
        )

    def retract(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        retraction: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str = "source_retracted",
        reason_detail: str | None = None,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create same-source retraction evidence and retract its predecessor."""
        if predecessor.record_ref.record_kind != "account":
            raise WorkflowOwnershipError("retraction predecessor is not an Account")
        coordinator = EvidenceLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit_account_retraction(
            predecessor,
            retraction,
            expected=expected,
            transition_id=transition_id,
            reason_code=reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
        )

