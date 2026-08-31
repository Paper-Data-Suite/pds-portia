"""Application rules shared by Event-local ``response@1`` workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from portia.models import PortiaRecord, ResponseV1
from portia.models.references import (
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.validation import GraphValidationOptions, validate_record_graph
from portia.workflows.action_common import require_action_owner
from portia.workflows.common import record_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)
from portia.workflows.judgment_common import require_represented_human_authority

_RESPONSE_PARTICIPANT_VERSION = "3"
_RESPONSE_WRITE_EVENT_STATUSES = frozenset({"draft", "active", "closed"})
_RESPONSE_CURRENT_EVENT_STATUSES = frozenset({"active", "closed"})


def require_response_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> ResponseV1:
    """Require exact Event ownership for a new ``response@1`` representation."""
    require_action_owner(work, contract="response")
    if not isinstance(record, ResponseV1):
        raise WorkflowOwnershipError("new Response writes require response@1 input")
    if record.class_id != work.class_id or record.work_id != work.work_id:
        raise WorkflowOwnershipError(
            "Response does not belong to the explicitly selected Event"
        )
    return record


def require_digital_response_creation(record: PortiaRecord) -> None:
    """Keep v0.2 authoring digital-entry-first without rewriting historical data."""
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "v0.2 Response authoring supports digital_entry only"
        )


def require_response_current_materialization(record: PortiaRecord) -> None:
    """Fail closed when v0.2 cannot verify reviewed materialization provenance."""
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type")
        if isinstance(creation_source, Mapping)
        else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "current Response use requires reviewed materialization; "
            "v0.2 supports digital_entry only"
        )


def require_response_owner_write_eligibility(owner: PortiaRecord) -> None:
    if owner.contract != "event" or owner.contract_version != "2":
        raise WorkflowOwnershipError("Response owner must resolve to event@2")
    if owner.status not in _RESPONSE_WRITE_EVENT_STATUSES:
        expected = ", ".join(sorted(_RESPONSE_WRITE_EVENT_STATUSES))
        raise WorkflowPrerequisiteError(
            f"Response writes require Event status in {{{expected}}}"
        )


def require_response_owner_current_eligibility(owner: PortiaRecord) -> None:
    if owner.contract != "event" or owner.contract_version != "2":
        raise WorkflowOwnershipError("Response owner must resolve to event@2")
    if owner.status not in _RESPONSE_CURRENT_EVENT_STATUSES:
        expected = ", ".join(sorted(_RESPONSE_CURRENT_EVENT_STATUSES))
        raise WorkflowPrerequisiteError(
            f"active Response creation requires Event status in {{{expected}}}"
        )


def response_target_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Resolve exact Event-local Participant targets without loose matching."""
    require_action_owner(work, contract="response")
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("Response target is malformed")

    kind = target.get("kind")
    if kind == "event":
        return ()
    if kind == "event_participant":
        entries: Sequence[object] = (target,)
    elif kind == "event_participants":
        raw_targets = target.get("targets")
        if not isinstance(raw_targets, tuple):
            raise WorkflowOwnershipError("plural Response target is malformed")
        entries = raw_targets
    else:
        raise WorkflowOwnershipError("Response target is not Event-local")

    loaded: list[StoredRecord] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowOwnershipError("Response target entry is malformed")
        reference = entry.get("record_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError(
                "Response target record reference is malformed"
            )
        record_kind = reference.get("record_kind")
        record_id = reference.get("record_id")
        version = reference.get("contract_version")
        if record_kind != "event_participant" or not isinstance(record_id, str):
            raise WorkflowOwnershipError(
                "Response target names the wrong record family"
            )
        if version != _RESPONSE_PARTICIPANT_VERSION:
            raise WorkflowPrerequisiteError(
                "new Response targeting requires event_participant@3"
            )
        if record_id in seen:
            raise WorkflowOwnershipError(
                "Response target repeats the same logical Participant identity"
            )
        seen.add(record_id)
        loaded.append(
            repository.load_work_record(
                work,
                "event_participant",
                _RESPONSE_PARTICIPANT_VERSION,
                record_id,
            )
        )
    return tuple(loaded)


def require_response_targets_current_use(
    work: ExactPortiaWorkRef,
    targets: Sequence[StoredRecord],
    *,
    quarantine: QuarantineGuard,
) -> None:
    """Require active exact Participant targets for an active new Response."""
    for target in targets:
        if target.record.status != "active":
            raise WorkflowPrerequisiteError(
                "active Response target Participant must be active"
            )
        quarantine.require_allowed(
            record_target(work, target.record),
            "block_current_use",
        )


