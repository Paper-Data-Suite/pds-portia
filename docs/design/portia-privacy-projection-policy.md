# Portia Privacy Projection Policy

**Status:** Issue #21 Slice 2 architecture
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Date:** 2026-08-14
**Wire-contract status:** No public Issue #21 schema is introduced by this slice.

## 1. Purpose

This document defines the semantic contract for Portia privacy projections before
the repository commits to an export, retention, request, or Sunset wire shape.

A Portia privacy projection is:

> a purpose-bounded, source-bounded, subject-bounded, authorization-aware
> representation derived from exact canonical Portia state without changing the
> canonical records from which it was produced.

The projection layer must preserve:

```text
canonical record != projection
projection != export
export != disclosure
audience context != authorization
redaction != correction
withheld != absent
unavailable != false/no
```

No projection creates a canonical student profile, dossier, behavior score, risk
score, discipline score, or permanent tier.

## 2. Projection-policy identity

The foundation requires a versioned policy identity even though Slice 2 does not
yet decide whether that identity is a public JSON record.

A projection decision must be attributable to an exact policy identity
equivalent to:

```text
policy_id
policy_version
policy_digest or exact immutable definition identity
```

A mutable display label is not sufficient policy provenance.

A later local configuration system may bind an institution-approved policy to
that identity, but changing the configured policy must not retroactively rewrite
historical export provenance.

## 3. Projection purposes

The initial closed purpose vocabulary is:

```text
teacher_current
participant_specific
student_facing
family_facing
aggregate_equity
administrative_export
```

These purposes define projection behavior only.

They do **not** establish:

```text
requester identity
student identity of the requester
parent/guardian relationship
FERPA rights
legitimate educational interest
consent
institutional role
legal disclosure exception
lawful disclosure basis
```

### 3.1 `teacher_current`

Purpose:

> support the teacher's current work inside one explicit current class, Event,
> Support Process, or deliberately selected focal context.

Default constraints:

- current-use eligible records are favored;
- historical/superseded records require deliberate history access where
  practical;
- Contact Point values appear only in an explicit communication/contact
  workflow, not in generic behavior history;
- operation journals, locks, quarantine internals, source paths, and import
  payload metadata are not ordinary teacher-current display;
- no workspace-wide automatic "everything ever recorded about this student"
  landing view.

### 3.2 `participant_specific`

Purpose:

> derive one internally useful view of one exact focal participant/subject inside
> one exact work scope.

This profile may be richer than a student/family-facing disclosure view, but it
still must not expose unrelated participant identity/content merely because the
teacher can resolve the underlying record.

### 3.3 `student_facing`

Purpose:

> produce student-understandable content about the exact focal student while
> protecting unrelated people and internal-only operational material.

Student-facing does not authenticate a student.

### 3.4 `family_facing`

Purpose:

> produce family-understandable content about the exact focal student while
> protecting unrelated people and internal-only material.

Family-facing does not establish that a requester is a parent, guardian, or
otherwise authorized recipient.

### 3.5 `aggregate_equity`

Purpose:

> derive authorized aggregate/equity analysis without exposing identifiable
> student-level narrative as the mechanism of aggregation.

This purpose is incompatible by default with:

```text
raw Account text
Communication summary text
Contact Point values
individual source-artifact paths
individual operation/integrity records
free-text grouping keys
student-level row export
```

Aggregate output still requires contextual re-identification analysis.

### 3.6 `administrative_export`

Purpose:

> build a deliberately requested export using one explicitly selected outward
> projection policy and authorization decision.

This purpose does not mean "raw Portia dump."

The eventual export contract must name the actual selected projection semantics
rather than using `administrative_export` as a bypass around the producer privacy
floor.

## 4. Required projection inputs

Before a privacy projection can be considered valid, the application must
establish inputs equivalent to:

```text
exact source scope
exact source contract versions
projection purpose
exact projection-policy version
focal participant/subject when required
authorization decision/input when required
generation/request context
```

### 4.1 Exact source scope

Allowed scope is deliberately bounded. Examples:

```text
one exact Event
one exact Support Process
one selected class context
one exact participant inside one work
one deliberate aggregate query scope
one deliberate export source set
```

An unbounded workspace crawl is not an ordinary participant/student/family
projection.

### 4.2 Focal subject

`participant_specific`, `student_facing`, and `family_facing` require an exact
focal subject/participant identity.

Do not infer focal identity from:

```text
display name
email address
phone number
similar name
file name
row order
historical roster position
Actor relationship label
```

### 4.3 Authorization input

