from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ReviewWorkflowService,
    classification_reference,
    determination_reference,
    hypothesis_reference,
    review_reference,
)
from portia.workflows.errors import WorkflowPrerequisiteError
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref


def _judgment_record(contract: str, *, status: str = "active") -> PortiaRecord:
    common: dict[str, object] = {
        "schema_version": "1",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "status": status,
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
                "review_id": "rvw_lifecycle",
                "review_state": "open",
                "trigger": {"kind": "routine_review"},
                "question": {
                    "kind": "evidence_review",
                    "text": "What information is available for this Event?",
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
                "classification_id": "cls_lifecycle",
                "selector": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
                "stage": "reporter_selected",
                "result": {
                    "kind": "unable_to_determine",
                    "rationale": "Synthetic lifecycle fixture.",
                },
            }
        )
    elif contract == "hypothesis":
        common.update(
            {
                "record_type": "hypothesis",
                "hypothesis_id": "hyp_lifecycle",
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
                "determination_id": "det_lifecycle",
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


def _record_id(contract: str) -> str:
    return {
        "review": "rvw_lifecycle",
        "classification": "cls_lifecycle",
        "hypothesis": "hyp_lifecycle",
        "determination": "det_lifecycle",
    }[contract]


def _transition(
    contract: str,
    *,
    transition_id: str,
    from_status: str = "proposed",
    to_status: str = "active",
    previous_transition: str | None = None,
) -> PortiaRecord:
    previous: dict[str, object] | None = None
    if previous_transition is not None:
        previous = {
            "record_kind": "lifecycle_transition",
            "record_id": previous_transition,
            "contract_version": "1",
        }
    return parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "transition_id": transition_id,
            "target": {
                "kind": "local_record",
                "record_ref": {
                    "record_kind": contract,
                    "record_id": _record_id(contract),
                    "contract_version": "1",
                },
            },
            "previous_transition": previous,
            "from_status": from_status,
            "to_status": to_status,
            "reason": {
                "category": (
                    "workflow" if to_status == "active" else "record_validity"
                ),
                "code": (
                    "judgment_recorded" if to_status == "active" else "recording_error"
                ),
            },
            "effective_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
        },
    )


_CASES = (
    ("review", ReviewWorkflowService, review_reference),
    ("classification", ClassificationWorkflowService, classification_reference),
    ("hypothesis", HypothesisWorkflowService, hypothesis_reference),
    ("determination", DeterminationWorkflowService, determination_reference),
)


@pytest.mark.parametrize(("contract", "service_type", "reference_builder"), _CASES)
def test_current_use_accepts_matching_judgment_lifecycle_head(
    tmp_path: Path,
    contract: str,
    service_type: type,
    reference_builder: object,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = service_type(tmp_path, repository=repository)
    service.create(work, _judgment_record(contract))
    repository.create_work_record(
        work,
        _transition(contract, transition_id=f"lct_{contract}_active"),
    )

    reference = reference_builder(work, _record_id(contract))
    assert service.require_current_use(reference).record.status == "active"


@pytest.mark.parametrize(("contract", "service_type", "reference_builder"), _CASES)
def test_current_use_rejects_judgment_lifecycle_head_status_mismatch(
    tmp_path: Path,
    contract: str,
    service_type: type,
    reference_builder: object,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = service_type(tmp_path, repository=repository)
    service.create(work, _judgment_record(contract))
    repository.create_work_record(
        work,
        _transition(
            contract,
            transition_id=f"lct_{contract}_invalidated",
            to_status="invalidated",
        ),
    )
    reference = reference_builder(work, _record_id(contract))

    assert service.load_exact(reference).record.status == "active"
    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_current_use(reference)


def test_current_review_use_rejects_forked_lifecycle_history(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = ReviewWorkflowService(tmp_path, repository=repository)
    service.create(work, _judgment_record("review"))
    repository.create_work_record(
        work,
        _transition("review", transition_id="lct_review_root_a"),
    )
    repository.create_work_record(
        work,
        _transition("review", transition_id="lct_review_root_b"),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="exactly one root"):
        service.require_current_use(review_reference(work, "rvw_lifecycle"))


def test_current_review_use_rejects_missing_lifecycle_predecessor(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = ReviewWorkflowService(tmp_path, repository=repository)
    service.create(work, _judgment_record("review"))
    repository.create_work_record(
        work,
        _transition(
            "review",
            transition_id="lct_review_orphan",
            previous_transition="lct_review_missing",
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing predecessor"):
        service.require_current_use(review_reference(work, "rvw_lifecycle"))
