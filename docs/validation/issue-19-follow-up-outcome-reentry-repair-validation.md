# Issue #19 Validation: Follow-Up, Outcome, Reentry, and Repair

**Status:** Contract, integration, and documentation validation complete
**Issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`
**ADR:** `0015 — Define Follow-Up, Outcome, Reentry, and Repair Domain Models`
**Date:** 2026-08-13

## Result

Issue #19 establishes Portia's bounded teacher-local downstream documentation and
evaluation layer while preserving:

```text
scheduled Follow-Up
≠ completed Follow-Up

completed Follow-Up
≠ favorable Outcome

Account / Observation
≠ Outcome evaluation

Implementation completed
≠ Support effective

Fidelity as_planned
≠ Support effective

Support Process completed
≠ goal attained
≠ resolved
≠ causal success

later Event / recurrence
≠ intervention failure

fewer documented Events
≠ improvement without adequate coverage

Reentry completed
≠ clearance
≠ compliance
≠ rehabilitation

Repair completed
≠ remorse
≠ forgiveness
≠ relationship restored
≠ admission

temporal sequence / linkage
≠ causation
```

## Canonical contracts

Issue #19 publishes or adds current-use versions for:

```text
account@2
observation@2

follow_up@1
outcome@1
reentry@1
repair@1
```

The earlier `account@1` and `observation@1` contracts remain immutable Event-local
representations.

Opaque #19 identities are:

```text
Follow-Up  fup_
Outcome    out_
Reentry    ren_
Repair     rpr_
```

No public `outcome_evidence_ref@1`, `repair_action@1`,
`repair_participant@1`, `progress@1`, `effectiveness@1`, `closure@1`,
`success@1`, `engagement@1`, `compliance@1`, `remorse@1`,
`forgiveness@1`, `readiness@1`, or `case@1` is introduced.

## Repository anchors

Final pre-acceptance drift check, immediately before this closeout slice:

```text
pds-portia feature branch
9958c10

