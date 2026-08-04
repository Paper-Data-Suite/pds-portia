# Portia Lifecycle, Amendment, Correction, and Migration Contracts

**Status:** Working design — approved through Decision 17  
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


# 11. Approved Decision 8: Statement-of-Disagreement Contract

## 11.1 Decision

Portia represents disagreement through an independent substantive attributed record:

```text
statement_of_disagreement
```

A statement of disagreement preserves one identified human source's position concerning one canonical Portia domain record.

It does not:

- rewrite the disputed record;
- establish that the target is false;
- establish that the disagreement is correct;
- automatically invalidate or supersede the target;
- change the target's lifecycle status;
- or remove the target from authorized historical views.

## 11.2 Identity and storage

Statement-of-disagreement identifiers use:

```text
sod_<opaque-id>
```

The identifier follows the accepted Portia-owned identifier alphabet and length rules.

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    statement_of_disagreement/
      <disagreement_id>.json
```

The record is stored beneath the work containing the disputed target.

## 11.3 Semantic unit

One statement-of-disagreement record means:

> One identified human source expresses one attributed position disputing, qualifying, or objecting to one canonical Portia domain record.

A statement of disagreement is not a correction, retraction, invalidation, determination, or reply.

## 11.4 One target per record

A statement of disagreement targets exactly one:

- containing work; or
- same-work canonical domain record.

The target uses the accepted compact same-work target shape:

```text
work
local_record
```

Plural targets and target arrays are prohibited.

When one source statement concerns several records, Portia creates one disagreement record per disputed target.

Each record receives independent:

- lifecycle treatment;
- privacy treatment;
- correction treatment;
- supersession treatment;
- and projection treatment.

## 11.5 Permitted targets

Initial permitted targets include:

- Event;
- Event Participant;
- Event Participant Role;
- Work Relationship;
- and later human-meaningful Portia domain records such as Accounts, Observations, Determinations, Responses, Communications, Supports, Follow-Ups, and Outcomes.

A statement of disagreement cannot target:

- another statement of disagreement;
- a lifecycle transition;
- a lifecycle-history correction;
- an amendment;
- a migration record;
- an operation journal;
- a derived view;
- or an external-module record.

Errors in infrastructure and audit records use integrity or correction contracts rather than disagreement.

## 11.6 Required envelope

A statement-of-disagreement version-1 record contains:

```text
schema_version
record_type
module_id
class_id
work_id
disagreement_id
status
target
source
positions
statement
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

Constants are:

```text
schema_version = "1"
record_type = "statement_of_disagreement"
module_id = "portia"
```

Unlike lifecycle transitions, lifecycle-history corrections, and amendments, a statement of disagreement is a substantive attributed assertion.

It therefore has lifecycle status and ordinary update attribution.

## 11.7 Lifecycle statuses

The initial status vocabulary is:

```text
proposed
active
withdrawn
invalidated
superseded
```

Meanings are:

### `proposed`

Captured but not yet accepted as an active attributed disagreement.

### `active`

Currently preserved as the represented source's attributed disagreement.

### `withdrawn`

The represented source later withdrew the disagreement.

### `invalidated`

The disagreement should no longer be treated as a valid current assertion, without representing source withdrawal.

### `superseded`

A materially corrected successor disagreement replaces it.

The exact legal transitions and terminal-state treatment are governed by the next lifecycle decision.

## 11.8 Source and recorder are distinct

`source` identifies the human whose position is represented.

`created_by` identifies the local operator or deterministic system process that recorded it in Portia.

For example:

```text
source = roster student
created_by = teacher-local operator
```

These fields must not be conflated.

## 11.9 Source branches

### Roster student

```json
{
  "kind": "roster_student",
  "roster_student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Jordan Lee"
  }
}
```

