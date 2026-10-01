from __future__ import annotations

from pathlib import Path

import pytest

from portia.exports import (
    TeacherReferenceExportScope,
    TeacherReferenceManualReviewChoice,
    TeacherReferenceProjectionService,
    TeacherReferenceScopeDiscoveryService,
)
from portia.exports.preparation import (
    TEACHER_REFERENCE_AUTHORIZATION_SCOPE_ID,
    TEACHER_REFERENCE_PREPARATION_ID,
    TEACHER_REFERENCE_PREPARATION_VERSION,
    TeacherReferenceExportPreparationService,
)
from portia.menu.identifiers import PortiaIdGenerator
from portia.models.errors import PortiaLocalValidationError
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage import PortiaRepository
from portia.storage.deliberate_export_operations import (
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_lock_agreement,
)
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.locks import validate_operation_lock_application
from portia.storage.operation_journal import validate_operation_journal_application
from portia.views import CurrentnessDecision
from tests.workflow_helpers import event_record, event_ref, participant_record

REQUESTED = "2026-09-29T19:30:00-04:00"
GENERATED = "2026-09-29T19:31:00-04:00"
REVIEWED = "2026-09-29T19:30:30-04:00"
OPERATOR = {"type": "local_operator", "display_label": "Synthetic Teacher"}


class _Currentness:
    def evaluate(
        self,
        source_ref: ExactPortiaWorkRef | ExactPortiaWorkRecordRef,
    ) -> CurrentnessDecision:
        return CurrentnessDecision(source_ref, "current", "synthetic_current")


def _seed(tmp_path: Path) -> PortiaRepository:
    repository = PortiaRepository(tmp_path)
    repository.create_work(event_ref(), event_record())
    repository.create_work_record(event_ref(), participant_record())
    return repository


def _participant_ref() -> ExactPortiaWorkRecordRef:
    return ExactPortiaWorkRecordRef(
        work_ref=event_ref(),
        record_ref=ExactLocalRecordRef(
            record_kind="event_participant",
            record_id="ep_alpha",
            contract_version="3",
        ),
    )


def _decision(
    tmp_path: Path,
    *,
    repository: PortiaRepository | None = None,
    purpose: str = "teacher_current",
):
    repo = repository or _seed(tmp_path)
    focal = _participant_ref() if purpose == "participant_specific" else None
    discovery = TeacherReferenceScopeDiscoveryService(
        tmp_path,
        repository=repo,
        currentness=_Currentness(),
    ).discover(
        TeacherReferenceExportScope(
            purpose,
            event_ref(),
            focal,
        )
    )
    service = TeacherReferenceProjectionService(tmp_path, repository=repo)
    pending = service.project(discovery)
    choices = []
    for item in pending.unresolved_manual_items:
        assert item.field_name is not None
        resolution = (
            "include_exact"
            if item.source_ref == event_ref() and item.field_name == "summary"
            else "omit"
        )
        choices.append(
            TeacherReferenceManualReviewChoice(
                item.source_ref,
                item.field_name,
                resolution,
            )
        )
    final = service.resolve_manual_review(
        pending,
        choices,
        reviewed_at=REVIEWED,
        reviewed_by=OPERATOR,
    )
    return repo, pending, final


def _ids(*tokens: str) -> PortiaIdGenerator:
    iterator = iter(tokens)
    return PortiaIdGenerator(token_source=iterator.__next__)


def _prepare(
    tmp_path: Path,
    repository: PortiaRepository,
    decision: object,
    *,
    tokens: tuple[str, str, str, str] = (
        "export_alpha",
        "operation_alpha",
        "artifact_alpha",
        "provenance_alpha",
    ),
):
    service = TeacherReferenceExportPreparationService(
        tmp_path,
        repository=repository,
        id_generator=_ids(*tokens),
    )
    return service.prepare(
        decision,
        requested_at=REQUESTED,
        requested_by=OPERATOR,
        generated_at=GENERATED,
        deployment_instance_id="deployment_test",
        process_instance_id="process_test",
    )


