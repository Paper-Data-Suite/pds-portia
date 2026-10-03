from __future__ import annotations

from pathlib import Path

import pytest

from portia.storage.errors import PortiaConflictError, PortiaStorageError
from portia.storage.fingerprint import canonical_json_bytes, fingerprint_bytes
from portia.storage.generated_paths import (
    REPLACEMENT_TEMPORARY_LEAF_LENGTH,
    build_replacement_temporary_leaf,
)
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


def test_guarded_replace_uses_fixed_bounded_target_adjacent_leaf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / ("record_" + "x" * 96 + ".json")
    first = b"first"
    second = b"second"
    expected = exclusive_create(path, first)
    nonce = "a" * 32
    monkeypatch.setattr("portia.storage.io.secrets.token_hex", lambda _size: nonce)

    import portia.storage.io as storage_io

    real_replace = storage_io.os.replace
    observed: list[tuple[Path, Path]] = []

    def recording_replace(source: str | Path, destination: str | Path) -> None:
        source_path = Path(source)
        destination_path = Path(destination)
        observed.append((source_path, destination_path))
        real_replace(source_path, destination_path)

    monkeypatch.setattr(storage_io.os, "replace", recording_replace)

    result = guarded_replace(path, second, expected=expected)
    assert result == fingerprint_bytes(second)
    assert len(observed) == 1
    temporary, destination = observed[0]
    assert destination == path
    assert temporary.parent == path.parent
    assert temporary.name == build_replacement_temporary_leaf(nonce)
    assert len(temporary.name) == REPLACEMENT_TEMPORARY_LEAF_LENGTH == 51
    assert path.name not in temporary.name
    assert not temporary.exists()


def test_guarded_replace_retries_exact_temporary_collision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "record.json"
    expected = exclusive_create(path, b"old")
    nonces = iter(("0" * 32, "1" * 32))
    monkeypatch.setattr(
        "portia.storage.io.secrets.token_hex",
        lambda _size: next(nonces),
    )
    collision = path.parent / build_replacement_temporary_leaf("0" * 32)
    collision.write_bytes(b"unrelated-existing-temporary")

    result = guarded_replace(path, b"new", expected=expected)
    assert result == fingerprint_bytes(b"new")
    assert collision.read_bytes() == b"unrelated-existing-temporary"
    assert path.read_bytes() == b"new"


def test_guarded_replace_cleans_bounded_temporary_after_replace_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "record.json"
    expected = exclusive_create(path, b"old")
    nonce = "f" * 32
    temporary = path.parent / build_replacement_temporary_leaf(nonce)
    monkeypatch.setattr("portia.storage.io.secrets.token_hex", lambda _size: nonce)

    def failing_replace(_source: str | Path, _destination: str | Path) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr("portia.storage.io.os.replace", failing_replace)

    with pytest.raises(PortiaStorageError, match="could not atomically replace"):
        guarded_replace(path, b"new", expected=expected)

    assert path.read_bytes() == b"old"
    assert not temporary.exists()


def test_canonical_json_bytes_are_platform_stable() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}\n'
