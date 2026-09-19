"""Capability-guarded removal of one exact accepted canonical representation."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from portia.models import PortiaRecord, parse_portia_record
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaPathError,
    PortiaRecoveryRequiredError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.integrity import expected_target_relative_path
from portia.storage.io import exact_delete, read_bytes, read_json
from portia.storage.operation_journal import absence_step_view
from portia.storage.paths import (
    actor_directory_removal_path,
    exceptional_removal_path,
    resolve_workspace_relative,
    workspace_relative,
)
from portia.storage.quarantine import quarantine_applies
from portia.storage.series import OperationJournalStore, QuarantineStore
from portia.storage.staging import ensure_runtime_containment

Clock = Callable[[], str]
_CAPABILITY_MARKER = object()


@dataclass(frozen=True, slots=True)
class _ValidatedRemovalCapability:
    marker: object
    decision_reference: str
    authorized_by: Mapping[str, object]


def _issue_removal_capability(
    decision_reference: str,
    authorized_by: Mapping[str, object],
) -> _ValidatedRemovalCapability:
    """Issue the non-serializable marker after workflow authorization validation."""
    return _ValidatedRemovalCapability(
        _CAPABILITY_MARKER,
        decision_reference,
        dict(authorized_by),
    )


@dataclass(frozen=True, slots=True)
class CanonicalRemovalRequest:
    """Identity-only request; callers cannot supply a filesystem path."""

    target: Mapping[str, object]
    operation_id: str
    journal_revision: int
    step_id: str
    quarantine_id: str


@dataclass(frozen=True, slots=True)
class AbsenceObservation:
    """Minimal verified observation suitable for operation_journal@3."""

    workspace_relative_path: str
    observed_at: str
    already_absent: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": "absent",
            "workspace_relative_path": self.workspace_relative_path,
            "observed_at": self.observed_at,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _certificate_path(
    root: Path,
    removal_ref: Mapping[str, Any],
) -> tuple[str, Path]:
    removal_id = removal_ref.get("removal_id")
    if not isinstance(removal_id, str):
        raise PortiaCorruptionError("removal certificate reference lacks removal_id")
    class_id = removal_ref.get("class_id")
    if isinstance(class_id, str):
        path = exceptional_removal_path(root, class_id, removal_id)
        return "exceptional_removal", path
    path = actor_directory_removal_path(root, removal_id)
    return "actor_directory_exceptional_removal", path


def _certificate_target(target: Mapping[str, object]) -> object:
    if target.get("kind") == "actor_directory_record":
        return target.get("actor_directory_record_ref")
    return dict(target)


def _validate_certificate_content(
    contract: str,
    certificate: PortiaRecord,
    target: Mapping[str, object],
    content: bytes,
    expected: ContentFingerprint,
) -> None:
    data = certificate.to_dict()
    if data.get("target") != _certificate_target(target):
        raise PortiaConflictError("removal certificate identifies another exact target")
    if contract == "actor_directory_exceptional_removal":
        if (
            data.get("original_fingerprint") != expected.digest
            or data.get("original_byte_length") != expected.byte_length
        ):
            raise PortiaConflictError(
                "Actor removal certificate differs from exact prior bytes"
            )
        return
    evidence = data.get("content_evidence")
    if not isinstance(evidence, Mapping) or evidence.get("kind") != "salted_sha256":
        raise PortiaConflictError(
            "ordinary canonical removal requires exact salted content evidence"
        )
    salt = evidence.get("salt")
    try:
        salt_bytes = base64.b64decode(str(salt), validate=True)
    except Exception as exc:
        raise PortiaCorruptionError("removal certificate salt is malformed") from exc
    digest = hashlib.sha256(salt_bytes + content).hexdigest()
    if evidence.get("digest") != digest or evidence.get("byte_length") != len(content):
        raise PortiaConflictError("removal certificate content evidence does not match")


def _validate_quarantine(
    root: Path,
    request: CanonicalRemovalRequest,
) -> None:
    current = QuarantineStore(root).load_current(request.quarantine_id)
    data = current.revision.to_dict()
    if data.get("state") != "active" or not quarantine_applies(
        data.get("target"), request.target
    ):
        raise PortiaRecoveryRequiredError(
            "canonical removal requires an exact active Quarantine"
        )
    effects = data.get("effects")
    if not isinstance(effects, list) or not {
        "block_current_use",
        "block_operation_completion",
    }.issubset(effects):
        raise PortiaRecoveryRequiredError(
            "canonical removal Quarantine lacks protective effects"
        )
    origin = data.get("origin")
    applying = origin.get("applying_operation") if isinstance(origin, Mapping) else None
    if not isinstance(applying, Mapping) or applying.get("operation_id") != request.operation_id:
        raise PortiaRecoveryRequiredError(
            "canonical removal Quarantine belongs to another operation"
        )


class CanonicalRemovalStore:
    """Lowest-level non-generic canonical absence primitive."""

    def __init__(self, root: str | Path, *, clock: Clock = _utc_now) -> None:
        self.root = Path(root).resolve(strict=False)
        self.clock = clock

    def remove(
        self,
        request: CanonicalRemovalRequest,
        *,
        capability: _ValidatedRemovalCapability,
    ) -> AbsenceObservation:
        if capability.marker is not _CAPABILITY_MARKER:
            raise PortiaConflictError("canonical removal capability is not validated")
        current = OperationJournalStore(self.root).load_current(request.operation_id)
        journal = current.revision
        data = journal.to_dict()
        if (
            journal.contract_version != "3"
            or data.get("operation_kind") != "exceptionally_remove"
            or data.get("journal_revision") != request.journal_revision
        ):
            raise PortiaConflictError(
                "canonical removal requires the exact selected v3 removal journal"
            )
        steps = data.get("write_set")
        if not isinstance(steps, list):
            raise PortiaCorruptionError("removal operation write_set is malformed")
        matches = [
            step
            for step in steps
            if isinstance(step, Mapping) and step.get("step_id") == request.step_id
        ]
        if len(matches) != 1 or matches[0].get("target") != dict(request.target):
            raise PortiaConflictError("canonical removal step does not own the exact target")
        step = matches[0]
        view = absence_step_view(step)
        certificate_contract, certificate_path = _certificate_path(
            self.root,
            view.removal_ref,
        )
        expected_certificate_relative = workspace_relative(self.root, certificate_path)
        if expected_certificate_relative != view.certificate_path:
            raise PortiaConflictError(
                "journal certificate path is not identity-derived"
            )
        ensure_runtime_containment(self.root, certificate_path)
        certificate_value, _certificate_bytes, certificate_fingerprint = read_json(
            certificate_path
        )
        if certificate_fingerprint != view.certificate_fingerprint:
            raise PortiaConflictError("removal certificate fingerprint changed")
        try:
            certificate = parse_portia_record(
                certificate_contract,
                "1",
                certificate_value,
            )
        except Exception as exc:
            raise PortiaCorruptionError("removal certificate is invalid") from exc
        certificate_data = certificate.to_dict()
        authorization = certificate_data.get("authorization")
        if (
            not isinstance(authorization, Mapping)
            or authorization.get("decision_reference") != capability.decision_reference
            or authorization.get("authorized_by") != dict(capability.authorized_by)
        ):
            raise PortiaConflictError(
                "removal certificate authorization differs from validated authority"
            )
        if certificate_contract == "actor_directory_exceptional_removal":
            operation_ref = certificate_data.get("operation_ref")
            if (
                not isinstance(operation_ref, Mapping)
                or operation_ref.get("operation_id") != request.operation_id
            ):
                raise PortiaConflictError(
                    "Actor removal certificate belongs to another operation"
                )
        certificate_steps = [
            candidate
            for candidate in steps
            if isinstance(candidate, Mapping)
            and candidate.get("destination_path") == view.certificate_path
        ]
        if len(certificate_steps) != 1 or certificate_steps[0].get("disposition") != "accepted":
            raise PortiaRecoveryRequiredError(
                "removal certificate must be accepted before canonical removal"
            )
        _validate_quarantine(self.root, request)

        expected_relative = expected_target_relative_path(self.root, dict(request.target))
        if expected_relative is None or expected_relative != view.destination_path:
            raise PortiaPathError("canonical removal target has no exact identity-derived path")
        destination = resolve_workspace_relative(self.root, expected_relative)
        ensure_runtime_containment(self.root, destination)
        if destination.is_symlink():
            raise PortiaPathError("canonical removal refuses symbolic-link targets")
        try:
            content = read_bytes(destination)
        except PortiaNotFoundError:
            return AbsenceObservation(expected_relative, self.clock(), True)
        observed = fingerprint_bytes(content)
        if observed != view.prior_fingerprint:
            raise PortiaConflictError("canonical target changed after removal preflight")
        _validate_certificate_content(
            certificate_contract,
            certificate,
            request.target,
            content,
            observed,
        )
        exact_delete(destination, expected=observed)
        try:
            read_bytes(destination)
        except PortiaNotFoundError:
            return AbsenceObservation(expected_relative, self.clock(), False)
        raise PortiaRecoveryRequiredError("canonical payload remained after exact removal")
