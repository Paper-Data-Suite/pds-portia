# Issue #16 Final Repository Drift Check

**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**Date:** 2026-08-09
**Branch:** `16-review-classification-hypothesis-determination-domain-models`
**Checkpoint:** final pre-close integration review

## Verified anchors

```text
pds-portia branch:
f83c8368b7eff86d8527c01cd67cf13ac254522c
test: add judgment shared infrastructure compatibility

pds-portia main:
35df69904cff3c696876f04e208bbe704bab3e97
15 account observation domain models (#28)

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

At this checkpoint the Issue #16 branch is 8 commits ahead of Portia `main`
and 0 behind. Portia `main` and Core remain at the same anchors recorded at the
start/pre-ADR checkpoints. No upstream contract drift requires an Issue #16
wire-shape change.

## Ownership and authority boundary

Core remains authoritative for workspace/class identity, class-qualified roster
identity, PDS2 routing/registration, retained scan provenance, and suite-level
module/publication infrastructure.

Portia owns Event-local Review, Classification, Hypothesis, and Determination
identity and semantics. Portia may preserve represented decision-maker identity,
authority claims/evidence, and policy/process basis, but the teacher-local
deployment does not itself confer or authenticate institutional authority.

No Core change is required.

## Existing Portia contracts retained unchanged

Compatibility is proven without changing the wire shape of:

```text
event@2
event_participant@3
event_participant_role@3
account@1
observation@1
portia_target_ref@1
local_record_ref@1
exact_local_record_ref@1
exact_portia_work_record_ref@1
module_work_record_ref@1
represented_human_attribution@1
source_artifact_ref@1
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

Issue #16 adds:

```text
portia_review_id@1
portia_classification_id@1
portia_hypothesis_id@1
portia_determination_id@1
judgment_evidence_ref@1
review@1
classification@1
hypothesis@1
determination@1
```

No dedicated exact judgment-reference families and no judgment-specific
lifecycle/operation/derived forks are needed.

## Sibling-module classification

Typed sibling-PDS references are contextual locators only. A sibling record does
not become behavioral truth, credibility, decision authority, or proof merely
because Portia can reference it. No sibling public-contract change is required.

## Drift classification

```text
pds-portia main: no drift
pds-core main: no drift
shared Portia contracts: reuse proven; no version bump
sibling modules: no required contract change
future Support-Process/FBA ownership: deferred to #18
Response/Communication semantics: deferred to #17
```

Run one final branch-vs-main comparison immediately before merge.
