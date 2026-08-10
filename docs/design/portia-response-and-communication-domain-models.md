# Portia Response and Communication Domain Models

**Status:** Accepted architecture — ADR 0013
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#17 — Define Response and Communication domain models`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-09
**Branch:** `17-response-communication-domain-models`
**Decision:** ADR 0013 accepted

## 1. Purpose

This document defines the pre-ADR architecture for Portia's action and
communication layer.

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

The arrows identify possible relationships. They do not require every Event to
progress through every record family.

The central semantic boundary for Issue #17 is:

```text
Response
= one bounded action taken, attempted, or completed in direct Event context

Communication
= one bounded communication act or attempt associated with one Portia work context
```

Neither family is evidence merely because it exists.

```text
Response != Event
Response != Determination
Response != Support
Response != Outcome

Communication != Account
Communication != Response
Communication != Determination
Communication != mutable thread
```

A Response may be consequential without proving that its underlying decision was
correct. A Communication may preserve that a contact act occurred without
proving that its contents were true, delivered, read, understood, legally
sufficient, or evidence of participation.

This issue defines architecture and public contracts. It does not implement an
institutional messaging transport, district discipline system, legal-notice
service, threat-assessment platform, or clinical case-management system.

---

## 2. Governing Repository Baseline

Initial Issue #17 comparison:

```text
pds-portia/main:
34d8100a1775effc43737409f86ad0486c01fb34

17-response-communication-domain-models:
34d8100a1775effc43737409f86ad0486c01fb34

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

Issue #16 is therefore fully merged before Issue #17 begins.

No initial Portia or Core drift requires a contract change.

---

## 3. Governing Contracts

Issue #17 is subordinate to the accepted Portia foundation through ADR 0012.

Important existing contracts include:

```text
event@2
event_participant@3
event_participant_role@3
work_relationship@2

actor@1
actor_contact_point@1
actor_student_relationship@1

account@1
observation@1
review@1
classification@1
hypothesis@1
determination@1

portia_target_ref@1
support_process_target_ref@1
portia_local_work_target@1

represented_human_attribution@1
attribution_agent@1

exact_portia_work_ref@1
exact_portia_work_record_ref@1
exact_local_record_ref@1
module_work_record_ref@1

exact_actor_ref@1
exact_actor_contact_point_ref@1

source_artifact_ref@1
judgment_evidence_ref@1

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

The design must not broaden an existing contract merely because its shape is
convenient.

---

## 4. Governing Principles

1. Action is not evidence.
2. Consequence is not proof.
3. Communication is not Account evidence.
4. Recipient listing is not participation.
5. Contact Point preference is not consent.
6. Contact Point verification is not delivery proof.
7. Provider/sender identity is separate from recorder identity.
8. Human identity is separate from institutional authority.
9. Immediate Response is distinct from planned or longitudinal Support.
10. Repeated actions remain separately addressable where they are separately
    meaningful.
11. Repeated communication attempts remain separate canonical records.
12. A later successful contact does not rewrite an earlier unsuccessful attempt.
13. Communication history is not a mutable thread.
14. Material correction preserves historical representation.
15. Exact historical references never silently follow successors.
16. Restricted crisis, clinical, legal, and investigative workflows remain
    outside ordinary Response/Communication payloads.
17. Software may organize and validate but must not select punishment, infer
    engagement, or infer effectiveness.
18. Operational and derived records must remain privacy-minimized.

---

# 5. Accepted Direction: Response Is Event-Local

One Response represents:

> One bounded action that a represented provider took, attempted, initiated, or
> completed in direct relation to one Event or its Event-local review/decision
> context.

Response v1 should be Event-local.

Proposed identifier:

```text
rsp_<opaque-id>
```

Proposed identifier contract:

```text
portia_response_id@1
```

