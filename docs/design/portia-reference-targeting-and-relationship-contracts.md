# Portia Reference, Targeting, and Relationship Contracts

**Status:** Current-reference audit and accepted initial direction  
**Project:** Paper Data Suite  
**Module:** `pds-portia`  
**Issue:** `#11 — Define shared reference, targeting, and relationship contracts`  
**Umbrella:** `#10 — Complete the Portia foundations milestone`  
**Date:** 2026-07-24  
**Revision:** 1 — repository audit and reference-family direction  
**Suggested branch:** `11-shared-reference-targeting-relationship-contracts`

## 1. Purpose

This document begins Portia’s shared reference, targeting, and relationship architecture by auditing every reference pattern already present in the active repository and the relevant shared contracts supplied by `pds-core`.

The audit has four purposes:

1. identify every existing reference, target, and relationship shape;
2. distinguish accepted domain-specific contracts from provisional or stale examples;
3. identify contradictions, incomplete identities, and terminology drift;
4. establish the accepted initial direction for the shared contract work.

This revision does not finalize every serialized reference object or the canonical Work Relationship schema.

It establishes the evidence and constraints that those later decisions must preserve.

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

The exact serialized fields, nesting, version requirements, and schema names remain to be decided.

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

### 8.7 Embedded references versus canonical relationships

A separate Work Relationship is not justified merely because an association:

* crosses a work boundary;
* crosses a class boundary;
* crosses a school year;
* points to another module;
* is expected to persist;
* appears in navigation;
* or may be queried in a derived view.

Those characteristics may increase the need for complete target identity, but they do not by themselves create an independently managed domain fact.

Portia applies the relationship-record threshold accepted in Decision 9.

A separate canonical Work Relationship is appropriate only when:

1. no accepted specialized field or canonical record fully owns the association’s meaning;
2. the association is itself a durable Portia domain fact;
3. and at least one independent-management condition applies.

Independent-management conditions include:

* independent lifecycle or status;
* independent creation provenance or review;
* independent correction, invalidation, or supersession;
* relationship-specific detail;
* direct referenceability;
* independent audit or navigation requirements;
* or meaning that neither endpoint’s existing canonical record can fully own.

When those conditions are not satisfied, the association remains an embedded reference under its specialized containing contract.

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
| Shared reference resolution outcomes | Issue #11 and accepted reference-family contracts | Exact authoritative lookup without silent repair or retargeting | Separate resolution, native lifecycle, and consumer eligibility | Derived assessment using `resolved`, `missing`, `invalid`, `unsupported`, or `unavailable` |
| Associations that may require independent canonical identity | ADR 0004 and Issue #11 | Embedded reference or canonical Work Relationship | Apply the semantic-independence threshold; do not decide from scope alone | Specialized embedded field unless all Work Relationship threshold conditions are satisfied |
| Event root `module_id + class_id + work_id` | Event schema and ADRs | Owning Event | Retain | Inherited scope for local references |
| Canonical Work Relationship ownership | ADR 0004 and Issue #11 | Source-owned relationship stored beneath one Portia work root | Make storage ownership and semantic source identical; prohibit third-party ownership | Containing Portia work must equal `source`; no separate owner field |
| Work Relationship direction and reverse semantics | ADR 0004 and Issue #11 | One canonical source-to-target assertion with derived target-side wording | Persist only the directed type; prohibit per-record inverse fields and initial symmetric types | Controlled directional `relationship_type`; reverse wording remains derived |
| Initial Work Relationship vocabulary | ADR 0004 and Issues #11, #18, and #19 | Explicit contextual association between a source Portia work and a target Event | Begin with one narrow noncausal type; defer domain-specific relationship types | Sole initial type `draws_context_from` with controlled endpoint matrix |
| Event `instructional_context.external_refs` | Event schema | Complete module-qualified record reference | Retain instructional-context semantics; replace provisional flat shape | `module_work_record_ref` composed from Core `ModuleWorkRef` and `ModuleRecordRef` |
| Event `supersedes` | Event schema and ADR 0005 | Cross-work Portia Event | Retain supersession semantics; reconcile serialized identity | `portia_work_ref` supplied directly by the `supersedes` field |
| Future Support Process child-record targets | Issue #11 and future Issue #18 contracts | Support Process-level or Support Process Participant-level application | Introduce shared target family without finalizing participant roles or Support models | `support_process_target_ref` |
| Participant roster-student subject | Participant schema and ADR 0005 | Core roster identity | Retain | `roster_student_ref` plus snapshot |
| Participant Actor subject | Participant schema and ADR 0005 | Workspace Actor identity | Retain semantics; reconcile serialized shape | `actor_ref` plus sibling snapshot |
| Descriptive-person subject | Participant schema | Event-local non-durable description | Retain specialized | Not a durable reference |
| Unknown-person subject | Participant schema | Event-local unresolved identity | Retain specialized | Not a durable reference |
| Participant `supersedes` | Participant schema and ADR 0005 | Same Event | Retain relationship semantics; reconcile serialized identity | Reason-bearing wrapper around `local_record_ref` |
| Role `participant_id` | Role schema and ADR 0006 | One Event Participant in the same Event | Retain one-participant semantics; replace direct ID field | Required `target` using the singular Event Participant branch of `portia_target_ref` |
| Role Account basis | Role schema and ADR 0006 | Same Event | Retain basis semantics; reconcile serialized identity | `account_ref` wrapper around `local_record_ref` |
| Role Observation basis | Role schema and ADR 0006 | Same Event | Retain basis semantics; reconcile serialized identity | `observation_ref` wrapper around `local_record_ref` |
| Role paper basis | Role schema and ADR 0006 | Same Event/PDS2 capture context | Retain specialized | Provenance/basis, not generic record relationship |
| Role `supersedes` | Role schema and ADR 0006 | Same Event | Retain relationship semantics; reconcile serialized identity | Reason-bearing wrapper around `local_record_ref` |
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

The Event schema currently defines a flat external reference:

```
{
  "module_id": "quillan",
  "class_id": "eng10_p2_2026",
  "work_id": "assignment_work_001",
  "record_kind": "assignment",
  "record_id": "assignment_001"
}
```

The schema describes this as an initial module-qualified instructional-reference shape.

#### Meaning

The reference identifies a canonical record owned by another Paper Data Suite module and connects that record to an Event’s instructional context.

The originating module remains authoritative for:

* the work;
* the record;
* the record kind;
* the record contract;
* the record lifecycle;
* and the educational meaning of the referenced data.

Portia owns only the meaning of including that reference within the Event’s instructional context.

The reference does not:

* transfer ownership to Portia;
* copy the sibling record into Portia;
* authorize Portia to mutate the sibling record;
* create a Score or Grade;
* create an Academic Work Registration;
* or establish that the referenced information affected an academic result.

#### Decision

Portia will replace the provisional flat shape with the shared, composed:

```
module_work_record_ref
```

contract.

The reconciled conceptual form is:

```
{
  "work_ref": {
    "module_id": "quillan",
    "class_id": "eng10_p2_2026",
    "work_id": "assignment_work_001"
  },
  "record_ref": {
    "module_id": "quillan",
    "record_kind": "assignment",
    "record_id": "assignment_001",
    "contract_version": "1"
  }
}
```

The `work_ref` conforms to Core’s exact `ModuleWorkRef` contract.

The `record_ref` conforms to Core’s exact `ModuleRecordRef` contract.

#### Module agreement

The following values must match exactly:

```
work_ref.module_id
record_ref.module_id
```

A mismatch is invalid.

Portia must not:

* select one module ID as authoritative over the other;
* infer the intended module from `record_kind`;
* rewrite either module ID silently;
* or search several modules for a matching record.

The duplicated module ID is intentional because each nested object remains an exact Core-defined value.

#### Module-neutral scope

The shared `module_work_record_ref` contract is module-neutral.

It can structurally identify a record owned by any Paper Data Suite producer, including Portia.

Usage is nevertheless context-sensitive.

Within ordinary Portia-native domain records:

* Portia-owned same-work records use `local_record_ref`;
* Portia-owned cross-work records use `portia_work_record_ref`;
* and records owned by another PDS module use `module_work_record_ref`.

At a suite-neutral boundary, such as:

* Core publication;
* manifest provenance;
* registry integration;
* cross-module interchange;
* or another module-neutral contract,

the Core-qualified work-and-record pair may also identify a Portia-owned record.

That suite-neutral use does not replace Portia’s more expressive native reference contracts inside Portia-owned domain records.

#### Contract version

The nested `record_ref` always contains the:

```
contract_version
```

key.

Its value is either:

```
a supported nonempty Core-safe string
null
```

The exact meaning and compatibility of the version remain governed by the originating module’s public contract.

Portia must not interpret `null` as:

* use the latest available record;
* use any compatible contract;
* ignore version compatibility;
* or guess the target schema.

The final suite-wide rules for creating new null-version references and preserving historical null-version references remain part of the consolidated contract-version decision.

#### No sibling work-kind metadata

The shared reference must not add:

```
work_kind
work_contract_version
title
status
filesystem_path
display_snapshot
```

Portia does not own another module’s work-kind vocabulary or work-contract model.

A consuming Portia field may impose additional application-level eligibility rules, but those rules do not become fields in the shared Core-qualified reference.

#### Resolution

Structural validity establishes only that the two nested Core values have the accepted shape.

Application validation must:

1. validate `work_ref` as a Core `ModuleWorkRef`;
2. validate `record_ref` as a Core `ModuleRecordRef`;
3. confirm that both module IDs match;
4. confirm that the module is recognized by the active suite environment;
5. resolve only the exact class-owned work identified by `work_ref`;
6. use the originating module’s published contract to resolve or validate `record_ref`;
7. confirm that the record belongs to the named work;
8. confirm the record kind and ID;
9. confirm contract-version support;
10. confirm current or historical eligibility for the Event instructional-context use.

Portia must not resolve the reference by:

* inspecting an undocumented sibling-module filesystem layout;
* searching other class or work roots;
* matching a display label;
* inferring the module from a record kind;
* relying solely on an ID prefix;
* querying a derived catalog as canonical authority;
* or silently following a successor.

#### Core Publication distinction

A Core Publication Record stores the same two conceptual identity components under Core-owned field names:

```
work
source_record
```

A Core Publication Record is not required to serialize Portia’s:

```
module_work_record_ref
```

wrapper.

Portia publication integration should pass the exact Core values to Core’s publication API according to Core’s contract.

The Portia reference object remains the reusable Portia-owned representation for Portia records that need a complete module-qualified record reference.

#### Audit finding

The existing Event reference already includes the complete work scope and most of the target-record identity.

It is incomplete because it:

* omits `contract_version`;
* flattens two Core identity concepts into one Portia-specific approximation;
* and does not preserve exact Core value-object boundaries.

#### Disposition

**Retain the Event instructional-context semantics and replace the provisional flat reference with `module_work_record_ref`.**

This change does not authorize Portia to interpret, grade, republish, or mutate the referenced sibling record.

### 11.5 Event supersession reference

#### Current shape

```
{
  "class_id": "eng10_p2_2026",
  "work_id": "evt_prior"
}
```

#### Meaning

A successor Event canonically identifies one or more prior Events that it replaces.

The supersession relationship remains:

* canonical;
* forward-owned by the successor Event;
* cross-class capable;
* provenance-preserving;
* and governed by Event lifecycle and coordinated persistence rules.

The prior Event does not store an independently editable reverse supersession reference.

#### Decision

Each entry in the Event’s `supersedes` array will use the complete shared `portia_work_ref` contract.

The reconciled conceptual form is:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_prior",
  "work_kind": "event",
  "contract_version": "1"
}
```

The surrounding `supersedes` property supplies the relationship meaning.

No additional wrapper such as:

```
work_ref
event_ref
prior_event_ref
```

is required inside the array.

#### Identity

The referenced Event’s canonical work identity is:

```
module_id + class_id + work_id
```

The additional:

```
work_kind
contract_version
```

fields identify the target Portia work contract expected by the reference.

For Event supersession:

```
module_id
```

must equal:

```
portia
```

and:

```
work_kind
```

must equal:

```
event
```

#### Cross-class supersession

The referenced Event’s `class_id` may differ from the successor Event’s owning `class_id`.

This permits provenance-preserving corrections in which a replacement Event must be owned by a different class or instructional context.

The reference does not:

* relocate the prior Event;
* duplicate it beneath the successor’s class;
* alter its original ownership;
* or create an editable reverse reference.

#### Contract version

The `contract_version` key is required.

For an Event governed by the accepted initial Event work contract, the value is:

```
"1"
```

A value of `null` is permitted only when the referenced work kind does not yet expose an accepted public work-contract version.

Because the Event work contract already has an accepted version, newly created Event supersession references should not use `null`.

#### Resolution

Structural validity establishes only that the reference has the accepted shape.

Application validation must confirm that:

* the referenced Core class exists or remains historically recognizable;
* the canonical work root exists;
* the target manifest identifies `module_id = portia`;
* the target manifest identifies `work_kind = event`;
* the target `class_id` and `work_id` agree with the reference and canonical path;
* the target supports the stated contract version;
* the target is not the successor Event itself;
* the supersession graph does not contain an invalid cycle;
* and the lifecycle operation is valid.

Portia must not resolve the reference by:

* searching all classes for a matching `work_id`;
* relying only on the `evt_` prefix;
* matching an Event summary;
* consulting a derived reverse index as authority;
* or silently following another successor.

#### Audit finding

The current `{ class_id, work_id }` reference identifies the correct class-owned Event but omits:

```
module_id
work_kind
contract_version
```

The complete Portia Work Reference:

* preserves Core’s module-qualified work identity;
* makes the expected Event contract explicit;
* supports cross-class references without searching;
* and provides consistent work-reference equality and diagnostics.

#### Disposition

**Retain the specialized Event-supersession semantics and reconcile each target identity through `portia_work_ref`.**

Do not replace Event supersession with a generic Work Relationship record.

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

The current Event Participant schema stores Actor identity directly in the discriminated subject:

```json
{
  "kind": "actor",
  "actor_id": "actr_example",
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

Earlier identity-and-storage examples instead use a nested reference:

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

#### Meaning

The Actor ID identifies one reusable non-roster person in Portia’s teacher-workspace Actor Directory.

The historical display snapshot preserves the display value associated with this particular use of the Actor reference.

The Actor reference does not define the person’s role in every Event, Account, Communication, Response, Support, or Follow-Up.

Work-specific relationships remain properties of the containing domain record.

#### Decision

Portia will use a reusable, identity-only:

```text
actor_ref
```

object.

The exact reference shape is:

```json
{
  "actor_id": "actr_example"
}
```

An Event Participant Actor subject will therefore use:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

The reference and snapshot remain separate.

#### Audit finding

The current Event Participant schema’s direct:

```text
actor_id
```

field represents the correct identity but does not provide the reusable Actor Reference value object required by later Portia record families.

Accounts, Observations, Communications, Responses, Supports, Determinations, and Follow-Ups will need to refer to Actors without duplicating the complete Actor record or independently inventing Actor-reference shapes.

The nested `actor_ref` form provides that reusable identity primitive.

Because Portia has no production data, the current Event Participant serialized shape may be corrected without migration aliases or compatibility handling.

#### Identity authority

The Actor Directory in the selected teacher workspace remains authoritative for:

* Actor existence;
* current Actor data;
* Actor lifecycle;
* duplicate consolidation;
* and current display information.

The Actor Reference itself establishes only:

```text
actor_id
```

It does not establish:

* institutional identity;
* authenticated user identity;
* authorization;
* current employment or relationship;
* current Actor status;
* or eligibility for a particular workflow role.

#### Display snapshot

The historical display snapshot remains a sibling of `actor_ref`.

It is not part of Actor identity.

The snapshot must not be used to:

* locate an Actor record;
* merge Actor records;
* repair an unresolved reference;
* authorize an action;
* or infer the Actor’s current role.

The Event Participant Actor subject continues to require a display snapshot.

Other future containing records must explicitly declare whether their Actor-reference snapshot is:

```text
required
optional
prohibited
```

#### Disposition

**Retain the accepted Actor identity semantics and replace the provisional serialized placement.**

The Event Participant schema will eventually change from:

```json
{
  "kind": "actor",
  "actor_id": "actr_example",
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

to:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "display_snapshot": {
    "display_name": "Recorded display name"
  }
}
```

The reusable `actor_ref` contract is defined in Section 13.2.

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

```
{
  "participant_id": "ep_prior",
  "reason": "identity_resolved"
}
```

Optional reason detail is permitted under controlled conditions.

#### Meaning

A successor Event Participant identifies one prior Event Participant in the same Event and records why the prior participant is being replaced.

The supersession relationship remains:

* canonical;
* forward-owned by the successor;
* same-Event only;
* reason-bearing;
* and governed by participant lifecycle rules.

#### Decision

The relationship semantics remain specialized, but the target identity will use the shared `local_record_ref` contract.

The reconciled conceptual form is:

```
{
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_prior",
    "contract_version": "1"
  },
  "reason": "identity_resolved"
}
```

Optional controlled `detail` remains permitted where required by the selected reason.

The nested `record_ref` inherits:

```
module_id
class_id
work_id
```

from the successor Event Participant.

It must not repeat Event or work scope.

#### Audit finding

The existing `participant_id` identifies the correct same-Event target but uses a record-specific identity shape.

The shared Local Record Reference provides:

* an explicit target record kind;
* a target public-contract version;
* consistent reference equality;
* and reuse across later Portia records.

The controlled reason remains outside `record_ref` because it describes the supersession relationship rather than the referenced participant.

#### Disposition

**Retain the specialized supersession relationship and reconcile its target identity through `local_record_ref`.**

Do not replace participant supersession with a generic Work Relationship record.

### 11.11 Role participant target

#### Current shape

The Event Participant Role currently identifies its participant through:

```
"participant_id": "ep_example"
```

#### Meaning

One Event Participant Role applies to exactly one Event Participant in the same Event.

The target is the Event Participant record—not the underlying:

* roster student;
* Portia Actor;
* descriptive person;
* unidentified person;
* or participant subject snapshot.

This distinction preserves the difference between:

```
the person
```

and:

```
the person’s participation in this Event
```

A Role assertion must not silently become a general assertion about the person outside the Event context.

#### Decision

The Role’s direct `participant_id` field will be replaced by a required:

```
target
```

property using the singular Event Participant branch of the shared `portia_target_ref` contract.

The reconciled conceptual form is:

```
{
  "target": {
    "kind": "event_participant",
    "record_ref": {
      "record_kind": "event_participant",
      "record_id": "ep_example",
      "contract_version": "1"
    }
  }
}
```

The nested `record_ref` conforms to the accepted `local_record_ref` contract.

The Role supplies the same-Event work scope through its own:

```
module_id
class_id
work_id
```

#### Fixed cardinality

An Event Participant Role permits exactly one target.

The Role schema must permit only:

```
kind = event_participant
```

It must reject:

```
kind = event
kind = event_participants
```

One Role must not apply to several participants.

When several participants require comparable Role assertions, each participant receives a separate canonical Role record.

This preserves independent:

* identity;
* assertion basis;
* lifecycle;
* correction history;
* provenance;
* and supersession.

#### Target versus subject

The target must not embed:

```
roster_student_ref
actor_ref
display_snapshot
subject
participant record
student record
Actor record
```

The referenced Event Participant remains authoritative for its own subject identity and historical display snapshot.

The Role target identifies only the participant’s Event-local canonical record.

#### Target versus basis

The Role target identifies the Event Participant to whom the Role applies.

It does not identify why the Role is asserted.

The Role’s basis remains separately represented through its accepted basis contract, such as:

```
account_ref
observation_ref
paper_capture
```

Target and basis must not be inferred from one another.

#### Target versus attribution

The Role target does not identify:

* who created the Role;
* who supplied the Role assertion;
* who reviewed it;
* who observed the Event;
* or who authored an Account.

Those meanings remain governed by creation provenance, attribution, Account, Observation, and review contracts.

#### Scope

The target inherits:

```
module_id
class_id
work_id
```

from the containing Role.

The nested `record_ref` must not repeat Event or work scope.

Application validation must confirm that the referenced Event Participant belongs to the exact Event that owns the Role.

A participant in another Event is invalid even when its participant ID and reference shape are structurally valid.

#### Contract version

The required:

```
record_ref.contract_version
```

identifies the Event Participant public record contract expected by the Role.

For the accepted initial Event Participant contract, newly created Role targets should use:

```
"1"
```

Portia must not interpret an unsupported or unknown target contract silently.

#### Resolution

Structural validity establishes only that the target has the accepted singular Event Participant shape.

Application validation must confirm that the referenced participant:

* exists;
* belongs to the containing Event;
* has the expected record kind;
* agrees with its canonical path and persisted identity;
* supports the stated contract version;
* has a lifecycle state eligible for a new Role;
* and satisfies any additional Role-specific requirements.

Portia must not resolve the target by:

* matching a roster student;
* matching an Actor;
* matching a display name;
* searching other Events;
* relying solely on the `ep_` prefix;
* consulting a derived index as authority;
* or silently following participant supersession.

If the referenced participant has been superseded, the historical Role continues to identify the participant it originally targeted.

A new operation must apply the current lifecycle and correction rules explicitly rather than silently retargeting the Role.

#### Audit finding

The current `participant_id` preserves the correct one-participant semantics but uses a direct, unversioned record-specific field.

The shared target contract adds:

* explicit target meaning;
* explicit target record kind;
* target-contract versioning;
* consistent same-work record identity;
* and a reusable distinction between Event-level and participant-level application.

#### Disposition

**Retain the Role’s exact one-participant semantics and replace direct `participant_id` with the singular Event Participant branch of `portia_target_ref`.**

Do not permit Event-level or multi-participant Role targets.

### 11.12 Role Account basis

#### Current shape

```
{
  "kind": "account_ref",
  "record_id": "acct_example"
}
```

#### Meaning

The Account supports one Role assertion.

The Account must belong to the same Event as the Role.

#### Decision

The domain-specific `account_ref` wrapper remains, but its target identity will use the shared Local Record Reference.

The reconciled conceptual form is:

```
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": null
  }
}
```

Until the public Account record contract is accepted, `contract_version` may be `null`.

After the Account contract defines its initial public version, newly created references should identify that supported version, such as:

```
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": "1"
  }
}
```

#### Scope

The nested reference inherits:

```
module_id
class_id
work_id
```

from the containing Role.

It must not repeat:

```
module_id
class_id
work_id
work_kind
event_id
```

Application validation confirms that the target:

* exists;
* is an Account;
* belongs to the same Event;
* uses a supported contract version;
* has a lifecycle state eligible for the Role’s intended use;
* and satisfies any applicable attribution requirement.

#### Audit finding

The outer:

```
kind = account_ref
```

identifies the Role-basis variant and its domain meaning.

The nested:

```
record_kind = account
```

identifies the referenced canonical record contract.

That apparent repetition is intentional.

The basis wrapper and the target reference perform different functions.

#### Disposition

**Retain the specialized Account-basis semantics and reconcile its target identity through `local_record_ref`.**

The basis remains embedded in the Role.

It must not become a generic Work Relationship record.

### 11.13 Role Observation basis

#### Current shape

```
{
  "kind": "observation_ref",
  "record_id": "obs_example"
}
```

#### Meaning

The Observation supports one Role assertion.

The Observation must belong to the same Event as the Role.

#### Decision

The domain-specific `observation_ref` wrapper remains, but its target identity will use the shared Local Record Reference.

The reconciled conceptual form is:

```
{
  "kind": "observation_ref",
  "record_ref": {
    "record_kind": "observation",
    "record_id": "obs_example",
    "contract_version": null
  }
}
```

Until the public Observation record contract is accepted, `contract_version` may be `null`.

After the Observation contract defines its initial public version, newly created references should identify that supported version, such as:

```
{
  "kind": "observation_ref",
  "record_ref": {
    "record_kind": "observation",
    "record_id": "obs_example",
    "contract_version": "1"
  }
}
```

#### Scope

The nested reference inherits:

```
module_id
class_id
work_id
```

from the containing Role.

It must not repeat:

```
module_id
class_id
work_id
work_kind
event_id
```

Application validation confirms that the target:

* exists;
* is an Observation;
* belongs to the same Event;
* uses a supported contract version;
* and has a lifecycle state eligible for the Role’s intended use.

#### Audit finding

The outer `kind` identifies the Role-basis variant.

The nested `record_kind` identifies the canonical target contract.

The two fields are not interchangeable.

#### Disposition

**Retain the specialized Observation-basis semantics and reconcile its target identity through `local_record_ref`.**

The basis remains embedded in the Role and does not become a generic Work Relationship record.

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

```
{
  "role_id": "epr_prior",
  "reason": "basis_corrected"
}
```

Optional nested detail is permitted where required.

#### Meaning

A successor Role replaces one prior Role in the same Event.

One successor may replace several prior Roles.

The supersession relationship remains:

* canonical;
* forward-owned by the successor;
* same-Event only;
* reason-bearing;
* effective only through the accepted coordinated lifecycle operation;
* and distinct from generic navigation relationships.

#### Decision

The specialized supersession wrapper remains, but the target identity will use the shared Local Record Reference.

The reconciled conceptual form is:

```
{
  "record_ref": {
    "record_kind": "event_participant_role",
    "record_id": "epr_prior",
    "contract_version": "1"
  },
  "reason": "basis_corrected"
}
```

Optional controlled `detail` remains permitted where required by the selected reason.

The nested `record_ref` inherits:

```
module_id
class_id
work_id
```

from the successor Role.

#### Audit finding

The existing `role_id` correctly identifies a same-Event Role but uses a record-specific target shape.

The Local Record Reference adds:

* explicit target record kind;
* explicit target contract version;
* shared reference equality;
* and consistent structural validation.

The controlled reason remains outside `record_ref` because it describes the correction relationship.

#### Disposition

**Retain the specialized Role-supersession relationship and reconcile its target identity through `local_record_ref`.**

Do not create a duplicate Work Relationship record for the same supersession.

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

The serialized envelope is provisional.

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

The relationship vocabulary is not finalized.

#### Disposition

**Replace provisional envelope.**

Retain the accepted ownership and direction rules.

Define the canonical Work Relationship schema later in this issue.

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

The identity examples should eventually be:

* updated to current canonical shapes;
* reduced to conceptual fragments that cannot be mistaken for schemas;
* or clearly labeled as superseded by the later domain-model examples.

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

#### Decision

Portia will represent a Core roster student through a reusable, identity-only **Roster Student Reference**.

The serialized property name is:

```text
roster_student_ref
```

The exact conceptual shape is:

```json
{
  "class_id": "eng10_p2_2026",
  "student_id": "stu_1001"
}
```

The reference contains only the durable Core roster identity:

```text
class_id + student_id
```

A bare `student_id` is not a valid Portia roster-student reference.

#### Identity Authority

Core remains authoritative for:

* the source class;
* the source roster;
* the student identifier within that roster;
* identifier validation;
* and current roster resolution.

Portia preserves the reference but does not create a competing workspace-wide student identity.

The source `class_id` may differ from the containing Event’s owning class.

For example, an Event owned by:

```text
eng10_p2_2026
```

may legitimately contain:

```json
{
  "roster_student_ref": {
    "class_id": "art1_p5_2026",
    "student_id": "stu_2088"
  }
}
```

when the participant belongs to the teacher’s Art Period 5 roster.

The cross-class reference does not:

* change Event ownership;
* copy the Event beneath the source roster class;
* merge the student with another roster entry;
* or create a workspace-wide student record.

#### Required Fields

Every Roster Student Reference requires exactly:

```text
class_id
student_id
```

Both values:

* are strings;
* are preserved exactly;
* may contain leading zeros;
* must satisfy the applicable Core identifier contract;
* and must not be silently normalized.

Unknown properties are prohibited.

#### Prohibited Fields

The Roster Student Reference must not contain:

```text
kind
display_snapshot
display_name
first_name
last_name
preferred_name
period
email
school_year
module_id
work_id
contract_version
```

Those values are not part of roster-student identity.

#### Equality

Two Roster Student References are equal exactly when both contain the same:

```text
class_id
student_id
```

Display values, current roster metadata, and the containing Portia work do not participate in identity equality.

Portia must not treat two references as equal merely because they have matching:

* student IDs in different rosters;
* names;
* email addresses;
* periods;
* or other display metadata.

Portia must not treat two references as necessarily different real-world people merely because their identifiers differ.

The reference preserves Core source identity rather than asserting broader person identity.

#### Display Snapshot

A historical display snapshot is a sibling of the Roster Student Reference, not part of it.

For example:

```json
{
  "kind": "roster_student",
  "roster_student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Avery Chen"
  }
}
```

The snapshot:

* preserves historical readability;
* does not participate in identity;
* does not authorize lookup or access;
* does not repair an unresolved reference;
* and must not be used to merge roster entries.

The containing record contract determines whether `display_snapshot` is:

```text
required
optional
prohibited
```

For an Event Participant whose subject kind is `roster_student`, the display snapshot remains required.

Other future records do not inherit that requirement merely because they contain a Roster Student Reference.

#### Resolution

Structural validity establishes only that the reference has the correct shape.

Application validation determines whether:

* the referenced Core class exists;
* a valid roster exists for that class;
* the student currently exists in that roster;
* and the reference is eligible for the intended operation.

Portia must distinguish:

```text
structurally invalid reference
structurally valid but unresolved reference
historically valid reference whose current roster entry is unavailable
currently resolved reference
```

A missing current roster entry does not automatically invalidate an otherwise valid historical Portia record.

Portia must not resolve or repair an unavailable reference by:

* searching other rosters for the same `student_id`;
* matching a display name;
* matching an email address;
* choosing the first similar roster entry;
* or substituting a current roster record silently.

Any future identity correction must use an explicit reviewed correction or supersession workflow.

#### Schema Direction

The shared reference schema should define a reusable closed object for `roster_student_ref`.

The schema should enforce:

* required `class_id`;
* required `student_id`;
* string values;
* no unknown properties;
* and the accepted structural identifier rules.

Core remains authoritative for exact identifier validity, class existence, roster existence, and student resolution.

The Event Participant schema should eventually rename its current nested:

```text
student_ref
```

field to:

```text
roster_student_ref
```

so the persisted contract uses the shared and scope-explicit name.

Because Portia has no production data, this development-stage correction does not require runtime migration or compatibility aliases.

#### Invariants

1. A Roster Student Reference contains exactly one `class_id` and one `student_id`.
2. A bare `student_id` is invalid.
3. The reference’s class is the authoritative source-roster class.
4. The source-roster class may differ from the containing Event’s owning class.
5. Names and other display values are not identity.
6. Display snapshots are stored outside the identity object.
7. Display snapshots do not participate in equality.
8. Matching IDs or names across rosters do not establish one person.
9. Portia does not create workspace-wide student identity through this reference.
10. Structural validity does not prove current target existence.
11. Historical records are not silently rewritten after roster changes.
12. Unresolved references are reported rather than repaired through inference.

### 13.2 `actor_ref`

#### Decision

Portia will represent a recurring non-roster person through a reusable, identity-only **Actor Reference**.

The serialized property name is:

```text
actor_ref
```

The exact conceptual shape is:

```json
{
  "actor_id": "actr_counselor_001"
}
```

The reference contains only the durable Portia Actor identity:

```text
actor_id
```

#### Identity authority

The Portia Actor Directory in the selected teacher workspace is authoritative for the referenced Actor.

Its canonical location is:

```text
<PDS workspace>/portia/actors/<actor_id>.json
```

The Actor Directory is:

* Portia-owned;
* workspace-scoped;
* local to one teacher workspace;
* and limited to reusable non-roster people.

It is not:

* a school directory;
* a district directory;
* an employee directory;
* an authenticated user directory;
* an institutional person registry;
* or an authorization service.

An Actor Reference must therefore not be interpreted as institutionally authoritative identity.

#### Required fields

Every Actor Reference requires exactly:

```text
actor_id
```

The value:

* is a string;
* uses the Portia Actor identifier form;
* must begin with `actr_`;
* is opaque;
* must not encode a person’s name, title, relationship, or other sensitive semantics;
* and must not be silently normalized.

Unknown properties are prohibited.

#### Prohibited fields

The Actor Reference must not contain:

```text
kind
display_snapshot
display_name
actor_type
role_labels
title
status
email
telephone
address
class_id
student_id
work_id
module_id
contract_version
```

Those values are not part of Actor identity.

Current Actor metadata remains in the canonical Actor record.

Work-specific relationships remain in the containing Portia domain record.

#### Equality

Two Actor References are equal exactly when they contain the same:

```text
actor_id
```

Display snapshots, names, titles, role labels, contact details, current status, and containing work do not participate in reference equality.

Portia must not treat two Actor References as equal merely because their current or recorded display information matches.

Portia must not treat two differently identified Actor records as the same person without an explicit reviewed duplicate-consolidation or correction workflow.

#### Roster-student exclusion

A Core roster student must not be represented through `actor_ref`.

Roster students use:

```text
roster_student_ref
```

with the durable identity:

```text
class_id + student_id
```

Portia must not create an Actor record merely because a roster student appears in:

* several classes;
* several Events;
* Communications;
* Support Processes;
* or later Follow-Ups.

The Actor Directory is not a workaround for Core’s roster-qualified student identity.

#### Descriptive and unknown people

A descriptive, incidental, unidentified, or withheld person does not automatically receive an Actor Reference.

Such a person may remain represented through a domain-specific descriptive or unknown-person value.

Creating an Actor and replacing the descriptive identity requires a deliberate reviewed operation.

Portia must not fabricate an Actor merely to satisfy a reference field.

#### Display snapshot

A historical display snapshot is a sibling of the Actor Reference, not part of it.

For example:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_counselor_001"
  },
  "display_snapshot": {
    "display_name": "Riley Thompson"
  }
}
```

The snapshot:

* preserves historical readability;
* does not participate in identity;
* does not establish current Actor data;
* does not authorize an action;
* and must not be used to repair an unresolved reference.

The containing record determines whether `display_snapshot` is:

```text
required
optional
prohibited
```

For an Event Participant whose subject kind is `actor`, the display snapshot remains required.

Other future records do not inherit that requirement merely because they contain an Actor Reference.

#### Work-specific roles

An Actor Reference identifies the reusable person.

It does not identify the person’s role in a particular workflow.

For example, the following remain separate record-specific relationships:

```text
Account source
Observation source
Communication sender
Communication recipient
Response provider
Support provider
Follow-Up owner
Determination authority
family contact
consulted counselor
```

Those relationships belong to the containing record and must not be inferred from:

* Actor type;
* Actor title;
* Actor role labels;
* prior Portia records;
* contact information;
* or repeated appearances.

#### Resolution

Structural validity establishes only that the reference has the accepted shape.

Application validation determines whether:

* the Actor record exists in the selected workspace;
* the Actor record has the expected type;
* the Actor lifecycle permits the intended operation;
* the Actor has been superseded;
* or the reference is available only for historical display.

Portia must distinguish:

```text
structurally invalid reference
structurally valid but unresolved reference
historically resolvable reference
resolved but not currently eligible reference
currently resolved and eligible reference
```

The exact lifecycle states and duplicate-consolidation behavior belong to Issue #14.

A missing or terminal Actor must not cause Portia to:

* search another workspace;
* substitute a matching name;
* create a replacement Actor automatically;
* rewrite historical references;
* or delete the containing canonical record.

#### Schema direction

The shared reference schema should define a reusable closed object for `actor_ref`.

The schema should enforce:

* required `actor_id`;
* string type;
* the accepted `actr_` identifier prefix;
* and no unknown properties.

Application validation remains responsible for:

* selected-workspace containment;
* Actor existence;
* Actor-record validation;
* lifecycle eligibility;
* duplicate consolidation;
* and historical versus current resolution.

The Event Participant schema should eventually replace its direct:

```text
actor_id
```

property with:

```text
actor_ref
```

using the shared reference definition.

Because Portia has no production data, this correction does not require runtime migration, aliases, or dual accepted shapes.

#### Invariants

1. An Actor Reference contains exactly one `actor_id`.
2. The Actor ID is Portia-owned and workspace-scoped.
3. The reference does not claim institutional identity.
4. Display information is not identity.
5. Display snapshots are stored outside the identity object.
6. Display snapshots do not participate in equality.
7. Actor metadata is not copied into the reference.
8. Work-specific roles are not stored in the reference.
9. Roster students are never represented through `actor_ref`.
10. Descriptive and unknown people are not silently promoted to Actors.
11. Structural validity does not prove Actor existence.
12. Current Actor changes do not rewrite historical references.
13. Unresolved references are reported rather than repaired through inference.
14. Actor lifecycle eligibility is determined by application logic and the Actor Directory contract.


### 13.3 `local_record_ref`

#### Decision

Portia will use a reusable, typed, version-aware **Local Record Reference** when one canonical Portia record refers to another canonical record inside the same owning Portia work root.

The serialized nested property name is:

```text
record_ref
```

The exact conceptual shape is:

```json
{
  "record_kind": "account",
  "record_id": "acct_example",
  "contract_version": "1"
}
```

When the target does not yet expose an accepted public record-contract version, the required version key contains `null`:

```json
{
  "record_kind": "account",
  "record_id": "acct_example",
  "contract_version": null
}
```

#### Inherited scope

A Local Record Reference is relative to exactly one unambiguous Portia work-scope provider.

In ordinary same-work use, the scope provider is the containing canonical Portia record. The containing record supplies:

```
module_id
class_id
work_id
```

For example, a Role’s Account-basis reference receives its work scope from the containing Role.

Inside a `portia_work_record_ref`, the scope provider is instead the sibling:

```
work_ref
```

The sibling `work_ref` supplies:

```
module_id
class_id
work_id
```

for the nested `record_ref`.

The Local Record Reference itself must not contain:

```
module_id
class_id
work_id
work_kind
event_id
support_process_id
filesystem_path
display_snapshot
```

The consuming schema must identify exactly one scope provider structurally.

A Local Record Reference is invalid when:

* no work-scope provider exists;
* more than one possible provider exists;
* the containing contract leaves the provider ambiguous;
* or the reference attempts to override its provider’s scope.

A reference to a record in a different Portia work root must use a complete:

```
portia_work_record_ref
```

rather than an ordinary same-work Local Record Reference.

#### Required fields

Every Local Record Reference contains exactly:

```text
record_kind
record_id
contract_version
```

Unknown properties are prohibited.

#### `record_kind`

`record_kind`:

* is required;
* is a lowercase string;
* identifies the expected Portia target-record contract;
* must use a controlled Portia record-kind value;
* and must not be inferred solely from an ID prefix or filesystem directory.

Representative record kinds include:

```text
event_participant
event_participant_role
account
observation
response
communication
follow_up
outcome
```

Later domain issues may add controlled Portia record kinds without changing the fundamental Local Record Reference shape.

The presence of a record kind in the shared reference vocabulary does not imply that every consuming record may refer to that kind.

#### `record_id`

`record_id`:

* is required;
* is a string;
* is the durable opaque identifier of the target canonical record;
* must satisfy the identifier contract associated with `record_kind`;
* and must not encode a person’s name, behavior meaning, allegation, status, or other sensitive semantics.

A record ID prefix may support structural validation and diagnostics.

It does not replace `record_kind`.

#### `contract_version`

The `contract_version` key is required.

Its value is either:

```text
a supported nonempty safe string
null
```

A string such as:

```text
"1"
```

identifies the public target-record contract expected by the reference.

`null` means:

> The reference deliberately does not identify a stable public target-contract version because no such version has yet been accepted for that target kind.

`null` must not mean:

* use the newest installed package;
* guess the current schema;
* ignore compatibility;
* or interpret the target through whichever model is available.

The following concepts remain distinct:

```text
containing record schema_version
target record contract_version
installed package version
shared reference schema version
```

The issue will later decide whether newly created references may continue using `null` after the target record kind has an accepted public contract.

#### Identity

Within the inherited work root, the canonical target-record identity is:

```text
record_kind + record_id
```

The complete target identity is therefore:

```text
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_kind
+ record_id
```

The contract version does not create a different canonical target record.

It identifies the target-record contract expected by this use of the reference.

#### Equality

Two Local Record Reference values are equal when all of the following match:

```text
inherited module_id
inherited class_id
inherited work_id
record_kind
record_id
contract_version
```

Two references may identify the same canonical target record while expecting different target contract versions.

Those references are not equal as reference values.

Display labels and other snapshots never participate in Local Record Reference equality.

#### Specialized wrappers

A Local Record Reference may appear inside a domain-specific wrapper.

The wrapper defines the relationship meaning.

The nested `record_ref` defines the canonical target identity.

For Account basis:

```json
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": "1"
  }
}
```

For Observation basis:

```json
{
  "kind": "observation_ref",
  "record_ref": {
    "record_kind": "observation",
    "record_id": "obs_example",
    "contract_version": "1"
  }
}
```

For Event Participant supersession:

```json
{
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_prior",
    "contract_version": "1"
  },
  "reason": "identity_resolved"
}
```

For Event Participant Role supersession:

```json
{
  "record_ref": {
    "record_kind": "event_participant_role",
    "record_id": "epr_prior",
    "contract_version": "1"
  },
  "reason": "basis_corrected"
}
```

The nested property remains named:

```text
record_ref
```

Specialized property names such as:

```text
participant_ref
role_ref
account_record_ref
```

must not be introduced merely to rename the same Local Record Reference contract.

The outer field, array, or discriminator already supplies the relationship context.

#### Reference versus target

A Local Record Reference identifies a canonical record.

It does not, by itself, state whether the referenced record is:

* the target of an action;
* the source of an Account;
* the observer;
* evidence;
* basis;
* a predecessor;
* a provider;
* or a recipient.

The containing domain field or wrapper provides that meaning.

Decision 7 reconciles the Role’s former direct `participant_id` through a required `target` value whose singular Event Participant branch contains a `local_record_ref`. This does not make target and reference synonymous: the outer target wrapper states what the Role applies to, while the nested record reference identifies the canonical Event Participant.

#### Resolution

Structural validity establishes only that the Local Record Reference has the accepted shape.

Application validation determines whether the referenced target:

* exists beneath the inherited work root;
* has the expected `record_kind`;
* has a record ID agreeing with its canonical path and stored identity;
* supports the stated `contract_version`;
* has a lifecycle state eligible for the intended use;
* and satisfies the containing record’s domain-specific requirements.

Portia must distinguish:

```text
structurally invalid reference
structurally valid but unresolved reference
resolved to the wrong record kind
resolved under an unsupported target contract
historically resolvable target
currently resolved but ineligible target
currently resolved and eligible target
```

Portia must not resolve a Local Record Reference by:

* searching other work roots;
* matching a display label;
* selecting the first matching record ID;
* inferring a record kind from a filename alone;
* silently following a successor;
* or consulting a derived reverse index as authority.

#### Missing and historical targets

A missing current target does not automatically invalidate every historical record containing the reference.

The consuming contract determines whether it requires:

```text
current eligible target
historically valid target
target existence only
best-effort historical display
```

Portia must report unresolved or unsupported references.

It must not silently rewrite them.

#### Schema direction

The shared reference schema should define a closed reusable Local Record Reference object.

JSON Schema should enforce:

* required `record_kind`;
* lowercase controlled structural form;
* required `record_id`;
* required `contract_version`;
* string-or-null contract-version type;
* no unknown properties;
* and prohibition of repeated work-scope fields.

Application validation remains responsible for:

* target existence;
* inherited-scope agreement;
* exact target record kind;
* record-kind and ID-prefix compatibility;
* target contract support;
* lifecycle eligibility;
* and domain-specific use requirements.

#### Existing-contract consequences

The following current serialized shapes will eventually be reconciled:

```text
participant supersedes[].participant_id
Role basis[].record_id for account_ref
Role basis[].record_id for observation_ref
Role supersedes[].role_id
```

They will use nested:

```text
record_ref
```

objects while retaining their specialized relationship or basis semantics.

The Role’s top-level:

```text
participant_id
```

does not change at this stage because it is a target field rather than a general local-record reference.

#### Invariants

1. A Local Record Reference identifies one canonical record inside the containing record’s own work root.
2. It inherits `module_id`, `class_id`, and `work_id`.
3. It never repeats inherited work scope.
4. It contains exactly `record_kind`, `record_id`, and `contract_version`.
5. `record_kind` is explicit and is not inferred solely from the ID.
6. `record_id` is opaque and durable.
7. `contract_version` is always present.
8. `contract_version` is a supported string or deliberate `null`.
9. A Local Record Reference cannot identify a record in another work root.
10. Display snapshots do not belong inside the reference.
11. Specialized wrappers preserve domain meaning outside `record_ref`.
12. The nested property name is consistently `record_ref`.
13. Structural validity does not prove target existence or eligibility.
14. Unresolved references are reported rather than repaired through inference.
15. Reference resolution never searches other work roots for a matching local ID.

### 13.4 `portia_work_ref`

#### Decision

Portia will use a complete, typed, version-aware **Portia Work Reference** whenever a canonical Portia record refers to a Portia Event or Support Process outside the containing record’s own work root.

The exact conceptual shape is:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_example",
  "work_kind": "event",
  "contract_version": "1"
}
```

