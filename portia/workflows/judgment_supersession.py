"""Shared one-to-one material-correction rules for Event-local judgments."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.judgment_common import (
    JUDGMENT_CONTRACTS,
    JUDGMENT_VERSION,
    require_judgment_record_owner,
)

_SPECIAL_SUPERSESSION_REASONS = frozenset(
    {"duplicate_consolidated", "work_root_corrected", "contract_migrated"}
)
_DETERMINATION_RECONSIDERATION_REASONS = frozenset(
    {"reconsidered", "reversed_on_reconsideration"}
)
_NON_MATERIAL_FIELDS = frozenset(
    {
        "schema_version",
        "record_type",
        "module_id",
        "class_id",
        "work_id",
        "review_id",
        "classification_id",
        "hypothesis_id",
        "determination_id",
        "status",
        "supersedes",
        "creation_source",
        "created_at",
        "created_by",
        "updated_at",
        "updated_by",
    }
)
_REASON_FIELDS: dict[str, dict[str, frozenset[str]]] = {
    "review": {
        "review_reframed": frozenset({"trigger", "question", "review_subjects"}),
        "reviewer_corrected": frozenset({"reviewer"}),
        "target_corrected": frozenset({"target"}),
    },
    "classification": {
        "selector_corrected": frozenset({"selector"}),
        "target_corrected": frozenset({"target"}),
        "definition_corrected": frozenset({"result"}),
    },
    "hypothesis": {
        "hypothesis_refined": frozenset(
            {"proposition", "consideration_state", "review_ref", "evidence"}
        ),
        "hypothesis_reconsidered": frozenset(
            {"proposition", "consideration_state", "review_ref", "evidence"}
        ),
        "author_corrected": frozenset({"author"}),
        "target_corrected": frozenset({"target"}),
        "evidence_role_corrected": frozenset({"evidence"}),
    },
    "determination": {
        "outcome_corrected": frozenset({"outcome"}),
        "question_corrected": frozenset({"question"}),
        "decision_maker_corrected": frozenset({"decision_maker"}),
        "target_corrected": frozenset({"target"}),
        "authority_corrected": frozenset({"authority_context"}),
        "process_basis_corrected": frozenset({"process_basis"}),
    },
}
_BROAD_CORRECTION_REASONS = {
    "review": frozenset({"review_corrected", "other"}),
    "classification": frozenset({"classification_corrected", "other"}),
    "hypothesis": frozenset({"hypothesis_corrected", "other"}),
    "determination": frozenset({"other"}),
}


def require_exact_judgment_correction_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    successor: PortiaRecord,
) -> str:
    """Require one exact same-Event predecessor and return its declared reason."""
    if successor.contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError(
            "judgment correction requires Review, Classification, Hypothesis, "
            "or Determination"
        )
    require_judgment_record_owner(work, successor, contract=successor.contract)
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "judgment correction predecessor must belong to the selected exact Event"
        )
    if (
        predecessor.record_ref.record_kind != successor.contract
        or predecessor.record_ref.contract_version != JUDGMENT_VERSION
    ):
        raise WorkflowOwnershipError(
            "judgment correction predecessor must use the same exact v1 judgment family"
        )
    if successor.contract_version != JUDGMENT_VERSION:
        raise WorkflowOwnershipError(
            "judgment correction successor must use contract v1"
        )

    supersedes = successor.to_dict().get("supersedes")
    if not isinstance(supersedes, list) or len(supersedes) != 1:
        raise WorkflowPrerequisiteError(
            "ordinary material judgment correction requires exactly one predecessor"
        )
    entry = supersedes[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError("judgment supersession entry is malformed")
    reference = entry.get("work_record_ref")
    if not isinstance(reference, Mapping) or dict(reference) != predecessor.to_dict():
        raise WorkflowOwnershipError(
            "judgment successor must name the exact selected predecessor"
        )
    if successor.logical_id == predecessor.record_ref.record_id:
        raise WorkflowPrerequisiteError(
            "material judgment correction must create a distinct successor identity"
        )
    reason = entry.get("reason")
    if not isinstance(reason, str):
        raise WorkflowOwnershipError("judgment supersession reason is malformed")
    if reason in _SPECIAL_SUPERSESSION_REASONS:
        raise WorkflowPrerequisiteError(
            f"{reason} is a separate shared supersession operation"
        )
    if (
        successor.contract == "determination"
        and reason in _DETERMINATION_RECONSIDERATION_REASONS
    ):
        raise WorkflowPrerequisiteError(
            "Determination reconsideration/reversal requires "
            "the dedicated guarded workflow"
        )
    if reason == "other":
        detail = entry.get("detail")
        if not isinstance(detail, str) or not detail.strip():
            raise WorkflowPrerequisiteError(
                "judgment supersession reason 'other' requires bounded detail"
            )
    return reason


def _changed_material_fields(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> frozenset[str]:
    prior_data = prior.to_dict()
    successor_data = successor.to_dict()
    fields = (set(prior_data) | set(successor_data)) - _NON_MATERIAL_FIELDS
    return frozenset(
        field for field in fields if prior_data.get(field) != successor_data.get(field)
    )


def require_material_judgment_correction(
    prior: PortiaRecord,
    successor: PortiaRecord,
    supersession_reason: str,
) -> frozenset[str]:
    """Require an accepted one-to-one correction and return changed material fields."""
    if prior.contract not in JUDGMENT_CONTRACTS or prior.contract != successor.contract:
        raise WorkflowOwnershipError(
            "material judgment correction requires the same judgment family"
        )
    if (
        prior.contract_version != JUDGMENT_VERSION
        or successor.contract_version != JUDGMENT_VERSION
    ):
        raise WorkflowOwnershipError("material judgment correction requires v1 records")
    if prior.class_id != successor.class_id or prior.work_id != successor.work_id:
        raise WorkflowOwnershipError(
            "ordinary material judgment correction must remain in the same Event"
        )
    if prior.logical_id == successor.logical_id:
        raise WorkflowPrerequisiteError(
            "material judgment correction must create a distinct successor identity"
        )
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "material judgment correction requires active predecessor and "
            "successor judgments"
        )
    if supersession_reason in _SPECIAL_SUPERSESSION_REASONS:
        raise WorkflowPrerequisiteError(
            f"{supersession_reason} is not an ordinary material-correction reason"
        )
    if (
        prior.contract == "determination"
        and supersession_reason in _DETERMINATION_RECONSIDERATION_REASONS
    ):
        raise WorkflowPrerequisiteError(
            "Determination reconsideration/reversal is not an ordinary correction"
        )

    changed = _changed_material_fields(prior, successor)
    if not changed:
        raise WorkflowPrerequisiteError(
            "material judgment correction requires an actual substantive change"
        )

    # Reporter and reviewer Classification assertions are separate canonical
    # judgments. A stage change is therefore not an ordinary correction path.
    if prior.contract == "classification" and "stage" in changed:
        raise WorkflowPrerequisiteError(
            "Classification stage disagreement/progression is not supersession"
        )

    expected = _REASON_FIELDS[prior.contract].get(supersession_reason)
    if expected is not None:
        if not changed.intersection(expected):
            raise WorkflowPrerequisiteError(
                f"supersession reason {supersession_reason!r} does not match "
                "the judgment change"
            )
        return changed
    if supersession_reason in _BROAD_CORRECTION_REASONS[prior.contract]:
        return changed
    raise WorkflowPrerequisiteError(
        f"unsupported ordinary {prior.contract} correction reason "
        f"{supersession_reason!r}"
    )


def superseded_judgment_predecessor(
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> PortiaRecord:
    """Build the predecessor revision with only lifecycle metadata changed."""
    if prior.contract not in JUDGMENT_CONTRACTS or prior.contract != successor.contract:
        raise WorkflowOwnershipError(
            "judgment predecessor supersession requires one judgment family"
        )
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "judgment predecessor supersession requires active predecessor "
            "and successor"
        )
    successor_data = successor.to_dict()
    updated_at = successor_data.get("updated_at")
    updated_by = successor_data.get("updated_by")
    if not isinstance(updated_at, str) or not isinstance(updated_by, Mapping):
        raise WorkflowPrerequisiteError(
            "corrected judgment successor update provenance is incomplete"
        )
    data = prior.to_dict()
    data["status"] = "superseded"
    data["updated_at"] = updated_at
    data["updated_by"] = dict(updated_by)
    return parse_portia_record(prior.contract, prior.contract_version, data)
