# Portia JSON Schemas

Portia uses JSON Schema Draft 2020-12 for structural validation of canonical
records, reusable value objects, and explicitly noncanonical derived projections.

## Canonical schema identity

Every public schema has one canonical `$id`. Once published, that `$id` keeps
one stable meaning.

The three initial Event-family version-1 schemas predate the versioned-path
policy and remain at their existing locations:

- `schemas/event.schema.json`
- `schemas/event-participant.schema.json`
- `schemas/event-participant-role.schema.json`

New public schemas use matching versioned paths and `$id` values beneath
directories such as `schemas/v1/` and `schemas/v2/`.

Canonical schemas do not use mutable `latest` or `current` identities.

## Schema catalog

`schemas/schema-catalog.json` is a noncanonical tooling catalog. It maps a
conceptual contract name and schema version to the canonical schema `$id` and
the repository-relative source path.

The catalog contains the retained Event-family contracts, versioned shared
contracts, the Actor Directory record family, the Account and Observation
version-1 evidence contracts, the Review/Classification/Hypothesis/Determination
version-1 judgment contracts, and additive Actor-aware operational version-2
contracts implemented by Portia.

## Identifier contracts

Portia-owned identifiers are independently addressable beneath
`schemas/v1/identifiers/`.

The initial prefixes are:

- Event: `evt_`
- Support Process: `sup_`
- Support Process Participant: `spp_`
- Support Need: `spn_`
- Support Goal: `spg_`
- Support: `spt_`
- Intervention: `int_`
- Implementation: `imp_`
- Fidelity: `fid_`
- Actor: `actr_`
- Actor Contact Point: `acp_`
- Actor-to-Student Relationship: `asrel_`
- Actor–Roster Student Collision: `arsc_`
- Event Participant: `ep_`
- Event Participant Role: `epr_`
- Account: `acct_`
- Observation: `obs_`
- Review: `rvw_`
- Classification: `cls_`
- Hypothesis: `hyp_`
- Determination: `det_`
- Response: `rsp_`
- Communication: `comm_`
- Work Relationship: `rel_`
- Lifecycle Transition: `lct_`
- Lifecycle-History Correction: `lhc_`
- Amendment: `amd_`
- Statement of Disagreement: `sod_`
- Dependency: `dep_`
- Record Migration: `mig_`
- Ownership Correction: `owc_`
- Exceptional Removal: `rmv_`
- Coordinated Operation: `op_`
- Operation Step: `step_`
- Operation Lock: `lock_`
- Quarantine: `qnt_`
- Finding Acknowledgement: `fack_`
- Finding Suppression: `fsup_`
- Derived Generation: `dgen_`

The operation, step, Quarantine, acknowledgement, suppression, and generation
suffixes are opaque. `portia-lock-id` is specialized: `lock_` is followed by
exactly 64 lowercase hexadecimal characters derived from the deterministic
canonical lock key.

Portia-owned identifiers:

- are JSON strings;
- preserve case and leading zeros;
- permit only ASCII letters, digits, underscores, and hyphens;
- reject periods, whitespace, path separators, control characters, and non-ASCII characters;
- and have a maximum length of 128 characters.

Event and Support Process identifiers are also used as Core
`ModuleWorkRef.work_id` values. Their alphabet therefore remains compatible
with Core's shared identifier contract.

The retained Event-family version-1 schemas are historical contracts and are
not rewritten by this identifier correction. New reconciled record schemas
must compose the versioned Portia identifier contracts.

`structurally-safe-external-id.schema.json` provides only a conservative
structural and path-safety check for an identifier owned by Core or another
module. Passing it does not establish registration, existence, uniqueness,
ownership, lifecycle, contract support, or authorization.

## Primitive shared reference contracts

The first independently reusable reference contracts are stored beneath:

    schemas/v1/references/

They are:

- `roster-student-ref.schema.json`
- `actor-ref.schema.json`
- `local-record-ref.schema.json`
- `portia-work-ref.schema.json`
- `portia-work-record-ref.schema.json`
- `module-work-record-ref.schema.json`

`roster_student_ref` preserves Core roster identity as the exact
`class_id + student_id` pair. Its structural schema does not prove that either
identifier resolves in the current workspace.

`actor_ref` identifies one Portia Actor Directory record and contains no
display snapshot or work-specific role information.

`local_record_ref` identifies a typed record within exactly one work scope
supplied by its consuming schema. Its required `contract_version` property may
contain a version string or explicit `null`; omission is not equivalent to
`null`.

`portia_work_ref` identifies one Portia Event or Support Process. It requires
`module_id = "portia"` and enforces agreement between `work_kind` and the
Portia-owned `work_id` prefix.

`portia_work_record_ref` identifies one child record in another explicitly
identified Portia work. It contains exactly `work_ref` and `record_ref`; the
sibling `work_ref` is the sole work-scope provider for the nested local record
reference.

`module_work_record_ref` identifies one record owned by one explicitly named
module work. It contains exactly `work_ref` and `record_ref`, using the exact
Core `ModuleWorkRef` and `ModuleRecordRef` wire shapes. Both nested values
retain `module_id`; application validation must require those module IDs to
match. The record contract version is always present as a supported string or
deliberate `null`.

This schema is a Portia-owned structural composition, not a Core v0.5 adapter
and not a competing identity authority. It does not pin a Core package
version, register a module, resolve a work or record, or establish lifecycle,
authorization, or consumer eligibility. Core runtime validation remains
authoritative.