When the reference appears inside a domain-specific wrapper, the reusable serialized property name is:

```
work_ref
```

A wrapper is unnecessary when the containing field already establishes the relationship meaning.

For example, entries in an Event’s `supersedes` array and Work Relationship `source` and `target` fields may use the Portia Work Reference directly.

#### Required fields

Every Portia Work Reference contains exactly:

```
module_id
class_id
work_id
work_kind
contract_version
```

Unknown properties are prohibited.

#### `module_id`

`module_id`:

* is required;
* must equal `portia`;
* preserves Core’s module-qualified work identity;
* and must not be inferred solely from the property name or containing Portia record.

Retaining `module_id` makes the reference self-describing and compatible with Core’s `ModuleWorkRef` identity.

#### `class_id`

`class_id`:

* is required;
* identifies the Core class that owns the canonical Portia work root;
* may differ from the class owning the referring record;
* and must satisfy the applicable Core identifier contract.

A cross-class reference does not change the target work’s ownership.

#### `work_id`

`work_id`:

* is required;
* identifies the canonical Portia work item beneath the named owning class;
* is durable and opaque;
* must satisfy the ID contract associated with the stated `work_kind`;
* and must not be resolved by searching other classes.

The initial Portia work-ID families are:

```
evt_<opaque-id>
sup_<opaque-id>
```

The prefix supports structural validation and diagnostics.

It does not replace the explicit `work_kind`.

#### `work_kind`

`work_kind` is required.

The initial controlled values are:

```
event
support_process
```

Later Portia work kinds may be added deliberately without changing the fundamental Portia Work Reference shape.

`work_kind` does not participate in Core’s canonical module-work identity.

It identifies the Portia target-work contract expected by this reference.

The stated work kind and the target manifest must agree.

#### `contract_version`

The `contract_version` key is required.

Its value is either:

```
a supported nonempty version string
null
```

A value such as:

```
"1"
```

identifies the public Portia work contract expected by the reference.

`null` means:

> The reference deliberately does not identify a stable public target-work contract version because no such version has yet been accepted for that work kind.

`null` must not mean:

* use the newest available contract;
* guess the target schema;
* ignore compatibility;
* or interpret the target through whichever package version is installed.

New references to Events should use:

```
"1"
```

because the initial Event work contract is accepted.

References to Support Processes may use `null` only until the initial Support Process work contract is accepted.

#### Canonical identity

The canonical target-work identity is:

```
module_id + class_id + work_id
```

Neither `work_kind` nor `contract_version` creates a separate canonical work item.

They identify the target contract expected by this use of the reference.

#### Reference equality

Two Portia Work Reference values are equal when all of the following match:

```
module_id
class_id
work_id
work_kind
contract_version
```

Two references may identify the same canonical work item while expecting different target-contract versions.

Those references identify the same canonical work but are not equal as complete reference values.

#### Prohibited fields

A Portia Work Reference must not contain:

```
school_year
status
summary
title
record_kind
record_id
filesystem_path
display_snapshot
student_id
actor_id
```

Those values are not part of the Portia work-reference identity.

A bounded historical work-label snapshot, if later justified, must be stored outside the reference.

#### Use without a wrapper

A containing field may use Portia Work Reference values directly when the field itself supplies complete relationship meaning.

Examples include:

```
Event.supersedes[]
WorkRelationship.source
WorkRelationship.target
```

An Event supersession entry therefore has this direct form:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_prior",
  "work_kind": "event",
  "contract_version": "1"
}
```

#### Use inside a wrapper

A containing contract may use:

```
work_ref
```

when additional relationship metadata surrounds the reference.

For example:

```
{
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  },
  "relationship_role": "review_context"
}
```

The wrapper supplies domain meaning.

The nested `work_ref` supplies canonical target identity and expected contract information.

#### Work Relationship endpoints

Canonical Portia Work Relationship endpoints will use Portia Work Reference values.

Conceptually:

```
{
  "source": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "sup_example",
    "work_kind": "support_process",
    "contract_version": null
  },
  "target": {
    "module_id": "portia",
    "class_id": "eng10_p5_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  }
}
```

The final Work Relationship envelope, lifecycle, and relationship vocabulary remain separate unresolved decisions.

#### Resolution

Structural validity establishes only that the reference has the accepted shape.

Application validation determines whether:

* the named Core class exists or remains historically recognizable;
* the canonical Portia work root exists;
* the target manifest agrees with the stated module, class, and work ID;
* the target manifest has the stated work kind;
* the target supports the stated contract version;
* the target lifecycle permits the intended operation;
* and the consuming domain contract permits that target work kind.

Portia must distinguish:

```
structurally invalid reference
structurally valid but unresolved reference
resolved to the wrong module
resolved to the wrong work kind
resolved under an unsupported target contract
historically resolvable target
currently resolved but ineligible target
currently resolved and eligible target
```

Portia must not resolve a Portia Work Reference by:

* searching other class roots for the same `work_id`;
* relying only on an ID prefix;
* matching a title or summary;
* following a derived reverse index as authority;
* or silently redirecting to a successor work item.

#### Schema direction

The shared reference schema should define a closed reusable Portia Work Reference object.

JSON Schema should enforce:

* required `module_id`;
* `module_id = portia`;
* required `class_id`;
* required `work_id`;
* required controlled `work_kind`;
* required string-or-null `contract_version`;
* structural compatibility between `work_kind` and work-ID prefix where appropriate;
* and no unknown properties.

Application validation remains responsible for:

* Core class existence;
* canonical work-root existence;
* path and stored-identity agreement;
* exact work kind;
* target-contract support;
* lifecycle eligibility;
* and consuming-record restrictions.

#### Existing-contract consequences

The Event schema’s current:

```
supersedes[].class_id
supersedes[].work_id
```

shape will eventually be replaced by complete Portia Work Reference values.

The provisional Work Relationship examples will eventually use the same exact endpoint contract.

Because Portia has no production data, this development-stage correction does not require runtime migration aliases or dual accepted shapes.

#### Invariants

1. A Portia Work Reference identifies one canonical Portia work item.
2. It always contains `module_id`, `class_id`, and `work_id`.
3. `module_id` always equals `portia`.
4. The reference never inherits class or work scope from its containing record.
5. `work_kind` is explicit and is not inferred solely from the work ID.
6. `contract_version` is always present.
7. The contract version is a supported string or deliberate `null`.
8. Canonical work identity is `module_id + class_id + work_id`.
9. Work kind and contract version do not create a second canonical work item.
10. Cross-class and cross-year references do not alter target ownership.
11. Filesystem paths and display snapshots do not belong inside the reference.
12. Structural validity does not prove target existence or eligibility.
13. Resolution never searches other classes for a matching `work_id`.
14. Unresolved references are reported rather than repaired through inference.


### 13.5 `portia_work_record_ref`

#### Decision

Portia will use a composed, complete **Portia Work Record Reference** when one canonical Portia record refers to a canonical child record inside another Portia work root.

The contract composes the accepted:

```
portia_work_ref
local_record_ref
```

contracts.

The exact conceptual shape is:

```
{
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p5_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  },
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": "1"
  }
}
```

When a domain-specific wrapper is required, the reusable serialized property name is:

```
work_record_ref
```

#### Purpose

A Portia Work Record Reference identifies one canonical child record whose work scope cannot be inherited from the containing canonical record.

It provides two stages of identity:

1. `work_ref` identifies the exact target Portia work root.
2. `record_ref` identifies the exact canonical record inside that work root.

The contract must not be used merely because a complete reference appears more convenient than an inherited local reference.

When the target belongs to the containing record’s own work root and the consuming contract permits local scope inheritance, the consuming record should use:

```
local_record_ref
```

instead.

#### Required properties

Every Portia Work Record Reference contains exactly:

```
work_ref
record_ref
```

Unknown properties are prohibited.

#### `work_ref`

`work_ref` must satisfy the accepted Portia Work Reference contract.

It therefore contains exactly:

```
module_id
class_id
work_id
work_kind
contract_version
```

The `work_ref`:

* identifies the target’s canonical Portia work root;
* provides the scope for the sibling `record_ref`;
* permits cross-class and cross-year references;
* preserves the target work’s original ownership;
* and identifies the expected public target-work contract.

For every Portia Work Record Reference:

```
work_ref.module_id = portia
```

#### `record_ref`

`record_ref` must satisfy the accepted Local Record Reference structural contract.

It therefore contains exactly:

```
record_kind
record_id
contract_version
```

Within this composed contract, the sibling `work_ref` is the `record_ref`’s work-scope provider.

The nested `record_ref` must be resolved only beneath:

```
work_ref.module_id
work_ref.class_id
work_ref.work_id
```

It must not be resolved relative to the outer containing canonical record.

#### No repeated top-level identity

The Portia Work Record Reference must not repeat any of the following at its top level:

```
module_id
class_id
work_id
work_kind
record_kind
record_id
contract_version
```

Those values belong inside either:

```
work_ref
record_ref
```

The composed form prevents ambiguity between:

```
work_ref.contract_version
record_ref.contract_version
```

The first identifies the expected target-work contract.

The second identifies the expected target-record contract.

#### Work and record compatibility

The presence of a structurally valid `work_ref` and `record_ref` does not prove that the named record kind is valid beneath the named work kind.

Application validation must enforce compatibility between:

```
work_ref.work_kind
record_ref.record_kind
```

For example, a reference identifying:

```
work_kind = event
record_kind = account
```

may be valid once the Account contract is accepted beneath Events.

A reference identifying a record kind that cannot canonically exist beneath the named work kind is invalid even when both nested objects validate independently.

The shared reference contract does not make every record kind legal beneath every work kind.

#### Canonical target identity

The canonical target-record identity is:

```
work_ref.module_id
+ work_ref.class_id
+ work_ref.work_id
+ record_ref.record_kind
+ record_ref.record_id
```

The following fields do not create another canonical record:

```
work_ref.work_kind
work_ref.contract_version
record_ref.contract_version
```

They identify expected target contracts and support compatibility validation.

#### Complete reference-value equality

Two Portia Work Record Reference values are equal when every field inside both nested references matches, including:

```
work_ref.module_id
work_ref.class_id
work_ref.work_id
work_ref.work_kind
work_ref.contract_version
record_ref.record_kind
record_ref.record_id
record_ref.contract_version
```

Two references may identify the same canonical child record while expecting different work-contract or record-contract versions.

Those references identify the same canonical record but are not equal as complete reference values.

#### Contract-version behavior

Both nested `contract_version` keys are required.

`work_ref.contract_version` identifies the expected public contract for the target Event or Support Process.

`record_ref.contract_version` identifies the expected public contract for the target child record.

Either value may be `null` only when the corresponding target kind does not yet expose an accepted public contract version.

For example, before the Account contract is finalized:

```
{
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p5_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  },
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": null
  }
}
```

Because the initial Event contract is already accepted, a newly created Event work reference should use:

```
work_ref.contract_version = "1"
```

rather than `null`.

After a child-record contract receives an accepted public version, newly created references to that record kind should identify the supported version rather than use `null`.

The complete rules governing continued use of historical null-version references remain part of the consolidated contract-version decision.

#### Reference versus relationship

A Portia Work Record Reference identifies a target record.

It does not state why the target is relevant.

The containing property or domain-specific wrapper supplies relationship meaning.

For example:

```
{
  "source_account": {
    "work_record_ref": {
      "work_ref": {
        "module_id": "portia",
        "class_id": "eng10_p5_2026",
        "work_id": "evt_example",
        "work_kind": "event",
        "contract_version": "1"
      },
      "record_ref": {
        "record_kind": "account",
        "record_id": "acct_example",
        "contract_version": "1"
      }
    }
  }
}
```

The outer:

```
source_account
```

field supplies the domain meaning.

The nested Portia Work Record Reference supplies only canonical target identity and expected contract information.

A Portia Work Record Reference does not, by itself, mean:

* basis;
* evidence;
* source;
* target of an action;
* predecessor;
* provider;
* recipient;
* observer;
* or causal relationship.

#### Reference versus Work Relationship

A cross-work child-record reference does not automatically require a separate canonical Work Relationship record.

An embedded Portia Work Record Reference is appropriate when the containing record owns the complete meaning of the association.

A separate relationship record may be required only when the association needs its own:

* durable identity;
* lifecycle;
* provenance;
* correction history;
* independent status;
* or domain meaning outside the containing record.

The relationship-record threshold remains governed by the later Work Relationship decision.

#### Whole-work references

A Portia Work Record Reference must not be used when the intended target is the work root itself.

A reference to an Event or Support Process as a whole uses:

```
portia_work_ref
```

For example, Work Relationship endpoints linking a Support Process to an Event use Portia Work References, not Portia Work Record References.

#### Sibling-module exclusion

A Portia Work Record Reference may identify only Portia-owned work and records.

It must not identify records owned by:

```
core
concord
quillan
scoreform
or another PDS module
```

References to sibling-module records use:

```
module_work_record_ref
```

The originating sibling module remains authoritative for those records.

#### Display snapshots

No display snapshot belongs inside:

```
work_ref
record_ref
```

or at the top level of the Portia Work Record Reference.

A later containing record may place a bounded historical snapshot beside:

```
work_record_ref
```

only when the shared snapshot contract permits it.

The snapshot does not participate in canonical identity or complete reference-value equality.

#### Resolution order

Application validation must resolve a Portia Work Record Reference in this order:

1. validate the complete reference structure;
2. resolve the Core class named by `work_ref.class_id`;
3. locate only the Portia work root named by `work_ref`;
4. validate path and stored work identity agreement;
5. verify the target `work_kind`;
6. verify the target work-contract version;
7. locate `record_ref` only beneath the resolved target work root;
8. verify the target record kind;
9. verify path and stored record identity agreement;
10. verify the target record-contract version;
11. verify work-kind and record-kind compatibility;
12. verify target lifecycle eligibility;
13. apply the containing record’s domain-specific eligibility rules.

Failure at one stage must not cause Portia to search for a substitute elsewhere.

#### Prohibited resolution behavior

Portia must not resolve a Portia Work Record Reference by:

* searching other classes for the same `work_id`;
* searching other work roots for the same `record_id`;
* relying only on ID prefixes;
* matching a summary, label, or display snapshot;
* consulting a derived index as canonical authority;
* silently following a work successor;
* silently following a record successor;
* replacing an unresolved target with a similarly named record;
* or interpreting a Portia reference through a sibling module.

#### Resolution states

Portia must be able to distinguish:

```
structurally invalid complete reference
structurally valid but unresolved work reference
resolved work under the wrong work kind
resolved work under an unsupported work contract
resolved work but unresolved child record
resolved child record under the wrong record kind
resolved child record under an unsupported record contract
historically resolvable child record
currently resolved but ineligible child record
currently resolved and eligible child record
```

The containing record determines which resolution states remain acceptable for historical preservation and which are required for a new operation.

#### Schema direction

The shared reference schema should define a closed reusable Portia Work Record Reference object.

JSON Schema should enforce:

* exactly `work_ref` and `record_ref`;
* `work_ref` conforming to the shared Portia Work Reference definition;
* `record_ref` conforming to the shared Local Record Reference definition;
* no unknown top-level properties;
* and no duplicated top-level identity fields.

Application validation remains responsible for:

* target class existence;
* target work-root existence;
* target record existence;
* path and persisted-identity agreement;
* work-kind compatibility;
* record-kind compatibility;
* target contract support;
* lifecycle eligibility;
* and consuming-record restrictions.

#### Existing-contract consequences

No finalized active Portia schema currently exposes a general-purpose cross-work child-record reference.

The contract can therefore be introduced without migration aliases or dual accepted shapes.

Later domain issues may use `portia_work_record_ref` when they need, for example:

* a Support Process record to refer to an Account or Observation beneath an Event;
* a Follow-Up to refer to a record beneath another Portia work item;
* or a correction record to identify a canonical child record in another work root.

Those later issues must still define whether each particular relationship is permitted.

#### Invariants

1. A Portia Work Record Reference identifies one canonical child record inside one explicitly named Portia work root.
2. It contains exactly `work_ref` and `record_ref`.
3. The nested `work_ref` satisfies the complete Portia Work Reference contract.
4. The nested `record_ref` satisfies the Local Record Reference structural contract.
5. The sibling `work_ref` is the sole work-scope provider for `record_ref`.
6. The reference never inherits work scope from the outer containing record.
7. Work and record identity fields are not duplicated at the top level.
8. The two contract-version fields remain distinct.
9. The reference cannot identify a sibling-module record.
10. A reference to the work root alone uses `portia_work_ref`.
11. Same-work references use `local_record_ref` when permitted by the consuming contract.
12. Display snapshots do not belong inside the complete reference.
13. Structural validity does not prove target existence, compatibility, or eligibility.
14. Resolution occurs first at the work level and then at the record level.
15. Resolution never searches other classes or work roots for matching IDs.
16. Unresolved references are reported rather than repaired through inference.

### 13.6 `module_work_record_ref`

#### Decision

Portia will use a composed, complete, Core-qualified **Module Work Record Reference** when a Portia-owned record must identify one canonical module-owned record together with its exact class-owned work context.

The contract composes Core’s exact:

```
ModuleWorkRef
ModuleRecordRef
```

value objects.

The exact conceptual shape is:

```
{
  "work_ref": {
    "module_id": "quillan",
    "class_id": "eng10_p2_2026",
    "work_id": "assignment_work_001"
  },
  "record_ref": {
    "module_id": "quillan",
    "record_kind": "assignment",
    "record_id": "assignment_001",
    "contract_version": "1"
  }
}
```

When a domain-specific wrapper is required, the reusable serialized property name is:

```
module_work_record_ref
```

#### Purpose

A Module Work Record Reference provides complete module-qualified record identity without requiring Portia to:

* understand another module’s private storage layout;
* search the workspace for a matching record ID;
* duplicate the referenced record;
* or define a competing suite-wide record identity.

It provides two identity components:

1. `work_ref` identifies the exact class-owned module work context.
2. `record_ref` identifies the exact typed module-owned record contract.

#### Required properties

Every Module Work Record Reference contains exactly:

```
work_ref
record_ref
```

Unknown top-level properties are prohibited.

#### `work_ref`

`work_ref` must conform exactly to Core’s `ModuleWorkRef` contract.

It contains:

```
module_id
class_id
work_id
```

The `work_ref` identifies one module-owned top-level work context beneath one Core class.

The reference must not assume that the named work is:

* academic;
* graded;
* reportable;
* published;
* registered;
* or associated with an Academic Period.

Those meanings require separate contracts.

#### `record_ref`

`record_ref` must conform exactly to Core’s `ModuleRecordRef` contract.

It contains:

```
module_id
record_kind
record_id
contract_version
```

The `record_ref` identifies:

* the owning module;
* the expected record kind;
* the canonical record ID;
* and the expected public record-contract version.

The `contract_version` key is always present.

Its value is either:

```
a supported nonempty safe string
null
```

#### Module agreement

The following values must match exactly:

```
work_ref.module_id
record_ref.module_id
```

A disagreement is invalid.

The repeated module ID is intentional.

It allows both nested objects to remain exact Core-defined values rather than introducing a Portia-specific shortened form.

JSON Schema may validate each nested object independently.

Application validation must enforce equality between the two module IDs unless the selected schema technology provides a portable exact cross-property equality constraint.

Portia must not guess which module ID was intended when they differ.

#### Module-neutral identity

The Module Work Record Reference is structurally module-neutral.

It may identify a record owned by:

```
scoreform
quillan
concord
portia
another recognized PDS producer
```

The reference contract itself does not prohibit:

```
module_id = portia
```

Usage is nevertheless context-sensitive.

#### Ordinary Portia-native usage

Inside Portia-owned native domain records:

* a Portia record in the same work root should use `local_record_ref`;
* a Portia record in another Portia work root should use `portia_work_record_ref`;
* and a record owned by another PDS module should use `module_work_record_ref`.

This keeps Portia-native references expressive and preserves Portia work-kind and work-contract validation where Portia owns those semantics.

A Portia-owned record should not use the generic module-neutral reference merely to avoid the more precise Portia-native contract.

#### Suite-boundary usage

At a suite-neutral boundary, the Core-qualified work-and-record pair may identify a Portia-owned record.

Relevant suite-boundary contexts may include:

* Core Publication Records;
* Portia-owned publication manifests;
* registry integration;
* manifest provenance;
* cross-module interchange;
* import or export provenance;
* and another shared module-neutral contract.

In those contexts, Portia appears as one producer among several and must use Core’s neutral identity contracts.

The same canonical Portia record may therefore have:

```
Portia-native identity representation
→ portia_work_record_ref
```

and:

```
suite-neutral identity representation
→ ModuleWorkRef + ModuleRecordRef
```

These representations identify the same canonical record in different architectural contexts.

They are not interchangeable serialized contracts.

#### Core Publication Record relationship

Core Publication Records pair:

```
work
source_record
```

where:

* `work` is a Core `ModuleWorkRef`;
* and `source_record`, when present, is a Core `ModuleRecordRef`.

Core requires the source-record module ID to match the work module ID.

A Core Publication Record owns its own serialization.

Portia must not require Core to wrap those values inside:

```
module_work_record_ref
```

Portia publication integration should instead provide the exact Core values through Core’s producer-facing publication contract.

A Portia-owned manifest may use this shared Portia reference object when the manifest itself needs to express complete source-record provenance.

#### No work-kind field

A Module Work Record Reference must not contain:

```
work_kind
work_contract_version
```

Core’s `ModuleWorkRef` is intentionally neutral.

Portia does not own another producer’s work-kind vocabulary or top-level work-contract model.

Where a consuming contract requires a particular producer capability or record kind, that rule belongs to:

* the containing Portia field;
* the originating module’s public contract;
* a Core Publication Record capability;
* or another explicit integration contract.

It does not change the shared reference shape.

#### Canonical target identity

The canonical target-record identity is:

```
work_ref.module_id
+ work_ref.class_id
+ work_ref.work_id
+ record_ref.record_kind
+ record_ref.record_id
```

Because the two module IDs must agree, both occurrences identify the same module authority.

The following field does not create a separate canonical record:

```
record_ref.contract_version
```

It identifies the public target-record contract expected by this use of the reference.

#### Complete reference-value equality

Two Module Work Record Reference values are equal when every nested field matches, including:

```
work_ref.module_id
work_ref.class_id
work_ref.work_id
record_ref.module_id
record_ref.record_kind
record_ref.record_id
record_ref.contract_version
```

Two references may identify the same canonical record while expecting different record-contract versions.

Those references identify the same canonical record but are not equal as complete reference values.

#### Reference versus relationship

A Module Work Record Reference identifies one canonical record.

It does not state why the record is relevant.

The containing property or domain-specific wrapper supplies the relationship meaning.

For example:

```
{
  "instructional_context_ref": {
    "module_work_record_ref": {
      "work_ref": {
        "module_id": "quillan",
        "class_id": "eng10_p2_2026",
        "work_id": "assignment_work_001"
      },
      "record_ref": {
        "module_id": "quillan",
        "record_kind": "assignment",
        "record_id": "assignment_001",
        "contract_version": "1"
      }
    }
  }
}
```

The outer:

```
instructional_context_ref
```

field supplies the Portia domain meaning.

The nested Module Work Record Reference supplies only complete canonical target identity and expected record-contract information.

#### Reference versus publication

A Module Work Record Reference does not establish that the referenced record is:

* reportable;
* published;
* included in a Core registry;
* eligible for Meridian;
* authorized for disclosure;
* or part of a Meridian report.

Those meanings require:

* a producer-owned immutable manifest;
* a Core Publication Record;
* current publication and withdrawal state;
* applicable authorization;
* and Meridian source-selection and report-composition policy.

Likewise, a Core Publication Record does not automatically make a source record a Grade item or academic result.

#### Roster-student and Actor exclusion

A Core roster student does not use Module Work Record Reference identity.

Roster students use:

```
roster_student_ref
```

A Portia Actor does not use Module Work Record Reference identity.

Actors use:

```
actor_ref
```

Those are identity-authority references, not module work-record references.

#### Display snapshots

No display snapshot belongs inside:

```
work_ref
record_ref
```

or at the top level of the Module Work Record Reference.

A containing Portia contract may place a bounded historical snapshot beside:

```
module_work_record_ref
```

only when the shared snapshot contract permits it.

The snapshot does not participate in canonical identity or complete reference-value equality.

#### Resolution

Structural validity establishes only that:

* `work_ref` has the exact Core work-reference shape;
* and `record_ref` has the exact Core record-reference shape.

Application validation must:

1. validate both nested Core values;
2. confirm module-ID agreement;
3. confirm that the named module is recognized;
4. resolve exactly the class and work named by `work_ref`;
5. use the originating module’s public integration contract to resolve or validate `record_ref`;
6. confirm that the target record belongs to the named work;
7. confirm record-kind agreement;
8. confirm record-ID agreement;
9. confirm contract-version support;
10. confirm current or historical lifecycle eligibility;
11. apply the containing Portia record’s domain-specific eligibility rules;
12. and apply authorization separately where disclosure or reporting is involved.

#### Prohibited resolution behavior

Portia must not resolve a Module Work Record Reference by:

* recursively crawling the workspace;
* inspecting undocumented module-private paths;
* searching another class or work root for the same record ID;
* inferring the module from `record_kind`;
* relying solely on an ID prefix;
* matching a title or display label;
* treating Core’s derived catalog as canonical authority;
* silently changing `contract_version`;
* silently following a successor;
* or copying the sibling record into Portia.

#### Resolution states

Portia must be able to distinguish:

```
structurally invalid complete reference
module-ID mismatch
unrecognized module
structurally valid but unresolved work reference
resolved work but unresolved record reference
resolved record under the wrong record kind
resolved record under an unsupported contract
historically resolvable record
currently resolved but ineligible record
currently resolved and eligible record
resolved record not authorized for the intended disclosure
```

Authorization is not established by reference resolution.

#### Schema direction

The shared reference schema should define a closed reusable Module Work Record Reference object.

JSON Schema should enforce:

* exactly `work_ref` and `record_ref`;
* `work_ref` conforming to the exact Core `ModuleWorkRef` structure;
* `record_ref` conforming to the exact Core `ModuleRecordRef` structure;
* required `record_ref.contract_version`;
* string-or-null contract-version type;
* no unknown top-level properties;
* and no duplicated top-level identity fields.

Application validation remains responsible for:

* module-ID equality;
* recognized-module status;
* work existence;
* record existence;
* record-to-work membership;
* originating-module contract compatibility;
* lifecycle eligibility;
* consuming-record restrictions;
* and authorization.

#### Existing-contract consequences

The Event schema’s provisional flat:

```
instructional_context.external_refs[]
```

shape will eventually be replaced by Module Work Record Reference values.

No finalized active Portia schema currently exposes another general-purpose module-qualified record-reference contract.

The change can therefore be introduced without migration aliases or dual accepted shapes.

#### Invariants

1. A Module Work Record Reference identifies one typed module-owned record within one exact class-owned module work context.
2. It contains exactly `work_ref` and `record_ref`.
3. `work_ref` conforms to Core’s exact `ModuleWorkRef`.
4. `record_ref` conforms to Core’s exact `ModuleRecordRef`.
5. Both module IDs must match exactly.
6. The repeated module ID is intentional.
7. The contract is structurally module-neutral.
8. Ordinary Portia-native references continue to use the more precise Portia contracts.
9. Suite-neutral boundaries may use the Core-qualified pair for Portia-owned records.
10. The reference contains no sibling work-kind or work-contract metadata.
11. The `contract_version` key is always present.
12. The reference does not establish publication, reportability, authorization, or Grade eligibility.
13. Roster students and Actors use their own identity-authority references.
14. Display snapshots do not belong inside the complete reference.
15. Structural validity does not prove target existence, compatibility, eligibility, or authorization.
16. Resolution never crawls sibling-module private storage.
17. Unresolved references are reported rather than repaired through inference.

### 13.7 `portia_target_ref`

#### Decision

Portia will use a closed, discriminated **Portia Target Reference** family for records that explicitly declare what part of an Event they apply to.

The initial target family contains exactly three branches:

```
event
event_participant
event_participants
```

The ordinary serialized property name is:

```
target
```

A target states the application scope of the containing record.

It does not identify:

* the record’s creator;
* an Account source;
* an observer;
* evidence;
* assertion basis;
* an authorizing person;
* a workflow trigger;
* a relationship endpoint;
* or record ownership.

Those concepts require separate typed fields.

#### Event-local scope

The initial `portia_target_ref` family is Event-local.

Its scope provider must identify one unambiguous Portia Event work root.

Ordinarily, the containing canonical Event child record supplies:

```
module_id
class_id
work_id
```

The shared Event target family must not be used to target an Event or participant in another work root.

A genuine cross-work application requires a complete Portia work or work-record reference under a domain contract that explicitly permits cross-work targeting.

Support Process targeting is a separate contract decision because:

* a Support Process as a whole;
* a support recipient;
* a provider;
* an implementation subject;
* and a linked Event Participant

are not automatically the same target concept.

#### Closed union

A Portia Target Reference is exactly one of:

```
event_target
event_participant_target
event_participant_set_target
```

Mixed target kinds are prohibited within one target value.

A record cannot combine:

```
Event as a whole
+
selected Event Participants
```

through one target object.

A later record requiring two distinct application concepts must represent them through separately named domain fields or through a new explicit architectural decision.

It must not broaden this target union implicitly.

---

#### Event target

The exact Event target shape is:

```
{
  "kind": "event"
}
```

It contains exactly:

```
kind
```

Unknown properties are prohibited.

The Event target identifies the containing Event as a whole.

It does not require or permit:

```
module_id
class_id
work_id
work_kind
event_id
record_ref
participant_id
participant_ids
targets
contract_version
display_snapshot
```

The containing Event scope already provides complete identity.

##### Meaning

An Event target means:

> The containing record applies to the Event-level context rather than to one or more explicitly selected Event Participants.

It must not be interpreted as applying automatically to:

* every Event Participant;
* every roster student associated with the Event;
* every Actor associated with the Event;
* every person mentioned in an Account;
* every linked Support Process;
* or every later record beneath the Event.

Event-level application and participant-level application remain distinct.

##### Eligibility

An Event target is valid only when its scope provider is an Event work root.

It is not valid merely because a containing record happens to mention an Event.

Each consuming record schema must explicitly permit Event-level targeting.

---

#### Singular Event Participant target

The exact singular participant-target shape is:

```
{
  "kind": "event_participant",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "1"
  }
}
```

It contains exactly:

```
kind
record_ref
```

Unknown properties are prohibited.

The nested `record_ref` must conform to the accepted `local_record_ref` contract.

Within this target branch:

```
record_ref.record_kind
```

must equal:

```
event_participant
```

##### Meaning

The target identifies one canonical Event Participant record in the containing Event.

It targets the participant’s Event-local involvement.

It does not directly target:

* the participant’s roster student;
* the participant’s Actor;
* an unidentified person description;
* a display snapshot;
* or the real-world person independently of the Event.

The Event Participant record remains authoritative for its subject identity.

##### Prohibited embedded identity

The target must not contain:

```
roster_student_ref
actor_ref
student_id
actor_id
subject
display_snapshot
participant record content
```

The target must not copy any independently editable participant data.

##### Resolution

Application validation must confirm that the participant:

* exists;
* belongs to the containing Event;
* has the expected record kind;
* agrees with its canonical path and stored identity;
* supports the stated contract version;
* and has a lifecycle state eligible for the consuming record’s operation.

The consuming record determines whether it requires a participant that is:

```
proposed
active
historically valid
superseded but historically resolvable
another explicitly permitted state
```

The shared target contract does not silently select one lifecycle rule for every record family.

##### Supersession

A participant target identifies the exact historical Event Participant record named by `record_ref`.

It must not silently redirect to:

* a successor participant;
* another participant with the same subject;
* a participant with a matching roster-student reference;
* or a participant with a matching Actor reference.

A new operation may require a current eligible participant, but historical records retain their original target identity.

---

#### Event Participant set target

The exact participant-set target shape is:

```
{
  "kind": "event_participants",
  "targets": [
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_one",
        "contract_version": "1"
      }
    },
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_two",
        "contract_version": "1"
      }
    }
  ]
}
```

It contains exactly:

```
kind
targets
```

Unknown properties are prohibited.

The `targets` array contains only singular Event Participant target values.

It must not contain:

* an Event target;
* another participant-set target;
* a bare participant ID;
* a roster-student reference;
* an Actor reference;
* or another record-reference kind.

##### Cardinality

A participant-set target contains at least two singular participant targets.

An empty array is invalid.

A one-participant application must use:

```
kind = event_participant
```

rather than a one-element set.

The shared target family does not require every consuming record type to permit participant sets.

Each consuming schema must explicitly authorize plural targeting.

##### Duplicate prohibition

Two entries targeting the same canonical Event Participant are duplicates even when their:

```
contract_version
```

values differ.

Duplicate detection therefore uses canonical participant identity:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_kind
+ record_id
```

