# Portia Record Sensitivity and Projection Matrix

**Status:** Issue #21 Slice 2 baseline
**Purpose:** Define privacy-projection handling across the complete Portia
foundation through merged Issue #20.

This matrix is product architecture, not a legal entitlement table.

## 1. Legend

Projection columns use:

```text
I   candidate for inclusion after normal exact-scope/policy checks
C   conditional; focal context and field-level policy required
W   withheld by default from this outward purpose
M   may require manual privacy review
A   aggregate-only/derived treatment; no native record row
N   not an ordinary projection surface
```

These are **defaults**, not authorization.

A record marked `I` can still contain a field classified `W` or `M`.

A record marked `W` can still contribute a privacy-safe fact through an explicit
policy transformation without exposing its native payload.

Retention-class values are preliminary Issue #21 semantic classifications.
Slice 5 will reconcile/finalize the retention policy and disposition boundary.

## 2. Domain and relationship records

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `event` | I | C | C | C | A | summary, exact time/location, instructional context can indirectly identify others | No | Yes | `canonical_behavior_support` |
| `event_participant` | I | C | C focal / W others | C focal / W others | A | student identity/display snapshot | No | Yes | `canonical_behavior_support` |
| `event_participant_role` | I | C | C focal / W others | C focal / W others | A | role itself may identify or stigmatize another person | No | Yes | `canonical_behavior_support` |
| `work_relationship` | I | C | C | C | A | linked work may reveal unrelated participants/context | No | Yes | `canonical_behavior_support` |
| `account` | I | C | M | M | W | source identity, quote/summary, elicitation context, targets, artifact refs | No | **Yes** | `source_evidence` |
| `observation` | I | C | C/M | C/M | A | observer identity, multi-target content, narrative/detail, artifact refs | No | Yes | `source_evidence` |
| `review` | I | C | C | C | A | reviewer identity, evidence references, scope/status | No | Yes | `canonical_behavior_support` |
| `classification` | I | C | C | C | A | human label/judgment can become identity-like if decontextualized | No | Yes | `canonical_behavior_support` |
| `hypothesis` | I | C | C/M | C/M | A | tentative human interpretation; supporting/contrary evidence can identify others | No | Yes | `canonical_behavior_support` |
| `determination` | I | C | C/M | C/M | A | authority/scope, supporting/contrary evidence, outcome wording | No | Yes | `canonical_behavior_support` |
| `response` | I | C | C | C | A | providers/recipients, reason/detail, linked records | No | Yes | `canonical_behavior_support` |
| `communication` | I in explicit workflow | C | M | M | W | recipients, endpoint refs, summary, attachments, `privacy_scope` | No | **Yes** | `canonical_behavior_support` |

## 3. Actor Directory records

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `actor` | I | C | C | C | W | non-student identity, display information, local-only identity semantics | No | Yes | `actor_identity` |
| `actor_contact_point` | C only in contact workflow | W | W | W | W | exact email/phone, source, verification, preference | **Never by default** | Yes | `actor_contact` |
| `actor_student_relationship` | I | C | C/M | C/M | W | relationship label can imply guardianship/authority that Portia does not establish | No | Yes | `actor_identity` |
| `actor_roster_student_collision` | C administrative | W | W | W | W | identity collision diagnostic | No | Yes | `operation_recovery_integrity` |
| `actor_directory_lifecycle_transition` | C administrative/history | W | W | W | W | operational lifecycle reason/actor | No | Yes | `lifecycle_correction_disagreement` |
| `actor_directory_lifecycle_history_correction` | C administrative/history | W | W | W | W | correction rationale/provenance | No | Yes | `lifecycle_correction_disagreement` |
| `actor_directory_amendment` | C | C when needed | C when needed | C when needed | W | amendment text/source may be sensitive narrative | No | Yes | `lifecycle_correction_disagreement` |
| `actor_directory_record_migration` | C administrative | W | W | W | W | old/new ownership/path identities | No | Yes | `lifecycle_correction_disagreement` |
| `actor_directory_exceptional_removal` | C administrative | C existence only if relevant | C existence only if relevant | C existence only if relevant | W | removal rationale/authority detail | No | Yes | `exceptional_removal_certificate` |

## 4. Support Process and intervention records

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `support_process` | I | C | C | C | A | initiating context, linked Events/Determinations, multi-participant context | No | Yes | `canonical_behavior_support` |
| `support_process_participant` | I | C | C focal / W others | C focal / W others | A | participant/provider/collaborator identity | No | Yes | `canonical_behavior_support` |
| `support_need` | I | C | C | C | A | need wording can become trait-like if decontextualized | No | Yes | `canonical_behavior_support` |
| `support_goal` | I | C | C | C | A | goal wording, participant/provider context | No | Yes | `canonical_behavior_support` |
| `support` | I | C | C | C | A | provider/recipient relationships, details | No | Yes | `canonical_behavior_support` |
| `intervention` | I | C | C | C | A | provider/recipient relationships, plan detail | No | Yes | `canonical_behavior_support` |
| `planned_schedule` component | I | C | C | C | A | timing/pattern can indirectly identify support context | No | Yes | `canonical_behavior_support` |
| `implementation` | I | C | C | C | A | provider/recipient/timing; completion does not imply success | No | Yes | `canonical_behavior_support` |
| `fidelity` | I | C | C/M | C/M | A | human implementation-quality judgment, evidence refs | No | Yes | `canonical_behavior_support` |

