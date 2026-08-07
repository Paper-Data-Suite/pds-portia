# Issue #15 Initial Repository Checkpoint

**Issue:** `#15 — Define Account and Observation domain models`
**Date:** 2026-08-07
**Branch:** `15-account-observation-domain-models`
**Checkpoint type:** Initial pre-ADR repository review

## Branch state

The Issue #15 branch was confirmed identical to `main` at the initial checkpoint:

```text
base: main
head: 15-account-observation-domain-models
status: identical
ahead_by: 0
behind_by: 0
```

The shared Portia commit anchor is:

```text
ed09e6779281a23be05124afdb266579d2d560de
```

## PDS Core anchor

Reviewed Core anchor:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
```

Core v0.6 remains authoritative for workspace selection, class identity and metadata, class-qualified roster-student identity, PDS2 routing identity, route registration, retained source-scan provenance, and generic module references.

Core does not define Portia Account identity, Portia Observation identity, source credibility, Event evidence semantics, `reported_involved` Role semantics, Observation interpretation, or behavior findings.

Initial classification:

```text
no Core change required
```

## Portia contracts reviewed

The initial checkpoint reviewed:

```text
event@2
event_participant_role@3
portia_target_ref@1
local_record_ref@1
exact_local_record_ref@1
creation_source@1
attribution_agent@1
statement_of_disagreement@1
dependency@1
lifecycle_transition@1
portia_local_work_target@1
module_work_record_ref@1
Actor Directory design and ADR 0010
```

## Existing Account/Observation placeholders

Event Participant Role v3 already supports basis entries whose local record kind is `account` or `observation`. Those are structural placeholders only; no canonical public Account or Observation record currently exists.

Role v3 already establishes:

```text
reported_involved proposal
    -> requires source-oriented basis

reported_involved active/superseded
    -> requires account_ref
```

Issue #15 must make those references semantically valid without mutating the published Role v3 wire shape unless a genuine compatibility problem is found.

## Initial architecture findings

1. Account and Observation should be Event-local child records.
2. `portia_target_ref@1` already provides the correct Event/Participant target family.
3. The represented source or observer must remain distinct from `created_by`.
4. The source/observer need not be an Event Participant.
5. Account needs explicit information-origin semantics.
6. Quote and summary require structural separation.
7. Observation should carry observable/measurable content, not interpretation.
8. Positive, neutral, and potentially concerning observations can use one neutral record model.
9. Account retraction requires source evidence and must not be a teacher-only status toggle.
10. Active `reported_involved` should require an eligible Account whose target is the same Participant or a Participant set containing that Participant.
11. Paper/import provenance does not substitute for source attribution.
12. Paper/import evidence should begin proposed and require local review.
13. Existing class/work-scoped lifecycle and correction infrastructure should be reusable.
14. Existing same-work operational targeting should be reusable.
15. Account and Observation must not automatically create findings.

## Initial drift classification

```text
pds-core:
    no immediate contract change

pds-portia:
    new Account/Observation public contracts required

event_participant_role@3:
    preserve published wire shape if possible;
    tighten Account eligibility through new contracts and application rules

shared lifecycle/operations:
    reuse expected;
    prove through compatibility tests

other sibling modules:
    no concrete initial public-contract implication
```

## Required later checkpoints

Before ADR 0011 is accepted:

1. re-check `pds-portia/main`;
2. re-check `pds-core/main`;
3. inspect any sibling public contract that newly affects source attribution, observer identity, provenance, attachments, or consumer eligibility;
4. classify drift;
5. reconcile the design before freezing schemas.

Repeat the drift check immediately before Issue #15 closes.
