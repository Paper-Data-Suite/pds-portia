# Issue #56 Slice 1 — Reconciliation Baseline Validation

## Scope

Slice 1 records and mechanically protects the exact starting gap between:

```text
accepted Issue #20 / ADR 0016 paper-import contracts
and
released Portia v0.2.0 runtime support
```

It intentionally makes no production capture/import behavior current.

## Exact branch baseline

The applying script requires:

```text
branch:
56-reconcile-paper-import-contracts-v02-runtime

HEAD:
7794b577ab6da444a501efb198895f9e4ff5726c

tree:
3da71310deb3cfb1f3bf05136909e6d660527b6d
```

and a clean working tree before writing Slice 1.

## Mechanical baseline checks

The focused validator confirms:

1. the durable v0.2.0 release audit still records the exact verified release;
2. Core 0.6.5 remains the current release qualification authority;
3. all 12 accepted capture/import record contracts exist in the schema catalog;
4. all 12 remain exactly `deferred_v0_3` and `modelled=false`;
5. the five generic PDS2/retained-source contract families remain Core-owned;
6. `page_target@1` still has the accepted v1 closed purpose vocabulary;
7. first-class Classroom Observation / monitoring / communication purposes are
   not silently present in v1;
8. `capture_batch@1` still lacks structured lesson/session context;
9. `observation@2` still permits only Event or Support Process ownership and
   retains the no-fake-Event invariant;
10. `capture_review@1` still exposes the exact accepted v1 dispositions and
    field-review decisions;
11. ADR 0016 remains accepted and retains the proposal/fact separation.

These are characterization assertions, not claims that the starting design is
the final v0.3 design.

## Focused validation

Run:

```powershell
python scripts/validate_issue56_reconciliation_baseline.py

python -m pytest -q `
  tests/test_issue56_reconciliation_baseline.py

python -m ruff check `
  scripts/validate_issue56_reconciliation_baseline.py `
  tests/test_issue56_reconciliation_baseline.py

python -m mypy `
  scripts/validate_issue56_reconciliation_baseline.py

git diff --check
```

Expected validator terminal result:

```text
Portia Issue #56 Slice 1 reconciliation baseline validation passed
```

## Recommended baseline regression

After focused validation, run:

```powershell
python scripts/validate_runtime_models.py

python -m pytest -q `
  tests/test_runtime_models.py `
  tests/test_issue56_reconciliation_baseline.py
```

Slice 1 should not change the Issue #37 runtime-model validator result because no
capture/import contract has yet been promoted into runtime support.

## Boundary

A passing Slice 1 proves the repository's exact starting state is known and
guarded.

It does **not** prove:

```text
capture_batch@1 is the final v0.3 runtime contract
page_target@1 is sufficient for v0.3 forms
observation@2 is sufficient for standalone classroom observation
capture_review@1 is sufficient for split/defer/rescan workflows
any capture/import service exists
any paper/import record may be materialized
```

Those are later Issue #56 reconciliation decisions.
