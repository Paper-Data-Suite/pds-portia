# ADR 0012: Define Review, Classification, Hypothesis, and Determination Domain Models

- **Status:** Accepted
- **Date:** 2026-08-07
- **Decision owners:** Portia maintainers
- **Related issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Supersedes/refines:** implementation semantics originally sketched by ADR 0001 for Classification, Hypothesis, and Determination

## Context

ADR 0001 established the foundational principle that Portia must separate observations, interpretations, classifications, hypotheses, determinations, responses, and outcomes rather than collapse them into one mutable incident narrative.

Subsequent accepted architecture made that principle concrete:

```text
Event v2
Event Participant v3
Event Participant Role v3
Account v1
Observation v1
Actor Directory v1
shared exact references / targets
shared lifecycle / correction / dependency / migration / removal
coordinated operations / Quarantine / Integrity Findings / derived projections
```

Account v1 now preserves what one represented human source said. Observation v1 preserves directly observed, recorded, counted, timed, or measured information. Neither record establishes credibility, corroboration, Classification, Hypothesis, policy violation, behavioral function, risk, or Determination.

Issue #16 therefore defines the next layer: explicit human review, interpretation, and decision records.

The current deployment remains teacher-local. Core does not provide institution-wide staff identity, RBAC, or a service capable of authenticating institutional decision authority. The model must preserve authority provenance without making a false platform-level authorization claim.

## Decision

### 1. Review is a canonical Event-local process record

One Review represents one bounded human review process concerning one question, one Event-local target, and the information actually considered.

Review receives opaque identity:

```text
rvw_<opaque-id>
```

and canonical storage beneath the containing Event.

Concern/referral semantics are Review-initiation context in v1, not separate canonical record families. Accepted trigger vocabulary is:

```text
concern
referral
routine_review
reconsideration
support_related
other
```

Optional requester attribution is separate from trigger kind.

Review question kinds are:

```text
evidence_review
classification_review
hypothesis_review
determination_review
reconsideration
other
```

Every Review also carries bounded question text. Review completion does not imply a finding.

### 2. Review lifecycle and workflow state remain separate

Canonical lifecycle is:

```text
proposed
active
invalidated
superseded
```

Review workflow state is:

```text
open
in_review
awaiting_information
completed
cancelled
```

A proposed Review may be revised before activation. An active nonterminal Review may advance workflow state and append exact evidence-considered references through guarded revision-aware persistence. Material identity/question/target/reviewer changes require correction history. A completed/cancelled Review is frozen. Reconsideration creates a new Review.

### 3. Human judgment attribution reuses represented-human attribution

`represented_human_attribution@1` is reused for reviewer, Classification selector, Hypothesis author, and Determination decision-maker because each needs the same represented-human semantics.

Persistence attribution remains separate. A system process may persist a proposal but cannot become the represented substantive human.

Human identity does not establish authority.

### 4. Judgment evidence uses one canonical-reference primitive

Issue #16 will publish:

```text
judgment_evidence_ref@1
```

with three branches:

```text
portia_work   -> exact_portia_work_ref@1
portia_record -> exact_portia_work_record_ref@1
module_record -> module_work_record_ref@1
```

The primitive carries no weight, credibility, truth, independence, or outcome semantics.

Raw `source_artifact_ref@1` is intentionally excluded. When raw artifact contents matter to a judgment, Portia first preserves the relevant human statement or direct artifact-review observation through Account/Observation and then cites that canonical evidence record. This preserves the source-evidence layer and avoids overlapping reference forms.

Authority or policy material may separately use source-artifact provenance where appropriate; such provenance is not automatically judgment evidence.

### 5. Classification is one attributed contextual category assertion

One Classification represents one human category selection, confirmation, or inability-to-select outcome for one Event-local target.

Identity:

```text
cls_<opaque-id>
```

Stages:

```text
reporter_selected
reviewer_selected
reviewer_confirmed
unknown
```

Reporter and reviewer assertions remain separate canonical records. A reviewer disagreement does not invalidate or supersede a reporter Classification merely because it is later.

`reviewer_confirmed` requires an exact prior Classification and the same result semantics; selected categories must carry the same category identity. `unknown` exists for historical/imported material whose stage cannot be reconstructed and does not satisfy reviewer-confirmed current-use requirements.

Classification result is:

```text
category_selected
unable_to_determine
```

A selected category preserves:

```text
scheme_id
scheme_version
category_code
category_label
definition_text
```

Identity for comparison is `scheme_id + scheme_version + category_code`. Label and definition text preserve historical meaning; they do not turn the Classification into a person attribute or prove policy applicability.

No suite-wide behavior taxonomy or Classification-definition registry is introduced in v1.

### 6. Hypothesis remains explicitly tentative

One Hypothesis represents one attributable tentative human explanation for one Event-local target.

Identity:

```text
hyp_<opaque-id>
```

It contains one bounded proposition and evidence roles:

```text
supporting
contrary
contextual
```

