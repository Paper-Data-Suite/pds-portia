# Student Timeline and Work View

Issue #48 implements Portia's production teacher-facing, privacy-minimized
student timeline and work view. The view is derived at read time from exact
canonical Portia state. It is not a canonical student dossier, export,
disclosure record, grade input, portfolio feed, attention queue, or behavior
score.

## Exact focal identity and bounded scope

The focal student identity is the exact Core roster tuple:

```text
(class_id, student_id)
```

Names, preferred names, initials, Actor identity, Contact Points, fuzzy
similarity, and a matching local student ID in another class do not establish
identity. Actor and roster identity remain separate. A broader multi-class
query is allowed only when the caller explicitly supplies the exact work-owner
class scope and focal roster references.

The default view is deliberately bounded. It does not perform workspace-wide,
all-year, all-class, Actor-expanded, same-name, or same-student-ID discovery.
Related work may add context only when the related work is independently inside
the explicit focal query scope.

## Work discovery and grouping

`StudentWorkDiscoveryService` discovers current `event@2` and
`support_process@1` work roots by exact focal participant membership.
`StudentTimelineService` groups authorized entries under those authoritative
Event or Support Process roots. A multi-student Event remains one shared Event;
the view does not create student-owned copies of the Event.

Legacy Event history is fail-closed when exact historical participant authority
cannot be established. Present-day membership is never treated as proof of
historical membership.

## Current and history modes

Current mode uses canonical sources plus family-specific current-use and
lifecycle authority. It does not select currentness by timestamp, filename,
identifier ordering, or highest schema version. Superseded and invalidated
representations are not independent current facts. Quarantine/current-use blocks
produce bounded unavailable state rather than bypassing the guard.

History mode is deliberate and requires explicit history permission. It may
include privacy-safe historical domain representations, lifecycle transitions,
lifecycle-history corrections, Amendments, Statements of Disagreement,
representation migration, Ownership Correction, and bounded Exceptional
Removal history. Storage revision history is not presented as domain history.
Historical references stay pinned to their exact identities and do not silently
follow correction, supersession, migration, ownership correction, duplicate
consolidation, or removal.

A Statement of Disagreement never rewrites its target. The generic view marks
statement content for manual review rather than reproducing contested text by
default.

## Projection policy and privacy dispositions

The code-owned student-view policy has a deterministic policy identity and a
closed exact contract/version inventory. Unknown contracts and versions fail
closed. The ordinary projection preserves five distinct dispositions:

```text
included
absent
withheld
unavailable
requires_manual_review
```

`withheld` is not absence. `unavailable` is not absence. A manual-review result
is not silently paraphrased into a supposedly safe source statement.

The projection is a positive allowlist. Generic views do not expose Contact
Point values, endpoint references, filesystem paths, retained-source paths,
operation-journal internals, locks, raw integrity findings, source fingerprints,
or derived-pointer internals.

Multi-participant and multi-person records preserve native scope and focal
applicability separately. Unrelated participant/recipient identities and hidden
counts are not emitted by default. The view does not rewrite a multi-party
source as though it originally concerned only the focal student.

## Record categories and semantic distinctions

The view preserves distinct semantic families rather than flattening them into
one behavior narrative:

```text
Account                  represented-source report or perspective
Observation              direct or instrumented evidence
Review                    human review activity
Classification            attributed classification
Hypothesis                tentative attributed interpretation
Determination             bounded attributed determination
Response                  bounded action
Communication             bounded contact act or attempt
Support / Intervention    planned support activity
Implementation            actual occurrence
Fidelity                  implementation-quality judgment
Follow-Up                 later workflow activity
Outcome                   attributable bounded evaluation
Reentry                   bounded reentry workflow
Repair                    bounded repair workflow
```

The view does not infer responsibility from reported involvement, success from
completion, read/understood/consent from completed Communication, effectiveness
from Fidelity, causal proof from Outcome, clearance from Reentry, or
admission/remorse/forgiveness from Repair.

No behavior score, risk score, severity score, offender count, permanent tier,
student ranking, predictive label, or automatic intervention recommendation is
part of the production surface.

## Account, Observation, and Communication boundaries

Account and Observation remain separate. Account source/target applicability,
information origin, certainty, quote/summary representation, content,
elicitation, relations, and artifacts are not collapsed into one field.
Unsafe narrative is manual-review or withheld rather than automatically
rewritten.

Observation structured-measurement shape can be independently represented while
narrative remains separately controlled. Source artifacts remain separately
authorized.

Communication privacy scope is a handling classification rather than generic
authorization. Restricted and unknown scope fail closed for ordinary detail.
Recipients, Contact Points, endpoint references, attachments, and relations are
not exposed merely because the focal student is one participant. Completed does
not imply delivered, read, understood, or consented.

## Chronology

`StudentChronologyService` uses a closed record-family chronology adapter.
Semantic chronology is drawn from the accepted family fields: Event occurrence,
Account provided time, Observation time, Response/Communication act time,
planned Support/Intervention timing, Implementation occurrence, Fidelity
evaluation, Follow-Up timing, Outcome timeframe, and Reentry/Repair timing.
History artifacts use their explicit lifecycle/correction/migration/removal
history time.

Precision is preserved as exact offset timestamp, approximate timestamp,
timestamp range, date only, date range, or unknown. The view does not invent
midnight for a date-only source. `created_at` and `updated_at` remain audit
provenance unless a history artifact explicitly uses recorded/created time as
its honest navigation basis. Unknown semantic time remains unknown. Ordering is
deterministic with exact source identity as the neutral tie-breaker.

## Filters

`StudentTimelineFilter` provides bounded filters for:

```text
current/history mode
calendar date/range
work kind
exact work
record family
category
canonical status
safe workflow/evaluation state
sort direction
```

Filters operate only on already-authorized/projectable metadata and cannot
widen privacy. There is no severity, risk, offender, or score filter.

## Quarantine and Exceptional Removal

Quarantine is operational state, not lifecycle status. The generic student view
does not expose raw integrity findings or operation-journal diagnostics. A
blocked source is represented only through a bounded unavailable reason and
detailed recovery/attention presentation remains Issue #49's responsibility.

Exceptional Removal is never reversed by the view. If a removal certificate
exists for an exact history target and the canonical payload is absent, the
view may state only that the historical representation is unavailable. It does
not reproduce removed payload or confidential removal rationale. If both the
payload and certificate exist, the view treats that as recovery-required rather
than choosing one by convenience.

## Foreign-source boundary

Portia may carry exact references to sibling-module or external artifacts, but
Issue #48 does not fetch or copy foreign canonical payload. Foreign content and
source artifacts remain separately authorized by their owning module/service.
No Meridian, Vitrine, Concord, ScoreForm, or Quillan runtime dependency is added
by the student view.

## Read-only and noncanonical behavior

Generating, sorting, filtering, or grouping the view performs no canonical
student-view write. It does not create a timeline/profile schema, mutate Event
or Support Process records, create Actors or Actor relationships, transition
lifecycle, advance canonical pointers, create deliberate exports, or mutate
Core rosters. Any future acceleration must remain rebuildable derived state and
cannot become authoritative student truth.

## Issue boundaries

Issue #48 owns the derived student timeline/work projection only.

- #49 owns teacher-facing attention and unresolved/recovery presentation.
- #50 owns teacher-menu composition and navigation.
- #51 owns deliberate export generation and export provenance.
- #52 owns suite readiness/integration providers.

The student view therefore does not implement attention ranking, menu redesign,
export/disclosure, or suite-readiness behavior.
