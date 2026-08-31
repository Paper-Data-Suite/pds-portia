"""Focused Slice 8 tests for schema-local Communication attachment authority."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRecordRef, ExactPortiaWorkRef
from portia.storage.fingerprint import fingerprint_bytes
from portia.workflows import (
    CommunicationWorkflowService,
    ModuleCommunicationAttachmentAuthority,
)
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_FIXTURE_ROOT = (
    Path(__file__).parent
    / "schema_validation"
    / "fixtures"
    / "issue-17"
    / "communication"
)


def _wire(path: str, *, section: str = "valid") -> dict[str, object]:
    return json.loads(
        (_FIXTURE_ROOT / section / path).read_text(encoding="utf-8")
    )


def _communication(path: str, *, section: str = "valid") -> PortiaRecord:
    return parse_portia_record("communication", "1", _wire(path, section=section))


def _work_for(record: PortiaRecord) -> ExactPortiaWorkRef:
    assert record.class_id is not None
    assert record.work_id is not None
    return ExactPortiaWorkRef(
        class_id=record.class_id,
        work_id=record.work_id,
        work_kind="event",
        contract_version="2",
    )


def _service(
    tmp_path: Path,
    *,
    module_authority: ModuleCommunicationAttachmentAuthority | None = None,
) -> tuple[CommunicationWorkflowService, Mock, Mock]:
    repository = Mock()
    repository.load_work.return_value = SimpleNamespace(
        record=SimpleNamespace(
            contract="event",
            contract_version="2",
            status="active",
        )
    )
    repository.load_work_record.return_value = SimpleNamespace(
        record=SimpleNamespace(status="superseded")
    )
    repository.create_work_record.return_value = SimpleNamespace(record="stored")
    contexts = Mock()
    service = CommunicationWorkflowService(
        tmp_path,
        repository=repository,
        quarantine=Mock(),
        context_assembler=contexts,
        module_attachment_authority=module_authority,
    )
    return service, repository, contexts


def _attachment(record: PortiaRecord) -> dict[str, object]:
    attachments = record.to_dict()["attachments"]
    assert isinstance(attachments, list)
    item = attachments[0]
    assert isinstance(item, dict)
    return item


def test_workspace_file_attachment_requires_current_exact_bytes(
    tmp_path: Path,
) -> None:
    value = _wire("workspace-file-attachment.json")
    attachment = value["attachments"][0]  # type: ignore[index]
    assert isinstance(attachment, dict)
    path = tmp_path / str(attachment["path"])
    path.parent.mkdir(parents=True)
    content = b"synthetic communication attachment\n"
    path.write_bytes(content)
    attachment["fingerprint"] = fingerprint_bytes(content).to_dict()
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)

    service.create(work, candidate)

    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_workspace_file_attachment_rejects_fingerprint_drift(tmp_path: Path) -> None:
    candidate = _communication("workspace-file-attachment.json")
    attachment = _attachment(candidate)
    path = tmp_path / str(attachment["path"])
    path.parent.mkdir(parents=True)
    path.write_bytes(b"different bytes\n")
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="fingerprint"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_workspace_file_attachment_rejects_missing_file(tmp_path: Path) -> None:
    candidate = _communication("workspace-file-attachment.json")
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="selected workspace"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_portia_record_attachment_resolves_exact_historical_representation(
    tmp_path: Path,
) -> None:
    candidate = _communication("portia-record-attachment.json")
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)
    attachment = _attachment(candidate)
    reference = ExactPortiaWorkRecordRef.from_dict(attachment["record_ref"])

    service.create(work, candidate)

    repository.load_work_record.assert_called_once_with(
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_self_portia_record_attachment_is_rejected_before_target_load(
    tmp_path: Path,
) -> None:
    candidate = _communication(
        "self-portia-attachment.json",
        section="application-invalid",
    )
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="attach itself"):
        service.create(work, candidate)

    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_module_record_attachment_uses_only_explicit_public_authority(
    tmp_path: Path,
) -> None:
    authority = Mock()
    authority.resolve_exact.return_value = object()
    candidate = _communication("module-record-attachment.json")
    work = _work_for(candidate)
    service, repository, _contexts = _service(
        tmp_path,
        module_authority=authority,
    )

    service.create(work, candidate)

    authority.resolve_exact.assert_called_once()
    reference = authority.resolve_exact.call_args.args[0]
    assert reference.work_ref.module_id == "quillan"
    assert reference.record_ref.module_id == "quillan"
    assert reference.record_ref.record_id == "submission_001"
    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_called_once_with(work, candidate)


def test_new_module_attachment_fails_closed_without_public_authority(
    tmp_path: Path,
) -> None:
    candidate = _communication("module-record-attachment.json")
    work = _work_for(candidate)
    service, repository, _contexts = _service(tmp_path)

    with pytest.raises(WorkflowPrerequisiteError, match="explicit public"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_module_attachment_fails_closed_when_authority_resolves_nothing(
    tmp_path: Path,
) -> None:
    authority = Mock()
    authority.resolve_exact.return_value = None
    candidate = _communication("module-record-attachment.json")
    work = _work_for(candidate)
    service, repository, _contexts = _service(
        tmp_path,
        module_authority=authority,
    )

    with pytest.raises(WorkflowPrerequisiteError, match="did not resolve"):
        service.create(work, candidate)

    repository.create_work_record.assert_not_called()


def test_module_attachment_rejects_mismatched_module_identity_before_authority(
    tmp_path: Path,
) -> None:
    authority = Mock()
    candidate = _communication(
        "module-attachment-module-mismatch.json",
        section="application-invalid",
    )
    work = _work_for(candidate)
    service, repository, _contexts = _service(
        tmp_path,
        module_authority=authority,
    )

    with pytest.raises(WorkflowOwnershipError, match="module identities disagree"):
        service.create(work, candidate)

    authority.resolve_exact.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_portia_module_attachment_must_use_portia_record_branch(
    tmp_path: Path,
) -> None:
    value = _wire("module-record-attachment.json")
    attachment = value["attachments"][0]  # type: ignore[index]
    assert isinstance(attachment, dict)
    reference = attachment["module_work_record_ref"]
    assert isinstance(reference, dict)
    work_ref = reference["work_ref"]
    record_ref = reference["record_ref"]
    assert isinstance(work_ref, dict)
    assert isinstance(record_ref, dict)
    work_ref["module_id"] = "portia"
    record_ref["module_id"] = "portia"
    candidate = parse_portia_record("communication", "1", value)
    work = _work_for(candidate)
    authority = Mock()
    service, repository, _contexts = _service(
        tmp_path,
        module_authority=authority,
    )

    with pytest.raises(WorkflowOwnershipError, match="portia_record"):
        service.create(work, candidate)

    authority.resolve_exact.assert_not_called()
    repository.create_work_record.assert_not_called()


def test_external_record_attachment_is_inert_metadata(tmp_path: Path) -> None:
    candidate = _communication("external-record-attachment.json")
    work = _work_for(candidate)
    authority = Mock()
    service, repository, _contexts = _service(
        tmp_path,
        module_authority=authority,
    )

    service.create(work, candidate)

    authority.resolve_exact.assert_not_called()
    repository.load_work_record.assert_not_called()
    repository.create_work_record.assert_called_once_with(work, candidate)