### Actor

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_parent_001"
  },
  "display_snapshot": {
    "display_name": "Morgan Lee"
  }
}
```

### Local operator

```json
{
  "kind": "local_operator",
  "display_label": "Stephen Severino"
}
```

This is teacher-local attribution, not institutional identity authority.

### Descriptive person

```json
{
  "kind": "descriptive_person",
  "description_type": "family_member",
  "display_label": "Student's parent"
}
```

This branch is reserved for a source who should not or cannot yet be represented through the Actor Directory.

## 11.10 No unknown or system source

A canonical statement of disagreement requires enough information to attribute the position.

The initial contract does not permit:

- `unknown_person`;
- anonymous source;
- or `system_process`

as the represented disagreeing source.

A system process may import or record the statement, but it cannot itself hold a human disagreement.

## 11.11 Positions

`positions` is a nonempty unique array containing one or more of:

```text
disputes_accuracy
disputes_completeness
disputes_attribution
disputes_interpretation
disputes_context
disputes_authority
qualifies_record
objects_to_recording
objects_to_disclosure
other
```

These values describe the represented source's expressed relationship to the target.

They do not adjudicate the dispute.

When `other` is present, the statement text must make the position adequately understandable.

## 11.12 Statement representation

`statement` is a closed object containing:

```text
representation
text
```

Permitted representation values are:

```text
verbatim_quote
recorded_summary
```

Example:

```json
{
  "representation": "verbatim_quote",
  "text": "I was in the room, but I was not part of that conversation."
}
```

Example:

```json
{
  "representation": "recorded_summary",
  "text": "The student disputes being characterized as directly involved."
}
```

The distinction is authoritative:

- `verbatim_quote` claims the text preserves the source's words;
- `recorded_summary` identifies the text as the recorder's attributed summary.

The statement text composes `non_empty_text`.

It must not include unrelated third-party information merely because the field permits free text.

## 11.13 Relationship to Account

A statement of disagreement is a specialized attributed statement with an explicit disputed target.

A later Account contract must not require duplicate canonical storage of the same statement merely to make the disagreement valid.

A broader Account may exist when the represented source supplied additional context beyond the disagreement.

Later contracts may define references between the two record families, but neither record silently substitutes for the other.

## 11.14 Creation provenance and review gates

Permitted creation sources are:

```text
digital_entry
paper_capture, ingested only
import
```

Paper-capture `preallocated` creation is prohibited.

Application rules are:

- paper-captured disagreements begin as `proposed`;
- imported disagreements begin as `proposed` unless a later reviewed-import workflow explicitly permits otherwise;
- automated interpretation cannot activate a disagreement;
- a human must confirm source attribution, target, positions, and statement representation before activation.

## 11.15 Supersession

A materially corrected disagreement creates a successor.

The successor may reference predecessors through complete `portia_work_record_ref` values.

This permits correction of the disputed target to move the successor to another work root without silently relocating the predecessor.

Each supersession entry contains:

```text
work_record_ref
reason
detail, optional
```

Initial reasons are:

```text
source_corrected
target_corrected
positions_corrected
statement_corrected
duplicate_consolidated
other
```

`detail` is required for `other`.

Examples requiring successor replacement include:

- changing the represented source;
- changing the disputed target;
- changing `verbatim_quote` to a substantively different statement;
- adding or removing a material position;
- or correcting a summary in a way that changes meaning.

A nonmaterial spelling or punctuation correction may use an amendment when statement meaning and representation remain unchanged.

## 11.16 Withdrawal is not correction

When the represented source later states that they no longer maintain the disagreement:

- the original disagreement is not amended away;
- the record transitions to `withdrawn`;
- the withdrawal transition preserves reason and attribution;
- and the original statement remains historically visible to authorized readers.

A recorder must not infer withdrawal merely because the disputed target was corrected, superseded, invalidated, or otherwise changed.

## 11.17 Target lifecycle independence

A disagreement remains attached to the exact target it originally disputed.

When the target becomes:

- closed;
- withdrawn;
- invalidated;
- or superseded,

the disagreement is not automatically:

- retargeted;
- invalidated;
- withdrawn;
- superseded;
- or deleted.

Authorized views may show:

- the original target;
- its lifecycle state;
- its known successor;
- and the disagreement attached to the original target.

The disagreement does not automatically apply to the successor.

A source who also disputes the successor requires a separate disagreement record targeting that successor.

## 11.18 No reply-thread model in version 1

Statement-of-disagreement version 1 does not implement:

- replies;
- nested comments;
- debate threads;
- endorsements;
- votes;
- or automated conflict resolution.

A response may later be represented through an Account, Communication, Determination, amendment, successor record, or another appropriate domain record.

A disagreement cannot target another disagreement merely to simulate a reply.

## 11.19 Current-use implications

An active disagreement may trigger:

- a derived review indicator;
- a teacher-facing attention queue;
- or a record-specific review requirement.

It does not automatically make the target:

- invalid;
- unusable;
- unverified;
- or ineligible for all downstream use.

Later domain contracts may require specialized treatment for disputed Determinations or other high-impact records.

## 11.20 Structural validation

JSON Schema will validate:

- the exact envelope;
- constants;
- `sod_` identifier syntax;
- status vocabulary;
- compact singular target;
- closed source branches;
- nonempty unique positions;
- quote-versus-summary representation;
- optional supersession entries;
- creation provenance;
- timestamps;
- and attribution.

## 11.21 Application validation

Application validation must confirm:

- canonical path and scope agreement;
- exact target resolution;
- target eligibility for disagreement;
- source resolution and snapshot consistency;
- source and recorder remain distinct concepts;
- active uniqueness rules, if later required;
- paper and import review gates;
- statement representation is honest;
- supersession references and reasons are valid;
- no self-supersession, duplicate predecessors, or cycles exist;
- no silent retargeting occurs;
- target lifecycle changes do not automatically alter the disagreement;
- lifecycle transitions are legal;
- and authorization and privacy rules are satisfied.

## 11.22 Rejected alternatives

### Disagreement text embedded in the target

Rejected because it mutates the disputed assertion and turns the target body into an unbounded discussion container.

### Account-only representation

Rejected because disagreement requires an explicit durable relationship to one disputed target and independent lifecycle treatment.

### Anonymous or system disagreement source

Rejected because canonical disagreement requires human attribution.

### Plural-target disagreement

Rejected because each target requires independent lifecycle, privacy, correction, and projection treatment.

### Reply threads

Rejected from version 1 because Portia is not a discussion-forum model.

---


# 12. Approved Decision 9: Invalidation and Terminal-State Rules

## 12.1 Decision

Portia uses tiered lifecycle finality.

The shared model distinguishes:

1. reopenable completion;
2. replaceable terminal states;
3. an absolute terminal state.

The status token alone does not determine all use eligibility, but each terminal state has a precise lifecycle meaning.

## 12.2 Reopenable completion: `closed`

For Event, `closed` means ordinary active work is complete while the Event remains a valid canonical record.

A closed Event may:

- remain closed indefinitely;
- remain usable by authorized consumers;
- receive a nonmaterial amendment;
- transition back to `active` when additional work is genuinely required;
- transition to `invalidated`;
- or transition to `superseded`.

Reopening uses an ordinary lifecycle transition:

```text
closed -> active
```

with:

```text
reason.category = workflow
reason.code = reopened_for_review
```

Reopening does not create a successor because it does not change Event identity or intended meaning.

## 12.3 Replaceable terminal states

The following statuses are terminal for ordinary domain progression:

```text
cancelled
withdrawn
invalidated
```

A record in one of these states cannot return through an ordinary lifecycle transition to:

```text
draft
proposed
active
closed
```

It may transition only to:

```text
superseded
```

when a materially corrected successor is created.

Permitted replacement transitions include:

```text
cancelled -> superseded
withdrawn -> superseded
invalidated -> superseded
```

This preserves both facts:

1. the predecessor genuinely reached its earlier terminal state;
2. a later successor replaced it as the canonical corrected representation.

## 12.4 Absolute terminal state: `superseded`

`superseded` has no legal outgoing lifecycle transition.

A superseded record:

- remains exactly resolvable;
- remains historically visible to authorized readers;
- retains its lifecycle and amendment history;
- cannot become active again;
- cannot later become invalidated, withdrawn, cancelled, or closed;
- and is never silently redirected to its successor.

A further material correction creates another successor in the replacement graph.

It does not reactivate the superseded predecessor.

## 12.5 Status meanings

### `cancelled`

`cancelled` means the record's draft or proposal workflow was intentionally abandoned before it became an accepted active assertion.

For Event:

```text
draft -> cancelled
```

is permitted.

These are not permitted:

```text
active -> cancelled
closed -> cancelled
```

After activation, loss of current validity uses `invalidated`, while material replacement uses `superseded`.

Cancellation does not claim that a proposition was false. It means the unfinished workflow was abandoned.

### `withdrawn`

`withdrawn` applies only where the represented human source can withdraw their own attributed assertion.

The initial use is Statement of Disagreement.

Withdrawal requires a lifecycle transition representing actual source withdrawal.

A recorder must not infer withdrawal merely because:

- the target was corrected;
- the target was superseded;
- another source disagreed;
- the recorder believes the statement is inaccurate;
- or the disagreement is inconvenient.

Withdrawal does not erase the original statement.

### `invalidated`

`invalidated` means:

> The record must no longer be treated as a valid current canonical assertion, and no corrected successor presently replaces it.

Invalidation does not inherently mean:

- false;
- fabricated;
- blameworthy;
- discredited;
- malicious;
- or legally void.

Representative grounds include:

- entered in error;
- source retraction where withdrawal is not the appropriate record-specific state;
- inadequate identity;
- unsupported assertion;
- or loss of a mandatory dependency.

Invalidation is not used when a corrected successor exists.

That case uses `superseded`.

### `superseded`

`superseded` means:

> One or more accepted successor records now provide the canonical replacement representation.

Supersession does not delete the predecessor and does not rewrite references that identify it.

## 12.6 Event transition matrix

| From | Permitted destinations |
|---|---|
| `draft` | `active`, `cancelled`, `invalidated`, `superseded` |
| `active` | `closed`, `invalidated`, `superseded` |
| `closed` | `active`, `invalidated`, `superseded` |
| `cancelled` | `superseded` only |
| `invalidated` | `superseded` only |
| `superseded` | none |

The following transitions are prohibited:

```text
active -> draft
closed -> draft
active -> cancelled
closed -> cancelled
cancelled -> active
invalidated -> active
superseded -> any status
```

## 12.7 Event Participant, Event Participant Role, and Work Relationship matrix

| From | Permitted destinations |
|---|---|
| `proposed` | `active`, `invalidated`, `superseded` |
| `active` | `invalidated`, `superseded` |
| `invalidated` | `superseded` only |
| `superseded` | none |

## 12.8 Statement-of-Disagreement matrix

| From | Permitted destinations |
|---|---|
| `proposed` | `active`, `withdrawn`, `invalidated`, `superseded` |
| `active` | `withdrawn`, `invalidated`, `superseded` |
| `withdrawn` | `superseded` only |
| `invalidated` | `superseded` only |
| `superseded` | none |

`proposed -> withdrawn` is permitted when the represented source withdraws the captured statement before activation.

## 12.9 Transition-reason constraints

### Activation

Transitions to `active` use:

```text
category = workflow
```

Representative code:

```text
review_confirmed
```

### Closure and reopening

Transitions to `closed` or from `closed` to `active` use:

```text
category = workflow
```

Representative codes:

```text
work_completed
reopened_for_review
```

### Cancellation

Transitions to `cancelled` use:

```text
category = workflow
```

Representative code:

```text
teacher_cancelled
```

### Withdrawal

Transitions to `withdrawn` use:

```text
category = workflow
```

Representative code:

```text
source_withdrew
```

### Invalidation

Transitions to `invalidated` ordinarily use:

```text
record_validity
dependency
other
```

`other` requires detail.

A transition to `invalidated` must not use `correction` when a corrected successor exists.

That situation is supersession.

### Supersession

Transitions to `superseded` ordinarily use:

```text
correction
consolidation
migration
other
```

The lifecycle-transition reason must agree with the successor's specialized supersession reason.

## 12.10 Nonmaterial correction of terminal records

A terminal domain record may receive an amendment when:

- its record family permits amendment;
- every changed path is amendable;
- the semantic-equivalence test passes;
- lifecycle status remains unchanged;
- and supersession consistency remains intact.

For example, punctuation in a withdrawn disagreement's recorded summary may be corrected without reopening it.

The amendment does not change terminal status.

## 12.11 Material correction of terminal records

A materially incorrect terminal domain record receives a successor.

The predecessor:

- remains in its current terminal state until the coordinated replacement operation;
- transitions to `superseded`;
- and retains the earlier terminal transition in lifecycle history.

The successor begins with the status appropriate to its own canonical state.

For example, a corrected successor to a withdrawn disagreement may itself begin as `withdrawn` when the represented source's withdrawal still applies.

Detailed predecessor-and-successor reconciliation belongs to the next decision.

## 12.12 Erroneous terminal transition

When the terminal transition itself should never have been canonically accepted, Portia uses `lifecycle_history_correction`.

For example, an:

```text
active -> invalidated
```

transition recorded against the wrong target may be removed from the selected lifecycle branch through history correction.

The corrected selected branch may restore validated current state to `active`.

This is not an ordinary:

```text
invalidated -> active
```

transition.

It means the prior invalidation transition was historically erroneous.

## 12.13 Genuine later reversal

A later change of mind or new information does not make an earlier terminal transition erroneous.

Examples include:

- a source genuinely withdrew a disagreement and later expresses another disagreement;
- a draft Event was genuinely cancelled and later a similar Event must be recorded;
- a record was genuinely invalidated and later new evidence supports another assertion.

These cases create new canonical records.

They do not use lifecycle-history correction to rewrite what genuinely occurred.

## 12.14 Default use dispositions

Lifecycle status and use disposition remain distinct concepts.

The default mappings are:

| Current lifecycle state | Default use disposition |
|---|---|
| `draft` | `review_required` |
| `proposed` | `review_required` |
| `active` | `usable` |
| Event `closed` | `usable` |
| `cancelled` | `historical_only` |
| `withdrawn` | `historical_only` |
| `invalidated` | `historical_only` |
| `superseded` | `historical_only` |

These are defaults, not authorization decisions.

A consumer may impose stricter treatment because of:

- unresolved dependencies;
- unsupported contract versions;
- privacy;
- authorization;
- active disagreement;
- or record-family-specific rules.

A lifecycle-history mismatch yields:

```text
review_required
```

until repaired.

## 12.15 Historical resolution

Terminal records remain exactly resolvable.

Resolution does not silently return a successor.

A resolver may additionally provide derived information such as:

```text
lifecycle_status = superseded
use_disposition = historical_only
known_successors = [...]
```

but the original reference continues to identify the original record.

## 12.16 Dependencies and attached records

A terminal record may continue to have historically attached:

- statements of disagreement;
- lifecycle transitions;
- amendments;
- supersession relationships;
- and other authorized historical context.

A terminal transition does not automatically cascade status changes to attached records.

Whether an active dependent record must itself change state is governed by the later dependency decision.

## 12.17 Application validation

Application validation must confirm:

- the exact record-family transition matrix;
- terminal-state restrictions;
- reason-category and reason-code compatibility;
- existence of a successor before transition to `superseded`;
- source authority for withdrawal;
- lifecycle-history reconciliation;
- current target status agreement;
- correct default use disposition;
- no ordinary transition out of an absolute terminal state;
- and no misuse of history correction to rewrite a genuine later change.

## 12.18 Rejected alternatives

### Every end-state absolutely terminal

Rejected because Event closure is legitimate reopenable completion and terminal records may later require corrected successors.

### Every end-state reversible

Rejected because it weakens invalidation, withdrawal, cancellation, and supersession semantics.

### `invalidated -> active` ordinary transition

Rejected because reactivation would erase the distinction between a genuine later assertion and an erroneous historical transition.

### Automatic cascading from terminal records

Rejected because dependencies require record-specific treatment rather than universal status propagation.

---


# 13. Approved Decision 10: Supersession Reconciliation

## 13.1 Decision

Portia uses split authority with mandatory reconciliation.

The successor's `supersedes` field is authoritative for:

- replacement-edge identity;
- predecessor identity and contract version;
- edge-specific replacement reason;
- and any permitted edge detail.

The predecessor's selected lifecycle transition is authoritative for:

- the predecessor's current lifecycle status;
- when supersession became effective;
- who recorded the status change;
- and the lifecycle reason for the transition.

A supersession relationship is valid only when both canonical sides reconcile.

Neither side silently wins when they disagree.

## 13.2 Declared and effective supersession

A successor-side `supersedes` entry creates a:

```text
declared supersession edge
```

That edge becomes an:

```text
effective supersession edge
```

only when all of the following are true:

1. the successor is canonically accepted in a replacement-eligible state;
2. the predecessor's selected lifecycle history ends in `superseded`;
3. the selected transition to `superseded` is semantically compatible with the successor entry;
4. predecessor and successor belong to the same semantic record family;
5. the replacement topology is permitted;
6. and the coordinated operation is complete or recoverable.

A draft or proposed successor may therefore declare replacement intent without prematurely superseding its predecessor.

## 13.3 Replacement-eligible successor states

A successor is replacement-eligible when it is no longer merely preparatory and is not itself initially `superseded`.

The current record families use these replacement-eligible states:

| Record family | Replacement-eligible states |
|---|---|
| Event | `active`, `closed`, `cancelled`, `invalidated` |
| Event Participant | `active`, `invalidated` |
| Event Participant Role | `active`, `invalidated` |
| Work Relationship | `active`, `invalidated` |
| Statement of Disagreement | `active`, `withdrawn`, `invalidated` |

This permits correction of historical terminal records.

For example, an invalidated predecessor may be replaced by a corrected successor that remains invalidated.

`draft` and `proposed` successors may declare replacement intent, but their edges are not effective.

## 13.4 Reconciliation states

### Pending declaration

A successor is `draft` or `proposed`, contains `supersedes`, and the predecessor has not transitioned to `superseded`.

This is valid preparation.

It does not affect:

- predecessor use eligibility;
- reverse current-successor discovery;
- or replacement-frontier calculation.

If the proposed replacement is abandoned, its declaration never becomes effective.

### Effective replacement

The successor is replacement-eligible and the predecessor's selected lifecycle head is the matching transition to `superseded`.

The edge participates in the canonical replacement graph.

### Broken replacement

A broken replacement exists when canonical sides disagree or the intended topology is incomplete.

Representative examples include:

- a replacement-eligible successor claims an unsuperseded predecessor;
- a predecessor is `superseded` but has no effective incoming successor edge;
- transition and edge reasons conflict;
- successor and predecessor belong to different record families;
- an unauthorized second successor claims the predecessor;
- or only part of a consolidation or split operation was persisted.

A broken replacement is an integrity failure.

Portia does not:

- ignore the successor edge;
- automatically change predecessor status;
- choose whichever file is newer;
- infer the intended replacement graph;
- or silently redirect a reference.

Lifecycle-dependent writes involving affected records are blocked pending repair.

Issue #13 defines partial-write recovery mechanics.

## 13.5 Same-family requirement

A replacement edge connects records from the same semantic family.

Permitted examples include:

```text
Event v2 -> Event v1
Event Participant v2 -> Event Participant v1
Statement of Disagreement v1 -> Statement of Disagreement v1
```

Prohibited examples include:

```text
Event -> Event Participant
Event Participant -> Event Participant Role
Statement of Disagreement -> Account
Work Relationship -> Event
```

Contract-version migration may cross schema versions while preserving the semantic family.

## 13.6 Ordinary one-to-one replacement

The default topology is:

```text
one predecessor -> one direct successor
```

This covers ordinary material correction.

The successor identifies the predecessor through `supersedes`.

The predecessor receives one selected lifecycle transition to `superseded`.

## 13.7 Consolidation topology

The replacement graph permits:

```text
many predecessors -> one successor
```

for explicit consolidation.

Each predecessor:

- remains independently resolvable;
- receives its own lifecycle transition to `superseded`;
- and has its own successor-side edge and edge reason where the record contract supports per-edge reasons.

The successor becomes effective only when every predecessor in the intended consolidation set reconciles.

A partial consolidation is an integrity failure.

Portia does not accept a successful subset.

The criteria for determining that records are duplicates remain part of the later duplicate-consolidation decision.

Until that policy is accepted, the graph supports consolidation topology, but approval of a new consolidation remains blocked.

## 13.8 Split replacement topology

The general replacement graph supports:

```text
one predecessor -> several direct successors
```

only when the record family explicitly authorizes split replacement.

A split means one predecessor conflated material that must now be represented through several independent successors.

### Initial split policy

Event is the only current record family eligible for split replacement.

Representative case:

> One Event incorrectly combined two distinct occurrences and must be replaced by two Events.

Requirements are:

- every successor is an Event;
- every successor directly lists the same predecessor;
- every successor is replacement-eligible;
- all successors become effective in one coordinated operation;
- the predecessor has one transition to `superseded`;
- that transition uses:

```text
reason.category = correction
reason.code = event_split
```

- and the Issue #13 operation journal identifies the complete split set.

A later successor cannot be added to the direct split after the coordinated operation completes.

Event Participant, Event Participant Role, Work Relationship, and Statement of Disagreement do not initially permit split replacement.

Their predecessors may have at most one direct effective successor.

## 13.9 No many-to-many replacement set

Version 1 does not permit one coordinated operation with:

```text
several predecessors -> several successors
```

Such repartitioning makes lineage, reason attribution, completion, and recovery unnecessarily ambiguous.

A future contract may introduce an explicit replacement-set record when a concrete use case justifies it.

## 13.10 Successor-side authority

The successor's `supersedes` entry is canonical for:

- exact predecessor identity;
- predecessor contract version;
- edge-specific reason where the record family supplies one;
- and permitted edge detail.

Reverse relationships are derived.

The predecessor does not persist:

```text
superseded_by
successor_ids
replacement_set
```

fields.

## 13.11 Predecessor-side authority

The selected lifecycle transition is canonical for:

- when the predecessor became `superseded`;
- who recorded that state change;
- the transition's lifecycle reason;
- and the predecessor's current status.

The transition does not identify successor records.

Successor identity is resolved from incoming canonical forward edges.

## 13.12 Reason reconciliation

Where the successor edge contains a specialized reason, the predecessor transition reason must be semantically equivalent.

Representative mappings are:

| Successor edge reason | Predecessor transition reason |
|---|---|
| `identity_corrected` | `correction / identity_corrected` |
| `role_type_corrected` | `correction / role_type_corrected` |
| `basis_corrected` | `correction / basis_corrected` |
| `duplicate_consolidated` | `consolidation / duplicate_consolidated` |
| `target_corrected` | `correction / target_corrected` |
| `source_corrected` | `correction / source_corrected` |
| `statement_corrected` | `correction / statement_corrected` |

When an Event successor stores predecessor references without per-edge reasons, the predecessor lifecycle transition remains canonical for semantic reason.

Record-specific matrices define exact accepted mappings.

The later migration decision may extend mappings for migration-specific replacement.

## 13.13 Timing reconciliation

For an effective edge:

1. the successor must become replacement-eligible no later than the predecessor transition's `effective_at`;
2. the predecessor transition's `effective_at` marks when replacement became effective;
3. the transition cannot predate canonical successor acceptance;
4. all predecessors in one consolidation use a mutually consistent effective time;
5. all successors in one Event split are replacement-eligible by the split transition's effective time.

A draft successor's creation timestamp does not make replacement effective.

Its activation or accepted terminal state does.

## 13.14 Immutability after effectiveness

Once a supersession edge becomes effective:

- the successor's predecessor set is immutable;
- edge reasons are immutable;
- predecessor transitions remain append-only;
- and effective edges are never deleted.

A nonmaterial amendment cannot change `supersedes`.

## 13.15 Later lifecycle changes to a successor

An effective replacement edge remains historically valid even when the successor later becomes:

- closed;
- withdrawn;
- invalidated;
- or superseded.

The predecessor does not reactivate.

Example:

```text
A -> B
B later invalidated
```

`A` remains superseded.

There is temporarily no usable current replacement.

Example:

```text
A -> B
B -> C
```

`A` and `B` remain superseded.

`C` is the current replacement frontier.

A new correction should ordinarily supersede `B`, not create another ordinary direct edge from a later record back to `A`.

## 13.16 Replacement frontier

Successor discovery is derived separately from exact record resolution.

Given a record, Portia may derive:

```text
direct_effective_successors
replacement_frontier
```

The replacement frontier is found by following effective successor edges until reaching records that are not superseded.

It may contain:

- one record after ordinary replacement;
- several records after an authorized Event split;
- a historical-only terminal record;
- or no usable record when the latest successor was invalidated without replacement.

The resolver must still return the exact originally referenced record.

It must not silently substitute the replacement frontier.

## 13.17 Graph constraints

Application validation must reject:

- self-supersession;
- replacement cycles;
- duplicate predecessor entries;
- incompatible semantic record families;
- unsupported split topology;
- many-to-many replacement operations;
- late additions to a completed split;
- conflicting successor reasons;
- and a successor that indirectly supersedes itself.

The effective replacement graph is a directed acyclic graph.

## 13.18 Correcting an erroneous supersession edge

An effective supersession edge is never edited or deleted.

When a supersession relationship was accepted in error, correction may require:

- a corrected successor record;
- lifecycle-history correction for an incorrectly superseded predecessor;
- invalidation or supersession of the erroneous successor;
- and Issue #13 coordinated-recovery records.

The corrected graph must remain explicit.

Portia does not hide an erroneous effective edge during ordinary resolution.

A declared but never-effective edge on a draft or proposed record may be abandoned by cancelling or invalidating that proposed successor and creating a corrected replacement proposal.

## 13.19 Derived indexes

Reverse and frontier indexes are rebuildable projections.

They may cache:

```text
predecessor -> declared successors
predecessor -> effective successors
record -> replacement frontier
```

They are never canonical authority.

Rebuilding them from successor records, selected lifecycle histories, and accepted operation state must produce the same graph.

## 13.20 Structural validation

JSON Schema validates each successor-side `supersedes` field and each lifecycle-transition record independently.

Schema validation cannot establish cross-record effectiveness or topology.

## 13.21 Application validation

Application validation must confirm:

- exact predecessor and successor resolution;
- same-family compatibility;
- replacement-eligible successor state;
- predecessor selected status of `superseded`;
- transition-and-edge reason compatibility;
- timing compatibility;
- supported graph topology;
- complete consolidation and split sets;
- no self-reference or cycle;
- immutable effective predecessor sets;
- exact historical resolution;
- rebuildable reverse indexes;
- and atomic or recoverable coordinated persistence.

## 13.22 Rejected alternatives

### Predecessor transition as sole replacement authority

Rejected because a transition to `superseded` does not identify the replacement record.

### Successor field as sole replacement authority

Rejected because the predecessor could remain active while a successor claimed to replace it.

### Canonical reverse successor fields

Rejected because duplicated forward and reverse edges could disagree.

### Silent reconciliation

Rejected because neither canonical side may overwrite or reinterpret the other.

### Unrestricted split replacement

Rejected because most record families require one clear corrected successor.

### Many-to-many replacement sets

Rejected because lineage and completion semantics are too ambiguous without a dedicated future contract.

---


# 14. Approved Decision 11: Dependency Handling

## 14.1 Decision

Portia distinguishes:

1. intrinsic dependencies derived from canonical domain fields and record-family rules;
2. declared dependencies represented through separate lifecycle-bearing records when the dependency is not already fully encoded in the dependent record.

Both forms feed one derived dependency-evaluation model.

Portia does not duplicate canonical subject, target, basis, provenance, attribution, or relationship fields merely to create dependency edges.

## 14.2 Intrinsic dependencies

An intrinsic dependency exists because a domain record already contains the authoritative reference and its contract defines that reference as necessary.

Examples include:

- an Event Participant's containing Event;
- an Event Participant Role's targeted Participant;
- a Role's Account, Observation, paper, or import basis;
- a Work Relationship's source and target;
- a Statement of Disagreement's target;
- and a Statement of Disagreement's represented human source.

These relationships remain authoritative in their domain records.

Portia does not create separate dependency records merely to restate them.

A record-family policy defines:

- whether the intrinsic dependency is required or advisory;
- when the dependency is evaluated;
- which lifecycle and use states satisfy it;
- and what review follows when the dependency changes.

Intrinsic dependencies may appear in derived dependency views, but those views are not canonical storage.

## 14.3 Declared dependency record

Additional dependency conditions use a separate record:

```text
dependency
```

Dependency identifiers use:

```text
dep_<opaque-id>
```

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    dependency/
      <dependency_id>.json
```

The dependency record is stored beneath the work containing its dependent target.

## 14.4 Semantic unit

One dependency record means:

> One dependent Portia work or record has one declared dependency condition involving one exact referenced work or record.

One dependency record contains:

- one dependent;
- one dependency target;
- one strength;
- one evaluation scope;
- and one purpose.

Several dependency conditions require several dependency records.

## 14.5 Required envelope

A dependency version-1 record contains:

```text
schema_version
record_type
module_id
class_id
work_id
dependency_id
status
dependent
dependency
strength
applies_to
purpose
detail, optional
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

Constants are:

```text
schema_version = "1"
record_type = "dependency"
module_id = "portia"
```

## 14.6 Dependent target

`dependent` uses the compact same-work target model:

```text
work
local_record
```

The dependency record is dependent-owned.

A dependency whose dependent belongs to another work must be stored under that work root.

Reverse navigation from dependency target to dependent records is derived.

## 14.7 Dependency target branches

`dependency` uses one complete reference through one of the following branches.

### Portia work

```json
{
  "kind": "portia_work",
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "2"
  }
}
```

### Portia work record

```json
{
  "kind": "portia_record",
  "work_record_ref": {
    "work_ref": {
      "module_id": "portia",
      "class_id": "eng10_p2_2026",
      "work_id": "evt_example",
      "work_kind": "event",
      "contract_version": "2"
    },
    "record_ref": {
      "record_kind": "observation",
      "record_id": "obs_example",
      "contract_version": null
    }
  }
}
```

### Sibling-module work record

```json
{
  "kind": "module_record",
  "module_work_record_ref": {
    "work_ref": {
      "module_id": "another_module",
      "class_id": "eng10_p2_2026",
      "work_id": "work_example",
      "work_kind": "example_kind",
      "contract_version": "1"
    },
    "record_ref": {
      "record_kind": "example_record",
      "record_id": "record_example",
      "contract_version": "1"
    }
  }
}
```

## 14.8 Excluded targets

Version 1 does not use generic dependency records for:

- roster-student identity;
- Actor identity;
- creation attribution;
- lifecycle transitions;
- lifecycle-history corrections;
- amendments;
- dependency records;
- operation journals;
- or derived views.

Those relationships use their specialized contracts.

## 14.9 Strength

`strength` is:

```text
required
advisory
```

### `required`

A required dependency must satisfy its applicable policy before the dependent may complete the affected operation or remain automatically usable.

Failure does not directly rewrite the dependent's lifecycle status.

It first produces a dependency review condition.

### `advisory`

An advisory dependency informs interpretation, context, or review.

Loss or degradation of an advisory dependency:

- produces a derived attention indicator;
- does not alone block activation or closure;
- does not alone make the dependent unusable;
- and never automatically changes lifecycle status.

A dependency that must block use is not advisory.

## 14.10 Evaluation scope

`applies_to` is:

```text
activation
current_use
completion
```

### `activation`

The dependency is evaluated when the dependent transitions into `active`.

It must satisfy the applicable policy at the lifecycle transition's `effective_at`.

A later change to the dependency does not retroactively invalidate activation unless the record family separately requires a `current_use` dependency.

### `current_use`

The dependency is evaluated continuously for current-use eligibility.

Changes to the dependency may place an active or closed dependent into derived review.

### `completion`

The dependency is evaluated when an Event or later supported workflow record transitions to its completed state.

For Event, the initial completion gate applies before:

```text
active -> closed
```

A later dependency change does not rewrite the historical validity of a completed transition unless the original evaluation itself was erroneous.

A dependent may have separate dependency records against the same target for different evaluation scopes.

## 14.11 Purpose

The initial purpose vocabulary is:

```text
identity_resolution
evidentiary_support
authorization_basis
workflow_prerequisite
implementation_input
contextual_support
other
```

`detail` is required for `other`.

Purpose explains why the dependency matters.

It does not replace:

- a canonical subject;
- a Role basis;
- an Account;
- an Observation;
- an authority decision;
- a Work Relationship;
- or another substantive domain relationship.

Record-specific policy defines which combinations of:

```text
record family
strength
applies_to
purpose
```

are permitted.

For example, `contextual_support` will ordinarily be advisory, while `authorization_basis` may be required.

## 14.12 Dependency lifecycle

Dependency records use:

```text
proposed
active
invalidated
superseded
```

Transition matrix:

| From | Permitted destinations |
|---|---|
| `proposed` | `active`, `invalidated`, `superseded` |
| `active` | `invalidated`, `superseded` |
| `invalidated` | `superseded` only |
| `superseded` | none |

Meanings are:

- `proposed`: dependency condition prepared but not yet effective;
- `active`: current canonical dependency declaration;
- `invalidated`: dependency declaration should not be treated as valid and has no replacement;
- `superseded`: a corrected dependency declaration replaces it.

Only active declared dependencies affect current dependency evaluation.

## 14.13 Correcting a dependency declaration

The following are material changes:

- dependent target;
- dependency target;
- strength;
- evaluation scope;
- purpose.

They require a successor dependency record.

The successor's `supersedes` entries use complete `portia_work_record_ref` values.

Initial supersession reasons are:

```text
dependent_corrected
dependency_target_corrected
strength_corrected
evaluation_scope_corrected
purpose_corrected
duplicate_consolidated
other
```

`detail` is required for `other`.

A spelling or punctuation correction in nonmaterial `detail` may use an amendment.

Effective dependency supersession follows the accepted general supersession-reconciliation rules.

## 14.14 No duplicate semantic relationship

A declared dependency must not duplicate a canonical intrinsic dependency unless a future record-family contract explicitly requires both.

For example, a Role cannot:

1. identify an Account in `basis`;
2. create a generic dependency record repeating the same Account as evidentiary support;
3. and allow those references to diverge.

The Role contract governs that intrinsic dependency.

Declared dependency records exist for additional dependency conditions, not shadow copies of domain fields.

## 14.15 Derived dependency condition

Dependency health is derived rather than stored canonically.

The initial derived conditions are:

```text
satisfied
review_required
unsatisfied
indeterminate
not_currently_evaluated
```

### `satisfied`

The exact referenced target resolves and satisfies the applicable record-family policy.

### `review_required`

The dependency resolves, but its status, use disposition, disagreement state, compatibility, or another condition requires human review.

### `unsatisfied`

The exact dependency target is known not to satisfy policy.

Representative cases include:

- required target invalidated;
- required target cancelled;
- required source withdrawn;
- exact target confirmed missing;
- or target otherwise ineligible under its record-family contract.

### `indeterminate`

Portia cannot safely decide because of:

- unsupported contract version;
- unresolved external-module semantics;
- insufficient authorized visibility;
- or incomplete canonical state.

`indeterminate` must not be mislabeled as missing when authorization prevents resolution.

### `not_currently_evaluated`

The dependency is valid, but its gate is not presently being evaluated.

For example, an activation-only dependency attached to an already active record is not a continuous current-use dependency.

## 14.16 External-module dependencies

Portia does not interpret sibling-module lifecycle tokens directly.

For a `module_record` dependency, Portia relies on:

- Core reference resolution;
- compatible producer contracts;
- module-defined use disposition;
- and accepted cross-module compatibility rules.

When those semantics are unavailable:

- a required dependency is `indeterminate` and blocks its gated operation or produces `review_required`;
- an advisory dependency produces a derived attention indicator.

Portia does not invent lifecycle meaning for another module.

## 14.17 Activation gate

A dependent cannot transition into `active` unless every required activation dependency is `satisfied`.

These conditions block activation:

```text
review_required
unsatisfied
indeterminate
```

## 14.18 Completion gate

A dependent cannot enter its completed state unless every required completion dependency is `satisfied`.

## 14.19 Current-use dependency effects

For an active or closed dependent:

| Dependency condition | Derived dependent treatment |
|---|---|
| `satisfied` | No additional restriction |
| `review_required` | Dependent becomes `review_required` |
| `indeterminate` | Dependent becomes `review_required` |
| `unsatisfied` | Dependent becomes `review_required`; lifecycle-dependent writes are blocked |

The dependent's persisted lifecycle status is not automatically changed.

This avoids cascading writes before semantic consequences have been reviewed.

## 14.20 Review outcomes after dependency loss

A required current-use dependency becoming unsatisfied triggers review.

Review may produce one of the following outcomes.

### No semantic change is required

Examples include:

- the dependency becomes usable again;
- an external module becomes available;
- an authorization problem is resolved;
- or prior evaluation was temporarily indeterminate.

The derived review condition clears.

No lifecycle transition or amendment is required.

### Dependency declaration correction

When another exact dependency target can replace the prior dependency without changing the dependent's canonical meaning:

1. create a successor dependency record;
2. transition the prior dependency record to `superseded`;
3. reevaluate the dependent.

The dependent record remains unchanged.

### Material correction of the dependent

When repairing the dependency changes the dependent's:

- subject;
- target;
- evidentiary basis;
- authority;
- substantive assertion;
- or another material dimension,

the dependent requires successor replacement.

A dependency-edge correction cannot conceal a material correction to the dependent.

### Dependent invalidation

When no valid dependency can support continued current use and no corrected successor is appropriate, the dependent transitions to `invalidated`.

### Erroneous historical invalidation

Lifecycle-history correction is used only when the invalidation transition itself should never have been accepted.

Newly restored evidence or later changed circumstances do not make an earlier genuine invalidation erroneous.

## 14.21 Superseded dependency targets

Dependency references remain exact.

When a dependency target becomes `superseded`, Portia does not silently follow its replacement frontier.

For a required current-use dependency, target supersession ordinarily produces:

```text
review_required
```

until an authorized process decides whether:

- the original exact target remains historically sufficient;
- one successor should become the corrected dependency target;
- the dependent itself requires material replacement;
- or no valid dependency remains.

Selecting a successor requires an explicit successor dependency record.

Exact references are never rewritten in place.

## 14.22 No automatic cascades

A dependency target's lifecycle change does not directly write new statuses into dependent records.

Instead, Portia:

1. derives affected dependency conditions;
2. surfaces affected dependents through a review queue;
3. blocks operations whose required gates are unsatisfied or indeterminate;
4. applies explicit review outcomes to each dependent.

This prevents one incorrect transition from automatically invalidating an entire graph.

Coordinated multi-record repair remains subject to Issue #13 persistence and recovery rules.

## 14.23 Dependency cycles

Version 1 prohibits:

- self-dependency;
- direct dependency cycles;
- indirect dependency cycles.

This applies to required and advisory declared dependencies.

Intrinsic dependency graphs must also remain acyclic unless a later record-family contract explicitly defines a safe recursive structure.

A required cycle would make gate evaluation unstable.

An advisory cycle provides little semantic value and complicates review.

## 14.24 Reverse dependency discovery

Reverse indexes are derived and rebuildable.

They may provide:

```text
target -> intrinsic dependents
target -> declared dependents
target -> affected required dependents
target -> affected advisory dependents
```

They are not canonical authority.

Rebuilding them from domain records, dependency records, lifecycle histories, and producer contracts must yield the same results.

## 14.25 Structural validation

JSON Schema will validate:

- the exact dependency-record envelope;
- constants;
- `dep_` identifier syntax;
- status vocabulary;
- compact dependent target;
- complete dependency-target branches;
- strength;
- evaluation scope;
- purpose and required `other` detail;
- optional supersession entries;
- creation provenance;
- timestamps;
- and attribution.

## 14.26 Application validation

Application validation must confirm:

- canonical path and scope agreement;
- exact dependent and dependency resolution;
- dependency-target eligibility;
- absence of duplicated intrinsic relationships;
- record-specific strength, scope, and purpose compatibility;
- unique active dependency conditions;
- lifecycle legality;
- supersession reconciliation;
- no self-dependency or cycles;
- exact temporal evaluation for activation and completion gates;
- current-use dependency health;
- external-module compatibility;
- conservative treatment of authorization limitations;
- no silent successor retargeting;
- no automatic lifecycle cascade;
- and atomic or recoverable coordinated operations.

## 14.27 Rejected alternatives

### Generic dependency arrays in all domain records

Rejected because they would mix operational prerequisites with substantive domain references and require broad schema revision.

### Purely derived dependencies

Rejected because additional operational dependencies sometimes need explicit canonical representation.

### Duplicate dependency records for every reference

Rejected because canonical domain references and generic dependency edges could disagree.

### Automatic dependent invalidation

Rejected because dependency changes require explicit review and record-specific consequences.

### Silent replacement-frontier following

Rejected because exact dependency references must remain historically stable.

---


# 15. Approved Decision 12: Duplicate Consolidation

## 15.1 Decision

Portia represents duplicate consolidation through the accepted many-to-one supersession topology.

A successful consolidation creates one new reviewed successor that supersedes every confirmed duplicate predecessor.

Portia does not:

- delete duplicate records;
- select one existing duplicate as the survivor;
- mutate an existing record to absorb predecessor lineage;
- or automatically consolidate records based on similarity.

Every predecessor remains exactly resolvable with its original provenance, lifecycle, amendments, disagreements, dependencies, and incoming references.

## 15.2 Core classifications

Portia distinguishes:

```text
duplicate_candidate
confirmed_duplicate
related_but_distinct
material_correction
```

A similarity match creates only a duplicate candidate.

Consolidation occurs only after authorized review confirms that the records represent the same canonical assertion, subject, occurrence, relationship, or dependency condition.

## 15.3 Duplicate-equivalence test

Records are confirmed duplicates only when all five gates pass.

### Same semantic family

Every proposed predecessor belongs to the same semantic record family.

Permitted examples include:

```text
Event + Event
Event Participant + Event Participant
Dependency + Dependency
```

Prohibited examples include:

```text
Event + Observation
Account + Statement of Disagreement
Event Participant + Event Participant Role
```

Contract versions may differ when the records remain members of the same semantic family.

### Same real-world referent or assertion

The records represent the same underlying thing, not merely similar or overlapping things.

The following are not sufficient by themselves:

- same student;
- same date;
- same classroom;
- similar wording;
- same Role type;
- same dependency target;
- or nearby timestamps.

### No independent semantic significance

Preserving both records must not communicate independently meaningful:

- source attribution;
- observation act;
- communication act;
- institutional decision;
- occurrence;
- implementation;
- outcome;
- or lifecycle event.

Two independently made Observations are not duplicates merely because they report the same conduct.

Two separate statements from the same person are not duplicates merely because their wording is identical.

They are duplicates only when review establishes that both are duplicate captures of the same originating act or assertion.

### Compatible material content

The records must not materially contradict one another.

Potentially compatible differences include:

- one record omitting a detail contained in another;
- spelling or formatting differences;
- complementary noncontradictory Role basis entries;
- or compatible descriptive precision.

Material conflicts block consolidation.

Representative conflicts include disagreement about:

- who was involved;
- whether an occurrence happened;
- occurrence date or time;
- Role type;
- represented statement source;
- target;
- authority;
- relationship direction;
- or substantive meaning.

Conflicting records remain separate until handled through correction, disagreement, determination, invalidation, or another appropriate process.

### Complete provenance preservation

Every predecessor remains an immutable historical record.

The consolidation must preserve access to:

- each predecessor's creator;
- creation time;
- creation source;
- lifecycle history;
- amendments;
- statements of disagreement;
- dependencies;
- and references from other records.

Successor lineage exposes predecessor provenance.

It does not overwrite or collapse it.

## 15.4 Duplicate classes

### Exact duplicate

Records are semantically identical after excluding:

- canonical identifiers;
- storage paths;
- creation and update timestamps;
- creation and update attribution;
- lifecycle history;
- and replacement lineage.

Mechanical detection may identify exact equivalence, but human confirmation remains required before canonical consolidation.

### Compatible duplicate

Records represent the same canonical assertion but contain compatible, noncontradictory differences.

A human constructs the unified successor.

### Related but distinct

Records overlap but preserve independent semantic or evidentiary value.

They are not consolidated.

A relationship, shared target, derived grouping, or another domain mechanism may connect them.

## 15.5 No separate consolidation record

Version 1 does not introduce a canonical `consolidation` record.

Consolidation is represented through:

1. one new successor containing the complete predecessor set;
2. one lifecycle transition to `superseded` for each predecessor;
3. `consolidation / duplicate_consolidated` lifecycle-transition reasons;
4. record-family successor entries using `duplicate_consolidated` where supported;
5. the coordinated-operation contract defined in Issue #13.

The successor's `supersedes` set is the canonical consolidation-membership list.

A separate consolidation record would duplicate that topology.

## 15.6 New successor required

Portia never designates an existing duplicate as the survivor.

Every successful consolidation creates a new canonical successor.

This applies even when the predecessors are exact duplicates.

The new successor provides:

- symmetric treatment of predecessor provenance;
- immutable predecessor content;
- explicit reviewed lineage;
- a canonical consolidation time;
- and an independently validated unified representation.

The successor receives its own:

```text
record_id
creation_source
created_at
created_by
updated_at
updated_by
```

It does not inherit or backdate those fields from a predecessor.

Domain occurrence time remains represented in the relevant domain field.

## 15.7 Eligible predecessors

A direct consolidation predecessor:

- resolves exactly;
- belongs to the same semantic family as every other predecessor;
- is not already `superseded`;
- passes the duplicate-equivalence test;
- and may legally transition to `superseded`.

A predecessor may currently be:

- active;
- closed;
- invalidated;
- withdrawn;
- cancelled;
- proposed;
- or draft,

when its record-family lifecycle permits replacement from that status.

A duplicate draft or proposal that was never meaningfully accepted and contributes no unique compatible information should ordinarily be cancelled or invalidated rather than consolidated.

Consolidation is appropriate when symmetric lineage preservation is substantively useful.

## 15.8 Pure-consolidation rule

A duplicate-consolidation operation must be a pure consolidation.

It may:

- reconcile compatible omissions;
- normalize presentation;
- preserve the union of compatible set-valued information;
- and create a reviewed unified expression of the same assertion.

It must not simultaneously conceal:

- identity correction;
- target correction;
- source correction;
- changed occurrence;
- changed Role type;
- changed authority basis;
- or another unrelated material correction.

When one record materially corrects another, Portia uses ordinary replacement with the appropriate correction reason.

When one Event conflates several occurrences, Portia uses Event split replacement.

Mixed correction and consolidation must be decomposed into explicit operations.

## 15.9 Constructing the successor

The successor must be independently valid under its current record-family contract.

### Identity-bearing fields

Identity-bearing fields must:

- agree exactly;
- be demonstrably equivalent under record-family policy;
- or cause consolidation to fail.

### Scalar substantive fields

A scalar value may be selected from one predecessor only when:

- other predecessors do not contradict it;
- the value remains part of the same assertion;
- and selection does not hide uncertainty.

Portia does not use:

```text
newest_wins
oldest_wins
majority_vote
non_null_wins
longest_text_wins
```

rules.

### Set-valued fields

Compatible set-valued fields may be unified when:

- order is contractually nonsemantic;
- every item remains valid;
- entries do not conflict;
- and the union does not alter canonical meaning.

For example, duplicate Role records with the same target and Role type may preserve a union of compatible basis entries.

### Narrative fields

Narrative content may be synthesized only when:

- every material proposition is supported by at least one predecessor;
- no predecessor materially contradicts the proposition;
- the result introduces no unsupported proposition;
- and the result remains the same canonical assertion.

Simple concatenation is not automatically valid.

## 15.10 Event duplicate rules

Events are duplicates only when they represent the same real-world occurrence.

Review considers:

- occurrence;
- participants;
- location;
- instructional context;
- summary;
- ownership;
- and surrounding records.

Two Events on the same day involving the same student are not necessarily duplicates.

When one Event conflates several occurrences, use Event split replacement.

Consolidation must not bypass later Event-ownership correction rules.

## 15.11 Event Participant duplicate rules

Event Participants are duplicates only when they:

- belong to the same Event;
- and represent the same human subject.

Different durable subject identities block consolidation.

Resolving an unknown or descriptive subject to a roster student or Actor is ordinarily identity correction, not pure duplicate consolidation.

## 15.12 Event Participant Role duplicate rules

Roles are duplicates only when they have:

- the same Event;
- the same Participant target;
- the same Role type;
- and materially compatible Role meaning.

Compatible basis sets may be unified.

Different Role types or materially conflicting details are not duplicates.

## 15.13 Work Relationship duplicate rules

Work Relationships are duplicates only when they have:

- the same source;
- the same target;
- the same relationship type;
- and compatible detail.

Similar relationships with different endpoints remain distinct.

## 15.14 Statement-of-Disagreement duplicate rules

Statements of disagreement are duplicates only when they represent duplicate captures of the same originating statement by:

- the same represented source;
- concerning the same exact target;
- with the same material positions;
- and the same substantive statement.

Separate expressions of disagreement remain distinct even when wording is identical.

## 15.15 Dependency duplicate rules

Dependencies are duplicates only when they have the same:

- dependent;
- dependency target;
- strength;
- evaluation scope;
- and purpose.

A difference in any of these dimensions is material dependency correction, not consolidation.

## 15.16 Consolidation operation

A successful consolidation logically performs:

1. identify and lock the complete predecessor set;
2. confirm duplicate equivalence;
3. create and validate the new successor;
4. make the successor replacement-eligible;
5. transition every predecessor to `superseded`;
6. reconcile every successor edge and transition reason;
7. confirm the complete effective many-to-one replacement graph;
8. rebuild affected projections and review queues.

Every predecessor transition uses:

```text
reason.category = consolidation
reason.code = duplicate_consolidated
```

Application policy requires concise `reason.detail` explaining why the records were determined to represent the same canonical assertion.

Where the successor contract includes per-edge reasons, every edge uses:

```text
duplicate_consolidated
```

Every predecessor transition uses one mutually consistent effective time.

Partial success creates a broken replacement and an integrity failure.

Issue #13 defines persistence and recovery mechanics.

## 15.17 Successor lifecycle

The successor begins in the lifecycle state appropriate to the unified canonical record.

It does not automatically inherit the chronologically newest or nominally highest predecessor state.

Representative outcomes include:

- duplicate active Roles ordinarily producing an active successor;
- duplicate closed Events potentially producing a closed successor;
- duplicate historical invalidated records potentially producing an invalidated successor;
- duplicate disagreements not becoming active when represented-source withdrawal still applies.

Lifecycle selection requires record-specific review.

## 15.18 Attached records and exact references

Consolidation does not automatically move or copy:

- statements of disagreement;
- dependencies;
- Accounts;
- Observations;
- relationships;
- amendments;
- or other records attached to a predecessor.

Those records continue to identify the exact predecessor they originally referenced.

They do not silently apply to the consolidated successor.

A current-use relationship that should target the successor requires explicit review and, where necessary:

- successor dependency;
- successor relationship;
- new statement of disagreement;
- or materially corrected dependent record.

Exact references remain stable.

## 15.19 Duplicate detection

Applications may derive duplicate candidates using:

- exact semantic fingerprints;
- matching authoritative identities;
- overlapping occurrence information;
- matching endpoints;
- normalized-text comparison;
- import-source identifiers;
- or other family-specific signals.

Candidate-generation logic must preserve the distinction between:

```text
possible_duplicate
confirmed_duplicate
```

A confidence score, fingerprint match, or machine-learning result cannot canonically consolidate records.

Automated detection may place candidates in a review queue only.

## 15.20 Existing uniqueness violations

When several active records violate a record-family uniqueness rule:

- affected records become `review_required`;
- lifecycle-dependent writes may be blocked;
- but Portia does not automatically select a survivor or consolidate them.

Review may conclude that records are:

- duplicates requiring consolidation;
- materially conflicting;
- valid and distinct;
- or subject to another correction path.

## 15.21 Later-discovered duplicates

An effective consolidation set is immutable.

A later-discovered duplicate is not added retroactively to the old successor's predecessor set.

Instead, Portia creates a new successor that supersedes:

- the current replacement-frontier record;
- and the newly discovered duplicate.

Example:

```text
A + B -> C
C + D -> E
```

The original:

```text
A + B -> C
```

consolidation remains unchanged.

## 15.22 Erroneous consolidation

An effective consolidation edge is never edited or deleted.

Incorrect consolidation may require:

- lifecycle-history correction for predecessors that should not have been superseded;
- invalidation or supersession of the erroneous consolidated successor;
- new corrected successor records;
- and coordinated recovery under Issue #13.

Portia does not silently hide an erroneous consolidation or restore predecessors through ordinary lifecycle transitions.

The later integrity-finding decision defines how such failures are classified and surfaced.

## 15.23 Derived views

Derived indexes may expose:

```text
duplicate_candidates
confirmed_effective_consolidations
consolidation_predecessor_sets
current_replacement_frontiers
```

These indexes are rebuildable.

They are not canonical authority.

## 15.24 Structural validation

Duplicate equivalence cannot be established by JSON Schema.

Existing and later record-family schemas validate:

- successor structure;
- predecessor-reference structure;
- supersession reasons;
- lifecycle-transition structure;
- and local field constraints.

Consolidation semantics remain application-level.

## 15.25 Application validation

Application validation must confirm:

- same semantic record family;
- complete predecessor set;
- no already-superseded direct predecessor;
- duplicate equivalence;
- absence of independently meaningful source acts;
- compatible material content;
- independently valid successor content;
- no survivor shortcut;
- no newest-wins or other arbitrary selection rule;
- pure-consolidation semantics;
- complete reason reconciliation;
- mutually consistent effective timing;
- supported many-to-one topology;
- no silent movement of attached records;
- immutable completed consolidation sets;
- and atomic or recoverable persistence.

## 15.26 Rejected alternatives

### Delete duplicate records

Rejected because deletion would erase provenance, lifecycle history, references, amendments, and disagreement context.

### Select an existing survivor

Rejected because it privileges one predecessor's provenance and requires retroactive lineage mutation.

### Automatic consolidation

Rejected because similarity signals cannot prove semantic equivalence.

### Separate consolidation record

Rejected because the successor's predecessor set already provides canonical consolidation membership.

### Mixed correction and consolidation

Rejected because each material operation requires explicit semantics and lineage.

---


# 16. Approved Decision 13: Migration-Record Semantics

## 16.1 Decision

Portia represents a completed representation-only migration through a dedicated immutable canonical record:

```text
record_migration
```

A migration record certifies that one exact canonical Portia representation was transformed into one exact destination representation through one identified migration procedure while preserving canonical meaning.

Migration-attempt progress, failure, retry, rollback, and recovery are not lifecycle states on this record. They belong to the Issue #13 operation-journal and recovery architecture.

## 16.2 Identity and storage

Migration identifiers use:

```text
mig_<opaque-id>
```

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    record_migration/
      <migration_id>.json
```

