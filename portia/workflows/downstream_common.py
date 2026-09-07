"""Shared authority mechanics for Issue #46 downstream workflow families."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Final

from portia.models import PortiaRecord
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaNotFoundError
from portia.storage.repository import StoredRecord
from portia.workflows.common import (
    EVENT_VERSION,
    PARTICIPANT_VERSION,
    WorkflowServiceBase,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from portia.workflows.judgment_common import require_represented_human_authority
from portia.workflows.participants import ParticipantWorkflowService
from portia.workflows.support_process_participants import (
    SUPPORT_PROCESS_PARTICIPANT_VERSION,
    SupportProcessParticipantPersonResolution,
    SupportProcessParticipantWorkflowService,
    support_process_participant_reference,
)
from portia.workflows.support_processes import SUPPORT_PROCESS_VERSION

DOWNSTREAM_VERSION: Final[str] = "1"
DOWNSTREAM_CONTRACTS: Final[frozenset[str]] = frozenset(
    {"follow_up", "outcome", "reentry", "repair"}
)
DOWNSTREAM_OWNERS: Final[frozenset[tuple[str, str]]] = frozenset(
    {
        ("event", EVENT_VERSION),
        ("support_process", SUPPORT_PROCESS_VERSION),
    }
)

_EVENT_TARGET_KINDS = frozenset(
    {"event", "event_participant", "event_participants"}
)
_SUPPORT_PROCESS_TARGET_KINDS = frozenset(
    {
        "support_process",
        "support_process_participant",
        "support_process_participants",
    }
)
_EVENT_OPERATIONAL_KINDS = frozenset({"actor", "local_operator"})


@dataclass(frozen=True, slots=True)
class DownstreamTargetResolution:
    """Exact owner plus any explicitly targeted participant records."""

    owner: StoredRecord
    participants: tuple[StoredRecord, ...]


@dataclass(frozen=True, slots=True)
class DownstreamExactRecordResolution:
    """One exact Portia work-record resolution without successor following."""

    reference: ExactPortiaWorkRecordRef
    stored: StoredRecord


@dataclass(frozen=True, slots=True)
class DownstreamRelatedRecordResolution:
    """One role-bearing exact Portia work-record relation."""

    role: str
    reference: ExactPortiaWorkRecordRef
    stored: StoredRecord


def require_downstream_owner(work: ExactPortiaWorkRef) -> None:
    """Require the frozen Event/Support Process owner union used by Issue #46."""
    if (work.work_kind, work.contract_version) not in DOWNSTREAM_OWNERS:
        raise WorkflowOwnershipError(
            "Issue #46 downstream workflows require exact event@2 or "
            "support_process@1 ownership"
        )


def require_downstream_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    contract: str,
) -> None:
    """Require exact work-local ownership for one v1 downstream record."""
    require_downstream_owner(work)
    if contract not in DOWNSTREAM_CONTRACTS:
        raise WorkflowOwnershipError(
            f"unsupported Issue #46 downstream contract {contract!r}"
        )
    if record.contract != contract or record.contract_version != DOWNSTREAM_VERSION:
        raise WorkflowOwnershipError(
            f"new {contract} writes require {contract}@1 input"
        )
    if (
        record.class_id != work.class_id
        or record.work_id != work.work_id
        or record.work_kind != work.work_kind
    ):
        raise WorkflowOwnershipError(
            f"{contract} does not belong to the explicitly selected "
            f"{work.work_kind} work"
        )


def downstream_reference(
    work: ExactPortiaWorkRef,
    contract: str,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct an exact v1 reference for one Issue #46 record family."""
    require_downstream_owner(work)
    if contract not in DOWNSTREAM_CONTRACTS:
        raise WorkflowOwnershipError(
            f"unsupported Issue #46 downstream contract {contract!r}"
        )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=contract,
            record_id=record_id,
            contract_version=DOWNSTREAM_VERSION,
        ),
    )


