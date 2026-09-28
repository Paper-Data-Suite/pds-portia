"""Read-only recovery classification for deliberate-export custody."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.deliberate_export_operations import (
    deliberate_export_immutable_plan,
    planned_deliberate_export_commit_revision,
    validate_deliberate_export_candidate_reconciliation,
    validate_deliberate_export_committed_reference,
    validate_deliberate_export_journal,
)
from portia.storage.errors import (
    PortiaNotFoundError,
    PortiaPathError,
    PortiaStorageError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes, read_json
from portia.storage.paths import operation_revision_path, resolve_workspace_relative
from portia.storage.series import OperationJournalStore
from portia.storage.staging import ensure_runtime_containment


@dataclass(frozen=True, slots=True)
class ExportRepresentationObservation:
    """Exact observation of one final deliberate-export representation."""

    role: str
    relative_path: str
    disposition: str
    fingerprint: ContentFingerprint | None


@dataclass(frozen=True, slots=True)
class DeliberateExportRecoveryAssessment:
    """Privacy-minimized, non-mutating classification of one export operation."""

    operation_id: str
    export_id: str | None
    disposition: str
    journal_state: str | None
    selected_revision: int | None
    planned_committed_revision: int | None
    series_disposition: str
    artifact: ExportRepresentationObservation | None
    provenance: ExportRepresentationObservation | None


def _export_id(journal: PortiaRecord) -> str:
    data = journal.to_dict()
    target = data.get("primary_target")
    if not isinstance(target, dict):
        raise ValueError("deliberate-export journal primary target is not an object")
    export_ref = target.get("export_ref")
    if not isinstance(export_ref, dict):
        raise ValueError("deliberate-export target lacks export_ref")
    export_id = export_ref.get("export_id")
    if not isinstance(export_id, str):
        raise ValueError("deliberate-export target lacks export_id")
    return export_id


def _step_for_role(journal: PortiaRecord, role: str) -> dict[str, object]:
    raw = journal.to_dict().get("write_set")
    if not isinstance(raw, list):
        raise ValueError("deliberate-export journal write_set is not an array")
    matches = [
        step
        for step in raw
        if isinstance(step, dict) and step.get("representation_role") == role
    ]
    if len(matches) != 1:
        raise ValueError(f"deliberate-export journal requires one {role} step")
    return dict(matches[0])


def _intended_fingerprint(step: dict[str, object]) -> ContentFingerprint:
    intended = step.get("intended_result")
    if not isinstance(intended, dict):
        raise ValueError("deliberate-export step lacks intended_result")
    return ContentFingerprint.from_dict(intended.get("fingerprint"))


def _observe(
    root: Path,
    journal: PortiaRecord,
    role: str,
) -> ExportRepresentationObservation:
    step = _step_for_role(journal, role)
    relative = step.get("destination_path")
    if not isinstance(relative, str):
        raise ValueError("deliberate-export destination is not a string")
    intended = _intended_fingerprint(step)
    try:
        path = resolve_workspace_relative(root, relative)
        ensure_runtime_containment(root, path)
        content = read_bytes(path)
    except PortiaNotFoundError:
        return ExportRepresentationObservation(role, relative, "absent", None)
    except (PortiaPathError, PortiaStorageError, OSError, RuntimeError):
        return ExportRepresentationObservation(role, relative, "indeterminate", None)

    actual = fingerprint_bytes(content)
    disposition = "exact" if actual == intended else "mismatch"
    return ExportRepresentationObservation(role, relative, disposition, actual)


def _load_exact_export(
    root: Path,
    journal: PortiaRecord,
    provenance: ExportRepresentationObservation,
) -> PortiaRecord | None:
    if provenance.disposition != "exact":
        return None
    try:
        path = resolve_workspace_relative(root, provenance.relative_path)
        ensure_runtime_containment(root, path)
        raw, _content, _fingerprint = read_json(path)
        record = parse_portia_record("deliberate_export", "1", raw)
        validate_deliberate_export_candidate_reconciliation(journal, record)
        return record
    except Exception:
        return None


def _load_committed_revision(
    root: Path,
    operation_id: str,
    revision: int,
) -> tuple[str, PortiaRecord | None]:
    path = operation_revision_path(root, operation_id, revision)
    try:
        raw, _content, _fingerprint = read_json(path)
    except PortiaNotFoundError:
        return "missing", None
    except Exception:
        return "indeterminate", None
    try:
        record = parse_portia_record("operation_journal", "4", raw)
        validate_deliberate_export_journal(record)
    except Exception:
        return "indeterminate", None
    return "present", record


class DeliberateExportRecovery:
    """Inspect exact durable export state without mutating any representation."""

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).resolve(strict=False)
        self.store = OperationJournalStore(self.root)

    def assess(self, operation_id: str) -> DeliberateExportRecoveryAssessment:
        series = self.store.inspect_recovery(operation_id)
        if series.disposition in {"absent", "pointer_missing_manual_recovery"}:
            return DeliberateExportRecoveryAssessment(
                operation_id=operation_id,
                export_id=None,
                disposition="indeterminate",
                journal_state=None,
                selected_revision=series.selected_revision,
                planned_committed_revision=None,
                series_disposition=series.disposition,
                artifact=None,
                provenance=None,
            )

        try:
            current = self.store.load_current(operation_id)
            journal = current.revision
            if (
                journal.contract != "operation_journal"
                or journal.contract_version != "4"
                or journal.to_dict().get("operation_kind")
                != "generate_deliberate_export"
            ):
                raise ValueError("operation is not a deliberate-export v4 series")
            validate_deliberate_export_journal(journal)
            export_id = _export_id(journal)
            planned_revision = planned_deliberate_export_commit_revision(journal)
        except Exception:
            return DeliberateExportRecoveryAssessment(
                operation_id=operation_id,
                export_id=None,
                disposition="indeterminate",
                journal_state=None,
                selected_revision=series.selected_revision,
                planned_committed_revision=None,
                series_disposition=series.disposition,
                artifact=None,
                provenance=None,
            )

        data = journal.to_dict()
        state_value = data.get("state")
        state = state_value if isinstance(state_value, str) else None
        selected_value = data.get("journal_revision")
        selected = (
            selected_value
            if isinstance(selected_value, int) and not isinstance(selected_value, bool)
            else None
        )

        artifact = _observe(self.root, journal, "deliberate_export_artifact")
        provenance = _observe(self.root, journal, "deliberate_export_provenance")

        pair = (artifact.disposition, provenance.disposition)
        if "indeterminate" in pair:
            disposition = "indeterminate"
        elif pair == ("absent", "absent"):
            disposition = "nothing_durable"
        elif pair == ("exact", "absent"):
            disposition = "artifact_only"
        elif pair == ("mismatch", "absent"):
            disposition = "artifact_mismatch"
        elif pair == ("absent", "exact"):
            disposition = "provenance_only"
        elif pair[0] in {"exact", "mismatch"} and pair[1] in {"exact", "mismatch"}:
            if pair != ("exact", "exact"):
                disposition = "artifact_provenance_mismatch"
            else:
                export = _load_exact_export(self.root, journal, provenance)
                if export is None:
                    disposition = "indeterminate"
                else:
                    committed_status, committed = _load_committed_revision(
                        self.root,
                        operation_id,
                        planned_revision,
                    )
                    if committed_status == "missing":
                        disposition = "exact_both_committed_journal_missing"
                    elif committed_status != "present" or committed is None:
                        disposition = "indeterminate"
                    else:
                        try:
                            if (
                                deliberate_export_immutable_plan(committed)
                                != deliberate_export_immutable_plan(journal)
                            ):
                                raise ValueError("journal immutable plan differs")
                            validate_deliberate_export_committed_reference(
                                committed,
                                export,
                            )
                            if (
                                state == "completed"
                                and selected is not None
                                and selected > planned_revision
                            ):
                                validate_deliberate_export_candidate_reconciliation(
                                    journal,
                                    export,
                                )
                                disposition = "completed"
                            else:
                                disposition = "committed"
                        except Exception:
                            disposition = "indeterminate"
        else:
            disposition = "indeterminate"

        return DeliberateExportRecoveryAssessment(
            operation_id=operation_id,
            export_id=export_id,
            disposition=disposition,
            journal_state=state,
            selected_revision=selected,
            planned_committed_revision=planned_revision,
            series_disposition=series.disposition,
            artifact=artifact,
            provenance=provenance,
        )
