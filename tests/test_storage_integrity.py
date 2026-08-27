from __future__ import annotations

from pathlib import Path

from portia.storage.integrity import expected_target_relative_path


def test_work_target_derives_accepted_canonical_path(tmp_path: Path) -> None:
    target = {
        "kind": "work",
        "work_ref": {
            "module_id": "portia",
            "class_id": "class_a",
            "work_id": "evt_a",
            "work_kind": "event",
            "contract_version": "2",
        },
    }
    assert expected_target_relative_path(tmp_path, target) == (
        "classes/class_a/modules/portia/work/evt_a/work.json"
    )


def test_work_record_target_derives_accepted_canonical_path(tmp_path: Path) -> None:
    target = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": {
                "module_id": "portia",
                "class_id": "class_a",
                "work_id": "evt_a",
                "work_kind": "event",
                "contract_version": "2",
            },
            "record_ref": {
                "record_kind": "account",
                "record_id": "acc_a",
                "contract_version": "2",
            },
        },
    }
    assert expected_target_relative_path(tmp_path, target) == (
        "classes/class_a/modules/portia/work/evt_a/records/account/acc_a.json"
    )


def test_actor_target_derives_workspace_scoped_path(tmp_path: Path) -> None:
    target = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor",
            "actor_ref": {
                "actor_id": "actr_a",
                "contract_version": "1",
            },
        },
    }
    assert expected_target_relative_path(tmp_path, target) == (
        "portia/actors/actr_a/actor.json"
    )
