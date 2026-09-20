# Issue #47 public ownership-correction workflow validation

Corrective Slice 33.2 adds `OwnershipCorrectionWorkflowService` as the bounded
application authority for child work-root correction. It is exported from
`portia.workflows`; the callback-oriented
`ActionOwnershipCorrectionCoordinator` remains internal machinery. The public
surface is limited to exact assessment, correction, and certificate resolution.
It exposes no generic move, copy, relocate, callback, or force API.

## Closed family and work-kind policy

The immutable registry admits only `fidelity@1`, `implementation@1`,
`follow_up@1`, `outcome@1`, `reentry@1`, and `repair@1`. Fidelity and
Implementation accept distinct Support Process roots only. The other four
families accept distinct Event and Support Process roots in all four work-kind
combinations. Each route delegates destination construction, successor
legality, provenance, roster/participant validation, and source lifecycle
transition to the existing family `correct_work_root` implementation.

## Exact preflight and durable evidence

Preflight binds an exact source work-record reference and fingerprint, exact
destination work and candidate identity, current work versions, the closed
family/pair policy, destination absence, Quarantine, fresh Integrity state,
complete canonical incoming-reference discovery, and all relevant Dependency
declarations. Missing, stale, malformed, unsupported, or blocking authority
fails before a canonical write.

Callers disposition every discovered incoming reference and Dependency by its
privacy-minimal deterministic key. Incoming references are never rewritten.
Required unresolved Dependencies block completion; advisory declarations do
not become required. The accepted keys and disposition codes are persisted in
bounded `operation_journal@2` intent facts. The journal stores no referenced
payload and no absolute host path.

## Certificate, lifecycle, and recovery

The shared ownership coordinator now journals the destination successor,
destination-owned `ownership_correction@2` certificate, source lifecycle
transition, and superseded source revision as one recoverable canonical plan.
The certificate uses `correction_kind=child_work_root`, binds the exact source
and destination endpoints, and agrees with the successor and lifecycle
effective time and agent. A real parent certificate must resolve as an exact
destination-local `ownership_correction@2`; standalone corrections omit it.

The source exact reference continues to resolve the source history. Navigation
to the destination is explicit through successor/certificate evidence. The
generic `RecoveryWorkflowService` classifies and resumes interrupted journal
steps without deleting an accepted destination or certificate. Same-intent
completed replay is idempotent; reused operation, destination, certificate, or
transition identity with contradictory intent fails closed.

## Actor boundary

This service changes work ownership only. It never mutates Actor Directory
identity, merges or splits Actors, or reassigns roster students. Family
validation re-resolves destination participant and roster-scoped facts; it
does not silently retarget them.

## Automated coverage

`tests/test_workflow_ownership_correction.py` covers the public import and
method boundary, the closed six-family registry, all six real family paths,
Event→Support Process, Support Process→Event, Support Process→Support Process,
and distinct Event→Event corrections, v2 certificate persistence, journal v2,
same-intent replay, strict missing-Integrity failure, reference and Dependency
dispositions, byte-for-byte preservation of an incoming exact reference, and
recovery after interruption immediately after certificate publication and
after the source lifecycle write is durable. A synthetic sensitive sentinel
proves that substantive payload text is absent from the certificate, journal
disposition evidence, and public result metadata.

The installed-wheel smoke imports and executes the public service outside the
checkout against Core 0.6.3. It performs the original Event-owned Follow-Up to
Support Process correction and verifies the v2 certificate, active destination,
historically resolvable superseded source, and completed journal v2.

## Deliberate boundaries

Event class-ownership correction is not exposed by this child-family service.
Unsupported families, contract versions, work-kind pairs, unbounded disposition
inventories, incomplete reviews, blocking reference or required Dependency
dispositions, and unavailable Integrity authority require manual correction or
prerequisite repair. No schema, ADR, journal contract, Core floor, or sibling
runtime dependency changes in this slice. Broader final Slice 33 remains paused.
