# Portia Actor Directory Examples

**Status:** Accepted
**Issue:** #14
**ADR:** [`ADR 0010`](../decisions/0010-define-actor-directory-domain-model-and-lifecycle.md)
**Design:** [`Actor Directory Domain Model and Lifecycle`](../design/portia-actor-directory-domain-model-and-lifecycle.md)
**Machine-readable manifest:** [`issue-14/manifest.json`](issue-14/manifest.json)

These examples are synthetic and machine validated. They demonstrate the
accepted public contracts without implementing production filesystem mutation,
identity matching, contact delivery, institutional authorization, or a
teacher-facing directory.

## Actor roots and reviewed replacement topology

[`actor-active.json`](issue-14/actor-active.json) is a current Actor root for one
recurring non-roster person.

[`actor-duplicate-consolidation.json`](issue-14/actor-duplicate-consolidation.json)
shows the accepted many-predecessor-to-one-new-successor topology for a
human-confirmed duplicate consolidation.

[`actor-conflated-split.json`](issue-14/actor-conflated-split.json) shows one
new Actor produced as part of correcting a predecessor that conflated several
people. A complete split operation creates all reviewed successors
coordinately; no consumer silently chooses one.

Actor identifiers are opaque. Display, category, organization, title, contact
information, relationship claims, and workflow roles do not participate in
identity.

## Privacy-sensitive Contact Points

[`actor-contact-point.json`](issue-14/actor-contact-point.json) is a separate
canonical Contact Point child. It preserves contact kind, bounded label, source,
local verification, use preference, lifecycle, and attribution.

Local confirmation is not institutional verification, consent, successful
delivery, exclusive control, or authorization to communicate. Contact values
are excluded from ordinary display snapshots, operational facts, locks,
findings, derived indexes, and removal certificates.

## Explicit Actor-to-Student Relationships

[`actor-student-relationship.json`](issue-14/actor-student-relationship.json)
links one Actor to one exact Core roster-qualified student through:

```text
class_id + student_id
```

The record retains relationship type, basis, local review, and an optional
effective period. It does not establish legal parentage, guardianship, custody,
employment, disclosure permission, consent, or decision authority.

## Roster-student collision correction

[`actor-roster-student-collision.json`](issue-14/actor-roster-student-collision.json)
is immutable reviewed evidence that one exact Actor and one exact
class-qualified roster student represent the same human person.

The collision links a coordinated operation and Actor invalidation transition.
It creates no Actor successor, does not convert Actor Contact Points into roster
data, and establishes no workspace-wide student identity.

## Lifecycle, history correction, and amendment

[`actor-directory-lifecycle-transition.json`](issue-14/actor-directory-lifecycle-transition.json)
records an append-only Actor invalidation for a confirmed roster collision.
Transition predecessor chains—not timestamp sorting—select history.

[`actor-directory-lifecycle-history-correction.json`](issue-14/actor-directory-lifecycle-history-correction.json)
selects a corrected lifecycle branch without deleting or rewriting prior
transition files.

[`actor-directory-amendment.json`](issue-14/actor-directory-amendment.json)
binds one nonmaterial change to exact prior and resulting whole-file
fingerprints. Typed amendment paths exclude identity, lifecycle, contact values,
student targets, relationship types, creation provenance, and supersession
lineage.

## Representation migration and exceptional removal

[`actor-directory-record-migration.json`](issue-14/actor-directory-record-migration.json)
binds exact source and destination representations, deterministic procedure
identity, whole-file fingerprints, and the generating operation. Migration
preserves logical identity and meaning; it cannot hide correction, lifecycle
change, consolidation, splitting, collision handling, or removal.

[`actor-directory-exceptional-removal.json`](issue-14/actor-directory-exceptional-removal.json)
is a minimal workspace-level certificate for a narrowly authorized removal. It
retains exact opaque identity, canonical path, contract version, SHA-256 digest,
byte length, ground, authorization, execution, and operation evidence without
retaining the removed contact value or substantive payload.

## Actor-aware operations and diagnostics

[`integrity-finding-v2.json`](issue-14/integrity-finding-v2.json) represents an
Actor duplicate candidate as a rebuildable, indeterminate, nonblocking finding.
Similarity does not confirm identity.

[`operation-journal-v2.json`](issue-14/operation-journal-v2.json) shows a
recoverable duplicate-consolidation operation with one complete sorted Actor set,
deterministic locks, preflight evidence, ordered writes, commit evidence, and
privacy-minimized facts.

[`operation-lock-v2.json`](issue-14/operation-lock-v2.json) protects the Actor
Directory collection for namespace-sensitive work. Lock age or process absence
does not prove safe takeover.

[`quarantine-record-v2.json`](issue-14/quarantine-record-v2.json) protects an
Actor set during split reconciliation. Quarantine remains operational
protection, does not change Actor lifecycle, and release does not reactivate an
Actor.

## Reused derived-generation contracts

[`source-snapshot.json`](issue-14/source-snapshot.json) inventories exact source
paths, contracts, roles, byte lengths, and digests under explicit authorization
coverage.

[`derived-index-metadata.json`](issue-14/derived-index-metadata.json) binds one
complete incoming-reference generation to the exact snapshot, builder,
validation record, output fingerprint, and Actor-aware operation journal.

[`derived-current-pointer.json`](issue-14/derived-current-pointer.json) selects
one generation explicitly. It does not prove freshness, completeness, identity
truth, duplicate equivalence, contact validity, or relationship authority.

The Actor Directory reuses the accepted `incoming_reference_index`,
`replacement_frontier_index`, and `lifecycle_timeline` projection families.
Incomplete authorization or discovery coverage must produce an indeterminate
result rather than an empty-graph claim.

## Validation boundary

The JSON examples validate structurally through the offline schema catalog.
Application validation must additionally establish:

```text
canonical path and persisted identity agreement
exact Actor and Core roster resolution
current-use and authority eligibility
review and timestamp chronology
lifecycle-chain and selected-history correctness
duplicate-consolidation and split topology
roster-collision operation completeness
incoming-reference discovery completeness
privacy-safe payload and diagnostic evidence
operation intent, lock order, write order, commit, replay, and recovery
fingerprint and byte-length truth
migration semantic equivalence
exceptional-removal authorization and certificate-before-removal ordering
derived source completeness, freshness, and current-use eligibility
```

Schema-valid does not mean identity-confirmed, authorized, current, or safe to
execute.
