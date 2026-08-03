# Portia Lifecycle, Amendment, Correction, and Migration Contracts

**Status:** Working design — approved through Decision 2  
**Project:** Paper Data Suite  
**Module:** `pds-portia`  
**Issue:** `#12 — Define shared lifecycle, amendment, correction, and migration contracts`  
**Umbrella:** `#10 — Complete the Portia foundations milestone`  
**Date:** 2026-08-02  
**Branch:** `12-shared-lifecycle-amendment-correction-migration-contracts`

## 1. Purpose

This document defines Portia's shared architecture for lifecycle state, append-only lifecycle history, amendment, disagreement, correction, invalidation, supersession, dependency handling, duplicate consolidation, migration, and correction of wrongly owned or located work.

It applies first to:

- Event v2;
- Event Participant v2;
- Event Participant Role v2;
- Work Relationship v1;
- and later Portia record families.

This document is implementation-neutral. Production persistence, operation journals, atomicity, rollback, and crash recovery belong to Issue #13.

## 2. Governing contracts

This design must remain consistent with ADRs 0001–0007 and these current implementation-target schemas:

```text
schemas/v2/event.schema.json
schemas/v2/event-participant.schema.json
schemas/v2/event-participant-role.schema.json
schemas/v1/work-relationship.schema.json
```

Historical Event-family version-1 schemas remain immutable compatibility contracts.

## 3. Governing principles

1. Current state must remain practical to load directly.
2. Lifecycle history must be append-only and independently auditable.
3. Material correction must preserve prior canonical records.
4. Canonical records are not hard-deleted through ordinary workflows.
5. References are never silently retargeted to successors.
6. Migration must not conceal semantic correction.
7. Cross-record lifecycle effects require explicit domain validation rather than a universal cascade.
8. JSON Schema validates local structure; application validation enforces cross-record and lifecycle invariants.
9. Coordinated persistence and recovery mechanics are deferred to Issue #13.

---

# 4. Approved Decision 1: Current Status and Lifecycle History

## 4.1 Decision

Portia adopts a **consistency-bound dual model**:

- the canonical target record's persisted `status` is the authoritative current-state projection;
- append-only lifecycle-transition records are the authoritative history of status changes;
- the two must reconcile before the lifecycle state is considered valid.

Portia is not a pure event-sourced system, but lifecycle history is not optional commentary.

```text
canonical target status
+ creation baseline
+ append-only lifecycle transitions
= validated lifecycle state
```

## 4.2 Initial baseline

Initial canonical acceptance establishes the lifecycle baseline through:

```text
initial status
creation_source
created_at
created_by
```

Initial creation does **not** create a separate lifecycle-transition record. A transition records a change in state, not the initial existence of the target.

This permits record-specific contracts to create records directly as `draft`, `proposed`, or `active` where allowed.

## 4.3 Required transition history

Every persisted status change after canonical acceptance requires exactly one lifecycle-transition record for that target.

Examples include:

```text
Event: draft -> active
Event: active -> closed
Participant: proposed -> active
Role: active -> superseded
Work Relationship: active -> invalidated
```

The target status update and transition creation form one coordinated logical operation. Issue #13 will define how that operation is made atomic or recoverable.

## 4.4 Reconciliation rules

For one canonical target:

1. With no transitions, the persisted status is the creation baseline.
2. The first transition's `from_status` must equal the creation-baseline status.
3. Each later transition's `from_status` must equal the preceding valid transition's `to_status`.
4. The target's persisted current `status` must equal the latest valid transition's `to_status`.
5. Record-specific validation must confirm that every transition is legal.
6. Transition and record chronology must satisfy the chronology rules accepted later in this issue.

## 4.5 Disagreement is an integrity failure

When target status and lifecycle history disagree, neither source silently wins.

Portia must not automatically:

- overwrite the target from transition history;
- generate missing transitions;
- discard contradictory transitions;
- infer authority from file modification time;
- or choose the latest-written file.

The persisted status may be displayed as **unverified**, but operations requiring a valid current lifecycle state must be blocked until explicit repair.

## 4.6 Imported and migrated records

Portia does not fabricate pre-Portia transition history.

For an imported or migrated record whose earlier history is unavailable:

- the status at canonical acceptance becomes the Portia lifecycle baseline;
- provenance must disclose that earlier history is incomplete or unavailable;
- later Portia status changes require transition records normally.

Migration does not create fictional historical transitions.

## 4.7 Derived views

Timelines, reverse histories, current-state summaries, and lifecycle diagnostics are derived from:

- the canonical target;
- its creation baseline;
- and canonical lifecycle-transition records.

They are rebuildable and nonauthoritative.

---

# 5. Approved Decision 2: Lifecycle-Transition Identity, Target, and Storage

## 5.1 Semantic unit

One lifecycle-transition record represents:

```text
one canonical target
+ one lifecycle-status change
```

A transition never changes several targets at once.

A coordinated operation affecting several records creates one transition per affected target. A later Issue #13 operation or journal identity may correlate them without collapsing them into one multi-target transition.

## 5.2 Identity

Lifecycle-transition identifiers use:

```text
lct_<opaque-id>
```

The ID is nonsemantic and must not encode student identity, status, reason, record type, or sensitive meaning.

It follows the accepted Portia-owned identifier alphabet and length rules:

- suffix begins with an ASCII letter or digit;
- remaining suffix characters are ASCII letters, digits, underscores, or hyphens;
- periods are prohibited;
- case and leading zeros are preserved;
- maximum total length is 128 characters.

