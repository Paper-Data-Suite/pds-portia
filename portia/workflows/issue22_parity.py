"""Issue #22 production accounting for the Issue #40 workflow boundary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WorkflowParityEntry:
    scenario_id: str
    disposition: str
    note: str


WORKFLOW_ISSUE22_PARITY: tuple[WorkflowParityEntry, ...] = (
    WorkflowParityEntry(
        "P22-01",
        "newly_covers_workflow",
        "Event, Participant, and Role are production workflows; Observation remains #41.",
    ),
    WorkflowParityEntry(
        "P22-03",
        "consumes_issue39_identity",
        "Class-qualified roster resolution is consumed without duplicating the resolver.",
    ),
    WorkflowParityEntry(
        "G22-009",
        "consumes_issue37_validation",
        "The workflow assembles complete authoritative facts for I/O-free validation.",
    ),
    WorkflowParityEntry(
        "G22-010",
        "newly_covers_workflow",
        "Exact historical workflow reads never follow a successor.",
    ),
    WorkflowParityEntry(
        "G22-017",
        "shares_issue41_boundary",
        "Role current use reads but never mutates qualifying Account authority.",
    ),
    WorkflowParityEntry(
        "exact-reference-wrong-work",
        "consumes_issue37_validation",
        "Public workflows surface exact-reference ownership rejection.",
    ),
    WorkflowParityEntry(
        "exact-reference-wrong-version",
        "consumes_issue37_validation",
        "Public workflows preserve exact requested contract versions.",
    ),
    WorkflowParityEntry(
        "exact-reference-unresolved",
        "consumes_issue38_persistence",
        "Strict exact repository loads surface unresolved references.",
    ),
)


def workflow_issue22_parity() -> tuple[WorkflowParityEntry, ...]:
    return WORKFLOW_ISSUE22_PARITY
