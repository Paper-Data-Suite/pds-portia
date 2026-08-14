# ADR 0016: Define Paper-Assisted Capture, PDS2 Routing, and Import Contracts

- **Status:** Accepted
- **Date:** 2026-08-14
- **Decision owners:** Portia maintainers
- **Related issue:** `#20 — Define paper-assisted capture, PDS2 routing, and import contracts`
- **Umbrella:** `#10 — Complete the Portia foundations milestone`
- **Builds on:** ADR 0002, ADR 0004, ADR 0007, ADR 0008, ADR 0009, ADR 0010, ADR 0011, ADR 0012, ADR 0013, ADR 0014, and ADR 0015
- **Preserves:** Core ownership of PDS2 routing and retained-source history; Portia ownership of behavior-domain meaning and human judgment

## Context

Portia's accepted canonical progression is:

```text
Event
→ Accounts / Observations
→ Review
→ Classification and/or Hypothesis
→ Determination
→ Response and/or Communication
→ Support Process / Support / Intervention
→ Implementation
→ Fidelity
→ Follow-Up / Outcome / Reentry / Repair
```

Issue #20 defines how paper-assisted capture and structured imports may feed that
progression without allowing transport, OCR, mark recognition, source-system
assertions, or software inference to manufacture behavior facts or human
judgments.

The governing distinctions are:

```text
printed page ≠ domain Event
registered route ≠ returned page
returned page ≠ interpreted page
retained source ≠ accepted evidence
OCR/mark candidate ≠ confirmed value
successful PDS2 routing ≠ semantically valid Portia content
blank/unreadable ≠ false/no
same route ≠ same returned physical page
reprocessing ≠ new domain record
Import Source Record ≠ Portia canonical record
source-system assertion ≠ Portia judgment
missing later import row ≠ deletion
```

Portia already has appropriate generic operational infrastructure:

```text
operation_journal
operation_lock
quarantine_record
integrity_finding
derived state
```

Core already owns generic PDS2 infrastructure:

```text
ModuleWorkRef
RouteLocator
ModuleRecordRef
RouteRegistration
RouteResolution
RetainedSourceScan
module dispatch
```

Issue #20 therefore must add only Portia-specific capture/import semantics and
must not create competing generic route or retained-source contracts.

### Pre-ADR drift check

Immediately before accepting this ADR:

```text
pds-portia/main
c69533fa980cf41aa92c52978617e170263f6135

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
b03ffad0749db0dce47e68f095a8d477fa69eb2d

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede
```

Portia, Core, and ScoreForm remain at the Issue #20 starting checkpoints.
Quillan is exactly one commit ahead of its starting checkpoint
`5974c6436f5f34df6d869e846fbb638d02359451`. That commit adds Core 0.6
academic-publication producer-profile support and does not change Quillan's
retain-first or per-physical-page paper-intake precedent.

ADR 0016 was unused immediately before this file was added.

The authoritative local branch checkpoint immediately before ADR acceptance is:

```text
Ran 1013 tests

OK
```

with `git diff --check` clean and 52 synthetic Issue #20 fixture examples.

## Decision

### 1. Core remains the sole owner of generic PDS2 routing and retained-source history

Portia does not publish replacements for Core concepts such as:

```text
pds2_route
route_registration
retained_source
generic_scan_record
```

Core route registration, resolution, retained-source identity, page dispatch,
and raw retained-source bytes remain Core responsibilities.

Portia consumes exact Core route/retained-source provenance and adds only
Portia-specific page meaning, interpretation, review, and materialization
semantics.

### 2. Capture Batch is the non-domain Portia work root for paper capture

Issue #20 accepts:

```text
portia_capture_batch_id@1
capture_batch@1
```

A Capture Batch is an operational work root for bounded paper capture. It solves
Core's required `work_id` for blank/new-record pages without fabricating an
Event or Support Process.

Capture Batch is not added to:

```text
portia_work_ref@1
exact_portia_work_ref@1
```

Those existing contracts remain intentionally limited to canonical Event and
Support Process work.

Creating a Capture Batch does not assert that any behavior-domain occurrence,
participant, judgment, response, support, implementation, outcome, reentry, or
repair exists.

### 3. Page Target is the legitimate pre-print route target

Issue #20 accepts:

```text
portia_page_target_id@1
page_target@1
```

A Page Target exists before QR/PDS2 rendering and preserves exact historical
capture semantics including:

- class/module ownership;
- Capture Batch ownership;
- page purpose;
- template identity and version;
- layout version and fingerprint;
- capture-spec version;
- page role and ordinal;
- capture mode;
- stable page-local entry keys;
- and exact existing Event/Support Process context when applicable.

