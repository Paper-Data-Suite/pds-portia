# Issue #56 — v0.3 Capture / Import Runtime Reconciliation

Status: **Reconciliation complete — PR qualification pending**

Issue: `#56 — Reconcile accepted paper/import contracts with the released v0.2 runtime`

Umbrella: `#55 — C. v0.3.0 — Add reviewed paper/import intake and privacy-minimized downstream publication`

## Purpose

Issue #56 is the contract/runtime reconciliation gate between the accepted
Issue #20 / ADR 0016 paper-import architecture and the released Portia v0.2.0
application.

Slice 1 does not choose new contract versions and does not promote deferred
capture/import schemas into production runtime support. It records and
mechanically protects the exact starting state that later slices must reconcile.

The governing distinction remains:

```text
paper / scan / import source
≠ interpreted candidate
≠ human-confirmed capture value
≠ canonical Portia domain fact
≠ human domain judgment
```

## Exact starting authority

The Issue #56 branch starts from authoritative post-release `main`:

```text
commit:
7794b577ab6da444a501efb198895f9e4ff5726c

tree:
3da71310deb3cfb1f3bf05136909e6d660527b6d
```

The immutable released v0.2.0 application baseline remains:

```text
version:
0.2.0

tag:
v0.2.0

release commit:
83cfe05ef6b03d8453fdb60d1a1702f138d5293d

release tree:
2050bd1c7aabb47ccf2df4a8285c7a61ac360f2e

wheel:
pds_portia-0.2.0-py3-none-any.whl

wheel SHA-256:
7ae545e62740b4411736fc55e572a86384ed8714f1f65346d65e36a7943f3550
```

Current Core qualification authority recorded by the v0.2.0 release audit:

```text
pds_core-0.6.5-py3-none-any.whl

SHA-256:
9ace75f17b23b7f0ed6a709d531af5120db43d0325b4148d26f2d6ba1d4b3c18

source commit:
64da9d2e4884ffe78a020aed87b1d5b9500927ad
```

## Published but deferred capture/import contracts

The following contracts already exist in the public schema catalog but are
deliberately classified by the released v0.2 runtime as:

```text
disposition = deferred_v0_3
modelled = false
```

Paper capture:

```text
capture_batch@1
page_target@1
page_record@1
paper_interpretation@1
capture_proposal@1
capture_review@1
capture_materialization@1
```

Structured import:

```text
import_batch@1
import_source_record@1
import_proposal@1
import_review@1
import_materialization@1
```

This distinction is important:

```text
published schema
≠ executable v0.2 runtime support
```

Issue #56 must deliberately move from this state. No later slice may treat the
contracts as already operational merely because their schemas are catalogued.

## Core-owned boundary at the baseline

The released runtime explicitly keeps the generic paper infrastructure
Core-owned and unmodelled by Portia:

```text
module_work_ref@core-0.6
module_record_ref@core-0.6
route_locator@core-0.6
route_registration@core-0.6
retained_source_scan@core-0.6
```

Issue #56 may reconcile Portia usage of the current Core APIs, but it must not
create Portia replacements for these concepts.

## Concrete reconciliation questions exposed by the v0.3 product direction

### 1. Daily Classroom Observation is not a first-class Page Target purpose

`page_target@1` currently defines:

```text
new_event_capture
event_evidence_capture
support_process_evidence_capture
follow_up_capture
implementation_capture
fidelity_capture
reentry_capture
repair_capture
multi_entry_event_capture
other
```

The initial v0.3 product surface now requires first-class support for:

```text
Daily Classroom Observation
Focused Tally / Monitoring
Communication Log
```

Permanent use of `other` for these central workflows would erase useful
mechanical meaning. Later Issue #56 slices must decide whether this requires
`page_target@2`, a separate versioned purpose contract, or another minimum
versioned representation.

Slice 1 records the mismatch only. It does not choose the successor design.

### 2. Capture Batch has no structured class-session context

`capture_batch@1` is intentionally minimal. Beyond operational identity and an
optional label, it does not carry structured fields for:

```text
class-session date
lesson objective
lesson steps / activities
bounded instructional context
```

The Daily Classroom Observation workflow needs that context available during
review without turning it into behavior-domain history or duplicating it into
every downstream canonical record.

Later slices must decide where exact class-session context belongs.

### 3. Canonical Observation v2 requires Event or Support Process ownership

`observation@2` currently permits:

```text
work_kind = event
or
work_kind = support_process
```

That is a deliberate v0.2 rule and includes the invariant:

```text
portia.observation.no_fake_event_requirement
```

