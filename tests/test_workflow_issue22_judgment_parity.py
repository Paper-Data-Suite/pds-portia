from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef
from portia.storage.repository import PortiaRepository
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ObservationWorkflowService,
    ReviewWorkflowService,
    account_reference,
    determination_reference,
    observation_reference,
    review_reference,
)
from tests.workflow_helpers import (
    AGENT,
    TIMESTAMP,
    event_record,
    event_ref,
    participant_record,
)


def _write_roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Synthetic",
                    "first_name": "One",
                    "period": "2",
                },
                {
                    "student_id": "student_2",
                    "last_name": "Synthetic",
                    "first_name": "Two",
                    "period": "2",
                },
                {
                    "student_id": "student_3",
                    "last_name": "Synthetic",
                    "first_name": "Three",
                    "period": "2",
                },
            ],
        ),
    )


def _participant_subject(student_id: str, display_name: str) -> dict[str, object]:
    return {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": "class_a",
            "student_id": student_id,
        },
        "display_snapshot": {"display_name": display_name},
    }


def _participant_target(participant_id: str) -> dict[str, object]:
    return {
        "kind": "event_participant",
        "record_ref": {
            "record_kind": "event_participant",
            "record_id": participant_id,
            "contract_version": "3",
        },
    }


def _roster_source(student_id: str, display_name: str) -> dict[str, object]:
    return {
        "kind": "roster_student",
        "roster_student_ref": {
            "class_id": "class_a",
            "student_id": student_id,
        },
        "display_snapshot": {"display_name": display_name},
    }


def _account_record(
    *,
    account_id: str,
    participant_id: str,
    source_student_id: str,
    source_display_name: str,
    text: str,
) -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": "active",
            "target": _participant_target(participant_id),
            "source": _roster_source(source_student_id, source_display_name),
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [{"representation": "recorded_summary", "text": text}],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _observation_record() -> PortiaRecord:
    return parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "observation_id": "obs_p22_direct",
            "status": "active",
            "target": _participant_target("ep_three"),
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": "Synthetic Teacher",
                },
            },
            "method": "manual_count",
            "content": {
                "measurements": [
                    {"measure_type": "count", "value": 1, "unit": "count"}
                ]
            },
            "observation_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _portia_record_evidence(
    reference: ExactPortiaWorkRecordRef,
) -> dict[str, object]:
    return {"kind": "portia_record", "work_record_ref": reference.to_dict()}


def _review_record(evidence: list[dict[str, object]]) -> PortiaRecord:
    return parse_portia_record(
        "review",
        "1",
        {
            "schema_version": "1",
            "record_type": "review",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "review_id": "rvw_p22_conflict",
            "status": "active",
            "review_state": "completed",
            "trigger": {"kind": "routine_review"},
            "question": {
                "kind": "evidence_review",
                "text": "Can the conflicting information be resolved from the record?",
            },
            "target": {"kind": "event"},
            "reviewer": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "evidence_considered": evidence,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def _determination_record(
    review_ref: dict[str, object],
    basis: list[dict[str, object]],
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
            "determination_id": "det_p22_unresolved",
            "status": "active",
            "target": {"kind": "event"},
            "question": "Can one bounded conclusion be supported from this record?",
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
                "process_label": "Synthetic bounded review",
            },
            "outcome": {"kind": "insufficient_information"},
            "review_ref": review_ref,
            "basis": basis,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_p22_02_conflicting_evidence_can_end_honestly_without_synthesized_judgment(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path)
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_one",
            subject=_participant_subject("student_1", "Synthetic One"),
        ),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_two",
            subject=_participant_subject("student_2", "Synthetic Two"),
        ),
    )
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_three",
            subject=_participant_subject("student_3", "Synthetic Three"),
        ),
    )

    accounts = AccountWorkflowService(tmp_path, repository=repository)
    account_one = accounts.create(
        work,
        _account_record(
            account_id="acct_p22_one",
            participant_id="ep_one",
            source_student_id="student_1",
            source_display_name="Synthetic One",
            text="Synthetic One reports that the disputed action occurred.",
        ),
    )
    account_two = accounts.create(
        work,
        _account_record(
            account_id="acct_p22_two",
            participant_id="ep_two",
            source_student_id="student_2",
            source_display_name="Synthetic Two",
            text="Synthetic Two reports that the disputed action did not occur.",
        ),
    )
    observation = ObservationWorkflowService(
        tmp_path, repository=repository
    ).create(work, _observation_record())

    account_one_ref = account_reference(work, "acct_p22_one")
    account_two_ref = account_reference(work, "acct_p22_two")
    observation_ref = observation_reference(work, "obs_p22_direct")
    evidence = [
        _portia_record_evidence(account_one_ref),
        _portia_record_evidence(account_two_ref),
        _portia_record_evidence(observation_ref),
    ]

    reviews = ReviewWorkflowService(tmp_path, repository=repository)
    review = reviews.create(work, _review_record(evidence))
    exact_review_ref = review_reference(work, "rvw_p22_conflict")
    basis = [
        {"relation": "supporting", "evidence_ref": evidence[0]},
        {"relation": "contrary", "evidence_ref": evidence[1]},
        {"relation": "contextual", "evidence_ref": evidence[2]},
    ]
    determinations = DeterminationWorkflowService(tmp_path, repository=repository)
    determination = determinations.create(
        work,
        _determination_record(exact_review_ref.to_dict(), basis),
    )

    assert account_one.record.logical_id != account_two.record.logical_id
    assert account_one.record.field("content") != account_two.record.field("content")
    assert observation.record.contract == "observation"
    assert review.record.field("evidence_considered") == tuple(evidence)
    assert (
        reviews.require_current_use(exact_review_ref).record.logical_id
        == review.record.logical_id
    )
    assert determination.record.field("outcome") == {"kind": "insufficient_information"}
    assert determinations.require_current_use(
        determination_reference(work, "det_p22_unresolved")
    ).record.logical_id == determination.record.logical_id
    assert ClassificationWorkflowService(
        tmp_path, repository=repository
    ).list_classifications(work) == ()
    assert HypothesisWorkflowService(
        tmp_path, repository=repository
    ).list_hypotheses(work) == ()


