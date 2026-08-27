from __future__ import annotations

from pathlib import Path

import pytest

from portia.models.references import ExactPortiaWorkRef
from portia.storage.errors import PortiaPathError
from portia.storage.locks import derive_lock_id
from portia.storage.paths import (
    actor_child_path,
    actor_directory_removal_path,
    actor_record_path,
    derived_current_path,
    operation_current_path,
    operation_revision_path,
    resolve_workspace_relative,
    work_manifest_path,
    work_record_path,
)


def _event_ref() -> ExactPortiaWorkRef:
    return ExactPortiaWorkRef(
        class_id="class_english10_p2",
        work_id="evt_example",
        work_kind="event",
        contract_version="2",
    )


def test_canonical_work_and_actor_paths_are_deterministic(tmp_path: Path) -> None:
    work = _event_ref()
    assert work_manifest_path(tmp_path, work) == (
        tmp_path
        / "classes"
        / "class_english10_p2"
        / "modules"
        / "portia"
        / "work"
        / "evt_example"
        / "work.json"
    )
    assert work_record_path(tmp_path, work, "event_participant", "ep_example") == (
        tmp_path
        / "classes"
        / "class_english10_p2"
        / "modules"
        / "portia"
        / "work"
        / "evt_example"
        / "records"
        / "event_participant"
        / "ep_example.json"
    )
    assert actor_record_path(tmp_path, "actr_example") == (
        tmp_path / "portia" / "actors" / "actr_example" / "actor.json"
    )
    assert actor_child_path(
        tmp_path, "actr_example", "actor_contact_point", "acp_example"
    ) == (
        tmp_path
        / "portia"
        / "actors"
        / "actr_example"
        / "records"
        / "actor_contact_point"
        / "acp_example.json"
    )
    assert actor_directory_removal_path(tmp_path, "rmv_example") == (
        tmp_path / "portia" / "actor-directory-removals" / "rmv_example.json"
    )


def test_operation_paths_use_immutable_revision_series(tmp_path: Path) -> None:
    assert operation_revision_path(tmp_path, "op_example", 3) == (
        tmp_path / "portia" / "operations" / "op_example" / "revisions" / "3.json"
    )
    assert operation_current_path(tmp_path, "op_example") == (
        tmp_path / "portia" / "operations" / "op_example" / "current.json"
    )


def test_workspace_derived_scope_never_manufactures_workspace_identity(
    tmp_path: Path,
) -> None:
    with pytest.raises(PortiaPathError, match="authoritative workspace_id"):
        derived_current_path(tmp_path, "class_summary", {"scope": "workspace"})


def test_workspace_relative_paths_reject_windows_and_traversal_forms(
    tmp_path: Path,
) -> None:
    for value in (
        "../outside.json",
        "portia\\operations\\op_example.json",
        "C:/outside.json",
        "/absolute.json",
    ):
        with pytest.raises(PortiaPathError):
            resolve_workspace_relative(tmp_path, value)


def test_lock_id_matches_accepted_issue13_work_lock_fixture() -> None:
    target = {
        "kind": "work",
        "work_ref": {
            "module_id": "portia",
            "class_id": "class_english10_p2",
            "work_id": "evt_example",
            "work_kind": "event",
            "contract_version": "2",
        },
    }
    assert derive_lock_id("work", target) == (
        "lock_fa7db2eeed2ed3dc58cb12f945306b0a3311a22c54ed10fda0c9cecc35cb6fa2"
    )
