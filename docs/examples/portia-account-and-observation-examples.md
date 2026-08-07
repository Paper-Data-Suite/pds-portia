# Portia Account and Observation Examples

**Status:** Accepted synthetic examples
**Issue:** `#15 — Define Account and Observation domain models`
**ADR:** `0011 — Define Account and Observation Domain Models`
**Date:** 2026-08-07

These examples illustrate the accepted Account and Observation contracts. The
corresponding JSON fixtures are synthetic and are exercised by the Issue #15
schema-validation tests.

```text
Account
= what one represented source said

Observation
= what one human observer or instrument directly observed, counted, timed,
  recorded, or measured

Account / Observation
!= finding, credibility judgment, policy violation, diagnosis, intent, risk,
   severity, or behavioral interpretation
```

## Required representative set

| # | Example | Validated fixture |
| ---: | --- | --- |
| 1 | Firsthand roster-student Account | `tests/schema_validation/fixtures/issue-15/account/valid/minimum-active.json` |
| 2 | Actor Account | `tests/schema_validation/fixtures/issue-15/account/valid/actor-source-event-target.json` |
| 3 | Verbatim quotation plus recorder summary | `tests/schema_validation/fixtures/issue-15/account/valid/quote-and-summary.json` |
| 4 | Secondhand Account with known lineage | `tests/schema_validation/fixtures/issue-15/account/valid/secondhand-lineage.json` |
| 5 | Conflicting Accounts coexist | `account/valid/conflicting-account-a.json` + `conflicting-account-b.json` |
| 6 | Source-evidenced Account retraction | `account/retraction/valid/same-source-active-retraction.json` |
| 7 | Corrected Account successor | `account/valid/correction-successor.json` |
| 8 | Paper-derived proposed Account | `account/valid/paper-proposed.json` |
| 9 | Imported proposed Account | `account/valid/import-proposed.json` |
| 10 | Positive human Observation using neutral schema | `observation/valid/positive-narrative.json` |
| 11 | Neutral human Observation | `observation/valid/neutral-narrative.json` |
| 12 | Potentially concerning but purely observable Observation | `observation/valid/potentially-concerning-narrative.json` |
| 13 | Bounded Observation interval | `observation/valid/bounded-interval.json` |
| 14 | Instrumented duration Observation | `observation/valid/instrumented-duration.json` |
| 15 | Corrected Observation successor | `observation/valid/correction-successor.json` |
| 16 | Invalidated Observation retained historically | `observation/valid/invalidated-observation.json` |
| 17 | Active `reported_involved` Role with qualifying aligned Account | `account/role-compatibility/valid/aligned-singular.json` |
| 18 | Account with typed source-artifact provenance | `account/valid/paper-proposed.json` |
| 19 | Observation with typed sibling-PDS work-record source reference | `observation/valid/external-pds-record-artifact.json` |
| 20 | Statement of Disagreement targeting exact Account | `shared-lifecycle-correction-dependency/valid/disagreement-targets-account.json` |

## Boundary notes

The two conflicting Account fixtures intentionally make incompatible source
claims about the same contextual fact. Both remain valid canonical source
records. Portia does not merge them, choose a winner, calculate credibility, or
create a finding from the conflict.

The bounded Observation uses `evidence_time@1` with `precision = range`; record
creation time remains separate from observation time.

The invalidated Observation remains historically resolvable but is not eligible
for ordinary current use.

The typed sibling-PDS source reference uses `module_work_record_ref`. It is an
inert versioned locator for Portia semantics and does not establish
authorization, authenticity, credibility, or truth.

The `reported_involved` example demonstrates the stronger participant-alignment
rule: the active Account must target the same Participant or a Participant set
containing that Participant. An Event-wide Account is insufficient.

## Additional validated coverage

The fixture corpus also covers Participant-set targeting, unidentified proposed
Accounts, manual count and manual timing, percentage and `other_numeric`
measurements, artifact review, paper/import Observations, duplicate
consolidation, lifecycle-history correction, Dependency references,
representation-only migration, exceptional removal, exact operational
targeting, Quarantine, Integrity Findings, deterministic source snapshots,
immutable derived generations, explicit current pointers, and operational
privacy failures.

See:

```text
docs/validation/issue-15-application-invalid-matrix.json
docs/validation/issue-15-acceptance-matrix.json
docs/validation/issue-15-account-observation-validation.md
```
