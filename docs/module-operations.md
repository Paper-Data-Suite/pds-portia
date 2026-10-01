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

Owner-action references are intentionally deferred to Slice 3. Slice 2 projects attention facts only.

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

Slices 1-2 establish the profile/discovery boundary, lazy callable seams, and native #49 attention projection. Owner-action mapping, Portia readiness semantics, installed-wheel acceptance, and closeout qualification are implemented in later Issue #52 slices.
