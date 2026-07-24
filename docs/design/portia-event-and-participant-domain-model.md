# Portia Event and Event Participant Domain Model

## 1. Event Semantics and Boundary

### Decision

A Portia Event represents one time-bounded occurrence, interaction, observation period, or reported occurrence that can be understood as one coherent context.

An Event may include a short sequence of directly connected actions when those actions:

* occur within the same limited time period;
* arise from the same immediate circumstances;
* involve one substantially shared set of participants or observers;
* and can be documented accurately as one occurrence context.

An Event must not combine unrelated occurrences merely because they:

* involve the same student;
* occur in the same class;
* receive the same Classification;
* contribute to the same Support Process;
* or appear to form a recurring pattern.

The Event is the bounded context within which evidence, perspectives, participant relationships, Responses, and later Outcomes may be connected. It is not itself an Account, finding, judgment, intervention, or permanent case.

### Supported Event Forms

The initial model supports Events such as:

* one specific classroom occurrence;
* one positive observation;
* one brief interaction involving several people;
* one defined observation period;
* one short sequence of directly connected actions;
* one student or Actor report about an earlier occurrence;
* one Event with an approximate occurrence time;
* one occurrence documented after the fact;
* and one classroom Event initially captured on a Portia-generated paper quick-capture sheet.

An Event may be created without:

* a behavior concern;
* a Classification;
* a formal Response;
* an Outcome;
* or a Support Process.

Positive and neutral Events are therefore first-class records rather than exceptional uses of a concern-oriented schema.

### Observation Periods

An Event may represent a defined observation period rather than one instantaneous act.

For example:

```text
A five-minute independent-work observation
```

may be one Event when the observation has:

* a defined beginning and end;
* one shared instructional context;
* and one coherent documentation purpose.

An observation period must not become an indefinite monitoring record. Repeated observations across separate periods or dates should normally be separate Events that may later be linked to the same Support Process.

### Short Connected Sequences

Several actions may belong to one Event when separating them would remove essential context.

For example:

```text
A disagreement begins during group work,
continues through a brief teacher intervention,
and ends when the students return to separate seats.
```

This may be one Event because the actions form one continuous and coherent occurrence.

A later interaction after the class has ended, a renewed disagreement the next day, or a separate follow-up conversation is not automatically part of the original Event.

### Reported Events

An Event may document an occurrence reported after it happened.

The Event’s occurrence time remains distinct from:

* the time the report was made;
* the time the Event was entered;
* the time an Account was recorded;
* and the time the teacher responded.

The Event may preserve approximate or incomplete occurrence information without inventing false precision.

The person reporting the Event does not automatically become:

* an observer of every part of the occurrence;
* the authoritative source of all Event facts;
* or an Event Participant.

Those relationships must be represented explicitly.

### Event and Account Boundary

An Event represents the shared occurrence context.

An Account represents one attributed source’s description, recollection, or perspective concerning that Event.

An Event may therefore exist while:

* Accounts remain incomplete;
* Accounts conflict;
* no firsthand Account is available;
* or the Event is known only through one reported perspective.

The Event root must not absorb attributed statements into one apparently objective narrative.

### Event and Observation Boundary

An Observation records information presented as directly perceived or documented.

The Event provides the context to which the Observation belongs.

One Event may contain several Observations from:

* different times within the Event;
* different observers;
* different artifacts;
* or different participant-specific perspectives.

An Observation does not ordinarily become a separate Event unless it concerns a separately bounded occurrence or observation period.

### Event and Pattern Boundary

A recurring pattern is not one Event.

Patterns emerge from relationships among several Events, Observations, Follow-Ups, or other records.

For example:

```text
Three similar classroom occurrences across two weeks
```

should ordinarily be represented as three Events rather than one Event spanning two weeks.

A Support Process, derived timeline, or later analytic view may connect those Events without merging their original contexts.

### Event and Support-Process Boundary

An Event documents a bounded context.

A Support Process documents an ongoing teacher-managed effort to provide, implement, review, or adjust support.

A Support Process may:

* arise from one Event;
* arise from several Events;
* begin proactively without a triggering Event;
* and continue after all linked Events are closed.

An Event must not remain open merely to function as an ongoing support case.

### Event and Follow-Up Boundary

Information belongs to the original Event when it clarifies or corrects the bounded occurrence itself.

A later action ordinarily becomes a Follow-Up when it concerns:

* subsequent monitoring;
* a later conversation;
* implementation of a Response;
* review of impact;
* progress after the Event;
* or another action occurring outside the original Event boundary.

A later occurrence with its own bounded context should be represented as a new Event, even when it is related to the earlier Event.

### Event Boundary Test

Portia should treat information as part of one Event only when the teacher can reasonably answer yes to all of the following:

1. Does it concern one bounded occurrence, interaction, observation period, or reported occurrence?
2. Does it share one coherent immediate context?
3. Are the included actions directly connected rather than merely similar?
4. Can the Event be explained without relying on an indefinite student history?
5. Would separating the actions materially distort the occurrence?

When these conditions are not met, Portia should create separate Events and represent any relationship explicitly.

### Event-Boundary Invariants

1. One Event represents one coherent, time-bounded context.
2. An Event may contain a short sequence of directly connected actions.
3. An Event may represent a defined observation period.
4. An Event may be documented after it occurred.
5. Approximate occurrence information is permitted when its precision is recorded honestly.
6. Positive, neutral, and concern-related Events use the same fundamental Event model.
7. An Event does not require a Classification, Response, Outcome, or Support Process.
8. Accounts remain attributed records separate from the Event root.
9. Observations remain distinct records connected to the Event context.
10. Conflicting Accounts do not require separate Events unless they describe genuinely separate occurrences.
11. A recurring pattern across dates is represented through several Events and derived or explicit relationships.
12. A Support Process is not an Event and must not be implemented as an indefinitely open Event.
13. Later monitoring or review normally belongs in Follow-Up records.
14. A later bounded occurrence receives a new Event identity.
15. Related Events may be linked without being merged or duplicated.

## 2. Event Root Record

### Decision

Every Event root must:

* identify the Event and its canonical storage context;
* preserve its owning class and school year;
* declare its lifecycle status;
* identify its creation path;
* and preserve local creation and update provenance.

Before activation, the Event root must also:

* record the occurrence with honest temporal precision;
* and provide a concise neutral summary.

Location and instructional context are optional structured fields.

Participants, Accounts, Observations, Classifications, Responses, Determinations, Follow-Ups, Outcomes, and Supports remain separate canonical records.

The Event root must not become a single narrative record containing every fact, interpretation, participant relationship, and workflow action associated with the Event.

An Event may begin through:

```text
direct digital entry
Portia-generated paper quick capture
import
```

All creation paths produce the same canonical Event model. Paper is a capture interface, not a separate or reduced Event type.

---

## 2.1 Canonical Location

The Event root is stored as:

```text
classes/<class_id>/modules/portia/work/<event_id>/work.json
```

The Event ID is also the Core `work_id`.

For an Event:

```text
work_id = event_id
```

The containing path and the persisted identity must agree exactly.

A file stored beneath:

```text
classes/english10_p2/modules/portia/work/evt_01j7m2k4/work.json
```

must declare:

```text
module_id = portia
class_id = english10_p2
work_id = evt_01j7m2k4
work_kind = event
```

Portia must reject identity mismatches rather than infer or repair them silently.

---

## 2.2 Required Fields

The Event schema must distinguish between:

```text
fields required for every Event root
fields required before activation
optional contextual fields
```

This distinction allows Portia to create a legitimate preallocated draft before rendering a paper quick-capture page without inventing an occurrence or summary that has not yet been recorded.

### Required for Every Event Root

Every draft, active, closed, cancelled, invalidated, or superseded Event root requires:

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

### Required Before Activation

An Event must also contain the following before it may enter `active` or another completed operational state:

```text
occurrence
summary
```

The later lifecycle decision will determine exactly which non-draft states require the activation-complete field set. At minimum, an Event must not become active without both fields.

### Optional Context

The following root fields are optional:

```text
location
instructional_context
```

### Active Event Example

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j7m2k4",
  "school_year": "2026-2027",
  "status": "active",
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-18T09:14:00-04:00"
  },
  "summary": "Student requested a break appropriately during independent work.",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:22:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  },
  "updated_at": "2026-09-18T09:22:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

### Preallocated Paper Draft Example

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j7paper",
  "school_year": "2026-2027",
  "status": "draft",
  "creation_source": {
    "type": "paper_quick_capture",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_72a8..."
  },
  "created_at": "2026-09-18T07:10:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  },
  "updated_at": "2026-09-18T07:10:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

The draft does not contain placeholder occurrence data or a fabricated summary. Those values are added only after classroom capture and teacher review.

These examples illustrate the required shape. They do not finalize every controlled vocabulary or nested field used by the eventual JSON Schema.

---

## 2.3 Identity Fields

The following fields establish the Event’s durable identity and storage authority:

```text
schema_version
record_type
work_kind
module_id
class_id
work_id
school_year
```

### `schema_version`

`schema_version` identifies the Event schema contract used by the record.

The initial value is:

```text
1
```

The value must be stored as a string.

Unsupported future versions must be reported explicitly. Portia must not interpret an unknown schema version as though it were version `1`.

### `record_type`

The initial Event root uses:

```text
portia_work
```

This distinguishes the top-level work manifest from subordinate Portia records.

### `work_kind`

For an Event:

```text
event
```

The work kind must be declared explicitly.

Portia must not determine the work kind solely from the `evt_` identifier prefix.

### `module_id`

The module identifier is:

```text
portia
```

### `class_id`

`class_id` identifies the Event’s one owning Core class.

It determines the canonical work root and must remain stable after creation unless a deliberate provenance-preserving ownership-correction workflow is performed.

Participant roster classes do not alter this value.

### `work_id`

`work_id` is the Event’s durable opaque identifier.

It must:

* begin with the diagnostic prefix `evt_`;
* satisfy Core identifier safety rules;
* contain no student identity or sensitive Event meaning;
* remain stable through normal correction and lifecycle transitions;
* and match the containing work directory.

### `school_year`

`school_year` records the owning class’s academic year at Event creation.

It should initially be copied from valid Core class metadata.

The stored value remains part of the Event’s historical context even when:

* the active workspace school year changes;
* the class metadata is later corrected;
* or the Event becomes historical.

A correction to `school_year` requires recorded history and must not occur merely because the active workspace year changes.

---

## 2.4 Occurrence

Every activation-complete Event must contain a structured `occurrence` object.

A draft Event may omit `occurrence` while awaiting direct entry, paper return, import review, or teacher confirmation.

Occurrence information is required before activation because one Event represents a bounded occurrence, interaction, observation period, or reported occurrence.

Exact timestamp precision is not required when it is not known.

Portia must preserve uncertainty honestly rather than inventing a precise time.

The initial model should support these precision modes:

```text
exact
approximate
date_only
range
unknown
```

The precise field requirements for each mode will be defined in the Event-time section and enforced by the JSON Schema.

Representative forms include:

### Exact Time

```json
{
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-18T09:14:00-04:00"
  }
}
```

### Approximate Time

```json
{
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-18T09:15:00-04:00",
    "approximation": "about"
  }
}
```

### Date Only

```json
{
  "occurrence": {
    "precision": "date_only",
    "date": "2026-09-18"
  }
}
```

### Time Range

```json
{
  "occurrence": {
    "precision": "range",
    "started_at": "2026-09-18T09:10:00-04:00",
    "ended_at": "2026-09-18T09:20:00-04:00"
  }
}
```

### Unknown Time

```json
{
  "occurrence": {
    "precision": "unknown"
  }
}
```

Occurrence time remains distinct from:

* record-creation time;
* Account-recording time;
* Response time;
* Follow-Up time;
* import time;
* and page-scan time.

---

## 2.5 Summary

Every activation-complete Event requires a concise plain-language `summary`.

A draft Event may omit `summary` until the teacher has entered or confirmed a neutral description.

The summary exists to make Event lists, timelines, search results, and teacher-facing screens understandable without loading every subordinate record.

A summary should be:

* brief;
* factual in tone;
* neutral;
* understandable without sensitive information in its filename or identifier;
* and appropriate for display in a teacher-controlled Event list.

Examples include:

```text
Student requested a break appropriately during independent work.
```

```text
Two students disagreed during group work and separated after teacher direction.
```

```text
Student reported an earlier hallway interaction.
```

The summary must not be treated as:

* the sole factual record;
* an attributed Account;
* an objective Observation;
* a Classification;
* a formal finding;
* a diagnosis;
* a severity rating;
* or a participant-specific Determination.

The summary may be corrected or clarified.

Changes must update Event provenance and create the required history or amendment record under the later correction contract.

A summary must not be rewritten merely to make later interpretations appear to have been known at Event creation.

---

## 2.6 Lifecycle Status

Every Event requires a `status` field from creation onward.

The exact Event lifecycle vocabulary and transition rules will be decided in a later section.

The initial design anticipates values such as:

```text
draft
active
closed
cancelled
invalidated
superseded
```

The presence of a lifecycle status does not indicate:

* severity;
* responsibility;
* discipline;
* truthfulness;
* or whether a concern was substantiated.

Lifecycle status describes only the operational state of the Event record.

---

## 2.7 Creation Source

Every Event requires a structured `creation_source`.

The initial source types are:

```text
digital_entry
paper_quick_capture
import
```

These values describe how the canonical Event entered Portia. They do not create different Event schemas.

### Digital Entry

```json
{
  "creation_source": {
    "type": "digital_entry"
  }
}
```

### Paper Quick Capture

```json
{
  "creation_source": {
    "type": "paper_quick_capture",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_72a8..."
  }
}
```

A paper-quick-capture Event begins with a Portia-generated capture page associated with:

* one owning class;
* one preallocated draft Event ID;
* one Portia page-record ID;
* and one persisted Core PDS2 route registration.

The Event work root and draft `work.json` must exist before the page is rendered. This preserves the current PDS2 requirement that a returned page route identify a legitimate class-qualified Portia work context.

The printed page may allow the teacher to record concise classroom information while circulating, such as:

* a student selection or roster mark;
* exact, approximate, or date-only occurrence information;
* a short neutral note;
* a positive or concern-oriented capture marker;
* and a reminder that later review or follow-up may be needed.

The paper capture does not become an active Event automatically.

After the page returns through scanning, Portia must present the captured information for teacher review. The teacher must confirm or correct, as applicable:

* the owning class;
* the occurrence representation and precision;
* the neutral Event summary;
* each participant identity;
* and any optional location or instructional context.

The teacher may then:

```text
activate the Event
leave it as a draft
invalidate the draft
```

Handwriting recognition, mark interpretation, or imported scan data is proposed input. It is not authoritative until confirmed.

The later page return is part of the capture provenance; it is not a separate Event creation source. Unused preallocated paper drafts must remain distinguishable from active Events and require an explicit cleanup, cancellation, or invalidation workflow. They must not appear as completed Events merely because an ID and route were allocated.

### Import

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": null
  }
}
```

`creation_source` identifies how the Portia Event record entered the system.

It does not establish that the source was:

* correct;
* verified;
* firsthand;
* institutionally authorized;
* or the observer of the underlying Event.

The Event’s creation source remains distinct from:

* Event occurrence;
* Account-source attribution;
* scan time;
* import time;
* and local operator confirmation.

---

## 2.8 Creation and Update Provenance

Every Event requires:

```text
created_at
created_by
updated_at
updated_by
```

### Timestamps

`created_at` records when the canonical Event record was first created.

`updated_at` records when its current canonical representation was last changed.

Both timestamps must use timezone-aware ISO 8601 values.

At creation:

```text
created_at = updated_at
```

Later canonical changes update `updated_at` but do not alter `created_at`.

### Local Attribution

`created_by` and `updated_by` identify the locally recorded operator attribution.

Conceptually:

```json
{
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

These fields provide local provenance.

They do not claim:

* authenticated identity;
* a verified electronic signature;
* authorization;
* exclusive computer access;
* or institutional authorship.

The person who created the Event record is not automatically:

* the Event observer;
* an Event Participant;
* the source of every Account;
* or the person who selected every later Response.

Those relationships must be represented independently.

---

## 2.9 Optional Location

An Event may contain a structured `location` object.

Location is optional because it may be:

* unknown;
* approximate;
* withheld;
* unnecessary;
* virtual;
* or not relevant to the teacher’s documentation purpose.

Conceptually:

```json
{
  "location": {
    "type": "classroom",
    "display_detail": "Room 214"
  }
}
```

Possible high-level location types may later include:

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
```

A location value provides Event context.

It does not:

* determine the owning class;
* establish institutional jurisdiction;
* identify a school;
* or change Event storage.

The final controlled vocabulary and privacy rules remain later schema decisions.

---

## 2.10 Optional Instructional Context

An Event may contain a structured `instructional_context` object.

Conceptually:

```json
{
  "instructional_context": {
    "context_type": "independent_work",
    "display_label": "Independent reading",
    "external_refs": []
  }
}
```

Instructional context may describe:

* direct instruction;
* independent work;
* group work;
* assessment;
* transition;
* class discussion;
* laboratory work;
* rehearsal;
* online work;
* or another teacher-defined activity.

The object may later contain typed references to:

* a sibling-module Assignment;
* an Activity;
* an assessment;
* a lesson;
* a generated page;
* or another external instructional record.

Instructional context remains separate from location.

For example:

```text
location: classroom
instructional context: group work
```

or:

```text
location: field trip
instructional context: independent observation task
```

An external instructional reference remains owned by its originating module.

Portia records only its relevance to the Event.

---

## 2.11 Fields Excluded from the Event Root

The Event root must not directly embed canonical collections of:

```text
Event Participants
Accounts
Observations
Classifications
Concerns
Referrals
Responses
Determinations
Communications
Follow-Ups
Outcomes
Support Processes
Amendments
Attachments
generated pages
```

Those records receive:

* independent durable identities;
* separate canonical files;
* explicit parent or target references;
* and their own validation and lifecycle rules.

The Event root may later contain nonauthoritative summary values or derived counts, but such values must be clearly marked as derived and must not replace the subordinate canonical records.

For example, a future derived summary might report:

```json
{
  "derived_summary": {
    "participant_count": 2,
    "account_count": 3,
    "has_open_follow_up": true
  }
}
```

Such data must be rebuildable and must not be required to understand the Event’s canonical identity.

---

## 2.12 Mutability

The Event root contains both stable identity fields and correctable contextual fields.

### Stable Identity Fields

The following fields are ordinarily immutable after creation:

```text
record_type
work_kind
module_id
work_id
created_at
created_by
```

`class_id` is also stable under normal workflows because it controls canonical storage and work identity.

Correcting an incorrect owning class requires a dedicated provenance-preserving migration or supersession process.

### Historically Stable Context

The following fields may be corrected only through recorded history:

```text
school_year
occurrence
summary
location
instructional_context
creation_source
```

A correction must preserve:

* the prior value;
* the new value;
* the update timestamp;
* the local operator attribution;
* and, where required, the stated reason.

### Operational Fields

The following fields change through normal operation:

```text
status
updated_at
updated_by
```

Lifecycle transitions must still follow the accepted transition rules and history requirements.

---

## 2.13 Minimum Active Event

An Event may be created initially as a draft with incomplete contextual detail.

An Event must not become active until it contains at least:

```text
valid identity
valid owning class
valid school year
supported occurrence representation
nonempty neutral summary
valid creation source
valid creation and update provenance
supported lifecycle status
```

For a paper-quick-capture Event, activation additionally requires teacher review of the proposed scan or mark interpretation. A route match or successful scan alone is insufficient.

The participant requirement will be decided in the Event Participant section.

Until that decision is made, the root schema must not assume that participant data is embedded in `work.json`.

---

## 2.14 Root-Record Invariants

1. `work.json` is the canonical Event root record.
2. The Event ID and Core `work_id` are the same value.
3. Persisted identity must match the containing Core work path.
4. Every Event records one owning class and one school year.
5. Every activation-complete Event includes structured occurrence information.
6. Occurrence precision must be represented honestly.
7. Every activation-complete Event includes a concise neutral summary.
8. The summary is navigational context, not evidence or Determination.
9. Every Event declares a lifecycle status.
10. Every Event records its creation source.
11. Every Event preserves creation and update provenance.
12. Local operator attribution does not imply authentication.
13. Location is optional and does not determine ownership.
14. Instructional context is optional and separate from location.
15. Event Participants remain separate canonical records.
16. Accounts, Observations, Classifications, Responses, Follow-Ups, and Outcomes remain separate canonical records.
17. Identity fields are not silently rewritten.
18. Contextual corrections preserve prior values through history or amendment.
19. An Event root must remain understandable without collapsing all subordinate records into one narrative.
20. Digital entry, paper quick capture, and import produce the same canonical Event model.
21. Draft Event roots may omit occurrence and summary until activation requirements are met.
22. A Portia paper capture page is associated with a preallocated draft Event and persisted PDS2 route before rendering.
23. Scan or handwriting interpretation remains proposed data until teacher confirmation.
24. A returned paper capture must not activate an Event automatically.
25. Unused paper drafts remain distinguishable from completed Events.
26. Illustrative JSON in this design does not replace the normative JSON Schema.

## 2.15 Paper Quick-Capture Workflow

### Decision

Portia must support a classroom paper workflow equal in legitimacy to direct digital entry.

The expected workflow is:

```text
generate class-specific quick-capture page
→ persist draft Event, page record, and route
→ teacher writes while circulating
→ page returns through PDS2 scanning
→ Portia proposes captured values
→ teacher reviews and corrects
→ teacher activates, retains, or invalidates the draft
```

### Before Class

The teacher may generate one or more quick-capture pages for a selected class.

Before rendering each page, Portia must:

1. generate a new opaque Event ID;
2. create the class-scoped Event work root;
3. write a valid draft `work.json`;
4. create the Portia page record;
5. persist the Core route registration;
6. and render the PDS2 locator on the page.

The preallocated draft may omit fields required for activation, including the final occurrence representation, summary, and participant records. The Event schema must validate this draft shape without treating it as activation-complete.

The draft must still contain enough information to establish:

* Event identity;
* owning class;
* school year;
* draft lifecycle status;
* creation source;
* creation provenance;
* and page-route identity.

### During Class

The paper interface should support rapid, low-friction notation.

The teacher should not need to leave classroom circulation merely to create a valid Event.

The paper may provide compact spaces or marks for:

* roster-student selection;
* time or approximation;
* a short neutral note;
* positive or concern-oriented capture;
* and a follow-up reminder.

Paper fields are capture aids. They do not alter the canonical domain boundaries.

For example, a positive or concern marker may assist review or navigation, but it must not become a formal Classification or Determination merely because it appeared on the page.

### After Return

When the page is scanned:

1. Core resolves the PDS2 route.
2. Portia locates the existing draft Event and page record.
3. Portia extracts or presents the page’s captured information.
4. The teacher reviews all proposed canonical values.
5. Portia validates the reviewed Event and participant records.
6. The teacher explicitly activates, retains, or invalidates the draft.

The original page image or source artifact may be retained according to later attachment, privacy, and retention decisions.

The scan timestamp remains separate from the Event occurrence, report time, and creation time.

### One Canonical Event

The paper page is not a competing authoritative Event record.

After review:

* `work.json` remains the canonical shared Event record;
* Event Participant files remain the canonical participant relationships;
* the route registration remains the paper-routing record;
* and any retained scan remains a source artifact.

Digital and paper workflows must converge on the same validation, lifecycle, history, and correction rules.

### Current Routing Boundary

Under the accepted Portia work identity and current PDS2 locator, one routed Portia page belongs to one class-qualified `work_id`. The directly supported initial form is therefore one routed capture page or slip associated with one draft Event.

A single class sheet containing several independently created Event entries would require an additional capture-batch or multi-entry routing contract. That design is not established by this issue and must not be simulated by storing several Events beneath one Event work root.

Portia may use compact page formats or print several capture slips for a class, but it must preserve one canonical Event identity per captured occurrence.

### Paper-Workflow Invariants

1. Paper quick capture is a supported Portia v1 Event-creation path.
2. Every printed capture page has a legitimate owning class.
3. Every initially supported routed capture page or slip is associated with one preallocated draft Event.
4. The Event work root, page record, and route registration exist before rendering.
5. Paper capture does not create a second Event schema.
6. Scan interpretation is proposed data rather than accepted fact.
7. Teacher review is required before activation.
8. A returned page cannot activate an Event automatically.
9. The teacher may correct occurrence precision, summary, participant identity, and context before activation.
10. Unused or abandoned paper drafts require explicit lifecycle handling.
11. Paper markers do not automatically become Classifications, Determinations, or Responses.
12. The canonical Event and participant records remain digital Portia records after paper return.
13. A multi-entry class capture sheet requires a later explicit routing and storage decision.

---

## 3. Event Occurrence Model

### Decision

Every activation-complete Event must contain exactly one structured `occurrence` variant.

A draft Event may omit `occurrence`. Once supplied, the occurrence object must validate as exactly one supported variant.

The required `precision` discriminator determines:

* which temporal fields are required;
* which temporal fields are permitted;
* how the occurrence is displayed;
* and what uncertainty the record preserves.

The initial occurrence precision values are:

```text
exact
approximate
date_only
range
unknown
```

Portia must record the precision actually known.

It must not manufacture an exact occurrence timestamp from:

* Event creation time;
* Account creation time;
* a class schedule;
* an import timestamp;
* a page-scan timestamp;
* midnight on a known date;
* or another convenient default.

The occurrence object describes when the underlying Event happened or was observed.

It remains distinct from when the Event was:

* reported;
* entered;
* imported;
* updated;
* reviewed;
* or acted upon.

---

## 3.1 Discriminated Occurrence Variants

The `occurrence` object is a discriminated union.

Conceptually, the Event schema should use `precision` as the discriminator and validate the remaining object against exactly one supported variant.

Each variant must:

* require its own relevant fields;
* prohibit fields belonging to other variants;
* and reject contradictory temporal representations.

For example, this must be invalid:

```json
{
  "occurrence": {
    "precision": "unknown",
    "started_at": "2026-09-18T09:14:00-04:00"
  }
}
```

Likewise, this must be invalid:

```json
{
  "occurrence": {
    "precision": "date_only",
    "date": "2026-09-18",
    "started_at": "2026-09-18T09:14:00-04:00"
  }
}
```

Portia must not choose which conflicting value to trust.

---

## 3.2 Exact Occurrence

Use `exact` when the teacher or source knows the occurrence start time with reasonable confidence.

### Point or Start Time

```json
{
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-18T09:14:00-04:00"
  }
}
```

### Known Duration

```json
{
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-18T09:14:00-04:00",
    "ended_at": "2026-09-18T09:18:00-04:00"
  }
}
```

### Required Fields

```text
precision
started_at
```

### Optional Fields

```text
ended_at
```

### Prohibited Fields

```text
date
approximation
reason
```

### Rules

1. `precision` must equal `exact`.
2. `started_at` must be a timezone-aware ISO 8601 timestamp.
3. `ended_at`, when present, must be a timezone-aware ISO 8601 timestamp.
4. `ended_at` must not precede `started_at`.
5. The timestamp represents the teacher’s reasonably confident knowledge, not mathematical certainty.
6. An exact occurrence may have a known duration without becoming a `range` occurrence when the Event is understood primarily as an occurrence or interaction with a known start.
7. Portia must not label a timestamp exact merely because the interface supplied a default value.

---

## 3.3 Approximate Occurrence

Use `approximate` when a useful timestamp estimate is available but should not be presented as exact.

The initial approximation values are:

```text
about
before
after
within_range
```

### About a Time

```json
{
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-18T09:15:00-04:00",
    "approximation": "about"
  }
}
```

### Before a Time

```json
{
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-18T09:15:00-04:00",
    "approximation": "before"
  }
}
```

### After a Time

```json
{
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-18T09:15:00-04:00",
    "approximation": "after"
  }
}
```

### Within an Estimated Range

```json
{
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-18T09:10:00-04:00",
    "ended_at": "2026-09-18T09:20:00-04:00",
    "approximation": "within_range"
  }
}
```

### Required Fields

```text
precision
started_at
approximation
```

### Conditionally Required Fields

`ended_at` is required when:

```text
approximation = within_range
```

### Prohibited Fields

```text
date
reason
```

### Rules

1. `precision` must equal `approximate`.
2. `started_at` must be a timezone-aware ISO 8601 timestamp.
3. `approximation` must use a supported controlled value.
4. `ended_at` is permitted only when `approximation` is `within_range`.
5. When present, `ended_at` must occur after `started_at`.
6. Portia must display the approximation qualifier wherever the occurrence time is presented as a fact.
7. Sorting by the stored estimate does not make the estimate exact.
8. Schedule information may suggest an approximate timestamp, but the teacher must confirm that it accurately represents what is known.

The meaning of `started_at` depends on `approximation`:

| Approximation  | Meaning of `started_at`                                       |
| -------------- | ------------------------------------------------------------- |
| `about`        | The Event occurred at approximately this time                 |
| `before`       | The Event occurred before this time                           |
| `after`        | The Event occurred after this time                            |
| `within_range` | The Event occurred within the interval beginning at this time |

For `within_range`, `ended_at` supplies the interval’s upper boundary.

---

## 3.4 Date-Only Occurrence

Use `date_only` when the calendar date is known but no reliable clock time is available.

```json
{
  "occurrence": {
    "precision": "date_only",
    "date": "2026-09-18"
  }
}
```

### Required Fields

```text
precision
date
```

### Prohibited Fields

```text
started_at
ended_at
approximation
reason
```

### Rules

1. `precision` must equal `date_only`.

2. `date` must use the ISO calendar-date format:

   ```text
   YYYY-MM-DD
   ```

3. Portia must not convert the date into a persisted midnight timestamp.

4. Portia must not infer a class period or clock time from the owning class.

5. Teacher-facing displays must communicate that the time is not known.

6. Date-only Events may be sorted by date, but any within-day ordering is derived and nonfactual.

A display may say:

```text
September 18, 2026 — time not recorded
```

It must not present:

```text
September 18, 2026 at 12:00 AM
```

unless midnight was actually recorded as the occurrence time.

---

## 3.5 Range Occurrence

Use `range` when the bounded interval itself is the primary occurrence or observation context.

This variant is especially appropriate for:

* structured observation periods;
* defined monitoring windows;
* class activities observed over a known interval;
* or another Event whose meaning depends on the complete start-to-end window.

```json
{
  "occurrence": {
    "precision": "range",
    "started_at": "2026-09-18T09:10:00-04:00",
    "ended_at": "2026-09-18T09:20:00-04:00"
  }
}
```

### Required Fields

```text
precision
started_at
ended_at
```

### Prohibited Fields

```text
date
approximation
reason
```

### Rules

1. `precision` must equal `range`.
2. Both timestamps must be timezone-aware ISO 8601 values.
3. `ended_at` must occur after `started_at`.
4. The range must represent one coherent bounded Event.
5. A range must not be used to combine separate occurrences merely because they involve the same student or concern.
6. A range must not substitute for an ongoing Support Process or indefinite monitoring record.
7. Repeated observation periods ordinarily receive separate Event identities.

### Exact Duration Versus Range Context

Both an `exact` occurrence and a `range` occurrence may contain start and end timestamps.

Their semantic distinction is:

```text
exact
```

The Event is primarily understood as an occurrence or interaction whose start is known, with an optional known completion time.

```text
range
```

The defined interval itself is the Event’s observation or documentation context.

Examples:

```text
exact:
A disagreement began at 9:14 and ended at 9:18.
```

```text
range:
A structured classroom observation was conducted from 9:10 to 9:20.
```

The distinction reflects the Event’s meaning rather than a difference in timestamp accuracy.

---

## 3.6 Unknown Occurrence Time

Use `unknown` when neither a calendar date nor a reliable time estimate is available.

```json
{
  "occurrence": {
    "precision": "unknown",
    "reason": "not_reported"
  }
}
```

The initial reason values are:

```text
not_known
not_reported
withheld
source_uncertain
legacy_import
```

### Required Fields

```text
precision
reason
```

### Prohibited Fields

```text
date
started_at
ended_at
approximation
```

### Rules

1. `precision` must equal `unknown`.
2. `reason` must use a supported controlled value.
3. No date or timestamp may be stored in the occurrence object.
4. Event creation time must not be substituted for occurrence time.
5. A reported or imported Event may remain active with unknown occurrence time.
6. The Event must still describe one coherent occurrence rather than an indefinite pattern.
7. Teacher-facing displays must make the missing occurrence information visible.

Representative meanings include:

| Reason             | Meaning                                                  |
| ------------------ | -------------------------------------------------------- |
| `not_known`        | The occurrence time could not be determined              |
| `not_reported`     | The source did not provide occurrence-time information   |
| `withheld`         | The time was intentionally not disclosed or recorded     |
| `source_uncertain` | Available sources conflict or are too uncertain          |
| `legacy_import`    | The imported source lacked reliable occurrence-time data |

An unknown occurrence time is incomplete information, not an invalid Event identity.

---

## 3.7 Activation with Unknown Time

An Event with:

```text
precision = unknown
```

may become active.

Activation requires that:

* the uncertainty is explicit;
* a supported unknown-time reason is recorded;
* the Event has a meaningful neutral summary;
* the Event still describes one coherent reported or documented occurrence;
* the owning class is legitimate;
* and all other active-Event validation requirements are satisfied.

Portia must not require the teacher to invent a date or timestamp merely to activate an otherwise valid Event.

An Event must not become active when `unknown` is being used to avoid defining whether the record concerns:

* one occurrence;
* several occurrences;
* a recurring pattern;
* or an ongoing Support Process.

Temporal uncertainty is supported.

Semantic indeterminacy about what the Event represents is not.

---

## 3.8 Timezone Rules

All persisted occurrence timestamps must include an explicit UTC offset.

Valid examples include:

```text
2026-09-18T09:14:00-04:00
2026-12-18T09:14:00-05:00
2026-09-18T13:14:00Z
```

A local timestamp without an offset must be rejected:

```text
2026-09-18T09:14:00
```

Portia should preserve the confirmed offset supplied at entry or import.

It must not silently reinterpret an existing occurrence timestamp merely because:

* the computer timezone changes;
* daylight-saving rules change;
* the workspace moves to another device;
* or the Event is viewed from another location.

Teacher-facing displays may convert timestamps for presentation when the conversion is clearly controlled, but the canonical value must remain stable.

---

## 3.9 Schedule Assistance

A teacher schedule may assist occurrence entry.

Portia may:

* suggest the current class period;
* suggest the current timestamp;
* identify the likely instructional block;
* or warn that a selected time conflicts with the selected owning class.

Schedule assistance must not:

* silently populate a historical Event time;
* convert an unknown time to exact;
* choose an owning class without confirmation;
* or override a teacher-confirmed occurrence value.

Suggested values become canonical facts only after explicit confirmation.

The existence of a scheduled class at a particular time does not prove that the Event occurred at that time.

A paper quick-capture page may contain a handwritten time, approximation mark, or blank time field. Portia must convert that capture into one proposed occurrence variant and require teacher confirmation. The page-return timestamp and scan timestamp must never substitute for the occurrence.

---

## 3.10 Reported Time and Occurrence Time

A reported Event may require several distinct temporal facts.

For example:

```text
Event occurred:
September 18 at approximately 9:15 AM

