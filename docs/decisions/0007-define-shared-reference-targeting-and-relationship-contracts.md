# ADR 0007: Define Shared Reference, Targeting, and Relationship Contracts

* **Status:** Accepted
* **Date:** 2026-08-02
* **Decision owners:** Portia maintainers
* **Related issue:** [#11 — Define shared reference, targeting, and relationship contracts](https://github.com/Paper-Data-Suite/pds-portia/issues/11)
* **Related design:** [`docs/design/portia-reference-targeting-and-relationship-contracts.md`](../design/portia-reference-targeting-and-relationship-contracts.md)
* **Related examples:** [`docs/examples/portia-reference-targeting-and-relationship-examples.md`](../examples/portia-reference-targeting-and-relationship-examples.md)
* **Related schema catalog:** [`schemas/schema-catalog.json`](../../schemas/schema-catalog.json)
* **Related schema guide:** [`schemas/README.md`](../../schemas/README.md)
* **Related decisions:**
  * [`0001-establish-portia-record-distinctions.md`](0001-establish-portia-record-distinctions.md)
  * [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)
  * [`0003-adopt-teacher-local-initial-deployment.md`](0003-adopt-teacher-local-initial-deployment.md)
  * [`0004-define-portia-identity-ownership-and-storage.md`](0004-define-portia-identity-ownership-and-storage.md)
  * [`0005-define-event-and-participant-domain-model.md`](0005-define-event-and-participant-domain-model.md)
  * [`0006-define-event-participant-role-domain-model.md`](0006-define-event-participant-role-domain-model.md)

## Context

Portia records already require several materially different kinds of reference:

* Core roster-qualified student identity;
* workspace-local Portia Actor identity;
* same-work child-record identity;
* complete Portia work identity;
* complete cross-work Portia record identity;
* complete sibling-module work-and-record identity;
* Event-local and Support Process-local application targets;
* specialized basis and supersession references;
* and independently managed durable work relationships.

These uses do not share one authority or one scope. A roster student is resolved through Core roster identity. An Actor is resolved through Portia's teacher-workspace Actor Directory. A compact child reference inherits exactly one work scope from its containing record. A cross-work or cross-module reference must carry enough identity to resolve without a search.

The initial Event-family version-1 schemas also contained several provisional or duplicated shapes:

* Event instructional references omitted `contract_version` and did not compose Core's work and record identities;
* Event supersession used a compact Event-specific object;
* Participant subjects embedded direct student or Actor fields;
* Role targeting used a bare `participant_id`;
* Role Account and Observation basis used bare `record_id` values;
* and each schema duplicated private identifier, provenance, attribution, text, and timestamp definitions.

Portia has not been deployed with production data. There is therefore no user-data compatibility reason to make those provisional shapes the implementation target. Historical version-1 contracts remain readable and immutable, while current implementation work uses reconciled version-2 Event-family contracts.

Portia also needs one canonical representation for a durable association between work items. ADR 0004 established canonical forward ownership and derived reverse views, but it did not finalize the relationship envelope, vocabulary, lifecycle, or correction behavior.

## Decision

Portia will use a **small family of closed, scope-specific, independently versioned reference and target contracts**. Portia will not use one unrestricted universal polymorphic reference object.

The initial public contract families are:

```text
roster_student_ref
actor_ref
local_record_ref
portia_work_ref
portia_work_record_ref
module_work_record_ref
person_display_snapshot
portia_target_ref
support_process_target_ref
work_relationship
```

New public schemas use canonical versioned `$id` values and repository paths. Historical Event-family version-1 schemas retain their existing unversioned paths. The schema catalog is a derived tooling index and is not itself canonical contract identity.

## Identity References

### Roster student

A durable roster-student reference contains exactly:

```text
class_id
student_id
```

The source `class_id` identifies the authoritative Core roster and may differ from the class owning the Portia work. Equality is the exact `class_id + student_id` pair. Names are not identity and must not be used to locate, merge, repair, or authorize a reference.

The serialized property name is:

```text
roster_student_ref
```

### Actor

A durable Actor reference contains exactly:

```text
actor_id
```

Equality is exact `actor_id`. The Actor Directory is authoritative only within the selected teacher workspace. Roster students are not duplicated as Actors.

The serialized property name is:

```text
actor_ref
```

Incidental, descriptive, unidentified, or withheld people may remain descriptive rather than receiving durable Actor identity.

## Record References

### Same-work record

A `local_record_ref` identifies one typed record within exactly one Portia work scope supplied by the consuming record. It contains exactly:

```text
record_kind
record_id
contract_version
```

`contract_version` is required and is either a supported nonempty string or explicit `null`. `null` is not a wildcard and must not mean newest, any, or infer automatically.

A compact local reference never repeats `module_id`, `class_id`, or `work_id`. Resolution must not search other work roots for a matching identifier.

### Portia work

A `portia_work_ref` contains exactly:

```text
module_id
class_id
work_id
work_kind
contract_version
```

`module_id` equals `portia`. Initial `work_kind` values are `event` and `support_process`. Canonical work identity is `module_id + class_id + work_id`; `work_kind` and `contract_version` are required contract checks.

Resolution is exact. A missing or superseded work is reported rather than silently replaced or followed.

### Cross-work Portia record

A `portia_work_record_ref` contains exactly:

```text
work_ref
record_ref
```

The nested `work_ref` is the sole work-scope provider for the nested local record reference. The reference identifies one record in one explicitly identified Portia work without flattening or repeating scope.

### Sibling-module record

A `module_work_record_ref` contains exactly:

```text
work_ref
record_ref
```

`work_ref` uses Core's exact `ModuleWorkRef` wire shape:

```text
module_id
class_id
work_id
```

`record_ref` uses Core's exact `ModuleRecordRef` wire shape:

```text
module_id
record_kind
record_id
contract_version
```

Both nested module IDs are required and must agree. JSON Schema validates each nested shape; application validation enforces equality because standard JSON Schema cannot compare sibling values.

The originating module remains authoritative. A Portia reference does not copy, mutate, reclassify, or authorize the sibling record.

## Display Snapshots

The initial historical person snapshot is:

```json
{
  "display_name": "Recorded display name"
}
```

The serialized sibling property name is:

```text
display_snapshot
```

A `person_display_snapshot` contains exactly one required non-whitespace `display_name`. It is frozen once the containing assertion becomes active and is excluded from identity, equality, resolution, duplicate detection, authorization, lifecycle, and repair.

Snapshots are not nested inside identity references and are not stored on relationship endpoints.

## Targets

A target identifies what a containing record applies to. It does not identify source, basis, provenance, attribution, provider, recipient, responsibility, or cause.

### Event-local targets

`portia_target_ref` supports exactly:

```text
event
one event_participant
at least two explicit event_participants
```

A singular Event Participant target contains a constrained `local_record_ref`. A plural target contains only singular participant targets. A consuming record must explicitly restrict its allowed branch and cardinality.

An Event-level target does not automatically target every Event Participant. A participant target identifies the Event Participant record, not the underlying person outside the Event context.

Canonical duplicate participant identity is prohibited even when two references differ only by `contract_version`. Participant-set order has no domain meaning.

### Support Process-local targets

`support_process_target_ref` establishes the parallel structural family:

```text
support_process
one support_process_participant
at least two explicit support_process_participants
```

This shared target structure does not finalize Support Process Participant identity, roles, provider semantics, recipient semantics, implementation, fidelity, or outcomes. Those domain decisions remain assigned to Issue #18 and later issues.

## Relationship-Record Threshold

A separate canonical relationship record is appropriate only when all of the following are true:

1. no accepted specialized field or canonical record already owns the association's meaning;
2. the association is itself a durable Portia domain fact;
3. and at least one independent-management condition applies.

Independent-management conditions include independent lifecycle, provenance, review, correction, supersession, relationship-specific detail, direct referenceability, audit requirements, or meaning that neither endpoint's existing record can fully own.

Crossing a work, class, school-year, or module boundary does not by itself justify a relationship record. Portia must not canonically represent the same association both as a specialized embedded field and as a Work Relationship.

## Work Relationship

A Work Relationship is stored beneath its semantic source Portia work. The containing work identity is the source and manages lifecycle. There is no separate owner field and no target-side canonical reverse copy.

The initial directional relationship type is:

```text
draws_context_from
```

Its meaning is:

> The source Portia work explicitly uses the target Event as contextual information in understanding, documenting, reviewing, or managing the source work.

The source may be an Event or Support Process. The target is an Event. The relationship does not assert causation, proof, blame, responsibility, credibility, diagnosis, authorization, or institutional approval.

The initial envelope contains:

```text
schema_version
record_type
module_id
class_id
work_id
relationship_id
status
relationship_type
source
target
creation_source
created_at
created_by
updated_at
updated_by
```

It may also contain subordinate neutral `detail` and structured `supersedes` entries.

Initial statuses are:

```text
proposed
active
invalidated
superseded
```

Reviewed digital entry may create an active relationship. Paper, import, automation, or ambiguous creation begins as proposed. Material correction creates a successor record. Canonical relationship records are not hard-deleted through ordinary workflows.

Persisted relationship identity, type, endpoints, creation provenance, and creation attribution are immutable. Reverse wording and target-side navigation are derived.

## Resolution and Use Eligibility

Reference assessment is layered and nonpersistent:

1. structural validity;
2. exact authoritative resolution;
3. target-contract support;
4. target lifecycle;
5. consumer-specific use eligibility;
6. authorization and privacy.

The initial resolution states are:

```text
resolved
missing
invalid
unsupported
unavailable
```

A failure may be localized to:

```text
reference
scope_provider
authority
work
record
contract
```

Resolution is separate from use disposition:

```text
usable
historical_only
not_usable
review_required
undetermined
```

Resolution never silently searches, repairs by name, normalizes identifiers, follows a successor, chooses a newest contract, or mutates the canonical referring record.

## Identifier Policy

Portia-owned IDs use these exact prefixes:

```text
evt_
sup_
actr_
ep_
epr_
rel_
```

The suffix begins with an ASCII letter or digit and then permits ASCII letters, digits, underscores, or hyphens. Periods are prohibited. Maximum length is 128 characters. Case and leading zeros are preserved. Identifiers are never normalized silently.

Core- or sibling-owned identifiers use the applicable Core authority. Portia's `structurally_safe_external_id` is only a conservative structural fallback and does not establish ownership, registration, existence, uniqueness, contract support, lifecycle, or authorization.

## Schema and Versioning Policy

Each public contract has one stable canonical `$id`. Public contracts use one file and one identity per version. There are no mutable `latest` or `current` aliases.

The historical Event-family version-1 schemas remain:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json
```

The current implementation-target Event-family schemas are:

```text
schemas/v2/event.schema.json
schemas/v2/event-participant.schema.json
schemas/v2/event-participant-role.schema.json
```

Version 2 composes the accepted public reference, target, snapshot, identifier, provenance, attribution, text, and timestamp contracts. Version 2 rejects the obsolete version-1 property names that it replaces.

Migration is explicit. Historical version-1 files and IDs remain unchanged and readable. Ordinary reads do not mutate or silently migrate them. A migration may preserve a record ID when the assertion identity and meaning remain unchanged.

A first Portia intervention publication manifest may later use manifest contract version `"1"`; that is a distinct contract family and does not imply use of native Event-family schema version 1.

## Validation Boundary

JSON Schema establishes local structure, including:

* exact object shape;
* required fields;
* constants and controlled vocabularies;
* identifier and timestamp syntax;
* discriminated branches;
* contract-version field presence;
* target cardinality;
* and relationship envelope structure.

Application validation remains responsible for:

* storage-path and persisted-identity agreement;
* exact authoritative resolution;
* nested module-ID equality;
* target existence and lifecycle eligibility;
* same-work and same-Event scope;
* canonical duplicate identity across records or contract versions;
* lifecycle transitions;
* timestamp chronology;
* supersession cycles and coordinated activation;
* relationship source/storage agreement;
* authorization and privacy;
* and transaction atomicity or recovery.

Schema-valid does not mean application-usable.

## Event-Family Reconciliation

The accepted current Event-family contracts apply the shared architecture as follows:

* Event v2 uses `module_work_record_ref` for instructional-context records and direct Event-constrained `portia_work_ref` values for supersession.
* Event Participant v2 uses `roster_student_ref`, `actor_ref`, sibling `person_display_snapshot`, and nested local-record supersession references.
* Event Participant Role v2 uses a required singular Event Participant `target`, nested Account and Observation local-record basis references, and nested local-record supersession references.
* Account and Observation references retain explicit `contract_version: null` until those public contracts are accepted; `null` is deliberate and not a wildcard.
* The retained version-1 schemas remain historical compatibility contracts only.

## Consequences

### Positive

* Later Portia records receive consistent identity, scope, target, and version semantics.
* Cross-work and cross-module references can resolve without workspace searches.
* Historical readability remains separate from identity.
* Current implementation work is not constrained by unused provisional v1 shapes.
* Work relationships have one source-owned canonical direction and auditable lifecycle.
* Structural validation remains strong without pretending to resolve cross-record facts.
* Core can consume future Portia publication manifests without importing Portia native schemas.

### Costs

* References are more explicit than bare IDs.
* Application validation must perform exact resolution and cross-record checks.
* Historical v1 and current v2 Event-family contracts require explicit dispatch.
* Some fields repeat Core-owned module identity because Core's work and record references are independently self-describing.
* Future Support Process, Account, Observation, and publication contracts must deliberately state their supported versions rather than relying on implicit latest behavior.

## Rejected Alternatives

### One universal optional-field reference object

Rejected because it permits invalid field combinations, obscures authority, weakens scope guarantees, and encourages undocumented future semantics.

### Bare IDs with workspace search

Rejected because a bare record or work ID is not complete identity across work, class, or module boundaries and can resolve nondeterministically.

### Display names as fallback identity

Rejected because names are mutable, nonunique, and inappropriate for repair, merging, or authorization.

### Canonical reverse relationship copies

Rejected because two independently editable directions can diverge. Reverse views remain derived and rebuildable.

### Silent successor following

Rejected because it rewrites historical meaning and can change a consumer's target without review.

### Rewriting Event-family v1 in place

Rejected because published schema identity must retain one stable meaning. Current implementation uses version 2 while historical version 1 remains readable.

## Follow-on Work

This ADR does not define:

* production resolution services;
* lifecycle-transition records;
* Actor records and Actor lifecycle;
* Account or Observation contracts;
* Support Process Participant semantics;
* the full Support, Intervention, implementation, fidelity, Follow-Up, or Outcome model;
* privacy projections and retention policy;
* or the Portia intervention-publication manifest and Core producer profile.

Those concerns remain assigned to later Portia foundation issues. The Core v0.6 handoff becomes ready only after Portia accepts a minimal Support Process/status contract and an intervention-publication profile and manifest fixture based on the current implementation-target contracts.
