# ADR 0014: Define Support Process, Support, Intervention, Implementation, and Fidelity Contracts

- **Status:** Accepted
- **Date:** 2026-08-10
- **Decision owners:** Portia maintainers
- **Related issue:** `#18 — Define Support Process, Support, Intervention, implementation, and fidelity contracts`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Builds on:** ADR 0002, ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012, and ADR 0013
- **Refines:** historical shorthand that grouped ongoing Supports/Interventions without separately specifying plan, implementation, fidelity, and outcome layers

## Context

The accepted Portia foundation now separates:

```text
Event
→ source evidence
→ human review/judgment
→ Response and/or Communication
→ longitudinal support planning
→ later Follow-Up / Outcome / Reentry / Repair
```

ADR 0013 made the immediate/ongoing boundary explicit: Response is one bounded
Event-local action, while planned, recurring, scheduled, longitudinal,
goal-directed, implementation-tracked, or fidelity-tracked activity belongs to
Support/Intervention.

Issue #18 must make that latter layer concrete without creating a teacher-local
IEP, 504, BIP, FBA, clinical treatment plan, diagnosis, service-authorization
registry, district MTSS platform, or permanent student dossier.

The architecture must also preserve four different claims:

```text
what was planned
≠ what was implemented

what was implemented
≠ how closely it matched the plan

how closely it matched the plan
≠ whether it worked

operational completion
≠ success / goal attainment / resolution
```

The required pre-ADR checkpoint found no Portia or Core drift. Portia `main`
remains `5898ad79a7d405dc1e23b94753a0eeba793c8e72`; Core `main` remains
`6c507213618b68a6dd3ea096e1a898201ff029e6`; ADR 0014 was free before this
file was added.

## Decision

### 1. Support Process is the second initial Portia work kind

One Support Process represents one bounded, class-owned, teacher-local support
workflow. It groups participants, explicit Needs/Goals, planned Supports and/or
Interventions, actual Implementation history, optional Fidelity evaluations,
and later #19 references without becoming a student-global dossier.

The already-published work identity remains authoritative:

```text
sup_<opaque-id>
portia_support_process_id@1
```

Issue #18 publishes:

```text
support_process@1
```

Canonical storage is:

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

Exactly one Core class owns the work root. Cross-class participants do not split
or duplicate ownership. Student/cross-process histories remain derived.

The root carries no diagnosis, tier, IEP/504/BIP/FBA authority, effectiveness,
or academic Grade semantics.

### 2. Support Process root stays small

`support_process@1` carries the work envelope plus bounded process metadata:

```text
schema_version = 1
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
supersedes?
creation_source
created_at
created_by
updated_at
updated_by
```

Participants, Needs, Goals, Supports, Interventions, Implementations, Fidelity,
Communications, and later Outcomes are not mutable arrays embedded in `work.json`.
They are separately canonical records or derived views.

Canonical lifecycle is:

```text
proposed
active
invalidated
superseded
```

Workflow state is separately:

```text
planning
active
paused
completed
discontinued
cancelled
```

Accepted ordinary workflow progression is:

```text
planning -> active | cancelled
active   -> paused | completed | discontinued
paused   -> active | completed | discontinued
```

`completed`, `discontinued`, and `cancelled` are terminal workflow states in v1.
They do not imply effectiveness, goal attainment, failure, blame, or resolution.
A valid historical process may remain canonical `active` after workflow
completion/discontinuation because canonical lifecycle answers whether the
representation remains valid, not whether the workflow is ongoing.

Dates never transition workflow state automatically.

### 3. Initiation is one primary bounded context, not proof

The root has one `initiation` union. Accepted initiation kinds are:

```text
event_context
review_context
determination_context
response_handoff
represented_request
teacher_identified_need
imported_history
other
```

Reference requirements are:

