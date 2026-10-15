# Issue #56 Slice 6 — Paper Interpretation Runtime Promotion

## Scope

Slice 6 promotes the accepted `paper_interpretation@1` contract into the
Portia v0.3 executable runtime without changing its public schema.

```text
paper_interpretation@1 → current_v0_3 / modelled=true
```

Previously promoted paper contracts remain:

```text
capture_batch@1 → current_v0_3
page_target@1 → historical_read
page_target@2 → current_v0_3
page_record@1 → current_v0_3
```

Capture Proposal, Capture Review, Capture Materialization, and every import
contract remain deferred.

## Semantic boundary

Paper Interpretation is immutable operational staging data for one interpretation
generation of one returned Page Record. It is not human review, accepted
evidence, source truth, identity/authorship confirmation, a behavior-domain
judgment, or authorization to materialize a canonical record.

Local runtime parsing validates the public wire representation only. Cross-record
exactness, generation replay/idempotency, and historical lineage resolution
remain application/service work.

## Preserved uncertainty semantics

```text
blank ≠ false/no/absent
unmarked ≠ false/no/declined
unreadable ≠ blank
ambiguous ≠ resolved
candidate_detected ≠ human-confirmed value
confidence ≠ truth
mapped_record_kind ≠ authorization to create that record family
```

`interpretation_status=complete` means configured historical regions were
processed. It does not mean values are correct, reviewed, or accepted.

## Focused validation

```powershell
python scripts/validate_issue56_paper_interpretation_runtime.py

python -m pytest -q `
  tests/test_issue56_paper_interpretation_runtime.py `
  tests/test_issue56_page_record_runtime.py `
  tests/test_issue56_capture_batch_runtime.py `
  tests/test_issue56_page_target_runtime.py `
  tests/test_issue56_reconciliation_baseline.py `
  tests/test_issue56_classroom_capture_decision.py `
  tests/test_runtime_models.py

python -m ruff check `
  portia/models/base.py `
  portia/models/records.py `
  portia/models/__init__.py `
  scripts/validate_issue56_paper_interpretation_runtime.py `
  scripts/smoke_test_issue56_paper_interpretation_runtime_wheel.py `
  scripts/validate_issue56_page_target_runtime.py `
  tests/test_issue56_paper_interpretation_runtime.py `
  tests/test_runtime_models.py

python -m mypy `
  scripts/validate_issue56_paper_interpretation_runtime.py `
  scripts/smoke_test_issue56_paper_interpretation_runtime_wheel.py

python scripts/validate_runtime_models.py
git diff --check
```

Expected runtime-model result:

```text
Portia Issue #37 runtime-model validation passed: 76 modelled contract versions
```

## Package / installed acceptance

```powershell
Remove-Item dist, build, pds_portia.egg-info `
  -Recurse -Force -ErrorAction SilentlyContinue

python -m build
python -m twine check dist/*
python scripts/check_package.py dist
```

Then:

```powershell
python scripts/smoke_test_issue56_paper_interpretation_runtime_wheel.py `
  dist/pds_portia-0.2.0-py3-none-any.whl `
  <authenticated-pds_core-0.6.5-wheel>
```

Expected:

```text
Portia Issue #56 Slice 6 installed Paper Interpretation runtime acceptance passed
```

## Non-goals

Slice 6 does not implement the interpretation engine, generation persistence,
Page Target/Page Record resolution, Capture Proposal, Capture Review,
Capture Materialization, canonical writes, or structured imports.
