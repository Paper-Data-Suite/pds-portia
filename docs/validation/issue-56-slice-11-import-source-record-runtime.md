# Issue #56 Slice 11 — Import Source Record Runtime Promotion

Slice 11 promotes the accepted `import_source_record@1` contract unchanged to
`current_v0_3 / modelled=true`.

Import Source Record remains immutable, noncanonical source-side history inside
one exact Import Batch. It preserves exact `ibat_` lineage, Portia-local `isrc_`
identity, stable source-key origin/value, content and identity digests, bounded
normalized scalar/array source fields, explicit null values, source observation
time, and attribution.

Row order, array position, display text, filename alone, fuzzy identity, and
import order remain prohibited identity inputs. Changed source content preserves
later history. A missing record in a later Import Batch is not deletion,
deactivation, invalidation, or supersession.

This slice does not implement source-profile resolution, digest recomputation,
replay services, identity resolution, proposal generation, review, or
materialization.

Expected modeled runtime count after this slice: `81`.

Still deferred:

```text
import_proposal@1
import_review@1
import_materialization@1
```
