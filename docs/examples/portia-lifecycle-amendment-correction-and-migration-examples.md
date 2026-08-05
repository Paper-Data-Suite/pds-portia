# Portia Lifecycle, Amendment, Correction, and Migration Examples

**Status:** Accepted synthetic examples
**Issue:** `#12 — Define shared lifecycle, amendment, correction, and migration contracts`
**Date:** 2026-08-05

These examples illustrate the public wire shapes accepted by ADR 0008. They are synthetic and contain no real student data.

Every machine-readable example is listed in [`issue-12/manifest.json`](issue-12/manifest.json) and is validated against the exact cataloged contract version. Structural validity does not establish authoritative resolution, lifecycle legality, authorization, semantic preservation, successful reconciliation, or safe persistence.

## 1. Lifecycle Transition

[`issue-12/lifecycle-transition.json`](issue-12/lifecycle-transition.json) records a reviewed Event transition from `draft` to `active`.

The canonical Event still persists its current status. The transition is append-only history and must reconcile with that current value.

## 2. Lifecycle-History Correction

[`issue-12/lifecycle-history-correction.json`](issue-12/lifecycle-history-correction.json) selects a corrected transition-history head after a prior history branch recorded the wrong resulting status.

The earlier transitions remain preserved. The correction changes the selected history interpretation rather than rewriting the original chain.

## 3. Amendment

[`issue-12/amendment.json`](issue-12/amendment.json) records a spelling correction to an Event summary with explicit before-and-after values and a target-revision precondition.

The example is nonmaterial. Changing subject, target, source, ownership, status, or substantive meaning would require a successor or another governed correction workflow.

## 4. Statement of Disagreement

[`issue-12/statement-of-disagreement.json`](issue-12/statement-of-disagreement.json) preserves a roster-qualified student's verbatim dispute of attribution.

The Statement of Disagreement is independently attributable and lifecycle-bearing. It does not silently alter, invalidate, supersede, or adjudicate the disputed Event Participant.

## 5. Dependency

[`issue-12/dependency.json`](issue-12/dependency.json) records a required current-use dependency from an Event Participant Role to an Observation.

The Dependency declares an invariant. Whether a particular operation is blocked requires application evaluation of exact resolution, lifecycle, authority, and the consuming record's semantics.

## 6. Record Migration

[`issue-12/record-migration.json`](issue-12/record-migration.json) records an Event representation upgrade from contract version 1 to version 2 under a named transformer.

The work identity and intended semantics remain unchanged. Migration is not permission to repair substantive content or move the record to another work root.

## 7. Ownership Correction

[`issue-12/ownership-correction.json`](issue-12/ownership-correction.json) records an Event whose owning class and canonical work root were wrong.

The destination receives a fresh Event identity under the corrected class. Children, relationships, dependencies, incoming references, lifecycle, and current-use state require coordinated reconciliation; references do not silently retarget.

## 8. Exceptional Removal

[`issue-12/exceptional-removal.json`](issue-12/exceptional-removal.json) records a privacy-governed removal with explicit authorization, salted content evidence, and a bounded lifecycle snapshot.

The certificate retains no removed substantive payload. The removed exact identity remains distinguishable from ordinary absence, invalidation, or supersession.

## 9. Event Participant Version 3

[`issue-12/event-participant-v3.json`](issue-12/event-participant-v3.json) demonstrates a cross-work ownership-correction successor.

Version 3 preserves Participant version-2 subject semantics while replacing same-work predecessor references with complete exact Portia work-record references.

## 10. Event Participant Role Version 3

[`issue-12/event-participant-role-v3.json`](issue-12/event-participant-role-v3.json) demonstrates the corresponding destination Role after a work-root correction.

The destination Role targets a Participant in its destination Event. Cross-root correction therefore coordinates destination Participant and Role records rather than retargeting the predecessor Role.

## 11. Work Relationship Version 2

[`issue-12/work-relationship-v2.json`](issue-12/work-relationship-v2.json) demonstrates a same-identity contract migration from Work Relationship version 1 to version 2.

The source-owned direction and `draws_context_from` semantics remain unchanged. The exact predecessor representation remains visible through `supersedes`.

## 12. Integrity-Finding Projection

[`issue-12/integrity-finding.json`](issue-12/integrity-finding.json) reports a confirmed mismatch between persisted and derived lifecycle status.

The finding is a rebuildable diagnostic projection. It has deterministic keys, explicit effects, exact targets, and bounded evidence, but no canonical record identity or lifecycle.

## Application-Invalid Examples

Structurally valid objects may still violate cross-record or semantic invariants. The comprehensive matrix is:

[`../validation/issue-12-application-invalid-matrix.json`](../validation/issue-12-application-invalid-matrix.json)

The matrix maps every Issue #12 application-invalid fixture to its exact contract version, schema path, and application rule identity. These fixtures must continue to pass JSON Schema while being rejected by application validation.

## Exact Resolution and No Silent Repair

Across all examples:

* contract versions are explicit;
* predecessor and target references identify exact representations;
* migration does not silently correct meaning;
* ownership correction does not silently move or retarget references;
* supersession does not erase predecessors;
* disagreement does not rewrite its target;
* removal does not masquerade as lifecycle deletion;
* and integrity findings do not become canonical history.
