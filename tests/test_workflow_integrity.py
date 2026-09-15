from __future__ import annotations

import json
from pathlib import Path

import pytest

import portia.workflows.integrity as integrity_module
from portia.models import parse_portia_record
from portia.storage.derived import DerivedCurrentState, DerivedStore
from portia.storage.errors import PortiaAmbiguousRecoveryError, PortiaConflictError
from portia.storage.fingerprint import (
    canonical_json_bytes,
    fingerprint_bytes,
)
from portia.storage.integrity import PersistenceFinding
from portia.storage.io import exclusive_create, guarded_replace, read_bytes
from portia.storage.paths import (
    derived_data_path,
    operation_current_path,
    operation_revision_path,
)
from portia.storage.series import OperationJournalStore
from portia.workflows import (
    IntegrityWorkflowService,
    OperationIntegrityEvaluation,
    OperationIntegrityProjection,
)
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


def _append_operation(tmp_path: Path, data: dict[str, object]) -> None:
    journal = parse_portia_record("operation_journal", "2", data)
    revision = data["journal_revision"]
    assert isinstance(revision, int)
    pointer = parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": "op_create_actor",
            "journal_revision": revision,
        },
    )
    store = OperationJournalStore(tmp_path)
    current = store.load_current("op_create_actor")
    store.append(journal, pointer, expected_pointer=current.pointer_fingerprint)


def _projection_scope() -> dict[str, object]:
    return {
        "scope": "operation",
        "operation_ref": {"operation_id": "op_create_actor"},
    }


def _current_projection(tmp_path: Path) -> DerivedCurrentState:
    return DerivedStore(tmp_path).load_current(
        "active_integrity_finding_index", _projection_scope()
    )


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
    assert evaluation.pointer_fingerprint == before.pointer_fingerprint
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


def test_operation_persistence_projection_installs_schema_valid_public_finding(
    tmp_path: Path,
) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)

    projected = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")

    assert isinstance(projected, OperationIntegrityProjection)
    assert len(projected.findings) == 1
    finding = projected.findings[0]
    assert finding.contract == "integrity_finding"
    assert finding.contract_version == "2"
    value = finding.to_dict()
    assert parse_portia_record("integrity_finding", "2", value) == finding
    assert value["code"] == "canonical_path_mismatch"
    assert value["category"] == "structure"
    assert value["assessment"] == {"result": "confirmed"}
    assert value["primary_target"] == {
        "kind": "operation",
        "operation_id": "op_create_actor",
    }
    assert {
        "name": "destination_path",
        "kind": "path",
        "value": "portia/actors/actr_other/actor.json",
    } in value["evidence"]
    current = _current_projection(tmp_path)
    assert current.data == {"findings": [value]}
    metadata = current.metadata.to_dict()
    snapshot = metadata["source_snapshot"]
    assert isinstance(snapshot, dict)
    assert snapshot["entries"] == [
        {
            "workspace_relative_path": "portia/operations/op_create_actor/current.json",
            "byte_length": projected.evaluation.pointer_fingerprint.byte_length,
            "sha256_digest": projected.evaluation.pointer_fingerprint.digest,
            "source_role": "operational_pointer",
            "contract_or_artifact_kind": "operation_current_pointer",
        },
        {
            "workspace_relative_path": (
                "portia/operations/op_create_actor/revisions/1.json"
            ),
            "byte_length": projected.evaluation.journal_fingerprint.byte_length,
            "sha256_digest": projected.evaluation.journal_fingerprint.digest,
            "source_role": "operational_revision",
            "contract_or_artifact_kind": "operation_journal",
        },
    ]
    assert metadata["generating_operation"] == {
        "operation_id": "op_create_actor",
        "journal_revision": 1,
        "contract_version": "2",
    }


