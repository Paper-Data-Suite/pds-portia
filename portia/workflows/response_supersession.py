"""Exact material-correction supersession rules for Event-local Responses."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.action_common import require_action_owner
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.response_common import require_response_record_owner

_ORDINARY_CORRECTION_REASONS = frozenset(
    {
        "provider_corrected",
        "target_corrected",
        "action_corrected",
        "timing_corrected",
        "decision_context_corrected",
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
_RESPONSE_MATERIAL_FIELDS = (
    "target",
    "provider",
    "action",
    "execution_state",
    "started_at",
    "ended_at",
    "review_ref",
    "determination_ref",
)


@dataclass(frozen=True, slots=True)
class ResponseSupersessionResolution:
    """One exact historical predecessor and the work that owns it."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


_RESPONSE_CORRECTION_FIELDS = {
    "provider_corrected": ("provider",),
    "target_corrected": ("target",),
    "action_corrected": ("action",),
    "timing_corrected": ("execution_state", "started_at", "ended_at"),
    "decision_context_corrected": ("review_ref", "determination_ref"),
}


def _supersession_entry(successor: PortiaRecord) -> Mapping[str, object]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or len(values) != 1:
        raise WorkflowPrerequisiteError(
            "material Response correction requires exactly one supersedes predecessor"
        )
    entry = values[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("Response supersession entry is malformed")
    return entry


def _supersession_values(successor: PortiaRecord) -> tuple[object, ...]:
    values = successor.field("supersedes")
    if values is None:
        return ()
    if not isinstance(values, tuple):
        raise WorkflowOwnershipError("Response supersedes collection is malformed")
    return values


def response_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ResponseSupersessionResolution, ...]:
    """Resolve exact predecessors after validating the frozen v1 topology."""
    require_response_record_owner(work, successor)
    values = _supersession_values(successor)
    if not values:
        return ()

    references: list[ExactPortiaWorkRecordRef] = []
    seen: set[tuple[str, str, str, str]] = set()
    reasons: set[str] = set()
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError("Response supersession entry is malformed")
        raw_reference = value.get("work_record_ref")
        if not isinstance(raw_reference, Mapping):
            raise WorkflowOwnershipError(
                "Response supersession predecessor reference is malformed"
            )
        reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
        require_action_owner(reference.work_ref, contract="response")
        if (
            reference.record_ref.record_kind != "response"
            or reference.record_ref.contract_version != "1"
        ):
            raise WorkflowOwnershipError(
                "Response supersession predecessor must name response@1"
            )
        key = (
            reference.work_ref.class_id,
            reference.work_ref.work_id,
            reference.record_ref.record_id,
            reference.record_ref.contract_version,
        )
        if key in seen:
            raise WorkflowPrerequisiteError(
                "Response supersession repeats one logical predecessor identity"
            )
        seen.add(key)
        reason = value.get("reason")
        if not isinstance(reason, str):
            raise WorkflowOwnershipError("Response supersession reason is malformed")
        accepted_reasons = (
            _ORDINARY_CORRECTION_REASONS | _NON_MATERIAL_CORRECTION_REASONS
        )
        if reason not in accepted_reasons:
            raise WorkflowPrerequisiteError(
                f"unsupported Response supersession reason {reason!r}"
            )
        reasons.add(reason)
        if reason == "other":
            detail = value.get("detail")
            if not isinstance(detail, str) or not detail.strip():
                raise WorkflowPrerequisiteError(
                    "Response supersession reason 'other' requires bounded detail"
                )
        references.append(reference)

    if len(reasons) != 1:
        raise WorkflowPrerequisiteError(
            "one Response successor must use one uniform supersession reason"
        )
    reason = next(iter(reasons))

    # Mirror the frozen Issue #17 application oracle before any predecessor I/O.
    # contract_migrated is intentionally exempt from the same-work/same-id and
    # cardinality rules because migration can preserve identity across contract
    # boundaries or represent more than one historical predecessor.
    for reference in references:
        same_work = reference.work_ref == work
        same_id = reference.record_ref.record_id == successor.logical_id
        if same_work and same_id and reason != "contract_migrated":
            raise WorkflowPrerequisiteError("Response cannot supersede itself")
        if reason == "work_root_corrected":
            if same_work:
                raise WorkflowPrerequisiteError(
                    "work-root Response correction requires a different Event"
                )
            if not same_id:
                raise WorkflowPrerequisiteError(
                    "work-root Response correction must preserve Response identity"
                )
        elif reason != "contract_migrated" and not same_work:
            raise WorkflowPrerequisiteError(
                "ordinary Response correction cannot cross work roots"
            )

    if reason == "duplicate_consolidated":
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "Response duplicate consolidation requires multiple predecessors"
            )
    elif reason != "contract_migrated" and len(references) != 1:
        raise WorkflowPrerequisiteError(
            "non-consolidation Response correction requires one predecessor"
        )

    resolved: list[ResponseSupersessionResolution] = []
    for reference in references:
        stored = repository.load_work_record(
            reference.work_ref,
            "response",
            "1",
            reference.record_ref.record_id,
        )
        require_response_record_owner(reference.work_ref, stored.record)
        if stored.record.logical_id != reference.record_ref.record_id:
            raise WorkflowOwnershipError(
                "resolved Response predecessor identity does not match exact reference"
            )
        resolved.append(
            ResponseSupersessionResolution(
                work_ref=reference.work_ref,
                stored=stored,
            )
        )
    return tuple(resolved)


