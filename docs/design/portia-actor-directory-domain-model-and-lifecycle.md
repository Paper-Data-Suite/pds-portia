# Portia Actor Directory Domain Model and Lifecycle

**Status:** Working design — Decisions 1–25 adopted
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

# 10. Approved Decision 6: Actor Contact Point Semantic Unit and Identity

## 10.1 Decision

Actor contact information uses a separate canonical child record:

```text
actor_contact_point@1
```

One Actor Contact Point represents:

> One exact contact method and value recorded for one exact Actor, together with
> its local source, verification state, use preference, lifecycle, and
> provenance.

One contact-point record never represents:

- several Actors;
- several email addresses;
- several phone numbers;
- a household;
- a recipient group;
- an organization switchboard as an organization identity;
- or a communication event.

Several contact values require several Contact Point records.

## 10.2 Identity

Actor Contact Point identifiers use:

```text
acp_<opaque-id>
```

The prefix is diagnostic only.

The identifier must not encode:

- the contact value;
- an email domain;
- phone digits;
- the Actor name;
- contact type;
- preference;
- status;
- or source.

The public identifier contract will be:

```text
portia_actor_contact_point_id@1
```

## 10.3 Canonical storage

A Contact Point is Actor-owned and stored beneath the owning Actor root:

```text
portia/actors/<actor_id>/
  records/
    actor_contact_point/
      <contact_point_id>.json
```

The contained `actor_id` and `contact_point_id` must agree with the canonical
path.

A Contact Point is not stored:

- beneath a class;
- beneath a Communication;
- in the Actor root record;
- in a workspace-wide address book;
- or in a derived search index.

## 10.4 Stable reference

The stable child identity is:

```text
actor_id + contact_point_id
```

Issue #14 will introduce an exact reference containing:

```text
actor_ref
contact_point_id
contract_version
```

Conceptually:

```json
{
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "contact_point_id": "acp_example",
  "contract_version": "1"
}
```

The contact value is not part of the reference.

A later Communication may preserve an exact Contact Point reference when the
selected method materially matters. The Communication contract, not the Contact
Point, owns the communication act, direction, recipient role, delivery status,
and message summary.

## 10.5 Initial supported contact kinds

Actor Contact Point v1 supports exactly:

```text
email
phone
```

Postal addresses are excluded from version 1 because:

- Portia does not yet have a mailing workflow;
- full addresses are highly sensitive;
- address sharing does not establish person identity;
- and storing addresses would create retention and disclosure obligations
  without a current product need.

Website, social-media handle, messaging-app account, portal identity, and other
arbitrary contact kinds are also deferred.

A later version may add a contact kind only for a concrete accepted workflow.

## 10.6 Contact-value branches

The final schema will use a discriminated union.

### Email

Conceptually:

```json
{
  "kind": "email",
  "address": "person@example.test",
  "label": "personal"
}
```

Email labels are:

```text
personal
work
other
```

`other` requires a concise non-sensitive `other_label`.

### Phone

Conceptually:

```json
{
  "kind": "phone",
  "number": "+1 555 010 0100",
  "label": "mobile"
}
```

Phone labels are:

```text
mobile
home
work
other
```

`other` requires a concise non-sensitive `other_label`.

## 10.7 Entered representation and normalization

The canonical Contact Point preserves the reviewed human-readable value entered
or imported into Portia.

Application validation may normalize a value in memory for:

- structural validation;
- exact-current duplicate checks;
- teacher-facing search;
- or duplicate-candidate generation.

Portia v1 does not persist an unsalted deterministic hash of an email address or
phone number as a general lookup identity.

Email addresses and phone numbers have low enough entropy that such hashes may
be reversible through guessing.

A normalized value:

- is not Actor identity;
- is not Contact Point identity;
- does not prove ownership or control;
- and does not prove that two Actors are the same person.

## 10.8 Contact identity and value changes

The exact contact value is material to one Contact Point record.

After activation, changing:

```text
email.address
phone.number
contact.kind
```

requires a new Contact Point successor.

It must not be represented as a hidden in-place amendment.

This preserves:

- historical communication context;
- exact source provenance;
- correction history;
- and the distinction between an obsolete value and a value that was always
  wrong.

Nonmaterial label, preference, source-detail, or verification corrections may
use Actor-directory amendment when semantic equivalence remains true.

## 10.9 Shared values across Actors

The same contact value may legitimately appear under several Actors, including:

- a shared household phone;
- a shared family email;
- an office switchboard;
- a department inbox;
- or an external provider's shared scheduling address.

A shared value may create a duplicate-review signal.

It does not establish duplicate Actor identity and does not permit automatic
consolidation.

## 10.10 Contact-point invariants

1. One Contact Point belongs to one Actor.
2. One Contact Point contains one contact value.
3. Contact identity is `actor_id + contact_point_id`.
4. Contact values never appear in identifiers or paths.
5. Email and phone are the only version-1 kinds.
6. Postal address and arbitrary handles are excluded.
7. Contact-value normalization is not identity.
8. Contact-value changes after activation create a successor.
9. Shared values do not prove duplicate Actor identity.
10. A Communication act is not a Contact Point record.

---

# 11. Approved Decision 7: Actor Contact Point Envelope, Privacy, and Lifecycle

## 11.1 Required envelope

Actor Contact Point v1 will contain exactly:

```text
schema_version
record_type
module_id
actor_id
contact_point_id
status
contact
use_preference
source
verification
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

Constants are:

```text
schema_version = "1"
record_type = "actor_contact_point"
module_id = "portia"
```

## 11.2 Use preference

`use_preference` is:

```text
preferred
alternate
unspecified
```

It is a teacher-local current presentation preference.

It does not:

- authorize contact;
- establish consent;
- override a consuming Communication's purpose or restrictions;
- guarantee deliverability;
- or require a future Communication to use that method.

Application validation permits at most one active `preferred` Contact Point per
Actor and contact kind.

If no active Contact Point is preferred, selection remains explicit.

## 11.3 Contact source

`source` is a closed object whose initial source kinds are:

```text
actor_provided
related_person_provided
student_provided
school_record
professional_directory
communication_observed
import
other
```

Source means:

> The locally recorded origin from which the teacher or import workflow obtained
> the contact value.

It does not establish that the value is current, controlled by the Actor, or
lawfully usable for every purpose.

The final schema will require bounded detail for:

```text
school_record
professional_directory
import
other
```

The detail must identify the source sufficiently for local review without
copying an unrestricted narrative or credential.

## 11.4 Verification object

`verification` records only the local verification state:

```text
unverified
locally_reviewed
actor_confirmed
```

### `unverified`

The value was recorded but has not completed local review.

### `locally_reviewed`

The local operator reviewed the source and accepted the value for possible
Portia use.

This does not prove current Actor control or successful delivery.

### `actor_confirmed`

The represented Actor directly confirmed the value according to the recorded
local process.

This still does not prove:

- authenticated digital control;
- legal identity;
- future deliverability;
- consent for every communication;
- or institutional authority.

For `locally_reviewed` and `actor_confirmed`, the verification object records:

```text
observed_at
observed_by
```

For `unverified`, both are null.

Application validation enforces branch consistency.

## 11.5 Contact lifecycle

Contact Point statuses are:

```text
proposed
active
inactive
invalidated
superseded
```

### `proposed`

The Contact Point is structurally present but not accepted for ordinary current
selection.

Imported unreviewed contact values begin as proposed.

### `active`

The Contact Point is eligible for explicit current selection, subject to
purpose, privacy, authorization, relationship, and Communication policy.

### `inactive`

The Contact Point remains historically valid but is excluded from ordinary
current selection.

Representative reasons include:

- value no longer used;
- Actor requested another method;
- organization assignment changed;
- teacher no longer expects the method to be useful;
- or value has not been recently confirmed.

Inactive does not mean the value was false.

### `invalidated`

The Contact Point must not be treated as a valid current contact assertion and no
accepted corrected Contact Point presently replaces it.

Representative grounds include:

- entered for the wrong Actor;
- unsupported value;
- prohibited sensitive value;
- or source proved unreliable.

### `superseded`

An accepted successor Contact Point provides the corrected representation.

Superseded is absolute terminal.

## 11.6 Contact transition matrix

| From | Permitted destinations |
| --- | --- |
| `proposed` | `active`, `inactive`, `invalidated`, `superseded` |
| `active` | `inactive`, `invalidated`, `superseded` |
| `inactive` | `active`, `invalidated`, `superseded` |
| `invalidated` | `superseded` only |
| `superseded` | none |

The status does not change automatically because:

- time passed;
- a delivery failed;
- another Contact Point became preferred;
- the Actor became inactive;
- or the related student left a roster.

Those conditions may produce review or an explicit coordinated operation.

## 11.7 Obsolescence versus correction

Portia distinguishes:

```text
obsolete but historically correct
from
incorrect canonical value
```

An obsolete but historically correct value ordinarily transitions:

```text
active -> inactive
```

A materially incorrect value with an accepted corrected successor transitions:

```text
active or inactive -> superseded
```

A materially incorrect value without a successor transitions:

```text
active or inactive -> invalidated
```

Portia must not classify ordinary obsolescence as falsity.

## 11.8 Contact supersession

A Contact Point successor uses exact predecessor references.

Initial reasons are:

```text
value_corrected
wrong_actor_corrected
duplicate_consolidated
contract_migrated
other
```

`other` requires bounded detail.

Ordinary replacement is one-to-one.

Duplicate Contact Point consolidation may be many-to-one only when review
confirms that the predecessor records captured the same contact assertion for
the same Actor.

## 11.9 Contact privacy rules

Contact values are privacy-sensitive canonical payload.

They must not be copied into:

- Actor identifiers;
- Contact Point identifiers;
- paths;
- ordinary Actor display snapshots;
- Actor-to-student relationship snapshots;
- lock records;
- integrity-finding keys;
- ordinary operation intent facts;
- duplicate-candidate titles;
- or nonsensitive derived summary indexes.

Operation journals may preserve:

- typed Contact Point identity;
- contract version;
- workspace-relative path;
- content fingerprint;
- byte length;
- and bounded non-payload state facts.

They must not duplicate the contact value merely to support recovery.

Staging and canonical files necessarily contain the proposed or accepted
payload and therefore require deployment-appropriate filesystem protection.

## 11.10 Contact discovery and current selection

Loading one Actor's Contact Points requires bounded discovery beneath:

```text
portia/actors/<actor_id>/records/actor_contact_point/
```

Current selection requires:

- structurally valid canonical records;
- path and identity agreement;
- reconciled lifecycle history;
- absence of blocking Quarantine;
- current status of `active`;
- and consuming-workflow eligibility.

A missing Contact Point index does not prove that the Actor has no Contact
Points.

## 11.11 Contact application validation

Application validation must establish:

- canonical path agreement;
- exact Actor ownership;
- supported contact syntax;
- lifecycle/history reconciliation;
- legal status transitions;
- supersession reconciliation;
- no self-reference or cycle;
- contact-value-change replacement rules;
- at most one active preferred Contact Point per kind;
- no duplicate current Contact Point for the same normalized Actor-owned value;
- source and verification consistency;
- import review gates;
- privacy-safe diagnostics;
- typed operation targeting;
- and recoverable persistence.

## 11.12 Contact rejected alternatives

### Contact arrays embedded in Actor

Rejected because values have independent provenance, lifecycle, sensitivity, and
correction requirements.

### Email or phone as Contact Point identity

Rejected because contact values change, may be shared, and are sensitive.

### Global verified/unverified boolean

Rejected because local review, direct Actor confirmation, deliverability, legal
identity, and consent are different claims.

### Automatic inactivation after time elapsed

Rejected because age alone does not establish that a contact method is obsolete.

### Unsalted deterministic contact hash

Rejected because low-entropy contact values may be recovered through guessing.

---

# 12. Approved Decision 8: Actor-to-Student Relationship Semantic Unit and Identity

## 12.1 Decision

Recurring Actor-to-student relationships use a separate canonical child record:

```text
actor_student_relationship@1
```

One record represents:

> One locally accepted relationship assertion between one exact Actor and one
> exact Core roster-qualified student identity.

The Actor owns the relationship record.

The target student remains owned and resolved by Core through:

```text
class_id + student_id
```

## 12.2 Relationship identity

Actor-to-Student Relationship identifiers use:

```text
asrel_<opaque-id>
```

The public identifier contract will be:

```text
portia_actor_student_relationship_id@1
```

The identifier must not encode:

- Actor name;
- student identity;
- class;
- relationship type;
- legal status;
- school;
- or lifecycle state.

Stable child identity is:

```text
actor_id + relationship_id
```

## 12.3 Canonical storage

The relationship is stored beneath its Actor owner:

```text
portia/actors/<actor_id>/
  records/
    actor_student_relationship/
      <relationship_id>.json
```

The relationship is not duplicated beneath:

- the target class;
- the target student's roster;
- an Event;
- a Support Process;
- or another Actor.

Reverse navigation from a roster student to Actor relationships is derived.

## 12.4 Exact target student

The relationship target composes the existing identity-only
`roster_student_ref@1`:

```json
{
  "class_id": "english10_p2",
  "student_id": "1001"
}
```

The same real-world student appearing in two Core rosters remains two distinct
roster-qualified identities unless a future shared identity authority explicitly
links them.

Portia therefore does not silently apply one Actor relationship across several
rosters.

When the teacher needs the relationship available for two roster-qualified
student identities, Portia records two independently reviewable relationship
records.

## 12.5 Initial relationship types

The initial relationship vocabulary is:

```text
parent
guardian
caregiver
family_contact
counselor
case_manager
administrator
support_staff
external_support_provider
other
```

`other` requires bounded detail.

The relationship type is a teacher-local descriptive assertion.

It does not by itself establish:

- legal parentage;
- legal guardianship;
- custody;
- educational decision authority;
- employment;
- case assignment;
- professional licensure;
- access authorization;
- or communication consent.

A future consequential record must preserve its own authority basis.

## 12.6 Relationship versus Actor category

Actor category and Actor-to-student relationship remain independent.

Examples:

- an Actor categorized `family_or_caregiver` may have a `parent` relationship to
  one student and a `family_contact` relationship to another;
- an Actor categorized `school_staff` may be `counselor` for one student and
  have no canonical relationship to another;
- an Actor categorized `external_support_provider` may have a
  `external_support_provider` relationship only where deliberately recorded.

Category does not generate relationship records automatically.

A relationship does not rewrite Actor category automatically.

## 12.7 No household or family graph

Actor-to-Student Relationship v1 does not create:

- a household identity;
- family-unit membership;
- sibling relationships;
- Actor-to-Actor relationships;
- shared custody topology;
- or organization identity.

Several Actors may independently relate to one roster student.

One Actor may independently relate to several roster students.

Those records do not imply relationships among the other people.

## 12.8 Stable relationship reference

Issue #14 will add an exact relationship reference containing:

```text
actor_ref
relationship_id
contract_version
```

Conceptually:

```json
{
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "relationship_id": "asrel_example",
  "contract_version": "1"
}
```

A consuming record may use the exact relationship reference when the canonical
relationship materially supports interpretation.

The reference does not authorize access or action.

## 12.9 Relationship uniqueness

Application validation ordinarily permits at most one active relationship for:

```text
exact Actor
+ exact roster_student_ref
+ relationship_type
```

A second structurally valid record with the same tuple is a duplicate candidate,
not an automatically accepted second current relationship.

Different relationship types may coexist when they represent distinct locally
accepted assertions.

## 12.10 Relationship invariants

1. One relationship has one Actor owner.
2. One relationship targets one exact roster-qualified student.
3. Relationship identity is `actor_id + relationship_id`.
4. Relationship type is not Actor identity.
5. Relationship type is not legal or institutional authority.
6. Actor category does not imply a relationship.
7. A relationship does not silently span several rosters.
8. Reverse student-to-Actor navigation is derived.
9. Duplicate tuples require review.
10. No household or general family graph is introduced.

---

# 13. Approved Decision 9: Relationship Envelope, Basis, Lifecycle, and Correction

## 13.1 Required envelope

Actor-to-Student Relationship v1 will contain exactly:

```text
schema_version
record_type
module_id
actor_id
relationship_id
status
student_ref
relationship
basis
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

