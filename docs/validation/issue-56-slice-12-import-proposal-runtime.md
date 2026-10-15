# Issue #56 Slice 12 — Import Proposal Runtime Promotion

Slice 12 promotes the accepted `import_proposal@1` contract unchanged to
`current_v0_3 / modelled=true`.

Import Proposal remains immutable, noncanonical mapping-stage history. It does
not create a Portia domain record, establish person identity, or turn a
source-system label into Portia judgment.

Source values are referenced rather than copied where possible; transformed
values remain candidates; and `human_resolution_required` supplies no implied
value. `new_work` remains restricted to Event or Support Process roots.

This slice does not implement lineage resolution, digest recomputation, replay
reconciliation, identity resolution, judgment semantics, human review,
canonical writes, or materialization.

Expected modeled runtime count after this slice: `82`.

Still deferred:

```text
import_review@1
import_materialization@1
```

Qualification for this slice is source-only. Installed-wheel qualification is
deferred to the completed import-chain checkpoint unless packaging behavior
changes.
