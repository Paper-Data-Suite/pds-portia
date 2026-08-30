"""Bounded source-artifact authority for Account/Observation workflows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import (
    ExactLocalRecordRef,
    ExactPortiaWorkRecordRef,
    ExactPortiaWorkRef,
)
from portia.storage.errors import PortiaPathError, PortiaStorageError
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes
from portia.storage.paths import resolve_workspace_relative, workspace_relative
from portia.storage.repository import PortiaRepository, StoredRecord
from portia.workflows.errors import (
    WorkflowOwnershipError,
    WorkflowPrerequisiteError,
)

_SUPPORTED_CURRENT_ARTIFACT_KINDS = frozenset({"workspace_file", "portia_work_record"})
_DEFERRED_CURRENT_ARTIFACT_KINDS = frozenset(
    {"paper_capture", "module_work_record", "external_record"}
)


def evidence_validation_record(record: PortiaRecord) -> PortiaRecord:
    """Project evidence for domain-graph validation after artifact authority is checked.

    ``source_artifacts`` use their own authority boundary.  Removing only that optional
    field prevents the generic complete-graph validator from recursively treating a
    provenance locator as if the referenced record's whole domain graph were being
    activated by the evidence operation.
    """
    if record.contract not in {"account", "observation"}:
        return record
    data = record.to_dict()
    if data.pop("source_artifacts", None) is None:
        return record
    return parse_portia_record(record.contract, record.contract_version, data)


def evidence_validation_records(
    records: Sequence[PortiaRecord],
) -> tuple[PortiaRecord, ...]:
    """Return a duplicate-free graph projection for evidence-domain validation."""
    values: list[PortiaRecord] = []
    seen: set[tuple[str, str, str | None, str | None, str | None]] = set()
    for record in records:
        projected = evidence_validation_record(record)
        key = (
            projected.contract,
            projected.contract_version,
            projected.class_id,
            projected.work_id,
            projected.logical_id,
        )
        if key in seen:
            continue
        seen.add(key)
        values.append(projected)
    return tuple(values)


def _artifact_entries(record: PortiaRecord) -> tuple[Mapping[str, object], ...]:
    value = record.field("source_artifacts")
    if value is None:
        return ()
    if not isinstance(value, tuple):
        raise WorkflowOwnershipError("source_artifacts collection is malformed")
    entries: list[Mapping[str, object]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise WorkflowOwnershipError("source artifact entry is malformed")
        entries.append(item)
    return tuple(entries)


def require_artifact_review_source(record: PortiaRecord) -> None:
    """Require an Observation artifact-review method to name reviewed material."""
    if record.contract != "observation" or record.field("method") != "artifact_review":
        return
    if not _artifact_entries(record):
        raise WorkflowPrerequisiteError(
            "artifact_review Observation requires at least one source artifact"
        )


def _workspace_file_authority(
    workspace_root: Path,
    artifact: Mapping[str, object],
) -> None:
    relative_path = artifact.get("path")
    fingerprint_value = artifact.get("fingerprint")
    if not isinstance(fingerprint_value, Mapping):
        raise WorkflowOwnershipError(
            "workspace_file source artifact fingerprint is malformed"
        )
    try:
        expected = ContentFingerprint.from_dict(dict(fingerprint_value))
    except ValueError as exc:
        raise WorkflowOwnershipError(
            "workspace_file source artifact fingerprint is malformed"
        ) from exc

    try:
        candidate = resolve_workspace_relative(workspace_root, relative_path)
        resolved = candidate.resolve(strict=True)
        workspace_relative(workspace_root, resolved)
    except (OSError, PortiaPathError) as exc:
        raise WorkflowPrerequisiteError(
            "workspace_file source artifact must resolve within the selected workspace"
        ) from exc
    if not resolved.is_file():
        raise WorkflowPrerequisiteError(
            "workspace_file source artifact must resolve to a regular file"
        )
    try:
        observed = fingerprint_bytes(read_bytes(resolved))
    except PortiaStorageError as exc:
        raise WorkflowPrerequisiteError(
            "workspace_file source artifact could not be read exactly"
        ) from exc
    if observed != expected:
        raise WorkflowPrerequisiteError(
            "workspace_file source artifact fingerprint does not match current bytes"
        )


def _exact_portia_artifact_reference(
    artifact: Mapping[str, object],
) -> ExactPortiaWorkRecordRef:
    composite = artifact.get("work_record_ref")
    if not isinstance(composite, Mapping):
        raise WorkflowOwnershipError(
            "portia_work_record source artifact reference is malformed"
        )
    work_value = composite.get("work_ref")
    record_value = composite.get("record_ref")
    if not isinstance(work_value, Mapping) or not isinstance(record_value, Mapping):
        raise WorkflowOwnershipError(
            "portia_work_record source artifact reference is incomplete"
        )
    try:
        work = ExactPortiaWorkRef(
            module_id=str(work_value["module_id"]),
            class_id=str(work_value["class_id"]),
            work_id=str(work_value["work_id"]),
            work_kind=str(work_value["work_kind"]),
            contract_version=str(work_value["contract_version"]),
        )
        local = ExactLocalRecordRef(
            record_kind=str(record_value["record_kind"]),
            record_id=str(record_value["record_id"]),
            contract_version=str(record_value["contract_version"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WorkflowOwnershipError(
            "portia_work_record source artifact reference is malformed"
        ) from exc
    return ExactPortiaWorkRecordRef(work_ref=work, record_ref=local)


def _portia_work_record_authority(
    repository: PortiaRepository,
    artifact: Mapping[str, object],
) -> StoredRecord:
    reference = _exact_portia_artifact_reference(artifact)
    repository.load_work(reference.work_ref)
    return repository.load_work_record(
        reference.work_ref,
        reference.record_ref.record_kind,
        reference.record_ref.contract_version,
        reference.record_ref.record_id,
    )


def require_source_artifact_refs_authority(
    workspace_root: str | Path,
    repository: PortiaRepository,
    artifacts: Sequence[object],
    *,
    require_current_use: bool,
) -> tuple[StoredRecord, ...]:
    """Verify an explicit sequence of ``source_artifact_ref@1`` values.

    This is the shared locator-authority primitive used by source evidence and by
    judgment authority/process provenance. It verifies only supported local locator
    authority; it never claims authenticity, legal sufficiency, applicability,
    credibility, or evidentiary weight.
    """
    resolved_portia: list[StoredRecord] = []
    for artifact_value in artifacts:
        if not isinstance(artifact_value, Mapping):
            raise WorkflowOwnershipError("source artifact entry is malformed")
        artifact = artifact_value
        kind = artifact.get("kind")
        if kind == "workspace_file":
            _workspace_file_authority(Path(workspace_root), artifact)
            continue
        if kind == "portia_work_record":
            resolved_portia.append(_portia_work_record_authority(repository, artifact))
            continue
        if kind in _DEFERRED_CURRENT_ARTIFACT_KINDS:
            if require_current_use:
                raise WorkflowPrerequisiteError(
                    f"{kind} source artifact requires authority outside "
                    "Issue #41 current-use execution"
                )
            continue
        if kind not in _SUPPORTED_CURRENT_ARTIFACT_KINDS:
            raise WorkflowOwnershipError(f"unsupported source artifact kind {kind!r}")
    return tuple(resolved_portia)


def require_source_artifact_authority(
    workspace_root: str | Path,
    repository: PortiaRepository,
    record: PortiaRecord,
    *,
    require_current_use: bool,
) -> tuple[StoredRecord, ...]:
    """Verify source-artifact authority available inside the v0.2 local boundary.

    Proposed/history records may preserve structurally valid deferred artifact branches.
    Active/current evidence may rely only on artifact kinds that Issue #41 can verify
    without paper/PDS2 execution, sibling-module readers, or external dereferencing.
    """
    require_artifact_review_source(record)
    return require_source_artifact_refs_authority(
        workspace_root,
        repository,
        _artifact_entries(record),
        require_current_use=require_current_use,
    )
