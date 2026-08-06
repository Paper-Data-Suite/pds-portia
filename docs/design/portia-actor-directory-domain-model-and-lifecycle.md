# Portia Actor Directory Domain Model and Lifecycle

**Status:** Working design — Decisions 1–5 adopted
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#14 — Define the Actor Directory domain model and lifecycle`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-06
**Branch:** `14-actor-directory-domain-model-lifecycle`

## 1. Purpose

This document defines Portia's teacher-workspace Actor Directory for recurring
non-roster human collaborators.

It will establish:

- the semantic unit represented by one Actor;
- Actor eligibility and exclusion rules;
- stable Actor identity;
- exact Actor references;
- canonical storage;
- the Actor root record;
- current display metadata;
- contact-point boundaries;
- Actor-to-student relationship boundaries;
- lifecycle;
- nonmaterial correction;
- material identity correction;
- duplicate detection and consolidation;
- roster-student collision handling;
- workspace-scoped lifecycle and amendment history;
- operational targeting;
- integrity and Quarantine behavior;
- privacy boundaries;
- and compatibility requirements for records that consume Actor identity.

This document defines architecture and public contracts. Production Python
models, filesystem services, search, duplicate-review workflows, communication
delivery, and teacher-facing Actor management belong to a later executable
milestone.

## 2. Governing contracts

The design is subordinate to accepted ADRs 0001–0009.

The existing Actor identity contracts are already public and immutable:

```text
schemas/v1/identifiers/portia-actor-id.schema.json
schemas/v1/references/actor-ref.schema.json
schemas/v1/snapshots/person-display-snapshot.schema.json
```

