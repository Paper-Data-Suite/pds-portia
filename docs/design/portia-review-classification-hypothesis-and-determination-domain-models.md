# Portia Review, Classification, Hypothesis, and Determination Domain Models

**Status:** Accepted architecture — ADR 0012
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#16 — Define review, Classification, Hypothesis, and Determination domain models`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-07
**Branch:** `16-review-classification-hypothesis-determination-domain-models`

## 1. Purpose

This document defines the accepted ADR 0012 architecture for Portia's human review, interpretation, and decision layer.

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

The pre-ADR drift check found no Portia-main or Core drift requiring a contract change. A final drift check remains required before Issue #16 closes.

Pre-ADR checkpoint result:

```text
pds-portia/main = 35df69904cff3c696876f04e208bbe704bab3e97
Issue #16 branch = 71372063da4aad9dc85a61927aa8b6aaa793b587
                    1 commit ahead, 0 behind main
pds-core/main = 6c507213618b68a6dd3ea096e1a898201ff029e6

classification:
    Portia main drift: none
    Core drift: none
    sibling contract change: none required
```

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

# 5. Approved Decision 1: Review Is a Canonical Event-Local Record

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

# 6. Approved Decision 2: Concern and Referral Are Review-Initiation Context in v1

Issue #16 does not introduce separate canonical Concern or Referral record families merely to drive navigation.

For the initial Event-local judgment layer, concern/referral semantics are represented as bounded Review initiation context.

Accepted trigger vocabulary:

```text
concern
referral
routine_review
reconsideration
support_related
other
```

`other` requires concise detail.

The trigger identifies why the Review was opened, not who requested it. When the workflow genuinely records a requester, Review may preserve an optional `requested_by` using `represented_human_attribution@1`.

This avoids encoding the requester's relationship into the trigger vocabulary. A teacher, student, family member, Actor, descriptive person, or other represented human may initiate a concern/referral workflow without creating a parallel trigger taxonomy.

Review initiation context does not answer what happened, whether a category is correct, whether a hypothesis is supported, whether a policy applies, or whether misconduct occurred.

Paper or import provenance remains `creation_source`; capture medium is not a trigger kind.

If later implementation demonstrates that Referral needs independent identity, provenance, lifecycle, routing history, or cross-work existence, that must be introduced through a later explicit contract rather than inferred from this navigation field.

# 7. Approved Decision 3: Review Lifecycle and Review Workflow State Are Separate

Review has two distinct state dimensions.

## 7.1 Canonical record lifecycle

Accepted lifecycle vocabulary:

```text
proposed
active
invalidated
superseded
```

This answers whether the canonical Review representation is valid and current.

## 7.2 Review workflow state

Accepted review-state vocabulary:

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

Review v1 uses a guarded current-workflow record while the review is still in progress.

Before activation, a `proposed` Review may be revised within structural and application constraints.

After activation:

- `target`, `question`, substantive reviewer identity, trigger semantics, and creation provenance are materially fixed;
- `review_state` may advance through the permitted workflow-state matrix;
- `evidence_considered` may append exact references as material is actually reviewed;
- previously recorded evidence identities are not silently removed or rewritten;
- revision-aware persistence and coordinated-operation rules apply to every in-place workflow update.

Once `review_state` becomes `completed` or `cancelled`, the substantive Review snapshot is frozen.

Later reconsideration creates a new Review linked to the prior Review rather than reopening or rewriting the completed record.

An erroneous active evidence entry, target, question, or reviewer is a material correction and requires successor/history handling rather than destructive editing.

Review workflow progression is not an Amendment. Review v1 exposes no generic Amendment path.

# 8. Approved Decision 4: Reviewer and Recorder Are Separate

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

# 9. Approved Decision 5: Review Question Is Explicit and Bounded

Every Review must state the question being reviewed.

Accepted structure:

```text
question:
    kind
    text
```

Accepted `kind` vocabulary:

```text
evidence_review
classification_review
hypothesis_review
determination_review
reconsideration
other
```

`text` is required for every branch and is the bounded human-readable question. Because the question text is always required, `other` does not require a second detail field.

The question must not become an unrestricted student-profile narrative.

Examples:

```text
What information is available concerning the participant-specific report?

Does the reporter-selected local category remain appropriate under the reviewed definition?

What tentative explanations remain supported or contradicted by the reviewed evidence?

Is there sufficient information to record a teacher-local conclusion?

Should the prior Determination be reconsidered?
```

