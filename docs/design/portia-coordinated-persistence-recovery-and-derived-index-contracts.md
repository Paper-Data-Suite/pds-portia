# Portia Coordinated Persistence, Recovery, and Derived-Index Contracts

**Status:** In development — through Decision 3
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#13 — Define coordinated persistence, recovery, and derived-index contracts`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-05
**Branch:** `13-coordinated-persistence-recovery-derived-index-contracts`

## 1. Purpose

This document defines Portia's implementation-neutral architecture for operations that affect one or more canonical representations.

It will establish shared contracts for:

- operation identity;
- preflight;
- expected prior state;
- exclusive creation;
- revision-aware replacement;
- staging;
- durable operation journals;
- partial success;
- coordinated commit;
- compensation;
- interruption recovery;
- lock handling;
- repair mode;
- quarantine;
- integrity diagnostics;
- derived-index rebuilding;
- and current-view regeneration.

The design applies first to the current implementation-target contracts:

```text
Event v2
Event Participant v3
Event Participant Role v3
Work Relationship v2
```

It must also support the shared Issue #12 contracts for:

```text
Lifecycle Transition
Lifecycle History Correction
Amendment
Statement of Disagreement
Dependency
Record Migration
Ownership Correction
Exceptional Removal
Integrity Finding
```

This document defines architecture and public contracts. Production Python persistence services, filesystem mutation, recovery execution, background work, and teacher-facing workflows belong to a later implementation milestone.

## 2. Governing contracts

This design remains subordinate to accepted ADRs 0001–0008.

It must not change the meaning of accepted public records merely to simplify storage.

The current implementation-target schemas are:

```text
schemas/v2/event.schema.json
schemas/v3/event-participant.schema.json
schemas/v3/event-participant-role.schema.json
schemas/v2/work-relationship.schema.json
```

The current shared lifecycle and correction schemas include:

```text
schemas/v1/lifecycle/lifecycle-transition.schema.json
schemas/v1/lifecycle/lifecycle-history-correction.schema.json
schemas/v1/corrections/amendment.schema.json
schemas/v1/corrections/statement-of-disagreement.schema.json
schemas/v1/dependencies/dependency.schema.json
schemas/v1/migrations/record-migration.schema.json
schemas/v1/corrections/ownership-correction.schema.json
schemas/v1/removals/exceptional-removal.schema.json
schemas/v1/projections/integrity-finding.schema.json
```

Published schemas remain immutable. If Issue #13 requires a changed wire shape, only the affected contract receives a new version.

## 3. Reviewed repository baseline

The first required cross-repository drift check was completed on 2026-08-05.

| Repository | Reviewed commit | Relevant current pattern | Immediate implication |
| --- | --- | --- | --- |
| `pds-portia` | `0841bd946c6c3a098ebaad4bfb90669816ecc93b` | Issue #12 is merged. Current status plus append-only history, exact replacement, migration, ownership correction, exceptional removal, Dependencies, and rebuildable Integrity Findings now require a coordinated operation contract. | Required foundation for this issue. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core v0.6 uses exclusive creation, expected-revision protection, explicit current pointers, idempotent service orchestration, structured partial success, fingerprint-protected lock clearing, source snapshots, and verified atomic replacement of complete derived catalogs. | Reuse the principles without importing Core-private storage code or making Core authoritative for Portia operations. |
| `pds-meridian` | `c7e9129f6547bca9953f8ae5c8718ce358341172` | Meridian treats catalogs as discovery only, reloads canonical records, preserves exact historical provenance, and distinguishes current, historical, unavailable, incompatible, unauthorized, and policy-excluded states. | Preserve future exact Portia provenance; no immediate Meridian change. |
| `pds-vitrine` | `cea3a9b66bb31ebc7d6511bcf287d4e42c58f7d7` | Vitrine's current design uses immutable revisions, explicit current pointers, optimistic concurrency, nondestructive replacement, and rebuildable views. | Maintain compatible operational patterns; no immediate Vitrine change. |

These anchors record the reviewed state. They do not vendor sibling contracts into Portia.

The baseline classification is:

```text
pds-core: documentation reconciliation and reusable operational precedent
pds-meridian: future integration concern; no immediate contract change
pds-vitrine: future integration concern; no immediate contract change
```

The baseline must be checked again before accepting ADR 0009 and immediately before closing Issue #13.

## 4. Governing principles

