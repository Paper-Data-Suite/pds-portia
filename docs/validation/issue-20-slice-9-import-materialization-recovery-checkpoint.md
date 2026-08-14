# Issue #20 Slice 9 Checkpoint — Import Materialization and Recovery

Date: 2026-08-14

## Observed user validation

The user applied Slice 9 and ran:

```text
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

Observed result:

```text
Ran 994 tests in 136.234s

OK
```

`git diff --check` produced no output.

The reported working tree contained the expected accumulated Issue #20 design,
validation, capture/import schema, identifier, and focused schema-test files,
with `schemas/schema-catalog.json` modified by the cumulative catalog patches.

## Accepted Slice 9 boundary

Slice 9 completed the first safe import materialization path:

```text
Import Batch
→ Import Source Record
→ Import Proposal
→ attributable Import Review
→ coordinated Operation Journal / locks
→ canonical acceptance
→ immutable Import Materialization receipt
```

The receipt binds exact batch, source-record, proposal, review, operation-journal,
and canonical-result identity. Ordinary replay must reconcile the stable operation
and historical import identity instead of creating duplicate canonical records.

## Deferred from Slice 9

The following Issue #20 closeout work remained intentionally deferred:

- cross-path failure and recovery matrix;
- application-invalid matrix;
- explicit Integrity Finding versus ordinary review/retry versus Quarantine rules;
- lifecycle/correction matrix for all Issue #20 persistent families;
- synthetic fixture/example inventory and the required example floor;
- ADR 0016 and pre-ADR/final drift checks;
- README/schema-guide reconciliation;
- final acceptance matrix, schema inventory, anchor/test-count closeout.
