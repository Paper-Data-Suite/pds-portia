"""Shared exact ownership and target rules for Account/Observation workflows."""

from __future__ import annotations

from collections.abc import Mapping

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRef
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.common import (
    record_target,
    require_revision_invariants,
    work_target,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

ACCOUNT_VERSION = "2"
OBSERVATION_VERSION = "2"
ACCOUNT_READ_VERSIONS = frozenset({"1", "2"})
OBSERVATION_READ_VERSIONS = frozenset({"1", "2"})


ACCOUNT_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"retracted", "invalidated", "superseded"}),
    "retracted": frozenset({"superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}
OBSERVATION_STATUS_TRANSITIONS = {
    "proposed": frozenset({"active", "invalidated", "superseded"}),
    "active": frozenset({"invalidated", "superseded"}),
    "invalidated": frozenset({"superseded"}),
    "superseded": frozenset(),
}

_EVIDENCE_REVISION_MUTABLE_FIELDS = frozenset({"status", "updated_at", "updated_by"})
_EVIDENCE_OWNER_VERSIONS = {"event": "2", "support_process": "1"}
_TARGET_KINDS = {
    "event": ("event", "event_participant", "event_participants"),
    "support_process": (
        "support_process",
        "support_process_participant",
        "support_process_participants",
    ),
}
_TARGET_RECORD_KINDS = {
    "event": ("event_participant", "3"),
    "support_process": ("support_process_participant", "1"),
}
_WRITE_OWNER_STATUSES = {
    "event": frozenset({"draft", "active", "closed"}),
    "support_process": frozenset({"proposed", "active"}),
}
_CURRENT_OWNER_STATUSES = {
    # Draft Events must be able to assemble active attributed Accounts before
    # Event activation (including reported_involved Role preflight). Closed
    # Events remain legitimate evidence contexts rather than becoming absent.
    "event": frozenset({"draft", "active", "closed"}),
    "support_process": frozenset({"active"}),
}


def require_evidence_owner(work: ExactPortiaWorkRef) -> None:
    expected = _EVIDENCE_OWNER_VERSIONS.get(work.work_kind)
    if expected is None or work.contract_version != expected:
        raise WorkflowOwnershipError(
            "Account/Observation workflows require exact event@2 or support_process@1 ownership"
        )


def require_supported_evidence_version(
    work: ExactPortiaWorkRef,
    *,
    contract: str,
    version: str,
    supported_versions: frozenset[str],
) -> None:
    require_evidence_owner(work)
    if version not in supported_versions:
        raise WorkflowOwnershipError(
            f"unsupported exact {contract} contract version {version!r}"
        )
    if version == "1" and work.work_kind != "event":
        raise WorkflowOwnershipError(
            f"{contract}@1 is Event-local and cannot use support_process ownership"
        )


def require_evidence_record_owner(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    contract: str,
) -> None:
    """Require exact work/record ownership without guessing from paths or names."""
    require_evidence_owner(work)
    if record.contract != contract:
        raise WorkflowOwnershipError(f"record is not {contract} evidence")
    if record.class_id != work.class_id or record.work_id != work.work_id:
        raise WorkflowOwnershipError(
            f"{contract} does not belong to the explicitly selected Portia work"
        )
    if record.contract_version == "1":
        if work.work_kind != "event":
            raise WorkflowOwnershipError(f"{contract}@1 is Event-local")
        return
    if record.contract_version == "2" and record.work_kind != work.work_kind:
        raise WorkflowOwnershipError(
            f"{contract}@2 work_kind does not agree with exact work ownership"
        )


def require_digital_entry_creation(record: PortiaRecord) -> None:
    creation_source = record.field("creation_source")
    source_type = (
        creation_source.get("type") if isinstance(creation_source, Mapping) else None
    )
    if source_type != "digital_entry":
        raise WorkflowPrerequisiteError(
            "v0.2 Account/Observation creation supports digital_entry only"
        )


def require_basic_evidence_shape(
    record: PortiaRecord,
    *,
    allow_related_accounts: bool = False,
    allow_supersedes: bool = False,
    allow_source_artifacts: bool = False,
) -> None:
    """Fail closed on evidence features not yet owned by the caller."""
    fields: list[str] = []
    if not allow_source_artifacts:
        fields.append("source_artifacts")
    if not allow_supersedes:
        fields.insert(0, "supersedes")
    if not allow_related_accounts:
        fields.insert(0, "related_accounts")
    for field in fields:
        if record.field(field) is not None:
            raise WorkflowPrerequisiteError(
                f"{field} is handled by a later Issue #41 evidence-history slice"
            )


def require_owner_write_eligibility(
    work: ExactPortiaWorkRef, owner: PortiaRecord
) -> None:
    allowed = _WRITE_OWNER_STATUSES[work.work_kind]
    if owner.status not in allowed:
        expected = ", ".join(sorted(allowed))
        raise WorkflowPrerequisiteError(
            f"evidence writes require {work.work_kind} status in {{{expected}}}"
        )


def require_owner_current_eligibility(
    work: ExactPortiaWorkRef, owner: PortiaRecord
) -> None:
    allowed = _CURRENT_OWNER_STATUSES[work.work_kind]
    if owner.status not in allowed:
        expected = ", ".join(sorted(allowed))
        raise WorkflowPrerequisiteError(
            f"current evidence use requires {work.work_kind} status in {{{expected}}}"
        )


def evidence_target_records(
    repository: PortiaRepository,
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
) -> tuple[StoredRecord, ...]:
    """Resolve every exact owner-local Participant target for one evidence record."""
    target = record.field("target")
    if not isinstance(target, Mapping):
        raise WorkflowOwnershipError("evidence target is malformed")
    kinds = _TARGET_KINDS[work.work_kind]
    target_kind = target.get("kind")
    if target_kind not in kinds:
        raise WorkflowOwnershipError(
            "evidence target family does not agree with exact work ownership"
        )
    if target_kind == kinds[0]:
        return ()

    entries: tuple[object, ...]
    if target_kind == kinds[1]:
        entries = (target,)
    else:
        raw_targets = target.get("targets")
        if not isinstance(raw_targets, tuple):
            raise WorkflowOwnershipError("plural evidence target is malformed")
        entries = tuple(raw_targets)

    expected_kind, current_version = _TARGET_RECORD_KINDS[work.work_kind]
    loaded: list[StoredRecord] = []
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise WorkflowOwnershipError("evidence target entry is malformed")
        reference = entry.get("record_ref")
        if not isinstance(reference, Mapping):
            raise WorkflowOwnershipError("evidence target record reference is malformed")
        record_kind = reference.get("record_kind")
        record_id = reference.get("record_id")
        version = reference.get("contract_version")
        if record_kind != expected_kind or not isinstance(record_id, str):
            raise WorkflowOwnershipError("evidence target names the wrong record family")
        if not isinstance(version, str):
            raise WorkflowOwnershipError(
                "production evidence targeting requires an exact contract version"
            )
        if version != current_version:
            raise WorkflowPrerequisiteError(
                f"new/current evidence targeting requires {expected_kind}@{current_version}"
            )
        if record_id in seen:
            raise WorkflowOwnershipError(
                "evidence target repeats the same logical Participant identity"
            )
        seen.add(record_id)
        loaded.append(
            repository.load_work_record(work, expected_kind, version, record_id)
        )
    return tuple(loaded)


def require_targets_current_use(
    work: ExactPortiaWorkRef,
    targets: tuple[StoredRecord, ...],
    *,
    quarantine: QuarantineGuard,
) -> None:
    """Require exact target Participants to remain active/current-use eligible."""
    for stored in targets:
        if stored.record.status != "active":
            raise WorkflowPrerequisiteError(
                "current evidence target Participant must be active"
            )
        quarantine.require_allowed(
            record_target(work, stored.record), "block_current_use"
        )


def require_work_current_use_quarantine(
    work: ExactPortiaWorkRef,
    record: PortiaRecord,
    *,
    quarantine: QuarantineGuard,
) -> None:
    quarantine.require_allowed(work_target(work), "block_current_use")
    quarantine.require_allowed(record_target(work, record), "block_current_use")


def require_evidence_revision_invariants(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Reject ordinary in-place evidence edits while enforcing lifecycle legality."""
    if prior.contract == "account":
        transitions = ACCOUNT_STATUS_TRANSITIONS
    elif prior.contract == "observation":
        transitions = OBSERVATION_STATUS_TRANSITIONS
    else:
        raise WorkflowOwnershipError(
            "evidence revision invariants require Account or Observation records"
        )
    require_revision_invariants(prior, candidate, transitions=transitions)
    prior_data = prior.to_dict()
    candidate_data = candidate.to_dict()
    comparable_fields = set(prior_data) | set(candidate_data)
    for field in sorted(comparable_fields - _EVIDENCE_REVISION_MUTABLE_FIELDS):
        if prior_data.get(field) != candidate_data.get(field):
            raise WorkflowPrerequisiteError(
                f"ordinary {prior.contract} replacement cannot rewrite evidence field {field}"
            )


def require_coordinated_evidence_transition(
    prior: PortiaRecord,
    candidate: PortiaRecord,
) -> None:
    """Require a real status change suitable for later lifecycle coordination."""
    require_evidence_revision_invariants(prior, candidate)
    if prior.status == candidate.status:
        raise WorkflowPrerequisiteError(
            "lifecycle transition coordination requires a status change"
        )
