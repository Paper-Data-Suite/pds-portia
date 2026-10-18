# Issue #58 — Slice 4: Core Capture Form Catalog and Frozen Drawing Plans

**Branch:** `58-reusable-capture-forms-pds2-rendering`
**Expected starting HEAD:** `792005b5270d35ffd8ea37712d6885fd5299befd`
**Authority:** #58, #57, ADR 0016/0021, `page_target@2`, `paper_interpretation@1`
**Status:** prepared for local focused gate; not yet a PDF/print/scan qualification.

## Scope

Extend the immutable, read-only v1 catalog from the two Daily Classroom
Observation page roles to **ten frozen page specifications across nine teacher
form choices**. Add pure source-faithful drawing plans for eight additional
core forms. All forms are blank and do not create Event, Observation,
Communication, Support Process, Implementation, Follow-Up, judgment or source
identity merely by being selected or prepared.

This slice does **not** generate a PDF, QR/fallback, Capture Batch, Page Target,
Core route, domain record, or viewer alias. Only the later renderer (Slice 5)
can generate PDF after a separate authorization and exact durable route recheck.

## Supported form-to-purpose/context matrix

| Teacher choice | Exact Page Target `page_purpose` | Context rules | Source entries and candidate maps |
| --- | --- | --- | --- |
| Daily Classroom Observation (unchanged) | `classroom_observation_capture` | Existing work forbidden | `session_context` unmapped; independent observations may be proposed toward `observation`/`event` after review |
| Focused Tally / Monitoring | `focused_monitoring_capture` | Optional exact Event/Support Process | Unmapped monitoring context; monitoring entry to `observation` candidate |
| Communication Log | `communication_capture` | Optional exact Event/Support Process | Unmapped date/party context; communication entry to `communication` candidate |
| Event Information (New) | `new_event_capture` | Existing work forbidden | Unmapped time/place context; neutral event description to `event` candidate |
| Event Information (Multiple) | `multi_entry_event_capture` | Existing work forbidden | Unmapped shared page context; two **separately reviewable** event entries |
| Event Information / Evidence (Existing) | `event_evidence_capture` | **Required exact Event** | Unmapped source context; evidence to `account` / `observation` candidates |
| Support / Intervention Implementation | `implementation_capture` | Optional exact Event/Support Process | Unmapped reference/date context; implementation candidate with **planned and actual** regions separated |
| Support Process Evidence (Existing) | `support_process_evidence_capture` | **Required exact Support Process** | Unmapped source context; observational support evidence candidate |
| Follow-Up | `follow_up_capture` | Optional exact Event/Support Process | Unmapped reference/date context; follow-up candidate with proposed and actual activity separated |

**Explicitly unsupported:** `fidelity_capture`, `reentry_capture`,
`repair_capture`, and a default `other` form. Existing schema vocabulary is
not reduced, but the renderer catalog refuses these until a stable authorized
purpose-specific capture specification exists. No silent generic substitution.

Every context entry is a **page-local source locator with no mapped domain kind**.
Every field is optional; empty fields and unmarked boxes are not `false` or
record absence. A positive/general/concern cue on the unchanged daily form is a
capture aid, not a Classification, severity, diagnosis or behavior judgment.

## Frozen resource and historical lookup

The eight additional JSON resources are stored in the installed
`portia.capture.form_specs` subpackage and packaged by the existing
`capture/form_specs/*.json` package-data declaration and `MANIFEST.in` rule.
The existing main/continuation JSON **resources are byte-identical** to Slice 2:

- Daily main: `33483a2543ee50c636415a53dbca611c38b361a1d649f1e5f4533cc00aaa1518`
- Daily continuation: `25fe7682a2ffab06309975194405be8020bd45935357702028f8e810b2908ee9`

New known-answer fixtures are in
`tests/fixtures/issue_58/catalog/v1/additional_identities.json`. Each
resource's immutable SHA-256 covers the canonical sorted-key compact UTF-8
semantic JSON plus a single final LF, including text labels, ordered
entries/fields, source roles/mappings, optionality, bounds, PDF-point geometry,
reserved QR area and versions. No class, person, date of generation, route,
output location, QR bitmap, scan source or Core viewer alias contributes to a
layout fingerprint.

