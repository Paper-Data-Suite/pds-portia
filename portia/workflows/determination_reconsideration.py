"""Pure topology validation for Determination reconsideration and reversal."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.judgment_common import require_judgment_record_owner

_RECONSIDERATION_REASONS = frozenset(
    {"reconsidered", "reversed_on_reconsideration"}
)


def _exact_reference(value: object, *, field_name: str) -> ExactPortiaWorkRecordRef:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"{field_name} is malformed")
    try:
        return ExactPortiaWorkRecordRef.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(f"{field_name} is malformed") from exc


def _require_exact_determination_predecessor(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    prior: PortiaRecord,
    successor: PortiaRecord,
) -> str:
    if predecessor.work_ref != work:
        raise WorkflowOwnershipError(
            "Determination reconsideration predecessor must belong to "
            "the selected Event"
        )
    if (
        predecessor.record_ref.record_kind != "determination"
        or predecessor.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            "Determination reconsideration requires an exact "
            "determination@1 predecessor"
        )
    if prior.contract != "determination" or prior.contract_version != "1":
        raise WorkflowOwnershipError(
            "Determination reconsideration prior must be determination@1"
        )
    if prior.logical_id != predecessor.record_ref.record_id:
        raise WorkflowOwnershipError(
            "supplied prior Determination does not match the selected predecessor"
        )
    require_judgment_record_owner(work, prior, contract="determination")
    require_judgment_record_owner(work, successor, contract="determination")
    if successor.contract_version != "1":
        raise WorkflowOwnershipError(
            "Determination reconsideration successor must use determination@1"
        )
    if prior.status != "active" or successor.status != "active":
        raise WorkflowPrerequisiteError(
            "Determination reconsideration requires active predecessor and successor"
        )
    if successor.logical_id == prior.logical_id:
        raise WorkflowPrerequisiteError(
            "Determination reconsideration must create a distinct successor identity"
        )

    supersedes = successor.to_dict().get("supersedes")
    if not isinstance(supersedes, list) or len(supersedes) != 1:
        raise WorkflowPrerequisiteError(
            "Determination reconsideration requires exactly one predecessor"
        )
    entry = supersedes[0]
    if not isinstance(entry, Mapping):
        raise WorkflowOwnershipError(
            "Determination reconsideration supersession entry is malformed"
        )
    selected = _exact_reference(
        entry.get("work_record_ref"),
        field_name="Determination reconsideration predecessor reference",
    )
    if selected != predecessor:
        raise WorkflowOwnershipError(
            "Determination successor predecessor does not match the supplied prior"
        )
    reason = entry.get("reason")
    if not isinstance(reason, str) or reason not in _RECONSIDERATION_REASONS:
        raise WorkflowPrerequisiteError(
            "Determination reconsideration requires reconsidered or "
            "reversed_on_reconsideration supersession reason"
        )
    return reason


def require_determination_reconsideration_topology(
    work: ExactPortiaWorkRef,
    predecessor: ExactPortiaWorkRecordRef,
    prior: PortiaRecord,
    review: PortiaRecord,
    successor: PortiaRecord,
) -> str:
    """Validate the bounded Review -> prior Determination -> successor topology."""
    reason = _require_exact_determination_predecessor(
        work,
        predecessor,
        prior,
        successor,
    )

    if review.contract != "review" or review.contract_version != "1":
        raise WorkflowOwnershipError(
            "Determination reconsideration requires an exact review@1"
        )
    require_judgment_record_owner(work, review, contract="review")
    review_id = review.logical_id
    if review_id is None:
        raise WorkflowOwnershipError(
            "Determination reconsideration Review lacks canonical identity"
        )
    if review.status != "active" or review.field("review_state") != "completed":
        raise WorkflowPrerequisiteError(
            "Determination reconsideration requires an active completed Review"
        )

    review_data = review.to_dict()
    trigger = review_data.get("trigger")
    if not isinstance(trigger, Mapping) or trigger.get("kind") != "reconsideration":
        raise WorkflowPrerequisiteError(
            "Determination reconsideration Review trigger must be reconsideration"
        )
    question = review_data.get("question")
    if not isinstance(question, Mapping) or question.get("kind") != "reconsideration":
        raise WorkflowPrerequisiteError(
            "Determination reconsideration Review question must be reconsideration"
        )

    subjects = review_data.get("review_subjects")
    if not isinstance(subjects, list):
        raise WorkflowPrerequisiteError(
            "Determination reconsideration Review must name the predecessor "
            "as a subject"
        )
    subject_refs = tuple(
        _exact_reference(
            value,
            field_name="Determination reconsideration Review subject",
        )
        for value in subjects
    )
    if predecessor not in subject_refs:
        raise WorkflowPrerequisiteError(
            "Determination reconsideration Review subject must match the predecessor"
        )

    successor_data = successor.to_dict()
    review_ref = _exact_reference(
        successor_data.get("review_ref"),
        field_name="Determination reconsideration review_ref",
    )
    if (
        review_ref.work_ref != work
        or review_ref.record_ref.record_kind != "review"
        or review_ref.record_ref.contract_version != "1"
        or review_ref.record_ref.record_id != review_id
    ):
        raise WorkflowOwnershipError(
            "Determination reconsideration successor must reference the exact Review"
        )

    prior_target = prior.to_dict().get("target")
    review_target = review_data.get("target")
    successor_target = successor_data.get("target")
    if prior_target != review_target or prior_target != successor_target:
        raise WorkflowPrerequisiteError(
            "Determination reconsideration predecessor, Review, and successor targets "
            "must match"
        )

    if (
        reason == "reversed_on_reconsideration"
        and prior.to_dict().get("outcome") == successor_data.get("outcome")
    ):
        raise WorkflowPrerequisiteError(
            "reversed_on_reconsideration requires a changed Determination outcome"
        )
    return reason
