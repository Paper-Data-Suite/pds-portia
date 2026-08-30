from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactLocalRecordRef, ExactPortiaWorkRecordRef
from portia.storage.errors import PortiaConflictError, PortiaNotFoundError
from portia.storage.paths import work_storage_history_path
from portia.storage.repository import PortiaRepository
from portia.storage.series import OperationJournalStore
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.judgment_transition import JudgmentLifecycleCoordinator
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

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
    data["supersedes"] = [
        {
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
    ]
    return parse_portia_record(prior.contract, "1", data)


def _reference(prior: PortiaRecord) -> ExactPortiaWorkRecordRef:
    identifier = prior.logical_id
    assert identifier is not None
    return ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind=prior.contract,
            record_id=identifier,
            contract_version="1",
        ),
    )


_CASES = (
    (
        "review",
        "rvw_prior",
        "rvw_successor",
        "review_reframed",
        ("question", {"kind": "other", "text": "Corrected bounded question."}),
    ),
    (
        "classification",
        "cls_prior",
        "cls_successor",
        "classification_corrected",
        (
            "result",
            {"kind": "unable_to_determine", "rationale": "Corrected rationale."},
        ),
    ),
    (
        "hypothesis",
        "hyp_prior",
        "hyp_successor",
        "hypothesis_refined",
        ("proposition", "A narrower contextual factor may be relevant."),
    ),
    (
        "determination",
        "det_prior",
        "det_successor",
        "outcome_corrected",
        ("outcome", {"kind": "unable_to_determine"}),
    ),
)


@pytest.mark.parametrize(
    ("contract", "prior_id", "successor_id", "reason", "field"),
    _CASES,
)
def test_coordinator_commits_exact_one_to_one_judgment_correction(
    tmp_path: Path,
    contract: str,
    prior_id: str,
    successor_id: str,
    reason: str,
    field: tuple[str, object],
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    prior = repository.create_work_record(work, _judgment(contract, prior_id))
    successor = _successor(prior.record, successor_id, reason, field=field)
    transition_id = f"lct_{contract}_correction"
    operation_id = f"op_{contract}_correction"

    coordinator = JudgmentLifecycleCoordinator(tmp_path, repository=repository)
    coordinator.commit_correction(
        _reference(prior.record),
        successor,
        expected=prior.fingerprint,
        transition_id=transition_id,
        operation_id=operation_id,
        successor_validator=lambda _record: None,
    )

    predecessor_after = repository.load_work_record(
        work, contract, "1", prior_id
    ).record
    successor_after = repository.load_work_record(
        work, contract, "1", successor_id
    ).record
    transition = repository.load_work_record(
        work, "lifecycle_transition", "1", transition_id
    ).record
    journal = OperationJournalStore(tmp_path).load_current(operation_id).revision

    assert predecessor_after.status == "superseded"
    assert successor_after.to_dict() == successor.to_dict()
    assert transition.field("from_status") == "active"
    assert transition.field("to_status") == "superseded"
    assert transition.field("reason")["category"] == "correction"
    assert transition.field("reason")["code"] == reason
    assert journal.field("state") == "completed"
    assert journal.field("operation_kind") == "activate_successor"

    history_path = work_storage_history_path(
        tmp_path,
        work,
        contract,
        prior_id,
        prior.fingerprint.digest,
    )
    assert history_path.is_file()


def test_correction_requires_family_specific_successor_validation(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    prior = repository.create_work_record(
        work, _judgment("classification", "cls_prior")
    )
    successor = _successor(
        prior.record,
        "cls_successor",
        "classification_corrected",
        field=(
            "result",
            {"kind": "unable_to_determine", "rationale": "Corrected rationale."},
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="family-specific"):
        JudgmentLifecycleCoordinator(tmp_path, repository=repository).commit_correction(
            _reference(prior.record),
            successor,
            expected=prior.fingerprint,
            transition_id="lct_cls_requires_validator",
        )

    assert repository.load_work_record(
        work, "classification", "1", "cls_prior"
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            work, "classification", "1", "cls_successor"
        )


def test_correction_rejects_stale_predecessor_fingerprint(tmp_path: Path) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    prior = repository.create_work_record(work, _judgment("review", "rvw_prior"))
    successor = _successor(
        prior.record,
        "rvw_successor",
        "review_reframed",
        field=("question", {"kind": "other", "text": "Corrected question."}),
    )
    wrong = repository.load_work(work).fingerprint

    with pytest.raises(PortiaConflictError, match="expected predecessor judgment"):
        JudgmentLifecycleCoordinator(tmp_path, repository=repository).commit_correction(
            _reference(prior.record),
            successor,
            expected=wrong,
            transition_id="lct_review_stale",
            successor_validator=lambda _record: None,
        )

    assert repository.load_work_record(
        work, "review", "1", "rvw_prior"
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(work, "review", "1", "rvw_successor")
