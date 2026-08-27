"""Issue #22 persistence parity accounting for the Issue #38 storage boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

StorageParityDisposition: TypeAlias = Literal[
    "covered_by_38",
    "shared_boundary",
    "later_v0_2_service",
    "external_boundary",
]


@dataclass(frozen=True, slots=True)
class StorageIssue22Parity:
    """One explicit disposition for a scenario left outside Issue #37 runtime scope."""

    scenario_id: str
    disposition: StorageParityDisposition
    rationale: str


_COVERED = {
    "P22-14": "coordinated operation staging, locking, guarded publication, partial success, replay, and explicit recovery are implemented by the storage layer",
    "G22-002": "repository loads and writes reconcile persisted owner/class identity with the canonical Core-backed path",
    "G22-003": "typed operation targets and canonical path derivation reject path/owner disagreement",
    "G22-028": "committed-operation durable-result reconciliation verifies exact result paths and fingerprints",
    "G22-029": "restart recovery reconciles durable readback and does not replay an already accepted canonical write blindly",
    "G22-036": "derived current selection revalidates the exact source snapshot and source bytes before use",
}

_SHARED = {
    "P22-13": "#38 implements nonauthoritative immutable derived generations, exact source snapshots, and guarded current selection; retention policy, foreign custody, and projection-specific product semantics remain with later owners",
}

_LATER = {
    "P22-12": "participant privacy projection and deliberate export generation belong to later v0.2 privacy/export workflows",
    "G22-005": "cross-class roster identity resolution belongs to the Actor/Core resolver service",
    "G22-006": "display-name similarity resolution belongs to the Actor/Core resolver service",
    "G22-007": "Actor-versus-roster identity selection belongs to the Actor/Core resolver service",
    "G22-009": "foreign Core reference substitution requires an authoritative resolver result",
    "G22-010": "silent successor-following is observable only at the historical-resolution service boundary",
    "G22-012": "#38 verifies derived generation identity, source freshness, and explicit pointer selection; whether a projection semantically chooses a superseded predecessor belongs to the projection builder",
    "G22-013": "Statement-of-Disagreement target intent is workflow context outside generic persistence",
    "G22-015": "migration-driven historical retargeting is a later migration/resolution service concern",
    "G22-016": "cross-year continuation versus migration depends on workflow intent supplied by the owning service",
    "G22-024": "a later evaluation must receive a new Outcome identity; generic expected-state persistence cannot infer that domain-timeframe intent",
    "G22-025": "historical Support successor-following is a later resolution-service concern",
    "G22-030": "participant privacy projection field selection belongs to the privacy-projection workflow",
    "G22-031": "privacy outward-state distinctions belong to the privacy-projection workflow",
    "G22-032": "export source-inventory binding belongs to deliberate export generation",
    "G22-033": "privacy-safe export destination naming belongs to deliberate export generation",
    "G22-034": "#38 guarantees source/fingerprint truth and atomic derived replacement; incoming-reference semantic reconstruction belongs to its projection builder",
    "G22-035": "#38 guarantees source/fingerprint truth and atomic derived replacement; replacement-frontier/current-view semantics belong to their projection builders",
}

_EXTERNAL = {
    "G22-037": "verification of destruction in Core, sibling, or external custody is outside Portia local persistence authority",
}

_entries: list[StorageIssue22Parity] = []
for scenario_id, rationale in sorted(_COVERED.items()):
    _entries.append(StorageIssue22Parity(scenario_id, "covered_by_38", rationale))
for scenario_id, rationale in sorted(_SHARED.items()):
    _entries.append(StorageIssue22Parity(scenario_id, "shared_boundary", rationale))
for scenario_id, rationale in sorted(_LATER.items()):
    _entries.append(StorageIssue22Parity(scenario_id, "later_v0_2_service", rationale))
for scenario_id, rationale in sorted(_EXTERNAL.items()):
    _entries.append(StorageIssue22Parity(scenario_id, "external_boundary", rationale))

ISSUE22_STORAGE_PARITY: Final[tuple[StorageIssue22Parity, ...]] = tuple(_entries)


def storage_parity_by_id() -> dict[str, StorageIssue22Parity]:
    """Return every Issue #22 scenario that was outside the #37 runtime boundary."""
    return {entry.scenario_id: entry for entry in ISSUE22_STORAGE_PARITY}
