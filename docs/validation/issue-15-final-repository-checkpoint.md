# Issue #15 Final Repository Drift Check

**Issue:** `#15 — Define Account and Observation domain models`
**Date:** 2026-08-07
**Branch:** `15-account-observation-domain-models`
**Checkpoint:** final pre-close integration review

## Verified anchors

```text
pds-portia branch:
2ce756f83cab5bedcbc00c931dedd370c9c68c53
test: add account observation operational compatibility

pds-portia main:
ed09e6779281a23be05124afdb266579d2d560de
14 actor directory domain model lifecycle (#27)

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

At this checkpoint the Issue #15 branch was 8 commits ahead of Portia `main`
and 0 behind. Portia `main` and Core remained unchanged throughout Issue #15
implementation, so no upstream contract reconciliation was required.

## Ownership boundary

Core remains authoritative for workspace/class identity, class-qualified roster
student identity, PDS2 route identity/registration, retained scan provenance,
and generic cross-module/publication infrastructure.

Portia owns Account/Observation identity and semantics, Event-local
source/observer targeting, `reported_involved` Account eligibility,
source-evidenced Account retraction, Observation method/measurement semantics,
Portia lifecycle/current-use rules, and Portia operational/derived
compatibility.

No Core change is required.

## Existing Portia contracts retained unchanged

Compatibility was proven without changing the wire shape of:

```text
event@2
event_participant@3
event_participant_role@3
portia_target_ref@1
local_record_ref@1
exact_local_record_ref@1
portia_local_work_target@1
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
exceptional_removal@1
operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

Role v3 therefore needs no v4 for Issue #15.

## Sibling-module classification

Synthetic typed sibling-module references demonstrate the public reference
boundary only. They do not claim runtime integration with Quillan, Scoreform,
Concord, Meridian, or another sibling.

No sibling public-contract change was required.

## Drift classification

```text
pds-portia main: no drift
pds-core main: no drift
shared Portia contracts: reuse proven; no version bump
sibling modules: no required contract change
```

Run one final branch-vs-main comparison immediately before merge.