A Review may also identify exact subject records under review, such as an earlier Classification, Hypothesis, or Determination.

The Event-local `target` still answers whom or what the Review concerns.

# 10. Approved Decision 6: Review Records What Was Actually Considered

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

# 11. Approved Decision 7: Add One Shared Judgment-Evidence Reference Primitive

Review, Classification where a basis is explicitly preserved, Hypothesis, and Determination have an immediate shared need to identify canonical material considered without embedding its payload.

Accepted public primitive:

```text
judgment_evidence_ref@1
```

Accepted nonoverlapping branches:

```text
portia_work
portia_record
module_record
```

`portia_work` wraps `exact_portia_work_ref@1`.

`portia_record` wraps `exact_portia_work_record_ref@1`.

`module_record` wraps `module_work_record_ref@1`.

The primitive does not carry evidence weight, credibility, truth, corroboration count, source independence, or decision outcome. It answers only which canonical Portia work, exact Portia record representation, or typed sibling-module record the consuming judgment record cites.

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

Classification may use the primitive for optional basis references but is not required to imply adjudicative evidence weight.

## 11.1 Raw source artifacts are intentionally excluded

`judgment_evidence_ref@1` does **not** wrap `source_artifact_ref@1`.

This is intentional for two reasons.

First, `source_artifact_ref@1` already contains Portia-record and sibling-module-record branches. Wrapping the complete source-artifact union alongside direct Portia/module branches would create overlapping logical reference forms for the same canonical record.

Second, Issue #15 established Account and Observation as Portia's source-evidence layer. When the substantive contents of paper, an image, audio/video, a workspace file, email, screenshot, or another raw artifact matter to a Review or judgment, the relevant human statement or direct artifact-review observation should first be preserved through an Account or Observation and then referenced canonically.

This prevents Review/Hypothesis/Determination from bypassing the source-evidence layer.

Raw artifacts may still appear in record-specific provenance contexts, such as documented decision-authority or policy/process material, using `source_artifact_ref@1` where its locator-without-proof semantics are appropriate. Such provenance is not part of the judgment evidence set merely because it is attached to the same record.

# 12. Approved Decision 8: Classification Is One Attributed Category Selection

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

# 13. Approved Decision 9: Reporter and Reviewer Classifications Are Separate Assertions

Accepted classification-stage vocabulary:

```text
reporter_selected
reviewer_selected
reviewer_confirmed
unknown
```

`reporter_selected` preserves a category or inability-to-determine outcome selected by a reporting human before substantive reviewer adjudication.

`reviewer_selected` preserves a reviewer's own category or inability-to-determine outcome. It may reference an earlier Classification under review, but it does not imply agreement with that Classification.

`reviewer_confirmed` is an explicit reviewer assertion that the reviewed earlier Classification remains the selected category. Application validation requires an exact reviewed Classification and the same result semantics when this stage is used: matching result branch, and matching category identity when both results are `category_selected`.

`unknown` exists for historical/imported material whose original review stage cannot be reconstructed honestly. It must not be treated as reviewer-confirmed for current-use eligibility.

A reviewer-selected or reviewer-confirmed Classification may reference the exact earlier Classification it reviewed.

A reviewer disagreement does not invalidate or supersede the reporter's Classification merely because the reviewer selected another result.

Example:

```text
Classification A
stage = reporter_selected
result = category_selected / disruption

Classification B
stage = reviewer_selected
reviews = Classification A
result = unable_to_determine
```

Both remain attributable historical records.

Use invalidation only when a Classification record itself is incorrect as a record, for example wrong selector, wrong target, wrong definition identity, recording error, or invalid provenance.

Do not use correction semantics to erase a legitimate difference of judgment.

# 14. Approved Decision 10: Classification Result Is a Closed Union

Classification does not force a category when the human cannot make one.

Accepted result branches:

```text
category_selected
unable_to_determine
```

`category_selected` preserves one nested historical definition snapshot:

```text
definition:
    scheme_id
    scheme_version
    category_code
    category_label
    definition_text
```

Canonical category identity for v1 comparison is:

```text
scheme_id + scheme_version + category_code
```

`category_label` and `definition_text` are required historical presentation/meaning snapshots. They do not replace the identity tuple and do not establish that the local definition was lawful, unbiased, institutionally approved, or correctly applied.

