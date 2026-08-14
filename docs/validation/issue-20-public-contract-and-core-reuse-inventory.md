# Issue #20 Public Contract and Core-Reuse Inventory

This inventory is authoritative for ADR 0016 closeout.

## Public Issue #20 contracts

Issue #20 adds 22 public Portia contracts: 12 record contracts and 10 identifier
contracts.

### Paper capture records

| Contract | Path | Meaning |
|---|---|---|
| `capture_batch@1` | `schemas/v1/capture/capture-batch.schema.json` | non-domain paper-capture work root |
| `page_target@1` | `schemas/v1/capture/page-target.schema.json` | legitimate pre-print Portia route target |
| `page_record@1` | `schemas/v1/capture/page-record.schema.json` | one returned physical page intake |
| `paper_interpretation@1` | `schemas/v1/capture/paper-interpretation.schema.json` | immutable candidate interpretation generation |
| `capture_proposal@1` | `schemas/v1/capture/capture-proposal.schema.json` | mapped paper candidate proposed for review |
| `capture_review@1` | `schemas/v1/capture/capture-review.schema.json` | attributable operational human confirmation |
| `capture_materialization@1` | `schemas/v1/capture/capture-materialization.schema.json` | accepted-review → canonical operation receipt |

### Structured import records

| Contract | Path | Meaning |
|---|---|---|
| `import_batch@1` | `schemas/v1/imports/import-batch.schema.json` | bounded import attempt against exact source snapshot/mapping |
| `import_source_record@1` | `schemas/v1/imports/import-source-record.schema.json` | one source-side unit, not a Portia Event |
| `import_proposal@1` | `schemas/v1/imports/import-proposal.schema.json` | one mapping-local reviewable proposal |
| `import_review@1` | `schemas/v1/imports/import-review.schema.json` | attributable import confirmation/correction/rejection |
| `import_materialization@1` | `schemas/v1/imports/import-materialization.schema.json` | accepted import review → canonical operation receipt |

### Identifier contracts

| Contract | Prefix | Path |
|---|---|---|
| `portia_capture_batch_id@1` | `cbat_` | `schemas/v1/identifiers/portia-capture-batch-id.schema.json` |
| `portia_page_target_id@1` | `ptgt_` | `schemas/v1/identifiers/portia-page-target-id.schema.json` |
| `portia_page_record_id@1` | `prec_` | `schemas/v1/identifiers/portia-page-record-id.schema.json` |
| `portia_paper_interpretation_id@1` | `pint_` | `schemas/v1/identifiers/portia-paper-interpretation-id.schema.json` |
| `portia_capture_proposal_id@1` | `cprp_` | `schemas/v1/identifiers/portia-capture-proposal-id.schema.json` |
| `portia_capture_review_id@1` | `crev_` | `schemas/v1/identifiers/portia-capture-review-id.schema.json` |
| `portia_import_batch_id@1` | `ibat_` | `schemas/v1/identifiers/portia-import-batch-id.schema.json` |
| `portia_import_source_record_id@1` | `isrc_` | `schemas/v1/identifiers/portia-import-source-record-id.schema.json` |
| `portia_import_proposal_id@1` | `iprp_` | `schemas/v1/identifiers/portia-import-proposal-id.schema.json` |
| `portia_import_review_id@1` | `irev_` | `schemas/v1/identifiers/portia-import-review-id.schema.json` |

Materialization intentionally reuses existing `portia_operation_id@1` / `op_`
identity and does not introduce paper/import materialization IDs.

## Existing Portia contracts reused without semantic broadening

Issue #20 reuses, rather than replaces or mutates, existing contracts including:

```text
creation_source@1
source_artifact_ref@1

exact_portia_work_ref@1
exact_portia_work_record_ref@1
exact_local_record_ref@1
operation_journal_ref@1
operation_ref@1

attribution_agent@1
represented_human_attribution@1

operation_journal
operation_lock
quarantine_record
integrity_finding

common sha256/content fingerprint/timestamp/path/text primitives
```

`portia_work_ref@1` and `exact_portia_work_ref@1` remain canonical Event/Support
Process references. Capture Batch is not added as a third domain work kind.

The existing derived `source_snapshot@1` meaning is not repurposed as import
source authority.

## Core contracts and services reused

Core remains authoritative for generic PDS2 transport/provenance:

```text
ModuleWorkRef
RouteLocator
ModuleRecordRef
RouteRegistration
RouteResolution
RetainedSourceScan
retain-first scan preservation
page-by-page module dispatch
```

Portia consumes Core identities/provenance and must not publish competing
generic route or retained-source contracts.

Core's retained-source identity remains distinct from:

```text
source page number
Portia Page Record
Portia interpretation generation
Portia proposal/review
canonical Portia domain record
```

## Sibling precedents and boundaries

### Quillan

Reused as precedent only for:

- retain-first intake;
- preservation after downstream failure;
- terminal handling per physical page.

Quillan remains owner of long-form written-response processing.

### ScoreForm

Reviewed as mechanical precedent only for mark recognition/OMR.

ScoreForm remains owner of academic selected-response scoring.

### Meridian

Issue #20 does not create Grades, standards ratings, academic-result
publication, or automatic Meridian ingestion.

### Vitrine

Issue #20 does not publish paper/import results automatically to portfolios.

## Public-schema count

```text
12 record contracts
10 identifier contracts
22 public Issue #20 contracts total
```

## Fixture coverage

Slice 11 provides:

```text
22 valid baseline fixtures
22 structural-invalid fixtures
8 richer valid scenarios
52 synthetic examples total
```

Each public Issue #20 contract is represented by both a valid and
structural-invalid fixture.
