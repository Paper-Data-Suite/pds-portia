# Portia Paper-Assisted Capture, PDS2 Routing, and Import Design

**Status:** Working architecture — pre-ADR
**Issue:** `#20 — Define paper-assisted capture, PDS2 routing, and import contracts`
**Date:** 2026-08-13
**Expected ADR:** `0016`, if still free at ADR publication time

## 1. Purpose

Issue #20 defines Portia's complete ingress boundary for:

```text
paper-assisted capture
Core-owned PDS2 routing
Core-retained paper-source provenance
machine interpretation candidates
attributable human review
canonical paper-derived materialization
structured/local imports
import replay/idempotency
```

The governing rule is:

> Paper, scans, OCR/mark recognition, imports, routing success, linkage, and
> software inference may produce source records and proposals, but must not
> manufacture behavior-domain facts, human judgments, or active canonical
> records when human review is required.

The architecture must preserve:

```text
printed page
≠ domain event

registered route
≠ returned page

returned page
≠ interpreted page

retained source
≠ accepted evidence

OCR / mark candidate
≠ confirmed value

successful PDS2 routing
≠ semantically valid Portia content

blank / unreadable
≠ false / no

same route
≠ same returned physical page

reprocessing
≠ new domain record

import source record
≠ Portia canonical record

source-system assertion
≠ Portia judgment

missing later import row
≠ deletion
```

Issue #20 must integrate with the behavior-domain model completed through Issue
#19 without reopening those semantics.

## 2. Starting Repository State

Issue #20 begins after Issue #19 was squash-merged and reconciled.

Exact initial remote anchors:

```text
pds-portia/main
c69533fa980cf41aa92c52978617e170263f6135

pds-portia/20-paper-assisted-capture-pds2-routing-import-contracts
c69533fa980cf41aa92c52978617e170263f6135

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
5974c6436f5f34df6d869e846fbb638d02359451

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede
```

Initial remote Portia comparison:

```text
status:    identical
ahead:     0
behind:    0
merge base:
c69533fa980cf41aa92c52978617e170263f6135
```

The final observed Issue #19 authoritative suite was:

```text
880 tests
OK
```

Issue #20 must establish its own observed local baseline on the exact branch
checkout before ADR acceptance. The preceding value is context, not a substitute
for that run.

ADR `0016` appeared unused at this initial checkpoint and must be rechecked
immediately before publication.

## 3. Existing Domain Semantics That #20 Must Not Reopen

Portia's accepted progression is:

```text
Event
→ Accounts and Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Implementation
→ Fidelity
→ Follow-Up / Outcome / Reentry / Repair
```

The arrows describe possible relationships, not mandatory record creation.

Issue #20 therefore must not make a paper/import workflow silently create a
semantic fact merely because a source artifact exists.

Examples:

```text
blank incident form
≠ Event

printed observation grid
≠ Observation

printed Intervention schedule
≠ Implementation

returned fidelity form
≠ Fidelity conclusion

returned Follow-Up form
≠ completed Follow-Up

returned Reentry form
≠ clearance

returned Repair form
≠ agreement / remorse / forgiveness

import label "resolved"
≠ Outcome / closure
```

Current exact work/history semantics also remain unchanged: exact references do
not silently follow correction, supersession, migration, ownership correction,
plan adaptation, or cross-year continuation.

## 4. Core PDS2 Is Infrastructure Authority

Core currently owns the generic PDS2 routing models:

```text
ModuleWorkRef
RouteLocator
ModuleRecordRef
RouteRegistration
RouteResolution
RetainedSourceScan
```

A Core locator is one expected physical-page route:

```text
schema = PDS2
module_id
class_id
work_id
route_id
```

A Core `RouteRegistration` maps that locator to an already-existing
module-owned `ModuleRecordRef`.

This creates the normative print-time sequence:

```text
module work exists
→ module routing target exists
→ Core RouteRegistration exists
→ exact active route resolves
→ PDS2 locator / QR may be rendered
→ page may be printed
```

Portia must not create replacements for Core's locator, route registration,
route resolution, retained-source identity, or generic dispatch contracts.

