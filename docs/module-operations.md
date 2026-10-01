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

Slice 1 establishes only the profile/discovery boundary and lazy callable seams. Native #49 attention projection, Portia readiness semantics, owner-action mapping, installed-wheel acceptance, and closeout qualification are implemented in later Issue #52 slices.
