# Portia Follow-Up, Outcome, Reentry, and Repair Domain Models

**Status:** Initial pre-ADR design
**Issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`
**Date:** 2026-08-12
**Expected ADR:** `0015`, if still free at ADR publication time

## 1. Purpose

Issue #19 defines Portia's downstream behavior-support layer: what follow-up was
planned and completed, what later evidence exists, what bounded human evaluation
was made from that evidence, how a return/reentry process was planned and
carried out, and what restorative or reparative process was offered, agreed,
attempted, or completed.

The accepted progression is:

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Implementation
→ Fidelity
→ Follow-Up / Outcome / Reentry / Repair
```

The arrows represent possible relationships, not mandatory record creation.

Issue #19 must preserve:

```text
scheduled Follow-Up
≠ completed Follow-Up

completed Follow-Up
≠ favorable Outcome

Account / Observation
≠ Outcome evaluation

Implementation completed
≠ Support effective

Fidelity as_planned
≠ Support effective

Support Process completed
≠ goal attained
≠ resolved
≠ causal success

later Event / recurrence
≠ intervention failure

fewer documented Events
≠ improvement without adequate observation/reporting basis

Reentry completed
≠ clearance
≠ compliance
≠ rehabilitation

Repair completed
≠ remorse
≠ forgiveness
≠ relationship restored
≠ admission of wrongdoing

temporal sequence or record linkage
≠ causation
```

The purpose is not to build a single mutable "case outcome." It is to preserve
separate, attributable records for downstream work and downstream evaluation.

## 2. Starting Repository State

Issue #19 begins after the completed and reconciled Issue #18 merge.

Exact starting anchors:

```text
pds-portia/main
0d08495557721681b11d081e91c8b416a556df8a

pds-portia branch
19-follow-up-outcome-reentry-repair-domain-models
0d08495557721681b11d081e91c8b416a556df8a

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-meridian/main (consumer context only)
9e5f9217ff2a935a98a12f7fc76ae2e74774159c
```

At the initial remote checkpoint, the Issue #19 branch and Portia `main` are:

```text
0 commits ahead
0 commits behind
```

ADR 0015 is currently unused.

The observed authoritative Portia schema-validation baseline on the exact local
Issue #19 checkout is:

```text
762 tests
93.403 seconds
OK
```

This count is recorded by the Slice 1 helper rather than assumed from the
pre-merge Issue #18 test count.

## 3. Post-#18 Semantics That #19 Must Not Reopen

Accepted ADR 0014 establishes:

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

Support Process workflow state, Support/Intervention plan state,
Implementation execution state, and Fidelity result are already separate
semantic dimensions.

Issue #19 therefore must not retrofit Outcome semantics into those records.

Examples:

```text
Support Process workflow_state = completed
```

means only that the workflow is no longer actively carried forward in the v1
workflow.

```text
Support plan_state = completed
```

means only that the plan's operational lifecycle completed.

```text
Implementation execution_state = completed
```

means only that one actual occurrence/interval completed.

```text
Fidelity result = as_planned
```

means only that the evaluated implementation matched the identified plan to the
degree represented by the Fidelity record.

None of those values establishes that a Goal was met, that behavior changed,
that recurrence stopped, that a relationship was repaired, or that a particular
Response/Support/Intervention caused a later result.

## 4. Initial Ownership Decision: Work-Local Canonical Children

The leading design is to model:

```text
Follow-Up
Outcome
Reentry
Repair
```

as separate canonical Portia child records, not new top-level work kinds.

Candidate canonical paths are:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    follow_up/<follow_up_id>.json
    outcome/<outcome_id>.json
    reentry/<reentry_id>.json
    repair/<repair_id>.json
```

Eligible work owners are expected to be:

```text
event
support_process
```

This follows the already-published `communication@1` precedent for one
Portia-work-local family capable of Event or Support Process ownership.

The proposed owner envelope is therefore expected to include:

```text
module_id = portia
class_id
work_kind = event | support_process
work_id
```

with application validation enforcing:

```text
work_kind = event
→ work_id resolves as the exact/current eligible Event owner

work_kind = support_process
→ work_id resolves as the exact/current eligible Support Process owner
```

No new top-level `case`, `outcome_process`, `reentry_process`, or
`repair_process` work kind is currently justified.

ADR 0015 must confirm this after graph examples are tested.

## 5. Targeting Reuses Existing Closed Families

No new generic #19 target family is initially justified.

For Event-owned records, reuse:

```text
portia_target_ref@1
```

which already supports:

```text
event
event_participant
event_participants
```

For Support-Process-owned records, reuse:

```text
support_process_target_ref@1
```

which already supports:

```text
support_process
support_process_participant
support_process_participants
```

Application validation must enforce logical-human uniqueness for plural targets
rather than relying only on JSON-object uniqueness.

The target must not be inferred from:

- first linked Event;
- first student;
- first Support Process Participant;
- Follow-Up owner;
- plan provider;
- Communication recipient;
- Goal target;
- prior Outcome.

Target membership does not establish participation, agreement, fault,
responsibility, authority, or effect.

## 6. Exact Historical References Reuse Existing Infrastructure

Issue #19 should initially reuse:

```text
exact_portia_work_ref@1
exact_portia_work_record_ref@1
exact_local_record_ref@1
```

`exact_portia_work_record_ref@1` already identifies:

```text
exact work owner
+
exact local child-record kind / ID / contract version
```

and is specifically designed not to silently follow correction, migration,
consolidation, ownership correction, or successor history.

This is sufficient for exact references to:

```text
Account
Observation
Review
Classification
Hypothesis
Determination
Response
Communication
Support Process Participant
Need
Goal
Support
Intervention
Implementation
Fidelity
and later #19 child records
```

No new generic exact reference family is authorized at this stage.

If Outcome requires role-bearing evidence references, ADR 0015 should first
evaluate a schema-local role + `exact_portia_work_record_ref@1` composition.
A public `outcome_evidence_ref@1` should be published only if independent stable
reuse is demonstrated.

## 7. Candidate Identifier Inventory

Repository code search found no collisions for these candidate prefixes:

```text
Follow-Up  fup_
Outcome    out_
Reentry    ren_
Repair     rpr_
```

The corresponding candidate public identifiers are:

```text
portia_follow_up_id@1
portia_outcome_id@1
portia_reentry_id@1
portia_repair_id@1
```

These prefixes are provisional until ADR 0015 accepts them and schema-catalog
collision checks are repeated immediately before publication.

The design should not add generic IDs for:

```text
progress
effectiveness
closure
success
engagement
compliance
remorse
forgiveness
readiness
case
party
task
agreement
facilitator
```

## 8. Follow-Up Semantic Unit

Candidate public family:

```text
follow_up@1
```

One Follow-Up represents:

> One bounded, explicitly owned downstream check, review, coordination action,
> or follow-up obligation associated with one Event or Support Process.

A Follow-Up is not:

```text
Account
Observation
Review
Communication
Outcome
Support / Intervention
Implementation
Fidelity
Determination
```

The initial contract should evaluate:

```text
schema_version
record_type = follow_up
module_id = portia
class_id
work_kind
work_id
follow_up_id
status
target
owner
purpose
planned_timing
workflow_state
completed_at?
completion_summary?
related_record_refs?
supersedes?
creation_source
created_at
created_by
updated_at
updated_by
```

Exact final fields remain ADR work.

### 8.1 Follow-Up owner

Follow-Up requires one explicit responsible human.

Owner is distinct from:

```text
created_by / updated_by
target
Support/Intervention provider
Implementation provider
Outcome evaluator
institutional authority
```

For a Support Process-owned Follow-Up, an exact Support Process Participant
reference is the preferred leading design because it preserves process-local
identity and exact historical membership.

For Event-owned Follow-Up, `represented_human_attribution@1` is the leading
candidate unless a more restrictive existing exact Actor/participant model is
required by the workflow.

Owner representation does not prove:

```text
employment
licensure
case-manager status
legal responsibility
institutional authority
```

Current-use unidentified owners are not acceptable.

### 8.2 Follow-Up purpose

Initial closed vocabulary to evaluate:

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

Purpose does not determine result:

```text
goal_review
≠ goal met

family_or_support_person_check_in
≠ family participated

repair_check
≠ repair completed
```

### 8.3 Follow-Up timing and workflow state

The contract must distinguish planned timing from actual completion.

A bounded timing union should support at least:

```text
date_only
exact_time
window
```

without forcing false timestamp precision.

Candidate workflow states:

```text
scheduled
in_progress
completed
cancelled
unable_to_complete
```

Canonical lifecycle remains separately expected to be:

```text
proposed
active
invalidated
superseded
```

`overdue` should be derived from current time + canonical planned timing +
workflow state, not stored as authoritative domain state.

Required semantics:

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

## 9. Follow-Up Produces or Links Records; It Does Not Absorb Them

A completed Follow-Up may exact-link records created or reviewed through the
follow-up action.

Examples:

```text
student check-in
→ Follow-Up + Account when a substantive Event-local perspective exists

family call
→ Follow-Up + Communication

direct observation
→ Follow-Up + Observation when a legitimate Event owner exists

goal review
→ Follow-Up + Outcome

reentry check
→ Follow-Up + later Account/Observation/Outcome as applicable
```

The Follow-Up should not copy those records' substantive payload into itself.

This preserves:

```text
workflow action
≠ source evidence
≠ evaluation
```

## 10. Critical Pre-ADR Question: Account and Observation Are Event-Local

The existing published contracts create a real #19 architecture pressure point.

`account@1` is Event-local:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

`observation@1` is also Event-local:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

They cannot currently be stored directly as Support Process child records.

At the same time, #19 must preserve:

```text
substantive perspective
→ Account

direct/instrumented measurement
→ Observation

Outcome
→ evaluation based on evidence
```

rather than putting unrestricted source evidence directly into Outcome.

### 10.1 Initial conservative rule

Issue #19 must **not** broaden Account or Observation merely for convenience.

The leading rule before ADR 0015 is:

1. Event-owned Follow-Up may create/reference Event-local Account/Observation
   normally.
2. Support Process-owned Follow-Up/Outcome may exact-reference legitimate
   Event-owned Account/Observation records across work using
   `exact_portia_work_record_ref@1`.
3. A real-world support check-in/measurement occurrence may be represented by an
   Event only if that occurrence honestly satisfies Event semantics.
4. Portia must not create a fake Event solely to obtain storage for an Account or
   Observation.
5. Outcome may carry bounded evaluation and evidence references but must not
   become a substitute raw Account/Observation container.
6. If concrete Support Process progress-monitoring examples cannot be
   represented honestly without Support-Process-local Account/Observation, that
   is a genuine wire requirement. ADR 0015 must then evaluate explicit new
   Account/Observation versions rather than silently changing v1.

### 10.2 Why this is intentionally unresolved in Slice 1

Publishing `account@2` / `observation@2` with dual Event/Support Process ownership
would broaden a foundational evidence semantic boundary and create:

- new owner-resolution rules;
- target-union changes;
- cross-version reader behavior;
- migration/compatibility questions;
- fixture/test expansion beyond the four #19 families;
- downstream assumptions about Event-local evidence.

That cost is justified only by demonstrated examples, not convenience.

ADR 0015 must resolve this before Outcome schemas are finalized.

## 11. Outcome Semantic Unit

Candidate public family:

```text
outcome@1
```

One Outcome represents:

> One bounded, attributable human evaluation of one defined downstream question
> for an explicit target and timeframe, based on explicit evidence/context.

Outcome is not:

```text
raw Account
raw Observation
mutable progress log
Fidelity
workflow completion
scientific causal effect
Grade
standards proficiency
student identity label
```

Initial fields to evaluate:

```text
schema_version
record_type = outcome
module_id = portia
class_id
work_kind
work_id
outcome_id
status
target
evaluator
scope
timeframe
basis
result
limitations?
summary?
supersedes?
creation_source
created_at
created_by
updated_at
updated_by
```

## 12. Outcome Evaluator

Outcome requires explicit human attribution.

Evaluator is distinct from:

```text
created_by / updated_by
evidence source
Follow-Up owner
Support/Intervention provider
Implementation provider
Fidelity evaluator
institutional authority
```

Support Process-owned Outcome should preferably use an exact Support Process
Participant evaluator when practical.

Event-owned Outcome should evaluate whether
`represented_human_attribution@1` is sufficient.

Current-use unidentified evaluators are prohibited.

Evaluator identity does not prove professional or institutional authority.

## 13. Outcome Scope / Question

Initial closed scope to evaluate:

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

`other` requires bounded detail.

Each scope must define its required references and compatible result family.

Examples:

```text
goal_status
→ exact Goal + bounded timeframe + basis + goal-status result

observed_change
→ explicit target/measure question + comparison basis + direction result

recurrence_review
→ explicit recurrence question + coverage + result

reentry_status
→ exact Reentry + basis + result

repair_status
→ exact Repair + basis + result
```

Scope must not be inferred from free text or first reference.

## 14. Outcome Timeframe

Every Outcome requires explicit temporal scope.

Initial union:

```text
point_in_time
bounded_period
```

or an equally bounded representation.

Rules:

- chronology validates;
- later assessment for a later period is normally a **new Outcome**;
- later favorable Outcome does not rewrite an earlier inconclusive/unfavorable
  Outcome;
- Outcome does not silently remain true forever;
- missing later Outcome does not imply the prior result continues;
- `created_at` cannot substitute for unknown evaluation time.

This distinction is essential to keeping longitudinal evaluation as history
rather than one mutable status.

## 15. Goal-Status Outcome

`goal_status` exact-links one `support_goal@1`.

Candidate result vocabulary:

```text
met
partially_met
not_met
unable_to_determine
not_applicable
```

Rules:

```text
met
→ bounded to the stated timeframe

partially_met
→ not an invented percentage

not_met
→ not student failure / defiance / noncompliance

unable_to_determine
→ missing/insufficient evidence, not failure
```

Goal planned criteria and measurement approach may guide evaluation but never
establish attainment automatically.

No universal goal-progress percentage.

## 16. Observed Change and Positive Progress

Candidate result vocabulary for `observed_change`:

```text
improved
no_clear_change
mixed
worsened
unable_to_determine
not_applicable
```

Outcome must state what defined target/measure changed and on what evidence.

Acceptable examples include:

```text
Use of the agreed break-request strategy increased across the defined
observation periods.

Time outside the assigned area decreased relative to the identified baseline.

Participation was mixed across the two observed settings.
```

Avoid:

```text
student improved
better attitude
more compliant
behavior score +12
```

Specific positive source facts remain Account/Observation evidence.

## 17. Raw Measurement Remains Observation Evidence

The existing `observation@1` already supports bounded quantitative measurement
with explicit measurement method/window/denominator/unit semantics.

Issue #19 should not duplicate that measurement model inside Outcome.

Outcome should evaluate exact measurement evidence where available.

If a derived comparison value is persisted, ADR 0015 must define:

- exact source refs;
- compatible measure kinds;
- numerator/denominator or scale where applicable;
- observation windows;
- missingness/coverage;
- comparison semantics.

Never convert:

```text
no Observation
→ zero

no Event
→ no recurrence

blank
→ no change
```

## 18. Outcome Basis and Evidence Roles

Outcome needs explicit basis.

Initial schema-local evidence roles to evaluate:

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

The leading locator is:

```text
exact_portia_work_record_ref@1
```

for Portia-native records, plus existing module-qualified exact refs where
legitimate sibling context is necessary.

Do not automatically broaden `judgment_evidence_ref@1`. Its accepted semantics
belong to the judgment layer.

No:

```text
evidence weight
credibility score
truth flag
causal weight
```

## 19. Limitations and Missingness

Outcome must represent incomplete evidence honestly.

Initial limitations to evaluate:

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

`other` requires detail.

Important distinctions:

```text
unable_to_determine
≠ failure
≠ no change

source unavailable
≠ source declined

fidelity unknown
≠ poor fidelity

no recurrence observed within limited coverage
≠ proof of no recurrence
```

ADR 0015 must decide which results require at least one limitation.

## 20. Recurrence Is an Evaluation With Coverage, Not a Link Count

A later documented Event can mean:

- recurrence;
- changed opportunity/exposure;
- changed definition;
- easier reporting;
- closer monitoring;
- different setting;
- changed documentation expectations;
- incomplete historical capture.

Therefore:

```text
later linked Event
≠ automatic recurrence conclusion

recurrence observed
≠ intervention failure

no later Event found
≠ no recurrence
```

`recurrence_review` must require:

- defined recurrence question or operational target;
- bounded timeframe;
- observation/reporting coverage;
- exact basis/context;
- explicit result.

Initial result vocabulary:

```text
recurrence_observed
no_recurrence_observed_within_defined_coverage
unable_to_determine
not_applicable
```

There should be no bare `no_recurrence`.

No recurrence forecast or risk score.

## 21. Causal Interpretation Is Prohibited in Ordinary Outcome v1

Portia may represent observed temporal change and a bounded human
response-to-support evaluation. Ordinary linked records do not establish a
scientific causal effect.

Outcome v1 should reject or omit fields such as:

```text
caused_by
causal_effect
treatment_effect
percent_effective
intervention_caused_improvement
response_prevented_recurrence
```

Preferred semantics are:

```text
observed change
goal status
recurrence review
response-to-support review
limitations
```

with exact evidence and attribution.

If an external authorized research/evaluation process makes a causal claim,
Portia may preserve a minimal inert/exact external reference where an accepted
contract supports it. Portia does not convert that into a teacher-local causal
finding.

No automated causal inference.

## 22. Resolving "Effectiveness"

ADR 0014 intentionally deferred effectiveness to #19.

The leading design is **not**:

```text
effective = true | false
effectiveness_percent = 82
```

Instead `support_response_review` should represent a bounded human evaluation
such as:

```text
progress_observed
no_clear_progress
mixed
worsening_observed
unable_to_determine
not_applicable
```

from explicit evidence and limitations.

This states the observed response during a defined period without claiming a
scientifically established treatment effect.

## 23. Fidelity and Outcome Remain Separate

Outcome may exact-link Fidelity.

Valid combinations include:

```text
as_planned Fidelity + favorable Outcome
→ high implementation match and favorable downstream evaluation