A routine Daily Classroom Observation may contain useful student-specific
observable information before any legitimate Event or Support Process exists.

Issue #56 must therefore choose an honest path without fabricating an Event:

```text
capture-only source until later domain choice

or

human-reviewed creation of a legitimate Event + Observation

or

a minimum new versioned ownership/context model
```

Slice 1 freezes only the starting constraint.

### 4. Capture Review v1 does not directly model the full umbrella vocabulary

`capture_review@1` currently has these immutable review dispositions:

```text
accepted
corrected_and_accepted
rejected
unresolved
```

and field decisions:

```text
accept_candidate
correct
select_alternative
mark_unreadable
leave_unresolved
```

Umbrella #55 describes teacher actions using the broader product vocabulary:

```text
accept
revise
split
reject
defer
request rescan
```

Those do not necessarily require a new review contract. For example:

- revise may already be `corrected_and_accepted`;
- split may belong to proposal generation rather than review disposition;
- defer may be represented by unresolved/no-current-decision semantics;
- request rescan may be a workflow action rather than a review decision.

Issue #56 must decide that explicitly before review UI/services are built.

## Initial v0.3 paper surface

The reconciled architecture should optimize for low-friction classroom capture,
not for reproducing every Portia digital record family on paper.

The initial form inventory is:

```text
Daily Classroom Observation
Focused Tally / Monitoring
Communication Log
Support / Intervention Implementation
Follow-Up
bounded Fidelity / Reentry / Repair forms where domain semantics justify them
```

### Daily Classroom Observation

This is a primary use case.

One form represents one exact class/session context and should support:

```text
class
session date
lesson objective
major lesson steps / activities
optional bounded contextual notes
0..N independently reviewable observation entries
```

Entries may be:

```text
positive
general / neutral
concerning
student-specific
class-level
```

The capture cue is not a domain judgment:

```text
positive / general / concern
≠ Classification
≠ severity
≠ risk
≠ misconduct
≠ culpability
```

One physical sheet may produce zero, one, or many later canonical operations.
The returned page does not imply one Event or one student.

## Slice 1 invariant

Until Issue #56 explicitly changes the contract/runtime disposition:

```text
capture/import v1 public schemas remain published
and
capture/import v1 runtime support remains deferred/unmodelled
```

Later slices are expected to change that state deliberately.

## Slice 1 non-goals

Slice 1 does not:

```text
change runtime-coverage.json
add capture/import runtime models
change MODEL_REGISTRY
change the compiled runtime contract bundle
modify any published schema
create a @2 contract
choose Observation ownership
choose Page Target v2 semantics
choose Capture Review v2 semantics
implement Capture Batch/Page Target services
render forms
render PDS2 QR codes
accept scans
run OCR/mark recognition
materialize canonical records
implement imports
change teacher authority
change privacy/export policy
```

The next slice should use this baseline to make the first explicit contract
disposition decisions.

## Slice 2 decision — Classroom Observation capture

ADR 0021 freezes the first concrete v0.3 paper decision:

```text
Capture Batch@1 remains the non-domain operational work root.

Page Target@2 is additive and names:
- classroom_observation_capture
- focused_monitoring_capture
- communication_capture

Daily Classroom Observation lesson/session values are returned-page source
context, not pre-print Capture Batch fields.

Observation@2 remains Event/Support-Process owned.

No class-day Event container is introduced.

Positive/general/concern form cues remain capture aids, not domain judgment.
```

`page_target@2.entry_layout.context_entry_key` identifies the page-local entry
whose capture-spec fields provide source/session context. It does not contain the
context values itself.

A routine classroom note remains capture-stage source material until a teacher
deliberately maps it to legitimate domain work. A selected note may later
contribute to an existing Event/Support Process or to a newly accepted neutral
Event plus child evidence. Merely printing/scanning the daily sheet never
creates that Event.

At Slice 2, `page_target@2` is intentionally catalogued as
`deferred_v0_3 / modelled=false`. Runtime promotion is a later reconciliation
step.

## Slice 4 decision — Capture Batch runtime

`capture_batch@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

It remains the non-domain operational work root accepted by ADR 0016. Runtime
promotion does not add `capture_batch` to `portia_work_ref@1`, whose domain work
kinds remain exactly `event` and `support_process`.

## Slice 5 decision — Page Record runtime

`page_record@1` is sufficient unchanged and is promoted to
`current_v0_3 / modelled=true`.

The runtime preserves exact Page Record, Capture Batch, Page Target, route,
retained-source, digest, physical-page, and processing-state values. Core remains
authoritative for RouteRegistration and retained-source existence/agreement;
local parsing does not fabricate those cross-system facts.

Page Record processing state remains non-domain and cannot itself materialize or
confirm a behavior-domain record.

## Slice 6 decision — Paper Interpretation runtime

`paper_interpretation@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

