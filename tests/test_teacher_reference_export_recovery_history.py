from __future__ import annotations

from pathlib import Path

import pytest

from portia.exports import (
    TeacherReferenceExportHistoryService,
    TeacherReferenceExportRecoveryService,
)
from portia.exports.execution import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionSuccess,
)
from portia.exports.preparation import TeacherReferenceExportPreparationService
from portia.storage import (
    OperationJournalStore,
    PortiaOperationPartialCommitError,
)
from portia.storage.deliberate_export_persistence import (
    commit_deliberate_export_candidates,
    stage_deliberate_export_candidates,
)
from portia.storage.deliberate_export_recovery import DeliberateExportRecovery
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import read_json
from portia.storage.staging import staging_path_for
from tests.test_teacher_reference_export_execution import (
    CONFIRMED,
    GENERATED,
    OPERATOR,
    REQUESTED,
    _decision,
    _execution_service,
    _ids,
    _prepare,
    _seed,
)
from tests.workflow_helpers import event_ref

RECOVERED = "2026-09-29T19:35:00-04:00"
LATER_GENERATED = "2026-09-29T19:40:00-04:00"
LATER_CONFIRMED = "2026-09-29T19:41:00-04:00"


def _pointer(operation_id: str):
    from portia.models import parse_portia_record

    return parse_portia_record(
        "operation_current_pointer",
        "1",
        {
            "schema_version": "1",
            "record_type": "operation_current_pointer",
            "module_id": "portia",
            "operation_id": operation_id,
            "journal_revision": 1,
        },
    )


def _persist_prepared_journal(
    tmp_path: Path, preparation
) -> None:  # type: ignore[no-untyped-def]
    OperationJournalStore(tmp_path).create(
        preparation.operation_journal,
        _pointer(preparation.operation_id),
    )


def _artifact_only(tmp_path: Path, preparation) -> None:  # type: ignore[no-untyped-def]
    _persist_prepared_journal(tmp_path, preparation)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        preparation.operation_journal,
        artifact_bytes=preparation.artifact_bytes,
        export=preparation.deliberate_export,
    )

    def fail_after_artifact(checkpoint: str, step_id: str | None) -> None:
        artifact_step = preparation.operation_journal.to_dict()["write_set"][0]
        assert isinstance(artifact_step, dict)
        if checkpoint == "after_publish" and step_id == artifact_step["step_id"]:
            raise RuntimeError("synthetic artifact-only interruption")

    with pytest.raises(PortiaOperationPartialCommitError):
        commit_deliberate_export_candidates(
            tmp_path,
            preparation.operation_journal,
            staged,
            artifact_bytes=preparation.artifact_bytes,
            export=preparation.deliberate_export,
            lock=preparation.operation_lock,
            fault_hook=fail_after_artifact,
        )
    assert DeliberateExportRecovery(tmp_path).assess(
        preparation.operation_id
    ).disposition == "artifact_only"


def _provenance_staging_path(
    tmp_path: Path, preparation
) -> Path:  # type: ignore[no-untyped-def]
    steps = preparation.operation_journal.to_dict()["write_set"]
    assert isinstance(steps, list)
    provenance = next(
        step
        for step in steps
        if isinstance(step, dict)
        and step.get("representation_role") == "deliberate_export_provenance"
    )
    step_id = provenance["step_id"]
    destination = provenance["destination_path"]
    assert isinstance(step_id, str) and isinstance(destination, str)
    return staging_path_for(
        tmp_path,
        preparation.operation_id,
        step_id,
        destination,
    )


def _commit_both_without_journal_recovery(
    tmp_path: Path, preparation
) -> None:  # type: ignore[no-untyped-def]
    _persist_prepared_journal(tmp_path, preparation)
    staged = stage_deliberate_export_candidates(
        tmp_path,
        preparation.operation_journal,
        artifact_bytes=preparation.artifact_bytes,
        export=preparation.deliberate_export,
    )
    commit_deliberate_export_candidates(
        tmp_path,
        preparation.operation_journal,
        staged,
        artifact_bytes=preparation.artifact_bytes,
        export=preparation.deliberate_export,
        lock=preparation.operation_lock,
    )
    assert DeliberateExportRecovery(tmp_path).assess(
        preparation.operation_id
    ).disposition == "exact_both_committed_journal_missing"


def _prepare_with_identity(
    tmp_path: Path,
    repository,
    *,
    export_token: str,
    operation_token: str,
    generated_at: str,
):  # type: ignore[no-untyped-def]
    decision = _decision(tmp_path, repository)
    service = TeacherReferenceExportPreparationService(
        tmp_path,
        repository=repository,
        id_generator=_ids(
            export_token,
            operation_token,
            f"artifact_{export_token}",
            f"provenance_{export_token}",
        ),
    )
    return service.prepare(
        decision,
        requested_at=REQUESTED,
        requested_by=OPERATOR,
        generated_at=generated_at,
        deployment_instance_id="deployment_test",
        process_instance_id="process_test",
    )


