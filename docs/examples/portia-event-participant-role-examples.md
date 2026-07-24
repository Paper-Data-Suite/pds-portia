# Portia Event Participant Role Examples

These examples are synthetic. Names, identifiers, classes, dates, and circumstances are fictional and exist only to demonstrate the accepted Portia Event Participant Role domain model.

The canonical storage form is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/event_participant_role/<role_id>.json
```

Each complete JSON record in this document validates independently against `schemas/event-participant-role.schema.json`.

Cross-record and lifecycle invariants remain application-validation responsibilities, including parent Event and Event Participant state, same-Event Account and Observation existence, Account attribution, exact paper-source and paper-basis reference equality, duplicate and compatibility checks across files, chronology, coordinated supersession, and lifecycle-history persistence.

## Example Index

| Example | Demonstrates |
| --- | --- |
| 1 | Direct reviewed digital assignment created as active |
| 2 | Compatible `present` and `directly_involved` Roles |
| 3 | Proposed and active `contextual` detail requirements |
| 4 | Paper-derived `reported_involved` proposal and activation |
| 5 | Imported `reported_involved` proposal and activation |
| 6 | Role-type refinement through successor activation |
| 7 | Basis correction and duplicate consolidation |

## 1. Direct Reviewed Digital Assignment

The teacher explicitly selects an active Event Participant and saves `directly_involved`. The Role may be created directly as active because review is complete.

### `records/event_participant_role/epr_direct_001.json`

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_direct_001",
  "participant_id": "ep_avery_001",
  "status": "active",
  "role_type": "directly_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  }
}
```

The Role records a neutral Event-level relationship. It does not establish fault, misconduct, harm, intent, or responsibility.

## 2. Compatible Active Roles

`present` may coexist with one of the other initial Role types. Each assertion remains a separate canonical record.

### Direct involvement

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_direct_001",
  "participant_id": "ep_avery_001",
  "status": "active",
  "role_type": "directly_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  }
}
```

### Presence supported by an Observation

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_present_001",
  "participant_id": "ep_avery_001",
  "status": "active",
  "role_type": "present",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "basis": [
    {
      "kind": "observation_ref",
      "record_id": "obs_classroom_001"
    }
  ]
}
```

Application validation evaluates the participant's complete intended active-role set. It permits this pair but would prohibit simultaneous active `directly_involved` and `reported_involved`.

## 3. Contextual Review and Activation

A proposed `contextual` Role may temporarily omit `detail`.

### Proposed contextual Role

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_context_proposed_001",
  "participant_id": "ep_counselor_001",
  "status": "proposed",
  "role_type": "contextual",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  }
}
```

Before activation, the Role must contain concise, neutral explanation of the legitimate Event-context relationship.

### Active contextual Role

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_context_active_001",
  "participant_id": "ep_counselor_001",
  "status": "active",
  "role_type": "contextual",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "detail": "Participated in the immediate class-related conference."
}
```

Top-level `detail` is reserved for `contextual`. Accounts, Observations, Event summaries, and basis records preserve clarifying information for the other Role types.

## 4. Paper-Derived Reported Involvement

A returned paper artifact may propose `reported_involved`.

### 4.1 Proposed from returned paper

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_reported_paper_proposed_001",
  "participant_id": "ep_jordan_001",
  "status": "proposed",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_role_paper_001",
    "page_record_id": "pg_role_paper_001"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_role_paper_001",
      "page_record_id": "pg_role_paper_001"
    }
  ]
}
```

The matching paper basis is sufficient for proposal. It is not sufficient for activation because the paper artifact does not structurally identify the attributed report.

### 4.2 Active after attributed Account review

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_reported_paper_active_001",
  "participant_id": "ep_jordan_001",
  "status": "active",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_role_paper_001",
    "page_record_id": "pg_role_paper_001"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "paper_capture_ingest"
  },
  "updated_at": "2026-09-18T09:31:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "basis": [
    {
      "kind": "paper_capture",
      "route_id": "rt_role_paper_001",
      "page_record_id": "pg_role_paper_001"
    },
    {
      "kind": "account_ref",
      "record_id": "acct_jordan_report_001"
    }
  ]
}
```

The matching paper basis preserves the returned artifact. The `account_ref` identifies the separate canonical attributed Account required for every active `reported_involved` Role.

The Account itself is omitted because the Account schema belongs to a later issue.

## 5. Imported Reported Involvement

An import-source basis may preserve an imported proposal while attribution is reviewed.