rather than complete reference-value equality.

A participant set must not contain two contract expectations for the same participant.

##### Ordering

Participant-set order has no domain meaning.

Array position must not imply:

* priority;
* responsibility;
* severity;
* chronology;
* leadership;
* sequence of involvement;
* or presentation order.

Canonical serialization should sort validated targets deterministically by:

```
record_ref.record_id
record_ref.contract_version
```

after canonical duplicate detection.

Interfaces may display targets in another useful order, but display order must not become canonical semantic state.

##### No synthetic group

Several explicitly selected participants do not create:

* a Group;
* a collective participant identity;
* a shared subject;
* a team;
* a household;
* a cohort;
* or another canonical entity.

The target set states only that the containing record applies jointly to the explicitly listed Event Participant records under the consuming record’s defined semantics.

Plural targeting does not imply identical:

* involvement;
* responsibility;
* credibility;
* evidence;
* Role;
* Response;
* support;
* Follow-Up;
* or Outcome.

A consuming record that requires participant-specific differences must represent those differences explicitly or use separate canonical records.

---

#### Consuming-record restrictions

The shared `portia_target_ref` contract defines the available Event-local target vocabulary.

It does not authorize every target branch in every record.

Each consuming record contract must define:

* whether `target` is required;
* whether target omission is permitted;
* which target kinds are permitted;
* whether exactly one participant is required;
* whether plural participant targeting is permitted;
* whether Event-level targeting is permitted;
* lifecycle requirements for participant targets;
* and the domain meaning of plural application.

Representative restrictions may include:

```
Event only
one Event Participant only
one or several Event Participants
Event or one Event Participant
Event or one-or-several Event Participants
no target concept
```

The Event Participant Role contract permits only:

```
kind = event_participant
```

because one Role applies to exactly one participant.

#### No undocumented default target

Omitting a target must not silently mean:

```
the containing Event
every Event Participant
the first Event Participant
the record creator
the owning class
the roster student associated with the work
the person named in an Account
the participant inferred from another field
```

A consuming record must do one of the following explicitly:

1. require a `target`;
2. define one fixed target through its canonical parent and record semantics;
3. or establish that the record has no target concept.

Implicit target inference is prohibited.

#### Target versus reference

A target and a reference are related but distinct concepts.

The outer target object states:

```
what the containing record applies to
```

The nested `record_ref`, when present, states:

```
which canonical Event Participant record is identified
```

For example:

```
kind = event_participant
```

supplies the target semantics.

The nested:

```
record_kind
record_id
contract_version
```

supplies record identity and expected target-contract information.

A `local_record_ref` does not become a target merely because it is nested inside a field named `target`.

The domain wrapper remains authoritative for application meaning.

#### Target identity and equality

##### Event target identity

An Event target’s canonical target identity is:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ kind = event
```

Two Event targets are equal when they inherit the same Event work identity.

##### Singular participant target identity

A singular participant target’s canonical target identity is:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_ref.record_kind
+ record_ref.record_id
```

Complete target-value equality also includes:

```
record_ref.contract_version
```

Two singular targets may identify the same canonical participant while expecting different participant contract versions.

They identify the same canonical target but are not equal as complete target values.

##### Participant-set equality

Participant-set equality is order-insensitive.

Two participant-set target values are equal when their deterministically normalized singular target values match, including contract-version expectations.

Canonical duplicate detection remains based on canonical participant identity rather than complete target-value equality.

#### Missing and historical targets

A missing current participant does not automatically invalidate every historical record that targets it.

The consuming contract determines whether it requires:

```
current eligible target
historically valid target
target existence only
best-effort historical resolution
```

Portia must report unresolved, unsupported, or ineligible targets.

It must not:

* retarget them automatically;
* replace them with a subject identity;
* search other Events;
* or treat display information as canonical identity.

#### Structural and application validation

JSON Schema should enforce:

* the closed target discriminator;
* exact branch properties;
* no unknown properties;
* fixed `record_kind = event_participant` in participant branches;
* required participant `contract_version`;
* participant-set minimum size of two;
* singular target objects inside participant sets;
* and prohibition of structurally mixed target kinds.

Application validation remains responsible for:

* identifying the Event scope provider;
* confirming the scope provider is an Event;
* target existence;
* same-Event participant membership;
* canonical duplicate detection;
* contract-version support;
* lifecycle eligibility;
* deterministic canonical ordering;
* consuming-record branch permissions;
* consuming-record cardinality;
* historical-resolution behavior;
* and prohibition against silent supersession following.

#### Role reconciliation

The Event Participant Role’s current:

```
participant_id
```

will eventually become:

```
target
```

using the singular participant branch:

```
{
  "kind": "event_participant",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "1"
  }
}
```

The Role continues to apply to exactly one participant.

The target decision does not authorize multi-participant Role records.

#### Invariants

1. A Portia Event target states what part of one Event the containing record applies to.
2. The initial target family is Event-local.
3. The family contains exactly Event, singular participant, and participant-set branches.
4. One target value cannot mix Event-level and participant-level application.
5. An Event target does not target every participant.
6. Participant targets identify Event Participant records rather than underlying people.
7. Participant targets use `local_record_ref`.
8. Participant target `record_kind` always equals `event_participant`.
9. A participant set contains at least two singular participant targets.
10. One participant uses the singular branch.
11. Duplicate canonical participant targets are prohibited.
12. Participant-set order has no domain meaning.
13. A participant set does not create a synthetic Group.
14. Every consuming schema explicitly declares permitted target kinds and cardinality.
15. Target omission creates no undocumented default.
16. Targets do not replace source, basis, evidence, attribution, or relationship fields.
17. Display snapshots do not belong inside target values.
18. Structural validity does not prove target existence or eligibility.
19. Historical targets are not silently redirected to successors.
20. Decision 8 defines the separate support_process_target_ref family. Event and Support Process target families intentionally remain distinct and non-interchangeable.

### 13.8 `support_process_target_ref`

#### Decision

Portia will use a separate, closed, discriminated **Support Process Target Reference** family for records that explicitly declare what part of a Support Process they apply to.

The initial target family contains exactly three branches:

```
support_process
support_process_participant
support_process_participants
```

The ordinary serialized property name is:

```
target
```

The family parallels the Event-local `portia_target_ref` contract accepted in Decision 7.

The two target families are intentionally similar but are not interchangeable.

An Event record must not use a Support Process target.

A Support Process record must not use an Event-local target merely because the two shapes are structurally similar.

#### Architectural commitment

This decision establishes that a Support Process may have canonical:

```
support_process_participant
```

records.

A Support Process Participant represents one person’s documented connection to one Support Process.

The participant record—not the underlying person identity—is the canonical target for participant-specific Support Process records.

This preserves the distinction between:

```
the person
```

and:

```
the person’s participation in this Support Process
```

The complete Support Process Participant schema remains deferred to the dedicated Support Process issue.

That later contract must define matters such as:

* participant subject identity;
* participant lifecycle;
* participant roles;
* recipient eligibility;
* provider eligibility;
* implementation-subject eligibility;
* correction and supersession;
* and cross-year continuity.

This target decision does not finalize those models.

#### Support Process-local scope

The `support_process_target_ref` family is local to one Support Process work root.

Its scope provider must identify one unambiguous Portia work item whose:

```
work_kind
```

is:

```
support_process
```

Ordinarily, the containing canonical Support Process child record supplies:

```
module_id
class_id
work_id
```

The target must not repeat those scope fields.

A target identifying a participant in another Support Process requires a complete:

```
portia_work_record_ref
```

under a separately named domain field that explicitly permits cross-work application.

A target identifying an Event Participant requires a complete cross-work Portia record reference.

It must not be inserted into the local Support Process target family.

#### Closed union

A Support Process Target Reference is exactly one of:

```
support_process_target
support_process_participant_target
support_process_participant_set_target
```

Mixed target kinds are prohibited within one target value.

A target cannot combine:

```
Support Process as a whole
+
selected Support Process Participants
```

A later record requiring two distinct application concepts must use separately named fields or receive a new explicit architectural decision.

It must not broaden this shared target union implicitly.

---

#### Support Process target

The exact whole-process target shape is:

```
{
  "kind": "support_process"
}
```

It contains exactly:

```
kind
```

Unknown properties are prohibited.

The target identifies the containing Support Process as a whole.

It does not require or permit:

```
module_id
class_id
work_id
work_kind
support_process_id
record_ref
participant_id
participant_ids
targets
contract_version
display_snapshot
```

The containing Support Process work scope already supplies complete identity.

##### Meaning

A whole-process target means:

> The containing record applies to the Support Process-level context rather than to one or more explicitly selected Support Process Participants.

It must not be interpreted as applying automatically to:

* every Support Process Participant;
* every recipient;
* every provider;
* every implementation subject;
* every linked Event;
* every Event Participant in a linked Event;
* every planned Support or Intervention;
* every implementation occurrence;
* every Follow-Up;
* or every Outcome.

Process-level and participant-level application remain distinct.

##### Eligibility

A whole-process target is valid only when its scope provider is a Support Process work root.

Each consuming record schema must explicitly permit whole-process targeting.

The existence of this branch does not mean every Support Process child record may target the entire process.

---

#### Singular Support Process Participant target

The exact singular participant-target shape is:

```
{
  "kind": "support_process_participant",
  "record_ref": {
    "record_kind": "support_process_participant",
    "record_id": "spp_example",
    "contract_version": null
  }
}
```

It contains exactly:

```
kind
record_ref
```

Unknown properties are prohibited.

The nested `record_ref` must conform to the accepted `local_record_ref` contract.

Within this target branch:

```
record_ref.record_kind
```

must equal:

```
support_process_participant
```

##### Meaning

The target identifies one canonical Support Process Participant record beneath the containing Support Process.

It targets the participant’s documented connection to that Support Process.

It does not directly target:

* a Core roster student;
* a Portia Actor;
* a descriptive or unidentified person;
* a historical display snapshot;
* or the real-world person independently of the Support Process.

The Support Process Participant record remains authoritative for its subject identity and participation history.

##### Prohibited embedded identity

The target must not contain:

```
roster_student_ref
actor_ref
student_id
actor_id
subject
display_snapshot
recipient
provider
participant record content
```

The target must not copy independently editable participant information.

##### Contract version

The required:

```
record_ref.contract_version
```

is initially:

```
null
```

because the public Support Process Participant record contract has not yet been accepted.

After that contract receives an accepted version, newly created targets should use the supported non-null version.

A historical null-version target must not be silently reinterpreted as:

* the newest participant contract;
* any compatible participant contract;
* or a target whose contract version does not matter.

The consolidated contract-version rules remain authoritative for null-version behavior.

##### Resolution

Application validation must confirm that the participant:

* exists;
* belongs to the containing Support Process;
* has the expected record kind;
* agrees with its canonical path and persisted identity;
* supports the stated contract version when non-null;
* and has a lifecycle state eligible for the consuming record.

The consuming contract determines whether it requires:

```
proposed participant
active participant
historically valid participant
superseded but historically resolvable participant
another explicitly permitted state
```

The shared target contract does not impose one lifecycle rule on every Support Process record family.

##### Supersession

The participant target identifies the exact historical Support Process Participant named by the reference.

It must not silently redirect to:

* a successor participant record;
* a participant with the same underlying roster-student identity;
* a participant with the same Actor identity;
* a participant in a successor Support Process;
* or a similarly named participant.

Historical records retain their original target identity.

New operations apply current lifecycle and correction rules explicitly.

---

#### Support Process Participant set target

The exact participant-set target shape is:

```
{
  "kind": "support_process_participants",
  "targets": [
    {
      "kind": "support_process_participant",
      "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_one",
        "contract_version": null
      }
    },
    {
      "kind": "support_process_participant",
      "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_two",
        "contract_version": null
      }
    }
  ]
}
```

It contains exactly:

```
kind
targets
```

Unknown properties are prohibited.

The `targets` array contains only singular Support Process Participant target values.

It must not contain:

* a whole Support Process target;
* another participant-set target;
* an Event Participant target;
* a bare participant ID;
* a roster-student reference;
* an Actor reference;
* or another record-reference kind.

##### Cardinality

A participant-set target contains at least two singular participant targets.

An empty participant set is invalid.

A one-participant application must use:

```
kind = support_process_participant
```

rather than a one-element set.

The shared target family does not require every consuming Support Process record to permit plural targeting.

Each consuming schema must explicitly authorize it.

##### Duplicate prohibition

Two entries targeting the same canonical Support Process Participant are duplicates even when their:

```
contract_version
```

values differ.

Duplicate detection therefore uses canonical participant identity:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_kind
+ record_id
```

rather than complete reference-value equality.

A participant set must not contain competing contract expectations for the same canonical participant.

##### Ordering

Participant-set order has no domain meaning.

Array position must not imply:

* priority;
* primary-recipient status;
* provider status;
* service sequence;
* implementation sequence;
* severity;
* responsibility;
* or presentation order.

Canonical serialization should sort validated participant targets deterministically by:

```
record_ref.record_id
record_ref.contract_version
```

after canonical duplicate detection.

A user interface may display participants in another useful order, but display order must not become canonical target semantics.

##### No synthetic group

Several selected Support Process Participants do not create:

* a Group;
* a household;
* a cohort;
* a team;
* a shared recipient identity;
* a provider team identity;
* or another canonical collective entity.

The target set states only that the containing record applies jointly to the explicitly listed participant records under the consuming record’s defined semantics.

Plural targeting does not imply identical:

* need;
* eligibility;
* participant role;
* Support;
* Intervention;
* implementation;
* frequency;
* duration;
* fidelity;
* Follow-Up;
* or Outcome.

A consuming record that requires participant-specific differences must represent those differences explicitly or create separate canonical records.

---

#### Participant role remains separate

A Support Process target identifies:

```
which participant
```

It does not identify:

```
why that participant is relevant
```

The target therefore must not include role labels such as:

```
recipient
provider
implementation_subject
coordinator
observer
reviewer
family_contact
```

The dedicated Support Process issue will define the participant-role architecture.

That architecture may use:

* participant fields;
* participant-role records;
* relationship records;
* or another accepted domain structure.

Regardless of the final representation, role meaning must not be duplicated inside the target reference.

#### Recipient eligibility

A later consuming record may restrict participant targets to participants holding an eligible recipient role.

For example, a planned Support may permit:

```
one recipient
several recipients
```

The shared target contract does not itself establish that the targeted participant is a recipient.

Application validation must evaluate the participant-role contract and the consuming record’s eligibility rules.

#### Provider is not automatically a target

A provider identifies who supplies, delivers, coordinates, or implements a Support or Intervention.

A target identifies what or whom the containing record applies to.

Those concepts must remain separate.

A future implementation occurrence may therefore contain conceptually distinct fields such as:

```
target
provider_ref
```

or another later accepted provider relationship.

The provider must not be inferred from the target.

The target must not be inferred from the provider.

A provider may itself be a Support Process Participant, but that fact does not make the provider the target of every record the provider creates or implements.

#### Implementation subject

An implementation subject may sometimes be the same Support Process Participant as the recipient.

That equivalence must not be assumed universally.

The consuming implementation contract must define:

* whether a target represents the implementation subject;
* which participant roles are eligible;
* whether several implementation subjects are permitted;
* and how providers remain separately identified.

The shared target family supplies identity and cardinality only.

#### Linked Event Participants

A Support Process Participant target must not directly identify an Event Participant.

Event Participants belong to Event work roots.

A Support Process record referring to a linked Event Participant must use:

```
portia_work_record_ref
```

through a separately named field whose semantics are defined by the consuming contract.

Examples of possible later domain meanings include:

```
initiating_event_participant_ref
related_event_participant_ref
source_event_participant_ref
```

Those names are illustrative only.

This decision does not authorize any specific cross-work field.

#### Cross-year succession

A successor Support Process has a different canonical work identity.

Participants in a successor Support Process are therefore distinct Support Process Participant records, even when they refer to the same underlying roster student or Actor.

A predecessor participant target must not silently retarget to a participant in the successor Support Process.

Cross-year continuity may be represented through:

* Support Process succession;
* explicit participant continuity relationships;
* subject-identity comparison;
* or another later accepted contract.

It must not be inferred through target resolution.

#### Consuming-record restrictions

The shared `support_process_target_ref` contract defines the available local target vocabulary.

It does not authorize every branch in every Support Process record.

Each consuming record contract must define:

* whether `target` is required;
* whether target omission is permitted;
* which target kinds are permitted;
* whether exactly one participant is required;
* whether plural participant targeting is permitted;
* which participant roles are eligible;
* which participant lifecycle states are eligible;
* and the domain meaning of plural application.

Representative restrictions may include:

```
Support Process only
one Support Process Participant only
one or several Support Process Participants
Support Process or one participant
Support Process or one-or-several participants
no Support Process target concept
```

A fidelity record may instead target:

* a planned Support;
* a planned Intervention;
* an implementation occurrence;
* or another local record

through a separate record-reference contract.

The presence of `support_process_target_ref` does not require every fidelity record to target the process or a participant.

#### No undocumented default target

Omitting a target must not silently mean:

```
the containing Support Process
every participant
every recipient
the primary recipient
the first participant
the record creator
the provider
the owning class
the student associated with a linked Event
the participant inferred from another field
```

A consuming contract must do one of the following explicitly:

1. require a `target`;
2. define one fixed target through its canonical parent and record semantics;
3. or establish that the record has no Support Process target concept.

Implicit target inference is prohibited.

#### Target identity and equality

##### Whole-process target identity

A whole-process target’s canonical identity is:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ kind = support_process
```

Two whole-process targets are equal when they inherit the same Support Process work identity.

##### Singular participant target identity

A singular participant target’s canonical identity is:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_ref.record_kind
+ record_ref.record_id
```

Complete target-value equality also includes:

```
record_ref.contract_version
```

Two targets may identify the same canonical participant while expressing different participant contract expectations.

They identify the same canonical target but are not equal as complete target values.

##### Participant-set equality

Participant-set equality is order-insensitive.

Two participant-set target values are equal when their deterministically normalized singular target values match, including contract-version expectations.

Canonical duplicate detection remains based on canonical participant identity rather than complete target-value equality.

#### Missing and historical targets

A missing current participant does not automatically invalidate every historical record that targets it.

The consuming contract determines whether it requires:

```
current eligible target
historically valid target
target existence only
best-effort historical resolution
```

Portia must report unresolved, unsupported, or ineligible targets.

It must not:

* retarget them automatically;
* replace them with the participant’s subject identity;
* search other Support Processes;
* search successor Support Processes;
* or use display information as canonical identity.

#### Structural and application validation

JSON Schema should enforce:

* the closed Support Process target discriminator;
* exact branch properties;
* no unknown properties;
* fixed `record_kind = support_process_participant`;
* required participant `contract_version`;
* participant-set minimum size of two;
* singular participant targets inside participant sets;
* and prohibition of structurally mixed target kinds.

Application validation remains responsible for:

* identifying the Support Process scope provider;
* confirming the scope provider is a Support Process;
* target existence;
* same-Support-Process participant membership;
* canonical duplicate detection;
* contract-version support;
* lifecycle eligibility;
* participant-role eligibility;
* deterministic canonical ordering;
* consuming-record branch permissions;
* consuming-record cardinality;
* historical-resolution behavior;
* and prohibition against silent successor or supersession following.

#### Schema direction

The shared target schema should define a closed reusable `support_process_target_ref` union.

The schema may reuse the same general structural strategy as `portia_target_ref`, but the branch constants and participant record kind must remain Support Process-specific.

The schema must not define one unrestricted union containing both Event and Support Process target branches.

Keeping the target families separate prevents a consuming schema from accidentally accepting the wrong work-local participant type.

#### Deferred Support Process details

This decision does not define:

* the Support Process record envelope;
* Support Process Participant subject variants;
* participant role vocabulary;
* participant-role cardinality;
* recipient eligibility rules;
* provider identity or relationships;
* Support records;
* Intervention records;
* implementation occurrence records;
* frequency or duration;
* fidelity records;
* adaptation records;
* Follow-Up;
* Outcome;
* Reentry;
* or Repair.

Those remain responsibilities of their dedicated later issues.

#### Invariants

1. A Support Process target states what part of one Support Process the containing record applies to.
2. The target family is local to one Support Process work root.
3. The family contains exactly whole-process, singular participant, and participant-set branches.
4. Event and Support Process target families remain separate.
5. One target value cannot mix process-level and participant-level application.
6. A whole-process target does not target every participant.
7. Participant targets identify Support Process Participant records rather than underlying people.
8. Participant targets use `local_record_ref`.
9. Participant target `record_kind` always equals `support_process_participant`.
10. Participant contract version is initially null until the public participant contract is accepted.
11. A participant set contains at least two singular participant targets.
12. One participant uses the singular branch.
13. Duplicate canonical participant targets are prohibited.
14. Participant-set order has no domain meaning.
15. A participant set does not create a synthetic Group.
16. Participant roles do not belong inside target references.
17. Recipient eligibility is validated separately.
18. Provider identity remains separate from target identity.
19. Event Participants require complete cross-work references.
20. Every consuming schema declares permitted target kinds and cardinality.
21. Target omission creates no undocumented default.
22. Display snapshots do not belong inside targets.
23. Historical targets are not silently redirected to successors.
24. Structural validity does not prove target existence, role eligibility, or lifecycle eligibility.

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

A reference to a Portia Event or Support Process outside the containing record’s own work root must use the complete `portia_work_ref` contract:

```
module_id
class_id
work_id
work_kind
contract_version
```

The reference does not inherit class or work scope from its containing record.

For all Portia Work References:

```
module_id = portia
```

The referenced `class_id` may differ from the containing record’s owning class.

Application validation must resolve the target only beneath the class and work root explicitly named by the reference.

It must not search other class roots for a matching `work_id`.

When the intended target is a canonical child record inside the explicitly named Portia work root, the reference must compose the complete `work_ref` with a nested `record_ref` through `portia_work_record_ref`. Within that composed reference, the sibling `work_ref` is the sole scope provider for `record_ref`. Resolution must first validate the work root and then resolve the child record only beneath that root.

### Rule 5: complete module-qualified record scope

A complete reference to a typed module-owned record must compose:

```
Core ModuleWorkRef
+
Core ModuleRecordRef
```

through:

```
module_work_record_ref
```

The exact components are:

```
work_ref.module_id
work_ref.class_id
work_ref.work_id
```

and:

```
record_ref.module_id
record_ref.record_kind
record_ref.record_id
record_ref.contract_version
```

The two module IDs must match exactly.

The reference does not inherit class, work, module, or record scope from its containing Portia record.

Within ordinary Portia-native domain records:

* Portia-owned same-work records use `local_record_ref`;
* Portia-owned cross-work records use `portia_work_record_ref`;
* and records owned by another module use `module_work_record_ref`.

At a suite-neutral boundary, the Core-qualified work-and-record pair may also identify a Portia-owned record.

Portia must resolve the record only through the explicitly named work context and the originating module’s public contract.

It must not inspect undocumented module-private storage or search other work roots for matching IDs.

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
| Portia cross-work record | work_ref`canonical identity` +record_ref `canonical identity; complete reference-value equality also includes both nested contract versions` |
| Sibling-module record | module work identity + module record identity |
| Display snapshot | never participates in identity equality |
| Event target | Inherited Portia Event work identity plus `kind = event` |
| Singular Event Participant target | Inherited Event work identity plus participant `record_kind` and `record_id`; complete target-value equality also includes `contract_version` |
| Event Participant set target | Order-insensitive normalized set of singular participant target values; duplicate detection uses canonical participant identity without `contract_version` |
| Support Process target | Inherited Portia Support Process work identity plus `kind = support_process` |
| Singular Support Process Participant target | Inherited Support Process work identity plus participant `record_kind` and `record_id`; complete target-value equality also includes `contract_version` |
| Support Process Participant set target | Order-insensitive normalized set of singular participant target values; duplicate detection uses canonical participant identity without `contract_version` |

The exact effect of:

```text
contract_version omitted
contract_version = null
contract_version = "1"
```

remains an open decision.

## 16. Reference resolution

### 16.1 Purpose

Reference resolution determines whether an accepted reference identifies an authoritative target that the current implementation can locate and interpret.

Resolution does not establish:

* authorization;
* disclosure eligibility;
* evidentiary value;
* workflow eligibility;
* current lifecycle suitability;
* permission to mutate the target;
* or permission to follow a successor.

Those decisions belong to the consuming domain contract.

The shared resolution architecture must preserve the distinction among:

```
reference structure
exact target existence
contract support
target lifecycle
consumer-specific usability
```

These dimensions must not be collapsed into one ambiguous status.

### 16.2 Resolution assessment is derived

Resolution assessment is derived application state.

It is not persisted inside canonical reference objects.

Canonical references must not gain sibling fields such as:

```
resolution_status
resolved
target_status
last_resolved_at
replacement_ref
current_target_ref
resolution_error
```

Merely resolving a reference must not mutate the containing canonical record.

An application may cache resolution results for performance, but such a cache is:

* nonauthoritative;
* rebuildable;
* time-sensitive;
* and subordinate to the canonical reference and authoritative target.

A cached result must not become the sole evidence that a target exists or previously existed.

### 16.3 Layered assessment

Every reference is evaluated through the following distinct layers:

1. structural validity;
2. exact authoritative resolution;
3. target-contract support;
4. native target lifecycle;
5. consumer-specific use eligibility;
6. authorization and privacy policy.

A successful result at one layer does not imply success at a later layer.

For example:

```
resolution_state = resolved
target_status = superseded
use_disposition = historical_only
```

is coherent.

Likewise:

```
resolution_state = resolved
target_status = active
use_disposition = not_usable
```

is coherent when the consuming field prohibits that target for another domain reason.

### 16.4 Structural validation precedes lookup

Resolution begins only after the reference family and its scope provider have been identified.

Structural invalidity includes:

* missing required identity fields;
* unexpected properties in a closed reference object;
* invalid identifier syntax;
* a missing required `contract_version` key;
* an invalid discriminator;
* a discriminator whose value conflicts with its payload;
* nested module IDs that disagree;
* repeated scope where repetition is prohibited;
* or an ambiguous scope provider for `local_record_ref`.

A structurally invalid reference has:

```
resolution_state = invalid
```

Possible diagnostic reasons include:

```
malformed_reference
unknown_reference_kind
ambiguous_scope
missing_scope_provider
inconsistent_composition
conflicting_identity_fields
```

Normal creation workflows should prevent structurally invalid references from being committed.

The outcome remains necessary for imported, legacy, corrupted, or externally supplied data.

### 16.5 Shared resolution states

The shared resolution-state vocabulary is:

```
resolved
missing
invalid
unsupported
unavailable
```

These states describe resolution of the exact referenced identity.

They do not describe whether the target is active, current, authorized, or usable.

#### Resolved

A reference is:

```
resolved
```

when the exact authoritative target has been located and its canonical persisted identity agrees with the reference.

Resolved does not mean:

* active;
* current;
* approved;
* authorized;
* eligible;
* reportable;
* safe to disclose;
* evidentiary;
* or suitable for automatic workflow use.

#### Missing

A reference is:

```
missing
```

when authoritative lookup completed successfully and no target matching the exact canonical identity exists.

Missing must not be inferred merely because:

* a derived index lacks an entry;
* a reverse projection is stale;
* a display-name search fails;
* a guessed path fails;
* an identifier prefix is unknown;
* or the resolver lacks authority to inspect the target.

A missing result requires a completed authoritative lookup at the appropriate resolution stage.

#### Invalid

A reference or discovered target is:

```
invalid
```

when it contradicts the accepted reference or target contract.

Examples include:

* path identity disagreeing with persisted identity;
* referenced `record_kind` disagreeing with the discovered record;
* referenced `work_kind` disagreeing with the canonical work;
* source module disagreement;
* nested module-ID disagreement;
* scope-provider disagreement;
* several authoritative candidates appearing where identity should be unique;
* a target malformed under its declared public contract;
* or an exact target declaring a different contract version from the version required by the reference.

Invalidity must not be repaired by choosing whichever field, file, path, or candidate appears most plausible.

#### Unsupported

A reference is:

```
unsupported
```

when it is structurally valid but the current implementation cannot interpret the requested contract.

Examples include:

* an unknown `contract_version`;
* a valid future version not supported by the current application;
* a recognized sibling module whose referenced public record contract is unsupported;
* a recognized module with an unsupported `record_kind`;
* or a valid reference branch not implemented by the current resolver.

Unsupported is not equivalent to missing.

The target may exist.

A later application upgrade may make the same unchanged reference resolvable.

#### Unavailable

A reference is:

```
unavailable
```

when the resolver cannot complete authoritative resolution because the necessary authority or storage service cannot currently be consulted.

Examples include:

* temporary storage failure;
* originating-module resolver failure;
* incomplete recovery from a staged operation;
* access restrictions;
* or a privacy boundary that prohibits confirming target existence.

Unavailable must not be reported as missing.

User-facing presentation may intentionally avoid revealing whether a protected target exists.

### 16.6 Failure stage

Composite references should preserve the stage at which resolution failed.

The conceptual failure stages are:

```
reference
scope_provider
authority
work
record
contract
```

Examples include:

```
resolution_state = missing
failure_stage = work
```

and:

```
resolution_state = missing
failure_stage = record
```

A missing work root and a missing child record are different conditions.

Likewise:

```
resolution_state = unsupported
failure_stage = contract
```

must remain distinguishable from:

```
resolution_state = unavailable
failure_stage = authority
```

Failure-stage information is derived diagnostic metadata.

It is not persisted inside the canonical reference.

### 16.7 Target lifecycle is separate

A target’s lifecycle state is not a resolution state.

A reference to a superseded record normally resolves to that exact historical record:

```
resolution_state = resolved
target_status = superseded
```

The same rule applies to targets that are:

```
proposed
draft
closed
cancelled
inactive
invalidated
superseded
```

when those statuses exist in the target’s native domain contract.

Portia must not define one universal lifecycle enum for every reference target.

The resolver preserves the target’s native status vocabulary.

For example:

```
Event:
  draft
  active
  closed
  cancelled
  invalidated
  superseded

Event Participant:
  proposed
  active
  invalidated
  superseded

Work Relationship:
  proposed
  active
  invalidated
  superseded
```

Actor and roster lifecycle information remains governed by their authoritative contracts.

### 16.8 No silent successor following

A resolver must return the exact referenced target.

It must not silently replace a superseded target with its successor.

When authorized, the resolver may provide a derived successor-navigation hint.

For example:

```
requested target:
  rel_prior_001

resolution_state:
  resolved

target_status:
  superseded

derived successor hint:
  rel_successor_001
```

The derived successor hint:

* is not canonical identity;
* does not alter the original reference;
* is not persisted into the containing record;
* is not automatically followed;
* and does not authorize use of the successor.

Following a successor requires consumer-specific policy or an explicit user operation.

### 16.9 Consumer use disposition

After resolution, the consuming field or workflow determines whether the target is usable.

The shared conceptual use-disposition vocabulary is:

```
usable
historical_only
not_usable
review_required
undetermined
```

#### Usable

The target satisfies the consuming contract’s current requirements.

#### Historical only

The target may be retained, displayed, audited, or used for historical navigation but cannot satisfy the current operational requirement.

#### Not usable

The consumer explicitly prohibits the target because of lifecycle, contract, endpoint, domain, or authorization rules.

#### Review required

The target exists, but explicit human review is required before the consuming operation may proceed.

#### Undetermined

Resolution succeeded, but eligibility has not been defined or cannot currently be evaluated.

An undetermined target must not be treated as usable by default.

Use disposition is consumer-specific.

The same resolved target may be usable for historical display and not usable for activating a dependent record.

### 16.10 Resolution is not authorization

A successfully resolved reference does not establish permission to:

* view the complete target;
* disclose it;
* mutate it;
* include it in a report;
* use it as evidence;
* activate a dependent record;
* follow a successor;
* interpret a sibling-module result;
* or make an institutional decision.

Resolution establishes identity, existence, contract support, and observable target state within the resolver’s authority.

Access, privacy, disclosure, evidentiary use, and workflow authority remain separate decisions.

### 16.11 Exact authoritative lookup

Resolution must use only the accepted identity and scope fields of the reference family.

It must not locate or repair a target through:

* display names;
* display snapshots;
* filename resemblance;
* a bare `record_id`;
* a bare `work_id`;
* matching student information;
* identifier prefix alone;
* workspace-wide first-match search;
* a derived reverse index as sole authority;
* or presumed equivalence between records.

Derived indexes may identify candidate canonical locations.

The resolver must still validate the candidate against the complete reference and authoritative record.

### 16.12 Roster student resolution

A:

```
roster_student_ref
```

resolves through its exact:

```
class_id
student_id
```

against the authoritative Core roster identified by `class_id`.

Portia must not:

* search another roster for the same student ID;
* search by name;
* merge identities across rosters;
* infer continuity from matching display information;
* or replace the roster-qualified reference with an Actor reference.

A historical display snapshot may remain available when the roster target is missing or unavailable.

The snapshot does not change the resolution result.

### 16.13 Actor resolution

An:

```
actor_ref
```

resolves through its exact:

```
actor_id
```

against the teacher-workspace Portia Actor Directory.

An inactive, invalidated, consolidated, or superseded Actor may still resolve to its exact historical record.

The consuming contract determines whether that Actor may be used for a current operation.

Resolution must not create a missing Actor automatically.

It must not match an Actor by display name or contact information.

### 16.14 Local record resolution

A:

```
local_record_ref
```

requires exactly one unambiguous Portia work-scope provider.

The resolver uses only:

```
provided work scope
record_kind
record_id
contract_version
```

It must not search sibling work roots.

If no scope provider exists or several providers conflict:

```
resolution_state = invalid
failure_stage = scope_provider
```

If the exact work scope exists but the child record does not:

```
resolution_state = missing
failure_stage = record
```

### 16.15 Portia work resolution

A:

```
portia_work_ref
```

first resolves the exact canonical work identity:

```
module_id
class_id
work_id
```

The resolver then validates:

```
work_kind
contract_version
```

against the authoritative work record.

If the work does not exist:

```
resolution_state = missing
failure_stage = work
```

If the work exists but its kind contradicts the reference:

```
resolution_state = invalid
```

If the requested contract version is unknown to the implementation:

```
resolution_state = unsupported
failure_stage = contract
```

### 16.16 Portia work-record resolution

A:

```
portia_work_record_ref
```

resolves in two explicit stages:

1. resolve `work_ref`;
2. resolve `record_ref` beneath that exact work.

Failure at the first stage must not be reported as a missing child record.

Failure at the second stage must not trigger a search in another Portia work root.

The sibling:

```
work_ref
```

is the sole scope provider for its:

```
record_ref
```

within this composed reference.

### 16.17 Module work-record resolution

A:

```
module_work_record_ref
```

resolves:

1. the exact Core `ModuleWorkRef` context;
2. the originating module’s exact `ModuleRecordRef`;
3. the target record under that module’s public contract.

The originating module remains authoritative for:

* record meaning;
* lifecycle;
* contract interpretation;
* and supported use.

Portia must not infer sibling-module semantics from:

* record IDs;
* filenames;
* display labels;
* private storage layout;
* or similar Portia record kinds.

A structurally valid sibling-module reference may be unsupported even when its target exists.

### 16.18 Target-reference resolution

Event-local and Support-Process-local target references resolve their nested local record references within the exact containing work.

Resolution alone does not establish valid targeting.

After resolution, the consuming record contract must enforce:

* permitted target branch;
* target cardinality;
* participant lifecycle;
* role or recipient eligibility;
* plural-target meaning;
* and any requirement for distinct canonical targets.

A resolved Event Participant is not automatically an eligible target for every Event-local record.

### 16.19 Work Relationship endpoint resolution

A Work Relationship resolves its:

```
source
target
```

independently as `portia_work_ref` values.

Application validation then separately enforces:

* source equals the containing work;
* the relationship-type endpoint matrix;
* non-self-reference;
* supported endpoint contracts;
* source ownership;
* active-edge uniqueness;
* and lifecycle eligibility for the attempted operation.

A target Event becoming superseded or invalidated does not silently rewrite, invalidate, or retarget the Work Relationship.

### 16.20 Contract-version behavior

A non-null:

```
contract_version
```

is an explicit target-contract expectation.

It does not mean:

```
latest
any supported version
ignore version
upgrade automatically
```

When the current implementation does not recognize the referenced version:

```
resolution_state = unsupported
```

When the target exists but declares a different contract from the reference’s expectation:

```
resolution_state = invalid
```

When:

```
contract_version = null
```

the reference records that no accepted public target contract was available under the reference contract.

Null does not mean latest or unrestricted.

Each consuming contract must determine whether a null-version reference is:

```
usable
historical_only
review_required
not_usable
undetermined
```

### 16.21 Historical display snapshots

An accepted sibling display snapshot may remain available when a target is:

* missing;
* unsupported;
* unavailable;
* invalidated;
* inactive;
* or superseded.

Presentation must distinguish:

```
resolved current target data
historically recorded snapshot data
unavailable current data
```

A display snapshot must never:

* change the resolution state;
* repair identity;
* establish current lifecycle status;
* authorize an operation;
* locate a replacement target;
* or create a new canonical record.

### 16.22 No canonical mutation during resolution

Resolution is observational.

It must not:

* rewrite a reference;
* update a reference’s contract version;
* replace a target with its successor;
* change a display snapshot;
* move a canonical record;
* create a missing Actor;
* merge roster identities;
* create reverse relationships;
* modify lifecycle status;
* or delete an unresolved reference.

Reference repair is a separate explicit correction operation governed by the containing record’s lifecycle and amendment contract.

### 16.23 Consumer-declared requirements

Every field that accepts a reference must declare:

1. the accepted reference family;
2. its scope provider;
3. required resolution state;
4. supported contract-version policy;
5. permitted target lifecycle states;
6. required use disposition;
7. missing-target behavior;
8. unsupported-target behavior;
9. historical-display behavior;
10. and whether explicit human review is required.

A structurally valid reference alone is never sufficient to establish domain eligibility.

Examples include:

#### Historical display

A historical display may permit:

```
resolved + usable
resolved + historical_only
missing + accepted display snapshot
unsupported + accepted display snapshot
```

#### Active basis

An active basis reference may require:

```
resolution_state = resolved
supported contract
eligible target lifecycle
use_disposition = usable
```

#### Supersession predecessor

A supersession operation may require:

```
resolution_state = resolved
```

while permitting a consumer-specific set of predecessor lifecycle states.

#### Work Relationship activation

Activation requires both endpoints to be:

```
resolved
contract-supported
domain-eligible
authorized for the operation
```

### 16.24 Resolution invariants

1. Resolution assessment is derived rather than persisted inside canonical references.
2. Structural validation precedes authoritative lookup.
3. Shared resolution states are `resolved`, `missing`, `invalid`, `unsupported`, and `unavailable`.
4. Missing requires completed authoritative lookup.
5. Invalid identifies a contract contradiction rather than simple absence.
6. Unsupported identifies a well-formed contract the implementation cannot interpret.
7. Unavailable must not be reported as missing.
8. Target lifecycle is separate from resolution state.
9. Superseded targets ordinarily resolve to their exact historical records.
10. Successors are not followed silently.
11. Workflow usability is separate from resolved identity.
12. Undetermined usability is not treated as usable.
13. Resolution does not establish authorization, disclosure eligibility, or evidentiary value.
14. Lookup uses exact authoritative identity and scope.
15. Display data never repairs identity.
16. Composite references preserve their failure stage.
17. Contract versions are not silently upgraded.
18. Null contract version does not mean latest or any version.
19. Resolution does not mutate canonical records.
20. Every consuming field declares its own resolution and eligibility requirements.

## 17. Targeting contracts

### 17.1 Purpose

A target identifies what part of a Portia work item a canonical record applies to.

A target does not identify:

* who created the record;
* who supplied information;
* who observed an occurrence;
* who authorized a decision;
* what evidence supports an assertion;
* who provided a Support or Intervention;
* what record initiated the workflow;
* or which work owns a cross-work relationship.

Those concepts require separate typed fields.

### 17.2 Initial target families

Portia defines two separate work-local target families:

```
portia_target_ref
support_process_target_ref
```

`portia_target_ref` applies only within Event work roots.

Its branches are:

```
event
event_participant
event_participants
```

`support_process_target_ref` applies only within Support Process work roots.

Its branches are:

```
support_process
support_process_participant
support_process_participants
```

The two families must not be combined into one unrestricted union.

A consuming schema must select the target family appropriate to its owning work kind.

### 17.3 Work-level targets

The work-level target shapes are:

```
{
  "kind": "event"
}
```

and:

```
{
  "kind": "support_process"
}
```

Each inherits complete work identity from the containing canonical record.

A work-level target does not automatically target every participant in that work.

It also does not target:

* every linked work item;
* every related person;
* every local child record;
* or every later successor.

### 17.4 Participant-level targets

An Event participant target identifies one canonical:

```
event_participant
```

record.

A Support Process participant target identifies one canonical:

```
support_process_participant
```

record.

Both use:

```
local_record_ref
```

inside a work-specific target wrapper.

Participant targets identify a person’s participation in the containing work—not the underlying roster student, Actor, or real-world person independently of that work.

A target must not embed the participant’s subject identity or display snapshot.

### 17.5 Singular and plural cardinality

Each work-local target family supports:

```
one participant
several explicitly selected participants
```

A singular participant application uses the singular branch.

A plural participant application uses the corresponding participant-set branch and contains at least two singular targets.

An empty participant set is invalid.

A one-element participant set is invalid.

The shared availability of a plural branch does not mean every consuming record may use it.

### 17.6 Duplicate participant targets

Duplicate canonical participant targets are prohibited.

Duplicate detection uses canonical participant identity:

```
inherited module_id
+ inherited class_id
+ inherited work_id
+ record_kind
+ record_id
```

Contract version is excluded from canonical duplicate identity.

A participant set must not contain two references to the same participant with different contract versions.

### 17.7 Ordering

Participant-set ordering has no domain meaning.

Array position must not imply:

* priority;
* responsibility;
* chronology;
* severity;
* recipient primacy;
* provider status;
* or presentation order.

Canonical serialization should sort validated participant targets deterministically.

Display layers may choose another useful order without changing canonical target semantics.

### 17.8 No synthetic group

Several participant targets do not create a new canonical Group or collective person identity.

They also do not imply identical:

* involvement;
* Role;
* responsibility;
* need;
* eligibility;
* evidence;
* Response;
* Support;
* Intervention;
* implementation;
* Follow-Up;
* or Outcome.

When participant-specific meaning differs, the consuming record must represent those differences explicitly or use separate canonical records.

### 17.9 Mixed target kinds

A single target value must not combine:

```
work as a whole
+
selected participants
```

A participant-set target must not contain:

* a work-level target;
* another participant-set target;
* a participant from the other work kind;
* or an unrelated record reference.

A record needing two distinct application concepts must use separately named fields or receive an explicit new contract.

### 17.10 Consuming-record obligations

Every consuming record contract must define:

* whether a target is required;
* which target family applies;
* which branches are permitted;
* whether singular or plural targeting is permitted;
* participant lifecycle eligibility;
* participant-role eligibility where applicable;
* and the meaning of plural application.

The shared target schemas establish vocabulary and structure.

They do not authorize every branch for every record.

### 17.11 Target omission

Target omission must not create an undocumented default.

Omission must not silently mean:

```
the owning work
every participant
the first participant
the record creator
the provider
the owning class
the person inferred from another field
```

A consuming contract must explicitly:

1. require a target;
2. define a fixed target through its record semantics;
3. or establish that the record has no target concept.

### 17.12 Target versus participant role

A target identifies which participant a record applies to.

It does not identify the participant’s Role.

For Events, participant Role assertions remain separate canonical records.

For Support Processes, participant roles such as recipient, provider, or implementation subject remain part of the later Support Process architecture.

Roles must not be duplicated inside target references.

### 17.13 Target versus provider

A provider identifies who performed, delivered, coordinated, or implemented something.

A target identifies what or whom the record applies to.

Provider and target are separate concepts even when the same person participates in both capacities.

Neither may be inferred automatically from the other.

### 17.14 Target versus basis and evidence

A target does not establish the factual or evidentiary basis for a record.

Account references, Observation references, paper-capture provenance, source-record references, and other basis fields remain separate.

A record may target one participant while relying on evidence supplied by another person or record.

### 17.15 Cross-work boundary

The work-local target families may identify only:

* the containing work itself;
* or participants belonging to that same work.

They must not identify a participant in another Event or Support Process.

Cross-work participant references use:

```
portia_work_record_ref
```

through a separately named domain field.

A complete cross-work reference does not automatically become a target.

The containing field must explicitly supply target or relationship meaning.

### 17.16 Successors and supersession

Targets identify exact canonical historical work or participant records.

Portia must not silently redirect a target to:

* a successor participant;
* a participant with the same underlying subject;
* a participant in a successor work;
* or a similarly named participant.

Historical records retain their original targets.

New operations apply current lifecycle and eligibility requirements explicitly.

### 17.17 Structural validation

Shared JSON Schemas should enforce:

* closed target discriminators;
* exact branch properties;
* fixed participant record kinds;
* required participant contract-version keys;
* participant-set minimum cardinality;
* singular target values inside participant sets;
* no unknown properties;
* and no structurally mixed target kinds.

### 17.18 Application validation

Application validation remains responsible for:

* identifying the work-scope provider;
* confirming the owning work kind;
* target existence;
* same-work participant membership;
* canonical duplicate detection;
* contract-version compatibility;
* participant lifecycle eligibility;
* participant-role eligibility;
* consuming-record target permissions;
* consuming-record cardinality;
* deterministic canonical ordering;
* historical-resolution behavior;
* and prohibition against silent retargeting.

### 17.19 Current reconciliation

The Event Participant Role’s current direct:

```
participant_id
```

will eventually become a required Event Participant target.

One Role continues to apply to exactly one Event Participant.

No active Support Process schema currently requires reconciliation because the Support Process family has not yet been implemented.

Later Support Process schemas must adopt the target family accepted here rather than invent direct roster-student, Actor, recipient-ID, or provider-ID target forms.

### 17.20 Targeting invariants

1. Targets identify application scope, not evidence, provenance, authorship, or ownership.
2. Event and Support Process target families remain separate.
3. Work-level targets do not target every participant.
4. Participant targets identify participation records rather than underlying people.
5. Participant sets contain at least two explicit singular targets.
6. Duplicate canonical participant targets are prohibited.
7. Participant-set order carries no domain meaning.
8. Participant sets do not create synthetic Groups.
9. Mixed work-level and participant-level targets are prohibited.
10. Every consuming schema declares permitted target kinds and cardinality.
11. Target omission creates no undocumented default.
12. Participant roles remain separate from target identity.
13. Providers remain separate from target identity.
14. Cross-work participants require complete cross-work references.
15. Historical targets are not silently redirected.
16. Structural validity does not establish target eligibility.

## 18. Relationship Findings

### 18.1 Relationship-record threshold

#### Purpose

Not every association between Portia values or records becomes a separate canonical relationship record.

An embedded reference is appropriate when the containing canonical record completely owns:

* why the association exists;
* what the association means;
* its direction;
* its lifecycle;
* its provenance;
* its correction behavior;
* and any domain-specific detail.

A separate canonical Work Relationship is appropriate only when the association is itself an independently managed Portia domain fact.

The threshold prevents both:

* creating a generic relationship record for every pointer;
* and hiding a meaningful independently managed association inside a record that cannot fully own it.

#### Required three-part test

An association becomes a separate canonical Work Relationship only when all three requirements are satisfied.

##### Requirement 1: no specialized contract fully owns the association

No accepted specialized field or canonical record may already provide the complete authoritative representation of the association.

Examples of specialized contracts that ordinarily remain authoritative include:

```
target
subject
basis
observer
recipient
owner
provider
parent-work identity
creation provenance
source-record provenance
supersedes
successor_of
```

A generic Work Relationship must not duplicate or replace one of those fields merely to create uniform graph storage.

##### Requirement 2: the association is a durable Portia domain fact

The association must have durable meaning independently of a temporary interface, report, query, or navigation view.

A derived reverse link, dashboard row, search result, timeline entry, or report inclusion does not by itself establish a canonical relationship.

The association must remain meaningful as Portia domain state even when all derived views are deleted and rebuilt.

##### Requirement 3: at least one independent-management condition applies

At least one of the following must be true:

* the association has its own lifecycle or status;
* it has independent creation provenance;
* it requires independent review or confirmation;
* it may be corrected independently of either endpoint;
* it may be invalidated independently of either endpoint;
* it may be superseded independently of either endpoint;
* it carries relationship-specific detail;
* another canonical record may need to refer directly to the association;
* it requires independent audit or navigation;
* or neither endpoint’s existing canonical record can fully own its meaning.

All three threshold requirements must be satisfied.

Cross-work scope alone does not satisfy the test.

#### Embedded-reference rule

An association remains embedded when:

* the containing record supplies its complete domain meaning;
* the association shares the containing record’s lifecycle;
* it requires no independent provenance or review;
* it carries no independently managed detail;
* it does not require direct canonical identity;
* and correction occurs by correcting, invalidating, or superseding the containing record.

An embedded reference may be:

```
same-work
cross-work
cross-class
cross-year
cross-module
```

Scope determines the completeness of the required reference identity.

Scope does not determine whether the association becomes a relationship record.

#### Embedded associations

The following associations ordinarily remain embedded under their specialized contracts:

* a Role’s Account basis;
* a Role’s Observation basis;
* a Role’s paper-capture basis;
* an Observation’s observer;
* a Communication’s sender or recipient;
* a Follow-Up’s owner;
* a record’s Event or Support Process target;
* a participant record’s subject;
* a child record’s parent-work identity;
* an Event’s instructional-context reference;
* a record’s creation provenance;
* an Event’s specialized `supersedes` reference;
* a participant’s specialized supersession entry;
* a Role’s specialized supersession entry;
* and a Support Process’s specialized `successor_of` reference.

Those fields remain canonical unless a later explicit decision establishes a materially different independently managed relationship.

#### Associations that ordinarily qualify

The following associations are likely to satisfy the threshold when their later domain contracts require independent management:

* a Support Process explicitly connected to one Event;
* a Support Process explicitly connected to several Events through one relationship record per Event;
* an Event explicitly related to another Event outside the specialized supersession contract;
* a durable association between two Support Processes outside specialized predecessor or successor fields;
* a deliberate Portia work-to-sibling-module association whose meaning is not fully owned by an existing instructional-context or provenance field;
* and another durable cross-work association with its own provenance, lifecycle, review, correction history, or relationship-specific detail.

Qualification remains dependent on the complete three-part test.

The examples do not authorize every association of those broad types automatically.

#### Support Process-to-Event example

A Support Process-to-Event association ordinarily qualifies when Portia needs to preserve an independently managed fact such as:

> This Event informed, initiated, contributed to, or is otherwise explicitly connected to this Support Process under a controlled relationship type.

The relationship may need:

* its own controlled type;
* independent creation provenance;
* explicit lifecycle state;
* independent invalidation;
* relationship-specific explanation;
* and navigation independent of either endpoint.

Each linked Event receives its own canonical relationship record.

A single relationship record must not contain an untyped array of Event endpoints merely because several Events informed the same Support Process.

#### Instructional-context counterexample

An Event’s instructional-context reference ordinarily remains embedded when the Event fully owns the meaning:

> This external record supplies instructional or assessment context for this Event.

The association does not become a Work Relationship merely because the target belongs to another module.

A later domain requirement may escalate the association only through an explicit contract and migration decision.

#### Specialized supersession precedence

Supersession remains a specialized lifecycle and correction relationship.

Accepted:

```
supersedes
successor_of
```

fields remain canonical.

Portia must not create duplicate generic Work Relationship records for the same supersession or succession fact.

Derived histories may expose those specialized associations alongside Work Relationships, but they must preserve their different canonical sources and semantics.

#### No dual canonical representation

One semantic association must have exactly one canonical representation.

Portia must not store the same association simultaneously as:

* an authoritative embedded field;
* and an authoritative Work Relationship record.

A derived view may project an embedded association into a relationship-like row for navigation.

That projection remains nonauthoritative and rebuildable.

Likewise, a derived reverse view of a Work Relationship must not be written back as another canonical field on the opposite endpoint.

#### Escalation from embedded reference

An association originally modeled as an embedded reference may later require independent relationship identity.

Such an escalation requires an explicit architectural and migration decision defining:

* the new canonical relationship contract;
* the previous embedded representation;
* the migration boundary;
* canonical authority during migration;
* historical compatibility;
* duplicate prevention;
* and whether old records retain their original representation.

Portia must not silently generate canonical relationship records from existing embedded references.

It must not treat both representations as simultaneously authoritative.

#### De-escalation from relationship record

A canonical Work Relationship must not later be collapsed silently into an embedded field.

Any de-escalation requires an explicit migration decision preserving:

* relationship identity where historically required;
* lifecycle and correction history;
* provenance;
* references from other records;
* and auditability.

#### Relationship identity is not a query optimization

A relationship record must not be created solely because:

* reverse lookup is expensive;
* a dashboard needs an edge;
* a timeline needs an entry;
* a report combines two work items;
* or a derived index would be convenient.

Those needs should ordinarily be served through rebuildable projections and indexes.

Canonical relationship identity exists for domain meaning and independent management—not query acceleration.

#### Relationship identity is not authorization

A canonical Work Relationship establishes that Portia records an association.

It does not establish that:

* every user may view both endpoints;
* every report may disclose the relationship;
* Meridian may include it;
* a linked sibling module may read Portia records;
* or either endpoint may be disclosed to the other endpoint’s ordinary audience.

Privacy, projection, authorization, and reporting rules remain separate.

#### Relationship threshold decision procedure

Later Portia issues should evaluate a proposed association in this order:

1. Identify the complete semantic statement the association represents.
2. Determine whether an accepted specialized field already owns that statement.
3. Determine whether another canonical record can own it completely.
4. Determine whether the association remains meaningful independently of derived views.
5. Identify any independent lifecycle, provenance, review, correction, detail, referenceability, or audit requirement.
6. Select exactly one canonical representation.
7. Document why an embedded field or Work Relationship is authoritative.
8. Define reverse views as derived.
9. Define migration explicitly if the representation changes later.

#### Schema consequence

The shared Work Relationship schema must not be used as a permissive fallback for associations that do not fit another schema.

A consuming domain contract must establish that its relationship type passes the threshold before it may create a Work Relationship record.

JSON Schema cannot determine semantic independence by itself.

Application and domain validation must enforce:

* allowed relationship types;
* endpoint compatibility;
* ownership rules;
* prohibition of specialized-contract duplication;
* and uniqueness rules for associations whose domain contract requires uniqueness.

#### Invariants

1. A reference does not become a relationship merely because it crosses scope.
2. A Work Relationship requires an independently managed durable Portia domain fact.
3. All three threshold requirements must be satisfied.
4. At least one independent-management condition is required.
5. Specialized accepted fields take precedence over generic relationships.
6. Relationship records must not duplicate targets, basis, provenance, supersession, succession, or other specialized fields.
7. Same-work associations may qualify when independently managed.
8. Cross-work associations may remain embedded when fully owned by a containing record.
9. Query and navigation convenience do not establish canonical relationship identity.
10. Every semantic association has one canonical representation.
11. Reverse views remain derived.
12. Escalation or de-escalation requires an explicit migration decision.
13. Relationship identity does not establish authorization or reportability.
14. Schema validation alone cannot determine whether an association passes the threshold.

### 18.2 Canonical relationship ownership

#### Decision

Every canonical Portia Work Relationship is owned by its semantic source work.

The normative invariant is:

```
containing work identity = source work identity
```

The relationship record is stored beneath the source Portia work root.

The source work creates, manages, corrects, invalidates, supersedes, retains, and otherwise controls the canonical relationship record.

The target endpoint does not store an independently editable reverse copy.

#### Source must be a Portia work

A canonical Work Relationship is Portia-owned domain state.

Its source must therefore identify the containing Portia Event or Support Process through:

```
portia_work_ref
```

The source cannot be:

* a bare `work_id`;
* a local child-record reference;
* a roster-student reference;
* an Actor reference;
* a sibling-module record;
* a derived reverse endpoint;
* or a third work that is not the semantic source.

A Portia Work Relationship may point to a sibling-module record as its target when a controlled relationship type and domain contract permit that endpoint.

Portia cannot make a sibling module the source of a canonical Portia-owned relationship because Portia does not own or write beneath the sibling module’s work root.

#### Storage agreement

The relationship’s canonical storage location must be beneath:

```
classes/<source.class_id>/modules/portia/work/<source.work_id>/
```

The exact relationship-record path will be defined with the Work Relationship envelope.

Regardless of the eventual child-record path, the containing work root must agree exactly with the source reference’s:

```
module_id
class_id
work_id
work_kind
contract_version
```

The source:

```
module_id
```

must equal:

```
portia
```

A disagreement between storage scope and source identity is:

* application-invalid;
* a storage-integrity failure;
* and not repairable by choosing whichever value appears more plausible.

Portia must not relocate, reinterpret, or rewrite the relationship silently.

#### No separate owner field

The Work Relationship must not contain an additional:

```
owner
owner_ref
owning_work
owning_work_ref
managed_by_work
```

field.

Canonical ownership is already established by:

1. the containing Portia work root;
2. the relationship record’s containing envelope;
3. and the required `source` endpoint.

A separate owner field would duplicate the same identity and create another opportunity for disagreement.

#### Source-to-target semantics

Every Work Relationship type must be defined in the direction:

```
source --relationship_type--> target
```

The source is not merely the left-hand serialized endpoint.

It is the work whose perspective, action, management, or domain meaning makes the relationship canonical.

The relationship type must therefore be worded and documented from the source perspective.

For example:

```
Support Process --informed_by--> Event
```

means that the Support Process owns and manages the fact that the Event informed it.

The same record must not be stored under the Support Process while using a type formally defined as:

```
Event --informed--> Support Process
```

That would make storage ownership disagree with semantic direction.

When the managing work is naturally the object of an English active-voice phrase, the controlled relationship vocabulary should use an inverse or passive formulation that preserves source ownership.

#### Support Process-to-Event ownership

When a Support Process records that one or more Events informed, initiated, contributed to, or otherwise contextualized the process, the Support Process is ordinarily the source and canonical owner.

For two linked Events, Portia creates two independently managed relationship records:

```
Support Process --relationship_type--> Event A
Support Process --relationship_type--> Event B
```

It must not create one relationship containing an untyped array of Event endpoints.

It must not store editable reverse relationship records beneath Event A or Event B.

#### Event-to-Event ownership

For an Event-to-Event Work Relationship, the controlled relationship type determines which Event is the semantic source and therefore the owner.

The source must not be selected through:

* lexical sorting of Event IDs;
* filesystem ordering;
* whichever Event was opened first;
* whichever interface initiated the action;
* whichever record was created most recently;
* or an arbitrary left-versus-right convention.

Examples of source-defining semantics may include:

```
later Event --follows_up_on--> earlier Event
clarifying Event --clarifies--> referenced Event
consolidating Event --duplicates--> earlier Event
current Event --provides_context_for--> another Event
```

These labels are illustrative until the controlled relationship vocabulary is accepted.

Specialized Event supersession remains outside the generic Work Relationship model.

#### Support Process-to-Support Process ownership

A Support Process-to-Support Process relationship outside specialized:

```
successor_of
```

semantics is owned by whichever process the controlled relationship type defines as the source.

For example, a later process may own a relationship expressing that it:

```
draws_context_from
continues_noncanonical_context_from
coordinates_with
```

another process, provided the relationship passes the accepted threshold and the controlled vocabulary permits it.

Cross-year succession itself remains governed by the specialized successor contract and must not be duplicated as a generic Work Relationship.

#### No third-party ownership

A Work Relationship may not be stored beneath a work that is neither semantic endpoint.

For example, a Support Process must not own:

```
Event A --related_to--> Event B
```

merely because both Events informed the Support Process.

The Support Process may instead own:

```
Support Process --informed_by--> Event A
Support Process --informed_by--> Event B
```

A genuine Event A-to-Event B relationship requires a controlled type that identifies one of those Events as the semantic source and owner.

This prevents Portia from becoming a generalized workspace knowledge graph in which one work asserts independently managed facts between two other works.

#### Target-side workflows

A user may begin a workflow while viewing the proposed target endpoint.

That interface context does not determine canonical ownership.

Before creation, Portia must determine:

* the controlled relationship type;
* its formal source kind;
* its formal target kind;
* the corresponding semantic source;
* and the source work root that must contain the record.

The application may then route the creation operation to the source work.

It must not create the relationship beneath the currently displayed target merely for interface convenience.

#### Symmetric-looking relationships

A conversationally symmetric association still requires one canonical source owner.

Portia must not store two inverse relationship records merely to make the relationship appear symmetric.

A relationship type that is genuinely symmetric must define a deterministic canonical-orientation rule.

That rule belongs to the controlled relationship-type contract and must produce exactly one source and one target for the same endpoint pair.

Potential orientation rules must not rely on unstable factors such as:

* file traversal order;
* current interface context;
* record load order;
* or creation race order.

The initial vocabulary should prefer meaningful directed semantics over a vague symmetric:

```
related_to
```

type.

#### Reverse views

The target endpoint stores no canonical reverse field or relationship record.

Reverse navigation is derived from the source-owned Work Relationship.

A derived reverse view should preserve:

* relationship ID;
* relationship type;
* canonical source;
* canonical target;
* source-owned storage scope;
* lifecycle state;
* and the fact that the view is derived.

A derived reverse label may use audience-friendly wording, but it must not change canonical direction.

For example, the canonical relationship:

```
Support Process --informed_by--> Event
```

may appear from the Event side as:

```
informs Support Process
```

The Event-side wording is a projection, not a second relationship type or editable record.

#### Source lifecycle and relationship lifecycle

Ownership does not mean the relationship’s lifecycle is identical to the source work’s lifecycle.

A qualifying Work Relationship may have its own lifecycle under the accepted relationship-record threshold.

However:

* only the source work manages that lifecycle;
* the target cannot edit it independently;
* source invalidation does not silently rewrite the target;
* target invalidation does not silently delete the relationship;
* and endpoint lifecycle effects must be defined by the relationship type and validation rules.

An unresolved or historically unavailable target may leave the relationship historically meaningful.

The application must report the endpoint state rather than silently retargeting the relationship.

#### Target authority

The source-owned relationship records Portia’s assertion that the association exists under a particular controlled relationship type.

It does not transfer ownership of the target.

The source may not:

* mutate the target;
* change the target’s lifecycle;
* rewrite the target’s identity;
* alter a sibling module’s record;
* or require the target to store a reverse reference.

The target’s originating work or module remains authoritative for the target record itself.

#### Duplicate prevention

Deterministic ownership establishes one canonical creation scope for a proposed relationship:

```
source work
+ relationship type
+ target identity
```

The complete logical uniqueness rules remain dependent on the relationship type.

Some types may permit only one active relationship for a source-target pair.

Other types may permit several independently meaningful relationships when their relationship-specific details or effective periods differ.

Regardless of type-specific multiplicity:

* the target must not create an inverse canonical copy;
* a third work must not create another copy;
* and concurrent creation beneath the same source must be reconciled under the eventual relationship persistence contract.

#### Ownership validation

Application validation must confirm that:

1. the containing work is a valid Portia Event or Support Process;
2. the `source` is a valid `portia_work_ref`;
3. `source.module_id` equals `portia`;
4. the containing work identity equals the complete source identity;
5. the relationship type permits the source work kind;
6. the relationship type permits the target endpoint kind;
7. the source and target orientation matches the type definition;
8. no specialized contract already owns the same semantic association;
9. no third-party work is attempting to own the relationship;
10. and no prohibited inverse canonical copy exists.

JSON Schema can validate the source reference’s structure.

Application validation must enforce agreement between source identity, containing storage scope, relationship type, and target kind.

#### Ownership invariants

1. Every canonical Work Relationship has exactly one owner.
2. The owner is always the semantic source work.
3. The containing work identity equals the complete source identity.
4. The source is always a Portia Event or Support Process.
5. Portia does not create source-owned relationships beneath sibling-module roots.
6. No separate owner field is persisted.
7. Relationship types are defined from source to target.
8. The target stores no editable reverse copy.
9. A third work cannot own a relationship between two other endpoints.
10. Interface location does not determine ownership.
11. Event-to-Event ownership follows controlled semantic direction.
12. Symmetric-looking relationships still receive one deterministic orientation.
13. Specialized supersession and succession contracts retain their own ownership rules.
14. Reverse views are derived and nonauthoritative.
15. Source ownership does not transfer authority over the target.
16. Source/storage mismatch is an integrity failure.

### 18.3 Direction, inverse wording, and symmetric orientation

#### Decision

Every canonical Work Relationship expresses one directed semantic assertion:

```
source --relationship_type--> target
```

The relationship record persists only the canonical source-to-target relationship type.

Target-side inverse wording is derived from the controlled relationship-type definition.

It is not persisted independently in each relationship record.

#### Direction belongs to the relationship type

The `relationship_type` must itself communicate the canonical direction.

Portia must not separate semantic meaning from orientation through fields such as:

```
direction
orientation
is_reverse
source_is_left
relationship_direction
```

A reader should be able to interpret the canonical assertion from:

```
source
relationship_type
target
```

without consulting a separate per-record direction flag.

For example:

```
Support Process --informed_by--> Event
```

has the canonical meaning:

> The source Support Process was informed by the target Event.

The relationship type must remain valid when read from the formal source toward the formal target.

#### Persisted canonical fields

The eventual Work Relationship record will persist:

```
source
relationship_type
target
```

It must not persist a second per-record field such as:

```
inverse_relationship_type
reverse_relationship_type
target_relationship_type
inverse_label
reverse_label
display_direction
```

Those values are derived from the controlled relationship-type contract.

Persisting them would create redundant canonical state that could disagree with the accepted type definition.

#### Controlled relationship-type definition

Every accepted relationship type must define at least:

```
relationship_type
source meaning
target meaning
permitted source work kinds
permitted target endpoint kinds
canonical source-to-target description
derived target-side wording
self-reference policy
multiplicity and duplicate policy
```

A type may later define additional rules for:

* required relationship-specific detail;
* lifecycle eligibility;
* provenance requirements;
* effective periods;
* correction behavior;
* privacy classification;
* and disclosure eligibility.

Those rules belong to the controlled relationship-type contract rather than being reinvented by each relationship record.

#### Type-code form

Relationship-type codes should be:

* stable;
* lowercase;
* snake_case;
* semantically directional;
* sufficiently specific for endpoint validation;
* and free of unsupported causal, evidentiary, disciplinary, diagnostic, or institutional claims.

Illustrative directional forms include:

```
informed_by
follows_up_on
clarifies
draws_context_from
uses_context_from
```

These examples illustrate naming form only.

They do not constitute the accepted initial relationship vocabulary.

#### Canonical source-to-target description

Every type must have one normative description that states exactly what the canonical record asserts.

For example, a future type might define:

```
relationship_type:
  informed_by

