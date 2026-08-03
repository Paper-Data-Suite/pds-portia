# Portia Lifecycle, Amendment, Correction, and Migration Contracts

**Status:** Working design — approved through Decision 7  
**Project:** Paper Data Suite  
**Module:** `pds-portia`  
**Issue:** `#12 — Define shared lifecycle, amendment, correction, and migration contracts`  
**Umbrella:** `#10 — Complete the Portia foundations milestone`  
**Date:** 2026-08-03  
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


# 6. Approved Decision 3: Lifecycle-Transition Envelope

## 6.1 Required fields

A lifecycle-transition version-1 record contains exactly:

```text
schema_version
record_type
module_id
class_id
work_id
transition_id
target
previous_transition
from_status
to_status
reason
effective_at
creation_source
created_at
created_by
```

The initial envelope does not contain:

```text
status
updated_at
updated_by
recorded_at
authorized_by
operation_id
```

The exact `reason` object remains unresolved and will be defined by the next decision. The field itself is required.

## 6.2 Constants and identity

The envelope uses:

```text
schema_version = "1"
record_type = "lifecycle_transition"
module_id = "portia"
```

`transition_id` uses the `lct_` identifier contract accepted in Decision 2.

The top-level `class_id` and `work_id` identify the containing work scope and must agree with the canonical storage path.

## 6.3 Explicit predecessor chain

`previous_transition` is required.

It is either:

- `null` for the first transition after the target's creation baseline; or
- a same-work `local_record_ref` constrained to a lifecycle-transition version-1 record.

First transition:

```json
{
  "previous_transition": null
}
```

Later transition:

```json
{
  "previous_transition": {
    "record_kind": "lifecycle_transition",
    "record_id": "lct_prior",
    "contract_version": "1"
  }
}
```

The predecessor chain, rather than timestamp sorting, establishes lifecycle-transition sequence.

This permits application validation to diagnose:

- missing predecessors;
- branches;
- cycles;
- contradictory prior states;
- and multiple competing transition heads.

Application validation requires a non-null predecessor to:

- exist beneath the same work root;
- target the same canonical work or child record;
- have `to_status` equal to the new transition's `from_status`;
- and be the unique current transition head for that target when the new transition is accepted.

Two transitions that cite the same predecessor for the same target form a conflicting branch. Portia must not order them automatically by timestamp, filename, or file modification time.

## 6.4 Status-token structure

`from_status` and `to_status` use lowercase status tokens matching:

```text
^[a-z][a-z0-9_]*$
```

The shared lifecycle-transition schema validates lexical form only.

The target's record-specific contract and application validator determine:

- whether each status is supported;
- whether the transition between them is legal;
- whether the target satisfies activation or closure prerequisites;
- and whether dependent records require coordinated treatment.

`from_status` and `to_status` must differ.

## 6.5 Time model

Both `effective_at` and `created_at` are required and compose the accepted explicit-offset timestamp contract.

`effective_at` means:

> The time at which the lifecycle change became effective for the target.

`created_at` means:

> The time at which the immutable lifecycle-transition record was first canonically persisted in Portia.

There is no separate `recorded_at` field because `created_at` already represents canonical recording time.

Application validation requires:

- `effective_at` must not precede the target's `created_at`;
- `effective_at` must not be later than the transition's `created_at`;
- future-effective lifecycle transitions are not supported in version 1;
- `effective_at` must be nondecreasing along the predecessor chain;
- `created_at` must be nondecreasing along the predecessor chain;
- and equal timestamps are permitted because `previous_transition` establishes sequence.

A planned future status change is not a lifecycle transition until it actually becomes effective.

## 6.6 Attribution

`created_by` composes the accepted `attribution_agent` contract.

Its meaning is:

> The local operator or deterministic system process responsible for canonically recording the transition in Portia.

`created_by` does not establish:

- institutional identity;
- legal authorship;
- employment status;
- decision-making authority;
- or authorization to perform the lifecycle change.

When a domain transition requires authority, that authority belongs in the applicable domain record, Determination, or later authorization contract rather than in the generic lifecycle-transition envelope.

The generic envelope therefore does not contain `authorized_by`.

## 6.7 Creation provenance

`creation_source` composes the accepted shared creation-source contract but lifecycle-transition version 1 permits only:

```text
digital_entry
import
```

Paper capture does not directly create a canonical lifecycle transition.

A returned page or interpreted paper artifact may initiate review, but an accepted status change arising from that review is recorded as `digital_entry`. The underlying page and route provenance remain attached to the affected domain records or later supporting-reference contracts.

The `import` branch is permitted only when Portia imports an explicit external lifecycle change.

Importing a record that already has a current status but lacks complete transition history establishes an initial lifecycle baseline under Decision 1 rather than fabricating imported transitions.

## 6.8 No operation-correlation field

Lifecycle-transition version 1 does not contain:

```text
operation_id
operation_ref
journal_id
transaction_id
```

Issue #13 may define a coordinated-operation or recovery journal that references every affected target and transition.

