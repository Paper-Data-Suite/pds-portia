# Issue #20 Slice 6 — Materialization / Recovery Checkpoint

Date observed: 2026-08-14

## User-reported validation

The user applied `pds-portia-issue-20-slice-6-materialization-recovery.zip`, applied the Slice 6 schema-catalog patch, and ran:

```text
python -m unittest discover -s tests/schema_validation

git diff --check
git status --short
```

Observed schema-validation result:

```text
Ran 943 tests in 175.395s

OK
```

`git diff --check` produced no output.

Observed working-tree status:

```text
 M schemas/schema-catalog.json
?? docs/design/portia-paper-assisted-capture-pds2-routing-and-import.md
?? docs/design/portia-paper-interpretation-staging.md
?? docs/design/portia-paper-materialization-and-recovery.md
?? docs/design/portia-paper-preallocation-matrix.md
?? docs/design/portia-paper-proposal-and-human-review.md
?? docs/validation/issue-20-initial-repository-checkpoint.md
?? docs/validation/issue-20-slice-2-capture-foundations-checkpoint.md
?? docs/validation/issue-20-slice-3-preprint-semantics-checkpoint.md
?? docs/validation/issue-20-slice-4-paper-interpretation-checkpoint.md
?? docs/validation/issue-20-slice-5-proposal-human-review-checkpoint.md
?? schemas/v1/capture/
?? schemas/v1/identifiers/portia-capture-batch-id.schema.json
?? schemas/v1/identifiers/portia-capture-proposal-id.schema.json
?? schemas/v1/identifiers/portia-capture-review-id.schema.json
?? schemas/v1/identifiers/portia-page-record-id.schema.json
?? schemas/v1/identifiers/portia-page-target-id.schema.json
?? schemas/v1/identifiers/portia-paper-interpretation-id.schema.json
?? tests/schema_validation/test_issue_20_capture_contracts.py
?? tests/schema_validation/test_issue_20_capture_materialization_contract.py
?? tests/schema_validation/test_issue_20_capture_proposal_review_contract.py
?? tests/schema_validation/test_issue_20_paper_interpretation_contract.py
```

This is the expected Issue #20 working surface through Slice 6.

## Slice 6 checkpoint conclusion

The paper-assisted path now has a clean schema-validation checkpoint through:

```text
Capture Batch
→ Page Target
→ Core route / retained source
→ Page Record
→ Paper Interpretation
→ Capture Proposal
→ attributable Capture Review
→ coordinated canonical materialization / recovery receipt
```

The next bounded design area is structured import source identity and replay semantics. It must remain separate from the paper/PDS2 path and must not reuse paper-specific capture lineage contracts.
