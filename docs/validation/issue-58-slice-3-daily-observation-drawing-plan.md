# Issue #58 — Slice 3: Daily Classroom Observation drawing plans

**Branch:** `58-reusable-capture-forms-pds2-rendering`
**Starting HEAD:** `e1d60631b6b7902a6bfa8c2baeefa6521e1d76bf`
**Authority:** #58, ADR 0016/0021; immutable v1 resources from Slice 2.

## Delivered boundary

Adds the read-only `portia.capture.observation_layout` drawing-plan service and
exports `plan_daily_classroom_observation`, `ObservationPageDrawing`,
`DailyObservationPacketDrawing`, `ObservationLayoutError` and stable drawing
primitives. The plan describes the **US Letter, top-left PDF-point** geometry
that the later independently authorized PDS2 PDF renderer will draw. It does
**not** generate a PDF, open a viewer, register a Core route, persist a Page
Target, or claim a page has been printed or returned.

A request `plan_daily_classroom_observation(continuation_pages=N)` returns a
main Daily Classroom Observation layout and `N` continuation layouts, each
with a distinct logical batch `page_index`. `N` is deliberately bounded from
0 to 8; no generic custom-form editing is introduced. Continuation pages
reuse the frozen continuation `page_role=observation_continuation` and
`page_ordinal=2` while acquiring **different** actual Page Targets/routes under
#57 in the future preparation/render service. Page-local `observation_01`
keys may recur across *different* continuation pages: their full provenance
also requires the exact Page Target, not adjacency or a filename.

## Human-readable writable design

- The main page has handwritten session date, optional session reference,
  **lesson objective**, **major lesson steps/activities**, optional session
  context notes, and two separately labeled observation entries.
- Each continuation has optional handwritten session reference/date plus three
  separate observation entries. It deliberately does not duplicate objective
  and steps from the main sheet or infer them from an adjacent scan page.
- Every observation entry has **unmarked** positive/general/concern cues,
  optional student-or-class reference, optional observed time, and a generous
  ruled description area. Positive/general/concern are capture aids, **not**
  Classification, risk, fault, severity or automatic finding.
- Each visible field uses the exact `field_key`, `region_key`, source role,
  wording and geometry in the immutable Slice 2 specifications; the drawing
  contract cannot introduce a new field or remap session context to a domain
  family. Empty marks/boxes are not evidence of absence or completion.
- The header reserves space for the later authorized form/class/route fallback,
  while the 108-point QR square (including the four-module quiet zone) remains
  **empty in this pure plan**. Only the verified renderer may emit a Core PDS2
  QR and human fallback after durable registration and immediate recheck.
- Thin ruled handwriting lines, legible labels, separate observation headings,
  page numbering, grayscale outlines, printer-safe margins and no roster data
  are planned using pure dataclasses; no optional renderer dependency is
  imported or required in this slice.

The actual glyph widths, clipping, vector QR module pitch, output PDF integrity,
contrast/physical print quality and scanned-page decodability will be qualified
under Slice 5/8. The lightweight width guard used here is deliberately
conservative, but **is not a substitute for a renderer font-metrics gate**.

## Historical immutability and non-domain semantics

The drawing-plan version is `daily_observation_draw_plan_v1`. The two catalog
resources, canonical semantic bytes and original SHA-256 fingerprints are
**unchanged**:

- Main: `33483a2543ee50c636415a53dbca611c38b361a1d649f1e5f4533cc00aaa1518`
- Continuation: `25fe7682a2ffab06309975194405be8020bd45935357702028f8e810b2908ee9`

A plan is accepted only when its *entire* resolved catalog specification is
identical to the installed historical resource, not merely an equal claimed
fingerprint. `ObservationPageDrawing.assert_target_exact(target)` checks pure
agreement with the target's frozen v2 identity, purpose, capture mode,
ordered entry layout, and exact `page_index`. It **does not** assert the target
is durably persisted or that its Core route is registered: those checks are
required immediately before PDF rendering.

The source-context entry has no `mapped_record_kind`; drawing a form never
preallocates an Event, Observation, class-session domain record, Communication,
student identity or proof of action. Printed date, queued time and actual
observation time remain distinct source facts. One returned page may have zero,
one or several independently reviewable observations or only context notes.

## Focused acceptance gate

The guarded local script verifies the exact branch/commit, clean working tree
and unchanged remote before application. It adds one immutable drawing-plan
module, one synthetic test module and this document; it adds only public
re-exports to `portia.capture.__init__`. It does not touch Slice 2 resources,
schema files, dependency pins, preexisting route writers or domain services.

After application, run **once**:

```powershell
python -m ruff check portia/capture/__init__.py portia/capture/observation_layout.py tests/test_issue58_slice3_daily_layout.py
python -m mypy --strict portia/capture/observation_layout.py
python -m compileall -q portia/capture
python -m pytest -q tests/test_issue58_slice3_daily_layout.py tests/test_issue58_slice2_catalog.py tests/test_issue57_slice6_preparation.py
```

Tests cover exact source/geometry field concordance, minimum writable lines,
QR/header/footer exclusion, unmarked cues and conservative text bounds,
continuation ordering/maxima, pure Page Target agreement, tamper refusal,
no PII prefill, no QR/route, and unchanged catalog known-answer hashes.

An **isolated** stand-in model preflight for Slice 2 and Slice 3 completed
39 tests. This is **not** a substitute for the real Portia model and installed
Core gate executed by the user's activated `.venv`. Automatically commit/push
only after the real local gate and staged-path/whitespace checks succeed.

**Next:** Slice 4 adds separate bounded form specs for Monitoring, Communication,
Event-information/evidence, Implementation/Support and Follow-Up. Slice 5
renders only verified Core-registered pages as validated vector-QR PDFs; the
current drawing plans are not printable artifacts.
