"""Explicit Issue #22 scenario disposition for the Issue #37 runtime boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

ParityDisposition: TypeAlias = Literal[
    "covered_by_37", "deferred_to_v0_3", "outside_37_runtime_boundary"
]


@dataclass(frozen=True, slots=True)
class Issue22Parity:
    """One deliberate mapping from foundation evidence to production runtime scope."""

    scenario_id: str
    disposition: ParityDisposition
    rationale: str
    production_codes: tuple[str, ...] = ()


_POSITIVE = {
    "P22-01": "digital Event/Participant/Role/Observation graph",
    "P22-02": "multi-participant evidence and judgment graph",
    "P22-03": "cross-class exact roster identity graph",
    "P22-04": "immutable correction/supersession/disagreement graph",
    "P22-07": "Actor, Response, and Communication graph",
    "P22-08": "Support Process through positive Outcome graph",
    "P22-09": "inconclusive/adverse Outcome graph",
    "P22-10": "Reentry/Repair graph without semantic overclaim",
    "P22-11": "cross-year Support Process continuation graph",
    "P22-15": "Classification/Hypothesis/Intervention graph",
}

_INVALID_CODES: dict[str, tuple[str, ...]] = {
    "G22-001": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-004": ("PORTIA.GRAPH.EXACT_REFERENCE_VERSION_MISMATCH",),
    "G22-008": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-011": ("PORTIA.GRAPH.SUPERSESSION_CYCLE",),
    "G22-014": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-017": ("PORTIA.GRAPH.UNRESOLVED_EXACT_REFERENCE",),
    "G22-018": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-021": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-022": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
    "G22-023": ("PORTIA.GRAPH.EXACT_REFERENCE_WRONG_WORK",),
}

_DEFERRED_V03 = {
    "P22-05": "paper capture/materialization is explicitly deferred to Portia v0.3",
    "P22-06": "structured import/materialization is explicitly deferred to Portia v0.3",
    "G22-019": "import-origin judgment activation belongs to the v0.3 import workflow",
    "G22-020": "source assertion/import promotion belongs to the v0.3 import workflow",
    "G22-026": "import replay/materialization belongs to the v0.3 import workflow",
    "G22-027": "paper capture review/materialization belongs to the v0.3 capture workflow",
}

_OUTSIDE = {
    "P22-12": "privacy projection/export generation is implemented by later v0.2 workflow issues; #37 models export provenance only",
    "P22-13": "retention/custody policy and derived rebuild execution require later services; #37 models their public values only",
    "P22-14": "coordinated persistence/recovery execution is Issue #38; #37 models operation records only",
    "G22-002": "authoritative persisted-owner comparison requires the storage placement supplied by Issue #38",
    "G22-003": "canonical filesystem path agreement is a storage-placement invariant for Issue #38",
    "G22-005": "detecting an erroneous cross-class identity resolver result requires the Actor/roster resolution service in Issue #39",
    "G22-006": "detecting an erroneous display-name resolver result requires the Actor/roster resolution service in Issue #39",
    "G22-007": "detecting Actor-for-roster substitution requires the Actor/roster resolution service in Issue #39",
    "G22-009": "detecting a foreign-Core substitution requires an authoritative resolver result, not record structure alone",
    "G22-010": "detecting silent successor-following requires observing a historical-resolution service result",
    "G22-012": "derived-current selection execution belongs to canonical persistence/derived rebuilding in Issue #38",
    "G22-013": "the intended contested record is workflow context outside a Statement of Disagreement wire value",
    "G22-015": "observing migration-driven historical retargeting requires the later migration/resolution service",
    "G22-016": "distinguishing a requested cross-year continuation operation from migration requires workflow intent supplied by later services",
    "G22-024": "a rejected later write is operation intent rather than a second accepted canonical record in an in-memory graph",
    "G22-025": "detecting historical Support successor-following requires observing a resolution service result",
    "G22-028": "reconciling committed operation state with durable result bytes is Issue #38 persistence/recovery work",
    "G22-029": "restart replay versus exact readback reconciliation is Issue #38 persistence/recovery work",
    "G22-030": "participant privacy projection generation is a later v0.2 privacy workflow",
    "G22-031": "privacy outward-state serialization is a later v0.2 privacy workflow",
    "G22-032": "binding the exact representation actually consumed is export-generation behavior, not record conversion",
    "G22-033": "privacy-minimized export path generation is a later deliberate-export workflow",
    "G22-034": "incoming-reference index comparison requires derived-state generation/rebuild services in Issue #38",
    "G22-035": "current-view frontier generation requires derived-state rebuilding in Issue #38",
    "G22-036": "source-snapshot freshness requires exact persisted representation fingerprints from Issue #38",
    "G22-037": "foreign-custody destruction verification is an external policy/service boundary, not record-graph inference",
}

_entries: list[Issue22Parity] = []
for scenario_id, rationale in sorted(_POSITIVE.items()):
    _entries.append(Issue22Parity(scenario_id, "covered_by_37", rationale))
for scenario_id, codes in sorted(_INVALID_CODES.items()):
    _entries.append(
        Issue22Parity(
            scenario_id,
            "covered_by_37",
            "the principal defect is observable from the in-memory exact record graph",
            codes,
        )
    )
for scenario_id, rationale in sorted(_DEFERRED_V03.items()):
    _entries.append(Issue22Parity(scenario_id, "deferred_to_v0_3", rationale))
for scenario_id, rationale in sorted(_OUTSIDE.items()):
    _entries.append(Issue22Parity(scenario_id, "outside_37_runtime_boundary", rationale))

ISSUE22_PARITY: Final[tuple[Issue22Parity, ...]] = tuple(_entries)


def parity_by_id() -> dict[str, Issue22Parity]:
    """Return the complete Issue #22 parity matrix keyed by scenario ID."""
    return {entry.scenario_id: entry for entry in ISSUE22_PARITY}
