# Portia Review, Classification, Hypothesis, and Determination Domain Models

**Status:** Working design — pre-ADR
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-07
**Branch:** `16-review-classification-hypothesis-determination-domain-models`

## 1. Purpose

This document defines the working pre-ADR architecture for Portia's human review, interpretation, and decision layer.

The accepted record progression remains:

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response / Support / Follow-Up
```

The arrows express possible workflow progression, not mandatory record creation.

An Event may have no Review. A Review may end without a Classification, Hypothesis, or Determination. A Classification may exist without a Determination. Several competing Hypotheses may remain unresolved. A Determination may record insufficient information rather than an affirmative conclusion.

The central boundary is:

```text
Account / Observation
= source evidence

Review
= bounded human examination of a question and evidence set

Classification
= attributed human category selection under an identified definition

Hypothesis
= attributed, explicitly tentative human explanation

Determination
= attributed human decision answering a bounded question under an explicit authority context
```

None of these concepts is a durable student identity label.

This issue defines architecture and public contracts. Production repositories, authorization services, institutional staff identity, policy engines, teacher-facing workflows, and executable decision services remain outside this milestone.

## 2. Governing Contracts

The design is subordinate to the accepted Portia architecture through ADR 0011.

Current implementation-target contracts include:

```text
event@2
event_participant@3
event_participant_role@3
work_relationship@2

actor@1
account@1
observation@1

portia_target_ref@1
local_record_ref@1
exact_local_record_ref@1
portia_work_ref@1
portia_work_record_ref@1
exact_portia_work_record_ref@1
module_work_record_ref@1

represented_human_attribution@1
source_artifact_ref@1

lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
ownership_correction@1
exceptional_removal@1
```

The existing coordinated-operation, lock, Quarantine, Integrity Finding, source-snapshot, derived-generation, and current-pointer contracts are also part of the governing implementation baseline.

Published public schemas remain immutable.

Issue #16 should reuse those contracts unless a concrete wire-shape incompatibility is demonstrated.

## 3. Reviewed Repository Baseline

The Issue #16 branch was confirmed identical to `main` at the initial checkpoint.

| Repository | Reviewed commit | Immediate implication |
| --- | --- | --- |
| `pds-portia` | `35df69904cff3c696876f04e208bbe704bab3e97` | Issue #15 is merged. Account and Observation are concrete evidence families. Review, Classification, Hypothesis, and Determination remain conceptual. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core remains authoritative for workspace, class, roster, PDS2 routing, retained-source provenance, and module-publication infrastructure. It does not provide institutional staff identity or decision authorization. |

Initial classification:

```text
pds-core:
    governing workspace / roster / routing boundary
    no contract change required for initial Issue #16 work

pds-portia:
    new review / judgment domain contracts required

sibling modules:
    no concrete initial contract change required
```

A new drift check is required immediately before ADR 0012 is accepted.

## 4. Governing Principles

1. Source evidence remains separate from human interpretation.
2. Review state is not itself a finding.
3. A concern, referral, or queue label is not evidence.
4. Classification is a contextual category selection, not a person identity.
5. Reporter and reviewer classifications remain separately attributable.
6. Hypothesis is always tentative.
7. Competing Hypotheses may coexist.
8. Contrary evidence is first-class rather than hidden in narrative.
9. Evidence-reference count does not equal evidentiary weight.
10. Repeated reports do not automatically become corroboration.
11. A Determination answers one bounded question under one bounded scope.
12. Decision-maker identity is distinct from recorder identity.
13. Human identity is distinct from decision authority.
14. Actor title, category, organization, or contact data do not confer authority.
15. Teacher-local judgment must not be represented as an authenticated institutional finding.
16. Software may organize review but must not make substantive judgment automatically.
17. Material judgment changes preserve history through replacement or a new decision.
18. Historical exact references never silently follow successors.
19. A Response or consequence does not prove a Determination.
20. Operational and derived records must not duplicate sensitive judgment text unnecessarily.

---

# 5. Proposed Decision 1: Review Is a Canonical Event-Local Record

One Review represents:

> One bounded human review process concerning one defined question, one Event-local target, and an explicitly identified set of information actually considered during that review.

Review is a canonical record because it may have independent identity, target, review question, review type, reviewer, workflow state, evidence considered, chronology, creation provenance, completion state, and reconsideration relationship.

Review is not an Account, Observation, Classification, Hypothesis, Determination, Response, Support Process, or permanent student case.

One Review should not become a container that owns canonical Classification, Hypothesis, or Determination children. Those records remain separately addressable Event-local records.

A later judgment record may reference the Review from which it arose. Reverse "Review produced X" views are derived.

## 5.1 Review identity

Proposed identifier:

```text
rvw_<opaque-id>
```

Proposed public identifier contract:

```text
portia_review_id@1
```

The identifier carries no student, question, category, urgency, finding, or lifecycle meaning.

## 5.2 Review storage

Proposed canonical path:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/review/<review_id>.json
```

