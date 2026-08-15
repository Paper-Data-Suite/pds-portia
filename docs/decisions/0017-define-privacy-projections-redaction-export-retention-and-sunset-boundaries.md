# ADR 0017: Define Privacy Projections, Redaction, Export, Retention, and Sunset Boundaries

- **Status:** Accepted
- **Date:** 2026-08-14
- **Decision owners:** Portia maintainers
- **Related issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Builds on:** ADR 0002, ADR 0003, ADR 0004, ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012, ADR 0013, ADR 0014, ADR 0015, and ADR 0016
- **Preserves:** teacher-local scope; exact historical identity; correction history; privacy-by-design; Core ownership of shared identity/PDS2 infrastructure; producer ownership of sibling records

## Context

Portia now has a complete foundation through paper-assisted capture and imports:

```text
Event
→ Accounts / Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Implementation
→ Fidelity
→ Follow-Up / Outcome / Reentry / Repair
```

with supporting:

```text
Actor Directory
lifecycle/correction/disagreement/migration
Exceptional Removal
Operation Journal / Lock
Integrity Finding / Quarantine
derived indexes and pointers
paper capture / PDS2 provenance
structured import provenance
```

Those canonical records can contain information needed for teacher-local support
and historical integrity. They therefore cannot be copied wholesale into every
student, family, administrative, aggregate, or archival surface.

The governing distinctions are:

```text
canonical record != projection
projection != export
export != disclosure
audience context != recipient authorization
record exists != field may be exposed
withheld != absent
unavailable != false/no
redacted != corrected
derived history != authoritative student dossier
work closed/completed != retention expired
retention eligible != destruction authorized
deletion request != deletion authorization
record invalidated/superseded != record may be erased
Exceptional Removal != routine retention disposition
Portia retention class != institution retention policy
Portia disposition candidate != suite-wide destruction authority
```

Issue #21 therefore establishes privacy-minimized outward projection, deliberate
export provenance, semantic retention classification, records-request/hold
boundaries, and the module-side capabilities a future suite-wide disposition
orchestrator will require.

### Pre-ADR drift check

Immediately before accepting this ADR:

```text
pds-portia/main
2ec841ffdf9c20850cbaef5811ca20720dc5954b

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
3ae37eaaf89cf913020a5afc75bc11a68df0d5cc

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c

pds-vitrine/main
16317d8764a2e79018aa2bc7082faf66759c13b6

pds-concord/main
e6db668f0f8729b058f34cdda86a4cb443ca068d
```

These exactly match the review checkpoints recorded in Issue #21. No repository
anchor moved during implementation.

No `pds-sunset` repository exists at this checkpoint.

ADR 0017 was unused immediately before this file was added.

The authoritative local branch checkpoint immediately before ADR acceptance is:

```text
Ran 1077 tests in 305.924s

OK
```

with `git diff --check` clean.

## Decision

### 1. Canonical records remain authoritative; ordinary privacy projections remain derived

Portia does not introduce a canonical student dossier, student profile, family
profile, behavior history, or longitudinal student record.

The following remain derived/rebuildable:

```text
teacher-current views
participant-specific views
student-facing views
family-facing views
aggregate-equity views
dashboards
timelines
reverse links
histories
privacy projections
ordinary reports
```

Projection is purpose-bounded representation over exact canonical state.

Ordinary projections are not persisted by default.

### 2. Projection purpose is closed and does not authorize disclosure

Issue #21 accepts the initial closed purpose vocabulary:

```text
teacher_current
participant_specific
student_facing
family_facing
aggregate_equity
administrative_export
```

A purpose identifies the intended representation policy.

It does not authenticate a requester, establish a guardian relationship, prove
FERPA entitlement, establish legitimate educational interest, authorize an
artifact, or record disclosure.

Student-facing and family-facing are separate policy profiles; family-facing is
not automatically a broader student-facing profile.

### 3. Projection policy is allowlist-oriented, exact, and versioned

Every projection/export decision is based on an exact policy identity equivalent
to:

