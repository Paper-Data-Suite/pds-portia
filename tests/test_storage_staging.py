from __future__ import annotations

from pathlib import Path

import pytest

from portia.storage.errors import PortiaConflictError
from portia.storage.fingerprint import fingerprint_bytes
from portia.storage.generated_paths import STAGING_CANDIDATE_LEAF_LENGTH
from portia.storage.staging import (
    cleanup_staged,
    legacy_staging_path_for,
    publish_staged,
    stage_bytes,
    staging_path_for,
)


def test_staging_path_uses_bounded_workspace_level_namespace(
    tmp_path: Path,
) -> None:
    destination = "classes/class_a/modules/portia/work/evt_a/records/account/acc_a.json"
    path = staging_path_for(tmp_path, "op_test", "step_test", destination)
    assert path == (
        tmp_path
        / "portia"
        / ".staging"
        / "pt_dcc99bffa04701fc8e0b752e946c9a37"
        / "pt_6303d89e16dcca94b69851be93be9e4f.candidate"
    )
    assert len(path.name) == STAGING_CANDIDATE_LEAF_LENGTH == 45
    assert "acc_a" not in path.name


def test_legacy_staging_path_remains_exactly_addressable(tmp_path: Path) -> None:
    destination = "classes/class_a/modules/portia/work/evt_a/records/account/acc_a.json"
    path = legacy_staging_path_for(tmp_path, "op_test", "step_test", destination)
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


def test_staging_geometry_is_independent_of_destination_depth(
    tmp_path: Path,
) -> None:
    shallow = staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        "portia/example.json",
    )
    deep_destination = "/".join(
        [
            "classes",
            "class_" + "x" * 96,
            "modules",
            "portia",
            "work",
            "evt_" + "y" * 96,
            "records",
            "observation",
            "obs_" + "z" * 96 + ".json",
        ]
    )
    deep = staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        deep_destination,
    )
    assert len(shallow.relative_to(tmp_path).as_posix()) == len(
        deep.relative_to(tmp_path).as_posix()
    )
    assert shallow.parent == deep.parent
    assert shallow.name != deep.name
    assert len(deep.name) == STAGING_CANDIDATE_LEAF_LENGTH


def test_exact_staging_replay_and_contradiction(tmp_path: Path) -> None:
    destination = "portia/example.json"
    first = stage_bytes(tmp_path, "op_test", "step_test", destination, b"one")
    replay = stage_bytes(tmp_path, "op_test", "step_test", destination, b"one")
    assert replay.fingerprint == first.fingerprint
    assert replay.staging_path == first.staging_path
    with pytest.raises(PortiaConflictError):
        stage_bytes(tmp_path, "op_test", "step_test", destination, b"two")


def test_legacy_staging_candidate_is_replayed_without_migration(
    tmp_path: Path,
) -> None:
    destination = "portia/example.json"
    legacy = legacy_staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        destination,
    )
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"one")

    replay = stage_bytes(
        tmp_path,
        "op_test",
        "step_test",
        destination,
        b"one",
    )

    assert replay.staging_path == legacy
    assert replay.fingerprint == fingerprint_bytes(b"one")
    assert not staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        destination,
    ).exists()


def test_current_and_legacy_staging_candidates_fail_closed(
    tmp_path: Path,
) -> None:
    destination = "portia/example.json"
    current = staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        destination,
    )
    legacy = legacy_staging_path_for(
        tmp_path,
        "op_test",
        "step_test",
        destination,
    )
    current.parent.mkdir(parents=True)
    legacy.parent.mkdir(parents=True)
    current.write_bytes(b"one")
    legacy.write_bytes(b"one")

    with pytest.raises(PortiaConflictError, match="current and legacy"):
        stage_bytes(
            tmp_path,
            "op_test",
            "step_test",
            destination,
            b"one",
        )


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
    assert not (tmp_path / "portia" / ".staging").exists()
