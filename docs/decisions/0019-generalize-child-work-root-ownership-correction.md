# ADR 0019: Generalize Child Work-Root Ownership Correction

- **Status:** Accepted
- **Date:** 2026-09-19
- **Decision owners:** Portia maintainers
- **Related issue:** `#47 — Implement lifecycle, amendment, disagreement, correction, and exceptional recovery services`
- **Builds on:** ADR 0008, ADR 0009, ADR 0014, and ADR 0015
- **Preserves:** immutable published schemas; exact historical references; Event-only class-ownership correction; explicit successor and lifecycle evidence

## Context

The published `ownership_correction@1` certificate is Event-oriented. Its child
endpoints narrow the shared exact work-record reference to Event roots, and its
destination-owned envelope requires an Event ID. Later accepted workflows
correct child ownership between exact Event and Support Process roots. In
particular, Follow-Up, Outcome, Reentry, and Repair support cross-kind moves,
while Implementation and Fidelity support corrections between distinct Support
Process roots. Their operations preserve the source, create a destination
successor, use `work_root_corrected`, and journal `correct_ownership`.

Those are ownership-correction semantics, not representation-only migration or
ordinary semantic correction. Version 1 cannot truthfully certify every
accepted destination.

## Decision

Publish additive `ownership_correction@2`. Version 1 is immutable historical
read authority. Version 2 is current write authority for every new ownership
correction; readers do not infer or upgrade versions.

Version 2 adds required top-level `work_kind`. Together, `class_id`, `work_id`,
and `work_kind` unambiguously name the destination containing work. The work ID
is conditionally validated as an Event ID or Support Process ID. Application
validation requires this envelope scope, the destination endpoint, and the
canonical destination storage path to agree. The certificate is stored once
beneath the destination work root; it is not copied beneath the source.

`event_class_ownership` remains restricted to exact Event-work endpoints and an
Event destination. `child_work_root` uses the existing unrestricted
`exact-portia-work-record-ref` for both endpoints. Its schema can express
Event→Event, Event→Support Process, Support Process→Event, and Support
Process→Support Process pairs, but application policy still closes each record
family's supported pairs.

The reason vocabulary retains all v1 codes and adds `wrong_work_root` for the
common neutral cross-kind case. `wrong_event_root` remains available for
Event-specific history. The source and destination endpoint kinds must match.
Application validation continues to require the same semantic record family,
a changed exact ownership identity, any family-required fresh destination
identity, exact resolution, complete successor/lifecycle reconciliation, and no
silent incoming-reference retargeting.

`parent_correction`, when present, is an exact local
`ownership_correction@2` reference. It is valid only when a real v2 parent
certificate governs the child mapping, normally beneath the same destination
scope. Standalone child moves do not fabricate a parent. Exact historical v1
references remain v1 references.

The certificate records only exact source/destination ownership lineage.
Dependency and incoming-reference discovery and disposition remain coordinated
operation/application responsibilities. Version 2 does not create a batch
certificate or filesystem-move authority.

## Compatibility audit

| Family | Accepted source/destination work kinds | Successor reference | Lifecycle reason | Operation kind | v2 certificate |
| --- | --- | --- | --- | --- | --- |
| Fidelity | Support Process→Support Process | exact cross-root `fidelity@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |
| Implementation | Support Process→Support Process | exact cross-root `implementation@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |
| Follow-Up | Event↔Support Process and same-kind distinct roots | exact cross-root `follow_up@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |
| Outcome | Event↔Support Process and same-kind distinct roots | exact cross-root `outcome@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |
| Reentry | Event↔Support Process and same-kind distinct roots | exact cross-root `reentry@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |
| Repair | Event↔Support Process and same-kind distinct roots | exact cross-root `repair@1` work-record ref | `correction/work_root_corrected` | `correct_ownership` | yes |

The generic work path service derives canonical paths from class and work ID and
already supports both typed work kinds. No path-contract change is required.

## Rejected alternatives

- Mutating v1 would break immutable published history.
- Reclassifying these operations as migration would falsely claim stable work
  ownership and logical identity.
- Treating them as ordinary semantic correction would omit the ownership,
  successor, and incoming-reference boundary.
- Omitting the certificate would leave accepted coordinated operations without
  durable ownership lineage.
- Treating a filesystem move as authority would destroy exact source history.

## Consequences

Runtime coverage, the model registry, catalog, and installed contract bundle
must expose both versions. New writers select v2 explicitly. The public
ownership-correction workflow facade, certificate persistence, and complete
Dependency/incoming-reference execution remain deferred to the resumed Issue
#47 implementation slice.