def _corrected_account_record(prior: PortiaRecord) -> PortiaRecord:
    data = deepcopy(prior.to_dict())
    data["account_id"] = "acct_p22_corrected"
    data["content"] = [
        {
            "representation": "recorded_summary",
            "text": "Synthetic One corrects the disputed-action account.",
        }
    ]
    data["created_at"] = "2026-08-26T13:00:00-04:00"
    data["updated_at"] = "2026-08-26T13:00:00-04:00"
    data["supersedes"] = [
        {
            "work_record_ref": account_reference(
                event_ref(), "acct_p22_original"
            ).to_dict(),
            "reason": "statement_corrected",
        }
    ]
    return parse_portia_record("account", "2", data)


def test_p22_04_account_correction_preserves_review_exact_historical_evidence(
    tmp_path: Path,
) -> None:
    _write_roster(tmp_path)
    repository = PortiaRepository(tmp_path)
    work = event_ref()
    repository.create_work(work, event_record(status="active"))
    repository.create_work_record(
        work,
        participant_record(
            participant_id="ep_one",
            subject=_participant_subject("student_1", "Synthetic One"),
        ),
    )

    accounts = AccountWorkflowService(tmp_path, repository=repository)
    original = accounts.create(
        work,
        _account_record(
            account_id="acct_p22_original",
            participant_id="ep_one",
            source_student_id="student_1",
            source_display_name="Synthetic One",
            text="Synthetic One reports the disputed action occurred.",
        ),
    )
    original_ref = account_reference(work, "acct_p22_original")
    original_evidence = _portia_record_evidence(original_ref)

    reviews = ReviewWorkflowService(tmp_path, repository=repository)
    review = reviews.create(work, _review_record([original_evidence]))
    review_ref = review_reference(work, "rvw_p22_conflict")

    successor = _corrected_account_record(original.record)
    accounts.correct(
        original_ref,
        successor,
        expected=original.fingerprint,
        transition_id="lct_p22_account_correction",
        operation_id="op_p22_account_correction",
    )

    predecessor_after = accounts.load_exact(original_ref)
    successor_ref = account_reference(work, "acct_p22_corrected")
    successor_after = accounts.require_current_use(successor_ref)
    review_current = reviews.require_current_use(review_ref)
    review_exact = reviews.load_exact(review_ref)

    assert predecessor_after.record.status == "superseded"
    assert successor_after.record.status == "active"
    assert successor_after.record.to_dict()["supersedes"] == [
        {
            "work_record_ref": original_ref.to_dict(),
            "reason": "statement_corrected",
        }
    ]
    assert review_current.fingerprint == review.fingerprint
    assert review_exact.fingerprint == review.fingerprint
    assert review_exact.record.field("evidence_considered") == (original_evidence,)
    assert review_current.record.field("evidence_considered") == (original_evidence,)
    assert review_exact.record.to_dict() == review.record.to_dict()

