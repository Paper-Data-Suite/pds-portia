# ADR 0015: Define Follow-Up, Outcome, Reentry, and Repair Domain Models

- **Status:** Accepted
- **Date:** 2026-08-12
- **Decision owners:** Portia maintainers
- **Related issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Builds on:** ADR 0001, ADR 0002, ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012, ADR 0013, and ADR 0014
- **Refines:** the earlier Event-local evidence assumption for Account/Observation by adding new versioned dual-owner contracts; the v1 contracts remain immutable

## Context

Portia now has a complete canonical foundation through support planning,
implementation, and fidelity:

```text
Event
→ Accounts / Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Implementation
→ Fidelity
→ Follow-Up / Outcome / Reentry / Repair
```

ADR 0014 intentionally stopped before downstream outcome semantics.

It established:

```text
planned Support / Intervention
≠ actual Implementation

Implementation
≠ Fidelity

Fidelity
≠ Outcome

workflow / plan / execution completion
≠ effectiveness
≠ success
≠ resolution
```

Issue #19 must define the downstream layer without turning Portia into a
student-global case system, clinical outcome platform, threat/safety-clearance
system, district restorative-justice authority, debt ledger, causal-inference
engine, or academic grading source.

The repository research also requires Portia to:

- track support processes rather than only incident counts;
- preserve student/family perspective as first-class source evidence;
- preserve direct and measured observation separately from interpretation;
- monitor both implementation fidelity and outcomes;
- preserve missingness and opportunity/coverage;
- support restorative/reparative and reentry work without coercive product
  semantics;
- and avoid automatic behavioral, moral, diagnostic, causal, or disciplinary
  judgment.

The pre-ADR checkpoint identified one genuine incompatibility in the already
published evidence layer:

```text
account@1
observation@1
```

are both structurally Event-local.

Each requires:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

That is correct for event evidence, but not sufficient for routine Support
Process work.

A legitimate Support Process may produce:

- a weekly direct count or timed observation;
- a student check-in perspective;
- a family perspective;
- an observed replacement-skill opportunity;
- a review-period measurement;
- or another bounded source record

without any real-world occurrence that should become an Event.

Creating a fake Event solely to store that evidence would violate Portia's
Event semantics and would distort recurrence/event counts.

Copying the statement or measurement directly into Outcome would collapse:

```text
source evidence
≠ evaluation
```

Changing `account@1` or `observation@1` in place would violate published-schema
immutability.

ADR 0015 therefore resolves both the downstream #19 model and the evidence
versioning required to support it honestly.

The required pre-ADR drift check found:

```text
pds-portia/main
0d08495557721681b11d081e91c8b416a556df8a

Issue #19 branch before this ADR
7f1ce8c

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c
```

Portia main, Core main, and Meridian main have not drifted from the Issue #19
initial checkpoint. ADR 0015 was unused immediately before this file was added.

The authoritative local starting suite remains:

```text
762 tests
OK
```

as recorded by Slice 1.

## Decision

### 1. Follow-Up, Outcome, Reentry, and Repair are canonical work-local children

Issue #19 will publish four separate canonical record families:

```text
follow_up@1
outcome@1
reentry@1
repair@1
```

They are not new top-level work kinds.

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    follow_up/<follow_up_id>.json
    outcome/<outcome_id>.json
    reentry/<reentry_id>.json
    repair/<repair_id>.json
```

Each record is owned by exactly one existing Portia work root:

```text
event
support_process
```

The owner envelope follows the accepted `communication@1` precedent:

```text
module_id = portia
class_id
work_kind = event | support_process
work_id
```

Application validation resolves `work_id` according to `work_kind`, verifies
class/path agreement, verifies the owner is current-use eligible when required,
and rejects cross-work identity mismatch.

No new top-level:

```text
case
outcome_process
reentry_process
repair_process
```

is introduced.

### 2. Existing target families remain authoritative

Issue #19 publishes no generic target family.

For Event-owned records:

```text
target -> portia_target_ref@1
```

For Support-Process-owned records:

```text
target -> support_process_target_ref@1
```

Application validation enforces owner/target agreement and logical-human
uniqueness for plural targets.

Targets are never inferred from:

- the first Event;
- the first student;
- the first Support Process Participant;
- a Communication recipient;
- a Follow-Up owner;
- a provider;
- a Goal;
- a prior Outcome;
- a Repair participant.

Target membership does not establish participation, agreement, fault,
responsibility, authority, or effect.

### 3. Existing exact work/record references are reused

Issue #19 reuses:

```text
exact_portia_work_ref@1
exact_portia_work_record_ref@1
exact_local_record_ref@1
module_work_record_ref@1
```

for exact historical links.

These references must not silently follow:

```text
correction
supersession
plan adaptation
record migration
duplicate consolidation
ownership correction
cross-year Support Process continuation
```

No new generic exact #19 reference contract is published.

### 4. Account and Observation gain additive version 2 contracts

Issue #19 will publish:

```text
account@2
observation@2
```

while leaving:

```text
account@1
observation@1
```

unchanged.

Version 2 preserves the v1 semantic units.

Account remains:

> one coherent attributed statement, report, response, recollection, or
> perspective from one represented human source.

Observation remains:

> one coherent attributed or instrumented record of directly observable,
> counted, timed, recorded, or measured information.

Neither becomes Outcome, interpretation, finding, credibility judgment,
diagnosis, behavioral-function claim, risk score, or causal conclusion.

The version-2 owner envelope adds:

```text
work_kind = event | support_process
work_id
```

with owner-conditioned target rules:

```text
work_kind = event
→ work_id is Event identity
→ target is portia_target_ref@1

work_kind = support_process
→ work_id is Support Process identity
→ target is support_process_target_ref@1
```

All existing v1 source/observer, content, evidence-time, measurement,
provenance, lifecycle, retraction/correction, and privacy semantics are
preserved unless the v2 schema must make the owner-generalization explicit.

New current writers should prefer v2 after it is published. V1 remains readable
and valid history. No automatic migration is required.

### 5. Account/Observation v2 correction may preserve v1 predecessors

Version-2 exact predecessor references may identify contract version 1 or 2.

A v2 Event-owned Account/Observation may legitimately supersede a v1
Event-owned predecessor when correcting or migrating the same represented
record.

A Support-Process-owned v2 record cannot claim a v1 Support-Process predecessor
because no such v1 representation existed.

Application validation must preserve:

- exact predecessor contract version;
- same represented record semantics;
- owner/work-root correction rules;
- no silent successor following;
- no migration by mere reference;
- no automatic conversion of old v1 records.

The existing opaque Account/Observation IDs and prefixes remain authoritative;
only contract version changes.

### 6. No fake Event may be created to host support evidence

A Support Process check-in, measurement, or progress-monitoring observation may
be stored directly under the Support Process through Account/Observation v2.

An Event should exist only when the real-world occurrence honestly satisfies
Event semantics.

Portia must not create an Event merely because a storage contract requires one.

This protects:

- Event counts;
- recurrence interpretation;
- event timelines;
- causal reasoning;
- equity analytics;
- incident/documentation meaning.

### 7. Follow-Up identity is accepted

Issue #19 publishes:

```text
portia_follow_up_id@1
follow_up@1
```

with prefix:

```text
fup_
```

One Follow-Up represents:

> one bounded, explicitly owned downstream check, review, coordination action,
> or follow-up obligation associated with one Event or Support Process.

Follow-Up is not Account, Observation, Event Review, Communication, Outcome,
Support/Intervention, Implementation, Fidelity, or Determination.

### 8. Follow-Up owner is explicit and operational

Follow-Up owner is distinct from:

```text
created_by
updated_by
target
Support/Intervention provider
Implementation provider
Outcome evaluator
institutional authority
```

For Event-owned Follow-Up, current-use owner representation uses
`represented_human_attribution@1`, with application validation requiring an
eligible operational human. Current-use roster-student, descriptive-only, and
unidentified representations cannot become operational staff owners merely
because they are representable human identities.

For Support-Process-owned Follow-Up, current-use owner uses an exact
Support Process Participant reference. The resolved participant must be
current-use eligible and carry an operational context such as:

```text
provider_or_collaborator
coordinator
```

A supported student or family/support participant does not become operational
owner by default.

Historical/imported uncertainty remains proposed until Issue #20 review
semantics permit current use.

Owner identity does not establish employment, licensure, case-manager status,
legal responsibility, or institutional authority.

### 9. Follow-Up purpose is closed

Accepted v1 purpose vocabulary:

```text
student_check_in
family_or_support_person_check_in
affected_person_check_in
event_review
response_review
support_process_review
goal_review
implementation_review
fidelity_review
reentry_check
repair_check
coordination
other
```

`other` requires bounded detail.

Purpose does not determine result.

Examples:

```text
goal_review
≠ goal met

family_or_support_person_check_in
≠ family participated

repair_check
≠ repair completed
```

### 10. Follow-Up planning and workflow preserve honest timing

Follow-Up uses a schema-local planned-timing union rather than publishing a new
shared timing contract.

It must support at least:

```text
date_only
exact_time
window
```

without inventing timestamp precision.

Canonical lifecycle remains:

```text
proposed
active
invalidated
superseded
```

Workflow state is:

```text
scheduled
in_progress
completed
cancelled
unable_to_complete
```

`overdue` is derived, not canonical.

Required meanings:

```text
time elapsed
≠ completed

reminder fired
≠ attempted

calendar entry
≠ Communication

completed Follow-Up
≠ favorable Outcome
≠ goal met
≠ resolved

missing completion
≠ declined
≠ unavailable
```

Material correction of terminal completion facts uses successor/history.

### 11. Follow-Up may exact-link produced/reviewed/context records

Follow-Up may carry a bounded array of schema-local exact record relations.

Accepted relation roles are:

```text
context
reviewed
produced
follow_up_to
```

The locator is `exact_portia_work_record_ref@1`.

Application validation checks relation-kind compatibility, exact resolution,
logical uniqueness, no self-reference, and owner/authorization constraints.

The relation records workflow provenance only.

For example:

```text
family call
→ Follow-Up + Communication

student check-in
→ Follow-Up + Account v2

direct progress measurement
→ Follow-Up + Observation v2

goal review
→ Follow-Up + Outcome
```

A Follow-Up must not copy the substantive payload of those records.

### 12. Completed Support Process review may carry a human workflow disposition

A completed Support-Process-owned Follow-Up whose purpose is a review purpose
may optionally carry:

```text
continue_current_support
review_later
adapt_plan
fade_or_reduce_support
complete_process
discontinue_process
no_additional_action
other
```

`other` requires detail.

This disposition means:

> the bounded next workflow action chosen by a human at that review.

It is not:

```text
Outcome
Determination
effectiveness
causal finding
automatic workflow-state transition
automatic plan adaptation
```

Any Support Process workflow-state change remains an explicit revision-aware
write.

Any material Support/Intervention adaptation remains an ADR 0014
`plan_adapted` successor.

### 13. Outcome identity is accepted

Issue #19 publishes:

```text
portia_outcome_id@1
outcome@1
```

with prefix:

```text
out_
```

One Outcome represents:

> one bounded, attributable human evaluation of one defined downstream
> question for an explicit target and timeframe, based on explicit
> evidence/context.

Outcome is not a mutable progress log, raw evidence container, Fidelity record,
workflow completion, scientific causal-effect estimate, Grade, standards
proficiency value, or permanent student trait.

### 14. Outcome evaluator is explicit and operational

Outcome evaluator is distinct from:

```text
created_by
updated_by
evidence source
Follow-Up owner
Support/Intervention provider
Implementation provider
Fidelity evaluator
institutional authority
```

Event-owned current-use Outcome uses an eligible represented operational human.

Support-Process-owned current-use Outcome uses an exact eligible Support Process
Participant with an appropriate evaluator context, including:

```text
provider_or_collaborator
coordinator
observer
```

A supported student/family perspective remains Account evidence rather than
being converted into staff evaluation.

Current-use unidentified evaluators are prohibited.

Evaluator identity does not establish professional/institutional authority.

### 15. Outcome scope is a closed discriminated union

Accepted scope kinds are:

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

Scope carries the exact references/details required for the question.

#### goal_status

Requires one exact `support_goal@1` reference and Support Process ownership.

#### observed_change

Requires a bounded operational question/measure label describing what change is
being evaluated.

#### recurrence_review

Requires a bounded recurrence question plus explicit coverage.

#### support_response_review

Requires one or more exact Support/Intervention plan refs and a bounded response
question.

#### unintended_or_adverse_effect_review

Requires a bounded question and coverage sufficient for the represented claim.

#### reentry_status

Requires one exact `reentry@1` reference.

#### repair_status

Requires one exact `repair@1` reference.

#### other

Requires bounded detail.

Scope is never inferred from free text or the first basis record.

### 16. Outcome timeframe reuses evidence-time precision

Outcome timeframe reuses:

```text
evidence_time@1
```

because it already preserves exact, approximate, date-only, range, and unknown
temporal precision without fabrication.

Interpretation is:

```text
exact / approximate / date_only
→ point evaluation

range
→ bounded evaluation period
```

Current-use active Outcome may not use `unknown`.

A later evaluation for a later point/period is normally a **new Outcome**, not
correction.

Creation timestamp is not outcome timeframe.

### 17. Outcome basis is schema-local and role-bearing

Issue #19 does not broaden `judgment_evidence_ref@1`.

Outcome basis is a schema-local array with explicit evidence role.

Accepted roles:

```text
baseline
current_period
supporting
contrary
contextual
student_or_family_perspective
implementation_context
fidelity_context
```

Accepted locators are:

```text
exact Portia work-record reference
module-qualified sibling record reference
```

Portia exact refs are preferred for native evidence.

Raw source artifacts are not normal Outcome basis; substantive source material
should become Account/Observation where the evidence model can represent it.

No:

```text
weight
credibility score
truth flag
causal weight
```

is introduced.

A public `outcome_evidence_ref@1` is **not** justified for v1 because the
role-bearing composition is currently used only by Outcome.

### 18. Outcome result vocabulary is scope-specific

Outcome does not publish one universal numeric score.

#### goal_status

```text
met
partially_met
not_met
unable_to_determine
not_applicable
```

#### observed_change

```text
improved
no_clear_change
mixed
worsened
unable_to_determine
not_applicable
```

#### recurrence_review

```text
recurrence_observed
no_recurrence_observed_within_defined_coverage
unable_to_determine
not_applicable
```

#### support_response_review

```text
progress_observed
no_clear_progress
mixed
worsening_observed
unable_to_determine
not_applicable
```

#### unintended_or_adverse_effect_review

```text
change_observed
no_change_observed_within_defined_coverage
mixed
unable_to_determine
not_applicable
```

#### reentry_status

```text
improved
no_clear_change
mixed
worsened
unable_to_determine
not_applicable
```

#### repair_status

```text
improved
no_clear_change
mixed
worsened
unable_to_determine
not_applicable
```

`other` uses:

```text
conclusion
unable_to_determine
not_applicable
```

with bounded conclusion detail where required.

These values are bounded evaluations, not causal effect sizes.

### 19. Goal status does not rewrite Goal

`goal_status` exact-links one Goal.

Required meanings:

```text
met
→ met for the represented timeframe/basis

partially_met
→ no invented percentage

not_met
→ not student failure, defiance, or noncompliance

unable_to_determine
→ evidence limitation, not failure
```

Goal planned criteria/measurement approach may guide human evaluation but cannot
automatically establish status.

No universal goal-progress percentage is introduced.

### 20. Raw measurement remains Observation

Account/Observation v2 resolves the evidence-owner gap.

Counts, rates, duration, latency, percentages, opportunity measures, and direct
or instrumented measurements remain Observation evidence where sufficient.

Outcome references those exact Observations and records the human bounded
evaluation.

Issue #19 must not convert:

```text
missing Observation
→ zero

missing Event
→ no recurrence

blank value
→ no change
```

Any persisted derived comparison requires exact sources, compatible measures,
time windows, denominators/scales where applicable, and explicit missingness.

### 21. Outcome limitations are first-class

Accepted limitation vocabulary:

```text
insufficient_evidence
insufficient_observation_opportunity
comparison_basis_unavailable
implementation_history_incomplete
fidelity_unknown
source_unavailable
follow_up_not_completed
authorization_limited
other
```

`other` requires bounded detail.

`unable_to_determine` requires at least one limitation.

A no-event/no-change claim that depends on coverage must preserve that coverage.

Required distinctions:

```text
unable_to_determine
≠ failure
≠ no change

source unavailable
≠ source declined

fidelity unknown
≠ poor fidelity