Use `local_record_ref` when the consuming schema already supplies one
unambiguous Portia work scope. Use `portia_work_record_ref` when the target
Portia work must be stated explicitly.

Use `module_work_record_ref` for a record owned by a sibling module when both
the module work and module record identities must be explicit. A consuming
schema may impose a narrower module, record-kind, contract-version, or
cardinality policy.

These schemas validate local structure only. Target existence, authoritative
resolution, lifecycle eligibility, contract support, authorization, and
consumer-specific use remain application-validation responsibilities.

Issue #13 adds these operational reference contracts:

- `operation-ref.schema.json` identifies one stable operation series;
- `operation-journal-ref.schema.json` selects one exact immutable journal revision;
- `quarantine-ref.schema.json` selects one exact immutable Quarantine revision;
- `derived-generation-ref.schema.json` selects one immutable derived generation.

Stable references do not imply existence or currentness. Exact revision references
must resolve the named revision and contract; consumers must not substitute the
greatest revision, newest timestamp, filename order, or current pointer.

Issue #14 adds exact Actor Directory representation references:

- `exact-actor-ref.schema.json`;
- `exact-actor-contact-point-ref.schema.json`;
- `exact-actor-student-relationship-ref.schema.json`;
- `exact-actor-roster-student-collision-ref.schema.json`;
- and the closed `exact-actor-directory-record-ref.schema.json` union.

Every exact reference carries the expected public contract version. Exact
references remain bound to the named historical representation and never
silently follow correction, consolidation, splitting, supersession, or
migration.

`actor-target.schema.json` wraps the exact Actor Directory record union for
operational and diagnostic target composition. The immutable Collision record
is included in exact operational targeting but is excluded from lifecycle and
amendment target subsets.

Issue #15 does not add redundant Account- or Observation-specific exact-reference
families. Event-local relations may constrain `exact_local_record_ref`, while
cross-work operational, dependency, migration, removal, and diagnostic surfaces
reuse `exact_portia_work_record_ref`. Exact Account and Observation references
therefore preserve the containing work, record family, opaque record ID, and
required contract version without creating a second reference vocabulary.

Issue #16 likewise does not add dedicated exact Review-, Classification-,
Hypothesis-, or Determination-reference families. Exact generic local/work-record
references already preserve the required record kind, opaque ID, work scope, and
contract version. `judgment_evidence_ref@1` is a narrow evidence-role locator
union for Review/Hypothesis/Determination use; it does not change generic exact
identity semantics or make a referenced record true, current, or authoritative.

Issue #17 likewise does not add dedicated Response- or Communication-specific
exact-reference families. `exact_portia_work_record_ref@1` already preserves
exact work scope, record kind, opaque ID, and contract version for both families.
Exact Response and Communication references therefore never silently follow
successor correction, consolidation, migration, or ownership correction.

## Shared snapshots and target contracts

The initial reusable historical snapshot is:

    schemas/v1/snapshots/person-display-snapshot.schema.json

`person_display_snapshot` contains only a required non-whitespace
`display_name`. It is nonauthoritative historical presentation data and does
not participate in identity, equality, resolution, duplicate detection,
authorization, or lifecycle. Consuming schemas place it as a sibling of an
eligible person reference; it is never nested inside `roster_student_ref` or
`actor_ref`.

Event-local and Support Process-local target families are stored beneath:

    schemas/v1/targets/

`portia_target_ref` supports exactly the containing Event, one Event
Participant, or a selected set of at least two Event Participants.

Account v1, Observation v1, Review v1, Classification v1, Hypothesis v1, and Determination v1 reuse this target contract unchanged. Their
represented source or observer is modeled separately from the Event-local target;
a source or observer does not become an Event Participant merely by supplying or
observing information.

`support_process_target_ref` supports exactly the containing Support Process,
one Support Process Participant, or a selected set of at least two Support
Process Participants.

A singular participant target contains a constrained `local_record_ref`.
Plural branches contain only singular participant targets. Exact duplicate
array items are rejected structurally.

Canonical duplicate identity is stricter than JSON object equality. A plural
target containing the same participant `record_kind + record_id` more than
once is application-invalid even when the references carry different
`contract_version` values. Participant-set order has no domain meaning, and
deterministic canonical serialization remains an application responsibility.

These target contracts establish application scope only. They do not establish
participant roles, source, basis, evidence, attribution, provenance,
relationship direction, target existence, lifecycle eligibility, or
authorization.

## Shared envelope primitives

Reusable envelope-oriented contracts are independently addressable beneath:

    schemas/v1/common/
    schemas/v1/provenance/
    schemas/v1/attribution/

`non_empty_text` requires a string containing at least one non-whitespace
character. It does not silently trim, normalize, or impose an unrelated
maximum length.

`explicit_offset_timestamp` requires an RFC 3339 date-time carrying either an
explicit numeric UTC offset or uppercase `Z`. Timestamp ordering, creation-time
equality, and monotonic updates remain application-validation concerns.

`creation_source` preserves structured creation provenance through exactly
three initial branches: `digital_entry`, `paper_capture`, and `import`.
Paper-capture route and page-record identifiers use a nonauthoritative
structural fallback until the originating PDS2 contract is independently
addressable. A consuming record may impose stricter workflow eligibility; for
example, a Work Relationship created from paper must use an ingested page.

`attribution_agent` distinguishes a `local_operator` display label from a
`system_process` identifier. It records local persistence-operation
attribution and is not interchangeable with `actor_ref` or institutional
identity and authorization.

Issue #15 adds three reusable evidence primitives:

```text
schemas/v1/attribution/represented-human-attribution.schema.json
schemas/v1/common/evidence-time.schema.json
schemas/v1/provenance/source-artifact-ref.schema.json
```

`represented_human_attribution` identifies the human whose statement or direct
observation is represented. Its closed branches are `roster_student`, `actor`,
`local_operator`, `descriptive_person`, and `unidentified_person`. It remains
distinct from `attribution_agent`: the represented source/observer and the local
operator or system process that persisted a record are separate facts.

Issue #16 reuses `represented_human_attribution@1` where the same
represented-human semantics apply to reviewer, Classification selector,
Hypothesis author, and Determination decision-maker identity. That reuse does
not broaden the attribution contract into an authorization contract:
represented human identity remains separate from institutional authority,
process/policy basis, and persistence-operation `created_by` / `updated_by`.

Issue #17 reuses `represented_human_attribution@1` for Response provider and
Communication sender/recipient identity. That reuse remains structural: represented
human identity does not establish provider eligibility, institutional authority,
guardianship, consent, disclosure authorization, participation, or delivery.
Communication may additionally retain `exact_actor_contact_point_ref@1` for an
Actor recipient; the exact Contact Point remains historical endpoint identity, not
proof of consent or successful delivery.

`evidence_time` preserves honest source-evidence timing through `exact`,
`approximate`, `date_only`, `range`, and `unknown` variants. Application
validation establishes range chronology and record-specific timing consistency;
record creation time is never substituted for unknown evidence time.

`source_artifact_ref` provides closed typed references to `paper_capture`,
`workspace_file`, `portia_work_record`, `module_work_record`, and
`external_record` sources. It does not embed binary content, make external
locators authoritative, or prove authenticity, accuracy, authorization, or
consumer eligibility. Core remains authoritative for PDS2 routing and retained
paper-source provenance.

The retained Event-family version-1 schemas keep their private historical
`$defs` unchanged. New record contracts compose these public shared schemas so
that provenance, attribution, text, and timestamp behavior do not drift across
record families.

Issue #13 adds three reusable persistence primitives:

    schemas/v1/common/workspace-relative-path.schema.json
    schemas/v1/common/sha256-digest.schema.json
    schemas/v1/common/content-fingerprint.schema.json

A workspace-relative path is lexical diagnostic location evidence, not identity.
Passing the schema does not prove actual containment, symlink safety, existence,
file kind, or identity/path agreement. A content fingerprint binds exact SHA-256
bytes and byte length; it does not prove semantic meaning, acceptance, or
authorization.


## Support Process, Support, Intervention, Implementation, and Fidelity contracts

ADR 0014 adds the canonical Support Process planning, implementation, and
implementation-quality family:

```text
schemas/v1/support-processes/support-process.schema.json
schemas/v1/support-processes/support-process-participant.schema.json
schemas/v1/support-processes/support-need.schema.json
schemas/v1/support-processes/support-goal.schema.json
schemas/v1/support-processes/planned-schedule.schema.json
schemas/v1/support-processes/support.schema.json
schemas/v1/support-processes/intervention.schema.json
schemas/v1/support-processes/implementation.schema.json
schemas/v1/support-processes/fidelity.schema.json
```

The central boundary is:

```text
planned Support / Intervention
≠ actual Implementation
≠ Fidelity
≠ Outcome
```

`planned_schedule@1` is planning only. A scheduled occurrence never creates an
Implementation, and Implementation history never creates or implies Fidelity.

Issue #18 adds no dedicated exact-reference family because
`exact_local_record_ref@1` and `exact_portia_work_record_ref@1` already preserve
record kind, opaque ID, work scope, and contract version. Exact references do
not silently follow plan adaptation, correction, consolidation, migration,
ownership correction, or cross-year succession.

The Issue #18 v1 families expose no Amendment paths. Material correction and
prospective plan adaptation use preserved successor/history semantics.
Statement of Disagreement remains additive.

Support Process-owned Communication is now resolvable against the canonical
owner, but Communication remains a contact act/attempt rather than consent,
service delivery, Implementation, Fidelity, or Outcome.

Shared operation, lock, Quarantine, Integrity Finding, source-snapshot, and
derived-state contracts are reused. Derived state remains rebuildable and
nonauthoritative.

Core v0.6 `intervention_record_set` is not canonical Portia storage and is not
published by Issue #18. Future publication remains a separate privacy-minimized
projection.

## Actor Directory contracts

The canonical teacher-local Actor Directory record family is stored beneath:

```text
portia/actors/<actor_id>/
  actor.json
  records/
```

The public version-1 contracts are:

```text
schemas/v1/actors/actor.schema.json
schemas/v1/actors/actor-contact-point.schema.json
schemas/v1/actors/actor-student-relationship.schema.json
schemas/v1/actors/actor-roster-student-collision.schema.json
schemas/v1/actors/actor-directory-lifecycle-transition.schema.json
schemas/v1/actors/actor-directory-lifecycle-history-correction.schema.json
schemas/v1/actors/actor-directory-amendment.schema.json
schemas/v1/migrations/actor-directory-record-migration.schema.json
schemas/v1/removals/actor-directory-exceptional-removal.schema.json
```

One Actor represents one recurring non-roster human person in one selected
teacher-local workspace. Actor identity is the opaque `actr_` identifier.
Display name, category, organization, title, contact information, relationship
assertions, and workflow roles do not participate in identity.

