"""Bounded workflow integrity evaluation over accepted storage evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.storage.fingerprint import ContentFingerprint
from portia.storage.integrity import (
    PersistenceFinding,
    validate_operation_durable_state,
)
from portia.storage.series import OperationJournalStore
from portia.workflows.errors import WorkflowPrerequisiteError


@dataclass(frozen=True, slots=True)
class OperationIntegrityEvaluation:
    """Persistence-integrity evidence for one exact selected journal revision."""

    operation_id: str
    journal_revision: int
    journal_fingerprint: ContentFingerprint
    findings: tuple[PersistenceFinding, ...]


class IntegrityWorkflowService:
    """Application boundary for deterministic Portia integrity evaluation."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self._operations = OperationJournalStore(self.root)

    def evaluate_operation_persistence(
        self,
        operation_id: str,
    ) -> OperationIntegrityEvaluation:
        """Evaluate the exact current operation revision without mutating state.

        Recovery topology is deliberately checked before and after evaluation.
        A missing pointer, orphan successor, or other non-current series must be
        handled through recovery rather than silently evaluating a stale head.
        """
        before = self._operations.inspect_recovery(operation_id)
        if before.disposition != "current":
            raise WorkflowPrerequisiteError(
                "integrity evaluation requires an unambiguous current operation "
                "journal; resolve recovery state first"
            )

        current = self._operations.load_current(operation_id)
        revision_value = current.revision.to_dict().get("journal_revision")
        if not isinstance(revision_value, int) or isinstance(revision_value, bool):
            raise WorkflowPrerequisiteError(
                "selected operation journal has no valid journal revision"
            )

        findings = validate_operation_durable_state(self.root, current.revision)

        after = self._operations.inspect_recovery(operation_id)
        if (
            after.disposition != "current"
            or after.selected_revision != revision_value
        ):
            raise WorkflowPrerequisiteError(
                "operation recovery state changed during integrity evaluation"
            )
        readback = self._operations.load_current(operation_id)
        if (
            readback.revision_fingerprint != current.revision_fingerprint
            or readback.pointer_fingerprint != current.pointer_fingerprint
        ):
            raise WorkflowPrerequisiteError(
                "operation current selection changed during integrity evaluation"
            )

        return OperationIntegrityEvaluation(
            operation_id=operation_id,
            journal_revision=revision_value,
            journal_fingerprint=current.revision_fingerprint,
            findings=findings,
        )
