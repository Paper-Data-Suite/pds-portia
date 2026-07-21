# Portia Event and Event Participant Examples

These examples are synthetic. Names, identifiers, classes, dates, and circumstances are fictional and exist only to demonstrate the accepted Portia Event and Event Participant domain model.

The examples use the canonical storage forms:

```text
classes/<class_id>/modules/portia/work/<work_id>/work.json
classes/<class_id>/modules/portia/work/<work_id>/records/event_participant/<participant_id>.json
```

Each JSON record in this document validates independently against either `schemas/event.schema.json` or `schemas/event-participant.schema.json`. Cross-record and Core-owned invariants remain application-validation responsibilities.

## Example Index

| Example | Demonstrates |
| --- | --- |
| 1 | Direct digital capture of a positive Event |
| 2 | Paper preallocation, scan proposal, and teacher confirmation |
| 3 | One class-owned Event with participants from different Core rosters |
| 4 | Active Event with unknown occurrence timing and an unresolved person |
| 5 | Identity resolution through participant replacement and supersession |
| 6 | Event-boundary correction by splitting one Event into two replacements |

Role assignments, lifecycle-transition records, Accounts, Observations, Responses, Supports, and Follow-Ups are omitted because their schemas are outside the current issue.

## 1. Direct Digital Capture of a Positive Event

This Event is owned by `eng10_p2_2026`. The teacher selects the student directly, enters a brief neutral summary, and saves an activation-complete Event. No proposed review state is needed because the participant selection is explicit and unambiguous.

### `classes/eng10_p2_2026/modules/portia/work/evt_digital_positive_001/work.json`

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_digital_positive_001",
  "school_year": "2026-2027",
  "status": "active",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-08T09:20:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-08T09:20:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-08T09:18:00-04:00"
  },
  "summary": "Avery redirected the group to the task and invited another student to contribute.",
  "location": {
    "type": "classroom",
    "detail": "Table group 3"
  },
  "instructional_context": {
    "type": "group_work",
    "detail": "Short-story discussion"
  }
}
```

### `classes/eng10_p2_2026/modules/portia/work/evt_digital_positive_001/records/event_participant/ep_avery_001.json`

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_digital_positive_001",
  "participant_id": "ep_avery_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1001"
    },
    "display_snapshot": {
      "display_name": "Avery Chen"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-08T09:20:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-08T09:20:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

The Event summary records a positive contribution without converting the observation into a grade or a durable judgment about the student.

## 2. Paper Preallocation, Scan Proposal, and Confirmation

This workflow uses one preallocated draft Event. The returned page resolves to that existing Event; scanning does not create a second Event.

### 2.1 Preallocated Draft Event

The Event exists before printing. Because it is a draft, `occurrence` and `summary` may be absent.

#### `classes/eng10_p2_2026/modules/portia/work/evt_paper_capture_001/work.json`

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_paper_capture_001",
  "school_year": "2026-2027",
  "status": "draft",
  "creation_source": {
    "type": "paper_capture",
    "stage": "preallocated",
    "route_id": "rt_portia_p2_20260909_001",
    "page_record_id": "pg_portia_p2_20260909_001"
  },
  "created_at": "2026-09-09T07:35:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-09T07:35:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

### 2.2 Participant Proposed from the Returned Page

The scan process creates an unconfirmed participant proposal. It does not activate the participant or Event.

#### `classes/eng10_p2_2026/modules/portia/work/evt_paper_capture_001/records/event_participant/ep_paper_jordan_001.json`

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_paper_capture_001",
  "participant_id": "ep_paper_jordan_001",
  "status": "proposed",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1024"
    },
    "display_snapshot": {
      "display_name": "Jordan Lee"
    }
  },
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_portia_p2_20260909_001",
    "page_record_id": "pg_portia_p2_20260909_001"
  },
  "created_at": "2026-09-09T10:14:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-09T10:14:00-04:00",
  "updated_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  }
}
```

### 2.3 Same Event After Teacher Review

The teacher confirms the occurrence, summary, and participant. The Event retains its original `paper_capture / preallocated` creation source, while update attribution records the teacher’s confirmation.

