from __future__ import annotations

from portia.identity.issue22_parity import (
    ISSUE39_IDENTITY_PARITY,
    identity_parity_by_id,
)


def test_issue39_identity_parity_accounts_for_exact_owned_scenarios() -> None:
    by_id = identity_parity_by_id()
    assert set(by_id) == {"G22-005", "G22-006", "G22-007", "G22-009"}
    assert by_id["G22-005"].disposition == "covered_by_39"
    assert by_id["G22-006"].disposition == "covered_by_39"
    assert by_id["G22-007"].disposition == "covered_by_39"
    assert by_id["G22-009"].disposition == "bounded_shared_boundary"
    assert len(ISSUE39_IDENTITY_PARITY) == 4
