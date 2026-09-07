"""Shared exact supersession topology for Issue #46 downstream families."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.downstream_common import (
    DOWNSTREAM_CONTRACTS,
    DOWNSTREAM_VERSION,
    require_downstream_owner,
    require_downstream_record_owner,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

DOWNSTREAM_RESERVED_SUPERSESSION_REASONS: Final[frozenset[str]] = frozenset(
    {"duplicate_consolidated", "work_root_corrected", "contract_migrated"}
)
DOWNSTREAM_CORRECTION_REASONS: Final[Mapping[str, frozenset[str]]] = {
    "follow_up": frozenset(
        {
            "owner_corrected",
            "purpose_corrected",
            "target_corrected",
            "timing_corrected",
            "completion_corrected",
            "related_record_corrected",
            "other",
        }
    ),
    "outcome": frozenset(
        {
            "evaluator_corrected",
            "scope_corrected",
            "target_corrected",
            "timeframe_corrected",
            "basis_corrected",
            "result_corrected",
            "limitation_corrected",
            "summary_corrected",
            "other",
        }
    ),
    "reentry": frozenset(
        {
            "coordinator_corrected",
            "target_corrected",
            "context_corrected",
            "timing_corrected",
            "plan_element_corrected",
            "completion_corrected",
            "other",
        }
    ),
    "repair": frozenset(
        {
            "facilitator_corrected",
            "participant_corrected",
            "focus_corrected",
            "agreement_corrected",
            "completion_corrected",
            "other",
        }
    ),
}

_FOLLOW_UP_MATERIAL_FIELDS: Final[tuple[str, ...]] = (
    "target",
    "owner",
    "purpose",
    "planned_timing",
    "workflow_state",
    "completed_at",
    "related_records",
    "disposition",
)
_FOLLOW_UP_CORRECTION_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "owner_corrected": ("owner",),
    "purpose_corrected": ("purpose",),
    "target_corrected": ("target",),
    "timing_corrected": ("planned_timing",),
    "completion_corrected": (
        "workflow_state",
        "completed_at",
        "disposition",
    ),
    "related_record_corrected": ("related_records",),
}

_OUTCOME_MATERIAL_FIELDS: Final[tuple[str, ...]] = (
    "target",
    "evaluator",
    "scope",
    "timeframe",
    "basis",
    "result",
    "result_detail",
    "limitations",
    "summary",
)
_OUTCOME_CORRECTION_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "evaluator_corrected": ("evaluator",),
    "scope_corrected": ("scope",),
    "target_corrected": ("target",),
    "timeframe_corrected": ("timeframe",),
    "basis_corrected": ("basis",),
    "result_corrected": ("result", "result_detail"),
    "limitation_corrected": ("limitations",),
    "summary_corrected": ("summary",),
}


_REENTRY_MATERIAL_FIELDS: Final[tuple[str, ...]] = (
    "target",
    "coordinator",
    "initiating_context",
    "planned_return",
    "planned_elements",
    "support_refs",
    "workflow_state",
    "completed_at",
)
_REENTRY_CORRECTION_FIELDS: Final[Mapping[str, tuple[str, ...]]] = {
    "coordinator_corrected": ("coordinator",),
    "target_corrected": ("target",),
    "context_corrected": ("initiating_context",),
    "timing_corrected": ("planned_return",),
    "plan_element_corrected": ("planned_elements", "support_refs"),
    "completion_corrected": ("workflow_state", "completed_at"),
}


_REPAIR_MATERIAL_FIELDS: Final[tuple[str, ...]] = (
    "facilitator",
    "participants",
    "focus",
    "actions",
    "workflow_state",
    "completed_at",
)
_REPAIR_AGREEMENT_ACTION_FIELDS: Final[tuple[str, ...]] = (
    "action_key",
    "action_type",
    "type_detail",
    "description",
    "agreed_by",
    "responsible_participant_keys",
    "agreed_at",
)
_REPAIR_COMPLETION_ACTION_FIELDS: Final[tuple[str, ...]] = (
    "action_key",
    "completion_state",
    "completed_at",
)


@dataclass(frozen=True, slots=True)
class DownstreamSupersessionResolution:
    """One exact downstream predecessor resolved without following successors."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def downstream_correction_reasons(contract: str) -> frozenset[str]:
    """Return the frozen ordinary correction vocabulary for one downstream family."""
    try:
        return DOWNSTREAM_CORRECTION_REASONS[contract]
    except KeyError as exc:
        raise WorkflowOwnershipError(
            f"unsupported Issue #46 downstream contract {contract!r}"
        ) from exc


