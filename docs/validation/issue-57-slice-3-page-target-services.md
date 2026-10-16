# Issue #57 — Slice 3: Page Target persistence and exact historical reads

**Branch:** `57-capture-batch-page-target-services`
**Starting commit:** `05e71f40939417932c8df082fc853a23daa2c599`
**Contract authority:** Portia #56; ADR 0016 and ADR 0021.
**Core qualification:** Existing `pds-core>=0.6.3,<0.7` retained. Official v0.6.6 installed/platform qualification belongs to #57 Slice 8.

## Production API

`FilePageTargetService(workspace_root, *, batch_service=None)` implements the
Slice 1 `PageTargetService` protocol:

- `create_or_load(PageTargetV2, authorization=trusted_provider)`
- `load(class_id, work_id, page_target_id, authorization=trusted_provider)`
- `list_targets(class_id, work_id, authorization=trusted_provider)`

No Page Target update, delete, rebind, or implicit migration API exists.

An incoming v2 target must already satisfy its immutable schema; new records
must be `active`, with exact `class_id`/`work_id`, a `ptgt_` identity and
verified `created_by`/`updated_by` attribution. Trusted Core class metadata and
an explicit class authorization are required. No student identity, behavioral
classification, domain Event, Observation, or Support Process is manufactured.

## Canonical storage and retry contract

Use Core's `safe_module_work_descendant` beneath the *Capture Batch* work root:

```text
classes/<class_id>/modules/portia/work/<cbat_work_id>/
  work.json
  records/capture_page_target/<ptgt_page_target_id>.json
```

The directory and each record must match their exact in-record ownership.
Creating v2 uses Portia's fsync-backed `exclusive_create`, canonical JSON bytes,
strict reload, and exact readback comparison. Creating a duplicate exact v2
representation returns it without writing. A conflicting duplicate identity,
case-insensitive identity collision, or duplicate `page_index` fails closed.

**All Page Target creation and Capture Batch terminal transitions share the
existing `.capture-batch-lifecycle.lock`.** A writer re-reads the batch under
that lock; a new page cannot be created after the batch becomes `closed` or
`cancelled`. Exact repeat reads of previously created pages remain possible,
including after closure. An interrupted/occupied lock is never cleared because
of its age or the apparent absence of a process.

An existing `page_target@1` is read **only** through the accepted historical
contract; its bytes are never migrated or reserialized. Unknown versions,
duplicate JSON keys, invalid schema data, mismatched path identity, unexpected
files, mixed-case colliding identities, and duplicated page indices block the
collection rather than silently choosing a preferred representation.

The writer checks existing symlinks/junction-like components and path boundaries.
Adversarial link-swap races between preflight and filesystem I/O will receive
additional hardening in the later Issue #57 security/concurrency slice; this
slice must not be described as fully race-hardened against hostile filesystem
mutators.

## Boundary and downstream work

Page Target v2 is an immutable operational preparation target, **not** a Core
route, physical print, retained source, interpreted handwriting, source session,
canonical behavior fact, or proof that a form was used. All `page_purpose`,
`entry_layout`, `template_identity`, and exact historical context fields remain
unchanged once written. Page-specific contextual semantic rules and existing-work
resolution remain Slice 4; route registration/verification remains Slice 5.

This slice does not implement PDF/QR rendering or any scan/intake workflow.
Core v0.6.6 Windows viewer aliases are not used, serialized, or derived by this
service and must not affect canonical work/target identities.

## Focused qualification

The bundled `run_slice3_focused_gate.ps1` exercises Slices 1–3 with synthetic
fixtures and runs changed-file Ruff, module-level mypy, Python compileall,
and `git diff --check`. It deliberately does **not** rerun the full repository
suite; full authoritative acceptance is due before the PR.

The synthetic test matrix includes v2 create/list/load/exact retry; uniqueness
and collision; terminal lifecycle exclusion; authorization; attribution;
historical v1 read; missing/corrupt/unknown/mismatched representations;
interrupted locks; link-like path denial (where permitted by the OS); and
simultaneous page-index contenders.

After the focused gate passes, stage, commit, and push the exact four-file
Slice 3 scope:

```text
portia/capture/__init__.py
portia/capture/page_targets.py
tests/test_issue57_slice3_page_targets.py
docs/validation/issue-57-slice-3-page-target-services.md
```

The work remains on issue branch #57. Do not publish a Portia release for this slice.
