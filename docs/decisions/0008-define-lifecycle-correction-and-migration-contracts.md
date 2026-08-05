# ADR 0008: Define Shared Lifecycle, Correction, and Migration Contracts

* **Status:** Accepted
* **Date:** 2026-08-05
* **Decision owners:** Portia maintainers
* **Related issue:** [#12 — Define shared lifecycle, amendment, correction, and migration contracts](https://github.com/Paper-Data-Suite/pds-portia/issues/12)
* **Related design:** [`docs/design/portia-lifecycle-amendment-correction-and-migration-contracts.md`](../design/portia-lifecycle-amendment-correction-and-migration-contracts.md)
* **Related examples:** [`docs/examples/portia-lifecycle-amendment-correction-and-migration-examples.md`](../examples/portia-lifecycle-amendment-correction-and-migration-examples.md)
* **Related validation:** [`docs/validation/issue-12-lifecycle-amendment-correction-and-migration-validation.md`](../validation/issue-12-lifecycle-amendment-correction-and-migration-validation.md)
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

## Context

Portia record families persist practical current-state fields, but current state alone cannot explain how a record reached that state, why it changed, which representation is authoritative, or how a correction affected exact references and dependent records.

The Event-family and Work Relationship contracts already preserve canonical records and use successor-owned forward replacement links. They did not yet provide one accepted architecture for:

* append-only lifecycle history;
* nonmaterial amendment;
* material correction;
* disagreement;
* invalidation and supersession;
* dependencies;
* representation migration;
* work-root and class-ownership correction;
* exceptional administrative removal;
* or rebuildable integrity findings.

Later Portia record families must be able to adopt this infrastructure without inventing incompatible meanings or silently rewriting historical records.

## Decision

Portia adopts a shared lifecycle, correction, migration, and integrity architecture with independently versioned public contracts. The architecture standardizes envelopes, exact references, chronology, attribution, and validation boundaries without imposing one universal status vocabulary on every record family.

### Current status and append-only history

A canonical record may persist its current `status` for direct loading. Append-only lifecycle-transition records preserve the accepted history of status changes. The two form a consistency-bound dual model:

```text
persisted current status
+ creation baseline
+ selected append-only transition history
= validated lifecycle state
```

A mismatch is an integrity finding. Portia does not silently choose one side or rewrite history.

The public history contracts are:

```text
schemas/v1/lifecycle/lifecycle-transition.schema.json
schemas/v1/lifecycle/lifecycle-history-correction.schema.json
```

A lifecycle-history correction selects a replacement history head. It does not mutate or delete the earlier transition chain.

### Amendment and material correction

A nonmaterial change may use an append-only Amendment record with explicit before-and-after values and a target-revision precondition:

```text
schemas/v1/corrections/amendment.schema.json
```

Amendment is conservative. It must not change canonical identity, ownership, subject, target, source, basis, status, or material meaning.

A material correction creates a successor record. The successor retains exact forward references to its predecessor or predecessors. Predecessors become superseded only through a coordinated lifecycle operation; merely proposing a successor does not change predecessor state.

### Invalidation and supersession

Invalidation means the record is no longer a valid current assertion for the applicable workflow and may have no replacement.

Supersession means another canonical record replaces the predecessor for a defined purpose. Neither state deletes the historical record. References to a predecessor continue to identify that exact predecessor unless the referring record is itself explicitly corrected.

### Statements of disagreement

Disagreement is represented by its own append-oriented canonical record:

```text
schemas/v1/corrections/statement-of-disagreement.schema.json
```

A Statement of Disagreement does not mutate, invalidate, supersede, or adjudicate its target. It preserves an attributable position while leaving the disputed record and later review visible.

### Dependencies

Cross-record dependency is represented explicitly:

```text
schemas/v1/dependencies/dependency.schema.json
```

A Dependency records one dependent, one dependency target, strength, evaluation scope, and purpose. Dependency effects are proportionate and record-family-specific. Portia does not apply one automatic lifecycle cascade.

Exact references never silently follow successors. A superseded, removed, inaccessible, or unsupported target produces explicit resolution and review behavior.

### Migration

Representation or contract-version migration is distinct from semantic correction:

```text
schemas/v1/migrations/record-migration.schema.json
```

Migration preserves logical identity, record family, work root, lifecycle meaning, and substantive semantics while changing representation. It requires explicit source and destination representations and a registered compatible transformer.

Migration must not hide a substantive repair. When source content is semantically wrong, the applicable amendment, invalidation, or successor workflow remains required.

### Ownership correction

Incorrect class ownership or work-root placement uses an explicit certificate:

```text
schemas/v1/corrections/ownership-correction.schema.json
```

An ownership correction identifies exact source and destination work or work-record representations. Destination work and child records receive fresh ownership identities where required. Child mappings, incoming references, dependencies, and current-use state must be reconciled explicitly.

Filesystem relocation is not ownership correction authority. References are not silently retargeted to the destination.

### Exceptional removal

Ordinary workflows do not hard-delete accepted canonical records. Narrow legal, privacy, security, accepted-test-data, and unrecoverable-corruption cases use an exceptional-removal certificate:

```text
schemas/v1/removals/exceptional-removal.schema.json
```

The certificate preserves exact target identity, authorization, minimal content evidence, effective time, and available lifecycle evidence without retaining prohibited substantive payload. Removal changes exact availability; it is not a `deleted` lifecycle state and is not ordinary correction.

### Record-family upgrades

Issue #12 selectively versions only record contracts whose accepted wire shape changes:

```text
schemas/v3/event-participant.schema.json
schemas/v3/event-participant-role.schema.json
schemas/v2/work-relationship.schema.json
```

Participant and Role version 3 replace same-work predecessor links with complete exact work-record references. Work Relationship version 2 accepts predecessor versions 1 and 2. All three add `work_root_corrected` and `contract_migrated` successor reasons while preserving their prior domain semantics.

Event remains at version 2 because its existing exact predecessor work references already support migration, correction, consolidation, and ownership replacement.

### Integrity findings

Integrity findings are deterministic, rebuildable diagnostics rather than canonical domain records:

```text
schemas/v1/projections/integrity-finding.schema.json
```

A finding has a deterministic `finding_key`, revision-sensitive `evaluation_key`, stable rule identity, category and code, severity, assessment, effects, scope, exact targets, bounded evidence, and observation time.

A finding has no canonical record identifier, lifecycle, supersession, amendment, migration, or user-cleared state. It clears only when reevaluation no longer detects the violation or limitation.

Acknowledgement, suppression, scan history, quarantine mechanics, and operational caches belong to Issue #13 and must never become the sole evidence of canonical state.

### Public schema organization

Portia retains version-first immutable public paths. Existing published schemas are not reorganized or rewritten. New canonical records live beneath their contract-version directory, shared components remain in semantic subdirectories, and noncanonical projections live beneath:

```text
schemas/v1/projections/
```

There are no mutable `latest` or `current` schema aliases. The schema catalog is a checked tooling index, not canonical contract identity.

### Validation boundary

JSON Schema establishes local structure, closed envelopes, controlled vocabularies, identifier syntax, exact reference shape, and structural conditionals.

Application validation remains responsible for:

* exact authoritative resolution;
* storage and envelope agreement;
* lifecycle legality and history reconciliation;
* materiality;
* authorization;
* timestamp ordering across records;
* successor and dependency graphs;
* duplicate identity and topology;
* migration semantic preservation;
* ownership and child reconciliation;
* removal execution and derived-payload purge;
* deterministic finding generation;
* and coordinated atomic or recoverable persistence.

Issue #13 owns operation journals, persistence ordering, rollback, crash recovery, repair-mode writes, quarantine, and rebuildable operational indexes.

## Consequences

### Positive

* Later Portia records can share one lifecycle and correction architecture without sharing one state machine.
* Current status remains practical while historical transitions remain independently auditable.
* Nonmaterial amendment, material correction, invalidation, supersession, disagreement, migration, ownership correction, and removal have distinct public meanings.
* Exact historical references remain stable across replacements and migrations.
* Dependencies and integrity findings support explicit review and enforcement without silent cascades or hidden repair.
* Public schema versions remain immutable and independently evolvable.

### Costs

* Material correction and ownership repair may require coordinated creation of several canonical records.
* Applications must maintain application validators for cross-record invariants that JSON Schema cannot express.
* Consumers must distinguish exact historical resolution from current-successor navigation.
* Issue #13 must provide robust atomicity, recovery, quarantine, and rebuild behavior before production persistence is safe.

## Rejected alternatives

### One universal lifecycle state machine

Rejected because Events, Roles, Dependencies, later Supports, and other record families have different semantic states and transition authority.

### Pure event sourcing

Rejected because routine loading should not require replaying an unbounded history merely to determine current status.

### Mutable history or in-place material correction

Rejected because it erases what previously existed and destabilizes exact references and auditability.

### No silent successor following

Rejected because it changes the meaning of stored references and can conceal correction, consolidation, migration, removal, or disagreement.

### Migration as a generic repair mechanism

Rejected because representation change must not conceal semantic correction.

### Filesystem relocation as ownership repair

Rejected because storage movement alone does not establish new canonical identity, child mapping, lifecycle reconciliation, or reference disposition.

### Ordinary hard deletion

Rejected because accepted records require historical preservation and exact resolution. Narrow exceptional removal retains a durable certificate.

### Canonical lifecycle-bearing integrity findings

Rejected because findings are rule-derived projections that may clear, recur, or change after reevaluation.

## Implementation boundary

This ADR defines accepted semantic and public-schema contracts. Production operation records, transactional persistence, atomic multi-record changes, rollback, crash recovery, finding caches, acknowledgement, suppression, and quarantine remain assigned to Issue #13.
