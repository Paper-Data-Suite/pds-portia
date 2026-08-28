"""Strict Account/Observation lifecycle-chain planning and reconciliation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRef
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.evidence import (
    require_coordinated_evidence_transition,
    require_evidence_record_owner,
)

_LIFECYCLE_VERSION = "1"
_ACCOUNT_INVALIDATION_REASONS = frozenset(
    {
        "recording_error",
        "wrong_source",
        "wrong_target",
        "invalid_provenance",
        "prohibited_payload",
    }
)
_OBSERVATION_INVALIDATION_REASONS = frozenset(
    {
        "recording_error",
        "wrong_observer",
        "wrong_target",
        "wrong_method",
        "measurement_error",
        "invalid_provenance",
        "prohibited_payload",
    }
)
_REASON_CATEGORIES = {
    "review_completed": "workflow",
    "source_retracted": "workflow",
    "recording_error": "record_validity",
    "wrong_source": "record_validity",
    "wrong_observer": "record_validity",
    "wrong_target": "record_validity",
    "wrong_method": "record_validity",
    "measurement_error": "record_validity",
    "invalid_provenance": "record_validity",
    "prohibited_payload": "record_validity",
    "corrected_by_successor": "correction",
    "duplicate_consolidated": "consolidation",
    "work_root_corrected": "correction",
    "contract_migrated": "migration",
}


@dataclass(frozen=True, slots=True)
class EvidenceLifecycleState:
    """One exact linear lifecycle chain selected for an evidence record."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected lifecycle head has no valid to_status"
            )
        return value


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


def _previous_transition_id(record: PortiaRecord) -> str | None:
    previous = record.field("previous_transition")
    if previous is None:
        return None
    if not isinstance(previous, Mapping):
        raise WorkflowOwnershipError("lifecycle previous_transition is malformed")
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "lifecycle previous_transition is not an exact lifecycle_transition@1 reference"
        )
    return str(previous["record_id"])


def _lifecycle_target(evidence: PortiaRecord) -> dict[str, object]:
    if evidence.logical_id is None:
        raise WorkflowOwnershipError("lifecycle target evidence has no exact identity")
    return {
        "kind": "local_record",
        "record_ref": ExactLocalRecordRef(
            record_kind=evidence.contract,
            record_id=evidence.logical_id,
            contract_version=evidence.contract_version,
        ).to_dict(),
    }


def _targets_record(
    transition: PortiaRecord,
    work: ExactPortiaWorkRef,
    evidence: PortiaRecord,
) -> bool:
    require_evidence_record_owner(work, evidence, contract=evidence.contract)
    return transition.field("target") == _lifecycle_target(evidence)


def evidence_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    evidence: PortiaRecord,
) -> EvidenceLifecycleState:
    """Resolve one exact linear lifecycle chain without timestamp ordering."""
    if evidence.contract not in {"account", "observation"}:
        raise WorkflowOwnershipError(
            "evidence lifecycle resolution requires Account or Observation"
        )
    require_evidence_record_owner(work, evidence, contract=evidence.contract)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work, "lifecycle_transition", version=_LIFECYCLE_VERSION
        )
        if _targets_record(stored.record, work, evidence)
    )
    if not selected:
        return EvidenceLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None:
            raise WorkflowOwnershipError("lifecycle transition has no exact identity")
        by_id[transition_id] = stored
        previous_id = _previous_transition_id(stored.record)
        if previous_id is None:
            roots.append(stored)
            continue
        referenced[previous_id] = referenced.get(previous_id, 0) + 1

    missing = sorted(identifier for identifier in referenced if identifier not in by_id)
    if missing:
        raise WorkflowPrerequisiteError(
            "evidence lifecycle history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "evidence lifecycle history must contain exactly one root transition"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError("evidence lifecycle history contains a fork")

    head_ids = sorted(identifier for identifier in by_id if identifier not in referenced)
    if len(head_ids) != 1:
        raise WorkflowPrerequisiteError(
            "evidence lifecycle history must contain exactly one selected head"
        )
    head = by_id[head_ids[0]]

    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError("evidence lifecycle history contains a cycle")
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        previous_to = previous.record.field("to_status")
        current_from = current.record.field("from_status")
        if previous_to != current_from:
            raise WorkflowPrerequisiteError(
                "evidence lifecycle predecessor status does not reconcile with its successor"
            )
        current = previous
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "evidence lifecycle history contains a disconnected transition"
        )
    return EvidenceLifecycleState(selected, head)


def require_evidence_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    evidence: PortiaRecord,
) -> EvidenceLifecycleState:
    """Require the selected history head, when present, to equal canonical status."""
    state = evidence_lifecycle_state(repository, work, evidence)
    selected_status = state.selected_status
    if selected_status is not None and selected_status != evidence.status:
        raise WorkflowPrerequisiteError(
            "canonical evidence status does not reconcile with lifecycle history head"
        )
    return state


