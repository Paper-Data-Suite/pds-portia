# Issue #21 Targeted Review Findings

**Review baseline:** `05a6e625a8cd5e02701a97850cade3ecfdd0173f`
**Date:** 2026-08-14
**Status:** Reconciliation patch prepared; full local validation required

The targeted post-implementation review found four actionable architecture /
contract defects. None requires reopening the overall ADR 0017 direction.

## R1 — High — Raw source-artifact locators can leak secrets or PII into durable export provenance

`export_source_inventory@1` currently embeds the complete
`source_artifact_ref@1`.

That reference family can contain workspace-relative paths, paper route/page
identifiers, foreign module refs, external system labels, arbitrary
`external_reference` values, and optional external record labels.

An arbitrary external reference can contain signed URLs, capability tokens,
query credentials, names, case identifiers, or other values inappropriate for
durable export audit/provenance.

This conflicts with Issue #21's privacy-minimal audit requirement and its
explicit prohibition on secrets/capability tokens in IDs or provenance.

### Reconciliation

`source_artifact` inventory entries no longer persist the raw locator.

They instead bind:

```text
artifact_kind
artifact_identity_algorithm = portia_source_artifact_identity_v1
artifact_identity_digest
representation_digest
byte_length
```

`artifact_identity_digest` binds the canonical exact source-artifact reference
without copying the locator into the deliberate-export receipt.

The exact source reference remains only in the restricted projection/operation
material required to verify that digest and source authorization.

## R2 — High — Focal export identity is not constrained to an actual work participant

The first implementation used generic `exact_portia_work_record_ref@1` for
`focal_subject_ref`.

That permits a structurally valid focal reference to an Account, Observation,
Communication, or other non-participant child record.

It also permits focal purposes with class/workspace/source-set export scope even
though the focal reference is work-local.

### Reconciliation

Issue #21 v1 now makes these deliberate-export purposes exact-work scoped:

```text
participant_specific
student_facing
family_facing
```

For those purposes:

```text
export_scope.scope = work
focal_subject_ref is required
```

and the focal subject must resolve structurally as either:

```text
Event -> event_participant
Support Process -> support_process_participant
```

Broader class/workspace student/family export is deferred until Portia has an
accepted stable focal identity contract appropriate to cross-work scope.

## R3 — Medium-high — `explicit_source_set` scope was not immutable enough for historical exact-scope binding

The first contract stored only `scope_id` for an explicit source set.

If the definition behind that ID changed, the historical export receipt could no
longer prove exactly which source-set definition was requested, especially
because the privacy-minimized source inventory intentionally omits
withheld/unavailable source identities.

### Reconciliation

An explicit source set now requires:

```text
scope_id
scope_version
scope_algorithm = portia_export_scope_set_v1
scope_digest
```

The digest binds the exact immutable source-set definition used by the export.

## R4 — Medium — Projection-decision digest lacked an algorithm/version identity

The first contract stored `projection_decision_digest` without identifying the
versioned decision-manifest canonicalization used to produce it.

That weakens future verification if the internal decision representation
evolves.

### Reconciliation

`deliberate_export@1` now also requires:

```text
projection_decision_algorithm = portia_projection_decision_v1
```

Any incompatible decision-manifest/canonicalization change requires a new
algorithm identifier rather than silently reinterpreting an old digest.

## Review disposition

```text
R1: patch required
R2: patch required
R3: patch required
R4: patch required
```

The public contract names and `pexp_` identifier remain unchanged.

ADR 0017 remains directionally valid; the patch tightens privacy and exact
historical binding before merge.
