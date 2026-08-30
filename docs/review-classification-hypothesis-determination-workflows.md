# Review, Classification, Hypothesis, and Determination workflows

Issue #42 provides Portia's production Event-local human review, interpretation,
and decision workflow layer. It turns the accepted Issue #16 / ADR 0012 record
contracts into guarded application services without collapsing source evidence,
human review, category selection, tentative explanation, or bounded decision into
one mutable finding.

The executable progression remains optional rather than automatic:

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ later Response / Support / Follow-Up workflows
```

The four record families retain different meanings:

```text
Review
= one bounded human process considering one question and exact information

Classification
= one attributed contextual category assertion

Hypothesis
= one attributed explicitly tentative proposition

Determination
= one attributed human decision answering one bounded question
  under explicit authority/process context
```

A Review is not a finding. A Classification is not proof or a durable student
trait. A Hypothesis is not fact, diagnosis, cause, risk, or determined behavioral
function. A Determination is not evidence, consequence, Response, Support, or
proof that a policy applies.

## Public API and ownership boundary

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

All four implemented record families are Event-local version 1:

```text
review@1
classification@1
hypothesis@1
determination@1
```

The containing work must be an exact Portia `event@2`. Issue #42 does not add
Support Process ownership, cross-Event judgment ownership, team case ownership,
or a formal FBA workflow. Canonical writes continue through `PortiaRepository`
and Issue #38 coordinated persistence.

The default implementation has no sibling-module runtime dependency and remains
on the Core compatibility line:

```text
pds-core>=0.6.3,<0.7
```

## Exact history versus current/consequential use

The workflow layer preserves a hard distinction between exact historical
resolution and eligibility for current use.

Exact reads:

- resolve only the requested contract version and canonical identity;
- preserve historical representations;
- never choose a latest record by timestamp;
- never follow a successor automatically;
- never migrate or repair during read;
- never mutate canonical bytes merely because a record is historical.

Current-use qualification additionally enforces the applicable Event, target,
represented-human, lifecycle/history, Review, source-artifact, Quarantine,
external-authority, and family-specific requirements.

A successor does not rewrite a historical consumer. If a Review, Hypothesis, or
Determination accepted an exact Account/Observation representation while it was
eligible, a later invalidation, retraction, or supersession of that evidence does
not silently retarget the judgment or erase the historical fact that the earlier
representation was considered. New consequential acceptance is stricter: an
already-ineligible Account/Observation cannot be newly accepted into an active
judgment.

Quarantine remains current operational state rather than history rewriting. An
exact historical judgment can remain readable while `block_current_use` prevents
consequential use.

## Digital authoring and imported historical records

Executable v0.2 judgment authoring is `digital_entry` only. Public schemas still
permit historical paper/import provenance, and exact reads preserve those valid
representations, but Issue #42 does not pretend that a schema-valid imported
active judgment has passed a human-reviewed materialization workflow.

For all four families, current-use qualification therefore fails closed when an
active record's creation provenance is not the executable digital-authoring path.
The record is not deleted, rewritten, or silently downgraded; it remains exact
history until a future explicit capture/import materialization workflow can
establish the missing authority.

## Shared judgment-evidence resolution

Issue #42 implements the accepted `judgment_evidence_ref@1` branches:

```text
portia_work
portia_record
module_record
```

`portia_work` and `portia_record` resolve through canonical Portia storage using
exact reference semantics. A Portia record reference may identify Account,
Observation, Review, Classification, Hypothesis, Determination, or another
compatible exact Portia record allowed by the consuming contract; resolving a
record does not convert it into truth or proof.

Raw `source_artifact_ref@1` is not judgment evidence. When the substantive
contents of paper, a workspace file, image, message, or other source matter to a
judgment, the relevant statement or direct artifact-review observation must first
be represented through the source-evidence layer and then cited canonically.

### Sibling-module evidence

A `module_record` reference is structurally legitimate but does not authorize
Portia to crawl a sibling module's private storage or import sibling private code.
Current use requires an explicitly supplied public
`ModuleJudgmentEvidenceAuthority` whose `resolve_exact()` operation establishes
that the exact external record can be resolved through an approved interface.

Adapter presence alone is not evidence of truth, credibility, corroboration, or
policy applicability. The adapter may return opaque external material to establish
resolution authority; Portia does not reinterpret the sibling record's private
semantics. If no adapter is supplied, or the adapter cannot resolve the exact
record, activation/current use fails closed while schema-valid historical or
proposed references remain preservable where the contract permits them.

External module authority is revalidated on later current use. Successful earlier
resolution is not persisted as a permanent trust flag.

## Review workflow

One `review@1` is one bounded human review process for one Event-local target and
one explicit question.

Canonical lifecycle remains separate from Review workflow state:

```text
canonical lifecycle:
proposed | active | invalidated | superseded

