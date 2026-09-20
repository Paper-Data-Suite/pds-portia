from __future__ import annotations

from pathlib import Path

import pytest
from pds_core.classes import write_class_roster
from pds_core.rosters import create_roster

from portia.storage import (
    OperationJournalStore,
    PortiaConflictError,
    PortiaOperationPartialCommitError,
    PortiaRepository,
)
from portia.storage.paths import work_record_path
from portia.storage.recovery import OperationRecovery
from portia.workflows import (
    EventBundle,
    EventBundleWorkflowService,
    EventWorkflowService,
    RecoveryWorkflowService,
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)
from tests.workflow_helpers import (
    event_record,
    event_ref,
    participant_record,
    role_record,
)


def _roster(root: Path) -> None:
    write_class_roster(
        root,
        create_roster(
            "class_a",
            [
                {
                    "student_id": "student_1",
                    "last_name": "Student",
                    "first_name": "Synthetic",
                    "period": "2",
                }
            ],
        ),
    )


def test_valid_bundle_commits_through_coordinated_canonical_gate(tmp_path: Path) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
        roles=(role_record(),),  # type: ignore[arg-type]
    )
    result = EventBundleWorkflowService(tmp_path).commit(bundle)
    assert result.accepted_steps == ("step_1", "step_2", "step_3")
    repository = PortiaRepository(tmp_path)
    assert repository.load_work(event_ref()).record.logical_id == "evt_alpha"
    assert len(repository.list_event_participants(event_ref())) == 1
    assert len(repository.list_event_participant_roles(event_ref())) == 1

    current = OperationJournalStore(tmp_path).load_current(result.operation_id)
    assert current.revision.to_dict()["state"] == "completed"
    assessment = OperationRecovery(tmp_path).assess(result.operation_id)
    assert assessment.disposition == "terminal_consistent"

    replay = EventBundleWorkflowService(tmp_path).commit(bundle)
    assert replay.operation_id == result.operation_id
    assert replay.accepted_steps == result.accepted_steps
    assert len(repository.list_event_participants(event_ref())) == 1
    assert len(repository.list_event_participant_roles(event_ref())) == 1


def test_stale_existing_event_preflight_has_zero_child_writes(tmp_path: Path) -> None:
    _roster(tmp_path)
    created = EventWorkflowService(tmp_path).create(event_record(status="draft"))
    bundle = EventBundle(
        event=event_record(status="draft"),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )
    stale = type(created.fingerprint)(
        algorithm="sha256", digest="0" * 64, byte_length=0
    )
    with pytest.raises(PortiaConflictError):
        EventBundleWorkflowService(tmp_path).commit(
            bundle, expected_event=stale
        )
    assert PortiaRepository(tmp_path).list_event_participants(event_ref()) == ()


def test_active_event_bundle_without_participant_is_zero_write(tmp_path: Path) -> None:
    bundle = EventBundle(event=event_record())  # type: ignore[arg-type]
    with pytest.raises(WorkflowPrerequisiteError):
        EventBundleWorkflowService(tmp_path).commit(bundle)
    assert not (tmp_path / "classes").exists()


def test_bundle_accepts_active_role_under_draft_event(tmp_path: Path) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(status="draft"),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
        roles=(role_record(),),  # type: ignore[arg-type]
    )
    EventBundleWorkflowService(tmp_path).commit(bundle)
    repository = PortiaRepository(tmp_path)
    assert repository.load_work(event_ref()).record.status == "draft"
    roles = repository.list_event_participant_roles(event_ref())
    assert len(roles) == 1
    assert roles[0].record.status == "active"


def test_invalid_bundle_fails_before_any_canonical_domain_write(tmp_path: Path) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(
            participant_record(event_id="evt_other"),  # type: ignore[arg-type]
        ),
    )
    with pytest.raises(WorkflowOwnershipError):
        EventBundleWorkflowService(tmp_path).commit(bundle)
    assert not (tmp_path / "classes/class_a/modules/portia/work/evt_alpha").exists()


def test_partial_bundle_commit_preserves_journal_and_exact_canonical_evidence(
    tmp_path: Path,
) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )

    def fail_after_event(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_1":
            raise RuntimeError("synthetic interrupted bundle")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_partial",
            fault_hook=fail_after_event,
        )

    assert exc_info.value.accepted_steps == ("step_1",)
    repository = PortiaRepository(tmp_path)
    assert repository.load_work(event_ref()).record.logical_id == "evt_alpha"
    assert not work_record_path(
        tmp_path,
        event_ref(),
        "event_participant",
        "ep_alpha",
    ).exists()
    current = OperationJournalStore(tmp_path).load_current("op_bundle_partial")
    current_data = current.revision.to_dict()
    assert current_data["state"] == "recovering"
    assert current_data["partial_state"]["accepted_steps"] == ["step_1"]
    assessment = OperationRecovery(tmp_path).assess("op_bundle_partial")
    assert assessment.disposition == "resume"
    assert assessment.findings == ()
    assert [item.disposition for item in assessment.step_evidence] == [
        "accepted",
        "not_written",
    ]

    accepted_event = repository.load_work(event_ref()).fingerprint
    recovered = RecoveryWorkflowService(tmp_path).resume_incomplete(
        "op_bundle_partial",
        expected_pointer=current.pointer_fingerprint,
    )
    assert recovered.disposition == "terminal_consistent"
    assert repository.load_work(event_ref()).fingerprint == accepted_event
    assert work_record_path(
        tmp_path,
        event_ref(),
        "event_participant",
        "ep_alpha",
    ).exists()
    assert RecoveryWorkflowService(tmp_path).resume_incomplete(
        "op_bundle_partial",
        expected_pointer=current.pointer_fingerprint,
    ).disposition == "terminal_consistent"
    assert len(repository.list_event_participants(event_ref())) == 1


