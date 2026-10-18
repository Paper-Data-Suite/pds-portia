# Portia #58 — Slice 5: verified PDS2 vector PDF rendering

Branch: `58-reusable-capture-forms-pds2-rendering`
Starting commit: `cc8cddbf0b010308f4a04dbb4fbb97d3a24c1f59`

## Scope

Implements `portia.capture.pdf_rendering.render_verified_capture_batch_pdf()`.
This consumes an actual `FileCapturePreparationService`, exact class and Capture
Batch identifiers, and a trusted `CaptureAuthorization`. It **never** accepts
caller-provided claimed-verification objects, QR contents, Page Targets,
student/lesson values, or template substitutions. It emits **PDF bytes and a
transient page/locator summary only**; it does not write output, issue a print
job, create behavior work, or claim someone scanned a page. File handling,
reprint policies, retention, and recovery follow in Slice 6.

## Authority and fail-closed steps

1. Require real preparation service, trusted `capture_form.render` class
   authorization through Portia's metadata gate, and an open Capture Batch.
2. Reload the current persisted Batch, Page Target v2 inventory, and Core route
   registrations using `FileCapturePreparationService.inspect`.
3. Require every page **verified** with distinct target IDs, distinct canonical
   PDS2 payloads, and consecutive logical page indices starting at 1.
4. Verify exact registered Core locator/target relationship; validate the
   active route inventory (including orphan and duplicate Core routes);
   resolve each exact frozen catalog identity and validate Page Target purpose,
   entry keys, existing-work references and current live context.
5. Require main Daily Observation plus zero to eight continuation pages, or
   non-Daily core forms. Mixing a Daily packet with other families is rejected
   rather than silently drawing the wrong page index or role.
6. Produce one US Letter 612 × 792 point page for every target, using the
   immutable Slice 3/4 drawing plans, bounded Helvetica glyphs and blank mark
   boxes. No domain facts or assumed class/student context appear in forms.
7. Paint a vector QR from the **canonical Core PDS2 payload**, with a white
   four-module quiet zone, at the exactly reserved 108-point square.
   Explicitly reject an overfull QR when module pitch falls below 1.55 PDF
   points. Print the same complete human fallback in one or two lines within
   the 400 × 20 point reserved label area; never truncate it.
8. Before returning bytes, reauthorize and reload all persisted authority,
   checking it against the initial snapshot. Fail if the Batch transitioned,
   target/registration changed, or an incomplete route appeared during render.

## Output, boundaries, and dependencies

`RenderedCapturePdf` returns `pdf_bytes`, SHA-256, `pages` with the exact target,
locator and template-identity snapshot, and renderer version. Every QR is drawn
as PDF vector rectangles using the Python `qrcode` matrix; ReportLab paints
all text/lines. There are no image-backed QR objects. ReportLab's invariant
PDF mode suppresses timestamp-driven nondeterminism, supporting safe
idempotency comparisons. A caller must still follow Slice 6 managed output
policy and must reauthorize on later reprints.

Portia declares `reportlab>=4.2,<5` and `qrcode>=7.4,<9`; strict mypy treats these
third-party packages as lacking bundled type markers. No Core internal route
persistence is forked or patched. Viewer aliasing in Core 0.6.6 is unrelated to
canonical PDS2 identity and is not used by this bytes-only implementation.

## Validation and next slices

The standalone isolated geometry/renderer check exercised all nine teacher form
families on a ten-page PDF, with no embedded raster objects; decoding the QR
from a high-resolution PDF raster restored the complete fixture locator. This
was **not** a Portia integration test and the fixture locator was synthetic.

The local gate runs changed-file Ruff, strict mypy, `compileall`, and focused
Portia tests, including real #57 preparation/route readback and the existing
#58 catalog/layout contracts. No complete-suite or printer/scanner qualification
is claimed. Slice 6 owns managed output, reprint auditability and recovery;
Slice 8 owns print/scan/device security and physical QR qualification.
