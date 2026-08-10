# Issue #16 Pre-ADR Repository Checkpoint

**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**Date:** 2026-08-07
**Checkpoint:** Immediately before ADR 0012 acceptance

## Purpose

Record repository drift immediately before freezing the Review / Classification / Hypothesis / Determination architecture.

## Reviewed anchors

```text
pds-portia/main
35df69904cff3c696876f04e208bbe704bab3e97

Issue #16 branch
16-review-classification-hypothesis-determination-domain-models
71372063da4aad9dc85a61927aa8b6aaa793b587
1 commit ahead of main
0 commits behind main

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6
```

The Issue #16 branch contains only Slice 1 at this checkpoint:

```text
docs/design/portia-review-classification-hypothesis-and-determination-domain-models.md
docs/validation/issue-16-initial-repository-checkpoint.md
```

## Drift classification

| Area | Result | Implication |
| --- | --- | --- |
| Portia `main` | no drift since Issue #16 branch point | no rebase or contract reconciliation required |
| Core `main` | unchanged from Issue #16 initial anchor | no shared Core change required |
| Account / Observation contracts | current and merged | remain authoritative source-evidence boundary |
| shared exact references | current and generic | sufficient basis for judgment-reference design |
| lifecycle/correction infrastructure | current and generic | reuse rather than publish judgment-specific infrastructure |
| institutional identity / authorization | still absent from Core | Determination must record authority context without claiming platform authentication |
| sibling modules | no concrete contract change identified | no sibling repository work required before ADR 0012 |

## Contract checks that materially affected the freeze

### `represented_human_attribution@1`

ADR 0011 permits later Portia records to adopt the primitive when they need the same represented-human semantics. Issue #16 therefore reuses it for reviewer, Classification selector, Hypothesis author, and decision-maker identity. Authority remains a separate concept.

### `exact_portia_work_record_ref@1`

The existing exact reference preserves exact work and record contract versions and explicitly prohibits silent migration/supersession following. No judgment-family-specific exact reference is required.

### `source_artifact_ref@1`

The contract is a typed material/provenance locator and explicitly does not establish authenticity, accuracy, authorization, credibility, or evidentiary weight.

The pre-ADR freeze does **not** place the complete source-artifact union inside `judgment_evidence_ref@1`. Doing so would permit overlapping logical reference shapes and would allow judgment records to bypass the Account/Observation source-evidence layer.

Raw artifacts may still be used as record-specific authority/policy provenance where the contract's locator-without-proof semantics are appropriate.

## Freeze result

The twelve Slice-1 open questions were resolved as follows:

1. `judgment_evidence_ref@1` = Portia work + exact Portia record + sibling-module record only.
2. Review trigger = `concern | referral | routine_review | reconsideration | support_related | other`.
3. Review question kind = `evidence_review | classification_review | hypothesis_review | determination_review | reconsideration | other`.
4. Active nonterminal Review may append evidence and advance workflow state; completed/cancelled Review is frozen.
5. Classification stage = `reporter_selected | reviewer_selected | reviewer_confirmed | unknown`.
6. Classification result = `category_selected | unable_to_determine`; category identity = scheme/version/code with required meaning snapshot.
7. Hypothesis uses `under_consideration | set_aside`; no confidence/probability field.
8. Teacher-local scope = `classroom_management | teacher_review | teacher_support_coordination | other`.
9. Recorded-institutional authority status = `documented_basis | asserted | unknown`.
10. Determination process basis and outcome unions are frozen in the design.
11. Imported historical judgments may be preserved after human review with explicit limitations, but unresolved identity/authority does not become consequential authority.
12. All four v1 record families expose no Amendment paths.

## ADR readiness

No remaining pre-ADR issue requires a new Core contract, sibling-module contract, or revision of a published Portia schema.

ADR 0012 may therefore be accepted before public Issue #16 schemas are published.

## Remaining drift obligation

Perform one final Portia/Core drift check immediately before Issue #16 closure.
