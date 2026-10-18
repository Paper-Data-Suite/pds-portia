# Issue #59 — Slice 7: Core retained-source restart recovery and adversarial checks

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`
**Exact parent:** `2ad0e5b7556260ff81064212ab12644f1eacdab0`
**Scope:** read-only restart recovery of original Core-retained PDF/JPEG/PNG files, teacher menu integration, negative-path tests, and official Core 0.6.6 CI qualification.

## Teacher recovery after restart

`Portia -> Scan / Import Returned Paper -> Resume a previously Core-retained scan` lists a bounded set of recent Core-managed source files and processes the selected source with `TeacherReturnedPaperService.resume_retained`, **not** `admit_and_retain`. A second intake event is neither necessary nor permitted by the recovery path. Previously accepted Page Records are reused under the existing Slice 5 same-source/page identity.

A Core-retained file is not automatically a verified page. The recovery service enumerates candidates only from Core's public `pds_core.scan_routes.scans_source_dir` layout, checks its Core-generated filename/date-bucket shape, and never reads class-specific content while listing. Before any QR discovery, selected candidates are revalidated with Slice 2 `preflight` and exact full-file SHA-256 readback, a match of the Core-retained filename's digest prefix, ordinary path symlink/junction guards, and strict page/pixel bounds. Core's original is not modified or deleted.

The original pre-retention filename **cannot always be reconstructed** from Core's sanitized retained filename, because Core does not expose a list/readback API or sidecar retaining it. A reconstructed `RetainedSourceScan.source_filename` therefore identifies its actual retained leaf, **not** an invented original basename. Source-page numbers, the full original-file SHA-256 as observed during recovery, and the exact Core retention identifier are preserved. The teacher list intentionally shows only format and Core retention time (UTC), not QR payloads, rosters, or narrative text.

A candidate's presence is not an authorization grant. Once a page's QR is decoded, Slice 4 must still authorize the class **before** loading protected routes/Page Targets, and Slice 5 reauthorizes inside the operation lock before receipt creation. Non-Portia pages remain unresolved rather than being coerced to Portia.

## Scope and residual risks

- Bounded maximum: 8,192 inventory entries walked, at most 64 returned candidates (24 by default). Unexpected filenames and TIFF are excluded; Core v0.6.3 has no public retained-filename length constant, so the adapter uses its own 255-character leaf guard and the existing Page Record source-ID bound for historical compatibility. Link-like inventory components fail closed instead of being traversed.
- Reject changed/malformed, encrypted, oversized, mismatched-digest or directory-escaping candidates. No silent repair, lock clearing, raw-source deletion, student assertion or domain materialization.
- Recovery deliberately enumerates Core's shared raw source store, including other PDS modules. A foreign-module QR is a delegation/Needs Attention result, never a Portia Page Record.
- **Known Core limitation:** `retain_source_scan` has no read-only `load_retained_source_scan`/enumeration API or signed original-source metadata. This service reconstructs type-safe runtime provenance from Core's published store topology and checks, but cannot cryptographically prove original-file identity against a malicious actor able to replace retained content **and** forge a matching filename digest prefix. File-system races after verification are also not eliminated by a path-based reader. A future additive Core sidecar/read API with durable full-file digest and file-descriptor-based safe opens would close those gaps. Do not claim a stronger guarantee.
- Preview/printing or scanning hardware acceptance beyond the previously accepted #58 pilot is not implied.

## Qualification

Focused Slice 7 tests cover restart reconstruction of actual Core-retained 3-page PDFs, JPEG/PNG, matched physical-page identities, unsigned/corrupted candidate rejection, untrusted path and link rejection, inventory bounds, no writes during listing, and teacher menu recovery that never calls Core retention a second time.

The runner executes Ruff autofix/format once, checks strict mypy for changed runtime modules, then **one focused pytest invocation for Slices 1–7**. It stages and commits only after all checks pass. CI's existing installed-official-Core-0.6.6 Windows/Ubuntu job gains the same Issue #59 focused tests. The existing CI qualification job covers the repo's promised historical Core versions; no duplicate full local repository gate is performed for this slice.

**Not in this slice:** OCR/OMR, manual route invention, canonical behavior materialization, additive Core API changes, final release wheel/sdist or full Issue #59 closing matrix (Slice 8).
