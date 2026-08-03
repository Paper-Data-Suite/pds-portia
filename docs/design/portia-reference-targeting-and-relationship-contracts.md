# Portia Reference, Targeting, and Relationship Contracts

**Status:** Accepted  
**Project:** Paper Data Suite  
**Module:** `pds-portia`  
**Issue:** `#11 — Define shared reference, targeting, and relationship contracts`  
**Umbrella:** `#10 — Complete the Portia foundations milestone`  
**Date:** 2026-08-02  
**Revision:** 2 — accepted contracts and implemented reconciliation  
**Suggested branch:** `11-shared-reference-targeting-relationship-contracts`

## 1. Purpose

This document defines Portia’s accepted shared reference, targeting, and relationship architecture. It preserves the repository audit that exposed the relevant identity authorities, scope boundaries, and provisional shapes, and it records the decisions that reconcile those findings into implemented public contracts.

The document has four purposes:

1. identify the reference, target, basis, provenance, and relationship categories Portia must keep distinct;
2. define the accepted scope-specific public value objects and their version semantics;
3. define canonical Work Relationship ownership, direction, lifecycle, and correction behavior;
4. record how the Event-family version-2 contracts implement the accepted architecture while retaining historical version-1 schemas unchanged.

Historical audit passages describe the shapes that existed when Issue #11 began. The accepted decisions, ADR 0007, public schemas, and final implementation-status sections govern the current contract.

## 2. Scope

This audit covers:

* Core roster-student identity;
* Core module-work identity;
* Core module-record identity;
* Event root identity and inherited work scope;
* Event instructional-context references;
* Event supersession references;
* Event Participant roster-student subjects;
* Event Participant Actor subjects;
* descriptive and unknown Event Participant subjects;
* Event Participant supersession references;
* Event Participant Role participant references;
* Role Account and Observation basis references;
* Role paper-capture basis;
* Role supersession references;
* creation-source route and page references;
* local creation and update attribution;
* historical display snapshots;
* illustrative Portia Work Relationship records;
* canonical relationship ownership;
* and derived reverse views.

This audit does not define:

* the complete Actor record or Actor lifecycle;
* Account or Observation schemas;
* the Support Process schema;
* complete lifecycle-transition records;
* persistence transactions or recovery implementation;
* PDS2 page and import workflows;
* privacy projections and export rules;
* or executable reference resolution.

Those concerns remain assigned to later sub-issues beneath #10.

## 3. Sources Reviewed

### 3.1 Portia repository

The audit reviewed the current active Portia contracts, including:

```text
README.md

docs/design/portia-identity-and-storage.md
docs/design/portia-event-and-participant-domain-model.md

docs/decisions/0004-define-portia-identity-ownership-and-storage.md
docs/decisions/0005-define-event-and-participant-domain-model.md
docs/decisions/0006-define-event-participant-role-domain-model.md

docs/examples/portia-identity-and-storage-examples.md
docs/examples/portia-event-and-participant-examples.md
docs/examples/portia-event-participant-role-examples.md

schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json

tests/schema_validation/
```

### 3.2 Core contracts

The audit reviewed the current shared Core identity contracts, especially:

```text
pds-core/docs/routing_identity_models.md
pds-core/docs/module_qualified_workspace.md
pds-core/docs/pds2_payload_contract.md
```

The most relevant shared Core value objects are:

```text
ModuleWorkRef
ModuleRecordRef
RouteLocator
RouteRegistration
```

### 3.3 Comparative PDS patterns

The audit also reviewed the conceptual reference conventions used by `pds-concord`.

Those conventions are informative but are not authoritative for Portia.

Portia must preserve its own accepted identity, Event, participant, Role, and teacher-local constraints.

## 4. Authority and Decision Precedence

The following precedence applies during reconciliation:

1. accepted Portia ADRs;
2. active validated Portia schemas;
3. finalized active Portia design documents;
4. current Core public contracts;
5. validated current examples;
6. illustrative or provisional examples;
7. superseded or development-era wording.

When two active sources conflict:

* a later accepted ADR governs an earlier design proposal;
* a validated finalized schema governs a stale illustrative fragment;
* Core governs the exact meaning of Core-owned identity values;
* and Portia governs the meaning of Portia-owned work and records.

A contradiction must be documented and reconciled.

It must not be silently resolved by preserving whichever shape is easiest to implement.

## 5. Settled Architectural Constraints

The audit treats the following constraints as settled.

### 5.1 Core identity authority

Core remains authoritative for:

```text
workspace selection
class_id
class metadata
rosters
student_id within one roster
module-qualified work identity
PDS2 route identity
route registration
retained-source provenance
safe shared path construction
```

Portia must not create competing canonical Core identities.

### 5.2 Roster-student identity

A durable Portia roster-student identity is:

```text
class_id + student_id
```

A bare `student_id` is insufficient.

Names are display information, not identity.

### 5.3 Portia work identity

A Portia work item uses Core’s module-qualified work identity:

```text
module_id + class_id + work_id
```

For Portia:

```text
module_id = portia
```

The initial Portia work kinds are:

```text
event
support_process
```

The work kind is Portia domain meaning.

It is not part of Core’s generic `ModuleWorkRef` identity.

### 5.4 Canonical class-owned work roots

Every Event and Support Process has one owning class and one canonical root:

```text
classes/<class_id>/modules/portia/work/<work_id>/
```

A cross-class or cross-year reference does not duplicate or relocate canonical work.

### 5.5 Event-local child identity

Event Participants and Event Participant Roles are canonical children beneath one Event.

The containing child record repeats:

```text
module_id
class_id
work_id
```

The containing path and persisted identity must agree.

### 5.6 Workspace Actor identity

Recurring non-roster people may use Portia Actor identity:

```text
actor_id = actr_<opaque-id>
```