Proposed canonical path:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/response/<response_id>.json
```

Response identity carries no student, provider, consequence, severity, action
type, policy, or lifecycle meaning.

Response is Event-local because the semantic unit is an immediate or bounded
action taken in relation to an Event.

Planned, recurring, scheduled, longitudinal, goal-directed, or fidelity-tracked
activity belongs to Support/Intervention under Issue #18.

---

## 6. Response Target Is the Action Recipient/Scope

Response v1 should reuse:

```text
portia_target_ref@1
```

Accepted target scopes remain:

```text
event
event_participant
event_participants
```

The target identifies who or what the action applied to.

No separate `recipient` field is needed when the target already carries that
semantic role.

Examples:

```text
teacher paused the entire activity
→ Event target

teacher redirected one participant
→ one Event Participant target

teacher moved two selected participants to another work area
→ explicit Participant-set target
```

Event-level Response does not imply that every Participant received the same
consequence, bore the same responsibility, or was the object of the same
person-specific action.

A roster student must not become the direct durable owner of Response history
outside an Event.

---

## 7. Response Provider Reuses Represented-Human Attribution

Response provider should reuse:

```text
represented_human_attribution@1
```

The provider is the represented human who performed or attempted the action.

Provider remains separate from:

```text
created_by
updated_by
```

The same local operator may be both provider and recorder, but the schema must
not equate those roles.

The shared attribution union remains broad enough to preserve:

```text
local_operator
actor
descriptive school staff
roster student
other descriptive person
unidentified historical person
```

Structural representability does not establish current workflow eligibility.

Application validation must govern action-family eligibility.

Examples:

- teacher-local classroom Response ordinarily requires a `local_operator` or
  eligible school-staff representation;
- an institutional action may preserve another represented provider;
- roster-student attribution does not make that student an institutional
  discipline provider;
- an Actor title such as `administrator` does not itself establish authority;
- unidentified historical provider attribution may preserve imports but cannot
  satisfy a workflow requiring a currently resolved responsible provider.

---

## 8. Response Action Representation

Response should use a small stable semantic family plus bounded descriptive
detail rather than a universal discipline taxonomy.

Proposed initial action families:

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

Each Response should carry a concise human-readable action description.

`other` requires bounded detail.

The action family describes what the responder did.

It does not describe:

```text
student character
severity
culpability
intent
risk
policy finding
effectiveness
```

No numeric severity or response score is introduced.

---

## 9. Classroom-Managed Response

A classroom-managed Response may exist without a Determination.

Examples include:

```text
redirection
direction repeated
task clarified
instruction retaught
choice offered
temporary seating change
activity paused
brief change of setting
assistance requested
```

These records do not imply misconduct or institutional discipline.

Ordinary classroom management must not be forced through a formal adjudication
workflow merely to make Response auditable.

---

## 10. Support-Access Response

An immediate use of an already available support can be a Response.

Example:

```text
student offered the already-established break option during this Event
```

That does not make the standing break arrangement part of Response.

Future Issue #18 may permit an exact link from the Response to the Support or
Implementation record that supplied the option.

The Response should record the bounded Event-local action only.

---

## 11. Safety-Oriented Response

Ordinary Response may represent bounded safety/protective actions such as:

```text
activity paused
students moved away from immediate hazard
assistance requested
de-escalation location offered
restricted safety workflow notified
```

Issue #17 must not make the following ordinary Response categories:

```text
restraint
seclusion
threat assessment
self-harm/suicide process
suspected abuse/neglect investigation
sexual violence investigation
law-enforcement investigation
medical emergency treatment
clinical intervention
```

Those processes require specialized jurisdiction-dependent handling.

Portia may preserve a minimal handoff/notification Response without copying
restricted details.

---

## 12. Consequence Response

A consequence is an action that occurred.

It is not proof that the consequence was warranted.

Response should distinguish:

```text
teacher_local
recorded_institutional
```

consequence context.

A teacher-local consequence may exist without a Determination.

A `recorded_institutional` consequence should require an exact same-Event
Determination reference.

This reference means:

> this Response records implementation of or action following that recorded
> decision.

It does not mean:

```text
the Determination was correct
the policy was correctly applied
the action was lawful
the action was proportionate
the action was effective
```

Response must not duplicate the Determination's authority or policy/process
basis.

---

## 13. Review and Determination Context

Response may optionally retain exact same-Event references to:

```text
Review
Determination
```

Proposed fields:

```text
review_ref
determination_ref
```

These are context links, not evidence.

`recorded_institutional` consequence requires `determination_ref`.

Other Response families may have a Determination reference when useful, but it
must not be fabricated merely because a Response exists.

A Response does not own reverse lists of Communications. Communication should
own its forward relation to Response, with reverse views derived.

---

## 14. Referral/Handoff Response

Referral/handoff is a Response family because it records an action taken.

Its execution state must remain distinct from downstream service delivery.

Examples:

```text
counselor handoff requested
administrative assistance requested
restricted workflow notified
student escorted to designated support location
```

A completed handoff does not mean a Support or Intervention was later delivered.

Issue #18 owns ongoing Support.

---

## 15. Response Execution State

Canonical lifecycle and action execution state are different dimensions.

Proposed execution vocabulary:

```text
attempted
in_progress
completed
partially_completed
discontinued
unable_to_complete
unknown
```

Definitions:

- `attempted`: provider attempted the action but it did not proceed far enough
  to be represented as partial completion;
- `in_progress`: bounded action was underway when recorded;
- `completed`: the described action was carried out;
- `partially_completed`: only part of the described bounded action occurred;
- `discontinued`: action began and was intentionally stopped;
- `unable_to_complete`: provider could not complete the intended bounded action;
- `unknown`: historical/imported execution state cannot be reconstructed.

Execution state must never include:

```text
successful
effective
appropriate
resolved
```

Those are Outcome/evaluation concepts.

---

## 16. Response Timing

Response should preserve:

```text
started_at
ended_at
```

`started_at` is required.

`ended_at` is optional where the action has a meaningful end.

Application validation enforces:

```text
ended_at >= started_at
```

A Response must not reuse evidence-specific time primitives merely for shape
convenience.

The shared explicit-offset timestamp primitive remains sufficient.

---

## 17. Response Lifecycle

Response should reuse the shared lifecycle:

```text
proposed
active
invalidated
superseded
```

Proposed lifecycle reasons should include concepts such as:

```text
action_recorded
recording_error
wrong_provider
wrong_target
wrong_event
wrong_action
wrong_timing
wrong_decision_context
invalid_provenance
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Supersession reasons should include:

```text
provider_corrected
target_corrected
action_corrected
timing_corrected
decision_context_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Invalidation means the representation is defective.

It does not mean:

```text
ineffective
later disliked
later reversed policy
student disagreed
Support changed
```

---

## 18. Response Amendment Policy

Pre-ADR direction:

> Response v1 exposes no `amendment@1` paths.

Provider, target, action, execution state, material timing, and decision context
are all historically meaningful.

Allowing an in-place amendment surface would create difficult distinctions
between action history and metadata correction before production workflows
demonstrate a genuinely safe nonmaterial field.

Material correction therefore uses successor/history semantics.

This is intentionally conservative and may be revisited in a future contract
version if production use demonstrates a safe, useful nonmaterial surface.

---

# 19. Accepted Direction: Communication Is Portia-Work-Local

One Communication represents:

> One bounded communication act or attempt associated with one canonical Portia
> work context.

Proposed identifier:

```text
comm_<opaque-id>
```

Proposed identifier contract:

```text
portia_communication_id@1
```

Communication should be Portia-work-local rather than Event-only.

Existing shared work identity already recognizes:

```text
event
support_process
```

Therefore Communication v1 can avoid an immediate future wire-version bump when
Issue #18 introduces ongoing Support Process communications.

Proposed canonical path:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/communication/<communication_id>.json
```

