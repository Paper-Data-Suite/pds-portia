# Issue #22 Handoff to Issue #23

**Source:** #22 — Build representative end-to-end synthetic contract examples
**Consumer:** #23 — final Portia foundations architecture audit
**Date:** 2026-08-17
**Status:** Ready for architecture-audit consumption after Slice 23 validation

## What #23 receives

Issue #22 provides a deterministic, network-independent, repository-local
integration corpus containing:

```text
15 positive synthetic graphs      P22-01..P22-15
37 schema-valid graph-invalid      G22-001..G22-037
52 total scenarios
0 planned scenarios
```

The corpus descriptor is:

```text
tests/fixtures/issue_22/corpus.json
```

The test-only application validator is:

```text
tests/schema_validation/issue_22_graph_validation.py
```

The positive stories, graph-invalid matrix, contract coverage matrix, initial and
final checkpoints, and acceptance matrix are the principal human-audit surfaces.

## Positive-story map

| Scenario | Architectural pressure exercised |
| --- | --- |
| P22-01 | neutral/positive Event, exact roster-qualified participant identity, Observation without misconduct inference |
| P22-02 | multi-participant conflicting Accounts, reported-vs-observed evidence, bounded insufficient-information Determination |
| P22-03 | cross-class identity and repeated local-ID/display-name collision resistance |
| P22-04 | immutable predecessor, supersession, disagreement, exact historical reference stability |
| P22-05 | paper/PDS2 retained-source boundary, proposal/review/materialization, truthful source bytes |
| P22-06 | structured import staging, source assertion vs Portia truth, replay idempotency |
| P22-07 | immediate Response, Actor/Contact Point/relationship boundaries, family Communication |
| P22-08 | Support planning vs Implementation vs Fidelity vs Follow-Up vs positive noncausal Outcome |
| P22-09 | positive/inconclusive/adverse downstream evaluation without causal inference or identity overwrite |
| P22-10 | Reentry/Repair completion without clearance, remorse, forgiveness, or restoration overclaim |
| P22-11 | cross-year Support continuation as new work, new participant/plan/evaluation identities, no migration |
| P22-12 | participant-specific privacy projection and deliberate export with exact source inventory and no third-party leakage |
| P22-13 | rebuildable derived views, exact source snapshots, retention classes, Portia-vs-foreign custody |
| P22-14 | coordinated append-preserving correction, current Operation Journal/Lock versions, interruption/restart/reconciliation |
| P22-15 | Review → human Classification + tentative Hypothesis and separate Support Process → Intervention → Implementation |

## Negative-story map

Use `docs/validation/issue-22-graph-invalid-matrix.md` as the 37-row index. Each
case names one principal defect and stable primary `G22.*` finding. #23 should
sample the implementation behind each finding family rather than treating a green
schema-validation result as proof of graph correctness.

High-value audit clusters are:

```text
identity and exact reference resolution             G22-001..010
correction, migration, continuation, derived current G22-011..016
provenance, evidence, review, human judgment          G22-017..020
Support/Fidelity/Outcome owner and identity locality  G22-021..025
paper/import acceptance and operation replay          G22-026..029
privacy/export, derived staleness, foreign custody    G22-030..037
```

## Architecture invariants #23 should challenge

1. **Authority remains distributed.** Core owns shared roster/PDS2 infrastructure;
   Portia owns its teacher-local domain records; sibling/external custody is not
   silently converted into Portia authority.
2. **Exact identity dominates convenience matching.** Owning class/work,
   contract version, exact record identity, roster qualification, and canonical
   path must agree. Display names and repeated local student IDs never establish
   identity.
3. **Evidence and judgment remain distinct.** Account, Observation, Review,
   Classification, Hypothesis, and Determination do not collapse into each other;
   imports/machine interpretations do not manufacture human judgments.
4. **Response/support/evaluation phases remain distinct.** Response != Support;
   plan != Implementation; Implementation != Fidelity; Fidelity != Outcome;
   completed Follow-Up/Reentry/Repair does not manufacture favorable semantic
   conclusions.
5. **Correction is append-preserving.** Material corrections preserve exact
   predecessors and historical references. Migration is not semantic correction;
   ownership correction is not a filesystem move; cross-year continuation is a
   new work relationship.
6. **Operations remain evidence, not domain truth.** Journal/Lock records
   coordinate writes and recovery; committed state must reconcile against
   canonical readback; restart does not replay already accepted semantic writes.
7. **Derived state remains rebuildable and nonauthoritative.** Missing/stale
   caches never mean empty canonical truth; reverse indexes must agree with
   canonical forward edges; current views cannot retain superseded predecessors.
8. **Privacy/export semantics fail closed.** Withheld != absent; unavailable !=
   false; stable IDs are not safe pseudonyms; export provenance binds exact
   consumed representations; output paths are PII-minimized; export generation
   is not disclosure.
9. **Retention is not destruction authority.** Portia retention classification
   does not create legal duration or permission to destroy Core, Vitrine,
   external email/download/backup copies.
10. **Exceptional administration remains exceptional.** Integrity Finding,
    Quarantine, Exceptional Removal, history correction, migration, ownership
    correction, and suppression/acknowledgement records should not appear merely
    because ordinary uncertainty exists.

## Focused-only families

The final coverage matrix deliberately leaves specialized administrative families
in `existing_focused_fixture_only`, not `planned`. #23 should audit the cited Issue
#12–#14 suites together with the relevant G22 misuse cases rather than demand
artificial positive stories for Exceptional Removal, Quarantine, Integrity
Finding, migration, ownership correction, or Actor Directory administrative
records.

## Validation evidence available to #23

```text
pristine pds-portia starting baseline: 1095 / 1095 OK
final Issue #22 regression before closeout docs: 345 / 345 OK
full schema-validation before closeout docs: 1440 / 1440 OK
repeated full schema-validation: 1440 / 1440 OK
```

See:

```text
docs/validation/issue-22-initial-repository-checkpoint.md
docs/validation/issue-22-final-repository-checkpoint.md
docs/validation/issue-22-acceptance-matrix.md
docs/validation/issue-22-contract-coverage-matrix.md
docs/validation/issue-22-graph-invalid-matrix.md
```

## Scope / non-claims

Issue #22 does **not** prove live sibling-module runtime integration, legal or
regulatory compliance, institution-specific retention periods, disclosure/receipt,
clinical or disciplinary truth, or atomic multi-file transactions. It proves that
the accepted Portia foundation can be represented coherently in deterministic
synthetic graphs and that a substantial class of structurally valid graph defects
is detected by explicit application validation.

## #23 entry condition

#23 may begin final approval work when the Slice 23 closeout test and the complete
schema-validation suite pass after these evidence documents are applied. Any #23
finding that contradicts a corpus invariant should be treated as an architecture
finding, not patched by weakening a fixture expectation.