Current Event Participant v3 composes those contracts for an Actor subject:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "display_snapshot": {
    "display_name": "Maria Smith"
  }
}
```

The existing identity-only Actor reference remains:

```json
{
  "actor_id": "actr_example"
}
```

Issue #14 must not add display metadata, contact information, relationship
claims, status, paths, or contract versions to `actor_ref@1`.

The current class/work-scoped lifecycle and correction contracts include:

```text
schemas/v1/lifecycle/lifecycle-transition.schema.json
schemas/v1/lifecycle/lifecycle-history-correction.schema.json
schemas/v1/corrections/amendment.schema.json
schemas/v1/migrations/record-migration.schema.json
schemas/v1/removals/exceptional-removal.schema.json
```

Those envelopes require a containing class-owned Portia work. They cannot be
assumed to apply to a workspace-scoped Actor.

The current operational and diagnostic contracts include:

```text
schemas/v1/projections/integrity-finding.schema.json
schemas/v1/operations/operation-journal.schema.json
schemas/v1/operations/operation-lock.schema.json
schemas/v1/operations/quarantine-record.schema.json
schemas/v1/projections/source-snapshot.schema.json
schemas/v1/projections/derived-index-metadata.schema.json
schemas/v1/projections/derived-current-pointer.schema.json
```

Their version-1 target vocabularies do not provide one exact Actor target.
Issue #14 must use new versions or new Actor-specific contracts where exact
Actor targeting is required.

Published public schemas remain immutable.

## 3. Reviewed repository baseline

The initial Issue #14 repository checkpoint was completed on 2026-08-06.

| Repository | Reviewed commit | Relevant current contract | Immediate implication |
| --- | --- | --- | --- |
| `pds-portia` | `d60966f8486bf93fb0185e3662b76d3b79ce9dcb` | Issues #11–#13 are merged. Actor identity and historical display references exist, but no canonical Actor record or workspace-scoped Actor history exists. | Issue #14 must define the domain record and reconcile workspace-scoped lifecycle, correction, operations, and diagnostics. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core v0.6 remains authoritative for workspace selection, class identity, roster parsing, and roster-scoped student identity. It provides no workspace person registry or cross-roster identity authority. | Portia must retain teacher-local Actor ownership and must not treat Core roster similarity as automatic person resolution. |

The Issue #14 branch was confirmed identical to `main` at the initial
checkpoint.

The baseline classification is:

```text
pds-core: governing roster and workspace boundary; no Core change required
pds-portia: required Actor contract work
other sibling repositories: no concrete initial contract implication
```

A pre-ADR checkpoint and a final pre-acceptance checkpoint remain required.

## 4. Governing principles

1. One Actor represents one recurring human person.
2. Actor identity is teacher-local and workspace-scoped.
3. Actor identity is not institutional person identity.
4. Roster students use Core roster-qualified references, not Actor identity.
5. Names, titles, organizations, contact values, and relationship labels are not identity.
6. Actor identity is distinct from a workflow-specific role.
7. Actor identity is distinct from a student relationship.
8. Contact information is optional and independently lifecycle-bearing.
9. Historical Actor references remain exact.
10. Historical display snapshots are nonauthoritative and are not rewritten from current Actor metadata.
11. Similarity may create a duplicate candidate but never establishes identity.
12. Confirmed duplicate consolidation creates a new successor.
13. Existing duplicate Actors are never silently selected as survivors.
14. Current Actor state and append-only Actor history must reconcile.
15. Actor operations require typed exact Actor targets.
16. Canonical Actor records are not physically deleted through ordinary workflows.
17. Derived search and duplicate indexes are nonauthoritative.
18. Operational and diagnostic data must remain privacy-minimized.
19. JSON Schema validates local structure; application validation establishes cross-record identity and lifecycle truth.
20. Existing public contracts remain independently versioned and immutable.

---

# 5. Approved Decision 1: Actor Semantic Unit and Eligibility

## 5.1 Decision

One Portia Actor represents:

> One recurring human person deliberately recorded for reuse as a non-roster
> collaborator within one selected teacher-local Paper Data Suite workspace.

An Actor is a person identity record.

An Actor is not:

- a household;
- a family unit;
- a school;
- a district;
- an organization;
- a department;
- a team;
- a role;
- a job position;
- a communication recipient group;
- a contact method;
- an authenticated user;
- or a Core roster student identity.

One person who performs several roles remains one Actor.

Several people who share one email address or phone number remain several
Actors.

## 5.2 Recurrence and deliberate creation

An Actor may be created when the teacher expects the same person to recur across
Portia workflows or when stable historical identity is otherwise necessary.

Representative eligible people include:

```text
parent or caregiver
counselor
administrator
case manager
paraprofessional
school psychologist
social worker
nurse
coach
interpreter
external service provider
community collaborator
other recurring non-roster person
```

Creation is always deliberate.

Portia must not create an Actor automatically from:

- a free-text name;
- an email header;
- a phone number;
- an imported contact row;
- repeated communication;
- matching surnames;
- an Event narrative;
- or a duplicate-candidate result.

An import may create a proposal requiring explicit review. It does not establish
active Actor identity merely because an external record contains a name or
contact value.

## 5.3 Minimum identity information

Actor v1 requires one current nonblank `display_name`.

Actor v1 does not require:

- a structured legal name;
- a given name;
- a family name;
- a contact method;
- an organization;
- a title;
- a student relationship;
- or an institutional identifier.

Requiring only a display name follows data minimization and permits honest
records for recurring collaborators when no verified structured name is
available.

The display name is necessary for human usability. It is not identity.

## 5.4 Roster-student prohibition

A person represented in a valid Core roster must be referenced as:

```text
class_id + student_id
```

when the Portia relationship is a student relationship.

Portia must not create an Actor:

- from a roster-selection workflow;
- as a shortcut for cross-class student identity;
- because one student appears in several classes;
- because a student is a Communication sender or recipient;
- because the roster entry later becomes historical;
- or because a current roster is temporarily unavailable.

Core does not establish workspace-wide person identity across rosters.
Therefore:

- equal student IDs across rosters do not prove one person;
- different student IDs do not prove different people;
- equal names do not prove one person;
- and contact similarity does not prove one person.

A possible Actor/roster match creates a review condition only.

A confirmed Actor/roster collision requires explicit correction under a later
decision. It does not authorize automatic Actor conversion or reference
rewriting.

## 5.5 Incidental and unidentified people

A durable Actor is not required for every person mentioned in Portia.

A person may remain descriptive when the person is:

- unidentified;
- identity-withheld;
- incidental;
- one-time;
- unlikely to recur;
- or deliberately represented only by a contextual label.

The existing descriptive-person and unknown-person subject branches remain
valid alternatives.

A descriptive person may later be associated with a new Actor only through an
explicit reviewed correction of the consuming record.

## 5.6 Institutional-authority boundary

An Actor record states only what Portia records in the teacher-local workspace.

An Actor category, title, organization, contact point, or relationship does not
prove:

- employment;
- legal guardianship;
- custody;
- current assignment;
- professional licensure;
- institutional decision authority;
- access authorization;
- authority to approve a Support;
- authority to make a Determination;
- or authority to receive an export.

Consequential records must preserve their own authority evidence.

## 5.7 Actor existence without current use

An Actor may remain canonical without an active incoming workflow reference.

This permits:

- deliberate creation before first use;
- temporary lack of active references;
- historical Actors;
- inactive Actors;
- and preservation after all referencing work becomes historical.

Portia must not delete an Actor merely because no current derived incoming
reference is found.

A graph-sensitive removal or consolidation operation must use a verified current
index, a bounded canonical scan, or an indeterminate result under Issue #13.

## 5.8 Eligibility invariants

1. One Actor represents one human person.
2. Actor creation is deliberate.
3. Actor creation does not require contact information.
4. Actor creation does not require an institutional identifier.
5. A roster-student selection cannot create an Actor.
6. A possible roster collision is not a confirmed collision.
7. A descriptive or unknown person does not require an Actor.
8. One shared contact value does not combine several people.
9. One person with several roles does not receive several Actors merely because the roles differ.
10. An Actor record makes no institutional identity or authority claim.

---

# 6. Approved Decision 2: Identity and Reference Compatibility

## 6.1 Stable Actor identity

Actor identity remains:

```text
actr_<opaque-id>
```

The existing `portia_actor_id@1` contract remains authoritative and unchanged.

The identifier must not encode:

- a name;
- initials;
- title;
- organization;
- email address;
- phone number;
- student relationship;
- class;
- school;
- status;
- support information;
- Event information;
- or another sensitive semantic value.

## 6.2 Identity-only reference

The existing `actor_ref@1` remains:

```json
{
  "actor_id": "actr_example"
}
```

Reference equality is determined only by `actor_id`.

The reference does not contain:

- display name;
- category;
- status;
- organization;
- title;
- contact information;
- relationship;
- path;
- contract version;
- or successor identity.

This compact identity-only contract remains appropriate for historical and
cross-work use.

## 6.3 Historical display companion

The existing `person_display_snapshot@1` remains the standard bounded historical
display companion for an Actor reference.

It contains exactly:

```json
{
  "display_name": "Maria Smith"
}
```

The snapshot:

- is not identity;
- does not participate in equality;
- is not an alternate Actor lookup key;
- does not establish relationship or authority;
- does not contain contact information;
- and is not silently rewritten when the current Actor changes.

A consumer may display both recorded and current information when they differ.

## 6.4 Exact Actor representation reference

Issue #14 will introduce a new exact Actor representation reference rather than
changing `actor_ref@1`.

The conceptual version-1 shape is:

```json
{
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "contract_version": "1"
}
```

The contract name will be:

```text
exact_actor_ref
```

Its purpose is to identify:

```text
one Actor identity
+ one expected Actor record contract version
```

It is intended for:

- Actor supersession lineage;
- Actor migration;
- Actor lifecycle and amendment targets;
- Actor operation targets;
- Actor Quarantine;
- Actor integrity findings;
- and exact diagnostic resolution.

It does not by itself identify one observed byte representation.

Expected prior fingerprints, timestamps, and paths remain operation preconditions
rather than identity fields.

## 6.5 Actor target contract

Issue #14 will introduce a typed exact Actor target rather than using a generic
workspace target.

The conceptual shape is:

```json
{
  "kind": "actor",
  "actor_ref": {
    "actor_ref": {
      "actor_id": "actr_example"
    },
    "contract_version": "1"
  }
}
```

The final naming and nesting will be normalized during schema implementation.

The important invariant is:

> An operation or diagnostic changing or evaluating one Actor must identify that
> exact Actor representation contract.

This is not equivalent to:

```json
{
  "kind": "workspace"
}
```

A workspace target may protect a workspace-wide operation. It cannot substitute
for the identity of the Actor being changed.

## 6.6 No silent successor following

An `actor_ref` always resolves the identified Actor.

When the Actor becomes superseded:

- the predecessor remains exactly resolvable;
- historical references remain unchanged;
- derived interfaces may show successor information;
- new records should ordinarily select the reviewed successor;
- and current records that require corrected identity must be replaced or
  amended through their own accepted domain rules.

Portia must not silently return the successor when asked to resolve the
predecessor.

## 6.7 Reference invariants

1. `actor_id` is stable identity.
2. `actor_ref@1` remains unchanged.
3. A display snapshot is adjacent historical display only.
4. Exact contract version belongs in a new exact reference.
5. Fingerprints and timestamps do not become Actor identity.
6. A typed Actor target is required for exact Actor operations.
7. Generic workspace scope does not identify an Actor.
8. Actor references never silently follow successors.

---

# 7. Approved Decision 3: Canonical Actor Root and Storage Topology

## 7.1 Decision

The final Actor v1 canonical root is:

```text
<PDS workspace>/portia/actors/<actor_id>/
```

The root Actor record is:

```text
<PDS workspace>/portia/actors/<actor_id>/actor.json
```

This supersedes the earlier provisional flat example:

```text
<PDS workspace>/portia/actors/<actor_id>.json
```

The earlier path appeared before a canonical Actor contract, Actor child records,
or production Actor data existed. Finalizing a directory-style root now does not
change `actor_id`, `actor_ref`, or any existing persisted Actor record contract.

## 7.2 Reason for the directory root

Actor identity requires bounded subordinate records for:

- lifecycle transitions;
- lifecycle-history correction;
- amendments;
- contact points;
- Actor-to-student relationships;
- migrations;
- and any later Actor-specific correction evidence.

A flat Actor file plus workspace-wide history collections would require broad
workspace scans to load one Actor's canonical history.

The directory root provides:

- one bounded canonical aggregate;
- deterministic child discovery;
- straightforward identity/path validation;
- exact Actor lock scope;
- local history inspection;
- and space for independently lifecycle-bearing sensitive records.

## 7.3 Initial canonical topology

The accepted conceptual topology is:

```text
<PDS workspace>/
  portia/
    actors/
      <actor_id>/
        actor.json
        records/
          actor_lifecycle_transition/
            <transition_id>.json
          actor_lifecycle_history_correction/
            <correction_id>.json
          actor_amendment/
            <amendment_id>.json
          actor_contact_point/
            <contact_point_id>.json
          actor_student_relationship/
            <relationship_id>.json
          actor_record_migration/
            <migration_id>.json
          actor_exceptional_removal/
            <removal_id>.json
