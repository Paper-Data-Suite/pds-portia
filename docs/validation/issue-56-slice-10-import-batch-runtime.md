# Issue #56 Slice 10 — Import Batch Runtime Promotion

Slice 10 begins the structured-import runtime path by promoting the accepted
`import_batch@1` contract unchanged to `current_v0_3 / modelled=true`.

Import Batch remains an operational import-attempt root. It is not Capture
Batch, paper/PDS2 routing state, or behavior-domain work.

The runtime preserves:

- exact class scope and `ibat_` batch identity;
- exact source-system/profile identity;
- exact import-specific source snapshot locator and fingerprint;
- exact mapping profile/version/digest;
- stable import identity digest;
- optional exact previous-batch comparison;
- lifecycle status/failure/timestamps.

The import-specific `source_snapshot` member is intentionally distinct from
Portia `source_snapshot@1`, whose established meaning is a deterministic
derived-generation source inventory.

Application/service responsibilities remain deferred, including recomputation
of import identity digests, exact prior-batch comparison, replay reconciliation,
source/profile resolution, fuzzy-identity prohibition, and downstream proposal/
review/materialization behavior.

Expected modeled runtime count after this slice: `80`.

Still deferred:

```text
import_source_record@1
import_proposal@1
import_review@1
import_materialization@1
```

The installed-wheel smoke preflights the candidate wheel payload before isolated
installation so stale `dist` output fails explicitly.
