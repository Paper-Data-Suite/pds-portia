# Issue #22 Acceptance Matrix

**Status:** Complete implementation — PR-review traceability repair pending confirmation gates
**Date:** 2026-08-17

## Implemented acceptance evidence through Slice 14

| Requirement | State | Evidence |
| --- | --- | --- |
| Versioned non-runtime corpus descriptor exists | PASS | `tests/fixtures/issue_22/corpus.json` |
| Scenario descriptor is explicitly non-runtime and synthetic | PASS | P22-01 `scenario.json` |
| Public records contain no fixture-only fields | PASS | P22-01 `records/*.json` |
| Exact catalog contract/version validation is reused | PASS | `issue_22_graph_validation.py` |
| Synthetic Core roster context is clearly non-public/test-only | PASS | `shared/core-context/roster.json` and corpus README |
| P22-01 positive classroom Event exists | PASS | P22-01 fixture directory |
| Event@2 participates in a coherent graph | PASS | P22-01 |
| Event Participant@3 participates in a coherent graph | PASS | P22-01 |
| Event Participant Role@3 participates in a coherent graph | PASS | P22-01 |
| Observation@2 participates in a coherent graph | PASS | P22-01 |
| Exact roster-qualified subject resolution is graph-checked | PASS | P22-01 + graph validator |
| Canonical class/work/path agreement is graph-checked | PASS | P22-01 + graph validator |
| Participant targets are graph-resolved | PASS | P22-01 + graph validator |
| Deterministic teacher-current derived summary rebuilds | PASS | P22-01 expected fixture + tests |
| No Classification/Determination/Response/Outcome is fabricated | PASS | P22-01 expected fixture + tests |
| No public schema is added by Slice 1 | PASS | Slice 1 file inventory |
| No ADR is added by Slice 1 | PASS | Slice 1 file inventory |
| P22-02 multi-participant Event exists | PASS | P22-02 fixture directory |
| Three participant relationships coexist in one Event | PASS | P22-02 |
| Conflicting Account v2 records remain separate evidence | PASS | P22-02 |
| Active reported-involvement role has exact Account basis | PASS | P22-02 + graph validator |
| Direct Observation remains distinct from reported involvement | PASS | P22-02 |
| Completed Review resolves all exact Portia evidence refs | PASS | P22-02 + graph validator |
| Active Determination resolves completed Review exactly | PASS | P22-02 + graph validator |
| Determination preserves supporting/contrary/contextual basis | PASS | P22-02 |
| Determination ends in `insufficient_information` | PASS | P22-02 |
| No Classification or Hypothesis is fabricated | PASS | P22-02 expected fixture + tests |
| P22-03 cross-class participant scenario exists | PASS | P22-03 fixture directory |
| Event retains one exact owning class | PASS | P22-03 Event/descriptor |
| Cross-class participant resolves through exact foreign roster pair | PASS | P22-03 + graph validator |
| Matching local `student_id` across two rosters is not merged | PASS | P22-03 collision fixture + tests |
| Matching display name across two rosters is not merged | PASS | P22-03 collision fixture + tests |
| Active subject uniqueness uses full durable subject key | PASS | graph validator |
| Cross-class Observation targets exact Event Participant, not unqualified student | PASS | P22-03 Observation + tests |
| P22-04 correction/supersession scenario exists | PASS | P22-04 fixture directory |
| Material predecessor Account remains canonical and `superseded` | PASS | P22-04 |
| Corrected Account is a distinct active successor | PASS | P22-04 |
| Successor uses exact `supersedes` work-record reference | PASS | P22-04 + graph validator |
| Statement of Disagreement targets exact predecessor | PASS | P22-04 + graph validator |
| Disagreement does not mutate/adjudicate predecessor | PASS | P22-04 fixtures + tests |
| Historical Review remains pinned to predecessor | PASS | P22-04 Review + tests |
| Lifecycle predecessor chain reconciles final statuses | PASS | P22-04 + graph validator |
| Derived current frontier selects successor without deleting predecessor | PASS | graph helper + P22-04 tests |
| P22-05 paper/PDS2 scenario exists | PASS | P22-05 fixture directory |
| Capture Batch remains operational and distinct from Event | PASS | P22-05 |
| Page Target is the exact pre-print Core route target | PASS | P22-05 + graph validator |
| Deterministic retained-source BMP has real SHA-256/length | PASS | byte fixture + graph validator |
| Page Record resolves exact route/source/page identity | PASS | P22-05 + graph validator |
| Paper Interpretation preserves candidate status and exact layout snapshot | PASS | P22-05 + graph validator |
| Capture Proposal binds exact interpreted fields to Event target paths | PASS | P22-05 + graph validator |
| Teacher Capture Review gates materialization without becoming domain judgment | PASS | P22-05 + tests |
| Paper-derived Event uses `paper_capture` / `ingested` provenance | PASS | P22-05 Event + graph validator |
| Event domain time is independent of capture workflow time | PASS | P22-05 tests |
| Capture Materialization resolves exact accepted Review and committed operation context | PASS | P22-05 + graph validator |
| Capture Materialization follows canonical Event acceptance | PASS | P22-05 + graph validator |
| Physical-page idempotency tuple is explicit and unique | PASS | P22-05 + graph validator |
| P22-06 structured-import scenario exists | PASS | P22-06 fixture directory |
| Import Batch is class-local operational state without `work_id` | PASS | P22-06 + graph validator |
| CSV snapshots use truthful SHA-256/byte lengths | PASS | source fixtures + graph validator |
| Import Batch identity digest recomputes deterministically | PASS | P22-06 + graph validator |
| Import Source Record content/identity digests recompute | PASS | P22-06 + graph validator |
| Stable source-provided key is preserved independently of row order | PASS | P22-06 |
| Import Proposal identity digest recomputes from exact lineage/mapping | PASS | P22-06 + graph validator |
| Source values are referenced rather than copied into Proposal | PASS | P22-06 |
| Source `resolved` assertion is deliberately not mapped to Portia judgment | PASS | P22-06 fixtures + tests |
| Human Import Review gates materialization without becoming domain Review | PASS | P22-06 + graph validator |
| Import-derived Event uses exact import provenance | PASS | P22-06 Event + graph validator |
| Event domain time is independent of import workflow times | PASS | P22-06 tests |
| Import Materialization binds exact Batch/Source/Proposal/Review/Operation lineage | PASS | P22-06 + graph validator |
| Later missing source row leaves prior Event active | PASS | second batch + graph validator |
| P22-07 immediate Response/family Communication scenario exists | PASS | P22-07 fixture directory |
| Actor is workspace-scoped rather than class/work-owned | PASS | P22-07 + graph validator |
| Contact Point resolves beneath exact Actor | PASS | P22-07 + graph validator |
| Local Contact Point verification is preserved separately from recipient participation | PASS | P22-07 fixtures + tests |
| Actor-to-Student Relationship resolves exact Core roster pair | PASS | P22-07 + graph validator |
| Active Relationship has local human review | PASS | P22-07 + graph validator |
| Family relationship does not encode legal/disclosure authority | PASS | P22-07 fixtures + tests |
| Immediate Response targets exact Event Participant | PASS | P22-07 + graph validator |
| Non-consequence Response requires no Determination | PASS | P22-07 fixtures + tests |
| Communication recipient Actor and exact endpoint resolve | PASS | P22-07 + graph validator |
| Completed Communication preserves `participation = not_established` | PASS | P22-07 fixtures + tests |
| Communication resolves exact same-Event Response relation | PASS | P22-07 + graph validator |
| No Response effectiveness or downstream Outcome is fabricated | PASS | P22-07 fixtures + tests |
| P22-08 multi-Event Support Process positive-Outcome scenario exists | PASS | P22-08 fixture directory |
| Support Process initiation resolves exact Event A | PASS | P22-08 + graph validator |
| Later Event B remains separately owned while contributing exact Outcome context | PASS | P22-08 + graph validator |
| Support Need remains bounded planning rather than diagnosis | PASS | P22-08 fixtures + tests |
| Goal criteria and measurement approach remain planning only | PASS | P22-08 fixtures + tests |
| Support resolves exact Need, Goal, target, and provider participants | PASS | P22-08 + graph validator |
| Planned recurring schedule does not substitute for Implementation | PASS | P22-08 fixtures + tests |
| Two actual Implementations resolve exact Support plan | PASS | P22-08 + graph validator |
| Fidelity scopes the exact Implementations and same exact Support | PASS | P22-08 + graph validator |
| Fidelity result is adherence-only and does not claim effectiveness | PASS | P22-08 fixtures + tests |
| Completed Follow-Up resolves exact owner and related records | PASS | P22-08 + graph validator |
| Follow-Up completion remains separate from Outcome | PASS | P22-08 fixtures + tests |
| Positive Outcome is separately attributable and evidence-bound | PASS | P22-08 + graph validator |
| Outcome basis includes exact records from both Event works and Support Process | PASS | P22-08 + graph validator |
| Outcome explicitly avoids causal-effect claim | PASS | P22-08 fixtures + tests |
| Positive Outcome does not auto-complete Support Process | PASS | P22-08 fixtures + tests |