Communication should carry explicit:

```text
work_kind
```

with:

```text
event
support_process
```

and a `work_id` whose prefix/contract matches that kind.

Current-use rule before #18:

> Active current-use Communication requires a resolvable owning work. Until
> `support_process@1` is published, current active Communication can therefore
> be Event-owned; support-process structural support remains future-compatible
> rather than fabricated.

No workspace-global correspondence dossier is introduced.

---

## 20. Communication Sender

Human Communication sender should reuse:

```text
represented_human_attribution@1
```

Sender is distinct from recorder.

Issue #17 v1 should not introduce system-originated canonical Communication.

A system may generate a draft or template, but no canonical completed
Communication exists until an explicit represented human communication act is
recorded.

If future transport infrastructure needs machine-originated communication, that
requires a later explicit contract decision rather than placing
`system_process` inside human attribution.

---

## 21. Communication Recipients

Communication should require one or more recipient entries.

Each recipient should contain:

```text
person
optional endpoint_ref
```

`person` reuses:

```text
represented_human_attribution@1
```

`endpoint_ref`, when present, should currently support exact Actor Contact Point
identity.

Recipient identity does not establish:

```text
guardianship
educational decision rights
consent
communication authorization
entitlement to all Portia information
```

Recipient order has no semantic meaning in v1.

Application validation must reject duplicate logical recipients even when
different display snapshots make two JSON objects structurally distinct.

---

## 22. Actor Contact Point Use

When an Actor recipient was contacted through a known Actor Contact Point,
Communication may retain:

```text
exact_actor_contact_point_ref@1
```

This preserves the exact historical endpoint representation.

Application validation requires:

```text
recipient kind = actor
endpoint Actor = recipient Actor
endpoint resolves exactly
```

The Communication must not silently follow a later Contact Point successor.

Existing semantics remain unchanged:

```text
preferred != consent
locally_confirmed != delivery
locally_confirmed != exclusive endpoint control
Actor identity != communication authorization
```

Raw email/phone values should not be copied into Communication when an exact
Contact Point reference is sufficient.

One-off descriptive people and roster students do not require fabricated Actor
records merely to create Communication.

---

## 23. Communication Method

Proposed closed method vocabulary:

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

`unknown` exists for historical/imported records.

Method describes the communication channel only.

It does not establish:

```text
delivery
read receipt
identity verification
understanding
legal service
```

---

## 24. Communication Purpose

Proposed closed purpose vocabulary:

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

Purpose does not establish completion of the process named by the purpose.

Examples:

```text
determination_notice
!= legal sufficiency of notice

support_coordination
!= Support delivered

referral_or_handoff
!= downstream service completed
```

---

## 25. Communication Act State

Communication act state is separate from lifecycle.

Proposed state vocabulary:

```text
attempted
completed
recipient_unavailable
recipient_declined
interrupted
unknown
```

`completed` means the bounded communication act was completed from the recorder's
documented perspective.

It does not mean:

```text
email delivered
email opened
message read
message understood
notice legally sufficient
recipient agreed
```

Neutral state language is required.

Do not store:

```text
family_refused
ignored
uncooperative
successful
effective
```

as communication states.

---

## 26. Repeated Attempts and Replies

Every separately meaningful attempt is a separate Communication.

Example:

```text
3:10 PM phone call — recipient unavailable
4:25 PM phone call — completed
```

The second record must not mutate the first.

Replies and follow-up messages are also separate canonical Communications.

A thread or conversation view is derived.

Communication v1 should not create a mutable canonical thread container.

A relation such as `responds_to` may link an exact prior Communication.

---

## 27. Communication Timing

Communication should preserve:

```text
started_at
ended_at
```

`started_at` is required.

`ended_at` is optional for methods where an interval is meaningful.

Application validation enforces chronology.

