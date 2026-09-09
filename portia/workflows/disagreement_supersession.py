"""Exact correction and consolidation lineage for ``statement_of_disagreement@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.disagreement_lifecycle import disagreement_lifecycle_state
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

DISAGREEMENT_CORRECTION_REASONS = frozenset(
    {
        "source_corrected",
        "target_corrected",
        "positions_corrected",
        "statement_corrected",
        "other",
    }
)
_CONSOLIDATION_REASON = "duplicate_consolidated"
_REPLACEMENT_ELIGIBLE_STATUSES = frozenset({"active", "withdrawn", "invalidated"})
_REPLACEABLE_PREDECESSOR_STATUSES = frozenset(
    {"proposed", "active", "withdrawn", "invalidated"}
)
_DISAGREEMENT_MATERIAL_FIELDS = ("target", "source", "positions", "statement")
_DISAGREEMENT_CORRECTION_FIELDS = {
    "source_corrected": ("source",),
    "target_corrected": ("target",),
    "positions_corrected": ("positions",),
    "statement_corrected": ("statement",),
}


@dataclass(frozen=True, slots=True)
class DisagreementSupersessionResolution:
    """One exact disagreement predecessor resolved without successor following."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        (work.work_kind, work.contract_version)
        not in {("event", "2"), ("support_process", "1")}
        or record.contract != "statement_of_disagreement"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Statement of Disagreement supersession requires exact event@2 or "
            "support_process@1 ownership"
        )


def _supersession_entries(
    successor: PortiaRecord,
) -> tuple[Mapping[str, object], ...]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or not values:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement correction requires supersession history"
        )
    entries: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(
                "Statement of Disagreement supersession entry is malformed"
            )
        entries.append(value)
    return tuple(entries)


def _entry_reference(entry: Mapping[str, object]) -> ExactPortiaWorkRecordRef:
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Statement of Disagreement supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if (
        (reference.work_ref.work_kind, reference.work_ref.contract_version)
        not in {("event", "2"), ("support_process", "1")}
        or reference.record_ref.record_kind != "statement_of_disagreement"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Statement of Disagreement supersession predecessor must name "
            "statement_of_disagreement@1 beneath an accepted work root"
        )
    return reference


def _entry_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError(
            "Statement of Disagreement supersession reason is malformed"
        )
    accepted = DISAGREEMENT_CORRECTION_REASONS | {_CONSOLIDATION_REASON}
    if reason not in accepted:
        raise WorkflowPrerequisiteError(
            f"unsupported Statement of Disagreement supersession reason {reason!r}"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement supersession reason 'other' requires detail"
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
            "one Statement of Disagreement successor cannot mix supersession reasons"
        )
    references = tuple(_entry_reference(entry) for entry in entries)
    if len(set(references)) != len(references):
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement supersession repeats a predecessor identity"
        )
    successor_id = successor.logical_id
    if successor_id is None:
        raise WorkflowOwnershipError(
            "Statement of Disagreement successor has no canonical identity"
        )
    for reference in references:
        if (
            reference.work_ref.class_id == successor.class_id
            and reference.work_ref.work_id == successor.work_id
            and reference.record_ref.record_id == successor_id
        ):
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement cannot supersede itself"
            )
    return reasons[0], references, entries


def _require_topology(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...]]:
    _require_owner(work, successor)
    reason, references, _entries = _uniform_reason(successor)
    if any(reference.work_ref != work for reference in references):
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement replacement cannot cross owning work roots"
        )
    if reason == _CONSOLIDATION_REASON:
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement duplicate consolidation requires multiple predecessors"
            )
    elif len(references) != 1:
        raise WorkflowPrerequisiteError(
            "ordinary Statement of Disagreement correction is one-to-one"
        )
    return reason, references


