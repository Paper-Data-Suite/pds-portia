# Issue #22 Representative Contract Graph Corpus

This directory contains deterministic synthetic fixtures for Portia Issue
#22.

The root descriptor contract:

```text
pds-portia.representative-contract-graph-corpus / 1
```

and scenario descriptor contract:

```text
pds-portia.representative-contract-graph-scenario / 1
```

are development/test metadata only.

They are not public Portia JSON Schemas, are not added to the schema catalog,
and are not production persistence formats.

## Authority

Files under scenario `records/` directories are ordinary public Portia
records and must validate through the exact catalog contract/version declared
by the scenario.

Files under `shared/core-context/` are deliberately small synthetic lookup
context. They are not Core public records and do not replace Core authority.

Expected files and derived summaries are test expectations, not canonical
Portia records.

## Slice 1

Slice 1 implements:

```text
P22-01 — Positive classroom Event
```

It intentionally contains no downstream judgment, Response, Support, or
Outcome record.

Later slices extend the same harness with P22-02 through P22-14 and the
schema-valid/graph-invalid corpus.


## Slice 2

Slice 2 implements:

```text
P22-02 — Multi-participant Event with conflicting Accounts
```

It adds current Account v2 evidence, exact role-basis resolution, completed
Review evidence resolution, and a linked Determination whose bounded outcome is
`insufficient_information`.

No graph-validator rule ranks Account credibility or converts participant role
into fault.


## Slice 3

Slice 3 implements:

```text
P22-03 — Cross-class participant identity
```

The scenario deliberately repeats both the same synthetic `student_id` and the
same display name in two source rosters.

Those values do not merge identities.

The graph harness keys a durable roster-student subject by exact:

```text
class_id + student_id
```

and keeps the one Event canonically owned by its original class.


## Slice 4

Slice 4 implements:

```text
P22-04 — Correction, supersession, disagreement, and exact history
```

Material Account correction is represented by a distinct successor with an
exact `supersedes` edge.

The predecessor is retained as `superseded`; the Statement of Disagreement
and a historical Review stay pinned to that exact predecessor. Lifecycle
transitions reconcile the two Account representations independently.


## Slice 5

Slice 5 implements P22-05 across Capture Batch, Page Target, Core-shaped route
and retained-source context, Page Record, machine Interpretation, Proposal,
human Capture Review, canonical Event, and Capture Materialization receipt.

The source fixture is a real deterministic BMP:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-05-returned-page.bmp
sha256: 75f767d36c35c9d42ed81dd6a2f45c652244c8a66291a50b1228ac32ed125251
bytes: 70
```

Core context remains foreign test authority. Full public Operation Journal
coverage is intentionally deferred to P22-14.


## Slice 6

Slice 6 implements P22-06 across Import Batch, Import Source Record, Import
Proposal, attributable Import Review, canonical Event, Import Materialization,
and a later changed snapshot in which the original source key is absent.

The first deterministic CSV snapshot is:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-06-structured-import-v1.csv
sha256: a18156ec10efd8aa046beb4e94afc30d94c9e3b6101a866fab511399ed93e987
bytes: 158
```

The later header-only snapshot is:

```text
tests/fixtures/issue_22/shared/source-bytes/p22-06-structured-import-v2-missing-row.csv
sha256: 916b6eadc141fffa4789d897f67a57c17b71f6ed7a396a9ac93c0bd451430f9a
bytes: 44
```

The representative graph recomputes Batch/Source/Proposal fixture digests and
preserves the source assertion `source_status = resolved` without translating
it into Portia judgment.


## Slice 7

Slice 7 implements P22-07 across a workspace Actor, Actor Contact Point,
Actor-to-Student Relationship, Event-local immediate Response, and family
Communication.

The Actor aggregate uses accepted workspace storage:

```text
portia/actors/actr_p22_family_001/
```

The communication deliberately records:

```text
act_state = completed
recipient.participation = not_established
```

so a completed communication act never becomes evidence of delivery, read
status, consent, or participation.


## Slice 8

Slice 8 implements P22-08 with two separately owned Events and one Event-
initiated Support Process. The Support Process includes exact participants,
Need, Goal, Support, two actual Implementations, Fidelity, completed Follow-Up,
and a separately authored Outcome.

The Outcome uses exact baseline/current Event Observation references plus
Support Process implementation/fidelity/follow-up context. `progress_observed`
is bounded to the documented review coverage and does not assert causation.

## Slice 9

Slice 9 implements P22-09 with one Support Process and three separately owned
Event evidence windows. It adds two active Outcome records for two different
bounded human-evaluation questions.

The first Outcome records:

```text
scope.kind = support_response_review
result = unable_to_determine
limitations = [insufficient_observation_opportunity]
```

A synthetic drill truncates the first review opportunity. Missing evidence is
preserved as missingness rather than converted into a negative result.

