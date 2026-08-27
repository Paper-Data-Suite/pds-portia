from __future__ import annotations

from pathlib import Path

import pytest

from portia.storage.errors import PortiaConflictError
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.io import exclusive_create, guarded_replace, read_bytes


def test_exclusive_create_and_guarded_replace_are_fingerprint_protected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "record.json"
    first = canonical_json_bytes({"value": 1})
    second = canonical_json_bytes({"value": 2})
    first_fingerprint = exclusive_create(path, first)
    assert first_fingerprint == fingerprint_bytes(first)
    assert read_bytes(path) == first

    with pytest.raises(PortiaConflictError):
        exclusive_create(path, first)

    stale = fingerprint_bytes(canonical_json_bytes({"value": 0}))
    with pytest.raises(PortiaConflictError):
        guarded_replace(path, second, expected=stale)
    assert read_bytes(path) == first

    second_fingerprint = guarded_replace(path, second, expected=first_fingerprint)
    assert second_fingerprint == fingerprint_bytes(second)
    assert read_bytes(path) == second


def test_canonical_json_bytes_are_platform_stable() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}\n'
