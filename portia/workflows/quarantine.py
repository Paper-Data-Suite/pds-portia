"""Evidence-backed application and resolution of Portia Quarantine."""

from __future__ import annotations

import re
import secrets
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import PortiaConflictError, PortiaCorruptionError
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.integrity import expected_target_relative_path
from portia.storage.io import read_bytes, read_json
from portia.storage.paths import (
    actors_root,
    operation_revision_path,
    resolve_workspace_relative,
)
from portia.storage.quarantine import quarantine_applies
from portia.storage.series import OperationJournalStore, QuarantineStore, SeriesState
from portia.workflows.errors import WorkflowPrerequisiteError

_REASONS = frozenset(
    {
        "journal_integrity",
        "partial_commit",
        "canonical_contradiction",
        "lock_integrity",
        "lifecycle_reconciliation",
        "replacement_reconciliation",
        "dependency_reconciliation",
        "migration_reconciliation",
        "ownership_reconciliation",
        "removal_reconciliation",
        "authorization_limitation",
        "derived_state_safety",
        "external_mutation",
        "actor_identity_contradiction",
        "actor_contact_privacy",
        "actor_roster_collision",
        "actor_split_reconciliation",
    }
)
_ACTOR_REASONS = frozenset(
    {
        "actor_identity_contradiction",
        "actor_contact_privacy",
        "actor_roster_collision",
        "actor_split_reconciliation",
    }
)
_ACTOR_KINDS = frozenset(
    {"actor_directory_record", "actor_set", "actor_directory_collection"}
)
_TARGET_EFFECTS: dict[str, frozenset[str]] = {
    "operation": frozenset({"block_operation_completion", "review_required"}),
    "work": frozenset(
        {
            "block_current_use",
            "block_lifecycle_writes",
            "block_work_writes",
            "block_operation_completion",
            "review_required",
        }
    ),
    "work_record": frozenset(
        {
            "block_current_use",
            "block_lifecycle_writes",
            "block_work_writes",
            "block_operation_completion",
            "review_required",
        }
    ),
    "exceptional_removal": frozenset(
        {"block_operation_completion", "review_required"}
    ),
    "class": frozenset(
        {
            "block_current_use",
            "block_lifecycle_writes",
            "block_work_writes",
            "block_class_writes",
            "block_operation_completion",
            "review_required",
        }
    ),
    "workspace": frozenset(
        {
            "block_current_use",
            "block_lifecycle_writes",
            "block_work_writes",
            "block_class_writes",
            "block_operation_completion",
            "block_projection_use",
            "review_required",
            "block_actor_directory_writes",
        }
    ),
    "derived_projection": frozenset({"block_projection_use", "review_required"}),
    "actor_directory_record": frozenset(
        {
            "block_current_use",
            "block_actor_directory_writes",
            "block_operation_completion",
            "review_required",
        }
    ),
    "actor_set": frozenset(
        {
            "block_current_use",
            "block_actor_directory_writes",
            "block_operation_completion",
            "review_required",
        }
    ),
    "actor_directory_collection": frozenset(
        {"block_actor_directory_writes", "block_projection_use", "review_required"}
    ),
}
_NON_FINDING_REASONS = frozenset(
    {
        "journal_integrity",
        "partial_commit",
        "canonical_contradiction",
        "lock_integrity",
        "authorization_limitation",
        "external_mutation",
    }
)
_RELEASE_REQUIREMENTS = frozenset(
    {"canonical_state_reconciled", "actor_state_reconciled", "integrity_scan_clean"}
)