@pytest.mark.parametrize(
    ("internal_code", "public_category", "public_code", "public_check"),
    [
        (
            "PORTIA.STORAGE.OPERATION_WRITE_SET_INVALID",
            "persistence_recovery",
            "recovery_required",
            "journal_write_set",
        ),
        (
            "PORTIA.STORAGE.UNSAFE_OPERATION_PATH",
            "structure",
            "canonical_path_mismatch",
            "workspace_containment",
        ),
        (
            "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH",
            "structure",
            "canonical_path_mismatch",
            "target_path_ownership",
        ),
        (
            "PORTIA.STORAGE.DURABLE_RESULT_MISSING",
            "persistence_recovery",
            "recovery_required",
            "durable_destination",
        ),
        (
            "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH",
            "persistence_recovery",
            "content_digest_mismatch",
            "intended_fingerprint",
        ),
        (
            "PORTIA.STORAGE.READBACK_RESULT_MISMATCH",
            "persistence_recovery",
            "content_digest_mismatch",
            "observed_fingerprint",
        ),
    ],
)
def test_operation_persistence_projection_maps_closed_diagnostics_without_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    internal_code: str,
    public_category: str,
    public_code: str,
    public_check: str,
) -> None:
    _create_operation(tmp_path)
    monkeypatch.setattr(
        integrity_module,
        "validate_operation_durable_state",
        lambda _root, _journal: (
            PersistenceFinding(
                internal_code,
                "portia/actors/actr_synthetic/actor.json",
                "PRIVATE-DIAGNOSTIC-SENTINEL",
            ),
        ),
    )

    projected = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")
    serialized = json.dumps(
        {"findings": [finding.to_dict() for finding in projected.findings]},
        sort_keys=True,
    )
    value = projected.findings[0].to_dict()

    assert value["category"] == public_category
    assert value["code"] == public_code
    assert value["code"] != internal_code
    assert {
        "name": "persistence_check",
        "kind": "token",
        "value": public_check,
    } in value["evidence"]
    assert internal_code not in serialized
    assert "PRIVATE-DIAGNOSTIC-SENTINEL" not in serialized


def test_operation_persistence_projection_rejects_unknown_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_operation(tmp_path)
    monkeypatch.setattr(
        integrity_module,
        "validate_operation_durable_state",
        lambda _root, _journal: (
            PersistenceFinding(
                "PORTIA.STORAGE.FUTURE_UNKNOWN",
                "portia/synthetic.json",
                "PRIVATE-DIAGNOSTIC-SENTINEL",
            ),
        ),
    )

    with pytest.raises(WorkflowPrerequisiteError, match="no public.*mapping"):
        IntegrityWorkflowService(tmp_path).project_operation_persistence_findings(
            "op_create_actor"
        )

    assert DerivedStore(tmp_path).load_current_or_none(
        "active_integrity_finding_index", _projection_scope()
    ) is None


def test_operation_persistence_projection_identity_and_order_are_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _create_operation(tmp_path)
    diagnostics = (
        PersistenceFinding(
            "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH",
            "portia/actors/actr_second/actor.json",
            "second detail",
        ),
        PersistenceFinding(
            "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH",
            "portia/actors/actr_first/actor.json",
            "first detail",
        ),
    )
    changed_details = tuple(
        PersistenceFinding(
            finding.code,
            finding.relative_path,
            f"changed PRIVATE detail {index}",
        )
        for index, finding in enumerate(reversed(diagnostics))
    )
    calls = 0

    def evaluate(_root: object, _journal: object) -> tuple[PersistenceFinding, ...]:
        nonlocal calls
        calls += 1
        return diagnostics if calls == 1 else changed_details

    monkeypatch.setattr(
        integrity_module,
        "validate_operation_durable_state",
        evaluate,
    )
    service = IntegrityWorkflowService(tmp_path)

    first = service.project_operation_persistence_findings("op_create_actor")
    second = service.project_operation_persistence_findings("op_create_actor")
    first_values = [finding.to_dict() for finding in first.findings]
    second_values = [finding.to_dict() for finding in second.findings]

    assert first_values == second_values
    assert [value["code"] for value in first_values] == [
        "content_digest_mismatch",
        "canonical_path_mismatch",
    ]
    assert first.generation.metadata.to_dict()["generation_id"] == (
        second.generation.metadata.to_dict()["generation_id"]
    )
    assert [value["finding_key"] for value in first_values] == [
        value["finding_key"] for value in second_values
    ]
    assert [value["evaluation_key"] for value in first_values] == [
        value["evaluation_key"] for value in second_values
    ]


