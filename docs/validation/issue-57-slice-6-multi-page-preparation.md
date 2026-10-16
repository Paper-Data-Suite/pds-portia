# Issue #57 — Slice 6: Multi-page preparation and safe replay

**Branch:** `57-capture-batch-page-target-services`
**Starting commit:** `521ac0b680815a7df3435793427a5a74051b6b9a`
**Authority:** Portia #56, ADR 0016/0021, Core public PDS2 API.

## Bounded public service

`FileCapturePreparationService(workspace_root)` coordinates the already-released
runtime models and the Issue #57 Batch, Page Target, and route services:

- `prepare(CapturePreparationRequest(batch, targets), authorization=provider)`
- `inspect(class_id, work_id, authorization=provider)`
- `recover(class_id, work_id, authorization=provider)` — **read-only assessment
  in Slice 6**; explicit interrupted-state repair is reserved for Slice 7.

Preparation first authorizes all three mutation scopes, validates each purpose
and any exact existing-work context, and rejects duplicate/case-insensitive
requested target identities. These steps precede creation of the operational
Capture Batch. After the Batch exists, it validates known persisted Page Targets
and the Core route namespace before creating new Page Targets. Known conflicting
page IDs, indices, historical representations, or corrupt route files block new
Page Target creation.

The service processes pages by increasing `page_index`. Each page is persisted,
Core-registered, and verified by reloading the exact Portia Page Target and Core
`RouteRegistration`. **Only `verified` results expose the PDS2 locator/payload.**
If a page fails, remaining pages receive `retryable/not_attempted` results and
are not created by that attempt. Successfully verified earlier pages remain
intact; no deletion, rollback, guesswork, route overwrite, or implicit repair
occurs. Repeating the exact request reuses immutable Page Targets and Core route
registrations; the workflow continues from durable evidence.

`inspect()` reads without changing state, reports current Page Target v2 route
readiness, and rejects historical v1 targets rather than falsely treating them
as new v2 pages. `recover()` is currently the same non-mutating assessment.
Explicit recovery and unresolved partial-state handling belong to Slice 7.

`CapturePreparationResult.ready_for_rendering` also requires an **open** Batch;
a closed Batch can retain verified historical routes without authorizing a new
print run. Cancelled batches remain unprintable. The later renderer must
independently authorize and check current state at actual render time.

The service does not create a class-day Event, Observation, Support Process,
Communication, behavior classification, or student identity. No Core viewer
alias becomes part of a target, route, template or source-provenance identity.

## Focused acceptance

The synthetic Slice 6 tests exercise ordered multi-page preparation; exact
PDS2 target identity; unchanged retry routes; partial success and resumption;
conflict and permission gating; existing page-index preflight; read-only
inspection; closed-Batch print readiness; corrupt Core routes; domain
noncreation; and workspace mismatches. Existing Slice 1 and Slice 5 contract/
routing tests are included in the focused qualification. No full repository
suite is required at this slice.

Official Core v0.6.6 Windows alias qualification remains Slice 8. Slice 7 will
strengthen explicit recovery, concurrency, and path security.