The exact immutable record preserves one interpretation generation, its
historical layout snapshot, interpreter/mapping profile, page-local entry/field
keys, candidate literals, normalized candidates, alternatives, uncertainty
state, and confidence.

Runtime promotion does not change the authority model: machine/manual candidate
≠ human confirmation; confidence ≠ truth; mapped record kind ≠ creation
authorization; complete processing ≠ semantic correctness. Same-profile replay
idempotency, changed-profile generation creation, and lineage resolution remain
service-layer responsibilities.

## Slice 7 decision — Capture Proposal runtime

`capture_proposal@1` is sufficient unchanged and is promoted to `current_v0_3 / modelled=true`. Capture Proposal remains immutable, noncanonical, and pre-review: it binds exact Paper Interpretation fields to one exact target contract/context without copying candidate literals or authorizing materialization. `new_work` remains limited to Event or Support Process; exact context resolution, target-path validation, logical-path uniqueness, replay idempotency, review, and materialization remain later service/application responsibilities.

## Slice 8 decision — Capture Review runtime

`capture_review@1` is sufficient unchanged and is promoted to
`current_v0_3 / modelled=true`.

Capture Review is the first attributable human-confirmation record in the paper
pipeline, but the authority boundary remains narrow: accepted or
corrected-and-accepted confirms staging transcription/mapping for the next
workflow step. It does not establish source truth, credibility, fault,
institutional authority, domain judgment, or canonical materialization.

The accepted immutable sequence model remains authoritative. Review corrections
or reversals create later review sequences with exact predecessor identity;
current decision is derived from preserved history. Review eligibility,
cross-record lineage, cycle/fork policy, split/defer product actions,
source recovery/rescan, and materialization remain later service/workflow
responsibilities. No Capture Review v2 is introduced.

## Slice 9 decision — Capture Materialization runtime

`capture_materialization@1` is sufficient unchanged and is promoted to
`current_v0_3 / modelled=true`.

Capture Materialization remains an immutable operational receipt, not a domain
record or persistence engine. It intentionally has no standalone `cmat_` identity;
receipt identity is the exact Operation Journal reference plus exact review lineage.

Materialization continues to reuse existing Operation Journal, Operation Lock,
preflight, write-set, commit-point, readback, and recovery rules. Retry/restart
must reconcile the same stable operation intent, and a missing receipt after durable
canonical acceptance must not replay canonical creation. Runtime promotion does not
yet implement the materialization service or cross-record recovery checks.

## Slice 10 decision — Import Batch runtime

`import_batch@1` is sufficient unchanged and is promoted to
`current_v0_3 / modelled=true`.

Import Batch begins a distinct structured-import runtime path. It remains an
operational attempt root rather than Portia domain work and must not be confused
with Capture Batch, paper/PDS2 routing state, or the existing derived
`source_snapshot@1` contract.

The runtime preserves exact source profile, import-specific source snapshot,
mapping profile, stable import identity digest, optional previous-batch
comparison, and lifecycle state. Recomputing identity/comparison truth,
reconciling unchanged replay, resolving source profiles, preventing fuzzy person
identity, and producing downstream source-record/proposal/review/materialization
state remain later application/service responsibilities. No Import Batch v2 is
introduced.

## Slice 11 decision — Import Source Record runtime

`import_source_record@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

The runtime preserves one immutable source-side observation within one exact
Import Batch, including the Portia-local `isrc_` identity, stable source-key
origin/value, content digest, source-record identity digest, bounded normalized
source fields, provenance time, and attribution.

This does not make a source row a Portia Event or other domain record.
`source_record_key` remains source/profile identity rather than person, Actor,
student, work, or canonical-record identity. Row number, array position,
display text, filename alone, fuzzy matching, and import order remain prohibited
identity inputs.

The runtime preserves explicit source null separately from an absent field.
Source values remain assertions, not Portia judgments. Changed source content
creates preserved later history, and absence from a later Import Batch is not
deletion, deactivation, invalidation, or supersession.

Runtime promotion does not implement source-profile resolution, digest
recomputation, logical field-key uniqueness, replay reconciliation, identity
resolution, proposal generation, review, or materialization services.

## Slice 12 decision — Import Proposal runtime

`import_proposal@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

The runtime preserves one immutable mapping-stage proposal derived from one
exact Import Source Record under its exact Import Batch mapping identity. The
opaque `iprp_` proposal ID remains distinct from the deterministic
`proposal_key` and `proposal_identity_digest` used for replay reconciliation.