## 5. Follow-Up, Outcome, Reentry, and Repair

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `follow_up` | I | C | C | C | A | participant/family perspectives, linked evidence, narrative | No | Yes | `canonical_behavior_support` |
| `outcome` | I | C | C/M | C/M | A | attributable human evaluation, evidence, timeframe; no causal inference | No | Yes | `canonical_behavior_support` |
| `reentry` | I | C | C/M | C/M | A | plan/participant/provider context; completion is not clearance | No | Yes | `canonical_behavior_support` |
| `repair` | I | C | C/M | C/M | A | multiple parties, agreement/perspective detail; no admission/remorse inference | No | **Yes** | `canonical_behavior_support` |

## 6. Shared lifecycle, correction, migration, and removal

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `lifecycle_transition` | C history | C when necessary for truth | C when necessary | C when necessary | W | reason/actor/timing may expose internal process | No | Yes | `lifecycle_correction_disagreement` |
| `lifecycle_history_correction` | C history | C when necessary | C when necessary | C when necessary | W | correction rationale/provenance | No | Yes | `lifecycle_correction_disagreement` |
| `amendment` | C | C | C/M | C/M | W | substantive correction text/source | No | Yes | `lifecycle_correction_disagreement` |
| `statement_of_disagreement` | C | C | C/M when applicable | C/M when applicable | W | source identity and statement narrative | No | **Yes** | `lifecycle_correction_disagreement` |
| `ownership_correction` | C administrative/history | C existence when needed | C existence when needed | C existence when needed | W | wrong/current class/work ownership, rationale | No | Yes | `lifecycle_correction_disagreement` |
| `record_migration` | C administrative/history | C existence when needed | C existence when needed | C existence when needed | W | old/new contract/path/ownership detail | No | Yes | `lifecycle_correction_disagreement` |
| `dependency` | C administrative | W | W | W | W | graph can reveal otherwise withheld records | No | Yes | `operation_recovery_integrity` |
| `exceptional_removal` | C administrative/history | C existence if needed for truthful history | C existence if needed | C existence if needed | W | authority/rationale/path information | No | Yes | `exceptional_removal_certificate` |

## 7. Paper-assisted capture records

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `capture_batch` | C capture workflow | W | W | W | W | operational work/batch metadata | No | No ordinary outward | `paper_import_provenance` |
| `page_target` | C capture workflow | W | W | W | W | route target, template/layout, intended work context | No | Yes | `paper_import_provenance` |
| `page_record` | C capture workflow | W | W | W | W | retained-source identity, route, source fingerprint | No | Yes | `paper_import_provenance` |
| `paper_interpretation` | C review workflow | W | W | W | W | OCR/mark/handwriting candidates, alternatives/confidence | No | Yes | `paper_import_provenance` |
| `capture_proposal` | C review workflow | W | W | W | W | proposed mappings/targets before canonical acceptance | No | Yes | `paper_import_provenance` |
| `capture_review` | C review workflow | W | W | W | W | reviewer/correction operational decision | No | Yes | `paper_import_provenance` |
| `capture_materialization` | C administrative/recovery | W | W | W | W | exact operation/canonical-result lineage | No | Yes | `paper_import_provenance` |

## 8. Structured import records

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `import_batch` | C import workflow | W | W | W | W | source snapshot/profile/mapping identity | No | Yes | `paper_import_provenance` |
| `import_source_record` | C import workflow | W | W | W | W | source keys and bounded source fields may carry PII | No | **Yes** | `paper_import_provenance` |
| `import_proposal` | C review workflow | W | W | W | W | source/transformed candidates and proposed targets | No | Yes | `paper_import_provenance` |
| `import_review` | C review workflow | W | W | W | W | reviewer/correction operational decision | No | Yes | `paper_import_provenance` |
| `import_materialization` | C administrative/recovery | W | W | W | W | exact source/proposal/review/operation/result lineage | No | Yes | `paper_import_provenance` |