Core retains the original scan before module semantic processing. A later Portia
interpretation failure therefore cannot erase or rewrite Core routing/source
truth.

## 5. The Work-Identity Conflict

Portia's accepted domain storage model treats top-level behavior work as:

```text
Event
Support Process
```

and current `portia_work_ref@1` / `exact_portia_work_ref@1` intentionally encode
that meaning.

Core PDS2, however, requires `work_id` even for:

```text
blank new-Event form
class-level multi-entry capture sheet
```

where no legitimate Event or Support Process exists yet.

The following solution is rejected:

```text
create fake Event
→ obtain work_id
→ print blank form
```

That would make routing infrastructure manufacture a behavior-domain Event and
would corrupt Event counts, recurrence analysis, history, and downstream
semantics.

## 6. Working Decision: Operational Capture Batch

The recommended pre-ADR solution is a bounded **Capture Batch** operational
work root.

Candidate public surface:

```text
portia_capture_batch_id@1
capture_batch@1
```

A Capture Batch means:

> one bounded Portia operational context for preparing, routing, receiving, and
> reviewing one or more expected paper pages that cannot or should not be owned
> directly by an already-existing Event or Support Process.

A Capture Batch is **not**:

```text
Event
Support Process
case
incident
student dossier
behavior finding
atomic acceptance unit
statement that all pages concern one person
statement that all pages concern one occurrence
```

Likely storage shape:

```text
classes/<class_id>/modules/portia/work/<capture_batch_id>/
  work.json
  records/
  pages/
  routes/
  history/
  derived/
```

Using the existing module `work/` namespace is attractive because Core requires
a module work identity. The semantic distinction must nevertheless remain
explicit:

```text
behavior-domain work
= Event | Support Process

operational paper-capture work
= Capture Batch
```

The existing behavior-domain `portia_work_ref@1`,
`exact_portia_work_ref@1`, work-relationship semantics, and generic domain
target unions should **not** automatically gain `capture_batch`.

Capture-specific references/targets should be introduced only where concrete
paper routing/recovery examples require them.

### Why a batch rather than making Page Target the work root?

A separate Capture Batch better supports:

* a class-level multi-entry sheet;
* multi-page packets;
* reprints;
* several expected pages sharing one print/review operation;
* independent Page Targets under one operational context;
* Core's work-vs-record distinction;
* and later capture-level recovery/derived queues.

It also avoids making one expected physical page simultaneously mean both
"module work" and "route target record."

This remains a working decision until ADR 0016.

## 7. Existing-Work Pages

Not every page needs a Capture Batch.

A page may legitimately be associated with an already-existing:

```text
Event
Support Process
```

when that work exists for independent domain reasons.

Examples:

```text
existing Event
→ print bounded evidence-capture page

existing Support Process
→ print monitoring / follow-up page
```

The page must preserve the exact printed context. If the referenced work/child
is later corrected or superseded before return, software does not silently
retarget the historical page to the successor.

ADR 0016 must decide whether Page Targets for existing work live directly under
that work root or whether all printed pages are normalized under Capture Batch.
The current preference is:

```text
existing legitimate Event/SP page
→ may use existing domain work root

blank / class-level / not-yet-domain-owned page
→ Capture Batch root
```

because it minimizes extra operational work while preserving honest identity.

## 8. Working Decision: Page Target

Issue #20 needs an existing Portia module record that Core can target before QR
rendering.

Candidate surface:

```text
portia_page_target_id@1
page_target@1
```

One Page Target means:

> one expected physical page with a stable Portia capture purpose and exact
> layout/context required to interpret a later return.

It is routing/capture infrastructure, not behavior evidence.

Creating it does not assert:

```text
Event occurred
person participated
statement was made
Observation occurred
classification applies
Response occurred
Support was delivered
Implementation occurred
Fidelity result exists
Outcome exists
Reentry occurred
Repair occurred
```

A Page Target should preserve at least:

```text
page_target_id
class/module context
containing work/capture context
page purpose
template identity
template/layout version
layout fingerprint or equivalent stable specification
page role / ordinal where applicable
entry definitions or layout reference
exact existing domain context where intentionally printed
lifecycle / provenance
```

Core's `RouteRegistration.target` should identify this exact Portia Page Target
with a supported contract version.

Core `module_details` may contain convenience routing hints but must not become
the only authoritative copy of Portia page semantics.

## 9. Page Purpose

A closed descriptive vocabulary should be evaluated, likely including:

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

Purpose is descriptive only:

```text
new_event_capture
≠ Event exists

implementation_capture
≠ Implementation occurred

fidelity_capture
≠ Fidelity result

repair_capture
≠ Repair completed
```

## 10. Registration Before Render

The intended application sequence is:

```text
1. persist legitimate containing work/capture context
2. persist Page Target
3. create Core RouteRegistration
4. resolve and verify exact active route
5. render QR/PDS2 locator
6. print page
```

Application validation must reject or block rendering for at least:

```text
missing Page Target
wrong module
wrong class
wrong work
route-target disagreement
unsupported/null target contract version where exactness is required
inactive/invalidated route
template/layout disagreement
```

Human fallback and locator content must be privacy-minimized.

## 11. Preallocation Rule

The baseline rule is:

> Printing alone does not create a new behavior-domain record.

Existing records may be rendered if they already exist for independent domain
reasons.

Examples:

```text
teacher intentionally creates Follow-Up plan
→ may print it

teacher intentionally creates Reentry plan
→ may print it

teacher intentionally creates Intervention
→ may print monitoring material
```

But:

```text
blank Event form
→ no Event yet

blank Account form
→ no Account yet

blank Observation sheet
→ no Observation yet

printed Intervention schedule
→ no Implementation yet

blank Fidelity form
→ no Fidelity yet

blank Outcome form
→ no Outcome yet

blank Repair form
→ no participation/agreement/completion yet
```

### `creation_source@1` reconciliation

Existing `creation_source@1` paper provenance includes:

```text
type = paper_capture
stage = preallocated | ingested
route_id
page_record_id
```

The word `preallocated` must not be generalized into permission to create every
domain family before printing.

Working interpretation:

* an already-legitimate canonical record may carry paper-preallocation
  provenance when the record exists independently of the act of printing;
* a source/proposal workflow may reserve operational IDs;
* blank forms do not create substantive domain facts merely to reserve identity.

ADR 0016 must reconcile this explicitly with a per-family preallocation matrix.

## 12. Working Decision: Returned Page Record

Existing `source_artifact_ref@1` already anticipates paper provenance shaped as:

```text
kind = paper_capture
route_id
page_record_id
source_page_number?
```

This is strong evidence that Issue #20 should publish the previously deferred
Page Record identity.

Candidate surface:

```text
portia_page_record_id@1
page_record@1
```

One Page Record should mean:

> one Core-retained source-scan intake successfully dispatched to one exact
> Portia Page Target.

It should preserve:

```text
Page Record identity
Core source_scan_id
Core source SHA-256 / retained-source provenance as appropriate
exact route identity
exact Page Target
intake / dispatch occurrence
template/layout interpretation context
processing generations/status
```

It must not duplicate the raw image/PDF bytes.

Core remains authoritative for the retained source. Portia records the semantic
bridge from that retained source to Portia capture processing.

## 13. Source Retention and Semantic Failure

These may coexist:

```text
Core routing success
Core retained source exists
Portia Page Record exists or processing starts
Portia semantic interpretation fails
```

Portia must not repair such a failure by rewriting or deleting:

```text
Core route registration
Core route identity
Core source_scan_id
Core retained-source bytes
Core source fingerprint
```

Examples of Portia-local failures:

```text
unknown template version
missing Page Target
wrong class/work relationship
unreadable page
ambiguous handwriting
impossible mark combination
proposal validation failure
human rejection
application invariant failure
```

Those are Portia processing/review/integrity facts, not retroactive Core routing
failures.

## 14. Physical Page Independence

PDS2 identifies physical pages independently.

Therefore:

* each expected page has its own route;
* each retained returned source remains independently represented;
* scan order does not create page identity;
* missing page 2 does not invalidate page 1;
* a foreign-module page remains opaque to Portia;
* packet membership must be explicit rather than inferred from filenames/order.

A Capture Batch may group pages operationally without making them one semantic
incident or one atomic acceptance unit.

## 15. Reprocessing Versus Duplicate Returns

These must be distinct.

### Same Page Record, same interpreter version

Reprocessing is idempotent and must not duplicate proposals or canonical domain
records.

### Same Page Record, new interpreter version

A new interpretation generation may be created. Earlier candidate/review
history remains preserved. Active canonical records are not silently rewritten.

### Same route, different Core retained source

The sources remain distinct historical intakes. Same route does not prove same
physical page occurrence.

### Same content hash

Identical bytes/content are duplicate evidence, not authority to erase one
source intake. Copies, scanner behavior, and legitimate resubmission remain
possible.

Possible duplicates may be surfaced for human review without deleting Core
history.

## 16. Multi-Entry Pages

One physical page may contain:

```text
0..N independently reviewable entries
```

PDS2 identifies the page, not each row/box.

The preferred identity is a stable Page-Target-local key:

```text
entry_key
```

rather than a globally opaque entry ID unless later examples prove that global
identity is required.

Requirements:

* entry ordering is not identity unless the versioned layout says so;
* each accepted entry preserves exact Page Record + entry/region provenance;
* entries may be accepted/rejected/unresolved independently;
* blank entries create no domain record;
* unreadable is not blank;
* partial-page success is allowed;
* one page does not imply one student or one Event;
* duplicate/reprocessing logic operates at exact page + entry + interpretation
  generation scope.

## 17. Source/Recognition State

Paper interpretation must preserve at least the conceptual distinctions:

```text
blank
unmarked
unreadable
ambiguous
candidate present
human confirmed
```

These are source/recognition states, not behavior conclusions.

Examples:

```text
blank checkbox
≠ false

unreadable name
≠ unidentified person confirmed

ambiguous mark
≠ selected value

empty Repair field
≠ declined participation
```

## 18. Working Interpretation / Proposal / Review Layers

Issue #20 needs to preserve three different things:

```text
what the machine/source appears to contain
what Portia proposes it might become
what a human actually accepts/corrects/rejects
```

Candidate concepts:

```text
paper_interpretation@1
capture_proposal@1
capture_review@1
```

The ADR must determine the minimum justified public surface.

### Paper Interpretation

Likely records an immutable/versioned processing generation over one exact Page
Record and contains entry/region candidates such as:

```text
interpreter identity/version
layout version
candidate literal text/mark
optional deterministic normalization
recognition uncertainty/confidence
bounded alternatives
processing timestamp
```

It must not become an active canonical domain record.

### Capture Proposal

Likely represents a prospective mapping from one source entry/region to one
Portia domain record or bounded record set.

A proposal does not assert that the target domain fact is true.

### Capture Review

Likely preserves:

```text
reviewer attribution
exact interpretation/proposal generation
entry key
review time
accepted | corrected_and_accepted | rejected | unresolved
correction where applicable
exact canonical records materialized
```

The machine candidate must survive human correction.

The design should not overload `quarantine_record@2` as the ordinary review
queue. Quarantine remains exceptional integrity isolation.

## 19. OCR and Mark Boundaries

Automation may mechanically detect text/marks but may not independently infer
Portia human judgments.

For handwriting/OCR:

```text
uncertain OCR
≠ confirmed verbatim quotation

normalized OCR
≠ exact source wording

nearby roster label
≠ confirmed Actor identity
```

For marks:

```text
detected mark
≠ Classification
≠ Hypothesis
≠ Determination
≠ Fidelity
≠ Outcome
≠ Repair agreement
```

A machine may preserve a candidate corresponding to a human mark on a
judgment-bearing paper field. Human review confirms that the mark was interpreted
correctly; software does not independently make the underlying judgment.

Confidence may prioritize review. It cannot serve as a universal threshold that
bypasses semantically required human review.

## 20. Canonical Paper Materialization

After review, the target domain contract remains authoritative.

Examples:

```text
paper perspective
→ Account proposal
→ attributable review
→ active Account only when allowed

paper direct count
→ Observation proposal
→ attributable review
→ active Observation only when allowed

paper incident row
→ proposed Event / participant evidence
→ human review
→ current-use domain records

paper schedule/checklist
→ candidate evidence
≠ automatic Implementation

paper Fidelity form
→ candidate human marks
≠ software-generated Fidelity judgment

returned Reentry / Repair page
≠ automatic completion / clearance / remorse / forgiveness
```

