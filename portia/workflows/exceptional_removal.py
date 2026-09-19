"""Bounded production workflow for exact Exceptional Removal."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast

from portia.identity.actors import ActorDirectoryService
from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactActorContactPointRef,
    ExactActorRef,
    ExactActorRosterStudentCollisionRef,
    ExactActorStudentRelationshipRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.canonical_removal import (
    AbsenceObservation,
    CanonicalRemovalRequest,
    CanonicalRemovalStore,
    _issue_removal_capability,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.integrity import expected_target_relative_path
from portia.storage.io import exact_delete, read_bytes, read_json
from portia.storage.locks import HeldLock, LockStore, derive_lock_id
from portia.storage.paths import (
    actor_directory_removal_path,
    exceptional_removal_path,
    operation_root,
    portia_root,
    resolve_workspace_relative,
    workspace_relative,
)
from portia.storage.quarantine import QuarantineGuard, quarantine_applies
from portia.storage.recovery import OperationRecovery
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore, QuarantineStore, SeriesState
from portia.storage.staging import ensure_runtime_containment
from portia.workflows.errors import WorkflowOwnershipError, WorkflowPrerequisiteError
from portia.workflows.quarantine import QuarantineWorkflowService

FaultHook = Callable[[str, str | None], None]
Entropy = Callable[[int], bytes]
Clock = Callable[[], str]
GovernanceState = Literal["clear", "blocked", "unknown"]

_GENERIC_CATEGORIES = frozenset(
    {
        "legal_requirement",
        "privacy_requirement",
        "security_containment",
        "administrative_test_data",
        "unrecoverable_corruption",
        "other",
    }
)
_ACTOR_GROUNDS = frozenset(
    {
        "prohibited_sensitive_payload",
        "synthetic_or_test_record",
        "unrecoverable_corruption",
        "binding_legal_or_administrative_requirement",
        "other_exceptional_ground",
    }
)
_ORDINARY_RATIONALES = frozenset(
    {
        "incorrect",
        "duplicate",
        "duplicated",
        "disputed",
        "withdrawn",
        "invalidated",
        "superseded",
        "embarrassing",
        "old",
        "inconvenient",
        "closed",
        "unwanted",
        "mis_owned",
        "ownership_error",
    }
)
_CHILD_DISPOSITIONS = frozenset(
    {"retained", "exceptionally_removed", "superseded", "invalidated", "review_required"}
)
_DEPENDENCY_DISPOSITIONS = frozenset(
    {"corrected", "historical_only", "unsatisfied_manual_review", "advisory_reviewed"}
)
_RETAINABLE_WORK_AUDIT_KINDS = frozenset(
    {
        "amendment",
        "dependency",
        "lifecycle_transition",
        "ownership_correction",
        "record_migration",
        "statement_of_disagreement",
        "work_migration",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _explicit_timestamp(value: str) -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError("removal timestamp is invalid") from exc
    if parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError("removal timestamp requires an explicit offset")
    return parsed


def _portable_relative_path(value: str) -> str:
    """Normalize a relative path for bounded, platform-neutral comparisons."""
    return "/".join(value.split("\\"))


def _safe_text(value: object, description: str, *, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkflowPrerequisiteError(f"{description} must be non-empty text")
    if len(value) > maximum or any(character in value for character in "\r\n\x00"):
        raise WorkflowPrerequisiteError(f"{description} is not bounded one-line text")
    lowered = value.lower()
    if "@" in value or ":\\" in value or ":/" in value or lowered.startswith(("/", "\\\\")):
        raise WorkflowPrerequisiteError(f"{description} contains sensitive or path-like data")
    return value


@dataclass(frozen=True, slots=True)
class ExceptionalRemovalAuthority:
    """Application-local capability configuration, never institutional RBAC."""

    enabled: bool
    governance_state: GovernanceState
    allowed_generic_categories: frozenset[str] = _GENERIC_CATEGORIES
    allowed_actor_grounds: frozenset[str] = _ACTOR_GROUNDS

    def require_generic(
        self,
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        *,
        synthetic_test_data_confirmed: bool,
        recovery_disposition: str | None,
    ) -> None:
        self._require_common(authorization)
        category = reason.get("category")
        code = reason.get("code")
        if category not in self.allowed_generic_categories or category not in _GENERIC_CATEGORIES:
            raise WorkflowPrerequisiteError("Exceptional Removal category is not configured")
        if not isinstance(code, str) or code in _ORDINARY_RATIONALES:
            raise WorkflowPrerequisiteError("ordinary correction/lifecycle rationale cannot remove")
        if category == "administrative_test_data" and not synthetic_test_data_confirmed:
            raise WorkflowPrerequisiteError("test-data removal requires positive synthetic evidence")
        if category == "unrecoverable_corruption" and recovery_disposition != "unrecoverable":
            raise WorkflowPrerequisiteError(
                "corruption removal requires exact unrecoverable recovery evidence"
            )
        if category == "other":
            _safe_text(reason.get("detail"), "other removal detail")

    def require_actor(
        self,
        ground: Mapping[str, object],
        authorization: Mapping[str, object],
        *,
        synthetic_test_data_confirmed: bool,
        recovery_disposition: str | None,
    ) -> None:
        self._require_common(authorization)
        code = ground.get("code")
        if code not in self.allowed_actor_grounds or code not in _ACTOR_GROUNDS:
            raise WorkflowPrerequisiteError("Actor Exceptional Removal ground is not configured")
        if code == "synthetic_or_test_record" and not synthetic_test_data_confirmed:
            raise WorkflowPrerequisiteError("Actor test removal requires positive synthetic evidence")
        if code == "unrecoverable_corruption" and recovery_disposition != "unrecoverable":
            raise WorkflowPrerequisiteError(
                "Actor corruption removal requires unrecoverable recovery evidence"
            )
        if code == "other_exceptional_ground":
            _safe_text(ground.get("detail"), "other Actor removal detail")

    def _require_common(self, authorization: Mapping[str, object]) -> None:
        if not self.enabled:
            raise WorkflowPrerequisiteError("Exceptional Removal capability is not configured")
        if self.governance_state != "clear":
            raise WorkflowPrerequisiteError(
                "Exceptional Removal governance clearance is not known clear"
            )
        _safe_text(authorization.get("decision_reference"), "external decision reference")
        actor = authorization.get("authorized_by")
        if not isinstance(actor, Mapping) or actor.get("type") != "local_operator":
            raise WorkflowPrerequisiteError(
                "local-operator attribution alone is insufficient without configured capability"
            )
        _safe_text(actor.get("display_label"), "local operator label", maximum=200)


@dataclass(frozen=True, slots=True)
class RemovalChild:
    relative_path: str
    target: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class RemovalAssessment:
    target: Mapping[str, object]
    stored: StoredRecord
    canonical_bytes: bytes
    relative_path: str
    incoming_references: tuple[str, ...]
    dependencies: tuple[str, ...]
    children: tuple[RemovalChild, ...]
    lifecycle_snapshot: Mapping[str, object] | None
    integrity_clearance: str
    managed_payload_copies: tuple[str, ...]
    active_quarantines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExceptionalRemovalResolution:
    target: Mapping[str, object]
    disposition: Literal["present", "exceptionally_removed"]
    stored: StoredRecord | None
    certificate: StoredRecord | None


@dataclass(frozen=True, slots=True)
class ExceptionalRemovalResult:
    operation: SeriesState
    certificate: StoredRecord
    quarantine: SeriesState
    resolution: ExceptionalRemovalResolution
    observation: AbsenceObservation


def _contains_exact(value: object, needle: object) -> bool:
    if value == needle:
        return True
    if isinstance(value, Mapping):
        return any(_contains_exact(child, needle) for child in value.values())
    if isinstance(value, list):
        return any(_contains_exact(child, needle) for child in value)
    return False


def _target_reference_needles(target: Mapping[str, object]) -> tuple[object, ...]:
    kind = target.get("kind")
    if kind == "work":
        return (target.get("work_ref"),)
    if kind == "work_record":
        composite = target.get("work_record_ref")
        if isinstance(composite, Mapping):
            return (dict(composite),)
    if kind == "actor_directory_record":
        reference = target.get("actor_directory_record_ref")
        if isinstance(reference, Mapping):
            fields = {
                "actor": "actor_ref",
                "actor_contact_point": "contact_point_ref",
                "actor_student_relationship": "relationship_ref",
                "actor_roster_student_collision": "collision_ref",
            }
            field = fields.get(str(reference.get("kind")))
            if field is not None:
                return (reference.get(field),)
    raise WorkflowOwnershipError("unsupported exact Exceptional Removal target")


def _canonical_candidates(root: Path) -> tuple[Path, ...]:
    candidates: list[Path] = []
    classes = root / "classes"
    if classes.exists():
        if not classes.is_dir() or classes.is_symlink():
            raise PortiaCorruptionError("workspace classes root is unsafe")
        for class_root in sorted(classes.iterdir(), key=lambda item: item.name):
            work_root = class_root / "modules" / "portia" / "work"
            if not work_root.exists():
                continue
            if not work_root.is_dir() or work_root.is_symlink():
                raise PortiaCorruptionError("Portia work collection is unsafe")
            for work in sorted(work_root.iterdir(), key=lambda item: item.name):
                if not work.is_dir() or work.is_symlink():
                    raise PortiaCorruptionError("Portia work collection has unsafe member")
                manifest = work / "work.json"
                if manifest.exists():
                    candidates.append(manifest)
                records = work / "records"
                if records.exists():
                    for path in sorted(records.glob("*/*.json")):
                        candidates.append(path)
    actors = portia_root(root) / "actors"
    if actors.exists():
        if not actors.is_dir() or actors.is_symlink():
            raise PortiaCorruptionError("Actor Directory root is unsafe")
        for actor in sorted(actors.iterdir(), key=lambda item: item.name):
            if not actor.is_dir() or actor.is_symlink():
                raise PortiaCorruptionError("Actor Directory has unsafe member")
            root_record = actor / "actor.json"
            if root_record.exists():
                candidates.append(root_record)
            records = actor / "records"
            if records.exists():
                candidates.extend(sorted(records.glob("*/*.json")))
    for path in candidates:
        ensure_runtime_containment(root, path)
        if path.is_symlink() or not path.is_file():
            raise PortiaCorruptionError("canonical reference scan encountered unsafe artifact")
    return tuple(candidates)


def _actor_ids(value: object) -> frozenset[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        actor_id = value.get("actor_id")
        if isinstance(actor_id, str):
            found.add(actor_id)
        for child in value.values():
            found.update(_actor_ids(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_actor_ids(child))
    return frozenset(found)


def _actor_reference(
    target: Mapping[str, object],
) -> (
    ExactActorRef
    | ExactActorContactPointRef
    | ExactActorStudentRelationshipRef
    | ExactActorRosterStudentCollisionRef
):
    wrapper = target.get("actor_directory_record_ref")
    if not isinstance(wrapper, Mapping):
        raise WorkflowOwnershipError("Actor removal target is malformed")
    kind = wrapper.get("kind")
    if kind == "actor":
        return ExactActorRef.from_dict(wrapper.get("actor_ref"))
    if kind == "actor_contact_point":
        return ExactActorContactPointRef.from_dict(wrapper.get("contact_point_ref"))
    if kind == "actor_student_relationship":
        return ExactActorStudentRelationshipRef.from_dict(wrapper.get("relationship_ref"))
    if kind == "actor_roster_student_collision":
        return ExactActorRosterStudentCollisionRef.from_dict(wrapper.get("collision_ref"))
    raise WorkflowOwnershipError("unsupported Actor Directory removal target")


class ExceptionalRemovalWorkflowService:
    """Bounded authority for generic and Actor Directory Exceptional Removal."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        authority: ExceptionalRemovalAuthority,
        entropy: Entropy = secrets.token_bytes,
        clock: Clock = _utc_now,
    ) -> None:
        self.root = Path(workspace_root).resolve(strict=False)
        self.authority = authority
        self.entropy = entropy
        self.clock = clock
        self.repository = PortiaRepository(self.root)
        self.actors = ActorDirectoryService(self.root)
        self.operations = OperationJournalStore(self.root)
        self.locks = LockStore(self.root)
        self.remover = CanonicalRemovalStore(self.root, clock=clock)
        self.quarantines = QuarantineWorkflowService(self.root)

    def _load_target(self, target: Mapping[str, object]) -> StoredRecord:
        kind = target.get("kind")
        if kind == "work":
            work_reference = ExactPortiaWorkRef.from_dict(target.get("work_ref"))
            if work_reference.module_id != "portia":
                raise WorkflowOwnershipError("Exceptional Removal supports only Portia work")
            return self.repository.load_work(work_reference)
        if kind == "work_record":
            record_reference = ExactPortiaWorkRecordRef.from_dict(
                target.get("work_record_ref")
            )
            if record_reference.work_ref.module_id != "portia":
                raise WorkflowOwnershipError("Exceptional Removal supports only Portia records")
            if record_reference.record_ref.record_kind == "exceptional_removal":
                raise WorkflowOwnershipError("removal certificates cannot be removal targets")
            return self.repository.load_work_record(
                record_reference.work_ref,
                record_reference.record_ref.record_kind,
                record_reference.record_ref.contract_version,
                record_reference.record_ref.record_id,
            )
        if kind == "actor_directory_record":
            reference = _actor_reference(target)
            if isinstance(reference, ExactActorRef):
                resolution = self.actors.resolve_actor(reference)
            else:
                resolution = self.actors.resolve_actor_child(reference)
            if resolution.stored is None:
                raise PortiaNotFoundError(
                    "exact Actor Directory payload has been exceptionally removed"
                )
            return resolution.stored
        raise WorkflowOwnershipError("unsupported Exceptional Removal target")

    def _matching_certificates(
        self,
        target: Mapping[str, object],
    ) -> tuple[StoredRecord, ...]:
        kind = target.get("kind")
        if kind in {"work", "work_record"}:
            work_wire = (
                target.get("work_ref")
                if kind == "work"
                else cast(Mapping[str, object], target.get("work_record_ref")).get("work_ref")
            )
            if not isinstance(work_wire, Mapping):
                raise WorkflowOwnershipError("removal target lacks exact work scope")
            class_id = work_wire.get("class_id")
            if not isinstance(class_id, str):
                raise WorkflowOwnershipError("removal target lacks exact class scope")
            return tuple(
                item
                for item in self.repository.list_exceptional_removals(class_id)
                if item.record.field("target") == dict(target)
            )
        exact = target.get("actor_directory_record_ref")
        return tuple(
            item
            for item in self.actors.list_exceptional_removals()
            if item.record.field("target") == exact
        )

    def resolve_removal_state(
        self,
        target: Mapping[str, object],
    ) -> ExceptionalRemovalResolution:
        matches = self._matching_certificates(target)
        if len(matches) > 1:
            raise PortiaCorruptionError(
                "multiple removal certificates identify one exact representation"
            )
        try:
            stored = self._load_target(target)
        except PortiaNotFoundError:
            if not matches:
                raise
            return ExceptionalRemovalResolution(
                dict(target), "exceptionally_removed", None, matches[0]
            )
        if matches:
            raise PortiaRecoveryRequiredError(
                "canonical payload and its removal certificate both exist"
            )
        return ExceptionalRemovalResolution(dict(target), "present", stored, None)

    def require_current_use(self, target: Mapping[str, object]) -> StoredRecord:
        resolution = self.resolve_removal_state(target)
        if resolution.disposition == "exceptionally_removed":
            raise PortiaRecoveryRequiredError(
                "requested exact representation was exceptionally removed"
            )
        assert resolution.stored is not None
        return resolution.stored

    def _operation_quarantine(
        self,
        operation_id: str,
        target: Mapping[str, object],
    ) -> SeriesState:
        matches: list[str] = []
        for record in QuarantineGuard(self.root).active_records():
            data = record.to_dict()
            origin = data.get("origin")
            applying = origin.get("applying_operation") if isinstance(origin, Mapping) else None
            if (
                isinstance(applying, Mapping)
                and applying.get("operation_id") == operation_id
                and data.get("target") == dict(target)
            ):
                quarantine_id = data.get("quarantine_id")
                if isinstance(quarantine_id, str):
                    matches.append(quarantine_id)
        if len(matches) != 1:
            raise PortiaRecoveryRequiredError(
                "removal recovery requires one exact active operation Quarantine"
            )
        return QuarantineStore(self.root).load_current(matches[0])

    def _journal_certificate(
        self,
        data: Mapping[str, object],
        target: Mapping[str, object],
    ) -> StoredRecord | None:
        steps = data.get("write_set")
        if not isinstance(steps, list) or len(steps) != 2:
            raise PortiaCorruptionError("removal recovery write set is malformed")
        certificate_step = steps[0]
        if not isinstance(certificate_step, Mapping):
            raise PortiaCorruptionError("removal recovery certificate step is malformed")
        relative = certificate_step.get("destination_path")
        intended = certificate_step.get("intended_result")
        if not isinstance(relative, str) or not isinstance(intended, Mapping):
            raise PortiaCorruptionError("removal recovery certificate evidence is malformed")
        path = resolve_workspace_relative(self.root, relative)
        try:
            value, _content, fingerprint = read_json(path)
        except PortiaNotFoundError:
            return None
        expected = intended.get("fingerprint")
        if fingerprint.to_dict() != expected:
            raise PortiaConflictError("removal certificate differs from journal intent")
        contract = (
            "actor_directory_exceptional_removal"
            if target.get("kind") == "actor_directory_record"
            else "exceptional_removal"
        )
        try:
            record = parse_portia_record(contract, "1", value)
        except Exception as exc:
            raise PortiaCorruptionError("removal recovery certificate is invalid") from exc
        stored = StoredRecord(record, path, fingerprint)
        matches = self._matching_certificates(target)
        if len(matches) != 1 or matches[0].fingerprint != fingerprint:
            raise PortiaRecoveryRequiredError(
                "removal recovery certificate does not uniquely identify the target"
            )
        return stored

    def recover_operation(
        self,
        operation_id: str,
        *,
        synthetic_test_data_confirmed: bool = False,
        recovery_disposition: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> ExceptionalRemovalResult:
        """Resume one exact partial removal using accepted recovery evidence."""
        recovery = OperationRecovery(self.root).assess(operation_id)
        if recovery.disposition in {
            "absent",
            "manual_review",
            "restore_pointer_candidate",
        }:
            raise PortiaRecoveryRequiredError(
                "removal operation series is not exactly selected for safe recovery"
            )
        operation = self.operations.load_current(operation_id)
        data = operation.revision.to_dict()
        if (
            operation.revision.contract_version != "3"
            or data.get("operation_kind") != "exceptionally_remove"
        ):
            raise WorkflowOwnershipError(
                "recover_operation supports only operation_journal@3 Exceptional Removal"
            )
        target = data.get("primary_target")
        if not isinstance(target, Mapping):
            raise PortiaCorruptionError("removal operation has no exact primary target")
        certificate = self._journal_certificate(data, target)
        if certificate is None:
            try:
                self._load_target(target)
            except PortiaNotFoundError as exc:
                raise PortiaRecoveryRequiredError(
                    "payload absence without a durable certificate is not removal success"
                ) from exc
            raise PortiaRecoveryRequiredError(
                "certificate-absent removal requires explicit retry or abort with original input"
            )
        certificate_data = certificate.record.to_dict()
        reason_field = (
            "ground" if target.get("kind") == "actor_directory_record" else "reason"
        )
        reason = certificate_data.get(reason_field)
        authorization = certificate_data.get("authorization")
        if not isinstance(reason, Mapping) or not isinstance(authorization, Mapping):
            raise PortiaCorruptionError("removal certificate authority evidence is malformed")
        if target.get("kind") == "actor_directory_record":
            self.authority.require_actor(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        else:
            self.authority.require_generic(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        quarantine = self._operation_quarantine(operation_id, target)
        steps = data.get("write_set")
        assert isinstance(steps, list)
        certificate_step = cast(Mapping[str, object], steps[0])
        removal_step = cast(Mapping[str, object], steps[1])
        timestamp = self.clock()
        _explicit_timestamp(timestamp)
        if certificate_step.get("disposition") == "pending":
            operation = self._append_certificate_accepted(
                operation, certificate, quarantine, timestamp
            )
            data = operation.revision.to_dict()
            recovered_steps = cast(list[Mapping[str, object]], data["write_set"])
            removal_step = recovered_steps[1]
        elif certificate_step.get("disposition") != "accepted":
            raise PortiaRecoveryRequiredError(
                "removal certificate journal disposition is not recoverable"
            )

        removal_disposition = removal_step.get("disposition")
        if data.get("state") == "completed":
            resolution = self.resolve_removal_state(target)
            assert resolution.certificate is not None
            return ExceptionalRemovalResult(
                operation,
                resolution.certificate,
                quarantine,
                resolution,
                AbsenceObservation(
                    cast(str, removal_step["destination_path"]),
                    timestamp,
                    True,
                ),
            )
        if removal_disposition == "accepted":
            try:
                self._load_target(target)
            except PortiaNotFoundError:
                pass
            else:
                raise PortiaRecoveryRequiredError(
                    "accepted removal absence contradicts a present canonical payload"
                )
            observation = AbsenceObservation(
                cast(str, removal_step["destination_path"]), timestamp, True
            )
        elif removal_disposition == "verified":
            try:
                self._load_target(target)
            except PortiaNotFoundError:
                pass
            else:
                raise PortiaRecoveryRequiredError(
                    "verified removal absence contradicts a present canonical payload"
                )
            observed = removal_step.get("observed_result")
            observed_at = observed.get("observed_at") if isinstance(observed, Mapping) else None
            observation = AbsenceObservation(
                cast(str, removal_step["destination_path"]),
                observed_at if isinstance(observed_at, str) else timestamp,
                True,
            )
        elif removal_disposition == "pending":
            capability = _issue_removal_capability(
                cast(str, authorization["decision_reference"]),
                cast(Mapping[str, object], authorization["authorized_by"]),
            )
            quarantine_data = quarantine.revision.to_dict()
            observation = self.remover.remove(
                CanonicalRemovalRequest(
                    target=target,
                    operation_id=operation_id,
                    journal_revision=cast(int, data["journal_revision"]),
                    step_id="step_remove_canonical_payload",
                    quarantine_id=cast(str, quarantine_data["quarantine_id"]),
                ),
                capability=capability,
            )
            operation = self._append_absence_verified(operation, observation, timestamp)
            if fault_hook is not None:
                fault_hook("after_recovery_absence_journaled", None)
        else:
            raise PortiaRecoveryRequiredError(
                "removal step journal disposition is not safely recoverable"
            )
        prior = removal_step.get("precondition")
        prior_fingerprint = prior.get("fingerprint") if isinstance(prior, Mapping) else None
        if not isinstance(prior_fingerprint, Mapping):
            raise PortiaCorruptionError("removal recovery lacks exact prior fingerprint")
        self._purge_managed_copies_from_journal(target, prior_fingerprint)
        if fault_hook is not None:
            fault_hook("after_recovery_purge", None)
        operation = self._append_completed(operation, observation, timestamp)
        resolution = self.resolve_removal_state(target)
        return ExceptionalRemovalResult(
            operation,
            certificate,
            quarantine,
            resolution,
            observation,
        )

    def _incoming_references(
        self,
        target: Mapping[str, object],
        target_path: Path,
    ) -> tuple[str, ...]:
        needles = _target_reference_needles(target)
        excluded_root = target_path.parent if target.get("kind") in {"work", "actor_directory_record"} else None
        found: list[str] = []
        for path in _canonical_candidates(self.root):
            if path == target_path:
                continue
            if target.get("kind") == "work" and excluded_root is not None:
                try:
                    path.relative_to(excluded_root)
                    continue
                except ValueError:
                    pass
            if target.get("kind") == "actor_directory_record":
                wrapper = target.get("actor_directory_record_ref")
                if isinstance(wrapper, Mapping) and wrapper.get("kind") == "actor":
                    actor_root = target_path.parent
                    try:
                        path.relative_to(actor_root)
                        continue
                    except ValueError:
                        pass
            value, _content, _fingerprint = read_json(path)
            if any(needle is not None and _contains_exact(value, needle) for needle in needles):
                found.append(workspace_relative(self.root, path))
        return tuple(sorted(found))

    def _active_quarantines(
        self,
        target: Mapping[str, object],
    ) -> tuple[str, ...]:
        matches: list[str] = []
        for record in QuarantineGuard(self.root).active_records():
            data = record.to_dict()
            if quarantine_applies(data.get("target"), target):
                quarantine_id = data.get("quarantine_id")
                if isinstance(quarantine_id, str):
                    matches.append(quarantine_id)
        return tuple(sorted(matches))

    @staticmethod
    def _targets_overlap(left: object, right: object) -> bool:
        if left == right:
            return True
        if quarantine_applies(left, right) or quarantine_applies(right, left):
            return True
        left_actor_ids = _actor_ids(left)
        right_actor_ids = _actor_ids(right)
        return bool(left_actor_ids and left_actor_ids.intersection(right_actor_ids))

    def _require_no_active_operation_conflict(
        self,
        target: Mapping[str, object],
    ) -> None:
        operations = portia_root(self.root) / "operations"
        if not operations.exists():
            return
        if not operations.is_dir() or operations.is_symlink():
            raise PortiaCorruptionError("operation collection is unsafe")
        terminal = {"completed", "compensated", "aborted"}
        for child in sorted(operations.iterdir(), key=lambda path: path.name):
            if child != operation_root(self.root, child.name):
                raise PortiaCorruptionError("operation collection member is not canonical")
            try:
                current = self.operations.load_current(child.name)
            except Exception as exc:
                raise PortiaRecoveryRequiredError(
                    f"operation series requires recovery before removal: {child.name}"
                ) from exc
            data = current.revision.to_dict()
            if data.get("state") in terminal:
                continue
            related: list[object] = [data.get("primary_target")]
            affected = data.get("affected_targets")
            if isinstance(affected, list):
                related.extend(affected)
            steps = data.get("write_set")
            if isinstance(steps, list):
                related.extend(
                    step.get("target")
                    for step in steps
                    if isinstance(step, Mapping)
                )
            if any(self._targets_overlap(candidate, target) for candidate in related):
                raise PortiaRecoveryRequiredError(
                    f"active operation {child.name!r} overlaps the removal target"
                )

    def _managed_payload_copy_paths(
        self,
        stored: StoredRecord,
        content: bytes,
    ) -> tuple[str, ...]:
        target_value = stored.record.to_dict()
        found: list[str] = []
        for path in self._managed_copy_candidates(stored.path):
            candidate = read_bytes(path)
            contains = candidate == content
            if not contains:
                try:
                    contains = _contains_exact(
                        json.loads(candidate.decode("utf-8")), target_value
                    )
                except (UnicodeDecodeError, json.JSONDecodeError):
                    contains = False
            if contains:
                found.append(workspace_relative(self.root, path))
        return tuple(sorted(found))

    def _child_inventory(
        self,
        target: Mapping[str, object],
        stored: StoredRecord,
    ) -> tuple[RemovalChild, ...]:
        children: list[RemovalChild] = []
        if target.get("kind") == "work":
            records_root = stored.path.parent / "records"
            if not records_root.exists():
                return ()
            for path in sorted(records_root.glob("*/*.json")):
                value, _content, _fp = read_json(path)
                if not isinstance(value, Mapping):
                    raise PortiaCorruptionError("work child is not a JSON object")
                record_kind = value.get("record_type")
                record_id = path.stem
                version = value.get("schema_version")
                work_ref = target.get("work_ref")
                if not all(isinstance(item, str) for item in (record_kind, record_id, version)):
                    raise PortiaCorruptionError("work child lacks exact identity")
                children.append(
                    RemovalChild(
                        workspace_relative(self.root, path),
                        {
                            "kind": "work_record",
                            "work_record_ref": {
                                "work_ref": deepcopy(work_ref),
                                "record_ref": {
                                    "record_kind": record_kind,
                                    "record_id": record_id,
                                    "contract_version": version,
                                },
                            },
                        },
                    )
                )
        elif target.get("kind") == "actor_directory_record":
            wrapper = target.get("actor_directory_record_ref")
            if isinstance(wrapper, Mapping) and wrapper.get("kind") == "actor":
                records_root = stored.path.parent / "records"
                if not records_root.exists():
                    return ()
                actor_ref = wrapper.get("actor_ref")
                actor_id = actor_ref.get("actor_id") if isinstance(actor_ref, Mapping) else None
                for path in sorted(records_root.glob("*/*.json")):
                    value, _content, _fp = read_json(path)
                    if not isinstance(value, Mapping) or not isinstance(actor_id, str):
                        raise PortiaCorruptionError("Actor child inventory is malformed")
                    kind = value.get("record_type")
                    version = value.get("schema_version")
                    fields = {
                        "actor_contact_point": ("contact_point_ref", "contact_point_id"),
                        "actor_student_relationship": ("relationship_ref", "relationship_id"),
                        "actor_roster_student_collision": ("collision_ref", "collision_id"),
                    }
                    if kind not in fields or not isinstance(version, str):
                        raise PortiaCorruptionError("unsupported Actor child inventory member")
                    reference_field, id_field = fields[str(kind)]
                    children.append(
                        RemovalChild(
                            workspace_relative(self.root, path),
                            {
                                "kind": "actor_directory_record",
                                "actor_directory_record_ref": {
                                    "kind": kind,
                                    reference_field: {
                                        "actor_id": actor_id,
                                        id_field: path.stem,
                                        "contract_version": version,
                                    },
                                },
                            },
                        )
                    )
        return tuple(children)

    def assess_removal(
        self,
        *,
        target: Mapping[str, object],
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        integrity_clearance: str = "unknown",
        synthetic_test_data_confirmed: bool = False,
        recovery_disposition: str | None = None,
    ) -> RemovalAssessment:
        if integrity_clearance != "clear":
            raise WorkflowPrerequisiteError("current Integrity state is not known clear")
        if target.get("kind") == "actor_directory_record":
            self.authority.require_actor(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        else:
            self.authority.require_generic(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        if self._matching_certificates(target):
            return self._assessment_from_resolution(target, integrity_clearance)
        self._require_no_active_operation_conflict(target)
        active_quarantines = self._active_quarantines(target)
        if active_quarantines:
            raise PortiaRecoveryRequiredError(
                "an existing active Quarantine must be explicitly reconciled before removal"
            )
        stored = self._load_target(target)
        content = read_bytes(stored.path)
        if fingerprint_bytes(content) != stored.fingerprint:
            raise PortiaConflictError("canonical bytes changed during removal assessment")
        relative = expected_target_relative_path(self.root, dict(target))
        if relative is None or resolve_workspace_relative(self.root, relative) != stored.path:
            raise WorkflowOwnershipError("target path is not identity-derived")
        incoming = self._incoming_references(target, stored.path)
        dependencies = tuple(
            path
            for path in incoming
            if "/records/dependency/" in _portable_relative_path(path)
        )
        status = stored.record.status
        snapshot = {"status": status} if isinstance(status, str) else None
        return RemovalAssessment(
            dict(target),
            stored,
            content,
            relative,
            incoming,
            dependencies,
            self._child_inventory(target, stored),
            snapshot,
            integrity_clearance,
            self._managed_payload_copy_paths(stored, content),
            active_quarantines,
        )

    def _assessment_from_resolution(
        self,
        target: Mapping[str, object],
        integrity_clearance: str,
    ) -> RemovalAssessment:
        resolution = self.resolve_removal_state(target)
        if resolution.disposition == "exceptionally_removed":
            raise PortiaConflictError("exact target is already exceptionally removed")
        assert resolution.stored is not None
        content = read_bytes(resolution.stored.path)
        relative = workspace_relative(self.root, resolution.stored.path)
        return RemovalAssessment(
            dict(target),
            resolution.stored,
            content,
            relative,
            (),
            (),
            self._child_inventory(target, resolution.stored),
            None,
            integrity_clearance,
            self._managed_payload_copy_paths(resolution.stored, content),
            self._active_quarantines(target),
        )

    @staticmethod
    def _pointer(operation_id: str, revision: int) -> PortiaRecord:
        return parse_portia_record(
            "operation_current_pointer",
            "1",
            {
                "schema_version": "1",
                "record_type": "operation_current_pointer",
                "module_id": "portia",
                "operation_id": operation_id,
                "journal_revision": revision,
            },
        )

    def _certificate(
        self,
        assessment: RemovalAssessment,
        *,
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        removal_id: str,
        operation_id: str,
        timestamp: str,
        parent_removal: Mapping[str, object] | None,
    ) -> PortiaRecord:
        target = assessment.target
        authorized_by = authorization["authorized_by"]
        if target.get("kind") == "actor_directory_record":
            actor_value = {
                "schema_version": "1",
                "record_type": "actor_directory_exceptional_removal",
                "module_id": "portia",
                "removal_id": removal_id,
                "target": deepcopy(target["actor_directory_record_ref"]),
                "original_workspace_relative_path": assessment.relative_path,
                "original_contract_version": assessment.stored.record.contract_version,
                "original_fingerprint": assessment.stored.fingerprint.digest,
                "original_byte_length": assessment.stored.fingerprint.byte_length,
                "ground": deepcopy(dict(reason)),
                "authorization": deepcopy(dict(authorization)),
                "removed_at": timestamp,
                "removed_by": deepcopy(authorized_by),
                "operation_ref": {"operation_id": operation_id},
                "retained_identity_evidence": deepcopy(
                    target["actor_directory_record_ref"]
                ),
            }
            return parse_portia_record(
                "actor_directory_exceptional_removal", "1", actor_value
            )
        salt = self.entropy(18)
        if len(salt) < 3:
            raise WorkflowPrerequisiteError("removal entropy provider returned too little entropy")
        evidence = {
            "kind": "salted_sha256",
            "salt": base64.b64encode(salt).decode("ascii"),
            "digest": hashlib.sha256(salt + assessment.canonical_bytes).hexdigest(),
            "byte_length": len(assessment.canonical_bytes),
        }
        work_wire = (
            target.get("work_ref")
            if target.get("kind") == "work"
            else cast(Mapping[str, object], target["work_record_ref"]).get("work_ref")
        )
        assert isinstance(work_wire, Mapping)
        certificate_value: dict[str, object] = {
            "schema_version": "1",
            "record_type": "exceptional_removal",
            "module_id": "portia",
            "class_id": work_wire["class_id"],
            "removal_id": removal_id,
            "target": deepcopy(dict(target)),
            "reason": deepcopy(dict(reason)),
            "authorization": deepcopy(dict(authorization)),
            "content_evidence": evidence,
            "effective_at": timestamp,
            "creation_source": {"type": "digital_entry"},
            "created_at": timestamp,
            "created_by": deepcopy(authorized_by),
        }
        if parent_removal is not None:
            certificate_value["parent_removal"] = deepcopy(dict(parent_removal))
        if assessment.lifecycle_snapshot is not None:
            certificate_value["lifecycle_snapshot"] = deepcopy(
                dict(assessment.lifecycle_snapshot)
            )
        return parse_portia_record("exceptional_removal", "1", certificate_value)

    def _certificate_ref_path(
        self,
        target: Mapping[str, object],
        removal_id: str,
    ) -> tuple[dict[str, object], str]:
        if target.get("kind") == "actor_directory_record":
            reference: dict[str, object] = {
                "module_id": "portia",
                "removal_id": removal_id,
                "contract_version": "1",
            }
            path = actor_directory_removal_path(self.root, removal_id)
        else:
            work_wire = (
                target.get("work_ref")
                if target.get("kind") == "work"
                else cast(Mapping[str, object], target["work_record_ref"]).get("work_ref")
            )
            assert isinstance(work_wire, Mapping)
            class_id = cast(str, work_wire["class_id"])
            reference = {
                "module_id": "portia",
                "class_id": class_id,
                "removal_id": removal_id,
                "contract_version": "1",
            }
            path = exceptional_removal_path(self.root, class_id, removal_id)
        return reference, workspace_relative(self.root, path)

    def _journal_value(
        self,
        assessment: RemovalAssessment,
        certificate: PortiaRecord,
        *,
        operation_id: str,
        removal_id: str,
        timestamp: str,
        authorization: Mapping[str, object],
        child_dispositions: Mapping[str, str],
        child_assessments: Mapping[str, RemovalAssessment],
    ) -> tuple[dict[str, object], dict[str, PortiaRecord]]:
        target = assessment.target
        certificate_bytes = canonical_json_bytes(certificate.to_dict())
        certificate_fp = fingerprint_bytes(certificate_bytes)
        removal_ref, certificate_path = self._certificate_ref_path(target, removal_id)
        certificate_target = {
            "kind": (
                "actor_directory_removal"
                if target.get("kind") == "actor_directory_record"
                else "exceptional_removal"
            ),
            "removal_ref": removal_ref,
        }
        cert_step = {
            "step_id": "step_create_removal_certificate",
            "sequence": 1,
            "phase": "canonical_gate",
            "action": "exclusive_create",
            "target": certificate_target,
            "representation_role": "canonical_domain",
            "destination_path": certificate_path,
            "precondition": {"presence": "must_be_absent"},
            "intended_result": {
                "kind": "present",
                "contract_version": "1",
                "fingerprint": certificate_fp.to_dict(),
                "selected_state": [],
            },
            "disposition": "pending",
            "observed_result": None,
            "compensation_step_id": None,
            "reason_code": None,
        }
        selected_state: list[dict[str, object]] = []
        if assessment.stored.record.status is not None:
            selected_state.append(
                {
                    "name": "status",
                    "kind": "token",
                    "value": assessment.stored.record.status,
                }
            )
        removal_step = {
            "step_id": "step_remove_canonical_payload",
            "sequence": 2,
            "phase": "canonical_gate",
            "action": "exceptional_remove",
            "target": deepcopy(dict(target)),
            "representation_role": "canonical_domain",
            "destination_path": assessment.relative_path,
            "precondition": {
                "presence": "must_match",
                "fingerprint": assessment.stored.fingerprint.to_dict(),
                "contract_version": assessment.stored.record.contract_version,
                "semantic_checks": [],
            },
            "intended_result": {
                "kind": "absent",
                "prior_contract_version": assessment.stored.record.contract_version,
                "prior_fingerprint": assessment.stored.fingerprint.to_dict(),
                "removal_certificate": {
                    "ref": removal_ref,
                    "workspace_relative_path": certificate_path,
                    "fingerprint": certificate_fp.to_dict(),
                },
                "selected_state": [
                    {
                        "name": "availability",
                        "kind": "token",
                        "value": "exceptionally_removed",
                    }
                ],
            },
            "disposition": "pending",
            "observed_result": None,
            "compensation_step_id": None,
            "reason_code": None,
        }
        preflight = [
            {
                "target": deepcopy(dict(target)),
                "representation_role": "canonical_domain",
                "expected_state": {
                    "presence": "must_match",
                    "fingerprint": assessment.stored.fingerprint.to_dict(),
                    "semantic_checks": [],
                },
                "workspace_relative_path": assessment.relative_path,
                "contract_version": assessment.stored.record.contract_version,
                "source_basis": "canonical",
                "source_projection": None,
                "selected_state": selected_state,
                "observed_at": timestamp,
            }
        ]
        for child in assessment.children:
            child_assessment = child_assessments.get(child.relative_path)
            if child_assessment is None:
                child_stored = self._load_target(child.target)
                child_fingerprint = child_stored.fingerprint
                child_contract = child_stored.record.contract_version
            else:
                child_fingerprint = child_assessment.stored.fingerprint
                child_contract = child_assessment.stored.record.contract_version
            preflight.append(
                {
                    "target": deepcopy(dict(child.target)),
                    "representation_role": "canonical_domain",
                    "expected_state": {
                        "presence": "must_match",
                        "fingerprint": child_fingerprint.to_dict(),
                        "semantic_checks": [],
                    },
                    "workspace_relative_path": child.relative_path,
                    "contract_version": child_contract,
                    "source_basis": "canonical",
                    "source_projection": None,
                    "selected_state": [
                        {
                            "name": "root_child_disposition",
                            "kind": "token",
                            "value": child_dispositions[child.relative_path],
                        }
                    ],
                    "observed_at": timestamp,
                }
            )
        operation_target: dict[str, object] = {
            "kind": "operation",
            "operation_ref": {"operation_id": operation_id},
        }
        lock_targets: list[tuple[str, dict[str, object]]] = []
        if target.get("kind") == "actor_directory_record":
            lock_targets.extend(
                [("actor_directory_record", dict(target)), ("operation", operation_target)]
            )
        else:
            protected_target: dict[str, object] = dict(target)
            lock_scope = "work"
            if target.get("kind") == "work_record":
                composite = target.get("work_record_ref")
                work_reference = (
                    composite.get("work_ref")
                    if isinstance(composite, Mapping)
                    else None
                )
                if not isinstance(work_reference, Mapping):
                    raise PortiaCorruptionError(
                        "work-record removal lock lacks exact work ownership"
                    )
                protected_target = {
                    "kind": "work",
                    "work_ref": deepcopy(dict(work_reference)),
                }
            lock_targets.extend(
                [
                    ("operation", operation_target),
                    (lock_scope, protected_target),
                ]
            )
        lock_entries: list[dict[str, object]] = []
        lock_records: dict[str, PortiaRecord] = {}
        for sequence, (scope, protected) in enumerate(lock_targets, start=1):
            lock_id = derive_lock_id(scope, protected)
            lock_entries.append(
                {
                    "lock_id": lock_id,
                    "sequence": sequence,
                    "lock_scope": scope,
                    "protected_target": protected,
                    "lock_path": f"portia/locks/{lock_id}.json",
                    "disposition": "planned",
                    "fingerprint": None,
                    "acquired_at": None,
                    "released_at": None,
                }
            )
            lock_records[lock_id] = parse_portia_record(
                "operation_lock",
                "2",
                {
                    "schema_version": "2",
                    "record_type": "operation_lock",
                    "module_id": "portia",
                    "lock_id": lock_id,
                    "lock_scope": scope,
                    "protected_target": protected,
                    "owning_operation": {"operation_id": operation_id},
                    "acquired_at": timestamp,
                    "deployment_instance_id": "exceptional_removal",
                    "process_instance_id": "exceptional_removal",
                },
            )
        intent = {
            "target": target,
            "removal_id": removal_id,
            "decision_reference": authorization["decision_reference"],
        }
        value: dict[str, object] = {
            "schema_version": "3",
            "record_type": "operation_journal",
            "module_id": "portia",
            "operation_id": operation_id,
            "operation_kind": "exceptionally_remove",
            "intent_digest": fingerprint_bytes(canonical_json_bytes(intent)).digest,
            "scope": "workspace" if target.get("kind") == "actor_directory_record" else "work",
            "primary_target": deepcopy(dict(target)),
            "affected_targets": [
                certificate_target,
                *[deepcopy(dict(child.target)) for child in assessment.children],
            ],
            "intent_facts": [
                {"name": "incoming_reference_count", "kind": "integer", "value": len(assessment.incoming_references)},
                {"name": "dependency_count", "kind": "integer", "value": len(assessment.dependencies)},
                {"name": "child_count", "kind": "integer", "value": len(assessment.children)},
                {"name": "managed_copy_count", "kind": "integer", "value": len(assessment.managed_payload_copies)},
            ],
            "initiated_at": timestamp,
            "initiated_by": deepcopy(authorization["authorized_by"]),
            "authorization_references": [],
            "journal_revision": 1,
            "previous_journal_revision": None,
            "state": "prepared",
            "preflight_snapshot_digest": fingerprint_bytes(
                canonical_json_bytes({"entries": preflight})
            ).digest,
            "preflight_snapshot": preflight,
            "lock_set": lock_entries,
            "write_set": [cert_step, removal_step],
            "staged_artifacts": [],
            "commit_point": {"reached": False, "reached_at": None},
            "compensation_plan": [],
            "recovery_plan": [
                "resume",
                "reconcile_as_complete",
                "complete_remaining_steps",
                "quarantine",
                "require_manual_review",
            ],
            "partial_state": {
                "durability_assessment": "none",
                "accepted_steps": [],
                "verified_steps": [],
                "durable_unverified_steps": [],
                "indeterminate_steps": [],
                "remaining_canonical_steps": [
                    "step_create_removal_certificate",
                    "step_remove_canonical_payload",
                ],
                "remaining_post_commit_steps": [],
                "current_pointer_changes": [],
                "held_or_possible_locks": [],
                "quarantined_targets": [],
                "active_finding_keys": [],
                "recommended_disposition": "resume",
            },
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return value, lock_records

    def _append_certificate_accepted(
        self,
        state: SeriesState,
        certificate: StoredRecord,
        quarantine: SeriesState,
        timestamp: str,
    ) -> SeriesState:
        data = deepcopy(state.revision.to_dict())
        data.update(
            {
                "journal_revision": 2,
                "previous_journal_revision": 1,
                "state": "recovering",
                "updated_at": timestamp,
            }
        )
        steps = cast(list[dict[str, object]], data["write_set"])
        steps[0]["disposition"] = "accepted"
        steps[0]["observed_result"] = {
            "kind": "present",
            "workspace_relative_path": workspace_relative(self.root, certificate.path),
            "fingerprint": certificate.fingerprint.to_dict(),
            "observed_at": timestamp,
        }
        partial = cast(dict[str, object], data["partial_state"])
        quarantine_data = quarantine.revision.to_dict()
        partial.update(
            {
                "durability_assessment": "confirmed",
                "accepted_steps": ["step_create_removal_certificate"],
                "remaining_canonical_steps": ["step_remove_canonical_payload"],
                "quarantined_targets": [
                    {
                        "quarantine_id": quarantine_data["quarantine_id"],
                        "quarantine_revision": quarantine_data["quarantine_revision"],
                        "contract_version": quarantine.revision.contract_version,
                    }
                ],
            }
        )
        record = parse_portia_record("operation_journal", "3", data)
        return self.operations.append(
            record,
            self._pointer(cast(str, data["operation_id"]), 2),
            expected_pointer=state.pointer_fingerprint,
        )

    def _append_completed(
        self,
        state: SeriesState,
        observation: AbsenceObservation,
        timestamp: str,
    ) -> SeriesState:
        data = deepcopy(state.revision.to_dict())
        prior = cast(int, data["journal_revision"])
        data.update(
            {
                "journal_revision": prior + 1,
                "previous_journal_revision": prior,
                "state": "completed",
                "commit_point": {"reached": True, "reached_at": timestamp},
                "updated_at": timestamp,
            }
        )
        steps = cast(list[dict[str, object]], data["write_set"])
        steps[1]["disposition"] = "accepted"
        steps[1]["observed_result"] = observation.to_dict()
        partial = cast(dict[str, object], data["partial_state"])
        partial.update(
            {
                "durability_assessment": "confirmed",
                "accepted_steps": [
                    "step_create_removal_certificate",
                    "step_remove_canonical_payload",
                ],
                "verified_steps": [],
                "durable_unverified_steps": [],
                "indeterminate_steps": [],
                "remaining_canonical_steps": [],
                "remaining_post_commit_steps": [],
                "recommended_disposition": None,
            }
        )
        record = parse_portia_record("operation_journal", "3", data)
        return self.operations.append(
            record,
            self._pointer(cast(str, data["operation_id"]), prior + 1),
            expected_pointer=state.pointer_fingerprint,
        )

    def _append_absence_verified(
        self,
        state: SeriesState,
        observation: AbsenceObservation,
        timestamp: str,
    ) -> SeriesState:
        """Journal verified absence before post-removal purge can complete."""
        data = deepcopy(state.revision.to_dict())
        prior = cast(int, data["journal_revision"])
        data.update(
            {
                "journal_revision": prior + 1,
                "previous_journal_revision": prior,
                "state": "recovering",
                "updated_at": timestamp,
            }
        )
        steps = cast(list[dict[str, object]], data["write_set"])
        steps[1]["disposition"] = "verified"
        steps[1]["observed_result"] = observation.to_dict()
        partial = cast(dict[str, object], data["partial_state"])
        partial.update(
            {
                "durability_assessment": "confirmed",
                "accepted_steps": ["step_create_removal_certificate"],
                "verified_steps": ["step_remove_canonical_payload"],
                "remaining_canonical_steps": [],
                "remaining_post_commit_steps": [],
                "recommended_disposition": "resume",
            }
        )
        record = parse_portia_record("operation_journal", "3", data)
        return self.operations.append(
            record,
            self._pointer(cast(str, data["operation_id"]), prior + 1),
            expected_pointer=state.pointer_fingerprint,
        )

    def _managed_copy_candidates(self, canonical_path: Path) -> tuple[Path, ...]:
        candidates: set[Path] = set()
        for path in self.root.rglob("*"):
            if not path.is_file() or path == canonical_path:
                continue
            relative = "/" + _portable_relative_path(workspace_relative(self.root, path))
            staged = "/.portia-staging/" in relative
            derived = relative.startswith("/portia/derived/") or (
                "/modules/portia/" in relative and "/derived/" in relative
            )
            if staged or derived:
                candidates.add(path)
        return tuple(sorted(candidates))

    def _purge_derived_generation(self, payload_path: Path) -> tuple[str, ...]:
        parts = payload_path.parts
        indices = [index for index, part in enumerate(parts) if part == "generations"]
        if not indices or indices[-1] + 1 >= len(parts):
            raise PortiaRecoveryRequiredError(
                "payload-bearing derived artifact is not in an accepted generation"
            )
        index = indices[-1]
        generation_root = Path(*parts[: index + 2])
        projection_root = generation_root.parent.parent
        ensure_runtime_containment(self.root, generation_root)
        removed: list[str] = []
        current = projection_root / "current.json"
        if current.exists():
            value, _content, fingerprint = read_json(current)
            generation_ref = value.get("generation_ref") if isinstance(value, Mapping) else None
            if (
                isinstance(generation_ref, Mapping)
                and generation_ref.get("generation_id") == generation_root.name
            ):
                exact_delete(current, expected=fingerprint)
                removed.append(workspace_relative(self.root, current))
        for path in sorted(generation_root.rglob("*"), reverse=True):
            if path.is_symlink():
                raise PortiaCorruptionError("derived purge encountered a symbolic link")
            if path.is_file():
                fingerprint = fingerprint_bytes(read_bytes(path))
                exact_delete(path, expected=fingerprint)
                removed.append(workspace_relative(self.root, path))
        return tuple(removed)

    def _purge_matching_managed_copies(
        self,
        canonical_path: Path,
        matches: Callable[[bytes], bool],
    ) -> tuple[str, ...]:
        removed: list[str] = []
        matched = [
            path
            for path in self._managed_copy_candidates(canonical_path)
            if matches(read_bytes(path))
        ]
        for path in matched:
            if not path.exists():
                continue
            ensure_runtime_containment(self.root, path)
            if path.is_symlink():
                raise PortiaCorruptionError("managed-copy purge encountered a symbolic link")
            relative = "/" + _portable_relative_path(workspace_relative(self.root, path))
            if "/derived/" in relative:
                removed.extend(self._purge_derived_generation(path))
                continue
            content = read_bytes(path)
            fingerprint = fingerprint_bytes(content)
            exact_delete(path, expected=fingerprint)
            removed.append(workspace_relative(self.root, path))
        if any(matches(read_bytes(path)) for path in self._managed_copy_candidates(canonical_path)):
            raise PortiaRecoveryRequiredError(
                "prohibited Portia-managed payload copy remains after purge"
            )
        return tuple(removed)

    def _purge_managed_copies(
        self,
        assessment: RemovalAssessment,
    ) -> tuple[str, ...]:
        target_value = assessment.stored.record.to_dict()
        def matches(content: bytes) -> bool:
            contains = content == assessment.canonical_bytes
            if not contains:
                try:
                    contains = _contains_exact(json.loads(content.decode("utf-8")), target_value)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    contains = False
            return contains

        return self._purge_matching_managed_copies(assessment.stored.path, matches)

    def _purge_managed_copies_from_journal(
        self,
        target: Mapping[str, object],
        prior_fingerprint: Mapping[str, object],
    ) -> tuple[str, ...]:
        digest = prior_fingerprint.get("digest")
        byte_length = prior_fingerprint.get("byte_length")
        if not isinstance(digest, str) or not isinstance(byte_length, int):
            raise PortiaCorruptionError("removal journal prior fingerprint is malformed")
        relative = expected_target_relative_path(self.root, dict(target))
        if relative is None:
            raise PortiaCorruptionError("removal journal target has no canonical path")
        canonical_path = resolve_workspace_relative(self.root, relative)

        def exact_value(value: object) -> bool:
            try:
                candidate = canonical_json_bytes(value)
            except (TypeError, ValueError):
                return False
            observed = fingerprint_bytes(candidate)
            if observed.digest == digest and observed.byte_length == byte_length:
                return True
            if isinstance(value, Mapping):
                return any(exact_value(child) for child in value.values())
            if isinstance(value, list):
                return any(exact_value(child) for child in value)
            return False

        def matches(content: bytes) -> bool:
            observed = fingerprint_bytes(content)
            if observed.digest == digest and observed.byte_length == byte_length:
                return True
            try:
                return exact_value(json.loads(content.decode("utf-8")))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return False

        return self._purge_matching_managed_copies(canonical_path, matches)

    @staticmethod
    def _require_reviews(
        assessment: RemovalAssessment,
        reviewed_incoming_references: Sequence[str],
        dependency_dispositions: Mapping[str, str],
        child_dispositions: Mapping[str, str],
    ) -> None:
        if tuple(sorted(reviewed_incoming_references)) != assessment.incoming_references:
            raise WorkflowPrerequisiteError(
                "incoming-reference review is not complete for the fresh canonical scan"
            )
        if set(dependency_dispositions) != set(assessment.dependencies):
            raise WorkflowPrerequisiteError("Dependency review is incomplete")
        if any(value not in _DEPENDENCY_DISPOSITIONS for value in dependency_dispositions.values()):
            raise WorkflowPrerequisiteError("Dependency review has unsupported disposition")
        expected_children = {child.relative_path for child in assessment.children}
        if set(child_dispositions) != expected_children:
            raise WorkflowPrerequisiteError("root child inventory/disposition is incomplete")
        if any(value not in _CHILD_DISPOSITIONS for value in child_dispositions.values()):
            raise WorkflowPrerequisiteError("root child disposition is unsupported")

    def _prepare_child_removals(
        self,
        assessment: RemovalAssessment,
        *,
        child_dispositions: Mapping[str, str],
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        synthetic_test_data_confirmed: bool,
        recovery_disposition: str | None,
    ) -> dict[str, RemovalAssessment]:
        prepared: dict[str, RemovalAssessment] = {}
        actor_root = False
        wrapper = assessment.target.get("actor_directory_record_ref")
        if assessment.target.get("kind") == "actor_directory_record" and isinstance(
            wrapper, Mapping
        ):
            actor_root = wrapper.get("kind") == "actor"
        for child in assessment.children:
            disposition = child_dispositions[child.relative_path]
            if actor_root and disposition != "exceptionally_removed":
                raise WorkflowPrerequisiteError(
                    "Actor-root removal requires every owned current child to be "
                    "exceptionally removed"
                )
            if disposition == "retained" and assessment.target.get("kind") == "work":
                reference = child.target.get("work_record_ref")
                local = reference.get("record_ref") if isinstance(reference, Mapping) else None
                record_kind = local.get("record_kind") if isinstance(local, Mapping) else None
                if record_kind not in _RETAINABLE_WORK_AUDIT_KINDS:
                    raise WorkflowPrerequisiteError(
                        "a substantive work child cannot remain current without its root"
                    )
            if disposition != "exceptionally_removed":
                continue
            child_assessment = self.assess_removal(
                target=child.target,
                reason=reason,
                authorization=authorization,
                integrity_clearance=assessment.integrity_clearance,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
            if child_assessment.incoming_references or child_assessment.dependencies:
                raise WorkflowPrerequisiteError(
                    "root-owned child with incoming references must be removed in a "
                    "separately reviewed operation"
                )
            prepared[child.relative_path] = child_assessment
        return prepared

    def _remove_prepared_children(
        self,
        prepared: Mapping[str, RemovalAssessment],
        *,
        target: Mapping[str, object],
        removal_id: str,
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        timestamp: str,
        synthetic_test_data_confirmed: bool,
        recovery_disposition: str | None,
    ) -> None:
        parent_ref: Mapping[str, object] | None = None
        if target.get("kind") == "work":
            parent_ref, _path = self._certificate_ref_path(target, removal_id)
        for child_path in sorted(prepared):
            child = prepared[child_path]
            self.exceptionally_remove(
                child,
                reason=reason,
                authorization=authorization,
                reviewed_incoming_references=(),
                dependency_dispositions={},
                child_dispositions={},
                parent_removal=parent_ref,
                effective_at=timestamp,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )

    def exceptionally_remove(
        self,
        assessment: RemovalAssessment,
        *,
        reason: Mapping[str, object],
        authorization: Mapping[str, object],
        reviewed_incoming_references: Sequence[str] = (),
        dependency_dispositions: Mapping[str, str] | None = None,
        child_dispositions: Mapping[str, str] | None = None,
        parent_removal: Mapping[str, object] | None = None,
        operation_id: str | None = None,
        removal_id: str | None = None,
        quarantine_id: str | None = None,
        effective_at: str | None = None,
        synthetic_test_data_confirmed: bool = False,
        recovery_disposition: str | None = None,
        fault_hook: FaultHook | None = None,
    ) -> ExceptionalRemovalResult:
        timestamp = effective_at or self.clock()
        _explicit_timestamp(timestamp)
        target = assessment.target
        if target.get("kind") == "actor_directory_record":
            self.authority.require_actor(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        else:
            self.authority.require_generic(
                reason,
                authorization,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
        self._require_reviews(
            assessment,
            reviewed_incoming_references,
            dependency_dispositions or {},
            child_dispositions or {},
        )
        selected_child_dispositions = child_dispositions or {}
        prepared_children = self._prepare_child_removals(
            assessment,
            child_dispositions=selected_child_dispositions,
            reason=reason,
            authorization=authorization,
            synthetic_test_data_confirmed=synthetic_test_data_confirmed,
            recovery_disposition=recovery_disposition,
        )
        current_content = read_bytes(assessment.stored.path)
        if fingerprint_bytes(current_content) != assessment.stored.fingerprint:
            raise PortiaConflictError("canonical target changed after preflight")
        if current_content != assessment.canonical_bytes:
            raise PortiaConflictError("canonical target bytes changed after preflight")
        if self._matching_certificates(target):
            resolution = self.resolve_removal_state(target)
            if resolution.disposition == "exceptionally_removed":
                raise PortiaConflictError("use resolve_removal_state for completed replay")
            raise PortiaRecoveryRequiredError(
                "existing certificate requires operation recovery, not a second removal"
            )
        op_id = operation_id or f"op_{secrets.token_hex(16)}"
        rmv_id = removal_id or f"rmv_{secrets.token_hex(16)}"
        certificate = self._certificate(
            assessment,
            reason=reason,
            authorization=authorization,
            removal_id=rmv_id,
            operation_id=op_id,
            timestamp=timestamp,
            parent_removal=parent_removal,
        )
        journal_value, lock_records = self._journal_value(
            assessment,
            certificate,
            operation_id=op_id,
            removal_id=rmv_id,
            timestamp=timestamp,
            authorization=authorization,
            child_dispositions=selected_child_dispositions,
            child_assessments=prepared_children,
        )
        journal = parse_portia_record("operation_journal", "3", journal_value)
        operation = self.operations.create(journal, self._pointer(op_id, 1))
        held: list[HeldLock] = []
        try:
            for entry in cast(list[dict[str, object]], journal_value["lock_set"]):
                held.append(self.locks.acquire(lock_records[cast(str, entry["lock_id"])]))
            quarantine = self.quarantines.apply_quarantine(
                target=target,
                reason="removal_reconciliation",
                effects=(
                    [
                        "block_current_use",
                        "block_actor_directory_writes",
                        "block_operation_completion",
                        "review_required",
                    ]
                    if target.get("kind") == "actor_directory_record"
                    else [
                        "block_current_use",
                        "block_operation_completion",
                        "review_required",
                    ]
                ),
                applying_operation={
                    "operation_id": op_id,
                    "journal_revision": 1,
                    "contract_version": "3",
                },
                supporting_finding_keys=[],
                applied_at=timestamp,
                applied_by=cast(Mapping[str, object], authorization["authorized_by"]),
                release_requirements=[
                    "actor_state_reconciled"
                    if target.get("kind") == "actor_directory_record"
                    else "canonical_state_reconciled"
                ],
                quarantine_id=quarantine_id,
            )
            if fault_hook is not None:
                fault_hook("after_quarantine_selected", None)
            if target.get("kind") == "actor_directory_record":
                stored_certificate = self.actors.create_exceptional_removal(certificate)
            else:
                stored_certificate = self.repository.create_exceptional_removal(certificate)
            if fault_hook is not None:
                fault_hook("after_certificate_durable", None)
            operation = self._append_certificate_accepted(
                operation,
                stored_certificate,
                quarantine,
                timestamp,
            )
            suspended_work_lock: PortiaRecord | None = None
            if prepared_children and target.get("kind") == "work":
                for acquired in tuple(held):
                    if acquired.record.to_dict().get("lock_scope") == "work":
                        suspended_work_lock = acquired.record
                        self.locks.release(acquired)
                        held.remove(acquired)
                        break
            self._remove_prepared_children(
                prepared_children,
                target=target,
                removal_id=rmv_id,
                reason=reason,
                authorization=authorization,
                timestamp=timestamp,
                synthetic_test_data_confirmed=synthetic_test_data_confirmed,
                recovery_disposition=recovery_disposition,
            )
            if suspended_work_lock is not None:
                held.append(self.locks.acquire(suspended_work_lock))
            if fault_hook is not None:
                fault_hook("before_exceptional_remove", None)
            quarantine_data = quarantine.revision.to_dict()
            capability = _issue_removal_capability(
                cast(str, authorization["decision_reference"]),
                cast(Mapping[str, object], authorization["authorized_by"]),
            )
            observation = self.remover.remove(
                CanonicalRemovalRequest(
                    target=target,
                    operation_id=op_id,
                    journal_revision=2,
                    step_id="step_remove_canonical_payload",
                    quarantine_id=cast(str, quarantine_data["quarantine_id"]),
                ),
                capability=capability,
            )
            if fault_hook is not None:
                fault_hook("after_payload_absence", None)
            operation = self._append_absence_verified(operation, observation, timestamp)
            if fault_hook is not None:
                fault_hook("after_absence_journaled", None)
            self._purge_managed_copies(assessment)
            if fault_hook is not None:
                fault_hook("after_purge", None)
            operation = self._append_completed(operation, observation, timestamp)
            if fault_hook is not None:
                fault_hook("after_operation_completion", None)
            resolution = self.resolve_removal_state(target)
            return ExceptionalRemovalResult(
                operation,
                stored_certificate,
                quarantine,
                resolution,
                observation,
            )
        finally:
            for acquired in reversed(held):
                self.locks.release(acquired)
