"""Typed application-service failures for Event-family workflows."""

from __future__ import annotations

from portia.validation import ApplicationFinding


class PortiaWorkflowError(RuntimeError):
    """Base class for failures introduced at the workflow boundary."""


class WorkflowValidationError(PortiaWorkflowError):
    """The complete proposed in-memory graph was rejected."""

    def __init__(self, findings: tuple[ApplicationFinding, ...]) -> None:
        self.findings = findings
        codes = ", ".join(sorted({finding.code for finding in findings}))
        super().__init__(f"proposed record graph is invalid: {codes}")


class WorkflowOwnershipError(PortiaWorkflowError):
    """A typed record/reference names a different exact owner."""


class WorkflowPrerequisiteError(PortiaWorkflowError):
    """A current-use or activation authority is absent or ineligible."""
