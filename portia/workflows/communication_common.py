"""Application rules shared by work-local ``communication@1`` workflows."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime

from portia.models import CommunicationV1, PortiaRecord
from portia.models.references import (
    ExactActorContactPointRef,
    ExactPortiaWorkRef,
)
from portia.validation import GraphValidationOptions, validate_record_graph
from portia.workflows.action_common import require_action_owner
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)
from portia.workflows.judgment_common import require_represented_human_authority

_COMMUNICATION_WRITE_EVENT_STATUSES = frozenset({"draft", "active", "closed"})
_COMMUNICATION_CURRENT_EVENT_STATUSES = frozenset({"active", "closed"})
_COMMUNICATION_IO_AUTHORITY_FINDINGS = frozenset(
    {
        "PORTIA.GRAPH.COMMUNICATION_ACTOR_UNRESOLVED",
        "PORTIA.GRAPH.COMMUNICATION_ACTOR_NOT_ACTIVE",
        "PORTIA.GRAPH.COMMUNICATION_ENDPOINT_UNRESOLVED",
        "PORTIA.GRAPH.COMMUNICATION_ENDPOINT_NOT_ACTIVE",
    }
)


def require_communication_write_owner(work: ExactPortiaWorkRef) -> None:
    """Require one frozen Communication owner for authoring."""
    require_action_owner(work, contract="communication")


def require_communication_current_owner(work: ExactPortiaWorkRef) -> None:
    """Require one frozen Communication owner for current-use qualification."""
    require_action_owner(work, contract="communication")


def require_event_communication_write_owner(work: ExactPortiaWorkRef) -> None:
    """Retain the Issue #43 Event-only lifecycle/correction boundary."""
    require_communication_write_owner(work)
    if work.work_kind != "event" or work.contract_version != "2":
        raise WorkflowPrerequisiteError(
            "Support Process Communication authoring requires Issue #44 authority"
        )


def require_event_communication_current_owner(work: ExactPortiaWorkRef) -> None:
    """Retain the Issue #43 Event-only helper for callers that require Event scope."""
    require_communication_current_owner(work)
    if work.work_kind != "event" or work.contract_version != "2":
        raise WorkflowPrerequisiteError(
            "Support Process Communication current use requires Issue #44 authority"
        )


def _require_communication_identity(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> CommunicationV1:
    if not isinstance(record, CommunicationV1):
        raise WorkflowOwnershipError(
            "Communication workflows require communication@1 input"
        )
    if (
        record.class_id != work.class_id
        or record.work_id != work.work_id
        or record.work_kind != work.work_kind
    ):
        raise WorkflowOwnershipError(
            "Communication does not belong to the explicitly selected work"
        )
    return record


def require_communication_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> CommunicationV1:
    """Require exact frozen-owner identity for one new ``communication@1`` value."""
    require_communication_write_owner(work)
    if not isinstance(record, CommunicationV1):
        raise WorkflowOwnershipError(
            "new Communication writes require communication@1 input"
        )
    if (
        record.class_id != work.class_id
        or record.work_id != work.work_id
        or record.work_kind != work.work_kind
    ):
        owner_label = "Event" if work.work_kind == "event" else "Support Process"
        raise WorkflowOwnershipError(
            f"Communication does not belong to the explicitly selected {owner_label}"
        )
    return record


def require_current_communication_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> CommunicationV1:
    """Require one exact Communication under its frozen owner union."""
    require_communication_current_owner(work)
    return _require_communication_identity(work, record)


def require_digital_communication_creation(record: PortiaRecord) -> None:
    """Keep Issue #43 authoring digital-entry-first without rewriting history."""
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "v0.2 Communication authoring supports digital_entry only"
        )


def require_communication_current_materialization(record: PortiaRecord) -> None:
    """Fail closed when v0.2 cannot verify reviewed materialization provenance."""
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "current Communication use requires reviewed materialization; "
            "v0.2 supports digital_entry only"
        )


def require_communication_owner_write_eligibility(owner: PortiaRecord) -> None:
    if owner.contract == "event" and owner.contract_version == "2":
        if owner.status not in _COMMUNICATION_WRITE_EVENT_STATUSES:
            expected = ", ".join(sorted(_COMMUNICATION_WRITE_EVENT_STATUSES))
            raise WorkflowPrerequisiteError(
                f"Communication writes require Event status in {{{expected}}}"
            )
        return
    if owner.contract == "support_process" and owner.contract_version == "1":
        if owner.status != "active":
            raise WorkflowPrerequisiteError(
                "Communication writes require active Support Process canonical lifecycle"
            )
        return
    raise WorkflowOwnershipError(
        "Communication owner must resolve to event@2 or support_process@1"
    )


