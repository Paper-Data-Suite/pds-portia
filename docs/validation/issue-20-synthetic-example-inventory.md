# Issue #20 Synthetic Fixture and Example Inventory

All examples in this inventory are synthetic. They contain no real student, family, staff, behavior, support, or source-system data.

## Inventory summary

Slice 11 establishes **52 machine-checked synthetic examples**:

- 22 baseline-valid fixtures;
- 22 structural-invalid fixtures;
- 8 additional valid scenario fixtures.

This exceeds Issue #20's minimum requirement of 40 synthetic examples.

The machine-readable manifest is:

```text
tests/fixtures/issue_20/manifest.json
```

The fixture validator is:

```text
tests/schema_validation/test_issue_20_fixture_examples.py
```

## Per-contract baseline coverage

Every public schema introduced by Issue #20 has at least one valid and one structural-invalid fixture.

| Contract | Valid | Structural-invalid |
|---|---:|---:|
| `capture_batch@1` | 1 | 1 |
| `page_target@1` | 1 | 1 |
| `page_record@1` | 1 | 1 |
| `paper_interpretation@1` | 1 | 1 |
| `capture_proposal@1` | 1 | 1 |
| `capture_review@1` | 1 | 1 |
| `capture_materialization@1` | 1 | 1 |
| `import_batch@1` | 1 | 1 |
| `import_source_record@1` | 1 | 1 |
| `import_proposal@1` | 1 | 1 |
| `import_review@1` | 1 | 1 |
| `import_materialization@1` | 1 | 1 |
| `portia_capture_batch_id@1` | 1 | 1 |
| `portia_page_target_id@1` | 1 | 1 |
| `portia_page_record_id@1` | 1 | 1 |
| `portia_paper_interpretation_id@1` | 1 | 1 |
| `portia_capture_proposal_id@1` | 1 | 1 |
| `portia_capture_review_id@1` | 1 | 1 |
| `portia_import_batch_id@1` | 1 | 1 |
| `portia_import_source_record_id@1` | 1 | 1 |
| `portia_import_proposal_id@1` | 1 | 1 |
| `portia_import_review_id@1` | 1 | 1 |

Baseline structural-invalid record examples deliberately violate the closed `record_type` discriminator. Identifier invalid fixtures use a conflicting Portia family prefix. These examples test structural rejection without attempting to encode application-invalid cross-record conditions as JSON Schema failures.

## Additional valid scenarios

The eight additional scenario fixtures exercise behavior that is important to Issue #20 but is not represented by a single minimal baseline fixture:

1. Page Target for an exact existing Event context.
2. Multi-entry Page Target with stable page-local entry keys.
3. Paper Interpretation preserving ambiguous handwriting alternatives without choosing a winner.
4. Capture Review using `corrected_and_accepted` with an explicit human-confirmed correction.
5. Completed Import Batch with explicit completion time.
6. Import Source Record using a profile-defined exact source key rather than row position.
7. Import Proposal mapping one source record to an Account in an exact existing Event.
8. Import Review using `corrected_and_accepted` while preserving the original source/mapping candidate history.

## What these examples do not prove

A structurally valid fixture does not prove cross-record or runtime application validity. In particular, fixtures do not by themselves prove:

- Core route registration or active route resolution;
- Page Target existence at routing time;
- retained-source identity or byte-fingerprint agreement;
- historical template availability;
- reviewer authorization;
- import source authority or truth;
- canonical write durability;
- Operation Journal/lock agreement;
- or semantic eligibility to activate a domain record.

Those remain application-validation responsibilities and are covered by the Issue #20 application-invalid and operational-failure matrices.