Student reported it:
September 19 at 1:05 PM

Teacher created the Event:
September 19 at 1:12 PM
```

The Event root occurrence object stores only the first fact.

The report time belongs to the later Account or source record.

The creation time belongs to:

```text
created_at
```

Portia must not collapse these values into one timestamp.

---

## 3.11 Sorting and Derived Temporal Values

Portia may derive sortable values from occurrence data.

For example:

| Precision     | Possible derived sort key |
| ------------- | ------------------------- |
| `exact`       | `started_at`              |
| `approximate` | estimated `started_at`    |
| `date_only`   | calendar date             |
| `range`       | `started_at`              |
| `unknown`     | no occurrence sort key    |

Derived sort keys:

* are nonauthoritative;
* must not be written back as occurrence facts;
* must not remove approximation labels;
* and must be reproducible from canonical data.

When Events with unknown times appear in a timeline, Portia should group or label them explicitly rather than assigning fabricated positions.

---

## 3.12 Occurrence Corrections

Occurrence information may be corrected when better information becomes available.

Examples include:

* correcting the calendar date;
* changing `date_only` to `approximate`;
* replacing `unknown` with an exact timestamp;
* correcting an incorrect timezone offset;
* or narrowing an approximate interval.

A correction must preserve:

* the prior occurrence object;
* the replacement occurrence object;
* the update timestamp;
* local operator attribution;
* and the correction reason when required.

A precision change must not rewrite history as though the more precise value had always been known.

For example, replacing:

```json
{
  "precision": "unknown",
  "reason": "not_reported"
}
```

with:

```json
{
  "precision": "exact",
  "started_at": "2026-09-18T09:14:00-04:00"
}
```

must preserve evidence that the original Event was entered without a reported time.

The exact history or Amendment mechanism will be finalized in the correction section.

---

## 3.13 Schema Requirements

The Event JSON Schema should implement occurrence variants through mutually exclusive conditional shapes.

Conceptually:

```text
occurrence
  oneOf:
    exact occurrence
    approximate occurrence
    date-only occurrence
    range occurrence
    unknown occurrence
```

Each branch should:

* require a constant `precision` value;
* declare its required fields;
* reject unrelated properties;
* enforce timestamp or date formats;
* and prevent multiple branches from validating simultaneously.

JSON Schema can validate structural and format requirements.

Some chronological rules may require application-level validation, including:

```text
ended_at > started_at
```

The design must distinguish:

* constraints enforced directly by JSON Schema;
* and semantic constraints enforced by Portia application logic.

Both remain normative.

---

## 3.14 Occurrence Invariants

1. Every Event contains exactly one occurrence variant.
2. `precision` determines the required and permitted fields.
3. Contradictory occurrence representations are invalid.
4. Exact timestamps require explicit timezone offsets.
5. Approximate timestamps remain visibly qualified.
6. Date-only Events do not receive fabricated midnight timestamps.
7. Range Events represent one bounded coherent interval.
8. Unknown occurrence time is permitted when the uncertainty is explicit.
9. An active Event may have unknown occurrence time.
10. Event creation time never substitutes for occurrence time.
11. Report time remains separate from occurrence time.
12. Account creation time remains separate from occurrence time.
13. Schedule information may assist entry but does not establish occurrence facts.
14. Portia does not manufacture precision from defaults or contextual inference.
15. Derived sorting values are nonauthoritative.
16. Occurrence corrections preserve prior values and provenance.
17. Schema validation prohibits fields that do not belong to the selected variant.
18. Application validation enforces chronological ordering that JSON Schema cannot reliably express.
19. Temporal uncertainty does not permit an Event to become an indefinite pattern or ongoing case.
20. Handwritten or scanned time information remains proposed until teacher confirmation.
21. Page-return and scan timestamps never substitute for Event occurrence.
22. The canonical occurrence object preserves what was actually known about when the Event occurred.

## 4. Location and Instructional Context

### Decision

Portia represents Event location and instructional context through separate optional structured objects.

Each object combines:

* a small controlled `type` vocabulary;
* optional teacher-entered clarification;
* and, where applicable, typed references to external instructional records.

This structure supports:

* consistent filtering;
* concise paper capture;
* teacher-facing display;
* future reporting;
* and classroom situations not anticipated by the initial vocabulary.

Location and instructional context provide descriptive context only.

They do not determine:

* Event ownership;
* student identity;
* institutional jurisdiction;
* Event severity;
* or whether a concern occurred.

---

## 4.1 Location and Instructional Context Are Distinct

Location answers:

> Where did the Event occur?

Instructional context answers:

> What instructional or classroom activity was occurring?

For example:

```json
{
  "location": {
    "type": "classroom",
    "detail": "Room 214"
  },
  "instructional_context": {
    "type": "group_work",
    "detail": "Literary analysis stations",
    "external_refs": []
  }
}
```

The two objects must not be collapsed.

The same instructional context may occur in several locations:

```text
independent work in the classroom
independent work during a field trip
independent work online
```

Likewise, several instructional contexts may occur in the same location:

```text
direct instruction in the classroom
group work in the classroom
assessment in the classroom
transition in the classroom
```

---

## 4.2 Optionality

Both objects are optional:

```text
location
instructional_context
```

An Event may remain valid when either or both are absent.

Absence means only that the object was not recorded.

When Portia needs to distinguish an omitted value from an explicitly unknown, withheld, or inapplicable value, the appropriate controlled `type` should be stored.

For example:

```json
{
  "location": {
    "type": "unknown"
  }
}
```

is different from an Event containing no `location` object.

The first records that location was considered but not known.

The second makes no claim about why location was omitted.

---

## 4.3 Location Object

The initial location structure is:

```json
{
  "location": {
    "type": "classroom",
    "detail": "Back table"
  }
}
```

### Required Field

When `location` is present, it requires:

```text
type
```

### Optional Field

```text
detail
```

### Initial Location Types

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

### Location-Type Meanings

| Type              | Meaning                                                       |
| ----------------- | ------------------------------------------------------------- |
| `classroom`       | A classroom or other normal instructional room                |
| `hallway`         | A corridor, stairwell, or transition space                    |
| `cafeteria`       | A cafeteria or meal-service area                              |
| `transportation`  | A bus, vehicle, loading area, or transportation context       |
| `online`          | A virtual meeting, learning platform, or other online setting |
| `field_trip`      | An off-site or class-sponsored trip                           |
| `assembly`        | An assembly, presentation, or school gathering                |
| `extracurricular` | A club, performance, team, or other extracurricular setting   |
| `before_school`   | A setting or activity before the instructional day            |
| `after_school`    | A setting or activity after the instructional day             |
| `other`           | A known location not represented by another controlled type   |
| `unknown`         | The location could not be determined                          |
| `withheld`        | The location was deliberately not recorded or disclosed       |

---

## 4.4 Location Detail

`detail` is optional free text that clarifies the broad location type.

Examples include:

```json
{
  "location": {
    "type": "classroom",
    "detail": "Back table"
  }
}
```

```json
{
  "location": {
    "type": "hallway",
    "detail": "Outside Room 214"
  }
}
```

```json
{
  "location": {
    "type": "online",
    "detail": "Class video meeting"
  }
}
```

`detail` must not contain information that belongs in:

* an Account;
* an Observation;
* an Event summary;
* a Classification;
* or a participant-specific record.

For example, this is inappropriate:

```json
{
  "location": {
    "type": "classroom",
    "detail": "Back table where the student became disruptive"
  }
}
```

The phrase describing alleged conduct belongs elsewhere.

When:

```text
type = other
```

a nonempty `detail` is required so the location remains understandable.

When:

```text
type = unknown
```

or:

```text
type = withheld
```

`detail` should normally be absent. Portia may later define a separate explanatory or provenance field when additional explanation is necessary.

---

## 4.5 Location Does Not Determine Ownership

The Event’s owning class remains established through the accepted identity and ownership model.

Location must not change that ownership automatically.

For example:

```text
owning class: english10_p2
location: hallway
```

may accurately represent an Event that occurred while the teacher was supervising or transitioning the Period 2 class.

Likewise:

```text
owning class: english10_p2
location: field_trip
```

may represent an Event occurring during a class trip.

Portia must not:

* create a hallway class;
* create a cafeteria class;
* create a transportation class;
* transfer ownership because the Event occurred outside the classroom;
* or infer schoolwide ownership from a location value.

When no legitimate owning class exists, recording a location does not make the Event representable under the normal Portia v1 ownership model.

---

## 4.6 Instructional-Context Object

The initial instructional-context structure is:

```json
{
  "instructional_context": {
    "type": "independent_work",
    "detail": "Independent reading",
    "external_refs": []
  }
}
```

### Required Field

When `instructional_context` is present, it requires:

```text
type
```

### Optional Fields

```text
detail
external_refs
```

### Initial Instructional-Context Types

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

### Instructional-Context Meanings

| Type                 | Meaning                                                           |
| -------------------- | ----------------------------------------------------------------- |
| `direct_instruction` | Teacher-led explanation, modeling, demonstration, or lecture      |
| `independent_work`   | Individual student work                                           |
| `group_work`         | Collaborative work involving pairs or groups                      |
| `class_discussion`   | Whole-class or structured discussion                              |
| `assessment`         | Quiz, test, performance task, or another assessment context       |
| `transition`         | Movement or change between activities, spaces, or class periods   |
| `laboratory`         | Laboratory, practical, workshop, or hands-on technical activity   |
| `rehearsal`          | Practice, rehearsal, or preparation for a performance             |
| `conference`         | An individual or small-group teacher conference                   |
| `unstructured_time`  | Teacher-supervised time without a defined instructional task      |
| `online_activity`    | An instructional activity conducted through an online environment |
| `other`              | A known instructional context not represented by another type     |
| `unknown`            | The instructional context could not be determined                 |
| `not_applicable`     | The Event did not occur during an instructional activity          |

---

## 4.7 Instructional Detail

`detail` provides optional teacher-facing clarification.

Examples include:

```json
{
  "instructional_context": {
    "type": "independent_work",
    "detail": "Independent reading"
  }
}
```

```json
{
  "instructional_context": {
    "type": "group_work",
    "detail": "Literary analysis stations"
  }
}
```

```json
{
  "instructional_context": {
    "type": "assessment",
    "detail": "Unit 1 constructed-response assessment"
  }
}
```

When:

```text
type = other
```

a nonempty `detail` is required.

When:

```text
type = unknown
```

or:

```text
type = not_applicable
```

`detail` should normally be absent.

Instructional detail must remain concise contextual information.

It must not become:

* an Event narrative;
* a copied Assignment;
* an Account;
* an Observation;
* or a participant-specific description.

---

## 4.8 External Instructional References

`instructional_context.external_refs` may contain typed references to instructional records owned by Core or another Paper Data Suite module.

Potential references include:

* an Assignment;
* a Concord Activity;
* a ScoreForm assessment;
* a Quillan writing task;
* a generated page;
* a lesson;
* or another durable instructional record.

Conceptually:

```json
{
  "instructional_context": {
    "type": "assessment",
    "detail": "Unit 1 assessment",
    "external_refs": [
      {
        "module_id": "scoreform",
        "class_id": "english10_p2",
        "work_id": "unit_1_assessment",
        "record_kind": "assignment",
        "record_id": "asg_01j8..."
      }
    ]
  }
}
```

The final shared typed-reference contract remains a later decision.

Every external reference must preserve the originating record’s ownership.

Portia records only the relationship between that instructional record and the Event.

Portia must not:

* copy the external record into the Event;
* use a display title as identity;
* rely on an absolute filesystem path;
* or infer a reference from similar names.

An external reference does not change:

* Event ownership;
* Event identity;
* or the authority of the originating module.

---

## 4.9 Several Instructional References

One Event may reference several instructional records when they describe the same coherent context.

For example, an Event occurring during a returned assessment page might reference:

* the ScoreForm assignment;
* and the specific Portia or Core page record.

Several references do not permit unrelated instructional contexts to be combined into one Event.

The Event-boundary rules remain controlling.

---

## 4.10 Paper Quick Capture

A Portia-generated quick-capture page should present a compact subset of common location and instructional-context types.

For example, the paper page may provide location marks such as:

```text
Classroom
Hallway
Online
Other: __________
```

and instructional-context marks such as:

```text
Direct instruction
Independent work
Group work
Assessment
Transition
Other: __________
```

The printed form does not need to expose every supported controlled value.

A handwritten or marked selection becomes proposed data after scanning.

Before Event activation, the teacher must be able to:

* confirm the interpreted value;
* select another supported type;
* add or correct `detail`;
* omit the object;
* or record `unknown`, `withheld`, or `not_applicable` where appropriate.

Paper capture must not silently translate an unmarked field into:

```text
unknown
```

or:

```text
not_applicable
```

An unmarked field ordinarily means that no value was captured.

---

## 4.11 Display and Filtering

Portia may use the controlled `type` fields for:

* teacher-facing filters;
* Event lists;
* timelines;
* class summaries;
* derived reports;
* and quick-capture form generation.

For example, a teacher may filter for:

```text
location = hallway
```

or:

```text
instructional_context.type = group_work
```

Filtering by these fields must not imply:

* causation;
* student risk;
* instructional quality;
* Event severity;
* or a behavior judgment.

Teacher-entered `detail` may support display or text search but should not become a controlled classification.

---

## 4.12 Corrections

Location and instructional context may be corrected after Event creation.

A correction must preserve:

* the prior object or absence;
* the replacement object or removal;
* the update timestamp;
* local operator attribution;
* and the correction reason when required.

A correction to either object does not ordinarily create a new Event.

Changing location or instructional context must not silently change the owning class.

When the corrected context shows that the Event was created under the wrong owning class, ownership correction must follow the separate provenance-preserving ownership-migration or supersession process.

---

## 4.13 Schema Requirements

The Event JSON Schema should enforce the following structural rules.

### Location

When present:

* `location` is an object;
* `type` is required;
* `type` uses the controlled vocabulary;
* `detail` is optional text;
* unknown properties are rejected;
* and `detail` is required when `type` is `other`.

### Instructional Context

When present:

* `instructional_context` is an object;
* `type` is required;
* `type` uses the controlled vocabulary;
* `detail` is optional text;
* `external_refs` is an optional array;
* unknown properties are rejected;
* and `detail` is required when `type` is `other`.

The schema should prohibit empty strings where a meaningful `detail` is required.

Some semantic constraints may remain application-level validation, including whether:

* an external record exists;
* an external reference belongs to the expected module and class;
* or a chosen context is plausible for a particular owning class.

---

## 4.14 Location and Instructional-Context Invariants

1. Location and instructional context are separate optional objects.
2. Each object uses a controlled `type` plus optional clarification.
3. Omission is distinct from explicitly recording `unknown`, `withheld`, or `not_applicable`.
4. Location describes where the Event occurred.
5. Instructional context describes what instructional or classroom activity was occurring.
6. Neither object determines Event ownership.
7. Neither object creates institutional jurisdiction.
8. Neither object may contain participant-specific allegations or findings.
9. `other` requires a meaningful clarifying detail.
10. Location supports explicit `unknown` and `withheld` values.
11. Instructional context supports explicit `unknown` and `not_applicable` values.
12. External instructional references remain owned by their originating modules.
13. External references do not transfer Event ownership.
14. Paper quick capture may expose a concise subset of common values.
15. Scan interpretation remains proposed until teacher confirmation.
16. An unmarked paper field does not automatically mean unknown or inapplicable.
17. Controlled types may support filtering but must not be treated as causal or evaluative data.
18. Corrections preserve prior values and provenance.
19. Correcting context does not silently change the owning class.
20. Location and instructional context remain descriptive context rather than evidence, interpretation, or Determination.

## 5. Minimum Event Participant Requirement

### Decision

Participant requirements depend on the Event’s lifecycle state.

A draft Event may contain zero or more Event Participants.

An Event must contain at least one valid active Event Participant before it may enter the `active` lifecycle state.

A closed Event must continue to preserve at least one valid participant relationship.

This rule supports incomplete digital entry and preallocated paper quick-capture drafts without permitting active Events whose relationship to any person is undefined.

Conceptually:

```text
draft Event:
zero or more Event Participants

active Event:
one or more active Event Participants

closed Event:
one or more preserved valid Event Participants
```

An Event Participant remains a separate canonical record beneath:

```text
records/event_participant/<participant_id>.json
```

Participants must not be embedded as an authoritative array inside `work.json`.

---

## 5.1 Draft Events

A draft Event may exist without an Event Participant.

This is necessary when:

* a paper quick-capture Event is preallocated before class;
* handwriting or roster marks have not yet been reviewed;
* a teacher begins digital entry before selecting a person;
* participant identity remains unresolved;
* or an imported Event requires review before participant records are created.

For example, Portia may create:

```text
classes/english10_p2/modules/portia/work/evt_01j9.../
  work.json
  pages/
    pg_01j9....json
  routes/
    rt_0123456789abcdef0123456789abcdef.json
