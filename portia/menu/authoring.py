"""Typed candidate authoring for Portia teacher-menu workflows."""

from __future__ import annotations

from dataclasses import dataclass

from portia.menu.clock import MenuClock
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import EventParticipantV3, EventV2, parse_portia_record
from portia.models.common import ExplicitOffsetTimestamp
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


def _operator(display_label: str) -> dict[str, object]:
    normalized = " ".join(display_label.split())
    if not normalized:
        raise ValueError("local operator display label must not be blank")
    return {"type": "local_operator", "display_label": normalized}


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
    summary = " ".join(request.summary.split())
    if not summary:
        raise ValueError("Event summary must not be blank")

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