The safe pre-print sequence is:

```text
1. create Capture Batch
2. create Page Target
3. create Core RouteRegistration
4. verify exact active locator → exact Page Target
5. render QR/PDS2 locator
6. print
```

A QR locator must not be rendered first and repaired by guessing a missing
Portia target later.

### 4. Printing never preallocates behavior-domain facts

A blank form does not create:

```text
Event
Event Participant / Role
Account
Observation
Review
Classification
Hypothesis
Determination
Response
Communication
Support Process / Participant
Support Need / Goal
Support
Intervention
Implementation
Fidelity
Follow-Up
Outcome
Reentry
Repair
```

Existing legitimately created records may be rendered when the paper page is a
representation of that existing context.

The accepted preallocation matrix is documented in:

```text
docs/design/portia-paper-preallocation-matrix.md
```

### 5. Page Record represents one returned physical page intake

Issue #20 accepts:

```text
portia_page_record_id@1
page_record@1
```

One Page Record means one Core-retained source page routed to one exact Page
Target.

A Page Record preserves Core retained-source identity, route identity, source
page number and fingerprint, Portia target identity, and processing state. It
does not embed raw image/PDF bytes.

Each physical page is independent:

```text
same route + different retained source → distinct Page Records
same content hash → possible duplicate evidence, not automatic collapse
scan adjacency/order → nonsemantic
missing packet page → does not invalidate successfully returned pages
```

Core retained-source history survives Portia failure or semantic rejection.

### 6. Paper Interpretation is immutable candidate staging

Issue #20 accepts:

```text
portia_paper_interpretation_id@1
paper_interpretation@1
```

One Paper Interpretation is one immutable interpretation generation for one
exact Page Record under one exact interpreter/mapping profile.

It preserves:

- exact historical template/layout snapshot;
- page-local entry and field keys;
- capture method;
- blank/unmarked/unreadable/ambiguous/candidate states;
- candidate literal value;
- optional normalized value;
- alternatives;
- confidence for review prioritization only;
- and deterministic mapped record kind when supplied by exact mapping.

It does not establish source truth, authorship, person identity, firsthand
status, fault, intent, severity, Classification, Hypothesis, Determination,
Response appropriateness, Support recommendation, Fidelity, Outcome, recurrence
failure, Reentry completion, or Repair meaning.

Same Page Record + same interpreter/mapping profile is idempotent.
A changed interpreter or mapping profile creates a preserved new generation.

### 7. Paper proposal and human review are separate from interpretation

Issue #20 accepts:

```text
portia_capture_proposal_id@1
capture_proposal@1

portia_capture_review_id@1
capture_review@1
```

Capture Proposal references exact interpretation fields rather than copying
source candidates unnecessarily.

Capture Review is an operational human-confirmation record, not Portia's
canonical domain `review@1`.

Accepted review dispositions are:

```text
accepted
corrected_and_accepted
rejected
unresolved
```

Human correction preserves the machine candidate in history. Review records
are immutable and sequenced so later review correction/reversal does not erase
earlier decisions.

A system process may create or persist operational artifacts, but the
substantive reviewer for human confirmation must be represented as a human
operator.

### 8. Paper materialization reuses coordinated-operation infrastructure

Issue #20 accepts:

```text
capture_materialization@1
```

and does not create a new materialization ID family.

The existing Portia coordinated-operation `op_` identity, Operation Journal,
and Operation Lock infrastructure remain authoritative for canonical writes.

The safe materialization boundary is:

```text
accepted Capture Review
→ deterministic operation intent
→ preflight
→ locks
→ canonical write/readback/acceptance
→ recovery/reconciliation if interrupted
→ immutable Capture Materialization receipt
```

If canonical acceptance succeeds and the process crashes before the receipt is
written, restart reconciles the same operation and writes the missing receipt.
It does not create the canonical record again.

New paper-derived canonical records use existing:

```text
creation_source.type = paper_capture
creation_source.stage = ingested
```

with exact route/Page Record provenance.

### 9. Import is a distinct source path, not a paper variant

Issue #20 accepts:

```text
portia_import_batch_id@1
import_batch@1

portia_import_source_record_id@1
import_source_record@1
```

One Import Batch represents one bounded attempt against one exact byte snapshot
and one exact mapping configuration.

One Import Source Record represents one source-side unit. It is not an Event
and may produce `0..N` proposals.

Import identity is derived from exact source/profile identity, source snapshot
or record content fingerprint, stable source-record key, and mapping
profile/version.

The following are not sufficient stable identity:

```text
row order
array position
display text
filename alone
similar name
similar email
```

The existing derived-state `source_snapshot@1` contract is not repurposed as
import-source authority.

### 10. Import replay preserves history

