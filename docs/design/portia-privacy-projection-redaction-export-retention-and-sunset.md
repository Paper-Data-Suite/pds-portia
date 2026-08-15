# Portia Privacy Projection, Redaction, Export, Retention, and Sunset Architecture

**Status:** Initial Issue #21 architecture; pre-schema Slice 1
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-14

> This document is architecture and product-policy design, not legal advice.
> Institutional counsel, records officers, administrators, and deployment policy
> remain authoritative for jurisdiction-specific disclosure, retention, hold,
> destruction, and requester-entitlement decisions.

## 1. Purpose

Issue #21 defines how Portia can produce useful teacher, participant, student,
family, aggregate, and export views without exposing unrelated people, creating
an authoritative student dossier, confusing export with disclosure, hard-coding
retention periods, breaking correction history, deleting foreign custody, or
inventing a `pds-sunset` implementation before that module exists.

The governing rule is:

> Canonical Portia records may preserve information needed for teacher-local
> support and historical integrity, but every projection, export, and
> disposition workflow must narrow that information to the exact purpose,
> subject, policy, authorization, and custody actually established.

## 2. Governing distinctions

```text
canonical record != projection
projection != export
export != disclosure
audience context != recipient authorization
record exists != field may be exposed

absent != withheld
withheld != unavailable
unavailable != false/no
redacted != corrected
manual-review-required != denied

derived history != authoritative student dossier
dashboard count != behavior fact
aggregate row != de-identified by default

work closed/completed != retention expired
retention class != retention duration
retention eligible != approved for destruction
deletion request != deletion authorization
hold input != Portia legal determination

invalidated/superseded != erasable
Exceptional Removal != routine retention cleanup
derived-cache deletion != canonical deletion

Portia reference != ownership of referenced custody
Portia disposition != Core/sibling disposition
module-local verification != proof all external copies are destroyed

future Sunset orchestration != module semantic authority
```

## 3. Existing meanings remain authoritative

Issue #21 is subordinate to ADRs 0001–0016.

Portia remains local-first, teacher-controlled, classroom-focused, and scoped to
one selected PDS workspace. It is not a district discipline system,
institutional student-record repository, clinical record system, IEP platform,
threat-assessment platform, legal case-management system, or authoritative
longitudinal student dossier.

Canonical records remain authoritative at their accepted locations. Reverse
links, indexes, current pointers, timelines, student histories,
participant-specific views, teacher-current summaries, dashboards, aggregate
summaries, privacy projections, and ordinary reports remain derived and
rebuildable unless a later accepted contract explicitly says otherwise.

No Issue #21 decision may silently retarget historical references to a successor.

## 4. Correction, disagreement, and removal

Issue #12 already establishes append-preserving correction and lifecycle
semantics. Material correction may use invalidation, supersession, replacement,
migration, ownership correction, or duplicate consolidation while historical
representations remain exact.

`statement_of_disagreement@1` remains linked to one exact canonical target.
Issue #21 must preserve the ability to include an applicable disagreement with
the contested portion when governing policy requires that relationship during
disclosure/export.

`exceptional_removal@1` remains exceptional. Ordinary lifecycle correction is
not physical removal.

Portia does not itself decide legal retention periods, legal holds, whether a
privacy/deletion request must be granted, whether destruction authorization is
legally sufficient, or whether every backup or external copy has been destroyed.

## 5. Highest-risk existing privacy surfaces

### Event / Participant / Role

Multi-participant Event context can identify unrelated students through
participant references, display snapshots, role labels, participant-set targets,
time/location/context, or rare combinations. Event membership does not make all
Event content equally projectable for every participant.

### Account

Account can preserve represented source identity, verbatim source wording,
recorder summary, elicitation context, firsthand/secondhand origin,
source-expressed uncertainty, participant targets, and source-artifact lineage.

The focal student may be the Account target without Portia being able to infer
that source identity or complete source text may be disclosed.

### Observation

Observation is direct/instrumented evidence rather than a reported Account, but
multi-target Observations still require participant-specific projection and
re-identification review.

### Communication / Actor / Contact Point

Communication already uses:

```text
ordinary
participant_limited
restricted
unknown
```

as `privacy_scope`. This remains a handling classification, not authorization.
Recipients, endpoint references, Actor Contact Points, summaries, attachments,
and relationships have independent privacy meaning.

### Support and downstream records

Support Process, Implementation, Fidelity, Follow-Up, Outcome, Reentry, and
Repair may contain several participants, providers, family collaborators,
perspectives, and historical judgments. Inclusion in support does not create
general disclosure permission.

### Paper/import and operations

Route IDs, Page Records, interpretation candidates, import identities, operation
journals, Quarantine, Integrity Findings, and diagnostics are provenance or
operational state. They are not ordinary student/family content merely because
they are resolvable.

## 6. Initial projection architecture

### 6.1 Ordinary projections are derived

Initial direction:

> Ordinary teacher-current, participant-specific, student-facing, family-facing,
> and aggregate views are derived/rebuildable products, not canonical domain
> records.

A later cache must remain rebuildable, nonauthoritative, source-bound,
policy-bound, privacy-minimized, and independently disposable.

This prevents a persistent parallel student history from becoming the dossier
Issue #21 is intended to prohibit.

### 6.2 Projection policy is closed

The producer rule should be:

```text
include only explicitly declared record/field semantics
```

not:

```text
include everything except currently known secrets
```

Unknown fields and unsupported contract versions must fail closed for outward
projection.

No generic bypass is accepted:

```text
include_private
include_all
admin_mode
raw_record
debug_export
```

A downstream consumer may narrow a Portia-approved projection but must not
broaden Portia's privacy floor.

### 6.3 Purpose is not authorization

Purposes to evaluate:

```text
teacher_current
participant_specific
student_facing
family_facing
aggregate_equity
administrative_export
```

They do not establish requester identity, parent/guardian status,
eligible-student status, legitimate educational interest, consent, legal
disclosure exception, or institutional authorization.

Authorization remains an explicit application/deployment/institution input.

### 6.4 Focal scope is exact

Participant-specific projection starts from:

```text
one exact Portia work
+ one exact focal participant/subject
+ one exact purpose
+ one exact policy version
```

It must not infer cross-class/cross-year continuity from names, contact values,
or similar roster fields.

Teacher-current views should default to explicit selected work/class/support
context, not a workspace-wide "everything about this student" view.

## 7. Projection disposition semantics

Issue #21 must preserve at least:

```text
included
    source exists and exact policy permits the represented content

absent
    source value/record does not exist

withheld
    source exists but the current projection must not expose it

unavailable
    referenced/expected source cannot currently be resolved or retrieved

requires_manual_review
    safe mechanical projection/redaction cannot be established
```

Invariants:

```text
withheld must not become absent
unavailable must not become false/no
manual review must not silently become included
withheld content must not leak through counts or flags unless policy permits it
```

Recipient-facing wording may be more privacy-minimal than the restricted
internal projection decision.

## 8. Mechanical redaction boundaries

Mechanical redaction is acceptable only when truthful meaning survives.

Projection must consider leakage through IDs, display snapshots, names, roles,
participant counts, target sets, source identities, quoted/free text,
timestamps, locations, rare combinations, filenames, paths, artifact metadata,
and reverse links.

Replacing a name with an opaque token does not prove de-identification.

If safe segregation/redaction cannot be established without destroying meaning,
the default automated result is:

```text
requires_manual_review
```

not automatic full disclosure, an invented sanitized summary, or
meaning-changing context removal.

No automated paraphraser is accepted in this foundation as a way to "sanitize"
third-party Account text.

## 9. Student- and family-facing projections

Student-facing and family-facing are separate purposes. Neither proves requester
identity or legal entitlement.

A bounded outward projection should generally:

- use understandable labels;
- distinguish source evidence from human judgment;
- preserve unresolved/inconclusive states;
- preserve applicable correction/supersession context;
- preserve applicable Statement of Disagreement relationships;
- avoid unrelated participant identity/content;
- avoid Contact Point values;
- avoid private operational details;
- avoid source paths/route internals;
- avoid implying omitted information is adverse.

## 10. Derived histories, dashboards, aggregates

No canonical:

```text
student_behavior_history
student_behavior_profile
student_dossier
risk_profile
discipline_score
```

is introduced.

A longitudinal view must be explicitly requested, scope-bounded,
source-traceable, policy-bound, and nonauthoritative.

Counts/timelines must reconcile correction and supersession so obsolete
predecessors are not counted as independent current facts.

Aggregate/de-identified projections must consider small cells, rare
combinations, exact time/location, free text, repeated queries, cross-table
linkage, and protected attributes. Removing a name is not sufficient
de-identification.

## 11. Deliberate export boundary

Initial direction:

> Durable export provenance is justified; durable ordinary projection state is
> not.

Export is a separate operation from viewing/searching and must bind:

```text
export scope
projection purpose/profile
projection policy identity/version
authorization decision/reference where available
exact source inventory
requesting/recording actor
generation time
output format/media type
output digest/size
privacy-safe disposition summary
```

Export bytes remain outside canonical JSON.

Safe export paths must be contained relative paths and must not encode student
names or sensitive semantic labels.

An export record/receipt, if adopted, is operational provenance rather than
behavior-domain truth.

Export generation does not prove disclosure, delivery, recipient identity,
receipt, read/open state, consent, or lawful basis.

## 12. Export correction/history

If durable export history is adopted:

```text
historical export bytes are immutable
current native correction does not rewrite old export
policy change does not rewrite old export
materially changed source/policy creates successor/new export state
exact semantic replay may reuse exact verified output
```

An old export that should no longer be used may require explicit
restriction/withdrawal/disposition rather than silent replacement.

## 13. Existing derived-source infrastructure: pressure point

Current `source_snapshot@1` is semantically relevant because it inventories exact
source representations for a derived projection generation.

But its `projection_kind` is a closed enum limited to Issue #13 kinds such as:

```text
incoming_reference_index
lifecycle_timeline
current_state_view
work_summary
class_summary
```

It does not contain participant/student/family/export kinds.

Current `derived_index_metadata@1` uses the same closed vocabulary and
specifically represents derived index generations.

Issue #21 must not silently broaden either published v1 schema.

Before export/projection schema work, explicitly choose among:

1. `source_snapshot@2` with justified new semantics;
2. an export-specific exact-source snapshot;
3. an internal projection source inventory plus durable export-only provenance;
4. another minimal versioned approach.

Also decide whether `derived_index_metadata@1` needs a successor at all. Outward
privacy projection is not automatically an index.

## 14. Records/privacy request boundary

Request intents to evaluate:

```text
inspect_access
export_copy
amend_correct
statement_of_disagreement
restrict_withhold
delete_destroy
other
```

Possible processing states:

```text
received
needs_policy_review
approved
partially_approved
denied
unresolved
completed
```

A deletion request never means `delete now`.

An amendment request should use existing correction/disagreement machinery where
applicable.

Slice 1 deliberately leaves open whether a durable Portia request record is
necessary or whether this remains an application/institution boundary.

## 15. Retention architecture

### 15.1 Portia owns classification and custody truth

Portia can truthfully provide:

```text
what Portia custody exists
which module owns it
which exact work/record/Actor/export it represents
which correction/dependency lineage it participates in
which stable retention class applies
which trigger facts Portia can establish
which module-local disposition actions are technically supported
which integrity blockers exist
```

### 15.2 Institution/deployment owns disposition authority

Portia must not independently decide:

```text
retention duration
legal hold existence
requester entitlement
disclosure exception
destruction authorization
backup purge requirement
state/district schedule interpretation
```

Retention periods therefore must not be hard-coded into domain schemas.

### 15.3 Retention classes to evaluate

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
disclosure_audit_if_adopted
exceptional_removal_certificate
core_owned_retained_source_reference
```

These are policy keys, not durations. Prefer a versioned mapping layer rather
than adding `retention_class` to every domain record.

### 15.4 Trigger fact is not policy

Potential observable facts include record creation, work closure, Support
Process completion, school-year end, Actor/Contact Point inactivation, export
generation, or request resolution. None is itself permission to dispose.

## 16. Holds and preservation constraints

Potential blockers include:

```text
outstanding access/inspection request
outstanding amendment/disagreement process
legal/litigation hold
subpoena/court-order process
special-education process
civil-rights process
records audit
integrity/recovery uncertainty
pending disclosure/export obligation
other local policy hold
```

Portia should consume an exact authoritative decision or represent the condition
as unresolved. It must not infer a legal hold from domain content.

Slice 1 leaves open whether a Portia-local hold record is warranted; a future
suite records layer may be the better owner.

## 17. Derived-state retention

Derived state is separately disposable.

```text
delete derived cache != delete canonical source
missing derived state != canonical absence
stale derived state must not resurrect removed source
derived state should not outlive source without explicit policy
temporary staging requires bounded recovery/cleanup
```

Removed/unavailable source must not be reconstructed from stale derived output
and written back as canonical truth.

## 18. Cross-module custody boundary

Portia may reference but does not own Core roster records, Core retained scans,
Core publication state, sibling canonical records, Vitrine immutable
Snapshot/Export custody, or other externally owned files.

Therefore:

```text
remove Portia Page Record != remove Core RetainedSourceScan
remove Portia source reference != remove sibling source
dispose Portia export != erase a Vitrine Snapshot containing a prior projection
```

Cross-module disposition requires each owning module to act on its own custody.

## 19. Future Sunset boundary

No `pds-sunset` repository/package currently exists.

Issue #21 therefore defines required future capabilities, not a concrete Sunset
API.

A future Sunset-like orchestrator should:

1. discover participating module retention/disposition capabilities;
2. obtain module-owned custody inventories and stable retention classes;
3. obtain exact dependency/correction-lineage constraints;
4. consume institution-approved retention/hold decisions;
5. produce dry-run disposition plans;
6. surface unresolved policy/ownership;
7. coordinate module-owned actions in safe order;
8. never delete arbitrary paths based on filename inference;
9. use crash/recovery semantics for partial operations;
10. verify only custody it can actually verify;
11. preserve privacy-minimal disposition evidence;
12. leave external/backup copies explicitly unresolved when outside control.

It must not decide Portia domain meaning or institutional legal policy.

## 20. Future module retention adapter boundary

The Portia side of a future PDS-wide adapter should be capable of supplying:

```text
module_id
adapter/profile version

