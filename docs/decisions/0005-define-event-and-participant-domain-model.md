# ADR 0005: Define the Initial Event and Event Participant Domain Model

* **Status:** Accepted
* **Date:** 2026-07-21
* **Decision owners:** Portia maintainers
* **Related issue:** [#6 — Define the initial Portia Event and Event Participant domain model](https://github.com/Paper-Data-Suite/pds-portia/issues/6)
* **Related design:** [`docs/design/portia-event-and-participant-domain-model.md`](../design/portia-event-and-participant-domain-model.md)
* **Related schemas:**
  * [`schemas/event.schema.json`](../../schemas/event.schema.json)
  * [`schemas/event-participant.schema.json`](../../schemas/event-participant.schema.json)
* **Related examples:** [`docs/examples/portia-event-and-participant-examples.md`](../examples/portia-event-and-participant-examples.md)
* **Related decisions:**
  * [`0001-establish-portia-record-distinctions.md`](0001-establish-portia-record-distinctions.md)
  * [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)
  * [`0003-adopt-teacher-local-initial-deployment.md`](0003-adopt-teacher-local-initial-deployment.md)
  * [`0004-define-portia-identity-ownership-and-storage.md`](0004-define-portia-identity-ownership-and-storage.md)

## Context

ADR 0001 requires Portia to distinguish observations, attributed Accounts, interpretations, Classifications, Hypotheses, Determinations, Responses, Supports, Follow-Ups, and Outcomes rather than collapsing them into one behavior narrative.

ADR 0002 establishes Portia as Paper Data Suite’s behavior-support and response module. Portia may reference instructional and assessment context, but it does not evaluate academic work or calculate grades.

ADR 0003 establishes the initial deployment as teacher-local, classroom-focused, and based on one selected Paper Data Suite workspace.

ADR 0004 establishes:

* one owning Core class for every Event;
* one canonical class-scoped work root;
* a Portia `work_id` that is also the Event’s durable identifier;
* roster-qualified student identity using `class_id + student_id`;
* explicit cross-class student participation within the same teacher workspace;
* independent Event Participant identifiers;
* a limited workspace-scoped Actor Directory for recurring non-roster people;
* descriptive representation for incidental or unidentified people;
* one canonical direction for relationships;
* and derived rather than authoritative histories, indexes, reverse links, and projections.

Those decisions define where Events and Event Participants live and how their identities are scoped, but they do not define what one Event means, what belongs in `work.json`, how people are attached to an Event, how uncertainty is represented, or how Event and participant records move through their lifecycles.

Portia also requires a paper-compatible capture model. A teacher may need to record a brief Event while circulating through a classroom without interrupting instruction to complete a detailed digital form. The domain model must therefore support:

* preallocated paper capture;
* returned-page routing through PDS2;
* proposed interpretation of handwriting or marks;
* rapid teacher confirmation or correction;
* and the same canonical Event and Event Participant records used by digital entry.

The model must preserve sufficient provenance and correction history without turning routine teacher documentation into a time-consuming case-management workflow.

## Decision

Portia will use a **bounded Event root with separate Event Participant records, explicit uncertainty, lifecycle-preserving correction, and workflow-generated provenance**.

The principal decisions are:

1. One Event represents one coherent, time-bounded occurrence, interaction, observation period, or reported occurrence.
2. An Event is distinct from Accounts, Observations, Classifications, Determinations, Responses, Support Processes, Follow-Ups, Outcomes, and Communications.
3. The Event root contains only shared Event context.
4. Event Participants are separate canonical child records.
5. An active Event requires at least one active Event Participant, but no roster student is specifically required.
6. Participants may represent roster students, recurring Actors, descriptive people, or unknown people.
7. Participant identity is separate from participant role.
8. Event-level participant roles will be separate canonical records rather than embedded role fields.
9. Event occurrence uses an explicit precision variant rather than fabricated timestamps.
10. Event location and instructional context are optional, separate structured objects.
11. Draft and cancelled Events may remain incomplete; accepted Event states retain a valid occurrence and neutral summary.
12. Events use explicit lifecycle states with append-only transition history.
13. Event Participants use explicit lifecycle states with replacement-based identity correction.
14. Replacement records own canonical `supersedes` relationships to prior records.
15. Creation source and local attribution use structured discriminated objects.
16. Paper capture creates or proposes ordinary canonical records rather than a parallel paper-only domain.
17. Scanning or automated interpretation never activates an Event or participant without teacher review where review is required.
18. JSON Schema enforces local record shape; application validation enforces cross-record, lifecycle, path, chronology, and reference invariants.
19. Internal rigor must remain largely invisible during routine use.
20. Teacher workload must remain proportionate to the instructional or support value produced.

## Event Meaning and Boundary

One Event represents one coherent context that is bounded in time.

An Event may describe:

* one instantaneous occurrence;
* one interaction;
* a short connected sequence of actions;
* a defined observation period;
* or an occurrence reported after it happened.

A later report may document an earlier occurrence. Occurrence time, report time, Account time, record-entry time, response time, and follow-up time remain distinct concepts.

A short sequence may remain one Event when the actions are meaningfully connected and understood as one context. Portia must create separate Events when occurrences are unrelated merely because they involve:

* the same participant;
* the same class;
* the same category;
* the same support need;
* or a perceived recurring pattern.

An Event must not become:

* a permanent student narrative;
* a pattern record;
* a Support Process;
* a communication log;
* an unattributed Account;
* or a container for every later development concerning the same student.

A later bounded occurrence is a new Event. Later work concerning the original occurrence may be represented through an Account, Observation, Response, Follow-Up, Outcome, Communication, amendment, or explicit work relationship.

Positive, neutral, and concerning Events are all valid. The initial Event root does not require a problem-oriented category, severity score, finding, discipline recommendation, or behavior-to-grade field.

## Event Root Record

Each Event is stored at:

```text
classes/<class_id>/modules/portia/work/<event_id>/work.json
```

The root record declares:

```text
schema_version
record_type
work_kind
module_id
class_id
work_id
school_year
status
creation_source
created_at
created_by
updated_at
updated_by
```

For an Event:

```text
record_type = portia_work
work_kind = event
module_id = portia
work_id = event_id
```

The root may also contain:

```text
occurrence
summary
location
instructional_context
supersedes
```

The Event root contains shared Event context only.

It must not embed:

* Event Participants;
* participant-specific roles;
* participant-specific Accounts;
* participant-specific judgments;
* participant-specific Responses;
* participant-specific Outcomes;
* or a generalized narrative that collapses later record types.

The Event summary is concise, human-readable, neutral, and nonauthoritative. It supports navigation and review but is not the sole factual record, a formal finding, or an immutable title.

Draft and cancelled Events may omit occurrence and summary when they represent incomplete entry or unused paper allocation. Active, closed, invalidated, and superseded Events retain a valid occurrence and nonempty summary.

## Event Occurrence

Event occurrence is represented by one discriminated `occurrence` object with exactly one precision:

```text
exact
approximate
date_only
range
unknown
```

### Exact

An exact occurrence requires `started_at` and may include `ended_at`.

### Approximate

An approximate occurrence requires `started_at` and one approximation value:

```text
about
before
after
within_range
```

`within_range` also requires `ended_at`.

### Date Only

A date-only occurrence preserves one calendar date without inventing a time.

### Range

A range requires a start and end. The interval itself is the primary occurrence context, including a defined observation period.

### Unknown

An unknown occurrence requires one reason:

```text
not_known
not_reported
withheld
source_uncertain
legacy_import
```

It contains no fabricated date or timestamp.

All persisted timestamps require an explicit UTC offset or `Z`.

Portia must not derive occurrence time from:

* record creation;
* scan return;
* file modification;
* a default midnight value;
* a teacher schedule without confirmation;
* or route resolution.

Chronological ordering and contextual consistency are application-level validations.

## Location and Instructional Context

Location and instructional context are optional and separate.

Location uses a controlled `type` plus optional `detail`.

Initial location types are:

```text
classroom
hallway
cafeteria
transportation
online
field_trip
assembly
extracurricular
before_school
after_school
other
unknown
withheld
```

`other` requires meaningful detail.

Instructional context uses a controlled `type`, optional `detail`, and optional typed external references when those reference contracts are later defined.

Initial instructional-context types are:

```text
direct_instruction
independent_work
group_work
class_discussion
assessment
transition
laboratory
rehearsal
conference
unstructured_time
online_activity
other
unknown
not_applicable
```

Neither location nor instructional context changes Event ownership. The owning class remains authoritative for canonical storage.

An unmarked optional paper field means omitted. It does not automatically mean `unknown`.

## Minimum Participant Requirement

Event Participants are stored separately at:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/event_participant/<participant_id>.json
```

A draft Event may have zero or more participants.

An active Event requires at least one valid active Event Participant.

A closed Event preserves at least one valid participant relationship.

Any supported participant subject variant may satisfy the minimum:

```text
roster_student
actor
descriptive_person
unknown_person
```

No roster-student participant is specifically required.

Portia must not create fabricated student records or synthetic `whole_class` students to satisfy the requirement.

An active Event may legitimately contain an unknown person when uncertainty is explicit and honest.

The final active participant cannot be removed from an active Event without first adding or activating a valid replacement, changing the Event lifecycle appropriately, or invalidating the Event.

## Event Participant Record

Each Event Participant declares:

```text
schema_version
record_type
module_id
class_id
work_id
participant_id
status
subject
creation_source
created_at
created_by
updated_at
updated_by
```

For an Event Participant:

```text
record_type = event_participant
module_id = portia
participant_id = ep_<opaque-id>
```

The participant’s top-level `class_id` is the Event’s owning class, not necessarily the class that supplies a roster-student identity.

`work_id` identifies the parent Event. A separate embedded `event_id` is not required.

The participant record may also contain canonical forward replacement relationships:

```text
supersedes
```

The record must not contain authoritative embedded:

```text
role
roles
participant_roles
```

## Participant Subject Variants

The `subject` object uses one discriminator:

```text
kind
```

The initial subject variants are:

```text
roster_student
actor
descriptive_person
unknown_person
```

### Roster Student

A roster-student subject requires:

```text
student_ref.class_id
student_ref.student_id
display_snapshot.display_name
```

The durable identity is the complete roster-qualified pair:

```text
class_id + student_id
```

The display snapshot is required for historical readability but is not identity.

Cross-class roster students are permitted within the same teacher workspace. Their roster class does not change Event ownership.

### Actor

An Actor subject requires:

```text
actor_id
display_snapshot.display_name
```

The `actor_id` refers to the teacher-workspace Actor Directory established by ADR 0004.

A roster student must not be duplicated as an Actor merely to obtain workspace-scoped identity.

### Descriptive Person

A descriptive person is Event-local and has no durable Actor or roster identity.

It requires:

```text
description_type
display_label
```

Initial descriptive types are:

```text
outside_student
family_member
school_staff
visitor
community_member
other
```

Descriptive people are not automatically promoted to Actors.

### Unknown Person

An unknown person explicitly preserves unresolved identity.

It requires one reason:

```text
identity_not_known
identity_not_reported
identity_withheld
ambiguous_source
ambiguous_paper_mark
legacy_import
```

An optional description may preserve limited context without claiming identity.

An unknown participant may remain active indefinitely when that accurately reflects what is known.

## Participant Identity and Role

Participant identity and Event-level role are separate canonical concepts.

A participant may have zero, one, or several role assignments.

No role is required for Event activation.

The Event Participant schema contains no authoritative role fields.

Future Event Participant Role records will live separately, conceptually at:

```text
records/event_participant_role/<role_id>.json
```

Initial neutral role types are:

```text
directly_involved
present
reported_involved
contextual
```

Those roles describe relationship to the Event without establishing blame, fault, credibility, guilt, or a formal finding.

Labels such as the following are prohibited as generic participant roles:

```text
offender
victim
aggressor
perpetrator
guilty
responsible
problem_student
innocent
credible
dishonest
at_fault
```

Source and workflow roles that belong to later records remain separate, including reporter, observer, Account source, Response provider, support provider, follow-up owner, and decision maker.

A paper mark may propose a role, but it cannot activate the role automatically.

## Event Lifecycle

Event statuses are:

```text
draft
active
closed
cancelled
invalidated
superseded
```

Status describes record lifecycle only. It does not describe severity, responsibility, substantiation, discipline, or support outcome.

The ordinary lifecycle is:

```text
draft → active → closed
```

Allowed transitions are:

```text
draft → active
draft → cancelled

active → closed
active → invalidated
active → superseded

closed → active
closed → invalidated
closed → superseded
```

`cancelled`, `invalidated`, and `superseded` are terminal under ordinary workflows.

### Draft

A draft has not yet been accepted as a canonical representation of an occurrence. It may be incomplete and may represent digital work in progress, a preallocated paper Event, a returned page awaiting review, or an import awaiting confirmation.

### Active

An active Event has passed activation validation and is accepted as a canonical Event. Activation requires a valid occurrence, nonempty neutral summary, valid provenance, and at least one active Event Participant.

Active means open for ordinary documentation. It does not mean that the classroom situation remains ongoing.

### Closed

A closed Event remains valid, but ordinary documentation of the bounded occurrence is considered complete.

Closure does not establish a finding, end a linked Support Process, or prevent later provenance-preserving correction.

A closed Event may return to active with an explicit reason when additional ordinary documentation belongs to the same bounded occurrence.

### Cancelled

Cancellation applies only to a draft that was abandoned before activation, including an unused paper allocation or accidental blank draft.

A previously active Event never becomes cancelled.

### Invalidated

An invalidated Event is no longer treated as a valid representation of an occurrence.

Correctable field errors do not automatically require invalidation.

### Superseded

A superseded Event has been replaced by one or more canonical Events, such as when one Event is split into several Events or several overlapping Events are replaced by one reviewed Event.

Replacement Events own canonical forward `supersedes` relationships to the prior Event. Reverse `superseded_by` views are derived.

Every transition creates append-only lifecycle history. Root `status` remains the direct current-state field.

## Event Participant Lifecycle

Event Participant statuses are:

```text
proposed
active
invalidated
superseded
```

Allowed transitions are:

```text
proposed → active
proposed → invalidated
proposed → superseded

active → invalidated
active → superseded
```

`invalidated` and `superseded` are terminal under ordinary workflows.

### Proposed

A proposed participant has been suggested but not yet accepted. This state is useful for paper interpretation, imports, ambiguous matching, and incomplete entry.

A proposed participant does not satisfy Event activation.

### Active

An active participant is an accepted relationship between one represented person and the Event.

Active status does not establish responsibility, credibility, fault, or misconduct.

### Invalidated

An invalidated participant should no longer be treated as a valid relationship to the Event, and no replacement participant is required.

### Superseded

A superseded participant has been replaced by a corrected, resolved, or consolidated participant record.

A proposed participant may become active in place when the teacher confirms the same canonical subject.

A new participant record is required when the canonical subject changes materially, including:

* unknown person resolved to roster student or Actor;
* descriptive person replaced by roster student or Actor;
* incorrect roster student or Actor corrected;
* or duplicate participant records consolidated.

The replacement participant owns the canonical forward `supersedes` relationship to the prior participant.

When replacing the Event’s final active participant, the replacement must become active before the prior participant becomes superseded.

Every participant transition creates append-only lifecycle history.

## Creation Source and Local Provenance

Every Event and Event Participant records:

```text
creation_source
created_at
created_by
updated_at
updated_by
```

These fields remain top-level for direct inspection and indexing.

### Creation Source

Initial creation-source types are:

```text
digital_entry
paper_capture
import
```

#### Digital Entry

`digital_entry` indicates direct creation through Portia’s digital workflow.

#### Paper Capture

`paper_capture` requires:

```text
stage
route_id
page_record_id
```

Supported stages are:

```text
preallocated
ingested
```

`preallocated` applies when a canonical record exists before the paper page is rendered, ordinarily a draft Event.

`ingested` applies when a canonical record is created from information returned through the paper workflow, ordinarily a proposed child record.

The canonical term is `paper_capture`. Earlier illustrative terms such as `returned_paper` and `paper_quick_capture` are not normative schema values.

#### Import

`import` requires a meaningful `source_label` and may include an `external_reference`.

Import provenance does not imply review or accuracy.

### Attribution Agents

Initial attribution-agent types are:

```text
local_operator
system_process
```

A local operator requires a historical `display_label`.

A system process requires a machine-readable `process_id`.

Local attribution does not claim authenticated legal identity, an electronic signature, institutional authorization, or exclusive device access.

At creation:

```text
updated_at = created_at
updated_by = created_by
```

Creation source, creation time, and creation attribution are ordinarily immutable.

Update time and attribution change with canonical mutations.

Occurrence time remains separate from provenance time.

Lifecycle transition history remains separate from root update provenance.

No duplicate root-level `reviewed_at`, `reviewed_by`, `confirmed_at`, or `confirmed_by` fields are required for ordinary lifecycle confirmation.

## Paper Capture Workflow

Paper capture is an interface into the canonical Event model, not a separate record system.

Before rendering a class-specific capture page or slip, Portia creates:

* a draft Event root;
* a page record;
* a persisted PDS2 route;
* and the identifiers required to return the page to that Event.

The Event begins with:

```text
status = draft
creation_source.type = paper_capture
creation_source.stage = preallocated
```

After scanning, extracted participant or role information remains proposed.

A scan or recognition process must not activate:

* an Event;
* an Event Participant;
* or a participant role

without required teacher review.

The routine teacher-facing review actions should be concise:

```text
Confirm
Correct
Dismiss
Activate
```

An unused paper draft becomes cancelled rather than closed.

The current PDS2 design supports one routed page or slip per preallocated draft Event. A multi-entry capture sheet would require a separate capture-batch routing contract and is deferred.

## Teacher-Workflow Constraint

Portia’s internal lifecycle and provenance model may be rigorous, but routine teacher interaction must remain fast and proportionate.

Teachers should not ordinarily manage:

* technical lifecycle-state names;
* opaque identifiers;
* canonical relationship direction;
* filesystem paths;
* route IDs;
* page-record IDs;
* process IDs;
* timestamps;
* provenance objects;
* or append-only history records.

Portia must derive the necessary canonical operations from plain-language teacher actions.

For example, one action such as:

```text
Wrong student—change to Jordan Lee.
```

may internally:

1. create a corrected participant;
2. validate and activate it;
3. link it as superseding the prior participant;
4. supersede the prior participant;
5. write lifecycle history;
6. update provenance;
7. and refresh derived views.

The teacher experiences one correction action.

Routine direct digital capture should prioritize:

```text
select participant
→ record occurrence
→ enter brief neutral summary
→ save active Event
```

Portia must not force explicitly selected digital participants through a visible proposed-review step when no uncertainty exists.

Paper review should support batching, keyboard navigation, confirmation of several correct proposals, and correction only of uncertain fields.

Optional detail should use progressive disclosure.

A field or workflow step that creates teacher burden without a clear documentation, support, correction, privacy, or decision benefit should be omitted or deferred.

## Validation Boundary

The Event and Event Participant schemas use JSON Schema Draft 2020-12.

JSON Schema enforces local record structure, including:

* required fields;
* constants;
* enums;
* identifier formats;
* discriminated unions;
* timestamp syntax;
* mutually exclusive occurrence variants;
* mutually exclusive subject variants;
* creation-source variants;
* attribution-agent variants;
* and rejection of unknown or misplaced properties.

Application validation enforces conditions that require history, paths, external data, or multiple records, including:

* `class_id` and `work_id` matching canonical paths;
* owning class existence;
* school-year validity;
* roster-student reference validity;
* Actor existence;
* route and page-record existence;
* route ownership consistency;
* timestamp chronology;
* lifecycle transition legality;
* lifecycle-history existence;
* Event activation requiring an active participant;
* duplicate durable participants;
* final-active-participant protection;
* replacement ordering;
* canonical supersession consistency;
* imported or paper-derived review completion;
* and immutable creation provenance.

The schemas do not embed Event Participants inside the Event root and do not embed participant roles inside Event Participant records.

## Consequences

### Positive Consequences

* One Event has a clear semantic and lifecycle boundary.
* Event context remains distinct from evidence, interpretation, judgment, response, support, and outcome.
* Positive and neutral Events are first-class rather than exceptions to an incident model.
* Exact and uncertain occurrence information can both be represented honestly.
* Multi-student and cross-class Events remain possible without duplicating canonical work.
* Roster identity, Actor identity, descriptive identity, and unresolved identity remain explicit.
* Participant identity corrections preserve original uncertainty and prior claims.
* Participant roles do not contaminate identity records or imply unsupported findings.
* Paper and digital workflows converge on the same canonical schema.
* Automated paper interpretation remains reviewable rather than authoritative.
* Event and participant corrections remain auditable.
* Current status is directly loadable while transition history remains append-only.
* Root records remain relatively compact.
* Student-specific and Actor-specific histories can be derived from separate participant records.
* The model supports future privacy-conscious projections.
* Strict internal provenance does not require corresponding manual data entry.
* Teachers can capture useful information with a brief note and participant selection.
* No blocking change to `pds-core` is required.

### Costs and Tradeoffs

* Event activation and some corrections require cross-record application validation.
* Lifecycle history introduces additional child records.
* Replacement-based identity correction creates more records than unrestricted mutation.
* Reverse supersession views require derived indexing.
* Paper workflows require preallocation, persisted routing, and cleanup of unused drafts.
* Cross-class participants require explicit roster qualification and validation.
* Unknown and descriptive identities may require later teacher resolution.
* A strict schema cannot enforce every temporal, path, or cross-record invariant.
* Event Participant Role records require a separate schema before implementation.
* The interface must coordinate several internal writes as one teacher action.
* Recovery from partially completed coordinated writes requires later staged-write rules.
* Teacher-local attribution remains intentionally weaker than authenticated institutional audit.
* A future multi-user or institutional product will require a different authorization and audit architecture.

## Alternatives Considered

### Alternative A: One Mutable Incident Narrative

Under this alternative, the Event root would contain participants, observations, allegations, classifications, responses, outcomes, and later updates in one mutable narrative.

Rejected.

This would collapse source information, observation, interpretation, determination, and action. It would also make participant-specific privacy, correction, and projection unreliable.

### Alternative B: Event Per Participant

Under this alternative, one multi-student occurrence would create one Event for each participant.

Rejected.

This would duplicate shared context, obscure the fact that the records concern one occurrence, and allow copies to drift.

### Alternative C: Embed Participants in `work.json`

Under this alternative, the Event root would contain a participant array.

Rejected.

Participants require independent identity, status, provenance, correction, supersession, role assignment, and later targeting by child records.

### Alternative D: Embed Roles on Event Participant

Under this alternative, each Event Participant would contain one role or a role list.

Rejected.

Roles have their own lifecycle, provenance, basis, correction history, and potential multiplicity. Identity must remain valid even when no role is assigned.

### Alternative E: Mutable Participant Identity

Under this alternative, an unknown or descriptive participant could be edited directly into a roster student or Actor.

Rejected.

This would erase what was originally known and when identity resolution occurred.

### Alternative F: Replace Every Proposed Participant on Confirmation

Under this alternative, confirming any paper-derived participant would create a second participant record.

Rejected.

Routine confirmation of the same subject does not justify duplicate records. Proposed participants become active in place when identity is unchanged.

### Alternative G: Minimal Event Lifecycle

Under this alternative, Events would use only:

```text
draft
active
closed
```

Rejected.

It would conflate unused drafts, invalid records, duplicate Events, and replacement Events with valid completed Events.

### Alternative H: Derive Current Status Only From Transition History

Under this alternative, the Event root would contain no current status.

Rejected for Portia v1.

Every load and validation would require lifecycle-log resolution. The selected design stores current status on the root and append-only history separately.

### Alternative I: Simple Provenance Strings

Under this alternative, creation source and attribution would be stored as free-text strings.

Rejected.

Strings cannot reliably distinguish preallocation from paper ingestion, local operator actions from system processes, or import provenance from direct entry.

### Alternative J: Automatic Activation After Scanning

Under this alternative, a recognized paper page would immediately create active Events and participants.

Rejected.

Optical or handwriting interpretation may be uncertain. Teacher review is required before proposed values become accepted canonical records.

### Alternative K: Require Complete Documentation During Capture

Under this alternative, the teacher would complete context, roles, classifications, responses, and outcome fields before saving an Event.

Rejected.

Behavior-support documentation is secondary to instruction. Initial capture must remain brief, with optional detail deferred and progressively disclosed.

### Alternative L: Require a Roster Student for Every Event

Under this alternative, every active Event would require at least one roster-student participant.

Rejected.

Portia must honestly represent Events involving only non-roster Actors, descriptive people, or unknown participants without fabricating a student relationship.

## Implementation Constraints

Portia implementations must preserve these invariants:

1. One Event represents one coherent bounded context.
2. Unrelated occurrences are separate Events.
3. Event, Account, Observation, Classification, Determination, Response, Support Process, Follow-Up, Outcome, and Communication remain distinct.
4. Positive and neutral Events are fully supported.
5. Every Event has one class-owned canonical root.
6. The Event root stores only shared Event context.
7. Event Participants are separate canonical records.
8. Active Events require at least one active Event Participant.
9. No roster-student participant is specifically required.
10. Participants may be roster students, Actors, descriptive people, or unknown people.
11. Roster-student identity always uses `class_id + student_id`.
12. Display snapshots never function as identity.
13. Unknown participants may remain active without forced resolution.
14. Participant identity remains separate from participant role.
15. Event Participant Role records are separate and are not required for Event activation.
16. Occurrence precision is explicit.
17. Portia never fabricates occurrence time.
18. Location and instructional context never determine ownership.
19. Draft and cancelled Events may be incomplete.
20. Active, closed, invalidated, and superseded Events retain occurrence and summary.
21. Event statuses are `draft`, `active`, `closed`, `cancelled`, `invalidated`, and `superseded`.
22. Participant statuses are `proposed`, `active`, `invalidated`, and `superseded`.
23. Cancellation applies only before Event activation.
24. Invalidated and superseded records remain preserved.
25. Replacement records own canonical forward `supersedes` links.
26. Reverse replacement views are derived.
27. Material participant identity changes create replacement records.
28. Confirmation of the same proposed identity may occur in place.
29. Every lifecycle transition preserves append-only history.
30. Root current status and lifecycle history remain consistent.
31. Creation source is record-specific and ordinarily immutable.
32. Canonical creation-source types are `digital_entry`, `paper_capture`, and `import`.
33. Paper-capture stages are `preallocated` and `ingested`.
34. Attribution distinguishes `local_operator` from `system_process`.
35. Occurrence timestamps remain separate from provenance timestamps.
36. Scanning or automated interpretation never constitutes teacher confirmation.
37. Paper capture and digital entry produce the same canonical record types.
38. JSON Schema enforces local shape.
39. Application validation enforces cross-record and lifecycle invariants.
40. Unknown properties and misplaced embedded records are rejected.
41. Canonical records are not duplicated for histories, dashboards, or exports.
42. Teacher-facing actions remain concise and plain-language.
43. Technical provenance and relationship mechanics are populated automatically.
44. Routine capture does not require later-stage judgment or response records.
45. Workflow burden remains proportionate to instructional or support value.

## Follow-Up Decisions

Separate ADRs, schemas, or specifications should define:

* Event Participant Role schema and lifecycle;
* Event and participant lifecycle-transition schemas;
* general amendment and correction records;
* owning-class migration when storage ownership was incorrect;
* Account and Account-source schemas;
* Observation schema;
* Classification, Hypothesis, and Determination schemas;
* Response and Communication schemas;
* Support Process schema;
* Follow-Up and Outcome schemas;
* Actor Directory schema and lifecycle;
* typed external-module references;
* participant-targeting contracts for later records;
* duplicate-detection and consolidation workflows;
* detailed privacy projections for multi-student Events;
* redacted student-specific exports;
* staged-write, rollback, and recovery behavior;
* teacher schedule representation and context suggestions;
* PDS2 page-record and route schemas;
* possible capture-batch routing for multi-entry paper sheets;
* retention and archival integration with Sunset;
* authenticated multi-user provenance for any future institutional deployment;
* and performance targets for classroom capture and batch review.

## Notes

This decision defines the initial Event and Event Participant foundation, not a complete behavior-management application.

It deliberately separates:

```text
what occurred
when and where it occurred
who was connected to it
what each source said
what was later observed
what was inferred or classified
what was determined
what response or support was provided
and what happened afterward
```

The domain model is intentionally more rigorous than the routine interface.

That rigor exists to preserve uncertainty, correction, provenance, and participant-specific context. It must not become an excuse to require teachers to perform case-management administration during instruction.

Portia succeeds only when its records improve support, follow-up, instructional judgment, and recognition of positive progress while remaining fast enough for actual classroom use.
