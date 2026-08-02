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

The catalog contains the retained Event-family contracts and the versioned
shared contracts implemented by Portia.

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

The retained Event-family version-1 schemas keep their private historical
`$defs` unchanged. New record contracts compose these public shared schemas so
that provenance, attribution, text, and timestamp behavior do not drift across
record families.

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