| P22-09 inconclusive/adverse downstream-evaluation scenario exists | PASS | P22-09 fixture directory |
| First Outcome uses `support_response_review / unable_to_determine` | PASS | P22-09 fixtures + tests |
| Inconclusive Outcome preserves explicit insufficient-observation limitation | PASS | P22-09 fixtures + tests |
| Missing evidence remains distinct from a negative or adverse result | PASS | P22-09 fixtures + tests |
| Later Outcome uses `unintended_or_adverse_effect_review / change_observed` | PASS | P22-09 fixtures + tests |
| Adverse/unintended review carries explicit bounded direct-observation coverage | PASS | P22-09 fixtures + tests |
| Later changed question/timeframe creates a separate active Outcome | PASS | P22-09 fixtures + tests |
| Later Outcome does not supersede/correct the earlier valid timeframe | PASS | P22-09 fixtures + tests |
| Temporal overlap with Support is explicitly noncausal | PASS | P22-09 fixtures + tests |
| Event count is not treated as proof of improvement or deterioration | PASS | P22-09 fixtures + tests |
| Inconclusive/adverse Outcomes do not auto-complete Support Process | PASS | P22-09 fixtures + tests |

| P22-10 Reentry/Repair scenario exists | PASS | P22-10 fixture directory |
| Two participant Accounts remain separate perspectives rather than findings/admissions | PASS | P22-10 fixtures + tests |
| Immediate Response and in-person Communication remain distinct exact context | PASS | P22-10 fixtures + tests |
| Reentry preserves planned return/elements separately from actual completion | PASS | P22-10 fixtures + tests |
| Reentry initiates from exact same-Event Response | PASS | P22-10 fixtures + tests |
| Reentry completion does not encode safety clearance or rehabilitation | PASS | P22-10 fixtures + tests |
| Repair preserves `participated` and `declined` as neutral workflow states | PASS | P22-10 fixtures + tests |
| Completed Repair action is agreed/responsible only by the participating student | PASS | P22-10 fixtures + tests |
| Repair exact context preserves both Accounts and Communication | PASS | P22-10 fixtures + tests |
| Repair completion does not imply admission, remorse, forgiveness, or restored relationship | PASS | P22-10 fixtures + tests |
| Later Follow-Up reviews exact Reentry/Repair without manufacturing Outcome | PASS | P22-10 + graph validator |


