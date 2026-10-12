# Issue #56 Slice 7 — Capture Proposal Runtime Promotion

Slice 7 promotes the accepted `capture_proposal@1` contract unchanged:

```text
capture_proposal@1 → current_v0_3 / modelled=true
```

Capture Proposal remains an immutable, noncanonical, pre-review mapping artifact.
It references exact Paper Interpretation fields and an exact target contract/context;
it does not copy candidate OCR/mark values and does not authorize canonical writes.

The accepted target contexts remain `new_work`, `existing_work`, and
`existing_record`. `new_work` remains structurally limited to Event or Support
Process. Exact existing-context resolution, target-path validation, logical-path
deduplication, replay idempotency, and review/materialization remain later
application/service responsibilities.

Capture Review, Capture Materialization, and every import contract remain deferred.
Expected runtime-model count after this slice: **77**.
