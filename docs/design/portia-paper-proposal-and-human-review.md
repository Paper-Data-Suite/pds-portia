# Portia Paper Proposal and Human Review

Issue #20 Slice 5 defines the two staging layers between immutable paper interpretation and later canonical materialization:

```text
Paper Interpretation generation
→ Capture Proposal
→ attributable Capture Review
≠ canonical materialization
```

The governing distinction remains:

```text
machine candidate ≠ human-confirmed value
human-confirmed transcription/mapping ≠ source truth
accepted review ≠ canonical record write
```

## Capture Proposal semantic unit

One `capture_proposal@1` is one immutable, independently reviewable mapping proposal for one exact page-local interpretation entry.

It preserves:

```text
exact Capture Batch / Page Target / Page Record lineage
exact Paper Interpretation ID + generation
exact entry_key
exact target Portia record kind + contract version
exact historical existing-work/record context where applicable
field-to-target mappings
privacy-minimized review-routing flags
proposal attribution/time
```

A proposal is not an Event, Account, Observation, Review, Classification, Implementation, Fidelity, Outcome, Reentry, Repair, or other domain fact.

## Candidate values are not duplicated into proposals

The proposal maps each target path to one exact interpretation field using:

```text
target_path
field_key
value_source
```

`value_source` is one of:

```text
candidate_literal
normalized_value
human_resolution_required
```

The proposal deliberately does not copy OCR text, handwriting candidates, mark alternatives, or normalized candidate payloads. Those remain in the immutable Paper Interpretation generation.

This reduces sensitive duplication and makes later audit straightforward:

```text
review decision
→ exact proposal binding
→ exact interpretation field
→ exact Page Record
→ Core-retained source
```

`human_resolution_required` can route an ambiguous or unreadable interpreted field to a human without software selecting a winner or manufacturing a value.

## Target contract and historical context

Proposal target identity is exact:

```text
record_kind
contract_version
context
```

Context is one of:

```text
new_work
existing_work
existing_record
```

`existing_work` uses `exact_portia_work_ref@1` and `existing_record` uses `exact_portia_work_record_ref@1`. These are historical anchors only. A returned page is never silently retargeted to a successor record created after printing.

The proposal does not decide generic lifecycle/materialization mechanics. Later materialization must respect the existing target family's own create/revision/correction rules.

## Proposal identity and replay

A proposal uses opaque:

```text
cprp_<opaque>
```

The prefix encodes no person, page, family, date, review state, or domain meaning.

Replaying the same exact interpretation entry through the same exact mapping to the same target contract must be idempotent. Changed mapping/proposal semantics preserve a new proposal instead of rewriting an earlier reviewed proposal.

There is no mutable proposal status. Pending/current review queues are derived, rebuildable state.

## Capture Review is a human decision-history record

One `capture_review@1` is one immutable human review decision over one exact Capture Proposal and one exact Paper Interpretation generation.

It uses opaque:

```text
crev_<opaque>
```

which is intentionally distinct from canonical Event-local `review@1` / `rvw_` semantics.

Review preserves:

```text
exact capture lineage
exact proposal
exact interpretation generation
exact entry_key
human reviewer attribution
review time
review disposition
field-level corrections/selections/unresolved states where needed
review sequence history
```

The substantive reviewer is represented with `represented_human_attribution@1`, not `attribution_agent@1`. A `system_process` therefore cannot structurally masquerade as the human reviewer. Application policy still determines which represented human is eligible and authorized to review a given class/work/capture context.

## Review dispositions

Version 1 uses:

```text
accepted
corrected_and_accepted
rejected
unresolved
```

### accepted

The reviewer accepts the exact proposal as staged. No field correction payload is stored.

This means only that the reviewer confirmed the staging transcription/mapping for the next workflow step. It does not establish source truth, credibility, consent, fault, authority, or domain outcome.

### corrected_and_accepted

At least one field has a human correction or explicit selection among machine alternatives.

A correction stores the human-confirmed replacement value only in the Capture Review. The original candidate remains untouched in Paper Interpretation.

An ambiguous candidate may be resolved with:

```text
select_alternative
alternative_index
```

so the human-selected option remains visibly distinct from the machine's original alternative set.

### rejected

The proposal should not proceed. Rejection requires a bounded reason code and does not erase the returned source, Page Record, interpretation, or proposal.

Human rejection is not Quarantine and does not prove the original source false.

### unresolved

Review cannot presently accept or reject the proposal. At least one field remains explicitly:

```text
mark_unreadable
leave_unresolved
```

Unresolved and unreadable remain distinct from blank/false/no/declined/absent.

## Review correction never mutates history

Capture Review is immutable. Review correction/reversal uses:

```text
review_sequence
predecessor_review_id
```

Sequence 1 has no predecessor. A later decision is another `crev_` record referencing the exact prior review. Current review state is derived from the preserved chain; no mutable `latest=true` field exists.

This is separate from `corrected_and_accepted`, which corrects the interpreted candidate while accepting the proposal. A later review sequence corrects the *review decision itself*.

## Acceptance does not materialize

Slice 5 intentionally forbids canonical materialization fields in both proposal and review.

The safe path remains:

```text
Page Record
→ Paper Interpretation
→ Capture Proposal
→ Capture Review
→ later coordinated canonical materialization
```

The later materialization layer must be idempotent and must preserve the exact accepted review plus exact canonical records produced/affected. This separation is required for recovery scenarios such as:

```text
human review accepted
→ canonical write starts
→ partial failure/crash
→ safe retry without duplicate records
```

An accepted review therefore cannot be treated as proof that a canonical record already exists.

## Review, Quarantine, and Integrity remain distinct

Ordinary OCR uncertainty, ambiguous marks, unresolved identity, reviewer correction, proposal rejection, or pending human review are normal proposal/review states.

Quarantine remains reserved for exceptional integrity isolation such as malformed persisted records, impossible owner/path mismatch, unsafe source path, or incompatible schema.

Integrity Finding remains diagnostic and may identify broken references such as a review pointing to a missing proposal. It does not make or reverse the review decision.