#### Updated `work.json`

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_paper_capture_001",
  "school_year": "2026-2027",
  "status": "active",
  "creation_source": {
    "type": "paper_capture",
    "stage": "preallocated",
    "route_id": "rt_portia_p2_20260909_001",
    "page_record_id": "pg_portia_p2_20260909_001"
  },
  "created_at": "2026-09-09T07:35:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-09T10:18:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "approximate",
    "started_at": "2026-09-09T09:05:00-04:00",
    "approximation": "about"
  },
  "summary": "Jordan returned to the assigned seat after one reminder and resumed independent work.",
  "location": {
    "type": "classroom"
  },
  "instructional_context": {
    "type": "independent_work"
  }
}
```

#### Updated participant record

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_paper_capture_001",
  "participant_id": "ep_paper_jordan_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1024"
    },
    "display_snapshot": {
      "display_name": "Jordan Lee"
    }
  },
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_portia_p2_20260909_001",
    "page_record_id": "pg_portia_p2_20260909_001"
  },
  "created_at": "2026-09-09T10:14:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-09T10:17:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

The proposed participant becomes active in place because the canonical subject identity did not change.

## 3. Cross-Class Participation

The occurrence belongs to the instructional context of `eng10_p2_2026`, so that class owns the Event. One participant comes from the owning roster; the other comes from a different valid Core roster in the same teacher workspace.

### Event Root

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_cross_class_001",
  "school_year": "2026-2027",
  "status": "active",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-10T11:12:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-10T11:12:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "range",
    "started_at": "2026-09-10T11:02:00-04:00",
    "ended_at": "2026-09-10T11:07:00-04:00"
  },
  "summary": "Two students from different rosters worked together to return shared materials and resolve a disagreement about their use.",
  "location": {
    "type": "hallway",
    "detail": "Outside room 214"
  },
  "instructional_context": {
    "type": "transition"
  }
}
```

### Participant from the Owning Roster

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_cross_class_001",
  "participant_id": "ep_maya_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1031"
    },
    "display_snapshot": {
      "display_name": "Maya Patel"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-10T11:12:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-10T11:12:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

### Participant from Another Roster

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_cross_class_001",
  "participant_id": "ep_luis_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "art1_p5_2026",
      "student_id": "stu_2088"
    },
    "display_snapshot": {
      "display_name": "Luis Rivera"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-10T11:12:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-10T11:12:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

Both participant files remain beneath the Event’s owning class and work root. The second student’s durable identity remains the complete reference `art1_p5_2026 + stu_2088`. Portia does not duplicate the Event beneath the Art class.

## 4. Honest Uncertainty

An Event may be active even when exact occurrence timing or participant identity is unknown, provided uncertainty is represented explicitly rather than replaced by fabricated values.

### Event with Unknown Occurrence Timing

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_unresolved_online_001",
  "school_year": "2026-2027",
  "status": "active",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-11T13:40:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-11T13:40:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "unknown",
    "reason": "not_reported"
  },
  "summary": "A student reported receiving repeated disruptive messages from an unidentified person through an online class activity.",
  "location": {
    "type": "online"
  },
  "instructional_context": {
    "type": "online_activity",
    "detail": "Class discussion board"
  }
}
```

### Active Unknown-Person Participant

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_unresolved_online_001",
  "participant_id": "ep_unknown_sender_001",
  "status": "active",
  "subject": {
    "kind": "unknown_person",
    "reason": "identity_not_known",
    "description": "Unidentified account using a generic display name"
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-11T13:40:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-11T13:40:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

The `unknown_person` participant satisfies the active Event’s minimum-participant requirement. Portia does not create a fake roster student or force immediate identity resolution.

## 5. Later Identity Resolution

The unidentified participant from Example 4 is later resolved to a roster student in another class. Portia preserves the original uncertainty instead of mutating the old participant’s subject.

### Original Participant After Supersession

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_unresolved_online_001",
  "participant_id": "ep_unknown_sender_001",
  "status": "superseded",
  "subject": {
    "kind": "unknown_person",
    "reason": "identity_not_known",
    "description": "Unidentified account using a generic display name"
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-11T13:40:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-12T08:20:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

### Canonical Replacement Participant

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_unresolved_online_001",
  "participant_id": "ep_resolved_sender_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p4_2026",
      "student_id": "stu_1142"
    },
    "display_snapshot": {
      "display_name": "Riley Brooks"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-12T08:20:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-12T08:20:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "supersedes": [
    {
      "participant_id": "ep_unknown_sender_001",
      "reason": "identity_resolved"
    }
  ]
}
```

