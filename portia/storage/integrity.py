"""Deterministic persistence-level integrity evaluation for Portia durable state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from portia.models import PortiaRecord, parse_portia_record
from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaNotFoundError, PortiaPathError
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import read_bytes, read_json
from portia.storage.operation_journal import (
    AbsenceStepView,
    absence_step_view,
    is_absence_step,
    validate_operation_journal_application,
)
from portia.storage.paths import (
    actor_child_path,
    actor_directory_removal_path,
    actor_record_path,
    resolve_workspace_relative,
    work_manifest_path,
    work_record_path,
    workspace_relative,
)
from portia.storage.staging import ensure_runtime_containment


@dataclass(frozen=True, slots=True, order=True)
class PersistenceFinding:
    """Privacy-minimized diagnostic about persisted operational evidence."""

    code: str
    relative_path: str
    detail: str


@dataclass(frozen=True, slots=True, order=True)
class OperationStepEvidence:
    """Exact durable observation for one journaled canonical write step."""

    step_id: str
    disposition: str
    relative_path: str
    fingerprint: ContentFingerprint | None


def _fingerprint(value: object) -> ContentFingerprint | None:
    if value is None:
        return None
    try:
        return ContentFingerprint.from_dict(value)
    except ValueError:
        return None


def _work_ref(value: object) -> ExactPortiaWorkRef | None:
    if not isinstance(value, dict):
        return None
    try:
        return ExactPortiaWorkRef(
            class_id=str(value["class_id"]),
            work_id=str(value["work_id"]),
            work_kind=str(value["work_kind"]),
            contract_version=str(value["contract_version"]),
            module_id=str(value.get("module_id", "portia")),
        )
    except (KeyError, ValueError, TypeError):
        return None


def expected_target_relative_path(root: str | Path, target: object) -> str | None:
    """Return an exact canonical path for target branches whose storage is #38-owned."""
    if not isinstance(target, dict):
        return None
    kind = target.get("kind")
    workspace = Path(root).resolve(strict=False)

    if kind == "work":
        work = _work_ref(target.get("work_ref"))
        if work is None:
            return None
        return workspace_relative(workspace, work_manifest_path(workspace, work))

    if kind == "work_record":
        composite = target.get("work_record_ref")
        if not isinstance(composite, dict):
            return None
        work = _work_ref(composite.get("work_ref"))
        record_ref = composite.get("record_ref")
        if work is None or not isinstance(record_ref, dict):
            return None
        record_kind = record_ref.get("record_kind")
        record_id = record_ref.get("record_id")
        if not isinstance(record_kind, str) or not isinstance(record_id, str):
            return None
        return workspace_relative(
            workspace,
            work_record_path(workspace, work, record_kind, record_id),
        )

    if kind == "actor_directory_record":
        reference = target.get("actor_directory_record_ref")
        if not isinstance(reference, dict):
            return None
        record_kind = reference.get("kind")
        if record_kind == "actor":
            actor_ref = reference.get("actor_ref")
            if not isinstance(actor_ref, dict):
                return None
            actor_id = actor_ref.get("actor_id")
            if not isinstance(actor_id, str):
                return None
            return workspace_relative(workspace, actor_record_path(workspace, actor_id))

        reference_field = {
            "actor_contact_point": "contact_point_ref",
            "actor_student_relationship": "relationship_ref",
            "actor_roster_student_collision": "collision_ref",
        }.get(str(record_kind))
        id_field = {
            "actor_contact_point": "contact_point_id",
            "actor_student_relationship": "relationship_id",
            "actor_roster_student_collision": "collision_id",
        }.get(str(record_kind))
        if reference_field is None or id_field is None:
            return None
        child_ref = reference.get(reference_field)
        if not isinstance(child_ref, dict):
            return None
        actor_id = child_ref.get("actor_id")
        record_id = child_ref.get(id_field)
        if not isinstance(actor_id, str) or not isinstance(record_id, str):
            return None
        return workspace_relative(
            workspace,
            actor_child_path(workspace, actor_id, str(record_kind), record_id),
        )

    if kind == "actor_directory_removal":
        removal_ref = target.get("removal_ref")
        if not isinstance(removal_ref, dict):
            return None
        removal_id = removal_ref.get("removal_id")
        if not isinstance(removal_id, str):
            return None
        return workspace_relative(
            workspace,
            actor_directory_removal_path(workspace, removal_id),
        )

    return None


