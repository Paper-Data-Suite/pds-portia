from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from pds_core.class_metadata import (
    create_class_metadata,
    write_class_metadata_for_class,
)
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster
from pds_core.workspace import ensure_workspace_root

from portia.menu.authoring import (
    AccountAuthoringInput,
    ClassificationAuthoringInput,
    DeterminationAuthoringInput,
    EventAuthoringInput,
    EventEvidenceTargetInput,
    HumanAttributionInput,
    HypothesisAuthoringInput,
    JudgmentEvidenceInput,
    JudgmentEvidenceRelationInput,
    ReviewAuthoringInput,
    RosterParticipantInput,
    prepare_account,
    prepare_classification,
    prepare_determination,
    prepare_event_bundle,
    prepare_hypothesis,
    prepare_review,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.event import commit_prepared_event
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.information import launch_add_information_menu
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaRepository
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ReviewWorkflowService,
)

FIXED_NOW = datetime(2026, 9, 24, 2, 0, tzinfo=timezone.utc)


def _tokens(*values: str) -> PortiaIdGenerator:
    iterator = iter(values)
    return PortiaIdGenerator(lambda: next(iterator))


def _add_class(root: Path) -> None:
    ensure_workspace_root(root)
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )
    created = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    write_class_metadata_for_class(
        root,
        create_class_metadata("class_a", "2026-2027", created_at=created),
    )


def _seed_event(root: Path) -> ExactPortiaWorkRef:
    prepared = prepare_event_bundle(
        EventAuthoringInput(
            owner_class_id="class_a",
            school_year="2026-2027",
            occurrence=ExplicitOffsetTimestamp("2026-09-23T14:30:00-04:00"),
            summary="Synthetic Event context.",
            location_type="classroom",
            location_detail=None,
            local_operator_label="Synthetic Teacher",
            participants=(
                RosterParticipantInput(
                    class_id="class_a",
                    student_id="student_1",
                    display_name="Synthetic Student",
                ),
            ),
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("seed", "participant", "seedop"),
    )
    commit_prepared_event(root, prepared)
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_seed",
        work_kind="event",
        contract_version="2",
    )


def _seed_account(root: Path, work: ExactPortiaWorkRef) -> None:
    account = prepare_account(
        AccountAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            source=HumanAttributionInput(
                kind="local_operator",
                display_label="Synthetic Teacher",
            ),
            information_origin="firsthand",
            source_certainty="stated_certain",
            representation="recorded_summary",
            text="Synthetic bounded evidence.",
            provided_time=ExplicitOffsetTimestamp("2026-09-23T15:00:00-04:00"),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("basis"),
    )
    AccountWorkflowService(root).create(work, account)


def _account_evidence() -> JudgmentEvidenceInput:
    return JudgmentEvidenceInput(
        kind="account",
        record_id="acct_basis",
        contract_version="2",
    )


