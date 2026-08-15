# Portia Participant Redaction and Segregation Rules

**Status:** Issue #21 Slice 3 architecture
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Date:** 2026-08-14
**Wire-contract status:** No new public Issue #21 schema is introduced by this slice.

## 1. Purpose

This document defines deterministic Portia-side privacy rules for deriving one
focal-participant view from multi-participant Event and Support Process data.

The governing rule is:

> A focal projection may narrow what is shown, but it must not rewrite the
> native source into a materially different fact.

In particular:

```text
source applies to focal participant
!= source concerned only focal participant

other participant withheld
!= other participant never existed

native source withheld
!= source absent

focal view
!= new canonical per-student record
```

## 2. Projection pipeline

A participant/student/family projection should process source state in this
order:

1. resolve exact source work and supported contract version;
2. resolve exact focal participant/subject;
3. reconcile source lifecycle/currentness;
4. identify every identity-bearing and narrative-bearing segment;
5. classify each segment under the exact projection policy;
6. evaluate cross-field coherence and indirect-identification risk;
7. apply only truth-preserving transformations;
8. stop at `requires_manual_review` where safe mechanical segregation is not
   possible;
9. produce the recipient-facing representation;
10. retain restricted internal source/policy/disposition provenance separately.

Changing this order is unsafe. Redacting names before resolving lifecycle or
focal identity can cause the wrong representation to be disclosed.

## 3. Exact focal identity

For Event projections, the focal subject must resolve through one exact Event
Participant representation.

Current Event Participant v3 may represent:

```text
roster_student
actor
descriptive_person
unknown_person
```

The projection must not infer equivalence between two participant records from
display text alone.

Do not match focal identity by:

```text
name
email
phone
display label
historical roster position
description text
similar Actor identity
```

If exact focal identity cannot be established:

```text
requires_manual_review
```

or `unavailable` when the exact source cannot be resolved.

A correction/supersession relationship does not authorize silent retargeting.
The projection must explicitly select the current/required representation under
the existing lifecycle rules.

## 4. Native identity is not safe merely because it is opaque

These are all identity-bearing:

```text
roster_student_ref
actor_ref
participant_id
display_snapshot
descriptive_person display_label
unknown-person description
role target
stable pseudonym reused across outputs
```

An opaque Portia ID can permit linkage and is not automatic de-identification.

For outward participant/student/family projection:

```text
focal identity -> conditional inclusion
unrelated identity -> withheld by default
```

## 5. Event-level shared context

Event v2 can carry:

```text
occurrence
summary
location
instructional_context
supersedes
```

Each is projected independently.

### 5.1 `summary`

Event summary is teacher-authored free text.

Automatic outward handling:

```text
summary contains no unresolved third-party narrative/identity
    -> eligible for inclusion

summary contains or may contain third-party identity/content
    -> requires_manual_review
```

The automated privacy layer does not silently paraphrase Event summary text.

### 5.2 `occurrence`

Occurrence precision can itself identify an incident.

Policy may deliberately reduce precision only through an explicit
truth-preserving projection rule, for example:

```text
exact timestamp -> date-only presentation
```

The projection must not claim that the native source was date-only or unknown.

Source precision remains exact provenance.

`withheld` occurrence reason must not be converted into `unknown` or
`not_reported`.

### 5.3 `location`

Location `type` may be conditionally included.

`detail` is free text and may identify a person, classroom, specialized program,
or rare context.

Location detail therefore requires separate policy evaluation.

A policy may omit detail while retaining a truthful broader type only if doing
so does not materially change meaning.

### 5.4 `instructional_context`

Context `type` may be conditionally included.

`detail` and `external_refs` are separate privacy decisions.

A sibling-module instructional reference does not transfer permission to
resolve or disclose the foreign record.

## 6. Multi-participant Event segregation

A participant-specific projection may include one focal Event Participant and
must evaluate every non-focal Event Participant independently.

Default outward behavior:

