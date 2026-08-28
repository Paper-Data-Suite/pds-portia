"""Shared, bounded mechanics for Event-family application services."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path

from portia.models import PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.validation import GraphValidationOptions, validate_record_graph
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)

EVENT_VERSION = "2"
PARTICIPANT_VERSION = "3"
ROLE_VERSION = "3"
RELATIONSHIP_VERSION = "2"

EVENT_STATUS_TRANSITIONS = {
    "draft": frozenset({"active", "cancelled"}),
    "active": frozenset({"closed", "invalidated", "superseded"}),
    "closed": frozenset({"active", "invalidated", "superseded"}),
    "cancelled": frozenset(),
    "invalidated": frozenset(),
    "superseded": frozenset(),
}
CHILD_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset(),
    "superseded": frozenset(),
}
_IMMUTABLE_CREATION_FIELDS = ("creation_source", "created_at", "created_by")


def exact_work_for(record: PortiaRecord) -> ExactPortiaWorkRef:
    if record.class_id is None or record.work_id is None:
        raise WorkflowOwnershipError("record does not declare an exact owning work")
    work_kind = record.work_kind if record.contract == "support_process" else "event"
    version = record.contract_version if record.contract in {"event", "support_process"} else EVENT_VERSION
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind=work_kind or "event",
        contract_version=version,
    )


def work_target(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {"kind": "work", "work_ref": work.to_dict()}


def record_target(
    work: ExactPortiaWorkRef, record: PortiaRecord
) -> dict[str, object]:
    if record.logical_id is None:
        raise WorkflowOwnershipError("record has no exact logical identity")
    reference = ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=record.contract,
            record_id=record.logical_id,
            contract_version=record.contract_version,
        ),
    )
    return {"kind": "work_record", "work_record_ref": reference.to_dict()}


def require_owned(record: PortiaRecord, work: ExactPortiaWorkRef) -> None:
    if record.class_id != work.class_id or record.work_id != work.work_id:
        raise WorkflowOwnershipError(
            "record does not belong to the explicitly selected Event work"
        )


def require_current_status(record: PortiaRecord) -> None:
    if record.status != "active":
        raise WorkflowPrerequisiteError(
            f"exact {record.contract} representation is not active for current use"
        )


def require_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transitions: Mapping[str, frozenset[str]],
    immutable_fields: Sequence[str] = (),
) -> None:
    """Enforce ordinary lifecycle and immutable creation facts before mutation."""
    if (
        prior.contract != candidate.contract
        or prior.contract_version != candidate.contract_version
        or prior.logical_id != candidate.logical_id
        or prior.class_id != candidate.class_id
        or prior.work_id != candidate.work_id
    ):
        raise WorkflowOwnershipError(
            "replacement does not preserve the exact canonical record identity"
        )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    for field in (*_IMMUTABLE_CREATION_FIELDS, *immutable_fields):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                f"ordinary replacement cannot rewrite immutable {field}"
            )
    prior_status = prior.status
    candidate_status = candidate.status
    if not isinstance(prior_status, str) or not isinstance(candidate_status, str):
        raise WorkflowPrerequisiteError("replacement record has no lifecycle status")
    if (
        prior_status != candidate_status
        and candidate_status not in transitions.get(prior_status, frozenset())
    ):
        raise WorkflowPrerequisiteError(
            f"illegal ordinary lifecycle transition: {prior_status} -> {candidate_status}"
        )
    prior_updated = prior_data.get("updated_at")
    candidate_updated = candidate_data.get("updated_at")
    if not isinstance(prior_updated, str) or not isinstance(candidate_updated, str):
        raise WorkflowPrerequisiteError("replacement update provenance is incomplete")

    def parsed(value: str) -> datetime:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        return datetime.fromisoformat(normalized)

    if parsed(candidate_updated) < parsed(prior_updated):
        raise WorkflowPrerequisiteError(
            "replacement updated_at cannot precede the selected canonical revision"
        )


class WorkflowServiceBase:
    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        quarantine: QuarantineGuard | None = None,
        context_assembler: WorkflowContextAssembler | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.quarantine = quarantine or QuarantineGuard(self.workspace_root)
        self.contexts = context_assembler or WorkflowContextAssembler(
            self.workspace_root
        )

    def validate_complete_graph(
        self,
        records: Sequence[PortiaRecord],
        *,
        require_actor_current_use: bool = False,
    ) -> None:
        context = self.contexts.assemble(
            records,
            require_actor_current_use=require_actor_current_use,
        )
        findings = validate_record_graph(
            records,
            context=context.validation,
            options=GraphValidationOptions(require_internal_resolution=True),
        )
        if findings:
            raise WorkflowValidationError(findings)


def participant_id_from_target(record: PortiaRecord) -> tuple[str, str]:
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("Role has no exact Participant target")
    ref = target.get("record_ref")
    if not isinstance(ref, Mapping):
        raise WorkflowOwnershipError("Role Participant target is malformed")
    kind = ref.get("record_kind")
    identifier = ref.get("record_id")
    version = ref.get("contract_version")
    if kind != "event_participant" or not isinstance(identifier, str) or not isinstance(version, str):
        raise WorkflowOwnershipError("Role does not name an exact Participant")
    return identifier, version


def records_only(values: Sequence[StoredRecord]) -> tuple[PortiaRecord, ...]:
    return tuple(item.record for item in values)
