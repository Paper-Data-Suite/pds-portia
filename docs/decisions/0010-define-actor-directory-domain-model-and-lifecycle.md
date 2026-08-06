# ADR 0010: Define the Actor Directory Domain Model and Lifecycle

* **Status:** Accepted
* **Date:** 2026-08-06
* **Decision owners:** Portia maintainers
* **Related issue:** [#14 — Define the Actor Directory domain model and lifecycle](https://github.com/Paper-Data-Suite/pds-portia/issues/14)
* **Related design:** [`docs/design/portia-actor-directory-domain-model-and-lifecycle.md`](../design/portia-actor-directory-domain-model-and-lifecycle.md)
* **Related schema catalog:** [`schemas/schema-catalog.json`](../../schemas/schema-catalog.json)
* **Related schema guide:** [`schemas/README.md`](../../schemas/README.md)
* **Related decisions:**
  * [`0001-separate-observations-interpretations-and-determinations.md`](0001-separate-observations-interpretations-and-determinations.md)
  * [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)
  * [`0003-adopt-teacher-local-initial-deployment.md`](0003-adopt-teacher-local-initial-deployment.md)
  * [`0004-define-portia-identity-ownership-and-storage.md`](0004-define-portia-identity-ownership-and-storage.md)
  * [`0005-define-event-and-participant-domain-model.md`](0005-define-event-and-participant-domain-model.md)
  * [`0006-define-event-participant-role-domain-model.md`](0006-define-event-participant-role-domain-model.md)
  * [`0007-define-shared-reference-targeting-and-relationship-contracts.md`](0007-define-shared-reference-targeting-and-relationship-contracts.md)
  * [`0008-define-lifecycle-correction-and-migration-contracts.md`](0008-define-lifecycle-correction-and-migration-contracts.md)
  * [`0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md`](0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md)

## Context

Portia already publishes opaque Actor identifiers and identity-only Actor
references. Event Participant v3 can refer to one Actor and preserve a bounded
historical display snapshot.

The repository did not yet define:

- one canonical Actor record;
- Actor eligibility;
- workspace-scoped Actor storage;
- contact information;
- recurring Actor-to-student relationships;
- Actor lifecycle;
- Actor-specific amendment and correction;
- duplicate review and consolidation;
- conflated-person correction;
- roster-student collision handling;
- Actor-aware operation targets;
- or privacy-minimized Actor recovery and derived-state behavior.

The existing lifecycle, amendment, migration, and removal contracts are owned by
a containing class-qualified Portia work. An Actor is intentionally
workspace-scoped and may recur across several classes.

The Actor Directory therefore requires its own domain records and
workspace-scoped history while remaining compatible with ADRs 0007–0009.

Core remains authoritative for:

```text
workspace resolution
class_id
class metadata
rosters
class-qualified roster-student identity
```

Core does not provide a workspace person registry, cross-roster person
equivalence, guardian identity, staff identity, or legal relationship authority.

## Decision

Portia adopts the Actor Directory architecture defined by Decisions 1–25 of the
related design.

### Semantic unit

One Actor represents:

> One recurring non-roster human person deliberately recorded for reuse within
> one selected teacher-local Paper Data Suite workspace.

An Actor is not:

- a roster student;
- a household;
- an organization;
- a position;
- a role;
- a recipient group;
- a contact method;
- an authenticated user;
- or an institutionally authoritative person identity.

Actor creation is deliberate.

Names, contact values, imports, communication recurrence, and similarity results
do not create active Actor identity automatically.

### Identity and authority

Actor identity remains the opaque:

```text
actr_<opaque-id>
```

contract.

The existing `actor_ref@1` remains identity-only and unchanged.

Display names, organizations, titles, categories, contacts, relationships,
lifecycle, and authority claims are not Actor identity.

The Actor Directory is teacher-local and workspace-scoped. It makes no claim of
institutional, legal, employment, guardianship, custody, disclosure, or
decision-making authority.

### Roster-student separation

Core roster-student identity remains:

```text
class_id + student_id
```

Portia does not create Actors from roster selection and does not use Actors as a
cross-class student identity shortcut.

Name, student-ID, or contact similarity across rosters does not establish
workspace-wide person equivalence.

A confirmed Actor–roster collision is explicit cross-family correction. It
invalidates the Actor and preserves one exact roster-qualified reference. It
does not create an Actor-to-student replacement edge.

### Canonical storage

The canonical Actor root is:

```text
<PDS workspace>/portia/actors/<actor_id>/
```

The current Actor record is:

```text
<PDS workspace>/portia/actors/<actor_id>/actor.json
```

This supersedes the earlier provisional flat-file example before any public
Actor record contract or production Actor data exists.

Actor child and history records remain beneath the same bounded Actor root.

Actor records are not stored beneath an arbitrary class.

### Aggregate decomposition

Actor v1 consists of:

```text
Actor root
Actor Contact Point
Actor-to-Student Relationship
Actor lifecycle and correction history
```

Contact Points are separate because contact values have independent provenance,
lifecycle, correction, privacy, and removal requirements.

Actor-to-Student Relationships are separate because relationship assertions are
student-specific, sourced, lifecycle-bearing, and nonauthoritative.

Workflow-specific roles remain in Events, Accounts, Communications, Supports,
Determinations, and other consuming records.

### Actor root

The Actor root contains:

- current lifecycle status;
- current display name;
- broad Actor category;
- optional organization;
- optional title;
- creation provenance;
- timestamps and attribution;
- and explicit predecessor lineage where applicable.

It does not contain:

- contact values;
- student lists;
- workflow-role lists;
- legal authority;
- credentials;
- or unrestricted notes.

Initial Actor statuses are:

```text
proposed
active
inactive
invalidated
superseded
```

`inactive` remains historically valid and reopenable.

`invalidated` is not a valid current assertion.

`superseded` is absolute terminal.

### Contact Points

Actor Contact Points are separate canonical child records with opaque `acp_`
identity.

Version 1 supports:

```text
email
phone
```

Contact Points preserve source, verification, use preference, lifecycle,
provenance, and replacement lineage.

Changing an exact contact value requires a successor Contact Point.

Contact values never become Actor identity, path components, lock metadata,
finding keys, or ordinary historical snapshots.

### Actor-to-Student Relationships

Actor-to-Student Relationships are separate canonical child records with opaque
`asrel_` identity.

They bind one exact Actor to one exact Core roster-qualified student and preserve:

- relationship type;
- source or basis;
- review state;
- optional effective period;
- lifecycle;
- provenance;
- and replacement lineage.

A teacher-recorded parent, guardian, counselor, administrator, or support
relationship does not independently prove legal or institutional authority.

Portia does not propagate a relationship automatically across rosters.

### Historical bindings

A consuming record should ordinarily preserve:

```text
actor_ref
person_display_snapshot
contextual role
```

It may also preserve one exact Actor-to-Student Relationship reference when the
canonical relationship is materially relevant.

Historical snapshots are nonauthoritative and are not rewritten when current
Actor, contact, or relationship data changes.

### Lifecycle and amendment

Actor, Contact Point, and Actor-to-Student Relationship share workspace-scoped:

```text
actor_directory_lifecycle_transition@1
actor_directory_lifecycle_history_correction@1
actor_directory_amendment@1
```

Creation status is the lifecycle baseline.

Later status changes use append-only predecessor-selected transitions.

Current status and selected history must reconcile.

A history correction selects corrected append-only evidence; it does not delete
or rewrite prior transitions.

A nonmaterial amendment uses bounded typed paths and exact prior/resulting
fingerprints.

Status, identity, Actor ownership, contact value, student target, relationship
type, and material relationship basis are not amendable.

### Material correction and replacement

Material correction creates new canonical identity and explicit lineage.

The Actor replacement graph permits:

```text
one Actor -> one Actor
several Actors -> one Actor
one Actor -> several Actors
```

It prohibits many-to-many replacement.

Exact historical references never silently follow successors.

### Duplicate review and consolidation

Duplicate candidates are derived Actor-targeted Integrity Findings.

Similarity never proves identity.

Finding Acknowledgement records review.

Finding Suppression affects presentation only and expires when relevant evidence
changes.

Confirmed duplicate Actors use:

```text
several existing Actors
-> one new reviewed Actor successor
```

No existing Actor is selected as survivor.

Every predecessor transitions to `superseded`.

Contact Points, Relationships, and incoming references receive explicit reviewed
dispositions and are never moved automatically.

### Conflated-person split

One Actor that conflates several distinct people may be replaced through:

```text
one predecessor Actor
-> several new Actor successors
```

The complete direct successor set is fixed in one coordinated operation.

Profiles, Contact Points, Relationships, and incoming references are assigned
explicitly. Unresolved evidence remains attached to the predecessor or
review-required; Portia does not guess.

### Incoming references

Exact Actor references remain exact after:

- lifecycle change;
- amendment;
- consolidation;
- split;
- roster collision;
- migration;
- Quarantine;
- or exceptional removal.

Resolution and current-use eligibility are separate.

Graph-sensitive operations require a fresh complete incoming-reference
generation or complete bounded canonical scan.

Missing, stale, corrupt, or authorization-limited derived state does not prove an
empty graph.

### Migration

Representation-only Actor-directory migration uses:

```text
actor_directory_record_migration@1
```

It preserves record identity, Actor ownership, record family, lifecycle meaning,
and domain semantics.

Migration cannot conceal person correction, contact-value correction,
relationship correction, consolidation, split, roster collision, lifecycle
change, or removal.

### Exceptional removal

Ordinary hard deletion is prohibited.

Narrow Actor-directory removal uses:

```text
actor_directory_exceptional_removal@1
```

and reuses the existing scope-neutral:

```text
rmv_<opaque-id>
```

identifier.

Certificates are stored outside the removable Actor root:

```text
portia/actor-directory-removals/<removal_id>.json
```

The certificate retains minimum opaque identity, path, contract, fingerprint,
byte-length, authorization, time, attribution, and operation evidence.

It does not retain removed substantive payload.

### Actor-aware operational contracts

Issue #14 introduces additive versions:

```text
integrity_finding@2
operation_journal@2
operation_lock@2
quarantine_record@2
```

They add exact Actor-directory record, Actor-set, or Actor-directory collection
targets as appropriate.

Version-1 wire shapes remain immutable.

Operation Journal v2 retains workspace scope and the accepted operation-kind
vocabulary.

Operation Lock v2 adds Actor collection and exact Actor-directory record scopes.

Quarantine Record v2 adds Actor targets and
`block_actor_directory_writes`.

Quarantine remains separate from lifecycle.

### Derived state

The existing Issue #13 contracts remain unchanged:

```text
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

The initial Actor Directory reuses generic projection kinds including:

```text
incoming_reference_index
replacement_frontier_index
lifecycle_timeline
active_integrity_finding_index
active_quarantine_index
operation_recovery_queue
current_state_view
```

Actor search initially uses bounded canonical scanning and an in-memory index.

No persisted Actor search or duplicate-candidate index is required in version 1.

Derived state remains nonauthoritative and authorization-aware.

### Privacy

Operational records preserve opaque identity, paths, fingerprints, byte lengths,
contract versions, and bounded reason codes only as required.

They do not copy:

- contact values;
- display names;
- student names;
- relationship narratives;
- or removed payload

for convenience.

Whole-file content fingerprints remain permitted.

Standalone unsalted hashes of contact values are prohibited.

## Consequences

### Positive

- Recurring collaborators receive stable identity across class-owned workflows.
- Roster-student and Actor identity authorities remain distinct.
- Contact and relationship claims receive explicit provenance and lifecycle.
- Historical records remain readable without silent retargeting.
- Duplicate consolidation and conflated-person correction preserve complete
  lineage.
- Workspace-scoped Actor history no longer requires fabricated class ownership.
- Actor operations compose with ADR 0009 recovery and derived-state rules.
- Sensitive contact payload is isolated from ordinary operational evidence.
- Later Portia domains receive one accepted Actor-binding architecture.

### Costs

- The Actor Directory adds several independently versioned public contracts.
- Contact and relationship reconciliation requires human review.
- Exact incoming-reference discovery is required for graph-sensitive correction.
- Actor-aware versions of several Issue #13 contracts must coexist with version 1.
- Current status and append-only history require cross-record validation.
- Split and consolidation operations require explicit child and reference
  disposition.
- Exceptional removal requires durable external certificates and recovery logic.

### Risks

- Teacher-local assertions may be mistaken for institutional authority if user
  interfaces fail to preserve disclaimers.
- Contact data remains sensitive even in local-first storage.
- Similarity systems may encourage overconfident duplicate or roster matches.
- Incomplete derived state may be mistaken for absence.
- Operational logs may leak payload unless implementations enforce the accepted
  privacy boundary.
- Future consuming domains may invent incompatible Actor shapes if they bypass
  the shared references and snapshots.

## Alternatives rejected

Rejected alternatives include:

- storing Actors beneath one class;
- retaining the provisional flat Actor file;
- embedding all contacts and relationships in Actor;
- using names or contacts as identity;
- automatic Actor creation from communication data;
- treating Actor categories as authority;
- automatic cross-roster relationship propagation;
- reusing class/work lifecycle envelopes;
- timestamp-selected history;
- arbitrary JSON Patch amendment;
- selecting an existing duplicate as survivor;
- automatic child or incoming-reference reassignment;
- Actor-to-roster replacement edges;
- many-to-many Actor replacement;
- ordinary hard deletion;
- generic workspace targets for exact Actor operations;
- lock expiry or heartbeat;
- Quarantine as lifecycle;
- a new Actor-specific derived-generation system;
- persisted Actor search in version 1;
- and standalone contact-value hashes.

## Compatibility

Existing public contracts remain readable and immutable.

In particular:

```text
actor_ref@1
person_display_snapshot@1
Event Participant v3
Issue #12 version-1 lifecycle and correction contracts
Issue #13 version-1 operation and derived contracts
```

do not change in place.

Future consuming domains must compose the accepted Actor references, snapshots,
and relationship references rather than inventing alternate person shapes.

## Implementation order

Implementation proceeds in this order:

1. Actor child identifiers;
2. exact Actor-directory references and target;
3. Actor root;
4. Contact Point;
5. Actor-to-Student Relationship;
6. Actor–Roster Student Collision;
7. shared Actor-directory lifecycle, history correction, and amendment;
8. Actor-directory migration and exceptional removal;
9. Integrity Finding, Operation Journal, Operation Lock, and Quarantine version 2;
10. examples, validation matrix, documentation reconciliation, and final drift
    check.

## Validation boundary

JSON Schema validates local wire shape.

Application validation establishes:

- exact path and ownership;
- Core roster resolution;
- roster-student prohibition;
- lifecycle and history reconciliation;
- materiality;
- duplicate equivalence;
- replacement topology;
- split completeness;
- incoming-reference completeness;
- privacy;
- authorization;
- operation recovery;
- lock and Quarantine semantics;
- exceptional removal;
- and derived freshness.

## Pre-ADR checkpoint

The decision was accepted after reviewing:

```text
pds-portia/main:
  d60966f8486bf93fb0185e3662b76d3b79ce9dcb

Issue #14 branch:
  f8bd98c09f9702058563db84d4b1d8a962597721
  five commits ahead, zero behind

pds-core/main:
  6c507213618b68a6dd3ea096e1a898201ff029e6
```

No drift required changing Decisions 1–25.

The existing exceptional-removal identifier was confirmed scope-neutral and is
reused unchanged.

A final Core and Portia checkpoint remains required before repository acceptance.
