# Issue #17 Validation: Response and Communication Domain Models

**Status:** Implementation validation complete; final repository reconciliation pending
**Issue:** `#17 — Define Response and Communication domain models`
**ADR:** `0013 — Define Response and Communication Domain Models`
**Date:** 2026-08-10

## Result

Issue #17 now establishes Portia's bounded action and communication layer while preserving the existing separation among evidence, human judgment, action, communication, ongoing Support, and later Outcome.

Public contracts introduced:

```text
portia_response_id@1
portia_communication_id@1
response@1
communication@1
```

No new target, represented-human, exact-reference, lifecycle-history, Amendment, Statement of Disagreement, Dependency, migration, exceptional-removal, operation, lock, Quarantine, Integrity Finding, source-snapshot, derived-generation, or current-pointer contract was required.

## Repository anchors

Initial and pre-ADR anchors are recorded in:

```text
docs/validation/issue-17-initial-repository-checkpoint.md
docs/validation/issue-17-pre-adr-checkpoint.md
```

The final Portia/Core drift checkpoint is intentionally deferred to the final closeout slice. `docs/validation/issue-17-final-repository-checkpoint.md` must be added only after the final pre-acceptance drift verification is performed.

Current implementation branch commit verified before this validation slice:

```text
0020aca5fc354df65e4699feaaa215a876315d9a
```

## Test status

Immediately before this validation-artifact slice, the authoritative command:

```powershell
python -m unittest discover -s tests/schema_validation
```

passed with:

```text
638 tests
0 failures
0 errors
```

The focused shared-infrastructure suite reported:

```text
16 tests
0 failures
0 errors
```

This slice adds six validation-artifact consistency tests and no public wire-shape changes. After applying the slice, a clean repository should therefore report **644 tests**. The observed test output always takes precedence over this expected count.

## Fixture coverage

Response fixture manifest:

```text
valid:               10
structural-invalid:  13
application-invalid: 19
```

Communication fixture manifest:

```text
valid:               14
structural-invalid:  22
application-invalid: 33
```

Cross-record bundles:

```text
valid scenario bundles: 4
```

The two identifier primitives additionally have focused valid/invalid boundary coverage.

## Application-invalid coverage

`docs/validation/issue-17-application-invalid-matrix.json` indexes:

```text
fixture application-invalid scenarios: 52
programmatic cross-record invariants:     8
total coverage entries:                  60
```

## Acceptance coverage

`docs/validation/issue-17-acceptance-matrix.json` records all 60 checklist criteria recovered from Issue #17.

At this intermediate closeout point:

```text
pass:    57
pending: 3
```

The pending criteria are deliberately limited to:

1. final repository/Core drift checkpoint;
2. final validation-note completion after that checkpoint;
3. README/schema-guide and related active-document reconciliation.

No pending criterion is being represented as a pass.

## Response boundary

One Response is one Event-local bounded action with opaque `rsp_` identity, explicit Event/Participant target, represented-human provider, stable action family, execution state, timing, lifecycle, and preserved correction history.

Response remains distinct from evidence, Determination, longitudinal Support, and Outcome. `recorded_institutional` consequence requires an exact same-Event Determination; the link does not establish correctness, lawfulness, proportionality, or effectiveness.

Response v1 exposes no Amendment surface. Material changes use successor/history semantics.

## Communication boundary

One Communication is one Portia-work-local bounded human communication act or attempt with opaque `comm_` identity, represented-human sender, one or more explicit recipients, method, purpose, act state, privacy scope, timing, and preserved correction history.

Event ownership is usable now. `support_process` ownership is structurally reserved but current-use validation remains blocked until Issue #18 publishes the canonical Support Process owner.

Exact Actor Contact Point references preserve historical endpoint identity. Preference is not consent; local verification is not delivery or exclusive control.

Communication stores a bounded summary, not an unrestricted mutable message body. Replies and repeated attempts are separate records.

## Communication versus Account

Communication records that contact occurred. When a represented source makes a substantive assertion that matters as evidence, that assertion remains separately preservable as Account.

The cross-record fixture and compatibility test prove that `account_from_communication` points to an exact Account without making Communication itself a qualifying source-evidence record.

## Attachments and relations

Communication attachments remain schema-local in v1:

```text
workspace_file
portia_record
module_record
external_record
```

No binary payload is embedded. `source_artifact_ref@1` was not broadened beyond its accepted Account/Observation semantics.

Communication relations use exact Portia work-record references with typed purposes such as `responds_to`, `conveys_determination`, `relates_to_response`, and `account_from_communication`.

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

Exact dependencies and Contact Point references do not silently follow successors. Operational and derived records remain metadata-oriented and do not copy substantive Response descriptions or Communication summaries.

## Paper, import, and automation

Paper preallocation cannot fabricate a Response or Communication. Ingest/import representations remain proposed until accepted review history permits current use. Imported uncertainty can be represented honestly.

Automation may validate contracts, resolve references, build timelines, prepare drafts, and surface reminders. It must not automatically choose punishment, escalate discipline, infer risk, engagement, remorse, compliance, effectiveness, legal notice completion, or message delivery. Draft generation does not mean communication occurred.

## Representative examples

`docs/examples/portia-response-and-communication-examples.md` documents all 32 required synthetic example classes and ties each to executable fixture/test evidence.

## Remaining closeout work

The final Issue #17 slice must:

1. reverify Portia `main`, this branch, Core `main`, and materially relevant sibling contracts;
2. add `docs/validation/issue-17-final-repository-checkpoint.md`;
3. reconcile README, schema guide, and related active/historical design documentation;
4. change the three pending acceptance criteria to `pass`;
5. change this validation note from pending to final;
6. run the focused final-documentation test, full authoritative schema-validation discovery, and `git diff --check`.

## Acceptance commands for this slice

```powershell
python -m unittest `
  tests.schema_validation.test_issue_17_validation_artifacts
```

```powershell
python -m unittest discover -s tests/schema_validation
```

```powershell
git diff --check
git status --short
```