The Actor root stores only current profile, category, lifecycle status,
creation provenance, attribution, and reviewed predecessor lineage. Email and
phone values are separate privacy-sensitive Contact Point children.
Actor-to-Student Relationships are separate children using exact Core
`class_id + student_id` identity, explicit basis, local review, and no implied
legal, institutional, disclosure, consent, custody, employment, or
decision-making authority.

An Actor–Roster Student Collision is immutable reviewed correction evidence. It
links one exact Actor, one exact class-qualified roster student, the coordinated
operation, and the Actor invalidation transition. It creates no Actor successor,
does not convert Contact Points into roster data, and establishes no
workspace-wide student identity.

Actor Directory lifecycle and amendment records are Actor-root-local and
append-only. Immutable Collision records are structurally excluded from those
mutable target families. Material identity, contact-value, relationship-target,
or relationship-type correction creates successors rather than rewriting
history.

Representation migration preserves logical identity and meaning across explicit
contract versions. Exceptional-removal certificates are stored outside Actor
roots at:

```text
portia/actor-directory-removals/<removal_id>.json
```

Ordinary inactivity, historical status, duplication, or lack of current
references does not justify removal.

JSON Schema establishes closed local wire shapes. Application validation remains
responsible for canonical path and owner agreement, Core roster resolution,
lifecycle history, local review, duplicate and split topology, incoming
reference completeness, operation ordering, authorization, fingerprint truth,
privacy, recovery, and current-use eligibility.

## Account and Observation contracts

ADR 0011 defines two Event-local canonical evidence families:

```text
schemas/v1/accounts/account.schema.json
schemas/v1/observations/observation.schema.json
```

Account identity uses `acct_<opaque-id>` and Observation identity uses
`obs_<opaque-id>`. Canonical paths are:

```text
classes/<class_id>/modules/portia/work/<event_id>/records/account/<account_id>.json
classes/<class_id>/modules/portia/work/<event_id>/records/observation/<observation_id>.json
```

One Account preserves one coherent attributed source contribution. The record
keeps represented source separate from persistence attribution, distinguishes
`verbatim_quote` from `recorded_summary`, records information origin as
`firsthand`, `secondhand`, `mixed`, or `unknown`, and preserves source-expressed
certainty without treating it as credibility. Optional exact same-Event Account
relations support `reports_from`, `clarifies`, and source-evidenced `retracts`.
Conflicting Accounts may coexist without automatic adjudication.

Account lifecycle is:

```text
proposed
active
retracted
invalidated
superseded
```

Retraction requires source evidence: a later qualifying same-source Account
references the exact predecessor with `retracts`, coordinated with the
predecessor's transition to `retracted`. Retraction does not assert that the
prior Account was false.

One Observation preserves one coherent human or instrumented direct observation
context. Its method vocabulary is `live_direct`, `artifact_review`,
`manual_count`, `manual_timing`, `instrumented`, or `other`. Content may contain
observable narrative, structured measurements, or both. Structured measurement
supports count, duration, latency, percentage, and bounded other numeric values.
The contract contains no positive/neutral/concerning valence, severity, policy,
intent, diagnosis, risk, or finding field.

Observation lifecycle is:

```text
proposed
active
invalidated
superseded
```

Both records reuse `portia_target_ref`. Application validation resolves all
Participant targets within the containing Event and preserves exact historical
targets. Active `reported_involved` Role v3 use requires a qualifying active
same-Event Account targeted to that Participant or a set containing that
Participant. Observation alone cannot satisfy the Account requirement.

Paper and import provenance reuse `creation_source`. Paper preallocation does
not create canonical evidence; paper- and import-derived Account/Observation
records begin proposed and require accepted review before activation. OCR,
handwriting recognition, imported prose, names, or external-system provenance do
not silently establish source identity, firsthand status, target, or a finding.

Account and Observation v1 intentionally expose no in-place Amendment paths.
Material correction creates a successor and preserves exact predecessor history.
The generic lifecycle, history-correction, Statement of Disagreement, Dependency,
Record Migration, Exceptional Removal, Operation Journal, Operation Lock,
Quarantine, Integrity Finding, source-snapshot, derived-generation metadata, and
current-pointer contracts already accept exact generic work-record references and
are reused without Account/Observation-specific versions.

Operational and derived records are privacy-minimized. They may retain opaque
IDs, exact references, paths, contract versions, fingerprints, byte lengths,
status tokens, counts, and machine-readable diagnostic facts, but they must not
copy Account quotations/summaries or Observation narrative merely for
coordination or diagnostics.

JSON Schema establishes local record shape, closed vocabularies, identifier and
reference shape, measurement branches, provenance shape, and structural
conditionals. Application validation remains responsible for canonical path and
Event agreement, represented-source/observer resolution, target resolution,
chronology, review gates, method/measurement compatibility, source-evidenced
retraction, Role eligibility and target alignment, correction topology, exact
reference behavior, authorization, privacy, operational recovery, and derived
freshness.

## Work Relationship contract

The initial canonical Work Relationship schema is:

    schemas/v1/work-relationship.schema.json

A Work Relationship is stored beneath its semantic source Portia work. The
containing work identity and the required direct `source` endpoint must agree.
The target does not store a canonical reverse copy; reverse navigation and
target-side wording are derived from the source-owned record.

The initial controlled vocabulary contains exactly:

    draws_context_from

Its source may be an Event or Support Process. Its target is always an Event.
The relationship is contextual and does not assert causation, proof, blame,
responsibility, credibility, diagnosis, service authorization, or
institutional approval.

