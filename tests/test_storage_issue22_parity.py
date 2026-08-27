from __future__ import annotations

from portia.storage.issue22_parity import storage_parity_by_id
from portia.validation.issue22_parity import parity_by_id


def test_storage_parity_accounts_for_every_issue37_outside_scenario() -> None:
    runtime = parity_by_id()
    expected = {
        scenario_id
        for scenario_id, entry in runtime.items()
        if entry.disposition == "outside_37_runtime_boundary"
    }
    actual = set(storage_parity_by_id())
    assert actual == expected


def test_storage_parity_claims_only_persistence_owned_scenarios() -> None:
    parity = storage_parity_by_id()
    assert {
        scenario_id
        for scenario_id, entry in parity.items()
        if entry.disposition == "covered_by_38"
    } == {"P22-14", "G22-002", "G22-003", "G22-028", "G22-029", "G22-036"}
    assert parity["P22-13"].disposition == "shared_boundary"
    assert parity["G22-037"].disposition == "external_boundary"
