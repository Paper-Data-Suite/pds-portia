"""Exact successor-history validation for ``support_process@1`` roots."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from portia.models import PortiaRecord, SupportProcessV1, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.support_process_lifecycle import (
    require_support_process_lifecycle_reconciled,
)

SUPPORT_PROCESS_CORRECTION_REASONS = frozenset(
    {
        "summary_corrected",
        "initiation_corrected",
        "planned_timing_corrected",
        "other",
    }
)
RESERVED_SUPPORT_PROCESS_REASONS = frozenset(
    {
        "duplicate_consolidated",
        "work_root_corrected",
        "contract_migrated",
    }
)
_SUPPORT_PROCESS_MATERIAL_FIELDS = (
    "summary",
    "initiation",
    "planned_start_date",
    "planned_end_date",
    "review_on",
)
_SUPPORT_PROCESS_CORRECTION_FIELDS = {
    "summary_corrected": ("summary",),
    "initiation_corrected": ("initiation",),
    "planned_timing_corrected": (
        "planned_start_date",
        "planned_end_date",
        "review_on",
    ),
}


def _parsed_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"Support Process {field_name} timestamp lacks an explicit offset"
        )
    return parsed


def _exact_predecessor_entry(
    successor: PortiaRecord,
) -> tuple[ExactPortiaWorkRef, str, str | None]:
    if not isinstance(successor, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process correction requires support_process@1 successor"
        )
    entries = successor.field("supersedes")
    if not isinstance(entries, tuple) or len(entries) != 1:
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction requires exactly one predecessor"
        )
    entry = entries[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError(
            "Support Process supersession entry is malformed"
        )
    work_ref = entry.get("work_ref")
    if not isinstance(work_ref, Mapping):
        raise WorkflowOwnershipError(
            "Support Process supersession predecessor is not exact"
        )
    try:
        predecessor = ExactPortiaWorkRef.from_dict(work_ref)
    except (TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(
            "Support Process supersession predecessor is not exact"
        ) from exc
    if (
        predecessor.work_kind != "support_process"
        or predecessor.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Support Process supersession predecessor must be support_process@1"
        )
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError(
            "Support Process supersession reason is malformed"
        )
    detail = entry.get("detail")
    if detail is not None and not isinstance(detail, str):
        raise WorkflowOwnershipError(
            "Support Process supersession detail is malformed"
        )
    return predecessor, reason, detail


def support_process_supersession_reason_detail(
    successor: PortiaRecord,
) -> tuple[str, str | None]:
    """Return the exact one-predecessor successor reason and optional detail."""
    _predecessor, reason, detail = _exact_predecessor_entry(successor)
    return reason, detail


def require_exact_support_process_correction_predecessor(
    predecessor: ExactPortiaWorkRef,
    successor: PortiaRecord,
) -> str:
    """Require the ordinary proposed-root correction topology for Slice 9e."""
    exact, reason, detail = _exact_predecessor_entry(successor)
    if exact != predecessor:
        raise WorkflowPrerequisiteError(
            "Support Process correction successor does not name the selected "
            "exact predecessor"
        )
    if reason in RESERVED_SUPPORT_PROCESS_REASONS:
        raise WorkflowPrerequisiteError(
            f"Support Process correction reason {reason!r} requires the dedicated "
            "topology/migration workflow"
        )
    if reason not in SUPPORT_PROCESS_CORRECTION_REASONS:
        raise WorkflowPrerequisiteError(
            f"unsupported ordinary Support Process correction reason {reason!r}"
        )
    if reason == "other" and (detail is None or not detail.strip()):
        raise WorkflowPrerequisiteError(
            "Support Process correction reason 'other' requires detail"
        )
    if successor.class_id != predecessor.class_id:
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction cannot change owning class"
        )
    if successor.work_id == predecessor.work_id:
        raise WorkflowPrerequisiteError(
            "Support Process correction requires a new canonical work identity"
        )
    if successor.status != "proposed":
        raise WorkflowPrerequisiteError(
            "Slice 9e Support Process correction successor must remain proposed"
        )
    if successor.field("workflow_state") != "planning":
        raise WorkflowPrerequisiteError(
            "Slice 9e Support Process correction successor must remain planning"
        )
    return reason


def require_material_support_process_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    *,
    reason: str,
) -> None:
    """Require the correction reason to correspond to the changed root fact."""
    if not isinstance(prior, SupportProcessV1) or not isinstance(
        successor, SupportProcessV1
    ):
        raise WorkflowOwnershipError(
            "Support Process correction requires support_process@1 records"
        )
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()

    if prior.status != "proposed" or prior.field("workflow_state") != "planning":
        raise WorkflowPrerequisiteError(
            "active or progressed Support Process correction requires the later "
            "work-root child-reconciliation workflow"
        )
    if prior.class_id != successor.class_id:
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction cannot change owning class"
        )
    if prior.field("school_year") != successor.field("school_year"):
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction cannot change school_year"
        )
    if prior.field("continues_from") != successor.field("continues_from"):
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction cannot rewrite continues_from"
        )
    if prior.field("creation_source") != successor.field("creation_source"):
        raise WorkflowPrerequisiteError(
            "ordinary Support Process correction cannot rewrite creation_source"
        )
    if prior.field("workflow_state") != successor.field("workflow_state"):
        raise WorkflowPrerequisiteError(
            "Support Process correction cannot smuggle workflow_state progression"
        )

    prior_updated = _parsed_timestamp(
        prior.field("updated_at"), field_name="predecessor updated_at"
    )
    successor_created = _parsed_timestamp(
        successor.field("created_at"), field_name="successor created_at"
    )
    successor_updated = _parsed_timestamp(
        successor.field("updated_at"), field_name="successor updated_at"
    )
    if successor_created < prior_updated or successor_updated < successor_created:
        raise WorkflowPrerequisiteError(
            "Support Process correction successor chronology is inconsistent"
        )

    changed = {
        field
        for field in _SUPPORT_PROCESS_MATERIAL_FIELDS
        if prior_data.get(field) != successor_data.get(field)
    }
    if not changed:
        raise WorkflowPrerequisiteError(
            "Support Process correction requires an actual material root change"
        )
    if reason == "other":
        return
    allowed = set(_SUPPORT_PROCESS_CORRECTION_FIELDS[reason])
    if not changed <= allowed or not changed.intersection(allowed):
        raise WorkflowPrerequisiteError(
            f"Support Process correction reason {reason!r} does not match "
            "the corrected fact"
        )

    immutable_content = (
        "record_type",
        "work_kind",
        "module_id",
        "school_year",
        "workflow_state",
        "continues_from",
        "creation_source",
    )
    for field in immutable_content:
        if prior_data.get(field) != successor_data.get(field):
            raise WorkflowPrerequisiteError(
                f"ordinary Support Process correction cannot rewrite {field}"
            )


def superseded_support_process_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the old root revision that becomes superseded atomically."""
    if not isinstance(prior, SupportProcessV1) or not isinstance(
        successor, SupportProcessV1
    ):
        raise WorkflowOwnershipError(
            "Support Process correction requires support_process@1 records"
        )
    wire = prior.to_dict()
    successor_data = successor.to_dict()
    wire["status"] = "superseded"
    wire["updated_at"] = successor_data["updated_at"]
    wire["updated_by"] = successor_data["updated_by"]
    return parse_portia_record("support_process", "1", wire)