Actor records are workspace-scoped and Portia-owned.

Roster students must not be duplicated as Actors.

### 5.7 Canonical relationship direction

Each durable relationship has one canonical representation.

Reverse links, histories, dashboards, indexes, and timelines are derived.

### 5.8 Historical preservation

Historical references may preserve nonauthoritative display snapshots.

Current source changes must not silently rewrite those snapshots.

Missing or changed source records must not be repaired through name matching.

### 5.9 Specialized correction relationships

Event, Event Participant, and Role supersession are specialized forward relationships owned by the successor.

They preserve correction reason and lifecycle semantics.

They are not generic navigation links.

### 5.10 Module authority

A sibling module remains authoritative for its own work and records.

A Portia reference does not copy, mutate, reclassify, or assume authority over the referenced record.

## 6. Terminology

The shared architecture must use the following distinctions consistently.

### 6.1 Identity reference

An **identity reference** identifies an entity owned by an identity authority.

Examples:

```text
Core roster student
Portia Actor
Portia Event Participant
```

An identity reference does not state why the entity is involved in a workflow.

### 6.2 Record reference

A **record reference** identifies one canonical record.

A record reference may inherit unambiguous scope from its containing record or may contain complete cross-scope identity.

A record reference does not copy the target record.

### 6.3 Target

A **target** identifies what a containing record applies to.

A target does not identify:

* the record’s creator;
* an Account source;
* an observer;
* a provider;
* a recipient;
* the record’s basis;
* or the cause of the record.

### 6.4 Relationship

A **relationship** is a meaningful association between canonical endpoints.

A relationship becomes a separate canonical record when the association requires independent identity, provenance, lifecycle, correction, or durable cross-work meaning.

### 6.5 Basis

A **basis** identifies a source, artifact, or record supporting one assertion.

Basis does not establish truth, credibility, weight, agreement, or a formal Determination.

### 6.6 Provenance

**Provenance** records how, when, or by what local process a record entered or changed within Portia.

Creation provenance is not assertion basis.

### 6.7 Attribution

**Attribution** identifies the local operator or system process responsible for a record action.

Attribution does not automatically identify an Event participant, observer, Account source, provider, or institutional user.

### 6.8 Display snapshot

A **display snapshot** is a bounded historical display aid stored with a durable reference.

A display snapshot is not:

* identity;
* authorization;
* a lookup key;
* a duplicate source record;
* or a repair mechanism.

### 6.9 Derived reverse view

A **derived reverse view** reports a relationship by scanning or indexing its canonical forward source.

It is not independently editable authority.

## 7. Accepted Initial Direction

Portia will use a **small family of scope-specific reference contracts**.

Portia will not use one unrestricted universal polymorphic reference object.

The accepted conceptual families are:

```text
roster_student_ref
actor_ref
local_record_ref
portia_work_ref
portia_work_record_ref
module_work_record_ref
portia_target_ref
```

This direction is accepted because the audited reference uses have materially different identity authorities and scope rules.

For example:

* roster students require a source roster;
* Actors use a workspace Portia identity;
* same-Event Role basis may inherit Event scope;
* cross-work Portia links require complete owning-class and work identity;
* sibling-module record references require both module work and module record identity;
* and targets express application scope rather than source-record identity alone.

The exact serialized fields, nesting, version requirements, and schema names are finalized in Sections 13 through 23, ADR 0007, and the public schemas cataloged under `schemas/schema-catalog.json`.

## 8. Reference-Family Principles

### 8.1 No universal optional-field object

Portia must not define a single object resembling:

```json
{
  "module_id": null,
  "class_id": null,
  "work_id": null,
  "work_kind": null,
  "record_kind": null,
  "record_id": null,
  "student_id": null,
  "actor_id": null,
  "participant_id": null,
  "display_name": null
}
```

Such an object would:

* permit invalid combinations;
* obscure which authority owns identity;
* make scope inheritance ambiguous;
* weaken schema validation;
* and encourage future record types to invent undocumented semantics.

### 8.2 Compact references require inherited scope

A compact reference is permitted only when the containing canonical record establishes one unambiguous target scope.

For an Event-local Role basis, the containing Role supplies:

```text
module_id = portia
class_id = owning Event class
work_id = owning Event ID
```

A compact Account or Observation reference may therefore identify only the local record kind and record ID.

### 8.3 Scope boundaries require complete identity

A reference crossing a work boundary must contain the complete work identity required to locate the target without searching.

A reference crossing a module boundary must also identify the target’s owning module and public record contract.

### 8.4 Snapshots do not participate in equality

Reference equality must be determined from durable identity fields.

A display snapshot must not change equality.

### 8.5 Record-specific wrappers may remain

A specialized wrapper such as:

```json
{
  "kind": "account_ref",
  "record_id": "acct_example"
}
```

may remain when the wrapper communicates domain meaning that a generic local reference alone would not express clearly.

The specialized wrapper must nevertheless conform to the shared scope and identity rules.

### 8.6 Target contracts remain constrained by consuming records

A shared target union does not imply that every record may target every supported target kind.

Each consuming record schema must explicitly define:

* allowed target kinds;
* minimum and maximum target count;
* mixed-target behavior;
* and lifecycle eligibility.

## 9. Audit Status Legend

The audit uses these dispositions.

| Disposition | Meaning |
| --- | --- |
| **Retain** | Current shape and semantics are accepted and should remain. |
| **Retain specialized** | Current shape is intentionally domain-specific but must align with shared semantics. |
| **Reconcile** | Current semantics remain, but shape or terminology must be normalized. |
| **Replace provisional** | Current material is illustrative or incomplete and should be replaced before implementation. |
| **Defer exact contract** | The issue records the boundary, but another issue owns the final domain contract. |
| **Derived only** | Must not become an independently editable canonical record. |