1. Canonical domain records remain authoritative for Portia domain meaning.
2. Durable operational records coordinate and recover writes but do not replace domain evidence.
3. Derived projections are rebuildable and never authorize domain changes.
4. Transient artifacts may be removed only while they are proven not to be accepted canonical or required recovery evidence.
5. Preflight occurs before canonical mutation.
6. New canonical identities use exclusive creation.
7. Existing mutable representations require explicit expected prior state.
8. One-file atomic replacement does not imply graph-wide atomicity.
9. Multi-record operations are recoverable unless a stronger mechanism is actually implemented and verified.
10. Canonical acceptance is distinct from operation completion.
11. Accepted canonical records are not deleted to simulate rollback.
12. Exact replay is distinct from contradictory reuse of an operation identity.
13. Recovery diagnoses exact evidence before it writes.
14. Lock age alone never proves that a lock is stale.
15. Missing derived state never proves an empty canonical graph.
16. Reads do not silently rebuild or repair derived state.
17. Current views report canonical disagreement rather than choosing a convenient answer.
18. Operational data remains privacy-minimized.
19. Workspace-relative paths support diagnostics but do not become identity.
20. Public contracts remain independently versioned and immutable.

---

# 5. Approved Decision 1: Durable State Categories and Authority

## 5.1 Decision

Portia adopts four distinct persistence categories:

```text
canonical domain record
durable operational record
derived projection
transient artifact
```

Every persisted artifact must belong to exactly one category under the operation being evaluated.

An artifact's category determines:

- its authority;
- whether it may be rebuilt;
- whether it may be removed;
- what recovery evidence it carries;
- how it is backed up;
- and whether ordinary readers may rely on it.

## 5.2 Canonical domain records

A canonical domain record carries accepted Portia meaning.

Current examples include:

- Event;
- Event Participant;
- Event Participant Role;
- Work Relationship;
- Lifecycle Transition;
- Lifecycle History Correction;
- Amendment;
- Statement of Disagreement;
- Dependency;
- Record Migration;
- Ownership Correction;
- Exceptional Removal.

Canonical records remain authoritative for their defined domain assertions.

An operation journal does not become the sole evidence that:

- a status changed;
- an amendment was accepted;
- a predecessor was superseded;
- a migration occurred;
- ownership was corrected;
- or exceptional removal occurred.

The applicable canonical record or records must exist and reconcile.

## 5.3 Durable operational records

A durable operational record preserves information required to coordinate, diagnose, recover, compensate, or safely conclude an operation.

Initial operational concepts include:

- Operation Journal revision;
- Operation Current Pointer;
- operation lock metadata;
- quarantine state;
- recovery decision;
- finding acknowledgement;
- permitted finding suppression.

Operational records are not domain records merely because they are durable.

They must not:

- redefine the target's lifecycle;
- create a Work Relationship;
- change a Dependency;
- select a successor;
- establish semantic migration;
- or authorize exceptional removal.

## 5.4 In-progress journals are not disposable

An incomplete journal may be the only durable evidence that explains:

- what the operation intended;
- which preconditions were validated;
- which writes may have become durable;
- which records were read back successfully;
- which lock scope was held;
- and which recovery actions remain safe.

An in-progress journal must not be deleted as disposable cache data.

A completed journal may later be compacted or removed only when:

1. the operation is in a terminal state;
2. no accepted canonical record depends on the journal as its sole operation evidence;
3. no recovery, quarantine, compensation, acknowledgement, or suppression state depends on it;
4. the retention policy permits removal;
5. and removal cannot obscure a partial-success history.

The exact retention period remains a later deployment and policy decision.

## 5.5 Derived projections

A derived projection is a deterministic or policy-bound view generated from canonical records and accepted operational evidence.

Initial examples may include:

- incoming-reference index;
- reverse Work Relationship index;
- Dependency graph;
- replacement frontier;
- lifecycle timeline;
- migration logical-identity view;
- ownership-correction mapping;
- exceptional-removal lookup;
- active Integrity Finding cache;
- operation recovery queue;
- work current-state summary.

Derived state is nonauthoritative.

A derived row cannot:

- create a canonical relationship;
- prove a Dependency absent;
- select a lifecycle head;
- authorize a write;
- establish ownership;
- establish removal;
- or repair canonical state.

## 5.6 Missing derived state

A missing derived projection means only that the projection is unavailable.

It does not mean:

- no incoming references exist;
- no Dependencies exist;
- no successor exists;
- no removal certificate exists;
- no Integrity Finding exists;
- or the canonical graph is empty.

A graph-sensitive operation must use one of these methods:

```text
verified current projection
bounded canonical evaluation
indeterminate blocking result
```

It must not interpret projection absence as permission to proceed.

## 5.7 Transient artifacts

A transient artifact is an unaccepted implementation artifact created to prepare or verify an operation.

Examples include:

- staged candidate bytes;
- target-adjacent temporary replacement file;
- candidate derived database;
- temporary current-pointer file;
- unaccepted serialization output.

A transient artifact may be removed only when Portia can prove that:

- it never became the accepted canonical representation;
- it is not the currently selected operational revision;
- it is not required to diagnose partial success;
- and removal does not destroy required recovery evidence.

## 5.8 Acceptance boundary

An artifact becomes an accepted canonical representation only after all required acceptance checks for that step succeed.

The initial conceptual sequence is:

```text
serialized
-> staged
-> durably written to intended canonical path
-> read-back validated
-> identity and path verified
-> accepted
```

A later decision will define exact per-step dispositions and commit gates.

Filesystem existence alone does not prove acceptance.

## 5.9 Backup boundary

The foundation assumes that recovery of domain meaning requires preservation of:

- canonical Portia records;
- append-only histories;
- incomplete operation journals;
- active quarantine and repair evidence;
- migration and ownership-correction certificates;
- exceptional-removal certificates;
- and compatible schema and application versions.

Derived projections ordinarily need not be backed up when every authoritative source and required recovery record is preserved.

Institutional backup frequency, encryption, retention, and off-device policy remain out of scope.

---

# 6. Approved Decision 2: Operation Identity, References, Kinds, and Scope

## 6.1 Semantic unit

One Portia operation represents one bounded teacher-visible or system-visible intent whose accepted execution may require several coordinated steps.

Examples include:

```text
create one Event
activate one successor graph
apply one nonmaterial Amendment
transition one target lifecycle
consolidate one duplicate set
migrate one logical record
correct one ownership graph
exceptionally remove one target
rebuild one derived projection scope
repair one interrupted operation
```

An operation must not become an indefinitely open container for unrelated work.

## 6.2 Operation identity

Operation identifiers use:

```text
op_<opaque-id>
```

The identifier is workspace-scoped, opaque, never reused, and nonsemantic.

It follows the established Portia-owned identifier rules:

- total length from 4 through 128 characters;
- suffix begins with an ASCII letter or digit;
- remaining suffix characters are ASCII letters, digits, underscores, or hyphens;
- periods are prohibited;
- case and leading zeros are preserved.

The identifier must not encode:

- student identity;
- class identity;
- work identity;
- operation kind;
- outcome;
- timestamp;
- lifecycle state;
- or a filesystem path.

## 6.3 Stable operation reference

The stable version-1 Operation Reference is:

```json
{
  "operation_id": "op_example"
}
```

It identifies the operation series, not one exact journal revision.

The shape intentionally matches the `operation_id` field already accepted by the Integrity Finding version-1 operation target.

Therefore Issue #13 does not require an Integrity Finding wire-shape change merely to identify an operation.

A later public schema should be placed at:

```text
schemas/v1/references/operation-ref.schema.json
```

## 6.4 Exact journal reference

When exact operational evidence is required, use an Operation Journal Reference:

```json
{
  "operation_id": "op_example",
  "journal_revision": 3,
  "contract_version": "1"
}
```

This reference identifies one immutable journal revision.

It must not be replaced by:

- operation ID alone;
- filename;
- greatest revision;
- newest timestamp;
- or current pointer without reading the selected revision.

## 6.5 Operation intent digest

Every operation series has one immutable `intent_digest`.

The digest is lowercase SHA-256 over a deterministic canonical encoding of the operation request.

The encoded request includes all contract-significant intent, including:

- operation kind;
- exact primary target;
- affected targets;
- requested canonical outcomes;
- predecessor expectations;
- operation-specific policy references;
- and ordered intent where order is semantically significant.

The digest excludes generated operational facts such as:

- operation ID;
- journal revision;
- staging path;
- process identifier;
- lock acquisition time;
- and recovery observations.

The intent digest supports exact replay detection.

It does not prove that the requested operation is authorized or valid.

## 6.6 Exact replay