For instantaneous/send-style methods, omission of `ended_at` is valid.

No state should imply a read/delivery timestamp that Portia cannot verify.

---

## 28. Communication Content Representation

Pre-ADR direction:

> Communication v1 stores a bounded recorder-authored `summary`, not an
> unrestricted canonical message-body archive.

The summary is optional for unsuccessful attempts and may be required by
application workflow for selected completed purposes.

The summary describes what the communication concerned.

It is not an exact quotation unless the record explicitly says so.

Communication v1 should not include a generic mutable `body` field.

Reasons:

1. Portia is not a messaging archive.
2. Full message bodies increase privacy exposure.
3. Incoming substantive claims belong in Account when they matter as evidence.
4. Exact outbound documents can be preserved as linked artifacts when needed.
5. A bounded summary is sufficient for ordinary teacher-local workflow.

A future transport/message-preservation feature may require a later schema
version or dedicated artifact contract.

---

## 29. Communication vs. Account

This is a hard boundary.

Example:

```text
Communication:
family phone call occurred at 16:25

Account:
family member reported that the student believed an alarm was sounding
```

When substantive source content matters to review:

```text
Communication != evidence source record
Account = attributed source statement
```

The Account may reference relevant provenance according to existing/future
contracts.

Do not copy a long narrative into both Communication and Account.

A Communication relation to an Account means the Account arose from or was
communicated through that act. It does not make Communication itself judgment
evidence.

---

## 30. Communication Attachments

`source_artifact_ref@1` should not be reused directly for Communication because
its published meaning is specifically source material associated with
Account/Observation.

Issue #17 should not broaden that accepted semantic contract.

Pre-ADR direction:

> Keep Communication attachment representation local to `communication@1`
> rather than publishing a new reusable attachment primitive prematurely.

Proposed inline attachment branches:

```text
workspace_file
portia_record
module_record
external_record
```

`workspace_file` should preserve:

```text
workspace-relative path
content fingerprint
```

`portia_record` should use:

```text
exact_portia_work_record_ref@1
```

`module_record` should use:

```text
module_work_record_ref@1
```

`external_record` should preserve bounded inert system/reference metadata.

External references are never dereferenced automatically.

Binary payloads are never embedded in Communication JSON.

Paper-capture attachment semantics remain deferred to #20 rather than copying
`source_artifact_ref@1`'s paper branch into a new family now.

If later record families genuinely need the same attachment shape, a future
shared primitive may be extracted deliberately.

---

## 31. Communication Related-Record Relations

Communication should own typed forward relations to exact Portia records.

Proposed relation structure:

```text
relation
record_ref
```

where `record_ref` uses:

```text
exact_portia_work_record_ref@1
```

Proposed initial relation vocabulary:

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

`other` requires detail.

Application validation must constrain semantic combinations.

Examples:

```text
responds_to
→ prior Communication

conveys_determination
→ Determination

relates_to_response
→ Response

account_from_communication
→ Account
```

No semantically empty untyped `related_records` array is introduced.

Exact historical refs never follow successors.

Cross-work communication context remains possible because exact work-record
references carry exact work identity.

Work-to-work `draws_context_from` continues to use `work_relationship@2`; that
contract must not be overloaded with record-to-record communication semantics.

---

## 32. Response and Communication Are Independently Canonical

One real-world workflow may produce both records.

Examples:

```text
teacher phones family
→ Communication only

family contact explicitly treated as an immediate Event action
→ Response + Communication relation

teacher requests counselor handoff by phone
→ Response = handoff requested
→ Communication = phone act

administrator makes decision
→ Determination

teacher conveys decision to family
→ Communication

action is implemented
→ Response
```

Do not duplicate sender, recipient, method, content summary, provider, or action
detail across both records merely for display convenience.

Forward relations plus derived reverse views are preferred.

---

## 33. Family and Student Participation

Communication must support descriptive participation without engagement scoring.