| P22-11 cross-year Support continuation scenario exists | PASS | P22-11 fixture directory |
| Predecessor and successor are distinct Support Process work roots | PASS | P22-11 fixtures + tests |
| Successor has a new owning class and school year | PASS | P22-11 fixtures + tests |
| `continues_from` resolves exact predecessor Support Process | PASS | P22-11 + graph validator |
| Cross-year continuation is not represented as supersession | PASS | P22-11 fixtures + tests |
| Scenario contains no Record Migration or Ownership Correction | PASS | P22-11 fixtures + tests |
| New year creates new Support Process Participant identities | PASS | P22-11 fixtures + tests |
| Repeated local student ID/display name remains class-qualified, not global identity | PASS | P22-11 roster contexts + tests |
| New-year Need/Goal/Support identities are distinct from predecessor children | PASS | P22-11 fixtures + tests |
| New-year Support procedure is reviewed/adapted rather than cloned predecessor payload | PASS | P22-11 fixtures + tests |
| New-year Implementation and Observation use new current-year identities | PASS | P22-11 fixtures + tests |
| Historical Outcome exact basis remains pinned to predecessor work root | PASS | P22-11 fixtures + tests |
| New-year Outcome is a distinct bounded evaluation using successor-year evidence | PASS | P22-11 fixtures + tests |
| Continuation does not silently retarget predecessor exact references | PASS | P22-11 fixtures + tests |
| Slice 11 requires no public schema or ADR change | PASS | existing `support_process@1` `continues_from` contract + Slice 11 file inventory |

