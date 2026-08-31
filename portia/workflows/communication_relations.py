"""Exact related-record authority for ``communication@1`` workflows."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_RELATION_KIND_REQUIREMENTS: dict[str, frozenset[str]] = {
    "responds_to": frozenset({"communication"}),
    "conveys_determination": frozenset({"determination"}),
    "documents_handoff_for": frozenset({"response"}),
    "relates_to_response": frozenset({"response"}),
    "account_from_communication": frozenset({"account"}),
}


def _communication_work(record: PortiaRecord) -> ExactPortiaWorkRef:
    class_id = record.class_id
    work_id = record.work_id
    work_kind = record.work_kind
    if class_id is None or work_id is None or work_kind is None:
        raise WorkflowOwnershipError("Communication has malformed owning work identity")
    if work_kind == "event":
        version = "2"
    elif work_kind == "support_process":
        version = "1"
    else:
        raise WorkflowOwnershipError("Communication has unsupported work kind")
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind=work_kind,
        contract_version=version,
    )


def communication_relations(
    record: PortiaRecord,
) -> tuple[Mapping[str, object], ...]:
    """Return bounded relation entries without changing their semantics."""
    value = record.field("relations")
    if value is None:
        return ()
    if not isinstance(value, tuple):
        raise WorkflowOwnershipError("Communication relations are malformed")
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise WorkflowOwnershipError("Communication relation entry is malformed")
        result.append(item)
    return tuple(result)


def _relation_reference(item: Mapping[str, object]) -> ExactPortiaWorkRecordRef:
    value = item.get("record_ref")
    try:
        return ExactPortiaWorkRecordRef.from_dict(value)
    except Exception as exc:
        raise WorkflowOwnershipError(
            "Communication relation exact record reference is malformed"
        ) from exc


def _same_work(left: ExactPortiaWorkRef, right: ExactPortiaWorkRef) -> bool:
    return (
        left.module_id == right.module_id
        and left.class_id == right.class_id
        and left.work_kind == right.work_kind
        and left.work_id == right.work_id
        and left.contract_version == right.contract_version
    )


def _is_self_relation(
    owner: ExactPortiaWorkRef,
    record: PortiaRecord,
    reference: ExactPortiaWorkRecordRef,
) -> bool:
    return (
        _same_work(owner, reference.work_ref)
        and reference.record_ref.record_kind == "communication"
        and reference.record_ref.record_id == record.logical_id
        and reference.record_ref.contract_version == record.contract_version
    )


def require_communication_relation_authority(
    repository: PortiaRepository,
    record: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Resolve exact relation targets without successor or current-use following."""
    owner = _communication_work(record)
    resolved: list[StoredRecord] = []
    seen: set[tuple[str, str, str, str, str, str, str]] = set()

    for item in communication_relations(record):
        relation = item.get("relation")
        if not isinstance(relation, str):
            raise WorkflowOwnershipError("Communication relation type is malformed")
        reference = _relation_reference(item)
        target_kind = reference.record_ref.record_kind

        expected = _RELATION_KIND_REQUIREMENTS.get(relation)
        if expected is not None and target_kind not in expected:
            raise WorkflowPrerequisiteError(
                f"{relation} relation requires an exact "
                f"{', '.join(sorted(expected))} record"
            )
        if _is_self_relation(owner, record, reference):
            raise WorkflowPrerequisiteError("Communication cannot relate to itself")
        if relation == "responds_to" and not _same_work(owner, reference.work_ref):
            raise WorkflowPrerequisiteError(
                "responds_to relation must remain within the owning work"
            )

        identity = (
            relation,
            reference.work_ref.class_id,
            reference.work_ref.work_kind,
            reference.work_ref.work_id,
            target_kind,
            reference.record_ref.record_id,
            reference.record_ref.contract_version,
        )
        if identity in seen:
            raise WorkflowPrerequisiteError(
                "Communication repeats the same logical related-record relation"
            )
        seen.add(identity)

        repository.load_work(reference.work_ref)
        resolved.append(
            repository.load_work_record(
                reference.work_ref,
                target_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        )

    return tuple(resolved)
