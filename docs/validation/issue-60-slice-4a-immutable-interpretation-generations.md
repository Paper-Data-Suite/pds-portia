# Portia #60 Slice 4A - Immutable Paper Interpretation Generations

## Scope and exact authority

Parent commit `d5257c18bc15e34467a6cf179bfd9cf1a7eb7fd8` is the passing and pushed Slice 3B baseline. This increment creates the first durable `paper_interpretation@1` records from **real** `FileLocalMarkCandidateService` / `FileManualTextCandidateService` operations. It does not authorize accepting source truth, interpreting student identity, creating Capture Proposals, reviewing or materializing a canonical record.

The entry point takes class, work and a persisted Page Record ID (not a file, QR candidate or caller-composed interpretation). `FileHistoricalPageRegionService.resolve` requires class authorization and revalidates Batch, Page Record, active route, Page Target, historical seven-element layout and Core retained source. Recognition output is then checked against the **entire** historical entry/field inventory and conservative state rules. Immediately before exclusive creation, the same facts are reverified while the existing Capture Batch lifecycle lock is held.

## Persistence

- Path: canonical Portia Capture Batch work subtree `records/paper_interpretation/pint_<40 lowercase hex>.json`.
- Identity: deterministic SHA-256 over exact Page Record ID and four-key versioned interpreter profile. No student ID, class, source filename, candidate literal or writable latest pointer appears in the filename.
- One immutable generation per exact Page Record plus interpreter profile. Existing profile + exactly equivalent candidates => `reused`; changed content under same profile => **conflict, no overwrite**. Changed profile => next monotonic per-receipt `generation` (not globally by Batch). Gaps/duplicates/unknown profiles and foreign/corrupt history fail shut.
- `PaperInterpretationV1` schema-backed construction, canonical JSON and bounded size, exclusive file create, exact readback; existing Core original and Page Record **remain unchanged**. No `processing_state=processed` claim is added.
- Locks are the existing Capture Batch operation lock; an interrupted/stale lock still requires deliberate recovery. There is no lock stealing or automatic deletion of previous interpretations.
- No paths, original scan pixels, registration images, full QR, or PDF bytes in record JSON.

## Conservatism and boundary

- Explicitly *unreadable* text remains unreadable. The only manual candidate is one source-faithful, operator-attributed text selection with separate `portia_local_assisted_marks/1` profile, not a silent edit of `portia_local_marks/1`.
- Mark tokens must belong to the exact historical choices; multiple alternatives remain unchosen; `unmarked` and `blank` do not become Boolean negative values. Only actual candidate entries contain `fields`; unreadable/blank entries retain their states without contradictory payload.
- The `interpretation_status` records mechanical coverage, not correctness, student attribution, semantic acceptance or a canonical writing permission. The page-local context remains context only.
- A second different manual selection with the same assisted profile is a **conflict**, because v1 does not yet support combining multiple same-profile corrections into a new immutable generation. Later teacher orchestration must explicitly version/profile the next correction; it must not force-overwrite this history.

## Validation

Guarded runner enforces clean exact branch/HEAD and origin tip, checks SHA-256 payloads and runs targeted Ruff, strict mypy and focused tests before staging exactly three additive paths, committing, and pushing. Synthetic tests use real #59 Page Record/Core source lifecycle with a substituted candidate classifier so persisted-contract behavior is independent of optional CV or real student handwriting. No full-suite rerun.

## Later #60 work

1. Extend interpretation coverage: field-level partial failures when measured registration is unavailable, a privacy-safe teacher fallback, and optional actually qualified text OCR/handwriting providers.
2. Build exact, reviewable `capture_proposal@1` mappings from committed interpretation generations without inventing target work, people or values.
3. Teacher multi-page workflow, restart/replay audit, security and real paper physical qualification, release guards.
