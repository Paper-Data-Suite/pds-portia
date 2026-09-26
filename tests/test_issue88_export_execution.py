from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from portia.models import parse_portia_record
from portia.storage.deliberate_export_operations import (
    DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
)
from portia.storage.deliberate_export_persistence import (
    commit_deliberate_export_candidates,
    stage_deliberate_export_candidates,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.locks import LockStore, derive_lock_id
from portia.storage.orchestration import commit_journaled_candidates
from portia.storage.series import OperationJournalStore

ROOT = Path(__file__).resolve().parents[1]
V3_FIXTURE = (
    ROOT
    / "tests/schema_validation/fixtures/issue-47/"
    "operation-journal-v3/valid/v3-present-write.json"
)
EXPORT_FIXTURE = (
    ROOT
    / "tests/schema_validation/fixtures/issue-21/"
    "deliberate-export/valid/administrative-csv.json"
)

EXPORT_ID = "pexp_issue88_execution_01"
EXPORT_REF = {"export_id": EXPORT_ID, "contract_version": "1"}
EXPORT_TARGET = {"kind": "deliberate_export", "export_ref": EXPORT_REF}
ARTIFACT_PATH = f"portia/exports/{EXPORT_ID}/artifact.csv"
PROVENANCE_PATH = f"portia/exports/{EXPORT_ID}/export.json"
OPERATION_ID = "op_issue88_export_execution"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _preflight(role: str, path: str, contract_version: str) -> dict[str, Any]:
    return {
        "target": copy.deepcopy(EXPORT_TARGET),
        "representation_role": role,
        "expected_state": {"presence": "must_be_absent"},
        "workspace_relative_path": path,
        "contract_version": contract_version,
        "source_basis": "canonical",
        "source_projection": None,
        "selected_state": [],
        "observed_at": "2026-08-05T20:00:01-04:00",
    }


def _write(
    *,
    step_id: str,
    sequence: int,
    role: str,
    path: str,
    contract_version: str,
    fingerprint: dict[str, Any],
    selected_state: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "step_id": step_id,
        "sequence": sequence,
        "phase": "canonical_gate",
        "action": "exclusive_create",
        "target": copy.deepcopy(EXPORT_TARGET),
        "representation_role": role,
        "destination_path": path,
        "precondition": {"presence": "must_be_absent"},
        "intended_result": {
            "kind": "present",
            "contract_version": contract_version,
            "fingerprint": copy.deepcopy(fingerprint),
            "selected_state": copy.deepcopy(selected_state),
        },
        "disposition": "staged",
        "observed_result": None,
        "compensation_step_id": None,
        "reason_code": None,
    }


def _export(artifact_bytes: bytes) -> dict[str, Any]:
    value = _load(EXPORT_FIXTURE)
    artifact_fp = fingerprint_bytes(artifact_bytes)
    value["export_id"] = EXPORT_ID
    output = value["output"]
    assert isinstance(output, dict)
    output["workspace_relative_path"] = ARTIFACT_PATH
    output["byte_length"] = artifact_fp.byte_length
    output["sha256_digest"] = artifact_fp.digest
    value["operation_journal_ref"] = {
        "operation_id": OPERATION_ID,
        "journal_revision": 2,
        "contract_version": "4",
    }
    return value


def _journal(
    artifact_bytes: bytes,
    export: dict[str, Any],
    *,
    revision: int = 1,
    previous: int | None = None,
    state: str = "staged",
) -> dict[str, Any]:
    value = _load(V3_FIXTURE)
    value["schema_version"] = "4"
    value["operation_id"] = OPERATION_ID
    value["operation_kind"] = "generate_deliberate_export"
    value["scope"] = "workspace"
    value["primary_target"] = copy.deepcopy(EXPORT_TARGET)
    value["affected_targets"] = []
    value["intent_facts"] = []
    value["journal_revision"] = revision
    value["previous_journal_revision"] = previous
    value["state"] = state

    artifact_fp = fingerprint_bytes(artifact_bytes).to_dict()
    provenance_fp = fingerprint_bytes(canonical_json_bytes(export)).to_dict()

    value["preflight_snapshot"] = [
        _preflight(
            "deliberate_export_artifact",
            ARTIFACT_PATH,
            DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
        ),
        _preflight("deliberate_export_provenance", PROVENANCE_PATH, "1"),
    ]
    lock_id = derive_lock_id("deliberate_export", EXPORT_TARGET)
    value["lock_set"] = [
        {
            "lock_id": lock_id,
            "sequence": 1,
            "lock_scope": "deliberate_export",
            "protected_target": copy.deepcopy(EXPORT_TARGET),
            "lock_path": f"portia/locks/{lock_id}.json",
            "disposition": "planned",
            "fingerprint": None,
            "acquired_at": None,
            "released_at": None,
        }
    ]
    value["write_set"] = [
        _write(
            step_id="step_export_artifact",
            sequence=1,
            role="deliberate_export_artifact",
            path=ARTIFACT_PATH,
            contract_version=DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
            fingerprint=artifact_fp,
            selected_state=[],
        ),
        _write(
            step_id="step_export_provenance",
            sequence=2,
            role="deliberate_export_provenance",
            path=PROVENANCE_PATH,
            contract_version="1",
            fingerprint=provenance_fp,
            selected_state=[
                {
                    "name": "committed_journal_revision",
                    "kind": "integer",
                    "value": 2,
                }
            ],
        ),
    ]
    value["staged_artifacts"] = []
    value["compensation_plan"] = []
    value["recovery_plan"] = [
        "resume",
        "complete_remaining_steps",
        "abandon_preacceptance_artifacts",
        "require_manual_review",
    ]
    value["commit_point"] = {
        "reached": state in {"committed", "completed"},
        "reached_at": (
            "2026-08-05T20:00:04-04:00"
            if state in {"committed", "completed"}
            else None
        ),
    }
    partial = value["partial_state"]
    assert isinstance(partial, dict)
    partial["accepted_steps"] = []
    partial["verified_steps"] = []
    partial["durable_unverified_steps"] = []
    partial["indeterminate_steps"] = []
    partial["remaining_canonical_steps"] = [
        "step_export_artifact",
        "step_export_provenance",
    ]
    partial["remaining_post_commit_steps"] = []
    partial["current_pointer_changes"] = []
    partial["held_or_possible_locks"] = []
    partial["quarantined_targets"] = []
    partial["active_finding_keys"] = []
    partial["durability_assessment"] = "none"
    partial["recommended_disposition"] = "resume"

    if state in {"committed", "completed"}:
        write_set = value["write_set"]
        assert isinstance(write_set, list)
        for step in write_set:
            assert isinstance(step, dict)
            step["disposition"] = "accepted"
            intended = step["intended_result"]
            assert isinstance(intended, dict)
            step["observed_result"] = {
                "kind": "present",
                "workspace_relative_path": step["destination_path"],
                "fingerprint": copy.deepcopy(intended["fingerprint"]),
                "observed_at": "2026-08-05T20:00:03-04:00",
            }
        partial["accepted_steps"] = [
            "step_export_artifact",
            "step_export_provenance",
        ]
        partial["verified_steps"] = [
            "step_export_artifact",
            "step_export_provenance",
        ]
        partial["remaining_canonical_steps"] = []
        partial["durability_assessment"] = "confirmed"
        partial["recommended_disposition"] = None

    return value


def _lock() -> dict[str, Any]:
    lock_id = derive_lock_id("deliberate_export", EXPORT_TARGET)
    return {
        "schema_version": "3",
        "record_type": "operation_lock",
        "module_id": "portia",
        "lock_id": lock_id,
        "lock_scope": "deliberate_export",
        "protected_target": copy.deepcopy(EXPORT_TARGET),
        "owning_operation": {"operation_id": OPERATION_ID},
        "acquired_at": "2026-08-05T20:00:02-04:00",
        "deployment_instance_id": "test_deployment",
        "process_instance_id": "test_process",
    }


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


def _records(artifact_bytes: bytes):
    export = parse_portia_record("deliberate_export", "1", _export(artifact_bytes))
    journal = parse_portia_record(
        "operation_journal",
        "4",
        _journal(artifact_bytes, export.to_dict()),
    )
    lock = parse_portia_record("operation_lock", "3", _lock())
    return journal, export, lock


def test_specialized_export_execution_publishes_artifact_then_provenance(
    tmp_path: Path,
) -> None:
    artifact = b"student_id,score\ns1,87\n"
    journal, export, lock = _records(artifact)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        journal,
        artifact_bytes=artifact,
        export=export,
    )
    assert tuple(item.step_id for item in staged) == (
        "step_export_artifact",
        "step_export_provenance",
    )
    result = commit_deliberate_export_candidates(
        tmp_path,
        journal,
        staged,
        artifact_bytes=artifact,
        export=export,
        lock=lock,
    )
    assert result.accepted_steps == (
        "step_export_artifact",
        "step_export_provenance",
    )
    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == canonical_json_bytes(
        export.to_dict()
    )
    lock_id = lock.field("lock_id")
    assert isinstance(lock_id, str)
    assert not (tmp_path / f"portia/locks/{lock_id}.json").exists()