Projection policy answers:

```text
what Portia is willing to expose for this semantic purpose
```

Authorization answers:

```text
whether this requester/context is permitted to receive/use that projection
```

Both must succeed when the use case requires authorization.

A projection-safe field does not override a failed or missing authorization
decision.

## 5. Closed producer policy

Portia uses an allowlist model:

```text
known source contract
+ known field semantics
+ known purpose
+ known focal context
+ exact policy rule
-> candidate projection decision
```

Unknown source fields, unknown record kinds, unsupported contract versions, or
unknown policy versions fail closed.

The following are prohibited as architecture shortcuts:

```text
include_private
include_all
raw_record
raw_graph
admin_mode
debug_export
skip_redaction
trust_requester
```

A consumer can always narrow Portia output.

A consumer cannot request Portia-native private material that the producer
policy excluded.

## 6. Projection disposition vocabulary

Every semantically relevant source field/record considered by a projection must
resolve internally to one of these five meanings.

### 6.1 `included`

```text
source exists
+ exact source resolved
+ exact policy permits representation
+ authorization conditions are satisfied where applicable
```

Included does not imply that every native source field is copied verbatim.

The projection may deliberately transform native representation into a safer
display representation only when that transformation is deterministic and
truth-preserving.

### 6.2 `absent`

```text
the source field/record does not exist in the exact source state
```

Absence is a source fact, not a privacy decision.

Do not use `absent` when content exists but is hidden.

### 6.3 `withheld`

```text
source exists
but this policy/purpose/authorization does not permit exposure
```

Withheld must not become:

```text
empty string
false
no
none
unknown
not applicable
zero
```

unless that value is independently the actual source value.

### 6.4 `unavailable`

```text
a source is referenced/expected
but cannot currently be resolved, verified, or retrieved
```

Examples may include:

```text
referenced artifact unavailable
foreign module source unavailable
historical source bytes unavailable
required source contract unsupported
```

Unavailable does not prove that the source never existed.

### 6.5 `requires_manual_review`

```text
Portia cannot mechanically determine a truthful privacy-safe representation
```

Typical triggers:

- redaction would change meaning;
- free text contains unresolved third-party identity/content;
- rare context creates significant re-identification risk;
- source/target roles cannot be separated safely;
- applicable authorization/policy condition requires an institutional decision;
- safe inclusion depends on context that Portia cannot establish.

Manual review is not:

```text
approved
denied
included
withheld
```

It means automated projection must stop.

## 7. Internal decision vs outward presentation

The restricted internal decision may preserve:

```text
source reference
internal disposition
rule/policy reason
manual-review reason
```

The recipient-facing projection should expose only the minimum omission signal
needed for truthful interpretation.

Therefore:

```text
internal withheld reason
!= outward explanation text
```

A policy may legitimately render an internal `withheld` decision outward as a
generic omission without announcing that a sensitive third-party record exists.

The outward artifact must never expose a private record count merely to explain
that records were omitted unless policy explicitly permits that existence
information.

## 8. Field-level handling classes

Issue #21 does not add a `sensitivity` property to every domain schema.

Instead, projection policy derives handling from existing field semantics.

The initial handling classes are:

### 8.1 `focal_identity`

Exact focal student's identity or explicitly authorized display representation.

Conditional outward inclusion.

### 8.2 `third_party_identity`

Identity, display snapshot, role, or relationship that identifies someone other
than the focal subject.

Default outward result:

```text
withheld
```

unless the exact policy establishes a truthful allowed shared context.

### 8.3 `direct_contact`

Email address, phone number, Contact Point exact value, endpoint reference, or
other direct-contact locator.

Default outward result:

```text
withheld
```

Contact data is exposed only by an explicit contact/communication purpose and
authorization rule.

### 8.4 `source_narrative`

Account quote/summary, Communication summary, disagreement statement, free-text
rationale, or similar substantive narrative.

Default outward result:

```text
requires_manual_review
```

when third-party content cannot be mechanically ruled out.

### 8.5 `human_judgment`

Classification, Hypothesis, Determination, Fidelity evaluation, Outcome
evaluation, review disposition, and similar attributable judgment.

Conditional outward inclusion only when:

- it applies to the focal subject/scope;
- the exact status/currentness is preserved;
- the judgment is labeled as judgment rather than source fact;
- supporting/contrary third-party references are separately projected.

### 8.6 `shared_context`

Bounded occurrence, method, current status, neutral Event/Support context, or
other content potentially relevant to more than one participant.

Conditional inclusion.

Shared context must still undergo indirect-identification review.

