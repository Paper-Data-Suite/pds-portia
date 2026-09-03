"""Exact ordinary correction supersession rules for ``implementation@1``."""

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

IMPLEMENTATION_CORRECTION_REASONS = frozenset(
    {
        "provider_corrected",
        "target_corrected",
        "timing_corrected",
        "execution_state_corrected",
        "variation_corrected",
        "summary_corrected",
        "other",
    }
)
_RESERVED_IMPLEMENTATION_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_IMPLEMENTATION_MATERIAL_FIELDS = (
    "plan_ref",
    "actual_target",
    "implementation_provider",
    "execution_state",
    "started_at",
    "ended_at",
    "variation",
    "summary",
)
_IMPLEMENTATION_CORRECTION_FIELDS = {
    "provider_corrected": ("implementation_provider",),
    "target_corrected": ("actual_target",),
    "timing_corrected": ("started_at", "ended_at"),
    "execution_state_corrected": ("execution_state",),
    "variation_corrected": ("variation",),
    "summary_corrected": ("summary",),
}


@dataclass(frozen=True, slots=True)
class ImplementationSupersessionResolution:
    """One exact Implementation predecessor resolved without following successors."""

    work_ref: ExactPortiaWorkRef
    stored: StoredRecord


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "implementation"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Implementation supersession requires exact support_process@1 ownership"
        )


def _supersession_entries(successor: PortiaRecord) -> tuple[Mapping[str, object], ...]:
    values = successor.field("supersedes")
    if not isinstance(values, tuple) or not values:
        raise WorkflowPrerequisiteError(
            "Implementation correction requires supersession history"
        )
    entries: list[Mapping[str, object]] = []
    for value in values:
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(
                "Implementation supersession entry is malformed"
            )
        entries.append(value)
    return tuple(entries)


def _supersession_reason(entry: Mapping[str, object]) -> str:
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("Implementation supersession reason is malformed")
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "Implementation supersession reason 'other' requires bounded detail"
            )
    return reason


def _entry_reference(entry: Mapping[str, object]) -> ExactPortiaWorkRecordRef:
    raw_reference = entry.get("work_record_ref")
    if not isinstance(raw_reference, Mapping):
        raise WorkflowOwnershipError(
            "Implementation supersession predecessor reference is malformed"
        )
    reference = ExactPortiaWorkRecordRef.from_dict(raw_reference)
    if (
        reference.work_ref.work_kind != "support_process"
        or reference.work_ref.contract_version != "1"
        or reference.record_ref.record_kind != "implementation"
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Implementation supersession predecessor must name implementation@1 "
            "beneath support_process@1"
        )
    return reference


def _uniform_reason(
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...], tuple[Mapping[str, object], ...]]:
    entries = _supersession_entries(successor)
    reasons = tuple(_supersession_reason(entry) for entry in entries)
    if len(set(reasons)) != 1:
        raise WorkflowPrerequisiteError("mixed Implementation supersession reasons")
    reason = reasons[0]
    references = tuple(_entry_reference(entry) for entry in entries)
    if len(set(references)) != len(references):
        raise WorkflowPrerequisiteError(
            "Implementation supersession repeats a predecessor identity"
        )
    successor_id = successor.logical_id
    if successor_id is None:
        raise WorkflowOwnershipError(
            "Implementation successor has no canonical identity"
        )
    for reference in references:
        if (
            reason != "work_root_corrected"
            and reference.work_ref.class_id == successor.class_id
            and reference.work_ref.work_id == successor.work_id
            and reference.record_ref.record_id == successor_id
        ):
            raise WorkflowPrerequisiteError("Implementation cannot supersede itself")
    return reason, references, entries


def _require_topology(
    successor: PortiaRecord,
) -> tuple[str, tuple[ExactPortiaWorkRecordRef, ...]]:
    reason, references, _entries = _uniform_reason(successor)
    if reason == "duplicate_consolidated":
        if len(references) < 2:
            raise WorkflowPrerequisiteError(
                "duplicate consolidation needs two Implementation predecessors"
            )
        for reference in references:
            if (
                reference.work_ref.class_id != successor.class_id
                or reference.work_ref.work_id != successor.work_id
            ):
                raise WorkflowPrerequisiteError(
                    "Implementation duplicate consolidation cannot cross "
                    "Support Process roots"
                )
        return reason, references
    if reason == "work_root_corrected":
        if len(references) != 1:
            raise WorkflowPrerequisiteError(
                "work-root Implementation correction is one-to-one"
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
                "work-root correction must preserve Implementation ID"
            )
        return reason, references
    if reason == "contract_migrated":
        if len(references) != 1:
            raise WorkflowPrerequisiteError(
                "Implementation contract migration is one-to-one"
            )
        return reason, references
    if len(references) != 1:
        raise WorkflowPrerequisiteError(
            "ordinary Implementation correction is one-to-one"
        )
    return reason, references


