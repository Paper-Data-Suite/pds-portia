# ADR 0013: Define Response and Communication Domain Models

- **Status:** Accepted
- **Date:** 2026-08-09
- **Decision owners:** Portia maintainers
- **Related issue:** `#17 — Define Response and Communication domain models`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Builds on:** ADR 0001, ADR 0002, ADR 0010, ADR 0011, and ADR 0012
- **Refines:** ADR 0002's broad "family contact" shorthand by defining Communication as its own canonical act

## Context

ADR 0001 established the foundational rule that Portia must separate source
evidence, interpretation, formal decision, response/support, and later outcome.
ADR 0002 assigned immediate behavior-related actions and family communication to
Portia's domain. ADR 0011 made the Account/Observation source-evidence layer
concrete, and ADR 0012 made Review, Classification, Hypothesis, and
Determination concrete.

Issue #17 defines the next layer:

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

The arrows describe possible workflow progression rather than mandatory record
creation.

The architecture must keep action and communication from becoming implicit
proof. The fact that a teacher redirected, removed, referred, or otherwise
responded to a student does not establish that the underlying allegation,
Classification, Hypothesis, or Determination was correct. Likewise, the fact
that a Communication was attempted or completed does not establish that its
contents were true, that the intended recipient read or understood it, that
legal notice was sufficient, or that a listed recipient participated.

The current product remains local-first, teacher-controlled, and
classroom-focused. It is not an institutional messaging transport, district
discipline system, legal-notice engine, threat-assessment platform, or clinical
case-management system.

## Decision

### 1. Response is one bounded Event-local action

One Response represents one bounded action that a represented provider took,
attempted, initiated, or completed in direct relation to one Event or its
Event-local review/decision context.

Response is distinct from:

```text
Event
Account
Observation
Classification
Hypothesis
Determination
Support
Intervention
Outcome
```

A Response never establishes that misconduct occurred, an allegation was true,
a Determination was correct, an action was justified, or an action was
effective.

Response v1 is Event-local.

Canonical identity is:

```text
rsp_<opaque-id>
```

with public identifier contract:

```text
portia_response_id@1
```

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/response/<response_id>.json
```

The identifier encodes no student, provider, action, severity, consequence,
policy, status, or date information.

### 2. Response reuses Event-local targeting

Response v1 reuses:

```text
portia_target_ref@1
```

and therefore targets:

```text
event
event_participant
event_participants
```

The target identifies the recipient/scope of the action.

No parallel `response_target@1` contract is introduced.

An Event-level Response records an Event-level action. It does not imply that
every Participant received the same person-specific action or consequence and
does not imply equal responsibility.

Response is never owned directly by a roster student or Actor as a durable
person-level action history.

### 3. Response provider reuses represented-human attribution

Response provider reuses:

```text
represented_human_attribution@1
```

The provider is the represented human who performed or attempted the action.

Provider remains distinct from:

```text
created_by
updated_by
```

Represented-human identity does not itself establish action eligibility,
institutional authority, employment status, or delegation.

Application validation governs provider eligibility by action context.

A system process may persist a proposed record but may not masquerade as the
human Response provider.

### 4. Response uses one descriptive action object

Response v1 uses an action object with:

```text
family
description
consequence_context?
```

`description` is a concise human-readable statement of what the provider did or
attempted.

Accepted action families are:

```text
classroom_management
environmental_or_instructional
support_access
de_escalation
safety_or_protective
referral_or_handoff
restorative_or_repair
consequence
other
```

`family` describes the provider action, not the student.

Response v1 contains no action severity score, student-risk score, culpability
score, credibility score, punishment recommendation, effectiveness rating, or
Outcome field.

### 5. Consequence context is explicit and narrow

When:

```text
action.family = consequence
```

the action also identifies:

```text
teacher_local
recorded_institutional
```

consequence context.

A teacher-local consequence may exist without a Determination.

A `recorded_institutional` consequence requires an exact same-Event
Determination reference.

The exact Determination reference means that the Response records implementation
of or action following that recorded decision. It does not prove:

```text
the Determination was correct
the authority was legally sufficient
the policy was correctly applied
the consequence was lawful
the consequence was proportionate
the consequence was effective
```

Response does not copy the Determination's authority or policy/process basis.

### 6. Review and Determination links are exact context, not evidence

Response may retain exact same-Event:

```text
review_ref
determination_ref
```

where relevant.

Those references identify historical context.

They do not become evidence roles and do not make either source record
automatically applicable to every Response.

`recorded_institutional` consequence requires `determination_ref`.

Other Response families may reference a Determination only when the relationship
is meaningful.

### 7. Immediate Response is distinct from ongoing Support

Response is a bounded Event-local action.

Support/Intervention under #18 is planned, recurring, scheduled, longitudinal,
goal-directed, implementation-tracked, or fidelity-tracked activity.

Examples:

```text
offer established break option during this Event
→ Response

