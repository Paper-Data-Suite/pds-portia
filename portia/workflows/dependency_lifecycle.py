"""Lifecycle authority for canonical ``dependency@1`` declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import require_revision_invariants
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError

_DEPENDENCY_VERSION = "1"
_LIFECYCLE_VERSION = "1"
_DEPENDENCY_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}
_DEPENDENCY_REVISION_MUTABLE_FIELDS = frozenset(
    {"status", "updated_at", "updated_by"}
)
_DEPENDENCY_SUPERSESSION_REASONS = frozenset(
    {
        "dependent_corrected",
        "dependency_target_corrected",
        "strength_corrected",
        "evaluation_scope_corrected",
        "purpose_corrected",
        "duplicate_consolidated",
    }
)


@dataclass(frozen=True, slots=True)
class DependencyLifecycleState:
    """One exact linear lifecycle chain selected for one Dependency."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected Dependency lifecycle head has no valid to_status"
            )
        return value


def _require_owner(work: ExactPortiaWorkRef, record: PortiaRecord) -> None:
    if (
        (work.work_kind, work.contract_version)
        not in {("event", "2"), ("support_process", "1")}
        or record.contract != "dependency"
        or record.contract_version != _DEPENDENCY_VERSION
        or record.class_id != work.class_id
        or record.work_id != work.work_id
    ):
        raise WorkflowOwnershipError(
            "Dependency lifecycle requires exact event@2 or support_process@1 ownership"
        )


def _target(record: PortiaRecord) -> dict[str, object]:
    identifier = record.logical_id
    if not isinstance(identifier, str):
        raise WorkflowOwnershipError(
            "Dependency lifecycle target requires exact identity"
        )
    return {
        "kind": "local_record",
        "record_ref": ExactLocalRecordRef(
            record_kind="dependency",
            record_id=identifier,
            contract_version=_DEPENDENCY_VERSION,
        ).to_dict(),
    }


def _previous_transition_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_transition")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError("Dependency lifecycle predecessor is malformed")
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError("Dependency lifecycle predecessor is not exact")
    return str(previous["record_id"])


def dependency_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    dependency: PortiaRecord,
) -> DependencyLifecycleState:
    """Resolve persisted Dependency lifecycle without timestamp winner logic."""
    _require_owner(work, dependency)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work,
            "lifecycle_transition",
            version=_LIFECYCLE_VERSION,
        )
        if stored.record.field("target") == _target(dependency)
    )
    if not selected:
        return DependencyLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None or transition_id in by_id:
            raise WorkflowPrerequisiteError(
                "Dependency lifecycle repeats a transition identity"
            )
        by_id[transition_id] = stored
        previous_id = _previous_transition_id(stored.record)
        if previous_id is None:
            roots.append(stored)
        else:
            referenced[previous_id] = referenced.get(previous_id, 0) + 1

    if any(identifier not in by_id for identifier in referenced):
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle must contain exactly one root"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError("Dependency lifecycle contains a fork")

    heads = [identifier for identifier in by_id if identifier not in referenced]
    if len(heads) != 1:
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle must contain exactly one head"
        )
    head = by_id[heads[0]]
    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError("Dependency lifecycle contains a cycle")
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        if previous.record.field("to_status") != current.record.field("from_status"):
            raise WorkflowPrerequisiteError(
                "Dependency lifecycle predecessor status does not reconcile"
            )
        current = previous
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle contains a disconnected transition"
        )
    return DependencyLifecycleState(selected, head)


def require_dependency_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    dependency: PortiaRecord,
) -> DependencyLifecycleState:
    """Require selected lifecycle history to agree with canonical status."""
    state = dependency_lifecycle_state(repository, work, dependency)
    selected = state.selected_status
    if selected is not None and selected != dependency.status:
        raise WorkflowPrerequisiteError(
            "canonical Dependency status does not reconcile with lifecycle history"
        )
    return state


def require_dependency_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Permit ordinary lifecycle replacement to change lifecycle metadata only."""
    require_revision_invariants(
        prior,
        candidate,
        transitions=_DEPENDENCY_STATUS_TRANSITIONS,
    )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    fields = set(prior_data) | set(candidate_data)
    for field in sorted(fields - _DEPENDENCY_REVISION_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                "ordinary Dependency lifecycle replacement cannot rewrite "
                f"field {field}"
            )


def require_coordinated_dependency_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require one legal non-supersession Dependency lifecycle change."""
    require_dependency_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle coordination requires a status change"
        )
    if candidate.status == "superseded":
        raise WorkflowPrerequisiteError(
            "Dependency supersession requires correction or consolidation"
        )
    if candidate.status not in {"active", "invalidated"}:
        raise WorkflowPrerequisiteError(
            f"ordinary Dependency lifecycle cannot select {candidate.status!r}"
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
    if to_status == "active":
        if reason_code != "review_confirmed":
            raise WorkflowPrerequisiteError(
                "Dependency activation requires review_confirmed"
            )
        category = "workflow"
    elif to_status == "invalidated":
        if reason_code in _DEPENDENCY_SUPERSESSION_REASONS:
            raise WorkflowPrerequisiteError(
                "Dependency correction/consolidation reasons cannot invalidate a declaration"
            )
        category = "record_validity"
    elif to_status == "superseded":
        if not allow_supersession:
            raise WorkflowPrerequisiteError(
                "Dependency supersession requires correction or consolidation"
            )
        if reason_code not in _DEPENDENCY_SUPERSESSION_REASONS and reason_code != "other":
            raise WorkflowPrerequisiteError(
                f"unsupported Dependency supersession reason {reason_code!r}"
            )
        category = (
            "consolidation" if reason_code == "duplicate_consolidated" else "correction"
        )
    else:
        raise WorkflowPrerequisiteError(
            f"Dependency lifecycle cannot select status {to_status!r}"
        )

    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Dependency lifecycle reason 'other' requires detail"
            )
        return {"category": "other", "code": "other", "detail": reason_detail}
    reason: dict[str, object] = {"category": category, "code": reason_code}
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError(
                "Dependency lifecycle reason detail cannot be empty"
            )
        reason["detail"] = reason_detail
    return reason


def build_dependency_lifecycle_transition(
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
    """Build the exact next Dependency lifecycle transition without writing bytes."""
    _require_owner(work, prior)
    _require_owner(work, candidate)
    if allow_supersession:
        require_dependency_revision_invariants(prior, candidate)
        if candidate.status != "superseded":
            raise WorkflowPrerequisiteError(
                "Dependency successor coordination must supersede its predecessor"
            )
    else:
        require_coordinated_dependency_transition(prior, candidate)
    state = require_dependency_lifecycle_reconciled(repository, work, prior)

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created_time = _parsed_timestamp(created_at, "Dependency transition created_at")
    effective_time = _parsed_timestamp(effective, "Dependency transition effective_at")
    dependency_created = _parsed_timestamp(
        prior.to_dict().get("created_at"),
        "Dependency created_at",
    )
    if effective_time < dependency_created:
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle effective_at cannot precede creation"
        )
    if effective_time > created_time:
        raise WorkflowPrerequisiteError(
            "Dependency lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if state.head is not None:
        head_id = state.head.record.logical_id
        if not isinstance(head_id, str):
            raise WorkflowOwnershipError(
                "selected Dependency lifecycle head has no identity"
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
            "target": _target(prior),
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
