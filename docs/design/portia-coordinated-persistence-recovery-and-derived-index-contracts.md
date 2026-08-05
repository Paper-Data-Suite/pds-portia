# Portia Coordinated Persistence, Recovery, and Derived-Index Contracts

**Status:** In development — through Decision 6
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

# 8. Approved Decision 4: Preflight and Exact Observation Boundaries

## 8.1 Decision

Every operation begins with a complete bounded preflight before any canonical domain mutation.

Preflight establishes:

```text
what the operation intends
+
what exact state was observed
+
which invariants were evaluated
+
which targets may be affected
+
which writes would be required
+
which facts remain unavailable or indeterminate
```

A preflight is successful only when every required fact for the operation kind is either:

- confirmed from authoritative state;
- confirmed from a verified current derived projection whose source snapshot still matches;
- or explicitly declared unnecessary by the operation contract.

A required fact that is unavailable, authorization-limited, unsupported, contradictory, or stale prevents successful preflight.

## 8.2 Preflight is read-only

Preflight must not:

- create or modify canonical domain records;
- publish lifecycle transitions;
- select a journal revision;
- acquire long-lived commit locks;
- create a current pointer;
- rebuild a missing derived index implicitly;
- repair a malformed record;
- follow a successor silently;
- retarget a reference;
- or remove an artifact.

Temporary in-memory serialization and bounded read-only validation do not constitute mutation.

A later implementation may create short-lived operating-system resources while computing preflight, but those resources must not become durable workspace state.

## 8.3 Initial journal publication follows successful preflight

Operation Journal revision 1 records the accepted preflight result.

The sequence is:

```text
receive bounded operation request
-> resolve and validate selected workspace
-> perform preflight
-> construct exact operation intent and write set
-> compute intent digest
-> exclusively create operation series
-> publish prepared journal revision 1
```

No canonical domain write may occur before the prepared journal is durably selected.

If operation-series creation discovers an existing exact intent, the service evaluates replay rather than repeating preflight blindly.

## 8.4 Preflight scope

Preflight must identify:

- one primary target;
- every initially known affected target;
- every planned canonical or operational write;
- every required current pointer;
- every required lifecycle head;
- every required predecessor or successor;
- every required Dependency;
- every incoming reference relevant to the operation;
- every authorization or policy reference required by the operation;
- and every derived projection relied upon for safe planning.

The scope must be bounded and explicit.

Preflight must not recursively crawl the entire workspace merely because the operation references one record.

## 8.5 Canonical source priority

Preflight obtains domain facts from canonical records.

A derived projection may narrow discovery or accelerate evaluation only when:

1. the projection contract is supported;
2. the projection is complete for the required scope;
3. its recorded source snapshot is available;
4. the current canonical source snapshot matches;
5. the projection is not quarantined or known stale;
6. and the operation contract permits reliance on that projection.

Otherwise Portia must perform a bounded canonical evaluation or return an indeterminate blocking result.

## 8.6 Exact observed-representation entry

For every representation whose state matters to the operation, preflight records one observed-representation entry.

The conceptual entry contains:

```text
target
representation_role
expected_presence
workspace_relative_path
contract_version
content_digest
byte_length
observed_at
selected_state
```

`selected_state` contains only operation-relevant structured facts, such as:

- lifecycle status;
- selected lifecycle transition;
- selected journal revision;
- current pointer revision;
- migration representation role;
- exceptional-removal availability;
- or quarantine state.

It must not copy complete canonical payload merely to avoid rereading the source.

## 8.7 Presence expectations

The initial presence vocabulary is:

```text
must_be_absent
must_match
```

### `must_be_absent`

The target identity and canonical path must not already contain an accepted representation.

This expectation is used for exclusive creation.

### `must_match`

The target must exist and its exact prior bytes and contract-significant selected state must match preflight.

This expectation is used for revision-aware replacement, pointer replacement, and exact cleanup or quarantine actions.

Version 1 does not use a permissive `may_exist` precondition for canonical writes.

An operation that can validly handle either condition must preflight the observed branch and publish an exact branch-specific write plan.

## 8.8 Missing, malformed, and unsupported representations

Preflight distinguishes:

```text
expected absence
unexpected absence
malformed representation
unsupported contract
unresolved exact target
authorization-limited target
quarantined target
removed target
```

These outcomes are not interchangeable.

An expected absence may support exclusive creation.