```text
event_context        -> exact Event work ref
review_context       -> exact Review work-record ref
determination_context-> exact Determination work-record ref
response_handoff     -> exact Response work-record ref
represented_request  -> exact Account or Communication work-record ref
teacher_identified_need -> bounded detail, no fabricated source ref required
imported_history     -> import creation provenance plus bounded detail
other                -> bounded detail
```

The initiation object identifies why the workflow was opened. It does not prove
that an Event occurred as alleged, that a Determination was correct, that a
request was authorized, or that support was warranted.

Additional Support Process → Event context reuses `work_relationship@2`
unchanged:

```text
Support Process --draws_context_from--> Event
```

Several linked Events never automatically establish pattern, cause, behavioral
function, diagnosis, risk, or a preferred Intervention.

### 4. Support Process Participant is a distinct canonical child

Issue #18 publishes:

```text
portia_support_process_participant_id@1
support_process_participant@1
```

Identifier prefix:

```text
spp_<opaque-id>
```

One Support Process Participant represents one human explicitly included in one
Support Process. Human representation reuses:

```text
represented_human_attribution@1
```

rather than duplicating person-identity shapes.

A participant has one or more nonexclusive descriptive contexts:

```text
supported_person
provider_or_collaborator
family_or_support_person
coordinator
observer
other
```

`other` requires bounded detail.

These contexts are navigation/workflow context only. They do not establish
plan-specific provider assignment, recipient status, guardianship, consent,
professional authorization, employment, licensure, educational decision rights,
or disclosure permission.

Application validation rejects duplicate logical human identity within one
Support Process. Active current-use unidentified Participants are prohibited;
historical/imported proposed material may preserve honest uncertainty.

A current-use active Support Process requires at least one eligible active
Participant carrying `supported_person` context.

### 5. Existing Support Process targeting is reused unchanged

Issue #18 does not publish another target family. It makes the already-published:

```text
support_process_target_ref@1
```

operational through `support_process_participant@1`.

Accepted target scopes remain:

```text
support_process
support_process_participant
support_process_participants
```

Participant-set ordering is nonsemantic. Duplicate logical Participant identity
is application-invalid. A whole-process target does not imply that every
Participant has the same Need, Goal, plan, provider, or outcome.

Targeting does not establish consent, authority, provider responsibility, or
participation.

### 6. Need and Goal are independently addressable canonical children

Issue #18 publishes:

```text
portia_support_need_id@1
support_need@1

portia_support_goal_id@1
support_goal@1
```

Opaque prefixes are:

```text
spn_<opaque-id>
spg_<opaque-id>
```

One Need is one bounded teacher-local statement of a barrier, access need,
skill/support need, environmental need, or reason for planning support for one
Support Process target.

Need kinds are:

```text
access
environmental_or_instructional
organizational_or_routine
skill_or_strategy
relationship_or_connection
resource_or_coordination
other
```

`other` requires bounded detail.

A Need is not a diagnosis, disability determination, behavioral-function
finding, policy finding, risk score, permanent student deficit, or eligibility
record.

One Goal is one intended support objective or desired future condition for one
Support Process target. It may contain bounded `planned_criteria` and
`measurement_approach` describing how a later review could be conducted.

Goal does not contain current progress, attainment, Outcome, academic Grade,
standards proficiency, punishment target, compliance score, or predicted result.

Independent identity is required because Needs/Goals may be referenced by
several plans, corrected independently, and later targeted exactly by #19.

### 7. Support and Intervention are separate canonical plan families

Issue #18 publishes separate:

```text
portia_support_id@1
support@1

portia_intervention_id@1
intervention@1
```

Prefixes are:

```text
spt_<opaque-id>
int_<opaque-id>
```

Support and Intervention share ownership, targeting, lifecycle, strategy,
provider, schedule, and correction infrastructure, but their required semantics
are materially different.

One Support is one planned assistance, access arrangement, routine,
environmental/instructional adjustment, resource, relationship-based support, or
other assistance intended to address at least one exact Need. A Support may
legitimately be as-needed, may have no Goal, and may explicitly have no assigned
human provider when the semantics are an access condition, self-directed
strategy, or available resource.