review_state:
open | in_review | awaiting_information | completed | cancelled
```

`ReviewWorkflowService` provides guarded digital creation, exact reads, bounded
listing, current-use qualification, workflow-state progression, ordinary
lifecycle transitions, and material correction through a successor.

The active nonterminal Review workflow permits the accepted progression paths,
including:

```text
open -> in_review
in_review -> awaiting_information
awaiting_information -> in_review
in_review -> completed
open -> cancelled
```

It rejects prohibited backward/reopen transitions. Completed and cancelled
Reviews are substantively frozen.

While an active Review remains nonterminal, `update_workflow()` may advance legal
workflow state and append exact evidence actually considered. It may not silently
remove prior evidence, rewrite an earlier evidence reference, or materially
change target, reviewer, question, trigger, review subject, or creation
provenance. Those are successor/correction concerns rather than ordinary workflow
updates.

Completing a Review does not synthesize a Classification, Hypothesis,
Determination, evidence winner, credibility finding, policy finding, or Response.
A reconsideration Review remains a new Review with explicit exact subject history;
it does not reopen the earlier completed Review.

## Classification workflow

One `classification@1` is one attributable contextual category assertion for one
Event-local target. Reporter and reviewer assertions remain separate canonical
records rather than revisions of one shared classification state.

Accepted stages remain:

```text
reporter_selected
reviewer_selected
reviewer_confirmed
unknown
```

Accepted result branches remain:

```text
category_selected
unable_to_determine
```

A selected category preserves the accepted versioned definition snapshot:

```text
scheme_id
scheme_version
category_code
category_label
definition_text
```

Category comparison identity is the scheme/version/code identity; label text is a
historical meaning snapshot, not a universal taxonomy registry.

Reviewer-stage Classifications require the applicable exact Review linkage and
represented reviewer authority. Current reviewer-stage use requires a completed
current Review where the accepted contract requires one. `reviewer_confirmed`
additionally requires the exact prior Classification and result agreement under
the accepted category identity rules.

A reviewer disagreement does not invalidate or supersede a reporter
Classification merely because it is later. `unknown` is not automatically
promoted to a reviewer conclusion. No automatic classification engine exists.

## Hypothesis workflow

One `hypothesis@1` is one attributable explicitly tentative proposition.
Competing Hypotheses may coexist without a winner.

Accepted consideration states remain:

```text
under_consideration
set_aside
```

Accepted evidence relations remain:

```text
supporting
contrary
contextual
```

Contrary evidence is first-class. Evidence counts do not create evidentiary
weight, confidence, probability, credibility, or automatic ranking.

`HypothesisWorkflowService` provides guarded creation, exact/current reads,
bounded listing, `set_aside()`, ordinary lifecycle transitions, and material
correction through a successor. Setting a Hypothesis aside is a workflow meaning,
not invalidation: it does not mean false, delete the record, or promote another
Hypothesis.

A new active Hypothesis may only accept currently eligible Account/Observation
evidence. Once accepted, those exact references are historical evidence: later
evidence lifecycle changes do not silently rewrite or by themselves disqualify
the Hypothesis. Exact-evidence Quarantine and external module authority remain
current-use checks.

No confidence scores, function inference, intent inference, diagnostic inference,
risk scores, or automatic Hypothesis ranking are added.

## Determination workflow

One `determination@1` is one bounded attributable human decision answering one
explicit question for one Event-local target.

Accepted authority branches remain:

```text
teacher_local
recorded_institutional
```

Teacher-local current use requires the accepted local-operator decision-maker
eligibility. Recorded institutional authority remains a historical attribution
and provenance model, not a claim that Portia authenticated institutional RBAC or
legal authority.

Recorded-institutional `authority_status` remains:

```text
documented_basis
asserted
unknown
```

`documented_basis` means typed supporting material was retained. It does not mean
Portia proved that the material is authentic, grants authority, is legally
sufficient, applies to the Event, or was interpreted correctly.

Process basis remains:

```text
teacher_local
identified
unknown
```

Accepted outcomes remain:

```text
conclusion
coded_conclusion
insufficient_information
unable_to_determine
not_applicable
```

Unresolved outcomes are first-class. Portia does not force a binary conclusion or
hard-code local category labels as universal semantics.

Where authority/process provenance uses supported `source_artifact_ref@1`
branches, current-use verification reuses the source-artifact authority boundary
from Issue #41. Workspace-file bytes/fingerprint and exact Portia references may
be verified where supported; unsupported artifact branches fail closed when
current authority depends on them. Verification establishes reference/byte
identity, not legal or institutional sufficiency.

A linked Review must satisfy the exact same-Event, target, and completion/current
requirements imposed by the accepted contract. Issue #42 does not synthesize a
Review merely to make a Determination valid.

A new active Determination may only accept currently eligible Account/Observation
basis evidence. After acceptance, exact basis history remains pinned: later
lifecycle changes to that evidence do not retroactively rewrite the decision or
change what it was based on. Basis Quarantine, sibling-module authority, linked
Review current use, decision-maker authority, and authority/process provenance
remain current/consequential checks.

## Determination reconsideration and reversal

Ordinary correction is distinct from reconsideration. The Determination
supersession reasons:

```text
reconsidered
reversed_on_reconsideration
```

are reserved for the dedicated guarded reconsideration path.

`DeterminationWorkflowService.reconsider()` requires an exact qualifying completed
Review in the same Event whose trigger/question and review subjects establish the
reconsideration topology. The successor must be a new active Determination and
must cite that exact Review. Reversal additionally requires a changed outcome.

The operation coordinates successor creation and predecessor supersession through
Issue #38 persistence. The earlier Determination remains historical rather than
being overwritten or deleted. A changed later decision therefore does not erase
the fact that the earlier decision existed under its then-recorded basis and
authority context.

## Lifecycle transitions and material correction

All four judgment families use the accepted canonical lifecycle vocabulary:

```text
proposed
active
invalidated
superseded
```

Ordinary domain lifecycle changes are recorded through `lifecycle_transition@1`
and coordinated persistence rather than naked status replacement. Lifecycle
history reconciliation is required before current use.

Material correction creates a distinct active successor and coordinates the exact
predecessor to `superseded`. The correction reason must correspond to a material
change in the relevant family. Historical consumers remain pinned to the exact
predecessor and do not follow the successor automatically.

Ordinary disagreement is not invalidation. Review workflow progression is not a
material correction. Hypothesis `set_aside` is not invalidation. Determination
reconsideration/reversal uses its dedicated guarded path rather than ordinary
correction.

## Quarantine and failure isolation

`block_work_writes` and `block_current_use` remain different controls.
`block_work_writes` prevents canonical mutation but is not itself a reason to deny
an otherwise valid read/current-use operation. `block_current_use` denies
consequential use while preserving exact readback.

Current-use qualification applies Quarantine both at the owning Event/judgment
record and to exact Portia evidence/basis records where the consuming workflow
requires it. Quarantine does not alter lifecycle state, choose a successor, or
convert an integrity problem into a substantive behavior judgment.

Storage conflicts, corruption, identity failures, Quarantine failures, and
recovery-required state retain their typed lower-layer errors. Workflow services
use workflow ownership/prerequisite/validation errors for the application rules
introduced at this layer.

## Issue #16 and Issue #22 runtime parity

Issue #42 preserves the frozen Issue #16 contract/application-invalid boundary and
adds executable coverage for representative Issue #22 judgment behavior.

P22-02 is exercised as an end-to-end judgment subgraph in which materially
conflicting Accounts remain separate, a direct Observation remains distinct from
reported perspective, one completed Review cites the exact evidence, and a
Determination can honestly record `insufficient_information` with explicit
supporting/contrary/contextual basis roles. The workflow does not fabricate a
Classification or Hypothesis merely because a Review and Determination exist.

P22-04 is exercised through the real coordinated Account correction path. A
Review that considered the exact Account predecessor remains byte-for-byte pinned
to that predecessor after a corrected successor becomes current. The same
historical-reference principle is applied to already-accepted Hypothesis evidence
and Determination basis.

Application-invalid active imported Review, Classification, Hypothesis, and
Determination records remain exact-readable but fail current-use materialization
checks in v0.2.

## Explicit non-equivalences

The implemented workflows deliberately preserve these boundaries:

```text
Review != finding
Classification != fact or person identity
Hypothesis != fact or diagnosis
Determination != evidence
Review completion != Determination
authority provenance != authenticated authority
policy reference != proven applicability
repeated reports != proof
disagreement != invalidation
set_aside != false
reversal != deletion of the prior decision
Determination != Response
```

## Downstream handoff

Later Response, Communication, Support, Intervention, Follow-Up, Outcome, Reentry,
and Repair workflows may consume exact/current judgment context under their own
contracts. They must not retroactively prove the underlying Classification,
Hypothesis, or Determination correct, and they must not rewrite historical exact
references merely because a later successor exists.
