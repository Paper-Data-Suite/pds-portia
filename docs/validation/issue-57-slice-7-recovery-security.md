# Issue #57 — Slice 7: bounded recovery, path safety, concurrency

**Branch:** `57-capture-batch-page-target-services`
**Starting commit:** `7d93d4a6862e4ddf16b2bf35ffd8132fcbc42436`
**Authority:** Issue #57; ADRs 0016/0021; frozen Issue #56 runtime contracts.

## Teacher-visible recovery behavior

`FileCapturePreparationService.recover(class_id, work_id, authorization=...)`
now performs an explicitly requested, narrowly bounded recovery operation.
It does **not** reconstruct the teacher's missing request or infer a student,
Event, Observation, Communication, or other behavior-domain fact.

1. Authorize the recovery, class access, target listing, route inspection, and
   potential Core registration *before the first write*.
2. Strictly reload Capture Batch and every persisted Page Target.
3. Read **all** Core route registrations with Core's public read API.
4. Audit every route's exact target identity, contract version, work/class owner,
   uniqueness, active status for v2, and the frozen template identity snapshot.
5. Block the entire request on orphan routes, duplicates, invalid history,
   unknown target/version, or any incomplete/contradictory registration.
6. If the batch is open and the Page Target is already durable and active,
   register only a **missing** route using Core's exclusive writer, then reload
   both durable records and verify the canonical PDS2 payload.
7. Stop immediately after a failed recovery step. Previously verified routes
   remain untouched; unattempted later pages are explicitly `retryable`.

`inspect()` remains read-only. `prepare()` keeps its original request-based
idempotent retry semantics. `recover()` does not manufacture a Page Target for
a requested page that never reached durable storage: that requires `prepare()`
with the exact original request.

## Safety and historical integrity

- Capture Batch lifecycle transitions, Page Target creation, and Core route
  creation retain the existing exclusive batch lock.
- Interrupted or occupied locks are never removed because of age, apparent
  process absence, or a second caller's guess. An interrupted lock produces
  `requires_manual_lock_review` and preserves all evidence.
- The whole-inventory audit prevents an orphan or contradictory registration
  from being overlooked merely because it does not match the requested page.
- Historical `page_target@1` files remain intact. The recovery writer only
  targets current `page_target@2` and does not mutate historical Core routes.
- Core remains the only route-registration writer and loader. Portia checks
  link-like route path components before and after the Core write.
- The temporary Windows viewer alias introduced in Core #232 is never a PDS2
  identifier, module path, template fingerprint, or provenance input.
- Detectable symlink/junction paths are rejected. Fully adversarial directory
  swaps between independent filesystem calls remain a platform-level risk;
  no claim of atomic multi-path repair or race-free Windows handle security is
  made here. Additional platform qualification belongs to Slice 8.
- No quarantine is created automatically: contradictory evidence is reported
  without destroying or selecting historical records.

## Slice 7 focused acceptance

Synthetic tests cover durable-target/missing-route restart, replay without
byte changes, unmodified inspection, orphan/dangling routes, mismatched
contract/template/owner, duplicate registrations, permission denial, terminal
batches, occupied locks, failed later pages, concurrent recovery, prevention of
new target writes alongside contradictory routes, and alias isolation.

Run changed-file Ruff, strict mypy, compileall, then focused Issue #57 tests
through `run_slice7_focused_gate.ps1`. Full repository qualification and exact
installed-wheel Core v0.6.6 authentication remain Slice 8/9 tasks.