One Intervention is one deliberately structured, goal-linked plan with explicit
implementation parameters and an expectation of repeated implementation or
monitoring. An active Intervention requires at least one exact Need, at least one
exact Goal, an assigned provider set, an explicit non-`as_needed` schedule, and a
bounded monitoring approach.

Neither plan family establishes MTSS/RTI tier, IEP/504/BIP/FBA status, clinical
treatment, evidence-based-program certification, service authorization, or
likely effectiveness.

A single generic all-optional `plan@1` is rejected because it would weaken
required semantics and force consumers to infer plan type from optional fields.

### 8. Plan strategy vocabulary is shared and neutral

Both plan families use a broad strategy family plus bounded procedure text.
Accepted strategy families are:

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

`other` requires bounded detail.

The strategy family describes what is planned, not student identity, severity,
risk, culpability, diagnosis, or predicted response.

### 9. Plan target, Need/Goal linkage, and provider expectation are explicit

Both plan families reuse `support_process_target_ref@1` for the recipient/scope.

Need/Goal links are exact same-Support-Process local references. Existing exact
references never silently follow correction or adaptation successors.

Support requires:

```text
target
one or more exact Need refs
strategy
provider_plan
schedule
plan_state
```

and may include exact Goal refs.

Intervention requires:

```text
target
one or more exact Need refs
one or more exact Goal refs
strategy
assigned provider_plan
schedule
monitoring_approach
plan_state
```

`provider_plan` is a schema-local union:

```text
assigned
  -> one or more exact Support Process Participant refs

no_assigned_provider
  -> reason = access_condition | self_directed | resource_availability | other
```

`other` requires detail. Active Intervention accepts only `assigned`.

Participant identity never establishes provider authorization. Plan assignment
also does not authenticate licensure, employment, institutional authorization,
or legal service obligation.

### 10. `planned_schedule@1` separates planned cadence from actual history

Issue #18 publishes one shared:

```text
planned_schedule@1
```

with four closed branches:

```text
as_needed
recurring
condition_triggered
custom
```

Common optional planning fields are:

```text
window
planned_duration
```

`window` may contain:

```text
starts_on?
ends_on?
review_on?
```

with application validation for chronology.

`planned_duration` is either:

```text
minutes
  minutes

range_minutes
  minimum_minutes
  maximum_minutes
```

with positive bounded values and application validation that minimum does not
exceed maximum.

`recurring` additionally requires:

```text
frequency:
  occurrences
  interval_count
  interval_unit = day | week | month
```

and may contain unique `selected_days` plus bounded `timing_detail`.

`condition_triggered` requires bounded `trigger` text.

`custom` requires bounded `description` for schedules that cannot be represented
honestly by the typed cadence branches.

`as_needed` contains no fabricated frequency.

Active Support may use any branch. Active Intervention may use `recurring`,
`condition_triggered`, or `custom`, but not bare `as_needed`.

Planned schedule never proves Implementation. Planned frequency/duration never
become actual frequency/duration. Calendar/reminder occurrence never creates an
Implementation automatically.

### 11. Plan operational state is separate from canonical lifecycle

Support and Intervention canonical lifecycle is:

```text
proposed
active
invalidated
superseded
```

Plan state is:

```text
planned
active
paused
completed
discontinued
```

Accepted ordinary progression is:

```text
planned -> active | discontinued
active  -> paused | completed | discontinued
paused  -> active | completed | discontinued
```

`completed` and `discontinued` are terminal in v1. A later materially renewed
plan uses a successor rather than reopening the old plan.

Plan-state progression is an ordinary revision-aware workflow update, not a
substantive Amendment. It does not establish effectiveness or Goal attainment.

### 12. Implementation is one actual occurrence or attempt

Issue #18 publishes:

```text
portia_implementation_id@1
implementation@1
```

Prefix:

```text
imp_<opaque-id>
```

One Implementation is one bounded actual occurrence, attempt, or explicitly
delimited implementation interval for one exact Support or Intervention.

Implementation requires:

```text
exact plan_ref
actual_target
implementation_provider
execution_state
started_at
ended_at?
variation?
summary?
canonical lifecycle/provenance fields
```

`plan_ref` is a closed exact local union for `support@1` or `intervention@1`.

`implementation_provider` is explicit. It is a schema-local union:

```text
participants
  -> one or more exact Support Process Participant refs

no_human_provider
  -> reason = self_directed | environmental_condition | resource_access | other
```

`other` requires detail.

Execution states are:

```text
attempted
in_progress
completed
partially_completed
unable_to_complete
unknown
```

`unknown` is historical/import-only.

Only `in_progress` has ordinary execution progression:

```text
in_progress -> completed | partially_completed | unable_to_complete
```

The other states are terminal factual states. Correction of a terminal factual
claim uses successor/history.

A scheduled occurrence cancelled before any attempt is not an Implementation.
Repeated actual occurrences remain separate canonical records.

Implementation never contains `successful`, `effective`, `compliant`,
`noncompliant`, `resolved`, or Outcome state.

### 13. One-occurrence variation stays on Implementation

Implementation may preserve an optional `variation` object:

```text
kinds: one or more unique values from
  provider
  target
  timing_or_duration
  procedure
  context
  other

detail
```

The variation describes what actually differed during that occurrence. It does
not judge whether the difference was appropriate, authorized, high/low fidelity,
or effective.

When actual provider/target differs materially from the plan expectation,
application validation requires the corresponding variation kind rather than
silently treating the plan as if it always contained that value.

### 14. Material prospective adaptation uses plan successor history

Issue #18 does not publish `adaptation@1` in v1.

The boundary is:

```text
one-occurrence variation
-> Implementation.variation

material prospective plan change
-> new Support/Intervention successor with reason plan_adapted

recording error
-> correction successor with an appropriate correction reason
```

Plan successor reasons are:

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

A Support may omit `goal_link_corrected`/`monitoring_corrected` use when those
fields are not present; the shared vocabulary remains stable across the two plan
families.

Plan adaptation never silently retargets existing Implementation, Fidelity, or
later Outcome references.

### 15. Fidelity is attributed implementation-quality evaluation

Issue #18 publishes:

```text
portia_fidelity_id@1
fidelity@1
```

Prefix:

```text
fid_<opaque-id>
```

One Fidelity record is one attributed evaluation of how closely one exact
Implementation, an explicit set of Implementations, or a bounded interval of one
exact plan matched that plan/protocol.

Fidelity always identifies one exact Support/Intervention plan and one evaluator
as an exact Support Process Participant. A person performing fidelity review can
be added as a Participant with `observer` and/or `provider_or_collaborator`
context; Participant status does not itself establish professional authority.

Scope is one of:

```text
one_implementation
  -> one exact Implementation ref

implementation_set
  -> two or more unique exact Implementation refs

bounded_plan_interval
  -> started_at + ended_at
```

All referenced Implementations must belong to the same Support Process and exact
plan represented by the Fidelity record.

Categorical result is:

```text
as_planned
partially_as_planned
not_as_planned
unable_to_determine
not_applicable
```

Fidelity also requires explicit basis. Basis kind is:

```text
direct_observation
implementation_records
checklist_or_instrument
record_review
combined
other
```

Basis may contain exact record references and bounded detail. `other` requires
detail. `checklist_or_instrument` requires `instrument_result` when the basis
uses a scored instrument.

An optional `instrument_result` is source-defined and contains:

```text
instrument_name
instrument_version
scale_minimum
scale_maximum
value
scale_label?
```

Application validation requires the value to fall within the declared scale.
There is no Portia-defined universal fidelity score and no automatic conversion
from numeric value to effectiveness.

