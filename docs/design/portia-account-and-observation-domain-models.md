# Portia Account and Observation Domain Models

**Status:** Draft — pre-ADR design checkpoint
**Project:** Paper Data Suite
**Module:** `pds-portia`
**Issue:** `#15 — Define Account and Observation domain models`
**Umbrella:** `#10 — Complete the Portia foundations milestone`
**Date:** 2026-08-07
**Branch:** `15-account-observation-domain-models`

## 1. Purpose

This document defines the pre-ADR architecture for Portia Accounts and Observations.

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

A pre-ADR drift check and final pre-acceptance drift check remain required.

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

# 5. Provisional Decision 1: Account Semantic Unit

One Account represents:

> One coherent attributed statement, report, response, recollection, or perspective from one represented human source concerning one Event-local target.

An Account is not the Event, an objective Event narrative, a credibility judgment, an Event Participant Role, a finding, a Classification, a Hypothesis, a Determination, a Communication record, or a permanent person identity.

The same source may have several Accounts when there are several distinct source contributions. A later clarification, correction, or retraction must not silently rewrite the earlier Account.

One interview, email, paper form, or imported source artifact may yield several Event-local Accounts when it contains materially separate source contributions. Common artifact provenance may be shared without merging those Accounts.

## 5.1 Coherence boundary

One Account should normally correspond to one coherent contribution that a teacher could present as one source position without materially changing its meaning.

A single Account may preserve several content segments from that same contribution, including both verbatim quotation and recorded summary, when the provenance of each segment remains explicit.

Unrelated statements should not be grouped merely because they were captured during the same conversation.

# 6. Provisional Decision 2: Observation Semantic Unit

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

# 7. Provisional Decision 3: Canonical Identity and Storage

Account identity will use:

```text
acct_<opaque-id>
```

Observation identity will use:

```text
obs_<opaque-id>
```

The diagnostic prefixes do not carry source, target, student, Actor, content, severity, or lifecycle meaning.

Expected public identifier contracts:

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

# 8. Provisional Decision 4: Event-Local Targeting

Both Account and Observation will reuse `portia_target_ref@1`.

The target may be the containing Event, one Event Participant, or an explicit set of Event Participants.

The target answers what the source contribution or observation concerns. The source or observer answers who supplied or directly observed the information. These concepts remain independent.

Application validation must require Participant targets to resolve within the containing Event. Historical targets remain exact and are not silently retargeted after Participant replacement.

# 9. Provisional Decision 5: Human Source and Observer Attribution

Account source and human Observation observer require substantially the same human-attribution semantics. Schema implementation should therefore evaluate one small shared public primitive rather than copy two incompatible unions.

Provisional branches:

```text
roster_student
actor
local_operator
descriptive_person
unidentified_person
```

Roster-student attribution preserves `roster_student_ref` plus a bounded display snapshot. Actor attribution preserves `actor_ref` plus a bounded display snapshot. Actor contact values are not copied into attribution.

A descriptive person supports a human source who should not be promoted to Actor identity. Representative description types may reuse the established `outside_student`, `family_member`, `school_staff`, `visitor`, `community_member`, and `other` vocabulary.

The unidentified branch supports:

```text
anonymous
withheld
uncertain
not_recorded
```

without fabricating a canonical person reference.

An unidentified Account may be valid canonical evidence while remaining ineligible for a consequential consuming use.

# 10. Provisional Decision 6: Recorder Attribution Is Separate

Every Account distinguishes represented source from `created_by` / `updated_by`.

Every Observation distinguishes represented observer or instrument from `created_by` / `updated_by`.

An OCR process, import process, or system process is not the represented source merely because it generated JSON.

The same teacher may be both observer and `created_by` for a directly entered teacher Observation, but the concepts remain separate in the wire model.

# 11. Provisional Decision 7: Account Information Origin

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

# 12. Provisional Decision 8: Source-Expressed Uncertainty

Portia may preserve source-expressed certainty using a bounded nonnumeric vocabulary such as:

```text
stated_certain
stated_uncertain
mixed_or_qualified
not_recorded
```

This records how the source expressed the contribution. It is not credibility, reliability, truth probability, or a confidence score.

Automated prose analysis must not populate this field without explicit review.

# 13. Provisional Decision 9: Account Content Representation

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

# 14. Provisional Decision 10: Account Timing

Account statement time is distinct from Event occurrence time, record creation time, paper scan time, and import time.

At minimum, source-contribution time should support:

```text
exact
approximate
date_only
unknown
```

Observation timing additionally requires bounded ranges.

Schema implementation should determine whether one small shared temporal primitive can serve both records without importing Event-specific semantics.

No precise source-contribution timestamp may be invented from `created_at`.

# 15. Provisional Decision 11: Observation Attribution

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

# 16. Provisional Decision 12: Observation Method

Observation method must distinguish how the information was directly obtained.

Provisional vocabulary:

```text
live_direct
artifact_review
manual_count
manual_timing
instrumented
other
```

`artifact_review` means the observer directly examined a source artifact. It does not mean the observer was present for the original Event. The source artifact remains separately referenced when material to the Observation's meaning.

# 17. Provisional Decision 13: Observation Content and Measurement

Observation content may contain narrative observable information, structured measurements, or both. At least one is required before activation.

The canonical Observation model will not contain a positive/neutral/concerning valence field.

Version 1 should support bounded common classroom measurement forms:

```text
count
duration
latency
percentage
other_numeric
```

The final schema must bind measure type, value, and unit coherently. `other_numeric` requires an explicit measure label and unit.

Measurement does not imply normative interpretation.

# 18. Provisional Decision 14: Observation Timing

Observation time may represent an exact instant, approximate instant, date-only observation, bounded range, or unknown time.

A bounded observation period remains one Observation when the content and method form one coherent observation context.

Observation time is distinct from `created_at`. Artifact review may legitimately occur after the original Event.

# 19. Provisional Decision 15: Positive, Neutral, and Potentially Concerning Use

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

# 20. Provisional Decision 16: Conflicting Accounts

Conflicting Accounts remain separate canonical records.

Portia does not automatically merge them, invalidate one, choose a winner, calculate credibility, count agreeing Accounts as proof, or generate a finding.

The existing Statement of Disagreement contract remains the preferred mechanism when an identified human explicitly disputes an exact canonical Account or Observation.

Ordinary source disagreement does not require a Statement of Disagreement merely because two Accounts conflict.

# 21. Provisional Decision 17: Account Retraction

Account retraction must be source-evidenced. A teacher must not mark an Account `retracted` merely because the teacher no longer believes it.

Provisional architecture:

```text
original Account
    <- exact retracts relation from
new Account by the same represented source

coordinated lifecycle transition:
original Account -> retracted
```

The retraction Account preserves what the source said when retracting or withdrawing the earlier contribution.

Application validation must require the same represented source, same Event, exact predecessor Account reference, eligible retraction Account lifecycle, and coordinated original-Account lifecycle transition.

Retraction does not establish that the earlier Account was false. A retracted Account remains historically resolvable. A later reaffirmation creates new source evidence rather than silently reactivating the same retracted representation.

# 22. Provisional Decision 18: Account Lifecycle

Provisional statuses:

```text
proposed
active
retracted
invalidated
superseded
```

Provisional matrix:

```text
proposed -> active | invalidated | superseded
active -> retracted | invalidated | superseded
retracted -> superseded
invalidated -> superseded
superseded -> terminal
```

Retraction and invalidation are intentionally distinct.

# 23. Provisional Decision 19: Observation Lifecycle

Provisional statuses:

```text
proposed
active
invalidated
superseded
```

Provisional matrix:

```text
proposed -> active | invalidated | superseded
active -> invalidated | superseded
invalidated -> superseded
superseded -> terminal
```

Observation does not acquire `retracted` merely because Account uses it.

# 24. Provisional Decision 20: Material Correction and Supersession

Material Account changes include represented source, target, content, quote/summary representation, information origin, materially different source-expressed uncertainty, statement timing, and material source provenance.

Material Observation changes include observer or instrument, target, observable narrative, measurement, unit, observation interval, method, and material source provenance.

The existing Amendment contract may be used only for a narrow set of nonmaterial fields approved during schema implementation. Primary source wording and primary observed information are not routine mutable text.

Historical consumers do not silently follow successors.

# 25. Provisional Decision 21: Account-to-Account Relations

Account needs a small typed relation set for source lineage and retraction.

Provisional relation types:

```text
reports_from
clarifies
retracts
```

`reports_from` may preserve known secondhand lineage. `clarifies` preserves an additional same-source contribution without declaring the predecessor invalid. `retracts` supports source-evidenced retraction.

Material correction remains represented through canonical supersession rather than a `corrects` relation.

Relations use exact same-Event Account references and establish neither credibility nor truth.

# 26. Provisional Decision 22: `reported_involved` Integration

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

Provisional qualifying source forms are `roster_student`, `actor`, `local_operator`, and `descriptive_person`. The `unidentified_person` branch does not qualify. This is a traceability requirement, not a credibility judgment.

