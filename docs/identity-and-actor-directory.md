# Core roster identity and the Portia Actor Directory

Issue #39 implements Portia's production identity-resolution boundary for the
v0.2.0 workflow. It connects authoritative Core rosters to Portia's existing
immutable Actor Directory contracts and guarded persistence without turning
Portia into a second roster owner or a workspace-wide person registry.

The active dependency baseline is:

```text
Python >=3.11
pds-core>=0.6.3,<0.7
pds-portia 0.2.0 development line
```

## Identity boundaries

The fundamental identities remain distinct:

```text
class-qualified roster identity != Actor identity
class-qualified roster identity != participant identity
Actor identity != participant identity
display snapshot != identity
```

A Core roster student is identified by:

```text
class_id + student_id
```

The class component is part of identity. Therefore
`("class_a", "student_17")` and `("class_b", "student_17")` are different
roster identities even when the local `student_id` text is identical.

Portia does not infer that two class-qualified records describe one longitudinal
person. If a teacher-local Actor has accepted relationships to students in more
than one class, those are multiple explicit relationship assertions, not a
global student/person merge.

## Names are display data

Names are display data, not identity.

Authoritative resolution never keys on:

- first, last, full, or preferred name;
- initials;
- capitalization or whitespace normalization;
- punctuation or Unicode normalization; or
- fuzzy or approximate similarity.

`CoreRosterResolver` intentionally exposes only exact class and student-ID
resolution. There is no authoritative name lookup or "best match" operation.
A name change does not change roster identity when `class_id + student_id`
remains unchanged.

## Core roster authority

Core owns class folders, rosters, and `StudentRecord` values. Portia consumes
Core's public v0.6.3 APIs:

```text
pds_core.classes.load_class_roster
pds_core.rosters.Roster
pds_core.rosters.StudentRecord
pds_core.rosters.student_lookup
```

Portia does not read Core-private files or mutate a roster while resolving
identity.

`CoreRosterResolver` distinguishes these outcomes:

```text
successful exact resolution
invalid identifier input
class roster absent
student absent from an existing roster
requested/returned class mismatch
malformed or unsupported roster data
Core/workspace access failure
```

A read/access failure is never reported as student absence. A roster returned
for another class is never silently accepted or retargeted.

Roster resolution is read-only. It does not create an Actor, Relationship,
Contact Point, Event Participant, or any other Portia canonical record.

## Actor identity

An Actor is a Portia-owned teacher-local identity for a recurring non-roster
human collaborator. Actor identity is opaque and separate from Core roster
identity.

An Actor ID does not satisfy a roster lookup. An Actor display name does not
prove roster identity. Actor existence does not imply that any
Actor–Student Relationship exists.

The service facade is `ActorDirectoryService`. It composes the guarded storage
services established by Issue #38; it does not create a second write path.

The Actor Directory supports exact:

- Actor create/load/guarded replacement;
- Contact Point resolution;
- Actor–Student Relationship create/load/guarded replacement;
- bounded relationship enumeration; and
- current-use eligibility checks.

## Explicit Actor–Student Relationship

An Actor↔student association exists only through an accepted
Actor–Student Relationship record.

The Relationship contains one exact `student_ref` with `class_id + student_id`.
Resolving it invokes the Core roster resolver for that exact pair. Matching
names, matching local IDs in another class, another Relationship, or apparent
cross-year similarity never creates or changes the association.

Current use requires the persisted Relationship to be active and locally
reviewed. When an effective period is present, the requested current-use date
must fall within that period. Actor and Contact Point current selection likewise
requires their exact persisted representation to be active. Full append-only
lifecycle/history reconciliation (including imported-record review-history gates)
remains a cross-record validation responsibility; the identity service does not
reconstruct or silently repair lifecycle history merely to answer an exact load.
These checks do not establish legal guardianship, custody, consent, disclosure
permission, or institutional authority.

## Exact historical behavior

Exact Actor-family references are never silently redirected.

Portia does not automatically:

- follow a successor Actor;
- replace a historical Contact Point reference;
- migrate a Relationship;
- convert a superseded representation into its successor; or
- rewrite another Portia record because Actor Directory state changed.

An exact representation that exists but is not current-use eligible remains an
exact historical read. Current-use eligibility is a separate question.

## Quarantine

Quarantine is operational protection, not lifecycle.

```text
Quarantine != inactive
Quarantine != invalidated
Quarantine != removed
```

`ActorDirectoryService` asks the Issue #38 `QuarantineGuard` before ordinary
Actor Directory writes and before current-use operations. Actor-record,
Actor-set, and Actor-directory-collection scopes therefore retain the target
semantics already defined by Quarantine v2.

A `block_current_use` effect does not erase historical exact readability. A
`block_actor_directory_writes` effect does not mutate the Actor or Relationship
lifecycle merely because the write is refused.

## Exceptional removal

Exceptional removal is not historical nonexistence.

Actor Directory removal certificates remain outside Actor roots. The bounded
`ActorDirectoryRepository` can enumerate and strictly parse those certificates.
When an exact payload is absent but a matching accepted certificate exists,
`ActorDirectoryService.resolve_*()` reports the distinct
`exceptionally_removed` disposition and retains the certificate as identity
evidence.

Ordinary `load_*()` calls fail with `ActorDirectoryRemovedError` rather than
pretending the identity never existed. If both the payload and its removal
certificate are simultaneously present, the service treats that as recovery
work rather than choosing one silently.

## Validation context and I/O boundary

Application graph validation remains I/O-free.

The supported direction is:

```text
caller
  -> Core/Actor resolver
  -> bounded authoritative identity facts
  -> validation context
  -> validate_record_graph(...)
```

`ResolvedIdentityValidationContext` carries positive facts from successful
individual resolutions. An identity that was not checked remains `None`
(unknown), not `False`.

`RosterSnapshotValidationContext` represents complete authority for explicitly
loaded classes. It may report `False` for an absent student inside one of those
loaded classes while still returning `None` for classes that were not loaded.

This avoids turning a partial lookup into a false global negative.
`validate_record_graph()` itself does not read a workspace, load Core, inspect
Actor files, or access the network.

## Issue #22 identity parity

Issue #39 owns production behavior for:

```text
G22-005  cross-class local-ID merge
G22-006  display-name merge
G22-007  Actor substitutes for roster identity
```

It also owns the bounded roster-scope portion of `G22-009`: a Core result from
another class cannot be reported as the requested identity. Other producer and
foreign-custody semantics remain with their owning resolvers.

The machine-readable accounting is `portia.identity.issue22_parity`.

## Ownership summary

Core owns:

- class and roster storage;
- roster validation;
- `StudentRecord` authority; and
- correction of roster data.

Portia owns:

- Actor records and Actor child records;
- explicit Actor–Student Relationship assertions;
- Actor current-use policy within the accepted contracts; and
- Portia persistence, Quarantine, and exceptional-removal semantics.

Portia does not add, rename, merge, move, or delete Core roster students while
performing identity resolution.
