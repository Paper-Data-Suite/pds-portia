"""Target-adjacent staging and exact publication for coordinated Portia writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from portia.models.identifiers import validate_portia_id
from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaPathError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.io import (
    exact_delete,
    exclusive_create,
    guarded_replace,
    read_bytes,
)
from portia.storage.paths import resolve_workspace_relative, workspace_relative


@dataclass(frozen=True, slots=True)
class StagedArtifact:
    """One exact operation-owned candidate that is not yet canonical."""

    operation_id: str
    step_id: str
    staging_path: Path
    destination_path: Path
    fingerprint: ContentFingerprint


def ensure_runtime_containment(root: Path, candidate: Path) -> None:
    """Reject existing symlink/junction chains that escape the selected workspace."""
    try:
        root_resolved = root.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise PortiaPathError(
            "selected workspace must exist before persistence"
        ) from exc
    if not root_resolved.is_dir():
        raise PortiaPathError("selected workspace must be a directory")

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise PortiaPathError("candidate is outside the selected workspace") from exc

    probe = candidate
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            raise PortiaPathError("candidate has no existing workspace ancestor")
        probe = parent
    try:
        resolved_probe = probe.resolve(strict=True)
        resolved_probe.relative_to(root_resolved)
    except (OSError, RuntimeError, ValueError) as exc:
        raise PortiaPathError(
            "existing path ancestry escapes the selected workspace"
        ) from exc

    if candidate.exists() or candidate.is_symlink():
        try:
            resolved_candidate = candidate.resolve(strict=True)
            resolved_candidate.relative_to(root_resolved)
        except (OSError, RuntimeError, ValueError) as exc:
            raise PortiaPathError(
                "persisted target resolves outside the selected workspace"
            ) from exc


def staging_path_for(
    workspace_root: str | Path,
    operation_id: str,
    step_id: str,
    destination_relative_path: object,
) -> Path:
    """Return the deterministic target-adjacent candidate path for one step."""
    operation = validate_portia_id(operation_id, "op_", "operation_id")
    step = validate_portia_id(step_id, "step_", "step_id")
    root = Path(workspace_root).resolve(strict=False)
    destination = resolve_workspace_relative(root, destination_relative_path)
    ensure_runtime_containment(root, destination)
    staging = destination.parent / ".portia-staging" / operation / f"{step}.candidate"
    ensure_runtime_containment(root, staging)
    return staging


def stage_bytes(
    workspace_root: str | Path,
    operation_id: str,
    step_id: str,
    destination_relative_path: object,
    content: bytes,
    *,
    intended: ContentFingerprint | None = None,
) -> StagedArtifact:
    """Stage bytes, allowing only exact idempotent replay of an existing candidate."""
    root = Path(workspace_root).resolve(strict=False)
    destination = resolve_workspace_relative(root, destination_relative_path)
    staging = staging_path_for(root, operation_id, step_id, destination_relative_path)
    fingerprint = fingerprint_bytes(content)
    if intended is not None and fingerprint != intended:
        raise PortiaConflictError(
            "candidate bytes do not match the journaled intended result"
        )
    try:
        observed = exclusive_create(staging, content)
    except PortiaConflictError:
        existing = read_bytes(staging)
        observed = fingerprint_bytes(existing)
        if observed != fingerprint or existing != content:
            raise PortiaConflictError(
                "staging identity already contains contradictory candidate bytes"
            ) from None
    if observed != fingerprint:
        raise PortiaCorruptionError("staged-candidate readback fingerprint mismatch")
    return StagedArtifact(operation_id, step_id, staging, destination, observed)


def publish_staged(
    workspace_root: str | Path,
    staged: StagedArtifact,
    *,
    action: str,
    expected_prior: ContentFingerprint | None = None,
) -> ContentFingerprint:
    """Publish one exact staged candidate under an accepted write action."""
    root = Path(workspace_root).resolve(strict=False)
    ensure_runtime_containment(root, staged.staging_path)
    ensure_runtime_containment(root, staged.destination_path)
    if workspace_relative(root, staged.staging_path).startswith("../"):
        raise PortiaPathError("staged candidate is outside the selected workspace")
    content = read_bytes(staged.staging_path)
    if fingerprint_bytes(content) != staged.fingerprint:
        raise PortiaConflictError("staged candidate changed after validation")

    if action == "exclusive_create":
        if expected_prior is not None:
            raise PortiaConflictError("exclusive creation cannot specify prior bytes")
        accepted = exclusive_create(staged.destination_path, content)
    elif action in {"revision_aware_replace", "atomic_pointer_replace"}:
        if expected_prior is None:
            raise PortiaConflictError(
                f"{action} requires an exact expected prior fingerprint"
            )
        accepted = guarded_replace(
            staged.destination_path,
            content,
            expected=expected_prior,
        )
    else:
        raise PortiaConflictError(f"unsupported staged publication action: {action}")

    if accepted != staged.fingerprint:
        raise PortiaCorruptionError(
            "accepted destination does not match staged candidate"
        )
    return accepted


def cleanup_staged(
    workspace_root: str | Path,
    staged: StagedArtifact,
) -> None:
    """Remove one exact proven-unaccepted candidate without broad cleanup."""
    root = Path(workspace_root).resolve(strict=False)
    ensure_runtime_containment(root, staged.staging_path)
    exact_delete(staged.staging_path, expected=staged.fingerprint)
    _prune_empty_staging_dirs(root, staged.staging_path.parent)


def _prune_empty_staging_dirs(root: Path, start: Path) -> None:
    """Best-effort removal of empty operation-owned staging directories only."""
    current = start
    for _ in range(2):
        if current == root or current.name not in {
            start.name,
            ".portia-staging",
        }:
            break
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def replace_staging_candidate(
    workspace_root: str | Path,
    staged: StagedArtifact,
    content: bytes,
) -> StagedArtifact:
    """Regenerate a pre-acceptance candidate only against its exact old bytes."""
    root = Path(workspace_root).resolve(strict=False)
    ensure_runtime_containment(root, staged.staging_path)
    new_fingerprint = guarded_replace(
        staged.staging_path,
        content,
        expected=staged.fingerprint,
    )
    return StagedArtifact(
        staged.operation_id,
        staged.step_id,
        staged.staging_path,
        staged.destination_path,
        new_fingerprint,
    )