def downstream_supersession_reason_detail(
    successor: PortiaRecord,
) -> str | None:
    """Return bounded uniform supersession detail when one is present."""
    entries = _supersession_entries(successor)
    details = {
        entry.get("detail")
        for entry in entries
        if entry.get("detail") is not None
    }
    if not details:
        return None
    if len(details) != 1:
        raise WorkflowPrerequisiteError(
            f"{successor.contract} supersession detail must be uniform"
        )
    detail = next(iter(details))
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            f"{successor.contract} supersession detail must be bounded non-empty text"
        )
    return detail


def _require_family_reference(
    reference: ExactPortiaWorkRecordRef,
    *,
    contract: str,
) -> None:
    require_downstream_owner(reference.work_ref)
    if (
        reference.record_ref.record_kind != contract
        or reference.record_ref.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            f"{contract} supersession predecessor must name exact {contract}@1"
        )


def _supersession_entries(
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], ...]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or not values:
        raise WorkflowPrerequisiteError(
            f"{successor.contract} correction requires supersession history"
        )
    entries: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(
                f"{successor.contract} supersession entry is malformed"
            )
        entries.append(value)
    return tuple(entries)


def _supersession_reason(
    successor: PortiaRecord,
    entry: Mapping[str, object],
) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError(
            f"{successor.contract} supersession reason is malformed"
        )
    allowed = (
        downstream_correction_reasons(successor.contract)
        | DOWNSTREAM_RESERVED_SUPERSESSION_REASONS
    )
    if reason not in allowed:
        raise WorkflowPrerequisiteError(
            f"unsupported {successor.contract} supersession reason {reason!r}"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                f"{successor.contract} supersession reason 'other' "
                "requires bounded detail"
            )
    return reason


def _entry_reference(
    successor: PortiaRecord,
    entry: Mapping[str, object],
) -> ExactPortiaWorkRecordRef:
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            f"{successor.contract} supersession predecessor reference is malformed"
        )
    try:
        reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    except (TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(
            f"{successor.contract} supersession predecessor reference is malformed"
        ) from exc
    _require_family_reference(reference, contract=successor.contract)
    if reference.work_ref.class_id != successor.class_id:
        raise WorkflowOwnershipError(
            f"{successor.contract} supersession cannot cross class boundaries"
        )
    return reference


def downstream_supersession_topology(
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...]]:
    """Validate uniform exact predecessor topology for one downstream successor."""
    if (
        successor.contract not in DOWNSTREAM_CONTRACTS
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "downstream supersession requires a v1 Issue #46 record"
        )
    entries = _supersession_entries(successor)
    reasons = tuple(_supersession_reason(successor, entry) for entry in entries)
    if len(set(reasons)) != 1:
        raise WorkflowPrerequisiteError(
            f"mixed {successor.contract} supersession reasons"
        )
    reason = reasons[0]
    references = tuple(_entry_reference(successor, entry) for entry in entries)
    if len(set(references)) != len(references):
        raise WorkflowPrerequisiteError(
            f"{successor.contract} supersession repeats a predecessor identity"
        )

    successor_id = successor.logical_id
    class_id = successor.class_id
    work_id = successor.work_id
    work_kind = successor.work_kind
    if (
        successor_id is None
        or class_id is None
        or work_id is None
        or work_kind not in {"event", "support_process"}
    ):
        raise WorkflowOwnershipError(
            f"{successor.contract} successor has incomplete owner identity"
        )
    successor_work = ExactPortiaWorkRef(
        class_id=class_id,
        work_id=work_id,
        work_kind=work_kind,
        contract_version="2" if work_kind == "event" else "1",
    )
    require_downstream_owner(successor_work)

    if reason == "duplicate_consolidated":
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                f"duplicate consolidation needs two {successor.contract} predecessors"
            )
        if any(reference.work_ref != successor_work for reference in references):
            raise WorkflowPrerequisiteError(
                f"{successor.contract} duplicate consolidation cannot cross work roots"
            )
        if any(
            reference.record_ref.record_id == successor_id
            for reference in references
        ):
            raise WorkflowPrerequisiteError(
                f"{successor.contract} cannot supersede itself"
            )
        return reason, references

    if reason == "work_root_corrected":
        if len(references) != 1:
            raise WorkflowPrerequisiteError(
                f"work-root {successor.contract} correction is one-to-one"
            )
        predecessor = references[0]
        if predecessor.work_ref == successor_work:
            raise WorkflowPrerequisiteError(
                "work-root correction requires a different owner work"
            )
        if predecessor.record_ref.record_id != successor_id:
            raise WorkflowPrerequisiteError(
                f"work-root correction must preserve {successor.contract} identity"
            )
        return reason, references

    if reason == "contract_migrated":
        if len(references) != 1:
            raise WorkflowPrerequisiteError(
                f"{successor.contract} contract migration is one-to-one"
            )
        return reason, references

    if len(references) != 1:
        raise WorkflowPrerequisiteError(
            f"ordinary {successor.contract} correction is one-to-one"
        )
    selected = references[0]
    if selected.work_ref != successor_work:
        raise WorkflowPrerequisiteError(
            f"ordinary {successor.contract} correction cannot cross work roots"
        )
    if selected.record_ref.record_id == successor_id:
        raise WorkflowPrerequisiteError(
            f"{successor.contract} cannot supersede itself"
        )
    return reason, references