The initial architecture does not define one suite-wide behavior taxonomy.

Classification schemes remain Portia-scoped local or imported configuration context unless a later explicit configuration contract is justified.

`unable_to_determine` is a real human classification outcome, not a fake behavior category. A concise rationale may explain why no category was selected, but the absence of a category must not be encoded through a fabricated code such as `unknown_behavior`.

# 15. Approved Decision 11: Classification Definition Identity Is Nested in v1

Issue #16 does not publish a classification-definition registry merely because Classification needs stable historical meaning.

Classification v1 preserves the definition identity and bounded definition snapshot directly in the `category_selected` result branch.

This keeps historical Classification meaning readable even when a separately managed local taxonomy does not yet exist as a canonical Portia contract.

The nested definition snapshot is not an authority registry and is not independently mutable.

If a later workflow requires separately managed local taxonomies with their own identity, lifecycle, activation dates, examples, nonexamples, ownership, governance, or migration, that should become a dedicated configuration contract and a future Classification version may reference it explicitly.

# 16. Approved Decision 12: Hypothesis Is an Explicitly Tentative Human Interpretation

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

# 17. Approved Decision 13: Hypothesis Proposition and Evidence Roles Are Explicit

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

# 18. Approved Decision 14: Hypothesis Has No Numeric or Generic Confidence Score in v1

Issue #16 does not introduce:

```text
confidence_percent
truth_probability
evidence_score
credibility_score
risk_score
AI_confidence
```

Hypothesis v1 expresses uncertainty through its explicit Hypothesis record type, supporting and contrary evidence, consideration state, and bounded human rationale where needed.

Accepted consideration-state vocabulary:

```text
under_consideration
set_aside
```

This is separate from canonical lifecycle status.

A valid Hypothesis may be set aside without being invalidated. `set_aside` means the human workflow is no longer actively considering that proposition in the current review context; it does not mean the proposition was proven false.

If a later human reconsiders or materially refines the proposition, a new or successor Hypothesis preserves that later act rather than silently toggling the historical record back to `under_consideration`.

No qualitative confidence enum is added in v1. The explicit tentativeness of the record family and its evidence/rationale are preferred to an underspecified `low` / `medium` / `high` scale.

# 19. Approved Decision 15: Routine Event Hypothesis Is Not an FBA

Hypothesis v1 is Event-local.

It may record tentative contextual interpretations but must not present one Event as a formal functional behavioral assessment.

Longitudinal or formal FBA work may require multiple Events, occurrence and non-occurrence evidence, direct and indirect sources, team review, and Support Process ownership.

That cross-Event architecture belongs with Issue #18.

Issue #16 must not fabricate a synthetic Event owner merely to model a future FBA workspace.

---

# 20. Approved Decision 16: Determination Is One Bounded Human Decision

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

# 21. Approved Decision 17: Teacher-Local and Recorded Institutional Scope Are Explicit

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

# 22. Approved Decision 18: Decision-Maker Identity and Authority Are Separate

Determination uses a represented human decision-maker separate from persistence attribution.

Accepted reuse:

```text
represented_human_attribution@1
```

ADR 0011 explicitly permits later Portia records to adopt this primitive when they need the same represented-human semantics. Issue #16 uses it only to answer which human is represented as reviewer, selector, Hypothesis author, or decision-maker. It does not confer authority.

A separate nested authority context answers what kind of decision scope is being represented and what authority provenance, if any, was recorded.

Actor category, title, organization, email, display label, or local-operator status must not establish decision authority.

## 22.1 Teacher-local authority context

Accepted shape:

```text
kind = teacher_local
scope
detail, optional
```

Accepted scope vocabulary:

```text
classroom_management
teacher_review
teacher_support_coordination
other
```

`other` requires detail.

These values describe the bounded teacher-local workflow context. They do not claim institutional delegation.

## 22.2 Recorded-institutional authority context

Accepted shape:

```text
kind = recorded_institutional
authority_label
authority_status
authority_basis, conditional
```

Accepted authority-status vocabulary:

```text
documented_basis
asserted
unknown
```

`documented_basis` requires at least one typed authority-basis reference. It means Portia retains material documenting the authority claim; it does **not** mean Portia authenticated the person or proved that the authority was legally sufficient.

`asserted` means the represented decision record states or was recorded as having institutional/external authority, but Portia retains no typed authority-basis material sufficient to use `documented_basis`.

