"""Exact material-correction supersession rules for Communications."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.action_common import require_action_owner
from portia.workflows.communication_common import (
    require_current_communication_record_owner,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_ORDINARY_CORRECTION_REASONS = frozenset(
    {
        "sender_corrected",
        "recipient_corrected",
        "method_corrected",
        "purpose_corrected",
        "timing_corrected",
        "content_summary_corrected",
        "attachment_corrected",
        "relation_corrected",
        "privacy_scope_corrected",
        "other",
    }
)
_NON_MATERIAL_CORRECTION_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_COMMUNICATION_MATERIAL_FIELDS = (
    "sender",
    "recipients",
    "method",
    "purpose",
    "act_state",
    "privacy_scope",
    "started_at",
    "ended_at",
    "summary",
    "attachments",
    "relations",
)
_COMMUNICATION_CORRECTION_FIELDS = {
    "sender_corrected": ("sender",),
    "recipient_corrected": ("recipients",),
    "method_corrected": ("method",),
    "purpose_corrected": ("purpose",),
    "timing_corrected": ("act_state", "started_at", "ended_at"),
    "content_summary_corrected": ("summary",),
    "attachment_corrected": ("attachments",),
    "relation_corrected": ("relations",),
    "privacy_scope_corrected": ("privacy_scope",),
}


@dataclass(frozen=True, slots=True)
class CommunicationSupersessionResolution:
    """One exact historical Communication predecessor and its owning work."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _supersession_values(successor: PortiaRecord) -> tuple[object, ...]:
    values = successor.field("supersedes")
    if values is None:
        return ()
    if not isinstance(values, tuple):
        raise WorkflowOwnershipError("Communication supersedes collection is malformed")
    return values


def _supersession_entry(successor: PortiaRecord) -> Mapping[str, object]:
    values = _supersession_values(successor)
    if len(values) != 1:
        raise WorkflowPrerequisiteError(
            "material Communication correction requires exactly one "
            "supersedes predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Communication supersession entry is malformed")
    return entry


def communication_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[CommunicationSupersessionResolution, ...]:
    """Resolve exact predecessors after validating the frozen v1 topology."""
    require_current_communication_record_owner(work, successor)
    values = _supersession_values(successor)
    if not values:
        return ()

    references: list[ExactPortiaWorkRecordRef] = []
    seen: set[tuple[str, str, str, str]] = set()
    reasons: set[str] = set()
    accepted_reasons = _ORDINARY_CORRECTION_REASONS | _NON_MATERIAL_CORRECTION_REASONS
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(
                "Communication supersession entry is malformed"
            )
        raw_reference = value.get("work_record_ref")
        if not isinstance(raw_reference, Mapping):
            raise WorkflowOwnershipError(
                "Communication supersession predecessor reference is malformed"
            )
        reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
        require_action_owner(reference.work_ref, contract="communication")
        if (
            reference.record_ref.record_kind != "communication"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Communication supersession predecessor must name communication@1"
            )
        key = (
            reference.work_ref.class_id,
            reference.work_ref.work_id,
            reference.record_ref.record_id,
            reference.record_ref.contract_version,
        )
        if key in seen:
            raise WorkflowPrerequisiteError(
                "Communication supersession repeats one logical predecessor identity"
            )
        seen.add(key)
        reason = value.get("reason")
        if not isinstance(reason, str):
            raise WorkflowOwnershipError(
                "Communication supersession reason is malformed"
            )
        if reason not in accepted_reasons:
            raise WorkflowPrerequisiteError(
                f"unsupported Communication supersession reason {reason!r}"
            )
        reasons.add(reason)
        if reason == "other":
            detail = value.get("detail")
            if not isinstance(detail, str) or not detail.strip():
                raise WorkflowPrerequisiteError(
                    "Communication supersession reason 'other' requires bounded detail"
                )
        references.append(reference)

    if len(reasons) != 1:
        raise WorkflowPrerequisiteError(
            "one Communication successor must use one uniform supersession reason"
        )
    reason = next(iter(reasons))

    # Frozen Issue #17 topology is checked before predecessor I/O.
    for reference in references:
        same_work = reference.work_ref == work
        same_id = reference.record_ref.record_id == successor.logical_id
        if same_work and same_id and reason != "contract_migrated":
            raise WorkflowPrerequisiteError("Communication cannot supersede itself")
        if reason == "work_root_corrected":
            if same_work:
                raise WorkflowPrerequisiteError(
                    "work-root Communication correction requires a different work"
                )
            if not same_id:
                raise WorkflowPrerequisiteError(
                    "work-root Communication correction must preserve "
                    "Communication identity"
                )
        elif reason != "contract_migrated" and not same_work:
            raise WorkflowPrerequisiteError(
                "ordinary Communication correction cannot cross work roots"
            )

    if reason == "duplicate_consolidated":
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "Communication duplicate consolidation requires multiple predecessors"
            )
    elif reason != "contract_migrated" and len(references) != 1:
        raise WorkflowPrerequisiteError(
            "non-consolidation Communication correction requires one predecessor"
        )

    resolved: list[CommunicationSupersessionResolution] = []
    for reference in references:
        stored = repository.load_work_record(
            reference.work_ref,
            "communication",
            "1",
            reference.record_ref.record_id,
        )
        # Current Issue #43 executable ancestry remains Event-owned.
        require_current_communication_record_owner(reference.work_ref, stored.record)
        if stored.record.logical_id != reference.record_ref.record_id:
            raise WorkflowOwnershipError(
                "resolved Communication predecessor identity does not match "
                "exact reference"
            )
        resolved.append(
            CommunicationSupersessionResolution(
                work_ref=reference.work_ref,
                stored=stored,
            )
        )
    return tuple(resolved)


