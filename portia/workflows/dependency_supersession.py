"""Exact correction and consolidation lineage for ``dependency@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.dependency_lifecycle import (
    dependency_lifecycle_state,
    require_dependency_lifecycle_reconciled,
)
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

DEPENDENCY_CORRECTION_REASONS = frozenset(
    {
        "dependent_corrected",
        "dependency_target_corrected",
        "strength_corrected",
        "evaluation_scope_corrected",
        "purpose_corrected",
        "other",
    }
)
_CONSOLIDATION_REASON = "duplicate_consolidated"
_REPLACEMENT_ELIGIBLE_STATUSES = frozenset({"active", "invalidated"})
_REPLACEABLE_PREDECESSOR_STATUSES = frozenset({"proposed", "active", "invalidated"})
_DEPENDENCY_DIMENSION_FIELDS = {
    "dependent": ("dependent",),
    "dependency_target": ("dependency",),
    "strength": ("strength",),
    "evaluation_scope": ("applies_to",),
    "purpose": ("purpose",),
    "detail": ("detail",),
}
_REASON_DIMENSION = {
    "dependent_corrected": "dependent",
    "dependency_target_corrected": "dependency_target",
    "strength_corrected": "strength",
    "evaluation_scope_corrected": "evaluation_scope",
    "purpose_corrected": "purpose",
}


@dataclass(frozen=True, slots=True)
class DependencySupersessionResolution:
    """One exact dependency predecessor and its successor-side edge reason."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord
    reason: str


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        (work.work_kind, work.contract_version)
        not in {("event", "2"), ("support_process", "1")}
        or record.contract != "dependency"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Dependency supersession requires exact event@2 or support_process@1 ownership"
        )


def _supersession_entries(
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], ...]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or not values:
        raise WorkflowPrerequisiteError(
            "Dependency correction requires supersession history"
        )
    entries: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError("Dependency supersession entry is malformed")
        entries.append(value)
    return tuple(entries)


def _entry_reference(entry: Mapping[str, object]) -> ExactPortiaWorkRecordRef:
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Dependency supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if (
        (reference.work_ref.work_kind, reference.work_ref.contract_version)
        not in {("event", "2"), ("support_process", "1")}
        or reference.record_ref.record_kind != "dependency"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Dependency supersession predecessor must name dependency@1 beneath "
            "an accepted work root"
        )
    return reference


def _entry_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Dependency supersession reason is malformed")
    accepted = DEPENDENCY_CORRECTION_REASONS | {_CONSOLIDATION_REASON}
    if reason not in accepted:
        raise WorkflowPrerequisiteError(
            f"unsupported Dependency supersession reason {reason!r}"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Dependency supersession reason 'other' requires detail"
            )
    return reason


def _uniform_reason(
    successor: PortiaRecord,
) -> tuple[
    str,
    tuple[ExactPortiaWorkRecordRef, ...],
    tuple[Mapping[str, object], ...],
]:
    entries = _supersession_entries(successor)
    reasons = tuple(_entry_reason(entry) for entry in entries)
    if len(set(reasons)) != 1:
        raise WorkflowPrerequisiteError(
            "one Dependency successor cannot mix supersession reasons"
        )
    references = tuple(_entry_reference(entry) for entry in entries)
    if len(set(references)) != len(references):
        raise WorkflowPrerequisiteError(
            "Dependency supersession repeats a predecessor identity"
        )
    successor_id = successor.logical_id
    if not isinstance(successor_id, str):
        raise WorkflowOwnershipError("Dependency successor has no canonical identity")
    for reference in references:
        if (
            reference.work_ref.class_id == successor.class_id
            and reference.work_ref.work_id == successor.work_id
            and reference.record_ref.record_id == successor_id
        ):
            raise WorkflowPrerequisiteError("Dependency cannot supersede itself")
    return reasons[0], references, entries


def _require_topology(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...]]:
    _require_owner(work, successor)
    reason, references, _entries = _uniform_reason(successor)
    if any(reference.work_ref != work for reference in references):
        raise WorkflowPrerequisiteError(
            "Dependency replacement cannot cross owning work roots"
        )
    if reason == _CONSOLIDATION_REASON:
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "Dependency duplicate consolidation requires multiple predecessors"
            )
    elif len(references) != 1:
        raise WorkflowPrerequisiteError(
            "ordinary Dependency correction is one-to-one"
        )
    return reason, references


