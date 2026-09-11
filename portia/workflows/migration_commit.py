"""Journaled commit authority for exact work-record representation migration.

Slice 22 deliberately covers only work-record sources whose exact representation
is still on its creation-baseline lifecycle branch.  Existing lifecycle
transition or lifecycle-history-correction evidence fails closed so later slices
can extend the selected-history topology without weakening it here.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import Path
from typing import cast

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRecordRef
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import (
    ContentFingerprint,
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.io import read_bytes
from portia.storage.migration_representations import (
    MigrationRepresentationStore,
    version_qualified_representation_path,
)
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.paths import (
    resolve_workspace_relative,
    work_record_path,
    work_storage_history_path,
    workspace_relative,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows.action_transition import (
    ActionLifecycleCoordinator,
    _journal_plan,
    _lock_plan,
    _state_fact,
)
from portia.workflows.common import WorkflowServiceBase, record_target, work_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.dependencies import DependencyWorkflowService
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.migrations import MigrationPlan

PlanValidator = Callable[[MigrationPlan], MigrationPlan]


def _parsed_timestamp(value: str, *, description: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} is not an explicit timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"{description} lacks an explicit UTC offset"
        )
    return parsed


def _work_record_target(reference: ExactPortiaWorkRecordRef) -> dict[str, object]:
    return {"kind": "work_record", "work_record_ref": reference.to_dict()}


def _local_lifecycle_target(
    reference: ExactPortiaWorkRecordRef,
) -> dict[str, object]:
    return {
        "kind": "local_record",
        "record_ref": reference.record_ref.to_dict(),
    }


def _exact_transition_ref(transition_id: str) -> dict[str, object]:
    return ExactLocalRecordRef(
        record_kind="lifecycle_transition",
        record_id=transition_id,
        contract_version="1",
    ).to_dict()


def _superseded_source(source: PortiaRecord) -> PortiaRecord:
    value = source.to_dict()
    value["status"] = "superseded"
    try:
        return parse_portia_record(
            source.contract,
            source.contract_version,
            value,
        )
    except Exception as exc:
        raise WorkflowPrerequisiteError(
            "migration source contract cannot represent final superseded state"
        ) from exc


def _migration_transition(
    plan: MigrationPlan,
    *,
    transition_id: str,
    created_at: str,
) -> PortiaRecord:
    if not isinstance(plan.source_reference, ExactPortiaWorkRecordRef):
        raise WorkflowOwnershipError(
            "work-record migration transition requires an exact work-record source"
        )
    if plan.reason_code == "other":
        raise WorkflowPrerequisiteError(
            "journaled migration requires a recognized non-'other' transition reason code"
        )
    reason: dict[str, object] = {
        "category": "migration",
        "code": plan.reason_code,
    }
    if plan.reason_detail is not None:
        reason["detail"] = plan.reason_detail
    reference = plan.source_reference
    try:
        return parse_portia_record(
            "lifecycle_transition",
            "1",
            {
                "schema_version": "1",
                "record_type": "lifecycle_transition",
                "module_id": "portia",
                "class_id": reference.work_ref.class_id,
                "work_id": reference.work_ref.work_id,
                "transition_id": transition_id,
                "target": _local_lifecycle_target(reference),
                "previous_transition": None,
                "from_status": plan.source.record.status,
                "to_status": "superseded",
                "reason": reason,
                "effective_at": plan.effective_at,
                "creation_source": {"type": "digital_entry"},
                "created_at": created_at,
                "created_by": dict(plan.created_by),
            },
        )
    except Exception as exc:
        raise WorkflowPrerequisiteError(
            "migration lifecycle transition is not structurally valid"
        ) from exc


def _migration_certificate(
    plan: MigrationPlan,
    *,
    migration_id: str,
    created_at: str,
) -> PortiaRecord:
    if not isinstance(plan.source_reference, ExactPortiaWorkRecordRef) or not isinstance(
        plan.destination_reference,
        ExactPortiaWorkRecordRef,
    ):
        raise WorkflowOwnershipError(
            "work-record migration certificate requires exact work-record endpoints"
        )
    source = plan.source_reference
    destination = plan.destination_reference
    try:
        return parse_portia_record(
            "record_migration",
            "1",
            {
                "schema_version": "1",
                "record_type": "record_migration",
                "module_id": "portia",
                "class_id": source.work_ref.class_id,
                "work_id": source.work_ref.work_id,
                "migration_id": migration_id,
                "source": {
                    "kind": "work_record",
                    "work_record_ref": source.to_dict(),
                    "observed_updated_at": plan.source_observed_updated_at,
                },
                "destination": {
                    "kind": "work_record",
                    "work_record_ref": destination.to_dict(),
                    "observed_updated_at": plan.destination_observed_updated_at,
                },
                "reason": plan.reason,
                "transformation": plan.transformation,
                "effective_at": plan.effective_at,
                "creation_source": {"type": "digital_entry"},
                "created_at": created_at,
                "created_by": dict(plan.created_by),
            },
        )
    except Exception as exc:
        raise WorkflowPrerequisiteError(
            "migration certificate is not structurally valid"
        ) from exc


def _intent_digest(
    plan: MigrationPlan,
    *,
    certificate: PortiaRecord,
    transition: PortiaRecord,
    superseded_source: PortiaRecord,
) -> str:
    return hashlib.sha256(
        canonical_json_bytes(
            {
                "source_reference": cast(
                    ExactPortiaWorkRecordRef,
                    plan.source_reference,
                ).to_dict(),
                "destination_reference": cast(
                    ExactPortiaWorkRecordRef,
                    plan.destination_reference,
                ).to_dict(),
                "source": plan.source.record.to_dict(),
                "destination": plan.destination.to_dict(),
                "certificate": certificate.to_dict(),
                "transition": transition.to_dict(),
                "superseded_source": superseded_source.to_dict(),
            }
        )
    ).hexdigest()


class RecordMigrationCommitCoordinator(WorkflowServiceBase):
    """Commit one validated baseline-history work-record migration through #38."""

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
        self.representations = MigrationRepresentationStore(
            workspace_root,
            repository=self.repository,
        )

    def _writer(self) -> ActionLifecycleCoordinator:
        return ActionLifecycleCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _completed_result(
        self,
        operation_id: str,
        current_data: Mapping[str, object],
    ) -> OperationCommitResult:
        """Verify a completed migration by each destination's final intended bytes.

        Migration deliberately revises the ordinary current path twice: first to
        the final superseded source, then to the already-verified destination.
        The generic coordinated replay verifier assumes one durable final result
        per write step and therefore cannot verify this migration topology.
        """

        completed_steps = current_data.get("write_set")
        if not isinstance(completed_steps, list):
            raise PortiaRecoveryRequiredError(
                "completed migration has no verifiable write set"
            )

        accepted: list[tuple[str, ContentFingerprint]] = []
        by_destination: dict[
            str,
            list[tuple[str, ContentFingerprint]],
        ] = {}
        for step in completed_steps:
            if not isinstance(step, dict):
                raise PortiaRecoveryRequiredError(
                    "completed migration has an invalid write step"
                )
            intended = step.get("intended_result")
            destination = step.get("destination_path")
            step_id = step.get("step_id")
            if not isinstance(intended, dict):
                raise PortiaRecoveryRequiredError(
                    "completed migration intended result is invalid"
                )
            if not isinstance(destination, str) or not isinstance(step_id, str):
                raise PortiaRecoveryRequiredError(
                    "completed migration destination identity is invalid"
                )
            fingerprint_value = intended.get("fingerprint")
            try:
                expected = ContentFingerprint.from_dict(fingerprint_value)
            except (TypeError, ValueError) as exc:
                raise PortiaRecoveryRequiredError(
                    f"completed migration fingerprint is invalid: {step_id}"
                ) from exc
            accepted.append((step_id, expected))
            by_destination.setdefault(destination, []).append((step_id, expected))

        repeated = {
            destination: tuple(step_id for step_id, _expected in values)
            for destination, values in by_destination.items()
            if len(values) > 1
        }
        expected_repeat = (
            "step_source_superseded",
            "step_current_switch",
        )
        if repeated and (
            len(repeated) != 1
            or next(iter(repeated.values())) != expected_repeat
        ):
            raise PortiaRecoveryRequiredError(
                "completed migration contains an unexpected repeated destination"
            )

        for destination, values in by_destination.items():
            step_id, expected = values[-1]
            try:
                observed = fingerprint_bytes(
                    read_bytes(
                        resolve_workspace_relative(
                            self.workspace_root,
                            destination,
                        )
                    )
                )
            except OSError as exc:
                raise PortiaRecoveryRequiredError(
                    f"completed migration destination is unavailable: {step_id}"
                ) from exc
            if observed != expected:
                raise PortiaRecoveryRequiredError(
                    f"completed migration destination changed: {step_id}"
                )

        return OperationCommitResult(
            operation_id=operation_id,
            accepted_steps=tuple(step_id for step_id, _expected in accepted),
            accepted_fingerprints=tuple(accepted),
            acquired_lock_ids=(),
        )

    def _completed_replay(
        self,
        operation_id: str,
        *,
        digest: str,
    ) -> OperationCommitResult | None:
        store = OperationJournalStore(self.workspace_root)
        try:
            current = store.load_current(operation_id)
        except PortiaNotFoundError:
            return None
        data = current.revision.to_dict()
        if data.get("intent_digest") != digest:
            raise PortiaConflictError(
                "migration operation identity is already bound to different intent"
            )
        if data.get("operation_kind") != "migrate_representation":
            raise PortiaConflictError(
                "migration operation identity is bound to another operation kind"
            )
        if data.get("state") == "completed":
            return self._completed_result(operation_id, data)
        raise PortiaRecoveryRequiredError(
            "existing migration operation requires explicit #38 recovery"
        )

    def _require_baseline_history(
        self,
        reference: ExactPortiaWorkRecordRef,
    ) -> None:
        target = _local_lifecycle_target(reference)
        transitions = tuple(
            stored
            for stored in self.repository.list_work_records(
                reference.work_ref,
                "lifecycle_transition",
                version="1",
            )
            if stored.record.field("target") == target
        )
        corrections = tuple(
            stored
            for stored in self.repository.list_work_records(
                reference.work_ref,
                "lifecycle_history_correction",
                version="1",
            )
            if stored.record.field("target") == target
        )
        if transitions or corrections:
            raise WorkflowPrerequisiteError(
                "Slice 22 migration commit requires a source still on its "
                "creation-baseline lifecycle branch"
            )

    def _require_dependency_lifecycle_write(
        self,
        reference: ExactPortiaWorkRecordRef,
        *,
        evaluated_at: str,
    ) -> None:
        gate = DependencyWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        ).evaluate_gate(
            reference,
            gate="current_use",
            evaluated_at=evaluated_at,
        )
        blockers: list[str] = []
        for condition in gate.conditions:
            if condition.strength != "required" or condition.condition != "unsatisfied":
                continue
            blockers.append(condition.reference.record_ref.record_id)
        if blockers:
            raise WorkflowPrerequisiteError(
                "migration required Dependency current-use lifecycle-write gate "
                "is unsatisfied; blockers: " + ", ".join(blockers)
            )

    def _require_plan_current(
        self,
        plan: MigrationPlan,
    ) -> StoredRecord:
        source_reference = cast(
            ExactPortiaWorkRecordRef,
            plan.source_reference,
        )
        current = self.repository.load_work_record(
            source_reference.work_ref,
            source_reference.record_ref.record_kind,
            source_reference.record_ref.contract_version,
            source_reference.record_ref.record_id,
        )
        if (
            current.fingerprint != plan.source.fingerprint
            or current.record.to_dict() != plan.source.record.to_dict()
        ):
            raise PortiaConflictError(
                "migration source changed after planning"
            )
        return current

    @staticmethod
    def _require_same_plan(
        supplied: MigrationPlan,
        validated: MigrationPlan,
    ) -> None:
        same = (
            supplied.source_reference == validated.source_reference
            and supplied.destination_reference == validated.destination_reference
            and supplied.source.fingerprint == validated.source.fingerprint
            and supplied.source.record.to_dict() == validated.source.record.to_dict()
            and supplied.destination.to_dict() == validated.destination.to_dict()
            and supplied.source_observed_updated_at
            == validated.source_observed_updated_at
            and supplied.destination_observed_updated_at
            == validated.destination_observed_updated_at
            and supplied.transformation == validated.transformation
            and supplied.reason == validated.reason
            and supplied.effective_at == validated.effective_at
            and dict(supplied.created_by) == dict(validated.created_by)
        )
        if not same:
            raise PortiaConflictError(
                "migration plan changed during commit revalidation"
            )

    def _require_quarantine_allowed(
        self,
        plan: MigrationPlan,
        *,
        certificate: PortiaRecord,
        transition: PortiaRecord,
    ) -> None:
        source = cast(ExactPortiaWorkRecordRef, plan.source_reference)
        destination = cast(ExactPortiaWorkRecordRef, plan.destination_reference)
        self.quarantine.require_allowed(
            work_target(source.work_ref),
            "block_work_writes",
        )
        for target in (
            _work_record_target(source),
            _work_record_target(destination),
            record_target(source.work_ref, certificate),
            record_target(source.work_ref, transition),
        ):
            self.quarantine.require_allowed(target, "block_work_writes")

    @staticmethod
    def _step(
        *,
        step_id: str,
        sequence: int,
        action: str,
        target: dict[str, object],
        role: str,
        destination_path: str,
        precondition: dict[str, object],
        contract_version: str,
        content: bytes,
        selected_state: list[dict[str, object]],
        reason_code: str,
    ) -> dict[str, object]:
        return {
            "step_id": step_id,
            "sequence": sequence,
            "phase": "canonical_gate",
            "action": action,
            "target": target,
            "representation_role": role,
            "destination_path": destination_path,
            "precondition": precondition,
            "intended_result": {
                "contract_version": contract_version,
                "fingerprint": fingerprint_bytes(content).to_dict(),
                "selected_state": selected_state,
            },
            "disposition": "staged",
            "observed_result": None,
            "compensation_step_id": None,
            "reason_code": reason_code,
        }

    def commit(
        self,
        plan: MigrationPlan,
        *,
        migration_id: str,
        transition_id: str,
        created_at: str,
        operation_id: str | None,
        fault_hook: FaultHook | None,
        plan_validator: PlanValidator,
    ) -> OperationCommitResult:
        """Commit one exact baseline-history work-record representation migration."""
        if not isinstance(plan.source_reference, ExactPortiaWorkRecordRef) or not isinstance(
            plan.destination_reference,
            ExactPortiaWorkRecordRef,
        ):
            raise WorkflowOwnershipError(
                "Slice 22 journaled commit supports work-record migrations only"
            )
        source_reference = plan.source_reference
        destination_reference = plan.destination_reference
        if source_reference.work_ref != destination_reference.work_ref:
            raise WorkflowOwnershipError(
                "migration commit cannot change the owning work root"
            )
        if (
            source_reference.record_ref.record_kind
            != destination_reference.record_ref.record_kind
            or source_reference.record_ref.record_id
            != destination_reference.record_ref.record_id
        ):
            raise WorkflowOwnershipError(
                "migration commit must preserve work-record logical identity"
            )

        created = _parsed_timestamp(created_at, description="migration created_at")
        effective = _parsed_timestamp(
            plan.effective_at,
            description="migration effective_at",
        )
        if created < effective:
            raise WorkflowPrerequisiteError(
                "migration created_at cannot precede effective_at"
            )

        certificate = _migration_certificate(
            plan,
            migration_id=migration_id,
            created_at=created_at,
        )
        transition = _migration_transition(
            plan,
            transition_id=transition_id,
            created_at=created_at,
        )
        superseded_source = _superseded_source(plan.source.record)
        digest = _intent_digest(
            plan,
            certificate=certificate,
            transition=transition,
            superseded_source=superseded_source,
        )
        op_id = operation_id or f"op_{digest}"
        replay = self._completed_replay(op_id, digest=digest)
        if replay is not None:
            return replay

        validated = plan_validator(plan)
        self._require_same_plan(plan, validated)
        current = self._require_plan_current(validated)
        self._require_baseline_history(source_reference)
        self._require_dependency_lifecycle_write(
            source_reference,
            evaluated_at=validated.effective_at,
        )
        self._require_quarantine_allowed(
            validated,
            certificate=certificate,
            transition=transition,
        )

        source_status = current.record.status
        destination_status = validated.destination.status
        if not isinstance(source_status, str) or not isinstance(
            destination_status,
            str,
        ):
            raise WorkflowPrerequisiteError(
                "migration source and destination require lifecycle status"
            )
        if source_status != destination_status:
            raise WorkflowPrerequisiteError(
                "migration destination lifecycle changed after planning"
            )

        work = source_reference.work_ref
        current_path = work_record_path(
            self.workspace_root,
            work,
            source_reference.record_ref.record_kind,
            source_reference.record_ref.record_id,
        )
        current_bytes = read_bytes(current.path)
        if fingerprint_bytes(current_bytes) != current.fingerprint:
            raise PortiaConflictError(
                "selected migration source changed during commit preflight"
            )

        source_id = source_reference.record_ref.record_id
        source_contract = source_reference.record_ref.record_kind
        source_version = source_reference.record_ref.contract_version
        destination_version = destination_reference.record_ref.contract_version
        history_path = work_storage_history_path(
            self.workspace_root,
            work,
            source_contract,
            source_id,
            current.fingerprint.digest,
        )
        destination_path = version_qualified_representation_path(
            self.workspace_root,
            work,
            source_contract,
            source_id,
            destination_version,
        )
        source_version_path = version_qualified_representation_path(
            self.workspace_root,
            work,
            source_contract,
            source_id,
            source_version,
        )
        certificate_path = work_record_path(
            self.workspace_root,
            work,
            "record_migration",
            migration_id,
        )
        transition_path = work_record_path(
            self.workspace_root,
            work,
            "lifecycle_transition",
            transition_id,
        )

        for description, path in (
            ("destination representation", destination_path),
            ("migration certificate", certificate_path),
            ("migration transition", transition_path),
            ("final source representation", source_version_path),
        ):
            if path.exists():
                raise PortiaConflictError(
                    f"{description} already exists before journaled migration commit"
                )

        destination_bytes = canonical_json_bytes(validated.destination.to_dict())
        certificate_bytes = canonical_json_bytes(certificate.to_dict())
        transition_bytes = canonical_json_bytes(transition.to_dict())
        superseded_bytes = canonical_json_bytes(superseded_source.to_dict())
        superseded_fp = fingerprint_bytes(superseded_bytes)

        steps: list[dict[str, object]] = []
        candidates: dict[str, bytes] = {}

        if history_path.exists():
            history_bytes = read_bytes(history_path)
            if (
                history_bytes != current_bytes
                or fingerprint_bytes(history_bytes) != current.fingerprint
            ):
                raise PortiaCorruptionError(
                    "migration technical storage-history collision"
                )
        else:
            candidates["step_source_history"] = current_bytes
            steps.append(
                self._step(
                    step_id="step_source_history",
                    sequence=len(steps) + 1,
                    action="exclusive_create",
                    target={"kind": "workspace"},
                    role="operational_revision",
                    destination_path=workspace_relative(
                        self.workspace_root,
                        history_path,
                    ),
                    precondition={"presence": "must_be_absent"},
                    contract_version=source_version,
                    content=current_bytes,
                    selected_state=[_state_fact("status", source_status)],
                    reason_code="preserve_prior_revision",
                )
            )

        candidates["step_destination"] = destination_bytes
        steps.append(
            self._step(
                step_id="step_destination",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target={"kind": "workspace"},
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    destination_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version=destination_version,
                content=destination_bytes,
                selected_state=[_state_fact("status", destination_status)],
                reason_code="prepare_migration_destination",
            )
        )

        certificate_target = record_target(work, certificate)
        candidates["step_certificate"] = certificate_bytes
        steps.append(
            self._step(
                step_id="step_certificate",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target=certificate_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    certificate_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version="1",
                content=certificate_bytes,
                selected_state=[_state_fact("migration", "accepted")],
                reason_code=validated.reason_code,
            )
        )

        transition_target = record_target(work, transition)
        candidates["step_transition"] = transition_bytes
        steps.append(
            self._step(
                step_id="step_transition",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target=transition_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    transition_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version="1",
                content=transition_bytes,
                selected_state=[
                    _state_fact("from_status", source_status),
                    _state_fact("to_status", "superseded"),
                ],
                reason_code=validated.reason_code,
            )
        )

        source_target = _work_record_target(source_reference)
        candidates["step_source_superseded"] = superseded_bytes
        steps.append(
            self._step(
                step_id="step_source_superseded",
                sequence=len(steps) + 1,
                action="revision_aware_replace",
                target=source_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    current_path,
                ),
                precondition={
                    "presence": "must_match",
                    "fingerprint": current.fingerprint.to_dict(),
                    "contract_version": source_version,
                    "semantic_checks": [_state_fact("status", source_status)],
                },
                contract_version=source_version,
                content=superseded_bytes,
                selected_state=[_state_fact("status", "superseded")],
                reason_code=validated.reason_code,
            )
        )

        candidates["step_source_version"] = superseded_bytes
        steps.append(
            self._step(
                step_id="step_source_version",
                sequence=len(steps) + 1,
                action="exclusive_create",
                target={"kind": "workspace"},
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    source_version_path,
                ),
                precondition={"presence": "must_be_absent"},
                contract_version=source_version,
                content=superseded_bytes,
                selected_state=[_state_fact("status", "superseded")],
                reason_code="preserve_migrated_source",
            )
        )

        destination_target = _work_record_target(destination_reference)
        candidates["step_current_switch"] = destination_bytes
        steps.append(
            self._step(
                step_id="step_current_switch",
                sequence=len(steps) + 1,
                action="revision_aware_replace",
                target=destination_target,
                role="canonical_domain",
                destination_path=workspace_relative(
                    self.workspace_root,
                    current_path,
                ),
                precondition={
                    "presence": "must_match",
                    "fingerprint": superseded_fp.to_dict(),
                    "contract_version": source_version,
                    "semantic_checks": [_state_fact("status", "superseded")],
                },
                contract_version=destination_version,
                content=destination_bytes,
                selected_state=[_state_fact("status", destination_status)],
                reason_code="select_migration_destination",
            )
        )

        lock_entries, lock_records = _lock_plan(op_id, work, created_at)
        plan_wire = _journal_plan(
            operation_id=op_id,
            digest=digest,
            timestamp=created_at,
            initiated_by=validated.created_by,
            primary_target=source_target,
            affected_targets=[
                destination_target,
                certificate_target,
                transition_target,
            ],
            lock_entries=lock_entries,
            steps=steps,
            prior_status=source_status,
            candidate_status=destination_status,
            contract=source_contract,
            operation_kind="migrate_representation",
        )
        result = self._writer()._write_plan(
            plan=plan_wire,
            candidates=candidates,
            lock_records=lock_records,
            operation_id=op_id,
            digest=digest,
            fault_hook=fault_hook,
        )

        accepted_current = self.repository.load_work_record(
            work,
            source_contract,
            destination_version,
            source_id,
        )
        accepted_source = self.representations.load_preserved_work_record_representation(
            source_reference
        )
        accepted_destination = (
            self.representations.load_preserved_work_record_representation(
                destination_reference
            )
        )
        accepted_certificate = self.repository.load_work_record(
            work,
            "record_migration",
            "1",
            migration_id,
        )
        accepted_transition = self.repository.load_work_record(
            work,
            "lifecycle_transition",
            "1",
            transition_id,
        )
        if accepted_current.record.to_dict() != validated.destination.to_dict():
            raise PortiaCorruptionError(
                "migration current-representation readback disagrees with destination"
            )
        if accepted_destination.record.to_dict() != validated.destination.to_dict():
            raise PortiaCorruptionError(
                "migration destination exact-version readback disagrees"
            )
        if accepted_source.record.to_dict() != superseded_source.to_dict():
            raise PortiaCorruptionError(
                "migration source exact-version readback is not final superseded source"
            )
        if accepted_certificate.record.to_dict() != certificate.to_dict():
            raise PortiaCorruptionError(
                "migration certificate readback disagrees with committed certificate"
            )
        if accepted_transition.record.to_dict() != transition.to_dict():
            raise PortiaCorruptionError(
                "migration lifecycle-transition readback disagrees with committed transition"
            )
        return result