Paper-derived canonical records use:

```text
creation_source.type = paper_capture
```

where their existing contract supports creation-source provenance.

The final design must produce the per-family materialization/preallocation
matrix required by the issue.

## 21. Import Is a Separate Ingress Mode

Import provenance uses:

```text
creation_source.type = import
```

Paper does not become import merely because OCR is used.

Import does not become PDS2 merely because the source is a PDF/image/file.

The layers remain distinct:

```text
retained / referenced import source
→ bounded import attempt
→ source-side record
→ mapping / proposal generation
→ human review where required
→ canonical Portia record
```

## 22. Existing `source_snapshot@1` Must Not Be Overloaded

Portia already publishes `source_snapshot@1`, but its current contract is
specifically:

> a deterministic bounded inventory of exact source representations used or
> proposed for one **derived-projection generation**.

Its closed `projection_kind` and source-role vocabularies serve derived-state
rebuilds such as dependency graphs, lifecycle timelines, current-state views,
operation recovery, integrity indexes, and summaries.

It is therefore **not** the authoritative import-source snapshot contract.

Issue #20 should:

* reuse `source_snapshot@1` later when rebuilding derived import/paper review
  indexes if its projection semantics fit;
* not mutate or overload it for raw import-file history;
* define the minimum import-native source/batch provenance needed for exact
  replay.

Existing `source_artifact_ref@1` does provide a useful `workspace_file`
representation with:

```text
workspace-relative path
content fingerprint
```

for Account/Observation source association, but that alone does not model an
import attempt, source-record identity, or mapping generation.

## 23. Working Import Model

Candidate surface:

```text
portia_import_batch_id@1
import_batch@1
import_source_record@1
```

A separate opaque source-record ID should be added only if durable
cross-reference value requires it.

### Import Batch

One bounded import attempt should preserve at least:

```text
source/profile identity
exact source artifact/fingerprint
mapping profile/version
started/completed/review state as appropriate
source-record counts/results
provenance
```

Batch completion does not mean every source record became a canonical Portia
record.

### Import Source Record

Represents the source-side unit, not an Event.

Identity should prefer a stable source-provided key when available and must not
silently fall back to mutable display text or row order when a better key exists.

One source record may produce:

```text
0..N proposals
```

and, when explicitly reviewed, several source records may contribute to one
canonical domain record.

## 24. Import Replay and Idempotency

### Same source snapshot + same mapping

Replay should produce the same logical source/proposal results without duplicate
canonical materialization.

### Same logical source key + changed content

Preserve new source/proposal history. Do not silently mutate the already
accepted Portia record.

### Same source + changed mapping version

Create a new interpretation/mapping generation rather than rewriting historical
accepted results.

### Source record absent later

Absence does not automatically mean:

```text
delete
invalidate
supersede
exceptionally remove
```

an existing Portia record.

Any correction/removal must use explicit Portia lifecycle/history semantics.

Import time and row order are not Event occurrence time.

## 25. Import Identity and Judgment Safeguards

Prohibited automatic identity mappings include:

```text
nearest name
→ Actor

same display name
→ same person

row position
→ student identity

source role label
→ Portia operational authority
```

Exact trusted identifiers may resolve under an explicit configured mapping
policy. Ambiguous identity remains unresolved/proposed for human review.

Likewise:

```text
source "behavior"
≠ automatic Classification

source "consequence"
≠ automatic Determination

source "resolved"
≠ automatic Outcome

source "returned"
≠ automatic Reentry completion

source "apologized"
≠ remorse / forgiveness / Repair completion
```

Import provenance preserves what the source asserted; it does not make the
source assertion a Portia human judgment.

## 26. Shared Infrastructure Reuse

Issue #20 should reuse existing generic infrastructure where the existing
semantic target actually fits.

### Operation Journal / Lock

Do not broaden behavior-domain exact target unions merely so Capture Batch looks
like Event/Support Process work.

