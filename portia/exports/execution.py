"""Final revalidation and coordinated teacher-reference export execution.

Issue #51 Slice 6 deliberately accepts one exact reviewed preparation and never
silently calls preparation again.  All durable artifact/provenance publication
continues through the specialized Issue #88 persistence and recovery seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal

from portia.exports.discovery import TeacherReferenceScopeDiscoveryService
from portia.exports.inventory import TeacherReferenceSourceInventoryService
from portia.exports.policy import (
    TEACHER_REFERENCE_EXPORT_POLICY,
    TeacherReferenceExportPolicy,
    require_teacher_reference_generation_authorized,
)
from portia.exports.preparation import TeacherReferenceExportPreparation
from portia.exports.projection import (
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionDecision,
    TeacherReferenceProjectionService,
)
from portia.exports.rendering import TeacherReferenceHtmlRenderer
from portia.models import ExplicitOffsetTimestamp, parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.storage import (
    ContentFingerprint,
    OperationJournalStore,
    PortiaCorruptionError,
    PortiaLockError,
    PortiaOperationPartialCommitError,
    PortiaRecoveryRequiredError,
    PortiaRepository,
    PortiaStorageError,
    fingerprint_bytes,
)
from portia.storage.deliberate_export_operations import (
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_committed_reference,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.deliberate_export_persistence import (
    commit_deliberate_export_candidates,
    stage_deliberate_export_candidates,
)
from portia.storage.deliberate_export_recovery_actions import (
    finalize_deliberate_export,
    recover_deliberate_export_committed_revision,
)
from portia.storage.io import read_bytes, read_json
from portia.storage.locks import validate_operation_lock_application
from portia.storage.operation_journal import validate_operation_journal_application
from portia.storage.paths import (
    lock_path,
    operation_revision_path,
    operation_root,
    resolve_workspace_relative,
    validate_workspace_relative_path,
)

TEACHER_REFERENCE_CONFIRMATION: Final[str] = "EXPORT"

PreparedStateDetail = Literal[
    "policy_changed",
    "source_or_currentness_changed",
    "projection_changed",
    "inventory_changed",
    "authorization_changed",
    "renderer_changed",
    "candidate_changed",
    "output_preflight_changed",
]
ExecutionFailureCode = Literal[
    "confirmation_required",
    "prepared_state_changed",
    "execution_conflict",
    "recovery_required",
]


@dataclass(frozen=True, slots=True)
class TeacherReferencePreparedStateCheck:
    """Read-only result of final prepared-state revalidation."""

    is_current: bool
    detail_code: PreparedStateDetail | None = None

    def __post_init__(self) -> None:
        if self.is_current and self.detail_code is not None:
            raise PortiaLocalValidationError(
                "current teacher-reference preparation cannot carry a stale detail"
            )
        if not self.is_current and self.detail_code is None:
            raise PortiaLocalValidationError(
                "stale teacher-reference preparation requires a stable detail code"
            )


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportExecutionFailure:
    """Stable task-level failure without inventing recovery conclusions."""

    code: ExecutionFailureCode
    message: str
    export_id: str
    operation_id: str
    preparation_digest: str
    durable_state_may_exist: bool
    status: str = "failed"

    def __post_init__(self) -> None:
        if self.status != "failed" or not self.message:
            raise PortiaLocalValidationError(
                "teacher-reference execution failure must be explicit"
            )


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportExecutionSuccess:
    """Verified completed export result bound to the reviewed preparation."""

    export_id: str
    operation_id: str
    preparation_digest: str
    artifact_relative_path: str
    provenance_relative_path: str
    artifact_fingerprint: ContentFingerprint
    committed_journal_revision: int
    completed_journal_revision: int
    status: str = "completed"

    def __post_init__(self) -> None:
        if self.status != "completed":
            raise PortiaLocalValidationError(
                "teacher-reference success result must be completed"
            )
        if self.committed_journal_revision < 1:
            raise PortiaLocalValidationError(
                "teacher-reference success requires committed journal revision"
            )
        if self.completed_journal_revision != self.committed_journal_revision + 1:
            raise PortiaLocalValidationError(
                "teacher-reference completed revision must follow committed revision"
            )


TeacherReferenceExportExecutionResult = (
    TeacherReferenceExportExecutionSuccess | TeacherReferenceExportExecutionFailure
)


def _failure(
    preparation: TeacherReferenceExportPreparation,
    code: ExecutionFailureCode,
    message: str,
    *,
    durable_state_may_exist: bool,
) -> TeacherReferenceExportExecutionFailure:
    return TeacherReferenceExportExecutionFailure(
        code=code,
        message=message,
        export_id=preparation.export_id,
        operation_id=preparation.operation_id,
        preparation_digest=preparation.preparation_digest,
        durable_state_may_exist=durable_state_may_exist,
    )


def _manual_choices(
    decision: TeacherReferenceProjectionDecision,
) -> tuple[TeacherReferenceManualReviewChoice, ...]:
    choices: list[TeacherReferenceManualReviewChoice] = []
    for item in decision.items:
        if item.manual_resolution is None:
            continue
        if item.field_name is None:
            raise PortiaLocalValidationError(
                "manual teacher-reference resolution cannot be source-level"
            )
        choices.append(
            TeacherReferenceManualReviewChoice(
                item.source_ref,
                item.field_name,
                item.manual_resolution,
            )
        )
    return tuple(choices)


def _requested_operator_kind(preparation: TeacherReferenceExportPreparation) -> str:
    requested_by = preparation.deliberate_export.to_dict().get("requested_by")
    if not isinstance(requested_by, dict):
        raise PortiaLocalValidationError(
            "teacher-reference candidate lacks requested_by attribution"
        )
    value = requested_by.get("type")
    if not isinstance(value, str):
        raise PortiaLocalValidationError(
            "teacher-reference candidate lacks requester type"
        )
    return value


def _expected_policy(policy: TeacherReferenceExportPolicy) -> dict[str, object]:
    return {
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
    }


class TeacherReferenceExportExecutionService:
    """Revalidate and execute one exact reviewed preparation through Issue #88."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        repository: PortiaRepository | None = None,
        discovery_service: TeacherReferenceScopeDiscoveryService | None = None,
        projection_service: TeacherReferenceProjectionService | None = None,
        inventory_service: TeacherReferenceSourceInventoryService | None = None,
        renderer: TeacherReferenceHtmlRenderer | None = None,
        policy: TeacherReferenceExportPolicy = TEACHER_REFERENCE_EXPORT_POLICY,
    ) -> None:
        self.workspace_root = Path(workspace_root)
        self.repository = repository or PortiaRepository(self.workspace_root)
        self.discovery_service = discovery_service or TeacherReferenceScopeDiscoveryService(
            self.workspace_root,
            repository=self.repository,
        )
        self.projection_service = projection_service or TeacherReferenceProjectionService(
            self.workspace_root,
            repository=self.repository,
        )
        self.inventory_service = inventory_service or TeacherReferenceSourceInventoryService(
            self.workspace_root,
            repository=self.repository,
        )
        self.renderer = renderer or TeacherReferenceHtmlRenderer()
        self.policy = policy

    def _stale(self, detail: PreparedStateDetail) -> TeacherReferencePreparedStateCheck:
        return TeacherReferencePreparedStateCheck(False, detail)

    def _output_preflight_is_clear(
        self,
        preparation: TeacherReferenceExportPreparation,
    ) -> bool:
        validate_workspace_relative_path(preparation.artifact_relative_path)
        validate_workspace_relative_path(preparation.provenance_relative_path)
        artifact = resolve_workspace_relative(
            self.workspace_root,
            preparation.artifact_relative_path,
        )
        provenance = resolve_workspace_relative(
            self.workspace_root,
            preparation.provenance_relative_path,
        )
        if artifact.exists() or artifact.is_symlink():
            return False
        if provenance.exists() or provenance.is_symlink():
            return False
        if operation_root(self.workspace_root, preparation.operation_id).exists():
            return False
        lock_id = preparation.operation_lock.field("lock_id")
        if not isinstance(lock_id, str):
            return False
        lock_candidate = lock_path(self.workspace_root, lock_id)
        return not lock_candidate.exists() and not lock_candidate.is_symlink()

    def revalidate(
        self,
        preparation: TeacherReferenceExportPreparation,
    ) -> TeacherReferencePreparedStateCheck:
        """Recompute material state only to compare with the reviewed preparation."""

        if not isinstance(preparation, TeacherReferenceExportPreparation):
            raise TypeError("preparation must be a TeacherReferenceExportPreparation")

        export_data = preparation.deliberate_export.to_dict()
        if export_data.get("projection_policy") != _expected_policy(self.policy):
            return self._stale("policy_changed")

        try:
            discovery = self.discovery_service.discover(preparation.decision.discovery.scope)
            pending = self.projection_service.project(discovery)
            original_review = preparation.decision.manual_review
            if original_review.status == "resolved":
                if original_review.reviewed_at is None or original_review.reviewed_by is None:
                    return self._stale("projection_changed")
                fresh = self.projection_service.resolve_manual_review(
                    pending,
                    _manual_choices(preparation.decision),
                    reviewed_at=original_review.reviewed_at,
                    reviewed_by=original_review.reviewed_by.to_dict(),
                )
            else:
                fresh = pending
        except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError):
            return self._stale("source_or_currentness_changed")

        if not fresh.is_final:
            return self._stale("projection_changed")
        if (
            fresh.projection_decision_digest
            != preparation.decision.projection_decision_digest
            or fresh.disposition_summary.to_dict()
            != preparation.decision.disposition_summary.to_dict()
            or fresh.manual_review.to_export_dict()
            != preparation.decision.manual_review.to_export_dict()
        ):
            return self._stale("projection_changed")

        try:
            inventory = self.inventory_service.author(fresh)
        except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError):
            return self._stale("source_or_currentness_changed")
        if inventory.to_dict() != preparation.inventory.to_dict():
            return self._stale("inventory_changed")

        source_kinds = tuple(
            sorted({str(entry["source_kind"]) for entry in inventory.entries})
        )
        try:
            rule = require_teacher_reference_generation_authorized(
                projection_purpose=fresh.discovery.scope.projection_purpose,
                work_kind=fresh.discovery.scope.work_ref.work_kind,
                work_contract_version=fresh.discovery.scope.work_ref.contract_version,
                operator_kind=_requested_operator_kind(preparation),
                source_kinds=source_kinds,
            )
        except (PortiaLocalValidationError, TypeError, ValueError):
            return self._stale("authorization_changed")
        authorization = export_data.get("authorization")
        if not isinstance(authorization, dict):
            return self._stale("authorization_changed")
        if (
            authorization.get("kind") != "policy_rule"
            or authorization.get("result") != "authorized"
            or authorization.get("policy_rule_id") != rule.policy_rule_id
            or authorization.get("policy_rule_version") != rule.policy_rule_version
            or authorization.get("policy_rule_digest") != rule.policy_rule_digest
        ):
            return self._stale("authorization_changed")

        try:
            artifact = self.renderer.render(fresh, inventory)
        except (PortiaLocalValidationError, TypeError, ValueError):
            return self._stale("renderer_changed")
        if (
            artifact.content != preparation.artifact.content
            or artifact.fingerprint != preparation.artifact.fingerprint
            or artifact.renderer_id != preparation.artifact.renderer_id
            or artifact.output_format != preparation.artifact.output_format
            or artifact.media_type != preparation.artifact.media_type
        ):
            return self._stale("renderer_changed")

        expected_scope: dict[str, object] = {
            "scope": "work",
            "work_ref": fresh.discovery.scope.work_ref.to_dict(),
        }
        if (
            export_data.get("projection_purpose")
            != fresh.discovery.scope.projection_purpose
            or export_data.get("export_scope") != expected_scope
            or export_data.get("source_inventory") != inventory.to_dict()
            or export_data.get("projection_decision_algorithm")
            != fresh.projection_decision_algorithm
            or export_data.get("projection_decision_digest")
            != fresh.projection_decision_digest
            or export_data.get("disposition_summary")
            != fresh.disposition_summary.to_dict()
            or export_data.get("manual_review") != fresh.manual_review.to_export_dict()
        ):
            return self._stale("candidate_changed")
        focal = fresh.discovery.scope.focal_subject_ref
        if focal is None:
            if "focal_subject_ref" in export_data:
                return self._stale("candidate_changed")
        elif export_data.get("focal_subject_ref") != focal.to_dict():
            return self._stale("candidate_changed")

        output = export_data.get("output")
        expected_output = {
            "format": artifact.output_format,
            "media_type": artifact.media_type,
            "workspace_relative_path": preparation.artifact_relative_path,
            "byte_length": artifact.byte_length,
            "sha256_digest": artifact.representation_digest,
        }
        if output != expected_output:
            return self._stale("candidate_changed")

        try:
            validate_operation_journal_application(preparation.operation_journal)
            validate_operation_lock_application(preparation.operation_lock)
            validate_deliberate_export_lock_agreement(
                preparation.operation_journal,
                preparation.operation_lock,
            )
            validate_deliberate_export_candidate_reconciliation(
                preparation.operation_journal,
                preparation.deliberate_export,
            )
        except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError):
            return self._stale("candidate_changed")

        try:
            if not self._output_preflight_is_clear(preparation):
                return self._stale("output_preflight_changed")
        except (PortiaLocalValidationError, PortiaStorageError, TypeError, ValueError):
            return self._stale("output_preflight_changed")
        return TeacherReferencePreparedStateCheck(True)

    def execute(
        self,
        preparation: TeacherReferenceExportPreparation,
        *,
        confirmation: str,
        confirmed_preparation_digest: str,
        confirmed_at: str,
    ) -> TeacherReferenceExportExecutionResult:
        """Execute only the exact reviewed preparation after final revalidation."""

        if not isinstance(preparation, TeacherReferenceExportPreparation):
            raise TypeError("preparation must be a TeacherReferenceExportPreparation")
        if (
            confirmation != TEACHER_REFERENCE_CONFIRMATION
            or confirmed_preparation_digest != preparation.preparation_digest
        ):
            return _failure(
                preparation,
                "confirmation_required",
                "Export requires explicit EXPORT confirmation for the exact previewed preparation.",
                durable_state_may_exist=False,
            )
        try:
            confirmed = ExplicitOffsetTimestamp(confirmed_at)
            export_generated = preparation.deliberate_export.field("generated_at")
            if not isinstance(export_generated, str):
                raise PortiaLocalValidationError(
                    "teacher-reference candidate lacks generated_at"
                )
            generated = ExplicitOffsetTimestamp(export_generated)
            if confirmed.datetime < generated.datetime:
                raise PortiaLocalValidationError(
                    "teacher-reference confirmation cannot predate generation"
                )
        except (PortiaLocalValidationError, TypeError, ValueError):
            return _failure(
                preparation,
                "confirmation_required",
                "Export confirmation timestamp is invalid for the reviewed preparation.",
                durable_state_may_exist=False,
            )

        check = self.revalidate(preparation)
        if not check.is_current:
            return _failure(
                preparation,
                "prepared_state_changed",
                "The reviewed export preview is stale; create and review a new preview before exporting.",
                durable_state_may_exist=False,
            )

        persistence_started = False
        try:
            # Re-run the path preflight at the write boundary rather than trusting the
            # earlier read-only check across an arbitrary confirmation delay.
            if not self._output_preflight_is_clear(preparation):
                return _failure(
                    preparation,
                    "prepared_state_changed",
                    "The reviewed export destination changed; create a new preview.",
                    durable_state_may_exist=False,
                )

            store = OperationJournalStore(self.workspace_root)
            pointer = parse_portia_record(
                "operation_current_pointer",
                "1",
                {
                    "schema_version": "1",
                    "record_type": "operation_current_pointer",
                    "module_id": "portia",
                    "operation_id": preparation.operation_id,
                    "journal_revision": 1,
                },
            )
            persistence_started = True
            store.create(preparation.operation_journal, pointer)

            staged = stage_deliberate_export_candidates(
                self.workspace_root,
                preparation.operation_journal,
                artifact_bytes=preparation.artifact_bytes,
                export=preparation.deliberate_export,
            )
            commit_deliberate_export_candidates(
                self.workspace_root,
                preparation.operation_journal,
                staged,
                artifact_bytes=preparation.artifact_bytes,
                export=preparation.deliberate_export,
                lock=preparation.operation_lock,
            )

            recover_deliberate_export_committed_revision(
                self.workspace_root,
                preparation.operation_id,
                export=preparation.deliberate_export,
                observed_at=confirmed_at,
                committed_at=confirmed_at,
            )
            finalize_deliberate_export(
                self.workspace_root,
                preparation.operation_id,
                export=preparation.deliberate_export,
                lock=preparation.operation_lock,
            )
            return self._verify_completed(preparation)
        except PortiaOperationPartialCommitError:
            return _failure(
                preparation,
                "recovery_required",
                "Export execution became partially durable and requires exact operation recovery.",
                durable_state_may_exist=True,
            )
        except (PortiaRecoveryRequiredError, PortiaLockError):
            return _failure(
                preparation,
                "recovery_required",
                "Export operation state requires exact recovery before ordinary continuation.",
                durable_state_may_exist=True,
            )
        except PortiaStorageError:
            code: ExecutionFailureCode = (
                "recovery_required" if persistence_started else "execution_conflict"
            )
            return _failure(
                preparation,
                code,
                (
                    "Export operation state changed after confirmation and requires recovery."
                    if persistence_started
                    else "Export could not start because the exact operation state conflicted."
                ),
                durable_state_may_exist=persistence_started,
            )

    def _verify_completed(
        self,
        preparation: TeacherReferenceExportPreparation,
    ) -> TeacherReferenceExportExecutionSuccess:
        artifact_path = resolve_workspace_relative(
            self.workspace_root,
            preparation.artifact_relative_path,
        )
        provenance_path = resolve_workspace_relative(
            self.workspace_root,
            preparation.provenance_relative_path,
        )
        artifact_bytes = read_bytes(artifact_path)
        provenance_bytes = read_bytes(provenance_path)
        if (
            artifact_bytes != preparation.artifact_bytes
            or fingerprint_bytes(artifact_bytes) != preparation.artifact.fingerprint
            or provenance_bytes != preparation.provenance_bytes
        ):
            raise PortiaCorruptionError(
                "completed teacher-reference bytes differ from reviewed preparation"
            )

        committed_revision = planned_deliberate_export_commit_revision(
            preparation.operation_journal
        )
        raw, _content, _fingerprint = read_json(
            operation_revision_path(
                self.workspace_root,
                preparation.operation_id,
                committed_revision,
            )
        )
        committed = parse_portia_record("operation_journal", "4", raw)
        validate_deliberate_export_committed_reference(
            committed,
            preparation.deliberate_export,
        )

        current = OperationJournalStore(self.workspace_root).load_current(
            preparation.operation_id
        )
        current_data = current.revision.to_dict()
        completed_revision = committed_revision + 1
        if (
            current.revision.contract_version != "4"
            or current_data.get("state") != "completed"
            or current_data.get("journal_revision") != completed_revision
            or current_data.get("previous_journal_revision") != committed_revision
        ):
            raise PortiaCorruptionError(
                "teacher-reference operation did not finish at exact completed revision"
            )

        return TeacherReferenceExportExecutionSuccess(
            export_id=preparation.export_id,
            operation_id=preparation.operation_id,
            preparation_digest=preparation.preparation_digest,
            artifact_relative_path=preparation.artifact_relative_path,
            provenance_relative_path=preparation.provenance_relative_path,
            artifact_fingerprint=preparation.artifact.fingerprint,
            committed_journal_revision=committed_revision,
            completed_journal_revision=completed_revision,
        )


__all__ = [
    "TEACHER_REFERENCE_CONFIRMATION",
    "ExecutionFailureCode",
    "PreparedStateDetail",
    "TeacherReferenceExportExecutionFailure",
    "TeacherReferenceExportExecutionResult",
    "TeacherReferenceExportExecutionService",
    "TeacherReferenceExportExecutionSuccess",
    "TeacherReferencePreparedStateCheck",
]
