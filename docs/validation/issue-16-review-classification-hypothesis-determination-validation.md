# Issue #16 Validation: Review, Classification, Hypothesis, and Determination Domain Models

**Status:** Contract and integration validation complete
**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**ADR:** `0012 — Define Review, Classification, Hypothesis, and Determination Domain Models`
**Date:** 2026-08-09

## Result

Issue #16 establishes Portia's Event-local human review, interpretation, and
decision layer without collapsing evidence, categorization, tentative
explanation, decision authority, or later response into one mutable finding.

Public contracts introduced:

```text
portia_review_id@1
portia_classification_id@1
portia_hypothesis_id@1
portia_determination_id@1
judgment_evidence_ref@1
review@1
classification@1
hypothesis@1
determination@1
```

No new lifecycle-history, Amendment, Statement of Disagreement, Dependency,
migration, exceptional-removal, operation, lock, Quarantine, Integrity Finding,
source-snapshot, derived-generation, or current-pointer contract was required.

## Repository anchors

See `docs/validation/issue-16-final-repository-checkpoint.md`.

```text
pds-portia branch:
f83c8368b7eff86d8527c01cd67cf13ac254522c

pds-portia main:
35df69904cff3c696876f04e208bbe704bab3e97

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
```

## Test status

Immediately before this documentation/final-acceptance slice:

```powershell
python -m unittest discover -s tests/schema_validation
```

passed with:

```text
589 tests
0 failures
0 errors
```

This closeout slice adds eight documentation-consistency tests and no schema
wire-shape changes. After applying the slice, a clean repository should report
597 tests. If the count or result differs, the observed test output takes
precedence and the closeout should not be committed until reconciled.

## Application-invalid coverage

`docs/validation/issue-16-application-invalid-matrix.json` indexes:

```text
fixture application-invalid scenarios: 92
programmatic cross-record invariants:     9
total coverage entries:                 101
```

## Acceptance coverage

`docs/validation/issue-16-acceptance-matrix.json` contains all 108 acceptance
criteria from Issue #16 and records repository evidence for each.

## Semantic boundaries

One Review is one bounded canonical human review process. Review is not a
finding, and concern/referral concepts remain initiation/routing context.

One Classification is one attributed controlled-category assertion under one
identifiable versioned definition. Reporter and reviewer assertions remain
separate, and Classification is not a student identity trait or policy finding.

One Hypothesis is one attributable explicitly tentative proposition. Supporting,
contrary, and contextual evidence are first-class; competing Hypotheses may
coexist; counts do not establish evidentiary weight. No numeric probability,
risk, credibility, diagnosis, or determined behavioral-function field is added.

One Determination answers one bounded question under explicit scope,
decision-maker attribution, authority context, process/policy basis, and exact
decision basis. Teacher-local and recorded-institutional scope remain distinct.
Portia may preserve authority evidence but does not itself authenticate
institutional authority. Unresolved outcomes remain first-class.

## Correction and shared infrastructure

Material judgment changes use successors rather than substantive in-place
Amendment. Invalidation is distinct from reconsideration/reversal.
Reconsideration and reversal preserve the earlier Determination. Statement of
Disagreement is additive and nonadjudicating. Exact references do not silently
follow successors.

`test_issue_16_shared_infrastructure_compatibility.py` proves reuse of:

```text
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
exceptional_removal@1
operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

## Privacy, automation, paper, and import

Operational/derived records remain metadata-oriented and do not copy substantive
judgment text unnecessarily. Integrity Findings remain data-integrity
diagnostics rather than behavior findings.

Portia may validate, warn, route, and display definitions/checklists. It must not
automatically classify prose, infer intent/function, decide credibility, choose
a winning Hypothesis, determine policy violation, substantiate an allegation,
calculate disciplinary risk, or recommend punishment.

Paper preallocation does not fabricate human judgment. OCR/import may propose
transcription but does not establish reviewer, selector, author, decision-maker,
authority, policy applicability, Hypothesis truth, or Determination outcome.

## Representative examples

`docs/examples/portia-review-classification-hypothesis-and-determination-examples.md`
documents all 28 examples required by Issue #16 using synthetic fixtures or
focused compatibility tests.

## Documentation reconciliation

ADR 0001 remains the research-era conceptual precursor. ADR 0012 is active
implementation authority for the current Review/Classification/Hypothesis/
Determination layer and refines ADR 0001's earlier formal-institutional,
confidence, and amendment assumptions.

ADR 0011 remains authoritative for the Account/Observation source-evidence
layer; Issue #16 begins after that boundary.

After this slice, README, schema guide, ADR 0001, Portia's role design, and the
Account/Observation design carry explicit Issue #16 reconciliation notes.

## Acceptance commands

```powershell
python -m unittest `
  tests.schema_validation.test_issue_16_final_documentation
```

```powershell
python -m unittest discover -s tests/schema_validation
```

```powershell
git diff --check
git status --short
```

## Deferred work

Response/Communication remains #17; Support Process and formal FBA/support
ownership remains #18; Follow-Up/Outcome/Reentry/Repair remains #19; later paper,
privacy, end-to-end graph, and final architecture audit work remains in #20–#23.
