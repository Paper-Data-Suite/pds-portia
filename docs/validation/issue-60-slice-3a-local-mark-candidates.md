# Issue #60, Slice 3A: local choice-mark candidates (no handwriting OCR)

## Exact authority and implementation boundary

Slice 2B commit `15c9d2d4821d19c86c04e7826b4ad71cb3d91317` is the baseline.
`FileLocalMarkCandidateService.interpret(...)` is the **only production service**:
it resolves a durable Page Record and historical layout with class authorization,
uses `FileMeasuredRegionService.extract` to obtain independently measured
QR- and sheet-aligned crops of the original Core-retained page, then rechecks
provenance, permission and the source/route/target/receipt snapshot before
returning **ephemeral, noncanonical** candidates. The exported pure helper
`interpret_registered_fields` is for deterministic provider characterization;
**caller-composed crops are never accepted as authorized paper**.

The original `portia_local_candidates/1` profile is unchanged in capability.
A new *exact*, local-only `portia_local_marks/1` interpreter identity
selects `local_checkbox_v1` and the existing exact mapping-profile version.
No `latest` alias, network service, sibling-module runtime, or implicit OCR.

## Mark capability and conservative limits

- Uses each form's **historically declared** choice field and exact frozen
  printed 8-point checkbox positions, not ScoreForm-style answer bubbles.
- Each check requires sufficient pixel density, a separately measurable dark
  checkbox frame on all four sides, and ink in the center excluding its frame.
- One clear checkbox yields `candidate_detected` with the literal **printed
  choice token**; two or more clear marks yield `ambiguous` with each printed
  token as a distinct alternative. No first/strongest choice selection.
- A confirmed clean interior in every visible checkbox yields `unmarked` (not
  `no`, `false`, nonparticipation, or a business judgment).
- Faint or borderline interior ink, insufficient crop resolution, missing or
  damaged checkbox frames, and competing weak marks yield `unreadable` and
  `mark_quality_insufficient`. Nothing becomes a guessed blank or a chosen
  mark merely because one checkbox appears stronger.
- All declared text/handwriting fields are **unreadable** and add
  `text_provider_unavailable`. This includes white-looking text regions;
  absence of OCR output is not evidence of no handwriting.
- Page-local entries are enumerated for all ten supported layouts. A
  `candidate` entry has a complete set of field states; `blank` and
  `unreadable` entries omit the field map in v1 wire representation.
- Confidence/normalization are *not* emitted by the uncalibrated provider.
  A candidate literal is source staging, **not a quotation or verified fact**.

## Scope and limitations

A partially readable page can return useful marks but is still partial when
handwriting is unsupported. The result is **not yet persisted** as a
`paper_interpretation@1` generation. This increment does not construct
`capture_proposal@1`, update Page Record processing state, prompt for manual
transcription, create a Capture Review, or materialize canonical records.

The measured-page provider currently requires a contrasting border and
corroborating exact QR; full-frame white scanner pages remain unsupported.
Synthetic local marks qualify the classifier only; printed/scanned acceptance,
low-quality real scanner characterization, privacy and performance tests,
manual fallback, and broader detection remain #60 acceptance requirements.

## Qualification gate

- Exact current branch and Slice 2B HEAD plus remote branch/main authority.
- Git blob preimage guard on `interpretation_profiles.py`, narrow deterministic
  patch, and SHA-256 validation for the entire delivered payload.
- Ruff check/fix/format, strict mypy for both production modules.
- One focused pytest run covering Slice 3A, Slice 2B and the historical profile
  registry; automatic scoped commit/push only if all gates pass.
