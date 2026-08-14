# Portia paper materialization and recovery

Issue #20 distinguishes human-confirmed paper staging from canonical Portia domain persistence. This slice defines the bridge without creating a second persistence engine.

## Boundary

The safe path is:

```text
Capture Review (accepted/corrected_and_accepted)
  -> stable coordinated-operation intent
  -> Operation Journal preflight + deterministic locks
  -> canonical write staging/readback/acceptance
  -> commit/recovery reconciliation
  -> Capture Materialization receipt
```

A Capture Review is not a domain record and does not itself create anything canonical. A Capture Materialization is likewise not a domain record. It is an immutable receipt proving which exact accepted review was reconciled through which exact Portia coordinated operation and which exact canonical work/record representations were produced or affected.

## Reuse existing Portia persistence contracts

Issue #13 already defines the required persistence machinery:

- `operation_journal@1` for immutable operation revisions, intent, preflight, write sets, commit point, partial state, compensation, and recovery;
- `operation_lock@1` for deterministic privacy-minimized exclusive locks;
- `operation_journal_ref@1` for an exact immutable journal revision;
- existing exact Portia work/record targets for canonical representations.

Paper materialization MUST reuse those contracts. It does not define a capture-specific lock, transaction, current pointer, or retry token.

The existing `operation_kind` values remain sufficient. A materializer uses the operation kind required by the canonical domain action, for example `create_work`, `create_record`, or an existing correction/lifecycle operation. Issue #20 does not add a generic `materialize_capture` operation kind because that would obscure the actual canonical mutation being coordinated.

## Stable operation identity and idempotency

The same exact accepted Capture Review plus the same canonical materialization intent is one logical operation. Process restart does not create a second logical operation.

Before writes, application preflight must reconcile at least:

- exact Capture Batch / Page Target / Page Record lineage;
- exact Proposal and exact Capture Review sequence;
- the effective review decision at preflight time;
- exact target contract and existing context;
- deterministic materialization intent;
- expected prior canonical state;
- any prior Operation Journal revisions for that intent;
- any durable/accepted write fingerprints already recorded;
- any existing Capture Materialization receipt.

If a prior operation has partially persisted canonical state, recovery resumes or reconciles that operation under the Issue #13 rules. It does not allocate new Event/record identifiers merely because the process restarted.

## Capture Materialization receipt

`capture_materialization@1` is an immutable operational receipt. It intentionally has no new `cmat_` identifier. Its identity is carried by the exact operation journal reference plus exact Capture Review lineage.

The receipt preserves:

- class and capture-work lineage;
- exact Page Target and physical Page Record;
- exact Capture Proposal;
- exact Capture Review ID and sequence;
- exact completed/reconciled Operation Journal revision;
- one or more exact canonical results;
- materialization and receipt-recording attribution/time.

Canonical results distinguish only:

- `produced` — the operation created and canonically accepted the named representation;
- `affected` — an exact existing representation was materially involved under a legitimate domain operation.

`affected` is descriptive receipt language, not permission for in-place mutation. Existing Portia correction, lifecycle, successor, migration, consolidation, ownership-correction, and immutability rules still govern the domain operation.

## Receipt timing and crash recovery

The receipt is written only after the referenced Operation Journal proves required canonical-gate acceptance or equivalent recovery reconciliation.

A critical failure case is:

```text
canonical write accepted
-> process crashes
-> receipt not written
```

That state is recoverable. On restart, Portia reads the stable operation series, verifies the exact accepted write/readback state, and writes the missing receipt as a remaining post-commit artifact. It MUST NOT repeat canonical creation simply because the receipt is absent.

Conversely, a receipt must never claim canonical success when the referenced exact journal revision has not reached/reconciled canonical acceptance.

## Paper provenance on canonical records

For a canonical representation newly created from a returned paper page:

```json
{
  "type": "paper_capture",
  "stage": "ingested",
  "route_id": "<exact Core route>",
  "page_record_id": "<exact Portia Page Record>"
}
```

is the required `creation_source` shape where the target contract composes `creation_source@1`.

`stage = preallocated` is not valid for returned-page materialization. Page Target is the legitimate pre-print route target; behavior-domain records are not preallocated merely to render a QR/PDS2 route.

The shared version-1 provenance schema retains its historical structurally-safe fallback for paper identifiers. Issue #20 does not silently rewrite that already-published `$id`. Materialization application validation therefore applies the stricter now-known Page Record and Core route resolution requirements.

Where a canonical evidence contract supports `source_artifact_ref@1`, paper-derived evidence should preserve the matching paper locator using the same route, Page Record, and retained-source page number. That locator establishes provenance/location only, not truth, credibility, authenticity, authorization, or evidentiary weight.

## Capture review is not domain judgment

The Capture Review reviewer confirms staging transcription/mapping. That reviewer is not automatically the represented reviewer/selector/decision-maker/provider/assessor/participant required by a canonical domain contract.

In particular, materialization must not use Capture Review to manufacture:

- Classification or Hypothesis;
- Determination/fault/intent/severity;
- Response appropriateness;
- Support or Intervention recommendation;
- Fidelity;
- Outcome/effectiveness;
- recurrence failure;
- Reentry completion;
- Repair agreement, admission, remorse, forgiveness, or restoration.

If a paper page records one of those human judgments, the canonical target may be materialized only when the paper content and confirmed mapping supply the actual domain-required human attribution/basis/values under that target contract. Mechanical mark recognition and capture-stage review do not replace those semantics.

## Time semantics

Paper pipeline timestamps are workflow time:

- scan/retention time;
- interpretation time;
- proposal time;
- review time;
- operation time;
- receipt time.

They are not substitutes for unknown domain time. Materialization must preserve `unknown`/date-only/approximate/range semantics where the domain contract provides them rather than filling a required Event/evidence/Implementation/Follow-Up/etc. time from scan or review timestamps.

## Later review correction

Capture Review history is immutable. If a later review sequence reverses or corrects a decision after canonical materialization, the earlier Capture Materialization receipt remains historical fact. Any required domain correction uses the existing canonical correction/lifecycle/successor mechanisms. Portia does not delete the old receipt or silently rewrite the canonical record in place.

## Quarantine boundary

Ordinary materialization interruption belongs to Operation Journal recovery. Quarantine is reserved for exceptional integrity contradictions that cannot be safely reconciled, such as irreconcilable Page Record-to-target provenance, operation/write identity conflict, or duplicate materialization whose canonical identity cannot be safely determined.