Review v1 is Event-local.

Cross-Event or Support-Process review ownership is deferred until the Support Process model is defined.

---

# 6. Proposed Decision 2: Concern and Referral Are Review-Initiation Context in v1

Issue #16 does not introduce separate canonical Concern or Referral record families merely to drive navigation.

For the initial Event-local judgment layer, concern/referral semantics are represented as bounded Review initiation context.

Proposed trigger vocabulary:

```text
teacher_concern
student_request
family_request
referral
routine_review
reconsideration
support_related
other
```

`other` requires concise detail.

The trigger may identify the represented human requester where the workflow genuinely records one.

Review initiation context answers why this Review was opened. It does not answer what happened, whether a category is correct, whether a hypothesis is supported, whether a policy applies, or whether misconduct occurred.

If later implementation demonstrates that Referral needs independent identity, provenance, lifecycle, routing history, or cross-work existence, that must be introduced through a later explicit contract rather than inferred from this navigation field.

---

# 7. Proposed Decision 3: Review Lifecycle and Review Workflow State Are Separate

Review has two distinct state dimensions.

## 7.1 Canonical record lifecycle

Proposed lifecycle vocabulary:

```text
proposed
active
invalidated
superseded
```

This answers whether the canonical representation is valid and current.

## 7.2 Review workflow state

Proposed review-state vocabulary:

```text
open
in_review
awaiting_information
completed
cancelled
```

This answers where the human review process stands.

A Review may therefore be:

```text
status = active
review_state = completed
```

without contradiction.

`completed` means the bounded review process concluded. It does not imply that a finding was made.

`cancelled` means the valid historical Review was ended without ordinary completion. It is not the same as invalidation.

## 7.3 Workflow mutation boundary

While a Review remains open, application workflows may append evidence considered and advance review workflow state through guarded revision-aware persistence.

Once `review_state` is `completed` or `cancelled`, the substantive review snapshot is frozen.

Later reconsideration should create a new Review linked to the prior Review rather than reopening or rewriting the completed record.

Review v1 should expose no generic Amendment path for substantive question, target, reviewer, or completed evidence-set correction.

---

# 8. Proposed Decision 4: Reviewer and Recorder Are Separate

Review uses a represented human reviewer separate from persistence attribution.

Proposed reuse:

```text
represented_human_attribution@1
```

This reuse does not confer authority. It only answers which human is represented as performing the review.

The record still preserves `created_by` and `updated_by` through the existing operation-attribution contract.

A system process may create or import a proposed Review record.

A system process must not become the substantive reviewer merely because it persisted JSON.

Current-use application rules may require stronger reviewer identity than structural storage. For example, an imported historical Review may validly preserve an unidentified reviewer while being ineligible for a new consequential decision.

---

# 9. Proposed Decision 5: Review Question Is Explicit and Bounded

Every Review must state the question being reviewed.

Proposed structure:

```text
question:
    kind
    text
```

Initial `kind` vocabulary:

```text
evidence_review
classification_review
determination_review
reconsideration
other
```