no recurrence observed within defined coverage
≠ proof of no recurrence outside that coverage
```

### 22. Recurrence requires explicit coverage

`recurrence_review` includes schema-local coverage with at least:

```text
coverage_kind
coverage_description
```

Accepted coverage kinds:

```text
direct_observation
event_record_review
combined
other
```

`other` requires detail.

Coverage is bounded to the Outcome timeframe.

A no-recurrence result is valid only as:

```text
no_recurrence_observed_within_defined_coverage
```

and requires explicit coverage sufficient for that represented claim.

A later linked Event never automatically creates:

```text
recurrence conclusion
intervention failure
causal failure
```

No later Event found never automatically creates no-recurrence Outcome.

No recurrence forecast/risk score is introduced.

### 23. Outcome does not claim ordinary causation

Outcome v1 has no fields such as:

```text
caused_by
causal_effect
treatment_effect
percent_effective
intervention_caused_improvement
response_prevented_recurrence
```

Temporal order and exact linkage are context only.

`support_response_review` represents a bounded human review of progress/change
during exposure to identified support; it is not a scientific treatment-effect
estimate.

If an authorized external research process later makes a causal claim, Portia
may preserve an inert external/module reference where an accepted contract
permits. Portia does not convert that into teacher-local causal truth.

No automated causal inference is permitted.

### 24. Fidelity and Outcome remain orthogonal

Outcome may exact-link Fidelity as basis/context.

All combinations remain possible:

```text
as_planned Fidelity + favorable Outcome
as_planned Fidelity + unfavorable/inconclusive Outcome
not_as_planned Fidelity + favorable Outcome
unknown/no Fidelity + any supportable Outcome
```

None establishes causation.

Implementation count also does not establish complete dosage without capture
coverage.

### 25. Support Process review uses Follow-Up + Outcome

Issue #19 does not broaden Event-local `review@1`.

A Support Process review is represented by a Follow-Up whose purpose is, for
example:

```text
support_process_review
goal_review
implementation_review
fidelity_review
```

and may produce/reference:

```text
Account v2
Observation v2
Communication
Outcome
later Follow-Up
```

This preserves:

```text
review action happened
≠ review conclusion
```

No Support Process `review@2` is introduced.

### 26. Support Process closure remains human-controlled workflow

No date, plan completion, Goal result, Fidelity result, Event count, or Outcome
automatically changes Support Process workflow state.

A completed review Follow-Up may record a human disposition.

If that disposition is implemented:

```text
complete_process
discontinue_process
```

the Support Process root receives a separate explicit revision-aware workflow
update.

If it is:

```text
adapt_plan
fade_or_reduce_support
```

any material plan change uses an ADR 0014 plan successor.

Outcome remains evidence/evaluation, not workflow command.

### 27. Reentry identity is accepted

Issue #19 publishes:

```text
portia_reentry_id@1
reentry@1
```

with prefix:

```text
ren_
```

One Reentry represents:

> one bounded teacher-local plan/process for supporting return to an ordinary
> educational setting, activity, relationship context, or classroom workflow
> after a represented interruption, removal, absence, conflict, or other
> relevant context.

Reentry is not medical clearance, threat-assessment clearance, special-
education placement authority, legal permission to attend, proof a prior
exclusion was valid, punishment, apology requirement, behavioral contract, or
readiness score.

### 28. Reentry coordinator is explicit and operational

Coordinator is distinct from persistence recorder and external/institutional
clearance authority.

Event-owned current-use Reentry uses an eligible represented operational human.

Support-Process-owned current-use Reentry uses an exact eligible Support Process
Participant carrying an operational context such as:

```text
provider_or_collaborator
coordinator
```

Current-use unidentified coordinators are prohibited.

Coordinator identity does not establish exclusion/admission authority, clinical
qualification, or institutional case-manager status.

### 29. Reentry initiating context is exact and minimal

Reentry carries one primary schema-local initiating context.

Accepted context kinds:

```text
event
determination
response
support_process
communication
external_or_restricted_process
other
```

Portia-native kinds use exact work/work-record refs.

`external_or_restricted_process` stores only a minimal inert locator:

```text
system_label
reference_id
status_label?
```

with no unrestricted external payload.

`other` requires bounded detail.

The context does not establish that the prior action was correct or that Portia
has authority over the external process.

### 30. Reentry planning is bounded and does not clone implementation

Reentry supports bounded planned elements:

```text
orientation_or_check_in
schedule_or_environment
academic_access
support_handoff
relationship_reconnection
communication
other
```

`other` requires detail.

Reentry may exact-link existing Support/Intervention plans.

Actual actions remain existing canonical records:

```text
Response
Communication
Implementation
Follow-Up
Repair
```

No pseudo-Implementation array is embedded in Reentry.

### 31. Reentry workflow state is operational

Canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

Workflow state:

```text
planned
active
completed
cancelled
unable_to_complete
```

Planned return timing uses a schema-local precision-preserving timing union and
does not require fabricated exact time.

Required meanings:

```text
return date passed
≠ Reentry completed

person returned
≠ every planned element occurred

completed Reentry
≠ safe
≠ compliant
≠ rehabilitated
≠ relationship restored
```

Post-reentry evaluation/check is a separate Follow-Up and, if appropriate,
Outcome.

Optional teacher-local Reentry steps must not become unauthorized barriers to
class/school access.

### 32. Repair identity is accepted

Issue #19 publishes:

```text
portia_repair_id@1
repair@1
```

with prefix:

```text
rpr_
```

One Repair represents:

> one bounded teacher-local restorative or reparative process intended to
> address represented impact, relationship/community needs, or agreed
> restorative actions without converting participation into admission,
> punishment, or character judgment.

Repair does not prove the underlying allegation.

Repair is distinct from Response, Communication, Determination, Support,
Reentry, and Outcome.

### 33. Repair facilitator is explicit and operational

Facilitator is distinct from recorder, target, institutional authority, and the
people whose participation is represented.

Event-owned current-use Repair uses an eligible represented operational human.

Support-Process-owned current-use Repair uses an exact eligible Support Process
Participant with an operational context such as:

```text
provider_or_collaborator
coordinator
```

Facilitator identity does not establish professional licensure, restorative-
justice authority, or legal authority.

### 34. Repair participants are embedded process-local entries

Issue #19 does **not** publish `repair_participant@1`.

Repair carries bounded process-local participant entries because the participant
semantics are meaningful only inside one Repair and do not yet require
independent canonical lifecycle.

Each entry has a local stable `participant_key`, a person locator, one or more
neutral process roles, and participation state.

For Event-owned Repair, person representation uses
`represented_human_attribution@1`.

For Support-Process-owned Repair, current-use participant representation uses an
exact Support Process Participant reference.

Accepted roles:

```text
affected_person
person_addressing_impact
supporter
community_participant
other
```

Facilitator remains a separate field.

Accepted participation states:

```text
invited
agreed_to_participate
participated
declined
unavailable
withdrew
not_applicable
unknown
```

`unknown` is historical/import-only for current-use validation.

Required meanings:

```text
declined
≠ uncooperative
≠ noncompliant
≠ lack of remorse

participated
≠ agreement
≠ forgiveness
≠ remorse
≠ truth of another Account

