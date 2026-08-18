# Portia Foundation Traceability

**Issue:** #23 — final foundations architecture audit
**Starting audit baseline:** `523cfd6dd75eef9cb10930e328bb7d98b8924bdf`

This document maps the foundation outcome to controlling decisions and executable evidence. It is intentionally repository-local and network-independent.

## Foundation issue traceability

| Issue | Foundation area | Governing ADR(s) | Principal active design / contract surface | Representative / focused evidence | Audit conclusion |
| --- | --- | --- | --- | --- | --- |
| #10 | Complete Portia foundations milestone | 0001–0017 | README, all foundation designs, schema catalog | #11–#22 deliverables, Issue #23 audit | Foundation is architecturally coherent; final post-audit validation remains. |
| #11 | Shared references, targeting, relationships | 0007 | shared refs, targets, `work_relationship` | Issue #11 focused validation; P22-03/P22-04; G22-001..010 | Accepted. Exact identity dominates convenience matching. |
| #12 | Lifecycle, amendment, correction, migration | 0008 | lifecycle transition, history correction, amendment, disagreement, dependency, migration, ownership correction, exceptional removal | Issue #12 matrices; P22-04; G22-010..016 | Accepted. Correction preserves history; migration is not correction. |
| #13 | Coordinated persistence, recovery, derived indexes | 0009 | Operation Journal/Lock, Quarantine, Integrity Finding, finding admin, source snapshots, derived generations/current pointers | Issue #13 focused suites; P22-14; G22-012/G22-028/G22-029/G22-034..036 | Accepted with runtime implementation concern. |
| #14 | Actor Directory | 0010 | Actor, Contact Point, Actor-to-Student Relationship, Collision and Actor lifecycle | Issue #14 matrices; P22-07; G22-007 | Accepted. Actor identity never replaces roster identity or proves legal authority. |
| #15 | Account and Observation | 0011 | `account`, `observation`, represented-human attribution, evidence time/source refs | Issue #15 matrices; P22-02; G22-017 | Accepted. Source evidence is not a finding. |
| #16 | Review, Classification, Hypothesis, Determination | 0012 | review/judgment contracts and judgment-evidence refs | Issue #16 matrices; P22-15; G22-018..020 | Accepted. Human judgment remains explicit and authority-scoped. |
| #17 | Response and Communication | 0013 | `response@1`, `communication@1` | Issue #17 validation; P22-07 | Accepted. Response/communication do not prove misconduct, effectiveness, delivery, or truth. |
| #18 | Support Process, Support, Intervention, Implementation, Fidelity | 0014 | support-process family, `planned_schedule@1` | Issue #18 validation; P22-08/P22-11/P22-15; G22-021..022 | Accepted. Plan != Implementation != Fidelity != Outcome. |
| #19 | Follow-Up, Outcome, Reentry, Repair | 0015 | follow-up/outcome/reentry/repair plus Account/Observation v2 owner expansion | Issue #19 validation; P22-08..11; G22-023..025 | Accepted. Evaluation does not manufacture causation, clearance, remorse, or restoration. |
| #20 | Paper-assisted capture, PDS2 routing, import | 0016 | capture/import families, Core route/retained-source boundary | Issue #20 validation; P22-05/P22-06; G22-026..029 | Accepted with runtime replay/human-review concern. |
| #21 | Privacy, redaction, export, retention, Sunset boundary | 0017 | deliberate export, source inventory, privacy/retention designs, future Sunset adapter boundary | Issue #21 matrices; P22-12/P22-13; G22-030..037 | Accepted after README authority wording repair. |
| #22 | Representative end-to-end synthetic graphs | 0001–0017 | `tests/fixtures/issue_22/corpus.json`, contract coverage, graph validator | 15 positive + 37 graph-invalid; 161/161 contract-family coverage at handoff | Accepted as integration evidence; final #23 rerun pending. |

## ADR-to-evidence traceability

