# Issue #22 End-to-End Validation

**Issue:** #22 — Build representative end-to-end synthetic contract examples
**Date:** 2026-08-17
**Status:** Final validation evidence; PR-review traceability repair requires the same final gates to remain green

## Purpose

This document is the required end-to-end validation record for Issue #22. It
collects the authoritative execution evidence for the representative synthetic
contract corpus and separates:

```text
pristine starting baseline
focused scenario/closeout validation
Issue #22 regression
complete repository schema-validation regression
repository hygiene
```

from the semantic coverage documents themselves.

The corpus remains development/test-only, synthetic, deterministic, and
network-independent. This validation record is not a production-readiness,
legal/compliance, or sibling-runtime certification.

## Repository anchor

Issue #22 began from and was implemented against:

```text
pds-portia/main
53be03d535d5e697b3a0fcfd962fc2c308b1710c
```

The final repository checkpoint records the complete Core/Vitrine/Quillan
anchor recheck and sibling-drift assessment.

## Pristine implementation-start baseline

A detached temporary worktree at the exact Portia starting commit was used so
the starting test count was measured rather than inferred from the later branch.

Command:

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"
```

Observed result:

```text
Ran 1095 tests in 177.297s

OK
```

This is the authoritative pristine starting baseline.

## Final positive-coverage audit

The final contract audit identified three public families that had not yet
appeared inside the positive corpus itself:

```text
classification@1
hypothesis@1
intervention@1
```

P22-15 added bounded positive coverage without altering the semantics of the
original required P22-01..P22-14 stories.

Focused P22-15 validation:

```text
Ran 17 tests in 2.119s

OK
```

At that stage:

```text
Issue #22 regression:       344 / 344 OK
complete schema validation: 1439 / 1439 OK
```

## Current Operation Journal / Lock normalization

P22-14 was then normalized from historical operation contracts to the current
catalog forms:

```text
operation_journal@2
operation_lock@2
operation_current_pointer@1
```

Focused P22-14 validation after normalization:

```text
Ran 33 tests in 2.166s

OK
```

The subsequent branch gates were:

```text
Issue #22 regression
Ran 345 tests in 73.038s
OK

complete schema-validation suite
Ran 1440 tests in 266.728s
OK

repeat complete schema-validation suite
Ran 1440 tests in 180.234s
OK
```

`git diff --check` was clean.

## Closeout evidence validation

After the closeout evidence package was applied, the focused closeout module
produced:

```text
Ran 11 tests in 0.661s

OK
```

A stale exact wording invariant in the initial checkpoint was then restored:
Issue #22 does not allocate ADR 0018.

The repaired corpus-foundation gate produced:

```text
Ran 12 tests in 1.507s

OK
```

The complete Issue #22 regression then produced:

```text
Ran 356 tests in 47.168s

OK
```

The final complete repository schema-validation suite produced:

```text
Ran 1451 tests in 211.912s

OK
```

Repository hygiene:

```powershell
git diff --check
git status --short
```

`git diff --check` emitted no output. `git status --short` showed only the
expected Issue #22 additions before commit.

## Corpus result

The validated corpus contains:

```text
15 positive scenarios       P22-01..P22-15
37 graph-invalid scenarios  G22-001..G22-037
52 total scenarios
0 planned positive scenarios
0 planned graph-invalid scenarios
```

Every graph-invalid scenario declares one stable primary `G22.*` finding and
an exact expected finding set. Public Portia records in graph-invalid scenarios
remain structurally valid; their declared failure is at the application/graph
layer.

## Current public-catalog coverage

The final coverage artifacts are:

```text
docs/validation/issue-22-contract-coverage-matrix.md
tests/fixtures/issue_22/contract-coverage.json
```

The JSON coverage manifest maps every current `schemas/schema-catalog.json`
contract key and cataloged version set to an Issue #22 disposition. The closeout
test compares the manifest against the live catalog so catalog drift cannot be
silently omitted.

Current mapping:

```text
161 / 161 public catalog contract families mapped
 50 positive_graph
 17 existing_focused_fixture_only
 94 not_applicable_with_rationale supporting schemas
```

Foreign/Core/sibling context remains outside the Portia public schema catalog
and is documented separately as context-only authority.

## Source-byte and representation evidence

Where Issue #22 claims exact bytes, digest, length, or immutable representation
identity, executable tests recompute the evidence rather than trusting fixture
labels. This includes, as applicable:

- P22-05 retained paper-source bytes;
- P22-06 structured-import source snapshots;
- P22-12 source/export representation fingerprints and output bytes;
- P22-13 source snapshots and derived metadata;
- P22-14 lock and preflight representation fingerprints.

## Public architecture delta

Issue #22 introduces no public contract change:

```text
published JSON Schema change: none
schemas/schema-catalog.json:  unchanged
new ADR:                      none
ADR 0018 allocation:          none
runtime implementation:       none
```

Fixture descriptors, graph-finding identifiers, noncanonical projection
expectations, synthetic contexts, and the contract-coverage manifest remain
test/development metadata.

## PR-review closeout repair

The final PR review found traceability/document-state defects rather than corpus
semantic defects:

1. this required end-to-end validation file was absent;
2. catalog coverage was documented but not mechanically checked against every
   live catalog contract;
3. several closeout documents still displayed pre-Slice-23 counts/status;
4. the representative walkthrough still labeled Issue #22/P22-14 as in progress.

The review repair adds this file, the machine-readable catalog mapping, stronger
assertions inside the existing 11-test closeout module, and final documentation
normalization. It does **not** alter public schemas, scenario semantics, graph
finding behavior, or runtime code.

Because the repair strengthens documentation/test traceability only and adds no
new test method, the expected final discovery counts remain:

```text
closeout focused gate:      11 tests
Issue #22 regression:      356 tests
complete schema validation: 1451 tests
```

Those gates must remain green on the repaired PR head before merge.

## Issue #23 handoff

Once the repaired PR head retains the gates above, Issue #22 is complete and
Issue #23 may consume:

- the 15 positive stories;
- all 37 graph-invalid cases;
- the exact-finding matrix;
- the machine-checked public-catalog coverage mapping;
- the initial/final repository checkpoints;
- this end-to-end validation record;
- the acceptance matrix;
- the dedicated Issue #23 handoff document.

Issue #23 remains responsible for final architecture approval; Issue #22 does
not declare the Portia foundation production-ready.


## Post-review repaired-head execution

The PR-review traceability repair was then applied and the repaired tree was
validated directly:

```text
closeout gate:             11 / 11 OK   (0.037s)
Issue #22 regression:    356 / 356 OK  (42.655s)
complete schema suite: 1451 / 1451 OK (233.551s)
```

`git diff --check` was clean. The only working-tree entries were the expected
review-repair documentation/test updates plus the new end-to-end validation and
contract-coverage artifacts. Informational LF-to-CRLF warnings from Git on
Windows do not represent diff-check failures.

These results are the authoritative final execution evidence for the repaired
pre-commit tree; earlier timings in this document remain historical checkpoints.