The later Outcome records:

```text
scope.kind = unintended_or_adverse_effect_review
result = change_observed
coverage.coverage_kind = direct_observation
```

It has a later timeframe and a different evaluation question, so it is a
separate Outcome rather than a correction or supersession of the earlier valid
Outcome. Its summary explicitly rejects causal inference from temporal overlap
with the Support and rejects Event count as proof of deterioration.



## Slice 10

Slice 10 implements P22-10 as one Event-owned Reentry/Repair graph with two
participant Accounts, an immediate Response, an in-person Communication, one
completed Reentry, one completed Repair, and a later completed Follow-Up.

The Reentry preserves its planning facts (`planned_return` and
`planned_elements`) separately from the actual `completed_at` fact. Completion
does not create clearance, readiness, safety, or rehabilitation semantics.

The Repair deliberately records asymmetric participation:

```text
student_a = participated
student_b = declined
```

Only `student_a` agrees to and completes the bounded restorative action. This
proves that Repair/action completion does not manufacture mutual participation,
admission, remorse, forgiveness, or a restored relationship. The later
Follow-Up reviews the exact Reentry and Repair records without creating an
Outcome.

## Slice 11

Slice 11 implements P22-11 with two distinct Support Process roots in adjacent
synthetic school years/classes.

The successor uses the accepted exact:

```text
continues_from
```

reference to the predecessor Support Process. Continuation is not encoded as
supersession, Record Migration, Ownership Correction, or a filesystem move.

Both process roots have fresh Participant, Need, Goal, Support, Implementation,
Observation, and Outcome identities. The current-year Support is deliberately
reviewed/adapted rather than copied byte-for-byte. Historical Outcome basis refs
remain pinned to predecessor-year records; the successor Outcome exact-links
only successor-year evidence.

The scenario's two Core-shaped roster contexts intentionally reuse the same
local-looking student ID/display name under different class IDs. That does not
create a workspace-global student identity; the class-qualified references
remain distinct.


## Slice 12

Slice 12 implements P22-12 with one multi-participant Event, an exact focal
participant, separate focal/third-party Accounts, a direct Observation, a
noncanonical student-facing projection-decision expectation, and one real
`deliberate_export@1` provenance record.

The projection keeps `included`, `withheld`, `absent`, `unavailable`, and
`requires_manual_review` distinct. Third-party Account text is withheld after
manual review rather than auto-paraphrased. Stable IDs never become output
pseudonyms. A focal Account source artifact is byte-bearing and fingerprinted,
but separate authorization denies its inclusion in the export.

The export inventory contains only exact source representations that materially
contributed to the accepted CSV output. Policy, authorization-rule, projection-
decision, source-representation, and output digests are all computed from the
committed synthetic bytes. Export generation remains distinct from disclosure,
delivery, receipt, read, consent, or external acceptance.


## Slice 13

Slice 13 implements P22-13 with a small canonical Event graph containing an
append-preserving Account correction, exact Lifecycle Transition chain, forward
Work Relationship, and forward Dependency. Eight representative derived views
are rebuilt deterministically from those canonical records; none is treated as
domain authority.

A representative replacement-frontier generation uses the accepted
`source_snapshot@1`, `derived_index_metadata@1`, and
`derived_current_pointer@1` contracts with truthful source/data fingerprints. A
changed-source simulation proves that stale snapshot state blocks reuse even
when a privacy-minimized semantic view would otherwise happen to be unchanged.

The noncanonical retention/custody expectation keeps `derived_cache` separate
from canonical retention, keeps `export_bytes` separate from
`export_provenance`, and marks Core retained-source bytes as foreign custody
outside Portia destruction authority. No legal duration or Sunset public record
is invented.


## Slice 14

Slice 14 implements P22-14 as a recoverable material correction to one canonical
Work Relationship. The final domain graph retains the original relationship as
`superseded` and one corrected successor as `active`; the successor uses the
exact accepted `supersedes` link and does not rewrite or delete the predecessor.

Six immutable `operation_journal@2` revisions record successful preflight,
staging, interrupted partial success, recovery reconciliation, commit, and
completion. The synthetic interruption occurs only after the successor has
already been accepted. Recovery therefore verifies that exact representation
and completes the remaining predecessor write rather than deleting/recreating
the successor or producing a duplicate semantic record.

The scenario also carries an explicit `operation_current_pointer@1`, one
operation-scoped `operation_lock@2`, and one work-scoped lock. Lock IDs and all
representation fingerprints are recomputable from committed fixture bytes.
Operational records remain durable coordination/recovery evidence and never
become Work Relationship domain truth.

P22-14 completes the required positive scenario set P22-01 through P22-14. The
remaining Issue #22 work is cross-cutting coverage/traceability plus the required
schema-valid but graph-invalid corpus; positive-story completion is not Issue
#22 closeout.


