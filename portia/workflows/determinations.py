"""Production creation and current-use workflow for Event-local ``determination@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from portia.models import DeterminationV1, PortiaRecord
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    ModuleWorkRecordRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.accounts import AccountWorkflowService, account_reference
from portia.workflows.common import record_target, work_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from portia.workflows.evidence_artifacts import require_source_artifact_refs_authority
from portia.workflows.judgment_common import (
    JudgmentReadService,
    judgment_reference,
    judgment_target_records,
    require_digital_judgment_creation,
    require_judgment_current_materialization,
    require_judgment_owner_current_eligibility,
    require_judgment_owner_write_eligibility,
    require_judgment_record_owner,
    require_judgment_targets_current_use,
    require_represented_human_authority,
    validate_partial_judgment_graph,
)
from portia.workflows.judgment_evidence import (
    JudgmentEvidenceResolution,
    ModuleJudgmentEvidenceAuthority,
    resolve_judgment_evidence,
)
from portia.workflows.judgment_lifecycle import (
    require_judgment_lifecycle_reconciled,
)
from portia.workflows.judgment_transition import JudgmentLifecycleCoordinator
from portia.workflows.observations import (
    ObservationWorkflowService,
    observation_reference,
)
from portia.workflows.reviews import ReviewWorkflowService, review_reference


def determination_reference(
    work: ExactPortiaWorkRef,
    determination_id: str,
) -> ExactPortiaWorkRecordRef:
    return judgment_reference(work, "determination", determination_id)


def _exact_review(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> StoredRecord | None:
    value = record.field("review_ref")
    if value is None:
        return None
    reference = ExactPortiaWorkRecordRef.from_dict(value)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            "Determination Review must belong to the same Event"
        )
    if (
        reference.record_ref.record_kind != "review"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Determination review_ref must name exact review@1"
        )
    return repository.load_work_record(
        work,
        "review",
        "1",
        reference.record_ref.record_id,
    )


def _evidence_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Determination basis reference is malformed")
    kind = value.get("kind")
    if kind == "portia_work":
        work_reference = ExactPortiaWorkRef.from_dict(value.get("work_ref"))
        return (
            kind,
            work_reference.class_id,
            work_reference.work_id,
            work_reference.contract_version,
        )
    if kind == "portia_record":
        record_reference = ExactPortiaWorkRecordRef.from_dict(
            value.get("work_record_ref")
        )
        return (
            kind,
            record_reference.work_ref.class_id,
            record_reference.work_ref.work_id,
            record_reference.record_ref.record_kind,
            record_reference.record_ref.record_id,
            record_reference.record_ref.contract_version,
        )
    if kind == "module_record":
        module_reference = ModuleWorkRecordRef.from_dict(
            value.get("module_work_record_ref")
        )
        return (
            kind,
            module_reference.work_ref.module_id,
            module_reference.work_ref.class_id,
            module_reference.work_ref.work_id,
            module_reference.record_ref.module_id,
            module_reference.record_ref.record_kind,
            module_reference.record_ref.record_id,
            module_reference.record_ref.contract_version,
        )
    raise WorkflowOwnershipError(f"unsupported Determination basis kind {kind!r}")


def _basis_values(record: PortiaRecord) -> tuple[object, ...]:
    entries = record.field("basis")
    if entries is None:
        return ()
    if not isinstance(entries, tuple):
        raise WorkflowOwnershipError("Determination basis is malformed")
    values: list[object] = []
    identities: list[tuple[object, ...]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowOwnershipError("Determination basis entry is malformed")
        evidence_ref = entry.get("evidence_ref")
        values.append(evidence_ref)
        identities.append(_evidence_identity(evidence_ref))
    if len(identities) != len(set(identities)):
        raise WorkflowOwnershipError(
            "Determination basis repeats the same logical evidence identity"
        )
    return tuple(values)


def _artifact_values(value: object, *, field_name: str) -> tuple[object, ...]:
    if value is None:
        return ()
    if not isinstance(value, tuple):
        raise WorkflowOwnershipError(f"Determination {field_name} is malformed")
    return tuple(value)


class DeterminationWorkflowService(JudgmentReadService):
    """Create and qualify bounded human Determinations without automated judgment."""

    CONTRACT = "determination"

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
    ) -> DeterminationV1:
        if not isinstance(record, DeterminationV1):
            raise WorkflowOwnershipError(
                "new Determination writes require determination@1 input"
            )
        require_judgment_record_owner(work, record, contract="determination")
        require_digital_judgment_creation(record)
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Determination identity must begin proposed or active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "Determination correction/reconsideration requires the later "
                "coordinated successor path"
            )
        return record

    def _require_decision_maker(
        self,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> None:
        authority = record.field("authority_context")
        maker = record.field("decision_maker")
        if not isinstance(authority, Mapping) or not isinstance(maker, Mapping):
            raise WorkflowOwnershipError(
                "Determination authority or decision-maker attribution is malformed"
            )
        authority_kind = authority.get("kind")
        maker_kind = maker.get("kind")

        if authority_kind == "teacher_local":
            if maker_kind != "local_operator":
                raise WorkflowPrerequisiteError(
                    "teacher-local Determination requires local-operator decision-maker"
                )
            require_represented_human_authority(
                self.contexts,
                maker,
                field_name="Determination decision-maker",
                require_current_use=require_current_use,
            )
            return

        if authority_kind != "recorded_institutional":
            raise WorkflowOwnershipError(
                f"unsupported Determination authority context {authority_kind!r}"
            )

        if maker_kind == "actor":
            require_represented_human_authority(
                self.contexts,
                maker,
                field_name="Determination decision-maker",
                require_current_use=require_current_use,
            )
            return
        if maker_kind == "local_operator":
            return
        if maker_kind == "descriptive_person":
            if maker.get("description_type") != "school_staff":
                raise WorkflowPrerequisiteError(
                    "recorded-institutional Determination requires school-staff "
                    "descriptive decision-maker"
                )
            return
        if maker_kind == "unidentified_person":
            # Historical/current representation may honestly preserve an unidentified
            # institutional decision-maker; authority provenance remains separate.
            return
        raise WorkflowPrerequisiteError(
            "decision-maker attribution is ineligible for recorded-institutional "
            "Determination"
        )

    def _require_authority_and_process_artifacts(
        self,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> None:
        authority = record.field("authority_context")
        if not isinstance(authority, Mapping):
            raise WorkflowOwnershipError("Determination authority context is malformed")
        if (
            authority.get("kind") == "recorded_institutional"
            and authority.get("authority_status") == "documented_basis"
        ):
            artifacts = _artifact_values(
                authority.get("authority_basis"),
                field_name="authority_basis",
            )
            require_source_artifact_refs_authority(
                self.workspace_root,
                self.repository,
                artifacts,
                require_current_use=require_current_use,
            )

        process_basis = record.field("process_basis")
        if not isinstance(process_basis, Mapping):
            raise WorkflowOwnershipError("Determination process basis is malformed")
        if process_basis.get("kind") != "identified":
            return
        for descriptor_name in ("policy", "process"):
            descriptor = process_basis.get(descriptor_name)
            if descriptor is None:
                continue
            if not isinstance(descriptor, Mapping):
                raise WorkflowOwnershipError(
                    f"Determination {descriptor_name} descriptor is malformed"
                )
            artifacts = _artifact_values(
                descriptor.get("source_artifacts"),
                field_name=f"{descriptor_name} source_artifacts",
            )
            if artifacts:
                require_source_artifact_refs_authority(
                    self.workspace_root,
                    self.repository,
                    artifacts,
                    require_current_use=require_current_use,
                )

    def _resolve_review(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> StoredRecord | None:
        review = _exact_review(self.repository, work, record)
        if review is None:
            return None
        if record.to_dict().get("target") != review.record.to_dict().get("target"):
            raise WorkflowPrerequisiteError(
                "Determination target must match the governing Review target"
            )
        if require_current_use:
            review_id = review.record.logical_id
            if review_id is None:
                raise WorkflowOwnershipError("governing Review has no logical identity")
            review = ReviewWorkflowService(
                self.workspace_root,
                repository=self.repository,
                quarantine=self.quarantine,
                context_assembler=self.contexts,
                module_authority=self.module_authority,
            ).require_current_use(review_reference(work, review_id))
            if review.record.field("review_state") != "completed":
                raise WorkflowPrerequisiteError(
                    "active linked Determination requires an active completed Review"
                )
        return review

    def _resolve_basis(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_module_authority: bool,
    ) -> tuple[JudgmentEvidenceResolution, ...]:
        resolved: list[JudgmentEvidenceResolution] = []
        for value in _basis_values(record):
            if not isinstance(value, Mapping):
                raise WorkflowOwnershipError(
                    "Determination basis reference is malformed"
                )
            kind = value.get("kind")
            if kind == "portia_work":
                work_reference = ExactPortiaWorkRef.from_dict(value.get("work_ref"))
                if work_reference != work:
                    raise WorkflowOwnershipError(
                        "Event-local Determination basis cannot resolve another "
                        "Portia work"
                    )
            elif kind == "portia_record":
                record_reference = ExactPortiaWorkRecordRef.from_dict(
                    value.get("work_record_ref")
                )
                if record_reference.work_ref != work:
                    raise WorkflowOwnershipError(
                        "Event-local Determination basis cannot resolve another "
                        "Portia work"
                    )
            elif kind == "module_record" and not require_module_authority:
                module_reference = ModuleWorkRecordRef.from_dict(
                    value.get("module_work_record_ref")
                )
                if (
                    module_reference.work_ref.module_id
                    != module_reference.record_ref.module_id
                ):
                    raise WorkflowOwnershipError(
                        "module judgment evidence work and record identities disagree"
                    )
                if module_reference.work_ref.module_id == "portia":
                    raise WorkflowOwnershipError(
                        "Portia records must use the portia_record "
                        "judgment-evidence branch"
                    )
                resolved.append(
                    JudgmentEvidenceResolution(
                        kind="module_record",
                        module_reference=module_reference,
                    )
                )
                continue
            resolved.append(
                resolve_judgment_evidence(
                    self.repository,
                    value,
                    module_authority=self.module_authority,
                )
            )
        return tuple(resolved)

    def _require_current_basis_acceptance(
        self,
        work: ExactPortiaWorkRef,
        resolutions: Sequence[JudgmentEvidenceResolution],
    ) -> None:
        for resolution in resolutions:
            stored = resolution.stored
            if stored is None:
                if (
                    resolution.kind == "module_record"
                    and resolution.module_value is None
                ):
                    raise WorkflowPrerequisiteError(
                        "active Determination module basis requires explicit "
                        "resolution authority"
                    )
                continue
            if resolution.kind == "portia_work":
                self.quarantine.require_allowed(work_target(work), "block_current_use")
                continue
            self.quarantine.require_allowed(
                record_target(work, stored.record), "block_current_use"
            )
            identifier = stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Determination basis record has no logical identity"
                )
            if stored.record.contract == "account":
                AccountWorkflowService(
                    self.workspace_root,
                    repository=self.repository,
                    quarantine=self.quarantine,
                    context_assembler=self.contexts,
                ).require_current_use(
                    account_reference(
                        work,
                        identifier,
                        version=stored.record.contract_version,
                    )
                )
            elif stored.record.contract == "observation":
                ObservationWorkflowService(
                    self.workspace_root,
                    repository=self.repository,
                    quarantine=self.quarantine,
                    context_assembler=self.contexts,
                ).require_current_use(
                    observation_reference(
                        work,
                        identifier,
                        version=stored.record.contract_version,
                    )
                )

    def _require_activation_candidate(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> None:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        self._require_decision_maker(candidate, require_current_use=True)
        review = self._resolve_review(
            work,
            candidate,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=True,
        )
        self._require_authority_and_process_artifacts(
            candidate,
            require_current_use=True,
        )
        require_judgment_owner_current_eligibility(owner.record)
        require_judgment_targets_current_use(
            work,
            targets,
            quarantine=self.quarantine,
        )
        self._require_current_basis_acceptance(work, basis)
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                candidate,
            ),
        )

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> None:
        if not isinstance(record, DeterminationV1):
            raise WorkflowOwnershipError(
                "Determination correction successor must use determination@1"
            )
        require_judgment_record_owner(work, record, contract="determination")
        require_digital_judgment_creation(record)
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "Determination correction successor must be active"
            )
        if record.field("supersedes") is None:
            raise WorkflowPrerequisiteError(
                "Determination correction successor must preserve exact "
                "supersession provenance"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, record)
        self._require_decision_maker(record, require_current_use=True)
        review = self._resolve_review(
            work,
            record,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            work,
            record,
            require_module_authority=True,
        )
        self._require_authority_and_process_artifacts(
            record,
            require_current_use=True,
        )
        require_judgment_owner_current_eligibility(owner.record)
        require_judgment_targets_current_use(
            work,
            targets,
            quarantine=self.quarantine,
        )
        self._require_current_basis_acceptance(work, basis)
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                record,
            ),
        )

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        self._require_decision_maker(
            candidate,
            require_current_use=candidate.status == "active",
        )
        review = self._resolve_review(
            work,
            candidate,
            require_current_use=candidate.status == "active",
        )
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=candidate.status == "active",
        )
        self._require_authority_and_process_artifacts(
            candidate,
            require_current_use=candidate.status == "active",
        )

        if candidate.status == "active":
            require_judgment_owner_current_eligibility(owner.record)
            require_judgment_targets_current_use(
                work,
                targets,
                quarantine=self.quarantine,
            )
            self._require_current_basis_acceptance(work, basis)

        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                candidate,
            ),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

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
        """Create a corrected Determination successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "determination":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Determination"
            )
        coordinator = JudgmentLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit_correction(
            predecessor,
            successor,
            expected=expected,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=lambda value: self._require_correction_successor(
                predecessor.work_ref, value
            ),
        )

    def reconsider(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        review_reference: ExactPortiaWorkRecordRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create a reconsidered or reversed Determination successor."""
        if predecessor.record_ref.record_kind != "determination":
            raise WorkflowOwnershipError(
                "reconsideration predecessor is not a Determination"
            )
        if review_reference.record_ref.record_kind != "review":
            raise WorkflowOwnershipError(
                "Determination reconsideration requires an exact Review"
            )
        coordinator = JudgmentLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit_determination_reconsideration(
            predecessor,
            review_reference,
            successor,
            expected=expected,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
            successor_validator=lambda value: self._require_correction_successor(
                predecessor.work_ref, value
            ),
        )

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
        """Persist one ordinary Determination lifecycle transition."""
        if reference.record_ref.record_kind != "determination":
            raise WorkflowOwnershipError(
                "reference is not a Determination"
            )
        coordinator = JudgmentLifecycleCoordinator(
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
            activation_validator=lambda value: self._require_activation_candidate(
                reference.work_ref, value
            ),
        )

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        determination = self.load_exact(reference)
        require_judgment_lifecycle_reconciled(
            self.repository, reference.work_ref, determination.record
        )
        if determination.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Determination use requires an active canonical Determination"
            )
        require_judgment_current_materialization(determination.record)
        owner = self.repository.load_work(reference.work_ref)
        require_judgment_owner_current_eligibility(owner.record)
        targets = judgment_target_records(
            self.repository,
            reference.work_ref,
            determination.record,
        )
        require_judgment_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        self._require_decision_maker(
            determination.record,
            require_current_use=True,
        )
        review = self._resolve_review(
            reference.work_ref,
            determination.record,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            reference.work_ref,
            determination.record,
            require_module_authority=True,
        )
        # Basis already accepted into this exact Determination remains historical
        # decision basis. Later Account/Observation lifecycle changes do not
        # silently rewrite or disqualify that accepted reference; Quarantine can
        # still block consequential use of the exact representation.
        for resolution in basis:
            if resolution.stored is not None and resolution.kind == "portia_record":
                self.quarantine.require_allowed(
                    record_target(reference.work_ref, resolution.stored.record),
                    "block_current_use",
                )
        self._require_authority_and_process_artifacts(
            determination.record,
            require_current_use=True,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, determination.record),
            "block_current_use",
        )
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                determination.record,
            ),
        )
        return determination

    resolve_current = require_current_use

    def list_determinations(
        self, work: ExactPortiaWorkRef
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)
