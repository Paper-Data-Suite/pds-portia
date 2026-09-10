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
from portia.storage.errors import (
    PortiaConflictError,
    PortiaNotFoundError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import ContentFingerprint
from portia.storage.locks import derive_lock_id
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    LifecycleHistoryCorrectionResolution,
    LifecycleWorkflowService,
)
from portia.workflows.common import work_target
from portia.workflows.errors import WorkflowPrerequisiteError
from portia.workflows.lifecycle_history import build_lifecycle_history_correction
from tests.workflow_helpers import AGENT, TIMESTAMP, event_record


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


def _real_account(
    *, status: str = "active", updated_at: str = TIMESTAMP
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
            "account_id": "acct_alpha",
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


_CORRECTION_AT = "2026-08-26T13:00:00-04:00"


def _real_transition(
    transition_id: str,
    *,
    from_status: str,
    to_status: str,
    previous: str | None = None,
    reason_code: str = "review_completed",
) -> PortiaRecord:
    if to_status == "invalidated":
        category = "record_validity"
        if reason_code == "review_completed":
            reason_code = "wrong_target"
    elif to_status == "superseded":
        category = "correction"
        if reason_code == "review_completed":
            reason_code = "corrected_by_successor"
    else:
        category = "workflow"
    return parse_portia_record(
        "lifecycle_transition",
        "1",
        {
            "schema_version": "1",
            "record_type": "lifecycle_transition",
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_alpha",
            "transition_id": transition_id,
            "target": _target(),
            "previous_transition": (
                None
                if previous is None
                else _local_ref("lifecycle_transition", previous)
            ),
            "from_status": from_status,
            "to_status": to_status,
            "reason": {"category": category, "code": reason_code},
            "effective_at": TIMESTAMP,
            "creation_source": {"type": "digital_entry"},
            "created_at": TIMESTAMP,
            "created_by": AGENT,
        },
    )


def _seed_mutation_history(
    tmp_path: Path,
    *,
    canonical_status: str = "active",
    replacement_status: str = "invalidated",
    replacement_reason: str = "wrong_target",
    include_replacement: bool = True,
) -> tuple[PortiaRepository, StoredRecord]:
    repository = PortiaRepository(tmp_path)
    repository.create_work(_event_work(), event_record())
    account = repository.create_work_record(
        _event_work(),
        _real_account(status=canonical_status),
    )
    repository.create_work_record(
        _event_work(),
        _real_transition(
            "lct_old",
            from_status="proposed",
            to_status=canonical_status,
        ),
    )
    if include_replacement:
        repository.create_work_record(
            _event_work(),
            _real_transition(
                "lct_replacement",
                from_status="proposed",
                to_status=replacement_status,
                reason_code=replacement_reason,
            ),
        )
    return repository, account


def _mutation_service(
    tmp_path: Path,
    repository: PortiaRepository,
) -> LifecycleWorkflowService:
    return LifecycleWorkflowService(tmp_path, repository=repository)



def test_correct_history_commits_selector_reconciles_status_and_replays(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    service = _mutation_service(tmp_path, repository)

    # Slice 4 must not weaken the ordinary family reader/transition path merely
    # because a complete replacement branch is waiting to be selected.
    with pytest.raises(WorkflowPrerequisiteError, match="root transition"):
        service.transition(
            _account_reference(),
            _real_account(status="invalidated", updated_at=_CORRECTION_AT),
            expected=account.fingerprint,
            transition_id="lct_ordinary_still_blocked",
            reason_code="wrong_target",
        )

    result = service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_select_replacement",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_to_status",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
        operation_id="op_history_select",
    )

    accepted = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert accepted.record.status == "invalidated"
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_status == "invalidated"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_replacement"
    assert resolution.selected_correction is not None
    assert resolution.selected_correction.record.logical_id == "lhc_select_replacement"
    current = OperationJournalStore(tmp_path).load_current("op_history_select")
    assert current.revision.field("operation_kind") == "correct_history"
    assert current.revision.field("state") == "completed"
    assert "step_correction" in result.accepted_steps
    assert "step_target" in result.accepted_steps

    replay = service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_select_replacement",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_to_status",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
        operation_id="op_history_select",
    )
    assert replay.accepted_steps == result.accepted_steps


def test_correct_history_can_select_creation_baseline_and_reconcile_target(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(
        tmp_path,
        include_replacement=False,
    )
    service = _mutation_service(tmp_path, repository)

    service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_select_baseline",
        replaced_head_id="lct_old",
        replacement_head_id=None,
        reason_code="transition_should_not_exist",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )

    accepted = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert accepted.record.status == "proposed"
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_head is None
    assert resolution.selected_status == "proposed"
    assert resolution.excluded_transition_ids == frozenset({"lct_old"})