| P22-12 participant-specific privacy projection/export scenario exists | PASS | P22-12 fixture directory |
| Exact focal participant and exact work-scoped purpose are preserved | PASS | P22-12 projection/export refs + tests |
| Projection remains noncanonical and does not rewrite source records | PASS | P22-12 projection-decision fixture + tests |
| `included` / `withheld` / `absent` / `unavailable` / `requires_manual_review` remain distinct | PASS | P22-12 projection decision + tests |
| Stable native IDs are not emitted as pseudonyms | PASS | P22-12 output no-leakage tests |
| Third-party Account free text is manually reviewed and withheld without paraphrase | PASS | P22-12 projection decision + tests |
| Student-facing purpose is separate from exact export authorization | PASS | P22-12 authorization context + tests |
| Safe Account projection does not authorize raw source-artifact bytes | PASS | P22-12 Account/source-artifact authorization + tests |
| Export source inventory contains only contributing exact representations | PASS | P22-12 deliberate export + graph validator |
| Source representation digest/length evidence recomputes from fixture bytes | PASS | P22-12 graph validator + tests |
| Projection policy/rule/decision digests recompute from exact fixture bytes | PASS | P22-12 tests |
| Deliberate export output path/digest/length matches committed CSV bytes | PASS | P22-12 graph validator + tests |
| Export generation does not claim disclosure/delivery/read/consent | PASS | P22-12 export + tests |
| Slice 12 requires no public schema or ADR change | PASS | existing #21 contracts + Slice 12 file inventory |

| P22-13 rebuildable-derived/retention-custody scenario exists | PASS | P22-13 fixture directory |
| Canonical Work Relationship and Dependency remain forward authority | PASS | P22-13 canonical records + tests |
| Eight required representative views rebuild deterministically | PASS | P22-13 derived view expectation + tests |
| Incoming-reference and Work Relationship reverse indexes are derived from exact forward edges | PASS | P22-13 builder + tests |
| Replacement/current frontier derives exact Account successor without rewriting predecessor | PASS | P22-13 Account pair + tests |
| Dependency graph preserves exact target without silent successor following | PASS | P22-13 Dependency + tests |
| Lifecycle timeline follows `previous_transition` chain rather than timestamp sorting | PASS | P22-13 Lifecycle Transition pair + tests |
| Work/class summaries remain nonauthoritative and class summary is not a student dossier | PASS | P22-13 derived expectations + tests |
| Participant-specific history remains exact work scoped | PASS | P22-13 derived expectations + tests |
| `source_snapshot@1` binds truthful exact canonical source fingerprints | PASS | P22-13 source snapshot + tests |
| `derived_index_metadata@1` binds complete immutable generation and truthful data fingerprint | PASS | P22-13 metadata + tests |
| `derived_current_pointer@1` explicitly selects generation without freshness claim | PASS | P22-13 pointer + tests |
| Missing/deleted derived state does not imply empty graph or canonical deletion | PASS | P22-13 rebuild tests |
| Unchanged source rebuild is semantically deterministic | PASS | P22-13 rebuild digest test |
| Changed source fingerprint invalidates prior snapshot | PASS | P22-13 changed-source simulation test |
| `derived_cache` retention remains distinct from `canonical_behavior_support` | PASS | P22-13 retention expectation + tests |
| `export_bytes` remains distinct from `export_provenance` | PASS | P22-13 retention expectation + tests |
| Core retained-source custody remains outside Portia destruction authority | PASS | P22-13 foreign-custody context + tests |
| No legal retention duration or Portia Sunset public record is invented | PASS | P22-13 retention expectation + tests |
| Slice 13 requires no public schema or ADR change | PASS | existing Issue #13/#21 contracts + Slice 13 file inventory |

| P22-14 coordinated operation/recovery scenario exists | PASS | P22-14 fixture directory |
| Material Work Relationship correction preserves superseded predecessor and active successor | PASS | P22-14 canonical records + tests |
| Operation Journal revision 1 records successful preflight before any canonical mutation | PASS | P22-14 journal r1 + tests |
| Exact predecessor bytes and absent successor state are fingerprinted during preflight | PASS | P22-14 preflight context + journal r1 + tests |
| Operation and work locks use deterministic accepted lock-key identities | PASS | P22-14 lock fixtures + tests |
| Candidate successor and predecessor replacement are staged before canonical acceptance | PASS | P22-14 journal r2 + staged candidates + tests |
| Interrupted revision records accepted successor separately from remaining predecessor write | PASS | P22-14 journal r3 + tests |
| Accepted successor remains canonical across interruption and is not deleted as rollback | PASS | P22-14 journals r3-r6 + tests |
| Recovery revision reconciles exact already-accepted successor before completing remaining write | PASS | P22-14 journal r4 + tests |
| Recovery does not issue a second successor creation or duplicate semantic relationship | PASS | P22-14 journal chain + final frontier tests |
| Commit point is reached only after both canonical gates are accepted | PASS | P22-14 journal r5 + tests |
| Completed operation explicitly releases all locks | PASS | P22-14 journal r6 + tests |
| Operation current pointer selects exact terminal journal revision | PASS | P22-14 `operation_current_pointer@1` + tests |
| Operation Journal remains durable operational evidence rather than Work Relationship domain truth | PASS | P22-14 canonical/operational separation + tests |
| Slice 14 requires no public schema or ADR change | PASS | existing Issue #13 contracts + Slice 14 file inventory |

## Positive scenario set complete

P22-01 through P22-14 are implemented and independently inspectable. P22-15 is
a supplemental positive coverage story added by the final contract-family audit
to exercise the ticket-required current forms of Classification, Hypothesis,
and Intervention without changing the semantics of the original 14 stories.

## Supplemental positive Classification / Hypothesis / Intervention coverage

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| Positive corpus exercises `classification@1` | PASS | P22-15 Classification + focused tests |
| Classification remains attributable bounded categorization, not Determination | PASS | P22-15 Classification/Review assertions |
| Positive corpus exercises `hypothesis@1` | PASS | P22-15 Hypothesis + focused tests |
| Hypothesis remains tentative and carries no diagnosis/function/confidence/risk shortcut | PASS | P22-15 semantic assertions |
| Positive corpus exercises `intervention@1` | PASS | P22-15 Intervention + focused tests |
| Intervention resolves exact Support Process Need/Goal/target/provider | PASS | P22-15 graph validation |
| Intervention schedule remains planning distinct from actual Implementation | PASS | P22-15 Intervention + Implementation assertions |
| Graph validator checks Classification/Hypothesis evidence/review and Intervention ownership | PASS | P22-15 focused mutation tests |
| Slice 21 adds no public schema, catalog entry, ADR, or runtime API | PASS | Slice 21 file inventory |