def require_exact_downstream_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-work predecessor for an ordinary correction."""
    require_downstream_record_owner(work, successor, contract=successor.contract)
    _require_family_reference(predecessor, contract=successor.contract)
    reason, references = downstream_supersession_topology(successor)
    if reason == "work_root_corrected":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} work-root correction requires a dedicated "
            "ownership path"
        )
    if reason == "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} duplicate consolidation requires a dedicated "
            "consolidation path"
        )
    if reason == "contract_migrated":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} contract migration requires a dedicated "
            "migration path"
        )
    if reason not in downstream_correction_reasons(successor.contract):
        raise WorkflowPrerequisiteError(
            f"unsupported {successor.contract} correction reason {reason!r}"
        )
    selected = references[0]
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            f"selected {successor.contract} predecessor does not belong to "
            "the selected work"
        )
    if selected != predecessor:
        raise WorkflowOwnershipError(
            f"{successor.contract} successor must supersede the exact "
            "selected predecessor"
        )
    return reason


def require_material_follow_up_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the correction reason to match a substantive Follow-Up fact change."""
    if (
        prior.contract != "follow_up"
        or successor.contract != "follow_up"
        or prior.contract_version != DOWNSTREAM_VERSION
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "material Follow-Up correction requires follow_up@1 records"
        )
    if prior.status == "superseded":
        raise WorkflowPrerequisiteError(
            "material Follow-Up correction cannot reuse a superseded predecessor"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Follow-Up successor must be active"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _FOLLOW_UP_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Follow-Up correction requires an actual Follow-Up fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _FOLLOW_UP_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Follow-Up material correction reason "
            f"{supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Follow-Up supersession reason {supersession_reason!r} "
            "does not match the corrected fact"
        )


def require_material_outcome_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the correction reason to match one substantive Outcome fact change."""
    if (
        prior.contract != "outcome"
        or successor.contract != "outcome"
        or prior.contract_version != DOWNSTREAM_VERSION
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "material Outcome correction requires outcome@1 records"
        )
    if prior.status == "superseded":
        raise WorkflowPrerequisiteError(
            "material Outcome correction cannot reuse a superseded predecessor"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Outcome successor must be active"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _OUTCOME_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Outcome correction requires an actual Outcome fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _OUTCOME_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Outcome material correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Outcome supersession reason {supersession_reason!r} "
            "does not match the corrected fact"
        )


def require_material_reentry_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the reason to match one substantive Reentry fact correction."""
    if (
        prior.contract != "reentry"
        or successor.contract != "reentry"
        or prior.contract_version != DOWNSTREAM_VERSION
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "material Reentry correction requires reentry@1 records"
        )
    if prior.status == "superseded":
        raise WorkflowPrerequisiteError(
            "material Reentry correction cannot reuse a superseded predecessor"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Reentry successor must be active"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _REENTRY_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Reentry correction requires an actual Reentry fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _REENTRY_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Reentry material correction reason "
            f"{supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Reentry supersession reason {supersession_reason!r} "
            "does not match the corrected fact"
        )


