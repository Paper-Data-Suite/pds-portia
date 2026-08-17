# Issue #22 Graph-Invalid Matrix

**Status:** Complete — 37 / 37 enumerated cases
**Date:** 2026-08-17

This matrix is the stable traceability index for Issue #22 schema-valid / graph-invalid cases. Every row names the scenario descriptor and its declared primary `G22.*` application finding. Individual Portia public records remain structurally valid; the defect exists in combined graph, projection, export, derived-state, or custody semantics.

| Scenario | Story | Primary finding | Principal application defect |
| --- | --- | --- | --- |
| G22-001 | Exact local ref resolves only to same-looking ID in another work | `G22.EVIDENCE.ROLE_BASIS_UNRESOLVED` | The reported-involvement Role in Event A references acct_g22_same_001, but that exact Account exists only in Event B. |
| G22-002 | Work/record ref uses wrong owning class | `G22.EVIDENCE.WRONG_WORK` | An Event-A Review uses an exact Account reference whose work_ref names another owning class/work. |
| G22-003 | Canonical path inconsistent with owner | `G22.OWNERSHIP.CANONICAL_PATH_MISMATCH` | The scenario descriptor declares a canonical work path whose work_id differs from the Event's persisted owner identity. |
| G22-004 | Exact ref requests wrong contract version | `G22.REFERENCE.PARTICIPANT_VERSION_MISMATCH` | The Observation requests Event Participant contract version 2 while the exact fixture representation is version 3. |
| G22-005 | Repeated local student_id merged across classes | `G22.IDENTITY.CROSS_CLASS_LOCAL_ID_MERGE` | A synthetic resolver collapses two class-qualified roster subjects solely because their local student_id strings match. |
| G22-006 | Display-name equality treated as identity | `G22.IDENTITY.DISPLAY_NAME_MERGE` | A synthetic resolver collapses two different class-qualified roster subjects solely because their display snapshots are equal. |
| G22-007 | Actor identity replaces roster identity | `G22.IDENTITY.ACTOR_ROSTER_SUBSTITUTION` | The same-looking roster student is duplicated as a workspace Actor and the synthetic identity resolver claims the Actor can replace the roster identity without an accepted explicit link. |
| G22-008 | Participant-targeted record points outside owning work | `G22.REFERENCE.PARTICIPANT_TARGET_MISSING` | An Observation owned by Event A targets a Participant identity that exists only in Event B. |
| G22-009 | Exact foreign/Core ref silently substituted by Portia record | `G22.REFERENCE.FOREIGN_SUBSTITUTION` | The participant's exact Core-owned roster reference exists, but a synthetic resolver reports a local Portia Actor as its resolved authority. |
| G22-010 | Historical exact ref silently follows successor | `G22.REFERENCE.HISTORICAL_SUCCESSOR_FOLLOW` | A synthetic resolver receives an exact predecessor Work Relationship reference but returns its active successor under follow-current behavior. |
| G22-011 | Material Account supersession graph contains a cycle | `G22.CORRECTION.SUPERSESSION_CYCLE` | Two schema-valid Account replacements supersede each other, forming a material replacement cycle with no acyclic current frontier. |
| G22-012 | Derived current selection chooses superseded predecessor | `G22.DERIVED.CURRENT_SELECTS_PREDECESSOR` | A schema-valid derived current pointer selects a generation whose declared replacement result still chooses the superseded Account predecessor rather than the active successor. |
| G22-013 | Statement of Disagreement resolves to the wrong exact contested record | `G22.CORRECTION.DISAGREEMENT_WRONG_TARGET` | The Statement of Disagreement is structurally valid and resolves to Account B, but the fixture-declared contested representation is the distinct exact Account A. |
| G22-014 | Required Dependency points to a record that exists only in another work | `G22.DEPENDENCY.REQUIRED_TARGET_UNRESOLVED` | A required Dependency names Account acct_g22_014_only_b inside Event A, but that exact Account exists only in Event B. |
| G22-015 | Migration is used to retarget historical exact refs after substantive correction | `G22.MIGRATION.HISTORICAL_RETARGET` | A representation-only Record Migration is used to make an exact historical Event@1 reference resolve to Event@2 even though the accepted summary changed substantively. |
| G22-016 | Cross-year Support continuation is encoded as migration | `G22.SUPPORT.CONTINUATION_ENCODED_AS_MIGRATION` | A new-year Support Process omits continues_from and is instead linked to the predecessor by a Record Migration, collapsing continuation into representation migration. |
| G22-017 | Active reported involvement lacks resolvable source Account provenance | `G22.EVIDENCE.ROLE_BASIS_UNRESOLVED` | The active reported-involvement role carries the structurally required Account basis reference, but that exact Account does not exist in the owning Event. |
| G22-018 | Judgment evidence resolves outside the accepted owning work | `G22.EVIDENCE.WRONG_WORK` | A Determination owned by Event A cites an exact Observation that correctly exists in Event B, outside the Determination's accepted owning Event scope. |
| G22-019 | Imported judgment proposal is activated without required review history | `G22.JUDGMENT.IMPORT_ACTIVE_WITHOUT_REVIEW` | An import-origin Determination is already active even though no review_ref records the required human review gate. |
| G22-020 | Imported source assertion is used as though it were a Portia Determination | `G22.JUDGMENT.IMPORT_ASSERTION_AS_DETERMINATION` | The imported source assertion is copied into an active Determination even though the completed review covered source mapping only and no human decision actually occurred. |
| G22-021 | Implementation plan resolves only in another Support Process | `G22.SUPPORT.IMPLEMENTATION_PLAN_WRONG_PROCESS` | The Implementation is owned by Support Process A but its exact plan_ref names a Support record that exists only under Support Process B. |
| G22-022 | Fidelity scopes an Implementation from another Support Process | `G22.SUPPORT.FIDELITY_IMPLEMENTATION_WRONG_PROCESS` | Fidelity belongs to Support Process A and names plan A, but its one_implementation scope resolves only to an Implementation in Support Process B. |
| G22-023 | Outcome target resolves only in another Support Process | `G22.OUTCOME.TARGET_WRONG_PROCESS` | The Outcome is owned by Support Process A, while its support_process_participant target exists only under Support Process B. |
| G22-024 | Later-timeframe Outcome overwrites an earlier Outcome identity | `G22.OUTCOME.IDENTITY_REUSED_FOR_LATER_EVALUATION` | A persistence operation attempts to write a distinct later-timeframe evaluation over the exact identity of an already accepted Outcome. |
| G22-025 | Cross-year successor silently replaces an exact historical Support Process reference | `G22.SUPPORT.HISTORICAL_PROCESS_SUCCESSOR_FOLLOW` | The resolver receives an exact reference to the 2026-2027 Support Process but silently follows continues_from/current semantics to the distinct 2027-2028 successor. |
| G22-026 | Unchanged import replay creates a second accepted canonical Event | `G22.IMPORT.ACCEPTED_PROPOSAL_DUPLICATE_MATERIALIZATION` | Unchanged retained-source replay materializes a second accepted Event for the same accepted proposal identity instead of reconciling the existing canonical result. |
| G22-027 | Paper materialization claims acceptance without a resolvable review | `G22.PAPER.MATERIALIZATION_REVIEW_UNRESOLVED` | Capture materialization claims an accepted canonical result while its required exact Capture Review does not resolve. |
| G22-028 | Completed operation claims a committed result that canonical readback cannot resolve | `G22.OPERATION.COMMITTED_RESULT_UNRESOLVED` | A completed Operation Journal marks a canonical write accepted even though the exact committed successor record is absent from canonical readback. |
| G22-029 | Restart replays an already committed semantic write | `G22.OPERATION.RESTART_REPLAYS_COMMITTED_WRITE` | Restart replays an already accepted durable semantic write instead of reconciling exact canonical readback and continuing only remaining work. |
| G22-030 | Participant-specific projection leaks unrelated participant data | `G22.PRIVACY.PROJECTION_LEAKS_UNRELATED_DATA` | A participant-specific projection emits an unrelated participant stable ID and unsafe Account content. |
| G22-031 | Projection collapses withheld and unavailable states | `G22.PRIVACY.PROJECTION_STATE_COLLAPSE` | An outward projection collapses privacy/missingness semantics by serializing withheld as absent and unavailable as false. |
| G22-032 | Deliberate export inventory silently binds successor representation | `G22.PRIVACY.EXPORT_INVENTORY_WRONG_REPRESENTATION` | The export actually consumed the historical Account predecessor but its truthful source inventory names the corrected successor instead. |
| G22-033 | Deliberate export output path contains unnecessary identifying labels | `G22.PRIVACY.EXPORT_OUTPUT_PATH_PII` | The deliberate-export path is correctly scoped beneath its opaque export ID but embeds unnecessary synthetic person/class/behavior labels. |
| G22-034 | Derived incoming-reference index disagrees with canonical forward edge | `G22.DERIVED.INCOMING_INDEX_DISAGREES_FORWARD_REFS` | The derived incoming-reference index attributes a canonical Work Relationship to the wrong target work. |
| G22-035 | Derived current view includes both predecessor and successor | `G22.DERIVED.CURRENT_VIEW_INCLUDES_PREDECESSOR` | The derived replacement/current view presents both the superseded Account predecessor and its active successor as current. |
| G22-036 | Stale source-snapshot result is accepted after canonical source change | `G22.DERIVED.STALE_SOURCE_SNAPSHOT_ACCEPTED` | A derived result is accepted from a structurally valid Source Snapshot whose recorded fingerprint no longer matches the current exact canonical Account bytes. |
| G22-037 | Portia disposition claims unverified destruction in foreign custody | `G22.CUSTODY.FOREIGN_DESTRUCTION_UNVERIFIED` | A Portia-local completed disposition is reported as global destruction across Core, Vitrine, email/download, and external backup custody without owner verification. |

## Matrix invariants

- Corpus registration contains exactly G22-001 through G22-037.
- `planned_graph_invalid_scenarios` is empty.
- Every scenario descriptor declares `scenario_kind: graph_invalid`, `expected_graph_result: invalid`, a stable `primary_finding_id`, and an exact `expected_finding_ids` set.
- Focused tests require each scenario to produce exactly its declared finding set; incidental validation order is not treated as the contract.
- Public Portia record fixtures in the negative corpus are structurally validated before application findings are asserted.
- Synthetic semantic contexts are closed, deterministic, test-only, and non-runtime.

## Finding-family summary

```text
G22-001..010  identity / ownership / exact reference
G22-011..016  lifecycle / correction / continuation
G22-017..020  evidence / review / judgment
G22-021..025  response-support / fidelity / outcome
G22-026..029  paper-import / operation replay and commit
G22-030..037  privacy-export / derived state / custody
```

This document is traceability evidence only. The executable source of truth remains the scenario descriptors plus `tests/schema_validation/issue_22_graph_validation.py` and the six `test_issue_22_graph_invalid_*.py` suites.
