# Portia JSON Schemas

Portia uses JSON Schema Draft 2020-12 for structural validation of canonical
records and reusable value objects.

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

The catalog currently contains the retained version-1 Event-family contracts
and the version-1 identifier contracts.

## Identifier contracts

Portia-owned identifiers are independently addressable beneath
`schemas/v1/identifiers/`.

The initial prefixes are:

- Event: `evt_`
- Support Process: `sup_`
- Actor: `actr_`
- Event Participant: `ep_`
- Event Participant Role: `epr_`
- Work Relationship: `rel_`

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

Use `local_record_ref` when the consuming schema already supplies one
unambiguous Portia work scope. Use `portia_work_record_ref` when the target
Portia work must be stated explicitly.

These schemas validate local structure only. Target existence, authoritative
resolution, lifecycle eligibility, contract support, authorization, and
consumer-specific use remain application-validation responsibilities.

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

## Offline resolution

Schema tests build a local `referencing.Registry` from checked-in schema
resources. An unresolved `$ref`, duplicate canonical `$id`, or disagreement
between a catalog entry and its source schema is a test failure.

## Validation boundary

JSON Schema establishes local structure. It does not establish target
existence, authoritative identity resolution, lifecycle eligibility,
authorization, duplicate state across files, or other cross-record invariants.

## Running the schema tests

From the repository root, run:

    python -m unittest discover -s tests/schema_validation -p "test_*.py"