def test_correct_history_same_status_appends_selector_without_rewriting_target(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(
        tmp_path,
        replacement_status="active",
        replacement_reason="review_completed",
    )
    service = _mutation_service(tmp_path, repository)

    result = service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_reason_only",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_reason",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )

    accepted = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert accepted.fingerprint == account.fingerprint
    assert accepted.record.to_dict() == account.record.to_dict()
    assert result.accepted_steps == ("step_correction",)
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_replacement"


def test_correct_history_appends_to_selected_correction_chain(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    service = _mutation_service(tmp_path, repository)
    service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_first",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_to_status",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )
    first_target = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    repository.create_work_record(
        _event_work(),
        _real_transition(
            "lct_second_replacement",
            from_status="proposed",
            to_status="active",
        ),
    )

    service.correct_history(
        _account_reference(),
        expected=first_target.fingerprint,
        correction_id="lhc_second",
        replaced_head_id="lct_replacement",
        replacement_head_id="lct_second_replacement",
        reason_code="multiple_fields_corrected",
        created_at="2026-08-26T14:00:00-04:00",
        created_by=AGENT,
    )

    history = service.load_correction_history(_account_reference())
    assert [item.record.logical_id for item in history] == ["lhc_first", "lhc_second"]
    assert history[-1].record.field("previous_correction") == _local_ref(
        "lifecycle_history_correction", "lhc_first"
    )
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_status == "active"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_second_replacement"


