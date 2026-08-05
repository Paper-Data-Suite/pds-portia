# Portia Coordinated Persistence, Recovery, and Derived-Index Contracts

**Status:** In development — through Decision 9
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

# 11. Approved Decision 7: Lock Identity, Scope, Ordering, and Conservative Clearing

## 11.1 Decision

Portia uses explicit exclusive lock records to coordinate writers that may affect the same operational or canonical scope.

A lock:

- prevents a conflicting writer from beginning the protected mutation;
- identifies the operation that owns the coordination claim;
- preserves minimum diagnostic metadata;
- and supports exact inspection and conservative clearing.

A lock does not:

- establish canonical identity;
- prove authorization;
- prove that its owner process is still active;
- prove that the protected target exists;
- make a multi-file operation atomic;
- or replace operation-journal evidence.

## 11.2 Lock namespace

Workspace-scoped lock records are stored beneath:

```text
<PDS workspace>/
  portia/
    locks/
      <lock_id>.json
```

The lock namespace is bounded and separate from:

- canonical Portia work roots;
- operation-journal revisions;
- staged artifacts;
- and derived projections.

A lock path is derived from a validated stable lock identity.

User-supplied arbitrary paths must not determine the lock location.

## 11.3 Stable lock identity

Lock identifiers use:

```text
lock_<64-lowercase-hex-digits>
```

The hexadecimal suffix is the SHA-256 digest of the deterministic canonical encoding of the lock key.

The lock key includes:

```text
lock_scope
+
normalized protected target
```

The lock ID is stable for the same protected scope.

It must not encode human-readable student, class, work, or record information.

## 11.4 Lock scopes

The initial lock scopes are:

```text
operation
workspace
class
work
record
derived_projection
```

### `operation`

Protects one Operation Journal series, its current pointer, and operation-owned coordination state.

### `workspace`

Protects an explicitly bounded workspace-wide Portia mutation.

Workspace locks are exceptional because they block broad work.

They must not be used merely because acquiring narrower locks is inconvenient.

### `class`

Protects Portia mutations whose safe evaluation requires exclusive access to one class scope.

A class lock does not grant authority to modify Core-owned class or roster records.

### `work`

Protects one exact Portia work and its same-work records against conflicting writes.

### `record`

Protects one exact Portia work-record representation when the operation contract proves that broader work locking is unnecessary.

### `derived_projection`

Protects installation or replacement of one exact derived-projection kind and scope.

It does not block canonical writes unless the operation separately owns the required canonical lock scopes.

## 11.5 Protected targets

A lock target uses a normalized branch appropriate to its scope.

Examples include:

```text
operation reference
exact Portia work reference
exact Portia work-record reference
class ID
workspace marker
derived projection kind + exact projection scope
```

Lock normalization must preserve exact identity and must not rely on display labels, filenames, or directory enumeration.

## 11.6 Lock conflict hierarchy

Application validation enforces these initial conflicts:

- a workspace lock conflicts with every Portia mutation lock in the workspace;
- a class lock conflicts with work and record locks within that class;
- a work lock conflicts with record locks within that work;
- two record locks conflict only when they protect the same exact record;
- two operation locks conflict only when they protect the same operation series;
- two derived-projection locks conflict when projection kind and scope agree;
- and operation-specific validation may require a broader conflict where one derived installation is safety-critical to the canonical mutation.

A narrower lock cannot bypass a conflicting broader lock.

## 11.7 Minimum necessary scope

An operation must acquire the narrowest lock set that safely protects:

- its precondition recheck;
- staged candidate validation;
- canonical-gate writes;
- current-pointer publication;
- and operation-specific safety effects.

The operation must not acquire broad locks merely to conceal an incomplete target analysis.

## 11.8 Complete lock set before canonical mutation

The prepared journal records the complete intended lock set.

Before canonical mutation:

1. every required lock is acquired;
2. every acquired lock matches the journaled lock identity;
3. the complete set is revalidated;
4. and every protected precondition is rechecked.