These inferences are prohibited:

```text
missing Fidelity -> poor fidelity
high Fidelity -> effective intervention
low Fidelity -> student fault
Implementation count -> Fidelity
Fidelity -> provider competence
Fidelity -> student compliance
```

Outcome/effectiveness remains Issue #19.

### 16. Event-local Hypothesis remains Event-local; formal FBA is not fabricated

Issue #16 correctly deferred broader cross-Event/FBA questions until Support
Process existed. Issue #18 resolves that deferral by **not** inventing a formal
FBA record merely because a work owner now exists.

Support Process may reference exact Event-local Hypotheses as context. Those
Hypotheses remain separately authored, Event-local, tentative records.

Portia does not automatically aggregate several Hypotheses into one behavioral
function, diagnosis, risk conclusion, or preferred Intervention. No
`support_process_hypothesis@1` is published in v1.

Formal FBA/team-hypothesis authority remains deferred until a concrete later
requirement can define an honest teacher-local semantic unit and authorization
boundary.

### 17. Support Process-owned Communication becomes current-use eligible without a wire change

ADR 0013 intentionally allowed `communication@1` to carry:

```text
work_kind = event | support_process
```

while the Issue #17 application validator temporarily rejected Support Process
ownership because the canonical owner did not yet exist.

Once `support_process@1` is implemented, current validation must replace that
unconditional gate with:

- exact class/work-kind/work-ID owner agreement;
- Support Process resolution;
- owner lifecycle/current-use eligibility;
- all existing sender/recipient/contact-point/privacy/chronology rules.

`communication@1` itself does not change. Support coordination Communication is
still Communication; it does not prove consent, participation, implementation,
or service delivery.

### 18. Cross-year continuity uses explicit `continues_from`, not supersession

A new school-year workflow normally creates a new Support Process under the new
legitimate owning class/year.

The new root may carry one:

```text
continues_from
```

exact Support Process work reference.

Rules:

```text
successor work_id != predecessor work_id
predecessor resolves exactly as support_process
school-year/work-owner context is independently valid
one predecessor maximum in v1
reverse successor lookup is derived
```

The predecessor does not become canonical `superseded` merely because related
support continues. It may be operationally `active`, `paused`, `completed`, or
`discontinued` when the new-year process is created; Core year closure does not
mutate it automatically.

Cross-year continuation is not migration, ownership correction, duplicate
consolidation, contract migration, proof of effectiveness, or automatic copying
of prior child records.

Split/merge continuation is deferred to a later version if a concrete need
arises.

### 19. Canonical correction remains successor-based; v1 exposes no Amendment paths

All Issue #18 child families use canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

Material correction creates a successor/history. Exact references remain exact
and never silently follow successors.

No Issue #18 family exposes application-level `amendment@1` paths in v1:

```text
support_process
support_process_participant
support_need
support_goal
support
intervention
implementation
fidelity
```

This does not prohibit ordinary revision-aware workflow progression of:

```text
Support Process workflow_state
Support/Intervention plan_state
in_progress Implementation execution_state
```

Those changes describe the continuing state of the same workflow/occurrence and
are not corrections. Once a terminal workflow/factual state is recorded,
material correction uses successor/history.

Statement of Disagreement remains additive and nonadjudicating.

Family-specific successor reason vocabularies are required. At minimum:

```text
Support Process:
  summary_corrected
  initiation_corrected
  planned_timing_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other

Participant:
  person_corrected
  contexts_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other

Need:
  target_corrected
  kind_corrected
  description_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other

Goal:
  target_corrected
  description_corrected
  criteria_corrected
  measurement_approach_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other

Implementation:
  provider_corrected
  target_corrected
  timing_corrected
  execution_state_corrected
  variation_corrected
  summary_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other

Fidelity:
  evaluator_corrected
  scope_corrected
  basis_corrected
  result_corrected
  instrument_result_corrected
  evaluation_period_corrected
  duplicate_consolidated
  work_root_corrected
  contract_migrated
  other
```