def test_correct_history_rejects_replaced_head_that_is_not_current_status_head(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    service = _mutation_service(tmp_path, repository)

    with pytest.raises(WorkflowPrerequisiteError, match="does not reconcile"):
        service.correct_history(
            _account_reference(),
            expected=account.fingerprint,
            correction_id="lhc_wrong_replaced",
            replaced_head_id="lct_replacement",
            replacement_head_id="lct_old",
            reason_code="wrong_to_status",
            created_at=_CORRECTION_AT,
            created_by=AGENT,
        )

    assert service.load_correction_history(_account_reference()) == ()


def test_correct_history_rejects_unrelated_third_active_branch(tmp_path: Path) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    repository.create_work_record(
        _event_work(),
        _real_transition(
            "lct_third",
            from_status="proposed",
            to_status="active",
        ),
    )
    service = _mutation_service(tmp_path, repository)

    with pytest.raises(WorkflowPrerequisiteError, match="unique complete alternative"):
        service.correct_history(
            _account_reference(),
            expected=account.fingerprint,
            correction_id="lhc_ambiguous",
            replaced_head_id="lct_old",
            replacement_head_id="lct_replacement",
            reason_code="wrong_to_status",
            created_at=_CORRECTION_AT,
            created_by=AGENT,
        )


def test_correct_history_rejects_stale_expected_target_revision(tmp_path: Path) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    stale = ContentFingerprint(
        digest="0" * len(account.fingerprint.digest),
        byte_length=account.fingerprint.byte_length,
        algorithm=account.fingerprint.algorithm,
    )
    service = _mutation_service(tmp_path, repository)

    with pytest.raises(PortiaConflictError, match="expected lifecycle-history target"):
        service.correct_history(
            _account_reference(),
            expected=stale,
            correction_id="lhc_stale",
            replaced_head_id="lct_old",
            replacement_head_id="lct_replacement",
            reason_code="wrong_to_status",
            created_at=_CORRECTION_AT,
            created_by=AGENT,
        )


def test_correct_history_partial_commit_preserves_durable_selector_for_recovery(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(tmp_path)
    service = _mutation_service(tmp_path, repository)

    def fail_after_selector(event: str, step_id: str | None) -> None:
        if event == "after_publish" and step_id == "step_correction":
            raise RuntimeError("synthetic interruption after selector durability")

    with pytest.raises(PortiaOperationPartialCommitError) as captured:
        service.correct_history(
            _account_reference(),
            expected=account.fingerprint,
            correction_id="lhc_partial",
            replaced_head_id="lct_old",
            replacement_head_id="lct_replacement",
            reason_code="wrong_to_status",
            created_at=_CORRECTION_AT,
            created_by=AGENT,
            operation_id="op_history_partial",
            fault_hook=fail_after_selector,
        )

    assert "step_correction" in captured.value.accepted_steps
    correction = repository.load_work_record(
        _event_work(),
        "lifecycle_history_correction",
        "1",
        "lhc_partial",
    )
    assert correction.record.logical_id == "lhc_partial"
    unchanged = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert unchanged.record.status == "active"
    current = OperationJournalStore(tmp_path).load_current("op_history_partial")
    assert current.revision.field("operation_kind") == "correct_history"
    assert current.revision.field("state") == "failed"


_AFTER_CORRECTION = "2026-08-26T14:00:00-04:00"


def test_ordinary_transition_continues_selected_corrected_branch(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(
        tmp_path,
        replacement_status="active",
        replacement_reason="review_completed",
    )
    service = _mutation_service(tmp_path, repository)
    service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_select_active_replacement",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_reason",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )
    current = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )

    result = service.transition(
        _account_reference(),
        _real_account(status="invalidated", updated_at=_AFTER_CORRECTION),
        expected=current.fingerprint,
        transition_id="lct_after_correction",
        reason_code="wrong_target",
        operation_id="op_after_correction",
    )

    transition = repository.load_work_record(
        _event_work(),
        "lifecycle_transition",
        "1",
        "lct_after_correction",
    )
    assert transition.record.field("previous_transition") == _local_ref(
        "lifecycle_transition", "lct_replacement"
    )
    assert "step_transition" in result.accepted_steps
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_status == "invalidated"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_after_correction"
    assert resolution.excluded_transition_ids == frozenset({"lct_old"})
    current_journal = OperationJournalStore(tmp_path).load_current(
        "op_after_correction"
    )
    assert current_journal.revision.field("operation_kind") == "transition_lifecycle"
    assert current_journal.revision.field("state") == "completed"


def test_ordinary_transition_can_continue_from_corrected_creation_baseline(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(
        tmp_path,
        include_replacement=False,
    )
    service = _mutation_service(tmp_path, repository)
    service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_select_baseline_for_transition",
        replaced_head_id="lct_old",
        replacement_head_id=None,
        reason_code="transition_should_not_exist",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )
    current = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert current.record.status == "proposed"

    service.transition(
        _account_reference(),
        _real_account(status="active", updated_at=_AFTER_CORRECTION),
        expected=current.fingerprint,
        transition_id="lct_after_baseline",
        reason_code="review_completed",
        operation_id="op_after_baseline",
    )

    transition = repository.load_work_record(
        _event_work(),
        "lifecycle_transition",
        "1",
        "lct_after_baseline",
    )
    assert transition.record.field("previous_transition") is None
    resolution = service.require_corrected_history_reconciled(_account_reference())
    assert resolution.selected_status == "active"
    assert resolution.selected_head is not None
    assert resolution.selected_head.record.logical_id == "lct_after_baseline"
    assert resolution.excluded_transition_ids == frozenset({"lct_old"})


def test_corrected_transition_rechecks_correction_chain_under_work_lock(
    tmp_path: Path,
) -> None:
    repository, account = _seed_mutation_history(
        tmp_path,
        replacement_status="active",
        replacement_reason="review_completed",
    )
    service = _mutation_service(tmp_path, repository)
    service.correct_history(
        _account_reference(),
        expected=account.fingerprint,
        correction_id="lhc_selected_before_race",
        replaced_head_id="lct_old",
        replacement_head_id="lct_replacement",
        reason_code="wrong_reason",
        created_at=_CORRECTION_AT,
        created_by=AGENT,
    )
    current = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    inserted = False
    work_lock_id = derive_lock_id("work", work_target(_event_work()))

    def change_correction_chain_before_work_lock(
        event: str,
        identifier: str | None,
    ) -> None:
        nonlocal inserted
        if event != "after_lock_acquire" or inserted:
            return
        if identifier is None or identifier == work_lock_id:
            return
        competing = build_lifecycle_history_correction(
            _account_reference(),
            correction_id="lhc_competing_selector",
            previous_correction_id="lhc_selected_before_race",
            replaced_head_id="lct_replacement",
            replacement_head_id="lct_old",
            reason_code="wrong_reason",
            reason_detail=None,
            created_at="2026-08-26T13:30:00-04:00",
            created_by=AGENT,
        )
        repository.create_work_record(_event_work(), competing)
        inserted = True

    with pytest.raises(
        PortiaConflictError,
        match="correction chain changed after transition preflight",
    ):
        service.transition(
            _account_reference(),
            _real_account(status="invalidated", updated_at=_AFTER_CORRECTION),
            expected=current.fingerprint,
            transition_id="lct_raced_transition",
            reason_code="wrong_target",
            operation_id="op_raced_transition",
            fault_hook=change_correction_chain_before_work_lock,
        )

    assert inserted is True
    unchanged = repository.load_work_record(
        _event_work(), "account", "2", "acct_alpha"
    )
    assert unchanged.fingerprint == current.fingerprint
    with pytest.raises(PortiaNotFoundError):
        repository.load_work_record(
            _event_work(),
            "lifecycle_transition",
            "1",
            "lct_raced_transition",
        )