def _removal_certificate_findings(
    root: Path,
    *,
    journal_data: Mapping[str, Any],
    step: Mapping[str, Any],
    view: AbsenceStepView,
) -> tuple[bool, tuple[PersistenceFinding, ...]]:
    """Resolve and validate the exact certificate linked by an absence step."""
    relative = view.certificate_path
    try:
        path = resolve_workspace_relative(root, relative)
        ensure_runtime_containment(root, path)
    except PortiaPathError:
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH",
                relative,
                "removal certificate path is not safely contained in the workspace",
            ),
        )
    try:
        raw, _content, actual_fp = read_json(path)
    except Exception:
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISSING",
                relative,
                "exact journal-linked removal certificate is unavailable",
            ),
        )
    if actual_fp != view.certificate_fingerprint:
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH",
                relative,
                "removal certificate bytes differ from the journal-linked fingerprint",
            ),
        )

    ref = view.removal_ref
    contract_version = ref.get("contract_version")
    if not isinstance(contract_version, str):
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH",
                relative,
                "removal certificate reference has no exact contract version",
            ),
        )
    is_actor = "class_id" not in ref
    contract = (
        "actor_directory_exceptional_removal" if is_actor else "exceptional_removal"
    )
    try:
        certificate = parse_portia_record(contract, contract_version, raw)
    except Exception:
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH",
                relative,
                "journal-linked removal certificate is not a valid exact record",
            ),
        )
    data = certificate.to_dict()
    identity_matches = (
        data.get("module_id") == ref.get("module_id")
        and data.get("removal_id") == ref.get("removal_id")
        and (is_actor or data.get("class_id") == ref.get("class_id"))
    )
    target = step.get("target")
    if is_actor:
        target_matches = (
            isinstance(target, Mapping)
            and target.get("kind") == "actor_directory_record"
            and data.get("target") == target.get("actor_directory_record_ref")
        )
        expected_certificate_path = workspace_relative(
            root,
            actor_directory_removal_path(root, str(ref.get("removal_id"))),
        )
        evidence_matches = (
            data.get("original_workspace_relative_path") == view.destination_path
            and data.get("original_contract_version") == view.prior_contract_version
            and data.get("original_fingerprint") == view.prior_fingerprint.digest
            and data.get("original_byte_length") == view.prior_fingerprint.byte_length
            and relative == expected_certificate_path
        )
        operation_ref = data.get("operation_ref")
        operation_matches = (
            isinstance(operation_ref, Mapping)
            and operation_ref.get("operation_id") == journal_data.get("operation_id")
            and operation_ref.get("contract_version") == "3"
            and isinstance(operation_ref.get("journal_revision"), int)
            and not isinstance(operation_ref.get("journal_revision"), bool)
            and operation_ref.get("journal_revision")
            <= journal_data.get("journal_revision", -1)
        )
    else:
        target_matches = data.get("target") == target
        content_evidence = data.get("content_evidence")
        evidence_matches = (
            isinstance(content_evidence, Mapping)
            and content_evidence.get("kind") == "salted_sha256"
            and content_evidence.get("byte_length") == view.prior_fingerprint.byte_length
        )
        operation_matches = True
    if not identity_matches or not target_matches or not evidence_matches or not operation_matches:
        return False, (
            PersistenceFinding(
                "PORTIA.STORAGE.REMOVAL_CERTIFICATE_MISMATCH",
                relative,
                "removal certificate identity, target, operation, or prior-content evidence disagrees with the absence step",
            ),
        )
    return True, ()


