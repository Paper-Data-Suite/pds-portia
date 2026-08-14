# Portia Import Proposal and Human Review

## Status

Issue #20 Slice 8 design checkpoint.

This document defines the staging layer between the durable structured-import source history established by Slice 7 and later coordinated canonical materialization.

## Governing boundary

The import workflow remains:

```text
exact source snapshot
→ Import Batch
→ Import Source Record
→ Import Proposal
→ attributable Import Review
→ later canonical materialization when allowed
```

The following are deliberately unequal:

```text
Import Source Record ≠ Import Proposal
Import Proposal ≠ accepted mapping
accepted Import Review ≠ canonical Portia record
source-system assertion ≠ Portia judgment
source-side identity string ≠ Portia person identity
```

Paper staging contracts are not reused. `capture_proposal@1` and `capture_review@1` carry Page Record / interpretation semantics that do not apply to structured imports.

## Public contracts

Slice 8 adds:

```text
portia_import_proposal_id@1  iprp_
import_proposal@1

portia_import_review_id@1    irev_
import_review@1
```

`irev_` is intentionally distinct from both:

- `rvw_`: canonical Event-local domain Review;
- `crev_`: paper Capture Review.

An Import Review is staging review, not the behavioral/evaluative Review domain family.

## Proposal identity and 0..N mapping

One Import Source Record may produce zero, one, or many logical proposals.

Each proposal therefore carries two different identity concepts:

1. `proposal_id` — opaque Portia persistence identity (`iprp_`);
2. `proposal_key` + `proposal_identity_digest` — stable logical replay evidence under the exact source record and exact mapping configuration.

`proposal_key` is deterministic within the exact mapping profile. It may distinguish, for example, an Event proposal from an Account proposal generated from the same source record. It must not be derived from:

```text
row number
proposal array position
source-record array position
filename
run order
random local ordering
```

Application validation recomputes `proposal_identity_digest` from a versioned canonical encoding of at least:

- exact Import Source Record identity;
- exact Import Batch import/mapping identity;
- `proposal_key`;
- target record kind/version/context;
- and field bindings.

The opaque `proposal_id` and timestamps are not logical replay inputs.

Same exact source record + same exact mapping + same logical proposal key must reconcile to the same logical proposal rather than produce a duplicate proposal or canonical record.

## Target semantics

A proposal identifies one possible Portia target family and exact contract version.

The closed record-family vocabulary follows the behavior/support families already accepted for paper capture:

```text
Event / Event Participant / Role
Account / Observation
Review / Classification / Hypothesis / Determination
Response / Communication
Support Process / Participant
Support Need / Goal
Support / Intervention / Implementation / Fidelity
Follow-Up / Outcome / Reentry / Repair
```

An import proposal does not add Actor as a target family. Imports must not silently manufacture or merge person identity.

Target context is one of:

```text
new_work
existing_work
existing_record
```

`new_work` is structurally restricted to Event and Support Process roots. Exact existing references never silently follow later correction, migration, consolidation, ownership correction, or successor relationships.

## Field bindings

A proposal maps source fields to target-contract paths through one of three value modes:

### `source_value`

The exact value remains in the immutable Import Source Record. The proposal references the source field by key and does not copy the value.

### `transformed_candidate`

The exact mapping profile deterministically produced a value different from the literal source representation—for example a parsed timestamp or exact code-table translation.

The transformed value is preserved in the proposal because it is itself part of the mapping candidate requiring review/history.

It remains a candidate, not truth.

### `human_resolution_required`

Automation cannot safely supply a value. This mode carries no candidate value.

Typical examples include ambiguous person identity or a mapping whose meaning would require a local judgment.

Missingness or unresolved identity must not be converted into `null`, `false`, `no`, or a fabricated identifier merely to satisfy a target schema.

## Identity safeguards

Software must not silently establish person identity from:

```text
similar name
similar email
row position
nearby labels
roster position
source-system display text
fuzzy similarity scores
```

An exact source identifier may be mapped only under the exact mapping profile and authorization rules. If resolution remains ambiguous, the proposal must require human resolution.

Human correction can explicitly supply the reviewed target value, but the original Import Source Record and automated proposal remain preserved.

## Judgment safeguards

Import Proposal mapping must not translate source labels automatically into Portia human judgments such as:

```text
Classification
Hypothesis
Determination
fault or intent
severity judgment
Response appropriateness
Support recommendation
Fidelity
Outcome
recurrence failure
Reentry completion
Repair agreement/remorse/forgiveness/restoration
```

A source system may assert words resembling these concepts. Those words remain source assertions until the appropriate Portia human-attributed domain workflow establishes any corresponding Portia judgment.

Import staging review of a transcription/mapping does not replace those domain judgment layers.

## Attributable human review

`import_review@1` records the substantive human review of one exact Import Proposal.

The closed dispositions are:

```text
accepted
corrected_and_accepted
rejected
unresolved
```

### `accepted`

The exact proposal is accepted unchanged for the next workflow gate. No field-review payload or reason code is needed.

This means only that the reviewer accepts the staging mapping. It does not mean the source is true, authoritative, credible, or sufficient for a judgment-bearing domain record.

### `corrected_and_accepted`

At least one field is explicitly corrected by the human reviewer. The review preserves `confirmed_value`; it does not overwrite the original source field or transformed candidate.

Other fields may be explicitly marked `accept_candidate` in the same review.

### `rejected`

The proposal is rejected as a staging mapping and requires at least one reason code.

Rejection does not delete or invalidate the Import Source Record, Import Batch, source snapshot, or earlier canonical Portia records.

### `unresolved`

At least one exact target path is explicitly `leave_unresolved`.

Unresolved does not mean false/no/declined/unidentified-confirmed or any other negative domain value.

## Review history

Review correction or reversal never mutates an earlier review.

```text
review_sequence = 1
→ no predecessor

review_sequence > 1
→ exact predecessor_review_id required
```

Current staging disposition is a derived application view over immutable review history. A mutable `latest` flag is not authoritative.

## Provenance and materialization boundary

No Slice 8 contract writes canonical Portia records.

An accepted Import Review is merely eligible input to the later import-materialization gate. That later gate must be idempotent and coordinated with the existing operation journal/lock infrastructure.

When an eligible canonical record is created from reviewed import data, its creation provenance is:

```text
creation_source.type = import
```

never `paper_capture`.

Import provenance is historical source lineage; it does not grant source authority or truth.

## Replay and mapping changes

Unchanged replay must reconcile stable proposal identity and preserved review/materialization history.

If source content or mapping changes:

- preserve the earlier Import Source Record;
- preserve the earlier Import Proposal;
- preserve all review history;
- create the appropriate later proposal history;
- do not silently rewrite an already accepted canonical record.

If a source record disappears from a later batch, no proposal or canonical deletion is inferred.

## Quarantine boundary

Ordinary rejected, unresolved, or identity-ambiguous import proposals belong in normal review history, not Quarantine.

Quarantine remains reserved for exceptional integrity failures such as broken lineage, contradictory immutable identity, unknown mapping version, or duplicated canonical materialization that cannot be safely reconciled.

## Slice boundary

Slice 8 ends after attributable Import Review.

The next materialization slice must address:

```text
accepted Import Review
→ deterministic coordinated operation
→ canonical writes when allowed
→ creation_source.type = import
→ exact import-source linkage
→ crash/retry reconciliation
→ no duplicate canonical records
```
