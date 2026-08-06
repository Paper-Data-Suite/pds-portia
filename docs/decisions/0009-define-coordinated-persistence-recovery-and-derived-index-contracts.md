# ADR 0009: Define Coordinated Persistence, Recovery, and Derived-Index Contracts

* **Status:** Accepted
* **Date:** 2026-08-05
* **Decision owners:** Portia maintainers
* **Related issue:** [#13 — Define coordinated persistence, recovery, and derived-index contracts](https://github.com/Paper-Data-Suite/pds-portia/issues/13)
* **Related design:** [`docs/design/portia-coordinated-persistence-recovery-and-derived-index-contracts.md`](../design/portia-coordinated-persistence-recovery-and-derived-index-contracts.md)
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

## Context

ADR 0008 established canonical contracts whose accepted effects may span several files and record families.

Examples include:

* creating a Lifecycle Transition while updating the target's persisted status;
* creating a successor while superseding one or more predecessors;
* consolidating duplicates;
* reconciling required Dependencies;
* migrating one logical record between representation contracts;
* correcting ownership across class-qualified work roots;
* and making accepted substantive payload unavailable through Exceptional Removal.

A local filesystem may provide exclusive creation and atomic replacement for one file under supported conditions. It does not provide one atomic transaction across an arbitrary graph of:

```text
canonical records
current pointers
operation evidence
locks
quarantines
dependencies
derived indexes
```

A process may stop after one file becomes durable but before another write, readback, pointer update, journal update, derived rebuild, cleanup, or lock release.

Portia therefore needs one shared integrity architecture that can determine:

* what operation was intended;
* which exact prior state was validated;
* which writes were planned;
* which writes may already be durable;
* when canonical state is accepted;
* whether the operation committed;
* what recovery actions remain safe;
* and whether derived views may be trusted.

The architecture must remain compatible with the broader Paper Data Suite.

Core v0.6 demonstrates suite-level patterns including immutable revisions, explicit current pointers, expected-revision protection, exclusive creation, structured partial success, conservative lock clearing, and complete source-snapshot-bound rebuilding.

Meridian's current package foundation consumes official Core public contracts but does not yet implement producer ingestion, evidence projection, grading, reporting, or persistence.

Vitrine's current architecture uses immutable curation revisions, explicit current pointers, optimistic concurrency, nondestructive correction, and rebuildable views.

Portia aligns with those principles without importing sibling-private implementation code.

## Decision

Portia adopts the coordinated persistence, recovery, and derived-index architecture defined by Decisions 1–18 of the related design.

### State categories and authority

Portia distinguishes:

```text
canonical domain record
durable operational record
derived projection
transient artifact
```

Canonical records remain authoritative for domain meaning.

Operational records coordinate and recover work but do not replace canonical evidence.

Derived projections are rebuildable and nonauthoritative.

Transient artifacts may be removed only while proven unaccepted and unnecessary for recovery.

An incomplete Operation Journal is durable recovery evidence, not disposable cache data.

### Operation identity and replay

Operations use opaque workspace-scoped `op_` identifiers.

One operation represents one bounded intent with:

* an immutable intent digest;
* one operation kind;
* one primary scope;
* exact primary and affected targets;
* and one complete operation plan.

Exact replay requires agreement in all contract-significant intent.

Reusing an operation ID for different intent is an integrity error.

### Immutable journals and explicit current pointers

Each operation has immutable complete journal revisions and one explicit current pointer:

```text
portia/
  operations/
    <operation_id>/
      revisions/
        <revision>.json
      current.json
```

Current state is never selected from greatest revision, newest timestamp, filesystem modification time, filename, or directory order.

### Preflight before mutation

No canonical mutation begins until preflight validates:

* exact targets and current representations;
* contract and lifecycle state;
* relevant Dependencies and incoming references;
* authorization and policy evidence;
* canonical paths;
* candidate bytes;
* the complete write and lock sets;
* and recovery or compensation plans.

Preflight is read-only.

A required fact that is missing, unsupported, authorization-limited, contradictory, or stale blocks the operation or leaves it indeterminate.

### Identity, location, and representation evidence

Portia treats these separately:

```text
typed reference
= identity

workspace-relative path
= validated location evidence

SHA-256 digest + byte length
= exact representation evidence
```

Application validation still establishes actual containment, symlink safety, and identity-derived canonical path agreement.

### Exclusive creation and guarded replacement

New identities use exclusive creation.

Existing mutable representations and pointers use exact expected prior state, with byte fingerprints as the primary concurrency token.

Last-write-wins is prohibited.

A preexisting target is evaluated as replay, conflict, or integrity failure rather than overwritten.

### Ordered write sets and staging

Every prepared operation has one complete deterministic write set.

Each step identifies:

* stable step ID and sequence;
* phase and action;
* exact target and destination;
* expected prior state;
* intended fingerprint;
* and disposition.

Byte-producing canonical steps are staged on a compatible filesystem, fingerprinted, validated, and excluded from canonical resolution.

The write set is frozen once canonical mutation may have begun.

### Locking

Portia uses exclusive lock records with stable digest-derived `lock_` identifiers.

Initial scopes include:

```text
operation
workspace
class
work
record
derived_projection
```

The full set is acquired in deterministic order before canonical mutation.

A lock contains minimum coordination metadata.

Age alone never proves staleness.

External clearing requires exact fingerprinting, inspection of the owning operation, external evidence that no active writer owns the lock, and explicit recovery or repair journaling.

### One-file durability and multi-record recovery

One-file atomic replacement does not imply graph-wide atomicity.

Multi-record operations use deterministic ordering, immutable journal evidence, exact per-step readback, explicit commit gates, and recovery.

Step states distinguish:

```text
staged
durable
verified
accepted
```

A file may be durable even if final verification or journal publication fails.

### Acceptance, commit, and completion

Portia distinguishes:

```text
serialized
staged
durably installed
read-back verified
accepted as canonical
operation committed
post-commit work complete
operation completed
```

Canonical commit occurs when every `canonical_gate` step is accepted.

Ordinary rebuildable derived work is generally post-commit.

Privacy-critical payload purge may be a canonical gate.

### Partial success

A generic error must not conceal possible or confirmed durable effects.

Partial state records:

* durability assessment;
* accepted, verified, durable-unverified, and indeterminate steps;
* remaining canonical and post-commit work;
* pointer changes;
* staged artifacts;
* locks;
* quarantines;
* findings;
* and recommended disposition.

Blind retry and blind deletion are prohibited.

### Cleanup and compensation

Pre-acceptance cleanup may remove exact proven-unaccepted artifacts.

Accepted canonical records are not deleted to simulate rollback.

Post-acceptance correction uses explicit compensation such as:

* later canonical evidence;
* legal lifecycle transition;
* history correction;
* guarded pointer restoration;
* quarantine;
* or Exceptional Removal under its own contract.

Compensation preserves the original operation history.

### Recovery

Recovery constructs one exact observation over:

* the selected and reachable journal chain;
* staged artifacts;
* canonical records;
* pointers;
* locks;
* quarantine;
* Dependencies;
* incoming references;
* and derived state.

Recovery does not invent missing history or choose authority from timestamps or greatest revisions.

Accepted dispositions include:

```text
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

Recovery against unchanged state is idempotent.

### Journal corruption and branching

Missing pointers, missing selected revisions, corrupt revisions, predecessor gaps, intent mismatches, and branching histories are separate conditions.

An unselected linear successor is selected only through explicit recovery after exact validation.

Branches are not resolved by higher revision or later time.

Contradictory evidence requires quarantine or review.

### Repair mode

`repair_operation` is bounded and explicitly authorized.

Repair may bypass only a named ordinary gate required for the approved repair.

It never bypasses schema validation, typed identity, workspace containment, expected prior state, public versioning, journaling, readback verification, no-generic-hard-delete rules, or required removal authorization.

An unrestricted repair flag is prohibited.

### Quarantine

Quarantine uses opaque `qnt_` identity, immutable revisions, and an explicit current pointer.

It may block use, writes, operation completion, projection use, or require review.

Quarantine is operational rather than lifecycle state.

It does not silently mean invalidated, superseded, removed, or deleted.

Release requires an explicit verified operation and a new immutable revision.

### Coordinated domain operations

The journal coordinates but does not replace Issue #12 canonical records.

Operation ordering ensures, as applicable:

* Amendment evidence precedes guarded target replacement;
* transition evidence precedes persisted status replacement;
* successors verify before predecessor supersession;
* consolidation preserves every predecessor;
* required Dependencies receive explicit dispositions;
* migration destination and certificate verify before current selection changes;
* ownership-correction destination graphs verify before source retirement;
* and removal preserves authorization-bearing evidence while making prohibited payload unavailable.

Historical exact references are never silently retargeted.

### Exceptional Removal

Generic cleanup cannot remove accepted canonical payload.

Exceptional Removal requires exact target and fingerprint, authorization, containment, certificate evidence, lifecycle and Dependency reconciliation, ordinary-resolution verification, and prohibited derived-payload purge.

Emergency containment may precede complete evidence only under ADR 0008's narrow boundary.

The unresolved certificate and recovery obligations remain durable.

### Integrity Findings

Issue #13 continues to use Integrity Finding version 1.

Its operation-target shape is compatible with valid `op_` identifiers.

Stable rule IDs carry specific operational diagnosis.

No version 2 is introduced solely for narrower IDs or additional subcodes.

### Acknowledgement and suppression

Acknowledgement records review of one exact:

```text
finding_key + evaluation_key
```

It does not resolve or suppress the finding.

Suppression is revisioned, expiring, and presentation-only.

It is prohibited for critical, blocking, quarantine, unsafe authorization-limited, and retained-removed-payload findings.

Suppressed findings remain visible to validation, recovery, audit, and authorized maintenance.

### Derived projection generations

Derived projections use:

* opaque `dgen_` generation identities;
* complete immutable generations;
* explicit current pointers;
* common metadata;
* exact data fingerprints;
* contract and builder versions;
* source snapshots;
* and authorization scope.

Manual row repair is prohibited.

Malformed, corrupt, stale, incompatible, missing, or quarantined projections do not invalidate independently valid canonical records.

### Deterministic rebuild

A rebuild:

1. discovers only bounded documented namespaces;
2. inventories exact source paths, byte lengths, and digests;
3. computes a versioned deterministic source snapshot;
4. builds and validates a separate complete candidate;
5. rechecks the source snapshot;
6. installs a complete generation or explicit pointer;
7. and verifies current selection.

Changed sources prevent installation.

A partial candidate never becomes current.

### Missing derived state

A missing index does not prove an empty graph.

Safety-sensitive absence claims require a verified complete projection or an accepted bounded canonical scan.

Reads do not rebuild or repair projections implicitly.

### Current views

Current views are rebuildable projections over exact canonical and operational inputs.

They report verified, historical, superseded, invalidated, removed, quarantined, in-progress, unverified, indeterminate, authorization-limited, or unsupported state.

They do not silently repair disagreement, choose the newest successor, follow replacements, select greatest versions, reinterpret ownership, or reconstruct removed payload.

### Public contracts and compatibility

Issue #13 adds independently versioned identifier, common, reference, operation, and projection contracts under semantic directories.

It does not add new unversioned root schemas or add `operation_id` to every canonical record.

These accepted contracts remain unchanged:

```text
Event v2
Event Participant v3
Event Participant Role v3
Work Relationship v2
Lifecycle Transition v1
Lifecycle History Correction v1
Amendment v1
Statement of Disagreement v1
Dependency v1
Record Migration v1
Ownership Correction v1
Exceptional Removal v1
Integrity Finding v1
```

## Consequences

### Positive

* Multi-record operations gain one shared recoverability model.
* Exact prior-state checks prevent stale-writer overwrite.
* Immutable journals make interruption diagnosis deterministic.
* Partial success is explicit.
* Accepted domain evidence survives failure and compensation.
* Lock clearing is conservative.
* Quarantine blocks unsafe use without corrupting lifecycle.
* Derived indexes cannot become hidden authority.
* Complete rebuilds reduce mixed-snapshot drift.
* Current views remain honest when canonical inputs disagree.
* Issue #12 schemas remain stable.
* Portia aligns with Core, Meridian, and Vitrine while preserving module ownership.

### Costs

* Writers perform additional reads, staging, validation, journaling, and synchronization.
* Partial operations may temporarily block use.
* Journals, locks, quarantines, and generations add storage overhead.
* Recovery must handle explicit interruption boundaries.
* Safe operation may block when graph evaluation is incomplete.
* Exact byte fingerprints make serialization changes operationally significant.
* Some conditions require human review.
* Complete projection rebuilding may cost more than row mutation.
* Filesystem guarantees must be tested per platform.

## Alternatives Considered

### Best-effort sequential writes without journals

Rejected because interruption could leave durable canonical state without trustworthy intent or progress evidence.

### One mutable universal transaction record

Rejected because in-place mutation can obscure prior durable observations and concurrent recovery expectations.

### Claim graph-wide filesystem atomicity

Rejected because the local filesystem cannot provide that guarantee across arbitrary record graphs.

### Timestamp, newest-file, or greatest-revision selection

Rejected because those values do not establish authority.

### Last-write-wins replacement

Rejected because stale processes could overwrite newer accepted state.

### Delete accepted records as rollback

Rejected because it erases accepted evidence and disguises interruption history.

### Age-based stale-lock clearing

Rejected because age does not prove that no writer is active.

### Add operation identity to every canonical record

Rejected because the journal's exact write set provides correlation without mass schema versioning.

### Treat derived indexes as authoritative

Rejected because indexes may be missing, stale, incompatible, authorization-limited, locked, malformed, or corrupt.

### Patch derived rows manually

Rejected because local patches can mix source snapshots and conceal systematic errors.

### Rebuild during reads

Rejected because reads would gain hidden side effects and potentially use the wrong authorization or source snapshot.

### Silently follow successors or migrations

Rejected because exact references must continue to identify exact historical records.

### Treat Quarantine as lifecycle

Rejected because protective operational blocking and domain assertions have different authority and recovery requirements.

## Deferred Work

This ADR does not implement:

* production Python persistence services;
* path and filesystem services;
* lock acquisition;
* staged writes;
* journal publication;
* recovery execution;
* projection builders;
* integrity scans;
* teacher-facing maintenance workflows;
* distributed transactions;
* multi-host locking;
* cloud-sync conflict resolution;
* institutional authorization;
* retention or backup policy;
* or production workspace migration.

Issue #13 will now implement and validate the accepted public contracts, fixtures, examples, catalog entries, documentation, and offline tests.
