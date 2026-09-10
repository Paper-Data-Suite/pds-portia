"""Production Statement of Disagreement creation, resolution, and lifecycle service."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from portia.models import PortiaRecord, StatementOfDisagreementV1
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.action_consolidation import ActionConsolidationCoordinator
from portia.workflows.action_transition import ActionLifecycleCoordinator
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.disagreement_lifecycle import (
    build_disagreement_lifecycle_transition,
    require_disagreement_lifecycle_reconciled,
)
from portia.workflows.disagreement_supersession import (
    disagreement_supersession_ancestry,
    disagreement_supersession_reason_detail,
    require_disagreement_replacement_timing,
    require_disagreement_supersession_effective,
    require_duplicate_disagreement_consolidation_predecessors,
    require_duplicate_disagreement_equivalence,
    require_exact_disagreement_correction_predecessor,
    require_material_disagreement_correction,
    require_no_competing_disagreement_successor,
    superseded_disagreement_predecessor,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

DISAGREEMENT_VERSION = "1"

_CURRENT_WORKS = frozenset({("event", "2"), ("support_process", "1")})
_HUMAN_MEANINGFUL_RECORDS = frozenset(
    {
        ("event_participant", "1"),
        ("event_participant", "2"),
        ("event_participant", "3"),
        ("event_participant_role", "1"),
        ("event_participant_role", "2"),
        ("event_participant_role", "3"),
        ("work_relationship", "1"),
        ("work_relationship", "2"),
        ("account", "1"),
        ("account", "2"),
        ("observation", "1"),
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


def disagreement_reference(
    work: ExactPortiaWorkRef,
    disagreement_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact same-work ``statement_of_disagreement@1`` reference."""
    _require_current_work(work)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="statement_of_disagreement",
            record_id=disagreement_id,
            contract_version=DISAGREEMENT_VERSION,
        ),
    )


