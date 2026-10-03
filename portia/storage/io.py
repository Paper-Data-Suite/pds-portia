"""Bounded exact-byte filesystem primitives for Portia persistence."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any, Final

from portia.storage.errors import (
    PortiaConflictError,
    PortiaCorruptionError,
    PortiaNotFoundError,
    PortiaStorageError,
)
from portia.storage.fingerprint import ContentFingerprint, fingerprint_bytes
from portia.storage.generated_paths import build_replacement_temporary_leaf

_REPLACEMENT_TEMPORARY_ALLOCATION_ATTEMPTS: Final[int] = 8


def read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise PortiaNotFoundError(f"persisted artifact not found: {path}") from exc
    except OSError as exc:
        raise PortiaStorageError(f"could not read persisted artifact: {path}") from exc


def read_json(path: Path) -> tuple[object, bytes, ContentFingerprint]:
    content = read_bytes(path)
    try:
        value: object = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortiaCorruptionError(f"persisted artifact is not valid UTF-8 JSON: {path}") from exc
    return value, content, fingerprint_bytes(content)


def _fsync_dir(path: Path) -> None:
    if os.name == "nt":
        return
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def exclusive_create(path: Path, content: bytes) -> ContentFingerprint:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_dir(path.parent)
    except FileExistsError as exc:
        raise PortiaConflictError(f"persisted identity already exists: {path}") from exc
    except OSError as exc:
        raise PortiaStorageError(f"could not exclusively create artifact: {path}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    observed = read_bytes(path)
    if observed != content:
        raise PortiaCorruptionError(f"exclusive-create readback mismatch: {path}")
    return fingerprint_bytes(observed)


def _write_replacement_temporary(directory: Path, content: bytes) -> Path:
    """Create one bounded target-adjacent replacement candidate exclusively."""
    for _attempt in range(_REPLACEMENT_TEMPORARY_ALLOCATION_ATTEMPTS):
        candidate = directory / build_replacement_temporary_leaf(secrets.token_hex(16))
        descriptor: int | None = None
        try:
            descriptor = os.open(
                candidate,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
        except FileExistsError:
            continue
        try:
            with os.fdopen(descriptor, "wb") as handle:
                descriptor = None
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except OSError:
            if descriptor is not None:
                os.close(descriptor)
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                pass
            raise
        return candidate
    raise FileExistsError(
        "could not allocate a unique bounded replacement temporary artifact"
    )


def guarded_replace(
    path: Path,
    content: bytes,
    *,
    expected: ContentFingerprint,
) -> ContentFingerprint:
    prior = read_bytes(path)
    observed_prior = fingerprint_bytes(prior)
    if observed_prior != expected:
        raise PortiaConflictError(
            f"expected prior fingerprint does not match persisted artifact: {path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        temporary = _write_replacement_temporary(path.parent, content)
        # Recheck immediately before replace; do not silently retry on drift.
        if fingerprint_bytes(read_bytes(path)) != expected:
            raise PortiaConflictError(
                f"persisted artifact changed while replacement was staged: {path}"
            )
        os.replace(temporary, path)
        temporary = None
        _fsync_dir(path.parent)
    except PortiaConflictError:
        raise
    except OSError as exc:
        raise PortiaStorageError(f"could not atomically replace artifact: {path}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
    observed = read_bytes(path)
    if observed != content:
        raise PortiaCorruptionError(f"replacement readback mismatch: {path}")
    return fingerprint_bytes(observed)


def exact_delete(path: Path, *, expected: ContentFingerprint) -> None:
    content = read_bytes(path)
    if fingerprint_bytes(content) != expected:
        raise PortiaConflictError(f"refusing to remove changed artifact: {path}")
    try:
        path.unlink()
        _fsync_dir(path.parent)
    except FileNotFoundError as exc:
        raise PortiaConflictError(f"artifact disappeared before removal: {path}") from exc
    except OSError as exc:
        raise PortiaStorageError(f"could not remove artifact: {path}") from exc


def json_object(value: object, *, description: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PortiaCorruptionError(f"{description} must contain a JSON object")
    return value
