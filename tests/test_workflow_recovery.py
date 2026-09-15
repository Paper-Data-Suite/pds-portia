from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage.errors import (
    PortiaAmbiguousRecoveryError,
    PortiaConflictError,
)
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create
from portia.storage.paths import operation_current_path, operation_revision_path
from portia.storage.series import OperationJournalStore
from portia.workflows import RecoveryWorkflowAssessment, RecoveryWorkflowService
from portia.workflows.errors import WorkflowPrerequisiteError

ROOT = Path(__file__).resolve().parents[1]
CREATE_ACTOR_FIXTURE = (
    ROOT
    / "tests"
    / "schema_validation"
    / "fixtures"
    / "issue-14"
    / "actor-aware-operations"
    / "operation-journal"
    / "valid"
    / "create-actor.json"
)


def _journal_data() -> dict[str, object]:
    value = json.loads(CREATE_ACTOR_FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _create_operation(tmp_path: Path) -> None:
    journal = parse_portia_record("operation_journal", "2", _journal_data())
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": "op_create_actor",
            "journal_revision": 1,
        },
    )
    OperationJournalStore(tmp_path).create(journal, pointer)


def _write_orphan_revision(
    tmp_path: Path,
    revision: int,
    *,
    previous: int,
    state: str,
) -> None:
    data = _journal_data()
    data["journal_revision"] = revision
    data["previous_journal_revision"] = previous
    data["state"] = state
    data["updated_at"] = f"2026-08-05T20:00:0{revision + 1}-04:00"
    journal = parse_portia_record("operation_journal", "2", data)
    exclusive_create(
        operation_revision_path(tmp_path, "op_create_actor", revision),
        canonical_json_bytes(journal.to_dict()),
    )


def test_assess_absent_operation_is_non_mutating(tmp_path: Path) -> None:
    assessment = RecoveryWorkflowService(tmp_path).assess("op_missing")

    assert isinstance(assessment, RecoveryWorkflowAssessment)
    assert assessment.operation_id == "op_missing"
    assert assessment.state is None
    assert assessment.disposition == "absent"
    assert assessment.series.valid_revisions == ()
    assert not (tmp_path / "portia").exists()


def test_assess_prepared_operation_exposes_resume_without_mutation(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    current_before = OperationJournalStore(tmp_path).load_current("op_create_actor")

    assessment = RecoveryWorkflowService(tmp_path).assess("op_create_actor")
    current_after = OperationJournalStore(tmp_path).load_current("op_create_actor")

    assert assessment.state == "prepared"
    assert assessment.disposition == "resume"
    assert assessment.findings == ()
    assert current_after.pointer_fingerprint == current_before.pointer_fingerprint
    assert current_after.revision_fingerprint == current_before.revision_fingerprint


def test_restore_exact_orphan_pointer_reassesses_selected_successor(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    _write_orphan_revision(tmp_path, 2, previous=1, state="staged")
    store = OperationJournalStore(tmp_path)
    expected_pointer = store.load_current("op_create_actor").pointer_fingerprint
    service = RecoveryWorkflowService(tmp_path)

    before = service.assess("op_create_actor")
    after = service.restore_exact_orphan_pointer(
        "op_create_actor",
        expected_pointer=expected_pointer,
    )

    assert before.disposition == "restore_pointer_candidate"
    assert before.series.selected_revision == 1
    assert before.series.orphan_successors == (2,)
    assert after.state == "staged"
    assert after.disposition == "resume"
    assert after.series.selected_revision == 2
    assert after.series.orphan_successors == ()
    assert store.load_current("op_create_actor").revision.to_dict()[
        "journal_revision"
    ] == 2

    with pytest.raises(WorkflowPrerequisiteError, match="restore_pointer_candidate"):
        service.restore_exact_orphan_pointer(
            "op_create_actor",
            expected_pointer=expected_pointer,
        )


def test_restore_requires_exact_expected_pointer_fingerprint(tmp_path: Path) -> None:
    _create_operation(tmp_path)
    _write_orphan_revision(tmp_path, 2, previous=1, state="staged")
    store = OperationJournalStore(tmp_path)
    current = store.load_current("op_create_actor")
    stale_pointer = current.pointer_fingerprint

    operation_current_path(tmp_path, "op_create_actor").write_text(
        json.dumps(current.pointer.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    service = RecoveryWorkflowService(tmp_path)
    assert service.assess("op_create_actor").disposition == "restore_pointer_candidate"
    with pytest.raises(PortiaConflictError, match="pointer changed"):
        service.restore_exact_orphan_pointer(
            "op_create_actor",
            expected_pointer=stale_pointer,
        )

    assert service.assess("op_create_actor").series.selected_revision == 1


def test_restore_rejects_non_candidate_before_mutation(tmp_path: Path) -> None:
    _create_operation(tmp_path)
    store = OperationJournalStore(tmp_path)
    expected_pointer = store.load_current("op_create_actor").pointer_fingerprint

    with pytest.raises(WorkflowPrerequisiteError, match="restore_pointer_candidate"):
        RecoveryWorkflowService(tmp_path).restore_exact_orphan_pointer(
            "op_create_actor",
            expected_pointer=expected_pointer,
        )

    assert store.load_current("op_create_actor").revision.to_dict()[
        "journal_revision"
    ] == 1


def test_assess_fails_closed_when_multiple_orphan_revisions_exist(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    _write_orphan_revision(tmp_path, 2, previous=1, state="staged")
    _write_orphan_revision(tmp_path, 3, previous=2, state="committing")

    with pytest.raises(PortiaAmbiguousRecoveryError, match="multiple unselected"):
        RecoveryWorkflowService(tmp_path).assess("op_create_actor")

    assert OperationJournalStore(tmp_path).load_current(
        "op_create_actor"
    ).revision.to_dict()["journal_revision"] == 1