```text
policy_id
policy_version
policy_digest
```

Known source contract + known field semantics + known purpose + known focal scope
+ exact policy rule are required before inclusion.

Unknown fields, unknown source kinds, and unsupported contract versions fail
closed.

Consumer shortcut flags such as:

```text
include_private
include_all
raw_record
raw_graph
admin_mode
debug_export
skip_redaction
trust_requester
```

must never broaden the producer privacy floor.

### 4. Five projection dispositions remain semantically distinct

Issue #21 accepts:

```text
included
absent
withheld
unavailable
requires_manual_review
```

They must not be collapsed.

In particular:

```text
withheld != absent
unavailable != absent
unavailable != false/no
requires_manual_review != safe_to_include
```

Outward rendering may conceal the existence of withheld material when even
existence is sensitive.

### 5. Redaction is field/segment-aware and meaning-preserving

A record being eligible does not make every field eligible.

Portia evaluates field classes including:

```text
focal identity
third-party identity
direct contact
source narrative
human judgment
shared context
source locator
operational provenance
integrity diagnostics
correction history
```

Mechanical redaction must consider direct and indirect identification through:

```text
names
native IDs
display snapshots
roles
counts
targets
source identity
quotes/free text
timestamps
locations
rare combinations
filenames/paths
artifact metadata
reverse links
```

Removing names alone is not de-identification.

When removing third-party information would alter the proposition, source/target
relationship, attribution, evidence basis, or practical meaning:

```text
requires_manual_review
```

rather than automatic paraphrase.

### 6. Multi-participant records do not become falsely singular

A focal projection can hide unrelated participants without rewriting a
multi-participant source as though it was natively about one person.

Portia preserves the distinction between:

```text
native source scope
focal applicability
outward representation
```

Unrelated identity, native IDs, role snapshots, counts, and contextual details
are independently evaluated.

`reported_involved` remains exactly that and never becomes responsibility,
fault, guilt, offender status, or Determination.

### 7. Account, Observation, Communication, and Actor privacy remain distinct

For Account, independently evaluate source identity, target, source-origin
status, certainty, content segments, elicitation context, related Accounts, and
source artifacts.

A `verbatim_quote` must not be edited/paraphrased and still represented as the
original quote.

For Observation, structured focal measurements may be separable from unsafe
narrative, but source artifacts remain independently authorized.

For Communication:

```text
ordinary
participant_limited
restricted
unknown
```

remains handling classification, not authorization.

`restricted` and `unknown` fail closed for ordinary outward use.

Recipients are individually evaluated; endpoint references and exact contact
values remain withheld by default.

Actor identity or Actor-to-Student Relationship never proves guardianship,
custody, employment, licensure, institutional authority, or disclosure
authorization.

### 8. Source-artifact authorization is independent

The following remain distinct:

```text
record projection authorization
!= source-artifact authorization
!= attachment authorization
!= Core retained-source authorization
!= sibling-module source authorization
```

A safe projected record does not grant access to raw scans, attachments, source
files, contact endpoints, or foreign-module records.

### 9. Correction/currentness/disagreement must remain truthful in projection

Exact historical references never silently follow a successor/current record.

A current projection must not present invalidated/superseded content as current.

When a Statement of Disagreement is applicable to material being disclosed, the
projection/export must preserve enough disagreement relationship to avoid
misleading presentation.

If the disagreement itself contains unresolved third-party material, the
contested content and disagreement may become one manual-review disclosure unit.

Redaction never changes the canonical record and is not correction.

### 10. Aggregate-equity projection is not name-stripping

Aggregate projections default away from:

```text
raw Account text
Communication summaries
Contact Point values
native student rows
source paths
operational diagnostics
free-text grouping keys
```

Stable native IDs are still identifiers.

Small/rare cells, repeated queries, time/location combinations, and other
linkage can create re-identification risk.

Numeric thresholds remain policy parameters, not universal legal constants.

### 11. Deliberate export is a separate immutable workflow

