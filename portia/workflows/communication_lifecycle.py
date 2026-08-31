"""Lifecycle planning and reconciliation for executable ``communication@1`` records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import require_revision_invariants
from portia.workflows.communication_common import (
    require_current_communication_record_owner,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_LIFECYCLE_VERSION = "1"
_COMMUNICATION_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}
_COMMUNICATION_REVISION_MUTABLE_FIELDS = frozenset(
    {"status", "updated_at", "updated_by"}
)


@dataclass(frozen=True, slots=True)
class CommunicationLifecycleState:
    """One exact linear lifecycle chain selected for a Communication record."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected Communication lifecycle head has no valid to_status"
            )
        return value


def _previous_transition_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_transition")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError(
            "Communication lifecycle previous_transition is malformed"
        )
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "Communication lifecycle previous_transition is not an exact "
            "lifecycle_transition@1 reference"
        )
    return str(previous["record_id"])


def _lifecycle_target(communication: PortiaRecord) -> dict[str, object]:
    if (
        communication.contract != "communication"
        or communication.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Communication lifecycle target requires communication@1"
        )
    if communication.logical_id is None:
        raise WorkflowOwnershipError(
            "Communication lifecycle target requires an exact Communication identity"
        )
    return {
        "kind": "local_record",
        "record_ref": ExactLocalRecordRef(
            record_kind="communication",
            record_id=communication.logical_id,
            contract_version="1",
        ).to_dict(),
    }


def _targets_communication(
    transition: PortiaRecord,
    communication: PortiaRecord,
) -> bool:
    return transition.field("target") == _lifecycle_target(communication)


def communication_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    communication: PortiaRecord,
) -> CommunicationLifecycleState:
    """Resolve one exact linear Communication lifecycle chain without sorting."""
    require_current_communication_record_owner(work, communication)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work,
            "lifecycle_transition",
            version=_LIFECYCLE_VERSION,
        )
        if _targets_communication(stored.record, communication)
    )
    if not selected:
        return CommunicationLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None:
            raise WorkflowOwnershipError(
                "Communication lifecycle transition has no exact identity"
            )
        if transition_id in by_id:
            raise WorkflowPrerequisiteError(
                "Communication lifecycle history repeats a transition identity"
            )
        by_id[transition_id] = stored
        previous_id = _previous_transition_id(stored.record)
        if previous_id is None:
            roots.append(stored)
            continue
        referenced[previous_id] = referenced.get(previous_id, 0) + 1

    missing = sorted(identifier for identifier in referenced if identifier not in by_id)
    if missing:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle history must contain exactly one root transition"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError(
            "Communication lifecycle history contains a fork"
        )

    head_ids = sorted(
        identifier for identifier in by_id if identifier not in referenced
    )
    if len(head_ids) != 1:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle history must contain exactly one selected head"
        )
    head = by_id[head_ids[0]]

    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError(
                "Communication lifecycle history contains a cycle"
            )
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        if previous.record.field("to_status") != current.record.field("from_status"):
            raise WorkflowPrerequisiteError(
                "Communication lifecycle predecessor status does not reconcile "
                "with its successor"
            )
        current = previous

    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "Communication lifecycle history contains a disconnected transition"
        )
    return CommunicationLifecycleState(selected, head)


def require_communication_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    communication: PortiaRecord,
) -> CommunicationLifecycleState:
    """Require the selected lifecycle head, when present, to equal canonical status."""
    state = communication_lifecycle_state(repository, work, communication)
    selected_status = state.selected_status
    if selected_status is not None and selected_status != communication.status:
        raise WorkflowPrerequisiteError(
            "canonical Communication status does not reconcile with "
            "lifecycle history head"
        )
    return state


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
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(f"{description} lacks an explicit offset")
    return parsed


def require_communication_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Allow only lifecycle metadata to change in an ordinary transition."""
    if prior.contract != "communication" or candidate.contract != "communication":
        raise WorkflowOwnershipError(
            "Communication revision invariants require communication@1 records"
        )
    require_revision_invariants(
        prior,
        candidate,
        transitions=_COMMUNICATION_STATUS_TRANSITIONS,
    )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    comparable_fields = set(prior_data) | set(candidate_data)
    for field in sorted(comparable_fields - _COMMUNICATION_REVISION_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                "ordinary Communication lifecycle replacement cannot rewrite field "
                f"{field}"
            )


def require_coordinated_communication_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require one legal non-supersession Communication status change."""
    require_communication_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle coordination requires a status change"
        )
    if candidate.status == "superseded":
        raise WorkflowPrerequisiteError(
            "Communication supersession requires the material successor/"
            "correction workflow"
        )
    if candidate.status not in {"active", "invalidated"}:
        raise WorkflowPrerequisiteError(
            "ordinary Communication lifecycle cannot select status "
            f"{candidate.status!r}"
        )


def _transition_reason(
    to_status: str,
    reason_code: str,
    reason_detail: str | None,
    *,
    allow_supersession: bool = False,
) -> dict[str, object]:
    if to_status == "active":
        category = "workflow"
    elif to_status == "invalidated":
        category = "record_validity"
    elif to_status == "superseded":
        if not allow_supersession:
            raise WorkflowPrerequisiteError(
                "Communication supersession requires the material successor/"
                "correction workflow"
            )
        if reason_code == "duplicate_consolidated":
            category = "consolidation"
        elif reason_code == "contract_migrated":
            category = "migration"
        else:
            category = "correction"
    else:
        raise WorkflowPrerequisiteError(
            f"Communication lifecycle cannot select status {to_status!r}"
        )
    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError("lifecycle reason 'other' requires detail")
        return {"category": "other", "code": "other", "detail": reason_detail}
    reason: dict[str, object] = {"category": category, "code": reason_code}
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError("lifecycle reason detail cannot be empty")
        reason["detail"] = reason_detail
    return reason


def build_communication_lifecycle_transition(
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
    """Build the exact next lifecycle_transition@1 without writing canonical bytes."""
    require_current_communication_record_owner(work, prior)
    require_current_communication_record_owner(work, candidate)
    if allow_supersession:
        require_communication_revision_invariants(prior, candidate)
        if candidate.status != "superseded":
            raise WorkflowPrerequisiteError(
                "Communication successor coordination must supersede its predecessor"
            )
    else:
        require_coordinated_communication_transition(prior, candidate)
    state = require_communication_lifecycle_reconciled(repository, work, prior)
    if not isinstance(prior.status, str) or not isinstance(candidate.status, str):
        raise WorkflowPrerequisiteError("Communication lifecycle status is incomplete")
    reason = _transition_reason(
        candidate.status,
        reason_code,
        reason_detail,
        allow_supersession=allow_supersession,
    )

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Communication lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created = _parsed_timestamp(created_at, "Communication lifecycle created_at")
    effective_time = _parsed_timestamp(
        effective,
        "Communication lifecycle effective_at",
    )
    communication_created = _parsed_timestamp(
        prior.to_dict().get("created_at"), "Communication created_at"
    )
    if effective_time < communication_created:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle effective_at cannot precede Communication creation"
        )
    if effective_time > created:
        raise WorkflowPrerequisiteError(
            "Communication lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if state.head is not None:
        head_id = state.head.record.logical_id
        if head_id is None:
            raise WorkflowOwnershipError(
                "selected Communication lifecycle head has no identity"
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
            "target": _lifecycle_target(prior),
            "previous_transition": previous,
            "from_status": prior.status,
            "to_status": candidate.status,
            "reason": reason,
            "effective_at": effective,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )
