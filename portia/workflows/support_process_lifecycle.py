"""Lifecycle planning for canonical ``support_process@1`` work roots."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import require_revision_invariants
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_LIFECYCLE_VERSION = "1"
_SUPPORT_PROCESS_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}
_SUPPORT_PROCESS_REVISION_MUTABLE_FIELDS = frozenset(
    {"status", "updated_at", "updated_by"}
)


@dataclass(frozen=True, slots=True)
class SupportProcessLifecycleState:
    """One exact linear lifecycle chain for one Support Process root."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected Support Process lifecycle head has no valid to_status"
            )
        return value


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        work.work_kind != "support_process"
        or work.contract_version != "1"
        or record.contract != "support_process"
        or record.contract_version != "1"
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Support Process lifecycle requires exact support_process@1 ownership"
        )


def _local_work_target() -> dict[str, object]:
    return {
        "kind": "work",
        "work_kind": "support_process",
        "contract_version": "1",
    }


def _previous_transition_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_transition")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError(
            "Support Process lifecycle previous_transition is malformed"
        )
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "Support Process lifecycle previous_transition is not exact"
        )
    return str(previous["record_id"])


def support_process_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    root: PortiaRecord,
) -> SupportProcessLifecycleState:
    """Resolve the persisted root lifecycle chain without timestamp ordering."""
    _require_owner(work, root)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work,
            "lifecycle_transition",
            version=_LIFECYCLE_VERSION,
        )
        if stored.record.field("target") == _local_work_target()
    )
    if not selected:
        return SupportProcessLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None or transition_id in by_id:
            raise WorkflowPrerequisiteError(
                "Support Process lifecycle history repeats a transition identity"
            )
        by_id[transition_id] = stored
        previous_id = _previous_transition_id(stored.record)
        if previous_id is None:
            roots.append(stored)
        else:
            referenced[previous_id] = referenced.get(previous_id, 0) + 1

    if any(identifier not in by_id for identifier in referenced):
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle history must contain exactly one root"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle history contains a fork"
        )

    head_ids = [identifier for identifier in by_id if identifier not in referenced]
    if len(head_ids) != 1:
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle history must contain exactly one head"
        )
    head = by_id[head_ids[0]]
    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError(
                "Support Process lifecycle history contains a cycle"
            )
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        if previous.record.field("to_status") != current.record.field("from_status"):
            raise WorkflowPrerequisiteError(
                "Support Process lifecycle predecessor status does not reconcile"
            )
        current = previous
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle history contains a disconnected transition"
        )
    return SupportProcessLifecycleState(selected, head)


def require_support_process_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    root: PortiaRecord,
) -> SupportProcessLifecycleState:
    """Require the selected root history head to match canonical status."""
    state = support_process_lifecycle_state(repository, work, root)
    selected_status = state.selected_status
    if selected_status is not None and selected_status != root.status:
        raise WorkflowPrerequisiteError(
            "canonical Support Process status does not reconcile with lifecycle history"
        )
    return state


def require_support_process_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Allow ordinary root lifecycle revisions to change metadata only."""
    require_revision_invariants(
        prior,
        candidate,
        transitions=_SUPPORT_PROCESS_STATUS_TRANSITIONS,
    )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    fields = set(prior_data) | set(candidate_data)
    for field in sorted(fields - _SUPPORT_PROCESS_REVISION_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                "ordinary Support Process lifecycle replacement cannot rewrite "
                f"field {field}"
            )


def require_coordinated_support_process_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require one legal non-supersession Support Process lifecycle change."""
    require_support_process_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle coordination requires a status change"
        )
    if candidate.status == "superseded":
        raise WorkflowPrerequisiteError(
            "Support Process supersession requires the later correction workflow"
        )
    if candidate.status not in {"active", "invalidated"}:
        raise WorkflowPrerequisiteError(
            f"ordinary Support Process lifecycle cannot select {candidate.status!r}"
        )


def _parsed_timestamp(value: object, description: str) -> datetime:
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


def _transition_reason(
    to_status: str,
    reason_code: str,
    reason_detail: str | None,
    *,
    allow_supersession: bool = False,
) -> dict[str, object]:
    if to_status == "superseded":
        if not allow_supersession:
            raise WorkflowPrerequisiteError(
                "Support Process supersession requires the correction workflow"
            )
        if reason_code == "duplicate_consolidated":
            category = "consolidation"
        elif reason_code == "contract_migrated":
            category = "migration"
        else:
            category = "correction"
    else:
        category = "workflow" if to_status == "active" else "record_validity"
    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Support Process lifecycle reason 'other' requires detail"
            )
        return {"category": "other", "code": "other", "detail": reason_detail}
    reason: dict[str, object] = {"category": category, "code": reason_code}
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Support Process lifecycle reason detail cannot be empty"
            )
        reason["detail"] = reason_detail
    return reason


def build_support_process_lifecycle_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
    allow_supersession: bool = False,
) -> PortiaRecord:
    """Build the exact next lifecycle_transition@1 without writing bytes."""
    _require_owner(work, prior)
    _require_owner(work, candidate)
    if allow_supersession:
        require_support_process_revision_invariants(prior, candidate)
        if candidate.status != "superseded":
            raise WorkflowPrerequisiteError(
                "Support Process correction transition requires superseded predecessor"
            )
    else:
        require_coordinated_support_process_transition(prior, candidate)
    state = require_support_process_lifecycle_reconciled(repository, work, prior)

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created_time = _parsed_timestamp(
        created_at,
        "Support Process transition created_at",
    )
    effective_time = _parsed_timestamp(
        effective,
        "Support Process transition effective_at",
    )
    root_created = _parsed_timestamp(
        prior.to_dict().get("created_at"),
        "Support Process created_at",
    )
    if effective_time < root_created:
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle effective_at cannot precede creation"
        )
    if effective_time > created_time:
        raise WorkflowPrerequisiteError(
            "Support Process lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if state.head is not None:
        head_id = state.head.record.logical_id
        if head_id is None:
            raise WorkflowOwnershipError(
                "selected Support Process lifecycle head has no identity"
            )
        previous = ExactLocalRecordRef(
            record_kind="lifecycle_transition",
            record_id=head_id,
            contract_version=_LIFECYCLE_VERSION,
        ).to_dict()

    return parse_portia_record(
        "lifecycle_transition",
        _LIFECYCLE_VERSION,
        {
            "schema_version": _LIFECYCLE_VERSION,
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": work.class_id,
            "work_id": work.work_id,
            "transition_id": transition_id,
            "target": _local_work_target(),
            "previous_transition": previous,
            "from_status": prior.status,
            "to_status": candidate.status,
            "reason": _transition_reason(
                str(candidate.status),
                reason_code,
                reason_detail,
                allow_supersession=allow_supersession,
            ),
            "effective_at": effective,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )
