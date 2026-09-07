"""Closed lifecycle authority across established Portia work-record families.

Issue #47 composes the already-qualified family lifecycle readers and mutation
services rather than introducing another status matrix.  Read-side history
selection remains delegated to the family lifecycle modules.  Ordinary status
transitions are dispatched only to current-write family services that already
own legality, semantic preflight, coordinated persistence, and reconciliation.

Historical-read versions remain readable but are never promoted to new-write
authority.  Work-root and Actor Directory lifecycle use different ownership
and persistence topologies and therefore require dedicated later adapters.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Protocol, TypeAlias, cast

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.accounts import AccountWorkflowService
from portia.workflows.classifications import ClassificationWorkflowService
from portia.workflows.common import WorkflowServiceBase
from portia.workflows.communication_attachments import (
    ModuleCommunicationAttachmentAuthority,
)
from portia.workflows.communication_lifecycle import (
    communication_lifecycle_state,
    require_communication_lifecycle_reconciled,
)
from portia.workflows.communications import CommunicationWorkflowService
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.determinations import DeterminationWorkflowService
from portia.workflows.downstream_lifecycle import (
    downstream_lifecycle_state,
    require_downstream_lifecycle_reconciled,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence_lifecycle import (
    evidence_lifecycle_state,
    require_evidence_lifecycle_reconciled,
)
from portia.workflows.fidelity import FidelityWorkflowService
from portia.workflows.fidelity_lifecycle import (
    fidelity_lifecycle_state,
    require_fidelity_lifecycle_reconciled,
)
from portia.workflows.follow_ups import FollowUpWorkflowService
from portia.workflows.hypotheses import HypothesisWorkflowService
from portia.workflows.implementation_lifecycle import (
    implementation_lifecycle_state,
    require_implementation_lifecycle_reconciled,
)
from portia.workflows.implementations import ImplementationWorkflowService
from portia.workflows.intervention_lifecycle import (
    intervention_lifecycle_state,
    require_intervention_lifecycle_reconciled,
)
from portia.workflows.interventions import InterventionWorkflowService
from portia.workflows.judgment_evidence import ModuleJudgmentEvidenceAuthority
from portia.workflows.judgment_lifecycle import (
    judgment_lifecycle_state,
    require_judgment_lifecycle_reconciled,
)
from portia.workflows.lifecycle_history import (
    LifecycleHistoryCorrectionResolution,
    load_lifecycle_history_corrections,
    resolve_corrected_lifecycle_history,
)
from portia.workflows.observations import ObservationWorkflowService
from portia.workflows.outcomes import (
    ModuleOutcomeBasisAuthority,
    OutcomeWorkflowService,
)
from portia.workflows.reentries import ReentryWorkflowService
from portia.workflows.repairs import RepairWorkflowService
from portia.workflows.response_lifecycle import (
    require_response_lifecycle_reconciled,
    response_lifecycle_state,
)
from portia.workflows.responses import ResponseWorkflowService
from portia.workflows.reviews import ReviewWorkflowService
from portia.workflows.support_goal_lifecycle import (
    require_support_goal_lifecycle_reconciled,
    support_goal_lifecycle_state,
)
from portia.workflows.support_goals import SupportGoalWorkflowService
from portia.workflows.support_lifecycle import (
    require_support_lifecycle_reconciled,
    support_lifecycle_state,
)
from portia.workflows.support_need_lifecycle import (
    require_support_need_lifecycle_reconciled,
    support_need_lifecycle_state,
)
from portia.workflows.support_needs import SupportNeedWorkflowService
from portia.workflows.support_process_participant_lifecycle import (
    participant_lifecycle_state,
    require_participant_lifecycle_reconciled,
)
from portia.workflows.support_process_participants import (
    SupportProcessParticipantWorkflowService,
)
from portia.workflows.supports import SupportWorkflowService

LifecycleContractKey: TypeAlias = tuple[str, str]


class _LifecycleState(Protocol):
    """Structural shape already exposed by each family lifecycle reader."""

    @property
    def transitions(self) -> tuple[StoredRecord, ...]: ...

    @property
    def head(self) -> StoredRecord | None: ...

    @property
    def selected_status(self) -> str | None: ...


class _LifecycleTransitionService(Protocol):
    """Shared ordinary-transition surface already exposed by #40-#46 services."""

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
    ) -> OperationCommitResult: ...


