from __future__ import annotations

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef

TIMESTAMP = "2026-08-26T12:00:00-04:00"
AGENT = {"type": "system_process", "process_id": "workflow_test"}


def event_wire(
    *,
    class_id: str = "class_a",
    event_id: str = "evt_alpha",
    status: str = "active",
    updated_at: str = TIMESTAMP,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    created_by: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "2",
        "record_type": "portia_work",
        "work_kind": "event",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": event_id,
        "school_year": "2026-2027",
        "status": status,
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": created_by or AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
        "occurrence": {"precision": "exact", "started_at": TIMESTAMP},
        "summary": "Synthetic neutral classroom context.",
    }


def event_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("event", "2", event_wire(**kwargs))


def event_ref(
    *, class_id: str = "class_a", event_id: str = "evt_alpha", version: str = "2"
) -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id=class_id,
        work_id=event_id,
        work_kind="event",
        contract_version=version,
    )


def participant_wire(
    *,
    participant_id: str = "ep_alpha",
    class_id: str = "class_a",
    event_id: str = "evt_alpha",
    subject: dict[str, object] | None = None,
    status: str = "active",
    updated_at: str = TIMESTAMP,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    created_by: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "3",
        "record_type": "event_participant",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": event_id,
        "participant_id": participant_id,
        "status": status,
        "subject": subject
        or {
            "kind": "roster_student",
            "roster_student_ref": {
                "class_id": class_id,
                "student_id": "student_1",
            },
            "display_snapshot": {"display_name": "Same Display"},
        },
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": created_by or AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }


def participant_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record(
        "event_participant", "3", participant_wire(**kwargs)
    )


def role_wire(
    *,
    role_id: str = "epr_alpha",
    participant_id: str = "ep_alpha",
    class_id: str = "class_a",
    event_id: str = "evt_alpha",
    role_type: str = "present",
    status: str = "active",
    basis: list[dict[str, object]] | None = None,
    updated_at: str = TIMESTAMP,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    created_by: dict[str, object] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "3",
        "record_type": "event_participant_role",
        "module_id": "portia",
        "class_id": class_id,
        "work_id": event_id,
        "role_id": role_id,
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": participant_id,
                "contract_version": "3",
            },
        },
        "status": status,
        "role_type": role_type,
        "creation_source": creation_source or {"type": "digital_entry"},
        "created_at": created_at,
        "created_by": created_by or AGENT,
        "updated_at": updated_at,
        "updated_by": AGENT,
    }
    if basis is not None:
        value["basis"] = basis
    return value


def role_record(**kwargs: object) -> PortiaRecord:
    return parse_portia_record("event_participant_role", "3", role_wire(**kwargs))


def account_wire(
    *,
    account_id: str = "acct_alpha",
    participant_id: str = "ep_alpha",
    status: str = "active",
    source_kind: str = "local_operator",
) -> dict[str, object]:
    source: dict[str, object]
    if source_kind == "local_operator":
        source = {"kind": "local_operator", "display_label": "Synthetic Teacher"}
    elif source_kind == "unidentified_person":
        source = {
            "kind": "unidentified_person",
            "identity_status": "not_recorded",
            "detail": "Unknown source",
        }
    else:
        raise ValueError(source_kind)
    return {
        "schema_version": "1",
        "record_type": "account",
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_alpha",
        "account_id": account_id,
        "status": status,
        "target": {
            "kind": "event_participant",
            "record_ref": {
                "record_kind": "event_participant",
                "record_id": participant_id,
                "contract_version": "3",
            },
        },
        "source": source,
        "information_origin": "firsthand",
        "source_certainty": "stated_certain",
        "content": [
            {"representation": "recorded_summary", "text": "Synthetic report."}
        ],
        "provided_time": {"precision": "exact", "at": TIMESTAMP},
        "creation_source": {"type": "digital_entry"},
        "created_at": TIMESTAMP,
        "created_by": AGENT,
        "updated_at": TIMESTAMP,
        "updated_by": AGENT,
    }


def relationship_record(
    *,
    source_event: str = "evt_alpha",
    target_event: str = "evt_beta",
    relationship_id: str = "rel_alpha",
    status: str = "active",
    updated_at: str = TIMESTAMP,
    creation_source: dict[str, object] | None = None,
    created_at: str = TIMESTAMP,
    created_by: dict[str, object] | None = None,
) -> PortiaRecord:
    return parse_portia_record(
        "work_relationship",
        "2",
        {
            "schema_version": "2",
            "record_type": "work_relationship",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": source_event,
            "relationship_id": relationship_id,
            "status": status,
            "relationship_type": "draws_context_from",
            "source": event_ref(event_id=source_event).to_dict(),
            "target": event_ref(event_id=target_event).to_dict(),
            "creation_source": creation_source or {"type": "digital_entry"},
            "created_at": created_at,
            "created_by": created_by or AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )
