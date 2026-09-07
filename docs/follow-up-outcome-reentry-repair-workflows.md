# Follow-Up, Outcome, Reentry, and Repair Workflows

**Issue:** #46 — Implement Follow-Up, Outcome, Reentry, and Repair workflows  
**Milestone:** Portia v0.2.0  
**Contract authority:** ADR 0015 / Issue #19

Issue #46 supplies the production application/workflow layer for the accepted
downstream contracts without changing their published wire formats:

```text
follow_up@1
outcome@1
reentry@1
repair@1
```

These families remain teacher-local records beneath one exact Event or Support
Process work root. They document what happened next and what an attributable
human concluded from explicit context; they do not manufacture causation,
effectiveness, compliance, readiness, remorse, forgiveness, rehabilitation, or
resolution.

## Semantic units

The four contracts intentionally answer different questions.

```text
Follow-Up
= one bounded downstream check, review, coordination action, or obligation

Outcome
= one bounded attributable human evaluation for an explicit target/timeframe

Reentry
= one bounded teacher-local process for return/reentry planning and follow-through

Repair
= one bounded teacher-local restorative/reparative process
```

They are not interchangeable:

```text
scheduled Follow-Up != completed Follow-Up
completed Follow-Up != favorable Outcome != goal attained != resolved

Implementation completed != Support effective != Outcome
Fidelity as_planned != Support effective != favorable Outcome

Outcome linkage / temporal sequence != causation
later Event != automatic recurrence conclusion != intervention failure
fewer documented Events != improvement without adequate coverage

Reentry completed != safety/medical clearance
                  != compliance
                  != rehabilitation
                  != relationship restored

Repair participation != admission != remorse != forgiveness
Repair completed != remorse
                 != forgiveness
                 != relationship restored
                 != recurrence prevented

later Outcome for a later timeframe != correction of an earlier valid Outcome
```

## Public API

`portia.workflows` exports:

```text
FollowUpWorkflowService
OutcomeWorkflowService
ReentryWorkflowService
RepairWorkflowService

follow_up_reference(...)
outcome_reference(...)
reentry_reference(...)
repair_reference(...)
```

All four services retain exact historical reads, explicit current-use
qualification, work-local listing, canonical lifecycle, successor-based material
correction, duplicate consolidation, work-root correction, and exact current
resolution. Follow-Up, Reentry, and Repair additionally expose bounded ordinary
workflow-state progression. Outcome deliberately has no invented mutable
workflow-state axis.

None of the four v1 families exposes Amendment or an arbitrary `save(dict)`,
`patch`, `set_status`, or update-any-field API.

## Canonical ownership and targets

All four records are canonical children beneath exactly one existing Portia work:

```text
classes/<class_id>/modules/portia/work/<work_id>/records/
  follow_up/<follow_up_id>.json
  outcome/<outcome_id>.json
  reentry/<reentry_id>.json
  repair/<repair_id>.json
```

Eligible work roots are only:

```text
event@2
support_process@1
```

Current-use authority verifies the exact module, class, work kind, work ID,
record identity, canonical path, owner authority, lifecycle, and Quarantine
boundary. Exact historical reads do not silently follow successors.

Event-owned targets use the accepted Event target family. Support-Process-owned
targets use exact Support Process Participant authority. Targets are explicit;
Portia does not infer them from creators, coordinators, evaluators, providers,
prior outcomes, or participant ordering.

Operational humans likewise remain explicit. Event authority reuses the accepted
represented-human/Actor boundary; Support Process operational authority uses
exact current Support Process Participants with an eligible context. A roster
student, descriptive-only person, or unidentified person does not silently
become an operational owner, evaluator, coordinator, or facilitator.

## Lifecycle, correction, consolidation, and work-root correction

The canonical lifecycle remains separate from family-specific operational state:

```text
proposed
active
invalidated
superseded
```