def test_artifact_only_recovery_uses_exact_staged_provenance(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _artifact_only(tmp_path, preparation)

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "recovered"
    assert result.initial_disposition == "artifact_only"
    assert result.final_disposition == "completed"
    assert (tmp_path / preparation.provenance_relative_path).read_bytes() == (
        preparation.provenance_bytes
    )
    current = OperationJournalStore(tmp_path).load_current(preparation.operation_id)
    assert current.revision.field("state") == "completed"


def test_artifact_only_recovery_fails_closed_without_staged_provenance(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _artifact_only(tmp_path, preparation)
    _provenance_staging_path(tmp_path, preparation).unlink()

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "recovery_required"
    assert result.final_disposition == "artifact_only"
    assert not (tmp_path / preparation.provenance_relative_path).exists()


def test_artifact_only_recovery_rejects_changed_staged_provenance(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _artifact_only(tmp_path, preparation)
    staged = _provenance_staging_path(tmp_path, preparation)
    staged.write_bytes(b"{}\n")

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "recovery_required"
    assert result.final_disposition == "artifact_only"
    assert staged.read_bytes() == b"{}\n"
    assert not (tmp_path / preparation.provenance_relative_path).exists()



def test_recovery_never_overwrites_mismatched_durable_artifact(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _artifact_only(tmp_path, preparation)
    artifact = tmp_path / preparation.artifact_relative_path
    artifact.write_bytes(b"contradictory durable artifact\n")

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "recovery_required"
    assert result.initial_disposition == "artifact_mismatch"
    assert artifact.read_bytes() == b"contradictory durable artifact\n"
    assert not (tmp_path / preparation.provenance_relative_path).exists()

def test_exact_both_recovery_reconstructs_committed_then_completed(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _commit_both_without_journal_recovery(tmp_path, preparation)

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "recovered"
    assert result.final_disposition == "completed"
    assert OperationJournalStore(tmp_path).load_current(
        preparation.operation_id
    ).revision.field("journal_revision") == 3


def test_completed_recovery_is_idempotent(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    execution = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )
    assert isinstance(execution, TeacherReferenceExportExecutionSuccess)
    before_artifact = (tmp_path / preparation.artifact_relative_path).read_bytes()
    before_provenance = (tmp_path / preparation.provenance_relative_path).read_bytes()

    result = TeacherReferenceExportRecoveryService(tmp_path).recover(
        preparation.operation_id,
        observed_at=RECOVERED,
        committed_at=RECOVERED,
    )

    assert result.code == "already_completed"
    assert (tmp_path / preparation.artifact_relative_path).read_bytes() == (
        before_artifact
    )
    assert (tmp_path / preparation.provenance_relative_path).read_bytes() == (
        before_provenance
    )


def test_history_lists_verified_export_for_exact_work(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )
    assert isinstance(result, TeacherReferenceExportExecutionSuccess)

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())

    assert len(history) == 1
    entry = history[0]
    assert entry.export_id == preparation.export_id
    assert entry.generated_at == GENERATED
    assert entry.projection_purpose == "teacher_current"
    assert entry.focal_participant is False
    assert entry.verification_status == "available_verified"


def test_history_reports_missing_and_mismatched_artifact_without_regeneration(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )
    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    artifact = tmp_path / preparation.artifact_relative_path
    artifact.unlink()

    missing = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())
    assert missing[0].verification_status == "artifact_missing"
    assert not artifact.exists()

    artifact.write_bytes(b"changed historical bytes\n")
    mismatch = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())
    assert mismatch[0].verification_status == "artifact_mismatch"
    assert artifact.read_bytes() == b"changed historical bytes\n"


def test_history_reports_operation_recovery_required_before_committed_revision(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    _commit_both_without_journal_recovery(tmp_path, preparation)

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())

    assert history[0].verification_status == "operation_recovery_required"


def test_history_reports_invalid_provenance_without_rewriting_it(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )
    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    provenance_path = tmp_path / preparation.provenance_relative_path
    raw, _content, _fingerprint = read_json(provenance_path)
    assert isinstance(raw, dict)
    raw["projection_decision_digest"] = "f" * 64
    changed = canonical_json_bytes(raw)
    provenance_path.write_bytes(changed)

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())

    assert history[0].verification_status == "provenance_invalid"
    assert provenance_path.read_bytes() == changed


def test_history_is_work_scoped_and_chronological_not_authoritative(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    first = _prepare_with_identity(
        tmp_path,
        repository,
        export_token="history_first",
        operation_token="history_first",
        generated_at=GENERATED,
    )
    second = _prepare_with_identity(
        tmp_path,
        repository,
        export_token="history_second",
        operation_token="history_second",
        generated_at=LATER_GENERATED,
    )
    for preparation, confirmed_at in (
        (first, CONFIRMED),
        (second, LATER_CONFIRMED),
    ):
        result = _execution_service(tmp_path, repository).execute(
            preparation,
            confirmation=TEACHER_REFERENCE_CONFIRMATION,
            confirmed_preparation_digest=preparation.preparation_digest,
            confirmed_at=confirmed_at,
        )
        assert isinstance(result, TeacherReferenceExportExecutionSuccess)

    foreign = tmp_path / "portia/exports/pexp_foreign/export.json"
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(
        canonical_json_bytes(
            {
                "export_id": "pexp_foreign",
                "export_scope": {
                    "scope": "work",
                    "work_ref": event_ref(event_id="evt_other").to_dict(),
                },
            }
        )
    )

    history = TeacherReferenceExportHistoryService(tmp_path).list_for_work(event_ref())

    assert [entry.export_id for entry in history] == [
        second.export_id,
        first.export_id,
    ]
    assert all(entry.verification_status == "available_verified" for entry in history)
    assert not hasattr(history[0], "current")
