"""Typed candidate authoring for Portia teacher-menu workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from portia.menu.clock import MenuClock
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import (
    AccountV2,
    ClassificationV1,
    CommunicationV1,
    DeterminationV1,
    EventParticipantV3,
    EventV2,
    HypothesisV1,
    ObservationV2,
    ResponseV1,
    ReviewV1,
    SupportGoalV1,
    SupportNeedV1,
    SupportProcessParticipantV1,
    SupportProcessV1,
    SupportV1,
    parse_portia_record,
)
from portia.models.common import ExplicitOffsetTimestamp
from portia.models.json_values import JsonValue
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




@dataclass(frozen=True, slots=True)
class SupportProcessAuthoringInput:
    """Teacher-entered facts for one proposed teacher-local Support Process."""

    owner_class_id: str
    school_year: str
    summary: str
    initiation_detail: str
    local_operator_label: str
    planned_start_date: str | None = None
    planned_end_date: str | None = None
    review_on: str | None = None


@dataclass(frozen=True, slots=True)
class SupportParticipantContextInput:
    """One explicit participation context within a Support Process."""

    kind: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class SupportParticipantAuthoringInput:
    """Teacher-entered facts for one proposed Support Process Participant."""

    work: ExactPortiaWorkRef
    person: HumanAttributionInput
    contexts: tuple[SupportParticipantContextInput, ...]
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class PreparedSupportProcessActivation:
    """One in-memory proposed->active Support Process lifecycle request."""

    candidate: SupportProcessV1
    transition_id: str
    operation_id: str


@dataclass(frozen=True, slots=True)
class PreparedSupportParticipantActivation:
    """One in-memory proposed->active Support Participant lifecycle request."""

    candidate: SupportProcessParticipantV1
    transition_id: str
    operation_id: str


@dataclass(frozen=True, slots=True)
class SupportPlanTargetInput:
    """One exact Support Process-local planning target."""

    kind: Literal["support_process", "support_process_participant"]
    participant_id: str | None = None


@dataclass(frozen=True, slots=True)
class SupportNeedAuthoringInput:
    """Teacher-entered facts for one bounded Support Need."""

    work: ExactPortiaWorkRef
    status: Literal["proposed", "active"]
    target: SupportPlanTargetInput
    need_kind: str
    description: str
    kind_detail: str | None
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class SupportGoalAuthoringInput:
    """Teacher-entered facts for one bounded future Support Goal."""

    work: ExactPortiaWorkRef
    status: Literal["proposed", "active"]
    target: SupportPlanTargetInput
    description: str
    planned_criteria: str | None
    measurement_approach: str | None
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class SupportScheduleInput:
    """Planning-only schedule facts; no implementation semantics."""

    kind: Literal["as_needed", "recurring", "condition_triggered", "custom"]
    planned_minutes: int | None = None
    occurrences: int | None = None
    interval_count: int | None = None
    interval_unit: str | None = None
    trigger: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class SupportAuthoringInput:
    """Teacher-entered facts for one Support planning record."""

    work: ExactPortiaWorkRef
    status: Literal["proposed", "active"]
    target: SupportPlanTargetInput
    need_ids: tuple[str, ...]
    goal_ids: tuple[str, ...]
    strategy_kind: str
    procedure: str
    strategy_detail: str | None
    provider_participant_ids: tuple[str, ...]
    no_provider_reason: str | None
    no_provider_detail: str | None
    schedule: SupportScheduleInput
    local_operator_label: str


@dataclass(frozen=True, slots=True)
class ResponseAuthoringInput:
    """Teacher-entered facts for one bounded Event-local Response."""

    work: ExactPortiaWorkRef
    target: EventEvidenceTargetInput
    action_family: str
    description: str
    execution_state: str
    started_at: ExplicitOffsetTimestamp
    local_operator_label: str
    consequence_context: str | None = None


@dataclass(frozen=True, slots=True)
class CommunicationRecipientInput:
    """One represented recipient and explicitly recorded participation state."""

    person: HumanAttributionInput
    participation: str


@dataclass(frozen=True, slots=True)
class CommunicationAuthoringInput:
    """Teacher-entered facts for one Event-owned Communication act."""

    work: ExactPortiaWorkRef
    recipients: tuple[CommunicationRecipientInput, ...]
    method_kind: str
    method_detail: str | None
    purpose_kind: str
    purpose_detail: str | None
    act_state: str
    privacy_scope: str
    started_at: ExplicitOffsetTimestamp
    summary: str | None
    local_operator_label: str


def _normalized_text(value: str, field_name: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _operator(display_label: str) -> dict[str, JsonValue]:
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


def prepare_response(
    request: ResponseAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> ResponseV1:
    """Build one bounded active Response without inferring effectiveness or outcome."""

    _require_event_work(request.work)
    timestamp = clock.now().text
    action: dict[str, object] = {
        "family": request.action_family,
        "description": _normalized_text(request.description, "Response description"),
    }
    if request.action_family == "consequence":
        if request.consequence_context != "teacher_local":
            raise ValueError(
                "routine teacher Response consequence requires teacher_local context"
            )
        action["consequence_context"] = "teacher_local"
    elif request.consequence_context is not None:
        raise ValueError(
            "Response consequence_context is only valid for consequence actions"
        )

    record = parse_portia_record(
        "response",
        "1",
        {
            "schema_version": "1",
            "record_type": "response",
            "module_id": "portia",
            "class_id": request.work.class_id,
            "work_id": request.work.work_id,
            "response_id": ids.new("rsp_"),
            "status": "active",
            "target": _event_target(request.target),
            "provider": {
                "kind": "local_operator",
                "display_label": _normalized_text(
                    request.local_operator_label, "local operator display label"
                ),
            },
            "action": action,
            "execution_state": request.execution_state,
            "started_at": request.started_at.text,
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": _operator(request.local_operator_label),
            "updated_at": timestamp,
            "updated_by": _operator(request.local_operator_label),
        },
    )
    if not isinstance(record, ResponseV1):
        raise TypeError("Response authoring produced an unexpected runtime model")
    return record


def prepare_communication(
    request: CommunicationAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> CommunicationV1:
    """Build one Event-owned Communication without inferring delivery or agreement."""

    _require_event_work(request.work)
    if not request.recipients:
        raise ValueError("Communication requires at least one explicit recipient")
    timestamp = clock.now().text

    method: dict[str, object] = {"kind": request.method_kind}
    if request.method_kind == "other":
        if request.method_detail is None:
            raise ValueError("other Communication method requires detail")
        method["detail"] = _normalized_text(
            request.method_detail, "Communication method detail"
        )
    elif request.method_detail is not None:
        raise ValueError("Communication method detail is only valid for other")

    purpose: dict[str, object] = {"kind": request.purpose_kind}
    if request.purpose_kind == "other":
        if request.purpose_detail is None:
            raise ValueError("other Communication purpose requires detail")
        purpose["detail"] = _normalized_text(
            request.purpose_detail, "Communication purpose detail"
        )
    elif request.purpose_detail is not None:
        raise ValueError("Communication purpose detail is only valid for other")

    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "communication",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_kind": "event",
        "work_id": request.work.work_id,
        "communication_id": ids.new("comm_"),
        "status": "active",
        "sender": {
            "kind": "local_operator",
            "display_label": _normalized_text(
                request.local_operator_label, "local operator display label"
            ),
        },
        "recipients": [
            {
                "person": _represented_human(item.person),
                "participation": item.participation,
            }
            for item in request.recipients
        ],
        "method": method,
        "purpose": purpose,
        "act_state": request.act_state,
        "privacy_scope": request.privacy_scope,
        "started_at": request.started_at.text,
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.summary is not None:
        normalized_summary = " ".join(request.summary.split())
        if normalized_summary:
            data["summary"] = normalized_summary

    record = parse_portia_record("communication", "1", data)
    if not isinstance(record, CommunicationV1):
        raise TypeError("Communication authoring produced an unexpected runtime model")
    return record


def _require_support_work(work: ExactPortiaWorkRef) -> None:
    if work.work_kind != "support_process" or work.contract_version != "1":
        raise ValueError(
            "this teacher-menu path requires an exact support_process@1 work"
        )


def _optional_iso_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD") from exc
    return normalized


def prepare_support_process(
    request: SupportProcessAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> SupportProcessV1:
    """Build one proposed Support Process without inventing downstream planning state."""

    timestamp = clock.now().text
    actor = _operator(request.local_operator_label)
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "portia_work",
        "work_kind": "support_process",
        "module_id": "portia",
        "class_id": request.owner_class_id,
        "work_id": ids.new("sup_"),
        "school_year": request.school_year,
        "status": "proposed",
        "workflow_state": "planning",
        "summary": _normalized_text(request.summary, "Support Process summary"),
        "initiation": {
            "kind": "teacher_identified_need",
            "detail": _normalized_text(
                request.initiation_detail,
                "Support Process initiation detail",
            ),
        },
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": actor,
        "updated_at": timestamp,
        "updated_by": actor,
    }
    dates = {
        "planned_start_date": _optional_iso_date(
            request.planned_start_date, "planned_start_date"
        ),
        "planned_end_date": _optional_iso_date(
            request.planned_end_date, "planned_end_date"
        ),
        "review_on": _optional_iso_date(request.review_on, "review_on"),
    }
    for key, value in dates.items():
        if value is not None:
            data[key] = value
    record = parse_portia_record("support_process", "1", data)
    if not isinstance(record, SupportProcessV1):
        raise TypeError("Support Process authoring produced an unexpected runtime model")
    return record


def prepare_support_participant(
    request: SupportParticipantAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> SupportProcessParticipantV1:
    """Build one proposed Participant without inferring role, need, goal, or support."""

    _require_support_work(request.work)
    if not request.contexts:
        raise ValueError("Support Process Participant requires at least one context")
    contexts: list[dict[str, object]] = []
    seen: set[tuple[str, str | None]] = set()
    for item in request.contexts:
        detail: str | None = None
        if item.kind == "other":
            if item.detail is None:
                raise ValueError("other Support Participant context requires detail")
            detail = _normalized_text(item.detail, "Support Participant context detail")
        elif item.detail is not None:
            raise ValueError("Support Participant context detail is only valid for other")
        identity = (item.kind, detail)
        if identity in seen:
            raise ValueError("Support Participant context is duplicated")
        seen.add(identity)
        value: dict[str, object] = {"kind": item.kind}
        if detail is not None:
            value["detail"] = detail
        contexts.append(value)

    timestamp = clock.now().text
    record = parse_portia_record(
        "support_process_participant",
        "1",
        {
            "schema_version": "1",
            "record_type": "support_process_participant",
            "module_id": "portia",
            "class_id": request.work.class_id,
            "work_id": request.work.work_id,
            "participant_id": ids.new("spp_"),
            "status": "proposed",
            "person": _represented_human(request.person),
            "contexts": contexts,
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": _operator(request.local_operator_label),
            "updated_at": timestamp,
            "updated_by": _operator(request.local_operator_label),
        },
    )
    if not isinstance(record, SupportProcessParticipantV1):
        raise TypeError(
            "Support Process Participant authoring produced an unexpected runtime model"
        )
    return record


def prepare_support_participant_activation(
    prior: SupportProcessParticipantV1,
    *,
    local_operator_label: str,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> PreparedSupportParticipantActivation:
    """Prepare one explicit Participant activation without writing canonical state."""

    if prior.status != "proposed":
        raise ValueError("only a proposed Support Process Participant can be activated")
    data = prior.to_dict()
    data["status"] = "active"
    data["updated_at"] = clock.now().text
    data["updated_by"] = _operator(local_operator_label)
    candidate = parse_portia_record("support_process_participant", "1", data)
    if not isinstance(candidate, SupportProcessParticipantV1):
        raise TypeError("Support Participant activation produced an unexpected runtime model")
    return PreparedSupportParticipantActivation(
        candidate=candidate,
        transition_id=ids.new("lct_"),
        operation_id=ids.new("op_"),
    )


def prepare_support_process_activation(
    prior: SupportProcessV1,
    *,
    local_operator_label: str,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> PreparedSupportProcessActivation:
    """Prepare one explicit root activation without changing workflow_state."""

    if prior.status != "proposed":
        raise ValueError("only a proposed Support Process can be activated")
    if prior.field("workflow_state") != "planning":
        raise ValueError("Support Process activation requires planning workflow state")
    data = prior.to_dict()
    data["status"] = "active"
    data["updated_at"] = clock.now().text
    data["updated_by"] = _operator(local_operator_label)
    candidate = parse_portia_record("support_process", "1", data)
    if not isinstance(candidate, SupportProcessV1):
        raise TypeError("Support Process activation produced an unexpected runtime model")
    return PreparedSupportProcessActivation(
        candidate=candidate,
        transition_id=ids.new("lct_"),
        operation_id=ids.new("op_"),
    )

def _support_plan_target(value: SupportPlanTargetInput) -> dict[str, object]:
    if value.kind == "support_process":
        if value.participant_id is not None:
            raise ValueError("whole-process target cannot include a participant ID")
        return {"kind": "support_process"}
    if value.kind != "support_process_participant" or value.participant_id is None:
        raise ValueError("participant target requires one exact participant ID")
    return {
        "kind": "support_process_participant",
        "record_ref": {
            "record_kind": "support_process_participant",
            "record_id": value.participant_id,
            "contract_version": "1",
        },
    }


def prepare_support_need(
    request: SupportNeedAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> SupportNeedV1:
    """Build one explicit Need without diagnosis, eligibility, or outcome inference."""

    _require_support_work(request.work)
    if request.status not in {"proposed", "active"}:
        raise ValueError("Support Need status must be proposed or active")
    if request.need_kind == "other":
        if request.kind_detail is None:
            raise ValueError("other Support Need kind requires detail")
        kind_detail = _normalized_text(request.kind_detail, "Support Need kind detail")
    else:
        if request.kind_detail is not None and request.kind_detail.strip():
            raise ValueError("Support Need kind detail is only valid for other")
        kind_detail = None
    timestamp = clock.now().text
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support_need",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "need_id": ids.new("spn_"),
        "status": request.status,
        "target": _support_plan_target(request.target),
        "need_kind": request.need_kind,
        "description": _normalized_text(request.description, "Support Need description"),
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if kind_detail is not None:
        data["kind_detail"] = kind_detail
    record = parse_portia_record("support_need", "1", data)
    if not isinstance(record, SupportNeedV1):
        raise TypeError("Support Need authoring produced an unexpected runtime model")
    return record


def prepare_support_goal(
    request: SupportGoalAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> SupportGoalV1:
    """Build one future-facing Goal without recording progress or attainment."""

    _require_support_work(request.work)
    if request.status not in {"proposed", "active"}:
        raise ValueError("Support Goal status must be proposed or active")
    timestamp = clock.now().text
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support_goal",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "goal_id": ids.new("spg_"),
        "status": request.status,
        "target": _support_plan_target(request.target),
        "description": _normalized_text(request.description, "Support Goal description"),
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.planned_criteria is not None and request.planned_criteria.strip():
        data["planned_criteria"] = _normalized_text(
            request.planned_criteria, "Support Goal planned criteria"
        )
    if request.measurement_approach is not None and request.measurement_approach.strip():
        data["measurement_approach"] = _normalized_text(
            request.measurement_approach, "Support Goal measurement approach"
        )
    record = parse_portia_record("support_goal", "1", data)
    if not isinstance(record, SupportGoalV1):
        raise TypeError("Support Goal authoring produced an unexpected runtime model")
    return record


def _support_schedule(value: SupportScheduleInput) -> dict[str, object]:
    schedule: dict[str, object] = {"kind": value.kind}
    if value.planned_minutes is not None:
        if value.planned_minutes < 1:
            raise ValueError("planned support duration must be at least one minute")
        schedule["planned_duration"] = {
            "kind": "minutes",
            "minutes": value.planned_minutes,
        }
    if value.kind == "as_needed":
        return schedule
    if value.kind == "recurring":
        if value.occurrences is None or value.interval_count is None or value.interval_unit is None:
            raise ValueError("recurring support schedule requires frequency")
        schedule["frequency"] = {
            "occurrences": value.occurrences,
            "interval_count": value.interval_count,
            "interval_unit": value.interval_unit,
        }
        return schedule
    if value.kind == "condition_triggered":
        if value.trigger is None:
            raise ValueError("condition-triggered support schedule requires a trigger")
        schedule["trigger"] = _normalized_text(value.trigger, "Support schedule trigger")
        return schedule
    if value.kind == "custom":
        if value.description is None:
            raise ValueError("custom support schedule requires a description")
        schedule["description"] = _normalized_text(
            value.description, "Support schedule description"
        )
        return schedule
    raise ValueError(f"unsupported Support schedule kind {value.kind!r}")


def prepare_support(
    request: SupportAuthoringInput,
    *,
    clock: MenuClock,
    ids: PortiaIdGenerator,
) -> SupportV1:
    """Build one planning Support without claiming delivery or effectiveness."""

    _require_support_work(request.work)
    if request.status not in {"proposed", "active"}:
        raise ValueError("Support status must be proposed or active")
    if not request.need_ids:
        raise ValueError("Support requires at least one exact Need")
    if len(set(request.need_ids)) != len(request.need_ids):
        raise ValueError("Support Need selection repeats an exact Need")
    if len(set(request.goal_ids)) != len(request.goal_ids):
        raise ValueError("Support Goal selection repeats an exact Goal")
    if len(set(request.provider_participant_ids)) != len(request.provider_participant_ids):
        raise ValueError("Support provider selection repeats an exact Participant")

    strategy: dict[str, object] = {
        "kind": request.strategy_kind,
        "procedure": _normalized_text(request.procedure, "Support procedure"),
    }
    if request.strategy_kind == "other":
        if request.strategy_detail is None:
            raise ValueError("other Support strategy requires detail")
        strategy["kind_detail"] = _normalized_text(
            request.strategy_detail, "Support strategy detail"
        )
    elif request.strategy_detail is not None and request.strategy_detail.strip():
        raise ValueError("Support strategy detail is only valid for other")

    if request.provider_participant_ids:
        if request.no_provider_reason is not None:
            raise ValueError("assigned Support providers cannot also use no-provider reason")
        provider_plan: dict[str, object] = {
            "kind": "assigned",
            "participant_refs": [
                {
                    "record_kind": "support_process_participant",
                    "record_id": participant_id,
                    "contract_version": "1",
                }
                for participant_id in request.provider_participant_ids
            ],
        }
    else:
        if request.no_provider_reason is None:
            raise ValueError("Support without assigned providers requires an explicit reason")
        provider_plan = {
            "kind": "no_assigned_provider",
            "reason": request.no_provider_reason,
        }
        if request.no_provider_reason == "other":
            if request.no_provider_detail is None:
                raise ValueError("other no-provider reason requires detail")
            provider_plan["detail"] = _normalized_text(
                request.no_provider_detail, "Support no-provider detail"
            )
        elif request.no_provider_detail is not None and request.no_provider_detail.strip():
            raise ValueError("no-provider detail is only valid for other")

    timestamp = clock.now().text
    data: dict[str, object] = {
        "schema_version": "1",
        "record_type": "support",
        "module_id": "portia",
        "class_id": request.work.class_id,
        "work_id": request.work.work_id,
        "support_id": ids.new("spt_"),
        "status": request.status,
        "target": _support_plan_target(request.target),
        "need_refs": [
            {
                "record_kind": "support_need",
                "record_id": need_id,
                "contract_version": "1",
            }
            for need_id in request.need_ids
        ],
        "strategy": strategy,
        "provider_plan": provider_plan,
        "schedule": _support_schedule(request.schedule),
        "plan_state": "active" if request.status == "active" else "planned",
        "creation_source": {"type": "digital_entry"},
        "created_at": timestamp,
        "created_by": _operator(request.local_operator_label),
        "updated_at": timestamp,
        "updated_by": _operator(request.local_operator_label),
    }
    if request.goal_ids:
        data["goal_refs"] = [
            {
                "record_kind": "support_goal",
                "record_id": goal_id,
                "contract_version": "1",
            }
            for goal_id in request.goal_ids
        ]
    record = parse_portia_record("support", "1", data)
    if not isinstance(record, SupportV1):
        raise TypeError("Support authoring produced an unexpected runtime model")
    return record