```

before any file exists beneath:

```text
records/event_participant/
```

The absence of participants must remain visible in draft validation and teacher-facing review.

Portia must not treat the owning class, Event summary, paper route, or local operator as an implied Event Participant.

---

## 5.2 Activation Requirement

Before an Event becomes active, Portia must validate that it contains at least one Event Participant whose:

* record structure is valid;
* participant ID is valid and unique within the Event;
* parent Event reference is correct;
* subject uses one supported identity variant;
* lifecycle state represents a current participant relationship;
* and identity has been reviewed when it originated through paper capture, import, or uncertain automated interpretation.

Activation must fail clearly when no participant satisfies those conditions.

Portia must not satisfy the requirement through:

* an empty participant placeholder;
* the Event’s owning class;
* a copied display name;
* the teacher’s local operator identity;
* an invented student;
* a synthetic `whole_class` student;
* or a malformed unresolved-person record.

---

## 5.3 Participant Types That Satisfy Activation

Any supported Event Participant identity variant may satisfy the minimum participant requirement.

The initial model anticipates:

```text
roster_student
actor
descriptive_person
unknown_person
```

The exact participant schemas will be defined in the next section.

### Roster Student

```json
{
  "subject": {
    "kind": "roster_student",
    "class_id": "english10_p2",
    "student_id": "1001"
  }
}
```

The roster student may belong to:

* the Event’s owning class;
* or another valid Core class in the same teacher workspace.

A cross-class student participant does not alter Event ownership.

### Actor

```json
{
  "subject": {
    "kind": "actor",
    "actor_id": "actr_01j9..."
  }
}
```

An Actor represents a recurring non-roster person recorded through Portia’s teacher-local Actor Directory.

### Descriptive Person

```json
{
  "subject": {
    "kind": "descriptive_person",
    "description_type": "outside_student",
    "display_label": "Student from another teacher's class"
  }
}
```

A descriptive person may be used when the person is known contextually but does not require or qualify for a reusable Actor identity.

### Unknown Person

```json
{
  "subject": {
    "kind": "unknown_person",
    "reason": "identity_not_known"
  }
}
```

An explicitly unresolved participant may satisfy activation when the Event genuinely involves a person whose identity cannot yet be established.

Portia must preserve the uncertainty rather than fabricating identity.

---

## 5.4 No Roster-Student Requirement

An active Event does not require a roster-student participant.

Portia may represent an Event involving only:

* one or more Actor participants;
* descriptive outside people;
* unidentified people;
* a family member and counselor;
* or another valid combination of non-roster participants.

The Event must still have one legitimate owning class and an honest connection to the teacher’s classroom practice.

For example, the teacher may document a class-related conference involving:

```text
parent Actor
counselor Actor
```

without claiming that either person is a roster student.

Such an Event will not appear in a student-specific history unless a roster-student participant is explicitly linked.

Portia must not infer a student relationship merely because:

* an Actor is known to be a parent;
* the Event belongs to a class;
* the summary mentions a student;
* or the instructional context refers to one student’s work.

---

## 5.5 Unresolved Participants

An Event Participant may remain unresolved after Event activation.

This is permitted when:

* the person’s identity is genuinely unknown;
* the source withheld the identity;
* available information is insufficient;
* or a descriptive representation is more honest than a durable identity claim.

An unresolved participant must be represented explicitly through a supported identity variant and reason.

It must not be represented through:

* a blank `student_id`;
* a fake Actor;
* a display name used as identity;
* a temporary roster record;
* or an identifier derived from the Event summary.

A later identity resolution must use an explicit reviewed operation.

Portia must preserve:

* the original unresolved participant record;
* the replacement or resolved identity;
* the relationship between them;
* the time of resolution;
* the local operator attribution;
* and the reason for the change.

The detailed participant-resolution lifecycle will be decided later.

---

## 5.6 Adding Participants

Participants may be added while an Event is:

```text
draft
active
closed
```

Adding a participant to a closed Event must be treated as a historical correction or amendment rather than ordinary Event development.

Every addition must:

* create a new opaque Event Participant ID;
* identify the parent Event;
* use one supported subject variant;
* preserve creation provenance;
* and pass duplicate-participant validation.

Adding a participant does not alter:

* Event ownership;
* Event occurrence;
* Event identity;
* or the identity of existing participants.

---

## 5.7 Correcting or Removing a Participant

Portia should not physically delete a participant record merely because it was linked incorrectly.

An incorrect participant should normally be:

* invalidated;
* superseded;
* resolved to another identity;
* or otherwise transitioned through the later participant-lifecycle contract.

The original record must remain historically inspectable.

While an Event is active, Portia must not permit an operation that leaves it with zero valid active participants.

To correct the final active participant, the teacher must either:

1. create or activate the correct participant relationship before invalidating the incorrect one; or
2. cancel or invalidate the Event itself.

For example:

```text
add corrected participant
→ validate corrected relationship
→ invalidate mistaken participant
```

is permitted.

This sequence is not permitted:

```text
invalidate only participant
→ leave active Event with no participant
```

A cancelled or invalidated Event may preserve only invalidated participant records because it is no longer presented as an active or completed representation of an occurrence.

---

## 5.8 Closed Events

Closing an Event does not remove or deactivate its participant relationships.

A closed Event must preserve the valid participants connected to the Event when it was closed.

Later participant corrections may still occur through:

* amendment;
* invalidation;
* identity resolution;
* or another provenance-preserving correction process.

A closed Event must not become participantless through ordinary editing.

If later review establishes that the Event should never have represented the recorded occurrence or people, the Event itself should be invalidated or superseded rather than stripped of all participant relationships while remaining closed.

---

## 5.9 Paper Quick Capture

A preallocated paper quick-capture Event may begin with no participants.

The paper may provide:

* roster bubbles;
* checkboxes;
* abbreviated roster references;
* handwriting space;
* or another compact selection method.

After scanning, Portia may propose one or more participant records.

Those proposals must remain unconfirmed until the teacher reviews:

* the selected class;
* the interpreted roster identity;
* any cross-class student reference;
* any descriptive or unknown participant;
* and any duplicate or ambiguous marks.

The teacher may:

```text
confirm a proposed participant
correct the participant
add another participant
discard a false interpretation
leave the Event as a draft
invalidate the unused draft
```

A returned page with no recognized participant must not activate the Event automatically.

A recognized roster mark must also not activate the Event automatically.

Teacher confirmation remains required.

---

## 5.10 Group and Whole-Class Events

The minimum participant requirement must not be bypassed through a fabricated student representing:

* a group;
* the whole class;
* several unidentified students;
* or an audience.

The initial participant variants do not yet establish a canonical `group` or `class_context` subject.

Until such a variant is explicitly accepted, Portia must not create:

```text
student_id = whole_class
student_id = group_1
actor_id = period_2_students
```

A teacher may represent individually identifiable people through separate Event Participant records.

An unidentified person may use an unresolved-person participant.

A genuine collective Event that cannot be represented honestly through the accepted participant types must remain unsupported or await a later group-participant decision.

The Event must not be activated with zero participants merely because the teacher considers the owning class to be the subject.

---

## 5.11 Derived Views

An Event with no roster-student participant may still appear in:

* the owning class’s Event list;
* Event-date views;
* Actor-related views;
* open-work queues;
* and other appropriate teacher-facing projections.

It must not appear in a student-specific history unless that student has an explicit roster-qualified Event Participant record.

An unresolved participant must not be indexed under a guessed student.

A descriptive person must not be indexed under an Actor unless an explicit resolution relationship exists.

Derived views must follow canonical participant records rather than Event-summary text.

---

## 5.12 Validation Requirements

Portia must enforce participant-count requirements through application-level lifecycle validation.

The Event JSON Schema cannot validate the contents of separate participant files merely from `work.json`.

Activation validation must therefore inspect the canonical Event Participant collection and confirm that at least one participant satisfies the active-participant contract.

Validation should distinguish:

```text
no participant records exist
participant records exist but are malformed
participant records exist but all are invalidated
participant records exist but identity review is pending
one or more valid active participants exist
```

Only the final condition satisfies activation.

A closed Event must similarly preserve at least one valid participant relationship unless the Event itself has been invalidated, cancelled, or superseded under an accepted lifecycle rule.

---

## 5.13 Minimum-Participant Invariants

1. Draft Events may contain zero participants.
2. Preallocated paper quick-capture Events may begin without participants.
3. Active Events require at least one valid active Event Participant.
4. Closed Events preserve at least one valid participant relationship.
5. Event Participants remain separate canonical records.
6. The owning class is not an Event Participant.
7. The local operator is not automatically an Event Participant.
8. A paper route is not an Event Participant.
9. Any supported participant identity variant may satisfy activation.
10. An active Event does not require a roster-student participant.
11. Non-roster-only Events remain permissible when they have a legitimate owning-class context.
12. Unresolved identity may be represented honestly without fabricated IDs.
13. Unresolved participants may remain active when their uncertainty is explicit.
14. Participant additions do not alter Event ownership.
15. Incorrect participants are preserved through invalidation, supersession, or resolution rather than silent deletion.
16. An active Event must not be left with zero valid participants.
17. Removing the final active participant requires adding a correction first or changing the Event lifecycle.
18. Closed Events do not lose participant relationships through ordinary editing.
19. A synthetic whole-class or group student is prohibited.
20. Student-specific views require explicit roster-qualified participant records.
21. Scan interpretation does not create a confirmed participant automatically.
22. Participant-count requirements are enforced through application validation across canonical files.

## 6. Event Participant Record and Subject Identity

### Decision

Every Event Participant uses one canonical record envelope and exactly one discriminated `subject` variant.

The participant record answers:

> Which person is connected to this Event?

The initial subject variants are:

```text
roster_student
actor
descriptive_person
unknown_person
```

Each variant preserves a different kind of identity claim:

* `roster_student` references a class-qualified Core student;
* `actor` references a recurring non-roster person in Portia’s teacher-local Actor Directory;
* `descriptive_person` records an Event-local person description without creating reusable identity;
* `unknown_person` records that a participant exists but cannot currently be identified.

The Event Participant record does not, by itself, determine:

* what the person did;
* what the person said;
* whether the person observed the Event;
* whether the person reported the Event;
* whether the person was responsible;
* whether the person received support;
* or whether a concern was substantiated.

Those meanings belong to later role, Account, Observation, Determination, Response, or Support records.

---

## 6.1 Canonical Location

Event Participant records are stored beneath the owning Event:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    event_participant/
      <participant_id>.json
```

For example:

```text
classes/english10_p2/modules/portia/work/evt_01j9.../
  records/
    event_participant/
      ep_01j9....json
```

The top-level `class_id` is the Event’s owning Core class.

It is not necessarily the roster class of a student participant.

The top-level `work_id` is the parent Event ID.

No separate `event_id` field is required because:

```text
work_id = event_id
```

The containing path and persisted identity must agree exactly.

Portia must reject mismatches rather than silently infer or repair them.

---

## 6.2 Required Record Envelope

Every Event Participant requires:

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

Conceptually:

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j9...",
  "participant_id": "ep_01j9...",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "english10_p2",
      "student_id": "1001"
    },
    "display_snapshot": {
      "display_name": "Jordan Lee"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:22:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  },
  "updated_at": "2026-09-18T09:22:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

The example illustrates the accepted conceptual shape.

The normative JSON Schema will define exact property constraints.

---

## 6.3 Record Identity Fields

### `schema_version`

The initial value is:

```text
1
```

It is stored as a string.

Unsupported future versions must be reported explicitly.

### `record_type`

The required value is:

```text
event_participant
```

### `module_id`

The required value is:

```text
portia
```

### `class_id`

`class_id` identifies the parent Event’s owning Core class.

It must match:

* the Event root;
* the containing class path;
* and the Event’s canonical work root.

It must not be replaced with the participant’s roster class.

### `work_id`

`work_id` identifies the parent Event.

It must:

* begin with the accepted Event prefix;
* match the containing work directory;
* and resolve to a valid Portia Event.

### `participant_id`

`participant_id` is the Event Participant’s durable opaque identity.

It must:

* begin with the diagnostic prefix `ep_`;
* satisfy Core identifier-safety rules;
* contain no name or sensitive meaning;
* remain stable through normal lifecycle transitions;
* and match the containing filename.

The `ep_` prefix assists diagnosis.

Portia must still validate `record_type` explicitly rather than infer record kind solely from the prefix.

---

## 6.4 Discriminated Subject

The `subject` object is a discriminated union.

The required field:

```text
kind
```

selects exactly one supported subject structure.

Conceptually:

```text
subject
  oneOf:
    roster-student subject
    Actor subject
    descriptive-person subject
    unknown-person subject
```

Each branch must:

* require its own identity fields;
* reject fields belonging to other variants;
* and prevent contradictory identity claims.

For example, this is invalid:

```json
{
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "english10_p2",
      "student_id": "1001"
    },
    "actor_id": "actr_01j9..."
  }
}
```

Portia must not choose one identity and ignore the other.

---

## 6.5 Roster-Student Subject

Use `roster_student` when the participant is represented by a valid Core student reference.

```json
{
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "english10_p2",
      "student_id": "1001"
    },
    "display_snapshot": {
      "display_name": "Jordan Lee"
    }
  }
}
```

### Required Fields

```text
kind
student_ref
display_snapshot
```

Within `student_ref`:

```text
class_id
student_id
```

Within `display_snapshot`:

```text
display_name
```

### Rules

1. `kind` must equal `roster_student`.
2. `student_ref.class_id` and `student_ref.student_id` together form the canonical student reference.
3. A bare `student_id` is insufficient.
4. The referenced class must exist in the teacher workspace.
5. The referenced student must exist within that Core roster.
6. `display_snapshot` is required for historical readability.
7. The snapshot is nonauthoritative.
8. Core roster data remains authoritative for current identity.
9. A changed roster display name does not rewrite the historical participant snapshot automatically.
10. Snapshot correction requires recorded provenance.

Portia must not use:

* display name;
* email address;
* local nickname;
* seat number;
* or paper roster position

as the canonical student identity.

---

## 6.6 Cross-Class Roster Students

A roster-student participant may belong to a different class from the Event’s owning class.

For example:

```json
{
  "class_id": "english10_p2",
  "work_id": "evt_01j9...",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "english10_p4",
      "student_id": "2047"
    },
    "display_snapshot": {
      "display_name": "Taylor Morgan"
    }
  }
}
```

In this example:

```text
english10_p2
```

is the Event’s owning class.

```text
english10_p4 + 2047
```

is the participant’s canonical roster-qualified student identity.

The cross-class participant does not:

* change Event ownership;
* create a duplicate Event beneath the participant’s class;
* or create a cross-roster merged student identity.

Derived student views may locate the Event through the complete participant reference.

---

## 6.7 Display Snapshots

A roster-student or Actor subject requires a nonauthoritative `display_snapshot`.

Conceptually:

```json
{
  "display_snapshot": {
    "display_name": "Jordan Lee"
  }
}
```

The snapshot exists so historical records remain understandable when:

* a roster is unavailable;
* a person’s current display name changes;
* the Event is exported;
* or the source directory is later archived.

A snapshot:

* is not canonical identity;
* must not be used to merge records;
* must not override the referenced source;
* and must not be treated as proof that two references identify the same person.

The initial schema should require only:

```text
display_name
```

Additional snapshot fields should not be added without a clear historical or display need.

Portia should avoid copying unnecessary personal data into participant records.

---

## 6.8 Actor Subject

Use `actor` for a recurring non-roster person represented in Portia’s workspace-scoped Actor Directory.

```json
{
  "subject": {
    "kind": "actor",
    "actor_id": "actr_01j9...",
    "display_snapshot": {
      "display_name": "Ms. Rivera"
    }
  }
}
```

### Required Fields

```text
kind
actor_id
display_snapshot
```

### Rules

1. `kind` must equal `actor`.
2. `actor_id` must reference an existing Portia Actor record.
3. The Actor belongs to the teacher-local workspace rather than one class roster.
4. The Actor reference may be reused across several Events.
5. `display_snapshot` is required and nonauthoritative.
6. An Actor reference does not create an institutional directory identity.
7. Portia must not infer an Actor relationship from a matching name.
8. A descriptive person must not be promoted automatically into an Actor.

The Actor lifecycle and Actor schema remain governed by the separate identity architecture and later Actor work.

---

## 6.9 Descriptive-Person Subject

Use `descriptive_person` when the person is known sufficiently for Event-local description but should not receive a reusable identity.

```json
{
  "subject": {
    "kind": "descriptive_person",
    "description_type": "outside_student",
    "display_label": "Student from another teacher's class"
  }
}
```

The initial description types are:

```text
outside_student
family_member
school_staff
visitor
community_member
other
```

### Required Fields

```text
kind
description_type
display_label
```

### Optional Fields

```text
detail
```

### Rules

1. `kind` must equal `descriptive_person`.
2. `description_type` must use the controlled vocabulary.
3. `display_label` must be meaningful within the Event.
4. The description remains local to the Event.
5. It must not be used as durable cross-Event identity.
6. Similar labels must not be merged automatically.
7. Portia must not create an Actor automatically.
8. `other` requires a meaningful `detail` or sufficiently explicit `display_label`.

Examples include:

```json
{
  "subject": {
    "kind": "descriptive_person",
    "description_type": "family_member",
    "display_label": "Student's aunt"
  }
}
```

```json
{
  "subject": {
    "kind": "descriptive_person",
    "description_type": "school_staff",
    "display_label": "Substitute teacher"
  }
}
```

A known name may appear in `display_label` when appropriate.

The label still does not become durable identity.

---

## 6.10 Unknown-Person Subject

Use `unknown_person` when a person participated in or was connected to the Event but cannot currently be identified adequately.

```json
{
  "subject": {
    "kind": "unknown_person",
    "reason": "identity_not_known",
    "description": "Student wearing a blue team jacket"
  }
}
```

The initial reason values are:

```text
identity_not_known
identity_not_reported
identity_withheld
ambiguous_source
ambiguous_paper_mark
legacy_import
```

### Required Fields

```text
kind
reason
```

### Optional Field

```text
description
```

### Rules

1. `kind` must equal `unknown_person`.
2. `reason` must use the controlled vocabulary.
3. No student reference is permitted.
4. No Actor ID is permitted.
5. `description` may preserve useful nonidentity context.
6. Description must not be treated as a durable identifier.
7. Portia must not guess identity from similarity.
8. A later identity resolution must preserve the original unresolved record.

Representative meanings include:

| Reason                  | Meaning                                                        |
| ----------------------- | -------------------------------------------------------------- |
| `identity_not_known`    | The identity could not be determined                           |
| `identity_not_reported` | The source did not provide identity                            |
| `identity_withheld`     | Identity was intentionally withheld or not recorded            |
| `ambiguous_source`      | Available sources do not identify one person reliably          |
| `ambiguous_paper_mark`  | A paper selection or mark could not be interpreted confidently |
| `legacy_import`         | Imported data lacked a reliable identity reference             |

An unknown person is an explicit representation of uncertainty.

It is not an empty placeholder.

---

## 6.11 Participant Status

The initial Event Participant status values are:

```text
proposed
active
invalidated
superseded
```

### `proposed`

The participant relationship has been suggested or entered but has not yet been accepted as canonical.

Typical uses include:

* interpreted paper roster marks;
* handwriting recognition;
* imported participant suggestions;
* ambiguous identity matching;
* and incomplete teacher review.

A proposed participant does not satisfy Event activation requirements.

### `active`

The participant relationship has been reviewed and is currently accepted as valid.

Only active participant records satisfy the minimum active-Event participant requirement.

### `invalidated`

The record should not be treated as a valid participant relationship.

Possible reasons include:

* incorrect person selected;
* false paper interpretation;
* duplicate record;
* participant did not belong to the Event;
* or imported data was wrong.

Invalidation preserves the original record and provenance.

### `superseded`

Another participant record now represents the corrected or resolved relationship.

For example:

```text
unknown person
→ later resolved to roster student
```

The unknown-person record may become `superseded`, while the new roster-student record becomes `active`.

The exact status-transition rules and correction-link fields will be defined in the participant-lifecycle section.

---

## 6.12 Creation Source

Every Event Participant requires its own `creation_source`.

The participant source must not be inherited implicitly from the Event because a participant may be added later through a different workflow.

The initial source types are:

```text
digital_entry
returned_paper
import
```

### Digital Entry

```json
{
  "creation_source": {
    "type": "digital_entry"
  }
}
```

### Returned Paper

```json
{
  "creation_source": {
    "type": "returned_paper",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  }
}
```

### Import

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record"
  }
}
```

A participant originating through paper or uncertain import should ordinarily begin with:

```text
status = proposed
```

Teacher confirmation is required before it becomes active.

The Event and Participant may therefore have different creation sources.

For example:

```text
Event created through returned paper
second participant added later through digital entry
```

---

## 6.13 Creation and Update Provenance

Every Event Participant requires:

```text
created_at
created_by
updated_at
updated_by
```

The timestamp and local-attribution semantics follow the Event-root provenance contract.

At creation:

```text
created_at = updated_at
```

Later changes update:

```text
updated_at
updated_by
```

without rewriting:

```text
created_at
created_by
```

Local operator attribution does not establish:

* authentication;
* institutional authorization;
* authorship of an Account;
* observation of the Event;
* or participation in the Event.

---

## 6.14 Duplicate Durable Subjects

Within one Event, Portia should allow no more than one active participant record for the same durable subject.

### Roster-Student Duplicate Key

```text
student_ref.class_id
+
student_ref.student_id
```

Two active participant records with the same complete student reference are duplicates.

### Actor Duplicate Key

```text
actor_id
```

Two active participant records with the same Actor ID are duplicates.

Portia may preserve invalidated or superseded duplicates for history.

Only one should remain active.

---

## 6.15 Descriptive and Unknown Duplicate Handling

Portia must not automatically merge descriptive or unknown participants based only on similar text.

For example:

```text
Student from another class
```

may refer to:

* the same person entered twice;
* two different people;
* or an intentionally general description.

Likewise:

```text
Student wearing a blue jacket
```

is not a durable identity key.

Possible duplicates involving descriptive or unknown subjects require teacher review.

Portia may warn about similarity but must not:

* merge records automatically;
* infer identity;
* assign an Actor;
* or assign a roster student.

---

## 6.16 Paper Quick Capture

A paper quick-capture page may propose participant records through:

* roster bubbles;
* checkboxes;
* abbreviated roster codes;
* handwritten names;
* handwritten descriptions;
* or other compact marks.

After scanning, each interpreted person must become either:

```text
a proposed Event Participant
or
an unresolved review item
```

Portia must not treat a recognized mark as a confirmed participant automatically.

The teacher must be able to:

* confirm the proposed subject;
* choose another roster student;
* select a cross-class student;
* select or create an Actor through an explicit workflow;
* change the subject to descriptive person;
* change the subject to unknown person;
* or discard the interpretation.

An ambiguous paper mark may be represented temporarily as:

```json
{
  "status": "proposed",
  "subject": {
    "kind": "unknown_person",
    "reason": "ambiguous_paper_mark"
  }
}
```

That proposed record does not satisfy Event activation until reviewed and changed to `active`.

---

## 6.17 Identity Resolution

A descriptive or unknown person may later be resolved to a roster student or Actor.

Resolution must not mutate the original subject into a different identity variant without history.

The expected pattern is:

```text
preserve original participant
→ create corrected participant
→ link correction or resolution
→ activate corrected participant
→ supersede original participant
```

For example:

```text
ep_original:
unknown_person
status = superseded

ep_corrected:
roster_student
status = active
```

The later lifecycle section must define the exact fields used to connect the records, such as:

```text
superseded_by
resolves
replacement_reason
```

Portia must preserve:

* the original uncertainty;
* the later identity claim;
* when the resolution occurred;
* who recorded it locally;
* and why the change was made.

---

## 6.18 Identity Is Separate from Role

The Event Participant record establishes identity connection only.

It must not embed unstructured role assumptions such as:

```text
offender
victim
witness
reporter
responsible_student
problem_student
```

A later role model should determine how a person is connected to the Event.

That role model must distinguish at least among concepts such as:

* occurrence involvement;
* source or reporting relationship;
* observation relationship;
* response or support relationship;
* and later workflow responsibility.

Separating identity from role prevents one participant file from becoming an unsupported judgment about conduct or responsibility.

---

## 6.19 Derived Views

Participant-derived views must use canonical subject identity.

### Student Views

A roster-student Event Participant may place the Event in the referenced student’s derived history.

The complete student reference must be used:

```text
class_id + student_id
```

### Actor Views

An Actor participant may place the Event in an Actor-derived view.

### Descriptive-Person Views

A descriptive person may appear only within Event-local or text-search views unless later resolved explicitly.

### Unknown-Person Views

An unknown participant may appear in unresolved-identity queues.

Portia must not place descriptive or unknown participants into student or Actor histories through name matching.

---

## 6.20 Schema Requirements

The Event Participant JSON Schema should enforce:

### Envelope

* all required envelope fields;
* constant `record_type`;
* constant `module_id`;
* valid identifier patterns;
* timezone-aware provenance timestamps;
* supported participant statuses;
* supported creation-source variants;
* and rejection of unknown top-level properties.

### Subject

The `subject` object should use `oneOf` with four mutually exclusive branches:

```text
roster_student
actor
descriptive_person
unknown_person
```

Each branch should:

* require a constant `kind`;
* require its identity fields;
* prohibit fields belonging to other kinds;
* reject unknown properties;
* and enforce meaningful nonempty text where required.

### Roster Student

The schema should require:

```text
student_ref.class_id
student_ref.student_id
display_snapshot.display_name
```

### Actor

The schema should require:

```text
actor_id
display_snapshot.display_name
```

### Descriptive Person

The schema should require:

```text
description_type
display_label
```

and conditionally require meaningful clarification for `other`.

### Unknown Person

The schema should require:

```text
reason
```

and prohibit durable identity fields.

Application-level validation must additionally confirm:

* the parent Event exists;
* top-level class and work identity match the path;
* a referenced roster student exists;
* an Actor exists;
* duplicate durable active subjects do not exist;
* proposed participants do not satisfy Event activation;
* and identity-resolution operations preserve history.

---

## 6.21 Event Participant Identity Invariants

1. Every Event Participant uses one canonical record envelope.
2. Every Event Participant contains exactly one subject variant.
3. `participant_id` is a durable opaque ID.
4. The participant path and persisted parent identity must agree.
5. Top-level `class_id` identifies the Event’s owning class.
6. A roster student uses a complete `class_id + student_id` reference.
7. A roster student’s class may differ from the Event’s owning class.
8. Cross-class participation does not alter Event ownership.
9. Display snapshots are required for roster students and Actors.
10. Display snapshots are nonauthoritative.
11. Actors use workspace-scoped Portia Actor IDs.
12. Actor references do not create institutional identity.
13. Descriptive people remain Event-local.
14. Descriptive labels are not durable identity.
15. Unknown people preserve explicit uncertainty.
16. Unknown-person descriptions must not be treated as identity.
17. Paper and import interpretations may begin as proposed participants.
18. Only active participant records satisfy Event activation.
19. Participant creation source is recorded independently from Event creation source.
20. Duplicate active roster students are identified by complete student reference.
21. Duplicate active Actors are identified by Actor ID.
22. Descriptive and unknown participants are not merged automatically.
23. Identity resolution preserves the original participant record.
24. Identity is separate from Event role.
25. Student and Actor views follow canonical references rather than display-name matching.
26. Schema validation enforces structural subject exclusivity.
27. Application validation enforces reference existence, duplicate rules, and lifecycle semantics.

## 7. Event Participant Role Assignments

### Decision

Event Participant identity and Event-level role remain separate canonical records.

The Event Participant record answers:

> Who is connected to this Event?

An Event Participant Role record answers:

> In what neutral way is this participant connected to the bounded occurrence?

A participant may have:

```text
zero, one, or several role assignments
```

No role assignment is required for Event activation.

Portia must preserve an honestly identified participant with no assigned role rather than requiring the teacher to select a role that is unsupported, premature, or unclear.

The canonical Event Participant record must not contain:

```text
role
roles
participant_roles
```

as authoritative embedded fields.

---

## 7.1 Separate Canonical Records

Role assignments are stored separately from Event Participant identity.

Conceptually:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    event_participant/
      ep_<participant_id>.json
    event_participant_role/
      epr_<role_id>.json
```

The relationship is:

```text
Event
└── Event Participant
    └── zero or more Event Participant Role records
```

Separating the records permits each role assignment to have independent:

* identity;
* lifecycle;
* creation source;
* creation and update attribution;
* evidentiary or documentary basis;
* correction history;
* and supersession relationships.

A Role’s creation source belongs to that Role record.

It must not be inherited implicitly from:

* the Event;
* the Event Participant;
* another Role;
* or the source record named in `basis`.

Adding, correcting, confirming, invalidating, or superseding a Role must not require rewriting the participant’s canonical subject identity or creation provenance.

---

## 7.2 Scope of the Initial Role Model

The initial role model represents only neutral relationships to the bounded Event occurrence.

It does not represent every relationship a person may have to Portia records.

Relationships established through other record types remain represented by those records.

For example:

| Relationship                                            | Canonical representation |
| ------------------------------------------------------- | ------------------------ |
| Person supplied a statement or report                   | Account                  |
| Person directly observed information                    | Observation              |
| Person received or performed a Response                 | Response                 |
| Person received or provided ongoing support             | Support Process          |
| Person participated in later review                     | Follow-Up                |
| A finding or decision concerns the person               | Determination            |
| Person is neutrally connected to the bounded occurrence | Event Participant Role   |

Portia must not duplicate those relationships automatically as generic Event-level roles.

---

## 7.3 Initial Event-Level Role Types

The initial neutral role types are:

```text
directly_involved
present
reported_involved
contextual
```

These values describe connection to the occurrence.

They do not establish:

* blame;
* fault;
* misconduct;
* harm;
* credibility;
* intent;
* responsibility;
* or whether a concern was substantiated.

---

## 7.4 Directly Involved

Use:

```text
directly_involved
```

when the person participated directly in the bounded occurrence.

Examples may include:

* taking part in an interaction;
* being one of the people in a disagreement;
* requesting assistance or a break;
* participating in a positive classroom exchange;
* or otherwise acting within the occurrence itself.

This role does not indicate whether the person:

* initiated the occurrence;
* acted appropriately;
* violated a rule;
* caused harm;
* or bears responsibility.

Example:

```json
{
  "role_type": "directly_involved"
}
```

---

## 7.5 Present

Use:

```text
present
```

when the person was present within the Event context but direct involvement is not asserted.

Presence may be relevant because the person:

* occupied the same immediate space;
* was part of the observed group;
* may later provide an Account;
* or helps define the occurrence context.

Presence alone must not imply:

* observation of every action;
* knowledge of what happened;
* agreement with an Account;
* or direct involvement.

A person may be present without becoming an Account source or Observation source.

---

## 7.6 Reported Involved

Use:

```text
reported_involved
```

when one or more attributed sources describe the person as involved, but Portia is not presenting that relationship as independently established.

This role preserves the distinction between:

```text
a reported relationship
```

and:

```text
a relationship accepted as directly established
```

The role must remain visibly qualified as reported.

It must not be displayed merely as:

```text
Involved
```

when the canonical assignment is:

```text
Reported involved
```

### Proposal Requirement

A proposed `reported_involved` Role must contain at least one source-oriented basis entry.

The initial source-oriented proposal basis kinds are:

```text
account_ref
paper_capture
import_source
```

For example, a paper-derived Role may initially contain only its required matching paper basis:

```json
{
  "status": "proposed",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    }
  ]
}
```

