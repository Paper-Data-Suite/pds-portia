"""Read-only immutable teacher-reference export history and verification."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from portia.exports.policy import TEACHER_REFERENCE_EXPORT_PURPOSES
from portia.models import ExplicitOffsetTimestamp, PortiaRecord, parse_portia_record
from portia.models.errors import PortiaLocalValidationError
from portia.models.identifiers import validate_portia_id
from portia.models.references import ExactPortiaWorkRef
from portia.storage import PortiaNotFoundError, PortiaStorageError, fingerprint_bytes
from portia.storage.deliberate_export_operations import (
    validate_deliberate_export_committed_reference,
)
from portia.storage.deliberate_export_recovery import DeliberateExportRecovery
from portia.storage.fingerprint import canonical_json_bytes
from portia.storage.io import read_bytes, read_json
from portia.storage.paths import operation_revision_path, resolve_workspace_relative
from portia.storage.staging import ensure_runtime_containment

TeacherReferenceHistoryVerification = Literal[
    "available_verified",
    "artifact_missing",
    "artifact_mismatch",
    "operation_recovery_required",
    "provenance_invalid",
]


@dataclass(frozen=True, slots=True)
class TeacherReferenceExportHistoryEntry:
    """Bounded teacher-facing view of one immutable export provenance record."""

    export_id: str
    generated_at: str | None
    projection_purpose: str | None
    artifact_format: str | None
    focal_participant: bool | None
    artifact_relative_path: str | None
    verification_status: TeacherReferenceHistoryVerification
    operation_id: str | None

    def __post_init__(self) -> None:
        validate_portia_id(self.export_id, "pexp_", "history_export_id")
        if self.generated_at is not None:
            ExplicitOffsetTimestamp(self.generated_at)
        if self.projection_purpose is not None and (
            self.projection_purpose not in TEACHER_REFERENCE_EXPORT_PURPOSES
        ):
            raise PortiaLocalValidationError(
                "teacher-reference history contains unsupported projection purpose"
            )
        if (
            self.focal_participant is True
            and self.projection_purpose != "participant_specific"
        ):
            raise PortiaLocalValidationError(
                "teacher-reference focal history indicator requires "
                "participant-specific purpose"
            )


class TeacherReferenceExportHistoryService:
    """Enumerate and verify accepted teacher-reference exports for one exact work."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).resolve(strict=False)
        self.exports_root = self.root / "portia" / "exports"

    def list_for_work(
        self,
        work_ref: ExactPortiaWorkRef,
    ) -> tuple[TeacherReferenceExportHistoryEntry, ...]:
        if not isinstance(work_ref, ExactPortiaWorkRef):
            raise TypeError("work_ref must be an ExactPortiaWorkRef")
        if not self.exports_root.exists():
            return ()
        ensure_runtime_containment(self.root, self.exports_root)
        if not self.exports_root.is_dir():
            raise PortiaLocalValidationError(
                "teacher-reference export history root is not a directory"
            )

        entries: list[TeacherReferenceExportHistoryEntry] = []
        for child in sorted(self.exports_root.iterdir(), key=lambda path: path.name):
            if not child.is_dir() or child.is_symlink():
                raise PortiaLocalValidationError(
                    "unexpected artifact in teacher-reference export history root"
                )
            export_id = validate_portia_id(child.name, "pexp_", "history_export_id")
            provenance_path = child / "export.json"
            try:
                raw, content, _fingerprint = read_json(provenance_path)
            except PortiaNotFoundError:
                continue
            except PortiaStorageError:
                continue

            if not _raw_matches_work(raw, export_id, work_ref):
                continue
            try:
                export = parse_portia_record("deliberate_export", "1", raw)
            except Exception:
                entries.append(_invalid_entry(export_id, raw))
                continue
            data = export.to_dict()
            if not _is_supported_teacher_reference(data):
                continue
            if content != canonical_json_bytes(data):
                entries.append(_entry(export, "provenance_invalid"))
                continue
            entries.append(_entry(export, self._verification(export)))

        return tuple(sorted(entries, key=_history_sort_key))

    def _verification(
        self,
        export: PortiaRecord,
    ) -> TeacherReferenceHistoryVerification:
        data = export.to_dict()
        export_id = data.get("export_id")
        output = data.get("output")
        if not isinstance(export_id, str) or not isinstance(output, Mapping):
            return "provenance_invalid"
        expected_path = f"portia/exports/{export_id}/artifact.html"
        relative = output.get("workspace_relative_path")
        expected_length = output.get("byte_length")
        expected_digest = output.get("sha256_digest")
        if (
            output.get("format") != "html"
            or output.get("media_type") != "text/html"
            or relative != expected_path
            or not isinstance(expected_length, int)
            or isinstance(expected_length, bool)
            or not isinstance(expected_digest, str)
        ):
            return "provenance_invalid"

        try:
            artifact_path = resolve_workspace_relative(self.root, relative)
            ensure_runtime_containment(self.root, artifact_path)
            artifact = read_bytes(artifact_path)
        except PortiaNotFoundError:
            return "artifact_missing"
        except PortiaStorageError:
            return "provenance_invalid"
        artifact_fp = fingerprint_bytes(artifact)
        if (
            artifact_fp.byte_length != expected_length
            or artifact_fp.digest != expected_digest
        ):
            return "artifact_mismatch"

        journal_ref = data.get("operation_journal_ref")
        if not isinstance(journal_ref, Mapping):
            return "provenance_invalid"
        operation_id = journal_ref.get("operation_id")
        revision = journal_ref.get("journal_revision")
        contract_version = journal_ref.get("contract_version")
        if (
            not isinstance(operation_id, str)
            or not isinstance(revision, int)
            or isinstance(revision, bool)
            or contract_version != "4"
        ):
            return "provenance_invalid"
        try:
            raw, _content, _fingerprint = read_json(
                operation_revision_path(self.root, operation_id, revision)
            )
        except PortiaNotFoundError:
            return "operation_recovery_required"
        except PortiaStorageError:
            return "provenance_invalid"
        try:
            committed = parse_portia_record("operation_journal", "4", raw)
            validate_deliberate_export_committed_reference(committed, export)
        except Exception:
            return "provenance_invalid"

        assessment = DeliberateExportRecovery(self.root).assess(operation_id)
        if assessment.disposition != "completed":
            return "operation_recovery_required"
        return "available_verified"