normative description:
  The source Support Process was informed by the target Event.
```

The normative description—not an interface label—governs:

* source eligibility;
* target eligibility;
* ownership;
* validation;
* equality;
* duplicate detection;
* and correction.

A user-interface phrase must not broaden or alter the normative claim.

#### Derived inverse wording

Each controlled type may define target-side wording for derived reverse views.

For example:

```
canonical:
  Support Process --informed_by--> Event

derived target-side wording:
  Event informs Support Process
```

The derived inverse wording:

* is not persisted in the canonical relationship record;
* does not create another relationship type for that instance;
* does not create another relationship ID;
* does not change ownership;
* does not participate in canonical relationship equality;
* and is not independently editable.

The inverse wording exists only to render the same canonical relationship from the target endpoint’s perspective.

#### Reverse wording is presentation metadata

Derived target-side wording may include:

* a concise label;
* a sentence template;
* singular and plural grammar;
* and audience-appropriate display phrasing.

Those display forms remain nonauthoritative.

They must preserve the semantic content of the canonical source-to-target type.

A presentation layer may not render:

```
informed_by
```

as:

```
caused by
```

unless the controlled type actually establishes causation.

Likewise, it may not transform contextual association into:

* proof;
* responsibility;
* blame;
* guilt;
* diagnosis;
* authorization;
* or institutional determination.

#### Reverse view preserves canonical orientation

A reverse projection must retain the canonical:

```
relationship_id
source
relationship_type
target
lifecycle state
source-owned storage scope
```

The projection may additionally expose:

```
inverse display wording
source display information
target-side navigation
derived sentence text
```

It must not rewrite the canonical relationship as though the target were the source.

For example, a target-side view may display:

> This Event informs Support Process `sup_example`.

The underlying canonical record remains:

```
sup_example --informed_by--> evt_example
```

The reverse view must continue to identify:

```
sup_example
```

as the source and owner.

#### Inverse lookup is not inverse creation

A missing target-side reverse projection must not cause Portia to create an inverse canonical relationship.

Portia should instead:

* query the derived relationship index;
* rebuild the derived projection;
* inspect authorized source-owned relationship records;
* or report that reverse navigation is unavailable.

The absence of a derived reverse row does not establish that the canonical relationship is absent.

A target-side interface must never create a second record merely to repair navigation.

#### Endpoint reversal changes directed meaning

For a directed relationship type:

```
A --relationship_type--> B
```

is not equal to:

```
B --relationship_type--> A
```

Reversing the endpoints changes:

* the semantic assertion;
* the canonical source;
* the canonical owner;
* the storage root;
* endpoint eligibility;
* and relationship identity.

For example:

```
Event A --clarifies--> Event B
```

is not equivalent to:

```
Event B --clarifies--> Event A
```

Likewise:

```
Support Process --informed_by--> Event
```

must not be normalized into:

```
Event --informed_by--> Support Process
```

The latter fails the type’s formal orientation and source-kind requirements.

#### Inverse type codes

The initial architecture does not require every relationship type to have a separately accepted inverse type code.

For example, a canonical:

```
informed_by
```

relationship may have derived reverse wording:

```
informs
```

without defining:

```
informs
```

as a separately creatable canonical relationship type.

A separately creatable inverse type should be introduced only when it represents a genuinely distinct source-owned domain assertion with its own valid creation semantics.

It must not be added merely to simplify reverse display.

If two accepted directional types are linguistic inverses, their contracts must still prevent both from being used to store the same semantic association twice.

#### Semantic correction versus wording correction

Changing derived inverse wording without changing the normative relationship meaning is a presentation-contract revision.

It does not:

* create a new relationship;
* change canonical relationship identity;
* require relationship supersession;
* or move the record.

For example, a display phrase may be clarified while continuing to render the same canonical type accurately.

Changing the actual domain assertion is different.

A change from:

```
informed_by
```

to:

```
initiated_by
```

would alter the canonical semantic claim.

That change requires the accepted relationship correction, invalidation, or supersession process.

It must not be implemented as a display-label change.

#### No initial symmetric relationship types

The initial Portia Work Relationship vocabulary will contain no symmetric relationship types.

Every initial type must define meaningful source-to-target direction.

The foundation therefore does not initially accept generic symmetric types such as:

```
related_to
associated_with
connected_to
```

This avoids using symmetry as a substitute for unresolved semantics.

It also preserves deterministic source ownership under Decision 10.

#### Future symmetric relationship requirements

A future genuinely symmetric relationship type may be introduced only through an explicit architectural decision.

That decision must define:

1. the exact symmetric domain meaning;
2. why no directed type is sufficient;
3. permitted endpoint kinds;
4. whether same-kind and cross-kind endpoint pairs are allowed;
5. a deterministic canonical-orientation rule;
6. one canonical source owner;
7. one canonical relationship record;
8. endpoint-order-independent duplicate normalization;
9. target-side and source-side display behavior;
10. self-reference policy;
11. privacy and authorization implications;
12. and migration behavior.

Even a symmetric relationship must be serialized with one canonical:

```
source
target
```

pair for ownership and storage.

Symmetry would be controlled type metadata.

It would not authorize two inverse canonical records.

#### Symmetric orientation must be deterministic

A future symmetric type’s canonical orientation must not depend on:

* current interface context;
* file traversal order;
* record load order;
* creation race order;
* which endpoint initiated the user action;
* or whichever endpoint was supplied first.

The orientation rule must produce the same canonical source and target for the same endpoint pair in every conforming implementation.

No such rule is needed for the initial vocabulary because no initial symmetric types are accepted.

#### Self-reference

Every relationship type must define whether:

```
source identity = target identity
```

is permitted.

The default should be:

```
prohibited
```

A type may permit self-reference only when the domain meaning is coherent and an explicit use case requires it.

A self-reference must not be accepted merely because both endpoint schemas validate independently.

Examples such as:

```
Event --clarifies--> itself
Support Process --informed_by--> itself
```

would ordinarily be invalid.

Specialized lifecycle fields remain responsible for any accepted self-referential correction semantics.

#### Direction and relationship equality

Canonical relationship equality and duplicate detection use the accepted directed orientation.

At minimum, the directional semantic unit includes:

```
source canonical identity
relationship_type
target canonical identity
```

The later multiplicity decision may add relationship-specific dimensions when a controlled type permits several independently meaningful relationships between the same endpoints.

The derived inverse wording does not participate in equality.

For a directed type, reversed endpoints identify a different proposed assertion rather than an equal relationship.

That reversed assertion may still be invalid because the type does not permit the reversed endpoint kinds.

#### No canonical reverse copies

Portia must not store both:

```
A --type--> B
```

and a second canonical record intended solely to express:

```
B --inverse-of-type--> A
```

when both records represent the same domain fact.

One source-owned record remains authoritative.

Reverse indexes, timelines, dashboards, histories, exports, and reports derive the opposite endpoint’s view from that record.

If a separately accepted inverse type represents a different independently managed fact, its domain contract must establish why it is not a duplicate of the existing relationship.

#### Relationship type is not evidence

A relationship type records the accepted meaning of an association.

It does not, by itself, establish:

* evidentiary sufficiency;
* factual certainty;
* causation;
* blame;
* responsibility;
* credibility;
* diagnosis;
* service authorization;
* or institutional approval.

A type whose meaning requires one of those claims must have explicit domain authority and validation rules.

Portia must not use directional wording that implies more than the canonical records support.

#### Schema direction

The eventual Work Relationship JSON Schema should require:

```
relationship_type
```

as a nonempty safe string satisfying the accepted type-code syntax.

The schema should prohibit per-record fields such as:

```
direction
inverse_relationship_type
inverse_label
reverse_label
```

Schema validation alone cannot determine whether a type is recognized or whether its endpoint orientation is valid.

#### Application validation

Application validation must confirm that:

1. the relationship type is recognized;
2. the type is active and supported;
3. the source work kind is permitted;
4. the target endpoint kind is permitted;
5. the source and target follow the type’s formal direction;
6. the containing source work owns the relationship;
7. the self-reference policy is satisfied;
8. no prohibited inverse canonical duplicate exists;
9. no specialized field already owns the same association;
10. and type-specific multiplicity rules are satisfied.

Validation must not repair invalid direction by automatically swapping source and target.

An orientation error must be reported explicitly.

The creation workflow may offer a corrected proposal, but canonical mutation requires an intentional validated operation.

#### Directional invariants

1. Every canonical Work Relationship has one source-to-target direction.
2. Direction is part of the controlled relationship type’s meaning.
3. No per-record direction flag is persisted.
4. Only the canonical directional type is persisted.
5. Inverse wording is derived and nonauthoritative.
6. Reverse views retain canonical source, type, and target.
7. Missing reverse projections do not cause inverse record creation.
8. Reversing endpoints changes a directed relationship’s meaning and ownership.
9. Derived wording changes do not change canonical identity.
10. Semantic type changes require canonical correction.
11. No symmetric types are included in the initial vocabulary.
12. Any future symmetric type requires deterministic canonical orientation.
13. Symmetry never permits two inverse canonical records.
14. Self-reference is prohibited by default.
15. Relationship wording must not imply unsupported causation, blame, proof, diagnosis, or authorization.
16. Schema validation cannot establish type recognition or endpoint compatibility.
17. Invalid orientation is reported rather than silently repaired.

### 18.4 Initial controlled Work Relationship vocabulary

#### Decision

The initial Portia Work Relationship vocabulary contains exactly one relationship type:

```
draws_context_from
```

This is the sole relationship type accepted for the initial shared Work Relationship contract.

The vocabulary is intentionally narrow.

It provides one concrete relationship that satisfies the accepted relationship-record threshold without prematurely defining semantics belonging to later Event, Determination, Response, Communication, Support, Follow-Up, Outcome, Reentry, or Repair contracts.

Additional types require explicit architectural decisions.

They must not be introduced as unreviewed strings merely because the Work Relationship schema accepts a safe relationship-type syntax.

#### Type definition

The exact type code is:

```
draws_context_from
```

The normative source-to-target statement is:

> The source Portia work explicitly uses the target Event as contextual information in understanding, documenting, reviewing, or managing the source work.

The canonical relationship is read as:

```
source --draws_context_from--> target Event
```

The target-side derived wording is:

```
provides context to
```

A derived target-side sentence may state:

> The target Event provides context to the source work.

The target-side wording is nonauthoritative presentation metadata.

It is not persisted independently in the Work Relationship record.

#### Meaning of context

For this relationship type, contextual information means that the source work deliberately records the target Event as relevant background or interpretive context.

The relationship establishes that Portia records the connection.

It does not establish that the target Event:

* caused the source work;
* initiated the source work;
* proves any allegation or statement;
* proves that the Events describe the same occurrence;
* establishes participant responsibility;
* establishes credibility;
* justifies a Classification;
* supports or authorizes a Determination;
* requires a Response;
* establishes eligibility for a Support or Intervention;
* authorizes an institutionally governed service;
* demonstrates recurrence;
* demonstrates escalation;
* demonstrates that a Response or Support was effective;
* or caused a later Outcome.

Those stronger claims require their own domain contracts, evidence rules, and authority.

#### Source endpoint

The source must be a complete:

```
portia_work_ref
```

The source:

```
module_id
```

must equal:

```
portia
```

The permitted source work kinds are:

```
event
support_process
```

The containing relationship storage scope must equal the complete source work identity under Decision 10.

#### Target endpoint

The target must also be a complete:

```
portia_work_ref
```

The target:

```
module_id
```

must equal:

```
portia
```

The target:

```
work_kind
```

must equal:

```
event
```

The initial type therefore does not target:

* a Support Process;
* a Portia child record;
* a sibling-module work;
* a sibling-module record;
* a roster student;
* a Portia Actor;
* an Event Participant;
* a Support Process Participant;
* or a derived report or publication.

Those endpoint forms may be considered only through later explicit relationship-type decisions.

#### Endpoint matrix

The initial endpoint matrix is:

| Source work kind  | Target endpoint               | Permitted |
| ----------------- | ----------------------------- | --------: |
| `event`           | Portia Event work             |       Yes |
| `support_process` | Portia Event work             |       Yes |
| `event`           | Portia Support Process work   |        No |
| `support_process` | Portia Support Process work   |        No |
| Any Portia work   | Portia child record           |        No |
| Any Portia work   | Sibling-module work or record |        No |
| Any Portia work   | Roster student or Actor       |        No |

Both permitted endpoint forms use complete `portia_work_ref` values.

Application validation—not the generic reference schema—enforces the relationship-type endpoint matrix.

#### Event-to-Event use

For:

```
Event A --draws_context_from--> Event B
```

the normative assertion is:

> Event A uses Event B as explicit contextual information in understanding, documenting, or reviewing Event A.

The relationship does not assert that:

* Event B caused Event A;
* Event A occurred after Event B;
* Event A follows up on Event B;
* the Events involve identical participants;
* participants had identical involvement;
* the Events describe one occurrence;
* Event B proves anything asserted about Event A;
* Event A corrects or clarifies Event B;
* Event A duplicates Event B;
* or either Event supersedes the other.

When one of those meanings is required, the appropriate later specialized contract or controlled relationship type must be used.

#### Support Process-to-Event use

For:

```
Support Process --draws_context_from--> Event
```

the normative assertion is:

> The Support Process uses the Event as explicit contextual information in understanding, defining, reviewing, or managing the Support Process.

The relationship does not assert that the Event:

* formally initiated the Support Process;
* established a verified need;
* proved a behavioral pattern;
* authorized a service;
* created recipient eligibility;
* required a particular Support or Intervention;
* established provider responsibility;
* or caused any implementation result or Outcome.

A later Support Process contract may define more specific links only when those links satisfy the relationship-record threshold and have independently accepted semantics.

#### Source ownership

The source work owns the relationship.

For an Event-to-Event relationship:

```
Event A --draws_context_from--> Event B
```

Event A is the source and owner.

For a Support Process-to-Event relationship:

```
Support Process --draws_context_from--> Event
```

the Support Process is the source and owner.

The target Event stores no editable reverse relationship.

Its target-side view is derived.

#### Self-reference

Self-reference is prohibited.

The following must be true:

```
source canonical work identity != target canonical work identity
```

An Event cannot draw context from itself.

Because the target must be an Event, a Support Process cannot produce a same-work self-reference under this type.

Application validation must compare complete canonical work identities rather than only `work_id`.

#### Cross-class and cross-year targets

The target Event may belong to another:

* Core class;
* instructional context;
* roster context;
* or school year.

The complete `portia_work_ref` preserves the target’s owning class and work contract.

Cross-class or cross-year scope does not change canonical ownership.

The source work continues to own the relationship.

The relationship must not imply that students or Actors referenced in the two works are the same merely because their display information matches.

#### Active multiplicity

For one source and one target, Portia permits at most one active:

```
draws_context_from
```

relationship.

The initial active semantic key is:

```
source canonical work identity
+ relationship_type
+ target canonical work identity
```

A second simultaneously active relationship with the same key is a duplicate.

The eventual lifecycle contract may preserve:

* invalidated historical relationships;
* superseded historical relationships;
* or corrected replacement relationships

with distinct relationship IDs.

It must not permit two equivalent active edges merely because their explanatory detail differs.

#### Relationship-specific detail

The eventual Work Relationship envelope may permit bounded relationship-specific detail explaining why the target Event supplies context.

That detail may describe matters such as:

* the aspect of the source work for which the Event is relevant;
* the reason the user recorded the contextual connection;
* or a concise noncausal explanation of the connection.

The detail must not broaden the accepted type into a claim of:

```
causation
proof
responsibility
blame
credibility
diagnosis
recurrence
eligibility
authorization
effectiveness
outcome attribution
```

Relationship detail remains subordinate to the controlled type’s normative meaning.

If the detail would change the semantic assertion, a different explicitly accepted type is required.

#### No untyped arrays

One relationship record identifies one source-target pair.

When one source draws context from several Events, Portia creates one canonical relationship per target Event.

For example:

```
Support Process --draws_context_from--> Event A
Support Process --draws_context_from--> Event B
```

The relationship record must not contain an untyped or independently ordered array of Event targets.

This permits each association to retain its own:

* identity;
* provenance;
* lifecycle;
* correction history;
* and bounded relationship detail.

#### Specialized contracts remain authoritative

The initial Work Relationship type must not replace or duplicate specialized accepted fields.

##### Supersession

Continue using specialized:

```
supersedes
```

references.

Do not create:

```
draws_context_from
```

merely to represent supersession, correction, replacement, consolidation, or invalidation history.

##### Support Process succession

Continue using specialized:

```
successor_of
```

semantics for predecessor and successor Support Processes.

The initial relationship type does not target Support Processes.

##### Instructional context from another module

Continue using the embedded:

```
module_work_record_ref
```

under the Event instructional-context contract.

The initial relationship type does not target sibling-module records.

##### Basis and evidence

Continue using specialized Account, Observation, paper-capture, supporting-reference, and contrary-reference fields.

A Work Relationship does not establish evidentiary support merely because a target Event supplies context.

##### Targets and participants

Continue using the accepted Event and Support Process target families.

Do not create Work Relationships merely to connect a work to its own participants or participant subjects.

#### Explicitly deferred relationship types

The initial vocabulary does not accept:

```
initiated_by
caused_by
prompted_by
follows_up_on
clarifies
corrects
duplicates
consolidates
recurs_after
escalates_from
coordinates_with
supports
responds_to
resulted_in
improved_by
associated_with
linked_to
connected_to
related_to
```

A deferred type may later be accepted only when its domain issue defines:

1. the exact normative semantic statement;
2. why an existing specialized field or record is insufficient;
3. why the association satisfies the relationship-record threshold;
4. permitted source work kinds;
5. permitted target endpoint kinds;
6. source ownership;
7. inverse wording;
8. self-reference policy;
9. multiplicity and duplicate policy;
10. lifecycle and correction behavior;
11. relationship-specific detail;
12. evidentiary limitations;
13. privacy and disclosure rules;
14. and migration consequences.

Deferral does not mean every listed type will eventually be accepted.

Some associations may remain embedded references or belong entirely to specialized domain records.

#### Vague relationship types are prohibited

The initial vocabulary contains no fallback type for unresolved semantics.

Portia must not create a relationship using:

```
related_to
associated_with
linked_to
connected_to
other
```

merely because the user or application recognizes that two records have some unspecified connection.

When the intended meaning does not match:

```
draws_context_from
```

the application must:

* use an accepted specialized field;
* use another accepted domain record;
* defer relationship creation;
* or require a later architectural decision.

It must not weaken the controlled vocabulary to preserve an ambiguous edge.

#### Relationship-type registry status

The initial relationship-type definition may be represented through:

* a closed schema enum;
* application-owned controlled metadata;
* an ADR table;
* or a combination of those mechanisms.

The implementation decision belongs with the relationship schema and envelope.

Regardless of implementation, the type definition and endpoint matrix are authoritative.

A safe string satisfying relationship-type syntax is not valid merely because it is structurally well formed.

It must match an active controlled relationship type.

#### Future vocabulary extension

Adding a Work Relationship type is a contract change.

A future extension must update:

* the controlled vocabulary;
* endpoint matrix;
* normative description;
* derived reverse wording;
* self-reference policy;
* multiplicity rules;
* validation fixtures;
* automated tests;
* ADR documentation;
* privacy analysis;
* and any affected schemas or application validators.

A future type must not reinterpret existing:

```
draws_context_from
```

records.

Existing relationships retain the meaning established by the contract version under which they were created.

#### Initial vocabulary invariants

1. `draws_context_from` is the sole initial Work Relationship type.
2. The type is directional and non-symmetric.
3. The source is a Portia Event or Support Process.
4. The target is always a Portia Event.
5. Both endpoints use complete `portia_work_ref` identity.
6. The source work owns and stores the relationship.
7. Self-reference is prohibited.
8. At most one equivalent active relationship exists per source-target pair.
9. The type records explicit contextual use, not causation or proof.
10. Event-to-Event use does not imply recurrence, clarification, duplication, or supersession.
11. Support Process-to-Event use does not imply initiation, eligibility, authorization, or effectiveness.
12. One relationship record contains one target endpoint.
13. Specialized fields retain precedence.
14. Sibling-module records are not endpoints for the initial type.
15. Vague fallback relationship types are prohibited.
16. Additional types require explicit architectural decisions.
17. Structurally safe but unrecognized type codes are invalid.

### 18.5 Work Relationship endpoint and canonical envelope

#### Decision

The initial Work Relationship uses direct work-level endpoints.

Both:

```
source
target
```

contain complete:

```
portia_work_ref
```

objects.

The initial contract does not define a new serialized `relationship_endpoint` wrapper or polymorphic endpoint union.

The endpoint concept is a domain use of an existing reference contract rather than a new reference shape.

#### Direct endpoint shape

A source endpoint has the exact `portia_work_ref` shape:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "sup_context_001",
  "work_kind": "support_process",
  "contract_version": null
}
```

A target endpoint has the same structural shape:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_context_001",
  "work_kind": "event",
  "contract_version": "1"
}
```

The controlled relationship-type contract determines which `work_kind` values are permitted in each position.

For the initial:

```
draws_context_from
```

type:

```
source.work_kind = event | support_process
target.work_kind = event
```

#### No endpoint wrapper

The initial record must not serialize endpoints as:

```
{
  "kind": "portia_work",
  "work_ref": {
    ...
  }
}
```

It must not add:

```
endpoint_kind
source_kind
target_kind
source_ref
target_ref
```

fields.

The accepted `portia_work_ref` already carries the target module, class, work identity, work kind, and expected work-contract version.

A wrapper would add no current meaning.

#### Closed initial endpoint family

The initial Work Relationship contract supports only:

```
Portia work → Portia work
```

It does not support:

```
Portia work → Portia child record
Portia work → sibling-module work
Portia work → sibling-module record
Portia work → roster student
Portia work → Actor
Portia work → Event Participant
Portia work → Support Process Participant
Portia child record → any endpoint
sibling-module record → any endpoint
```

A later relationship type requiring another endpoint family must explicitly define:

* why the association satisfies the relationship-record threshold;
* why an existing embedded field is insufficient;
* the new endpoint reference contract;
* ownership;
* direction;
* lifecycle;
* equality and duplicate rules;
* privacy implications;
* schema-version consequences;
* and migration behavior.

Future expansion must not silently reinterpret version 1 Work Relationship records as accepting endpoint forms they could not previously contain.

#### Canonical envelope

The initial canonical Work Relationship record contains the following required fields:

```
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

It may additionally contain:

```
detail
supersedes
```

No other top-level properties belong in the initial envelope.

The optional `supersedes` field appears only on a successor Work Relationship. Its exact structure and lifecycle meaning are defined in Section 18.6.

Unknown properties must be rejected.

#### Complete example

A canonical record may have the following form:

```
{
  "schema_version": "1",
  "record_type": "work_relationship",
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "sup_context_001",
  "relationship_id": "rel_context_001",
  "status": "active",
  "relationship_type": "draws_context_from",
  "source": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "sup_context_001",
    "work_kind": "support_process",
    "contract_version": null
  },
  "target": {
    "module_id": "portia",
    "class_id": "eng10_p2_2026",
    "work_id": "evt_context_001",
    "work_kind": "event",
    "contract_version": "1"
  },
  "detail": "The Event supplies context for the initial Support Process review.",
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

The example is structurally illustrative.

Complete lifecycle eligibility and transition behavior remain subject to Decision 14.

#### Record constants

The canonical constants are:

```
schema_version = "1"
record_type = "work_relationship"
module_id = "portia"
```

The initial controlled relationship type is:

```
relationship_type = "draws_context_from"
```

The initial schema should treat that value as a closed one-value vocabulary rather than accepting arbitrary safe strings.

A future vocabulary extension requires an explicit contract revision.

#### Relationship identifier

The canonical domain-specific identifier field is:

```
relationship_id
```

Its recommended form is:

```
rel_<opaque-id>
```

The canonical record does not use a top-level generic:

```
record_id
```

field.

This follows Portia’s existing domain-specific identifier pattern:

```
participant_id
role_id
relationship_id
```

When another record refers to the Work Relationship through the shared record-reference family, the reference uses:

```
{
  "record_kind": "work_relationship",
  "record_id": "rel_context_001",
  "contract_version": "1"
}
```

The canonical record field remains:

```
relationship_id
```

The shared reference field remains:

```
record_id
```

Those names serve different contracts and are not inconsistent.

#### Canonical relationship identity

The canonical record identity is:

```
source canonical work identity
+ relationship_id
```

Equivalently, its canonical storage identity is:

```
module_id = portia
class_id
work_id
record_kind = work_relationship
relationship_id
```

The following do not participate in record identity:

```
status
relationship_type
target
detail
creation_source
timestamps
attribution
```

Changing those fields does not change which persisted relationship record is being inspected.

However, material changes to the canonical assertion require a replacement record rather than mutation in place.

#### Semantic active-edge key

Relationship-record identity is distinct from the active semantic edge key accepted in Decision 12.

For:

```
draws_context_from
```

the active semantic edge key is:

```
source canonical work identity
+ relationship_type
+ target canonical work identity
```

Two files may have different `relationship_id` values while attempting to express the same active semantic edge.

Application validation must reject that condition.

Historical invalidated or superseded records may retain the same semantic components under the later lifecycle contract.

#### Storage location

The canonical storage location is:

```
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    work_relationship/
      <relationship_id>.json
