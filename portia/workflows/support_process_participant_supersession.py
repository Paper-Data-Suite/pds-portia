"""Exact correction supersession rules for ``support_process_participant@1`` records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

SUPPORT_PROCESS_PARTICIPANT_CORRECTION_REASONS = frozenset(
    {
        "person_corrected",
        "contexts_corrected",
        "other",
    }
)
_RESERVED_SUPPORT_PROCESS_PARTICIPANT_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_SUPPORT_PROCESS_PARTICIPANT_MATERIAL_FIELDS = (
    "person",
    "contexts",
)
_SUPPORT_PROCESS_PARTICIPANT_CORRECTION_FIELDS = {
    "person_corrected": ("person",),
    "contexts_corrected": ("contexts",),
}


@dataclass(frozen=True, slots=True)
class SupportProcessParticipantSupersessionResolution:
    """One exact Support Process Participant predecessor resolved without successor following."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_support_process_participant_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "support_process_participant"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Support Process Participant supersession requires exact support_process@1 ownership"
        )


def _supersession_entry(successor: PortiaRecord) -> Mapping[str, object]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "Support Process Participant correction requires exactly one supersedes predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Support Process Participant supersession entry is malformed")
    return entry


def _supersession_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Support Process Participant supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Support Process Participant supersession reason 'other' requires bounded detail"
            )
    return reason


def _selected_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], str]:
    _require_support_process_participant_owner(work, successor)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Support Process Participant successor predecessor does not belong to selected process"
        )
    if (
        predecessor.record_ref.record_kind != "support_process_participant"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Support Process Participant successor requires an exact support_process_participant@1 predecessor"
        )
    entry = _supersession_entry(successor)
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Support Process Participant supersession predecessor reference is malformed"
        )
    selected = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if selected != predecessor:
        raise WorkflowPrerequisiteError(
            "Support Process Participant successor must name the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Support Process Participant correction must use a new canonical identity"
        )
    return entry, _supersession_reason(entry)


def require_exact_participant_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and one ordinary material correction reason."""
    _entry, reason = _selected_predecessor(work, predecessor, successor)
    if reason in _RESERVED_SUPPORT_PROCESS_PARTICIPANT_REASONS:
        raise WorkflowPrerequisiteError(
            f"Support Process Participant supersession reason {reason!r} requires a dedicated "
            "topology path"
        )
    if reason not in SUPPORT_PROCESS_PARTICIPANT_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Support Process Participant correction reason {reason!r}"
        )
    return reason


def _changed_material_fields(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> set[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    return {
        field
        for field in _SUPPORT_PROCESS_PARTICIPANT_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def require_material_participant_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require correction to change a bounded Participant fact matching its reason."""
    if prior.contract != "support_process_participant" or successor.contract != "support_process_participant":
        raise WorkflowOwnershipError(
            "Support Process Participant correction requires support_process_participant@1 records"
        )
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError(
            "Support Process Participant correction requires support_process_participant@1 records"
        )
    if prior.status not in {"proposed", "active"} or successor.status != prior.status:
        raise WorkflowPrerequisiteError(
            "Support Process Participant successor must preserve proposed/active canonical status"
        )
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Support Process Participant correction requires an actual material Participant fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _SUPPORT_PROCESS_PARTICIPANT_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Support Process Participant correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Support Process Participant correction reason {supersession_reason!r} does not match "
            "the corrected Participant fact"
        )


def superseded_participant_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the superseded predecessor by changing lifecycle metadata only."""
    if prior.status not in {"proposed", "active"} or successor.status != prior.status:
        raise WorkflowPrerequisiteError(
            "Support Process Participant successor must preserve proposed/active canonical status"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Support Process Participant successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("support_process_participant", "1", data)


def participant_supersession_reason_detail(
    successor: PortiaRecord,
) -> str | None:
    """Return optional bounded supersession detail for lifecycle provenance."""
    entry = _supersession_entry(successor)
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Support Process Participant supersession detail must be bounded non-empty text"
        )
    return detail


def participant_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[SupportProcessParticipantSupersessionResolution, ...]:
    """Resolve one-predecessor Participant lineage without successor following."""
    _require_support_process_participant_owner(work, successor)
    values = successor.field("supersedes")
    if values is None:
        return ()
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "current Support Process Participant successor requires exactly one predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Support Process Participant supersession entry is malformed")
    reason = _supersession_reason(entry)
    if reason not in SUPPORT_PROCESS_PARTICIPANT_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"Support Process Participant current-use lineage does not support reason {reason!r}"
        )
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Support Process Participant supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            "ordinary Support Process Participant supersession cannot cross Support Processes"
        )
    if (
        reference.record_ref.record_kind != "support_process_participant"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Support Process Participant supersession predecessor must name support_process_participant@1"
        )
    if reference.record_ref.record_id == successor.logical_id:
        raise WorkflowPrerequisiteError("Support Process Participant cannot supersede itself")
    stored = repository.load_work_record(
        work,
        "support_process_participant",
        "1",
        reference.record_ref.record_id,
    )
    return (SupportProcessParticipantSupersessionResolution(work_ref=work, stored=stored),)


def participant_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    participant: PortiaRecord,
) -> tuple[SupportProcessParticipantSupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without following successors."""
    values: list[SupportProcessParticipantSupersessionResolution] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(record: PortiaRecord) -> None:
        for resolution in participant_supersession_records(repository, work, record):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Support Process Participant supersession predecessor has no canonical identity"
                )
            if identifier in visiting:
                raise WorkflowPrerequisiteError(
                    "Support Process Participant supersession ancestry contains a cycle"
                )
            if identifier in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Support Process Participant supersession ancestry exceeds bounded workflow limit"
                )
            visiting.add(identifier)
            values.append(resolution)
            visit(resolution.stored.record)
            visiting.remove(identifier)
            visited.add(identifier)

    visit(participant)
    return tuple(values)


def require_participant_supersession_effective(
    predecessors: tuple[SupportProcessParticipantSupersessionResolution, ...],
) -> None:
    """Require every exact predecessor in current lineage to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Support Process Participant successor requires exact predecessor superseded"
            )