```text
focal participant representation
    -> conditional

non-focal participant identity/display snapshot
    -> withheld

non-focal participant exact record IDs
    -> withheld

hidden participant count
    -> withheld unless exact policy permits existence/count disclosure
```

The projection must not return a native participant list with redacted names but
stable IDs left intact.

## 7. Event Participant subject variants

### `roster_student`

The exact roster reference and display snapshot are identity-bearing.

Student/family projection generally uses a bounded display representation rather
than exporting Core identity references.

### `actor`

Actor identity remains teacher-local. Actor reference inclusion does not imply
access to Actor Directory child records or Contact Points.

### `descriptive_person`

`description_type`, `display_label`, and optional `detail` can identify an
outside student, family member, staff member, visitor, or community member.

Default non-focal outward result:

```text
withheld
```

Do not assume a generic label such as "staff member" is always non-identifying in
a small context.

### `unknown_person`

Preserve source uncertainty distinctions such as:

```text
identity_not_known
identity_not_reported
identity_withheld
ambiguous_source
ambiguous_paper_mark
legacy_import
```

In particular:

```text
identity_withheld != identity_not_known
identity_withheld != anonymous
```

The recipient-facing artifact may use a more privacy-minimal omission label, but
restricted provenance preserves the native meaning.

## 8. Event Participant Role

Current role vocabulary is:

```text
directly_involved
present
reported_involved
contextual
```

Role is not a guilt, victim, witness, offender, severity, or intent label.

For the focal participant:

- role type is conditionally projectable;
- role status/currentness must be preserved;
- `detail` is free text and independently reviewed;
- `basis` references are independently projected.

For a non-focal participant:

```text
role type
role target
role detail
role basis
```

are withheld by default because any of them may identify the person or reveal a
sensitive relationship.

### `reported_involved`

The role may be supported by Account, paper-capture, or import basis. Including
the focal role does not automatically authorize disclosure of the Account
source, source text, paper route, Page Record, or import source key.

## 9. Multi-target Event-local records

`portia_target_ref@1` can target:

```text
event
event_participant
event_participants
```

When a native record targets several participants and the focal participant is
one of them:

> The projection may represent that the record applies to the focal participant,
> but it must not rewrite the native source as if its original target had been
> singular.

Unsafe transformation:

```text
native target = [student A, student B, student C]
projection target = student A
and presentation implies source originally concerned only student A
```

Safe conceptual representation:

```text
applies_to_focal_subject = true
native multi-party scope not exposed beyond policy
```

If the existence of additional targets is necessary to understand the meaning
and cannot safely be stated:

```text
requires_manual_review
```

## 10. Account segregation

Account v1 preserves:

```text
target
source
information_origin
source_certainty
content[]
elicitation_context
provided_time
related_accounts
source_artifacts
supersedes
```

These must be projected independently.

### 10.1 Focal student is Account source

The source identity may be eligible as focal identity.

This does **not** make `content` automatically safe. A student's own statement
may identify or describe another student.

Each content segment is independently assessed.

### 10.2 Focal student is target; source is someone else

Default student/family handling:

```text
Account applicability to focal student -> conditional
third-party source identity -> withheld
information_origin -> conditional
source_certainty -> conditional
content -> requires_manual_review unless safe content is established
elicitation_context -> requires_manual_review
source_artifacts -> withheld
```

The system must not emit a stable pseudonym for the source unless an explicit
projection policy requires that behavior for one bounded output.

### 10.3 Unidentified source

`represented_human_attribution` distinguishes:

```text
anonymous
withheld
uncertain
not_recorded
```

Do not normalize these into one generic "unknown source" internally.

The fact that source identity is withheld may itself be sensitive in the
recipient-facing artifact.

### 10.4 Content segments

Account content is an array of:

```text
verbatim_quote
recorded_summary
```

The representation label must survive projection.

Automatic privacy handling is segment-oriented:

```text
safe complete segment -> include
policy-disallowed complete segment -> withhold
third-party text cannot be safely separated -> requires_manual_review
```

The automatic layer does not rewrite a quote, splice words out of a sentence, or
paraphrase a narrative and continue to label it source evidence.

A later human-approved disclosure-specific summary would require attributable
review/provenance and is not the native Account.

### 10.5 Related Accounts

A relation such as:

```text
reports_from
clarifies
retracts
```

may be relevant to currentness/meaning.

The related Account itself must pass its own projection policy.

A safe projection may preserve a bounded currentness statement without exposing
the related Account ID or hidden source content.

## 11. Observation segregation

Observation v1 preserves:

```text
target
observer
method
method_detail
content.narrative
content.measurements
observation_time
source_artifacts
supersedes
```

### 11.1 Measurements

Measurements can often be segregated more safely than narrative when:

- target applicability to the focal participant is exact;
- the metric does not encode hidden participant identity;
- the measurement is not misleading outside the native context;
- source currentness is reconciled.

Measurement inclusion does not turn an Observation into a Determination.

### 11.2 Narrative

Observation narrative is free text.

If third-party identity/content cannot be mechanically ruled out:

```text
requires_manual_review
```

### 11.3 Observer

Human observer attribution is separately projected.

A teacher/staff observer identity is not automatically required in every
student/family view.

Instrument metadata such as label/process/known limitation is also separately
evaluated and should not leak internal implementation identifiers without need.

### 11.4 Source artifacts

Artifact-review method does not authorize the artifact itself.

Always preserve:

```text
Observation projectable
!= source artifact projectable
```

## 12. Communication segregation

Communication v1 is a bounded communication act, not a full message archive.

Fields requiring independent decisions include:

```text
sender
recipients[]
method
purpose
act_state
privacy_scope
started_at / ended_at
summary
attachments
relations
supersedes
```

### 12.1 `privacy_scope`

Apply first as handling input:

```text
ordinary
    continue field-level projection

participant_limited
    require exact focal relationship/alignment

restricted
    outward fields withheld by default unless explicit policy/manual review permits

unknown
    fail closed for outward projection
```

`privacy_scope` never establishes requester authorization.

### 12.2 Sender

Sender identity may be conditionally included when needed to understand the act.

A sender Actor reference does not authorize Actor Contact Point disclosure.

### 12.3 Recipients

Evaluate each recipient separately.

For a focal recipient:

```text
person -> conditional
participation -> conditional
endpoint_ref -> withheld by default
```

For unrelated recipients:

```text
person -> withheld
participation -> withheld
endpoint_ref -> withheld
```

Do not expose the number of hidden recipients unless the policy permits that
existence information.

### 12.4 Participation

Preserve:

```text
participated
not_established
unknown
```

Listing a recipient never becomes proof of participation.

### 12.5 Summary

Communication summary is recorder-authored narrative.

Default outward handling:

```text
requires_manual_review
```

unless the exact projection policy can establish safe complete content.

The automatic layer does not convert a Communication summary into an Account or
purported exact message.

### 12.6 Attachments

Attachment eligibility is independent.

For:

```text
workspace_file
portia_record
module_record
external_record
```

the projection may reveal bounded existence only when useful and allowed.

Do not expose:

```text
workspace path
foreign record capability
external reference
fingerprint
```

as an automatic consequence of Communication inclusion.

### 12.7 Relations

Communication relations can reveal hidden domain records.

A relation may be represented only if the referenced semantic fact is itself
projection-safe.

Do not expose an exact hidden record ID merely to preserve a graph edge.

## 13. Actor Contact Point segregation

Actor Contact Point v1 explicitly states that contact information is
privacy-sensitive and is not identity, institutional verification, communication
authorization, or proof of exclusive control.

Direct values:

```text
email address
phone number
```

are withheld from ordinary participant/student/family projections.