def follow_up_reference(
    work: ExactPortiaWorkRef,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return downstream_reference(work, "follow_up", record_id)


def outcome_reference(
    work: ExactPortiaWorkRef,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return downstream_reference(work, "outcome", record_id)


def reentry_reference(
    work: ExactPortiaWorkRef,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return downstream_reference(work, "reentry", record_id)


def repair_reference(
    work: ExactPortiaWorkRef,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    return downstream_reference(work, "repair", record_id)


def parse_explicit_timestamp(value: object, *, field_name: str) -> datetime:
    """Parse an accepted explicit-offset timestamp without inventing precision."""
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{field_name} timestamp is malformed")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{field_name} timestamp is malformed"
        ) from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"{field_name} timestamp lacks an explicit offset"
        )
    return parsed


def parse_date_only(value: object, *, field_name: str) -> date:
    """Parse a date-only value without upgrading it to timestamp precision."""
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{field_name} date is malformed")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(f"{field_name} date is malformed") from exc


def require_timestamp_order(
    earlier: object,
    later: object,
    *,
    earlier_name: str,
    later_name: str,
) -> None:
    """Require ``later >= earlier`` for explicit-offset timestamps."""
    earlier_at = parse_explicit_timestamp(earlier, field_name=earlier_name)
    later_at = parse_explicit_timestamp(later, field_name=later_name)
    if later_at < earlier_at:
        raise WorkflowPrerequisiteError(
            f"{later_name} cannot precede {earlier_name}"
        )


def require_date_order(
    earlier: object,
    later: object,
    *,
    earlier_name: str,
    later_name: str,
) -> None:
    """Require ``later >= earlier`` at honest date-only precision."""
    earlier_on = parse_date_only(earlier, field_name=earlier_name)
    later_on = parse_date_only(later, field_name=later_name)
    if later_on < earlier_on:
        raise WorkflowPrerequisiteError(
            f"{later_name} cannot precede {earlier_name}"
        )


def _exact_work_record_reference(
    value: object,
    *,
    field_name: str,
) -> ExactPortiaWorkRecordRef:
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"{field_name} exact record reference is malformed")
    try:
        reference = ExactPortiaWorkRecordRef.from_dict(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(
            f"{field_name} exact record reference is malformed"
        ) from exc
    if not isinstance(reference.record_ref.contract_version, str):
        raise WorkflowPrerequisiteError(
            f"{field_name} requires an exact record contract version"
        )
    return reference


def _require_exact_record_matches_reference(
    reference: ExactPortiaWorkRecordRef,
    stored: StoredRecord,
    *,
    field_name: str,
) -> None:
    record = stored.record
    if (
        record.contract != reference.record_ref.record_kind
        or record.contract_version != reference.record_ref.contract_version
        or record.class_id != reference.work_ref.class_id
        or record.work_id != reference.work_ref.work_id
        or (
            record.work_kind is not None
            and record.work_kind != reference.work_ref.work_kind
        )
        or record.logical_id != reference.record_ref.record_id
    ):
        raise WorkflowOwnershipError(
            f"{field_name} resolved record does not match its exact reference"
        )


def _target_entries(
    target: Mapping[str, object],
    *,
    singular_kind: str,
    plural_kind: str,
) -> tuple[Mapping[str, object], ...]:
    kind = target.get("kind")
    if kind == singular_kind:
        return (target,)
    if kind != plural_kind:
        return ()
    raw_targets = target.get("targets")
    if not isinstance(raw_targets, Sequence) or isinstance(
        raw_targets, (str, bytes)
    ):
        raise WorkflowOwnershipError("plural downstream target is malformed")
    entries: list[Mapping[str, object]] = []
    for item in raw_targets:
        if not isinstance(item, Mapping):
            raise WorkflowOwnershipError("downstream target entry is malformed")
        entries.append(item)
    return tuple(entries)


def _exact_target_ref(
    work: ExactPortiaWorkRef,
    entry: Mapping[str, object],
    *,
    record_kind: str,
) -> ExactPortiaWorkRecordRef:
    raw_ref = entry.get("record_ref")
    if not isinstance(raw_ref, Mapping):
        raise WorkflowOwnershipError("downstream target record reference is malformed")
    kind = raw_ref.get("record_kind")
    record_id = raw_ref.get("record_id")
    version = raw_ref.get("contract_version")
    if kind != record_kind or not isinstance(record_id, str):
        raise WorkflowOwnershipError(
            f"downstream target must name {record_kind}"
        )
    if not isinstance(version, str):
        raise WorkflowPrerequisiteError(
            "downstream target requires an exact contract version"
        )
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=record_kind,
            record_id=record_id,
            contract_version=version,
        ),
    )