def require_communication_owner_current_eligibility(owner: PortiaRecord) -> None:
    if owner.contract == "event" and owner.contract_version == "2":
        if owner.status not in _COMMUNICATION_CURRENT_EVENT_STATUSES:
            expected = ", ".join(sorted(_COMMUNICATION_CURRENT_EVENT_STATUSES))
            raise WorkflowPrerequisiteError(
                "active Communication creation requires Event status in "
                f"{{{expected}}}"
            )
        return
    if owner.contract == "support_process" and owner.contract_version == "1":
        if owner.status != "active":
            raise WorkflowPrerequisiteError(
                "current Communication use requires active Support Process "
                "canonical lifecycle"
            )
        return
    raise WorkflowOwnershipError(
        "Communication owner must resolve to event@2 or support_process@1"
    )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowOwnershipError(
            f"Communication {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowOwnershipError(
            f"Communication {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowOwnershipError(
            f"Communication {field_name} timestamp lacks an explicit offset"
        )
    return parsed


def _person_identity(person: Mapping[str, object]) -> tuple[object, ...]:
    kind = person.get("kind")
    if kind == "roster_student":
        reference = person.get("roster_student_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Communication recipient is malformed")
        return (
            kind,
            reference.get("class_id"),
            reference.get("student_id"),
        )
    if kind == "actor":
        reference = person.get("actor_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("Communication recipient is malformed")
        return (kind, reference.get("actor_id"))
    if kind == "local_operator":
        return (kind, person.get("display_label"))
    if kind == "descriptive_person":
        return (
            kind,
            person.get("description_type"),
            person.get("display_label"),
        )
    if kind == "unidentified_person":
        return (
            kind,
            person.get("identity_status"),
            person.get("display_label"),
        )
    raise WorkflowOwnershipError(
        f"unsupported Communication recipient attribution kind {kind!r}"
    )


def communication_recipients(record: PortiaRecord) -> tuple[Mapping[str, object], ...]:
    """Return explicit recipient entries while rejecting malformed runtime values."""
    recipients = record.field("recipients")
    if not isinstance(recipients, tuple) or not recipients:
        raise WorkflowOwnershipError("Communication recipients are malformed")
    values: list[Mapping[str, object]] = []
    for item in recipients:
        if not isinstance(item, Mapping):
            raise WorkflowOwnershipError("Communication recipient entry is malformed")
        person = item.get("person")
        if not isinstance(person, Mapping):
            raise WorkflowOwnershipError("Communication recipient person is malformed")
        values.append(item)
    return tuple(values)


def require_communication_creation_semantics(record: PortiaRecord) -> None:
    """Enforce the Issue #17 rules owned by initial digital Communication writes."""
    created_at = _parse_timestamp(
        record.field("created_at"),
        field_name="created_at",
    )
    updated_at = _parse_timestamp(
        record.field("updated_at"),
        field_name="updated_at",
    )
    started_at = _parse_timestamp(
        record.field("started_at"),
        field_name="started_at",
    )
    ended_value = record.field("ended_at")
    ended_at = (
        _parse_timestamp(ended_value, field_name="ended_at")
        if ended_value is not None
        else None
    )

    if updated_at < created_at:
        raise WorkflowPrerequisiteError(
            "Communication updated_at cannot precede created_at"
        )
    if started_at > updated_at:
        raise WorkflowPrerequisiteError(
            "Communication started_at cannot follow updated_at"
        )
    if ended_at is not None and ended_at < started_at:
        raise WorkflowPrerequisiteError(
            "Communication ended_at cannot precede started_at"
        )
    if ended_at is not None and ended_at > updated_at:
        raise WorkflowPrerequisiteError(
            "Communication ended_at cannot follow updated_at"
        )

    method = record.field("method")
    purpose = record.field("purpose")
    if not isinstance(method, Mapping) or not isinstance(purpose, Mapping):
        raise WorkflowOwnershipError("Communication method or purpose is malformed")
    if method.get("kind") == "unknown":
        raise WorkflowPrerequisiteError(
            "digital-entry Communication cannot use historical unknown method"
        )
    if purpose.get("kind") == "unknown":
        raise WorkflowPrerequisiteError(
            "digital-entry Communication cannot use historical unknown purpose"
        )
    if record.field("act_state") == "unknown":
        raise WorkflowPrerequisiteError(
            "digital-entry Communication cannot use historical unknown act state"
        )
    if record.field("privacy_scope") == "unknown":
        raise WorkflowPrerequisiteError(
            "digital-entry Communication cannot use historical unknown privacy scope"
        )

    recipients = communication_recipients(record)
    identities: list[tuple[object, ...]] = []
    for item in recipients:
        person = item["person"]
        assert isinstance(person, Mapping)
        identities.append(_person_identity(person))
        if item.get("participation") == "unknown":
            raise WorkflowPrerequisiteError(
                "digital-entry Communication cannot use historical unknown "
                "recipient participation"
            )

    if len(identities) != len(set(identities)):
        raise WorkflowPrerequisiteError(
            "Communication repeats the same logical recipient identity"
        )

    if record.field("act_state") == "recipient_unavailable" and any(
        item.get("participation") == "participated" for item in recipients
    ):
        raise WorkflowPrerequisiteError(
            "recipient-unavailable Communication cannot establish participation"
        )


def require_communication_people_authority(
    contexts: WorkflowContextAssembler,
    record: PortiaRecord,
    *,
    require_current_use: bool,
) -> None:
    """Resolve sender/recipients without treating recipients as Participants."""
    require_represented_human_authority(
        contexts,
        record.field("sender"),
        field_name="Communication sender",
        require_current_use=require_current_use,
    )
    for item in communication_recipients(record):
        require_represented_human_authority(
            contexts,
            item["person"],
            field_name="Communication recipient",
            require_current_use=require_current_use,
        )


def require_communication_contact_point_authority(
    contexts: WorkflowContextAssembler,
    record: PortiaRecord,
    *,
    require_current_use: bool,
) -> None:
    """Resolve exact recipient endpoints without inferring consent or delivery."""
    for item in communication_recipients(record):
        endpoint = item.get("endpoint_ref")
        if endpoint is None:
            continue
        person = item["person"]
        assert isinstance(person, Mapping)
        actor_ref = person.get("actor_ref")
        actor_id = (
            actor_ref.get("actor_id")
            if isinstance(actor_ref, Mapping)
            else None
        )
        if person.get("kind") != "actor" or not isinstance(actor_id, str):
            raise WorkflowOwnershipError(
                "Communication Contact Point requires an Actor recipient"
            )
        if not isinstance(endpoint, Mapping):
            raise WorkflowOwnershipError(
                "Communication recipient Contact Point reference is malformed"
            )
        endpoint_actor = endpoint.get("actor_id")
        contact_point_id = endpoint.get("contact_point_id")
        contract_version = endpoint.get("contract_version")
        if (
            not isinstance(endpoint_actor, str)
            or not isinstance(contact_point_id, str)
            or not isinstance(contract_version, str)
        ):
            raise WorkflowOwnershipError(
                "Communication recipient Contact Point reference is malformed"
            )
        if endpoint_actor != actor_id:
            raise WorkflowPrerequisiteError(
                "Communication Contact Point Actor does not match recipient Actor"
            )
        contexts.actors.load_contact_point(
            ExactActorContactPointRef(
                actor_id=endpoint_actor,
                contact_point_id=contact_point_id,
                contract_version=contract_version,
            ),
            require_current_use=require_current_use,
        )


def require_initial_communication_no_supersession(record: PortiaRecord) -> None:
    """Keep new attempts separate from the coordinated correction path."""
    if record.field("supersedes") is not None:
        raise WorkflowPrerequisiteError(
            "Communication supersession requires the coordinated correct() path"
        )


def validate_partial_communication_graph(record: PortiaRecord) -> None:
    """Run pure validation after this slice's I/O-backed authorities resolve."""
    findings = tuple(
        finding
        for finding in validate_record_graph(
            (record,),
            options=GraphValidationOptions(require_internal_resolution=False),
        )
        if finding.code not in _COMMUNICATION_IO_AUTHORITY_FINDINGS
    )
    if findings:
        raise WorkflowValidationError(findings)
