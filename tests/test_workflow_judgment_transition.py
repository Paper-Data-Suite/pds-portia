from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaConflictError
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
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

LATER = "2026-08-26T12:05:00-04:00"
LATEST = "2026-08-26T12:10:00-04:00"


def _judgment_record(contract: str, *, status: str) -> PortiaRecord:
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
                "review_id": "rvw_transition",
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
                "classification_id": "cls_transition",
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
                "hypothesis_id": "hyp_transition",
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
                "determination_id": "det_transition",
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
        "review": "rvw_transition",
        "classification": "cls_transition",
        "hypothesis": "hyp_transition",
        "determination": "det_transition",
    }[contract]


def _replace(
    record: PortiaRecord,
    *,
    status: str,
    updated_at: str = LATER,
    field: tuple[str, object] | None = None,
) -> PortiaRecord:
    data = deepcopy(record.to_dict())
    data["status"] = status
    data["updated_at"] = updated_at
    data["updated_by"] = AGENT
    if field is not None:
        data[field[0]] = field[1]
    return parse_portia_record(record.contract, record.contract_version, data)


_CASES = (
    (
        "review",
        ReviewWorkflowService,
        review_reference,
        "review_started",
    ),
    (
        "classification",
        ClassificationWorkflowService,
        classification_reference,
        "judgment_recorded",
    ),
    (
        "hypothesis",
        HypothesisWorkflowService,
        hypothesis_reference,
        "judgment_recorded",
    ),
    (
        "determination",
        DeterminationWorkflowService,
        determination_reference,
        "judgment_recorded",
    ),
)


@pytest.mark.parametrize(
    ("contract", "service_type", "reference_builder", "activation_reason"),
    _CASES,
)
def test_proposed_judgment_activation_is_coordinated_and_current(
    tmp_path: Path,
    contract: str,
    service_type: type,
    reference_builder: object,
    activation_reason: str,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = service_type(tmp_path, repository=repository)
    proposed = service.create(work, _judgment_record(contract, status="proposed"))
    candidate = _replace(proposed.record, status="active")
    reference = reference_builder(work, _record_id(contract))
    operation_id = f"op_{contract}_activation"

    service.transition_lifecycle(
        reference,
        candidate,
        expected=proposed.fingerprint,
        transition_id=f"lct_{contract}_activation",
        reason_code=activation_reason,
        operation_id=operation_id,
    )

    assert service.require_current_use(reference).record.status == "active"
    transition = repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        f"lct_{contract}_activation",
    ).record
    assert transition.field("from_status") == "proposed"
    assert transition.field("to_status") == "active"
    assert transition.field("previous_transition") is None
    reason = transition.field("reason")
    assert reason["category"] == "workflow"
    assert reason["code"] == activation_reason
    journal = OperationJournalStore(tmp_path).load_current(operation_id).revision
    assert journal.field("state") == "completed"
    assert journal.field("operation_kind") == "transition_lifecycle"


@pytest.mark.parametrize(
    ("contract", "service_type", "reference_builder", "activation_reason"),
    _CASES,
)
def test_active_judgment_invalidation_appends_to_existing_chain(
    tmp_path: Path,
    contract: str,
    service_type: type,
    reference_builder: object,
    activation_reason: str,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = service_type(tmp_path, repository=repository)
    proposed = service.create(work, _judgment_record(contract, status="proposed"))
    reference = reference_builder(work, _record_id(contract))
    active = _replace(proposed.record, status="active")
    service.transition_lifecycle(
        reference,
        active,
        expected=proposed.fingerprint,
        transition_id=f"lct_{contract}_active",
        reason_code=activation_reason,
    )
    active_stored = service.load_exact(reference)
    invalidated = _replace(
        active_stored.record,
        status="invalidated",
        updated_at=LATEST,
    )

    service.transition_lifecycle(
        reference,
        invalidated,
        expected=active_stored.fingerprint,
        transition_id=f"lct_{contract}_invalidated",
        reason_code="recording_error",
    )

    assert service.load_exact(reference).record.status == "invalidated"
    transition = repository.load_work_record(
        work,
        "lifecycle_transition",
        "1",
        f"lct_{contract}_invalidated",
    ).record
    previous = transition.field("previous_transition")
    assert previous["record_id"] == f"lct_{contract}_active"
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "invalidated"
    with pytest.raises(WorkflowPrerequisiteError, match="requires an active"):
        service.require_current_use(reference)


def test_review_activation_requires_review_specific_reason(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = ReviewWorkflowService(tmp_path, repository=repository)
    proposed = service.create(work, _judgment_record("review", status="proposed"))
    candidate = _replace(proposed.record, status="active")

    with pytest.raises(WorkflowPrerequisiteError, match="not valid for review"):
        service.transition_lifecycle(
            review_reference(work, "rvw_transition"),
            candidate,
            expected=proposed.fingerprint,
            transition_id="lct_review_wrong_reason",
            reason_code="judgment_recorded",
        )


def test_ordinary_transition_rejects_supersession_without_successor(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = DeterminationWorkflowService(tmp_path, repository=repository)
    active = service.create(work, _judgment_record("determination", status="active"))
    candidate = _replace(active.record, status="superseded")

    with pytest.raises(WorkflowPrerequisiteError, match="successor/correction"):
        service.transition_lifecycle(
            determination_reference(work, "det_transition"),
            candidate,
            expected=active.fingerprint,
            transition_id="lct_det_superseded",
            reason_code="outcome_corrected",
        )


def test_ordinary_transition_rejects_material_judgment_rewrite(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = HypothesisWorkflowService(tmp_path, repository=repository)
    proposed = service.create(work, _judgment_record("hypothesis", status="proposed"))
    candidate = _replace(
        proposed.record,
        status="active",
        field=("proposition", "A different proposition."),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="field proposition"):
        service.transition_lifecycle(
            hypothesis_reference(work, "hyp_transition"),
            candidate,
            expected=proposed.fingerprint,
            transition_id="lct_hyp_rewrite",
            reason_code="judgment_recorded",
        )


def test_transition_rejects_stale_expected_fingerprint(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = ClassificationWorkflowService(tmp_path, repository=repository)
    proposed = service.create(
        work,
        _judgment_record("classification", status="proposed"),
    )
    candidate = _replace(proposed.record, status="active")
    wrong = repository.load_work(work).fingerprint

    with pytest.raises(PortiaConflictError, match="expected judgment state"):
        service.transition_lifecycle(
            classification_reference(work, "cls_transition"),
            candidate,
            expected=wrong,
            transition_id="lct_cls_conflict",
            reason_code="judgment_recorded",
        )
