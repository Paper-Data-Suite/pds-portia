# Issue #22 Initial Repository Checkpoint

**Issue:** #22 — Build representative end-to-end synthetic contract examples
**Branch:** `22-representative-end-to-end-synthetic-contract-examples`
**Implementation start:** 2026-08-15
**Baseline execution recovered:** 2026-08-17
**Status:** Complete

## Repository anchors at implementation start

The Issue #22 branch began exactly from the merged Issue #21 foundation:

```text
pds-portia
branch: 22-representative-end-to-end-synthetic-contract-examples
commit: 53be03d535d5e697b3a0fcfd962fc2c308b1710c

pds-portia/main
53be03d535d5e697b3a0fcfd962fc2c308b1710c

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-vitrine/main
c1dbe3700b1b0d897e44576497ba240be2a49ff1
fixture/validation precedent only

pds-quillan/main
3ae37eaaf89cf913020a5afc75bc11a68df0d5cc
context only where current producer/reference behavior is discussed
```

These are review checkpoints, not dependency pins.

## Pristine-main schema-validation baseline

The ticket requires the complete Portia schema-validation suite to be executed
against the implementation-start `main` state rather than inferred from a later
Issue #22 branch run.

The first Issue #22 slice originally recorded the start commit but deliberately
did not guess a pristine-main test count. During closeout, `pds-portia/main` was
reverified and was still exactly the starting commit, so the missing baseline was
recovered without altering the Issue #22 branch by creating a temporary detached
git worktree at:

```text
53be03d535d5e697b3a0fcfd962fc2c308b1710c
```

Observed command:

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"
```

Observed result on 2026-08-17:

```text
Ran 1095 tests in 177.297s

OK
```

This **1095-test run is the authoritative pristine starting baseline** for Issue
#22. Earlier larger counts recorded during implementation were cumulative branch
runs after Issue #22 fixtures/tests had already been added and are not relabeled
as pristine-main results.

## Structural-validation mechanism

Issue #22 reuses Portia's existing offline schema catalog and local JSON Schema
registry through:

```text
tests/schema_validation/schema_support.py
```

and the existing helpers:

```text
load_validated_catalog_and_store()
validator_for(contract_name, version, ...)
```

The corpus therefore does not create an independent schema-resolution mechanism.

## Public-contract expectation

The expected public-schema delta for Issue #22 is:

```text
none
```

Issue #22 composes and validates the accepted foundation. Corpus descriptors,
synthetic context contracts, derived/projection expectations, and `G22.*`
finding codes are development/test artifacts only and are not registered in
`schemas/schema-catalog.json`.

ADR 0018 is not allocated by Issue #22. No ADR is allocated by this issue. A
new ADR would be warranted only if the corpus exposed a genuinely new
architectural decision that could not be resolved under ADRs 0001–0017; the
completed corpus did not require one.

## Starting implementation boundary

The first slice established the versioned non-runtime corpus descriptor,
canonical-path and exact-reference validation, deterministic derived-summary
expectations, synthetic Core roster context, and P22-01. Later slices extend the
same harness rather than creating a parallel fixture format.
