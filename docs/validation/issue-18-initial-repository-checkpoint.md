# Issue #18 Initial Repository Checkpoint

**Issue:** `#18 — Define Support Process, Support, Intervention, implementation, and fidelity contracts`
**Date:** 2026-08-10
**Branch:** `18-support-process-support-intervention-implementation-fidelity`
**Checkpoint:** initial repository and dependency review

## Portia branch baseline

GitHub comparison at the start of Issue #18:

```text
base: main
head: 18-support-process-support-intervention-implementation-fidelity
status: identical
ahead_by: 0
behind_by: 0
```

Both resolve to:

```text
5898ad79a7d405dc1e23b94753a0eeba793c8e72
17 response communication domain models (#30)
```

Issue #18 therefore starts from the fully merged Issue #17 architecture.

## Core baseline

Current reviewed Core main:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

Comparison of that checkpoint to `pds-core/main` is identical at Issue #18 start.

Core remains authoritative for workspace/class/roster identity, module-qualified
work identity, safe paths, PDS2 routing and retained-source provenance, and the
v0.6 reportable-data publication envelope.

Core v0.6 also defines `intervention_record_set` as a nonacademic publication
kind. Producer-native intervention and outcome semantics remain producer-owned,
and an intervention publication does not become a Score, standards rating, or
Grade. Issue #18 therefore needs native Portia contracts that could be projected
later without implementing publication in this issue.

No Core change is required by the initial Issue #18 design.

## Issue boundaries reviewed

The initial review covered:

```text
#10 — Complete the Portia foundations milestone
#17 — Define Response and Communication domain models
#18 — Define Support Process, Support, Intervention, implementation, and fidelity contracts
#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models
```

The governing progression remains:

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Follow-Up / Outcome / Reentry / Repair
```

The arrows are possible relationships, not mandatory record creation.

## Relevant Portia contracts reviewed

The initial review covered the current semantics of:

```text
portia_support_process_id@1
portia_work_ref@1
exact_portia_work_ref@1
portia_work_record_ref@1
exact_portia_work_record_ref@1
local_record_ref@1
exact_local_record_ref@1
support_process_target_ref@1
portia_local_work_target@1
work_relationship@2
represented_human_attribution@1
response@1
communication@1
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
ownership_correction@1
exceptional_removal@1
operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

The current Event v2 and Event Participant v3 shapes were also reviewed as
precedent for class-owned work roots, roster-qualified identity, participant
history, and application-level graph validation.

## Initial findings

### Support Process work identity is already reserved

`portia_support_process_id@1` already defines the opaque `sup_` work identifier.

Both `portia_work_ref@1` and `exact_portia_work_ref@1` already recognize:

```text
event
support_process
```

No new Support Process work-ID primitive or generic Portia work-reference version
is needed merely to publish `support_process@1`.

### Support Process targeting is intentionally preallocated

`support_process_target_ref@1` is already a closed Support Process-local target
family for:

```text
support_process
support_process_participant
support_process_participants
```

The participant branch deliberately uses a local typed/version-aware record
reference and does not assign provider, recipient, coordinator, or observer
semantics.

Issue #18 should therefore publish the canonical Support Process Participant
family that makes this accepted target contract resolvable rather than invent a
parallel target shape.

### Work Relationship remains narrow and useful

`work_relationship@2` retains exactly:

```text
relationship_type = draws_context_from
```

and requires an exact Portia source work plus an exact Event target.

That shape is directly useful for:

```text
Support Process draws_context_from Event
```

without implying causation.

It must not be broadened into a generic Support-Process-to-Support-Process or
child-record relation mechanism.

### Response already establishes the immediate/ongoing boundary

ADR 0013 defines Response as a bounded Event-local action and explicitly reserves
planned, recurring, scheduled, longitudinal, goal-directed,
implementation-tracked, or fidelity-tracked activity for Issue #18.

A completed Response handoff does not establish that a later Support or
Intervention was implemented.

Issue #18 must preserve this boundary rather than convert repeated Responses into
one Support record automatically.

### Communication already anticipates Support Process ownership

`communication@1` already structurally accepts:

```text
work_kind = event | support_process
```

ADR 0013 intentionally deferred active Support Process ownership until Issue #18
publishes the canonical owner.

The Issue #17 focused application validator currently rejects every
`support_process` owner with the explicit temporary reason that the canonical
Support Process contract is unavailable until Issue #18.

Issue #18 therefore needs to replace that temporary application gate with real
owner-resolution/current-use validation. No Communication wire-format change is
identified at the initial checkpoint.

### Support Process needs a participant family distinct from Event Participant

Event Participant v3 is Event-local and uses Event-specific identity and
correction semantics.

Support Process Participant should be a separate canonical child family because:

- its owner is a Support Process rather than an Event;
- provider/collaborator/family participation can legitimately include the local
  operator and recurring Actors;
- process participation is longitudinal rather than an Event occurrence claim;
- `support_process_target_ref@1` already names the intended record kind;
- and Support Process correction/continuity must not silently retarget Event
  Participant identity.

The participant subject should reuse `represented_human_attribution@1` rather
than duplicate person-identity wire shapes.

### Need and Goal require independent identity

