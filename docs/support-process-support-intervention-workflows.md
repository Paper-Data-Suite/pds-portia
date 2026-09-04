# Support Process, Support, and Intervention Workflows

**Issue:** #44 — Implement Support Process, Support, and Intervention planning  
**Milestone:** Portia v0.2.0  
**Contract authority:** ADR 0014 / Issue #18

Issue #44 supplies the production application/workflow layer for the accepted
Support planning contracts without changing their published wire formats:

```text
support_process@1
support_process_participant@1
support_need@1
support_goal@1
support@1
intervention@1
planned_schedule@1
```

Issue #45 now supplies the production application/workflow layer for
`implementation@1` and `fidelity@1`. Follow-Up, Outcome, Reentry, and Repair
remain Issue #46-owned.

## Semantic boundary

Portia is a teacher-local behavior-support adjunct. A Support Process is not a
student dossier, IEP, 504 plan, BIP, FBA, diagnosis, institutional MTSS/RTI
authority, threat-assessment process, clinical treatment plan, or service
authorization registry.

The production layer preserves the governing distinctions:

```text
planned != implemented
implemented != fidelity
fidelity != outcome

Participant != authorized provider
Need != diagnosis or permanent deficit
Goal != attainment, Grade, proficiency, or Outcome
Support / Intervention != delivery or effectiveness
planned schedule != actual occurrence
plan_state=completed != successful or effective
workflow_state=completed != resolved or rehabilitated
```

These are application invariants, not merely documentation cautions.

## Public API

`portia.workflows` exports the six planning services and exact reference
builders:

```text
SupportProcessWorkflowService
SupportProcessParticipantWorkflowService
SupportNeedWorkflowService
SupportGoalWorkflowService
SupportWorkflowService
InterventionWorkflowService

support_process_reference(...)
support_process_participant_reference(...)
support_need_reference(...)
support_goal_reference(...)
support_reference(...)
intervention_reference(...)
```

The child services retain the established guarded workflow shape where
semantically applicable: exact creation/read/list/current-use, canonical
lifecycle transition, material correction, and current resolution. Support and
Intervention additionally expose ordinary `plan_state` progression and explicit
prospective adaptation. Support Process separately exposes ordinary
`workflow_state` progression.

No Issue #44 v1 family exposes Amendment.

## Canonical ownership and bootstrap

One Support Process is one exact class-owned Portia work root:

```text
classes/<class_id>/modules/portia/work/<support_process_id>/
```

Cross-class participants do not move or duplicate that root. Roster identity is
always exact `class_id + student_id`; names and display snapshots never establish
identity.

Digital entry intentionally bootstraps in two stages:

```text
1. create support_process@1 as proposed / planning
2. add Support Process Participants
3. establish at least one active supported_person
4. activate the Support Process canonical lifecycle
5. add Needs, Goals, Supports, and/or Interventions
```

The supported-person invariant is not weakened to simplify creation.

## Support Process lifecycle and workflow state

Canonical lifecycle is:

```text
proposed -> active -> invalidated/superseded
```

subject to the accepted frozen lifecycle rules.

Ordinary workflow state is a separate dimension:

```text
planning -> active | cancelled
active   -> paused | completed | discontinued
paused   -> active | completed | discontinued
```

`completed`, `discontinued`, and `cancelled` are terminal workflow states in v1.
Dates do not transition state automatically. Passing `review_on` or
`planned_end_date`, completing a Support, or later recording a favorable Outcome
does not silently complete the root.

Material Support Process correction is successor-based. Cross-year continuation
is not correction, migration, or supersession: it creates a new Support Process
identity under the later owning class/year and retains an exact
`continues_from` reference to the predecessor.

## Initiating context and Event relationships

The frozen initiation union remains exact:

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

Exact source references remain historically pinned and do not follow later
successors automatically.

Additional Support Process to Event context reuses
`work_relationship@2` with `draws_context_from`. Multiple Event links establish
context only; they do not establish pattern, common cause, behavioral function,
diagnosis, risk, or a preferred intervention.

## Participants and authority

`support_process_participant@1` represents one human explicitly included in one
Support Process. Descriptive contexts include:

```text
supported_person
provider_or_collaborator
family_or_support_person
coordinator
observer
other
```

Context does not establish guardianship, consent, employment, licensure,
educational decision rights, disclosure permission, or plan-specific provider
assignment.

Current-use validation resolves Core roster or Actor authority exactly, rejects
duplicate logical humans in one Support Process, prohibits active unidentified
people, preserves cross-class roster identity without ownership drift, and
honors Quarantine.

