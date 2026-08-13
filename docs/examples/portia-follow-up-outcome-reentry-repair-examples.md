# Portia Follow-Up, Outcome, Reentry, and Repair Examples

**Issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`

All examples below are **synthetic**. They illustrate record boundaries rather than
prescribe school policy, prove causation, or represent real students, families, staff,
supports, reentry situations, or restorative processes.

The examples preserve these governing distinctions:

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

| # | Synthetic scenario | Correct canonical record(s) | Boundary preserved |
|---:|---|---|---|
| 1 | Synthetic Event student check-in is scheduled for Friday. | Follow-Up only | scheduled Follow-Up ≠ completed Follow-Up |
| 2 | Synthetic scheduled Follow-Up passes its planned date without a recorded completion. | Follow-Up + derived reminder state only | time elapsed / overdue-derived ≠ completed |
| 3 | Synthetic completed student check-in captures the student's substantive perspective. | Follow-Up + Account v2 | completion linkage ≠ copied perspective payload |
| 4 | Synthetic completed family phone call records that contact occurred. | Follow-Up + Communication | Communication ≠ family agreement or participation |
| 5 | Synthetic direct classroom count is collected during a planned check. | Follow-Up + Observation v2 | direct measurement ≠ Outcome evaluation |
| 6 | Synthetic Support Process review Follow-Up records an `adapt_plan` disposition. | Follow-Up | human disposition ≠ automatic plan successor |
| 7 | Synthetic second check-in occurs two weeks after an earlier completed check-in. | new Follow-Up | later Follow-Up ≠ mutation of earlier history |
| 8 | Synthetic Follow-Up is cancelled because the teacher changes the review plan. | Follow-Up | cancelled workflow ≠ target declined |
| 9 | Synthetic Follow-Up is unable to complete because the planned context is unavailable. | Follow-Up | unable_to_complete ≠ person unavailable unless separately evidenced |
| 10 | Synthetic Communication lists a family recipient while no Repair participation exists. | Communication | recipient ≠ participant / consent / agreement |
| 11 | Synthetic Goal review finds the bounded Goal met for the stated period. | Outcome + exact Goal ref | Goal-status Outcome ≠ rewriting Goal |
| 12 | Synthetic Goal review finds only partial attainment for the stated period. | Outcome + exact Goal ref | partially_met remains bounded to timeframe/evidence |
| 13 | Synthetic Goal review lacks enough current evidence to conclude. | Outcome | unable_to_determine requires explicit limitation |
| 14 | Synthetic direct-count comparison supports an improved observed-change conclusion. | Observation v2 + Outcome | raw measurement ≠ attributed evaluation |
| 15 | Synthetic mixed measures support a mixed observed-change conclusion. | Outcome | mixed result ≠ forced single success score |
| 16 | Synthetic recurrence review documents a later matching Event within defined coverage. | Outcome + exact evidence refs | later Event ≠ intervention failure / causation |
| 17 | Synthetic recurrence review finds no recurrence in a defined observed period. | Outcome | no_recurrence_observed_within_defined_coverage ≠ universal absence |
| 18 | Synthetic record review finds no later Event but observation coverage is inadequate. | Outcome | fewer documented Events ≠ improvement |
| 19 | Synthetic review notes a concerning change during a support period. | Outcome | adverse/unintended change ≠ causal-effect claim |
| 20 | Synthetic Intervention occurrence is completed while later progress is unclear. | Implementation + Outcome | Implementation completed ≠ Support effective |
| 21 | Synthetic Fidelity review is `as_planned` while the later Outcome is mixed. | Fidelity + Outcome | Fidelity as_planned ≠ effectiveness |
| 22 | Synthetic Fidelity evidence is unavailable and the evaluator records that limitation. | Outcome | unknown Fidelity ≠ poor Fidelity / automatic failure |
| 23 | Synthetic student Account provides contrary perspective to other evidence. | Account v2 + Outcome basis | student voice remains first-class evidence |
| 24 | Synthetic family Account provides supporting perspective during Support Process review. | Account v2 + Outcome basis | family perspective ≠ engagement score |
| 25 | Synthetic later review evaluates a new month after an earlier Outcome. | new Outcome | later timeframe ≠ correction of earlier Outcome |
| 26 | Synthetic completed Support Process review selects `continue_current_support`. | Follow-Up + optional Outcome | review completion ≠ closure |
| 27 | Synthetic review selects `adapt_plan` and a human later creates a plan successor. | Follow-Up + #18 successor plan | Outcome/disposition ≠ automatic adaptation |
| 28 | Synthetic favorable Outcome is recorded while the Support Process remains active. | Outcome | favorable Outcome ≠ auto-close |
| 29 | Synthetic unfavorable Outcome is recorded without automatically intensifying support. | Outcome | unfavorable Outcome ≠ auto-intensify |
| 30 | Synthetic Support Process is later marked completed after a human workflow decision. | Support Process + history | process completed ≠ causal success / resolved |
| 31 | Synthetic Reentry references a minimal external restricted-process locator. | Reentry | context locator ≠ Portia clearance authority |
| 32 | Synthetic Outcome basis retains an older exact Observation representation after a successor exists. | Outcome + exact ref | exact history ≠ silent successor following |
| 33 | Synthetic Reentry is planned for a date-only return. | Reentry | planned return timing ≠ actual return |
| 34 | Synthetic planned Reentry date passes with no completion recorded. | Reentry | date passage ≠ Reentry completed |
| 35 | Synthetic person returns while one planned orientation element remains unfinished. | Reentry | person returned ≠ every planned element occurred |
| 36 | Synthetic Reentry workflow is completed after planned teacher-local steps occur. | Reentry | Reentry completed ≠ clearance / safety / compliance / rehabilitation |
| 37 | Synthetic Reentry exact-links an existing Support and Intervention. | Reentry + exact plan refs | existing plans are referenced rather than cloned |
| 38 | Synthetic post-return check occurs the next day. | new Follow-Up | post-Reentry evaluation ≠ embedded Reentry completion field |
| 39 | Synthetic clinical or safety process remains outside Portia with only minimal context retained. | Reentry external context | external authority ≠ reconstructed Portia case record |
| 40 | Synthetic Reentry is cancelled as a local plan when circumstances change. | Reentry | cancelled Reentry ≠ denial of school/class access |
| 41 | Synthetic Repair invitation is offered and one participant declines. | Repair | declined ≠ uncooperative / noncompliant / lack of remorse |
| 42 | Synthetic affected person is unavailable for the proposed Repair process. | Repair | unavailable ≠ unwilling / forgiving / unforgiving |
| 43 | Synthetic student participates in a Repair conversation. | Repair | participated ≠ admission / agreement with allegation / remorse |
| 44 | Synthetic Repair includes a planned follow-up conversation without an apology requirement. | Repair embedded action | Repair ≠ mandatory apology |
| 45 | Synthetic agreed property-restoration action is completed. | Repair embedded action | completed action ≠ remorse / forgiveness |
| 46 | Synthetic Repair workflow is completed after its bounded agreed process. | Repair | Repair completed ≠ relationship restored / rehabilitation |
| 47 | Synthetic evaluator later reviews relationship change after a completed Repair. | Outcome with repair_status scope | relationship change is a separate Outcome |
| 48 | Synthetic agreed Repair action is withdrawn. | Repair embedded action | withdrawn ≠ uncooperative / insincere |
| 49 | Synthetic property replacement is documented as an agreed non-financial action. | Repair embedded action | Repair ≠ debt / billing / collections ledger |
| 50 | Synthetic fewer Event records follow a completed Repair during a partially observed period. | Observation/Account + optional Outcome | temporal sequence / linkage ≠ causation |

## Interpretation rule

The table is intentionally non-causal. A later record may be linked to earlier
context without establishing that the earlier Response, Support, Intervention,
Reentry, or Repair caused the later condition. Where a human evaluates change,
`outcome@1` carries the bounded question, timeframe, basis, result, and limitations.

No example creates a Score, standards rating, Grade, readiness score, compliance
score, engagement score, remorse score, forgiveness score, or automatic portfolio
publication.
