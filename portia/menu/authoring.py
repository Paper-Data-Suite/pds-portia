"""Typed candidate authoring for Portia teacher-menu workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from portia.menu.clock import MenuClock
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import (
    AccountV2,
    EventParticipantV3,
    EventV2,
    ObservationV2,
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
        raise ValueError("this teacher-menu evidence path requires an exact event@2 work")


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