## Graph-invalid identity / ownership / reference batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-001 through G22-010 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 15 tests |
| Every public record in G22-001..010 remains structurally valid | PASS | `test_issue_22_graph_invalid_identity_reference.py` |
| Every case declares one stable primary `G22.*` finding | PASS | scenario/expected descriptors + tests |
| Same-looking record ID in another work does not satisfy exact local resolution | PASS | G22-001 |
| Wrong owning class on an exact work/record reference is rejected | PASS | G22-002 |
| Declared canonical path must agree with record owner identity | PASS | G22-003 |
| Structurally safe but wrong exact contract version is rejected by graph validation | PASS | G22-004 |
| Repeated local student ID across classes does not create global identity | PASS | G22-005 |
| Display-name equality does not create cross-class identity | PASS | G22-006 |
| Actor identity does not replace class-qualified roster identity | PASS | G22-007 |
| Participant-targeted record cannot resolve a participant from another work | PASS | G22-008 |
| Exact foreign/Core reference cannot be substituted with local Portia authority | PASS | G22-009 |
| Exact historical reference cannot silently follow current/successor representation | PASS | G22-010 |
| Resolver-only negative expectations remain closed nonruntime corpus metadata | PASS | G22-005/006/007/009/010 + tests |
| Slice 15 adds no public schema, catalog entry, or ADR | PASS | Slice 15 file inventory |

Graph-invalid progress after Slice 15: **10 / 37 enumerated cases implemented**.

## Graph-invalid lifecycle / correction / dependency batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-011 through G22-016 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 16 tests |
| Every public domain record in G22-011..016 remains structurally valid | PASS | `test_issue_22_graph_invalid_lifecycle_correction.py` |
| G22-012 `derived_current_pointer@1` remains structurally valid | PASS | G22-012 focused structural test |
| Material supersession topology is acyclic | PASS | G22-011 |
| Derived current/replacement selection cannot choose superseded predecessor | PASS | G22-012 |
| Statement of Disagreement remains bound to exact contested record | PASS | G22-013 |
| Required Dependency resolves in the exact declared work | PASS | G22-014 |
| Record Migration cannot retarget historical exact refs after substantive correction | PASS | G22-015 |
| Cross-year Support continuation is a new Support Process with `continues_from`, not migration | PASS | G22-016 |
| Semantic resolver/derived expectations remain closed nonruntime fixture metadata | PASS | G22-012/013/015/016 + tests |
| Slice 16 adds no public schema, catalog entry, or ADR | PASS | Slice 16 file inventory |

Graph-invalid progress after Slice 16: **16 / 37 enumerated cases implemented**;
G22-017 through G22-037 remain planned.


## Graph-invalid evidence / judgment batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-017 through G22-020 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 17 tests |
| Every public record in G22-017..020 remains structurally valid | PASS | `test_issue_22_graph_invalid_evidence_judgment.py` |
| Active reported involvement requires resolvable source Account provenance | PASS | G22-017 |
| Review/judgment evidence remains exact and owner-work scoped | PASS | G22-018 |
| Active import/paper-origin Determination requires accepted review history | PASS | G22-019 |
| Imported/source assertion does not become a Portia Determination merely by mapping or attribution fields | PASS | G22-020 |
| Semantic no-inference assertion remains closed nonruntime fixture metadata | PASS | G22-020 + focused test |
| Slice 17 adds no public schema, catalog entry, or ADR | PASS | Slice 17 file inventory |

Graph-invalid progress after Slice 17: **20 / 37 enumerated cases implemented**;
G22-021 through G22-037 remain planned.