def support_process_supersession_ancestry(
    repository: PortiaRepository,
    successor: PortiaRecord,
    *,
    limit: int = 128,
) -> tuple[StoredRecord, ...]:
    """Resolve exact root predecessors without following them forward."""
    if not isinstance(successor, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process supersession ancestry requires support_process@1"
        )
    ancestry: list[StoredRecord] = []
    seen = {successor.work_id}
    current = successor
    for _ in range(limit):
        entries = current.field("supersedes")
        if entries is None:
            return tuple(ancestry)
        predecessor, reason, _detail = _exact_predecessor_entry(current)
        if reason not in SUPPORT_PROCESS_CORRECTION_REASONS:
            raise WorkflowPrerequisiteError(
                "Support Process ordinary current-use ancestry contains a "
                "topology/migration successor reason"
            )
        if predecessor.work_id in seen:
            raise WorkflowPrerequisiteError(
                "Support Process supersession ancestry contains a cycle"
            )
        if predecessor.class_id != current.class_id:
            raise WorkflowPrerequisiteError(
                "ordinary Support Process supersession ancestry cannot cross classes"
            )
        seen.add(predecessor.work_id)
        stored = repository.load_work(predecessor)
        if not isinstance(stored.record, SupportProcessV1):
            raise WorkflowOwnershipError(
                "Support Process predecessor does not resolve as support_process@1"
            )
        if stored.record.field("school_year") != current.field("school_year"):
            raise WorkflowPrerequisiteError(
                "ordinary Support Process supersession ancestry cannot change "
                "school_year"
            )
        if stored.record.status != "superseded":
            raise WorkflowPrerequisiteError(
                "Support Process predecessor is not superseded for successor use"
            )
        require_support_process_lifecycle_reconciled(
            repository,
            predecessor,
            stored.record,
        )
        ancestry.append(stored)
        current = stored.record
    raise WorkflowPrerequisiteError(
        "Support Process supersession ancestry exceeds the bounded depth"
    )