as_planned Fidelity + unfavorable/inconclusive Outcome
→ high plan match without favorable downstream result

not_as_planned Fidelity + favorable Outcome
→ favorable downstream result despite lower plan-match evidence

Fidelity unavailable
→ Outcome interpretation may be limited
```

None proves causation.

Implementation count also does not establish complete dosage unless capture
coverage is explicit.

## 24. Adverse or Unintended Change

Issue #19 must represent adverse/unintended change without automatically
attributing causation.

The distinction is:

```text
adverse/unintended condition observed or reported during the period
```

versus:

```text
the intervention caused the condition
```

Substantive source description remains Account/Observation where legitimate.

Clinical, self-harm, threat, abuse, discrimination, special-education, or other
restricted investigation details remain outside ordinary Outcome payloads.

## 25. Support Process Review Does Not Broaden `review@1`

The existing `review@1` is Event-local and judgment-layer specific.

A Support Process review should initially be represented as:

```text
Follow-Up
  purpose = support_process_review / goal_review /
            implementation_review / fidelity_review
```

which may produce/reference:

```text
Outcome
Account
Observation
Communication
later Follow-Up
```

This preserves:

```text
review action happened
≠ review conclusion
```

No generic Support Process `review@2` is currently justified.

If concrete use cases cannot fit Follow-Up + Outcome, ADR 0015 must document the
incompatibility before introducing another review family/version.

## 26. Support Process Closure Is an Explicit Human Workflow Decision

Support Process must not auto-complete/discontinue because:

- planned end date passed;
- all plan rows completed;
- Goal was met;
- no recent Events were found;
- Fidelity was `as_planned`;
- one favorable Outcome exists.

A completed Support Process review Follow-Up may carry a bounded human
disposition such as:

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

ADR 0015 must decide whether this disposition belongs on Follow-Up completion or
another narrow workflow object.

The leading design keeps it on the completed Follow-Up because it represents
the next workflow action chosen at review, not a new evaluative semantic unit.

Disposition is not Outcome and not institutional Determination.

A resulting Support Process workflow-state update remains an explicit,
revision-aware update.

Material Support/Intervention adaptation continues to use ADR 0014
`plan_adapted` successor semantics.

## 27. Reentry Semantic Unit

Candidate public family:

```text
reentry@1
```

One Reentry represents:

> One bounded teacher-local plan/process for supporting return to an ordinary
> educational setting, activity, relationship context, or classroom workflow
> after a represented interruption, removal, absence, conflict, or other
> relevant context.

Reentry is not:

```text
medical clearance
threat-assessment clearance
special-education placement authority
legal permission to attend
proof prior exclusion was valid
punishment
apology requirement
behavioral contract
readiness score
```

Initial fields to evaluate:

```text
schema_version
record_type = reentry
module_id = portia
class_id
work_kind
work_id
reentry_id
status
target
coordinator
context
planned_return
planned_elements
support_refs?
workflow_state
completed_at?
supersedes?
creation_source
created_at
created_by
updated_at
updated_by
```

## 28. Reentry Context and Coordinator

Reentry may exact-link context from:

```text
Event
Determination
Response
Support Process
Communication
restricted/external process reference
other
```

The context does not establish correctness of the prior action.

Coordinator must be explicit and distinct from:

```text
created_by / updated_by
institutional admission/exclusion authority
clinical authority
threat-assessment authority
```

Current-use unidentified coordinators are prohibited.

Restricted process details must not be copied into ordinary Reentry payload.

## 29. Reentry Planning Does Not Duplicate Implementation

Reentry may reference existing Support/Intervention plans.

Potential planning categories:

```text
orientation_or_check_in
schedule_or_environment
academic_access
support_handoff
relationship_reconnection
communication
other
```

Actual actions remain their existing canonical families:

```text
Response
Communication
Implementation
Follow-Up
Repair
```

Reentry does not contain pseudo-Implementation arrays.

Candidate workflow states:

```text
planned
active
completed
cancelled
unable_to_complete
```

with canonical lifecycle separately:

```text
proposed
active
invalidated
superseded
```

Required semantics:

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

Post-reentry review is a separate Follow-Up.

Portia must not turn optional teacher-local Reentry steps into unauthorized
barriers to access.

## 30. Repair Semantic Unit

Candidate public family:

```text
repair@1
```

One Repair represents:

> One bounded teacher-local restorative or reparative process intended to
> address represented impact, relationship/community needs, or agreed
> restorative actions without converting participation into admission,
> punishment, or character judgment.

Repair is not:

```text
Response
Communication
Determination
Support
Reentry
Outcome
institutional restorative authority
financial collections
```

It does not prove the underlying allegation.

## 31. Repair Roles and Participation

Avoid forced offender/victim labels.

Initial process-local roles to evaluate:

```text
affected_person
person_addressing_impact
supporter
facilitator
community_participant
other
```

Initial participation states:

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

`unknown` should be historical/import-only where current-use semantics require
certainty.

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

No engagement/cooperation/remorse/sincerity score.

Affected-person participation, direct meeting, apology, or disclosure must not
be mandatory.

## 32. Repair Focus Does Not Rewrite Event Evidence

Repair exact-links relevant Event/Determination/Account/Observation context and
carries only bounded process focus.

It must not create one mutable "official story."

If participants make substantive claims about impact/needs, preserve those as
attributed source records when the evidence model can honestly represent them.

Repair cannot overwrite conflicting Accounts or create a new factual
Determination.

## 33. Repair Agreement / Action Modeling Is an ADR Decision

Potential agreed actions include:

```text
return_or_restore_property
repair_or_replace_property
restorative_action
community_or_relationship_action
follow_up_conversation
other
```

ADR 0015 must decide whether these are:

1. bounded objects within `repair@1`; or
2. independent `repair_action@1` records.

The leading design is **embedded bounded actions** unless examples demonstrate
that actions need independent identity, correction, deadlines, completion
history, or external references.

Do not publish `repair_action@1` simply to mirror UI checklist rows.

Whichever choice is made must distinguish:

```text
agreed action
≠ completed action
```

Blank paper/template rows are not agreements.

## 34. Restitution / Completion Boundaries

Portia may represent bounded restorative completion such as:

```text
property returned
property restored/replaced
agreed nonfinancial action completed
```

Portia must not become:

```text
accounts receivable
debt ledger
payment processor
collections system
```

If an authoritative financial obligation exists elsewhere, preserve a minimal
reference rather than recreating its accounting semantics.

Inability to pay is not behavioral noncompliance.

Required meanings:

```text
agreed action completed
≠ remorse
≠ forgiveness
≠ relationship restored
≠ rehabilitation
≠ recurrence prevented
```

Later relationship change is evaluated by a separate Outcome.

## 35. Later Assessment Is New History, Not Correction

Example:

```text
Outcome week 2 = no_clear_change
Outcome week 6 = improved
```

Both can remain valid.

Supersession is used when correcting/replacing the same represented claim, not
for ordinary later reassessment.

This same principle applies to later Follow-Up/Reentry/Repair review records.

Exact older refs remain exact.

## 36. Lifecycle and Correction

The leading canonical lifecycle for all four #19 families is:

```text
proposed
active
invalidated
superseded
```

Domain workflow/evaluation state remains separate.

`invalidated` never means:

```text
unfavorable Outcome
Follow-Up cancelled
Reentry unable to complete
Repair declined
recurrence
goal not met
disagreement
workflow closure
```

The leading v1 policy is **no Amendment paths** for:

```text
Follow-Up
Outcome
Reentry
Repair
```

unless ADR 0015 identifies a truly safe nonmaterial path.

Ordinary revision-aware progression of an active workflow may be allowed where
the same factual process is continuing.

Material correction of terminal factual/evaluative state uses successor/history.

## 37. Candidate Successor Reasons

Follow-Up:

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

Outcome:

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

Reentry:

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

Repair:

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

`other` requires detail.

Final vocabularies are ADR decisions.

## 38. Shared Lifecycle / Recovery Infrastructure Is Reused

Issue #19 should reuse, where semantically sufficient:

```text
lifecycle_transition@1
lifecycle_history_correction@1
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

