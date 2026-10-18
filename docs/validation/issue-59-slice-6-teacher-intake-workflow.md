# Issue #59 - Slice 6: teacher-facing returned-paper intake

Branch: `59-core-retain-first-pdf-scan-intake-page-records`
Baseline: `fd12efc7d8ec79ad70d7c2f8e87fce564246c08a`

## Reachable teacher task

From the Portia main menu choose **11. Scan / Import Returned Paper**. Select one PDF, JPEG, or PNG by its exact filesystem path, including a file already saved by a scanner in its inbox. A multi-page PDF is submitted **once**; teachers never have to split, rename, or manually route its pages. Preview shows original filename, format and structural page count. The explicit **RETAIN** confirmation occurs before Core custody and Page Record writes. B/M/Q preserve the existing menu navigation.

The orchestration is `TeacherReturnedPaperService.inspect` (read only), `process_file` (Core retain first, QR discovery, Core route dispatch, Page Records) and `resume_retained` (retry the same Core retained source identity). The menu remembers the last `RetainedIntakeSource` only **within the process/session**. It is discarded when the workspace changes. Durable cross-session recovery/indexing is deferred to Slice 7; do not claim a new independent scan is an idempotent retry.

## Status and privacy boundaries

- For each original physical source page, report a **Recorded**, **Already recorded**, **Needs attention**, **Retryable**, or **Conflict** outcome, retaining original one-based source-page position.
- Explicit summary distinguishes **Completed**, **Completed with exceptions**, and **Retained - needs attention**. A saved receipt is not an accepted classroom observation or behavior fact.
- Page-detail view shows exact verified class and historical template name/index/ordinal where available; never presents decoded QR payloads, handwriting, roster names, scan bytes, or unverified class guesses.
- Missing/invalid/foreign QR, inactive or unknown registration, denied authorization, missing targets and interrupted writes have teacher-language follow-up labels. A source-level interruption produces one retryable position for every source page; existing receipts must be inspected and reused on retry.
- Repeating `process_file` on the **original file** constitutes another Core retention intake event, not reuse of the prior source. The menu's **Retry last retained source** uses `resume_retained`, rechecks original custody and yields idempotent Page Records for already accepted pages.
- An interrupted or tampered retained source is **not** described as fully completed. The workflow never deletes Core source custody, clears ambiguous locks, alters Core routes, or constructs domain records.

## Scope and validation

This slice adds typed service orchestration and main-menu integration. It does not implement OCR/OMR, behavior assertions, interpretation, form generation, Suite-wide mixed-module dispatch or per-page manual route override. It preserves existing primary task numbering and Capture Forms at option 10.

Focused checks cover one-file orchestration, page-level count/ordering, source-level interruption, session-local retained-source replay, explicit confirmation before writes, privacy-minimized details, and main-menu discoverability. Windows integration against installed official Core remains authoritative. Full repository/wheel compatibility and cross-session scan recovery are held for Slice 7/8 final qualification.
