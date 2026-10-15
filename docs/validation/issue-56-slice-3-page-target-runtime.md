# Issue #56 Slice 3 — Page Target Runtime Promotion

## Scope

Slice 3 promotes the reconciled Page Target contracts into Portia's executable
runtime while preserving every other paper/import family as deferred.

```text
page_target@1 → historical_read / modelled=true
page_target@2 → current_v0_3 / modelled=true
```

This slice also adds `current_v0_3` to the runtime-coverage vocabulary, exports
immutable `PageTargetV1` / `PageTargetV2` runtime classes, regenerates the
compiled runtime contract bundle, and enforces the v2 application rule that
`entry_layout.context_entry_key` must name a declared `entry_key`.

No Capture Batch, Page Record, Interpretation, Proposal, Review,
Materialization, or Import family is promoted here.

## Focused validation

```powershell
python scripts/validate_issue56_page_target_runtime.py

python -m pytest -q `
  tests/test_issue56_page_target_runtime.py `
  tests/test_issue56_reconciliation_baseline.py `
  tests/test_issue56_classroom_capture_decision.py `
  tests/test_runtime_models.py

python -m ruff check `
  portia/models/base.py `
  portia/models/coverage.py `
  portia/models/records.py `
  portia/models/__init__.py `
  portia/_bundle_builder.py `
  scripts/validate_issue56_page_target_runtime.py `
  scripts/smoke_test_issue56_page_target_runtime_wheel.py `
  tests/test_issue56_page_target_runtime.py

python -m mypy `
  scripts/validate_issue56_page_target_runtime.py `
  scripts/smoke_test_issue56_page_target_runtime_wheel.py

python scripts/validate_runtime_models.py
git diff --check
```

Expected:

```text
Portia Issue #56 Slice 3 Page Target runtime validation passed
Portia Issue #37 runtime-model validation passed: 73 modelled contract versions
```

## Build and installed acceptance

Because this slice changes packaged runtime models and the bundled schema
closure, build and test the candidate wheel before commit:

```powershell
Remove-Item dist, build, pds_portia.egg-info `
  -Recurse -Force -ErrorAction SilentlyContinue

python -m build
python -m twine check dist/*
python scripts/check_package.py dist
```

Then:

```powershell
python scripts/smoke_test_issue56_page_target_runtime_wheel.py `
  dist/pds_portia-0.2.0-py3-none-any.whl `
  <authenticated-pds_core-0.6.5-wheel>
```

Expected:

```text
Portia Issue #56 Slice 3 installed Page Target runtime acceptance passed
```

The development branch still carries distribution version `0.2.0`; this does
not republish or alter the immutable v0.2.0 release.

## Boundary

This slice does not implement Page Target persistence, route registration, form
rendering, PDS2 generation, returned-page intake, OCR, review, materialization,
or structured import.
