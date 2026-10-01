from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

import portia.exports.execution as execution_module
from portia.exports import (
    TEACHER_REFERENCE_EXPORT_POLICY,
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
)
from portia.exports.execution import (
    TEACHER_REFERENCE_CONFIRMATION,
    TeacherReferenceExportExecutionFailure,
    TeacherReferenceExportExecutionService,
    TeacherReferenceExportExecutionSuccess,
)
from portia.exports.preparation import TeacherReferenceExportPreparationService
from portia.exports.rendering import (
    TeacherReferenceHtmlRenderer,
    TeacherReferenceRenderedArtifact,
)
from portia.menu.identifiers import PortiaIdGenerator
from portia.models import parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage import (
    OperationJournalStore,
    PortiaOperationPartialCommitError,
    PortiaRepository,
)
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.io import read_bytes
from portia.storage.paths import operation_revision_path, operation_root
from portia.views import CurrentnessDecision
from tests.workflow_helpers import event_record, event_ref, participant_record

REQUESTED = "2026-09-29T19:30:00-04:00"
GENERATED = "2026-09-29T19:31:00-04:00"
REVIEWED = "2026-09-29T19:30:30-04:00"
CONFIRMED = "2026-09-29T19:32:00-04:00"
OPERATOR = {"type": "local_operator", "display_label": "Synthetic Teacher"}


class _Currentness:
    def evaluate(
        self,
        source_ref: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> CurrentnessDecision:
        return CurrentnessDecision(source_ref, "current", "synthetic_current")


class _ChangedRenderer(TeacherReferenceHtmlRenderer):
    def render(self, decision, inventory):  # type: ignore[no-untyped-def]
        base = super().render(decision, inventory)
        content = base.content.replace(b"</body>\n", b"<p>changed renderer</p>\n</body>\n")
        return TeacherReferenceRenderedArtifact(content, fingerprint_bytes(content))


def _seed(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), participant_record())
    return repository


def _decision(tmp_path: Path, repository: PortiaRepository):
    discovery_service = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repository,
        currentness=_Currentness(),
    )
    discovery = discovery_service.discover(
        TeacherReferenceExportScope("teacher_current", event_ref())
    )
    projection_service = TeacherReferenceProjectionService(
        tmp_path,
        repository=repository,
    )
    pending = projection_service.project(discovery)
    choices = []
    for item in pending.unresolved_manual_items:
        assert item.field_name is not None
        choices.append(
            TeacherReferenceManualReviewChoice(
                item.source_ref,
                item.field_name,
                (
                    "include_exact"
                    if item.source_ref == event_ref() and item.field_name == "summary"
                    else "omit"
                ),
            )
        )
    return projection_service.resolve_manual_review(
        pending,
        choices,
        reviewed_at=REVIEWED,
        reviewed_by=OPERATOR,
    )


def _ids(*tokens: str) -> PortiaIdGenerator:
    iterator = iter(tokens)
    return PortiaIdGenerator(token_source=iterator.__next__)


def _prepare(tmp_path: Path, repository: PortiaRepository):
    decision = _decision(tmp_path, repository)
    service = TeacherReferenceExportPreparationService(
        tmp_path,
        repository=repository,
        id_generator=_ids(
            "export_exec",
            "operation_exec",
            "artifact_exec",
            "provenance_exec",
        ),
    )
    return service.prepare(
        decision,
        requested_at=REQUESTED,
        requested_by=OPERATOR,
        generated_at=GENERATED,
        deployment_instance_id="deployment_test",
        process_instance_id="process_test",
    )


def _execution_service(
    tmp_path: Path,
    repository: PortiaRepository,
    *,
    renderer: TeacherReferenceHtmlRenderer | None = None,
    policy=TEACHER_REFERENCE_EXPORT_POLICY,
) -> TeacherReferenceExportExecutionService:
    return TeacherReferenceExportExecutionService(
        tmp_path,
        repository=repository,
        discovery_service=TeacherReferenceScopeDiscoveryService(
            tmp_path,
            repository=repository,
            currentness=_Currentness(),
        ),
        projection_service=TeacherReferenceProjectionService(
            tmp_path,
            repository=repository,
        ),
        renderer=renderer,
        policy=policy,
    )


def _files(tmp_path: Path) -> dict[Path, bytes]:
    return {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }


def test_execute_exact_preparation_completes_issue88_operation(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    service = _execution_service(tmp_path, repository)

    result = service.execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    assert result.export_id == preparation.export_id
    assert result.operation_id == preparation.operation_id
    assert result.committed_journal_revision == 2
    assert result.completed_journal_revision == 3
    assert read_bytes(tmp_path / preparation.artifact_relative_path) == preparation.artifact_bytes
    assert read_bytes(tmp_path / preparation.provenance_relative_path) == preparation.provenance_bytes

    committed_path = operation_revision_path(tmp_path, preparation.operation_id, 2)
    committed_raw = committed_path.read_text(encoding="utf-8")
    assert '"state":"committed"' in committed_raw
    current = OperationJournalStore(tmp_path).load_current(preparation.operation_id)
    assert current.revision.field("state") == "completed"
    assert current.revision.field("journal_revision") == 3


def test_confirmation_must_be_explicit_and_bind_exact_preparation(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    service = _execution_service(tmp_path, repository)
    before = _files(tmp_path)

    wrong_word = service.execute(
        preparation,
        confirmation="",
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )
    wrong_digest = service.execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest="0" * 64,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(wrong_word, TeacherReferenceExportExecutionFailure)
    assert wrong_word.code == "confirmation_required"
    assert isinstance(wrong_digest, TeacherReferenceExportExecutionFailure)
    assert wrong_digest.code == "confirmation_required"
    assert _files(tmp_path) == before
    assert not operation_root(tmp_path, preparation.operation_id).exists()


def test_source_change_after_preview_fails_closed_before_write(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    stored = repository.load_work(event_ref())
    changed = stored.record.to_dict()
    changed["summary"] = "Changed after preview."
    repository.replace_work(
        event_ref(),
        parse_portia_record("event", "2", changed),
        expected=stored.fingerprint,
    )
    before_execution = _files(tmp_path)

    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionFailure)
    assert result.code == "prepared_state_changed"
    assert not result.durable_state_may_exist
    assert _files(tmp_path) == before_execution
    assert not operation_root(tmp_path, preparation.operation_id).exists()


def test_policy_digest_change_marks_preview_stale(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    changed_policy = replace(
        TEACHER_REFERENCE_EXPORT_POLICY,
        policy_digest="f" * 64,
    )
    service = _execution_service(tmp_path, repository, policy=changed_policy)

    check = service.revalidate(preparation)

    assert not check.is_current
    assert check.detail_code == "policy_changed"
    assert not operation_root(tmp_path, preparation.operation_id).exists()


def test_renderer_drift_marks_preview_stale_without_writes(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    before = _files(tmp_path)
    service = _execution_service(
        tmp_path,
        repository,
        renderer=_ChangedRenderer(),
    )

    result = service.execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionFailure)
    assert result.code == "prepared_state_changed"
    assert _files(tmp_path) == before


def test_output_collision_after_preview_fails_preflight_without_operation_write(
    tmp_path: Path,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    target = tmp_path / preparation.artifact_relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"foreign bytes\n")

    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionFailure)
    assert result.code == "prepared_state_changed"
    assert target.read_bytes() == b"foreign bytes\n"
    assert not operation_root(tmp_path, preparation.operation_id).exists()


def test_partial_commit_is_translated_to_stable_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)

    def fail_commit(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise PortiaOperationPartialCommitError(
            operation_id=preparation.operation_id,
            accepted_steps=("step_artifact",),
            held_lock_ids=("lock_synthetic",),
        )

    monkeypatch.setattr(
        execution_module,
        "commit_deliberate_export_candidates",
        fail_commit,
    )
    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionFailure)
    assert result.code == "recovery_required"
    assert result.durable_state_may_exist
    assert operation_root(tmp_path, preparation.operation_id).exists()


def test_execution_never_substitutes_fresh_export_identity(tmp_path: Path) -> None:
    repository = _seed(tmp_path)
    preparation = _prepare(tmp_path, repository)
    result = _execution_service(tmp_path, repository).execute(
        preparation,
        confirmation=TEACHER_REFERENCE_CONFIRMATION,
        confirmed_preparation_digest=preparation.preparation_digest,
        confirmed_at=CONFIRMED,
    )

    assert isinstance(result, TeacherReferenceExportExecutionSuccess)
    assert result.export_id == "pexp_export_exec"
    assert (tmp_path / "portia/exports/pexp_export_exec/artifact.html").exists()
    export_dirs = tuple((tmp_path / "portia/exports").iterdir())
    assert [path.name for path in export_dirs] == ["pexp_export_exec"]