def _strong_person_identity(record: PortiaRecord) -> tuple[object, ...] | None:
    if record.contract == "event_participant":
        field_name = "subject"
    elif record.contract == "support_process_participant":
        field_name = "person"
    else:
        raise WorkflowOwnershipError(
            "logical-human target checks require a Participant record"
        )
    person = record.field(field_name)
    if not isinstance(person, Mapping):
        raise WorkflowOwnershipError("target Participant person is malformed")
    kind = person.get("kind")
    if kind == "roster_student":
        raw_ref = person.get("roster_student_ref")
        if not isinstance(raw_ref, Mapping):
            raise WorkflowOwnershipError(
                "target Participant roster identity is malformed"
            )
        return (
            kind,
            raw_ref.get("class_id"),
            raw_ref.get("student_id"),
        )
    if kind == "actor":
        raw_ref = person.get("actor_ref")
        if not isinstance(raw_ref, Mapping):
            raise WorkflowOwnershipError(
                "target Participant Actor identity is malformed"
            )
        return (kind, raw_ref.get("actor_id"))
    if kind == "local_operator":
        return (kind,)
    if kind in {
        "descriptive_person",
        "unknown_person",
        "unidentified_person",
    }:
        return None
    raise WorkflowOwnershipError(
        f"unsupported target Participant person kind {kind!r}"
    )


def _require_unique_target_people(records: Sequence[StoredRecord]) -> None:
    seen: set[tuple[object, ...]] = set()
    for stored in records:
        identity = _strong_person_identity(stored.record)
        if identity is None:
            continue
        if identity in seen:
            raise WorkflowPrerequisiteError(
                "downstream target repeats the same logical human identity"
            )
        seen.add(identity)


