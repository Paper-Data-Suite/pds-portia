# ADR 0020: Extend coordinated operations for deliberate export custody

- **Status:** Accepted for Issue #88 implementation
- **Date:** 2026-09-25
- **Preserves:** ADR 0009, ADR 0017, ADR 0018
- **Unblocks:** Issue #51

## Context

`deliberate_export@1` requires an exact `operation_journal_ref` and ADR 0017
requires deliberate export generation to reuse Portia's accepted coordinated
Operation Journal / Lock architecture.

The published operation-journal vocabulary is closed. Versions 1 through 3 do
not contain an operation kind meaning "generate one exact deliberate export".
They also lack an exact deliberate-export operation target and representation
roles for the durable export artifact and its immutable provenance record.

Using `create_record`, `derived_projection`, `transient_artifact`, or
`canonical_domain` would make the durable operational record semantically false.
Using a workspace-wide lock would be unnecessarily broad.

ADR 0009 permits a later record family to introduce a compatible versioned
operation extension. ADR 0018 establishes the precedent that a new truthful
postcondition is added through a new immutable journal version rather than by
changing an already-published schema.

## Decision

Issue #88 publishes:

```text
deliberate-export-ref@1
deliberate-export-target@1
operation_journal@4
operation_lock@3
```

`operation_journal@4` preserves the v3 present/absent result model and adds:

```text
operation kind:
  generate_deliberate_export

operation target:
  deliberate_export

representation roles:
  deliberate_export_artifact
  deliberate_export_provenance

lock scope:
  deliberate_export
```

`operation_lock@3` preserves v2 lock semantics and adds one exact
`deliberate_export` lock scope/target.

One export operation coordinates one exact `pexp_` identity.

The operation uses workspace scope because accepted export custody is
workspace-local, but its primary identity is always the exact deliberate-export
target. Workspace scope is not authorization.

Existing `exclusive_create` remains the intended final-write action. No new
write action is introduced by this decision.

`operation_current_pointer@1` is retained. Its explicit `contract_version`
already identifies the selected immutable journal contract version.

## Representation categories

The accepted export artifact is durable but noncanonical. It is not
`canonical_domain`, `derived_projection`, or `transient_artifact`.

The immutable `deliberate_export@1` JSON is durable export provenance, not
behavior/support domain truth.

Therefore v4 names both durable representations explicitly:

```text
deliberate_export_artifact
deliberate_export_provenance
```

Later Issue #88 slices define application validation, staging, commit ordering,
read-back verification, replay, and recovery.

## Exact journal-reference choreography

The immutable deliberate-export provenance record identifies the exact journal
revision that first establishes the operation as `committed` with both required
export representations accepted.

A later `completed` revision may release locks or record finalization without
rewriting the already-immutable export provenance record.

Therefore:

```text
deliberate_export.operation_journal_ref
    -> exact committed journal revision

operation_current_pointer
    -> may later select a completed revision
```

No "latest revision" inference is introduced.

## Application-validation seam

The v4 deliberate-export family is application-closed more narrowly than the
additive wire schema. Existing operation families remain on their accepted
journal versions; `operation_journal@4` is write authority only for
`generate_deliberate_export`.

A valid generation plan contains exactly two final exclusive-create writes in
this order:

```text
1. deliberate_export_artifact
2. deliberate_export_provenance
```

Both target the same exact `pexp_` identity and both have `must_be_absent`
preconditions. The artifact lives directly beneath:

```text
portia/exports/<pexp_...>/artifact.<format>
```

and the provenance record lives at:

```text
portia/exports/<pexp_...>/export.json
```

The artifact representation uses the operation-level serialization boundary:

```text
portia_deliberate_export_artifact_v1
```

This token is not a media type, file extension, or `deliberate_export@1`
schema version. Issue #51 must bind its renderer to this representation version
when it supplies candidate artifact bytes.

The provenance write reserves the first committed journal revision explicitly
in privacy-minimized selected state:

```text
committed_journal_revision = <positive integer>
```

Pre-commit revisions must reserve a later revision. The committed revision must
equal the reservation. A later completed revision must follow it. The immutable
`deliberate_export@1.operation_journal_ref` names the reserved committed v4
revision, never an implicit current or latest revision.

The journal contains one exact `deliberate_export` lock entry and the durable
lock record uses `operation_lock@3`. Generic lock acquisition and byte
publication remain deliberately disabled for this new family until a later
Issue #88 persistence slice qualifies the execution path.


## Bounded execution seam

The specialized deliberate-export persistence entry point is the only Issue #88
path allowed to execute the v4 export family. Generic coordinated execution
continues to reject direct `operation_journal@4` export publication unless the
specialized caller explicitly enters the internal execution seam.

Execution performs these effects in the journaled order:

```text
1. acquire exact operation_lock@3 for the pexp_ identity
2. exclusive-create artifact.<format>
3. exact read-back of artifact bytes
4. exclusive-create export.json
5. exact read-back of provenance bytes
6. release the exact acquired lock
```