`other` requires concise detail or a sufficiently specific `text`.

The question text is the bounded human-readable question. It must not become an unrestricted student-profile narrative.

Examples:

```text
What information is available concerning the participant-specific report?

Does the reporter-selected local category remain appropriate under the reviewed definition?

Is there sufficient information to record a teacher-local conclusion?

Should the prior Determination be reconsidered?
```

A Review may also identify exact subject records under review, such as an earlier Classification or Determination.

The Event-local `target` still answers whom or what the Review concerns.

---

# 10. Proposed Decision 6: Review Records What Was Actually Considered

A Review should preserve exact references to evidence actually considered.

It must not imply that every record associated with the Event was reviewed.

Proposed field:

```text
evidence_considered
```

The list may be empty when a Review is first proposed or opened.

A completed Review may validly contain no evidence if it was cancelled or closed as unavailable, but application validation must reconcile that outcome with the review question and state.

Evidence identity is exact where Portia owns exact reference semantics.

---

# 11. Proposed Decision 7: Add One Shared Judgment-Evidence Reference Primitive

Review, Hypothesis, and Determination have an immediate shared need to reference material considered without embedding the source payload.

Proposed public primitive:

```text
judgment_evidence_ref@1
```

Proposed branches:

```text
portia_record
module_record
source_artifact
```

`portia_record` wraps `exact_portia_work_record_ref@1`.

`module_record` wraps `module_work_record_ref@1`.

`source_artifact` wraps `source_artifact_ref@1`.

The primitive does not carry evidence weight, credibility, truth, corroboration count, or decision outcome.

It answers only which exact or typed material this judgment record refers to.

Consumers add their own role semantics.

Examples:

```text
Review:
    evidence_considered

Hypothesis:
    evidence:
        relation = supporting | contrary | contextual

Determination:
    basis:
        relation = supporting | contrary | contextual
```

Classification may use the primitive for optional basis references but should not be forced to imply adjudicative evidence weight.

The ADR must confirm whether raw `source_artifact` references belong in the primitive or whether all substantive artifact interpretation should first become Account/Observation evidence.

---

# 12. Proposed Decision 8: Classification Is One Attributed Category Selection

One Classification represents:

> One attributed human selection, confirmation, or inability-to-select outcome under one identified classification definition or scheme for one Event-local target.

Classification is not fact, finding, credibility judgment, policy determination, behavioral function, diagnosis, risk, or student identity.

## 12.1 Classification identity

Proposed identifier:

```text
cls_<opaque-id>
```

Proposed public contracts:

```text
portia_classification_id@1
classification@1
```

Proposed storage:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/classification/<classification_id>.json
```

## 12.2 Classification target

Classification reuses `portia_target_ref@1`.

The target may be the Event, one Event Participant, or an explicit Participant set.

Event-level Classification does not classify every participant.

Classification must never target a roster student or Actor directly as a durable person attribute.

---

# 13. Proposed Decision 9: Reporter and Reviewer Classifications Are Separate Assertions

The initial classification-stage vocabulary is:

```text
reporter_selected
reviewer_selected
reviewer_confirmed
```

A reviewer-selected or reviewer-confirmed Classification may reference the exact earlier Classification it reviewed.

A reviewer disagreement does not invalidate or supersede the reporter's Classification merely because the reviewer selected another result.

Example:

```text
Classification A
stage = reporter_selected
result = disruption