Communication completed
≠ Repair participation
```

No engagement/cooperation/remorse/sincerity score is introduced.

### 35. Repair focus does not create an official narrative

Repair carries a bounded process focus and exact context refs.

It does not overwrite Event evidence or Determination.

Substantive participant claims remain Account evidence where represented.

Conflicting Accounts remain separate and can coexist.

Affected-person participation, direct meeting, apology, disclosure, or
forgiveness cannot be mandatory schema requirements.

### 36. Repair agreed actions are embedded; no `repair_action@1` in v1

Issue #19 does **not** publish `repair_action@1`.

Repair carries bounded embedded agreement/action entries because the current use
cases do not require independent canonical action identity across the system.

Each action has a local stable `action_key` and may include:

```text
action_type
description
agreed_by participant keys
responsible participant keys?
agreed_at
completion_state
completed_at?
completion_detail?
```

Accepted action types:

```text
return_or_restore_property
repair_or_replace_property
restorative_action
community_or_relationship_action
follow_up_conversation
other
```

`other` requires detail.

Accepted completion states:

```text
planned
in_progress
completed
unable_to_complete
withdrawn
```

Agreement and completion are distinct.

If later issues demonstrate a need to reference actions independently across
records, a future `repair_action@1` can be added without pretending that v1
already had independent canonical action identity.

### 37. Repair is not financial collections

Repair may record bounded facts such as property returned/restored/replaced or
an agreed nonfinancial action completed.

It must not carry:

```text
account balance
invoice
payment schedule
collections status
debt enforcement
```

If an authoritative external financial obligation exists, Repair may preserve
only a minimal inert reference where allowed.

Inability to pay is not behavioral noncompliance.

### 38. Repair workflow completion has narrow meaning

Canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

Workflow state:

```text
planning
active
completed
cancelled
unable_to_complete
```

Participant decline/withdrawal may lead a human to cancel or stop the process,
but neither is blame.

Required meanings:

```text
completed agreed action
≠ remorse
≠ forgiveness
≠ relationship restored
≠ rehabilitation
≠ recurrence prevented
```

Later relationship/impact change is a separate Outcome.

### 39. Later assessment is new history, not correction

A later Outcome with a later timeframe is a new Outcome.

Example:

```text
week 2  -> no_clear_change
week 6  -> improved
```

Both remain valid.

Supersession is for material correction/replacement of the same represented
claim.

The same principle applies to later Follow-Up, Reentry, and Repair evaluation
history.

Exact old refs remain exact.

### 40. #19 canonical lifecycle is consistent

Follow-Up, Outcome, Reentry, and Repair use:

```text
proposed
active
invalidated
superseded
```

unless the concrete schema work uncovers a contradiction requiring another ADR.

Domain workflow/result state remains separate.

`invalidated` never means:

```text
unfavorable Outcome
cancelled Follow-Up
unable Reentry
declined Repair
recurrence
goal not met
disagreement
workflow closure
```

### 41. No #19 v1 Amendment paths

Issue #19 exposes no v1 Amendment paths for:

```text
Follow-Up
Outcome
Reentry
Repair
```

or for new Account/Observation v2 evidence records.

Ordinary revision-aware progression may update active workflow state where the
same represented process is continuing.

Material correction of terminal factual/evaluative claims uses
successor/history semantics.

Statement of Disagreement remains additive.

### 42. Successor reason vocabularies are closed

Follow-Up reasons:

```text
owner_corrected
purpose_corrected
target_corrected
timing_corrected
completion_corrected
related_record_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Outcome reasons:

```text
evaluator_corrected
scope_corrected
target_corrected
timeframe_corrected
basis_corrected
result_corrected
limitation_corrected
summary_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Reentry reasons:

```text
coordinator_corrected
target_corrected
context_corrected
timing_corrected
plan_element_corrected
completion_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Repair reasons:

```text
facilitator_corrected
participant_corrected
focus_corrected
agreement_corrected
completion_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

`other` requires bounded detail.

Account/Observation v2 retain their family-specific accepted correction
semantics while permitting exact v1/v2 predecessor history.

### 43. Existing lifecycle/migration/removal infrastructure is reused

Issue #19 reuses:

```text
lifecycle_transition@1
lifecycle_history_correction@1
statement_of_disagreement@1
dependency@1
record_migration@1
ownership_correction@1
exceptional_removal@1
```

No family-specific migration/removal contract is added unless concrete schema
work demonstrates a real incompatibility.

Cross-year Support Process continuation is not migration.

### 44. Existing operation/recovery infrastructure is reused

Issue #19 reuses:

```text
operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
```

Potential coordinated operations include:

- Follow-Up completion + Communication/Account/Observation/Outcome;
- Support Process review + explicit workflow-state update;
- Outcome + later plan adaptation;
- Reentry completion + later Follow-Up;
- Repair action completion + later Outcome;
- successor activation;
- migration/ownership correction/removal;
- derived rebuild.

Canonical domain records remain distinct from operation state.

Quarantine is not domain lifecycle.

Integrity Findings remain deterministic diagnostics, not behavioral judgments.

### 45. Derived state remains nonauthoritative

Issue #19 reuses:

```text
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

