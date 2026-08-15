# Issue #21 Synthetic Example Inventory

All examples in this inventory are synthetic.

They contain no real student, family, staff, behavior, support, contact,
retention, legal, policy, or source-system data.

## Inventory summary

Slice 7 establishes **24 machine-checked cross-cutting synthetic scenarios**.

The manifest is:

```text
tests/fixtures/issue_21/manifest.json
```

Scenario files are:

```text
tests/fixtures/issue_21/scenarios/*.json
```

The validator is:

```text
tests/schema_validation/test_issue_21_application_invalid_and_synthetic_examples.py
```

These are **scenario descriptors**, not new public Portia contracts.

Their purpose is to prove that Issue #21 has representative integrated examples
covering the privacy/export/retention boundaries before ADR 0017 is accepted.

## Scenario inventory

| ID | Focus | Expected boundary |
| --- | --- | --- |
| `P21-01` | teacher-current bounded Event view | current work only; no dossier |
| `P21-02` | three-participant student view | focal participant included; unrelated identities withheld |
| `P21-03` | third-party Account source | source identity withheld; narrative manual review |
| `P21-04` | multi-target Observation | focal applicability without false singularization |
| `P21-05` | Communication hidden recipient | unrelated recipient and endpoint withheld |
| `P21-06` | restricted Communication | fail closed |
| `P21-07` | active Statement of Disagreement | contested content and disagreement evaluated together |
| `P21-08` | manual redaction required | no automatic paraphrase |
| `P21-09` | absent vs withheld vs unavailable | meanings remain distinct |
| `P21-10` | small-cell aggregate | contextual re-identification review |
| `P21-11` | deliberate student-facing PDF | exact policy/source/output provenance |
| `P21-12` | successor export after correction | new `pexp_`; old export immutable |
| `P21-13` | generated export not disclosed | no recipient/delivery inference |
| `P21-14` | deletion request unresolved | no destructive action |
| `P21-15` | outstanding access hold | retention action blocked |
| `P21-16` | Statement of Disagreement retention unit | required association preserved |
| `P21-17` | coherent supersession retention unit | history may be disposed only coherently and when authorized |
| `P21-18` | derived cache deletion | cache deletion does not delete canonical source |
| `P21-19` | stale cache after source disposition | derived state cannot resurrect disposed source |
| `P21-20` | Portia Page Record / Core scan | Core retained source remains foreign custody |
| `P21-21` | future Sunset dry-run | planning is non-destructive and semantic |
| `P21-22` | stale Sunset candidate | source drift requires revalidation |
| `P21-23` | partial cross-module disposition | per-module result preserved; no fake atomicity |
| `P21-24` | outside-suite export copy | local deletion does not prove external destruction |

## What these examples prove

They prove that the Issue #21 documentation and tests contain explicit,
machine-checkable scenario coverage for the required boundaries.

They do not prove legal entitlement, legal-hold applicability, policy validity,
or runtime deletion correctness.

## What these examples do not become

The descriptors are not:

```text
canonical behavior records
privacy request cases
legal holds
retention policies
disposition certificates
Sunset protocol records
```

Issue #22 will build broader representative end-to-end synthetic contract graphs
after Issue #21 architecture is accepted.