The other outcomes require operation-specific blocking, recovery, quarantine, or historical behavior.

## 8.9 Contract and record-family agreement

For each observed representation, preflight validates:

- public contract version;
- record family;
- typed identity;
- envelope identity;
- canonical path agreement;
- selected workspace containment;
- and operation-kind compatibility.

A structurally valid record of the wrong family or scope is not an acceptable match.

## 8.10 Lifecycle and replacement observation

When lifecycle or replacement state matters, preflight records the exact selected state rather than a computed label alone.

Examples include:

```text
target persisted status
selected lifecycle-history head
selected history-correction record
exact predecessor set
exact active successor frontier
exact current migration representation
```

Preflight must not choose state from:

- newest timestamp;
- greatest contract version;
- lexical filename;
- directory order;
- or an unverified reverse index.

## 8.11 Dependency and incoming-reference observation

An operation that may affect current usability, replacement, migration, ownership, or removal must evaluate the relevant Dependencies and incoming references.

The preflight result records:

- the evaluation scope;
- the authoritative records or verified projection used;
- exact required Dependency identities;
- exact advisory Dependency identities;
- unresolved or authorization-limited scope;
- and the operation-specific disposition required for each relevant dependency.

A missing derived index does not establish that the dependency or incoming-reference set is empty.

## 8.12 Authorization and policy observation

Where an operation requires authorization or policy, preflight records an exact reference or bounded evidence object.

Examples include:

- exceptional-removal authorization;
- repair-mode authorization;
- finding-suppression policy;
- source-access authorization;
- or a compatible migration-transformer reference.

An authorization reference states which evidence was evaluated.

It does not cause JSON Schema validation or operation scope to establish authority.

## 8.13 Preflight findings

Preflight may produce:

```text
blocking validation result
indeterminate result
nonblocking review result
Integrity Finding projection
```

Routine rejected input that has not produced durable workspace inconsistency should normally return a direct validation result rather than create persistent integrity noise.

An Integrity Finding is appropriate when preflight detects an existing canonical or operational condition that remains after the request ends.

## 8.14 Preflight freshness

A successful preflight is valid only for the exact observed state.

Before staging or canonical mutation, Portia must recheck every required precondition according to the later commit decision.

If a required representation changed, the operation must not silently update its expected state.

It must:

- return to preflight before canonical mutation;
- publish a new prepared journal revision with the revised bounded plan;
- or fail or quarantine when mutation may already have begun.

## 8.15 Scope expansion before mutation

Before any canonical step is accepted, newly discovered required targets may be added only by:

1. stopping the current progression;
2. repeating the affected preflight evaluations;
3. updating the immutable intent where the newly discovered target changes requested intent;
4. or preserving the same intent while publishing a new complete prepared plan where the target was a deterministic consequence;
5. and selecting a new prepared journal revision.

The architecture must define operation-specific rules for whether newly discovered targets change intent.

## 8.16 Scope expansion after mutation

After canonical mutation may have begun, the operation must not silently broaden its write set.

A newly discovered required target produces:

- recovery;
- compensation;
- quarantine;
- or manual review.

A later repair uses a new `repair_operation` when the original operation cannot safely continue within its accepted scope.

## 8.17 Preflight snapshot digest

The prepared journal records a deterministic `preflight_snapshot_digest`.

The digest binds the ordered, normalized preflight entries that are relevant to safe execution.

It is distinct from:

- the operation `intent_digest`;
- each representation's exact `content_digest`;
- and a derived projection's source-snapshot digest.

The same intent may be preflighted against different canonical state and therefore produce different preflight snapshot digests.

## 8.18 Preflight reproducibility

Given the same:

- operation intent;
- supported contract set;
- selected workspace;
- authorization context;
- policy versions;
- canonical bytes;
- selected pointers;
- and verified derived inputs,

preflight should produce the same normalized plan and preflight snapshot digest.

Time of observation may be recorded separately and must not make the logical snapshot nondeterministic.

## 8.19 Application boundary

JSON Schema may validate preflight-entry structure.

Application logic must establish:

- actual containment;
- exact target resolution;
- authoritative source selection;
- content digest;
- selected lifecycle state;
- dependency completeness;
- authorization;
- policy compatibility;
- and freshness.

---

# 9. Approved Decision 5: Paths, Content Digests, and Expected Prior State

## 9.1 Decision

Portia uses exact workspace-relative paths and exact byte digests as operational evidence while preserving typed references as canonical identity.

