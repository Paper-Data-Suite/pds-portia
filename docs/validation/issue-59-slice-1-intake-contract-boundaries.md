# Issue #59 — Slice 1: Core custody, PDF/image intake and Page Record contract boundaries

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`
**Base:** `9202ca382cafc25848fea0a790e3b39dc13d2f17` (post-#58 main)
**Scope:** typed, pure intake admission and retained-page provenance. **No file ingestion, QR decoding, Page Record writes, or menu integration in this slice.**

## Audited installed/public interfaces

| Owner | Existing contract | Required use in later slices |
| --- | --- | --- |
| Core | `pds_core.scan_retention.retain_source_scan(root, source_file_path)` -> `RetainedSourceScan` | Copies **whole original** PDF/JPEG/PNG bytes to Core's retained-source store, SHA-256-checks the copy, assigns `source_scan_id`, records intake time and relative path. This is **the only** accepted source writer. |
| Core | `pds_core.scan_routes`: retained-store paths/extensions | Core supports `.pdf`, `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`. **Portia #59 v1** deliberately supports PDF/JPEG/PNG only; TIFF is explicitly unsupported until qualified. |
| Core | `pds_core.pds2.parse_pds2_payload` | Parse the complete untrusted QR locator after page decoding. No guess by form name or adjacency. |
| Core | `pds_core.module_dispatch.RouteDispatchRequest`, `dispatch_route`, `dispatch_routes`; `ModuleProfile`, `ModuleRegistry` | Dispatch *Core-retained*, one-based physical page references. Core does **not** rasterize PDF, decode QR, validate Portia Page Target contents, or authorize Portia's class records. |
| Portia | `capture_page_record` (`page_record@1`); `PageRecordV1`; `schemas/v1/capture/page-record.schema.json` | Source ref has exactly `source_scan_id`, `source_sha256`, `source_page_number`; Page Record separately identifies `class_id`, operational `work_id`, `page_target_id`, `route_id`. Exact target and route must be read back before persistence. |
| Portia | `CaptureAuthorization`, `FileCaptureBatchService`, `FilePageTargetService`, `route_binding_findings` | Require trusted authorization **before** protected route/target reads; revalidate historical target (`page_target@1` or `@2`) and exact registered identity rather than printed labels. |
| Portia #58 | versioned form/catalog specs, registered QR payload and immutable PDF | Only for *historical layout identity* used after routing. Printing is not returning/scanning or source custody. |

Direct sources: [Core scan retention](https://github.com/Paper-Data-Suite/pds-core/blob/main/pds_core/scan_retention.py), [Core page dispatch](https://github.com/Paper-Data-Suite/pds-core/blob/main/pds_core/module_dispatch.py), [Core installed module profiles](https://github.com/Paper-Data-Suite/pds-core/blob/main/pds_core/module_profiles.py), [Portia Page Record schema](https://github.com/Paper-Data-Suite/pds-portia/blob/main/schemas/v1/capture/page-record.schema.json), ADR 0016 and ADR 0021. **Inspection of repository source is not yet an installed-wheel compatibility pass**; verify Core v0.6.6 and advertised historical versions in later gates.

## New pure APIs (Slice 1)

`portia.intake.assess_source_signature(filename, byte_count, first_bytes, limits=...)` checks only a basename, reported byte count and **at most 1,024 prefix bytes**. The deterministic result can be a **candidate_unverified** or a specific rejection. It does not open the file, use OCR, decode a QR, create a Capture Batch, retain bytes, or claim that a PDF is structurally valid. It is deliberately usable by the later preflight in #59 Slice 2 before invoking Core custody.

- Supported: PDF, JPEG/JPG, PNG. Explicit unsupported TIFF/TIFF-multipage and all other extensions. Filename extension alone never wins over a mismatched signature.
- Default upper bounds: 128 MiB per submitted file, 96 pages, 24 million decoded pixels per page, 200-DPI target rasterization; hard ceilings: 256 MiB / 128 pages / 32 million pixels / 300-DPI rendering. **These limits are policy inputs only**: they are not enforced on PDF page structure or decoded images until Slices 2–3.
- PNG IHDR dimensions can be rejected from the header as a preliminary guard. JPEG dimensions, PDF encryption/page count, decompression risks, orientation, and complete image validity require a real bounded parser/decoder later. A synthetic header passing is **not** proof of a usable scan.
- `RetainedPageIdentity.from_core(RetainedSourceScan, one_based_number)` builds immutable source-page identity **only from Core's retained-source result**. `.page_record_source_ref()` exposes precisely the existing Page Record source-reference fields without persisting anything. It never replaces source identity with a printed route or assumes that ten scanned pages must arrive in template order.
- No class roster, source narrative, scan bytes, physical paths, or QR payloads are embedded in the admission result or page reference.

## Mandatory design decisions before side-effectful implementation

1. **Retain-first:** once a bounded parser has rejected obviously unsafe sources, call Core retention on the whole input file and verify exact SHA-256/retained readback. Process pages from the **retained copy**, never from a mutable original after retention. Preserve custody after interpretation, authorization, or route errors.
2. **Source safety:** Core `retain_source_scan` alone is **not** a complete symlink/junction/TOCTOU-aware scanner preflight. Check path/ownership and source-size limits, then recheck retained state. Escalate any irreducible race/gap into an additive Core contract instead of duplicating or deleting Core-owned source files.
3. **PDF decoding:** `pypdf` is installed for PDF reading but **does not rasterize pages**. Slice 3 must select and qualify a bounded rasterization library on Windows x64-on-ARM and Ubuntu; verify source page count, encryption, pixel limits, and per-page failure isolation before allocating large raster buffers. Do not make the teacher split PDF files.
4. **QR:** OpenCV was used in the #58 physical *qualification* environment, not as an already-proven installed runtime dependency. Slice 3 must choose a stable decoding provider, justify native/wheel portability, and classify missing/ambiguous/foreign codes without guessing.
5. **Dispatch:** Core `dispatch_route` requires a `ModuleRegistry`/`ModuleProfile` and a `RouteLocator`; Portia currently does not advertise a paper `paper_data_suite.modules` handler. Slice 4 must expose a **Portia-owned handler/profile** with correct authorization and exact Page Target validation, not overwrite `paper_data_suite.module_operations` and not claim generic Suite dispatch here.
6. **Page Record:** the accepted `page_record@1` schema uses Core `source_scan_id`/digest/**source_page_number** plus exact route/target identifiers. It does *not* store Core path, original PDF/image bytes, OCR text, student identity, or form-entry interpretations. Slice 5 must add durability/idempotency only after route authorization. Distinct retained sources using the same printed route are distinct; a replay of the same retained source page and route is idempotent.
7. **Teacher ergonomics:** one multi-page PDF selected once; each page numbered and reported separately; partial completion is truthful; unresolved pages remain under exact Core custody. The full teacher menu belongs to Slice 6.

## Tests and security expectations for Slice 1

Focused pytest exercises typed policy ceilings, magic-byte versus extension mismatch, unsupported TIFF, empty/truncated headers, PNG dimension bombs, oversized files, unsafe basename inputs, unchanged physical-source provenance, one-based page identity, and a deliberate no-I/O contract. `ruff` and `mypy` apply to new code. No full repository suite, wheel build, or physical rescans at this slice.

**Slice 1 disposition:** Read-only, non-domain foundation. **It is not PDF ingestion and must not be presented to teachers as intake readiness.**