Facts Portia may preserve include:

```text
communication completed with family member
recipient unavailable
recipient declined proposed meeting
student participated in conversation
```

Facts Portia must not infer include:

```text
family engaged
family uncooperative
parent responsiveness score
student remorse
student compliance
student attitude
```

Recipient listing does not establish participation.

A voicemail or email send does not establish that the recipient participated.

---

## 34. Communication Privacy Scope

Communication should require a minimal privacy scope.

Proposed initial values:

```text
ordinary
participant_limited
restricted
unknown
```

Definitions:

- `ordinary`: ordinary authorized Portia workflow handling;
- `participant_limited`: communication includes information that should be
  limited to relevant participant context;
- `restricted`: content/relationship requires narrower handling;
- `unknown`: historical/imported privacy classification unavailable.

This field is a handling classification, not an authorization engine.

It does not implement FERPA, legal privilege, access control, redaction, or
disclosure sufficiency.

Issue #21 owns complete projection/redaction/export policy.

---

## 35. Restricted Communication Boundary

Ordinary Communication must not become a container for:

```text
clinical notes
counseling treatment notes
trauma narratives
abuse-investigation detail
threat-assessment detail
sexual-violence investigation detail
protected medical detail
law-enforcement investigation narrative
```

Where Portia must preserve that notification or handoff occurred, the
Communication should retain only minimal metadata necessary to understand the
act and its restricted-workflow relationship.

---

## 36. Communication Lifecycle

Communication should reuse:

```text
proposed
active
invalidated
superseded
```

Potential lifecycle reasons:

```text
communication_recorded
recording_error
wrong_sender
wrong_recipient
wrong_method
wrong_purpose
wrong_timing
wrong_content_summary
wrong_attachment
communication_did_not_occur
invalid_provenance
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Potential supersession reasons:

```text
sender_corrected
recipient_corrected
method_corrected
purpose_corrected
timing_corrected
content_summary_corrected
attachment_corrected
relation_corrected
privacy_scope_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

A later reply or successful contact is not supersession merely because it is
later.

---

## 37. Communication Amendment Policy

Pre-ADR direction:

> Communication v1 exposes no `amendment@1` paths.

Even apparently administrative metadata can change material historical meaning.

Examples:

```text
method
recipient
sender
purpose
privacy_scope
summary
attachment
timing
```

all affect what communication record the system claims existed.

Using successor/history correction is safer than attempting to classify
nonmaterial communication metadata before production use demonstrates a stable
safe field.

This still satisfies the requirement that metadata can be corrected **without
rewriting message history**: correction creates a replacement representation
and preserves the prior record.

---

## 38. Statement of Disagreement

Existing:

```text
statement_of_disagreement@1
```

should remain structurally reusable for exact Response and Communication
records through generic exact targeting.

A disagreement:

```text
does not erase target
does not reverse action
does not change communication history
does not automatically invalidate target
```

If the disagreement contains substantive Event information, a separate Account
may also be appropriate.

---

## 39. Paper and Import Boundary

Creating paper or a draft does not create an action.

```text
printed letter != Communication sent
email draft != Communication sent
printed referral != handoff completed
preallocated Response form != Response occurred
```

Existing creation provenance supports:

```text
digital_entry
paper_capture
import
```

Issue #17 should prohibit `paper_capture/preallocated` for Response and
Communication canonical records.

An ingested paper capture may create only a proposed representation subject to
human review under the future #20 workflow.

Imported Response/Communication records begin proposed unless they are governed
migrations of already accepted Portia representations.

Imports may preserve honest `unknown` values where the contract explicitly
allows them.

No import source system establishes truth, delivery, authority, or legal
sufficiency.

---

## 40. Automation Boundary

Software may:

```text
validate schema
validate chronology
detect duplicate logical recipients
resolve exact references
show eligible Contact Points
display templates
show local checklists
build derived timelines
remind about incomplete follow-up
```

