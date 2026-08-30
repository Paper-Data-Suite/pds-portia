"""Shared exact ownership and authority mechanics for Event-local judgments."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import ClassVar

from portia.models import PortiaRecord
from portia.models.references import (
    ExactActorRef,
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
    RosterStudentRef,
)
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.validation import GraphValidationOptions, validate_record_graph
from portia.workflows.common import WorkflowServiceBase, record_target
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)

JUDGMENT_VERSION = "1"
JUDGMENT_OWNER_VERSION = "2"
JUDGMENT_CONTRACTS = frozenset(
    {"review", "classification", "hypothesis", "determination"}
)
JUDGMENT_TARGET_VERSION = "3"

_WRITE_EVENT_STATUSES = frozenset({"draft", "active", "closed"})
_CURRENT_EVENT_STATUSES = frozenset({"active", "closed"})


def require_judgment_owner(work: ExactPortiaWorkRef) -> None:
    """Require the accepted v0.2 Event owner for Issue #42 judgment records."""
    if work.work_kind != "event" or work.contract_version != JUDGMENT_OWNER_VERSION:
        raise WorkflowOwnershipError(
            "Review/Classification/Hypothesis/Determination workflows require "
            "exact event@2 ownership"
        )


def require_judgment_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    contract: str,
) -> None:
    """Require exact Event-local judgment ownership without path/name guessing."""
    require_judgment_owner(work)
    if record.contract != contract or record.contract_version != JUDGMENT_VERSION:
        raise WorkflowOwnershipError(f"new {contract} writes require {contract}@1 input")
    if record.class_id != work.class_id or record.work_id != work.work_id:
        raise WorkflowOwnershipError(
            f"{contract} does not belong to the explicitly selected Event"
        )


def require_digital_judgment_creation(record: PortiaRecord) -> None:
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type") if isinstance(creation_source, Mapping) else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "v0.2 judgment authoring supports digital_entry only"
        )


def require_judgment_current_materialization(record: PortiaRecord) -> None:
    """Fail closed when v0.2 cannot verify reviewed materialization provenance."""
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type") if isinstance(creation_source, Mapping) else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "current judgment use requires reviewed materialization; "
            "v0.2 supports digital_entry only"
        )


def require_judgment_owner_write_eligibility(owner: PortiaRecord) -> None:
    if owner.contract != "event" or owner.contract_version != JUDGMENT_OWNER_VERSION:
        raise WorkflowOwnershipError("judgment owner must resolve to event@2")
    if owner.status not in _WRITE_EVENT_STATUSES:
        expected = ", ".join(sorted(_WRITE_EVENT_STATUSES))
        raise WorkflowPrerequisiteError(
            f"judgment writes require Event status in {{{expected}}}"
        )


def require_judgment_owner_current_eligibility(owner: PortiaRecord) -> None:
    if owner.contract != "event" or owner.contract_version != JUDGMENT_OWNER_VERSION:
        raise WorkflowOwnershipError("judgment owner must resolve to event@2")
    if owner.status not in _CURRENT_EVENT_STATUSES:
        expected = ", ".join(sorted(_CURRENT_EVENT_STATUSES))
        raise WorkflowPrerequisiteError(
            f"current judgment use requires Event status in {{{expected}}}"
        )