### 8.7 `source_locator`

Source Artifact references, attachment paths, retained-source identity,
workspace-relative paths, PDS2 route identity, import source keys.

Default outward result:

```text
withheld
```

A record being projectable does not imply its source artifact is projectable.

### 8.8 `operational_provenance`

Operation IDs, creation machinery, Page Record processing, import mapping
identity, capture/import materialization, revision/pointer data.

Default student/family result:

```text
withheld
```

Teacher-current displays should also omit these unless an explicit
administrative/recovery workflow requires them.

### 8.9 `integrity_diagnostic`

Integrity Finding, Quarantine, suppression/acknowledgement state, collision
diagnostics, recovery detail.

Default ordinary outward result:

```text
withheld
```

A diagnostic may contain sensitive facts even when the underlying domain record
is otherwise safe.

### 8.10 `correction_history`

Lifecycle transition, supersession, amendment, ownership correction, migration,
Exceptional Removal certificate, and Statement of Disagreement relationship.

Conditional inclusion.

A current projection must not become misleading by hiding the fact that an
included record was corrected, invalidated, superseded, or materially contested.

Correction rationale itself may require a stricter field-level disposition.

## 9. Record-level decision does not override field-level decision

A record can be eligible while some of its fields are not.

Example:

```text
Communication:
  method                    included
  purpose                   included
  act_state                 included
  focal recipient           included
  unrelated recipient       withheld
  endpoint_ref              withheld
  summary                   requires_manual_review
  attachment locator        withheld
```

Therefore Portia must not implement:

```text
if record_is_visible:
    return native_record
```

The projection policy evaluates declared fields/semantic segments.

## 10. Multi-participant identity rule

For participant/student/family projections:

1. establish one exact focal subject;
2. inspect every identity-bearing field;
3. retain focal identity only when necessary for interpretation;
4. withhold unrelated identities by default;
5. review shared roles/context for indirect identification;
6. do not replace unrelated identities with stable pseudonyms unless the policy
   explicitly requires a one-export pseudonymization scheme;
7. do not expose the count/existence of hidden people if that existence itself
   leaks protected context.

An opaque native Portia ID is still an identifier and is not automatically safe.

## 11. Account rule

For `account`:

```text
target
source
information_origin
source_certainty
content
elicitation_context
provided_time
related_accounts
source_artifacts
supersession
```

must be considered independently.

### Focal student is source

Source identity may be representable as the focal student.

Content is still checked for third-party information.

### Focal student is target, different source

The fact that an Account concerns the focal student does not automatically
permit source identity or source wording.

Default:

```text
source identity -> withheld
content -> requires_manual_review
source artifact -> withheld
```

unless a narrower exact policy permits more.

### Multi-target Account

The focal participant's relationship to the Account may be included while
unrelated target identity is withheld.

If removing those identities changes the meaning of the statement:

```text
requires_manual_review
```

### Quotes

`verbatim_quote` must remain distinguishable from `recorded_summary`.

Projection must never silently rewrite a quote into a paraphrase and continue
labeling it as source evidence.

## 12. Observation rule

Observation is direct/instrumented observable evidence, not an Account.

Participant projection may include focal observable content when it can be
segregated truthfully.

Observer identity, non-focal targets, source artifacts, and free-text detail are
separate decisions.

Observation must not be upgraded into Determination through projection.

## 13. Communication rule

`privacy_scope` is a mandatory policy input but not authorization.

Initial handling:

```text
ordinary
    eligible for purpose-specific field evaluation

participant_limited
    require focal participant/relationship alignment

restricted
    default outward = withheld; manual/institution policy required to broaden

unknown
    fail closed for outward projection
```

Recipient array entries are evaluated individually.

`endpoint_ref` and resolved Contact Point value are not part of ordinary
student/family projection.

`summary` is substantive free text and defaults to manual review for outward
projection unless a policy can mechanically establish safe content.

Attachment eligibility is independent from Communication eligibility.

## 14. Actor and Contact Point rule

Actor Directory records are teacher-local identity conveniences, not
institutional identity authority.

Actor display identity may be conditionally projectable when the Actor is
itself an authorized focal/necessary party.

`actor_contact_point.contact` is direct-contact data and is not included merely
because the Actor is included.

`actor_student_relationship` does not prove legal guardianship, custody, FERPA
rights, or current authorization.

Collision records and Actor Directory operational lifecycle/removal records are
not ordinary student/family content.

## 15. Judgment-bearing record rule

For:

```text
Review
Classification
Hypothesis
Determination
Fidelity
Outcome
```