## Need and Goal

A `support_need@1` is one bounded teacher-local planning statement for an
explicit Support Process target. It is not a diagnosis, disability
determination, behavioral-function finding, risk score, policy finding, or
permanent student trait.

A `support_goal@1` is a desired future support condition. Optional
`planned_criteria` and `measurement_approach` describe future review planning;
they are not current progress, attainment, effectiveness, Grade, standards
proficiency, or Outcome.

Both families validate exact parent ownership, target authority, lifecycle,
provenance, logical target uniqueness, and Quarantine. Material correction
preserves predecessor history and exact old references remain exact.

## Support and Intervention

Support is the more flexible plan family. A valid Support may be as-needed,
self-directed, omit a Goal where the contract permits, or omit an assigned human
provider when that is honestly represented.

Intervention is deliberately more structured. An active Intervention requires:

```text
one or more exact Needs
one or more exact Goals
an assigned provider set
a non-as_needed planned schedule
an explicit monitoring approach
```

Support and Intervention share canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

and ordinary plan state:

```text
planned -> active | discontinued
active  -> paused | completed | discontinued
paused  -> active | completed | discontinued
```

Ordinary state progression preserves identity. Recording-error correction uses
a correction successor. Material prospective adaptation uses a distinct
`plan_adapted` successor path. A one-occurrence variation belongs to later
Implementation, not to plan correction/adaptation.

## Planned schedule

`planned_schedule@1` remains embedded planning data rather than an occurrence
record. Accepted schedule kinds are:

```text
as_needed
recurring
condition_triggered
custom
```

The application layer validates schedule chronology and duration-range ordering.
A recurring schedule does not fabricate Implementation records and never proves
that anything occurred.

## Support-Process-owned evidence and Communication

Issue #41 already allowed Account/Observation wire ownership under a Support
Process while failing closed when current Support Process authority did not
exist. Issue #44 now supplies that authority. Production integration tests prove
real Support-Process-owned Account and Observation creation/current use without
fabricating Need, Goal, Implementation, Fidelity, Follow-Up, or Outcome.

Issue #43 similarly reserved Support-Process-owned `communication@1`. Issue #44
activates that existing branch without introducing `communication@2`. Support
Process Communication now delegates owner creation/current-use/lifecycle
qualification to the authoritative Support Process workflow service.

Communication remains a bounded communication act or attempt. It is not
Implementation, provider assignment, participation, delivery proof, legal
notice, or Outcome.

## Exact history and no silent retargeting

Exact historical references remain exact across:

```text
correction
plan adaptation
cross-year continuation
duplicate consolidation
work-root correction
contract migration
```

A later successor does not silently retarget a historical Need, Goal, Support,
Intervention, Participant, Communication, Event context, or continuation link.

## Runtime parity and representative acceptance

Issue #44 locks runtime behavior to the frozen Issue #18 planning oracle. The
parity guard explicitly tracks:

```text
53 frozen valid planning scenarios
82 schema-valid/application-invalid planning scenarios
135 total #44-owned runtime-parity scenarios
```

Structural-invalid fixtures remain model/schema validation concerns.
Implementation and Fidelity runtime parity is qualified separately by Issue #45.

Representative production acceptance additionally covers:

* P22-08, Multi-Event Support Process through positive Outcome — the #44
  planning subset round-trips exactly without fabricating downstream records;
* P22-11, Cross-Year Support Continuation — two school-year roots preserve
  independent identities, exact continuation, disjoint children, and exact
  historical pinning;
* the exact frozen active recurring Intervention fixture through the production
  service; and
* the exact frozen cross-class Participant fixture against real Core rosters,
  proving foreign roster identity without Support Process ownership drift.

## Deferred scope

Issue #44 does not implement:

```text
implementation@1
fidelity@1
follow_up@1
outcome@1
reentry@1
repair@1
paper/import review materialization
automatic effectiveness conclusions
automatic Core/Meridian publication
institutional authorization inference
```

Issue #45 now owns and supplies Implementation/Fidelity. Issue #46 owns
Follow-Up/Outcome, Reentry, and Repair.

## Qualification

`scripts/validate_issue44_workflows.py` is the fast repository-local mechanical
drift detector for this surface. It does not replace pytest, Ruff, MyPy,
distribution inventory, isolated installed-wheel smoke, or final
repository-wide qualification.

Validation evidence is recorded in
`docs/validation/issue-44-support-process-support-intervention-workflows-validation.md`.
