# Issue #59 — Slice 2: PDF/image preflight and actual Core retain-first custody

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`
**Required baseline:** `baed62d341162b0a1a3a0523baee10e512477f23` (Slice 1).
**Scope:** one selected whole PDF/JPEG/PNG file; validation before Core custody and exact original-byte verification afterward. No QR detection, page dispatch, Page Records, OCR, student identity, or behavior-domain writes.

## Public implementation

`FileRetainFirstIntakeService(root, limits=SourceSafetyLimits(...))` provides:

- `preflight(path) -> SourcePreflight` — strictly **read-only**. Verifies ordinary source filename, extension + signature, file size, safe non-link path ancestry (including Windows reparse points), content structure, source hash, and stable file metadata. A PDF is parsed with `pypdf` in strict mode for encryption, number of pages, valid MediaBox geometry and projected maximum pixel area. JPEG/PNG are decoded through the image backend used by the existing ReportLab renderer; grayscale is valid. No DPI is inferred from a mobile JPEG.
- `admit_and_retain(path) -> RetainedIntakeSource` — calls official `pds_core.scan_retention.retain_source_scan` **once** on the selected whole file after preflight; checks Core's returned SHA-256 against the source preflight and independent full retained-byte readback/size; validates Core retained-path relative identity and denies link/reparse ancestors. It never writes scan bytes in Portia's own storage or removes Core-retained history when verification fails.
- `RetainedIntakeSource.page_identity(source_page_number)` — derives one-based physical page provenance for later Page Records; a 10-page PDF remains **one original retained source** with independently addressable pages. It cannot substitute printed page ordinals or form labels.

## Fail-closed / environmental policy

The service uses Core as the **only source custody authority**. Preflight and retained-byte verification are application-level bounds; they do **not** replace Core's exclusive source-writer or create a Portia source-store alternative.

- Supported inputs: PDF (one or many pages), JPEG/JPG and PNG. Unsupported TIFF, encrypted PDFs, invalid PDFs/images, missing/truncated files, path traversal, symlinks/junctions, too-large pages/files, and detected mid-preflight changes must not be treated as successful intake.
- Default source ceiling: 128 MiB; maximum 96 pages; maximum projected 24 million pixels per PDF page at 200 DPI or 24 million actual image pixels. These are **preflight and safety limits**, not a rasterizer or hard CPU/runtime sandbox. `pypdf` itself does not render PDF pixels. In Slice 3, the PDF rasterizer and QR decoder must enforce separate per-page resource and execution bounds and classify decoder failures without discarding the retained original.
- Scan input can be outside the PDS workspace (scanner folder or Downloads). Only the retained result must be inside the Core workspace. **No source file is moved or deleted.** Disallow a source path containing symlink/junction components, including an ancestor.
- A Core exception, post-retention hash mismatch, or missing retained file causes a typed, privacy-minimized failure; it does **not** attempt cleanup of a source that Core already accepted. The caller must not describe a partial/error result as fully ingested.
- Core's writer validates the file twice and copies through an exclusive target. Source-path swapping/TOCTOU remains a shared boundary requiring stronger Core API contracts if an adversary can mutate scanner folders concurrently; exact preflight/Core SHA matching and retained readback prevent silently processing mismatched bytes.
- Before class metadata reads or Page Record writing, Slice 4 must apply `CaptureAuthorization`. This stage has **no class context and no power to infer class ownership** from filename, page content, or a presumed student.
- This service is a typed library boundary, not yet a visible `Portia → Scan / Import Returned Paper` menu feature. Slice 6 will expose that workflow.

## Focused acceptance

`tests/test_issue59_slice2_retention.py` covers a **single ten-page PDF** with exact preserved source bytes and ten distinguishable source page positions, actual PNG/JPEG image decode including grayscale, source hash checks, encrypted/invalid PDFs, corrupt/mismatched images, source-page/file-size/pixel ceilings, path links and traversal, detected original mutation, injection of Core failure, retained-copy tampering without deletion, and a true installed-Core retained-source smoke test. All data are synthetic; no printed sheets or student records are needed.

The one focused pytest command includes Slice 1 contracts and Slice 2 regression tests. Ruff and strict mypy validate the modified production package. No full repository tests or wheel packaging are repeated in this slice. Report precise counts/results from the actual local run, not synthetic-harness counts, when documenting qualification.
