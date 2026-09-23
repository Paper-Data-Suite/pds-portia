"""Operational recovery, Quarantine, and Integrity attention for Issue #49."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

from portia.attention.models import (
    OpaqueAttentionSourceRef,
    PortiaAttentionContext,
    PortiaAttentionItem,
    PortiaAttentionQuery,
    PortiaAttentionScope,
)
from portia.attention.taxonomy import require_attention_definition
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import (
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaQuarantinedError,
)
from portia.storage.quarantine import QuarantineGuard, quarantine_applies
from portia.storage.series import OperationJournalStore, SeriesState
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.integrity import IntegrityWorkflowService
from portia.workflows.recovery import RecoveryWorkflowService

_TERMINAL_RECOVERY_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {"absent", "terminal_consistent"}
)
_INTEGRITY_CONFLICT_CODES: Final[frozenset[str]] = frozenset(
    {
        "selected_history_ambiguous",
        "multiple_current_representations",
        "replacement_frontier_ambiguous",
        "dependency_declaration_conflict",
        "dependency_target_resolution_ambiguous",
        "duplicate_current_identity",
        "conflicting_exact_identity",
        "actor_contact_preference_conflict",
    }
)
_INTEGRITY_REVIEW_CODES: Final[frozenset[str]] = frozenset(
    {
        "recovery_required",
        "canonical_path_mismatch",
        "content_digest_mismatch",
        "removal_reconciliation_broken",
        "payload_present_after_removal",
        "removal_certificate_without_target_history",
    }
)


def _query_wants_code(query: PortiaAttentionQuery, code: str) -> bool:
    definition = require_attention_definition(code)
    if query.attention_codes and code not in query.attention_codes:
        return False
    if (
        query.attention_classes
        and definition.attention_class not in query.attention_classes
    ):
        return False
    return True


def _work_target(work: ExactPortiaWorkRef) -> dict[str, object]:
    return {"kind": "work", "work_ref": work.to_dict()}


def _class_target(class_id: str) -> dict[str, object]:
    return {"kind": "class", "class_id": class_id}


def _exact_work_matches(value: object, work: ExactPortiaWorkRef) -> bool:
    return isinstance(value, Mapping) and dict(value) == work.to_dict()


def _target_belongs_to_work(target: object, work: ExactPortiaWorkRef) -> bool:
    """Return whether one exact target is in or covers the requested work."""
    requested = _work_target(work)
    if quarantine_applies(target, requested):
        return True
    if not isinstance(target, Mapping):
        return False

    kind = target.get("kind")
    if kind == "work_record":
        composite = target.get("work_record_ref")
        return (
            isinstance(composite, Mapping)
            and _exact_work_matches(composite.get("work_ref"), work)
        )

    if kind == "derived_projection":
        scope = target.get("projection_scope")
        if not isinstance(scope, Mapping):
            return False
        scope_kind = scope.get("scope")
        if scope_kind == "work":
            return _exact_work_matches(scope.get("work_ref"), work)
        if scope_kind == "class":
            return scope.get("class_id") == work.class_id
        if scope_kind == "workspace":
            return True

    return False


def _target_belongs_to_class(target: object, class_id: str) -> bool:
    """Return whether one exact operational target belongs to a class."""
    if not isinstance(target, Mapping):
        return False
    kind = target.get("kind")
    if kind == "class":
        return target.get("class_id") == class_id
    if kind == "work":
        work = target.get("work_ref")
        return isinstance(work, Mapping) and work.get("class_id") == class_id
    if kind == "work_record":
        composite = target.get("work_record_ref")
        work = (
            composite.get("work_ref")
            if isinstance(composite, Mapping)
            else None
        )
        return isinstance(work, Mapping) and work.get("class_id") == class_id
    if kind == "derived_projection":
        scope = target.get("projection_scope")
        if not isinstance(scope, Mapping):
            return False
        if scope.get("scope") == "class":
            return scope.get("class_id") == class_id
        if scope.get("scope") == "work":
            work = scope.get("work_ref")
            return (
                isinstance(work, Mapping)
                and work.get("class_id") == class_id
            )
    return False


def _operation_targets(
    journal_data: Mapping[str, object],
) -> tuple[object, ...]:
    affected = journal_data.get("affected_targets")
    if not isinstance(affected, list):
        raise PortiaCorruptionError(
            "selected Operation Journal affected_targets is malformed"
        )
    return (journal_data.get("primary_target"), *affected)


def _operation_applies_to_work(
    journal_data: Mapping[str, object],
    work: ExactPortiaWorkRef,
) -> bool:
    return any(
        _target_belongs_to_work(target, work)
        for target in _operation_targets(journal_data)
    )


def _operation_applies_to_class(
    journal_data: Mapping[str, object],
    class_id: str,
) -> bool:
    return any(
        _target_belongs_to_class(target, class_id)
        for target in _operation_targets(journal_data)
    )


class UnknownIntegrityAttentionCodeError(WorkflowPrerequisiteError):
    """A current finding code has no frozen native attention meaning."""


def _integrity_attention_code(code: object) -> str:
    if not isinstance(code, str):
        raise PortiaCorruptionError(
            "current Integrity Finding has no bounded code"
        )
    if code in _INTEGRITY_CONFLICT_CODES:
        return "portia_integrity_conflict"
    if code in _INTEGRITY_REVIEW_CODES:
        return "portia_integrity_review_required"
    raise UnknownIntegrityAttentionCodeError(
        "current Integrity Finding code has no native attention classification"
    )


def _quarantine_reason_codes(data: Mapping[str, object]) -> tuple[str, ...]:
    reason = data.get("reason")
    effects = data.get("effects")
    if not isinstance(reason, str) or not isinstance(effects, list):
        raise PortiaCorruptionError(
            "active Quarantine has malformed bounded reason/effect state"
        )
    if not all(isinstance(effect, str) for effect in effects):
        raise PortiaCorruptionError(
            "active Quarantine effects contain an unsupported value"
        )
    return (
        f"reason_{reason}",
        *(f"effect_{effect}" for effect in sorted(effects)),
    )


def _context(scope: PortiaAttentionScope) -> PortiaAttentionContext:
    if scope.kind == "work":
        assert scope.work_ref is not None
        return PortiaAttentionContext(
            class_id=scope.work_ref.class_id,
            work_ref=scope.work_ref,
        )
    if scope.kind == "class":
        assert scope.class_id is not None
        return PortiaAttentionContext(class_id=scope.class_id)
    return PortiaAttentionContext()


class OperationalAttentionSourceService:
    """Read-only operational attention in explicit work/class/workspace scope."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        quarantine: QuarantineGuard | None = None,
    ) -> None:
        self.root = Path(workspace_root)
        self.quarantine = quarantine or QuarantineGuard(self.root)
        self.operations = OperationJournalStore(self.root)
        self.recovery = RecoveryWorkflowService(
            self.root,
            quarantine=self.quarantine,
        )
        self.integrity = IntegrityWorkflowService(
            self.root,
            quarantine=self.quarantine,
        )

    def _selected_operation(
        self,
        operation_id: str,
    ) -> SeriesState | None:
        try:
            return self.operations.load_current(operation_id)
        except PortiaNotFoundError:
            return None

    def operation_ids_for_scope(
        self,
        scope: PortiaAttentionScope,
        *,
        selected_only: bool,
    ) -> tuple[str, ...]:
        """Return exact operation IDs attributable to one explicit scope."""
        selected: list[str] = []
        for operation_id in self.operations.series_ids():
            current = self._selected_operation(operation_id)
            if current is None:
                if scope.kind == "workspace" and not selected_only:
                    selected.append(operation_id)
                continue

            if scope.kind == "workspace":
                selected.append(operation_id)
                continue

            data = current.revision.to_dict()
            if scope.kind == "class":
                assert scope.class_id is not None
                if _operation_applies_to_class(data, scope.class_id):
                    selected.append(operation_id)
                continue

            assert scope.work_ref is not None
            if _operation_applies_to_work(data, scope.work_ref):
                selected.append(operation_id)

        return tuple(selected)

    def _operation_id_belongs_to_scope(
        self,
        operation_id: str,
        scope: PortiaAttentionScope,
    ) -> bool:
        current = self._selected_operation(operation_id)
        if current is None:
            return False
        if scope.kind == "workspace":
            return True
        data = current.revision.to_dict()
        if scope.kind == "class":
            assert scope.class_id is not None
            return _operation_applies_to_class(data, scope.class_id)
        assert scope.work_ref is not None
        return _operation_applies_to_work(data, scope.work_ref)

    def _quarantine_belongs_to_scope(
        self,
        data: Mapping[str, object],
        scope: PortiaAttentionScope,
    ) -> bool:
        if scope.kind == "workspace":
            return True

        target = data.get("target")
        if scope.kind == "work":
            assert scope.work_ref is not None
            if _target_belongs_to_work(target, scope.work_ref):
                return True
        else:
            assert scope.class_id is not None
            if quarantine_applies(target, _class_target(scope.class_id)):
                return True
            if _target_belongs_to_class(target, scope.class_id):
                return True

        if not isinstance(target, Mapping):
            return False
        if target.get("kind") == "operation":
            operation_ref = target.get("operation_ref")
            operation_id = (
                operation_ref.get("operation_id")
                if isinstance(operation_ref, Mapping)
                else None
            )
            if not isinstance(operation_id, str):
                raise PortiaCorruptionError(
                    "operational Quarantine target has malformed operation identity"
                )
            return self._operation_id_belongs_to_scope(operation_id, scope)

        if target.get("kind") == "derived_projection":
            projection_scope = target.get("projection_scope")
            if (
                isinstance(projection_scope, Mapping)
                and projection_scope.get("scope") == "operation"
            ):
                operation_ref = projection_scope.get("operation_ref")
                operation_id = (
                    operation_ref.get("operation_id")
                    if isinstance(operation_ref, Mapping)
                    else None
                )
                if not isinstance(operation_id, str):
                    raise PortiaCorruptionError(
                        "operation-scoped projection Quarantine is malformed"
                    )
                return self._operation_id_belongs_to_scope(
                    operation_id,
                    scope,
                )
        return False

    def recovery_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        if not _query_wants_code(query, "portia_recovery_required"):
            return ()

        context = _context(query.scope)
        operation_ids = self.operation_ids_for_scope(
            query.scope,
            selected_only=query.scope.kind != "workspace",
        )
        items: list[PortiaAttentionItem] = []
        for operation_id in operation_ids:
            assessment = self.recovery.assess(operation_id)
            if assessment.disposition in _TERMINAL_RECOVERY_DISPOSITIONS:
                continue
            reasons = [f"disposition_{assessment.disposition}"]
            if assessment.state is not None:
                reasons.append(f"state_{assessment.state}")
            items.append(
                PortiaAttentionItem(
                    code="portia_recovery_required",
                    source_ref=OpaqueAttentionSourceRef(
                        kind="recovery_scope",
                        identifier=operation_id,
                    ),
                    context=context,
                    reason_codes=tuple(reasons),
                )
            )
        return tuple(items)

    def quarantine_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        if not _query_wants_code(query, "portia_quarantine_active"):
            return ()

        context = _context(query.scope)
        items: list[PortiaAttentionItem] = []
        for record in self.quarantine.active_records():
            data = record.to_dict()
            if not self._quarantine_belongs_to_scope(data, query.scope):
                continue
            quarantine_id = data.get("quarantine_id")
            if not isinstance(quarantine_id, str):
                raise PortiaCorruptionError(
                    "active Quarantine has no opaque identity"
                )
            items.append(
                PortiaAttentionItem(
                    code="portia_quarantine_active",
                    source_ref=OpaqueAttentionSourceRef(
                        kind="quarantine",
                        identifier=quarantine_id,
                    ),
                    context=context,
                    reason_codes=_quarantine_reason_codes(data),
                )
            )
        return tuple(items)

    def integrity_items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        wants_conflict = _query_wants_code(
            query,
            "portia_integrity_conflict",
        )
        wants_review = _query_wants_code(
            query,
            "portia_integrity_review_required",
        )
        if not wants_conflict and not wants_review:
            return ()

        context = _context(query.scope)
        items: list[PortiaAttentionItem] = []
        for operation_id in self.operation_ids_for_scope(
            query.scope,
            selected_only=True,
        ):
            scope = self.integrity.operation_scope(operation_id)
            if not self.integrity.has_current_finding_projection(scope):
                continue
            try:
                findings = self.integrity.current_findings(scope)
            except PortiaQuarantinedError:
                # Containment is reported independently by the Quarantine source.
                continue

            for finding in findings:
                data = finding.to_dict()
                attention_code = _integrity_attention_code(data.get("code"))
                if (
                    attention_code == "portia_integrity_conflict"
                    and not wants_conflict
                ):
                    continue
                if (
                    attention_code == "portia_integrity_review_required"
                    and not wants_review
                ):
                    continue

                finding_key = data.get("finding_key")
                evaluation_key = data.get("evaluation_key")
                finding_code = data.get("code")
                if not all(
                    isinstance(value, str)
                    for value in (
                        finding_key,
                        evaluation_key,
                        finding_code,
                    )
                ):
                    raise PortiaCorruptionError(
                        "current Integrity Finding identity is malformed"
                    )
                assert isinstance(finding_key, str)
                assert isinstance(evaluation_key, str)
                assert isinstance(finding_code, str)

                if self.integrity.is_finding_presentation_suppressed(
                    scope,
                    finding_key=finding_key,
                    evaluation_key=evaluation_key,
                    evaluated_at=query.as_of.text,
                    surface="teacher_dashboard",
                    audience="local_teacher",
                ):
                    continue

                items.append(
                    PortiaAttentionItem(
                        code=attention_code,
                        source_ref=OpaqueAttentionSourceRef(
                            kind="integrity_finding",
                            identifier=finding_key,
                        ),
                        context=context,
                        reason_codes=(f"finding_{finding_code}",),
                    )
                )
        return tuple(items)

    def items(
        self,
        query: PortiaAttentionQuery,
    ) -> tuple[PortiaAttentionItem, ...]:
        """Return bounded operational items without repair or mutation."""
        return (
            *self.recovery_items(query),
            *self.quarantine_items(query),
            *self.integrity_items(query),
        )