and judgment-bearing parts of later records:

- preserve attribution;
- preserve scope;
- preserve status/currentness;
- preserve uncertainty / unable-to-determine / inconclusive states;
- label the representation as human evaluation/judgment;
- separately project evidence references;
- do not reveal contrary/supporting third-party content merely because the
  judgment itself is included.

A projection cannot make a teacher-local judgment appear institutionally
authoritative.

## 16. Support, Follow-Up, Reentry, and Repair rule

Support/downstream projections must preserve the accepted semantic boundaries:

```text
Implementation completion != success
Fidelity != effectiveness
Outcome != causal proof
Reentry completion != clearance/rehabilitation
Repair completion != admission/remorse/forgiveness/restoration
```

Provider/collaborator/participant identities are independently projected.

Student/family perspective content is narrative and may contain other people's
information; source identity alone does not make all text safe.

## 17. Correction and disagreement rule

If an included native record:

- has been invalidated/superseded;
- is replaced by a current successor;
- has an applicable Amendment;
- has an applicable Statement of Disagreement;
- moved via ownership correction/migration;
- or has an Exceptional Removal certificate relevant to what remains visible;

the projection must preserve enough lineage to avoid presenting stale or
misleading current truth.

This does not mean every operational correction record is copied verbatim.

A Statement of Disagreement's substantive statement is source narrative and
requires its own privacy decision.

## 18. Paper/import rule

Paper/import operational history is provenance, not outward domain content.

Student/family projection should not ordinarily expose:

```text
Capture Batch IDs
Page Target IDs
Page Record IDs
route IDs
retained-source scan IDs
OCR confidence
interpreter version
Capture Proposal internals
Capture Review internals
Import Batch IDs
Import Source Record keys
mapping-profile versions
Import Proposal internals
Import Review internals
Operation Journal references
```

If a domain record was paper/import-derived, recipient-facing provenance may
state a bounded truthful source category when useful, but it must not expose raw
operational lineage or source paths by default.

## 19. Operation/integrity rule

The following are not ordinary participant/student/family projection content:

```text
Operation Journal
Operation Lock
Operation Current Pointer
Quarantine Record
Quarantine Current Pointer
Integrity Finding
Finding Acknowledgement
Finding Suppression
Finding Suppression Current Pointer
```

Teacher-current UI should surface only bounded actionable status when needed,
not raw diagnostic graphs or sensitive payload.

## 20. Source-artifact authorization is separate

Always preserve:

```text
record projection authorization
!= source-artifact authorization
!= attachment authorization
!= Core retained-source authorization
!= foreign-module source authorization
```

A projection may truthfully say that evidence exists without exposing a locator,
filename, retained scan, or attachment.

Source hashes are integrity data, not capability tokens.

## 21. Aggregate/equity policy floor

Aggregate projection must not:

- group on raw narrative text;
- return student-level source rows by default;
- return Contact Point data;
- expose stable native IDs as "de-identification";
- expose rare unique combinations without risk review;
- treat missing data as zero;
- count superseded predecessors as separate current events;
- convert Classification/Determination labels into permanent student traits;
- use a behavior score/risk score not defined by an accepted domain contract.

Small-cell threshold and suppression parameters belong to versioned policy and
must not be invented as universal legal constants by Portia.

## 22. Failure behavior

Fail closed when:

```text
policy version unsupported
record contract unsupported
focal subject unresolved
authorization required but unavailable
source reference cannot be verified
unknown field would otherwise flow outward
privacy_scope is unknown for an outward Communication
redaction destroys meaning
re-identification risk cannot be bounded
```

Fail closed means:

```text
withheld
unavailable
or requires_manual_review
```

according to the actual reason.

It does not mean fabricating `absent`.

## 23. Persistence decision after Slice 2

Slice 2 accepts these architecture decisions:

1. ordinary privacy projections are noncanonical and need no new public record;
2. projection policy must have exact version identity;
3. five disposition semantics are mandatory;
4. projection is field/segment aware, not a record-level Boolean;
5. outward policy is closed/allowlist-oriented;
6. Contact Points, source locators, operation/integrity state, and capture/import
   internals are withheld by default from student/family output;
7. Account/Communication free text can require manual review;
8. `privacy_scope` cannot authorize disclosure;
9. aggregate de-identification is contextual, not "name removed";
10. deliberate export remains the first likely persisted Issue #21 workflow.

The wire shape of projection policy and deliberate export remains deferred to
Slice 4 so the participant/redaction rules in Slice 3 can constrain it first.