Likewise, an imported proposal may preserve an `import_source` basis while attribution is being reviewed and converted into the canonical Account model.

A source-oriented paper or import basis preserves the proposed assertion’s origin and review context.

It does not, by itself, satisfy the attribution requirement for an active Role.

### Activation Requirement

Before any `reported_involved` Role may become active, its basis must contain at least one:

```text
account_ref
```

that resolves to a same-Event attributed Account.

This requirement applies regardless of whether the Role originated through:

```text
digital_entry
paper_capture
import
```

For example:

```json
{
  "status": "active",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "basis": [
    {
      "kind": "account_ref",
      "record_id": "acct_01j9..."
    }
  ]
}
```

A paper-derived active Role additionally retains its matching paper basis:

```json
{
  "status": "active",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    },
    {
      "kind": "account_ref",
      "record_id": "acct_01j9..."
    }
  ]
}
```

The Account preserves:

* who supplied the report;
* what was reported;
* and the attribution required to make the qualified relationship meaningful.

A paper artifact, import-source entry, free-text note, or teacher confirmation does not substitute for the canonical attributed Account.

### Lifecycle Treatment

A proposed `reported_involved` Role may remain proposed with a valid source-oriented basis but no Account reference.

Activation must fail until a valid same-Event attributed Account is referenced.

A superseded `reported_involved` Role must retain the Account basis that made activation valid.

An invalidated proposal may legitimately lack an Account when it was rejected before activation.

If a `reported_involved` Role had previously been active, later invalidation must preserve its historical Account reference.

Removing or replacing the Account basis of an active `reported_involved` Role is a material correction and requires the accepted successor-and-supersession workflow.

### Account Creation During Review

Digital-entry, paper-review, and import-review workflows may create or select an attributed Account without requiring the teacher to enter the same information twice.

For captured or imported source material, Portia may prefill the Account for teacher review.

The Account must still be:

* a separate canonical record;
* stored beneath the same Event;
* attributed under the Account domain contract;
* reviewed as required by its own lifecycle;
* and referenced from the Role through `account_ref`.

The Role must not copy the Account’s narrative, attribution, or credibility information into top-level fields.

---

## 7.7 Contextual

Use:

```text
contextual
```

when the person has a legitimate connection to the Event context but none of the more specific initial Event-level roles applies.

Examples may include:

* a family member participating in a class-related conference;
* a staff member present because of the Event context;
* a person whose relationship matters to understanding the occurrence;
* or another participant connected without being asserted as directly involved or present during the occurrence itself.

`contextual` should be used sparingly.

### Detail Requirement

A proposed `contextual` Role may temporarily omit `detail` while captured information is incomplete or awaiting teacher review.

For example:

```json
{
  "status": "proposed",
  "role_type": "contextual"
}
```

Before a `contextual` Role may become active, it must contain a concise, neutral, nonempty explanation.

For example:

```json
{
  "status": "active",
  "role_type": "contextual",
  "detail": "Participated in the immediate class-related conference."
}
```

The explanation exists because `contextual` is less specific than the other initial role types. An active unexplained `contextual` Role would function as an ambiguous catch-all rather than a meaningful Event-local relationship.

The required detail should answer:

> What legitimate Event-context relationship makes this person a participant?

It should remain concise.

The detail must not become:

* an Account;
* an allegation;
* a finding;
* a credibility judgment;
* a responsibility label;
* or a narrative of the Event.

Top-level Role `detail` is reserved exclusively for:

```text
role_type = contextual
```

The following role types must not contain top-level `detail`:

```text
directly_involved
present
reported_involved
```

Clarifying facts for those roles belong in the canonical record type designed to preserve them, such as:

* an Account;
* an Observation;
* the Event summary;
* or a structured basis reference.

Nested:

```text
supersedes[].detail
```

is a separate replacement-explanation field and is not governed by the top-level contextual-detail restriction.

### Lifecycle Treatment

A proposed `contextual` Role with missing detail must remain proposed.

Activation validation must fail until valid detail is supplied.

A `contextual` Role created directly as active through reviewed digital entry must contain valid detail at creation.

A superseded `contextual` Role must retain the activation-complete detail that made the earlier Role understandable while active.

An invalidated proposed `contextual` Role may lack detail when it was rejected or abandoned before activation.

If a `contextual` Role had previously been active, later invalidation must not erase its historical detail.

Removing or substantively replacing detail on an active `contextual` Role is a material correction and requires the accepted successor-and-supersession workflow.

---

## 7.8 Semantic Unit and Cardinality

One Event Participant Role record represents one Event-local assertion that one existing Event Participant holds one role type within one Event.

Each Role record therefore references exactly:

```text
one Event through work_id
one Event Participant through participant_id
one role type through role_type
```

A Role record does not represent:

* every role held by one participant;
* one role shared by several participants;
* participant identity;
* a participant group;
* an Event narrative;
* or a formal finding, Determination, or disciplinary conclusion.

A participant with several applicable roles receives one separate canonical Role record for each role assignment.

For example, a participant who was both present and directly involved is represented through two records:

```text
epr_<present-role-id>.json
epr_<direct-involvement-role-id>.json
```

Conceptually:

```text
one Event
  → zero or more Event Participants
    → zero or more Event Participant Role records
```

No Role record is required for:

* Event activation;
* Event closure;
* Event Participant activation;
* or preservation of an Event Participant relationship.

Portia must preserve an honestly identified participant with no assigned role when the participant’s connection is unclear, paper capture identified a person but not a role, imported data lacks reliable role information, or assigning a role would require unsupported inference.

### Independent Role Assertions

Each role assignment has its own:

* `role_id`;
* status;
* role type;
* required structured `creation_source`;
* a conditionally required collection of basis entries;
* creation and update attribution;
* correction history;
* invalidation history;
* and supersession relationships.

`basis` is optional for many digitally entered or imported Roles.

It is required when:

* `role_type = reported_involved`; or
* `creation_source.type = paper_capture`.

A paper-derived Role must include a matching paper basis even when another basis entry also supports the assertion.

One role may therefore be proposed, confirmed, corrected, invalidated, or superseded without changing another role held by the same participant.

For example, an active `present` role may remain unchanged while a proposed `reported_involved` role is invalidated.

Similarly, a later `directly_involved` role does not silently overwrite an earlier `reported_involved` role. Portia must preserve the lifecycle and history of both assertions.

### Prohibited Aggregate Shapes

A Role record must not contain an authoritative collection of role types:

```json
{
  "participant_id": "ep_example",
  "roles": [
    "present",
    "directly_involved"
  ]
}
```

A Role record must not assign one role to several participants:

```json
{
  "role_type": "present",
  "participant_ids": [
    "ep_example_1",
    "ep_example_2"
  ]
}
```

A Role record must not embed participant identity through fields such as:

```text
subject
student_ref
student_id
actor_id
display_snapshot
descriptive_person
unknown_person
```

It must not embed the Event or its participant collection through fields such as:

```text
event
participants
event_participants
```

Participant identity remains canonical in the referenced Event Participant record. Event context remains canonical in the Event root and its other child records.

### Duplicate and Compatible Active Roles

Within one Event, Portia must prevent more than one active Role record with the same role type for the same participant.

The effective active-role uniqueness key is:

```text
work_id + participant_id + role_type
```

Distinct role types may coexist only when the accepted compatibility matrix permits the combination.

The initial compatible active combinations are:

```text
present + directly_involved
present + reported_involved
present + contextual
```

The initial incompatible active combinations are:

```text
directly_involved + reported_involved
directly_involved + contextual
reported_involved + contextual
```

`present` may accompany one other initial role because presence is a separate neutral assertion about the person’s physical or contextual presence during the Event.

The other three roles are mutually exclusive as current descriptions of how the person is connected to the occurrence:

* `directly_involved` states direct participation;
* `reported_involved` preserves a qualified reported relationship;
* `contextual` applies when neither involvement role adequately describes the connection.

A participant’s valid current active-role set is therefore limited to:

```text
no active roles
one active role
present plus one other active role
```

Application validation must detect both duplicate and incompatible active Role records.

JSON Schema cannot enforce either rule across separate files.

Proposed, invalidated, and superseded records may repeat or conflict with current active roles when necessary for review, correction, and preserved history. They do not become current until activation validation succeeds.

### Cardinality Invariants

1. Each Role record belongs to exactly one Event.
2. Each Role record references exactly one Event Participant.
3. The referenced participant must belong to the same Event.
4. Each Role record assigns exactly one role type.
5. Multiple roles require multiple Role records.
6. One Role record must not assign a role to several participants.
7. No role is required for Event or Event Participant validity.
8. Participant identity must not be duplicated in the Role record.
9. One active participant-role combination must not have duplicate active Role records.
10. Distinct active roles must satisfy the accepted compatibility matrix.
11. `present` may coexist with one of the other initial role types.
12. `directly_involved`, `reported_involved`, and `contextual` are mutually exclusive as current active roles.
13. Proposed and historical records may preserve otherwise incompatible assertions without making them current.
14. Correcting one role must not rewrite unrelated Role records.
15. Role assignments do not constitute formal findings or Determinations.

---

## 7.9 Recommended Role Record Envelope

A future canonical Event Participant Role record should contain its own record-level provenance.

The Role must not inherit provenance from its parent Event or Event Participant.

The required envelope is:

```text
schema_version
record_type
module_id
class_id
work_id
role_id
participant_id
status
role_type
creation_source
created_at
created_by
updated_at
updated_by
```

Depending on the Role and lifecycle state, it may also contain:

```text
basis
detail
supersedes
```

Top-level `detail` is permitted only when:

```text
role_type = contextual
```

A proposed `contextual` Role may omit `detail`. An active or superseded `contextual` Role requires nonempty `detail`.

An invalidated proposed `contextual` Role may omit `detail`; an invalidated Role that was previously active must retain its historical detail.

Top-level `detail` is prohibited for:

```text
directly_involved
present
reported_involved
```

Nested `supersedes[].detail` remains permitted under the supersession contract and is distinct from top-level contextual detail.

`supersedes` is stored only on a successor Role as the canonical forward replacement relationship.

A canonical `superseded_by` field is prohibited. Reverse successor views are derived from Role records that point forward through `supersedes`.

Replacement reasons belong inside each structured `supersedes` entry rather than in one top-level `replacement_reason` field.

Conceptually:

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j9...",
  "role_id": "epr_01j9...",
  "participant_id": "ep_01j9...",
  "status": "active",
  "role_type": "directly_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

This example represents an explicit, reviewed digital assignment created directly as `active`.

Its:

```text
creation_source.type = digital_entry
```

describes how this Role record entered Portia.

It does not claim that the Event or Event Participant was created digitally.

Direct active creation is permitted only under the reviewed-entry rules in Section 7.19. The presence of:

```text
creation_source.type = digital_entry
```

does not by itself authorize active status.

The exact JSON Schema for this record is not part of the currently required:

```text
event.schema.json
event-participant.schema.json
```

deliverables.

The Event Participant schema must nevertheless remain compatible with this design by excluding authoritative embedded roles.

A dedicated role schema should be introduced before role records are implemented.

---

## 7.10 Role Identity

`role_id` is the durable opaque identity of one role assignment.

It should:

* begin with the diagnostic prefix `epr_`;
* satisfy Core identifier-safety rules;
* contain no participant name or role meaning;
* remain stable through lifecycle transitions;
* and match the containing filename.

The prefix is diagnostic only.

Portia must validate:

```text
record_type = event_participant_role
```

rather than relying solely on the identifier prefix.

---

## 7.11 Parent References

Each role assignment must identify:

```text
class_id
work_id
participant_id
```

These values establish:

* the Event’s owning class;
* the parent Event;
* and the Event Participant receiving the role assignment.

Application validation must confirm that:

1. the Event exists;
2. the Event Participant exists;
3. the participant belongs to the referenced Event;
4. the role record is stored beneath the same Event work root;
5. and the top-level class and work references match the canonical path.

A role assignment must not point directly to:

* a Core student;
* an Actor;
* a descriptive person;
* or an unknown person.

It points to the Event Participant record that already preserves the appropriate subject identity.

---

## 7.12 Role Status and Lifecycle

The initial role-assignment lifecycle supports:

```text
proposed
active
invalidated
superseded
```

Status records the Role’s review and lifecycle state.

Status is not determined solely by:

```text
creation_source
```

The same creation-source type may produce either a proposed or active Role depending on whether the complete assertion has been explicitly reviewed and accepted.

### Initial Status Decision

A Role may be created directly as:

```text
active
```

when the teacher explicitly selects, reviews, and saves one unambiguous Role assertion through a digital interface.

Direct active creation requires that:

* the referenced Event Participant exists and is active;
* the owning Event is `draft` or `active`;
* the teacher deliberately selected or confirmed the role type;
* all conditionally required fields are complete;
* an active `contextual` Role contains concise nonempty `detail`;
* any supplied basis entries validate;
* an active `reported_involved` Role contains a same-Event attributed Account reference;
* no duplicate active participant-role assignment exists;
* the participant’s resulting active-role set satisfies Section 7.15;
* the Role is not merely an automated, imported, or paper-derived suggestion awaiting review;
* and creation provenance records the actual entry path and local operator.

A proposed Event Participant cannot own an active Role.

The Role may instead begin as:

```text
proposed
```

when review is incomplete, ambiguity remains, the referenced participant is not yet active, or the Role originated as a suggestion requiring confirmation.

Creation source and initial status answer different questions:

```text
creation_source:
How did this canonical Role record enter Portia?

status:
Has this Role assertion been accepted?
```

### Parent-State Requirements

Role activation depends directly on the accepted Event Participant relationship.

At the moment a Role becomes active:

```text
Event Participant status = active
Event status = draft or active
```

The Event does not need to be active yet.

This permits a teacher to review and finalize participants and Roles while assembling a draft Event.

An active Role beneath a draft Event is accepted relative to that draft Event, but it appears only in draft-review and preparation views.

It does not appear in ordinary current Event histories until the Event becomes active.

Event activation does not require any Role assignment.

After Role activation:

* Event closure does not change Role status;
* Event reopening does not change Role status;
* Event cancellation, invalidation, or supersession does not cascade-rewrite child Role statuses;
* but Roles beneath a cancelled, invalidated, or superseded Event are excluded from ordinary current views.

An active Role continuously requires an active Event Participant.

Participant invalidation or supersession must therefore resolve every dependent active Role through the coordinated rules in Section 7.16.

### `proposed`

The Role has been suggested or entered but has not yet been accepted as a current canonical Event-level relationship.

Roles ordinarily begin as proposed when they arise from:

* paper interpretation;
* automated extraction;
* imported data awaiting review;
* ambiguous participant or role matching;
* a participant relationship that is not yet active;
* incomplete digital entry;
* a `contextual` assignment whose required detail is not yet available;
* a `reported_involved` assignment whose attributed Account is not yet linked;
* or a material correction awaiting confirmation.

A creation source does not force proposed status forever.

After explicit teacher review, a valid proposed Role may transition:

```text
proposed → active
```

A proposed successor may contain structured `supersedes` references identifying the prior Role or Roles it is intended to replace.

Those references are prospective while the successor remains proposed.

They do not:

* transition a prior Role to `superseded`;
* remove a prior active Role from current views;
* make the proposed successor current;
* or establish that replacement has occurred.

A proposed successor that is abandoned or rejected becomes `invalidated`. Its intended prior Roles remain unchanged.

### `active`

The Role is currently accepted as a valid neutral Event-level relationship.

An active `contextual` Role must contain concise nonempty `detail`.

An active `reported_involved` Role must contain at least one same-Event attributed `account_ref`.

A Role may reach active status through either:

```text
direct reviewed creation as active
```

or:

```text
proposed → active
```

Direct active creation does not require a synthetic proposed state when the teacher has already explicitly reviewed and accepted the complete assertion before persistence.

For a Role created directly as active:

```text
created_at
```

records when the accepted canonical Role was created.

The Role’s own creation provenance and initial active status preserve that it entered Portia as an explicitly reviewed assignment.

Those facts do not depend on the Event or Event Participant creation source.

A fabricated lifecycle transition from a nonexistent proposed state must not be created.

An active Role may receive an additional corroborating basis entry in place only when the addition satisfies Section 7.13 and does not change:

* the participant;
* the role type;
* the Role’s substantive meaning;
* or the interpretation of any existing basis entry.

The addition must preserve append-only amendment history. It must not be presented as though the added basis existed when the Role was originally activated.

When a proposed successor containing `supersedes` references becomes active, the replacement becomes effective through one coordinated operation.

That operation must:

1. validate the successor;
2. validate every referenced prior Role;
3. validate the active Event Participant and eligible Event state;
4. transition the successor to `active`;
5. transition every effectively replaced prior Role to `superseded`;
6. append the required lifecycle and correction history;
7. and persist the resulting direct-load states atomically or through a recoverable staged-write process.

Portia must not expose a durable completed state in which the successor is active but an effectively replaced prior Role remains active.

A directly reviewed digital correction may create and activate a successor within one coordinated operation. The prior Role still becomes `superseded` only when the successor becomes active.

### `invalidated`

The Role assignment was incorrect, unsupported, duplicated, abandoned during review, or otherwise must not be treated as valid.

Invalidating a proposed successor before activation does not affect the status of any Role named in its prospective `supersedes` references.

Invalidating a Role that previously became active is a later lifecycle event. It does not rewrite the period during which the Role was accepted.

`invalidated` is terminal under ordinary workflows.

### `superseded`

A later Role became active and replaced or materially refined this Role through a completed supersession operation.

A prior Role must not become `superseded` merely because:

* a successor file was created;
* a proposed successor named it;
* teacher review began;
* or replacement validation was attempted.

The prior Role remains active until the successor activation operation completes successfully.

If activation fails before the coordinated operation commits, the durable recoverable state must remain:

```text
successor = proposed
prior Role or Roles = active
```

After successful completion, the durable state is:

```text
successor = active
prior Role or Roles = superseded
```

`superseded` is terminal under ordinary workflows.

### Allowed Transitions

The initial allowed transitions are:

| From | To | Meaning |
| --- | --- | --- |
| `proposed` | `active` | Reviewed and accepted |
| `proposed` | `invalidated` | Rejected without replacement |
| `proposed` | `superseded` | An active successor replaced the proposal |
| `active` | `invalidated` | Later rejected without replacement |
| `active` | `superseded` | An active successor replaced it |

Direct reviewed creation as `active` remains valid and does not imply a prior transition.

Every transition requires append-only lifecycle history containing at least:

```text
role_id
from_status
to_status
reason
changed_at
changed_by
```

The exact lifecycle-transition schema may be defined with the implementation deliverables.

### Prohibited Transitions and Terminal States

The following ordinary transitions are prohibited:

```text
active → proposed

invalidated → proposed
invalidated → active
invalidated → superseded

superseded → proposed
superseded → active
superseded → invalidated
```

A Role that entered accepted history must not return to an unreviewed state.

Invalidated and superseded Roles must not be silently restored or repurposed.

A mistaken terminal transition requires:

* an explicit append-only amendment;
* or a new Role record representing the corrected canonical assertion.

It must not use reactivation.

Role lifecycle changes never mutate the Event Participant’s canonical subject identity.

---

## 7.13 Basis

### Decision

A Role record may contain an optional `basis` array describing the separate sources, artifacts, or canonical records that support the one participant-role assertion.

When present, `basis` must contain one or more structured basis entries:

```json
{
  "basis": [
    {
      "kind": "account_ref",
      "record_id": "acct_01j9..."
    },
    {
      "kind": "account_ref",
      "record_id": "acct_01k0..."
    }
  ]
}
```

The array permits one Role assertion to preserve several supporting sources without creating duplicate active Role records for the same:

```text
work_id + participant_id + role_type
```

Array order has no semantic meaning.

The first basis entry is not automatically:

* primary;
* earlier;
* more credible;
* more authoritative;
* or more important than another entry.

Portia must not infer source agreement, evidentiary weight, or credibility from:

* array order;
* the number of basis entries;
* repeated reports;
* or the presence of several source kinds.

### Optionality

`basis` is optional for:

```text
directly_involved
present
contextual
```

A teacher may assign those neutral Event-level relationships directly during reviewed entry without creating a synthetic basis entry.

In that case, the Role record’s:

```text
creation_source
created_by
updated_by
lifecycle history
```

preserve how and by whom the canonical assignment was created or confirmed.

Those provenance fields do not themselves become assertion basis.

When `basis` is present, an empty array is invalid.

For:

```text
reported_involved
```

the Role record must contain at least one source-oriented basis entry even while proposed.

The initial source-oriented proposal basis kinds are:

```text
account_ref
paper_capture
import_source
```

Before any `reported_involved` Role becomes active, it must contain at least one same-Event attributed `account_ref`.

This activation rule is independent from `creation_source.type`.

A paper or import basis may preserve a proposal, but neither substitutes for the activation-required Account.

### Initial Basis Kinds

The initial basis-entry kinds are:

```text
account_ref
observation_ref
paper_capture
import_source
```

Each entry must validate as exactly one discriminated basis variant.

### Event Scope of Canonical Record References

`account_ref` and `observation_ref` basis entries are always Event-local.

They resolve within the Role record’s own:

```text
class_id + work_id
```

The persisted basis entry therefore contains only:

```text
kind
record_id
```

For example:

```json
{
  "kind": "account_ref",
  "record_id": "acct_01j9..."
}
```

must resolve to an Account stored beneath the same Event work root as the Role record.

Likewise:

```json
{
  "kind": "observation_ref",
  "record_id": "obs_01j9..."
}
```

must resolve to an Observation stored beneath that same Event.

An `account_ref` or `observation_ref` basis entry must not repeat or override Event scope through fields such as:

```text
class_id
work_id
module_id
event_id
```

Those fields would duplicate parent identity and could create conflicting authority about which Event owns the referenced record.

The initial Role model does not permit an Account or Observation from another Event to support an Event Participant Role directly.

Information from another occurrence must instead be represented through the appropriate cross-Event, pattern, Support Process, or later analytic relationship. It must not be imported into the current Event’s role basis in a way that blurs Event boundaries.

JSON Schema validates the compact reference shape.

Application validation must confirm that:

* the referenced record exists;
* the referenced record has the expected record type;
* the referenced record belongs to the Role’s owning Event;
* and the referenced record remains valid under its own lifecycle contract.

#### Account Reference

```json
{
  "kind": "account_ref",
  "record_id": "acct_01j9..."
}
```

An attributed Account belonging to the same Event supports the Role assertion.

For every `reported_involved` Role, at least one such Account reference is required before activation.

The referenced Account must contain valid attribution under the Account domain contract. An unattributed note, free-text summary, paper artifact, or import-source entry is not an Account substitute.

The Account remains the canonical source record. The Role record does not copy its content, attribution, credibility assessment, or Event ownership.

One Role may reference several same-Event Account records through several basis entries.

#### Observation Reference

```json
{
  "kind": "observation_ref",
  "record_id": "obs_01j9..."
}
```

An Observation belonging to the same Event supports the Role assertion.

The Observation remains canonical evidence. The Role record does not copy its content, observer attribution, or Event ownership.

An Observation reference may support `present` or `directly_involved`. It does not automatically make a Role a formal finding.

#### Paper Capture

```json
{
  "kind": "paper_capture",
  "route_id": "rt_0123456789abcdef0123456789abcdef",
  "page_record_id": "pg_01j9..."
}
```

A returned Portia paper artifact supplied or proposed the Role information.

For every Role whose creation source is:

```text
creation_source.type = paper_capture
```

the `basis` array is required and must contain at least one `paper_capture` entry whose:

```text
route_id
page_record_id
```

exactly match the corresponding fields in the Role’s `creation_source`.

For example:

```json
{
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    }
  ]
}
```

The duplication is intentional.

The two fields answer different questions:

```text
creation_source:
How did this Role record enter Portia?

matching paper basis:
Which returned artifact directly supports the Role assertion?
```

The matching requirement applies regardless of Role status.

A paper-derived Role that is:

```text
proposed
active
invalidated
superseded
```

must retain the matching basis entry.

Invalidating a mistaken paper interpretation does not erase which artifact produced and supported that interpretation.

A paper-derived Role may contain additional valid basis entries.

For example, it may later gain:

* an Account reference;
* an Observation reference;
* another supporting paper artifact;
* or an import-source reference where legitimately applicable.

Additional entries do not replace the required matching entry.

A second paper basis may reference another artifact only when that artifact independently supports the same Role assertion.

Structural and semantic duplicate rules still apply.

The matching paper basis does not indicate that:

* handwriting recognition was correct;
* mark interpretation was correct;
* the teacher confirmed the Role;
* an attributed Account exists;
* or the Role is active.

For a paper-derived `reported_involved` Role, the matching paper basis is sufficient for proposal but insufficient for activation.

As with every active `reported_involved` Role, activation additionally requires a same-Event attributed `account_ref`.

Those questions remain governed by status, lifecycle history, canonical Account records, and teacher review.

#### Import Source

```json
{
  "kind": "import_source",
  "source_label": "Legacy teacher record",
  "source_record_id": "row-184"
}
```

An imported source supplied the Role information.

`source_record_id` should be included when the imported source provides a stable row, object, or record reference.

The imported source remains external provenance. Portia does not treat it as verified merely because it was imported.

### Mixed Basis Kinds

One Role may contain several different basis kinds when they all support the same participant-role assertion.

For example:

```json
{
  "role_type": "reported_involved",
  "basis": [
    {
      "kind": "account_ref",
      "record_id": "acct_01j9..."
    },
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    }
  ]
}
```

The Role remains one assertion.

The basis array does not create:

* several Role assignments;
* a source hierarchy;
* a vote among sources;
* a credibility score;
* or a Determination.

### Direct Teacher Assignment Without Basis

A Role assigned directly by the teacher may omit `basis` when no other conditional basis rule applies.

This omission rule does not apply to a paper-derived Role or to `reported_involved`.

For example:

```json
{
  "role_type": "present",
  "creation_source": {
    "type": "digital_entry"
  }
}
```

The omitted basis does not mean that the Role lacks provenance.

It means only that no separate supporting source, artifact, or canonical record was attached to the assertion.

Portia must not manufacture a basis entry merely to distinguish direct teacher assignment from missing data.

Teacher-facing interfaces may communicate that the Role was directly assigned by using creation, update, and lifecycle provenance rather than a `teacher_entry` basis kind.

### Duplicate Basis Entries

A Role record must not contain structurally duplicate basis entries.

The JSON Schema should use:

```text
uniqueItems = true
```

where structurally identical array entries can be detected.

Application validation must additionally prevent semantic duplicates that use different but equivalent representations.

For example, Portia should not preserve two `account_ref` entries pointing to the same Account merely because their object-property order differed before serialization.

### Basis Corrections

Basis mutability depends on the Role lifecycle state.

#### Proposed Roles

A `proposed` Role may have its basis edited in place during review.

For a paper-derived Role, editing must preserve at least one paper basis entry that exactly matches the Role creation source.

The matching entry may not be removed while the record remains a paper-derived Role.

Any proposed `reported_involved` Role may gain an attributed same-Event Account during review.

It must not transition to active until that Account is referenced through `account_ref`.

The teacher may:

* add a basis entry;
* remove a basis entry;
* replace a basis entry;
* correct a referenced record;
* or omit `basis` when no separate supporting source should be attached.

Each change must update:

```text
updated_at
updated_by
```

Proposed-state editing is permitted because the Role has not yet been accepted as a current canonical relationship.

The Role’s immutable creation provenance must still be preserved.

#### Additive Support for Active Roles

An additional basis entry may be appended to an active Role in place only when all of the following are true:

1. the participant remains unchanged;
2. the role type remains unchanged;
3. the Role’s substantive meaning remains unchanged;
4. every existing basis entry remains valid and unchanged;
5. the new entry is genuinely additive rather than a replacement;
6. the new entry does not resolve, contradict, or recharacterize the earlier support;
7. the addition does not convert a reported relationship into a directly established relationship;
8. the resulting basis array contains no structural or semantic duplicate;
9. the current Role still satisfies every conditional basis requirement;
10. and append-only amendment history records when, why, and by whom the basis was added.