def _transition_reason(
    contract: str,
    from_status: str,
    to_status: str,
    reason_code: str,
    reason_detail: str | None,
    *,
    allow_account_retraction: bool = False,
    allow_supersession: bool = False,
) -> dict[str, object]:
    if to_status == "superseded":
        if not allow_supersession:
            raise WorkflowPrerequisiteError(
                "evidence supersession requires the material correction/successor workflow"
            )
        allowed = frozenset(
            {
                "corrected_by_successor",
                "duplicate_consolidated",
                "work_root_corrected",
                "contract_migrated",
            }
        )
        if reason_code not in allowed:
            raise WorkflowPrerequisiteError(
                f"reason {reason_code!r} is not valid for coordinated evidence supersession"
            )
        supersession_reason: dict[str, object] = {
            "category": _REASON_CATEGORIES[reason_code],
            "code": reason_code,
        }
        if reason_detail is not None:
            if not reason_detail.strip():
                raise WorkflowPrerequisiteError(
                    "lifecycle reason detail cannot be empty"
                )
            supersession_reason["detail"] = reason_detail
        return supersession_reason
    if contract == "account" and to_status == "retracted":
        if not allow_account_retraction:
            raise WorkflowPrerequisiteError(
                "Account retraction requires the source-evidenced retraction workflow"
            )
        if from_status != "active" or reason_code != "source_retracted":
            raise WorkflowPrerequisiteError(
                "Account retraction requires active -> retracted with source_retracted"
            )
        retraction_reason: dict[str, object] = {
            "category": _REASON_CATEGORIES[reason_code],
            "code": reason_code,
        }
        if reason_detail is not None:
            if not reason_detail.strip():
                raise WorkflowPrerequisiteError(
                    "lifecycle reason detail cannot be empty"
                )
            retraction_reason["detail"] = reason_detail
        return retraction_reason
    if to_status == "active":
        allowed = frozenset({"review_completed", "other"})
    elif to_status == "invalidated":
        invalidation = (
            _ACCOUNT_INVALIDATION_REASONS
            if contract == "account"
            else _OBSERVATION_INVALIDATION_REASONS
        )
        allowed = invalidation | {"other"}
    else:
        raise WorkflowPrerequisiteError(
            f"ordinary evidence lifecycle coordination does not handle {from_status} -> {to_status}"
        )
    if reason_code not in allowed:
        raise WorkflowPrerequisiteError(
            f"reason {reason_code!r} is not valid for ordinary "
            f"{contract} {from_status} -> {to_status}"
        )
    if reason_code == "other":
        if not isinstance(reason_detail, str) or not reason_detail.strip():
            raise WorkflowPrerequisiteError("lifecycle reason 'other' requires detail")
        return {"category": "other", "code": "other", "detail": reason_detail}
    reason: dict[str, object] = {
        "category": _REASON_CATEGORIES[reason_code],
        "code": reason_code,
    }
    if reason_detail is not None:
        if not reason_detail.strip():
            raise WorkflowPrerequisiteError("lifecycle reason detail cannot be empty")
        reason["detail"] = reason_detail
    return reason


def build_evidence_lifecycle_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
    _allow_account_retraction: bool = False,
    _allow_supersession: bool = False,
) -> PortiaRecord:
    """Build the exact next lifecycle_transition@1 candidate without writing bytes."""
    require_evidence_record_owner(work, prior, contract=prior.contract)
    require_evidence_record_owner(work, candidate, contract=prior.contract)
    require_coordinated_evidence_transition(prior, candidate)
    state = require_evidence_lifecycle_reconciled(repository, work, prior)
    if not isinstance(prior.status, str) or not isinstance(candidate.status, str):
        raise WorkflowPrerequisiteError("evidence lifecycle status is incomplete")
    reason = _transition_reason(
        prior.contract,
        prior.status,
        candidate.status,
        reason_code,
        reason_detail,
        allow_account_retraction=_allow_account_retraction,
        allow_supersession=_allow_supersession,
    )

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created = _parsed_timestamp(created_at, "lifecycle created_at")
    effective_time = _parsed_timestamp(effective, "lifecycle effective_at")
    evidence_created = _parsed_timestamp(
        prior.to_dict().get("created_at"), "evidence created_at"
    )
    if effective_time < evidence_created:
        raise WorkflowPrerequisiteError(
            "lifecycle effective_at cannot precede evidence creation"
        )
    if effective_time > created:
        raise WorkflowPrerequisiteError(
            "lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if state.head is not None:
        head_id = state.head.record.logical_id
        if head_id is None:
            raise WorkflowOwnershipError("selected lifecycle head has no identity")
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
