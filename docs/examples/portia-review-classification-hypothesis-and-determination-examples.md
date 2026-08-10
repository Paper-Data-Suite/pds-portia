# Portia Review, Classification, Hypothesis, and Determination Examples

**Status:** Accepted synthetic examples
**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**ADR:** `0012 — Define Review, Classification, Hypothesis, and Determination Domain Models`
**Date:** 2026-08-09

These examples document the accepted Issue #16 interpretation-and-decision layer.
All named people, classes, identifiers, categories, policies, and situations in
the backing fixtures are synthetic.

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response / Support / Follow-Up
```

No arrow means that progression is mandatory.

```text
Review != finding
Classification != fact or student identity
Hypothesis != fact, diagnosis, or determined behavioral function
Determination != evidence, consequence, or proof that every source was true
```

## Required representative set

| # | Example | Validated source |
| ---: | --- | --- |
| 1 | Review opened for one Event Participant | `tests/schema_validation/fixtures/issue-16/review/valid/active-open-participant-account-evidence.json` |
| 2 | Review completed with no Classification or Determination | `tests/schema_validation/fixtures/issue-16/review/valid/completed-without-finding-or-evidence.json` |
| 3 | Reporter-selected Classification | `tests/schema_validation/fixtures/issue-16/classification/valid/reporter-category.json` |
| 4 | Reviewer confirms the same category without rewriting the reporter record | `tests/schema_validation/fixtures/issue-16/classification/review-scenarios/valid/reviewer-confirmed-same-category.json` |
| 5 | Reviewer selects a different Classification | `tests/schema_validation/fixtures/issue-16/classification/review-scenarios/valid/reviewer-selected-disagrees.json` |
| 6 | Reviewer records `unable_to_determine` | `tests/schema_validation/fixtures/issue-16/classification/review-scenarios/valid/reviewer-selected-unable.json` |
| 7 | Event-level Classification does not automatically apply to every Participant | `tests/schema_validation/fixtures/issue-16/classification/valid/event-target.json` |
| 8 | Participant-specific Classification in a multi-participant Event | `tests/schema_validation/fixtures/issue-16/classification/valid/participant-target.json` |
| 9 | Tentative Hypothesis with supporting evidence | `tests/schema_validation/fixtures/issue-16/hypothesis/valid/supporting-account-evidence.json` |
| 10 | Hypothesis with supporting and contrary evidence | `tests/schema_validation/fixtures/issue-16/hypothesis/valid/mixed-evidence-roles.json` |
| 11 | Two competing Hypotheses coexist | `tests/schema_validation/fixtures/issue-16/hypothesis/competition-scenarios/valid/two-active-competing-hypotheses.json` |
| 12 | Hypothesis remains tentative rather than becoming numeric confidence/probability | `hypothesis/valid/supporting-account-evidence.json` plus structural rejection of `hypothesis/invalid/unexpected-confidence-percent.json` |
| 13 | Hypothesis is set aside without rewriting history | `tests/schema_validation/fixtures/issue-16/hypothesis/valid/event-set-aside-empty-evidence.json` |
| 14 | Teacher-local Determination | `tests/schema_validation/fixtures/issue-16/determination/valid/teacher-local-conclusion.json` |
| 15 | Recorded institutional Determination with explicit documented authority basis | `tests/schema_validation/fixtures/issue-16/determination/valid/recorded-institutional-documented-basis.json` |
| 16 | Insufficient-information Determination | `tests/schema_validation/fixtures/issue-16/determination/valid/insufficient-information.json` |
| 17 | Participant-specific Determinations may differ within one Event | `determination/valid/participant-target.json` demonstrates explicit target scope; cardinality semantics are validated by `test_issue_16_determination_contract.py` |
| 18 | Determination explicitly preserves contrary as well as supporting basis | `tests/schema_validation/fixtures/issue-16/determination/valid/mixed-basis-roles.json` |
| 19 | Reconsidered/reversed Determination preserves the earlier record | `tests/schema_validation/fixtures/issue-16/determination/reconsideration-scenarios/valid/reversed-changes-outcome.json` |
| 20 | Statement of Disagreement targets an exact Determination without reversing it | `tests/schema_validation/test_issue_16_shared_infrastructure_compatibility.py::test_statement_of_disagreement_reuses_generic_exact_target` |
| 21 | Related secondhand Accounts are not treated as independent proof | `tests/schema_validation/fixtures/issue-16/hypothesis/lineage-scenarios/valid/known-account-lineage-preserved.json` |
| 22 | Imported Classification preserves incomplete/unknown review-stage provenance | `tests/schema_validation/fixtures/issue-16/classification/valid/import-unknown-stage-proposed.json` |
| 23 | Imported historical Determination may preserve authority/process uncertainty | `tests/schema_validation/fixtures/issue-16/determination/valid/unknown-process-basis-import-proposed.json` and `recorded-institutional-unknown.json` |
| 24 | Paper-derived review material does not fabricate an automatic Determination | `tests/schema_validation/fixtures/issue-16/review/valid/paper-proposed.json` plus structural rejection of `determination/invalid/paper-preallocated.json` |
| 25 | Typed sibling-PDS contextual evidence is a locator, not proof | `tests/schema_validation/fixtures/issue-16/hypothesis/valid/module-evidence.json` |
| 26 | System-generated routing/navigation cannot masquerade as a human Classification | structural rejection of `classification/invalid/system-process-selector.json`; derived navigation remains noncanonical |
| 27 | Invalidated/superseded judgment history remains exactly addressable | lifecycle/history compatibility in `tests/schema_validation/test_issue_16_shared_infrastructure_compatibility.py` |
| 28 | Exact historical references never silently follow a successor | `tests/schema_validation/test_issue_16_shared_infrastructure_compatibility.py::test_dependency_does_not_silently_follow_a_successor` |

## Boundary notes

Reporter and reviewer Classifications are distinct attributed assertions. A
reviewer disagreement is not ordinary correction of the reporter's assertion.

Hypothesis v1 intentionally has no numeric confidence, truth probability,
credibility score, evidence score, risk score, AI confidence, diagnosis, or
determined behavioral-function field. `under_consideration` and `set_aside`
describe human consideration state, not truth.

A recorded institutional Determination preserves what authority is asserted or
documented, but Portia's teacher-local deployment does not independently
authenticate institutional authority. `decision_maker`, `created_by`, Actor
title/category, and local-operator status remain separate concepts.

Supporting, contrary, and contextual references identify how a human used a
source in one judgment. Reference count is not evidentiary weight, and shared
Account lineage must not be converted into automatic corroboration.

Reconsideration and reversal use new Determination records and exact predecessor
relationships. They do not rewrite the earlier decision to make it appear never
to have existed.

The shared operational and derived contracts contain opaque identifiers,
versions, paths, digests, status tokens, and bounded diagnostics rather than
copying substantive Review questions, category definitions, Hypothesis prose,
or Determination rationale.

See:

```text
docs/validation/issue-16-application-invalid-matrix.json
docs/validation/issue-16-acceptance-matrix.json
docs/validation/issue-16-review-classification-hypothesis-determination-validation.md
```