Source-value bindings reference exact source fields rather than copying source
values into the proposal. A `transformed_candidate` remains only a deterministic
mapping candidate. `human_resolution_required` supplies no value and must not
be treated as null, false, no, or another implied conclusion.

`new_work` remains structurally restricted to Event or Support Process roots.
Exact existing-work and existing-record contexts remain historical references.

Runtime promotion does not implement lineage resolution, digest recomputation,
replay reconciliation, fuzzy/person identity resolution, domain judgment,
human review, canonical writes, or materialization services.

## Slice 13 decision — Import Review runtime

`import_review@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

Import Review remains immutable operational staging review, distinct from the
canonical Portia `review@1` domain family. The substantive reviewer is
represented-human attribution; persistence attribution remains separate.

`accepted` and `corrected_and_accepted` mean only that the exact mapping is
accepted for the next workflow gate. They do not establish source truth,
authority, credibility, fault, causation, consent, domain judgment, or legal /
process validity. `unresolved` is not negative, false, no, declined, or another
implied conclusion, and `rejected` rejects only the staging proposal.

Review correction/reversal remains immutable history through `review_sequence`
and exact predecessor linkage. No mutable current/latest review pointer is
introduced; current staging disposition is derived from preserved history.

Runtime promotion does not implement reviewer authorization, lineage resolution,
target-path cross-checks, sequence/fork/cycle validation, domain judgment,
canonical writes, or materialization services.

## Slice 14 decision — Import Materialization runtime

`import_materialization@1` is sufficient unchanged and is promoted to:

```text
current_v0_3 / modelled=true
```

The runtime preserves the immutable post-commit receipt linking one exact
accepted Import Review and its exact Import Batch / Import Source Record /
Import Proposal lineage to one exact completed or reconciled coordinated
Operation Journal revision and the exact canonical results produced or affected.

No standalone import-materialization identifier is introduced. As accepted by
the public contract, receipt identity remains the exact import lineage plus the
stable coordinated operation identity/intent. `import_materialization` therefore
must not appear in `IDENTITY_FIELDS`, and `logical_id` remains `None`.

The existing Operation Journal, Operation Lock, expected-prior-state, preflight,
commit-point, recovery, and Quarantine boundaries remain authoritative.
Persisting the receipt does not execute writes. A missing receipt after durable
canonical acceptance is a recoverable post-commit artifact and must not cause
canonical creation to replay.

Accepted import review remains a staging gate rather than a domain judgment.
Produced canonical records use existing import creation provenance; source,
proposal, review, operation, and receipt timestamps do not substitute for domain
time. Changed source/mapping/review history and later source absence preserve
history rather than silently rewriting or deleting canonical data.

Runtime promotion does not implement materialization orchestration, operation
allocation, lock acquisition, canonical writes, recovery, replay reconciliation,
Quarantine decisions, or domain-correction workflows. Those remain owned by the
existing persistence/workflow machinery and later integration work.

## Final Issue #56 reconciliation — Slice 15 closeout

The accumulated Slice 1–14 decisions now form one complete executable contract
answer for the rest of v0.3.

There are no active `deferred_v0_3` capture/import contracts. Page Target v1 is
an exact historical read, Page Target v2 is current, and all other accepted
paper/import operational records are current v0.3 runtime models.

The only new public contract required by released-runtime/product reconciliation
is additive `page_target@2`. All accepted Issue #20 v1 contracts remain
byte-for-byte unchanged from the Issue #56 starting baseline.

ADR 0021 remains the accepted Classroom Observation decision. Session context is
returned-page source context, not a canonical ClassroomSession record. For this
contract freeze, unreviewed structured interpretation of lesson/session context
may be displayed during source review but must not be used as confirmed
structured analytics. Any later requirement for structured human-confirmed
classroom-session analytics requires an explicit versioned confirmation/storage
contract rather than silent promotion of interpretation output.

Capture Review v1 remains sufficient: accept/revise/reject/defer map to its
existing immutable dispositions/history; split remains service-level remapping
into independently reviewable proposals; rescan/source recovery remains a
workflow action rather than a review disposition.

The final runtime, Core-reuse, form, authorization, storage/ownership,
migration/history, synthetic-scenario, and deferred-capability matrices are
recorded in:

```text
docs/validation/issue-56-final-reconciliation-and-qualification.md
docs/validation/issue-56-acceptance-matrix.md
```

Production printing/scanning/OCR/review/import/materialization services remain
later #55 implementation work. That is capability deferral, not contract/runtime
ambiguity.