Ordinary lifecycle changes are coordinated through the shared downstream
lifecycle authority. Recording-error correction creates a successor and
preserves exact history. Duplicate consolidation requires explicit multiple
legitimate predecessors; Portia does not infer duplicates from similar payloads.
Work-root correction is a distinct ownership-correction path, not ordinary
cross-work correction.

Exact references stay exact. Historical reads never silently retarget to a later
successor, a later Support Process plan, or a new yearly work root.

## Follow-Up

One `follow_up@1` records one bounded downstream follow-up. Its accepted purposes
include student/family/affected-person checks, event/response/support/goal/
implementation/fidelity/reentry/repair review, coordination, and bounded
`other` detail.

Timing preserves its stated precision (`date_only`, `exact_time`, or `window`).
Time passing does not create completion or an attempted-contact fact.

The operational states are:

```text
scheduled
in_progress
completed
cancelled
unable_to_complete
```

`overdue` is derived rather than a stored workflow state. Completion may exact-link
records reviewed or produced, such as Account, Observation, Communication,
Outcome, Reentry, Repair, Fidelity, or another Follow-Up, but does not copy their
substantive payload and does not create a favorable Outcome.

A Support Process review disposition remains an explicit human disposition, not
an effectiveness judgment. Any actual Support Process state change or plan
adaptation still goes through the authoritative planning workflow.

## Outcome

One `outcome@1` is one bounded, attributable human evaluation of a defined
question for an explicit target and timeframe. It is not raw evidence, a mutable
progress log, Fidelity, a Grade, standards proficiency, a permanent student
trait, or causal effect.

Current use requires an explicit eligible evaluator. The evaluator remains
distinct from recorder, evidence source, Follow-Up owner, Support/Intervention
provider, Fidelity evaluator, and institutional authority.

Accepted scope families include:

```text
goal_status
observed_change
recurrence_review
support_response_review
unintended_or_adverse_effect_review
reentry_status
repair_status
other
```

Scope-specific references resolve exactly. Basis entries preserve explicit roles
such as baseline, current period, supporting, contrary, contextual,
student/family perspective, implementation context, and fidelity context.
Portia does not add truth, credibility, or causal weights.

Every Outcome preserves an explicit bounded evaluation point or period. A later
evaluation for a later timeframe is ordinarily another legitimate Outcome, not a
correction of the earlier Outcome.

Missingness remains explicit. `unable_to_determine` is not failure or no change;
`source_unavailable` is not source refusal; unknown Fidelity is not poor Fidelity;
and absent Observation is not zero.

### Recurrence boundary

A later Event can be exact context for `recurrence_review`, but temporal sequence
alone does not establish recurrence, failed intervention, worsening behavior, or
causation. Conversely, fewer documented Events do not establish improvement
without adequate observation/coverage.

## Reentry

One `reentry@1` records a bounded teacher-local return/reentry process. It can
preserve explicit planning elements, timing, context, coordinator authority,
communication references, and completion state without becoming a medical,
safety, legal, disciplinary, or institutional clearance system.

Operational state is bounded to the accepted workflow vocabulary:

```text
planned
active
completed
cancelled
unable_to_complete
```

Ordinary state progression preserves the same Reentry identity and does not
rewrite unrelated historical facts. Completion states only that the represented
teacher-local process completed. It does not establish clearance, compliance,
rehabilitation, readiness, fitness, or restored relationships.

Portia therefore does not infer a credential or clearance decision from a
coordinator identity, a completed checklist, a communication, elapsed time, or a
later Event.

## Repair

One `repair@1` records a bounded teacher-local restorative/reparative process
addressing represented impact, relationship/community needs, or agreed
restorative actions. It is not a punishment ledger, debt/collections system,
restorative transcript, truth-finding record, character judgment, or admission
mechanism.

Participants use neutral roles and explicit participation states. Participation
may be invited, agreed, completed, declined, unavailable, withdrawn,
not-applicable, or unknown as the frozen contract permits. Current operational
use fails closed where identity/participation authority is insufficient. An
affected person is not required to participate; face-to-face contact, disclosure,
and apology are never mandatory.

