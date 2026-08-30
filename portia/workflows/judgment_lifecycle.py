"""Strict lifecycle planning and reconciliation for Event-local judgments."""

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
from portia.workflows.judgment_common import (
    JUDGMENT_CONTRACTS,
    JUDGMENT_VERSION,
    require_judgment_record_owner,
)

_LIFECYCLE_VERSION = "1"
JUDGMENT_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}
_JUDGMENT_REVISION_MUTABLE_FIELDS = frozenset({"status", "updated_at", "updated_by"})
_ACTIVATION_REASONS = {
    "review": frozenset({"review_started", "other"}),
    "classification": frozenset({"judgment_recorded", "other"}),
    "hypothesis": frozenset({"judgment_recorded", "other"}),
    "determination": frozenset({"judgment_recorded", "other"}),
}
_INVALIDATION_REASONS = {
    "review": frozenset(
        {
            "recording_error",
            "wrong_reviewer",
            "wrong_target",
            "wrong_question",
            "invalid_provenance",
            "prohibited_payload",
            "other",
        }
    ),
    "classification": frozenset(
        {
            "recording_error",
            "wrong_selector",
            "wrong_target",
            "wrong_definition",
            "invalid_provenance",
            "prohibited_payload",
            "other",
        }
    ),
    "hypothesis": frozenset(
        {
            "recording_error",
            "wrong_author",
            "wrong_target",
            "invalid_provenance",
            "prohibited_payload",
            "other",
        }
    ),
    "determination": frozenset(
        {
            "recording_error",
            "wrong_decision_maker",
            "wrong_target",
            "wrong_authority",
            "wrong_process_basis",
            "invalid_provenance",
            "prohibited_payload",
            "other",
        }
    ),
}
_SUPERSESSION_REASONS = {
    "review": frozenset(
        {
            "review_corrected",
            "review_reframed",
            "reviewer_corrected",
            "target_corrected",
            "duplicate_consolidated",
            "work_root_corrected",
            "contract_migrated",
            "other",
        }
    ),
    "classification": frozenset(
        {
            "classification_corrected",
            "selector_corrected",
            "target_corrected",
            "definition_corrected",
            "duplicate_consolidated",
            "work_root_corrected",
            "contract_migrated",
            "other",
        }
    ),
    "hypothesis": frozenset(
        {
            "hypothesis_corrected",
            "hypothesis_refined",
            "hypothesis_reconsidered",
            "author_corrected",
            "target_corrected",
            "evidence_role_corrected",
            "duplicate_consolidated",
            "work_root_corrected",
            "contract_migrated",
            "other",
        }
    ),
    "determination": frozenset(
        {
            "outcome_corrected",
            "question_corrected",
            "decision_maker_corrected",
            "target_corrected",
            "authority_corrected",
            "process_basis_corrected",
            "reconsidered",
            "reversed_on_reconsideration",
            "duplicate_consolidated",
            "work_root_corrected",
            "contract_migrated",
            "other",
        }
    ),
}

@dataclass(frozen=True, slots=True)
class JudgmentLifecycleState:
    """One exact linear lifecycle chain selected for a judgment record."""

    transitions: tuple[StoredRecord, ...]
    head: StoredRecord | None

    @property
    def selected_status(self) -> str | None:
        if self.head is None:
            return None
        value = self.head.record.field("to_status")
        if not isinstance(value, str):
            raise WorkflowOwnershipError(
                "selected judgment lifecycle head has no valid to_status"
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
        raise WorkflowOwnershipError(
            "judgment lifecycle previous_transition is malformed"
        )
    if (
        previous.get("record_kind") != "lifecycle_transition"
        or previous.get("contract_version") != _LIFECYCLE_VERSION
        or not isinstance(previous.get("record_id"), str)
    ):
        raise WorkflowOwnershipError(
            "judgment lifecycle previous_transition is not an exact "
            "lifecycle_transition@1 reference"
        )
    return str(previous["record_id"])


def _lifecycle_target(judgment: PortiaRecord) -> dict[str, object]:
    if judgment.contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError(
            "judgment lifecycle resolution requires a judgment record"
        )
    if judgment.contract_version != JUDGMENT_VERSION or judgment.logical_id is None:
        raise WorkflowOwnershipError(
            "judgment lifecycle target requires an exact v1 judgment identity"
        )
    return {
        "kind": "local_record",
        "record_ref": ExactLocalRecordRef(
            record_kind=judgment.contract,
            record_id=judgment.logical_id,
            contract_version=JUDGMENT_VERSION,
        ).to_dict(),
    }


def _targets_record(
    transition: PortiaRecord,
    judgment: PortiaRecord,
) -> bool:
    return transition.field("target") == _lifecycle_target(judgment)


def judgment_lifecycle_state(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    judgment: PortiaRecord,
) -> JudgmentLifecycleState:
    """Resolve one exact linear judgment lifecycle chain without timestamp sorting."""
    if judgment.contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError(
            "judgment lifecycle resolution requires Review, Classification, "
            "Hypothesis, or Determination"
        )
    require_judgment_record_owner(work, judgment, contract=judgment.contract)
    selected = tuple(
        stored
        for stored in repository.list_work_records(
            work, "lifecycle_transition", version=_LIFECYCLE_VERSION
        )
        if _targets_record(stored.record, judgment)
    )
    if not selected:
        return JudgmentLifecycleState((), None)

    by_id: dict[str, StoredRecord] = {}
    referenced: dict[str, int] = {}
    roots: list[StoredRecord] = []
    for stored in selected:
        transition_id = stored.record.logical_id
        if transition_id is None:
            raise WorkflowOwnershipError(
                "judgment lifecycle transition has no exact identity"
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
            "judgment lifecycle history references a missing predecessor"
        )
    if len(roots) != 1:
        raise WorkflowPrerequisiteError(
            "judgment lifecycle history must contain exactly one root transition"
        )
    if any(count != 1 for count in referenced.values()):
        raise WorkflowPrerequisiteError("judgment lifecycle history contains a fork")

    head_ids = sorted(identifier for identifier in by_id if identifier not in referenced)
    if len(head_ids) != 1:
        raise WorkflowPrerequisiteError(
            "judgment lifecycle history must contain exactly one selected head"
        )
    head = by_id[head_ids[0]]

    visited: set[str] = set()
    current = head
    while True:
        current_id = current.record.logical_id
        if current_id is None or current_id in visited:
            raise WorkflowPrerequisiteError(
                "judgment lifecycle history contains a cycle"
            )
        visited.add(current_id)
        previous_id = _previous_transition_id(current.record)
        if previous_id is None:
            break
        previous = by_id[previous_id]
        if previous.record.field("to_status") != current.record.field("from_status"):
            raise WorkflowPrerequisiteError(
                "judgment lifecycle predecessor status does not reconcile "
                "with its successor"
            )
        current = previous
    if len(visited) != len(selected):
        raise WorkflowPrerequisiteError(
            "judgment lifecycle history contains a disconnected transition"
        )
    return JudgmentLifecycleState(selected, head)


def require_judgment_lifecycle_reconciled(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    judgment: PortiaRecord,
) -> JudgmentLifecycleState:
    """Require the selected lifecycle head, when present, to equal canonical status."""
    state = judgment_lifecycle_state(repository, work, judgment)
    selected_status = state.selected_status
    if selected_status is not None and selected_status != judgment.status:
        raise WorkflowPrerequisiteError(
            "canonical judgment status does not reconcile with lifecycle history head"
        )
    return state


def require_judgment_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Allow only lifecycle metadata to change in an ordinary judgment transition."""
    if prior.contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError(
            "judgment revision invariants require a judgment record"
        )
    require_revision_invariants(
        prior,
        candidate,
        transitions=JUDGMENT_STATUS_TRANSITIONS,
    )
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    comparable_fields = set(prior_data) | set(candidate_data)
    for field in sorted(comparable_fields - _JUDGMENT_REVISION_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                f"ordinary {prior.contract} lifecycle replacement cannot rewrite "
                f"judgment field {field}"
            )


def require_coordinated_judgment_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require a real legal status change before coordinated persistence."""
    require_judgment_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "judgment lifecycle coordination requires a status change"
        )