def require_exact_dependency_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-work predecessor for material Dependency correction."""
    if (
        predecessor.work_ref != work
        or predecessor.record_ref.record_kind != "dependency"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Dependency correction requires one exact same-work dependency@1 predecessor"
        )
    reason, references = _require_topology(work, successor)
    if reason == _CONSOLIDATION_REASON:
        raise WorkflowPrerequisiteError(
            "duplicate_consolidated requires the dedicated Dependency consolidation path"
        )
    if reason not in DEPENDENCY_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Dependency correction reason {reason!r}"
        )
    if references[0] != predecessor:
        raise WorkflowOwnershipError(
            "Dependency successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Dependency material correction requires a new canonical identity"
        )
    return reason


def require_duplicate_dependency_consolidation_predecessors(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRecordRef, ...]:
    """Require one same-work many-to-one Dependency consolidation topology."""
    reason, references = _require_topology(work, successor)
    if reason != _CONSOLIDATION_REASON:
        raise WorkflowPrerequisiteError(
            "Dependency consolidation requires duplicate_consolidated edges"
        )
    return references


def dependency_replacement_intent_is_abandoned(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> bool:
    """Whether a proposed replacement was invalidated before becoming effective."""
    _require_owner(work, successor)
    if successor.field("supersedes") is None or successor.status != "invalidated":
        return False
    state = require_dependency_lifecycle_reconciled(repository, work, successor)
    if state.head is None or len(state.transitions) != 1:
        return False
    return (
        state.head.record.field("from_status") == "proposed"
        and state.head.record.field("to_status") == "invalidated"
        and state.head.record.field("previous_transition") is None
    )


def require_no_competing_dependency_successor(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    predecessors: Sequence[ExactPortiaWorkRecordRef],
) -> None:
    """Fail closed when a selected predecessor already has a declared direct successor."""
    selected = set(predecessors)
    for stored in repository.list_work_records(work, "dependency", version="1"):
        values = stored.record.field("supersedes")
        if values is None:
            continue
        if dependency_replacement_intent_is_abandoned(
            repository,
            work,
            stored.record,
        ):
            continue
        for entry in _supersession_entries(stored.record):
            if _entry_reference(entry) in selected:
                raise WorkflowPrerequisiteError(
                    "Dependency predecessor already has a declared direct successor"
                )


def _changed_dimensions(prior: PortiaRecord, successor: PortiaRecord) -> set[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    changed: set[str] = set()
    for dimension, fields in _DEPENDENCY_DIMENSION_FIELDS.items():
        if any(prior_data.get(field) != successor_data.get(field) for field in fields):
            changed.add(dimension)
    return changed


def require_material_dependency_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require a real material Dependency change accurately named by its edge reason."""
    if (
        prior.contract != "dependency"
        or successor.contract != "dependency"
        or prior.contract_version != "1"
        or successor.contract_version != "1"
    ):
        raise WorkflowOwnershipError("Dependency correction requires version-1 records")
    if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
        raise WorkflowPrerequisiteError(
            "Dependency predecessor is not replacement-eligible"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "corrected Dependency successor must be active or invalidated"
        )
    changed = _changed_dimensions(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Dependency correction requires an actual material dependency change"
        )
    if supersession_reason == "other":
        return
    expected_dimension = _REASON_DIMENSION.get(supersession_reason)
    if expected_dimension is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Dependency correction reason {supersession_reason!r}"
        )
    if changed != {expected_dimension}:
        raise WorkflowPrerequisiteError(
            f"Dependency correction reason {supersession_reason!r} does not exactly match "
            f"the corrected dependency dimension(s): {sorted(changed)!r}"
        )


def require_duplicate_dependency_equivalence(
    priors: Sequence[PortiaRecord],
    successor: PortiaRecord,
    *,
    reason_detail: str,
) -> None:
    """Enforce Dependency's five frozen duplicate-equivalence dimensions."""
    if len(priors) < 2:
        raise WorkflowPrerequisiteError(
            "Dependency consolidation requires at least two predecessors"
        )
    if not isinstance(reason_detail, str) or not reason_detail.strip():
        raise WorkflowPrerequisiteError(
            "Dependency duplicate consolidation requires review detail"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "consolidated Dependency successor must be active or invalidated"
        )
    dimensions = ("dependent", "dependency", "strength", "applies_to", "purpose")
    expected = {field: priors[0].field(field) for field in dimensions}
    for prior in priors:
        if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
            raise WorkflowPrerequisiteError(
                "Dependency consolidation predecessor is not replaceable"
            )
        for field in dimensions:
            if prior.field(field) != expected[field]:
                raise WorkflowPrerequisiteError(
                    "Dependency duplicate consolidation requires identical dependent, "
                    "target, strength, evaluation scope, and purpose"
                )
    for field in dimensions:
        if successor.field(field) != expected[field]:
            raise WorkflowPrerequisiteError(
                "Dependency duplicate consolidation cannot change dependent, target, "
                "strength, evaluation scope, or purpose"
            )
    # Dependency detail may contain compatible descriptive precision.  Invoking the
    # named consolidation operation with review detail is the explicit human duplicate
    # confirmation; the five accepted material dimensions above remain deterministic.