No #19-specific operation, lock, Quarantine, Integrity Finding, source-snapshot,
or derived-generation fork is currently justified.

Potential coordinated operations include:

- Follow-Up completion + linked Communication/Outcome;
- Follow-Up review + Support Process workflow-state update;
- Outcome + subsequent plan adaptation;
- Reentry completion + later Follow-Up;
- Repair action completion + later Outcome;
- successor activation;
- ownership correction;
- migration/removal;
- derived rebuild.

Canonical domain records remain distinct from operation state.

## 39. Derived State Is Nonauthoritative

Derived views may support:

```text
due Follow-Ups
overdue Follow-Ups
recent/latest Outcome by question
support-review queue
reentry check queue
repair check queue
participant timeline
recurrence-review candidates
```

Required meanings:

```text
missing derived row
≠ no canonical record

stale queue
≠ Follow-Up cancelled

latest Outcome
≠ deletion of earlier Outcomes

zero counted Events
≠ no recurrence without coverage
```

Derived state must be rebuildable, privacy-minimized, and authorization-scoped.

## 40. Cross-Year Continuity

#19 records remain under their exact owning Event/Support Process.

When Support Process work continues into a new school year:

- prior #19 records remain with the predecessor Support Process;
- new work uses the #18 successor Support Process where appropriate;
- prior Outcomes are not copied as current;
- prior Reentry/Repair is not reopened automatically;
- exact refs remain exact;
- longitudinal history is derived through explicit links.