def validate_operation_durable_state(
    workspace_root: str | Path,
    journal: PortiaRecord,
) -> tuple[PersistenceFinding, ...]:
    """Reconcile durable/accepted journal evidence with exact filesystem bytes."""
    if journal.contract != "operation_journal" or journal.contract_version not in {"2", "3"}:
        raise ValueError("journal must be operation_journal@2 or operation_journal@3")
    root = Path(workspace_root).resolve(strict=False)
    data = journal.to_dict()
    findings: list[PersistenceFinding] = []
    try:
        validate_operation_journal_application(journal)
    except Exception:
        return (
            PersistenceFinding(
                "PORTIA.STORAGE.OPERATION_WRITE_SET_INVALID",
                "portia/operations",
                "operation journal violates version-aware write semantics",
            ),
        )

    write_set = data.get("write_set")
    if not isinstance(write_set, list):
        return (
            PersistenceFinding(
                "PORTIA.STORAGE.OPERATION_WRITE_SET_INVALID",
                "portia/operations",
                "operation journal write_set is unavailable",
            ),
        )

    for step in write_set:
        if not isinstance(step, dict):
            continue
        relative = step.get("destination_path")
        if not isinstance(relative, str):
            continue
        try:
            destination = resolve_workspace_relative(root, relative)
            ensure_runtime_containment(root, destination)
        except PortiaPathError:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.UNSAFE_OPERATION_PATH",
                    relative,
                    "journaled destination path is not safely contained in the workspace",
                )
            )
            continue

        expected_relative = expected_target_relative_path(root, step.get("target"))
        if expected_relative is not None and expected_relative != relative:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.CANONICAL_PATH_OWNER_MISMATCH",
                    relative,
                    "journaled target identity does not agree with destination path",
                )
            )

        disposition = step.get("disposition")
        if is_absence_step(step):
            view = absence_step_view(step)
            certificate_valid, certificate_findings = _removal_certificate_findings(
                root,
                journal_data=data,
                step=step,
                view=view,
            )
            try:
                actual = fingerprint_bytes(read_bytes(destination))
            except PortiaNotFoundError:
                actual = None
            except Exception:
                findings.extend(certificate_findings)
                findings.append(
                    PersistenceFinding(
                        "PORTIA.STORAGE.UNEXPLAINED_CANONICAL_ABSENCE",
                        relative,
                        "canonical removal target could not be read safely",
                    )
                )
                continue
            if disposition in {"durable", "verified", "accepted"}:
                findings.extend(certificate_findings)
                if actual is not None:
                    code = (
                        "PORTIA.STORAGE.REMOVAL_TARGET_RETAINED"
                        if actual == view.prior_fingerprint
                        else "PORTIA.STORAGE.REMOVAL_TARGET_CHANGED"
                    )
                    detail = (
                        "journal reports accepted absence but the exact prior payload remains"
                        if actual == view.prior_fingerprint
                        else "canonical removal target changed after its exact preflight fingerprint"
                    )
                    findings.append(PersistenceFinding(code, relative, detail))
                elif not view.observed_absent:
                    findings.append(
                        PersistenceFinding(
                            "PORTIA.STORAGE.UNEXPLAINED_CANONICAL_ABSENCE",
                            relative,
                            "payload is absent without matching journaled absence observation",
                        )
                    )
            elif actual is None and not certificate_valid:
                findings.extend(certificate_findings)
                findings.append(
                    PersistenceFinding(
                        "PORTIA.STORAGE.UNEXPLAINED_CANONICAL_ABSENCE",
                        relative,
                        "payload became absent before durable certificate-backed removal evidence",
                    )
                )
            elif actual is not None and actual != view.prior_fingerprint:
                findings.append(
                    PersistenceFinding(
                        "PORTIA.STORAGE.REMOVAL_TARGET_CHANGED",
                        relative,
                        "canonical removal target changed after its exact preflight fingerprint",
                    )
                )
            continue

        if disposition not in {"durable", "verified", "accepted"}:
            continue
        intended_result = step.get("intended_result")
        intended_fp = (
            _fingerprint(intended_result.get("fingerprint"))
            if isinstance(intended_result, dict)
            else None
        )
        observed_result = step.get("observed_result")
        observed_fp = (
            _fingerprint(observed_result.get("fingerprint"))
            if isinstance(observed_result, dict)
            else None
        )

        try:
            actual = fingerprint_bytes(read_bytes(destination))
        except Exception:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.DURABLE_RESULT_MISSING",
                    relative,
                    "journal reports durable state but destination bytes are unavailable",
                )
            )
            continue

        if intended_fp is not None and actual != intended_fp:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.INTENDED_RESULT_MISMATCH",
                    relative,
                    "persisted bytes do not match the journaled intended fingerprint",
                )
            )
        if observed_fp is not None and actual != observed_fp:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.READBACK_RESULT_MISMATCH",
                    relative,
                    "persisted bytes do not match the journaled observed fingerprint",
                )
            )

    return tuple(sorted(findings))