Software may not automatically:

```text
select punishment
escalate consequence based on count
recommend removal
infer family engagement
infer refusal from nonresponse
infer remorse
infer compliance
infer Response effectiveness
declare legal notice satisfied
convert Determination to consequence automatically
send substantive external communication solely from an automatic rule
```

A system-generated draft is not a completed Communication.

---

## 41. Cross-Module Boundary

Core remains authoritative for:

```text
workspace/class/roster identity
ModuleWorkRef / ModuleRecordRef
PDS2 routing
retained-source provenance
safe workspace paths
```

Portia owns Response/Communication semantics.

No Core change is currently required.

Sibling module records may be referenced when useful, but the originating
module remains authoritative.

Examples:

- Quillan may own a substantial written reflection or family-submitted writing
  artifact;
- ScoreForm may own a structured form/result;
- Concord may own a collaborative Artifact;
- Portia owns why the record is related to a Response/Communication.

Sibling academic data must not automatically generate behavior Response.

Meridian must not interpret Response, consequence, family contact, or
Communication frequency as academic Grade inputs.

Portfolio/Vitrine workflows must not receive Portia Communications or
consequences automatically.

---

## 42. Public Contract Plan

Expected additive public contracts:

```text
portia_response_id@1
portia_communication_id@1
response@1
communication@1
```

No additional public primitive is currently justified.

Specifically, the pre-ADR design does **not** propose:

```text
response_ref@1
communication_ref@1
response_target@1
communication_target@1
communication_party@1
communication_attachment_ref@1
```

Generic exact record refs and existing targets remain sufficient.

Communication recipient and attachment shapes should remain schema-local until
another record family proves a reusable shared semantic unit.

---

## 43. Proposed Response Root Shape

The exact JSON contract will be finalized after ADR acceptance, but the intended
semantic fields are:

```text
schema_version
record_type
module_id
class_id
work_id
response_id
status

target
provider
action
execution_state

started_at
ended_at?

review_ref?
determination_ref?

supersedes?

creation_source
created_at
created_by
updated_at
updated_by
```

No fields for:

```text
credibility
blame
severity score
risk score
effectiveness
success rating
Outcome
support plan
automatic punishment recommendation
```

---

## 44. Proposed Communication Root Shape

Intended semantic fields:

```text
schema_version
record_type
module_id
class_id
work_kind
work_id
communication_id
status

sender
recipients

method
purpose
act_state
privacy_scope

started_at
ended_at?

summary?
attachments?
relations?

supersedes?

creation_source
created_at
created_by
updated_at
updated_by
```

No fields for:

```text
family engagement score
read receipt unless actually supported by a trusted later transport contract
legal notice satisfied
remorse
compliance
sentiment
risk
effectiveness
mutable thread body
```

---

## 45. Application Validation Responsibilities

JSON Schema will validate local wire shape.

Application validation must handle:

### Response

```text
canonical storage
Event ownership
target resolution
provider resolution
provider eligibility
target/action compatibility
Determination linkage rules
recorded-institutional consequence requirements
Review/Determination same-Event constraints
execution chronology
paper/import activation gates
lifecycle legality
supersession topology
duplicate consolidation
ownership correction
no silent successor following
```

### Communication

```text
canonical work storage
work-kind/work-id agreement
owning work resolution
sender resolution
recipient resolution
recipient logical uniqueness
Actor Contact Point ownership
exact historical Contact Point resolution
relation resolution
relation/record-kind compatibility
reply same/logically compatible work rules
attachment path/fingerprint resolution
external locator inertness
act-state chronology
paper/import activation gates
privacy handling
lifecycle legality
supersession topology
duplicate consolidation
ownership correction
no silent successor following
```

Application-invalid coverage must be named and complete.

---

## 46. Shared Infrastructure Compatibility

Issue #17 should prove reuse of:

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

Response/Communication-specific forks should not be introduced unless a real
wire incompatibility appears.

