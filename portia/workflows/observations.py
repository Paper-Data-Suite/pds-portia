"""Observation creation, exact history, and bounded current-use workflows."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import ObservationV2, PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.repository import StoredRecord
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    OBSERVATION_READ_VERSIONS,
    OBSERVATION_VERSION,
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
    require_artifact_review_source,
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


def observation_reference(
    work: ExactPortiaWorkRef,
    observation_id: str,
    *,
    version: str = OBSERVATION_VERSION,
) -> ExactPortiaWorkRecordRef:
    require_supported_evidence_version(
        work,
        contract="observation",
        version=version,
        supported_versions=OBSERVATION_READ_VERSIONS,
    )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind="observation",
            record_id=observation_id,
            contract_version=version,
        ),
    )


def _measurement_types(record: PortiaRecord) -> frozenset[str]:
    content = record.field("content")
    if not isinstance(content, Mapping):
        raise WorkflowOwnershipError("Observation content is malformed")
    measurements = content.get("measurements")
    if measurements is None:
        return frozenset()
    if not isinstance(measurements, tuple):
        raise WorkflowOwnershipError("Observation measurements are malformed")
    values: set[str] = set()
    for measurement in measurements:
        if not isinstance(measurement, Mapping):
            raise WorkflowOwnershipError("Observation measurement is malformed")
        measure_type = measurement.get("measure_type")
        if not isinstance(measure_type, str):
            raise WorkflowOwnershipError("Observation measurement type is malformed")
        values.add(measure_type)
    return frozenset(values)


def _require_method_compatibility(record: PortiaRecord) -> None:
    observer = record.field("observer")
    method = record.field("method")
    if not isinstance(observer, Mapping) or not isinstance(method, str):
        raise WorkflowOwnershipError("Observation observer or method is malformed")
    observer_kind = observer.get("kind")
    if observer_kind == "human":
        if method == "instrumented":
            raise WorkflowPrerequisiteError(
                "human Observation observer cannot use instrumented method"
            )
    elif observer_kind == "instrument":
        if method != "instrumented":
            raise WorkflowPrerequisiteError(
                "instrument Observation observer requires instrumented method"
            )
    else:
        raise WorkflowOwnershipError("Observation observer kind is unsupported")

    measurement_types = _measurement_types(record)
    if method == "manual_count" and not (
        measurement_types & {"count", "percentage"}
    ):
        raise WorkflowPrerequisiteError(
            "manual_count Observation requires count or percentage measurement"
        )
    if method == "manual_timing" and not (
        measurement_types & {"duration", "latency"}
    ):
        raise WorkflowPrerequisiteError(
            "manual_timing Observation requires duration or latency measurement"
        )
    require_artifact_review_source(record)


class ObservationWorkflowService(WorkflowServiceBase):
    """Create v2 digital Observations and resolve exact v1/v2 evidence."""

    def _require_write_input(
        self, work: ExactPortiaWorkRef, record: PortiaRecord
    ) -> ObservationV2:
        require_evidence_owner(work)
        if not isinstance(record, ObservationV2):
            raise WorkflowOwnershipError(
                "new Observation writes require observation@2 input"
            )
        require_evidence_record_owner(work, record, contract="observation")
        require_digital_entry_creation(record)
        require_basic_evidence_shape(record, allow_source_artifacts=True)
        _require_method_compatibility(record)
        if record.status not in {"proposed", "active"}:
            raise WorkflowPrerequisiteError(
                "new Observation identity must begin proposed or active"
            )
        return record

    def create(self, work: ExactPortiaWorkRef, record: PortiaRecord) -> StoredRecord:
        candidate = self._require_write_input(work, record)
        owner = self.repository.load_work(work)
        require_owner_write_eligibility(work, owner.record)
        targets = evidence_target_records(self.repository, work, candidate)
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
        graph = evidence_validation_records(
            (owner.record, *(item.record for item in targets), candidate)
        )
        if candidate.status == "active":
            self.contexts.assemble(
                (owner.record, *(item.record for item in targets), validation_candidate),
                require_actor_current_use=True,
            )
        self.validate_complete_graph(
            graph,
            require_actor_current_use=False,
        )
        self.quarantine.require_allowed(work_target(work), "block_work_writes")
        self.quarantine.require_allowed(
            record_target(work, candidate), "block_work_writes"
        )
        return self.repository.create_work_record(work, candidate)

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        if reference.record_ref.record_kind != "observation":
            raise WorkflowOwnershipError("reference is not an Observation")
        require_supported_evidence_version(
            reference.work_ref,
            contract="observation",
            version=reference.record_ref.contract_version,
            supported_versions=OBSERVATION_READ_VERSIONS,
        )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            "observation",
            reference.record_ref.contract_version,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        require_evidence_owner(work)
        return self.repository.list_observations(work)

    list_observations = list

    def require_current_use(
        self, reference: ExactPortiaWorkRecordRef
    ) -> StoredRecord:
        observation = self.load_exact(reference)
        require_evidence_lifecycle_reconciled(
            self.repository, reference.work_ref, observation.record
        )
        require_basic_evidence_shape(
            observation.record,
            allow_supersedes=True,
            allow_source_artifacts=True,
        )
        _require_method_compatibility(observation.record)
        if observation.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current Observation use requires active evidence"
            )
        require_source_artifact_authority(
            self.workspace_root,
            self.repository,
            observation.record,
            require_current_use=True,
        )
        owner = self.repository.load_work(reference.work_ref)
        require_owner_current_eligibility(reference.work_ref, owner.record)
        targets = evidence_target_records(
            self.repository, reference.work_ref, observation.record
        )
        predecessors = supersession_ancestry(
            self.repository, reference.work_ref, observation.record
        )
        require_supersession_effective(predecessors)
        require_work_current_use_quarantine(
            reference.work_ref,
            observation.record,
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
                *(item.record for item in predecessors),
                observation.record,
            )
        )
        self.contexts.assemble(
            (evidence_validation_record(observation.record),),
            require_actor_current_use=True,
        )
        self.validate_complete_graph(graph, require_actor_current_use=False)
        return observation

    resolve_current = require_current_use

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
        """Create a corrected observation@2 successor and supersede its predecessor."""
        if predecessor.record_ref.record_kind != "observation":
            raise WorkflowOwnershipError("correction predecessor is not an Observation")
        _require_method_compatibility(successor)
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
        """Persist one ordinary Observation status transition through #38 coordination."""
        if reference.record_ref.record_kind != "observation":
            raise WorkflowOwnershipError("reference is not an Observation")
        _require_method_compatibility(candidate)
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