Support/Intervention use the plan successor vocabulary defined above.

`invalidated` never means ineffective, paused, discontinued, declined, poor
fidelity, goal not met, or disagreement.

### 20. Paper/import provenance never fabricates planning, implementation, or fidelity

The established distinction remains:

```text
paper template != accepted Support/Intervention
scheduled row != Implementation
checklist template != Fidelity evaluation
```

Preallocated paper cannot create an active plan, Implementation, or Fidelity
claim. Paper/import-derived representations remain `proposed` until the future
Issue #20 human-review gate is satisfied.

Historical imports may preserve explicit `unknown` only where the applicable
contract permits it. Source-system prestige never establishes diagnosis,
authorization, delivery, fidelity, effectiveness, or current applicability.

### 21. Privacy minimization is a native-contract requirement

Support data can expose sensitive family, disability-related, health-related,
safety, and behavioral context even though Portia is not authoritative for those
domains.

Issue #18 therefore requires:

- opaque IDs with no sensitive semantics;
- bounded contextual Need/Goal/strategy text;
- exact references rather than copied narrative where sufficient;
- no copied Actor phone/email values in support records;
- privacy-minimized operation/derived metadata;
- no inferred diagnosis, eligibility, or authorization;
- no automatic Core/Meridian/Vitrine publication/export.

Full redaction/export/retention policy remains Issue #21.

### 22. Automation may organize; it may not make support judgments

Software may validate references, chronology, schedule shape, logical
duplicates, and graph consistency; create reminders from a human-authored
schedule; build derived implementation timelines/counts with explicit coverage
caveats; show templates/checklists; and prepare drafts.

Software must not diagnose, infer function/disability/risk, choose or recommend
an Intervention from Event counts, escalate tier/punishment, convert Hypothesis
to Intervention, fabricate Implementation when time elapses, infer Fidelity from
counts, infer student compliance/remorse/attitude, infer family engagement,
infer provider competence, infer effectiveness/Outcome, close a process from
dates alone, or automatically publish intervention data.

### 23. Existing operational/derived infrastructure is reused

Issue #18 reuses the accepted generic contracts where their semantics fit:

```text
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1 (structurally reusable but application-prohibited for v1 families)
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

No Support-specific operation, lock, Quarantine, Integrity Finding, source
snapshot, or derived-generation fork is authorized without a demonstrated wire
incompatibility.

Derived implementation counts/timelines are nonauthoritative and cannot prove
absence when capture/discovery coverage is incomplete.

### 24. Core v0.6 intervention publication is future projection only

Core v0.6 distinguishes `intervention_record_set` from academic results and
keeps producer-native intervention/outcome semantics producer-owned.

Issue #18 therefore stabilizes Portia-native identities and exact references so
a future privacy-minimized producer projection can be added without redesigning
native storage.

Issue #18 does **not** implement:

```text
Academic Work Registration
Publication Record creation
producer manifest
PublicationProducerProfile
paper_data_suite.publication_producers
Meridian selection/subscription policy
academic_result_set
Score
standards rating
Grade
automatic intervention publication
```

Discoverable publication is not authorization, and intervention data never
becomes academic Score/Grade evidence merely because Core can carry an
intervention publication kind.

### 25. Additive public contract inventory and identifier prefixes are fixed

ADR 0014 authorizes additive implementation of:

```text
support_process@1

portia_support_process_participant_id@1  spp_
support_process_participant@1

portia_support_need_id@1                 spn_
support_need@1

portia_support_goal_id@1                 spg_
support_goal@1

portia_support_id@1                      spt_
support@1

portia_intervention_id@1                 int_
intervention@1

planned_schedule@1

portia_implementation_id@1               imp_
implementation@1