class DownstreamWorkflowAuthority(WorkflowServiceBase):
    """Shared exact owner, target, and operational-human authority for Issue #46."""

    def _participant_service(self) -> ParticipantWorkflowService:
        return ParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def _support_process_participant_service(
        self,
    ) -> SupportProcessParticipantWorkflowService:
        return SupportProcessParticipantWorkflowService(
            self.workspace_root,
            repository=self.repository,
            quarantine=self.quarantine,
            context_assembler=self.contexts,
        )

    def load_owner_exact(self, work: ExactPortiaWorkRef) -> StoredRecord:
        """Resolve exactly the requested owner without successor following."""
        require_downstream_owner(work)
        owner = self.repository.load_work(work)
        expected_contract = work.work_kind
        if (
            owner.record.contract != expected_contract
            or owner.record.contract_version != work.contract_version
            or owner.record.class_id != work.class_id
            or owner.record.work_id != work.work_id
        ):
            raise WorkflowOwnershipError(
                "resolved downstream owner does not match the exact work reference"
            )
        return owner

    resolve_owner_exact = load_owner_exact

    def resolve_target(
        self,
        work: ExactPortiaWorkRef,
        target: object,
        *,
        require_current_use: bool,
    ) -> DownstreamTargetResolution:
        """Resolve one owner-conditioned target without inferring target identity."""
        owner = self.load_owner_exact(work)
        if not isinstance(target, Mapping):
            raise WorkflowOwnershipError("downstream target is malformed")
        kind = target.get("kind")
        if work.work_kind == "event":
            if kind not in _EVENT_TARGET_KINDS:
                raise WorkflowOwnershipError(
                    "Event-owned downstream records require an Event-local target"
                )
            entries = _target_entries(
                target,
                singular_kind="event_participant",
                plural_kind="event_participants",
            )
            event_service = self._participant_service()
            participants: list[StoredRecord] = []
            for entry in entries:
                reference = _exact_target_ref(
                    work,
                    entry,
                    record_kind="event_participant",
                )
                if require_current_use:
                    if reference.record_ref.contract_version != PARTICIPANT_VERSION:
                        raise WorkflowPrerequisiteError(
                            "current Event target requires event_participant@3"
                        )
                    event_resolution = event_service.require_current_use(reference)
                else:
                    event_resolution = event_service.resolve_exact(reference)
                participants.append(event_resolution.participant)
        else:
            if kind not in _SUPPORT_PROCESS_TARGET_KINDS:
                raise WorkflowOwnershipError(
                    "Support-Process-owned downstream records require a "
                    "Support Process-local target"
                )
            entries = _target_entries(
                target,
                singular_kind="support_process_participant",
                plural_kind="support_process_participants",
            )
            support_service = self._support_process_participant_service()
            participants = []
            for entry in entries:
                reference = _exact_target_ref(
                    work,
                    entry,
                    record_kind="support_process_participant",
                )
                if require_current_use:
                    if (
                        reference.record_ref.contract_version
                        != SUPPORT_PROCESS_PARTICIPANT_VERSION
                    ):
                        raise WorkflowPrerequisiteError(
                            "current Support Process target requires "
                            "support_process_participant@1"
                        )
                    support_resolution = support_service.require_current_use(reference)
                else:
                    support_resolution = support_service.resolve_exact(reference)
                participants.append(support_resolution.participant)

        _require_unique_target_people(participants)
        return DownstreamTargetResolution(
            owner=owner,
            participants=tuple(participants),
        )

    def resolve_exact_work_record(
        self,
        owner_work: ExactPortiaWorkRef,
        value: object,
        *,
        field_name: str,
        require_same_class: bool = True,
        require_same_work: bool = False,
    ) -> DownstreamExactRecordResolution:
        """Resolve one exact Portia work-record reference without successor following."""
        require_downstream_owner(owner_work)
        reference = _exact_work_record_reference(value, field_name=field_name)
        require_downstream_owner(reference.work_ref)
        if require_same_class and reference.work_ref.class_id != owner_work.class_id:
            raise WorkflowOwnershipError(
                f"{field_name} exact record reference must remain in the owning class"
            )
        if require_same_work and reference.work_ref != owner_work:
            raise WorkflowOwnershipError(
                f"{field_name} exact record reference must remain in the owning work"
            )
        try:
            self.repository.load_work(reference.work_ref)
            stored = self.repository.load_work_record(
                reference.work_ref,
                reference.record_ref.record_kind,
                reference.record_ref.contract_version,
                reference.record_ref.record_id,
            )
        except PortiaNotFoundError as exc:
            raise WorkflowPrerequisiteError(
                f"{field_name} exact record reference does not resolve"
            ) from exc
        _require_exact_record_matches_reference(
            reference,
            stored,
            field_name=field_name,
        )
        return DownstreamExactRecordResolution(
            reference=reference,
            stored=stored,
        )

    def resolve_related_records(
        self,
        work: ExactPortiaWorkRef,
        values: object,
        *,
        field_name: str,
        allowed_roles: frozenset[str],
        role_contracts: Mapping[str, frozenset[str]],
        self_reference: ExactPortiaWorkRecordRef | None = None,
        same_work_roles: frozenset[str] = frozenset(),
    ) -> tuple[DownstreamRelatedRecordResolution, ...]:
        """Resolve role-bearing exact relations with no inference or successor following."""
        require_downstream_owner(work)
        if values is None:
            return ()
        if not isinstance(values, Sequence) or isinstance(
            values, (str, bytes, bytearray)
        ):
            raise WorkflowOwnershipError(f"{field_name} relation set is malformed")

        resolved: list[DownstreamRelatedRecordResolution] = []
        seen: set[tuple[str, ExactPortiaWorkRecordRef]] = set()
        for index, item in enumerate(values):
            if not isinstance(item, Mapping):
                raise WorkflowOwnershipError(
                    f"{field_name} relation entry {index} is malformed"
                )
            role = item.get("role")
            if not isinstance(role, str) or role not in allowed_roles:
                raise WorkflowPrerequisiteError(
                    f"{field_name} relation entry {index} has unsupported role {role!r}"
                )
            allowed_contracts = role_contracts.get(role)
            if allowed_contracts is None:
                raise WorkflowPrerequisiteError(
                    f"{field_name} role {role!r} has no configured contract policy"
                )
            reference = _exact_work_record_reference(
                item.get("record_ref"),
                field_name=f"{field_name} relation entry {index}",
            )
            relation_identity = (role, reference)
            if relation_identity in seen:
                raise WorkflowPrerequisiteError(
                    f"{field_name} cannot repeat one exact related-record relation"
                )
            if self_reference is not None and reference == self_reference:
                raise WorkflowPrerequisiteError(
                    f"{field_name} cannot reference the current record itself"
                )
            if reference.work_ref.class_id != work.class_id:
                raise WorkflowOwnershipError(
                    f"{field_name} exact related record must remain in the owning class"
                )
            if (
                reference.record_ref.record_kind not in allowed_contracts
            ):
                raise WorkflowPrerequisiteError(
                    f"{field_name} role {role!r} is incompatible with "
                    f"{reference.record_ref.record_kind!r}"
                )
            if role in same_work_roles and reference.work_ref != work:
                raise WorkflowOwnershipError(
                    f"{field_name} role {role!r} must remain in the owning work"
                )

            exact = self.resolve_exact_work_record(
                work,
                reference.to_dict(),
                field_name=f"{field_name} relation entry {index}",
                require_same_class=True,
                require_same_work=False,
            )
            seen.add(relation_identity)
            resolved.append(
                DownstreamRelatedRecordResolution(
                    role=role,
                    reference=reference,
                    stored=exact.stored,
                )
            )
        return tuple(resolved)

    def require_event_operational_human(
        self,
        value: object,
        *,
        field_name: str,
        require_current_use: bool,
    ) -> None:
        """Resolve one Event-owned operational human without treating a student as staff."""
        if not isinstance(value, Mapping):
            raise WorkflowOwnershipError(f"{field_name} attribution is malformed")
        kind = value.get("kind")
        if kind == "roster_student":
            raise WorkflowPrerequisiteError(
                f"{field_name} cannot use roster-student identity as operational authority"
            )
        if require_current_use and kind not in _EVENT_OPERATIONAL_KINDS:
            raise WorkflowPrerequisiteError(
                f"current {field_name} requires an identified operational human"
            )
        require_represented_human_authority(
            self.contexts,
            value,
            field_name=field_name,
            require_current_use=require_current_use,
        )

    def require_support_process_operational_participant(
        self,
        work: ExactPortiaWorkRef,
        participant_ref: object,
        *,
        field_name: str,
        allowed_contexts: frozenset[str],
        require_current_use: bool,
    ) -> SupportProcessParticipantPersonResolution:
        """Resolve an exact participant and require an explicit operational context."""
        if (
            work.work_kind != "support_process"
            or work.contract_version != SUPPORT_PROCESS_VERSION
        ):
            raise WorkflowOwnershipError(
                f"{field_name} Support Process participant requires "
                "exact support_process@1 ownership"
            )
        if not isinstance(participant_ref, Mapping):
            raise WorkflowOwnershipError(
                f"{field_name} Support Process Participant reference is malformed"
            )
        record_kind = participant_ref.get("record_kind")
        record_id = participant_ref.get("record_id")
        version = participant_ref.get("contract_version")
        if (
            record_kind != "support_process_participant"
            or not isinstance(record_id, str)
            or not isinstance(version, str)
        ):
            raise WorkflowOwnershipError(
                f"{field_name} must name an exact Support Process Participant"
            )
        reference = support_process_participant_reference(
            work,
            record_id,
            version=version,
        )
        service = self._support_process_participant_service()
        resolution = (
            service.require_current_use(reference)
            if require_current_use
            else service.resolve_exact(reference)
        )
        contexts = resolution.participant.record.field("contexts")
        if not isinstance(contexts, Sequence) or isinstance(
            contexts, (str, bytes)
        ):
            raise WorkflowOwnershipError(
                f"{field_name} Support Process Participant contexts are malformed"
            )
        present = {
            context.get("kind")
            for context in contexts
            if isinstance(context, Mapping)
        }
        if not present.intersection(allowed_contexts):
            allowed = ", ".join(sorted(allowed_contexts))
            raise WorkflowPrerequisiteError(
                f"{field_name} requires Support Process Participant context "
                f"in {{{allowed}}}"
            )
        return resolution
