# Issue #22 Contract Coverage Matrix

**Status:** Complete
**Date:** 2026-08-17

This matrix is the final Issue #22 disposition of the current public **record/operational families** that can independently participate in Portia graphs. It intentionally distinguishes those families from reusable identifiers, references, primitive/common schemas, targets, attribution fragments, and embedded value objects. The latter are exercised transitively by the record fixtures and by their original focused validation suites; requiring an independent end-to-end story for every identifier or helper schema would not be meaningful integration coverage.

Allowed dispositions for relevant record/operational families are:

```text
positive_graph
graph_invalid
existing_focused_fixture_only
foreign_context_only
not_applicable_with_rationale
```

No relevant family remains `planned`.

## Positive end-to-end graph families

| Contract family | Current exercised version | Disposition | Scenario(s) | Integration evidence |
| --- | --- | --- | --- | --- |
| `event` | 2 | positive_graph | P22-01, P22-02, P22-05, P22-06, P22-07, P22-09, P22-10, P22-12, P22-13, P22-14, P22-15 | Event-owned graph roots; neutral, disputed, imported, corrected, privacy, recovery, and support-initiation stories |
| `event_participant` | 3 | positive_graph | P22-01, P22-02, P22-03, P22-05, P22-06, P22-07, P22-09, P22-10, P22-12, P22-13, P22-14, P22-15 | exact work-local participant identity; cross-class source-roster behavior remains explicit |
| `event_participant_role` | 3 | positive_graph | P22-01, P22-02, P22-07 | relationship semantics without fault/guilt inference |
| `account` | 2 | positive_graph | P22-02, P22-10, P22-12, P22-13, P22-15 | firsthand/source-attributed evidence, conflicting perspectives, privacy filtering |
| `observation` | 2 | positive_graph | P22-01, P22-02, P22-08, P22-09, P22-11, P22-13, P22-15 | direct evidence distinct from Accounts and judgments |
| `review` | 1 | positive_graph | P22-02, P22-09, P22-10, P22-15 | bounded human review with exact evidence/target scope |
| `classification` | 1 | positive_graph | P22-15 | human-selected contextual categorization; no weight/proof/diagnosis claim |
| `hypothesis` | 1 | positive_graph | P22-15 | tentative review-bound explanation with supporting/contrary evidence roles |
| `determination` | 1 | positive_graph | P22-02 | bounded insufficient-information judgment; source assertions do not become decisions |
| `response` | 1 | positive_graph | P22-07, P22-10 | immediate action distinct from Support and effectiveness |
| `communication` | 1 | positive_graph | P22-07, P22-10 | attributable communication act distinct from recipient participation/delivery |
| `actor` | 1 | positive_graph | P22-07 | workspace-scoped external/family identity without roster substitution |
| `actor_contact_point` | 1 | positive_graph | P22-07 | contact endpoint distinct from identity, consent, delivery, or authorization |
| `actor_student_relationship` | 1 | positive_graph | P22-07 | reviewed local relationship assertion without legal-authority inference |
| `support_process` | 1 | positive_graph | P22-08, P22-09, P22-11, P22-15 | bounded class-owned Support Process; cross-year continuation uses a new work root |
| `support_process_participant` | 1 | positive_graph | P22-08, P22-11, P22-15 | exact supported-person/provider process participants |
| `support_need` | 1 | positive_graph | P22-08, P22-11, P22-15 | bounded planning need, not a judgment or diagnosis |
| `support_goal` | 1 | positive_graph | P22-08, P22-11, P22-15 | planning criteria distinct from outcome |
| `support` | 1 | positive_graph | P22-08, P22-11 | planned Support distinct from actual Implementation |
| `intervention` | 1 | positive_graph | P22-15 | recurring Intervention plan distinct from actual occurrence |
| `implementation` | 1 | positive_graph | P22-08, P22-11, P22-15 | actual occurrence bound to an exact same-process plan |
| `fidelity` | 1 | positive_graph | P22-08 | adherence/implementation evaluation, not effectiveness |
| `follow_up` | 1 | positive_graph | P22-08 | completed follow-up distinct from favorable Outcome |
| `outcome` | 1 | positive_graph | P22-08, P22-09, P22-11 | new bounded attributable evaluation; positive/inconclusive/adverse without causal inference |
| `reentry` | 1 | positive_graph | P22-10 | plan/completion without safety-clearance or rehabilitation overclaim |
| `repair` | 1 | positive_graph | P22-10 | offer/participation/action without admission, remorse, forgiveness, or restored-relationship inference |
| `lifecycle_transition` | 1 | positive_graph | P22-04, P22-13, P22-14 | append-preserving status history and material-successor topology |
| `statement_of_disagreement` | 1 | positive_graph | P22-04 | exact contested-predecessor binding without truth adjudication |
| `work_relationship` | 2 | positive_graph | P22-11, P22-13, P22-14 | canonical forward relationship and cross-year continuation/context topology |
| `dependency` | 1 | positive_graph | P22-13 | exact canonical dependency; derived reverse/index views remain nonauthoritative |
| `operation_journal` | 2 | positive_graph | P22-14 | current version; prepared→staged→committing→recovering→committed→completed recovery evidence |
| `operation_current_pointer` | 1 | positive_graph | P22-14 | explicit terminal revision selection; no newest-revision inference |
| `operation_lock` | 2 | positive_graph | P22-14 | current version; deterministic operation/work lock identity and release evidence |
| `source_snapshot` | 1 | positive_graph | P22-13 | truthful snapshot of exact canonical source representations |
| `derived_index_metadata` | 1 | positive_graph | P22-13 | immutable rebuild-generation metadata and exact source/data fingerprints |
| `derived_current_pointer` | 1 | positive_graph | P22-13 | explicit derived-generation selection without authority/freshness claim |
| `capture_batch` | 1 | positive_graph | P22-05 | paper capture operation root |
| `page_target` | 1 | positive_graph | P22-05 | exact pre-print Core/PDS2 route and layout target |
| `page_record` | 1 | positive_graph | P22-05 | returned physical-page/source processing record |
| `paper_interpretation` | 1 | positive_graph | P22-05 | machine candidate, not confirmed domain fact |
| `capture_proposal` | 1 | positive_graph | P22-05 | noncanonical field-binding proposal |
| `capture_review` | 1 | positive_graph | P22-05 | human capture/materialization gate, distinct from domain Review |
| `capture_materialization` | 1 | positive_graph | P22-05 | receipt only after canonical record acceptance; replay-safe |
| `import_batch` | 1 | positive_graph | P22-06 | structured-source snapshot/mapping attempt |
| `import_source_record` | 1 | positive_graph | P22-06 | source-system record/assertion preserved as source context |
| `import_proposal` | 1 | positive_graph | P22-06 | noncanonical mapping proposal |
| `import_review` | 1 | positive_graph | P22-06 | human import staging gate, not domain judgment |
| `import_materialization` | 1 | positive_graph | P22-06 | replay-safe receipt after canonical Event acceptance |
| `export_source_inventory` | 1 | positive_graph | P22-12 | exact contributing immutable representations and truthful fingerprints |
| `deliberate_export` | 1 | positive_graph | P22-12 | privacy decision + authorization + immutable output provenance; generation != disclosure |

