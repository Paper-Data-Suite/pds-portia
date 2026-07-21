# Portia Event and Event Participant Schema Validation

* **Validation date:** 2026-07-21
* **Schemas:**
  * `schemas/event.schema.json`
  * `schemas/event-participant.schema.json`
* **JSON Schema dialect:** Draft 2020-12
* **Reference validation environment:**
  * Python 3.13.5
  * `jsonschema` 4.26.0

## Purpose

This validation package confirms that the initial Portia Event and Event Participant schemas:

* are valid JSON Schema Draft 2020-12 documents;
* accept representative supported records;
* reject representative structurally invalid records;
* preserve strict discriminated unions;
* reject embedded records that belong in separate canonical files;
* and distinguish schema validation from application-level validation.

The fixtures are synthetic and contain no real student data.

## Files

```text
tests/schema_validation/
  test_event_and_participant_schemas.py
  fixtures/
    event/
      valid/
      invalid/
    event_participant/
      valid/
      invalid/
```

The automated tests load the canonical schemas from:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
```

No schema copies are stored in the test directory.

## Dependency

The tests use the standard-library `unittest` runner and one external package:

```text
jsonschema>=4.18,<5
```

Install it in the active development environment:

```bash
python -m pip install "jsonschema>=4.18,<5"
```

This validation package does not establish a project-wide Python dependency or packaging policy.

## Run the Tests

From the repository root:

```bash
python -m unittest discover           -s tests/schema_validation           -p "test_*.py"           -v
```

Expected result:

```text
Ran 5 tests
OK
```

Each fixture is evaluated within a `subTest`, so a failing file is identified by name.

## Fixture Coverage

### Valid Event Fixtures

The valid Event fixtures cover:

* a minimal digital draft without occurrence or summary;
* a preallocated paper draft;
* an active exact-time digital Event;
* an active imported Event with unknown occurrence time;
* a closed Event representing a bounded observation range;
* and an active replacement Event with a canonical `supersedes` reference.

### Invalid Event Fixtures

The invalid Event fixtures verify rejection of:

* an active Event missing occurrence;
* a closed Event missing summary;
* a timestamp without an explicit offset;
* contradictory approximate-occurrence fields;
* incomplete paper-capture provenance;
* `other` location without detail;
* embedded participant data in `work.json`;
* and obsolete `returned_paper` creation-source terminology.

### Valid Event Participant Fixtures

The valid participant fixtures cover:

* an active roster student;
* an active cross-class roster student;
* an active Actor;
* an active descriptive person;
* a proposed unknown person created by paper ingestion;
* and an active roster student that supersedes a previously unknown participant.

### Invalid Event Participant Fixtures

The invalid participant fixtures verify rejection of:

* a roster-student subject without a display snapshot;
* embedded participant roles;
* an invalid participant-ID prefix;
* incomplete paper-capture provenance;
* fields from multiple subject variants;
* `other` supersession reason without detail;
* an unsupported unknown-person reason;
* and fields from multiple attribution-agent variants.

## Schema-Level Assertions

These tests exercise requirements that JSON Schema can enforce locally:

* required properties;
* constants;
* enumerated values;
* identifier patterns;
* timestamp and date syntax;
* mutually exclusive occurrence variants;
* mutually exclusive participant-subject variants;
* creation-source variants;
* attribution-agent variants;
* status-dependent Event requirements;
* conditional detail requirements;
* and rejection of unknown properties.

## Application-Level Validation Not Covered

Passing JSON Schema validation does not establish that a record is operationally valid in a Portia workspace.

Application validation remains responsible for:

* matching `class_id`, `work_id`, and `participant_id` to canonical paths;
* confirming that the owning Core class exists;
* validating school-year semantics;
* resolving roster-student references;
* confirming Actor existence;
* confirming PDS2 route and page-record existence;
* confirming route, page, class, and Event consistency;
* checking that `updated_at` does not precede `created_at`;
* validating start and end chronology;
* enforcing Event lifecycle transitions;
* enforcing Event Participant lifecycle transitions;
* writing and reconciling append-only lifecycle history;
* enforcing immutable creation provenance;
* requiring teacher review for paper- or import-derived proposals;
* requiring at least one active participant before Event activation;
* preventing duplicate active durable participants;
* protecting the final active participant of an active Event;
* validating replacement ordering;
* confirming same-Event scope for participant supersession;
* confirming incoming replacement relationships for superseded Events;
* and coordinating multi-file writes, rollback, repair, and recovery.

Those checks require repository paths, Core data, related records, prior state, or transaction context and therefore do not belong in the two record schemas.

## Reference Validation Result

The package was run against the Issue #6 schemas using:

```text
Python 3.13.5
jsonschema 4.26.0
```

Results:

```text
Schema meta-validation: passed
Valid Event fixtures: 6 passed
Invalid Event fixtures: 8 correctly rejected
Valid Event Participant fixtures: 6 passed
Invalid Event Participant fixtures: 8 correctly rejected
Automated test methods: 5 passed
```

## Maintenance Rules

When either schema changes:

1. run the full validation suite;
2. add or revise fixtures for every new branch, enum, conditional requirement, or prohibited property;
3. keep valid and invalid fixture intent evident from filenames;
4. preserve synthetic data only;
5. update this document’s fixture counts and coverage;
6. and add separate application tests for invariants that cannot be expressed in JSON Schema.

A schema change is incomplete when it changes accepted or rejected behavior without a corresponding fixture.
