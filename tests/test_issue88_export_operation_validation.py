from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from portia.models import parse_portia_record
from portia.storage.deliberate_export_operations import (
    DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_committed_reference,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaLockError,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.locks import (
    LockStore,
    derive_lock_id,
    validate_operation_lock_application,
)
from portia.storage.operation_journal import validate_operation_journal_application
from portia.storage.orchestration import acquire_journaled_locks

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

EXPORT_REF = {
    "export_id": "pexp_issue88_validation_01",
    "contract_version": "1",
}
EXPORT_TARGET = {
    "kind": "deliberate_export",
    "export_ref": EXPORT_REF,
}
ARTIFACT_PATH = "portia/exports/pexp_issue88_validation_01/artifact.csv"
PROVENANCE_PATH = "portia/exports/pexp_issue88_validation_01/export.json"
ARTIFACT_FP = {
    "algorithm": "sha256",
    "digest": "c" * 64,
    "byte_length": 1200,
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _preflight(
    *,
    role: str,
    path: str,
    contract_version: str,
) -> dict[str, Any]:
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
        "disposition": "pending",
        "observed_result": None,
        "compensation_step_id": None,
        "reason_code": None,
    }


def _journal() -> dict[str, Any]:
    value = _load(V3_FIXTURE)
    value["schema_version"] = "4"
    value["operation_id"] = "op_issue88_export_validation"
    value["operation_kind"] = "generate_deliberate_export"
    value["scope"] = "workspace"
    value["primary_target"] = copy.deepcopy(EXPORT_TARGET)
    value["affected_targets"] = []
    value["intent_facts"] = []
    value["preflight_snapshot"] = [
        _preflight(
            role="deliberate_export_artifact",
            path=ARTIFACT_PATH,
            contract_version=DELIBERATE_EXPORT_ARTIFACT_REPRESENTATION_VERSION,
        ),
        _preflight(
            role="deliberate_export_provenance",
            path=PROVENANCE_PATH,
            contract_version="1",
        ),
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
            fingerprint=ARTIFACT_FP,
            selected_state=[],
        ),
        _write(
            step_id="step_export_provenance",
            sequence=2,
            role="deliberate_export_provenance",
            path=PROVENANCE_PATH,
            contract_version="1",
            fingerprint={
                "algorithm": "sha256",
                "digest": "d" * 64,
                "byte_length": 1,
            },
            selected_state=[
                {
                    "name": "committed_journal_revision",
                    "kind": "integer",
                    "value": 2,
                }
            ],
        ),
    ]
    value["compensation_plan"] = []
    value["recovery_plan"] = [
        "resume",
        "complete_remaining_steps",
        "abandon_preacceptance_artifacts",
        "require_manual_review",
    ]
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
    partial["recommended_disposition"] = "resume"
    return value


def _export() -> dict[str, Any]:
    value = _load(EXPORT_FIXTURE)
    value["export_id"] = EXPORT_REF["export_id"]
    output = value["output"]
    assert isinstance(output, dict)
    output["workspace_relative_path"] = ARTIFACT_PATH
    output["byte_length"] = ARTIFACT_FP["byte_length"]
    output["sha256_digest"] = ARTIFACT_FP["digest"]
    value["operation_journal_ref"] = {
        "operation_id": "op_issue88_export_validation",
        "journal_revision": 2,
        "contract_version": "4",
    }
    return value


def _bind_provenance_fingerprint(
    journal: dict[str, Any],
    export: dict[str, Any],
) -> None:
    export_record = parse_portia_record("deliberate_export", "1", export)
    fingerprint = fingerprint_bytes(
        canonical_json_bytes(export_record.to_dict())
    ).to_dict()
    write_set = journal["write_set"]
    assert isinstance(write_set, list)
    provenance = write_set[1]
    assert isinstance(provenance, dict)
    intended = provenance["intended_result"]
    assert isinstance(intended, dict)
    intended["fingerprint"] = fingerprint


def _committed(journal: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(journal)
    value["journal_revision"] = 2
    value["previous_journal_revision"] = 1
    value["state"] = "committed"
    value["commit_point"] = {
        "reached": True,
        "reached_at": "2026-08-05T20:00:04-04:00",
    }
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
    partial = value["partial_state"]
    assert isinstance(partial, dict)
    partial["durability_assessment"] = "confirmed"
    partial["accepted_steps"] = [
        "step_export_artifact",
        "step_export_provenance",
    ]
    partial["verified_steps"] = [
        "step_export_artifact",
        "step_export_provenance",
    ]
    partial["remaining_canonical_steps"] = []
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
        "owning_operation": {
            "operation_id": "op_issue88_export_validation",
        },
        "acquired_at": "2026-08-05T20:00:02-04:00",
        "deployment_instance_id": "test_deployment",
        "process_instance_id": "test_process",
    }


def test_valid_prepared_export_journal_has_exact_two_representation_plan() -> None:
    record = parse_portia_record("operation_journal", "4", _journal())
    validate_operation_journal_application(record)
    assert planned_deliberate_export_commit_revision(record) == 2


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda value: value.update(operation_kind="create_record"),
            "reserved",
        ),
        (
            lambda value: value.update(scope="class"),
            "scope",
        ),
        (
            lambda value: value["affected_targets"].append({"kind": "workspace"}),
            "primary identity",
        ),
        (
            lambda value: value["intent_facts"].append(
                {"name": "student_name", "kind": "token", "value": "alice"}
            ),
            "privacy-minimized",
        ),
        (
            lambda value: value["write_set"][0].update(
                action="revision_aware_replace"
            ),
            "exclusive_create",
        ),
        (
            lambda value: value["write_set"][0].update(
                representation_role="deliberate_export_provenance"
            ),
            "artifact then provenance",
        ),
        (
            lambda value: value["write_set"][0].update(
                destination_path=(
                    "portia/exports/pexp_issue88_validation_01/"
                    "student-alice.csv"
                )
            ),
            "artifact.<format>",
        ),
        (
            lambda value: value["write_set"].append(
                copy.deepcopy(value["write_set"][0])
            ),
            "exactly artifact and provenance",
        ),
    ],
)
def test_export_journal_application_rules_fail_closed(
    mutation,
    message: str,
) -> None:
    value = _journal()
    mutation(value)
    with pytest.raises(PortiaCorruptionError, match=message):
        validate_operation_journal_application(value)


