"""Teacher-facing human-judgment workflows for Add Information."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from portia.menu.authoring import (
    ClassificationAuthoringInput,
    DeterminationAuthoringInput,
    EventEvidenceTargetInput,
    HypothesisAuthoringInput,
    JudgmentEvidenceInput,
    JudgmentEvidenceRelationInput,
    ReviewAuthoringInput,
    prepare_classification,
    prepare_determination,
    prepare_hypothesis,
    prepare_review,
)
from portia.menu.clock import MenuClock
from portia.menu.context import MenuSessionContext
from portia.menu.identifiers import PortiaIdGenerator
from portia.menu.prompts import confirm_write, prompt_text, select_one
from portia.menu.selectors import (
    ClassOption,
    EventOption,
    class_options,
    event_options,
    event_participant_options,
)
from portia.menu.ui import clear_screen, pause_for_user, print_menu_header
from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import (
    AccountWorkflowService,
    ClassificationWorkflowService,
    DeterminationWorkflowService,
    HypothesisWorkflowService,
    ObservationWorkflowService,
    ReviewWorkflowService,
)

_REVIEW_TRIGGERS: tuple[tuple[str, str], ...] = (
    ("concern", "Concern"),
    ("referral", "Referral"),
    ("routine_review", "Routine review"),
    ("support_related", "Support-related review"),
    ("other", "Other explicit reason"),
)
_REVIEW_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("evidence_review", "Review available evidence"),
    ("classification_review", "Review a possible classification"),
    ("hypothesis_review", "Review a possible hypothesis"),
    ("determination_review", "Review a possible determination"),
    ("other", "Other bounded review question"),
)
_RELATIONS: tuple[tuple[str, str], ...] = (
    ("supporting", "Supporting"),
    ("contrary", "Contrary"),
    ("contextual", "Contextual"),
)
_DETERMINATION_OUTCOMES: tuple[tuple[str, str], ...] = (
    ("conclusion", "Record a bounded conclusion"),
    ("insufficient_information", "Insufficient information"),
    ("unable_to_determine", "Unable to determine"),
    ("not_applicable", "Not applicable"),
)


@dataclass(frozen=True, slots=True)
class JudgmentEvidenceOption:
    """One exact selectable evidence reference with bounded display text."""

    evidence: JudgmentEvidenceInput
    label: str


def _show_result(title: str, *lines: str) -> None:
    clear_screen()
    print_menu_header(title)
    for line in lines:
        print(line)
    print()
    pause_for_user()


def _require_operator(state: MenuSessionContext) -> str:
    if state.local_operator_label is not None:
        return state.local_operator_label
    value = prompt_text(
        "Add Information — Judgment Author",
        "Display label",
        help_text=(
            "Enter the teacher-facing label for the person making this local judgment. "
            "This is provenance and represented-human attribution, not authentication."
        ),
    )
    assert value is not None
    state.remember_local_operator(value)
    assert state.local_operator_label is not None
    return state.local_operator_label


def _choose_class(root: Path) -> ClassOption:
    options = class_options(root)
    if not options:
        raise ValueError("No Core classes with both metadata and rosters are available.")
    return select_one(
        "Add Information — Judgment Event Class",
        options,
        tuple(item.label for item in options),
        help_text="Choose the exact Core class that owns the Event.",
    )


def _choose_event(root: Path, state: MenuSessionContext) -> EventOption:
    owner = _choose_class(root)
    options = tuple(
        item for item in event_options(root, owner.class_id)
        if item.status in {"active", "closed"}
    )
    if not options:
        raise ValueError(
            "No active or closed Event is available in this class for current human judgment."
        )
    selected = select_one(
        "Add Information — Judgment Event",
        options,
        tuple(item.label for item in options),
        help_text=(
            "Choose the exact Event. Current human-judgment records require an active "
            "or closed Event; draft Events are not silently converted into current judgments."
        ),
    )
    state.remember_work(
        class_id=selected.work.class_id,
        work_kind="event",
        work_id=selected.work.work_id,
    )
    return selected


def _choose_target(root: Path, event: EventOption) -> tuple[EventEvidenceTargetInput, str]:
    participants = event_participant_options(root, event.work)
    values: list[EventEvidenceTargetInput] = [EventEvidenceTargetInput(kind="event")]
    labels = ["Event as a whole"]
    for participant in participants:
        values.append(
            EventEvidenceTargetInput(
                kind="event_participant",
                participant_id=participant.participant_id,
            )
        )
        labels.append(participant.label)
    selected = select_one(
        "Add Information — Judgment Target",
        tuple(values),
        tuple(labels),
        help_text=(
            "Choose exactly what this judgment concerns. Participant choices carry exact "
            "Event-local participant identity; display names are not lookup authority."
        ),
    )
    index = values.index(selected)
    return selected, labels[index]


def _human_label(value: object) -> str:
    if not isinstance(value, Mapping):
        return "represented person"
    kind = value.get("kind")
    if kind == "local_operator":
        label = value.get("display_label")
        return label if isinstance(label, str) else "local operator"
    if kind == "roster_student":
        snapshot = value.get("display_snapshot")
        if isinstance(snapshot, Mapping) and isinstance(snapshot.get("display_name"), str):
            return str(snapshot["display_name"])
        return "roster student"
    if kind == "descriptive_person":
        label = value.get("display_label")
        return label if isinstance(label, str) else "described person"
    if kind == "unidentified_person":
        label = value.get("display_label")
        return label if isinstance(label, str) else "unidentified person"
    if kind == "actor":
        snapshot = value.get("display_snapshot")
        if isinstance(snapshot, Mapping) and isinstance(snapshot.get("display_name"), str):
            return str(snapshot["display_name"])
        return "Actor"
    return "represented person"


def _account_excerpt(record: PortiaRecord) -> str:
    content = record.field("content")
    if not isinstance(content, tuple) or not content:
        return "Account without displayable content"
    first = content[0]
    if not isinstance(first, Mapping):
        return "Account without displayable content"
    text = first.get("text")
    if not isinstance(text, str):
        return "Account without displayable content"
    return text if len(text) <= 72 else text[:69] + "..."


def _observation_excerpt(record: PortiaRecord) -> str:
    content = record.field("content")
    if not isinstance(content, Mapping):
        return "Observation without displayable content"
    narrative = content.get("narrative")
    if isinstance(narrative, str):
        return narrative if len(narrative) <= 72 else narrative[:69] + "..."
    measurements = content.get("measurements")
    if isinstance(measurements, tuple):
        return f"{len(measurements)} recorded measurement(s)"
    return "Observation without displayable content"


def _evidence_options(root: Path, work: ExactPortiaWorkRef) -> tuple[JudgmentEvidenceOption, ...]:
    options: list[JudgmentEvidenceOption] = [
        JudgmentEvidenceOption(
            JudgmentEvidenceInput(kind="event"),
            "The exact Event context",
        )
    ]
    for stored in AccountWorkflowService(root).list(work):
        record = stored.record
        if record.status != "active" or record.logical_id is None:
            continue
        options.append(
            JudgmentEvidenceOption(
                JudgmentEvidenceInput(
                    kind="account",
                    record_id=record.logical_id,
                    contract_version=record.contract_version,
                ),
                f"Account — {_human_label(record.field('source'))}: {_account_excerpt(record)}",
            )
        )
    for stored in ObservationWorkflowService(root).list(work):
        record = stored.record
        if record.status != "active" or record.logical_id is None:
            continue
        observer = record.field("observer")
        human = observer.get("human_attribution") if isinstance(observer, Mapping) else None
        options.append(
            JudgmentEvidenceOption(
                JudgmentEvidenceInput(
                    kind="observation",
                    record_id=record.logical_id,
                    contract_version=record.contract_version,
                ),
                f"Observation — {_human_label(human)}: {_observation_excerpt(record)}",
            )
        )
    return tuple(options)


def _choose_evidence(
    root: Path,
    work: ExactPortiaWorkRef,
    *,
    title: str,
) -> tuple[JudgmentEvidenceInput, ...]:
    remaining = list(_evidence_options(root, work))
    selected: list[JudgmentEvidenceInput] = []
    while remaining:
        values: tuple[JudgmentEvidenceOption | None, ...] = (None, *remaining)
        labels = ("Done selecting evidence", *(item.label for item in remaining))
        choice = select_one(
            title,
            values,
            labels,
            help_text=(
                "Select only exact material you actually considered. A reference records "
                "consideration; it does not establish truth, credibility, or weight."
            ),
        )
        if choice is None:
            break
        selected.append(choice.evidence)
        remaining.remove(choice)
    return tuple(selected)


def _relations_for(
    evidence: tuple[JudgmentEvidenceInput, ...],
    *,
    title: str,
) -> tuple[JudgmentEvidenceRelationInput, ...]:
    related: list[JudgmentEvidenceRelationInput] = []
    for index, item in enumerate(evidence, start=1):
        relation = select_one(
            f"{title} — Evidence {index}",
            tuple(value for value, _label in _RELATIONS),
            tuple(label for _value, label in _RELATIONS),
            help_text=(
                "Record the relationship you intend. Supporting, contrary, and contextual "
                "remain explicit human judgments and are not inferred by Portia."
            ),
        )
        related.append(JudgmentEvidenceRelationInput(relation=relation, evidence=item))
    return tuple(related)


def _target_label(target: EventEvidenceTargetInput, display: str) -> str:
    if target.kind == "event":
        return "Event as a whole"
    return display


def record_review_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state)
    target, target_display = _choose_target(root, event)
    trigger = select_one(
        "Add Information — Review Trigger",
        tuple(value for value, _label in _REVIEW_TRIGGERS),
        tuple(label for _value, label in _REVIEW_TRIGGERS),
        help_text="Choose why this explicit Review is being opened.",
    )
    trigger_detail = None
    if trigger == "other":
        trigger_detail = prompt_text(
            "Add Information — Review Trigger",
            "Reason",
            help_text="Describe the bounded reason this Review is being opened.",
        )
    question_kind = select_one(
        "Add Information — Review Question Type",
        tuple(value for value, _label in _REVIEW_QUESTIONS),
        tuple(label for _value, label in _REVIEW_QUESTIONS),
        help_text="Choose the semantic kind of question this Review will examine.",
    )
    question = prompt_text(
        "Add Information — Review Question",
        "Question",
        help_text="State the bounded question to be reviewed; do not enter a conclusion here.",
    )
    assert question is not None
    evidence = _choose_evidence(root, event.work, title="Add Information — Review Evidence")
    candidate = prepare_review(
        ReviewAuthoringInput(
            work=event.work,
            target=target,
            trigger_kind=trigger,
            trigger_detail=trigger_detail,
            question_kind=question_kind,
            question_text=question,
            evidence=evidence,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    lines = (
        f"Event: {event.summary}",
        f"Target: {_target_label(target, target_display)}",
        f"Reviewer: {operator}",
        f"Question: {question}",
        f"Evidence explicitly selected: {len(evidence)}",
        "Review state after recording: Open",
        "This does not create a Classification, Hypothesis, or Determination.",
    )
    if not confirm_write(
        "Add Information — Review Review",
        "RECORD",
        lines,
        help_text="This writes exactly one Review and no downstream judgment.",
    ):
        return
    stored = ReviewWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Review Recorded",
        f"Review for: {event.summary}",
        f"State: {str(stored.record.field('review_state')).replace('_', ' ').title()}",
        "No later judgment was created automatically.",
    )


def record_classification_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state)
    target, target_display = _choose_target(root, event)
    result_kind = select_one(
        "Add Information — Classification Result",
        ("category_selected", "unable_to_determine"),
        ("Select a defined category", "Unable to determine a category"),
        help_text=(
            "A Classification records a category selection. It does not establish a "
            "Hypothesis, Determination, policy violation, severity, or discipline."
        ),
    )
    scheme_id = scheme_version = category_code = category_label = definition_text = None
    unable_rationale = None
    if result_kind == "category_selected":
        scheme_id = prompt_text(
            "Add Information — Classification Definition",
            "Scheme ID",
            help_text="Enter the structurally safe identifier for the category scheme.",
        )
        scheme_version = prompt_text(
            "Add Information — Classification Definition",
            "Scheme version",
            help_text="Enter the exact structurally safe scheme version identifier.",
        )
        category_code = prompt_text(
            "Add Information — Classification Definition",
            "Category code",
            help_text="Enter the exact structurally safe category code.",
        )
        category_label = prompt_text(
            "Add Information — Classification Definition",
            "Category label",
            help_text="Enter the teacher-readable category label.",
        )
        definition_text = prompt_text(
            "Add Information — Classification Definition",
            "Definition",
            help_text="Record the category definition used for this selection.",
        )
    else:
        unable_rationale = prompt_text(
            "Add Information — Classification",
            "Rationale",
            help_text="Optionally record why a category could not be determined.",
            optional=True,
        )
    basis = _choose_evidence(root, event.work, title="Add Information — Classification Basis")
    candidate = prepare_classification(
        ClassificationAuthoringInput(
            work=event.work,
            target=target,
            result_kind=result_kind,
            scheme_id=scheme_id,
            scheme_version=scheme_version,
            category_code=category_code,
            category_label=category_label,
            definition_text=definition_text,
            unable_rationale=unable_rationale,
            basis=basis,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    result = candidate.field("result")
    result_label = "Unable to determine"
    if isinstance(result, Mapping) and result.get("kind") == "category_selected":
        definition = result.get("definition")
        if isinstance(definition, Mapping) and isinstance(definition.get("category_label"), str):
            result_label = str(definition["category_label"])
    if not confirm_write(
        "Add Information — Review Classification",
        "RECORD",
        (
            f"Event: {event.summary}",
            f"Target: {_target_label(target, target_display)}",
            f"Selector: {operator}",
            f"Result: {result_label}",
            f"Basis explicitly selected: {len(basis)}",
            "Stage: Reporter selected",
            "This does not create a Hypothesis or Determination.",
        ),
        help_text="This writes exactly one reporter-selected Classification.",
    ):
        return
    ClassificationWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Classification Recorded",
        f"Classification: {result_label}",
        "No Hypothesis, Determination, Response, or Support record was created.",
    )


def record_hypothesis_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state)
    target, target_display = _choose_target(root, event)
    proposition = prompt_text(
        "Add Information — Hypothesis",
        "Proposition",
        help_text=(
            "State the proposition being considered. A Hypothesis remains provisional "
            "and is not a Determination."
        ),
    )
    assert proposition is not None
    rationale = prompt_text(
        "Add Information — Hypothesis",
        "Rationale",
        help_text="Optionally record bounded rationale for considering this proposition.",
        optional=True,
    )
    evidence = _choose_evidence(root, event.work, title="Add Information — Hypothesis Evidence")
    relations = _relations_for(evidence, title="Add Information — Hypothesis")
    candidate = prepare_hypothesis(
        HypothesisAuthoringInput(
            work=event.work,
            target=target,
            proposition=proposition,
            rationale=rationale,
            evidence=relations,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    if not confirm_write(
        "Add Information — Review Hypothesis",
        "RECORD",
        (
            f"Event: {event.summary}",
            f"Target: {_target_label(target, target_display)}",
            f"Author: {operator}",
            f"Proposition: {proposition}",
            f"Evidence relationships recorded: {len(relations)}",
            "Consideration state: Under consideration",
            "This does not create a Determination.",
        ),
        help_text="This writes exactly one Hypothesis under consideration.",
    ):
        return
    HypothesisWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Hypothesis Recorded",
        f"Hypothesis: {proposition}",
        "It remains under consideration; no Determination was created automatically.",
    )


def record_determination_once(
    state: MenuSessionContext,
    *,
    clock: MenuClock | None = None,
    ids: PortiaIdGenerator | None = None,
) -> None:
    root = state.resolve_workspace()
    event = _choose_event(root, state)
    operator = _require_operator(state)
    target, target_display = _choose_target(root, event)
    question = prompt_text(
        "Add Information — Determination",
        "Question",
        help_text="State the bounded question this teacher-local determination answers.",
    )
    assert question is not None
    outcome_kind = select_one(
        "Add Information — Determination Outcome",
        tuple(value for value, _label in _DETERMINATION_OUTCOMES),
        tuple(label for _value, label in _DETERMINATION_OUTCOMES),
        help_text=(
            "Choose only the conclusion state you intend to record. This is teacher-local "
            "authority and does not imply institutional adjudication or downstream action."
        ),
    )
    conclusion = None
    if outcome_kind == "conclusion":
        conclusion = prompt_text(
            "Add Information — Determination Conclusion",
            "Conclusion",
            help_text="Record the bounded teacher-local conclusion.",
        )
    rationale = prompt_text(
        "Add Information — Determination",
        "Rationale",
        help_text="Optionally record bounded rationale for this determination.",
        optional=True,
    )
    evidence = _choose_evidence(root, event.work, title="Add Information — Determination Basis")
    basis = _relations_for(evidence, title="Add Information — Determination")
    candidate = prepare_determination(
        DeterminationAuthoringInput(
            work=event.work,
            target=target,
            question=question,
            outcome_kind=outcome_kind,
            conclusion_text=conclusion,
            rationale=rationale,
            basis=basis,
            local_operator_label=operator,
        ),
        clock=clock or MenuClock(),
        ids=ids or PortiaIdGenerator(),
    )
    outcome = candidate.field("outcome")
    outcome_label = outcome_kind.replace("_", " ").title()
    if isinstance(outcome, Mapping) and outcome.get("kind") == "conclusion":
        text = outcome.get("text")
        if isinstance(text, str):
            outcome_label = text
    if not confirm_write(
        "Add Information — Review Determination",
        "RECORD",
        (
            f"Event: {event.summary}",
            f"Target: {_target_label(target, target_display)}",
            f"Decision-maker: {operator}",
            "Authority: Teacher-local review",
            f"Question: {question}",
            f"Outcome: {outcome_label}",
            f"Basis relationships recorded: {len(basis)}",
            "This does not create a Response, Support, Follow-Up, or Outcome record.",
        ),
        help_text="This writes exactly one teacher-local Determination.",
    ):
        return
    DeterminationWorkflowService(root).create(event.work, candidate)
    _show_result(
        "Determination Recorded",
        f"Determination: {outcome_label}",
        "No downstream action or outcome was created automatically.",
    )