```

The top-level:

```
class_id
work_id
```

identify the containing source work root.

The filename stem must equal:

```
relationship_id
```

The containing path, top-level scope fields, and complete `source` reference must agree.

#### Intentional scope repetition

The canonical record contains top-level:

```
module_id
class_id
work_id
```

and also contains a complete:

```
source
```

reference.

This repetition is intentional.

The top-level fields establish the canonical record envelope and storage scope.

The complete `source` establishes the relationship endpoint and carries:

```
work_kind
contract_version
```

The repetition does not authorize disagreement.

It creates a validation invariant:

```
top-level module_id = source.module_id
top-level class_id = source.class_id
top-level work_id = source.work_id
```

The source:

```
module_id
```

must equal:

```
portia
```

The containing work’s actual kind and public contract must agree with:

```
source.work_kind
source.contract_version
```

#### Schema version and contract version

The canonical Work Relationship record uses:

```
schema_version = "1"
```

It does not also persist a redundant top-level:

```
contract_version
```

field.

References to a Work Relationship use:

```
contract_version = "1"
```

within the appropriate `local_record_ref` or `portia_work_record_ref`.

The endpoint work references retain their own:

```
contract_version
```

fields.

Those endpoint values describe the expected public contracts of the referenced Event or Support Process.

They do not describe the Work Relationship schema.

#### Status boundary

The initial structural status vocabulary is:

```
proposed
active
invalidated
superseded
```

This decision establishes only that these values belong in the version 1 envelope.

Decision 14 will define:

* permitted transitions;
* direct reviewed active creation;
* imported and paper-derived creation;
* automated proposals;
* invalidation;
* correction;
* supersession;
* terminal behavior;
* transition-history persistence;
* and hard-deletion policy.

The status field does not authorize a transition merely because both the old and new values validate independently.

#### Relationship type

The relationship record persists one canonical:

```
relationship_type
```

For schema version 1, the only accepted value is:

```
draws_context_from
```

The record does not persist:

```
direction
orientation
inverse_relationship_type
reverse_relationship_type
inverse_label
reverse_label
```

Direction and target-side wording remain controlled metadata under Decision 11.

#### Optional detail

The optional property name is:

```
detail
```

When present, it contains concise neutral text explaining why the target Event provides context to the source work.

It must remain subordinate to the normative meaning of:

```
draws_context_from
```

It must not broaden the relationship into a claim of:

* causation;
* proof;
* responsibility;
* blame;
* credibility;
* recurrence;
* diagnosis;
* eligibility;
* authorization;
* effectiveness;
* or Outcome attribution.

A detail that changes the semantic assertion indicates that the selected relationship type is inadequate.

Portia must not preserve a stronger unsupported assertion by placing it in free text beneath a weaker type.

#### No generic rationale or basis

The initial Work Relationship envelope does not contain:

```
rationale
justification
basis
basis_refs
evidence
evidence_refs
supporting_records
contrary_records
triggered_by
```

The target Event is a relationship endpoint.

It is not automatically evidence supporting another claim.

A future type that genuinely requires independent basis must define:

* what proposition the basis supports;
* eligible reference kinds;
* required scope;
* lifecycle eligibility;
* provenance;
* evidentiary limitations;
* and why the basis belongs to the relationship rather than another domain record.

#### Creation provenance

The Work Relationship reuses the accepted structured Portia:

```
creation_source
```

contract.

It does not define an unrelated relationship-specific provenance object.

The shared provenance family may represent established Portia creation modes such as:

```
digital_entry
paper_capture
import
```

A paper-derived Work Relationship can exist only after returned-page interpretation creates a specific relationship assertion.

It therefore cannot use a preallocation stage merely because a blank form or route existed.

Complete creation-source variants and future automation behavior remain governed by the shared provenance contract and Decision 14.

#### Local attribution

The record requires:

```
created_by
updated_by
```

using the accepted Portia local-attribution shape.

These fields record local operation provenance.

They do not establish:

* institutional identity;
* institutional authorization;
* decision authority;
* employment status;
* or legal authorship.

At creation:

```
updated_by = created_by
```

A later lifecycle operation may update:

```
updated_by
```

without changing:

```
created_by
```

#### Timestamps

The record requires:

```
created_at
updated_at
```

Every timestamp must include an explicit UTC offset or:

```
Z
```

At creation:

```
updated_at = created_at
```

Later operations may advance:

```
updated_at
```

but must not rewrite:

```
created_at
```

Application validation remains responsible for timestamp chronology.

#### Immutable fields

After initial persistence, the following fields are immutable:

```
schema_version
record_type
module_id
class_id
work_id
relationship_id
relationship_type
source
target
creation_source
created_at
created_by
```

When present at creation, the following field is also immutable:

```
supersedes
```

Changing:

```
source
target
relationship_type
```

changes the canonical assertion and requires a new relationship record with a new:

```
relationship_id
```

Changing:

```
class_id
work_id
```

would change ownership and canonical storage and is prohibited in place.

The fields expected to change through controlled lifecycle operations are:

```
status
updated_at
updated_by
```

A proposed relationship's:

```
detail
```

may be edited in place before first activation.

After activation, canonical detail is frozen. Material correction requires a successor relationship. Nonmaterial amendment behavior remains governed by the shared amendment contract defined in Issue #12.

#### Prohibited redundant fields

The initial envelope must not contain:

```
owner
owner_ref
owning_work_ref
record_id
endpoint_kind
source_kind
target_kind
source_contract_version
target_contract_version
direction
orientation
inverse_relationship_type
reverse_relationship_type
inverse_label
reverse_label
target_display_snapshot
source_display_snapshot
```

Ownership, endpoint kind, contract expectations, and direction are already represented through:

* canonical storage;
* the direct `source` reference;
* the direct `target` reference;
* and the controlled relationship-type contract.

Display data belongs in derived views rather than the canonical Work Relationship.

#### Envelope invariants

1. Both endpoints are direct `portia_work_ref` objects.
2. No endpoint wrapper is serialized.
3. Both endpoints initially identify whole Portia works.
4. The initial target is always an Event.
5. The source is an Event or Support Process.
6. The containing work equals the source.
7. The top-level scope and source scope agree exactly.
8. The canonical identifier field is `relationship_id`.
9. The recommended ID form is `rel_<opaque-id>`.
10. The record uses `schema_version = "1"`.
11. References to the record use `contract_version = "1"`.
12. `detail` and `supersedes` are the only optional top-level fields.
13. `supersedes` appears only on a successor relationship and is immutable when present.
14. Generic basis, evidence, rationale, and owner fields are absent.
15. Creation provenance and local attribution reuse existing Portia contracts.
16. Timestamps require explicit offsets.
17. Source, target, type, owner scope, identity, and creation provenance are immutable.
18. Proposed detail may be edited before activation; active detail is frozen.
19. The initial schema uses a closed relationship-type vocabulary.
20. Unknown top-level properties are rejected.
21. Relationship-record identity and semantic-edge uniqueness remain distinct concepts.
22. Lifecycle transitions, correction, supersession, and retention follow Section 18.6.

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

### 19.1 Bounded historical person display snapshots

#### Decision

Portia defines one initial reusable historical display-snapshot contract:

```
person_display_snapshot
```

Its serialized property name is:

```
display_snapshot
```

Its exact shape is:

```
{
  "display_name": "Jordan Lee"
}
```

The snapshot is limited to historical display of a person identified through:

```
roster_student_ref
actor_ref
```

The initial contract does not define display snapshots for works, child records, relationships, targets, sibling-module records, or other reference families.

#### Exact structure

A `person_display_snapshot` contains exactly one required property:

```
display_name
```

The value must:

* be a string;
* contain at least one non-whitespace character;
* and remain bounded as a concise human-readable name.

Unknown properties are prohibited.

The snapshot contains no:

```
kind
snapshot_id
schema_version
contract_version
captured_at
captured_by
```

Its structure is versioned through the containing canonical record’s schema and the reusable shared schema contract.

#### Placement

The snapshot is a sibling of the person identity reference within the containing domain wrapper.

A roster-student wrapper has the form:

```
{
  "kind": "roster_student",
  "roster_student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Jordan Lee"
  }
}
```

An Actor wrapper has the form:

```
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_counselor_001"
  },
  "display_snapshot": {
    "display_name": "Morgan Ellis"
  }
}
```

The snapshot must not be nested inside:

```
roster_student_ref
actor_ref
```

The identity reference remains an identity-only value object.

#### Permitted use

The snapshot may appear only when a containing record has a legitimate historical-readability need for a durable person reference.

The shared contract permits a snapshot beside:

```
roster_student_ref
actor_ref
```

It does not require a snapshot beside every occurrence of those references.

Each consuming record contract must declare whether its snapshot is:

```
required
optional
prohibited
```

For Event Participant subjects, the snapshot remains required for durable roster-student and Actor subjects.

That requirement preserves historical readability if the authoritative roster or Actor Directory later becomes missing, unavailable, or inaccessible.

Other record families must not inherit that requirement automatically.

#### Historical meaning

The snapshot records the display name associated with the person when the containing canonical record established or confirmed the reference.

It is a historical presentation aid.

It is not necessarily:

* the person’s legal name;
* the person’s current name;
* the person’s current preferred name;
* a verified institutional identity;
* a permanent alias;
* or the name appropriate for every audience-specific export.

For reviewed digital creation, the snapshot should ordinarily be populated from authorized authoritative display data available at the time of creation or identity confirmation.

For imported historical records, the snapshot may preserve the source material’s historical display name when the import provenance supports that interpretation.

#### Identity exclusion

The snapshot does not participate in:

```
canonical identity
complete reference equality
duplicate detection
scope
resolution
authorization
lifecycle
target equality
relationship equality
successor selection
```

For example, these wrappers identify the same roster-qualified student:

```
{
  "roster_student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "Jordan Lee"
  }
}

{
  "roster_student_ref": {
    "class_id": "eng10_p2_2026",
    "student_id": "stu_1001"
  },
  "display_snapshot": {
    "display_name": "J. Lee"
  }
}
```

The differing snapshots may require review or amendment.

They do not identify different students.

Likewise, two wrappers with the same `actor_ref` remain references to the same Actor even if their snapshots differ.

#### Resolution behavior

A display snapshot is not consulted to resolve the adjacent reference.

Resolution uses only:

```
class_id + student_id
```

for `roster_student_ref`, or:

```
actor_id
```

for `actor_ref`.

Portia must not use `display_name` to:

* search for a replacement roster record;
* search for an Actor;
* merge identities;
* choose among candidates;
* repair a missing reference;
* follow a successor;
* or create a new canonical identity.

A snapshot does not change:

```
missing
invalid
unsupported
unavailable
```

into:

```
resolved
```

#### Current and historical presentation

When the reference resolves and authorized current display data is available, ordinary current views should generally use the authoritative current display name.

When the current display name differs from the historical snapshot, an authorized historical view may present both values.

Neutral presentation includes:

```
Current display name: Jordan Rivera
Recorded in this record as: Jordan Lee
```

The preferred historical label is:

```
Recorded in this record as
```

Portia must not automatically label a differing snapshot as:

```
former name
prior legal name
deadname
alias
incorrect name
obsolete name
```

The application ordinarily cannot infer why the values differ.

#### Presentation when resolution fails

When current authoritative display data cannot be obtained, the snapshot may support historical presentation such as:

```
Recorded name: Jordan Lee
Current roster record unavailable
```

or:

```
Historical name recorded in this record: Jordan Lee
```

The interface must make clear that the displayed value comes from the containing historical record rather than current authoritative data.

It must not present the snapshot as confirmed current information.

#### Snapshot correction before activation

While the containing canonical record remains proposed, its snapshot may be corrected in place when:

* the underlying durable person identity remains unchanged;
* the correction reflects the intended historical display name;
* and the operation follows the containing record’s proposed-record correction rules.

The operation may update:

```
updated_at
updated_by
```

It must not change the adjacent identity reference implicitly.

A change to the actual referenced person is a material identity correction governed by the containing record’s replacement process.

#### Snapshot behavior after activation

After the containing record becomes active, its historical snapshot is frozen.

It must not be automatically refreshed when:

* a roster name changes;
* an Actor display name changes;
* an Actor is consolidated or superseded;
* current display preferences change;
* or an authoritative directory is updated.

A material identity correction requires replacement of the containing canonical record under its lifecycle contract.

A nonmaterial correction, annotation, or statement of disagreement about the historical display text uses the shared amendment contract defined by Issue #12.

Until that contract is available, the active snapshot remains unchanged.

#### No automatic synchronization

The snapshot is not a cache of current display data.

Portia must not run background synchronization that rewrites historical snapshots to match current roster or Actor records.

Current display data belongs in derived views.

Historical snapshots belong to the canonical containing records that captured them.

#### Prohibited snapshot content

The initial `person_display_snapshot` must not contain:

```
class_id
student_id
actor_id
legal_name
preferred_name
former_name
pronouns
honorific
title
role
organization
school
grade_level
email
phone
address
family contact information
lifecycle status
active status
institutional identifiers
authorization data
privacy classification
notes
allegations
Account text
Observation text
Classification
Hypothesis
Determination
Response
Support
Outcome
private metadata
```

Durable identity remains in the adjacent reference.

Roles, statuses, contact information, decisions, and domain facts remain in their authoritative records.

#### Descriptive and unknown people

A descriptive or unknown person is not represented by:

```
roster_student_ref
actor_ref
```

and therefore does not use `person_display_snapshot`.

Its bounded descriptive information remains part of its own subject variant.

Portia must not wrap descriptive text in a display snapshot merely to resemble a durable identity reference.

#### No work or record snapshots initially

The initial shared architecture does not define historical display snapshots for:

```
local_record_ref
portia_work_ref
portia_work_record_ref
module_work_record_ref
portia_target_ref
support_process_target_ref
Work Relationship source
Work Relationship target
Work Relationship supersession references
```

When one of those targets cannot be resolved, an interface may display:

* canonical identifiers;
* record or work kind;
* and a neutral unavailable message.

It must not copy titles, summaries, narratives, academic work, ratings, feedback, notes, or other source content into an ad hoc snapshot.

#### Future snapshot extensions

A later record family may propose another bounded snapshot only through an explicit contract decision defining:

1. the exact snapshot object;
2. permitted reference families;
3. exact allowed fields;
4. the authoritative source of each field;
5. historical meaning;
6. placement;
7. required, optional, or prohibited status;
8. identity and equality exclusion;
9. resolution behavior;
10. correction and amendment behavior;
11. privacy limits;
12. prohibited copied content;
13. and migration consequences.

A future extension must not broaden `person_display_snapshot` into a universal arbitrary metadata container.

#### Event Participant reconciliation

The Event Participant roster-student subject should migrate from:

```
student_ref
```

to:

```
roster_student_ref
```

while retaining the sibling:

```
display_snapshot
```

The Event Participant Actor subject should migrate from:

```
actor_id
```

to:

```
actor_ref
```

while retaining the sibling:

```
display_snapshot
```

The accepted snapshot shape remains:

```
{
  "display_name": "..."
}
```

No new snapshot fields are added during this reconciliation.

#### Snapshot invariants

1. The initial reusable contract is `person_display_snapshot`.
2. Its serialized property name is `display_snapshot`.
3. It contains exactly one required field: `display_name`.
4. Unknown fields are prohibited.
5. It is a sibling of `roster_student_ref` or `actor_ref`.
6. It is never nested inside an identity reference.
7. It does not participate in identity, equality, resolution, or authorization.
8. It is not used to search for or repair a target.
9. Each consuming record declares whether it is required, optional, or prohibited.
10. Event Participant durable-person subjects continue to require it.
11. Proposed snapshots may be corrected when identity remains unchanged.
12. Active snapshots are frozen historical data.
13. Snapshots are not synchronized automatically with current directories.
14. Current and historical display values must be distinguishable.
15. Differing names receive neutral presentation rather than inferred labels.
16. Missing or unavailable targets may still show the snapshot as historical data.
17. The snapshot contains no contact, lifecycle, role, evidentiary, or domain-record content.
18. Descriptive and unknown persons do not use this contract.
19. Work and record snapshots are not initially defined.
20. Future snapshot families require explicit architectural decisions.

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

### 20.5 Versioned Event-family reconciliation

#### Decision

The existing version-1 contracts for:

```
Event
Event Participant
Event Participant Role
```

are frozen as historical public contracts.

Issue #11 will introduce reconciled version-2 contracts for all three record families.

The same:

```
schema_version = "1"
```

must not identify both the legacy serialization and the reconciled serialization.

Version-1 records remain valid only under their version-1 schemas.

Version-2 records use only the accepted Issue #11 shared reference and target contracts.

#### Version dispatch

A reader must inspect:

```
schema_version
```

before selecting the applicable record schema.

It must not:

* validate every record against only the latest schema;
* interpret version 1 using version-2 property meanings;
* infer the version from which properties happen to appear;
* or fall back from an unknown version to the newest supported version.

The exact schema filenames, `$id` values, directory organization, and registry structure remain governed by Decision 19.

Whatever organization is selected must leave both versions independently machine-addressable.

#### No dual canonical serialization

A version-2 schema must reject every superseded version-1 property or object shape.

Compatibility must not be implemented by allowing both old and new forms in one canonical schema.

Migration readers and conversion tools may understand both versions.

Canonical version-2 writers emit only version-2 forms.

#### Event version 2

A reconciled Event root uses:

```
schema_version = "2"
```

References expecting the reconciled Event contract use:

```
contract_version = "2"
```

Historical references expecting the original Event contract continue to use:

```
contract_version = "1"
```

##### Instructional-context references

Version-1:

```
instructional_context.external_refs[]
```

uses the provisional flat shape:

```
module_id
class_id
work_id
record_kind
record_id
```

Version 2 retains the containing property:

```
instructional_context.external_refs
```

but every array entry must conform to:

```
module_work_record_ref
```

Each entry therefore composes:

```
work_ref
record_ref
```

and the nested record reference includes its required:

```
contract_version
```

Version 2 rejects the legacy flat external-reference shape.

##### Event supersession

Version-1 Event supersession entries contain:

```
class_id
work_id
```

Version-2 Event supersession entries are complete direct:

```
portia_work_ref
```

objects.

For an Event predecessor, each entry requires:

```
module_id = portia
work_kind = event
```

and the predecessor’s expected Event:

```
contract_version
```

The `supersedes` field remains a specialized Event lifecycle relationship.

It does not become a Work Relationship record.

The reference entry remains direct because the containing `supersedes` field already establishes its domain meaning.

Supersession transition reasons and append-only transition history remain governed by Issue #12 rather than being invented as a second reference wrapper here.

#### Event Participant version 2

A reconciled Event Participant uses:

```
schema_version = "2"
```

References expecting the reconciled Event Participant contract use:

```
contract_version = "2"
```

##### Roster-student subject

Version-1 property:

```
student_ref
```

becomes:

```
roster_student_ref
```

The exact identity remains:

```
class_id
student_id
```

The sibling:

```
display_snapshot
```

remains required and continues to contain only:

```
display_name
```

Version 2 rejects:

```
student_ref
```

##### Actor subject

Version-1 property:

```
actor_id
```

becomes:

```
actor_ref
```

with exact shape:

```
{
  "actor_id": "actr_example"
}
```

The sibling:

```
display_snapshot
```

remains required and unchanged.

Version 2 rejects a bare subject-level:

```
actor_id
```

##### Participant supersession

Version-1 participant supersession entries use:

```
participant_id
reason
```

Version-2 entries preserve their specialized reason-bearing wrapper but replace the bare ID with:

```
record_ref
```

The nested value is a `local_record_ref` fixed to:

```
record_kind = event_participant
contract_version = "2"
```

The containing successor Event Participant remains the sole scope provider.

The exact version-2 structure is:

```
{
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_prior_001",
    "contract_version": "2"
  },
  "reason": "identity_corrected"
}
```

Any controlled reason detail remains governed by the Event Participant lifecycle contract.

Version 2 rejects supersession entries containing:

```
participant_id
```

#### Event Participant Role version 2

A reconciled Event Participant Role uses:

```
schema_version = "2"
```

References expecting the reconciled Role contract use:

```
contract_version = "2"
```

##### Participant target

Version-1 property:

```
participant_id
```

is replaced by required:

```
target
```

The target must use the singular Event Participant branch of:

```
portia_target_ref
```

The exact form is:

```
{
  "kind": "event_participant",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "2"
  }
}
```

A Role continues to target exactly one Event Participant in the same Event.

Version 2 rejects:

```
participant_id
event_participants
mixed target kinds
Event-level target
```

##### Account and Observation basis

Version-1 Account and Observation basis entries contain a bare:

```
record_id
```

Version-2 specialized wrappers retain their domain discriminators but use nested:

```
record_ref
```

For example:

```
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": null
  }
}
```

and:

```
{
  "kind": "observation_ref",
  "record_ref": {
    "record_kind": "observation",
    "record_id": "obs_example",
    "contract_version": null
  }
}
```

The containing Role remains the sole Event scope provider.

Account and Observation contract versions remain `null` until their accepted public target contracts are established.

Version 2 rejects the old bare-record-ID basis shapes.

##### Role supersession

Version-1 Role supersession entries use:

```
role_id
reason
```

Version-2 entries preserve the specialized reason-bearing wrapper but replace the bare ID with:

```
record_ref
```

The nested local reference is fixed to:

```
record_kind = event_participant_role
contract_version = "2"
```

The exact form is:

```
{
  "record_ref": {
    "record_kind": "event_participant_role",
    "record_id": "epr_prior_001",
    "contract_version": "2"
  },
  "reason": "basis_corrected"
}
```

Version 2 rejects supersession entries containing:

```
role_id
```

#### Stable identity through migration

A schema migration that does not change the underlying domain assertion preserves the existing canonical:

```
class_id
work_id
participant_id
role_id
```

and canonical storage location.

A record does not receive a new domain ID merely because its serialization is migrated from version 1 to version 2.

Schema migration is distinct from:

* identity correction;
* Event-boundary correction;
* participant replacement;
* Role replacement;
* invalidation;
* and supersession.

A migration that discovers a material domain error must stop and invoke the applicable correction workflow rather than disguising the correction as a schema conversion.

#### Explicit migration

Version-1 records are not upgraded during ordinary reading, reference resolution, or validation.

Migration requires an explicit operation that:

1. validates the complete version-1 source record;
2. selects the deterministic mapping for that record family;
3. constructs one complete version-2 candidate;
4. validates the candidate against the version-2 schema;
5. performs all required cross-record checks;
6. preserves canonical identity and unchanged provenance;
7. records migration attribution and recoverability under the future shared migration contract;
8. and commits the replacement atomically or through a recoverable staged operation.

The detailed migration-history and rollback envelope belongs to Issue #12.

#### Provenance and timestamps

Migration does not rewrite the original:

```
creation_source
created_at
created_by
```

when their meanings are unchanged.

The migrated canonical record updates:

```
updated_at
updated_by
```

according to the eventual shared migration contract.

Migration must not fabricate provenance that was absent from the version-1 record.

#### Historical version support

A version-2 implementation must retain the ability to:

* identify version-1 records;
* validate version-1 records;
* display them as historical contracts;
* resolve references carrying `contract_version = "1"`;
* and migrate them explicitly where supported.

It need not allow ordinary new record creation using version 1 after version 2 becomes the current writer contract.

#### New Issue #11 contracts

The newly defined shared reference, target, snapshot, and Work Relationship contracts begin at version 1.

They do not begin at version 2 merely because three older record families require reconciliation.

Contract versions are scoped to the specific public contract they identify.

#### Versioning invariants

1. Event-family version 1 remains frozen.
2. Reconciled Event-family records use schema version 2.
3. Version-1 and version-2 schemas remain independently addressable.
4. Readers dispatch on explicit schema version.
5. Version 2 rejects every obsolete version-1 shape.
6. Canonical schemas do not contain compatibility unions for legacy property names.
7. Event external references use `module_work_record_ref`.
8. Event supersession uses complete direct `portia_work_ref`.
9. Participant subjects use `roster_student_ref` or `actor_ref`.
10. Participant supersession uses nested `record_ref`.
11. Role participant application uses singular `target`.
12. Role Account and Observation basis use nested `record_ref`.
13. Role supersession uses nested `record_ref`.
14. Version-2 child references use contract version `"2"`.
15. Account and Observation references remain explicitly nullable until those contracts are accepted.
16. Migration preserves canonical identity when domain meaning is unchanged.
17. Material correction is not disguised as migration.
18. Reading and resolution do not migrate records.
19. Migration is explicit, validated, and recoverable.
20. Exact schema-file organization remains governed by Decision 19.

### 20.6 Identifier ownership and structural validation

#### Decision

Identifier validation follows the authority that owns the identifier contract.

Portia distinguishes among:

```
Portia-owned identifiers
Core-owned identifiers
sibling-module identifiers
structurally safe external identifiers
```

These categories must not be collapsed into one universal identifier schema.

#### Portia-owned identifiers

Portia is authoritative for the syntax of identifiers created for Portia domain records.

The initial Portia-owned identifier families are:

```
Event work ID
Support Process work ID
Actor ID
Event Participant ID
Event Participant Role ID
Work Relationship ID
```

The reusable conceptual schemas are:

```
portia_event_id
portia_support_process_id
portia_actor_id
portia_event_participant_id
portia_event_participant_role_id
portia_work_relationship_id
```

Their initial patterns are:

```
portia_event_id:
  ^evt_[A-Za-z0-9][A-Za-z0-9_-]*$

portia_support_process_id:
  ^sup_[A-Za-z0-9][A-Za-z0-9_-]*$

portia_actor_id:
  ^actr_[A-Za-z0-9][A-Za-z0-9_-]*$

portia_event_participant_id:
  ^ep_[A-Za-z0-9][A-Za-z0-9_-]*$

portia_event_participant_role_id:
  ^epr_[A-Za-z0-9][A-Za-z0-9_-]*$

portia_work_relationship_id:
  ^rel_[A-Za-z0-9][A-Za-z0-9_-]*$
```

The prefix is part of the accepted identifier contract.

It is not merely a display convention.

The complete Portia-owned identifier alphabet is limited to ASCII letters, digits, underscores, and hyphens.

Periods are not permitted in Portia-owned identifiers.

Event and Support Process identifiers must remain valid when used as Core `ModuleWorkRef.work_id` values.

A Portia schema must reject a Portia-owned identifier with the wrong prefix even when the remaining characters would be structurally safe.

#### Maximum length

Every Portia-owned identifier schema must include:

```
maxLength = 128
```

unless a later explicit architecture decision establishes a stricter bound for a particular family.

The maximum protects:

* filesystem paths;
* indexes;
* validation performance;
* logs;
* exports;
* and user-interface rendering.

The maximum-length rule does not participate in identifier equality.

An overlong value is invalid rather than equivalent to a truncated value.

#### Identifiers remain strings

Every identifier is serialized as a JSON string.

Portia must preserve:

* leading zeros;
* letter case;
* punctuation permitted by the owning contract;
* and the exact serialized value.

Portia must not convert:

```
"0012"
```

to:

```
12
```

It must not convert:

```
12
```

to:

```
"12"
```

during ordinary validation.

Numeric-looking identifiers remain strings.

#### Exact equality

Identifier equality uses exact serialized-string equality after structural validation.

Therefore:

```
"stu_001" != "STU_001"
"0012" != "12"
"evt_alpha" != "evt_Alpha"
```

Portia does not perform case-folding.

A value containing prohibited leading or trailing whitespace is invalid.

It is not trimmed before comparison.

#### Core-owned identifiers

Core remains authoritative for the complete syntax and validity of identifiers it owns.

Relevant examples include:

```
class_id
student_id
module_id
```

and the identifiers contained within Core contracts such as:

```
ModuleWorkRef
ModuleRecordRef
```

Where an independently addressable reusable Core schema exists, Portia should compose or reference that schema rather than reproduce its rules.

Portia must not redefine a Core-owned identifier merely because the same value appears inside a Portia record.

Schema organization and dependency pinning remain governed by Decision 19.

#### Core contract composition

When Portia uses:

```
module_work_record_ref
```

the nested:

```
work_ref
```

must conform to Core’s accepted `ModuleWorkRef`.

The nested:

```
record_ref
```

must conform to Core’s accepted `ModuleRecordRef`.

Portia additionally validates the Portia-owned composition rule that the nested:

```
module_id
```

values agree.

That agreement rule does not make Portia authoritative for either Core value object’s internal identifier syntax.

#### Conservative external fallback

When no reusable authoritative identifier schema is independently available, Portia may apply a conservative structural fallback.

The conceptual schema name is:

```
structurally_safe_external_id
```

It should not be named:

```
universal_id
canonical_id
suite_id
authoritative_id
```

The fallback requires:

* JSON string type;
* at least one character;
* at least one non-whitespace character;
* no control characters;
* no path separators;
* no isolated `.` path segment;
* no isolated `..` path segment;
* and a bounded maximum length.

An initial conservative pattern may be:

```
^[A-Za-z0-9][A-Za-z0-9._-]*$
```

with:

```
maxLength = 128
```

The schema description must state that the rule provides structural and path safety only.

It does not establish that the identifier is valid under the owning authority.

#### Structural fallback limitations

Passing `structurally_safe_external_id` does not establish:

* registration;
* existence;
* uniqueness;
* module ownership;
* class ownership;
* record kind;
* work kind;
* lifecycle;
* contract support;
* or authorization.

Application validation must consult the authoritative contract or resolver where such validation is required.

#### Sibling-module identifiers

Portia must treat sibling-module identifiers as opaque values governed by Core and the originating module.

Portia must not impose Portia prefixes on:

```
sibling module work_id
sibling module record_id
sibling module record_kind
```

Portia must not infer record meaning from an identifier’s text.

For example:

```
assignment_001
```

does not establish:

```
record_kind = assignment
```

The declared `record_kind` and originating module’s public contract remain authoritative.

#### Prefixes do not replace type fields

A prefix may validate one Portia-owned identifier family.

It must not replace an explicit domain discriminator or type field.

For example:

```
evt_example
```

does not eliminate the need for:

```
work_kind = event
```

Likewise:

```
rel_example
```

does not eliminate:

```
record_kind = work_relationship
```

or:

```
record_type = work_relationship
```

Prefixes provide structural validation and diagnostic clarity.

They do not carry the complete record contract.

#### Path-safety validation

Every identifier used as a canonical filesystem path component must satisfy structural path-safety requirements.

Path safety is distinct from domain authority.

For example, Portia may verify that a Core-owned `class_id` is safe to use as a path component while Core remains authoritative for whether that class exists and whether the ID is valid under Core’s contract.

A value must not be used as a path component when it contains:

```
/
\
control characters
isolated .
isolated ..
```

Percent-encoding, escaping, or sanitization must not be used to turn an invalid canonical identifier into an accepted path component.

#### No silent normalization

Ordinary schema validation, application validation, and resolution must not:

* trim whitespace;
* lowercase values;
* uppercase values;
* replace spaces;
* remove punctuation;
* add a prefix;
* remove a prefix;
* truncate values;
* convert numbers to strings;
* convert strings to numbers;
* or generate a replacement identifier.

A malformed identifier must be rejected or reported invalid.

Explicit import or migration tooling may define a traceable mapping from an external source identifier to a newly generated canonical identifier.

Such a mapping is a migration operation rather than silent normalization.

#### Identifier generation

When Portia creates a new canonical identifier, it must generate a value conforming to the applicable Portia-owned identifier schema.

Generated opaque suffixes must not encode:

* student names;
* Actor names;
* allegations;
* classifications;
* dates of birth;
* disability information;
* contact information;
* narrative summaries;
* or other sensitive domain content.

Identifiers should remain opaque and nonsemantic beyond their accepted type prefix.

#### Schema validation versus application validation

Schema validation may establish:

* JSON string type;
* prefix;
* permitted character structure;
* minimum length;
* maximum length;
* and closed reference-object shape.

Schema validation does not establish:

* whether the identifier exists;
* whether it is registered;
* whether it is unique across the required authority;
* whether it belongs to the stated class or module;
* whether it agrees with a containing path;
* whether its target contract is supported;
* or whether the current operation is authorized.

Those checks remain application responsibilities.

#### Existing schema reconciliation

Existing Portia-local schemas named generically:

```
safeId
```

should be replaced or reorganized during Issue #11 implementation according to ownership.

Portia-owned values should use their specific Portia identifier schemas.

Core-owned and sibling-module values should use:

* published authoritative schemas where available; or
* the explicitly nonauthoritative structural fallback.

A generic local `safeId` must not continue to obscure whether Portia or another component owns the identifier contract.

#### Identifier invariants

1. Identifier validation follows contract ownership.
2. Portia-owned identifiers use exact prefix-specific schemas.
3. The initial Portia-owned prefixes are `evt_`, `sup_`, `actr_`, `ep_`, `epr_`, and `rel_`.
4. Portia-owned identifiers permit only ASCII letters, digits, underscores, and hyphens after their accepted prefix.
5. Periods are prohibited in Portia-owned identifiers.
6. Portia-owned identifiers initially use `maxLength = 128`.
7. Every identifier remains a JSON string.
8. Leading zeros and case are preserved.
9. Equality uses exact serialized-string equality.
10. Portia does not silently normalize identifiers.
11. Core remains authoritative for Core-owned identifier syntax.
12. Portia reuses authoritative Core schemas where independently available.
13. Sibling-module identifiers remain opaque to Portia.
14. Structural fallback validation does not claim domain authority.
15. Prefixes do not replace explicit kind or type properties.
16. Path-safety validation is separate from registration and existence.
17. Passing schema validation does not establish target existence or authorization.
18. Import and migration mappings are explicit rather than silent repairs.
19. Opaque identifiers must not encode sensitive domain content.
20. Exact schema dependency organization remains governed by Decision 19.

### 20.7 Shared-schema organization, versioned addressing, and external compatibility

#### Decision

Portia uses:

* independently addressable modular JSON Schemas;
* immutable versioned paths and `$id` values for every new public contract;
* retained legacy locations for the existing Event-family version-1 schemas;
* canonical absolute `$ref` values between Portia-owned public schemas;
* a noncanonical schema catalog for tooling and version dispatch;
* explicit compatibility-adapter schemas for external contracts that do not yet publish canonical JSON Schema resources;
* and offline deterministic schema resolution during tests.

The initial architecture must not assume that another Paper Data Suite repository publishes independently addressable JSON Schemas merely because it exposes an equivalent Python value model or documented JSON mapping.

#### Legacy Event-family schemas

The existing files:

```
schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json
```

remain the canonical version-1 Event-family schemas.

They retain their existing:

* repository paths;
* public `$id` values;
* serialized meanings;
* and version-1 fixtures.

They must not be:

* moved into `schemas/v1/`;
* assigned replacement `$id` values;
* changed to accept version-2 structures;
* converted into redirect schemas;
* or treated as aliases for the latest version.

Their unversioned public locations are preserved as legacy contract identities.

That exception does not establish the naming policy for new schemas.

#### New public schema paths

Every new public Portia schema uses a versioned repository path and a matching versioned canonical `$id`.

The initial path families are:

```
schemas/v1/
schemas/v2/
```

The path version and canonical `$id` version must agree.

For example:

```
schemas/v1/references/roster-student-ref.schema.json
```

has canonical `$id`:

```
https://paper-data-suite.github.io/pds-portia/schemas/v1/references/roster-student-ref.schema.json
```

A reconciled Event version-2 schema is stored at:

```
schemas/v2/event.schema.json
```

with canonical `$id`:

```
https://paper-data-suite.github.io/pds-portia/schemas/v2/event.schema.json
```

A new public schema must not receive an unversioned canonical `$id`.

#### Initial directory organization

The initial schema organization is:

```
schemas/
  event.schema.json
  event-participant.schema.json
  event-participant-role.schema.json

  v1/
    identifiers/
      portia-event-id.schema.json
      portia-support-process-id.schema.json
      portia-actor-id.schema.json
      portia-event-participant-id.schema.json
      portia-event-participant-role-id.schema.json
      portia-work-relationship-id.schema.json
      structurally-safe-external-id.schema.json

    references/
      roster-student-ref.schema.json
      actor-ref.schema.json
      local-record-ref.schema.json
      portia-work-ref.schema.json
      portia-work-record-ref.schema.json
      module-work-record-ref.schema.json

    targets/
      portia-target-ref.schema.json
      support-process-target-ref.schema.json

    snapshots/
      person-display-snapshot.schema.json

    work-relationship.schema.json

  v2/
    event.schema.json
    event-participant.schema.json
    event-participant-role.schema.json

  compatibility/
    pds-core/
      <supported-core-version>/
        module-work-ref.adapter.schema.json
        module-record-ref.adapter.schema.json
        compatibility-lock.json

  schema-catalog.json
  README.md
```

Filenames use lowercase kebab-case.

The compatibility directory contains nonauthoritative adapter resources rather than Portia-native domain contracts.

#### One public contract per file

Every independently reusable public Portia value object receives:

* one schema file;
* one canonical `$id`;
* one documented semantic purpose;
* and one versioned contract identity.

Public reusable contracts must not remain buried inside another public schema’s private `$defs`.

For example:

```
portia_work_record_ref
```

must reference the public schemas for:

```
portia_work_ref
local_record_ref
```

rather than reproducing their complete definitions locally.

A schema may use local `$defs` for helpers that:

* are private to that schema;
* have no independent persisted meaning;
* are not referenced by another public contract;
* and do not establish a separate compatibility boundary.

#### Canonical Portia cross-schema references

Portia-owned public schemas use canonical absolute `$ref` values when referencing another Portia-owned public schema.

For example:

```
"$ref":
  "https://paper-data-suite.github.io/pds-portia/schemas/v1/references/local-record-ref.schema.json"