standing break-access plan
→ Support

temporary seating change during this Event
→ Response

planned multi-week seating intervention
→ Support

counselor handoff requested
→ Response

recurring counselor check-ins
→ Support
```

No arbitrary time threshold replaces this semantic distinction.

Repeated actions do not silently turn one Response into a longitudinal Support
record.

### 8. Referral/handoff state does not establish downstream service

Referral or handoff is a Response action family.

Examples include:

```text
administrative assistance requested
counselor handoff requested
restricted workflow notified
student escorted to designated support location
```

The Response execution state records the bounded action only.

A completed handoff does not establish that a later Support or Intervention was
implemented.

### 9. Restricted crisis workflows are outside ordinary Response payloads

Ordinary Response may record bounded protective actions and minimal handoffs.

It must not become the canonical case record for:

```text
restraint
seclusion
threat assessment
self-harm/suicide process
suspected abuse/neglect investigation
sexual-violence investigation
law-enforcement investigation
medical emergency treatment
clinical intervention
```

Where necessary, ordinary Response records only the minimal safe action or
handoff without copying restricted details.

### 10. Response execution state is separate from lifecycle and Outcome

Accepted Response execution states are:

```text
attempted
in_progress
completed
partially_completed
discontinued
unable_to_complete
unknown
```

Execution state describes whether the bounded action occurred and to what
extent.

It does not describe whether the action was:

```text
successful
effective
appropriate
resolved
```

Those are Outcome/evaluation concepts owned by later work.

### 11. Response preserves explicit action time

Response v1 requires:

```text
started_at
```

and optionally permits:

```text
ended_at
```

using the existing explicit-offset timestamp primitive.

Application validation requires:

```text
ended_at >= started_at
```

when `ended_at` is present.

No evidence-specific time primitive is reused merely for shape convenience.

### 12. Response reuses the shared canonical lifecycle

Response lifecycle is:

```text
proposed
active
invalidated
superseded
```

and reuses existing lifecycle/history infrastructure with Response-specific
reason vocabularies.

Invalidation means the Response representation is defective, such as:

```text
wrong provider
wrong target
wrong Event
wrong action
wrong timing
wrong decision context
action did not occur
invalid provenance
```

Invalidation does not mean ineffective, disliked, disproportionate, disputed,
or superseded by a later Support strategy.

Material correction uses successor/history semantics.

### 13. Response v1 exposes no Amendment paths

Response v1 permits no application-level `amendment@1` paths.

Provider, target, action, execution state, material timing, and decision context
all affect the historical claim about what action occurred.

The generic Amendment contract remains structurally reusable, but application
policy prohibits Response amendment until a later version demonstrates a stable
nonmaterial field that can be edited safely.

### 14. Communication is one bounded Portia-work-local communication act

One Communication represents one bounded communication act or attempt
associated with one canonical Portia work context.

Communication is distinct from:

```text
Account
Response
Determination
Support
mutable message thread
proof of delivery
proof of participation
proof of legal notice
```

Canonical identity is:

```text
comm_<opaque-id>
```

with public identifier contract:

```text
portia_communication_id@1
```

Canonical storage is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/communication/<communication_id>.json
```

Communication v1 is Portia-work-local rather than Event-only.

Its work kind is:

```text
event
support_process
```

This is compatible with already-published Portia exact work identity, which
already recognizes Event and Support Process work kinds.

Until `support_process@1` is published by #18, current active-use
Communication requires a resolvable Event owner. Structural support for
`support_process` avoids an immediate future Communication wire-version bump
without fabricating Support Process semantics in #17.

No workspace-global correspondence dossier is introduced.

### 15. Communication sender is represented human, not recorder

Human sender reuses:

```text
represented_human_attribution@1
```

Sender remains separate from persistence attribution.

Communication v1 does not introduce system-originated canonical Communication.

A system may create a template or draft, but that does not create a completed
Communication. Future transport infrastructure may add a separately governed
machine-originated model if needed.

### 16. Communication recipients are explicit represented humans

Communication requires one or more recipient entries.

Each recipient contains:

```text
person
endpoint_ref?
```

`person` reuses:

```text
represented_human_attribution@1
```

Recipient identity does not establish:

```text
guardianship
educational decision rights
consent
communication authorization
entitlement to all Portia information
```

Recipient order has no semantic meaning.

Application validation rejects duplicate logical recipient identity even when
different display snapshots make JSON values structurally distinct.

### 17. Exact Actor Contact Point may preserve the historical endpoint

When an Actor recipient was contacted using a known Actor Contact Point,
`endpoint_ref` may use:

```text
exact_actor_contact_point_ref@1
```

Application validation requires the Contact Point Actor to match the recipient
Actor and requires exact historical resolution.

The Communication never silently follows a corrected or superseded Contact
Point.

Existing semantics remain unchanged:

```text
preferred != consent
locally_confirmed != delivery
locally_confirmed != institutional verification
locally_confirmed != exclusive control
Actor identity != communication authorization
```

Raw email addresses or phone numbers are not copied into Communication when an
exact Contact Point reference is sufficient.

No Actor must be fabricated merely to represent a one-off descriptive recipient.

### 18. Communication method is a closed descriptive vocabulary

Accepted method values are:

```text
in_person
phone_call
voicemail
text_message
email
letter
portal_or_system_message
video_call
other
unknown
```

`other` requires bounded detail.

`unknown` exists for historical/imported material.

Method identifies channel only.

It does not establish delivery, reading, identity verification, understanding,
or legal service.

### 19. Communication purpose is a closed descriptive vocabulary

Accepted purpose values are:

```text
information_sharing
request_for_information
notice
scheduling
review_coordination
determination_notice
response_coordination
support_coordination
referral_or_handoff
follow_up
reentry_or_repair
other
unknown
```

`other` requires bounded detail.

Purpose does not establish that the named workflow or notice requirement was
completed.

### 20. Communication act state preserves attempts without moralizing

Accepted act-state values are:

```text
attempted
completed
recipient_unavailable
recipient_declined
interrupted
unknown
```

State values such as:

```text
family_refused
ignored
uncooperative
successful
effective
```

are not canonical v1 states.

A later successful contact is a new Communication, not a mutation or
supersession of an earlier unsuccessful attempt merely because it happened
later.

`completed` describes completion of the documented communication act from the
recorded workflow perspective. It does not establish message delivery, reading,
understanding, agreement, or legal sufficiency.

### 21. Communication preserves explicit act time

Communication requires:

```text
started_at
```

and optionally permits:

```text
ended_at
```

using explicit-offset timestamps.

Application validation enforces chronology.

Instantaneous/send-style Communications may omit `ended_at`.

No unsupported read/delivery timestamp is inferred.

### 22. Communication v1 is summary-oriented, not a message archive

Communication v1 may store a bounded recorder-authored:

```text
summary
```

It does not provide an unrestricted canonical mutable message-body field.

The summary describes the purpose/substance of the contact act.

It is not automatically an exact quotation or authoritative source-evidence
statement.

Reasons for the summary-only v1 model:

1. Portia is not a general messaging archive.
2. Full message bodies increase privacy exposure.
3. Substantive source assertions belong in Account when they matter as
   evidence.
4. Exact documents can be preserved through bounded attachment/reference
   mechanisms where appropriate.
5. Ordinary teacher-local workflows need a record of contact, not necessarily a
   duplicate of every transport payload.

A future exact-message transport/archive feature may require a later contract
version.

### 23. Communication remains separate from Account evidence

Communication records that a communication act occurred.

Account records what a represented source asserted when the substantive
statement matters as source evidence.

Example:

```text
Communication:
family phone call occurred

Account:
family member reported that the student believed an alarm was sounding
```

A Communication may retain an exact relation to such an Account, but the
Communication itself does not become judgment evidence by implication.

Long narratives should not be copied into both families.

### 24. Communication attachments are schema-local in v1