## 10. Summary Reconciliation Matrix

| Current item | Current authority | Current scope | Audit disposition | Shared-family mapping |
| --- | --- | --- | --- | --- |
| Core `ModuleWorkRef` | Core public contract | One module work item | Retain | Foundation for `portia_work_ref` and `module_work_record_ref` |
| Core `ModuleRecordRef` | Core public contract | One module-owned record, without work scope | Retain | Record component of `module_work_record_ref` |
| Event root `module_id + class_id + work_id` | Event schema and ADRs | Owning Event | Retain | Inherited scope for local references |
| Event `instructional_context.external_refs` | Event schema | Cross-module instructional record | Reconcile | `module_work_record_ref` |
| Event `supersedes` | Event schema and ADR 0005 | Cross-work Portia Event | Retain specialized | Specialized `portia_work_ref` |
| Participant roster-student subject | Participant schema and ADR 0005 | Core roster identity | Retain | `roster_student_ref` plus snapshot |
| Participant Actor subject | Participant schema and ADR 0005 | Workspace Actor identity | Retain | `actor_ref` plus snapshot |
| Descriptive-person subject | Participant schema | Event-local non-durable description | Retain specialized | Not a durable reference |
| Unknown-person subject | Participant schema | Event-local unresolved identity | Retain specialized | Not a durable reference |
| Participant `supersedes` | Participant schema and ADR 0005 | Same Event | Retain specialized | Specialized `local_record_ref` |
| Role `participant_id` | Role schema and ADR 0006 | Same Event | Retain specialized | Event Participant target/reference |
| Role Account basis | Role schema and ADR 0006 | Same Event | Retain specialized | Specialized `local_record_ref` |
| Role Observation basis | Role schema and ADR 0006 | Same Event | Retain specialized | Specialized `local_record_ref` |
| Role paper basis | Role schema and ADR 0006 | Same Event/PDS2 capture context | Retain specialized | Provenance/basis, not generic record relationship |
| Role `supersedes` | Role schema and ADR 0006 | Same Event | Retain specialized | Specialized `local_record_ref` |
| `creation_source.route_id + page_record_id` | Event, Participant, and Role schemas | Containing work’s paper provenance | Retain specialized; defer exact PDS2 contract | Provenance, not generic relationship |
| `created_by` and `updated_by` | Current schemas | Local action attribution | Retain specialized | Attribution agent, not `actor_ref` |
| Historical display snapshots | ADRs and schemas | Adjacent to durable identity | Reconcile placement conventions | Snapshot companion to identity reference |
| ADR 0004 Work Relationship example | Accepted architecture, illustrative shape | Cross-work Portia relationship | Replace provisional envelope | Canonical Work Relationship using `portia_work_ref` endpoints |
| Reverse links and histories | ADR 0004 and README | Derived cross-record navigation | Derived only | Derived from canonical references and relationships |

## 11. Detailed Current-Shape Audit

### 11.1 Core `ModuleWorkRef`

#### Current shape

```json
{
  "module_id": "portia",
  "class_id": "english10_p2",
  "work_id": "evt_example"
}
```

#### Authority

Core owns the structure and validation of `ModuleWorkRef`.

#### Meaning

The three fields identify one module-owned work context.

They do not identify:

* the Portia work kind;
* a child record;
* a student;
* or the existence or validity of the work root.

#### Audit finding

This is the mandatory identity foundation for every complete cross-work Portia reference.

Portia must not replace it with:

* a bare `work_id`;
* a filesystem path;
* a display label;
* or a student-based lookup.

#### Disposition

**Retain.**

`portia_work_ref` should build on this identity and may add Portia-specific contract metadata such as `work_kind`.

Whether `module_id = portia` is explicit or implied remains an open serialization decision.

### 11.2 Core `ModuleRecordRef`

#### Current shape

Core’s exact mapping includes:

```json
{
  "module_id": "concord",
  "record_kind": "artifact_page",
  "record_id": "artifact_page_example",
  "contract_version": "1"
}
```

Core’s current exact mapping always contains the `contract_version` key, including when its value is `null`.

#### Authority

Core owns the generic structure.

The originating module owns:

* record-kind meaning;
* record existence;
* lifecycle;
* usability;
* and the public contract identified by `contract_version`.

#### Audit finding

`ModuleRecordRef` alone is not a complete persisted cross-work reference for Portia because it contains no:

```text
class_id
work_id
```

Core can omit those values in route registrations because the separate `RouteLocator` supplies work context.

A Portia domain record referring directly to a sibling-module record must preserve both:

```text
ModuleWorkRef
ModuleRecordRef
```

or an equivalent complete structure.

#### Disposition

**Retain as Core-owned component.**

Use as the record-identity component of `module_work_record_ref`.

### 11.3 Event root identity as inherited scope

#### Current shape

Every Event root contains:

```text
module_id
class_id
work_id
work_kind
```

Every Event-local child currently repeats:

```text
module_id
class_id
work_id
```

#### Meaning

The containing record establishes its owning Event scope.

#### Audit finding

This accepted repetition makes compact same-Event references possible without ambiguity.

A compact local reference can inherit:

```text
module_id
class_id
work_id
```

from its containing canonical record.

The compact reference must not repeat those fields.

#### Disposition

**Retain.**

This becomes the scope-inheritance rule for `local_record_ref`.

### 11.4 Event instructional-context external references

#### Current shape

The Event schema currently defines:

```json
{
  "module_id": "quillan",
  "class_id": "english10_p2",
  "work_id": "essay_1",
  "record_kind": "assignment",
  "record_id": "assignment_example"
}
```

The current schema description calls this an initial module-qualified instructional reference shape.

#### Meaning

The reference connects an Event’s instructional context to a record owned by another module.

The source module remains authoritative.

#### Audit finding

