# Issue #18 Validation: Support Process, Support, Intervention, Implementation, and Fidelity

**Status:** Contract and integration validation complete
**Issue:** `#18 — Define Support Process, Support, Intervention, Implementation, and Fidelity contracts`
**ADR:** `0014 — Define Support Process, Support, Intervention, Implementation, and Fidelity Contracts`
**Date:** 2026-08-12

## Result

Issue #18 establishes Portia's bounded teacher-local support workflow layer while preserving:

```text
planned Support / Intervention
≠ actual Implementation

Implementation
≠ Fidelity

Fidelity / implementation quality
≠ effectiveness
≠ student compliance
≠ provider competence
≠ Outcome

workflow completion
≠ success
≠ resolution
```

Issue #19 remains authoritative for Follow-Up, Outcome, Reentry, Repair, recurrence interpretation, and effectiveness/causal claims.

## Canonical contracts

```text
support_process@1
support_process_participant@1
support_need@1
support_goal@1
support@1
intervention@1
planned_schedule@1
implementation@1
fidelity@1
```

Opaque identities are `sup_`, `spp_`, `spn_`, `spg_`, `spt_`, `int_`, `imp_`, and `fid_`. The existing `portia_support_process_id@1` is reused.

## Repository anchors

```text
pds-portia branch (pre-closeout):
4d23d30e1a1e7a86733cd9754b436e7da96d4b1c

pds-portia main:
5898ad79a7d405dc1e23b94753a0eeba793c8e72

pds-core main:
6c507213618b68a6dd3ea096e1a898201ff029e6
```

Final remote comparison before closeout: **9 commits ahead, 0 behind**. Neither Portia main nor Core main drifted from the starting anchors.

## Test status

The pre-closeout authoritative run passed with **754 tests**, 0 failures, 0 errors. This closeout slice adds eight documentation tests; a clean post-slice repository should therefore report **762 tests**. Observed output takes precedence.

## Fixture coverage

```text
Support Process              10 valid / 12 structural-invalid / 16 application-invalid
Support Process Participant   8 valid / 12 structural-invalid / 11 application-invalid
Support Need                  8 valid / 13 structural-invalid / 12 application-invalid
Support Goal                  6 valid / 12 structural-invalid / 12 application-invalid
Support                       8 valid / 14 structural-invalid / 13 application-invalid
Intervention                  8 valid / 14 structural-invalid / 15 application-invalid
Implementation               10 valid / 17 structural-invalid / 22 application-invalid
Fidelity                      9 valid / 21 structural-invalid / 21 application-invalid
```

The final application-invalid matrix indexes **122 fixture scenarios + 13 programmatic cross-record invariants = 135 coverage entries**.

## Acceptance coverage

`docs/validation/issue-18-acceptance-matrix.json` mirrors all **128** criteria in Issue #18.

```text
pass:    128
pending:   0
```

## Domain boundaries

Support Process is one bounded class-owned teacher-local workflow, not a student-global dossier, institutional case-management record, IEP/504/BIP/FBA system of record, diagnosis/treatment plan, or institutional authorization record.

Participant contexts do not establish provider assignment, guardianship, consent, employment, licensure, or authority. Need is descriptive and non-diagnostic. Goal is a desired future support condition, not progress, attainment, proficiency, Grade, compliance, effectiveness, or Outcome.

Support and Intervention are separate plan families. `planned_schedule@1` is planning only and never fabricates Implementation. Active Intervention requires an assigned provider and non-as-needed schedule.

One Implementation records one bounded actual occurrence/attempt/interval of one exact plan. One-off variation is descriptive; material prospective adaptation creates a plan successor. Existing exact references never silently retarget.

Fidelity evaluates one exact plan across one Implementation, an explicit same-plan Implementation set, or a bounded plan interval. Scored instruments retain their source-defined instrument/version/scale. Missing Fidelity does not imply poor Fidelity; high Fidelity does not imply effectiveness.

## Communication / Event integration

`communication@1` remains wire-compatible. Support Process-owned Communication can now resolve against the canonical owner, but Communication remains a contact act/attempt rather than consent, participation proof, service delivery, Implementation, Fidelity, or Outcome.

`work_relationship@2` is reused narrowly for Support Process `draws_context_from` Event context.

## Lifecycle / shared infrastructure

Issue #18 exposes no v1 Amendment paths for Support Process, Participant, Need, Goal, Support, Intervention, Implementation, or Fidelity. Material correction uses successor/history semantics; Statement of Disagreement remains additive.

Shared lifecycle/history, migration/removal, `operation_journal@2`, `operation_lock@2`, `quarantine_record@2`, `integrity_finding@2`, `source_snapshot@1`, `derived_index_metadata@1`, and `derived_current_pointer@1` are reused. Derived state remains rebuildable and nonauthoritative.

## Paper / privacy / automation

Paper preallocation cannot fabricate plan/Implementation/Fidelity. Imports remain proposed until accepted review history permits current use. Automation may validate references, chronology, schedules, duplicates, reminders, and privacy-minimized derived state, but must not diagnose, infer disability/function/risk, select Interventions from Event counts, create Implementation from schedule, infer Fidelity/compliance/engagement/provider competence/effectiveness, close a process from dates, or publish support data.

## Core v0.6 boundary

Core v0.6 `intervention_record_set` remains a future privacy-minimized publication projection over Portia-native authority. Issue #18 does not implement Academic Work Registration, `academic_result_set`, Scores, standards ratings, Grades, Portia producer manifests/profiles, automatic Meridian publication, or automatic Vitrine publication. Discoverability is not disclosure authorization.

## Representative examples

The example document contains **50 synthetic examples**, exceeding the Issue #18 minimum of 40.

## Documentation reconciliation

README, schema guide, Portia role analysis, and the Response/Communication design are reconciled to accepted ADR 0014 and the new downstream Support Process boundary.

All committed Issue #18 fixtures and examples use synthetic identities, classes, supports, communications, and situations. **No real student, family, staff, or support data is committed.**

## Deferred work

Issue #19 owns Follow-Up / Outcome / Reentry / Repair. Issue #20 owns paper/PDS2/import operationalization. Issue #21 owns privacy/redaction/export/retention/Sunset integration. Issue #22 owns full end-to-end foundation examples. Issue #23 owns final foundations audit.

## Acceptance commands

```powershell
python -m unittest tests.schema_validation.test_issue_18_final_documentation
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```