Issue #21 accepts three public contracts:

```text
portia_deliberate_export_id@1
export_source_inventory@1
deliberate_export@1
```

with opaque identifier prefix:

```text
pexp_
```

One `pexp_` represents one accepted immutable output artifact.

Multiple requested formats receive distinct export identities even if their
source/projection bytes happen to be equivalent.

Export is deliberate; it is never a side effect of ordinary view/search/report
generation.

### 12. `source_snapshot@1` remains unchanged

Existing `source_snapshot@1` remains the discovery/filesystem source inventory
for rebuildable derived projections.

It is not widened into outward export semantics and no `source_snapshot@2` is
created merely to add export purposes.

`export_source_inventory@1` instead binds exact source representations that
materially contributed to one accepted deliberate export.

It does not copy every withheld/unavailable identity into export provenance.

### 13. Deliberate export binds exact provenance without becoming a dossier

`deliberate_export@1` binds:

```text
export identity
projection purpose
exact export scope
focal subject when required
policy ID/version/digest
positive authorization provenance
exact contributing source inventory
projection-decision digest
privacy-minimized disposition counts
manual-review status
one output artifact path/length/SHA-256
exact Operation Journal revision
request/generation attribution and time
optional supersession
```

Output bytes remain outside canonical JSON.

Export paths derive from opaque export identity and must not encode person,
class-title, behavior, support, or other unnecessary PII.

### 14. Export generation is not disclosure

Preserve:

```text
export generated != disclosure
export generated != delivered
export generated != received
export generated != read
export generated != consent
export generated != legal notice
export generated != external acceptance
```

`deliberate_export@1` therefore contains no recipient/delivery/read fields.

Any later institutional disclosure/audit integration remains a separate
contract/system boundary.

### 15. Historical exports are immutable

Later source correction, policy change, authorization change, redaction-rule
change, or renderer change does not rewrite an accepted historical export.

A newly requested/current export receives a new `pexp_`.

Optional supersession identifies a later export as the current-use replacement;
it does not erase, recall, or authorize destruction of the predecessor.

### 16. Export generation reuses coordinated-operation recovery

Durable export creation reuses Portia's accepted Operation Journal/Lock
infrastructure.

If artifact bytes were durably accepted but receipt persistence was interrupted,
recovery verifies the exact existing artifact and creates only the missing
receipt.

It must not generate another artifact merely because the receipt write failed.

### 17. Portia uses semantic retention classes, not hard-coded legal periods

Issue #21 accepts these Portia semantic retention classes:

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

These classes are stable producer-side policy-mapping keys.

They are not durations and are not added as `retention_until`, `delete_after`,
or `legal_hold` fields to every domain record.

### 18. Retention uses exact trigger facts and external policy provenance

Portia may establish observable facts such as:

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

Institution/deployment systems may supply externally authoritative facts such as
school-year end, graduation/departure, institution case closure, or policy
effective date.

Portia must not fabricate a missing trigger.

A future evaluator must preserve exact external policy identity/version/digest
and the trigger evidence relied upon.

### 19. Eligibility, authorization, blockers, and unresolved state remain distinct

Retention evaluation requires semantic results equivalent to:

```text
not_yet_eligible
eligible_pending_authorization
blocked
unresolved
authorized_for_module_action
```

A schedule/policy indicating eligibility never by itself authorizes destruction.

Missing policy, missing trigger facts, unresolved custody, incomplete dependency
graphs, recovery uncertainty, or unresolved holds fail closed for automatic
destructive action.

### 20. Portia does not become the institution's legal/request case system

Issue #21 does not publish Portia canonical records for:

```text
portia_privacy_request
portia_legal_hold
portia_records_case
portia_retention_policy
```

Portia may accept local intent such as:

```text
inspect_access
export_copy
amend_correct
statement_of_disagreement
restrict_withhold
delete_destroy
other
```

but request intent does not establish entitlement or approval.

The institution/deployment layer owns legal identity, legal entitlement,
deadline/case management, hold decisions, records-officer decisions, and
destruction authorization.