## Existing focused-fixture-only families

These are current public record families, but inserting them into an ordinary positive story would be artificial or would weaken the very distinction the corpus is meant to preserve. Their accepted dedicated suites remain the right positive/invalid evidence, while Issue #22 graph-invalid cases exercise the relevant cross-record misuse where applicable.

| Contract family | Current version | Disposition | Existing evidence | Why no synthetic positive story is forced |
| --- | --- | --- | --- | --- |
| `actor_roster_student_collision` | 1 | existing_focused_fixture_only | Issue #14 Actor Directory fixtures | collision record is exceptional identity-integrity evidence; P22-03/G22-005..007 exercise the integration invariant without manufacturing a positive collision record |
| `actor_directory_lifecycle_transition` | 1 | existing_focused_fixture_only | Issue #14 Actor Directory lifecycle fixtures | Actor Directory lifecycle is workspace-scoped and already has dedicated structural/application coverage |
| `actor_directory_lifecycle_history_correction` | 1 | existing_focused_fixture_only | Issue #14 Actor Directory lifecycle fixtures | specialized Actor Directory history correction is not needed to tell a representative teacher-local positive story |
| `actor_directory_amendment` | 1 | existing_focused_fixture_only | Issue #14 Actor Directory correction fixtures | Actor Directory-specific amendment remains focused coverage |
| `actor_directory_record_migration` | 1 | existing_focused_fixture_only | Issue #14 / Issue #12 migration fixtures | specialized Actor Directory representation migration; negative corpus protects migration-vs-correction semantics |
| `actor_directory_exceptional_removal` | 1 | existing_focused_fixture_only | Issue #14 / Issue #12 removal fixtures | exceptional, non-routine removal must not be normalized into an ordinary positive story |
| `lifecycle_history_correction` | 1 | existing_focused_fixture_only | Issue #12 lifecycle/correction fixtures | history-repair administrative record is covered in focused validation; P22-04/P22-14 exercise ordinary append-preserving correction |
| `amendment` | 1 | existing_focused_fixture_only | Issue #12 amendment fixtures | P22-04 uses Statement of Disagreement for its coherent story; forcing an Amendment as well would be redundant; dedicated Issue #12 fixtures cover Amendment semantics |
| `record_migration` | 1 | existing_focused_fixture_only | Issue #12 migration fixtures | migration is representation change, not semantic correction; G22-015/G22-016 guard misuse |
| `ownership_correction` | 1 | existing_focused_fixture_only | Issue #12 ownership-correction fixtures | ownership repair is an exceptional administrative correction; canonical owner/path invariants are exercised by G22-002/G22-003 |
| `exceptional_removal` | 1 | existing_focused_fixture_only | Issue #12 exceptional-removal fixtures | explicitly exceptional and distinct from routine retention disposition |
| `integrity_finding` | 2 | existing_focused_fixture_only | Issue #13 + Issue #14 actor-aware operation fixtures | diagnostic administrative evidence, not ordinary domain judgment; ordinary uncertainty must not manufacture findings |
| `quarantine_record` | 2 | existing_focused_fixture_only | Issue #13 + Issue #14 actor-aware operation fixtures | exceptional isolation mechanism, not an ordinary review/lifecycle state |
| `quarantine_current_pointer` | 1 | existing_focused_fixture_only | Issue #13 coordinated-operation fixtures | administrative current-selection helper for quarantine history |
| `finding_acknowledgement` | 1 | existing_focused_fixture_only | Issue #13 integrity-administration fixtures | administrative acknowledgement of a finding; no representative domain story requires one |
| `finding_suppression` | 1 | existing_focused_fixture_only | Issue #13 integrity-administration fixtures | administrative suppression decision with dedicated focused invariants |
| `finding_suppression_current_pointer` | 1 | existing_focused_fixture_only | Issue #13 integrity-administration fixtures | administrative selection helper for suppression history |

