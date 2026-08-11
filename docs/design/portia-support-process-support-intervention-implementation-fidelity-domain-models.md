# Portia Support Process, Support, Intervention, Implementation, and Fidelity Domain Models

**Status:** Accepted architecture — ADR 0014
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#18 — Define Support Process, Support, Intervention, implementation, and fidelity contracts`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-10
**Branch:** `18-support-process-support-intervention-implementation-fidelity`
**Decision:** ADR 0014 accepted

## 1. Purpose

This document defines the accepted architecture for Portia's longitudinal
teacher-local support layer.

The accepted record progression is:

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

The arrows identify possible relationships. They do not require every Event or
Support Process to progress through every family.

Issue #18 must preserve four separate factual/judgment layers:

```text
planned activity
≠ actual implementation

actual implementation
≠ fidelity / implementation quality

fidelity / implementation quality
≠ Outcome / effectiveness

operational completion
≠ success / resolution
```

The central semantic units are accepted as:

```text
Support Process
= one bounded class-owned longitudinal support workflow

Support
= one planned assistance/strategy with bounded need, target, provider, and
  schedule semantics that may legitimately be less prescriptive or as-needed

Intervention
= one deliberately structured, goal-linked plan with explicit implementation
  parameters and an expectation of repeated implementation/monitoring

Implementation
= one bounded occurrence, attempt, or actual implementation interval of one
  exact Support or Intervention

Fidelity
= one attributed evaluation of how closely one exact Implementation, bounded
  implementation set, or bounded implementation interval matched an exact plan
```

This issue does not define Outcome/effectiveness, IEP/504/BIP/FBA authority,
clinical treatment, diagnosis, district service authorization, academic Grade
semantics, or Core publication.

---

## 2. Governing Repository Baseline

Initial Issue #18 comparison:

```text
pds-portia/main:
5898ad79a7d405dc1e23b94753a0eeba793c8e72

18-support-process-support-intervention-implementation-fidelity:
5898ad79a7d405dc1e23b94753a0eeba793c8e72

comparison:
identical
0 commits ahead
0 commits behind
```

Current Core anchor:

```text
pds-core/main:
6c507213618b68a6dd3ea096e1a898201ff029e6
```

Issue #17 is therefore fully merged before Issue #18 begins, and Core remains at
the v0.6 integration checkpoint named by the ticket.

No initial Portia or Core drift requires a contract change.

---

## 3. Governing Contracts

Issue #18 is subordinate to the accepted Portia foundation through ADR 0013.

Important existing contracts include:

```text
event@2
event_participant@3
event_participant_role@3
work_relationship@2

portia_support_process_id@1
portia_work_ref@1
exact_portia_work_ref@1
portia_work_record_ref@1
exact_portia_work_record_ref@1
local_record_ref@1
exact_local_record_ref@1
module_work_record_ref@1

portia_target_ref@1
support_process_target_ref@1
portia_local_work_target@1

actor@1
actor_contact_point@1
actor_student_relationship@1
represented_human_attribution@1
attribution_agent@1

account@1
observation@1
review@1
classification@1
hypothesis@1
determination@1
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

Published schemas remain immutable.

Existing contracts must not be broadened merely because their wire shapes are
convenient.

---

## 4. Governing Principles

1. Support planning is not evidence that a prior Event occurred as alleged.
2. A Need is not a diagnosis, disability determination, risk label, or permanent
   student trait.
3. A Goal is an intended future condition, not proof of current deficit or later
   attainment.
4. A Support/Intervention plan is not proof that implementation occurred.
5. A calendar/reminder occurrence is not Implementation.
6. Implementation is not fidelity.
7. Implementation count is not fidelity.
8. Fidelity is not effectiveness or Outcome.
9. Fidelity is not student compliance, family engagement, or provider competence.
10. Provider/participant identity is not institutional authorization.
11. Family relationship is not educational decision authority or disclosure
    permission.
12. Several linked Events do not automatically establish pattern, cause,
    behavioral function, diagnosis, or risk.
13. Event-local Hypotheses remain tentative and do not automatically select an
    Intervention.
14. A Response referral/handoff does not prove downstream service delivery.
15. A Communication does not prove implementation, consent, delivery, or
    participation.
16. Operational completion does not imply effectiveness, resolution, or goal
    attainment.
17. Material correction or adaptation preserves the prior representation.
18. Exact historical references never silently follow successors.
19. Cross-year continuity is not migration or ownership correction.
20. Derived histories and implementation summaries are nonauthoritative and
    cannot prove absence when capture/discovery coverage is incomplete.
21. Automation may organize and validate but must not choose an Intervention,
    infer fidelity, or infer Outcome.
22. Support data remains privacy-sensitive and must not automatically publish to
    Core, Meridian, Vitrine, or another module.

---

# 5. Support Process Is the Second Initial Portia Work Kind

One Support Process should represent:

> One bounded, class-owned teacher-local workflow that groups explicit
> participants, support needs, goals, planned Supports and/or Interventions,
> actual Implementation history, optional Fidelity evaluations, and later
> Outcome references without becoming an indefinite student dossier.

The existing work identifier is already authoritative:

```text
sup_<opaque-id>
portia_support_process_id@1
```

Accepted public root contract:

```text
support_process@1
```

Canonical storage should use the already-established work root:

```text
classes/<class_id>/modules/portia/work/<support_process_id>/
  work.json
  records/
  attachments/
  pages/
  routes/
  history/
  derived/
  exports/
```

The Support Process identifier carries no student, diagnosis, intervention,
provider, status, tier, school year, or date meaning.

Every Support Process has exactly one owning Core class.

The owning class establishes canonical storage and current class/work context.
Cross-class participants remain complete roster-qualified references and do not
split ownership.

A Support Process must not be owned by one roster student or Actor merely to make
student histories convenient. Student-specific and cross-process histories are
derived.

---

## 6. Support Process Root Shape

The root should remain intentionally small.

Accepted root fields are:

```text
schema_version
record_type = portia_work
work_kind = support_process
module_id = portia
class_id
work_id
school_year
status
workflow_state
summary
initiation
planned_start_date?
planned_end_date?
review_on?
continues_from?
creation_source
created_at
created_by
updated_at
updated_by
```

The root should not embed mutable arrays of Participants, Needs, Goals,
Supports, Interventions, Implementations, Fidelity records, Communications, or
Outcomes.

Those independently meaningful records belong under `records/` and are composed
through references/derived views.

### Canonical lifecycle

Accepted canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

This describes whether the representation is eligible/current, not the ordinary
support workflow stage.

### Workflow state

Accepted Support Process workflow state:

```text
planning
active
paused
completed
discontinued
cancelled
```

Semantics:

```text
planning
= support workflow is being assembled/reviewed

active
= current support workflow is intended for use

paused
= current workflow is intentionally suspended without being defective

completed
= workflow was operationally brought to its intended close

Discontinued
= an active workflow was intentionally ended before ordinary completion or
  without claiming success/failure

cancelled
= planning was intentionally stopped before ordinary activation
```

Spelling in the final wire vocabulary should use lowercase `discontinued`; the
capitalization above is prose only.

These states do not mean:

```text
effective
ineffective
resolved
goal_met
goal_not_met
compliant
noncompliant
```

A Support Process may remain canonical `active` while workflow state is
`paused`, `completed`, or `discontinued`, just as an accepted completed Review
can remain a valid canonical record.

A date passing must not automatically change workflow state.

---

## 7. Initiating Context Is Context, Not Proof

A Support Process may legitimately begin because of:

```text
one or more Events
Review or Determination context
Response referral/handoff
student or family request
teacher-identified need
historical/import context
other bounded reason
```

The root should preserve one bounded `initiation` object stating why the process
was opened and, when appropriate, an exact context reference.

ADR 0014 accepts an initiation union built from:

```text
reason
context_ref?
detail?
```

with a closed `reason` vocabulary.

Where student/family request content is substantively important as evidence, it
should normally be preserved in Account and/or Communication and referenced
exactly rather than copied as a long Support Process narrative.

Additional Event context should reuse canonical `work_relationship@2`:

```text
Support Process --draws_context_from--> Event
```

The relationship remains contextual and noncausal.

Child records such as Review, Hypothesis, Determination, Response, or
Communication should use exact Portia work-record references where direct
context is needed.

Several linked Events never automatically establish a pattern, cause, function,
or diagnosis.

---

# 8. Support Process Participant Is a Canonical Child

Issue #18 will publish:

```text
portia_support_process_participant_id@1
support_process_participant@1
```

Accepted opaque identifier prefix:

```text
spp_<opaque-id>
```


One Support Process Participant represents:

> One represented human explicitly included in one exact Support Process
> context.

Accepted canonical storage:

```text
classes/<class_id>/modules/portia/work/<support_process_id>/
  records/support_process_participant/<participant_id>.json
```

The participant should reuse:

```text
represented_human_attribution@1
```

for the represented person rather than copy another person union.

This supports:

```text
roster_student
actor
local_operator
descriptive_person
unidentified_person
```

while application validation restricts current-use eligibility.

An active/current Support Process Participant should not remain unidentified.
Historical/imported proposed material may preserve honest uncertainty.

### Process participation context

The Participant carries one or more nonexclusive descriptive contexts:

```text
supported_person
provider_or_collaborator
family_or_support_person
coordinator
observer
other
```

ADR 0014 accepts this context vocabulary.

These values are navigation/context only. They do not establish:

```text
plan-specific provider responsibility
plan-specific recipient status
guardianship
consent
professional authorization
employment
licensure
disclosure rights
```

Plan-specific provider and target relationships must be explicit on Support,
Intervention, and Implementation records.

Application validation should reject duplicate logical participant identity even
when display snapshots differ.

An active Support Process should require at least one active Participant that is
explicitly in the supported-person context before the process can be used as an
active support workflow.

---

# 9. Existing Support Process Targeting Becomes Operational

Issue #18 should reuse without versioning:

```text
support_process_target_ref@1
```

Accepted scopes are already:

```text
support_process
support_process_participant
support_process_participants
```

The target answers:

> Which Support Process scope/person/set does this Need, Goal, Support,
> Intervention, Implementation, or later Follow-Up/Outcome apply to?

A whole-process target does not imply that every Participant received the same
Support or shares the same Need/Goal.

Participant-set order is nonsemantic. Application validation should reject
duplicate logical Participant identity even if structurally distinct references
or snapshots could otherwise obscure duplication.

A target does not establish provider responsibility, authority, consent, or
participation.

---

# 10. Need Is an Independently Addressable Child

ADR 0014 accepts:

```text
portia_support_need_id@1
support_need@1
```

Accepted opaque prefix:

```text
spn_<opaque-id>
```

One Support Need represents:

> One bounded teacher-local statement of a barrier, access need, skill/support
> need, environmental need, or other reason for planning support for one exact
> Support Process target.

Accepted core fields:

```text
need_id
target
kind
description
status
supersedes?
creation_source
created_at / created_by
updated_at / updated_by
```

Accepted Need kind vocabulary is:

```text
access
environmental_or_instructional
organizational_or_routine
skill_or_strategy
relationship_or_connection
resource_or_coordination
other
```

The vocabulary describes the support need, not the student.

Need must not encode:

```text
diagnosis
disability eligibility
risk score
behavior function as fact
policy violation
character trait
permanent deficit
```

Independent identity is justified because one Need may be referenced by several
Supports/Interventions, corrected independently, reviewed later, and targeted by
future #19 records.

---

# 11. Goal Is an Independently Addressable Child

ADR 0014 accepts:

```text
portia_support_goal_id@1
support_goal@1
```

Accepted opaque prefix:

```text
spg_<opaque-id>
```

One Support Goal represents:

> One intended support objective or desired future condition for one exact
> Support Process target.

Accepted core fields:

```text
goal_id
target
description
planned_criteria?
measurement_approach?
status
supersedes?
creation_source
created_at / created_by
updated_at / updated_by
```

`planned_criteria` and `measurement_approach` describe how a later review may be
conducted. They do not record current progress, attainment, or Outcome.

Goal must not become:

```text
academic Grade
standards proficiency rating
punishment target
compliance target
predicted Outcome
universal progress percentage
```

Independent identity is justified because several Interventions may address one
Goal and later #19 Follow-Up/Outcome should be able to target the exact Goal
representation without reopening the plan.

---

# 12. Support and Intervention Are Separate Canonical Record Families

ADR 0014 accepts separate:

```text
portia_support_id@1
support@1

portia_intervention_id@1
intervention@1
```

Accepted prefixes:

```text
spt_<opaque-id>
int_<opaque-id>
```


This separation is intentional rather than cosmetic.

## Support

One Support represents:

> One planned assistance, strategy, access arrangement, routine,
> environmental/instructional adjustment, resource, or relationship-based
> support intended to address at least one explicit Support Need.

A Support may legitimately be:

```text
as_needed
less prescriptive
not tied to one numeric dosage
not tied to one explicit Goal
```

while still preserving target, strategy, need linkage, provider where
applicable, and plan state.

## Intervention

One Intervention represents:

> One deliberately structured, goal-linked plan with explicit implementation
> parameters and an expectation of repeated implementation or monitoring.

An Intervention should require:

```text
one or more exact Goal refs
one or more exact Need refs
explicit target
one or more planned providers
explicit planned schedule / implementation expectation
```

This stricter structure is the primary reason not to collapse Support and
Intervention into one all-optional record.

Neither record establishes:

```text
MTSS/RTI tier
IEP/504/BIP status
formal FBA
clinical treatment
evidence-based-program certification
institutional authorization
likely effectiveness
```

Separate record kinds also make exact Implementation/Fidelity/Outcome references
self-describing without inspecting a nested plan-kind discriminator.

---

# 13. Plan Strategy Vocabulary Should Stay Broad and Neutral

Support and Intervention share a small broad strategy family rather than
publish a district discipline/intervention taxonomy.

Accepted strategy family vocabulary:

```text
access
environmental_or_instructional
organizational
relationship_or_connection
routine_or_structure
skill_building
self_management
resource_or_coordination
other
```

Each plan should also carry bounded human-readable strategy/procedure text.

The family describes what is planned, not:

```text
student identity
severity
risk
culpability
diagnosis
predicted response
```

No evidence-strength or effectiveness rating belongs on the plan.

---

# 14. Plan Targets and Providers Are Explicit

Support and Intervention targets should reuse:

```text
support_process_target_ref@1
```

Plan provider relationships should reference exact Support Process Participants
rather than rely on process-level participation context.

The final schema can define a typed exact local Participant reference by
composing:

```text
exact_local_record_ref@1
record_kind = support_process_participant
contract_version = 1
```

This preserves the represented historical Participant version and never silently
follows correction.

Rules:

- process membership does not make someone a provider;
- `provider_or_collaborator` context does not assign a person to every plan;
- Support may omit a provider only where the plan genuinely represents an access
  condition/resource that has no responsible implementing person;
- Intervention should require at least one planned provider;
- provider identity does not establish institutional authority, licensure,
  employment, or delegated service responsibility;
- roster-student representability does not make a student an institutional
  service provider;
- family participation does not establish guardianship or educational decision
  rights.

---

# 15. Planned Schedule Is Shared but Separate From Actual History

Support and Intervention have at least two stable consumers for a common planned
schedule shape, so ADR 0014 accepts an additive:

```text
planned_schedule@1
```

The primitive should be bounded and typed rather than require ambiguous free
text for calculable scheduling semantics.

It must honestly represent at least:

```text
as_needed
recurring cadence
event/condition-triggered use
bounded custom schedule
```

and, where meaningful:

```text
planned start
planned end
review date
occurrences per interval
planned per-occurrence duration or bounded range
selected days/times
```

ADR 0014 defines the closed union as `as_needed`, `recurring`,
`condition_triggered`, and `custom`, with typed planning windows/duration and
recurring cadence fields as specified by the ADR.

Requirements:

```text
planned frequency
≠ actual frequency

planned duration
≠ actual duration

calendar occurrence
≠ Implementation
```

An expired planned end date must not automatically complete a plan or Support
Process.

Actual counts/durations are derived from Implementation records only when capture
coverage is sufficient. They should not be mutable authoritative counters on the
plan.

---

# 16. Plan Operational State Is Separate From Canonical Lifecycle

Support and Intervention need plan state because one plan can pause/end while the
containing Support Process continues.

Accepted plan state:

```text
planned
active
paused
completed
discontinued
```

Canonical record lifecycle remains:

```text
proposed
active
invalidated
superseded
```

Examples:

```text
plan_state = completed
status = active
```

means the valid historical plan reached its operational close.

It does not mean the plan was effective or the Goal was attained.

`invalidated` remains reserved for a defective representation.

---

# 17. Implementation Is One Actual Occurrence or Attempt

Issue #18 will publish:

```text
portia_implementation_id@1
implementation@1
```

Accepted prefix:

```text
imp_<opaque-id>
```

One Implementation represents:

> One bounded actual occurrence, attempt, or explicitly delimited implementation
> interval of one exact Support or Intervention.

Accepted core fields:

```text
implementation_id
plan_ref
actual_target
implemented_by
execution_state
started_at
ended_at?
variation?
summary?
status
supersedes?
creation_source
created_at / created_by
updated_at / updated_by
```

`plan_ref` should be a closed exact local union for:

```text
support@1
intervention@1
```

Actual provider(s) should reference exact Support Process Participants and remain
separate from persistence attribution.

Actual target should reuse `support_process_target_ref@1`.

Accepted execution states:

```text
attempted
in_progress
completed
partially_completed
unable_to_complete
unknown
```

The initial design intentionally does **not** add `cancelled` as an Implementation
state. A scheduled occurrence that was cancelled before any implementation
attempt should not become an Implementation merely because it was on a calendar.
If an actual implementation opportunity was reached but could not be completed,
`unable_to_complete` can preserve that bounded fact.

`unknown` should be historical/import-only.

Implementation state never means:

```text
successful
effective
compliant
noncompliant
good
bad
resolved
```

Repeated occurrences remain separate canonical records.

---

# 18. Implementation Variation Does Not Mutate the Plan

An Implementation may preserve bounded occurrence-local variation such as:

```text
different provider
shorter/longer actual duration
different permitted target subset
minor procedural deviation
context-specific adaptation used once
```

The variation records what actually happened during that occurrence.

It does not rewrite the Support/Intervention plan automatically.

Application validation should make deviations visible when they fall outside
planned target/provider/schedule expectations rather than silently treating them
as if the plan always contained those values.

A material prospective change belongs to a new Support/Intervention successor.

---

# 19. Material Adaptation Uses Plan Successor History

ADR 0014 does not justify a public `adaptation@1` record.

Use this boundary:

```text
one-occurrence variation
→ Implementation.variation

material prospective change
→ new Support/Intervention successor

recording error
→ correction successor/history
```

Material prospective changes include substantive changes to:

```text
strategy/procedure
target
planned provider
Need/Goal linkage
cadence
dosage/duration expectation
monitoring expectation
```

The successor should preserve a reason that distinguishes intentional plan
adaptation from correction of a falsely recorded prior plan.

Accepted plan successor reason concepts include:

```text
plan_adapted
strategy_corrected
target_corrected
provider_corrected
need_link_corrected
goal_link_corrected
schedule_corrected
monitoring_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

ADR 0014 additionally includes `monitoring_corrected` and fixes this shared
plan-successor vocabulary for v1.

No successor mechanism should silently retarget existing Implementation or
Fidelity references.

---

# 20. Fidelity Is Attributed Implementation-Quality Evaluation

Issue #18 will publish:

```text
portia_fidelity_id@1
fidelity@1
```

Accepted prefix:

```text
fid_<opaque-id>
```

One Fidelity record represents:

> One attributed evaluation of how closely one exact Implementation, explicit
> set of Implementations, or bounded implementation interval matched one exact
> Support/Intervention plan or identified protocol.

Accepted scope branches:

```text
one_implementation
implementation_set
bounded_plan_interval
```

Accepted categorical result vocabulary:

```text
as_planned
partially_as_planned
not_as_planned
unable_to_determine
not_applicable
```

The evaluator should be explicit and distinct from provider and recorder. The
final design should favor an exact Support Process Participant evaluator where
current process membership is meaningful.

A Fidelity record should preserve an explicit basis. Depending on the accepted
wire design, basis may include exact Implementation references, observation/
checklist records, or an identified source-defined instrument/protocol.

No universal numeric Portia fidelity score is justified.

A numeric/scaled value is acceptable only when the record preserves the
instrument/protocol identity, version, and source-defined scale semantics.
Portia must not reinterpret that number as effectiveness.

These implications are prohibited:

```text
missing Fidelity
=> poor fidelity

high Fidelity
=> effective Intervention

low Fidelity
=> student fault

Implementation count
=> Fidelity

Fidelity
=> provider competence
```

Outcome/effectiveness remains #19.

---

# 21. Hypothesis and Formal FBA Boundary

Current `hypothesis@1` remains Event-local and explicitly tentative.

Issue #16 deferred broader cross-Event/FBA ownership for reconsideration once
Support Process became concrete. That deferral does not require Issue #18 to
invent a formal FBA record.

ADR 0014 accepts this boundary:

- Support Process may draw context from several Events;
- Support Process planning may retain exact references to one or more Event-local
  Hypotheses;
- those Hypotheses remain separately authored, Event-local, and tentative;
- no automatic aggregation selects a behavioral function;
- no Hypothesis automatically selects/recommends an Intervention;
- ordinary teacher-local support planning is not labeled an FBA;
- formal FBA/team-hypothesis authority remains deferred unless a concrete later
  requirement demonstrates an honest teacher-local semantic unit.

No `support_process_hypothesis@1` is justified by the initial design.

---

# 22. Support Process-Owned Communication Becomes Current-Use Eligible

Issue #17 intentionally published `communication@1` with structural support for:

```text
event
support_process
```

while application validation temporarily rejected Support Process ownership until
Issue #18 published the owner.

Once `support_process@1` exists, Issue #18 integration should:

1. remove the temporary unconditional Support Process rejection from the current
   Communication application validator;
2. require exact owner/class/work-kind agreement and a resolvable eligible
   Support Process;
3. retain all existing sender/recipient/contact-point/privacy rules;
4. test `support_coordination` Communication under Support Process;
5. prove Communication does not create Implementation or consent;
6. avoid a `communication@2` wire change unless a genuine incompatibility is
   discovered.

Historical Issue #17 documentation can continue to state that Support Process
ownership was unavailable at that time. Current tests/documentation must be
reconciled so that statement no longer operates as a permanent runtime rule.

---

# 23. Lifecycle, Correction, and Amendment

All Issue #18 child families should initially reuse canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

Material correction preserves a successor/history.

`invalidated` means the representation is defective. It must not mean:

```text
ineffective
paused
discontinued
student_declined
family_declined
poor_fidelity
goal_not_met
```

The generic Amendment contract permits only family-approved nonmaterial paths.

ADR 0014 accepts the conservative v1 policy:

```text
Support Process root:
no v1 Amendment paths unless a clearly display-only/nonmaterial field is
identified

Participant / Need / Goal / Support / Intervention / Implementation / Fidelity:
no v1 Amendment paths by default
```

The ADR must evaluate this family by family. If a field changes the historical
claim, plan, target, provider, timing, result, or evaluation basis, it requires
successor/history rather than in-place mutation.

Statement of Disagreement remains additive and nonadjudicating.

---

# 24. Cross-Year Continuity Is Explicit and One-to-One in v1

A Support Process that legitimately continues into a new school year should
normally create a new Support Process under the new legitimate owning class/year.

ADR 0014 accepts a successor-owned root field:

```text
continues_from
```

containing one exact prior `support_process` work reference.

Application semantics:

```text
successor work_id != predecessor work_id
successor exact ref resolves
predecessor is support_process
predecessor and successor are distinct work roots
new owner/class/year is independently valid
one successor declares at most one predecessor in v1
```

The predecessor does not become canonically `superseded` merely because support
continues next year.

Typical prior state is operationally `completed` or `discontinued` while its
canonical representation remains valid.

Cross-year continuation is not:

```text
record migration
ownership correction
contract migration
duplicate consolidation
proof of effectiveness
automatic child-record cloning
```

Reverse successor lookup is derived.

If future requirements need split/merge continuation, publish an explicit later
version rather than implying graph semantics in v1.

---

# 25. Paper and Import Boundary

The established rule remains:

```text
paper template
≠ active Support Process

printed plan
≠ accepted plan

scheduled row
≠ Implementation

checklist template
≠ Fidelity evaluation
```

Preallocated paper must not fabricate Support, Intervention, Implementation, or
Fidelity records.

Ingested paper/import may preserve only proposed representations where future
Issue #20 workflow permits human review.

Historical imports may preserve honest uncertainty such as unknown provider,
method, timing, or execution state when the final schemas explicitly support it.

Source-system prestige does not establish authorization, diagnosis, delivery,
fidelity, effectiveness, or current applicability.

---

# 26. Privacy Boundary

Support Process data can expose sensitive disability-related, health-related,
family, safety, or behavioral context even though Portia is not the authoritative
institutional system for those domains.

Issue #18 should therefore minimize narrative at the native-contract level:

- opaque IDs contain no sensitive meaning;
- Need/Goal descriptions are bounded and contextual;
- exact references are preferred over copied narratives;
- Actor contact values are not copied into plan records;
- derived indexes should use IDs/status/time metadata where sufficient;
- no diagnosis/eligibility/authorization is inferred from titles or labels;
- Support Process data is not automatically exported/published.