| ADR | Decision area | Positive pressure | Negative/application pressure | Issue #23 disposition |
| --- | --- | --- | --- | --- |
| 0001 | Evidence, interpretation, determination separation | P22-02/P22-15 | G22-017..020 | `accepted` |
| 0002 | Module boundary | P22-13/P22-15 | G22-009/G22-037 | `accepted` |
| 0003 | Teacher-local initial deployment | P22-03/P22-07 | G22-005..007 | `accepted` |
| 0004 | Identity/ownership/storage | P22-03/P22-11 | G22-001..010/G22-016 | `accepted` |
| 0005 | Event/Participant | P22-01..03 | G22-002/G22-005/G22-008 | `accepted` |
| 0006 | Participant Role | P22-01/P22-02 | G22-017 | `accepted` |
| 0007 | References/targets/relationships | P22-03/P22-04 | G22-001..010/G22-014 | `accepted` |
| 0008 | Lifecycle/correction/migration | P22-04/P22-11 | G22-010..016/G22-025 | `accepted` |
| 0009 | Persistence/recovery/derived | P22-14 | G22-012/G22-028/G22-029/G22-034..036 | `accepted_with_nonblocking_implementation_concern` |
| 0010 | Actor Directory | P22-07 | G22-007 | `accepted` |
| 0011 | Account/Observation | P22-02 | G22-017 | `accepted` |
| 0012 | Review/Classification/Hypothesis/Determination | P22-15 | G22-018..020 | `accepted` |
| 0013 | Response/Communication | P22-07 | cross-record focused validation | `accepted` |
| 0014 | Support/Intervention/Implementation/Fidelity | P22-08/P22-11/P22-15 | G22-021/G22-022 | `accepted` |
| 0015 | Follow-Up/Outcome/Reentry/Repair | P22-08..11 | G22-023..025 | `accepted` |
| 0016 | Paper/PDS2/import | P22-05/P22-06 | G22-026..029 | `accepted_with_nonblocking_implementation_concern` |
| 0017 | Privacy/export/retention/Sunset | P22-12/P22-13 | G22-030..037 | `accepted_with_nonblocking_implementation_concern` |

## Contract-family coverage traceability

Issue #22's `tests/fixtures/issue_22/contract-coverage.json` is the machine-readable coverage map for the live `schemas/schema-catalog.json`.

The handoff reports:

```text
161 / 161 catalog contract families mapped
0 planned contract families
```

Issue #23 Slice 1 adds no public Portia runtime schema and does not alter any published `$id`.

The final audit validator recomputes catalog-versus-coverage equality in the real checkout. A mismatch blocks approval.

Specialized administrative families intentionally remain in focused coverage where a forced positive story would distort semantics, including:

```text
Actor Directory Collision/admin lifecycle
lifecycle-history correction
Amendment
Record Migration
Ownership Correction
Exceptional Removal
Integrity Finding
Quarantine
finding acknowledgement/suppression
```

This is accepted coverage, not a gap, when the coverage manifest explicitly says `existing_focused_fixture_only` and the cited focused suite exists.

## Issue #22 skeptical-test traceability

| Invariant family | Positive evidence | Graph-invalid evidence |
| --- | --- | --- |
| Exact roster/work identity | P22-03 | G22-001..010 |
| Append-preserving correction | P22-04 | G22-010..016 |
| Evidence != judgment | P22-02/P22-15 | G22-017..020 |
| Plan != implementation != fidelity != outcome | P22-08/P22-15 | G22-021..025 |
| Human-reviewed capture/import | P22-05/P22-06 | G22-026/G22-027 |
| Operation reconciliation/replay | P22-14 | G22-028/G22-029 |
| Privacy/export fail closed | P22-12 | G22-030..033 |
| Derived state nonauthoritative | P22-13/P22-14 | G22-012/G22-034..036 |
| Foreign custody remains foreign | P22-13 | G22-037 |

## Foundation exit-condition traceability

