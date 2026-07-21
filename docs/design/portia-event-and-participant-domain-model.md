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
* provenance;
* creation source;
* evidentiary or documentary basis;
* correction history;
* and supersession relationships.

Adding, correcting, or invalidating a role must not require rewriting the participant’s canonical subject identity.

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

when one or more sources describe the person as involved, but Portia is not presenting that relationship as independently established.

This role preserves the distinction between:

```text
a reported relationship
```

and:

```text
a relationship accepted as directly established
```

A `reported_involved` assignment should ordinarily identify the Account, imported source, or other record providing the basis for the claim.

For example:

```json
{
  "role_type": "reported_involved",
  "basis": {
    "kind": "account_ref",
    "record_id": "acct_01j9..."
  }
}
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

A contextual assignment should include a concise neutral explanation.

For example:

```json
{
  "role_type": "contextual",
  "detail": "Participated in the immediate class-related conference."
}
```

The detail must not become:

* an Account;
* an allegation;
* a finding;
* or a narrative of the Event.

---

## 7.8 Cardinality

One Event Participant may have several role assignments.

For example:

```text
present
directly_involved
```

may both apply when the participant was present throughout the context and also acted directly within it.

Similarly:

```text
reported_involved
```

may later be followed by:

```text
directly_involved
```

when additional reviewed information supports a more direct relationship.

Portia must preserve the history of those assignments rather than silently rewriting the earlier role.

No role is required when:

* the participant’s relationship is not yet clear;
* paper capture identified a person but not a role;
* imported data lacks reliable role information;
* or assigning a role would require unsupported inference.

---

## 7.9 Recommended Role Record Envelope

A future canonical Event Participant Role record should contain:

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

Depending on the role, it may also contain:

```text
basis
detail
superseded_by
replacement_reason
```

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

## 7.12 Role Status

The initial role-assignment lifecycle should support:

```text
proposed
active
invalidated
superseded
```

### `proposed`

The role has been suggested but not confirmed.

Typical sources include:

* paper interpretation;
* imported data;
* automated extraction;
* or incomplete teacher review.

### `active`

The role is currently accepted as a valid neutral relationship.

### `invalidated`

The role assignment was incorrect, unsupported, duplicated, or otherwise should not be treated as valid.

### `superseded`

A later role assignment replaces or refines the earlier assignment.

Only active role records should appear as current Event-level participant roles.

No role status affects whether the participant identity itself remains valid.

---

## 7.13 Basis

A role assignment may contain a structured `basis` describing why the role was assigned.

The initial basis kinds should include:

```text
teacher_entry
account_ref
observation_ref
returned_paper
import_source
```

### Teacher Entry

```json
{
  "basis": {
    "kind": "teacher_entry"
  }
}
```

The teacher assigned the neutral relationship directly during review or entry.

### Account Reference

```json
{
  "basis": {
    "kind": "account_ref",
    "record_id": "acct_01j9..."
  }
}
```

An attributed Account supports the role assignment.

This basis is ordinarily expected for:

```text
reported_involved
```

### Observation Reference

```json
{
  "basis": {
    "kind": "observation_ref",
    "record_id": "obs_01j9..."
  }
}
```

An Observation supports the role assignment.

The Observation remains canonical evidence. The role record does not copy its contents.

### Returned Paper

```json
{
  "basis": {
    "kind": "returned_paper",
    "route_id": "rt_0123456789abcdef0123456789abcdef",
    "page_record_id": "pg_01j9..."
  }
}
```

A paper capture proposed the relationship.

Such an assignment should ordinarily begin as `proposed`.

### Import Source

```json
{
  "basis": {
    "kind": "import_source",
    "source_label": "Legacy teacher record"
  }
}
```

An imported source supplied the relationship.

A basis records provenance for the role claim.

It does not establish that the underlying source is correct or authoritative.

---

## 7.14 Creation Source and Basis Are Distinct

`creation_source` describes how the role record entered Portia.

`basis` describes what supports the role relationship.

For example:

```text
creation source:
digital entry

basis:
student Account
```

means the teacher created the role digitally after reviewing a student Account.

Likewise:

```text
creation source:
returned paper