Constants are:

```text
schema_version = "1"
record_type = "actor_student_relationship"
module_id = "portia"
```

## 13.2 Relationship object

`relationship` is a closed object containing:

```text
type
detail, conditionally required
```

`detail` is:

- prohibited for standard types unless a later schema branch explicitly permits
  bounded clarification;
- and required when `type = other`.

The relationship object does not contain authority, contact, communication, or
workflow-role fields.

## 13.3 Basis architecture

Every relationship requires one explicit basis branch.

Initial branches are:

```text
local_operator_knowledge
actor_statement
roster_student_statement
school_record
import
other
```

### Local operator knowledge

```text
kind = local_operator_knowledge
```

This records that the local teacher entered the relationship from their own
professional knowledge.

It is not an institutional verification claim.

### Actor statement

```text
kind = actor_statement
source_actor_ref
```

The source may be the relationship's owning Actor or another exact Actor.

The source Actor's statement remains a reported basis, not proof of legal status.

### Roster-student statement

```text
kind = roster_student_statement
source_student_ref
```

The source student may be the target student or another exact roster-qualified
student.

The statement does not become institutional verification.

### School record

```text
kind = school_record
source_label
external_reference, optional
```

This identifies a locally reviewed source sufficiently for audit without copying
an entire school record into the relationship.

It does not make Portia authoritative for the source record.

### Import

```text
kind = import
source_label
external_reference, optional
```

An imported basis ordinarily requires the relationship to begin as proposed.

### Other

```text
kind = other
detail
```

The detail is concise and bounded.

It must not become an unrestricted narrative or contain contact credentials.

## 13.4 Relationship lifecycle

Relationship statuses are:

```text
proposed
active
inactive
invalidated
superseded
```

### `proposed`

The relationship assertion is present but has not completed required local
review.

Imported relationships ordinarily begin proposed.

### `active`

The relationship is accepted for current teacher-local Portia context.

Active does not mean legally or institutionally verified.

### `inactive`

The relationship remains historically valid but is excluded from ordinary
current relationship selection.

Representative reasons include:

- relationship no longer current;
- assignment ended;
- student left the relevant context;
- Actor no longer performs the role;
- or teacher chose to retain it only as history.

### `invalidated`

The assertion must not be treated as valid current relationship context and no
accepted corrected successor presently replaces it.

### `superseded`

An accepted successor relationship provides the corrected representation.

Superseded is absolute terminal.

## 13.5 Relationship transition matrix

| From | Permitted destinations |
| --- | --- |
| `proposed` | `active`, `inactive`, `invalidated`, `superseded` |
| `active` | `inactive`, `invalidated`, `superseded` |
| `inactive` | `active`, `invalidated`, `superseded` |
| `invalidated` | `superseded` only |
| `superseded` | none |

The relationship does not change lifecycle automatically because:

- the target roster changes;
- the student is removed from the current roster;
- the Actor becomes inactive;
- the school year changes;
- a date passes;
- or the relationship is not recently used.

Those conditions may create a review requirement.

## 13.6 Roster resolution and historical validity

New activation requires successful resolution of the exact `student_ref` against
the applicable current Core roster.

Later failure to resolve the historical student reference does not silently
invalidate or delete the relationship.

Portia reports the current resolution condition separately, such as:

```text
current
historical_unresolved
roster_unavailable
malformed
indeterminate
```

A historical unresolved relationship remains exactly identifiable from its
stored roster-qualified reference and provenance.

## 13.7 Material relationship fields

The following fields are material to relationship identity and meaning:

```text
actor_id
student_ref
relationship.type
basis branch and source identity
```

Changing any of those after activation ordinarily requires a successor
relationship record.

It must not be concealed as an in-place amendment.

Examples include:

- changing the target student;
- changing `parent` to `counselor`;
- changing the source Actor;
- changing from a reported statement to a different school-record basis;
- or moving the record to another Actor.

## 13.8 Nonmaterial amendment

Potentially nonmaterial changes include:

- punctuation or formatting in bounded detail;
- correcting a source label without changing source identity;
- correcting a nonidentity external-reference transcription;
- or another field explicitly declared amendable by the final contract.

The semantic-equivalence test must pass.

No amendment may change:

- Actor owner;
- target student;
- relationship type;
- basis branch;
- source person identity;
- or lifecycle status.

## 13.9 Relationship supersession

Initial supersession reasons are:

```text
relationship_corrected
wrong_actor_corrected
wrong_student_corrected
basis_corrected
duplicate_consolidated
contract_migrated
other
```

`other` requires bounded detail.

Ordinary correction is one-to-one.

Duplicate consolidation may be many-to-one only when review confirms the same
Actor, same exact student, same relationship type, and same underlying
relationship assertion.

Records that preserve independently meaningful source assertions are related but
distinct and must not be consolidated merely because the relationship tuple
matches.

## 13.10 Relationship authority rules

An active relationship may support user-interface context and record selection.

It does not by itself establish:

- permission to disclose student records;
- legal educational decision authority;
- consent;
- custody;
- emergency pickup authorization;
- authority to approve an intervention;
- authority to make a Determination;
- or authority to receive a Communication.

A consequential consuming record must preserve the applicable purpose,
authorization, policy, or decision basis independently.

Portia must not expose a button or API that treats:

```text
relationship.type = guardian
```

as sufficient authorization for disclosure.

## 13.11 Relationship application validation

Application validation must establish:

- path and Actor ownership agreement;
- exact roster-student resolution for current activation;
- historical-resolution behavior;
- allowed relationship type;
- basis branch completeness;
- source Actor or source student resolution where used;
- import review gates;
- lifecycle/history reconciliation;
- legal transition;
- material-field replacement rules;
- supersession reconciliation;
- no self-reference or cycle;
- active tuple uniqueness;
- duplicate versus independently meaningful assertion;
- authority limitation;
- privacy-safe diagnostics;
- typed operation targeting;
- and recoverable persistence.

## 13.12 Relationship rejected alternatives

### Relationship labels embedded in Actor

Rejected because one Actor may have different relationships to several students
and relationship claims require independent source and lifecycle.

### Name-qualified student target

Rejected because Core roster identity is `class_id + student_id`.

### Relationship inferred from Communication history

Rejected because communication recurrence does not prove the represented
relationship.

### Active relationship as legal verification

Rejected because Portia is teacher-local and does not adjudicate institutional or
legal authority.

### Automatic cross-roster propagation

Rejected because Core does not provide workspace-wide student identity.

### Automatic inactivation at school-year rollover

Rejected because relationship lifecycle changes require explicit review and may
remain relevant across years.

---

# 14. Approved Decision 10: Historical Actor Bindings and Shared Child Lifecycle

## 14.1 Decision

Portia will standardize three distinct concepts:

```text
stable Actor identity
exact Actor-directory child identity
historical display or relationship snapshot
```

They must not be collapsed into one universal person object.

## 14.2 Actor binding in consuming records

When a consuming record references an Actor as a person, the standard historical
binding is:

```text
actor_ref
person_display_snapshot
contextual role
```

Conceptually:

```json
{
  "actor_ref": {
    "actor_id": "actr_example"
  },
  "display_snapshot": {
    "display_name": "Maria Smith"
  },
  "role": "communication_recipient"
}
```

The role belongs to the consuming record.

The binding does not contain current contact values.

## 14.3 Canonical relationship binding

When an Actor-to-Student Relationship is materially relevant, a consuming record
may additionally preserve:

```text
exact relationship reference
relationship snapshot
```

The relationship snapshot v1 will contain exactly:

```text
relationship_type
```

Conceptually:

```json
{
  "relationship_ref": {
    "actor_ref": {
      "actor_id": "actr_example"
    },
    "relationship_id": "asrel_example",
    "contract_version": "1"
  },
  "relationship_snapshot": {
    "relationship_type": "parent"
  }
}
```

The snapshot is a bounded historical display aid.

It does not contain:

- source basis;
- student name;
- contact information;
- authority;
- status;
- verification language;
- or successor identity.

## 14.4 Contextual role without canonical relationship

A consuming record may use an Actor without an Actor-to-Student Relationship
when the workflow role does not assert a recurring student relationship.

Examples include:

- visitor to one Event;
- interpreter for one Communication;
- meeting participant;
- Account source;
- consulted administrator;
- or external provider participating in one bounded workflow.

Portia must not create a canonical Actor-to-Student Relationship merely because
an Actor appeared in one workflow.

## 14.5 Contact selection in future Communications

A future Communication contract may preserve:

- exact Actor reference;
- historical display snapshot;
- contextual participant role;
- exact Contact Point reference, when used;
- communication channel;
- direction;
- purpose;
- and delivery evidence.

The Contact Point remains the canonical reusable method.

The Communication remains the canonical communication act.

Issue #14 does not define the Communication wire shape.

## 14.6 No current-data rewrite

When the current Actor, Contact Point, or Relationship changes, Portia must not
rewrite:

- Event Participant display snapshots;
- Account source snapshots;
- historical Communication participants;
- historical relationship snapshots;
- or prior exact Contact Point references.

A user interface may display current resolution alongside the recorded snapshot,
clearly labeled.

## 14.7 Shared Actor-directory lifecycle family

Actor, Actor Contact Point, and Actor-to-Student Relationship will share one
workspace-scoped append-only lifecycle-transition family:

```text
actor_directory_lifecycle_transition@1
```

The transition is stored under the Actor root:

```text
portia/actors/<actor_id>/
  records/
    actor_lifecycle_transition/
      <transition_id>.json
```

It targets exactly one of:

```text
Actor root
Actor Contact Point
Actor-to-Student Relationship
```

The target is compact because the containing Actor root supplies `actor_id`.

The transition will reuse the existing opaque `lct_` identifier contract unless
the schema implementation audit finds a concrete incompatibility.

## 14.8 Shared lifecycle principles

The Actor-directory lifecycle family preserves the accepted Issue #12 model:

```text
persisted current status
+ creation baseline
+ append-only selected transition history
= validated current state
```

It requires:

- one target per transition;
- explicit `previous_transition` chaining;
- no timestamp sorting;
- same-target predecessor agreement;
- branch and cycle detection;
- current-status reconciliation;
- record-family transition legality;
- and coordinated status-plus-transition persistence.

The detailed envelope, reason vocabulary, chronology, and history-correction
contract belong to the next slice.

## 14.9 Shared Actor-directory amendment family

Actor, Contact Point, and Actor-to-Student Relationship will share one
workspace-scoped amendment family:

```text
actor_directory_amendment@1
```

It is stored under the Actor root and targets exactly one Actor-directory record.

The amendment will reuse the existing opaque `amd_` identifier contract unless
the schema implementation audit finds a concrete incompatibility.

The amendment must preserve:

- exact prior and resulting property state;
- explicit amendable paths;
- immutable append-only history;
- target `updated_at` precondition;
- and no lifecycle mutation.

Sensitive Contact Point prior values require special handling.

The next slice must decide whether a Contact Point amendment may retain a prior
sensitive value or whether all value-affecting changes are categorically
replacement-only.

Decisions 6–7 currently require contact value changes to use replacement, which
substantially limits sensitive prior-value exposure in amendments.

## 14.10 Child-record behavior when Actor state changes

An Actor lifecycle change does not automatically rewrite child statuses.

When an Actor becomes inactive:

- active Contact Points and Relationships remain canonical;
- ordinary current Actor selection is blocked or de-emphasized;
- and consuming workflows evaluate Actor eligibility before use.

When an Actor becomes invalidated or superseded:

- new ordinary use of its child records is blocked;
- child records remain historically resolvable;
- and explicit review determines whether any child requires independent
  invalidation, supersession, reassignment, or exceptional removal.

Portia must not perform an automatic lifecycle cascade.

A coordinated Actor correction may include explicit child operations when
preflight determines they are necessary.

## 14.11 Broken and historical resolution

Actor-directory resolution distinguishes:

```text
current
inactive
invalidated
superseded
missing
malformed
quarantined
historical_child_under_noncurrent_actor
authorization_limited
indeterminate
```

A missing current Actor index does not prove a missing Actor.

A missing or malformed Actor record does not authorize reconstruction from:

- contact values;
- relationship records;
- historical display names;
- or consuming-record snapshots.

## 14.12 Historical-binding invariants

1. Actor identity, child identity, and snapshots remain distinct.
2. Contextual roles belong to consuming records.
3. Canonical student relationships are referenced only when materially relevant.
4. Relationship snapshots contain no authority or contact data.
5. Contact values are not copied into ordinary person snapshots.
6. Current Actor changes do not rewrite historical bindings.
7. One shared Actor-directory lifecycle family governs root and child statuses.
8. One shared Actor-directory amendment family governs allowed nonmaterial edits.
9. Actor lifecycle changes do not automatically cascade to children.
10. Broken identity is never reconstructed from display or contact similarity.

---

# 15. Approved Decision 11: Exact Actor-Directory Targets and History Ownership

## 15.1 Shared exact target

Actor, Contact Point, and Actor-to-Student Relationship history will use one
closed exact target union:

```text
exact_actor_directory_record_ref@1
```

The union has exactly three branches:

```text
actor
actor_contact_point
actor_student_relationship
```

Conceptually:

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

```json
{
  "kind": "actor_contact_point",
  "contact_point_ref": {
    "actor_ref": {
      "actor_id": "actr_example"
    },
    "contact_point_id": "acp_example",
    "contract_version": "1"
  }
}
```

```json
{
  "kind": "actor_student_relationship",
  "relationship_ref": {
    "actor_ref": {
      "actor_id": "actr_example"
    },
    "relationship_id": "asrel_example",
    "contract_version": "1"
  }
}
```

The final schema names may remove one redundant nested `actor_ref` label while
preserving the same semantics.

The union does not include:

- a class-owned Portia work;
- a generic local record;
- a workspace;
- an operation;
- an organization;
- or a roster student by itself.