def observe_operation_durable_state(
    workspace_root: str | Path,
    journal: PortiaRecord,
) -> tuple[OperationStepEvidence, ...]:
    """Classify actual bytes without changing journal or canonical state.

    The classification deliberately uses the exact intended and prior
    fingerprints in the selected journal.  It never treats existence, age, or
    revision order as proof that a write was accepted.
    """
    if journal.contract != "operation_journal" or journal.contract_version not in {"2", "3"}:
        raise ValueError("journal must be operation_journal@2 or operation_journal@3")
    root = Path(workspace_root).resolve(strict=False)
    data = journal.to_dict()
    validate_operation_journal_application(journal)
    raw_steps = data.get("write_set")
    if not isinstance(raw_steps, list):
        return ()

    evidence: list[OperationStepEvidence] = []
    for raw in raw_steps:
        if not isinstance(raw, dict) or raw.get("phase") != "canonical_gate":
            continue
        step_id = raw.get("step_id")
        relative = raw.get("destination_path")
        intended_raw = raw.get("intended_result")
        if (
            not isinstance(step_id, str)
            or not isinstance(relative, str)
            or not isinstance(intended_raw, dict)
        ):
            continue
        if is_absence_step(raw):
            view = absence_step_view(raw)
            certificate_valid, _certificate_findings = _removal_certificate_findings(
                root,
                journal_data=data,
                step=raw,
                view=view,
            )
            try:
                destination = resolve_workspace_relative(root, relative)
                ensure_runtime_containment(root, destination)
                actual = fingerprint_bytes(read_bytes(destination))
            except PortiaNotFoundError:
                actual = None
            except Exception:
                evidence.append(
                    OperationStepEvidence(step_id, "indeterminate", relative, None)
                )
                continue
            journaled = raw.get("disposition")
            if actual is None and certificate_valid:
                if journaled == "accepted":
                    disposition = "accepted"
                elif journaled == "verified":
                    disposition = "verified"
                else:
                    disposition = "durable_unverified"
            elif actual == view.prior_fingerprint and journaled in {"pending", "staged"}:
                disposition = "not_written"
            else:
                disposition = "indeterminate"
            evidence.append(
                OperationStepEvidence(step_id, disposition, relative, actual)
            )
            continue
        intended = _fingerprint(intended_raw.get("fingerprint"))
        precondition = raw.get("precondition")
        prior = (
            _fingerprint(precondition.get("fingerprint"))
            if isinstance(precondition, dict)
            else None
        )
        try:
            destination = resolve_workspace_relative(root, relative)
            ensure_runtime_containment(root, destination)
            actual = fingerprint_bytes(read_bytes(destination))
        except PortiaNotFoundError:
            actual = None
        except Exception:
            evidence.append(
                OperationStepEvidence(step_id, "indeterminate", relative, None)
            )
            continue

        journaled = raw.get("disposition")
        if actual is not None and intended is not None and actual == intended:
            if journaled == "accepted":
                disposition = "accepted"
            elif journaled == "verified":
                disposition = "verified"
            else:
                disposition = "durable_unverified"
        elif actual is None and isinstance(precondition, dict) and precondition.get(
            "presence"
        ) == "must_be_absent":
            disposition = "not_written"
        elif actual is not None and prior is not None and actual == prior:
            disposition = "not_written"
        else:
            disposition = "indeterminate"
        evidence.append(
            OperationStepEvidence(step_id, disposition, relative, actual)
        )
    return tuple(evidence)