## Graph-invalid Response / Support / Outcome batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-021 through G22-025 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 18 tests |
| Every public record in G22-021..025 remains structurally valid | PASS | `test_issue_22_graph_invalid_response_support_outcome.py` |
| Implementation plan refs resolve inside the owning Support Process | PASS | G22-021 |
| Fidelity implementation scope resolves inside the owning Support Process and remains bound to its exact plan | PASS | G22-022 |
| Support Process Outcome target resolves inside the owning process | PASS | G22-023 |
| Distinct later-timeframe evaluation receives a new Outcome identity instead of overwriting the earlier Outcome | PASS | G22-024 |
| Cross-year `continues_from` never aliases historical exact refs to the successor | PASS | G22-025 |
| Write/resolution semantic expectations remain closed nonruntime fixture metadata | PASS | G22-024/025 + focused test |
| Slice 18 adds no public schema, catalog entry, or ADR | PASS | Slice 18 file inventory |

Graph-invalid progress after Slice 18: **25 / 37 enumerated cases implemented**;
G22-026 through G22-037 remain planned.



## Graph-invalid Paper / Import / Operations batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-026 through G22-029 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 19 tests |
| Every public domain and operational contract fixture in G22-026..029 remains structurally valid | PASS | `test_issue_22_graph_invalid_paper_import_operations.py` |
| Unchanged retained-source replay cannot create a second accepted domain identity for one accepted proposal | PASS | G22-026 |
| Capture materialization requires a resolvable accepted Capture Review | PASS | G22-027 |
| Committed/completed Operation Journal accepted writes reconcile to exact canonical readback | PASS | G22-028 |
| Restart reconciles an already accepted durable semantic write instead of replaying it | PASS | G22-029 |
| Replay/review/restart semantic expectations remain closed nonruntime fixture metadata | PASS | G22-026/027/029 + focused test |
| Operational public contracts are validated in operational storage scope rather than as domain records | PASS | graph-validation helper + G22-028/029 |
| Slice 19 adds no public schema, catalog entry, or ADR | PASS | Slice 19 file inventory |

Graph-invalid progress after Slice 19: **29 / 37 enumerated cases implemented**;
G22-030 through G22-037 remain planned.


## Graph-invalid Privacy / Export / Derived / Custody batch

| Acceptance item | Status | Evidence |
| --- | --- | --- |
| G22-030 through G22-037 are registered as `graph_invalid` scenarios | PASS | `corpus.json` + Slice 20 tests |
| `planned_graph_invalid_scenarios` is empty | PASS | `corpus.json` + focused inventory test |
| Every public domain/export/derived contract fixture remains structurally valid | PASS | `test_issue_22_graph_invalid_privacy_export_derived_custody.py` |
| Participant-specific projection does not leak unrelated identity/stable IDs/unsafe Account content | PASS | G22-030 |
| `withheld`, `unavailable`, and `absent` remain semantically distinct | PASS | G22-031 |
| Export inventory binds exact consumed representation rather than a successor | PASS | G22-032 |
| Export output path remains PII-minimized as well as export-ID scoped | PASS | G22-033 |
| Derived incoming-reference index agrees with canonical forward references | PASS | G22-034 |
| Derived replacement/current view excludes superseded predecessor | PASS | G22-035 |
| Changed canonical source invalidates stale Source Snapshot before acceptance | PASS | G22-036 |
| Portia does not claim foreign/external destruction without owner verification | PASS | G22-037 |
| Derived public contracts are structurally validated in derived/non-authoritative scope | PASS | graph-validation helper + G22-036 |
| Slice 20 adds no public schema, catalog entry, or ADR | PASS | Slice 20 file inventory |

Graph-invalid progress after Slice 20: **37 / 37 enumerated cases implemented**.
The enumerated graph-invalid corpus is complete.

## Pending cross-cutting completion