A roster student is the target of an Actor-to-Student Relationship. It is not an
Actor-directory record owned by Portia.

## 15.2 Exact ownership

Every branch contains the owning Actor identity.

This permits application validation to establish:

- the expected Actor root;
- the expected record-family directory;
- the expected canonical filename;
- the expected public contract version;
- and the bounded history location.

A child-record target whose embedded Actor differs from the containing Actor root
is invalid.

## 15.3 Stable identity versus observed representation

An exact Actor-directory reference identifies:

```text
stable record identity
+ expected public contract version
```

It does not contain:

- a filesystem path;
- content bytes;
- content digest;
- byte length;
- `updated_at`;
- lifecycle status;
- display data;
- contact data;
- relationship data;
- or Quarantine state.

An operation that changes a current representation must separately preserve its
observed expected prior state, including an exact content fingerprint and
validated workspace-relative path.

This maintains the accepted separation among:

```text
identity
path
observed representation
```

## 15.4 History ownership

Every lifecycle transition, lifecycle-history correction, and amendment is
stored beneath the Actor root that owns its target.

The canonical history topology is:

```text
portia/actors/<actor_id>/
  records/
    actor_directory_lifecycle_transition/
      <transition_id>.json
    actor_directory_lifecycle_history_correction/
      <correction_id>.json
    actor_directory_amendment/
      <amendment_id>.json
```

All three target families share these history collections.

Application validation must not assume that a transition or amendment applies to
the Actor root merely because it is stored beneath the Actor root. The contained
typed target remains authoritative.

## 15.5 Identifier reuse

Issue #14 will reuse the existing scope-neutral identifier contracts:

```text
portia_lifecycle_transition_id@1
portia_lifecycle_history_correction_id@1
portia_amendment_id@1
```

Therefore Actor-directory records use:

```text
lct_<opaque-id>
lhc_<opaque-id>
amd_<opaque-id>
```

New Actor-specific identifier prefixes are unnecessary.

The record envelopes, typed targets, canonical paths, and public contract names
distinguish the Actor-directory history families from the existing class/work
history families.

Identifier reuse does not permit one history record to exist in two canonical
locations.

## 15.6 Exact history references

Within one Actor root:

- a lifecycle transition may identify one prior transition by
  `previous_transition_id`;
- a lifecycle-history correction may identify one prior correction by
  `previous_correction_id`;
- and an amendment may identify one prior amendment for the same target by
  `previous_amendment_id`.

The owning `actor_id` and target are inherited from the containing history
record and must agree across each predecessor chain.

Predecessor identifiers are not globally resolved without the containing Actor
root and record-family context.

## 15.7 No generic workspace substitute

An exact Actor-directory record target must be used whenever one Actor,
Contact Point, or Actor-to-Student Relationship is:

- transitioned;
- amended;
- corrected;
- migrated;
- removed;
- quarantined;
- locked;
- scanned;
- or changed through a coordinated operation.

A workspace target may additionally describe the broad operation scope. It
cannot replace the exact primary target.

## 15.8 Target invariants

1. The target union is closed.
2. Every target contains exact Actor ownership.
3. Contract version is explicit.
4. Paths and fingerprints are operation evidence, not target identity.
5. History is stored beneath the owning Actor root.
6. Existing lifecycle, history-correction, and amendment identifier contracts
   are reused.
7. Predecessor IDs resolve within one Actor root and history family.
8. A generic workspace target cannot stand in for an exact Actor-directory
   record.

---

# 16. Approved Decision 12: Actor-Directory Lifecycle Transition and Selected History

## 16.1 Public contract

The shared lifecycle-transition contract will be:

```text
actor_directory_lifecycle_transition@1
```

Schema path:

```text
schemas/v1/actors/actor-directory-lifecycle-transition.schema.json
```

Record type:

```text
actor_directory_lifecycle_transition
```

## 16.2 Required envelope

The record contains exactly:

```text
schema_version
record_type
module_id
actor_id
transition_id
target
prior_status
new_status
reason
previous_transition_id
effective_at
recorded_at
recorded_by
operation_ref
```

Constants are:

```text
schema_version = "1"
record_type = "actor_directory_lifecycle_transition"
module_id = "portia"
```

`actor_id` must equal the Actor owner embedded in `target`.

`operation_ref` uses the accepted identity-only operation reference. The
referenced Operation Journal remains operational evidence and does not replace
the lifecycle transition as the canonical domain assertion.

## 16.3 Status vocabulary

The shared structural status vocabulary is:

```text
proposed
active
inactive
invalidated
superseded
```

All three initial Actor-directory record families use that vocabulary.

JSON Schema validates only vocabulary membership and that:

```text
prior_status != new_status
```

Application validation enforces the record-family transition matrix and all
required reason compatibility.

## 16.4 Creation baseline

Initial creation does not create a synthetic lifecycle transition.

The canonical record establishes its creation baseline through:

```text
status
creation_source
created_at
created_by
```

The first lifecycle transition has:

```text
previous_transition_id = null
```

Its `prior_status` must equal the canonical creation status.

Every later transition identifies exactly one immediate predecessor transition.

## 16.5 Predecessor-selected order

Lifecycle order is determined only by the explicit predecessor chain.

It is not inferred from:

- `effective_at`;
- `recorded_at`;
- filename;
- directory order;
- lexical identifier order;
- modification time;
- or the greatest identifier.

A valid selected transition chain must:

1. start with a transition whose predecessor is null;
2. begin at the canonical creation status;
3. have exactly one immediate predecessor for each later entry;
4. contain no repeated transition;
5. contain no branch in the selected chain;
6. obey the record-family transition matrix;
7. end at the current canonical status;
8. and remain compatible with accepted lifecycle-history corrections.

## 16.6 Effective and recorded time

`effective_at` states when the lifecycle change took effect in the teacher-local
Portia workflow.

`recorded_at` states when the transition record was accepted.

Version 1 requires:

```text
effective_at <= recorded_at
```

Future-dated automatic transitions are not supported.

A later workflow may record a transition whose effect began earlier than its
entry, provided the actor is authorized and the reason and surrounding evidence
support that chronology.

Time never changes status automatically.

## 16.7 Shared reason vocabulary

The structural reason vocabulary is:

```text
review_completed
made_inactive
reactivated
identity_invalidated
assertion_invalidated
contact_obsolete
relationship_ended
corrected_by_successor
duplicate_consolidated
wrong_actor_corrected
wrong_student_corrected
roster_student_collision
contract_migrated
prohibited_payload
source_disproved
other
```

`other` requires bounded non-sensitive detail.

Application validation restricts reasons by:

- target record family;
- prior status;
- new status;
- successor topology;
- and operation kind.

## 16.8 Actor transition rules

Actor transitions use:

| From | Permitted destinations |
| --- | --- |
| `proposed` | `active`, `inactive`, `invalidated`, `superseded` |
| `active` | `inactive`, `invalidated`, `superseded` |
| `inactive` | `active`, `invalidated`, `superseded` |
| `invalidated` | `superseded` |
| `superseded` | none |

Representative reason compatibility includes:

```text
proposed -> active: review_completed
active -> inactive: made_inactive
inactive -> active: reactivated
any nonterminal -> invalidated: identity_invalidated,
                                      roster_student_collision,
                                      prohibited_payload,
                                      source_disproved,
                                      other
any eligible predecessor -> superseded: corrected_by_successor,
                                       duplicate_consolidated,
                                       contract_migrated,
                                       other
```

`roster_student_collision` is Actor-only.

## 16.9 Contact Point transition rules

Contact Point uses the same matrix.

Representative reason compatibility includes:

```text
proposed -> active: review_completed
active -> inactive: contact_obsolete
inactive -> active: reactivated
any nonterminal -> invalidated: assertion_invalidated,
                                      wrong_actor_corrected,
                                      prohibited_payload,
                                      source_disproved,
                                      other
any eligible predecessor -> superseded: corrected_by_successor,
                                       duplicate_consolidated,
                                       wrong_actor_corrected,
                                       contract_migrated,
                                       other
```

A delivery failure alone does not change lifecycle.

## 16.10 Actor-to-Student Relationship transition rules

Actor-to-Student Relationship uses the same matrix.

Representative reason compatibility includes:

```text
proposed -> active: review_completed
active -> inactive: relationship_ended
inactive -> active: reactivated
any nonterminal -> invalidated: assertion_invalidated,
                                      wrong_actor_corrected,
                                      wrong_student_corrected,
                                      source_disproved,
                                      other
any eligible predecessor -> superseded: corrected_by_successor,
                                       duplicate_consolidated,
                                       wrong_actor_corrected,
                                       wrong_student_corrected,
                                       contract_migrated,
                                       other
```

A target student leaving the current roster does not automatically end or
invalidate the historical relationship.

## 16.11 Supersession prerequisites

A transition to `superseded` is valid only when:

- the current record contains compatible exact predecessor lineage;
- every named successor exists and validates;
- the successor record was accepted through the coordinated operation;
- the predecessor and successor topology is supported;
- no self-reference or replacement cycle exists;
- and the transition reason agrees with the successor's supersession reason.

The transition does not itself identify the successor. The successor-owned
predecessor lineage remains canonical for replacement topology.

## 16.12 Persisted current status

The mutable canonical Actor-directory record stores its current status.

A lifecycle change requires one recoverable operation that:

1. completes preflight;
2. stages and validates the transition;
3. exclusively creates and read-back verifies the transition;
4. revalidates the exact expected prior current representation;
5. atomically replaces the mutable current record with `status = new_status`;
6. read-back verifies the replacement;
7. reconciles the selected transition chain and current status;
8. and completes any required derived regeneration.

Writing only the transition or only the mutable current status is partial
success requiring recovery.

## 16.13 Persistence ordering

The transition is made durable before the mutable current record is replaced.

This ordering ensures that interruption cannot leave an unexplained accepted
status change.

An interruption after transition acceptance but before current-record
replacement leaves:

```text
durable intended lifecycle evidence
+ unchanged prior current status
+ incomplete operation journal
```

Recovery may:

- complete the current-record replacement;
- determine that an exact replay already completed;
- quarantine contradictory state;
- compensate through explicit accepted history;
- or require review.

It must not delete the accepted transition merely to hide the interruption.

## 16.14 Child independence

Changing Actor lifecycle does not automatically transition:

- Contact Points;
- Actor-to-Student Relationships;
- Events;
- Accounts;
- Communications;
- Supports;
- Determinations;
- or other referencing records.

Those records remain independently canonical.

An Actor becoming inactive or superseded may affect eligibility for future use
and may generate review findings. It does not rewrite child history.

## 16.15 Selected lifecycle state

Without an accepted lifecycle-history correction, the selected history is the
unique valid predecessor chain that:

- begins at the creation baseline;
- contains all accepted nonexcluded transitions required to reach current
  status;
- and terminates at current status.

When an accepted lifecycle-history correction exists, the correction identifies
the selected terminal transition and excluded history evidence.

If selection is:

- branched;
- cyclic;
- missing;
- inconsistent with current status;
- or dependent on an unavailable contract,

the Actor-directory record is not silently resolved.

It produces an integrity result and may require Quarantine.

## 16.16 Lifecycle invariants

1. Creation status is the baseline.
2. Every later status change has one transition.
3. Transition order comes from predecessor identity.
4. Effective time does not select history.
5. Future automatic transitions are unsupported.
6. Reason legality is record-family-specific.
7. Supersession requires accepted successor topology.
8. Transition acceptance precedes current-record replacement.
9. Current status and selected history must reconcile.
10. Actor lifecycle never cascades automatically to child or consuming records.

---

# 17. Approved Decision 13: Actor-Directory Lifecycle-History Correction

## 17.1 Public contract

The shared history-correction contract will be:

```text
actor_directory_lifecycle_history_correction@1
```

Schema path:

```text
schemas/v1/actors/
  actor-directory-lifecycle-history-correction.schema.json
```

Record type:

```text
actor_directory_lifecycle_history_correction
```

## 17.2 Purpose

A lifecycle-history correction records a reviewed replacement selection over
existing append-only transition evidence.

It is used when accepted transition records contain:

- an accidental branch;
- an incorrect transition that must be excluded;
- a superseded prior correction;
- an invalid predecessor choice;
- or another history-selection defect that cannot be solved by deleting or
  rewriting accepted transition files.

A correction does not mutate or delete a transition.

## 17.3 Required envelope

The correction contains exactly:

```text
schema_version
record_type
module_id
actor_id
correction_id
target
selected_terminal_transition_id
excluded_transition_ids
replacement_transition_ids
previous_correction_id
rationale
recorded_at
recorded_by
operation_ref
```

Constants are:

```text
schema_version = "1"
record_type = "actor_directory_lifecycle_history_correction"
module_id = "portia"
```

## 17.4 Selected terminal transition

`selected_terminal_transition_id` identifies the terminal transition of the
complete corrected selected chain.

It may be null only when the corrected selected history intentionally returns to
the creation baseline and the current canonical status equals that baseline.

The complete selected chain is reconstructed by following predecessor links from
the terminal transition to the null predecessor.

The correction does not copy a second mutable transition sequence.

## 17.5 Excluded transitions

`excluded_transition_ids` is a nonempty unique array.

Each excluded transition must:

- exist beneath the same Actor root;
- target the same exact Actor-directory record;
- be outside the corrected selected chain;
- and be materially relevant to the defect being corrected.

A correction must not list unrelated transitions merely to create a complete
inventory.

Excluded transitions remain canonical evidence and historically inspectable.

## 17.6 Replacement transitions

`replacement_transition_ids` identifies newly accepted transition records that
replace incorrect transition assertions.

It may be empty when correction only selects among already accepted branches.

When nonempty, each replacement transition must:

- target the same record;
- be created before the correction;
- participate in the selected corrected chain;
- be accepted through the same coordinated repair operation or a documented
  prerequisite operation;
- and preserve the intended legal state progression.

A correction does not alter the effective time, reason, status, or predecessor
of an existing transition.

Incorrect facts require a new replacement transition.

## 17.7 Correction predecessor chain

The first correction has:

```text
previous_correction_id = null
```

Every later correction identifies exactly one immediately preceding selected
correction for the same target.

Correction order is determined by predecessor identity, not timestamp or
identifier order.

The current correction is the unique valid terminal correction in the
correction predecessor graph.

A branch, cycle, or missing predecessor makes current history selection
indeterminate.

## 17.8 Current-status reconciliation

A history correction does not directly change the mutable current status field.

The corrected selected transition chain must end at the current canonical status.

When the repaired selected history requires a different current status, the
repair operation must also perform an explicit current-record replacement and,
where domain meaning changed, create the required new lifecycle transition.

The correction cannot silently relabel current status.

## 17.9 Correction chronology

`recorded_at` is the correction acceptance time.

The rationale may explain a historical defect, but the correction does not
pretend it existed at the earlier transition time.

Application validation must ensure:

- every referenced transition was accepted before the correction;
- every referenced prior correction was accepted before the correction;
- and the operation chronology is coherent.

## 17.10 Correction rationale

`rationale` is bounded nonempty text.

It may describe:

- the invalid branch;
- the selected valid chain;
- why replacement transitions were required;
- and the reviewed correction basis.

It must not duplicate:

- contact values;
- unrestricted family or student narratives;
- credentials;
- removed payload;
- or unrelated sensitive information.

Machine-readable transition identities carry the exact evidence.

## 17.11 Persistence ordering

A repair operation orders writes as follows:

1. create any required replacement transition records;
2. create the new history-correction record;
3. replace the mutable current record only if required for reconciliation;
4. verify the corrected selected history and current state;
5. regenerate affected derived views.

Accepted old transitions and corrections remain unchanged.

## 17.12 History-correction invariants

1. A correction selects history; it does not rewrite history.
2. Excluded transitions remain canonical evidence.
3. Incorrect transition facts require replacement transitions.
4. The selected chain is reconstructed from one terminal transition.
5. Correction order is predecessor-selected.
6. Correction branches and cycles are invalid.
7. Corrected history must reconcile with current status.
8. Correction rationale is privacy-minimized.
9. Repair writes preserve all prior transition and correction evidence.
10. Current history is never selected from the newest timestamp or greatest
    identifier.

---

# 18. Approved Decision 14: Actor-Directory Amendment and Nonmaterial Correction

## 18.1 Public contract

The shared amendment contract will be:

```text
actor_directory_amendment@1
```

Schema path:

```text
schemas/v1/actors/actor-directory-amendment.schema.json
```

Record type:

```text
actor_directory_amendment
```

## 18.2 Purpose

An Actor-directory amendment records a reviewed nonmaterial correction to one
mutable current Actor-directory record while preserving the same represented
identity or assertion.

An amendment is valid only when the before and after records remain semantically
the same:

- Actor person;
- Contact Point assertion;
- or Actor-to-Student Relationship assertion.

Material identity or assertion changes require a new successor record.

## 18.3 Required envelope

The amendment contains exactly:

```text
schema_version
record_type
module_id
actor_id
amendment_id
target
changes
prior_fingerprint
resulting_fingerprint
previous_amendment_id
effective_at
recorded_at
recorded_by
operation_ref
```

Constants are:

```text
schema_version = "1"
record_type = "actor_directory_amendment"
module_id = "portia"
```

## 18.4 Exact representation binding

`prior_fingerprint` and `resulting_fingerprint` use the accepted content
fingerprint contract.

Application validation must establish that:

- `prior_fingerprint` matches the exact accepted current bytes observed during
  preflight;
- applying the declared changes to the prior logical value produces the
  resulting logical value;
- `resulting_fingerprint` matches the exact replacement bytes;
- and no unlisted domain field changed.

Mechanical `updated_at` and `updated_by` changes are expected and are not
separate amendment change entries.

## 18.5 Change entries

`changes` is a nonempty bounded array of typed change entries.

Each entry contains:

```text
path
value_kind
before
after
```

Supported value kinds are limited to:

```text
text
nullable_text
token
timestamp
nullable_timestamp
attribution
verification
source
```

The final schema may use record-family-specific branches instead of one universal
value union where that produces safer validation.

Arbitrary JSON values and unrestricted JSON Patch are prohibited.

## 18.6 Actor amendable paths

Actor v1 permits nonmaterial amendment of:

```text
/display/display_name
/display/organization
/display/title
/actor_category
```

Application validation must establish that the represented person remains the
same.

A category change does not establish a new authority or relationship.

These paths are not amendable:

```text
/actor_id
/status
/supersedes
/creation_source
/created_at
/created_by
```

Status changes use lifecycle transition.

Supersession uses material replacement.

Creation provenance is immutable.

## 18.7 Contact Point amendable paths

Contact Point v1 permits nonmaterial amendment of:

```text
/contact/label
/contact/other_label
/use_preference
/source
/verification
```

These paths are not amendable:

```text
/actor_id
/contact_point_id
/status
/contact/kind
/contact/address
/contact/number
/supersedes
/creation_source
/created_at
/created_by
```

Changing contact kind or exact value requires a successor Contact Point.

Correcting the owning Actor requires material replacement.

## 18.8 Actor-to-Student Relationship amendable paths

Relationship v1 permits nonmaterial amendment of:

```text
/relationship/other_detail
/basis/detail
/review
/effective_period/start
/effective_period/end
```

The final schema will permit only fields actually present in the accepted
relationship contract.

These semantic dimensions are not amendable:

```text
/actor_id
/relationship_id
/status
/student_ref
/relationship/type
/basis/kind
/basis/source_person
/supersedes
/creation_source
/created_at
/created_by
```

Changing Actor owner, student target, relationship type, basis kind, or
source-person identity requires a successor Relationship.

## 18.9 Sensitive prior-value treatment

Contact values are never amendment paths.

Therefore the amendment record never copies a prior or resulting email address
or phone number.

Other before and after values must be bounded to the minimum needed to explain
the correction.

Application validation must reject:

- contact values disguised as rationale or labels;
- credentials;
- unrestricted narratives;
- removed payload;
- and unrelated student information.

When a permitted field is itself sensitive under a future contract version, that
version must define an explicit safe amendment representation rather than
falling back to arbitrary JSON.

## 18.10 Historical snapshots

Amending a current Actor display, Contact Point, or Relationship does not rewrite
historical consuming records.

For example, correcting the current Actor display name does not alter:

```text
person_display_snapshot@1
```

already stored in an Event Participant or later domain record.

A consumer may display the recorded snapshot and current Actor metadata
together.

## 18.11 Amendment predecessor chain

The first amendment for one exact target has:

```text
previous_amendment_id = null
```

Every later amendment identifies the immediately preceding accepted amendment
for the same target.

Amendment order is determined by predecessor identity.

A branch, cycle, target mismatch, or missing predecessor is an integrity defect.

An amendment predecessor chain is independent of lifecycle-transition order.

## 18.12 Effective and recorded time

`effective_at` states when the corrected current value should be understood to
apply in Portia.

`recorded_at` states when the amendment was accepted.

Version 1 requires:

```text
effective_at <= recorded_at
```

The amendment does not rewrite historical consuming-record snapshots as of the
earlier effective time.

## 18.13 Persistence ordering

The amendment record is made durable before the mutable current record is
replaced.

The coordinated operation:

1. observes and fingerprints the exact prior current record;
2. validates semantic equivalence and allowed paths;
3. stages the amendment and replacement current record;
4. exclusively creates and verifies the amendment;
5. revalidates the prior fingerprint;
6. atomically replaces and verifies the current record;
7. validates the amendment chain and resulting fingerprint;
8. and regenerates affected derived views.

An accepted amendment with an unchanged current record is incomplete recoverable
state.

The amendment is not deleted to conceal interruption.

## 18.14 Amendment versus lifecycle

An amendment must not change lifecycle status.

A lifecycle transition must not be used to change profile fields.

When one teacher action requires both:

- a nonmaterial profile correction; and
- a lifecycle transition,

the coordinated operation creates both canonical evidence records and performs
one expected-prior current-record replacement containing both accepted effects.

Each record retains its own semantic purpose.

## 18.15 Amendment versus material replacement

An amendment is prohibited when the requested change alters:

- represented Actor person;
- Contact Point exact value or owner;
- Relationship Actor, student, type, or material basis;
- canonical identity;
- record family;
- or contract-significant replacement lineage.

Those changes require:

```text
new successor record
+ predecessor supersession
+ exact reviewed lineage
+ coordinated operation
```

## 18.16 Amendment invariants

1. Amendments preserve semantic identity.
2. Arbitrary JSON Patch is prohibited.
3. Every changed path is explicitly allowed for the target family.
4. Before and after representations are exact and bounded.
5. Fingerprints bind the prior and resulting files.
6. Contact values cannot appear in amendment changes.
7. Status cannot be amended.
8. Historical snapshots are not rewritten.
9. Amendment order is predecessor-selected.
10. Amendment evidence becomes durable before current-record replacement.

---

# 19. Approved Decision 15: Duplicate Candidates and Reviewed Disposition

## 19.1 Decision

Actor duplicate detection is a derived review process.

A duplicate candidate is not a canonical Actor relationship and is not identity
authority.

Issue #14 will not introduce a separate canonical `actor_duplicate_review`
record in version 1.

Instead:

- candidate generation produces an Actor-targeted Integrity Finding;
- the finding uses stable deterministic Actor-set and evaluation keys;
- Finding Acknowledgement records that an authorized person reviewed the exact
  evaluation;
- bounded Finding Suppression may de-emphasize a reviewed candidate until
  relevant evidence changes;
- and confirmed duplicate identity is expressed only through an accepted Actor
  consolidation operation and resulting replacement graph.

This reuses the Issue #13 finding-administration model without creating a second
parallel review system.

## 19.2 Candidate semantic unit

One duplicate-candidate evaluation asks:

> Do these exact current Actor records appear likely enough to represent the same
> human person that authorized human review is required?

The initial candidate set contains two or more exact Actor references.

Candidate-set identity is based on the sorted exact Actor identities and the
candidate rule version.

It does not contain:

- names;
- email addresses;
- phone numbers;
- organizations;
- titles;
- student identifiers;
- or other sensitive payload.

A deterministic candidate key may conceptually use:

```text
rule ID
+ rule version
+ sorted actor IDs
```

The key does not prove duplicate identity.

## 19.3 Candidate evidence kinds

Candidate generation may consider privacy-minimized evidence kinds such as:

```text
display_name_similarity
shared_contact_value
shared_import_identity
shared_relationship_pattern
same_operator_selected_identity
overlapping_organization_and_title
other
```

Evidence should reference exact canonical records where possible.

For example, a shared-contact signal may preserve:

```text
exact Contact Point references
+ equality or normalization rule version
```

It must not copy the contact value into:

- finding keys;
- candidate titles;
- operation summaries;
- ordinary logs;
- or nonsensitive derived projections.

The authorized duplicate-review interface may resolve the underlying canonical
values according to privacy policy.

## 19.4 Candidate-generation limits

The following may create a candidate but cannot confirm identity:

- equal display names;
- similar names;
- equal normalized contact values;
- equal organization and title;
- overlapping student relationships;
- repeated co-occurrence;
- same import source;
- or a confidence score.

One shared household or office contact value may legitimately belong to several
distinct people.

One person may also have several different names and contact values.

## 19.5 Review outcomes

Human review uses these conceptual outcomes:

```text
confirmed_duplicate
related_but_distinct
insufficient_information
candidate_error
```

### `confirmed_duplicate`

The reviewed Actors represent the same human person and satisfy the pure
consolidation requirements in Decision 16.

The review outcome alone does not change canonical state.

A complete consolidation operation remains required.

### `related_but_distinct`

The Actors are connected or similar but represent different people.

The finding may be acknowledged as reviewed.

A bounded suppression may hide the same presentation warning until:

```text
Actor evaluation changes
Contact Point evaluation changes
relationship evaluation changes
rule version changes
policy version changes
or fixed expiry
```

Suppression does not establish a canonical relationship between the Actors.

### `insufficient_information`

Available evidence cannot support either identity equivalence or distinctness.

The finding remains available for future review.

An acknowledgement may record:

```text
awaiting_external_evidence
```

No lifecycle or replacement change follows.

### `candidate_error`

The candidate rule or source evidence was not applicable to the Actor set.

The evaluation may be acknowledged and suppressed until its evaluation inputs
change.

The underlying rule defect may require a separate integrity or implementation
correction.

## 19.6 Actor-targeted Integrity Finding requirement

The existing `integrity_finding@1` target union does not contain an exact Actor
target.

Issue #14 must introduce a new compatible Integrity Finding version or a
distinct Actor-directory finding contract.

The preferred direction is a new `integrity_finding@2` that:

- preserves all version-1 fields and semantics;
- adds exact Actor-directory record targets;
- remains wire-compatible for all existing version-1 target branches;
- and does not add Actor contact values or relationship payload to keys.

Existing version-1 findings remain valid and immutable.

The final operational-integration decision will confirm the exact versioning
approach.

## 19.7 Finding administration

Duplicate-candidate findings use the existing concepts:

```text
finding_key
evaluation_key
rule_id
rule_version
severity
effects
```

The initial candidate finding should ordinarily be:

```text
severity = advisory or warning
effects = attention and/or review_required
```

It is not automatically:

```text
error
critical
block_current_use
quarantine
```

A duplicate candidate becomes blocking only when another accepted invariant is
already violated, such as:

- an explicit uniqueness conflict;
- an incomplete attempted consolidation;
- contradictory effective successor edges;
- or a current operation that requires identity certainty.

## 19.8 Re-evaluation

A candidate evaluation changes when any contract-significant input changes,
including:

- Actor current representation;
- Actor lifecycle;
- relevant Contact Point current representation or lifecycle;
- relevant Actor-to-Student Relationship representation or lifecycle;
- candidate-rule version;
- authorization coverage;
- or candidate policy version.

A suppression tied to the prior evaluation must not conceal the new evaluation.

## 19.9 No canonical negative identity assertion

Portia v1 does not create a permanent canonical assertion that:

```text
Actor A is not Actor B
```

Human knowledge and evidence may change.

A reviewed `related_but_distinct` outcome is preserved through bounded finding
administration, not an irrevocable identity edge.

## 19.10 Candidate invariants

1. Duplicate candidates are derived.
2. Candidate keys contain no sensitive values.
3. Similarity never proves identity.
4. Human review is required.
5. Finding acknowledgement records review, not resolution.
6. Finding suppression affects presentation only and expires when relevant
   evidence changes.
7. Confirmed duplicate identity requires consolidation.
8. Related-but-distinct does not create a canonical Actor relationship.
9. Insufficient information causes no identity mutation.
10. Existing Integrity Finding v1 remains immutable.

---

# 20. Approved Decision 16: Actor Duplicate Consolidation

## 20.1 Decision

Confirmed duplicate Actors use the accepted many-to-one new-successor topology:

```text
several Actor predecessors
-> one new reviewed Actor successor
```

Portia never designates one existing Actor as the survivor.

The successor's exact predecessor set is the canonical consolidation membership
list.

No separate canonical consolidation record is introduced.

## 20.2 Eligibility

Actors may be consolidated only when human review establishes all of the
following:

1. every predecessor resolves exactly;
2. every predecessor is an Actor under the same workspace;
3. every predecessor represents the same human person;
4. no predecessor is already superseded;
5. all material profile, contact, and relationship conflicts have explicit
   reviewed dispositions;
6. preserving separate Actor identities has no independent semantic value;
7. the complete predecessor set is known for this operation;
8. every predecessor may legally transition to `superseded`;
9. and the resulting successor is independently valid.

Matching names or contacts alone never satisfy eligibility.

## 20.3 Pure-consolidation rule

Actor consolidation must remain a pure consolidation.

It may:

- reconcile compatible display metadata;
- choose a reviewed current display name;
- preserve compatible organization and title information;
- create reviewed successor Contact Points;
- create reviewed successor Actor-to-Student Relationships;
- and preserve complete predecessor lineage.

It must not conceal:

- roster-student correction;
- conflated-person splitting;
- wrong-person correction;
- unsupported legal or institutional relationship claims;
- prohibited sensitive data;
- or another unrelated material correction.

Those conditions require their own explicit correction operations.

## 20.4 Successor Actor

The successor receives a new:

```text
actor_id
creation_source
created_at
created_by
updated_at
updated_by
```

The successor does not inherit or backdate identity or provenance from a
predecessor.

The successor's `supersedes` entries identify every exact Actor predecessor and
use:

```text
reason = duplicate_consolidated
```

The successor's current status is selected through review.

It is not chosen through:

```text
newest_wins
active_wins
highest_status_wins
most_complete_wins
```

Typical results are:

- active predecessors producing an active successor;
- inactive historical duplicates producing an inactive successor;
- or consolidation being blocked when current-use state cannot be resolved.

A successor must not begin as `proposed` while predecessors are made effectively
superseded.

Preparation may use a staged or proposed successor, but effective consolidation
requires a replacement-eligible successor.

## 20.5 Predecessor transitions

Every predecessor receives its own Actor-directory lifecycle transition:

```text
new_status = superseded
reason = duplicate_consolidated
```

All predecessor transitions use one mutually consistent `effective_at`.

The successor becomes an effective replacement only when:

- it is replacement-eligible;
- every exact predecessor transition is accepted;
- every transition and successor edge reconciles;
- and the Issue #13 operation is complete or recoverable.

Partial consolidation is an integrity failure.

No successful subset is accepted.

## 20.6 Actor profile reconciliation

The successor's profile is constructed through explicit review.

### Display name

A current display name may be selected or composed only when it truthfully
describes the same person and does not conceal uncertainty.

Name length, formatting, or apparent completeness does not determine the winner.

### Organization and title

Organization and title may be selected when:

- values are compatible;
- one is current and another is clearly historical;
- or the reviewer has sufficient basis.

Materially conflicting organization or title evidence must be resolved before
effective consolidation or omitted when omission remains honest.

### Actor category

The category must describe the successor's broad current role in Portia without
creating specific student relationship or authority claims.

Predecessor categories are not mechanically unioned.

## 20.7 Contact Point reconciliation

Contact Points do not move automatically to the successor Actor root.

Every current or materially relevant predecessor Contact Point receives one
explicit disposition:

```text
create_successor_contact
historical_only
inactive_obsolete
invalid_assertion
duplicate_contact_consolidation
requires_further_review
```

### Create successor contact

A new successor-owned Contact Point is created when review accepts the contact
assertion for current or historical use under the consolidated Actor.

The new Contact Point may supersede one exact predecessor Contact Point.

### Duplicate Contact Point consolidation

When several predecessor Contact Points represent the same exact contact
assertion for the same person, one new successor-owned Contact Point may
supersede all compatible predecessors.

This is a child-record many-to-one consolidation.

It requires exact value review and compatible source, verification, and use
meaning.

### Distinct compatible contacts

Different valid email addresses or phone numbers are not duplicates merely
because their Actors are duplicates.

Portia creates separate successor Contact Points for each accepted distinct
method.

### Conflicting contacts

A conflict must be classified explicitly, for example:

```text
both_valid_distinct_methods
one_obsolete
one_wrong_actor
one_invalid
insufficient_information
```

Unresolved material contact conflict blocks effective Actor consolidation when
the unresolved value would otherwise be silently discarded or treated as
current.

The successor Actor root never embeds the reconciled contact values.

## 20.8 Relationship reconciliation

Actor-to-Student Relationships do not move automatically.

Every current or materially relevant predecessor Relationship receives one
explicit disposition:

```text
create_successor_relationship
historical_only
relationship_ended
invalid_assertion
duplicate_relationship_consolidation
requires_further_review
```

### Exact duplicate relationship

Relationships may be consolidated only when they have:

- the same exact roster-qualified student target;
- materially equivalent relationship type;
- compatible basis and review state;
- and the same underlying teacher-local assertion.

The successor-owned Relationship may supersede all compatible predecessors.

### Different roster-qualified targets

Different `class_id + student_id` targets are never mechanically collapsed.

They may represent:

- different students;
- the same real student in different rosters;
- or unresolved cross-roster identity.

Core does not establish which case applies.

The successor Actor may retain several separate Relationships.

Portia does not infer cross-roster student equivalence.

### Different relationship types

Different relationship types may both remain valid.

For example, one Actor may be recorded as both:

```text
caregiver
family_contact
```

for the same roster-qualified student when the teacher-local assertions are
independently supported.

Types are not mechanically unioned into one Relationship.

## 20.9 Child lifecycle independence

Actor consolidation does not automatically transition every predecessor child
record.

A predecessor child remains exact historical evidence unless an explicit child
operation:

- supersedes it;
- inactivates it;
- invalidates it;
- or creates a reviewed successor.

Because the owning Actor becomes superseded, predecessor children are not
eligible for ordinary new current selection through that Actor.

Their independent status and history remain intact.

## 20.10 Later-discovered duplicate

A completed predecessor set is immutable.

A later-discovered duplicate is handled through a new successor:

```text
A + B -> C
C + D -> E
```

Portia does not retroactively add `D` to `C`'s predecessor set.

The prior consolidation remains historically exact.

## 20.11 Erroneous consolidation

Effective consolidation edges are not edited or deleted.

An erroneous Actor consolidation may require:

- lifecycle-history correction for predecessors that should not have become
  superseded;
- invalidation or supersession of the erroneous successor;
- new corrected Actor records;
- explicit child-record correction;
- explicit consuming-record correction;
- and Issue #13 recovery or repair operations.

Portia does not reactivate a superseded predecessor through an ordinary
lifecycle transition.

## 20.12 Operation semantics

A successful Actor consolidation operation must:

1. identify the complete predecessor Actor set;
2. obtain a fresh complete incoming-reference inventory;
3. lock the Actor collection scope required to prevent conflicting creation;
4. lock every predecessor Actor root in deterministic order;
5. lock all child records selected for coordinated replacement;
6. validate duplicate equivalence;
7. stage and validate the successor Actor and all selected successor children;
8. exclusively create the successor root and child records;
9. make every predecessor transition durable;
10. verify the effective replacement graph;
11. record all unresolved incoming-reference review obligations;
12. regenerate affected derived views;
13. and release locks only after external verification.

The operation kind remains:

```text
consolidate_duplicates
```

Operation facts and lock records must not copy contact values.

## 20.13 Consolidation invariants

1. Consolidation is many-to-one.
2. The successor is always new.
3. Every predecessor remains exactly resolvable.
4. Duplicate equivalence requires human review.
5. Consolidation is pure and cannot hide roster or split correction.
6. Every predecessor transition is required.
7. The complete predecessor set is immutable after effectiveness.
8. Child records move only through explicit reviewed child operations.
9. Contact and relationship conflicts require explicit disposition.
10. Incoming references are never silently retargeted.

---

# 21. Approved Decision 17: Confirmed Actor–Roster Student Collision

## 21.1 Decision

A confirmed Actor–roster student collision means:

> One Actor record was incorrectly used to represent a person who, for the
> relevant Portia student relationship, must be represented by one exact Core
> roster-qualified student reference.

This is cross-family identity correction.

It is not:

- Actor duplicate consolidation;
- Actor-to-Actor supersession;
- migration;
- or proof of workspace-wide student identity.

The Actor is invalidated rather than superseded because a Core roster student is
not an Actor successor in the Actor replacement graph.

## 21.2 Candidate versus confirmed collision

A possible collision may be generated from:

- matching display names;
- matching contact values;
- imported identifiers;
- or local operator review.

Those signals create an Actor-targeted review finding only.

A collision becomes confirmed only through authorized human review of the exact:

```text
Actor
+ roster-qualified student
+ relevant evidence
```

Portia must distinguish:

```text
possible_same_person
confirmed_same_person
matching_name_only
matching_contact_only
related_but_distinct
insufficient_information
```

Only `confirmed_same_person` permits the correction operation.

## 21.3 Collision-resolution record

Issue #14 will introduce an immutable canonical record:

```text
actor_roster_student_collision@1
```

It is stored beneath the affected Actor root:

```text
portia/actors/<actor_id>/
  records/
    actor_roster_student_collision/
      <collision_id>.json
```

The identifier will use:

```text
arsc_<opaque-id>
```

The record will preserve at least:

```text
actor exact reference
exact roster_student_ref
resolution = confirmed_same_person
bounded evidence kinds
reviewed_at
reviewed_by
operation_ref
Actor invalidation transition reference
created_at
created_by
```

The record does not contain:

- a student name copied from the roster;
- Actor contact values;
- a new workspace student identity;
- or a claim that another roster entry represents the same person.

## 21.4 Roster authority boundary

The exact roster identity remains:

```text
class_id + student_id
```

The collision record applies only to that exact Core roster-qualified reference.

When the same human may appear in another roster:

- Portia does not infer equivalence;
- equal student IDs do not prove equivalence;
- equal names do not prove equivalence;
- and the collision record does not become a workspace person registry.

A separately reviewed exact roster collision may be recorded when another class
context requires it.

## 21.5 Actor lifecycle result

The Actor transitions to:

```text
invalidated
```

with:

```text
reason = roster_student_collision
```

The Actor does not transition to `superseded`.

No Actor successor is created merely to bridge the identity families.

The collision record and lifecycle transition must reconcile.

The Actor remains exactly resolvable for historical records.

## 21.6 Contact Points

Contact Points beneath the invalidated Actor do not become roster-student contact
records.

Portia must not:

- copy them into Core;
- reinterpret them as student contact data;
- use them for new Actor communication;
- or expose them through ordinary student views.

Each Contact Point remains historical evidence and receives review where
required.

A Contact Point may be invalidated when it was recorded only because the false
Actor identity existed or when privacy policy prohibits retention.

Exceptional removal may apply to prohibited payload under a later decision.

## 21.7 Actor-to-Student Relationships

A Relationship whose Actor and target student are confirmed to represent the
same person is a self-relationship defect.

It must be reviewed and ordinarily invalidated with:

```text
wrong_actor_corrected
```

Other Relationships beneath the Actor do not automatically transfer to the
roster student.

For example, a false student Actor recorded as a counselor for another student
requires explicit domain correction and cannot be inferred valid merely because
the represented person is a student.

## 21.8 Incoming consuming records

Historical records continue to resolve the exact Actor reference.

A current consuming record that should identify the roster student requires
explicit domain-specific material correction.

Examples include:

- replacing an Event Participant Actor subject with a roster-student subject;
- creating a corrected Account source;
- creating a corrected Communication party;
- or creating a corrected Support participant.

Changing Actor identity to roster-student identity is never a nonmaterial
amendment.

When the consuming record belongs to a different class than the confirmed roster
reference, Portia must not reuse that student reference automatically.

The result may remain:

```text
review_required
authorization_limited
or indeterminate
```

until an authoritative exact roster target is available.

## 21.9 Operation semantics

The collision-correction operation must:

1. lock the exact Actor and relevant child records;
2. obtain a complete incoming-reference inventory;
3. validate the exact Core roster reference;
4. preserve human review evidence;
5. create the collision-resolution record;
6. create the Actor invalidation transition;
7. replace the current Actor status;
8. create any explicitly reviewed corrected consuming records;
9. review or quarantine affected children;
10. regenerate derived views;
11. and verify that the Actor is no longer eligible for new Actor selection.

The operation kind is:

```text
correct_history
```

or a later new operation kind only if the pre-ADR audit shows that the existing
vocabulary cannot express the operation honestly.

The preferred direction is to retain the existing operation vocabulary and
classify the domain correction through the typed primary target and write set.

## 21.10 Collision invariants

1. A possible match is not a confirmed collision.
2. Confirmation is human-reviewed.
3. The exact Core identity is class-qualified.
4. The Actor is invalidated, not superseded.
5. No cross-family replacement edge is created.
6. Existing Actor references remain exact.
7. Current consuming records require explicit material correction.
8. Contact Points are not converted into roster data.
9. Self-Relationships are explicitly reviewed.
10. The correction makes no workspace-wide student identity claim.

---

# 22. Approved Decision 18: Conflated-Person Actor Split

## 22.1 Decision

Actor is explicitly eligible for one-to-many split replacement when one Actor
record incorrectly conflates several distinct human people.

The topology is:

```text
one Actor predecessor
-> several new Actor successors
```

This extends the accepted split-replacement architecture to the Actor semantic
family.

No many-to-many Actor replacement is permitted.

## 22.2 Eligibility

An Actor split is permitted only when review establishes:

1. the predecessor resolves exactly;
2. the predecessor materially conflates several distinct people;
3. every successor represents one distinct human person;
4. the complete direct successor set is known for the operation;
5. each successor is independently valid;
6. no successor is a roster-student identity disguised as an Actor;
7. child and incoming-reference uncertainty is explicitly inventoried;
8. the predecessor may legally transition to `superseded`;
9. and one coordinated operation can establish the complete split.

When the complete successor set is not known, Portia must not guess a split.

The predecessor may instead be:

```text
invalidated
quarantined
or left review_required
```

until sufficient evidence exists.

## 22.3 Successor lineage

Every successor Actor lists the same exact predecessor with:

```text
reason = conflated_person_split
```

Every successor must be replacement-eligible by the common split effective time.

The predecessor receives one transition:

```text
new_status = superseded
reason = conflated_person_split
```

The operation journal identifies the complete successor set.

A later successor cannot be added to the completed direct split.

If another person is discovered later, a new correction must operate from the
appropriate current replacement frontier without rewriting the old split.

## 22.4 No separate split record

Version 1 does not introduce a canonical Actor split record.

The complete split is represented through:

```text
successor-owned predecessor edges
+ predecessor lifecycle transition
+ complete Issue #13 operation journal
```

This matches the accepted replacement architecture and avoids duplicate topology
authority.

## 22.5 Profile construction

Each successor Actor receives independently reviewed:

- display;
- category;
- organization;
- title;
- lifecycle state;
- creation provenance;
- and timestamps.

Profile data is not copied mechanically to every successor.

A predecessor field may be copied only when evidence supports that it applies to
the specific successor.

Uncertain information is omitted or remains attached to the predecessor
historically.

## 22.6 Contact Point assignment

Predecessor Contact Points are not automatically assigned.

Every materially relevant Contact Point receives one explicit split disposition:

```text
assigned_to_one_successor
supported_for_several_successors
historical_unassigned
invalid_assertion
requires_further_review
```

### Assigned to one successor

A new successor-owned Contact Point is created and may supersede the predecessor
Contact Point when evidence establishes the correct person.

### Supported for several successors

A shared household or office contact may legitimately apply to several
successors.

Portia creates one new Contact Point under each supported successor.

One predecessor Contact Point is not physically shared across Actor roots.

The operation must preserve why multi-assignment was accepted.

### Historical unassigned

When available evidence cannot identify the correct person, the Contact Point
remains attached to the predecessor historically.

It is not available for ordinary current use through a successor.

### Invalid assertion

When the Contact Point should not have been recorded or belongs to none of the
successors, it is explicitly invalidated or handled under exceptional-removal
policy.