portia_fidelity_id@1                     fid_
fidelity@1
```

The existing:

```text
portia_support_process_id@1              sup_
```

is reused unchanged.

No public v1 contract is authorized for:

```text
adaptation
support_process_hypothesis
plan
party
provider
recipient
case
service
```

Schema-local compositions should be preferred until another stable independent
consumer demonstrates a shared primitive is warranted.

## Consequences

### Positive

- Support planning, actual implementation, implementation quality, and later
  Outcome remain separately auditable.
- Support can remain legitimately lightweight/as-needed without weakening the
  stricter Intervention contract.
- Need/Goal exact identity supports independent correction and later #19 linkage.
- Existing Support Process target/work/reference infrastructure becomes useful
  without version churn.
- Communication gains Support Process current-use ownership without a wire
  version bump.
- Cross-year continuity is explicit without creating one indefinite student
  dossier or abusing migration/supersession.
- Future Core intervention publication can project stable Portia-native records
  without making them academic Scores/Grades.

### Costs

- The support layer uses several canonical child families rather than one
  convenient mutable plan document.
- Application validation must evaluate same-work references, provider/target
  eligibility, schedule/chronology, variation visibility, fidelity scope, and
  successor topology across records.
- User interfaces must hide opaque IDs and graph mechanics behind concise
  teacher-facing workflows.
- Separate Support and Intervention families create additional schema/test work,
  but that cost preserves materially different required semantics.

## Alternatives Considered

### One generic Support/Intervention `plan@1`

Rejected. It would require many conditionally optional fields, weaken the
Intervention requirement for Goal/provider/schedule/monitoring, and force
consumers to inspect a discriminator before knowing the record's core semantic
obligations.

### Embed Needs/Goals/plans/implementation arrays on `support_process@1`

Rejected. The records require independent exact references, correction history,
cardinality, later Outcome targeting, and repeated implementation/fidelity
history.

### Treat Implementation as mutable plan counters

Rejected. Planned frequency is not actual history, and missing/incomplete
capture cannot safely be interpreted through counters.

### Create `adaptation@1`

Rejected for v1. One-occurrence variation and material successor adaptation
cover the current stable semantics without adding a speculative decision family.

### Create a Support Process Hypothesis / FBA record now

Rejected. An owner becoming available does not create an honest formal FBA or
institutional authority model. Event-local Hypotheses remain usable as exact
context without automatic aggregation.

### Reuse Response for Implementation occurrences

Rejected. Response is Event-local bounded action; Implementation is occurrence
history of an exact longitudinal plan and must remain separately canonical.

### Treat Fidelity as Outcome/effectiveness

Rejected. Fidelity describes implementation-plan match only. Effectiveness,
change, goal attainment, and causal interpretation remain Issue #19.

### Use `work_relationship@2` for cross-year Support Process continuity

Rejected. Its accepted semantics are `draws_context_from` with an Event target.
Broadening it would mutate a published semantic boundary. `continues_from` is a
narrow Support Process root relationship instead.

### Implement Core publication in Issue #18

Rejected. Publication is an integration/projection surface, not native support
record authority, and the ticket explicitly keeps privacy/export/publication
work separate.

## Deferred Work

Issue #18 does not define:

- Follow-Up, Outcome, effectiveness, goal attainment, Reentry, or Repair (#19);
- complete paper/PDS2/import activation workflow (#20);
- privacy projection/redaction/export/retention/Sunset policy (#21);
- end-to-end foundation record graphs (#22);
- final foundation architecture audit (#23);
- production filesystem services or teacher-facing application implementation;
- formal institution-authorized FBA/IEP/504/BIP/clinical workflows;
- Core intervention publication producer integration.

## Acceptance Implication

Schemas may now be added **only** in conformance with this ADR and the recorded
pre-ADR checkpoint. Existing published `$id` values remain immutable. Any later
discovery that requires a wire-incompatible change must publish a new version
and document migration/compatibility rather than silently rewriting v1.