Accepted replay rules are:

```text
same source + same mapping
→ idempotent replay

same stable source key + changed content
→ preserve new source history

same source + changed mapping
→ preserve new mapping/proposal history

record missing from later source snapshot
→ no deletion implication
```

Changed source or mapping does not silently mutate a previously accepted
canonical Portia record.

Deletion, invalidation, correction, or exceptional removal must use explicit
Portia semantics.

### 11. Import proposal and review are import-specific

Issue #20 accepts:

```text
portia_import_proposal_id@1
import_proposal@1

portia_import_review_id@1
import_review@1
```

Import Proposal uses a stable mapping-local `proposal_key` plus deterministic
proposal identity evidence so one Import Source Record may safely yield
`0..N` independently reviewable proposals without array-position identity.

Import field bindings distinguish:

```text
source_value
transformed_candidate
human_resolution_required
```

Import Review uses the same four high-level dispositions as paper review:

```text
accepted
corrected_and_accepted
rejected
unresolved
```

Import review does not invent a paper-only unreadability concept for structured
source values.

### 12. Import materialization is coordinated and replay-safe

Issue #20 accepts:

```text
import_materialization@1
```

and again reuses existing `op_` coordinated-operation identity rather than
creating a separate materialization identifier.

The receipt binds exact:

```text
Import Batch
Import Source Record
Import Proposal
Import Review
Operation Journal revision
canonical outputs
```

New import-derived canonical records use existing:

```text
creation_source.type = import
```

Import provenance records source history; it does not establish source
authority or truth.

A crash after canonical acceptance but before the materialization receipt is a
post-commit recovery condition. It is not permission to create another
canonical record.

### 13. Human review does not replace domain judgment

Human confirmation in capture/import staging establishes only that a human
reviewer accepted or corrected the proposed transcription/mapping for
materialization.

It does not automatically create or establish:

- Classification;
- Hypothesis;
- Determination;
- fault, intent, or severity;
- Response appropriateness;
- Support recommendation;
- Fidelity;
- Outcome/effectiveness;
- recurrence failure;
- Reentry completion or clearance;
- Repair agreement, admission, remorse, forgiveness, or restoration.

Judgment-bearing canonical records still require the human attribution and
domain semantics already defined by their own contracts.

Imported/paper-derived Account and Observation remain conservatively proposed
until their domain activation rules permit current use.

### 14. Review, Integrity Finding, and Quarantine remain distinct

Ordinary uncertainty, incomplete mapping, OCR ambiguity, human rejection, and
recoverable processing failure belong in normal review/retry state.

Integrity Finding is diagnostic for broken invariants such as:

- Page Record → missing/wrong Page Target;
- missing retained-source provenance;
- route/work mismatch;
- accepted proposal → wrong entry/source record;
- duplicate canonical materialization;
- unknown mapping version;
- import result → missing Import Source Record.

Quarantine is exceptional integrity isolation, not an ordinary review queue.

Integrity Finding remains diagnostic and does not mutate canonical history.

### 15. Exact historical context does not silently retarget

Existing-work pages preserve the exact Event/Support Process and exact child
representation, where applicable, that the page was created to represent.

Later correction, supersession, ownership correction, migration, duplicate
consolidation, or Support Process continuation does not silently retarget the
historical paper/import source.

A human may explicitly use historical information in a later context, but that
does not rewrite the original source context.

### 16. Scan/import/processing timestamps are not domain timestamps

The following are operational timestamps only:

```text
print time
scan time
Core retain time
Portia dispatch time
interpretation time
import time
review time
materialization time
```

They must not substitute for Event time, evidence time, Communication time,
Implementation time, Outcome timeframe, or another domain-specific time merely
because the source lacks that information.

Unknown or lower-precision domain time remains unknown/lower precision.

### 17. Raw source bytes remain outside Portia JSON

Portia Issue #20 records must not embed:

- base64 scan/image data;
- PDF bytes;
- whole import files;
- transient absolute paths;
- temporary upload paths.

Core owns retained paper-source bytes. Import Batch identifies exact source
snapshots through bounded fingerprints/locators while keeping the source payload
outside these JSON contracts.

### 18. Public Issue #20 contracts are closed and versioned

Issue #20 publishes 22 public contracts:

```text
capture_batch@1
page_target@1
page_record@1
paper_interpretation@1
capture_proposal@1
capture_review@1
capture_materialization@1

import_batch@1
import_source_record@1
import_proposal@1
import_review@1
import_materialization@1

portia_capture_batch_id@1
portia_page_target_id@1
portia_page_record_id@1
portia_paper_interpretation_id@1
portia_capture_proposal_id@1
portia_capture_review_id@1
portia_import_batch_id@1
portia_import_source_record_id@1
portia_import_proposal_id@1
portia_import_review_id@1
```

