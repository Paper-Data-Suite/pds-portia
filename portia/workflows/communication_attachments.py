"""Exact attachment authority for ``communication@1`` workflows."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from portia.models import PortiaRecord
from portia.models.references import ExactPortiaWorkRecordRef, ModuleWorkRecordRef
from portia.storage.errors import PortiaPathError, PortiaStorageError
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes
from portia.storage.paths import resolve_workspace_relative, workspace_relative
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)


class ModuleCommunicationAttachmentAuthority(Protocol):
    """Public exact-resolution authority for one sibling-module attachment."""

    def resolve_exact(self, reference: ModuleWorkRecordRef) -> object:
        """Resolve and authorize exactly the supplied sibling-module reference."""
        ...


@dataclass(frozen=True, slots=True)
class CommunicationAttachmentResolution:
    """One resolved attachment branch without changing its semantic authority."""

    kind: str
    stored: StoredRecord | None = None
    module_reference: ModuleWorkRecordRef | None = None
    module_value: object | None = None


def communication_attachments(
    record: PortiaRecord,
) -> tuple[Mapping[str, object], ...]:
    """Return schema-local Communication attachments as immutable mappings."""
    value = record.field("attachments")
    if value is None:
        return ()
    if not isinstance(value, tuple):
        raise WorkflowOwnershipError("Communication attachments are malformed")
    result: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise WorkflowOwnershipError("Communication attachment entry is malformed")
        result.append(item)
    return tuple(result)


def _workspace_file_authority(
    workspace_root: Path,
    attachment: Mapping[str, object],
) -> None:
    relative_path = attachment.get("path")
    fingerprint_value = attachment.get("fingerprint")
    if not isinstance(fingerprint_value, Mapping):
        raise WorkflowOwnershipError(
            "Communication workspace_file fingerprint is malformed"
        )
    try:
        expected = ContentFingerprint.from_dict(dict(fingerprint_value))
    except ValueError as exc:
        raise WorkflowOwnershipError(
            "Communication workspace_file fingerprint is malformed"
        ) from exc

    try:
        candidate = resolve_workspace_relative(workspace_root, relative_path)
        resolved = candidate.resolve(strict=True)
        workspace_relative(workspace_root, resolved)
    except (OSError, PortiaPathError) as exc:
        raise WorkflowPrerequisiteError(
            "Communication workspace_file must resolve within the selected workspace"
        ) from exc
    if not resolved.is_file():
        raise WorkflowPrerequisiteError(
            "Communication workspace_file must resolve to a regular file"
        )
    try:
        observed = fingerprint_bytes(read_bytes(resolved))
    except PortiaStorageError as exc:
        raise WorkflowPrerequisiteError(
            "Communication workspace_file could not be read exactly"
        ) from exc
    if observed != expected:
        raise WorkflowPrerequisiteError(
            "Communication workspace_file fingerprint does not match current bytes"
        )


def _is_self_attachment(
    record: PortiaRecord,
    reference: ExactPortiaWorkRecordRef,
) -> bool:
    return (
        record.class_id == reference.work_ref.class_id
        and record.work_id == reference.work_ref.work_id
        and record.work_kind == reference.work_ref.work_kind
        and reference.record_ref.record_kind == "communication"
        and reference.record_ref.record_id == record.logical_id
        and reference.record_ref.contract_version == record.contract_version
    )


def _portia_record_authority(
    repository: PortiaRepository,
    record: PortiaRecord,
    attachment: Mapping[str, object],
) -> StoredRecord:
    try:
        reference = ExactPortiaWorkRecordRef.from_dict(attachment.get("record_ref"))
    except Exception as exc:
        raise WorkflowOwnershipError(
            "Communication portia_record attachment reference is malformed"
        ) from exc
    if _is_self_attachment(record, reference):
        raise WorkflowPrerequisiteError("Communication cannot attach itself")
    repository.load_work(reference.work_ref)
    return repository.load_work_record(
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )


def _module_reference(attachment: Mapping[str, object]) -> ModuleWorkRecordRef:
    try:
        reference = ModuleWorkRecordRef.from_dict(
            attachment.get("module_work_record_ref")
        )
    except Exception as exc:
        raise WorkflowOwnershipError(
            "Communication module_record attachment reference is malformed"
        ) from exc
    if reference.work_ref.module_id != reference.record_ref.module_id:
        raise WorkflowOwnershipError(
            "Communication module_record work and record module identities disagree"
        )
    if reference.work_ref.module_id == "portia":
        raise WorkflowOwnershipError(
            "Portia records must use the Communication portia_record attachment branch"
        )
    return reference


def _module_record_authority(
    attachment: Mapping[str, object],
    *,
    module_authority: ModuleCommunicationAttachmentAuthority | None,
) -> CommunicationAttachmentResolution:
    reference = _module_reference(attachment)
    if module_authority is None:
        raise WorkflowPrerequisiteError(
            "Communication module_record attachment requires an explicit public "
            "resolution authority"
        )
    resolved = module_authority.resolve_exact(reference)
    if resolved is None:
        raise WorkflowPrerequisiteError(
            "Communication module_record attachment did not resolve through the "
            "supplied authority"
        )
    return CommunicationAttachmentResolution(
        kind="module_record",
        module_reference=reference,
        module_value=resolved,
    )


def require_communication_attachment_authority(
    workspace_root: str | Path,
    repository: PortiaRepository,
    record: PortiaRecord,
    *,
    module_authority: ModuleCommunicationAttachmentAuthority | None = None,
) -> tuple[CommunicationAttachmentResolution, ...]:
    """Resolve supported attachments without successor or foreign-authority guessing."""
    resolutions: list[CommunicationAttachmentResolution] = []
    for attachment in communication_attachments(record):
        kind = attachment.get("kind")
        if kind == "workspace_file":
            _workspace_file_authority(Path(workspace_root), attachment)
            resolutions.append(CommunicationAttachmentResolution(kind=kind))
            continue
        if kind == "portia_record":
            stored = _portia_record_authority(repository, record, attachment)
            resolutions.append(
                CommunicationAttachmentResolution(kind=kind, stored=stored)
            )
            continue
        if kind == "module_record":
            resolutions.append(
                _module_record_authority(
                    attachment,
                    module_authority=module_authority,
                )
            )
            continue
        if kind == "external_record":
            resolutions.append(CommunicationAttachmentResolution(kind=kind))
            continue
        raise WorkflowOwnershipError(
            f"unsupported Communication attachment kind {kind!r}"
        )
    return tuple(resolutions)
