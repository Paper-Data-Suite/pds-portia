"""Production in-memory application validation for Portia v0.2 records."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import TypeAlias, cast

from pds_core.routing_models import ModuleWorkRef

from portia.models.base import PortiaRecord
from portia.models.errors import PortiaModelError
from portia.models.references import RosterStudentRef
from portia.validation.context import UnknownValidationContext, ValidationContext
from portia.validation.findings import ApplicationFinding

RecordKey: TypeAlias = tuple[str, str, str | None, str | None, str]
WorkKey: TypeAlias = tuple[str, str, str]

_DOMAIN_RESOLUTION_CONTRACTS = frozenset(
    {
        "event_participant_role",
        "account",
        "observation",
        "review",
        "classification",
        "hypothesis",
        "determination",
        "response",
        "communication",
        "support_process",
        "support_process_participant",
        "support_need",
        "support_goal",
        "support",
        "intervention",
        "implementation",
        "fidelity",
        "follow_up",
        "outcome",
        "reentry",
        "repair",
        "work_relationship",
        "lifecycle_transition",
        "lifecycle_history_correction",
        "amendment",
        "statement_of_disagreement",
        "dependency",
        "record_migration",
        "ownership_correction",
        "exceptional_removal",
        "deliberate_export",
    }
)


@dataclass(frozen=True, slots=True)
class GraphValidationOptions:
    """Validation controls for complete graphs versus partial editing graphs."""

    require_internal_resolution: bool = False


@dataclass(slots=True)
class _GraphIndex:
    by_key: dict[RecordKey, PortiaRecord]
    by_identity: dict[tuple[str, str], list[PortiaRecord]]
    by_version_identity: dict[tuple[str, str, str], list[PortiaRecord]]
    roots: dict[WorkKey, PortiaRecord]
    actors: dict[str, PortiaRecord]
    actor_contacts: dict[tuple[str, str, str], PortiaRecord]


def _subject(record: PortiaRecord) -> str:
    identity = record.logical_id or "<no-id>"
    class_id = record.class_id or "<no-class>"
    work_id = record.work_id or "<no-work>"
    return f"{record.contract}@{record.contract_version}:{class_id}:{work_id}:{identity}"


def _record_key(record: PortiaRecord) -> RecordKey | None:
    identity = record.logical_id
    if identity is None:
        return None
    return (
        record.contract,
        record.contract_version,
        record.class_id,
        record.work_id,
        identity,
    )


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed


def _walk(value: object, path: str = "$") -> Iterable[tuple[str, object]]:
    yield path, value
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield from _walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, f"{path}[{index}]")


def _is_local_record_ref(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"record_kind", "record_id", "contract_version"}
        and isinstance(value.get("record_kind"), str)
        and isinstance(value.get("record_id"), str)
    )


def _is_portia_work_ref(value: object) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value)
        == {"module_id", "class_id", "work_id", "work_kind", "contract_version"}
        and value.get("module_id") == "portia"
        and isinstance(value.get("class_id"), str)
        and isinstance(value.get("work_id"), str)
        and value.get("work_kind") in {"event", "support_process"}
    )


def _complete_ref_key(value: object) -> RecordKey | None:
    if not isinstance(value, Mapping):
        return None
    work_ref = value.get("work_ref")
    record_ref = value.get("record_ref")
    if not _is_portia_work_ref(work_ref) or not _is_local_record_ref(record_ref):
        return None
    assert isinstance(work_ref, Mapping)
    assert isinstance(record_ref, Mapping)
    version = record_ref.get("contract_version")
    if not isinstance(version, str):
        return None
    return (
        cast(str, record_ref["record_kind"]),
        version,
        cast(str, work_ref["class_id"]),
        cast(str, work_ref["work_id"]),
        cast(str, record_ref["record_id"]),
    )


def _local_ref_key(record: PortiaRecord, value: object) -> RecordKey | None:
    if not _is_local_record_ref(value):
        return None
    assert isinstance(value, Mapping)
    version = value.get("contract_version")
    if not isinstance(version, str):
        return None
    return (
        cast(str, value["record_kind"]),
        version,
        record.class_id,
        record.work_id,
        cast(str, value["record_id"]),
    )


def _iter_record_refs(
    record: PortiaRecord, value: object, path: str = "$"
) -> Iterable[tuple[str, RecordKey]]:
    complete = _complete_ref_key(value)
    if complete is not None:
        yield path, complete
        return
    local = _local_ref_key(record, value)
    if local is not None:
        yield path, local
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield from _iter_record_refs(record, child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_record_refs(record, child, f"{path}[{index}]")


def _iter_work_refs(value: object, path: str = "$") -> Iterable[tuple[str, Mapping[str, object]]]:
    if _complete_ref_key(value) is not None:
        assert isinstance(value, Mapping)
        work_ref = value.get("work_ref")
        assert isinstance(work_ref, Mapping)
        yield f"{path}.work_ref", cast(Mapping[str, object], work_ref)
        return
    if _is_portia_work_ref(value):
        assert isinstance(value, Mapping)
        yield path, cast(Mapping[str, object], value)
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if isinstance(key, str):
                yield from _iter_work_refs(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_work_refs(child, f"{path}[{index}]")


def _work_root_key(record: PortiaRecord) -> WorkKey | None:
    class_id = record.class_id
    work_id = record.work_id
    work_kind = record.work_kind
    if (
        isinstance(class_id, str)
        and isinstance(work_id, str)
        and work_kind in {"event", "support_process"}
    ):
        return (work_kind, class_id, work_id)
    return None


def _target_duplicate_findings(record: PortiaRecord) -> list[ApplicationFinding]:
    """Reject duplicate identities only inside an explicit plural target value.

    Repeated references in evidence, relationships, or provenance are not target
    duplication.  The accepted target contracts use a top-level ``target`` object
    whose plural branches carry a ``targets`` collection.  Exact contract version
    is intentionally excluded from the duplicate-identity key.
    """
    wire = record.to_dict()
    target = wire.get("target")
    if not isinstance(target, Mapping):
        return []
    targets = target.get("targets")
    if not isinstance(targets, list) or len(targets) < 2:
        return []

    identities: dict[tuple[str, str], int] = {}
    for item in targets:
        candidate: object = item
        if isinstance(candidate, Mapping) and "participant_ref" in candidate:
            candidate = candidate.get("participant_ref")
        if isinstance(candidate, Mapping) and "record_ref" in candidate:
            nested = candidate.get("record_ref")
            if _is_local_record_ref(nested):
                candidate = nested
        if not _is_local_record_ref(candidate):
            continue
        assert isinstance(candidate, Mapping)
        key = (cast(str, candidate["record_kind"]), cast(str, candidate["record_id"]))
        identities[key] = identities.get(key, 0) + 1

    if not any(count > 1 for count in identities.values()):
        return []
    return [
        ApplicationFinding(
            code="PORTIA.GRAPH.DUPLICATE_TARGET_IDENTITY",
            subject=_subject(record),
            path="$.target.targets",
            message=(
                "a selected-target collection repeats the same canonical "
                "record identity under multiple exact representations"
            ),
        )
    ]


def _timestamp_findings(record: PortiaRecord) -> list[ApplicationFinding]:
    findings: list[ApplicationFinding] = []
    pairs = (
        ("created_at", "updated_at"),
        ("started_at", "ended_at"),
        ("effective_from", "effective_to"),
        ("scheduled_for", "completed_at"),
    )
    for path, value in _walk(record.to_dict()):
        if not isinstance(value, Mapping):
            continue
        for earlier_name, later_name in pairs:
            earlier = _parse_timestamp(value.get(earlier_name))
            later = _parse_timestamp(value.get(later_name))
            if earlier is not None and later is not None and later < earlier:
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.TIMESTAMP_ORDER",
                        subject=_subject(record),
                        path=path,
                        message=(
                            f"{later_name} must not precede {earlier_name} under "
                            "the accepted chronology rules"
                        ),
                    )
                )
    return findings


def _parse_date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _planning_findings(record: PortiaRecord) -> list[ApplicationFinding]:
    """Validate accepted planning chronology without implying implementation."""
    findings: list[ApplicationFinding] = []
    wire = record.to_dict()

    planned_start = _parse_date(wire.get("planned_start_date"))
    planned_end = _parse_date(wire.get("planned_end_date"))
    if planned_start is not None and planned_end is not None and planned_end < planned_start:
        findings.append(
            ApplicationFinding(
                code="PORTIA.GRAPH.PLANNED_DATE_ORDER",
                subject=_subject(record),
                path="$",
                message="planned_end_date must not precede planned_start_date",
            )
        )

    schedule = wire.get("schedule")
    if not isinstance(schedule, Mapping):
        return findings
    window = schedule.get("window")
    if isinstance(window, Mapping):
        starts_on = _parse_date(window.get("starts_on"))
        ends_on = _parse_date(window.get("ends_on"))
        if starts_on is not None and ends_on is not None and ends_on < starts_on:
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.PLANNED_SCHEDULE_WINDOW_ORDER",
                    subject=_subject(record),
                    path="$.schedule.window",
                    message="planned schedule ends_on must not precede starts_on",
                )
            )

    duration = schedule.get("planned_duration")
    if isinstance(duration, Mapping) and duration.get("kind") == "range_minutes":
        minimum = duration.get("minimum_minutes")
        maximum = duration.get("maximum_minutes")
        if (
            isinstance(minimum, int)
            and not isinstance(minimum, bool)
            and isinstance(maximum, int)
            and not isinstance(maximum, bool)
            and maximum < minimum
        ):
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.PLANNED_SCHEDULE_DURATION_ORDER",
                    subject=_subject(record),
                    path="$.schedule.planned_duration",
                    message=(
                        "planned schedule maximum_minutes must not be less than "
                        "minimum_minutes"
                    ),
                )
            )
    return findings


def _module_ref_findings(record: PortiaRecord) -> list[ApplicationFinding]:
    findings: list[ApplicationFinding] = []
    for path, value in _walk(record.to_dict()):
        if not isinstance(value, Mapping):
            continue
        work_ref = value.get("work_ref")
        record_ref = value.get("record_ref")
        if not isinstance(work_ref, Mapping) or not isinstance(record_ref, Mapping):
            continue
        work_module = work_ref.get("module_id")
        record_module = record_ref.get("module_id")
        if (
            isinstance(work_module, str)
            and isinstance(record_module, str)
            and work_module != record_module
        ):
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.MODULE_ID_MISMATCH",
                    subject=_subject(record),
                    path=path,
                    message="work and record references disagree on producer module identity",
                )
            )
    return findings


def _external_resolution_findings(
    record: PortiaRecord, context: ValidationContext
) -> list[ApplicationFinding]:
    findings: list[ApplicationFinding] = []
    seen_roster: set[tuple[str, str]] = set()
    seen_core_work: set[tuple[str, str, str]] = set()

    for path, value in _walk(record.to_dict()):
        if not isinstance(value, Mapping):
            continue
        roster_value: object | None = None
        if value.get("kind") == "roster_student":
            roster_value = value.get("roster_student_ref")
        elif set(value) == {"class_id", "student_id"}:
            roster_value = value
        if isinstance(roster_value, Mapping):
            try:
                roster_reference = RosterStudentRef.from_dict(roster_value)
            except PortiaModelError:
                roster_reference = None
            if roster_reference is not None:
                roster_key = (roster_reference.class_id, roster_reference.student_id)
                if roster_key not in seen_roster:
                    seen_roster.add(roster_key)
                    if context.roster_student_exists(roster_reference) is False:
                        findings.append(
                            ApplicationFinding(
                                code="PORTIA.GRAPH.ROSTER_STUDENT_UNRESOLVED",
                                subject=_subject(record),
                                path=path,
                                message=(
                                    "an exact class-qualified roster student reference "
                                    "was reported absent by the authoritative context"
                                ),
                            )
                        )

        work_ref = value.get("work_ref")
        if isinstance(work_ref, Mapping) and work_ref.get("module_id") != "portia":
            module_id = work_ref.get("module_id")
            class_id = work_ref.get("class_id")
            work_id = work_ref.get("work_id")
            if (
                isinstance(module_id, str)
                and isinstance(class_id, str)
                and isinstance(work_id, str)
            ):
                key = (module_id, class_id, work_id)
                if key not in seen_core_work:
                    seen_core_work.add(key)
                    core_reference = ModuleWorkRef(
                        module_id=module_id, class_id=class_id, work_id=work_id
                    )
                    if context.core_work_exists(core_reference) is False:
                        findings.append(
                            ApplicationFinding(
                                code="PORTIA.GRAPH.CORE_WORK_UNRESOLVED",
                                subject=_subject(record),
                                path=path,
                                message=(
                                    "an exact Core/sibling work reference was reported "
                                    "absent by the authoritative context"
                                ),
                            )
                        )
    return findings


def _index_records(records: Sequence[PortiaRecord]) -> tuple[_GraphIndex, list[ApplicationFinding]]:
    by_key: dict[RecordKey, PortiaRecord] = {}
    by_identity: dict[tuple[str, str], list[PortiaRecord]] = defaultdict(list)
    by_version_identity: dict[tuple[str, str, str], list[PortiaRecord]] = defaultdict(list)
    roots: dict[WorkKey, PortiaRecord] = {}
    actors: dict[str, PortiaRecord] = {}
    actor_contacts: dict[tuple[str, str, str], PortiaRecord] = {}
    findings: list[ApplicationFinding] = []

    for record in records:
        if not isinstance(record, PortiaRecord):
            raise TypeError("validate_record_graph accepts PortiaRecord values only")
        key = _record_key(record)
        if key is not None:
            if key in by_key:
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.DUPLICATE_IDENTITY",
                        subject=_subject(record),
                        message="the graph contains duplicate exact canonical identity",
                    )
                )
            else:
                by_key[key] = record
            by_identity[(record.contract, key[4])].append(record)
            by_version_identity[(record.contract, record.contract_version, key[4])].append(
                record
            )

        if record.contract in {"event", "support_process"}:
            class_id = record.class_id
            work_id = record.work_id
            if class_id is not None and work_id is not None:
                root_key = (record.contract, class_id, work_id)
                if root_key in roots:
                    findings.append(
                        ApplicationFinding(
                            code="PORTIA.GRAPH.DUPLICATE_WORK_ROOT",
                            subject=_subject(record),
                            message="the graph contains duplicate work-root identity",
                        )
                    )
                else:
                    roots[root_key] = record

        if record.contract == "actor" and record.logical_id is not None:
            actors[record.logical_id] = record
        if record.contract == "actor_contact_point":
            wire = record.to_dict()
            actor_id = wire.get("actor_id")
            contact_id = wire.get("contact_point_id")
            if isinstance(actor_id, str) and isinstance(contact_id, str):
                actor_contacts[(actor_id, contact_id, record.contract_version)] = record

    return (
        _GraphIndex(
            by_key=by_key,
            by_identity=by_identity,
            by_version_identity=by_version_identity,
            roots=roots,
            actors=actors,
            actor_contacts=actor_contacts,
        ),
        findings,
    )


def _reference_finding(
    record: PortiaRecord, path: str, ref_key: RecordKey, index: _GraphIndex
) -> ApplicationFinding | None:
    if ref_key in index.by_key:
        return None
    kind, version, class_id, work_id, record_id = ref_key
    same_version = index.by_version_identity.get((kind, version, record_id), [])
    same_identity = index.by_identity.get((kind, record_id), [])
    if any(
        candidate.class_id != class_id or candidate.work_id != work_id
        for candidate in same_version
    ):
        code = "PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK"
        message = (
            "an exact Portia record reference resolves only in a different "
            "class/work scope"
        )
    elif any(
        candidate.class_id == class_id
        and candidate.work_id == work_id
        and candidate.contract_version != version
        for candidate in same_identity
    ):
        code = "PORTIA.GRAPH.EXACT_REFERENCE_VERSION_MISMATCH"
        message = (
            "an exact Portia record reference requests a different contract "
            "version than the represented target"
        )
    else:
        code = "PORTIA.GRAPH.UNRESOLVED_EXACT_REFERENCE"
        message = "an exact Portia record reference does not resolve in the complete graph"
    return ApplicationFinding(
        code=code,
        subject=_subject(record),
        path=path,
        message=message,
        related=(": ".join(str(part) for part in ref_key),),
    )


def _work_reference_finding(
    record: PortiaRecord,
    path: str,
    work_ref: Mapping[str, object],
    index: _GraphIndex,
) -> ApplicationFinding | None:
    class_id = work_ref.get("class_id")
    work_id = work_ref.get("work_id")
    work_kind = work_ref.get("work_kind")
    version = work_ref.get("contract_version")
    if not all(isinstance(item, str) for item in (class_id, work_id, work_kind)):
        return None
    key = cast(WorkKey, (work_kind, class_id, work_id))
    root = index.roots.get(key)
    if root is None:
        same_id = [
            candidate
            for candidate_key, candidate in index.roots.items()
            if candidate_key[0] == work_kind and candidate_key[2] == work_id
        ]
        if same_id:
            return ApplicationFinding(
                code="PORTIA.GRAPH.EXACT_WORK_REFERENCE_WRONG_CLASS",
                subject=_subject(record),
                path=path,
                message="an exact Portia work reference resolves only in another class",
            )
        return ApplicationFinding(
            code="PORTIA.GRAPH.UNRESOLVED_WORK_REFERENCE",
            subject=_subject(record),
            path=path,
            message="an exact Portia work reference does not resolve in the complete graph",
        )
    if isinstance(version, str) and root.contract_version != version:
        return ApplicationFinding(
            code="PORTIA.GRAPH.EXACT_WORK_REFERENCE_VERSION_MISMATCH",
            subject=_subject(record),
            path=path,
            message="an exact Portia work reference requests the wrong contract version",
        )
    return None


def _actor_findings(record: PortiaRecord, index: _GraphIndex) -> list[ApplicationFinding]:
    if record.contract not in {
        "actor_contact_point",
        "actor_student_relationship",
        "communication",
    }:
        return []
    findings: list[ApplicationFinding] = []
    wire = record.to_dict()

    if record.contract in {"actor_contact_point", "actor_student_relationship"}:
        actor_id = wire.get("actor_id")
        actor = index.actors.get(actor_id) if isinstance(actor_id, str) else None
        if actor is None:
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.ACTOR_UNRESOLVED",
                    subject=_subject(record),
                    message="the owning Actor does not resolve in the complete graph",
                )
            )
        elif record.status == "active" and actor.status != "active":
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.ACTOR_NOT_ACTIVE",
                    subject=_subject(record),
                    message="an active Actor child record requires an active Actor",
                )
            )

    if record.contract != "communication":
        return findings

    recipients = wire.get("recipients")
    seen: set[tuple[str, str]] = set()
    if not isinstance(recipients, list):
        return findings
    for index_number, recipient in enumerate(recipients):
        if not isinstance(recipient, Mapping):
            continue
        person = recipient.get("person")
        if not isinstance(person, Mapping) or person.get("kind") != "actor":
            continue
        actor_ref = person.get("actor_ref")
        actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
        actor = index.actors.get(actor_id) if isinstance(actor_id, str) else None
        path = f"$.recipients[{index_number}]"
        if actor is None:
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.COMMUNICATION_ACTOR_UNRESOLVED",
                    subject=_subject(record),
                    path=path,
                    message="a Communication recipient Actor does not resolve",
                )
            )
        elif actor.status != "active":
            findings.append(
                ApplicationFinding(
                    code="PORTIA.GRAPH.COMMUNICATION_ACTOR_NOT_ACTIVE",
                    subject=_subject(record),
                    path=path,
                    message="a Communication recipient Actor is not active",
                )
            )
        if isinstance(actor_id, str):
            logical = ("actor", actor_id)
            if logical in seen:
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.COMMUNICATION_DUPLICATE_RECIPIENT",
                        subject=_subject(record),
                        path=path,
                        message="a Communication repeats the same logical recipient",
                    )
                )
            seen.add(logical)

        endpoint = recipient.get("endpoint_ref")
        if isinstance(endpoint, Mapping):
            endpoint_actor = endpoint.get("actor_id")
            contact_id = endpoint.get("contact_point_id")
            contract_version = endpoint.get("contract_version")
            if all(
                isinstance(item, str)
                for item in (endpoint_actor, contact_id, contract_version)
            ):
                contact_key = cast(
                    tuple[str, str, str],
                    (endpoint_actor, contact_id, contract_version),
                )
                contact = index.actor_contacts.get(contact_key)
                if contact is None:
                    findings.append(
                        ApplicationFinding(
                            code="PORTIA.GRAPH.COMMUNICATION_ENDPOINT_UNRESOLVED",
                            subject=_subject(record),
                            path=path,
                            message="an exact recipient Contact Point does not resolve",
                        )
                    )
                else:
                    if contact.status != "active":
                        findings.append(
                            ApplicationFinding(
                                code="PORTIA.GRAPH.COMMUNICATION_ENDPOINT_NOT_ACTIVE",
                                subject=_subject(record),
                                path=path,
                                message="the exact recipient Contact Point is not active",
                            )
                        )
                    if endpoint_actor != actor_id:
                        findings.append(
                            ApplicationFinding(
                                code="PORTIA.GRAPH.COMMUNICATION_ENDPOINT_WRONG_ACTOR",
                                subject=_subject(record),
                                path=path,
                                message="the Contact Point belongs to another Actor",
                            )
                        )
    return findings


def _judgment_evidence_scope_findings(
    record: PortiaRecord,
) -> list[ApplicationFinding]:
    """Keep Event-local judgment references inside the owning Event.

    Exact Portia references may resolve successfully and still be invalid for an
    Event-local human-judgment record when their work scope names another Event.
    The accepted application contract therefore requires both exact resolution
    and agreement with the judgment record's owning class/work scope.
    """
    if record.contract not in {
        "review",
        "classification",
        "hypothesis",
        "determination",
    }:
        return []

    class_id = record.class_id
    work_id = record.work_id
    if class_id is None or work_id is None:
        return []

    findings: list[ApplicationFinding] = []
    for path, work_ref in _iter_work_refs(record.to_dict()):
        if work_ref.get("class_id") == class_id and work_ref.get("work_id") == work_id:
            continue
        findings.append(
            ApplicationFinding(
                code="PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",
                subject=_subject(record),
                path=path,
                message=(
                    "an Event-local judgment reference points outside the "
                    "judgment record's owning Event"
                ),
            )
        )
    return findings


def _judgment_findings(record: PortiaRecord, index: _GraphIndex) -> list[ApplicationFinding]:
    if record.contract not in {"classification", "hypothesis", "determination"}:
        return []
    wire = record.to_dict()
    review_ref = wire.get("review_ref")
    if not isinstance(review_ref, Mapping):
        return []
    key = _complete_ref_key(review_ref)
    if key is None:
        return []
    review = index.by_key.get(key)
    if review is None:
        return []
    requires_completed = (
        record.contract == "determination" and record.status == "active"
    ) or (
        record.contract == "classification"
        and record.status == "active"
        and wire.get("stage") in {"reviewer_selected", "reviewer_confirmed"}
    )
    if requires_completed and review.field("review_state") != "completed":
        return [
            ApplicationFinding(
                code="PORTIA.GRAPH.JUDGMENT_REVIEW_NOT_COMPLETED",
                subject=_subject(record),
                path="$.review_ref",
                message="an active human judgment requires a completed Review",
            )
        ]
    return []


def _supersession_predecessors(record: PortiaRecord) -> tuple[RecordKey, ...]:
    supersedes = record.to_dict().get("supersedes")
    if not isinstance(supersedes, list):
        return ()
    predecessors: list[RecordKey] = []
    for _path, key in _iter_record_refs(record, supersedes, "$.supersedes"):
        predecessors.append(key)
    for _path, work_ref in _iter_work_refs(supersedes, "$.supersedes"):
        version = work_ref.get("contract_version")
        class_id = work_ref.get("class_id")
        work_id = work_ref.get("work_id")
        work_kind = work_ref.get("work_kind")
        if all(isinstance(item, str) for item in (version, class_id, work_id, work_kind)):
            predecessors.append(
                cast(
                    RecordKey,
                    (work_kind, version, class_id, work_id, work_id),
                )
            )
    return tuple(dict.fromkeys(predecessors))


def _supersession_findings(
    records: Sequence[PortiaRecord], index: _GraphIndex
) -> list[ApplicationFinding]:
    findings: list[ApplicationFinding] = []
    edges: dict[RecordKey, set[RecordKey]] = defaultdict(set)
    for record in records:
        own_key = _record_key(record)
        if own_key is None:
            continue
        for predecessor in _supersession_predecessors(record):
            if predecessor == own_key:
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.SELF_SUPERSESSION",
                        subject=_subject(record),
                        path="$.supersedes",
                        message="a record cannot supersede its own exact representation",
                    )
                )
            edges[own_key].add(predecessor)

    visiting: set[RecordKey] = set()
    visited: set[RecordKey] = set()
    emitted: set[tuple[RecordKey, ...]] = set()

    def visit(node: RecordKey, trail: tuple[RecordKey, ...]) -> None:
        if node in visited:
            return
        if node in visiting:
            start = trail.index(node) if node in trail else 0
            cycle = trail[start:] + (node,)
            normalized = tuple(sorted(set(cycle), key=str))
            if normalized not in emitted:
                emitted.add(normalized)
                source = index.by_key.get(node)
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.SUPERSESSION_CYCLE",
                        subject=_subject(source) if source is not None else str(node),
                        message="exact supersession references form a cycle",
                        related=tuple(str(item) for item in cycle),
                    )
                )
            return
        visiting.add(node)
        for target in sorted(edges.get(node, set()), key=str):
            if target in edges:
                visit(target, trail + (node,))
        visiting.remove(node)
        visited.add(node)

    for node in sorted(edges, key=str):
        visit(node, ())
    return findings


def validate_record_graph(
    records: Sequence[PortiaRecord],
    *,
    context: ValidationContext | None = None,
    options: GraphValidationOptions = GraphValidationOptions(),
) -> tuple[ApplicationFinding, ...]:
    """Validate an in-memory graph without filesystem or network access.

    Structural wire validation occurs while each ``PortiaRecord`` is built.  This
    function handles only cross-record/application invariants.  External
    existence is never guessed: callers may provide an authoritative bounded
    ``ValidationContext`` or leave it unknown.
    """
    effective_context: ValidationContext = context or UnknownValidationContext()
    index, findings = _index_records(records)

    for record in records:
        findings.extend(_target_duplicate_findings(record))
        findings.extend(_timestamp_findings(record))
        findings.extend(_planning_findings(record))
        findings.extend(_module_ref_findings(record))
        findings.extend(_external_resolution_findings(record, effective_context))
        findings.extend(_actor_findings(record, index))
        findings.extend(_judgment_evidence_scope_findings(record))
        findings.extend(_judgment_findings(record, index))

        if record.contract in {"event", "support_process"}:
            pass
        elif record.class_id is not None and record.work_id is not None:
            expected_root = _work_root_key(record)
            if (
                options.require_internal_resolution
                and expected_root is not None
                and expected_root not in index.roots
            ):
                findings.append(
                    ApplicationFinding(
                        code="PORTIA.GRAPH.UNRESOLVED_WORK_ROOT",
                        subject=_subject(record),
                        message=(
                            "the containing Portia work root is absent from the "
                            "complete graph"
                        ),
                    )
                )

        if options.require_internal_resolution and record.contract in _DOMAIN_RESOLUTION_CONTRACTS:
            wire = record.to_dict()
            for path, ref_key in _iter_record_refs(record, wire):
                finding = _reference_finding(record, path, ref_key, index)
                if finding is not None:
                    findings.append(finding)
            for path, work_ref in _iter_work_refs(wire):
                finding = _work_reference_finding(record, path, work_ref, index)
                if finding is not None:
                    findings.append(finding)

    findings.extend(_supersession_findings(records, index))
    return tuple(sorted(set(findings)))
