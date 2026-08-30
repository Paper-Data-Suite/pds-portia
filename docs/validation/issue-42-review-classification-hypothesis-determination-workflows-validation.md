# Issue #42 Review, Classification, Hypothesis, and Determination workflow validation

Issue #42 converts the accepted Issue #16 / ADR 0012 human-judgment architecture
into production Event-local workflow services without changing the published
`review@1`, `classification@1`, `hypothesis@1`, `determination@1`, or
`judgment_evidence_ref@1` wire contracts.

The implementation preserves the central epistemic boundary:

```text
Account / Observation = source evidence
Review                = bounded human examination
Classification        = attributed contextual category assertion
Hypothesis            = attributed explicitly tentative proposition
Determination         = attributed bounded human decision
```

No source evidence, repeated report, category, hypothesis, policy reference, or
software-derived signal becomes proof or an automatic Determination.

## Implemented public surface

`portia.workflows` exposes:

```text
ReviewWorkflowService
ClassificationWorkflowService
HypothesisWorkflowService
DeterminationWorkflowService

review_reference(...)
classification_reference(...)
hypothesis_reference(...)
determination_reference(...)
```

The services provide the relevant guarded digital-entry creation, exact load and
bounded listing, current-use qualification, lifecycle handling, and material
successor/correction operations. Review additionally provides guarded workflow
progression. Determination additionally provides guarded reconsideration/reversal
through a new successor Determination and an exact qualifying completed Review.

All four families remain Event-local v1 records. Issue #42 adds no Support Process,
cross-Event, team-owned, or formal FBA judgment ownership.

## Exact history and current-use validation

Focused tests prove that exact historical resolution remains distinct from
eligibility for current/consequential use.

Exact reads:

- resolve the exact requested representation;
- do not select a latest representation by timestamp;
- do not follow successors;
- do not migrate or rewrite canonical bytes;
- preserve historical judgment and evidence references.

Current-use checks additionally enforce the applicable Event, target,
represented-human, lifecycle/history, Review, source-artifact, Quarantine,
external-authority, and family-specific rules.

For Account/Observation evidence, acceptance and later use are deliberately
asymmetric. New active judgment acceptance requires evidence that is current-use
eligible at that time. Once exact evidence has been accepted into a historical
judgment, later evidence invalidation, retraction, or supersession does not
silently rewrite the consumer or erase what was considered. Exact evidence
Quarantine can still block consequential current use.

This historical-pinning behavior is covered across Review, Classification,
Hypothesis, and Determination. P22-04 additionally exercises the real
`AccountWorkflowService.correct()` path and proves that a Review remains pinned to
the exact predecessor after the corrected successor becomes current.

## Review validation

Focused Review tests cover:

- guarded proposed/active digital creation;
- exact and bounded reads;
- Event and target authority, including participant-set targets;
- represented reviewer authority;
- Account/Observation evidence acceptance;
- exact historical evidence pinning after later evidence lifecycle change;
- sibling-module evidence preservation in proposed history and fail-closed active
  use without explicit public authority;
- sibling-module authority revalidation on later current use;
- Review workflow progression, evidence append, and terminal freezing;
- reconsideration-subject rules;
- Quarantine at work, Review-record, and exact evidence levels;
- lifecycle reconciliation;
- material correction through coordinated successor persistence;
- active imported/paper historical representations remaining exact-readable but
  ineligible for v0.2 current use without explicit reviewed materialization.

Completing a Review does not fabricate a Classification, Hypothesis,
Determination, credibility finding, policy finding, or Response.

## Classification validation

Focused Classification tests cover:

- reporter-selected, reviewer-selected, reviewer-confirmed, and unknown stages;
- category-selected and unable-to-determine results;
- versioned category-definition identity and confirmation agreement;
- exact Review linkage and completed-Review prerequisites where required;
- represented selector/reviewer authority;
- exact optional basis resolution;
- historical Account/Observation basis pinning;
- Quarantine and lifecycle reconciliation;
- sibling-module public-authority fail-closed behavior and revalidation;
- material correction/supersession;
- active import history failing closed for current use.

Reporter and reviewer Classifications remain separate assertions; later
disagreement does not retroactively invalidate the earlier reporter assertion.

## Hypothesis validation

Focused Hypothesis tests cover:

- `under_consideration` and `set_aside` semantics;
- supporting, contrary, and contextual evidence roles;
- coexistence of competing Hypotheses without automatic ranking;
- exact optional Review linkage;
- represented author authority;
- current evidence acceptance followed by exact historical evidence pinning;
- Quarantine on the Hypothesis and exact evidence;
- sibling-module authority fail-closed behavior and later revalidation;
- lifecycle, ordinary correction, refinement/reconsideration successor rules;
- active import history failing closed for current use.

`set_aside` is not invalidation or proof that a Hypothesis is false. The workflow
adds no confidence, risk, probability, credibility, function, or intent inference.

## Determination validation

Focused Determination tests cover:

- teacher-local and recorded-institutional authority branches;
- decision-maker eligibility separate from recorder identity;
- teacher-local, identified, and unknown process basis;
- conclusion, coded conclusion, insufficient-information,
  unable-to-determine, and not-applicable outcomes;
- exact qualifying Review linkage and current Review revalidation;
- supporting, contrary, and contextual exact basis references;
- current Account/Observation basis acceptance followed by exact historical basis
  pinning;
- documented authority/process source-artifact verification without claiming
  authenticity, applicability, or legal sufficiency;
- work/record/exact-basis Quarantine;
- sibling-module authority fail-closed behavior and later revalidation;
- lifecycle and ordinary material correction;
- reconsideration and reversal through a new successor Determination;
- preservation of the earlier Determination after reconsideration/reversal;
- active import history failing closed for current use.

A Determination does not automatically create a Response, consequence, Support,
or later follow-up record.

## Shared lifecycle and coordinated persistence

Issue #42 reuses Issue #38 coordinated persistence and the accepted
`lifecycle_transition@1` history model rather than creating a parallel transaction
or history subsystem.

Focused tests cover:

- lifecycle read/reconciliation and write-side transition persistence;
- legal judgment lifecycle transitions;
- stale fingerprint rejection;
- ordinary material correction planning and coordinated persistence;
- exact predecessor supersession and successor activation;
- correction reason/topology validation;
- Determination reconsideration/reversal topology;
- partial-operation and shared storage behavior through existing lower-layer
  contracts.

No workflow performs direct canonical record writes outside the repository /
coordinator boundary.

## Judgment evidence and sibling-module boundary

The shared judgment-evidence resolver supports only the accepted branches:

```text
portia_work
portia_record
module_record
```

Raw `source_artifact_ref@1` is not judgment evidence. Substantive raw artifact
content must first enter the Portia source-evidence layer as Account/Observation
before a judgment cites it.

`module_record` does not authorize private sibling-module imports, filesystem
crawling, guessed paths, or structural-shape trust. Active/current use requires an
explicit public `ModuleJudgmentEvidenceAuthority`. Missing authority or an
authority that cannot resolve the exact record fails closed. Successful resolution
does not establish truth, credibility, corroboration, or policy applicability.

## Issue #16 runtime parity

Issue #42 runtime tests consume the accepted Issue #16 contract semantics rather
than weakening them for application convenience.

Focused parity includes:

- Review participant-set target acceptance;
- application-invalid active import materialization boundaries for all four
  judgment families;
- exact module evidence authority behavior;
- lifecycle/correction/supersession topology;
- Review, Classification, Hypothesis, and Determination family-specific
  prerequisites.

Published schemas and Issue #16 fixtures remain unchanged.

## Issue #22 runtime parity

`tests/test_workflow_issue22_judgment_parity.py` provides production-service
coverage for the judgment-relevant representative scenarios.

P22-02 proves that:

- conflicting Accounts remain separate;
- direct Observation remains distinct from reported involvement;
- a completed Review identifies the exact evidence considered;
- an active Determination identifies the exact completed Review and explicit
  basis relations;
- `insufficient_information` is a valid bounded outcome;
- no Classification or Hypothesis is fabricated merely to complete the graph.

P22-04 proves that Account correction/supersession does not rewrite the exact
historical Account representation recorded by a Review.

## Digital authoring, import, and Quarantine

Executable Issue #42 authoring is `digital_entry` only. Schema-valid paper/import
judgment records remain preservable and exactly readable, but active non-digital
history cannot masquerade as reviewed v0.2 materialization. Current use therefore
fails closed until a future explicit capture/import workflow can establish the
missing authority.

Quarantine remains operational integrity state, not judgment or lifecycle state.
`block_work_writes` controls mutation; `block_current_use` controls consequential
use. Neither deletes or rewrites exact historical bytes.

## Documentation

The production workflow guide is:

```text
docs/review-classification-hypothesis-determination-workflows.md
```

README includes an Issue #42 current-implementation entry pointing to that guide.
`tests/test_workflow_issue42_documentation.py` keeps the workflow guide,
validation record, README navigation, public services, semantic boundaries, and
closeout expectations mechanically aligned.

## Qualification state

Every implementation slice through the Issue #16/Issue #22 parity,
documentation, packaging, and installed-wheel work passed its proportional
pytest/Ruff/MyPy/`git diff --check` gates as applicable.

Final repository/package qualification **passed on 2026-08-30** against the
authenticated `pds_core-0.6.3-py3-none-any.whl` artifact through:

```powershell
python scripts/validate_repository.py --core-wheel <authenticated-pds-core-0.6.3-wheel>
```

The consolidated qualifier completed successfully through the repository
validators, full test/static-analysis/dependency gates, clean sdist/wheel build,
Twine checks, general package inventory, Issue #41 and Issue #42 package
inventories, and isolated installed-wheel smoke for the Issue #40, Issue #41,
and Issue #42 workflow surfaces. The final observed endpoint was:

```text
Portia Issue #42 repository qualification passed
```

Issue #42 is therefore repository/package qualified for the implemented v0.2
Review, Classification, Hypothesis, and Determination workflow scope.
