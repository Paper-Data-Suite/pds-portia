# Apply the Work Relationship v1 slice

Copy the package contents into the repository root while preserving paths.

## New schema

- `schemas/v1/work-relationship.schema.json`

## New tests and fixtures

- `tests/schema_validation/test_work_relationship_schema.py`
- all files beneath `tests/schema_validation/fixtures/work_relationship/v1/`

## Replace

- `schemas/schema-catalog.json`
- `schemas/README.md`

## Do not modify

- retained Event-family version-1 schemas
- existing identifier, reference, target, snapshot, provenance, attribution,
  text, or timestamp schemas
- `tests/schema_validation/schema_support.py`
- existing fixtures and test modules

## Validation boundary

Files under `application_invalid/` and `application_invalid_sets/` are
intentionally valid against JSON Schema. They exercise cross-field and
cross-record application invariants and must not be moved under `invalid/`.

## Run

    python -m unittest discover -s tests/schema_validation -p "test fixture set
- `test_work_relationship_schema.py`
- `APPLY.md`

Full assembled validation:

```text
Ran _*.py"

Suggested commit:

    feat: add Work Relationship schema
