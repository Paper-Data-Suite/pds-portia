# Representative End-to-End Portia Contract Graphs

## Status

**Issue #22 — in progress**

This document is the human-readable walkthrough for the repository-local
synthetic graph corpus under:

```text
tests/fixtures/issue_22/
```

The fixture descriptors are development/test metadata, not public Portia
serialization contracts.

## Scenario inventory

| Scenario | Status | Principal coverage |
| --- | --- | --- |
| P22-01 | Implemented in Slice 1 | positive Event, roster participant, `present` role, direct Observation, derived teacher-current summary |
| P22-02 | Implemented in Slice 2 | multi-participant Event, conflicting Accounts, direct Observation, completed Review, insufficient-information Determination |
| P22-03 | Implemented in Slice 3 | single-owner Event with exact cross-class roster-qualified participant identity and deliberate local-ID/name collision |
| P22-04 | Implemented in Slice 4 | append-preserving Account correction, exact supersession, Statement of Disagreement, lifecycle chain, and predecessor-pinned historical Review |
| P22-05 | Implemented in Slice 5 | complete paper/PDS2 staging through teacher review, paper-derived Event, and materialization receipt |
| P22-06 | Implemented in Slice 6 | exact CSV snapshot, digest-bound Import Batch/Source/Proposal, attributable Import Review, canonical Event materialization, replay-safe receipt, and later missing-row no-deletion proof |
| P22-07 | Implemented in Slice 7 | immediate non-consequence Response, workspace Actor family contact, locally confirmed Contact Point, reviewed Actor-to-Student Relationship, and Event-local Communication related to the Response |
| P22-08 | Implemented in Slice 8 | multi-Event Support Process through bounded positive Outcome |
| P22-09 | Implemented in Slice 9 | inconclusive support-response Outcome plus later bounded adverse/unintended-effect Outcome |
| P22-10 | Implemented in Slice 10 | Reentry and Repair without overclaiming |
| P22-11 | Implemented in Slice 11 | cross-year Support continuation with new work/child identities and predecessor-pinned exact refs |
| P22-12 | Implemented in Slice 12 | participant-specific privacy projection and deliberate export |
| P22-13 | Implemented in Slice 13 | rebuildable derived views and retention/custody boundary |
| P22-14 | Planned | coordinated operation and recovery |

## P22-01 — Positive classroom Event

### Story

One synthetic student is present during a classroom discussion. The
synthetic teacher records an active Event and a directly observed action:

> After the prompt, the participant raised a hand and read one sentence from
> prepared notes.

The wording deliberately stays at the observable layer.

### Graph

```text
Core-shaped synthetic roster context
  eng10_p2_2026
    -> stu_p22_001

Event@2
  evt_p22_positive_001
    |
    +-> Event Participant@3
    |     ep_p22_positive_001
    |       subject =
    |       eng10_p2_2026 + stu_p22_001
    |
    +-> Event Participant Role@3
    |     epr_p22_positive_001
    |       target -> ep_p22_positive_001
    |       role_type = present
    |
    +-> Observation@2
          obs_p22_positive_001
            target -> ep_p22_positive_001
            method = live_direct
```

### Canonical records

```text
classes/eng10_p2_2026/modules/portia/work/evt_p22_positive_001/
  work.json
  records/
    event_participant/
      ep_p22_positive_001.json
    event_participant_role/
      epr_p22_positive_001.json
    observation/
      obs_p22_positive_001.json
```

The `work_id` is also the Event identity. Child records retain separate
opaque identifiers.

### What is not created

P22-01 intentionally creates no:

```text
Account
Review
Classification
Hypothesis
Determination
Response
Communication
Support Process
Follow-Up
Outcome
```

A positive/neutral Event does not need artificial downstream records merely
to exercise a longer pipeline.

### Assertions

```text
Event existence != misconduct
participant presence != responsibility
Observation != Determination
display snapshot != identity
teacher-current summary != canonical record
```

### Derived view

The test-only graph harness rebuilds a deterministic teacher-current summary
from active canonical records.

Expected:

```json
{
  "work_id": "evt_p22_positive_001",
  "participant_ids": ["ep_p22_positive_001"],
  "role_ids": ["epr_p22_positive_001"],
  "observation_ids": ["obs_p22_positive_001"]
}
```

Deleting this summary would not alter any canonical record.

## Validation

Focused Slice 1 validation:

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_issue_22_corpus_foundation.py" `
  -v
```

Full foundation regression:

```powershell
python -m unittest discover -s tests/schema_validation
```

The Issue #22 harness performs no network calls and imports no sibling
runtime package.


## P22-02 — Multi-participant Event with conflicting Accounts

### Story

Three synthetic roster students participate in one Event.

Two firsthand Accounts disagree about whether Student B handled a blue folder
before it fell. The teacher's direct Observation begins only after the disputed
handling would have occurred.

The graph therefore preserves:

```text
Account A -> one reported perspective
Account C -> materially conflicting reported perspective
Observation -> directly observed later state
Review -> completed examination of all three evidence records
Determination -> insufficient_information
```

The completed Review is not itself a finding.

### Participant roles

```text
Student A -> directly_involved
Student B -> reported_involved
Student C -> present
```

Student B's `reported_involved` role is not source-free. It carries an exact
`account_ref` basis to `acct_p22_conflict_a@2`.

The role records do not encode guilt, fault, intent, or credibility.

### Evidence graph

```text
acct_p22_conflict_a@2 -----\
                            \
acct_p22_conflict_c@2 ------> rvw_p22_conflict_001@1
                            /             |
