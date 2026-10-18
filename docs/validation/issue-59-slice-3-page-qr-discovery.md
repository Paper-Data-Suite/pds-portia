# Issue #59 — Slice 3: retained-page rasterization and unverified QR discovery

**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`
**Baseline:** `910a4a4af1c37f1b7b107dba686beb5ecdda4abf`
**Disposition:** Per-page discovery only; **no page routing, class authorization, Page Record persistence, or domain materialization**.

## Service

`FilePageQrDiscoveryService(workspace, limits=...).discover(retained: RetainedIntakeSource)` accepts **only** the typed result of Core's retain-first Slice 2 service. It rechecks retained-file path containment, absence of symlink/junction components, size and exact SHA-256 **before and after** processing. Only the Core-retained original is opened. Nothing is written by discovery.

Each PDF page is rendered in-memory, one at a time, by PyMuPDF at the bounded `SourceSafetyLimits.raster_dpi` (default 200 DPI). Before raster allocation, effective page dimensions are checked against the policy pixel cap; the rendering result is checked again. JPEG/PNG are decoded to grayscale in-memory using the existing Pillow dependency. OpenCV finds/decode QR candidates independently per page; no image output or QR string is stored. Long OneDrive paths use filesystem APIs directly, never viewer-only alias paths.

Output is `SourceQrDiscovery` with **exactly one** `PageQrDiscovery` per one-based physical input page. `candidate_unverified` includes a Core-parsed, canonical PDS2 `RouteLocator` for module `portia`. It **does not mean** the route registration, class/work ownership, Page Target, authorization or active status has been validated. Those checks belong to Slice 4. All other statuses (`missing_qr`, `unreadable_qr`, `invalid_qr`, `ambiguous_qr`, `foreign_module`, `render_failed`) deliberately provide **no candidate locator**, preventing first-match-wins and foreign-module Portia routing.

One rejected or unrenderable page has an individual exception status, without hiding subsequent page outcomes. A changed Core-retained file causes overall discovery to fail closed: prior candidates must not be treated as usable.

## Runtime provider decision

PyMuPDF (`pymupdf>=1.26,<2`) handles PDF rasterization; `opencv-python-headless>=4.10,<6` handles QR codes; `numpy>=2,<3` supplies bounded grayscale arrays. These are declared as the `scan` **optional extra** in the package metadata for incremental implementation; this slice's runner installs the extra in the development `.venv`. Production release/installed-wheel qualification and making scan intake available by default belong to #59 Slice 7/8. Missing scan providers are explicit errors, not false `missing_qr` statuses.

PyMuPDF is required because existing `pypdf` validates PDF structure but does not render scanner pages. No poppler executable, OCR engine, external service, native temporary-image file or replacement Core source storage is used. Test wheel portability with Windows x64 (including Windows-on-ARM x64 Python) and Ubuntu before release.

## Synthetic, focused test boundaries

Tests use reportlab, QR generation and actual raster/decode backends to qualify a ten-page synthetic PDF: six differently ordered Portia PDS2 codes, one blank page, one foreign-module code, one invalid code and a page carrying two codes. Separate JPEG and PNG QR scans, post-retention tampering, injected page failure, small raster budgets and backend-unavailable paths are exercised. All source bytes are synthetic and remain outside version control; no printing/manual scanning is requested.

**Remaining work:** Slice 4 exact Core registration/profile dispatch and authorization; Slice 5 Page Records/idempotency; Slice 6 teacher menu; Slices 7–8 security, portability and distribution qualification. Do not report these as implemented by Slice 3.
