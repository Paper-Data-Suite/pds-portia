# Portia Reference, Targeting, and Relationship Examples

**Status:** Accepted synthetic examples  
**Issue:** `#11 — Define shared reference, targeting, and relationship contracts`  
**Date:** 2026-08-02

These examples illustrate the public wire shapes accepted by ADR 0007. They are synthetic and contain no real student data.

Structural validity does not establish that a target exists, is authorized, has a usable lifecycle state, or is eligible for a particular consumer. Application-invalid examples are labeled explicitly.

## 1. Roster Student Reference and Snapshot

The durable identity is the exact source-roster pair:

```json
{
  "roster_student_ref": {
    "class_id": "eng10_p5_2026",
    "student_id": "stu_0200"
  },
  "display_snapshot": {
    "display_name": "Avery Chen"
  }
}
```

`display_snapshot` is a sibling presentation aid. It is not part of identity or resolution.

## 2. Actor Reference and Snapshot

```json
{
  "actor_ref": {
    "actor_id": "actr_counselor_001"
  },
  "display_snapshot": {
    "display_name": "School Counselor"
  }
}
```

The Actor Directory is authoritative only within the selected teacher workspace.

## 3. Same-Work Local Record Reference

```json
{
  "record_kind": "account",
  "record_id": "acct_001",
  "contract_version": null
}
```

The containing record supplies the one unambiguous Portia work scope. `null` is deliberate because the Account public contract is not yet accepted.

A local reference must not repeat work scope:

```json
{
  "record_kind": "account",
  "record_id": "acct_001",
  "contract_version": null,
  "class_id": "eng10_p2_2026"
}
```

The second object is structurally invalid because the shared local reference is closed.

## 4. Portia Work Reference

Event:

```json
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_example",
  "work_kind": "event",
  "contract_version": "2"
}
```

Support Process before its first public work contract is accepted:

```json
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "sup_example",
  "work_kind": "support_process",
  "contract_version": null
}
```

After the Support Process contract is accepted, newly created references should state its supported version rather than continuing to use `null`.

## 5. Cross-Work Portia Record Reference

```json
{
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "2"
  },
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "2"
  }
}
```

The target work is explicit. Resolution must not search other classes or Events for `ep_example`.

## 6. Sibling-Module Work and Record Reference

`module_work_record_ref` composes the exact Core work and record wire shapes:

```json
{
  "work_ref": {
    "module_id": "quillan",
    "class_id": "eng10_p2_2026",
    "work_id": "essay_01"
  },
  "record_ref": {
    "module_id": "quillan",
    "record_kind": "review",
    "record_id": "review_01",
    "contract_version": "2"
  }
}
```

The two nested `module_id` values must agree.

This object is structurally valid but application-invalid:

```json
{
  "work_ref": {
    "module_id": "quillan",
    "class_id": "eng10_p2_2026",
    "work_id": "essay_01"
  },
  "record_ref": {
    "module_id": "scoreform",
    "record_kind": "review",
    "record_id": "review_01",
    "contract_version": "2"
  }
}
```

Standard JSON Schema cannot compare the sibling values; application validation rejects the mismatch.

## 7. Event Target

```json
{
  "kind": "event"
}
```

The target means the containing Event as a whole. It does not silently target every participant.

## 8. Singular Event Participant Target

```json
{
  "kind": "event_participant",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "2"
  }
}
```

The target identifies the Event Participant record, not the underlying person outside the Event.

## 9. Plural Event Participant Target

```json
{
  "kind": "event_participants",
  "targets": [
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_001",
        "contract_version": "2"
      }
    },
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_002",
        "contract_version": "2"
      }
    }
  ]
}
```

At least two explicit participant targets are required. Array order has no domain meaning.

This set is application-invalid even though the JSON objects are distinct:

```json
{
  "kind": "event_participants",
  "targets": [
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_001",
        "contract_version": "1"
      }
    },
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_001",
        "contract_version": "2"
      }
    }
  ]
}
```

Both entries have the same canonical participant identity inside the containing Event.

## 10. Support Process Targets

Whole process:

```json
{
  "kind": "support_process"
}
```

One future Support Process Participant:

```json
{
  "kind": "support_process_participant",
  "record_ref": {
    "record_kind": "support_process_participant",
    "record_id": "spp_example",
    "contract_version": null
  }
}
```

The target family reserves structure only. Issue #18 owns the participant record, roles, provider and recipient meanings, implementation, and fidelity semantics.

## 11. Event Participant v2 Subjects

Roster student:

```json
{
  "schema_version": "2",
  "record_type": "event_participant",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_example",
  "participant_id": "ep_roster_001",
  "status": "active",
  "subject": {
    "kind": "roster_student",
    "roster_student_ref": {
      "class_id": "eng10_p5_2026",
      "student_id": "stu_0200"
    },
    "display_snapshot": {
      "display_name": "Avery Chen"
    }
  },
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-08-02T17:00:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "S. Severino"
  },
  "updated_at": "2026-08-02T17:00:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "S. Severino"
  }
}
```