```

Only record families accepted by Issue #14 will be created.

The topology does not imply that every Actor has every child directory.

Path helpers must not create directories merely because a caller requests a
path.

## 7.4 Root ownership

The Actor identified by `<actor_id>` owns the root.

The contained `actor.json` must declare the same `actor_id`.

Every child record must:

- identify the same owning Actor;
- be stored beneath that Actor root;
- use its own opaque child-record identifier;
- and agree with its record-kind directory.

A child record that targets another Actor belongs under the Actor whose current
representation or relationship it governs, according to the later record-family
decision.

## 7.5 Workspace ownership

The selected Core workspace root is operational scope.

The Actor record does not store:

- an absolute workspace path;
- a teacher identifier;
- a school identifier;
- a tenant identifier;
- or a fabricated workspace identity.

Actor identity is therefore portable only within the documented teacher-local
workspace boundary.

Copying or merging workspaces is not Actor identity reconciliation.

## 7.6 No arbitrary class ownership

Actors are not stored beneath:

```text
classes/<class_id>/
```

An Actor that appears in several classes remains one workspace-scoped Actor.

An Event, Support Process, Account, Communication, or other consuming work
remains class-owned even when it references a workspace Actor.

Actor storage must not select:

- the first class where the person appeared;
- the most recent class;
- a synthetic schoolwide class;
- or an arbitrary class used only to obtain a Core work path.

## 7.7 Safe path construction

Actor path helpers must:

- accept the resolved Core workspace root;
- validate the Actor identifier through the public Actor ID contract;
- construct only documented workspace-relative descendants;
- reject absolute or traversal components;
- perform no hidden creation;
- and apply runtime containment and symlink policy appropriate to untrusted
  existing filesystem contents.

A stored path is diagnostic evidence, not Actor identity.

## 7.8 Discovery

Actor discovery enumerates only:

```text
<PDS workspace>/portia/actors/
```

Each direct child considered an Actor root must:

- have a structurally valid `actr_` directory name;
- contain `actor.json`;
- and have contained identity equal to the directory identity.

Malformed roots are reported independently.

Portia must not:

- reinterpret malformed names;
- search unrelated workspace directories for Actors;
- infer current state from modification time;
- or fabricate `actor.json` from child records.

## 7.9 Compatibility and migration

No production Actor schema or canonical Actor file existed before Issue #14.

The directory-root decision therefore requires documentation reconciliation, not
a production data migration.

If a development-era flat Actor fixture is later discovered, it must be treated
as unsupported provisional data and handled through an explicit reviewed import
or migration tool. It must not be moved silently during discovery.

## 7.10 Storage invariants

1. One Actor has one canonical Actor root.
2. The Actor root directory name equals the root record's `actor_id`.
3. `actor.json` is the current canonical Actor representation.
4. Actor child records are stored beneath the same Actor root.
5. Actor storage is not class-owned.
6. Absolute workspace paths are not persisted as identity.
7. Discovery is bounded to the Actor collection.
8. Directory order and modification time do not determine current state.
9. Path helpers perform no hidden creation.
10. The earlier flat path is superseded before a public Actor schema exists.

---

# 8. Approved Decision 4: Actor Aggregate Decomposition

## 8.1 Decision

Actor v1 uses a small canonical aggregate composed of distinct record families:

```text
Actor root record
Actor Contact Point
Actor-to-Student Relationship
Actor lifecycle and correction history
```

The root Actor record does not embed complete contact-point history or
student-relationship history.

## 8.2 Actor root responsibilities

The Actor root stores current identity-adjacent profile data:

- `actor_id`;
- current lifecycle status;
- current display name;
- broad Actor category;
- optional current organization display;
- optional current title display;
- supersession lineage where applicable;
- creation provenance;
- and current-representation timestamps and attribution.

The Actor root does not store:

- email values;
- phone values;
- passwords or credentials;
- a universal list of students;
- legal guardianship assertions;
- workflow-specific roles;
- institutional authority;
- Communications;
- Accounts;
- Support participation;
- or an unbounded note field.

## 8.3 Actor Contact Point

Contact information will be a separate canonical child record.

This decision is adopted because one person may have:

- several contact methods;
- changing preferred methods;
- obsolete contact values;
- contact values with different sources;
- contact values with different sensitivity or use constraints;
- and contact values requiring independent correction or removal.

A separate record permits:

- independent identity;
- independent lifecycle;
- bounded sensitive payload;
- exact provenance;
- historical preservation;
- duplicate candidate evidence without embedding contact data in the Actor ID;
- and exceptional removal of a prohibited contact payload without deleting the
  Actor identity.

The Actor root may derive a preferred-current contact view. It does not copy
contact values into the root record.

## 8.4 Actor-to-Student Relationship

Recurring relationships between an Actor and a roster-qualified student will be
separate canonical child records.

The initial relationship family is limited to:

```text
Actor -> Core roster-qualified student
```

The exact student identity remains:

```text
class_id + student_id
```

The relationship record will distinguish broad relationship types such as:

```text
parent_or_guardian
caregiver
family_contact
counselor
case_manager
support_staff
administrator
other
```

The final vocabulary and authority disclaimers remain later decisions.

The record must preserve:

- one exact Actor;
- one exact roster-qualified student;
- relationship type;
- source or basis;
- current status;
- effective scope or period where supported;
- provenance;
- lifecycle;
- correction;
- and supersession.

A teacher-recorded relationship does not become an institutionally verified
legal relationship.

## 8.5 Excluded canonical relationship families

Actor v1 will not introduce canonical:

- Actor-to-organization identity;
- Actor-to-class assignment;
- Actor-to-Actor relationship;
- household membership;
- recipient group;
- or universal Actor-to-work role.

Organization and title remain current display fields.

Class and work participation belongs in the consuming Portia record.

Actor-to-Actor and organization identity require distinct semantic and
authority models and are deferred.

## 8.6 Contextual workflow roles

Workflow-specific roles remain in the consuming record.

Examples include:

- Account source;
- Communication sender;
- Communication recipient;
- Support provider;
- Follow-Up owner;
- Determination decision maker;
- consulted collaborator;
- Event Participant;
- and family contact for one Communication.

An Actor category or Actor-to-student relationship may support a user interface,
but it does not replace the consuming record's explicit contextual role.

## 8.7 Historical snapshots

A consuming record that uses an Actor should ordinarily preserve:

```text
actor_ref
person_display_snapshot
contextual role or relationship
```

A consuming record may also reference an exact Actor-to-student relationship
when that canonical relationship is materially relevant.

The historical snapshot must not include current contact values by default.

Updating the Actor, Contact Point, or Actor-to-Student Relationship does not
rewrite historical consuming records.

## 8.8 Contact and relationship indexes

Search indexes, reverse-reference indexes, preferred-contact views, and
duplicate candidates are derived.

They do not become canonical Actor, contact, or relationship records.

The initial implementation may build them in memory through bounded canonical
scanning.

Persisted Actor-specific projection kinds are deferred until the Issue #14
design determines whether they are required. Existing Issue #13 projection
vocabularies will not be modified in place.

## 8.9 Aggregate invariants

1. The Actor root stores identity-adjacent profile data only.
2. Contact points are independently canonical child records.
3. Actor-to-student relationships are independently canonical child records.
4. Workflow roles remain in consuming records.
5. Organization and title are display metadata, not identity authorities.
6. Legal or institutional authority is not inferred from relationship type.
7. Contact values are not copied into the Actor root.
8. Historical references are not rewritten from current child records.
9. Derived search and duplicate views are not canonical authority.
10. No unsupported universal relationship graph is introduced.

---

# 9. Approved Decision 5: Initial Actor Root Envelope and Current Profile

## 9.1 Record identity

The canonical root contract will be:

```text
actor@1
```

The schema path will be:

```text
schemas/v1/actors/actor.schema.json
```

The record type will be:

```text
actor
```

The root envelope will use:

```text
schema_version = "1"
record_type = "actor"
module_id = "portia"
```

## 9.2 Required envelope

The Actor v1 root will contain exactly these top-level fields:

```text
schema_version
record_type
module_id
actor_id
status
display
actor_category
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

The record is a mutable current representation protected by revision-aware
replacement and append-only Actor-specific lifecycle and amendment history.

## 9.3 Display object

The initial display object will contain:

```text
display_name
organization, optional
title, optional
```

`display_name` is required.

`organization` and `title` are current display metadata only.

Actor v1 will not require or standardize:

- legal name;
- given name;
- middle name;
- family name;
- suffix;
- honorific;
- pronouns;
- postal address;
- date of birth;
- government identifier;
- employee identifier;
- or a separate alias collection.

This avoids unnecessary identity claims and sensitive data collection.

Historical names remain available through:

- historical consuming-record snapshots;
- append-only Actor amendment history;
- and exact predecessor Actor records after material correction.

A later version may add a bounded structured-name or alias contract only if a
concrete workflow requires it.

## 9.4 Actor category

The initial broad category vocabulary will be:

```text
family_or_caregiver
school_staff
external_support_provider
community_collaborator
other
```

The category supports search and presentation.

It does not establish:

- a specific student relationship;
- employment;
- organization identity;
- title;
- decision authority;
- or access authorization.

`other` will require concise detail through a later finalized representation.

The design will evaluate whether the detail belongs in the category object
rather than adding an unbounded Actor note.

## 9.5 Lifecycle status

The initial Actor status vocabulary will be:

```text
proposed
active
inactive
invalidated
superseded
```

Initial meanings are:

### `proposed`

The record is structurally present but has not completed the required human
review for current selection.

Expected uses include:

- imported candidate;
- paper- or external-source proposal;
- and deliberately saved incomplete review.

A proposed Actor is not selectable as established recurring identity in an
active canonical workflow unless the consuming contract explicitly supports a
proposal reference.

### `active`

The Actor is eligible for ordinary new selection, subject to current
relationship, privacy, authorization, and integrity checks.

### `inactive`

The Actor remains valid identity and historically resolvable but is excluded
from ordinary default new selection.

Inactive is reopenable.

Representative reasons include:

- no longer expected to recur;
- outdated local relationship;
- left the relevant organization;
- teacher chose to hide from normal selection;
- or temporarily unavailable.

Inactive does not mean false or invalid.

### `invalidated`

The Actor must no longer be treated as a valid current non-roster person identity
for new use and no accepted Actor successor presently replaces it.

Representative grounds may include:

- entered for the wrong person;
- insufficient identity;
- confirmed roster-student collision requiring cross-family correction;
- or prohibited identity representation.

Invalidation does not erase historical references.

### `superseded`

One or more accepted Actor successors provide the canonical replacement
representation under the supported Actor replacement topology.

Superseded is absolute terminal.

The predecessor remains exactly resolvable and is never silently redirected.

## 9.6 Proposed transition matrix

The detailed lifecycle decision will finalize reasons and prerequisites.

The initial matrix is:

| From | Permitted destinations |
| --- | --- |
| `proposed` | `active`, `inactive`, `invalidated`, `superseded` |
| `active` | `inactive`, `invalidated`, `superseded` |
| `inactive` | `active`, `invalidated`, `superseded` |
| `invalidated` | `superseded` only |
| `superseded` | none |

These transitions are prohibited:

```text
active -> proposed
inactive -> proposed
invalidated -> active
invalidated -> inactive
superseded -> any status
```

## 9.7 Creation baseline

Digital teacher-reviewed creation may begin as:

```text
active
```

Imported or otherwise unreviewed creation should normally begin as:

```text
proposed
```

The exact creation-source branches and review prerequisites remain a later
decision.

The creation baseline uses:

```text
status
creation_source
created_at
created_by
```

Later status changes require Actor-specific append-only lifecycle transitions.

## 9.8 Supersession field

The Actor root may contain successor-owned exact predecessor references.

The initial supported reasons will include:

```text
identity_corrected
duplicate_consolidated
contract_migrated
other
```

`other` requires bounded detail.