Classification B
stage = reviewer_selected
reviews = Classification A
result = unable_to_determine
```

Both remain attributable historical records.

Use invalidation only when a Classification record itself is incorrect as a record, for example wrong selector, wrong target, wrong definition identity, recording error, or invalid provenance.

Do not use correction semantics to erase a legitimate difference of judgment.

---

# 14. Proposed Decision 10: Classification Result Is a Closed Union

Classification should not force a category when the human cannot make one.

Proposed result branches:

```text
category_selected
unable_to_determine
```

`category_selected` preserves:

```text
scheme_id
category_code
category_label
definition_version
```

These values identify what definition was used at the time.

A mutable display label alone is not sufficient historical category identity.

The initial architecture does not define one suite-wide behavior taxonomy.

Classification schemes remain Portia-scoped local configuration unless a later explicit shared contract is justified.

`unable_to_determine` is a real human review outcome, not a fake behavior category.

---

# 15. Proposed Decision 11: Classification Definition Identity Is Nested in v1

Issue #16 should not publish a classification-definition registry merely because Classification needs stable historical meaning.

The first Classification contract may preserve the definition identity directly in a closed nested object.

This keeps v1 honest without creating a configuration subsystem prematurely.

If a later workflow requires separately managed local taxonomies with their own identity, lifecycle, activation dates, examples, nonexamples, ownership, or migration, that should become a dedicated configuration contract.

---

# 16. Proposed Decision 12: Hypothesis Is an Explicitly Tentative Human Interpretation

One Hypothesis represents:

> One attributable, explicitly tentative explanation being considered by a human for one Event-local target.

Hypothesis is not an Observation, fact, determined cause, diagnosis, personality trait, proven motive, formal behavioral-function determination, or predictive risk score.

## 16.1 Hypothesis identity

Proposed identifier:

```text
hyp_<opaque-id>
```

Proposed public contracts:

```text
portia_hypothesis_id@1
hypothesis@1
```

Proposed storage:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/hypothesis/<hypothesis_id>.json
```

## 16.2 Hypothesis target

Hypothesis reuses `portia_target_ref@1`.

A participant-specific hypothesis applies only to the named Event Participant context.

It must not become a durable characteristic of the underlying student or Actor.

---

# 17. Proposed Decision 13: Hypothesis Proposition and Evidence Roles Are Explicit

Every Hypothesis contains one bounded human-authored proposition.

Proposed field:

```text
proposition
```

Supporting material is not embedded into the proposition.

Proposed evidence relation vocabulary:

```text
supporting
contrary
contextual
```

Each entry contains:

```text
relation
evidence_ref
```

Contrary evidence is first-class.

Application validation must reject repeated exact evidence identity within one logical evidence set even when structurally distinct wrappers are used.

Application validation must also be capable of detecting known Account lineage that makes several records non-independent.

Neither validation layer computes evidentiary weight.

---

# 18. Proposed Decision 14: Hypothesis Has No Numeric or Generic Confidence Score in v1

Issue #16 should not introduce:

```text
confidence_percent
truth_probability
evidence_score
credibility_score
risk_score
AI_confidence
```

The v1 Hypothesis contract expresses uncertainty through its explicit Hypothesis record type, supporting and contrary evidence, consideration state, and bounded human rationale where needed.

Proposed consideration-state vocabulary:

```text
under_consideration
set_aside
```

This is separate from canonical lifecycle status.

A valid Hypothesis may be set aside without being invalidated.

If reconsidered later, a new or successor Hypothesis should preserve that later human act rather than silently reactivating the old record.

---

# 19. Proposed Decision 15: Routine Event Hypothesis Is Not an FBA

Hypothesis v1 is Event-local.

It may record tentative contextual interpretations but must not present one Event as a formal functional behavioral assessment.

Longitudinal or formal FBA work may require multiple Events, occurrence and non-occurrence evidence, direct and indirect sources, team review, and Support Process ownership.

That cross-Event architecture belongs with Issue #18.

Issue #16 must not fabricate a synthetic Event owner merely to model a future FBA workspace.

---

# 20. Proposed Decision 16: Determination Is One Bounded Human Decision

One Determination represents:

> One attributable human decision answering one defined question for one Event-local target under one explicit decision-scope and authority context.

Determination is not an Account, Observation, Classification, Hypothesis, Response, consequence, behavior score, or student identity.

## 20.1 Determination identity

Proposed identifier:

```text
det_<opaque-id>
```

Proposed public contracts:

```text
portia_determination_id@1
determination@1
```

