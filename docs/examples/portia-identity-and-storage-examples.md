# Portia Identity and Storage Examples

These synthetic examples illustrate the identity, ownership, and storage decisions established in:

* [`docs/design/portia-identity-and-storage.md`](../design/portia-identity-and-storage.md)
* [`docs/decisions/0004-define-portia-identity-ownership-and-storage.md`](../decisions/0004-define-portia-identity-ownership-and-storage.md)

The JSON fragments are illustrative rather than final domain schemas.

All names, identifiers, classes, Events, Supports, and Actors are synthetic.

## Common Workspace Context

The examples use one teacher-controlled Paper Data Suite workspace containing these Core classes:

```text
classes/
  english10_p2/
    class.json
    roster.csv

  english10_p5/
    class.json
    roster.csv

  english11_p3/
    class.json
    roster.csv
```

Example roster-qualified student references include:

```text
english10_p2 + stu_1001
english10_p2 + stu_1014
english10_p5 + stu_2047
english11_p3 + stu_3102
```

The same textual `student_id` appearing in another roster would not automatically establish that the entries represent the same person.

---

## Example 1: One-Class Event

### Scenario

During English 10 Period 2, the teacher records a positive Event involving one student from that class.

### Canonical Work Root

```text
classes/english10_p2/modules/portia/work/evt_01hx7m2k/
```

### Storage

```text
evt_01hx7m2k/
  work.json

  records/
    event_participant/
      ep_01hx7m3a.json

    observation/
      obs_01hx7m4c.json

  history/
    chg_01hx7m5d.json
```

### Event Manifest

```json
{
  "schema_version": "1",
  "module_id": "portia",
  "work_kind": "event",
  "work_id": "evt_01hx7m2k",
  "owning_class_id": "english10_p2",
  "occurred_at": "2026-09-18T09:14:00-04:00",
  "status": "active"
}
```

### Event Participant

```json
{
  "record_kind": "event_participant",
  "record_id": "ep_01hx7m3a",
  "event_id": "evt_01hx7m2k",
  "subject": {
    "kind": "roster_student",
    "class_id": "english10_p2",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Avery Chen"
  }
}
```

### Result

The Event:

* has one owning class;
* has one canonical work root;
* refers to the student through `class_id + student_id`;
* and does not create a student dossier or duplicate roster record.

---

## Example 2: Cross-Class Event

### Scenario

An Event occurs during English 10 Period 2.

One participant belongs to the English 10 Period 2 roster. Another belongs to the teacher’s English 10 Period 5 roster.

Because the Event occurred during Period 2, `english10_p2` owns it.

### Canonical Work Root

```text
classes/english10_p2/modules/portia/work/evt_01hy2b7n/
```

No duplicate Event is created beneath `english10_p5`.

### Storage

```text
evt_01hy2b7n/
  work.json

  records/
    event_participant/
      ep_01hy2b81.json
      ep_01hy2b92.json

    account/
      acct_01hy2ba3.json
```

### Owning-Class Participant

```json
{
  "record_kind": "event_participant",
  "record_id": "ep_01hy2b81",
  "event_id": "evt_01hy2b7n",
  "subject": {
    "kind": "roster_student",
    "class_id": "english10_p2",
    "student_id": "stu_1014"
  },
  "display_snapshot": {
    "display_name": "Jordan Ellis"
  }
}
```

### Cross-Class Participant

```json
{
  "record_kind": "event_participant",
  "record_id": "ep_01hy2b92",
  "event_id": "evt_01hy2b7n",
  "subject": {
    "kind": "roster_student",
    "class_id": "english10_p5",
    "student_id": "stu_2047"
  },
  "display_snapshot": {
    "display_name": "Morgan Patel"
  }
}
```

### Result

The Event has:

```text
Owning class:
english10_p2

Participants:
english10_p2 + stu_1014
english10_p5 + stu_2047
```

The Period 5 student is linked explicitly from that student’s source roster.

The cross-class participant:

* does not change Event ownership;
* does not cause the Event to be copied;
* and does not require a synthetic combined class.

---

## Example 3: Support Process Linked to Events in Two Classes

### Scenario

The teacher creates a Support Process owned by `english10_p2`.

The Support Process is informed by:

* an Event owned by `english10_p2`;
* and a second Event owned by `english10_p5`.

### Canonical Support Root

```text
classes/english10_p2/modules/portia/work/sup_01j02c4p/
```

### Referenced Events

```text
classes/english10_p2/modules/portia/work/evt_01hx7m2k/
classes/english10_p5/modules/portia/work/evt_01j01z8r/
```

### Storage

```text
sup_01j02c4p/
  work.json

  records/
    planned_action/
      act_01j02c5q.json

    follow_up/
      fu_01j02c6r.json

    work_relationship/
      rel_01j02c7s.json
      rel_01j02c8t.json
```

### Relationship to the Period 2 Event

```json
{
  "record_kind": "work_relationship",
  "record_id": "rel_01j02c7s",
  "source": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "sup_01j02c4p",
    "work_kind": "support_process"
  },
  "target": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "evt_01hx7m2k",
    "work_kind": "event"
  },
  "relationship": "informed_by_event",
  "status": "active"
}
```

### Relationship to the Period 5 Event