Derived views may support:

```text
due Follow-Ups
overdue Follow-Ups
latest Outcome by question/timeframe
support-review queue
reentry-check queue
repair-check queue
participant timeline
recurrence-review candidate list
```

Required meanings:

```text
missing derived row
≠ no canonical record

stale queue
≠ Follow-Up cancelled

latest Outcome
≠ deletion of older Outcomes

zero counted Events
≠ no recurrence without coverage
```

Derived state is rebuildable, privacy-minimized, and authorization-scoped.

### 46. Cross-year history does not create a student dossier

#19 records stay under their exact Event/Support Process owner.

When a Support Process continues across a year boundary:

- prior #19 records remain with the predecessor Support Process;
- new records belong to the legitimate successor Support Process;
- prior Outcomes are not copied as current;
- prior Reentry/Repair does not reopen automatically;
- exact refs remain exact;
- longitudinal display is derived from explicit links.

### 47. Paper/import semantics remain conservative

Issue #20 remains authoritative for paper/PDS2/import routing and human review.

Issue #19 must preserve:

```text
blank Follow-Up form
≠ completed Follow-Up

preprinted Outcome scale
≠ Outcome

scheduled Reentry checklist
≠ Reentry completed

Repair template
≠ Repair agreement

unchecked box
≠ declined
≠ unavailable
≠ no change

OCR / mark recognition
≠ progress/effectiveness judgment
≠ participation
≠ remorse
≠ causation
```

Paper/import-derived substantive #19 records and Account/Observation v2 evidence
remain proposed until accepted review history permits current use.

No new paper/PDS2 route contract is introduced by #19.

### 48. Native privacy is minimized

#19 schemas use opaque IDs, bounded summaries, exact refs, and closed structures.

They must not contain unrestricted:

```text
clinical notes
therapy notes
threat-assessment detail
abuse/investigation detail
restorative transcript
Actor phone/email values
student/family engagement scores
remorse/character labels
```

A Reentry external/restricted-process context stores only minimal inert locator
metadata.

Issue #21 remains authoritative for full redaction/export/retention/Sunset
policy.

### 49. Automation may organize but not make the human evaluation

Software may:

- validate refs and chronology;
- create reminders from human scheduling;
- surface due/overdue work;
- calculate transparent descriptive comparisons from compatible measures;
- identify missing evidence/coverage;
- show exact Implementation/Fidelity context;
- prepare drafts;
- rebuild derived state.

Software must not automatically:

- complete Follow-Up from time passage;
- create Outcome from counts;
- infer improvement from fewer reports;
- infer deterioration from more reports;
- infer recurrence failure;
- infer causation/effectiveness;
- select Goal status;
- infer Fidelity;
- infer compliance, engagement, motivation, remorse, attitude, or risk;
- infer family engagement;
- infer provider competence;
- close/adapt/intensify/fade Support;
- complete Reentry from a date;
- complete Repair from Communication;
- infer forgiveness/relationship restoration;
- publish intervention/outcome data.

Human attribution is explicit.

### 50. Core v0.6 publication remains a future projection

Core v0.6 provides:

```text
publication kind:
  intervention_record_set

capabilities:
  intervention_history
  intervention_status
  intervention_outcomes
```

Portia owns its native evidence/outcome semantics.

Issue #19 does not implement:

```text
PublicationProducerProfile
producer manifest
Publication Record creation
paper_data_suite.publication_producers registration
Meridian Portia adapter
Meridian selection/subscription policy
Academic Work Registration
academic_result_set
Score
standards rating
Grade
automatic intervention/outcome publication
```

Future publication is a separate privacy-minimized projection.

Discoverability is not disclosure authorization.

### 51. Meridian and portfolio boundaries remain unchanged

Portia does not depend on Meridian.

Outcome is not:

```text
standards proficiency
Grade evidence
Grade item
automatic Grade contribution
```

Issue #19 records do not automatically enter Vitrine/portfolio.

Any future reporting/portfolio projection must be separately authorized,
purpose-specific, privacy-governed, and preserve producer-native semantics.

### 52. Accepted public contract inventory

Issue #19 is expected to publish:

```text
account@2
observation@2

portia_follow_up_id@1
follow_up@1

portia_outcome_id@1
outcome@1

portia_reentry_id@1
reentry@1

portia_repair_id@1
repair@1
```

Candidate prefixes accepted after collision check:

```text
fup_
out_
ren_
rpr_
```

Issue #19 does not publish:

```text
outcome_evidence_ref@1
repair_action@1
repair_participant@1
progress@1
effectiveness@1
closure@1
success@1
engagement@1
compliance@1
remorse@1
forgiveness@1
readiness@1
case@1
```

