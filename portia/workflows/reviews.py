"""Production creation and current-use workflow for Event-local ``review@1``."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from portia.models import PortiaRecord, ReviewV1
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
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
    JUDGMENT_CONTRACTS,
    JUDGMENT_VERSION,
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
from portia.workflows.judgment_lifecycle import require_judgment_lifecycle_reconciled
from portia.workflows.judgment_transition import JudgmentLifecycleCoordinator
from portia.workflows.observations import (
    ObservationWorkflowService,
    observation_reference,
)

_REVIEW_WORKFLOW_ALLOWED = {
    "open": frozenset(
        {"open", "in_review", "awaiting_information", "completed", "cancelled"}
    ),
    "in_review": frozenset(
        {"in_review", "awaiting_information", "completed", "cancelled"}
    ),
    "awaiting_information": frozenset(
        {"awaiting_information", "in_review", "completed", "cancelled"}
    ),
    "completed": frozenset(),
    "cancelled": frozenset(),
}
_REVIEW_WORKFLOW_FIXED_FIELDS = (
    "schema_version",
    "record_type",
    "module_id",
    "class_id",
    "work_id",
    "review_id",
    "status",
    "trigger",
    "question",
    "target",
    "reviewer",
    "requested_by",
    "review_subjects",
    "supersedes",
    "creation_source",
    "created_at",
    "created_by",
)


def _parsed_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"Review {field_name} is not a timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    return datetime.fromisoformat(normalized)


def _canonical_evidence(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _require_review_workflow_revision(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> set[str]:
    """Validate one active Review workflow revision and return appended evidence IDs."""
    if not isinstance(candidate, ReviewV1):
        raise WorkflowOwnershipError("Review workflow updates require review@1 input")
    if (
        prior.contract != "review"
        or prior.contract_version != "1"
        or prior.logical_id != candidate.logical_id
        or prior.class_id != candidate.class_id
        or prior.work_id != candidate.work_id
    ):
        raise WorkflowOwnershipError(
            "Review workflow update must preserve exact canonical Review identity"
        )
    if prior.status != "active" or candidate.status != "active":
        raise WorkflowPrerequisiteError(
            "Review workflow progression keeps canonical lifecycle status active"
        )

    prior_state = prior.field("review_state")
    candidate_state = candidate.field("review_state")
    if not isinstance(prior_state, str) or not isinstance(candidate_state, str):
        raise WorkflowPrerequisiteError("Review workflow state is malformed")
    if candidate_state not in _REVIEW_WORKFLOW_ALLOWED.get(prior_state, frozenset()):
        raise WorkflowPrerequisiteError(
            f"illegal Review workflow transition: {prior_state} -> {candidate_state}"
        )

    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    for field in _REVIEW_WORKFLOW_FIXED_FIELDS:
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                f"active Review workflow cannot rewrite substantive field {field}"
            )

    if _parsed_timestamp(
        candidate_data.get("updated_at"), field_name="updated_at"
    ) <= _parsed_timestamp(prior_data.get("updated_at"), field_name="updated_at"):
        raise WorkflowPrerequisiteError(
            "Review workflow update must strictly advance updated_at"
        )

    prior_evidence = prior_data.get("evidence_considered")
    candidate_evidence = candidate_data.get("evidence_considered")
    if not isinstance(prior_evidence, list) or not isinstance(candidate_evidence, list):
        raise WorkflowOwnershipError("Review evidence_considered is malformed")
    prior_ids = {_canonical_evidence(value) for value in prior_evidence}
    candidate_ids = {_canonical_evidence(value) for value in candidate_evidence}
    if not prior_ids.issubset(candidate_ids):
        raise WorkflowPrerequisiteError(
            "Review workflow update cannot remove or rewrite previously considered evidence"
        )
    return candidate_ids - prior_ids


def review_reference(
    work: ExactPortiaWorkRef,
    review_id: str,
) -> ExactPortiaWorkRecordRef:
    return judgment_reference(work, "review", review_id)


def _review_subject_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    review: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    raw_subjects = review.field("review_subjects")
    if raw_subjects is None:
        subjects: tuple[object, ...] = ()
    elif isinstance(raw_subjects, tuple):
        subjects = raw_subjects
    else:
        raise WorkflowOwnershipError("Review review_subjects is malformed")

    review_id = review.logical_id
    loaded: list[StoredRecord] = []
    seen: set[tuple[str, str]] = set()
    for value in subjects:
        reference = ExactPortiaWorkRecordRef.from_dict(value)
        if reference.work_ref != work:
            raise WorkflowOwnershipError("Review subject must belong to the same Event")
        kind = reference.record_ref.record_kind
        identifier = reference.record_ref.record_id
        version = reference.record_ref.contract_version
        if kind not in JUDGMENT_CONTRACTS or version != JUDGMENT_VERSION:
            raise WorkflowOwnershipError(
                "Review subject must be an exact v1 judgment record"
            )
        if kind == "review" and identifier == review_id:
            raise WorkflowOwnershipError("Review cannot name itself as a subject")
        logical = (kind, identifier)
        if logical in seen:
            raise WorkflowOwnershipError(
                "Review subject repeats the same logical judgment identity"
            )
        seen.add(logical)
        loaded.append(repository.load_work_record(work, kind, version, identifier))

    trigger = review.field("trigger")
    question = review.field("question")
    reconsideration = (
        isinstance(trigger, Mapping) and trigger.get("kind") == "reconsideration"
    ) or (
        isinstance(question, Mapping) and question.get("kind") == "reconsideration"
    )
    if reconsideration and not loaded:
        raise WorkflowPrerequisiteError(
            "reconsideration Review requires an exact judgment subject"
        )
    return tuple(loaded)


class ReviewWorkflowService(JudgmentReadService):
    """Create digital Reviews and qualify exact active Reviews for current use."""

    CONTRACT = "review"

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
    ) -> ReviewV1:
        if not isinstance(record, ReviewV1):
            raise WorkflowOwnershipError("new Review writes require review@1 input")
        require_judgment_record_owner(work, record, contract="review")
        require_digital_judgment_creation(record)
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Review identity must begin proposed or active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "Review correction/supersession requires the later coordinated correction path"
            )
        return record

    def _resolve_evidence(
        self,
        work: ExactPortiaWorkRef,
        review: PortiaRecord,
        *,
        require_module_authority: bool,
    ) -> tuple[JudgmentEvidenceResolution, ...]:
        return resolve_judgment_evidence_set(
            self.repository,
            work,
            review,
            module_authority=self.module_authority,
            require_module_authority=require_module_authority,
        )

    def _require_current_evidence_acceptance(
        self,
        work: ExactPortiaWorkRef,
        resolutions: Sequence[JudgmentEvidenceResolution],
    ) -> None:
        for resolution in resolutions:
            stored = resolution.stored
            if stored is None:
                if resolution.kind == "module_record" and resolution.module_value is None:
                    raise WorkflowPrerequisiteError(
                        "active Review module evidence requires explicit resolution authority"
                    )
                continue
            if resolution.kind == "portia_work":
                self.quarantine.require_allowed(
                    work_target(work), "block_current_use"
                )
                continue
            self.quarantine.require_allowed(
                record_target(work, stored.record), "block_current_use"
            )
            identifier = stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError("judgment evidence record has no logical ID")
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
        subjects = _review_subject_records(self.repository, work, candidate)
        require_represented_human_authority(
            self.contexts,
            candidate.field("reviewer"),
            field_name="Review reviewer",
            require_current_use=True,
        )
        resolutions = self._resolve_evidence(
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
        self._require_current_evidence_acceptance(work, resolutions)
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in subjects),
                candidate,
            ),
        )

    def _require_correction_successor(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> None:
        if not isinstance(record, ReviewV1):
            raise WorkflowOwnershipError(
                "Review correction successor must use review@1"
            )
        require_judgment_record_owner(work, record, contract="review")
        require_digital_judgment_creation(record)
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "Review correction successor must be active"
            )
        if record.field("supersedes") is None:
            raise WorkflowPrerequisiteError(
                "Review correction successor must preserve exact supersession provenance"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, record)
        subjects = _review_subject_records(self.repository, work, record)
        require_represented_human_authority(
            self.contexts,
            record.field("reviewer"),
            field_name="Review reviewer",
            require_current_use=True,
        )
        resolutions = self._resolve_evidence(
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
        self._require_current_evidence_acceptance(work, resolutions)
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in subjects),
                record,
            ),
        )

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        subjects = _review_subject_records(self.repository, work, candidate)
        require_represented_human_authority(
            self.contexts,
            candidate.field("reviewer"),
            field_name="Review reviewer",
            require_current_use=candidate.status == "active",
        )
        resolutions = self._resolve_evidence(
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
            self._require_current_evidence_acceptance(work, resolutions)

        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in subjects),
                candidate,
            ),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def update_workflow(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        """Advance one active Review or append exact evidence under guarded replace."""
        if not isinstance(record, ReviewV1):
            raise WorkflowOwnershipError("Review workflow updates require review@1 input")
        require_judgment_record_owner(work, record, contract="review")
        review_id = record.logical_id
        if review_id is None:
            raise WorkflowOwnershipError("Review workflow update has no logical ID")
        reference = review_reference(work, review_id)
        prior = self.require_current_use(reference)
        appended_ids = _require_review_workflow_revision(prior.record, record)

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, record)
        subjects = _review_subject_records(self.repository, work, record)
        resolutions = self._resolve_evidence(
            work,
            record,
            require_module_authority=True,
        )
        raw_evidence = record.to_dict().get("evidence_considered")
        if not isinstance(raw_evidence, list):
            raise WorkflowOwnershipError("Review evidence_considered is malformed")
        appended_resolutions = tuple(
            resolution
            for value, resolution in zip(raw_evidence, resolutions, strict=True)
            if _canonical_evidence(value) in appended_ids
        )
        self._require_current_evidence_acceptance(work, appended_resolutions)

        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *(item.record for item in subjects),
                record,
            ),
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, record), "block_work_writes"
        )
        return self.repository.replace_work_record(
            work,
            record,
            expected=expected,
        )

    progress = update_workflow

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
        """Create one corrected Review successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "review":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Review"
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
        """Persist one ordinary Review lifecycle transition."""
        if reference.record_ref.record_kind != "review":
            raise WorkflowOwnershipError(
                "reference is not a Review"
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
        review = self.load_exact(reference)
        require_judgment_lifecycle_reconciled(
            self.repository, reference.work_ref, review.record
        )
        if review.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Review use requires an active canonical Review"
            )
        require_judgment_current_materialization(review.record)
        owner = self.repository.load_work(reference.work_ref)
        require_judgment_owner_current_eligibility(owner.record)
        targets = judgment_target_records(
            self.repository,
            reference.work_ref,
            review.record,
        )
        require_judgment_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        require_represented_human_authority(
            self.contexts,
            review.record.field("reviewer"),
            field_name="Review reviewer",
            require_current_use=True,
        )
        subjects = _review_subject_records(
            self.repository,
            reference.work_ref,
            review.record,
        )
        resolutions = self._resolve_evidence(
            reference.work_ref,
            review.record,
            require_module_authority=True,
        )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, review.record), "block_current_use"
        )
        # Historical Portia evidence remains pinned to the exact representation
        # considered; current-use does not silently follow or require successors.
        for resolution in resolutions:
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
                *(item.record for item in subjects),
                review.record,
            ),
        )
        return review

    resolve_current = require_current_use

    def list_reviews(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        return self.list(work)