`source_artifact_ref@1` is not reused directly for Communication attachment
semantics because its published meaning is specifically material associated with
Account or Observation.

Issue #17 does not broaden that published contract.

Communication v1 therefore defines an attachment union locally inside
`communication@1`.

Accepted branches are:

```text
workspace_file
portia_record
module_record
external_record
```

`workspace_file` preserves:

```text
workspace-relative path
content fingerprint
```

`portia_record` uses:

```text
exact_portia_work_record_ref@1
```

`module_record` uses:

```text
module_work_record_ref@1
```

`external_record` preserves bounded inert system/reference metadata.

External references are not dereferenced automatically.

Binary payloads are never embedded in Communication JSON.

Paper-capture attachment semantics remain deferred to #20.

No new public `communication_attachment_ref@1` contract is introduced until a
second stable consumer demonstrates a genuinely reusable semantic unit.

### 25. Communication uses typed exact record relations

Communication may own forward relations shaped as:

```text
relation
record_ref
detail?
```

where `record_ref` reuses:

```text
exact_portia_work_record_ref@1
```

Accepted relation values are:

```text
responds_to
communicates
requests
coordinates
notifies_about
conveys_determination
documents_handoff_for
relates_to_response
account_from_communication
other
```

`other` requires bounded detail.

Application validation constrains relation-to-record-kind compatibility.

Examples:

```text
responds_to
→ Communication

conveys_determination
→ Determination

relates_to_response
→ Response

account_from_communication
→ Account
```

Exact references never silently follow successors.

`work_relationship@2` remains a work-to-work `draws_context_from` relation and
is not broadened into a generic record-to-record relationship contract.

### 26. Response and Communication remain independently canonical

A single real-world workflow may produce one or both families.

Examples:

```text
teacher phones family
→ Communication

family contact explicitly tracked as an immediate Event action
→ Response + Communication relation

counselor handoff requested by phone
→ Response + Communication

administrator decides consequence
→ Determination

teacher conveys decision
→ Communication

consequence implemented
→ Response
```

ADR 0013 therefore refines ADR 0002's broad statement that "family contact" is
an Immediate Response.

The Communication act is canonical Communication. It becomes a separate
Response only when the contact act itself is deliberately tracked as an
Event-local action.

Payloads are not duplicated merely because both records exist.

### 27. Family/student participation is descriptive, not scored

Communication may preserve explicit facts such as:

```text
communication completed with family member
recipient unavailable
recipient declined proposed meeting
student participated in conversation
```

Recipient listing alone does not establish participation.

Voicemail or email send does not establish recipient participation.

Issue #17 introduces no:

```text
family engagement score
parent responsiveness score
student attitude score
remorse score
compliance score
```

### 28. Communication requires a minimal privacy scope

Communication v1 requires one of:

```text
ordinary
participant_limited
restricted
unknown
```

The field is a handling classification, not an authorization engine.

It does not implement:

```text
FERPA authorization
legal privilege
RBAC
redaction
disclosure sufficiency
```

Issue #21 owns full projections/redaction/export/retention policy.

Ordinary Communication must not become a container for clinical, counseling,
abuse-investigation, threat-assessment, medical, sexual-violence-investigation,
or law-enforcement narrative.

Where a restricted workflow must be recorded, Communication should preserve only
minimal necessary handoff/notification metadata.

### 29. Communication reuses the shared canonical lifecycle

Communication lifecycle is:

```text
proposed
active
invalidated
superseded
```

with Communication-specific reason vocabularies.

Invalidation means the Communication representation is defective, such as:

```text
wrong sender
wrong recipient
wrong method
wrong purpose
wrong time
wrong summary
wrong attachment
communication did not occur
invalid provenance
```

A later reply, follow-up, or successful attempt is not supersession merely
because it is later.

Material correction uses successor/history semantics.

### 30. Communication v1 exposes no Amendment paths

Communication v1 permits no application-level `amendment@1` paths.

Sender, recipient, method, purpose, privacy scope, summary, attachment, relation,
and material timing all affect the historical claim about what communication
occurred.

This still permits correction without rewriting history: a corrected
representation succeeds the prior representation.

The generic Amendment contract remains structurally reusable but
application-prohibited for Communication v1.

### 31. Statement of Disagreement remains additive

Existing:

```text
statement_of_disagreement@1
```