- [x] At least 25 individually schema-valid / graph-invalid scenarios exist (37 / 37 implemented).
- [x] Every graph-invalid scenario declares a stable primary `G22.*` finding (G22-001..037 complete).
- [x] Current public-contract coverage matrix has no remaining `planned` family — 67 relevant record/operational families receive explicit final disposition.
- [x] Graph-invalid matrix is complete (G22-001..037).
- [x] Paper/import byte fixtures use real digest/length evidence where required — P22-05 retained-source bytes, P22-06 source snapshots, P22-12 export/source fingerprints, and P22-13 source snapshots are recomputed by executable tests.
- [x] Privacy/export no-leakage story is complete.
- [x] Derived-state delete/rebuild/staleness proof is complete.
- [x] Coordinated recovery story is complete.
- [x] Initial local schema-validation baseline is recorded from actual execution — pristine starting commit: 1095/1095 OK.
- [x] Final repository drift check is recorded — Portia/Core unchanged; Vitrine/Quillan sibling drift documented as non-blocking.
- [x] Full Issue #22 validation and closeout evidence is recorded — 356/356 Issue #22 regression and 1451/1451 complete schema-validation gate on the committed PR tree before the PR-review traceability repair.
- [x] Handoff package for #23 is complete — `docs/validation/issue-22-handoff-to-issue-23.md` plus final coverage, graph-invalid, end-to-end validation, acceptance, and repository-checkpoint evidence.


## Final closeout evidence (authoritative)

Historical slice-progress notes above are retained as implementation history. The
following state supersedes any earlier wording such as “remain planned” or
intermediate counts.

| Closeout item | Final status | Evidence |
| --- | --- | --- |
| Positive corpus | PASS | 15 scenarios, P22-01..P22-15; zero planned positive scenarios |
| Graph-invalid corpus | PASS | 37 scenarios, G22-001..G22-037; zero planned graph-invalid scenarios |
| Current Classification/Hypothesis/Intervention positive coverage | PASS | P22-15 + `test_issue_22_classification_hypothesis_intervention.py` |
| Current Operation Journal/Lock version coverage | PASS | P22-14 uses `operation_journal@2` and `operation_lock@2` |
| Complete graph-invalid traceability | PASS | `issue-22-graph-invalid-matrix.md` + exact-finding-set tests |
| Public catalog coverage disposition | PASS | `issue-22-contract-coverage-matrix.md` + `tests/fixtures/issue_22/contract-coverage.json`; 161/161 current catalog families machine-mapped, no `planned` state |
| Pristine implementation-start baseline | PASS | exact start commit; 1095/1095 |
| Final Portia/Core drift | PASS | both unchanged from starting anchors |
| Sibling drift | REVIEWED / NON-BLOCKING | Vitrine and Quillan moved in sibling-owned workflow/release work; final hashes recorded |
| Issue #22 regression | PASS | 356/356 after closeout/ADR wording repair |
| Complete schema-validation suite | PASS | 1451/1451 after closeout/ADR wording repair |
| Public schema/catalog/ADR delta | NONE | Issue #22 remains integration/test evidence only |
| Required end-to-end validation record | PASS | `issue-22-end-to-end-validation.md` |
| Post-review repaired-head execution | PASS | 11/11 closeout; 356/356 Issue #22; 1451/1451 full suite; `git diff --check` clean |
| #23 handoff | READY FOR UPDATED-HEAD REVIEW | dedicated handoff document + all closeout evidence; repaired-head confirmation gates passed |

The PR-review traceability repair adds no scenario-semantic, schema, catalog, or
runtime change. It adds the ticket-required end-to-end validation record, a
machine-readable mapping of all 161 current catalog families, stronger assertions
inside the existing 11-test closeout module, and final documentation-state
normalization.

Before merge/Issue #23 entry, the repaired head must retain:

```text
11 / 11 closeout tests
356 / 356 Issue #22 regression tests
1451 / 1451 complete schema-validation tests
git diff --check clean
```