### 21. Outstanding preservation decisions block destructive action

When authoritative input says exact Portia custody is covered by an outstanding
access/amendment process, legal/litigation hold, special-education process,
civil-rights process, records audit, local policy hold, or similar preservation
decision:

```text
destructive disposition = blocked
```

Hold release must be explicit.

Age, inactivity, school-year end, supersession, or teacher belief do not
implicitly release a hold.

### 22. Correction/disagreement history is a retention dependency, not eternal storage

Portia's append-preserving correction design means ordinary correction does not
erase history.

It does not mean all historical representations must be kept forever regardless
of external policy.

Routine disposition must evaluate coherent predecessor/successor, Amendment,
Statement of Disagreement, Ownership Correction, Record Migration, Dependency,
and Exceptional Removal certificate relationships.

Required disagreement context cannot be deleted while a surviving contested
record still requires it.

### 23. Exceptional Removal remains exceptional

Existing `exceptional_removal@1` remains the narrow workflow for exceptional
authorized removal.

Routine schedule-based expiry does not automatically create Exceptional Removal.

Examples that do not by themselves justify Exceptional Removal include:

```text
retention period expired
student left class
school year ended
record is superseded
teacher wants cleanup
export is old
```

Routine records disposition is a separate future module/Sunset runtime path.

### 24. Derived state cannot extend or resurrect retention

Derived caches may be independently removable when they are rebuildable and not
required for recovery/hold evidence.

Deleting a cache never implies canonical deletion.

After lawful source disposition, stale derived state must be cleaned/rebuilt so
it cannot retain or reconstruct substantive source content beyond permitted
retention.

### 25. Export bytes and export provenance have independent retention

Preserve:

```text
export bytes deleted != export provenance deleted
export provenance retained != export bytes still exist
```

A future disposal-evidence mechanism may report that an artifact is no longer
available; the historical `deliberate_export@1` receipt is not silently rewritten
to simulate that later event.

### 26. Portia can verify only custody it controls

A successful Portia disposition must not claim:

```text
district backups purged
email attachment destroyed
downloaded copy destroyed
Core-owned retained scan destroyed
Vitrine copy destroyed
external submission destroyed
```

unless the owning/external system provides separate bounded verification.

### 27. Foreign-module custody remains owned by the producer

Portia may dispose only Portia-owned custody.

Examples:

```text
Portia Page Record disposition
!= Core RetainedSourceScan disposition

Portia source-reference disposition
!= sibling canonical-record disposition

Portia export disposition
!= Vitrine Snapshot/Export disposition
```

A future cross-module plan delegates each owned action to the owning module.

### 28. Future Sunset is orchestration-only

No `pds-sunset` repository exists and Issue #21 creates no import/dependency on
one.

A future Sunset-like module would orchestrate:

```text
policy-fed cross-module inventory
dry-run planning
plan revision
safe ordering
fan-out to module adapters
cross-module progress
restart/recovery coordination
bounded results
unresolved/outside-control reporting
```

It would not interpret Portia domain meaning or directly unlink Portia files.

### 29. Portia defines module-side capability requirements without publishing a premature suite protocol

Portia must eventually provide capabilities equivalent to:

```text
enumerate_owned_custody
classify_owned_custody
describe_dependencies
describe_trigger_facts
describe_supported_actions
evaluate_module_blockers
validate_candidate_action
execute_module_action
verify_module_action
describe_unresolved_foreign_custody
```

These are conceptual capabilities, not accepted method names.

Shared adapter envelopes/version negotiation/plan/result contracts are deferred
to future suite architecture and should likely live in Core/shared protocol
rather than Portia's schema namespace.

### 30. Dry-run planning is non-destructive and candidate validation expires on drift

A future disposition orchestrator must separate planning from execution.

A candidate is bound to exact current-state evidence.

If source/correction/dependency/hold/policy state changes after planning:

```text
stale_candidate
```

and revalidation/replanning is required.