obs_p22_conflict_001@2 ----/              |
                                          v
                              det_p22_conflict_001@1
                              outcome =
                              insufficient_information
```

The Determination also preserves the evidence relationships explicitly:

```text
supporting  -> acct_p22_conflict_a@2
contrary    -> acct_p22_conflict_c@2
contextual  -> obs_p22_conflict_001@2
```

Those labels describe the basis for this bounded human Determination. They do
not make the graph validator score credibility or choose which Account is
"true."

### Deliberate omissions

P22-02 creates no Classification or Hypothesis.

The synthetic facts do not require either record merely to lengthen the graph.

### Principal assertions

```text
one Account != another Account
reported involvement != direct Observation
repeated/conflicting reports != proof
role != guilt/fault
Review completed != finding reached
insufficient information is an explicit valid outcome
```


## P22-03 — Cross-class participant identity

### Story

One Event is canonically owned by:

```text
eng10_p2_2026
```

It contains two roster-student Event Participants.

The synthetic Core context deliberately creates the strongest collision case:

```text
eng10_p2_2026      + stu_collision_001 + "Synthetic Alex"
journalism_p6_2026 + stu_collision_001 + "Synthetic Alex"
```

The `student_id` strings match.

The display snapshots match.

They are still two distinct roster-qualified identities because Portia's
durable student reference is:

```text
class_id + student_id
```

No merge is inferred.

### Ownership

Both Event Participant records remain canonical children of the one Event:

```text
classes/eng10_p2_2026/modules/portia/work/evt_p22_crossclass_001/
```

The cross-class participant record therefore has two intentionally different
class concepts:

```text
record.class_id
= eng10_p2_2026
= owning Event class

record.subject.roster_student_ref.class_id
= journalism_p6_2026
= source roster for the participating student reference
```

That difference is valid and necessary.

It does not make the Event multi-class-owned.

### Work-local targeting

The direct Observation targets:

```text
ep_p22_cross_foreign@3
```

inside the owning Event.

It does not target:

```text
stu_collision_001
```

directly.

This preserves:

```text
roster student identity
!= Event Participant identity
```

### Graph uniqueness rule

Issue #22 now evaluates active durable participant-subject uniqueness using:

```text
("roster_student", source_class_id, student_id)
```

not:

```text
student_id
display_name
normalized display name
```

As a result, the two deliberate collision subjects remain distinct and valid.

### Principal assertions

```text
cross-class participant != cross-class Event ownership
same student_id across rosters != same person identity
same display name across rosters != same person identity
source roster class != owning Event class
Event Participant ID != roster student ID
```


## P22-04 — Correction, supersession, disagreement, and exact history

### Story

A synthetic teacher initially records one student's Account as:

```text
"The student said the notebook on the desk was red."
```

A completed Review later references that exact Account.

The student then supplies a Statement of Disagreement:

```text
"I said the notebook was blue, not red."
```

The material text is corrected by creating a new Account rather than
rewriting the predecessor.

### Replacement graph

```text
acct_p22_original_red@2
  status = superseded
        ^
        |
        | supersedes:
        | reason = statement_corrected
        |
acct_p22_corrected_blue@2
  status = active
```

The predecessor remains a real canonical record.

The successor is a different canonical identity.

### Exact historical references

The pre-correction Review remains:

```text
rvw_p22_before_correction@1
  -> acct_p22_original_red@2
```

It does not silently become:

```text
rvw_p22_before_correction@1
  -> acct_p22_corrected_blue@2
```

The Statement of Disagreement also remains targeted to the exact predecessor
that contains the disputed wording.

### Lifecycle history

The predecessor history is append-only:

```text
proposed
  -> active
  -> superseded
```

The corrected successor has its own history:

```text
proposed
  -> active
```

Each transition targets the exact Account representation. The selected
lifecycle head must reconcile with the persisted record status.

### Current-state derivation

For this replacement chain, the test-only current frontier is:

```text
acct_p22_corrected_blue
```

The frontier is derived from exact supersession edges and active status.

It does not erase or retarget the predecessor.

### Principal assertions

```text
correction != erasure
successor identity != predecessor identity
Statement of Disagreement != adjudication
lifecycle transition != record rewrite
historical exact ref != current successor
derived current frontier != canonical authority
```


## P22-05 — Paper-derived proposal, teacher review, and Event materialization

The complete synthetic chain is:

```text
Capture Batch@1
→ Page Target@1
→ Core-shaped PDS2 route / retained source
→ Page Record@1
→ Paper Interpretation@1
→ Capture Proposal@1
→ Capture Review@1
→ committed operation context
→ Event@2
→ Capture Materialization@1
```

The operational Capture Batch `cbat_p22_paper_001` exists before any Event. The canonical
Event `evt_p22_paper_001` is allocated only after the teacher accepts the staging proposal.

The returned source is an actual deterministic BMP byte fixture:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-05-returned-page.bmp
media_type: image/bmp
byte_length: 70
sha256: 75f767d36c35c9d42ed81dd6a2f45c652244c8a66291a50b1228ac32ed125251
```

The graph validator recomputes both length and SHA-256. Core-shaped context
retains source authority; the Portia Page Record only binds the exact route,
scan digest, and page number required for processing.

The machine Interpretation contains candidate values for:

```text
event_time
summary
```

The Proposal binds those candidates to:

```text
/occurrence/started_at
/summary
```

The teacher's `Capture Review@1` is `accepted`. That confirms staging only. It
does not create a Classification, Hypothesis, Determination, Response,
Support, Fidelity, or Outcome.