The migration record is stored beneath the destination's work root.

Ordinary migration cannot change Event ownership or work-root placement.

Source and destination therefore belong to the same Portia work root.

Moving a record to another root uses the later ownership-correction contract.

## 16.3 Semantic unit

One migration record means:

> One exact canonical Portia representation was transformed into one exact destination representation through one identified migration procedure, with canonical meaning preserved.

One migration record contains exactly:

- one source;
- one destination;
- one migration reason;
- one transformation procedure;
- and one effective time.

A migration record never represents several sources or several destinations.

## 16.4 Required envelope

A record-migration version-1 record contains:

```text
schema_version
record_type
module_id
class_id
work_id
migration_id
source
destination
reason
transformation
effective_at
creation_source
created_at
created_by
```

Constants are:

```text
schema_version = "1"
record_type = "record_migration"
module_id = "portia"
```

The record does not contain:

```text
status
updated_at
updated_by
previous_migration
operation_id
authorized_by
reviewed_by
```

## 16.5 No lifecycle status

A canonical migration record represents only a migration accepted as complete.

The following are operational conditions, not migration-record statuses:

```text
planned
queued
running
failed
retrying
rolled_back
abandoned
```

Those conditions belong to the Issue #13 operation journal and recovery model.

Operational progress is not represented through mutable lifecycle state on the immutable migration certificate.

## 16.6 Migration endpoint union

`source` and `destination` use the same closed endpoint union.

### Work endpoint

```json
{
  "kind": "work",
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  },
  "observed_updated_at": "2026-08-03T20:10:00-04:00"
}
```

### Work-record endpoint

```json
{
  "kind": "work_record",
  "work_record_ref": {
    "work_ref": {
      "module_id": "portia",
      "class_id": "eng10_p2_2026",
      "work_id": "evt_example",
      "work_kind": "event",
      "contract_version": "2"
    },
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ept_example",
      "contract_version": "1"
    }
  },
  "observed_updated_at": "2026-08-03T20:10:00-04:00"
}
```

Requirements are:

- source and destination use the same endpoint kind;
- both contract versions are non-null;
- both references resolve exactly;
- both belong to the same semantic record family;
- both belong to the same owning work root;
- source and destination references are not identical;
- and each `observed_updated_at` identifies the exact domain-record revision evaluated during migration.

The observed revision timestamp binds the certificate to the precise source and destination states that were compared.

The next decision defines whether record identifiers and other identity-bearing values must remain the same across endpoints.

## 16.7 Reason structure

`reason` is a closed object containing:

```text
category
code
detail, optional
```

Permitted categories are:

```text
contract_upgrade
contract_normalization
canonical_representation_change
other
```

### `contract_upgrade`

The destination uses a newer supported contract version.

### `contract_normalization`

The source uses a supported but nonpreferred representation and is transformed to the preferred representation without semantic change.

### `canonical_representation_change`

Canonical serialization changes while the domain assertion remains equivalent.

This category does not authorize movement to another ownership root.

### `other`

Reserved for a representation-only migration not covered by a recognized category.

`detail` is required for `other`.

`code` follows:

```text
^[a-z][a-z0-9_]*$
```

Representative codes include:

```text
event_v1_to_v2
event_participant_v1_to_v2
event_participant_role_v1_to_v2
```

A recognized migration code identifies a registered:

- source semantic family;
- source contract version;
- destination contract version;
- and transformation policy.

## 16.8 Transformation procedure

`transformation` is a closed object containing:

```text
transformer_id
transformer_version
```

Example:

```json
{
  "transformer_id": "event_v1_to_v2",
  "transformer_version": "1"
}
```

`transformer_id` follows:

```text
^[a-z][a-z0-9_]*$
```

`transformer_version` is a required nonempty version identifier.

The procedure may be:

- fully automated;
- deterministic but human-triggered;
- or manually applied through a registered migration procedure.

A manual migration still uses a stable procedure identifier, such as:

```text
manual_event_v1_to_v2
```

The procedure identifier does not prove semantic validity.

Application validation independently verifies the result.

## 16.9 Creation provenance and attribution

A migration record's `creation_source` is always:

```json
{
  "type": "digital_entry"
}
```

Paper capture cannot create a migration record.

An external legacy record entering Portia for the first time is an import, not a migration, because no canonical Portia source representation exists.

`created_by` composes `attribution_agent` and may identify:

- a local operator;
- or a deterministic system process.

`created_by` means the agent that canonically persisted the completed migration certificate.

It does not establish:

- authorization;
- institutional approval;
- employment status;
- legal authorship;
- or decision authority.

Version 1 does not add `authorized_by` or `reviewed_by`.

Application policy may require human review before acceptance, but the shared migration envelope does not invent an authority claim.

## 16.10 Representation-only boundary

Migration preserves the same canonical assertion for every legitimate downstream use.

It must not change:

- semantic record family;
- owning class;
- owning work root;
- subject identity;
- target identity;
- source identity;
- represented occurrence;
- relationship direction or type;
- evidentiary meaning;
- authority or disclosure meaning;
- lifecycle meaning;
- dependency meaning;
- substantive proposition;
- or historical attribution.

Permitted differences are limited to those required by the destination contract or canonical representation.

Examples include:

- renamed schema properties with equivalent meaning;
- replacement of an obsolete reference shape with an accepted shared reference;
- normalized structural wrappers;
- explicit representation of formerly implicit nullability;
- or the same value expressed under a newer schema vocabulary.

A migration must not introduce a factual proposition that cannot be derived from the source representation.

## 16.11 No guessing

When the destination requires information the source does not establish, migration is blocked unless the destination contract provides an honest semantically equivalent absence representation, such as:

```text
unknown
not_reported
withheld
legacy_import
```

A migration process cannot guess a value merely to satisfy destination schema requirements.

## 16.12 No repair during migration

When migration reveals that the source is substantively wrong, the transformation must not silently correct it.

The operator uses the applicable explicit process:

- amendment;
- material successor correction;
- invalidation;
- duplicate consolidation;
- Event split;
- dependency correction;
- or ownership correction.

Migration cannot be combined with those semantic changes in one operation.

## 16.13 Relationship to correction and import

| Operation | Meaning changes? | New representation? |
|---|---:|---:|
| Amendment | No | No contract migration |
| Material correction | Yes | Usually new successor |
| Duplicate consolidation | Unified assertion | New successor |
| Migration | No | Yes |
| Ownership correction | Ownership or root changes | Yes |
| Import | Creates first Portia representation | Yes |

The operator-selected reason does not establish semantic equivalence.

Application validation compares the complete source and destination states.

When semantic equivalence cannot be established, the operation is not a migration.

## 16.14 Relationship to supersession

A migration record does not by itself:

- activate the destination;
- change source status;
- create a replacement edge;
- or make the destination current.

When migration creates a separate replacement representation, it also reconciles through the accepted supersession architecture:

1. the destination identifies the source through the record-family `supersedes` mechanism;
2. the source receives a lifecycle transition to `superseded`;
3. the transition uses:

```text
reason.category = migration
```

4. the transition code matches the migration record's reason code;
5. the migration record identifies the same source and destination;
6. all effective times agree.

For record families with specialized successor-edge reasons, the common initial migration reason is:

```text
contract_migrated
```

That reason must be added explicitly to migration-capable record-family contracts.

Migration must not be hidden under `other` when a recognized migration reason exists.

The migration certificate, successor edge, and predecessor transition form a three-part reconciliation.

When any part is absent or contradictory after the destination becomes replacement-eligible, migration is broken and lifecycle-dependent operations are blocked pending recovery.

The next identity-preservation decision determines whether every migration uses a distinct replacement identity or some contract versions may share a stable logical identity.

## 16.15 Timing rules

`effective_at` means:

> The time at which the destination representation became the accepted current representation for the migration operation.

Application validation requires:

- source and destination existed no later than `effective_at`;
- both observed revisions existed no later than `effective_at`;
- `effective_at <= created_at`;
- no future-effective migration;
- destination was structurally and application-valid by `effective_at`;
- source and destination semantic equivalence was established before effectiveness;
- and any source supersession transition uses the same `effective_at`.

The migration record may be persisted after the effective operation, but Issue #13 must make the coordinated sequence atomic or recoverable.