The orchestrator must never delete by filename, path age, guessed student
identity, or other nonsemantic filesystem heuristics.

### 31. The orchestrator coordinates; Portia mutates and verifies

For Portia-owned durable changes:

```text
orchestrator selects candidate
→ Portia validates exact current state
→ Portia applies its own operation/recovery controls
→ Portia performs its own supported action
→ Portia verifies its own result
→ orchestrator records bounded cross-module outcome
```

A future Sunset module must not directly unlink Portia canonical files.

### 32. Cross-module disposition is recoverable, not magically atomic

Partial multi-module success is possible and must be represented honestly.

A successfully committed destructive Portia action is not "rolled back" by
reconstructing deleted canonical content merely because another module failed.

Restart asks each module to reconcile exact prior state before replaying any
remaining action.

Missing bytes alone do not prove prior deletion committed.

### 33. Core remains shared infrastructure, not institutional records authority

Core remains authoritative for shared workspace/class/roster identity,
module-qualified references, PDS2 routing, retained-source custody, and related
suite infrastructure.

Core does not become:

```text
institution retention-policy authority
legal-hold adjudicator
destruction-approval authority
module-domain semantic interpreter
```

Future adapter discovery/version negotiation may be appropriate shared/Core
mechanics, but policy and module semantics remain outside Core.

### 34. Institution/deployment policy owns legal and authorization decisions

The application/deployment/institution layer owns or supplies authoritative
decisions for:

```text
requester authentication
recipient authorization
guardian/custody/eligible-student status
legitimate educational interest
FERPA/state/district rule interpretation
retention schedule mapping
legal/preservation holds
destruction authorization
disclosure-log obligations
backup/external-copy requirements
```

Portia records the bounded input it relied upon where appropriate but does not
turn that input into a legal conclusion.

### 35. Some privacy/legal facts remain impossible for Portia to determine automatically

Portia cannot automatically prove:

```text
that a requester is legally entitled
that a relationship label establishes guardianship
that a redacted free-text passage preserves meaning
that a de-identified aggregate cannot be re-identified in context
that a legal hold applies or has been released
that a disclosure exception is legally sufficient
that all backups/external copies were destroyed
that foreign-module custody was removed without owner verification
```

The safe result is manual review, external decision, blocked/unresolved state,
or bounded local verification as appropriate.

### 36. Public Issue #21 contracts are closed and versioned

Issue #21 publishes exactly:

```text
portia_deliberate_export_id@1
export_source_inventory@1
deliberate_export@1
```

All are Draft 2020-12 public schemas with immutable canonical `$id` values and
closed object shapes where applicable.

No published pre-Issue-21 schema `$id` is mutated.

### 37. Accepted opaque Issue #21 identifier prefix

```text
Deliberate Export: pexp_
```

The identifier is opaque and does not encode student/person identity, class,
work, projection purpose, policy, date, format, digest, path, or disclosure
outcome.

### 38. Application-invalid and runtime-failure rules remain outside structural schema

JSON Schema cannot prove requester entitlement, source currentness, redaction
meaning, re-identification risk, exact cross-record resolution, hold
applicability, correction-graph completeness, cross-module custody, or external
destruction completion.

Issue #21 therefore records explicit application-invalid and runtime
failure/recovery matrices.

Application-invalid does not automatically mean Integrity Finding or Quarantine.

### 39. Synthetic examples remain synthetic and noncanonical

Issue #21 validates 24 cross-cutting synthetic scenarios covering projection,
redaction, correction/disagreement, aggregation, export, retention, foreign
custody, and future Sunset planning.

The scenario descriptors are test fixtures only.

They are not legal cases, retention policies, holds, disposition certificates,
or public Portia records.

## Responsibility Matrix

