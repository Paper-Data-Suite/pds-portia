# Portia Account and Observation Domain Models

**Status:** Accepted architecture — ADR 0011
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#15 — Define Account and Observation domain models`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-07
**Branch:** `15-account-observation-domain-models`

> **Current downstream authority (Issue #16, 2026-08-09):**
> This accepted Issue #15 design remains authoritative for source evidence.
> Accepted ADR 0012 begins after this layer and defines
> `Review → Classification and/or Hypothesis → Determination`. Reuse of
> `represented_human_attribution@1` for later reviewer/selector/author/
> decision-maker identity does not change Account/Observation semantics and does
> not make represented-human identity proof of institutional authority.

> **Current downstream communication boundary (Issue #17, 2026-08-10):**
> Accepted ADR 0013 preserves this source-evidence boundary. Communication
> records that a bounded contact act or attempt occurred. If a student, family
> member, staff member, or other represented source makes a substantive
> assertion that matters as evidence, that assertion remains separately
> preservable as Account. `account_from_communication` may link the records;
> Communication metadata does not itself become source evidence.

## 1. Purpose

This document defines the accepted architecture for Portia Accounts and Observations under ADR 0011.

The two record families preserve source-level evidence without collapsing:

```text
Event
Account
Observation
interpretation
formal judgment
```

into one mutable narrative.

The central distinction is:

```text
Account
= one attributed statement, report, response, recollection, or perspective

Observation
= one attributed or instrumented record of directly observable information
```

An Account preserves what one represented source said.

An Observation preserves what one observer or instrument directly observed, counted, timed, recorded, or measured.

Neither record establishes a finding, credibility judgment, Classification, Hypothesis, Determination, policy violation, severity judgment, diagnosis, behavioral function, intent, guilt, or risk assessment.

This issue defines architecture and public contracts. Production repositories, filesystem services, transcription, OCR, attachment storage, observation tools, and teacher-facing workflows belong to later executable work.

## 2. Governing contracts

The design is subordinate to accepted ADRs 0001–0010.

The current Event model already establishes that:

- the Event is the bounded occurrence context;
- Accounts remain attributed source records separate from the Event root;
- Observations remain direct-observation records separate from the Event root;
- several Accounts may conflict without requiring separate Events;
- several Observations may belong to one Event;
- the person reporting an Event does not automatically become a Participant;
- positive, neutral, and concern-related Events use the same Event model.

Current Event Participant Role v3 already reserves source-oriented basis entries for:

```text
account_ref
observation_ref
paper_capture
import_source
```

and already establishes the structural rule:

```text
active or superseded reported_involved
    -> contains at least one account_ref
```

Issue #15 must make the placeholder Account and Observation semantics concrete without modifying published Role v3 unless a genuine wire-shape change becomes necessary.

The shared Event-local target is already public:

```text
portia_target_ref@1
```

It can target:

```text
the containing Event
one Event Participant
an explicit set of Event Participants
```

The class/work-scoped history and correction infrastructure is already public:

```text
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
exceptional_removal@1
```

The same-work operational and derived-state contracts are also already capable of addressing generic local records. Account and Observation must reuse those contracts unless implementation proves an actual wire-shape incompatibility.

Published schemas remain immutable.

## 3. Reviewed repository baseline

The Issue #15 branch was confirmed identical to `main` at the initial checkpoint.

| Repository | Reviewed commit | Immediate implication |
| --- | --- | --- |
| `pds-portia` | `ed09e6779281a23be05124afdb266579d2d560de` | Issues #11–#14 are merged. Account and Observation remain placeholder local-record kinds in Role v3 but have no canonical public contracts. |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | Core v0.6 remains authoritative for workspace/class/roster identity, PDS2 routing, route registration, and retained scan provenance. It does not define Portia source or observation semantics. |

Initial classification:

```text
pds-core:
    governing roster and PDS2 provenance boundary;
    no Core change required

pds-portia:
    Account and Observation contract work required

other sibling repositories:
    no concrete initial public-contract implication
```

The pre-ADR drift check is complete. A final pre-acceptance drift check remains required before Issue #15 closes.

## 4. Governing principles

1. One Account represents one coherent attributed source contribution.
2. One Observation represents one coherent observation context.
3. Event, Account, and Observation remain separate canonical concepts.
4. Source or observer identity is distinct from record-creation attribution.
5. Source or observer identity is distinct from the target of the information.
6. A source or observer does not automatically become an Event Participant.
7. Firsthand is a source-origin claim, not independent verification.
8. Repeated secondhand reports do not become independent corroboration automatically.
9. Quoted wording and recorder summary remain structurally distinguishable.
10. Observation content remains observable or measurable rather than interpretive.
11. Positive, neutral, and potentially concerning Observations use one neutral model.
12. Conflicting Accounts may coexist without automatic adjudication.
13. Account retraction is distinct from record invalidation.
14. Material source-evidence correction uses replacement rather than silent rewrite.
15. Historical references remain exact and do not silently follow successors.
16. Paper and import provenance do not substitute for source attribution.
17. Unreviewed OCR/import interpretation does not activate canonical evidence.
18. Account and Observation do not automatically create findings.
19. Operational records must not copy sensitive source text unnecessarily.
20. Existing shared public contracts are reused where their wire shapes suffice.

---

# 5. Approved Decision 1: Account Semantic Unit

One Account represents:

> One coherent attributed statement, report, response, recollection, or perspective from one represented human source concerning one Event-local target.

An Account is not the Event, an objective Event narrative, a credibility judgment, an Event Participant Role, a finding, a Classification, a Hypothesis, a Determination, a Communication record, or a permanent person identity.

The same source may have several Accounts when there are several distinct source contributions. A later clarification, correction, or retraction must not silently rewrite the earlier Account.

One interview, email, paper form, or imported source artifact may yield several Event-local Accounts when it contains materially separate source contributions. Common artifact provenance may be shared without merging those Accounts.

## 5.1 Coherence boundary

One Account should normally correspond to one coherent contribution that a teacher could present as one source position without materially changing its meaning.

A single Account may preserve several content segments from that same contribution, including both verbatim quotation and recorded summary, when the provenance of each segment remains explicit.

Unrelated statements should not be grouped merely because they were captured during the same conversation.

# 6. Approved Decision 2: Observation Semantic Unit

One Observation represents:

> One coherent attributed or instrumented record of information that was directly perceived, counted, timed, recorded, or measured within one observation context and associated with one Event-local target.

Representative content includes:

```text
Student raised a hand before speaking.
Student remained in the assigned area for five minutes.
Three task initiations were observed.
Latency from direction to task start was 18 seconds.
```

An Observation is not a later source report about what someone says they saw, a credibility judgment, a behavioral interpretation, a diagnosis, a finding, a Classification, a Hypothesis, or a Determination.

Interpretive phrases such as `disrespectful`, `manipulative`, `defiant`, `attention-seeking`, `anxious`, or `dangerous` are not Observation content merely because they are commonly used in classroom notes.

## 6.1 Human report versus direct Observation

When a student tells a teacher, `I saw Alex leave the room`, Portia is preserving what the student said. That is an Account.

When an accepted workflow directly preserves the student as the observer of the recorded observable information, that record may be an Observation.

This distinction depends on what the canonical record claims to preserve, not on whether the source says the underlying information was firsthand.

# 7. Approved Decision 3: Canonical Identity and Storage

Account identity will use:

```text
acct_<opaque-id>
```

Observation identity will use:

```text
obs_<opaque-id>
```

The diagnostic prefixes do not carry source, target, student, Actor, content, severity, or lifecycle meaning.

Accepted public identifier contracts:

```text
portia_account_id@1
portia_observation_id@1
```

Canonical Account storage:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/account/<account_id>.json
```

Canonical Observation storage:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/observation/<observation_id>.json
```

Both records are owned by exactly one containing Event and are not workspace-global evidence records.

# 8. Approved Decision 4: Event-Local Targeting

Both Account and Observation will reuse `portia_target_ref@1`.

The target may be the containing Event, one Event Participant, or an explicit set of Event Participants.

The target answers what the source contribution or observation concerns. The source or observer answers who supplied or directly observed the information. These concepts remain independent.

Application validation must require Participant targets to resolve within the containing Event. Historical targets remain exact and are not silently retargeted after Participant replacement.

# 9. Approved Decision 5: Represented Human Attribution

Account source and human Observation observer use one shared public primitive:

```text
represented_human_attribution@1
schemas/v1/attribution/represented-human-attribution.schema.json
```

The primitive represents the human whose statement or observation is being
preserved. It is distinct from `attribution_agent@1`, which attributes record
creation and system operations.

The closed branches are:

```text
roster_student
actor
local_operator
descriptive_person
unidentified_person
```

## 9.1 Roster student

Preserves:

```text
kind = roster_student
roster_student_ref
display_snapshot
```

Roster identity remains `class_id + student_id` and must resolve through the
relevant Core roster.

## 9.2 Actor

Preserves:

```text
kind = actor
actor_ref
display_snapshot
```

Actor Contact Point values are not copied into represented attribution.

## 9.3 Local operator

Preserves:

```text
kind = local_operator
display_label
```

This identifies the represented local human for source/observer purposes. It
does not establish institutional staff identity or authorization.

## 9.4 Descriptive person

Preserves:

```text
kind = descriptive_person
description_type
display_label
detail, optional
```

The description-type vocabulary is:

```text
outside_student
family_member
school_staff
visitor
community_member
other
```

A descriptive person is not promoted to Actor identity automatically.

## 9.5 Unidentified person

Preserves:

```text
kind = unidentified_person
reason
label, optional
```

Reason is one of:

```text
anonymous
withheld
uncertain
not_recorded
```

The optional label is a bounded descriptive label only. It is not a canonical
person identity.

An unidentified Account may be valid canonical evidence but does not qualify as
the attributed Account required to activate `reported_involved` in version 1.

## 9.6 Reuse boundary

This primitive is justified because it has two immediate consumers:

```text
Account.source
Observation.observer.kind = human
```

Later Portia records may adopt it only when they need the same represented-human
semantics. Existing published contracts such as `statement_of_disagreement@1`
remain immutable and are not rewritten merely to use the new primitive.

# 10. Approved Decision 6: Recorder Attribution Is Separate

Every Account distinguishes represented source from `created_by` / `updated_by`.

Every Observation distinguishes represented observer or instrument from `created_by` / `updated_by`.

An OCR process, import process, or system process is not the represented source merely because it generated JSON.

The same teacher may be both observer and `created_by` for a directly entered teacher Observation, but the concepts remain separate in the wire model.

# 11. Approved Decision 7: Account Information Origin

Every Account will preserve one source-origin classification:

```text
firsthand
secondhand
mixed
unknown
```

`firsthand` means the represented source states or is recorded as supplying information from their own direct experience or perception. It does not mean verified, true, credible, or independently confirmed.

Where an exact upstream Account is known, a secondhand or mixed Account may retain that exact source-lineage reference. An upstream Account reference is not required when no canonical upstream Account exists; Portia must not fabricate one merely to complete lineage.

Two Accounts do not become independent corroboration merely because they are separate records.

# 12. Approved Decision 8: Source-Expressed Uncertainty

Portia preserves source-expressed certainty using this bounded nonnumeric vocabulary:

```text
stated_certain
stated_uncertain
mixed_or_qualified
not_recorded
```

This records how the source expressed the contribution. It is not credibility, reliability, truth probability, or a confidence score.

Automated prose analysis must not populate this field without explicit review.

# 13. Approved Decision 9: Account Content Representation

Account content will preserve one or more typed content segments. Each segment is one of:

```text
verbatim_quote
recorded_summary
```

Representative shape:

```json
{
  "content": [
    {
      "representation": "verbatim_quote",
      "text": "I was sitting by the window."
    },
    {
      "representation": "recorded_summary",
      "text": "The student reported being seated by the window."
    }
  ]
}
```

A verbatim segment represents preserved source wording. A summary segment represents recorder-created wording about the source's meaning. Portia must not silently convert between them.

An Account may also preserve bounded elicitation context when the meaning of the response depends on the prompt. Elicitation context remains separate from source wording.

# 14. Approved Decision 10: Evidence Time

Account source-contribution time and Observation time use one shared public
primitive:

```text
evidence_time@1
schemas/v1/common/evidence-time.schema.json
```

The primitive is deliberately evidence-oriented rather than Event-specific.
Its closed precision branches are:

```text
exact
approximate
date_only
range
unknown
```

Representative wire semantics:

```text
exact
    precision = exact
    at = explicit-offset timestamp

approximate
    precision = approximate
    at = explicit-offset timestamp
    approximation = about | before | after

date_only
    precision = date_only
    date = YYYY-MM-DD

range
    precision = range
    started_at = explicit-offset timestamp
    ended_at = explicit-offset timestamp

unknown
    precision = unknown
```

Account uses this as `provided_time`.
Observation uses it as `observation_time`.

The same shape is appropriate for both because both need to preserve honest
source/evidence timing independent of record creation. It does not inherit Event
occurrence meaning.

No precise evidence timestamp may be invented from `created_at`, paper scan
time, import time, or Event occurrence time.

Application validation must require range chronology and must permit legitimate
post-Event artifact review.

# 15. Approved Decision 11: Observation Attribution

Observation observer is a closed union:

```text
human
instrument
```

A human observer uses the same accepted human-attribution semantics as Account source attribution.

An instrument observer preserves bounded local provenance rather than claiming institutional device identity. Representative information includes instrument type, instrument label or process ID, method, and known limitation when applicable.

Possible instrument types:

```text
timer
counter
software
sensor
other
```

Instrument identity does not prove calibration, accuracy, scientific validity, clinical validity, or institutional approval.

# 16. Approved Decision 12: Observation Method

Observation method must distinguish how the information was directly obtained.

Accepted vocabulary:

```text
live_direct
artifact_review
manual_count
manual_timing
instrumented
other
```

`artifact_review` means the observer directly examined a source artifact. It does not mean the observer was present for the original Event. The source artifact remains separately referenced when material to the Observation's meaning.

# 17. Approved Decision 13: Observation Content and Measurement

Observation content may contain:

```text
narrative observable information
structured measurements
or both
```

At least one is required before activation.

Observation v1 does not define a separate public measurement contract. The
measurement shape remains nested inside `observation@1` because it has one
immediate semantic owner and premature generalization would create a suite-wide
measurement abstraction without evidence of another consumer.

The closed v1 measurement forms are:

```text
count
duration
latency
percentage
other_numeric
```

## 17.1 Count

```text
measure_type = count
value = integer >= 0
unit = count
```

## 17.2 Duration

```text
measure_type = duration
value = number >= 0
unit = milliseconds | seconds | minutes | hours
```

## 17.3 Latency

```text
measure_type = latency
value = number >= 0
unit = milliseconds | seconds | minutes | hours
```

## 17.4 Percentage

```text
measure_type = percentage
value = number from 0 through 100
unit = percent
```

## 17.5 Other numeric

```text
measure_type = other_numeric
measure_label = non-empty text
value = number
unit = non-empty text
```

`other_numeric` is an escape hatch for a bounded numeric observation, not an
interpretive rating system.

The canonical Observation model contains no positive/neutral/concerning,
severity, violation, or risk field.

Measurement does not establish normative interpretation, validity, calibration,
or causation.

# 18. Approved Decision 14: Observation Timing

Observation time may represent an exact instant, approximate instant, date-only observation, bounded range, or unknown time.

A bounded observation period remains one Observation when the content and method form one coherent observation context.

Observation time is distinct from `created_at`. Artifact review may legitimately occur after the original Event.

# 19. Approved Decision 15: Positive, Neutral, and Potentially Concerning Use

All of these are Observations:

```text
positive:
    Student independently requested clarification and resumed work.

neutral:
    Student changed seats after the group activity ended.

potentially concerning:
    Student left the classroom before dismissal.
```

Observation v1 will not encode `positive`, `neutral`, `concerning`, severity, violation, or risk as canonical truth fields.

# 20. Approved Decision 16: Conflicting Accounts

Conflicting Accounts remain separate canonical records.

Portia does not automatically merge them, invalidate one, choose a winner, calculate credibility, count agreeing Accounts as proof, or generate a finding.

The existing Statement of Disagreement contract remains the preferred mechanism when an identified human explicitly disputes an exact canonical Account or Observation.

Ordinary source disagreement does not require a Statement of Disagreement merely because two Accounts conflict.

# 21. Approved Decision 17: Account Retraction

Account retraction is source-evidenced and cannot be created by a teacher-only
status toggle.

Version 1 represents retraction with a new Account by the same represented
source containing an exact Account relation:

```text
relation = retracts
account_ref = exact predecessor Account
```

Once the retraction Account is reviewed and becomes active, one coordinated
operation transitions the referenced predecessor Account from `active` to
`retracted`.

Application validation requires:

```text
same represented source
same containing Event
exact predecessor Account reference
active retraction Account
relation target not self
eligible predecessor lifecycle
coordinated predecessor lifecycle transition
```

A `retracts` relation withdraws the predecessor Account as a whole.

Partial qualification uses a new Account with `clarifies`. A materially
corrected contribution uses canonical successor/supersession instead.

Retraction means the source no longer stands behind the earlier Account. It does
not establish that the earlier Account was false.

A retracted Account remains historically resolvable. A later reaffirmation is
new source evidence and does not reactivate the retracted representation.

# 22. Approved Decision 18: Account Lifecycle

Account statuses are:

```text
proposed
active
retracted
invalidated
superseded
```

Transition matrix:

```text
proposed
    -> active
    -> invalidated
    -> superseded

active
    -> retracted
    -> invalidated
    -> superseded

retracted
    -> superseded

invalidated
    -> superseded

superseded
    -> no later state
```

Accepted Account lifecycle reason codes are:

```text
review_completed
source_retracted
recording_error
wrong_source
wrong_target
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

`source_retracted` is valid only for the coordinated source-evidenced retraction
workflow defined by Decision 17.

`wrong_source`, `wrong_target`, and `invalid_provenance` invalidate the canonical
record; they do not claim the represented source was dishonest.

`other` requires bounded detail.

# 23. Approved Decision 19: Observation Lifecycle

Observation statuses are:

```text
proposed
active
invalidated
superseded
```

Transition matrix:

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

Accepted Observation lifecycle reason codes are:

```text
review_completed
recording_error
wrong_observer
wrong_target
wrong_method
measurement_error
invalid_provenance
prohibited_payload
corrected_by_successor
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Observation does not acquire `retracted` merely because Account uses it.

A human observer's later statement disputing an Observation may itself be an
Account or Statement of Disagreement while Observation correction remains a
separate lifecycle/supersession workflow.

`other` requires bounded detail.

# 24. Approved Decision 20: Material Correction and Supersession

Material Account changes include represented source, target, content, quote/summary representation, information origin, materially different source-expressed uncertainty, statement timing, and material source provenance.

Material Observation changes include observer or instrument, target, observable narrative, measurement, unit, observation interval, method, and material source provenance.

The existing Amendment contract may be used only for a narrow set of nonmaterial fields approved during schema implementation. Primary source wording and primary observed information are not routine mutable text.

Historical consumers do not silently follow successors.

# 25. Approved Decision 21: Account-to-Account Relations

Account-to-Account relations remain nested in `account@1`; version 1 does not
publish a separate relation contract.

The field is:

```text
related_accounts
```

Each entry contains:

```text
relation
account_ref
```

where `account_ref` is an exact same-Event Account reference constrained to:

```text
record_kind = account
contract_version = 1
```

The closed relation vocabulary is:

```text
reports_from
clarifies
retracts
```

Semantics:

```text
reports_from
    known secondhand lineage to another Account

clarifies
    additional same-source context that does not replace or invalidate the
    referenced Account

retracts
    same-source withdrawal of the referenced Account as a whole
```

Material correction remains canonical supersession and is not modeled with a
`corrects` relation.

Relations are directional from the current Account to the referenced earlier
Account. They never establish truth, credibility, or corroboration.

# 26. Approved Decision 22: `reported_involved` Integration

Event Participant Role v3 remains immutable unless implementation discovers an actual wire-shape requirement.

A qualifying Account for an active `reported_involved` Role must:

```text
resolve canonically
belong to the same Event
use a supported Account contract
be eligible for current use
have qualifying represented-source attribution
target the same Participant
    or
target an explicit Participant set containing that Participant
```

An Event-wide Account is not sufficient to justify a participant-specific `reported_involved` Role.

This stronger target-alignment rule prevents an unrelated same-Event Account from activating an arbitrary Participant Role.

The following do not satisfy the active-role Account requirement by themselves:

```text
Observation
paper_capture
import_source
free-text note
teacher confirmation
unidentified Account that does not meet the accepted attribution threshold
```

Qualifying source forms are `roster_student`, `actor`, `local_operator`, and `descriptive_person`. The `unidentified_person` branch does not qualify. This is a traceability requirement, not a credibility judgment.

If a referenced Account later becomes retracted, invalidated, superseded, or exceptionally removed, the Role basis is not silently rewritten and no automatic lifecycle cascade occurs.

# 27. Approved Decision 23: Observation Basis and Roles

Observation may remain a Role basis where compatible with Role semantics, but Observation does not satisfy the Account requirement for active `reported_involved`.

If an Observation supports a `present`, `directly_involved`, or `contextual` Role, application validation must still check same Event, target alignment, Observation current-use eligibility, and Role-specific lifecycle rules.

Observation does not automatically create or activate a Role.

# 28. Approved Decision 24: Paper Capture

Account and Observation will reuse `creation_source@1`.

Paper-derived canonical source records require:

```text
type = paper_capture
stage = ingested
route_id
page_record_id
```

Portia will not create a canonical Account or Observation merely because a page was rendered.

Preferred rule:

```text
no canonical Account or Observation at paper preallocation time
```

Automated handwriting, OCR, checkbox, or mark interpretation may create a proposal or staged interpretation. It must not silently establish source identity, observer identity, verbatim quotation, firsthand status, Participant target, finding, or active `reported_involved` Role.

Paper-derived Account and Observation records begin `proposed`. Local review is required before activation.

# 29. Approved Decision 25: Import

Imported Accounts and Observations use `creation_source.type = import`.

Version 1 uses a conservative review gate:

```text
imported canonical Account/Observation begins proposed
local review is required before activation
```

Import does not infer Actor identity from name similarity or email, Participant identity from display text, credibility from source system, or firsthand status from prose.

Import provenance remains distinct from source or observer attribution.

# 30. Approved Decision 26: Source Artifacts and External References

Account and Observation use one shared public source-artifact reference:

```text
source_artifact_ref@1
schemas/v1/references/source-artifact-ref.schema.json
```

The primitive is justified because Account and Observation both need to refer to
source material without embedding binary payloads.

The closed branches are:

```text
paper_capture
workspace_file
portia_work_record
module_work_record
external_record
```

## 30.1 Paper capture

```text
kind = paper_capture
route_id
page_record_id
```

Core/PDS2 remains authoritative for routing and retained-source provenance.

## 30.2 Workspace file

```text
kind = workspace_file
workspace_relative_path
fingerprint
media_type, optional
```

`fingerprint` reuses `content_fingerprint@1`.

Application validation establishes workspace containment, exact-file digest and
byte-length truth, authorization, and readable availability.

## 30.3 Exact Portia work record

```text
kind = portia_work_record
work_record_ref = exact_portia_work_record_ref@1
```

## 30.4 Typed sibling-module work record

```text
kind = module_work_record
module_work_record_ref = module_work_record_ref@1
```

Application validation requires a non-null supported `contract_version` for
source-evidence use and exact module/work/record agreement.

## 30.5 External record

```text
kind = external_record
source_label
external_reference
```

This branch preserves an inert locator supplied by the workflow. Portia does not
fetch, execute, authenticate, dereference, or infer authority from it merely
because it exists.

## 30.6 Binary and authority boundary

Account and Observation JSON do not embed base64 images, audio, video, or other
binary payloads.

A source-artifact reference establishes where related material may be found. It
does not establish authenticity, accuracy, authorization, credibility, or proof.

# 30A. Approved Decision 26A: Amendment Boundary

Account and Observation v1 expose **no in-place amendable domain paths**.

This is intentionally stricter than many Portia record families because their
primary content is source evidence.

The existing `amendment@1` contract remains reusable infrastructure, but
application validation must reject Account and Observation as amendable targets
in version 1.

The following therefore require replacement/supersession rather than Amendment:

```text
source or observer
source attribution
Event/Participant target
Account content
quote/summary representation
information origin
source-expressed uncertainty
provided time
Account relations
Observation narrative
Observation measurement
Observation method
observation time
source-artifact set when materially evidentiary
```

Spelling, punctuation, formatting, or transcription corrections to primary
Account/Observation evidence are still evidence changes. They do not become
nonmaterial merely because the change is small.

Lifecycle status changes continue through lifecycle transitions rather than
Amendment.

A future contract version may introduce an amendable nonsemantic metadata field
only after a concrete use case demonstrates that replacement is unnecessarily
burdensome and does not rewrite evidence.

# 31. Approved Decision 27: Shared Infrastructure Reuse

Account and Observation are Event-local records and should fit the existing class/work-scoped shared infrastructure.

Expected reuse:

```text
portia_target_ref@1
portia_local_work_target@1
local_record_ref@1
exact_local_record_ref@1
lifecycle_transition@1
lifecycle_history_correction@1
amendment@1
statement_of_disagreement@1
dependency@1
record_migration@1
exceptional_removal@1
```

No Account-specific or Observation-specific lifecycle-history family is expected. No new operation contract version is expected merely to target Account or Observation because same-work local-record targets already exist. No new derived-projection framework is expected.

Schema implementation must prove compatibility through fixtures and tests.

# 32. Approved Decision 28: Operational Privacy

Operational and diagnostic records should prefer opaque IDs, record kinds, paths, contract versions, fingerprints, byte lengths, status tokens, counts, and step results.

They should not copy Account quotation text, Account summary text, Observation narrative, student names, Actor display names, contact values, attachment content, or transcripts.

Integrity Findings may report structural defects such as source unresolved, target unresolved, paper provenance mismatch, successor chain broken, or privacy-unsafe payload. They must not become domain findings such as `credible report`, `concerning student`, `policy violation`, or `behavior finding`.

# 33. Approved Decision 29: No Automatic Finding

Persisting an Account or Observation creates source evidence only.

It does not automatically create a finding, Classification, Hypothesis, Determination, policy violation, severity, or risk level.

Likewise, three Accounts do not automatically mean three independent confirmations, and one Account plus one Observation does not automatically mean corroborated.

Later review and decision records may reference source evidence while preserving their own explicit human attribution and authority.

# 34. Approved Public Contract Plan

The first schema slices will add:

```text
portia_account_id@1
portia_observation_id@1
represented_human_attribution@1
evidence_time@1
source_artifact_ref@1
account@1
observation@1
```

Expected paths:

```text
schemas/v1/identifiers/portia-account-id.schema.json
schemas/v1/identifiers/portia-observation-id.schema.json
schemas/v1/attribution/represented-human-attribution.schema.json
schemas/v1/common/evidence-time.schema.json
schemas/v1/references/source-artifact-ref.schema.json
schemas/v1/accounts/account.schema.json
schemas/v1/observations/observation.schema.json
```

Dedicated public `account_ref` or `observation_ref` contracts are not added in
version 1. Consumers should constrain the existing `local_record_ref@1` or
`exact_local_record_ref@1` to the required record kind and contract version, as
Event Participant Role v3 already does.

Observation measurement remains nested in `observation@1`.

Account-to-Account relations remain nested in `account@1`.

Published Event Participant Role v3 remains unchanged.

# 35. Expected Account Envelope

Expected fields:

```text
schema_version
record_type
module_id
class_id
work_id
account_id
status
target
source
information_origin
source_certainty
content
provided_time
related_accounts, optional
source_artifacts, optional
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

The final schema must not treat `created_by` as represented source attribution.

# 36. Expected Observation Envelope

Expected fields:

```text
schema_version
record_type
module_id
class_id
work_id
observation_id
status
target
observer
method
content
observation_time
source_artifacts, optional
supersedes, optional
creation_source
created_at
created_by
updated_at
updated_by
```

Observation `content` may contain narrative and measurements, with at least one required before activation.

# 37. Expected Supersession Reasons

## 37.1 Account

```text
source_corrected
source_attribution_corrected
target_corrected
statement_corrected
representation_corrected
information_origin_corrected
timing_corrected
provenance_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Source retraction is lifecycle evidence, not a supersession reason.

## 37.2 Observation

```text
observer_corrected
instrument_corrected
target_corrected
observation_content_corrected
measurement_corrected
timing_corrected
method_corrected
provenance_corrected
duplicate_consolidated
work_root_corrected
contract_migrated
other
```

Changing the interpretation of a valid Observation is not an Observation supersession reason.

# 38. Structural Validation Boundary

JSON Schema should enforce local structure including closed envelopes, record constants, identifier syntax, status vocabularies, target shape, source/observer union, Account content representation, information-origin vocabulary, source-certainty vocabulary, instrument requirements, Observation method vocabulary, measurement requirements, paper-stage restrictions, artifact-reference shape, supersession shape, timestamps, and reason/detail compatibility.

Schema must reject prohibited top-level shortcuts such as:

```text
credibility_score
reliability_score
risk_score
diagnosis
intent
policy_violation
automatic_finding
automatic_role
```

# 39. Application Validation Boundary

Application validation remains responsible for:

```text
canonical path agreement
parent Event resolution
same-Event target resolution
source resolution
observer resolution
source attribution eligibility
reported_involved Account eligibility
reported_involved Participant-target alignment
paper route/page provenance agreement
Core retained-source resolution where required
import review gates
quote-review requirements
information-origin consistency
known source-lineage consistency
temporal chronology
Observation method/instrument compatibility
measurement value/unit compatibility
lifecycle transition legality
source-evidenced retraction
materiality
self-supersession
duplicate predecessor identity
supersession cycles
same-family predecessor requirements
ownership correction
migration reconciliation
no silent successor following
incoming-reference repair
artifact containment and fingerprint truth
external-reference policy
authorization
privacy
atomic or recoverable coordinated operations
```

# 40. Required Application-Invalid Coverage

Account coverage must include wrong path/Event/target, unresolvable or ineligible source, target misalignment for `reported_involved`, quote/summary misrepresentation, secondhand marked firsthand, paper/import provenance failures, retraction without source evidence, retracted/invalidated current-use misuse, silent successor following, material amendment misuse, and supersession graph defects.

Observation coverage must include wrong path/Event/target, unresolvable observer, secondhand report stored as Observation, instrument/method incompatibility, measurement/unit incompatibility, paper/import provenance failures, material amendment misuse, invalidated current-use misuse, silent successor following, and supersession graph defects.

Cross-record coverage must include Observation/paper/import basis alone activating `reported_involved`, cross-Event or Event-wide Account misuse for participant-specific Role activation, silent Role basis replacement, automatic lifecycle cascades, automatic corroboration, automatic findings, privacy-unsafe diagnostic copying, artifact containment failures, and external-reference authority overclaim.

# 41. Required Synthetic Examples

The completed issue should include at least:

1. firsthand roster-student Account;
2. Actor Account;
3. Account with verbatim quote and recorder summary;
4. secondhand Account;
5. conflicting Accounts;
6. source-evidenced Account retraction;
7. corrected Account successor;
8. paper-derived Account;
9. imported Account;
10. positive human Observation;
11. neutral Observation;
12. potentially concerning but purely observable Observation;
13. bounded Observation interval;
14. instrumented Observation;
15. corrected Observation;
16. invalidated Observation;
17. active `reported_involved` Role with qualifying aligned Account;
18. Account with source-artifact reference;
19. Observation with typed external PDS reference;
20. Statement of Disagreement targeting an Account.

All examples must be synthetic.

# 42. ADR 0011 Decision Set

ADR 0011 should finalize:

```text
Account semantic unit
Observation semantic unit
Account/Observation boundary
opaque identities and paths
human source/observer attribution
unidentified source treatment
source versus recorder distinction
firsthand/secondhand semantics
source-expressed uncertainty
quote versus summary
Observation method
structured measurement
targeting
Account retraction
lifecycle matrices
material correction
Account relations
reported_involved target alignment
paper/import review gates
source artifacts and external references
privacy boundaries
shared infrastructure reuse
no-automatic-finding rule
```

# 43. Resolved Pre-ADR Questions

The initial checkpoint left seven questions open. ADR 0011 freezes them as:

1. Shared represented-human attribution contract:
   `represented_human_attribution@1`.
2. Shared source-artifact reference contract:
   `source_artifact_ref@1`.
3. Shared evidence-time contract:
   `evidence_time@1`.
4. Observation measurement remains nested with the five bounded v1 measure
   forms defined by Decision 13.
5. Account relations remain nested in `account@1` with
   `reports_from | clarifies | retracts`.
6. Account and Observation v1 have no in-place Amendment paths.
7. Lifecycle reason vocabularies are frozen by Decisions 18 and 19.

No remaining architecture question blocks publication of the first Issue #15
schemas.

# 44. ADR 0011 Acceptance Gate

The pre-ADR gate is satisfied.

Accepted decisions now cover:

```text
Account/Observation semantic boundary
represented-human attribution
recorder separation
firsthand/secondhand semantics
source-expressed uncertainty
quote/summary representation
evidence timing
human/instrument observation
bounded measurement
Event/Participant targeting
source-evidenced Account retraction
lifecycle matrices and reason vocabularies
material correction and no-amendment v1 boundary
Account relations
reported_involved target alignment
paper/import review gates
source-artifact references
shared lifecycle/operational reuse
operational privacy
no-automatic-finding rule
```

The pre-ADR drift check found no conflicting Core or Portia public contract.

ADR 0011 therefore accepts this design as the implementation target for Issue
#15. Subsequent schema slices must remain within these boundaries unless a
concrete contradiction is discovered and documented through an explicit ADR
amendment or superseding decision.

# Current implementation reconciliation (Issue #19: Account/Observation v2)

Issue #19 encountered a concrete Support-Process evidence-owner gap: legitimate
support monitoring and student/family perspective do not necessarily represent
an Event. The accepted additive resolution is now published as:

```text
account@2
observation@2
```

Version 2 preserves the source-evidence unit of v1 while adding:

```text
work_kind = event | support_process
owner-conditioned work_id
owner-conditioned target family
```

Published Account/Observation v1 schemas remain immutable and Event-local.
Current writers prefer v2; no automatic migration is required.

Support-Process-owned evidence therefore no longer requires a fabricated Event,
and Outcome does not become a raw evidence container:

```text
substantive perspective → Account
direct measurement      → Observation
bounded evaluation      → Outcome
```

Exact v2 predecessor/history references remain version-specific and never
silently follow correction, migration, or successor state. Paper/import
activation continues to require the Issue #20 review gate.
