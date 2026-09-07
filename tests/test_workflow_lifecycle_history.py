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
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows import (
    LifecycleHistoryCorrectionResolution,
    LifecycleWorkflowService,
)
from portia.workflows.errors import WorkflowPrerequisiteError
from tests.workflow_helpers import AGENT, TIMESTAMP


class _SyntheticRecord:
    def __init__(
        self,
        *,
        contract: str,
        version: str,
        logical_id: str,
        fields: dict[str, object],
        status: str | None = None,
    ) -> None:
        self.contract = contract
        self.contract_version = version
        self.logical_id = logical_id
        self.class_id = "class_a"
        self.work_id = "evt_alpha"
        self.status = status
        self._fields = fields

    def field(self, name: str) -> object:
        return self._fields.get(name)


def _stored(record: object) -> StoredRecord:
    value = type("SyntheticStored", (), {"record": record})()
    return cast(StoredRecord, value)


def _event_work() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_a",
        work_id="evt_alpha",
        work_kind="event",
        contract_version="2",
    )


def _account_reference() -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=_event_work(),
        record_ref=ExactLocalRecordRef(
            record_kind="account",
            record_id="acct_alpha",
            contract_version="2",
        ),
    )


def _target() -> dict[str, object]:
    return {
        "kind": "local_record",
        "record_ref": _account_reference().record_ref.to_dict(),
    }


def _local_ref(kind: str, identifier: str) -> dict[str, object]:
    return ExactLocalRecordRef(
        record_kind=kind,
        record_id=identifier,
        contract_version="1",
    ).to_dict()


def _canonical(status: str) -> PortiaRecord:
    return cast(
        PortiaRecord,
        _SyntheticRecord(
            contract="account",
            version="2",
            logical_id="acct_alpha",
            fields={},
            status=status,
        ),
    )


def _transition(
    transition_id: str,
    *,
    from_status: str,
    to_status: str,
    previous: str | None = None,
) -> StoredRecord:
    return _stored(
        _SyntheticRecord(
            contract="lifecycle_transition",
            version="1",
            logical_id=transition_id,
            fields={
                "target": _target(),
                "previous_transition": (
                    None
                    if previous is None
                    else _local_ref("lifecycle_transition", previous)
                ),
                "from_status": from_status,
                "to_status": to_status,
            },
        )
    )


def _correction(
    correction_id: str,
    *,
    replaced: str,
    replacement: str | None,
    previous: str | None = None,
) -> StoredRecord:
    return _stored(
        _SyntheticRecord(
            contract="lifecycle_history_correction",
            version="1",
            logical_id=correction_id,
            fields={
                "target": _target(),
                "previous_correction": (
                    None
                    if previous is None
                    else _local_ref("lifecycle_history_correction", previous)
                ),
                "replaced_head": _local_ref("lifecycle_transition", replaced),
                "replacement_head": (
                    None
                    if replacement is None
                    else _local_ref("lifecycle_transition", replacement)
                ),
            },
        )
    )


class _HistoryRepository:
    def __init__(
        self,
        canonical: PortiaRecord,
        *,
        transitions: tuple[StoredRecord, ...] = (),
        corrections: tuple[StoredRecord, ...] = (),
    ) -> None:
        self.canonical = canonical
        self.transitions = transitions
        self.corrections = corrections

    def load_work(self, work: ExactPortiaWorkRef) -> StoredRecord:
        if work != _event_work():
            raise AssertionError("unexpected work lookup")
        return _stored(object())

    def load_work_record(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        version: str,
        record_id: str,
    ) -> StoredRecord:
        if (
            work != _event_work()
            or contract != "account"
            or version != "2"
            or record_id != "acct_alpha"
        ):
            raise AssertionError("unexpected exact record lookup")
        return _stored(self.canonical)

    def list_work_records(
        self,
        work: ExactPortiaWorkRef,
        contract: str,
        *,
        version: str,
    ) -> tuple[StoredRecord, ...]:
        if work != _event_work() or version != "1":
            return ()
        if contract == "lifecycle_transition":
            return self.transitions
        if contract == "lifecycle_history_correction":
            return self.corrections
        return ()


def _service(
    tmp_path: Path, repository: _HistoryRepository
) -> LifecycleWorkflowService:
    return LifecycleWorkflowService(
        tmp_path,
        repository=cast(PortiaRepository, repository),
    )


def test_correction_chain_uses_exact_predecessors_not_storage_order(
    tmp_path: Path,
) -> None:
    c1 = _correction("corr_1", replaced="old_1", replacement="new_1")
    c2 = _correction(
        "corr_2",
        replaced="new_1",
        replacement="new_2",
        previous="corr_1",
    )
    repository = _HistoryRepository(
        _canonical("active"),
        corrections=(c2, c1),
    )
    service = _service(tmp_path, repository)

    history = service.load_correction_history(_account_reference())

    assert [item.record.logical_id for item in history] == ["corr_1", "corr_2"]
    selected = service.resolve_selected_correction(_account_reference())
    assert selected is not None
    assert selected.record.logical_id == "corr_2"


