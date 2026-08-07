# ADR 0011: Define Account and Observation Domain Models

* **Status:** Accepted
* **Date:** 2026-08-07
* **Decision owners:** Portia maintainers
* **Related issue:** [#15 — Define Account and Observation domain models](https://github.com/Paper-Data-Suite/pds-portia/issues/15)
* **Related design:** [`docs/design/portia-account-and-observation-domain-models.md`](../design/portia-account-and-observation-domain-models.md)
* **Related schema catalog:** [`schemas/schema-catalog.json`](../../schemas/schema-catalog.json)
* **Related decisions:** ADRs 0001–0010

## Context

Portia already distinguishes Event context, Event Participants, Event
Participant Roles, and reusable Actors. Event Participant Role v3 already
contains structural basis placeholders for `account` and `observation`, and an
active or superseded `reported_involved` Role must contain at least one
`account_ref`.

The repository did not yet define canonical Account or Observation records.
Without those contracts, later Classification, Hypothesis, Determination,
Response, Communication, Support, Follow-Up, and Outcome work would either
invent incompatible evidence shapes or collapse source evidence into Event
narrative.

Core remains authoritative for workspace/class/roster identity, PDS2 routing,
route registration, and retained source-scan provenance. Portia owns Account and
Observation semantics.

## Decision

Portia adopts the Account and Observation architecture in the related design.

### Semantic boundary

```text
Account
= one coherent attributed statement, report, response, recollection, or
  perspective from one represented human source

Observation
= one coherent attributed or instrumented record of directly observable,
  counted, timed, recorded, or measured information
```

A human report of what the person says they observed remains an Account when the
canonical record preserves the statement. An Observation is used when the
workflow itself preserves the person or instrument as the observer of the
observable information.

Neither record is a finding or judgment.

### Identity and ownership

Account identity is:

```text
acct_<opaque-id>
```

Observation identity is:

```text
obs_<opaque-id>
```

Both are canonical children of one Event:

```text
classes/<class_id>/modules/portia/work/<event_id>/records/account/<account_id>.json
classes/<class_id>/modules/portia/work/<event_id>/records/observation/<observation_id>.json
```

Both reuse `portia_target_ref@1` for Event, one-Participant, or explicit
Participant-set targeting.

### Represented human attribution

Portia will publish:

```text
represented_human_attribution@1
```

with closed branches for:

```text
roster_student
actor
local_operator
descriptive_person
unidentified_person
```

This represents the human whose statement or observation is preserved. It is
distinct from `created_by` / `updated_by` operation attribution.

Unidentified sources may be canonically preserved but do not qualify for active
`reported_involved` use in v1.

### Account semantics

Account records preserve:

```text
firsthand | secondhand | mixed | unknown
```

information origin and bounded source-expressed certainty without assigning
credibility.

Content segments distinguish:

```text
verbatim_quote
recorded_summary
```

and optional elicitation context remains separate from source wording.

Known Account lineage may use nested exact relations:

```text
reports_from
clarifies
retracts
```

Relations do not establish truth or corroboration.

### Evidence time

Portia will publish:

```text
evidence_time@1
```

with:

```text
exact
approximate
date_only
range
unknown
```

precision branches. Account uses it for source-contribution time and Observation
uses it for observation time.

### Observation semantics

Observation supports human or instrument observers and methods including:

```text
live_direct
artifact_review
manual_count
manual_timing
instrumented
other
```

Observation v1 supports nested measurement forms:

```text
count
duration
latency
percentage
other_numeric
```

with measure-specific value/unit constraints.

Observation has no canonical positive/neutral/concerning, severity, violation,
or risk field.

### Account retraction

Retraction is source-evidenced.

A new same-source Account with exact `retracts` relation is reviewed and
activated, and a coordinated lifecycle operation transitions the referenced
predecessor Account to `retracted`.

Teachers cannot mark an Account retracted merely because they disbelieve it.
Retraction does not establish falsity.

### Lifecycle

Account statuses:

```text
proposed
active
retracted
invalidated
superseded
```

Observation statuses:

```text
proposed
active
invalidated
superseded
```

Lifecycle reasons are the bounded vocabularies recorded in the design.

Material evidence correction uses replacement/supersession.

Account and Observation v1 expose no in-place Amendment paths. Even spelling,
punctuation, formatting, or transcription changes to primary evidence are
source-evidence changes and require replacement when correction is necessary.

### `reported_involved`

Event Participant Role v3 remains unchanged.

A qualifying Account for active `reported_involved` must:

```text
resolve canonically
belong to the same Event
be eligible for current use
have identified/traceable represented-human attribution
and target the same Participant or a Participant set containing that Participant
```

An Event-wide Account is insufficient for a participant-specific
`reported_involved` Role.

Observation, paper provenance, import provenance, free text, or teacher
confirmation alone do not satisfy the Account requirement.

Later Account retraction, invalidation, supersession, or removal never silently
retargets or cascades the Role. Reconciliation is explicit and recoverable.

### Paper and import

Account and Observation reuse `creation_source@1`.

No canonical Account or Observation is created merely because a page is
rendered. Paper-derived canonical evidence requires `stage = ingested` and
begins proposed. Imported evidence likewise begins proposed. Local review is
required before activation.

OCR or import interpretation may propose evidence but cannot silently establish
source identity, verbatim quotation, firsthand status, Participant targeting,
Role activation, or findings.

### Source artifacts

Portia will publish:

```text
source_artifact_ref@1
```

with branches for:

```text
paper_capture
workspace_file
portia_work_record
module_work_record
external_record
```

Binary payloads are not embedded in Account or Observation JSON. References are
inert evidence locators and do not establish authenticity, accuracy,
authorization, credibility, or proof.

### Shared infrastructure

Account and Observation reuse existing class/work-scoped targeting, lifecycle,
history correction, disagreement, dependency, migration, removal, operations,
Quarantine, Integrity Finding, and derived-state infrastructure where the
published wire shapes already suffice.

No new operational contract version is required merely to target Account or
Observation.

### No automatic finding

Persisting Account or Observation creates source evidence only.

Portia does not automatically convert source evidence, repetition, agreement,
or Account-plus-Observation combinations into findings, corroboration,
Classification, Hypothesis, Determination, policy violation, severity, or risk.

## Public contract plan

Issue #15 will add:

```text
portia_account_id@1
portia_observation_id@1
represented_human_attribution@1
evidence_time@1
source_artifact_ref@1
account@1
observation@1
```

Dedicated Account/Observation reference schemas are not required for v1;
consumers constrain existing local/exact local record references.

Observation measurement and Account relations remain nested in their owning
record contracts.

## Consequences

### Positive

- source evidence remains distinct from interpretation;
- active `reported_involved` gains a concrete attributed-evidence contract;
- paper/import workflows can propose evidence without fabricating findings;
- conflicting Accounts remain representable without adjudication;
- source retraction is preserved without erasure;
- Observations support positive, neutral, and potentially concerning facts with
  one neutral model;
- shared history and operation contracts remain reusable;
- sensitive source text stays out of ordinary operational metadata.

### Costs

- material source-evidence corrections require successor records;
- retraction requires a coordinated source-evidenced workflow;
- participant-specific `reported_involved` cannot rely on an Event-wide Account;
- imported and paper-derived evidence requires review before activation;
- some future attachment workflows will need explicit source-artifact
  resolution and authorization.

## Rejected alternatives

### Store Accounts and Observations inside Event summary

Rejected because attributed evidence would become an apparently objective
mutable narrative.

### Treat firsthand Account as Observation automatically

Rejected because `firsthand` is the represented source's origin claim, not the
system's direct-observation provenance.

### Add credibility or reliability scoring

Rejected because Portia must preserve evidence without adjudicating source
truthfulness automatically.

### Let Event-wide Account activate any reported Participant

Rejected because unrelated same-Event evidence could justify an arbitrary
participant-specific Role.

### Teacher-only retraction toggle

Rejected because retraction is a claim about the represented source's position
and therefore requires source evidence.

### Permit small text Amendments

Rejected for v1 because even small changes to quote, summary, or Observation
content rewrite evidence.

### Separate positive and negative Observation families

Rejected because observable content does not require a valence ontology.

### Embed attachment binaries

Rejected because canonical evidence records should preserve references and
provenance rather than duplicate large or sensitive artifacts.

### Add dedicated Account/Observation reference families immediately

Rejected because existing local/exact local record references already support
typed version-aware composition.

## Compatibility

Published contracts through ADR 0010 remain immutable.

Event Participant Role v3 remains the implementation target unless schema work
uncovers a genuine incompatible wire requirement.

Core v0.6 requires no change for this architecture.

## Follow-up

The next Issue #15 slices should implement, in order:

1. shared identifiers and evidence primitives;
2. `account@1`;
3. `observation@1`;
4. Role/lifecycle/shared-infrastructure integration fixtures;
5. public examples and final validation/documentation reconciliation.