When a reviewed paper/import proposal materializes actual Event/Support-Process
domain records, existing `operation_journal@2` / `operation_lock@2` can
coordinate those canonical writes and recovery.

If capture-operational persistence needs its own narrow coordination mechanism,
the ADR must demonstrate the concrete gap before expanding generic operation
targets.

Core retained source is never rolled back by a Portia transaction.

### Quarantine

Normal uncertain OCR/import review is not quarantine.

Use Quarantine only for integrity/exceptional isolation.

### Integrity Finding

Reuse Integrity Finding for conditions such as:

```text
Page Record → missing Page Target
route / class / work mismatch
accepted proposal → wrong page/entry
duplicate canonical materialization
import result → missing source record
unknown mapping version
```

An Integrity Finding is diagnostic and does not mutate the underlying source or
domain record.

### Derived state

Review/recovery queues may be derived:

```text
awaiting interpretation
awaiting human review
uncertain source values
possible duplicate page
failed materialization
```

They remain rebuildable and nonauthoritative.

## 27. Storage Direction

The final path model is pre-ADR, but the working separation is:

### Existing Event / Support Process page

```text
classes/<class_id>/modules/portia/work/<event_or_support_process_id>/
  pages/
  routes/
  records/
```

### Capture Batch

```text
classes/<class_id>/modules/portia/work/<capture_batch_id>/
  work.json
  pages/
  routes/
  records/
  history/
  derived/
```

### Imports

Import storage must be class/workspace-contained and preserve immutable source
fingerprints. The ADR must decide whether import batches are:

```text
class-local operational records
separate operational roots
or another bounded store
```

without pretending they are Event/Support Process behavior work.

Raw import source files must not be duplicated into every domain record.

## 28. Privacy Boundary

Issue #21 remains authoritative for complete:

```text
redaction
export
retention
Sunset integration
```

Issue #20 nevertheless must avoid structurally unnecessary sensitive copies.

Baseline:

* QR/fallback text is privacy-minimized;
* raw OCR narratives do not belong in logs/derived queue rows when exact refs
  suffice;
* raw Core scans are not copied into Portia JSON;
* imported raw rows are not duplicated across canonical records;
* workspace paths must remain contained/safe;
* paper/import review is scoped to the correct class/capture/work context.

## 29. Sibling Boundaries

### Core

Owns generic PDS2 locator/registration/resolution, retained source, and generic
dispatch.

### Quillan

Provides useful retain-first/per-physical-page precedent. Quillan remains owner
of substantial written-response/reflection artifacts.

### ScoreForm

Provides selected-response/OMR mechanical precedent only. Portia does not adopt
academic answer/scoring semantics.

### Meridian

No paper/imported behavior value automatically becomes a Score, standards
rating, Grade, or academic result.

### Vitrine

No paper/imported Portia material automatically becomes portfolio content.

## 30. Candidate Contract Inventory for ADR 0016

The ADR should evaluate, not blindly approve, this minimum candidate surface:

```text
portia_capture_batch_id@1
capture_batch@1

portia_page_target_id@1
page_target@1

portia_page_record_id@1
page_record@1

paper_interpretation@1
capture_proposal@1
capture_review@1

portia_import_batch_id@1
import_batch@1

import_source_record@1
```

A separate globally opaque identity for:

```text
page entry
page region
import source record
```

should be rejected unless exact cross-record use demonstrates the need.
Prefer bounded local keys when sufficient.

ADR 0016 must also decide whether paper and import proposals/reviews share one
contract or only share conceptual primitives. Source-specific semantics must not
be erased merely for implementation reuse.

## 31. Questions to Resolve Before ADR 0016

1. Does every printed page use Capture Batch, or only pages lacking an existing
   Event/Support Process owner?
2. What exact reference shape lets Page Target identify either domain work or
   Capture Batch without broadening behavior-domain `portia_work_ref@1`?
3. Does `capture_batch@1` need lifecycle/history separate from ordinary domain
   lifecycle?
4. Is Page Record immutable one-per-Core-source intake, with processing
   generations held elsewhere?
5. Are `paper_interpretation@1`, `capture_proposal@1`, and `capture_review@1`
   all independently valuable public records, or can the surface be smaller?