### 5.1 Imported proposal

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_reported_import_proposed_001",
  "participant_id": "ep_morgan_001",
  "status": "proposed",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": "import-batch-2026-09-01"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "import"
  },
  "updated_at": "2026-09-18T09:24:00-04:00",
  "updated_by": {
    "type": "system_process",
    "process_id": "import"
  },
  "basis": [
    {
      "kind": "import_source",
      "source_label": "Legacy teacher record",
      "source_record_id": "row-184"
    }
  ]
}
```

### 5.2 Active after Account creation or selection

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_reported_import_active_001",
  "participant_id": "ep_morgan_001",
  "status": "active",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": "import-batch-2026-09-01"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "system_process",
    "process_id": "import"
  },
  "updated_at": "2026-09-18T09:35:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "basis": [
    {
      "kind": "import_source",
      "source_label": "Legacy teacher record",
      "source_record_id": "row-184"
    },
    {
      "kind": "account_ref",
      "record_id": "acct_imported_report_001"
    }
  ]
}
```

Review does not rewrite the Role's creation source from `import` to `digital_entry`.

## 6. Role-Type Refinement

A later reviewed relationship may replace `reported_involved` with `directly_involved`.

### Active successor

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_direct_successor_001",
  "participant_id": "ep_riley_001",
  "status": "active",
  "role_type": "directly_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T10:12:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "supersedes": [
    {
      "role_id": "epr_reported_prior_001",
      "reason": "role_type_corrected"
    }
  ]
}
```

The prior Role remains active during successor review. The coordinated activation operation activates the successor and transitions the prior Role to `superseded`.

A reverse `superseded_by` view is derived.

## 7. Basis Correction and Duplicate Consolidation

### 7.1 Corrected attributed support

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_reported_basis_successor_001",
  "participant_id": "ep_riley_001",
  "status": "active",
  "role_type": "reported_involved",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T10:18:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "basis": [
    {
      "kind": "account_ref",
      "record_id": "acct_corrected_report_001"
    }
  ],
  "supersedes": [
    {
      "role_id": "epr_reported_basis_prior_001",
      "reason": "basis_corrected"
    }
  ]
}
```

The prior Role keeps its original Account basis. The successor references the corrected Account and records `basis_corrected`.

### 7.2 Consolidating duplicate Role records

```json
{
  "schema_version": "1",
  "record_type": "event_participant_role",
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_role_examples",
  "role_id": "epr_present_consolidated_001",
  "participant_id": "ep_casey_001",
  "status": "active",
  "role_type": "present",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-09-18T09:24:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "updated_at": "2026-09-18T10:24:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "Sample Teacher"
  },
  "supersedes": [
    {
      "role_id": "epr_present_duplicate_001",
      "reason": "duplicate_consolidated"
    },
    {
      "role_id": "epr_present_duplicate_002",
      "reason": "duplicate_consolidated"
    }
  ]
}
```

One successor may replace several duplicate prior Roles. Each prior record remains historically inspectable.

## Validation Notes

The fixture set accompanying this document covers:

### Valid records

* direct active digital entry;
* Observation-supported presence;
* proposed contextual omission of detail;
* active contextual detail;
* invalidated contextual proposal without detail;
* paper-derived reported proposal;
* paper-derived reported activation with Account;
* imported reported proposal;
* imported reported activation with Account;
* role-type supersession;
* basis-correction supersession;
* and duplicate consolidation.

### Invalid records

* invalid `role_id` prefix;
* top-level detail on a non-contextual Role;
* missing or whitespace-only active contextual detail;
* proposed `reported_involved` without source-oriented basis;
* active or superseded `reported_involved` without `account_ref`;
* preallocated Role paper provenance;
* paper-derived Role without paper basis;
* malformed paper basis;
* repeated Event scope in compact Account references;
* duplicate basis entries;
* incomplete `other` supersession explanation;
* duplicate supersession entries;
* naive timestamps;
* prohibited role vocabulary;
* and embedded `roles`.

JSON Schema does not enforce every domain invariant.

Application validation must additionally confirm:

* canonical path and identifier agreement;
* parent Event and Event Participant existence;
* active participant status before Role activation;
* Event status of `draft` or `active` before Role activation;
* same-Event Account and Observation scope;
* Account attribution;
* exact paper creation-source and matching-basis route/page equality;
* duplicate and compatibility rules across separate Role files;
* allowed lifecycle transitions;
* immutable persisted `participant_id`;
* successor activation and prior supersession coordination;
* Account and participant dependency resolution;
* chronology;
* no hard deletion of canonical Roles;
* and atomic or recoverable multi-record writes.