Contrary evidence is first-class. Duplicate records, shared Account lineage, and reference counts do not establish evidence weight or corroboration automatically.

Hypothesis has no numeric or qualitative confidence field in v1. Its consideration state is:

```text
under_consideration
set_aside
```

`set_aside` is not invalidation and does not mean false. Reconsideration/refinement creates a new or successor Hypothesis rather than silently toggling history.

Event-local Hypothesis v1 is not an FBA. Cross-Event/team/FBA ownership is deferred to the Support Process architecture in #18.

### 7. Determination is one bounded attributed human decision

One Determination answers one explicit question for one Event-local target under one represented decision scope and authority context.

Identity:

```text
det_<opaque-id>
```

Determination is separate from Account, Observation, Classification, Hypothesis, Response, consequence, support, and student identity.

### 8. Teacher-local and recorded-institutional authority are distinct

Authority context is either:

```text
teacher_local
recorded_institutional
```

Teacher-local scopes are:

```text
classroom_management
teacher_review
teacher_support_coordination
other
```

Recorded-institutional authority status is:

```text
documented_basis
asserted
unknown
```

`documented_basis` means typed material documenting the authority claim is retained. It does not mean PDS authenticated the person or proved the authority legally sufficient.

`asserted` means authority is represented but no such typed basis is retained. `unknown` preserves historical uncertainty.

Actor title/category, organization, contact information, local-operator status, or recorder identity never confer authority.

Structural human attribution is broader than role eligibility. For current-use v1, a `teacher_local` Determination requires a `local_operator` decision-maker. A recorded-institutional Determination may preserve an Actor, local operator, descriptive school-staff person, or unidentified historical decision-maker, but the authority-context rules still govern what the record may claim. Roster-student or non-staff descriptive identity does not become institutional decision authority merely because the shared attribution union can represent that person.

### 9. Policy/process basis is separate from authority

Determination process basis is:

```text
teacher_local
identified
unknown
```

Teacher-local basis carries a local process label.

An identified basis may preserve a policy, a process, or both, each with label, optional version, and optional source-artifact provenance. Portia does not create a universal district-policy registry.

A source reference does not prove applicability or correct application.

### 10. Determination outcome is a closed union

Accepted branches:

```text
conclusion
coded_conclusion
insufficient_information
unable_to_determine
not_applicable
```

A coded conclusion preserves scheme/version/code plus a human-readable meaning snapshot. Local terms such as `substantiated` or `not_substantiated` appear only through an identified scheme.

`not_substantiated` never automatically means nothing occurred and never invalidates source evidence.

`insufficient_information` and `unable_to_determine` preserve different kinds of unresolved outcome rather than forcing a binary finding.

### 11. Repeated reports never become proof by count

Portia does not implement rules such as:

```text
three Accounts = substantiated
two Observations = confirmed
majority of sources = true
```

Known source lineage, duplicate capture, exact duplicate references, and conflicting evidence remain data-quality/context facts only.

### 12. All four record families reuse Event-local targeting

Review, Classification, Hypothesis, and Determination v1 reuse `portia_target_ref@1` and may target the containing Event, one Event Participant, or an explicit Participant set.

Event-level judgment does not automatically apply to each Participant. A multi-Participant target does not imply identical conduct, evidence, responsibility, or response.

No judgment becomes a durable roster-student or Actor profile attribute.

### 13. Shared canonical lifecycle is reused

All four record families use:

```text
proposed
active
invalidated
superseded
```

with the existing lifecycle-transition infrastructure and family-specific reason vocabularies documented in the design.

Invalidation means the record is defective as a representation; it does not mean another human later disagreed.

### 14. Reconsideration and reversal create new records

A valid Determination later changed on reconsideration remains historically valid as the earlier decision. A new Review and new Determination preserve the later act.

Determination successor reasons include `reconsidered` and `reversed_on_reconsideration`.

Reporter/reviewer Classification disagreement is not supersession by default. Competing Hypotheses are not supersession merely because they conflict.

### 15. No Issue #16 v1 family exposes Amendment paths

Review, Classification, Hypothesis, and Determination v1 expose no permitted `amendment@1` paths.

Open Review workflow progression is ordinary guarded workflow evolution, not Amendment.

Material correction to an accepted judgment uses successor/history semantics; disagreement uses `statement_of_disagreement@1` where appropriate.

### 16. Paper and imports never create automatic judgment

Paper preallocation does not create Classification, Hypothesis, or Determination. OCR/mark recognition may transcribe structure but cannot establish human judgment, authority, policy applicability, or outcome.

Imported judgment records begin proposed unless they are governed migrations of already accepted Portia representations. Human review may activate a historical representation with bounded unknown metadata, but current-use eligibility remains separate.

An unknown Classification stage cannot become reviewer-confirmed by implication. Unresolved human attribution does not satisfy consumers requiring resolved attribution. Institutional authority status never becomes authenticated merely by import or source-system prestige.

### 17. Automation may organize review but not decide

Software may validate, route, remind, expose missing evidence, show definitions/policy checklists, detect duplicate references/known lineage, and build derived navigation.

