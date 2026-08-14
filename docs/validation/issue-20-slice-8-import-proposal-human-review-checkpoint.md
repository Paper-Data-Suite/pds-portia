# Issue #20 Slice 8 Checkpoint — Import Proposal and Human Review

Date: 2026-08-14

## Observed user validation

After applying `pds-portia-issue-20-slice-8-import-proposal-human-review.zip` and its catalog patch, the user ran:

```powershell
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

Observed result:

```text
Ran 979 tests in 182.939s

OK
```

`git diff --check` emitted no errors.

The working tree contained the expected cumulative Issue #20 documentation, capture/import schemas, identifiers, focused tests, and modified `schemas/schema-catalog.json`. No unexpected tracked source modification was reported.

## Accepted checkpoint

Slice 8 is therefore accepted as a clean Issue #20 checkpoint:

- Import Source Record may yield 0..N stable proposals;
- Import Proposal preserves exact source/mapping lineage and candidate-vs-source separation;
- fuzzy person identity and source-label-to-Portia-judgment inference remain prohibited;
- Import Review is attributable to a substantive human;
- accepted / corrected-and-accepted / rejected / unresolved staging decisions are distinct;
- review corrections preserve source and transformed candidate history;
- accepted Import Review still does not itself create a canonical Portia record;
- import and paper staging remain distinct.

## Deferred to Slice 9

Slice 9 adds the crash-safe canonical materialization boundary for reviewed imports, reusing Portia's existing coordinated Operation Journal and lock infrastructure and preserving `creation_source.type = import` provenance.