An operation must not acquire an unplanned additional canonical lock after mutation may have begun.

A newly required lock after that boundary triggers recovery, compensation, quarantine, or a new repair operation.

## 11.9 Deterministic acquisition order

Locks are acquired in ascending order by this tuple:

```text
scope_rank
normalized_lock_key
lock_id
```

The initial scope ranks are:

```text
1 operation
2 workspace
3 class
4 work
5 record
6 derived_projection
```

Within one scope rank, the normalized lock key is compared bytewise using its deterministic UTF-8 encoding.

Every operation computes and records the complete ordered lock list before acquisition.

The implementation must not acquire locks in discovery order, dictionary order, or filesystem enumeration order.

## 11.10 Multiple operation locks

A repair or recovery action may need to coordinate:

- its own operation series;
- and one or more target operation series.

All required operation locks are included in the same ordered lock set and sorted by normalized operation identity.

The repair operation must not acquire one operation lock, inspect another, and later acquire the second in an inconsistent order.

## 11.11 Lock creation

Lock acquisition uses exclusive creation.

If the lock path already exists:

- the operation does not overwrite it;
- the existing lock is read and validated;
- exact same-operation reentrancy is evaluated only under an accepted operation-specific rule;
- otherwise the operation reports a conflict, recovery condition, or malformed lock.

Version 1 should not permit general recursive or reentrant lock ownership.

## 11.12 Lock record contents

A lock record contains minimum coordination metadata comparable to:

```text
schema_version
record_type
lock_id
lock_scope
protected_target
owning_operation
acquired_at
deployment_instance_id
process_instance_id
```

`deployment_instance_id` and `process_instance_id` are opaque diagnostic tokens.

They do not establish that the process remains active.

The lock record must not contain:

- canonical payload;
- student names;
- Event narratives;
- credentials;
- authorization secrets;
- removed content;
- or complete operation plans.

## 11.13 Lock fingerprint

Every lock observation records an exact content fingerprint:

```text
workspace-relative path
SHA-256 digest
byte length
```

The fingerprint binds later release or clearing to the exact inspected bytes.

The lock ID alone is insufficient because a lock may have been replaced after inspection.

## 11.14 Lock release by owner

Normal lock release requires:

- the exact lock identity;
- the exact observed fingerprint;
- agreement with the owning operation;
- confirmation that the protected mutation no longer requires the lock;
- and unchanged lock bytes immediately before removal.

If the lock changed, release stops and recovery begins.

A missing lock during an active mutation is an integrity condition.

## 11.15 Age does not prove staleness

Neither of these facts proves that a lock is stale:

```text
old acquired_at
old filesystem modification time
```

A long-running process, suspended host, clock skew, or delayed recovery may produce an old valid lock.

Portia must not automatically clear a lock based on age.

## 11.16 Conservative external clearing

Clearing a lock outside normal owner release requires:

1. identify the exact lock;
2. read and validate it;
3. record its exact fingerprint;
4. identify the owning operation;
5. inspect the selected journal and canonical state;
6. obtain external evidence that no active writer owns the lock;
7. perform a dry-run clearing evaluation;
8. reread and confirm the fingerprint is unchanged;
9. remove only that exact lock;
10. record the clearing through a recovery or repair operation;
11. and rerun affected integrity validation.

External evidence may include deployment-specific process inspection or an explicit operator assertion supported by the local environment.

The schema cannot establish that evidence.

## 11.17 Dry-run clearing

A dry run reports:

- exact lock reference;
- exact fingerprint;
- owning operation;
- protected target;
- selected journal revision;
- known durable steps;
- potential conflicts;
- and whether clearing would be structurally permitted if the external no-owner assertion is supplied.

A dry run does not modify the lock.

## 11.18 Lock replacement is prohibited

A lock is never updated in place to transfer ownership.

Ownership transfer requires:

- release or conservative clearing of the exact old lock;
- reevaluation;
- and exclusive creation of a new lock record.

