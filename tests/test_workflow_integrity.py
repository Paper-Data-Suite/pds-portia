from __future__ import annotations

import json
from pathlib import Path

import pytest

from portia.models import parse_portia_record
from portia.storage.errors import PortiaAmbiguousRecoveryError
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import exclusive_create
from portia.storage.paths import operation_revision_path
from portia.storage.series import OperationJournalStore
from portia.workflows import IntegrityWorkflowService, OperationIntegrityEvaluation
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


def _create_operation(tmp_path: Path, data: dict[str, object] | None = None) -> None:
    journal = parse_portia_record(
        "operation_journal",
        "2",
        _journal_data() if data is None else data,
    )
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


def test_operation_persistence_evaluation_is_exact_and_non_mutating(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    store = OperationJournalStore(tmp_path)
    before = store.load_current("op_create_actor")

    evaluation = IntegrityWorkflowService(tmp_path).evaluate_operation_persistence(
        "op_create_actor"
    )
    after = store.load_current("op_create_actor")

    assert isinstance(evaluation, OperationIntegrityEvaluation)
    assert evaluation.operation_id == "op_create_actor"
    assert evaluation.journal_revision == 1
    assert evaluation.journal_fingerprint == before.revision_fingerprint
    assert evaluation.findings == ()
    assert after.revision_fingerprint == before.revision_fingerprint
    assert after.pointer_fingerprint == before.pointer_fingerprint


def test_operation_persistence_evaluation_exposes_storage_finding(
    tmp_path: Path,
) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)

    evaluation = IntegrityWorkflowService(tmp_path).evaluate_operation_persistence(
        "op_create_actor"
    )

    assert len(evaluation.findings) == 1
    finding = evaluation.findings[0]
    assert finding.code == "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH"
    assert finding.relative_path == "portia/actors/actr_other/actor.json"


def test_operation_persistence_evaluation_rejects_absent_series(
    tmp_path: Path,
) -> None:
    with pytest.raises(WorkflowPrerequisiteError, match="resolve recovery state"):
        IntegrityWorkflowService(tmp_path).evaluate_operation_persistence("op_missing")

    assert not (tmp_path / "portia").exists()


def test_operation_persistence_evaluation_rejects_orphan_successor(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    _write_orphan_revision(tmp_path, 2, previous=1, state="staged")

    with pytest.raises(WorkflowPrerequisiteError, match="resolve recovery state"):
        IntegrityWorkflowService(tmp_path).evaluate_operation_persistence(
            "op_create_actor"
        )

    assert OperationJournalStore(tmp_path).load_current(
        "op_create_actor"
    ).revision.to_dict()["journal_revision"] == 1


def test_operation_persistence_evaluation_fails_closed_on_ambiguous_series(
    tmp_path: Path,
) -> None:
    _create_operation(tmp_path)
    _write_orphan_revision(tmp_path, 2, previous=1, state="staged")
    _write_orphan_revision(tmp_path, 3, previous=2, state="committing")

    with pytest.raises(PortiaAmbiguousRecoveryError, match="multiple unselected"):
        IntegrityWorkflowService(tmp_path).evaluate_operation_persistence(
            "op_create_actor"
        )

    assert OperationJournalStore(tmp_path).load_current(
        "op_create_actor"
    ).revision.to_dict()["journal_revision"] == 1