def response_context_reference(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    field_name: str,
    record_kind: str,
) -> ExactPortiaWorkRecordRef | None:
    """Parse one exact same-Event historical context link without substitution."""
    value = record.field(field_name)
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"Response {field_name} is malformed")
    reference = ExactPortiaWorkRecordRef.from_dict(value)
    if reference.work_ref != work:
        raise WorkflowOwnershipError(
            f"Response {field_name} must belong to the same Event"
        )
    if (
        reference.record_ref.record_kind != record_kind
        or reference.record_ref.contract_version != "1"
    ):
        raise WorkflowOwnershipError(
            f"Response {field_name} must name exact {record_kind}@1"
        )
    return reference


def response_is_recorded_institutional(record: PortiaRecord) -> bool:
    action = record.field("action")
    return bool(
        isinstance(action, Mapping)
        and action.get("family") == "consequence"
        and action.get("consequence_context") == "recorded_institutional"
    )


def _parse_timestamp(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowOwnershipError(
            f"Response {field_name} timestamp is malformed"
        )
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowOwnershipError(
            f"Response {field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowOwnershipError(
            f"Response {field_name} timestamp lacks an explicit offset"
        )
    return parsed


def require_response_creation_semantics(record: PortiaRecord) -> None:
    """Enforce frozen Issue #17 application rules for a new digital Response."""
    created_at = _parse_timestamp(record.field("created_at"), field_name="created_at")
    updated_at = _parse_timestamp(record.field("updated_at"), field_name="updated_at")
    started_at = _parse_timestamp(record.field("started_at"), field_name="started_at")
    ended_value = record.field("ended_at")
    ended_at = (
        _parse_timestamp(ended_value, field_name="ended_at")
        if ended_value is not None
        else None
    )

    if updated_at < created_at:
        raise WorkflowPrerequisiteError(
            "Response updated_at cannot precede created_at"
        )
    if started_at > updated_at:
        raise WorkflowPrerequisiteError(
            "Response started_at cannot follow updated_at"
        )
    if ended_at is not None and ended_at < started_at:
        raise WorkflowPrerequisiteError(
            "Response ended_at cannot precede started_at"
        )
    if ended_at is not None and ended_at > updated_at:
        raise WorkflowPrerequisiteError(
            "Response ended_at cannot follow updated_at"
        )

    execution_state = record.field("execution_state")
    if execution_state == "in_progress" and ended_at is not None:
        raise WorkflowPrerequisiteError(
            "in-progress Response cannot already have ended_at"
        )
    if execution_state == "unknown":
        raise WorkflowPrerequisiteError(
            "digital-entry Response cannot use historical unknown execution state"
        )

    action = record.field("action")
    provider = record.field("provider")
    if not isinstance(action, Mapping) or not isinstance(provider, Mapping):
        raise WorkflowOwnershipError("Response action or provider is malformed")

    if (
        action.get("family") == "consequence"
        and action.get("consequence_context") == "teacher_local"
        and provider.get("kind") in {"roster_student", "unidentified_person"}
    ):
        raise WorkflowPrerequisiteError(
            "teacher-local consequence requires an eligible human provider"
        )

    if response_is_recorded_institutional(record):
        if provider.get("kind") in {
            "roster_student",
            "descriptive_person",
            "unidentified_person",
        }:
            raise WorkflowPrerequisiteError(
                "recorded-institutional consequence requires an identified "
                "provider resolved through current local or Actor authority"
            )
        if record.field("determination_ref") is None:
            raise WorkflowPrerequisiteError(
                "recorded-institutional consequence requires Determination context"
            )


def require_response_provider_authority(
    contexts: WorkflowContextAssembler,
    record: PortiaRecord,
    *,
    require_current_use: bool,
) -> None:
    """Resolve the represented provider separately from persistence attribution."""
    provider = record.field("provider")
    require_represented_human_authority(
        contexts,
        provider,
        field_name="Response provider",
        require_current_use=require_current_use,
    )


def validate_partial_response_graph(record: PortiaRecord) -> None:
    """Run pure application validation after I/O-backed exact refs are resolved."""
    findings = validate_record_graph(
        (record,),
        options=GraphValidationOptions(require_internal_resolution=False),
    )
    if findings:
        raise WorkflowValidationError(findings)