Replacing lock bytes at the same path would defeat fingerprint-protected clearing.

## 11.19 Lock loss during commit

If a required lock disappears or changes after canonical mutation may have begun:

- no additional canonical step proceeds automatically;
- the operation publishes partial state when possible;
- affected targets are treated as requiring recovery;
- and operation-specific validation determines whether quarantine is required.

The operation must not simply reacquire the lock and continue without reconciling observed state.

## 11.20 Lock and journal ordering

The operation-series lock protects publication of journal revisions and the current pointer.

Target locks protect canonical and projection mutation.

The future implementation may release and reacquire only the operation-series lock between journal publications when it can prove that:

- target locks remain held;
- the selected journal expectation remains exact;
- and no concurrent recovery can acquire the full required lock set.

The simpler safe implementation may retain the complete lock set through the canonical commit gate.

The accepted behavior must be documented and tested before production use.

## 11.21 Lock cleanup failure

Failure to release a lock after canonical commit does not undo accepted canonical state.

It produces:

- structured partial success;
- an operation or lock recovery obligation;
- and an Integrity Finding when the stale coordination condition persists.

The operation must not report ordinary completion while required locks remain without an explicitly allowed deferred release state.

## 11.22 Public schema direction

Later schema work should evaluate:

```text
schemas/v1/identifiers/portia-lock-id.schema.json
schemas/v1/operations/operation-lock.schema.json
```

Lock fingerprinting should compose the common content-fingerprint contract rather than define another digest shape.

---

# 12. Approved Decision 8: One-File Durability and Recoverable Multi-Record Commit

## 12.1 Decision

Portia distinguishes:

```text
atomic replacement of one directory entry
from
recoverable completion of one coordinated operation
```

A supported filesystem primitive may atomically install or replace one file.

It does not make all canonical records, journal revisions, current pointers, locks, quarantine records, and derived projections one transaction.

Multi-record Portia operations therefore use:

- deterministic write ordering;
- immutable operation-journal evidence;
- exact per-step verification;
- explicit commit gates;
- and evidence-based recovery.

## 12.2 Filesystem capability preflight

Before staging or commit, the implementation must establish that every byte-producing step can use the required local filesystem primitives.

The capability evaluation includes:

- source staging and destination reside on a compatible filesystem;
- destination parent is validated and contained;
- exclusive creation is supported for create steps;
- same-filesystem atomic replacement is supported for replace steps;
- regular-file semantics are available;
- required flush and synchronization operations are available or their limitations are explicitly handled;
- and the environment is not known to provide weaker semantics than the operation requires.

When a required primitive cannot be verified, the operation fails closed before canonical mutation.

## 12.3 Honest durability language

The architecture uses these terms precisely:

### `durable`

The implementation completed its documented write and synchronization protocol and the file is observable at the intended path.

### `verified`

The implementation reread the installed bytes and confirmed:

- exact fingerprint;
- schema validity;
- identity;
- path agreement;
- and required local invariants.

### `accepted`

The step satisfied every operation-specific acceptance condition.

The design does not claim immunity from:

- hardware failure;
- storage-controller defects;
- filesystem corruption;
- unsupported network filesystems;
- malicious external mutation;
- or backup failure.

## 12.4 Exclusive-create protocol

The conceptual protocol for one `exclusive_create` step is:

1. confirm required locks remain owned;
2. revalidate `must_be_absent`;
3. verify the staged candidate fingerprint;
4. ensure the destination parent is contained and suitable;
5. create the destination exclusively;
6. write the exact candidate bytes;
7. flush the file;
8. synchronize the file where supported;
9. synchronize the containing directory where required and supported;
10. reread the destination;
11. verify the exact fingerprint and contract;
12. verify identity and path agreement;
13. mark the step `accepted` in a new journal revision.

If exclusive creation reports that the destination exists, the writer does not overwrite it.

## 12.5 Revision-aware replacement protocol

The conceptual protocol for one `revision_aware_replace` step is:

