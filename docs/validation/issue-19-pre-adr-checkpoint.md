# Issue #19 Pre-ADR Repository Checkpoint

**Status:** Pre-ADR drift and architecture audit complete
**Issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`
**Date:** 2026-08-12
**ADR:** `0015`

## Exact Repository Anchors

Immediately before ADR 0015 publication:

```text
pds-portia/main
0d08495557721681b11d081e91c8b416a556df8a

pds-portia/19-follow-up-outcome-reentry-repair-domain-models
7f1ce8c

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c
```

Portia main, Core main, and Meridian main are unchanged from the Issue #19
initial checkpoint.

## Slice 1 Remote Verification

Remote comparison:

```text
base:
0d08495557721681b11d081e91c8b416a556df8a

head:
7f1ce8c

status:
ahead

ahead:
1

behind:
0
```

The only changed files are:

```text
docs/design/portia-follow-up-outcome-reentry-repair-domain-models.md
docs/validation/issue-19-initial-repository-checkpoint.md
```

No schema or fixture drift was introduced by Slice 1.

## Authoritative Local Baseline

Recorded on the exact Issue #19 checkout:

```text
Ran 762 tests in 93.403s
OK
```

The pre-ADR slice changes documentation only.

## ADR Number Availability

Immediately before publication:

```text
docs/decisions/0015-define-follow-up-outcome-reentry-and-repair-domain-models.md
```

returned not found.

ADR 0015 is therefore available.

## Published Evidence Audit

### Account v1

`account@1` is explicitly Event-local.

Its schema requires:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

Its description defines Account as attributed source evidence concerning a
target inside the containing Event.

Application invariants include:

```text
parent_event_resolution
target_same_event
relation_same_event
no_automatic_finding
```

### Observation v1

`observation@1` is explicitly Event-local.

Its schema requires:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

Its description defines Observation as directly observable/counted/timed/
recorded/measured evidence concerning a target inside the containing Event.

Its application invariants include Event ownership and same-Event targeting.

Observation already has a rich measurement model; #19 should not duplicate that
model inside Outcome.

## Dual-Owner Precedent

`communication@1` already establishes an accepted Portia-work-local envelope:

```text
work_kind = event | support_process
work_id
class_id
```

with application owner resolution.

It became Support-Process-current-use eligible during Issue #18 without
changing its wire contract.

This is the direct structural precedent for dual-owner #19 child records and
for Account/Observation v2 owner generalization.

## Exact Reference Audit

`exact_portia_work_record_ref@1` already preserves:

```text
exact work identity
exact child-record kind
exact record ID
exact contract version
```

It is sufficient for #19 cross-work evidence/context/history.

No generic #19 exact-reference contract is needed.

## Target Audit

Existing closed target families remain sufficient:

```text
Event:
portia_target_ref@1

Support Process:
support_process_target_ref@1
```

A dual-owner schema can select the correct target family by `work_kind`.

No generic #19 target family is needed.

## Evidence Ownership Incompatibility

Concrete legitimate Support Process examples include:

```text
weekly direct count during routine support monitoring
timed observation during a planned support period
student check-in perspective
family perspective about current support
observed replacement-skill opportunity
review-period measurement
```

None necessarily represents an Event.

The current choices would otherwise be:

1. fabricate an Event;
2. place raw source evidence inside Outcome;
3. silently mutate v1;
4. duplicate evidence semantics under new family names.

All four are rejected.

The accepted additive remedy is:

```text
account@2
observation@2
```

with:

```text
work_kind = event | support_process
owner-conditioned work_id
owner-conditioned target
```

and preserved v1 evidence semantics.

## Versioning Precedent

Portia already preserves published prior contracts while adding new explicit
version paths, including Event v2 and Event Participant/Role later versions.

Account/Observation v2 therefore follows established immutable-versioning
practice rather than mutating v1 `$id` values.

## Research Reconciliation

Portia's completed behavior-support research requires:

- support-process monitoring rather than incident-count-only tracking;
- separate observation/evidence and evaluation;
- student/family perspective as first-class records;
- outcome measurement alongside implementation fidelity;
- restorative/reparative and reentry support;
- explicit follow-up owner/due work;
- missing-data/coverage awareness;
- no moral/disciplinary automation.

ADR 0015 is consistent with that research.

## Core / Meridian Boundary

Core v0.6 still provides future:

```text
intervention_record_set
intervention_history
intervention_status
intervention_outcomes
```

while leaving native semantics to producer modules.

Meridian remains downstream consumer context and has no Portia adapter.

ADR 0015 therefore stabilizes native Portia semantics only.

No producer profile, manifest, Publication Record, Academic Work Registration,
academic result, Score, standards rating, Grade, or automatic publication is
introduced.

## Accepted Architecture Summary

ADR 0015 accepts:

```text
Account v2 / Observation v2
  Event or Support Process source evidence

Event or Support Process owner
  ├─ Follow-Up
  ├─ Outcome
  ├─ Reentry
  └─ Repair
```

with:

```text
Follow-Up ID: fup_
Outcome ID:   out_
Reentry ID:   ren_
Repair ID:    rpr_
```

It reuses existing:

```text
target families
exact work/record refs
represented-human attribution
Support Process Participants
lifecycle/correction/history
migration/removal
operation/lock
Quarantine/Integrity Finding
source snapshot / derived metadata / current pointer
```

## Public Contracts Not Authorized

ADR 0015 does not authorize:

```text
outcome_evidence_ref@1
repair_action@1
repair_participant@1
progress@1
effectiveness@1
closure@1
success@1
engagement@1
compliance@1
remorse@1
forgiveness@1
readiness@1
case@1
```

## Implementation Consequence

Because the evidence-owner incompatibility is real, the next implementation
slice must be:

```text
Account v2 + Observation v2
```

before Follow-Up/Outcome schemas depend on them.

No #19 domain schema should force fake Event creation.

## Pre-ADR Conclusion

No upstream drift blocks ADR 0015.

The accepted design is additive, preserves published v1 contracts, resolves the
Support Process evidence gap explicitly, and keeps:

```text
source evidence
≠ evaluation

implementation
≠ fidelity
≠ outcome

workflow completion
≠ success

record linkage
≠ causation
```

ADR 0015 can be accepted without reopening Core, Meridian, or prior Portia
architectural decisions.