Canonical lifecycle history must not depend on transaction machinery, and Issue #12 must not create a premature reference to a contract that does not yet exist.

## 6.9 Immutability

Because lifecycle-transition records have no lifecycle status, they also have no `updated_at` or `updated_by`.

After canonical acceptance, the envelope is immutable.

An erroneous transition must be addressed through the history-correction architecture accepted later in Issue #12. It must not be edited, replaced in place, or silently removed.

## 6.10 Structural and application validation

JSON Schema will validate:

- the exact 15-field envelope;
- constants;
- `lct_` identifier syntax;
- the compact target union;
- nullable predecessor shape;
- lowercase status-token syntax;
- distinct `from_status` and `to_status`;
- required timestamps with explicit offsets;
- permitted creation-source branches;
- and attribution-agent structure.

Application validation remains responsible for:

- canonical path agreement;
- target resolution;
- predecessor resolution;
- same-target predecessor identity;
- branch and cycle detection;
- transition-head uniqueness;
- prior-state agreement;
- record-specific transition legality;
- target prerequisites;
- timestamp chronology across records;
- current-status and transition-history reconciliation;
- authorization;
- dependency handling;
- and coordinated persistence or recovery.

---


# 7. Approved Decision 4: Lifecycle-Transition Reason Architecture

## 7.1 Decision

The required `reason` field is a closed object with:

```text
category
code
detail, optional
```

Example:

```json
{
  "category": "correction",
  "code": "identity_corrected"
}
```

Example with neutral explanatory detail:

```json
{
  "category": "dependency",
  "code": "required_account_invalidated",
  "detail": "The Account required for this reported-involvement Role was invalidated."
}
```

Unknown properties are rejected.

The shared lifecycle contract defines a small stable category vocabulary. Each target record family defines a closed application-level matrix of permitted reason codes for its own transitions.

The generic lifecycle-transition schema does not contain one universal enum of every future Portia transition reason.

## 7.2 Shared categories

The initial shared categories are:

```text
workflow
record_validity
correction
dependency
consolidation
migration
other
```

### `workflow`

An ordinary record-specific lifecycle progression, confirmation, completion, closure, reopening, reversal, or cancellation.

Representative codes may include:

```text
review_confirmed
work_completed
teacher_cancelled
reopened_for_review
```

### `record_validity`

The target should no longer be treated as a valid current assertion, and replacement is not itself the primary reason.

Representative codes may include:

```text
entered_in_error
source_retracted
insufficient_identity
unsupported_assertion
```

This category does not assert blame, falsity, guilt, bad faith, or credibility.

### `correction`

The lifecycle change occurs because the target requires material correction or replacement.

Representative codes may include:

```text
identity_corrected
target_corrected
role_type_corrected
material_content_corrected
owning_class_corrected
```

### `dependency`

The target's lifecycle changes because another canonical record required for its current use changed lifecycle state or use eligibility.

Representative codes may include:

```text
required_account_invalidated
participant_superseded
parent_work_invalidated
```

The reason object does not identify the dependency itself. Structured dependency identity belongs in the applicable domain record, successor relationship, or later dependency contract.

### `consolidation`

Several records are being resolved as duplicates through explicit consolidation.

The initial shared code is:

```text
duplicate_consolidated
```

### `migration`

The lifecycle change results from an explicit representation or contract migration that preserves intended identity and meaning.

Representative codes may include:

```text
contract_version_migrated
storage_envelope_migrated
```

This category must not be used when semantic correction is also required.

### `other`

No accepted category adequately describes the primary reason.

When `category` is `other`:

```text
code = other
detail is required
```

## 7.3 Reason-code structure

`code` matches:

```text
^[a-z][a-z0-9_]*$
```

Reason codes:

- are exact, case-sensitive semantic tokens;
- are not silently normalized;
- must describe why the transition occurred rather than merely repeat `to_status`;
- must use neutral terminology;
- and must not encode blame, guilt, credibility, diagnosis, punishment, or future risk.

The generic lifecycle-transition schema validates lexical form.

Each target record family must define a closed application-level matrix containing:

```text
from_status
to_status
reason.category
reason.code
```

A structurally valid reason code may therefore be application-invalid for a particular target or transition.

This allows later record families to add legitimate domain-specific reason codes without revising the shared lifecycle-transition schema.

## 7.4 Detail rules

`detail` composes the accepted `non_empty_text` contract.

It is:

- required when `category` is `other`;
- required when `code` is `other`;
- optional for recognized codes unless a record-specific policy requires it;
- and prohibited from becoming the only canonical location of a material assertion, decision, dependency, or evidence reference.

For all categories other than `other`, `code` must not equal `other`.

A recognized category may use a recognized code with optional concise neutral clarification.

`detail` must not replace:

- an Account;
- an Observation;
- a Determination;
- a successor record;
- a supersession entry;
- a structured dependency reference;
- or another canonical domain record.

## 7.5 Structural validation

JSON Schema will validate:

- the exact object shape;
- the seven shared categories;
- lowercase reason-code syntax;
- optional nonempty detail;
- required `code = other` and required `detail` when `category = other`;
- required detail whenever `code = other`;
- and prohibition of `code = other` for recognized non-`other` categories.

The schema will not enumerate every permitted record-specific code.

## 7.6 Application validation

Application validation must confirm:

- the code is permitted for the target record family;
- the category and code are semantically compatible;
- the reason is permitted for the exact `from_status` and `to_status`;
- required record-specific detail is present;
- the reason is consistent with any successor or supersession relationship;
- the reason does not conceal a material correction as ordinary workflow;
- migration reasons preserve intended meaning;
- dependency reasons correspond to an actual affected dependency;
- and neutral terminology is preserved.

## 7.7 Relationship to specialized supersession reasons

Existing Event-family and Work Relationship successor records retain their specialized forward supersession reasons.

Those reasons remain canonical for the replacement relationship.

The predecessor's lifecycle transition separately records why the predecessor moved to `superseded`.

Where both records exist, application validation requires semantic consistency.

Examples:

```text
Event Participant successor reason:
identity_corrected

Predecessor transition reason:
category = correction
code = identity_corrected
```

```text
Work Relationship successor reason:
duplicate_consolidated

Predecessor transition reason:
category = consolidation
code = duplicate_consolidated
```

The two records preserve different facts:

- the successor identifies why it replaces one or more predecessors;
- the lifecycle transition records why the predecessor's status changed.

Neither record replaces the other.

## 7.8 Rejected alternatives

### One universal reason enum

Rejected because later Portia record families have materially different workflows and would continually expand or distort one shared enum.

### Free-text reason

Rejected because it weakens structural validation, deterministic comparison, migration, reporting, and dependency analysis.

### Record-specific reason object schemas embedded in the shared transition

Rejected because the shared lifecycle-transition contract would need revision whenever a later record family introduced a legitimate reason code.

### Evidence and dependency references inside `reason`

Rejected because `reason` should explain the transition's primary semantic cause, not become a universal container for supporting records or graph relationships.

---


# 8. Approved Decision 5: Correcting an Erroneous Immutable Transition

## 8.1 Decision

Portia corrects an erroneous accepted lifecycle transition through a separate immutable:

```text
lifecycle_history_correction
```

record.

The original transition remains preserved. Portia does not:

- edit it in place;
- delete it through an ordinary correction workflow;
- append a compensating transition that falsely asserts another real lifecycle change;
- or virtually reinterpret persisted predecessor references.

A lifecycle-history correction selects an explicitly rebuilt replacement branch.

## 8.2 Identity and storage

Lifecycle-history-correction identifiers use:

```text
lhc_<opaque-id>
```

The identifier follows the accepted Portia-owned identifier alphabet and length rules.

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    lifecycle_history_correction/
      <correction_id>.json
```

The correction is stored beneath the work containing its lifecycle target.

## 8.3 Semantic unit

One lifecycle-history-correction record means:

> For one lifecycle target, replace the previously selected lifecycle-transition-history head with another explicitly persisted head.

It does not mutate any transition and does not itself represent a domain lifecycle change.

## 8.4 Required envelope

A lifecycle-history-correction version-1 record contains exactly:

```text
schema_version
record_type
module_id
class_id
work_id
correction_id
target
previous_correction
replaced_head
replacement_head
reason
creation_source
created_at
created_by
```

It does not contain:

```text
status
updated_at
updated_by
effective_at
operation_id
```

Constants are:

```text
schema_version = "1"
record_type = "lifecycle_history_correction"
module_id = "portia"
```

The record is immutable after canonical acceptance.

## 8.5 Target

`target` uses the same compact same-work target contract as lifecycle-transition records:

```text
work
local_record
```

The correction must apply to one lifecycle target only.

Cross-target or plural corrections are not permitted.

## 8.6 Correction predecessor chain

`previous_correction` is required and is either:

- `null` for the first lifecycle-history correction for the target; or
- a same-work `local_record_ref` constrained to a lifecycle-history-correction version-1 record.

This creates an append-only correction series and permits diagnosis of:

- correction branches;
- competing correction heads;
- missing predecessors;
- and cycles.

Application validation requires a non-null predecessor correction to target the same canonical work or child record.

## 8.7 Replaced and replacement heads

`replaced_head` is required and identifies the lifecycle-transition version-1 record that was the selected transition head immediately before correction.

`replacement_head` is required but nullable.

It is either:

- a same-work lifecycle-transition version-1 reference selecting the corrected branch; or
- `null` when correction removes all transitions and restores the target's creation baseline.

Example:

```json
{
  "replaced_head": {
    "record_kind": "lifecycle_transition",
    "record_id": "lct_wrong",
    "contract_version": "1"
  },
  "replacement_head": {
    "record_kind": "lifecycle_transition",
    "record_id": "lct_corrected",
    "contract_version": "1"
  }
}
```

Reverting to the creation baseline:

```json
{
  "replaced_head": {
    "record_kind": "lifecycle_transition",
    "record_id": "lct_accidental",
    "contract_version": "1"
  },
  "replacement_head": null
}
```

`replacement_head` must not equal `replaced_head`.

## 8.8 Explicit branch rebuilding

The replacement branch is persisted explicitly.

Suppose the selected history is:

```text
creation baseline
  -> T1
  -> T2 erroneous
  -> T3
  -> T4 selected head
