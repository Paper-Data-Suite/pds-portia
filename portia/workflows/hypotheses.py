"""Production creation and current-use workflow for Event-local ``hypothesis@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from portia.models import HypothesisV1, PortiaRecord
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


def hypothesis_reference(
    work: ExactPortiaWorkRef,
    hypothesis_id: str,
) -> ExactPortiaWorkRecordRef:
    return judgment_reference(work, "hypothesis", hypothesis_id)


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
        raise WorkflowOwnershipError("Hypothesis Review must belong to the same Event")
    if (
        reference.record_ref.record_kind != "review"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError("Hypothesis review_ref must name exact review@1")
    return repository.load_work_record(
        work,
        "review",
        "1",
        reference.record_ref.record_id,
    )


def _evidence_identity(value: object) -> tuple[object, ...]:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError("Hypothesis evidence reference is malformed")
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
    raise WorkflowOwnershipError(f"unsupported Hypothesis evidence kind {kind!r}")


def _timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowOwnershipError(f"Hypothesis {field_name} timestamp is malformed")
    return datetime.fromisoformat(value)


def _require_set_aside_revision(
    previous: PortiaRecord,
    current: PortiaRecord,
) -> None:
    if previous.status != "active" or current.status != "active":
        raise WorkflowPrerequisiteError(
            "Hypothesis set-aside workflow requires active lifecycle status"
        )
    if previous.field("consideration_state") != "under_consideration":
        raise WorkflowPrerequisiteError(
            "only an under-consideration Hypothesis may be set aside"
        )
    if current.field("consideration_state") != "set_aside":
        raise WorkflowPrerequisiteError(
            "Hypothesis workflow update may only move to set_aside"
        )

    before = previous.to_dict()
    after = current.to_dict()
    for field_name in ("consideration_state", "updated_at", "updated_by"):
        before.pop(field_name, None)
        after.pop(field_name, None)
    if before != after:
        raise WorkflowPrerequisiteError(
            "setting aside a Hypothesis cannot rewrite substantive fields"
        )

    if _timestamp(
        current.field("updated_at"), field_name="updated_at"
    ) <= _timestamp(previous.field("updated_at"), field_name="updated_at"):
        raise WorkflowPrerequisiteError(
            "Hypothesis set-aside update must advance updated_at"
        )


def _evidence_values(record: PortiaRecord) -> tuple[object, ...]:
    entries = record.field("evidence")
    if not isinstance(entries, tuple):
        raise WorkflowOwnershipError("Hypothesis evidence is malformed")
    values: list[object] = []
    identities: list[tuple[object, ...]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowOwnershipError("Hypothesis evidence entry is malformed")
        evidence_ref = entry.get("evidence_ref")
        identity = _evidence_identity(evidence_ref)
        values.append(evidence_ref)
        identities.append(identity)
    if len(identities) != len(set(identities)):
        raise WorkflowOwnershipError(
            "Hypothesis evidence repeats the same logical evidence identity"
        )
    return tuple(values)


class HypothesisWorkflowService(JudgmentReadService):
    """Create and qualify explicitly tentative human Hypotheses."""

    CONTRACT = "hypothesis"

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
    ) -> HypothesisV1:
        if not isinstance(record, HypothesisV1):
            raise WorkflowOwnershipError(
                "new Hypothesis writes require hypothesis@1 input"
            )
        require_judgment_record_owner(work, record, contract="hypothesis")
        require_digital_judgment_creation(record)
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Hypothesis identity must begin proposed or active"
            )
        if record.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "Hypothesis refinement/correction requires the later coordinated "
                "successor path"
            )
        return record

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
                "Hypothesis target must match the governing Review target"
            )
        if require_current_use:
            review_id = review.record.logical_id
            if review_id is None:
                raise WorkflowOwnershipError("governing Review has no logical identity")
            return ReviewWorkflowService(
                self.workspace_root,
                repository=self.repository,
                quarantine=self.quarantine,
                context_assembler=self.contexts,
                module_authority=self.module_authority,
            ).require_current_use(review_reference(work, review_id))
        return review

    def _resolve_evidence(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        require_module_authority: bool,
    ) -> tuple[JudgmentEvidenceResolution, ...]:
        resolved: list[JudgmentEvidenceResolution] = []
        for value in _evidence_values(record):
            if not isinstance(value, Mapping):
                raise WorkflowOwnershipError(
                    "Hypothesis evidence reference is malformed"
                )
            kind = value.get("kind")
            if kind == "portia_work":
                work_reference = ExactPortiaWorkRef.from_dict(value.get("work_ref"))
                if work_reference != work:
                    raise WorkflowOwnershipError(
                        "Event-local Hypothesis evidence cannot resolve another "
                        "Portia work"
                    )
            elif kind == "portia_record":
                record_reference = ExactPortiaWorkRecordRef.from_dict(
                    value.get("work_record_ref")
                )
                if record_reference.work_ref != work:
                    raise WorkflowOwnershipError(
                        "Event-local Hypothesis evidence cannot resolve another "
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

    def _require_current_evidence_acceptance(
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
                        "active Hypothesis module evidence requires explicit "
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
                    "Hypothesis evidence record has no logical ID"
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
        if candidate.field("consideration_state") != "under_consideration":
            raise WorkflowPrerequisiteError(
                "only an under-consideration Hypothesis can be activated"
            )
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, candidate)
        require_represented_human_authority(
            self.contexts,
            candidate.field("author"),
            field_name="Hypothesis author",
            require_current_use=True,
        )
        review = self._resolve_review(
            work,
            candidate,
            require_current_use=True,
        )
        evidence = self._resolve_evidence(
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
        self._require_current_evidence_acceptance(work, evidence)
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
        if not isinstance(record, HypothesisV1):
            raise WorkflowOwnershipError(
                "Hypothesis correction successor must use hypothesis@1"
            )
        require_judgment_record_owner(work, record, contract="hypothesis")
        require_digital_judgment_creation(record)
        if record.status != "active":
            raise WorkflowPrerequisiteError(
                "Hypothesis correction successor must be active"
            )
        if record.field("supersedes") is None:
            raise WorkflowPrerequisiteError(
                "Hypothesis correction successor must preserve exact "
                "supersession provenance"
            )
        if record.field("consideration_state") != "under_consideration":
            raise WorkflowPrerequisiteError(
                "Hypothesis correction successor must remain under consideration"
            )

        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        targets = judgment_target_records(self.repository, work, record)
        require_represented_human_authority(
            self.contexts,
            record.field("author"),
            field_name="Hypothesis author",
            require_current_use=True,
        )
        review = self._resolve_review(
            work,
            record,
            require_current_use=True,
        )
        evidence = self._resolve_evidence(
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
        self._require_current_evidence_acceptance(work, evidence)
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
        require_represented_human_authority(
            self.contexts,
            candidate.field("author"),
            field_name="Hypothesis author",
            require_current_use=candidate.status == "active",
        )
        review = self._resolve_review(
            work,
            candidate,
            require_current_use=candidate.status == "active",
        )
        evidence = self._resolve_evidence(
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
            self._require_current_evidence_acceptance(work, evidence)

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

    def set_aside(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
        *,
        expected: ContentFingerprint,
    ) -> StoredRecord:
        if not isinstance(record, HypothesisV1):
            raise WorkflowOwnershipError(
                "Hypothesis set-aside workflow requires hypothesis@1 input"
            )
        require_judgment_record_owner(work, record, contract="hypothesis")
        if record.logical_id is None:
            raise WorkflowOwnershipError("Hypothesis has no logical identity")
        prior = self.repository.load_work_record(
            work,
            "hypothesis",
            "1",
            record.logical_id,
        )
        _require_set_aside_revision(prior.record, record)
        owner = self.repository.load_work(work)
        require_judgment_owner_write_eligibility(owner.record)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, record), "block_work_writes"
        )
        validate_partial_judgment_graph(
            self.contexts,
            (owner.record, record),
        )
        return self.repository.replace_work_record(
            work,
            record,
            expected=expected,
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
        """Create one corrected Hypothesis successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "hypothesis":
            raise WorkflowOwnershipError(
                "correction predecessor is not a Hypothesis"
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
        """Persist one ordinary Hypothesis lifecycle transition."""
        if reference.record_ref.record_kind != "hypothesis":
            raise WorkflowOwnershipError(
                "reference is not a Hypothesis"
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
        hypothesis = self.load_exact(reference)
        require_judgment_lifecycle_reconciled(
            self.repository, reference.work_ref, hypothesis.record
        )
        if hypothesis.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Hypothesis use requires an active canonical Hypothesis"
            )
        require_judgment_current_materialization(hypothesis.record)
        if hypothesis.record.field("consideration_state") != "under_consideration":
            raise WorkflowPrerequisiteError(
                "current Hypothesis use requires an under-consideration Hypothesis"
            )
        owner = self.repository.load_work(reference.work_ref)
        require_judgment_owner_current_eligibility(owner.record)
        targets = judgment_target_records(
            self.repository,
            reference.work_ref,
            hypothesis.record,
        )
        require_judgment_targets_current_use(
            reference.work_ref,
            targets,
            quarantine=self.quarantine,
        )
        require_represented_human_authority(
            self.contexts,
            hypothesis.record.field("author"),
            field_name="Hypothesis author",
            require_current_use=True,
        )
        review = self._resolve_review(
            reference.work_ref,
            hypothesis.record,
            require_current_use=True,
        )
        evidence = self._resolve_evidence(
            reference.work_ref,
            hypothesis.record,
            require_module_authority=True,
        )
        # Evidence already accepted into this exact Hypothesis remains historical
        # evidence. Later Account/Observation lifecycle changes do not silently
        # rewrite or disqualify that accepted reference; Quarantine can still
        # block consequential use of the exact representation.
        for resolution in evidence:
            if resolution.stored is not None and resolution.kind == "portia_record":
                self.quarantine.require_allowed(
                    record_target(reference.work_ref, resolution.stored.record),
                    "block_current_use",
                )
        self.quarantine.require_allowed(
            work_target(reference.work_ref), "block_current_use"
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, hypothesis.record),
            "block_current_use",
        )
        validate_partial_judgment_graph(
            self.contexts,
            (
                owner.record,
                *(item.record for item in targets),
                *((review.record,) if review is not None else ()),
                hypothesis.record,
            ),
        )
        return hypothesis

    resolve_current = require_current_use

    def list_hypotheses(
        self, work: ExactPortiaWorkRef
    ) -> tuple[StoredRecord, ...]:
        return self.list(work)