Filesystem timestamps are not migration authority.

## 16.16 One certificate per migrated record

One migration record contains one source and one destination.

A work migration involving:

- one Event;
- three Participants;
- five Roles;
- and two Work Relationships

creates eleven migration records.

Issue #13 may group those records through one coordinated operation-journal entry.

Individual migration records remain independently:

- resolvable;
- validatable;
- recoverable;
- and attributable.

This avoids a batch certificate whose partial success is ambiguous.

## 16.17 Parent and child ordering

A work-root migration may require an ordered operation:

1. prepare the destination root;
2. migrate required child records;
3. validate the destination graph;
4. make the destination representation replacement-eligible;
5. reconcile source retirement;
6. accept all migration certificates.

The exact persistence sequence belongs to Issue #13.

No child migration succeeds semantically merely because the parent root migrated.

## 16.18 Eligible records

Initial migration eligibility includes lifecycle-bearing Portia domain records and work roots.

Examples include:

- Event;
- Event Participant;
- Event Participant Role;
- Work Relationship;
- Statement of Disagreement;
- Dependency;
- and later substantive Portia record families.

Version 1 does not migrate immutable audit records such as:

- lifecycle transitions;
- lifecycle-history corrections;
- amendments;
- record-migration records;
- or Issue #13 operation journals.

Those records remain valid under their historical contract versions.

A newer immutable-audit schema applies prospectively instead of rewriting accepted historical audit records.

## 16.19 Source lifecycle restrictions

A migration source must not already be `superseded`.

An already superseded representation remains available under its historical contract.

A later migration applies to the current replacement-frontier record.

Migration may operate on other replacement-eligible terminal states while preserving their semantics, including:

- `cancelled`;
- `withdrawn`;
- or `invalidated`.

For example, an invalidated v1 record may migrate to an invalidated v2 representation without becoming active.

Migration cannot revive a terminal assertion.

## 16.20 Destination lifecycle preservation

A representation-only destination preserves the source's semantic lifecycle state at the moment migration becomes effective.

Representative mappings are:

```text
active v1 -> active v2
closed v1 -> closed v2
withdrawn v1 -> withdrawn v2
invalidated v1 -> invalidated v2
```

The source transitions to `superseded` only because the destination representation replaces it.

Migration does not perform:

```text
invalidated -> active
withdrawn -> active
cancelled -> active
```

Such lifecycle changes require separate semantic operations.

Record identifiers, original creation provenance, and lifecycle-history continuity are governed by the next identity-preservation decision.

## 16.21 Failed and interrupted migrations

A canonical migration record is not written merely because a migration attempt starts.

Interrupted operations may leave:

- destination preparation files;
- pending successor declarations;
- operation-journal entries;
- temporary staging content;
- or incomplete lifecycle updates.

Issue #13 determines whether those artifacts are:

- resumed;
- rolled back;
- quarantined;
- or completed.

A destination cannot be treated as the accepted current representation unless migration reconciliation is complete.

Portia never chooses between source and destination based on:

- file modification time;
- highest schema version;
- newest creation timestamp;
- or mere destination existence.

## 16.22 Erroneous migration records

A canonically accepted migration record is immutable.

It is not amended, invalidated, or deleted.

When a migration record was accepted in error:

- the failure is surfaced as an integrity problem;
- erroneous successor or lifecycle effects are repaired explicitly;
- a corrected migration certificate may be created only for a valid source-and-destination transformation;
- and Issue #13 recovery records preserve what occurred.

The migration graph does not silently ignore an accepted certificate.

The later integrity-finding vocabulary defines its diagnostic classification.

## 16.23 Derived migration views

Applications may derive rebuildable views such as:

```text
source_representation -> migration_records
destination_representation -> originating_migration
record_family -> migration_history
unsupported_contracts -> migration_candidates
broken_migration_reconciliations
```

These views are not canonical authority.

They are reproduced from:

- exact source and destination records;
- migration certificates;
- lifecycle histories;
- successor edges;
- and accepted operation state.

## 16.24 Structural validation

JSON Schema will validate:

- the exact envelope;
- constants;
- `mig_` identifier syntax;
- closed source and destination endpoint forms;
- non-null contract versions;
- observed revision timestamps;
- reason structure;
- transformation structure;
- digital-only creation provenance;
- effective and creation timestamps;
- and attribution.

JSON Schema cannot establish semantic equivalence or coordinated effectiveness.

## 16.25 Application validation

Application validation must confirm:

- canonical storage-path agreement with the destination work root;
- exact source and destination resolution;
- same endpoint kind;
- same semantic family;
- same owning work root;
- source and destination are not identical references;
- observed revision agreement;
- registered migration reason and transformation compatibility;
- representation-only semantic equivalence;
- absence of guessed or repaired facts;
- source lifecycle eligibility;
- destination lifecycle preservation;
- no migration of immutable audit records;
- no ownership or work-root change;
- no batch migration hidden inside one record;
- successor and lifecycle reconciliation where required;
- matching effective times;
- no migration cycles;
- and atomic or recoverable persistence.

## 16.26 Rejected alternatives

### Supersession-only migration

Rejected because successor and lifecycle records do not identify the exact transformation procedure or certify semantic equivalence.

### Migration metadata embedded in destination records

Rejected because migration concerns two representations rather than the destination's substantive assertion.

### Lifecycle-bearing migration jobs

Rejected because attempt progress belongs to operation and recovery mechanics.

### Batch migration certificates

Rejected because each migrated record must remain independently resolvable, validatable, and recoverable.

### Migration of immutable audit history

Rejected because accepted audit records remain valid under their historical contract versions.

---

# 17. Approved Decision 14: Migration Identity Preservation

## 17.1 Decision

Portia distinguishes:

```text
logical record identity
exact representation identity
```

A representation-only migration preserves logical identity and changes only exact representation identity.

Portia does not:

- assign a new Event `work_id`;
- assign a new child-record identifier;
- overwrite the source representation;
- copy source creation provenance into the destination;
- replay source lifecycle history into the destination;
- or silently redirect exact references.

## 17.2 Logical work identity

For a Portia work root, logical identity is:

```text
module_id
class_id
work_kind
work_id
```

These values remain stable across migration.

## 17.3 Logical child-record identity

For a Portia child record, logical identity is:

```text
module_id
class_id
work_id
record_kind
record_id
```

These values remain stable across migration.

## 17.4 Exact representation identity

Exact representation identity adds:

```text
contract_version
```

Therefore:

```text
evt_example / Event v1
evt_example / Event v2
```

are:

- the same logical Event identity;
- but different exact Event representations.

Likewise:

```text
ept_example / Event Participant v1
ept_example / Event Participant v2
```

are the same logical Participant identity but different exact representations.

## 17.5 Required identifier preservation

A representation-only migration preserves:

- `module_id`;
- `class_id`;
- `work_kind`;
- `work_id`;
- `record_kind`, for child records;
- `record_id`, for child records.

Source and destination differ in:

```text
contract_version
```

Version 1 does not support same-contract-version migration.

A representation rewrite retaining the same contract version is ordinarily:

- a nonmaterial amendment;
- an integrity repair;
- or no canonical operation,

depending on its semantics.

## 17.6 Event-root consequence

An Event migration retains the same `work_id`.

Example:

```text
Portia Event evt_123, contract v1
    ->
Portia Event evt_123, contract v2
```

The migration does not create a new Event work root.

All destination child records remain beneath:

```text
classes/<class_id>/modules/portia/work/evt_123/
```

A new Event ID would represent a different work.

It would therefore be correction, split, consolidation, or ownership movement rather than representation-only migration.

## 17.7 Child-record consequence

Migrated child records retain their record identifiers.

Example:

```text
Event Participant ept_123, contract v1
    ->
Event Participant ept_123, contract v2
```

Changing `ept_123` to another Participant ID is not ordinary migration.

It requires another explicit operation unless a future contract defines a broader identity-mapping architecture.

## 17.8 Stable kind tokens

Version 1 migration also requires stable:

```text
work_kind
record_kind
```

tokens.

Renaming a canonical kind cannot be represented safely as ordinary version-1 migration because no separate stable semantic-family identifier currently exists outside those tokens.

A future contract may add explicit semantic-family identifiers and permit kind renaming.

Until then, kind changes are blocked.

## 17.9 Representation coexistence

Source and destination are separate canonical representations.

Both remain exactly resolvable by:

```text
logical identifiers + contract_version
```

The destination does not overwrite or destroy the source representation.

The physical persistence mechanism for historical versioned representations belongs to Issue #13, but it must satisfy:

- the old representation remains immutable and retrievable;
- the new representation becomes current only after reconciliation;
- source and destination coexist logically under the same stable ID;
- and exact version resolution does not depend on filesystem modification time.

Migration cannot be enabled until persistence supports version-qualified historical resolution.

## 17.10 Self-supersession interpretation

The prohibition on self-supersession applies to the same exact representation identity.

Prohibited:

```text
Event evt_123 v2 -> Event evt_123 v2
```

Permitted only for accepted migration:

```text
Event evt_123 v1 -> Event evt_123 v2
```

The migration case preserves logical identity while replacing one exact representation with another.

Reusing one logical ID across contract versions is reserved for representation-only migration.

Ordinary material correction, consolidation, or split replacement creates new logical identifiers.

## 17.11 One current representation

For each logical identity, Portia permits at most one effective current representation.

After successful migration:

```text
evt_123 v1 = superseded
evt_123 v2 = current
```

Two non-superseded canonical representations of the same logical identity constitute a broken migration or integrity failure.

A source representation has at most one direct effective migration destination.

Migration therefore forms a nonbranching version chain:

```text
v1 -> v2 -> v3
```

It does not form:

```text
      -> v2a
v1
      -> v2b
```

Branching replacement remains available only through record-family correction or Event-split rules using new logical IDs.

## 17.12 Destination creation provenance

Creation provenance is representation-local.

The destination uses:

```json
{
  "type": "digital_entry"
}
```

It does not copy the source's `creation_source`.

For example:

```text
source v1 creation_source = paper_capture
destination v2 creation_source = digital_entry
```

This does not erase paper provenance.

The source remains immutable and is linked through:

- the migration certificate;
- the destination's migration supersession entry;
- and the source's lifecycle transition.

A derived provenance view may report that the current representation migrated from a paper-captured source representation.

Copying `paper_capture` to the destination would falsely claim the destination representation came directly from paper.

## 17.13 Destination timestamps and attribution

The destination receives representation-local provenance:

```text
created_at = migration effective_at
created_by = migration record created_by
updated_at = created_at
updated_by = created_by
creation_source = digital_entry
```

The destination does not backdate `created_at` to source creation time.

The source retains its original:

- `creation_source`;
- `created_at`;
- `created_by`;
- `updated_at`;
- and `updated_by`.

The migration certificate preserves the relationship between representation histories.

## 17.14 Logical-origin projection

Applications may derive:

```text
logical_origin_representation
logical_origin_creation_source
logical_origin_created_at
logical_origin_created_by
migration_chain
current_representation
```

These are projections.

They are not copied into every destination record.

For:

```text
v1 -> v2 -> v3
```

the logical origin remains v1, while v3 retains its own representation-local creation provenance.

## 17.15 Lifecycle-history treatment

Lifecycle history remains attached to exact representations.

The source representation retains:

- its creation baseline;
- all ordinary lifecycle transitions;
- all lifecycle-history corrections;
- all amendments;
- and its final transition to `superseded` for migration.

The destination does not copy or replay those transitions.

It begins with a creation baseline matching the source's semantic status immediately before migration.

Representative baselines include:

```text
active v1 -> active v2 baseline
closed v1 -> closed v2 baseline
proposed v1 -> proposed v2 baseline
withdrawn v1 -> withdrawn v2 baseline
invalidated v1 -> invalidated v2 baseline
```

The destination baseline is established at migration `effective_at`.

The source ends in:

```text
superseded
```

using:

```text
reason.category = migration
reason.code = <migration reason code>
```

## 17.16 No fabricated transition replay

Suppose v1 followed:

```text
draft -> active -> closed
```

A migrated v2 Event begins with baseline:

```text
closed
```

Portia does not fabricate v2 transitions replaying:

```text
draft -> active -> closed
```

Those transitions occurred in v1 representation history.

A logical-history projection may display:

```text
v1 creation and transitions
migration
v2 baseline and later transitions
```

but exact representation histories remain separate.

## 17.17 Migration of preparatory states

Pure migration may preserve:

```text
draft
proposed
```

states.

This is a narrow migration exception to ordinary successor replacement eligibility.

A migrated draft remains draft.

A migrated proposal remains proposed.

The migration becomes effective because:

- logical identity is unchanged;
- semantic status is unchanged;
- the migration certificate is accepted;
- and three-part migration reconciliation is complete.

This exception does not permit an ordinary correction or consolidation successor to become effective while merely draft or proposed.

## 17.18 Amendment history

Accepted amendment records remain attached to the exact source representation they amended.

The destination substantive state includes the complete valid effect of source amendments through:

```text
source.observed_updated_at
```

but amendment records are not copied or retargeted.

Future amendments target the destination representation.

A logical-history view may display source and destination amendments in migration-chain order.

## 17.19 Exact attached references

Records targeting the source remain exact historical references.

Migration does not automatically move or rewrite:

- Statements of Disagreement;
- Dependencies;
- Work Relationships;
- Role basis references;
- Accounts;
- Observations;
- or other attached records.

They continue to resolve to the source contract version.

For current use against the destination, each referring record must be:

- migrated;
- replaced;
- or explicitly reviewed under its own contract.

Sharing a logical ID does not authorize changing only a referenced `contract_version` in place.

That remains a material reference change unless performed as part of the referring record's own valid migration.

## 17.20 Exact reference resolution

Canonical references resolve exactly by:

```text
module
class
work
record kind and ID, where applicable
contract_version
```

An exact reference to v1 always returns v1.

It never silently returns v2.

## 17.21 Current-representation discovery

Applications may provide an explicit derived operation such as:

```text
resolve_current_representation
```

That operation may return:

- the exact requested representation;
- migration status;
- migration chain;
- current representation;
- and any integrity condition.

This is navigation, not canonical reference substitution.

## 17.22 Versionless lookup prohibited

Internal and public operations must not identify migrated records by identifier alone when several contract representations may exist.

`contract_version` is mandatory for exact canonical resolution.

Versionless lookup would be ambiguous and could silently cross historical boundaries.

## 17.23 Record-family identity invariants

Migration preserves every record-family identity invariant.

### Event

Migration preserves:

- the same real-world occurrence;
- the same owning class and school year;
- the same summary meaning;
- the same location meaning;
- and the same instructional-context meaning.

### Event Participant

Migration preserves:

- the same Event;
- the same represented human;
- and the same subject identity or honest equivalent representation.

### Event Participant Role

Migration preserves:

- the same Event;
- the same Participant target;
- the same Role type;
- the same basis meaning;
- and the same substantive contextual meaning.

### Work Relationship

Migration preserves:

- the same source;
- the same target;
- the same relationship type;
- and the same directional meaning.

### Statement of Disagreement

Migration preserves:

- the same represented source;
- the same exact disputed target;
- the same positions;
- the same substantive statement;
- and the same withdrawal state where applicable.

### Dependency

Migration preserves:

- the same dependent;
- the same dependency target;
- the same strength;
- the same evaluation scope;
- and the same purpose.

Failure of any invariant makes the operation correction, consolidation, split, invalidation, or ownership correction rather than migration.

## 17.24 Identifier compatibility requirement

A destination contract must permit the source's stable canonical identifier.

A schema upgrade that rejects previously valid Portia identifiers cannot use ordinary migration unless the destination contract explicitly preserves those IDs.

Migration cannot assign a new ID merely to satisfy a newer identifier pattern.

Changing the ID changes logical identity.

Contract evolution should preserve accepted historical identifier syntax or introduce a future explicit identity-mapping architecture.

## 17.25 Migration reconciliation

Every successful migration uses all three canonical components:

1. destination representation with the same logical ID and a different contract version;
2. source lifecycle transition to `superseded`;
3. immutable `record_migration` certificate.

Where the destination contract has `supersedes`, it references:

```text
same logical ID
source contract_version
```

All components agree on:

- source exact representation;
- destination exact representation;
- semantic family;
- reason;
- effective time;
- and migration procedure.

## 17.26 Current-representation chain

For:

```text
evt_123 v1 -> evt_123 v2 -> evt_123 v3
```

the effective migration chain determines current representation.

Portia does not select v3 merely because `3` is the highest version token.

A higher version lacking complete reconciliation is not current.

## 17.27 Corrections after migration

A material correction after migration creates a new logical record identifier.

Example:

```text
evt_123 v1
    migration
evt_123 v2
    material correction
evt_456 v2
```

The corrected Event does not reuse `evt_123`.

This preserves:

```text
same logical ID across versions = migration only
new logical ID = semantic replacement
```