basis:
returned paper capture
```

means the role was proposed through a scanned quick-capture page.

Portia must not collapse these concepts into one field.

---

## 7.15 Duplicate Role Assignments

Within one Event Participant, Portia should permit no more than one active role assignment with the same:

```text
role_type
```

For example, two active:

```text
present
```

records for the same participant are duplicates.

Portia may preserve earlier invalidated or superseded assignments for history.

Different active role types may coexist when they are meaningfully applicable.

Duplicate validation must use:

```text
participant_id + role_type
```

within the Event.

---

## 7.16 Corrections and Refinement

A role may be corrected or refined without changing participant identity.

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

The expected correction pattern is:

```text
preserve original role record
→ create replacement role record when needed
→ activate replacement
→ invalidate or supersede original
```

Portia must preserve:

* the original role assignment;
* the later assignment;
* the relationship between them;
* the correction timestamp;
* local operator attribution;
* and the reason for correction or refinement.

A role correction does not ordinarily require:

* a new Event;
* a new Event Participant;
* or mutation of the participant’s subject identity.

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

## 7.19 Paper Quick Capture

A Portia quick-capture page may include optional neutral role marks such as:

```text
Directly involved
Present
Reported involved
Other context
```

The printed page does not need to require a role selection.

After scanning:

* recognized role marks become proposed role assignments;
* ambiguous marks remain unresolved review items;
* an unmarked role area creates no role assignment;
* and no paper-derived role becomes active automatically.

The teacher must be able to:

* confirm the proposed role;
* choose another neutral role;
* add more than one applicable role;
* leave the participant without a role;
* or discard the interpretation.

Paper capture must not offer prohibited judgment labels merely for convenience.

---

## 7.20 Derived Views

Current participant-role views must use active canonical role records.

Portia may derive views such as:

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

Historical views may display invalidated or superseded role assignments when the teacher requests an audit or correction history.

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
* valid creation-source variants;
* valid basis variants;
* identifier patterns;
* timestamp formats;
* and rejection of unknown properties.

Application validation must additionally confirm:

* parent Event existence;
* parent participant existence;
* matching Event ownership;
* valid referenced Account or Observation records;
* no duplicate active role type for one participant;
* correct lifecycle transitions;
* and provenance-preserving correction links.

---

## 7.22 Event Participant Role Invariants

1. Participant identity and Event-level role are separate canonical records.
2. Event Participant records contain no authoritative embedded role or roles array.
3. One participant may have zero, one, or several role assignments.
4. No role assignment is required for Event activation.
5. A participant without a role remains a valid participant.
6. Role assignments use independent opaque identities.
7. Every role assignment references one Event Participant.
8. Role assignments do not point directly to students, Actors, or descriptive subjects.
9. Initial Event-level roles use neutral language.
10. `directly_involved` does not indicate responsibility or fault.
11. `present` does not assert observation or direct involvement.
12. `reported_involved` remains visibly qualified as reported.
13. `contextual` should include concise clarification and be used sparingly.
14. One participant may hold several compatible role types.
15. Only active role assignments appear as current roles.
16. Paper- or import-derived roles may begin as proposed.
17. Paper-derived roles require teacher confirmation.
18. An unmarked paper role area creates no assignment.
19. Creation source and documentary basis remain distinct.
20. Account, Observation, Response, Support, Follow-Up, and Determination relationships remain canonical in their own record types.
21. Responsibility and judgment labels are prohibited from the neutral role vocabulary.
22. Duplicate active role types for one participant are prohibited.
23. Corrections preserve prior role records and provenance.
24. Role changes do not mutate participant identity.
25. Event activation does not depend on role assignment.
26. The current Event Participant JSON Schema must remain compatible with separate future role records.

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
3. Status describes record lifecycle rather than behavior severity or responsibility.
4. Draft Events may be incomplete.
5. Draft Events do not appear as accepted Events in ordinary histories.
6. Activation requires successful application-level validation.
7. Active Events require at least one active Event Participant.
8. Event Participant Roles are not required for activation.
9. Active status does not mean the classroom situation remains ongoing.
10. Closed Events remain valid historical Events.
11. Closure does not establish a finding or Outcome.
12. Closed Events may be reopened with an explicit reason.
13. Reopening must not absorb a later bounded occurrence.
14. Cancellation applies only to Events that were never active.
15. Unused paper drafts should be cancelled rather than closed.
16. Invalidation means the Event itself is no longer treated as valid.
17. Correctable field or participant errors do not automatically require Event invalidation.
18. Supersession replaces an Event with one or more canonical Events.
19. Replacement Events own canonical `supersedes` relationships to prior Events.
20. Reverse `superseded_by` views are derived.
21. Cancelled, invalidated, and superseded Events are terminal under ordinary workflows.
22. Active or closed Events never return to draft.
23. Previously active Events never become cancelled.
24. Every transition preserves a reason and local provenance.
25. Every transition creates an append-only lifecycle-history record.
26. Root `status` and lifecycle history must remain consistent.
27. `updated_at` and `updated_by` do not replace lifecycle history.
28. Paper return or scan interpretation cannot activate an Event automatically.
29. Schema validation enforces the status vocabulary.
30. Application validation enforces transition legality and cross-record requirements.

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
* may receive Event Participant Role assignments;
* and may be referenced by Accounts, Observations, Responses, or later Portia records.

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
→ link corrected participant to prior participant
→ supersede prior participant
```

When replacing the final active participant of an active Event, Portia must activate the correction before superseding the prior participant.

This prevents the Event from temporarily having no active participant.

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

Strong validation and low-friction interaction are complementary requirements rather than competing goals.

---

## 9.20 Participant Lifecycle Invariants