```

Correcting `T2` requires:

```text
creation baseline
  -> T1
  -> T2'
  -> T3'
  -> T4' replacement head
```

The lifecycle-history correction then records:

```text
replaced_head = T4
replacement_head = T4'
```

The original `T2`, `T3`, and `T4` remain preserved but are no longer part of the validated selected lifecycle history.

Existing transitions are never interpreted as though their persisted `previous_transition` references had changed.

## 8.9 Derived replaced and replacement segments

The correction record does not enumerate every transition in either segment.

Application validation traces backward from:

- `replaced_head`;
- and `replacement_head`, when non-null.

The most recent shared predecessor—or the creation baseline—is the correction anchor.

The replaced and replacement segments are derived from the explicit predecessor chains.

This avoids storing redundant transition arrays that could disagree with the canonical graph.

## 8.10 Selection rules

For one lifecycle target:

1. With no correction records, the ordinary valid transition head is selected.
2. The first correction's `replaced_head` must equal that selected head.
3. Each later correction's `previous_correction` must identify the unique current correction head.
4. Each correction's `replaced_head` must equal the currently selected transition head immediately before correction.
5. `replacement_head` establishes the corrected selected branch.
6. Ordinary later transitions may extend only the selected replacement branch.
7. A transition extending an excluded branch is application-invalid.

Portia does not select correction or transition branches by:

- timestamp;
- filename;
- creation order;
- filesystem order;
- or file modification time.

A competing correction head is an integrity failure.

## 8.11 Wrong-target correction

A transition recorded against target A but intended for target B is not silently retargeted.

Correction requires:

- a lifecycle-history correction for target A removing the erroneous branch;
- normal lifecycle-transition records for target B;
- and target-status repairs where required.

Each record remains under its own canonical work root.

Cross-work coordination belongs to Issue #13.

## 8.12 Target-status repair

A lifecycle-history correction is not a lifecycle transition.

After the corrected history is selected, the target's persisted status must equal:

- the selected replacement head's `to_status`; or
- the creation-baseline status when `replacement_head` is `null`.

When that differs from the target's current persisted status, the correction operation repairs the target's status and ordinary update attribution.

It does not create a compensating transition merely to repair the current-state projection.

If the corrected history ends in the same status, the target body need not change.

## 8.13 Correction reason

`reason` is a closed correction-specific object with:

```text
code
detail, optional
```

Initial codes are:

```text
wrong_target
wrong_predecessor
wrong_from_status
wrong_to_status
wrong_reason
wrong_effective_at
wrong_attribution
duplicate_transition
transition_should_not_exist
multiple_fields_corrected
other
```

`code` uses the accepted lowercase token syntax.

`detail` composes `non_empty_text`.

Rules:

- `detail` is required for `other`;
- recognized codes may include concise neutral detail;
- `multiple_fields_corrected` is used only when no single error code adequately describes the correction;
- and the reason must not become the only canonical location of substantive domain evidence.

This reason vocabulary is distinct from lifecycle-transition reasons because it explains why historical transition evidence was corrected, not why a domain target changed status.

## 8.14 Canonically accepted versus never accepted

This mechanism applies to a structurally valid, canonically accepted transition later found to be semantically or historically wrong.

It does not legitimize:

- malformed JSON;
- a file whose envelope disagrees with its path;
- duplicate bytes produced by a failed write;
- an incomplete temporary file;
- or a record that was never validly accepted as canonical.

Those cases belong to integrity repair, exceptional-removal boundaries, and Issue #13 recovery.

## 8.15 Structural validation

JSON Schema will validate:

- the exact immutable envelope;
- constants;
- `lhc_` identifier syntax;
- the compact target;
- nullable correction predecessor;
- lifecycle-transition references for replaced and replacement heads;
- nullable `replacement_head`;
- distinct replaced and replacement heads;
- the correction-reason object;
- creation provenance;
- explicit-offset `created_at`;
- and attribution structure.

## 8.16 Application validation

Application validation must confirm:

- canonical path and scope agreement;
- exact target resolution;
- same-target identity across replaced and replacement branches;
- exact correction-predecessor resolution;
- unique current correction head;
- `replaced_head` was the selected head before correction;
- replacement transitions form a complete explicit branch;
- replacement transitions satisfy normal status, reason, and chronology rules;
- the branches have an inferable shared ancestor or creation baseline;
- no transition or correction cycles exist;
- excluded branches are not later extended;
- the correction reason matches the identified error;
- target status agrees with the corrected selected history;
- authority and privacy requirements are satisfied;
- and the coordinated operation is atomic or recoverable.

## 8.17 Rejected alternatives

### Editing or deleting the transition

Rejected because it destroys canonical historical evidence and may break descendant references.

### Compensating lifecycle transition

Rejected as the general correction mechanism because it falsely claims that both lifecycle changes actually occurred and cannot correct a wrong target, predecessor, reason, attribution, or effective time.

### Exclusion marker with virtual predecessor substitution

Rejected because it makes persisted transition references misleading and silently rewrites history during resolution.

### Enumerating every replaced transition

Rejected because the explicit predecessor chains already define the segments and a stored list could contradict them.

---


# 9. Approved Decision 6: Amendment Semantics and Wire Shape

## 9.1 Decision

Portia represents one atomic nonmaterial in-place update through a separate immutable:

```text
amendment
```

record.

The canonical target is updated in place, while the amendment preserves the exact prior and resulting states of every changed field.

Portia does not use:

- complete before-and-after target snapshots;
- unrestricted JSON Patch;
- silent in-place editing without append-only history;
- or replacement-based correction for every spelling, punctuation, formatting, or other genuinely nonmaterial change.

## 9.2 Identity and storage

Amendment identifiers use:

```text
amd_<opaque-id>
```

The identifier follows the accepted Portia-owned identifier alphabet and length rules.

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    amendment/
      <amendment_id>.json
```

