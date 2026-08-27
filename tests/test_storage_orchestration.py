from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaOperationPartialCommitError,
)
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.locks import derive_lock_id
from portia.storage.orchestration import (
    commit_journaled_candidates,
    stage_journaled_candidates,
    validate_lock_plan,
)


@dataclass(frozen=True)
class FakeLockRecord:
    payload: dict[str, Any]
    contract: str = "operation_lock"
    contract_version: str = "2"

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def _operation_lock(operation_id: str) -> tuple[dict[str, Any], FakeLockRecord]:
    target = {"kind": "operation", "operation_ref": {"operation_id": operation_id}}
    lock_id = derive_lock_id("operation", target)
    entry = {
        "lock_id": lock_id,
        "sequence": 1,
        "lock_scope": "operation",
        "protected_target": target,
        "lock_path": f"portia/locks/{lock_id}.json",
        "disposition": "planned",
        "fingerprint": None,
        "acquired_at": None,
        "released_at": None,
    }
    record = FakeLockRecord(
        {
            "schema_version": "2",
            "record_type": "operation_lock",
            "module_id": "portia",
            "lock_id": lock_id,
            "lock_scope": "operation",
            "protected_target": target,
            "owning_operation": {"operation_id": operation_id},
            "acquired_at": "2026-08-26T12:00:00-04:00",
            "deployment_instance_id": "test_deployment",
            "process_instance_id": "test_process",
        }
    )
    return entry, record


def _journal(
    operation_id: str = "op_storage_test",
) -> tuple[dict[str, Any], dict[str, bytes], dict[str, FakeLockRecord]]:
    lock_entry, lock_record = _operation_lock(operation_id)
    first = b'{"value":1}\n'
    second = b'{"value":2}\n'
    journal = {
        "operation_id": operation_id,
        "state": "staged",
        "lock_set": [lock_entry],
        "write_set": [
            {
                "step_id": "step_first",
                "sequence": 1,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": {"kind": "workspace"},
                "representation_role": "canonical_domain",
                "destination_path": "portia/test/first.json",
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": "1",
                    "fingerprint": fingerprint_bytes(first).to_dict(),
                    "selected_state": [],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": None,
            },
            {
                "step_id": "step_second",
                "sequence": 2,
                "phase": "canonical_gate",
                "action": "exclusive_create",
                "target": {"kind": "workspace"},
                "representation_role": "canonical_domain",
                "destination_path": "portia/test/second.json",
                "precondition": {"presence": "must_be_absent"},
                "intended_result": {
                    "contract_version": "1",
                    "fingerprint": fingerprint_bytes(second).to_dict(),
                    "selected_state": [],
                },
                "disposition": "staged",
                "observed_result": None,
                "compensation_step_id": None,
                "reason_code": None,
            },
        ],
    }
    return (
        journal,
        {"step_first": first, "step_second": second},
        {lock_entry["lock_id"]: lock_record},
    )


def test_coordinated_commit_accepts_bounded_write_set_and_releases_lock(tmp_path: Path) -> None:
    journal, candidates, locks = _journal()
    staged = stage_journaled_candidates(tmp_path, journal, candidates)
    result = commit_journaled_candidates(tmp_path, journal, staged, locks)  # type: ignore[arg-type]

    assert result.accepted_steps == ("step_first", "step_second")
    assert (tmp_path / "portia/test/first.json").read_bytes() == candidates["step_first"]
    assert (tmp_path / "portia/test/second.json").read_bytes() == candidates["step_second"]
    assert not (tmp_path / f"portia/locks/{next(iter(locks))}.json").exists()


def test_failure_after_first_publish_preserves_lock_and_partial_success(tmp_path: Path) -> None:
    journal, candidates, locks = _journal("op_partial_test")
    staged = stage_journaled_candidates(tmp_path, journal, candidates)

    def fail_after_first(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "after_publish" and step_id == "step_first":
            raise RuntimeError("synthetic crash boundary")

    with pytest.raises(PortiaOperationPartialCommitError) as exc_info:
        commit_journaled_candidates(
            tmp_path,
            journal,
            staged,
            locks,  # type: ignore[arg-type]
            fault_hook=fail_after_first,
        )

    assert exc_info.value.accepted_steps == ("step_first",)
    assert (tmp_path / "portia/test/first.json").exists()
    assert not (tmp_path / "portia/test/second.json").exists()
    assert (tmp_path / f"portia/locks/{next(iter(locks))}.json").exists()


def test_failure_before_first_publish_releases_lock_without_canonical_effect(
    tmp_path: Path,
) -> None:
    journal, candidates, locks = _journal("op_precommit_test")
    staged = stage_journaled_candidates(tmp_path, journal, candidates)

    def fail_before_first(checkpoint: str, step_id: str | None) -> None:
        if checkpoint == "before_publish" and step_id == "step_first":
            raise RuntimeError("synthetic precommit failure")

    with pytest.raises(RuntimeError, match="synthetic precommit failure"):
        commit_journaled_candidates(
            tmp_path,
            journal,
            staged,
            locks,  # type: ignore[arg-type]
            fault_hook=fail_before_first,
        )

    assert not (tmp_path / "portia/test/first.json").exists()
    assert not (tmp_path / "portia/test/second.json").exists()
    assert not (tmp_path / f"portia/locks/{next(iter(locks))}.json").exists()


def test_candidate_fingerprint_must_match_journaled_intent(tmp_path: Path) -> None:
    journal, candidates, _locks = _journal("op_fingerprint_test")
    candidates["step_second"] = b"different\n"
    with pytest.raises(PortiaConflictError, match="intended result"):
        stage_journaled_candidates(tmp_path, journal, candidates)


def test_generic_lock_order_requires_operation_before_work() -> None:
    operation_target = {"kind": "operation", "operation_ref": {"operation_id": "op_order"}}
    work_target = {
        "kind": "work",
        "work_ref": {
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_a",
            "work_kind": "event",
            "contract_version": "2",
        },
    }
    entries = []
    for sequence, scope, target in [
        (1, "work", work_target),
        (2, "operation", operation_target),
    ]:
        lock_id = derive_lock_id(scope, target)
        entries.append(
            {
                "lock_id": lock_id,
                "sequence": sequence,
                "lock_scope": scope,
                "protected_target": target,
                "lock_path": f"portia/locks/{lock_id}.json",
            }
        )
    with pytest.raises(PortiaCorruptionError, match="acquisition order"):
        validate_lock_plan({"lock_set": entries})


def test_actor_lock_order_places_collection_and_actor_before_operation() -> None:
    targets = [
        ("actor_directory_collection", {"kind": "actor_directory_collection"}),
        (
            "actor_directory_record",
            {
                "kind": "actor_directory_record",
                "actor_directory_record_ref": {
                    "kind": "actor",
                    "actor_ref": {"actor_id": "actr_a", "contract_version": "1"},
                },
            },
        ),
        ("operation", {"kind": "operation", "operation_ref": {"operation_id": "op_actor"}}),
    ]
    entries = []
    for sequence, (scope, target) in enumerate(targets, start=1):
        lock_id = derive_lock_id(scope, target)
        entries.append(
            {
                "lock_id": lock_id,
                "sequence": sequence,
                "lock_scope": scope,
                "protected_target": target,
                "lock_path": f"portia/locks/{lock_id}.json",
            }
        )
    assert validate_lock_plan({"lock_set": entries}) == tuple(entries)