For example, a second same-Event Account may be added to an unchanged active `reported_involved` Role when it independently supplies another report of the same neutral relationship.

The current Role record may then contain both Account references.

Portia must preserve history showing that the second Account was attached later.

The added source must not be displayed as though it supported the Role at initial activation.

#### Changes Requiring Replacement

An active Role requires a successor Role and supersession when a basis change:

* removes an existing basis entry;
* replaces an existing basis entry;
* changes a referenced record;
* corrects a basis kind;
* recharacterizes what supports the Role;
* changes the Role’s substantive meaning;
* resolves a reported relationship into a different role type;
* introduces a contradiction requiring reinterpretation;
* or would make the prior Role’s stored support misleading.

The replacement pattern is:

```text
preserve prior active Role
→ create proposed successor with corrected basis and intended supersedes references
→ review and validate successor
→ activate successor and supersede prior Role or Roles in one coordinated operation
```

Creating the proposed successor does not alter the prior Role’s active status.

If the successor is invalidated or abandoned before activation, every prior Role remains unchanged.

The successor must receive a new `role_id` and own the canonical forward `supersedes` relationship through one or more structured prior-Role references.

The reason for replacing each prior Role is stored on that individual reference.

The prior Role’s basis remains unchanged as historical evidence of what supported that Role during its active period.

#### Basis Retraction

A source retraction does not authorize deletion of the corresponding basis entry from an active Role.

The matching paper basis of a paper-derived Role is also historical provenance of the assertion’s support path. It remains attached after invalidation or supersession.

For any `reported_involved` Role that was active, the activation-required Account reference remains historical after invalidation or supersession.

Portia must instead determine whether the Role should be:

* superseded by a corrected Role using the remaining valid basis;
* invalidated because the assertion is no longer supported;
* or replaced by a Role with a different type or meaning.

A `reported_involved` successor must still contain at least one source-oriented basis entry before it may become active.

#### Invalidated and Superseded Roles

The basis of an invalidated or superseded Role is historical and must not be edited through an ordinary workflow.

A later correction must create additional history rather than rewriting the terminal record.

#### Amendment-History Requirement

An in-place additive basis change to an active Role requires append-only amendment history capable of preserving at least:

```text
role_id
change_kind = basis_added
added_basis
changed_at
changed_by
reason
```

The exact shared amendment-record schema may be defined in a later issue.

Until Portia can preserve this history reliably, the safer implementation is to create a successor Role rather than perform an in-place active basis addition.

Portia must never silently rewrite an active Role’s basis in a way that makes later support appear to have existed at creation.

### Basis Invariants

1. `basis` is an optional array except where a conditional requirement applies.
2. When present, `basis` contains one or more entries.
3. Array order has no semantic meaning.
4. Each entry validates as exactly one supported basis kind.
5. One Role may have several basis entries.
6. Several basis entries do not create several Role assignments.
7. The number or order of entries does not establish credibility or evidentiary weight.
8. Every proposed `reported_involved` Role requires at least one source-oriented basis entry.
9. A paper-derived proposal may satisfy that proposal requirement with its matching paper basis.
10. An imported proposal may satisfy that proposal requirement with an import-source basis.
11. Every active `reported_involved` Role requires at least one same-Event attributed Account reference.
12. Paper and import basis entries do not substitute for the activation-required Account.
13. Teacher confirmation does not substitute for the activation-required Account.
14. Every paper-derived Role requires a `paper_capture` basis entry matching its creation-source route and page.
15. The matching requirement applies to proposed, active, invalidated, and superseded paper-derived Roles.
16. Additional basis entries do not replace the required matching paper entry.
17. Direct teacher assignment may omit `basis` only when no conditional basis requirement applies.
18. Creation, update, and lifecycle provenance do not become assertion basis.
19. No `teacher_entry` basis kind is defined.
20. Creation source and basis remain distinct even when they reference the same paper artifact.
21. `account_ref` and `observation_ref` resolve only within the Role’s owning Event.
22. Event-local record references contain `kind` and `record_id` without repeated Event identity.
23. Cross-Event Account and Observation basis references are prohibited.
24. Referenced Accounts and Observations remain canonical in their own records.
25. An Account used to activate `reported_involved` must be attributed under the Account contract.
26. Paper and import basis entries do not become authoritative merely through capture or import.
27. Structurally and semantically duplicate basis entries are prohibited.
28. Proposed Roles may have basis entries added, removed, or replaced during review, subject to conditional requirements.
29. A paper-derived Role must not lose its matching paper basis during review.
30. A proposed `reported_involved` Role may gain its activation-required Account during review.
31. Active Roles may receive only genuinely additive, non-meaning-changing basis entries in place.
32. Every in-place active basis addition requires append-only amendment history.
33. Removing or replacing an active Role’s basis requires a successor Role and supersession.
34. The matching paper basis of a paper-derived Role remains historical after invalidation or supersession.
35. The Account basis of every formerly active `reported_involved` Role remains historical after invalidation or supersession.
36. An invalidated never-active `reported_involved` proposal may lack an Account.
37. A source retraction does not delete history from an active or terminal Role.
38. Invalidated and superseded Role bases are not edited through ordinary workflows.
39. Basis corrections preserve provenance and correction history.
40. When amendment history cannot be preserved, active basis additions use successor Roles.

---

## 7.14 Independent Role Creation Source

### Decision

Every Event Participant Role requires its own structured:

```text
creation_source
```

The object records how that specific canonical Role assertion originally entered Portia.

It is independent from the creation source of:

* the parent Event;
* the referenced Event Participant;
* any sibling Role;
* any Account or Observation named in `basis`;
* and any prior Role named in `supersedes`.

Portia must not infer or copy a Role’s creation source merely from its parent records.

### Initial Creation-Source Types

The initial Role creation-source types are:

```text
digital_entry
paper_capture
import
```

The Role source uses the same shared discriminated creation-source vocabulary as other Portia canonical records.

#### Digital Entry

```json
{
  "creation_source": {
    "type": "digital_entry"
  }
}
```

Use `digital_entry` when the Role is created through Portia’s digital interface.

This remains true when:

* the Event was created through paper capture;
* the Event Participant was imported;
* or the Role is a digitally created successor to a paper- or import-derived Role.

For example:

```text
Event:
paper_capture / preallocated

Event Participant:
paper_capture / ingested

Role added later:
digital_entry
```

#### Paper Capture

```json
{
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  }
}
```

Use `paper_capture` when the Role originates through interpretation of a returned Portia-generated paper artifact.

For an Event Participant Role:

```text
creation_source.type = paper_capture
→ creation_source.stage = ingested
```

A Role must never use:

```text
stage = preallocated
```

No canonical Role assertion exists merely because:

* an Event was preallocated;
* a capture page was rendered;
* the page included blank role marks;
* or a participant placeholder existed before return.

The Role comes into existence only after returned-page processing produces a specific proposed or reviewed participant-role assertion.

The source preserves the route and page-record references associated with that returned artifact.

The Role must also contain a `paper_capture` basis entry with the same:

```text
route_id
page_record_id
```

This is not accidental duplication. Creation source records origin; basis records assertion support.

Teacher confirmation does not change:

```text
creation_source.type = paper_capture
creation_source.stage = ingested
```

A paper-derived proposed Role that later becomes active remains paper-ingested and retains the matching paper basis.

Invalidation or supersession also preserves that matching basis as historical support provenance.

A workflow that needs pre-render configuration for role marks must store that configuration in the page template, page record, or another appropriate generated-paper record. It must not create blank preallocated Role records.

#### Import

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": "import-batch-2026-09-01"
  }
}
```

Use `import` when the Role originates outside the ordinary Portia digital or generated-paper workflows.

`source_label` is required.

`external_reference` is optional when the import provides a meaningful external batch or source reference.

A teacher’s later digital review does not rewrite the Role as:

```text
digital_entry
```

The imported origin remains historical provenance.

### Parent and Child Sources May Differ

One Event context may legitimately contain records with several creation sources.

For example:

```text
Event:
digital_entry

Event Participant:
digital_entry

present Role:
paper_capture / ingested

directly_involved successor:
digital_entry
```

Likewise:

```text
Event:
import

Event Participant:
import

contextual Role added later:
digital_entry
```

These differences are expected.

They preserve how each canonical record actually entered Portia.

### Successor Roles Have Their Own Sources

A successor Role receives its own `creation_source`.

It does not inherit the source of the Role it replaces.

For example:

```text
prior Role:
paper_capture / ingested

corrected successor:
digital_entry
```

The `supersedes` relationship preserves the correction lineage.

The successor’s creation source preserves how the corrected canonical assertion entered Portia.

The two facts must not be collapsed.

### Creation Source, Attribution, Status, and Basis Are Distinct

These fields answer different questions:

```text
creation_source:
How did this Role record originally enter Portia?

created_by:
Which local operator or system process created the canonical record?

updated_by:
Which local operator or system process most recently changed it?

status:
Is the Role proposed, active, invalidated, or superseded?

basis:
Which separate sources, artifacts, or canonical records support the assertion?
```

For example:

```json
{
  "status": "proposed",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    }
  ],
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  }
}
```

means:

* the Role entered Portia through paper ingestion;
* the paper artifact also supports the assertion;
* and a system process created the proposed canonical Role.

The same artifact appears in both `creation_source` and `basis` for every paper-derived Role because the fields represent different relationships.

For that required entry, the route and page references must match exactly.

A digitally entered Role may also be based on a paper artifact, but matching is not automatically required merely because a paper basis is present.

A paper-derived Role may later gain an Account basis.

A directly teacher-assigned Role may omit `basis` while retaining complete creation and operator provenance, provided it is neither paper-derived nor otherwise subject to a conditional basis requirement.

### Immutability

The following Role creation facts are ordinarily immutable:

```text
creation_source
created_at
created_by
```

Review, confirmation, correction, basis addition, invalidation, and supersession must not rewrite the Role’s original creation source.

For example:

```text
before confirmation:
status = proposed
creation_source = paper_capture / ingested
created_by = system_process

after confirmation:
status = active
creation_source = paper_capture / ingested
updated_by = local_operator
```

If creation provenance itself was recorded incorrectly, the correction must use the accepted amendment or provenance-preserving correction mechanism rather than an ordinary silent edit.

### No Inherited or Derived Source

Portia must not determine a Role source through rules such as:

```text
Role source = Event source
Role source = Event Participant source
Role source = first basis kind
Role source = current editor
Role source = source of superseded Role
```

The workflow that creates the Role supplies the source explicitly and automatically.

Teachers must not be required to enter technical source fields manually.

### Creation-Source Invariants

1. Every Role records its own structured creation source.
2. Role creation source is independent from Event and Event Participant creation source.
3. Role creation source is independent from assertion basis.
4. Role creation source is independent from lifecycle status.
5. Role creation source is independent from later update attribution.
6. A successor Role receives its own creation source.
7. A paper-derived Role uses `stage = ingested`.
8. A Role must never use `stage = preallocated`.
9. Blank pre-render role marks do not create canonical Role records.
10. Every paper-derived Role contains a matching paper basis entry.
11. The creation-source and matching-basis route and page references are identical.
12. A matching paper basis permits a proposed paper-derived `reported_involved` Role but does not authorize activation.
13. Every active `reported_involved` Role requires a same-Event attributed Account regardless of creation source.
14. Paper-derived Roles remain paper-ingested after teacher confirmation.
15. Confirmation, invalidation, and supersession preserve the matching paper basis.
16. Every formerly active `reported_involved` Role preserves its Account basis.
17. Imported Roles remain imported after teacher review.
18. Parent and child records may legitimately have different creation sources.
19. Creation source is ordinarily immutable.
20. Technical source metadata is populated by the workflow rather than manually by the teacher.

---

## 7.15 Active-Role Compatibility

### Decision

Portia uses a strict compatibility matrix for active Event Participant Roles.

The matrix applies to all active Role records for one:

```text
class_id + work_id + participant_id
```

It does not prohibit proposed, invalidated, or superseded records from preserving earlier, competing, or not-yet-reviewed assertions.

### Compatibility Matrix

| Existing active role | Candidate active role | Result |
| --- | --- | --- |
| `present` | `directly_involved` | Allowed |
| `present` | `reported_involved` | Allowed |
| `present` | `contextual` | Allowed |
| `directly_involved` | `reported_involved` | Prohibited |
| `directly_involved` | `contextual` | Prohibited |
| `reported_involved` | `contextual` | Prohibited |
| Any role | Same role | Duplicate; prohibited |

The matrix is symmetric.

For example, the result for:

```text
directly_involved + reported_involved
```

is the same regardless of which Role was created first.

### Meaning of `present`

`present` is compatible with one other initial role because it asserts presence without by itself asserting the nature of involvement.

For example:

```text
present + directly_involved
```

may accurately record that the person was present throughout the Event context and also participated directly.

Likewise:

```text
present + reported_involved
```

may preserve that the person was present while direct involvement remains reported rather than established.

And:

```text
present + contextual
```

may preserve presence together with another legitimate contextual connection.

`present` must not be duplicated merely to represent several periods or perspectives within the same Event. Additional temporal or observational detail belongs in the appropriate Observation, Account, or Event-context record.

### Mutually Exclusive Current Roles

The following role types are mutually exclusive as current active assertions:

```text
directly_involved
reported_involved
contextual
```

#### `directly_involved` and `reported_involved`

These roles express alternative current levels of assertion.

When reviewed information changes the current relationship from:

```text
reported_involved
```

to:

```text
directly_involved
```

Portia must create or activate a successor and supersede the earlier Role rather than leave both active.

The earlier `reported_involved` Role remains preserved historically.

#### `directly_involved` and `contextual`

`contextual` is intended for a legitimate Event connection not adequately described by the more specific initial involvement roles.

Once `directly_involved` accurately describes the current relationship, a simultaneous active `contextual` Role would be redundant or contradictory.

#### `reported_involved` and `contextual`

When a source specifically reports involvement, the qualified `reported_involved` Role is the more precise current representation.

A simultaneous active `contextual` Role would blur the distinction between a reported involvement assertion and a nonspecific contextual relationship.

### Maximum Initial Active-Role Set

Under the initial vocabulary, one participant may have at most two active Role records:

```text
present
+
one of:
  directly_involved
  reported_involved
  contextual
```

A participant may also have:

```text
zero active roles
```

or:

```text
one active role
```

Portia must not require a second Role merely because one Role is present.

### Activation-Time Validation

Compatibility is evaluated whenever a Role is:

* created directly as active;
* transitioned from proposed to active;
* activated as a successor;
* or restored through any future lifecycle operation that would make it current.

The application must compute the participant’s intended post-operation active-role set.

For an ordinary activation, that set consists of:

```text
all currently active Roles
+
the candidate Role
```

For a coordinated successor activation, that set consists of:

```text
currently active Roles
− every prior Role that will become superseded in the same operation
+ the successor Role
```

This post-operation calculation permits a valid correction such as:

```text
reported_involved
→ directly_involved
```

without treating the prior Role as a permanent compatibility conflict.

The coordinated operation must still fail when another incompatible active Role would remain after the planned supersession transitions.

For example, activating `directly_involved` while an unrelated active `contextual` Role remains current is invalid unless that contextual Role is also legitimately replaced in the same coordinated operation.

### Proposed Roles

A proposed Role may temporarily conflict with an active Role while correction or review is underway.

For example:

```text
active reported_involved
proposed directly_involved successor
```

is valid during review.

The proposed Role does not appear in current-role views and does not alter the active Role.

Activation must fail unless the final coordinated state satisfies the compatibility matrix.

### Duplicate Detection

Portia must prevent more than one active Role with the same:

```text
participant_id + role_type
```

within the Event.

A successor may have the same role type as a prior Role when it corrects basis, detail, or another material property.

That successor becomes active only as the prior Role becomes superseded in the same coordinated operation.

Duplicate validation must therefore also use the intended post-operation active-role set.

### No Warning-Only Override

The initial model does not permit the teacher to override an incompatible active-role combination after a warning.

Portia should explain the conflict and offer an appropriate correction workflow, such as:

```text
replace the earlier Role
leave the candidate proposed
invalidate the unsupported Role
cancel the new assignment
```

It must not save a canonically incompatible current state merely because the teacher acknowledges a warning.

### Compatibility Changes

Changing the controlled role vocabulary or compatibility matrix is a domain-model change.

It requires:

* explicit design review;
* schema and validation review where applicable;
* migration consideration for existing records;
* updated fixtures and tests;
* and an ADR or amendment to the governing decision.

The application must not infer new compatible combinations dynamically from observed teacher usage.

---

## 7.16 Corrections, Refinement, and Supersession

A Role may be corrected or refined without changing participant identity.

Examples include:

```text
reported_involved
→ directly_involved
```

```text
present
→ invalidated
```

```text
contextual
→ directly_involved
```

### Proposed-State Corrections

A proposed Role may be corrected in place while the teacher is reviewing:

* `role_type`;
* `basis`;
* top-level `detail` when the Role is `contextual`;
* and other reviewable proposed values that do not change canonical participant identity.

Once a canonical Role record has been persisted:

```text
participant_id
```

is immutable.

A proposed Role associated with the wrong Event Participant must be invalidated or superseded by a new Role referencing the correct participant.

Uncommitted interface state may be corrected before canonical persistence.

A proposed non-contextual Role must not acquire top-level `detail` during review.

The record retains its original creation provenance and updates its current update provenance.

Confirmation without material change may transition:

```text
proposed → active
```

in place.

### Active-State Additions

An active Role may receive an additional basis entry in place only under the additive-support rules in Section 7.13.

An additive basis change must not alter:

* participant identity;
* role type;
* substantive meaning;
* prior basis entries;
* or the historical interpretation of the Role.

It requires append-only amendment history.

### Material Corrections

A material correction to an active Role creates a successor Role.

Material corrections include changing:

* `participant_id`;
* `role_type`;
* removing required top-level `contextual` detail;
* the substantive meaning of top-level `contextual` detail;
* an existing basis entry;
* the interpretation of the Role’s support;
* or another value that changes the canonical assertion.

Removing or replacing any existing active basis entry is always material.

The expected correction pattern is:

```text
preserve original active Role
→ create proposed successor with structured supersedes references
→ review and validate successor
→ activate successor and transition every replaced prior Role to superseded
   in one coordinated operation