def require_duplicate_implementation_consolidation_predecessors(
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRecordRef, ...]:
    """Require one same-process multi-predecessor duplicate consolidation graph."""
    _require_owner(work, successor)
    reason, references = _require_topology(successor)
    if reason != "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            "Implementation consolidation requires supersession reason "
            "'duplicate_consolidated'"
        )
    if any(reference.work_ref != work for reference in references):
        raise WorkflowPrerequisiteError(
            "Implementation duplicate consolidation cannot cross Support Process roots"
        )
    return references


def require_implementation_work_root_correction_predecessor(
    destination_work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> ExactPortiaWorkRef:
    """Require one exact cross-root ownership-correction predecessor."""
    _require_owner(destination_work, successor)
    if (
        predecessor.record_ref.record_kind != "implementation"
        or predecessor.record_ref.contract_version != "1"
        or predecessor.work_ref.work_kind != "support_process"
        or predecessor.work_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Implementation work-root correction requires an exact "
            "implementation@1 predecessor beneath support_process@1"
        )
    reason, references = _require_topology(successor)
    if reason != "work_root_corrected":
        raise WorkflowPrerequisiteError(
            "Implementation ownership correction requires supersession reason "
            "'work_root_corrected'"
        )
    selected = references[0]
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Implementation work-root successor must supersede the exact "
            "selected predecessor"
        )
    if predecessor.work_ref == destination_work:
        raise WorkflowPrerequisiteError(
            "work-root correction requires a different Support Process root"
        )
    return predecessor.work_ref


def require_exact_implementation_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact predecessor and one ordinary material correction reason."""
    _require_owner(work, successor)
    if (
        predecessor.record_ref.record_kind != "implementation"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Implementation correction requires an exact implementation@1 predecessor"
        )
    reason, references = _require_topology(successor)
    if reason == "work_root_corrected":
        raise WorkflowPrerequisiteError(
            "Implementation work-root correction requires a dedicated ownership path"
        )
    if reason == "duplicate_consolidated":
        raise WorkflowPrerequisiteError(
            "Implementation duplicate consolidation requires a dedicated "
            "consolidation path"
        )
    if reason == "contract_migrated":
        raise WorkflowPrerequisiteError(
            "Implementation contract migration requires a dedicated migration path"
        )
    if reason not in IMPLEMENTATION_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported Implementation correction reason {reason!r}"
        )
    selected = references[0]
    if selected.work_ref != work:
        raise WorkflowPrerequisiteError(
            "ordinary Implementation correction cannot cross Support Process roots"
        )
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "selected Implementation predecessor does not belong to the "
            "selected process"
        )
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Implementation successor must supersede the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError("Implementation cannot supersede itself")
    return reason


def _changed_material_fields(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> set[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    return {
        field
        for field in _IMPLEMENTATION_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }


def require_material_implementation_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> None:
    """Require an ordinary correction to change the matching occurrence fact."""
    if (
        prior.contract != "implementation"
        or successor.contract != "implementation"
        or prior.contract_version != "1"
        or successor.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Implementation correction requires implementation@1 records"
        )
    if prior.status not in {"active", "invalidated"}:
        raise WorkflowPrerequisiteError(
            "Implementation correction predecessor must be active or invalidated"
        )
    if successor.status != "active":
        raise WorkflowPrerequisiteError(
            "corrected Implementation successor must be canonically active"
        )
    if prior.field("plan_ref") != successor.field("plan_ref"):
        raise WorkflowPrerequisiteError(
            "ordinary Implementation correction cannot rewrite plan_ref"
        )
    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "Implementation correction requires an actual material occurrence "
            "fact change"
        )
    changed.discard("plan_ref")
    if supersession_reason == "other":
        return
    expected_fields = _IMPLEMENTATION_CORRECTION_FIELDS.get(supersession_reason)
    if expected_fields is None:
        raise WorkflowPrerequisiteError(
            f"unsupported Implementation correction reason {supersession_reason!r}"
        )
    if not changed.intersection(expected_fields):
        raise WorkflowPrerequisiteError(
            f"Implementation correction reason {supersession_reason!r} does not match "
            "the corrected occurrence fact"
        )


def superseded_implementation_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the superseded predecessor by changing lifecycle metadata only."""
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Implementation successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record("implementation", "1", data)