owned canonical custody inventory
owned derived/export custody inventory
stable retention classification
exact semantic identity/scope
dependency and correction-lineage requirements
supported disposition actions
preconditions/blockers/unresolved conditions
module-local planning/validation
module-owned execution
module-local result verification
```

Issue #21 must not import nonexistent `pds-sunset`, make a Portia-only schema a
permanent suite standard by implication, or turn Core into retention-policy
authority merely because Core is shared.

The final ADR should identify concepts that are candidates for later shared/Core
protocol extraction.

## 21. Initial persisted-contract evaluation

No public schema is added in Slice 1.

| Candidate | Initial direction | Reason |
| --- | --- | --- |
| ordinary privacy projection record | **do not persist by default** | avoids dossier/parallel-authority risk |
| projection policy identity/profile | **required concept; persisted form unresolved** | exact policy provenance needed |
| projection disposition | **required semantics; wire form unresolved** | preserve included/absent/withheld/unavailable/manual-review |
| deliberate Export record/receipt | **likely justified** | durable source/policy/output provenance |
| export identifier | **likely justified if Export persists** | stable nonsemantic history |
| records/privacy request record | **evaluate later** | audit value without legal case-management creep |
| retention class mapping | **required; avoid per-record field** | semantic classification, not duration |
| retention policy profile | **likely external/deployment input** | institution policy authority |
| hold/preservation record | **ownership deferred** | may belong to suite/institution layer |
| retention evaluation | **likely derived/planning state** | candidate disposition is not authority |
| disposition certificate | **evaluate with Exceptional Removal/Sunset** | avoid duplicate removal semantics |
| Sunset adapter schema | **do not create in Portia now** | suite contract not yet accepted |
| `source_snapshot@1` reuse | **cannot reuse unchanged** | closed projection-kind vocabulary |
| `source_snapshot@2` | **candidate, not accepted** | possible exact source provenance |
| `derived_index_metadata@1` reuse | **probably not for outward views** | outward projection is not necessarily an index |

## 22. Initial implementation sequence

```text
Slice 1  architecture + policy checkpoint; no schemas
Slice 2  projection semantics + complete sensitivity matrix
Slice 3  participant/student/family redaction rules
Slice 4  deliberate export/provenance contracts
Slice 5  retention/request/hold architecture
Slice 6  future Sunset/module-adapter boundary
Slice 7  application-invalid/failure matrix + synthetic examples
Slice 8  pre-ADR drift + ADR 0017 + documentation/acceptance reconciliation
```

A final closeout slice may be separated if post-ADR validation warrants it.

## 23. Non-goals

Issue #21 does not implement institutional authentication/SSO, a student/family
portal, legal advice, automatic FERPA entitlement decisions, guardianship
resolution, OPRA adjudication, subpoena/court-order workflow, district records
office functionality, backup administration, secure media wiping outside
controlled custody, `pds-sunset`, suite-wide production disposition
orchestration, Meridian grading/reporting, Vitrine publication, or predictive
behavior/risk scoring.

## 24. Slice 1 acceptance

Slice 1 is complete when repository anchors and branch point are recorded,
policy inputs are recorded, ADR 0017 availability is checked, existing privacy /
correction / removal / derived infrastructure is reconciled, the closed-v1
source-snapshot pressure point is recorded, ownership boundaries are explicit,
no public wire contract is added prematurely, and the local schema-validation
baseline is observed on the exact feature branch.