remains structurally reusable for exact Response and Communication targets.

A disagreement does not erase, reverse, supersede, or automatically invalidate
its target.

If the disagreement contains substantive Event source information, a separate
Account may also be appropriate.

### 32. Paper, OCR, draft generation, and imports never fabricate action

The following are not equivalent:

```text
printed letter != letter sent
email draft != Communication sent
printed referral != handoff completed
preallocated Response form != Response occurred
```

Response and Communication prohibit `paper_capture/preallocated` as canonical
action records.

An ingested paper capture may create only a proposed representation subject to
the later #20 human-review workflow.

Imported records begin proposed unless they are governed migrations of already
accepted Portia representations.

Historical uncertainty may be preserved through explicit `unknown` branches
where the contract permits them.

Import source prestige does not prove action, delivery, authority, correctness,
or legal sufficiency.

### 33. Automation may organize but not make consequential decisions

Software may:

```text
validate structure
validate chronology
resolve exact references
detect duplicate logical recipients
show eligible Contact Points
offer templates/checklists
build derived timelines
remind about incomplete follow-up
```

Software may not automatically:

```text
choose punishment
escalate consequence by incident count
recommend removal
infer family engagement
infer refusal from nonresponse
infer remorse
infer compliance
infer Response effectiveness
declare legal notice sufficient
convert Determination into consequence
send substantive external communication solely because a rule fired
```

No predictive or risk score is introduced.

### 34. Shared infrastructure is reused without Response/Communication forks

Issue #17 reuses existing generic:

