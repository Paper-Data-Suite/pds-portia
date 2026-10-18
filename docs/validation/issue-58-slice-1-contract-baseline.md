# Issue #58 — Slice 1: post-#57 baseline and exact form-rendering contract audit

**Audit date:** 2026-10-17
**Branch:** `58-reusable-capture-forms-pds2-rendering`
**Parent:** #55; predecessor: #57 / PR #98
**Status:** Remote source/contract audit complete; developer-machine baseline and focused runtime gate are recorded separately by the accompanying apply script. No new renderer is claimed here.

## 1. Source baseline and evidence boundaries

| Item | Observed state before Slice 1 |
| --- | --- |
| Remote `main` and pushed #58 branch | Both `a89beeb9ab4eebdc5e6c13b7fad9112434b21eec` |
| Starting tree | `10098be758aa529ba02fd02dfe37e755fa5acac7` |
| Previous commit | `c26e3d91805e931d56ba76dd65e688953d0cd96f` |
| Portia source version | `0.2.0` (`portia/_version.py`); do not assume a new release |
| Portia declared Core requirement | `pds-core>=0.6.3,<0.7` (`pyproject.toml`) |
| Official Core v0.6.6 release identity (already qualified under #57) | Source `35af5d0642e84a625cd143285c4ef6de98dbcca4`; wheel SHA-256 `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301` |
| Actual local `git status`, Python, installed dependencies, focused tests | **Not observable through remote inspection**. Record them from the machine before a successful Slice 1 commit. |

The exact version and platform of the **current** developer environment must not be inferred from the historical #57 Windows/Python 3.11.9/Core 0.6.5 checkpoint. The application script writes `docs/validation/issue-58-slice-1-local-baseline.md` using actual local results and only commits after its focused gate passes.

## 2. Exact #57 services — production reuse boundary

| Component | Public behavior | #58 consumer rule |
| --- | --- | --- |
| `FileCaptureBatchService` | Authorized `create_or_load`, `load`, `list_batches`, terminal `transition` with Core class metadata and trusted attribution | Operational `cbat_` Core work root only. No fabricated class-day Event. |
| `FilePageTargetService` | Immutable current `PageTargetV2` `create_or_load`; v1/v2 exact `load` and `list_targets`; index/case/path guards | Current v2 to create; historical v1 never migrated or reinterpreted. |
| `FilePageRouteService` | Core-owned exclusive `register_or_load`, durable `inspect`, exact registration/locator/target agreement | Do not create a second route registry or QR identity. |
| `FileCapturePreparationService` | `prepare(CapturePreparationRequest(batch, targets), authorization=...)`, read-only `inspect`, deliberate `recover` | Plan all pages first; reuse ordering, partial reporting and restart-safe retry. |
| `PagePreparationResult` | `verified` carries reloaded canonical `payload`, `locator`, target and registration; nonverified results expose none | Renderer never invents or reconstructs printable routes. |
| `CapturePreparationResult` | `ready_for_rendering` requires open batch and **all** requested pages verified | Check again at render time; a standalone verified page is insufficient. |
| `validate_page_purpose` / `resolve_existing_capture_context` | Existing work/record resolved by exact Event or Support Process reference; no successor following | Catalog uses exact purpose/context matrix rather than a permissive generic form. |

**Important observed edge:** `FilePageRouteService._inspect_exact()` can report a historical verified route even when its batch is subsequently closed; `CapturePreparationResult.ready_for_rendering` correctly withholds print readiness. A future renderer must independently reload/reinspect the **current batch, targets and Core registration**, require an open batch and active targets, and verify exact catalog identity immediately before emitting any PDS2 symbol. A cancelled/closed batch, orphan or ambiguous route, inactive target, unsupported historical spec or partially prepared packet blocks printing.

Do not couple the renderer to private `_read`, `_registrations`, `_load_exact`, `_safe` or `_lifecycle_lock` methods merely for convenience. Prefer existing public services. If a render-time verification capability is genuinely absent, add the narrowest explicit public adapter instead of bypassing authorization or duplicating persistence.

## 3. Frozen page identity and future #60 capture semantics

Authoritative inputs: ADR 0016, ADR 0021, `schemas/v2/capture/page-target.schema.json`, `schemas/v1/capture/paper-interpretation.schema.json`, `docs/design/portia-paper-preallocation-matrix.md`, `docs/design/portia-paper-interpretation-staging.md`.

- `capture_batch@1` remains a non-domain work root; `open/closed/cancelled` is operational state, not proof of behavior or class-session observations.
- `page_target@2` has immutable purpose, capture mode, optional exact existing work/record context, ordered entry layout, status (`active/retired/invalidated`) and template identity. Older `page_target@1` is read-only historical authority.
- Complete `template_identity`: `template_id`, `template_version`, `layout_version`, `capture_spec_version`, `layout_fingerprint` (64 lowercase SHA-256 hex), `page_role`, `page_ordinal`.
- `page_index` is logical batch order; `page_ordinal` is template-local; **future** `source_page_number` belongs to returned retained-source history and is unknown at render time.
- `entry_layout.mode` is `single_entry` or `multi_entry`, with ordered stable `entry_keys`. For `classroom_observation_capture`, a declared `context_entry_key` and at least one separate observation key are required, with no prebound domain Event/Support Process.
- `new_event_capture`, `multi_entry_event_capture` cannot prebind existing work. `event_evidence_capture` requires exact Event context; `support_process_evidence_capture` requires exact Support Process. Monitoring/communication context is optional if genuinely eligible. Other purposes require explicit catalog binding, never implicit `other` fallback.
- `paper_interpretation@1` uses exact historical `layout_snapshot`, `entry_key`, `field_key`, optional `region_key`, capture method and distinct blank/unmarked/unreadable/ambiguous/candidate states. The session-context entry omits domain `mapped_record_kind`; an empty observation slot means no assertion, not negative evidence.

**Concrete gap:** current #56 synthetic classroom-observation Page Target fixture contains a placeholder SHA-256 of repeated `b` characters. #57 proves this field is persisted and checked across routes; it does **not** provide a production form catalog with executable historical field/geometry mappings that hash to that placeholder. Never reuse it as a production fingerprint. Slice 2 must implement deterministic canonical semantics, independent known-answer digest fixtures, historical version lookup and exact Page Target cross-validation.

No existing published schema/ADR needs modification merely to add a Portia-local immutable catalog. Any genuine contract incompatibility must be identified and versioned separately, rather than changing accepted v1/v2 bytes.

## 4. Inspected Core and sibling implementation precedents

| Source | Reusable precedent | Do **not** copy |
| --- | --- | --- |
| Core `pds_core.pds2`, `pds_core.routing_models`, Core route writers/readers | Canonical locator-only `PDS2|m=portia|c=...|w=...|r=...` serialization from verified registration | Names, student identifiers, Event identifiers, context, URLs or filesystem aliases in QR |
| ScoreForm `scoreform/templates.py` | Native vector PDF QR rectangles, solid white background, full four-module quiet zone; header bounds and collision checks | Academic OMR fields or sibling runtime imports |
| ScoreForm `scoreform/answer_sheet_generation.py` | Bounded dependency preflight, safe staging, exclusive/guarded output, explicit partial results | Student academic issuance/grade semantics |
| Quillan `quillan/printable_response.py` and generation/routes modules | ReportLab Letter-sized handwriting space, verified route-before-render, output verification, reprint/recovery lessons | Student snapshots, academic models or raster QR as the desired Portia vector default |
| Core `pds_core.local_open.open_local_path()` | Supported view/open handoff with Core 0.6.6 Windows deep-path alias | Persisting any temporary alias as provenance or treating shell handoff as visible PDF proof |

Portia currently declares only Core as a required runtime dependency. ReportLab and a QR matrix generator need an **explicit, packaged and installed-wheel-qualified** dependency policy before shipping a PDF renderer. Do not rely on ScoreForm or Quillan being installed.

## 5. Decisions and constraints to carry into Slice 2 onward

1. **Immutable catalog:** choose `form family -> supported version -> page roles -> entry definitions -> field/region definitions -> downstream mapping`. Every printable field gets stable page-local `entry_key`/`field_key`, display label, capture method/type, optionality, bounds, geometry and reading order. Validate cross-field/page uniqueness and page geometry instead of embedding all meaning only in drawing commands.
2. **Fingerprint algorithm:** freeze a canonical, explicitly versioned semantic envelope covering the real print geometry, recognition regions and field/entry meaning. SHA-256 must exclude generation clock, file path, QR pixels, work/route IDs and viewer aliases. Add independent digest regression fixtures and reject any supplied fingerprint/spec mismatch.
3. **Historical catalog:** lookup by the *complete exact* template identity and fingerprint. Preserve bundled older specs for later returned sheets; never reinterpret an older form with the newest installed template. Unknown versions fail explicitly.
4. **Daily Classroom Observation first:** handwritten `session_context` with date, objective, lesson steps and notes, plus independent positive/general/concerning observation slots. Optional student/class reference is source handwriting, not a required roster preprint. Cue labels are capture aids only—not severity, misconduct, risk, culpability or Classification.
5. **Continuation pages:** each actual PDF page, including extra writing space, has its own persisted Page Target and verified Core route/QR/fallback. Page ordinal remains template-local, while page index records packet order. No unregistered cover sheets.
6. **Additional core forms:** focused monitoring/tally, communication log, neutral new/existing Event information, support/implementation and follow-up must each bind approved purpose/context rules and preserve planned vs attempted/completed distinctions. `fidelity_capture`, `reentry_capture`, `repair_capture` remain explicitly unsupported until a bounded, source-faithful specification exists. `other` is not their substitute.
7. **Prepared-then-render:** preflight authorization, all page specifications, output geometry/dependencies and destination **before durable writes** where possible. Use #57 preparation. Reinspect active batch/targets/registrations before rendering and install only a complete, structurally verified, digested packet. A failed/partial page does not become a successfully labeled packet.
8. **Reprint policy:** exact same target/spec/routes can be reprinted without registration changes. Meaningful field, geometry or context change needs new Page Target/route. Two physical copies with the same route may later produce distinct #59 retained source/Page Record identities; never merge merely by route or image hash.
9. **Security/privacy:** minimal class/form identity on paper; never default-print student roster, diagnosis, sensitive existing work, or narrative. Prevent traversal, symlink/junction overwrite, route tampering, mixed-context/permission escalation and unowned temporary cleanup. QR and fallback remain privacy-minimized.
10. **Teacher entry point:** reuse `portia.menu.context`, `portia.menu.selectors.class_options`, and trusted class authorization. The process-local menu operator label is not authentication. Goal is guided class/form/pages/generate/open flow, without schema JSON entry or opaque route choices.

## 6. Qualification economy and slice transition

**Slice 1 gate:** capture actual Windows checkout/versions; run only the focused existing #57 contract and multi-page-preparation tests plus scoped Ruff/mypy once; `git diff --check`; then commit/push the two audit records if successful. No full suite or pretend physical scan proof.

**Slice 2 gate:** focused immutable catalog/spec tests; support/context matrix, stable field/entry mappings and geometry, known-answer canonical SHA-256 fixtures, exact `PageTargetV2` crosswalk, unknown version fail-closed, package-resource lookup; changed-file Ruff/mypy and one focused pytest invocation.

**Later gates:** Daily and continuation sheets, vector QR pitch/quiet zone and collision checks using real PDS2 lengths, safe atomic PDF staging/reprint/partial recovery, teacher menu and preview; Windows/Ubuntu installed-wheel and historical Core compatibility; actual synthetic laser-print/scanner verification; one final authoritative full-suite/package/CI qualification.

## 7. Slice 1 completion criteria

- [x] Exact remote starting branch/main commit and tree checked.
- [x] Core v0.6.6 published artifact authority distinguished from locally installed Core.
- [x] #57 public services, status boundaries, purpose/context and persisted-route verification audited.
- [x] `page_target@2` / ADR 0016 + ADR 0021 / #59-#60 historical entry/field contracts audited.
- [x] ScoreForm vector QR, Quillan generation and Core local-open precedents reviewed.
- [x] Next-slice catalog/historical mapping and failure-test plan specified without editing frozen schemas.
- [ ] Actual developer checkout/Python/installed packages and focused gate captured; complete with the companion application script.

**This slice does not create a PDF renderer, form catalog, Page Target, QR route, domain record or Portia release.**