Proposed storage:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/determination/<determination_id>.json
```

## 20.2 Determination question

Every Determination must preserve the bounded question it answers.

A Determination must not be one unconstrained answer to:

```text
What kind of student is this?
```

---

# 21. Proposed Decision 17: Teacher-Local and Recorded Institutional Scope Are Explicit

Determination v1 must distinguish at least:

```text
teacher_local
recorded_institutional
```

`teacher_local` means Portia records a local teacher-controlled decision within the current deployment's honest scope.

It must not be displayed or exported as an authenticated institutional finding.

`recorded_institutional` means Portia records that an institutional or external decision was represented to the local system.

It does not mean Portia independently authenticated the decision-maker or conferred authority.

This distinction is mandatory because current Core provides no institution-wide staff identity, RBAC, or decision-authority service.

---

# 22. Proposed Decision 18: Decision-Maker Identity and Authority Are Separate

Determination uses a represented human decision-maker separate from persistence attribution.

Proposed reuse:

```text
represented_human_attribution@1
```

The human attribution answers who is represented as making the decision.

A separate nested authority context answers what kind of authority or decision scope is being represented and what basis, if any, was recorded for that claim.

Actor category, title, organization, email, display label, or local-operator status must not establish decision authority.

## 22.1 Proposed authority-context branches

### Teacher-local

```text
kind = teacher_local
scope
detail, optional
```

Initial scope vocabulary should remain narrow:

```text
classroom_management
teacher_support_workflow
other
```

`other` requires detail.

### Recorded institutional

```text
kind = recorded_institutional
authority_label
authority_status
authority_basis, optional
```

Proposed authority-status vocabulary:

```text
source_evidenced
asserted
unknown
```

This is not a truth score.

It states only what authority provenance Portia has recorded.

Active consequential use of a `recorded_institutional` Determination may require stronger application-level authority evidence than structural storage.

An imported historical Determination may remain structurally valid with `authority_status = unknown`.

---

# 23. Proposed Decision 19: Process or Policy Basis Is Separate from Authority

Decision authority and the policy/process applied are distinct.

A person may be represented as an authorized decision-maker while the governing policy basis is missing, unsupported, or not applicable.

Determination should therefore have a separate process-basis union.

Proposed branches:

```text
teacher_local
identified_policy_or_process
unknown
```

An identified policy/process basis should preserve bounded historical identity such as label, version when known, and source references when available.

Issue #16 should not create a universal district-policy registry.

A source reference does not prove that the policy was correctly applied.

---

# 24. Proposed Decision 20: Determination Outcome Is a Closed Union

Determination v1 must permit honest uncertainty.

Proposed outcome branches:

```text
conclusion
coded_conclusion
insufficient_information
unable_to_determine
not_applicable
```

`conclusion` preserves a bounded human decision statement.

`coded_conclusion` preserves a local or external controlled outcome with historical scheme/code/version identity.

The schema must not hard-code one universal discipline finding vocabulary.

Terms such as `substantiated` and `not_substantiated` may appear only as identified local/external coded outcomes where that policy or process uses them.

`not_substantiated` must not automatically invalidate Accounts, Observations, Classifications, or Hypotheses.

---

# 25. Proposed Decision 21: Determination Basis Preserves Supporting and Contrary References

Determination may preserve exact or typed basis references using `judgment_evidence_ref@1`.

Proposed relation vocabulary:

```text
supporting
contrary
contextual
```

The presence of a reference means the human decision record cites or records consideration of that material in that role.

It does not mean Portia agrees with the evidence or computes its weight.

A Determination must not automatically inherit every record in the parent Review.

The human-authored Determination basis is explicit.

---

# 26. Proposed Decision 22: Repeated Reports Never Become Proof by Count

Portia must not implement rules such as:

```text
three Accounts = substantiated
two Observations = confirmed
majority of sources = true
```

Account lineage from ADR 0011 remains relevant.

Two canonical Accounts may represent independent sources, the same upstream source, secondhand repetition, a clarification, a retraction, or duplicate capture.

Application validation may identify known shared lineage, duplicate references, or repeated exact identity.

It must not convert those facts into automatic credibility or proof.

---

# 27. Proposed Decision 23: All Four New Families Reuse Event-Local Targeting

Review, Classification, Hypothesis, and Determination v1 reuse:

```text
portia_target_ref@1
```

Allowed target forms:

```text
the containing Event
one Event Participant
an explicit set of Event Participants
```

An Event-level judgment does not automatically apply to every participant.

A multi-participant judgment does not automatically establish identical conduct, responsibility, evidence, finding, or Response for each participant.

The consuming record must honestly support one shared judgment before multi-targeting is used.

---

# 28. Proposed Decision 24: Judgment Records Use a Common Canonical Lifecycle

Proposed canonical lifecycle for Classification, Hypothesis, and Determination:

```text
proposed
active
invalidated
superseded
```

Review uses the same canonical lifecycle plus its separate review workflow state.

## 28.1 Invalidation

Invalidation means the record itself is not a valid current representation because of a defect such as:

```text
recording_error
wrong_human
wrong_target
wrong_definition
wrong_authority
invalid_provenance
prohibited_payload
```

Invalidation must not mean a later human disagreed, a later reviewer chose another Classification, a Hypothesis was set aside, or a valid Determination was later reversed.

## 28.2 Supersession

Supersession preserves valid historical records when a new canonical representation replaces or evolves the prior one.

Examples include material correction, Hypothesis refinement, Determination reconsideration, Determination reversal, duplicate consolidation, work-root correction, and contract migration.

---

# 29. Proposed Decision 25: Reconsideration and Reversal Create New Records

A valid Determination later changed through reconsideration is not invalidated merely because the decision changed.

Preferred topology:

```text
Review B
    review_type = reconsideration
    subject_ref = exact Determination A