## 22.7 Relationship assignment

Predecessor Actor-to-Student Relationships are not automatically assigned.

Each Relationship receives one disposition:

```text
assigned_to_one_successor
supported_for_several_successors
historical_unassigned
invalid_assertion
requires_further_review
```

A new successor-owned Relationship is created for every accepted assignment.

A relationship may be supported for several successors only when the
teacher-local assertion independently applies to each person.

Portia must not infer assignment from:

- name similarity;
- contact ownership;
- organization;
- or arbitrary ordering.

## 22.8 Incoming-reference assignment

Existing incoming Actor references remain exact references to the conflated
predecessor.

Portia does not guess which successor an existing reference intended.

Every active incoming reference requiring current identity receives one of:

```text
correct_to_one_successor
replace_with_several_domain_records
historical_only
cannot_resolve
not_material_to_current_use
```

### Correct to one successor

The consuming record receives an explicit domain-specific material correction.

### Replace with several domain records

This is permitted only when the consuming record family supports plural
replacement honestly.

For example, one conflated Event Participant may require several corrected
Participants under the containing Event.

The consuming record's own replacement topology governs the correction.

### Historical only

The exact predecessor reference remains historically readable and no current
retarget is required.

### Cannot resolve

The record remains review-required or Quarantined according to use impact.

Portia does not choose a successor automatically.

## 22.9 Split operation

A successful split operation must:

1. identify and lock the predecessor Actor;
2. obtain a complete incoming-reference and child-record inventory;
3. validate the complete successor set;
4. stage all successor Actors and explicitly assigned child records;
5. exclusively create every successor root;
6. make the predecessor transition durable;
7. verify every successor edge and common effective time;
8. preserve unresolved assignment obligations;
9. perform only explicitly accepted consuming-record corrections;
10. regenerate affected derived views;
11. and verify that no hidden automatic assignment occurred.

The operation kind is:

```text
correct_history
```

or another existing semantically accurate correction kind selected during the
operational-integration decision.

It is not `consolidate_duplicates`.

## 22.10 Split invariants

1. Actor split is one-to-many.
2. The predecessor conflates distinct people.
3. Every successor is new.
4. The complete successor set is fixed at effectiveness.
5. Many-to-many replacement is prohibited.
6. Profiles are reviewed independently.
7. Contact Points are assigned explicitly.
8. Relationships are assigned explicitly.
9. Incoming references are never guessed.
10. Unresolved evidence remains explicit and may block current use.

---

# 23. Approved Decision 19: Incoming References and Current-Use Reconciliation

## 23.1 Exact historical references remain stable

Actor correction never rewrites historical references automatically.

This applies to references from:

```text
Events
Event Participants
Accounts
Communications
Supports and Interventions
Follow-Ups
Determinations
Responses
Outcomes
future Portia records
```

The exact reference continues to identify the exact original Actor.

Historical display snapshots remain unchanged.

## 23.2 Reference-resolution result

Actor reference resolution should distinguish at least:

```text
current
inactive
invalidated
superseded
missing
malformed
quarantined
authorization_limited
indeterminate
```

Resolution returns the exact referenced Actor and its current diagnostic state.

It does not return a successor as though it were the referenced Actor.

## 23.3 Current-use disposition

Current-use evaluation is separate from exact resolution.

Representative dispositions are:

```text
eligible
historical_only
review_required
blocked
indeterminate
```

Examples:

- active, valid, unquarantined Actor: ordinarily `eligible`;
- inactive Actor: ordinarily `historical_only` or `review_required`;
- superseded Actor: `historical_only` for new selection and often
  `review_required` for active consuming records;
- invalidated Actor: ordinarily `blocked` for new use;
- missing or malformed Actor: `indeterminate` or `blocked`;
- authorization-limited resolution: `indeterminate`.

Record-family policy determines the exact result.

## 23.4 Incoming-reference discovery

Graph-sensitive Actor operations require complete incoming-reference discovery.

The accepted generic projection kind:

```text
incoming_reference_index
```

may be used at workspace scope.

Issue #14 does not require a new Actor-specific projection kind merely to index
Actor references.

The index may contain entries keyed by exact Actor or Actor-directory child
identity.

It remains:

- nonauthoritative;
- source-snapshot-bound;
- authorization-aware;
- immutable by generation;
- explicitly selected;
- disposable;
- and rebuildable.

A missing index does not prove no incoming references.

## 23.5 Complete versus limited discovery

Before consolidation, collision correction, split, exceptional removal, or
another graph-sensitive operation, Portia must obtain either:

1. a fresh complete verified incoming-reference generation; or
2. a complete bounded canonical scan under the current authorization scope.

When discovery is:

```text
authorization_limited
stale
corrupt
missing
or otherwise indeterminate
```

Portia must not make a complete-graph claim.

The graph-sensitive operation is blocked unless its accepted semantics explicitly
permit limited scope.

Actor consolidation, collision correction, and split require complete discovery
for the selected workspace.

## 23.6 Reference classes

Every incoming reference is classified for correction planning.

### Immutable historical reference

Examples include:

- closed historical Event Participant;
- historical Account source;
- completed Communication party;
- accepted Determination attribution.

The reference remains unchanged.

Authorized views may show:

- recorded display snapshot;
- exact Actor state;
- direct effective successors;
- replacement frontier;
- or collision warning.

### Mutable current canonical assertion

When current domain meaning depends on Actor identity, the record may require
explicit material correction.

Changing an Actor reference to:

- another Actor;
- an Actor consolidation successor;
- an Actor split successor;
- or a roster student

is not a nonmaterial amendment unless that future consuming contract explicitly
defines a safe specialized correction model.

The default is successor replacement or another domain-specific material
correction.

### Current record where identity is not material to continued use

Some active records may remain valid while retaining the historical predecessor
reference.

The record-family validator must state why.

Portia does not assume that every active reference must be retargeted.

### Derived reference

Search results, reverse indexes, summaries, current Actor lists, preferred
contact views, and review queues are rebuilt.

Derived records are never manually retargeted.

### Operational reference

Operation journals, locks, Quarantine, findings, acknowledgements, and
suppressions continue to identify the exact target they originally governed.

They are not rewritten to a successor.

## 23.7 New selection after correction

After effective Actor consolidation or split:

- the superseded predecessor is excluded from ordinary new Actor selection;
- the reviewed successor or successors may be selected according to policy;
- the user interface may show predecessor lineage;
- and exact predecessor lookup remains available for authorized history.

After confirmed roster collision:

- the invalidated Actor is excluded from new Actor selection;
- the exact roster student may be selected only in the class context where the
  Core identity is authoritative;
- and Portia does not offer the roster student as a workspace Actor replacement.

## 23.8 Contact resolution after Actor correction

A new Communication must not resolve a current contact method through:

- a superseded Actor's child records;
- an invalidated collision Actor;
- an unassigned split predecessor;
- or a stale derived preferred-contact view.

Current contact selection requires:

```text
current eligible Actor
+ active eligible Contact Point under that Actor
+ purpose and authorization eligibility
+ absence of blocking Quarantine
```

Historical Communications retain the exact Contact Point or recorded party
evidence they originally used.

## 23.9 Relationship resolution after Actor correction

A new workflow must not infer a current Actor-to-Student Relationship from:

- a superseded Actor;
- an invalidated Actor;
- a predecessor child record not explicitly reconciled;
- or a historical relationship snapshot.

Current use requires an active eligible Relationship under the current Actor.

Historical records preserve the exact predecessor relationship evidence where
recorded.

## 23.10 Review obligations

A correction operation may create durable review obligations for incoming
records that cannot be corrected safely in the same operation.

Those obligations must be represented through:

- Actor-targeted or consuming-record-targeted Integrity Findings;
- Quarantine where current use must be blocked;
- or later domain-specific review records.

The operation journal alone is not the long-term user-facing review queue.

A review obligation must contain typed identity, not sensitive payload.

## 23.11 No automatic cascade

Portia never automatically:

- rewrites Actor references;
- rewrites display snapshots;
- changes child ownership;
- duplicates Contact Points;
- duplicates Relationships;
- converts Actor identity to roster identity;
- chooses one split successor;
- or copies attached records.

Every canonical change requires explicit domain semantics and accepted
persistence evidence.

## 23.12 Incoming-reference invariants

1. Exact references remain exact.
2. Resolution and current-use eligibility are separate.
3. Successors are not silently substituted.
4. Graph-sensitive operations require complete discovery.
5. Authorization-limited discovery cannot support complete-graph claims.
6. Historical records remain unchanged.
7. Current material references require explicit domain correction.
8. Derived references are rebuilt.
9. Contact and Relationship resolution uses the current owning Actor.
10. Unresolved incoming references remain explicit review obligations.

---

# 24. Approved Decision 20: Actor-Directory Representation Migration

## 24.1 Decision

Representation-only migration for Actor-directory records uses a dedicated
immutable contract:

```text
actor_directory_record_migration@1
```

The contract applies to:

```text
Actor
Actor Contact Point
Actor-to-Student Relationship
Actor–Roster Student Collision
```

It does not apply to:

- lifecycle transitions;
- lifecycle-history corrections;
- amendments;
- operation journals;
- locks;
- Quarantine records;
- Integrity Findings;
- or derived generations.

Those independently versioned records remain readable under their accepted
historical contracts.

## 24.2 Identity

Migration identifiers reuse the accepted scope-neutral:

```text
mig_<opaque-id>
```

contract.

No Actor-specific migration prefix is required.

One migration record represents:

> One exact Actor-directory record transformed from one exact public contract
> version to one exact destination contract version through one identified
> representation-only procedure while preserving semantic identity.

## 24.3 Canonical storage

A migration is stored beneath the destination Actor root:

```text
portia/actors/<actor_id>/
  records/
    actor_directory_record_migration/
      <migration_id>.json
```

The destination Actor owner embedded in the migration target must agree with the
containing Actor root.

Actor-directory migration never moves a record to another Actor root.

Changing Actor ownership is material correction and requires a successor.

## 24.4 Required conceptual envelope

The migration contract will preserve:

```text
schema_version
record_type
module_id
actor_id
migration_id
source
destination
reason
procedure
source_fingerprint
destination_fingerprint
effective_at
created_at
created_by
operation_ref
```

Constants are:

```text
schema_version = "1"
record_type = "actor_directory_record_migration"
module_id = "portia"
```

`source` and `destination` are exact Actor-directory representation references.

## 24.5 Identity-preserving rules

A migration must preserve:

- Actor ownership;
- record family;
- opaque domain identifier;
- represented person or assertion;
- current lifecycle meaning;
- successor lineage;
- creation provenance;
- and all contract-significant domain semantics.

Permitted examples include:

```text
actor@1 -> actor@2 with the same actor_id
actor_contact_point@1 -> actor_contact_point@2
actor_student_relationship@1 -> actor_student_relationship@2
actor_roster_student_collision@1 -> actor_roster_student_collision@2
```

Prohibited migration includes:

- changing Actor identity;
- changing Contact Point value or owner;
- changing Relationship Actor, student, type, or material basis;
- converting an Actor into a roster-student reference;
- consolidating duplicates;
- splitting a conflated Actor;
- changing lifecycle status;
- or removing prohibited payload.

Those are explicit correction, lifecycle, consolidation, split, collision, or
exceptional-removal operations.

## 24.6 Same logical identity

Source and destination use the same opaque domain identity.

Migration does not allocate a new:

```text
actor_id
contact_point_id
relationship_id
collision_id
```

A public contract that cannot preserve the same logical identity is not a
representation-only migration.

## 24.7 Procedure identity

`procedure` identifies one versioned deterministic migration procedure.

It includes:

```text
procedure_id
procedure_version
```

The procedure ID is nonsecret and must not encode contact values, names, or
student information.

Application validation must establish that the procedure is approved for the
exact source and destination contracts.

## 24.8 Current-file replacement

Actor, Contact Point, and Relationship records are mutable current
representations with append-only supporting history.

A migration operation:

1. reads and validates the exact source representation;
2. verifies lifecycle and amendment consistency;
3. transforms the logical value through the approved procedure;
4. stages and validates the destination bytes;
5. creates and verifies the migration record;
6. revalidates the exact source fingerprint;
7. atomically replaces the current representation at its canonical path;
8. verifies the destination fingerprint;
9. and rebuilds affected derived views.

The migration record becomes durable before replacement of the current file.

Interruption therefore leaves recoverable migration evidence rather than an
unexplained contract-version change.

## 24.9 Historical version resolution

The migration record preserves exact source and destination contract versions and
fingerprints.

Historical references that contain an older expected contract version do not
silently resolve as though the current bytes still implement that version.

Resolution may return:

```text
migrated_representation
```

together with the exact migration chain.

It must not:

- pretend that old bytes remain current;
- rewrite historical references;
- or classify migration as identity correction.

## 24.10 Migration predecessor chain

Several sequential representation migrations are ordered through exact
source/destination version continuity and migration chronology.

A destination representation may serve as the source of a later migration.

The chain must contain no:

- branch;
- cycle;
- skipped incompatible version;
- contradictory source fingerprint;
- or competing current destination.

## 24.11 Collision record migration

An Actor–Roster Student Collision record is immutable domain evidence.

A later schema migration may create a new representation with the same
`collision_id` only when semantic meaning is unchanged.

The migration does not alter:

- the exact Actor;
- the exact roster-qualified student;
- reviewed resolution;
- or linked invalidation evidence.

## 24.12 Migration invariants

1. Migration is representation-only.
2. Record identity and Actor ownership are preserved.
3. Record family is preserved.
4. Migration cannot conceal correction or removal.
5. Migration evidence is accepted before current-file replacement.
6. Source and destination fingerprints are exact.
7. Historical references are not rewritten.
8. Migration chains contain no branch or cycle.
9. Contact payload is not copied into operation facts.
10. Existing class/work `record_migration@1` remains immutable.

---

# 25. Approved Decision 21: Actor-Directory Exceptional Removal

## 25.1 Decision

Ordinary deletion of Actor-directory canonical records is prohibited.

Narrow exceptional removal uses a separate immutable certificate:

```text
actor_directory_exceptional_removal@1
```

The certificate preserves the minimum permitted evidence that an exact
Actor-directory payload was removed under explicit authority.

Exceptional removal is not:

- ordinary lifecycle;
- invalidation;
- supersession;
- duplicate consolidation;
- migration;
- privacy projection;
- or a substitute for retention policy.

## 25.2 Eligible targets

The initial target union permits:

```text
Actor
Actor Contact Point
Actor-to-Student Relationship
Actor–Roster Student Collision
```

Removal of an append-only lifecycle transition, correction, amendment, or
operation journal is not permitted through this contract.

Errors in those records use history correction, repair, or Quarantine.

## 25.3 Narrow grounds

Initial grounds are:

```text
prohibited_sensitive_payload
synthetic_or_test_record
unrecoverable_corruption
binding_legal_or_administrative_requirement
other_exceptional_ground
```

`other_exceptional_ground` requires bounded detail and explicit authorization.

