# Issue #57 — Slice 1: Service Boundaries and Core Routing Audit

**Baseline (remote GitHub snapshot, 2026-10-14):**

- Portia `main` commit: `c26e3d91805e931d56ba76dd65e688953d0cd96f`
- Portia `main` tree: `9329825549e90e3db6be2f086a4f337c62e432a1`
- Core `main` commit: `35af5d0642e84a625cd143285c4ef6de98dbcca4`
- Branch: `57-capture-batch-page-target-services`
- Core `v0.6.6`: **not yet published** when checked; qualification deferred, not passed.
- Local working-tree state, Python, and installed Core must be captured at application time.

## Frozen model authority

| Contract | Portia implementation | Policy |
| --- | --- | --- |
| `capture_batch@1` | `CaptureBatchV1` | Non-domain Core work root; `open/closed/cancelled` |
| `page_target@2` | `PageTargetV2` | Current; `active/retired/invalidated` |
| `page_target@1` | `PageTargetV1` | Historical exact-read only |

`page_target@2` stores `class_id`, Capture Batch `work_id`, `page_target_id`,
`page_index`, purpose, exact template identity, capture mode, entry layout, and
optional separate exact preexisting domain context. The Core registration target
kind is `capture_page_target`, with an exact non-null contract version.
`Capture Batch` must not be inserted into the domain `portia_work_ref@1` union.

## Reviewed producer and Core APIs

- Core `pds_core.routing_models`: `ModuleWorkRef`, `RouteLocator`,
  `ModuleRecordRef`, `RouteRegistration`, validation helpers.
- Core `pds_core.pds2`: `serialize_pds2_payload`, `parse_pds2_payload`.
- Core `pds_core.routes`: `module_work_dir`, `safe_module_work_descendant`,
  `route_registration_path`.
- Core `pds_core.route_ids`: `generate_route_id`.
- Core `pds_core.route_registrations`: exclusive-write
  `write_route_registration`, strict `load_route_registration`.
- Quillan `quillan/printable_response_routes.py`: preflight paths, route
  collision handling, exclusive write, reload and verification.
- ScoreForm `scoreform/answer_sheet_routes.py`: exact page-to-route agreement,
  non-authoritative diagnostics, immutable index, reload and verification.

Only **public Core APIs** may be used. Never reconstruct route history from a
human fallback, module details, a file alias, or current installed templates.
The Core #232 viewer alias is a transient viewer presentation facility and is
**not** a PDS2 alias or identity.

## Slice 1 implementation

- Adds typed request/result/authority/store/preparation service **interfaces**
  in `portia.capture` and exact route-binding diagnostics.
- Validates open batch, active current-version pages, exact class/batch match,
  and unique page target/page indices for an attempted multi-page request.
- Denies printable route/payload exposure in retryable, conflict, or rejected
  results. A verified page must have an exactly agreeing active registration,
  locator, and canonical PDS2 payload.
- Route comparison remains **pure**. Passing it does *not* attest to persistence.
  The future service MUST independently reload the Page Target and the Core
  registration before constructing a verified result.
- Adds synthetic focused contract tests, including historical v1 route reads.

**Not implemented here:** services' persistence and authorization adapters,
route writes, retries, recovery, printing, viewer opening, scanning, or creation
of any Portia domain record. Protocols are not runnable service implementations.

## Storage and authorization direction for Slice 2

1. Use Core's `ModuleWorkRef(module_id="portia", class_id, work_id=cbat_...)`.
2. Keep operational Capture Batches in the existing class/module/work topology;
   do not route them through `PortiaRepository`'s domain-only work-ref union.
3. Reuse Portia's `exclusive_create`, guarded replacement, canonical JSON,
   history, path containment, and recovery primitives rather than introducing
   another transaction engine.
4. Make Core class ownership and teacher authorization explicit, fail closed on
   ambiguous access; never permit caller-supplied unverified class grants.
5. Distinguish identical retry, coherent partial state, and contradiction.
6. Preserve exact historical version and content under concurrent operations.

## Focused qualification

```powershell
python -m pytest -q tests/test_issue57_slice1_contracts.py
python -m ruff check portia/capture tests/test_issue57_slice1_contracts.py
python -m mypy --strict portia/capture
python -m compileall -q portia/capture
git diff --check
```

The first slice must not run the full repository suite merely to check
unchanged behavior. Final Core v0.6.6 wheel identity, digest, release SHA,
Windows deep-path alias regression, package and full-suite qualification remain
open acceptance gates for Slice 8/9 and the PR.