The resulting Event uses exact ingested paper provenance:

```json
{
  "type": "paper_capture",
  "stage": "ingested",
  "route_id": "route_p22_portia_paper_001",
  "page_record_id": "prec_p22_paper_001"
}
```

Its occurrence time is `2026-08-15T08:35:00-04:00`, not the later scan,
interpretation, review, operation, or receipt timestamp.

`capture_materialization@1` has no independent materialization identifier. The
corpus therefore uses a deterministic privacy-minimal fixture filename derived
from its exact operation revision and exact Review lineage. That filename is a
test-fixture convention, not a public Portia identifier or storage contract.

Full public `operation_journal@2` graph coverage remains reserved for P22-14.
P22-05 uses only a bounded synthetic committed-operation context to prove the
receipt cannot precede canonical acceptance.

The physical-page replay identity exercised here is:

```text
(route_p22_portia_paper_001, scan_p22_portia_paper_001, 1)
```

Reprocessing that same tuple must reconcile existing staging/materialization
rather than allocate another Event.

Principal distinctions:

```text
Capture Batch != Event
Page Target != Event
route success != semantic acceptance
retained source != accepted evidence
processed Page Record != Event
machine candidate != confirmed domain value
Capture Proposal != canonical record
Capture Review != domain judgment
workflow timestamp != Event occurrence time
Capture Materialization != domain record
reprocessing != duplicate Event
```


## P22-06 — Structured import to reviewed Event

### Story

P22-06 begins with an exact synthetic CSV snapshot:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-06-structured-import-v1.csv
sha256: a18156ec10efd8aa046beb4e94afc30d94c9e3b6101a866fab511399ed93e987
bytes: 158
```

The source row has a stable source-provided key:

```text
SRC-EVENT-001
```

and four source fields:

```text
record_key
event_time
summary
source_status = "resolved"
```

`source_status = "resolved"` is deliberately judgment-like source vocabulary.
It is preserved in the Import Source Record but is not mapped into any Portia
judgment family.

The safe path is:

```text
Import Batch@1
→ Import Source Record@1
→ Import Proposal@1
→ Import Review@1
→ committed operation context
→ Event@2
→ Import Materialization@1
```

The Event receives only:

```text
event_time -> /occurrence/started_at
summary    -> /summary
```

There is no imported:

```text
Review
Classification
Hypothesis
Determination
Outcome
```

because a source-system `resolved` label is not Portia judgment.

### Exact replay identity

The Issue #22 harness recomputes deterministic fixture evidence for:

```text
Import Batch identity digest
Import Source Record content digest
Import Source Record identity digest
Import Proposal identity digest
```

using the test-only recipe:

```text
issue22_fixture_canonical_json_v1
```

That recipe belongs to the representative fixture harness only. It does not
publish a Portia runtime digest algorithm.

The mapping profile itself is byte-digest-bound:

```text
tests/fixtures/issue_22/shared/policy-context/p22-06-import-mapping.json
sha256: cc464edfccfc3b49d879ea27581f929709cf8f856f641832afe3d7d60f35c889
```

### Canonical Event provenance

The materialized Event uses:

```json
{
  "type": "import",
  "source_label": "Synthetic event export",
  "external_reference": "SRC-EVENT-001"
}
```

The exact import receipt retains the stronger Batch/Source/Proposal/Review/
Operation lineage.

### Import time is not domain time

The Event occurrence is:

```text
2026-08-15T09:05:00-04:00
```

The source snapshot is observed later at:

```text
2026-08-15T10:10:00-04:00
```

The source observation/import/review/materialization times therefore remain
operational provenance and are not substituted for Event time.

### Later missing-row snapshot

A second completed Import Batch uses the same mapping but a changed source
snapshot whose CSV contains only the header:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-06-structured-import-v2-missing-row.csv
sha256: 916b6eadc141fffa4789d897f67a57c17b71f6ed7a396a9ac93c0bd451430f9a
bytes: 44
rows: 0
```

It declares:

```text
relationship = changed_source_same_mapping
```

The previously materialized Event remains:

```text
status = active
```

No lifecycle, correction, supersession, or removal record is created merely
because `SRC-EVENT-001` disappeared from the later source.

### Fixture storage note

Import Batch is not behavior-domain work and carries no `work_id`. For this
representative corpus only, class-local import artifacts use the fixture
workspace convention:

```text
classes/<class_id>/modules/portia/imports/<import_batch_id>/...
```

This is test metadata for deterministic path/ownership checks, not a new public
Portia storage contract.

### Principal assertions

```text
Import Batch != Event
Import Source Record != Event
source assertion != Portia judgment
source "resolved" != Outcome/Determination
Import Proposal != canonical record
Import Review != domain Review
accepted Import Review != automatic materialization
row order != identity
import time != Event time
unchanged replay != duplicate canonical Event
later missing source row != deletion
```


## P22-07 — Immediate Response and family Communication

### Story

One Event has one exact roster-student participant.

The teacher takes a bounded immediate action:

```text
Response@1
family = environmental_or_instructional
execution_state = completed
```

The action is:

```text
Teacher offered the participant a quieter seat for the remainder of
independent work.
```

This is a Response because it is an Event-local human action.

It is not:

```text
evidence
Determination
Support
Outcome
proof of misconduct
proof that the action was justified
proof that the action was effective
```

No Determination is created because this is not a recorded institutional
consequence.

### Workspace Actor boundary

The family contact is a workspace Actor:

```text
portia/actors/actr_p22_family_001/actor.json
```

