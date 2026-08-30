from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef
from portia.storage.errors import PortiaNotFoundError
from portia.storage.paths import work_storage_history_path
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows.determination_reconsideration import (
    require_determination_reconsideration_topology,
)
from portia.workflows.determinations import DeterminationWorkflowService
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from portia.workflows.judgment_transition import JudgmentLifecycleCoordinator
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record, event_ref

LATER = "2026-08-26T13:00:00-04:00"


def _determination(
    determination_id: str,
    *,
    outcome: dict[str, object] | None = None,
    target: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "determination",
        "1",
        {
            "schema_version": "1",
            "record_type": "determination",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "determination_id": determination_id,
            "status": "active",
            "target": target or {"kind": "event"},
            "question": "What bounded conclusion is supported for this Event?",
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
            "outcome": outcome or {"kind": "insufficient_information"},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _predecessor() -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef.from_dict(
        {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "determination",
                "record_id": "det_prior",
                "contract_version": "1",
            },
        }
    )


def _review(
    predecessor: ExactPortiaWorkRecordRef,
    *,
    review_id: str = "rvw_reconsider",
    review_state: str = "completed",
    trigger_kind: str = "reconsideration",
    question_kind: str = "reconsideration",
    subjects: list[dict[str, object]] | None = None,
    target: dict[str, object] | None = None,
    work_id: str = "evt_alpha",
) -> PortiaRecord:
    return parse_portia_record(
        "review",
        "1",
        {
            "schema_version": "1",
            "record_type": "review",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": work_id,
            "review_id": review_id,
            "status": "active",
            "review_state": review_state,
            "trigger": {"kind": trigger_kind},
            "question": {
                "kind": question_kind,
                "text": "What Determination should follow reconsideration?",
            },
            "target": target or {"kind": "event"},
            "reviewer": {
                "kind": "local_operator",
                "display_label": "Synthetic Reviewer",
            },
            "review_subjects": subjects or [predecessor.to_dict()],
            "evidence_considered": [],
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": LATER,
            "updated_by": AGENT,
        },
    )


def _successor(
    prior: PortiaRecord,
    review: PortiaRecord,
    predecessor: ExactPortiaWorkRecordRef,
    *,
    reason: str = "reconsidered",
    outcome: dict[str, object] | None = None,
    target: dict[str, object] | None = None,
    selected_predecessor: ExactPortiaWorkRecordRef | None = None,
    review_id: str | None = None,
) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["determination_id"] = "det_after_reconsider"
    data["created_at"] = LATER
    data["updated_at"] = LATER
    if outcome is not None:
        data["outcome"] = outcome
    if target is not None:
        data["target"] = target
    data["review_ref"] = {
        "work_ref": event_ref().to_dict(),
        "record_ref": {
            "record_kind": "review",
            "record_id": review_id or review.logical_id,
            "contract_version": "1",
        },
    }
    data["supersedes"] = [
        {
            "work_record_ref": (
                selected_predecessor or predecessor
            ).to_dict(),
            "reason": reason,
        }
    ]
    return parse_portia_record("determination", "1", data)


def test_reconsidered_topology_may_preserve_outcome() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    successor = _successor(prior, review, predecessor)

    reason = require_determination_reconsideration_topology(
        event_ref(), predecessor, prior, review, successor
    )

    assert reason == "reconsidered"


def test_reversal_requires_and_accepts_changed_outcome() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    successor = _successor(
        prior,
        review,
        predecessor,
        reason="reversed_on_reconsideration",
        outcome={"kind": "unable_to_determine"},
    )

    reason = require_determination_reconsideration_topology(
        event_ref(), predecessor, prior, review, successor
    )

    assert reason == "reversed_on_reconsideration"


def test_reconsideration_review_must_belong_to_same_event() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor, work_id="evt_beta")
    successor = _successor(prior, review, predecessor)

    with pytest.raises(WorkflowOwnershipError):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_reconsideration_requires_completed_review() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor, review_state="in_review")
    successor = _successor(prior, review, predecessor)

    with pytest.raises(WorkflowPrerequisiteError, match="active completed Review"):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