Issue #21 remains responsible for full privacy classification, redaction, export,
retention, and Sunset boundaries.

---

# 27. Automation Boundary

Software may:

```text
validate references
validate chronology
validate schedule shape
detect logical duplicates
show human-authored plan templates
create reminders from an accepted schedule
derive implementation timelines/counts with coverage caveats
show planned-versus-recorded implementation views
prepare drafts/checklists
```

Software must not:

```text
diagnose
infer behavioral function
infer disability or risk
choose or recommend an Intervention from Event counts
escalate tier/punishment automatically
convert Hypothesis into Intervention
create Implementation because a scheduled time elapsed
infer Fidelity from counts
infer student compliance/remorse/attitude
infer family engagement
infer provider competence
infer effectiveness or Outcome
close a process because a date passed
publish intervention data automatically
```

---

# 28. Core v0.6 Publication Compatibility Is Future-Facing Only

Core v0.6 defines a nonacademic:

```text
intervention_record_set
```

publication kind and keeps intervention/outcome semantics producer-owned.

Issue #18 should make native Portia identity and exact-reference semantics stable
enough for a future privacy-minimized producer projection.

Issue #18 should **not** implement:

```text
Academic Work Registration
Publication Record creation
producer manifest
PublicationProducerProfile
paper_data_suite.publication_producers entry point
Meridian selection/subscription policy
academic_result_set
Score / standards rating / Grade semantics
automatic intervention publication
```

Future Core publication is a projection over authoritative Portia-native records,
not the canonical Support Process storage model.

---

# 29. Accepted Additive Public Contract Inventory

ADR 0014 authorizes implementation of this additive inventory:

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

Already-published contracts reused unchanged:

```text
portia_support_process_id@1
support_process_target_ref@1
portia_work_ref@1
exact_portia_work_ref@1
local_record_ref@1
exact_local_record_ref@1
exact_portia_work_record_ref@1
portia_local_work_target@1
work_relationship@2
represented_human_attribution@1
```

ADR 0014 does not authorize public:

```text
adaptation@1
support_process_hypothesis@1
communication_party@1
provider@1
recipient@1
party@1
case@1
service@1
plan@1
```

ADR 0014 is accepted after the required pre-ADR drift check. The contracts listed
above are authorized for additive implementation; no existing published `$id` is
modified in place.

---

# 30. Accepted Application-Level Invariants

The application validator/tests must cover at least these graph rules.

## Support Process

- canonical path/class/work-ID agreement;
- Core class and school-year resolution;
- workflow-state/lifecycle compatibility;
- dates never auto-transition state;
- active use requires an eligible supported-person Participant;
- initiation refs resolve exactly;
- `draws_context_from` Event relationships remain noncausal;
- cross-year `continues_from` is exact, non-self, and one-to-one in v1.

## Participant

- represented person resolves where current use requires it;
- logical identity is unique within one Support Process;
- roster references remain class-qualified;
- current active unidentified person is rejected;
- context labels do not confer provider/recipient/authority rights.

## Need / Goal

- target resolves within the containing Support Process;
- no diagnosis/risk/compliance/Outcome fields;
- material correction preserves successor history;
- exact references never silently follow successors.

## Support / Intervention

- target and Need/Goal refs belong to the same Support Process;
- Intervention requires Goal, Need, provider, and planned schedule;
- Support retains less-prescriptive/as-needed capability;
- planned provider is an eligible exact Participant;
- planned values do not become actual implementation counters;
- plan state is not effectiveness;
- material adaptation creates a successor rather than rewriting the plan.

## Implementation

- exact plan belongs to the same Support Process;
- actual provider and target are explicit;
- chronology is valid;
- schedule/reminder rows do not fabricate Implementation;
- repeated occurrences remain separate;
- deviations remain visible;
- execution state is neutral and not Outcome.

## Fidelity

- evaluator is explicit;
- exact plan/Implementation scope resolves;
- basis is explicit;
- instrument result requires instrument/scale identity;
- categorical result remains implementation-quality only;
- no compliance/provider-competence/effectiveness inference.

## Communication integration

- Support Process owner resolves and is current-use eligible;
- existing Communication privacy/contact rules remain unchanged;
- Communication never creates Implementation or proves participation/consent.