with:

```text
actor_category = family_or_caregiver
```

The Actor is not stored under the Event's class tree.

The Event and Communication remain class-owned consumers of that reusable Actor
identity.

### Contact Point boundary

The Actor owns:

```text
acp_p22_family_email_001@1
kind = email
verification = locally_confirmed
use_preference = preferred
```

Local confirmation means the teacher-local workspace has confirmed the
recorded endpoint for current use.

It does not establish:

```text
legal identity
exclusive control of the mailbox
consent
disclosure authorization
message delivery
message read status
```

### Actor-to-Student Relationship boundary

The Actor also owns:

```text
asrel_p22_family_001@1
relationship.type = family_contact
review.kind = locally_reviewed
```

The student target remains exact:

```text
eng10_p2_2026 + stu_p22_001
```

The relationship is useful teacher-local context. It does not establish legal
parentage, guardianship, custody, consent, disclosure permission, or decision
authority.

### Communication act

The Event-local Communication is:

```text
comm_p22_family_001@1
method = email
purpose = response_coordination
act_state = completed
privacy_scope = participant_limited
```

The listed recipient is the exact Actor, and the exact Contact Point is
referenced separately.

Crucially:

```text
recipient.participation = not_established
```

Therefore:

```text
listed recipient != established participation
completed communication act != proven delivery
verified endpoint != proven delivery
completed act != read receipt
```

### Relation to Response

The Communication carries an exact:

```text
relates_to_response
→ rsp_p22_family_001@1
```

That relation means the communication concerns the Response.

It does not establish that the Response worked, was appropriate, or caused any
later state.

### Principal assertions

```text
Response != evidence
Response != Outcome
Actor != family relationship
Actor != contact endpoint
Actor category != authority
Contact Point verification != consent
Contact Point verification != delivery
relationship != guardianship
relationship != disclosure permission
recipient != Event participant
listed recipient != participation
completed Communication != delivery/read proof
Communication relation != Response effectiveness
```


## P22-08 — Multi-Event Support Process through positive Outcome

P22-08 keeps three different layers explicit:

```text
Event evidence/context
Support planning and implementation
human Outcome evaluation
```

The graph is:

```text
Event A@2
  └─ Observation A@2  [baseline context]
        ↓
Support Process@1  [initiation = exact Event A]
  ├─ supported-person Participant@1
  ├─ teacher provider/coordinator/observer Participant@1
  ├─ Support Need@1
  ├─ Support Goal@1
  ├─ Support@1
  ├─ Implementation@1
  ├─ Implementation@1
  ├─ Fidelity@1
  ├─ Follow-Up@1
  └─ Outcome@1
        ↑
Event B@2
  └─ Observation B@2  [current-period context]
```

The Support Need is a bounded teacher-local environmental/instructional planning
statement. It is not diagnosis, disability determination, behavioral-function
finding, risk, eligibility, or permanent deficit.

The Goal contains planned criteria and a measurement approach. Those fields do
not assert progress or attainment.

The Support is an active plan. Its recurring schedule does not create actual
Implementation records. P22-08 therefore contains two separate Implementations,
each recording one actual occurrence.

Fidelity evaluates the exact two Implementations against the exact Support and
records:

```text
result = as_planned
```

That is adherence evidence only. It is not effectiveness or Outcome.

The completed Follow-Up selects:

```text
disposition = continue_current_support
```

Completion and disposition remain workflow facts. They do not generate or imply
the positive Outcome.

The Outcome is a distinct human evaluation:

```text
scope.kind = support_response_review
result = progress_observed
```

Its exact basis includes:

```text
baseline Observation from Event A
current-period Observation from Event B
both Implementation records
Fidelity
completed Follow-Up
```

The Outcome explicitly states that the comparison is bounded to the documented
review coverage and is not a causal-effect estimate.

The Support Process remains:

```text
workflow_state = active
```

after the positive Outcome. Outcome does not automatically close the workflow.

Principal assertions:

```text
Need != diagnosis
Goal criteria != attainment
Support plan != Implementation
schedule != Implementation
Implementation completion != Fidelity
Implementation completion != Outcome
Fidelity != effectiveness
completed Follow-Up != favorable Outcome
Outcome != automatic software inference
positive Outcome != causal proof
positive Outcome != automatic Support Process completion
Event evidence may inform Outcome without changing work ownership
```

## P22-09 — Inconclusive and adverse/unintended Outcomes

P22-09 keeps uncertainty and adverse-effect review separate instead of forcing
one mutable outcome state.

The graph is:

```text
Event A@2
  └─ Observation A@2  [baseline context]
        ↓
Support Process@1  [initiation = exact Event A]
  ├─ supported-person Participant@1
  ├─ teacher provider/coordinator/observer Participant@1
  ├─ Support Need@1
  ├─ Support Goal@1
  ├─ Support@1
  ├─ Implementation 1@1
  ├─ Outcome A@1  [inconclusive]
  ├─ Implementation 2@1
  └─ Outcome B@1  [later adverse-effect review]
        ↑                         ↑
Event B@2                    Event C@2
  └─ Observation B@2          └─ Observation C@2
     [short/interrupted]          [later bounded window]
```

The first Outcome asks a support-response question during an observation window
that ends after roughly three minutes because of a synthetic schoolwide drill:

```text
scope.kind = support_response_review
result = unable_to_determine
limitations = [insufficient_observation_opportunity]
```

Its exact basis includes the baseline Observation, the interrupted current-period
Observation, and the first actual Implementation. The Outcome says explicitly
that missing observation coverage is not a negative result. It does not convert
missingness into `no_clear_progress`, worsening, or an adverse finding.

A later observation supplies evidence for a different question. The later
Outcome is therefore a second immutable Outcome rather than a correction or
supersession of the earlier valid evaluation:

```text
scope.kind = unintended_or_adverse_effect_review
result = change_observed
coverage.coverage_kind = direct_observation
```

That Outcome records only the bounded later observation: during a whole-class
transition, the participant continued the prior task until the teacher approached
and repeated the direction. The fixture does not claim that the Support caused
the observed change, caused harm, or established general deterioration.

Both Outcomes remain:

```text
status = active
```

and neither contains `supersedes`. Their questions and timeframes differ, so the
later evaluation coexists with the earlier one as a separate attributable human
judgment.

The Support Process also remains:

```text
workflow_state = active
```

Principal assertions:

```text
missing evidence != negative result
unable_to_determine != adverse finding
inconclusive Outcome != adverse-effect Outcome
later changed evaluation question/timeframe != correction
later Outcome != automatic supersession
bounded adverse observation != causal-effect estimate
temporal overlap with Support != Support caused change
more/fewer Events != proof of improvement/deterioration
Outcome != automatic Support Process completion
```



## P22-10 — Reentry and Repair without overclaiming

P22-10 uses one classroom Event with two exact Event Participants and two
firsthand Accounts whose perspectives remain separate. The teacher records an
immediate environmental/instructional Response and an in-person Communication
about the bounded classroom transition.

The downstream graph is:

```text
Event@2
  ├─ Participant A@3
  ├─ Participant B@3
  ├─ Account A@2
  ├─ Account B@2
  ├─ Response@1
  ├─ Communication@1
  ├─ Reentry@1 [completed]
  ├─ Repair@1  [completed]
  └─ Follow-Up@1 [completed]
```

The Reentry keeps planning and actual completion distinct:

```text
planned_return = 2026-09-15
planned_elements = orientation/check-in + relationship reconnection
workflow_state = completed
completed_at = exact timestamp
```

`completed` means the bounded return process completed. It does not encode
safety clearance, readiness, rehabilitation, legal access authority, or proof
that the earlier classroom separation was justified.

Repair preserves neutral participation rather than inferring attitude or truth:

```text
student_a.participation_state = participated
student_b.participation_state = declined
action.agreed_by = [student_a]
action.completion_state = completed
```

The Repair focus explicitly declines to decide which Account is true. The
completed action belongs only to the participant who agreed to it, so completion
does not imply Student B participated, that either Account was adjudicated, or
that anyone admitted wrongdoing, felt remorse, forgave another person, or
restored a relationship.

A later `repair_check` Follow-Up exact-links the Reentry and Repair as reviewed
records. Follow-Up completion remains a workflow fact; no Outcome is fabricated.

Principal assertions:

```text
Account A != Account B
Response != Communication
Reentry plan != actual Reentry completion
Reentry completion != safety clearance
Reentry completion != rehabilitation
Repair participation != admission of wrongdoing
Repair completed action != mutual participation
Repair completion != remorse
Repair completion != forgiveness
Repair completion != relationship restored
completed Follow-Up != favorable Outcome
```

## P22-11 — Cross-year Support continuation

P22-11 represents reviewed continuity without turning a Support Process into an
all-years student case file. The graph contains two independently owned Support
Process roots:

```text
2026-2027 / eng10_p2_2026
Support Process A@1  [workflow_state = completed]
  ├─ Participant A/student@1
  ├─ Participant A/teacher@1
  ├─ Need A@1
  ├─ Goal A@1
  ├─ Support A@1  [plan_state = completed]
  ├─ Implementation A@1
  ├─ Observation A@2
  └─ Outcome A@1
           │
           │ exact process continuity only
           ▼
2027-2028 / eng11_p3_2027
Support Process B@1  [workflow_state = active]
  continues_from -> exact Support Process A@1
  ├─ Participant B/student@1
  ├─ Participant B/teacher@1
  ├─ Need B@1
  ├─ Goal B@1
  ├─ Support B@1  [adapted current-year procedure]
  ├─ Implementation B@1
  ├─ Observation B@2
  └─ Outcome B@1
```

The successor is not a moved predecessor. It has a new class-qualified work
identity and a new school year:

```text
A = eng10_p2_2026 / sup_p22_crossyear_2026 / 2026-2027
B = eng11_p3_2027 / sup_p22_crossyear_2027 / 2027-2028
```

Only the process root carries the accepted cross-year relation:

```text
B.continues_from = exact A@1
```

Neither root contains `supersedes`, and the scenario contains no
`record_migration` or `ownership_correction`.

Each year creates new participant and child-record identities. The current-year
Need, Goal, Support, Implementation, Observation, and Outcome are not copies or
current aliases of predecessor children. The current-year Support deliberately
adapts the earlier task-sequencing idea from a short two-step assignment aid to
a research-planning template with separate source-selection, note-taking, and
drafting sections.

The two synthetic roster contexts intentionally reuse the same local-looking
`student_id` and display name across different classes. That collision is not
used as a global person key. The participant references remain:

```text
eng10_p2_2026 + stu_p22_crossyear_001
!=
eng11_p3_2027 + stu_p22_crossyear_001
```

Cross-year continuity is therefore a reviewed process relationship, not a
workspace-global student identity claim.

Outcome A remains permanently bound to predecessor-year Observation A and
Implementation A. Outcome B is a distinct new-year evaluation with only
successor-year Observation B and Implementation B in its basis. The existence
of B never retargets A's exact references.