def response_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    response: PortiaRecord,
) -> tuple[ResponseSupersessionResolution, ...]:
    """Resolve bounded exact supersession ancestry without following successors."""
    values: list[ResponseSupersessionResolution] = []
    visited: set[tuple[str, str, str]] = set()
    visiting: set[tuple[str, str, str]] = set()

    def visit(selected_work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
        for resolution in response_supersession_records(
            repository,
            selected_work,
            record,
        ):
            identifier = resolution.stored.record.logical_id
            if identifier is None:
                raise WorkflowOwnershipError(
                    "Response supersession predecessor has no canonical identity"
                )
            key = (
                resolution.work_ref.class_id,
                resolution.work_ref.work_id,
                identifier,
            )
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Response supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Response supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.work_ref, resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(work, response)
    return tuple(values)


def require_response_supersession_effective(
    predecessors: tuple[ResponseSupersessionResolution, ...],
) -> None:
    """Require every exact predecessor in a current successor chain superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current corrected Response requires its exact predecessor "
                "to be superseded"
            )


def require_exact_response_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-Event predecessor for ordinary material correction."""
    require_response_record_owner(work, successor)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Response correction predecessor does not belong to the selected Event"
        )
    if (
        predecessor.record_ref.record_kind != "response"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Response correction requires an exact response@1 predecessor"
        )

    entry = _supersession_entry(successor)
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Response supersession predecessor reference is malformed"
        )
    selected = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Response successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Response material correction must use a new canonical identity"
        )

    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Response supersession reason is malformed")
    if reason in _NON_MATERIAL_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"{reason} requires its dedicated consolidation/root/migration workflow"
        )
    if reason not in _ORDINARY_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Response material correction reason {reason!r}"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Response supersession reason 'other' requires bounded detail"
            )
    return reason


def require_material_response_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require the selected correction reason to match a substantive Response change."""
    if prior.contract != "response" or successor.contract != "response":
        raise WorkflowOwnershipError(
            "material Response correction requires response@1 records"
        )
    if prior.contract_version != "1" or successor.contract_version != "1":
        raise WorkflowOwnershipError(
            "material Response correction requires response@1 records"
        )
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "material Response correction requires active predecessor and successor"
        )

    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed = {
        field
        for field in _RESPONSE_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "material Response correction requires an actual Response fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _RESPONSE_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Response material correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Response supersession reason {supersession_reason!r} does not match "
            "the corrected fact"
        )


def response_correction_lifecycle_reason(supersession_reason: str) -> str:
    """Preserve the accepted Response correction reason in lifecycle provenance."""
    return supersession_reason


def superseded_response_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build a superseded predecessor by changing lifecycle metadata only."""
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "Response predecessor supersession requires active predecessor "
            "and successor"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "corrected Response successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("response", "1", data)


def response_correction_reason_detail(successor: PortiaRecord) -> str | None:
    """Return bounded correction detail for lifecycle provenance when present."""
    entry = _supersession_entry(successor)
    detail = entry.get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Response supersession detail must be bounded non-empty text"
        )
    return detail