## Shared infrastructure

- lifecycle/disagreement/dependency/migration/removal remain generic;
- exact refs never silently follow successors;
- operational/derived records remain privacy-minimized;
- missing/incomplete derived data cannot prove absence.

---

# 31. ADR 0014 Resolution Summary

ADR 0014 resolves the required decisions as follows:

1. Support Process canonical lifecycle is `proposed`, `active`, `invalidated`,
   `superseded`; workflow state is separately `planning`, `active`, `paused`,
   `completed`, `discontinued`, or `cancelled`.
2. Support Process Participant uses opaque `spp_` identity and a nonexclusive
   context set: `supported_person`, `provider_or_collaborator`,
   `family_or_support_person`, `coordinator`, `observer`, `other`.
3. Need uses opaque `spn_` identity and the closed descriptive kind vocabulary
   `access`, `environmental_or_instructional`, `organizational_or_routine`,
   `skill_or_strategy`, `relationship_or_connection`,
   `resource_or_coordination`, `other`.
4. Support and Intervention are distinct canonical families. Support uses `spt_`;
   Intervention uses `int_`.
5. Both plan families share strategy families `access`,
   `environmental_or_instructional`, `organizational`,
   `relationship_or_connection`, `routine_or_structure`, `skill_building`,
   `self_management`, `resource_or_coordination`, `other`.
6. Need and Goal are independently addressable canonical children. Goal uses
   opaque `spg_` identity.
7. `planned_schedule@1` is a shared closed union for `as_needed`, `recurring`,
   `condition_triggered`, and `custom`; `as_needed` is Support-only for active
   current use.
8. Intervention requires at least one Need, at least one Goal, an assigned
   provider set, a non-`as_needed` schedule, and a bounded monitoring approach.
   Support requires at least one Need but may omit Goal and may explicitly state
   that no human provider is assigned when the support semantics justify it.
9. Plan operational state is `planned`, `active`, `paused`, `completed`, or
   `discontinued`, separate from canonical lifecycle and effectiveness.
10. Implementation uses opaque `imp_` identity and neutral execution state
    `attempted`, `in_progress`, `completed`, `partially_completed`,
    `unable_to_complete`, `unknown`. Only `in_progress` has an ordinary terminal
    progression update; terminal-state corrections use successor history.
11. One-occurrence deviation is Implementation-local variation. Material
    prospective adaptation creates a Support/Intervention successor with
    `plan_adapted`; no `adaptation@1` is published in v1.
12. Fidelity uses opaque `fid_` identity, exact plan scope plus one
    Implementation, an explicit Implementation set, or a bounded plan interval,
    and categorical results `as_planned`, `partially_as_planned`,
    `not_as_planned`, `unable_to_determine`, `not_applicable`.
13. Fidelity evaluator is an exact Support Process Participant. Instrument-defined
    numeric/scaled results are permitted only with explicit instrument version and
    source-defined scale bounds; there is no universal Portia fidelity score.
14. Support Process initiation has one primary closed reason/context union;
    additional Event context uses `work_relationship@2` unchanged.
15. Cross-year continuation uses one successor-owned exact `continues_from`
    Support Process reference. It is one-to-one in v1, does not supersede the
    predecessor, and is distinct from migration and ownership correction.
16. No Issue #18 family exposes v1 Amendment paths. Ordinary process/plan state
    progression and in-progress Implementation completion are revision-aware
    workflow updates; material semantic correction preserves successor history.
17. `communication@1` remains wire-compatible. Issue #18 replaces only the
    temporary application-level owner-unavailable gate with real Support Process
    resolution/current-use validation.
18. Event-local `hypothesis@1` remains Event-local; no formal FBA or
    `support_process_hypothesis@1` is published in v1.
19. The additive public inventory is `support_process@1`, seven new opaque child
    identifier contracts and their seven canonical record contracts, plus
    `planned_schedule@1`. Existing `portia_support_process_id@1` and shared
    reference/target/infrastructure contracts are reused unchanged.
20. Core `intervention_record_set` remains future publication compatibility only;
    Issue #18 does not implement publication, Academic Work Registration, Score,
    standards-rating, Grade, or Meridian policy.

The accepted architecture now authorizes additive schema implementation and
fixture/test work. Any later discovery of a genuine wire incompatibility must use
an explicit new contract version rather than mutate a published `$id`.