def test_corrected_history_selects_replacement_branch_from_raw_fork(
    tmp_path: Path,
) -> None:
    old = _transition("old_active", from_status="proposed", to_status="active")
    replacement = _transition(
        "corrected_invalid",
        from_status="proposed",
        to_status="invalidated",
    )
    correction = _correction(
        "corr_select_invalid",
        replaced="old_active",
        replacement="corrected_invalid",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("invalidated"),
            transitions=(replacement, old),
            corrections=(correction,),
        ),
    )

    resolution = service.require_corrected_history_reconciled(_account_reference())

    assert isinstance(resolution, LifecycleHistoryCorrectionResolution)
    assert resolution.baseline_status == "proposed"
    assert resolution.selected_status == "invalidated"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "corrected_invalid"
    assert resolution.excluded_transition_ids == frozenset({"old_active"})
    assert resolution.reconciled is True


def test_history_correction_can_select_creation_baseline(tmp_path: Path) -> None:
    old = _transition("old_active", from_status="proposed", to_status="active")
    correction = _correction(
        "corr_baseline",
        replaced="old_active",
        replacement=None,
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("proposed"),
            transitions=(old,),
            corrections=(correction,),
        ),
    )

    resolution = service.require_corrected_history_reconciled(_account_reference())

    assert resolution.baseline_status == "proposed"
    assert resolution.selected_head is None
    assert resolution.selected_status == "proposed"
    assert resolution.excluded_transition_ids == frozenset({"old_active"})


def test_selected_replacement_branch_may_receive_later_transition(
    tmp_path: Path,
) -> None:
    old = _transition("old_active", from_status="proposed", to_status="active")
    replacement = _transition(
        "corrected_invalid",
        from_status="proposed",
        to_status="invalidated",
    )
    extension = _transition(
        "later_superseded",
        from_status="invalidated",
        to_status="superseded",
        previous="corrected_invalid",
    )
    correction = _correction(
        "corr_select_invalid",
        replaced="old_active",
        replacement="corrected_invalid",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("superseded"),
            transitions=(old, extension, replacement),
            corrections=(correction,),
        ),
    )

    resolution = service.require_corrected_history_reconciled(_account_reference())

    assert resolution.selected_status == "superseded"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "later_superseded"
    assert resolution.excluded_transition_ids == frozenset({"old_active"})


def test_corrected_history_reconciliation_fails_closed_on_status_mismatch(
    tmp_path: Path,
) -> None:
    old = _transition("old_active", from_status="proposed", to_status="active")
    replacement = _transition(
        "corrected_invalid",
        from_status="proposed",
        to_status="invalidated",
    )
    correction = _correction(
        "corr_select_invalid",
        replaced="old_active",
        replacement="corrected_invalid",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("active"),
            transitions=(old, replacement),
            corrections=(correction,),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.require_corrected_history_reconciled(_account_reference())


def test_same_replaced_and_replacement_head_is_rejected(tmp_path: Path) -> None:
    transition = _transition("head_1", from_status="proposed", to_status="active")
    correction = _correction(
        "corr_same",
        replaced="head_1",
        replacement="head_1",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("active"),
            transitions=(transition,),
            corrections=(correction,),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="replace a head with itself"):
        service.resolve_corrected_history(_account_reference())


def test_self_predecessor_correction_is_rejected(tmp_path: Path) -> None:
    correction = _correction(
        "corr_self",
        replaced="head_1",
        replacement=None,
        previous="corr_self",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(_canonical("proposed"), corrections=(correction,)),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="itself as predecessor"):
        service.load_correction_history(_account_reference())


def test_correction_chain_fork_is_rejected(tmp_path: Path) -> None:
    root = _correction("corr_root", replaced="head_1", replacement="head_2")
    left = _correction(
        "corr_left",
        replaced="head_2",
        replacement="head_3",
        previous="corr_root",
    )
    right = _correction(
        "corr_right",
        replaced="head_2",
        replacement="head_4",
        previous="corr_root",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("active"),
            corrections=(left, root, right),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="contains a fork"):
        service.load_correction_history(_account_reference())


def test_missing_replaced_transition_head_is_rejected(tmp_path: Path) -> None:
    actual = _transition("actual", from_status="proposed", to_status="active")
    correction = _correction(
        "corr_missing",
        replaced="missing",
        replacement="actual",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("active"),
            transitions=(actual,),
            corrections=(correction,),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="missing transition head"):
        service.resolve_corrected_history(_account_reference())


def test_correction_branches_must_share_one_creation_baseline(tmp_path: Path) -> None:
    old = _transition("old", from_status="proposed", to_status="active")
    replacement = _transition(
        "replacement",
        from_status="draft",
        to_status="invalidated",
    )
    correction = _correction(
        "corr_baseline_mismatch",
        replaced="old",
        replacement="replacement",
    )
    service = _service(
        tmp_path,
        _HistoryRepository(
            _canonical("invalidated"),
            transitions=(old, replacement),
            corrections=(correction,),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="creation baseline"):
        service.resolve_corrected_history(_account_reference())


def _real_account() -> PortiaRecord:
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
            "account_id": "acct_alpha",
            "status": "active",
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
            "updated_at": TIMESTAMP,
            "updated_by": AGENT,
        },
    )


def test_no_correction_evidence_delegates_to_existing_family_reader(
    tmp_path: Path,
) -> None:
    service = _service(tmp_path, _HistoryRepository(_real_account()))

    resolution = service.resolve_corrected_history(_account_reference())

    assert resolution.corrections == ()
    assert resolution.selected_correction is None
    assert resolution.transitions == ()
    assert resolution.selected_head is None
    assert resolution.selected_status is None
    assert resolution.reconciled is True