_LifecycleReader: TypeAlias = Callable[
    [PortiaRepository, ExactPortiaWorkRef, PortiaRecord], _LifecycleState
]


@dataclass(frozen=True, slots=True)
class _LifecycleAdapter:
    resolve: _LifecycleReader
    require_reconciled: _LifecycleReader


@dataclass(frozen=True, slots=True)
class LifecycleResolution:
    """Normalized read result for one exact registered work-record representation."""

    work: ExactPortiaWorkRef
    contract: str
    contract_version: str
    record_id: str
    canonical_status: str
    selected_status: str | None
    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def reconciled(self) -> bool:
        """Whether selected lifecycle history agrees with the canonical status."""
        return (
            self.selected_status is None
            or self.selected_status == self.canonical_status
        )


def _adapter(
    resolve: _LifecycleReader,
    require_reconciled: _LifecycleReader,
) -> _LifecycleAdapter:
    return _LifecycleAdapter(resolve, require_reconciled)


_EVIDENCE = _adapter(evidence_lifecycle_state, require_evidence_lifecycle_reconciled)
_JUDGMENT = _adapter(judgment_lifecycle_state, require_judgment_lifecycle_reconciled)
_RESPONSE = _adapter(response_lifecycle_state, require_response_lifecycle_reconciled)
_COMMUNICATION = _adapter(
    communication_lifecycle_state,
    require_communication_lifecycle_reconciled,
)
_SUPPORT_PROCESS_PARTICIPANT = _adapter(
    participant_lifecycle_state,
    require_participant_lifecycle_reconciled,
)
_SUPPORT_NEED = _adapter(
    support_need_lifecycle_state,
    require_support_need_lifecycle_reconciled,
)
_SUPPORT_GOAL = _adapter(
    support_goal_lifecycle_state,
    require_support_goal_lifecycle_reconciled,
)
_SUPPORT = _adapter(support_lifecycle_state, require_support_lifecycle_reconciled)
_INTERVENTION = _adapter(
    intervention_lifecycle_state,
    require_intervention_lifecycle_reconciled,
)
_IMPLEMENTATION = _adapter(
    implementation_lifecycle_state,
    require_implementation_lifecycle_reconciled,
)
_FIDELITY = _adapter(fidelity_lifecycle_state, require_fidelity_lifecycle_reconciled)
_DOWNSTREAM = _adapter(
    downstream_lifecycle_state,
    require_downstream_lifecycle_reconciled,
)

_RECORD_LIFECYCLE_ADAPTERS: Mapping[LifecycleContractKey, _LifecycleAdapter] = (
    MappingProxyType(
        {
            ("account", "1"): _EVIDENCE,
            ("account", "2"): _EVIDENCE,
            ("observation", "1"): _EVIDENCE,
            ("observation", "2"): _EVIDENCE,
            ("review", "1"): _JUDGMENT,
            ("classification", "1"): _JUDGMENT,
            ("hypothesis", "1"): _JUDGMENT,
            ("determination", "1"): _JUDGMENT,
            ("response", "1"): _RESPONSE,
            ("communication", "1"): _COMMUNICATION,
            ("support_process_participant", "1"): _SUPPORT_PROCESS_PARTICIPANT,
            ("support_need", "1"): _SUPPORT_NEED,
            ("support_goal", "1"): _SUPPORT_GOAL,
            ("support", "1"): _SUPPORT,
            ("intervention", "1"): _INTERVENTION,
            ("implementation", "1"): _IMPLEMENTATION,
            ("fidelity", "1"): _FIDELITY,
            ("follow_up", "1"): _DOWNSTREAM,
            ("outcome", "1"): _DOWNSTREAM,
            ("reentry", "1"): _DOWNSTREAM,
            ("repair", "1"): _DOWNSTREAM,
        }
    )
)

