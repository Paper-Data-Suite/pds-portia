# Portia Architecture Decision Records

This index is navigation and Issue #23 audit metadata. The ADR bodies remain authoritative for their accepted decisions.

Audit dispositions are not new runtime statuses. They record the final foundations-audit conclusion for each accepted ADR.

| ADR | Title | Repository status | Issue #23 audit disposition | Principal area | File |
| --- | --- | --- | --- | --- | --- |
| 0001 | Separate observations, interpretations, and determinations | Accepted | `accepted` | Evidence/judgment separation | `0001-separate-observations-interpretations-and-determinations.md` |
| 0002 | Define Portia module boundaries | Accepted | `accepted` | Suite ownership and module scope | `0002-define-portia-module-boundaries.md` |
| 0003 | Adopt teacher-local initial deployment | Accepted | `accepted` | Teacher-local authority and deployment scope | `0003-adopt-teacher-local-initial-deployment.md` |
| 0004 | Define Portia identity, ownership, and storage | Accepted | `accepted` | Identity, work ownership, canonical paths | `0004-define-portia-identity-ownership-and-storage.md` |
| 0005 | Define Event and Participant domain model | Accepted | `accepted` | Event and participant semantics | `0005-define-event-and-participant-domain-model.md` |
| 0006 | Define Event Participant Role domain model | Accepted | `accepted` | Role semantics without fault inference | `0006-define-event-participant-role-domain-model.md` |
| 0007 | Define shared reference, targeting, and relationship contracts | Accepted | `accepted` | Exact references, targets, relationships | `0007-define-shared-reference-targeting-and-relationship-contracts.md` |
| 0008 | Define lifecycle, correction, and migration contracts | Accepted | `accepted` | Lifecycle, correction, disagreement, migration | `0008-define-lifecycle-correction-and-migration-contracts.md` |
| 0009 | Define coordinated persistence, recovery, and derived-index contracts | Accepted | `accepted_with_nonblocking_implementation_concern` | Operation/recovery and derived state | `0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md` |
| 0010 | Define Actor Directory domain model and lifecycle | Accepted | `accepted` | Teacher-local recurring non-roster identity | `0010-define-actor-directory-domain-model-and-lifecycle.md` |
| 0011 | Define Account and Observation domain models | Accepted | `accepted` | Attributed source evidence | `0011-define-account-and-observation-domain-models.md` |
| 0012 | Define Review, Classification, Hypothesis, and Determination domain models | Accepted | `accepted` | Human judgment and authority | `0012-define-review-classification-hypothesis-and-determination-domain-models.md` |
| 0013 | Define Response and Communication domain models | Accepted | `accepted` | Response/communication separation | `0013-define-response-and-communication-domain-models.md` |
| 0014 | Define Support Process, Support, Intervention, Implementation, and Fidelity contracts | Accepted | `accepted` | Planning/execution/fidelity separation | `0014-define-support-process-support-intervention-implementation-and-fidelity-contracts.md` |
| 0015 | Define Follow-Up, Outcome, Reentry, and Repair domain models | Accepted | `accepted` | Evaluation and post-event semantics | `0015-define-follow-up-outcome-reentry-and-repair-domain-models.md` |
| 0016 | Define paper-assisted capture, PDS2 routing, and import contracts | Accepted | `accepted_with_nonblocking_implementation_concern` | Paper/import provenance and human review | `0016-define-paper-assisted-capture-pds2-routing-and-import-contracts.md` |
| 0017 | Define privacy projections, redaction, export, retention, and Sunset boundaries | Accepted | `accepted_with_nonblocking_implementation_concern` | Privacy/export/retention and future orchestration boundary | `0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md` |

## Audit disposition meanings

- `accepted` — the decision remains internally consistent and suitable to govern implementation.
- `accepted_with_nonblocking_implementation_concern` — the architecture is accepted, but the executable milestone must preserve a named runtime constraint.
- `superseded`, `deprecated`, `rejected`, and `requires_new_decision` are available audit dispositions but are not required by the current Issue #23 review.

Issue #23 does not add ADR 0018 because the audit found no genuinely new foundational architectural decision. The three active-documentation blockers found by the audit are reconciliations to existing accepted decisions, not new architecture.