```json
{
  "record_kind": "work_relationship",
  "record_id": "rel_01j02c8t",
  "source": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "sup_01j02c4p",
    "work_kind": "support_process"
  },
  "target": {
    "module_id": "portia",
    "class_id": "english10_p5",
    "work_id": "evt_01j01z8r",
    "work_kind": "event"
  },
  "relationship": "informed_by_event",
  "status": "active"
}
```

### Result

The Support Process owns both canonical relationship records.

When either Event is displayed, Portia may derive:

```text
Linked Support Process:
sup_01j02c4p
```

The Events do not store separate editable reverse links.

---

## Example 4: Recurring Non-Roster Actor

### Scenario

A counselor participates repeatedly in Events, Support Processes, Communications, and Follow-Ups across several classes.

The teacher creates one reusable Actor record.

### Canonical Actor Record

```text
portia/actors/actr_01j15d9v.json
```

### Actor Data

```json
{
  "schema_version": "1",
  "record_type": "portia_actor",
  "actor_id": "actr_01j15d9v",
  "display_name": "Riley Thompson",
  "actor_type": "school_staff",
  "role_labels": [
    "counselor"
  ],
  "status": "active"
}
```

### Work-Specific Reference

A Communication beneath a Support Process may contain:

```json
{
  "record_kind": "communication",
  "record_id": "comm_01j15da6",
  "actor_ref": {
    "actor_id": "actr_01j15d9v"
  },
  "display_snapshot": {
    "display_name": "Riley Thompson"
  },
  "relationship": "consulted_counselor"
}
```

### Result

The Actor record identifies the recurring person.

The Communication record identifies the person’s role in this particular workflow.

Updating the Actor’s current name, title, or contact details does not rewrite the historical display snapshot.

The counselor is not:

* added to a class roster;
* stored separately beneath each class;
* or represented as an authenticated institutional user.

---

## Example 5: Unidentified Outside Person

### Scenario

A student reports that an unidentified student from another teacher’s class was present during an Event.

The person cannot be resolved through any roster available in the teacher’s workspace and is unlikely to recur in Portia workflows.

### Canonical Event Record

```text
classes/english10_p2/modules/portia/work/evt_01j21f4w/
```

### Descriptive Source or Contextual Actor

```json
{
  "source": {
    "kind": "descriptive_person",
    "source_type": "external_person",
    "source_role": "student_from_another_teacher",
    "display_label": "Unidentified student",
    "actor_id": null
  }
}
```

### Result

Portia does not create:

* a student record;
* an Actor record;
* a temporary class;
* an invented `student_id`;
* or a synthetic Event Participant.

The person remains part of the Event context without receiving unsupported durable identity.

A later reviewed operation could link the descriptive person to a valid Actor or roster reference if trustworthy identity information becomes available.

Portia must not make that conversion automatically.

---

## Example 6: Cross-Year Successor Support Process

### Scenario

A Support Process begins while the student is in English 10 Period 2 during the 2026–2027 school year.

The support remains useful when the teacher later teaches the student in English 11 Period 3 during the 2027–2028 school year.

Portia does not move or indefinitely extend the prior-year Support Process.

It creates a successor.

### Prior Support

```text
classes/english10_p2/modules/portia/work/sup_01j30g5x/
```

Its original class metadata identifies the 2026–2027 school year.

### Successor Support

```text
classes/english11_p3/modules/portia/work/sup_01k40h6y/
```

Its owning class provides the new instructional and school-year context.

### Canonical Successor Relationship

The successor Support Process stores the explicit predecessor relationship:

```text
classes/english11_p3/modules/portia/work/sup_01k40h6y/
  records/
    work_relationship/
      rel_01k40h7z.json
```

```json
{
  "record_kind": "work_relationship",
  "record_id": "rel_01k40h7z",
  "source": {
    "module_id": "portia",
    "class_id": "english11_p3",
    "work_id": "sup_01k40h6y",
    "work_kind": "support_process"
  },
  "target": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "sup_01j30g5x",
    "work_kind": "support_process"
  },
  "relationship": "successor_of",
  "status": "active"
}
```

### Derived Reverse View

When the prior Support Process is displayed, Portia may derive:

```text
Succeeded by:
sup_01k40h6y
```

No independently editable reverse relationship is required.

### Result

The prior Support Process:

* retains its original class;
* retains its original school-year context;
* retains its original history;
* and remains independently explainable.

The successor receives:

* a new `work_id`;
* a new owning class;
* a new school-year context;
* and an explicit link to its predecessor.

Longitudinal continuity is represented through linked work rather than one permanent student dossier.

---

## Summary of Represented Invariants

These examples demonstrate that:

1. Every Event and Support Process has one canonical work root.
2. Every Event and Support Process has one owning class.
3. Event ownership normally follows temporal and instructional context.
4. Student identity is always qualified by the source `class_id`.
5. Cross-class participants are linked without duplicating the Event.
6. Cross-class work relationships contain complete work references.
7. Recurring non-roster people may use workspace-scoped Actor IDs.
8. Incidental or unidentified people may remain descriptive.
9. Relationships have one canonical direction.
10. Reverse links, student histories, and timelines are derived.
11. Historical display snapshots are readable but nonauthoritative.
12. Cross-year continuation uses linked successor work.
13. Names and sensitive descriptions do not appear in identity-bearing paths.
14. Unsupported identities are not fabricated.
