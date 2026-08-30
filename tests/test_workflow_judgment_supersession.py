from __future__ import annotations

from copy import deepcopy

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from portia.workflows.judgment_supersession import (
    require_exact_judgment_correction_predecessor,
    require_material_judgment_correction,
    superseded_judgment_predecessor,
)
from tests.workflow_helpers import AGENT, TIMESTAMP, event_ref

LATER = "2026-08-26T12:05:00-04:00"


def _judgment(contract: str, identifier: str) -> PortiaRecord:
    common: dict[str, object] = {
        "schema_version": "1",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "status": "active",
        "target": {"kind": "event"},
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }
    if contract == "review":
        common.update(
            {
                "record_type": "review",
                "review_id": identifier,
                "review_state": "completed",
                "trigger": {"kind": "routine_review"},
                "question": {
                    "kind": "evidence_review",
                    "text": "What information was considered?",
                },
                "reviewer": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
                "evidence_considered": [],
            }
        )
    elif contract == "classification":
        common.update(
            {
                "record_type": "classification",
                "classification_id": identifier,
                "selector": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
                "stage": "reporter_selected",
                "result": {
                    "kind": "unable_to_determine",
                    "rationale": "Synthetic original classification.",
                },
            }
        )
    elif contract == "hypothesis":
        common.update(
            {
                "record_type": "hypothesis",
                "hypothesis_id": identifier,
                "author": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
                "proposition": "A contextual factor may be relevant.",
                "consideration_state": "under_consideration",
                "evidence": [],
            }
        )
    elif contract == "determination":
        common.update(
            {
                "record_type": "determination",
                "determination_id": identifier,
                "question": "What bounded conclusion is supported?",
                "decision_maker": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
                "authority_context": {
                    "kind": "teacher_local",
                    "scope": "teacher_review",
                },
                "process_basis": {
                    "kind": "teacher_local",
                    "process_label": "Local teacher review",
                },
                "outcome": {"kind": "insufficient_information"},
            }
        )
    else:
        raise ValueError(contract)
    return parse_portia_record(contract, "1", common)


def _successor(
    prior: PortiaRecord,
    identifier: str,
    reason: str,
    *,
    field: tuple[str, object],
    detail: str | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    id_field = {
        "review": "review_id",
        "classification": "classification_id",
        "hypothesis": "hypothesis_id",
        "determination": "determination_id",
    }[prior.contract]
    data[id_field] = identifier
    data[field[0]] = field[1]
    data["created_at"] = LATER
    data["updated_at"] = LATER
    entry: dict[str, object] = {
        "work_record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": prior.contract,
                "record_id": prior.logical_id,
                "contract_version": "1",
            },
        },
        "reason": reason,
    }
    if detail is not None:
        entry["detail"] = detail
    data["supersedes"] = [entry]
    return parse_portia_record(prior.contract, "1", data)


def _reference(prior: PortiaRecord):
    return {
        "work_ref": event_ref().to_dict(),
        "record_ref": {
            "record_kind": prior.contract,
            "record_id": prior.logical_id,
            "contract_version": "1",
        },
    }


@pytest.mark.parametrize(
    ("contract", "reason", "field"),
    [
        (
            "review",
            "review_reframed",
            (
                "question",
                {"kind": "other", "text": "Corrected bounded question."},
            ),
        ),
        (
            "classification",
            "classification_corrected",
            (
                "result",
                {
                    "kind": "unable_to_determine",
                    "rationale": "Corrected rationale.",
                },
            ),
        ),
        (
            "hypothesis",
            "hypothesis_refined",
            ("proposition", "A narrower contextual factor may be relevant."),
        ),
        (
            "determination",
            "outcome_corrected",
            ("outcome", {"kind": "unable_to_determine"}),
        ),
    ],
)
def test_ordinary_material_correction_requires_exact_distinct_predecessor(
    contract: str,
    reason: str,
    field: tuple[str, object],
) -> None:
    prior = _judgment(contract, {
        "review": "rvw_prior",
        "classification": "cls_prior",
        "hypothesis": "hyp_prior",
        "determination": "det_prior",
    }[contract])
    successor = _successor(
        prior,
        {
            "review": "rvw_successor",
            "classification": "cls_successor",
            "hypothesis": "hyp_successor",
            "determination": "det_successor",
        }[contract],
        reason,
        field=field,
    )

    predecessor = ExactPortiaWorkRecordRef.from_dict(_reference(prior))
    selected_reason = require_exact_judgment_correction_predecessor(
        event_ref(), predecessor, successor
    )
    changed = require_material_judgment_correction(prior, successor, selected_reason)

    assert selected_reason == reason
    assert field[0] in changed