All new JSON record schemas use Draft 2020-12, closed object shapes unless a
bounded map is intentionally required, immutable canonical `$id` values,
explicit discriminators, and `x-portia-application-invariants` for rules that
cannot be established structurally.

No published pre-Issue-20 schema `$id` is mutated by this decision.

### 19. Accepted opaque Issue #20 identifier prefixes

```text
Capture Batch:         cbat_
Page Target:           ptgt_
Page Record:           prec_
Paper Interpretation:  pint_
Capture Proposal:      cprp_
Capture Review:        crev_
Import Batch:          ibat_
Import Source Record:  isrc_
Import Proposal:       iprp_
Import Review:         irev_
```

No identifier encodes student identity, date, domain conclusion, confidence,
review disposition, or source-system meaning.

Materialization uses existing coordinated-operation `op_` identity.

## Rejected alternatives

### Pre-create an Event to obtain a PDS2 work ID

Rejected because it fabricates behavior-domain history and contaminates Event
counts/timelines.

### Put all page semantics in Core `module_details`

Rejected because Portia must own authoritative Portia page semantics and exact
historical template/layout identity.

### Treat one route as one returned page forever

Rejected because the same printed route may be returned more than once; each
Core-retained intake remains distinct.

### Treat identical content hashes as the same physical source

Rejected because content equality is evidence of possible duplication, not
authority to collapse retained-source history.

### Treat OCR/OMR confidence as acceptance

Rejected because confidence may prioritize human review but cannot establish
domain truth.

### Reuse canonical domain Review as capture/import review

Rejected because operational source confirmation and behavior-domain Review are
different semantic layers.

### Reuse Quarantine as the normal review queue

Rejected because Quarantine is exceptional integrity isolation.

### Reuse paper contracts for imports

Rejected because structured import source identity, replay, null/missing values,
and mapping history differ materially from physical-page interpretation.

### Use row number, filename, display text, or fuzzy person matching as import identity

Rejected because those are unstable or unsafe and can silently attach history
to the wrong source/person.

### Auto-delete Portia records when a later import omits a source row

Rejected because later absence is not a deletion instruction.

### Add a new materialization transaction system

Rejected because ADR 0009 already defines coordinated-operation identity,
journals, locks, recovery, partial-state handling, and Quarantine.

## Consequences

### Positive

- Portia can print blank/new-Event forms without fake Events.
- Core PDS2 ownership remains intact.
- retained-source history survives Portia processing failures.
- each physical returned page has independent provenance.
- machine interpretation remains reviewable candidate data.
- paper and import sources remain distinct.
- replay can be idempotent without erasing history.
- human review is attributable and correctable.
- canonical writes are crash-recoverable through existing Portia operations.
- source uncertainty and temporal precision are preserved.
- behavior-domain judgments remain human/domain-specific.
- raw source bytes are not duplicated into Portia JSON.

### Costs

- capture/import workflows require several explicit operational records;
- application validation must resolve exact cross-record and Core provenance
  that JSON Schema alone cannot prove;
- historical template/mapping versions must remain resolvable;
- recovery must reconcile operation history rather than simply retry writes;
- implementations must maintain derived review queues rather than treating them
  as canonical authority.

### Follow-up boundaries

Issue #20 does not implement:

- an executable Portia application;
- UI/UX for scanning or import review;
- Core generic PDS2 contracts;
- Quillan long-form paper processing;
- ScoreForm academic OMR/scoring;
- Meridian Grade/result production;
- Vitrine portfolio publication;
- suite-wide retention/export/redaction policy assigned to later issues.

## Validation artifacts

The accepted decision is supported by:

```text
docs/design/portia-paper-assisted-capture-pds2-routing-and-import.md
docs/design/portia-paper-preallocation-matrix.md
docs/design/portia-paper-interpretation-staging.md
docs/design/portia-paper-proposal-and-human-review.md
docs/design/portia-paper-materialization-and-recovery.md
docs/design/portia-structured-import-source-and-replay-semantics.md
docs/design/portia-import-proposal-and-human-review.md
docs/design/portia-import-materialization-and-recovery.md
docs/design/portia-paper-import-operational-failure-recovery-and-integrity.md

docs/validation/issue-20-application-invalid-matrix.md
docs/validation/issue-20-synthetic-example-inventory.md
docs/validation/issue-20-public-contract-and-core-reuse-inventory.md
docs/validation/issue-20-acceptance-matrix.md
```

Final authoritative validation and final repository drift are recorded after ADR
acceptance rather than inferred from this pre-ADR checkpoint.