1. Participant statuses are `proposed`, `active`, `invalidated`, and `superseded`.
2. Proposed participants do not satisfy Event activation.
3. Active participants satisfy the participant requirement.
4. Proposed participants may be confirmed as active in place when identity is unchanged.
5. Material identity changes require replacement participant records.
6. Replacement participants own canonical `supersedes` links to prior participants.
7. Reverse `superseded_by` views are derived.
8. Invalidated and superseded participants are terminal under ordinary workflows.
9. Active participants do not return to proposed status.
10. Unknown participants may remain active without forced resolution.
11. Resolving unknown or descriptive participants preserves the original record.
12. Descriptive people are not automatically promoted to Actors.
13. Duplicate durable identities are detected through canonical references.
14. Descriptive and unknown participants are not consolidated automatically through text similarity.
15. Every transition preserves lifecycle history and local provenance.
16. Paper interpretations ordinarily begin as proposed.
17. Paper review supports direct Confirm, Correct, and Dismiss actions.
18. Digital entry does not require unnecessary proposed-state review after explicit teacher selection.
19. Internal lifecycle complexity must remain largely invisible during routine use.
20. Teachers do not manually manage opaque IDs, files, provenance records, or canonical relationship direction.
21. Routine capture requires only the information needed for useful documentation.
22. Optional detail is progressively disclosed rather than demanded initially.
23. Batch review and contextual defaults should reduce repetitive work.
24. Validation messages must describe the corrective teacher action.
25. Portia must not collect data merely because the schema can represent it.
26. Workflow burden must remain proportionate to the instructional or support value produced.

## 10. Creation Source and Local Provenance

### Decision

Event and Event Participant records preserve provenance through:

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

Every Event and Event Participant requires a structured:

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
```

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

The supported stages are:

```text
preallocated
ingested
```

---

## 10.5 Preallocated Paper Capture

Use:

```text
stage = preallocated
```

when the canonical record is created before the capture page is rendered.

This stage ordinarily applies to a draft Event root.

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

---

## 10.6 Ingested Paper Capture

Use:

```text
stage = ingested
```

when a canonical record is created from information returned through the paper workflow.

This stage ordinarily applies to records such as:

* proposed Event Participants;
* proposed Event Participant Roles;
* or other child records extracted after scanning.

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

Both fields are required for:

```text
stage = preallocated
stage = ingested
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

Every Event and Event Participant requires:

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

Every Event and Event Participant requires:

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

For example, a paper-ingested participant remains paper-ingested even after the teacher corrects or confirms it digitally.

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

The Event and Event Participant roots should not add:

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

For example, confirming a paper-derived participant produces:

```text
participant status:
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

It must not be inherited implicitly from the parent Event.

For example:

```text
Event:
paper_capture / preallocated

first participant:
paper_capture / ingested

second participant added later:
digital_entry
```

Similarly:

```text
imported Event:
import

teacher-added participant:
digital_entry
```

This preserves the actual origin of each record.

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

After scanning, Portia proposes a participant:

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

After teacher confirmation:

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

The participant lifecycle transition separately records the teacher confirmation.

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

Both required JSON Schemas should define equivalent reusable structures for:

```text
creation_source
created_by
updated_by
```

Unless a shared schema file is introduced later, the structures may initially be duplicated consistently in:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
```

### Creation Source

The schema should use `oneOf` with three mutually exclusive branches:

```text
digital_entry
paper_capture
import
```

The `paper_capture` branch must require:

```text
stage
route_id
page_record_id
```

and constrain `stage` to:

```text
preallocated
ingested
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
* and system-process IDs are recognized where required.

---

## 10.21 Creation-Source and Provenance Invariants

1. Every Event and Event Participant records its own creation source.
2. Creation source is a discriminated object.
3. Initial source types are `digital_entry`, `paper_capture`, and `import`.
4. `paper_capture` replaces earlier inconsistent paper-source terminology.
5. Paper capture distinguishes `preallocated` from `ingested`.
6. Preallocated paper records exist before page rendering.
7. Ingested paper records originate from returned-page processing.
8. Both paper stages require route and page-record references.
9. Paper ingestion does not establish teacher confirmation.
10. Imported records preserve a meaningful source label.
11. Every Event and Event Participant records creation and update attribution.
12. Attribution distinguishes local operators from system processes.
13. Local-operator labels are historical snapshots rather than institutional identity.
14. System-process IDs describe automated canonical operations.
15. Creation timestamps and attribution are immutable.
16. Creation source is ordinarily immutable.
17. Update timestamps and attribution change through canonical mutations.
18. At creation, update provenance equals creation provenance.
19. Occurrence time remains separate from provenance timestamps.
20. Lifecycle history remains separate from update provenance.
21. No duplicate root-level review or confirmation fields are required.
22. Parent and child records may have different creation sources.
23. Paper-derived records remain paper-derived after digital confirmation.
24. Provenance fields are populated automatically.
25. Teachers do not manage route IDs, process IDs, timestamps, or technical source stages manually.
26. Schema validation enforces discriminated object shapes.
27. Application validation enforces reference existence, chronology, and immutability.
28. Internal provenance rigor must not create additional routine teacher steps.