If a referenced Account later becomes retracted, invalidated, superseded, or exceptionally removed, the Role basis is not silently rewritten and no automatic lifecycle cascade occurs.

# 27. Provisional Decision 23: Observation Basis and Roles

Observation may remain a Role basis where compatible with Role semantics, but Observation does not satisfy the Account requirement for active `reported_involved`.

If an Observation supports a `present`, `directly_involved`, or `contextual` Role, application validation must still check same Event, target alignment, Observation current-use eligibility, and Role-specific lifecycle rules.

Observation does not automatically create or activate a Role.

# 28. Provisional Decision 24: Paper Capture

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

# 29. Provisional Decision 25: Import

Imported Accounts and Observations use `creation_source.type = import`.

Version 1 uses a conservative review gate:

```text
imported canonical Account/Observation begins proposed
local review is required before activation
```

Import does not infer Actor identity from name similarity or email, Participant identity from display text, credibility from source system, or firsthand status from prose.

Import provenance remains distinct from source or observer attribution.

# 30. Provisional Decision 26: Source Artifacts and External References

Account and Observation may need to refer to returned paper, written statements, images, audio, video, screenshots, documents, emails, instrument output, other PDS records, or external institutional records.

Canonical Account and Observation JSON will not embed binary payloads.

Schema implementation should evaluate one shared Portia-scoped source-artifact reference primitive with closed branches for:

```text
workspace artifact
exact Portia record
typed sibling-module record
external record locator
```

Core-retained paper provenance remains Core-owned and should be referenced through the accepted PDS2/retained-source boundary rather than copied into a new Portia attachment store.

External references are inert locators. Portia must not fetch, execute, authenticate, or infer authority from an external reference merely because it exists.

Artifact references do not establish authenticity or truth.

# 31. Provisional Decision 27: Shared Infrastructure Reuse

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

# 32. Provisional Decision 28: Operational Privacy

Operational and diagnostic records should prefer opaque IDs, record kinds, paths, contract versions, fingerprints, byte lengths, status tokens, counts, and step results.

They should not copy Account quotation text, Account summary text, Observation narrative, student names, Actor display names, contact values, attachment content, or transcripts.

Integrity Findings may report structural defects such as source unresolved, target unresolved, paper provenance mismatch, successor chain broken, or privacy-unsafe payload. They must not become domain findings such as `credible report`, `concerning student`, `policy violation`, or `behavior finding`.

# 33. Provisional Decision 29: No Automatic Finding

Persisting an Account or Observation creates source evidence only.

It does not automatically create a finding, Classification, Hypothesis, Determination, policy violation, severity, or risk level.

Likewise, three Accounts do not automatically mean three independent confirmations, and one Account plus one Observation does not automatically mean corroborated.

Later review and decision records may reference source evidence while preserving their own explicit human attribution and authority.

# 34. Expected Public Contract Work

The schema phase should evaluate and likely add:

```text
portia_account_id@1
portia_observation_id@1
account@1
observation@1
```

Likely shared primitives to evaluate:

```text
human_source_attribution@1
source_artifact_ref@1
```

A shared temporal primitive should be added only if Account and Observation really need the same public wire shape.

Dedicated Account/Observation reference schemas should not be added merely for convenience if constrained `local_record_ref@1` and `exact_local_record_ref@1` already provide the correct semantics.

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

# 43. Remaining Pre-ADR Questions

The following are intentionally not frozen into public wire contracts by this checkpoint:

1. Exact name and shape of the shared human-attribution schema.
2. Exact name and shape of the source-artifact reference schema.
3. Whether Account/Observation temporal precision should use one shared public schema or nested contract-specific definitions.
4. Exact structured measurement vocabulary and unit rules.
5. Whether retraction relation evidence lives directly in Account or in a small dedicated relation primitive.
6. Exact nonmaterial Amendment paths.
7. Exact lifecycle reason vocabularies.

These questions should be resolved in the next design/ADR slice before any Account or Observation public schema is published.

# 44. Pre-ADR Acceptance Gate

The design is ready for ADR 0011 only when:

- the Account/Observation boundary is accepted;
- human source/observer attribution is settled;
- Account retraction has source-evidenced semantics;
- structured measurement is bounded enough for v1;
- the `reported_involved` target-alignment rule is accepted;
- paper/import activation gates are accepted;
- artifact/reference semantics are bounded;
- shared lifecycle and operational reuse is confirmed;
- and no repository drift introduces a conflicting public contract.

No JSON Schema should be published before those decisions are frozen.