## 9. Coordinated operations, integrity, and quarantine

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `operation_journal` | C recovery/admin | W | W | W | W | write set, lock set, intent, recovery detail | Never ordinary | Yes | `operation_recovery_integrity` |
| `operation_lock` | N except recovery/admin | W | W | W | W | paths/identities/operation state | Never ordinary | No | `operation_recovery_integrity` |
| `operation_current_pointer` | N | W | W | W | W | operational revision pointer | Never ordinary | No | `derived_cache` |
| `quarantine_record` | C integrity workflow | W | W | W | W | exceptional broken-state payload/refs | Never ordinary | **Yes** | `operation_recovery_integrity` |
| `quarantine_current_pointer` | N | W | W | W | W | operational pointer | Never ordinary | No | `derived_cache` |
| `integrity_finding` | C integrity workflow | W | W | W | W | diagnostic evidence and affected identities | Never ordinary | **Yes** | `operation_recovery_integrity` |
| `finding_acknowledgement` | C integrity workflow | W | W | W | W | operator/diagnostic context | Never ordinary | Yes | `operation_recovery_integrity` |
| `finding_suppression` | C integrity workflow | W | W | W | W | diagnostic reasoning and scope | Never ordinary | Yes | `operation_recovery_integrity` |
| `finding_suppression_current_pointer` | N | W | W | W | W | operational pointer | Never ordinary | No | `derived_cache` |

## 10. Existing derived projection infrastructure

| Record family | Teacher current | Participant-specific | Student-facing | Family-facing | Aggregate/equity | Third-party / field risk | Raw native outward export | Manual review possible | Preliminary retention class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `source_snapshot` | N infrastructure | W | W | W | N infrastructure | source paths, fingerprints, authorization-scope metadata | Never ordinary | Yes | `derived_cache` |
| `derived_index_metadata` | N infrastructure | W | W | W | N infrastructure | source inventory/output path/operation provenance | Never ordinary | Yes | `derived_cache` |
| `derived_current_pointer` | N infrastructure | W | W | W | N infrastructure | current derived generation pointer | Never ordinary | No | `derived_cache` |

Existing v1 projection infrastructure is not silently redefined as Issue #21
outward privacy projection.

## 11. Non-record components with mandatory field-level handling

These contracts/components are not new canonical student records but can carry
sensitive information wherever embedded.

| Component / field class | Default outward handling |
| --- | --- |
| `represented_human_attribution` | focal identity conditional; unrelated identity withheld |
| person display snapshots | focal/necessary display conditional; third-party withheld |
| Actor Contact Point exact value | withheld outside explicit contact workflow |
| `source_artifact_ref` | locator withheld; bounded existence may be represented |
| Communication `endpoint_ref` | withheld |
| workspace-relative attachment path | withheld |
| foreign module record reference | conditional; never grants foreign source access |
| PDS2 route / retained-source identity | withheld |
| import source key / external reference | withheld |
| source hash/fingerprint | operational/integrity only by default |
| Account/Communication/disagreement free text | manual review possible |
| correction/removal rationale | conditional/manual review |
| operation/integrity diagnostic detail | restricted administrative |
| creation/update attribution | conditional; not automatically recipient-facing |

## 12. Cross-cutting rules

### 12.1 No raw-record pass-through

A projectable record is not returned as its native JSON object.

### 12.2 No existence leakage by default

Withheld record counts, source identities, attachment counts, and restricted
Communication counts are themselves projection decisions.

### 12.3 No silent currentness errors

A current projection must reconcile:

```text
status
supersession
invalidation
correction
ownership correction
migration
Statement of Disagreement
Exceptional Removal
```

as applicable.

### 12.4 No cross-module authority transfer

A Portia projection may reference a Core/sibling-owned source without exposing
or authorizing that foreign source.

### 12.5 No unsupported inference

Projection does not infer:

```text
credibility
guilt
intent
diagnosis
severity
risk
effectiveness
clearance
rehabilitation
remorse
forgiveness
```

## 13. Matrix inventory

The matrix explicitly tracks **66 current top-level/operational record families
or record-like schema surfaces**, plus embedded sensitive components.

Tracked families:

```text
event
event_participant
event_participant_role
work_relationship
account
observation
review
classification
hypothesis
determination
response
communication

actor
actor_contact_point
actor_student_relationship
actor_roster_student_collision
actor_directory_lifecycle_transition
actor_directory_lifecycle_history_correction
actor_directory_amendment
actor_directory_record_migration
actor_directory_exceptional_removal

support_process
support_process_participant
support_need
support_goal
support
intervention
planned_schedule
implementation
fidelity

follow_up
outcome
reentry
repair

lifecycle_transition
lifecycle_history_correction
amendment
statement_of_disagreement
ownership_correction
record_migration
dependency
exceptional_removal

capture_batch
page_target
page_record
paper_interpretation
capture_proposal
capture_review
capture_materialization

import_batch
import_source_record
import_proposal
import_review
import_materialization

operation_journal
operation_lock
operation_current_pointer
quarantine_record
quarantine_current_pointer
integrity_finding
finding_acknowledgement
finding_suppression
finding_suppression_current_pointer

source_snapshot
derived_index_metadata
derived_current_pointer
```

`planned_schedule` is included because it is a public support-process schema
surface even though it is used as a support planning component rather than an
independent behavior-domain work root.

Future Issue #21 schemas will be added to this inventory only after their
semantic ownership is accepted.
