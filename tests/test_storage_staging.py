from __future__ import annotations

from pathlib import Path

import pytest

from portia.storage.errors import PortiaConflictError
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.staging import (
    cleanup_staged,
    publish_staged,
    stage_bytes,
    staging_path_for,
)


def test_staging_path_is_target_adjacent(tmp_path: Path) -> None:
    destination = "classes/class_a/modules/portia/work/evt_a/records/account/acc_a.json"
    path = staging_path_for(tmp_path, "op_test", "step_test", destination)
    assert path == (
        tmp_path
        / "classes"
        / "class_a"
        / "modules"
        / "portia"
        / "work"
        / "evt_a"
        / "records"
        / "account"
        / ".portia-staging"
        / "op_test"
        / "step_test.candidate"
    )


def test_exact_staging_replay_and_contradiction(tmp_path: Path) -> None:
    destination = "portia/example.json"
    first = stage_bytes(tmp_path, "op_test", "step_test", destination, b"one")
    replay = stage_bytes(tmp_path, "op_test", "step_test", destination, b"one")
    assert replay.fingerprint == first.fingerprint
    with pytest.raises(PortiaConflictError):
        stage_bytes(tmp_path, "op_test", "step_test", destination, b"two")


def test_publish_exclusive_create_then_exact_cleanup(tmp_path: Path) -> None:
    staged = stage_bytes(
        tmp_path,
        "op_test",
        "step_test",
        "portia/example.json",
        b"candidate",
        intended=fingerprint_bytes(b"candidate"),
    )
    accepted = publish_staged(tmp_path, staged, action="exclusive_create")
    assert accepted == staged.fingerprint
    assert staged.destination_path.read_bytes() == b"candidate"
    cleanup_staged(tmp_path, staged)
    assert not staged.staging_path.exists()