def require_exact_disagreement_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-work predecessor for ordinary material correction."""
    if (
        predecessor.work_ref != work
        or predecessor.record_ref.record_kind != "statement_of_disagreement"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Statement of Disagreement correction requires one exact same-work "
            "statement_of_disagreement@1 predecessor"
        )
    reason, references = _require_topology(work, successor)
    if reason == _CONSOLIDATION_REASON:
        raise WorkflowPrerequisiteError(
            "duplicate_consolidated requires the dedicated disagreement consolidation path"
        )
    if reason not in DISAGREEMENT_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Statement of Disagreement correction reason {reason!r}"
        )
    if references[0] != predecessor:
        raise WorkflowOwnershipError(
            "Statement of Disagreement successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement material correction requires a new canonical identity"
        )
    return reason


def require_duplicate_disagreement_consolidation_predecessors(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRecordRef, ...]:
    """Require one same-work many-to-one disagreement consolidation topology."""
    reason, references = _require_topology(work, successor)
    if reason != _CONSOLIDATION_REASON:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement consolidation requires duplicate_consolidated edges"
        )
    return references




def require_no_competing_disagreement_successor(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    predecessors: Sequence[ExactPortiaWorkRecordRef],
) -> None:
    """Fail closed when any selected predecessor already has a declared successor."""
    selected = set(predecessors)
    for stored in repository.list_work_records(
        work,
        "statement_of_disagreement",
        version="1",
    ):
        values = stored.record.field("supersedes")
        if values is None:
            continue
        for entry in _supersession_entries(stored.record):
            if _entry_reference(entry) in selected:
                raise WorkflowPrerequisiteError(
                    "Statement of Disagreement predecessor already has a declared direct successor"
                )


def _changed_material_fields(prior: PortiaRecord, successor: PortiaRecord) -> set[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    return {
        field
        for field in _DISAGREEMENT_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def require_material_disagreement_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require a real material change matching the selected disagreement reason."""
    if (
        prior.contract != "statement_of_disagreement"
        or successor.contract != "statement_of_disagreement"
        or prior.contract_version != "1"
        or successor.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Statement of Disagreement correction requires version-1 records"
        )
    if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement predecessor is not replacement-eligible"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "corrected Statement of Disagreement successor must be active, withdrawn, or invalidated"
        )
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement correction requires an actual material fact change"
        )
    if supersession_reason == "other":
        return
    expected_fields = _DISAGREEMENT_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Statement of Disagreement correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Statement of Disagreement correction reason {supersession_reason!r} "
            "does not match the corrected fact"
        )


def _positions(record: PortiaRecord) -> frozenset[str]:
    value = record.field("positions")
    if not isinstance(value, tuple):
        raise WorkflowOwnershipError(
            "Statement of Disagreement positions are malformed"
        )
    positions: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            raise WorkflowOwnershipError(
                "Statement of Disagreement positions are malformed"
            )
        positions.add(item)
    return frozenset(positions)


def require_duplicate_disagreement_equivalence(
    priors: Sequence[PortiaRecord],
    successor: PortiaRecord,
    *,
    reason_detail: str,
) -> None:
    """Enforce deterministic duplicate gates around an explicitly reviewed consolidation."""
    if len(priors) < 2:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement consolidation requires at least two predecessors"
        )
    if not isinstance(reason_detail, str) or not reason_detail.strip():
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement duplicate consolidation requires review detail"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "consolidated Statement of Disagreement successor must be active, withdrawn, or invalidated"
        )
    common_source = priors[0].field("source")
    common_target = priors[0].field("target")
    common_positions = _positions(priors[0])
    for prior in priors:
        if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement consolidation predecessor is not replaceable"
            )
        if prior.field("source") != common_source:
            raise WorkflowPrerequisiteError(
                "duplicate disagreement consolidation requires the same represented source"
            )
        if prior.field("target") != common_target:
            raise WorkflowPrerequisiteError(
                "duplicate disagreement consolidation requires the same exact target"
            )
        if _positions(prior) != common_positions:
            raise WorkflowPrerequisiteError(
                "duplicate disagreement consolidation requires the same material positions"
            )
    if successor.field("source") != common_source:
        raise WorkflowPrerequisiteError(
            "duplicate disagreement consolidation cannot correct the represented source"
        )
    if successor.field("target") != common_target:
        raise WorkflowPrerequisiteError(
            "duplicate disagreement consolidation cannot correct the exact target"
        )
    if _positions(successor) != common_positions:
        raise WorkflowPrerequisiteError(
            "duplicate disagreement consolidation cannot correct material positions"
        )
    if any(prior.status == "withdrawn" for prior in priors) and successor.status != "withdrawn":
        raise WorkflowPrerequisiteError(
            "duplicate disagreement consolidation must preserve actual source withdrawal"
        )
    # Whether separately stored statements are duplicate captures of the same originating
    # human expression cannot be inferred from matching text.  Invoking this named
    # consolidation operation with the required review detail is the explicit human
    # confirmation; the deterministic gates above prevent it from concealing source,
    # target, or position correction.