@pytest.mark.parametrize(
    ("field_name", "kind", "message"),
    [
        ("trigger", "routine_review", "trigger must be reconsideration"),
        ("question", "determination_review", "question must be reconsideration"),
    ],
)
def test_reconsideration_requires_explicit_review_semantics(
    field_name: str,
    kind: str,
    message: str,
) -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    if field_name == "trigger":
        review = _review(predecessor, trigger_kind=kind)
    else:
        review = _review(predecessor, question_kind=kind)
    successor = _successor(prior, review, predecessor)

    with pytest.raises(WorkflowPrerequisiteError, match=message):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_reconsideration_review_subject_must_match_predecessor() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    other = ExactPortiaWorkRecordRef.from_dict(
        {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "determination",
                "record_id": "det_other",
                "contract_version": "1",
            },
        }
    )
    review = _review(predecessor, subjects=[other.to_dict()])
    successor = _successor(prior, review, predecessor)

    with pytest.raises(WorkflowPrerequisiteError, match="subject must match"):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_successor_review_ref_must_match_supplied_review() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    successor = _successor(
        prior,
        review,
        predecessor,
        review_id="rvw_other",
    )

    with pytest.raises(WorkflowOwnershipError, match="exact Review"):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_reconsideration_targets_must_match() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    successor = _successor(
        prior,
        review,
        predecessor,
        target={
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": "ep_alpha",
                "contract_version": "3",
            },
        },
    )

    with pytest.raises(WorkflowPrerequisiteError, match="targets must match"):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_reversal_rejects_same_outcome() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    successor = _successor(
        prior,
        review,
        predecessor,
        reason="reversed_on_reconsideration",
    )

    with pytest.raises(
        WorkflowPrerequisiteError, match="changed Determination outcome"
    ):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_successor_predecessor_must_match_supplied_prior() -> None:
    predecessor = _predecessor()
    prior = _determination("det_prior")
    review = _review(predecessor)
    other = ExactPortiaWorkRecordRef.from_dict(
        {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "determination",
                "record_id": "det_other",
                "contract_version": "1",
            },
        }
    )
    successor = _successor(
        prior,
        review,
        predecessor,
        selected_predecessor=other,
    )

    with pytest.raises(
        WorkflowOwnershipError, match="does not match the supplied prior"
    ):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def test_supplied_prior_identity_must_match_selected_predecessor() -> None:
    predecessor = _predecessor()
    prior = _determination("det_other")
    review = _review(predecessor)
    successor = _successor(prior, review, predecessor)

    with pytest.raises(WorkflowOwnershipError, match="supplied prior Determination"):
        require_determination_reconsideration_topology(
            event_ref(), predecessor, prior, review, successor
        )


def _review_reference(review: PortiaRecord) -> ExactPortiaWorkRecordRef:
    review_id = review.logical_id
    assert review_id is not None
    return ExactPortiaWorkRecordRef.from_dict(
        {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "review",
                "record_id": review_id,
                "contract_version": "1",
            },
        }
    )


def _persisted_reconsideration(
    tmp_path: Path,
    *,
    reason: str = "reconsidered",
    outcome: dict[str, object] | None = None,
) -> tuple[
    PortiaRepository,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRecordRef,
    PortiaRecord,
    StoredRecord,
]:
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    prior = repository.create_work_record(work, _determination("det_prior"))
    predecessor = _predecessor()
    review = repository.create_work_record(work, _review(predecessor))
    successor = _successor(
        prior.record,
        review.record,
        predecessor,
        reason=reason,
        outcome=outcome,
    )
    return (
        repository,
        predecessor,
        _review_reference(review.record),
        successor,
        prior,
    )


def test_coordinator_commits_reconsidered_successor_and_preserves_history(
    tmp_path: Path,
) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )
    transition_id = "lct_det_reconsidered"
    operation_id = "op_det_reconsidered"

    JudgmentLifecycleCoordinator(
        tmp_path, repository=repository
    ).commit_determination_reconsideration(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id=transition_id,
        operation_id=operation_id,
        successor_validator=lambda _record: None,
    )

    predecessor_after = repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record
    successor_after = repository.load_work_record(
        event_ref(), "determination", "1", "det_after_reconsider"
    ).record
    review_after = repository.load_work_record(
        event_ref(), "review", "1", "rvw_reconsider"
    ).record
    transition = repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", transition_id
    ).record
    journal = OperationJournalStore(tmp_path).load_current(operation_id).revision

    assert predecessor_after.status == "superseded"
    assert predecessor_after.field("outcome") == prior.record.field("outcome")
    assert successor_after.to_dict() == successor.to_dict()
    assert review_after.field("review_state") == "completed"
    assert review_after.status == "active"
    assert transition.field("reason")["code"] == "reconsidered"
    assert journal.field("state") == "completed"
    assert journal.field("operation_kind") == "activate_successor"
    assert work_storage_history_path(
        tmp_path,
        event_ref(),
        "determination",
        "det_prior",
        prior.fingerprint.digest,
    ).is_file()


