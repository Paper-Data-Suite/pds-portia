# Issue #56 Slice 4 — Capture Batch Runtime Promotion

## Scope

Slice 4 promotes the already-accepted `capture_batch@1` contract into the
Portia v0.3 executable runtime without changing its public schema.

```text
capture_batch@1 → current_v0_3 / modelled=true
page_target@1   → historical_read / modelled=true
page_target@2   → current_v0_3 / modelled=true
```

All remaining paper/import families stay deferred.

Capture Batch remains a non-domain operational work root. Promoting it into the
runtime does not add `capture_batch` to `portia_work_ref@1`, which remains
limited to `event` and `support_process`.

## Focused validation

```powershell
python scripts/validate_issue56_capture_batch_runtime.py

python -m pytest -q `
  tests/test_issue56_capture_batch_runtime.py `
  tests/test_issue56_page_target_runtime.py `
  tests/test_issue56_reconciliation_baseline.py `
  tests/test_issue56_classroom_capture_decision.py `
  tests/test_runtime_models.py

python -m ruff check `
  portia/models/base.py `
  portia/models/records.py `
  portia/models/__init__.py `
  scripts/validate_issue56_capture_batch_runtime.py `
  scripts/smoke_test_issue56_capture_batch_runtime_wheel.py `
  tests/test_issue56_capture_batch_runtime.py

python -m mypy `
  scripts/validate_issue56_capture_batch_runtime.py `
  scripts/smoke_test_issue56_capture_batch_runtime_wheel.py

python scripts/validate_runtime_models.py
git diff --check
```

Expected:

```text
Portia Issue #56 Slice 4 Capture Batch runtime validation passed
Portia Issue #37 runtime-model validation passed: 74 modelled contract versions
```

## Build / installed acceptance

```powershell
Remove-Item dist, build, pds_portia.egg-info `
  -Recurse -Force -ErrorAction SilentlyContinue

python -m build
python -m twine check dist/*
python scripts/check_package.py dist
```

Then run the isolated installed-wheel smoke against the authenticated Core 0.6.5
wheel:

```powershell
python scripts/smoke_test_issue56_capture_batch_runtime_wheel.py `
  dist/pds_portia-0.2.0-py3-none-any.whl `
  <authenticated-pds_core-0.6.5-wheel>
```

Expected:

```text
Portia Issue #56 Slice 4 installed Capture Batch runtime acceptance passed
```

## Boundary

This slice does not implement Capture Batch persistence/lifecycle services,
Page Target services, Core RouteRegistration creation, form rendering, returned
source intake, Page Record, interpretation/proposal/review/materialization, or
structured import.
