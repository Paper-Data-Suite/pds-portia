"""Registered representation-only migration planning authority.

This module introduces the side-effect-free planning half of
``RecordMigrationWorkflowService``.  It never writes a destination, migration
certificate, lifecycle transition, or current-selection change.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TypeAlias

from portia.models import PortiaRecord, parse_portia_record
from portia.models.common import AttributionAgent, ExplicitOffsetTimestamp
from portia.models.coverage import modelled_contract_versions
from portia.models.errors import PortiaLocalValidationError, PortiaWireError
from portia.models.identifiers import validate_external_id
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.orchestration import FaultHook, OperationCommitResult
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import WorkflowServiceBase
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

MigrationReference: TypeAlias = ExactPortiaWorkRef | ExactPortiaWorkRecordRef
_TOKEN = re.compile(r"^[a-z][a-z0-9_]*$")
_REASON_CATEGORIES = frozenset(
    {
        "canonical_representation_change",
        "contract_normalization",
        "contract_upgrade",
        "other",
    }
)
_IMMUTABLE_AUDIT_CONTRACTS = frozenset(
    {
        "amendment",
        "exceptional_removal",
        "lifecycle_history_correction",
        "lifecycle_transition",
        "ownership_correction",
        "record_migration",
    }
)


@dataclass(frozen=True, slots=True)
class MigrationTransformContext:
    """Exact immutable inputs supplied to one registered transformer."""

    source_reference: MigrationReference
    destination_version: str
    effective_at: str
    created_by: Mapping[str, object]
    reason_category: str
    reason_code: str
    reason_detail: str | None


MigrationTransform: TypeAlias = Callable[
    [PortiaRecord, MigrationTransformContext], PortiaRecord
]
MigrationSemanticValidator: TypeAlias = Callable[[PortiaRecord, PortiaRecord], bool]


@dataclass(frozen=True, slots=True)
class MigrationTransformerSpec:
    """Public metadata for one exact registered migration procedure."""

    contract: str
    source_version: str
    destination_version: str
    transformer_id: str
    transformer_version: str
    reason_category: str
    reason_code: str


@dataclass(frozen=True, slots=True)
class _MigrationTransformerRegistration:
    spec: MigrationTransformerSpec
    transform: MigrationTransform
    semantic_equivalence: MigrationSemanticValidator


@dataclass(frozen=True, slots=True)
class MigrationPlan:
    """Side-effect-free validated candidate for one exact representation migration."""

    source_reference: MigrationReference
    destination_reference: MigrationReference
    source: StoredRecord
    destination: PortiaRecord
    source_observed_updated_at: str
    destination_observed_updated_at: str
    transformer_id: str
    transformer_version: str
    reason_category: str
    reason_code: str
    reason_detail: str | None
    effective_at: str
    created_by: Mapping[str, object]

    @property
    def transformation(self) -> dict[str, str]:
        return {
            "transformer_id": self.transformer_id,
            "transformer_version": self.transformer_version,
        }

    @property
    def reason(self) -> dict[str, str]:
        value = {"category": self.reason_category, "code": self.reason_code}
        if self.reason_detail is not None:
            value["detail"] = self.reason_detail
        return value


def _contract_and_version(reference: MigrationReference) -> tuple[str, str]:
    if isinstance(reference, ExactPortiaWorkRef):
        return reference.work_kind, reference.contract_version
    return reference.record_ref.record_kind, reference.record_ref.contract_version


def _destination_reference(
    source: MigrationReference,
    destination_version: str,
) -> MigrationReference:
    if isinstance(source, ExactPortiaWorkRef):
        return ExactPortiaWorkRef(
            module_id=source.module_id,
            class_id=source.class_id,
            work_id=source.work_id,
            work_kind=source.work_kind,
            contract_version=destination_version,
        )
    return ExactPortiaWorkRecordRef(
        work_ref=source.work_ref,
        record_ref=ExactLocalRecordRef(
            record_kind=source.record_ref.record_kind,
            record_id=source.record_ref.record_id,
            contract_version=destination_version,
        ),
    )


def _validated_external(value: object, field_name: str) -> str:
    try:
        return validate_external_id(value, field_name)
    except PortiaLocalValidationError as exc:
        raise WorkflowPrerequisiteError(str(exc)) from exc


def _validated_token(value: object, field_name: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise WorkflowPrerequisiteError(
            f"{field_name} must be a lowercase migration token"
        )
    return value


def _timestamp(value: object, field_name: str) -> ExplicitOffsetTimestamp:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{field_name} must be an explicit timestamp")
    try:
        return ExplicitOffsetTimestamp(value)
    except PortiaLocalValidationError as exc:
        raise WorkflowPrerequisiteError(
            f"{field_name} must be an explicit RFC 3339 timestamp"
        ) from exc


def _updated_at(record: PortiaRecord, description: str) -> str:
    value = record.field("updated_at")
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} has no observed updated_at")
    _timestamp(value, f"{description} updated_at")
    return value


def _require_source_eligible(record: PortiaRecord) -> None:
    if record.contract in _IMMUTABLE_AUDIT_CONTRACTS:
        raise WorkflowPrerequisiteError(
            f"immutable audit contract {record.contract}@{record.contract_version} "
            "is not migration eligible"
        )
    status = record.status
    if not isinstance(status, str):
        raise WorkflowPrerequisiteError(
            "migration source must be a lifecycle-bearing Portia domain representation"
        )
    if status == "superseded":
        raise WorkflowPrerequisiteError(
            "migration source is already superseded; migrate the current frontier instead"
        )
    _updated_at(record, "migration source")


def _require_destination_identity(
    source_reference: MigrationReference,
    source: PortiaRecord,
    destination: PortiaRecord,
    destination_version: str,
) -> None:
    source_contract, source_version = _contract_and_version(source_reference)
    if destination.contract != source_contract:
        raise WorkflowOwnershipError(
            "migration destination changes the semantic record family"
        )
    if destination.contract_version != destination_version:
        raise WorkflowOwnershipError(
            "registered transformer returned the wrong destination contract version"
        )
    if destination_version == source_version:
        raise WorkflowPrerequisiteError(
            "migration source and destination contract versions must differ"
        )
    if destination.module_id != source.module_id:
        raise WorkflowOwnershipError("migration destination changes module identity")
    if destination.class_id != source.class_id:
        raise WorkflowOwnershipError("migration destination changes class ownership")
    if destination.work_id != source.work_id:
        raise WorkflowOwnershipError("migration destination changes work-root identity")
    if destination.logical_id != source.logical_id:
        raise WorkflowOwnershipError("migration destination changes stable logical identity")
    if isinstance(source_reference, ExactPortiaWorkRef):
        if destination.work_kind != source_reference.work_kind:
            raise WorkflowOwnershipError("migration destination changes work_kind")
    elif destination.contract != source_reference.record_ref.record_kind:
        raise WorkflowOwnershipError("migration destination changes record_kind")


def _require_destination_lifecycle(
    source: PortiaRecord,
    destination: PortiaRecord,
) -> None:
    if destination.status != source.status:
        raise WorkflowPrerequisiteError(
            "representation-only migration must preserve semantic lifecycle state"
        )


def _require_destination_provenance(
    destination: PortiaRecord,
    *,
    effective_at: str,
    created_by: Mapping[str, object],
) -> None:
    data = destination.to_dict()
    if data.get("creation_source") != {"type": "digital_entry"}:
        raise WorkflowPrerequisiteError(
            "migration destination creation_source must be digital_entry"
        )
    if data.get("created_at") != effective_at or data.get("updated_at") != effective_at:
        raise WorkflowPrerequisiteError(
            "migration destination created_at and updated_at must equal effective_at"
        )
    expected_by = dict(created_by)
    if data.get("created_by") != expected_by or data.get("updated_by") != expected_by:
        raise WorkflowPrerequisiteError(
            "migration destination attribution must match migration planning attribution"
        )


class RecordMigrationWorkflowService(WorkflowServiceBase):
    """Register exact migration procedures and validate side-effect-free plans."""

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
        self._transformers: dict[
            tuple[str, str, str], _MigrationTransformerRegistration
        ] = {}
        self._procedure_keys: dict[tuple[str, str], tuple[str, str, str]] = {}
        self._reason_keys: dict[str, tuple[str, str, str]] = {}

    def registered_transformers(self) -> tuple[MigrationTransformerSpec, ...]:
        """Return deterministic metadata for all explicitly registered procedures."""
        return tuple(
            registration.spec
            for _key, registration in sorted(self._transformers.items())
        )

    def register_transformer(
        self,
        contract: str,
        source_version: str,
        destination_version: str,
        *,
        transformer_id: str,
        transformer_version: str,
        reason_category: str,
        reason_code: str,
        transform: MigrationTransform,
        semantic_equivalence: MigrationSemanticValidator,
    ) -> MigrationTransformerSpec:
        """Register one exact migration pair; registration never infers a version path."""
        family = _validated_external(contract, "migration contract")
        source = _validated_external(source_version, "source contract version")
        destination = _validated_external(
            destination_version, "destination contract version"
        )
        if source == destination:
            raise WorkflowPrerequisiteError(
                "migration transformer source and destination versions must differ"
            )
        if (family, source) not in modelled_contract_versions():
            raise WorkflowPrerequisiteError(
                f"migration source contract is not modeled: {family}@{source}"
            )
        if (family, destination) not in modelled_contract_versions():
            raise WorkflowPrerequisiteError(
                f"migration destination contract is not modeled: {family}@{destination}"
            )
        if family in _IMMUTABLE_AUDIT_CONTRACTS:
            raise WorkflowPrerequisiteError(
                f"immutable audit contract {family} is not migration eligible"
            )
        procedure_id = _validated_token(transformer_id, "transformer_id")
        procedure_version = _validated_external(
            transformer_version, "transformer_version"
        )
        category = _validated_token(reason_category, "migration reason category")
        if category not in _REASON_CATEGORIES:
            raise WorkflowPrerequisiteError(
                f"unsupported migration reason category: {category}"
            )
        code = _validated_token(reason_code, "migration reason code")
        if not callable(transform) or not callable(semantic_equivalence):
            raise WorkflowPrerequisiteError(
                "migration registration requires callable transform and semantic policy"
            )

        key = (family, source, destination)
        if key in self._transformers:
            raise WorkflowPrerequisiteError(
                "an exact migration transformer is already registered for this version pair"
            )
        procedure_key = (procedure_id, procedure_version)
        prior_key = self._procedure_keys.get(procedure_key)
        if prior_key is not None and prior_key != key:
            raise WorkflowPrerequisiteError(
                "one transformer identity/version cannot name multiple migration pairs"
            )
        prior_reason_key = self._reason_keys.get(code)
        if prior_reason_key is not None and prior_reason_key != key:
            raise WorkflowPrerequisiteError(
                "one migration reason code cannot name multiple migration pairs"
            )

        spec = MigrationTransformerSpec(
            contract=family,
            source_version=source,
            destination_version=destination,
            transformer_id=procedure_id,
            transformer_version=procedure_version,
            reason_category=category,
            reason_code=code,
        )
        self._transformers[key] = _MigrationTransformerRegistration(
            spec=spec,
            transform=transform,
            semantic_equivalence=semantic_equivalence,
        )
        self._procedure_keys[procedure_key] = key
        self._reason_keys[code] = key
        return spec

    def _load_current_source(self, reference: MigrationReference) -> StoredRecord:
        if isinstance(reference, ExactPortiaWorkRef):
            stored = self.repository.load_work(reference)
        else:
            self.repository.load_work(reference.work_ref)
            stored = self.repository.load_work_record(
                reference.work_ref,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        _require_source_eligible(stored.record)
        return stored

    def can_migrate(
        self,
        reference: MigrationReference,
        destination_version: str,
    ) -> bool:
        """Report explicit registry support without running a transformer."""
        destination = _validated_external(
            destination_version, "destination contract version"
        )
        contract, source_version = _contract_and_version(reference)
        if source_version == destination:
            return False
        if (contract, source_version, destination) not in self._transformers:
            return False
        self._load_current_source(reference)
        return True

    def plan_migration(
        self,
        reference: MigrationReference,
        destination_version: str,
        *,
        effective_at: str,
        created_by: Mapping[str, object],
        reason_detail: str | None = None,
    ) -> MigrationPlan:
        """Transform and validate one migration candidate without persistence."""
        destination = _validated_external(
            destination_version, "destination contract version"
        )
        contract, source_version = _contract_and_version(reference)
        key = (contract, source_version, destination)
        registration = self._transformers.get(key)
        if registration is None:
            raise WorkflowPrerequisiteError(
                "unsupported migration: no registered transformer for exact version pair"
            )
        if registration.spec.reason_category == "other":
            if reason_detail is None or reason_detail.strip() == "":
                raise WorkflowPrerequisiteError(
                    "other migration reason requires nonempty detail"
                )
        elif reason_detail is not None and reason_detail.strip() == "":
            raise WorkflowPrerequisiteError(
                "migration reason detail must be nonempty when supplied"
            )

        source = self._load_current_source(reference)
        effective = _timestamp(effective_at, "migration effective_at")
        try:
            validated_created_by = AttributionAgent.from_dict(created_by).to_dict()
        except (PortiaLocalValidationError, PortiaWireError) as exc:
            raise WorkflowPrerequisiteError(
                "migration created_by is not a valid attribution agent"
            ) from exc
        source_updated_text = _updated_at(source.record, "migration source")
        source_updated = _timestamp(source_updated_text, "migration source updated_at")
        if effective.datetime < source_updated.datetime:
            raise WorkflowPrerequisiteError(
                "migration effective_at cannot precede the observed source revision"
            )

        context = MigrationTransformContext(
            source_reference=reference,
            destination_version=destination,
            effective_at=effective_at,
            created_by=MappingProxyType(validated_created_by),
            reason_category=registration.spec.reason_category,
            reason_code=registration.spec.reason_code,
            reason_detail=reason_detail,
        )
        try:
            candidate = registration.transform(source.record, context)
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "registered migration transformer failed"
            ) from exc
        if not isinstance(candidate, PortiaRecord):
            raise WorkflowPrerequisiteError(
                "registered migration transformer did not return a PortiaRecord"
            )

        _require_destination_identity(
            reference,
            source.record,
            candidate,
            destination,
        )
        # Reparse the exact destination contract so planning never trusts a
        # transformer-returned object without the public wire contract passing.
        try:
            candidate = parse_portia_record(
                candidate.contract,
                candidate.contract_version,
                candidate.to_dict(),
            )
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "migration destination is not independently valid"
            ) from exc
        _require_destination_lifecycle(source.record, candidate)
        _require_destination_provenance(
            candidate,
            effective_at=effective_at,
            created_by=validated_created_by,
        )

        try:
            equivalent = registration.semantic_equivalence(source.record, candidate)
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                "registered migration semantic-equivalence policy failed"
            ) from exc
        if equivalent is not True:
            raise WorkflowPrerequisiteError(
                "migration destination failed semantic-equivalence validation"
            )

        destination_updated = _updated_at(candidate, "migration destination")
        return MigrationPlan(
            source_reference=reference,
            destination_reference=_destination_reference(reference, destination),
            source=source,
            destination=candidate,
            source_observed_updated_at=source_updated_text,
            destination_observed_updated_at=destination_updated,
            transformer_id=registration.spec.transformer_id,
            transformer_version=registration.spec.transformer_version,
            reason_category=registration.spec.reason_category,
            reason_code=registration.spec.reason_code,
            reason_detail=reason_detail,
            effective_at=effective_at,
            created_by=MappingProxyType(validated_created_by),
        )

    def _revalidate_commit_plan(self, plan: MigrationPlan) -> MigrationPlan:
        """Re-run registered planning authority before a new mutation begins."""
        if not isinstance(plan.source_reference, ExactPortiaWorkRecordRef) or not isinstance(
            plan.destination_reference,
            ExactPortiaWorkRecordRef,
        ):
            raise WorkflowOwnershipError(
                "Slice 22 journaled commit supports work-record migrations only"
            )
        regenerated = self.plan_migration(
            plan.source_reference,
            plan.destination_reference.record_ref.contract_version,
            effective_at=plan.effective_at,
            created_by=plan.created_by,
            reason_detail=plan.reason_detail,
        )
        return regenerated

    def commit_migration(
        self,
        plan: MigrationPlan,
        *,
        migration_id: str,
        transition_id: str,
        created_at: str,
        operation_id: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> OperationCommitResult:
        """Commit one validated work-record migration through journaled persistence.

        Slice 22 intentionally fails closed when the exact source already has
        lifecycle transition or lifecycle-history correction evidence.  Later
        slices extend migration over selected historical branches.
        """
        from portia.workflows.migration_commit import (
            RecordMigrationCommitCoordinator,
        )

        coordinator = RecordMigrationCommitCoordinator(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )
        return coordinator.commit(
            plan,
            migration_id=migration_id,
            transition_id=transition_id,
            created_at=created_at,
            operation_id=operation_id,
            fault_hook=fault_hook,
            plan_validator=self._revalidate_commit_plan,
        )