def test_coordinator_commits_reversal_with_changed_outcome(tmp_path: Path) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(
            tmp_path,
            reason="reversed_on_reconsideration",
            outcome={"kind": "unable_to_determine"},
        )
    )

    JudgmentLifecycleCoordinator(
        tmp_path, repository=repository
    ).commit_determination_reconsideration(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id="lct_det_reversed",
        successor_validator=lambda _record: None,
    )

    predecessor_after = repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record
    successor_after = repository.load_work_record(
        event_ref(), "determination", "1", "det_after_reconsider"
    ).record
    transition = repository.load_work_record(
        event_ref(), "lifecycle_transition", "1", "lct_det_reversed"
    ).record

    assert predecessor_after.field("outcome") == {"kind": "insufficient_information"}
    assert successor_after.field("outcome") == {"kind": "unable_to_determine"}
    assert transition.field("reason")["code"] == "reversed_on_reconsideration"


def test_reconsideration_persistence_requires_family_specific_validation(
    tmp_path: Path,
) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )

    with pytest.raises(WorkflowPrerequisiteError, match="family-specific"):
        JudgmentLifecycleCoordinator(
            tmp_path, repository=repository
        ).commit_determination_reconsideration(
            predecessor,
            review_reference,
            successor,
            expected=prior.fingerprint,
            transition_id="lct_det_requires_validator",
        )

    assert repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            event_ref(), "determination", "1", "det_after_reconsider"
        )


def test_reconsideration_completed_operation_replays_without_reopening_prior(
    tmp_path: Path,
) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )
    coordinator = JudgmentLifecycleCoordinator(tmp_path, repository=repository)

    first = coordinator.commit_determination_reconsideration(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id="lct_det_replay",
        operation_id="op_det_replay",
        successor_validator=lambda _record: None,
    )
    second = coordinator.commit_determination_reconsideration(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id="lct_det_replay",
        operation_id="op_det_replay",
        successor_validator=lambda _record: None,
    )

    assert second.operation_id == first.operation_id
    assert repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record.status == "superseded"


def test_reconsideration_persistence_rejects_supplied_review_ref_mismatch(
    tmp_path: Path,
) -> None:
    repository, predecessor, _review_reference_value, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )
    wrong_review = ExactPortiaWorkRecordRef.from_dict(
        {
            "work_ref": event_ref().to_dict(),
            "record_ref": {
                "record_kind": "review",
                "record_id": "rvw_other",
                "contract_version": "1",
            },
        }
    )

    with pytest.raises(WorkflowOwnershipError, match="exact supplied Review"):
        JudgmentLifecycleCoordinator(
            tmp_path, repository=repository
        ).commit_determination_reconsideration(
            predecessor,
            wrong_review,
            successor,
            expected=prior.fingerprint,
            transition_id="lct_det_wrong_review",
            successor_validator=lambda _record: None,
        )

    assert repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record.status == "active"

def test_public_service_commits_reconsidered_successor(tmp_path: Path) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    service.reconsider(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id="lct_det_public_reconsidered",
        operation_id="op_det_public_reconsidered",
    )

    assert repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record.status == "superseded"
    assert service.require_current_use(
        ExactPortiaWorkRecordRef.from_dict(
            {
                "work_ref": event_ref().to_dict(),
                "record_ref": {
                    "record_kind": "determination",
                    "record_id": "det_after_reconsider",
                    "contract_version": "1",
                },
            }
        )
    ).record.to_dict() == successor.to_dict()


def test_public_service_commits_reversal_with_changed_outcome(tmp_path: Path) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(
            tmp_path,
            reason="reversed_on_reconsideration",
            outcome={"kind": "unable_to_determine"},
        )
    )
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    service.reconsider(
        predecessor,
        review_reference,
        successor,
        expected=prior.fingerprint,
        transition_id="lct_det_public_reversed",
    )

    stored = repository.load_work_record(
        event_ref(), "determination", "1", "det_after_reconsider"
    ).record
    assert stored.field("outcome") == {"kind": "unable_to_determine"}


def test_public_reconsideration_revalidates_successor_authority(
    tmp_path: Path,
) -> None:
    repository, predecessor, review_reference, successor, prior = (
        _persisted_reconsideration(tmp_path)
    )
    data = successor.to_dict()
    data["decision_maker"] = {
        "kind": "unidentified_person",
        "identity_status": "not_recorded",
    }
    invalid_successor = parse_portia_record("determination", "1", data)
    service = DeterminationWorkflowService(tmp_path, repository=repository)

    with pytest.raises(WorkflowPrerequisiteError, match="local-operator"):
        service.reconsider(
            predecessor,
            review_reference,
            invalid_successor,
            expected=prior.fingerprint,
            transition_id="lct_det_public_bad_authority",
        )

    assert repository.load_work_record(
        event_ref(), "determination", "1", "det_prior"
    ).record.status == "active"
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            event_ref(), "determination", "1", "det_after_reconsider"
        )