def test_preparation_authors_exact_issue88_candidates(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    preparation = _prepare(tmp_path, repository, decision)

    assert preparation.preparation_id == TEACHER_REFERENCE_PREPARATION_ID
    assert preparation.preparation_version == TEACHER_REFERENCE_PREPARATION_VERSION
    assert preparation.export_id == "pexp_export_alpha"
    assert preparation.operation_id == "op_operation_alpha"
    assert preparation.artifact_relative_path == (
        "portia/exports/pexp_export_alpha/artifact.html"
    )
    assert preparation.provenance_relative_path == (
        "portia/exports/pexp_export_alpha/export.json"
    )
    assert preparation.authorization.authorization_scope_id == (
        TEACHER_REFERENCE_AUTHORIZATION_SCOPE_ID
    )

    export = preparation.deliberate_export.to_dict()
    assert export["projection_purpose"] == "teacher_current"
    assert export["projection_decision_digest"] == decision.projection_decision_digest
    assert export["source_inventory"] == preparation.inventory.to_dict()
    assert export["output"] == {
        "format": "html",
        "media_type": "text/html",
        "workspace_relative_path": preparation.artifact_relative_path,
        "byte_length": preparation.artifact.byte_length,
        "sha256_digest": preparation.artifact.representation_digest,
    }
    assert export["operation_journal_ref"] == {
        "operation_id": preparation.operation_id,
        "journal_revision": 2,
        "contract_version": "4",
    }

    validate_operation_journal_application(preparation.operation_journal)
    validate_operation_lock_application(preparation.operation_lock)
    validate_deliberate_export_lock_agreement(
        preparation.operation_journal,
        preparation.operation_lock,
    )
    validate_deliberate_export_candidate_reconciliation(
        preparation.operation_journal,
        preparation.deliberate_export,
    )
    assert planned_deliberate_export_commit_revision(preparation.operation_journal) == 2

    journal = preparation.operation_journal.to_dict()
    assert journal["state"] == "staged"
    assert journal["operation_kind"] == "generate_deliberate_export"
    assert journal["affected_targets"] == []
    assert journal["intent_facts"] == []
    write_set = journal["write_set"]
    assert isinstance(write_set, list)
    assert [item["representation_role"] for item in write_set] == [
        "deliberate_export_artifact",
        "deliberate_export_provenance",
    ]
    assert [item["destination_path"] for item in write_set] == [
        preparation.artifact_relative_path,
        preparation.provenance_relative_path,
    ]


def test_preparation_preview_shows_actual_outgoing_content(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    preparation = _prepare(tmp_path, repository, decision)
    preview = preparation.preview

    assert preview.selected_work == "Event (evt_alpha)"
    assert preview.projection_purpose_label == "Teacher current work reference"
    assert preview.artifact_format == "html"
    assert "Work Context" in preview.included_sections
    assert "Participants / Participation" in preview.included_sections
    assert preview.artifact_html == preparation.artifact.text
    assert "Synthetic neutral classroom context." in preview.artifact_html
    assert preview.included_count == decision.disposition_summary.included
    assert preview.withheld_count == decision.disposition_summary.withheld
    assert preview.unavailable_count == decision.disposition_summary.unavailable
    assert preview.manual_review_decisions
    assert any(
        item.field_name == "summary" and item.resolution == "include_exact"
        for item in preview.manual_review_decisions
    )
    assert preview.warnings
    assert preview.preparation_digest == preparation.preparation_digest


def test_participant_preview_uses_frozen_display_snapshot_only(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(
        tmp_path,
        purpose="participant_specific",
    )
    preparation = _prepare(tmp_path, repository, decision)

    assert preparation.preview.focal_participant == "Same Display"
    assert "student_1" not in preparation.preview.artifact_html
    assert "Participant-specific scope" in " ".join(preparation.preview.warnings)


def test_preparation_is_deterministic_for_frozen_inputs_and_ids(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    first = _prepare(tmp_path, repository, decision)
    second = _prepare(tmp_path, repository, decision)

    assert first.artifact.content == second.artifact.content
    assert first.inventory.inventory_digest == second.inventory.inventory_digest
    assert first.deliberate_export.to_dict() == second.deliberate_export.to_dict()
    assert first.operation_journal.to_dict() == second.operation_journal.to_dict()
    assert first.operation_lock.to_dict() == second.operation_lock.to_dict()
    assert first.preparation_fingerprint == second.preparation_fingerprint


def test_preparation_fingerprint_binds_future_identity(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    first = _prepare(tmp_path, repository, decision)
    second = _prepare(
        tmp_path,
        repository,
        decision,
        tokens=(
            "export_beta",
            "operation_beta",
            "artifact_beta",
            "provenance_beta",
        ),
    )

    assert first.artifact.content == second.artifact.content
    assert first.preparation_digest != second.preparation_digest
    assert first.export_id != second.export_id
    assert first.operation_id != second.operation_id


def test_preparation_is_zero_write(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    before = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    preparation = _prepare(tmp_path, repository, decision)

    after = {
        path.relative_to(tmp_path): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert before == after
    assert not (tmp_path / preparation.artifact_relative_path).exists()
    assert not (tmp_path / preparation.provenance_relative_path).exists()
    assert not any((tmp_path / "portia").glob("locks/*.json"))
    assert not any(tmp_path.rglob(".portia-staging"))


def test_preparation_rejects_unresolved_manual_review(tmp_path: Path) -> None:
    repository, pending, _decision_value = _decision(tmp_path)
    service = TeacherReferenceExportPreparationService(
        tmp_path,
        repository=repository,
        id_generator=_ids("a", "b", "c", "d"),
    )

    with pytest.raises(PortiaLocalValidationError, match="completed manual review"):
        service.prepare(
            pending,
            requested_at=REQUESTED,
            requested_by=OPERATOR,
            generated_at=GENERATED,
            deployment_instance_id="deployment_test",
            process_instance_id="process_test",
        )


def test_preparation_requires_local_operator_and_chronology(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    service = TeacherReferenceExportPreparationService(
        tmp_path,
        repository=repository,
        id_generator=_ids("a", "b", "c", "d"),
    )

    with pytest.raises(PortiaLocalValidationError, match="local_operator"):
        service.prepare(
            decision,
            requested_at=REQUESTED,
            requested_by={"type": "system_process", "process_id": "synthetic_process"},
            generated_at=GENERATED,
            deployment_instance_id="deployment_test",
            process_instance_id="process_test",
        )

    with pytest.raises(PortiaLocalValidationError, match="predate"):
        service.prepare(
            decision,
            requested_at=GENERATED,
            requested_by=OPERATOR,
            generated_at=REQUESTED,
            deployment_instance_id="deployment_test",
            process_instance_id="process_test",
        )


def test_provenance_candidate_bytes_are_exact_and_bound(tmp_path: Path) -> None:
    repository, _pending, decision = _decision(tmp_path)
    preparation = _prepare(tmp_path, repository, decision)

    assert preparation.provenance_bytes == canonical_json_bytes(
        preparation.deliberate_export.to_dict()
    )
    journal = preparation.operation_journal.to_dict()
    write_set = journal["write_set"]
    assert isinstance(write_set, list)
    provenance_step = write_set[1]
    assert isinstance(provenance_step, dict)
    intended = provenance_step["intended_result"]
    assert isinstance(intended, dict)
    assert intended["fingerprint"] == fingerprint_bytes(
        preparation.provenance_bytes
    ).to_dict()
