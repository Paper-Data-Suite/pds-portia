"""Exact correction supersession rules for ``support_goal@1`` records."""

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

SUPPORT_GOAL_CORRECTION_REASONS = frozenset(
    {
        "target_corrected",
        "description_corrected",
        "criteria_corrected",
        "measurement_approach_corrected",
        "other",
    }
)
_RESERVED_SUPPORT_GOAL_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_SUPPORT_GOAL_MATERIAL_FIELDS = (
    "target",
    "description",
    "planned_criteria",
    "measurement_approach",
)
_SUPPORT_GOAL_CORRECTION_FIELDS = {
    "target_corrected": ("target",),
    "description_corrected": ("description",),
    "criteria_corrected": ("planned_criteria",),
    "measurement_approach_corrected": ("measurement_approach",),
}


@dataclass(frozen=True, slots=True)
class SupportGoalSupersessionResolution:
    """One exact Support Goal predecessor resolved without successor following."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_support_goal_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "support_goal"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Support Goal supersession requires exact support_process@1 ownership"
        )


def _supersession_entry(successor: PortiaRecord) -> Mapping[str, object]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "Support Goal correction requires exactly one supersedes predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Support Goal supersession entry is malformed")
    return entry


def _supersession_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Support Goal supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Support Goal supersession reason 'other' requires bounded detail"
            )
    return reason


def _selected_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], str]:
    _require_support_goal_owner(work, successor)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Support Goal successor predecessor does not belong to selected process"
        )
    if (
        predecessor.record_ref.record_kind != "support_goal"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Support Goal successor requires an exact support_goal@1 predecessor"
        )
    entry = _supersession_entry(successor)
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Support Goal supersession predecessor reference is malformed"
        )
    selected = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if selected != predecessor:
        raise WorkflowPrerequisiteError(
            "Support Goal successor must name the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Support Goal correction must use a new canonical identity"
        )
    return entry, _supersession_reason(entry)


def require_exact_support_goal_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and one ordinary material correction reason."""
    _entry, reason = _selected_predecessor(work, predecessor, successor)
    if reason in _RESERVED_SUPPORT_GOAL_REASONS:
        raise WorkflowPrerequisiteError(
            f"Support Goal supersession reason {reason!r} requires a dedicated "
            "topology path"
        )
    if reason not in SUPPORT_GOAL_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Support Goal correction reason {reason!r}"
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
        for field in _SUPPORT_GOAL_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def require_material_support_goal_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require correction to change a bounded Goal fact matching its reason."""
    if prior.contract != "support_goal" or successor.contract != "support_goal":
        raise WorkflowOwnershipError(
            "Support Goal correction requires support_goal@1 records"
        )
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError(
            "Support Goal correction requires support_goal@1 records"
        )
    if prior.status not in {"proposed", "active"} or successor.status != prior.status:
        raise WorkflowPrerequisiteError(
            "Support Goal successor must preserve proposed/active canonical status"
        )
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Support Goal correction requires an actual material Goal planning fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _SUPPORT_GOAL_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Support Goal correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Support Goal correction reason {supersession_reason!r} does not match "
            "the corrected Goal planning fact"
        )


def superseded_support_goal_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the superseded predecessor by changing lifecycle metadata only."""
    if prior.status not in {"proposed", "active"} or successor.status != prior.status:
        raise WorkflowPrerequisiteError(
            "Support Goal successor must preserve proposed/active canonical status"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Support Goal successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("support_goal", "1", data)


def support_goal_supersession_reason_detail(
    successor: PortiaRecord,
) -> str | None:
    """Return optional bounded supersession detail for lifecycle provenance."""
    entry = _supersession_entry(successor)
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Support Goal supersession detail must be bounded non-empty text"
        )
    return detail


def support_goal_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[SupportGoalSupersessionResolution, ...]:
    """Resolve one-predecessor Goal lineage without successor following."""
    _require_support_goal_owner(work, successor)
    values = successor.field("supersedes")
    if values is None:
        return ()
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "current Support Goal successor requires exactly one predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Support Goal supersession entry is malformed")
    reason = _supersession_reason(entry)
    if reason not in SUPPORT_GOAL_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"Support Goal current-use lineage does not support reason {reason!r}"
        )
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Support Goal supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            "ordinary Support Goal supersession cannot cross Support Processes"
        )
    if (
        reference.record_ref.record_kind != "support_goal"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Support Goal supersession predecessor must name support_goal@1"
        )
    if reference.record_ref.record_id == successor.logical_id:
        raise WorkflowPrerequisiteError("Support Goal cannot supersede itself")
    stored = repository.load_work_record(
        work,
        "support_goal",
        "1",
        reference.record_ref.record_id,
    )
    return (SupportGoalSupersessionResolution(work_ref=work, stored=stored),)


def support_goal_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    goal: PortiaRecord,
) -> tuple[SupportGoalSupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without following successors."""
    values: list[SupportGoalSupersessionResolution] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(record: PortiaRecord) -> None:
        for resolution in support_goal_supersession_records(repository, work, record):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Support Goal supersession predecessor has no canonical identity"
                )
            if identifier in visiting:
                raise WorkflowPrerequisiteError(
                    "Support Goal supersession ancestry contains a cycle"
                )
            if identifier in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Support Goal supersession ancestry exceeds bounded workflow limit"
                )
            visiting.add(identifier)
            values.append(resolution)
            visit(resolution.stored.record)
            visiting.remove(identifier)
            visited.add(identifier)

    visit(goal)
    return tuple(values)


def require_support_goal_supersession_effective(
    predecessors: tuple[SupportGoalSupersessionResolution, ...],
) -> None:
    """Require every exact predecessor in current lineage to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Support Goal successor requires exact predecessor superseded"
            )