Principal assertions:

```text
cross-year continuation != migration
cross-year continuation != ownership correction
new process != old process moved
continues_from != supersedes
new class/year => new Support Process identity
new participant instance != predecessor participant identity
old child records != silently cloned current records
old exact refs remain pinned to predecessor
new-year plan facts require new records
new-year Implementation facts require new records
new-year Observation/Outcome facts require new records
repeated local student_id/display name != global student identity
```



## P22-12 — Participant-specific privacy projection and deliberate export

P22-12 keeps the canonical multi-participant Event intact while deriving one
student-facing representation for exact Participant B. The projection itself is
noncanonical test metadata; it does not replace, redact, or rewrite source JSON.

```text
Event@2
├─ Participant A@3                 [third party]
├─ Participant B@3                 [exact focal subject]
├─ Account A@2                     [third-party attribution/text]
├─ Account B@2                     [focal source; has raw source artifact]
└─ Observation B@2                 [direct focal observation]
          │
          ├─ exact policy + exact authorization
          ├─ noncanonical projection decision
          │    ├─ included
          │    ├─ withheld
          │    ├─ absent
          │    ├─ unavailable
          │    └─ requires_manual_review -> withheld without paraphrase
          │
          └─ deliberate_export@1
               ├─ contributing-source inventory only
               └─ exact CSV digest / length / opaque export path
```

The source artifact attached to Account B is deliberately not authorized for
export. Projecting the Account summary therefore does not bootstrap access to
the raw artifact. Account A's source identity and free text remain present in
canonical source records but never enter the output bytes or contributing-source
inventory.

Principal assertions:

```text
projection != canonical record
student-facing purpose != authorization
withheld != absent
unavailable != false/no
requires_manual_review != safe-to-include
stable IDs != safe pseudonyms
manual review != automatic paraphrase
safe projected record != source-artifact authorization
export inventory != inventory of withheld identities
export generated != disclosure/delivery/read/consent
```


## P22-13 — Rebuildable derived views and retention/custody boundary

P22-13 uses one primary Event, one exact contextual Event, a focal Participant,
an append-preserving Account correction, two Lifecycle Transitions, one forward
Work Relationship, and one forward Dependency. Canonical forward records remain
the authority.

From those exact records the fixture deterministically rebuilds eight
noncanonical views:

```text
incoming-reference index
work-relationship reverse index
replacement/current frontier
dependency graph
lifecycle timeline
work summary
class summary
participant-specific work-scoped history
```

One representative replacement-frontier generation additionally exercises the
accepted `source_snapshot@1`, `derived_index_metadata@1`, and
`derived_current_pointer@1` contracts. The source snapshot fingerprints the
exact canonical Account representations; the immutable `dgen_` metadata binds
the complete data artifact; and the explicit pointer selects that generation
without embedding a freshness claim.

The participant-specific view remains bounded to the exact Event Participant
and work root. The class summary contains work-level counts/status only and does
not become a longitudinal student dossier.

Retention/custody expectations preserve:

```text
derived_cache != canonical_behavior_support
export_bytes != export_provenance
Portia custody != Core retained-source custody
Portia disposition != Core/sibling/external destruction
```

No legal duration is calculated and no Portia retention-policy or Sunset public
record is invented.

Principal assertions:

```text
canonical forward records remain authority
derived reverse links are rebuildable, not hand-authored authority
missing derived index != empty canonical graph
deleting derived cache != deleting canonical records
unchanged source rebuild => same semantic view
changed source fingerprint => stale prior snapshot
explicit current pointer != newest-generation inference
exact predecessor ref != current successor
derived-cache retention != canonical retention
foreign custody != Portia destruction authority
```


## P22-14 — Coordinated operation and recovery boundary

P22-14 performs one material correction to a canonical Work Relationship using
the accepted Issue #13 Operation Journal, current-pointer, and lock contracts.
The domain result remains ordinary Portia canonical state: the original
relationship is retained as `superseded`, while one distinct corrected
relationship is `active` and exactly supersedes it.

The operational sequence is deliberately interrupted after the corrected
successor has already been accepted but before the predecessor representation
has been replaced with its final superseded state:

```text
revision 1  prepared   : exact preflight; no canonical mutation
revision 2  staged     : both candidate representations validated
revision 3  committing : corrected successor accepted; predecessor write remains
                         [synthetic interruption]
revision 4  recovering : accepted successor reconciled as exact replay; no recreate
revision 5  committed  : predecessor supersession also accepted; commit point reached
revision 6  completed  : locks released; no remaining canonical/post-commit work
```

The exact operation current pointer selects revision 6. Two real
`operation_lock@2` fixtures use the accepted digest-derived lock identity recipe:
one operation lock and one work lock. Their fingerprints are carried in the
post-acquisition journal revisions.

The journals contain only typed targets, state facts, fingerprints, paths,
write dispositions, lock state, and recovery evidence required to coordinate
the operation. They do not copy the Work Relationship narrative or replace the
canonical source/target/detail assertions.

Principal assertions:

```text
preflight occurs before mutation
Operation Journal != domain truth
accepted canonical successor != disposable rollback artifact
interrupted multi-record operation != graph-wide atomic failure
partial success is explicit
restart reconciles exact observed state before replay
exact replay != duplicate create
recovery completes remaining canonical work without deleting accepted evidence
commit point requires every canonical gate accepted
current journal revision requires explicit pointer selection
completed operation releases locks
```