The ticket requires later exact linkage, correction, reuse by several plans, and
future Outcome review.

Initial design therefore favors canonical child records for both Need and Goal
rather than mutable embedded arrays on `support_process@1`.

This preserves independent correction and allows later #19 records to identify
exact Need/Goal representations without placing Outcome state on the Support
Process root.

### Support and Intervention should remain separate record kinds

The two concepts share ownership, targeting, provider, schedule, and lifecycle
infrastructure, but their required semantics differ materially.

Initial design favors separate:

```text
support@1
intervention@1
```

rather than one permissive all-optional plan object.

An ordinary Support may legitimately be less prescriptive or `as_needed`.
An Intervention is expected to be deliberately structured, goal-linked, and
implementation-parameterized.

Separate record kinds also permit typed exact references from Implementation,
Fidelity, and later Outcome without inspecting a discriminator inside one generic
plan payload.

### Implementation must be occurrence history, not a counter

One Implementation should represent one bounded occurrence, attempt, or actual
implementation interval for one exact Support or Intervention.

Planned frequency/duration and actual implementation history must remain
separate. Calendar/reminder state must not create Implementation records merely
because time passed.

### Fidelity must remain distinct from effectiveness

Issue #18 can record attributed implementation-quality/fidelity evaluation, but
it must not become Outcome, provider competence, student compliance, family
engagement, or causal effectiveness.

Initial direction favors a canonical `fidelity@1` record with a neutral
categorical result and optional source-defined instrument result when the
instrument/scale identity is preserved.

No universal numeric Portia fidelity score is justified.

### Material adaptation does not require a new family initially

The initial design finds no stable need for `adaptation@1`.

A one-occurrence variation belongs on the affected Implementation. A material
prospective plan change creates a Support/Intervention successor with preserved
history and an adaptation/correction reason appropriate to the change.

A separate Adaptation family should be added only if later design demonstrates
an independently meaningful decision record that cannot be represented by those
mechanisms.

### Formal cross-Event/FBA ownership remains out of scope for v1

ADR 0012 deferred formal cross-Event/FBA use until Support Process became
concrete.

Making Support Process concrete does not by itself require a formal FBA or a new
longitudinal Hypothesis family.

Initial direction is:

- keep `hypothesis@1` Event-local;
- permit Support Process context to reference exact Event-local Hypotheses;
- prohibit automatic aggregation into function, diagnosis, risk, or a preferred
  Intervention;
- and defer formal FBA/team-hypothesis authority unless a later requirement
  demonstrates a safe, teacher-local semantic unit.

### Cross-year continuation is continuity, not correction

The current README already states that a Support Process continuing into a new
school year should normally receive a successor work item under the new
legitimate owning class.

Initial direction is a successor-owned exact predecessor link on the new Support
Process work root with one-to-one v1 cardinality.

The prior work does not become `superseded` merely because a reviewed next-year
process continues related support. Cross-year continuity is not migration,
ownership correction, or proof of prior effectiveness.

### Generic shared infrastructure remains sufficient

`portia_local_work_target@1` already targets either the containing Event/Support
Process work root or an exact canonical child representation.

Generic lifecycle, disagreement, dependency, migration/removal, operation,
Quarantine, Integrity Finding, source-snapshot, and derived-state contracts are
structurally reusable for the anticipated Issue #18 families.

No shared-infrastructure version bump is identified at the initial checkpoint.

## Initial public-contract direction

The pre-ADR design will evaluate the following additive public contracts:

```text
support_process@1
portia_support_process_participant_id@1
support_process_participant@1
portia_support_need_id@1
support_need@1
portia_support_goal_id@1
support_goal@1
portia_support_id@1
support@1
portia_intervention_id@1
intervention@1
planned_schedule@1
portia_implementation_id@1
implementation@1
portia_fidelity_id@1
fidelity@1
```

This list is a design candidate, not a publication authorization. ADR 0014 must
justify each contract before any schema `$id` is published.

Initial design does **not** justify:

```text
adaptation@1
support_process_hypothesis@1
provider@1
recipient@1
party@1
case@1
service@1
plan@1
```

## Initial drift classification

```text
pds-portia main:
no drift; Issue #18 branch starts identical

pds-core main:
no drift from the ticket checkpoint

shared Portia contracts:
reusable; no version bump identified

Issue #17 Communication:
wire shape reusable; temporary application-level Support Process gate must be
reconciled after canonical Support Process publication

Issue #16 Hypothesis:
Event-local contract remains valid; formal cross-Event/FBA semantics should not
be fabricated merely because Support Process is now concrete

Issue #19 Outcome boundary:
still deferred; #18 must not encode effectiveness or goal attainment as Outcome

Core v0.6 publication:
future compatibility consideration only; no publication integration in #18
```

## Next checkpoint

Before accepting ADR 0014:

1. re-fetch current Portia main;
2. re-fetch current Core main;
3. compare the Issue #18 branch to Portia main;
4. confirm ADR 0014 remains the next free ADR number;
5. reconcile the proposed contract inventory and identifier prefixes;
6. classify any drift as:
   - required contract change;
   - documentation reconciliation;
   - future concern; or
   - no implication.

No Issue #18 schema `$id` should be published until that pre-ADR checkpoint is
recorded.