## Slice 15

Slice 15 begins the required schema-valid / graph-invalid corpus with
G22-001 through G22-010, covering the Issue #22 identity, ownership, and exact
reference-resolution family. Every public Portia record remains structurally
valid under its declared contract/version; each combined fixture fails for one
declared primary `G22.*` application finding.

The first ten cases cover same-looking local IDs in another work, wrong owning
class, canonical-path disagreement, wrong exact contract version, invalid
cross-class identity merging by repeated local student ID or display name,
Actor-for-roster substitution, participant targeting outside the owning work,
foreign/Core-reference substitution, and silent successor-following of an exact
historical reference.

G22-005, G22-006, G22-007, G22-009, and G22-010 use small closed noncanonical
resolver-expectation fixtures because the defect is a bad application/derived
resolution result rather than a malformed public record. Those fixtures are
explicitly `not_runtime_contract` and never become identity or reference
authority. No patch language, public schema, or ADR is introduced.

After Slice 15 the corpus contains 14 positive scenarios and 10 of the 37
enumerated graph-invalid scenarios.

## Slice 16

Slice 16 adds G22-011 through G22-016 for lifecycle/correction/dependency/
migration/continuation boundaries. The batch proves that a material
supersession graph cannot cycle; a derived replacement/current view cannot
select a superseded predecessor; a Statement of Disagreement must remain
bound to the exact contested record; required Dependency targets must resolve
inside the declared work; Record Migration cannot rewrite exact historical
references across substantive correction; and cross-year Support continuation
must use a new Support Process with exact `continues_from` rather than
migration semantics.

G22-012, G22-013, G22-015, and G22-016 use closed nonruntime semantic-context
fixtures where the defect lives in a derived/resolver decision rather than in
the structural shape of a canonical public record. G22-012 additionally
includes a structurally valid `derived_current_pointer@1` fixture so the
invalidity remains the selected replacement meaning, not pointer syntax.

After Slice 16 the corpus contains 14 positive scenarios and 16 of the 37
enumerated graph-invalid scenarios. G22-017 through G22-037 remain planned.

## Slice 17

Slice 17 adds G22-017 through G22-020 for evidence/judgment boundaries. The
batch proves that active `reported_involved` role meaning requires a resolvable
source Account rather than merely a structurally shaped reference; Review and
Determination evidence remains exact and owner-work scoped; import/paper-origin
judgments cannot become active merely because their JSON is structurally valid;
and a source-system assertion cannot be promoted into Portia Determination
semantics without an actual attributable human decision.

G22-017 and G22-018 exercise ordinary canonical reference resolution. G22-019
reuses the accepted Issue #16 application boundary for an active import-origin
Determination with no review history. G22-020 uses one closed nonruntime
semantic-context fixture because whether a human decision actually occurred is
not inferable from arbitrary JSON text or topology alone; the canonical Event,
completed Review, and Determination all remain structurally valid.

After Slice 17 the corpus contains 14 positive scenarios and 20 of the 37
enumerated graph-invalid scenarios. G22-021 through G22-037 remain planned.

## Slice 18

Slice 18 adds G22-021 through G22-025 for Response/Support/Outcome ownership,
identity, and historical-reference boundaries. The first three fixtures use
ordinary canonical graph topology: an Implementation cannot borrow a Support or
Intervention from another Support Process; Fidelity cannot evaluate an
Implementation from another Support Process as though it were locally owned; and
an Outcome cannot target a Support Process participant owned by another process.

G22-024 uses closed nonruntime write-expectation metadata because the prohibited
state is an attempted persistence operation: a distinct later-timeframe
evaluation is written over the exact identity of an earlier accepted Outcome. A
later evaluation must receive a new Outcome identity; correction/supersession is
reserved for correcting an earlier representation rather than extending its
timeframe in place.

G22-025 keeps both predecessor- and successor-year Support Process roots valid
and linked by exact `continues_from`, then uses closed nonruntime resolver
metadata to demonstrate the prohibited behavior: an exact historical reference
to the predecessor silently following to the new-year successor. Continuation
creates relationship, not aliasing.

After Slice 18 the corpus contains 14 positive scenarios and 25 of the 37
enumerated graph-invalid scenarios. G22-026 through G22-037 remain planned.

## Slice 19

Slice 19 adds G22-026 through G22-029 for paper/import idempotency and durable
operation recovery. G22-026 keeps two valid imported Event representations but
uses closed replay metadata to prove that unchanged retained-source processing
incorrectly materialized a second domain identity for the same accepted Import
Proposal. The failure is replay semantics, not Event structure.

G22-027 uses a structurally valid `capture_materialization@1` under a valid
Capture Batch and closed fixture-only resolution metadata stating that the exact
proposal resolves while the required Capture Review does not. This isolates the
human review gate without inventing a production proposal/review substitute.

