# Issue #20 Acceptance Matrix

This matrix reconciles the Issue #20 acceptance surface against the implemented
Slice 2–12 architecture.

Status meaning:

- **Passed** — the criterion is implemented and supported by the final Issue #20
  contract, documentation, fixture, test, or repository-drift evidence.

| # | Area | Acceptance criterion | Status |
|---:|---|---|---|
| 1 | Core ownership | Core remains authoritative for generic PDS2 RouteLocator. | Passed |
| 2 | Core ownership | Core remains authoritative for RouteRegistration and RouteResolution. | Passed |
| 3 | Core ownership | Core remains authoritative for RetainedSourceScan and retained bytes. | Passed |
| 4 | Core ownership | Portia publishes no competing generic route/retained-source contract. | Passed |
| 5 | Capture work | Capture Batch solves Core work_id without a fabricated Event. | Passed |
| 6 | Capture work | Capture Batch is explicitly non-domain operational work. | Passed |
| 7 | Capture work | Existing portia_work_ref/exact_portia_work_ref remain Event/Support Process only. | Passed |
| 8 | Pre-print | Page Target exists before QR/PDS2 rendering. | Passed |
| 9 | Pre-print | Core RouteRegistration targets the exact Page Target. | Passed |
| 10 | Pre-print | Registration is verified before rendering/printing. | Passed |
| 11 | Pre-print | Page Target preserves exact template/layout/capture-spec identity. | Passed |
| 12 | Pre-print | Page Target supports exact existing Event/Support Process context. | Passed |
| 13 | Pre-print | Page purpose vocabulary is closed and descriptive. | Passed |
| 14 | Pre-print | QR/fallback routing content remains privacy-minimized by invariant. | Passed |
| 15 | Preallocation | Blank Event form does not pre-create Event. | Passed |
| 16 | Preallocation | Blank evidence form does not pre-create Account/Observation. | Passed |
| 17 | Preallocation | Printed support/fidelity/follow-up/reentry/repair forms do not manufacture completion/facts. | Passed |
| 18 | Preallocation | Existing legitimate records may be rendered. | Passed |
| 19 | Returned page | Page Record represents one physical retained-source page intake. | Passed |
| 20 | Returned page | Page Record preserves exact Core route and retained-source identity. | Passed |
| 21 | Returned page | Page Record does not embed raw source bytes. | Passed |
| 22 | Returned page | Same route + different retained source remains distinct. | Passed |
| 23 | Returned page | Same hash does not automatically collapse retained-source history. | Passed |
| 24 | Returned page | Multi-page scan adjacency/order is nonsemantic. | Passed |
| 25 | Interpretation | Paper Interpretation is immutable generation staging. | Passed |
| 26 | Interpretation | Same source + same interpreter/mapping replay is idempotent. | Passed |
| 27 | Interpretation | Changed interpreter/mapping creates preserved new generation. | Passed |
| 28 | Interpretation | Blank, unmarked, unreadable, ambiguous, and candidate states are distinct. | Passed |
| 29 | Interpretation | Candidate literal is preserved separately from normalization. | Passed |
| 30 | Interpretation | Ambiguous alternatives can be preserved without choosing a winner. | Passed |
| 31 | Interpretation | Confidence may prioritize review but cannot bypass it. | Passed |
| 32 | Interpretation | Mapped record kind comes only from exact mapping/template. | Passed |
| 33 | Interpretation | Machine interpretation does not infer person identity or judgment. | Passed |
| 34 | Multi-entry | Stable page-local entry_key supports independent entries. | Passed |
| 35 | Multi-entry | Blank entries create no proposal/domain record. | Passed |
| 36 | Multi-entry | Unreadable is not treated as blank/false/no. | Passed |
| 37 | Multi-entry | Partial page success is allowed. | Passed |
| 38 | Paper review | Capture Proposal references exact interpretation provenance. | Passed |
| 39 | Paper review | Capture Review is distinct from canonical domain Review. | Passed |
| 40 | Paper review | Human reviewer attribution is first-class. | Passed |
| 41 | Paper review | Accepted/corrected/rejected/unresolved dispositions are represented. | Passed |
| 42 | Paper review | Human correction preserves original machine candidate. | Passed |
| 43 | Paper review | Review correction/reversal preserves immutable predecessor history. | Passed |
| 44 | Paper materialization | Only accepted/current Capture Review may authorize materialization. | Passed |
| 45 | Paper materialization | Operation Journal and locks are reused. | Passed |
| 46 | Paper materialization | Partial canonical writes recover without duplicate canonical records. | Passed |
| 47 | Paper materialization | Missing post-commit receipt is reconciled rather than replay-created. | Passed |
| 48 | Paper materialization | Paper-derived canonical provenance uses creation_source paper_capture. | Passed |
| 49 | Import source | Import path is semantically distinct from paper capture. | Passed |
| 50 | Import source | Import Batch binds one exact source snapshot and mapping config. | Passed |
| 51 | Import source | Import Source Record is source-side unit, not Event. | Passed |
| 52 | Import source | One Import Source Record may produce 0..N proposals. | Passed |
| 53 | Import identity | Stable source-provided key is preferred. | Passed |
| 54 | Import identity | Profile-defined exact key is permitted only by deterministic profile rule. | Passed |
| 55 | Import identity | Row order/array position/filename/display text are not stable identity. | Passed |
| 56 | Import replay | Same source + same mapping is idempotent. | Passed |
| 57 | Import replay | Same source key + changed content preserves new history. | Passed |
| 58 | Import replay | Changed mapping preserves new mapping/proposal history. | Passed |
| 59 | Import replay | Missing later source row does not auto-delete Portia history. | Passed |
| 60 | Import safety | Fuzzy name/email matching does not silently create Actor identity. | Passed |
| 61 | Import safety | Source-system labels do not automatically become Portia judgments. | Passed |
| 62 | Import review | Import Proposal has mapping-local stable proposal identity. | Passed |
| 63 | Import review | Source value/transformed candidate/human-resolution-required remain distinct. | Passed |
| 64 | Import review | Import Review is attributable and immutable. | Passed |
| 65 | Import review | Accepted/corrected/rejected/unresolved import dispositions are represented. | Passed |
| 66 | Import review | Import correction preserves source/mapping candidate history. | Passed |
| 67 | Import materialization | Import materialization reuses Operation Journal/locks. | Passed |
| 68 | Import materialization | Import receipt binds exact batch/source/proposal/review lineage. | Passed |
| 69 | Import materialization | Crash replay does not duplicate canonical records. | Passed |
| 70 | Import materialization | Import-derived canonical provenance uses creation_source import. | Passed |
| 71 | Judgment boundary | Capture/import confirmation does not manufacture Classification/Hypothesis/Determination. | Passed |
| 72 | Judgment boundary | Capture/import confirmation does not manufacture Fidelity/Outcome/effectiveness. | Passed |
| 73 | Judgment boundary | Reentry/Repair completion, remorse, forgiveness, clearance are not inferred. | Passed |
| 74 | Integrity | Ordinary uncertainty remains review/retry, not Quarantine. | Passed |
| 75 | Integrity | Integrity Finding is diagnostic for broken provenance/linkage/invariants. | Passed |
| 76 | Integrity | Quarantine is exceptional isolation only. | Passed |
| 77 | Lifecycle | Exact historical paper/import context does not silently follow successors/corrections. | Passed |
| 78 | Lifecycle | Source/review/materialization history is preserved rather than overwritten. | Passed |
| 79 | Time/privacy | Scan/import/processing time is not substituted for domain time. | Passed |
| 80 | Time/privacy | Raw scans/PDF/import files/temp paths are not embedded in Portia JSON. | Passed |
| 81 | Final closeout | Re-run authoritative full schema-validation suite after ADR/docs reconciliation. | Passed |
| 82 | Final closeout | Re-check Portia/Core/Quillan/ScoreForm drift immediately before issue closeout. | Passed |

## Totals

```text
82 criteria tracked
82 passed
0 pending
0 known implementation gaps
```

Final closeout evidence:

```text
python -m unittest discover -s tests/schema_validation
Ran 1020 tests in 130.205s
OK

git diff --check
(no output)

final repository drift verification
Portia unchanged
Core unchanged
ScoreForm unchanged
Quillan unchanged from the accepted pre-ADR one-commit-ahead state
```
