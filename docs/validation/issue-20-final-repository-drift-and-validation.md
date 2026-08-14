# Issue #20 Final Repository Drift and Validation Record

Date: 2026-08-14

Issue:

```text
#20 — Define paper-assisted capture, PDS2 routing, and import contracts
```

ADR:

```text
ADR 0016 — Accepted
```

## Final implementation scope

Issue #20 publishes:

```text
12 record contracts
10 identifier contracts
22 public contracts total
```

Paper path:

```text
Capture Batch
→ Page Target
→ Core RouteRegistration / QR
→ Core retain-first intake / dispatch
→ Page Record
→ Paper Interpretation
→ Capture Proposal
→ attributable Capture Review
→ coordinated canonical materialization
```

Import path:

```text
exact source snapshot
→ Import Batch
→ Import Source Record
→ 0..N Import Proposals
→ attributable Import Review
→ coordinated canonical materialization
```

Materialization on both paths reuses the existing Portia coordinated-operation
identity, Operation Journal, and Operation Lock infrastructure.

## Final repository drift

The final closeout drift check found:

```text
pds-portia/main
c69533fa980cf41aa92c52978617e170263f6135

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
b03ffad0749db0dce47e68f095a8d477fa69eb2d

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede
```

Relative to the Issue #20 starting checkpoints:

- Portia: unchanged;
- Core: unchanged;
- ScoreForm: unchanged;
- Quillan: remains exactly one commit ahead at the same producer-profile commit
  already evaluated in the pre-ADR checkpoint.

No repository moved after ADR 0016's pre-ADR drift assessment.

The Quillan delta remains academic-publication/producer-profile integration and
does not alter the retain-first/per-physical-page paper-intake precedent used by
Issue #20.

Result:

> No final repository drift requires a contract, ADR, fixture, or
> application-invariant revision.

## Authoritative schema-validation result

Authoritative final implementation checkpoint supplied by the maintainer
after applying Slice 13:

```text
Ran 1020 tests in 130.205s

OK
```

`git diff --check`:

```text
(no output)
```

The final working tree contains only the expected accumulated Issue #20 changes.

Slice 13 changed only final validation/acceptance documentation and the
documentation-consistency expectation that verifies the acceptance matrix has
no pending rows. It did not add or modify a published schema wire shape.

## Validation progression

Authoritative user-run Issue #20 checkpoints:

```text
Slice 1:   880 tests — OK
Slice 2:   890 tests — OK
Slice 3:   899 tests — OK
Slice 4:   912 tests — OK
Slice 5:   929 tests — OK
Slice 6:   943 tests — OK
Slice 7:   961 tests — OK
Slice 8:   979 tests — OK
Slice 9:   994 tests — OK
Slice 10: 1009 tests — OK
Slice 11: 1013 tests — OK
Slice 12: 1020 tests — OK
Final post-Slice-13 verification: 1020 tests — OK
```

Every reported checkpoint also had a clean `git diff --check`.

## Synthetic examples

Issue #20 contains:

```text
22 baseline-valid fixtures
22 structural-invalid fixtures
8 richer valid scenarios
52 synthetic examples total
```

This exceeds the required 40-example minimum.

Every public Issue #20 contract has at least:

```text
1 valid fixture
1 structural-invalid fixture
```

Application-invalid cross-record/runtime conditions remain separately
documented rather than being falsely treated as JSON Schema facts.

## Public contract inventory

Paper records:

```text
capture_batch@1
page_target@1
page_record@1
paper_interpretation@1
capture_proposal@1
capture_review@1
capture_materialization@1
```

Import records:

```text
import_batch@1
import_source_record@1
import_proposal@1
import_review@1
import_materialization@1
```

Opaque identifiers:

```text
portia_capture_batch_id@1          cbat_
portia_page_target_id@1            ptgt_
portia_page_record_id@1            prec_
portia_paper_interpretation_id@1   pint_
portia_capture_proposal_id@1       cprp_
portia_capture_review_id@1         crev_
portia_import_batch_id@1           ibat_
portia_import_source_record_id@1   isrc_
portia_import_proposal_id@1        iprp_
portia_import_review_id@1          irev_
```

Materialization intentionally reuses existing `op_` coordinated-operation
identity.

## Core ownership preserved

Issue #20 does not replace Core:

```text
ModuleWorkRef
RouteLocator
ModuleRecordRef
RouteRegistration
RouteResolution
RetainedSourceScan
retain-first source preservation
generic page dispatch
```

Core remains authoritative for generic routing and retained-source history.
Portia owns Portia-specific page/import meaning and downstream human-reviewed
materialization.

## Safety boundaries preserved

Final closeout preserves:

```text
printed page ≠ domain Event
retained source ≠ accepted evidence
OCR/mark candidate ≠ confirmed value
blank/unreadable ≠ false/no
reprocessing ≠ new canonical record
Import Source Record ≠ Event
source assertion ≠ Portia judgment
missing later import row ≠ deletion
capture/import review ≠ canonical domain Review
capture/import confirmation ≠ Classification/Hypothesis/Determination/Outcome
ordinary review/retry ≠ Integrity Finding ≠ Quarantine
scan/import time ≠ domain time
exact historical source context ≠ silently retargeted successor context
```

Paper/import source bytes are not embedded in Portia JSON.

## Acceptance result

```text
82 criteria tracked
82 passed
0 pending
0 known implementation gaps
```

The authoritative acceptance matrix is:

```text
docs/validation/issue-20-acceptance-matrix.md
```

## Closeout conclusion

Issue #20's architecture, public contracts, fixtures, application-invalid
boundaries, failure/recovery rules, documentation reconciliation, and ADR are
complete.

No additional Issue #20 workflow contract is required before branch
commit/PR review.
