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

New public schemas will use matching versioned paths and `$id` values beneath
directories such as `schemas/v1/` and `schemas/v2/`.

Canonical schemas do not use mutable `latest` or `current` identities.

## Schema catalog

`schemas/schema-catalog.json` is a noncanonical tooling catalog. It maps a
conceptual contract name and schema version to:

- the canonical schema `$id`; and
- the repository-relative source path.

The catalog supports validator setup and explicit version dispatch. It does
not override a schema's `$id`, become part of canonical Portia data, or serve
as a Paper Data Suite Core registry.

The initial catalog contains only the retained version-1 Event, Event
Participant, and Event Participant Role contracts. Later Issue #11
implementation slices will add shared references, targets, snapshots, Work
Relationship, compatibility adapters, and reconciled version-2 contracts.

## Offline resolution

Schema tests build a local `referencing.Registry` from checked-in schema
resources. Canonical HTTPS `$id` and `$ref` values identify public contracts,
while the local registry resolves them without network access.

An unresolved `$ref`, duplicate canonical `$id`, or disagreement between a
catalog entry and its source schema is a test failure.

## Public contracts and private helpers

An independently reusable persisted contract receives its own schema file and
canonical `$id`.

A schema may retain private, nonreusable helpers in local `$defs`. Public
contracts must not remain available only as private definitions inside another
schema.

## Validation boundary

JSON Schema establishes local structure. It does not establish target
existence, authoritative identity resolution, lifecycle eligibility,
authorization, duplicate state across files, or other cross-record
invariants. Those remain application-validation responsibilities.

## Running the schema tests

From the repository root, run:

    python -m unittest discover -s tests/schema_validation -p "test_*.py"

The test environment requires a current `jsonschema` release that supports
Draft 2020-12 validators and the `referencing` registry API.