Convenience, inactivity, lack of current references, duplicate status, or user
preference alone are not exceptional-removal grounds.

## 25.4 Workspace-level certificate storage

Certificates are stored outside the removable Actor root:

```text
portia/
  actor-directory-removals/
    <removal_id>.json
```

This permits the certificate to survive removal of:

- `actor.json`;
- an Actor child payload;
- or, in the narrowest case, the remaining Actor root.

The directory is a canonical Portia workspace collection.

It is not derived state.

## 25.5 Identifier reuse

Issue #14 will reuse the existing exceptional-removal identifier contract when
its accepted syntax is scope-neutral.

If the existing identifier contract is tied structurally to class/work removal,
Issue #14 will add an Actor-directory removal identifier with the same opaque,
nonsemantic principles.

The pre-ADR contract audit must record the final choice.

No identifier may encode:

- Actor name;
- contact value;
- student identity;
- removal ground;
- or sensitive payload.

## 25.6 Required certificate evidence

The conceptual envelope preserves:

```text
schema_version
record_type
module_id
removal_id
target
original_workspace_relative_path
original_contract_version
original_fingerprint
original_byte_length
ground
authorization
removed_at
removed_by
operation_ref
retained_identity_evidence
```

The certificate does not retain the removed substantive payload.

## 25.7 Retained identity evidence

Retained identity evidence is limited to exact opaque identity required for:

- historical reference resolution;
- authorization audit;
- operation recovery;
- and proof that a specific canonical payload was removed.

For an Actor, it may retain only:

```text
actor_id
original contract version
content fingerprint
byte length
```

For a Contact Point, it may retain:

```text
actor_id
contact_point_id
original contract version
content fingerprint
byte length
```

It does not retain:

- display name;
- email address;
- phone number;
- organization;
- title;
- relationship type;
- student name;
- or unrestricted narrative.

An exact roster-qualified student reference may be retained only when necessary
to identify a removed Relationship or Collision certificate and permitted by the
authorizing policy.

## 25.8 Actor-root removal

Removing `actor.json` is permitted only under exceptional authority.

Before Actor-root removal, Portia must:

1. obtain complete incoming-reference discovery;
2. inventory all canonical child records and history;
3. determine which child payloads must also be removed;
4. preserve every required removal certificate;
5. preserve operation and authorization evidence;
6. ensure no ordinary workflow can select the Actor;
7. and verify post-removal historical-resolution behavior.

The resulting exact Actor resolution is:

```text
exceptionally_removed
```

It is not:

```text
missing
superseded
invalidated
```

unless separate surviving canonical evidence also establishes one of those
states.

Portia must not create a replacement Actor merely to avoid removal semantics.

## 25.9 Contact payload removal

Contact Point is the most likely exceptional-removal target because it contains
privacy-sensitive payload.

Removal may be appropriate when:

- the value was prohibited from retention;
- the value belongs to the wrong person and must not remain;
- a binding requirement prohibits retaining it;
- or synthetic/test data must be destroyed.

The certificate retains no contact value or reversible unsalted contact hash.

Historical Communications may retain their own independently justified evidence
under their future contract and policy. The Contact Point removal certificate
does not rewrite them.

## 25.10 Relationship and collision removal

Relationship or Collision removal requires heightened review because those
records preserve identity and correction context.

Removal is not appropriate merely because:

- the Relationship ended;
- the Actor was invalidated;
- the roster changed;
- or the collision became historical.

When removal is required, the certificate retains exact opaque identity and the
minimum permitted target evidence.

## 25.11 Graph-sensitive preflight

Exceptional removal requires:

- fresh complete incoming-reference discovery;
- exact target and path validation;
- authorization validation;
- removal-ground validation;
- child and dependent review;
- expected fingerprint agreement;
- and a complete write/remove plan.

Authorization-limited discovery blocks removal.

No absence claim may be inferred from a missing or stale index.

## 25.12 Operation ordering

The operation:

1. validates and stages the certificate;
2. creates and verifies the certificate;
3. revalidates the exact target fingerprint;
4. removes the target payload through the approved filesystem procedure;
5. verifies absence and containment;
6. creates required findings or Quarantines for affected references;
7. regenerates derived views;
8. and verifies exact historical resolution through the certificate.

Certificate acceptance precedes payload removal.

An accepted certificate with a remaining payload or a removed payload without an
accepted certificate is recovery-required state.

## 25.13 No contact value in diagnostics

Findings, journals, locks, Quarantine records, and removal certificates refer to
the exact Contact Point identity and fingerprint.

They do not copy the removed value.

Authorized repair tools may inspect staged or surviving canonical payload only
when policy permits.

## 25.14 Exceptional-removal invariants

1. Ordinary deletion is prohibited.
2. Grounds are narrow and explicit.
3. The certificate survives outside the Actor root.
4. Certificate acceptance precedes payload removal.
5. Removed payload is not copied into the certificate.
6. Complete incoming-reference discovery is required.
7. Removal does not masquerade as lifecycle.
8. Exact resolution returns `exceptionally_removed`.
9. Historical references are not silently rewritten.
10. Existing class/work `exceptional_removal@1` remains immutable.

---

# 26. Approved Decision 22: Actor-Aware Integrity Findings

## 26.1 Decision

Issue #14 will introduce:

```text
integrity_finding@2
```

Version 2 preserves the complete version-1 envelope, severity vocabulary, effect
vocabulary, deterministic key semantics, and noncanonical derived status.

It adds Actor-directory target branches.

Version 1 remains immutable and valid for all existing targets.

## 26.2 Added target branches

Integrity Finding v2 adds:

```text
actor_directory_record
actor_set
actor_directory_collection
```

### Actor-directory record

This branch targets one exact:

```text
Actor
Actor Contact Point
Actor-to-Student Relationship
Actor–Roster Student Collision
```

It composes the appropriate exact reference.

### Actor set

This branch targets a bounded sorted unique set of exact Actors.

It is intended for:

- duplicate candidates;
- conflicting effective successor sets;
- and multi-Actor consolidation diagnostics.

The set contains at least two Actors.

It contains no display or contact data.

### Actor-directory collection

This branch targets the workspace Actor collection when one finding cannot be
honestly assigned to a single known Actor, such as:

- malformed Actor-root discovery;
- duplicate directory identity;
- collection-level path conflict;
- or authorization-limited collection scan.

It does not replace exact targets when exact identity is known.

## 26.3 Existing target compatibility

Every value valid under `integrity_finding@1` remains valid under version 2 when
its `schema_version` and `$id` expectations are updated according to the accepted
versioning policy.

Version 2 must not reinterpret:

- work targets;
- operation targets;
- class targets;
- workspace targets;
- graph targets;
- or derived-projection targets.

## 26.4 Actor rule families

Initial Actor rule families include:

```text
portia.actor.path_identity_mismatch
portia.actor.lifecycle_disagreement
portia.actor.replacement_broken
portia.actor.duplicate_candidate
portia.actor.roster_collision_candidate
portia.actor.roster_collision_incomplete
portia.actor.split_incomplete
portia.actor.contact_owner_mismatch
portia.actor.contact_preference_conflict
portia.actor.relationship_owner_mismatch
portia.actor.relationship_target_unavailable
portia.actor.relationship_authority_overclaim
portia.actor.incoming_reference_indeterminate
portia.actor.privacy_payload_leak
portia.actor.removal_incomplete
portia.actor.migration_inconsistent
portia.actor.operation_incomplete
```

Rule IDs remain versioned separately from the finding contract.

## 26.5 Severity and effects

Representative duplicate candidates are ordinarily:

```text
advisory or warning
attention and/or review_required
```

Representative corrupt or incomplete Actor operations may be:

```text
error or critical
block_current_use
block_lifecycle_writes
quarantine
review_required
```

Severity and effects are selected from actual consequence, not record family.

A name or contact similarity signal alone is never critical.

## 26.6 Privacy-minimized evidence

Finding keys, evaluation keys, titles, and context must not contain:

- display names;
- contact values;
- phone digits;
- email domains;
- student names;
- relationship narratives;
- or removed payload.

Findings may preserve:

- exact opaque references;
- rule and contract versions;
- paths;
- fingerprints;
- counts;
- bounded evidence-kind tokens;
- and authorization-coverage status.

An authorized review interface may resolve canonical values separately.

## 26.7 Finding administration compatibility

The existing contracts remain reusable unchanged:

```text
finding_acknowledgement@1
finding_suppression@1
finding_suppression_current_pointer@1
```

They bind stable:

```text
finding_key
evaluation_key
rule_id
rule_version
severity
effects
```

and do not embed the Integrity Finding target wire shape.

Acknowledgement and suppression therefore work for version-2 Actor findings
without new versions.

Application validation must still confirm that the bound finding evaluation
exists and that suppression eligibility remains permitted.

## 26.8 Quarantine distinction

An Integrity Finding may recommend or require Quarantine.

It is not itself Quarantine.

A duplicate candidate ordinarily does not quarantine an Actor.

A broken consolidation, contradictory identity graph, privacy leak, or incomplete
removal may require Quarantine according to actual risk.

## 26.9 Finding invariants

1. Integrity Finding v2 is additive.
2. Version-1 findings remain valid.
3. Actor sets contain opaque exact identities only.
4. Collection targets are used only when exact identity is unavailable or
   genuinely plural at collection scope.
5. Findings are derived and rebuildable.
6. Findings do not mutate Actor lifecycle.
7. Acknowledgement and suppression v1 remain reusable.
8. Sensitive payload is excluded from keys and presentation context.
9. Duplicate candidates do not establish identity.
10. Quarantine remains a separate operational control.

---

# 27. Approved Decision 23: Actor-Aware Operation Journals

## 27.1 Decision

Issue #14 will introduce:

```text
operation_journal@2
```

Version 2 preserves:

- immutable journal revisions;
- explicit current pointer selection;
- operation identity;
- intent digest;
- replay semantics;
- preconditions;
- planned writes;
- observed evidence;
- step state;
- outcomes;
- compensation;
- and recovery behavior

from version 1.

It adds Actor-directory operation targets.

## 27.2 Current pointer and references

These contracts remain unchanged:

```text
operation_current_pointer@1
operation_ref@1
operation_journal_ref@1
```

The current pointer selects:

```text
operation_id + journal_revision
```

and does not embed the journal target shape.

`operation_journal_ref@1` already carries `contract_version`, so it may refer to a
version-2 journal revision.

## 27.3 Operation scope

Actor-directory operations use:

```text
scope = workspace
```

because Actor ownership is workspace-scoped.

Issue #14 does not add a new operation-scope token merely to restate that
ownership.

Exact Actor identity is carried by the version-2 primary and affected target
unions.

## 27.4 Added operation target branches

Operation Journal v2 adds:

```text
actor_directory_record
actor_set
actor_directory_collection
```

The semantics match Integrity Finding v2.

Actor-set targets are used for:

- duplicate consolidation;
- Actor split planning;
- and other operations whose complete identity set is contract-significant.

The planned write set still identifies every exact path and expected
representation independently.

## 27.5 Existing operation kinds

The accepted operation-kind vocabulary is sufficient.

Actor workflows use:

| Actor workflow | Operation kind |
| --- | --- |
| Create Actor, Contact Point, Relationship, or Collision | `create_record` |
| Nonmaterial Actor-directory correction | `apply_amendment` |
| Lifecycle status change | `transition_lifecycle` |
| Lifecycle-history repair | `correct_history` |
| Ordinary material successor correction | `correct_history` |
| Duplicate consolidation | `consolidate_duplicates` |
| Conflated-person split | `correct_history` |
| Actor–roster collision correction | `correct_history` |
| Representation-only migration | `migrate_representation` |
| Exceptional removal | `exceptionally_remove` |
| Derived rebuild | `rebuild_projection` |
| Integrity scan | `integrity_scan` |
| Interrupted-operation repair | `repair_operation` |

No new operation kind is introduced merely because the target is an Actor.

## 27.6 Typed primary target

An operation changing one Actor-directory record must use that exact record as
its primary target.

A generic workspace target is insufficient.

A consolidation uses the complete Actor set.

A split uses:

- the exact predecessor Actor as primary target;
- and the complete successor set in intent and planned writes.

A creation may identify the intended new exact Actor-directory identity together
with a `must_be_absent` precondition.

## 27.7 Write-set privacy

Planned and observed write evidence may preserve:

```text
workspace-relative path
must_be_absent or must_match precondition
content fingerprint
byte length
contract name and version
typed record identity
step state
readback result
```

It must not copy:

- contact values;
- display names;
- organization or title;
- relationship detail;
- student names;
- or removed payload

into operation facts merely for convenience.

The canonical staged and destination payload necessarily contains the domain
record and is protected by deployment filesystem policy.

## 27.8 Actor operation families

Version-2 operation validation must recognize complete write families.

### Actor creation

Expected writes may include:

```text
actor.json
initial Contact Points
initial Relationships
journal revisions
current pointer
```

Initial child creation remains explicit.

### Lifecycle transition

Expected writes include:

```text
Actor-directory transition
current target replacement
derived regeneration or finding update
journal evidence
```

### Amendment

Expected writes include:

```text
Actor-directory amendment
current target replacement
derived regeneration
journal evidence
```

### Consolidation or split

Expected writes include:

```text
successor Actor roots
selected successor children
predecessor lifecycle transitions
current predecessor replacements
incoming-reference review findings
derived regeneration
journal evidence
```

### Collision correction

Expected writes include:

```text
collision record
Actor invalidation transition
current Actor replacement
selected consuming-record corrections
child review findings or Quarantines
derived regeneration
journal evidence
```

### Exceptional removal

Expected writes include:

```text
removal certificate
target removal
reference findings or Quarantines
derived regeneration
journal evidence
```

## 27.9 Replay and recovery

Actor operations retain exact Issue #13 replay rules.

The same `operation_id` may be replayed only with the same immutable
`intent_digest`.

Recovery evaluates actual evidence, not timestamps or greatest revisions.

A partially created Actor root is never accepted merely because `actor.json`
exists.

A partially completed consolidation or split is never reduced to a successful
subset.

## 27.10 Operation outcomes

The existing outcomes remain sufficient:

```text
completed
replayed
rejected
conflict
partial_success
recovery_required
compensated
failed
```

Actor-domain meaning does not require a new outcome vocabulary.

## 27.11 Operation Journal v1 compatibility

Version-1 journals remain valid and readable.

They are not retroactively upgraded.

An operation involving any Actor-directory target uses version 2.

A version-2 journal may also contain existing work or projection targets when one
coordinated Actor correction explicitly affects those records.

## 27.12 Journal invariants

1. Actor operations use workspace scope plus exact Actor targets.
2. Operation Journal v2 is additive.
3. Existing operation identities and pointers remain valid.
4. Existing operation kinds are sufficient.
5. Contact and other sensitive payload is excluded from journal facts.
6. Actor sets are complete and deterministically ordered.
7. Partial consolidation and split are not successful subsets.
8. Exact replay requires the same intent digest.
9. Recovery uses evidence rather than age or timestamps.
10. Version-1 journals remain immutable.

---