`installed_capture_page_specs()` lists all ten page resources. The formerly
two-page-only legacy assumptions in the dedicated Slice 2/3 synthetic tests
are refined to `capture_pages_for_form("daily_classroom_observation")`; no
production historical digest or role was modified. All seven `template_identity`
fields are required by `resolve_capture_page_spec()`; an unknown digest/version,
corrupt spec, mismatched page purpose/context/entry layout, or unsupported
form fails closed. A legitimate new historical template version must be added
as a **new** resource/identity; never edit these frozen JSON bytes in place.

## Drawing plans and actual rendering boundary

`portia.capture.core_form_layout.plan_core_capture_form(form_id)` returns a
pure, deterministic `CoreFormDrawing` for each non-Daily form, with:

- exact frozen source specification and human-readable heading/instructions;
- text labels and ruled writable capture boxes for every declared field;
- unmarked mark-recognition choices (outgoing/incoming/unknown for the
  Communication Log); independent entries, including both multi-Event slots;
- printer-safe US Letter coordinates, 36-point minimum page margins,
  108×108-point reserved QR zone with four-module quiet-zone requirement,
  route fallback reservation, neutral fixed footer (packet pagination is added
  by the later renderer), and no QR payload;
- strict validation against exact installed template identity/field keys,
  and a pure `assert_target_exact(PageTargetV2)` consistency check.

The existing `plan_daily_classroom_observation()` remains authoritative for the
main sheet and its continuation, and rejects unrelated form roles. It is not
replaced by the generic planner. A form's template-local `page_ordinal` does
not set the later Batch `page_index`: every actual PDF page must be bound to a
**distinct** persisted Page Target/Core route by Slices 5–6, even if using the
same historical printable layout.

### Security and authorization

For all forms, `CapturePageSpec.assert_page_target_exact` checks purpose,
mode, exact template identity, ordered entries, current active status and
purpose-appropriate context presence/kind. This is **not** trusted existing
work verification: #57's `resolve_existing_capture_context()` must load the
exact representation under authorization when the Page Target is prepared.
The later renderer must separately reauthorize and reload the active Batch,
exact persisted Page Target, unique active Core RouteRegistration and canonical
PDS2 payload before any QR/fallback or final PDF may appear. A closed batch
may have historical verified routes but is not print-ready.

## Tests and focused gate

The Slice 4 focused set covers:

- preserved Daily SHA-256 digests, roles, entry keys and drawing behavior;
- eight resource SHA-256 known answers, unique keys and exact order;
- each approved purpose/context rule and forbidden/required combinations;
- no `other`, Fidelity, Reentry or Repair default mapping;
- planned versus actually attempted distinction and absence of presumed completion;
- optional handwriting slots, neutral/non-domain contexts and candidate-only mappings;
- print margins, QR/footer/header nonoverlap, label and choice box fit;
- mutated historical identities, semantics and drawing instructions denied;
- existing #57 purpose and preparation regression tests.

A standalone isolated Python 3.13 **model-stand-in** test run completed
**63 tests passed**, and ReportLab font metrics fit **85 text runs** across
the eight new form drawing plans. These checks are preliminary only: local
Ruff/strict mypy/real-Portia focused pytest must pass before commit/push.
Do not run full repository pytest twice; the authoritative full Windows/Ubuntu,
source/wheel, Core compatibility and real printed/scanned form checks remain
final candidate work under #58 Slices 8–9.

## Handoff to Slice 5

Implement a managed PDF renderer that consumes **only** immutable installed
specifications and **fresh, authorized, durably verified** #57 Page
Target/Core route results. Render complete, high-contrast, grayscale-friendly
US Letter pages using vector QR with explicit module-pitch and quiet-zone
checks; write no QR before registration verification. Render exactly the
planned fields and every actual page's own fallback identity. Stage and
verify output before guarded install; no incomplete packet may be reported
ready. Later scan/review (#59/#60) must consume the same immutable historical
entry/field/region map, not reverse-engineer drawn shapes.