`amendment@1` remains structurally generic even though v1 application policy
prohibits Response/Communication amendment paths.

Operational/derived records should retain:

```text
opaque IDs
paths
contract versions
revisions
status
hashes
bounded diagnostics
```

rather than copying:

```text
message summaries
contact values
family statements
consequence rationale
attachment contents
```

Integrity Finding remains a data-integrity diagnostic, not an action-quality or
family-engagement finding.

---

## 47. ADR 0013 Decision Checklist

ADR 0013 resolves the following decisions:

1. Confirm Response Event-local ownership.
2. Confirm Communication generic Portia-work-local ownership.
3. Confirm current active support-process Communication is gated until
   `support_process@1` exists.
4. Confirm `rsp_` and `comm_` identifiers.
5. Confirm Response action-family vocabulary.
6. Confirm Response execution-state vocabulary.
7. Confirm teacher-local versus recorded-institutional consequence context.
8. Confirm exact Determination requirement for recorded-institutional
   consequence.
9. Confirm represented-human reuse for provider/sender/recipients.
10. Confirm no system-originated Communication v1.
11. Confirm Communication method/purpose/state vocabularies.
12. Confirm exact Actor Contact Point semantics.
13. Confirm summary-only Communication content model.
14. Confirm schema-local attachment union rather than `source_artifact_ref@1`
    reuse.
15. Confirm typed exact related-record relations.
16. Confirm required Communication privacy scope.
17. Confirm no Amendment paths for Response or Communication v1.
18. Confirm paper preallocation prohibition and ingested/import proposal gates.
19. Confirm specialized crisis workflow exclusion.
20. Confirm shared-infrastructure reuse without forks.

---

## 48. Deferred Work

Issue #17 does not define:

```text
#18 Support Process / Support / Intervention / implementation / fidelity
#19 Follow-Up / Outcome / Reentry / Repair
#20 complete paper / PDS2 / import workflows
#21 privacy projection / redaction / export / retention
#22 end-to-end combined synthetic graphs
#23 final architecture audit
```

Also outside this issue:

```text
institutional staff authentication
RBAC
authoritative guardian rights
district messaging transport
email/SMS delivery APIs
legal-notice adjudication
clinical or threat-assessment case management
```

---

## 49. Planned Deliverables

Issue #17 should ultimately produce:

```text
docs/design/portia-response-and-communication-domain-models.md
docs/decisions/0013-define-response-and-communication-domain-models.md

schemas/v1/identifiers/portia-response-id.schema.json
schemas/v1/identifiers/portia-communication-id.schema.json
schemas/v1/responses/response.schema.json
schemas/v1/communications/communication.schema.json

docs/examples/portia-response-and-communication-examples.md

docs/validation/issue-17-initial-repository-checkpoint.md
docs/validation/issue-17-pre-adr-checkpoint.md
docs/validation/issue-17-final-repository-checkpoint.md
docs/validation/issue-17-application-invalid-matrix.json
docs/validation/issue-17-acceptance-matrix.json
docs/validation/issue-17-response-communication-validation.md
```

plus synthetic fixtures, focused schema/application tests, shared-infrastructure
compatibility tests, README/schema-guide reconciliation, and related active
documentation reconciliation.

---

## 50. ADR 0013 Acceptance

ADR 0013 accepts the decisions above. The required pre-ADR repository drift
check found no contradiction requiring a change.

The most consequential choices are:

```text
Response:
Event-local
target = portia_target_ref
provider = represented_human_attribution
no v1 Amendment paths

Communication:
Portia-work-local
human sender/recipient attribution
exact Actor Contact Point when applicable
summary-only content
schema-local attachments
typed exact record relations
required privacy scope
no v1 Amendment paths
```

These choices preserve the existing Portia epistemic and authority boundaries
while leaving #18–#21 room to extend the record graph without immediately
versioning the new contracts.