The specialized path revalidates the `deliberate_export@1` candidate before
staging and again before publication. Provenance bytes are canonical JSON bytes
of that exact record. A failure before the first accepted final write releases
the lock. A failure after the artifact becomes durable preserves the v3 export
lock and raises the existing partial-commit recovery signal; it does not delete
the accepted artifact or manufacture rollback.

`OperationJournalStore` now admits application-valid v4 export series while
continuing to prohibit mixed journal contract versions. The immutable export
plan is compared across v4 revisions, so a committed or completed successor
cannot change the export identity, lock plan, preflight, artifact bytes,
provenance bytes, committed-revision reservation, or other immutable write
intent. Revision-local observations and lifecycle state may advance normally.

This slice intentionally does not classify or repair interrupted export state.
Recovery inspection, exact replay, committed/completed reconciliation, and
lock clearing remain later Issue #88 work.

## Compatibility

Published schemas remain immutable:

```text
operation_journal@1/@2/@3
operation_lock@1/@2
deliberate_export@1
export_source_inventory@1
```

Existing operation series are not migrated. Version 3 remains required for
existing canonical-absence series. Version 4 is the deliberate-export journal
family.

## Non-goals

This ADR does not implement teacher export selection, rendering, CSV/HTML/PDF
output, disclosure/delivery, recipient tracking, authorization policy, source
projection, retention/disposition, or external-system synchronization.

## Read-only recovery classification

Recovery inspection for `generate_deliberate_export` is deliberately separate
from recovery mutation. The classifier observes the exact journaled artifact
and provenance paths and compares durable bytes with their exact intended
fingerprints. It reports one of these principal states:

```text
nothing_durable
artifact_only
artifact_mismatch
provenance_only
artifact_provenance_mismatch
exact_both_committed_journal_missing
committed
completed
indeterminate
```

`artifact_only` means the exact artifact bytes are already durable and the
provenance representation is absent. That state is eligible for a later
provenance-only recovery action; it is not permission to regenerate or
overwrite the artifact.

`exact_both_committed_journal_missing` means both exact representations are
durable and parse/reconcile correctly, but the deterministically reserved
committed journal revision is absent. A later recovery slice may reconstruct
only the missing operational revision from already-proven facts.

`committed` requires resolution of the exact journal revision named by
`deliberate_export@1.operation_journal_ref`, and that revision must reconcile
both accepted writes. `completed` may be a later selected revision; the export
record continues to name the original committed revision.

Mismatches, unreadable durable state, invalid exact provenance, broken journal
history, and otherwise ambiguous states fail closed as review-required. This
slice performs no overwrite, deletion, journal repair, pointer repair, lock
clearing, or candidate regeneration.


## Evidence-preserving recovery mutations

Recovery mutation is narrower than recovery classification.

For an exact `artifact_only` state, Portia may create only the missing
`deliberate_export@1` provenance bytes after revalidating the supplied exact
candidate against the journal. The already-durable artifact is neither
regenerated nor overwritten.

For an exact artifact/provenance pair with the deterministically reserved
committed journal revision missing, Portia may construct only that exact next
`operation_journal@4` revision from the existing immutable plan and the proven
durable fingerprints. The reconstructed revision records both final writes as
accepted/verified and advances `operation_current_pointer@1` through the
existing guarded immutable-series mechanism.

If the reserved committed revision already exists as the single exact orphan
successor, recovery validates its immutable plan and exact export reference,
then repairs only the current pointer. It does not create a duplicate revision.

Exact replay is idempotent. Already-correct provenance, committed journals, and
terminal completed state are validated and returned without rewriting durable
export representations.

Artifact mismatch, provenance-only state, provenance mismatch, unexpected
orphan revisions, contradictory candidates, and indeterminate evidence remain
non-mutating recovery-required states.

This slice still does not release preserved export locks or synthesize the
later completed journal revision. Finalization remains a separate recovery
step.


## Post-commit export finalization

A committed deliberate-export operation may be finalized only after the exact
committed revision and immutable export provenance reconcile.

If the exact v3 export lock remains durable from a partial-commit recovery,
finalization requires the caller to supply the matching `operation_lock@3`
record. Portia reconstructs the `HeldLock` from the durable lock bytes and
fingerprint and delegates deletion to the existing guarded
`LockStore.release()` primitive. A mismatched lock is never cleared. A missing
lock is treated as an already-released idempotent state; Portia does not
recreate it merely to release it again.

Lock release precedes recording completed state. Therefore a crash after lock
release but before journal advancement leaves an exact committed operation that
can safely retry finalization.

The completed revision is the exact successor of the reserved committed
revision and preserves the immutable export plan. Advancing
`operation_current_pointer@1` to that later revision does not rewrite
`deliberate_export@1`; its `operation_journal_ref` continues to identify the
historical committed revision that first established both accepted export
representations.

If the completed revision is already durable as the single exact orphan
successor, finalization validates it and repairs only the current pointer.
Repeated finalization of an already-completed exact export is an idempotent
replay and creates no additional revisions.