unless a later concrete contradiction requires a new ADR.

### 53. Implementation order isolates the evidence upgrade

Accepted implementation sequence:

```text
Slice 1
  initial design + initial repository checkpoint

Slice 2
  pre-ADR checkpoint + accepted ADR 0015

Slice 3
  Account v2 + Observation v2 dual-owner evidence contracts

Slice 4
  #19 identifiers and any proven schema-local/shared prerequisites

Slice 5
  Follow-Up

Slice 6
  Outcome

Slice 7
  Reentry

Slice 8
  Repair

Slice 9
  shared-infrastructure / cross-record integration

Slice 10
  examples + matrices + final reconciliation / validation
```

The exact slice count may change if focused validation uncovers a schema defect,
but semantic scope must remain bounded.

## Consequences

### Positive

1. Portia can represent ordinary Support Process progress-monitoring evidence
   without fabricating Events.
2. Source perspective and direct measurement remain separate from Outcome.
3. Existing Event evidence remains backward compatible.
4. Follow-Up, Outcome, Reentry, and Repair remain distinct canonical units.
5. Outcome supports positive progress, inconclusive results, recurrence, and
   adverse/unintended change without a universal score.
6. Fidelity and Outcome remain orthogonal.
7. Reentry cannot masquerade as clearance.
8. Repair cannot masquerade as remorse, forgiveness, truth, or collections.
9. Support Process review/closure remains human-controlled.
10. Future Core/Meridian publication can project stable native records without
    contaminating canonical Portia storage with academic semantics.

### Costs

1. Account/Observation require new version-2 schemas, fixtures, validators, and
   catalog entries before the four #19 families.
2. Readers/writers must understand both evidence contract versions.
3. Owner-conditioned target validation adds graph/application complexity.
4. Outcome is deliberately more verbose than a single `effective=true` flag.
5. Recurrence/no-change claims require explicit coverage and missingness.
6. Repair embedded action logic needs careful revision/correction testing.
7. Teacher-facing UI must progressively disclose these semantics rather than
   expose one giant form.

These costs are accepted because they preserve epistemic status and prevent
false certainty.

## Rejected Alternatives

### Mutate Account/Observation v1 in place

Rejected because published schema IDs are immutable.

### Create fake Events for Support Process check-ins/measurements

Rejected because it corrupts Event semantics, recurrence counts, timelines, and
analytics.

### Put raw statements/measurements directly inside Outcome

Rejected because source evidence and evaluation are different claims.

### Add separate `support_process_account@1` and `support_process_observation@1`

Rejected because the semantic units are still Account and Observation; a
versioned owner generalization is cleaner than duplicating evidence families.

### Make Outcome one mutable Support Process status

Rejected because evaluation is time/question/evidence bounded and later
evaluations must coexist.

### Add `effective=true/false` or an effectiveness percentage

Rejected because it encourages unsupported causal interpretation and flattens
missingness, fidelity, timeframe, and evidence.

### Treat no later Event as no recurrence

Rejected because absence of a record is not absence of occurrence or adequate
observation opportunity.

### Broaden Event `review@1` to Support Process

Rejected because Follow-Up + Outcome already separate review action from review
conclusion without redefining the Event judgment layer.

### Make Reentry a clearance/readiness record

Rejected because teacher-local Portia does not own medical, safety,
special-education, exclusion/admission, or legal clearance authority.

### Require apology/direct conference in Repair

Rejected because restorative/reparative participation must not be coerced by
the product model.

### Publish independent Repair Participant/Action families now

Rejected because current use cases do not demonstrate independent canonical
identity/lifecycle needs. Embedded process-local entries are sufficient.

### Let favorable Outcome automatically close Support Process

Rejected because Outcome and workflow decision are separate claims.

### Publish #19 records automatically through Core/Meridian

Rejected because publication/selection/authorization is a separate future
projection concern.

## Validation Obligations

Implementation must prove:

- Account/Observation v1 remain unchanged and valid;
- Account/Observation v2 support both owner kinds without semantic flattening;
- owner-conditioned targets resolve correctly;
- cross-version predecessor history is exact;
- no fake Event is required for Support Process evidence;
- Follow-Up scheduling/completion/result separation;
- Support Process review disposition does not auto-transition work;
- Outcome scope/timeframe/basis/result/limitations compatibility;
- recurrence coverage rules;
- no causal/effectiveness score;
- Fidelity/Outcome orthogonality;
- Reentry no-clearance semantics;
- Repair voluntary/nonjudgmental participation;
- agreement vs completion;
- no financial collections semantics;
- shared lifecycle/correction/migration/removal reuse;
- shared operation/recovery/derived reuse;
- paper/import proposed-state guardrails;
- privacy minimization;
- no academic publication semantics;
- no real student/family/staff data.

Final Issue #19 acceptance still requires:

```powershell
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

with the observed final test count recorded rather than predicted.
