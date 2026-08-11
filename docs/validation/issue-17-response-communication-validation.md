# Issue #17 Validation: Response and Communication Domain Models

**Status:** Contract and integration validation complete
**Issue:** `#17 — Define Response and Communication domain models`
**ADR:** `0013 — Define Response and Communication Domain Models`
**Date:** 2026-08-10

## Result

Issue #17 establishes Portia's bounded action and communication layer while
preserving the separation among evidence, human judgment, action,
communication, ongoing Support, and later Outcome.

Public contracts introduced:

```text
portia_response_id@1
portia_communication_id@1
response@1
communication@1
```

No new target, represented-human, exact-reference, lifecycle-history,
Amendment, Statement of Disagreement, Dependency, migration,
exceptional-removal, operation, lock, Quarantine, Integrity Finding,
source-snapshot, derived-generation, or current-pointer contract was required.

## Repository anchors

See `docs/validation/issue-17-final-repository-checkpoint.md`.

```text
pds-portia branch (pre-closeout):
cd2bc6537b9007269fb1178a6168ccdcd459d232

pds-portia main:
34d8100a1775effc43737409f86ad0486c01fb34

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
```

Final remote comparison before closeout:

```text
7 commits ahead
0 behind
```

Portia `main` and Core `main` are unchanged from the initial Issue #17
checkpoint, so no drift requires a contract change.

## Test status

Immediately before the final closeout slice:

```powershell
python -m unittest discover -s tests/schema_validation
```

passed with:

```text
644 tests
0 failures
0 errors
```

The final closeout slice adds eight final-documentation tests and no schema
wire-shape changes. After applying it, a clean repository should report
**652 tests**. The observed result takes precedence.

## Fixture and application-invalid coverage

Response:

```text
valid:               10
structural-invalid:  13
application-invalid: 19
```

Communication:

```text
valid:               14
structural-invalid:  22
application-invalid: 33
```

Cross-record synthetic bundles:

```text
4
```

`docs/validation/issue-17-application-invalid-matrix.json` indexes:

```text
fixture application-invalid scenarios: 52
programmatic cross-record invariants:     8
total coverage entries:                  60
```

## Acceptance coverage

`docs/validation/issue-17-acceptance-matrix.json` contains all 60 acceptance
criteria from Issue #17.

Final status:

```text
pass:    60
pending:  0
```

## Response boundary

One Response is one Event-local bounded action with opaque `rsp_` identity,
explicit Event/Participant target, represented-human provider, stable action
family, execution state, timing, lifecycle, and preserved correction history.

Response remains distinct from evidence, Determination, longitudinal Support,
and Outcome. `recorded_institutional` consequence requires an exact same-Event
Determination. That link does not establish correctness, lawfulness,
proportionality, or effectiveness.

Response v1 exposes no Amendment surface. Material change uses
successor/history semantics.

## Communication boundary

One Communication is one Portia-work-local bounded human communication act or
attempt with opaque `comm_` identity, represented-human sender, one or more
explicit recipients, method, purpose, act state, privacy scope, timing, and
preserved correction history.

Event ownership is usable now. `support_process` ownership is structurally
reserved, while active current use remains blocked until Issue #18 publishes
the canonical Support Process owner.

Exact Actor Contact Point references preserve historical endpoint identity.
Preference is not consent; local verification is not delivery proof,
institutional verification, exclusive control, or authorization.

Communication stores a bounded summary rather than an unrestricted mutable
message body. Replies and repeated attempts are separate records.

## Communication versus Account

Communication records that a contact act or attempt occurred.

When a represented source makes a substantive assertion that matters as
evidence, the assertion remains separately preservable as Account.

`account_from_communication` therefore points to an exact Account without
turning Communication itself into source evidence.

## Response and Communication remain independent

One workflow may create both records without collapsing them.

Examples:

```text
teacher phones family
→ Communication

same contact explicitly tracked as an immediate action
→ Response + Communication relation

administrator decision conveyed to family
→ Communication linked to Determination

institutional consequence implemented
→ separate Response linked to Determination
```

A failed communication attempt and later completed communication remain two
canonical Communications; later success does not supersede or rewrite the
earlier attempt merely because it is later.

## Attachments and relations

Communication attachments remain schema-local in v1:

```text
workspace_file
portia_record
module_record
external_record
```

No binary payload is embedded. `source_artifact_ref@1` remains scoped to its
accepted Account/Observation semantics rather than being broadened for
convenience.

Communication relations use exact Portia work-record references with typed
purposes such as `responds_to`, `conveys_determination`,
`relates_to_response`, and `account_from_communication`.

## Shared infrastructure

`test_issue_17_shared_infrastructure_compatibility.py` proves reuse of:

```text
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
exceptional_removal@1
operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

Response and Communication add no family-specific forks of these contracts.

Exact dependencies and Contact Point references never silently follow
successors. Operational and derived records remain metadata-oriented and do not
copy substantive Response descriptions or Communication summaries.

## Paper, import, privacy, and automation

Paper preallocation cannot fabricate a Response or Communication.
Ingest/import representations remain proposed until accepted review history
permits current use. Imported uncertainty can be represented honestly.

Automation may validate contracts, resolve references, build timelines, prepare
drafts, and surface reminders. It must not automatically choose punishment,
escalate discipline from counts, infer risk, engagement, remorse, compliance,
effectiveness, legal-notice completion, or message delivery. Draft generation
does not mean communication occurred.

Restricted crisis, clinical, investigative, legal, and emergency details remain
outside ordinary Response/Communication payloads. Operational and derived state
remains privacy-minimized.

## Representative examples

`docs/examples/portia-response-and-communication-examples.md` documents all 32
required synthetic example classes and ties them to executable fixture/test
evidence.

## Documentation reconciliation

README and the schema guide now identify accepted ADR 0013,
`response@1`, `communication@1`, `rsp_`, and `comm_` as current implementation
targets.

ADR 0002 remains the broad module-boundary decision, but its historical
"family contact" shorthand under Immediate Responses is explicitly refined:
the communication act is Communication; a separate Response exists only when
the contact is itself deliberately tracked as a bounded action.

The Portia role analysis now carries an Issue #17 reconciliation note. The
Account/Observation design now states the downstream Communication-versus-
Account boundary. The Review/Classification/Hypothesis/Determination design now
states the downstream Determination-versus-Response/Communication boundary.

## Deferred work

Issue #18 owns Support Process / Support / Intervention / Implementation /
Fidelity. Issue #19 owns Follow-Up / Outcome / Reentry / Repair. Paper/PDS2,
privacy/export/retention, end-to-end examples, and final foundations audit remain
with Issues #20–#23.

## Acceptance commands

```powershell
python -m unittest `
  tests.schema_validation.test_issue_17_validation_artifacts `
  tests.schema_validation.test_issue_17_final_documentation
```

```powershell
python -m unittest discover -s tests/schema_validation
```

```powershell
git diff --check
git status --short
```