The governing distinction is:

```text
typed reference
= identity

workspace-relative path
= validated location evidence

content digest + byte length
= exact representation evidence
```

None substitutes for the others.

## 9.2 Workspace-relative path contract

A serialized operational path is relative to the selected Paper Data Suite workspace.

It uses POSIX separators regardless of host platform.

Examples:

```text
classes/english10_p2/modules/portia/work/evt_example/work.json
portia/operations/op_example/revisions/1.json
```

A structurally valid path must:

- be nonempty;
- be relative;
- use `/`, not `\`;
- contain no NUL;
- contain no empty component;
- contain no `.` or `..` component;
- contain no URI scheme;
- contain no drive prefix;
- and remain within the accepted maximum length.

Lexical validity does not prove containment.

## 9.3 Path containment and symlink safety

Application validation must resolve every operational path beneath the exact selected workspace.

It must reject:

- absolute paths;
- traversal;
- symlink escape;
- junction or reparse-point escape where applicable;
- unexpected mount boundaries where required primitives cannot be guaranteed;
- nonregular files where a regular file is required;
- and identity-derived paths that disagree with the target reference.

A path previously validated during preflight must be revalidated before mutation.

## 9.4 Path is not identity

Portia must not identify a record through:

- stored path alone;
- filename;
- directory name;
- or a scan for matching bytes.

The typed target and canonical path must agree.

A record found at the wrong path is an integrity condition, not permission to reinterpret its identity.

## 9.5 Durable path reporting

Operation journals and structured results may report validated workspace-relative paths when required for:

- recovery;
- partial-success reporting;
- staged-artifact inspection;
- lock inspection;
- or derived-projection replacement.

They must not report host-specific absolute paths in canonical or public operational records.

A user-facing implementation may display an absolute path locally when authorized, but that display is not persisted contract identity.

## 9.6 Exact content digest

Version 1 uses:

```text
algorithm = sha256
value = 64 lowercase hexadecimal characters
```

The digest is computed over the exact bytes read from or intended for the recorded path.

It is not computed over:

- a parsed object;
- normalized whitespace;
- a reconstructed dictionary;
- or an assumed canonical serialization

unless the exact operation contract explicitly defines those bytes as the representation.

## 9.7 Byte length

Every exact content observation records the nonnegative byte length.

Digest plus byte length supports:

- readback verification;
- staged-candidate verification;
- exact cleanup;
- lock fingerprinting;
- replay diagnosis;
- and source inventories.

Byte length is not a substitute for the digest.

## 9.8 Deterministic operation intent versus representation bytes

The operation `intent_digest` is computed over a deterministic canonical encoding of operation intent.

A representation `content_digest` is computed over exact stored or staged bytes.

Therefore two byte-distinct serializations may represent semantically similar JSON while still having different content digests.

Portia must not treat semantic similarity as exact representation equality during guarded replacement.

## 9.9 Expected absence

An exclusive-create step records:

```text
expected_presence = must_be_absent
```

and the exact intended target path.

Immediately before creation, application validation must confirm:

- the path does not exist;
- no accepted target with that identity exists elsewhere;
- no conflicting operation owns the exclusive scope;
- and the parent scope remains valid.

A preexisting path is not overwritten.

## 9.10 Existing target during exclusive creation

When the target exists, the service distinguishes:

### Exact replay candidate

The existing canonical representation, operation intent, and journal evidence exactly match a previously accepted result.

### Conflict

Another accepted representation owns the identity or path.

### Integrity failure

The existing bytes, envelope, path, or operation evidence are malformed or contradictory.

The low-level exclusive writer does not make this distinction by overwriting. Higher-level orchestration evaluates it.

## 9.11 Expected match

A guarded replacement step records:

```text
expected_presence = must_match
expected_content_digest
expected_byte_length
expected_contract_version
```

It may also record operation-significant semantic cross-checks such as:

```text
expected_updated_at
expected_status
expected_selected_transition
expected_pointer_revision
```

The exact byte digest is the primary representation concurrency token.

Semantic cross-checks strengthen validation but do not replace byte equality.

## 9.12 Revision-aware replacement

Immediately before replacing an existing representation, Portia must:

1. resolve the exact target again;
2. confirm identity and canonical path;
3. read the current bytes;
4. confirm byte length and content digest;
5. confirm contract version;
6. confirm required semantic cross-checks;
7. confirm the operation still owns the required lock scope;
8. and confirm the staged intended bytes remain unchanged.

Any mismatch prevents the replacement.

Last-write-wins is prohibited.

## 9.13 Mutable current records

A Portia domain record may persist a mutable current projection such as `status` or nonmaterial amended fields.

Guarded replacement of that file does not erase history when the operation also creates the required append-only canonical records.

For example:

```text
target status replacement
+
Lifecycle Transition exclusive creation
```

is one coordinated logical operation.

The target-file replacement remains revision-aware.

## 9.14 Immutable canonical records

An immutable canonical record is never updated through revision-aware replacement.

Correction produces:

- another canonical record;
- another immutable revision;
- a current-pointer change;
- a lifecycle or history correction;
- or explicit compensation,

according to the record contract.

## 9.15 Pointer replacement

A current pointer is replaced only when its exact selected prior state matches.

The expected state includes:

- exact operation or series identity;
- expected selected revision;
- expected pointer content digest;
- and expected pointer contract version.

A missing pointer and an existing pointer are distinct operation branches.

A pointer is never advanced by selecting the greatest available revision automatically.

## 9.16 Exact cleanup and quarantine targeting

Cleanup or quarantine of a transient or operational artifact requires an exact observed digest or fingerprint when the artifact may change concurrently.

Portia must not remove or quarantine a path merely because its filename matches an operation ID.

If the bytes changed after inspection, the action must stop and reevaluate.

## 9.17 Candidate-result digest

Every planned write that creates or replaces bytes records an `intended_content_digest` and `intended_byte_length` before commit.

The staged candidate must match them.

The accepted readback must also match them.

If the intended bytes change, the write step and applicable journal revision must change before mutation.

## 9.18 JSON serialization boundary

Issue #13 does not require every existing Portia record to be reserialized into one new byte format.

The future implementation must choose and document a stable canonical writer for new writes.

Operational equality remains exact byte equality for the representation observed and guarded.

Migration to a different serialization is a representation migration when contract-significant representation changes require it.

## 9.19 Digest privacy boundary

A digest is minimum-necessary evidence, not a guarantee that sensitive low-entropy content cannot be guessed.

Operational contracts must not publish unsalted hashes of narrowly enumerable sensitive fields as substitutes for full-record digests.

Exceptional Removal retains its separately accepted salted evidence rules.

## 9.20 Required reusable lexical contracts

Later schema work should evaluate:

```text
schemas/v1/common/workspace-relative-path.schema.json
schemas/v1/common/sha256-digest.schema.json
schemas/v1/common/content-fingerprint.schema.json
```

`content-fingerprint` should compose algorithm, digest, and byte length rather than repeat that structure inconsistently.

---

# 10. Approved Decision 6: Ordered Write Sets and Staged Candidate Artifacts

## 10.1 Decision

Every prepared operation contains one complete ordered write set.

The write set states:

```text
which effects are planned
in what deterministic order
against which exact targets and paths
under which prior-state expectations
with which intended bytes
and in which commit phase
```

The write set is part of the complete journal snapshot.

It is not an informal implementation log.

## 10.2 Step identity

Each operation step has an opaque operation-local identifier:

```text
step_<opaque-id>
```

The step ID is stable across journal revisions for the same planned effect.

It must not encode:

- student identity;
- record content;
- operation result;
- path;
- or sequence number.

A new materially different planned effect receives a new step ID.

## 10.3 Step sequence

Every step has a positive integer `sequence`.

Within one complete write set:

- sequences are unique;
- sequences begin at 1;
- sequences are contiguous;
- array order agrees with sequence;
- and execution order follows sequence unless the final operation contract explicitly permits safe parallel execution.

Version 1 should prefer deterministic sequential ordering over parallel writes.

## 10.4 Step phases

Each step belongs to exactly one phase:

```text
canonical_gate
post_commit
cleanup
```

The meaning follows Decision 3.

A post-commit or cleanup step cannot be used to conceal a write that is necessary for canonical correctness or privacy safety.

Operation-specific validation decides whether derived-payload purge is a canonical gate.

## 10.5 Initial action vocabulary

The initial write-action vocabulary is:

```text
exclusive_create
revision_aware_replace
atomic_pointer_replace
install_derived_replacement
quarantine_artifact
remove_transient
```

### `exclusive_create`

Create one new canonical or durable operational representation only when the exact target is absent.

### `revision_aware_replace`

Replace one mutable current canonical or operational representation only when exact expected prior bytes and semantic preconditions match.

### `atomic_pointer_replace`

Publish an explicit current selection only when the expected pointer state matches.

### `install_derived_replacement`

Install one complete verified derived candidate or select one complete verified generation.

### `quarantine_artifact`

Make an exact artifact unavailable to ordinary resolution without changing its domain lifecycle.

### `remove_transient`

Remove an exact proven-unaccepted artifact.

This generic action must not remove an accepted canonical domain record.

Exceptional Removal of canonical payload is an operation-specific protocol, not a generic write action.

## 10.6 Step target and representation role

Each write step identifies:

- exact target;
- representation role;
- intended workspace-relative path;
- action;
- phase;
- expected prior state;
- intended result state;
- and operation-specific reason code where needed.

Initial representation roles include:

```text
canonical_domain
operational_revision
operational_pointer
derived_projection
staged_candidate
transient_artifact
quarantine_state
```

The representation role does not change the authority of the referenced record.

## 10.7 Step precondition

Every mutating step contains exactly one expected-state branch.

### Exclusive-create branch

Contains:

```text
expected_presence = must_be_absent
```

### Match branch

Contains:

```text
expected_presence = must_match
expected content fingerprint
expected contract version
required semantic cross-checks
```

A step cannot contain both branches.

## 10.8 Intended result

A byte-producing step records:

- intended contract version;
- intended content fingerprint;
- intended target path;
- and intended identity or pointer selection.

The journal may record the intended fingerprint without embedding the complete candidate payload.

## 10.9 Staging requirement

Every byte-producing canonical-gate step must be staged before canonical mutation.

Pointer replacement and small operational selection files should also use staged candidate bytes.

A future implementation may exempt an operation-specific action only through an accepted design amendment proving equivalent validation and recoverability.

## 10.10 Staging path

A staged candidate uses a validated operation-owned path on the same filesystem as its intended destination.

The initial conceptual layout is target-adjacent:

```text
<validated target parent>/
  .portia-staging/
    <operation_id>/
      <step_id>.candidate