Duplicate consolidation may contain several exact Actor predecessors.

Ordinary identity correction normally contains one predecessor.

The later replacement-topology decision will determine whether conflated-person
correction permits one-to-many Actor replacement or requires invalidation plus a
separate resolution record.

## 9.9 Timestamps and attribution

`created_at` and `updated_at` use explicit-offset timestamps.

`created_by` and `updated_by` use the existing attribution-agent contract.

Attribution identifies the local operator or deterministic system process
responsible for persistence.

It does not establish:

- authenticated identity;
- institutional role;
- authority over the represented person;
- or legal authority for a relationship claim.

For a newly created Actor:

```text
updated_at = created_at
updated_by = created_by
```

Application validation enforces that equality.

Later replacements require monotonic `updated_at` and exact expected prior
state.

## 9.10 No general notes field

Actor v1 will not contain an unbounded `notes`, `description`, or `metadata`
object.

Concise domain-specific detail may be permitted only where required by a closed
branch such as:

- `actor_category = other`;
- correction reason;
- lifecycle reason;
- contact label;
- or relationship source detail.

Narrative information belongs in the appropriate Account, Communication,
Support, or other domain record.

## 9.11 Current-profile invariants

1. The root contract is `actor@1`.
2. The root record type is `actor`.
3. `display_name` is required but is not identity.
4. Structured legal identity is not required.
5. Organization and title are current display metadata only.
6. Actor category is broad navigation metadata.
7. Specific student relationship is not embedded in Actor category.
8. Contact information is not embedded in the Actor root.
9. The Actor has one current persisted lifecycle status.
10. Later status changes require Actor-specific append-only history.
11. Superseded is absolute terminal.
12. The Actor root has no unbounded notes or metadata field.