def implementation_supersession_reason_detail(successor: PortiaRecord) -> str | None:
    """Return optional bounded supersession detail for lifecycle provenance."""
    entries = _supersession_entries(successor)
    if len(entries) != 1:
        return None
    detail = entries[0].get("detail")
    if detail is None:
        return None
    if not isinstance(detail, str) or not detail.strip():
        raise WorkflowPrerequisiteError(
            "Implementation supersession detail must be bounded non-empty text"
        )
    return detail


def implementation_supersession_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> tuple[ImplementationSupersessionResolution, ...]:
    """Resolve exact ordinary-correction lineage without successor following."""
    _require_owner(work, successor)
    values = successor.field("supersedes")
    if values is None:
        return ()
    reason, references = _require_topology(successor)
    if reason == "duplicate_consolidated":
        require_duplicate_implementation_consolidation_predecessors(work, successor)
        return tuple(
            ImplementationSupersessionResolution(
                work_ref=work,
                stored=repository.load_work_record(
                    work,
                    "implementation",
                    "1",
                    reference.record_ref.record_id,
                ),
            )
            for reference in references
        )
    if reason == "work_root_corrected":
        reference = references[0]
        return (
            ImplementationSupersessionResolution(
                work_ref=reference.work_ref,
                stored=repository.load_work_record(
                    reference.work_ref,
                    "implementation",
                    "1",
                    reference.record_ref.record_id,
                ),
            ),
        )
    if reason not in IMPLEMENTATION_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            "Implementation current-use lineage requires supported ordinary "
            f"correction, got {reason!r}"
        )
    reference = references[0]
    if reference.work_ref != work:
        raise WorkflowPrerequisiteError(
            "ordinary Implementation correction cannot cross Support Process roots"
        )
    stored = repository.load_work_record(
        work,
        "implementation",
        "1",
        reference.record_ref.record_id,
    )
    return (ImplementationSupersessionResolution(work_ref=work, stored=stored),)


def implementation_supersession_ancestry(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    implementation: PortiaRecord,
) -> tuple[ImplementationSupersessionResolution, ...]:
    """Resolve bounded exact predecessor ancestry without following successors."""
    values: list[ImplementationSupersessionResolution] = []
    visited: set[tuple[str, str, str, str, str]] = set()
    visiting: set[tuple[str, str, str, str, str]] = set()

    def identity(
        record_work: ExactPortiaWorkRef,
        record: PortiaRecord,
    ) -> tuple[str, str, str, str, str]:
        identifier = record.logical_id
        if identifier is None:
            raise WorkflowOwnershipError(
                "Implementation supersession predecessor has no canonical identity"
            )
        return (
            record_work.class_id,
            record_work.work_id,
            record_work.work_kind,
            record_work.contract_version,
            identifier,
        )

    def visit(record_work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
        for resolution in implementation_supersession_records(
            repository,
            record_work,
            record,
        ):
            key = identity(resolution.work_ref, resolution.stored.record)
            if key in visiting:
                raise WorkflowPrerequisiteError(
                    "Implementation supersession ancestry contains a cycle"
                )
            if key in visited:
                continue
            if len(visited) >= 128:
                raise WorkflowPrerequisiteError(
                    "Implementation supersession ancestry exceeds the bounded "
                    "workflow limit"
                )
            visiting.add(key)
            values.append(resolution)
            visit(resolution.work_ref, resolution.stored.record)
            visiting.remove(key)
            visited.add(key)

    visit(work, implementation)
    return tuple(values)


def require_implementation_supersession_effective(
    predecessors: Sequence[ImplementationSupersessionResolution],
) -> None:
    """Require every exact predecessor in current ordinary lineage to be superseded."""
    for resolution in predecessors:
        if resolution.stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "current Implementation successor requires its exact predecessor "
                "superseded"
            )
