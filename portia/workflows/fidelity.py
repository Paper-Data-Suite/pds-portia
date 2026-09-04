"""Support Process-local ``fidelity@1`` evaluation workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from portia.models import FidelityV1, PortiaRecord
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
from portia.workflows.action_consolidation import ActionConsolidationCoordinator
from portia.workflows.action_reownership import ActionOwnershipCorrectionCoordinator
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.fidelity_lifecycle import (
    build_fidelity_lifecycle_transition,
    require_coordinated_fidelity_transition,
    require_fidelity_lifecycle_reconciled,
)
from portia.workflows.fidelity_supersession import (
    fidelity_supersession_ancestry,
    fidelity_supersession_reason_detail,
    require_duplicate_fidelity_consolidation_predecessors,
    require_exact_fidelity_correction_predecessor,
    require_fidelity_supersession_effective,
    require_fidelity_work_root_correction_predecessor,
    require_material_fidelity_correction,
    superseded_fidelity_predecessor,
)
from portia.workflows.implementations import (
    ImplementationWorkflowService,
    implementation_reference,
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

FIDELITY_VERSION = "1"
_FIDELITY_OWNER = ("support_process", "1")
_PLAN_KINDS = frozenset({"support", "intervention"})
_WORK_ROOT_PRESERVED_EVALUATION_FIELDS = (
    "plan_ref",
    "evaluator_ref",
    "scope",
    "result",
    "basis",
    "instrument_result",
    "evaluated_at",
    "summary",
)


def _require_fidelity_owner(work: ExactPortiaWorkRef) -> None:
    if (work.work_kind, work.contract_version) != _FIDELITY_OWNER:
        raise WorkflowOwnershipError(
            "Fidelity workflows require exact support_process@1 ownership"
        )


def fidelity_reference(
    work: ExactPortiaWorkRef,
    fidelity_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Support Process-local ``fidelity@1`` reference."""
    _require_fidelity_owner(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="fidelity",
            record_id=fidelity_id,
            contract_version=FIDELITY_VERSION,
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
    kinds: frozenset[str] | None = None,
    field_name: str,
) -> ExactLocalRecordRef:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"Fidelity {field_name} reference is malformed")
    reference = ExactLocalRecordRef.from_dict(value)
    if kinds is not None and (
        reference.record_kind not in kinds or reference.contract_version != "1"
    ):
        allowed = " or ".join(f"{kind}@1" for kind in sorted(kinds))
        raise WorkflowOwnershipError(
            f"Fidelity {field_name} must name exact {allowed}"
        )
    return reference