`unknown` means the available historical/imported record does not permit an honest characterization of authority provenance.

Authority-basis references are provenance, not judgment evidence. They may reuse `source_artifact_ref@1` when the reference means exactly "where the material documenting this claim can be found" without asserting authenticity, authorization, or evidentiary weight.

Current PDS does not provide institutional staff authentication or RBAC. No authority-status value, including `documented_basis`, may be interpreted as Portia independently authenticating institutional authority.

## 22.3 Role-specific human eligibility is application-level

Reusing `represented_human_attribution@1` does not mean every attribution branch is eligible for every judgment role.

For current-use v1 application validation:

- a `teacher_local` Determination requires a `local_operator` decision-maker;
- a `recorded_institutional` Determination may preserve an Actor, local operator, descriptive school-staff person, or unidentified historical decision-maker, subject to authority-status rules;
- a roster student or non-staff descriptive person does not become an institutional decision-maker merely because the structural human-attribution union can represent that person;
- `unidentified_person` may preserve historical/imported judgment attribution but cannot satisfy a workflow that requires a resolved current human decision-maker;
- reviewer and reviewer-stage Classification eligibility is likewise workflow-dependent and must not be inferred from structural attribution alone.

This keeps the reusable human identity shape separate from consumer-specific authority and role eligibility.

# 23. Approved Decision 19: Process or Policy Basis Is Separate from Authority

Decision authority and the policy/process applied are distinct.

A person may be represented as a decision-maker while the governing policy or process basis is missing, unsupported, unknown, or purely teacher-local.

Determination therefore uses a closed process-basis union.

Accepted branches:

```text
teacher_local
identified
unknown
```

## 23.1 Teacher-local process basis

```text
kind = teacher_local
process_label
```

`process_label` is a bounded human-readable description of the local teacher workflow or decision context. It is not a policy identifier and does not imply institutional authorization.

## 23.2 Identified policy/process basis

```text
kind = identified
policy, optional
process, optional
```

At least one of `policy` or `process` is required.

Each descriptor preserves:

```text
label
version, optional
source_artifacts, optional
```

A source artifact is a provenance locator only. It does not prove that the policy/process was current, applicable, lawful, or correctly applied.

The design does not create a universal district-policy registry.

## 23.3 Unknown process basis

```text
kind = unknown
```

This supports honest historical/import representation without fabricating a policy or process identity.

Application validation determines whether a consuming workflow requires an identified policy/process basis. Structural validity alone does not establish applicability.

# 24. Approved Decision 20: Determination Outcome Is a Closed Union

Determination v1 permits honest uncertainty and does not hard-code one universal discipline vocabulary.

Accepted outcome branches:

```text
conclusion
coded_conclusion
insufficient_information
unable_to_determine
not_applicable
```

## 24.1 Conclusion

```text
kind = conclusion
text
```

This preserves a bounded human decision statement.

## 24.2 Coded conclusion

```text
kind = coded_conclusion
scheme_id
scheme_version
code
label
definition_text
```

Canonical coded-outcome identity for v1 comparison is:

```text
scheme_id + scheme_version + code
```

`label` and `definition_text` are historical meaning snapshots, not proof that the scheme was authoritative or correctly applied.

Terms such as `substantiated` and `not_substantiated` may appear only as identified coded outcomes where the named local/external scheme uses them.

## 24.3 Insufficient information

`insufficient_information` means the decision-maker records that the available information is insufficient to answer the bounded determination question under the represented process or standard.

It does not mean nothing occurred and does not invalidate source evidence.

## 24.4 Unable to determine

`unable_to_determine` records that no determination can be made, without asserting the specific evidentiary conclusion represented by `insufficient_information`.

## 24.5 Not applicable

`not_applicable` records that the bounded question/process does not apply to the target or reviewed circumstances.

It does not erase the Event or its evidence.

A bounded optional rationale may accompany any outcome. Rationale remains the decision-maker's explanation, not copied source evidence.

`not_substantiated` must never automatically invalidate Accounts, Observations, Classifications, or Hypotheses.

# 25. Approved Decision 21: Determination Basis Preserves Supporting and Contrary References

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

# 26. Approved Decision 22: Repeated Reports Never Become Proof by Count

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

# 27. Approved Decision 23: All Four New Families Reuse Event-Local Targeting

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

# 28. Approved Decision 24: Judgment Records Use a Common Canonical Lifecycle

Review, Classification, Hypothesis, and Determination use the same canonical status vocabulary:

```text
proposed
active
invalidated
superseded
```

Review additionally has the separate workflow state defined in Decision 3.

Accepted transition matrix for all four families:

```text
proposed
    -> active
    -> invalidated
    -> superseded

active
    -> invalidated
    -> superseded

invalidated
    -> superseded

superseded
    -> no later state
```

A record may also be created directly active when a permitted human-reviewed digital workflow produces a complete canonical record. Paper/import proposals do not gain active status automatically.

## 28.1 Lifecycle reason vocabularies

### Review

```text
review_started
recording_error
wrong_reviewer
wrong_target
wrong_question
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Classification

```text
judgment_recorded
recording_error
wrong_selector
wrong_target
wrong_definition
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Hypothesis

```text
judgment_recorded
recording_error
wrong_author
wrong_target
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Determination

```text
judgment_recorded
recording_error
wrong_decision_maker
wrong_target
wrong_authority
wrong_process_basis
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

`other` requires bounded detail.

`review_started` and `judgment_recorded` are the family-specific activation reasons when a proposed record is accepted into active canonical use through transition history. They do not authorize an automated judgment.

## 28.2 Invalidation

Invalidation means the record itself is not a valid current representation because of a defect such as wrong attribution, wrong target, wrong definition/authority/process basis, recording error, invalid provenance, or prohibited payload.

Invalidation must not mean a later human disagreed, a later reviewer chose another Classification, a Hypothesis was set aside, or a valid Determination was later reversed.

## 28.3 Supersession reasons

### Review

```text
review_corrected
review_reframed
reviewer_corrected
target_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Classification

```text
classification_corrected
selector_corrected
target_corrected
definition_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Hypothesis

```text
hypothesis_corrected
hypothesis_refined
hypothesis_reconsidered
author_corrected
target_corrected
evidence_role_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

### Determination

```text
outcome_corrected
question_corrected
decision_maker_corrected
target_corrected
authority_corrected
process_basis_corrected
reconsidered
reversed_on_reconsideration
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Every predecessor in one successor operation must use the same logical supersession reason. `other` requires detail.

Ordinary cross-human disagreement is not supersession.

# 29. Approved Decision 25: Reconsideration and Reversal Create New Records

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

# 30. Approved Decision 26: Classification Disagreement Is Not Supersession by Default

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

# 31. Approved Decision 27: Hypothesis Refinement May Use Supersession

A later Hypothesis may genuinely refine an earlier Hypothesis from the same review lineage.

Examples include statement correction, scope narrowing, materially refined evidence interpretation, and target correction.

When the later record is intended to replace the earlier Hypothesis as that author's current proposition, successor/supersession is appropriate.

Different competing Hypotheses do not supersede one another merely because they conflict.

---

# 32. Approved Decision 28: No New Family Gets an In-Place Amendment Surface in v1

Review, Classification, Hypothesis, and Determination v1 expose **no permitted Amendment paths**.

This is stricter than merely rejecting broad Amendment.

Material changes to target, Review question, reviewer, Classification selector, Classification result, definition identity, Hypothesis proposition, Hypothesis author, decision question, decision outcome, decision-maker, authority context, policy/process basis, or completed evidence/basis sets require replacement, a new judgment record, or a new reconsideration Review as appropriate.

Open Review workflow progression is not an Amendment. It is guarded revision-aware mutation of the still-active review process under Decision 3.

A `proposed` record may be revised before activation because it is not yet an accepted current judgment representation.

Once a Classification, Hypothesis, or Determination is active, substantive correction uses successor/history semantics. A future contract version may introduce specifically justified nonmaterial Amendment paths, but v1 does not guess at them.

# 33. Approved Decision 29: Statement of Disagreement Is Reused

The existing:

```text
statement_of_disagreement@1
```

can target generic exact work records.

It should be reused for attributable dispute or qualification of Classification, Hypothesis, and Determination where application policy permits.

A Statement of Disagreement does not invalidate, supersede, reverse, adjudicate, or prove wrong its target.

A reversal requires a new Determination and explicit lifecycle/reconsideration history.

---

# 34. Approved Decision 30: Paper and Import Never Create Automatic Judgment

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

