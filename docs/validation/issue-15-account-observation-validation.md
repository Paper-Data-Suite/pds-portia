# Issue #15 Validation: Account and Observation Domain Models

**Status:** Contract and integration validation complete
**Issue:** `#15 — Define Account and Observation domain models`
**ADR:** `0011 — Define Account and Observation Domain Models`
**Date:** 2026-08-07

## Result

Issue #15 establishes canonical Event-local Account and Observation evidence
without turning either family into a finding or objective Event truth.

Public contracts introduced:

```text
portia_account_id@1
portia_observation_id@1
represented_human_attribution@1
evidence_time@1
source_artifact_ref@1
account@1
observation@1
```

No new Role, lifecycle-history, Amendment, Dependency, migration, exceptional
removal, operational, Quarantine, Integrity Finding, source-snapshot, or
derived-generation contract was required.

## Repository anchors

See `docs/validation/issue-15-final-repository-checkpoint.md`.

```text
pds-portia branch:
2ce756f83cab5bedcbc00c931dedd370c9c68c53

pds-portia main:
ed09e6779281a23be05124afdb266579d2d560de

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
```

## Validation corpus

After the representative examples in this slice, Issue #15 manifests contain:

```text
valid scenarios:               82
structurally invalid:          87
application-invalid scenarios: 76
total manifest scenarios:     245
```

The 87 structural-invalid scenarios comprise 86 ordinary `invalid` entries plus
the one Role-v3 structural-invalid Observation-only `reported_involved`
scenario.

The complete application-invalid index is:

`docs/validation/issue-15-application-invalid-matrix.json`

The acceptance index is:

`docs/validation/issue-15-acceptance-matrix.json`

## Test status

Immediately before this finalization slice, the complete repository command:

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"
```

passed with:

```text
508 tests
0 failures
0 errors
```

This slice adds valid fixture entries and documentation but no new unittest test
methods. Rerun the same full discovery command after applying it.

## Account validation boundary

JSON Schema enforces the closed envelope, `acct_` identity, Event-local work
envelope, target shape, represented-human source shape, information-origin and
source-certainty vocabularies, quote/summary segmentation, evidence-time shape,
Account relation vocabulary, source-artifact references, lifecycle vocabulary,
supersession structure, paper-preallocation prohibition, and operation
attribution shape.

Application validation covers canonical path/Event resolution, Participant
target resolution, represented-source resolution, chronology, paper/import
review gates, `reports_from` origin compatibility, relation self/duplicate
checks, supersession topology, source-evidenced retraction, active
`reported_involved` source eligibility, same-Event basis, Participant alignment,
current-use eligibility, and no silent successor following.

## Observation validation boundary

JSON Schema enforces the closed envelope, `obs_` identity, Event-local work
envelope, target shape, human/instrument observer branches, method vocabulary,
narrative/measurement content, bounded measurement shapes, evidence-time shape,
source-artifact references, lifecycle vocabulary, supersession structure,
paper-preallocation prohibition, and operation attribution shape.

Application validation covers canonical path/Event resolution, target/observer
resolution, chronology, paper/import review gates, method-observer
compatibility, manual count/timing measurement compatibility, artifact-review
provenance, supersession topology, lifecycle/current-use eligibility, Role
same-Event/target alignment, and no silent successor following.

## `reported_involved`

Published `event_participant_role@3` remains immutable.

A qualifying active Account must be active, same-Event, explicitly referenced,
traceably attributed, and targeted to the same Participant or a Participant set
containing that Participant. Event-wide Account basis is insufficient.

Observation, paper provenance, import provenance, free text, and teacher
confirmation cannot satisfy the Account requirement by themselves.

## Retraction and correction

Account retraction requires a new active same-source Account with exact
`retracts` linkage plus a coordinated predecessor `active -> retracted`
transition using source-retraction semantics. Retraction does not prove the
earlier Account false.

Account and Observation v1 expose no in-place Amendment paths for primary
evidence. Material correction uses explicit replacement/supersession. Exact
historical references do not silently follow replacement, consolidation,
migration, ownership correction, or exceptional removal.

## Shared infrastructure

Compatibility tests prove reuse of:

```text
lifecycle_transition@1
lifecycle_history_correction@1
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

## Privacy

Operational and derived state should retain opaque IDs, record kinds, contract
versions, paths, fingerprints, byte lengths, status tokens, counts, and bounded
machine-readable facts rather than Account quote/summary text or Observation
narrative.

Quarantine free-text reason detail is subject to application-level
substantive-text-leak validation. Integrity Findings remain diagnostics and must
not become source credibility, misconduct, severity, risk, or policy findings.

## Paper and import

Issue #15 reuses `creation_source@1`. Canonical Account/Observation creation is
prohibited at paper preallocation. Paper/import records begin proposed before
accepted local review.

OCR/import processing does not silently establish source, observer, verbatim
quotation, firsthand status, Participant target, finding, or active
`reported_involved` Role.

Core remains authoritative for PDS2 routing and retained source-scan provenance.

## Representative examples

`docs/examples/portia-account-and-observation-examples.md` documents the required
20-example minimum, backed by synthetic fixtures.

## Acceptance commands

```powershell
python -m unittest `
  tests.schema_validation.test_issue_15_account_observation_primitives `
  tests.schema_validation.test_issue_15_account_contract `
  tests.schema_validation.test_issue_15_observation_contract `
  tests.schema_validation.test_issue_15_shared_lifecycle_correction_dependency `
  tests.schema_validation.test_issue_15_migration_removal_compatibility `
  tests.schema_validation.test_issue_15_operational_derived_privacy_compatibility
```

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"
```

```powershell
git diff --check
git status --short
```

## Remaining repository reconciliation

The contract work, fixtures, examples, matrices, and validation artifacts are
complete. One final navigation/documentation slice should reconcile:

```text
README.md
schemas/README.md
```

with ADR 0011 and the accepted contracts, then rerun the full suite and final
branch-vs-main comparison.

No additional Account/Observation wire shape is expected.