```text
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

No Response- or Communication-specific copy is introduced unless implementation
demonstrates a genuine wire incompatibility.

Operational and derived records should retain opaque IDs, paths, contract
versions, revisions, status, hashes, and bounded diagnostics rather than copying
message summaries, contact values, family statements, consequence rationale, or
attachment contents.

Integrity Finding remains a data-integrity diagnostic, not a Response-quality,
discipline, or family-engagement finding.

### 35. Core and sibling-module ownership remain unchanged

Core remains authoritative for:

```text
workspace/class/roster identity
module-qualified work/record identity
PDS2 routing
retained-source provenance
safe shared path infrastructure
```

Portia owns Response and Communication semantics.

No Core change is authorized by ADR 0013.

Sibling module records may be referenced, but the source module remains
authoritative.

Portia does not convert ScoreForm, Quillan, Concord, Meridian, Vitrine, or other
sibling records automatically into behavior Responses, Communications,
consequences, academic Grade inputs, or portfolio material.

## Public Contract Plan

ADR 0013 authorizes implementation of:

```text
portia_response_id@1
portia_communication_id@1
response@1
communication@1
```

No additional public primitive is currently required.

In particular, ADR 0013 does not authorize:

```text
response_ref@1
communication_ref@1
response_target@1
communication_target@1
communication_party@1
communication_attachment_ref@1
```

unless later implementation demonstrates a distinct reusable semantic unit that
cannot be represented by the accepted generic references/targets or schema-local
structures.

No published schema is modified in place.

## Consequences

### Positive

- Immediate action remains distinct from evidence and decision.
- Consequence implementation cannot retroactively define what occurred.
- Response stays separate from longitudinal Support.
- Communication can be recorded without becoming a general messaging archive.
- Repeated communication attempts preserve actual history.
- Family/student participation remains descriptive rather than scored.
- Exact Contact Point history can be preserved without claiming consent or
  delivery.
- Communication can become Support-Process-local later without an immediate
  wire-version bump.
- Account remains the source-evidence family for substantive communicated
  assertions.
- Published Account/Observation artifact semantics remain unchanged.
- Shared lifecycle, migration, operation, and derived contracts remain reusable.
- Privacy exposure is reduced by summary-oriented Communication and
  privacy-minimized operational records.

### Costs

- A workflow may need both Response and Communication records for one real-world
  sequence.
- Current-view logic must derive threads rather than mutate one conversation
  container.
- Exact Contact Point ownership and duplicate-recipient checks require
  application validation.
- Institutional consequence linkage requires exact Determination resolution.
- Communication attachment handling requires schema-local variants.
- Corrections create successor history rather than convenient in-place edits.
- Support-Process-owned Communication cannot become active current-use data
  until #18 publishes a resolvable Support Process contract.

## Alternatives Considered

### Store Response directly on Event or Determination

Rejected because action history, provider attribution, multiple Responses, and
correction lifecycle would be lost or would turn consequence into part of the
decision itself.

### Treat every family contact as Response only

Rejected because Communication has independent sender, recipient, method,
purpose, attempt state, endpoint, content-summary, attachment, privacy, and
history semantics.

ADR 0013 refines ADR 0002 accordingly.

### Make Communication Event-only

Rejected because communications will also occur during Support Process work.
Existing Portia work identity already supports future Support Process ownership,
so work-local Communication avoids an unnecessary future version bump.

### Make Communication workspace-global or student-global

Rejected because it creates a correspondence dossier divorced from Portia work
context and increases privacy/cross-work ambiguity.

### Use Work Relationship for all related records

Rejected because `work_relationship@2` is intentionally a work-to-work
`draws_context_from` contract, not a generic record relation.

### Reuse `source_artifact_ref@1` for Communication attachments

Rejected because its published semantic scope is material associated with
Account or Observation. Reuse would broaden an accepted public contract.

### Publish a shared Communication attachment primitive immediately

Rejected because Communication is currently the only demonstrated consumer.
Schema-local structure avoids premature abstraction.

### Store full mutable message bodies

Rejected because Portia is not a messaging archive, full payloads increase
privacy exposure, and source assertions should remain Accounts where relevant.

### Mark later successful contact as update to an earlier attempt

Rejected because the unsuccessful attempt actually happened and must remain
separately queryable.

### Permit v1 Amendment for metadata

Rejected because no candidate field is clearly nonmaterial to the historical
claim about action or communication.

### Infer family engagement or Response effectiveness

Rejected because those are evaluative judgments, not observable communication
or action metadata.

## Deferred Work

- Support Process / Support / Intervention / implementation / fidelity: #18.
- Follow-Up / Outcome / Reentry / Repair: #19.
- Complete paper/PDS2/import workflows: #20.
- Privacy projection/redaction/export/retention: #21.
- End-to-end combined synthetic record graphs: #22.
- Final foundations architecture audit: #23.
- Institutional staff authentication/RBAC/guardian-rights authority: future
  platform work.
- District messaging/email/SMS transport and trusted delivery receipts: future
  platform work.
- Legal-notice adjudication: future platform work.
- Specialized clinical/safety/investigative case-management systems: outside
  ordinary Portia Response/Communication.

## Invariants

1. Response is action, not evidence.
2. Consequence is not proof.
3. Response is not Determination.
4. Response is not Support.
5. Response is not Outcome.
6. Event-level Response does not imply identical Participant action.
7. Provider is separate from recorder.
8. Provider identity is separate from authority.
9. Institutional consequence requires exact decision context.
10. Response execution state is not effectiveness.
11. Restricted crisis workflows are not ordinary Response payloads.
12. Communication is one act or attempt, not a mutable thread.
13. Communication is not Account evidence.
14. Communication is not proof of delivery, reading, understanding, consent, or
    legal sufficiency.
15. Sender is separate from recorder.
16. Recipient identity is not guardianship or communication authorization.
17. Contact Point preference is not consent.
18. Contact Point local confirmation is not delivery or institutional
    verification.
19. Exact historical Contact Points never silently follow successors.
20. Repeated attempts remain separate canonical Communications.
21. Later success does not rewrite earlier failure.
22. Communication summary is not an authoritative exact message archive.
23. Substantive communicated assertions remain separately preservable as
    Accounts.
24. Communication attachments do not broaden `source_artifact_ref@1`.
25. External attachment locators remain inert.
26. Binary payloads are not embedded in Communication JSON.
27. Record relations use exact historical references.
28. Work Relationship remains work-to-work context only.
29. Recipient listing is not participation.
30. No engagement, remorse, compliance, risk, or effectiveness score is
    introduced.
31. Privacy scope is handling metadata, not authorization.
32. Response and Communication v1 expose no Amendment paths.
33. Disagreement is additive and nonadjudicating.
34. Paper/draft/OCR/import never create automatic accepted action.
35. Automation may organize but may not select punishment or infer consequence.
36. Shared infrastructure is reused without unnecessary family-specific forks.
37. Operational/derived records do not copy sensitive substantive payload merely
    for coordination.
38. Published schemas remain immutable.