class FidelityWorkflowService(WorkflowServiceBase):
    """Create and resolve exact teacher-local ``fidelity@1`` evaluations."""

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

    def _implementation_service(self) -> ImplementationWorkflowService:
        return ImplementationWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> FidelityV1:
        _require_fidelity_owner(work)
        if not isinstance(record, FidelityV1):
            raise WorkflowOwnershipError(
                "new Fidelity writes require fidelity@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Fidelity does not belong to the explicitly selected Support Process"
            )

        source = record.field("creation_source")
        if not isinstance(source, Mapping):
            raise WorkflowOwnershipError("Fidelity creation_source is malformed")
        source_type = source.get("type")
        if source_type in {"paper_capture", "import"} and record.status == "active":
            raise WorkflowPrerequisiteError(
                "paper/import activation requires accepted review history"
            )
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Fidelity authoring accepts "
                "creation_source=digital_entry only"
            )
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "new digital Fidelity identity must begin active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Fidelity identity cannot establish supersession history"
            )

        evaluated = _parse_timestamp(
            record.field("evaluated_at"), "Fidelity evaluated_at"
        )
        created = _parse_timestamp(record.field("created_at"), "Fidelity created_at")
        if created < evaluated:
            raise WorkflowPrerequisiteError(
                "Fidelity created_at cannot precede evaluated_at"
            )
        updated = _parse_timestamp(record.field("updated_at"), "Fidelity updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Fidelity updated_at cannot precede created_at"
            )

        self._require_scope_chronology(record)
        self._require_instrument_scale(record)
        return record

    def _require_scope_chronology(self, record: PortiaRecord) -> None:
        scope = record.field("scope")
        if not isinstance(scope, Mapping):
            raise WorkflowOwnershipError("Fidelity scope is malformed")
        if scope.get("kind") != "bounded_plan_interval":
            return
        started = _parse_timestamp(
            scope.get("started_at"),
            "Fidelity bounded interval started_at",
        )
        ended = _parse_timestamp(
            scope.get("ended_at"),
            "Fidelity bounded interval ended_at",
        )
        if ended < started:
            raise WorkflowPrerequisiteError(
                "Fidelity bounded interval ended_at cannot precede started_at"
            )

    def _require_instrument_scale(self, record: PortiaRecord) -> None:
        result = record.field("instrument_result")
        if result is None:
            return
        if not isinstance(result, Mapping):
            raise WorkflowOwnershipError("Fidelity instrument_result is malformed")
        minimum = result.get("scale_minimum")
        maximum = result.get("scale_maximum")
        value = result.get("value")
        numbers = (minimum, maximum, value)
        if any(
            isinstance(item, bool) or not isinstance(item, (int, float))
            for item in numbers
        ):
            raise WorkflowOwnershipError("Fidelity instrument scale is malformed")
        assert isinstance(minimum, (int, float))
        assert isinstance(maximum, (int, float))
        assert isinstance(value, (int, float))
        if minimum >= maximum:
            raise WorkflowPrerequisiteError(
                "instrument scale_minimum must be less than scale_maximum"
            )
        if value < minimum or value > maximum:
            raise WorkflowPrerequisiteError(
                "instrument value must fall within declared scale"
            )

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
                "Fidelity plan ref does not resolve in owning Support Process"
            ) from exc

    def _resolve_evaluator(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        current: bool,
    ) -> StoredRecord:
        evaluator = _exact_local_ref(
            record.field("evaluator_ref"),
            kinds=frozenset({"support_process_participant"}),
            field_name="evaluator_ref",
        )
        exact = support_process_participant_reference(work, evaluator.record_id)
        try:
            if current:
                return self._participant_service().require_current_use(exact).participant
            return self._participant_service().load_exact(exact)
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                "Fidelity evaluator Participant ref does not resolve in owning "
                "Support Process"
            ) from exc

    def _scope_implementation_refs(
        self,
        record: PortiaRecord,
    ) -> tuple[ExactLocalRecordRef, ...]:
        scope = record.field("scope")
        if not isinstance(scope, Mapping):
            raise WorkflowOwnershipError("Fidelity scope is malformed")
        kind = scope.get("kind")
        if kind == "bounded_plan_interval":
            return ()
        if kind == "one_implementation":
            return (
                _exact_local_ref(
                    scope.get("implementation_ref"),
                    kinds=frozenset({"implementation"}),
                    field_name="scope Implementation",
                ),
            )
        if kind == "implementation_set":
            values = scope.get("implementation_refs")
            if not isinstance(values, Sequence) or isinstance(
                values, (str, bytes, bytearray)
            ):
                raise WorkflowOwnershipError(
                    "Fidelity scope Implementation set is malformed"
                )
            return tuple(
                _exact_local_ref(
                    value,
                    kinds=frozenset({"implementation"}),
                    field_name="scope Implementation",
                )
                for value in values
            )
        raise WorkflowOwnershipError(f"unsupported Fidelity scope kind {kind!r}")

    def _resolve_scope(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        expected_plan = record.field("plan_ref")
        resolved: list[StoredRecord] = []
        service = self._implementation_service()
        for reference in self._scope_implementation_refs(record):
            try:
                implementation = service.load_exact(
                    implementation_reference(work, reference.record_id)
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Fidelity scope Implementation ref does not resolve in owning "
                    "Support Process"
                ) from exc
            if implementation.record.field("plan_ref") != expected_plan:
                raise WorkflowPrerequisiteError(
                    "Fidelity scope Implementation must reference the same exact plan"
                )
            resolved.append(implementation)
        return tuple(resolved)

    def _resolve_basis_records(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        basis = record.field("basis")
        if not isinstance(basis, Mapping):
            raise WorkflowOwnershipError("Fidelity basis is malformed")
        raw_refs = basis.get("record_refs")
        if raw_refs is None:
            return ()
        if not isinstance(raw_refs, Sequence) or isinstance(
            raw_refs, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Fidelity basis record_refs are malformed")
        resolved: list[StoredRecord] = []
        for raw in raw_refs:
            reference = _exact_local_ref(raw, field_name="basis record")
            try:
                resolved.append(
                    self.repository.load_work_record(
                        work,
                        reference.record_kind,
                        reference.contract_version,
                        reference.record_id,
                    )
                )
            except PortiaNotFoundError as exc:
                raise WorkflowPrerequisiteError(
                    "Fidelity basis record ref does not resolve in owning "
                    "Support Process"
                ) from exc
        return tuple(resolved)

    def _require_existing_record(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> FidelityV1:
        _require_fidelity_owner(work)
        if not isinstance(record, FidelityV1):
            raise WorkflowOwnershipError(
                "Fidelity current authority requires fidelity@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Fidelity does not belong to the selected Support Process"
            )
        source = record.field("creation_source")
        if not isinstance(source, Mapping) or source.get("type") != "digital_entry":
            raise WorkflowPrerequisiteError(
                "v0.2 Fidelity current authority requires digital_entry materialization"
            )
        evaluated = _parse_timestamp(
            record.field("evaluated_at"), "Fidelity evaluated_at"
        )
        created = _parse_timestamp(record.field("created_at"), "Fidelity created_at")
        if created < evaluated:
            raise WorkflowPrerequisiteError(
                "Fidelity created_at cannot precede evaluated_at"
            )
        updated = _parse_timestamp(record.field("updated_at"), "Fidelity updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Fidelity updated_at cannot precede created_at"
            )
        self._require_scope_chronology(record)
        self._require_instrument_scale(record)
        return record

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> FidelityV1:
        value = self._require_existing_record(work, candidate)
        require_coordinated_fidelity_transition(prior, value)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, value), "block_work_writes"
        )
        if value.status == "active":
            self._root_service().require_current_use(work)
            self._resolve_plan(work, value)
            self._resolve_evaluator(work, value, current=True)
            self._resolve_scope(work, value)
            self._resolve_basis_records(work, value)
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value), "block_current_use"
            )
        else:
            self.repository.load_work(work)
            self._resolve_plan(work, value)
            self._resolve_evaluator(work, value, current=False)
            self._resolve_scope(work, value)
            self._resolve_basis_records(work, value)
        return value

    def _require_successor_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        successor: PortiaRecord,
        *,
        supersession_reason: str,
    ) -> FidelityV1:
        value = self._require_existing_record(work, successor)
        require_fidelity_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Fidelity predecessor updated_at",
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Fidelity successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Fidelity successor updated_at cannot precede predecessor update"
            )
        require_material_fidelity_correction(
            prior,
            value,
            supersession_reason,
        )

        self._root_service().require_current_use(work)
        self._resolve_plan(work, value)
        self._resolve_evaluator(work, value, current=True)
        self._resolve_scope(work, value)
        self._resolve_basis_records(work, value)
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
    ) -> FidelityV1:
        value = self._require_existing_record(destination_work, successor)
        require_fidelity_lifecycle_reconciled(
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
                "work-root correction must preserve Fidelity ID"
            )
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Fidelity work-root predecessor updated_at",
        )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Fidelity work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Fidelity work-root successor updated_at cannot precede "
                "predecessor update"
            )
        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_EVALUATION_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root correction cannot rewrite Fidelity evaluation fact "
                    f"{field}"
                )

        self.repository.load_work(source_work)
        self._root_service().require_current_use(destination_work)
        self._resolve_plan(destination_work, value)
        self._resolve_evaluator(destination_work, value, current=True)
        self._resolve_scope(destination_work, value)
        self._resolve_basis_records(destination_work, value)
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
    ) -> FidelityV1:
        value = self._require_existing_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate consolidation successor must be canonically active"
            )
        successor_updated = _parse_timestamp(
            value.field("updated_at"),
            "Fidelity consolidation successor updated_at",
        )
        successor_plan = value.field("plan_ref")
        for prior in priors:
            require_fidelity_lifecycle_reconciled(
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
                "Fidelity consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Fidelity consolidation successor updated_at cannot precede "
                    "a predecessor update"
                )
            if prior.field("plan_ref") != successor_plan:
                raise WorkflowPrerequisiteError(
                    "duplicate consolidation requires one exact Fidelity plan"
                )

        self._root_service().require_current_use(work)
        self._resolve_plan(work, value)
        self._resolve_evaluator(work, value, current=True)
        self._resolve_scope(work, value)
        self._resolve_basis_records(work, value)
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
        """Persist one ordinary Fidelity activation/invalidation."""
        if (
            reference.record_ref.record_kind != "fidelity"
            or reference.record_ref.contract_version != FIDELITY_VERSION
        ):
            raise WorkflowOwnershipError(
                "Fidelity lifecycle requires exact fidelity@1 reference"
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
                build_fidelity_lifecycle_transition(
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
        require_fidelity_lifecycle_reconciled(
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
        """Create a corrected Fidelity successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "fidelity"
            or predecessor.record_ref.contract_version != FIDELITY_VERSION
        ):
            raise WorkflowOwnershipError(
                "Fidelity correction requires exact fidelity@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_fidelity_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = fidelity_supersession_reason_detail(successor)
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
            predecessor_factory=superseded_fidelity_predecessor,
            transition_factory=lambda prior, value: (
                build_fidelity_lifecycle_transition(
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
        require_fidelity_lifecycle_reconciled(
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
        """Move one corrected Fidelity representation to its true root."""
        _require_fidelity_owner(destination_work)
        source_work = require_fidelity_work_root_correction_predecessor(
            destination_work,
            predecessor,
            successor,
        )
        reason_detail = fidelity_supersession_reason_detail(successor)
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
            predecessor_factory=superseded_fidelity_predecessor,
            transition_factory=lambda prior, value: (
                build_fidelity_lifecycle_transition(
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
        require_fidelity_lifecycle_reconciled(
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
        """Create one canonical successor for duplicate Fidelity records."""
        _require_fidelity_owner(work)
        predecessors = require_duplicate_fidelity_consolidation_predecessors(
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
            return build_fidelity_lifecycle_transition(
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
            predecessor_factory=superseded_fidelity_predecessor,
            transition_factory=build_transition,
        )
        for predecessor in predecessors:
            accepted = self.load_exact(predecessor)
            require_fidelity_lifecycle_reconciled(
                self.repository,
                work,
                accepted.record,
            )
        return result

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Create one active digital Fidelity evaluation after complete preflight."""
        candidate = self._require_write_input(work, record)
        self._root_service().require_current_use(work)
        self._resolve_plan(work, candidate)
        self._resolve_evaluator(work, candidate, current=True)
        self._resolve_scope(work, candidate)
        self._resolve_basis_records(work, candidate)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        """Load exactly the requested Fidelity record without successor following."""
        _require_fidelity_owner(reference.work_ref)
        if reference.record_ref.record_kind != "fidelity":
            raise WorkflowOwnershipError("reference is not Fidelity")
        if reference.record_ref.contract_version != FIDELITY_VERSION:
            raise WorkflowOwnershipError(
                "unsupported exact Fidelity contract version "
                f"{reference.record_ref.contract_version!r}"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "fidelity",
            FIDELITY_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        """List exact canonical Fidelity identities for one Support Process."""
        _require_fidelity_owner(work)
        return self.repository.list_work_records(
            work,
            "fidelity",
            version=FIDELITY_VERSION,
        )

    list_fidelity_records = list

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Require one canonically active Fidelity evaluation without inferring Outcome."""
        fidelity = self.load_exact(reference)
        require_fidelity_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            fidelity.record,
        )
        self._require_existing_record(reference.work_ref, fidelity.record)
        if fidelity.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Fidelity use requires active canonical status"
            )

        predecessors = fidelity_supersession_ancestry(
            self.repository,
            reference.work_ref,
            fidelity.record,
        )
        require_fidelity_supersession_effective(predecessors)
        for predecessor in predecessors:
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )

        self._root_service().require_current_use(reference.work_ref)
        self._resolve_plan(reference.work_ref, fidelity.record)
        self._resolve_evaluator(reference.work_ref, fidelity.record, current=True)
        self._resolve_scope(reference.work_ref, fidelity.record)
        self._resolve_basis_records(reference.work_ref, fidelity.record)
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, fidelity.record),
            "block_current_use",
        )
        return fidelity

    resolve_current = require_current_use
