# Due Follow-Up and Native Attention Queries

Issue #49 adds Portia's production, read-only native query layer for teacher
workflow attention. Portia owns the interpretation of its own workflow,
integrity, Quarantine, recovery, and derived state; PDS Core continues to own
shared workspace/class identity. The result is presentation-neutral and does
not create canonical task or alert records.

## Follow-Up schedule and attention are separate

`FollowUpScheduleQueryService` answers which current Follow-Ups are scheduled,
due, or overdue as of one explicit caller-supplied time.
`AttentionQueryService` consumes the same timing authority but only turns due
and overdue Follow-Ups into attention.

A future scheduled Follow-Up is therefore visible in the Follow-Up schedule
without automatically becoming teacher attention. Completed, cancelled, and
unable-to-complete Follow-Ups are historical workflow state, not current overdue
attention.

## Explicit time semantics

Every schedule and attention query carries an offset-aware `as_of`.
Classification never obtains an implicit wall clock. Date-only planned timing
remains calendar-date precision; exact timestamps compare offset-aware instants;
planned windows preserve inclusive start/end semantics.

## Exact query scope

The native scope is exactly one of:

```text
workspace
exact Core class_id
ExactPortiaWorkRef
```

Workspace evaluation must be explicitly requested. Unknown exact class or work
scope fails safely and never widens to workspace scope. `active_school_year` is
an optional exact filter, not an identity join.

Broad workspace/class evaluation may preserve unrelated valid results when one
independent source fails safely. Such reports carry the bounded
`portia_attention_partial` notice. If the requested exact scope itself cannot
be safely evaluated, the report is `unavailable`, with empty items/summaries
and `portia_attention_unavailable`. Raw exception text is never copied into
notices.

## Stable taxonomy and count units

The code-owned native taxonomy is deterministic presentation order, not
priority, severity, urgency, behavior risk, or a recommendation ranking.

| Code | Class | Count unit |
| --- | --- | --- |
| `portia_follow_up_due` | workflow | follow_ups |
| `portia_follow_up_overdue` | workflow | follow_ups |
| `portia_review_incomplete` | workflow | reviews |
| `portia_integrity_conflict` | integrity | integrity_findings |
| `portia_integrity_review_required` | integrity | integrity_findings |
| `portia_recovery_required` | recovery | recovery_scopes |
| `portia_quarantine_active` | integrity | quarantines |
| `portia_derived_state_stale` | recovery | derived_projections |
| `portia_support_process_review_due` | workflow | support_processes |
| `portia_support_process_review_overdue` | workflow | support_processes |
| `portia_support_process_dependency_attention` | workflow | support_processes |

Counts across codes may overlap. Their sum is not a count of students, unique
works, or unique problems.

## Review semantics

Current active Reviews in `open`, `in_review`, or `awaiting_information` are
`portia_review_incomplete`. Completed/cancelled Reviews are not. Review
attention does not infer that a Determination is missing or required.

## Integrity and conflict semantics

Integrity attention is sourced only from accepted current
`integrity_finding@2` authority. Conflicting Accounts, competing Hypotheses, or
a Statement of Disagreement do not independently become integrity conflicts.

A closed code-owned mapping distinguishes explicit
`portia_integrity_conflict` from `portia_integrity_review_required`. Unknown
future finding codes fail closed rather than being classified by substring or
label similarity.

Acknowledging a finding records review evidence; it does not resolve or hide the
finding. Presentation suppression reuses Issue #47 authority. An effective
accepted suppression may remove a suppressible finding from the routine native
surface, but suppression does not repair canonical state, release Quarantine,
or authorize current use. Findings whose accepted severity/effects make
suppression impermissible remain visible/operative.

## Recovery attention

Operation Journal enumeration remains storage-owned and identity-validated.
`RecoveryWorkflowService.assess()` supplies recovery meaning. Current
nonterminal recovery dispositions may produce `portia_recovery_required`.
Completed/compensated/aborted operations that are terminal-consistent do not
remain permanent historical attention.

Attention queries never restore pointers, resume operations, compensate writes,
or otherwise perform recovery.

## Quarantine attention

`QuarantineGuard.active_records()` is the current containment authority. Active
Quarantine produces `portia_quarantine_active`; released/superseded historical
Quarantine does not.

Quarantine remains a separate fact from an underlying Integrity Finding and
from domain lifecycle. Native items include only opaque Quarantine identity and
bounded reason/effect categories. They do not expose journal payloads, locks,
staging paths, free-form detail, or private record content. Queries never
release Quarantine.

## Derived-state staleness

Derived attention uses a closed registry. The current production registry
contains `active_integrity_finding_index` at operation scope.

Freshness is evaluated through `DerivedStore` source-snapshot authority.
Filesystem modification time and record age are not semantic freshness.
Optional missing derived state is ordinary absence. A selected generation whose
accepted source snapshot is stale can produce `portia_derived_state_stale`.
Corrupt or unavailable selected derived state remains a failure/partial case,
not a stale finding.

Reads never install or rebuild a derived generation.

## Support Process attention

For current nonterminal Support Processes, `review_on` is the explicit
date-driven review trigger. Exact date semantics produce due/overdue codes.
Planning or paused state alone is not attention.

Dependency attention reuses `DependencyWorkflowService.evaluate_gate(...)`.
`review_required`, `unsatisfied`, and `indeterminate` remain distinguishable in
bounded structural reason codes, including required/advisory distinctions.
Attention does not infer support effectiveness or recommend changing,
intensifying, reducing, or ending support.

## Deterministic ordering

Definition order is stable presentation order only. Within a code, timing and
exact class/work/source identity provide deterministic tie-breaking. Student
identity, alleged conduct, narrative, record age, and technical severity are
not used to rank students or teacher priorities.

## Privacy boundary

Native attention is deliberately low-density. It may carry exact class/work
navigation and safe opaque technical identities, but it does not duplicate
student narrative, Account/Observation/Communication content, Contact Points,
recipient arrays, raw integrity evidence, raw Operation Journals, locks,
staging paths, fingerprints, source paths, removed payload, or absolute
filesystem paths.

No behavior/risk/urgency/priority score is introduced. No student ranking,
predictive intervention recommendation, or automatic discipline/support
decision is introduced.

Teacher navigation that needs richer student context belongs in the existing
Issue #48 privacy-minimized student view rather than being copied into the
attention item.

## Read-only boundary

Attention is derived and noncanonical. Querying does not create or replace:

```text
canonical Portia records
Operation Journal revisions
Finding Acknowledgements
Finding Suppressions
Quarantine revisions
derived generations
notification/menu state
```

The same source state plus the same explicit query produces deterministic
semantic output.

## Issue boundaries

Issue #49 does not implement the Issue #50 teacher menu or navigation layout.
It does not implement Issue #51 export. It does not register the Issue #52 Core
module-operations/readiness provider; Issue #52 can adapt the native taxonomy
without re-deriving Portia semantics. Issue #49 also does not absorb Issue #53's
full installed Event-to-Follow-Up acceptance story.

It adds no sibling PDS runtime dependency, background polling, notifications,
automatic recovery, automatic Quarantine release, automatic acknowledgement or
suppression, automatic derived rebuild, behavior scoring, student ranking, or
legal/compliance determination.

See `docs/validation/issue-49-attention-query-validation.md` for observed
qualification evidence.