The shape correctly preserves:

```text
module_id
class_id
work_id
record_kind
record_id
```

but does not include:

```text
contract_version
```

It therefore does not fully align with Core’s current `ModuleRecordRef` contract.

The shape also does not distinguish explicitly between:

* referencing an entire sibling work item;
* and referencing one child record inside that work item.

#### Additional validation finding

The current `module_id` and `record_kind` fields use Portia’s generic `safeId` definition.

Core requires `module_id` and `record_kind` to be lowercase.

The current schema does not structurally enforce that lowercase requirement.

#### Disposition

**Reconcile.**

Replace this provisional `$defs.externalRecordRef` with the accepted complete sibling-module reference contract.

Existing Event semantics do not change.

### 11.5 Event supersession reference

#### Current shape

The Event schema stores:

```json
{
  "class_id": "english10_p2",
  "work_id": "evt_prior"
}
```

inside the successor Event’s `supersedes` array.

#### Meaning

The successor Event canonically identifies one prior Event it replaces.

The target may belong to another class if a provenance-preserving ownership correction requires it.

#### Audit finding

This is a specialized cross-work Portia reference.

The current shape omits:

```text
module_id
work_kind
contract_version
```

because:

* `module_id = portia` is implied;
* `work_id` is structurally restricted to the Event ID prefix;
* and the containing field’s meaning requires the target to be an Event.

The reference remains unambiguous within Portia’s accepted Event contract.

#### Disposition

**Retain specialized** and reconcile through a direct Event-constrained `portia_work_ref` value.

Event v2 implements that complete shape in `supersedes`. The relationship remains specialized and is not replaced by a generic Work Relationship record.

### 11.6 Event Participant roster-student subject

#### Current shape

```json
{
  "kind": "roster_student",
  "student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Avery Chen"
  }
}
```

#### Meaning

`student_ref` establishes durable Core roster identity.

`display_snapshot` preserves historical readability.

#### Audit finding

The identity contract is accepted and complete.

The snapshot is correctly excluded from identity.

The older identity-and-storage examples used a different placement:

```json
{
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

That older fragment is illustrative and predates the finalized participant schema.

It is stale relative to the active schema.

#### Disposition

**Retain** the finalized participant shape.

Map `student_ref` to the shared `roster_student_ref` identity value.

Document whether snapshot placement is:

* always inside the containing discriminated subject;
* always adjacent to the reference field;
* or selected by each containing contract under one shared snapshot semantic rule.

### 11.7 Event Participant Actor subject

#### Current shape

```json
{
  "kind": "actor",
  "actor_id": "actr_example",
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

#### Meaning

`actor_id` identifies a reusable Portia Actor.

The snapshot preserves the display value recorded at participant creation.

#### Audit finding

The durable Actor identity is accepted.

The reusable `actor_ref` contract is finalized as an exact object containing only `actor_id`. Event Participant v2 places it beside the bounded `display_snapshot`.

The older identity-and-storage examples use:

```json
{
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

The two forms differ in whether:

* `actor_id` appears directly in the discriminated subject;
* or an explicit `actor_ref` object is nested.

The active Event Participant schema governs participant records, but later Communications, Accounts, Supports, and Follow-Ups need a reusable Actor reference contract.

#### Disposition

**Retain** the participant subject semantics.

**Reconcile** the reusable `actor_ref` value and snapshot placement for later records.

### 11.8 Descriptive-person subject

#### Current shape

```json
{
  "kind": "descriptive_person",
  "description_type": "outside_student",
  "display_label": "Unidentified student",
  "detail": "Optional neutral detail"
}
```

#### Meaning

The object describes a one-time or incidental person without claiming durable identity.

#### Audit finding

This is not a durable reference.

It must not be converted into:

```text
roster_student_ref
actor_ref
```

without a deliberate reviewed identity-resolution operation.

The older identity example includes:

```json
{
  "actor_id": null
}
```

inside a descriptive-person fragment.

The finalized participant schema does not permit `actor_id: null`.

The finalized schema is clearer because absence of durable identity should not be encoded as a null Actor reference.

#### Disposition

**Retain specialized** as an Event Participant subject variant.

Do not include it in the durable reference family.

Mark the older `actor_id: null` illustrative fragment for correction.

### 11.9 Unknown-person subject

#### Current shape

```json
{
  "kind": "unknown_person",
  "reason": "identity_not_known",
  "description": "Optional neutral description"
}
```

#### Meaning

The Event Participant exists, but the underlying person identity is unavailable, withheld, ambiguous, or unresolved.

#### Audit finding

This is an explicit uncertainty record, not an invalid or incomplete reference.

It must not be resolved through:

* name matching;
* inferred roster membership;
* an arbitrary Actor;
* or the first matching external record.

#### Disposition

**Retain specialized.**

It is not a member of the durable reference family.

### 11.10 Event Participant supersession reference

#### Current shape

```json
{
  "participant_id": "ep_prior",
  "reason": "identity_resolved"
}
```

Optional reason detail is permitted under controlled conditions.

#### Meaning

A successor participant identifies a prior Event Participant in the same Event.

#### Audit finding

The reference inherits:

```text
module_id
class_id
work_id
```

from the successor participant.

The field is specialized because it also records correction reason.

The target cannot legitimately belong to another Event.

#### Disposition

**Retain specialized.**

Semantically align its identity component with `local_record_ref`.

Do not remove the controlled reason or replace the relationship with a generic Work Relationship record.

### 11.11 Role `participant_id`

#### Current shape

```json
{
  "participant_id": "ep_example"
}
```

The Role itself contains the owning Event’s:

```text
module_id
class_id
work_id
```

#### Meaning

The Role applies to one existing Event Participant.

#### Audit finding

This is an Event-local participant target/reference.

It intentionally does not embed:

```text
student_ref
actor_id
subject
display_snapshot
```

The Event Participant remains authoritative for identity.

The local ID is sufficient because the containing Role establishes exactly one Event scope.

#### Disposition

**Retain specialized.**

Use it as the precedent for a compact single-Event-Participant target.

### 11.12 Role Account basis

#### Current shape

```json
{
  "kind": "account_ref",
  "record_id": "acct_example"
}
```

#### Meaning

The Account supports one Role assertion.

The Account must belong to the same Event.

#### Audit finding

The compact reference correctly inherits Event scope from the Role.

The domain-specific `kind` communicates more than a generic record kind:

* this entry is basis;
* it references an Account;
* and the Account has Role-specific eligibility requirements.

The field must not repeat:

```text
module_id
class_id
work_id
event_id
```

#### Disposition

**Retain specialized.**

Align the identity semantics with `local_record_ref`.

Do not replace it with a generic cross-work reference.

### 11.13 Role Observation basis

#### Current shape

```json
{
  "kind": "observation_ref",
  "record_id": "obs_example"
}
```

#### Meaning

The Observation supports one Role assertion.

The Observation must belong to the same Event.

#### Audit finding

The same findings as Account basis apply.

#### Disposition

**Retain specialized.**

Align with `local_record_ref` semantics while preserving the domain-specific wrapper.

### 11.14 Role paper-capture basis

#### Current shape

```json
{
  "kind": "paper_capture",
  "route_id": "rt_example",
  "page_record_id": "pg_example"
}
```

#### Meaning

The returned paper artifact supports or proposed the Role assertion.

#### Audit finding

This object is basis and capture provenance.

It is not a generic reference to an Account, Observation, Event, or sibling-module record.

Its exact route and page meaning depends on the PDS2 and Portia page contracts that Issue #20 will finalize.

The Role contract already requires exact equality with the corresponding paper creation-source fields for paper-derived Roles.

#### Disposition

**Retain specialized.**

Do not generalize it into `local_record_ref` or Work Relationship.

Defer the complete PDS2 reference contract to Issue #20.

### 11.15 Role supersession reference

#### Current shape

```json
{
  "role_id": "epr_prior",
  "reason": "basis_corrected"
}
```

Optional nested detail is permitted where required.

#### Meaning

A successor Role replaces one prior Role in the same Event.

One successor may identify several prior Roles.

#### Audit finding

The identity inherits Event scope.

The object also preserves correction reason.

It is a specialized lifecycle relationship, not generic navigation.

#### Disposition

**Retain specialized.**

Align its identity semantics with `local_record_ref`.

Do not replace it with Work Relationship records.

### 11.16 Creation-source route and page references

#### Current shape

Paper creation sources contain:

```json
{
  "type": "paper_capture",
  "stage": "preallocated",
  "route_id": "rt_example",
  "page_record_id": "pg_example"
}
```

or:

```json
{
  "type": "paper_capture",
  "stage": "ingested",
  "route_id": "rt_example",
  "page_record_id": "pg_example"
}
```

Role records permit only `ingested`.

#### Meaning

The fields preserve how the canonical record entered Portia.

#### Audit finding

These are provenance fields.

They are not:

* assertion basis by themselves;
* Event targets;
* Work Relationships;
* or generic sibling-module references.

The current objects omit the full Core `RouteLocator` because the containing Portia record supplies:

```text
module_id
class_id
work_id
```

Whether this compact representation remains sufficient depends on the final Portia PDS2 page and capture contract.

#### Disposition

**Retain specialized; defer exact contract.**

Issue #20 owns final page, route, capture-batch, and returned-source semantics.

### 11.17 `created_by` and `updated_by`

#### Current shapes

```json
{
  "type": "local_operator",
  "display_label": "Taylor Morgan"
}
```

```json
{
  "type": "system_process",
  "process_id": "paper_capture_ingest"
}
```

#### Meaning

These values attribute a local record action.

#### Audit finding

A `local_operator` display label is not durable person identity.

A `system_process` identifies a local process kind, not a Portia Actor.

The values must not be converted automatically into:

```text
actor_ref
participant_ref
Account source
observer
provider
recipient
```

Portia’s teacher-local deployment does not currently provide authenticated user identity.

#### Disposition

**Retain specialized.**

Exclude attribution agents from the shared person-reference family.

The later lifecycle issue may reuse the attribution object.

### 11.18 Historical display snapshots

#### Current shapes

Current finalized participant subjects use:

```json
{
  "display_snapshot": {
    "display_name": "Recorded name"
  }
}
```

Older illustrative examples place the snapshot beside `student_ref` or `actor_ref`.

#### Meaning

The snapshot preserves what Portia displayed or knew when the containing record was created.

#### Audit finding

The semantic rule is accepted.

The placement convention is inconsistent across examples.

The current snapshot supports only:

```text
display_name
```

Later work and sibling-module references may require a different bounded label such as:

```text
record_label
work_label
```

A single unrestricted generic snapshot would risk copying source records.

#### Disposition

**Reconcile.**

Define bounded person, work, and record snapshot shapes only where justified.

Snapshots remain optional or required according to the containing record contract.

### 11.19 ADR 0004 Work Relationship example

#### Current illustrative shape

```json
{
  "record_kind": "work_relationship",
  "record_id": "rel_example",
  "source": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "sup_example",
    "work_kind": "support_process"
  },
  "target": {
    "module_id": "portia",
    "class_id": "english10_p5",
    "work_id": "evt_example",
    "work_kind": "event"
  },
  "relationship": "supported_by_event",
  "status": "active"
}
```

The identity examples use the relationship label:

```text
informed_by_event
```

instead.

#### Meaning

A Support Process owns a durable directed link to an Event.

The target Event does not store an editable reverse copy.

#### Audit finding

The architecture is accepted.

The serialized envelope is finalized by `schemas/v1/work-relationship.schema.json`.

The current examples lack the normal Portia canonical envelope:

```text
schema_version
record_type
module_id
class_id
work_id
creation_source
created_at
created_by
updated_at
updated_by
```

Terminology also drifts among:

```text
record_kind
record_id
relationship
supported_by_event
informed_by_event
```

The source and target objects are close to the proposed `portia_work_ref`.

The initial relationship vocabulary is finalized with the sole directional type `draws_context_from`.

#### Disposition

**Replaced and implemented.**

The canonical Work Relationship schema retains the accepted source ownership and derived reverse-view rules.

### 11.20 Derived reverse views

#### Current rule

When a Support Process stores:

```text
Support Process S -> Event A
```

an Event view may display:

```text
Event A <- linked from Support Process S
```

#### Meaning

The reverse view is generated from the canonical relationship record stored beneath the Support Process.

#### Audit finding

No reverse canonical record is required.

A persisted reverse index, if later introduced, must remain:

* nonauthoritative;
* disposable;
* rebuildable;
* versioned;
* and traceable to the canonical source record.

#### Disposition

**Derived only.**

### 11.21 Identifier validation drift

#### Current Core contract

Core’s documented generic safe identifier set permits:

```text
ASCII letters
digits
underscore
hyphen
```

Core additionally requires lowercase for:

```text
module_id
record_kind
```

#### Current Portia schemas

The three current schemas use a generic pattern equivalent to:

```regex
^[A-Za-z0-9][A-Za-z0-9._-]*$
```

This pattern also permits:

```text
.
```

It does not require lowercase for module or record-kind values.

#### Audit finding

The schemas describe the pattern as conservative structural validation while stating that Core remains authoritative.

That division is explicit, but the pattern is broader than the reviewed Core contract.

A future reusable reference schema must not accidentally present the broader pattern as exact Core validation.

#### Disposition

**Reconcile.**

The shared schema decision must choose one of these explicit approaches:

1. structurally match Core’s documented identifier contract exactly;
2. import or mirror an exact versioned Core schema if one exists;
3. or intentionally perform weaker structural validation while clearly assigning exact validation to application logic.

The current ambiguity must not persist unnoticed.

## 12. Stale and Provisional Material

The audit identified development-era material that must not be treated as current serialized authority.

### 12.1 Identity examples predating finalized schemas

`docs/examples/portia-identity-and-storage-examples.md` states that its JSON fragments are illustrative rather than final.

Its examples include shapes such as:

```text
owning_class_id
event_id
record_kind
record_id
subject.class_id
subject.student_id
actor_id: null
```

The finalized Event and Event Participant schemas instead use:

```text
class_id
work_id
record_type
participant_id
subject.student_ref
discriminated descriptive and unknown subjects
```

#### Required reconciliation

The identity examples are reconciled by the accepted shared-reference examples and Event-family v2 schemas. Earlier fragments remain historical audit evidence and must not be treated as current schemas.

### 12.2 Early paper source terminology

Earlier design material used terms such as:

```text
paper_quick_capture
returned_paper
```

The active schemas use:

```text
paper_capture
```

with explicit stages.

#### Required reconciliation

The active schema terminology governs.

Stale terminology should be corrected when Issue #11 updates related design material, unless the text is explicitly historical.

### 12.3 Work Relationship labels

Current material uses both:

```text
supported_by_event
informed_by_event
```

without a finalized relationship vocabulary.

#### Required reconciliation

Do not select one merely because it appears first.

The later relationship-vocabulary decision must define exact semantics and direction.

## 13. Shared-Family Mapping

### 13.1 `roster_student_ref`

#### Conceptual identity

```text
class_id
student_id
```

#### Current accepted use

Event Participant `roster_student` subject.

#### Excluded from identity

```text
display_name
preferred_name
period
email
demographics
```

#### Snapshot

A bounded historical display snapshot may accompany the identity according to the containing record contract.

### 13.2 `actor_ref`

#### Conceptual identity

```text
actor_id
```

#### Current accepted use

Event Participant `actor` subject.

#### Excluded from identity

```text
display_name
actor_type
role_labels
contact information
current status
```

#### Snapshot

A bounded historical display snapshot may accompany the identity.

### 13.3 `local_record_ref`

#### Conceptual identity

```text
inherited module_id
inherited class_id
inherited work_id
record_kind
record_id
target contract version, if required
```

#### Current accepted specialized uses

```text
Event Participant supersession
Role participant reference
Role Account basis
Role Observation basis
Role supersession
```

#### Rule

A local reference must not repeat inherited scope.

### 13.4 `portia_work_ref`

#### Conceptual identity

```text
module_id
class_id
work_id
```

with Portia work-kind contract metadata as required.

#### Current uses

```text
Event supersession
Work Relationship endpoints
Support Process links
cross-year Support continuation
```

### 13.5 `portia_work_record_ref`

#### Conceptual identity

```text
Portia work identity
Portia record kind
Portia record ID
target contract version, if required
```

#### Current uses

No finalized general-purpose serialized form exists yet.

Later issues will require it for explicit cross-work references to Portia child records.

### 13.6 `module_work_record_ref`

#### Accepted shape

The contract composes two exact nested Core wire values:

```text
work_ref   = ModuleWorkRef
record_ref = ModuleRecordRef
```

The nested module IDs must agree. Event v2 uses this contract for instructional-context external references.

#### Rule

A bare Core `ModuleRecordRef` is insufficient when the containing context does not separately supply the sibling work identity.

### 13.7 `portia_target_ref`

#### Conceptual role

A discriminated value identifying what a containing record applies to.

#### Initial expected target kinds

```text
owning Event
one Event Participant
several explicitly selected Event Participants
owning Support Process
complete referenced Portia work where later contracts permit
```

#### Rule

Each consuming record must restrict the target kinds and cardinality it supports.

## 14. Preliminary Scope-Inheritance Rules

The audit supports the following rules.

### Rule 1: containing-work scope

A canonical Portia child record supplies:

```text
module_id
class_id
work_id
```

for references that are explicitly constrained to that same work root.

### Rule 2: same-Event participant scope

A compact:

```text
participant_id
```

may identify an Event Participant only when the containing record belongs to the same Event and the consuming contract forbids cross-Event targets.

### Rule 3: same-work record scope

A compact record reference may identify another child record only when:

* the target must belong to the same work root;
* target record kind is explicit;
* record ID is durable;
* and application validation confirms target existence and type.

### Rule 4: cross-work Portia scope

A cross-work Portia reference requires at least:

```text
class_id
work_id
```

plus sufficient Portia type metadata to validate the expected work or record kind.

### Rule 5: cross-module scope

A sibling-module record reference requires:

```text
module_id
class_id
work_id
record_kind
record_id
contract_version behavior
```

The accepted shape is composed: `work_ref` contains Core `ModuleWorkRef`, and `record_ref` contains Core `ModuleRecordRef`.

### Rule 6: workspace Actor scope

An Actor reference uses:

```text
actor_id
```

because the Actor Directory is workspace-scoped within the selected teacher workspace.

The reference must not be resolved across several workspaces.

### Rule 7: source roster scope

A roster-student reference always includes:

```text
class_id
student_id
```

even when the student belongs to the Event’s owning class.

### Rule 8: no path identity

References must not store a filesystem path as their identity.

Paths are derived from validated identities and canonical path contracts.

## 15. Reference Equality Findings

The audit supports these conceptual equality rules.

| Reference family | Identity equality |
| --- | --- |
| Roster student | `class_id + student_id` |
| Actor | `actor_id` |
| Event Participant local reference | inherited Event scope + `participant_id` |
| Same-work child record | inherited work scope + record kind + record ID + contract version semantics |
| Portia work | `module_id + class_id + work_id` |
| Portia cross-work record | work identity + record kind + record ID + contract version semantics |
| Sibling-module record | module work identity + module record identity |
| Display snapshot | never participates in identity equality |

The exact effect of:

```text
contract_version omitted
contract_version = null
contract_version = "1"
```

remains an open decision.

## 16. Reference Resolution Findings

A shared reference object establishes structural identity only.

It does not establish:

* target existence;
* canonical path agreement;
* current lifecycle eligibility;
* permission to use the target;
* factual truth;
* evidentiary weight;
* or current module availability.

Application logic must distinguish at least:

```text
structurally invalid
structurally valid but unresolved
resolved to wrong kind
resolved to unsupported contract
resolved historically but not currently eligible
resolved and currently eligible
```

The containing record or operation must define which resolution state it requires.

## 17. Targeting Findings

### 17.1 Event-level targeting

A record targeting the Event as a whole does not target every Event Participant.

### 17.2 Participant targeting

A participant-specific Event record should target:

```text
Event Participant
```

rather than the underlying student or Actor identity.

### 17.3 Several participants

A record applying to several participants must identify each participant explicitly.

Several targets do not create a Group or imply identical involvement.

### 17.4 Cardinality

The shared target contracts use closed discriminated branches. Singular participant targets contain `record_ref`; plural branches contain a `targets` array of singular targets. Consuming records use their own field name, such as the Role v2 field `target`, and must restrict the allowed branch explicitly.

Omission never creates an Event-level default.

### 17.5 Support Process targeting

The audit confirms that future Support Process records will need shared work and person references.

It does not finalize support-recipient, provider, or implementation-subject semantics.

Those remain assigned to Issue #18.

## 18. Relationship Findings

### 18.1 Not every reference is a relationship record

Embedded references are appropriate when the containing record fully owns the relationship meaning.

Examples include:

```text
Role basis
participant subject
Account source
Observation observer
Response recipient
Follow-Up owner
supersession reference
creation provenance
```

### 18.2 Separate relationship records are justified for durable cross-work associations

A canonical Work Relationship is appropriate when the association:

* connects independently managed work items;
* has explicit semantic direction;
* may carry its own provenance or lifecycle;
* may be corrected or invalidated;
* and must remain navigable independently of either endpoint’s immediate fields.

### 18.3 Canonical owner

The accepted default is:

> The work item that creates, manages, or gives meaning to the relationship owns the canonical relationship record.

### 18.4 Direction

Every relationship type must define:

```text
source meaning
target meaning
canonical owner
allowed endpoint kinds
derived reverse wording
```

### 18.5 Vague relationships are unsafe

A generic:

```text
related_to
```

should not become the default for unresolved semantics.

A relationship label must not imply unsupported causation or proof.

### 18.6 Specialized lifecycle links remain specialized

Supersession remains in the successor record.

It must not be duplicated as a Work Relationship merely to support navigation.

## 19. Privacy and Data-Minimization Findings

A reference should carry only enough information to:

* establish durable identity;
* select the target contract;
* preserve bounded historical readability where necessary;
* and validate the containing record’s intended use.

A reference must not copy:

* Account text;
* Observation text;
* student work;
* ratings;
* feedback;
* behavior labels;
* disability information;
* demographics;
* contact details;
* private notes;
* or complete sibling-module records.

Display snapshots must remain bounded.

## 20. Schema Findings

### 20.1 Reuse is required

Later Portia schemas need reusable `$defs` for shared reference and target values.

Duplicating the same shape independently across every schema would recreate the inconsistency this issue is intended to prevent.

### 20.2 Specialized wrappers may reference shared `$defs`

A domain-specific object may preserve its discriminator while reusing a shared identity definition.

Conceptually:

```json
{
  "kind": "account_ref",
  "record_id": "<shared Account ID definition>"
}
```

### 20.3 External `$ref` testing must be deliberate

If shared schemas use external `$ref` values, tests must load them through an explicit registry or resolver.

Validation must not succeed only because the current directory happens to contain a file with a matching name.

### 20.4 Existing schemas require reconciliation, not wholesale replacement

The Event, Participant, and Role schemas contain accepted specialized contracts.

They should change only where:

* a current shape is provisional;
* shared terminology eliminates drift;
* or a reusable schema can replace exact duplication without weakening validation.

## 21. Application-Validation Findings

JSON Schema can enforce:

* exact object shape;
* required fields;
* discriminators;
* identifier patterns;
* contract-version field shape;
* duplicate entries inside one array;
* compact-versus-complete variant exclusivity;
* bounded snapshots;
* and relationship envelope structure.

Application logic must enforce:

* selected workspace containment;
* Core class and roster existence;
* student existence;
* Actor existence;
* work-root existence;
* child-record existence;
* path and identity agreement;
* expected work kind;
* expected record kind;
* target contract support;
* lifecycle eligibility;
* same-Event scope;
* same-work scope;
* relationship owner/source agreement;
* endpoint compatibility;
* duplicate canonical relationships across files;
* reverse-copy absence;
* and historically valid versus currently eligible resolution.

## 22. Accepted Decision Summary

Issue #11 resolved the audit through the following accepted decisions:

1. Portia uses a small family of scope-specific contracts rather than one universal reference object.
2. `roster_student_ref` contains exactly `class_id + student_id`.
3. `actor_ref` contains exactly `actor_id`.
4. `local_record_ref` contains exactly `record_kind + record_id + contract_version` and inherits one unambiguous work scope.
5. `portia_work_ref` contains `module_id + class_id + work_id + work_kind + contract_version`.
6. `portia_work_record_ref` composes one `work_ref` and one `record_ref`.
7. `module_work_record_ref` composes Core `ModuleWorkRef` and `ModuleRecordRef` wire shapes.
8. `person_display_snapshot` contains only `display_name` and never participates in identity.
9. `portia_target_ref` distinguishes Event, singular Event Participant, and explicit plural Event Participants.
10. `support_process_target_ref` reserves the parallel Support Process-local structure without finalizing Issue #18 semantics.
11. A separate relationship record is permitted only when the association is a durable independently managed domain fact not already owned by a specialized field or record.
12. Work Relationships are stored beneath their semantic source; reverse views are derived.
13. The sole initial directional relationship type is `draws_context_from`.
14. Work Relationships use review-gated append-preserving lifecycle and replacement-based correction.
15. Reference assessment separates structural validity, authoritative resolution, contract support, lifecycle, consumer eligibility, and authorization/privacy.
16. Portia-owned IDs use exact prefixes, prohibit periods, preserve case and leading zeros, and have a maximum length of 128.
17. Public schemas use stable versioned canonical identities without mutable latest aliases.
18. Historical Event-family v1 schemas remain unchanged and readable.
19. Event, Event Participant, and Event Participant Role v2 are the current implementation-target contracts.

ADR 0007 is the concise decision record for these conclusions.

## 23. Implemented Public Contracts

The accepted shared schemas are organized beneath:

```text
schemas/v1/identifiers/
schemas/v1/references/
schemas/v1/snapshots/
schemas/v1/targets/
schemas/v1/common/
schemas/v1/provenance/
schemas/v1/attribution/
schemas/v1/work-relationship.schema.json
```

The noncanonical tooling catalog is:

```text
schemas/schema-catalog.json
```

Offline tests construct an explicit local registry from checked-in canonical `$id` values. Duplicate `$id` values, unresolved `$ref` values, and catalog/path disagreement are failures.

The public contract examples are documented in:

```text
docs/examples/portia-reference-targeting-and-relationship-examples.md
```

## 24. Event-Family Reconciliation Completed

The historical schemas remain:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json
```