6. Can paper/import share a proposal/review contract without losing source
   semantics?
7. What exact retained import-source representation is required for deterministic
   replay?
8. Does `import_source_record@1` need a globally opaque ID?
9. Which current Portia domain families legitimately permit pre-print
   preallocation, and under what independent domain action?
10. Which existing operation/integrity/derived contracts can be reused without
    broadening Event/Support Process meanings?

## 32. Initial Preallocation Matrix Direction

This table is provisional and must be expanded/validated before ADR acceptance.

| Family | Blank-print precreate? | Existing record may print? | Returned source may propose? | Human judgment gate |
|---|---:|---:|---:|---|
| Event | No | Yes | Yes | Yes for identity/domain interpretation |
| Event Participant / Role | No | Yes | Yes | Yes |
| Account | No | Yes | Yes | Yes before active paper/import use |
| Observation | No | Yes | Yes | Yes before active paper/import use |
| Review | No | Yes | Potentially | Human-authored review required |
| Classification | No | Yes | Potentially | Human-attributed judgment required |
| Hypothesis | No | Yes | Potentially | Human-attributed judgment required |
| Determination | No | Yes | Potentially | Human-attributed judgment required |
| Response | No solely for printing | Yes | Potentially | Existing Response semantics |
| Communication | No solely for printing | Yes | Potentially | Contact/participant semantics reviewed |
| Support Process | No solely for printing | Yes | Potentially | Human workflow decision |
| Need / Goal | No solely for printing | Yes | Potentially | Human planning semantics |
| Support / Intervention | No solely for printing | Yes | Potentially | Human planning semantics |
| Implementation | No | Yes | Yes | Occurrence must be confirmed |
| Fidelity | No | Yes | Yes | Human-attributed evaluation |
| Follow-Up | No solely for printing | Yes | Yes | Workflow completion not inferred |
| Outcome | No | Yes | Yes | Human-attributed evaluation |
| Reentry | No solely for printing | Yes | Yes | Return/clearance not inferred |
| Repair | No solely for printing | Yes | Yes | Participation/agreement/completion not inferred |

"Potentially" means the source may support a proposal if a concrete template or
import mapping exists; it does not authorize software to make the semantic
judgment.

## 33. Proposed Implementation Slicing

Subject to ADR 0016, the implementation can likely proceed as:

```text
Slice 1  initial repository checkpoint + working design
Slice 2  pre-ADR checkpoint + ADR 0016
Slice 3  collision-checked capture/page/import identifiers
Slice 4  Capture Batch + Page Target + Core PDS2 registration integration
Slice 5  Page Record + retained-source provenance + duplicate/reprocessing rules
Slice 6  multi-entry interpretation/proposal/review + uncertainty
Slice 7  Import Batch + Import Source Record + mapping/replay/idempotency
Slice 8  shared recovery/integrity/derived integration
Slice 9  examples, matrices, final reconciliation/validation
```

The final slice count may change if ADR 0016 deliberately combines or rejects
candidate contracts.

## 34. Initial Architectural Recommendation

Proceed to ADR design with these working decisions:

```text
Core owns generic PDS2 routing + retained source.

Portia Capture Batch
= operational work identity for paper that has no legitimate domain work yet.

Capture Batch
≠ Event
≠ Support Process
≠ new behavior-domain portia_work_ref kind.

Page Target
= existing pre-print Portia record targeted by Core RouteRegistration.

Page Record
= one returned Core-retained source intake routed to one exact Page Target.

Page entry
= local stable key unless cross-record evidence proves global identity is needed.

Machine interpretation
≠ proposal
≠ human review
≠ canonical domain record.

Paper/import materialization
= review-gated according to the existing target-family semantics.

source_snapshot@1
= derived-projection infrastructure only, not import source authority.

Import Batch / Import Source Record
= likely required for deterministic replay and idempotency, subject to ADR.

Existing domain operation/lock targets
= not broadened merely to make capture infrastructure appear to be domain work.
```

This recommendation preserves both sides of the integration:

```text
Core gets a legitimate module work + record target before QR rendering.

Portia does not invent behavior-domain facts merely to satisfy Core routing.
```

That is the principal architecture constraint Issue #20 must solve.