## Graph-invalid invariant coverage

The negative corpus does not substitute for the family dispositions above. It proves application invariants that JSON Schema alone cannot express. The authoritative row-by-row mapping is `docs/validation/issue-22-graph-invalid-matrix.md`.

```text
G22-001..010  exact identity / ownership / reference resolution
G22-011..016  lifecycle / correction / continuation
G22-017..020  evidence / review / judgment
G22-021..025  Support / Fidelity / Outcome locality and identity
G22-026..029  paper/import materialization and operation replay
G22-030..037  privacy/export / derived state / custody
```

All 37 cases are `graph_invalid`; every public Portia record in those scenarios remains structurally valid.

## Supporting public helpers and embedded contracts

Identifiers, exact/local/module references, target unions, timestamps, digests/fingerprints, `creation_source`, attribution fragments, `person_display_snapshot`, `evidence_time`, `planned_schedule`, and other embedded/common contracts are **not independent graph-family coverage units**. Their independent-story disposition is `not_applicable_with_rationale`; they are nevertheless exercised transitively throughout P22-01..P22-15 and the original Issue #11–#21 focused suites.

This scope rule prevents a misleading count in which, for example, `portia_event_id@1` is treated as though it were an independently persisted domain record alongside `event@2`.

## Foreign/context-only contracts

Core roster/class identity, Core PDS2 routing/retained-source context, sibling-module exact references, and external custody/disclosure state are `foreign_context_only`. Issue #22 commits only the minimum synthetic context needed to test Portia semantics and never republishes those foreign records as Portia authority.

P22-05, P22-06, P22-13, G22-009, and G22-037 are the principal boundary stories. Vitrine is used only as a fixture/validation precedent and as synthetic foreign-custody context where explicitly declared.

## Conceptual retention / Sunset boundary

Retention classes and the future Sunset orchestration boundary are architectural policy concepts from Issue #21 rather than new standalone public Portia record families. Their independent-record disposition is `not_applicable_with_rationale`. P22-13 exercises retention/custody expectations and G22-037 proves that Portia cannot claim destruction of Core, Vitrine, email, download, backup, or other foreign copies without owner verification.

## Current-version normalization

P22-14 uses `operation_journal@2` and `operation_lock@2`, the highest current catalog versions. Version 2 preserves ordinary work/record recovery semantics while adding Actor Directory target shapes. `operation_current_pointer@1` remains the current pointer contract. Older cataloged versions remain valid historical contracts; Issue #22 does not mutate or republish them.

## Completion statement

The final relevant record/operational family inventory contains **67 explicit dispositions: 50 `positive_graph` and 17 `existing_focused_fixture_only`**. No relevant family is left in a `planned` state. Foreign/context-only and helper/embedded scopes are documented separately above rather than being miscounted as Portia-owned persisted record families.
