"""Focused Slice 1 tests for exact Response/Communication reads and references."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.workflows import (
    CommunicationWorkflowService,
    ResponseWorkflowService,
    communication_reference,
    response_reference,
)
from portia.workflows.errors import WorkflowOwnershipError


def _event(*, version: str = "2") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_issue43",
        work_id="evt_issue43",
        work_kind="event",
        contract_version=version,
    )


def _support(*, version: str = "1") -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_issue43",
        work_id="sup_issue43",
        work_kind="support_process",
        contract_version=version,
    )


def test_response_reference_is_exact_event_local_v1() -> None:
    work = _event()
    reference = response_reference(work, "rsp_issue43")

    assert reference.work_ref == work
    assert reference.record_ref == ExactLocalRecordRef(
        record_kind="response",
        record_id="rsp_issue43",
        contract_version="1",
    )


@pytest.mark.parametrize(
    "work",
    [
        _event(version="1"),
        _support(),
    ],
)
def test_response_reference_rejects_non_event2_owner(
    work: ExactPortiaWorkRef,
) -> None:
    with pytest.raises(WorkflowOwnershipError):
        response_reference(work, "rsp_issue43")


@pytest.mark.parametrize("work", [_event(), _support()])
def test_communication_reference_preserves_frozen_owner_union(
    work: ExactPortiaWorkRef,
) -> None:
    reference = communication_reference(work, "comm_issue43")

    assert reference.work_ref == work
    assert reference.record_ref == ExactLocalRecordRef(
        record_kind="communication",
        record_id="comm_issue43",
        contract_version="1",
    )


@pytest.mark.parametrize(
    "work",
    [
        _event(version="1"),
        _support(version="2"),
    ],
)
def test_communication_reference_rejects_unknown_owner_versions(
    work: ExactPortiaWorkRef,
) -> None:
    with pytest.raises(WorkflowOwnershipError):
        communication_reference(work, "comm_issue43")


def test_response_load_exact_pins_requested_identity(tmp_path: Path) -> None:
    repository = Mock()
    stored = object()
    repository.load_work_record.return_value = stored
    work = _event()
    reference = response_reference(work, "rsp_issue43")
    service = ResponseWorkflowService(tmp_path, repository=repository)

    assert service.load_exact(reference) is stored
    repository.load_work.assert_called_once_with(work)
    repository.load_work_record.assert_called_once_with(
        work,
        "response",
        "1",
        "rsp_issue43",
    )


def test_communication_exact_historical_support_owner_is_readable(
    tmp_path: Path,
) -> None:
    repository = Mock()
    stored = object()
    repository.load_work_record.return_value = stored
    work = _support()
    reference = communication_reference(work, "comm_issue43")
    service = CommunicationWorkflowService(tmp_path, repository=repository)

    assert service.resolve_exact(reference) is stored
    repository.load_work.assert_called_once_with(work)
    repository.load_work_record.assert_called_once_with(
        work,
        "communication",
        "1",
        "comm_issue43",
    )


@pytest.mark.parametrize(
    ("service_type", "work", "contract", "record_id"),
    [
        (ResponseWorkflowService, _event(), "response", "rsp_issue43"),
        (
            CommunicationWorkflowService,
            _event(),
            "communication",
            "comm_issue43",
        ),
        (
            CommunicationWorkflowService,
            _support(),
            "communication",
            "comm_support_issue43",
        ),
    ],
)
def test_bounded_list_delegates_to_exact_canonical_collection(
    tmp_path: Path,
    service_type: type[ResponseWorkflowService] | type[CommunicationWorkflowService],
    work: ExactPortiaWorkRef,
    contract: str,
    record_id: str,
) -> None:
    repository = Mock()
    stored = object()
    repository.list_work_records.return_value = (stored,)
    service = service_type(tmp_path, repository=repository)

    assert service.list(work) == (stored,)
    repository.list_work_records.assert_called_once_with(
        work,
        contract,
        version="1",
    )
    # Listing is bounded by the explicit work and family; it never asks for or
    # follows a successor identity.
    assert record_id


@pytest.mark.parametrize(
    ("service", "reference"),
    [
        (
            ResponseWorkflowService,
            ExactPortiaWorkRecordRef(
                work_ref=_event(),
                record_ref=ExactLocalRecordRef(
                    record_kind="communication",
                    record_id="comm_issue43",
                    contract_version="1",
                ),
            ),
        ),
        (
            CommunicationWorkflowService,
            ExactPortiaWorkRecordRef(
                work_ref=_event(),
                record_ref=ExactLocalRecordRef(
                    record_kind="response",
                    record_id="rsp_issue43",
                    contract_version="1",
                ),
            ),
        ),
    ],
)
def test_exact_load_rejects_wrong_record_family_before_repository_access(
    tmp_path: Path,
    service: type[ResponseWorkflowService] | type[CommunicationWorkflowService],
    reference: ExactPortiaWorkRecordRef,
) -> None:
    repository = Mock()
    workflow = service(tmp_path, repository=repository)

    with pytest.raises(WorkflowOwnershipError):
        workflow.load_exact(reference)

    repository.load_work.assert_not_called()
    repository.load_work_record.assert_not_called()


@pytest.mark.parametrize(
    ("service", "record_kind"),
    [
        (ResponseWorkflowService, "response"),
        (CommunicationWorkflowService, "communication"),
    ],
)
def test_exact_load_rejects_non_v1_record_reference(
    tmp_path: Path,
    service: type[ResponseWorkflowService] | type[CommunicationWorkflowService],
    record_kind: str,
) -> None:
    repository = Mock()
    reference = ExactPortiaWorkRecordRef(
        work_ref=_event(),
        record_ref=ExactLocalRecordRef(
            record_kind=record_kind,
            record_id="historical_issue43",
            contract_version="2",
        ),
    )
    workflow = service(tmp_path, repository=repository)

    with pytest.raises(WorkflowOwnershipError):
        workflow.load_exact(reference)

    repository.load_work.assert_not_called()
    repository.load_work_record.assert_not_called()


def test_public_workflow_exports_are_available() -> None:
    assert ResponseWorkflowService.__name__ == "ResponseWorkflowService"
    assert CommunicationWorkflowService.__name__ == "CommunicationWorkflowService"
    assert callable(response_reference)
    assert callable(communication_reference)
