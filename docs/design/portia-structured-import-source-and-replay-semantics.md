# Portia Structured Import Source and Replay Semantics

Issue: #20 — Define paper-assisted capture, PDS2 routing, and import contracts

Slice: 7 — Import Batch + Import Source Record + stable replay identity

Status: implementation slice pending ADR 0016 consolidation

## Purpose

This slice establishes the source-history half of Portia structured imports. It deliberately stops before import proposals, human review, or canonical materialization.

The governing boundary is:

```text
source snapshot
→ Import Batch
→ Import Source Record
→ later mapping/proposal/review
→ later canonical materialization when allowed
```

and never:

```text
source row = Event
source label = Portia judgment
missing later row = deletion
same-looking person = same Actor
import timestamp = Event time
```

Paper-assisted capture and structured import are separate workflows. Import does not use Capture Batch, Page Target, Page Record, Paper Interpretation, Capture Proposal, Capture Review, or Core PDS2 route/retained-source identity.

## Public contracts introduced

```text
portia_import_batch_id@1
import_batch@1
portia_import_source_record_id@1
import_source_record@1
```

Identifiers use opaque Portia-owned prefixes:

```text
ibat_   Import Batch
isrc_   Import Source Record
```

The identifiers do not encode class, person, student, source record key, filename, date, mapping result, domain family, or review state.

A separate Import Source Record ID is justified because later immutable proposals, reviews, materialization receipts, integrity findings, and audit/history surfaces need an exact Portia-local reference to the source-side observation. The opaque ID remains distinct from the source-system key.

## Import Batch semantics

One Import Batch represents one bounded import attempt against:

1. one class scope;
2. one exact source/profile identity;
3. one exact source byte snapshot;
4. one exact mapping profile/version/configuration digest.

It is operational history, not a behavior-domain work.

Creating or completing an Import Batch does not establish that:

- an Event occurred;
- a source row corresponds to one Portia Event;
- a person identity was resolved;
- a Classification or Determination applies;
- a Response or Support occurred;
- an Implementation occurred;
- an Outcome, Reentry, or Repair exists;
- or any source assertion is true or institutionally authoritative.

### Source profile

`source_profile` preserves:

```text
source_system_id
profile_id
profile_version
optional display_label
```

The profile defines the exact extraction/keying rules used before Portia mapping. A later profile version is a different historical interpretation surface; it does not rewrite older batches.

### Exact source snapshot

`source_snapshot` contains one explicit locator plus an exact `content_fingerprint` and observation time.

Closed locator forms are:

```text
workspace_file
external_snapshot
opaque_snapshot
```

The locator is diagnostic/provenance context. The exact fingerprint is the byte-snapshot evidence. A later file at the same path, a reused export name, modification time, or a display label does not replace the stored fingerprint.

Portia does **not** reuse `source_snapshot@1` here. That published contract already means a deterministic bounded inventory for derived-projection generation. Reusing it for an imported source file/API snapshot would collapse two distinct meanings under one contract.

### Exact mapping profile

`mapping_profile` preserves:

```text
mapping_profile_id
mapping_version
mapping_digest
```

The digest binds the exact mapping configuration bytes/representation. `current`, `latest`, same-name lookup, or silently upgraded configuration is not acceptable historical identity.

### Import identity digest

`import_identity_digest` is deterministic logical identity evidence for the source+mapping inputs. Application validation recomputes it using a versioned canonical encoding of at least:

```text
class_id
source_profile
exact source locator identity
exact source fingerprint
mapping_profile_id
mapping_version
mapping_digest
```

It excludes:

```text
import_batch_id
attempt timestamps
status
failure codes
run order
filename when filename is only a display label
```

`import_batch_id` identifies the bounded attempt. `import_identity_digest` lets Portia recognize that two attempts processed the same logical source+mapping inputs.

## Replay classification

An Import Batch may preserve an exact previous-batch comparison:

```text
replay_same_source_same_mapping
changed_source_same_mapping
same_source_changed_mapping
changed_source_and_mapping
```

The label is not trusted blindly. Application validation resolves the previous batch in the same authorized class scope and recomputes the relationship from exact profile/fingerprint/mapping values.

### Same source + same mapping

A repeated attempt may remain useful operational history, but downstream processing is idempotent:

```text
same logical source input
+ same mapping
≠ duplicate logical proposals
≠ duplicate canonical records
```

Later proposal/materialization work must reconcile stable import identity before creating anything new.

### Changed source

Changed source bytes create new source history. Earlier batches and source records remain intact.

### Changed mapping

The same source bytes mapped through a different exact mapping version/configuration create new mapping history. Older proposals/reviews/materializations are not silently rewritten.

### Missing later record

If a source key appeared in Batch A and is absent from Batch B:

```text
absence in Batch B
≠ source-side deletion instruction
≠ Portia deletion
≠ Portia deactivation
≠ Portia invalidation
≠ Portia supersession
```

Correction/removal must use explicit Portia lifecycle/correction/removal semantics.

## Import Source Record semantics

One Import Source Record represents one source-side unit observed inside one exact Import Batch.