Determination B
    review_ref = Review B
    supersedes = exact Determination A
    supersession reason = reconsidered | reversed_on_reconsideration
```

Determination A remains historically resolvable.

The predecessor may transition to `superseded` through the existing lifecycle infrastructure.

No in-place rewrite changes the prior decision outcome.

---

# 30. Proposed Decision 26: Classification Disagreement Is Not Supersession by Default

If a reviewer selects a category different from a reporter:

```text
reporter Classification A
reviewer Classification B
```

Classification B does not supersede A merely because B is later or more authoritative in a specific workflow.

They represent different human assertions.

A derived current-view rule may prefer a reviewer-stage Classification for a reviewer-oriented display, but the reporter Classification remains canonical and attributable.

Supersession is reserved for replacement of the same logical human assertion or representation, not ordinary disagreement among different human judgments.

---

# 31. Proposed Decision 27: Hypothesis Refinement May Use Supersession

A later Hypothesis may genuinely refine an earlier Hypothesis from the same review lineage.

Examples include statement correction, scope narrowing, materially refined evidence interpretation, and target correction.

When the later record is intended to replace the earlier Hypothesis as that author's current proposition, successor/supersession is appropriate.

Different competing Hypotheses do not supersede one another merely because they conflict.

---

# 32. Proposed Decision 28: No New Family Gets Broad In-Place Amendment in v1

Review, Classification, Hypothesis, and Determination v1 should expose no broad Amendment surface.

Material changes to target, review question, reviewer, Classification selector, Classification result, definition identity, Hypothesis proposition, Hypothesis author, decision question, decision outcome, decision-maker, authority context, or policy/process basis require replacement or a new record.

Open Review workflow progression is not treated as correction.

If implementation later identifies genuinely nonmaterial safe fields, they may be considered through a new contract version rather than inventing permissive v1 Amendment paths.

---

# 33. Proposed Decision 29: Statement of Disagreement Is Reused

The existing:

```text
statement_of_disagreement@1
```

can target generic exact work records.

It should be reused for attributable dispute or qualification of Classification, Hypothesis, and Determination where application policy permits.

A Statement of Disagreement does not invalidate, supersede, reverse, adjudicate, or prove wrong its target.

A reversal requires a new Determination and explicit lifecycle/reconsideration history.

---

# 34. Proposed Decision 30: Paper and Import Never Create Automatic Judgment

Reuse:

```text
creation_source@1
source_artifact_ref@1
```

## 34.1 Paper

Page preallocation must not fabricate Classification, Hypothesis, or Determination.

A Review may exist before printing when it is the legitimate workflow context for a review packet.

Returned paper may produce proposed judgment records only after human interpretation.

OCR or mark recognition may transcribe structure.

It must not establish human reviewer, Classification correctness, Hypothesis truth, decision-maker, decision authority, policy applicability, or Determination outcome automatically.

## 34.2 Import

Imported historical categories and findings may have incomplete provenance.

Portia must preserve uncertainty rather than fabricate reviewer-confirmed status, definition version, decision-maker identity, institutional authority, or policy version.

An imported institutional record may be stored in a proposed or historical representation with unknown authority context until reviewed.

Source-system prestige does not establish truth or current-use eligibility.

---

# 35. Proposed Decision 31: Automation May Organize Review but Not Make Judgment

Permitted automation includes:

```text
structural validation
completeness checks
due-date reminders
review queues
missing-evidence warnings
definition lookup
policy checklist display
duplicate-reference detection
known-lineage warnings
unsupported-version warnings
derived navigation
```

Prohibited automatic judgment includes:

```text
classifying prose
inferring intent
inferring behavioral function
ranking Hypotheses
deciding credibility
substantiating allegations
determining policy violation
recommending punishment
predictive behavior scoring
automatic risk scoring
Observation -> Determination conversion
report-count -> proof conversion
```

A `system_process` may persist or import a proposed record.

It may not be represented as the substantive human selector, Hypothesis author, reviewer, or decision-maker.

---

# 36. Proposed Decision 32: Operational and Derived Records Remain Privacy-Minimized

Operational infrastructure may retain:

```text
opaque IDs
record kinds
contract versions
paths
fingerprints
byte lengths
status tokens
counts
machine-readable defect codes
```

It should not copy Classification rationale, Hypothesis proposition, Determination conclusion, Account quotation/summary, Observation narrative, or sensitive authority detail merely for coordination or diagnostics.

Quarantine free-text fields require application-level privacy controls.

Integrity Findings remain integrity diagnostics and must not become substantive judgment records such as credible allegation, valid Hypothesis, policy violation, or substantiated Determination.

---

# 37. Proposed Decision 33: Shared Infrastructure Is Reused Without Parallel Families

The initial implementation should prove compatibility with:

```text
lifecycle_transition@1
lifecycle_history_correction@1
statement_of_disagreement@1
dependency@1
record_migration@1
ownership_correction@1
exceptional_removal@1