def source_snapshot_digest(snapshot: PortiaRecord | dict[str, Any]) -> str:
    """Recompute the accepted ``portia_source_snapshot_v1`` logical digest."""
    data = snapshot.to_dict() if isinstance(snapshot, PortiaRecord) else dict(snapshot)
    digest_value = {
        "snapshot_algorithm": data.get("snapshot_algorithm"),
        "projection_kind": data.get("projection_kind"),
        "projection_scope": data.get("projection_scope"),
        "authorization_scope": data.get("authorization_scope"),
        "discovery_roots": data.get("discovery_roots"),
        "source_contracts": data.get("source_contracts"),
        "entries": data.get("entries"),
    }
    encoded = json.dumps(
        digest_value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_contract_sort_key(value: object) -> tuple[str, str]:
    if not isinstance(value, dict):
        return ("", "")
    return (str(value.get("contract_name", "")), str(value.get("contract_version", "")))


def _source_entry_sort_key(value: object) -> tuple[str, str, str, str, int]:
    if not isinstance(value, dict):
        return ("", "", "", "", -1)
    length = value.get("byte_length")
    return (
        str(value.get("workspace_relative_path", "")),
        str(value.get("source_role", "")),
        str(value.get("contract_or_artifact_kind", "")),
        str(value.get("sha256_digest", "")),
        length if isinstance(length, int) and not isinstance(length, bool) else -1,
    )


def validate_source_snapshot(
    workspace_root: str | Path,
    snapshot: PortiaRecord,
) -> tuple[PersistenceFinding, ...]:
    """Verify Source Snapshot v1 logical digest, ordering, and exact source bytes."""
    if snapshot.contract != "source_snapshot" or snapshot.contract_version != "1":
        raise ValueError("snapshot must be source_snapshot@1")
    root = Path(workspace_root).resolve(strict=False)
    data = snapshot.to_dict()
    entries = data.get("entries")
    contracts = data.get("source_contracts")
    findings: list[PersistenceFinding] = []

    recorded_digest = data.get("source_snapshot_digest")
    if not isinstance(recorded_digest, str) or source_snapshot_digest(snapshot) != recorded_digest:
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_SNAPSHOT_DIGEST_MISMATCH",
                "portia/derived",
                "source snapshot logical digest does not match its recorded digest",
            )
        )

    if isinstance(contracts, list) and contracts != sorted(contracts, key=_source_contract_sort_key):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_CONTRACT_ORDER_INVALID",
                "portia/derived",
                "source contracts are not in deterministic order",
            )
        )

    if not isinstance(entries, list):
        return tuple(sorted(findings))
    if entries != sorted(entries, key=_source_entry_sort_key):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_ENTRY_ORDER_INVALID",
                "portia/derived",
                "source snapshot entries are not in deterministic order",
            )
        )
    paths = [
        entry.get("workspace_relative_path")
        for entry in entries
        if isinstance(entry, dict)
    ]
    if len(paths) != len(set(paths)):
        findings.append(
            PersistenceFinding(
                "PORTIA.STORAGE.SOURCE_PATH_DUPLICATE",
                "portia/derived",
                "source snapshot contains duplicate workspace-relative paths",
            )
        )

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        relative = entry.get("workspace_relative_path")
        digest = entry.get("sha256_digest")
        byte_length = entry.get("byte_length")
        if not isinstance(relative, str):
            continue
        try:
            path = resolve_workspace_relative(root, relative)
            ensure_runtime_containment(root, path)
        except PortiaPathError:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_PATH_UNSAFE",
                    relative,
                    "source snapshot path is not safely contained in the workspace",
                )
            )
            continue
        try:
            actual = fingerprint_bytes(read_bytes(path))
        except Exception:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_SNAPSHOT_MISSING",
                    relative,
                    "source snapshot entry no longer resolves to persisted bytes",
                )
            )
            continue
        if actual.digest != digest or actual.byte_length != byte_length:
            findings.append(
                PersistenceFinding(
                    "PORTIA.STORAGE.SOURCE_SNAPSHOT_STALE",
                    relative,
                    "source bytes changed after the recorded source snapshot",
                )
            )
    return tuple(sorted(findings))