A repeated request using the same Operation Reference is an exact replay only when:

- `intent_digest` agrees;
- operation kind agrees;
- exact target set agrees;
- requested outcomes agree;
- predecessor expectations agree;
- and all operation-specific intent agrees.

An exact replay may return:

```text
existing prepared operation
existing partial operation requiring recovery
existing committed operation
existing completed operation
```

The service must report the actual state.

## 6.7 Contradictory reuse

Reusing one `operation_id` with different intent is an integrity error.

Portia must not:

- overwrite the original journal;
- create a second unrelated operation series under the same ID;
- or reinterpret the original operation from the newer request.

## 6.8 Same intent with a different operation ID

Submitting semantically similar intent under a different operation ID does not automatically make the second request a replay.

Application validation must examine current canonical state and conflict rules.

The architecture does not define a workspace-wide automatic semantic-operation deduplication service.

## 6.9 Operation-kind vocabulary

Operation Journal version 1 will use this closed initial vocabulary:

```text
create_work
create_record
update_record
apply_amendment
transition_lifecycle
correct_history
activate_successor
consolidate_duplicates
create_dependency
migrate_representation
correct_ownership
exceptionally_remove
rebuild_projection
regenerate_current_view
integrity_scan
repair_operation
```

A later record family may require a new operation kind.

Adding a new kind requires a new compatible operation-journal contract version or another explicitly versioned extension strategy. Unknown operation kinds are not silently accepted.

## 6.10 Operation scope

Every operation declares one primary scope:

```text
work
class
workspace
graph
operation
```

### Work scope

A work-scoped operation identifies one exact Portia work.

### Class scope

A class-scoped operation identifies one Core-owned `class_id`.

Class scope does not give Portia authority to change Core class or roster records.

### Workspace scope

Workspace scope means the currently selected and validated Paper Data Suite workspace.

The journal does not invent a suite-wide workspace identity.

Workspace containment and selected-root agreement remain application invariants.

### Graph scope

Graph scope is used when the coordinated operation crosses work or class boundaries.

Examples include:

- ownership correction;
- cross-work successor topology;
- several-work Dependency recovery;
- or workspace-level integrity evaluation.

Graph scope still requires an explicit bounded target set.

### Operation scope

Operation scope is used by a repair, recovery, acknowledgement, suppression, or maintenance operation targeting another exact operation.

## 6.11 Primary and affected targets

Every operation declares:

- one `primary_target`;
- zero or more unique `affected_targets`.

Targets compose existing exact Portia references where possible.

Initial target branches are:

```text
Portia work
Portia work record
Exceptional Removal certificate
class
workspace
operation
```

The target list is part of operation intent.

A later discovered record cannot be silently added to the write set. The operation must return to preflight and publish a new journal revision describing the expanded plan before canonical mutation.

## 6.12 Scope is not authorization

Operation scope states the bounded graph the operation intends to evaluate or change.

It does not establish:

- user identity;
- institutional authority;
- source access;
- exceptional-removal permission;
- legal authority;
- or privacy permission.

Authorization evidence remains operation-specific and is validated separately.

---

# 7. Approved Decision 3: Immutable Operation-Journal Revisions and Explicit Current Selection

## 7.1 Decision

Portia adopts immutable Operation Journal revisions plus an explicit current pointer.

One operation series is stored at:

```text
<PDS workspace>/
  portia/
    operations/
      <operation_id>/
        revisions/
          1.json
          2.json
          ...
        current.json
```

The journal series is workspace-scoped operational state.

It is not stored beneath every affected work root.

Affected work roots may expose derived links to the operation, but those links are not independently editable journals.

## 7.2 Why immutable revisions

An operation may be interrupted while:

- staging;
- publishing a journal update;
- committing canonical steps;
- verifying a write;
- compensating;
- clearing locks;
- or rebuilding derived state.

Immutable revisions preserve what the process had durably reported at each stage.

A single mutable journal file would make it harder to distinguish:

- prior accepted progress;
- interrupted replacement;
- contradictory retry;
- and later recovery conclusions.

## 7.3 Journal revision identity

One exact journal revision is identified by:

```text
operation_id
+
journal_revision
+
contract_version
```

`journal_revision` is a positive integer beginning at 1.

A later revision contains the exact previous revision number.

Journal revisions form one linear predecessor chain.

Branching journal histories are an integrity error.

## 7.4 Current pointer