The record composes the public Portia work-reference, relationship-identifier,
creation-source, attribution-agent, explicit-offset timestamp, and nonempty
text contracts. Paper-derived relationships require
`creation_source.stage = "ingested"` even though the broader shared provenance
contract also supports preallocation for other record families.

Optional `supersedes` entries use complete `portia_work_record_ref` values
constrained to `record_kind = "work_relationship"` and
`contract_version = "1"`.

JSON Schema establishes the closed envelope, endpoint shape, controlled
vocabularies, identifier syntax, timestamp syntax, paper-ingestion gate, and
predecessor-reference shape. Application validation remains responsible for
storage/source agreement, self-reference, exact resolution, endpoint
eligibility, active edge uniqueness, inverse duplicates, timestamp chronology,
lifecycle transitions, self-supersession, predecessor identity uniqueness,
supersession cycles, and coordinated successor activation.

## Event version 2

The current implementation-target Event root schema is:

    schemas/v2/event.schema.json

The retained unversioned-path Event schema remains the historical version-1
contract. Version 2 does not rewrite, alias, or silently migrate that schema.

Version 2 preserves the Event status, occurrence, location, instructional
context, school-year, summary, provenance, attribution, and activation
semantics established by version 1. It reconciles two provisional reference
shapes:

- `instructional_context.external_refs` now contains complete
  `module_work_record_ref` values;
- `supersedes` now contains direct `portia_work_ref` values constrained to
  Event works and explicit Event contract version `"1"` or `"2"`.

A module work-record reference repeats `module_id` inside its `work_ref` and
`record_ref` because both Core wire values are independently self-describing.
Application validation must require those module IDs to match. Structural
validity alone does not establish target existence, contract support, lifecycle
eligibility, authorization, or consumer-specific use.

Event supersession remains a specialized successor-owned correction
relationship. Predecessor identity is the target Event's
`module_id + class_id + work_id`; `work_kind` and `contract_version` express the
expected Portia contract but do not create a second Event identity. Application
validation prevents self-supersession, duplicate canonical predecessor identity
across versions, cycles, silent retargeting, and uncoordinated lifecycle changes.

JSON Schema establishes the closed Event envelope, public shared-contract
composition, identifier and timestamp syntax, occurrence and vocabulary
branches, activation-time required fields, instructional-reference structure,
and Event-only predecessor-reference shape. Application validation remains
responsible for storage agreement, Core resolution, chronology, lifecycle,
review gates, participant-state requirements, nested module equality,
supersession graph invariants, and authorization.

Migration fixtures beneath
`tests/schema_validation/fixtures/migrations/event_v1_to_v2/` document explicit
version-1 to version-2 transformations. Historical version-1 Event files remain
readable and unchanged.

## Event Participant version 2

The current implementation-target Event Participant schema is:

    schemas/v2/event-participant.schema.json

The retained unversioned-path Event Participant schema remains the historical
version-1 contract. Version 2 does not rewrite or alias that schema.

Version 2 preserves the four subject variants while replacing embedded or flat
identity fields with the public shared contracts:

- roster subjects use `roster_student_ref`;
- Actor subjects use `actor_ref`;
- durable roster and Actor subjects retain a sibling
  `person_display_snapshot`;
- descriptive and unknown subjects retain their version-1 vocabularies;
- supersession links use a constrained `local_record_ref` rather than a flat
  `participant_id`.

A version-2 supersession reference must identify `record_kind =
"event_participant"`, use an `ep_` record identifier, and state contract
version `"1"` or `"2"`. Contract version is never omitted or treated as a
wildcard.

The record composes public Portia identifier, reference, snapshot, provenance,
attribution, timestamp, and text contracts. Version-1 property names such as
`student_ref` and a bare `actor_id` are rejected by the closed version-2
subject branches.

JSON Schema establishes the closed envelope, subject branch, shared-contract
composition, identifier syntax, lifecycle vocabulary, provenance and
attribution shapes, timestamp syntax, and predecessor-reference structure.
Application validation remains responsible for parent Event resolution,
storage-path agreement, durable-subject uniqueness, chronology, lifecycle and
creation-workflow rules, self-supersession, predecessor identity uniqueness,
supersession cycles, and coordinated state changes.

Migration fixtures beneath
`tests/schema_validation/fixtures/migrations/event_participant_v1_to_v2/`
document explicit version-1 to version-2 transformations. Reading a historical
version-1 record does not silently mutate it or change its canonical identity.

## Event Participant Role version 2

The current implementation-target Event Participant Role schema is:

    schemas/v2/event-participant-role.schema.json

The retained unversioned-path Role schema remains the historical version-1
contract. Version 2 preserves the accepted Role types, lifecycle vocabulary,
reported-involvement basis rules, contextual-detail rules, paper-ingestion
boundary, and correction semantics while reconciling its reference shapes.

Version 2 replaces the direct `participant_id` property with a required
singular `target` using the Event Participant branch of `portia_target_ref`.
The target must identify `record_kind = "event_participant"`, an `epr_` record
identifier, and contract version `"1"` or `"2"`. Event-level and
multi-participant Role targets are structurally rejected.

Account and Observation basis entries retain their specialized outer kinds but
now contain a nested `record_ref`. Because their public contracts are deferred,
current fixtures use explicit `contract_version: null`; omission is invalid and
`null` is not a wildcard. Exact target existence, supported versions, and
same-Event eligibility remain application-validation responsibilities.

Role supersession entries likewise use a nested `record_ref` constrained to
`record_kind = "event_participant_role"`, an `epr_` record identifier, and
contract version `"1"` or `"2"`.