| Concern | Portia | Core/shared | Institution/deployment | Future Sunset |
| --- | --- | --- | --- | --- |
| Portia record meaning | owns | does not own | may configure workflows | consumes |
| Canonical Portia custody | owns | path/workspace primitives | governs policy | coordinates |
| Roster identity | consumes | owns | supplies upstream roster policy | references |
| PDS2/retained scans | references | owns | governs access/retention | coordinates owner action |
| Projection/redaction semantics | owns producer floor | shared primitives only | supplies authorization/policy | does not broaden |
| Recipient entitlement | does not decide | does not decide | owns authoritative decision | consumes |
| Deliberate export provenance | owns | shared path/hash primitives | governs disclosure/use | may coordinate disposition |
| Disclosure log | integration boundary | possible shared mechanics | owns requirement/system | may reference |
| Retention classes | owns semantic mapping | may host shared protocol | maps to approved policy | consumes |
| Retention durations | does not own | does not own | owns | consumes |
| Legal/preservation holds | consumes authoritative input | does not adjudicate | owns | consumes |
| Destruction approval | does not create legal authority | does not create legal authority | owns | consumes |
| Portia mutation/verification | owns | shared filesystem primitives | authorizes | requests/coordin­ates |
| Cross-module plan | participates | may host shared envelopes | authorizes policy | owns orchestration |
| External/backup destruction | cannot verify | cannot globally verify | owns/coordinates external systems | reports unresolved unless verified |

## Consequences

### Positive

- Portia can support privacy-minimized student/family/administrative use without
  weakening canonical history.
- Multi-party evidence keeps exact native meaning.
- Deliberate exports have exact replay/audit provenance without becoming
  disclosure records.
- Retention policy can vary by jurisdiction/institution without schema churn.
- Portia remains compatible with a future suite-wide Sunset module without a
  dependency on an imaginary current package.
- Cross-module destructive work remains module-owned and recoverable.
- Existing correction, Exceptional Removal, Operation Journal, and Core/PDS2
  boundaries remain coherent.

### Tradeoffs

- Some projections require manual review.
- Some retention actions remain blocked/unresolved until external institutional
  decisions exist.
- No single Portia field answers "when may this be deleted?"
- No one-command suite-wide wipe is defined.
- The future shared Sunset adapter wire protocol still requires separate suite
  architecture.
- Old export bytes may persist until separately authorized for disposition even
  after a successor export exists.

## Alternatives Rejected

### Persist one canonical student privacy profile/history

Rejected because it would create the dossier architecture Portia explicitly
avoids and duplicate class/work-owned source records.

### Use one `public/private` Boolean

Rejected because identity, contact data, source narrative, judgment, artifact
access, operational provenance, and correction history have materially
different exposure semantics.

### Treat family-facing as automatically authorized

Rejected because audience/purpose does not establish requester identity,
guardian status, or disclosure authority.

### Reuse `source_snapshot@1` for exports

Rejected because it is a discovery/filesystem inventory for rebuildable derived
projections, not outward export provenance.

### Log export generation as disclosure

Rejected because a locally generated file may never be sent, delivered, or read.

### Hard-code New Jersey retention periods

Rejected because Portia semantic classes are not jurisdictional schedules and
schedule eligibility is not equivalent to destruction authorization.

### Use Exceptional Removal for routine retention expiry

Rejected because Exceptional Removal is a narrow exceptional-erasure workflow,
not ordinary records disposition.

### Create Portia legal-hold/privacy-request case records

Rejected because Portia cannot authoritatively establish the legal/institutional
case facts those records would imply.

### Let Sunset delete module paths directly

Rejected because paths do not establish domain identity, dependency semantics,
or safe mutation/recovery rules.

### Publish the future shared adapter protocol under Portia now

Rejected because `pds-sunset` does not exist and the shared wire protocol
requires suite-level ownership decisions not appropriate to one module.

## Follow-up

Issue #22 should exercise these boundaries in broader end-to-end representative
synthetic contract graphs.

Issue #23 should audit the complete Portia foundations for contradictions,
boundary drift, identifier/schema consistency, privacy/retention safety, and
remaining execution dependencies.

A future Core/Sunset architecture effort should decide the final shared adapter
wire/API protocol without changing the Portia semantic ownership accepted here.