def _raw_matches_work(
    raw: object,
    export_id: str,
    work_ref: ExactPortiaWorkRef,
) -> bool:
    if not isinstance(raw, Mapping) or raw.get("export_id") != export_id:
        return False
    scope = raw.get("export_scope")
    return (
        isinstance(scope, Mapping)
        and scope.get("scope") == "work"
        and scope.get("work_ref") == work_ref.to_dict()
    )


def _is_supported_teacher_reference(data: Mapping[str, object]) -> bool:
    purpose = data.get("projection_purpose")
    output = data.get("output")
    return (
        isinstance(purpose, str)
        and purpose in TEACHER_REFERENCE_EXPORT_PURPOSES
        and isinstance(output, Mapping)
        and output.get("format") == "html"
        and output.get("media_type") == "text/html"
    )


def _entry(
    export: PortiaRecord,
    status: TeacherReferenceHistoryVerification,
) -> TeacherReferenceExportHistoryEntry:
    data = export.to_dict()
    output = data.get("output")
    journal_ref = data.get("operation_journal_ref")
    purpose = data.get("projection_purpose")
    generated_at = data.get("generated_at")
    return TeacherReferenceExportHistoryEntry(
        export_id=str(data["export_id"]),
        generated_at=(generated_at if isinstance(generated_at, str) else None),
        projection_purpose=(purpose if isinstance(purpose, str) else None),
        artifact_format=(
            str(output.get("format")) if isinstance(output, Mapping) else None
        ),
        focal_participant=(purpose == "participant_specific"),
        artifact_relative_path=(
            str(output.get("workspace_relative_path"))
            if isinstance(output, Mapping)
            and isinstance(output.get("workspace_relative_path"), str)
            else None
        ),
        verification_status=status,
        operation_id=(
            str(journal_ref.get("operation_id"))
            if isinstance(journal_ref, Mapping)
            and isinstance(journal_ref.get("operation_id"), str)
            else None
        ),
    )


def _invalid_entry(
    export_id: str,
    raw: object,
) -> TeacherReferenceExportHistoryEntry:
    generated_at: str | None = None
    if isinstance(raw, Mapping):
        candidate = raw.get("generated_at")
        if isinstance(candidate, str):
            try:
                ExplicitOffsetTimestamp(candidate)
                generated_at = candidate
            except (TypeError, ValueError, PortiaLocalValidationError):
                generated_at = None
    return TeacherReferenceExportHistoryEntry(
        export_id=export_id,
        generated_at=generated_at,
        projection_purpose=None,
        artifact_format=None,
        focal_participant=None,
        artifact_relative_path=None,
        verification_status="provenance_invalid",
        operation_id=None,
    )


def _history_sort_key(entry: TeacherReferenceExportHistoryEntry) -> tuple[float, str]:
    if entry.generated_at is None:
        return (float("inf"), entry.export_id)
    timestamp = ExplicitOffsetTimestamp(entry.generated_at).datetime.timestamp()
    return (-timestamp, entry.export_id)


__all__ = [
    "TeacherReferenceExportHistoryEntry",
    "TeacherReferenceExportHistoryService",
    "TeacherReferenceHistoryVerification",
]
