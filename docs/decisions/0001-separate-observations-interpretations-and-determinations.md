# ADR 0001: Separate Observations, Interpretations, Classifications, and Determinations

- **Status:** Proposed
- **Date:** 2026-07-14
- **Decision owners:** Portia maintainers
- **Related issue:** [#1 — Research best practices for tracking and managing student behavior](https://github.com/Paper-Data-Suite/pds-portia/issues/1)
- **Related research:** [`docs/research/student-behavior-tracking-best-practices.md`](../research/student-behavior-tracking-best-practices.md)

## Context

Behavior records commonly combine several different kinds of information in one narrative or mutable incident form:

- what a person directly observed;
- what another person reported;
- a quotation attributed to a participant;
- a category selected for routing or reporting;
- an inference about intent, motivation, or behavioral function;
- an administrator's policy finding;
- the response imposed or support provided; and
- a later judgment about whether the matter was resolved.

Those statements do not have the same evidentiary status, author, purpose, or authority. Combining them creates several risks:

1. **Interpretation can be presented as fact.** Labels such as “defiant,” “aggressive,” or “attention-seeking” can replace a description of observable actions.
2. **The original account can be overwritten.** A reviewer may revise a reporter's category or narrative, obscuring what was initially submitted and by whom.
3. **Uncertainty can disappear.** Conflicting or incomplete accounts may be collapsed into one institutional narrative before review is complete.
4. **Tentative hypotheses can become durable student attributes.** A possible behavioral function may be repeated in later records as though formally established.
5. **Reporter and decision-maker roles can become blurred.** A referral may be treated as proof of a policy violation rather than a request for review.
6. **Corrections can conflict with auditability.** A wholly immutable record does not adequately support correction or amendment, while unrestricted editing destroys provenance.
7. **Analytics can count unlike concepts as equivalent.** Reporter-selected categories, confirmed classifications, and formal findings can be mixed in the same metric.
8. **Bias can be amplified.** Prior labels and subjective descriptions can prime later observers and reviewers.

Federal functional behavioral assessment guidance emphasizes objective and measurable descriptions and the use of multiple direct and indirect data sources. FERPA gives parents and eligible students rights to inspect education records and seek amendment of information they believe is inaccurate, misleading, or privacy-violating. Discipline-equity research also identifies subjective decision points as especially vulnerable to inconsistent and disproportionate outcomes.

Portia therefore needs a domain model that preserves provenance, epistemic status, and decision authority from the beginning.

## Decision

Portia will represent a behavior-related occurrence through linked records rather than one canonical incident document.

### 1. Event

An **Event** is a neutral container for a real-world occurrence. It establishes shared context such as date, approximate time, location, activity, participants, and safety status. Creating an event does not establish misconduct, responsibility, victim status, intent, or behavioral function.

### 2. Account or Observation

An **Account** is an author-attributed statement about the event. Each account will identify:

- the author;
- whether the information was directly observed, reported by another person, or derived from a document;
- the time of observation or report;
- an objective narrative;
- quotations distinctly marked as quotations; and
- its correction and amendment history.

Separate people will ordinarily have separate accounts. Portia will not silently merge multiple authors' statements or rewrite one person's account into another person's voice.

### 3. Classification

A **Classification** is a controlled category used for routing, reporting, or local policy workflows. It will record:

- the selected category;
- the applicable definition and version;
- who selected it;
- whether it is reporter-selected, reviewer-confirmed, changed, or unable to determine; and
- the reason for a change.

A reporter-selected classification will remain distinguishable from a reviewer-confirmed classification. A later value may supersede an earlier active value without erasing the earlier submission.

### 4. Hypothesis

A **Hypothesis** is a tentative explanation that requires evidence and review. It may include a possible relationship among context, behavior, consequences, and function. Portia will:

- label hypotheses explicitly;
- preserve the author and supporting data;
- allow competing hypotheses;
- record review status and confidence in descriptive—not predictive—terms; and
- prevent a hypothesis from automatically triggering discipline or being displayed as a student trait.

A perceived motive entered during rapid reporting will not be treated as a determined behavioral function.

### 5. Determination

A **Determination** is a formal institutional finding made by an authorized decision-maker under an identified policy or process. It will record:

- the question or allegation reviewed;
- the decision-maker;
- the policy and version applied;
- the finding;
- the factual basis;
- required notice, review, or disability-related safeguards; and
- appeal, reconsideration, or supersession status.

An account, referral, or reporter-selected classification will never be represented as a formal determination.

### 6. Response, Support, and Outcome

Immediate responses, planned supports or interventions, and later outcomes will be distinct linked records. This separation prevents the consequence imposed from becoming the definition of what occurred and permits Portia to evaluate whether a support was implemented and whether it helped.

### 7. Provenance and correction model

Portia will use an append-only audit history together with correctable active records:

- every creation, material edit, reclassification, determination, and correction will retain actor, timestamp, prior value, new value, and reason;
- ordinary users will not silently alter another person's authored account;
- authorized correction workflows may replace inaccurate active values while retaining protected history;
- parents, eligible students, and authorized staff can attach additional statements or disagreement records according to policy;
- exported or disclosed records will include the current authorized representation and any legally required statement of disagreement; and
- access to superseded or restricted historical values will be permission-controlled.

“Append-only” applies to the audit history, not to a requirement that known inaccuracies remain the only visible active record.

### 8. User-interface presentation

The interface will communicate epistemic status rather than relying only on color. Each statement or field will show a textual status such as:

- Direct observation
- Reported account
- Quotation
- Reporter-selected classification
- Reviewer-confirmed classification
- Hypothesis
- Formal determination
- Outcome measurement

Initial rapid capture will prioritize the current event and objective description. Prior negative history will not be shown by default while a user is recording an initial observation, except where a separately governed safety workflow establishes a legitimate need.

### 9. Analytics

Analytics will identify which layer supplies each measure. For example:

- “reports submitted” will count referrals or accounts;
- “reviewer-confirmed classifications” will count confirmed classifications;
- “formal findings” will count determinations; and
- “supports delivered” and “outcomes observed” will count their respective records.

Portia will not combine these into one undifferentiated “incident” count without clear labeling and an explicit analytical purpose.

## Consequences

### Positive consequences

- Objective observations remain distinguishable from interpretation.
- Conflicting accounts can coexist without premature resolution.
- Reporter, reviewer, and decision-maker authority is explicit.
- Corrections and FERPA-related amendments can occur without destroying provenance.
- Functional hypotheses remain tentative and evidence-linked.
- Analytics can distinguish referral behavior, institutional findings, responses, and outcomes.
- Multi-student events can share context while maintaining student-specific access and redaction.
- The model better supports restorative, PBIS/MTSS, FBA/BIP, and due-process workflows without making any one framework mandatory.
- Audit and accountability questions can be answered more reliably.

### Costs and tradeoffs

- The data model and permissions system will be more complex than a single incident table.
- Users may need additional interface guidance to understand record types and statuses.
- Imports from legacy systems may be unable to reconstruct provenance or epistemic status and must be marked accordingly.
- Reporting queries must choose the appropriate layer and avoid accidental double counting.
- Correction, supersession, and redaction workflows require careful testing.
- Some districts may initially prefer a familiar single-form workflow; Portia will need progressive disclosure so the underlying distinctions do not create unnecessary entry burden.

## Alternatives Considered

### Alternative A: One mutable incident record

A single record is familiar and simple to implement, but it encourages overwriting, conflates allegation with finding, obscures authorship, and makes correction history unreliable. Rejected.

### Alternative B: One immutable incident record with addenda

This preserves history but can leave inaccurate information as the primary active representation and make lawful amendment or correction cumbersome. It also continues to combine statements with different statuses. Rejected.

### Alternative C: One narrative normalized by automated text analysis

Automated rewriting or classification could standardize language, but it risks changing meaning, erasing voice, inferring intent, and obscuring who asserted what. It would also introduce difficult explainability and bias concerns into consequential records. Rejected.

### Alternative D: Separate modules with no shared event model

Independent referral, discipline, intervention, and communication modules reduce local complexity but create duplicate records, inconsistent timelines, and weak traceability from event to support and outcome. Rejected.

## Implementation Constraints

This ADR establishes conceptual boundaries, not a final database schema. Any implementation should nevertheless preserve these invariants:

1. An event is not itself a finding of misconduct.
2. Every account has an author and source status.
3. Quotations are distinguishable from paraphrase.
4. Reporter-selected and reviewer-confirmed classifications are separate states.
5. A hypothesis is never stored or displayed as a determination.
6. A formal determination identifies authorized decision-maker and policy basis.
7. Response, support, and outcome remain independently queryable.
8. Material changes retain an auditable prior value and reason.
9. The active record can be corrected without deleting protected history.
10. Analytics identify the record layer and denominator used.

## Follow-Up Decisions

Separate ADRs should address:

- linked event/account modeling for multi-student incidents;
- predictive scoring and automated discipline prohibitions;
- authorization and field-level access;
- highly sensitive safety, clinical, and legal workflows;
- retention, destruction, legal holds, and backup expiration;
- bias-reducing history visibility;
- accessibility baseline; and
- terminology and tenant configuration governance.