def judgment_target_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Resolve exact Event/Participant targets accepted by judgment@1 records."""
    require_judgment_owner(work)
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("judgment target is malformed")
    kind = target.get("kind")
    if kind == "event":
        return ()
    if kind == "event_participant":
        entries: Sequence[object] = (target,)
    elif kind == "event_participants":
        raw_targets = target.get("targets")
        if not isinstance(raw_targets, tuple):
            raise WorkflowOwnershipError("plural judgment target is malformed")
        entries = raw_targets
    else:
        raise WorkflowOwnershipError("judgment target is not Event-local")

    loaded: list[StoredRecord] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowOwnershipError("judgment target entry is malformed")
        reference = entry.get("record_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("judgment target record reference is malformed")
        kind_value = reference.get("record_kind")
        identifier = reference.get("record_id")
        version = reference.get("contract_version")
        if kind_value != "event_participant" or not isinstance(identifier, str):
            raise WorkflowOwnershipError("judgment target names the wrong record family")
        if version != JUDGMENT_TARGET_VERSION:
            raise WorkflowPrerequisiteError(
                "new/current judgment targeting requires event_participant@3"
            )
        if identifier in seen:
            raise WorkflowOwnershipError(
                "judgment target repeats the same logical Participant identity"
            )
        seen.add(identifier)
        loaded.append(
            repository.load_work_record(
                work, "event_participant", JUDGMENT_TARGET_VERSION, identifier
            )
        )
    return tuple(loaded)


def require_judgment_targets_current_use(
    work: ExactPortiaWorkRef,
    targets: Sequence[StoredRecord],
    *,
    quarantine: QuarantineGuard,
) -> None:
    for target in targets:
        if target.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current judgment target Participant must be active"
            )
        quarantine.require_allowed(
            record_target(work, target.record), "block_current_use"
        )


def require_represented_human_authority(
    contexts: WorkflowContextAssembler,
    value: object,
    *,
    field_name: str,
    require_current_use: bool,
) -> None:
    """Resolve the represented human without conflating it with recorder identity."""
    if not isinstance(value, Mapping):
        raise WorkflowOwnershipError(f"{field_name} attribution is malformed")
    kind = value.get("kind")
    if kind == "roster_student":
        reference = RosterStudentRef.from_dict(value.get("roster_student_ref"))
        contexts.rosters.resolve_reference(reference)
        return
    if kind == "actor":
        actor_ref = value.get("actor_ref")
        actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
        if not isinstance(actor_id, str):
            raise WorkflowOwnershipError(f"{field_name} Actor attribution is malformed")
        contexts.actors.load_actor(
            ExactActorRef(actor_id=actor_id, contract_version="1"),
            require_current_use=require_current_use,
        )
        return
    if kind in {"local_operator", "descriptive_person"}:
        return
    if kind == "unidentified_person":
        if require_current_use:
            raise WorkflowPrerequisiteError(
                f"current {field_name} use requires an identified represented human"
            )
        return
    raise WorkflowOwnershipError(f"unsupported {field_name} attribution kind {kind!r}")


def validate_partial_judgment_graph(
    contexts: WorkflowContextAssembler,
    records: Sequence[PortiaRecord],
) -> None:
    """Run pure application validation while I/O-backed refs are checked separately."""
    authoritative = contexts.assemble(records, require_actor_current_use=False)
    findings = validate_record_graph(
        records,
        context=authoritative.validation,
        options=GraphValidationOptions(require_internal_resolution=False),
    )
    if findings:
        raise WorkflowValidationError(findings)


def judgment_reference(
    work: ExactPortiaWorkRef,
    contract: str,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact Event-local v1 judgment reference."""
    require_judgment_owner(work)
    if contract not in JUDGMENT_CONTRACTS:
        raise WorkflowOwnershipError(f"unsupported judgment contract {contract!r}")
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=contract,
            record_id=record_id,
            contract_version=JUDGMENT_VERSION,
        ),
    )


class JudgmentReadService(WorkflowServiceBase):
    """Strict exact-reader base for one Event-local judgment family."""

    CONTRACT: ClassVar[str]

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        require_judgment_owner(reference.work_ref)
        if reference.record_ref.record_kind != self.CONTRACT:
            raise WorkflowOwnershipError(
                f"reference is not a {self.CONTRACT} judgment record"
            )
        if reference.record_ref.contract_version != JUDGMENT_VERSION:
            raise WorkflowOwnershipError(
                f"unsupported exact {self.CONTRACT} contract version "
                f"{reference.record_ref.contract_version!r}"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            self.CONTRACT,
            JUDGMENT_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        require_judgment_owner(work)
        return self.repository.list_work_records(
            work,
            self.CONTRACT,
            version=JUDGMENT_VERSION,
        )