A later migration of the corrected Event may preserve:

```text
evt_456 v2 -> evt_456 v3
```

## 17.28 Interrupted migration

Staged destination content is not a second canonical current representation.

Issue #13 must keep incomplete destination representations:

- outside ordinary canonical resolution;
- explicitly marked through operation state;
- or quarantined from current-use indexes.

Only the completed coordinated operation makes the destination canonical at `effective_at`.

Portia does not resolve competing representations by:

- highest contract version;
- newest filesystem timestamp;
- destination file existence;
- or newest `created_at`.

## 17.29 Erroneous identity-preserving migration

When a supposed migration changed logical identity or semantic meaning:

- the migration certificate remains immutable;
- the operation is surfaced as an integrity failure;
- source lifecycle history may require correction;
- the erroneous destination may require invalidation or supersession;
- and corrected records use the appropriate semantic operation.

Portia does not relabel the operation as valid migration after the fact.

## 17.30 Structural validation

JSON Schema may validate:

- source and destination contract versions;
- stable identifier syntax;
- endpoint kinds;
- and local reference shapes.

JSON Schema cannot prove:

- logical-identity equality across endpoint structures;
- record-family invariant preservation;
- lifecycle-baseline equivalence;
- provenance reconciliation;
- or migration-chain uniqueness.

These remain application-level obligations.

## 17.31 Application validation

Application validation must confirm:

- source and destination have the same logical identity;
- contract versions differ;
- exact representations differ;
- work-kind and record-kind tokens remain stable;
- destination identifiers equal source identifiers;
- destination contract accepts preserved IDs;
- same owning class and work root;
- all record-family identity invariants;
- destination representation-local creation provenance;
- source historical provenance remains intact;
- lifecycle status is semantically preserved;
- lifecycle and amendment histories remain representation-local;
- destination state incorporates all valid source amendments through the observed revision;
- one effective current representation per logical ID;
- no migration branching or cycles;
- no silent reference rewriting;
- complete three-part reconciliation;
- and version-aware historical persistence.

## 17.32 Rejected alternatives

### New identifiers for every migration

Rejected because representation-only schema change would appear to create a different domain entity.

### In-place source overwrite

Rejected because historical exact representation resolution would be destroyed.

### Copied source creation provenance

Rejected because the destination representation was created digitally during migration.

### Replayed lifecycle history

Rejected because lifecycle events belong to the exact representation in which they occurred.

### Versionless current-record lookup

Rejected because it would silently cross historical representation boundaries.

---


# 18. Approved Decision 15: Incorrect Event Ownership and Work-Root Correction

## 18.1 Decision

Portia corrects incorrect Event ownership or child work-root placement through:

1. a new destination record under the correct ownership scope;
2. explicit cross-root successor lineage;
3. a source lifecycle transition to `superseded`;
4. and an immutable ownership-correction certificate.

Portia does not:

- mutate source ownership fields in place;
- physically move or rename the source work directory;
- preserve source identifiers under a different ownership scope;
- rewrite incoming references;
- or automatically copy the complete source graph.

Each source record remains exactly resolvable under the scope where it was originally persisted.

## 18.2 Canonical ownership-correction record

The canonical record type is:

```text
ownership_correction
```

Identifiers use:

```text
owc_<opaque-id>
```

Canonical storage is:

```text
classes/<destination_class_id>/modules/portia/
  work/<destination_work_id>/
    records/
      ownership_correction/
        <correction_id>.json
```

The certificate is destination-owned because it documents how the destination representation originated.

## 18.3 Semantic unit

One ownership-correction record means:

> One exact Portia work or child record was recreated under its correct ownership scope and replaced one exact incorrectly owned predecessor.

One certificate contains:

- one source;
- one destination;
- one correction kind;
- one reason;
- and one effective time.

It does not cover several child records.

A complete Event-root correction therefore creates:

- one Event-level certificate;
- one certificate for each relocated child record;
- and one coordinated Issue #13 operation encompassing the complete graph.

## 18.4 Required envelope

An ownership-correction version-1 record contains:

```text
schema_version
record_type
module_id
class_id
work_id
correction_id
correction_kind
source
destination
parent_correction, optional
reason
effective_at
creation_source
created_at
created_by
```

Constants are:

```text
schema_version = "1"
record_type = "ownership_correction"
module_id = "portia"
```

The record does not contain:

```text
status
updated_at
updated_by
operation_id
authorized_by
```

The certificate is immutable and represents only an accepted correction.

Attempt progress, partial persistence, rollback, and recovery belong to Issue #13.

## 18.5 Correction kinds

`correction_kind` is:

```text
event_class_ownership
child_work_root
```

### `event_class_ownership`

The Event was created beneath the wrong Core class.

The destination is a new Event under the correct class and a new Portia work root.

### `child_work_root`

A child record was created beneath the wrong Event work root.

The destination is a new record of the same semantic family beneath the correct Event root.

This may occur:

- as part of an Event class-ownership correction;
- or independently when only one child record was misfiled.

## 18.6 Source and destination endpoint union

`source` and `destination` use the same closed endpoint union.

### Event-work endpoint

```json
{
  "kind": "event_work",
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_wrong",
    "work_kind": "event",
    "contract_version": "2"
  },
  "observed_updated_at": "2026-08-04T07:30:00-04:00"
}
```

### Child-record endpoint

```json
{
  "kind": "work_record",
  "work_record_ref": {
    "work_ref": {
      "module_id": "portia",
      "class_id": "eng10_p2_2026",
      "work_id": "evt_wrong",
      "work_kind": "event",
      "contract_version": "2"
    },
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ept_wrong",
      "contract_version": "2"
    }
  },
  "observed_updated_at": "2026-08-04T07:30:00-04:00"
}
```

Requirements are:

- source and destination use the same endpoint kind;
- both resolve exactly;
- both belong to the same semantic record family;
- their ownership scopes differ;
- source and destination exact identities differ;
- and each observed timestamp binds the certificate to the exact revision reviewed.

## 18.7 New canonical identifiers

Ownership correction changes logical ownership identity.

The destination therefore receives new identifiers.

### Event correction

A corrected Event receives:

```text
new class_id
new work_id
```

It does not reuse the source `work_id` under the destination class.

Example:

```text
class_A / evt_old
    ->
class_B / evt_new
```

### Child correction

A relocated child receives:

```text
destination work_id
new record_id
```

Example:

```text
class_A / evt_old / ept_old
    ->
class_B / evt_new / ept_new
```

Fresh identifiers preserve the distinction:

```text
same logical ID across versions = migration
new logical ID = ownership or semantic replacement
```

Contract versions may remain the same or change independently.

A version change is not what makes the operation an ownership correction.

## 18.8 Parent correction

A child certificate created as part of an Event-root correction contains:

```text
parent_correction
```

This is a same-destination-work `local_record_ref` to the Event-level ownership-correction certificate.

Application validation requires:

- the child source belongs to the parent certificate's source Event;
- the child destination belongs to the parent certificate's destination Event;
- and the parent correction became effective in the same coordinated operation.

A standalone child correction omits `parent_correction`.

## 18.9 Reason vocabulary

`reason` is a closed object containing:

```text
code
detail, optional
```

Initial codes are:

```text
wrong_class
wrong_event_root
incorrect_initial_routing
other
```

Meanings are:

- `wrong_class`: the Event was owned by the wrong Core class;
- `wrong_event_root`: the child record belonged to another Event;
- `incorrect_initial_routing`: ingestion or entry selected the wrong canonical root;
- `other`: another ownership-only correction.

`detail` is required for `other`.

Reason language must remain neutral.

It must not imply blame, fault, misconduct, or credibility.

## 18.10 Event-root replacement reconciliation

A corrected Event uses three canonical components:

1. the destination Event's `supersedes` reference to the exact source Event;
2. the source Event's lifecycle transition to `superseded`;
3. the immutable ownership-correction certificate.

The source transition uses:

```text
reason.category = correction
reason.code = ownership_corrected
```

All three components agree on:

- source Event;
- destination Event;
- reason;
- effective time;
- and correction kind.

## 18.11 Child-record replacement reconciliation

Each relocated child uses the analogous three components:

1. destination child successor reference to the exact source child;
2. source child lifecycle transition to `superseded`;
3. child ownership-correction certificate.

The source transition uses:

```text
reason.category = correction
reason.code = work_root_corrected
```

## 18.12 Cross-work successor requirement

A child contract participating in ownership correction must identify its predecessor through a complete:

```text
portia_work_record_ref
```

A same-work `local_record_ref` is insufficient because it cannot identify a predecessor under another Event root.

Event Participant v2 currently restricts predecessor links to the same Event work scope.

Cross-root correction of a Participant therefore requires a later Participant contract version whose successor entries support complete cross-work predecessor references.

The same rule applies to every family whose current successor contract is same-work only.

Portia does not introduce a second competing replacement authority merely to avoid versioning an affected domain contract.

## 18.13 No physical move

Ownership correction creates new destination records.

It does not:

- rename the source directory;
- move source files;
- edit source ownership fields;
- or rewrite source paths.

The complete source graph remains available under its original class and work root.

That graph records what Portia actually persisted before correction.

## 18.14 Destination provenance

Destination records use representation-local provenance:

```text
creation_source = digital_entry
created_at = correction effective_at
created_by = correction created_by
updated_at = created_at
updated_by = created_by
```

They do not inherit or backdate source creation provenance.

For example, a paper-captured source remains paper-captured, while its digitally recreated destination uses `digital_entry`.

A derived ownership-lineage view may expose the original provenance chain.

## 18.15 Destination lifecycle baseline

The destination begins in the lifecycle state justified by current review.

It does not automatically inherit source status.

Representative outcomes include:

- an active incorrectly owned Event producing an active destination;
- a closed Event producing a closed destination;
- an invalidated historical Event producing an invalidated destination;
- a proposed child producing a proposed destination while correction remains preparatory.

A destination does not become active or closed merely because the source had that status.

It must independently satisfy:

- schema validity;
- record-family application rules;
- dependency gates;
- authorization;
- and destination-scope identity validation.

The source transitions to `superseded` only when the destination becomes replacement-eligible and the complete correction reconciles.

## 18.16 Pre-acceptance routing mistakes

When a routing mistake is discovered before the source became meaningfully accepted, referenced, or populated, the preferred workflow is:

1. cancel or invalidate the mistaken draft or proposal;
2. create the correct destination normally.

An ownership-correction certificate is required when explicit replacement lineage matters, including when the source:

- was active or closed;
- has child records;
- has incoming references;
- has amendments or lifecycle history;
- or was exposed to a user or downstream consumer.

## 18.17 Complete Event-graph review

Correcting the Event root does not automatically copy every source child.

Every source child receives a record-family-specific disposition.

### Relocated successor

The child remains substantively applicable to the corrected Event.

Portia creates:

- a destination successor;
- a child ownership-correction certificate;
- and a source transition to `superseded`.

### Explicit invalidation

The child does not remain valid under the corrected Event and has no replacement.

The source child transitions to `invalidated` using an appropriate record-validity or dependency reason.

### Historical attachment retained at source

Some records describe or audit the exact source representation and remain at the source.

Examples include:

- lifecycle transitions;
- lifecycle-history corrections;
- amendments;
- migration certificates;
- ownership-correction certificates;
- Issue #13 operation records;
- and Statements of Disagreement targeting the exact source record.

These records are not copied merely because the Event was corrected.

### Review required

A current-use child cannot yet be safely relocated or invalidated.

The root correction is not fully reconciled while an unresolved active child remains dependent on the incorrectly owned Event.

## 18.18 No automatic cascade

Superseding the Event does not itself rewrite child statuses.

Instead, the coordinated correction explicitly resolves every lifecycle-bearing Event-owned child requiring current-use treatment.

This preserves the accepted rule against automatic dependency cascades.

A root correction is incomplete when active Event-owned children remain without an accepted disposition.

## 18.19 Roster-scoped Participant identity

A roster-student reference is authoritative only within its roster scope.

Moving an Event to another class may therefore require a different destination `roster_student_ref`.

Portia treats this as ownership-scope adaptation only when authorized review establishes that both roster references identify the same human.

It does not infer identity from:

- matching display names;
- matching initials;
- matching local student IDs;
- or similar snapshots.

The destination Participant uses:

- the verified destination roster reference;
- a display snapshot appropriate to destination creation;
- and a fresh Participant identifier.

When identity equivalence cannot be established, the Participant cannot be automatically relocated.

Changing to an Actor, descriptive person, or another subject branch is a separate identity correction unless record-family policy explicitly establishes semantic equivalence.

## 18.20 Child-reference rewriting

Internal references among relocated child records identify destination counterparts explicitly.

For example:

- destination Roles target destination Participants;
- destination Dependencies identify destination dependents and targets where reviewed;
- destination Relationships identify destination endpoints.

Portia does not preserve a source local reference and reinterpret it under the destination root.

The complete destination graph must validate before effectiveness.

## 18.21 Statements of Disagreement

A Statement of Disagreement remains attached to its exact original target.

It does not automatically transfer to:

- the corrected Event;
- a relocated Participant;
- a relocated Role;
- or another destination record.

The represented source may also disagree with the destination, but that requires a separate Statement of Disagreement targeting the destination.

Portia does not attribute a broader disagreement than the person expressed.

## 18.22 Dependencies

Dependencies remain exact.

A Dependency targeting or owned by a source record does not silently retarget to the destination.

Review may conclude that:

- the source dependency remains historically sufficient;
- a successor Dependency should identify the destination;
- the dependent itself requires replacement;
- or the Dependency should be invalidated.

The accepted dependency rules continue to apply.

## 18.23 Work Relationships

A Work Relationship is source-owned.

When its source Event is corrected to another root:

- the old Relationship remains under the old source root;
- a continuing Relationship requires a new successor under the destination root;
- and the old Relationship transitions to `superseded`.

A Relationship from another work targeting the old Event remains an exact reference.

It is not rewritten automatically.

Review may create a successor Relationship targeting the corrected Event when semantically appropriate.

## 18.24 Incoming cross-work references

References from outside the source root continue to identify the exact source record.

They never silently return the destination.

Applications may derive authorized navigation information such as:

```text
ownership_correction_available
corrected_destination
review_required
```

Changing an incoming current-use reference requires an explicit correction or successor in the referring record's own scope.

## 18.25 Cross-class authorization boundary

An Event class-ownership correction requires authority to:

- read the complete source graph;
- create and validate the destination graph;
- transition source records;
- and inspect affected incoming references.

The initial teacher-local model supports correction only when both classes belong to the same teacher workspace.

Cross-teacher relocation is unsupported in version 1.

Portia does not copy records into another teacher's ownership scope through this contract.

Insufficient visibility produces `review_required` or blocks correction.

It is not interpreted as proof that no affected records exist.

## 18.26 Timing

`effective_at` means:

> The time at which the destination became the accepted corrected owner or work-root representation.

Requirements are:

- source and destination existed by `effective_at`;
- destination was independently valid by `effective_at`;
- source observed revision still matched;
- destination observed revision still matched;
- successor edges and source transitions use the same effective time;
- every certificate in one Event-root operation uses one consistent effective time;
- and no certificate is future-effective.

Issue #13 defines atomicity and recovery.

## 18.27 One-to-one topology

Each ownership-correction certificate maps:

```text
one source -> one destination
```

The contract does not perform:

- consolidation;
- Event split;
- many-to-many movement;
- or simultaneous semantic correction.

When source records contain duplicates or conflated occurrences, those conditions use their existing explicit operations.

Ownership correction must not conceal them.

## 18.28 Immutability

An accepted ownership-correction certificate is immutable.

It is not amended, invalidated, or deleted.

Its source and destination mapping never changes.

A later-discovered routing error creates another explicit correction from the current destination.

Example:

```text
class_A / evt_A
    ->
class_B / evt_B
    ->
class_C / evt_C
```

The first correction remains intact.

## 18.29 Erroneous ownership correction

When an ownership correction was accepted in error:

- the certificate remains historically visible;
- incorrect source supersession may require lifecycle-history correction;
- the erroneous destination may require invalidation or supersession;
- affected children require explicit repair;
- and Issue #13 recovery records preserve the failed operation.

Portia does not physically move the destination back or silently erase correction lineage.

## 18.30 Exact resolution and derived navigation

Exact references continue to resolve the exact source or destination identified.

A resolver does not silently follow ownership correction.

Applications may derive:

```text
source -> corrected destination
destination -> ownership source
event-root correction graph
child relocation mappings
unresolved source children
affected incoming references
```

These indexes are rebuildable.

They are not canonical authority.

## 18.31 Structural validation

JSON Schema will validate:

- the exact certificate envelope;
- `owc_` identifier syntax;
- correction kind;
- closed work and work-record endpoint forms;
- optional parent-correction reference;
- reason structure;
- digital-only creation provenance;
- timestamps;
- and attribution.