Portia preserves uncertainty rather than fabricating reviewer-confirmed status, definition version, decision-maker identity, institutional authority, or policy version.

Imported judgment records begin `proposed` unless they are created through an explicit governed migration of an already accepted Portia representation.

Local human review may activate an imported historical representation even when some original metadata remains unknown, because canonical existence and consequential-use eligibility are separate concepts.

After activation:

- a Classification with `stage = unknown` remains ineligible to satisfy any consumer that specifically requires a reviewer-confirmed Classification;
- a Review/Classification/Hypothesis whose represented human remains `unidentified_person` may be preserved historically but does not satisfy a consumer requiring resolved current human attribution;
- a `recorded_institutional` Determination with `authority_status = unknown` or `asserted` may be preserved and displayed with that limitation but cannot be presented as authenticated institutional authority;
- `authority_status = documented_basis` means Portia has typed material supporting the authority claim, not that current PDS authenticated the decision-maker or proved legal sufficiency;
- no imported historical judgment automatically creates a Response, Support, lifecycle change, or other consequential downstream record.

Source-system prestige does not establish truth, authority, or current-use eligibility.

# 35. Approved Decision 31: Automation May Organize Review but Not Make Judgment

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

# 36. Approved Decision 32: Operational and Derived Records Remain Privacy-Minimized

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

# 37. Approved Decision 33: Shared Infrastructure Is Reused Without Parallel Families

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

# 38. Accepted Public Contract Plan

ADR 0012 accepts the following initial public-contract plan:

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

No standalone public contract is introduced in v1 for Review trigger, Review question, Classification definition, Hypothesis confidence, decision authority, process/policy basis, or Determination outcome. Those structures currently have one immediate semantic owner or are not yet stable enough to justify independent public versioning.

`judgment_evidence_ref@1` is the only new shared value object because Review, optional Classification basis, Hypothesis, and Determination have multiple immediate consumers requiring the same canonical-reference semantics.

Dedicated exact Review/Classification/Hypothesis/Determination reference families are not planned. Existing exact generic work-record references already provide the required identity and historical exactness.

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

# 42. Frozen Pre-ADR Decisions

The pre-ADR freeze resolved all twelve questions from Slice 1.

1. **Judgment evidence reference:** `judgment_evidence_ref@1` includes only `portia_work`, `portia_record`, and `module_record`; raw `source_artifact_ref` is excluded from judgment evidence.
2. **Review trigger/question vocabularies:** trigger is `concern | referral | routine_review | reconsideration | support_related | other`; question kind is `evidence_review | classification_review | hypothesis_review | determination_review | reconsideration | other`, with required bounded question text.
3. **Open Review mutation:** proposed Reviews may be edited before activation; active nonterminal Reviews may advance workflow state and append evidence under revision-aware persistence; substantive identity/question/target changes require successor handling; completed/cancelled Reviews are frozen.
4. **Classification stage:** `reporter_selected | reviewer_selected | reviewer_confirmed | unknown`.
5. **Classification result/definition:** `category_selected | unable_to_determine`; category identity is `scheme_id + scheme_version + category_code`, with required label and definition-text snapshot.
6. **Hypothesis set-aside:** `set_aside` remains a consideration state, not lifecycle status; no confidence/probability field is added in v1.
7. **Teacher-local authority scope:** `classroom_management | teacher_review | teacher_support_coordination | other`.
8. **Recorded-institutional authority status:** `documented_basis | asserted | unknown`; none authenticates institutional authority.
9. **Determination process/outcome:** process basis is `teacher_local | identified | unknown`; outcome is `conclusion | coded_conclusion | insufficient_information | unable_to_determine | not_applicable`.
10. **Lifecycle/supersession reasons:** family-specific inventories in Decision 24 are accepted, with the common `proposed | active | invalidated | superseded` status matrix.
11. **Imported historical judgments:** may be preserved and, after human review, activated despite bounded unknown metadata, but unresolved attribution/stage/authority limits consequential current-use eligibility and never becomes authenticated authority by implication.
12. **Amendment:** Review, Classification, Hypothesis, and Determination v1 expose no permitted Amendment paths. Open Review workflow progression is not Amendment.

No unresolved pre-ADR question remains that requires delaying the initial v1 public contracts.

Cross-Event/FBA Hypothesis ownership and institution-wide authentication/authorization remain explicitly deferred rather than unresolved within Issue #16.

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