The record composes public Portia target, local-record reference, identifier,
provenance, attribution, timestamp, and text contracts. Paper-derived Roles
must use ingested creation provenance and must include a paper basis. Exact
route and page equality between provenance and basis remains an application
invariant.

JSON Schema establishes the closed envelope, singular target shape, Role and
status vocabularies, basis variants, contextual-detail rules,
reported-involvement Account requirements, paper-ingestion gate, shared
contract composition, and predecessor-reference structure. Application
validation remains responsible for parent and target resolution, same-Event
scope, lifecycle eligibility, chronology, paper identity equality, duplicate
active Role compatibility, self-supersession, predecessor identity uniqueness,
supersession cycles, and coordinated state changes.

Migration fixtures beneath
`tests/schema_validation/fixtures/migrations/event_participant_role_v1_to_v2/`
document explicit version-1 to version-2 transformations. Reading a historical
version-1 Role does not silently mutate it or change its canonical identity.

## Review, Classification, Hypothesis, and Determination contracts

ADR 0012 defines four Event-local canonical human review/judgment families:

```text
schemas/v1/reviews/review.schema.json
schemas/v1/classifications/classification.schema.json
schemas/v1/hypotheses/hypothesis.schema.json
schemas/v1/determinations/determination.schema.json
```

Their identifiers are opaque `rvw_`, `cls_`, `hyp_`, and `det_` values. Canonical
records remain separately addressable children of the containing Event rather
than being nested inside one Review directory.

`review@1` preserves one bounded human review process. It separates canonical
record lifecycle from Review workflow state and explicitly records the
considered-evidence set, including the valid empty set.

`classification@1` preserves one attributed category assertion under one
versioned definition snapshot. Reporter-selected, reviewer-selected,
reviewer-confirmed, and unknown historical stage remain distinguishable.
`unable_to_determine` is a first-class result branch.

`hypothesis@1` preserves one explicitly tentative proposition and
`under_consideration` / `set_aside` consideration state. Supporting, contrary,
and contextual evidence roles are explicit. The contract has no predictive
probability, numeric confidence, credibility, risk, diagnosis, or FBA/function
determination field.

`determination@1` preserves one bounded decision question, represented
decision-maker, authority context, process/policy basis, outcome, and exact
decision basis. Teacher-local and recorded-institutional scope remain distinct.
Authority evidence may be preserved, but the teacher-local deployment does not
authenticate institutional authority.

All four families reuse the existing shared lifecycle/history, disagreement,
Dependency, migration/removal, operation/lock, Quarantine/Integrity Finding,
source-snapshot, derived-generation, and current-pointer contracts. Material
judgment changes have no v1 in-place Amendment surface; successor records and
exact predecessor relationships preserve history. Reconsideration/reversal of a
Determination creates a new record rather than editing the earlier decision.

JSON Schema validates local wire shape. Application validation remains
responsible for canonical path/Event resolution, represented-human resolution,
Review linkage and chronology, definition support, evidence resolution and
lineage, authority/process sufficiency, paper/import review gates, replacement
topology, reconsideration/reversal semantics, authorization, privacy,
operational recovery, and derived freshness.

## Response and Communication contracts

ADR 0013 adds four public version-1 contracts:

```text
schemas/v1/identifiers/portia-response-id.schema.json
schemas/v1/identifiers/portia-communication-id.schema.json
schemas/v1/responses/response.schema.json
schemas/v1/communications/communication.schema.json
```

Response identity uses `rsp_<opaque-id>` and Communication identity uses
`comm_<opaque-id>`. Neither identifier encodes student, provider/sender,
recipient, action/method, consequence, date, privacy, or lifecycle meaning.

`response@1` is Event-local and reuses `portia_target_ref@1`. The provider is a
represented human distinct from persistence attribution. Stable action families
describe what action occurred; execution state remains separate from lifecycle
and effectiveness. A recorded institutional consequence requires exact
same-Event Determination context without duplicating authority or policy meaning.

`communication@1` is Portia-work-local with `event` and `support_process`
structural ownership. Event ownership is current-use eligible under Issue #17;
Support Process current use waits for Issue #18's published owner contract.
Sender and recipients are represented humans. Recipient participation is explicit
and descriptive; listing a recipient is not participation.

Communication attachments are schema-local rather than a broadening of
`source_artifact_ref@1`. The closed v1 attachment branches are
`workspace_file`, `portia_record`, `module_record`, and `external_record`.
No binary payload is embedded, external locators remain inert, and attachment
presence proves neither delivery nor evidentiary weight.

Communication uses typed exact record relations including `responds_to`,
`conveys_determination`, `relates_to_response`, and
`account_from_communication`. Communication records the contact act; Account
remains the source-evidence record for a substantive represented-source
assertion.

Both families use `proposed`, `active`, `invalidated`, and `superseded`
canonical lifecycle states and expose no v1 Amendment paths. Material correction
uses successor/history semantics. Generic lifecycle, disagreement, dependency,
migration/removal, operation, diagnostic, snapshot, and derived-state contracts
remain authoritative.

## Lifecycle and lifecycle-history contracts

The shared append-only history contracts are:

    schemas/v1/lifecycle/lifecycle-transition.schema.json
    schemas/v1/lifecycle/lifecycle-history-correction.schema.json

A Lifecycle Transition identifies one exact work or same-work record target, the prior and resulting status tokens, reason, effective time, creation provenance, and attribution. Status vocabularies and permitted edges remain record-family responsibilities.

