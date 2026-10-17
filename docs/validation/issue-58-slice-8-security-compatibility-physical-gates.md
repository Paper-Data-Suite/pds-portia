# Issue #58 — Slice 8: Security, Compatibility, Physical Qualification

**Branch:** `58-reusable-capture-forms-pds2-rendering`
**Starting commit:** `e32746e8bd52ffc1e3a4f97ec7ff20705771903a`
**Status:** Automated gates pending Windows execution; **physical qualification OPEN**.

## Automated scope

`tests/test_issue58_slice8_security_compat.py` adds cross-layer synthetic tests for:

- Exact active Core-route readback and independently routable Daily continuations.
- PDF/receipt tampering, immutable artifact refusal and evidence-preserving stale locks.
- Deep OneDrive-like paths; no temporary viewer alias in stored route provenance.
- Read-only preview only after managed artifact verification; missing Core viewer API
  fails clearly without preventing menu startup or ordinary PDF generation.
- Exact class authorization and false-claim prevention.
- Direct symlink guard on Unix and **unprivileged Windows Junction** guard on Windows.
  This specifically replaces reliance on the environment-skipped symlink path.
- Frozen ten-layout, nine-form catalog identity lookup.

These tests are additional, focused security probes. Earlier Slice 2–7 focused
and regression suites remain authoritative for the core feature implementation.

## Synthetic physical print fixture generator

From the Portia source checkout with the active development virtualenv:

```powershell
$destination = Join-Path $HOME 'Downloads\portia58-physical-qualification-01'
python scripts/qualify_issue58_physical_samples.py `
    --output $destination --confirm-synthetic
```

`--output` **must be a new folder** outside the repository or production PDS
workspace. The generator makes its own synthetic Core class, Capture Batches,
Page Targets, exact Core routes, Event/Support Process fixture context, and
managed PDFs. It produces **nine PDFs / ten physical pages** (the Daily main
sheet + continuation and the eight remaining form families). No live students,
class rosters, observations or event narratives are rendered. Its
`synthetic_core_workspace` and `synthetic-route-manifest.json` are required
for later QR route verification; do not move them separately or delete them
before the scanner gate. All artifacts are synthetic, local and uncommitted.

The fixture generator checks exact live Core route reloads and SHA-256 on
copied print samples. It never claims a form was printed or scanned.

## Printer/scanner acceptance — must actually happen

1. Print all ten synthetic pages on an ordinary laser printer at **100% scale**
   (no fit-to-page or reduced margins). Note printer model/driver/firmware,
   paper size, whether duplex was used, and any graying, clipping or blur.
2. Inspect each form's readability and writable area; inspect checkbox
   geometry, the four-module QR quiet zone and complete human fallback.
3. Scan each printed page to a distinct PNG/JPEG at **200 DPI**, then repeat
   at **300 DPI** if practical. Record grayscale/color and scanner settings.
4. Install OpenCV only in the **qualification virtualenv**, if absent:
   `python -m pip install opencv-python-headless`. This is **not** a runtime
   requirement for Portia, and this tool performs no behavior-data OCR.
5. From the source checkout run (example for two individual pages):

```powershell
python scripts/verify_issue58_physical_scans.py `
  --manifest "$destination\synthetic-route-manifest.json" `
  --scan "daily_classroom_observation:1=$destination\scans\daily-main.png" `
  --scan "daily_classroom_observation:2=$destination\scans\daily-cont.png" `
  --allow-partial
```

For the **final** pass, supply `--scan` for **all ten** distinct page keys,
remove `--allow-partial`, and repeat with independently scanned 300-DPI images.
The verifier rejects missing/mismatched QR data and reloads the corresponding
persisted Core registration. Record any decode or readability failure and fix
before marking Slice 8 qualified. If the office scanner exports PDF only,
export pages as PNG/JPEG *from that actual scan*, not from the source PDF.

### Operator qualification record (fill only with actual observations)

| Gate | Actual evidence | Outcome |
| --- | --- | --- |
| Windows focused security/compat tests | _Pending local run_ | OPEN |
| Unprivileged Junction denial | _Pending local run_ | OPEN |
| Core 0.6.6 installed-wheel on Windows | _Pending_ | OPEN |
| Core minimum/historical supported version | _Pending isolated version matrix_ | OPEN |
| Hosted Ubuntu/Windows CI | _Pending PR_ | OPEN |
| 10 synthetic sheets printed (model, driver, scale) | _Pending_ | OPEN |
| Scan 200 DPI + 300 DPI (10 exact routes each) | _Pending_ | OPEN |
| Writable regions / text legibility inspection | _Pending_ | OPEN |
| QR negative conditions (cropped, scaled, low contrast) | _Pending_ | OPEN |
| Packaging wheel / sdist + full repo suite | _Deferred final Slice 9_ | OPEN |

## Invariants

- Physical copy count is independent of canonical route count. A reprinted
  blank form may be a new physical source in #59; route duplication alone does
  not establish that two returned scans are the same sheet.
- Do not promote a synthetic form to domain evidence, create a domain Event on
  generation, or reuse a real student's name as fixture data.
- Never publish copied scan images, Core workspace fixture route files, or
  printed QR values in a public GitHub issue. Report counts and failures only.
- Windows viewer aliasing remains a *presentation-only* capability. No alias
  identity is stored in a Page Target, manifest, receipt or QR.
- Do not mislabel computer-side QR decoding as physical print/scanner success.
- The issue cannot close until the physical and compatibility gates pass.