```

The prior Role remains active throughout successor review.

A proposed successor that is invalidated or abandoned does not change the prior Role.

Before committing activation, Portia must validate the participant’s intended post-operation active-role set after removing every Role that will become superseded and adding the successor.

The correction operation must fail when that final set contains:

* duplicate active role types;
* an incompatible pair under Section 7.15;
* or more than the permitted initial active-role set.

The successor Role must:

1. receive a new `role_id`;
2. contain the corrected canonical assertion;
3. identify each prior Role through a structured `supersedes` entry;
4. record one controlled reason on each prior-Role reference;
5. require nonempty `detail` when a reference uses `other`;
6. preserve creation and update provenance;
7. and become `proposed` or `active` as appropriate.

The original Role remains unchanged except for its lifecycle transition to `superseded`.

### Structured Supersession References

A successor Role represents each replacement relationship through an array of structured references:

```json
{
  "supersedes": [
    {
      "role_id": "epr_prior",
      "reason": "basis_corrected"
    }
  ]
}
```

The array:

* must contain one or more entries when present;
* must contain structurally unique entries;
* may reference one prior Role for an ordinary correction;
* may reference several prior Roles for legitimate consolidation;
* and has no semantic ordering.

Each entry requires:

```text
role_id
reason
```

Each entry may also contain nested:

```text
detail
```

This nested field explains the replacement relationship. It is distinct from top-level Role `detail`, which is reserved for `contextual`.

The initial replacement reasons are:

```text
participant_corrected
role_type_corrected
basis_corrected
detail_corrected
duplicate_consolidated
role_relationship_corrected
other
```

#### `participant_corrected`

Use when the prior Role referenced the wrong Event Participant and the successor records the corrected participant relationship.

The prior and successor Roles must still belong to the same Event.

#### `role_type_corrected`

Use when the prior Role’s `role_type` was incorrect or when reviewed information supports a materially different Event-level role.

For example:

```text
reported_involved
→ directly_involved
```

#### `basis_corrected`

Use when an existing basis entry was removed, replaced, corrected, or materially reinterpreted.

A purely additive basis entry that satisfies the accepted in-place amendment rules does not use supersession.

#### `detail_corrected`

Use when correcting `detail` changes the substantive meaning of the Role rather than merely fixing punctuation, spelling, or formatting.

#### `duplicate_consolidated`

Use when one successor Role replaces two or more duplicate or overlapping prior Role records.

For example:

```json
{
  "supersedes": [
    {
      "role_id": "epr_duplicate_1",
      "reason": "duplicate_consolidated"
    },
    {
      "role_id": "epr_duplicate_2",
      "reason": "duplicate_consolidated"
    }
  ]
}
```

A consolidation must not erase differences among the prior Role records. Each remains historically inspectable.

#### `role_relationship_corrected`

Use for another material correction to the participant-to-Event role relationship that is not described more precisely by the other controlled reasons.

It must not become a substitute for an unsupported or vague correction rationale.

#### `other`

Use only when no controlled reason accurately describes the replacement.

When:

```text
reason = other
```

the reference requires nonempty `detail`.

For example:

```json
{
  "supersedes": [
    {
      "role_id": "epr_prior",
      "reason": "other",
      "detail": "Corrected a migrated relationship whose legacy mapping was incomplete."
    }
  ]
}
```

### Replacement Effect and Activation Boundary

A `supersedes` array may appear on a proposed successor so Portia can preserve and review the intended correction before activation.

While the successor remains proposed, its references describe replacement intent only.

The replacement becomes effective when the successor reaches:

```text
status = active
```

The successor activation and prior-Role supersession transitions form one logical transaction.

Conceptually:

```text
validate successor and all prior references
→ prepare successor active transition
→ prepare each prior superseded transition
→ append lifecycle and correction history
→ commit all resulting canonical states
```

The implementation must use either:

* an atomic multi-record transaction;
* or a recoverable staged-write protocol that prevents a partial operation from being accepted as complete.

A completed operation must not leave:

```text
successor = active
prior = active
```

for a prior Role that the successor effectively replaces.

It also must not leave:

```text
successor = proposed
prior = superseded
```

A recoverable implementation should converge to one of two valid durable outcomes:

```text
not committed:
successor = proposed
prior Role or Roles = active
```

```text
committed:
successor = active
prior Role or Roles = superseded
```

When one successor consolidates several prior Roles, all applicable prior transitions belong to the same coordinated operation.

Failure to transition any required prior Role prevents the replacement operation from being considered complete.

### Abandoned or Invalidated Successors

A proposed successor may be invalidated before activation.

In that case:

* its `supersedes` references remain historical evidence of the attempted correction;
* none of the referenced prior Roles becomes superseded;
* current-role views continue to use the unchanged active prior Role or Roles;
* and lifecycle history records that the proposed successor was invalidated.

Reverse supersession views must distinguish:

* prospective references that never became effective;
* and effective replacement relationships completed through successor activation.

An effective historical replacement remains part of lifecycle history even if the successor is later invalidated through a separate lifecycle event.

### Supersession Scope and Validation

Before successor activation, every referenced prior Role must:

* exist;
* belong to the same Event as the successor;
* have a different `role_id` from the successor;
* remain eligible for replacement under the lifecycle rules;
* ordinarily remain active until the coordinated operation commits;
* and correspond to the reason recorded on that reference.

A proposed successor may preserve its intended references even when later review determines that activation should not occur. Such references remain prospective and do not by themselves establish effective supersession.

A successor may reference a prior Role associated with a different `participant_id` only when the reason legitimately corrects the participant relationship, such as:

```text
participant_corrected
role_relationship_corrected
duplicate_consolidated
```

Application validation must prevent:

* self-supersession;
* duplicate references to the same prior Role;
* references to Roles in another Event;
* unsupported replacement reasons;
* reason-and-change mismatches;
* circular supersession chains;
* and conflicting successor relationships that violate the accepted correction model.

The initial model stores no canonical top-level:

```text
replacement_reason
superseded_by
```

Reverse `superseded_by` views are derived from structured successor references together with lifecycle history showing that the successor reached `active` and the replacement operation became effective.

A proposed or pre-activation-invalidated successor must not appear as an effective `superseded_by` relationship merely because it contains a prospective reference.

### Invalidation Without Replacement

A Role should become `invalidated` rather than `superseded` when the assertion should no longer be treated as valid and no corrected Role replaces it.

Examples include:

* a false paper interpretation;
* a duplicate active Role;
* a Role created in error;
* unsupported involvement;
* or a retracted source that leaves the assertion without sufficient support.

### Role-Type Refinement

A later `directly_involved` Role does not mutate an earlier `reported_involved` Role.

When reviewed information supports the new relationship:

```text
create directly_involved successor
→ link successor to prior reported_involved Role
→ activate successor
→ supersede prior Role
```

This preserves that the earlier canonical assertion was qualified as reported.

### Supporting Account Dependency Resolution

An Account referenced by a Role remains a separate canonical record with its own lifecycle.

Portia must never silently retarget:

```text
account_ref
```

when the referenced Account is corrected, superseded, or invalidated.

#### Proposed Roles

A proposed Role may have its Account basis corrected in place during review, subject to the other proposed-state rules.

For example, Portia may replace an incorrect proposed `account_ref` before the Role becomes active.

The change must preserve ordinary update provenance.

#### Active Roles

Replacing or removing an Account basis from an active Role is material.

When a corrected Account replaces the original Account:

```text
preserve prior Account
→ create or activate corrected Account
→ create successor Role referencing corrected Account
→ activate successor Role
→ supersede prior Role
→ complete Account transition
```

The prior Role continues to reference the Account that actually supported it during its active period.

When an Account is invalidated without replacement, every dependent active `reported_involved` Role must be resolved through one of these paths:

```text
invalidate the dependent Role
```

or:

```text
create a successor Role supported by another qualifying attributed Account
→ activate successor
→ supersede prior Role
```

If several active Roles depend on the Account, the Account and Role transitions form one coordinated, atomic or recoverable operation.

An Account transition must not commit a durable state in which an active `reported_involved` Role lacks a qualifying same-Event attributed Account.

If dependency resolution fails, the Account transition must remain uncommitted or recover to its prior valid state.

#### Historical Preservation

The original Account and every dependent prior Role remain historically inspectable.

Account correction does not rewrite the Role basis that existed earlier.

Role correction does not rewrite the Account’s earlier canonical content or lifecycle history.

### Event Participant Dependency Resolution

An active Role continuously requires:

```text
referenced Event Participant status = active
```

Portia must resolve dependent Roles before an active participant becomes invalidated or superseded.

#### Participant Invalidation Without Replacement

When an active Event Participant is invalidated without replacement:

```text
identify every dependent active Role
→ invalidate each dependent active Role
→ append Role lifecycle history
→ invalidate the participant
→ commit as one coordinated operation
```

A dependent Role must not remain active while pointing to an invalidated participant.

#### Participant Supersession

When an active Event Participant is superseded, each dependent active Role must be handled explicitly.

For a Role that should carry forward:

```text
create successor Role
→ reference the replacement participant_id
→ preserve the appropriate role type and valid basis
→ link successor to prior Role
→ activate successor
→ supersede prior Role
```

For a Role that should not carry forward:

```text
invalidate prior Role
```

The participant replacement and all required Role transitions must be atomic or recoverable.

The operation must not durably leave:

```text
prior participant = superseded
dependent Role = active
```

Existing Role records are never retargeted to a different `participant_id`.

The replacement relationship is represented through new participant and Role records.

#### Proposed Dependent Roles

A proposed Role referencing a participant that becomes invalidated or superseded cannot later become active unchanged.

It must be:

* invalidated;
* or replaced by a new proposed or active Role referencing the valid participant.

### Event Lifecycle Effects

Role status is not cascade-rewritten merely because the owning Event changes lifecycle state.

#### Event Closure

Closing an Event leaves child Role statuses unchanged.

Accepted Roles remain historically meaningful relationships within the closed Event.

New Role activation requires reopening the Event to `active`.

#### Event Reopening

Reopening a closed Event does not reactivate, invalidate, or otherwise rewrite child Roles.

Their existing statuses remain authoritative.

#### Event Cancellation, Invalidation, or Supersession

Cancelling, invalidating, or superseding an Event excludes its Roles from ordinary current Event views.

Portia does not cascade every Role to `invalidated` or `superseded`.

The child records remain available in explicit audit and correction views.

A replacement Event receives new Event Participant and Role records where appropriate. Roles are not moved or retargeted across Event roots.

### Canonical Retention and No Hard Delete

After a Role record has been canonically persisted, Portia must not hard-delete its file through an ordinary workflow.

This applies to:

```text
proposed
active
invalidated
superseded
```

Roles created in error use lifecycle invalidation rather than deletion.

Replaced Roles use supersession rather than deletion.

Abandoned proposed Roles use invalidation rather than deletion.

The following are not canonical Role records and may be cleaned up:

* failed writes that never committed;
* temporary upload or parsing artifacts;
* transaction staging files;
* and other explicitly noncanonical implementation debris.

Canonical Role retention preserves:

* provenance;
* review history;
* correction lineage;
* participant dependency history;
* Account dependency history;
* and auditability.

A mistaken terminal transition is corrected through append-only amendment or a new Role record, not deletion or reactivation.

### Correction History

Portia must preserve:

* the original Role assignment;
* every successor Role;
* every structured forward supersession reference;
* whether and when each intended replacement became effective;
* the reason associated with each replaced prior Role;
* successor activation and prior supersession lifecycle transitions;
* additive-basis amendments;
* correction timestamps;
* local operator attribution;
* and controlled correction or replacement reasons.

A Role correction does not ordinarily require:

* a new Event;
* a new Event Participant;
* or mutation of the participant’s subject identity.

Reverse `superseded_by` views are derived rather than stored canonically.

---

## 7.17 Prohibited Responsibility and Judgment Labels

The initial Event-level role vocabulary must not include:

```text
offender
victim
aggressor
perpetrator
guilty
responsible
responsible_student
problem_student
innocent
credible
dishonest
at_fault
```

These values embed:

* responsibility findings;
* moral or disciplinary judgments;
* contested interpretations;
* impact determinations;
* or credibility conclusions.

Such meanings must not be encoded in identity or neutral Event-level role assignments.

When Portia later records a formal or teacher-level conclusion, that conclusion belongs in an attributed and provenance-preserving Determination record.

An Account may use a source’s own language where appropriate, but source language must not become a neutral canonical role automatically.

---

## 7.18 Source and Workflow Relationships Are Not Generic Roles

Portia must not use generic role assignments to duplicate relationships already established elsewhere.

The initial Event-level role model therefore excludes values such as:

```text
reporter
observer
account_source
response_recipient
response_provider
support_recipient
support_provider
follow_up_owner
decision_maker
```

Those relationships should be derived from the canonical records that establish them.

For example:

* an Account identifies its source;
* an Observation identifies its observer or documentary source;
* a Response identifies its recipients and providers;
* a Support Process identifies relevant support relationships;
* and a Follow-Up identifies its responsible or participating people.

This prevents role assignments from becoming an inconsistent parallel relationship system.

---

## 7.19 Role Creation and Review Workflows

### Decision

Initial Role status is determined by review state, not automatically by creation source.

Every workflow must also assign the Role’s own creation source from the workflow that creates that Role.

Portia supports:

```text
direct reviewed creation as active
unreviewed or ambiguous creation as proposed
reviewed proposed-to-active confirmation
reviewed successor activation
```

The teacher-facing workflow should avoid a redundant confirmation step when the teacher has already made an explicit, unambiguous digital selection.

It must still prevent machine-interpreted, imported, ambiguous, or incomplete suggestions from appearing as current Roles without review.

### Explicit Reviewed Digital Entry

A teacher may create a Role directly as `active` when the teacher:

1. selects an active Event Participant;
2. works within an Event whose status is `draft` or `active`;
3. deliberately selects one supported neutral role type;
4. reviews any required basis or detail;
5. saves the complete Role assertion;
6. and all schema and application validation succeeds.

For example:

```json
{
  "status": "active",
  "role_type": "present",
  "creation_source": {
    "type": "digital_entry"
  }
}
```

may be created directly when the teacher explicitly selected and saved `present`.

The Role remains `digital_entry` even when its Event or Event Participant originated through paper capture or import.

The interface must not require:

```text
save proposed
→ reopen
→ confirm active
```

for that ordinary reviewed workflow.

A direct digital Role may omit `basis` when the accepted basis rules permit omission.

A directly entered:

```text
directly_involved
present
reported_involved
```

Role must not contain top-level `detail`.

### Directly Entered `reported_involved`

A digitally entered `reported_involved` Role may begin as active only when:

* the teacher explicitly selects or confirms `reported_involved`;
* at least one same-Event attributed Account exists;
* the Role basis contains an `account_ref` to that Account;
* every referenced source validates;
* the reported qualification remains visible;
* and no unresolved ambiguity remains.

The Account requirement is the same for digital, paper, and import workflows.

For example:

```json
{
  "status": "active",
  "role_type": "reported_involved",
  "basis": [
    {
      "kind": "account_ref",
      "record_id": "acct_01j9..."
    }
  ],
  "creation_source": {
    "type": "digital_entry"
  }
}
```

A bare digital selection of `reported_involved` without a valid same-Event attributed `account_ref` must not become active.

### Directly Entered `contextual`

A digitally entered `contextual` Role may begin as active only when:

* the teacher explicitly selects or confirms `contextual`;
* no more specific compatible role accurately describes the current relationship;
* concise nonempty `detail` explains the legitimate Event-context connection;
* the detail remains neutral and non-narrative;
* the resulting active-role set satisfies Section 7.15;
* and no unresolved ambiguity remains.

For example:

```json
{
  "status": "active",
  "role_type": "contextual",
  "detail": "Participated in the immediate class-related conference.",
  "creation_source": {
    "type": "digital_entry"
  }
}
```

A digital `contextual` assignment without valid detail must remain proposed or be rejected.

### Reviewed Digital Successors

A teacher may review a material correction digitally and create the successor directly as active within the coordinated replacement operation.

The operation must:

```text
validate the successor and intended post-operation active-role set
→ create or transition successor as active
→ transition every effectively replaced prior Role to superseded
→ append lifecycle and correction history
→ commit atomically or through recoverable staged writes
```

The workflow must not manufacture a separate proposed-state persistence step when the successor has already been fully reviewed before the transaction begins.

When correction review is incomplete, the successor begins as proposed and the prior Role remains active.

### Paper Capture

A Portia paper-capture page may include optional neutral role marks such as:

```text
Directly involved
Present
Reported involved
Other context
```

The printed page does not need to require a role selection.

Before scanning, printed role marks are only capture affordances.

They do not create:

* blank Role records;
* proposed Role records;
* preallocated Role IDs;
* or Role creation provenance.

After scanning:

* recognized role marks may create proposed Role assignments;
* every paper-created Role uses `creation_source.stage = ingested`;
* every paper-created Role receives a matching `paper_capture` basis entry;
* the matching basis repeats the creation-source `route_id` and `page_record_id` exactly;
* a recognized `reported_involved` mark may create a proposed Role with only that matching paper basis;
* a recognized contextual or “other context” mark may create a proposed `contextual` Role without `detail`;
* ambiguous marks remain unresolved review items;
* an unmarked role area creates no Role assignment;
* and no paper-interpreted Role becomes active automatically.

The teacher must be able to:

* inspect the originating paper artifact through the matching basis;
* create, review, or select the attributed Account required before activating paper-derived `reported_involved`;
* confirm the proposed Role;
* supply the required detail before activating `contextual`;
* choose another neutral role;
* add more than one compatible Role;
* leave the participant without a Role;
* or discard the interpretation.

After explicit review, a valid paper-derived proposed Role may transition to active.

A paper-derived `reported_involved` Role is not valid for activation until its basis also contains at least one same-Event attributed `account_ref`.

The review interface may create the Account from captured page content and link it automatically, but the Account remains a separate canonical record governed by its own schema and lifecycle.

Its `creation_source` remains:

```text
paper_capture / ingested
```

A Role cannot transition from:

```text
paper_capture / preallocated
```

because that Role source shape is invalid.

Confirmation changes status and update attribution, not historical origin or the required matching basis.

Paper-derived explanatory text may populate top-level `detail` only for a reviewed `contextual` Role.

For `directly_involved`, `present`, or `reported_involved`, explanatory text must be routed to the appropriate Account, Observation, Event summary, or other canonical record rather than stored as Role `detail`.

A paper workflow could create a Role directly as active only when teacher review occurs before canonical Role creation and the complete assertion is explicitly accepted.

For `reported_involved`, that complete assertion must already include the same-Event attributed Account reference.

The paper source alone never authorizes active status.

Paper capture must not offer prohibited judgment labels merely for convenience.

### Imports

Imported Role data awaiting teacher review ordinarily begins as proposed.

An import does not become active merely because:

* parsing succeeded;
* identifiers matched;
* the source system marked the record complete;
* or the import operation was initiated by the teacher.

After explicit review, Portia may:

* transition a proposed imported Role to active;
* or create the reviewed imported Role directly as active when review occurs before canonical Role creation.

An imported `contextual` Role must acquire valid nonempty top-level `detail` before either activation path succeeds.

An imported `reported_involved` proposal may initially preserve an `import_source` basis.

Before activation, Portia must create or select a same-Event attributed Account representing the imported report and add an `account_ref` to the Role basis.

The import basis remains useful provenance and proposal support, but it does not replace the canonical Account.

Imported top-level `detail` must be rejected or remapped when the Role type is:

```text
directly_involved
present
reported_involved
```

In either case:

```text
creation_source.type = import
```

remains accurate.

Review changes status and update attribution.

It does not rewrite the Role source as `digital_entry`, and it does not copy the Event or Event Participant source.

### Automated Extraction and Suggestions

A Role produced or suggested through:

* handwriting recognition;
* checkbox interpretation;
* automated text extraction;
* heuristic matching;
* or another system-generated inference

must begin as proposed unless the teacher explicitly reviews the complete assertion before canonical creation.

A system process must not activate its own suggestion merely because it meets structural validation.

### Ambiguity

A Role must begin or remain proposed when ambiguity exists concerning:

* participant identity;
* role type;
* the required meaning of a `contextual` relationship;
* source linkage;
* paper-mark interpretation;
* imported-field mapping;
* duplicate resolution;
* or material correction intent.

Portia must not resolve ambiguity by selecting the most likely active Role automatically.

### Creation Source Does Not Determine Status or Inherit from Parents

The following rules are prohibited:

```text
digital_entry always means active
paper_capture always means proposed forever
import always means proposed forever
Role source equals Event source
Role source equals Event Participant source
```

Instead:

* explicit completed teacher review may permit active status;
* incomplete or machine-dependent review requires proposed status;
* each Role source is assigned from the workflow that created that Role;
* creation source remains immutable provenance;
* parent and child sources may differ;
* and status records whether the Role is currently accepted.

The application must evaluate the complete workflow state rather than infer review status from `creation_source.type` alone.

---

## 7.20 Derived Views

Role views must evaluate the Role together with its parent records.

### Ordinary Current Event Views

A Role appears in an ordinary current Event view only when:

```text
Role status = active
Event Participant status = active
Event status = active
```

Portia may derive current views such as:

```text
participants directly involved
participants present
participants reported involved
participants with no assigned Event-level role
```

A role-free participant must remain visible.

The absence of a role must not be displayed as:

```text
unknown involvement
```

unless Portia explicitly records that meaning elsewhere.

### Draft-Review Views

An active Role beneath a draft Event may appear in:

* draft Event assembly;
* teacher review;
* validation;
* and activation-preparation views.

It must be visibly scoped to the draft Event and must not appear in ordinary accepted Event histories.

### Closed-Event History

A Role that remains active when its Event closes may appear as an accepted historical relationship within that closed Event.

Closing does not require a Role status transition.

### Terminal or Noncurrent Parents

Roles beneath a cancelled, invalidated, or superseded Event are excluded from ordinary current views regardless of their stored Role status.

Roles referencing an invalidated or superseded Event Participant are also excluded.

Such records remain available in explicit:

* lifecycle audit views;
* correction-history views;
* supersession views;
* and provenance inspection.

Derived views must distinguish stored Role status from effective current visibility.

---

## 7.21 Validation Requirements

Because role records are stored separately, `event-participant.schema.json` cannot validate the role collection.

The Event Participant schema should:

* reject authoritative `role` fields;
* reject authoritative `roles` arrays;
* and remain valid when no role assignments exist.

A future Event Participant Role schema should enforce:

* the required role-record envelope;
* constant `record_type`;
* supported role types;
* supported statuses;
* the structural fields required for Role lifecycle history references where included;
* required record-level `creation_source`;
* valid creation-source variants;
* `stage = ingested` whenever Role `creation_source.type = paper_capture`;
* rejection of Role `creation_source.stage = preallocated`;
* a conditional nonempty `basis` requirement when `creation_source.type = paper_capture`;
* at least one `paper_capture` basis variant for every paper-derived Role;
* no schema-level inheritance from Event or Event Participant provenance;
* no schema-level implication that one creation source uniquely determines status;
* top-level `detail` permitted only when `role_type` is `contextual`;
* optional top-level `detail` for proposed `contextual` Roles;
* nonempty top-level `detail` for active and superseded `contextual` Roles;
* rejection of top-level `detail` for `directly_involved`, `present`, and `reported_involved`;
* rejection of empty or whitespace-only required contextual detail;
* independent nested `supersedes[].detail` rules;
* `basis` as an optional nonempty array except where conditionally required;
* mutually exclusive structured basis-entry variants;
* `contains` validation for a paper basis when the Role source is paper capture;
* compact `account_ref` and `observation_ref` shapes containing only `kind` and `record_id`;
* rejection of repeated Event-scope fields inside Event-local record references;
* structurally unique basis entries;
* a source-oriented basis requirement for proposed `reported_involved`;
* an `account_ref` requirement for every active and superseded `reported_involved`;
* `supersedes` as a nonempty array of structured prior-Role references;
* `role_id` and controlled `reason` on every supersession entry;
* nonempty `detail` when a supersession reason is `other`;
* structurally unique supersession entries;
* rejection of top-level canonical `replacement_reason` and `superseded_by`;
* identifier patterns;
* timestamp formats;
* and rejection of unknown properties.

JSON Schema can require that a paper-derived Role contain at least one `paper_capture` basis entry.

It can also conditionally require at least one `account_ref` when:

```text
role_type = reported_involved
status = active or superseded
```

This rule is independent from creation source.

Standard JSON Schema cannot determine whether an invalidated Role was rejected while proposed or invalidated after having been active. Lifecycle validation must preserve the Account reference for the latter case.

Standard JSON Schema also cannot, by itself, compare the `route_id` and `page_record_id` values in the paper basis entry against sibling values inside `creation_source`.

Exact cross-field equality is therefore an application invariant.

JSON Schema may permit `supersedes` on a proposed successor because the field can preserve reviewed replacement intent.

JSON Schema cannot determine whether those references have become effective. Effectiveness depends on lifecycle history and the coordinated activation operation.

JSON Schema can conditionally require `detail` from `role_type` and current `status`.

It cannot determine from one invalidated record whether that Role was rejected while proposed or invalidated after having been active. Application lifecycle validation must therefore prevent deletion of historical detail from a formerly active `contextual` Role.

JSON Schema also cannot enforce duplicate or compatibility rules across the participant’s separate Role files. Those rules depend on the complete intended active-role set.

Application validation must additionally confirm:

* that Role activation references an active Event Participant;
* that Role activation occurs only while the Event is `draft` or `active`;
* that an active Role beneath a draft Event is excluded from ordinary current Event histories;
* that current-view eligibility is derived from Role, participant, and Event state;
* that every Role has its own creation source;
* that the Role source matches the workflow that created the Role;
* that every paper-derived Role was created only after returned-page interpretation and uses `stage = ingested`;
* that every paper-derived Role contains a matching `paper_capture` basis entry;
* that the matching basis `route_id` and `page_record_id` equal the creation-source values exactly;
* that additional basis entries do not substitute for the matching paper entry;
* that paper or import basis alone leaves `reported_involved` proposed;
* that every active `reported_involved` contains at least one same-Event attributed `account_ref`;
* that the referenced Account satisfies the Account attribution contract;
* that every superseded or formerly active invalidated `reported_involved` Role preserves its Account reference;
* that an invalidated never-active proposal may lack an Account;
* that the matching entry remains present through confirmation, invalidation, and supersession;
* that no blank or pre-render Role record was created merely from page generation;
* that Role `stage = preallocated` is rejected;
* that no Role source was inferred merely from the Event, Event Participant, basis, prior Role, or current editor;
* that successor Roles preserve their own source independently from superseded Roles;
* that immutable Role creation provenance is not rewritten through ordinary review or lifecycle transitions;
* whether initial active status was produced through explicit completed teacher review;
* whether proposed status is required because review, identity, role, source, or correction intent remains ambiguous;
* that creation source is preserved independently from review status;
* that machine-generated or unreviewed suggestions do not become active automatically;
* that every directly active `reported_involved` Role has the required same-Event attributed Account reference and explicit confirmation;
* that every active `contextual` Role contains concise neutral nonempty top-level detail;
* that a proposed `contextual` Role may remain incomplete without becoming current;
* that top-level detail is absent from every non-contextual Role;
* that imported, paper-derived, or digitally entered explanatory text is routed appropriately rather than copied into prohibited Role detail;
* that nested `supersedes[].detail` is validated independently from top-level contextual detail;
* that a superseded `contextual` Role preserves activation-complete detail;
* that an invalidated formerly active `contextual` Role does not lose historical detail;
* that removing or substantively replacing active contextual detail uses material correction and supersession;
* that a reviewed direct-active successor participates in the complete coordinated replacement operation;
* parent Event existence;
* parent participant existence;
* matching Event ownership;
* valid referenced Account or Observation records;
* same-Event ownership for every Account and Observation basis reference;
* rejection of cross-Event Account and Observation basis relationships;
* valid referenced paper routes and page records;
* import-source traceability;
* semantic duplicate-basis detection;
* duplicate active-role detection using the intended post-operation state;
* compatibility-matrix validation using the intended post-operation state;
* enforcement of the maximum initial active-role set;
* rejection of warning-only overrides for incompatible active-role combinations;
* classification of active basis changes as additive or material;
* append-only amendment history for in-place active basis additions;
* rejection of in-place active basis removal or replacement;
* the complete allowed Role-transition matrix;
* rejection of prohibited transitions and ordinary reactivation of terminal Roles;
* append-only lifecycle history for every Role transition;
* no hard deletion of canonical Role records;
* immutability of persisted `participant_id`;
* correct lifecycle transitions;
* prospective-versus-effective supersession interpretation;
* successor activation as the exact replacement boundary;
* coordinated successor activation and prior-Role supersession;
* atomic or recoverable staged-write behavior;
* rollback or recovery to a valid durable state after partial failure;
* preservation of prior active Roles when a successor is abandoned or invalidated before activation;
* existence and same-Event scope of every referenced prior Role;
* activation-time eligibility of every referenced prior Role;
* reason-and-correction consistency for every supersession reference;
* participant-change eligibility for cross-participant replacement;
* self-reference, duplicate-reference, cycle, and conflicting-successor prevention;
* forward supersession consistency;
* Account correction, supersession, and invalidation dependency resolution;
* prevention of silent `account_ref` retargeting;
* prevention of active `reported_involved` Roles without a qualifying Account after an Account transition;
* active-participant dependency enforcement;
* coordinated participant invalidation or supersession with dependent Role transitions;
* prevention of persisted Role retargeting to another participant;
* Event closure, reopening, cancellation, invalidation, and supersession visibility effects;
* source-retraction handling;
* and provenance-preserving correction links.

---

## 7.22 Event Participant Role Invariants

1. Participant identity and Event-level role are separate canonical records.
2. Event Participant records contain no authoritative embedded role or roles array.
3. One Role record assigns one role type to one Event Participant within one Event.
4. Multiple roles require multiple Role records.
5. One participant may have zero, one, or several historical or proposed role assignments.
6. No role assignment is required for Event activation.
7. A participant without a role remains a valid participant.
8. Role assignments use independent opaque identities.
9. Every Role assignment references exactly one Event Participant.
10. A persisted Role’s `participant_id` is immutable.
11. A wrong-participant proposed Role is invalidated or superseded by a new Role rather than retargeted.
12. Role activation requires an active Event Participant.
13. Role activation is permitted only while the Event is `draft` or `active`.
14. A proposed Event Participant cannot own an active Role.
15. An active Role beneath a draft Event is accepted for draft assembly but excluded from ordinary current Event histories.
16. Ordinary current Role visibility requires an active Role, active Event Participant, and active Event.
17. Event closure does not alter child Role status.
18. Event reopening does not alter child Role status.
19. Event cancellation, invalidation, or supersession excludes child Roles from ordinary current views without cascade-rewriting their statuses.
20. An active Role continuously requires an active Event Participant.
21. Participant invalidation without replacement requires coordinated invalidation of dependent active Roles.
22. Participant supersession requires successor Roles for relationships that carry forward or invalidation of Roles that do not.
23. Participant and dependent-Role transitions are atomic or recoverable.
24. Role assignments do not point directly to students, Actors, or descriptive subjects.
25. Initial Event-level roles use neutral language.
26. `directly_involved` does not indicate responsibility or fault.
27. `present` does not assert observation or direct involvement.
28. `reported_involved` remains visibly qualified as reported.
29. `reported_involved` requires at least one source-oriented basis entry.
30. `contextual` is used sparingly when no more specific initial role adequately describes the relationship.
31. A proposed `contextual` Role may omit `detail`.
32. An active `contextual` Role requires concise neutral nonempty `detail`.
33. A superseded `contextual` Role preserves its activation-complete detail.
34. An invalidated proposed `contextual` Role may lack detail.
35. An invalidated formerly active `contextual` Role retains its historical detail.
36. Removing or substantively replacing active contextual detail is a material correction.
37. Top-level Role `detail` is permitted only for `contextual`.
38. Top-level `detail` is prohibited for `directly_involved`, `present`, and `reported_involved`.
39. Nested `supersedes[].detail` is distinct from top-level contextual detail.
40. Clarifying facts for non-contextual Roles remain in Accounts, Observations, Event context, or basis records.
41. Stored active status is necessary but not sufficient for ordinary current-view visibility.
42. One participant may have at most two active Roles under the initial vocabulary.
43. `present` may coexist with `directly_involved`, `reported_involved`, or `contextual`.
44. `directly_involved`, `reported_involved`, and `contextual` are mutually exclusive as current active roles.
45. Duplicate active role types for one participant are prohibited.
46. Compatibility and duplicate validation use the intended post-operation active-role set.
47. Proposed and historical Roles may preserve incompatible assertions without making them current.
48. Incompatible active-role combinations cannot be saved through a warning-only override.
49. `basis` is an optional unordered array of one or more structured entries.
50. Direct teacher assignment may omit `basis`.
51. No `teacher_entry` basis kind is defined.
52. The number or order of basis entries does not establish credibility, agreement, or evidentiary weight.
53. Several basis entries support one Role assertion rather than creating several Role assignments.
54. Structurally and semantically duplicate basis entries are prohibited.
55. Creation source, operator provenance, lifecycle history, and assertion basis remain distinct.
56. Every Role has its own required structured creation source.
57. A Role source is independent from Event and Event Participant sources.
58. A Role source is not inferred from its basis, current editor, or superseded Role.
59. A successor Role records its own creation source.
60. Paper-derived Roles remain paper-derived after confirmation.
61. Every paper-derived Role uses `creation_source.stage = ingested`.
62. Event Participant Roles must never use `creation_source.stage = preallocated`.
63. Page generation and blank printed role marks do not create canonical Role records.
64. Every paper-derived Role contains at least one matching `paper_capture` basis entry.
65. The matching basis route and page references equal the Role creation-source references exactly.
66. Additional basis entries do not replace the required matching paper basis.
67. The matching paper basis remains attached after confirmation, invalidation, or supersession.
68. Paper or import basis may support a proposed `reported_involved` Role.
69. No `reported_involved` Role may become active without a same-Event attributed Account reference.
70. The active Account requirement is independent from Role creation source.
71. Account correction, supersession, or invalidation never silently retargets an active Role’s `account_ref`.
72. A proposed Role may correct its Account basis in place during review.
73. Replacing or removing an Account basis from an active Role requires Role supersession or invalidation.
74. An Account lifecycle operation must not leave an active `reported_involved` Role without a qualifying attributed Account.
75. Account and dependent-Role transitions are coordinated, atomic, or recoverable.
76. Prior Accounts and prior Roles remain historically inspectable.
77. Teacher confirmation does not substitute for the activation-required Account.
78. Every superseded or formerly active invalidated `reported_involved` Role preserves its Account reference.
79. An invalidated never-active `reported_involved` proposal may lack an Account.
80. Imported Roles remain imported after review.
81. Ordinary lifecycle changes do not rewrite Role creation provenance.
82. Account and Observation basis references resolve only within the Role’s owning Event.
83. Event-local Account and Observation references contain only `kind` and `record_id`.
84. Cross-Event Account and Observation basis references are prohibited.
85. Proposed Role bases may be edited during review.
86. Active Role bases may receive only genuinely additive, non-meaning-changing entries in place.
87. In-place active basis additions require append-only amendment history.
88. Removing or replacing an active basis entry requires a successor Role and supersession.
89. Material Role corrections receive new Role identities.
90. Successor Roles own canonical forward `supersedes` arrays.
91. A proposed successor may contain prospective `supersedes` references.
92. Prospective references do not alter prior Role status.
93. Every `supersedes` entry identifies one prior `role_id` and one controlled reason.
94. The `other` supersession reason requires nonempty `detail`.
95. One successor may consolidate several prior Roles through several structured references.
96. Supersession-array order has no semantic meaning.
97. Every referenced prior Role belongs to the same Event as the successor.
98. A prior Role becomes `superseded` only when the successor becomes `active`.
99. Successor activation and every required prior-Role supersession form one logical transaction.
100. The transaction is atomic or uses recoverable staged writes.
101. A failed or abandoned successor activation leaves the successor proposed or invalidated and the prior Role or Roles active.
102. A completed replacement must not durably leave both the successor and an effectively replaced prior Role active.
103. The completed replacement must leave a compatibility-valid post-operation active-role set.
104. Self-supersession, duplicate prior references, and circular supersession are prohibited.
105. Canonical top-level `replacement_reason` and `superseded_by` fields are prohibited.
106. Effective reverse `superseded_by` views require completed activation and lifecycle history.
107. Invalidated and superseded Role bases remain historical and are not edited ordinarily.
108. Source retraction is handled through invalidation or replacement rather than deletion of history.
109. Status records review and lifecycle state rather than creation source.
110. Explicit, unambiguous, reviewed digital entry may create a Role directly as active.
111. Direct active creation does not require a fabricated proposed-state transition.
112. A directly active `reported_involved` Role requires a same-Event attributed Account reference and explicit teacher confirmation.
113. A directly active `contextual` Role requires valid detail and explicit teacher confirmation.
114. Every direct-active creation must satisfy duplicate and compatibility validation.
115. Paper interpretation, automated extraction, unreviewed imports, ambiguous matching, incomplete contextual detail, and incomplete corrections ordinarily begin as proposed.
116. No paper-interpreted or machine-generated Role becomes active automatically.
117. A reviewed import may become active without changing its creation source to `digital_entry`.
118. A reviewed digital successor may be created and activated within the coordinated replacement operation.
119. Creation source alone neither authorizes nor permanently prohibits active status.
120. Paper-derived Roles require teacher confirmation.
121. An unmarked paper role area creates no assignment.
122. Account, Observation, Response, Support, Follow-Up, and Determination relationships remain canonical in their own record types.
123. Responsibility and judgment labels are prohibited from the neutral role vocabulary.
124. Allowed Role transitions are `proposed → active`, `proposed → invalidated`, `proposed → superseded`, `active → invalidated`, and `active → superseded`.
125. Direct reviewed creation as active remains permitted.
126. Invalidated and superseded Roles are terminal under ordinary workflows.
127. Active Roles do not return to proposed.
128. Terminal Roles are not reactivated or repurposed.
129. Every Role transition creates append-only lifecycle history.
130. Canonical Role records are never hard-deleted through ordinary workflows.
131. Failed or uncommitted temporary artifacts may be cleaned up because they are not canonical Role records.
132. Mistaken terminal transitions use append-only amendment or a new Role rather than deletion or reactivation.
133. Corrections preserve prior Role records and provenance.
134. Role changes do not mutate or retarget canonical participant identity.
135. Event activation does not depend on Role assignment.
136. The Event Participant JSON Schema remains compatible with separate canonical Role records.

## 8. Event Lifecycle and Status Transitions

### Decision

Every Event root stores one current lifecycle status.

The initial Event statuses are:

```text
draft
active
closed
cancelled
invalidated
superseded
```

The status describes the operational state of the Event record.

It does not describe:

* Event severity;
* participant responsibility;
* whether conduct was appropriate;
* whether an Account is credible;
* whether a concern was substantiated;
* whether a Response was successful;
* or whether a student requires support.

The Event root stores the current status for direct loading, filtering, and validation.

Every lifecycle transition must also be preserved through a separate append-only lifecycle-history record. Updating `work.json` alone is not sufficient lifecycle history.

---

## 8.1 Lifecycle Overview

The ordinary lifecycle is:

```text
draft
→ active
→ closed
```

Alternative terminal dispositions are:

```text
draft → cancelled