# 28. Approved Decision 24: Actor-Aware Locks and Quarantine

## 28.1 Operation Lock v2

Issue #14 will introduce:

```text
operation_lock@2
```

Version 2 preserves the deterministic lock-key rule:

```text
lock_id =
  "lock_" + sha256(
    canonical_json({
      "lock_scope": lock_scope,
      "protected_target": protected_target
    })
  )
```

It adds Actor-directory scopes and protected targets.

Version-1 locks remain valid for existing scopes.

## 28.2 Added lock scopes

Operation Lock v2 adds:

```text
actor_directory_collection
actor_directory_record
```

### Actor-directory collection

Protects namespace-sensitive operations beneath:

```text
portia/actors/
```

Representative uses include:

- Actor creation;
- duplicate consolidation;
- Actor split;
- collection-wide migration;
- and discovery-sensitive repair.

It does not imply a lock over unrelated workspace content.

### Actor-directory record

Protects one exact:

```text
Actor
Contact Point
Actor-to-Student Relationship
Actor–Roster Student Collision
```

A multi-Actor operation acquires one deterministic lock per exact record rather
than one opaque set lock.

## 28.3 Lock ordering

The initial deterministic acquisition order is:

1. Actor-directory collection lock, when required;
2. Actor locks sorted by `actor_id`;
3. Contact Point locks sorted by `(actor_id, contact_point_id)`;
4. Relationship locks sorted by `(actor_id, relationship_id)`;
5. Collision locks sorted by `(actor_id, collision_id)`;
6. class/work or derived locks required by consuming-record corrections;
7. operation lock.

The implementation must document any refinement before production use.

All participants use the same total order.

## 28.4 No age-based lock inference

Actor locks have no:

```text
expires_at
released_at
heartbeat_at
state
```

Lock age, modification time, or process absence does not prove that a lock is
stale.

Release or takeover follows Issue #13 evidence and recovery rules.

## 28.5 Lock privacy

Protected targets contain opaque exact identity only.

Lock records do not contain:

- Actor display name;
- contact value;
- relationship detail;
- roster student name;
- removal payload;
- or duplicate-review narrative.

## 28.6 Quarantine Record v2

Issue #14 will introduce:

```text
quarantine_record@2
```

Version 2 preserves:

- immutable revisions;
- explicit current pointer selection;
- `active`, `released`, and `superseded` states;
- reason, effects, origin, resolution, and review evidence;
- and the separation between Quarantine and lifecycle.

It adds Actor-directory targets and one Actor-specific write effect.

## 28.7 Added Quarantine targets

Quarantine v2 adds:

```text
actor_directory_record
actor_directory_collection
actor_set
```

Actor-set Quarantine is permitted only when the risk is genuinely set-wide, such
as an incomplete consolidation or split.

When independent per-Actor controls are sufficient, separate exact Actor
Quarantines are preferred.

## 28.8 Added effect

Quarantine v2 adds:

```text
block_actor_directory_writes
```

Existing generic effects remain reusable, including:

```text
block_current_use
block_lifecycle_writes
block_operation_completion
block_projection_use
review_required
```

`block_actor_directory_writes` blocks writes to the targeted Actor root or
collection according to target scope.

It does not block unrelated class/work records unless separately targeted.

## 28.9 Actor Quarantine reasons

Existing reason categories remain broadly applicable.

Version 2 may add or document Actor-specific reason mapping for:

```text
actor_identity_contradiction
actor_replacement_reconciliation
actor_relationship_reconciliation
actor_contact_privacy
actor_roster_collision
actor_split_reconciliation
actor_removal_reconciliation
```

The final schema should prefer existing general reason values when they remain
semantically accurate, adding new enum values only where necessary.

## 28.10 Lifecycle separation

Quarantining an Actor does not change it to:

```text
inactive
invalidated
superseded
```

Releasing Quarantine does not reactivate an Actor.

Lifecycle and Quarantine require separate canonical evidence.

## 28.11 Quarantine current pointer

The existing:

```text
quarantine_current_pointer@1
```

remains unchanged.

It identifies only:

```text
quarantine_id
quarantine_revision
```

and does not embed target shape.

## 28.12 Quarantine privacy

Quarantine records preserve:

- exact target identity;
- bounded reason codes;
- supporting finding keys;
- operation references;
- effects;
- and review requirements.

They do not copy:

- contact values;
- display names;
- student names;
- relationship narratives;
- or removed payload.

## 28.13 Lock and Quarantine invariants

1. Lock v2 is additive.
2. Quarantine v2 is additive.
3. Collection and exact-record scopes are distinct.
4. Multi-Actor operations use deterministic per-record locks.
5. Lock age never proves staleness.
6. Quarantine does not mutate lifecycle.
7. Actor-specific write blocking is explicit.
8. Current-pointer contracts remain unchanged.
9. Sensitive payload is excluded.
10. Version-1 locks and Quarantines remain immutable.

---

# 29. Approved Decision 25: Derived State and Privacy-Minimized Operational Evidence

## 29.1 Existing derived contracts remain sufficient

Issue #14 reuses these published contracts unchanged:

```text
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

Actor-directory sources fit the existing model through:

```text
workspace scope
workspace-relative paths
exact byte lengths and SHA-256 digests
canonical_domain source role
operational_revision source role
operational_pointer source role
operational_lock source role
quarantine_state source role
```

No Actor payload field must be added to the metadata contracts.

## 29.2 Existing projection kinds

The initial Actor architecture reuses:

```text
incoming_reference_index
replacement_frontier_index
lifecycle_timeline
active_integrity_finding_index
active_quarantine_index
operation_recovery_queue
finding_acknowledgement_index
finding_suppression_index
current_state_view
```

These projection kinds are generic enough to include Actor-directory identity.

Issue #14 does not add a persisted Actor search index or duplicate-candidate
index.

Duplicate candidates appear through `active_integrity_finding_index`.

Actor search may initially use bounded canonical scanning and an in-memory index.

## 29.3 Projection scope

Actor projections ordinarily use:

```text
scope = workspace
```

A graph-scoped projection may use a nonsemantic `graph_id` when it represents a
specific replacement or incoming-reference graph.

The existing work scope is not used for Actor ownership.

## 29.4 Source-snapshot roles

Actor root, Contact Point, Relationship, Collision, Actor-directory lifecycle,
correction, amendment, migration, and exceptional-removal certificates are
canonical domain evidence.

They may use:

```text
source_role = canonical_domain
```

Operation Journal revisions, pointers, locks, and Quarantine use their existing
operational roles.

Issue #14 does not need a new source-role token merely to name Actor data.

## 29.5 Freshness

An Actor-derived generation is fresh only when its exact source snapshot still
matches all contract-significant canonical and operational sources required by
its declared scope and authorization coverage.

A generation does not remain fresh because:

- its build time is recent;
- Actor file modification times are unchanged;
- its generation ID sorts last;
- or its current pointer still exists.

## 29.6 Authorization-limited state

An authorization-limited Actor scan must declare:

```text
coverage = authorization_limited
```

with explicit limitation codes.

It must not produce:

- an empty-directory claim;
- a complete incoming-reference claim;
- a complete duplicate-candidate claim;
- or an exceptional-removal eligibility claim.

## 29.7 Privacy classes

Issue #14 establishes these operational privacy classes:

### Opaque identity

Examples:

```text
actor_id
contact_point_id
relationship_id
collision_id
transition_id
operation_id
quarantine_id
```

Opaque identity may appear where exact targeting is required.

It remains sensitive operational metadata when combined with other records.

### Low-sensitivity domain metadata

Examples:

```text
status token
contract version
record kind
broad Actor category
bounded reason code
path kind
byte length
```

These values may appear in diagnostics when necessary.

### Privacy-sensitive domain payload

Examples:

```text
display name
organization
title
email address
phone number
relationship detail
relationship source detail
verification detail
roster student identity
```

These values remain canonical only where the domain contract requires them.

They are not copied into ordinary operation facts.

### Prohibited operational duplication

The following must not appear in:

```text
lock files
finding keys
evaluation keys
intent digests as cleartext facts
Quarantine titles
nonsensitive derived summaries
removal certificates
```

unless a future explicit contract and threat analysis requires a safe
representation.

## 29.8 Digests do not declassify payload

A SHA-256 content fingerprint may be retained for integrity and recovery.

A deterministic unsalted digest of only a low-entropy contact value is not an
approved privacy-safe substitute.

Portia does not persist standalone email or phone hashes for cross-Actor lookup
in version 1.

Whole-file fingerprints remain permitted because they bind exact representations
and are not advertised as contact-value indexes.

## 29.9 Derived search

Teacher-facing Actor search may consider current canonical:

- display name;
- organization;
- title;
- category;
- lifecycle;
- and authorized Contact Point values.

The initial implementation may normalize those values in memory.

Search results must still resolve exact Actor identity.

Search similarity does not alter lifecycle, replacement, or duplicate status.

## 29.10 Current pointer meaning

A derived current pointer selects one generation.

It does not claim:

- freshness;
- complete authorization;
- Actor identity truth;
- duplicate equivalence;
- contact validity;
- or relationship authority.

Every consequential consumer verifies generation metadata and current sources
according to Issue #13.

## 29.11 Operational integration inventory

The pre-ADR public-contract result is:

| Contract | Issue #14 result |
| --- | --- |
| `operation_ref@1` | Reuse unchanged |
| `operation_journal_ref@1` | Reuse unchanged |
| `operation_current_pointer@1` | Reuse unchanged |
| `operation_journal@1` | Retain unchanged |
| `operation_journal@2` | Add Actor-aware target branches |
| `operation_lock@1` | Retain unchanged |
| `operation_lock@2` | Add Actor collection and record scopes |
| `quarantine_record@1` | Retain unchanged |
| `quarantine_record@2` | Add Actor targets and write effect |
| `quarantine_current_pointer@1` | Reuse unchanged |
| `integrity_finding@1` | Retain unchanged |
| `integrity_finding@2` | Add Actor record, set, and collection targets |
| `finding_acknowledgement@1` | Reuse unchanged |
| `finding_suppression@1` | Reuse unchanged |
| `finding_suppression_current_pointer@1` | Reuse unchanged |
| `source_snapshot@1` | Reuse unchanged |
| `derived_index_metadata@1` | Reuse unchanged |
| `derived_current_pointer@1` | Reuse unchanged |

## 29.12 Derived and privacy invariants

1. Existing derived contracts remain sufficient.
2. Actor projections use workspace or graph scope.
3. Missing or limited projections never imply empty state.
4. Actor search is initially bounded and nonauthoritative.
5. Duplicate candidates remain findings.
6. Contact values are not operational facts.
7. Whole-file fingerprints remain permitted.
8. Standalone deterministic contact hashes are prohibited.
9. Current pointers do not claim freshness.
10. Consequential consumers revalidate current source evidence.

---

## 30. Consequences of Decisions 1–25

The complete pre-ADR design requires these new version-1 Actor contracts:

```text
actor@1
actor_contact_point@1
actor_student_relationship@1
actor_roster_student_collision@1

exact_actor_ref@1
exact_actor_contact_point_ref@1
exact_actor_student_relationship_ref@1
exact_actor_roster_student_collision_ref@1
exact_actor_directory_record_ref@1
actor_target@1

actor_directory_lifecycle_transition@1
actor_directory_lifecycle_history_correction@1
actor_directory_amendment@1
actor_directory_record_migration@1
actor_directory_exceptional_removal@1
```

Required identifier additions include:

```text
portia_actor_contact_point_id@1
portia_actor_student_relationship_id@1
portia_actor_roster_student_collision_id@1
```

Existing scope-neutral identifiers are reused where applicable:

```text
portia_actor_id@1
portia_lifecycle_transition_id@1
portia_lifecycle_history_correction_id@1
portia_amendment_id@1
portia_record_migration_id@1
exceptional-removal identifier, subject to pre-ADR schema audit
```

Issue #14 also requires these additive public versions:

```text
integrity_finding@2
operation_journal@2
operation_lock@2
quarantine_record@2
```

These contracts remain unchanged:

```text
actor_ref@1
person_display_snapshot@1
roster_student_ref@1
operation_ref@1
operation_journal_ref@1
operation_current_pointer@1
quarantine_current_pointer@1
finding_acknowledgement@1
finding_suppression@1
finding_suppression_current_pointer@1
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

The accepted Actor replacement graph permits:

```text
one Actor -> one Actor
several Actors -> one Actor
one Actor -> several Actors
```

It prohibits:

```text
several Actors -> several Actors
Actor -> roster student replacement edge
silent reference retargeting
automatic child reassignment
```

A confirmed Actor–roster collision uses:

```text
Actor–Roster Student Collision record
+ Actor invalidation transition
+ explicit consuming-record correction
```

The operational model uses:

```text
workspace scope
+ exact Actor-directory targets
+ privacy-minimized paths and fingerprints
+ deterministic locks
+ recoverable journals
+ separate Quarantine
+ rebuildable derived state
```

No existing public schema will be modified in place.

## 31. Rejected alternatives through Decision 25

### Actor migration through class/work `record_migration@1`

Rejected because that contract requires a class-owned work and would fabricate
Actor ownership.

### Migration that changes Actor owner or contact value

Rejected because those changes alter semantic identity or assertion.

### Ordinary hard deletion

Rejected because it erases exact historical identity and incoming-reference
context.

### Removal certificate beneath the removable Actor root

Rejected because removing the root could remove its own surviving evidence.

### Retaining removed contact values in a certificate

Rejected because the certificate must not recreate prohibited payload.

### Reusing Integrity Finding v1 by placing Actor identity in a generic workspace target

Rejected because exact diagnostic identity would be lost.

### Separate Actor duplicate-review record

Rejected because Issue #13 finding administration already provides durable review
and bounded presentation suppression.

### New Actor-specific operation kinds

Rejected because existing operation semantics already describe creation,
correction, consolidation, migration, removal, scanning, and repair.

### Generic workspace target as Actor primary target

Rejected because workspace scope does not identify the record being changed.

### One lock for an opaque Actor set

Rejected because deterministic per-record locks provide clearer ownership and
ordering.

### Workspace-wide lock for every Actor update

Rejected because it unnecessarily blocks unrelated Actor operations.

### Lock expiry or heartbeat

Rejected because time and process liveness do not prove safe takeover.

### Quarantine encoded as Actor lifecycle

Rejected because operational safety and domain truth are separate.

### New Actor-specific derived metadata family

Rejected because Issue #13 source snapshots, generations, and pointers are
already scope-generic.

### Persisted Actor search index in version 1

Rejected because bounded scanning and an in-memory index are sufficient for the
initial teacher-local directory.

### Standalone contact-value hashes

Rejected because low-entropy values may be guessed and the hash would become a
privacy-sensitive correlation key.

## 32. Next slice

The next slice should perform the pre-ADR repository checkpoint and produce:

```text
ADR 0010
final accepted design status
exact public-contract inventory
implementation sequence
schema dependency ordering
```

No public schema should be added until the pre-ADR checkpoint confirms that the
accepted Core and Portia boundaries have not drifted.