operation_journal
operation_lock
quarantine_record
integrity_finding

source_snapshot
derived_index_metadata
derived_current_pointer
```

Do not publish parallel contracts such as:

```text
classification_dependency
determination_operation_journal
hypothesis_quarantine
review_record_migration
```

unless an existing published wire shape genuinely cannot express the requirement.

Dedicated exact reference families are not expected. Existing exact generic work-record references should be sufficient.

---

# 38. Proposed Public Contract Plan

If ADR 0012 accepts this design, the expected new public contracts are:

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

Expected paths:

```text
schemas/v1/identifiers/portia-review-id.schema.json
schemas/v1/identifiers/portia-classification-id.schema.json
schemas/v1/identifiers/portia-hypothesis-id.schema.json
schemas/v1/identifiers/portia-determination-id.schema.json

schemas/v1/references/judgment-evidence-ref.schema.json

schemas/v1/reviews/review.schema.json
schemas/v1/classifications/classification.schema.json
schemas/v1/hypotheses/hypothesis.schema.json
schemas/v1/determinations/determination.schema.json
```

The exact schema organization remains pre-ADR until the design is frozen.

No standalone public contract is currently proposed for Review trigger, Classification definition, Hypothesis confidence, decision authority, policy/process basis, or Determination outcome because each currently has only one immediate semantic owner or does not yet justify independent versioning.

---

# 39. Structural Validation Boundary

JSON Schema should enforce local wire shape such as:

```text
closed envelopes
record constants
ID syntax
target shape
human-attribution shape
Review question and workflow state
Classification stage and result union
Classification definition identity fields
Hypothesis proposition
Hypothesis evidence-role vocabulary
Hypothesis consideration state
Determination question
decision scope / authority branch
process-basis branch
outcome branch
evidence-reference structure
paper/import shape
timestamps
supersession shape
reason/detail compatibility
```

Schema should reject obviously prohibited shortcuts such as:

```text
credibility_score
truth_score
behavior_score
risk_score
AI_confidence
student_label
automatic_finding
automatic_determination
```

when added as unsupported record properties.

---

# 40. Application Validation Boundary

Application logic remains responsible for:

```text
canonical path agreement
parent Event resolution
same-Event target resolution
Review-subject resolution
reviewer / selector / author / decision-maker resolution
current-use identity eligibility