`current.json` explicitly selects the journal revision governing ordinary operation inspection.

The pointer contains only the minimum exact selection data:

```json
{
  "schema_version": "1",
  "record_type": "operation_current_pointer",
  "operation_id": "op_example",
  "journal_revision": 3
}
```

Current state is never selected from:

- greatest revision;
- newest timestamp;
- directory order;
- lexical filename order;
- or most recently modified file.

## 7.5 Publishing a journal revision

The conceptual journal-publication sequence is:

1. acquire the operation-series lock;
2. load and validate the selected current revision, if any;
3. verify the expected current revision;
4. exclusively create the next immutable revision;
5. flush and read back the new revision;
6. validate its predecessor and state transition;
7. atomically replace the current pointer;
8. read back the pointer and selected revision;
9. report any partial success precisely;
10. release the operation-series lock.

The exact filesystem implementation remains deferred.

## 7.6 Initial journal revision

Journal revision 1 is created only after preflight has produced a complete operation intent and bounded plan.

Its state is:

```text
prepared
```

Creating revision 1 does not mutate a canonical domain record.

If exclusive journal creation finds an existing operation series:

- exact intent may be reconciled as replay;
- different intent is an integrity error;
- malformed existing state requires recovery or quarantine.

## 7.7 Complete snapshots, not deltas

Every journal revision contains a complete bounded operational snapshot for the operation at that revision.

It includes the complete:

- operation identity and immutable intent;
- current operation state;
- preflight summary;
- write set;
- per-step dispositions;
- accepted canonical results known at that point;
- staged artifacts still relevant;
- partial-state summary;
- quarantine state;
- recovery or compensation decision, when applicable.

Journal revisions do not require replaying an unbounded delta log merely to inspect current operation state.

The predecessor chain remains necessary to audit how the operation progressed.

## 7.8 Journal state vocabulary

Operation Journal version 1 uses:

```text
prepared
staged
committing
committed
recovering
compensating
quarantined
completed
compensated
aborted
failed
```

### `prepared`

Preflight succeeded and a complete write plan exists. No canonical operation step has been accepted.

### `staged`

Every required pre-commit candidate artifact has been staged and verified. No canonical operation step has been accepted.

### `committing`

Canonical mutation has begun or may have begun. Recovery evidence must be preserved.

### `committed`

Every required canonical commit-gate step is accepted. Post-commit verification, cleanup, or rebuildable derived work may remain.

### `recovering`

The operation is evaluating or executing an evidence-based recovery disposition.

### `compensating`

The requested result cannot be completed safely and explicit evidence-preserving compensation is in progress.

### `quarantined`

The operation or affected target scope is blocked from ordinary use pending recovery, compensation, or review.

### `completed`

The requested canonical result and required finalization are complete.

Optional rebuildable derived work may still be unavailable only when the operation contract explicitly allows completion with a corresponding Integrity Finding.

### `compensated`

The original requested result was not completed, but accepted compensating records or pointer changes established the defined safe state.

### `aborted`

The operation ended before any canonical domain step was accepted. Pre-acceptance artifacts may be cleaned up under the accepted cleanup rules.

### `failed`

The operation cannot safely continue automatically.

A failed operation may still have accepted canonical steps. Its journal must report that partial state and any required quarantine or manual review.

## 7.9 State-transition principles

The initial normal path is:

```text
prepared
-> staged
-> committing
-> committed
-> completed
```

Pre-acceptance termination may use:

```text
prepared or staged
-> aborted
```

Interruption or contradiction after canonical mutation may use:

```text
committing or committed
-> recovering
-> committing, committed, completed, compensating, quarantined, or failed
```

Compensation uses:

```text
recovering
-> compensating
-> compensated, quarantined, or failed
```

Quarantine may later transition to:

```text
recovering
compensating
failed
```

`completed`, `compensated`, `aborted`, and `failed` are terminal for that operation series.

A later repair of terminal state uses a new `repair_operation` that references the original operation.

## 7.10 Same-state revisions

A later journal revision may retain the same operation state only when it records monotonic additional evidence or progress.

Examples include:

- another step moved from `durable` to `verified`;
- an additional readback observation was recorded;
- a lock-clearing dry run completed;
- a recovery scan discovered an exact additional affected target before mutation.

A same-state revision must not erase earlier accepted steps or weaken known durable state.

## 7.11 Per-step dispositions