def _require_current_work(work: ExactPortiaWorkRef) -> None:
    if (work.work_kind, work.contract_version) not in _CURRENT_WORKS:
        raise WorkflowOwnershipError(
            "Statement of Disagreement workflows require exact event@2 or support_process@1 ownership"
        )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Statement of Disagreement {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Statement of Disagreement {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"Statement of Disagreement {field_name} timestamp lacks an explicit offset"
        )
    return parsed


class StatementOfDisagreementWorkflowService(WorkflowServiceBase):
    """Preserve one represented human source's position without adjudicating target truth."""

    def _require_write_input(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StatementOfDisagreementV1:
        _require_current_work(work)
        self.repository.load_work(work)
        if not isinstance(record, StatementOfDisagreementV1):
            raise WorkflowOwnershipError(
                "Statement of Disagreement writes require statement_of_disagreement@1 input"
            )
        if record.class_id != work.class_id or record.work_id != work.work_id:
            raise WorkflowOwnershipError(
                "Statement of Disagreement does not belong to selected Portia work"
            )
        return record

    def _resolve_target(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        target = record.field("target")
        if not isinstance(target, Mapping):
            raise WorkflowOwnershipError("Statement of Disagreement target is malformed")
        kind = target.get("kind")
        if kind == "work":
            target_kind = target.get("work_kind")
            target_version = target.get("contract_version")
            if (target_kind, target_version) != (work.work_kind, work.contract_version):
                raise WorkflowOwnershipError(
                    "Statement of Disagreement work target must name the exact containing work"
                )
            return self.repository.load_work(work)
        if kind != "local_record":
            raise WorkflowOwnershipError(
                "Statement of Disagreement target must be exact work or local record"
            )
        local = target.get("record_ref")
        if not isinstance(local, Mapping):
            raise WorkflowOwnershipError(
                "Statement of Disagreement local target is malformed"
            )
        record_kind = local.get("record_kind")
        record_id = local.get("record_id")
        version = local.get("contract_version")
        if not all(isinstance(value, str) for value in (record_kind, record_id, version)):
            raise WorkflowOwnershipError(
                "Statement of Disagreement local target is not exact"
            )
        key = (str(record_kind), str(version))
        if key not in _HUMAN_MEANINGFUL_RECORDS:
            raise WorkflowOwnershipError(
                "Statement of Disagreement target is not an allowed human-meaningful domain record"
            )
        resolved = self.repository.load_work_record(
            work,
            str(record_kind),
            str(version),
            str(record_id),
        )
        if (
            resolved.record.contract != record_kind
            or resolved.record.contract_version != version
            or resolved.record.logical_id != record_id
        ):
            raise WorkflowOwnershipError(
                "Statement of Disagreement exact target does not match resolved canonical record"
            )
        return resolved

    def _require_source_resolution(self, candidate: PortiaRecord) -> None:
        source = candidate.field("source")
        if not isinstance(source, Mapping):
            raise WorkflowOwnershipError("Statement of Disagreement source is malformed")
        kind = source.get("kind")
        if kind == "roster_student":
            roster_ref = source.get("roster_student_ref")
            if not isinstance(roster_ref, Mapping) or roster_ref.get("class_id") != candidate.class_id:
                raise WorkflowOwnershipError(
                    "Statement of Disagreement roster source must belong to the owning class"
                )
        elif kind == "actor":
            actor_ref = source.get("actor_ref")
            if not isinstance(actor_ref, Mapping) or not isinstance(actor_ref.get("actor_id"), str):
                raise WorkflowOwnershipError(
                    "Statement of Disagreement Actor source is malformed"
                )
        elif kind not in {"local_operator", "descriptive_person"}:
            raise WorkflowOwnershipError(
                "Statement of Disagreement represented source kind is unsupported"
            )
        # The context assembler is the existing authority for resolvable roster/Actor
        # identities. Current-use is deliberately not required: the source attribution
        # is historical and must survive later identity-directory lifecycle changes.
        self.contexts.assemble((candidate,), require_actor_current_use=False)

    @staticmethod
    def _require_creation_semantics(candidate: PortiaRecord) -> None:
        source = candidate.field("creation_source")
        source_type = source.get("type") if isinstance(source, Mapping) else None
        if source_type == "digital_entry":
            if candidate.status not in {"proposed", "active"}:
                raise WorkflowPrerequisiteError(
                    "new digital Statement of Disagreement must begin proposed or active"
                )
        elif source_type in {"paper_capture", "import"}:
            if candidate.status != "proposed":
                raise WorkflowPrerequisiteError(
                    "paper/import Statement of Disagreement must begin proposed"
                )
        else:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement creation source is unsupported"
            )
        if candidate.field("supersedes") is not None:
            raise WorkflowPrerequisiteError(
                "fresh Statement of Disagreement creation cannot establish supersession history"
            )
        created = _parse_timestamp(candidate.field("created_at"), field_name="created_at")
        updated = _parse_timestamp(candidate.field("updated_at"), field_name="updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement updated_at cannot precede created_at"
            )

    @staticmethod
    def _require_replacement_creation_semantics(candidate: PortiaRecord) -> None:
        source = candidate.field("creation_source")
        source_type = source.get("type") if isinstance(source, Mapping) else None
        if source_type != "digital_entry":
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement correction/consolidation successor requires digital_entry review"
            )
        if candidate.status not in {"active", "withdrawn", "invalidated"}:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement replacement successor must begin active, withdrawn, or invalidated"
            )
        if candidate.field("supersedes") is None:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement replacement successor requires supersession history"
            )
        created = _parse_timestamp(candidate.field("created_at"), field_name="created_at")
        updated = _parse_timestamp(candidate.field("updated_at"), field_name="updated_at")
        if updated < created:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement successor updated_at cannot precede created_at"
            )

    def create(
        self,
        work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> StoredRecord:
        """Persist one exact disagreement without mutating or adjudicating its target."""
        candidate = self._require_write_input(work, record)
        self._require_creation_semantics(candidate)
        self._resolve_target(work, candidate)
        self._require_source_resolution(candidate)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate),
            "block_work_writes",
        )
        if candidate.status == "active":
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, candidate),
                "block_current_use",
            )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        _require_current_work(reference.work_ref)
        if (
            reference.record_ref.record_kind != "statement_of_disagreement"
            or reference.record_ref.contract_version != DISAGREEMENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Statement of Disagreement exact read requires statement_of_disagreement@1 reference"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "statement_of_disagreement",
            DISAGREEMENT_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        _require_current_work(work)
        self.repository.load_work(work)
        return self.repository.list_work_records(
            work,
            "statement_of_disagreement",
            version=DISAGREEMENT_VERSION,
        )

    list_disagreements = list

    def _require_transition_candidate(
        self,
        work: ExactPortiaWorkRef,
        prior: PortiaRecord,
        candidate: PortiaRecord,
    ) -> None:
        self._require_write_input(work, prior)
        self._require_write_input(work, candidate)
        self._resolve_target(work, candidate)
        self._require_source_resolution(candidate)

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
        """Persist activation, actual source withdrawal, or invalidation."""
        if (
            reference.record_ref.record_kind != "statement_of_disagreement"
            or reference.record_ref.contract_version != DISAGREEMENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Statement of Disagreement lifecycle requires exact statement_of_disagreement@1 reference"
            )
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
            transition_factory=lambda prior, value: build_disagreement_lifecycle_transition(
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
        require_disagreement_lifecycle_reconciled(
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
        effective_at: str | None,
    ) -> None:
        self._require_write_input(work, prior)
        value = self._require_write_input(work, successor)
        self._require_replacement_creation_semantics(value)
        require_disagreement_lifecycle_reconciled(self.repository, work, prior)
        require_material_disagreement_correction(
            prior,
            value,
            supersession_reason,
        )
        predecessor_id = prior.logical_id
        if not isinstance(predecessor_id, str):
            raise WorkflowOwnershipError(
                "Statement of Disagreement predecessor has no canonical identity"
            )
        require_no_competing_disagreement_successor(
            self.repository,
            work,
            (disagreement_reference(work, predecessor_id),),
        )
        require_disagreement_replacement_timing(
            self.repository,
            work,
            (prior,),
            value,
            effective_at=effective_at,
        )
        self._resolve_target(work, value)
        self._require_source_resolution(value)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, value), "block_work_writes")
        if value.status == "active":
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
            )

    def _require_consolidation_successor(
        self,
        work: ExactPortiaWorkRef,
        priors: tuple[PortiaRecord, ...],
        successor: PortiaRecord,
        *,
        reason_detail: str,
        effective_at: str | None,
    ) -> None:
        value = self._require_write_input(work, successor)
        self._require_replacement_creation_semantics(value)
        for prior in priors:
            self._require_write_input(work, prior)
            require_disagreement_lifecycle_reconciled(self.repository, work, prior)
        require_duplicate_disagreement_equivalence(
            priors,
            value,
            reason_detail=reason_detail,
        )
        predecessor_references = tuple(
            disagreement_reference(work, identifier)
            for identifier in (prior.logical_id for prior in priors)
            if isinstance(identifier, str)
        )
        if len(predecessor_references) != len(priors):
            raise WorkflowOwnershipError(
                "Statement of Disagreement consolidation predecessor lacks canonical identity"
            )
        require_no_competing_disagreement_successor(
            self.repository,
            work,
            predecessor_references,
        )
        require_disagreement_replacement_timing(
            self.repository,
            work,
            priors,
            value,
            effective_at=effective_at,
        )
        self._resolve_target(work, value)
        self._require_source_resolution(value)
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(record_target(work, value), "block_work_writes")
        if value.status == "active":
            self.quarantine.require_allowed(work_target(work), "block_current_use")
            self.quarantine.require_allowed(
                record_target(work, value),
                "block_current_use",
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
        """Create one reviewed material successor and supersede its exact predecessor."""
        if (
            predecessor.record_ref.record_kind != "statement_of_disagreement"
            or predecessor.record_ref.contract_version != DISAGREEMENT_VERSION
        ):
            raise WorkflowOwnershipError(
                "Statement of Disagreement correction requires exact statement_of_disagreement@1 predecessor"
            )
        work = predecessor.work_ref
        supersession_reason = require_exact_disagreement_correction_predecessor(
            work,
            predecessor,
            successor,
        )
        reason_detail = disagreement_supersession_reason_detail(successor)
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
                effective_at=effective_at,
            ),
            predecessor_factory=superseded_disagreement_predecessor,
            transition_factory=lambda prior, value: build_disagreement_lifecycle_transition(
                self.repository,
                work,
                prior,
                value,
                transition_id=transition_id,
                reason_code=supersession_reason,
                reason_detail=reason_detail,
                effective_at=effective_at,
                allow_supersession=True,
            ),
        )
        accepted_predecessor = self.load_exact(predecessor)
        require_disagreement_lifecycle_reconciled(
            self.repository,
            work,
            accepted_predecessor.record,
        )
        successor_id = successor.logical_id
        if not isinstance(successor_id, str):
            raise WorkflowOwnershipError(
                "Statement of Disagreement successor has no canonical identity"
            )
        accepted_successor = self.load_exact(disagreement_reference(work, successor_id))
        lineage = disagreement_supersession_ancestry(
            self.repository,
            work,
            accepted_successor.record,
        )
        require_disagreement_supersession_effective(lineage)
        return result

    def consolidate_duplicates(
        self,
        work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: Mapping[str, ContentFingerprint],
        transition_ids: Mapping[str, str],
        reason_detail: str,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Create one reviewed successor for duplicate captures of one source statement."""
        _require_current_work(work)
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement duplicate consolidation requires review detail"
            )
        predecessors = require_duplicate_disagreement_consolidation_predecessors(
            work,
            successor,
        )
        predecessor_ids = tuple(
            reference.record_ref.record_id for reference in predecessors
        )
        if set(expected) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement consolidation requires one expected fingerprint for every predecessor"
            )
        if set(transition_ids) != set(predecessor_ids):
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement consolidation requires one lifecycle transition ID for every predecessor"
            )
        ordered_transition_ids = tuple(
            transition_ids[identifier] for identifier in predecessor_ids
        )
        if len(set(ordered_transition_ids)) != len(ordered_transition_ids):
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement consolidation lifecycle transition IDs must be unique"
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
                reason_detail=reason_detail,
                effective_at=effective_at,
            )

        def build_transition(
            prior: PortiaRecord,
            candidate: PortiaRecord,
            selected_transition_id: str,
        ) -> PortiaRecord:
            return build_disagreement_lifecycle_transition(
                self.repository,
                work,
                prior,
                candidate,
                transition_id=selected_transition_id,
                reason_code="duplicate_consolidated",
                reason_detail=reason_detail,
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
            predecessor_factory=superseded_disagreement_predecessor,
            transition_factory=build_transition,
        )
        for predecessor in predecessors:
            accepted = self.load_exact(predecessor)
            require_disagreement_lifecycle_reconciled(
                self.repository,
                work,
                accepted.record,
            )
        successor_id = successor.logical_id
        if not isinstance(successor_id, str):
            raise WorkflowOwnershipError(
                "Statement of Disagreement successor has no canonical identity"
            )
        accepted_successor = self.load_exact(disagreement_reference(work, successor_id))
        lineage = disagreement_supersession_ancestry(
            self.repository,
            work,
            accepted_successor.record,
        )
        require_disagreement_supersession_effective(lineage)
        return result

    def require_current_use(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Require one exact active disagreement without following target successors."""
        disagreement = self.load_exact(reference)
        require_disagreement_lifecycle_reconciled(
            self.repository,
            reference.work_ref,
            disagreement.record,
        )
        predecessors = disagreement_supersession_ancestry(
            self.repository,
            reference.work_ref,
            disagreement.record,
        )
        require_disagreement_supersession_effective(predecessors)
        for predecessor in predecessors:
            require_disagreement_lifecycle_reconciled(
                self.repository,
                predecessor.work_ref,
                predecessor.stored.record,
            )
            self.quarantine.require_allowed(
                record_target(predecessor.work_ref, predecessor.stored.record),
                "block_current_use",
            )
        if disagreement.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Statement of Disagreement use requires active canonical status"
            )
        self._resolve_target(reference.work_ref, disagreement.record)
        self._require_source_resolution(disagreement.record)
        self.quarantine.require_allowed(
            work_target(reference.work_ref),
            "block_current_use",
        )
        self.quarantine.require_allowed(
            record_target(reference.work_ref, disagreement.record),
            "block_current_use",
        )
        return disagreement

    resolve_current = require_current_use
