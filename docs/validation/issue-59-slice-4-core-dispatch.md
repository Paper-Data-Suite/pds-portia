# #59 Slice 4 — Core PDS2 dispatch and read-only Page Target verification

**Base:** `28d4fea5520affe6025e38de403f5ba305362039`
**Branch:** `59-core-retain-first-pdf-scan-intake-page-records`

## Contract and implementation

`FilePageRouteDispatchService.verify(discovery, authorization=...)` accepts an existing `SourceQrDiscovery` from Slice 3 and produces one `PageRouteOutcome` per physical retained-source page, in original order. This service has **no persistence API** and does not create Page Records, paper interpretations, proposals, reviews, or domain records. It checks Core-retained source digest/size before and after dispatch.

For each candidate locator, it first calls trusted class authorization, then authorizes and loads the durable Capture Batch. Cancelled batches are rejected, while previously printed active registrations may be processed after a batch is closed. It checks the Core route path against Portia's link/junction guard before invoking the **public Core** `dispatch_route` with a one-request `ModuleRegistry` and `ModuleProfile` owned by the invoking Portia teacher operation. The selected module profile permits only active PDS2 routes and supports the frozen current Core routing/registration contract versions. No global installed profile or module entry point is claimed by this slice.

Core performs exact registration loading, compatibility and status checks. The Portia route handler then loads the persisted Page Target under authorization and verifies exact module/class/work, record kind, target contract version, status, and historical template identity stored in the active Core registration's `module_details`. No guessed IDs or inferred students enter verified outputs. Mismatched and missing targets fail closed. Foreign-module pages preserve the explicit Slice 3 `foreign_module` disposition rather than being claimed as Portia work; generic mixed-module Suite delegation remains a future #55 integration.

Return statuses distinguish QR detection failures, authorization denial, missing/cancelled batch, missing/retired/conflicting route, missing/mismatched target and processing failures. Only `status="verified"` may expose a `VerifiedPageRoute` typed Core resolution and Portia Page Target, required for Slice 5 durable Page Record creation. Source page number remains distinct from printed Page Target `page_index` or template `page_ordinal`.

## Security and limitations

The Core retain-first source bytes remain authoritative and unchanged. Class authorization precedes any class-owned route or target lookup; Core route files are read via their canonical paths. Intake does not log decoded QR strings, path details or student data as teacher-facing routine statuses. Unexpected failures must never be represented as success; the service creates no files.

Slice 4 does **not** register a global `paper_data_suite.modules` entry point, does not dispatch non-Portia modules, and does not create Page Records. Global installed profile discovery, multi-module delegation and durable retry semantics are later integration steps. Core's legacy race behavior under concurrent malicious directory replacement is not solved by this preflight; the subsequent security slice will test it explicitly.

## Focused validation

Test real Core retained-source and Core registered-route dispatch against Portia fixture batch/target records. Cover verified and repeated read-only results, missing/ambiguous/foreign QR pages, unknown/retired routes, no-access-before-Core-lookup, historical template mismatch, missing Page Target, cancelled/closed batch, source tampering, original source-page order and lack of any Page Record/domain artifact. Ruff, mypy and focused pytest only; **no redundant full suite or manual individual paper rescans**.
