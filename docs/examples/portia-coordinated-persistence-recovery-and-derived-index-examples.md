# Portia Coordinated Persistence, Recovery, and Derived-Index Examples

**Status:** Accepted
**Issue:** #13
**Machine-readable manifest:** [`issue-13/manifest.json`](issue-13/manifest.json)

These synthetic examples exercise the accepted ADR 0009 wire contracts. They
contain no real student data and do not implement filesystem mutation.

## Coordinated operation and explicit current selection

[`operation-journal.json`](issue-13/operation-journal.json) shows a committed
lifecycle operation whose canonical-gate steps are accepted while an ordinary
derived rebuild remains post-commit. The journal distinguishes exact intent,
preflight, locks, ordered writes, observed durability, canonical acceptance,
commit point, partial state, and recommended completion.

[`operation-current-pointer.json`](issue-13/operation-current-pointer.json)
selects one exact immutable journal revision. It does not repeat operation state
or infer the greatest revision.

## Deterministic locking

[`operation-lock.json`](issue-13/operation-lock.json) is a privacy-minimized
work-scoped lock owned by a stable operation series. Its `lock_` identity is the
SHA-256-derived deterministic lock key. The record has no expiry or heartbeat;
conservative external evidence and exact fingerprint protection are required to
clear it.

## Quarantine without lifecycle rewriting

[`quarantine-record.json`](issue-13/quarantine-record.json) preserves the full
active origin and records explicit release through a later immutable revision.
It does not mutate the target lifecycle or delete the protected record.

[`quarantine-current-pointer.json`](issue-13/quarantine-current-pointer.json)
selects the released revision explicitly.

## Finding review and bounded presentation suppression

[`finding-acknowledgement.json`](issue-13/finding-acknowledgement.json) records
review of one exact finding evaluation. It does not resolve or suppress the
finding.

[`finding-suppression.json`](issue-13/finding-suppression.json) demonstrates a
warning-only, presentation-scoped suppression series with explicit policy,
authorization, expiry conditions, and release evidence. The matching
[`finding-suppression-current-pointer.json`](issue-13/finding-suppression-current-pointer.json)
selects the terminal revision.

## Complete source-bound derived replacement

[`source-snapshot.json`](issue-13/source-snapshot.json) inventories exact
workspace-relative source paths, byte lengths, digests, roles, contracts, scope,
and authorization coverage in deterministic order.

[`derived-index-metadata.json`](issue-13/derived-index-metadata.json) binds one
complete immutable generation to that snapshot, builder, output fingerprint,
validation summary, and generating operation.

[`derived-current-pointer.json`](issue-13/derived-current-pointer.json) selects
one exact generation for one projection kind and scope. It does not claim
freshness or authorization compatibility; consumers must verify those facts.

## Validation boundary

The examples validate structurally against the offline schema catalog.
Application validation must still establish digest truth, exact filesystem
containment, journal and revision linearity, replay equivalence, lock conflicts,
authorization, operation-specific ordering, recovery safety, snapshot freshness,
complete installation, and current-use eligibility.