def test_interruption_before_first_canonical_write_replays_without_duplicate(
    tmp_path: Path,
) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )

    def stop_before_publish(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "before_publish" and step_id == "step_1":
            raise RuntimeError("synthetic pre-publication interruption")

    with pytest.raises(RuntimeError, match="pre-publication"):
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_no_write",
            fault_hook=stop_before_publish,
        )
    assessment = OperationRecovery(tmp_path).assess("op_bundle_no_write")
    assert assessment.disposition == "resume"
    assert {item.disposition for item in assessment.step_evidence} == {"not_written"}

    first = EventBundleWorkflowService(tmp_path).commit(
        bundle,
        operation_id="op_bundle_no_write",
    )
    replay = EventBundleWorkflowService(tmp_path).commit(
        bundle,
        operation_id="op_bundle_no_write",
    )
    assert first.accepted_steps == replay.accepted_steps == ("step_1", "step_2")
    assert len(PortiaRepository(tmp_path).list_event_participants(event_ref())) == 1


def test_recovery_reconciles_journal_lag_without_rewriting_durable_results(
    tmp_path: Path,
) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )

    def interrupt_initial(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_1":
            raise RuntimeError("synthetic initial interruption")

    with pytest.raises(PortiaOperationPartialCommitError):
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_journal_lag",
            fault_hook=interrupt_initial,
        )
    current = OperationJournalStore(tmp_path).load_current("op_bundle_journal_lag")

    def interrupt_recovery(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_recovery_publish" and step_id == "step_2":
            raise RuntimeError("synthetic recovery journal lag")

    service = RecoveryWorkflowService(tmp_path)
    with pytest.raises(RuntimeError, match="journal lag"):
        service.resume_incomplete(
            "op_bundle_journal_lag",
            expected_pointer=current.pointer_fingerprint,
            fault_hook=interrupt_recovery,
        )
    lagged = service.assess("op_bundle_journal_lag")
    assert [item.disposition for item in lagged.step_evidence] == [
        "accepted",
        "durable_unverified",
    ]
    participant = PortiaRepository(tmp_path).load_work_record(
        event_ref(), "event_participant", "3", "ep_alpha"
    )
    accepted = participant.fingerprint

    reconciled = service.reconcile_as_complete(
        "op_bundle_journal_lag",
        expected_pointer=current.pointer_fingerprint,
    )
    assert reconciled.disposition == "terminal_consistent"
    assert PortiaRepository(tmp_path).load_work_record(
        event_ref(), "event_participant", "3", "ep_alpha"
    ).fingerprint == accepted


def test_committed_recovery_finalizes_post_commit_on_second_run(tmp_path: Path) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )

    def interrupt_initial(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_1":
            raise RuntimeError("synthetic initial interruption")

    with pytest.raises(PortiaOperationPartialCommitError):
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_post_commit",
            fault_hook=interrupt_initial,
        )
    current = OperationJournalStore(tmp_path).load_current("op_bundle_post_commit")

    def stop_after_commit(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_recovery_commit_journal":
            raise RuntimeError("synthetic post-commit interruption")

    service = RecoveryWorkflowService(tmp_path)
    with pytest.raises(RuntimeError, match="post-commit"):
        service.resume_incomplete(
            "op_bundle_post_commit",
            expected_pointer=current.pointer_fingerprint,
            fault_hook=stop_after_commit,
        )
    committed = OperationJournalStore(tmp_path).load_current("op_bundle_post_commit")
    assert service.assess("op_bundle_post_commit").disposition == "finalize_post_commit"

    final = service.finalize_post_commit(
        "op_bundle_post_commit",
        expected_pointer=committed.pointer_fingerprint,
    )
    assert final.disposition == "terminal_consistent"


def test_conflicting_durable_bytes_fail_closed_without_rollback(tmp_path: Path) -> None:
    _roster(tmp_path)
    bundle = EventBundle(
        event=event_record(),  # type: ignore[arg-type]
        participants=(participant_record(),),  # type: ignore[arg-type]
    )

    def interrupt_initial(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_1":
            raise RuntimeError("synthetic initial interruption")

    with pytest.raises(PortiaOperationPartialCommitError):
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_conflict",
            fault_hook=interrupt_initial,
        )
    current = OperationJournalStore(tmp_path).load_current("op_bundle_conflict")
    event_path = current.revision.to_dict()["write_set"][0]["destination_path"]
    assert isinstance(event_path, str)
    absolute = tmp_path / Path(event_path)
    absolute.write_bytes(b'{"foreign":"bytes"}\n')
    conflicting = absolute.read_bytes()

    assessment = RecoveryWorkflowService(tmp_path).assess("op_bundle_conflict")
    assert assessment.disposition == "quarantine_or_manual_review"
    assert {finding.code for finding in assessment.findings} >= {
        "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH"
    }
    with pytest.raises(WorkflowPrerequisiteError, match="resumable"):
        RecoveryWorkflowService(tmp_path).resume_incomplete(
            "op_bundle_conflict",
            expected_pointer=current.pointer_fingerprint,
        )
    assert absolute.read_bytes() == conflicting
