from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.orchestration import OperationCommitResult
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows import (
    LifecycleResolution,
    LifecycleWorkflowService,
    supported_record_lifecycle_contracts,
)
from portia.workflows.accounts import AccountWorkflowService
from portia.workflows.errors import WorkflowOwnershipError
from tests.workflow_helpers import AGENT, TIMESTAMP

LATER = "2026-09-07T16:05:00-04:00"


class _EmptyRepository:
    def list_work_records(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        *,
        version: str,
    ) -> tuple[StoredRecord, ...]:
        del work, contract, version
        return ()


class _RecordRepository(_EmptyRepository):
    def __init__(self, record: PortiaRecord) -> None:
        self.record = record

    def load_work(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if work != _event_work():
            raise AssertionError("unexpected exact test work lookup")
        return cast(StoredRecord, object())

    def load_work_record(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        version: str,
        record_id: str,
    ) -> StoredRecord:
        if (
            work != _event_work()
            or contract != self.record.contract
            or version != self.record.contract_version
            or record_id != self.record.logical_id
        ):
            raise AssertionError("unexpected exact test repository lookup")
        stored = type("SyntheticStored", (), {"record": self.record})()
        return cast(StoredRecord, stored)


def _event_work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _account_reference(*, version: str = "2") -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=_event_work(),
        record_ref=ExactLocalRecordRef(
            record_kind="account",
            record_id="acct_alpha",
            contract_version=version,
        ),
    )


def _account(
    *,
    status: str = "active",
    account_id: str = "acct_alpha",
    updated_at: str = TIMESTAMP,
) -> PortiaRecord:
    return parse_portia_record(
        "account",
        "2",
        {
            "schema_version": "2",
            "record_type": "account",
            "module_id": "portia",
            "class_id": "class_a",
            "work_kind": "event",
            "work_id": "evt_alpha",
            "account_id": account_id,
            "status": status,
            "target": {"kind": "event"},
            "source": {
                "kind": "local_operator",
                "display_label": "Synthetic Teacher",
            },
            "information_origin": "firsthand",
            "source_certainty": "stated_certain",
            "content": [
                {
                    "representation": "recorded_summary",
                    "text": "Synthetic source contribution.",
                }
            ],
            "provided_time": {"precision": "exact", "at": TIMESTAMP},
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
            "updated_at": updated_at,
            "updated_by": AGENT,
        },
    )


def test_registered_record_lifecycle_adapters_are_closed_and_versioned() -> None:
    assert supported_record_lifecycle_contracts() == (
        ("account", "1"),
        ("account", "2"),
        ("classification", "1"),
        ("communication", "1"),
        ("determination", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("hypothesis", "1"),
        ("implementation", "1"),
        ("intervention", "1"),
        ("observation", "1"),
        ("observation", "2"),
        ("outcome", "1"),
        ("reentry", "1"),
        ("repair", "1"),
        ("response", "1"),
        ("review", "1"),
        ("support", "1"),
        ("support_goal", "1"),
        ("support_need", "1"),
        ("support_process_participant", "1"),
    )


def test_current_write_lifecycle_transition_registry_is_closed() -> None:
    assert LifecycleWorkflowService.supported_transition_contracts() == (
        ("account", "2"),
        ("classification", "1"),
        ("communication", "1"),
        ("determination", "1"),
        ("fidelity", "1"),
        ("follow_up", "1"),
        ("hypothesis", "1"),
        ("implementation", "1"),
        ("intervention", "1"),
        ("observation", "2"),
        ("outcome", "1"),
        ("reentry", "1"),
        ("repair", "1"),
        ("response", "1"),
        ("review", "1"),
        ("support", "1"),
        ("support_goal", "1"),
        ("support_need", "1"),
        ("support_process_participant", "1"),
    )


def test_real_evidence_adapter_resolves_empty_history_without_inventing_head(
    tmp_path: Path,
) -> None:
    service = LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, _EmptyRepository()),
    )
    resolution = service.resolve_record(_event_work(), _account())

    assert isinstance(resolution, LifecycleResolution)
    assert resolution.record_id == "acct_alpha"
    assert resolution.canonical_status == "active"
    assert resolution.selected_status is None
    assert resolution.transitions == ()
    assert resolution.head is None
    assert resolution.reconciled is True
    assert service.resolve_selected_head(_event_work(), _account()) is None


def test_exact_reference_history_loader_does_not_follow_successors(
    tmp_path: Path,
) -> None:
    repository = _RecordRepository(_account())
    service = LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, repository),
    )

    resolution = service.load_history(_account_reference())

    assert resolution.record_id == "acct_alpha"
    assert resolution.contract == "account"
    assert resolution.contract_version == "2"
    assert resolution.canonical_status == "active"
    assert resolution.transitions == ()