pds-portia/main
0d08495557721681b11d081e91c8b416a556df8a

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c
```

Final remote comparison before closeout: **9 commits ahead, 0 behind** Portia
`main`. Portia main, Core main, and Meridian main did not drift from the Issue
#19 initial/pre-ADR anchors.

Meridian remains downstream consumer context only and is not a Portia runtime
dependency.

## Test status

The Issue #19 starting authoritative baseline was:

```text
762 tests
OK
```

The pre-closeout authoritative run on `9958c10` passed with:

```text
872 tests
OK
```

This closeout slice adds eight final-documentation tests. A clean post-slice
repository should therefore report:

```text
880 tests
OK
```

Observed local output takes precedence over the predicted count.

## Fixture coverage

```text
Account v2       6 valid /  8 structural-invalid /  8 application-invalid
Observation v2   6 valid /  8 structural-invalid /  8 application-invalid
Follow-Up       10 valid / 13 structural-invalid / 14 application-invalid
Outcome         13 valid / 18 structural-invalid / 17 application-invalid
Reentry         11 valid / 16 structural-invalid / 14 application-invalid
Repair          12 valid / 25 structural-invalid / 19 application-invalid
---------------------------------------------------------------------------
TOTAL           58 valid / 88 structural-invalid / 80 application-invalid
```

The identifier primitive suite separately validates the four collision-checked
opaque ID families.

The final application-invalid matrix indexes:

```text
fixture application-invalid:       80
programmatic integration checks:   26
total coverage entries:           106
```

## Acceptance coverage

`docs/validation/issue-19-acceptance-matrix.json` mirrors all **88** live Issue
#19 acceptance criteria.

```text
pass:     88
pending:   0
```

## Evidence ownership

Issue #19 resolves the Support-Process evidence gap additively with
`account@2` and `observation@2`.

```text
source perspective → Account
direct measurement → Observation
bounded human evaluation → Outcome
```

Support-Process evidence no longer requires a fabricated Event. Raw Account or
Observation payload is not copied into Outcome.

## Follow-Up

One Follow-Up is one bounded owned downstream check/review/coordination
obligation. Planned timing and workflow completion remain separate.

`overdue` remains derived; time passage or reminder delivery does not manufacture
completion. Completed Follow-Up may exact-link produced Account, Observation,
Communication, Outcome, Fidelity, Reentry, Repair, or later Follow-Up records
without copying their substantive payload.

A Support Process review uses Follow-Up and, when a bounded evaluation is made,
Outcome. Event-local `review@1` is not broadened.

## Outcome / recurrence / causality

One Outcome is one bounded attributable human evaluation of one defined question
for an explicit target and timeframe, based on explicit evidence/context.

Outcome can represent Goal status, observed change, recurrence review, support
response review, unintended/adverse change, Reentry status, Repair status, or a
bounded other conclusion.

Missingness and `unable_to_determine` are first-class. Recurrence conclusions
require explicit timeframe and coverage. A later Event does not automatically
mean intervention failure; no later Event does not prove no recurrence.

Ordinary Outcome has no causal-effect boolean or universal effectiveness score.
Outcome, Fidelity, workflow completion, and plan adaptation remain distinct.

## Support Process review / closure

A completed review does not automatically close a Support Process. A favorable
Outcome does not auto-close it, and an unfavorable Outcome does not auto-adapt or
intensify a plan.

A human-selected Follow-Up disposition may inform a revision-aware workflow
operation. Material prospective plan adaptation continues to use Issue #18
successor semantics.

Support Process completion remains distinct from causal success or resolution.

## Reentry

Reentry is a bounded teacher-local return-support plan/process. It is not medical
clearance, threat-assessment clearance, special-education placement authority,
legal permission to attend, punishment, apology requirement, behavior contract,
or readiness score.

Existing Support/Intervention plans are exact-linked rather than cloned. Actual
actions remain their existing canonical families.

Date passage, physical return, and completion of one planned element do not
automatically complete Reentry. Reentry completion does not establish safety,
compliance, rehabilitation, or restored relationships. Post-Reentry evaluation
is a separate Follow-Up and optionally Outcome.

Optional Portia Reentry steps do not create school/class access barriers.

## Repair

Repair is one bounded teacher-local restorative/reparative process, not an
admission, punishment, truth finding, character judgment, institutional
restorative-justice authority, or financial ledger.

Participant roles are neutral and participation states preserve invitation,
agreement to participate, participation, decline, unavailability, withdrawal,
not-applicable, and unknown without cooperation, compliance, remorse, or
sincerity labels.

Repair participants and agreed actions remain embedded process-local entries;
there is no public `repair_participant@1` or `repair_action@1`.

Affected-person participation, a direct meeting, and apology are not mandatory.
Repair/action completion does not establish remorse, forgiveness, relationship
restoration, rehabilitation, or recurrence prevention. Evaluated relationship
change is a separate Outcome.

## Lifecycle / shared infrastructure / cross-year

All four #19 v1 families use canonical lifecycle:

```text
proposed
active
invalidated
superseded
```

with family-specific workflow/evaluation state separate from lifecycle.

No v1 Amendment paths are exposed. Material correction uses successor/history
semantics. Exact references never silently follow successors, migration,
consolidation, ownership correction, or adaptation.

Issue #19 reuses generic disagreement, dependency, migration, Event-oriented
ownership correction where applicable, exceptional removal,
`operation_journal@2`, `operation_lock@2`, `quarantine_record@2`,
`integrity_finding@2`, `source_snapshot@1`, `derived_index_metadata@1`, and
`derived_current_pointer@1`.

Derived state is rebuildable and nonauthoritative. **Missing derived state never
proves absence.**

Cross-year Support Process continuity continues to use `continues_from`. Old
Issue #19 records remain exact historical records; they are not cloned,
migrated merely because a school year changes, or silently retargeted.

## Paper / privacy / automation

Issue #20 remains authoritative for paper/PDS2/import activation and human-review
operationalization. Paper templates must not fabricate completion, Outcome,
agreement, participation, Reentry completion, Repair completion, or judgment.

Issue #21 remains authoritative for full redaction/export/retention/Sunset
integration.

Native #19 payloads minimize restricted content. Automation may validate,
remind, calculate transparent comparisons, rebuild derived state, and surface
review needs, but must not infer progress, recurrence, effectiveness, causation,
closure, plan adaptation, Reentry completion, Repair completion, compliance,
engagement, remorse, forgiveness, risk, family engagement, or provider
competence.

## Core v0.6 / Meridian / portfolio boundary

Core v0.6 `intervention_record_set` with `intervention_outcomes` remains a future
privacy-minimized publication projection over Portia-native authority. Portia
owns native Outcome semantics.

Issue #19 does not implement a producer profile, producer manifest, Publication
Record, Academic Work Registration, `academic_result_set`, Meridian adapter,
Score, standards rating, Grade, or automatic portfolio publication.

Discoverability is not disclosure authorization.

## Representative examples

`docs/examples/portia-follow-up-outcome-reentry-repair-examples.md` contains
**50 synthetic examples**, exceeding the Issue #19 minimum of 40.

## Documentation reconciliation

README, schema guide, the Issue #19 design, Account/Observation design, Support
Process design, and Portia role analysis are reconciled to accepted ADR 0015 and
the implemented contracts.

All committed Issue #19 fixtures and examples use synthetic identities, classes,
Events, supports, communications, measurements, reentry situations, and repair
processes. **No real student, family, staff, or support data is committed.**
No real reentry or repair case data is committed.

## Deferred work

Issue #20 owns paper/PDS2/import operationalization.

Issue #21 owns privacy/redaction/export/retention/Sunset integration.

Issue #22 owns broader full-foundations end-to-end examples across all Portia
layers.

Issue #23 owns the final foundations audit.

## Acceptance commands

```powershell
python -m unittest tests.schema_validation.test_issue_19_final_documentation
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```