# Schema-valid / graph-invalid corpus

## G22-001 through G22-010 — Identity, ownership, and exact references

The first graph-invalid batch deliberately keeps every public record JSON-Schema
valid while breaking one application invariant per fixture. The expected primary
findings are stable and machine-checked:

```text
G22-001  G22.EVIDENCE.ROLE_BASIS_UNRESOLVED
G22-002  G22.EVIDENCE.WRONG_WORK
G22-003  G22.OWNERSHIP.CANONICAL_PATH_MISMATCH
G22-004  G22.REFERENCE.PARTICIPANT_VERSION_MISMATCH
G22-005  G22.IDENTITY.CROSS_CLASS_LOCAL_ID_MERGE
G22-006  G22.IDENTITY.DISPLAY_NAME_MERGE
G22-007  G22.IDENTITY.ACTOR_ROSTER_SUBSTITUTION
G22-008  G22.REFERENCE.PARTICIPANT_TARGET_MISSING
G22-009  G22.REFERENCE.FOREIGN_SUBSTITUTION
G22-010  G22.REFERENCE.HISTORICAL_SUCCESSOR_FOLLOW
```

The two cross-class identity cases demonstrate that neither repeated local
`student_id` nor equal display name is a suite-wide identity key. G22-007 keeps
Actor Directory identity separate from class-qualified roster identity. G22-009
keeps a foreign/Core roster reference foreign rather than resolving it through a
local Portia Actor. G22-010 proves exact historical references are not
current-pointer references and cannot silently follow a corrected successor.

Where the invalid state is itself a resolver result rather than a public Portia
record, the fixture uses a closed test-only `pds-portia.synthetic-*` expectation.
This is noncanonical corpus metadata; the underlying public records remain
ordinary contract fixtures.

## G22-011 through G22-016 — Lifecycle, correction, dependency, and continuation

The second graph-invalid batch keeps each declared public record structurally
valid while exercising application invariants that require graph or derived
semantics:

```text
G22-011  G22.CORRECTION.SUPERSESSION_CYCLE
G22-012  G22.DERIVED.CURRENT_SELECTS_PREDECESSOR
G22-013  G22.CORRECTION.DISAGREEMENT_WRONG_TARGET
G22-014  G22.DEPENDENCY.REQUIRED_TARGET_UNRESOLVED
G22-015  G22.MIGRATION.HISTORICAL_RETARGET
G22-016  G22.SUPPORT.CONTINUATION_ENCODED_AS_MIGRATION
```

G22-011 uses two exact Account replacements that point to each other. G22-012
retains the valid active successor but declares a stale derived replacement
selection that still chooses the superseded predecessor. G22-013 targets a
real, schema-valid Account, but not the exact Account the synthetic source
actually contests. G22-014 names a required Account dependency under Event A
while the only matching Account exists in Event B.

G22-015 uses a structurally valid Event-v1-to-v2 Record Migration certificate
while deliberately changing the accepted Event summary and then retargeting an
exact historical Event@1 reference. That is both a semantic-correction boundary
and an exact-reference boundary: migration never rewrites old references.
G22-016 creates a new Support Process in a new class/year but omits
`continues_from` and encodes the predecessor/successor link as Record Migration,
which collapses cross-year continuity into representation migration.


## G22-017 through G22-020 — Evidence and judgment

The third graph-invalid batch preserves the evidence/judgment distinctions that
cannot be established by JSON Schema alone:

```text
G22-017  G22.EVIDENCE.ROLE_BASIS_UNRESOLVED
G22-018  G22.EVIDENCE.WRONG_WORK
G22-019  G22.JUDGMENT.IMPORT_ACTIVE_WITHOUT_REVIEW
G22-020  G22.JUDGMENT.IMPORT_ASSERTION_AS_DETERMINATION
```

G22-017 keeps the active `reported_involved` role itself structurally valid by
including the Account-basis shape required by the current role contract, but the
exact Account does not exist in the owning Event. This distinguishes structural
presence of a provenance reference from successful provenance resolution.

G22-018 gives an Event-A Determination a fully formed exact evidence reference to
a real Observation in Event B. The record exists, but it is outside the accepted
owner-local evidence scope. G22-019 uses an active import-origin Determination
with explicit human attribution but no review history, isolating the import
activation gate rather than conflating it with a missing attribution field.

G22-020 deliberately supplies a completed Review and an exact `review_ref` so it
does not collapse into G22-019. Closed test-only semantic metadata states that
the review covered source mapping only and that no human decision occurred; the
source assertion was copied into Determination meaning. That semantic assertion
is necessary because graph topology cannot infer whether a human actually made
a decision from arbitrary narrative text.

## G22-021 through G22-025 — Response, Support, and Outcome

The fourth graph-invalid batch tests owner-local Support Process semantics and
Outcome identity/history without weakening the public contracts:

```text
G22-021  G22.SUPPORT.IMPLEMENTATION_PLAN_WRONG_PROCESS
G22-022  G22.SUPPORT.FIDELITY_IMPLEMENTATION_WRONG_PROCESS
G22-023  G22.OUTCOME.TARGET_WRONG_PROCESS
G22-024  G22.OUTCOME.IDENTITY_REUSED_FOR_LATER_EVALUATION
G22-025  G22.SUPPORT.HISTORICAL_PROCESS_SUCCESSOR_FOLLOW
```

G22-021 gives an Implementation a structurally valid local `plan_ref` whose
Support exists only under another Support Process. G22-022 gives Fidelity a
valid local plan but scopes an Implementation owned by a different Support
Process. The resolver distinguishes these from genuinely dangling references so
the primary finding records the actual ownership defect.

