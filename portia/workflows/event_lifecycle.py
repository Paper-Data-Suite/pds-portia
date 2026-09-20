"""Version-explicit lifecycle authority for canonical Event work roots.

Issue #47 keeps Event root lifecycle evidence append-only while preserving the
existing version boundary: ``event@1`` remains historical-read authority and
``event@2`` remains current-write authority.  Migration may retire an exact
``event@1`` source as ``superseded`` only through the dedicated migration
validator/builder below; this module does not itself perform representation
migration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from portia.models import EventV1, EventV2, PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import (
    EVENT_STATUS_TRANSITIONS,
    require_revision_invariants,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_LIFECYCLE_VERSION = "1"
_EVENT_VERSIONS = frozenset({"1", "2"})
_EVENT_LIFECYCLE_MUTABLE_FIELDS = frozenset({"status", "updated_at", "updated_by"})


@dataclass(frozen=True, slots=True)
class EventLifecycleState:
    """One exact linear lifecycle chain selected for one Event root version."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected Event lifecycle head has no valid to_status"
            )
        return value


def _require_owner(work: ExactPortiaWorkRef, root: PortiaRecord) -> None:
    if (
        work.work_kind != "event"
        or work.contract_version not in _EVENT_VERSIONS
        or root.contract != "event"
        or root.contract_version != work.contract_version
        or root.class_id != work.class_id
        or root.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Event lifecycle requires exact event@1 or event@2 work-root ownership"
        )


def _work_target(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {
        "kind": "work",
        "work_kind": "event",
        "contract_version": work.contract_version,
    }


def _previous_transition_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_transition")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError("Event lifecycle previous_transition is malformed")
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "Event lifecycle previous_transition is not an exact "
            "lifecycle_transition@1 reference"
        )
    return str(previous["record_id"])


def event_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    root: PortiaRecord,
) -> EventLifecycleState:
    """Resolve one exact Event root history without timestamp winner logic."""
    _require_owner(work, root)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work,
            "lifecycle_transition",
            version=_LIFECYCLE_VERSION,
        )
        if stored.record.field("target") == _work_target(work)
    )
    if not selected:
        return EventLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None or transition_id in by_id:
            raise WorkflowPrerequisiteError(
                "Event lifecycle history repeats a transition identity"
            )
        by_id[transition_id] = stored
        previous_id = _previous_transition_id(stored.record)
        if previous_id is None:
            roots.append(stored)
        else:
            referenced[previous_id] = referenced.get(previous_id, 0) + 1

    if any(identifier not in by_id for identifier in referenced):
        raise WorkflowPrerequisiteError(
            "Event lifecycle history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "Event lifecycle history must contain exactly one root transition"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError("Event lifecycle history contains a fork")

    head_ids = [identifier for identifier in by_id if identifier not in referenced]
    if len(head_ids) != 1:
        raise WorkflowPrerequisiteError(
            "Event lifecycle history must contain exactly one selected head"
        )
    head = by_id[head_ids[0]]

    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError("Event lifecycle history contains a cycle")
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        if previous.record.field("to_status") != current.record.field("from_status"):
            raise WorkflowPrerequisiteError(
                "Event lifecycle predecessor status does not reconcile"
            )
        current = previous
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "Event lifecycle history contains a disconnected transition"
        )
    return EventLifecycleState(selected, head)


def require_event_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    root: PortiaRecord,
) -> EventLifecycleState:
    """Require the selected Event root history head to match canonical status."""
    state = event_lifecycle_state(repository, work, root)
    selected_status = state.selected_status
    if selected_status is not None and selected_status != root.status:
        raise WorkflowPrerequisiteError(
            "canonical Event status does not reconcile with lifecycle history"
        )
    return state


def require_event_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Allow Event lifecycle revisions to change status/update provenance only."""
    if not isinstance(prior, (EventV1, EventV2)) or not isinstance(
        candidate, (EventV1, EventV2)
    ):
        raise WorkflowOwnershipError(
            "Event lifecycle revision requires event@1 or event@2 records"
        )
    require_revision_invariants(
        prior,
        candidate,
        transitions=EVENT_STATUS_TRANSITIONS,
    )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    fields = set(prior_data) | set(candidate_data)
    for field in sorted(fields - _EVENT_LIFECYCLE_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                "Event lifecycle replacement cannot rewrite " f"field {field}"
            )


def require_coordinated_event_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require one ordinary current-write ``event@2`` lifecycle transition."""
    if not isinstance(prior, EventV2) or not isinstance(candidate, EventV2):
        raise WorkflowOwnershipError(
            "ordinary Event lifecycle mutation requires event@2"
        )
    require_event_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "Event lifecycle coordination requires a status change"
        )
    if candidate.status == "superseded":
        raise WorkflowPrerequisiteError(
            "Event supersession requires explicit correction or migration authority"
        )