G22-028 reuses an accepted `operation_journal@1` completed-write shape and omits
one exact canonical successor from readback. The journal therefore cannot make
that missing domain record true. G22-029 keeps both canonical results present
and the committed journal structurally valid, then records the prohibited
restart decision: replay an already accepted durable semantic write instead of
reconciling exact readback first.

Operational public contracts are validated as operational fixtures rather than
misclassified as class/work domain records. No public schema, catalog entry, or
ADR is added.

After Slice 19 the corpus contains 14 positive scenarios and 29 of the 37
enumerated graph-invalid scenarios. G22-030 through G22-037 remain planned.


## Slice 20

Slice 20 completes the enumerated schema-valid / graph-invalid corpus with
G22-030 through G22-037 for privacy projection, deliberate export, rebuildable
derived state, and custody boundaries. Public Event/Participant/Account,
Deliberate Export, and Source Snapshot fixtures remain structurally valid; the
failures are cross-record/application semantics.

G22-030 rejects participant-specific output that leaks unrelated participant
identity/stable IDs or unsafe third-party Account content. G22-031 preserves
`withheld`, `unavailable`, and `absent` as distinct states. G22-032 requires the
export inventory to bind the exact representation actually consumed rather than
a later successor, even when the successor fingerprint itself is truthful.
G22-033 requires export paths to remain PII-minimized in addition to being
correctly scoped beneath the opaque `pexp_` identity.

G22-034 treats canonical forward references as authority over rebuildable
incoming indexes. G22-035 prevents a replacement/current view from presenting
both superseded predecessor and active successor as current. G22-036 adds a
structurally valid `source_snapshot@1` fixture whose recorded source fingerprint
is stale after canonical source change and proves that such a generation cannot
be accepted as current. G22-037 keeps local Portia disposition separate from
Core, Vitrine, email/download, backup, and other foreign/external custody.

All semantic contexts remain closed `not_runtime_contract` corpus metadata.
`derived_contract_fixtures` are now structurally validated alongside ordinary
domain/export records and operational fixtures. No public schema, catalog, or
ADR is introduced.

After Slice 20 the corpus contains **14 positive scenarios and all 37 enumerated
graph-invalid scenarios**. `planned_graph_invalid_scenarios` is empty. This
completes the graph-invalid corpus, not Issue #22 closeout; final contract-family
disposition, baseline/drift evidence, full validation, and the Issue #23 handoff
remain separate closeout gates.

## Slice 21

Slice 21 adds supplemental positive scenario P22-15 after the closeout audit
found that the ticket's positive-corpus minimum explicitly requires current
`classification@1`, `hypothesis@1`, and `intervention@1` forms. The original
P22-01 through P22-14 required stories remain unchanged; P22-15 closes the
contract-family coverage gap without forcing judgment records into P22-02 or an
Intervention into the Support-only plan already used by P22-08.

P22-15 starts with one participant-targeted Event, firsthand Account, direct
Observation, and completed Review. A reviewer-selected Classification preserves
an exact local definition snapshot and exact Account/Observation basis. A
separate Hypothesis remains `under_consideration`, uses explicit
supporting/contextual evidence roles, and makes only a tentative bounded
proposition. Neither record is a Determination, diagnosis, credibility score,
risk score, or automatic inference.

The scenario then opens one Support Process from the exact Event. A bounded
environmental/instructional Need and planning-only Goal feed one active recurring
Intervention with an assigned teacher provider. One Implementation records one
actual occurrence of that exact Intervention. Schedule, Intervention,
Implementation, Fidelity, Goal attainment, and Outcome remain distinct.

The test-only graph validator now resolves Classification/Hypothesis evidence
and Review links and checks Intervention target/Need/Goal/provider ownership.
No public schema, catalog entry, ADR, or runtime API is added.

After Slice 21 the corpus contains **15 positive scenarios and all 37 enumerated
graph-invalid scenarios**. Both planned scenario lists remain empty. Final Issue
#22 closeout still requires the complete contract-family disposition, graph-
invalid matrix document, repository checkpoint, end-to-end validation record,
and Issue #23 handoff.

## Final closeout state

Issue #22 closes with:

```text
15 positive scenarios       P22-01..P22-15
37 graph-invalid scenarios  G22-001..G22-037
52 total scenarios
0 planned scenarios
```

The machine-readable public-catalog disposition is
`contract-coverage.json`; it maps all 161 current catalog contract families and
is checked against the live repository catalog by `test_issue_22_closeout.py`.

The authoritative validation record is:

```text
docs/validation/issue-22-end-to-end-validation.md
```

The latest observed committed-tree gates before the PR-review traceability
repair were 356/356 Issue #22 tests and 1451/1451 complete schema-validation
tests. The repair changes documentation/test traceability only and must retain
those same discovery counts before merge.