Issue #19 must not create an indefinite student Outcome dossier.

## 41. Paper and Import Boundary

Issue #20 remains authoritative for PDS2 routing, paper return, interpretation,
import batches, and current-use review gates.

Required distinctions:

```text
blank Follow-Up form
≠ completed Follow-Up

preprinted Outcome scale
≠ Outcome evaluation

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

Paper/import-derived substantive #19 records should remain proposed until Issue
#20 review semantics permit current use.

Issue #19 must not redefine Core PDS2 routes/pages/source retention.

## 42. Privacy Minimization

#19 may contain sensitive family, conflict, restorative, disability-support, or
exclusion context.

Native contracts should require:

- opaque IDs;
- bounded summaries;
- exact refs instead of copied narrative where sufficient;
- no raw Actor contact values;
- no unrestricted restorative transcript;
- no clinical/counseling notes;
- no detailed threat/abuse/investigation content;
- no family/student engagement score;
- no remorse/character labels;
- privacy-minimized operational/derived metadata;
- no automatic publication/export.

Issue #21 remains authoritative for complete redaction/export/retention/Sunset
policy.

Ordinary Reentry may preserve a minimal external/restricted status reference
where authorized, but it must not copy restricted payload or decide medical or
safety clearance.

## 43. Automation Boundary

Software may:

- validate references;
- validate chronology;
- create reminders from human-authored schedules;
- surface due/overdue work;
- calculate transparent descriptive comparisons from compatible explicit
  measures;
- identify missing evidence/coverage;
- show exact Implementation/Fidelity context;
- prepare drafts;
- rebuild derived views.

Software must not automatically:

- complete Follow-Up from time passage;
- create Outcome from counts;
- infer improvement from fewer reports;
- infer deterioration from more reports;
- infer recurrence failure;
- infer causation/effectiveness;
- choose Goal status;
- infer Fidelity;
- infer compliance/engagement/motivation/remorse/attitude/risk;
- infer family engagement;
- infer provider competence;
- close/adapt/intensify/fade Support;
- complete Reentry from a date;
- complete Repair from Communication;
- infer forgiveness/relationship restoration;
- publish intervention/outcome records.

Human attribution remains explicit.

## 44. Core v0.6 Publication Boundary

Core v0.6 provides:

```text
publication kind:
  intervention_record_set

intervention capabilities:
  intervention_history
  intervention_status
  intervention_outcomes
```

Core leaves native intervention/outcome semantics producer-owned.

Issue #19 should stabilize Portia-native Outcome identity and exact references so
a future privacy-minimized publication projection can be added later.

Issue #19 does **not** implement:

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

Discoverability is not authorization.

## 45. Meridian and Portfolio Boundaries

Portia must not depend on Meridian.

Meridian remains a downstream consumer of authorized producer publications and
must preserve producer-native semantics.

Portia Outcome is not:

```text
standards proficiency
Grade evidence
Grade item
automatic Grade contribution
```

#19 records also do not automatically enter Vitrine/portfolio.

Any future reporting/portfolio projection must be deliberate, privacy-governed,
purpose-specific, and separately authorized.

## 46. Public Contract Inventory to Evaluate in ADR 0015

Expected additive inventory:

```text
portia_follow_up_id@1
follow_up@1

portia_outcome_id@1
outcome@1

portia_reentry_id@1
reentry@1

