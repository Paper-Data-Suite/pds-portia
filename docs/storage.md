# Portia canonical storage and guarded persistence

Issue #38 implements the first production persistence layer for Portia v0.2.0.
It consumes the immutable runtime models and in-memory validation introduced by
Issue #37; it does not redefine the accepted ADRs or public JSON contracts.

## Layering

The executable boundary is now:

```text
public JSON wire value
  -> exact contract/version parser
  -> immutable Portia runtime record
  -> in-memory application validation
  -> guarded Portia storage/recovery services
  -> later teacher workflow services
```

Portia deliberately keeps these persistence categories separate:

```text
canonical domain record
!= durable operational record
!= derived projection
!= transient artifact
```

Canonical records remain authoritative for domain meaning. Operation journals,
locks, Quarantine, acknowledgement, and suppression coordinate or diagnose work
but do not become behavior evidence. Derived generations are rebuildable and
never authorize domain mutation. Staged candidates are removable only while
Portia can prove that they are unaccepted and are not required for recovery.

## Canonical topology

Class-owned Event and Support Process work continues to use Core's public
module-work paths:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  work.json
  records/<record_kind>/<record_id>.json
  history/storage_revisions/...
  derived/...
```

Portia uses Core's public `module_work_dir`, `safe_module_work_descendant`, and
class-module helpers rather than reproducing Core-private path logic.

The workspace-scoped Actor Directory is:

```text
portia/actors/<actor_id>/
  actor.json
  records/<record_kind>/<record_id>.json
  history/storage_revisions/...
```

Actor exceptional-removal certificates survive outside the removable Actor
aggregate:

```text
portia/actor-directory-removals/<removal_id>.json
```

Workspace-scoped operation journals use the accepted explicit revision series:

```text
portia/operations/<operation_id>/
  revisions/<journal_revision>.json
  current.json
```

Quarantine and finding-suppression state use the same immutable-revision plus
explicit-current-pointer pattern. Finding Acknowledgements are append-only
single records. Integrity Findings remain derived diagnostics and have no
invented canonical finding path.

## Repository facade

`PortiaRepository` is the ordinary canonical-record persistence boundary. It
provides strict load, exclusive create, and expected-state guarded replacement
for:

- Event and Support Process work roots;
- work-owned child records;
- Actor roots; and
- Actor-owned child records.

Actor exceptional-removal certificates use exclusive creation through the same
facade.

Later domain services should not implement their own JSON globbing, current
selection, hashing, or direct `os.replace()` calls for these records.

### Strict loads

A load resolves the exact deterministic path, reads exact bytes, parses the
explicit requested contract/version through `portia.models`, and verifies path,
owner, class/work, record ID, and Actor ownership where applicable.

Ordinary loads do **not**:

- trim or normalize payloads;
- migrate historical records;
- follow successors;
- choose a latest contract version;
- repair a current pointer;
- rebuild derived state;
- clear locks; or
- mutate the workspace.

A missing artifact, malformed JSON, schema-invalid record, ownership mismatch,
or conflicting exact identity produces a typed storage error.

## Exclusive create and guarded replacement

New canonical identities are created with filesystem-exclusive creation.
Duplicate identity is a deterministic `PortiaConflictError`; Portia does not
silently overwrite it.

Existing canonical representations require the caller's exact prior
`ContentFingerprint`. Replacement stages target-adjacent bytes, rechecks the
prior fingerprint immediately before publication, publishes one file with
`os.replace()`, and read-backs the exact resulting bytes.

Before an accepted canonical representation is replaced, its exact prior bytes
are retained in a private technical storage-history path keyed by SHA-256. This
history supports recovery and diagnosis; it is **not** a new public domain
revision contract and does not replace lifecycle, Amendment, correction,
migration, or supersession records.

Portia therefore preserves the distinction:

```text
technical storage revision != domain history
```

## Deterministic serialization and fingerprints

Canonical storage uses deterministic UTF-8 JSON with:

- sorted object keys;
- compact separators;
- no NaN values;
- one final LF; and
- SHA-256 plus exact byte length for representation fingerprints.

Content fingerprints, operation intent digests, Source Snapshot digests, and
journal revision identity remain different concepts. The Source Snapshot digest
is the accepted logical digest of its normalized inventory; it is not treated as
the hash of the serialized snapshot file.

## Staging and containment

Byte-producing journal steps stage candidates under target-adjacent
`.portia-staging` storage. Replay of the same staged candidate is exact and
idempotent; contradictory bytes for the same staged identity are rejected.

Before destructive or replacement publication, Portia checks resolved runtime
containment so an existing symlink or junction cannot redirect a target outside
the intended workspace boundary. Lexical Core path safety is necessary but not
mistaken for runtime containment against hostile filesystem links.

## Coordinated operations

`OperationJournalStore` persists immutable journal revisions and advances
`current.json` only after the selected revision is durable. The current revision
is never inferred from greatest revision number, timestamp, modification time,
or directory order.

`portia.storage.orchestration` executes the generic byte-publication subset of an
accepted journal:

1. validate exact write-step order and target/path agreement;
2. validate deterministic lock order and lock identity;
3. stage exact intended bytes;
4. acquire all planned locks before canonical mutation;
5. publish each canonical-gate step using its declared action;
6. read back and fingerprint the durable result; and
7. release locks only when the bounded operation reaches a safe conclusion.

The generic publisher supports:

```text
exclusive_create
revision_aware_replace
atomic_pointer_replace
```

Specialized actions such as complete derived installation and Quarantine remain
owned by their typed storage services rather than being smuggled through an
anonymous byte writer.

### Partial success

One-file atomicity is not represented as graph-wide transactionality. If a fault
occurs after one or more canonical steps have been accepted, Portia raises a
structured `PortiaOperationPartialCommitError` containing exact accepted-step and
held-lock evidence. Accepted canonical bytes are preserved; Portia does not
pretend to roll them back by deletion.

If failure occurs before canonical mutation, partially acquired locks can be
released safely because no accepted domain result needs recovery protection.

## Locks

Lock IDs are deterministic SHA-256 identities over canonical compact JSON
containing `lock_scope` and `protected_target`. Issue #38 verifies this algorithm
against the accepted Issue #13 work-lock fixture.

The journal must agree with the recomputed lock ID, lock path, protected target,
and owning operation. All planned locks are acquired before canonical mutation.
Actor-aware operations preserve the accepted Actor-directory total order; other
operations preserve the accepted scope/key ordering.

Lock age, file modification time, process absence, or elapsed wall time never
proves that a lock is stale. Takeover or clearing requires explicit recovery
evidence and exact fingerprint protection.

## Recovery

Normal reads never repair state. `OperationRecovery` and revision-series
recovery are explicit entry points.

Recovery inspects exact selected pointers, immutable revisions, canonical bytes,
recorded result fingerprints, and locks before deciding whether continuation is
safe. A uniquely evidenced linear orphan successor may be selected explicitly;
Portia never chooses the numerically greatest revision merely because
`current.json` is missing. Branching or contradictory history remains ambiguous
and blocks automatic repair.

Committed-operation reconciliation verifies that every recorded durable result
still exists at the exact path with the exact fingerprint. Restart replay checks
those facts before deciding whether a write remains outstanding.

## Quarantine and finding administration

Quarantine remains a protective operational state, not lifecycle. Active
Quarantine can block bounded current use, work/class/Actor writes, operation
completion, or derived-projection use according to its typed target and effects.
Age, acknowledgement, lock release, or operation completion does not implicitly
release it.

Finding Acknowledgements are append-only. Finding Suppressions are revisioned
and explicitly selected. Neither repairs canonical state or changes the meaning,
severity, or truth of an Integrity Finding.

## Derived generations

`DerivedStore` installs immutable complete generations under the accepted
scope-owned topology:

```text
<scope-derived root>/<projection_kind>/
  generations/<generation_id>/
    metadata.json
    data.json
  current.json
