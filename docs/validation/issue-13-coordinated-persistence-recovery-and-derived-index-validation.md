# Issue #13 Validation: Coordinated Persistence, Recovery, and Derived-Index Contracts

**Status:** Accepted implementation record
**Issue:** #13
**ADR:** [`ADR 0009`](../decisions/0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md)
**Design:** [`Coordinated Persistence, Recovery, and Derived-Index Contracts`](../design/portia-coordinated-persistence-recovery-and-derived-index-contracts.md)
**Examples:** [`Machine-readable manifest`](../examples/issue-13/manifest.json)
**Application-invalid matrix:** [`issue-13-application-invalid-matrix.json`](issue-13-application-invalid-matrix.json)

## Accepted public contract inventory

Issue #13 adds 25 independently cataloged version-1 public contracts.

### Identifiers

```text
portia_operation_id
portia_operation_step_id
portia_lock_id
portia_quarantine_id
portia_finding_acknowledgement_id
portia_finding_suppression_id
portia_derived_generation_id
```

### Common and references

```text
workspace_relative_path
sha256_digest
content_fingerprint
operation_ref
operation_journal_ref
quarantine_ref
derived_generation_ref
```

### Durable operational records

```text
operation_journal
operation_current_pointer
operation_lock
quarantine_record
quarantine_current_pointer
finding_acknowledgement
finding_suppression
finding_suppression_current_pointer
```

### Derived-generation records

```text
source_snapshot
derived_index_metadata
derived_current_pointer
```

Every contract uses a path-matching immutable `$id`, appears in
`schemas/schema-catalog.json`, and resolves through the offline test registry.
No Issue #12 public schema was modified in place.

## Fixture and example coverage

The Issue #13 fixture tree contains:

```text
23 structurally valid fixtures
44 structurally invalid fixtures
23 structurally valid application-invalid fixtures
```

The comprehensive matrix contains 23 entries and covers every
application-invalid fixture exactly once. Each entry records the contract,
version, schema path, stable rule ID, operation family, and violated invariant.

The public example manifest contains 11 representative machine-readable examples
covering journals, pointers, locks, Quarantine, finding administration, source
snapshots, immutable generation metadata, and derived current selection.

## Structural versus application validation

JSON Schema establishes closed envelopes, required fields, identifier and path
syntax, exact reference shapes, digest and fingerprint representation, operation
and step vocabularies, state-dependent structural branches, Quarantine and
suppression states, projection families, and minimal current pointers.

Application validation remains responsible for:

```text
workspace containment and symlink safety
exact byte and digest truth
identity-derived storage agreement
intent and source-snapshot digest construction
journal and revision-chain linearity
monotonic operation progress and legal state transitions
exact replay and contradictory replay
contiguous unique write and lock ordering
lock conflict detection, ownership, and conservative clearing
expected-prior-state and immediate precommit revalidation
operation-specific canonical ordering and acceptance
partial-success reconciliation, compensation, and recovery safety
Quarantine applicability and release requirements
finding/evaluation compatibility and suppression eligibility
authorization and privacy-minimized evidence
source completeness, deterministic ordering, and changed-during-rebuild detection
generation/data fingerprint verification and complete installation
pointer/generation kind and scope agreement
freshness and current-use eligibility
```

Schema-valid does not mean operation-safe.

## Issue #12 compatibility

The implementation retains Event v2, Event Participant v3, Event Participant
Role v3, Work Relationship v2, Lifecycle Transition v1, Lifecycle-History
Correction v1, Amendment v1, Statement of Disagreement v1, Dependency v1,
Record Migration v1, Ownership Correction v1, Exceptional Removal v1, and
Integrity Finding v1 unchanged.

Integrity Finding v1 remains wire-compatible because its operation target uses a
structurally safe external identifier, and every `op_` identifier satisfies that
contract. Portia does not add `operation_id` to every canonical domain record.

## Final sibling-repository drift check

| Repository | Immutable anchor | Classification | Result |
| --- | --- | --- | --- |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | documentation reconciliation | No change from the accepted v0.6 operational baseline; no Portia contract change. |
| `pds-meridian` | `44778d43b13b8c5f66b9adc24a6674692816300f` | future integration concern | Typed evidence inventory reinforces exact provenance and projection boundaries; no Portia adapter or contract change. |
| `pds-vitrine` | `840cf492b3503d5d6eba77c7ca2130cf21125d0c` | future integration concern | Regulated Portfolio design reinforces immutable evidence and workflow history; no automatic Portia eligibility or contract change. |

## Production handoff

Issue #13 defines architecture and public contracts only. A later executable
milestone owns Python models, path services, strict writers, staging, lock
acquisition and clearing, orchestration, recovery execution, Quarantine
enforcement, projection builders, integrity scans, and teacher-facing
maintenance workflows.

## Repository acceptance commands

From the repository root:

```powershell
python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"

git diff --check
git status --short
```

Acceptance requires the complete offline schema suite to pass with no unresolved
`$ref`, duplicate `$id`, catalog mismatch, invalid public example, matrix gap,
stale Issue #13 documentation, or broken relative link.
