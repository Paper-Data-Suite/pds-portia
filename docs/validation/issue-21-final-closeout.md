# Issue #21 Final Closeout

**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Status:** Implementation architecture complete; ready for review
**Date:** 2026-08-14

## Final local validation checkpoint

The post-ADR maintainer run completed:

```text
Ran 1087 tests in 203.152s

OK
```

with `git diff --check` clean.

Slice 9 changes no public schema and adds no test method, so the expected full
suite count remains 1087.

## Accepted ADR

ADR 0017 accepts the complete Issue #21 architecture.

## Public Issue #21 contract delta

Exactly three public contracts:

```text
portia_deliberate_export_id@1
export_source_inventory@1
deliberate_export@1
```

Exactly one new opaque identifier prefix:

```text
pexp_
```

No previously published `$id` is changed.

## Projection / redaction closeout

Accepted boundaries include:

```text
canonical != projection
projection != export
export != disclosure
purpose/audience != authorization
withheld != absent
unavailable != false/no
redaction != correction
```

Ordinary privacy views remain derived/noncanonical.

No canonical student dossier, student privacy profile, family profile, or
longitudinal behavior-history record is introduced.

Multi-participant identity/content is focalized without falsely rewriting the
native source as a single-person record.

Free text can require manual review; Portia does not silently paraphrase
verbatim source text into supposedly equivalent safe text.

## Export closeout

One deliberate export binds one immutable output artifact and exact
policy/source/decision/output provenance.

`source_snapshot@1` remains unchanged and is not repurposed for outward export.

Export generation does not prove disclosure, delivery, receipt, read, consent,
legal notice, or external acceptance.

Changed source/policy creates a new export; historical exports are not rewritten.

## Retention / request closeout

Portia accepts 11 semantic retention classes but no legal duration.

Retention requires exact trigger facts and external policy/authorization
provenance.

Deletion request remains distinct from destruction authorization.

Outstanding authoritative preservation/hold state blocks destructive action.

Routine retention disposition remains distinct from Exceptional Removal.

Derived caches cannot extend or resurrect lawfully disposed substantive source.

## Core / sibling / Sunset closeout

Core continues to own shared identity/workspace/PDS2 and retained-source
infrastructure.

Each sibling module retains authority over its own canonical custody.

Portia cannot destroy Core/Vitrine/other sibling custody by following a
reference.

No `pds-sunset` repository exists.

A future orchestrator coordinates; Portia validates, mutates, recovers, and
verifies Portia-owned custody.

Cross-module disposition is recoverable/reportable, not falsely atomic.

## Validation assets

Issue #21 includes:

```text
initial architecture/policy checkpoint
complete sensitivity/projection matrix
participant/student/family redaction rules
redaction scenario matrix
deliberate export schemas + valid/invalid/application-invalid fixtures
retention/request/hold design
32 retention/request scenarios
future Sunset adapter boundary
36 Sunset/adapter scenarios
application-invalid matrix
36 runtime failure/recovery cases
24 machine-checked cross-cutting synthetic scenarios
pre-ADR drift checkpoint
accepted ADR 0017
final drift checkpoint
complete acceptance matrix
```

## Acceptance status

```text
acceptance criteria: 58
PASS: 58
PENDING: 0
```

## Intentionally unresolved institutional dependencies

Issue #21 does not guess requester authentication, recipient authorization,
guardian/custody/eligible-student status, legitimate educational interest, legal
interpretation, retention schedule/profile selection, record-series mapping,
institution-owned trigger dates, preservation/legal holds and releases,
destruction authorization, disclosure-log requirements, backup/archive purge
requirements, external-copy destruction, or secure-media destruction.

## Review handoff

The targeted review found four concrete contract-hardening issues. They are reconciled by the pre-merge review patch; the full local suite must be rerun before merge. Review focus remains:

```text
privacy leakage through indirect identifiers/existence/counts
contradictory retention semantics
unsafe cross-module deletion assumptions
Exceptional Removal vs routine-disposition leakage
export-provenance overcollection
manual-review edge cases
application-invariant gaps
schema/test strengthening
README/schema-guide/ADR consistency
```

Any review findings should be reconciled before merge.

Issue #22 remains next for broader representative end-to-end synthetic contract
examples, followed by Issue #23 final foundations architecture audit.
