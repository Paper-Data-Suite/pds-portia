# Issue #20 — Slice 7 Import Source and Replay Checkpoint

Date: 2026-08-14

## Scope validated

Slice 7 established the structured-import source-history foundation:

- `import_batch@1`;
- `import_source_record@1`;
- `portia_import_batch_id@1` (`ibat_`);
- `portia_import_source_record_id@1` (`isrc_`);
- exact import-source snapshot and mapping-profile identity;
- stable source-record key policy;
- replay/change classification rules;
- and explicit separation of import provenance from paper/PDS2 capture.

## User-reported repository validation

From the Issue #20 working branch after applying Slice 7:

```text
python -m unittest discover -s tests/schema_validation
...
Ran 961 tests in 124.468s

OK
```

`git diff --check` returned no diagnostics.

The reported working tree contained the expected cumulative Issue #20 additions through Slice 7 and the modified schema catalog; no unexpected tracked-file modification was reported.

## Accepted checkpoint

The Slice 7 import-source/replay contracts are therefore the input boundary for Slice 8.

The next layer may rely on these accepted meanings:

```text
Import Batch
→ 0..N Import Source Records
→ 0..N proposals per source record
```

but must continue to preserve:

```text
Import Source Record ≠ Portia canonical record
source-system assertion ≠ Portia judgment
same source key + changed content = preserved new history
missing later source record ≠ deletion
same exact source + same mapping replay ≠ duplicate downstream records
```

## Deferred from this checkpoint

Slice 7 intentionally did not define:

- import-specific proposal identity/content;
- import-specific human review;
- import canonical materialization/receipt;
- import failure/integrity queue surfaces;
- final ADR/acceptance matrices/examples/README reconciliation.
