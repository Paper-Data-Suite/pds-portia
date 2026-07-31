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
