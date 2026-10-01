# Portia module operations

Issue #52 exposes Portia through PDS Core's neutral module-operations v1 contract.

## Installed profile

Portia owns one operations profile:

```text
entry-point group: paper_data_suite.module_operations
entry-point name:  portia
provider:          portia.pds_operations:get_module_operations_profile
contract version:  1
```

The profile identifies the module as `portia` and exposes independent attention and readiness callables. Core remains responsible for provider discovery, request/profile/result validation, capability invocation, and provider-failure isolation.

Portia remains responsible for Portia-specific attention/readiness meaning and for every sensitive read needed to derive those facts.

## Metadata-safe discovery

`portia.pds_operations` is intentionally small. Constructing the profile does not:

- resolve a workspace;
- read class, roster, Portia, export, or student data;
- import Portia menu, storage, or export workflow modules;
- prompt or print normal UI output;
- create or modify workspace state.

The capability callables are lazy seams. The dedicated `portia.attention_provider` and `portia.readiness_provider` implementations are imported only when their respective capability is invoked.

This prevents installed provider discovery from becoming a hidden teacher-data access path or package-initialization dependency cycle.

## Attention adapter

`portia.attention_provider` is a presentation-neutral Core adapter over Issue #49's native `AttentionQueryService`; it is not a second attention engine.

For each Core attention invocation, Portia captures one timezone-aware instant and converts it to the existing `ExplicitOffsetTimestamp` authority. That same `as_of` value is used for the entire native query. Core's optional `active_school_year` passes through unchanged to the native query.

Request scope is exact:

- no `workspace_root` returns bounded `unavailable` and does not resolve environment, saved, default, current-directory, or menu context;
- workspace with no `class_id` maps to `PortiaAttentionScope.workspace_scope()`;
- an explicit `class_id` maps only to `PortiaAttentionScope.class_scope(class_id)` and never widens to workspace scope.

Native Issue #49 summaries remain authoritative for code, label, and count. The shared report exposes only the Core-bounded projection. Exact class/work context is added only when it is truthful for every contributor to that summary. Multi-class or multi-work summaries omit false representative context.

Native partial/unavailable messages are not copied across the boundary. The adapter emits a fixed Portia-owned Core notice vocabulary:

```text
portia_attention_partial
portia_attention_unavailable
```

If a native count exceeds Core's shared count bound, the adapter does not clamp or reinterpret it. That summary is omitted and the shared evaluation is marked partial. Unsupported future native attention codes fail closed rather than being inferred by substring or heuristic.

Unexpected implementation exceptions are not converted into empty attention. They cross the provider boundary so Core can classify `module_operations.provider_failed` without exposing Portia exception text.

### Owner-action references

Each projected attention summary carries one stable opaque Portia-owned `ModuleOwnerActionRef`. The closed mapping is:

```text
portia_follow_up_due / portia_follow_up_overdue
  -> open_complete_follow_up
portia_review_incomplete
  -> open_add_information
portia_support_process_review_due / portia_support_process_review_overdue /
portia_support_process_dependency_attention
  -> open_manage_support
portia_integrity_conflict / portia_integrity_review_required /
portia_recovery_required / portia_quarantine_active / portia_derived_state_stale
  -> open_advanced_tools
```

These values are interoperability identity only. They are not commands, URLs, filesystem paths, callables, serialized menu state, or execution payloads. Issue #52 does not execute owner actions.

The mapping lives in the presentation-neutral attention package. The #50 teacher menu derives its existing routine route table from the same action authority, so menu routing and shared Core projection cannot silently drift while the Core adapter remains independent of `portia.menu`.

## Ownership boundaries

The operations entry point is separate from Portia's existing launcher:

```text
portia = portia.cli:main
```

Issue #52 does not replace launcher identity, introduce a Suite-owned Portia executable, or add a Portia-specific parallel operations protocol.

The runtime dependency remains:

```text
pds-core>=0.6.3,<0.7
```

The exact Core release used for final Issue #52 qualification is a release-evidence decision, not the minimum compatibility declaration.

## Slice status

Slices 1-3 establish the profile/discovery boundary, lazy callable seams, native #49 attention projection, and shared Portia-owned action identity. Portia readiness semantics, installed-wheel acceptance, and closeout qualification are implemented in later Issue #52 slices.