The canonical target may persist current status for direct loading. Application validation must reconcile that value with the selected transition history. A mismatch is not silently repaired.

A Lifecycle-History Correction selects a replacement transition-history head while preserving the replaced branch. It is append-only correction evidence and is not itself a status transition.

## Amendment and disagreement contracts

The correction contracts are:

    schemas/v1/corrections/amendment.schema.json
    schemas/v1/corrections/statement-of-disagreement.schema.json

An Amendment records a bounded nonmaterial change with explicit before-and-after presence and value, JSON Pointer path, target-revision precondition, reason, chronology, and attribution. Application validation determines materiality and protects identity, ownership, subject, target, source, basis, status, and substantive meaning.

Account v1 and Observation v1 define no permitted Amendment paths. Their
substantive evidence remains immutable in place; corrections create explicit
successor records and preserve exact historical representations.

A Statement of Disagreement preserves an attributable dispute, qualification, objection, or withdrawal position. It does not mutate, invalidate, supersede, or adjudicate its target.

## Dependency contract

The shared dependency record is:

    schemas/v1/dependencies/dependency.schema.json

A Dependency identifies one same-work dependent and one exact Portia work, Portia record, or sibling-module record dependency. It records required or advisory strength, activation/current-use/completion scope, and purpose.

Dependency effects are derived through application evaluation. Portia does not store one universal dependency-health value, silently follow a successor, duplicate an intrinsic domain dependency, or apply an automatic lifecycle cascade.

## Migration, ownership correction, and exceptional removal

The operation-evidence contracts are:

    schemas/v1/migrations/record-migration.schema.json
    schemas/v1/corrections/ownership-correction.schema.json
    schemas/v1/removals/exceptional-removal.schema.json

Record Migration changes representation while preserving logical identity, record family, work root, lifecycle meaning, and substantive semantics. Source and destination are exact representations and the transformer identity and version are explicit.

Ownership Correction records a wrong Event class or child work root. It identifies exact source and destination representations and supports parent-child mapping without treating filesystem movement as canonical authority. References do not silently retarget.

Exceptional Removal is the narrow administrative boundary for legal, privacy, security, accepted-test-data, and unrecoverable-corruption cases. The certificate preserves exact target identity, authorization, minimal content evidence, available lifecycle evidence, and effective time without retaining prohibited payload. Removal is not a `deleted` lifecycle state.

## Upgraded Event-family and relationship contracts

Issue #12 introduces these current implementation targets:

    schemas/v3/event-participant.schema.json
    schemas/v3/event-participant-role.schema.json
    schemas/v2/work-relationship.schema.json

Participant and Role version 3 preserve version-2 domain semantics while replacing same-work predecessor references with complete exact Portia work-record references. Work Relationship version 2 accepts predecessor versions 1 and 2.

All three support `work_root_corrected` and `contract_migrated`. Application validation requires ownership correction to use a changed work scope and fresh destination identity where required, while migration preserves logical identity in the same work across different contract versions.

Event remains at version 2 because its existing exact predecessor work references already support migration, correction, duplicate consolidation, and Event ownership replacement.

## Integrity-finding projection

The noncanonical diagnostic projection is:

    schemas/v1/projections/integrity-finding.schema.json

An Integrity Finding contains deterministic finding and evaluation keys, stable rule identity and version, category and code, severity, confirmed or indeterminate assessment, explicit effects, scope, exact targets, bounded evidence, and observation time.

The projection deliberately excludes `schema_version`, `record_type`, lifecycle status, attribution, supersession, amendment, migration, and canonical storage identity. It may be deleted and rebuilt without altering domain history.

Issue #13 implements acknowledgement, suppression, Quarantine, operation
state, recovery evidence, and rebuildable operational projections without
changing Integrity Finding v1.

## Coordinated operation journals and pointers

The central durable operational contracts are:

    schemas/v1/operations/operation-journal.schema.json
    schemas/v1/operations/operation-current-pointer.schema.json

An Operation Journal is one immutable complete revision of a bounded operation
series. It records stable intent, scope, exact targets, preflight observations,
locks, an ordered write set, staged artifacts, per-step dispositions, the
canonical commit point, compensation and recovery plans, and structured partial
state.

The pointer contains only `operation_id + journal_revision` with its fixed
envelope. Current state is never inferred from the greatest revision, newest
file, timestamp, or directory order.

JSON Schema closes the journal envelope and vocabularies and enforces selected
state-dependent constraints. Application validation establishes intent and
preflight digest truth, journal linearity and monotonicity, contiguous unique
step ordering, exact replay, expected prior state, lock ownership, canonical
acceptance, operation-specific ordering, authorization, compensation safety, and
recovery disposition.

## Locks and Quarantine

The protective operational contracts are:

    schemas/v1/operations/operation-lock.schema.json
    schemas/v1/operations/quarantine-record.schema.json
    schemas/v1/operations/quarantine-current-pointer.schema.json

A lock has deterministic scope and target, stable operation-series ownership,
and privacy-minimized acquisition metadata. It has no expiry, heartbeat, mutable
state, or age-based stale claim. Clearing requires exact fingerprint protection
and external evidence that no active writer remains.

Quarantine is an immutable revision series with `active`, `released`, and
`superseded` states. It blocks explicit ordinary effects while preserving
canonical identity and lifecycle. Age, acknowledgement, operation completion,
or lock absence does not release Quarantine. The current pointer explicitly
selects one revision.

## Finding acknowledgement and suppression

