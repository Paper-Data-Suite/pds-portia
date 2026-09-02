"""Shared exact authority and graph handling for Support Process initiation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from portia.models import PortiaRecord, SupportProcessV1
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.quarantine import QuarantineGuard
from portia.storage.repository import PortiaRepository
from portia.validation import GraphValidationOptions, validate_record_graph
from portia.workflows.context import WorkflowContextAssembler
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
    WorkflowValidationError,
)

_LOCAL_INITIATION_KINDS = frozenset({"teacher_identified_need", "other"})
_UNRESOLVED_INITIATION_CODES = frozenset(
    {
        "PORTIA.GRAPH.UNRESOLVED_WORK_REFERENCE",
        "PORTIA.GRAPH.UNRESOLVED_EXACT_REFERENCE",
    }
)


def require_support_process_initiation_authority(
    workspace_root: str | Path,
    repository: PortiaRepository,
    quarantine: QuarantineGuard,
    contexts: WorkflowContextAssembler,
    record: PortiaRecord,
) -> None:
    """Resolve exactly the frozen initiating source without successor following."""
    if not isinstance(record, SupportProcessV1):
        raise WorkflowOwnershipError(
            "Support Process initiation authority requires support_process@1"
        )
    initiation = record.field("initiation")
    if not isinstance(initiation, Mapping):
        raise WorkflowOwnershipError("Support Process initiation is malformed")
    kind = initiation.get("kind")
    if kind in _LOCAL_INITIATION_KINDS:
        return
    if kind == "imported_history":
        raise WorkflowPrerequisiteError(
            "imported_history initiation requires import provenance and is not "
            "valid for the digital-entry workflow"
        )

    if kind == "event_context":
        from portia.workflows.events import EventWorkflowService

        event_reference = ExactPortiaWorkRef.from_dict(initiation.get("event_ref"))
        EventWorkflowService(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=contexts,
        ).resolve_exact(event_reference)
        return

    record_reference = ExactPortiaWorkRecordRef.from_dict(
        initiation.get("record_ref")
    )
    if kind == "review_context":
        from portia.workflows.reviews import ReviewWorkflowService

        ReviewWorkflowService(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=contexts,
        ).resolve_exact(record_reference)
        return
    if kind == "determination_context":
        from portia.workflows.determinations import DeterminationWorkflowService

        DeterminationWorkflowService(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=contexts,
        ).resolve_exact(record_reference)
        return
    if kind == "response_handoff":
        from portia.workflows.responses import ResponseWorkflowService

        ResponseWorkflowService(
            workspace_root,
            repository=repository,
            quarantine=quarantine,
            context_assembler=contexts,
        ).resolve_exact(record_reference)
        return
    if kind == "represented_request":
        if record_reference.record_ref.record_kind == "account":
            if record_reference.record_ref.contract_version != "1":
                raise WorkflowOwnershipError(
                    "support_process@1 represented_request permits account@1 only"
                )
            from portia.workflows.accounts import AccountWorkflowService

            AccountWorkflowService(
                workspace_root,
                repository=repository,
                quarantine=quarantine,
                context_assembler=contexts,
            ).resolve_exact(record_reference)
            return
        if record_reference.record_ref.record_kind == "communication":
            from portia.workflows.communications import CommunicationWorkflowService

            CommunicationWorkflowService(
                workspace_root,
                repository=repository,
                quarantine=quarantine,
                context_assembler=contexts,
            ).resolve_exact(record_reference)
            return
        raise WorkflowOwnershipError(
            "represented_request initiation must name an exact Account or "
            "Communication"
        )
    raise WorkflowOwnershipError(
        f"unsupported Support Process initiation kind {kind!r}"
    )


def validate_support_process_graph(
    contexts: WorkflowContextAssembler,
    records: Sequence[PortiaRecord],
    *,
    require_actor_current_use: bool = False,
) -> None:
    """Keep strict graph validation while externalizing only root initiation edges."""
    context = contexts.assemble(
        records,
        require_actor_current_use=require_actor_current_use,
    )
    findings = validate_record_graph(
        records,
        context=context.validation,
        options=GraphValidationOptions(require_internal_resolution=True),
    )
    remaining = tuple(
        finding
        for finding in findings
        if not (
            finding.code in _UNRESOLVED_INITIATION_CODES
            and finding.subject.startswith("support_process@1:")
            and finding.path.startswith("$.initiation")
        )
    )
    if remaining:
        raise WorkflowValidationError(remaining)
