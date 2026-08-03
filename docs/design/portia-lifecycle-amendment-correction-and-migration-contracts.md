# Portia Lifecycle, Amendment, Correction, and Migration Contracts

**Status:** Working design — approved through Decision 5  
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

# 9. Consequences

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

# 10. Unresolved Decisions

The following remain unresolved and must not be treated as accepted architecture:

1. amendment semantics and wire shape;
2. nonmaterial-versus-material decision test;
3. statement-of-disagreement semantics;
4. invalidation and terminal-state rules;
5. supersession reconciliation;
6. dependency handling;
7. duplicate consolidation;
8. migration-record semantics;
9. migration identity preservation;
10. incorrect Event ownership or work-root correction;
11. exceptional removal boundaries;
12. integrity-finding vocabulary;
13. final public schema organization.

No schemas should be created for unresolved items until their architectural decisions are approved.

## 11. Next Decision

The next decision should define the amendment record's semantics and wire shape, including:

- which nonmaterial changes may be applied in place;
- whether one amendment may affect several fields;
- how prior and resulting values are preserved;
- whether amendments use typed field changes, snapshots, or a constrained patch;
- and how the canonical target's `updated_at` and `updated_by` reconcile with append-only amendment history.