The initial step-disposition vocabulary is:

```text
pending
staged
durable
verified
accepted
compensated
skipped
blocked
indeterminate
```

The normal acceptance path is:

```text
pending
-> staged
-> durable
-> verified
-> accepted
```

Not every step uses every intermediate state.

For example, a bounded canonical read may move from `pending` directly to `verified`, while a cleanup step may move from `pending` to `skipped`.

`compensated` may apply only to a step whose accepted effect was later addressed by explicit compensation.

`blocked` and `indeterminate` do not mean that no other step became durable.

## 7.12 Commit-gate classification

Every planned step belongs to one phase:

```text
canonical_gate
post_commit
cleanup
```

### `canonical_gate`

A step required before the requested canonical result may be considered committed.

### `post_commit`

A required or optional operation finalization step performed after canonical commit.

Rebuildable projection regeneration is normally post-commit.

For exceptional removal, purging prohibited derived payload may be a canonical gate because privacy safety depends on it.

### `cleanup`

Removal of transient artifacts or safely clearable coordination artifacts.

Cleanup failure does not erase accepted canonical state.

## 7.13 Orphan journal revisions

A journal revision may be written and verified while pointer publication fails.

Such a revision is durable operational evidence but is not automatically current.

Portia must not select it merely because it has the greatest revision.

Recovery must evaluate:

- the selected current revision;
- the orphan revision's predecessor;
- its intent digest;
- its state transition;
- its recorded step evidence;
- and observed canonical state.

An exact unique unselected successor may be explicitly selected through recovery. Contradictory or branching revisions require quarantine or review.

## 7.14 Missing current pointer

Journal revisions without `current.json` are not treated as a completed operation series.

Recovery must determine whether the series is:

- an interrupted initial journal publication;
- a pointer-loss condition;
- a contradictory branch;
- or malformed operational state.

No current revision is inferred from timestamps or revision numbers alone.

## 7.15 Journal content minimization

The journal records:

- typed references;
- safe relative paths;
- digests;
- expected state;
- dispositions;
- bounded reason codes;
- and minimum recovery facts.

It must not copy complete:

- Event narratives;
- Accounts;
- Observations;
- Communications;
- removed payload;
- student names;
- credentials;
- or sibling-module manifests

merely to make recovery convenient.

## 7.16 Journal schema direction

Later schema work should evaluate these public contracts:

```text
schemas/v1/identifiers/portia-operation-id.schema.json
schemas/v1/references/operation-ref.schema.json
schemas/v1/references/operation-journal-ref.schema.json
schemas/v1/operations/operation-journal.schema.json
schemas/v1/operations/operation-current-pointer.schema.json
```

Reusable step, digest, path, target, and partial-state contracts may be separate schemas only where they have genuine reuse value.

---

# 8. Decisions Remaining

Later design slices must resolve:

1. preflight snapshots and exact expected prior state;
2. workspace-relative path and digest contracts;
3. complete write-set and step structure;
4. staging placement and same-filesystem requirements;
5. exclusive canonical creation;
6. revision-aware canonical replacement;
7. deterministic lock scope and acquisition order;
8. one-file atomic replacement and durability assumptions;
9. recoverable multi-record commit order;
10. partial-success reporting;
11. pre-acceptance cleanup;
12. post-acceptance compensation;
13. recovery dispositions and missing-journal behavior;
14. repair mode and quarantine;
15. coordinated lifecycle and history operations;
16. successor activation and duplicate consolidation;
17. migration and ownership-correction recovery;
18. exceptional-removal recovery;
19. Dependency gating;
20. Integrity Finding versioning and operational code vocabulary;
21. acknowledgement and suppression records;
22. derived-index families and common metadata;
23. deterministic source inventories and source snapshots;
24. complete candidate build, verification, and atomic installation;
25. missing, stale, corrupt, and incompatible derived-state behavior;
26. current-view regeneration;
27. privacy-minimized diagnostics;
28. public schema organization;
29. Issue #12 contract reconciliation;
30. and final cross-repository drift checks.

## 9. Current implementation boundary

No production filesystem mutation is introduced by Decisions 1–3.

The current design establishes:

```text
what kind of persisted evidence exists
how an operation is identified
how exact replay is distinguished
where the journal series lives
how journal revisions are selected
which top-level operation states exist
```

Later slices will define the remaining operation and derived-state contracts before any public schema is treated as final.
