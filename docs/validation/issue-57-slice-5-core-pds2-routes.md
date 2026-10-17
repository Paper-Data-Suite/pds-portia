# Issue #57 — Slice 5: Core PDS2 route registration and verification

**Branch:** `57-capture-batch-page-target-services`
**Starting commit:** `791e8b9a8f7bf752305be9e6390fda46d9af1693`
**Source authority:** Portia #56; Core public PDS2 and route-registration APIs.
**Qualification boundary:** Final installed release verification against official
Core v0.6.6 and viewer alias behavior remains in Slice 8.

## Production service

`FilePageRouteService(workspace_root, *, batch_service=None, page_service=None)`
provides:

- `register_or_load(PageTargetV2, authorization=trusted_provider)` — exclusively
  register the exact previously persisted active Page Target or verify/reuse an
  existing registration. Returns `PagePreparationResult`.
- `inspect(class_id, work_id, page_target_id, authorization=trusted_provider)` —
  strictly reload and inspect without mutating the workspace.

The caller must first persist the Capture Batch and Page Target through the
Slice 2/3 services. Both methods require trusted class authorization and Core
class metadata. Neither accepts an arbitrary path or a caller-provided route
registration. The teacher does not supply or manage a route ID.

## Core work and record identity

The Core locator is exactly:

```
PDS2|m=portia|c=<class_id>|w=<cbat_work_id>|r=<Core route_id>
```

The Core registration targets:

```
ModuleRecordRef(
    module_id="portia",
    record_kind="capture_page_target",
    record_id=<persisted page_target_id>,
    contract_version="2",
)
```

Every new registration includes a snapshot of the exact current Page Target
`template_identity` and `page_target_contract_version` in Core
`module_details`. Readiness requires that those details agree with the exact
reloaded Page Target, not just the route locator. These routing details are
not source interpretation, a student, or a behavior-domain assertion.

## Registration-before-render

1. Verify class access, operational batch, and exact current Page Target bytes.
2. Acquire the shared exclusive Capture Batch lifecycle lock.
3. Rescan Core's canonical route directory with strict Core loads.
4. Reuse an already verified exact route; reject contradictory, duplicate, or
   malformed registrations without deleting or rewriting them.
5. For an open batch with no matching route, generate a non-semantic Core route
   ID. Retry a bounded number of pre-existing ID collisions.
6. Call Core `write_route_registration()` exactly once for the selected ID.
7. Strictly reload persisted Page Target and Core route registration, validate
   target version, owner, status and template identity; serialize and parse
   PDS2 using Core. **Only then** return `status="verified"` and payload.

A missing route is `retryable` only while the batch is open. A closed batch
permits read-only verification of a previously registered route but does not
create a new one. A cancelled batch never exposes printable readiness. Partial
Core writes are retained for inspection; no speculative rollback takes place.

An invalid/ambiguous route collection is `conflict`, with bounded diagnostic
codes and **no locator, registration, or payload**. Security/path exceptions
fail closed. Neither endpoint creates Event/Observation/Support Process or other
canonical behavior records.

## Compatibility and scope

Core is the exclusive routing authority: no private Core APIs or Portia route
writer are introduced. New Page Targets remain v2, historical v1 remain readable
but may not be registered as new targets here. The declared
`pds-core>=0.6.3,<0.7` dependency range is unchanged pending release-wide
qualification. The Core #232 temporary Windows viewer-opening alias is
unrelated to and absent from PDS2, route registration, template identity, and
canonical provenance. No alias lifecycle is invoked by this service.

## Focused qualification

`tests/test_issue57_slice5_routes.py` covers persisted reload/PDS2, exact
registration/target/template fidelity, authorized use, missing targets,
immutable retry, route-ID collision, duplicate registrations, inactive or
corrupted Core routes, wrong contract version, Core write/reload faults,
terminal batch handling, link-like directory rejection, and no domain artifacts.

The focused gate runs changed-file Ruff, strict mypy for the capture package,
syntax validation and the Slice 5 route tests plus the relevant Slice 4 purpose
regressions. This is not the final repository-wide or installed-wheel gate.

**Next:** Slice 6 integrates single/multi-page request planning, idempotency,
and partial completion onto this verified per-page routing primitive. Slice 7
handles more extensive failure-recovery/security/concurrency coverage.
