from __future__ import annotations

from portia.storage.quarantine import quarantine_applies


def test_workspace_quarantine_covers_work_target() -> None:
    assert quarantine_applies(
        {"kind": "workspace"},
        {
            "kind": "work",
            "work_ref": {
                "module_id": "portia",
                "class_id": "class_a",
                "work_id": "evt_a",
                "work_kind": "event",
                "contract_version": "2",
            },
        },
    )


def test_work_quarantine_covers_child_but_not_other_work() -> None:
    work = {
        "module_id": "portia",
        "class_id": "class_a",
        "work_id": "evt_a",
        "work_kind": "event",
        "contract_version": "2",
    }
    quarantine_target = {"kind": "work", "work_ref": work}
    requested = {
        "kind": "work_record",
        "work_record_ref": {
            "work_ref": work,
            "record_ref": {
                "record_kind": "account",
                "record_id": "acct_a",
                "contract_version": "2",
            },
        },
    }
    assert quarantine_applies(quarantine_target, requested)
    other = {
        **requested,
        "work_record_ref": {
            **requested["work_record_ref"],
            "work_ref": {**work, "work_id": "evt_b"},
        },
    }
    assert not quarantine_applies(quarantine_target, other)


def test_actor_set_quarantine_matches_only_listed_actor() -> None:
    quarantine_target = {
        "kind": "actor_set",
        "actor_refs": [
            {"actor_id": "actr_one", "contract_version": "1"},
            {"actor_id": "actr_two", "contract_version": "1"},
        ],
    }
    requested = {
        "kind": "actor_directory_record",
        "actor_directory_record_ref": {
            "kind": "actor",
            "actor_ref": {"actor_id": "actr_two", "contract_version": "1"},
        },
    }
    assert quarantine_applies(quarantine_target, requested)


def test_derived_quarantine_requires_exact_projection_scope() -> None:
    quarantine_target = {
        "kind": "derived_projection",
        "projection_kind": "current_state_view",
        "projection_scope": {"scope": "class", "class_id": "class_a"},
    }
    assert quarantine_applies(quarantine_target, dict(quarantine_target))
    assert not quarantine_applies(
        quarantine_target,
        {
            **quarantine_target,
            "projection_scope": {"scope": "class", "class_id": "class_b"},
        },
    )
