"""Exact ordinary correction supersession rules for ``fidelity@1``."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

FIDELITY_CORRECTION_REASONS = frozenset(
    {
        "evaluator_corrected",
        "scope_corrected",
        "basis_corrected",
        "result_corrected",
        "instrument_result_corrected",
        "evaluation_period_corrected",
        "other",
    }
)
_RESERVED_FIDELITY_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_FIDELITY_MATERIAL_FIELDS = (
    "plan_ref",
    "evaluator_ref",
    "scope",
    "result",
    "basis",
    "instrument_result",
    "evaluated_at",
    "summary",
)
_FIDELITY_CORRECTION_FIELDS = {
    "evaluator_corrected": ("evaluator_ref",),
    "scope_corrected": ("scope",),
    "basis_corrected": ("basis",),
    "result_corrected": ("result",),
    "instrument_result_corrected": ("instrument_result",),
    # A Fidelity evaluation period can be represented by its bounded scope interval
    # and/or by the recorded evaluation timestamp. Keep the correction reason honest
    # without forcing callers to collapse those distinct wire fields.
    "evaluation_period_corrected": ("scope", "evaluated_at"),
}


@dataclass(frozen=True, slots=True)
class FidelitySupersessionResolution:
    """One exact Fidelity predecessor resolved without following successors."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "fidelity"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Fidelity supersession requires exact support_process@1 ownership"
        )


def _supersession_entries(successor: PortiaRecord) -> tuple[Mapping[str, object], ...]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or not values:
        raise WorkflowPrerequisiteError(
            "Fidelity correction requires supersession history"
        )
    entries: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError("Fidelity supersession entry is malformed")
        entries.append(value)
    return tuple(entries)


def _supersession_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Fidelity supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Fidelity supersession reason 'other' requires bounded detail"
            )
    return reason


def _entry_reference(entry: Mapping[str, object]) -> ExactPortiaWorkRecordRef:
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Fidelity supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if (
        reference.work_ref.work_kind != "support_process"
        or reference.work_ref.contract_version != "1"
        or reference.record_ref.record_kind != "fidelity"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Fidelity supersession predecessor must name fidelity@1 beneath "
            "support_process@1"
        )
    return reference


def _uniform_reason(
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...], tuple[Mapping[str, object], ...]]:
    entries = _supersession_entries(successor)
    reasons = tuple(_supersession_reason(entry) for entry in entries)
    if len(set(reasons)) != 1:
        raise WorkflowPrerequisiteError("mixed Fidelity supersession reasons")
    reason = reasons[0]
    references = tuple(_entry_reference(entry) for entry in entries)
    if len(set(references)) != len(references):
        raise WorkflowPrerequisiteError(
            "Fidelity supersession repeats a predecessor identity"
        )
    successor_id = successor.logical_id
    if successor_id is None:
        raise WorkflowOwnershipError("Fidelity successor has no canonical identity")
    for reference in references:
        if (
            reason != "work_root_corrected"
            and reference.work_ref.class_id == successor.class_id
            and reference.work_ref.work_id == successor.work_id
            and reference.record_ref.record_id == successor_id
        ):
            raise WorkflowPrerequisiteError("Fidelity cannot supersede itself")
    return reason, references, entries


def _require_topology(
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...]]:
    reason, references, _entries = _uniform_reason(successor)
    if reason == "duplicate_consolidated":
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "duplicate consolidation needs two Fidelity predecessors"
            )
        for reference in references:
            if (
                reference.work_ref.class_id != successor.class_id
                or reference.work_ref.work_id != successor.work_id
            ):
                raise WorkflowPrerequisiteError(
                    "Fidelity duplicate consolidation cannot cross Support Process roots"
                )
        return reason, references
    if reason == "work_root_corrected":
        if len(references) != 1:
            raise WorkflowPrerequisiteError(
                "work-root Fidelity correction is one-to-one"
            )
        predecessor = references[0]
        if (
            predecessor.work_ref.class_id == successor.class_id
            and predecessor.work_ref.work_id == successor.work_id
        ):
            raise WorkflowPrerequisiteError(
                "work-root correction requires a different Support Process root"
            )
        if predecessor.record_ref.record_id != successor.logical_id:
            raise WorkflowPrerequisiteError(
                "work-root correction must preserve Fidelity ID"
            )
        return reason, references
    if reason == "contract_migrated":
        if len(references) != 1:
            raise WorkflowPrerequisiteError("Fidelity contract migration is one-to-one")
        return reason, references
    if len(references) != 1:
        raise WorkflowPrerequisiteError("ordinary Fidelity correction is one-to-one")
    return reason, references


def require_duplicate_fidelity_consolidation_predecessors(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRecordRef, ...]:
    """Require one same-process multi-predecessor duplicate consolidation graph."""
    _require_owner(work, successor)
    reason, references = _require_topology(successor)
    if reason != "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            "Fidelity consolidation requires supersession reason "
            "'duplicate_consolidated'"
        )
    if any(reference.work_ref != work for reference in references):
        raise WorkflowPrerequisiteError(
            "Fidelity duplicate consolidation cannot cross Support Process roots"
        )
    return references


def require_fidelity_work_root_correction_predecessor(
    destination_work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> ExactPortiaWorkRef:
    """Require one exact cross-root ownership-correction predecessor."""
    _require_owner(destination_work, successor)
    if (
        predecessor.record_ref.record_kind != "fidelity"
        or predecessor.record_ref.contract_version != "1"
        or predecessor.work_ref.work_kind != "support_process"
        or predecessor.work_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Fidelity work-root correction requires an exact fidelity@1 "
            "predecessor beneath support_process@1"
        )
    reason, references = _require_topology(successor)
    if reason != "work_root_corrected":
        raise WorkflowPrerequisiteError(
            "Fidelity ownership correction requires supersession reason "
            "'work_root_corrected'"
        )
    selected = references[0]
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Fidelity work-root successor must supersede the exact selected "
            "predecessor"
        )
    if predecessor.work_ref == destination_work:
        raise WorkflowPrerequisiteError(
            "work-root correction requires a different Support Process root"
        )
    return predecessor.work_ref