```

Relative cross-file references are not used as canonical public dependencies.

Local fragment references remain permitted for private helpers:

```
"#/$defs/nonEmptyText"
```

Canonical absolute references separate public contract identity from a validator’s local filesystem layout.

#### No mutable latest or current schema

Portia must not create canonical schema identifiers such as:

```
schemas/latest/
schemas/current/
```

No canonical schema may reference a mutable latest or current URI.

Documentation may identify the currently recommended writer contract.

That documentation is not a schema identity and must not appear as a persisted schema dependency.

Once published, a canonical schema `$id` must retain one stable meaning.

#### Schema catalog

Portia provides a noncanonical tooling file:

```
schemas/schema-catalog.json
```

The name `catalog` is deliberate.

Paper Data Suite Core uses registry terminology for authoritative shared registration and publication infrastructure. Portia’s schema lookup file is not such a registry.

The catalog maps:

```
conceptual contract
schema version
canonical schema $id
local source path
```

For example:

```
{
  "contracts": {
    "event": {
      "1": {
        "schema_id": "https://paper-data-suite.github.io/pds-portia/schemas/event.schema.json",
        "path": "schemas/event.schema.json"
      },
      "2": {
        "schema_id": "https://paper-data-suite.github.io/pds-portia/schemas/v2/event.schema.json",
        "path": "schemas/v2/event.schema.json"
      }
    },
    "work_relationship": {
      "1": {
        "schema_id": "https://paper-data-suite.github.io/pds-portia/schemas/v1/work-relationship.schema.json",
        "path": "schemas/v1/work-relationship.schema.json"
      }
    }
  }
}
```

The catalog may also identify:

```
roster_student_ref
actor_ref
local_record_ref
portia_work_ref
portia_work_record_ref
module_work_record_ref
portia_target_ref
support_process_target_ref
person_display_snapshot
```

The catalog:

* supports validator setup;
* supports record-family and version dispatch;
* supports documentation generation;
* is rebuildable from canonical schemas;
* does not override a schema’s `$id`;
* is not authoritative for record identity;
* is not persisted inside canonical Portia records;
* and is not a Meridian integration contract.

A stale or missing schema catalog does not change the meaning of any canonical schema or instance record.

#### Record-schema dispatch

Canonical records continue to declare:

```
schema_version
```

A validator selects the applicable record schema from:

```
record family
schema_version
```

For Event roots, dispatch uses:

```
record_type = portia_work
work_kind = event
schema_version
```

For child records, dispatch uses:

```
record_type
schema_version
```

An unknown version is:

```
unsupported
```

The validator must not:

* infer version from property names;
* fall back to the latest schema;
* try schemas sequentially until one accepts the instance;
* or reinterpret a legacy record under a newer contract.

#### Shared value-object versioning

Shared reference, target, identifier, and snapshot objects do not gain serialized:

```
schema_version
```

fields.

Their value-object schema version is established through:

* the containing record schema;
* the containing schema’s canonical `$ref`;
* and the referenced shared schema’s canonical `$id`.

This is distinct from:

```
contract_version
```

inside a reference.

`contract_version` identifies the expected public contract of the referenced target.

It does not identify the schema version of the reference value object itself.

#### Current Core integration reality

PDS Core currently exposes strict runtime value models and exact dictionary conversions for:

```
ModuleWorkRef
ModuleRecordRef
```

Portia must not claim that those models have canonical Core JSON Schema `$id` values unless Core actually publishes such resources.

Until official independently addressable Core JSON Schemas exist, Portia uses explicit compatibility-adapter schemas.

The initial adapter resources are:

```
compatibility/pds-core/<supported-core-version>/module-work-ref.adapter.schema.json
compatibility/pds-core/<supported-core-version>/module-record-ref.adapter.schema.json
```

These adapter schemas model the exact serialized shapes accepted by the supported Core implementation.

They are not authoritative Core contracts.

#### Core compatibility-adapter identity

A compatibility adapter uses a Portia-owned canonical `$id` that clearly identifies it as an adapter.

For example:

```
https://paper-data-suite.github.io/pds-portia/schemas/compatibility/pds-core/0.5.0/module-work-ref.adapter.schema.json
```

It must not use or imitate an official Core `$id` that Core has not published.

The adapter’s:

```
title
description
$comment
```

must state that it is:

* a downstream compatibility representation;
* pinned to a particular Core version or commit;
* verified against the actual Core implementation;
* and nonauthoritative outside Portia’s compatibility boundary.

#### Core compatibility lock

Each supported Core adapter set includes:

```
compatibility-lock.json
```

The lock records:

```
core_repository
supported_package_version
source_commit
source_module
source_model
source_documentation
adapter_schema_id
adapter_path
compatibility_test_path
```

Where practical, it should also record:

```
source_blob_sha
adapter_sha256
```

The lock allows reviewers to determine exactly which Core implementation the adapter represents.

Updating an adapter or lock is an explicit dependency change.

#### Core adapter parity tests

Portia must test compatibility adapters against the actual pinned `pds_core` implementation.

For both:

```
ModuleWorkRef
ModuleRecordRef
```

tests must verify that:

1. every adapter-valid fixture is accepted by the corresponding Core validator;
2. every adapter-invalid fixture is rejected by the corresponding Core validator;
3. Core serialization produces the exact expected dictionary shape;
4. dictionary round-trip preserves every accepted value;
5. unknown properties are rejected;
6. required nullable `contract_version` remains present;
7. identifier casing and character restrictions agree;
8. and nested use inside `module_work_record_ref` preserves matching module ownership.

Passing an adapter schema without passing the actual Core validator is insufficient.

The Python implementation remains authoritative until Core publishes a canonical JSON Schema contract.

#### Adoption of future official Core schemas

When Core publishes an independently addressable immutable JSON Schema for a required contract, Portia may adopt it through an explicit dependency decision.

Portia must first confirm:

* the schema represents the same Core value model;
* its `$id` is immutable and version-specific;
* its serialized shape matches the accepted Portia composition;
* its identifier semantics match;
* and it is supported by the declared Core dependency line.

A previously published Portia schema must not be silently edited to replace an adapter `$ref` with a new official Core `$ref`.

After a Portia schema is published, changing its external contract dependency requires:

* a new Portia shared-schema version; or
* another explicit compatibility mechanism that preserves the original schema’s immutable meaning.

If an official Core schema becomes available before the initial Issue #11 schemas are published, Portia may use it directly after compatibility verification.

#### Core package-version boundary

Core package versions and target `contract_version` values are different concepts.

For example:

```
pds-core 0.5.0
```

is a software package version.

A ModuleRecordRef:

```
contract_version = "1"
```

identifies a producer-record contract.

Portia’s compatibility lock records the supported Core software version.

Canonical persisted references continue to carry the target record’s contract version rather than the installed Core package version.

#### Meridian boundary

Portia’s native schema tree and schema catalog are not Meridian’s data-ingestion API.

Meridian must not be required to:

* read arbitrary Portia work-root files;
* resolve Portia’s internal schema catalog;
* depend on Portia’s private compatibility adapters;
* or interpret Portia-native records outside an authorized producer contract.

Portia will later expose privacy-minimized intervention publications through the Core-governed publication boundary.

Those later publication and reporting contracts remain assigned to the applicable Portia publication and reporting issues.

Meridian consumes Core-governed registrations and Publication Records while preserving producer authority and the distinction between:

```
academic information
intervention information
```

Decision 19 does not define or freeze the future Portia publication-manifest schema.

#### No direct Meridian dependency

No Portia `$ref` should point into the Meridian repository as part of Issue #11.

No Meridian schema is required to validate Portia’s native reference, target, relationship, Event, Participant, or Role contracts.

Future shared reporting contracts may introduce explicit dependencies only through later reviewed architecture decisions.

#### Offline deterministic resolution

Automated tests must not retrieve schemas over the network.

Every `$ref` must resolve through:

* the local Portia schema catalog;
* the checked-in Portia schema sources;
* the pinned compatibility-adapter catalog;
* or an explicitly configured immutable external resource.

Tests must fail when:

* a `$ref` cannot be resolved;
* two source files claim the same canonical `$id`;
* a catalog entry disagrees with the schema’s `$id`;
* a compatibility adapter disagrees with its lock;
* an expected Core parity test is missing;
* or a schema references a mutable latest or current contract.

Canonical HTTPS `$id` values identify public contracts.

Local resolver mappings make those contracts available offline.

#### Fixture organization

Fixtures are divided by validation responsibility.

The recommended structure is:

```
tests/
  fixtures/
    schema-valid/
      shared/
      event-v1/
      event-v2/
      event-participant-v1/
      event-participant-v2/
      event-participant-role-v1/
      event-participant-role-v2/
      work-relationship-v1/
      core-compatibility/

    schema-invalid/
      shared/
      event-v1/
      event-v2/
      event-participant-v1/
      event-participant-v2/
      event-participant-role-v1/
      event-participant-role-v2/
      work-relationship-v1/
      core-compatibility/

    application-invalid/
      references/
      targets/
      relationships/
      resolution/
      migrations/
      core-integration/

    migrations/
      event-v1-to-v2/
      event-participant-v1-to-v2/
      event-participant-role-v1-to-v2/
```

Schema-valid fixtures pass structural JSON Schema validation.

Schema-invalid fixtures fail structural validation.

Application-invalid fixtures pass structural validation but fail rules requiring:

* authoritative resolution;
* scope agreement;
* lifecycle reasoning;
* duplicate detection;
* ownership validation;
* Core model validation;
* or cross-record reasoning.

The categories must not be conflated.

#### Required schema tests

Issue #11 automated tests must verify:

1. every public schema declares Draft 2020-12;
2. every new public Portia schema has a versioned canonical `$id`;
3. retained Event-family version-1 schemas keep their existing IDs;
4. every canonical `$id` is unique;
5. path version and `$id` version agree;
6. every catalog entry resolves to the declared schema;
7. every canonical `$ref` resolves offline;
8. no new canonical schema uses `latest` or `current`;
9. valid fixtures pass;
10. schema-invalid fixtures fail for the intended reason;
11. application-invalid fixtures first pass structural validation;
12. version-1 fixtures remain valid;
13. version-1 schemas reject version-2-exclusive forms;
14. version-2 schemas reject legacy forms;
15. migration outputs validate as version 2;
16. shared reference schemas reject unknown properties;
17. required nullable contract-version keys remain present;
18. target arrays reject schema-detectable duplicates;
19. compatibility adapters match their locks;
20. Core adapter-valid fixtures pass actual Core validation;
21. Core adapter-invalid fixtures fail actual Core validation;
22. no Meridian dependency is introduced into native Portia schemas;
23. and generated bundles reproduce the canonical source contracts.

#### Bundled schemas

Tooling may generate bundled or dereferenced schema artifacts for:

* offline consumers;
* release packaging;
* documentation;
* validators without multi-resource resolution;
* or integration testing.

Bundles are derived artifacts.

They do not replace the modular source schemas.

A bundle must:

* be reproducible;
* preserve the canonical identity of embedded resources;
* distinguish Portia-owned schemas from Core compatibility adapters;
* and contain no mutable network dependency.

#### Documentation

Add:

```
schemas/README.md
```

It must explain:

* legacy Event-family version-1 exceptions;
* new versioned path and `$id` policy;
* public versus private schema definitions;
* the schema catalog;
* record-family version dispatch;
* Core compatibility adapters;
* compatibility locking and parity tests;
* offline resolution;
* fixture categories;
* bundle generation;
* and how to add a new public schema version.

ADR 0007 records the architectural rationale and ownership boundary.

It should not duplicate the entire schema catalog.

#### Schema-organization invariants

1. Existing Event-family version-1 schemas retain their current paths and `$id` values.
2. Every new public Portia schema uses a versioned path and canonical `$id`.
3. Each reusable public contract receives its own schema file.
4. Portia-owned cross-schema dependencies use canonical absolute `$ref` values.
5. Private helpers may remain in local `$defs`.
6. Mutable latest and current schema identities are prohibited.
7. `schema-catalog.json` is noncanonical and rebuildable.
8. Record dispatch uses explicit family and `schema_version`.
9. Shared value-object versions are established through schema composition rather than new instance fields.
10. Portia does not assume Core publishes schemas it has not published.
11. Current Core value models are represented through clearly labeled compatibility adapters.
12. Core adapters are pinned and tested against the actual supported Core implementation.
13. Compatibility adapters do not become authoritative Core contracts.
14. Future official Core schemas are adopted explicitly rather than substituted silently.
15. Core package versions remain distinct from target contract versions.
16. Portia’s schema catalog is not Meridian’s ingestion API.
17. Native Portia schemas introduce no direct Meridian dependency.
18. Tests resolve every schema offline.
19. Schema-valid, schema-invalid, application-invalid, migration, and compatibility fixtures remain distinct.
20. Generated bundles are derived rather than canonical.

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

### Relationship representation exclusivity

Application validation must reject or report cases in which the same semantic association is represented canonically through both:

* a specialized embedded field;
* and a Work Relationship record.

Validation must apply the accepted relationship-record threshold and the controlled relationship-type rules.

It must not infer that an association qualifies merely because:

* the endpoints differ;
* the association crosses work or module scope;
* a derived index contains an edge;
* or a reverse lookup returns a matching record.

Where a relationship type overlaps conceptually with a specialized field, the domain contract must identify the sole canonical representation.

Derived projections may expose normalized relationship-like rows, but those rows remain nonauthoritative and must retain the identity of their canonical source.

### Shared reference-resolution validation

Schema validation establishes only the local structure of a reference.

It does not establish:

```
target existence
authoritative resolution
target contract support
target lifecycle
workflow eligibility
authorization
disclosure eligibility
```

Application validation must evaluate accepted references using the shared layered resolution model.

The shared derived resolution states are:

```
resolved
missing
invalid
unsupported
unavailable
```

Target lifecycle and consumer use disposition must be evaluated separately.

Application validation must not treat:

```
resolved
```

as equivalent to:

```
active
usable
authorized
reportable
evidentiary
```

For composite references, validation must preserve the failure stage, including whether failure occurred at:

```
reference
scope_provider
authority
work
record
contract
```

Application validation must use exact authoritative identity and scope.

It must not resolve or repair references through:

* display names;
* display snapshots;
* filename similarity;
* bare local identifiers outside an inherited scope;
* workspace-wide first-match search;
* presumed student identity;
* derived reverse views as sole authority;
* or automatic successor following.

An unknown but structurally valid contract version is unsupported.

A discovered target whose actual contract contradicts the reference is invalid.

A target that cannot be checked because authority or storage is unavailable must not be reported as missing.

Resolved superseded, invalidated, closed, inactive, or historical targets retain their native lifecycle status.

The consuming contract determines whether such targets are usable, historical-only, not usable, review-required, or undetermined.

Resolution must not mutate canonical references, retarget them, update contract versions, create missing records, or change lifecycle state.

Every consuming field must declare its accepted reference family, scope provider, required resolution state, contract-version policy, lifecycle eligibility, use disposition, and failure behavior.

### Historical person display-snapshot validation

Schema validation for `person_display_snapshot` must enforce:

```
required display_name
nonempty non-whitespace display_name
no unknown properties
```

A consuming schema must place `display_snapshot` only as a sibling to:

```
roster_student_ref
actor_ref
```

within a domain wrapper that explicitly permits it.

The snapshot must not appear inside either identity reference.

Each consuming schema must declare whether the snapshot is:

```
required
optional
prohibited
```

Event Participant roster-student and Actor subject branches must continue to require it.

Schema validation must reject snapshot properties such as:

```
identifiers
legal or preferred-name classifications
pronouns
titles
roles
organizations
contact information
lifecycle status
institutional data
notes
allegations
Account or Observation content
private metadata
```

Application validation must ensure that:

1. the snapshot is excluded from identity and duplicate comparisons;
2. resolution never uses the snapshot;
3. current display data is obtained from the authoritative resolved target;
4. historical and current display values remain distinguishable;
5. differing names are presented neutrally;
6. a snapshot shown after failed resolution is labeled as historical;
7. proposed snapshot correction does not silently change identity;
8. active snapshots are not rewritten in place;
9. automatic directory synchronization does not mutate canonical snapshots;
10. and privacy projections may further redact or omit the snapshot for a given audience.

A snapshot must not repair a missing target, select a successor, create an Actor, merge roster identities, establish authorization, or convert an unresolved reference into a resolved one.

### Event-family version and migration validation

Schema validation must treat Event-family versions as separate contracts.

A version-1 record must validate only against its retained version-1 schema.

A version-2 record must validate only against its reconciled version-2 schema.

A validator must select the schema from explicit:

```
schema_version
```

It must not select a schema by inspecting legacy or current property names.

Version-2 validation must reject:

```
flat Event external references
legacy Event supersession references
student_ref
bare Actor-subject actor_id
participant supersession participant_id
Role participant_id
bare Account or Observation basis record_id
Role supersession role_id
```

Application-level migration validation must confirm:

1. the source validates under the declared version-1 contract;
2. the migration mapping matches the record family;
3. canonical path and identity agree before migration;
4. the version-2 candidate preserves domain identity;
5. the candidate validates under the version-2 contract;
6. every newly composed reference resolves or receives its permitted unresolved disposition;
7. inherited scope remains unambiguous;
8. no material domain correction is hidden inside the migration;
9. creation provenance remains unchanged unless an explicit correction contract permits otherwise;
10. update attribution and chronology are valid;
11. related multi-record changes are atomic or recoverable;
12. and the original version remains recoverable or auditable under the shared migration contract.

Reference resolution must not migrate a record automatically.

An unsupported version must be reported as unsupported rather than interpreted as version 1 or version 2.

Tests must validate version-1 and version-2 fixture sets independently and must include invalid fixtures proving that each version rejects the other version’s exclusive serialization.

### Identifier ownership and path-safety validation

Schema validation must apply identifier rules according to contract ownership.

Portia-owned identifier schemas must enforce their accepted prefixes:

```
evt_
sup_
actr_
ep_
epr_
rel_
```

and their applicable structural and maximum-length constraints.

Core-owned identifiers must use published Core schemas where independently available.

When no reusable authoritative schema is available, Portia may apply only the explicitly nonauthoritative:

```
structurally_safe_external_id
```

fallback.

Application validation must not treat successful structural fallback validation as proof that an external identifier is registered, exists, is unique, or belongs to the declared module or class.

Application validation must also confirm, where applicable:

1. canonical path and persisted identifier agreement;
2. Core class existence;
3. roster student existence under the exact source class;
4. Actor existence in the Portia Actor Directory;
5. work existence under the exact module and class;
6. child-record existence under the exact owning work;
7. identifier uniqueness within its authoritative scope;
8. declared work-kind and record-kind agreement;
9. nested module-ID agreement;
10. supported target contract version;
11. and authorization for the attempted operation.

Validation must preserve exact serialized identifier values.

It must reject rather than silently:

```
trim
case-fold
truncate
add prefixes
remove prefixes
replace characters
coerce numbers and strings
```

Identifiers used in canonical paths must be rejected when structurally unsafe for path use.

Path escaping or sanitization must not create a second canonical spelling for one identifier.

Tests must distinguish:

* valid Portia-prefixed identifiers;
* wrong-prefix Portia identifiers;
* malformed structural fallback identifiers;
* path-unsafe values;
* overlong values;
* leading-zero strings;
* case-distinct values;
* and structurally valid external identifiers that remain application-invalid.

Tests must prove that a period-containing value is rejected by every Portia-owned identifier schema even when the prefix and all remaining characters are otherwise valid.

### Schema identity, dependency, and compatibility validation

Schema validation tooling must treat every canonical `$id` as an immutable public contract identity.

The retained Event-family version-1 schemas must remain available at their existing paths and IDs.

Every new public Portia schema must use a versioned path and matching versioned `$id`.

Automated validation must reject:

```
duplicate canonical $id values
path-version and $id-version disagreement
mutable latest or current schema references
unresolved canonical $ref values
catalog and source-schema disagreement
public reusable contracts hidden only in private $defs
```

The noncanonical:

```
schemas/schema-catalog.json
```

must map record family and schema version to the correct canonical schema and local source path.

A stale or missing catalog must not alter canonical schema meaning.

#### Core compatibility validation

Until Core publishes official independently addressable JSON Schemas for required contracts, Portia must validate its compatibility adapters against the actual pinned Core implementation.

For each adapter, automated tests must confirm:

1. the compatibility lock identifies the supported Core version or commit;
2. the adapter `$id` clearly belongs to Portia’s compatibility namespace;
3. the adapter does not impersonate an unpublished Core `$id`;
4. every adapter-valid fixture is accepted by Core’s runtime validator;
5. every adapter-invalid fixture is rejected by Core’s runtime validator;
6. Core serialization matches the expected exact dictionary shape;
7. round-trip conversion preserves the accepted value;
8. unknown fields are rejected;
9. required nullable fields remain present;
10. and module-ownership composition rules remain valid.

A fixture that passes only the adapter schema is not sufficient evidence of Core compatibility.

Application and integration tests must invoke the pinned Core implementation.

#### External dependency changes

Changing:

```
supported Core package line
Core source commit
compatibility adapter
compatibility lock
official external schema dependency
```

requires explicit review.

A published Portia schema must not silently acquire a different external contract meaning.

If a dependency change alters an existing public Portia schema’s interpretation, the change requires a new Portia schema version.

#### Meridian isolation

Native Portia schema validation must not require:

```
Meridian source code
Meridian schemas
Meridian runtime services
Meridian report definitions
```

Portia-to-Meridian compatibility is established later through Core-governed producer publications, not through direct validation of Portia’s canonical work-root records.

Tests should fail if a native Issue #11 Portia schema introduces an undeclared direct dependency on Meridian.

#### Offline resolution

Tests must resolve all schemas and compatibility resources locally.

Network schema retrieval is prohibited in automated validation.

The resolver must map canonical `$id` values to:

* checked-in Portia schemas;
* retained legacy schemas;
* pinned compatibility adapters;
* or explicitly supplied immutable external resources.

Failure to resolve any `$ref` is a test failure rather than a reason to skip validation or retrieve an arbitrary latest resource.

#### Fixture classification

Test infrastructure must preserve the distinction among:

```
schema-valid
schema-invalid
application-invalid
migration
compatibility
```

An application-invalid fixture must first pass its structural schema.

A compatibility fixture must additionally prove agreement with the external implementation it represents.

Migration fixtures must identify both the source and destination schema versions.

#### Catalog integrity

Catalog tests must confirm that:

1. every catalog path exists;
2. every catalog schema ID matches the file’s `$id`;
3. every public schema appears at most once per conceptual contract and version;
4. retained legacy schemas map to version 1;
5. reconciled Event-family schemas map to version 2;
6. compatibility adapters are identified separately from canonical Portia contracts;
7. and no catalog entry claims that a compatibility adapter is an authoritative Core schema.

### Relationship source and storage agreement

Application validation must confirm that every canonical Work Relationship is stored beneath the Portia work root identified by its `source`.

The containing work and `source` must agree exactly on:

```
module_id
class_id
work_id
work_kind
contract_version
```

The source module must be:

```
portia
```

A mismatch must be reported as a storage-integrity failure.

Validation must not repair the mismatch by:

* moving the relationship automatically;
* replacing the source with the containing work;
* selecting the newer value;
* selecting the value whose ID prefix appears correct;
* or searching for another work root.

Validation must also reject:

* a relationship owned by a work that is neither endpoint;
* an inverse canonical copy stored beneath the target;
* a relationship type whose formal direction disagrees with the source and target;
* and a sibling-module record used as the canonical source of a Portia Work Relationship.

Reverse indexes and target-side navigation must retain the canonical source-owned relationship ID and must not become alternate storage authorities.

### Relationship direction and inverse validation

Application validation must resolve every canonical Work Relationship through the controlled relationship-type definition.

Validation must confirm:

```
recognized relationship type
permitted source work kind
permitted target endpoint kind
correct source-to-target orientation
self-reference policy
multiplicity policy
no prohibited inverse canonical duplicate
```

A relationship record must not persist:

```
direction
inverse_relationship_type
inverse_label
reverse_label
```

as independently editable canonical fields.

Target-side wording must be derived from the controlled type definition.

Validation must not repair invalid orientation by:

* swapping source and target;
* replacing the relationship type with a guessed inverse;
* moving the record beneath the other endpoint;
* selecting the endpoint whose kind appears more plausible;
* or creating a second inverse record.

A derived reverse view must preserve the canonical relationship ID, source, relationship type, target, lifecycle state, and source-owned storage scope.

A missing or stale reverse view must be rebuilt or reported.

It must not become an alternate source of canonical relationship direction.

### Initial relationship-type and endpoint validation

Application validation must initially recognize exactly one Work Relationship type:

```
draws_context_from
```

For this type, validation must confirm that:

1. the source is a complete `portia_work_ref`;
2. the source module is `portia`;
3. the source work kind is `event` or `support_process`;
4. the target is a complete `portia_work_ref`;
5. the target module is `portia`;
6. the target work kind is `event`;
7. the source and target canonical work identities differ;
8. the containing work equals the source;
9. no equivalent active relationship already exists;
10. no specialized field already owns the intended association;
11. and any relationship-specific detail remains within the noncausal contextual meaning of the type.

Validation must reject:

```
unrecognized relationship types
vague fallback types
Event-to-Support Process orientation
Support Process-to-Support Process orientation
child-record endpoints
sibling-module endpoints
student or Actor endpoints
self-reference
inverse canonical duplicates
duplicate active source-type-target edges
```

Validation must not reinterpret an unrecognized type as:

```
draws_context_from
```

It must not downgrade a stronger unsupported claim into contextual association automatically.

A creation workflow may invite the user to restate the intended meaning, but canonical creation requires an intentional selection of the accepted type.

### Work Relationship envelope and storage validation

Schema validation must enforce the local Work Relationship structure, including:

```
schema_version = "1"
record_type = work_relationship
module_id = portia
relationship_id using the rel_ prefix
status in the accepted structural vocabulary
relationship_type = draws_context_from
direct portia_work_ref source
direct portia_work_ref target
required structured creation_source
required created_at and updated_at
required created_by and updated_by
optional bounded detail
rejection of unknown properties
```

The schema must reject endpoint wrappers, child-record endpoints, sibling-module endpoints, generic basis fields, separate owner fields, per-record direction fields, and inverse relationship fields.

Application validation must additionally confirm:

1. the canonical file path matches the top-level `class_id`, `work_id`, and `relationship_id`;
2. the containing Portia work exists;
3. the containing work is the complete `source`;
4. the source work kind and contract version agree with the canonical source work;
5. the target Event exists;
6. the target work kind and contract version agree with the canonical target work;
7. the source and target canonical identities differ;
8. the endpoint matrix for `draws_context_from` is satisfied;
9. no equivalent active semantic edge already exists;
10. the relationship does not duplicate a specialized field;
11. the creation source resolves where resolution is required;
12. timestamps are chronological;
13. immutable fields have not changed;
14. and any `detail` remains within the type’s neutral contextual meaning.

Application validation must not repair disagreement by:

* replacing the top-level scope with the source;
* replacing the source with the containing path;
* moving the file automatically;
* changing an endpoint contract version silently;
* swapping source and target;
* converting a child-record endpoint into its parent work;
* stripping unsupported basis fields and accepting the remainder;
* or rewriting a stronger relationship claim as `draws_context_from`.

A source, target, type, or owner-scope correction requires a new canonical relationship record under the lifecycle and supersession contract.

### Work Relationship lifecycle and supersession validation

Application validation must enforce the permitted Work Relationship lifecycle:

```
proposed → active
proposed → invalidated
active → invalidated
active → superseded
```

The following statuses are terminal:

```
invalidated
superseded
```

Validation must reject every unsupported transition.

Direct creation as active is permitted only for an explicit reviewed digital operation whose endpoints, ownership, type, detail, provenance, and duplicate state have been fully validated.

Paper-derived, imported, automated, unresolved, ambiguous, incomplete, and unreviewed relationships must begin proposed.

Activation validation must confirm:

1. source and target resolution;
2. supported endpoint contract versions;
3. exact source and containing-work agreement;
4. valid endpoint orientation;
5. non-self-reference;
6. no equivalent active semantic edge;
7. no conflicting specialized representation;
8. valid creation provenance;
9. neutral type-conforming detail;
10. and explicit local-operator confirmation.

Invalidation must preserve a controlled reason in the shared lifecycle-transition history.

Ordinary relationship removal must invalidate the record rather than delete it.

A material correction to:

```
source
target
relationship_type
owner scope
active detail
```

requires a new relationship ID.

A successor’s `supersedes` entries must:

* use complete `portia_work_record_ref` values;
* identify Work Relationship records with contract version `"1"`;
* use a controlled supersession reason;
* contain detail when the reason is `other`;
* contain no duplicate predecessors;
* prohibit self-reference;
* and form no supersession cycle.

A prior active relationship must not become superseded until the successor becomes active.

Successor activation and predecessor supersession must occur atomically or through a recoverable staged operation.

A proposed relationship’s detail may be edited in place.

Active detail must not be rewritten in place.

Application validation must reject hard deletion of valid committed canonical Work Relationships.

Endpoint lifecycle changes and endpoint contract-version drift must not silently alter relationship status, references, ownership, or storage.

## 22. Audit Findings Requiring Explicit Decisions

The audit does not support writing schemas before the following decisions are made.

### Decision 1: exact `roster_student_ref` shape — Resolved

Portia will use an identity-only Roster Student Reference:

```json
{
  "class_id": "eng10_p2_2026",
  "student_id": "stu_1001"
}
```

The reusable serialized property name is:

```text
roster_student_ref
```

A historical display snapshot is stored as a sibling field when required by the containing record contract.

The reference excludes display information, school year, work identity, module identity, and contract-version metadata.

Reference equality is exactly:

```text
class_id + student_id
```

The Event Participant roster-student subject will eventually rename its current `student_ref` field to `roster_student_ref`.

See Section 13.1 for the complete contract.

### Decision 2: exact `actor_ref` shape — Resolved

Portia will use an identity-only Actor Reference:

```json
{
  "actor_id": "actr_counselor_001"
}
```

The reusable serialized property name is:

```text
actor_ref
```

A historical display snapshot is stored as a sibling field when required by the containing record contract.

The Actor Reference excludes:

```text
display information
Actor type
role labels
title
status
contact information
class and work context
contract-version metadata
```

Reference equality is exactly:

```text
actor_id
```

The current Event Participant Actor subject will eventually replace its direct `actor_id` property with the nested `actor_ref` value:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_counselor_001"
  },
  "display_snapshot": {
    "display_name": "Riley Thompson"
  }
}
```

For Event Participants, `display_snapshot` remains required.

Other containing record contracts must explicitly declare the snapshot as required, optional, or prohibited.

Roster students remain represented exclusively through `roster_student_ref`.

Descriptive and unknown people do not receive Actor References without a deliberate reviewed identity-resolution operation.

See Section 13.2 for the complete contract.

### Decision 3: exact `local_record_ref` contract — Resolved

Portia will use a typed, version-aware Local Record Reference for references to canonical records inside the containing record’s own Portia work root.

The exact shape is:

```json
{
  "record_kind": "account",
  "record_id": "acct_example",
  "contract_version": "1"
}
```

The required `contract_version` value may be `null` only when the target record kind does not yet expose an accepted public record-contract version.

The reference inherits:

```text
module_id
class_id
work_id
```

from its containing canonical record and must not repeat that scope.

The reusable nested property name is:

```text
record_ref
```

Domain-specific wrappers remain permitted and supply relationship meaning.

For example:

```json
{
  "kind": "account_ref",
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": "1"
  }
}
```

Event Participant and Role supersession also retain their controlled reason-bearing wrappers while using nested `record_ref` identity objects.

Decision 7 subsequently replaces the Role’s direct `participant_id` with a required singular Event Participant `target` containing `local_record_ref`. Decision 3 remains authoritative for the nested record-reference contract.

See Section 13.3 for the complete contract.

### Decision 4: exact `portia_work_ref` contract — Resolved

Portia will use a complete, typed, version-aware Portia Work Reference for references to Events and Support Processes outside the containing record’s own work root.

The exact shape is:

```
{
  "module_id": "portia",
  "class_id": "eng10_p2_2026",
  "work_id": "evt_example",
  "work_kind": "event",
  "contract_version": "1"
}
```

Every Portia Work Reference contains exactly:

```
module_id
class_id
work_id
work_kind
contract_version
```

The canonical target-work identity is:

```
module_id + class_id + work_id
```

`work_kind` identifies the expected Portia work contract.

`contract_version` identifies the expected public version of that contract.

The `contract_version` key is always required and may be `null` only when the referenced work kind does not yet expose an accepted public work-contract version.

New references to Events should use:

```
"1"
```

The reference does not inherit scope from its containing record.

Cross-class and cross-year references preserve the target work’s original owning class and do not duplicate or relocate canonical work.

A containing field may use the reference directly when that field supplies complete relationship meaning.

Event `supersedes` entries and Work Relationship endpoints will use Portia Work Reference values directly.

The reusable nested property name is:

```
work_ref
```

when a domain-specific wrapper is necessary.

See Section 13.4 for the complete contract.

### Decision 5: exact complete Portia record reference — Resolved

Portia will use a composed, complete Portia Work Record Reference when one canonical Portia record refers to a canonical child record inside another Portia work root.

The exact shape is:

```
{
  "work_ref": {
    "module_id": "portia",
    "class_id": "eng10_p5_2026",
    "work_id": "evt_example",
    "work_kind": "event",
    "contract_version": "1"
  },
  "record_ref": {
    "record_kind": "account",
    "record_id": "acct_example",
    "contract_version": "1"
  }
}
```

The reusable serialized property name is:

```
work_record_ref
```

when a domain-specific wrapper is required.

The contract composes the accepted:

```
portia_work_ref
local_record_ref
```

contracts rather than defining a third flattened reference convention.

Within the composed reference, the sibling `work_ref` is the sole work-scope provider for `record_ref`.

The canonical target-record identity is:

```
work_ref.module_id
+ work_ref.class_id
+ work_ref.work_id
+ record_ref.record_kind
+ record_ref.record_id
```

The two nested contract versions remain distinct:

```
work_ref.contract_version
record_ref.contract_version
```

They identify the expected work and record contracts respectively.

A Portia Work Record Reference is used only when the target record’s work scope cannot be inherited from the containing canonical record.

Same-work references continue to use `local_record_ref` where permitted.

References to a Portia Event or Support Process as a whole continue to use `portia_work_ref`.

References to sibling-module records use `module_work_record_ref`, not this contract.

See Section 13.5 for the complete contract.

### Decision 6: exact `module_work_record_ref` contract — Resolved

Portia will use a composed Module Work Record Reference for complete Core-qualified references to typed module-owned records.

The exact shape is:

```
{
  "work_ref": {
    "module_id": "quillan",
    "class_id": "eng10_p2_2026",
    "work_id": "assignment_work_001"
  },
  "record_ref": {
    "module_id": "quillan",
    "record_kind": "assignment",
    "record_id": "assignment_001",
    "contract_version": "1"
  }
}
```

The reusable serialized property name is:

```
module_work_record_ref
```

The contract composes Core’s exact:

```
ModuleWorkRef
ModuleRecordRef
```

value objects.

The following values must match exactly:

```
work_ref.module_id
record_ref.module_id
```

The repeated module ID is intentional and preserves both exact Core values.

The canonical target-record identity is:

```
work_ref.module_id
+ work_ref.class_id
+ work_ref.work_id
+ record_ref.record_kind
+ record_ref.record_id
```

The required:

```
record_ref.contract_version
```

field identifies the expected public record contract but does not create a separate canonical record.

The contract is structurally module-neutral.

Within ordinary Portia-native domain records:

* same-work Portia records use `local_record_ref`;
* cross-work Portia records use `portia_work_record_ref`;
* and records owned by another PDS module use `module_work_record_ref`.

At suite-neutral boundaries, such as publication, registry integration, manifest provenance, or cross-module interchange, the Core-qualified pair may also identify a Portia-owned record.

A Core Publication Record retains its own Core-owned serialization through:

```
work
source_record
```

Portia does not require Core to use the `module_work_record_ref` wrapper.

The Module Work Record Reference does not establish:

```
publication
reportability
authorization
Academic Work Registration
Grade eligibility
Meridian report inclusion
```

Those require separate Core, producer, and Meridian contracts.

The Event schema’s provisional flat `instructional_context.external_refs` shape will eventually be replaced by this composed contract.

See Section 13.6 for the complete contract.

### Decision 7: exact Event target contract — Resolved

Portia will use a closed, discriminated `portia_target_ref` family for records that explicitly declare what part of an Event they apply to.

The initial target kinds are:

```
event
event_participant
event_participants
```

