# Portia #58 — Slice 6: Immutable Managed Capture PDF Generation

## Starting identity and authority

- Branch: `58-reusable-capture-forms-pds2-rendering`
- Required parent: `63b303bbe0815225c3d0df7e197f5279077e4982` (Slice 5)
- Authority: #58 §§4, 6–8; #57 verified Capture Batch / Page Target / Core route; Core PDS2.
- Dependencies: `reportlab`, `qrcode` from Slice 5 and `pypdf>=5,<7` from this slice.

## Frozen output policy

`FileCapturePdfArtifactService(FileCapturePreparationService)` is a typed,
non-domain, teacher-local service with `generate`, `inspect`, and explicit
`recover`. Only an existing *open*, fully verified Capture Batch can generate a
PDF. Authorization is separately enforced for `capture_form.generate`,
`capture_form.inspect`, and `capture_form.recover` and by the verified renderer
(`capture_form.render`). No caller supplies a route string or an output filename.

The unique managed output for one Capture Batch is:

`<workspace>/portia/capture_forms/<class_id>/<cbat_id>/capture-packet.pdf`

with immutable sidecar `capture-packet.receipt.json`. IDs are validated by the
existing Core work-ref authority and the existing Portia safe path guard. The
PDF and sidecar are separately staged adjacent to the destinations, read back,
and published only with an **exclusive atomic hardlink** (same filesystem). On
filesystems where exclusive hardlink publication is unavailable, generation
fails closed; it does not fall back to overwrite/partial ordinary file writes.
Partial publication is honestly observable: the PDF can exist without a receipt
if publication was interrupted. Neither file is treated as a complete managed
result until both pass exact verification.

The receipt records `receipt_version`, owner, batch ID, renderer version, PDF
SHA-256, PDF byte count, ordered Page Targets, full frozen template identities,
canonical Core PDS2 payloads, and `pdf_ready_not_printed`. It is **not** a
printer acknowledgement, retained returned page, captured observation, Event,
communication, implementation, or other domain evidence.

A complete byte-identical repeat reuses the same two files, without route
mutation or new Page Targets. A second physical *paper copy* of the same PDF is
permitted and may later return as its own distinct retained source in #59; a
route is not a unique physical paper identity. A materially different form,
context or session requires a **new Capture Batch and independently prepared
Page Targets/routes**; the same batch cannot silently replace its published
artifact. No successful-looking overwrite, latest-version substitution or
regeneration of diverged files is permitted.

## Failure, recovery, locks, and preview

A capture-artifact operation uses a dedicated exclusive lock under the safe
managed output directory and the existing Portia Batch lifecycle lock. This
prevents an ordinary Batch-close or route registration between the renderer's
final state check and durable output installation. Lock bytes are removed only
with exact expected-fingerprint proof. Crash-surviving locks or unexpected
stage files are **never** age-expired, recursively deleted or auto-adopted:
inspect them before explicit recovery. Ordinary failures remove only the exact
staging candidate they created; if proof fails, the candidate remains.

If just one of PDF/receipt exists, `generate` stops with recovery required.
`recover` is an explicit, authorized action that re-renders from the *same
persisted open Batch/targets/routes*, requires the surviving component's bytes
to match exactly, and exclusively publishes the missing component. Contradictory
bytes, orphan routes, changed template identity, terminal batches, external
symlinks/junctions, partial route inventory or concurrently held locks fail
closed. No canonical Page Targets/routes/history are deleted or rewritten.

`inspect` is read-only and checks the current open authority and both immutable
artifacts. It neither creates output nor requests a viewer or claims a printed
page. Slice 7 will connect a verified result to Core's `open_local_path()`;
Windows viewer alias paths remain ephemeral, never persisted in the receipt.

## PDF validation

The public renderer already checks route/readback and QR module geometry.
Before storage, `pypdf` strictly parses the PDF and checks document count,
US Letter geometry, extracted **complete per-page** canonical PDS2 fallback,
and absence of image XObjects. The renderer's SHA-256 must match actual PDF
bytes. The same checks and byte identity are enforced on managed inspection.
The validation does not claim optical scanner qualification (Slice 8).

## Tests and acceptance

`tests/test_issue58_slice6_managed_pdf.py` covers real-service generation,
receipt and digest, deterministic reprint, interrupted PDF/receipt recovery,
contradictory persisted bytes, terminal Batch rejection, class denial, unsafe
output symlinks, interrupted locks, failure before exclusive link publication,
missing route and absence of domain or print-completion claims.

The focused gate runs changed-file `ruff check --fix` and `ruff format` **once
before validation**, then `ruff check`, strict mypy, compileall, and one pytest
pass of Slice 6 + affected Slices 2–5 and #57 preparation tests. The guarded
script automatically commits and pushes only if all checks pass. Full-suite,
wheel/physical and Windows/Ubuntu platform qualification remain Slice 8–9.
