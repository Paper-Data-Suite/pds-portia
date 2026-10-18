# Issue #59 — Slice 5: exact Page Record receipts and replay safety

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`

**Base commit:** `9e30fba930d4af74f910318bca259839bfc5b37b`

**Scope:** persist `page_record@1` receipts for individually verified Core-retained pages; allow bounded idempotent resume and page-local exceptions. This is not OCR, evidence interpretation, review, a teacher menu, or canonical behavior-record creation.

## Ownership and persistence contracts

- **Core** retains the immutable whole PDF/image source and owns its SHA-256, `source_scan_id`, route registrations, locator, and dispatcher. Portia never copies raw source bytes into its Page Records.
- **Portia** persists one operational `PageRecordV1` under `records/capture_page_record/<prec_id>.json` within the verified Capture Batch. Source references use **only** Core `source_scan_id`, `source_sha256`, and physical one-based `source_page_number` as required by the accepted schema. The separate fields preserve the exact class, batch, target and route identities.
- Existing public `page_record@1` schema is unchanged. New receipts begin with `processing_state = received`. Neither `processed` nor any behavior-domain result is claimed at this stage.
- Receipt IDs are deterministic, opaque SHA-256-derived IDs over the retained *source scan ID and physical source-page number*. A different print route cannot fork a second receipt for the same physical source page under one batch. Same route on different accepted Core sources produces separate receipts. The printed Page Target `page_index`, historical `page_ordinal`, and physical `source_page_number` remain independent.
- All writes use Portia's preexisting protected Capture Batch work tree, path guard, shared lifecycle lock, canonical JSON, exclusive durable creation, and exact readback. **An existing receipt is never rewritten by re-intake.** Corrupt, contradictory, unexpected, or competing records produce conflict/attention instead of automatic deletion or repair.

## Authorization and commit boundary

`FilePageRecordService.record(SourceRouteOutcomes, authorization=trusted_gate)` first performs **a new complete Core dispatch verification** and retained-byte check. Each candidate that remains verified then requires class authorization again, acquires the owning batch's exclusive lifecycle lock, reloads the batch and exact Page Target/registration via Slice 4, rechecks retained custody, and finally creates or reads its Page Record. A cancelled batch, changed/retired route, lost authorization, or mismatched historical template cannot silently create a receipt.

Within a multi-page document the accepted effects are **page-local**. Pages with missing/invalid/ambiguous QR remain `needs_attention`; a transient write failure returns `retryable` for that page; corrupt persisted state returns `conflict`. Retrying the *same retained source* can reuse already accepted records and create missing ones without overwriting history. Existing `failed` or `processing` receipt states are preserved, **not** reset to `received`.

The accepted per-page statuses are: `created`, `reused`, `needs_attention`, `retryable`, `conflict`. `SourceReceiptOutcomes.completed_with_exceptions` is truthful whenever one or more pages lack an accepted receipt. Routine status codes contain no student names, raw PDF/QR bytes, or narrative text.

## Recovery and limitations

- If a crashed or interrupted `exclusive_create` leaves a partial Page Record, the next attempt sees corrupt state, fails closed, and requires explicit recovery. Do not delete a possibly authoritative file or automatically clear a batch lock.
- Core retention is not rolled back because a later page failed, a route was retired, a class was denied, or the teacher deferred processing.
- A single-process batch lifecycle lock serializes ordinary Portia writers. Filesystem replacement races and cross-machine OneDrive concurrent writers require final adversarial qualification; this slice does not claim a distributed transaction or linearizable remote filesystem lock.
- The durable receipt marks arrival/routing only. A later #60 Paper Interpretation, #61 human Review, and #62 accepted materialization own their separate historical lifecycle and policy checks.
- No broad repository suite, wheel build, or physical teacher scan is required for this slice. The runner performs Ruff autofix/format, strict mypy for changed production files, and one focused Slice 1–5 pytest invocation. Final official Core-version/wheel/sdist/Windows/Ubuntu qualification belongs to the release candidate.

## Synthetic test matrix

- Exact same-source replay returns `reused` and preserves existing JSON and retained Core bytes.
- Three-source-page PDF with missing QR and injected third-page write failure: first accepted, second unresolved, third retryable. Replay reuses the first and creates the third, retaining original 1-based page provenance.
- Permission revocation, cancelled batch, existing operation lock, and historical state mismatch fail without overwriting receipts or Core originals.
- Invalid persisted JSON and contradictory source/route are not auto-repaired.
- Distinct Core source identities with the same printed route produce distinct Page Records.
- Existing `failed` receipt remains unchanged; no Event, Observation, Communication or behavioral assessment is created during intake.
