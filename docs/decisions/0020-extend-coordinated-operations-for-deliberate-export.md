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