Software may not automatically classify prose, infer intent/function, rank Hypotheses, decide credibility, substantiate allegations, determine policy violations, recommend punishment, calculate predictive/risk scores, convert Observation to Determination, or convert report count to proof.

### 18. Shared infrastructure is reused

Issue #16 reuses the existing lifecycle, history correction, Statement of Disagreement, Dependency, migration, ownership correction, exceptional removal, operation journal, lock, Quarantine, Integrity Finding, source snapshot, derived metadata, and current-pointer contracts through their existing generic exact references.

No judgment-family-specific copy is introduced unless later implementation demonstrates a genuine wire incompatibility.

## Public Contract Plan

ADR 0012 authorizes implementation of:

```text
portia_review_id@1
portia_classification_id@1
portia_hypothesis_id@1
portia_determination_id@1
judgment_evidence_ref@1
review@1
classification@1
hypothesis@1
determination@1
```

No public schema is modified in place.

## Consequences

### Positive

- Source evidence remains distinct from interpretation and decision.
- Review can be tracked without forcing a finding.
- Reporter and reviewer categories preserve separate authorship.
- Classification cannot silently become student identity.
- Hypotheses remain tentative and can preserve contrary evidence.
- Report/reference counts do not become automatic corroboration.
- Determination authority is explicit without overstating teacher-local platform capabilities.
- Institutional decisions can be preserved historically with honest uncertainty.
- Insufficient-information outcomes are representable.
- Reconsideration/reversal preserve the earlier decision.
- Existing exact-reference, lifecycle, disagreement, migration, removal, operational, and derived contracts remain reusable.

### Costs

- The model uses several distinct canonical record families rather than one incident finding object.
- Current-view logic must choose among separately attributed Classification records without erasing them.
- Authority provenance requires careful display language.
- Review workflow updates need revision-aware persistence before completion.
- Consumers must distinguish canonical existence from eligibility for consequential use.
- Formal cross-Event/FBA use still requires the later Support Process architecture.

## Alternatives Considered

### One mutable incident/finding record

Rejected because it collapses evidence, interpretation, and decision and destroys provenance during review or appeal.

### Store Classification directly on Event or Participant

Rejected because category authorship, definition version, reviewer disagreement, and correction history would be lost; Participant-level fields would also encourage durable person labeling.

### One generic judgment record

Rejected because Classification, Hypothesis, and Determination have materially different epistemic status and authority semantics.

### Hypothesis as Classification subtype

Rejected because a category is not a tentative causal/contextual explanation.

### Determination as Classification status

Rejected because decision question, decision-maker, authority, policy/process basis, and reconsideration cannot be represented honestly as a category state.

### Raw artifact references directly as judgment evidence

Rejected because it would bypass the Account/Observation source-evidence layer and create overlapping reference forms with `source_artifact_ref@1`.

### Numeric evidence/confidence scoring

Rejected because counts and scores would invite false evidentiary weighting, credibility scoring, predictive interpretation, or automatic adjudication.

### Actor title/category as authority

Rejected because Actor data are teacher-local descriptive identity context and do not establish institutional delegation.

### Automatic Classification or Determination

Rejected because the product boundary requires attributable human judgment.

### Rewrite prior Determination after reconsideration

Rejected because it erases the actual earlier decision and its provenance.

## Deferred Work

- Cross-Event/team/FBA Hypothesis ownership: #18.
- Production Response and Communication: #17.
- Support Process and Intervention: #18.
- Follow-Up/Outcome/Reentry/Repair: #19.
- Complete paper/import workflows: #20.
- Privacy/redaction/export/retention: #21.
- End-to-end graph examples: #22.
- Final architecture audit: #23.
- Institution-wide staff identity, authentication, RBAC, and authority verification: future platform work.

## Invariants

1. Review is not a finding.
2. Concern/referral routing is not evidence.
3. Classification is an attributed contextual category, not a person identity.
4. Reporter and reviewer Classifications remain separately attributable.
5. Hypothesis is always tentative.
6. Contrary evidence is first-class.
7. Evidence count is not evidence weight.
8. Repeated reports do not become proof automatically.
9. Determination answers one bounded question.
10. Decision-maker identity is separate from recorder identity.
11. Decision-maker identity is separate from authority.
12. Teacher-local scope is not institutional authority.
13. `documented_basis` is not platform authentication.
14. Policy/process basis is separate from authority.
15. Event-level judgment does not automatically apply to each Participant.
16. No judgment is stored as a durable student/Actor trait.
17. Valid disagreement is not invalidation.
18. Reversal preserves the prior Determination.
19. Exact historical references do not silently follow successors.
20. No v1 Issue #16 record exposes Amendment paths.
21. Paper/import/OCR do not create automatic human judgment.
22. Software may organize review but may not make Classification, Hypothesis, or Determination automatically.
23. Operational/derived records do not copy substantive judgment text merely for coordination or diagnostics.
24. Published schemas remain immutable.