Classification definition availability
definition-version support
reporter/reviewer relationship
current-view selection

evidence resolution
evidence contract support
duplicate logical evidence identity
known Account source lineage
supporting/contrary semantics
no count-as-proof behavior

decision authority sufficiency
decision scope compatibility
policy/process basis sufficiency

chronology
Review workflow transitions
record lifecycle matrices
completion freezing

paper/import review gates
no automated human judgment

materiality
supersession topology
reconsideration topology
reversal topology
self-supersession prohibition
cycle prohibition
no silent successor following

incoming-reference reconciliation
Dependency evaluation
migration
ownership correction
exceptional removal

authorization boundary
privacy
recoverable coordinated persistence
derived freshness
```

---

# 41. Deferred Work

Issue #16 does not define production authorization, institutional staff identity, RBAC, district policy registry, Response, Communication, Support Process, Support/Intervention, formal FBA workspace, Follow-Up, Outcome, paper-capture implementation, complete privacy/export/retention policy, or end-to-end foundation graphs.

Formal cross-Event FBA or team Hypothesis ownership should be revisited in Issue #18 after `support_process` is concrete.

Institutional authentication and authorization remain a future platform concern beyond the current teacher-local deployment.

---

# 42. Pre-ADR Questions to Freeze

The next design-freeze slice should explicitly confirm:

1. whether `judgment_evidence_ref@1` should include raw `source_artifact_ref` or only canonical record references;
2. the final Review trigger and Review question vocabularies;
3. whether Review evidence may be appended in place until completion, as proposed;
4. the exact Classification stage names;
5. the exact Classification result and definition fields;
6. whether Hypothesis `set_aside` remains a separate consideration state rather than lifecycle status;
7. the exact teacher-local authority-scope vocabulary;
8. the exact recorded-institutional authority-status vocabulary;
9. the exact Determination process-basis and outcome unions;
10. family-specific lifecycle reasons and supersession reasons;
11. current-use rules for imported historical judgments with incomplete identity or authority;
12. whether all four v1 families expose no Amendment paths.

No public schema should be published before these questions are frozen.

---

# 43. Planned Implementation Sequence

A bounded implementation sequence is:

```text
Slice 1
    initial repository checkpoint
    working pre-ADR design

Slice 2
    pre-ADR drift checkpoint
    frozen design decisions
    ADR 0012

Slice 3
    identifier primitives
    judgment_evidence_ref@1

Slice 4
    review@1

Slice 5
    classification@1

Slice 6
    hypothesis@1

Slice 7
    determination@1

Slice 8
    lifecycle / disagreement / dependency compatibility

Slice 9
    migration / removal / operational / derived privacy compatibility

Slice 10
    examples
    application-invalid matrix
    acceptance matrix
    final validation and drift checkpoint

Slice 11, if needed
    README / schema-guide / historical-document reconciliation
```

The sequence may be compressed only when adjacent slices remain reviewable and do not force premature public-contract decisions.
