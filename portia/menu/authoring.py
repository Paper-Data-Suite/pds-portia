"""Typed candidate authoring for Portia teacher-menu workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from portia.menu.clock import MenuClock
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import (
    AccountV2,
    ClassificationV1,
    DeterminationV1,
    EventParticipantV3,
    EventV2,
    HypothesisV1,
    ObservationV2,
    ReviewV1,
    parse_portia_record,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.references import ExactPortiaWorkRef
from portia.workflows import EventBundle


@dataclass(frozen=True, slots=True)
class RosterParticipantInput:
    """Exact roster identity plus a nonauthoritative display snapshot."""

    class_id: str
    student_id: str
    display_name: str


@dataclass(frozen=True, slots=True)
class EventAuthoringInput:
    """Transient teacher-entered facts for one Event candidate."""

    owner_class_id: str
    school_year: str
    occurrence: ExplicitOffsetTimestamp
    summary: str
    location_type: str
    location_detail: str | None
    local_operator_label: str
    participants: tuple[RosterParticipantInput, ...]


@dataclass(frozen=True, slots=True)
class PreparedEventBundle:
    """Validated in-memory Event bundle plus fresh application operation identity."""

    bundle: EventBundle
    operation_id: str


EvidenceTargetKind = Literal["event", "event_participant"]
HumanAttributionKind = Literal[
    "local_operator",
    "roster_student",
    "descriptive_person",
    "unidentified_person",
]


@dataclass(frozen=True, slots=True)
class EventEvidenceTargetInput:
    """One exact Event-local evidence target selected by the teacher."""

    kind: EvidenceTargetKind
    participant_id: str | None = None


@dataclass(frozen=True, slots=True)
class HumanAttributionInput:
    """Transient represented-human attribution without authentication semantics."""

    kind: HumanAttributionKind
    display_label: str | None = None
    class_id: str | None = None
    student_id: str | None = None
    display_name: str | None = None
    description_type: str | None = None
    identity_status: str | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class AccountAuthoringInput:
    """Teacher-entered facts for one attributed Account."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    source: HumanAttributionInput
    information_origin: str
    source_certainty: str
    representation: str
    text: str
    provided_time: ExplicitOffsetTimestamp
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class ObservationAuthoringInput:
    """Teacher-entered facts for one direct human Observation."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    narrative: str
    observation_time: ExplicitOffsetTimestamp
    local_operator_label: str


JudgmentEvidenceKind = Literal["event", "account", "observation"]
JudgmentEvidenceRelation = str


@dataclass(frozen=True, slots=True)
class JudgmentEvidenceInput:
    """One exact Event-local material reference selected as judgment evidence."""

    kind: JudgmentEvidenceKind
    record_id: str | None = None
    contract_version: str | None = None


@dataclass(frozen=True, slots=True)
class JudgmentEvidenceRelationInput:
    """One explicit relationship between a judgment and selected evidence."""

    relation: JudgmentEvidenceRelation
    evidence: JudgmentEvidenceInput


@dataclass(frozen=True, slots=True)
class ReviewAuthoringInput:
    """Teacher-entered facts for one active, open Review."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    trigger_kind: str
    trigger_detail: str | None
    question_kind: str
    question_text: str
    evidence: tuple[JudgmentEvidenceInput, ...]
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class ClassificationAuthoringInput:
    """Teacher-entered facts for one reporter-selected Classification."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    result_kind: str
    scheme_id: str | None
    scheme_version: str | None
    category_code: str | None
    category_label: str | None
    definition_text: str | None
    unable_rationale: str | None
    basis: tuple[JudgmentEvidenceInput, ...]
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class HypothesisAuthoringInput:
    """Teacher-entered facts for one explicit Hypothesis under consideration."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    proposition: str
    rationale: str | None
    evidence: tuple[JudgmentEvidenceRelationInput, ...]
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class DeterminationAuthoringInput:
    """Teacher-local bounded conclusion without downstream action inference."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    question: str
    outcome_kind: str
    conclusion_text: str | None
    rationale: str | None
    basis: tuple[JudgmentEvidenceRelationInput, ...]
    local_operator_label: str


def _normalized_text(value: str, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _operator(display_label: str) -> dict[str, object]:
    return {
        "type": "local_operator",
        "display_label": _normalized_text(display_label, "local operator display label"),
    }


def _represented_human(value: HumanAttributionInput) -> dict[str, object]:
    if value.kind == "local_operator":
        if value.display_label is None:
            raise ValueError("local operator source requires a display label")
        return {
            "kind": "local_operator",
            "display_label": _normalized_text(value.display_label, "source display label"),
        }
    if value.kind == "roster_student":
        if value.class_id is None or value.student_id is None or value.display_name is None:
            raise ValueError("roster student source requires exact roster identity and display name")
        return {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": value.class_id,
                "student_id": value.student_id,
            },
            "display_snapshot": {
                "display_name": _normalized_text(value.display_name, "source display name")
            },
        }
    if value.kind == "descriptive_person":
        if value.description_type is None or value.display_label is None:
            raise ValueError("descriptive source requires a type and display label")
        result: dict[str, object] = {
            "kind": "descriptive_person",
            "description_type": value.description_type,
            "display_label": _normalized_text(value.display_label, "source display label"),
        }
        if value.detail is not None:
            detail = " ".join(value.detail.split())
            if detail:
                result["detail"] = detail
        return result
    if value.kind == "unidentified_person":
        if value.identity_status is None:
            raise ValueError("unidentified source requires an identity status")
        result = {
            "kind": "unidentified_person",
            "identity_status": value.identity_status,
        }
        if value.display_label is not None:
            label = " ".join(value.display_label.split())
            if label:
                result["display_label"] = label
        if value.detail is not None:
            detail = " ".join(value.detail.split())
            if detail:
                result["detail"] = detail
        return result
    raise ValueError(f"unsupported represented-human source kind: {value.kind}")


def _event_target(value: EventEvidenceTargetInput) -> dict[str, object]:
    if value.kind == "event":
        if value.participant_id is not None:
            raise ValueError("Event-level evidence target cannot include a participant ID")
        return {"kind": "event"}
    if value.kind == "event_participant":
        if value.participant_id is None:
            raise ValueError("participant evidence target requires an exact participant ID")
        return {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": value.participant_id,
                "contract_version": "3",
            },
        }
    raise ValueError(f"unsupported Event evidence target: {value.kind}")


def _require_event_work(work: ExactPortiaWorkRef) -> None:
    if work.work_kind != "event" or work.contract_version != "2":
        raise ValueError("this teacher-menu path requires an exact event@2 work")


def _judgment_evidence_ref(
    work: ExactPortiaWorkRef,
    evidence: JudgmentEvidenceInput,
) -> dict[str, object]:
    if evidence.kind == "event":
        if evidence.record_id is not None or evidence.contract_version is not None:
            raise ValueError("Event judgment evidence cannot include a child record identity")
        return {"kind": "portia_work", "work_ref": work.to_dict()}
    if evidence.kind not in {"account", "observation"}:
        raise ValueError(f"unsupported judgment evidence kind: {evidence.kind}")
    if evidence.record_id is None or evidence.contract_version is None:
        raise ValueError("record judgment evidence requires exact record identity and version")
    return {
        "kind": "portia_record",
        "work_record_ref": {
            "work_ref": work.to_dict(),
            "record_ref": {
                "record_kind": evidence.kind,
                "record_id": evidence.record_id,
                "contract_version": evidence.contract_version,
            },
        },
    }


def _judgment_relation(
    work: ExactPortiaWorkRef,
    value: JudgmentEvidenceRelationInput,
) -> dict[str, object]:
    return {
        "relation": value.relation,
        "evidence_ref": _judgment_evidence_ref(work, value.evidence),
    }


def _location(location_type: str, detail: str | None) -> dict[str, object]:
    value: dict[str, object] = {"type": location_type}
    if detail is not None:
        normalized = " ".join(detail.split())
        if normalized:
            value["detail"] = normalized
    return value


def prepare_event_bundle(
    request: EventAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> PreparedEventBundle:
    """Build schema-valid candidates without writing canonical Portia state."""

    if not request.participants:
        raise ValueError("an active Event requires at least one participant")
    summary = _normalized_text(request.summary, "Event summary")

    timestamp = clock.now().text
    actor = _operator(request.local_operator_label)
    event_id = ids.new("evt_")
    event_data: dict[str, object] = {
        "schema_version": "2",
        "record_type": "portia_work",
        "work_kind": "event",
        "module_id": "portia",
        "class_id": request.owner_class_id,
        "work_id": event_id,
        "school_year": request.school_year,
        "status": "active",
        "occurrence": {
            "precision": "exact",
            "started_at": request.occurrence.text,
        },
        "summary": summary,
        "location": _location(request.location_type, request.location_detail),
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": actor,
        "updated_at": timestamp,
        "updated_by": actor,
    }
    event = parse_portia_record("event", "2", event_data)
    if not isinstance(event, EventV2):
        raise TypeError("event authoring produced an unexpected runtime model")

    participants: list[EventParticipantV3] = []
    for participant in request.participants:
        record = parse_portia_record(
            "event_participant",
            "3",
            {
                "schema_version": "3",
                "record_type": "event_participant",
                "module_id": "portia",
                "class_id": request.owner_class_id,
                "work_id": event_id,
                "participant_id": ids.new("ep_"),
                "status": "active",
                "subject": {
                    "kind": "roster_student",
                    "roster_student_ref": {
                        "class_id": participant.class_id,
                        "student_id": participant.student_id,
                    },
                    "display_snapshot": {
                        "display_name": participant.display_name,
                    },
                },
                "creation_source": {"type": "digital_entry"},
                "created_at": timestamp,
                "created_by": actor,
                "updated_at": timestamp,
                "updated_by": actor,
            },
        )
        if not isinstance(record, EventParticipantV3):
            raise TypeError("participant authoring produced an unexpected runtime model")
        participants.append(record)

    return PreparedEventBundle(
        bundle=EventBundle(event=event, participants=tuple(participants)),
        operation_id=ids.new("op_"),
    )


def prepare_account(
    request: AccountAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> AccountV2:
    """Build one active Account without interpreting or resolving its truth."""

    _require_event_work(request.work)
    text = _normalized_text(request.text, "Account content")
    timestamp = clock.now().text
    record = parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "work_kind": "event",
            "class_id": request.work.class_id,
            "work_id": request.work.work_id,
            "account_id": ids.new("acct_"),
            "status": "active",
            "target": _event_target(request.target),
            "source": _represented_human(request.source),
            "information_origin": request.information_origin,
            "source_certainty": request.source_certainty,
            "content": [
                {
                    "representation": request.representation,
                    "text": text,
                }
            ],
            "provided_time": {
                "precision": "exact",
                "at": request.provided_time.text,
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": _operator(request.local_operator_label),
            "updated_at": timestamp,
            "updated_by": _operator(request.local_operator_label),
        },
    )
    if not isinstance(record, AccountV2):
        raise TypeError("Account authoring produced an unexpected runtime model")
    return record


def prepare_direct_observation(
    request: ObservationAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> ObservationV2:
    """Build one active live-direct Observation without interpretation."""

    _require_event_work(request.work)
    narrative = _normalized_text(request.narrative, "Observation narrative")
    timestamp = clock.now().text
    label = _normalized_text(request.local_operator_label, "local operator display label")
    record = parse_portia_record(
        "observation",
        "2",
        {
            "schema_version": "2",
            "record_type": "observation",
            "module_id": "portia",
            "work_kind": "event",
            "class_id": request.work.class_id,
            "work_id": request.work.work_id,
            "observation_id": ids.new("obs_"),
            "status": "active",
            "target": _event_target(request.target),
            "observer": {
                "kind": "human",
                "human_attribution": {
                    "kind": "local_operator",
                    "display_label": label,
                },
            },
            "method": "live_direct",
            "content": {"narrative": narrative},
            "observation_time": {
                "precision": "exact",
                "at": request.observation_time.text,
            },
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": _operator(label),
            "updated_at": timestamp,
            "updated_by": _operator(label),
        },
    )
    if not isinstance(record, ObservationV2):
        raise TypeError("Observation authoring produced an unexpected runtime model")
    return record


def prepare_review(
    request: ReviewAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> ReviewV1:
    """Build one active open Review without deciding any downstream judgment."""

    _require_event_work(request.work)
    timestamp = clock.now().text
    trigger: dict[str, object] = {"kind": request.trigger_kind}
    if request.trigger_kind == "other":
        if request.trigger_detail is None:
            raise ValueError("other Review trigger requires detail")
        trigger["detail"] = _normalized_text(request.trigger_detail, "Review trigger detail")
    record = parse_portia_record(
        "review",
        "1",
        {
            "schema_version": "1",
            "record_type": "review",
            "module_id": "portia",
            "class_id": request.work.class_id,
            "work_id": request.work.work_id,
            "review_id": ids.new("rvw_"),
            "status": "active",
            "review_state": "open",
            "trigger": trigger,
            "question": {
                "kind": request.question_kind,
                "text": _normalized_text(request.question_text, "Review question"),
            },
            "target": _event_target(request.target),
            "reviewer": {
                "kind": "local_operator",
                "display_label": _normalized_text(
                    request.local_operator_label, "local operator display label"
                ),
            },
            "evidence_considered": [
                _judgment_evidence_ref(request.work, item) for item in request.evidence
            ],
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": _operator(request.local_operator_label),
            "updated_at": timestamp,
            "updated_by": _operator(request.local_operator_label),
        },
    )
    if not isinstance(record, ReviewV1):
        raise TypeError("Review authoring produced an unexpected runtime model")
    return record


def prepare_classification(
    request: ClassificationAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> ClassificationV1:
    """Build one reporter-selected Classification chosen explicitly by the teacher."""

    _require_event_work(request.work)
    timestamp = clock.now().text
    if request.result_kind == "category_selected":
        required = {
            "scheme_id": request.scheme_id,
            "scheme_version": request.scheme_version,
            "category_code": request.category_code,
            "category_label": request.category_label,
            "definition_text": request.definition_text,
        }
        if any(value is None for value in required.values()):
            raise ValueError("selected Classification category requires a complete definition snapshot")
        result: dict[str, object] = {
            "kind": "category_selected",
            "definition": {
                key: _normalized_text(value, key)
                for key, value in required.items()
                if value is not None
            },
        }
    elif request.result_kind == "unable_to_determine":
        result = {"kind": "unable_to_determine"}
        if request.unable_rationale is not None:
            result["rationale"] = _normalized_text(
                request.unable_rationale, "Classification rationale"
            )
    else:
        raise ValueError(f"unsupported Classification result kind: {request.result_kind}")
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "classification",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "classification_id": ids.new("cls_"),
        "status": "active",
        "target": _event_target(request.target),
        "selector": {
            "kind": "local_operator",
            "display_label": _normalized_text(
                request.local_operator_label, "local operator display label"
            ),
        },
        "stage": "reporter_selected",
        "result": result,
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.basis:
        data["basis"] = [
            _judgment_evidence_ref(request.work, item) for item in request.basis
        ]
    record = parse_portia_record("classification", "1", data)
    if not isinstance(record, ClassificationV1):
        raise TypeError("Classification authoring produced an unexpected runtime model")
    return record


def prepare_hypothesis(
    request: HypothesisAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> HypothesisV1:
    """Build one explicit Hypothesis without converting it into a Determination."""

    _require_event_work(request.work)
    timestamp = clock.now().text
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "hypothesis",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "hypothesis_id": ids.new("hyp_"),
        "status": "active",
        "target": _event_target(request.target),
        "author": {
            "kind": "local_operator",
            "display_label": _normalized_text(
                request.local_operator_label, "local operator display label"
            ),
        },
        "proposition": _normalized_text(request.proposition, "Hypothesis proposition"),
        "consideration_state": "under_consideration",
        "evidence": [
            _judgment_relation(request.work, item) for item in request.evidence
        ],
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.rationale is not None:
        data["rationale"] = _normalized_text(request.rationale, "Hypothesis rationale")
    record = parse_portia_record("hypothesis", "1", data)
    if not isinstance(record, HypothesisV1):
        raise TypeError("Hypothesis authoring produced an unexpected runtime model")
    return record


def prepare_determination(
    request: DeterminationAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> DeterminationV1:
    """Build one teacher-local Determination without creating a Response or Outcome."""

    _require_event_work(request.work)
    timestamp = clock.now().text
    if request.outcome_kind == "conclusion":
        if request.conclusion_text is None:
            raise ValueError("conclusion Determination requires bounded conclusion text")
        outcome: dict[str, object] = {
            "kind": "conclusion",
            "text": _normalized_text(request.conclusion_text, "Determination conclusion"),
        }
    elif request.outcome_kind in {
        "insufficient_information",
        "unable_to_determine",
        "not_applicable",
    }:
        outcome = {"kind": request.outcome_kind}
    else:
        raise ValueError(f"unsupported Determination outcome kind: {request.outcome_kind}")
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "determination",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "determination_id": ids.new("det_"),
        "status": "active",
        "target": _event_target(request.target),
        "question": _normalized_text(request.question, "Determination question"),
        "decision_maker": {
            "kind": "local_operator",
            "display_label": _normalized_text(
                request.local_operator_label, "local operator display label"
            ),
        },
        "authority_context": {"kind": "teacher_local", "scope": "teacher_review"},
        "process_basis": {
            "kind": "teacher_local",
            "process_label": "Teacher-local review",
        },
        "outcome": outcome,
        "basis": [_judgment_relation(request.work, item) for item in request.basis],
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.rationale is not None:
        data["rationale"] = _normalized_text(request.rationale, "Determination rationale")
    record = parse_portia_record("determination", "1", data)
    if not isinstance(record, DeterminationV1):
        raise TypeError("Determination authoring produced an unexpected runtime model")
    return record