The current implementation-target schemas are:

```text
schemas/v2/event.schema.json
schemas/v2/event-participant.schema.json
schemas/v2/event-participant-role.schema.json
```

Reconciliation is complete:

* Event v2 replaces flat instructional references with `module_work_record_ref` and uses direct Event-constrained `portia_work_ref` supersession values.
* Event Participant v2 replaces `student_ref` and bare `actor_id` with `roster_student_ref` and `actor_ref`, retains sibling snapshots, and uses local-record supersession references.
* Event Participant Role v2 replaces bare `participant_id` targeting with a singular Event Participant target, wraps Account and Observation basis identity in local-record references, and uses local-record Role supersession references.
* Migration fixtures document explicit v1-to-v2 transformations while preserving canonical identity and creation provenance where the underlying assertion is unchanged.

The v1 files are not edited, aliased, or silently migrated.

## 25. Final Conclusion and Follow-on Boundary

Issue #11 establishes a complete shared reference, targeting, snapshot, resolution, versioning, and Work Relationship foundation for later Portia records.

The architecture now provides:

```text
exact identity authority
explicit inherited versus complete scope
required contract-version semantics
closed target families
bounded historical display snapshots
one canonical relationship direction
append-preserving correction
layered resolution outcomes
stable public schema identities
current Event-family v2 contracts
```

The issue does not implement production resolution, lifecycle-transition records, Support Process domain semantics, privacy projections, or publication manifests.

The next domain step belongs to Issue #18: define the minimum Support Process root and status contract needed for honest Portia intervention publication, then complete the broader Support, Intervention, implementation, and fidelity model deliberately.

The Core v0.6 handoff checkpoint is reached only after Portia also accepts:

1. the minimal Support Process/status contract;
2. the Portia intervention producer profile;
3. the immutable intervention manifest contract and synthetic fixture;
4. and the publication privacy boundary.
