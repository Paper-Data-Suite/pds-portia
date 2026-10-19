# Portia #60 — Slice 6A: Stage one previously received source

**Baseline:** `ec478ca0a325ba51085a0ea119c314fa790cc663` (Slice 5B, immutable proposals).

This additive service implements a source-wide **staging action**, not a new intake, scan, receipt, review, or materialization. It receives a `TeacherSourceResult` from the existing #59 workflow, uses one independently verified Page Record per accepted physical page, and reads only Core-retained originals. Each page may belong to a different class and Capture Batch; authorization is checked per page.

## Targeting and ordering

- `TeacherPageResult.work_id` is added as an **optional** locator, populated from the existing verified route. This is backward-compatible for callers constructing older result instances. `work_id`, like `class_id` and `receipt_id`, is not treated as authority; the protected Page Record/Core/route reader verifies all facts before access/writes. A previously constructed result with no work ID receives a bounded Needs Attention outcome rather than a guessed batch.
- Preserve original source-page order. An unaccepted/failed QR page is not staged, but does not block later pages in the same PDF. A duplicate receipt in a result is flagged instead of processed twice.
- Read immutable Page Record-scoped history first. If a prior generation exists, use its **latest preserved version**, including attributed manual-assisted candidates; do not erase manual work by regenerating a marks-only snapshot. If none exists, perform local checkbox staging; never claim unsupported OCR or text recognition.
- Recheck source/route after selection. Hand the exact saved interpretation ID and generation to Slice 5B, which independently reauthorizes and validates the proposal plan inside the batch lock.
- Reuse saved interpretations/proposals on retry, without creating new Core retention or Page Records. If registration is not measurable, state Needs Attention/retryability; do not guess pixel positions, text, handwriting, or negative facts.

## Result boundaries

`TeacherStagingSummary.summary()` reports only source physical page numbers, bounded status reasons, selected generation numbers, counts, and review-required indicators. No filename, path, source narrative, person identity, raw QR, actor details, transcribed text, or mark alternatives are returned. A proposal created from a **partial** interpretation remains Needs Attention and still requires #61 attributable Capture Review. A complete interpretation is *also not a review*.

No `capture_review@1`, `capture_materialization@1`, Event, Observation, or other canonical record can be created in this slice. The existing returned-paper menu does not yet invoke this service: **Slice 6B wires explicit opt-in staging to that menu**, while preserving existing intake choices and prompting for confirmation before writing interpretation/proposal records.

## Focused qualification

Synthetic retained-PNG receipt setup tests: fresh interpretation, restart-safe no-rescan replay, later assisted Event interpretation and proposal replay, denial before protected read, unaccepted page isolation, wrong work locator, missing old-style work locator; plus Slice 5B proposal and Slice 4A generation regression tests. No actual classroom/student scans are required or bundled.

**Operational limitation:** the Slice 2B alignment provider currently requires independently measurable contrast at the printed sheet boundary. Full-frame white office scans may report registration unavailable. This limitation must be addressed/verified with real scanner characteristics prior to declaring #60 universally usable; no speculative fallback is authorized.