| Exit ID | Exit condition | Evidence | Slice 1 status |
| --- | --- | --- | --- |
| EC-01 | Preceding foundation issues #11–#22 complete | merged architecture + Issue #22 handoff | `satisfied` |
| EC-02 | Foundational record families defined | ADRs 0004–0017 + catalog + coverage map | `satisfied` |
| EC-03 | Identity/ownership/storage coherent | ADR 0004 + P22-03 + G22-001..010 | `satisfied` |
| EC-04 | References/targets coherent | ADR 0007 + G22-001..010 | `satisfied` |
| EC-05 | Lifecycle/correction/dependencies coherent | ADR 0008 + P22-04 + G22-011..016 | `satisfied` |
| EC-06 | Coordinated persistence/recovery explicit | ADR 0009 + P22-14 + G22-028..029 | `satisfied` |
| EC-07 | Actor Directory coherent | ADR 0010 + Issue #14 + P22-07/G22-007 | `satisfied` |
| EC-08 | Evidence/judgment layers distinct | ADRs 0011–0012 + G22-017..020 | `satisfied` |
| EC-09 | Response/support/evaluation layers distinct | ADRs 0013–0015 + G22-021..025 | `satisfied` |
| EC-10 | Paper/import boundary coherent | ADR 0016 + P22-05/P22-06 + G22-026..029 | `satisfied` |
| EC-11 | Privacy/export/retention boundary coherent | ADR 0017 + P22-12/P22-13 + G22-030..037 | `satisfied` |
| EC-12 | Core/sibling ownership descriptions current | current baseline review + PF-AUD-002/PF-AUD-003 repair | `satisfied_after_audit_repair` |
| EC-13 | Schema catalog coverage complete and exact-byte evidence checkout-portable | Issue #22 161/161 + PF-AUD-013 LF policy/fixture validation | `satisfied_after_audit_repair` |
| EC-14 | ADRs 0001–0017 have audit dispositions | `docs/decisions/README.md` + audit JSON | `satisfied` |
| EC-15 | Active documentation internally consistent | PF-AUD-001..003 repair + Slice 2 Issue #16 exact-phrase compatibility repair | `satisfied_after_audit_repair` |
| EC-16 | Synthetic-data-only foundation | Issue #22 `synthetic: true`; #23 adds no real records | `satisfied_on_reviewed_corpus` |
| EC-17 | Complete post-audit validation passes | first run exposed PF-AUD-013; Slice 2 removed the broad fingerprint cluster; fresh post-Slice-3 full suite + Issue #22 regression + audit validator required | `blocked` |
| EC-18 | Approval binds exact final audited commit | final commit SHA + ready approval record | `blocked` |

## Findings-to-exit traceability

| Finding | Exit condition(s) affected | Disposition |
| --- | --- | --- |
| PF-AUD-001 | EC-15 | `fixed_in_audit` |
| PF-AUD-002 | EC-11, EC-12, EC-15 | `fixed_in_audit` |
| PF-AUD-003 | EC-08, EC-12, EC-15 | `fixed_in_audit` |
| PF-AUD-004 | EC-13, EC-15, EC-17, EC-18 | open; #23 closeout |
| PF-AUD-005 | EC-06 | nonblocking implementation concern |
| PF-AUD-006 | EC-11 | nonblocking implementation concern |
| PF-AUD-007 | EC-04..EC-11 | nonblocking application-validation implementation concern |
| PF-AUD-008 | EC-11 | accepted institutional-policy dependency |
| PF-AUD-009 | EC-11/EC-12 | accepted future enhancement |
| PF-AUD-010 | EC-12 | accepted future enhancement |
| PF-AUD-011 | foundation milestone scope | accepted out of scope |
| PF-AUD-012 | foundation approval non-claim | accepted out of scope |
| PF-AUD-013 | EC-06, EC-10, EC-11, EC-13, EC-17 | fixed in Slices 2–3; LF checkout policy + HEAD re-materialization + deterministic LF test writer |

## Closeout traceability still required

After Slice 1 is applied, #23 must add final evidence for:

```text
full schema/application-validation test count and result
Issue #22 regression result
foundation validator result
git diff --check result
exact final audited commit
PF-AUD-004 resolution
ready_for_implementation verdict
foundation approval record
```

Until those are present, the machine-readable audit correctly remains `not_ready`.