---

## 10. Consequences of Decisions 1–5

The initial accepted direction requires Issue #14 to introduce at least:

```text
actor@1
exact_actor_ref@1
actor_target@1
actor_contact_point@1
actor_student_relationship@1
actor_lifecycle_transition@1
actor_lifecycle_history_correction@1
actor_amendment@1
```

Later decisions will determine whether Actor-specific forms are also required
for:

```text
record migration
exceptional removal
integrity finding
operation journal
operation lock
Quarantine
derived projection metadata
```

Existing public schemas will not be modified in place.

The design must next resolve:

1. exact Actor Contact Point fields and lifecycle;
2. exact Actor-to-Student Relationship fields and authority limitations;
3. Actor lifecycle-transition and history-correction envelopes;
4. Actor amendment paths and privacy treatment of prior values;
5. duplicate-candidate and consolidation rules;
6. roster-student collision and conflated-person correction;
7. Actor migration and exceptional removal;
8. operational target versioning;
9. Actor-specific integrity rules;
10. and whether any persisted Actor projection is required in v1.

## 11. Rejected initial alternatives

### Flat Actor file with workspace-wide history collections

Rejected because loading and validating one Actor would require broad scans and
would separate the Actor from its bounded canonical child history.

### Actor stored beneath the first related class

Rejected because recurring Actors may participate across several classes and no
one class owns their identity.

### Actor root containing all contact and student relationships

Rejected because contact and relationship data have independent lifecycle,
sensitivity, provenance, and correction requirements.

### Actor category as a permanent role list

Rejected because person category, job title, student relationship, workflow role,
and decision authority are distinct.

### Structured legal-person profile

Rejected because Portia is teacher-local, does not verify institutional identity,
and should collect the least data necessary.

### Automatic Actor creation from names or communications

Rejected because similarity and recurrence do not establish identity.

### Existing duplicate selected as consolidation survivor

Rejected because it would privilege one predecessor, mutate accepted history,
and conflict with the accepted new-successor consolidation model.

### Generic workspace target for exact Actor operations

Rejected because workspace scope does not identify the Actor being changed.

## 12. Next design slice

The next slice should decide:

```text
Actor Contact Point
Actor-to-Student Relationship
relationship authority and source
contact and relationship lifecycle
historical relationship snapshots
```

Those decisions should precede Actor lifecycle-history schema implementation
because child-record lifecycle and correction requirements may affect the final
workspace-scoped history family.