Even when the focal family member is the same Actor, a generic family-facing
behavior projection must not inherit contact data merely because it exists.

Contact values require a deliberately selected contact/export purpose and
authorization rule.

Also withhold by default:

```text
source label
external reference
verification operator/time
normalization internals
supersession details
```

unless an exact administrative purpose requires them.

`preferred` remains a teacher-local use preference, not consent or authorization.

## 14. Relationship records

`actor_student_relationship` is descriptive local context.

It does not prove:

```text
guardianship
custody
FERPA entitlement
legal authority
current permission to receive information
```

Family-facing projection can use an externally established authorization
decision while treating the Portia relationship as descriptive context only.

## 15. Correction and supersession

A projection must reconcile lifecycle before privacy rendering.

Examples:

```text
active source -> current eligible source
superseded predecessor -> not presented as another current fact
invalidated representation -> not silently presented as current
ownership-corrected source -> exact historical source remains historical
migrated source -> exact historical reference does not silently retarget
```

A projection may provide bounded human-readable correction context without
exporting every technical lifecycle record.

If omitting correction history would materially misrepresent the current record,
the history indicator is part of truthful projection.

## 16. Statement of Disagreement

Statement of Disagreement is substantive source narrative, not operational
metadata.

When governing policy requires an applicable active disagreement to accompany
the contested portion:

```text
included contested target
-> disagreement relationship must be evaluated
```

The disagreement has its own:

```text
source
positions
statement representation
statement text
status
supersession
```

privacy decisions.

The statement can itself contain third-party information.

Critical rule:

> If policy requires the disagreement to accompany the contested material but
> the disagreement cannot be safely projected mechanically, Portia must not
> simply omit the disagreement and export the contested material alone.

Default result:

```text
requires_manual_review
```

for the combined disclosure unit.

`verbatim_quote` and `recorded_summary` must remain distinct.

## 17. Exceptional Removal and unavailable source

If canonical source content has been exceptionally removed, stale derived output
must not recreate it.

A projection may, when policy requires truthful history, represent a bounded
fact equivalent to:

```text
historical representation is no longer available
```

without exposing the confidential removal rationale or path.

Do not convert removed/unresolvable content into `absent`.

## 18. Deterministic safe transformations

The automatic projection layer may use only transformations that are both
policy-declared and truth-preserving.

Examples that can be acceptable when the policy explicitly allows them:

```text
exact timestamp -> date-only display
specific location detail omitted while truthful broad location type remains
native focal ID -> bounded focal display label
exact source locator -> bounded "supporting source exists" indicator
```

Not automatically acceptable:

```text
multi-party target -> singular source claim
quote -> paraphrase
third-party name -> stable pseudonym
"reported involved" -> "responsible"
"completed" -> "successful"
withheld -> unknown
unavailable -> absent
```

## 19. Manual review boundary

Manual review is required when any of these remain unresolved:

- narrative contains third-party material;
- identity removal changes the proposition;
- participant count/existence is itself identifying;
- rare time/location/context combination creates material re-identification risk;
- correction/disagreement content must accompany an otherwise projectable record
  but is not mechanically safe;
- foreign source meaning is required but foreign access is unavailable;
- authorization/policy decision cannot be established mechanically.

Manual review must not mutate the canonical source merely to make it exportable.

## 20. Slice 3 accepted decisions

Slice 3 accepts:

1. exact focal identity before redaction;
2. source lifecycle/currentness before redaction;
3. no false singularization of multi-party source scope;
4. no automatic free-text paraphrasing;
5. Account content handled per complete content segment;
6. Observation measurements and narrative handled separately;
7. Communication recipients handled independently;
8. `endpoint_ref` and Contact Point values withheld by default;
9. disagreement can form an inseparable disclosure unit with a contested record
   when policy requires it;
10. exceptional removal cannot be reversed through stale derived state;
11. safe coarsening must be explicit and truth-preserving;
12. unresolved privacy meaning stops at `requires_manual_review`.
