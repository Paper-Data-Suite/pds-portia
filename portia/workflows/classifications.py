"""Production creation and current-use workflow for Event-local ``classification@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from portia.models import ClassificationV1, PortiaRecord
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
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
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
    resolve_judgment_evidence_set,
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

_REVIEWER_STAGES = frozenset({"reviewer_selected", "reviewer_confirmed"})


def classification_reference(
    work: ExactPortiaWorkRef,
    classification_id: str,
) -> ExactPortiaWorkRecordRef:
    return judgment_reference(work, "classification", classification_id)


def _represented_human_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Classification represented-human attribution is malformed")
    kind = value.get("kind")
    if kind == "roster_student":
        reference = value.get("roster_student_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Classification roster attribution is malformed")
        return (kind, reference.get("class_id"), reference.get("student_id"))
    if kind == "actor":
        reference = value.get("actor_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Classification Actor attribution is malformed")
        return (kind, reference.get("actor_id"))
    if kind == "local_operator":
        return (kind, value.get("display_label"))
    if kind == "descriptive_person":
        return (kind, value.get("description_type"), value.get("display_label"))
    if kind == "unidentified_person":
        return (kind, value.get("identity_status"), value.get("display_label"))
    raise WorkflowOwnershipError(f"unsupported Classification selector kind {kind!r}")


def _result_identity(record: PortiaRecord) -> tuple[object, ...]:
    result = record.field("result")
    if not isinstance(result, Mapping):
        raise WorkflowOwnershipError("Classification result is malformed")
    kind = result.get("kind")
    if kind == "unable_to_determine":
        return (kind,)
    if kind == "category_selected":
        definition = result.get("definition")
        if not isinstance(definition, Mapping):
            raise WorkflowOwnershipError("Classification definition snapshot is malformed")
        return (
            kind,
            definition.get("scheme_id"),
            definition.get("scheme_version"),
            definition.get("category_code"),
        )
    raise WorkflowOwnershipError(f"unsupported Classification result kind {kind!r}")


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
        raise WorkflowOwnershipError("Classification Review must belong to the same Event")
    if (
        reference.record_ref.record_kind != "review"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError("Classification review_ref must name exact review@1")
    return repository.load_work_record(
        work,
        "review",
        "1",
        reference.record_ref.record_id,
    )


def _exact_reviewed_classification(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> StoredRecord | None:
    value = record.field("reviewed_classification")
    if value is None:
        return None
    reference = ExactPortiaWorkRecordRef.from_dict(value)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            "reviewed Classification must belong to the same Event"
        )
    if (
        reference.record_ref.record_kind != "classification"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "reviewed_classification must name exact classification@1"
        )
    if reference.record_ref.record_id == record.logical_id:
        raise WorkflowOwnershipError("Classification cannot review itself")
    return repository.load_work_record(
        work,
        "classification",
        "1",
        reference.record_ref.record_id,
    )


def _basis_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Classification basis reference is malformed")
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
    raise WorkflowOwnershipError(f"unsupported Classification basis kind {kind!r}")


def _require_unique_basis(record: PortiaRecord) -> None:
    raw = record.field("basis")
    if raw is None:
        return
    if not isinstance(raw, tuple):
        raise WorkflowOwnershipError("Classification basis is malformed")
    identities = [_basis_identity(value) for value in raw]
    if len(identities) != len(set(identities)):
        raise WorkflowOwnershipError(
            "Classification basis repeats the same logical evidence identity"
        )


class ClassificationWorkflowService(JudgmentReadService):
    """Create and qualify exact human-authored Classification assertions."""

    CONTRACT = "classification"

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
    ) -> ClassificationV1:
        if not isinstance(record, ClassificationV1):
            raise WorkflowOwnershipError(
                "new Classification writes require classification@1 input"
            )
        require_judgment_record_owner(work, record, contract="classification")
        require_digital_judgment_creation(record)
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Classification identity must begin proposed or active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "Classification correction/supersession requires the later coordinated correction path"
            )
        if record.field("stage") == "unknown":
            raise WorkflowPrerequisiteError(
                "new digital Classification cannot author the historical unknown stage"
            )
        return record

    def _resolve_basis(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_module_authority: bool,
    ) -> tuple[JudgmentEvidenceResolution, ...]:
        _require_unique_basis(record)
        return resolve_judgment_evidence_set(
            self.repository,
            work,
            record,
            module_authority=self.module_authority,
            require_module_authority=require_module_authority,
            field_name="basis",
        )

    def _require_current_basis_acceptance(
        self,
        work: ExactPortiaWorkRef,
        resolutions: Sequence[JudgmentEvidenceResolution],
    ) -> None:
        for resolution in resolutions:
            stored = resolution.stored
            if stored is None:
                if resolution.kind == "module_record" and resolution.module_value is None:
                    raise WorkflowPrerequisiteError(
                        "active Classification module basis requires explicit resolution authority"
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
                raise WorkflowOwnershipError("Classification basis record has no logical ID")
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

    def _require_review_semantics(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_current_use: bool,
    ) -> tuple[StoredRecord | None, StoredRecord | None]:
        stage = record.field("stage")
        review = _exact_review(self.repository, work, record)
        reviewed = _exact_reviewed_classification(self.repository, work, record)

        if stage in _REVIEWER_STAGES and review is None:
            raise WorkflowPrerequisiteError(
                "reviewer-stage Classification requires an exact governing Review"
            )
        if stage == "reviewer_confirmed" and reviewed is None:
            raise WorkflowPrerequisiteError(
                "reviewer-confirmed Classification requires an exact reviewed Classification"
            )

        if review is not None:
            if _represented_human_identity(record.field("selector")) != _represented_human_identity(
                review.record.field("reviewer")
            ):
                raise WorkflowPrerequisiteError(
                    "Classification selector must match the governing Review reviewer"
                )
            if record.to_dict().get("target") != review.record.to_dict().get("target"):
                raise WorkflowPrerequisiteError(
                    "Classification target must match the governing Review target"
                )

        if require_current_use and stage in _REVIEWER_STAGES:
            if review is None:
                raise WorkflowPrerequisiteError(
                    "current reviewer Classification requires a governing Review"
                )
            review_id = review.record.logical_id
            if review_id is None:
                raise WorkflowOwnershipError(
                    "governing Review has no logical identity"
                )
            current_review = ReviewWorkflowService(
                self.workspace_root,
                repository=self.repository,
                quarantine=self.quarantine,
                context_assembler=self.contexts,
                module_authority=self.module_authority,
            ).require_current_use(review_reference(work, review_id))
            if current_review.record.field("review_state") != "completed":
                raise WorkflowPrerequisiteError(
                    "active reviewer Classification requires an active completed Review"
                )

        if stage == "reviewer_confirmed" and reviewed is not None:
            if _result_identity(record) != _result_identity(reviewed.record):
                raise WorkflowPrerequisiteError(
                    "reviewer-confirmed Classification result must match the reviewed Classification"
                )
        return review, reviewed

    def _require_activation_candidate(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> None:
        candidate = self._require_write_input(work, record)
        if candidate.field("stage") == "unknown":
            raise WorkflowPrerequisiteError(
                "unknown-stage Classification cannot be activated for current use"
            )
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        require_represented_human_authority(
            self.contexts,
            candidate.field("selector"),
            field_name="Classification selector",
            require_current_use=True,
        )
        review, reviewed = self._require_review_semantics(
            work,
            candidate,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=True,
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
                *((reviewed.record,) if reviewed is not None else ()),
                candidate,
            ),
        )

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> None:
        if not isinstance(record, ClassificationV1):
            raise WorkflowOwnershipError(
                "Classification correction successor must use classification@1"
            )
        require_judgment_record_owner(work, record, contract="classification")
        require_digital_judgment_creation(record)
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "Classification correction successor must be active"
            )
        if record.field("supersedes") is None:
            raise WorkflowPrerequisiteError(
                "Classification correction successor must preserve exact "
                "supersession provenance"
            )
        if record.field("stage") == "unknown":
            raise WorkflowPrerequisiteError(
                "unknown-stage Classification cannot be a current correction successor"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, record)
        require_represented_human_authority(
            self.contexts,
            record.field("selector"),
            field_name="Classification selector",
            require_current_use=True,
        )
        review, reviewed = self._require_review_semantics(
            work,
            record,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            work,
            record,
            require_module_authority=True,
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
                *((reviewed.record,) if reviewed is not None else ()),
                record,
            ),
        )

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        require_represented_human_authority(
            self.contexts,
            candidate.field("selector"),
            field_name="Classification selector",
            require_current_use=candidate.status == "active",
        )
        review, reviewed = self._require_review_semantics(
            work,
            candidate,
            require_current_use=candidate.status == "active",
        )
        basis = self._resolve_basis(
            work,
            candidate,
            require_module_authority=candidate.status == "active",
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
                *((reviewed.record,) if reviewed is not None else ()),
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
        """Create one corrected Classification successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "classification":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Classification"
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
        """Persist one ordinary Classification lifecycle transition."""
        if reference.record_ref.record_kind != "classification":
            raise WorkflowOwnershipError(
                "reference is not a Classification"
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
        classification = self.load_exact(reference)
        require_judgment_lifecycle_reconciled(
            self.repository, reference.work_ref, classification.record
        )
        if classification.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Classification use requires an active canonical Classification"
            )
        require_judgment_current_materialization(classification.record)
        if classification.record.field("stage") == "unknown":
            raise WorkflowPrerequisiteError(
                "unknown-stage Classification is not reviewer-confirmed current authority"
            )
        owner = self.repository.load_work(reference.work_ref)
        require_judgment_owner_current_eligibility(owner.record)
        targets = judgment_target_records(
            self.repository,
            reference.work_ref,
            classification.record,
        )
        require_judgment_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        require_represented_human_authority(
            self.contexts,
            classification.record.field("selector"),
            field_name="Classification selector",
            require_current_use=True,
        )
        review, reviewed = self._require_review_semantics(
            reference.work_ref,
            classification.record,
            require_current_use=True,
        )
        basis = self._resolve_basis(
            reference.work_ref,
            classification.record,
            require_module_authority=True,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, classification.record),
            "block_current_use",
        )
        for resolution in basis:
            if resolution.stored is not None and resolution.kind == "portia_record":
                self.quarantine.require_allowed(
                    record_target(reference.work_ref, resolution.stored.record),
                    "block_current_use",
                )
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                *((reviewed.record,) if reviewed is not None else ()),
                classification.record,
            ),
        )
        return classification

    resolve_current = require_current_use

    def list_classifications(
        self, work: ExactPortiaWorkRef
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)
