# Portia Lifecycle, Amendment, Correction, and Migration Contracts

**Status:** Working design — approved through Decision 10  
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

# 14. Consequences

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

# 15. Unresolved Decisions

The following remain unresolved and must not be treated as accepted architecture:

1. dependency handling;
2. duplicate consolidation;
3. migration-record semantics;
4. migration identity preservation;
5. incorrect Event ownership or work-root correction;
6. exceptional removal boundaries;
7. integrity-finding vocabulary;
8. final public schema organization.

No schemas should be created for unresolved items until their architectural decisions are approved.

## 16. Next Decision

The next decision should define dependency handling, including:

- how required and advisory dependencies are represented;
- whether dependencies are declared on the dependent record or through separate edges;
- how dependency lifecycle changes affect current-use eligibility;
- when dependency loss requires review, invalidation, or successor replacement;
- and how dependency repair avoids automatic cascades or silent retargeting.