## 5.3 Canonical storage

A lifecycle transition is stored beneath the exact Portia work containing its target:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    lifecycle_transition/
      <transition_id>.json
```

The transition envelope's `class_id` and `work_id` must agree with the canonical path.

Transitions are not stored in a workspace-wide history collection, student dossier, derived timeline, or successor work root.

## 5.4 Compact same-work target

The transition target inherits its work scope from the containing transition envelope.

The target has exactly two branches:

```text
work
local_record
```

### Work target

A transition targeting the containing Event uses:

```json
{
  "kind": "work",
  "work_kind": "event",
  "contract_version": "2"
}
```

A future Support Process transition may use:

```json
{
  "kind": "work",
  "work_kind": "support_process",
  "contract_version": "1"
}
```

The target does not repeat `module_id`, `class_id`, or `work_id`. Those values are supplied by the transition envelope.

`work_kind` and `contract_version` state the exact target contract expected at the containing work root; they do not create a second work identity.

### Local-record target

A transition targeting an Event Participant uses:

```json
{
  "kind": "local_record",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "2"
  }
}
```

The nested `record_ref` composes the accepted public `local_record_ref` contract.

The same branch may later identify other same-work records whose public contracts have been accepted.

## 5.5 Same-work restriction

A lifecycle transition cannot target a work or record outside its containing work root.

The contract must reject:

- complete cross-work target wrappers;
- repeated `module_id`, `class_id`, or `work_id` inside a local target;
- a local reference that resolves in another work;
- and a transition stored beneath a work other than its target's work.

Cross-work correction is represented through separate canonical records:

- the predecessor receives its transition beneath its existing root;
- the successor receives its creation baseline beneath its new root;
- supersession, migration, or ownership-correction records preserve the cross-work relationship.

A transition under a successor root must not purport to change the predecessor in place.

## 5.6 No plural targets

A lifecycle transition has one target.

The schema will reject:

- target arrays;
- participant sets;
- mixed work and record targets;
- and several local record references.

One target receives one transition identity and one append-only historical record.

## 5.7 Transition records have no lifecycle status

A lifecycle-transition record is an immutable append-only historical fact.

It does not have a top-level lifecycle `status` and does not move through `proposed`, `active`, `invalidated`, or `superseded`.

An error in a transition must be addressed through the later accepted history-correction or amendment architecture. It must not be handled by silently editing or deleting the transition.

## 5.8 Application validation

Application validation must confirm:

- storage path and top-level scope agree;
- the containing work exists;
- the target resolves inside that exact work;
- `work_kind` and `contract_version` agree with the containing work contract;
- a local target's record kind, ID, and contract version agree with the resolved record;
- the target supports lifecycle status;
- `from_status` agrees with the validated prior state;
- `to_status` is supported by the target contract;
- the transition is permitted by the target's record-specific state machine;
- chronology is valid;
- and the target's current persisted status reconciles with the complete valid transition sequence.

---

# 6. Consequences

## Positive

- Current-state loading remains direct.
- Lifecycle history remains canonical and append-only.
- Initial creation does not generate redundant transition records.
- Transition storage remains local to the affected work.
- One transition has one clear target and status change.
- Coordinated operations remain decomposable and auditable.
- Later record families can reuse one envelope without adopting one universal state machine.

## Costs

- Every status change creates an additional canonical record.
- Applications must validate status against transition history.
- Multi-record lifecycle operations require coordinated persistence.
- Import and migration must represent incomplete prior history honestly.
- A separate correction contract is needed for erroneous transition records.
- Issue #13 must handle partial writes where target status and transition creation do not both complete.

## Rejected alternatives

### Transition history as sole authority

Rejected because normal loading would require replay and persisted target `status` would become only a cache.

### Target status as sole authority

Rejected because contradictory lifecycle history would be merely explanatory.

### Complete cross-work target on every transition

Rejected because it repeats containing scope and permits unnecessary scope disagreement.

### Separate work-transition and child-transition record families

Rejected because their envelopes and semantics would be nearly identical.

### One multi-target transition

Rejected because each target has its own prior state, resulting state, validation, and history.

### Lifecycle status on transition records

Rejected because a transition is evidence of another record's state change, not an ordinary mutable domain assertion.

---

# 7. Unresolved Decisions

The following remain unresolved and must not be treated as accepted architecture:

1. exact lifecycle-transition envelope fields;
2. lexical constraints for `from_status` and `to_status`;
3. transition reason architecture;
4. `effective_at` versus `recorded_at`;
5. transition ordering and equal timestamps;
6. operation correlation;
7. correction of an erroneous transition;
8. amendment semantics and wire shape;
9. nonmaterial-versus-material decision test;
10. statement-of-disagreement semantics;
11. invalidation and terminal-state rules;
12. supersession reconciliation;
13. dependency handling;
14. duplicate consolidation;
15. migration-record semantics;
16. migration identity preservation;
17. incorrect Event ownership or work-root correction;
18. exceptional removal boundaries;
19. integrity-finding vocabulary;
20. final public schema organization.

No schemas should be created for unresolved items until their architectural decisions are approved.

## 8. Next Decision

The next decision should define the lifecycle-transition envelope, including:

- required top-level fields;
- whether both `effective_at` and `recorded_at` are required;
- how `created_at` relates to `recorded_at`;
- which attribution identifies the recorder;
- and whether operation correlation belongs directly on the transition or remains deferred to Issue #13.