def superseded_dependency_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build a superseded predecessor by changing lifecycle metadata only."""
    if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
        raise WorkflowPrerequisiteError(
            "Dependency predecessor is not replacement-eligible"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "Dependency successor is not replacement-eligible"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Dependency successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("dependency", "1", data)


def dependency_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    """Return correction detail from a one-to-one successor edge when present."""
    entries = _supersession_entries(successor)
    if len(entries) != 1:
        return None
    detail = entries[0].get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Dependency supersession detail must be non-empty"
        )
    return detail


def dependency_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[DependencySupersessionResolution, ...]:
    """Resolve exact direct predecessor edges without successor substitution."""
    _require_owner(work, successor)
    if successor.field("supersedes") is None:
        return ()
    reason, references = _require_topology(work, successor)
    resolved: list[DependencySupersessionResolution] = []
    for reference in references:
        stored = repository.load_work_record(
            work,
            "dependency",
            "1",
            reference.record_ref.record_id,
        )
        _require_owner(work, stored.record)
        if stored.record.logical_id != reference.record_ref.record_id:
            raise WorkflowOwnershipError(
                "resolved Dependency predecessor does not match exact reference"
            )
        resolved.append(DependencySupersessionResolution(work, stored, reason))
    return tuple(resolved)


def dependency_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    dependency: PortiaRecord,
) -> tuple[DependencySupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without successor substitution."""
    values: list[DependencySupersessionResolution] = []
    visited: set[tuple[str, str, str]] = set()
    visiting: set[tuple[str, str, str]] = set()

    def identity(record: PortiaRecord) -> tuple[str, str, str]:
        identifier = record.logical_id
        if not isinstance(identifier, str):
            raise WorkflowOwnershipError(
                "Dependency predecessor has no canonical identity"
            )
        return (str(record.class_id), str(record.work_id), identifier)

    def visit(record: PortiaRecord) -> None:
        for resolution in dependency_supersession_records(repository, work, record):
            key = identity(resolution.stored.record)
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Dependency supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Dependency supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(dependency)
    return tuple(values)


def _expected_transition_category(reason: str) -> str:
    if reason == _CONSOLIDATION_REASON:
        return "consolidation"
    if reason == "other":
        return "other"
    return "correction"


def require_dependency_supersession_effective(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    predecessors: Sequence[DependencySupersessionResolution],
) -> None:
    """Require every exact declared predecessor edge to be lifecycle-effective."""
    for resolution in predecessors:
        record = resolution.stored.record
        if record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Dependency successor requires every exact predecessor superseded"
            )
        state = require_dependency_lifecycle_reconciled(repository, work, record)
        if state.head is None or state.head.record.field("to_status") != "superseded":
            raise WorkflowPrerequisiteError(
                "Dependency predecessor supersession lacks selected lifecycle evidence"
            )
        reason = state.head.record.field("reason")
        if not isinstance(reason, Mapping):
            raise WorkflowOwnershipError(
                "Dependency predecessor supersession lifecycle reason is malformed"
            )
        expected_category = _expected_transition_category(resolution.reason)
        if (
            reason.get("code") != resolution.reason
            or reason.get("category") != expected_category
        ):
            raise WorkflowPrerequisiteError(
                "Dependency predecessor lifecycle reason does not reconcile with successor edge"
            )


def _parse_timestamp(value: object, description: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} is not an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} is not an explicit timestamp"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(f"{description} lacks an explicit offset")
    return parsed


def require_dependency_replacement_timing(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    priors: Sequence[PortiaRecord],
    successor: PortiaRecord,
    *,
    effective_at: str | None,
) -> None:
    """Require replacement chronology against successor acceptance and selected history."""
    created = _parse_timestamp(
        successor.field("created_at"),
        "Dependency successor created_at",
    )
    updated = _parse_timestamp(
        successor.field("updated_at"),
        "Dependency successor updated_at",
    )
    effective = _parse_timestamp(
        effective_at or successor.field("updated_at"),
        "Dependency replacement effective_at",
    )
    if updated < created:
        raise WorkflowPrerequisiteError(
            "Dependency successor updated_at cannot precede created_at"
        )
    if effective < created:
        raise WorkflowPrerequisiteError(
            "Dependency replacement cannot become effective before successor acceptance"
        )
    if effective > updated:
        raise WorkflowPrerequisiteError(
            "Dependency replacement effective_at cannot follow successor update"
        )
    for prior in priors:
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Dependency predecessor updated_at",
        )
        if updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Dependency successor update cannot predate a predecessor revision"
            )
        state = dependency_lifecycle_state(repository, work, prior)
        if state.head is None:
            continue
        prior_effective = _parse_timestamp(
            state.head.record.field("effective_at"),
            "selected Dependency predecessor lifecycle effective_at",
        )
        prior_transition_created = _parse_timestamp(
            state.head.record.field("created_at"),
            "selected Dependency predecessor lifecycle created_at",
        )
        if effective < prior_effective:
            raise WorkflowPrerequisiteError(
                "Dependency replacement effective_at cannot precede selected lifecycle history"
            )
        if updated < prior_transition_created:
            raise WorkflowPrerequisiteError(
                "Dependency replacement recording cannot precede selected lifecycle history"
            )
