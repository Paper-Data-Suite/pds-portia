# Issue #57 — Final qualification and PR handoff

## Supported service surface

- `FileCaptureBatchService(workspace_root)` — `create_or_load`, `load`,
  `list_batches`, `transition`. Requires a trusted `CaptureAuthorization`.
- `FilePageTargetService(workspace_root)` — current `PageTargetV2` creation and
  exact v1/v2 reads/lists, including strict purpose and existing-work rules.
- `FilePageRouteService(workspace_root)` — Core-owned PDS2 registration and
  verification; a route becomes print-ready only after durable reload.
- `FileCapturePreparationService(workspace_root)` —
  `prepare(CapturePreparationRequest(batch, targets), authorization=...)`,
  `inspect(class_id, work_id, authorization=...)`,
  `recover(class_id, work_id, authorization=...)`.

The teacher-facing application flow to be built under parent #55 is:
**Choose class → Choose form → Choose pages/context → Prepare → Render**.
The rendering/menu/printing layer is not part of Issue #57. Teachers should
never enter raw JSON paths, route IDs or Core registration fields manually.

## Durability and conflict resolution

1. Preparation validates trusted class authorization and exact immutable models.
2. It creates/reuses a non-domain Capture Batch; it does not create a class-day
   Event or other behavior-domain work merely to satisfy Core's `work_id`.
3. Each Page Target stays bound to the frozen form template, layout and version.
4. Core's exclusive route writer is used for new registrations; exact retries
   must reload the same canonical registration without mutation.
5. The result includes a printable PDS2 payload **only** after both persisted
   target and exact active Core registration agree on identity, version and
   template snapshot. Partial results remain explicit and non-printable.
6. Inspect is read-only. Explicit recover re-registers only provably missing
   routes for durable active v2 targets in open batches after complete inventory
   audit; orphan/inconsistent state remains blocked for manual review.
7. Capture Batch locks, historical v1 representations and Core route files are
   not blindly cleared, rewritten, migrated or deleted. Authorization and path
   containment are part of the service contract.

## Core release and viewer isolation

Core v0.6.6 official release: `35af5d0642e84a625cd143285c4ef6de98dbcca4`.
Wheel SHA-256: `d6d21e426092b0329bcfd69b6fbee44c345edc46794a914d847d5ea73a2b7301`.
Exact official-wheel authentication is in `scripts/verify_core_wheel.py`;
`smoke_test_issue57_core066_wheel.py` isolates installed Core/Portia and tests
Windows real-junction/Ubuntu opener behavior with a mocked desktop handoff.
Core temporary viewer aliases are never canonical PDS2 route identity or
stored Portia target/provenance; cleanup must never remove authoritative files.

## Qualification to be completed before merging

1. Confirm latest branch-tip CI: legacy Windows and Ubuntu qualifications
   (Core 0.6.5 with 0.6.4 and 0.6.3 historical checks) **and** independent
   official Core 0.6.6 Windows/Ubuntu installed-wheel qualifications all pass.
2. The authoritative `validate_repository.py` includes Issue #57 closeout
   validation, then its single full pytest run, full Ruff/mypy, source and wheel
   build, Twine/package checks, and historical installed-wheel smokes.
3. Confirm Issue #57 service, package and exact wheel authentication tests pass;
   record the hosted CI URLs and exact branch SHA in the PR after completion.
4. Do not claim external viewer visibility or run real student data during
   automated qualification. Synthetic fixtures only.
5. Open a PR with `Closes #57` and `Refs #55`; squash merge only after all
   CI jobs are green, reconcile main to origin/main and verify clean tree.
6. Keep Issue #55 open. **Do not publish a Portia release solely for #57.**

The final acceptance matrix is in `issue-57-acceptance-matrix.md`.