An amendment is stored beneath the work containing its target.

## 9.3 Semantic unit

One amendment means:

> One atomic, nonmaterial in-place update to one canonical Portia domain record.

An amendment may contain several field changes only when:

- they form one teacher-facing correction;
- every individual change is nonmaterial;
- and their combined effect remains nonmaterial.

Several small edits must not be bundled to conceal a material correction.

## 9.4 Required envelope

An amendment version-1 record contains exactly:

```text
schema_version
record_type
module_id
class_id
work_id
amendment_id
target
previous_amendment
target_updated_at_before
changes
reason
creation_source
created_at
created_by
```

It does not contain:

```text
status
effective_at
updated_at
updated_by
operation_id
```

Constants are:

```text
schema_version = "1"
record_type = "amendment"
module_id = "portia"
```

The amendment record is immutable after canonical acceptance.

## 9.5 Target

`target` uses the compact same-work target contract:

```text
work
local_record
```

Application validation requires the target to:

- be a canonical Portia domain record;
- support in-place amendment;
- and persist `updated_at` and `updated_by`.

The following are not amendment targets:

- lifecycle-transition records;
- lifecycle-history-correction records;
- amendment records;
- other immutable audit records;
- derived views;
- or external-module records.

## 9.6 Amendment predecessor chain

`previous_amendment` is required and is either:

- `null` for the first amendment to the target; or
- a same-work `local_record_ref` constrained to an amendment version-1 record.

This creates one append-only amendment sequence per target and permits diagnosis of:

- amendment branches;
- competing amendment heads;
- missing predecessors;
- and cycles.

The amendment chain orders amendments to the same target. It does not replace lifecycle-transition history.

## 9.7 Update precondition

`target_updated_at_before` records the target's exact `updated_at` immediately before the amendment operation.

Application validation requires:

1. the target's current `updated_at` equals `target_updated_at_before` before mutation;
2. the amendment's `created_at` is later than `target_updated_at_before`;
3. after mutation, the target's `updated_at` equals the amendment's `created_at`;
4. after mutation, the target's `updated_by` equals the amendment's `created_by`.

A conflicting target `updated_at` blocks the amendment rather than causing an automatic merge.

This is an explicit revision precondition, not a substitute for Issue #13 coordinated-persistence and recovery contracts.

## 9.8 Change representation

`changes` is a nonempty array of closed change objects.

Example:

```json
{
  "path": "/summary",
  "operation": "replace",
  "before": {
    "present": true,
    "value": "Student recieveed the handout."
  },
  "after": {
    "present": true,
    "value": "Student received the handout."
  }
}
```

Each change contains exactly:

```text
path
operation
before
after
```

## 9.9 Path rules

`path` is a nonempty JSON Pointer identifying one property or nested property.

The empty root pointer is prohibited.

Application validation must reject:

- duplicate paths;
- ancestor-and-descendant paths in the same amendment;
- paths into arrays by numeric index;
- paths not approved as amendable by the target's record-specific contract;
- and paths that would alter identity, lifecycle, provenance, or material meaning.

An array may be replaced as one complete field value when the complete replacement is nonmaterial.

Individual array-index operations are not supported.

## 9.10 Operations

The initial operation vocabulary is:

```text
add
replace
remove
```

Required state combinations are:

| Operation | Before | After |
|---|---|---|
| `add` | absent | present |
| `replace` | present | present and unequal |
| `remove` | present | absent |

Portia does not support:

```text
move
copy
test
```

operations.

## 9.11 Explicit presence and value

`before` and `after` use closed state wrappers.

Present property:

```json
{
  "present": true,
  "value": null
}
```

Absent property:

```json
{
  "present": false
}
```

When `present` is `true`, `value` is required and may contain any valid JSON value.

When `present` is `false`, `value` is prohibited.

This distinguishes an absent property from a property whose JSON value is `null`.

## 9.12 Simultaneous application