portia_repair_id@1
repair@1
```

Potential but not yet justified:

```text
outcome_evidence_ref@1
repair_action@1
```

No public v1 contract is currently justified for:

```text
progress
effectiveness
closure
success
engagement
compliance
remorse
forgiveness
readiness
case
party
task
agreement
facilitator
```

Schema-local compositions are preferred until stable independent reuse is
demonstrated.

## 47. ADR 0015 Decisions That Must Be Resolved Before Schemas

ADR 0015 should explicitly decide:

1. whether all four #19 families are work-local canonical children;
2. whether all four permit Event and Support Process ownership;
3. exact owner/class/work-ID application invariants;
4. whether existing Event/Support Process target families are sufficient;
5. final identifier prefixes;
6. Follow-Up owner representation for Event vs Support Process ownership;
7. Follow-Up timing union and workflow states;
8. whether completed Follow-Up carries workflow disposition;
9. exact related-record reference family for Follow-Up;
10. how Support Process-owned Follow-Up/Outcome handles the current Event-local
    Account/Observation limitation;
11. whether any Account/Observation version bump is actually required;
12. Outcome scope/question discriminators;
13. Outcome timeframe representation;
14. Outcome basis/evidence roles and whether a public evidence-ref contract is
    warranted;
15. result vocabularies per Outcome scope;
16. limitation requirements;
17. conservative recurrence coverage semantics;
18. response-to-support semantics without universal effectiveness;
19. Support Process review without broadening `review@1`;
20. Reentry context/coordinator/planning/workflow model;
21. Repair roles/participation model;
22. embedded Repair actions versus `repair_action@1`;
23. lifecycle/workflow/correction/no-Amendment policy;
24. successor reason vocabularies;
25. cross-year behavior;
26. paper/import restrictions;
27. automation restrictions;
28. Core/Meridian publication boundary.

No #19 public schema should be published until these are resolved.

## 48. Proposed Implementation Sequence After ADR

A likely focused-slice sequence is:

```text
Slice 1
  initial design + repository checkpoint

Slice 2
  pre-ADR drift check + ADR 0015

Slice 3
  identifiers + any justified shared #19 primitive

Slice 4
  Follow-Up

Slice 5
  Outcome

Slice 6
  Reentry

Slice 7
  Repair

Slice 8
  shared infrastructure / cross-record integration

Slice 9
  examples + matrices + final reconciliation / validation
```

The sequence may change if ADR 0015 proves that Account/Observation need a new
version. If so, evidence-model work must be isolated and validated before
Outcome.

## 49. Validation Plan

Every public family should receive:

- Draft 2020-12 schema validation;
- valid fixtures;
- structural-invalid fixtures;
- application-invalid fixtures;
- focused tests;
- graph-resolution tests;
- lifecycle/correction tests;
- migration/removal compatibility;
- operation/derived reuse tests;
- paper/import guardrails;
- privacy/automation guardrails;
- documentation consistency.

Final acceptance must run:

```powershell
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

The observed final test count will be recorded rather than predicted.

At least 40 synthetic examples are required.

## 50. Initial Risk Register

### Risk A — Event-local Account/Observation ownership

This is the main architecture risk identified before ADR. Do not solve it with
silent duplication or a fake Event.

### Risk B — Outcome becoming a universal mutable status

Outcome must remain bounded by question/timeframe/evaluator/evidence.

### Risk C — correlation becoming causal "effectiveness"

The model must prohibit automatic causal interpretation from temporal linkage,
counts, or Fidelity.

### Risk D — recurrence as an absence claim

No later Event is not proof that recurrence did not occur. Coverage must be
explicit.

### Risk E — Reentry becoming clearance

Teacher-local reentry must not encode medical/safety/legal admission authority.

### Risk F — Repair becoming coerced compliance

Repair must preserve decline/withdrawal and cannot infer remorse, forgiveness,
or truth.

### Risk G — Support Process auto-closure

Outcome and workflow disposition must remain separate; closure is explicit and
human-controlled.

### Risk H — future publication driving native design

Core/Meridian compatibility is considered but cannot dictate native Portia
semantics or create academic grading fields.

## 51. Initial Conclusion

The post-#18 architecture provides sufficient shared identity, target, exact
reference, lifecycle, correction, migration/removal, operation, integrity, and
derived-state infrastructure for #19.

The leading design is:

```text
Event or Support Process owner
  ├─ Follow-Up
  ├─ Outcome
  ├─ Reentry
  └─ Repair
```

with:

```text
existing Event target family
existing Support Process target family
existing exact work / work-record references
existing represented-human attribution
existing shared lifecycle and operational infrastructure
```

The design should add only the four new semantic families plus independently
justified primitives.

The principal unresolved ADR question is how Support Process-owned downstream
work references substantive perspective/direct measurement while Account and
Observation remain Event-local. That issue must be demonstrated and resolved
honestly before Outcome wire contracts are finalized.
