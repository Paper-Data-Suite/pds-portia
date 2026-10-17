# Portia #57 — Slice 2: Capture Batch storage and lifecycle

## Boundary and status

Adds `FileCaptureBatchService` implementing the Slice 1 `CaptureBatchService` protocol
for frozen `capture_batch@1`. These batches are **non-domain operational work roots**.
They cannot be passed as an Event or Support Process and never allocate a canonical
Observation, Event, Communication, participant, or support record. Page Targets,
Core route creation, QR generation, PDF rendering, and teacher menu integration
remain later slices.

## Source and identity

- Core-owned class context is validated with `load_class_metadata_for_class()`;
  class access is authorized by a trusted `CaptureAuthorization` implementation.
- The provider additionally exposes `attribution()`, the trusted actor; user-supplied
  `created_by` / `updated_by` must match it on creation. On lifecycle transitions
  the service supplies updated attribution from the provider.
- The exact Capture Batch work ID is a `cbat_...` identifier, mapped through
  Core `ModuleWorkRef(module_id="portia", class_id=..., work_id=...)`.
- Persisted bytes live at Core's canonical path:
  `classes/<class_id>/modules/portia/work/<cbat_id>/work.json`.
- A Capture Batch remains distinct from Portia's domain `portia_work_ref` type;
  the Event/Support Process repository and schemas are unchanged.
- A class without valid Core `class.json` is rejected; this service never creates
  a class or roster implicitly.

## Operations

`create_or_load(batch, *, authorization=...)` requires an open v1 model and
exclusive creation. An identical persisted model is a safe retry; conflicting
identity/content is not overwritten. A nonempty work root lacking `work.json`
is reported for explicit recovery rather than adopted.

`load(class_id, work_id, *, authorization=...)` is strict and read-only.
`list_batches(class_id, *, authorization=...)` includes only `cbat_` work roots,
not Event and Support Process roots, and fails on inconsistent Capture Batch
manifests instead of ignoring them.

`transition(class_id, work_id, "closed" | "cancelled", *, authorization=...)`
accepts transitions from **open only**, and allows an exact terminal-state retry.
It never reopens closed/cancelled batches or interprets these states as printed,
received, reviewed, or materialized behavior facts.

## Storage/recovery semantics

The service reuses Portia `exclusive_create`, `canonical_json_bytes`,
`fingerprint_bytes`, `guarded_replace`, and the bounded technical-history leaf
builder. Prior exact bytes are preserved before replacing the canonical manifest.
An exclusive per-batch lifecycle lock serializes cooperating service transitions;
any lock left by an interrupted process blocks ordinary mutation and requires
explicit inspection. No lock is expired based on age. The lock is not a domain
record or PDS2 route alias.

Existing link-like/symlink/junction components inside the workspace are rejected
before operations, including Core class metadata, work roots, and history paths.
The eventual security/concurrency slice will address hostile filesystem
component swaps between checks and open calls and add Windows race qualification.
It must not silently weaken these protections or remove ambiguous history.

No Core viewer or alias API is used here. Viewer presentation paths cannot enter
Capture Batch identity, timestamps, or technical history.

## Focused qualification

- New synthetic tests: creation, strict read/list, duplicate retries,
  conflicting updates, trusted class/actor gates, Core class metadata,
  lifecycle, exact prior-byte history, explicit recovery from orphan roots,
  interrupted lock, injected replacement failure, link-like path denial,
  and absence of domain work creation.
- Slice 1 compatibility tests and the Issue #56 Capture Batch contract test.
- Changed-file Ruff/mypy and syntax check. Full-suite testing is deferred until
  the authoritative Issue #57 pre-PR gate; do not run a redundant clean suite.

## Follow-on slices

Slice 3 adds Page Target v2 writes and exact historical v1 loads under this
verified batch owner. Later slices add purpose/context checks, Core registration,
reload verification, multipage orchestration, and stronger recovery/concurrency
qualification. Core v0.6.6 official wheel/Windows alias checks remain a final
acceptance requirement, not an implied Slice 2 result.