Actor subject uses the same snapshot placement:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_counselor_001"
  },
  "display_snapshot": {
    "display_name": "School Counselor"
  }
}
```

## 12. Event Participant v2 Supersession

```json
{
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_prior_v1",
    "contract_version": "1"
  },
  "reason": "identity_corrected"
}
```

The successor preserves the prior record's exact public contract version. It does not follow a later successor automatically.

## 13. Event Participant Role v2 Target

```json
{
  "target": {
    "kind": "event_participant",
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ep_example",
      "contract_version": "2"
    }
  }
}
```

A Role permits only the singular participant branch. Event-level and plural participant Role targets are structurally invalid.

## 14. Role Account and Observation Basis

Account:

```json
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": null
  }
}
```

Observation:

```json
{
  "kind": "observation_ref",
  "record_ref": {
    "record_kind": "observation",
    "record_id": "obs_example",
    "contract_version": null
  }
}
```

The outer `kind` states basis meaning. The nested reference identifies the same-Event record. Creation provenance remains separate.

## 15. Role v2 Supersession

```json
{
  "record_ref": {
    "record_kind": "event_participant_role",
    "record_id": "epr_prior",
    "contract_version": "1"
  },
  "reason": "role_type_corrected"
}
```

Material target, role-type, basis, or detail corrections create a successor Role rather than mutating the active assertion's meaning.

## 16. Event v2 Instructional Context

```json
{
  "instructional_context": {
    "type": "assessment",
    "external_refs": [
      {
        "work_ref": {
          "module_id": "scoreform",
          "class_id": "eng10_p2_2026",
          "work_id": "unit_1_assessment"
        },
        "record_ref": {
          "module_id": "scoreform",
          "record_kind": "result_set",
          "record_id": "results_001",
          "contract_version": "1"
        }
      }
    ]
  }
}
```

Portia owns only its use of the reference as Event context. ScoreForm remains authoritative for the referenced record.

## 17. Event v2 Supersession

```json
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_prior",
  "work_kind": "event",
  "contract_version": "1"
}
```

The successor Event stores the predecessor's complete Portia work reference directly in `supersedes`.

## 18. Work Relationship

```json
{
  "schema_version": "1",
  "record_type": "work_relationship",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "sup_example",
  "relationship_id": "rel_context_001",
  "status": "active",
  "relationship_type": "draws_context_from",
  "source": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "sup_example",
    "work_kind": "support_process",
    "contract_version": null
  },
  "target": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "2"
  },
  "detail": "Used as contextual information while reviewing the support process.",
  "creation_source": {
    "type": "digital_entry"
  },
  "created_at": "2026-08-02T18:00:00-04:00",
  "created_by": {
    "type": "local_operator",
    "display_label": "S. Severino"
  },
  "updated_at": "2026-08-02T18:00:00-04:00",
  "updated_by": {
    "type": "local_operator",
    "display_label": "S. Severino"
  }
}
```

The record is stored beneath the source Support Process work root. The target Event stores no canonical reverse copy.

The source's `contract_version` remains `null` only until the first Support Process work contract is accepted.

## 19. Work Relationship Supersession

```json
{
  "work_record_ref": {
    "work_ref": {
      "module_id": "portia",
      "class_id": "eng10_p2_2026",
      "work_id": "sup_example",
      "work_kind": "support_process",
      "contract_version": null
    },
    "record_ref": {
      "record_kind": "work_relationship",
      "record_id": "rel_prior",
      "contract_version": "1"
    }
  },
  "reason": "target_corrected"
}
```

A successor may consolidate several predecessors. Predecessors remain active until successor activation is completed atomically or recoverably.

## 20. Resolution Outcomes

A missing target is not rewritten:

```json
{
  "resolution_state": "missing",
  "failure_stage": "record",
  "use_disposition": "not_usable"
}
```

A resolved historical predecessor may be nonusable for a current workflow:

```json
{
  "resolution_state": "resolved",
  "use_disposition": "historical_only"
}
```

These are runtime assessments. They are not cached as authoritative mutations inside the canonical reference.

## 21. Migration Principle

Historical version-1 records remain valid under their original schemas. Migration to version 2 is explicit and may preserve the canonical record ID when identity and assertion meaning remain unchanged.

For example, the v1 Role field:

```json
{
  "participant_id": "ep_example"
}
```

becomes the v2 target:

```json
{
  "target": {
    "kind": "event_participant",
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ep_example",
      "contract_version": "2"
    }
  }
}
```

Ordinary reads do not perform this transformation silently.