Finding administration uses:

    schemas/v1/operations/finding-acknowledgement.schema.json
    schemas/v1/operations/finding-suppression.schema.json
    schemas/v1/operations/finding-suppression-current-pointer.schema.json

Acknowledgement is append-only review workflow over one exact
`finding_key + evaluation_key`. It does not resolve, suppress, waive, downgrade,
or make the finding nonblocking.

Suppression is a bounded immutable revision series. It structurally permits only
`advisory` or `warning` findings whose effects are `attention` and/or
`review_required`, binds the exact evaluation, rule, severity, and effects, names
presentation surfaces and audiences, records policy and authorization evidence,
and requires at least one explicit expiry condition. It never hides a finding
from validation, recovery, audit, or authorized maintenance.

## Actor-aware operational version 2

Issue #14 adds new version-2 contracts without modifying the published
version-1 operational schemas:

```text
schemas/v2/projections/integrity-finding.schema.json
schemas/v2/operations/operation-journal.schema.json
schemas/v2/operations/operation-lock.schema.json
schemas/v2/operations/quarantine-record.schema.json
```

The additive target vocabulary supports:

```text
actor_directory_record
actor_set
actor_directory_collection
```

Actor sets are bounded, deterministically sorted, and unique by logical
`actor_id`. They contain no names, contact values, relationship narratives, or
student display data.

Operation Journals retain immutable revisions, explicit current-pointer
selection, preflight, deterministic lock ordering, exact write sets, commit
points, structured partial state, and recovery semantics. Actor operations use
workspace scope. Operation facts retain only privacy-minimized IDs, paths,
contract versions, fingerprints, byte lengths, statuses, counts, and step
results.

Operation Locks add Actor Directory collection and exact Actor Directory record
scopes. Multi-Actor operations acquire individual record locks in deterministic
order; there is no Actor-set lock target. Lock identity remains SHA-256-derived,
and no expiry or heartbeat implies safe takeover.

Quarantine adds Actor record, set, and collection targets plus
`block_actor_directory_writes`. Quarantine remains operational protection, not
Actor lifecycle, and release does not reactivate an Actor.

Integrity Finding v2 adds Actor-specific diagnostics for path/identity
mismatch, replacement defects, duplicate candidates, roster collisions,
ownership defects, preference conflicts, authority overclaim, incomplete
incoming-reference discovery, and privacy leaks. Duplicate candidates remain
human-review findings and cannot confirm identity or automatically merge
records.

Issue #15 reuses these version-2 operational target shapes unchanged for
Account and Observation because their generic exact Portia work-record branches
already accept `record_kind = "account"` and `record_kind = "observation"`.
No Role v4, Operation Journal v3, Operation Lock v3, Quarantine v3, or Integrity
Finding v3 is introduced. Application validation keeps Account/Observation prose
out of privacy-minimized operational facts and reason detail.

## Deterministic source snapshots and derived generations

The shared derived-generation contracts are:

    schemas/v1/projections/source-snapshot.schema.json
    schemas/v1/projections/derived-index-metadata.schema.json
    schemas/v1/projections/derived-current-pointer.schema.json

A Source Snapshot is a deterministic bounded inventory of exact source paths,
byte lengths, SHA-256 digests, roles, contracts, scope, and authorization
coverage. Observation time is recorded but is not a digest input.

Account v1 and Observation v1 participate as ordinary `canonical_domain` source
contracts. The snapshot records their paths, byte lengths, digests, roles, and
contract identities; it does not copy their substantive source-evidence text.

Derived Index Metadata describes one immutable `complete` generation. It binds
projection kind and scope, contract version, builder identity, authorization
coverage, the complete source snapshot, output artifact fingerprint, passed
validation summary, generating Operation Journal revision, and generation time.

A Derived Current Pointer selects one generation explicitly for one projection
kind and scope. It contains no freshness, authorization, builder, or source-digest
claim. Consumers must load and verify the selected generation and compare its
snapshot with current canonical sources. A missing or stale projection is not an
empty graph, and reads do not silently rebuild it.

## Offline resolution

Schema tests build a local `referencing.Registry` from checked-in schema
resources. An unresolved `$ref`, duplicate canonical `$id`, or disagreement
between a catalog entry and its source schema is a test failure.

## Validation boundary

JSON Schema establishes local structure, closed envelopes, required fields,
controlled vocabularies, identifier and timestamp syntax, exact reference
shape, and structural conditionals.

Application validation remains responsible for authoritative resolution,
storage and envelope agreement, lifecycle legality, history reconciliation,
materiality, authorization, chronology across records, duplicate identity,
successor and dependency graphs, migration semantic preservation, ownership
and child reconciliation, removal execution, deterministic finding generation,
workspace containment, exact byte and digest truth, replay, journal linearity,
lock conflicts and conservative clearing, expected prior state, operation
ordering, compensation and recovery safety, suppression eligibility, source
snapshot truth, generation completeness, freshness, authorization compatibility,
and verified atomic installation of complete derived replacements. For Account
and Observation this also includes represented-source/observer resolution,
Event-local target resolution, paper/import review gates, information-origin
consistency, source-evidenced retraction, observation method/measurement
compatibility, `reported_involved` Account target alignment, no silent successor
following, and privacy minimization of operational and derived evidence.

Issue #13 defines those public operational and derived contracts but does not
implement production filesystem writers, orchestration, recovery execution,
Quarantine enforcement, projection builders, or teacher-facing maintenance.

## Running the schema tests

From the repository root, run:

    python -m unittest discover -s tests/schema_validation -p "test_*.py"