G22-023 keeps the Outcome evaluator, scope, and basis locally resolvable while
targeting a participant that exists only in a different Support Process. This
is invalid even though the participant reference shape and the foreign
participant record are both valid.

G22-024 separates new evaluation from correction: one accepted Outcome remains
unchanged while test-only write metadata describes an attempted later-timeframe
overwrite using the same exact identity. G22-025 similarly keeps the valid
cross-year `continues_from` edge intact but proves that the edge does not turn an
exact historical predecessor reference into a current/successor reference.

## G22-026 through G22-029 — Paper, Import, and Operations

The fifth graph-invalid batch exercises retry/idempotency, review gating, and
durable operation reconciliation while keeping every public contract fixture
structurally valid:

```text
G22-026  G22.IMPORT.ACCEPTED_PROPOSAL_DUPLICATE_MATERIALIZATION
G22-027  G22.PAPER.MATERIALIZATION_REVIEW_UNRESOLVED
G22-028  G22.OPERATION.COMMITTED_RESULT_UNRESOLVED
G22-029  G22.OPERATION.RESTART_REPLAYS_COMMITTED_WRITE
```

G22-026 uses two distinct valid Event identities plus closed nonruntime replay
metadata binding both to the same unchanged retained-source and accepted proposal
identity. A retry may reconcile the already accepted result; it may not create a
second accepted domain record merely because the intake is processed again.

G22-027 gives a valid Capture Materialization an exact review reference that does
not resolve. Fixture-only resolution metadata states that the proposal itself is
known, keeping the primary defect at the required human review gate rather than
conflating it with proposal lineage.

G22-028 uses a completed Operation Journal whose accepted canonical write set
claims two durable results, while one exact successor record is deliberately
absent. The journal is operational evidence, not authority to fabricate missing
canonical truth. G22-029 is the complementary recovery case: both accepted
canonical results exist, but the restart decision tries to replay an already
durable semantic write instead of reconciling exact readback and continuing only
remaining work.


## G22-030 through G22-037 — Privacy, Export, Derived State, and Custody

The final enumerated graph-invalid batch applies the Issue #21 privacy/export/
retention boundaries to combined representative graphs while preserving
structural validity of every public contract fixture:

```text
G22-030  G22.PRIVACY.PROJECTION_LEAKS_UNRELATED_DATA
G22-031  G22.PRIVACY.PROJECTION_STATE_COLLAPSE
G22-032  G22.PRIVACY.EXPORT_INVENTORY_WRONG_REPRESENTATION
G22-033  G22.PRIVACY.EXPORT_OUTPUT_PATH_PII
G22-034  G22.DERIVED.INCOMING_INDEX_DISAGREES_FORWARD_REFS
G22-035  G22.DERIVED.CURRENT_VIEW_INCLUDES_PREDECESSOR
G22-036  G22.DERIVED.STALE_SOURCE_SNAPSHOT_ACCEPTED
G22-037  G22.CUSTODY.FOREIGN_DESTRUCTION_UNVERIFIED
```

G22-030/031 demonstrate that focal projection is both source-bounded and
state-preserving: unrelated native identities or unsafe Account segments do not
become safe merely because a focal participant is selected, and `withheld` /
`unavailable` cannot be rewritten as `absent` / false.

G22-032 keeps both Account predecessor and successor valid and makes the export
inventory fingerprint truthful for the successor; the defect is that the
historical output actually consumed the predecessor. G22-033 similarly keeps
the export path under the correct opaque export-ID directory but rejects
unnecessary person/class/behavior labels in the filename.

G22-034/035 treat reverse/current projections as rebuildable views over canonical
forward truth. G22-036 uses a real structurally valid `source_snapshot@1` but
accepts it after its exact canonical source bytes have changed, demonstrating
that structural snapshot validity is not freshness. G22-037 closes the custody
boundary: a successful Portia-local action cannot certify destruction of Core
retained sources, Vitrine copies, email/downloads, backups, or other externally
owned copies without authoritative owner verification.

With G22-030 through G22-037 implemented, all **37 enumerated graph-invalid
scenarios** are present. Corpus completion remains distinct from final Issue #22
contract-coverage and handoff closeout.

## P22-15 — Supplemental Classification / Hypothesis / Intervention coverage

P22-15 is an additional positive story added after the coverage audit found that
the Issue #22 positive corpus must itself exercise current Classification,
Hypothesis, and Intervention contracts.

```text
Event
  -> Event Participant
  -> Account
  -> Observation
  -> completed Review
       -> reviewer-selected Classification
       -> tentative Hypothesis (under consideration)

Event
  -> Support Process
       -> supported-person Participant
       -> provider Participant
       -> Support Need
       -> Support Goal
       -> Intervention (recurring plan)
            -> one Implementation (actual occurrence)
```

The Classification is an attributable local category selection with an exact
definition snapshot and exact evidence basis. It is not a Determination. The
Hypothesis remains a tentative proposition with explicit evidence roles and does
not encode diagnosis, behavioral function, intent, credibility, confidence, or
risk.

The Intervention is owned by the Support Process, targets its exact supported
participant, resolves its Need and Goal locally, and uses an exact assigned
provider. Its recurring schedule is planning only. The Implementation is a
separate immutable record for one actual occurrence and does not establish
Fidelity, Goal attainment, effectiveness, or Outcome.

This supplemental story does not alter the semantics of P22-01 through P22-14
and adds no public contract surface.

