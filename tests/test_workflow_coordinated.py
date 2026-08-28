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
        "part_alpha",
    ).exists()
    current = OperationJournalStore(tmp_path).load_current("op_bundle_partial")
    current_data = current.revision.to_dict()
    assert current_data["state"] == "failed"
    assert current_data["partial_state"]["accepted_steps"] == ["step_1"]
    assessment = OperationRecovery(tmp_path).assess("op_bundle_partial")
    assert assessment.disposition == "manual_review"
    assert assessment.findings == ()

    accepted_event = repository.load_work(event_ref()).fingerprint
    with pytest.raises((PortiaConflictError, PortiaOperationPartialCommitError)):
        EventBundleWorkflowService(tmp_path).commit(
            bundle,
            operation_id="op_bundle_partial",
        )
    assert repository.load_work(event_ref()).fingerprint == accepted_event
    assert not work_record_path(
        tmp_path,
        event_ref(),
        "event_participant",
        "part_alpha",
    ).exists()