def _repair_action_projection(
    record: PortiaRecord,
    fields: tuple[str, ...],
) -> tuple[tuple[object, ...], ...]:
    values = record.field("actions")
    if values is None:
        return ()
    if not isinstance(values, Sequence) or isinstance(
        values, (str, bytes, bytearray)
    ):
        raise WorkflowOwnershipError("Repair actions are malformed")
    projected: list[tuple[object, ...]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError("Repair action is malformed")
        projected.append(tuple(value.get(field) for field in fields))
    return tuple(projected)


def require_material_repair_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the reason to match one substantive Repair fact correction."""
    if (
        prior.contract != "repair"
        or successor.contract != "repair"
        or prior.contract_version != DOWNSTREAM_VERSION
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "material Repair correction requires repair@1 records"
        )
    if prior.status == "superseded":
        raise WorkflowPrerequisiteError(
            "material Repair correction cannot reuse a superseded predecessor"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Repair successor must be active"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _REPAIR_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Repair correction requires an actual Repair fact change"
        )
    if supersession_reason == "other":
        return

    matches = False
    if supersession_reason == "facilitator_corrected":
        matches = "facilitator" in changed
    elif supersession_reason == "participant_corrected":
        matches = "participants" in changed
    elif supersession_reason == "focus_corrected":
        matches = "focus" in changed
    elif supersession_reason == "agreement_corrected":
        matches = _repair_action_projection(
            prior,
            _REPAIR_AGREEMENT_ACTION_FIELDS,
        ) != _repair_action_projection(
            successor,
            _REPAIR_AGREEMENT_ACTION_FIELDS,
        )
    elif supersession_reason == "completion_corrected":
        matches = bool({"workflow_state", "completed_at"} & changed) or (
            _repair_action_projection(
                prior,
                _REPAIR_COMPLETION_ACTION_FIELDS,
            )
            != _repair_action_projection(
                successor,
                _REPAIR_COMPLETION_ACTION_FIELDS,
            )
        )
    else:
        raise WorkflowPrerequisiteError(
            f"unsupported Repair material correction reason "
            f"{supersession_reason!r}"
        )
    if not matches:
        raise WorkflowPrerequisiteError(
            f"Repair supersession reason {supersession_reason!r} "
            "does not match the corrected fact"
        )


def require_duplicate_downstream_consolidation_predecessors(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRecordRef, ...]:
    """Require one same-work multi-predecessor duplicate consolidation graph."""
    require_downstream_record_owner(work, successor, contract=successor.contract)
    reason, references = downstream_supersession_topology(successor)
    if reason != "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} consolidation requires supersession reason "
            "'duplicate_consolidated'"
        )
    if any(reference.work_ref != work for reference in references):
        raise WorkflowPrerequisiteError(
            f"{successor.contract} duplicate consolidation cannot cross work roots"
        )
    return references


def require_downstream_work_root_correction_predecessor(
    destination_work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> ExactPortiaWorkRef:
    """Require one exact cross-work ownership-correction predecessor."""
    require_downstream_record_owner(
        destination_work,
        successor,
        contract=successor.contract,
    )
    _require_family_reference(predecessor, contract=successor.contract)
    reason, references = downstream_supersession_topology(successor)
    if reason != "work_root_corrected":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} ownership correction requires supersession "
            "reason 'work_root_corrected'"
        )
    selected = references[0]
    if selected != predecessor:
        raise WorkflowOwnershipError(
            f"{successor.contract} work-root successor must supersede the exact "
            "selected predecessor"
        )
    if predecessor.work_ref == destination_work:
        raise WorkflowPrerequisiteError(
            "work-root correction requires a different owner work"
        )
    return predecessor.work_ref


def superseded_downstream_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build a superseded predecessor by changing lifecycle metadata only."""
    if (
        prior.contract != successor.contract
        or prior.contract not in DOWNSTREAM_CONTRACTS
        or prior.contract_version != DOWNSTREAM_VERSION
        or successor.contract_version != DOWNSTREAM_VERSION
    ):
        raise WorkflowOwnershipError(
            "downstream supersession requires one exact v1 record family"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            f"{successor.contract} successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record(prior.contract, DOWNSTREAM_VERSION, data)


def downstream_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[DownstreamSupersessionResolution, ...]:
    """Resolve exact predecessor records without following any successor."""
    require_downstream_record_owner(work, successor, contract=successor.contract)
    if successor.field("supersedes") is None:
        return ()
    reason, references = downstream_supersession_topology(successor)
    if reason == "contract_migrated":
        raise WorkflowPrerequisiteError(
            f"{successor.contract} migration lineage requires the dedicated "
            "migration service"
        )
    return tuple(
        DownstreamSupersessionResolution(
            work_ref=reference.work_ref,
            stored=repository.load_work_record(
                reference.work_ref,
                successor.contract,
                DOWNSTREAM_VERSION,
                reference.record_ref.record_id,
            ),
        )
        for reference in references
    )


def downstream_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[DownstreamSupersessionResolution, ...]:
    """Resolve bounded exact ancestry without following any successor pointers."""
    values: list[DownstreamSupersessionResolution] = []
    visited: set[tuple[str, str, str, str, str]] = set()
    visiting: set[tuple[str, str, str, str, str]] = set()

    def visit(selected_work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
        for resolution in downstream_supersession_records(
            repository,
            selected_work,
            record,
        ):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "downstream supersession predecessor has no canonical identity"
                )
            key = (
                resolution.work_ref.class_id,
                resolution.work_ref.work_kind,
                resolution.work_ref.work_id,
                record.contract,
                identifier,
            )
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "downstream supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "downstream supersession ancestry exceeds the bounded "
                    "workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.work_ref, resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(work, successor)
    return tuple(values)


def require_downstream_supersession_effective(
    predecessors: Sequence[DownstreamSupersessionResolution],
) -> None:
    """Require each exact predecessor selected for current use to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current downstream successor requires each exact predecessor "
                "to be superseded"
            )