def test_real_evidence_adapter_requires_reconciled_empty_history(
    tmp_path: Path,
) -> None:
    service = LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, _EmptyRepository()),
    )
    resolution = service.require_reconciled(_event_work(), _account())
    assert resolution.reconciled is True


@pytest.mark.parametrize(
    ("contract", "version"),
    [
        ("actor", "1"),
        ("event", "2"),
        ("support_process", "1"),
        ("event_participant", "3"),
        ("dependency", "1"),
        ("statement_of_disagreement", "1"),
        ("account", "99"),
    ],
)
def test_unregistered_family_or_version_fails_closed(
    tmp_path: Path,
    contract: str,
    version: str,
) -> None:
    service = LifecycleWorkflowService(tmp_path)
    record = cast(
        PortiaRecord,
        type(
            "SyntheticRecord",
            (),
            {
                "contract": contract,
                "contract_version": version,
                "logical_id": "synthetic_id",
                "status": "active",
            },
        )(),
    )

    with pytest.raises(WorkflowOwnershipError, match="no registered adapter"):
        service.resolve_record(_event_work(), record)


def test_generic_transition_delegates_to_existing_family_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prior = _account(status="proposed")
    candidate = _account(status="active", updated_at=LATER)
    repository = _RecordRepository(prior)
    service = LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, repository),
    )
    expected = cast(ContentFingerprint, object())
    sentinel = cast(OperationCommitResult, object())
    captured: dict[str, object] = {}

    def fake_transition(
        self: AccountWorkflowService,
        reference: ExactPortiaWorkRecordRef,
        value: PortiaRecord,
        *,
        expected: ContentFingerprint,
        transition_id: str,
        reason_code: str,
        reason_detail: str | None = None,
        effective_at: str | None = None,
        operation_id: str | None = None,
        fault_hook: object | None = None,
    ) -> OperationCommitResult:
        del self
        captured.update(
            {
                "reference": reference,
                "candidate": value,
                "expected": expected,
                "transition_id": transition_id,
                "reason_code": reason_code,
                "reason_detail": reason_detail,
                "effective_at": effective_at,
                "operation_id": operation_id,
                "fault_hook": fault_hook,
            }
        )
        repository.record = value
        return sentinel

    monkeypatch.setattr(AccountWorkflowService, "transition_lifecycle", fake_transition)

    result = service.transition(
        _account_reference(),
        candidate,
        expected=expected,
        transition_id="lt_account_activate",
        reason_code="review_completed",
        reason_detail="Synthetic activation qualification.",
        effective_at=LATER,
        operation_id="op_account_activate",
    )

    assert result is sentinel
    assert captured == {
        "reference": _account_reference(),
        "candidate": candidate,
        "expected": expected,
        "transition_id": "lt_account_activate",
        "reason_code": "review_completed",
        "reason_detail": "Synthetic activation qualification.",
        "effective_at": LATER,
        "operation_id": "op_account_activate",
        "fault_hook": None,
    }


def test_generic_transition_rejects_candidate_identity_change_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _RecordRepository(_account(status="proposed"))
    service = LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, repository),
    )
    called = False

    def fake_transition(*args: object, **kwargs: object) -> OperationCommitResult:
        nonlocal called
        called = True
        del args, kwargs
        return cast(OperationCommitResult, object())

    monkeypatch.setattr(AccountWorkflowService, "transition_lifecycle", fake_transition)

    with pytest.raises(WorkflowOwnershipError, match="preserve the exact"):
        service.transition(
            _account_reference(),
            _account(
                status="active",
                account_id="acct_other",
                updated_at=LATER,
            ),
            expected=cast(ContentFingerprint, object()),
            transition_id="lt_wrong_identity",
            reason_code="review_completed",
        )

    assert called is False


def test_historical_read_version_is_not_promoted_to_transition_authority(
    tmp_path: Path,
) -> None:
    service = LifecycleWorkflowService(tmp_path)

    with pytest.raises(WorkflowOwnershipError, match="historical-read account@1"):
        service.transition(
            _account_reference(version="1"),
            _account(status="active", updated_at=LATER),
            expected=cast(ContentFingerprint, object()),
            transition_id="lt_historical_write",
            reason_code="review_completed",
        )


def test_generic_surface_still_exposes_no_arbitrary_mutation_or_supersession_api() -> None:
    assert "transition" in vars(LifecycleWorkflowService)
    forbidden = {
        "transition_lifecycle",
        "correct_history",
        "correct",
        "consolidate_duplicates",
        "supersede",
        "replace",
        "revise",
        "save",
        "patch",
        "set_status",
        "force_status",
        "delete",
    }
    assert forbidden.isdisjoint(vars(LifecycleWorkflowService))