active → invalidated
active → superseded

closed → invalidated
closed → superseded
```

A closed Event may return to active status when additional ordinary documentation is required:

```text
closed → active
```

The accepted transition graph is:

```text
draft
├── active
└── cancelled

active
├── closed
├── invalidated
└── superseded

closed
├── active
├── invalidated
└── superseded
```

The following are terminal states under ordinary Portia workflows:

```text
cancelled
invalidated
superseded
```

Terminal Events remain preserved but do not return to ordinary active use.

---

## 8.2 Draft

Use:

```text
draft
```

when the Event exists but has not yet been accepted as a valid canonical representation of an occurrence.

Typical draft Events include:

* a digital entry still in progress;
* a preallocated paper quick-capture Event;
* a returned paper page awaiting review;
* an imported Event awaiting confirmation;
* an Event missing required activation data;
* or an Event whose participant identity remains under review.

A draft may contain incomplete contextual data.

Depending on the creation workflow, it may initially lack:

* a final occurrence object;
* a final neutral summary;
* active Event Participants;
* location;
* instructional context;
* or role assignments.

A draft must still preserve enough information to establish:

* durable Event identity;
* owning class;
* school year;
* creation source;
* creation provenance;
* and current lifecycle state.

A draft is not yet presented as an accepted Event in ordinary student or Actor histories.

Drafts may appear in:

* teacher work queues;
* paper-return review queues;
* incomplete-entry views;
* and cleanup views.

---

## 8.3 Active

Use:

```text
active
```

when the Event has passed activation validation and is currently accepted as a canonical representation of one bounded occurrence.

Activation requires at least:

```text
valid Event identity
valid owning class
valid school year
valid occurrence object
nonempty neutral summary
valid creation source
valid creation and update provenance
at least one valid active Event Participant
completed teacher review when required
```

For a returned-paper or uncertain import workflow, successful scanning, extraction, or identity matching is not sufficient.

The teacher must explicitly confirm the proposed canonical values before activation.

An active Event may receive ordinary additions such as:

* Event Participants;
* participant-role assignments;
* Accounts;
* Observations;
* Classifications;
* Responses;
* Communications;
* Follow-Ups;
* or other later Portia records.

The presence of:

```text
status = active
```

does not mean the underlying classroom situation remains ongoing.

It means only that the Event record remains open for ordinary documentation.

An active Event must not remain open merely to represent an ongoing pattern or Support Process.

---

## 8.4 Closed

Use:

```text
closed
```

when the Event remains valid but ordinary documentation of its bounded occurrence is considered complete.

Closing an Event does not:

* erase its participants;
* remove its Accounts or Observations;
* end a linked Support Process;
* imply that every question has been resolved;
* establish a Determination;
* indicate that a Response succeeded;
* prevent later historical correction;
* or prevent later Follow-Up records.

A closed Event remains part of valid Event history.

Closed Events ordinarily appear in:

* class Event histories;
* student histories when roster participation exists;
* Actor histories when Actor participation exists;
* timelines;
* and appropriate derived reports.

Closing an Event is an operational completion decision, not a behavioral judgment.

Closing does not cascade Role status changes.

Active child Roles remain accepted historical relationships within the closed Event.

A new Role must not be activated beneath a closed Event until the Event is reopened to `active`.

---

## 8.5 Reopening a Closed Event

A closed Event may return to:

```text
active
```

when additional ordinary documentation must be added to the same bounded Event.

Examples include:

* a relevant Account becomes available shortly after closure;
* an omitted participant must be added;
* an Observation belonging to the original occurrence is received;
* or routine Event documentation was closed prematurely.

The transition is:

```text
closed → active
```

Reopening requires:

* an explicit reason;
* a lifecycle-history record;
* an update to `updated_at`;
* and an update to `updated_by`.

Reopening must not be used to absorb:

* a later bounded occurrence;
* a renewed interaction on another date;
* an ongoing support effort;
* or later monitoring that belongs in Follow-Up.

When the new information concerns a separate occurrence, Portia must create a new Event instead.

Reopening does not reactivate, invalidate, or otherwise rewrite existing child Roles.

---

## 8.6 Cancelled

Use:

```text
cancelled
```

when a draft is intentionally abandoned before it ever becomes active.

Typical cancellation reasons include:

```text
unused_paper_draft
duplicate_preallocation
entry_abandoned
wrong_class_selected
created_in_error
other
```

Examples include:

* a preallocated paper quick-capture page was never used;
* the teacher began an entry and determined that no Event should be recorded;
* a blank draft was created accidentally;
* or an Event was preallocated under the wrong class and never activated.

The only ordinary transition into cancellation is:

```text
draft → cancelled
```

A cancelled Event never became an accepted representation of an occurrence.

It must not appear in ordinary Event histories as though an Event had occurred.

It may remain visible in:

* lifecycle audit views;
* paper-route cleanup views;
* draft-administration views;
* and explicit historical inspection.

An Event that has ever been active must not become cancelled.

Cancelling a draft Event does not cascade every child Role to another status.

Any persisted Roles remain available in audit views but are excluded from ordinary current histories because their Event is cancelled.

---

## 8.7 Invalidated

Use:

```text
invalidated
```

when a previously active or closed Event should no longer be treated as a valid representation of an occurrence.

Typical invalidation reasons include:

```text
duplicate_event
no_single_coherent_occurrence
incorrect_record
unsupported_identity_or_context
created_from_false_interpretation
other
```

Examples include:

* the Event was created from a false scan interpretation;
* later review showed that no coherent occurrence could be identified;
* the Event duplicated another valid Event and should not remain independently valid;
* or the record fundamentally misrepresented what was being documented.

Invalidation applies to the Event itself.

It should not be used merely because one field requires correction.

The following ordinarily require correction rather than Event invalidation:

* an inaccurate occurrence time;
* an incomplete summary;
* an incorrect location;
* a mistaken instructional context;
* one incorrect participant;
* or one incorrect role assignment.

The accepted transitions are:

```text
active → invalidated
closed → invalidated
```

An invalidated Event remains preserved for history and audit.

It must not appear as a valid current Event in ordinary student, Actor, or class histories unless the view explicitly includes invalidated records.

Invalidating an Event does not cascade-rewrite every child Role.

Child Roles remain historically inspectable but are excluded from ordinary current views because the owning Event is invalidated.

---

## 8.8 Superseded

Use:

```text
superseded
```

when one or more replacement Events become the canonical representation instead of the earlier Event.

Supersession is appropriate when correction cannot be performed honestly within the original Event identity.

Examples include:

* one Event incorrectly combined two occurrences and is replaced by two Events;
* two overlapping Events are replaced by one reviewed Event;
* a structurally incorrect imported Event is replaced;
* or a correction requires materially different Event boundaries.

The accepted transitions are:

```text
active → superseded
closed → superseded
```

A superseded Event remains preserved.

It must not continue to appear as the current canonical Event in ordinary views.

Superseding an Event does not move or retarget its child Roles to the replacement Event.

The replacement Event receives new Event Participant and Role records where appropriate.

Roles beneath the superseded Event remain available in historical and audit views but are excluded from ordinary current views.

---

## 8.9 Canonical Supersession Direction

Portia uses one canonical relationship direction.

The replacement Event owns the canonical forward relationship to the Event it replaces.

Conceptually, the replacement Event records:

```json
{
  "supersedes": [
    {
      "class_id": "english10_p2",
      "work_id": "evt_original"
    }
  ]
}
```

The superseded Event does not need to persist a canonical `superseded_by` field.

Reverse views such as:

```text
superseded by evt_replacement
```

are derived from replacement Events that reference the original Event.

This direction supports:

* one original Event being replaced by several Events;
* several original Events being replaced by one Event;
* and consistent reverse-index rebuilding.

For example, splitting one Event into two replacement Events produces:

```text
evt_replacement_a supersedes evt_original
evt_replacement_b supersedes evt_original
```

The original Event receives:

```text
status = superseded
```

Its reverse replacement list is derived.

Application validation must confirm that an Event marked `superseded` has at least one valid incoming canonical `supersedes` relationship from a replacement Event.

---

## 8.10 Allowed Transitions

The initial allowed Event transitions are:

| From     | To            | Meaning                                       |
| -------- | ------------- | --------------------------------------------- |
| `draft`  | `active`      | Event passed activation validation            |
| `draft`  | `cancelled`   | Draft was abandoned before activation         |
| `active` | `closed`      | Ordinary Event documentation is complete      |
| `active` | `invalidated` | Event is no longer treated as valid           |
| `active` | `superseded`  | Replacement Event or Events became canonical  |
| `closed` | `active`      | Event was reopened for ordinary documentation |
| `closed` | `invalidated` | Later review invalidated the Event            |
| `closed` | `superseded`  | Replacement Event or Events became canonical  |

No other ordinary transitions are permitted.

---

## 8.11 Prohibited Transitions

The following transitions are prohibited under ordinary workflows:

```text
active → draft
closed → draft

active → cancelled
closed → cancelled

cancelled → draft
cancelled → active
cancelled → closed

invalidated → draft
invalidated → active
invalidated → closed

superseded → draft
superseded → active
superseded → closed
```

### No Return to Draft

Once an Event has been activated, it has entered accepted history.

Returning it to draft would falsely imply that it had never passed activation review.

Corrections must instead use:

* ordinary field correction;
* reopening;
* invalidation;
* supersession;
* or a later amendment mechanism.

### Cancellation Is Pre-Activation Only

Cancellation means the draft never became an accepted Event.

An Event that was previously active cannot later be made historically equivalent to an unused draft.

### Terminal-State Preservation

Cancelled, invalidated, and superseded Events remain preserved historical records.

They must not be silently restored through ordinary status editing.

If a terminal disposition was itself entered incorrectly, the correction must use an explicit provenance-preserving exceptional mechanism defined by the later amendment architecture.

---

## 8.12 Transition Reasons

Every lifecycle transition records a reason.

The interface may provide controlled reasons with optional clarification.

A meaningful explicit reason is required for:

```text
draft → cancelled
closed → active
active → invalidated
closed → invalidated
active → superseded
closed → superseded
```

For routine transitions:

```text
draft → active
active → closed
```

Portia may supply a concise controlled reason, such as:

```text
activation_requirements_satisfied
routine_documentation_complete
```

The reason must still be preserved in transition history.

A transition reason must describe the lifecycle action.

It must not become:

* an Event summary;
* a behavior judgment;
* a participant Determination;
* or an Account.

---

## 8.13 Lifecycle-History Records

Every lifecycle transition creates a separate append-only history record.

Conceptually:

```json
{
  "schema_version": "1",
  "record_type": "event_lifecycle_transition",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j9...",
  "transition_id": "elt_01j9...",
  "from_status": "active",
  "to_status": "closed",
  "reason": {
    "type": "routine_documentation_complete"
  },
  "changed_at": "2026-09-18T15:42:00-04:00",
  "changed_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

A lifecycle-history record should contain at least:

```text
schema_version
record_type
module_id
class_id
work_id
transition_id
from_status
to_status
reason
changed_at
changed_by
```

The future record should use:

```text
record_type = event_lifecycle_transition
transition_id = elt_<opaque random value>
```

Conceptual storage is:

```text
records/
  event_lifecycle_transition/
    elt_<transition_id>.json
```

The exact lifecycle-transition JSON Schema is outside the two schemas required by the current issue.

The Event design must nevertheless preserve compatibility with this separate history model.

---

## 8.14 Initial Creation History

Creating a draft Event does not require a transition from a fictional prior status.

Portia may represent initial creation through:

* the Event root’s `created_at`, `created_by`, and `creation_source`;
* and optionally a lifecycle-history record whose action is Event creation rather than a status transition.

The first required status transition ordinarily occurs when the draft becomes:

```text
active
```

or:

```text
cancelled
```

Portia must not persist:

```text
from_status = null
```

unless a later lifecycle-history schema explicitly supports an initial-creation action.

---

## 8.15 Root Status and Transition Consistency

The root Event status must agree with lifecycle history.

After a successful transition:

1. Portia validates the requested transition.
2. Portia validates any destination-state requirements.
3. Portia creates the lifecycle-history record.
4. Portia updates the root `status`.
5. Portia updates `updated_at` and `updated_by`.
6. Portia commits the coordinated change according to Core persistence rules.

Portia must not leave:

* a transition record without the matching root status;
* or a changed root status without the matching transition record.

If coordinated persistence fails, Portia must report the inconsistent state and avoid presenting the transition as complete.

The Event root remains the direct source for current lifecycle status.

Transition records remain the authoritative history of how that status changed.

---

## 8.16 Activation Validation

The transition:

```text
draft → active
```

requires application-level validation across the Event work root and canonical child records.

Portia must confirm:

1. the Event root is structurally valid;
2. path and persisted identity agree;
3. the owning Core class exists;
4. the school year is valid;
5. the occurrence object uses one valid precision variant;
6. the summary is nonempty and valid;
7. creation and update provenance are valid;
8. at least one active Event Participant exists;
9. no required participant review remains pending;
10. returned-paper or import review has been completed where required;
11. and no blocking validation error remains.

Event Participant Role records are not required for activation.

Accounts, Observations, Classifications, Responses, Determinations, Follow-Ups, Outcomes, and Support Processes are also not required for activation.

---

## 8.17 Closure Validation

The transition:

```text
active → closed
```

requires that the Event remain structurally valid and preserve at least one valid participant relationship.

Portia should warn about unresolved work such as:

* proposed participants;
* proposed participant roles;
* incomplete paper-review items;
* or open teacher reminders.

Not every warning must block closure.

Blocking and nonblocking closure conditions should be defined explicitly as later record types are implemented.

Closing an Event must not require:

* a Classification;
* a Determination;
* a Response;
* an Outcome;
* or a Support Process.

Positive and neutral Events may close without concern-oriented records.

---

## 8.18 Paper Quick-Capture Lifecycle

A preallocated paper quick-capture Event begins as:

```text
status = draft
```

Before rendering, Portia creates:

* the Event work root;
* the draft `work.json`;
* the page record;
* and the persisted PDS2 route.

After scanning, the Event remains draft while Portia and the teacher review:

* occurrence information;
* summary text;
* participant identity;
* location;
* instructional context;
* and any proposed roles.

A scan must never cause:

```text
draft → active
```

automatically.

The teacher must explicitly activate the Event.

An unused paper draft transitions:

```text
draft → cancelled
```

with a reason such as:

```text
unused_paper_draft
```

It must not transition to `closed`, because it never became an accepted Event.

---

## 8.19 Derived Views

Ordinary Event views should treat statuses as follows:

| Status        | Ordinary current views         | Historical or audit views |
| ------------- | ------------------------------ | ------------------------- |
| `draft`       | Work queues only               | Yes                       |
| `active`      | Yes                            | Yes                       |
| `closed`      | Yes                            | Yes                       |
| `cancelled`   | No                             | Yes                       |
| `invalidated` | No                             | Yes                       |
| `superseded`  | Replacement-aware display only | Yes                       |

Student- and Actor-specific histories should ordinarily include:

```text
active
closed
```

They should exclude:

```text
draft
cancelled
invalidated
```

unless the teacher explicitly requests those states.

A superseded Event may appear in a replacement-aware historical view but must not be counted as a separate current Event alongside its canonical replacement without clear qualification.

---

## 8.20 Schema Requirements

The current Event JSON Schema should enforce:

```text
status
```

as a required field with the enum:

```text
draft
active
closed
cancelled
invalidated
superseded
```

The JSON Schema can validate the current status value.

It cannot, by itself, validate:

* prior status;
* transition legality;
* activation requirements involving separate participant files;
* lifecycle-history existence;
* supersession references in other Events;
* or whether a terminal state was reached correctly.

Those requirements must be enforced through application-level lifecycle validation.

The Event schema must not require lifecycle-history records to be embedded in `work.json`.

The root may later contain nonauthoritative derived lifecycle information, but current canonical transition history remains separate.

---

## 8.21 Event Lifecycle Invariants

1. Every Event root declares one current lifecycle status.
2. The initial statuses are `draft`, `active`, `closed`, `cancelled`, `invalidated`, and `superseded`.
3. Event closure does not alter child Role statuses.
4. Event reopening does not alter child Role statuses.
5. Event cancellation, invalidation, or supersession excludes child Roles from ordinary current views without cascade-rewriting them.
6. Event supersession does not move or retarget Roles across Event roots.
7. Status describes record lifecycle rather than behavior severity or responsibility.
8. Draft Events may be incomplete.
9. Draft Events do not appear as accepted Events in ordinary histories.
10. Activation requires successful application-level validation.
11. Active Events require at least one active Event Participant.
12. Event Participant Roles are not required for activation.
13. Active status does not mean the classroom situation remains ongoing.
14. Closed Events remain valid historical Events.
15. Closure does not establish a finding or Outcome.
16. Closed Events may be reopened with an explicit reason.
17. Reopening must not absorb a later bounded occurrence.
18. Cancellation applies only to Events that were never active.
19. Unused paper drafts should be cancelled rather than closed.
20. Invalidation means the Event itself is no longer treated as valid.
21. Correctable field or participant errors do not automatically require Event invalidation.
22. Supersession replaces an Event with one or more canonical Events.
23. Replacement Events own canonical `supersedes` relationships to prior Events.
24. Reverse `superseded_by` views are derived.
25. Cancelled, invalidated, and superseded Events are terminal under ordinary workflows.
26. Active or closed Events never return to draft.
27. Previously active Events never become cancelled.
28. Every transition preserves a reason and local provenance.
29. Every transition creates an append-only lifecycle-history record.
30. Root `status` and lifecycle history must remain consistent.
31. `updated_at` and `updated_by` do not replace lifecycle history.
32. Paper return or scan interpretation cannot activate an Event automatically.
33. Schema validation enforces the status vocabulary.
34. Application validation enforces transition legality and cross-record requirements.

## 9. Event Participant Lifecycle and Identity Resolution

### Decision

Event Participant records use the following lifecycle statuses:

```text
proposed
active
invalidated
superseded
```

A proposed participant may become active in place when the teacher confirms the same canonical subject identity.

A new participant record is required when the canonical subject identity changes materially, including:

* resolving an unknown person to a roster student or Actor;
* replacing an incorrect roster student or Actor;
* converting an Event-local descriptive person into a durable Actor or roster-student reference;
* or consolidating duplicate participant records.

The replacement participant owns the canonical relationship to the prior participant.

The original participant remains preserved and becomes `superseded`.

This model preserves meaningful identity history without requiring a new record for routine teacher confirmation.

---

## 9.1 Teacher-Workflow Constraint

Portia’s internal lifecycle and provenance model must not become the teacher’s workflow burden.

The teacher’s primary task is instruction.

Event capture, participant review, and behavior-support documentation are secondary activities intended to support instruction rather than interrupt it.

Portia must therefore follow this principle:

> Internal rigor may be complex; routine teacher interaction must remain fast, comprehensible, and proportionate to the instructional value produced.

Teachers should ordinarily interact with simple actions such as:

```text
Confirm
Correct
Dismiss
Add person
Resolve identity
Activate
Close
```

The interface should not ordinarily require teachers to:

* select technical lifecycle transitions;
* understand canonical replacement direction;
* enter opaque identifiers;
* create provenance records manually;
* manage filesystem locations;
* choose between invalidation and supersession without guidance;
* or repeat information Portia already knows.

Portia should derive the correct underlying records and transitions from the teacher’s plain-language action.

For example:

```text
Teacher action:
Wrong student—change to Jordan Lee.

Portia operation:
create corrected participant
activate corrected participant
link it as superseding the prior participant
transition prior participant to superseded
write lifecycle history
update derived views
```

The teacher should not need to perform those operations individually.

---

## 9.2 Proposed

Use:

```text
proposed
```

when a participant identity or Event relationship has been suggested but has not yet been confirmed.

Typical sources include:

* scanned roster marks;
* handwriting interpretation;
* imported data;
* uncertain student matching;
* and incomplete digital entry.

A proposed participant:

* does not satisfy Event activation;
* does not appear in ordinary student or Actor histories;
* may be corrected before confirmation;
* and must remain visibly identified as awaiting review.

Because a proposed participant has not yet entered accepted participant history, its subject fields may be edited during review.

Those edits must still update ordinary record provenance.

---

## 9.3 Active

Use:

```text
active
```

when the participant identity and relationship to the Event have been reviewed and are currently accepted.

An active participant:

* satisfies the Event’s minimum-participant requirement;
* appears in appropriate current and historical views;
* may receive active Event Participant Role assignments;
* and may be referenced by Accounts, Observations, Responses, or later Portia records.

Only an active participant may own an active Role.

Active status indicates only that the participant relationship is accepted.

It does not indicate:

* responsibility;
* fault;
* credibility;
* misconduct;
* harm;
* or whether a concern was substantiated.

---

## 9.4 Invalidated

Use:

```text
invalidated
```

when the participant record should not be treated as a valid relationship to the Event and no replacement participant is required.

Initial invalidation reasons should include:

```text
false_paper_interpretation
incorrect_person
not_participant
duplicate_record
created_in_error
unsupported_identity
other
```

Examples include:

* a scan falsely interpreted a roster mark;
* an imported record contained an extra participant;
* the teacher selected someone accidentally;
* or later review established that the person was not connected to the Event.

An invalidated participant remains preserved for provenance and audit.

It does not appear as a current Event participant.

Before an active participant is invalidated without replacement, every dependent active Role must be invalidated through the same coordinated, atomic or recoverable operation.

A dependent active Role must not remain active while pointing to the invalidated participant.

---

## 9.5 Superseded

Use:

```text
superseded
```

when another Event Participant record now represents the corrected, resolved, or consolidated relationship.

Typical cases include:

```text
unknown person → roster student
unknown person → Actor
descriptive person → Actor
descriptive person → roster student
wrong roster student → correct roster student
wrong Actor → correct Actor
duplicate records → one canonical participant
```

A superseded participant remains historically inspectable.

It no longer appears as the current canonical participant relationship.

Before supersession commits, each dependent active Role must either:

* be replaced by a successor Role referencing the replacement participant;
* or be invalidated when the relationship should not carry forward.

Existing Role records are never retargeted to another participant.

---

## 9.6 Allowed Transitions

The initial allowed transitions are:

| From       | To            | Meaning                                                         |
| ---------- | ------------- | --------------------------------------------------------------- |
| `proposed` | `active`      | Teacher confirmed the proposed subject                          |
| `proposed` | `invalidated` | Proposal was rejected without replacement                       |
| `proposed` | `superseded`  | A corrected participant replaced the proposal                   |
| `active`   | `invalidated` | Participant relationship was later rejected without replacement |
| `active`   | `superseded`  | A corrected or resolved participant replaced the active record  |

The following are terminal under ordinary workflows:

```text
invalidated
superseded
```

---

## 9.7 Prohibited Transitions

The following ordinary transitions are prohibited:

```text
active → proposed

invalidated → proposed
invalidated → active

superseded → proposed
superseded → active
```

A participant that entered accepted history must not return to an unreviewed state.

Invalidated and superseded records must not be silently restored.

A mistaken terminal transition requires a later explicit amendment mechanism.

---

## 9.8 Confirmation in Place

Use:

```text
proposed → active
```

when the teacher confirms that the proposed canonical subject is correct.

For example, a returned paper page proposes:

```json
{
  "participant_id": "ep_01j9...",
  "status": "proposed",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "english10_p2",
      "student_id": "1001"
    },
    "display_snapshot": {
      "display_name": "Jordan Lee"
    }
  }
}
```

When the teacher confirms Jordan Lee, the same participant record becomes active.

Portia must:

1. validate the subject reference;
2. create participant lifecycle history;
3. change `status` to `active`;
4. update `updated_at` and `updated_by`;
5. and refresh derived views.

The teacher-facing action may simply be:

```text
Confirm
```

No duplicate active participant record is needed.

---

## 9.9 Replacement When Identity Changes

A new participant record is required when the canonical identity claim changes materially.

The expected sequence is:

```text
create corrected participant
→ validate corrected participant
→ activate corrected participant
→ resolve every dependent Role
→ activate successor Roles or invalidate noncarried Roles
→ link corrected participant to prior participant
→ supersede prior participant
→ commit all related transitions
```

The participant and Role changes form one logical transaction.

The operation must be atomic or use recoverable staged writes.

When replacing the final active participant of an active Event, Portia must activate the correction before superseding the prior participant.

This prevents the Event from temporarily having no active participant.

It must also prevent any dependent Role from remaining active against the superseded participant.

---

## 9.10 Canonical Replacement Direction

The replacement participant owns the canonical forward relationship to the prior participant.

Conceptually:

```json
{
  "participant_id": "ep_corrected",
  "status": "active",
  "supersedes": [
    {
      "participant_id": "ep_original",
      "reason": "identity_resolved"
    }
  ]
}
```

The original participant receives:

```text
status = superseded
```

A `superseded_by` view is derived from replacement records.

The forward link may be an array because one corrected participant may consolidate several prior participant records.

---

## 9.11 Replacement Reasons

Initial replacement reasons should include:

```text
identity_resolved
identity_corrected
duplicate_consolidated
subject_variant_changed
participant_relationship_corrected
other
```

### `identity_resolved`

Previously uncertain identity becomes a durable reference.

Examples:

```text
unknown_person → roster_student
unknown_person → actor
```

### `identity_corrected`

The wrong durable identity was recorded.

Examples:

```text
wrong roster student → correct roster student
wrong Actor → correct Actor
```

### `duplicate_consolidated`

Several participant records are determined to represent the same person, and one becomes canonical.

### `subject_variant_changed`

The appropriate identity representation changes materially.

Examples:

```text
descriptive_person → actor
descriptive_person → roster_student
```

### `participant_relationship_corrected`

The participant representation requires replacement for another material relationship correction not captured by the preceding values.

---

## 9.12 Unknown-Person Resolution

An active unknown-person participant may remain unresolved indefinitely when that accurately represents what is known.

Portia must not require identity resolution merely to remove an unresolved item from a queue.

When identity is later resolved:

```text
create durable replacement participant
→ activate replacement
→ replacement supersedes unknown participant
```

The original unknown-person record remains preserved.

Portia can therefore show:

* what was originally known;
* when identity was resolved;
* which participant replaced the unresolved record;
* who recorded the resolution locally;
* and why the resolution occurred.

---

## 9.13 Descriptive Person to Actor or Student

Portia must not mutate a descriptive person directly into a roster student or Actor.

The explicit logical workflow is:

```text
select or create durable identity
→ create replacement participant
→ activate replacement
→ supersede descriptive participant
```

Creating an Actor remains a deliberate action.

Portia must not create an Actor automatically merely because the same descriptive label appears in several Events.

The teacher-facing interface may combine the logical workflow into a concise operation such as:

```text
Save this person as a recurring Actor
```

Portia remains responsible for producing the necessary canonical records and history.

---

## 9.14 Duplicate Participants

### Durable Subjects

Duplicate active roster-student participants are identified through:

```text
student_ref.class_id + student_ref.student_id
```

Duplicate active Actor participants are identified through:

```text
actor_id
```

Portia should normally prevent a duplicate from being activated.

When duplicates already exist, the teacher may select the canonical participant and consolidate the others.

Portia must review any child references, including role assignments, before completing consolidation.

References must not be silently redirected without provenance.

### Descriptive and Unknown Subjects

Similar labels or descriptions are insufficient for automatic consolidation.

Portia may warn that two records may describe the same person, but the teacher must decide whether they represent:

* the same person;
* different people;
* or unresolved ambiguity.

---

## 9.15 Participant Lifecycle History

Every participant transition creates a separate append-only lifecycle-history record.

Conceptually:

```json
{
  "schema_version": "1",
  "record_type": "event_participant_lifecycle_transition",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_01j9...",
  "participant_id": "ep_01j9...",
  "transition_id": "eplt_01j9...",
  "from_status": "proposed",
  "to_status": "active",
  "reason": {
    "type": "teacher_confirmed"
  },
  "changed_at": "2026-09-18T09:27:00-04:00",
  "changed_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

A reason is required for every transition.

Initial reason values should include:

```text
teacher_confirmed
false_paper_interpretation
incorrect_person
not_participant
duplicate_record
created_in_error
identity_resolved
identity_corrected
subject_variant_changed
other
```

The exact lifecycle-transition schema remains outside the two JSON Schemas required by the current issue.

---

## 9.16 Paper Review Workflow

A participant interpreted from paper ordinarily begins as:

```text
status = proposed
```

The teacher-facing review should support three primary actions:

```text
Confirm
Correct
Dismiss
```

### Confirm

```text
proposed → active
```

Use when the interpreted identity is correct.

### Correct

Portia allows the teacher to select the correct identity.

When the correction materially changes the canonical subject:

```text
create corrected participant
→ activate corrected participant
→ proposed participant becomes superseded
```

### Dismiss

```text
proposed → invalidated
```

Use when the paper interpretation was false or the person should not be connected to the Event.

The interface should permit rapid confirmation of several correct proposals together.

For example:

```text
Confirm all reviewed participants
```

may apply several valid transitions in one teacher action while still writing separate canonical lifecycle records.

---

## 9.17 Digital Workflow

Direct digital capture should prioritize the most common classroom path:

```text
select student
→ enter or choose occurrence
→ enter brief summary
→ save active Event
```

When all activation requirements are already satisfied, Portia may create the selected participant directly as active after explicit save or activation confirmation.

It does not need to force every manually selected participant through a visible proposed-review screen.

`proposed` is primarily useful for:

* uncertain interpretations;
* imported suggestions;
* paper capture;
* and incomplete entry.

Portia must not add review steps where the teacher has already made an explicit unambiguous selection.

---

## 9.18 Efficiency Requirements

Routine Event and participant workflows should satisfy the following design goals.

### Minimal Classroom Capture

A teacher circulating through the room should ordinarily be able to record an Event through:

* one participant mark or selection;
* one brief neutral note;
* and, when useful, one time, context, or follow-up mark.

The paper form must not require completion of every possible Portia field.

### Deferred Detail

Information not necessary for immediate capture or Event activation should remain optional and may be added later.

Portia must not require:

* participant roles;
* Classifications;
* Determinations;
* Responses;
* Outcomes;
* or detailed narratives

during initial capture.

### Batch Review

Returned-paper review should support efficient batching.

The teacher should be able to:

* move through several captured Events sequentially;
* confirm correct interpretations with one action;
* correct only the uncertain fields;
* use keyboard navigation;
* and activate several fully reviewed Events without reopening each record repeatedly.

### Contextual Defaults

Portia may preselect or suggest:

* the current class;
* the current date and time;
* commonly used location and instructional-context values;
* and frequently selected participant actions.

Suggested values require appropriate confirmation but should reduce repetitive entry.

### Progressive Disclosure

Advanced lifecycle, provenance, and correction details should appear only when needed.

Routine screens should not display every internal field or relationship.

### No Duplicate Entry

Portia must reuse valid known context and must not ask the teacher to re-enter:

* the selected class;
* the same student;
* the same paper route;
* creation-source information;
* local operator attribution;
* or values already confirmed during the workflow.

### Positive Utility

Portia workflows should produce teacher-facing value, such as:

* reminders for needed follow-up;
* concise student-support context;
* visibility into positive Events;
* recognition of useful patterns without merging Events;
* and evidence that supports better instructional or support decisions.

The purpose of collecting data is not collection itself.

A field or workflow step that creates teacher burden without a clear documentation, support, correction, or decision benefit should be omitted or deferred.

---

## 9.19 Validation Without Workflow Burden

Portia must enforce canonical validation internally.

The interface should translate validation errors into direct corrective guidance.

For example:

```text
Technical condition:
No active Event Participant exists.

Teacher-facing message:
Select or confirm at least one person before activating this Event.
```

The interface should not expose messages such as:

```text
Cross-record invariant EP-ACTIVE-001 failed.
```

except in diagnostic or developer views.

Where several automatic operations are required, Portia should perform them as one coordinated user action.

Participant invalidation and supersession validation must identify dependent Roles before committing the participant transition.

The interface should explain whether each Role will be:

* invalidated;
* replaced for the corrected participant;
* or left as a proposed review item that cannot become active unchanged.

Strong validation and low-friction interaction are complementary requirements rather than competing goals.

---

## 9.20 Participant Lifecycle Invariants

1. Participant statuses are `proposed`, `active`, `invalidated`, and `superseded`.
2. Proposed participants do not satisfy Event activation.
3. Active participants satisfy the participant requirement.
4. Only active participants may own active Roles.
5. Participant invalidation without replacement requires coordinated invalidation of dependent active Roles.
6. Participant supersession requires successor Roles for carried relationships or invalidation of Roles that do not carry forward.
7. Existing Role records are never retargeted to a replacement participant.
8. Participant and dependent-Role transitions are atomic or recoverable.
9. Proposed participants may be confirmed as active in place when identity is unchanged.
10. Material identity changes require replacement participant records.
11. Replacement participants own canonical `supersedes` links to prior participants.
12. Reverse `superseded_by` views are derived.
13. Invalidated and superseded participants are terminal under ordinary workflows.
14. Active participants do not return to proposed status.
15. Unknown participants may remain active without forced resolution.
16. Resolving unknown or descriptive participants preserves the original record.
17. Descriptive people are not automatically promoted to Actors.
18. Duplicate durable identities are detected through canonical references.
19. Descriptive and unknown participants are not consolidated automatically through text similarity.
20. Every transition preserves lifecycle history and local provenance.
21. Paper interpretations ordinarily begin as proposed.
22. Paper review supports direct Confirm, Correct, and Dismiss actions.
23. Digital entry does not require unnecessary proposed-state review after explicit teacher selection.
24. Internal lifecycle complexity must remain largely invisible during routine use.
25. Teachers do not manually manage opaque IDs, files, provenance records, or canonical relationship direction.
26. Routine capture requires only the information needed for useful documentation.
27. Optional detail is progressively disclosed rather than demanded initially.
28. Batch review and contextual defaults should reduce repetitive work.
29. Validation messages must describe the corrective teacher action.
30. Portia must not collect data merely because the schema can represent it.
31. Workflow burden must remain proportionate to the instructional or support value produced.

## 10. Creation Source and Local Provenance

### Decision

Event, Event Participant, and Event Participant Role records preserve provenance through:

```text
creation_source
created_at
created_by
updated_at
updated_by
```

These fields remain at the top level of each canonical record.

`creation_source` is a discriminated object that records how the record originally entered Portia.

`created_by` and `updated_by` are discriminated attribution objects that distinguish direct local-operator actions from automated Portia processes.

The initial creation-source types are:

```text
digital_entry
paper_capture
import
```

The initial attribution-agent types are:

```text
local_operator
system_process
```

All routine provenance values must be populated automatically.

Teachers must not be required to manage technical provenance fields manually.

---

## 10.1 Terminology Normalization

The canonical paper creation-source type is:

```text
paper_capture
```

Earlier illustrative references to:

```text
returned_paper
paper_quick_capture
```

should be interpreted as referring to the broader paper-capture workflow and should be replaced in the normative model and JSON Schemas by:

```text
paper_capture
```

The paper-capture `stage` field distinguishes:

```text
preallocated
ingested
```

This provides one consistent source vocabulary for both:

* records created before a page is printed;
* and records created from information returned through scanning.

---

## 10.2 Creation-Source Object

Every Event, Event Participant, and Event Participant Role requires a structured:

```text
creation_source
```

The object uses:

```text
type
```

as its discriminator.

Conceptually:

```text
creation_source
  oneOf:
    digital-entry source
    paper-capture source
    import source
```

Each source variant must:

* require its own relevant fields;
* reject fields belonging to other variants;
* reject unknown properties;
* and preserve how the record originally entered Portia.

Creation source does not establish:

* truth;
* accuracy;
* authorship of an Account;
* observation of the Event;
* institutional approval;
* or participant identity.

---

## 10.3 Digital Entry

Use:

```text
digital_entry
```

when the teacher explicitly creates the record through Portia’s digital interface.

```json
{
  "creation_source": {
    "type": "digital_entry"
  }
}
```

### Required Fields

```text
type
```

### Prohibited Fields

```text
stage
route_id
page_record_id
source_label
external_reference
```

### Rules

1. `type` must equal `digital_entry`.
2. No additional source fields are required.
3. Portia should populate the value automatically from the active workflow.
4. The teacher should not need to select `digital_entry` manually.

A record added digitally to an Event originally created through paper capture still has its own digital creation source.

For example:

```text
Event:
paper_capture / preallocated

participant added later:
digital_entry

Role added after that:
digital_entry
```

A Role added digitally to a paper-derived participant is also `digital_entry`.

Creation source belongs to each canonical record independently.

---

## 10.4 Paper Capture

Use:

```text
paper_capture
```

when the record originates through Portia’s generated-paper workflow.

A paper-capture source requires:

```text
type
stage
route_id
page_record_id
```

The shared paper-source vocabulary contains:

```text
preallocated
ingested
```

Not every canonical record type permits both stages.

Record-specific schemas must restrict the stage according to when that record can legitimately come into existence.

For Event Participant Role records:

```text
paper_capture
→ stage must equal ingested
```

---

## 10.5 Preallocated Paper Capture

Use:

```text
stage = preallocated
```

when the canonical record is created before the capture page is rendered.

This stage ordinarily applies to a draft Event root created before page rendering.

It must not be used for an Event Participant Role.

A blank role area or anticipated role selection on a generated page is page-template information, not a canonical Role assertion.

```json
{
  "creation_source": {
    "type": "paper_capture",
    "stage": "preallocated",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  }
}
```

The expected sequence is:

```text
generate Event ID
→ create draft Event root
→ create page record
→ persist route
→ render page
```

The source indicates that the Event was preallocated for paper capture.

It does not indicate:

* that the page was used;
* that the page was returned;
* that handwriting was recognized;
* that an occurrence was confirmed;
* or that the Event became active.

An unused preallocated Event remains a draft until it is cancelled through the accepted lifecycle workflow.

No equivalent preallocated Role exists in the initial model.

---

## 10.6 Ingested Paper Capture

Use:

```text
stage = ingested
```

when a canonical record is created from information returned through the paper workflow.

This stage applies to records created from returned-page processing, such as:

* proposed Event Participants;
* proposed Event Participant Roles;
* or other child records extracted after scanning.

For Event Participant Roles, `ingested` is the only valid paper-capture stage.

```json
{
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  }
}
```

An ingested record should ordinarily begin in an unconfirmed lifecycle state when teacher review is required.

For example:

```text
Event Participant:
status = proposed
creation_source.type = paper_capture
creation_source.stage = ingested
```

Ingestion does not establish that the interpreted value is correct.

The scan, mark interpretation, or handwriting extraction remains proposed until teacher confirmation.

The absence of a recognized or confirmed role mark creates no Role record.

---

## 10.7 Paper Route and Page References

Within a paper-capture source:

```text
route_id
```

identifies the persisted Core PDS2 route used to resolve the returned page.

```text
page_record_id
```

identifies the Portia page record associated with the generated capture page.

Both fields are required whenever the selected record-specific paper stage is valid.

For example:

```text
Event draft:
stage may be preallocated