1. confirm required locks remain owned;
2. resolve the exact destination again;
3. revalidate `must_match`;
4. verify exact prior content fingerprint;
5. verify required semantic cross-checks;
6. verify the staged candidate fingerprint;
7. flush and synchronize the staged candidate;
8. atomically replace the destination with the staged candidate;
9. synchronize the containing directory where required and supported;
10. reread the destination;
11. verify the intended fingerprint, contract, identity, and path;
12. mark the step `accepted` in a new journal revision.

The old representation is not retained as an implicit backup unless its contract already preserves it canonically.

Required historical evidence must exist through explicit canonical records.

## 12.6 Pointer-replacement protocol

An `atomic_pointer_replace` step follows the revision-aware replacement protocol, with additional validation that:

- the pointer identity is correct;
- the expected selected revision agrees;
- the intended selected revision exists and validates;
- the intended revision belongs to the same series;
- and operation-specific monotonicity or rollback rules permit the selection.

A pointer is never published before its selected immutable revision is durably verified.

## 12.7 Derived-installation protocol

An `install_derived_replacement` step must install one complete verified candidate or publish one explicit current-generation pointer.

The source snapshot must be rechecked immediately before installation.

If the source changed, the candidate is not installed.

Detailed derived-rebuild rules remain for a later decision.

## 12.8 One-file ambiguity

A write may become visible at the destination while final synchronization, readback, or journal publication fails.

Such a result is not reported as clean failure.

The step disposition becomes:

- `durable` when installation is confirmed but full verification is incomplete;
- `verified` when bytes and local structure are confirmed;
- `accepted` only when all step conditions are satisfied;
- or `indeterminate` when the process cannot establish which state occurred.

The operation then returns structured partial success or recovery required.

## 12.9 Commit preparation

Before the first canonical-gate write, Portia must:

1. own the complete ordered lock set;
2. verify the selected prepared or staged journal revision;
3. verify the complete staged candidate set;
4. recheck every required preflight observation;
5. recheck operation intent and write set;
6. verify no conflicting lock or operation appeared;
7. publish and select a `committing` journal revision;
8. and verify that journal selection.

If `committing` cannot be durably selected, canonical mutation does not begin.

## 12.10 Safety-oriented write ordering

Within the deterministic write set, operation-specific order follows these general priorities:

1. create immutable canonical destination or evidence records;
2. verify those new records;
3. update mutable current projections;
4. transition predecessors or affected current records;
5. publish explicit current pointers or selected representations;
6. perform safety-critical availability or derived-purge steps;
7. record canonical commit;
8. perform ordinary rebuildable post-commit work;
9. perform cleanup.

The exact operation family may refine this order.

It must preserve these safety principles:

- a predecessor is not made superseded before the successor exists and verifies;
- a current pointer is not advanced before its selected revision verifies;
- a mutable status is not changed without the required append-only history being available;
- a migration source is not displaced before the destination and certificate verify;
- and removal is not considered complete while prohibited payload remains ordinarily available.

## 12.11 Journal publication after accepted steps

After every canonical-gate step becomes accepted, Portia publishes a new complete journal revision recording:

- the accepted disposition;
- exact installed fingerprint;
- exact path;
- acceptance time;
- remaining steps;
- and any changed partial-state summary.

The operation does not rely only on an in-memory list of completed writes.

If journal publication fails after a canonical write, recovery compares the intended step with observed canonical bytes.

## 12.12 Canonical commit point

The operation reaches its canonical commit point when every `canonical_gate` step is accepted.

At that point Portia publishes and selects a `committed` journal revision.

The `committed` revision records:

- every accepted canonical-gate step;
- exact resulting references and fingerprints;
- current pointer selections;
- unresolved post-commit work;
- remaining locks;
- quarantine state;
- and any active Integrity Findings known at commit.

Canonical commit does not require ordinary rebuildable projections to be current unless the operation contract classifies a specific projection or purge as a canonical gate.

## 12.13 Commit publication ambiguity

All canonical-gate records may be accepted while publication of the `committed` journal revision or its current pointer fails.