Schema validation cannot establish graph completeness or semantic ownership correctness.

## 18.32 Application validation

Application validation must confirm:

- destination-root storage agreement;
- exact source and destination resolution;
- differing ownership scope;
- same semantic record family;
- fresh destination identifiers;
- compatible contract versions;
- independently valid destination content;
- complete cross-root successor references;
- source lifecycle eligibility;
- reason and timing reconciliation;
- parent and child correction consistency;
- verified roster identity mapping;
- complete destination internal references;
- explicit disposition of every affected current-use child;
- no automatic copying of audit or disagreement records;
- no silent dependency, relationship, or incoming-reference retargeting;
- one-to-one correction topology;
- same-workspace authorization;
- no cycles;
- and atomic or recoverable persistence.

## 18.33 Rejected alternatives

### In-place ownership mutation

Rejected because it would rewrite canonical identity and historical ownership.

### Physical directory movement

Rejected because record envelopes and references would continue to identify the old scope.

### Ordinary supersession without a certificate

Rejected because it would not certify why ownership changed or map relocated child records.

### Automatic graph copy

Rejected because every child and incoming relationship requires record-specific review.

### Reused destination identifiers

Rejected because ownership scope is part of logical identity.

---


# 19. Approved Decision 16: Exceptional Removal Boundaries

## 19.1 Decision

Ordinary Portia workflows never physically remove accepted canonical records.

Ordinary actions remain:

```text
cancel
withdraw
invalidate
supersede
correct
consolidate
migrate
```

Exceptional removal is a separate governed administrative operation.

It is not:

- ordinary correction;
- a teacher-facing cleanup action;
- a lifecycle transition;
- a substitute for invalidation;
- a substitute for withdrawal;
- or a way to conceal disputed, embarrassing, obsolete, or incorrect information.

When accepted canonical payload content must be removed under a narrow authorized basis, Portia destroys or quarantines that payload while retaining a minimal immutable exceptional-removal certificate.

## 19.2 Removal domains

Portia distinguishes:

```text
noncanonical_artifact_cleanup
accepted_canonical_content_removal
```

### Noncanonical artifact cleanup

Content may be deleted without a canonical removal certificate when it never became an accepted canonical record.

Examples include:

- temporary files;
- staging files;
- rejected writes;
- incomplete serialization;
- failed creation before canonical acceptance;
- duplicate bytes from an interrupted write;
- derived indexes;
- disposable test-workspace data;
- repository fixtures;
- or a file that never passed structural and application acceptance.

Issue #13 defines the exact acceptance boundary.

Deleting such material is storage cleanup, not record removal.

### Accepted canonical content removal

Once a record has been accepted canonically, even in `draft` or `proposed` state, its payload may be removed only through the exceptional-removal contract.

## 19.3 Canonical exceptional-removal record

The canonical record type is:

```text
exceptional_removal
```

Identifiers use:

```text
rmv_<opaque-id>
```

Canonical storage is:

```text
classes/<class_id>/modules/portia/
  removals/
    <removal_id>.json
```

The certificate is stored at class-module scope rather than beneath the target work.

This keeps the surviving evidence resolvable even when an entire Event work root is removed.

## 19.4 Semantic unit

One exceptional-removal record means:

> One exact accepted Portia representation had its canonical payload intentionally removed under one authorized exceptional basis.

One certificate identifies exactly one:

- work representation;
- or work-record representation.

A certificate never implies that an entire child graph was also removed.

## 19.5 Required envelope

An exceptional-removal version-1 record contains:

```text
schema_version
record_type
module_id
class_id
removal_id
target
parent_removal, optional
reason
authorization
content_evidence
lifecycle_snapshot, optional
effective_at
creation_source
created_at
created_by
```

Constants are:

```text
schema_version = "1"
record_type = "exceptional_removal"
module_id = "portia"
```

The record does not contain:

```text
status
updated_at
updated_by
supersedes
operation_id
replacement
```

The certificate is immutable and represents only an accepted removal.

Attempt state, partial destruction, retry, rollback, and media-level recovery belong to Issue #13 or an externally governed retention process.

## 19.6 Target branches

`target` uses one of two exact branches.

### Work representation

```json
{
  "kind": "work",
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "2"
  }
}
```

### Work-record representation

```json
{
  "kind": "work_record",
  "work_record_ref": {
    "work_ref": {
      "module_id": "portia",
      "class_id": "eng10_p2_2026",
      "work_id": "evt_example",
      "work_kind": "event",
      "contract_version": "2"
    },
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ept_example",
      "contract_version": "2"
    }
  }
}
```

Requirements are:

- `contract_version` is non-null;
- the target resolved exactly before removal;
- certificate `class_id` matches the target;
- and at most one accepted removal certificate exists for one exact representation.

Version 1 does not use this contract for:

- Actor-directory entries;
- entire Core classes;
- entire teacher workspaces;
- exceptional-removal certificates;
- or external-module records.

Those require separate governed contracts.

## 19.7 Parent removal

When a work root and child records are removed together, each child certificate contains:

```text
parent_removal
```

`parent_removal` identifies the `rmv_` certificate for the removed work representation.

Application validation confirms:

- the child belonged to the parent target work;
- both removals share one coordinated operation;
- and effective times are consistent.

A work-root certificate does not implicitly certify destruction of child records.

Every removed child requires its own certificate.

## 19.8 Permitted reason categories

`reason` is a closed object containing:

```text
category
code
detail, optional
```

Initial categories are:

```text
legal_requirement
privacy_requirement
security_containment
administrative_test_data
unrecoverable_corruption
other
```

### `legal_requirement`

A governed external decision requires destruction.

Representative code:

```text
required_destruction
```

Portia records the referenced decision supplied by the governing workflow; it does not determine legal sufficiency.

### `privacy_requirement`

Content must no longer be retained because of an accepted privacy or data-protection decision.

Representative codes include:

```text
sensitive_data_erasure
prohibited_data_retention
unlawful_collection
```

Reason detail must not repeat sensitive content.

### `security_containment`

Continued storage presents a concrete security risk.

Representative codes include:

```text
credential_exposure
secret_exposure
malicious_payload
unsafe_embedded_content
```

Credential rotation, malware handling, incident response, and external notifications remain outside Portia.

### `administrative_test_data`

Canonical content was definitively established as synthetic test data accidentally accepted into a nondisposable workspace.

Representative code:

```text
accepted_test_data
```

Similarity to test data is insufficient.

### `unrecoverable_corruption`

An accepted canonical representation cannot be recovered accurately.

Representative code:

```text
unrecoverable_payload
```

This category is used only after storage recovery cannot restore the exact accepted content.

### `other`

Another exceptional governed basis not represented above.

`detail` and an external decision reference are required.

## 19.9 Prohibited removal reasons

Exceptional removal is not permitted merely because a record is:

- incorrect;
- duplicated;
- disputed;
- withdrawn;
- invalidated;
- superseded;
- embarrassing;
- inconvenient;
- old;
- closed;
- no longer needed;
- or associated with the wrong class or Event root.

Those conditions use accepted lifecycle, correction, consolidation, migration, or ownership-correction contracts.

A request phrased as “delete this mistake” does not establish an exceptional-removal basis.

## 19.10 Authorization

`authorization` is a closed object containing:

```text
decision_reference
authorized_by
```

`decision_reference` is an opaque nonempty reference to the externally governed decision authorizing removal.

`authorized_by` uses the local-operator attribution branch.

A deterministic system process may execute and persist the operation through `created_by`, but it may not be the sole recorded authorizer.

The certificate does not itself prove legal or institutional authority.

Application validation establishes that the identified operator holds the configured exceptional-removal capability.

Exceptional removal is unavailable through ordinary teacher record-editing workflows.

## 19.11 External governance boundary

Portia does not decide:

- legal retention periods;
- whether a legal hold exists;
- whether a privacy request must be granted;
- whether regulatory destruction is complete;
- or which backups an institution must purge.

The governing administrative process supplies that decision.

When authorization or legal-hold status is unknown, removal is blocked rather than presumed permissible.

## 19.12 Content evidence

The certificate preserves evidence of which exact payload was removed without retaining the payload itself.

`content_evidence` uses one of two branches.

### Salted content digest

```json
{
  "kind": "salted_sha256",
  "salt": "<base64 random salt>",
  "digest": "<64 lowercase hexadecimal characters>",
  "byte_length": 2847
}
```

The digest is calculated over the exact canonical bytes removed.

A random salt reduces precomputed content guessing.

### Evidence unavailable

```json
{
  "kind": "unavailable",
  "reason": "unrecoverable_corruption"
}
```

This branch is permitted only when exact bytes were already unavailable or unsafe to process.

The certificate must not retain summaries, excerpts, names, statement text, credentials, secrets, or other removed substantive content.

## 19.13 Lifecycle snapshot

For a lifecycle-bearing target, the certificate records a minimal snapshot:

```text
status
selected_transition, optional
```

`status` records semantic lifecycle state immediately before removal.

`selected_transition` identifies the selected lifecycle head when one existed.

The snapshot distinguishes a valid but removed record from an invalidated, withdrawn, or superseded representation.

It is evidence only and does not create or change lifecycle status.

Immutable audit records without lifecycle status omit `lifecycle_snapshot`.

## 19.14 Removal is not invalidation

Exceptional removal does not mean the removed assertion was false or invalid.

Portia does not generate an `invalidated` transition merely because payload content was removed.

When the record independently requires invalidation or supersession, that semantic operation remains separate and explicit.

## 19.15 Availability override

A removal certificate establishes the availability condition:

```text
removed
```

`removed` is not a domain-record lifecycle status.

It is a derived canonical-resolution result.

For current-use evaluation, content availability overrides persisted semantic status.

A record whose last status was `active` but whose payload was removed is not usable merely because its historical status was active.

## 19.16 Exact resolution

An exact reference to removed content does not return `not_found`.

It returns a minimal removal result containing:

```text
resolution = removed
target
removal_id
effective_at
reason.category
lifecycle_snapshot, when present
```

The resolver does not fabricate a record body, silently follow a successor, return another contract version, search another root, or treat removal as accidental absence.

Normal content views, search indexes, and exports do not expose the removed payload.

Authorized audit views may expose the minimal certificate.

## 19.17 One certificate per exact representation

Removal applies to exact representation identity.

For migrated lineage:

```text
evt_123 v1 -> evt_123 v2
```

removing v1 does not remove v2.

Each removed representation requires its own certificate.

A certificate cannot identify a versionless logical record.


## 19.18 Work-root removal

Removing an Event work representation does not automatically remove:

- Event Participants;
- Event Participant Roles;
- Work Relationships;
- Statements of Disagreement;
- Dependencies;
- lifecycle transitions;
- amendments;
- migration certificates;
- ownership-correction certificates;
- or Issue #13 operation records.

Every child receives an explicit disposition:

```text
retained
exceptionally_removed
superseded
invalidated
review_required
```

A coordinated whole-graph destruction operation creates one removal certificate for every removed exact representation.

Partial completion is an integrity failure requiring Issue #13 recovery.

## 19.19 Audit-record treatment

Audit records are preserved unless the governed removal basis explicitly requires their destruction.

When substantive payload can be removed while audit records remain safely non-sensitive, Portia retains lifecycle transitions, amendment metadata, migration certificates, ownership-correction certificates, and operation evidence.

Those records continue to reference a target resolving as `removed`.

When an audit record itself contains prohibited content, it requires its own exceptional-removal certificate.

Exceptional-removal certificates themselves cannot be targeted by version-1 exceptional removal.

Their intentionally minimal design is the surviving evidence that removal occurred.

A requirement prohibiting retention of even opaque identity and removal metadata requires a separately governed class- or workspace-destruction process outside this contract.

## 19.20 Incoming references

Incoming canonical references remain unchanged.

They continue to identify the exact removed target.

Applications may derive:

```text
target_removed
review_required
replacement_available
```

information where authorized.

They do not silently substitute a successor, migrated version, consolidated record, or ownership-corrected destination.

Changing a referring record requires its own explicit correction or successor operation.

## 19.21 Dependency effects

A dependency targeting removed content is not treated as merely missing.

The dependency evaluator knows intentional removal occurred.

### Required dependency

A required dependency becomes:

```text
unsatisfied
```

unless consuming record-family policy explicitly permits tombstone-only historical sufficiency.

When policy cannot safely decide, it becomes:

```text
review_required
```

rather than silently satisfied.

### Advisory dependency

An advisory dependency creates a derived attention indicator and remains subject to record-family review policy.

### No automatic cascade

Removal does not automatically invalidate or supersede dependent records.

Portia:

1. removes the target from current use;
2. identifies affected dependents;
3. blocks gated operations where required;
4. places dependents in review;
5. requires explicit outcomes.

## 19.22 Derived data

After accepted removal, Portia-managed derived stores must remove payload-bearing material, including:

- search text;
- previews;
- cached summaries;
- duplicate-detection fingerprints derived from substantive fields;
- exported local projections under Portia's control;
- and denormalized display content.

Derived stores may retain only minimal removal state needed for exact resolution and review.

Rebuilds reproduce the removed state from the certificate rather than restoring payload content.

The certificate does not claim independently distributed exports or external backups were destroyed.

Those remain externally governed.

## 19.23 Corruption boundary

### Never-valid file

A file that never became a valid accepted canonical record may be deleted as a noncanonical artifact.

No removal certificate is created.

### Recoverable canonical corruption

When an accepted record is damaged but exact accepted bytes can be restored from an operation journal, verified duplicate, backup, or another authoritative storage copy, Portia restores the exact representation.

This is storage recovery, not exceptional removal.

### Unrecoverable canonical corruption

When accepted content cannot be recovered:

- create an exceptional-removal certificate;
- use `unrecoverable_corruption`;
- preserve available minimal identity and lifecycle evidence;
- mark exact resolution as `removed`;
- and review dependents.

Portia does not invent a replacement body.

## 19.24 Test-data boundary

Synthetic repository fixtures, disposable test workspaces, and pre-acceptance test files may be deleted normally.

Canonical test data accidentally accepted into a real workspace requires:

- positive confirmation that it is synthetic;
- exceptional administrative authorization;
- one certificate per removed representation;
- dependency and incoming-reference review;
- and no assumption that unlikely data is merely test data.

Genuine records must not be removed under the test-data category.

## 19.25 Emergency security containment

Security containment may require payload quarantine or destruction before the complete certificate operation finishes.

Issue #13 may permit the emergency sequence:

1. remove the payload from ordinary resolution;
2. quarantine surviving bytes;
3. record pending operation state;
4. validate authorization and affected graph;
5. persist the removal certificate;
6. purge Portia-managed derived content;
7. complete recovery and review actions.

Until completion, the target is unavailable and integrity review is required.

Emergency containment does not authorize silent deletion without eventual durable evidence.

## 19.26 Timing

`effective_at` means:

> The time at which the target payload ceased to be available through ordinary canonical resolution.

Requirements are:

- `effective_at <= created_at`;
- no future-effective removal;
- target exact identity was established before effectiveness;
- content evidence corresponds to the removed revision;
- authorization predates effectiveness or, for emergency containment, is reconciled immediately afterward;
- and all certificates in one coordinated work-root removal use compatible effective times.

Filesystem modification time is not removal authority.

## 19.27 No ordinary restoration

An accepted removal certificate is irreversible at the logical-resolution level.

The removed exact identity remains:

```text
removed
```

even when bytes later become available from a backup.

Portia does not silently restore the original file under the same exact identity.

When recovered content must become usable again, a separately governed recovery or successor process must:

- preserve the removal certificate;
- create a new canonical representation or record identity;
- establish why reuse is permitted;
- and reconcile affected references.

That recovery contract is not defined in version 1.

## 19.28 Erroneous exceptional removal

An accepted removal certificate is immutable.

When removal was unauthorized or mistaken:

- the certificate remains visible;
- the exact target remains marked `removed`;
- the incident becomes an integrity finding;
- surviving or recovered content is quarantined;
- affected dependents are reviewed;
- and restoration uses a future explicit recovery contract.

Portia does not erase the certificate or pretend removal never occurred.

## 19.29 Derived indexes

Applications may derive:

```text
exact target -> removal certificate
work root -> removed child representations
removed target -> incoming references
removed target -> affected dependencies
class -> exceptional-removal history
```

These indexes are rebuildable and are not canonical authority.

## 19.30 Structural validation

JSON Schema will validate:

- exact certificate envelope;
- constants;
- `rmv_` identifier syntax;
- exact work and work-record target branches;
- optional parent-removal identity;
- reason structure;
- authorization structure;
- content-evidence branch;
- optional lifecycle snapshot;
- digital-only creation provenance;
- timestamps;
- and attribution.

JSON Schema cannot establish authorization, legal sufficiency, canonical acceptance, or successful payload destruction.

## 19.31 Application validation

Application validation must confirm:

- the target was an accepted canonical representation;
- the target resolved exactly before removal;
- target and certificate class scope agree;
- the reason falls within the narrow exceptional boundary;
- ordinary lifecycle or correction mechanisms are insufficient;
- authorization is valid under configured policy;
- no unknown legal hold or governance block exists;
- content evidence identifies the removed revision;
- the certificate contains no removed substantive content;
- one certificate exists per exact representation;
- parent and child removal mappings are complete;
- derived payload-bearing material is purged;
- incoming references remain exact;
- dependencies enter explicit review;
- no silent successor following occurs;
- removal certificates are not recursively removed;
- and the physical operation is atomic or recoverable.

## 19.32 Rejected alternatives

### Absolute prohibition on physical removal

Rejected because Portia must support narrow security, privacy, legal, test-data, and corruption cases.

### `deleted` lifecycle status

Rejected because removal changes availability rather than semantic validity.

### Privileged deletion without surviving evidence

Rejected because exact references and dependencies must distinguish intentional removal from accidental absence.

### Retained substantive tombstone content

Rejected because the removal basis may prohibit continued retention of the payload itself.

### Automatic child-graph destruction

Rejected because each exact representation requires explicit disposition and evidence.

---

# 20. Approved Decision 17: Integrity-Finding Vocabulary

## 20.1 Decision

Portia integrity findings are structured, deterministic, rebuildable diagnostics. They are not canonical domain records.

Version 1 does not introduce:

```text
record_type = integrity_finding
```

A finding has no canonical record identifier or lifecycle. It is not amended, superseded, migrated, or stored as the sole evidence of a defect. Canonical records and accepted operation evidence remain authoritative. Repairs create the applicable canonical transition, correction, certificate, successor, or recovery evidence.

## 20.2 Core distinctions

Portia distinguishes:

```text
domain_condition
review_condition
integrity_finding
operation_failure
```

A domain condition is a valid state represented by a domain contract, such as a closed Event, withdrawn disagreement, superseded Dependency target, or exceptionally removed record.

A review condition is a valid but unresolved situation requiring human review. It may exist without an invariant violation.

An integrity finding means that a required invariant is confirmed to be violated or cannot be safely evaluated.

An operation failure means a coordinated write did not complete. Issue #13 represents operation progress and recovery. Partial canonical state may also generate an integrity finding.

## 20.3 Authority and reproducibility

Findings are reproducible from:

- canonical domain records;
- lifecycle transitions and history corrections;
- amendments;
- successor edges;
- migration, ownership-correction, and exceptional-removal certificates;
- producer contracts;
- configured policy;
- and Issue #13 operation state.

A public projection schema may standardize finding output without making findings canonical.

## 20.4 Finding boundary

Portia emits an integrity finding when canonical records contradict one another, canonical structure violates an accepted contract, a required invariant is violated, an operation leaves unresolved partial canonical state, current use continues despite a required block, exact resolution is ambiguous, or validation cannot safely conclude because required visibility or compatibility is unavailable.

Portia does not emit a finding merely because a record is invalidated, withdrawn, cancelled, superseded, legitimately awaiting review, detected as a duplicate candidate, disputed, validly removed, draft, or proposed.

## 20.5 Derived finding envelope

A finding projection contains:

```text
finding_key
evaluation_key
rule_id
rule_version
category
code
severity
assessment
effects
scope
primary_target
related_targets
evidence
observed_at
```

This is a derived-projection envelope, not a canonical record envelope.

## 20.6 Deterministic keys

`finding_key` is deterministic from stable `rule_id`, normalized primary target, normalized related exact identities, and an invariant-specific discriminator. The same underlying condition produces the same key across scans. Portia does not assign random finding identifiers.

`evaluation_key` identifies one evaluation under the rule version, observed record revisions, contract versions, and policy version. A rule or record revision changes the evaluation key while the stable finding key may remain the same.

## 20.7 Rule identity

`rule_id` uses a stable namespaced form, such as:

```text
portia.lifecycle.status_history_mismatch
portia.migration.multiple_current_representations
portia.removal.payload_retained
```

`rule_version` is a required nonempty token.

Changing wording does not require a new rule version. Changing detection semantics, affected-target calculation, default severity, or blocking effects does.

## 20.8 Category vocabulary

The initial closed categories are:

```text
structure
identity_scope
reference
lifecycle
replacement
dependency
migration
ownership_correction
removal
chronology_provenance
uniqueness_graph
authorization_compatibility
persistence_recovery
derived_state
```

### Structure

Initial codes:

```text
schema_invalid
unsupported_contract_version
canonical_path_mismatch
envelope_scope_mismatch
identifier_collision
```

### Identity and scope

Initial codes:

```text
logical_identity_conflict
ownership_scope_mismatch
roster_identity_unresolved
record_family_mismatch
```

`roster_identity_unresolved` is ordinarily indeterminate rather than a confirmed mismatch.

### Reference

Initial codes:

```text
exact_target_missing
reference_kind_mismatch
reference_scope_mismatch
silent_retarget_detected
removed_target_in_current_use
```

A validly removed historical target is not itself a finding. `removed_target_in_current_use` applies only when policy still treats it as usable.

### Lifecycle

Initial codes:

```text
status_history_mismatch
illegal_transition
history_chain_broken
selected_history_ambiguous
history_correction_invalid
terminal_state_violation
```

### Replacement

Initial codes:

```text
supersession_reconciliation_broken
replacement_cycle
unsupported_replacement_topology
multiple_current_representations
replacement_frontier_ambiguous
partial_consolidation
partial_event_split
```

### Dependency

Initial codes:

```text
dependency_cycle
duplicate_intrinsic_dependency
dependency_declaration_conflict
required_dependency_gate_violation
dependency_target_resolution_ambiguous
```

An unsatisfied required Dependency becomes a finding only when an affected operation or current-use decision violates the required gate.

### Migration

Initial codes:

```text
migration_reconciliation_broken
migration_identity_mismatch
migration_semantic_mismatch
migration_branch
migration_cycle
migration_lifecycle_mismatch
```

### Ownership correction

Initial codes:

```text
ownership_reconciliation_broken
unresolved_source_child
destination_graph_invalid
cross_workspace_ownership_correction
roster_mapping_unverified
```

### Removal

Initial codes:

```text
removal_reconciliation_broken
payload_present_after_removal
removal_certificate_without_target_history
derived_payload_retained_after_removal
duplicate_removal_certificate
removed_target_resolved_as_not_found
```

Payload retained after removal may require immediate containment.

### Chronology and provenance

Initial codes:

```text
timestamp_order_invalid
observed_revision_mismatch
creation_provenance_inconsistent
attribution_invalid
effective_time_mismatch
```

### Uniqueness and graph

Initial codes:

```text
active_uniqueness_violation
graph_cycle
duplicate_current_identity
conflicting_exact_identity
```

A possible duplicate is not a finding; a confirmed uniqueness violation is.

### Authorization and compatibility

Initial codes:

```text
authorization_limited_resolution
producer_contract_unavailable
unsupported_cross_module_semantics
policy_version_unavailable
```

These are normally indeterminate rather than confirmed defects.

### Persistence and recovery

Initial codes:

```text
operation_incomplete
canonical_write_partial
orphaned_canonical_artifact
content_digest_mismatch
recovery_required
```

A disposable staging artifact that never became canonical is cleanup, not necessarily a finding.

### Derived state

Initial codes:

```text
derived_index_drift
projection_stale
derived_reverse_link_mismatch
derived_payload_policy_violation
```

These normally permit projection rebuilding unless sensitive removed content is exposed.

## 20.9 Assessment

`assessment` separates confirmed violations from incomplete evaluation:

```text
result
limitation, when indeterminate
```

`result` is:

```text
confirmed
indeterminate
```

`confirmed` means available canonical evidence proves the invariant is violated.

`indeterminate` means Portia cannot safely establish whether the invariant holds.

When indeterminate, `limitation` is one of:

```text
authorization_limited
unsupported_contract
external_module_unavailable
incomplete_canonical_state
recovery_in_progress
insufficient_evidence
```

Portia never converts authorization-limited visibility into `missing`, `invalid`, or `cleared`. An indeterminate finding remains visible until the limitation resolves or policy explicitly permits the affected operation.

## 20.10 Severity

Severity communicates risk and urgency but does not independently determine enforcement.

The vocabulary is:

```text
advisory
warning
error
critical
```

`advisory` means canonical state remains usable but attention or maintenance is recommended.

`warning` means the condition may affect interpretation or later operations and requires review.

`error` means a confirmed invariant violation affects identified records, graph, or operation; relevant current use or writes are blocked.

`critical` means the condition risks unauthorized disclosure, irreversible data loss, broad ambiguity in canonical authority, or unsafe continued operation.

Severity is rule-defined but may escalate based on affected scope or evidence. Acknowledgement does not lower severity.

## 20.11 Effects

Blocking behavior is separate from severity.

`effects` is a nonempty set drawn from:

```text
attention
review_required
block_current_use
block_lifecycle_writes
block_operation_completion
block_work_writes
block_class_writes
quarantine_target
```

Meanings:

- `attention`: display and report without blocking;
- `review_required`: require explicit review;
- `block_current_use`: prevent automatic use of the affected record;
- `block_lifecycle_writes`: block lifecycle-dependent writes against the target;
- `block_operation_completion`: prevent the coordinated operation from completing;
- `block_work_writes`: block work-graph writes except authorized repair or containment;
- `block_class_writes`: block class-wide writes except authorized repair or containment;
- `quarantine_target`: disable ordinary resolution and display.

Effects do not mutate persisted lifecycle status.

## 20.12 Scope

`scope` is one of:

```text
representation
logical_record
work
class
workspace
operation
graph
```

`representation` means one exact contract-versioned representation.

`logical_record` means several representations of one stable migration identity.

`work`, `class`, and `workspace` identify their corresponding ownership scopes.

`operation` identifies one coordinated Issue #13 operation.

`graph` identifies several exact records connected by replacement, dependency, migration, ownership, or another invariant.

Scope controls escalation, blocking breadth, repair planning, and presentation. It does not replace exact affected references.

## 20.13 Affected targets

Every finding has one `primary_target`.

Permitted targets include:

- exact Portia work representation;
- exact Portia work-record representation;
- same-work immutable audit record;
- class scope;
- workspace scope;
- or Issue #13 operation reference.

`related_targets` contains zero or more additional exact references required to explain the invariant.

Examples:

- status/history mismatch: record as primary; selected and conflicting transitions as related;
- broken migration reconciliation: migration certificate or source as primary; destination and transition as related;
- unresolved ownership child: destination Event as primary; certificate and source child as related.

The projection does not copy substantive narrative content merely for display.

## 20.14 Evidence

`evidence` contains minimal machine-readable facts necessary to explain detection.

Examples include:

```text
persisted_status
derived_status
expected_effective_at
observed_effective_at
expected_target
observed_target
missing_component_kind
conflicting_count
```

Evidence must not duplicate teacher narratives, Statements of Disagreement, student names, removed payloads, credentials, or other sensitive content.

User-facing explanations are generated from rule metadata, authorized record access, and minimal evidence.

## 20.15 Resolution

A finding clears only when reevaluation determines that the violation or limitation no longer exists.

Portia does not provide a canonical:

```text
mark_resolved
```

operation for findings.

Resolution occurs because canonical state was repaired, history was corrected, an operation completed or recovered, authorization became available, a producer contract became supported, or a derived index was rebuilt.

After repair, rescanning removes the active projection. Canonical repair artifacts preserve what occurred.

## 20.16 Acknowledgement

Applications may retain operational acknowledgement:

```text
acknowledged
```

Acknowledgement means only that an authorized local operator has seen the finding.

It does not change severity, remove effects, establish correctness, authorize an exception, or clear the finding.

Acknowledgement metadata belongs to Issue #13 operational workspace state, not canonical domain records.

## 20.17 Suppression

Suppression is presentation-only.

It may be permitted only when:

- severity is `advisory` or `warning`;
- no blocking or quarantine effect applies;
- the finding is understood;
- suppression does not conceal sensitive exposure;
- and configured policy permits it.

Suppression is prohibited for errors, critical findings, blocking authorization limitations, incomplete operations, removal-policy violations, and any finding with a blocking effect.

Suppression does not remove a finding from integrity reports, complete API results, operation validation, or policy enforcement.

Suppression expires when the rule version, affected revisions, severity, effects, or configured expiration changes.

## 20.18 Recurrence

Because `finding_key` is deterministic, Portia can recognize recurrence.

A finding recurs when it was absent after a complete evaluation and the same invariant and affected identity later produce the same key again.

Operational metadata may retain:

```text
first_seen_at
last_seen_at
cleared_at
recurrence_count
```

These timestamps are scan history, not canonical chronology.

Losing this cache does not impair reconstruction of current integrity state.

Recurrence may escalate severity or review under configured policy but does not alter canonical records automatically.

## 20.19 False positives and rule changes

When a finding was produced by an incorrect rule:

- fix or version the rule;
- reevaluate affected state;
- clear obsolete operational instances;
- preserve software or operation logs where required.

Portia does not create a domain amendment asserting that a diagnostic was wrong.

A real exception must be represented by an accepted domain contract, configured policy, or governed administrative certificate. Blocking invariants are not bypassed through suppression.

## 20.20 Authorization-limited findings

When complete validation requires inaccessible data:

- assessment is `indeterminate`;
- limitation is `authorization_limited`;
- unavailable records are not identified through guessed metadata;
- no conclusion of `missing` or `valid` is made;
- the least-permissive applicable effect is enforced.

A user-facing display may state that the condition cannot be fully validated with currently authorized data. It must not expose records beyond authorized visibility.

## 20.21 Review disposition

A finding may cause derived `review_required` treatment.

The reverse is not always true.

A record may require review because of a valid domain condition without any integrity finding.

Therefore:

```text
review_required != integrity_error
```

Applications preserve that distinction in APIs and user interfaces.

## 20.22 Relationship to validation

Before canonical acceptance:

- schema failure rejects the proposed write;
- application-validation failure rejects or returns the operation for correction;
- no workspace integrity finding is required.

After canonical acceptance:

- discovering structurally invalid canonical content produces an integrity finding;
- content is not silently deleted;
- repair follows recovery, correction, or exceptional-removal rules.

Routine user-entry validation errors do not pollute workspace integrity reports.

## 20.23 Relationship to Issue #13

Issue #13 defines:

- scan scheduling;
- operational finding caches;
- acknowledgement and suppression storage;
- operation references;
- repair-mode write allowances;
- quarantine mechanics;
- atomic recovery;
- integrity-report rebuilding.

Issue #12 defines semantic vocabulary and enforcement expectations.

No operational cache may become the sole evidence required to determine canonical state.

## 20.24 Derived views

Applications may derive:

```text
active findings by work
active findings by class
blocking findings
authorization-limited findings
findings by category
findings by rule
recurring findings
findings associated with incomplete operations
```

These views are rebuildable.

Deleting the cache and rescanning must reproduce the currently active finding set under the same rule versions, policy, authorization, producer contracts, and operation state.

## 20.25 Structural validation

A later derived-projection schema may validate:

- finding projection shape;
- rule and category tokens;
- severity;
- assessment;
- effects;
- scope;
- typed targets;
- minimal evidence;
- observation timestamps.

JSON Schema cannot establish whether a finding should exist.

## 20.26 Application validation

Finding-generation logic must confirm:

- stable rule identity and version;
- deterministic finding-key construction;
- exact affected-reference normalization;
- correct category and code;
- severity and effect compatibility;
- no sensitive-content duplication;
- confirmed versus indeterminate assessment;
- conservative authorization-limited handling;
- no conflation of review conditions with integrity defects;
- no manual clearing of active violations;
- suppression restrictions;
- recurrence behavior;
- reproducibility from canonical state and accepted operational evidence.

## 20.27 Rejected alternatives

### Canonical lifecycle-bearing findings

Rejected because findings may clear, recur, or change under revised evaluation rules.

### Unstructured validation messages

Rejected because they cannot support deterministic deduplication, enforcement, or remediation.

### Boolean validity

Rejected because Portia must distinguish confirmed, indeterminate, blocking, scoped, and recoverable conditions.

### User-cleared findings

Rejected because acknowledgement or preference cannot make an active invariant violation disappear.

---

# 21. Consequences

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

# 22. Unresolved Decisions

The following remain unresolved and must not be treated as accepted architecture:

1. final public schema organization.

No schemas should be created for unresolved items until their architectural decisions are approved.

## 23. Next Decision

The final architectural decision should define public schema organization, including:

- which approved contracts receive public Draft 2020-12 schemas in this issue;
- how schema versions and directories are organized;
- which shared primitives are reused versus introduced;
- whether derived integrity-finding projections receive a public schema;
- how later domain-family versions compose cross-work correction and migration contracts;
- and how legacy, current, audit, certificate, and projection schemas are documented without implying unsupported automatic migration.
