# Issue #16 Initial Repository Checkpoint

**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**Date:** 2026-08-07
**Branch:** `16-review-classification-hypothesis-determination-domain-models`
**Checkpoint type:** Initial, pre-public-contract design checkpoint

## 1. Purpose

This checkpoint records the repository state reviewed before Issue #16 introduces any new public schema, identifier, lifecycle vocabulary, or judgment record family.

The Issue #16 branch is architecture-first. The initial slice adds only:

```text
working design documentation
repository checkpoint documentation
```

No public schema is created in this slice.

## 2. Portia Baseline

Reviewed repository:

```text
Paper-Data-Suite/pds-portia
```

Reviewed `main` commit:

```text
35df69904cff3c696876f04e208bbe704bab3e97
```

Commit:

```text
15 account observation domain models (#28)
```

The Issue #16 branch:

```text
16-review-classification-hypothesis-determination-domain-models
```

was confirmed identical to `main` at this checkpoint:

```text
ahead:  0
behind: 0
```

Issue #15 is therefore fully merged into the Issue #16 baseline.

## 3. Core Baseline

Reviewed repository:

```text
Paper-Data-Suite/pds-core
```

Reviewed `main` commit:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
```

Commit:

```text
Document Core integration contract and prepare v0.6.0 (#176)
```

Core remains authoritative for workspace resolution, class identity, rosters, roster-scoped student identity, module-qualified work identity, PDS2 routing, route registration, retained scan/source provenance, shared publication infrastructure, and safe shared path conventions.

Core does not currently provide institution-wide staff identity, role-based authorization, decision-maker authentication, district policy adjudication, or institutional case-management authority.

Issue #16 must not silently manufacture those platform capabilities inside Portia.

No Core contract change is required for the initial Issue #16 architecture.

## 4. Accepted Portia Preconditions

The current baseline already provides:

```text
Event v2
Event Participant v3
Event Participant Role v3
Work Relationship v2

Actor Directory v1
Account v1
Observation v1

shared exact references
Event-local targeting
lifecycle transitions
lifecycle-history correction
Amendment
Statement of Disagreement
Dependency
migration
ownership correction
exceptional removal

Operation Journal
Operation Lock
Quarantine
Integrity Finding

source snapshots
derived-generation metadata
current pointers
```

Issue #16 should consume those contracts rather than redefining them.

## 5. Evidence Boundary Entering Issue #16

ADR 0011 establishes:

```text
Account
= attributed human source contribution

Observation
= direct human or instrumented observable information
```

Neither record establishes:

```text
credibility
corroboration
intent
severity
policy violation
diagnosis
behavioral function
risk
Classification
Hypothesis
Determination
```

Issue #16 therefore starts at the human interpretation layer.

The new records must reference evidence without rewriting source evidence or turning evidence counts into proof.

## 6. ADR 0001 Status

ADR 0001 remains an important conceptual precursor:

```text
Separate Observations, Interpretations, Classifications, and Determinations
```

Its core separation remains aligned with current Portia direction.

However, ADR 0001 predates the accepted teacher-local deployment boundary, shared reference contracts, shared lifecycle/correction contracts, coordinated persistence contracts, Actor Directory, and Account/Observation contracts.

Issue #16 will therefore create ADR 0012 rather than silently rewriting ADR 0001.

ADR 0012 must explicitly reconcile which ADR 0001 concepts remain governing principles and which are refined by current architecture.

## 7. Initial Cross-Repository Classification

### `pds-portia`

```text
required contract work
```

Review, Classification, Hypothesis, and Determination do not yet have canonical public contracts.

### `pds-core`

```text
no immediate contract change
```

Core supplies infrastructure but not institutional judgment authority.

### Sibling modules

```text
no immediate contract change
```

Existing typed module-work-record references are sufficient for initial contextual evidence references.

Sibling records remain authoritative in their originating modules.

A ScoreForm result, Quillan review, Concord review, or other sibling record must not silently become a Portia judgment.

## 8. Initial Architectural Risks

The first design pass must resolve these risks before any public `$id` is published.

### 8.1 Authority inflation

Risk:

```text
Actor category or title
→ incorrectly treated as decision authority
```

Required boundary:

```text
human identity
≠ authority
```

### 8.2 Local/institutional conflation

Risk:

```text
teacher-local judgment
→ exported or displayed as institutional finding
```

Required boundary:

```text
teacher_local
≠ recorded_institutional
```

### 8.3 Evidence-count inflation

Risk:

```text
repeated Accounts
→ automatically treated as corroboration or proof
```

Required boundary:

```text
record count
≠ evidence weight
```

### 8.4 Classification-as-identity

Risk:

```text
Event-local category
→ durable student label
```

Required boundary:

```text
Classification target
= Event context / Event Participant context
```

not underlying person identity.

### 8.5 Hypothesis hardening

Risk:

```text
tentative explanation
→ fact / diagnosis / determined function
```

Required boundary:

```text
Hypothesis remains tentative
```

### 8.6 Automated adjudication

Risk:

```text
Observation / Classification / Hypothesis
→ automatic Determination
```

Required boundary:

```text
substantive judgment remains human
```

### 8.7 Reversal by overwrite

Risk:

```text
later decision
→ prior Determination silently rewritten
```

Required boundary:

```text
new decision + exact predecessor history
```

### 8.8 Sensitive-text duplication

Risk:

```text
judgment rationale
→ copied into operational diagnostics / derived indexes
```

Required boundary:

```text
privacy-minimized operational metadata
```

## 9. Initial Proposed Contract Families

The working design evaluates:

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

These are proposals only at this checkpoint.

No schema-catalog reservation is made in Slice 1.

No `$id` is published in Slice 1.

## 10. Drift Classification

Current drift classification:

```text
Portia main:
    no drift from Issue #16 branch

Core:
    no relevant new drift

Sibling modules:
    no concrete public-contract implication
```

The next required drift check occurs immediately before ADR 0012 acceptance.

## 11. Next Step

The next bounded slice should:

1. review and freeze the open pre-ADR decisions in the working design;
2. recheck Portia and Core drift;
3. add the pre-ADR checkpoint;
4. accept ADR 0012;
5. still avoid public schema publication until the architecture is frozen.

Only after ADR 0012 is accepted should identifier and evidence-reference schemas begin.