def test_export_preflight_must_reconcile_both_final_absence_checks() -> None:
    value = _journal()
    value["preflight_snapshot"] = value["preflight_snapshot"][:1]
    with pytest.raises(PortiaCorruptionError, match="exactly artifact and provenance"):
        validate_operation_journal_application(value)


def test_export_lock_plan_must_equal_exact_primary_export() -> None:
    value = _journal()
    entry = value["lock_set"][0]
    assert isinstance(entry, dict)
    entry["lock_scope"] = "workspace"
    entry["protected_target"] = {"kind": "workspace"}
    with pytest.raises(PortiaCorruptionError, match="exact export target"):
        validate_operation_journal_application(value)


def test_provenance_cannot_outrun_artifact_acceptance() -> None:
    value = _journal()
    artifact = value["write_set"][0]
    provenance = value["write_set"][1]
    assert isinstance(artifact, dict) and isinstance(provenance, dict)
    artifact["disposition"] = "durable"
    artifact["observed_result"] = {
        "kind": "present",
        "workspace_relative_path": artifact["destination_path"],
        "fingerprint": copy.deepcopy(artifact["intended_result"]["fingerprint"]),
        "observed_at": "2026-08-05T20:00:03-04:00",
    }
    provenance["disposition"] = "verified"
    provenance["observed_result"] = {
        "kind": "present",
        "workspace_relative_path": provenance["destination_path"],
        "fingerprint": copy.deepcopy(provenance["intended_result"]["fingerprint"]),
        "observed_at": "2026-08-05T20:00:03-04:00",
    }
    with pytest.raises(PortiaCorruptionError, match="cannot outrun"):
        validate_operation_journal_application(value)


def test_candidate_binds_output_bytes_and_exact_reserved_v4_revision() -> None:
    journal = _journal()
    export = _export()
    _bind_provenance_fingerprint(journal, export)
    journal_record = parse_portia_record("operation_journal", "4", journal)
    export_record = parse_portia_record("deliberate_export", "1", export)
    validate_deliberate_export_candidate_reconciliation(
        journal_record,
        export_record,
    )

    wrong_ref = copy.deepcopy(export)
    journal_ref = wrong_ref["operation_journal_ref"]
    assert isinstance(journal_ref, dict)
    journal_ref["contract_version"] = "1"
    with pytest.raises(PortiaCorruptionError, match="reserved committed v4"):
        validate_deliberate_export_candidate_reconciliation(
            journal_record,
            wrong_ref,
        )


def test_exact_committed_reference_does_not_accept_completed_as_substitute() -> None:
    prepared = _journal()
    export = _export()
    _bind_provenance_fingerprint(prepared, export)
    committed = _committed(prepared)
    committed_record = parse_portia_record("operation_journal", "4", committed)
    export_record = parse_portia_record("deliberate_export", "1", export)
    validate_deliberate_export_committed_reference(
        committed_record,
        export_record,
    )

    completed = copy.deepcopy(committed)
    completed["journal_revision"] = 3
    completed["previous_journal_revision"] = 2
    completed["state"] = "completed"
    completed_record = parse_portia_record(
        "operation_journal",
        "4",
        completed,
    )
    validate_deliberate_export_candidate_reconciliation(
        completed_record,
        export_record,
    )
    with pytest.raises(PortiaCorruptionError, match="committed, not current/latest"):
        validate_deliberate_export_committed_reference(
            completed_record,
            export_record,
        )


def test_operation_lock_v3_is_exact_and_agrees_with_export_journal() -> None:
    journal_record = parse_portia_record("operation_journal", "4", _journal())
    lock = _lock()
    lock_record = parse_portia_record("operation_lock", "3", lock)
    validate_operation_lock_application(lock_record)
    validate_deliberate_export_lock_agreement(journal_record, lock_record)

    wrong = copy.deepcopy(lock)
    owner = wrong["owning_operation"]
    assert isinstance(owner, dict)
    owner["operation_id"] = "op_other"
    wrong_record = parse_portia_record("operation_lock", "3", wrong)
    with pytest.raises(PortiaCorruptionError, match="another operation"):
        validate_deliberate_export_lock_agreement(
            journal_record,
            wrong_record,
        )


def test_v3_export_lock_and_v4_export_journal_are_not_executable_yet(
    tmp_path: Path,
) -> None:
    journal_record = parse_portia_record("operation_journal", "4", _journal())
    lock_record = parse_portia_record("operation_lock", "3", _lock())

    with pytest.raises(PortiaLockError, match="operation_lock@2"):
        LockStore(tmp_path).acquire(lock_record)

    lock_id = lock_record.field("lock_id")
    assert isinstance(lock_id, str)
    with pytest.raises(PortiaConflictError, match="validation-only"):
        acquire_journaled_locks(
            tmp_path,
            journal_record,
            {lock_id: lock_record},
        )


def test_existing_v3_application_validation_remains_supported() -> None:
    old = parse_portia_record(
        "operation_journal",
        "3",
        _load(V3_FIXTURE),
    )
    validate_operation_journal_application(old)
