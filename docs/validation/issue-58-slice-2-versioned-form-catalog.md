# Issue #58 — Slice 2: Immutable Form Catalog / Exact Capture Specification v1

**Branch:** `58-reusable-capture-forms-pds2-rendering`
**Expected starting HEAD:** `c32f52a43f9b20fa3c827c2cec2af9143f21c498`
**Authority:** Portia #58, #57, ADR 0016 / 0021, `page_target@2`, `paper_interpretation@1`.

## Scope

Adds an immutable, versioned **read-only** catalog implementation in
`portia.capture.form_catalog`, including **package-bundled** historical
specifications for the primary Daily Classroom Observation and its separately
routable continuation role. No PDF rendering, route registration, persistence,
menu interaction, interpretation, review or canonical behavior-domain record
creation is included in this slice.

Public read-only API:

- `list_supported_capture_forms()` — teacher-safe labels; v1 exposes the daily form.
- `capture_pages_for_form(form_id)` — main and continuation page-role specs.
- `installed_capture_page_specs()` — frozen bundled layout/capture semantics.
- `resolve_capture_page_spec(identity)` — exact **seven-field** historical lookup.
- `CapturePageSpec.template_identity()` and `.entry_layout()` — exact
  `page_target@2` snapshots for a later authorized creation plan.
- `CapturePageSpec.assert_page_target_exact(target)` — semantic agreement only;
  never replaces durable authorization/route verification at actual render time.
- `parse_capture_page_spec(bytes)` — strict validation for test/authoring tools;
  not arbitrary user-file loading or permission to alter historical package data.

## Published v1 form roles

| Form ID | Page role | Page ordinal | Entry keys | Context | Handwritten/marked regions |
| --- | --- | ---: | --- | --- | --- |
| `daily_classroom_observation` | `classroom_observation` | 1 | `session_context`, `observation_01`, `observation_02` | Date, optional session reference, lesson objective, major steps, session notes | Separate observation tone cue, optional subject, optional time, descriptive notes |
| Same form | `observation_continuation` | 2 | `session_context`, `observation_01`, `observation_02`, `observation_03` | Date and session reference (handwritten) | Three independently reviewable observation slots |

All printed writing fields remain optional and blank. The teacher is not required
to enter objectives, steps, observations, names, dates, or session notes into
Portia before printing. `session_context` is page-local **non-domain** source
context and has **no** `mapped_record_kind`. Each observation slot permits
`observation` or `event` as **future reviewed mapping candidates**, not as an
automatic mapping, established student identity or permission to create a
canonical record. Positive/general/concern marks are teacher capture cues only.
A checked cue is not Classification, severity, risk, misconduct, fault, outcome,
or proof the note was accepted.

`page_ordinal` distinguishes a stable template-local role and is **not**
`page_index`, printed physical-copy identity or a future scan's
`source_page_number`. Each generated continuation Page Target gets a distinct
page index, opaque target ID and registered Core route in subsequent slices.

## Immutable canonical layout / fingerprint

Each resource is a complete, closed semantic object with:

- a canonical `spec_format=portia_capture_layout_v1` and `schema_version=1`;
- exact `form_id`, template/version/layout/capture-spec IDs, role and ordinal;
- intended purpose, capture mode, human labels and instructions;
- US Letter **612×792 PDF-point** canvas with top-left geometric origin;
- fixed printer-safe margins and separate reserved header, footer and QR box;
- full four-module QR quiet-zone requirement (scannable pitch qualification is
  deferred to the real renderer and physical paper gate);
- ordered page-local entries with source roles and permitted candidate kinds;
- ordered visible fields with stable `field_key` and `region_key`, readable
  label, field type, expected recognition/transcription method, optionality,
  bounded source length/choice vocabulary, and integer rectangular geometry.

The canonical bytes are sorted-key, compact, UTF-8 JSON with `ensure_ascii=False`,
`allow_nan=False`, and a **single terminal LF**. SHA-256 of **those bytes** is
`template_identity.layout_fingerprint`. Thus a change to the visible wording,
field mapping, ordering, version IDs or geometry changes the fingerprint. Class,
student, batch, route, print timestamp, file location, QR pixels and temporary
viewer alias are not included. They cannot change historical field meaning.

Independently calculated known-answer fixtures are retained at
`tests/fixtures/issue_58/catalog/v1/identities.json`; they must never be
regenerated in-place to disguise a semantically changed historical template.

| Immutable resource | Known-answer SHA-256 |
| --- | --- |
| `classroom_observation_main_v1.json` | `33483a2543ee50c636415a53dbca611c38b361a1d649f1e5f4533cc00aaa1518` |
| `classroom_observation_continuation_v1.json` | `25fe7682a2ffab06309975194405be8020bd45935357702028f8e810b2908ee9` |

These are **real catalog digests**, replacing the placeholder-only concept in
synthetic Issue #56 Page Target fixtures, **without modifying** the old test
fixtures or any historically persisted target. No existing record is migrated.

## Fail-closed boundaries

- An unknown form, version, page role, digest or incomplete historical identity
  raises `UnsupportedCaptureFormError`; no fallback to `other`, current/latest
  installed template, fuzzy version resolution or source-meaning inference.
- Duplicate JSON keys, unexpected schema members, unknown entry/field keys,
  unsupported methods/mappings, overlapping capture rectangles, out-of-bounds
  writing areas, QR reservation changes and contradictory context declarations
  are rejected.
- Current support consists only of the two daily layouts. Focused Monitoring,
  Communication, Event Information, Implementation and Follow-Up will gain
  **their own** explicit v1 specs in Slice 4. Fidelity, Reentry and Repair
  remain unsupported pending bounded verified designs.
- This catalog does not claim a document was rendered, a PDF opened, a print
  job completed, a handwritten entry exists or an observation occurred.
- A later renderer must use #57 `FileCapturePreparationService`, then **recheck**
  current class authorization, active Batch, persisted Page Target, exact
  registration and canonical Core PDS2 payload before emitting QR/fallback.
  `assert_page_target_exact` alone is **not** render authorization.

## Packaging and follow-up

`portia.capture.form_specs` is a standard subpackage and its JSON resources are
included through `pyproject.toml` package-data. `MANIFEST.in` already includes
Portia JSON resources for sdists. Installed-wheel, Windows/Ubuntu and historical
Core compatibility gates remain final qualification obligations (#58 Slice 8/9).

Slice 3 will implement the actual Daily Classroom Observation layout/render
contract using these exact keys, geometry and identities (and separate page
preparation/registration). Slice 4 extends the catalog with additional form
families. Any meaningful changed historical spec is **new**, not an in-place
patch to an issued identity or silent reinterpretation of a returned sheet.

## Focused qualification

The guarded `apply_slice2.ps1` performs changed-file Ruff, strict mypy,
`compileall`, a single focused pytest run covering Slice 2 and #57 Slices 1/6,
then staged whitespace and exact path-scope checks. It commits/pushes only
after those pass, without redundant full repository suites.

A separate isolated Python 3.13 run on the generated catalog using a stand-in
Page Target model completed **21 catalog tests**; this is syntax/semantic
preflight **only**, not authoritative real-Portia test evidence. Record the
actual PowerShell gate results before declaring Slice 2 qualified. Do not
claim PDF/scanner or installed-wheel qualification in this slice.
