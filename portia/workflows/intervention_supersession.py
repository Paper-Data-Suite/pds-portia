"""Exact correction/adaptation supersession rules for ``intervention@1`` plans."""

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

INTERVENTION_CORRECTION_REASONS = frozenset(
    {
        "strategy_corrected",
        "target_corrected",
        "provider_corrected",
        "need_link_corrected",
        "goal_link_corrected",
        "schedule_corrected",
        "monitoring_corrected",
        "other",
    }
)
_RESERVED_INTERVENTION_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_INTERVENTION_MATERIAL_FIELDS = (
    "target",
    "need_refs",
    "goal_refs",
    "strategy",
    "provider_plan",
    "schedule",
    "monitoring_approach",
)
_INTERVENTION_CORRECTION_FIELDS = {
    "strategy_corrected": ("strategy",),
    "target_corrected": ("target",),
    "provider_corrected": ("provider_plan",),
    "need_link_corrected": ("need_refs",),
    "goal_link_corrected": ("goal_refs",),
    "schedule_corrected": ("schedule",),
    "monitoring_corrected": ("monitoring_approach",),
}


@dataclass(frozen=True, slots=True)
class InterventionSupersessionResolution:
    """One exact Intervention predecessor resolved without following successors."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_intervention_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "intervention"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Intervention supersession requires exact support_process@1 ownership"
        )


def _supersession_entry(successor: PortiaRecord) -> Mapping[str, object]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "Intervention correction/adaptation requires exactly one supersedes predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Intervention supersession entry is malformed")
    return entry


def _supersession_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Intervention supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Intervention supersession reason 'other' requires bounded detail"
            )
    return reason


def _selected_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], str]:
    _require_intervention_owner(work, successor)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Intervention successor predecessor does not belong to the selected process"
        )
    if (
        predecessor.record_ref.record_kind != "intervention"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Intervention successor requires an exact intervention@1 predecessor"
        )
    entry = _supersession_entry(successor)
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Intervention supersession predecessor reference is malformed"
        )
    selected = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Intervention successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Intervention correction/adaptation must use a new canonical identity"
        )
    return entry, _supersession_reason(entry)


def require_exact_intervention_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and one ordinary material correction reason."""
    _entry, reason = _selected_predecessor(work, predecessor, successor)
    if reason == "plan_adapted":
        raise WorkflowPrerequisiteError(
            "plan_adapted requires Intervention adapt(), not correction"
        )
    if reason in _RESERVED_INTERVENTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"Intervention supersession reason {reason!r} requires a dedicated later path"
        )
    if reason not in INTERVENTION_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Intervention correction reason {reason!r}"
        )
    return reason


def require_exact_intervention_adaptation_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and the prospective plan_adapted reason."""
    _entry, reason = _selected_predecessor(work, predecessor, successor)
    if reason != "plan_adapted":
        raise WorkflowPrerequisiteError(
            "Intervention adapt() requires supersession reason 'plan_adapted'"
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
        for field in _INTERVENTION_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def _require_successor_state_preserved(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> None:
    if prior.status not in {"proposed", "active"} or successor.status != prior.status:
        raise WorkflowPrerequisiteError(
            "Intervention successor must preserve proposed/active canonical status"
        )
    if prior.field("plan_state") != successor.field("plan_state"):
        raise WorkflowPrerequisiteError(
            "Intervention correction/adaptation cannot smuggle plan_state progression"
        )


def require_material_intervention_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require a recording-error correction to change the matching plan fact."""
    if prior.contract != "intervention" or successor.contract != "intervention":
        raise WorkflowOwnershipError("Intervention correction requires intervention@1 records")
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError("Intervention correction requires intervention@1 records")
    _require_successor_state_preserved(prior, successor)
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Intervention correction requires an actual material plan fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _INTERVENTION_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Intervention correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Intervention correction reason {supersession_reason!r} does not match "
            "the corrected plan fact"
        )


def require_material_intervention_adaptation(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> None:
    """Require a prospective material plan change without plan-state progression."""
    if prior.contract != "intervention" or successor.contract != "intervention":
        raise WorkflowOwnershipError("Intervention adaptation requires intervention@1 records")
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError("Intervention adaptation requires intervention@1 records")
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "Intervention adaptation requires active predecessor and successor"
        )
    if prior.field("plan_state") in {"completed", "discontinued"}:
        raise WorkflowPrerequisiteError(
            "terminal Intervention plan_state cannot receive prospective adaptation"
        )
    if prior.field("plan_state") != successor.field("plan_state"):
        raise WorkflowPrerequisiteError(
            "Intervention adaptation cannot smuggle plan_state progression"
        )
    if not _changed_material_fields(prior, successor):
        raise WorkflowPrerequisiteError(
            "Intervention adaptation requires an actual prospective material plan change"
        )


def superseded_intervention_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the superseded predecessor by changing lifecycle metadata only."""
    _require_successor_state_preserved(prior, successor)
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Intervention successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("intervention", "1", data)


def intervention_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    """Return optional bounded supersession detail for lifecycle provenance."""
    entry = _supersession_entry(successor)
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Intervention supersession detail must be bounded non-empty text"
        )
    return detail


def intervention_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[InterventionSupersessionResolution, ...]:
    """Resolve exact one-predecessor Intervention lineage without successor following."""
    _require_intervention_owner(work, successor)
    values = successor.field("supersedes")
    if values is None:
        return ()
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "current Intervention successor requires exactly one predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Intervention supersession entry is malformed")
    reason = _supersession_reason(entry)
    if reason not in INTERVENTION_CORRECTION_REASONS | {"plan_adapted"}:
        raise WorkflowPrerequisiteError(
            f"Intervention current-use lineage does not intervention reason {reason!r}"
        )
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Intervention supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            "ordinary Intervention supersession lineage cannot cross Support Processes"
        )
    if (
        reference.record_ref.record_kind != "intervention"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Intervention supersession predecessor must name intervention@1"
        )
    if reference.record_ref.record_id == successor.logical_id:
        raise WorkflowPrerequisiteError("Intervention cannot supersede itself")
    stored = repository.load_work_record(
        work,
        "intervention",
        "1",
        reference.record_ref.record_id,
    )
    return (InterventionSupersessionResolution(work_ref=work, stored=stored),)


def intervention_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    intervention: PortiaRecord,
) -> tuple[InterventionSupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without following successors."""
    values: list[InterventionSupersessionResolution] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(record: PortiaRecord) -> None:
        for resolution in intervention_supersession_records(repository, work, record):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Intervention supersession predecessor has no canonical identity"
                )
            if identifier in visiting:
                raise WorkflowPrerequisiteError(
                    "Intervention supersession ancestry contains a cycle"
                )
            if identifier in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Intervention supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(identifier)
            values.append(resolution)
            visit(resolution.stored.record)
            visiting.remove(identifier)
            visited.add(identifier)

    visit(intervention)
    return tuple(values)


def require_intervention_supersession_effective(
    predecessors: tuple[InterventionSupersessionResolution, ...],
) -> None:
    """Require every exact predecessor in current lineage to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Intervention successor requires its exact predecessor superseded"
            )