Event Participant Role:
stage must be ingested
```

Portia must validate that:

1. the route exists;
2. the page record exists;
3. the route and page belong to the expected Event work context;
4. the Event’s owning class matches the routed class;
5. and the referenced page belongs to Portia.

A paper source must not use:

* a filename;
* an absolute filesystem path;
* a printed student name;
* or a scanned-image hash

as a substitute for the canonical route and page references.

---

## 10.8 Import

Use:

```text
import
```

when the record originates outside the ordinary Portia digital or paper workflows.

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record"
  }
}
```

An optional external reference may be included:

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": "import-batch-2026-09-01"
  }
}
```

### Required Fields

```text
type
source_label
```

### Optional Field

```text
external_reference
```

### Prohibited Fields

```text
stage
route_id
page_record_id
```

### Rules

1. `type` must equal `import`.
2. `source_label` must be meaningful nonempty text.
3. `external_reference`, when present, must be meaningful nonempty text.
4. The external reference is provenance rather than Portia identity.
5. Portia must not assume an imported record is reviewed or accurate.
6. Import workflows may create proposed or draft records requiring teacher review.

Import metadata should ordinarily be supplied once for an import operation and applied automatically to all created records.

---

## 10.9 Attribution-Agent Object

Every Event, Event Participant, and Event Participant Role requires:

```text
created_by
updated_by
```

Each field uses one discriminated attribution-agent object.

The initial agent types are:

```text
local_operator
system_process
```

Conceptually:

```text
attribution agent
  oneOf:
    local operator
    system process
```

The object records local operational attribution.

It does not establish:

* authenticated legal identity;
* institutional authorization;
* a verified electronic signature;
* exclusive device access;
* or authorship of the underlying Event information.

---

## 10.10 Local Operator

Use:

```text
local_operator
```

when a teacher or other locally represented operator directly initiates or confirms the canonical action.

```json
{
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

### Required Fields

```text
type
display_label
```

### Prohibited Fields

```text
process_id
```

### Rules

1. `type` must equal `local_operator`.
2. `display_label` must be meaningful nonempty text.
3. The label is a historical display snapshot.
4. The label is not a durable institutional identity.
5. No email address or organization-wide user ID is required in Portia v1.
6. The interface should populate the local operator automatically.

The local operator is not automatically:

* an Event Participant;
* an Account source;
* an observer;
* a Response provider;
* or the subject of a Determination.

Those relationships require explicit canonical records.

---

## 10.11 System Process

Use:

```text
system_process
```

when Portia creates or modifies a record through an automated process.

```json
{
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  }
}
```

### Required Fields

```text
type
process_id
```

### Prohibited Fields

```text
display_label
```

Initial process identifiers may include:

```text
paper_capture_ingest
import
migration
derived_repair
```

### Rules

1. `type` must equal `system_process`.
2. `process_id` must use a safe machine-readable identifier.
3. `process_id` must not contain arbitrary prose.
4. The identifier describes the process that performed the canonical operation.
5. Automated creation does not constitute teacher confirmation.
6. Later teacher confirmation should update the record with a local-operator attribution.

For example:

```text
created_by:
system_process / paper_capture_ingest

updated_by:
local_operator / Stephen Severino
```

This records that Portia created the proposal and the teacher later reviewed it.

---

## 10.12 Creation and Update Timestamps

Every Event, Event Participant, and Event Participant Role requires:

```text
created_at
updated_at
```

Both fields use timezone-aware ISO 8601 timestamps with explicit offsets.

Example:

```json
{
  "created_at": "2026-09-18T09:22:00-04:00",
  "updated_at": "2026-09-18T09:27:00-04:00"
}
```

Valid forms include:

```text
2026-09-18T09:22:00-04:00
2026-12-18T09:22:00-05:00
2026-09-18T13:22:00Z
```

A timestamp without an offset is invalid:

```text
2026-09-18T09:22:00
```

At initial creation:

```text
updated_at = created_at
updated_by = created_by
```

On every canonical update:

* `updated_at` is replaced with the update timestamp;
* `updated_by` is replaced with the current attribution agent;
* `created_at` remains unchanged;
* and `created_by` remains unchanged.

Application validation must confirm:

```text
updated_at >= created_at
```

JSON Schema validates timestamp format but may not reliably enforce chronological ordering.

---

## 10.13 Immutable Creation Facts

The following fields are ordinarily immutable:

```text
creation_source
created_at
created_by
```

They describe how, when, and through which local agent or process the record originally entered Portia.

For example, a paper-ingested participant or Role remains paper-ingested even after the teacher corrects or confirms it digitally.

```text
creation_source:
paper_capture / ingested

updated_by:
local_operator
```

Portia must not change the creation source to `digital_entry` merely because later edits occur digitally.

If creation provenance itself was recorded incorrectly, the correction must preserve the prior value through the accepted amendment or history mechanism.

---

## 10.14 Mutable Update Facts

The following fields change through ordinary canonical updates:

```text
updated_at
updated_by
```

Examples of canonical updates include:

* editing an Event summary;
* confirming a proposed participant;
* correcting occurrence information;
* adding a supersession relationship;
* changing lifecycle status;
* or correcting location or instructional context.

`updated_at` and `updated_by` identify the most recent canonical mutation.

They do not replace:

* lifecycle-transition history;
* amendment history;
* identity-resolution history;
* or field-level correction history.

---

## 10.15 No Duplicate Review Fields

Event, Event Participant, and Event Participant Role records should not add:

```text
reviewed_at
reviewed_by
confirmed_at
confirmed_by
```

Teacher review and confirmation are already represented through:

* lifecycle transition records;
* current lifecycle status;
* `updated_at`;
* and `updated_by`.

For example, confirming a paper-derived participant or Role produces:

```text
record status:
active

lifecycle transition:
proposed → active

transition reason:
teacher_confirmed

updated_by:
local_operator
```

Adding separate confirmation fields would duplicate the same facts and create a risk of disagreement.

Specialized review records may later exist when they represent a distinct workflow rather than ordinary lifecycle confirmation.

---

## 10.16 Record-Specific Creation Sources

Creation source is recorded independently for every canonical record.

It must not be inherited implicitly from the parent Event, referenced Event Participant, source record, or superseded record.

For example:

```text
Event:
paper_capture / preallocated

first participant:
paper_capture / ingested

second participant added later:
digital_entry

Role proposed from the returned page:
paper_capture / ingested

pre-render Role:
not created

Role added later by the teacher:
digital_entry
```

Similarly:

```text
imported Event:
import

imported participant:
import

teacher-added contextual Role:
digital_entry
```

A successor Role also records its own source:

```text
prior Role:
paper_capture / ingested

digitally created successor:
digital_entry
```

The `supersedes` relationship preserves lineage.

The successor’s `creation_source` preserves its own origin.

This record-level independence preserves how each canonical record actually entered Portia.

It does not authorize a paper stage that is semantically impossible for a particular record type.

---

## 10.17 Paper Workflow Example

Before class, Portia creates a draft Event:

```json
{
  "status": "draft",
  "creation_source": {
    "type": "paper_capture",
    "stage": "preallocated",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "created_at": "2026-09-18T07:41:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  },
  "updated_at": "2026-09-18T07:41:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

Before scanning, the draft Event exists, but no Role record exists merely because the page contains blank role marks.

After scanning, Portia proposes a participant and may propose one or more Role records from the same returned page.

The participant and each proposed Role receive their own paper-ingested creation source.

No Role in this workflow uses `stage = preallocated`.

Participant example:

```json
{
  "status": "proposed",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "created_at": "2026-09-18T10:05:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-18T10:05:00-04:00",
  "updated_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  }
}
```

A proposed Role created from the same page would independently contain both its paper creation source and its matching paper basis:

```json
{
  "status": "proposed",
  "role_type": "present",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_0123456789abcdef0123456789abcdef",
      "page_record_id": "pg_01j9..."
    }
  ],
  "created_at": "2026-09-18T10:05:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-18T10:05:00-04:00",
  "updated_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  }
}
```

A proposed paper-derived `reported_involved` Role may initially contain only its matching paper basis.

Before activation, the review workflow must create or select a same-Event attributed Account and append:

```json
{
  "kind": "account_ref",
  "record_id": "acct_01j9..."
}
```

to the Role’s basis.

The Account remains the canonical attributed report. The Role does not copy the Account content.

After teacher confirmation, the participant or Role may become active:

```json
{
  "status": "active",
  "created_at": "2026-09-18T10:05:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-18T10:08:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Stephen Severino"
  }
}
```

The original creation provenance remains unchanged.

The participant or Role lifecycle transition separately records the teacher confirmation.

Each confirmed record retains its own paper-ingested creation source.

A confirmed Role also retains the matching paper basis. The status change does not remove or rewrite either relationship.

---

## 10.18 Teacher-Facing Workflow

Provenance fields must ordinarily be populated without teacher entry.

The teacher should not need to:

* choose a creation-source type;
* choose a paper-capture stage;
* enter a route ID;
* enter a page-record ID;
* type their attribution label repeatedly;
* choose a system-process ID;
* enter timestamps;
* or determine whether a record was preallocated or ingested.

Teacher-facing displays may translate technical provenance into concise language such as:

```text
Created digitally
Captured on paper
Imported from legacy records
Proposed from scanned page
Confirmed by you
Last updated by you
```

Full technical provenance should remain available in detail, audit, or diagnostic views.

---

## 10.19 Efficiency Requirements

Provenance rigor must not increase routine teacher workload.

Portia must:

1. infer creation source from the active workflow;
2. resolve route and page references automatically;
3. populate timestamps automatically;
4. populate local attribution automatically;
5. identify system processes automatically;
6. preserve immutable creation facts without prompting;
7. update modification provenance as part of the same teacher action;
8. and write lifecycle history without requiring a separate confirmation step.

For example, one teacher action:

```text
Confirm participant
```

may internally perform:

```text
validate participant
→ create lifecycle transition
→ change proposed to active
→ update updated_at
→ update updated_by
→ refresh derived views
```

The teacher experiences one action rather than five administrative steps.

---

## 10.20 Schema Requirements

The current Event and Event Participant schemas, and the future Event Participant Role schema, should define equivalent reusable structures for:

```text
creation_source
created_by
updated_by
```

Unless a shared schema file is introduced later, the structures may be duplicated consistently in:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json
```

The Role schema must require its own creation source rather than relying on a parent record.

### Creation Source

The schema should use `oneOf` with three mutually exclusive branches:

```text
digital_entry
paper_capture
import
```

The shared `paper_capture` branch requires:

```text
stage
route_id
page_record_id
```

The common stage vocabulary is:

```text
preallocated
ingested
```

Each record schema must narrow that vocabulary according to the record’s lifecycle semantics.

The Event Participant Role schema must constrain:

```text
creation_source.type = paper_capture
→ creation_source.stage = ingested
```

and reject:

```text
creation_source.stage = preallocated
```

It must also conditionally require:

```text
creation_source.type = paper_capture
→ basis contains at least one paper_capture entry
```

For reported involvement, it must additionally require:

```text
role_type = reported_involved
AND status = active or superseded
→ basis contains at least one account_ref
```

This rule applies to digital, paper, and import creation sources.

The schema can enforce the presence and shape of those entries.

Application validation must enforce exact equality between:

```text
creation_source.route_id
basis[matching paper entry].route_id
```

and:

```text
creation_source.page_record_id
basis[matching paper entry].page_record_id
```

The `import` branch must require:

```text
source_label
```

and optionally permit:

```text
external_reference
```

### Attribution Agent

The schema should use `oneOf` with two mutually exclusive branches:

```text
local_operator
system_process
```

The local-operator branch must require:

```text
display_label
```

The system-process branch must require:

```text
process_id
```

Each branch should reject fields belonging to the other branch.

### Timestamps

The schema should require:

```text
created_at
updated_at
```

as timezone-aware date-time strings.

Application validation must enforce:

* `updated_at` does not precede `created_at`;
* immutable creation facts are not changed through ordinary editing;
* referenced paper routes and pages exist;
* record-specific paper-stage eligibility;
* a matching paper basis for every paper-derived Event Participant Role;
* exact route and page equality between Role creation source and matching basis;
* an attributed same-Event Account before any `reported_involved` activation;
* preservation of that Account reference after effective activation;
* persistence of the matching basis through later lifecycle states;
* no pre-render or blank Event Participant Role creation;
* and system-process IDs are recognized where required.

---

## 10.21 Creation-Source and Provenance Invariants

1. Every Event, Event Participant, and Event Participant Role records its own creation source.
2. Creation source is a discriminated object.
3. Initial source types are `digital_entry`, `paper_capture`, and `import`.
4. `paper_capture` replaces earlier inconsistent paper-source terminology.
5. Paper capture distinguishes `preallocated` from `ingested`.
6. Paper-stage eligibility is record-type-specific.
7. Event Participant Roles permit only `paper_capture / ingested`.
8. Event Participant Roles prohibit `paper_capture / preallocated`.
9. Blank generated role marks do not create canonical Role records.
10. Every paper-derived Event Participant Role contains a matching paper basis.
11. The matching basis route and page references equal the Role creation-source references.
12. Creation source and matching basis remain semantically distinct despite referencing the same artifact.
13. Lifecycle review does not remove the matching paper basis.
14. Paper or import basis may preserve a proposed `reported_involved` assertion.
15. Every active `reported_involved` Role requires an attributed same-Event Account.
16. The active Account requirement is independent from digital, paper, or import origin.
17. The Account remains a separate canonical record from the Role.
18. Lifecycle history preserves the Account reference after effective activation.
19. Preallocated paper records exist before page rendering.
20. Ingested paper records originate from returned-page processing.
21. Both paper stages require route and page-record references.
22. Paper ingestion does not establish teacher confirmation.
23. Imported records preserve a meaningful source label.
24. Every Event, Event Participant, and Event Participant Role records creation and update attribution.
25. Attribution distinguishes local operators from system processes.
26. Local-operator labels are historical snapshots rather than institutional identity.
27. System-process IDs describe automated canonical operations.
28. Creation timestamps and attribution are immutable.
29. Creation source is ordinarily immutable.
30. Update timestamps and attribution change through canonical mutations.
31. At creation, update provenance equals creation provenance.
32. Occurrence time remains separate from provenance timestamps.
33. Lifecycle history remains separate from update provenance.
34. No duplicate root-level review or confirmation fields are required.
35. Parent and child records may have different creation sources.
36. A Role source is not inherited from its Event or Event Participant.
37. A successor Role records its own source rather than inheriting the prior Role source.
38. Creation source remains distinct from assertion basis.
39. Paper-derived records remain paper-derived after digital confirmation.
40. Imported records remain imported after digital review.
41. Provenance fields are populated automatically.
42. Teachers do not manage route IDs, process IDs, timestamps, or technical source stages manually.
43. Schema validation enforces discriminated object shapes.
44. Application validation enforces reference existence, chronology, source-workflow consistency, and immutability.
45. Internal provenance rigor must not create additional routine teacher steps.
