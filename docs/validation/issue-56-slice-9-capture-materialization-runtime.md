# Issue #56 Slice 9 — Capture Materialization Runtime Promotion

Slice 9 promotes the accepted `capture_materialization@1` contract unchanged to
`current_v0_3 / modelled=true`.

Capture Materialization is an immutable operational receipt linking one exact
accepted Capture Review to one exact completed/reconciled Portia coordinated
operation and its exact canonical results. It is not a domain record, review
authority, transaction engine, queue row, or new persistence mechanism.

The receipt intentionally has no `cmat_` identifier. Its identity is the exact
Operation Journal reference plus exact review lineage. Runtime promotion does
not invent a standalone logical ID.

Existing Operation Journal, Operation Lock, preflight, write-set, commit-point,
readback, and recovery semantics remain authoritative. Retry/restart must reuse
or reconcile the stable operation intent; receipt absence after durable canonical
acceptance is a recoverable post-commit artifact and must not trigger duplicate
canonical creation.

This slice does not implement materialization services. Cross-record review
currency, operation-journal resolution, stable-intent derivation, canonical
write orchestration, paper provenance checks, duplicate-result resolution, or
recovery remain service/application responsibilities.

Expected modeled runtime count after this slice: `79`.

All import contracts remain deferred.
