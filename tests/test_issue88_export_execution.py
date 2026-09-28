from __future__ import annotations

import copy
import json
from collections.abc import Mapping
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
from portia.storage.deliberate_export_recovery import DeliberateExportRecovery
from portia.storage.deliberate_export_recovery_actions import (
    finalize_deliberate_export,
    recover_deliberate_export_committed_revision,
    recover_deliberate_export_provenance,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaLockError,
    PortiaOperationPartialCommitError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.io import exclusive_create
from portia.storage.locks import LockStore, derive_lock_id
from portia.storage.orchestration import commit_journaled_candidates
from portia.storage.paths import (
    lock_path,
    operation_revision_path,
    validate_workspace_relative_path,
    workspace_relative,
)
from portia.storage.recovery import OperationRecovery
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


def _persist_staged_export_series(tmp_path: Path, artifact: bytes):
    export = parse_portia_record("deliberate_export", "1", _export(artifact))
    staged = parse_portia_record(
        "operation_journal",
        "4",
        _journal(artifact, export.to_dict()),
    )
    store = OperationJournalStore(tmp_path)
    current = store.create(staged, _pointer(1))
    return export, store, current


def _persist_exact_export_outputs(
    tmp_path: Path,
    artifact: bytes,
    export,
) -> None:
    exclusive_create(tmp_path / ARTIFACT_PATH, artifact)
    exclusive_create(
        tmp_path / PROVENANCE_PATH,
        canonical_json_bytes(export.to_dict()),
    )


def _append_committed_export_revision(
    store: OperationJournalStore,
    current,
    artifact: bytes,
    export,
):
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
    return store.append(
        committed,
        _pointer(2),
        expected_pointer=current.pointer_fingerprint,
    )


def test_export_recovery_classifies_nothing_durable(tmp_path: Path) -> None:
    artifact = b"a,b\\n1,2\\n"
    _export_record, _store, _current = _persist_staged_export_series(
        tmp_path,
        artifact,
    )
    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "nothing_durable"
    assert OperationRecovery(tmp_path).assess(OPERATION_ID).disposition == "resume"


def test_export_recovery_classifies_artifact_only(tmp_path: Path) -> None:
    artifact = b"a,b\\n1,2\\n"
    _export_record, _store, _current = _persist_staged_export_series(
        tmp_path,
        artifact,
    )
    exclusive_create(tmp_path / ARTIFACT_PATH, artifact)

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "artifact_only"
    assert assessment.artifact is not None
    assert assessment.artifact.disposition == "exact"


def test_export_recovery_classifies_artifact_mismatch(tmp_path: Path) -> None:
    artifact = b"a,b\\n1,2\\n"
    _export_record, _store, _current = _persist_staged_export_series(
        tmp_path,
        artifact,
    )
    exclusive_create(tmp_path / ARTIFACT_PATH, b"different\\n")

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "artifact_mismatch"
    assert (
        OperationRecovery(tmp_path).assess(OPERATION_ID).disposition
        == "quarantine_or_manual_review"
    )


def test_export_recovery_classifies_provenance_only(tmp_path: Path) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    exclusive_create(
        tmp_path / PROVENANCE_PATH,
        canonical_json_bytes(export.to_dict()),
    )

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "provenance_only"


def test_export_recovery_classifies_artifact_and_provenance_mismatch(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    _export_record, _store, _current = _persist_staged_export_series(
        tmp_path,
        artifact,
    )
    exclusive_create(tmp_path / ARTIFACT_PATH, b"different-artifact\\n")
    exclusive_create(tmp_path / PROVENANCE_PATH, b"{}\\n")

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "artifact_provenance_mismatch"


def test_export_recovery_classifies_exact_pair_with_committed_journal_missing(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "exact_both_committed_journal_missing"
    assert assessment.planned_committed_revision == 2


def test_export_recovery_classifies_committed(tmp_path: Path) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, store, current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)
    _append_committed_export_revision(store, current, artifact, export)

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "committed"
    assert assessment.selected_revision == 2
    assert (
        OperationRecovery(tmp_path).assess(OPERATION_ID).disposition
        == "finalize_post_commit"
    )


def test_export_recovery_classifies_completed_without_rewriting_provenance(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, store, current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)
    current = _append_committed_export_revision(
        store,
        current,
        artifact,
        export,
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

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "completed"
    assert assessment.planned_committed_revision == 2
    assert assessment.selected_revision == 3
    operation_ref = export.field("operation_journal_ref")
    assert isinstance(operation_ref, Mapping)
    assert operation_ref["journal_revision"] == 2
    assert (
        OperationRecovery(tmp_path).assess(OPERATION_ID).disposition
        == "terminal_consistent"
    )


def test_export_recovery_classifies_unreadable_durable_state_as_indeterminate(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    _export_record, _store, _current = _persist_staged_export_series(
        tmp_path,
        artifact,
    )
    (tmp_path / ARTIFACT_PATH).mkdir(parents=True)

    assessment = DeliberateExportRecovery(tmp_path).assess(OPERATION_ID)
    assert assessment.disposition == "indeterminate"
    assert (
        OperationRecovery(tmp_path).assess(OPERATION_ID).disposition
        == "quarantine_or_manual_review"
    )


def test_artifact_only_recovery_creates_only_missing_provenance(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    exclusive_create(tmp_path / ARTIFACT_PATH, artifact)
    before_artifact = (tmp_path / ARTIFACT_PATH).read_bytes()

    result = recover_deliberate_export_provenance(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert result.action == "created_missing_provenance"
    assert result.assessment.disposition == "exact_both_committed_journal_missing"
    assert (tmp_path / ARTIFACT_PATH).read_bytes() == before_artifact
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == canonical_json_bytes(
        export.to_dict()
    )


def test_missing_provenance_recovery_exact_replay_does_not_duplicate(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)
    before = (tmp_path / PROVENANCE_PATH).read_bytes()

    result = recover_deliberate_export_provenance(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert result.action == "exact_replay"
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == before


@pytest.mark.parametrize(
    "artifact_bytes,provenance_bytes",
    [
        (b"different\\n", None),
        (None, b"{}\\n"),
        (b"different\\n", b"{}\\n"),
    ],
)
def test_provenance_recovery_refuses_unsafe_durable_states(
    tmp_path: Path,
    artifact_bytes: bytes | None,
    provenance_bytes: bytes | None,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    if artifact_bytes is not None:
        exclusive_create(tmp_path / ARTIFACT_PATH, artifact_bytes)
    if provenance_bytes is not None:
        exclusive_create(tmp_path / PROVENANCE_PATH, provenance_bytes)

    with pytest.raises(
        PortiaRecoveryRequiredError,
        match="provenance recovery is not safe",
    ):
        recover_deliberate_export_provenance(
            tmp_path,
            OPERATION_ID,
            export=export,
        )


def test_exact_pair_recovery_creates_reserved_committed_revision(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)

    result = recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:03-04:00",
        committed_at="2026-08-05T20:00:04-04:00",
    )

    assert result.action == "created_missing_committed_revision"
    assert result.assessment.disposition == "committed"
    assert result.assessment.selected_revision == 2
    selected = OperationJournalStore(tmp_path).load_current(OPERATION_ID)
    assert selected.revision.field("journal_revision") == 2
    assert selected.revision.field("state") == "committed"


def test_committed_revision_recovery_exact_replay_does_not_add_revision(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)

    first = recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:03-04:00",
        committed_at="2026-08-05T20:00:04-04:00",
    )
    second = recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:09-04:00",
        committed_at="2026-08-05T20:00:10-04:00",
    )

    assert first.action == "created_missing_committed_revision"
    assert second.action == "exact_replay"
    assert (
        OperationJournalStore(tmp_path).inspect_recovery(OPERATION_ID).valid_revisions
        == (1, 2)
    )


def test_committed_revision_recovery_selects_exact_orphan_successor(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, store, current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)

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
    exclusive_create(
        operation_revision_path(tmp_path, OPERATION_ID, 2),
        canonical_json_bytes(committed.to_dict()),
    )

    observation = store.inspect_recovery(OPERATION_ID)
    assert observation.disposition == "orphan_linear_successor"
    assert (
        store.load_current(OPERATION_ID).pointer_fingerprint
        == current.pointer_fingerprint
    )

    result = recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:03-04:00",
        committed_at="2026-08-05T20:00:04-04:00",
    )

    assert result.action == "selected_existing_committed_revision"
    assert result.assessment.disposition == "committed"
    assert (
        OperationJournalStore(tmp_path)
        .load_current(OPERATION_ID)
        .pointer.field("journal_revision")
        == 2
    )


def test_committed_revision_recovery_refuses_artifact_mismatch(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\\n1,2\\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    exclusive_create(tmp_path / ARTIFACT_PATH, b"different\\n")
    exclusive_create(
        tmp_path / PROVENANCE_PATH,
        canonical_json_bytes(export.to_dict()),
    )

    with pytest.raises(PortiaRecoveryRequiredError):
        recover_deliberate_export_committed_revision(
            tmp_path,
            OPERATION_ID,
            export=export,
            observed_at="2026-08-05T20:00:03-04:00",
            committed_at="2026-08-05T20:00:04-04:00",
        )

    assert not operation_revision_path(tmp_path, OPERATION_ID, 2).exists()



def _recover_to_committed(
    tmp_path: Path,
    artifact: bytes,
):
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)
    recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:03-04:00",
        committed_at="2026-08-05T20:00:04-04:00",
    )
    return export


def test_export_finalization_appends_completed_revision_without_rewriting_export(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    before_provenance = (tmp_path / PROVENANCE_PATH).read_bytes()

    result = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert result.action == "completed_export_operation"
    assert result.assessment.disposition == "completed"
    assert result.assessment.selected_revision == 3
    assert result.assessment.planned_committed_revision == 2
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == before_provenance
    operation_ref = export.field("operation_journal_ref")
    assert isinstance(operation_ref, Mapping)
    assert operation_ref["journal_revision"] == 2


def test_export_finalization_releases_exact_preserved_v3_lock(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    lock = parse_portia_record("operation_lock", "3", _lock())
    held = LockStore(tmp_path).acquire(lock)
    assert held.path.exists()

    result = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
        lock=lock,
    )

    assert result.assessment.disposition == "completed"
    assert not held.path.exists()


def test_export_finalization_exact_replay_adds_no_revision(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)

    first = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )
    second = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert first.action == "completed_export_operation"
    assert second.action == "exact_replay"
    assert (
        OperationJournalStore(tmp_path).inspect_recovery(OPERATION_ID).valid_revisions
        == (1, 2, 3)
    )


def test_export_finalization_selects_exact_completed_orphan(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    store = OperationJournalStore(tmp_path)
    committed_state = store.load_current(OPERATION_ID)
    committed = committed_state.revision

    completed_data = committed.to_dict()
    completed_data["journal_revision"] = 3
    completed_data["previous_journal_revision"] = 2
    completed_data["state"] = "completed"
    completed = parse_portia_record("operation_journal", "4", completed_data)
    exclusive_create(
        operation_revision_path(tmp_path, OPERATION_ID, 3),
        canonical_json_bytes(completed.to_dict()),
    )

    observation = store.inspect_recovery(OPERATION_ID)
    assert observation.disposition == "orphan_linear_successor"

    result = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert result.action == "selected_existing_completed_revision"
    assert result.assessment.disposition == "completed"
    assert store.load_current(OPERATION_ID).pointer.field("journal_revision") == 3


def test_export_finalization_refuses_mismatched_durable_lock(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    lock = parse_portia_record("operation_lock", "3", _lock())
    lock_id = lock.field("lock_id")
    assert isinstance(lock_id, str)
    path = lock_path(tmp_path, lock_id)
    exclusive_create(path, b"{}\n")

    with pytest.raises(
        PortiaRecoveryRequiredError,
        match="lock differs",
    ):
        finalize_deliberate_export(
            tmp_path,
            OPERATION_ID,
            export=export,
            lock=lock,
        )

    assert path.exists()
    assert (
        OperationJournalStore(tmp_path)
        .load_current(OPERATION_ID)
        .revision.field("state")
        == "committed"
    )


def test_export_finalization_requires_lock_evidence_when_lock_is_present(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    lock = parse_portia_record("operation_lock", "3", _lock())
    held = LockStore(tmp_path).acquire(lock)

    with pytest.raises(
        PortiaRecoveryRequiredError,
        match="no lock record was supplied",
    ):
        finalize_deliberate_export(
            tmp_path,
            OPERATION_ID,
            export=export,
        )

    assert held.path.exists()



def test_contradictory_export_candidate_reuse_fails_without_mutation(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    exclusive_create(tmp_path / ARTIFACT_PATH, artifact)
    conflicting = parse_portia_record(
        "deliberate_export",
        "1",
        _export(b"different-output\n"),
    )

    with pytest.raises(PortiaConflictError):
        recover_deliberate_export_provenance(
            tmp_path,
            OPERATION_ID,
            export=conflicting,
        )

    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact
    assert not (tmp_path / PROVENANCE_PATH).exists()
    assert export.field("export_id") == conflicting.field("export_id")


def test_competing_operation_ids_cannot_hold_same_export_lock(
    tmp_path: Path,
) -> None:
    first = parse_portia_record("operation_lock", "3", _lock())
    second_data = copy.deepcopy(_lock())
    owning_operation = second_data["owning_operation"]
    assert isinstance(owning_operation, dict)
    owning_operation["operation_id"] = "op_issue88_competing_export"
    second = parse_portia_record("operation_lock", "3", second_data)

    store = LockStore(tmp_path)
    held = store.acquire(first)
    try:
        with pytest.raises(PortiaLockError, match="already held"):
            store.acquire(second)
        assert held.path.exists()
    finally:
        store.release(held)


def test_wrong_preexisting_artifact_is_never_overwritten_by_recovery(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    wrong = b"preexisting-wrong-artifact\n"
    exclusive_create(tmp_path / ARTIFACT_PATH, wrong)

    with pytest.raises(PortiaRecoveryRequiredError):
        recover_deliberate_export_provenance(
            tmp_path,
            OPERATION_ID,
            export=export,
        )

    assert (tmp_path / ARTIFACT_PATH).read_bytes() == wrong
    assert not (tmp_path / PROVENANCE_PATH).exists()


def test_wrong_preexisting_provenance_is_never_overwritten_by_recovery(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export, _store, _current = _persist_staged_export_series(tmp_path, artifact)
    exclusive_create(tmp_path / ARTIFACT_PATH, artifact)
    wrong = b"{}\n"
    exclusive_create(tmp_path / PROVENANCE_PATH, wrong)

    with pytest.raises(PortiaRecoveryRequiredError):
        recover_deliberate_export_provenance(
            tmp_path,
            OPERATION_ID,
            export=export,
        )

    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == wrong


def test_contradictory_replay_after_commit_does_not_add_revision(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    conflicting = parse_portia_record(
        "deliberate_export",
        "1",
        _export(b"contradictory-output\n"),
    )
    before_provenance = (tmp_path / PROVENANCE_PATH).read_bytes()

    with pytest.raises(PortiaConflictError):
        recover_deliberate_export_committed_revision(
            tmp_path,
            OPERATION_ID,
            export=conflicting,
            observed_at="2026-08-05T20:00:11-04:00",
            committed_at="2026-08-05T20:00:12-04:00",
        )

    assert (
        OperationJournalStore(tmp_path).inspect_recovery(OPERATION_ID).valid_revisions
        == (1, 2)
    )
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == before_provenance
    assert export.field("export_id") == conflicting.field("export_id")


def test_unexpected_committed_orphan_cannot_be_selected(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export, store, current = _persist_staged_export_series(tmp_path, artifact)
    _persist_exact_export_outputs(tmp_path, artifact, export)

    orphan_data = _journal(
        artifact,
        export.to_dict(),
        revision=2,
        previous=1,
        state="committed",
    )
    preflight = orphan_data["preflight_snapshot"]
    assert isinstance(preflight, list)
    assert isinstance(preflight[0], dict)
    preflight[0]["observed_at"] = "2026-08-05T20:00:59-04:00"
    orphan = parse_portia_record("operation_journal", "4", orphan_data)
    exclusive_create(
        operation_revision_path(tmp_path, OPERATION_ID, 2),
        canonical_json_bytes(orphan.to_dict()),
    )

    observation = store.inspect_recovery(OPERATION_ID)
    assert observation.disposition == "orphan_linear_successor"

    with pytest.raises(
        PortiaRecoveryRequiredError,
        match="immutable intent",
    ):
        recover_deliberate_export_committed_revision(
            tmp_path,
            OPERATION_ID,
            export=export,
            observed_at="2026-08-05T20:00:03-04:00",
            committed_at="2026-08-05T20:00:04-04:00",
        )

    selected = store.load_current(OPERATION_ID)
    assert selected.pointer_fingerprint == current.pointer_fingerprint
    assert selected.pointer.field("journal_revision") == 1


def test_exact_replay_across_recovery_apis_creates_no_duplicates(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )
    artifact_before = (tmp_path / ARTIFACT_PATH).read_bytes()
    provenance_before = (tmp_path / PROVENANCE_PATH).read_bytes()
    revisions_before = OperationJournalStore(tmp_path).inspect_recovery(
        OPERATION_ID
    ).valid_revisions

    provenance_replay = recover_deliberate_export_provenance(
        tmp_path,
        OPERATION_ID,
        export=export,
    )
    commit_replay = recover_deliberate_export_committed_revision(
        tmp_path,
        OPERATION_ID,
        export=export,
        observed_at="2026-08-05T20:00:21-04:00",
        committed_at="2026-08-05T20:00:22-04:00",
    )
    final_replay = finalize_deliberate_export(
        tmp_path,
        OPERATION_ID,
        export=export,
    )

    assert provenance_replay.action == "exact_replay"
    assert commit_replay.action == "exact_replay"
    assert final_replay.action == "exact_replay"
    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact_before
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == provenance_before
    assert (
        OperationJournalStore(tmp_path).inspect_recovery(OPERATION_ID).valid_revisions
        == revisions_before
        == (1, 2, 3)
    )


def test_export_workspace_path_traversal_is_rejected() -> None:
    with pytest.raises(PortiaPathError, match="unsafe components"):
        validate_workspace_relative_path(
            "../portia/exports/pexp_escape/artifact.csv"
        )


def test_export_symlink_escape_is_rejected_when_platform_supports_symlinks(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-issue88-outside"
    outside.mkdir(exist_ok=True)
    export_link = tmp_path / "portia" / "exports" / "pexp_escape"
    export_link.parent.mkdir(parents=True, exist_ok=True)
    try:
        export_link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are not available in this environment")

    with pytest.raises(PortiaPathError, match="outside the selected workspace"):
        workspace_relative(tmp_path, export_link / "artifact.csv")



def test_contradictory_completed_replay_is_conflict_without_mutation(
    tmp_path: Path,
) -> None:
    artifact = b"a,b\n1,2\n"
    export = _recover_to_committed(tmp_path, artifact)
    finalize_deliberate_export(tmp_path, OPERATION_ID, export=export)
    conflicting = parse_portia_record(
        "deliberate_export",
        "1",
        _export(b"contradictory-completed-output\n"),
    )
    artifact_before = (tmp_path / ARTIFACT_PATH).read_bytes()
    provenance_before = (tmp_path / PROVENANCE_PATH).read_bytes()
    revisions_before = OperationJournalStore(tmp_path).inspect_recovery(
        OPERATION_ID
    ).valid_revisions

    with pytest.raises(
        PortiaConflictError,
        match="contradicts journaled intent",
    ):
        finalize_deliberate_export(
            tmp_path,
            OPERATION_ID,
            export=conflicting,
        )

    assert (tmp_path / ARTIFACT_PATH).read_bytes() == artifact_before
    assert (tmp_path / PROVENANCE_PATH).read_bytes() == provenance_before
    assert (
        OperationJournalStore(tmp_path).inspect_recovery(OPERATION_ID).valid_revisions
        == revisions_before
        == (1, 2, 3)
    )