def test_prepare_review_is_open_and_does_not_encode_later_judgments() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    review = prepare_review(
        ReviewAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            trigger_kind="routine_review",
            trigger_detail=None,
            question_kind="evidence_review",
            question_text="What exact information is available?",
            evidence=(_account_evidence(),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("review"),
    )
    data = review.to_dict()
    assert data["review_id"] == "rvw_review"
    assert data["status"] == "active"
    assert data["review_state"] == "open"
    assert data["reviewer"] == {
        "kind": "local_operator",
        "display_label": "Synthetic Teacher",
    }
    assert data["evidence_considered"][0]["work_record_ref"]["record_ref"] == {
        "record_kind": "account",
        "record_id": "acct_basis",
        "contract_version": "2",
    }
    assert "result" not in data
    assert "outcome" not in data


def test_prepare_classification_preserves_definition_and_reporter_stage() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    classification = prepare_classification(
        ClassificationAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            result_kind="category_selected",
            scheme_id="teacher_local",
            scheme_version="v1",
            category_code="bounded_category",
            category_label="Bounded Category",
            definition_text="A bounded local category definition.",
            unable_rationale=None,
            basis=(_account_evidence(),),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("classification"),
    )
    data = classification.to_dict()
    assert data["classification_id"] == "cls_classification"
    assert data["stage"] == "reporter_selected"
    assert data["result"]["definition"] == {
        "scheme_id": "teacher_local",
        "scheme_version": "v1",
        "category_code": "bounded_category",
        "category_label": "Bounded Category",
        "definition_text": "A bounded local category definition.",
    }
    assert "review_ref" not in data
    assert "reviewed_classification" not in data


def test_prepare_hypothesis_is_under_consideration_not_determination() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    hypothesis = prepare_hypothesis(
        HypothesisAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            proposition="A contextual change may have contributed.",
            rationale="This remains provisional.",
            evidence=(
                JudgmentEvidenceRelationInput(
                    relation="contextual",
                    evidence=_account_evidence(),
                ),
            ),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("hypothesis"),
    )
    data = hypothesis.to_dict()
    assert data["hypothesis_id"] == "hyp_hypothesis"
    assert data["consideration_state"] == "under_consideration"
    assert data["evidence"][0]["relation"] == "contextual"
    assert "outcome" not in data


def test_prepare_determination_is_teacher_local_and_bounded() -> None:
    work = ExactPortiaWorkRef("class_a", "evt_seed", "event", "2")
    determination = prepare_determination(
        DeterminationAuthoringInput(
            work=work,
            target=EventEvidenceTargetInput(kind="event"),
            question="What bounded conclusion is supported?",
            outcome_kind="insufficient_information",
            conclusion_text=None,
            rationale="More evidence would be needed for a conclusion.",
            basis=(
                JudgmentEvidenceRelationInput(
                    relation="contextual",
                    evidence=_account_evidence(),
                ),
            ),
            local_operator_label="Synthetic Teacher",
        ),
        clock=MenuClock(lambda: FIXED_NOW),
        ids=_tokens("determination"),
    )
    data = determination.to_dict()
    assert data["determination_id"] == "det_determination"
    assert data["authority_context"] == {
        "kind": "teacher_local",
        "scope": "teacher_review",
    }
    assert data["process_basis"] == {
        "kind": "teacher_local",
        "process_label": "Teacher-local review",
    }
    assert data["outcome"] == {"kind": "insufficient_information"}
    assert "review_ref" not in data


def test_four_judgment_writes_remain_independent_and_create_no_downstream_action(
    tmp_path: Path,
) -> None:
    _add_class(tmp_path)
    work = _seed_event(tmp_path)
    _seed_account(tmp_path, work)
    clock = MenuClock(lambda: FIXED_NOW)
    target = EventEvidenceTargetInput(kind="event")
    evidence = _account_evidence()

    ReviewWorkflowService(tmp_path).create(
        work,
        prepare_review(
            ReviewAuthoringInput(
                work=work,
                target=target,
                trigger_kind="routine_review",
                trigger_detail=None,
                question_kind="evidence_review",
                question_text="What information is available?",
                evidence=(evidence,),
                local_operator_label="Synthetic Teacher",
            ),
            clock=clock,
            ids=_tokens("one"),
        ),
    )
    ClassificationWorkflowService(tmp_path).create(
        work,
        prepare_classification(
            ClassificationAuthoringInput(
                work=work,
                target=target,
                result_kind="unable_to_determine",
                scheme_id=None,
                scheme_version=None,
                category_code=None,
                category_label=None,
                definition_text=None,
                unable_rationale="No bounded category selected.",
                basis=(evidence,),
                local_operator_label="Synthetic Teacher",
            ),
            clock=clock,
            ids=_tokens("one"),
        ),
    )
    HypothesisWorkflowService(tmp_path).create(
        work,
        prepare_hypothesis(
            HypothesisAuthoringInput(
                work=work,
                target=target,
                proposition="A contextual factor may be relevant.",
                rationale=None,
                evidence=(
                    JudgmentEvidenceRelationInput(
                        relation="contextual",
                        evidence=evidence,
                    ),
                ),
                local_operator_label="Synthetic Teacher",
            ),
            clock=clock,
            ids=_tokens("one"),
        ),
    )
    DeterminationWorkflowService(tmp_path).create(
        work,
        prepare_determination(
            DeterminationAuthoringInput(
                work=work,
                target=target,
                question="What bounded conclusion is supported?",
                outcome_kind="insufficient_information",
                conclusion_text=None,
                rationale=None,
                basis=(
                    JudgmentEvidenceRelationInput(
                        relation="contextual",
                        evidence=evidence,
                    ),
                ),
                local_operator_label="Synthetic Teacher",
            ),
            clock=clock,
            ids=_tokens("one"),
        ),
    )

    repository = PortiaRepository(tmp_path)
    assert len(repository.list_work_records(work, "review", version="1")) == 1
    assert len(repository.list_work_records(work, "classification", version="1")) == 1
    assert len(repository.list_work_records(work, "hypothesis", version="1")) == 1
    assert len(repository.list_work_records(work, "determination", version="1")) == 1
    for contract in (
        "response",
        "communication",
        "support",
        "follow_up",
        "outcome",
    ):
        assert repository.list_work_records(work, contract, version="1") == ()


def test_add_information_routes_each_judgment_as_an_independent_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "portia.menu.information.record_review_once",
        lambda *_args, **_kwargs: calls.append("review"),
    )
    monkeypatch.setattr(
        "portia.menu.information.record_classification_once",
        lambda *_args, **_kwargs: calls.append("classification"),
    )
    monkeypatch.setattr(
        "portia.menu.information.record_hypothesis_once",
        lambda *_args, **_kwargs: calls.append("hypothesis"),
    )
    monkeypatch.setattr(
        "portia.menu.information.record_determination_once",
        lambda *_args, **_kwargs: calls.append("determination"),
    )
    answers = iter(("4", "5", "6", "7", "b"))
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))

    launch_add_information_menu(MenuSessionContext())

    assert calls == ["review", "classification", "hypothesis", "determination"]