def test_finding_identity_survives_distinct_exact_evaluations(tmp_path: Path) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)

    first = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")
    successor_data = _journal_data()
    successor_write_set = successor_data["write_set"]
    assert isinstance(successor_write_set, list)
    successor_step = successor_write_set[0]
    assert isinstance(successor_step, dict)
    successor_step["destination_path"] = "portia/actors/actr_other/actor.json"
    successor_data["journal_revision"] = 2
    successor_data["previous_journal_revision"] = 1
    successor_data["state"] = "staged"
    successor_data["updated_at"] = "2026-08-05T20:00:03-04:00"
    _append_operation(tmp_path, successor_data)

    second = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")
    first_value = first.findings[0].to_dict()
    second_value = second.findings[0].to_dict()

    assert first_value["finding_key"] == second_value["finding_key"]
    assert first_value["evaluation_key"] != second_value["evaluation_key"]


def test_finding_identity_is_independent_of_sibling_diagnostics(tmp_path: Path) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)
    first = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")

    successor_data = _journal_data()
    successor_write_set = successor_data["write_set"]
    assert isinstance(successor_write_set, list)
    successor_step = successor_write_set[0]
    assert isinstance(successor_step, dict)
    successor_step["destination_path"] = "portia/actors/actr_other/actor.json"
    successor_step["disposition"] = "durable"
    intended_result = successor_step["intended_result"]
    assert isinstance(intended_result, dict)
    intended_fingerprint = intended_result["fingerprint"]
    successor_step["observed_result"] = {
        "workspace_relative_path": "portia/actors/actr_other/actor.json",
        "fingerprint": intended_fingerprint,
        "observed_at": "2026-08-05T20:00:02-04:00",
    }
    successor_data["journal_revision"] = 2
    successor_data["previous_journal_revision"] = 1
    successor_data["state"] = "committing"
    successor_data["updated_at"] = "2026-08-05T20:00:03-04:00"
    exclusive_create(
        tmp_path / "portia" / "actors" / "actr_other" / "actor.json",
        b'{"synthetic":"different"}\n',
    )
    _append_operation(tmp_path, successor_data)

    second = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")
    first_path = next(
        finding.to_dict()
        for finding in first.findings
        if finding.to_dict()["code"] == "canonical_path_mismatch"
    )
    second_path = next(
        finding.to_dict()
        for finding in second.findings
        if finding.to_dict()["code"] == "canonical_path_mismatch"
    )

    assert len(second.findings) == 3
    assert first_path["finding_key"] == second_path["finding_key"]
    assert first_path["evaluation_key"] != second_path["evaluation_key"]


def test_material_path_change_changes_finding_identity(tmp_path: Path) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)
    first = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")

    successor_data = _journal_data()
    successor_write_set = successor_data["write_set"]
    assert isinstance(successor_write_set, list)
    successor_step = successor_write_set[0]
    assert isinstance(successor_step, dict)
    successor_step["destination_path"] = "portia/actors/actr_changed/actor.json"
    successor_data["journal_revision"] = 2
    successor_data["previous_journal_revision"] = 1
    successor_data["state"] = "staged"
    successor_data["updated_at"] = "2026-08-05T20:00:03-04:00"
    _append_operation(tmp_path, successor_data)

    second = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")

    assert first.findings[0].to_dict()["finding_key"] != (
        second.findings[0].to_dict()["finding_key"]
    )