def superseded_disagreement_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build a superseded predecessor by changing lifecycle metadata only."""
    if prior.status not in _REPLACEABLE_PREDECESSOR_STATUSES:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement predecessor is not replacement-eligible"
        )
    if successor.status not in _REPLACEMENT_ELIGIBLE_STATUSES:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement successor is not replacement-eligible"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("statement_of_disagreement", "1", data)


def disagreement_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    """Return correction detail from a one-to-one successor edge when present."""
    entries = _supersession_entries(successor)
    if len(entries) != 1:
        return None
    detail = entries[0].get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement supersession detail must be non-empty"
        )
    return detail


def disagreement_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[DisagreementSupersessionResolution, ...]:
    """Resolve exact predecessor edges without silently following a frontier."""
    _require_owner(work, successor)
    if successor.field("supersedes") is None:
        return ()
    reason, references = _require_topology(work, successor)
    if reason not in DISAGREEMENT_CORRECTION_REASONS | {_CONSOLIDATION_REASON}:
        raise WorkflowPrerequisiteError(
            f"unsupported Statement of Disagreement lineage reason {reason!r}"
        )
    resolved: list[DisagreementSupersessionResolution] = []
    for reference in references:
        stored = repository.load_work_record(
            work,
            "statement_of_disagreement",
            "1",
            reference.record_ref.record_id,
        )
        _require_owner(work, stored.record)
        if stored.record.logical_id != reference.record_ref.record_id:
            raise WorkflowOwnershipError(
                "resolved disagreement predecessor does not match exact reference"
            )
        resolved.append(DisagreementSupersessionResolution(work, stored))
    return tuple(resolved)


def disagreement_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    disagreement: PortiaRecord,
) -> tuple[DisagreementSupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without successor substitution."""
    values: list[DisagreementSupersessionResolution] = []
    visited: set[tuple[str, str, str]] = set()
    visiting: set[tuple[str, str, str]] = set()

    def identity(record: PortiaRecord) -> tuple[str, str, str]:
        identifier = record.logical_id
        if identifier is None:
            raise WorkflowOwnershipError(
                "Statement of Disagreement predecessor has no canonical identity"
            )
        return (str(record.class_id), str(record.work_id), identifier)

    def visit(record: PortiaRecord) -> None:
        for resolution in disagreement_supersession_records(repository, work, record):
            key = identity(resolution.stored.record)
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Statement of Disagreement supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Statement of Disagreement supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(disagreement)
    return tuple(values)


def require_disagreement_supersession_effective(
    predecessors: Sequence[DisagreementSupersessionResolution],
) -> None:
    """Require every exact declared predecessor to be canonically superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Statement of Disagreement successor requires every exact predecessor superseded"
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


def require_disagreement_replacement_timing(
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
        "Statement of Disagreement successor created_at",
    )
    updated = _parse_timestamp(
        successor.field("updated_at"),
        "Statement of Disagreement successor updated_at",
    )
    effective = _parse_timestamp(
        effective_at or successor.field("updated_at"),
        "Statement of Disagreement replacement effective_at",
    )
    if updated < created:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement successor updated_at cannot precede created_at"
        )
    if effective < created:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement replacement cannot become effective before successor acceptance"
        )
    if effective > updated:
        raise WorkflowPrerequisiteError(
            "Statement of Disagreement replacement effective_at cannot follow successor update"
        )
    for prior in priors:
        prior_updated = _parse_timestamp(
            prior.field("updated_at"),
            "Statement of Disagreement predecessor updated_at",
        )
        if updated < prior_updated:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement successor update cannot predate a predecessor revision"
            )
        state = disagreement_lifecycle_state(repository, work, prior)
        if state.head is None:
            continue
        prior_effective = _parse_timestamp(
            state.head.record.field("effective_at"),
            "selected predecessor lifecycle effective_at",
        )
        prior_transition_created = _parse_timestamp(
            state.head.record.field("created_at"),
            "selected predecessor lifecycle created_at",
        )
        if effective < prior_effective:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement replacement effective_at cannot precede selected lifecycle history"
            )
        if updated < prior_transition_created:
            raise WorkflowPrerequisiteError(
                "Statement of Disagreement replacement recording cannot precede selected lifecycle history"
            )
