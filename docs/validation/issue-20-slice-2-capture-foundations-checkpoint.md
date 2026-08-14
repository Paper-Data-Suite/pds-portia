# Issue #20 — Slice 2 Capture Foundations Checkpoint

Date: 2026-08-13

## Observed local validation

After applying Slice 2 plus the schema-catalog registration correction, the authoritative Portia schema-validation suite completed successfully:

```text
Ran 890 tests in 97.443s

OK
```

`git diff --check` produced no output.

Observed working-tree status at the checkpoint:

```text
 M schemas/schema-catalog.json
?? docs/design/portia-paper-assisted-capture-pds2-routing-and-import.md
?? docs/validation/issue-20-initial-repository-checkpoint.md
?? schemas/v1/capture/
?? schemas/v1/identifiers/portia-capture-batch-id.schema.json
?? schemas/v1/identifiers/portia-page-record-id.schema.json
?? schemas/v1/identifiers/portia-page-target-id.schema.json
?? tests/schema_validation/test_issue_20_capture_contracts.py
```

This confirms the Slice 2 public schema inventory is catalog-complete and that the Capture Batch, Page Target, Page Record, and three opaque identifier schemas integrate with the existing offline schema registry without regression.

## Scope still deferred after this checkpoint

Slice 2 did not yet complete:

- durable Page Target template/layout/purpose semantics;
- registration-before-render application invariants;
- per-family paper preallocation policy;
- returned-page interpretation generations;
- machine candidates and source uncertainty;
- capture proposals and attributable human review;
- canonical materialization;
- import batches/source records/idempotency;
- ADR 0016 and final acceptance matrices/documentation reconciliation.

Those remain Issue #20 work and are intentionally staged in later slices.