It is explicitly not a Portia Event.

The cardinality to later proposals is:

```text
Import Source Record
→ 0..N proposals
```

Examples:

- one source record may be irrelevant to Portia and produce zero proposals;
- one source record may propose one Account or Observation;
- one source record may contain several independently reviewable source assertions and produce several proposals;
- a source record must never create a judgment-bearing record merely because a source label resembles one.

## Stable source-record key policy

Each Import Source Record preserves:

```text
source_record_key_origin
source_record_key
```

Allowed key origins are:

```text
source_provided
profile_defined_exact
```

`source_provided` is preferred whenever the source supplies a durable record key.

`profile_defined_exact` is permitted only when the exact source profile defines a deterministic key from designated stable source fields.

The following are prohibited identity inputs:

```text
row number
CSV order
array position
display text
nearby label
filename alone
similar person name
similar email address
fuzzy string match
import attempt order
```

The source record key is source-side identity only. It does not establish Portia Actor, roster student, Event, or canonical record identity.

## Source field representation

`source_fields` is a bounded normalized representation of source-side assertions.

Each field contains:

```text
field_key
value
```

Values may be:

```text
string
number
boolean
null
bounded array of those scalar values
```

Arbitrary nested objects and binary payloads are intentionally excluded. A source profile must normalize nested source structures into this bounded representation before persistence.

This preserves an important distinction:

```text
field absent
≠ field present with null
```

Neither state is silently converted to `false`, `no`, `declined`, `uninvolved`, or another domain conclusion.

Logical `field_key` values must be unique within one source record. Array order itself has no record identity meaning; an array-valued field may preserve order only when the exact source profile defines that order as source-significant.

## Source record digests

Two digests serve different purposes.

### `source_record_digest`

Application validation recomputes a content digest from a versioned canonical representation of:

```text
source_record_key_origin
source_record_key
normalized source_fields
```

It excludes local IDs, timestamps, run order, and later mapping/review results.

### `source_record_identity_digest`

Application validation recomputes logical import-observation identity from:

```text
exact Import Batch import_identity_digest
source_record_key_origin
source_record_key
source_record_digest
```

Consequences:

- exact replay under the same source+mapping has stable logical identity evidence;
- same source key with changed content is distinguishable history;
- changed mapping is distinguishable through the parent batch identity;
- row order is never identity.

## Source assertions do not become Portia judgments

Imported values remain source assertions until Portia's own mapping/review/domain rules permit a canonical record.

For example, source text such as:

```text
"major"
"aggressive"
"suspended"
"successful"
"compliant"
"restored"
```

must not automatically become:

```text
Classification
Hypothesis
Determination
fault/intent/severity judgment
Response appropriateness
Support recommendation
Fidelity
Outcome
recurrence failure
Reentry completion
Repair agreement/remorse/forgiveness
```

Judgment/evaluation families retain their existing human-attribution requirements.

## Identity safeguards

Import mapping must not silently manufacture identity through:

```text
similar name → same Actor
similar email → same person
source row position → roster student
nearby source label → represented human identity
```

Exact source identifiers may participate only under explicit mapping-profile and authorization rules. Ambiguous identity goes to attributable human review.

## Time semantics

Import times are provenance/operation times:

```text
source_snapshot.observed_at
Import Batch started_at / finished_at
Import Source Record observed_at
```

They are not substitutes for unknown:

```text
Event time
evidence time
Implementation time
Communication time
Follow-Up time
Outcome time
Reentry time
Repair time
```

A reviewed source field may later map to a domain-time field only when the target contract allows it and the source semantics support that mapping.

## Provenance boundary

Paper-derived canonical records use:

```text
creation_source.type = paper_capture
```

Import-derived canonical records use:

```text
creation_source.type = import
```

The existing `creation_source@1` import branch records provenance, not authority or truth. Slice 7 does not mutate its published `$id`.

Exact Import Batch / Import Source Record lineage remains import-staging history. A later import materialization receipt may preserve exact operational linkage without redefining `creation_source@1` in place.

## Quarantine and integrity

Ordinary import conditions such as:

```text
unmapped source field
ambiguous identity
rejected proposal
unresolved review
source label not recognized
```

belong in normal mapping/review flow, not Quarantine.

Exceptional contradictions may justify Integrity Finding / Quarantine later, for example:

```text
source record claims a batch that cannot resolve
stored digest does not match normalized fields
mapping version cannot be resolved
same supposedly exact identity digest resolves contradictory content
materialization replay would duplicate an already accepted canonical target
```

## Slice boundary

Slice 7 stops at durable source history.

It does not yet define:

```text
import_proposal
import_review
import_materialization
```

Paper-specific `capture_proposal@1` and `capture_review@1` are not reused because they require Page Record / Paper Interpretation lineage.

The next import slice should define the smallest import-specific proposal/review surface needed to map one exact Import Source Record to 0..N reviewable Portia proposals while preserving the same rules already established for paper:

```text
machine/source mapping ≠ human confirmation
human confirmation ≠ domain judgment when target semantics require separate judgment
accepted proposal ≠ canonical record until coordinated materialization succeeds
```