```

Work scope stays under the owning work `derived/` boundary. Class scope stays
under the Core class/module boundary. Workspace scope requires an authoritative
`workspace_id` from an accepted contract; Portia refuses to manufacture one by
hashing or serializing the selected filesystem root.

A generation can become current only after Portia verifies:

- metadata and generation identity;
- projection kind/scope agreement;
- complete validation disposition;
- data artifact path and exact fingerprint;
- Source Snapshot logical digest;
- deterministic/unique source inventory;
- current exact source bytes; and
- guarded current-pointer publication.

Current use follows only `current.json` and rechecks source freshness. Missing,
stale, incompatible, or corrupt derived state is unavailable; it never proves
an empty canonical graph.

Projection-specific semantic builders remain separate from generic storage. For
example, Issue #38 can guarantee that an incoming-reference generation was built
from the declared exact source bytes and was selected atomically, while the
projection builder remains responsible for deriving every semantically required
reverse edge from those sources.

## Issue #22 persistence parity

`portia.storage.issue22_parity` accounts for every Issue #22 scenario that Issue
#37 correctly left outside its in-memory runtime boundary.

Issue #38 fully owns the scenarios whose principal defects are persistence facts:

```text
P22-14
G22-002
G22-003
G22-028
G22-029
G22-036
```

`P22-13` is explicitly shared: #38 supplies rebuildable derived persistence and
source truth, while later retention/custody and projection-product semantics
remain outside this storage layer. Resolver, privacy/export, domain-intent, and
projection-builder cases remain assigned to their later v0.2 services. Foreign
custody verification remains external to Portia authority.

This accounting is intentionally conservative. Storage does not claim to know a
semantic fact merely because it can persist the bytes that will later represent
that fact.

## Public error boundary

Storage failures use typed errors rooted at `PortiaStorageError`, including
not-found, conflict, corruption, ownership, path, lock, recovery-required,
ambiguous-recovery, Quarantine, and partial-commit conditions. Later workflows
should branch on these types rather than parse platform-specific `OSError`
messages.

## Privacy and diagnostics

Canonical paths use opaque identifiers rather than names or behavior semantics.
Operational diagnostics should prefer contract/version, opaque IDs,
workspace-relative paths, revisions, and digests. Storage does not log canonical
payloads by default, add telemetry, or create cloud/network dependencies.

## Explicit non-goals

Issue #38 does not implement:

- Event/Participant teacher entry screens;
- Actor/Core roster resolution;
- Account/Observation or judgment workflows;
- Response/Communication delivery;
- Support/Implementation or Follow-Up workflows;
- timeline/attention product builders;
- deliberate export/privacy workflows;
- Meridian publication;
- paper/OCR/import v0.3 execution;
- institutional backup/retention policy;
- distributed transactions; or
- background repair daemons.

Those later services consume this storage layer; they must not bypass it by
reintroducing direct canonical JSON mutation.
