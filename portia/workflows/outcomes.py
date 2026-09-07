"""Production core workflow service for work-local ``outcome@1`` records."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from portia.models import OutcomeV1, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    ModuleWorkRecordRef,
)
from portia.storage.errors import PortiaNotFoundError
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
    outcome_reference,
    parse_date_only,
    parse_explicit_timestamp,
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
    require_material_outcome_correction,
    superseded_downstream_predecessor,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_OUTCOME_EVALUATOR_CONTEXTS = frozenset(
    {"provider_or_collaborator", "coordinator", "observer"}
)
_SPECIAL_BASIS_ROLE_CONTRACTS = {
    "student_or_family_perspective": "account",
    "implementation_context": "implementation",
    "fidelity_context": "fidelity",
}
_SCOPE_LOCAL_CONTRACTS = {
    "goal_status": ("goal_ref", frozenset({"support_goal"})),
    "reentry_status": ("reentry_ref", frozenset({"reentry"})),
    "repair_status": ("repair_ref", frozenset({"repair"})),
}


_WORK_ROOT_PRESERVED_FACT_FIELDS = (
    "scope",
    "timeframe",
    "basis",
    "result",
    "result_detail",
    "limitations",
    "summary",
    "creation_source",
)


class ModuleOutcomeBasisAuthority(Protocol):
    """Explicit public authority for one exact sibling-module Outcome basis."""

    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        """Resolve and authorize exactly the supplied sibling-module reference."""
        ...


@dataclass(frozen=True, slots=True)
class OutcomeBasisResolution:
    """One exact Outcome basis branch without changing semantic authority."""

    role: str
    kind: str
    exact: DownstreamExactRecordResolution | None = None
    module_reference: ModuleWorkRecordRef | None = None
    module_value: object | None = None


class OutcomeWorkflowService(ActionReadService):
    """Create and qualify exact teacher-local ``outcome@1`` records."""

    CONTRACT = "outcome"

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        module_basis_authority: ModuleOutcomeBasisAuthority | None = None,
    ) -> None:
        super().__init__(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=context_assembler,
        )
        self.module_basis_authority = module_basis_authority

    def _authority(self) -> DownstreamWorkflowAuthority:
        return DownstreamWorkflowAuthority(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    @staticmethod
    def _require_outcome_record(
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> OutcomeV1:
        require_downstream_record_owner(work, record, contract="outcome")
        if not isinstance(record, OutcomeV1):
            raise WorkflowOwnershipError(
                "Outcome workflow requires outcome@1 input"
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
            raise WorkflowOwnershipError("Outcome creation_source is malformed")
        source_type = source.get("type")
        if fresh_digital_write and source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "new digital Outcome authoring accepts "
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
            earlier_name="Outcome created_at",
            later_name="Outcome updated_at",
        )

        timeframe = record.field("timeframe")
        if not isinstance(timeframe, Mapping):
            raise WorkflowOwnershipError("Outcome timeframe is malformed")
        precision = timeframe.get("precision")
        if precision in {"exact", "approximate"}:
            parse_explicit_timestamp(
                timeframe.get("at"),
                field_name="Outcome timeframe at",
            )
            return
        if precision == "date_only":
            parse_date_only(
                timeframe.get("date"),
                field_name="Outcome timeframe date",
            )
            return
        if precision == "range":
            require_timestamp_order(
                timeframe.get("started_at"),
                timeframe.get("ended_at"),
                earlier_name="Outcome timeframe started_at",
                later_name="Outcome timeframe ended_at",
            )
            return
        if precision == "unknown":
            if record.status == "active":
                raise WorkflowPrerequisiteError(
                    "active Outcome timeframe may not be unknown"
                )
            return
        raise WorkflowOwnershipError(
            f"unsupported Outcome timeframe precision {precision!r}"
        )

    def _require_evaluator_authority(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> None:
        evaluator = record.field("evaluator")
        if not isinstance(evaluator, Mapping):
            raise WorkflowOwnershipError("Outcome evaluator is malformed")
        authority = self._authority()

        if work.work_kind == "event":
            if evaluator.get("kind") != "represented_human":
                raise WorkflowOwnershipError(
                    "Event Outcome evaluator must be represented_human"
                )
            authority.require_event_operational_human(
                evaluator.get("person"),
                field_name="Outcome evaluator",
                require_current_use=require_current_use,
            )
            return

        if evaluator.get("kind") != "support_process_participant":
            raise WorkflowOwnershipError(
                "Support Process Outcome evaluator must be "
                "support_process_participant"
            )
        authority.require_support_process_operational_participant(
            work,
            evaluator.get("participant_ref"),
            field_name="Outcome evaluator",
            allowed_contexts=_OUTCOME_EVALUATOR_CONTEXTS,
            require_current_use=require_current_use,
        )

    def _resolve_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> DownstreamTargetResolution:
        # Outcome evaluates an explicit bounded historical/current target. Do
        # not require that target Participant to regain operational currency.
        return self._authority().resolve_target(
            work,
            record.field("target"),
            require_current_use=False,
        )

    @staticmethod
    def _exact_local_ref(
        value: object,
        *,
        field_name: str,
        allowed_contracts: frozenset[str],
    ) -> ExactLocalRecordRef:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(
                f"{field_name} exact local reference is malformed"
            )
        try:
            reference = ExactLocalRecordRef.from_dict(value)
        except (TypeError, ValueError) as exc:
            raise WorkflowOwnershipError(
                f"{field_name} exact local reference is malformed"
            ) from exc
        if reference.record_kind not in allowed_contracts:
            expected = ", ".join(sorted(allowed_contracts))
            raise WorkflowPrerequisiteError(
                f"{field_name} must reference one of {{{expected}}}"
            )
        return reference

    @staticmethod
    def _module_basis_reference(
        value: object,
        *,
        field_name: str,
    ) -> ModuleWorkRecordRef:
        try:
            reference = ModuleWorkRecordRef.from_dict(value)
        except Exception as exc:
            raise WorkflowOwnershipError(
                f"{field_name} module record reference is malformed"
            ) from exc
        if reference.work_ref.module_id != reference.record_ref.module_id:
            raise WorkflowOwnershipError(
                f"{field_name} module work and record identities disagree"
            )
        if reference.work_ref.module_id == "portia":
            raise WorkflowOwnershipError(
                f"{field_name} Portia records must use the portia_record basis branch"
            )
        return reference

    def _load_scope_record(
        self,
        work: ExactPortiaWorkRef,
        value: object,
        *,
        field_name: str,
        allowed_contracts: frozenset[str],
    ) -> StoredRecord:
        reference = self._exact_local_ref(
            value,
            field_name=field_name,
            allowed_contracts=allowed_contracts,
        )
        try:
            stored = self.repository.load_work_record(
                work,
                reference.record_kind,
                reference.contract_version,
                reference.record_id,
            )
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                f"{field_name} does not resolve in the owning {work.work_kind}"
            ) from exc
        if (
            stored.record.contract != reference.record_kind
            or stored.record.contract_version != reference.contract_version
            or stored.record.logical_id != reference.record_id
        ):
            raise WorkflowOwnershipError(
                f"{field_name} resolved record does not match its exact reference"
            )
        return stored

    def _resolve_scope_records(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[StoredRecord, ...]:
        scope = record.field("scope")
        if not isinstance(scope, Mapping):
            raise WorkflowOwnershipError("Outcome scope is malformed")
        kind = scope.get("kind")
        if not isinstance(kind, str):
            raise WorkflowOwnershipError("Outcome scope kind is malformed")

        policy = _SCOPE_LOCAL_CONTRACTS.get(kind)
        if policy is not None:
            field, contracts = policy
            return (
                self._load_scope_record(
                    work,
                    scope.get(field),
                    field_name=f"Outcome scope {field}",
                    allowed_contracts=contracts,
                ),
            )

        if kind == "support_response_review":
            raw_refs = scope.get("plan_refs")
            if not isinstance(raw_refs, Sequence) or isinstance(
                raw_refs, (str, bytes, bytearray)
            ):
                raise WorkflowOwnershipError(
                    "Outcome support_response_review plan_refs are malformed"
                )
            return tuple(
                self._load_scope_record(
                    work,
                    item,
                    field_name=f"Outcome scope plan_refs[{index}]",
                    allowed_contracts=frozenset({"support", "intervention"}),
                )
                for index, item in enumerate(raw_refs)
            )

        if kind in {
            "observed_change",
            "recurrence_review",
            "unintended_or_adverse_effect_review",
            "other",
        }:
            return ()

        raise WorkflowOwnershipError(f"unsupported Outcome scope kind {kind!r}")

    def _resolve_basis(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_module_authority: bool,
    ) -> tuple[OutcomeBasisResolution, ...]:
        values = record.field("basis")
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError("Outcome basis is malformed")
        record_id = record.logical_id
        if not isinstance(record_id, str):
            raise WorkflowOwnershipError("Outcome has no exact record identity")
        self_reference = outcome_reference(work, record_id)

        authority = self._authority()
        resolutions: list[OutcomeBasisResolution] = []
        seen: set[tuple[object, ...]] = set()
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"Outcome basis entry {index} is malformed"
                )
            role = item.get("role")
            locator = item.get("locator")
            if not isinstance(role, str) or not isinstance(locator, Mapping):
                raise WorkflowOwnershipError(
                    f"Outcome basis entry {index} is malformed"
                )
            kind = locator.get("kind")

            if kind == "module_record":
                module_reference = self._module_basis_reference(
                    locator.get("module_work_record_ref"),
                    field_name=f"Outcome basis entry {index}",
                )
                identity = (
                    "module_record",
                    module_reference.work_ref.module_id,
                    module_reference.work_ref.class_id,
                    module_reference.work_ref.work_id,
                    module_reference.record_ref.module_id,
                    module_reference.record_ref.record_kind,
                    module_reference.record_ref.record_id,
                    module_reference.record_ref.contract_version,
                    role,
                )
                if identity in seen:
                    raise WorkflowPrerequisiteError(
                        "Outcome basis cannot repeat one exact identity/role"
                    )

                if not require_module_authority:
                    resolved = None
                elif self.module_basis_authority is None:
                    raise WorkflowPrerequisiteError(
                        "Outcome module_record basis requires an explicit public "
                        "resolution authority"
                    )
                else:
                    resolved = self.module_basis_authority.resolve_exact(
                        module_reference
                    )
                    if resolved is None:
                        raise WorkflowPrerequisiteError(
                            "Outcome module_record basis did not resolve through the "
                            "supplied authority"
                        )

                seen.add(identity)
                resolutions.append(
                    OutcomeBasisResolution(
                        role=role,
                        kind="module_record",
                        module_reference=module_reference,
                        module_value=resolved,
                    )
                )
                continue

            if kind != "portia_record":
                raise WorkflowOwnershipError(
                    f"Outcome basis entry {index} locator is malformed"
                )

            raw_reference = locator.get("record_ref")
            try:
                portia_reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
            except Exception as exc:
                raise WorkflowOwnershipError(
                    f"Outcome basis entry {index} exact record reference is malformed"
                ) from exc
            if portia_reference == self_reference:
                raise WorkflowPrerequisiteError(
                    "Outcome basis cannot reference the current Outcome itself"
                )

            identity = (
                "portia_record",
                portia_reference.work_ref.class_id,
                portia_reference.work_ref.work_kind,
                portia_reference.work_ref.work_id,
                portia_reference.work_ref.contract_version,
                portia_reference.record_ref.record_kind,
                portia_reference.record_ref.record_id,
                portia_reference.record_ref.contract_version,
                role,
            )
            if identity in seen:
                raise WorkflowPrerequisiteError(
                    "Outcome basis cannot repeat one exact identity/role"
                )
            required_contract = _SPECIAL_BASIS_ROLE_CONTRACTS.get(role)
            if (
                required_contract is not None
                and portia_reference.record_ref.record_kind != required_contract
            ):
                raise WorkflowPrerequisiteError(
                    f"Outcome basis role {role!r} requires "
                    f"{required_contract!r}"
                )

            exact = authority.resolve_exact_work_record(
                work,
                portia_reference.to_dict(),
                field_name=f"Outcome basis entry {index}",
                require_same_class=True,
                require_same_work=False,
            )
            seen.add(identity)
            resolutions.append(
                OutcomeBasisResolution(
                    role=role,
                    kind="portia_record",
                    exact=exact,
                )
            )
        if not resolutions:
            raise WorkflowPrerequisiteError(
                "Outcome requires at least one explicit basis item"
            )
        return tuple(resolutions)

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
        OutcomeV1,
        DownstreamTargetResolution,
        tuple[StoredRecord, ...],
        tuple[OutcomeBasisResolution, ...],
    ]:
        candidate = self._require_outcome_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=False,
            current_use=require_current_use,
        )
        self._require_chronology(candidate)
        self._require_supersession_topology(candidate)
        self._require_evaluator_authority(
            work,
            candidate,
            require_current_use=require_current_use,
        )
        target = self._resolve_target(work, candidate)
        scope_records = self._resolve_scope_records(work, candidate)
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=require_current_use,
        )
        return candidate, target, scope_records, basis

    def _require_current_dependency_quarantine(
        self,
        work: ExactPortiaWorkRef,
        target: DownstreamTargetResolution,
        scope_records: tuple[StoredRecord, ...],
        basis: tuple[OutcomeBasisResolution, ...],
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
        for stored in scope_records:
            self.quarantine.require_allowed(
                record_target(work, stored.record),
                "block_current_use",
            )
        for item in basis:
            if item.exact is None:
                continue
            self.quarantine.require_allowed(
                work_target(item.exact.reference.work_ref),
                "block_current_use",
            )
            self.quarantine.require_allowed(
                record_target(
                    item.exact.reference.work_ref,
                    item.exact.stored.record,
                ),
                "block_current_use",
            )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one fresh digital Outcome identity after exact validation."""
        candidate = self._require_outcome_record(work, record)
        self._require_creation_source(
            candidate,
            fresh_digital_write=True,
            current_use=False,
        )
        if candidate.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Outcome must begin proposed or active"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Outcome identity cannot establish supersession history"
            )

        self._require_chronology(candidate)
        require_current = candidate.status == "active"
        self._require_evaluator_authority(
            work,
            candidate,
            require_current_use=require_current,
        )
        target = self._resolve_target(work, candidate)
        scope_records = self._resolve_scope_records(work, candidate)
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=require_current,
        )

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
                scope_records,
                basis,
            )
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        return self.repository.create_work_record(work, candidate)

    def list_outcomes(
        self,
        work: ExactPortiaWorkRef,
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)

    def _require_lifecycle_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> OutcomeV1:
        value = self._require_outcome_record(work, candidate)
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
        scope_records = self._resolve_scope_records(work, value)
        basis = self._resolve_basis(
            work,
            value,
            require_module_authority=value.status == "active",
        )
        self._require_supersession_topology(value)

        if value.status == "active":
            self._require_evaluator_authority(
                work,
                value,
                require_current_use=True,
            )
            self._require_current_dependency_quarantine(
                work,
                target,
                scope_records,
                basis,
            )
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )
        else:
            self._require_evaluator_authority(
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
        """Persist one ordinary Outcome activation/invalidation."""
        if (
            reference.record_ref.record_kind != "outcome"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Outcome lifecycle requires exact outcome@1 reference"
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
    ) -> OutcomeV1:
        value = self._require_outcome_record(work, successor)
        require_downstream_lifecycle_reconciled(
            self.repository,
            work,
            prior,
        )
        if prior.status == "superseded":
            raise WorkflowPrerequisiteError(
                "Outcome correction cannot reuse a superseded predecessor"
            )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "corrected Outcome successor must be active"
            )

        self._require_creation_source(
            value,
            fresh_digital_write=False,
            current_use=True,
        )
        self._require_chronology(value)
        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Outcome predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Outcome successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Outcome successor updated_at cannot precede predecessor update"
            )
        require_material_outcome_correction(
            prior,
            value,
            supersession_reason,
        )
        self._require_supersession_topology(value)

        self._require_evaluator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        scope_records = self._resolve_scope_records(work, value)
        basis = self._resolve_basis(
            work,
            value,
            require_module_authority=True,
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
            scope_records,
            basis,
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
        """Create one corrected Outcome successor and supersede its predecessor."""
        if (
            predecessor.record_ref.record_kind != "outcome"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Outcome correction requires exact outcome@1 predecessor"
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
    ) -> OutcomeV1:
        value = self._require_outcome_record(work, successor)
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "duplicate Outcome consolidation successor must be active"
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
            field_name="Outcome consolidation successor updated_at",
        )
        for prior in priors:
            self._require_outcome_record(work, prior)
            require_downstream_lifecycle_reconciled(
                self.repository,
                work,
                prior,
            )
            if prior.status not in {"active", "invalidated"}:
                raise WorkflowPrerequisiteError(
                    "duplicate Outcome consolidation predecessor must be "
                    "active or invalidated"
                )
            prior_updated = parse_explicit_timestamp(
                prior.field("updated_at"),
                field_name="Outcome consolidation predecessor updated_at",
            )
            if successor_updated < prior_updated:
                raise WorkflowPrerequisiteError(
                    "Outcome consolidation successor updated_at cannot "
                    "precede a predecessor update"
                )

        # Duplication is an explicit human-selected supersession fact.
        # Do not infer duplication from Outcome content similarity.
        self._require_evaluator_authority(
            work,
            value,
            require_current_use=True,
        )
        target = self._resolve_target(work, value)
        scope_records = self._resolve_scope_records(work, value)
        basis = self._resolve_basis(
            work,
            value,
            require_module_authority=True,
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
            scope_records,
            basis,
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
        """Create one active canonical Outcome from explicit duplicates."""
        predecessors = require_duplicate_downstream_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Outcome consolidation requires one expected "
                "fingerprint for every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Outcome consolidation requires one lifecycle "
                "transition ID for every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "duplicate Outcome consolidation lifecycle transition IDs "
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
    ) -> OutcomeV1:
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
                "work-root Outcome correction predecessor must be "
                "active or invalidated"
            )

        value, target, scope_records, basis = self._validate_existing(
            destination_work,
            successor,
            require_current_use=True,
        )
        if value.status != "active":
            raise WorkflowPrerequisiteError(
                "work-root Outcome correction successor must be active"
            )
        if prior.logical_id != value.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root Outcome correction must preserve Outcome ID"
            )

        prior_updated = parse_explicit_timestamp(
            prior.field("updated_at"),
            field_name="Outcome work-root predecessor updated_at",
        )
        successor_updated = parse_explicit_timestamp(
            value.field("updated_at"),
            field_name="Outcome work-root successor updated_at",
        )
        if successor_updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Outcome work-root successor updated_at cannot precede "
                "predecessor update"
            )

        prior_data = prior.to_dict()
        successor_data = value.to_dict()
        for field in _WORK_ROOT_PRESERVED_FACT_FIELDS:
            if prior_data.get(field) != successor_data.get(field):
                raise WorkflowPrerequisiteError(
                    "work-root Outcome correction cannot rewrite fact "
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
            scope_records,
            basis,
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
        """Move one Outcome representation to its corrected owning work root."""
        if (
            predecessor.record_ref.record_kind != "outcome"
            or predecessor.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Outcome work-root correction requires exact outcome@1 "
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

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Require one exact active Outcome without following successors."""
        outcome = self.load_exact(reference)
        require_downstream_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            outcome.record,
        )
        candidate, target, scope_records, basis = self._validate_existing(
            reference.work_ref,
            outcome.record,
            require_current_use=False,
        )
        if candidate.status != "active":
            raise WorkflowPrerequisiteError(
                "current Outcome use requires active canonical status"
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
        self._require_evaluator_authority(
            reference.work_ref,
            candidate,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            reference.work_ref,
            candidate,
            require_module_authority=True,
        )
        self._require_current_dependency_quarantine(
            reference.work_ref,
            target,
            scope_records,
            basis,
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, candidate),
            "block_current_use",
        )
        return outcome

    resolve_current = require_current_use