The operation is not assumed uncommitted.

Recovery must evaluate:

- the last selected journal revision;
- any orphan journal successor;
- all canonical-gate target bytes;
- pointer selections;
- and operation-specific invariants.

A unique exact completed graph may be reconciled as committed through recovery.

## 12.14 Post-commit phase

After canonical commit, the operation may perform:

- rebuildable projection regeneration;
- current-view regeneration;
- operation-recovery queue maintenance;
- ordinary cache invalidation;
- nonessential diagnostics;
- and cleanup.

Each post-commit step remains journaled.

A failure in optional rebuildable work does not invalidate accepted canonical records.

It may prevent `completed` when the operation contract requires a fresh view, or it may permit completion with an active derived-state finding.

## 12.15 Reader behavior during commit

Ordinary readers must not synthesize a confident current graph from known partial operation state.

When a relevant operation is `committing`, `recovering`, `compensating`, or `quarantined`, an authoritative reader must:

- use an exact pre-operation representation only where the operation contract proves that it remains valid;
- use an exact accepted post-operation representation only where the commit state proves it;
- or return blocked, unverified, or indeterminate state.

A reader must not fill missing pieces by:

- following successors;
- choosing newest files;
- selecting greatest revisions;
- or trusting stale derived views.

## 12.16 Discovering relevant in-progress operations

A later derived recovery queue may accelerate discovery of operations affecting a target.

That queue is not authoritative.

A safety-sensitive reader or writer must use:

- the exact operation or lock references already known;
- a verified current affected-operation projection;
- or a bounded scan of the operation and lock namespaces required by the target scope.

A missing queue does not prove that no operation is active.

## 12.17 Lock retention through commit

Required target locks remain held until:

- every canonical-gate step is accepted;
- the `committed` journal revision is durably selected or commit-publication ambiguity is recorded;
- and operation-specific safety conditions permit release.

A privacy-critical exceptional-removal operation may retain locks through required derived-payload purge.

Ordinary optional projection regeneration should not retain broad canonical locks unnecessarily.

## 12.18 Interruption boundaries

The operation journal must make these interruption points diagnosable:

```text
before staging
during staging
after complete staging
after selecting committing
after each canonical write
after each readback
after every accepted-step journal update
after all canonical gates
during committed-journal publication
during post-commit work
during cleanup
during lock release
```

Recovery must not assume that an interrupted process stopped between high-level steps.

## 12.19 External mutation

If canonical bytes, staged bytes, pointers, locks, or journal state change outside the protected operation:

- no further canonical step proceeds automatically;
- exact mismatches are recorded;
- the operation enters recovery, quarantine, or failure according to risk;
- and no later timestamp is treated as authority.

## 12.20 Unsupported filesystem behavior

When the environment cannot provide an accepted atomic replace, exclusive create, or containment guarantee, the later implementation must either:

- fail before mutation;
- use another separately accepted persistence backend;
- or obtain a future architecture amendment that defines a weaker but still recoverable protocol.

The implementation must not silently downgrade guarantees.

## 12.21 Production implementation boundary

This decision defines the contract-level write protocol.

It does not select:

- one Python standard-library call;
- one Windows API;
- one POSIX system call;
- one database;
- or one synchronization library.

The later implementation must document how each supported platform satisfies the accepted steps.

---

# 13. Approved Decision 9: Structured Partial Success, Cleanup, and Compensation

## 13.1 Decision

Portia treats partial success as a first-class result whenever an operation may have changed durable state without reaching clean completion.

The governing rule is:

```text
generic failure
must never conceal
possible or confirmed durable effects
```

The operation result, selected journal revision where possible, and Integrity Findings must describe the known state precisely.

## 13.2 Outcome vocabulary

The initial service-level outcome vocabulary is:

```text
completed
replayed
rejected
conflict
partial_success
recovery_required
compensated
failed
```

### `completed`

The operation reached journal state `completed`.

### `replayed`