The `changes` array is semantically unordered.

All `before` states are evaluated against the same pre-amendment target.

All `after` states describe the same resulting target.

Portia must not rely on change-array order to make one operation create, remove, or replace a path needed by another operation.

Overlapping ancestor-and-descendant paths are therefore prohibited.

## 9.13 Protected fields

The following categories cannot be amended in place:

- schema version or record type;
- module, class, work, or record identity;
- canonical target identity;
- lifecycle status;
- creation provenance;
- creation attribution or timestamp;
- supersession relationships;
- material source, subject, participant, provider, recipient, or relationship identity;
- or another field whose change alters the assertion's meaning, scope, authority, or lifecycle significance.

`updated_at` and `updated_by` change as part of the amendment operation but are not listed in `changes`. Their resulting values are fixed by the envelope rules.

The exact record-specific amendable-path matrix is governed by the materiality decision and later domain contracts.

## 9.14 Amendment reason

`reason` is a closed object containing:

```text
code
detail, optional
```

Initial reason codes are:

```text
spelling_corrected
punctuation_corrected
formatting_corrected
transcription_corrected
display_value_corrected
nonsemantic_metadata_corrected
other
```

`code` uses the accepted lowercase token syntax.

`detail` composes `non_empty_text`.

Rules:

- `detail` is required for `other`;
- recognized codes may include concise neutral detail;
- the reason must not contain substantive evidence or a replacement assertion;
- and unsupported or misleading reason codes are application-invalid.

`clarification` is not a shared amendment reason in version 1 because clarification can alter meaning. A proposed clarification must first satisfy the materiality rules accepted later.

## 9.15 Creation provenance

Amendment version 1 permits:

```text
digital_entry
import
```

Paper interpretation may propose a correction, but canonical application requires review and is recorded as `digital_entry`.

Migration does not use amendment records merely because representation changed. Migration receives its own contract later in Issue #12.

## 9.16 Target reconciliation

After applying an amendment:

- every `before` state must match the target immediately before mutation;
- every `after` state must match the target immediately after mutation;
- target identity and lifecycle status must remain unchanged;
- target `updated_at` must equal the amendment's `created_at`;
- target `updated_by` must equal the amendment's `created_by`;
- and unchanged fields must remain unchanged.

The complete amendment chain preserves prior values without complete record snapshots.

## 9.17 Correcting an amendment

An accepted amendment is immutable.

A later genuinely nonmaterial correction to the target may be represented by another amendment with accurate before-and-after states.

Portia must not edit the earlier amendment.

A discovered error involving:

- the wrong target;
- a fabricated prior state;
- a material semantic change;
- or an amendment that should never have been accepted

is an integrity problem rather than an ordinary amendment.

Its complete treatment will be reconciled with the material-correction and integrity-finding decisions later in Issue #12.

## 9.18 Structural validation

JSON Schema will validate:

- the exact immutable envelope;
- constants;
- `amd_` identifier syntax;
- compact target shape;
- nullable amendment predecessor;
- explicit-offset timestamps;
- a nonempty `changes` array;
- closed change objects;
- JSON Pointer syntax;
- the `add`, `replace`, and `remove` operations;
- before-and-after presence wrappers;
- operation-compatible presence states;
- amendment-reason structure;
- permitted creation provenance;
- and attribution.

## 9.19 Application validation

Application validation must confirm:

- canonical storage path and scope;
- exact target resolution;
- target eligibility for amendment;
- exact predecessor resolution and unique amendment head;
- target revision precondition;
- exact before-and-after value agreement;
- unique and nonoverlapping paths;
- prohibition of array-index traversal;
- record-specific amendable paths;
- individual and combined nonmateriality;
- unchanged target identity and lifecycle status;
- target update attribution;
- reason compatibility;
- authority and privacy;
- and atomic or recoverable persistence.

## 9.20 Rejected alternatives

### Complete before-and-after target snapshots

Rejected because they duplicate unchanged and potentially sensitive information.

### Unrestricted JSON Patch

Rejected because it permits overly general operations and does not independently preserve exact prior values.

### Replacement for every correction

Rejected because it creates new canonical identities for genuinely nonmaterial changes.

### Silent in-place editing

Rejected because it destroys append-only correction history.

### Ordered change execution

Rejected because amendment meaning should not depend on array ordering.

---


# 10. Approved Decision 7: Nonmaterial-versus-Material Change Test

## 10.1 Decision

Portia uses a shared semantic-equivalence test together with record-specific path classifications.

A change is nonmaterial only when the record before and after the change remains:

> The same canonical assertion for every legitimate downstream use.

The corrected record must identify the same:

```text
subject
target
source
occurrence
scope
relationship
basis
authority
substantive proposition
```

as before.

The size of the textual or structural edit does not determine materiality.

Several punctuation changes may remain nonmaterial. Replacing one word may materially reverse an assertion.

## 10.2 Categorical materiality gates

A proposed change is categorically material when it changes any of the following dimensions.

### Canonical identity or ownership

This includes:

- `module_id`;
- `class_id`;
- `work_id`;
- record ID;
- record kind;
- work kind;
- owning class;
- owning academic year where ownership depends on it;
- or canonical storage scope.

These changes cannot use amendment.

They require successor replacement, migration when representation alone changes, or the later ownership-correction process.

### Subject or target identity

This includes:

- roster-student reference;
- Actor reference;
- descriptive or unknown subject variant;
- Event Participant target;
- provider;
- recipient;
- source;
- observer;
- or another person or record that the assertion concerns.

Changing who or what a record concerns always requires replacement.

### Assertion type or substantive proposition

A change is material when it alters what the record asserts.

Examples include:

- Event-summary meaning;
- Role type;
- relationship type or direction;
- whether an occurrence happened;
- what was reportedly said;
- what was observed;
- what was determined;
- or what response, support, implementation, follow-up, or outcome occurred.

Changing:

```text
The student submitted the assignment.
```

to:

```text
The student did not submit the assignment.
```

is material despite changing only one word.

### Temporal, spatial, or contextual meaning

A change is material when it alters context that could affect identification or interpretation.

This includes:

- Event occurrence date, time, range, or precision;
- Event location type;
- instructional-context type;
- school year;
- or another context distinguishing the documented occurrence.

A spelling correction inside an existing location detail may be nonmaterial.

Changing:

```text
classroom
```

to:

```text
hallway
```

is material.

### Evidentiary basis or provenance

A change is material when it changes:

- which Account, Observation, paper artifact, or import source supports a record;
- whether a source was firsthand or secondhand;
- source attribution;
- creation provenance;
- or another evidentiary relationship.

Adding, removing, or replacing an Event Participant Role basis entry requires successor replacement rather than amendment.

### Authority, privacy, or disclosure scope

A change is material when it alters:

- who made or authorized a decision;
- the authority under which it was made;
- the intended recipient;
- confidentiality or privacy scope;
- disclosure eligibility;
- or whether the record represents a teacher-local or institutional action.

Later record contracts must classify these fields as replacement-only unless the field is explicitly nonauthoritative display metadata.

### Lifecycle or dependency significance

A change is material when it would alter:

- lifecycle status;
- activation eligibility;
- closure prerequisites;
- required dependencies;
- current-use eligibility;
- supersession relationships;
- or another consumer's lifecycle treatment.

Lifecycle status changes use lifecycle transitions, not amendments.

A field correction that would mean an active record no longer satisfied its activation prerequisites requires replacement, invalidation, or coordinated dependency handling.

## 10.3 Counterfactual downstream-use test

When no categorical gate appears obvious, amendment is permitted only when the answer to every following question is **no**.

Would the corrected value have changed:

- whether a consumer selected the record;
- how a consumer interpreted the assertion;
- whether the record satisfied a validation rule;
- whether another record could depend on it;
- which person or occurrence appeared in a projection;
- whether a decision maker might reach a different conclusion;
- or what an authorized reader would understand happened?

Any `yes` answer makes the change material.

## 10.4 Record-specific path classes

Every record-specific contract must classify mutable content paths into three groups.

### Protected

Protected paths are never amendable.

Representative categories include:

```text
identity
ownership
status
target
subject
source
basis
creation provenance
supersedes
```

### Conditionally amendable

Conditionally amendable paths may be changed only after the shared semantic-equivalence test passes.

Representative examples include:

```text
Event summary
Event location detail
instructional-context detail
contextual Role detail
display snapshots
human-facing labels
```

These paths may contain either clerical errors or substantive meaning. The path alone cannot determine materiality.

### Nonsemantic metadata

Nonsemantic metadata is normally amendable only when the exact record contract confirms that the field has no identity, assertion, lifecycle, authority, privacy, or evidentiary role.

Potential examples include:

- display-only formatting;
- generated presentation labels;
- nonauthoritative spelling in a display snapshot;
- or administrative metadata explicitly defined as nonsemantic.

A field is not nonsemantic merely because it is named:

```text
detail
description
label
summary
```

## 10.5 Additive information

Adding information is nonmaterial only when it repairs presentation without adding a factual proposition.

Potentially nonmaterial examples include:

- adding missing punctuation;
- restoring an accidentally omitted character in a display snapshot when the authoritative person reference is unchanged;
- adding formatting needed to display an already-present value correctly.

Material examples include:

- adding another action to an Event summary;
- adding a room number not previously documented;
- adding a new Account or Observation as Role basis;
- adding a rationale;
- adding an instructional reference;
- or adding detail that narrows, expands, qualifies, or changes the assertion.

Additive clarification is presumed material unless semantic equivalence is demonstrated.

## 10.6 Combined changes

Materiality is evaluated:

1. for each individual change;
2. for the resulting record as a whole.

An amendment is prohibited when individually small changes collectively alter meaning.

For example, replacing names with pronouns, changing punctuation, and removing a contextual phrase may each appear editorial alone but collectively make the subject or action ambiguous.

The combined result must remain semantically equivalent.

## 10.7 Uncertainty

When materiality is uncertain:

1. Portia does not apply an amendment automatically.
2. The proposed operation becomes `review_required` at the application-workflow level.
3. A human reviews the complete before-and-after record.
4. When uncertainty remains and correction must proceed, Portia uses successor replacement rather than amendment.

This is a conservative identity-preservation rule.

It does not assert that the predecessor was false.

Uncertainty does not automatically require invalidation.

Invalidation is appropriate only when the predecessor should no longer remain a valid current assertion and no replacement adequately expresses the correction.

## 10.8 Routing outcomes

### Amendment

Use amendment when:

- canonical identity is unchanged;
- all categorical materiality gates are false;
- the record remains semantically equivalent;
- the path is conditionally amendable or nonsemantic;
- and exact before-and-after values are preserved.

### Successor replacement

Use successor replacement when:

- the intended assertion remains recognizable as a corrected replacement;
- but identity, target, source, basis, substantive content, context, authority, or another material dimension changes.

The predecessor transitions to `superseded` through a coordinated operation.

### Invalidation

Use invalidation when:

- the predecessor should no longer be treated as a valid current assertion;
- and no corrected successor should replace it.

Examples include a record entered in error or a source retraction where the historical record should remain preserved but no replacement assertion is appropriate.

### Migration

Use migration only when:

- representation or contract version changes;
- identity, scope, provenance, and intended meaning remain unchanged;
- and semantic correction is not being concealed.

### Record-specific decision

Use a record-specific decision when the shared test does not produce a categorical result and the record family has specialized semantics requiring its own policy.

The operation remains blocked until that policy is defined.

## 10.9 Initial Event-family classification

| Proposed change | Required treatment |
|---|---|
| Correct spelling or punctuation in Event summary without changing meaning | Amendment |
| Add, remove, qualify, or reverse a factual statement in Event summary | Successor Event |
| Change Event occurrence value or precision | Successor Event |
| Correct punctuation in location detail without changing location | Amendment |
| Change Event location type | Successor Event |
| Correct formatting in instructional-context detail | Amendment |
| Change instructional-context type or external references | Successor Event |
| Change Event class, work ID, or ownership-defining school year | Ownership-correction process |
| Correct roster or Actor display snapshot while retaining the same authoritative reference | Amendment |
| Change Participant roster reference, Actor reference, or subject variant | Successor Participant |
| Change a descriptive-person label functioning as the only subject identification | Successor Participant |
| Change Role target | Successor Role |
| Change Role type | Successor Role |
| Add, remove, or replace Role basis | Successor Role |
| Correct spelling in contextual Role detail without changing meaning | Amendment |
| Change the substantive meaning of contextual Role detail | Successor Role |
| Change Work Relationship source, target, or relationship type | Successor Work Relationship |
| Correct spelling in nonmaterial Work Relationship detail | Amendment |
| Materially change Work Relationship detail | Successor Work Relationship |
| Change only schema representation while preserving meaning | Migration |
| Remove a record entered in error without replacement | Invalidation, not deletion |

## 10.10 Reason codes do not determine materiality

An operator-selected reason code cannot override the semantic test.

Selecting:

```text
spelling_corrected
```

does not make a substantive change nonmaterial.

Application validation determines materiality from the actual before-and-after record states and the record-specific path policy.

## 10.11 Structural validation

JSON Schema cannot prove semantic equivalence.

Schema validation remains responsible only for the local structure of the chosen operation record.

The materiality test is an application-level contract.

## 10.12 Application validation

Application validation must confirm:

- every changed path's classification;
- every categorical materiality gate;
- semantic equivalence for an amendment;
- individual and combined materiality;
- consistency with target-specific correction and supersession rules;
- correct routing to amendment, replacement, invalidation, migration, or review;
- and that the selected operation and reason do not misrepresent the actual change.

## 10.13 Rejected alternatives

### Path-only materiality

Rejected because the same field may receive either a clerical correction or a substantive rewrite.

### Operator-selected materiality

Rejected because a convenient interface choice must not determine historical semantics.

### Character-count or diff-size thresholds

Rejected because edit size does not establish semantic significance.

### Automatic amendment when no protected path changes

Rejected because conditionally amendable content can still change the assertion's meaning.

---

# 11. Consequences

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

# 12. Unresolved Decisions

The following remain unresolved and must not be treated as accepted architecture:

1. statement-of-disagreement semantics;
2. invalidation and terminal-state rules;
3. supersession reconciliation;
4. dependency handling;
5. duplicate consolidation;
6. migration-record semantics;
7. migration identity preservation;
8. incorrect Event ownership or work-root correction;
9. exceptional removal boundaries;
10. integrity-finding vocabulary;
11. final public schema organization.

No schemas should be created for unresolved items until their architectural decisions are approved.

## 13. Next Decision

The next decision should define statement-of-disagreement semantics and wire shape, including:

- who or what may be represented as the disagreeing source;
- which Portia records may be targeted;
- whether one statement may target several records;
- how disagreement differs from correction, retraction, invalidation, or reply;
- and how disagreement remains visible after the target is superseded or invalidated.