def test_reason_must_match_specific_correction_field() -> None:
    prior = _judgment("classification", "cls_prior")
    successor = _successor(
        prior,
        "cls_successor",
        "selector_corrected",
        field=("result", {"kind": "unable_to_determine", "rationale": "Changed."}),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="does not match"):
        require_material_judgment_correction(
            prior, successor, "selector_corrected"
        )


def test_classification_reviewer_disagreement_is_not_correction() -> None:
    prior = _judgment("classification", "cls_reporter")
    successor = _successor(
        prior,
        "cls_reviewer",
        "classification_corrected",
        field=("stage", "reviewer_selected"),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="not supersession"):
        require_material_judgment_correction(
            prior, successor, "classification_corrected"
        )


@pytest.mark.parametrize(
    "reason",
    ["duplicate_consolidated", "work_root_corrected", "contract_migrated"],
)
def test_special_supersession_reasons_do_not_enter_ordinary_correction(
    reason: str,
) -> None:
    prior = _judgment("review", "rvw_prior")
    successor = _successor(
        prior,
        "rvw_successor",
        reason,
        field=("question", {"kind": "other", "text": "Changed question."}),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="separate shared"):
        require_exact_judgment_correction_predecessor(
            event_ref(),
            ExactPortiaWorkRecordRef.from_dict(_reference(prior)),
            successor,
        )


@pytest.mark.parametrize("reason", ["reconsidered", "reversed_on_reconsideration"])
def test_determination_reconsideration_is_reserved_for_dedicated_workflow(
    reason: str,
) -> None:
    prior = _judgment("determination", "det_prior")
    successor = _successor(
        prior,
        "det_successor",
        reason,
        field=("outcome", {"kind": "unable_to_determine"}),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="dedicated guarded workflow"):
        require_exact_judgment_correction_predecessor(
            event_ref(),
            ExactPortiaWorkRecordRef.from_dict(_reference(prior)),
            successor,
        )


def test_superseded_predecessor_changes_only_lifecycle_metadata() -> None:
    prior = _judgment("hypothesis", "hyp_prior")
    successor = _successor(
        prior,
        "hyp_successor",
        "hypothesis_corrected",
        field=("proposition", "A corrected contextual proposition."),
    )

    candidate = superseded_judgment_predecessor(prior, successor)
    before = prior.to_dict()
    after = candidate.to_dict()

    assert candidate.status == "superseded"
    assert after["updated_at"] == LATER
    assert after["updated_by"] == successor.to_dict()["updated_by"]
    for field, value in before.items():
        if field not in {"status", "updated_at", "updated_by"}:
            assert after[field] == value


def test_exact_predecessor_must_match_successor_supersedes_entry() -> None:
    prior = _judgment("review", "rvw_prior")
    successor = _successor(
        prior,
        "rvw_successor",
        "review_corrected",
        field=("question", {"kind": "other", "text": "Changed question."}),
    )
    wrong = deepcopy(_reference(prior))
    wrong["record_ref"]["record_id"] = "rvw_other"  # type: ignore[index]

    with pytest.raises(WorkflowOwnershipError, match="exact selected predecessor"):
        require_exact_judgment_correction_predecessor(
            event_ref(), ExactPortiaWorkRecordRef.from_dict(wrong), successor
        )