def test_direct_generic_v4_execution_remains_closed(tmp_path: Path) -> None:
    artifact = b"a,b\n1,2\n"
    journal, export, lock = _records(artifact)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        journal,
        artifact_bytes=artifact,
        export=export,
    )
    lock_id = lock.field("lock_id")
    assert isinstance(lock_id, str)
    with pytest.raises(PortiaConflictError, match="specialized Issue #88"):
        commit_journaled_candidates(tmp_path, journal, staged, {lock_id: lock})


def test_failure_after_artifact_preserves_exact_v3_lock_for_recovery(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    journal, export, lock = _records(artifact)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        journal,
        artifact_bytes=artifact,
        export=export,
    )

    def fail_after_artifact(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_export_artifact":
            raise RuntimeError("synthetic export crash")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        commit_deliberate_export_candidates(
            tmp_path,
            journal,
            staged,
            artifact_bytes=artifact,
            export=export,
            lock=lock,
            fault_hook=fail_after_artifact,
        )
    assert exc_info.value.accepted_steps == ("step_export_artifact",)
    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact
    assert not (tmp_path / PROVENANCE_PATH).exists()
    lock_id = lock.field("lock_id")
    assert isinstance(lock_id, str)
    assert (tmp_path / f"portia/locks/{lock_id}.json").exists()


def test_failure_before_artifact_releases_export_lock(tmp_path: Path) -> None:
    artifact = b"a,b\n1,2\n"
    journal, export, lock = _records(artifact)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        journal,
        artifact_bytes=artifact,
        export=export,
    )

    def fail_before_artifact(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "before_publish" and step_id == "step_export_artifact":
            raise RuntimeError("synthetic preacceptance crash")

    with pytest.raises(RuntimeError, match="synthetic preacceptance"):
        commit_deliberate_export_candidates(
            tmp_path,
            journal,
            staged,
            artifact_bytes=artifact,
            export=export,
            lock=lock,
            fault_hook=fail_before_artifact,
        )
    assert not (tmp_path / ARTIFACT_PATH).exists()
    assert not (tmp_path / PROVENANCE_PATH).exists()
    lock_id = lock.field("lock_id")
    assert isinstance(lock_id, str)
    assert not (tmp_path / f"portia/locks/{lock_id}.json").exists()


def test_operation_lock_v3_can_be_acquired_and_released_exactly(
    tmp_path: Path,
) -> None:
    lock = parse_portia_record("operation_lock", "3", _lock())
    store = LockStore(tmp_path)
    held = store.acquire(lock)
    assert held.path.exists()
    store.release(held)
    assert not held.path.exists()


def test_operation_journal_store_persists_v4_staged_committed_completed_series(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = parse_portia_record("deliberate_export", "1", _export(artifact))
    store = OperationJournalStore(tmp_path)
    staged = parse_portia_record(
        "operation_journal",
        "4",
        _journal(artifact, export.to_dict()),
    )
    current = store.create(staged, _pointer(1))
    committed = parse_portia_record(
        "operation_journal",
        "4",
        _journal(
            artifact,
            export.to_dict(),
            revision=2,
            previous=1,
            state="committed",
        ),
    )
    current = store.append(
        committed,
        _pointer(2),
        expected_pointer=current.pointer_fingerprint,
    )
    completed = parse_portia_record(
        "operation_journal",
        "4",
        _journal(
            artifact,
            export.to_dict(),
            revision=3,
            previous=2,
            state="completed",
        ),
    )
    store.append(
        completed,
        _pointer(3),
        expected_pointer=current.pointer_fingerprint,
    )
    selected = store.load_current(OPERATION_ID)
    assert selected.revision.contract_version == "4"
    assert selected.revision.field("state") == "completed"
    assert selected.pointer.field("journal_revision") == 3


def test_v4_series_rejects_rewriting_export_intent_after_commit(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = parse_portia_record("deliberate_export", "1", _export(artifact))
    store = OperationJournalStore(tmp_path)
    staged = parse_portia_record(
        "operation_journal",
        "4",
        _journal(artifact, export.to_dict()),
    )
    current = store.create(staged, _pointer(1))
    committed = parse_portia_record(
        "operation_journal",
        "4",
        _journal(
            artifact,
            export.to_dict(),
            revision=2,
            previous=1,
            state="committed",
        ),
    )
    current = store.append(
        committed,
        _pointer(2),
        expected_pointer=current.pointer_fingerprint,
    )
    rewritten = _journal(
        artifact,
        export.to_dict(),
        revision=3,
        previous=2,
        state="completed",
    )
    preflight = rewritten["preflight_snapshot"]
    assert isinstance(preflight, list)
    first_preflight = preflight[0]
    assert isinstance(first_preflight, dict)
    first_preflight["observed_at"] = "2026-08-05T20:00:09-04:00"
    rewritten_record = parse_portia_record(
        "operation_journal",
        "4",
        rewritten,
    )
    with pytest.raises(PortiaConflictError, match="immutable write intent"):
        store.append(
            rewritten_record,
            _pointer(3),
            expected_pointer=current.pointer_fingerprint,
        )
