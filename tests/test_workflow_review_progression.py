from __future__ import annotations

from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaConflictError
from portia.storage.paths import work_storage_history_path
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows import ReviewWorkflowService
from portia.workflows.errors import WorkflowPrerequisiteError
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    account_wire,
    event_record,
    event_ref,
    participant_record,
)

NEXT_TIMESTAMP = "2026-08-26T12:01:00-04:00"
LATER_TIMESTAMP = "2026-08-26T12:02:00-04:00"


def _review_wire(
    *,
    state: str = "open",
    evidence: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "1",
        "record_type": "review",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "review_id": "rvw_alpha",
        "status": "active",
        "review_state": state,
        "trigger": {"kind": "routine_review"},
        "question": {
            "kind": "evidence_review",
            "text": "What exact information is available for this Event?",
        },
        "target": {"kind": "event"},
        "reviewer": {
            "kind": "local_operator",
            "display_label": "Synthetic Teacher",
        },
        "evidence_considered": evidence or [],
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def _review_record(
    *,
    state: str = "open",
    evidence: list[dict[str, object]] | None = None,
) -> PortiaRecord:
    return parse_portia_record("review", "1", _review_wire(state=state, evidence=evidence))


def _candidate(
    prior: PortiaRecord,
    *,
    state: str | None = None,
    evidence: list[dict[str, object]] | None = None,
    updated_at: str = NEXT_TIMESTAMP,
    question_text: str | None = None,
) -> PortiaRecord:
    value = prior.to_dict()
    if state is not None:
        value["review_state"] = state
    if evidence is not None:
        value["evidence_considered"] = evidence
    if question_text is not None:
        question = dict(value["question"])
        question["text"] = question_text
        value["question"] = question
    value["updated_at"] = updated_at
    value["updated_by"] = {
        "type": "system_process",
        "process_id": "workflow_progression_test",
    }
    return parse_portia_record("review", "1", value)


def _repository_with_review(
    tmp_path: Path,
    *,
    state: str = "open",
    evidence: list[dict[str, object]] | None = None,
) -> tuple[PortiaRepository, object, ReviewWorkflowService, StoredRecord]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    service = ReviewWorkflowService(tmp_path, repository=repository)
    stored = service.create(work, _review_record(state=state, evidence=evidence))
    return repository, work, service, stored


def _account_evidence() -> dict[str, object]:
    return {
        "kind": "portia_record",
        "work_record_ref": {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "account",
                "record_id": "acct_alpha",
                "contract_version": "1",
            },
        },
    }


def _add_current_account(repository: PortiaRepository, work: object) -> None:
    repository.create_work_record(
        work,
        participant_record(
            subject={
                "kind": "descriptive_person",
                "description_type": "school_staff",
                "display_label": "Synthetic Staff Member",
            }
        ),
    )
    repository.create_work_record(
        work,
        parse_portia_record("account", "1", account_wire()),
    )


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("open", "open"),
        ("open", "in_review"),
        ("open", "awaiting_information"),
        ("open", "completed"),
        ("open", "cancelled"),
        ("in_review", "in_review"),
        ("in_review", "awaiting_information"),
        ("in_review", "completed"),
        ("in_review", "cancelled"),
        ("awaiting_information", "awaiting_information"),
        ("awaiting_information", "in_review"),
        ("awaiting_information", "completed"),
        ("awaiting_information", "cancelled"),
    ],
)
def test_review_workflow_accepts_issue16_state_matrix(
    tmp_path: Path,
    before: str,
    after: str,
) -> None:
    _, work, service, stored = _repository_with_review(tmp_path, state=before)

    revised = service.update_workflow(
        work,
        _candidate(stored.record, state=after),
        expected=stored.fingerprint,
    )

    assert revised.record.field("review_state") == after
    assert revised.record.status == "active"


def test_review_workflow_rejects_backward_transition_without_writing(tmp_path: Path) -> None:
    repository, work, service, stored = _repository_with_review(
        tmp_path, state="in_review"
    )
    original = stored.record.to_dict()

    with pytest.raises(WorkflowPrerequisiteError, match="illegal Review workflow"):
        service.update_workflow(
            work,
            _candidate(stored.record, state="open"),
            expected=stored.fingerprint,
        )

    assert (
        repository.load_work_record(work, "review", "1", "rvw_alpha").record.to_dict()
        == original
    )