def _timestamp(value: object, description: str) -> datetime:
    if not isinstance(value, str):
        raise WorkflowPrerequisiteError(f"{description} must be an explicit timestamp")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise WorkflowPrerequisiteError(
            f"{description} must be a valid explicit-offset timestamp"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowPrerequisiteError(
            f"{description} must include an explicit UTC offset"
        )
    return parsed


def _bounded_detail(value: object, description: str, *, optional: bool) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise WorkflowPrerequisiteError(f"{description} must be bounded non-empty text")
    if len(value) > 512 or any(character in value for character in "\r\n\x00"):
        raise WorkflowPrerequisiteError(
            f"{description} must be one privacy-minimized line of at most 512 characters"
        )
    lowered = value.lower()
    if (
        "@" in value
        or ":\\" in value
        or ":/" in value
        or lowered.startswith(("/", "\\\\"))
        or "contact_value" in lowered
        or "student_name" in lowered
    ):
        raise WorkflowPrerequisiteError(
            f"{description} contains path-like or sensitive payload"
        )
    return value


def _operation_targets(journal: PortiaRecord) -> tuple[object, ...]:
    data = journal.to_dict()
    affected = data.get("affected_targets")
    return (
        data.get("primary_target"),
        *(affected if isinstance(affected, list) else ()),
    )


def _operation_owns_target(journal: PortiaRecord, target: object) -> bool:
    return any(
        candidate == target or quarantine_applies(candidate, target)
        for candidate in _operation_targets(journal)
    )


class QuarantineWorkflowService:
    """Application validation above the immutable Quarantine revision store."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self.store = QuarantineStore(self.root)
        self.operations = OperationJournalStore(self.root)

    def _load_operation_reference(
        self,
        value: Mapping[str, object],
        *,
        description: str,
    ) -> PortiaRecord:
        reference = dict(value)
        if set(reference) != {
            "operation_id",
            "journal_revision",
            "contract_version",
        }:
            raise WorkflowPrerequisiteError(
                f"{description} does not have the exact operation-reference shape"
            )
        operation_id = reference.get("operation_id")
        revision = reference.get("journal_revision")
        if (
            not isinstance(operation_id, str)
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or reference.get("contract_version") != "2"
        ):
            raise WorkflowPrerequisiteError(
                f"{description} is not an exact operation_journal@2 reference"
            )
        try:
            current = self.operations.load_current(operation_id)
            selected = current.revision.to_dict().get("journal_revision")
            if not isinstance(selected, int) or revision > selected:
                raise WorkflowPrerequisiteError(
                    f"{description} names an unaccepted journal revision"
                )
            raw, _content, _fingerprint = read_json(
                operation_revision_path(self.root, operation_id, revision)
            )
            journal = parse_portia_record("operation_journal", "2", raw)
        except WorkflowPrerequisiteError:
            raise
        except Exception as exc:
            raise WorkflowPrerequisiteError(
                f"{description} does not resolve through Operation Journal authority"
            ) from exc
        data = journal.to_dict()
        if (
            data.get("operation_id") != operation_id
            or data.get("journal_revision") != revision
            or data.get("state") != "completed"
        ):
            raise WorkflowPrerequisiteError(
                f"{description} must name an accepted completed operation"
            )
        return journal

    def _validate_target_resolution(self, target: Mapping[str, object]) -> None:
        kind = target.get("kind")
        if kind == "operation":
            operation_ref = target.get("operation_ref")
            operation_id = (
                operation_ref.get("operation_id")
                if isinstance(operation_ref, Mapping)
                else None
            )
            if not isinstance(operation_id, str):
                raise WorkflowPrerequisiteError("operation target is not exact")
            self.operations.load_current(operation_id)
            return
        if kind == "workspace":
            if not self.root.exists() or not self.root.is_dir():
                raise WorkflowPrerequisiteError("workspace target is unavailable")
            return
        if kind == "class":
            class_id = target.get("class_id")
            if not isinstance(class_id, str) or not (self.root / "classes" / class_id).is_dir():
                raise WorkflowPrerequisiteError("class target does not resolve exactly")
            return
        if kind == "actor_set":
            refs = target.get("actor_refs")
            if not isinstance(refs, list):
                raise WorkflowPrerequisiteError("Actor-set target is malformed")
            actor_ids = [
                ref.get("actor_id") for ref in refs if isinstance(ref, Mapping)
            ]
            if (
                len(actor_ids) != len(refs)
                or any(not isinstance(actor_id, str) for actor_id in actor_ids)
                or actor_ids != sorted(cast(list[str], actor_ids))
            ):
                raise WorkflowPrerequisiteError(
                    "Actor-set target must be complete and sorted by exact actor ID"
                )
            for ref in refs:
                assert isinstance(ref, Mapping)
                self._validate_target_resolution(
                    {
                        "kind": "actor_directory_record",
                        "actor_directory_record_ref": {
                            "kind": "actor",
                            "actor_ref": dict(ref),
                        },
                    }
                )
            return
        if kind == "actor_directory_collection":
            if not actors_root(self.root).is_dir():
                raise WorkflowPrerequisiteError(
                    "Actor Directory collection target is unavailable"
                )
            return
        if kind == "derived_projection":
            projection_kind = target.get("projection_kind")
            projection_scope = target.get("projection_scope")
            if not isinstance(projection_kind, str) or not isinstance(
                projection_scope, Mapping
            ):
                raise WorkflowPrerequisiteError("derived projection target is malformed")
            from portia.storage.derived import DerivedStore

            DerivedStore(self.root).load_current(
                projection_kind,
                dict(projection_scope),
                require_fresh=False,
            )
            return
        if kind == "exceptional_removal":
            # The schema establishes the exact reference shape.  Resolution is
            # deliberately left to the Exceptional Removal authority rather
            # than guessed from a current work successor.
            raise WorkflowPrerequisiteError(
                "Exceptional Removal target application requires its family-specific authority"
            )
        relative = expected_target_relative_path(self.root, dict(target))
        if relative is None:
            raise WorkflowPrerequisiteError("Quarantine target has no exact storage resolution")
        read_bytes(resolve_workspace_relative(self.root, relative))

    def _current_findings(
        self,
        finding_scope: Mapping[str, object],
    ) -> tuple[PortiaRecord, ...]:
        from portia.workflows.integrity import IntegrityWorkflowService

        return IntegrityWorkflowService(self.root).current_findings(finding_scope)

    def _validate_supporting_findings(
        self,
        finding_keys: Sequence[str],
        finding_scope: Mapping[str, object] | None,
        *,
        reason: str,
    ) -> None:
        if not finding_keys:
            if reason not in _NON_FINDING_REASONS:
                raise WorkflowPrerequisiteError(
                    "this Quarantine reason requires exact supporting Integrity Findings"
                )
            return
        if finding_scope is None:
            raise WorkflowPrerequisiteError(
                "supporting finding keys require an exact current projection scope"
            )
        current_keys = {
            str(finding.to_dict().get("finding_key"))
            for finding in self._current_findings(finding_scope)
        }
        if not set(finding_keys).issubset(current_keys):
            raise WorkflowPrerequisiteError(
                "supporting finding keys do not resolve in current fresh integrity state"
            )

    @staticmethod
    def _validate_reason_effect_policy(
        target: Mapping[str, object],
        reason: str,
        effects: Sequence[str],
    ) -> None:
        kind = target.get("kind")
        if not isinstance(kind, str) or kind not in _TARGET_EFFECTS:
            raise WorkflowPrerequisiteError("unsupported Quarantine target family")
        if reason not in _REASONS:
            raise WorkflowPrerequisiteError("unsupported Quarantine reason")
        if reason in _ACTOR_REASONS and kind not in _ACTOR_KINDS:
            raise WorkflowPrerequisiteError(
                "Quarantine reason is not compatible with its exact target family"
            )
        if (
            kind in _ACTOR_KINDS
            and reason not in _ACTOR_REASONS
            and reason != "authorization_limitation"
        ):
            raise WorkflowPrerequisiteError(
                "Quarantine reason is not compatible with its exact Actor target"
            )
        if not effects or len(set(effects)) != len(effects):
            raise WorkflowPrerequisiteError("Quarantine effects must be unique and non-empty")
        unsupported = set(effects) - _TARGET_EFFECTS[kind]
        if unsupported:
            raise WorkflowPrerequisiteError(
                "Quarantine effects are not proportional to the exact target"
            )
        if kind == "actor_directory_collection" and (
            "block_actor_directory_writes" not in effects
        ):
            raise WorkflowPrerequisiteError(
                "Actor Directory collection Quarantine must block Actor writes"
            )

    @staticmethod
    def _pointer(quarantine_id: str, revision: int) -> PortiaRecord:
        return parse_portia_record(
            "quarantine_current_pointer",
            "1",
            {
                "schema_version": "1",
                "record_type": "quarantine_current_pointer",
                "module_id": "portia",
                "quarantine_id": quarantine_id,
                "quarantine_revision": revision,
            },
        )

    def apply_quarantine(
        self,
        *,
        target: Mapping[str, object],
        reason: str,
        effects: Sequence[str],
        applying_operation: Mapping[str, object],
        supporting_finding_keys: Sequence[str],
        applied_at: str,
        applied_by: Mapping[str, object],
        release_requirements: Sequence[str],
        reason_detail: str | None = None,
        review_deadline: str | None = None,
        created_at: str | None = None,
        finding_scope: Mapping[str, object] | None = None,
        quarantine_id: str | None = None,
    ) -> SeriesState:
        """Create active revision 1 only after all evidence validates."""
        exact_target = deepcopy(dict(target))
        self._validate_reason_effect_policy(exact_target, reason, effects)
        detail = _bounded_detail(reason_detail, "reason_detail", optional=True)
        applied = _timestamp(applied_at, "applied_at")
        created_value = created_at or applied_at
        if _timestamp(created_value, "created_at") < applied:
            raise WorkflowPrerequisiteError("created_at cannot precede applied_at")
        if review_deadline is not None and _timestamp(
            review_deadline, "review_deadline"
        ) < applied:
            raise WorkflowPrerequisiteError("review_deadline cannot precede application")
        if (
            not release_requirements
            or len(set(release_requirements)) != len(release_requirements)
            or not set(release_requirements).issubset(_RELEASE_REQUIREMENTS)
        ):
            raise WorkflowPrerequisiteError(
                "release requirements are not supported evidence tokens"
            )
        actor_target = exact_target.get("kind") in _ACTOR_KINDS
        expected_state_token = (
            "actor_state_reconciled" if actor_target else "canonical_state_reconciled"
        )
        if expected_state_token not in release_requirements:
            raise WorkflowPrerequisiteError(
                "Quarantine requires an exact state-reconciliation release condition"
            )
        journal = self._load_operation_reference(
            applying_operation,
            description="applying operation",
        )
        journal_data = journal.to_dict()
        if dict(applied_by) != journal_data.get("initiated_by"):
            raise WorkflowPrerequisiteError(
                "applied_by is not the exact accepted applying-operation actor"
            )
        if applied < _timestamp(journal_data.get("initiated_at"), "operation initiated_at"):
            raise WorkflowPrerequisiteError("Quarantine application predates its operation")
        if not _operation_owns_target(journal, exact_target):
            raise WorkflowPrerequisiteError(
                "applying operation does not own the exact Quarantine target"
            )
        self._validate_supporting_findings(
            supporting_finding_keys,
            finding_scope,
            reason=reason,
        )
        self._validate_target_resolution(exact_target)

        identifier = quarantine_id or f"qnt_{secrets.token_hex(16)}"
        if re.fullmatch(r"qnt_[0-9a-f]{32}", identifier) is None:
            raise WorkflowPrerequisiteError(
                "Quarantine identifier must be an opaque qnt_ token"
            )
        value = {
            "schema_version": "2",
            "record_type": "quarantine_record",
            "module_id": "portia",
            "quarantine_id": identifier,
            "quarantine_revision": 1,
            "previous_quarantine_revision": None,
            "state": "active",
            "target": exact_target,
            "reason": reason,
            "reason_detail": detail,
            "effects": list(effects),
            "origin": {
                "applying_operation": deepcopy(dict(applying_operation)),
                "supporting_finding_keys": list(supporting_finding_keys),
                "applied_at": applied_at,
                "applied_by": deepcopy(dict(applied_by)),
                "release_requirements": list(release_requirements),
                "review_deadline": review_deadline,
            },
            "resolution": None,
            "created_at": created_value,
        }
        try:
            record = parse_portia_record("quarantine_record", "2", value)
        except Exception as exc:
            raise WorkflowPrerequisiteError("Quarantine application is invalid") from exc
        return self.store.create(record, self._pointer(identifier, 1))

    def _validate_resolution_operation(
        self,
        value: Mapping[str, object],
        *,
        resolved_by: Mapping[str, object],
        effective_at: str,
        target: object,
    ) -> PortiaRecord:
        journal = self._load_operation_reference(value, description="resolving operation")
        data = journal.to_dict()
        if dict(resolved_by) != data.get("initiated_by"):
            raise WorkflowPrerequisiteError(
                "resolved_by is not the exact accepted resolving-operation actor"
            )
        if _timestamp(effective_at, "effective_at") < _timestamp(
            data.get("initiated_at"), "operation initiated_at"
        ):
            raise WorkflowPrerequisiteError("resolution predates its operation")
        if not _operation_owns_target(journal, target):
            raise WorkflowPrerequisiteError(
                "resolving operation does not own the exact Quarantine target"
            )
        return journal

    def release_quarantine(
        self,
        quarantine_id: str,
        *,
        expected_pointer: ContentFingerprint,
        resolving_operation: Mapping[str, object],
        satisfied_release_requirements: Sequence[str],
        effective_at: str,
        resolved_by: Mapping[str, object],
        finding_scope: Mapping[str, object] | None = None,
    ) -> SeriesState:
        """Append one released revision after proving every stored requirement."""
        current = self.store.load_current(quarantine_id)
        data = current.revision.to_dict()
        origin = data.get("origin")
        if not isinstance(origin, dict):
            raise PortiaCorruptionError("selected Quarantine origin is malformed")
        required = origin.get("release_requirements")
        if not isinstance(required, list):
            raise PortiaCorruptionError("selected release requirements are malformed")
        if data.get("state") == "released":
            resolution = data.get("resolution")
            if (
                isinstance(resolution, dict)
                and resolution.get("resolving_operation") == dict(resolving_operation)
                and resolution.get("satisfied_release_requirements")
                == list(satisfied_release_requirements)
                and resolution.get("effective_at") == effective_at
                and resolution.get("resolved_by") == dict(resolved_by)
            ):
                return current
            raise WorkflowPrerequisiteError("Quarantine is already released differently")
        if data.get("state") != "active":
            raise WorkflowPrerequisiteError("only an active Quarantine can be released")
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError("Quarantine current pointer changed before release")
        if list(satisfied_release_requirements) != required:
            raise WorkflowPrerequisiteError(
                "release must prove every exact stored release requirement"
            )
        target = data.get("target")
        journal = self._validate_resolution_operation(
            resolving_operation,
            resolved_by=resolved_by,
            effective_at=effective_at,
            target=target,
        )
        if journal.to_dict().get("operation_kind") != "repair_operation":
            raise WorkflowPrerequisiteError(
                "state reconciliation requires a completed repair_operation"
            )
        supporting = origin.get("supporting_finding_keys")
        if not isinstance(supporting, list) or any(
            not isinstance(item, str) for item in supporting
        ):
            raise PortiaCorruptionError("supporting finding keys are malformed")
        supporting_keys = cast(list[str], supporting)
        resolved_keys: list[str] = []
        remaining_keys: list[str] = []
        if "integrity_scan_clean" in required:
            if finding_scope is None:
                raise WorkflowPrerequisiteError(
                    "integrity_scan_clean requires exact current integrity authority"
                )
            current_findings = self._current_findings(finding_scope)
            current_keys = {
                str(finding.to_dict().get("finding_key"))
                for finding in current_findings
            }
            remaining_keys = [key for key in supporting_keys if key in current_keys]
            resolved_keys = [key for key in supporting_keys if key not in current_keys]
            if current_findings:
                raise WorkflowPrerequisiteError(
                    "current complete Integrity Finding generation is not clean"
                )
        elif supporting_keys:
            raise WorkflowPrerequisiteError(
                "supporting findings cannot be resolved without integrity_scan_clean"
            )
        applied = _timestamp(origin.get("applied_at"), "applied_at")
        if _timestamp(effective_at, "effective_at") < applied:
            raise WorkflowPrerequisiteError("release predates Quarantine application")
        prior = data.get("quarantine_revision")
        if not isinstance(prior, int):
            raise PortiaCorruptionError("selected Quarantine revision is malformed")
        successor: dict[str, Any] = deepcopy(data)
        successor.update(
            {
                "quarantine_revision": prior + 1,
                "previous_quarantine_revision": prior,
                "state": "released",
                "resolution": {
                    "kind": "release",
                    "prior_revision": prior,
                    "resolving_operation": deepcopy(dict(resolving_operation)),
                    "satisfied_release_requirements": list(
                        satisfied_release_requirements
                    ),
                    "resolved_finding_keys": resolved_keys,
                    "remaining_finding_keys": remaining_keys,
                    "effective_at": effective_at,
                    "resolved_by": deepcopy(dict(resolved_by)),
                },
                "created_at": effective_at,
            }
        )
        record = parse_portia_record("quarantine_record", "2", successor)
        return self.store.append(
            record,
            self._pointer(quarantine_id, prior + 1),
            expected_pointer=expected_pointer,
        )

    def supersede_quarantine(
        self,
        quarantine_id: str,
        *,
        expected_pointer: ContentFingerprint,
        successor_quarantine: Mapping[str, object],
        resolving_operation: Mapping[str, object],
        rationale: str,
        effective_at: str,
        resolved_by: Mapping[str, object],
    ) -> SeriesState:
        """Append an explicit supersession by one exact active successor series."""
        current = self.store.load_current(quarantine_id)
        data = current.revision.to_dict()
        if data.get("state") == "superseded":
            resolution = data.get("resolution")
            if (
                isinstance(resolution, dict)
                and resolution.get("successor_quarantine")
                == dict(successor_quarantine)
                and resolution.get("resolving_operation") == dict(resolving_operation)
                and resolution.get("effective_at") == effective_at
                and resolution.get("resolved_by") == dict(resolved_by)
            ):
                return current
            raise WorkflowPrerequisiteError("Quarantine is already superseded differently")
        if data.get("state") != "active":
            raise WorkflowPrerequisiteError("only an active Quarantine can be superseded")
        if current.pointer_fingerprint != expected_pointer:
            raise PortiaConflictError("Quarantine current pointer changed before supersession")
        successor_ref = dict(successor_quarantine)
        if set(successor_ref) != {
            "quarantine_id",
            "quarantine_revision",
            "contract_version",
        } or successor_ref.get("contract_version") != "2":
            raise WorkflowPrerequisiteError(
                "successor Quarantine reference is not exact quarantine_record@2"
            )
        successor_id = successor_ref.get("quarantine_id")
        successor_revision = successor_ref.get("quarantine_revision")
        if not isinstance(successor_id, str) or successor_id == quarantine_id:
            raise WorkflowPrerequisiteError("Quarantine cannot supersede itself")
        successor_current = self.store.load_current(successor_id)
        successor_data = successor_current.revision.to_dict()
        if (
            successor_data.get("quarantine_revision") != successor_revision
            or successor_data.get("state") != "active"
        ):
            raise WorkflowPrerequisiteError(
                "successor is not the exact active selected Quarantine revision"
            )
        old_target = data.get("target")
        new_target = successor_data.get("target")
        if not quarantine_applies(old_target, new_target):
            raise WorkflowPrerequisiteError(
                "successor target is not an explicit equal-or-narrower containment"
            )
        old_effects = data.get("effects")
        new_effects = successor_data.get("effects")
        if not isinstance(old_effects, list) or not isinstance(new_effects, list):
            raise PortiaCorruptionError("Quarantine effects are malformed")
        if not set(new_effects).issubset(old_effects):
            raise WorkflowPrerequisiteError(
                "successor cannot silently broaden Quarantine effects"
            )
        self._validate_resolution_operation(
            resolving_operation,
            resolved_by=resolved_by,
            effective_at=effective_at,
            target=old_target,
        )
        origin = data.get("origin")
        if not isinstance(origin, dict):
            raise PortiaCorruptionError("selected Quarantine origin is malformed")
        if _timestamp(effective_at, "effective_at") < _timestamp(
            origin.get("applied_at"), "applied_at"
        ):
            raise WorkflowPrerequisiteError("supersession predates application")
        rationale_value = _bounded_detail(rationale, "rationale", optional=False)
        assert rationale_value is not None
        prior = data.get("quarantine_revision")
        if not isinstance(prior, int):
            raise PortiaCorruptionError("selected Quarantine revision is malformed")
        successor: dict[str, Any] = deepcopy(data)
        successor.update(
            {
                "quarantine_revision": prior + 1,
                "previous_quarantine_revision": prior,
                "state": "superseded",
                "resolution": {
                    "kind": "supersede",
                    "prior_revision": prior,
                    "resolving_operation": deepcopy(dict(resolving_operation)),
                    "successor_quarantine": successor_ref,
                    "rationale": rationale_value,
                    "effective_at": effective_at,
                    "resolved_by": deepcopy(dict(resolved_by)),
                },
                "created_at": effective_at,
            }
        )
        record = parse_portia_record("quarantine_record", "2", successor)
        return self.store.append(
            record,
            self._pointer(quarantine_id, prior + 1),
            expected_pointer=expected_pointer,
        )
