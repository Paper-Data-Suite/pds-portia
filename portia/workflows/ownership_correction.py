"""Public bounded ownership-correction workflow for supported child families."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Protocol, cast

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
)
from portia.storage.io import read_json
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import workspace_relative
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows.action_reownership import OwnershipCorrectionEvidence
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.dependencies import (
    DependencyConditionEvaluation,
    DependencyWorkflowService,
    dependency_reference,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.exceptional_removal import (
    _canonical_candidates,
    _contains_exact,
    _require_no_active_operation_conflict,
    _target_reference_needles,
)
from portia.workflows.fidelity import FidelityWorkflowService
from portia.workflows.follow_ups import FollowUpWorkflowService
from portia.workflows.implementations import ImplementationWorkflowService
from portia.workflows.integrity import IntegrityGuard
from portia.workflows.outcomes import OutcomeWorkflowService
from portia.workflows.reentries import ReentryWorkflowService
from portia.workflows.repairs import RepairWorkflowService

_REFERENCE_DISPOSITIONS = frozenset(
    {
        "remain_exact_historical",
        "requires_referrer_correction",
        "blocks_destination_current_use",
        "review_required",
        "authorization_limited",
        "unsupported",
    }
)
_BLOCKING_REFERENCE_DISPOSITIONS = frozenset(
    {
        "blocks_destination_current_use",
        "review_required",
        "authorization_limited",
        "unsupported",
    }
)
_DEPENDENCY_DISPOSITIONS = frozenset(
    {
        "satisfied_by_destination",
        "remains_historical_to_source",
        "requires_correction",
        "blocks_completion",
        "review_required",
        "unsupported",
    }
)
_BLOCKING_DEPENDENCY_DISPOSITIONS = frozenset(
    {"requires_correction", "blocks_completion", "review_required", "unsupported"}
)
_WORK_VERSIONS = {"event": "2", "support_process": "1"}
_MAX_DISPOSITION_ENTRIES = 29


class _FamilyService(Protocol):
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
        _ownership_evidence: OwnershipCorrectionEvidence | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult: ...


@dataclass(frozen=True, slots=True)
class OwnershipFamilyRegistration:
    """Public read-only description of one closed supported family binding."""

    contract: str
    contract_version: str
    supported_work_kind_pairs: frozenset[tuple[str, str]]
    workflow_service: Callable[..., _FamilyService]


@dataclass(frozen=True, slots=True)
class IncomingReferenceReview:
    """Privacy-minimal identity for one canonical incoming reference."""

    reference_key: str
    workspace_relative_path: str


@dataclass(frozen=True, slots=True)
class DependencyReview:
    """One relevant Dependency and its accepted evaluator outcome."""

    dependency_key: str
    reference: ExactPortiaWorkRecordRef
    strength: str
    condition: str
    reason: str


@dataclass(frozen=True, slots=True)
class OwnershipCorrectionAssessment:
    """Side-effect-free complete preflight inventory for one exact correction."""

    source: ExactPortiaWorkRecordRef
    destination: ExactPortiaWorkRecordRef
    source_fingerprint: ContentFingerprint
    incoming_references: tuple[IncomingReferenceReview, ...]
    dependencies: tuple[DependencyReview, ...]


@dataclass(frozen=True, slots=True)
class OwnershipCorrectionResult:
    """Bounded accepted result without payload bodies or mutable plans."""

    operation_id: str
    source: ExactPortiaWorkRecordRef
    destination: ExactPortiaWorkRecordRef
    ownership_correction: ExactPortiaWorkRecordRef
    status: str
    incoming_reference_count: int
    dependency_count: int
    recovery_required: bool


def _all_pairs() -> frozenset[tuple[str, str]]:
    return frozenset(
        (source, destination)
        for source in _WORK_VERSIONS
        for destination in _WORK_VERSIONS
    )


_FAMILY_REGISTRY: Mapping[str, OwnershipFamilyRegistration] = MappingProxyType(
    {
        "fidelity": OwnershipFamilyRegistration(
            "fidelity",
            "1",
            frozenset({("support_process", "support_process")}),
            FidelityWorkflowService,
        ),
        "implementation": OwnershipFamilyRegistration(
            "implementation",
            "1",
            frozenset({("support_process", "support_process")}),
            ImplementationWorkflowService,
        ),
        "follow_up": OwnershipFamilyRegistration(
            "follow_up", "1", _all_pairs(), FollowUpWorkflowService
        ),
        "outcome": OwnershipFamilyRegistration(
            "outcome", "1", _all_pairs(), OutcomeWorkflowService
        ),
        "reentry": OwnershipFamilyRegistration(
            "reentry", "1", _all_pairs(), ReentryWorkflowService
        ),
        "repair": OwnershipFamilyRegistration(
            "repair", "1", _all_pairs(), RepairWorkflowService
        ),
    }
)


def supported_ownership_correction_families() -> Mapping[
    str, OwnershipFamilyRegistration
]:
    """Return the immutable closed public family registry."""

    return _FAMILY_REGISTRY


def _evidence_key(prefix: str, value: object) -> str:
    digest = hashlib.sha256(canonical_json_bytes(value)).hexdigest()
    return f"{prefix}_{digest}"


def _record_reference(
    work: ExactPortiaWorkRef, record: PortiaRecord
) -> ExactPortiaWorkRecordRef:
    identifier = record.logical_id
    if identifier is None:
        raise WorkflowOwnershipError("ownership destination has no exact identity")
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=record.contract,
            record_id=identifier,
            contract_version=record.contract_version,
        ),
    )


class OwnershipCorrectionWorkflowService:
    """Correct ownership only for the six accepted child-record families."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
        integrity_guard: IntegrityGuard | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.contexts = context_assembler or WorkflowContextAssembler(
            self.workspace_root
        )
        self.integrity = integrity_guard or IntegrityGuard(
            self.workspace_root,
            quarantine=quarantine,
        )
        self._dependencies = DependencyWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.integrity,
            context_assembler=self.contexts,
        )

    def _fault_hook(self, phase: str, step_id: str | None) -> None:
        """Internal deterministic seam used by recovery acceptance tests."""

    @staticmethod
    def _registration(
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
    ) -> OwnershipFamilyRegistration:
        contract = predecessor.record_ref.record_kind
        registration = _FAMILY_REGISTRY.get(contract)
        if registration is None:
            raise WorkflowOwnershipError(
                f"unsupported ownership-correction family {contract!r}"
            )
        if predecessor.record_ref.contract_version != registration.contract_version:
            raise WorkflowOwnershipError(
                "unsupported ownership-correction contract version"
            )
        source_work = predecessor.work_ref
        if (
            source_work.work_kind,
            source_work.contract_version,
        ) not in {(kind, version) for kind, version in _WORK_VERSIONS.items()}:
            raise WorkflowOwnershipError(
                "source work is not an exact current work root"
            )
        if (
            destination_work.work_kind,
            destination_work.contract_version,
        ) not in {(kind, version) for kind, version in _WORK_VERSIONS.items()}:
            raise WorkflowOwnershipError(
                "destination work is not an exact current work root"
            )
        pair = (source_work.work_kind, destination_work.work_kind)
        if pair not in registration.supported_work_kind_pairs:
            raise WorkflowOwnershipError(
                f"unsupported {contract} ownership work-kind pair {pair!r}"
            )
        if source_work == destination_work:
            raise WorkflowOwnershipError(
                "ownership correction requires distinct exact work roots"
            )
        return registration

    def _workspace_works(self) -> tuple[ExactPortiaWorkRef, ...]:
        works: list[ExactPortiaWorkRef] = []
        for path in _canonical_candidates(self.workspace_root):
            if path.name != "work.json":
                continue
            value, _content, _fingerprint = read_json(path)
            if not isinstance(value, Mapping):
                raise WorkflowOwnershipError("canonical work inventory is malformed")
            try:
                work = ExactPortiaWorkRef(
                    module_id="portia",
                    class_id=cast(str, value["class_id"]),
                    work_id=cast(str, value["work_id"]),
                    work_kind=cast(str, value["work_kind"]),
                    contract_version=cast(str, value["schema_version"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise WorkflowOwnershipError(
                    "canonical work inventory contains an inexact work"
                ) from exc
            if (work.work_kind, work.contract_version) not in {
                (kind, version) for kind, version in _WORK_VERSIONS.items()
            }:
                raise WorkflowOwnershipError(
                    "canonical work inventory contains an unsupported current root"
                )
            works.append(work)
        return tuple(works)

    def _incoming_references(
        self,
        source: ExactPortiaWorkRecordRef,
        source_path: Path,
    ) -> tuple[IncomingReferenceReview, ...]:
        target = {"kind": "work_record", "work_record_ref": source.to_dict()}
        needles = _target_reference_needles(target)
        found: list[IncomingReferenceReview] = []
        for path in _canonical_candidates(self.workspace_root):
            if path == source_path:
                continue
            value, _content, _fingerprint = read_json(path)
            if any(
                needle is not None and _contains_exact(value, needle)
                for needle in needles
            ):
                relative = workspace_relative(self.workspace_root, path)
                found.append(
                    IncomingReferenceReview(
                        _evidence_key("ref", relative),
                        relative,
                    )
                )
        return tuple(sorted(found, key=lambda item: item.workspace_relative_path))

    def _dependency_reviews(
        self,
        source: ExactPortiaWorkRecordRef,
        *,
        effective_at: str,
    ) -> tuple[DependencyReview, ...]:
        works = self._workspace_works()
        candidates = {
            item.path: item
            for item in (
                *self._dependencies.list_for_dependent(source),
                *self._dependencies.list_incoming(works, source),
            )
        }
        owners = {(work.class_id, work.work_id): work for work in works}
        reviews: list[DependencyReview] = []
        for stored in sorted(candidates.values(), key=lambda item: str(item.path)):
            record = stored.record
            identifier = record.logical_id
            class_id = record.class_id
            work_id = record.work_id
            if identifier is None or class_id is None or work_id is None:
                raise WorkflowOwnershipError(
                    "relevant Dependency lacks exact canonical ownership"
                )
            owner = owners.get((class_id, work_id))
            if owner is None:
                raise WorkflowOwnershipError(
                    "relevant Dependency owner is absent from the complete work inventory"
                )
            reference = dependency_reference(owner, identifier)
            evaluation: DependencyConditionEvaluation = (
                self._dependencies.evaluate_condition(
                    reference,
                    gate="current_use",
                    evaluated_at=effective_at,
                )
            )
            reviews.append(
                DependencyReview(
                    _evidence_key("dep", reference.to_dict()),
                    reference,
                    evaluation.strength,
                    evaluation.condition,
                    evaluation.reason,
                )
            )
        return tuple(reviews)

    def assess_correction(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        effective_at: str,
    ) -> OwnershipCorrectionAssessment:
        """Establish the complete exact preflight without canonical mutation."""
        self._registration(predecessor, destination_work)
        source = self.repository.load_work_record(
            predecessor.work_ref,
            predecessor.record_ref.record_kind,
            predecessor.record_ref.contract_version,
            predecessor.record_ref.record_id,
        )
        if source.fingerprint != expected:
            raise PortiaConflictError(
                "expected source fingerprint does not match canonical bytes"
            )
        self.repository.load_work(destination_work)
        destination = _record_reference(destination_work, successor)
        if (
            successor.contract != predecessor.record_ref.record_kind
            or successor.contract_version != predecessor.record_ref.contract_version
            or successor.class_id != destination_work.class_id
            or successor.work_id != destination_work.work_id
        ):
            raise WorkflowOwnershipError(
                "destination candidate does not preserve the exact family and scope"
            )
        try:
            self.repository.load_work_record(
                destination_work,
                destination.record_ref.record_kind,
                destination.record_ref.contract_version,
                destination.record_ref.record_id,
            )
        except PortiaNotFoundError:
            pass
        else:
            raise PortiaConflictError("destination record identity already exists")

        source_target = {
            "kind": "work_record",
            "work_record_ref": predecessor.to_dict(),
        }
        destination_target = {
            "kind": "work_record",
            "work_record_ref": destination.to_dict(),
        }
        for target in (
            {"kind": "work", "work_ref": predecessor.work_ref.to_dict()},
            {"kind": "work", "work_ref": destination_work.to_dict()},
            source_target,
            destination_target,
        ):
            _require_no_active_operation_conflict(self.workspace_root, target)
            self.integrity.require_allowed(target, "block_current_use")

        incoming = self._incoming_references(predecessor, source.path)
        dependencies = self._dependency_reviews(
            predecessor,
            effective_at=effective_at,
        )
        if len(incoming) + len(dependencies) > _MAX_DISPOSITION_ENTRIES:
            raise WorkflowPrerequisiteError(
                "ownership review exceeds the bounded operation-journal evidence limit"
            )
        return OwnershipCorrectionAssessment(
            predecessor,
            destination,
            source.fingerprint,
            incoming,
            dependencies,
        )

    @staticmethod
    def _require_dispositions(
        assessment: OwnershipCorrectionAssessment,
        reference_dispositions: Mapping[str, str],
        dependency_dispositions: Mapping[str, str],
    ) -> None:
        reference_keys = {item.reference_key for item in assessment.incoming_references}
        if set(reference_dispositions) != reference_keys:
            raise WorkflowPrerequisiteError(
                "incoming-reference disposition review is incomplete or stale"
            )
        if any(
            value not in _REFERENCE_DISPOSITIONS
            for value in reference_dispositions.values()
        ):
            raise WorkflowPrerequisiteError(
                "incoming-reference review contains an unsupported disposition"
            )
        if any(
            value in _BLOCKING_REFERENCE_DISPOSITIONS
            for value in reference_dispositions.values()
        ):
            raise WorkflowPrerequisiteError(
                "incoming-reference disposition blocks ownership completion"
            )

        dependency_keys = {item.dependency_key for item in assessment.dependencies}
        if set(dependency_dispositions) != dependency_keys:
            raise WorkflowPrerequisiteError(
                "Dependency disposition review is incomplete or stale"
            )
        if any(
            value not in _DEPENDENCY_DISPOSITIONS
            for value in dependency_dispositions.values()
        ):
            raise WorkflowPrerequisiteError(
                "Dependency review contains an unsupported disposition"
            )
        for review in assessment.dependencies:
            disposition = dependency_dispositions[review.dependency_key]
            if review.strength == "required" and (
                review.condition in {"review_required", "unsatisfied", "indeterminate"}
                or disposition in _BLOCKING_DEPENDENCY_DISPOSITIONS
            ):
                raise WorkflowPrerequisiteError(
                    "unresolved required Dependency blocks ownership completion"
                )

    @staticmethod
    def _certificate(
        assessment: OwnershipCorrectionAssessment,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        correction_id: str,
        reason: Mapping[str, object],
        effective_at: str,
        created_by: Mapping[str, object],
        source_updated_at: str,
        parent_correction: ExactLocalRecordRef | None,
    ) -> PortiaRecord:
        successor_data = successor.to_dict()
        if successor_data.get("updated_at") != effective_at:
            raise WorkflowPrerequisiteError(
                "destination update time must equal correction effective_at"
            )
        if successor_data.get("updated_by") != dict(created_by):
            raise WorkflowPrerequisiteError(
                "destination update agent must equal certificate created_by"
            )
        data: dict[str, object] = {
            "schema_version": "2",
            "record_type": "ownership_correction",
            "module_id": "portia",
            "class_id": destination_work.class_id,
            "work_id": destination_work.work_id,
            "work_kind": destination_work.work_kind,
            "correction_id": correction_id,
            "correction_kind": "child_work_root",
            "source": {
                "kind": "work_record",
                "work_record_ref": assessment.source.to_dict(),
                "observed_updated_at": source_updated_at,
            },
            "destination": {
                "kind": "work_record",
                "work_record_ref": assessment.destination.to_dict(),
                "observed_updated_at": effective_at,
            },
            "reason": dict(reason),
            "effective_at": effective_at,
            "creation_source": {"type": "digital_entry"},
            "created_at": effective_at,
            "created_by": dict(created_by),
        }
        if parent_correction is not None:
            if (
                parent_correction.record_kind != "ownership_correction"
                or parent_correction.contract_version != "2"
            ):
                raise WorkflowOwnershipError(
                    "parent correction must be an exact ownership_correction@2 ref"
                )
            data["parent_correction"] = parent_correction.to_dict()
        try:
            return parse_portia_record("ownership_correction", "2", data)
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "ownership correction certificate is not runtime/schema valid"
            ) from exc

    def correct_work_root(
        self,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        correction_id: str,
        reason: Mapping[str, object],
        effective_at: str,
        created_by: Mapping[str, object],
        reference_dispositions: Mapping[str, str],
        dependency_dispositions: Mapping[str, str],
        parent_correction: ExactLocalRecordRef | None = None,
        operation_id: str | None = None,
    ) -> OwnershipCorrectionResult:
        """Persist one certified correction through its family workflow authority."""
        registration = self._registration(predecessor, destination_work)
        if operation_id is not None:
            replay = self._completed_replay(
                operation_id,
                predecessor,
                destination_work,
                successor,
                expected=expected,
                transition_id=transition_id,
                correction_id=correction_id,
                reason=reason,
                effective_at=effective_at,
                created_by=created_by,
                reference_dispositions=reference_dispositions,
                dependency_dispositions=dependency_dispositions,
                parent_correction=parent_correction,
            )
            if replay is not None:
                return replay
        assessment = self.assess_correction(
            predecessor,
            destination_work,
            successor,
            expected=expected,
            effective_at=effective_at,
        )
        self._require_dispositions(
            assessment,
            reference_dispositions,
            dependency_dispositions,
        )
        source = self.repository.load_work_record(
            predecessor.work_ref,
            predecessor.record_ref.record_kind,
            predecessor.record_ref.contract_version,
            predecessor.record_ref.record_id,
        )
        source_updated_at = source.record.field("updated_at")
        if not isinstance(source_updated_at, str):
            raise WorkflowPrerequisiteError(
                "ownership source has no exact observed update time"
            )
        if parent_correction is not None:
            if (
                parent_correction.record_kind != "ownership_correction"
                or parent_correction.contract_version != "2"
            ):
                raise WorkflowOwnershipError(
                    "parent correction must be an exact ownership_correction@2 ref"
                )
            self.repository.load_work_record(
                destination_work,
                parent_correction.record_kind,
                parent_correction.contract_version,
                parent_correction.record_id,
            )
        certificate = self._certificate(
            assessment,
            destination_work,
            successor,
            correction_id=correction_id,
            reason=reason,
            effective_at=effective_at,
            created_by=created_by,
            source_updated_at=source_updated_at,
            parent_correction=parent_correction,
        )
        evidence = OwnershipCorrectionEvidence(
            certificate,
            tuple(sorted(reference_dispositions.items())),
            tuple(sorted(dependency_dispositions.items())),
        )
        family = registration.workflow_service(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.integrity.quarantine,
            context_assembler=self.contexts,
        )
        committed = family.correct_work_root(
            predecessor,
            destination_work,
            successor,
            expected=expected,
            transition_id=transition_id,
            effective_at=effective_at,
            operation_id=operation_id,
            _ownership_evidence=evidence,
            fault_hook=self._fault_hook,
        )
        certificate_ref = _record_reference(destination_work, certificate)
        accepted = self.resolve_correction(certificate_ref)
        if accepted.record.to_dict() != certificate.to_dict():
            raise PortiaConflictError(
                "accepted ownership certificate differs from exact intent"
            )
        journal = OperationJournalStore(self.workspace_root).load_current(
            committed.operation_id
        )
        status = journal.revision.to_dict().get("state")
        if status != "completed" or journal.revision.contract_version != "2":
            raise WorkflowPrerequisiteError(
                "ownership operation did not reach completed journal v2 state"
            )
        return OwnershipCorrectionResult(
            committed.operation_id,
            predecessor,
            assessment.destination,
            certificate_ref,
            "completed",
            len(assessment.incoming_references),
            len(assessment.dependencies),
            False,
        )

    def _completed_replay(
        self,
        operation_id: str,
        predecessor: ExactPortiaWorkRecordRef,
        destination_work: ExactPortiaWorkRef,
        successor: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        correction_id: str,
        reason: Mapping[str, object],
        effective_at: str,
        created_by: Mapping[str, object],
        reference_dispositions: Mapping[str, str],
        dependency_dispositions: Mapping[str, str],
        parent_correction: ExactLocalRecordRef | None,
    ) -> OwnershipCorrectionResult | None:
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            return None
        journal = current.revision.to_dict()
        if journal.get("state") != "completed":
            raise PortiaRecoveryRequiredError(
                "existing ownership operation requires explicit recovery"
            )
        if (
            current.revision.contract_version != "2"
            or journal.get("operation_kind") != "correct_ownership"
            or journal.get("scope") != "graph"
        ):
            raise PortiaConflictError(
                "completed operation identity is bound to different intent"
            )
        destination = _record_reference(destination_work, successor)
        accepted_successor = self.repository.load_work_record(
            destination_work,
            successor.contract,
            successor.contract_version,
            cast(str, successor.logical_id),
        )
        if accepted_successor.record.to_dict() != successor.to_dict():
            raise PortiaConflictError(
                "completed ownership destination differs from replay intent"
            )
        certificate_ref = ExactPortiaWorkRecordRef(
            work_ref=destination_work,
            record_ref=ExactLocalRecordRef(
                record_kind="ownership_correction",
                record_id=correction_id,
                contract_version="2",
            ),
        )
        certificate = self.repository.load_work_record(
            destination_work,
            "ownership_correction",
            "2",
            correction_id,
        )
        certificate_data = certificate.record.to_dict()
        source_endpoint = certificate_data.get("source")
        destination_endpoint = certificate_data.get("destination")
        expected_parent = (
            parent_correction.to_dict() if parent_correction is not None else None
        )
        if (
            not isinstance(source_endpoint, Mapping)
            or source_endpoint.get("work_record_ref") != predecessor.to_dict()
            or not isinstance(destination_endpoint, Mapping)
            or destination_endpoint.get("work_record_ref") != destination.to_dict()
            or certificate_data.get("reason") != dict(reason)
            or certificate_data.get("effective_at") != effective_at
            or certificate_data.get("created_by") != dict(created_by)
            or certificate_data.get("parent_correction") != expected_parent
        ):
            raise PortiaConflictError(
                "completed ownership certificate differs from replay intent"
            )
        facts = journal.get("intent_facts")
        if not isinstance(facts, list):
            raise PortiaConflictError("completed ownership evidence is malformed")
        fact_map = {
            item.get("name"): item.get("value")
            for item in facts
            if isinstance(item, Mapping)
        }
        if fact_map.get("reference_disposition_count") != len(
            reference_dispositions
        ) or fact_map.get("dependency_disposition_count") != len(
            dependency_dispositions
        ):
            raise PortiaConflictError(
                "completed ownership disposition counts differ from replay intent"
            )
        for index, (identity, disposition) in enumerate(
            sorted(reference_dispositions.items()), start=1
        ):
            if (
                fact_map.get(f"reference_{index}_identity") != identity
                or fact_map.get(f"reference_{index}_disposition") != disposition
            ):
                raise PortiaConflictError(
                    "completed incoming-reference evidence differs from replay intent"
                )
        for index, (identity, disposition) in enumerate(
            sorted(dependency_dispositions.items()), start=1
        ):
            if (
                fact_map.get(f"dependency_{index}_identity") != identity
                or fact_map.get(f"dependency_{index}_disposition") != disposition
            ):
                raise PortiaConflictError(
                    "completed Dependency evidence differs from replay intent"
                )
        source_target = {
            "kind": "work_record",
            "work_record_ref": predecessor.to_dict(),
        }
        write_set = journal.get("write_set")
        matched_source = False
        matched_transition = False
        transition_target = {
            "kind": "work_record",
            "work_record_ref": {
                "work_ref": predecessor.work_ref.to_dict(),
                "record_ref": {
                    "record_kind": "lifecycle_transition",
                    "record_id": transition_id,
                    "contract_version": "1",
                },
            },
        }
        if isinstance(write_set, list):
            for step in write_set:
                if not isinstance(step, Mapping):
                    continue
                if step.get("target") == source_target:
                    precondition = step.get("precondition")
                    if isinstance(precondition, Mapping):
                        matched_source = (
                            precondition.get("fingerprint") == expected.to_dict()
                        )
                elif step.get("target") == transition_target:
                    matched_transition = True
        if not matched_source or not matched_transition:
            raise PortiaConflictError(
                "completed ownership source or transition differs from replay intent"
            )
        return OwnershipCorrectionResult(
            operation_id,
            predecessor,
            destination,
            certificate_ref,
            "completed",
            len(reference_dispositions),
            len(dependency_dispositions),
            False,
        )

    def resolve_correction(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> StoredRecord:
        """Resolve exactly one destination-owned ownership_correction@2."""
        if (
            reference.record_ref.record_kind != "ownership_correction"
            or reference.record_ref.contract_version != "2"
        ):
            raise WorkflowOwnershipError(
                "correction resolution requires an exact ownership_correction@2 ref"
            )
        stored = self.repository.load_work_record(
            reference.work_ref,
            "ownership_correction",
            "2",
            reference.record_ref.record_id,
        )
        data = stored.record.to_dict()
        destination = data.get("destination")
        endpoint = (
            destination.get("work_record_ref")
            if isinstance(destination, Mapping)
            else None
        )
        if (
            data.get("class_id") != reference.work_ref.class_id
            or data.get("work_id") != reference.work_ref.work_id
            or data.get("work_kind") != reference.work_ref.work_kind
            or not isinstance(endpoint, Mapping)
            or endpoint.get("work_ref") != reference.work_ref.to_dict()
        ):
            raise WorkflowOwnershipError(
                "ownership certificate destination scope is inconsistent"
            )
        self.integrity.quarantine.require_allowed(
            {"kind": "work_record", "work_record_ref": reference.to_dict()},
            "block_current_use",
        )
        return stored