def test_completed_and_cancelled_reviews_are_frozen(tmp_path: Path) -> None:
    for terminal in ("completed", "cancelled"):
        root = tmp_path / terminal
        _, work, service, stored = _repository_with_review(root, state=terminal)
        with pytest.raises(WorkflowPrerequisiteError, match="illegal Review workflow"):
            service.update_workflow(
                work,
                _candidate(stored.record, state=terminal),
                expected=stored.fingerprint,
            )


def test_review_workflow_appends_current_evidence_and_preserves_storage_history(
    tmp_path: Path,
) -> None:
    repository, work, service, stored = _repository_with_review(
        tmp_path, state="in_review"
    )
    _add_current_account(repository, work)
    evidence = _account_evidence()

    prior_bytes = stored.path.read_bytes()
    revised = service.update_workflow(
        work,
        _candidate(stored.record, evidence=[evidence]),
        expected=stored.fingerprint,
    )

    assert revised.record.to_dict()["evidence_considered"] == [evidence]
    history = work_storage_history_path(
        tmp_path,
        work,
        "review",
        "rvw_alpha",
        stored.fingerprint.digest,
    )
    assert history.read_bytes() == prior_bytes


def test_review_workflow_rejects_noncurrent_new_evidence(tmp_path: Path) -> None:
    repository, work, service, stored = _repository_with_review(
        tmp_path, state="in_review"
    )
    _add_current_account(repository, work)
    active = repository.load_work_record(work, "account", "1", "acct_alpha")
    stale_wire = active.record.to_dict()
    stale_wire["status"] = "invalidated"
    stale_wire["updated_at"] = NEXT_TIMESTAMP
    repository.replace_work_record(
        work,
        parse_portia_record("account", "1", stale_wire),
        expected=active.fingerprint,
    )

    with pytest.raises(WorkflowPrerequisiteError):
        service.update_workflow(
            work,
            _candidate(stored.record, evidence=[_account_evidence()]),
            expected=stored.fingerprint,
        )

    current = repository.load_work_record(work, "review", "1", "rvw_alpha")
    assert current.fingerprint == stored.fingerprint


def test_review_workflow_cannot_remove_previously_considered_evidence(
    tmp_path: Path,
) -> None:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    _add_current_account(repository, work)
    service = ReviewWorkflowService(tmp_path, repository=repository)
    stored = service.create(
        work,
        _review_record(state="in_review", evidence=[_account_evidence()]),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="remove or rewrite"):
        service.update_workflow(
            work,
            _candidate(stored.record, evidence=[]),
            expected=stored.fingerprint,
        )


def test_review_workflow_cannot_rewrite_substantive_question(tmp_path: Path) -> None:
    _, work, service, stored = _repository_with_review(tmp_path, state="in_review")

    with pytest.raises(WorkflowPrerequisiteError, match="substantive field question"):
        service.update_workflow(
            work,
            _candidate(stored.record, question_text="A different substantive question"),
            expected=stored.fingerprint,
        )


def test_review_workflow_requires_strictly_newer_updated_at(tmp_path: Path) -> None:
    _, work, service, stored = _repository_with_review(tmp_path, state="open")

    with pytest.raises(WorkflowPrerequisiteError, match="strictly advance updated_at"):
        service.update_workflow(
            work,
            _candidate(stored.record, state="in_review", updated_at=TIMESTAMP),
            expected=stored.fingerprint,
        )


def test_review_workflow_guarded_replace_rejects_stale_fingerprint(tmp_path: Path) -> None:
    _, work, service, stored = _repository_with_review(tmp_path, state="open")
    first = service.update_workflow(
        work,
        _candidate(stored.record, state="in_review"),
        expected=stored.fingerprint,
    )

    with pytest.raises(PortiaConflictError):
        service.update_workflow(
            work,
            _candidate(
                first.record,
                state="awaiting_information",
                updated_at=LATER_TIMESTAMP,
            ),
            expected=stored.fingerprint,
        )