def communication_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    communication: PortiaRecord,
) -> tuple[CommunicationSupersessionResolution, ...]:
    """Resolve bounded exact supersession ancestry without following successors."""
    values: list[CommunicationSupersessionResolution] = []
    visited: set[tuple[str, str, str]] = set()
    visiting: set[tuple[str, str, str]] = set()

    def visit(selected_work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
        for resolution in communication_supersession_records(
            repository,
            selected_work,
            record,
        ):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Communication supersession predecessor has no canonical identity"
                )
            key = (
                resolution.work_ref.class_id,
                resolution.work_ref.work_id,
                identifier,
            )
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Communication supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Communication supersession ancestry exceeds the bounded "
                    "workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.work_ref, resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(work, communication)
    return tuple(values)


def require_communication_supersession_effective(
    predecessors: tuple[CommunicationSupersessionResolution, ...],
) -> None:
    """Require every exact predecessor in a current successor chain superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current corrected Communication requires its exact predecessor "
                "to be superseded"
            )


def require_exact_communication_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-work predecessor for ordinary material correction."""
    require_current_communication_record_owner(work, successor)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Communication correction predecessor does not belong to the selected work"
        )
    if (
        predecessor.record_ref.record_kind != "communication"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Communication correction requires an exact communication@1 predecessor"
        )

    entry = _supersession_entry(successor)
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Communication supersession predecessor reference is malformed"
        )
    selected = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Communication successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Communication material correction must use a new canonical identity"
        )

    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Communication supersession reason is malformed")
    if reason in _NON_MATERIAL_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"{reason} requires its dedicated consolidation/root/migration workflow"
        )
    if reason not in _ORDINARY_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Communication material correction reason {reason!r}"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Communication supersession reason 'other' requires bounded detail"
            )
    return reason


def require_material_communication_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the correction reason to match a substantive Communication change."""
    if prior.contract != "communication" or successor.contract != "communication":
        raise WorkflowOwnershipError(
            "material Communication correction requires communication@1 records"
        )
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError(
            "material Communication correction requires communication@1 records"
        )
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "material Communication correction requires active predecessor "
            "and successor"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _COMMUNICATION_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Communication correction requires an actual "
            "Communication fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _COMMUNICATION_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            "unsupported Communication material correction reason "
            f"{supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Communication supersession reason {supersession_reason!r} does not "
            "match the corrected fact"
        )


def communication_correction_lifecycle_reason(supersession_reason: str) -> str:
    """Preserve the accepted correction reason in lifecycle provenance."""
    return supersession_reason


def superseded_communication_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build a superseded predecessor by changing lifecycle metadata only."""
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "Communication predecessor supersession requires active predecessor "
            "and successor"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "corrected Communication successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("communication", "1", data)


def communication_correction_reason_detail(successor: PortiaRecord) -> str | None:
    """Return bounded correction detail for lifecycle provenance when present."""
    entry = _supersession_entry(successor)
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Communication supersession detail must be bounded non-empty text"
        )
    return detail