def _transition_reason(
    contract: str,
    to_status: str,
    reason_code: str,
    reason_detail: str | None,
    *,
    allow_supersession: bool = False,
) -> dict[str, object]:
    if contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError("judgment lifecycle reason requires a judgment")
    if to_status == "active":
        allowed = _ACTIVATION_REASONS[contract]
        category = "workflow"
    elif to_status == "invalidated":
        allowed = _INVALIDATION_REASONS[contract]
        category = "record_validity"
    elif to_status == "superseded":
        if not allow_supersession:
            raise WorkflowPrerequisiteError(
                "judgment supersession requires the material successor/correction workflow"
            )
        allowed = _SUPERSESSION_REASONS[contract]
        if reason_code == "duplicate_consolidated":
            category = "consolidation"
        elif reason_code == "contract_migrated":
            category = "migration"
        else:
            category = "correction"
    else:
        raise WorkflowPrerequisiteError(
            f"ordinary judgment lifecycle coordination cannot select status {to_status!r}"
        )
    if reason_code not in allowed:
        raise WorkflowPrerequisiteError(
            f"reason {reason_code!r} is not valid for {contract} -> {to_status}"
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


def build_judgment_lifecycle_transition(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    prior: PortiaRecord,
    candidate: PortiaRecord,
    *,
    transition_id: str,
    reason_code: str,
    reason_detail: str | None = None,
    effective_at: str | None = None,
    _allow_supersession: bool = False,
) -> PortiaRecord:
    """Build the exact next lifecycle_transition@1 candidate without writing bytes."""
    require_judgment_record_owner(work, prior, contract=prior.contract)
    require_judgment_record_owner(work, candidate, contract=prior.contract)
    require_coordinated_judgment_transition(prior, candidate)
    state = require_judgment_lifecycle_reconciled(repository, work, prior)
    if not isinstance(prior.status, str) or not isinstance(candidate.status, str):
        raise WorkflowPrerequisiteError("judgment lifecycle status is incomplete")
    reason = _transition_reason(
        prior.contract,
        candidate.status,
        reason_code,
        reason_detail,
        allow_supersession=_allow_supersession,
    )

    candidate_data = candidate.to_dict()
    created_at = candidate_data.get("updated_at")
    created_by = candidate_data.get("updated_by")
    if not isinstance(created_at, str) or not isinstance(created_by, Mapping):
        raise WorkflowPrerequisiteError(
            "judgment lifecycle transition requires candidate update provenance"
        )
    effective = effective_at or created_at
    created = _parsed_timestamp(created_at, "judgment lifecycle created_at")
    effective_time = _parsed_timestamp(effective, "judgment lifecycle effective_at")
    judgment_created = _parsed_timestamp(
        prior.to_dict().get("created_at"), "judgment created_at"
    )
    if effective_time < judgment_created:
        raise WorkflowPrerequisiteError(
            "judgment lifecycle effective_at cannot precede judgment creation"
        )
    if effective_time > created:
        raise WorkflowPrerequisiteError(
            "judgment lifecycle effective_at cannot follow transition creation"
        )

    previous: dict[str, object] | None = None
    if state.head is not None:
        head_id = state.head.record.logical_id
        if head_id is None:
            raise WorkflowOwnershipError(
                "selected judgment lifecycle head has no identity"
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