The replacement owns the forward `supersedes` relationship. A reverse “superseded by” view for `ep_unknown_sender_001` is derived. The replacement is activated before the old participant is superseded so the active Event never temporarily lacks an active participant.

## 6. Event-Boundary Correction

The original Event improperly combined two separate interactions because they involved the same student on the same day. It is replaced by two bounded Events.

### Original Event After Supersession

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_combined_occurrences_001",
  "school_year": "2026-2027",
  "status": "superseded",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-14T14:30:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-15T07:50:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "range",
    "started_at": "2026-09-14T09:00:00-04:00",
    "ended_at": "2026-09-14T14:15:00-04:00"
  },
  "summary": "Initial entry combined two separate classroom interactions involving the same student."
}
```

### Morning Replacement Event

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_morning_interaction_001",
  "school_year": "2026-2027",
  "status": "closed",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-15T07:48:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-15T08:05:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-14T09:04:00-04:00"
  },
  "summary": "During morning independent work, Sam asked for clarification and resumed the assignment after the teacher restated the direction.",
  "location": {
    "type": "classroom"
  },
  "instructional_context": {
    "type": "independent_work"
  },
  "supersedes": [
    {
      "class_id": "eng10_p2_2026",
      "work_id": "evt_combined_occurrences_001"
    }
  ]
}
```

### Morning Participant

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_morning_interaction_001",
  "participant_id": "ep_sam_morning_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1077"
    },
    "display_snapshot": {
      "display_name": "Sam Okafor"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-15T07:48:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-15T07:48:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

### Afternoon Replacement Event

```json
{
  "schema_version": "1",
  "record_type": "portia_work",
  "work_kind": "event",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_afternoon_interaction_001",
  "school_year": "2026-2027",
  "status": "active",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-15T07:49:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-15T07:49:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "occurrence": {
    "precision": "exact",
    "started_at": "2026-09-14T14:08:00-04:00"
  },
  "summary": "During afternoon transition, Sam and the teacher discussed how materials would be returned before dismissal.",
  "location": {
    "type": "classroom",
    "detail": "Near classroom door"
  },
  "instructional_context": {
    "type": "transition"
  },
  "supersedes": [
    {
      "class_id": "eng10_p2_2026",
      "work_id": "evt_combined_occurrences_001"
    }
  ]
}
```

### Afternoon Participant

```json
{
  "schema_version": "1",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_afternoon_interaction_001",
  "participant_id": "ep_sam_afternoon_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "student_ref": {
      "class_id": "eng10_p2_2026",
      "student_id": "stu_1077"
    },
    "display_snapshot": {
      "display_name": "Sam Okafor"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-15T07:49:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  },
  "updated_at": "2026-09-15T07:49:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Taylor Morgan"
  }
}
```

Each replacement owns a canonical forward reference to the original Event. The original root does not need an authoritative `superseded_by` field; its replacement list is derived from incoming `supersedes` relationships.

## Validation Notes

The example set was validated with a Draft 2020-12 validator and RFC 3339 format checking.

Schema validation confirms record shape, required fields, constants, enums, identifier patterns, discriminated unions, timestamp syntax, and rejection of unknown properties.

Application validation must additionally confirm:

* path and persisted identity agreement;
* existence of owning classes, source rosters, students, Actors, routes, pages, parent Events, and superseded records;
* `updated_at >= created_at`;
* chronological ordering within occurrence intervals;
* lifecycle-transition legality and matching transition history;
* at least one active participant before Event activation;
* duplicate active durable-subject prevention;
* teacher review of paper- or import-derived proposals;
* replacement activation before removal of the final active participant;
* and incoming replacement relationships for Events or participants marked `superseded`.
