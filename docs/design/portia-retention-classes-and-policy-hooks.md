# Portia Retention Classes and Policy Hooks

**Status:** Issue #21 Slice 5 architecture
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Date:** 2026-08-14
**Wire-contract status:** No new public retention schema is introduced by this slice.

> This document defines Portia product architecture and policy hooks, not legal
> advice or a jurisdiction-specific records schedule.

## 1. Decision

Portia owns:

```text
semantic retention classification
exact custody identity
correction/dependency lineage
observable trigger facts
module-local technical capability
module-local integrity blockers
```

Portia does **not** own:

```text
institution retention schedule
legal interpretation
legal-hold decision
requester entitlement
destruction authorization
backup purge policy
proof of destruction outside Portia custody
```

Therefore the foundation uses stable semantic **retention classes** and external
policy/hold inputs rather than embedding retention durations in canonical domain
records.

## 2. Governing distinctions

```text
retention class != retention duration
trigger fact != retention rule
retention rule satisfied != destruction authorized
record inactive != retention expired
record superseded != disposable
request received != request granted
deletion request != deletion authorization
hold candidate != legal hold
Portia deletion != external-copy deletion
Exceptional Removal != routine records disposition
derived-cache deletion != canonical destruction
```

## 3. Final Portia retention classes

Issue #21 adopts these semantic class keys:

```text
canonical_behavior_support
source_evidence
actor_identity
actor_contact
lifecycle_correction_disagreement
paper_import_provenance
operation_recovery_integrity
derived_cache
export_bytes
export_provenance
exceptional_removal_certificate
```

These keys are deliberately:

- lowercase;
- non-jurisdictional;
- non-duration-bearing;
- stable enough for future external policy mapping;
- independent of one institution's schedule nomenclature.

They are **not** added as fields to every Portia record.

The mapping is producer-owned policy metadata derived from record semantics.

## 4. `canonical_behavior_support`

Includes accepted behavior/support domain meaning such as:

```text
Event
Event Participant
Event Participant Role
Work Relationship
Review
Classification
Hypothesis
Determination
Response
Communication
Support Process
Support Process Participant
Support Need
Support Goal
Support
Intervention
Implementation
Fidelity
Follow-Up
Outcome
Reentry
Repair
```

The class does not mean all records receive the same institutional retention
period.

It means an external policy can map these records to the institution's approved
record series/rule without Portia redefining the record.

## 5. `source_evidence`

Includes:

```text
Account
Observation
```

and any later canonical source-evidence family whose principal meaning is
preserving attributed/reproducible evidence rather than a judgment.

Source Artifact references remain part of the containing record's retention
analysis, while the underlying bytes may be separately owned.

A Portia reference to a Core or foreign artifact does not cause Portia to own
the referenced bytes.

## 6. Actor classes

### `actor_identity`

Includes:

```text
Actor
Actor Student Relationship
```

and identity-directory history only where it is substantively necessary to
preserve who a local recurring non-roster person represented.

### `actor_contact`

Includes exact Actor Contact Point values and contact-specific lifecycle state.

Contact data is separated because an institution may legitimately retain
identity/relationship history longer than obsolete email/phone values.

Deleting an obsolete contact value must not delete the Actor identity or
historical domain records that attributed actions to the Actor.

## 7. `lifecycle_correction_disagreement`

Includes:

```text
Lifecycle Transition
Lifecycle History Correction
Amendment
Statement of Disagreement
Ownership Correction
Record Migration
Actor Directory lifecycle/correction/migration records
```

The class exists because correction history must be evaluated as a graph, not as
disposable bookkeeping.

A predecessor/successor relationship can make a historical representation
necessary to interpret the current record.

## 8. `paper_import_provenance`

Includes:

```text
Capture Batch
Page Target
Page Record
Paper Interpretation
Capture Proposal
Capture Review
Capture Materialization
Import Batch
Import Source Record
Import Proposal
Import Review
Import Materialization
```

This class is operational provenance.

It does not imply the raw scan bytes are Portia-owned.

Core-owned retained source scans remain Core custody.

## 9. `operation_recovery_integrity`

Includes durable state required to diagnose or recover writes:

```text
Operation Journal
Operation Lock while valid/required
Quarantine Record
Integrity Finding
Finding Acknowledgement
Finding Suppression
identity-collision diagnostics
```

An in-progress or unresolved recovery record must not be deleted merely because
its age exceeds an ordinary completed-operation retention period.

Terminal operation state is a possible trigger fact, not permission to destroy.

## 10. `derived_cache`

Includes rebuildable:

```text
Source Snapshot
Derived Index Metadata
Derived Current Pointer
operation/current pointers where rebuildable by accepted rules
quarantine/finding current pointers where rebuildable
privacy projection cache
dashboard cache
timeline/index cache
```

Derived caches may generally be removed independently of canonical source when:

- they are not required recovery evidence;
- the relevant operation is not incomplete;
- no external hold/policy requires preservation;
- removal cannot make canonical absence appear true.

Deleting derived state never deletes canonical source.

## 11. Export classes

### `export_bytes`

The actual output bytes bound by `deliberate_export@1`.

Examples:

```text
PDF
CSV
JSON
HTML
ZIP
```

### `export_provenance`

Includes:

```text
deliberate_export@1
export_source_inventory@1
```

and any future bounded export-disposition evidence accepted by Issue #21.

These classes are intentionally separate:

```text
export bytes deleted != export provenance deleted
export provenance retained != export bytes still exist
```

A retained receipt must not imply local artifact availability after authorized
byte disposition.

## 12. `exceptional_removal_certificate`

Includes:

```text
exceptional_removal@1
actor_directory_exceptional_removal@1
```

These are minimum surviving evidence of narrowly authorized exceptional removal.

Routine retention expiry does not automatically create Exceptional Removal.

A future disposition system must not target an Exceptional Removal certificate
using the ordinary Exceptional Removal mechanism itself.

## 13. Retention classification is not copied into domain schemas

Issue #21 rejects adding:

```json
{
  "retention_class": "...",
  "retention_until": "...",
  "delete_after": "...",
  "legal_hold": true
}
```

to every canonical record.

Reasons:

1. jurisdiction/policy changes would force domain-version churn;
2. one record can participate in correction/dependency constraints that alter
   actual disposition;
3. legal holds are external decisions;
4. retention dates can depend on external trigger facts;
5. Portia must not claim institution-wide records authority.

Instead, Portia exposes producer-owned classification through module
capability/policy mapping.

## 14. Observable trigger facts

Portia may establish facts such as:

```text
record_created
record_updated
work_closed
support_process_completed
actor_inactivated
contact_point_inactivated
operation_terminal
export_generated
export_superseded
exceptional_removal_effective
```

A deployment may also supply trusted external facts such as:

```text
school_year_ended
student_departed
graduation_date
institution_case_closed
policy_effective_date
```

Portia must preserve provenance for whichever fact a retention policy uses.

Portia must not fabricate a missing trigger date.

If a policy requires a trigger that cannot be established:

```text
retention evaluation = unresolved
```

and destructive action is blocked.

## 15. Trigger facts are not silently inferred from unrelated state

Do not infer:

```text
Event inactive -> school year ended
Support Process completed -> all associated records disposable
Actor inactive -> no historical attribution required
student removed from current roster -> departed institution
export superseded -> predecessor may be destroyed
```

A valid retention evaluation requires the exact trigger specified by the external
policy.

## 16. External policy profile input

A future Portia retention evaluator must be capable of consuming an externally
approved policy description equivalent to:

```text
policy authority/system
policy/profile ID
policy version
policy digest
effective date/version
jurisdiction/organization scope
Portia retention class
recognized trigger
minimum/maximum or disposition rule if supplied
hold override behavior
policy source/citation/reference
```

This is an **input contract boundary**, not Portia canonical domain truth.

Slice 5 deliberately does not publish a Portia-only retention-policy JSON schema
that a future suite-wide records system would then have to inherit.

## 17. Evaluation result vocabulary

A retention evaluation needs at least these semantic results:

```text
not_yet_eligible
eligible_pending_authorization
blocked
unresolved
authorized_for_module_action
```

Meanings:

### `not_yet_eligible`

The applicable policy/trigger says the minimum retention requirement has not
been met.

### `eligible_pending_authorization`

The applicable schedule/rule indicates eligibility, but required destruction
approval has not been supplied.

### `blocked`

A known preservation/hold/dependency/integrity condition prohibits the proposed
action.

### `unresolved`

Portia cannot establish required policy, trigger, scope, custody, or dependency
facts safely.

### `authorized_for_module_action`

An authoritative external disposition decision covers the exact Portia custody
and exact proposed action, and module-local blockers have been cleared.

This final state is still bounded to Portia-controlled custody.

## 18. Destructive action requires explicit authorization

Portia must never transform:

```text
eligible_pending_authorization
```

into destructive execution.

This is especially important for New Jersey public-school deployments, where
eligibility under a records schedule and authorization to destroy are separate
records-management steps.

Other jurisdictions may have different approval machinery, so the architecture
remains generic.

## 19. No hard-coded New Jersey schedule

The current New Jersey published schedule identifies:

```text
School District Retention Schedule: Active Records - Student Records
M700106-001
```

while the State directs agencies to Artemis for current schedule information and
disposition requests.

Portia therefore stores no constant equivalent to:

```text
NJ student behavior records = N years
```

A district-approved deployment policy may map one or more Portia retention
classes to an exact current New Jersey record series/rule.

That mapping remains external and versioned.

## 20. Module-local action vocabulary

A future Portia disposition adapter may support actions such as:

```text
delete_derived_cache
delete_export_bytes
delete_transient_staging
routine_dispose_canonical_payload
routine_dispose_operational_payload
archive_to_historical_custody
no_action
```

Support for an action does not authorize its use.

`routine_dispose_canonical_payload` is intentionally separate from
`exceptional_removal`.

The exact executable action set remains Slice 6/future runtime work.

## 21. Foreign custody

Portia may classify the Portia-owned reference/provenance it stores, but cannot
dispose foreign custody.

Examples:

```text
Portia Page Record disposition
!= Core RetainedSourceScan disposition

Portia source reference disposition
!= sibling canonical record disposition

Portia export disposition
!= Vitrine Snapshot/Export disposition

Portia Actor relationship disposition
!= Core roster disposition
```

A cross-module plan must delegate each owned item to its owning module.

## 22. Backup and external-copy boundary

Portia can verify only custody it controls.

A successful local disposition must not claim:

```text
all backups purged
email attachment recalled
downloaded copy destroyed
Vitrine copy destroyed
district archive destroyed
external submission destroyed
```

when those copies are outside Portia control.

Such state remains external/unresolved unless an authoritative system supplies a
separate verifiable result.