def require_event_migration_supersession(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require the exact historical ``event@1`` retirement used by migration."""
    if not isinstance(prior, EventV1) or not isinstance(candidate, EventV1):
        raise WorkflowOwnershipError(
            "Event representation migration retirement requires event@1"
        )
    require_event_revision_invariants(prior, candidate)
    if candidate.status != "superseded" or prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "Event migration retirement requires a lifecycle change to superseded"
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
    candidate: PortiaRecord,
    reason_code: str,
    reason_detail: str | None,
    *,
    migration_supersession: bool,
) -> dict[str, object]:
    if migration_supersession:
        if reason_code != "contract_migrated":
            raise WorkflowPrerequisiteError(
                "Event migration supersession requires contract_migrated reason"
            )
        category = "migration"
    elif candidate.status == "invalidated":
        category = "record_validity"
    else:
        category = "workflow"

    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Event lifecycle reason 'other' requires detail"
            )
        return {"category": "other", "code": "other", "detail": reason_detail}

    reason: dict[str, object] = {"category": category, "code": reason_code}
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Event lifecycle reason detail cannot be empty"
            )
        reason["detail"] = reason_detail
    return reason


def _build_event_lifecycle_transition_from_selected_head(
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    selected_head: StoredRecord | None,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None,
    effective_at: str | None,
    migration_supersession: bool,
) -> PortiaRecord:
    _require_owner(work, prior)
    _require_owner(work, candidate)
    if migration_supersession:
        require_event_migration_supersession(prior, candidate)
    else:
        require_coordinated_event_transition(prior, candidate)

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Event lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created_time = _parsed_timestamp(created_at, "Event transition created_at")
    effective_time = _parsed_timestamp(effective, "Event transition effective_at")
    root_created = _parsed_timestamp(
        prior.to_dict().get("created_at"),
        "Event created_at",
    )
    if effective_time < root_created:
        raise WorkflowPrerequisiteError(
            "Event lifecycle effective_at cannot precede creation"
        )
    if effective_time > created_time:
        raise WorkflowPrerequisiteError(
            "Event lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if selected_head is not None:
        selected_record = selected_head.record
        if (
            selected_record.contract != "lifecycle_transition"
            or selected_record.contract_version != _LIFECYCLE_VERSION
            or selected_record.class_id != work.class_id
            or selected_record.work_id != work.work_id
            or selected_record.field("target") != _work_target(work)
        ):
            raise WorkflowOwnershipError(
                "selected Event lifecycle head does not belong to the exact work root"
            )
        if selected_record.field("to_status") != prior.status:
            raise WorkflowPrerequisiteError(
                "selected Event lifecycle head does not reconcile with canonical status"
            )
        head_id = selected_record.logical_id
        if head_id is None:
            raise WorkflowOwnershipError(
                "selected Event lifecycle head has no identity"
            )
        previous_effective = _parsed_timestamp(
            selected_record.field("effective_at"),
            "selected Event lifecycle predecessor effective_at",
        )
        if effective_time < previous_effective:
            raise WorkflowPrerequisiteError(
                "Event lifecycle effective_at cannot precede selected predecessor"
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
            "target": _work_target(work),
            "previous_transition": previous,
            "from_status": prior.status,
            "to_status": candidate.status,
            "reason": _transition_reason(
                candidate,
                reason_code,
                reason_detail,
                migration_supersession=migration_supersession,
            ),
            "effective_at": effective,
            "creation_source": {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": dict(created_by),
        },
    )


def _build_event_lifecycle_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None,
    effective_at: str | None,
    migration_supersession: bool,
) -> PortiaRecord:
    # Preserve the established validation ordering for the ordinary linear reader:
    # candidate legality is checked before persisted lifecycle-history selection.
    _require_owner(work, prior)
    _require_owner(work, candidate)
    if migration_supersession:
        require_event_migration_supersession(prior, candidate)
    else:
        require_coordinated_event_transition(prior, candidate)
    state = require_event_lifecycle_reconciled(repository, work, prior)
    return _build_event_lifecycle_transition_from_selected_head(
        work,
        prior,
        candidate,
        selected_head=state.head,
        transition_id=transition_id,
        reason_code=reason_code,
        reason_detail=reason_detail,
        effective_at=effective_at,
        migration_supersession=migration_supersession,
    )


def build_event_lifecycle_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
) -> PortiaRecord:
    """Build the exact next ordinary ``event@2`` lifecycle transition."""
    return _build_event_lifecycle_transition(
        repository,
        work,
        prior,
        candidate,
        transition_id=transition_id,
        reason_code=reason_code,
        reason_detail=reason_detail,
        effective_at=effective_at,
        migration_supersession=False,
    )


def build_event_migration_supersession_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
) -> PortiaRecord:
    """Build the exact ``event@1`` retirement transition for migration."""
    return _build_event_lifecycle_transition(
        repository,
        work,
        prior,
        candidate,
        transition_id=transition_id,
        reason_code="contract_migrated",
        reason_detail=reason_detail,
        effective_at=effective_at,
        migration_supersession=True,
    )


def build_event_migration_supersession_transition_from_selected_head(
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    selected_head: StoredRecord | None,
    transition_id: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
) -> PortiaRecord:
    """Build migration retirement from an independently selected Event history head.

    Callers must obtain ``selected_head`` from qualified Event lifecycle-history
    authority.  This entry point deliberately performs no winner selection itself;
    it only applies the same Event migration retirement, provenance, chronology,
    and exact-target validation used by the ordinary linear-history builder.
    """
    return _build_event_lifecycle_transition_from_selected_head(
        work,
        prior,
        candidate,
        selected_head=selected_head,
        transition_id=transition_id,
        reason_code="contract_migrated",
        reason_detail=reason_detail,
        effective_at=effective_at,
        migration_supersession=True,
    )
