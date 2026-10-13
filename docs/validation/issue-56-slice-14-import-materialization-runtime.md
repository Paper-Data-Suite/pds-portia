# Issue #56 Slice 14 — Import Materialization Runtime Promotion

Slice 14 promotes the accepted `import_materialization@1` contract unchanged to
`current_v0_3 / modelled=true`.

Import Materialization remains an immutable operational post-commit receipt. It
links exact accepted import lineage to one exact completed/reconciled Operation
Journal revision and exact canonical results. It is not a domain record, review
authority, source snapshot, transaction engine, or mutable queue.

No `imat_` identifier exists. `import_materialization` is intentionally absent
from `IDENTITY_FIELDS`, and its runtime `logical_id` remains `None`.

The existing Operation Journal / Operation Lock machinery remains authoritative
for stable operation identity, locking, preflight, expected-prior-state checks,
staged writes, commit points, recovery, reconciliation, and exceptional
Quarantine. A missing receipt after durable canonical acceptance is reconciled
without replaying canonical creation.

The receipt preserves exact Import Batch, Import Source Record, Import Proposal,
Import Review, Operation Journal, and canonical-result references without
copying source payloads, transformed candidates, confirmed values, or canonical
payloads.

Expected modeled runtime count after this slice: `84`.

No Issue #56 paper/import operational contract remains `deferred_v0_3` after
this promotion.

After source qualification, the completed five-stage import runtime chain gets
one fresh package build and isolated installed-wheel acceptance against the
authenticated Core 0.6.5 wheel.
