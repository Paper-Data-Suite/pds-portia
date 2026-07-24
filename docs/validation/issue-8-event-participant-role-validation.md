# Issue #8 Validation: Event Participant Role Domain Model

* **Issue:** [#8 — Define the initial Event Participant Role domain model](https://github.com/Paper-Data-Suite/pds-portia/issues/8)
* **Branch:** `8-event-participant-role-domain-model`
* **Validation date:** 2026-07-24
* **Result:** Passed

## Scope

This validation covers the initial Portia Event Participant Role schema and its integration with the existing Event and Event Participant schema-validation suite.

The validated artifacts include:

```text
schemas/event.schema.json
schemas/event-participant.schema.json
schemas/event-participant-role.schema.json
```

The Event Participant Role fixture suite is located at:

```text
tests/schema_validation/fixtures/event_participant_role/
  valid/
  invalid/
```

The automated validation module is:

```text
tests/schema_validation/test_event_and_participant_schemas.py
```

## Validation Standard

All three schemas use:

```text
JSON Schema Draft 2020-12
```

The test suite performs schema meta-validation before validating fixture records.

## Command

The complete schema-validation suite was run from the repository root with:

```powershell
python -m unittest discover -s tests/schema_validation -p "test_*.py" -v
```

## Result

```text
test_invalid_event_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_invalid_event_fixtures) ... ok
test_invalid_event_participant_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_invalid_event_participant_fixtures) ... ok
test_invalid_event_participant_role_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_invalid_event_participant_role_fixtures) ... ok
test_valid_event_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_valid_event_fixtures) ... ok
test_valid_event_participant_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_valid_event_participant_fixtures) ... ok
test_valid_event_participant_role_fixtures (test_event_and_participant_schemas.FixtureValidationTests.test_valid_event_participant_role_fixtures) ... ok
test_schemas_are_valid_draft_2020_12 (test_event_and_participant_schemas.SchemaMetaValidationTests.test_schemas_are_valid_draft_2020_12) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.335s

OK
```

## Fixture Results

The Event Participant Role fixture suite contains:

```text
12 valid fixtures
18 invalid fixtures
```

Validation confirmed that:

* every valid Role fixture was accepted;
* every invalid Role fixture was rejected;
* the Event and Event Participant fixture suites continued to pass;
* and all three schemas passed Draft 2020-12 meta-validation.

## Valid Fixture Coverage

The valid Event Participant Role fixtures cover:

* direct reviewed digital creation as active;
* an active `directly_involved` Role;
* an active `present` Role with Observation basis;
* a proposed `contextual` Role without detail;
* an active `contextual` Role with required detail;
* an invalidated contextual proposal that never became active;
* a paper-derived proposed `reported_involved` Role;
* a paper-derived active `reported_involved` Role with matching paper basis and Account reference;
* an imported proposed `reported_involved` Role;
* an imported active `reported_involved` Role with Account reference;
* role-type correction through a successor Role;
* basis correction through a successor Role;
* and duplicate consolidation through structured supersession.

## Invalid Fixture Coverage

The invalid Event Participant Role fixtures cover rejection of:

* an invalid `role_id` prefix;
* top-level detail on a non-contextual Role;
* an active contextual Role without detail;
* whitespace-only contextual detail;
* a proposed `reported_involved` Role without source-oriented basis;
* an active paper-derived `reported_involved` Role without an Account reference;
* a superseded imported `reported_involved` Role without an Account reference;
* paper Role creation using `stage = preallocated`;
* a paper-derived Role without paper basis;
* a paper-derived Role whose basis contains no `paper_capture` entry;
* malformed paper basis;
* an Account reference that improperly repeats Event scope;
* duplicate basis entries;
* an `other` supersession reason without required explanation;
* duplicate supersession entries;
* a timestamp without an explicit UTC offset or `Z`;
* an unsupported judgmental role type;
* and an embedded `roles` property.

## Schema-Enforced Invariants

The Event Participant Role schema enforces local record structure, including:

* required canonical envelope fields;

* `record_type = event_participant_role`;

* `module_id = portia`;

* `role_id` using the `epr_` prefix;

* the initial status vocabulary:

  ```text
  proposed
  active
  invalidated
  superseded
  ```

* the initial neutral role vocabulary:

  ```text
  directly_involved
  present
  reported_involved
  contextual
  ```

* structured `creation_source` variants;

* Role-specific `paper_capture / ingested` provenance;

* structured basis variants;

* source-oriented basis for `reported_involved`;

* an Account reference for active and superseded `reported_involved`;

* a paper-basis entry for paper-derived Roles;

* compact Event-local Account and Observation references;

* top-level detail only for `contextual`;

* required detail for active and superseded contextual Roles;

* structured forward supersession references;

* controlled supersession reasons;

* required detail when a supersession reason is `other`;

* unique array entries;

* timezone-aware provenance timestamps;

* and rejection of unknown or misplaced properties.

## Application-Level Invariants

Successful JSON Schema validation does not establish every Event Participant Role domain invariant.

Application validation remains responsible for rules requiring canonical paths, other records, lifecycle history, or evaluation of several Role files together.

These include:

### Canonical location and parent records

* `class_id` and `work_id` matching the canonical filesystem path;
* the owning Event existing;
* the referenced Event Participant existing beneath the same Event;
* the participant being active before Role activation;
* and the Event being `draft` or `active` before Role activation.

### Event-local references

* Account references resolving to Accounts beneath the same Event;
* Observation references resolving to Observations beneath the same Event;
* the referenced Account preserving valid attribution;
* and referenced records having lifecycle states eligible for their intended use.

### Paper provenance

* the paper-basis `route_id` exactly matching the Role creation-source `route_id`;
* the paper-basis `page_record_id` exactly matching the Role creation-source `page_record_id`;
* route and page records existing;
* and route, page, Event, participant, and Role ownership remaining consistent.

### Active-role compatibility

Application validation must evaluate all active Roles for one Event Participant and enforce the initial compatibility model.

Permitted combinations are:

```text
present + directly_involved
present + reported_involved
present + contextual
```

Prohibited combinations are:

```text
directly_involved + reported_involved
directly_involved + contextual
reported_involved + contextual
```

Application validation must also prohibit more than one active Role of the same type for the same participant and Event.

### Lifecycle and supersession

Application validation must enforce:

* allowed Role lifecycle transitions;
* terminal `invalidated` and `superseded` states;
* append-only lifecycle history;
* immutable persisted `participant_id`;
* same-Event supersession references;
* prevention of self-reference and supersession cycles;
* prospective supersession while a successor remains proposed;
* effective supersession only when the successor becomes active;
* and coordinated activation of the successor with supersession of prior Roles.

### Account dependencies

Application validation must ensure that:

* every active `reported_involved` Role retains at least one qualifying attributed Account;
* correcting an Account does not silently retarget an active Role;
* invalidating or superseding an Account resolves all dependent active Roles;
* and an Account lifecycle operation does not leave an active reported Role without qualifying support.

### Participant dependencies

Application validation must ensure that:

* an active Role never points to an inactive participant;
* participant invalidation resolves dependent active Roles;
* participant supersession creates successor Roles or invalidates relationships that do not carry forward;
* and existing Role records are never retargeted to another participant.

### Event lifecycle and visibility

Application validation and derived-view logic must distinguish stored Role status from effective visibility.

Ordinary current visibility requires:

```text
Role status = active
Event Participant status = active
Event status = active
```

Event closure, reopening, cancellation, invalidation, or supersession must follow the accepted Role visibility and retention rules without silently rewriting every child Role.

### Chronology, retention, and coordinated writes

Application validation must also enforce:

* provenance timestamp chronology;
* lifecycle timestamp chronology;
* creation-source immutability;
* canonical no-hard-delete rules;
* append-only correction history;
* atomic or recoverable participant, Account, Role, and supersession operations;
* and recovery from incomplete staged writes.

## Interpretation of the Result

The successful test run establishes that:

1. the Event Participant Role schema is a valid Draft 2020-12 schema;
2. the schema accepts the intended valid fixture shapes;
3. the schema rejects the targeted invalid fixture shapes;
4. the new Role tests integrate successfully with the existing Event and Event Participant test suite;
5. and the schema changes did not introduce a regression in the previously validated fixture sets.

The test run does not claim that the application-level invariants listed above have been implemented.

Those invariants are documented by the design specification and ADR 0006 and must be implemented and tested when Portia gains executable lifecycle, reference-resolution, transaction, and derived-view logic.

## Conclusion

Issue #8’s Event Participant Role schema and schema-fixture suite passed validation.

```text
Schemas meta-validated: 3
Tests passed: 7
Valid Role fixtures accepted: 12
Invalid Role fixtures rejected: 18
Result: PASS
```
