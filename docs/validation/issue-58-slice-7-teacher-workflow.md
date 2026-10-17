# Portia #58 Slice 7 — Guided paper capture generation, reprints and preview

Branch: `58-reusable-capture-forms-pds2-rendering`.
Starting commit: `2d367547f2078680ef426cc154779b78655e1663`.

## User experience

Existing task numbers 1–9 stay unchanged. Main menu adds **10. Create Paper Capture Forms**.

1. Choose create-new or saved-packet action; choose a real Core class (both roster and class metadata required).
2. Choose one of the nine historically frozen supported form families by human label.
3. Daily Observation: zero to eight optional continuation sheets, all separately registered.
4. Evidence forms: select exact existing Event or Support Process from the class; monitoring, communication, implementation and follow-up can optionally bind an exact existing work; new Event/Observation forms intentionally have **no** existing-work link. Unsupported form/continuation combinations are rejected.
5. Preview class/form/page count; explicitly type **GENERATE**. No domain facts are entered.
6. Build `capture_batch@1` and `page_target@2` models from the catalog with generated opaque IDs; call #57 `prepare()` to register/verify Core PDS2 routes; call #58 immutable artifact generation only when every page verifies.
7. Display PDF-ready/not-printed and optionally request Core `open_local_path()` viewer handoff.
8. Saved-packet actions: verify/open, exact PDF reuse, deliberate partial PDF recovery, deliberate Core route recovery.

`TeacherCaptureService.plan()` performs no persistence. `generate()`, `reprint()`, `recover_routes()`, `recover_pdf()` and `preview()` expose typed noninteractive service APIs using an explicitly supplied `CaptureAuthorization`.  A failed preparation returns **needs attention**, never a partially printable packet.

## Authority and privacy limitation

The teacher-local default `LocalWorkspaceCaptureAuthority` is an **OS-account and locally selected Core-workspace** gate: each requested class must currently have class metadata and a roster in that workspace. This is a bounded single-user pilot adapter, **not** a district login, institutional proof of identity, or student-specific authorization. The actor is honestly recorded as a Portia *system process*, never the operator's unverified display label. Multitenant deployment requires injecting an institutional `CaptureAuthorization` instead. Never extend this adapter to remote/multi-user access without an explicit decision.

The saved-packet picker does not expose student roster contents or prefill private observations. Existing-work selection uses version-specific canonical work references; no successor substitution. The prepared PDF displays route/fallback but does not imply a teacher printed, saw, or returned it. Preview loads Core's local-opening helper on demand, retaining compatibility with older Core versions that lack it. Core v0.6.6 may use a presentation-only junction alias for Windows viewer launch; only the original verified PDF location is retained.

## History and error boundaries

All ten frozen specs and known-answer fingerprints from Slices 2/4 are unchanged. Every physical page gets its own `page_target_id`, page index, current Page Target and Core route. Generation never creates Events, Support Processes, Observations, student identities, interventions or materialization. Partial routes are not paper-ready; operators must deliberately request exact recovery. The managed artifact service alone owns immutable PDF/receipt storage. Reprint of a second physical copy does **not** create a new route or assert only one page can be returned in #59.

## Validation

Run auto-fixing Ruff on the limited changed-file set, strict mypy on new typed service/menu, `compileall` and a single focused pytest run combining new flow/menu acceptance with #57 preparation, #58 renderer/storage and existing menu navigation. Apply-time checks are authoritative; this bundle is not a claim that installed Core/Portia tests or physical printing have passed.

Later #58 Slice 8/9 must still qualify Windows/Ubuntu installed wheels, old Core support, physical printer/scanner decode, path attacks and full CI. An unprivileged Windows account's symlink test skip remains a separately qualified physical/security condition, not a pass.