An Event-level target has the exact shape:

```
{
  "kind": "event"
}
```

It identifies the containing Event as a whole.

It does not target every Event Participant.

A singular Event Participant target has the exact shape:

```
{
  "kind": "event_participant",
  "record_ref": {
    "record_kind": "event_participant",
    "record_id": "ep_example",
    "contract_version": "1"
  }
}
```

The nested `record_ref` conforms to `local_record_ref`.

It targets the canonical Event Participant record—not the underlying roster student, Actor, or real-world person independently of the Event.

A plural Event Participant target has the exact shape:

```
{
  "kind": "event_participants",
  "targets": [
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_one",
        "contract_version": "1"
      }
    },
    {
      "kind": "event_participant",
      "record_ref": {
        "record_kind": "event_participant",
        "record_id": "ep_two",
        "contract_version": "1"
      }
    }
  ]
}
```

A participant set contains at least two singular participant targets.

A one-participant application uses the singular branch.

Duplicate canonical participant targets are prohibited even when their contract versions differ.

Participant-set order has no domain meaning, and canonical serialization is deterministic.

Several selected participants do not create a synthetic Group or imply identical involvement, responsibility, evidence, Response, or Outcome.

The shared target family does not authorize every target branch for every record.

Each consuming schema must explicitly define:

```
target requirement
permitted target kinds
target cardinality
lifecycle eligibility
plural-target meaning
```

Target omission creates no undocumented default.

One target value cannot combine Event-level and participant-level application.

The Event Participant Role will replace its direct:

```
participant_id
```

with a required:

```
target
```

using only the singular Event Participant branch.

One Role continues to apply to exactly one Event Participant.

The target contract remains distinct from:

```
source
basis
evidence
attribution
provenance
subject identity
relationship endpoints
```

The initial `portia_target_ref` family is Event-local.

Decision 8 subsequently defines the separate support_process_target_ref family without changing the Event-local target contract accepted here.

See Section 13.7 for the complete contract.

### Decision 8: exact Support Process target contract — Resolved

Portia will use a separate, closed, discriminated `support_process_target_ref` family for records that explicitly declare what part of a Support Process they apply to.

The initial target kinds are:

```
support_process
support_process_participant
support_process_participants
```

A whole-process target has the exact shape:

```
{
  "kind": "support_process"
}
```

It identifies the containing Support Process as a whole.

It does not target every participant, recipient, provider, linked Event, Support, Intervention, implementation occurrence, Follow-Up, or Outcome.

A singular Support Process Participant target has the exact shape:

```
{
  "kind": "support_process_participant",
  "record_ref": {
    "record_kind": "support_process_participant",
    "record_id": "spp_example",
    "contract_version": null
  }
}
```

The nested `record_ref` conforms to `local_record_ref`.

It identifies the participant’s canonical connection to the containing Support Process rather than directly targeting the underlying roster student, Actor, or real-world person.

The participant `contract_version` is initially null because the public Support Process Participant contract remains deferred to the dedicated Support Process issue.

After that contract is accepted, newly created references should identify its supported version.

A plural Support Process Participant target has the exact shape:

```
{
  "kind": "support_process_participants",
  "targets": [
    {
      "kind": "support_process_participant",
      "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_one",
        "contract_version": null
      }
    },
    {
      "kind": "support_process_participant",
      "record_ref": {
        "record_kind": "support_process_participant",
        "record_id": "spp_two",
        "contract_version": null
      }
    }
  ]
}
```

A participant set contains at least two singular targets.

A one-participant application uses the singular branch.

Duplicate canonical participant targets are prohibited even when their contract versions differ.

Participant-set order has no domain meaning, and canonical serialization is deterministic.

Several selected participants do not create a synthetic Group or imply identical need, role, eligibility, Support, Intervention, implementation, Follow-Up, or Outcome.

Participant roles do not belong inside target references.

Recipient, provider, implementation-subject, coordinator, observer, and other role meanings remain part of the later Support Process participant architecture.

The target identifies which participant a record applies to.

It does not identify why that participant is relevant.

Provider identity remains separate from target identity.

A provider must not be inferred from a target, and a target must not be inferred from a provider.

Event Participants do not belong inside the local Support Process target family.

A Support Process record referring to an Event Participant must use a complete `portia_work_record_ref` through a separately named field with explicit domain meaning.

Each consuming Support Process record must define:

```
target requirement
permitted target kinds
target cardinality
participant-role eligibility
participant lifecycle eligibility
plural-target meaning
```

Target omission creates no undocumented default.

The `support_process_target_ref` family establishes the existence of canonical Support Process Participant identity and the shared targeting structure.

It does not finalize the complete Support Process Participant, participant-role, recipient, provider, Support, Intervention, implementation, or fidelity models.

Those remain responsibilities of the dedicated Support Process issue.

See Section 13.8 for the complete contract and Section 17 for the consolidated targeting rules.

### Decision 9: relationship-record threshold — Resolved

Portia will apply a three-part semantic-independence test before representing an association as a separate canonical Work Relationship.

A Work Relationship is appropriate only when:

1. no accepted specialized field or canonical record fully owns the association’s meaning;
2. the association is itself a durable Portia domain fact;
3. and at least one independent-management condition applies.

Independent-management conditions include:

```
independent lifecycle or status
independent creation provenance
independent review
independent correction
independent invalidation
independent supersession
relationship-specific detail
direct referenceability
independent audit or navigation
meaning that neither endpoint can fully own
```

All three threshold requirements must be satisfied.

Scope alone does not determine representation.

An association may remain embedded even when it is:

```
cross-work
cross-class
cross-year
cross-module
```

A same-work association may qualify as a canonical relationship when it has independent domain meaning and management.

Specialized accepted contracts take precedence over the generic Work Relationship model.

The generic relationship model must not replace or duplicate:

```
target
subject
basis
observer
recipient
owner
provider
parent-work identity
creation provenance
source-record provenance
supersedes
successor_of
```

An embedded reference remains appropriate when the containing canonical record completely owns the association’s meaning, lifecycle, provenance, detail, and correction behavior.

A canonical Work Relationship is appropriate when the association itself requires durable identity and independent management.

Likely qualifying examples include:

* a Support Process explicitly connected to an Event;
* an Event explicitly related to another Event outside supersession;
* a durable Support Process-to-Support Process association outside specialized succession fields;
* and another cross-work or cross-module association with its own provenance, lifecycle, review, correction history, or relationship-specific detail.

The same semantic association must not be stored canonically both as an embedded field and as a Work Relationship.

Derived projections may expose embedded associations in relationship-like views, but those projections remain nonauthoritative.

Changing an association from embedded representation to a canonical relationship—or the reverse—requires an explicit schema and migration decision.

Relationship identity is established for independent Portia domain meaning.

It is not created merely for:

```
reverse lookup
dashboards
timelines
reports
query optimization
graph uniformity
```

Relationship identity also does not establish authorization, disclosure eligibility, or Meridian report inclusion.

See Section 18.1 for the complete threshold.

### Decision 10: canonical Work Relationship ownership — Resolved

Every canonical Portia Work Relationship is owned by its semantic source work.

The normative invariant is:

```
containing work identity = source work identity
```

The relationship is stored beneath the source Portia work root.

The source work owns:

```
creation
relationship-specific detail
lifecycle transitions
correction
invalidation
supersession
canonical retention management
```

The target endpoint does not store an independently editable reverse copy.

The source must be a complete:

```
portia_work_ref
```

identifying one Portia Event or Support Process.

The source:

```
module_id
```

must equal:

```
portia
```

Portia does not store a canonical Work Relationship whose source is a sibling-module work or record.

A sibling-module record may be a target when the relationship type and domain contract permit it.

The Work Relationship does not persist a separate:

```
owner
owner_ref
owning_work_ref
```

field.

Ownership is already established by:

* canonical storage location;
* containing work scope;
* and the required source endpoint.

Every relationship type is defined in the direction:

```
source --relationship_type--> target
```

The relationship type’s formal direction must agree with storage ownership.

A relationship must not be stored beneath one work while naming another work as its semantic source.

When a Support Process records associations with several Events, it owns one source-to-target relationship for each Event.

It does not own a third-party relationship whose semantic endpoints are two Events.

For Event-to-Event relationships, the controlled relationship type determines which Event is the semantic source and owner.

Ownership must not be selected through:

```
lexical ID order
filesystem order
current interface context
load order
arbitrary left-right placement
```

A symmetric-looking relationship still receives exactly one canonical source and target.

Any genuinely symmetric relationship type must define a deterministic orientation rule.

Portia must not create two inverse records to simulate symmetry.

The target stores no canonical reverse field.

Reverse navigation, histories, dashboards, timelines, and reports are derived from the source-owned record.

A target-side workflow may request relationship creation, but the canonical record must be written beneath the semantic source work.

Source ownership does not transfer authority over the target.

The source cannot mutate, retarget, or change the lifecycle of the target record.

The target’s originating work or module remains authoritative for the target itself.

Application validation must confirm:

```
containing work = source
source module = portia
source kind permitted by relationship type
target kind permitted by relationship type
source-target orientation matches relationship type
no third-party ownership
no inverse canonical duplicate
```

A source/storage mismatch is a storage-integrity failure and must not be repaired through inference.

See Section 18.2 for the complete ownership contract.

### Decision 11: Work Relationship direction and reverse semantics — Resolved

Every canonical Portia Work Relationship expresses one directed assertion:

```
source --relationship_type--> target
```

The relationship record persists only the canonical directional:

```
relationship_type
```

It does not persist per-record:

```
direction
inverse_relationship_type
reverse_relationship_type
inverse_label
reverse_label
```

Every controlled relationship type must define:

```
source meaning
target meaning
permitted source work kinds
permitted target endpoint kinds
canonical source-to-target description
derived target-side wording
self-reference policy
multiplicity and duplicate policy
```

Relationship-type codes are stable, lowercase, snake_case, and semantically directional.

The exact initial vocabulary remains a later decision.

Derived inverse wording exists for target-side navigation and presentation only.

It:

* is nonauthoritative;
* is not independently editable;
* does not create another relationship ID;
* does not create another canonical record;
* does not affect relationship equality;
* and does not change ownership.

A reverse projection must preserve the canonical:

```
relationship_id
source
relationship_type
target
lifecycle state
source-owned storage scope
```

It may add target-side display wording without inverting canonical state.

A missing reverse projection must not cause Portia to create an inverse relationship record.

For a directed type:

```
A --type--> B
```

is not equal to:

```
B --type--> A
```

Reversing endpoints changes the assertion, owner, storage root, endpoint eligibility, and canonical relationship identity.

Portia must not repair invalid direction by silently swapping endpoints or guessing an inverse type.

Changing display wording without changing the normative type meaning is a presentation-contract revision.

Changing the canonical relationship type is a semantic correction and requires the accepted lifecycle or supersession process.

The initial Work Relationship vocabulary contains no symmetric relationship types.

Generic symmetric types such as:

```
related_to
associated_with
connected_to
```

are not accepted as foundation-level fallbacks.

A future symmetric type requires an explicit architectural decision defining:

```
exact symmetric meaning
endpoint eligibility
deterministic canonical orientation
one canonical owner
order-independent duplicate normalization
reverse display behavior
self-reference policy
privacy implications
```

Even a future symmetric relationship is stored as one canonical source-target record.

It must not be duplicated in both directions.

Self-reference is prohibited by default and may be permitted only by an explicit relationship-type contract.

Relationship wording must not imply unsupported:

```
causation
proof
blame
responsibility
credibility
diagnosis
service authorization
institutional approval
```

Application validation must confirm recognized type, endpoint compatibility, formal orientation, self-reference policy, multiplicity, and absence of prohibited inverse duplicates.

See Section 18.3 for the complete direction and reverse-semantics contract.

### Decision 12: initial controlled Work Relationship vocabulary — Resolved for the initial foundation

The initial Portia Work Relationship vocabulary contains exactly one type:

```
draws_context_from
```

Its normative source-to-target meaning is:

> The source Portia work explicitly uses the target Event as contextual information in understanding, documenting, reviewing, or managing the source work.

The source must be a complete:

```
portia_work_ref
```

whose:

```
module_id = portia
```

and whose:

```
work_kind
```

is one of:

```
event
support_process
```

The target must be a complete:

```
portia_work_ref
```

whose:

```
module_id = portia
work_kind = event
```

The accepted endpoint orientations are therefore:

```
Event --draws_context_from--> Event
Support Process --draws_context_from--> Event
```

The following orientations are not accepted:

```
Event --draws_context_from--> Support Process
Support Process --draws_context_from--> Support Process
```

The type does not initially support:

```
child-record targets
sibling-module targets
roster-student targets
Actor targets
participant targets
```

The source work owns and stores the relationship.

The target stores no editable reverse copy.

The derived target-side wording is:

```
provides context to
```

That wording is nonauthoritative and is not persisted per relationship.

The relationship records explicit contextual use.

It does not establish:

```
causation
initiation
proof
responsibility
credibility
Classification
Determination authority
eligibility
service authorization
recurrence
effectiveness
outcome attribution
```

Self-reference is prohibited.

For one source and one target, Portia permits at most one equivalent active:

```
draws_context_from
```

relationship.

The initial active semantic key is:

```
source canonical work identity
+ draws_context_from
+ target canonical work identity
```

One relationship record identifies one source-target pair.

Several target Events require several independently managed relationship records.

The type must not replace specialized:

```
target
basis
instructional_context
supersedes
successor_of
source-record provenance
```

contracts.

The initial vocabulary does not accept vague fallback types such as:

```
related_to
associated_with
linked_to
connected_to
other
```

It also defers stronger or more domain-specific types such as:

```
initiated_by
caused_by
follows_up_on
clarifies
duplicates
recurs_after
coordinates_with
resulted_in
```

A future relationship type requires an explicit contract defining its normative meaning, endpoint matrix, ownership, direction, inverse wording, multiplicity, lifecycle, evidentiary limits, privacy rules, and migration consequences.

Future vocabulary expansion must not reinterpret existing `draws_context_from` records.

See Section 18.4 for the complete initial vocabulary and endpoint matrix.

### Decision 13: Work Relationship endpoint and canonical envelope — Resolved

The initial Work Relationship uses direct work-level endpoints.

Both:

```
source
target
```

are complete:

```
portia_work_ref
```

objects.

No separate serialized:

```
relationship_endpoint
endpoint_kind
kind + work_ref wrapper
```

contract is introduced.

The initial endpoint family supports only:

```
Portia work → Portia work
```

For:

```
draws_context_from
```

the endpoint matrix remains:

```
source.work_kind = event | support_process
target.work_kind = event
```

Child records, sibling-module records, students, Actors, and participant records are not valid initial endpoints.

The canonical Work Relationship envelope requires:

```
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

It may additionally contain: 
    detail 
    supersedes 
    
The `supersedes` field appears only on a successor Work Relationship and follows Decision 14. Unknown properties are prohibited.

The canonical constants are:

```
schema_version = "1"
record_type = "work_relationship"
module_id = "portia"
relationship_type = "draws_context_from"
```

The canonical domain-specific identifier is:

```
relationship_id
```

using the recommended form:

```
rel_<opaque-id>
```

The canonical record does not contain a top-level generic:

```
record_id
```

When referenced through a shared record-reference contract, the Work Relationship is identified as:

```
record_kind = work_relationship
record_id = <relationship_id>
contract_version = "1"
```

The canonical storage location is:

```
classes/<class_id>/modules/portia/work/<work_id>/
  records/work_relationship/<relationship_id>.json
```

The top-level:

```
class_id
work_id
```

must identify the containing source work.

The filename stem must equal:

```
relationship_id
```

The containing path, top-level scope, and complete source reference must agree exactly.

The source:

```
module_id
```

must equal:

```
portia
```

The top-level relationship record uses:

```
schema_version = "1"
```

It does not persist a redundant top-level:

```
contract_version
```

The source and target work references retain their own required:

```
contract_version
```

values.

The structural status vocabulary is:

```
proposed
active
invalidated
superseded
```

Decision 14 will define transition legality, creation-state rules, invalidation, supersession, retention, and transition history.

The optional:

```
detail
```

field contains only concise neutral explanation subordinate to the meaning of:

```
draws_context_from
```

The initial envelope does not contain generic:

```
rationale
basis
evidence
supporting_records
contrary_records
```

fields.

The Work Relationship reuses accepted structured Portia:

```
creation_source
created_by
updated_by
```

contracts.

Timestamps require an explicit UTC offset or `Z`.

At creation:

```
updated_at = created_at
updated_by = created_by
```

The following fields are immutable after initial persistence:

```
schema_version
record_type
module_id
class_id
work_id
relationship_id
relationship_type
source
target
creation_source
created_at
created_by
```

A change to source, target, relationship type, or owner scope requires a new relationship with a new relationship ID.

A proposed relationship’s `detail` may be edited in place before first activation. 

After activation, canonical detail is frozen. A material detail correction requires a successor relationship. Nonmaterial amendment behavior belongs to the shared Issue #12 amendment contract. 

When present, `supersedes` is established on the successor and is immutable after persistence.

The envelope does not persist redundant:

```
owner
owner_ref
endpoint_kind
source_kind
target_kind
direction
inverse_relationship_type
reverse_label
display_snapshot
```

fields.

See Section 18.5 for the complete endpoint and envelope contract.

### Decision 14: Work Relationship lifecycle, correction, and retention — Resolved

Work Relationships use:

```
proposed
active
invalidated
superseded
```

A deliberate, reviewed digital operation may create a Work Relationship directly as active.

Paper-derived, imported, automated, unresolved, ambiguous, incomplete, and unreviewed relationships begin proposed.

The permitted transitions are:

```
proposed → active
proposed → invalidated
active → invalidated
active → superseded
```

The following are terminal:

```
invalidated
superseded
```

A proposed relationship found to be materially wrong is invalidated.

A corrected candidate receives a new relationship ID.

Ordinary relationship removal means invalidation rather than filesystem deletion.

Canonical Work Relationship files are not hard-deleted through ordinary workflows.

Material correction of:

```
source
target
relationship_type
owner scope
active detail
```

requires a successor relationship with a new:

```
relationship_id
```

The successor may contain:

```
supersedes
```

as an array of structured entries containing:

```
work_record_ref
reason
```

and optional:

```
detail
```

when:

```
reason = other
```

Each predecessor uses a complete:

```
portia_work_record_ref
```

whose nested record reference has:

```
record_kind = work_relationship
contract_version = "1"
```

The initial supersession reasons are:

```
source_corrected
target_corrected
relationship_type_corrected
material_detail_corrected
duplicate_consolidated
other
```

A relationship cannot supersede itself.

Duplicate predecessor references and supersession cycles are prohibited.

One successor may supersede several duplicate prior relationships.

A proposed successor may identify active predecessors before activation.

The prior relationships remain active while the successor remains proposed.

They transition to superseded only when the successor becomes active.

Successor activation and predecessor supersession must be atomic or recoverable.

Source correction creates a new relationship beneath the corrected source work.

It does not move or rewrite the prior file.

The prior relationship remains preserved at its original canonical path.

A proposed relationship’s detail may be edited in place before first activation.

After activation, detail is frozen.

Material active-detail correction requires a successor.

Nonmaterial amendments and statements of disagreement remain governed by Issue #12.

Endpoint lifecycle changes do not silently:

```
retarget
invalidate
supersede
delete
update contract versions
follow successors
```

The relationship retains its original endpoint references and historically recorded endpoint contract versions.

Derived views may distinguish stored relationship status from endpoint resolution and current effective usability.

The complete append-only lifecycle-transition record is deferred to Issue #12.

Every transition must eventually preserve prior status, new status, timestamp, attribution, controlled reason, and any bounded explanation required by that shared contract.

See Section 18.6 for the complete lifecycle, correction, supersession, and retention rules.

### Decision 15: shared reference-resolution outcomes — Resolved

Portia uses a layered, derived reference-resolution assessment.

Resolution assessment is not persisted inside canonical reference objects.

The assessment separates:

```
structural validity
exact authoritative resolution
contract support
native target lifecycle
consumer-specific usability
authorization and privacy
```

The shared resolution states are:

```
resolved
missing
invalid
unsupported
unavailable
```

`resolved` means the exact authoritative target was located and its identity agrees with the reference.

It does not mean the target is active, usable, authorized, reportable, or evidentiary.

`missing` means authoritative lookup completed and the exact target does not exist.

A stale index, failed display search, guessed-path failure, or lack of access must not be reported as missing.

`invalid` means the reference or discovered target contradicts the accepted contract.

`unsupported` means the reference is structurally valid but the current implementation cannot interpret the requested target contract.

`unavailable` means authoritative resolution cannot currently be completed because the required authority, storage, or permitted access is unavailable.

Composite references preserve whether failure occurred at the reference, scope-provider, authority, work, record, or contract stage.

Target lifecycle is separate from resolution.

A reference to a superseded record ordinarily produces:

```
resolution_state = resolved
target_status = superseded
```

The resolver does not silently follow or persist a successor.

The shared conceptual use dispositions are:

```
usable
historical_only
not_usable
review_required
undetermined
```

Use disposition is determined by the consuming field or workflow.

An undetermined target is not treated as usable.

Resolution uses only exact authoritative identity and accepted scope.

Portia must not resolve or repair references through names, snapshots, filenames, bare identifiers outside scope, workspace-wide first matches, presumed student equivalence, or reverse indexes as sole authority.

A non-null `contract_version` is an explicit target-contract expectation.

Unknown but well-formed versions are unsupported.

A discovered target whose actual contract contradicts the reference is invalid.

A null contract version does not mean latest, any version, or ignore version.

Historical display snapshots may support presentation when a target is missing, unsupported, unavailable, inactive, invalidated, or superseded.

Snapshots do not alter resolution, repair identity, authorize use, or create a replacement target.

Resolution is observational.

It must not:

```
rewrite references
update contract versions
follow successors automatically
move records
create Actors
merge roster identities
create reverse relationships
change lifecycle status
```

Every field that accepts a reference must declare its accepted reference family, scope provider, required resolution state, contract policy, permitted lifecycle, use disposition, and failure behavior.

See Section 16 for the complete shared resolution contract.

### Decision 16: bounded historical person display snapshots — Resolved

Portia defines one initial reusable historical display-snapshot contract:

```
person_display_snapshot
```

Its serialized property name is:

```
display_snapshot
```

Its exact shape is:

```
{
  "display_name": "Jordan Lee"
}
```

The snapshot contains exactly one required nonempty, non-whitespace field:

```
display_name
```

Unknown properties are prohibited.

The snapshot may appear only as a sibling to:

```
roster_student_ref
actor_ref
```

within a containing domain wrapper.

It is never nested inside either identity reference.

The snapshot is permitted at the shared-contract level but is not universally required.

Each consuming record declares whether it is:

```
required
optional
prohibited
```

Event Participant roster-student and Actor subjects continue to require a display snapshot.

The snapshot records the person display name associated with the containing record when the durable reference was established or confirmed.

It is nonauthoritative historical presentation data.

It does not participate in:

```
canonical identity
reference equality
duplicate detection
scope
resolution
authorization
lifecycle
successor selection
```

Resolution uses only the adjacent durable identity reference.

Portia must not use `display_name` to locate, repair, merge, retarget, or create identities.

When current authoritative display information differs, authorized historical presentation should use neutral wording such as:

```
Current display name: Jordan Rivera
Recorded in this record as: Jordan Lee
```

The application must not infer that a differing snapshot is a former legal name, alias, error, or any other specific name category.

When the target is missing, unsupported, unavailable, invalidated, or superseded, the snapshot may still be displayed as historical data.

It does not alter the resolution result.

A proposed containing record may correct its snapshot in place when the durable identity remains unchanged.

After activation, the snapshot is frozen.

Material identity correction requires replacement of the containing canonical record.

Nonmaterial snapshot correction or annotation belongs to the shared Issue #12 amendment contract.

Snapshots are not automatically synchronized with current roster or Actor Directory data.

The initial snapshot must not contain identifiers, legal-name classifications, pronouns, titles, roles, organizations, grade level, contact information, lifecycle status, institutional data, allegations, narrative content, private notes, or other domain-record data.

Descriptive and unknown person variants do not use this snapshot contract.

The initial architecture defines no display snapshots for works, child records, module records, targets, Work Relationship endpoints, or supersession references.

A future snapshot family requires a separate explicit architectural decision.

Event Participant reconciliation will rename:

```
student_ref → roster_student_ref
actor_id → actor_ref
```

while retaining the existing sibling:

```
display_snapshot
```

with only:

```
display_name
```

See Section 19.1 for the complete historical display-snapshot contract.

### Decision 17: Event-family reconciliation and contract versioning — Resolved

The existing version-1 Event, Event Participant, and Event Participant Role contracts are frozen.

Issue #11 introduces reconciled version-2 contracts for all three record families.

The same schema version must not acquire two incompatible serialized meanings.

Readers select the applicable schema from explicit:

```
schema_version
```

Version 1 remains independently valid and machine-readable.

Version 2 uses only the accepted Issue #11 shared reference, target, and snapshot contracts.

Version-2 schemas reject obsolete version-1 properties rather than accepting both forms through compatibility unions.

Event version 2:

* uses `schema_version = "2"`;
* uses `module_work_record_ref` entries for `instructional_context.external_refs`;
* and uses complete direct `portia_work_ref` values for Event supersession.

Event Participant version 2:

* uses `schema_version = "2"`;
* renames `student_ref` to `roster_student_ref`;
* replaces bare subject-level `actor_id` with `actor_ref`;
* retains the sibling one-field `display_snapshot`;
* and uses nested `record_ref` in participant supersession entries.

Event Participant Role version 2:

* uses `schema_version = "2"`;
* replaces `participant_id` with singular Event Participant `target`;
* uses nested `record_ref` for Account and Observation basis;
* and uses nested `record_ref` in Role supersession entries.

References expecting reconciled Event-family records use:

```
contract_version = "2"
```

Historical references expecting version-1 records retain:

```
contract_version = "1"
```

Account and Observation references remain:

```
contract_version = null
```

until those public target contracts are accepted.

Version migration is explicit.

Ordinary reading, validation, and reference resolution do not mutate or upgrade canonical records.

A migration that preserves domain meaning retains the same canonical Event, participant, or Role identity and storage scope.

Material identity, target, Role, or Event-boundary corrections must use their established correction and supersession workflows rather than being hidden inside migration.

Migration must validate the complete version-1 source, construct and validate a complete version-2 candidate, preserve unchanged creation provenance, perform required cross-record checks, and commit atomically or recoverably.

The detailed migration-history, attribution, retention, and rollback contract remains assigned to Issue #12.

The new shared reference, target, snapshot, and Work Relationship contracts begin at their own version 1.

Exact schema filenames, `$id` values, external-reference organization, and validation registry structure remain governed by Decision 19.

See Section 20.5 for the complete versioned reconciliation contract.

### Decision 18: identifier ownership and validation boundary — Resolved

Identifier validation follows the authority that owns the identifier contract.

Portia is authoritative for Portia-owned identifier families.

The initial Portia-owned schemas and prefixes are:

```
Event:
  evt_

Support Process:
  sup_

Actor:
  actr_

Event Participant:
  ep_

Event Participant Role:
  epr_

Work Relationship:
  rel_
```

Every Portia-owned identifier uses only ASCII letters, digits, underscores, and hyphens.

Periods are prohibited.

Event and Support Process identifiers therefore remain compatible with Core's `ModuleWorkRef.work_id` identifier alphabet.

Portia-owned identifiers use prefix-specific reusable schemas and an initial maximum length of 128 characters.

Every identifier remains a JSON string.

Leading zeros and case are preserved.

Identifier equality uses exact serialized-string equality after structural validation.

Portia performs no silent trimming, case-folding, coercion, truncation, prefix repair, or character substitution.

Core remains authoritative for Core-owned identifiers such as:

```
class_id
student_id
module_id
```

Portia should reuse independently addressable Core schemas where available rather than duplicating their exact rules.

Sibling-module work IDs, record IDs, and record kinds remain opaque to Portia.

Their complete meaning and syntax remain governed by Core and the originating module’s public contract.

When no reusable authoritative identifier schema is available, Portia may apply a conservative:

```
structurally_safe_external_id
```

fallback.

That fallback provides only basic string and path-safety validation.

It does not establish registration, existence, uniqueness, ownership, lifecycle, contract support, or authorization.

Prefixes do not replace explicit work-kind, record-kind, target-kind, or record-type fields.

Identifiers used in filesystem paths must satisfy path-safety requirements, but path safety does not transfer domain authority to Portia.

Ordinary validation and resolution do not normalize or repair malformed identifiers.

Explicit import or migration tooling may create a traceable mapping to a newly generated canonical identifier.

Portia-generated opaque identifiers must not encode sensitive domain content.

Schema validation establishes only local structure.

Application validation remains responsible for:

```
existence
registration
uniqueness
scope
path agreement
kind agreement
contract support
authorization
```

Existing generic `safeId` definitions should be replaced or reorganized according to identifier ownership during Issue #11 implementation.

Exact external-schema dependency and file organization remain governed by Decision 19.

See Section 20.6 for the complete identifier-validation boundary.

### Decision 19: shared-schema organization and compatibility boundaries — Resolved

Portia uses modular, independently addressable Draft 2020-12 schemas.

The existing Event, Event Participant, and Event Participant Role version-1 schemas retain their current repository paths and public `$id` values.

Every new public Portia schema uses:

```
versioned repository path
matching versioned canonical $id
```

Each independently reusable public contract receives its own schema file.

Portia-owned cross-schema composition uses canonical absolute `$ref` values.

Private nonreusable helpers may remain in local `$defs`.

Portia does not publish mutable:

```
latest
current
```

schema identities.

A noncanonical:

```
schemas/schema-catalog.json
```

maps conceptual contract names and versions to canonical schema IDs and local paths.

The catalog supports tooling and dispatch but does not override schema identity, become canonical record data, or function as a Core registry.

Canonical records dispatch through explicit:

```
record family
schema_version
```

Unknown versions are unsupported and do not fall back to the newest known schema.

Shared value-object schema versions are established through containing-schema composition and canonical `$ref` values.

They do not add serialized `schema_version` fields.

A reference’s `contract_version` continues to identify the expected target-record contract rather than the reference object’s own schema version.

PDS Core currently exposes required routing identity contracts through strict Python value models and exact dictionary conversions.

Portia must not claim canonical Core JSON Schema IDs that Core has not published.

Until official independently addressable Core schemas exist, Portia uses clearly labeled, nonauthoritative compatibility-adapter schemas for:

```
ModuleWorkRef
ModuleRecordRef
```

Compatibility adapters:

* use Portia-owned compatibility `$id` values;
* are pinned to an explicit Core package version or source commit;
* include a compatibility lock;
* are tested against the actual Core runtime validators;
* preserve exact Core dictionary shapes;
* and do not become authoritative Core contracts.

A fixture passing only an adapter schema is insufficient.

Compatibility tests must also pass the pinned Core implementation.

When Core later publishes official immutable JSON Schemas, Portia may adopt them only through explicit compatibility review.

Published Portia schemas are not silently edited to replace adapter dependencies.

A semantic external dependency change requires a new Portia schema version or another explicit compatibility mechanism that preserves the original contract.

Core package versions remain distinct from producer-record `contract_version` values.

Portia’s native schema tree and schema catalog are not Meridian’s ingestion API.

Issue #11 introduces no direct schema or runtime dependency on Meridian.

Portia-to-Meridian interoperability remains mediated by later privacy-minimized producer publications registered through Core.

Decision 19 does not define or freeze those publication manifests.

Automated tests resolve every schema offline.

Test resources are separated into:

```
schema-valid
schema-invalid
application-invalid
migration
compatibility
```

The test suite verifies canonical `$id` uniqueness, version-path agreement, complete `$ref` resolution, legacy and reconciled version separation, adapter lock integrity, Core runtime parity, catalog integrity, and absence of undeclared Meridian dependencies.

Generated schema bundles are derived artifacts rather than canonical sources.

The schema organization and compatibility process are documented in:

```
schemas/README.md
ADR 0007
```

See Section 20.7 for the complete schema-organization and external-compatibility contract.

## 23. Recommended Decision Order

Resolve the remaining architecture in this order:

1. shared naming and identity components;
2. local versus complete scope rules;
3. `contract_version` semantics;
4. flat versus composed cross-work references;
5. snapshot placement and shape;
6. target kinds and cardinality;
7. relationship-record threshold;
8. Work Relationship envelope and ownership;
9. initial relationship vocabulary;
10. schema file organization;
11. existing-schema reconciliation;
12. examples, fixtures, tests, ADR, validation note, and README.

This order prevents later decisions from forcing a redesign of earlier schema primitives.

## 24. Reconciliation Work Required During Issue #11

The issue must eventually update or explicitly classify every audited item.

### 24.1 Event schema

Review:

```text
instructional_context.external_refs
eventRef
safeId
module_id validation
record_kind validation
```

### 24.2 Event Participant schema

Review:

```text
studentRef
actor subject
displaySnapshot
participantSupersessionRef
safeId
```

### 24.3 Event Participant Role schema

Review:

```text
accountRefBasis
observationRefBasis
roleSupersessionRef
participant_id
safeId
```

Do not weaken the accepted same-Event restrictions.

### 24.4 Identity examples

Correct stale serialized fragments or label them more explicitly as historical conceptual examples.

### 24.5 Event and participant examples

Preserve validated examples while updating shared `$ref` use if the final schemas change.

### 24.6 Role examples

Preserve accepted Role semantics while updating shared schema references if necessary.

### 24.7 ADR 0004 examples

Replace the provisional Work Relationship envelope with the finalized schema shape.

Preserve the accepted ownership rule.

### 24.8 README

Add the finalized reference, target, and relationship distinctions only after the decisions are accepted.

## 25. Current Audit Conclusion

The repository does not contain one existing reference shape that can be promoted unchanged into a universal Portia reference.

The existing shapes instead reveal several legitimate identity and scope categories:

```text
Core roster identity
workspace Actor identity
Event-local child identity
complete Portia work identity
complete cross-work record identity
sibling-module record identity
targeting
basis
provenance
specialized correction relationships
```

The accepted direction is therefore a small family of scope-specific reference value objects with shared naming, validation, snapshot, and resolution principles.

Most current Event Participant and Role references are not architectural mistakes.

They are intentionally specialized local relationships and should remain specialized.

The principal reconciliation problems are:

1. the Event schema’s incomplete sibling-module reference;
2. inconsistent display-snapshot placement;
3. provisional Work Relationship examples and vocabulary;
4. stale identity example fragments;
5. unresolved `contract_version` semantics;
6. unresolved flat-versus-composed cross-work references;
7. unresolved target cardinality conventions;
8. and Portia schema identifier patterns that are broader than Core’s documented contract.

No production data or compatibility requirement prevents clean correction of these development-stage inconsistencies.

The next architecture step is to finalize the exact shared identity and reference value objects, beginning with:

```text
roster_student_ref
actor_ref
local_record_ref
```

before deciding complete cross-work and sibling-module forms.