```

For a target whose final parent does not yet exist, staging occurs beneath the nearest validated existing parent that will remain on the same filesystem.

Examples include:

```text
classes/<class_id>/modules/portia/work/.portia-staging/<operation_id>/
portia/operations/<operation_id>/.portia-staging/
```

The exact later implementation layout may refine the hidden directory name, but it must preserve the accepted containment and same-filesystem invariants.

## 10.11 Staging namespace is noncanonical

Staging directories:

- are excluded from canonical record enumeration;
- are excluded from ordinary derived-index inputs;
- are excluded from normal reference resolution;
- and do not establish record existence.

A staged Event is not a canonical Event.

A staged transition is not lifecycle history.

## 10.12 Staged-candidate metadata

The journal records for every staged candidate:

```text
step_id
staging_path
destination_path
contract_version
content fingerprint
staged_at
validation disposition
```

The metadata does not grant acceptance.

## 10.13 Candidate validation before commit

Before moving to `staged`, every required candidate must pass:

- exact byte fingerprint verification;
- JSON decoding where applicable;
- Draft 2020-12 schema validation;
- contract-version validation;
- envelope and target identity validation;
- intended destination-path validation;
- operation-specific local invariants;
- and staging containment and regular-file checks.

Cross-record invariants are evaluated against the intended post-operation graph, not only the current graph.

## 10.14 Complete staging gate

An operation may enter journal state `staged` only when:

- every required pre-commit candidate exists;
- every candidate matches its intended fingerprint;
- every candidate passed required validation;
- the complete write set remains current;
- no canonical step has been accepted;
- and required preflight observations remain valid or have been revalidated according to the operation contract.

## 10.15 Staging failure

A staging failure before any canonical mutation may lead to:

```text
prepared
-> aborted
```

or a later same-operation prepared revision when the intent remains unchanged and a deterministic candidate can be regenerated safely.

No accepted canonical record is deleted because staging failed.

## 10.16 Candidate regeneration

Regenerating a staged candidate is permitted before canonical mutation only when:

- operation intent is unchanged;
- the write step identity and intended semantic result are unchanged;
- the new exact bytes are recorded in a new journal revision;
- the preflight state still supports the plan;
- and the old staged candidate is removed only through exact fingerprinted cleanup.

If the intended semantic result changes, the operation must return to preflight and may require a different intent digest.

## 10.17 Staging after canonical mutation

Once any canonical-gate step may have become durable, Portia must not silently regenerate a missing or contradictory staged candidate.

Recovery must compare:

- journaled intended bytes;
- remaining staged bytes;
- accepted canonical bytes;
- and current operation scope.

The result may be resume, compensation, quarantine, or manual review.

## 10.18 Write-set mutation before commit

Before canonical mutation, a write-set change requires a new complete prepared journal revision.

The new revision must identify:

- retained steps;
- removed pre-acceptance steps;
- newly required steps;
- changed ordering;
- and whether the preflight or intent digest changed.

No existing accepted step may exist at this point.

## 10.19 Write-set mutation after commit begins

After canonical mutation may have begun, the accepted write set is frozen.

A newly required effect must be handled through:

- an operation-specific recovery branch already represented in the journal;
- explicit compensation;
- quarantine;
- or a new repair operation.

The original operation must not pretend that the newly discovered effect was always part of its prepared plan.

## 10.20 Step disposition monotonicity

Within the normal path, a step may advance:

```text
pending
-> staged
-> durable
-> verified
-> accepted
```

A later journal revision must not move a step backward.

`compensated`, `skipped`, `blocked`, and `indeterminate` require operation-specific justification.

A step known durable must never be reported later as merely pending.

## 10.21 Intended post-operation graph

Preflight and staging validate the intended graph assembled from:

```text
unchanged current canonical representations
+
staged candidate representations
+
planned pointer selections
+
planned availability or quarantine changes
```

Validation must not assume that array order or filesystem state during staging already represents the intended committed graph.

## 10.22 Staging privacy and permissions

Staged artifacts may contain the same sensitive information as their intended canonical targets.

A future implementation must apply permissions at least as restrictive as the destination and must avoid:

- world-readable temporary files;
- predictable public temporary locations;
- system-wide temporary directories when target-adjacent staging is required;
- diagnostic content dumps;
- and backup or synchronization behavior that exposes abandoned candidates.

The architecture does not claim that a dot-prefixed directory is a security boundary.

## 10.23 Staging cleanup

Pre-acceptance staged artifacts may be removed only when:

- their exact operation and step are known;
- the exact fingerprint still matches;
- they are not accepted canonical representations;
- they are not required for active recovery;
- and the selected journal permits cleanup.

Cleanup failure is reported but does not convert staged data into canonical state.

## 10.24 Public schema direction

Later schema work should evaluate:

```text
schemas/v1/identifiers/portia-operation-step-id.schema.json
schemas/v1/operations/operation-preflight-entry.schema.json
schemas/v1/operations/operation-write-step.schema.json
schemas/v1/operations/operation-staged-artifact.schema.json
```

The final schema set should avoid separate public files where `$defs` provide clearer reuse without creating independent contracts.

---

# 11. Decisions Remaining

Later design slices must resolve:

1. deterministic lock scope and acquisition order;
2. one-file atomic replacement and durability assumptions;
3. recoverable multi-record commit order;
4. partial-success reporting;
5. pre-acceptance cleanup completion;
6. post-acceptance compensation;
7. recovery dispositions and missing-journal behavior;
8. repair mode and quarantine;
9. coordinated lifecycle and history operations;
10. successor activation and duplicate consolidation;
11. migration and ownership-correction recovery;
12. exceptional-removal recovery;
13. Dependency gating;
14. Integrity Finding operational code vocabulary;
15. acknowledgement and suppression records;
16. derived-index families and common metadata;
17. deterministic source inventories and source snapshots;
18. complete candidate build, verification, and atomic installation;
19. missing, stale, corrupt, and incompatible derived-state behavior;
20. current-view regeneration;
21. privacy-minimized diagnostics;
22. public schema organization;
23. Issue #12 contract reconciliation;
24. and final cross-repository drift checks.

## 12. Current implementation boundary

No production filesystem mutation is introduced by Decisions 1–6.

The current design now establishes:

```text
durable state categories and authority
operation identity, intent, scope, and replay
immutable journal revisions and explicit current selection
complete preflight and observation boundaries
exact relative-path and byte-fingerprint evidence
exclusive-create and guarded-replacement preconditions
ordered write sets
target-adjacent staged candidates
```

Later slices will define locking, commit, partial success, compensation, recovery, coordinated domain-operation plans, integrity operations, and derived-state rebuilding before public operational schemas are finalized.
