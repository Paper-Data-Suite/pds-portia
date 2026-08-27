"""Issue #22 identity-resolution parity accounting owned by Issue #39."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

Issue39Disposition = Literal["covered_by_39", "bounded_shared_boundary"]


@dataclass(frozen=True, slots=True)
class Issue39IdentityParity:
    scenario_id: str
    disposition: Issue39Disposition
    invariant: str


ISSUE39_IDENTITY_PARITY: Final[tuple[Issue39IdentityParity, ...]] = (
    Issue39IdentityParity(
        "G22-005",
        "covered_by_39",
        "same local student_id across classes never collapses class-qualified identity",
    ),
    Issue39IdentityParity(
        "G22-006",
        "covered_by_39",
        "display or preferred-name equality never establishes roster identity",
    ),
    Issue39IdentityParity(
        "G22-007",
        "covered_by_39",
        "Actor identity never substitutes for required Core roster identity",
    ),
    Issue39IdentityParity(
        "G22-009",
        "bounded_shared_boundary",
        "resolver rejects authoritative Core roster/student results from another class scope; "
        "foreign producer semantics remain with their owning resolver",
    ),
)


def identity_parity_by_id() -> dict[str, Issue39IdentityParity]:
    return {entry.scenario_id: entry for entry in ISSUE39_IDENTITY_PARITY}