An exact prior operation result was returned without repeating its canonical writes.

The response also reports the prior operation's actual terminal or active state.

### `rejected`

Validation, authorization, policy, compatibility, or preflight prevented mutation.

No canonical step became durable.

### `conflict`

Expected prior state, lock ownership, operation identity, or exclusive scope disagreed before mutation.

No new canonical step became durable through the rejected attempt.

### `partial_success`

One or more effects may be or are durable, but the operation has not reached a safe terminal result.

### `recovery_required`

The observed state cannot be completed or compensated safely without an explicit recovery evaluation.

This outcome may accompany `partial_success`.

### `compensated`

The operation reached journal state `compensated`.

### `failed`

The operation cannot continue automatically.

A failed operation may still have durable effects, which must be reported separately.

## 13.3 Direct result versus durable journal

A service response reports what the process observed.

The selected Operation Journal is the durable operational record when publication succeeded.

If journal publication failed:

- the response must say so;
- durable canonical effects must still be reported;
- and the operation must not claim that the response alone completed durable journaling.

Recovery later reconciles the workspace.

## 13.4 Partial-state structure

The operation's `partial_state` contains bounded structured fields comparable to:

```text
durability_assessment
accepted_steps
verified_steps
durable_unverified_steps
indeterminate_steps
remaining_canonical_steps
remaining_post_commit_steps
current_pointer_changes
staged_artifacts
held_or_possible_locks
quarantined_targets
active_findings
recommended_disposition
```

The structure uses step IDs, typed references, relative paths, fingerprints, and bounded codes.

It must not duplicate substantive canonical payload.

## 13.5 Durability assessment

The initial operation-level durability assessment is:

```text
none
possible
confirmed
```

### `none`

The process confirmed that no canonical-gate step became durable.

### `possible`

The process cannot prove whether one or more planned effects became durable.

### `confirmed`

At least one canonical-gate step is known durable or accepted.

This assessment does not state that the entire operation committed.

## 13.6 Per-step evidence

Every nonpending step result records as applicable:

- action;
- exact target;
- intended path;
- observed path;
- intended fingerprint;
- observed fingerprint;
- disposition;
- acceptance result;
- and bounded failure or limitation code.

A path without a fingerprint is insufficient for exact cleanup or recovery.

## 13.7 Partial-success triggers

Structured partial success is required when any of these may occur:

- destination creation succeeded but final synchronization failed;
- atomic replacement may have succeeded but readback failed;
- accepted bytes exist but journal update failed;
- all canonical gates succeeded but committed-pointer publication failed;
- a current pointer changed but final operation verification failed;
- cleanup failed after accepted state;
- required lock release failed;
- operation interruption occurred after selecting `committing`;
- compensation became partially durable;
- or a safety-critical post-commit step remains incomplete.

## 13.8 Failure messages

A direct error message must not say only:

```text
save failed
operation failed
rollback failed
```

when durable state may exist.

It must identify:

- the Operation Reference;
- the latest known journal revision;
- durability assessment;
- affected step IDs;
- recovery requirement;
- and whether ordinary use is blocked or quarantined.

## 13.9 Pre-acceptance cleanup

Pre-acceptance cleanup may remove:

- staged candidate files;
- temporary pointer candidates;
- empty operation-owned staging directories;
- and other proven-unaccepted transient artifacts.

Cleanup requires:

- exact operation ownership;
- exact step ownership;
- exact fingerprint when bytes exist;
- confirmation that the artifact is not the accepted destination;
- confirmation that active recovery does not require it;
- and journal permission.

Pre-acceptance cleanup is not canonical rollback.

## 13.10 Aborted operations

An operation may enter `aborted` only when Portia confirms:

- no canonical-gate step became durable;
- no current pointer changed;
- no canonical availability changed;
- and remaining artifacts are transient or operational only.

If any canonical effect is possible, the operation cannot be classified as aborted.

## 13.11 Cleanup after commit

After canonical commit, cleanup may remove only:

- exact staged leftovers;
- temporary candidate files;
- releasable lock records;
- and other operation-owned transient artifacts.

Cleanup must not remove:

- accepted canonical records;
- accepted immutable journal revisions;
- active quarantine evidence;
- required compensation evidence;
- or files merely because they were part of the original preflight snapshot.

## 13.12 Cleanup failure

Cleanup failure does not erase accepted canonical state.

It produces:

- partial success when the operation cannot finalize;
- a recovery obligation;
- and an Integrity Finding when the leftover artifact or lock persists.

An operation may reach `completed` with a harmless deferred transient cleanup only if the final contract explicitly permits it and records a nonblocking finding.

Sensitive staged payload should normally prevent completion until securely handled.

## 13.13 Canonical rollback is rejected

Portia rejects generic rollback that deletes or rewrites an accepted canonical record to make the operation appear never to have occurred.

This applies even when:

- the record was created seconds earlier;
- the user immediately changed their mind;
- a later step failed;
- or the accepted record is inconvenient for recovery.

Accepted history remains visible.

## 13.14 Compensation

Compensation is an explicit, journaled, evidence-preserving operation phase that establishes a defined safe state after accepted effects prevent simple pre-acceptance cleanup.

Compensation may:

- create a correcting or superseding canonical record;
- create a lifecycle transition;
- create a lifecycle-history correction;
- restore an explicit current pointer to an already accepted revision;
- quarantine a target;
- create a required Dependency disposition;
- or perform exceptional removal only under the accepted Exceptional Removal contract.

Compensation must not silently alter domain meaning.

## 13.15 Compensation plan

The prepared journal records operation-specific compensation capabilities before canonical mutation.

A compensation plan identifies:

- which accepted steps may require compensation;
- safe compensation actions;
- required authorization or policy;
- exact evidence needed to choose a branch;
- and conditions requiring quarantine or manual review instead.

The plan does not require Portia to predict every hardware or external corruption case.

## 13.16 Compensation after newly discovered conditions

A newly discovered condition after mutation may use the predeclared compensation plan only when:

- the condition fits an accepted branch;
- the required authorization exists;
- affected scope remains bounded;
- and exact observed state supports the branch.

Otherwise the operation enters quarantine or failure and a new repair operation is required.

## 13.17 Compensation journal state

The normal compensation path is:

```text
recovering
-> compensating
-> compensated
```

Each compensating write is represented as an explicit step with:

- its own step ID;
- exact precondition;
- intended result;
- disposition;
- and accepted canonical evidence.

The complete journal snapshot preserves both original and compensating steps.

## 13.18 Compensated step disposition

An original step may be marked `compensated` only when:

- the original accepted effect remains preserved;
- explicit compensating evidence exists;
- the defined safe state is verified;
- and the journal links the compensation step.

`compensated` does not mean that the original bytes were removed or that the operation never happened.

## 13.19 Pointer restoration

Restoring an explicit current pointer to a prior accepted revision is compensation only when:

- the pointer contract permits rollback;
- the exact currently selected pointer still matches;
- the prior revision remains valid;
- intervening canonical records remain preserved;
- and the restoration is journaled.

Pointer restoration does not delete the temporarily selected revision.

## 13.20 Lifecycle compensation

When an accepted current-state change must be counteracted, compensation follows the record family's legal lifecycle and correction contracts.

It must not:

- edit the prior Lifecycle Transition;
- delete transition history;
- reset status without a new accepted transition;
- or fabricate an earlier effective time.

## 13.21 Successor and migration compensation

An accepted successor, migration destination, or ownership-corrected destination is not deleted as generic compensation.

Depending on accepted state, recovery may:

- complete the remaining activation;
- create an invalidating or superseding transition;
- restore a pointer;
- quarantine the new representation;
- create another explicit correction;
- or require manual review.

The exact operation-family decisions remain later in this design.

## 13.22 Exceptional-removal boundary

Generic compensation and cleanup cannot delete accepted canonical payload.

When actual removal is required, the Exceptional Removal contract governs:

- authority;
- evidence;
- target availability;
- certificate;
- dependencies;
- and derived-payload purge.

A compensation plan cannot bypass that contract.

## 13.23 Compensation failure

If compensation becomes partial or indeterminate:

- the operation remains `compensating`, becomes `quarantined`, or becomes `failed`;
- structured partial state reports both original and compensating durable effects;
- affected current use is blocked where safety requires;
- and a later repair operation may be required.

Compensation failure is not hidden by returning the original operation's failure alone.

## 13.24 Post-commit derived failure

Failure to rebuild an ordinary derived projection after canonical commit does not invalidate canonical records.

The operation may:

- remain `committed` until required finalization succeeds;
- reach `completed` with a permitted active derived-state finding;
- or require recovery when the projection is safety-critical.

A missing or corrupt derived projection must not be filled from partial operation memory.

## 13.25 Privacy-critical post-commit work

For Exceptional Removal and any later privacy-critical operation, removing prohibited payload from derived artifacts may be classified as a canonical gate rather than optional post-commit work.

The operation cannot report canonical commit or completion while prohibited payload remains available contrary to the accepted removal contract.

## 13.26 Recommended disposition vocabulary

Partial-state reporting uses the initial recommended-disposition vocabulary:

```text
retry_preflight
resume
reconcile_as_complete
complete_remaining_steps
compensate
restore_pointer
clear_lock_after_external_verification
quarantine
abandon_preacceptance_artifacts
rebuild_projection
require_manual_review
```

A recommendation is not authority to execute the action.

The later recovery decision validates exact evidence again.

## 13.27 Integrity Finding integration

Persistent operational defects use the existing Integrity Finding categories:

```text
persistence_recovery
derived_state
```

Current Issue #12 codes already support conditions including:

```text
operation_incomplete
canonical_write_partial
orphaned_canonical_artifact
content_digest_mismatch
recovery_required
derived_index_drift
projection_stale
```

Later decisions will determine whether additional codes require Integrity Finding version 2.

Issue #13 must not modify version 1 in place.

## 13.28 Public schema direction

Later schema work should evaluate:

```text
schemas/v1/operations/operation-partial-state.schema.json
schemas/v1/operations/operation-result.schema.json
```

A service result need not become a durable independent record when the complete information already belongs in the Operation Journal.

The final schema set should avoid duplicating one partial-state vocabulary across journal and API contracts.

---

# 14. Decisions Remaining

Later design slices must resolve:

1. recovery dispositions and recovery state evaluation;
2. missing, corrupt, orphaned, and branching journal behavior;
3. repair mode and quarantine;
4. coordinated lifecycle and history operations;
5. successor activation and duplicate consolidation;
6. migration and ownership-correction recovery;
7. exceptional-removal recovery;
8. Dependency gating;
9. Integrity Finding operational code vocabulary and version audit;
10. acknowledgement and suppression records;
11. derived-index families and common metadata;
12. deterministic source inventories and source snapshots;
13. complete candidate build, verification, and atomic installation;
14. missing, stale, corrupt, and incompatible derived-state behavior;
15. current-view regeneration;
16. privacy-minimized diagnostics;
17. public schema organization;
18. Issue #12 contract reconciliation;
19. and final cross-repository drift checks.

## 15. Current implementation boundary

No production filesystem mutation is introduced by Decisions 1–9.

The current design now establishes:

```text
durable state categories and authority
operation identity, intent, scope, and replay
immutable journal revisions and explicit current selection
complete preflight and exact observation boundaries
relative-path and byte-fingerprint evidence
exclusive-create and guarded-replacement preconditions
ordered write sets and staged candidates
stable lock identity, conflicts, ordering, and clearing
one-file durability and recoverable multi-record commit
structured partial success
pre-acceptance cleanup
post-acceptance compensation
```

Later slices will define the recovery state machine, repair and quarantine, exact coordinated operation-family plans, integrity administration, and complete derived-state rebuilding before public operational schemas are finalized.
