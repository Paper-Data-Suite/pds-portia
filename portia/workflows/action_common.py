"""Shared exact read/reference mechanics for Response and Communication."""

from __future__ import annotations

from typing import ClassVar

from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.repository import StoredRecord
from portia.workflows.common import WorkflowServiceBase
from portia.workflows.errors import WorkflowOwnershipError

ACTION_VERSION = "1"
_RESPONSE_OWNER = ("event", "2")
_COMMUNICATION_OWNERS = frozenset(
    {
        ("event", "2"),
        ("support_process", "1"),
    }
)
_ACTION_CONTRACTS = frozenset({"response", "communication"})


def require_action_owner(work: ExactPortiaWorkRef, *, contract: str) -> None:
    """Require the frozen exact owner shape for one action-layer record family."""
    if contract == "response":
        if (work.work_kind, work.contract_version) != _RESPONSE_OWNER:
            raise WorkflowOwnershipError(
                "Response workflows require exact event@2 ownership"
            )
        return
    if contract == "communication":
        if (work.work_kind, work.contract_version) not in _COMMUNICATION_OWNERS:
            raise WorkflowOwnershipError(
                "Communication workflows require exact event@2 or "
                "support_process@1 ownership"
            )
        return
    if contract == "support_process_participant":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Support Process Participant lifecycle requires exact "
                "support_process@1 ownership"
            )
        return
    if contract == "implementation":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Implementation lifecycle requires exact "
                "support_process@1 ownership"
            )
        return
    if contract == "fidelity":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Fidelity lifecycle requires exact "
                "support_process@1 ownership"
            )
        return
    if contract == "support":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Support lifecycle requires exact support_process@1 ownership"
            )
        return
    if contract == "intervention":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Intervention lifecycle requires exact support_process@1 ownership"
            )
        return
    if contract == "support_need":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Support Need lifecycle requires exact support_process@1 ownership"
            )
        return
    if contract == "support_goal":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Support Goal lifecycle requires exact support_process@1 ownership"
            )
        return
    if contract == "support_process_participant":
        if (work.work_kind, work.contract_version) != ("support_process", "1"):
            raise WorkflowOwnershipError(
                "Participant lifecycle requires exact support_process@1 ownership"
            )
        return
    raise WorkflowOwnershipError(f"unsupported action-layer contract {contract!r}")


def action_reference(
    work: ExactPortiaWorkRef,
    contract: str,
    record_id: str,
) -> ExactPortiaWorkRecordRef:
    """Construct one exact v1 Response/Communication record reference."""
    if contract not in _ACTION_CONTRACTS:
        raise WorkflowOwnershipError(f"unsupported action-layer contract {contract!r}")
    require_action_owner(work, contract=contract)
    return ExactPortiaWorkRecordRef(
        work_ref=work,
        record_ref=ExactLocalRecordRef(
            record_kind=contract,
            record_id=record_id,
            contract_version=ACTION_VERSION,
        ),
    )


class ActionReadService(WorkflowServiceBase):
    """Strict exact-reader base for one Response/Communication record family."""

    CONTRACT: ClassVar[str]

    def load_exact(self, reference: ExactPortiaWorkRecordRef) -> StoredRecord:
        require_action_owner(reference.work_ref, contract=self.CONTRACT)
        if reference.record_ref.record_kind != self.CONTRACT:
            raise WorkflowOwnershipError(
                f"reference is not a {self.CONTRACT} record"
            )
        if reference.record_ref.contract_version != ACTION_VERSION:
            raise WorkflowOwnershipError(
                f"unsupported exact {self.CONTRACT} contract version "
                f"{reference.record_ref.contract_version!r}"
            )
        self.repository.load_work(reference.work_ref)
        return self.repository.load_work_record(
            reference.work_ref,
            self.CONTRACT,
            ACTION_VERSION,
            reference.record_ref.record_id,
        )

    resolve_exact = load_exact

    def list(self, work: ExactPortiaWorkRef) -> tuple[StoredRecord, ...]:
        require_action_owner(work, contract=self.CONTRACT)
        return self.repository.list_work_records(
            work,
            self.CONTRACT,
            version=ACTION_VERSION,
        )