Embedded agreed actions retain stable action keys, explicit agreement by
participant keys, optional responsible participant keys, bounded action types,
and factual completion chronology. Action completion states are process facts:

```text
planned
in_progress
completed
unable_to_complete
withdrawn
```

Neither participation nor action completion establishes admission, sincerity,
remorse, forgiveness, relationship restoration, rehabilitation, recurrence
prevention, or a favorable Outcome.

Repair workflow state is:

```text
planning
active
completed
cancelled
unable_to_complete
```

Progression preserves existing participant/action identities and agreed facts.
Work-root correction may rebind only representations that must change with the
true owner (for example target/facilitator/person projection); it preserves the
Repair's substantive focus, context, participant keys/roles/state, agreed
actions, workflow/completion state, and creation provenance.

## Cross-year behavior

Cross-year continuation is explicit graph context, not automatic migration,
correction, supersession, or identity reuse. A later year's Event or Support
Process is a separate exact work root. Downstream records remain pinned to the
yearly owner under which they were recorded unless an explicit accepted
ownership-correction operation establishes that the earlier root was wrong.

P22-11 acceptance preserves this boundary. Exact history remains usable without
silently following the newer year or treating normal continuation as correction.

## Automation limits

Issue #46 intentionally does not automate substantive judgments. In particular:

```text
completed Follow-Up -> no automatic Outcome
favorable/unfavorable Outcome -> no automatic Support Process state change
favorable/unfavorable Outcome -> no automatic plan adaptation/intensification
later Event -> no automatic recurrence/failure conclusion
Reentry completion -> no automatic clearance/compliance conclusion
Repair participation/completion -> no automatic admission/remorse/forgiveness
```

The services may validate explicit links and chronology. They do not transform
linkage into causation or workflow completion into a human judgment.

## Frozen Issue #19 runtime parity

Issue #46 mechanically accounts for every schema-valid frozen Issue #19 runtime
scenario:

```text
Follow-Up  valid 10 + application-invalid 14 = 24
Outcome    valid 13 + application-invalid 17 = 30
Reentry    valid 11 + application-invalid 14 = 25
Repair     valid 12 + application-invalid 19 = 31
                                                ---
46 valid + 64 application-invalid = 110 runtime scenarios
```

The manifests separately contain **72 structural-invalid fixtures**. Those remain
schema/model-validation authority and are deliberately excluded from workflow
runtime parity.

The four family parity maps plus `tests/test_issue46_combined_fixture_parity.py`
fail closed on manifest drift, missing runtime evidence, missing application-error
evidence, count drift, or structural/runtime overlap. A workflow test may
legitimately represent more than one fixture; parity requires explicit fixture
coverage, not artificial uniqueness of test-function names.

## Representative integration

`tests/test_issue46_representative_integration.py` exercises P22-08 through
P22-11 through the production current-use services after seeding the frozen
synthetic graph into a temporary canonical workspace.

The representative path is read-only after seeding. Resolution cannot rewrite
Support Process, Outcome, Reentry, Repair, or Follow-Up records and cannot invent
causation, effectiveness, clearance, compliance, remorse, forgiveness,
restoration, or recurrence conclusions.

## Issue and repository boundaries

Issue #46 is an application/workflow issue. It does not redesign ADR 0015,
published schemas, paper/import contracts, privacy projection, deliberate export,
retention, academic interpretation, Meridian grading/proficiency, or Vitrine
portfolio meaning.

Paper/import records remain historically readable according to the accepted
contract, but current operational use fails closed unless the required accepted
review/materialization authority exists. The services do not add a Meridian or
Vitrine runtime dependency.

Distribution and installed-wheel qualification are performed separately from
source/runtime parity. Cumulative repository qualification remains the final
closeout gate.
