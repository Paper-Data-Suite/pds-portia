"""Issue #22 production accounting for the Issue #40/#41 workflow boundary."""

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
        "newly_covers_evidence_workflow",
        "Event/Participant production from #40 and direct Observation production from #41 cover the positive classroom evidence story.",
    ),
    WorkflowParityEntry(
        "P22-02",
        "newly_covers_evidence_workflow",
        "Conflicting Accounts remain separate evidence and reported_involved revalidates exact Account authority without adjudicating the accounts.",
    ),
    WorkflowParityEntry(
        "P22-03",
        "consumes_issue39_identity",
        "Class-qualified roster resolution is consumed for represented source/observer authority without duplicating the resolver.",
    ),
    WorkflowParityEntry(
        "P22-04",
        "newly_covers_evidence_correction",
        "Material Account correction creates an exact v2 successor, supersedes the predecessor, and keeps historical references pinned.",
    ),
    WorkflowParityEntry(
        "P22-10",
        "newly_covers_evidence_workflow",
        "Distinct participant Accounts remain separate source perspectives rather than findings or admissions.",
    ),
    WorkflowParityEntry(
        "G22-009",
        "consumes_issue37_validation",
        "The workflow assembles authoritative identity facts for I/O-free graph validation and does not substitute local Portia identity for foreign authority.",
    ),
    WorkflowParityEntry(
        "G22-010",
        "newly_covers_workflow",
        "Exact historical evidence and workflow reads never follow a successor.",
    ),
    WorkflowParityEntry(
        "G22-011",
        "newly_covers_evidence_correction",
        "Account/Observation supersession ancestry is bounded, exact, and rejects replacement cycles.",
    ),
    WorkflowParityEntry(
        "G22-017",
        "newly_covers_evidence_authority",
        "Role current use delegates exact reported_involved Account authority to AccountWorkflowService and never mutates or silently retargets the Role basis.",
    ),
    WorkflowParityEntry(
        "G22-035",
        "shares_derived_boundary",
        "#41 persists an acyclic superseded-predecessor/active-successor frontier; derived-current presentation remains nonauthoritative and must not include both as current.",
    ),
    WorkflowParityEntry(
        "exact-reference-wrong-work",
        "consumes_issue37_validation",
        "Public workflows surface exact-reference ownership rejection.",
    ),
    WorkflowParityEntry(
        "exact-reference-wrong-version",
        "consumes_issue37_validation",
        "Public evidence readers preserve exact requested v1/v2 contract versions.",
    ),
    WorkflowParityEntry(
        "exact-reference-unresolved",
        "consumes_issue38_persistence",
        "Strict exact repository loads surface unresolved references without searching other work roots.",
    ),
)


def workflow_issue22_parity() -> tuple[WorkflowParityEntry, ...]:
    return WORKFLOW_ISSUE22_PARITY