def test_clean_projection_supersedes_finding_without_canonical_mutation(
    tmp_path: Path,
) -> None:
    good_bytes = b'{"synthetic":"accepted"}\n'
    bad_bytes = b'{"synthetic":"changed"}\n'
    intended = fingerprint_bytes(good_bytes)
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    data["state"] = "committing"
    step["disposition"] = "durable"
    intended_result = step["intended_result"]
    assert isinstance(intended_result, dict)
    intended_result["fingerprint"] = intended.to_dict()
    step["observed_result"] = {
        "workspace_relative_path": "portia/actors/actr_new/actor.json",
        "fingerprint": intended.to_dict(),
        "observed_at": "2026-08-05T20:00:02-04:00",
    }
    _create_operation(tmp_path, data)
    target = tmp_path / "portia" / "actors" / "actr_new" / "actor.json"
    bad_fingerprint = exclusive_create(target, bad_bytes)
    revision_path = operation_revision_path(tmp_path, "op_create_actor", 1)
    pointer_path = operation_current_path(tmp_path, "op_create_actor")
    operation_before = (read_bytes(revision_path), read_bytes(pointer_path))

    first = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")

    assert [finding.to_dict()["code"] for finding in first.findings] == [
        "content_digest_mismatch",
        "content_digest_mismatch",
    ]
    assert (read_bytes(revision_path), read_bytes(pointer_path)) == operation_before
    assert read_bytes(target) == bad_bytes
    first_generation_id = first.generation.metadata.to_dict()["generation_id"]
    guarded_replace(target, good_bytes, expected=bad_fingerprint)
    canonical_before_clean = (
        read_bytes(revision_path),
        read_bytes(pointer_path),
        read_bytes(target),
    )

    clean = IntegrityWorkflowService(
        tmp_path
    ).project_operation_persistence_findings("op_create_actor")
    current = _current_projection(tmp_path)
    clean_generation_id = clean.generation.metadata.to_dict()["generation_id"]

    assert clean.findings == ()
    assert current.data == {"findings": []}
    assert clean_generation_id != first_generation_id
    assert current.metadata.to_dict()["generation_id"] == clean_generation_id
    assert derived_data_path(
        tmp_path,
        "active_integrity_finding_index",
        _projection_scope(),
        str(first_generation_id),
    ).exists()
    assert (
        read_bytes(revision_path),
        read_bytes(pointer_path),
        read_bytes(target),
    ) == canonical_before_clean


def test_operation_persistence_projection_fails_closed_when_source_turns_stale(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = _journal_data()
    write_set = data["write_set"]
    assert isinstance(write_set, list)
    step = write_set[0]
    assert isinstance(step, dict)
    step["destination_path"] = "portia/actors/actr_other/actor.json"
    _create_operation(tmp_path, data)
    service = IntegrityWorkflowService(tmp_path)
    original_validate = service._derived._validate_metadata
    validations = 0

    def validate_after_advancing_source(
        metadata: object, data_bytes: bytes
    ) -> object:
        nonlocal validations
        validations += 1
        if validations == 2:
            store = OperationJournalStore(tmp_path)
            selected = store.load_current("op_create_actor")
            successor_data = _journal_data()
            successor_data["journal_revision"] = 2
            successor_data["previous_journal_revision"] = 1
            successor_data["state"] = "staged"
            successor_data["updated_at"] = "2026-08-05T20:00:03-04:00"
            successor = parse_portia_record("operation_journal", "2", successor_data)
            pointer = parse_portia_record(
                "operation_current_pointer",
                "1",
                {
                    "schema_version": "1",
                    "record_type": "operation_current_pointer",
                    "module_id": "portia",
                    "operation_id": "op_create_actor",
                    "journal_revision": 2,
                },
            )
            store.append(
                successor,
                pointer,
                expected_pointer=selected.pointer_fingerprint,
            )
        return original_validate(metadata, data_bytes)

    monkeypatch.setattr(
        service._derived,
        "_validate_metadata",
        validate_after_advancing_source,
    )

    with pytest.raises(PortiaConflictError, match="Source Snapshot is stale"):
        service.project_operation_persistence_findings("op_create_actor")

    assert DerivedStore(tmp_path).load_current_or_none(
        "active_integrity_finding_index", _projection_scope()
    ) is None
