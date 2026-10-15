# Issue #56 Slice 13 — Import Review Runtime Promotion

Slice 13 promotes the accepted `import_review@1` contract unchanged to
`current_v0_3 / modelled=true`.

Import Review remains immutable operational staging review rather than the
canonical Portia `review@1` domain family. The substantive reviewer is a
represented human; `created_by` remains persistence attribution.

The runtime preserves exact batch/source/proposal lineage, opaque `irev_`
identity, immutable review sequence/predecessor history, reviewer attribution,
disposition, field-level decisions/corrections, reason codes, and timestamps.

`accepted` and `corrected_and_accepted` mean only that the exact staging mapping
may proceed to a later materialization gate. They do not establish source truth,
identity, domain judgment, authority, credibility, fault, causation, consent, or
canonical mutation. `unresolved` carries no negative/false/no meaning, and
`rejected` is not deletion.

No mutable current/latest review pointer is introduced; current staging status
is derived from immutable history.

This slice does not implement reviewer authorization, cross-record lineage
resolution, target-path matching, sequence/fork/cycle validation, domain
judgment, canonical persistence, or materialization.

Expected modeled runtime count after this slice: `83`.

Still deferred:

```text
import_materialization@1
```

Qualification is source-only. Full package/installed-wheel qualification is
reserved for the completed import-chain integration checkpoint.
