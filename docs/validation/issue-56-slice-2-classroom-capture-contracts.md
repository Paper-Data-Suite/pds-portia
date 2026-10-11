# Issue #56 Slice 2 — Classroom Capture Contract Decision

## Scope

Slice 2 makes the first contract decisions after the Slice 1 reconciliation
baseline.

It:

```text
accepts ADR 0021
publishes page_target@2
catalogues page_target@2
records page_target@2 as deferred_v0_3 / modelled=false
preserves capture_batch@1
preserves observation@2 ownership
preserves page_target@1 unchanged
```

It does not yet add a Page Target runtime model or executable form-generation
service.

## Decisions mechanically guarded

The focused validator confirms:

1. ADR 0021 is accepted;
2. `page_target@1` retains its exact original purpose vocabulary;
3. `page_target@2` contains all v1 purposes plus:
   - `classroom_observation_capture`;
   - `focused_monitoring_capture`;
   - `communication_capture`;
4. v2 adds `entry_layout.context_entry_key`;
5. a Classroom Observation target requires multi-entry layout plus a context
   entry and cannot prebind existing domain work;
6. Capture Batch remains v1-only and has no lesson/session value fields;
7. `observation@2` remains Event/Support-Process owned and keeps the no-fake-Event
   invariant;
8. no `observation@3` is introduced;
9. `page_target@2` is catalogued but remains explicitly deferred/unmodelled;
10. no runtime model-registry or compiled-bundle promotion occurs in this slice.

## Focused validation

Run:

```powershell
python scripts/validate_issue56_classroom_capture_decision.py

python -m pytest -q `
  tests/test_issue56_classroom_capture_decision.py `
  tests/schema_validation/test_issue_56_page_target_v2.py

python -m ruff check `
  scripts/validate_issue56_classroom_capture_decision.py `
  tests/test_issue56_classroom_capture_decision.py `
  tests/schema_validation/test_issue_56_page_target_v2.py

python -m mypy `
  scripts/validate_issue56_classroom_capture_decision.py

python scripts/validate_runtime_models.py

python -m pytest -q `
  tests/test_runtime_models.py `
  tests/test_issue56_reconciliation_baseline.py `
  tests/test_issue56_classroom_capture_decision.py

git diff --check
```

Expected focused validator terminal result:

```text
Portia Issue #56 Slice 2 classroom-capture contract decision validation passed
```

## Later runtime promotion

Slice 3 intentionally advances runtime support to:

```text
page_target@1 → historical_read / modelled=true
page_target@2 → current_v0_3 / modelled=true
```

The Slice 2 design decision itself is unchanged.

## Boundary

A passing Slice 2 does not mean `page_target@2` is executable runtime support.

The next runtime-promotion slice must add an immutable model, exact round-trip
validation, runtime bundle inclusion, and update the runtime-support disposition
deliberately.

Later Issue #56 slices must still reconcile:

```text
page-level source-context human confirmation
Capture Review split/defer/rescan semantics
multi-record capture proposal/materialization choreography
remaining capture contract runtime dispositions
import contract reconciliation
```
