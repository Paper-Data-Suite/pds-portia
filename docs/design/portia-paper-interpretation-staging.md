# Portia Paper Interpretation Staging

Issue #20 Slice 4 defines the first post-dispatch staging layer after a returned physical page has a durable Portia Page Record.

The boundary is:

```text
Core retained source
→ Portia Page Record
→ Paper Interpretation generation
≠ attributable human review
≠ canonical behavior-domain record
```

## Semantic unit

One `paper_interpretation@1` is one immutable interpretation generation for one exact Page Record. It preserves what an interpreter detected from the exact historical page layout without claiming that the detected content is true, correctly attributed, semantically valid, or eligible for canonical use.

The record is capture-batch-local operational staging. It does not broaden `portia_work_ref@1`, which remains intentionally limited to canonical Event and Support Process work.

## Minimal interpretation identity

A durable interpretation uses:

```text
interpretation_id = pint_<opaque>
generation        = positive integer
```

The `pint_` prefix is collision-free against the Portia identifier inventory at the Slice 4 checkpoint and encodes no content or domain meaning.

Same Page Record plus the same contract-significant interpreter profile is idempotent. A retry does not create another logical generation merely because the code ran twice. A changed interpreter version or mapping profile/version creates a new preserved generation instead of mutating the earlier candidate history.

No mutable `latest_interpretation` pointer is added to Page Record. A current/latest review queue or convenience pointer is derived, rebuildable state.

## Historical layout exactness

Every interpretation copies the exact historical layout identity used during processing:

```text
template_id
template_version
layout_version
capture_spec_version
layout_fingerprint
page_role
page_ordinal
```

Application validation requires this snapshot to agree exactly with the Page Target. A later installed template or mapping must never reinterpret an older returned page silently.

The interpretation also preserves an exact interpreter profile:

```text
interpreter_id
interpreter_version
mapping_profile_id
mapping_version
```

This makes changed-code and changed-mapping reprocessing auditable.

## Entry keys are page-local slots, not domain records

Page Target defines stable `entry_key` slots. Paper Interpretation stores an object map keyed by those exact entry keys.

An entry key means only:

> this historical capture layout defines this independently reviewable slot.

It does not identify a student, Event, Account, Observation, or other canonical record.

Each slot has one mechanical state:

```text
blank
unreadable
candidate
```

`blank` and `unreadable` deliberately have no `fields` payload. A candidate slot contains one or more capture-spec field candidates.

A multi-entry page can therefore preserve, in one immutable generation:

```text
row_01 = candidate
row_02 = blank
row_03 = unreadable
row_04 = candidate
```

without forcing all rows into the same student/Event or requiring all-or-nothing page success.

## Field uncertainty is explicit

Candidate entries store field maps keyed by stable capture-spec `field_key`. An optional `region_key` is the smallest additional region locator when one field key is insufficient. No global field/region identifier is introduced.

Each field preserves one recognition state:

```text
blank
unmarked
unreadable
ambiguous
candidate_detected
```

These states are intentionally not Boolean domain values.

```text
blank     ≠ false / no
unmarked  ≠ false / no / declined
unreadable ≠ blank
ambiguous ≠ selected
```

`candidate_detected` requires the literal emitted candidate. An optional normalized value may preserve deterministic parsing, but normalization never replaces the literal candidate.

`ambiguous` requires at least two alternatives and intentionally forbids a selected winner in the interpretation layer.

## Candidate literal versus normalized candidate

`candidate_literal` is the literal transcription/detection result emitted by the interpreter. For handwriting/OCR it must not be silently polished into a purported quotation. For mark recognition it represents the detected/mapped literal candidate, not an independently made Portia judgment.

`normalized_value` may hold a deterministic scalar or bounded scalar list needed for later review. The original literal remains preserved.

Confidence values, when emitted, are bounded to `0..1` and exist only for review prioritization. They are not truth probability, credibility, authority, or permission to bypass review.

## Mapped record kind is descriptive only

An exact historical mapping profile may know that a slot is intended to feed a particular Portia family. `mapped_record_kind` may therefore name a current canonical family such as:

```text
event
account
observation
implementation
fidelity
follow_up
reentry
repair
```

This value must come from the exact mapping profile/template, not from interpreting narrative meaning or detected marks. It means only "the mapping profile would stage this slot toward this family." It does not create the record or establish its semantics.

This is especially important for judgment-bearing families. A fidelity form can map toward `fidelity`, but software detecting a marked box does not itself make a Fidelity judgment.

## Human review remains a separate later layer

Paper Interpretation deliberately has no fields for:

```text
reviewer
review disposition
human-confirmed value
canonical record ID
materialized records
```

Later Issue #20 work must preserve attributable review capable of:

```text
accept
correct
reject
leave unresolved
mark unreadable
```

without erasing the original interpretation generation.

A later review may confirm or correct a machine candidate. It may also decide that a candidate should produce no canonical record.

## No identity or judgment inference

Interpretation may perform mechanical recognition and deterministic normalization. It must not independently infer:

```text
person identity from display text / roster position
source authorship
firsthand status
Event participation or fault
Classification
Hypothesis
Determination
Response appropriateness
Support recommendation
Fidelity
Outcome / effectiveness
recurrence failure
Reentry completion
Repair completion
remorse
forgiveness
```

When a printed field records a human judgment, interpretation preserves only the detected human mark candidate. The human review layer later determines what can be confirmed and materialized under the existing domain contract.

## Raw source ownership

Paper Interpretation contains no scan/PDF/image bytes and no temporary scanner paths.

The provenance chain remains:

```text
Paper Interpretation
→ exact Page Record
→ Core RouteRegistration + retained-source identity
→ immutable Core-retained source
```

Core source history remains intact even when interpretation is partial, later rejected, or never materialized.