_SUPPORTED_RECORD_LIFECYCLE_CONTRACTS = tuple(sorted(_RECORD_LIFECYCLE_ADAPTERS))
_CURRENT_WRITE_LIFECYCLE_CONTRACTS = frozenset(
    {
        ("account", "2"),
        ("observation", "2"),
        ("review", "1"),
        ("classification", "1"),
        ("hypothesis", "1"),
        ("determination", "1"),
        ("response", "1"),
        ("communication", "1"),
        ("support_process_participant", "1"),
        ("support_need", "1"),
        ("support_goal", "1"),
        ("support", "1"),
        ("intervention", "1"),
        ("implementation", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("outcome", "1"),
        ("reentry", "1"),
        ("repair", "1"),
    }
)
_SUPPORTED_RECORD_LIFECYCLE_TRANSITIONS = tuple(
    sorted(_CURRENT_WRITE_LIFECYCLE_CONTRACTS)
)


def supported_record_lifecycle_contracts() -> tuple[LifecycleContractKey, ...]:
    """Return the frozen record/version read adapters available under Issue #47."""
    return _SUPPORTED_RECORD_LIFECYCLE_CONTRACTS


def _record_lifecycle_adapter(record: PortiaRecord) -> _LifecycleAdapter:
    key = (record.contract, record.contract_version)
    try:
        return _RECORD_LIFECYCLE_ADAPTERS[key]
    except KeyError as exc:
        raise WorkflowOwnershipError(
            "generic lifecycle authority has no registered adapter for "
            f"{record.contract}@{record.contract_version}"
        ) from exc


def _normalize_resolution(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    state: _LifecycleState,
) -> LifecycleResolution:
    record_id = record.logical_id
    status = record.status
    if not isinstance(record_id, str):
        raise WorkflowOwnershipError(
            "generic lifecycle authority requires an exact record identity"
        )
    if not isinstance(status, str):
        raise WorkflowOwnershipError(
            "generic lifecycle authority requires a lifecycle-bearing record"
        )
    return LifecycleResolution(
        work=work,
        contract=record.contract,
        contract_version=record.contract_version,
        record_id=record_id,
        canonical_status=status,
        selected_status=state.selected_status,
        transitions=state.transitions,
        head=state.head,
    )


def _require_exact_candidate_identity(
    reference: ExactPortiaWorkRecordRef,
    candidate: PortiaRecord,
) -> None:
    if (
        candidate.contract != reference.record_ref.record_kind
        or candidate.contract_version != reference.record_ref.contract_version
        or candidate.logical_id != reference.record_ref.record_id
        or candidate.class_id != reference.work_ref.class_id
        or candidate.work_id != reference.work_ref.work_id
    ):
        raise WorkflowOwnershipError(
            "generic lifecycle transition candidate must preserve the exact "
            "selected canonical record identity"
        )


class LifecycleWorkflowService(WorkflowServiceBase):
    """Read, reconcile, and transition registered work-record lifecycle histories.

    Ordinary mutation remains a façade over the existing family workflow services.
    Those services continue to own legal transition edges, family-specific active
    preconditions, transition reason policy, append-before-replace coordination,
    guarded optimistic concurrency, readback, and journal completion.
    """

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        module_judgment_evidence_authority: (
            ModuleJudgmentEvidenceAuthority | None
        ) = None,
        module_communication_attachment_authority: (
            ModuleCommunicationAttachmentAuthority | None
        ) = None,
        module_outcome_basis_authority: ModuleOutcomeBasisAuthority | None = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )
        self.module_judgment_evidence_authority = (
            module_judgment_evidence_authority
        )
        self.module_communication_attachment_authority = (
            module_communication_attachment_authority
        )
        self.module_outcome_basis_authority = module_outcome_basis_authority

    @staticmethod
    def supported_transition_contracts() -> tuple[LifecycleContractKey, ...]:
        """Return current-write family/version keys eligible for ordinary transition."""
        return _SUPPORTED_RECORD_LIFECYCLE_TRANSITIONS

    def _load_exact_record(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        key = (
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
        )
        if key not in _RECORD_LIFECYCLE_ADAPTERS:
            raise WorkflowOwnershipError(
                "generic lifecycle authority has no registered adapter for "
                f"{key[0]}@{key[1]}"
            )
        self.repository.load_work(reference.work_ref)
        stored = self.repository.load_work_record(
            reference.work_ref,
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )
        if (
            stored.record.contract != reference.record_ref.record_kind
            or stored.record.contract_version
            != reference.record_ref.contract_version
            or stored.record.logical_id != reference.record_ref.record_id
            or stored.record.class_id != reference.work_ref.class_id
            or stored.record.work_id != reference.work_ref.work_id
        ):
            raise WorkflowOwnershipError(
                "generic lifecycle exact target does not match the requested reference"
            )
        return stored

    def resolve_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> LifecycleResolution:
        """Resolve one registered lifecycle history without timestamp winner logic."""
        adapter = _record_lifecycle_adapter(record)
        state = adapter.resolve(self.repository, work, record)
        return _normalize_resolution(work, record, state)

    def load_history(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> LifecycleResolution:
        """Resolve history for exactly the supplied canonical work-record identity."""
        stored = self._load_exact_record(reference)
        return self.resolve_record(reference.work_ref, stored.record)

    def resolve_selected_head(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord | None:
        """Return the exact selected transition head, if history exists."""
        return self.resolve_record(work, record).head

    def require_reconciled(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> LifecycleResolution:
        """Require family history and canonical status to agree exactly."""
        adapter = _record_lifecycle_adapter(record)
        state = adapter.require_reconciled(self.repository, work, record)
        resolution = _normalize_resolution(work, record, state)
        if not resolution.reconciled:
            raise AssertionError(
                "family lifecycle reconciliation returned disagreement"
            )
        return resolution

    def load_correction_history(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> tuple[StoredRecord, ...]:
        """Load the exact append-only correction chain for one record target."""
        self._load_exact_record(reference)
        return load_lifecycle_history_corrections(self.repository, reference)

    def resolve_selected_correction(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord | None:
        """Return the exact selected correction-chain head, if one exists."""
        corrections = self.load_correction_history(reference)
        return corrections[-1] if corrections else None

    def resolve_corrected_history(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> LifecycleHistoryCorrectionResolution:
        """Resolve lifecycle selection after append-only correction evidence."""
        stored = self._load_exact_record(reference)
        status = stored.record.status
        if not isinstance(status, str):
            raise WorkflowOwnershipError(
                "corrected lifecycle target has no canonical lifecycle status"
            )
        corrections = load_lifecycle_history_corrections(
            self.repository,
            reference,
        )
        if corrections:
            return resolve_corrected_lifecycle_history(
                self.repository,
                reference,
                canonical_status=status,
                corrections=corrections,
            )

        ordinary = self.resolve_record(reference.work_ref, stored.record)
        return LifecycleHistoryCorrectionResolution(
            reference=reference,
            canonical_status=status,
            baseline_status=None,
            transitions=ordinary.transitions,
            corrections=(),
            selected_correction=None,
            selected_head=ordinary.head,
            selected_status=ordinary.selected_status,
            excluded_transition_ids=frozenset(),
        )

    def require_corrected_history_reconciled(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> LifecycleHistoryCorrectionResolution:
        """Require canonical status to agree with corrected selected history."""
        resolution = self.resolve_corrected_history(reference)
        if not resolution.reconciled:
            raise WorkflowPrerequisiteError(
                "canonical status does not reconcile with corrected lifecycle history"
            )
        return resolution

    def _transition_service(
        self,
        key: LifecycleContractKey,
    ) -> object:
        common: dict[str, Any] = {
            "repository": self.repository,
            "quarantine": self.quarantine,
            "context_assembler": self.contexts,
        }
        if key == ("account", "2"):
            return AccountWorkflowService(self.workspace_root, **common)
        if key == ("observation", "2"):
            return ObservationWorkflowService(self.workspace_root, **common)
        if key == ("review", "1"):
            return ReviewWorkflowService(
                self.workspace_root,
                **common,
                module_authority=self.module_judgment_evidence_authority,
            )
        if key == ("classification", "1"):
            return ClassificationWorkflowService(
                self.workspace_root,
                **common,
                module_authority=self.module_judgment_evidence_authority,
            )
        if key == ("hypothesis", "1"):
            return HypothesisWorkflowService(
                self.workspace_root,
                **common,
                module_authority=self.module_judgment_evidence_authority,
            )
        if key == ("determination", "1"):
            return DeterminationWorkflowService(
                self.workspace_root,
                **common,
                module_authority=self.module_judgment_evidence_authority,
            )
        if key == ("response", "1"):
            return ResponseWorkflowService(
                self.workspace_root,
                **common,
                module_authority=self.module_judgment_evidence_authority,
            )
        if key == ("communication", "1"):
            return CommunicationWorkflowService(
                self.workspace_root,
                **common,
                module_attachment_authority=(
                    self.module_communication_attachment_authority
                ),
            )
        if key == ("support_process_participant", "1"):
            return SupportProcessParticipantWorkflowService(
                self.workspace_root,
                **common,
            )
        if key == ("support_need", "1"):
            return SupportNeedWorkflowService(self.workspace_root, **common)
        if key == ("support_goal", "1"):
            return SupportGoalWorkflowService(self.workspace_root, **common)
        if key == ("support", "1"):
            return SupportWorkflowService(self.workspace_root, **common)
        if key == ("intervention", "1"):
            return InterventionWorkflowService(self.workspace_root, **common)
        if key == ("implementation", "1"):
            return ImplementationWorkflowService(self.workspace_root, **common)
        if key == ("fidelity", "1"):
            return FidelityWorkflowService(self.workspace_root, **common)
        if key == ("follow_up", "1"):
            return FollowUpWorkflowService(self.workspace_root, **common)
        if key == ("outcome", "1"):
            return OutcomeWorkflowService(
                self.workspace_root,
                **common,
                module_basis_authority=self.module_outcome_basis_authority,
            )
        if key == ("reentry", "1"):
            return ReentryWorkflowService(self.workspace_root, **common)
        if key == ("repair", "1"):
            return RepairWorkflowService(self.workspace_root, **common)
        raise WorkflowOwnershipError(
            "generic lifecycle transition has no current-write adapter for "
            f"{key[0]}@{key[1]}"
        )

    def transition(
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
        """Persist one ordinary family-authorized lifecycle status transition."""
        key = (
            reference.record_ref.record_kind,
            reference.record_ref.contract_version,
        )
        if key not in _CURRENT_WRITE_LIFECYCLE_CONTRACTS:
            if key in _RECORD_LIFECYCLE_ADAPTERS:
                raise WorkflowOwnershipError(
                    "generic lifecycle transition does not promote historical-read "
                    f"{key[0]}@{key[1]} to current write authority"
                )
            raise WorkflowOwnershipError(
                "generic lifecycle transition has no registered adapter for "
                f"{key[0]}@{key[1]}"
            )

        _require_exact_candidate_identity(reference, candidate)
        prior = self._load_exact_record(reference)
        self.require_reconciled(reference.work_ref, prior.record)

        transition_service = cast(
            _LifecycleTransitionService, self._transition_service(key)
        )
        result = transition_service.transition_lifecycle(
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

        accepted = self._load_exact_record(reference)
        self.require_reconciled(reference.work_ref, accepted.record)
        if accepted.record.to_dict() != candidate.to_dict():
            raise WorkflowPrerequisiteError(
                "generic lifecycle transition readback does not match the accepted "
                "candidate bytes"
            )
        return result
