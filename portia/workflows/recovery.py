"""Bounded workflow recovery over durable Operation Journal evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.storage.fingerprint import ContentFingerprint
from portia.storage.integrity import PersistenceFinding
from portia.storage.recovery import OperationRecovery, OperationRecoveryAssessment
from portia.storage.series import RecoveryObservation
from portia.workflows.errors import WorkflowPrerequisiteError


@dataclass(frozen=True, slots=True)
class RecoveryWorkflowAssessment:
    """Application-level view of one exact operation recovery assessment."""

    operation_id: str
    state: str | None
    disposition: str
    series: RecoveryObservation
    findings: tuple[PersistenceFinding, ...]


def _workflow_assessment(
    assessment: OperationRecoveryAssessment,
) -> RecoveryWorkflowAssessment:
    return RecoveryWorkflowAssessment(
        operation_id=assessment.operation_id,
        state=assessment.state,
        disposition=assessment.disposition,
        series=assessment.series,
        findings=assessment.findings,
    )


class RecoveryWorkflowService:
    """Explicit recovery surface over the accepted #38 storage authority."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self._recovery = OperationRecovery(self.root)

    def assess(self, operation_id: str) -> RecoveryWorkflowAssessment:
        """Inspect one operation without mutating durable recovery state."""
        return _workflow_assessment(self._recovery.assess(operation_id))

    def restore_exact_orphan_pointer(
        self,
        operation_id: str,
        *,
        expected_pointer: ContentFingerprint,
    ) -> RecoveryWorkflowAssessment:
        """Select the one exact linear orphan successor and verify the result.

        This is intentionally narrower than generic resume/repair.  The storage
        recovery authority remains responsible for predecessor, intent, pointer,
        and durable-byte validation.  Ambiguous or branched state stays fail-closed.
        """
        assessment = self.assess(operation_id)
        if assessment.disposition != "restore_pointer_candidate":
            raise WorkflowPrerequisiteError(
                "operation is not a restore_pointer_candidate"
            )
        self._recovery.select_exact_orphan_successor(
            operation_id,
            expected_pointer=expected_pointer,
        )
        return self.assess(operation_id)