def require_exact_fidelity_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and one ordinary Fidelity correction reason."""
    _require_owner(work, successor)
    if (
        predecessor.record_ref.record_kind != "fidelity"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Fidelity correction requires an exact fidelity@1 predecessor"
        )
    reason, references = _require_topology(successor)
    if reason == "work_root_corrected":
        raise WorkflowPrerequisiteError(
            "Fidelity work-root correction requires a dedicated ownership path"
        )
    if reason == "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            "Fidelity duplicate consolidation requires a dedicated consolidation path"
        )
    if reason == "contract_migrated":
        raise WorkflowPrerequisiteError(
            "Fidelity contract migration requires a dedicated migration path"
        )
    if reason not in FIDELITY_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Fidelity correction reason {reason!r}"
        )
    selected = references[0]
    if selected.work_ref != work:
        raise WorkflowPrerequisiteError(
            "ordinary Fidelity correction cannot cross Support Process roots"
        )
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "selected Fidelity predecessor does not belong to the selected process"
        )
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Fidelity successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError("Fidelity cannot supersede itself")
    return reason


def _changed_material_fields(prior: PortiaRecord, successor: PortiaRecord) -> set[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    return {
        field
        for field in _FIDELITY_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def require_material_fidelity_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require an ordinary correction to change the matching evaluation fact."""
    if (
        prior.contract != "fidelity"
        or successor.contract != "fidelity"
        or prior.contract_version != "1"
        or successor.contract_version != "1"
    ):
        raise WorkflowOwnershipError("Fidelity correction requires fidelity@1 records")
    if prior.status not in {"active", "invalidated"}:
        raise WorkflowPrerequisiteError(
            "Fidelity correction predecessor must be active or invalidated"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Fidelity successor must be canonically active"
        )
    if prior.field("plan_ref") != successor.field("plan_ref"):
        raise WorkflowPrerequisiteError(
            "ordinary Fidelity correction cannot rewrite plan_ref"
        )
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Fidelity correction requires an actual material evaluation fact change"
        )
    changed.discard("plan_ref")
    if supersession_reason == "other":
        return
    expected_fields = _FIDELITY_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Fidelity correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Fidelity correction reason {supersession_reason!r} does not match "
            "the corrected evaluation fact"
        )


def superseded_fidelity_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the superseded predecessor by changing lifecycle metadata only."""
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Fidelity successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("fidelity", "1", data)


def fidelity_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    """Return optional bounded supersession detail for lifecycle provenance."""
    entries = _supersession_entries(successor)
    if len(entries) != 1:
        return None
    detail = entries[0].get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Fidelity supersession detail must be bounded non-empty text"
        )
    return detail


def fidelity_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[FidelitySupersessionResolution, ...]:
    """Resolve exact ordinary-correction lineage without successor following."""
    _require_owner(work, successor)
    values = successor.field("supersedes")
    if values is None:
        return ()
    reason, references = _require_topology(successor)
    if reason == "duplicate_consolidated":
        require_duplicate_fidelity_consolidation_predecessors(work, successor)
        return tuple(
            FidelitySupersessionResolution(
                work_ref=work,
                stored=repository.load_work_record(
                    work,
                    "fidelity",
                    "1",
                    reference.record_ref.record_id,
                ),
            )
            for reference in references
        )
    if reason == "work_root_corrected":
        reference = references[0]
        return (
            FidelitySupersessionResolution(
                work_ref=reference.work_ref,
                stored=repository.load_work_record(
                    reference.work_ref,
                    "fidelity",
                    "1",
                    reference.record_ref.record_id,
                ),
            ),
        )
    if reason not in FIDELITY_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            "Fidelity current-use lineage requires supported ordinary correction, "
            f"got {reason!r}"
        )
    reference = references[0]
    if reference.work_ref != work:
        raise WorkflowPrerequisiteError(
            "ordinary Fidelity correction cannot cross Support Process roots"
        )
    stored = repository.load_work_record(
        work,
        "fidelity",
        "1",
        reference.record_ref.record_id,
    )
    return (FidelitySupersessionResolution(work_ref=work, stored=stored),)


def fidelity_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    fidelity: PortiaRecord,
) -> tuple[FidelitySupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without following successors."""
    values: list[FidelitySupersessionResolution] = []
    visited: set[tuple[str, str, str, str, str]] = set()
    visiting: set[tuple[str, str, str, str, str]] = set()

    def identity(
        record_work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[str, str, str, str, str]:
        identifier = record.logical_id
        if identifier is None:
            raise WorkflowOwnershipError(
                "Fidelity supersession predecessor has no canonical identity"
            )
        return (
            record_work.class_id,
            record_work.work_id,
            record_work.work_kind,
            record_work.contract_version,
            identifier,
        )

    def visit(record_work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
        for resolution in fidelity_supersession_records(
            repository,
            record_work,
            record,
        ):
            key = identity(resolution.work_ref, resolution.stored.record)
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Fidelity supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Fidelity supersession ancestry exceeds the bounded workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.work_ref, resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(work, fidelity)
    return tuple(values)


def require_fidelity_supersession_effective(
    predecessors: Sequence[FidelitySupersessionResolution],
) -> None:
    """Require every exact predecessor in current ordinary lineage to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Fidelity successor requires its exact predecessor superseded"
            )
