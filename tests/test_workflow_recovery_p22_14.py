from __future__ import annotations

import json
from pathlib import Path

from portia.models import parse_portia_record
from portia.storage.io import exclusive_create
from portia.storage.paths import (
    lock_path,
    resolve_workspace_relative,
    workspace_relative,
)
from portia.storage.series import OperationJournalStore
from portia.storage.staging import stage_bytes, staging_path_for
from portia.workflows import RecoveryWorkflowService

ROOT = Path(__file__).resolve().parents[1]
P22 = (
    ROOT
    / "tests"
    / "fixtures"
    / "issue_22"
    / "positive"
    / "p22_14_coordinated_operation_recovery"
)
OPERATION_ID = "op_p22_recovery_relationship"


def _json(name: str) -> dict[str, object]:
    value = json.loads((P22 / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _pointer(revision: int):
    return parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": OPERATION_ID,
            "journal_revision": revision,
        },
    )


def test_p22_14_production_recovery_preserves_successor_and_finishes_predecessor(
    tmp_path: Path,
) -> None:
    store = OperationJournalStore(tmp_path)
    current = None
    for revision in range(1, 5):
        journal_value = _json(f"operation-journal-r{revision}.json")
        if revision == 4:
            artifacts = journal_value["staged_artifacts"]
            assert isinstance(artifacts, list)
            for artifact in artifacts:
                assert isinstance(artifact, dict)
                artifact["staging_path"] = workspace_relative(
                    tmp_path,
                    staging_path_for(
                        tmp_path,
                        OPERATION_ID,
                        artifact["step_id"],
                        artifact["destination_path"],
                    ),
                )
        journal = parse_portia_record(
            "operation_journal",
            "2",
            journal_value,
        )
        if current is None:
            current = store.create(journal, _pointer(revision))
        else:
            current = store.append(
                journal,
                _pointer(revision),
                expected_pointer=current.pointer_fingerprint,
            )
    assert current is not None
    journal_data = current.revision.to_dict()
    write_set = journal_data["write_set"]
    assert isinstance(write_set, list)
    successor_step = write_set[0]
    predecessor_step = write_set[1]
    assert isinstance(successor_step, dict)
    assert isinstance(predecessor_step, dict)

    successor_bytes = (P22 / "relationship-corrected.json").read_bytes()
    predecessor_active_bytes = (P22 / "preflight-old-active.json").read_bytes()
    predecessor_superseded_bytes = (P22 / "staged-original-superseded.json").read_bytes()
    successor_path = resolve_workspace_relative(
        tmp_path, successor_step["destination_path"]
    )
    predecessor_path = resolve_workspace_relative(
        tmp_path, predecessor_step["destination_path"]
    )
    exclusive_create(successor_path, successor_bytes)
    exclusive_create(predecessor_path, predecessor_active_bytes)

    stage_bytes(
        tmp_path,
        OPERATION_ID,
        str(successor_step["step_id"]),
        successor_step["destination_path"],
        successor_bytes,
    )
    stage_bytes(
        tmp_path,
        OPERATION_ID,
        str(predecessor_step["step_id"]),
        predecessor_step["destination_path"],
        predecessor_superseded_bytes,
    )
    for name in ("operation-lock.json", "work-lock.json"):
        lock_data = _json(name)
        lock_id = lock_data["lock_id"]
        assert isinstance(lock_id, str)
        exclusive_create(lock_path(tmp_path, lock_id), (P22 / name).read_bytes())

    service = RecoveryWorkflowService(tmp_path)
    assessment = service.assess(OPERATION_ID)
    assert assessment.state == "recovering"
    assert assessment.disposition == "resume"
    assert [item.disposition for item in assessment.step_evidence] == [
        "accepted",
        "not_written",
    ]
    accepted_successor = successor_path.read_bytes()

    recovered = service.resume_incomplete(
        OPERATION_ID,
        expected_pointer=current.pointer_fingerprint,
    )
    assert recovered.disposition == "terminal_consistent"
    assert successor_path.read_bytes() == accepted_successor
    assert predecessor_path.read_bytes() == predecessor_superseded_bytes
    assert store.load_current(OPERATION_ID).revision.to_dict()["journal_revision"] == 6
    assert tuple((tmp_path / "portia" / "locks").glob("*.json")) == ()
