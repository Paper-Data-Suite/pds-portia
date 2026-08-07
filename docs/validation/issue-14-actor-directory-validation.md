# Issue #14 Validation: Actor Directory Domain Model and Lifecycle

**Status:** Accepted implementation record
**Issue:** #14
**ADR:** [`ADR 0010`](../decisions/0010-define-actor-directory-domain-model-and-lifecycle.md)
**Design:** [`Actor Directory Domain Model and Lifecycle`](../design/portia-actor-directory-domain-model-and-lifecycle.md)
**Examples:** [`Machine-readable manifest`](../examples/issue-14/manifest.json)
**Application-invalid matrix:** [`issue-14-application-invalid-matrix.json`](issue-14-application-invalid-matrix.json)
**Acceptance matrix:** [`issue-14-acceptance-matrix.json`](issue-14-acceptance-matrix.json)

## Accepted public contract inventory

Issue #14 adds **22 independently cataloged public contract versions**.

### New Actor Directory identifiers

```text
portia_actor_contact_point_id@1
portia_actor_student_relationship_id@1
portia_actor_roster_student_collision_id@1
```

The existing `portia_actor_id@1` contract remains unchanged.

### Exact references and target composition

```text
exact_actor_ref@1
exact_actor_contact_point_ref@1
exact_actor_student_relationship_ref@1
exact_actor_roster_student_collision_ref@1
exact_actor_directory_record_ref@1
actor_target@1
```

The existing identity-only `actor_ref@1` remains unchanged. Exact references add
the expected public contract version and never silently follow correction,
consolidation, splitting, supersession, or migration.

### Canonical Actor Directory records

```text
actor@1
actor_contact_point@1
actor_student_relationship@1
actor_roster_student_collision@1
actor_directory_lifecycle_transition@1
actor_directory_lifecycle_history_correction@1
actor_directory_amendment@1
```

### Migration and exceptional removal

```text
actor_directory_record_migration@1
actor_directory_exceptional_removal@1
```

These contracts reuse the existing scope-neutral `mig_` and `rmv_` identifier
families without modifying the published class/work-scoped schemas.

### Additive Actor-aware operational versions

```text
integrity_finding@2
operation_journal@2
operation_lock@2
quarantine_record@2
```

Their published version-1 schemas remain cataloged and unchanged. Current
pointers, operation references, finding administration, source snapshots,
derived-generation metadata, and derived current pointers remain compatible
without new versions.

Every new public contract uses a path-matching immutable `$id`, appears in
`schemas/schema-catalog.json`, and resolves through the offline schema registry.

## Fixture and example coverage

The complete Issue #14 fixture tree contains:

```text
26 fixture manifests
124 structurally and application-valid fixtures or bounded examples
220 structurally invalid fixtures
157 structurally valid application-invalid fixtures or bounded examples
```

The application-invalid matrix contains **157 entries** and covers every
Issue #14 `application-invalid` artifact exactly once. Each public-contract
entry records the contract, version, schema path, stable rule ID, operation
family, and violated invariant. The eight illustrative projection-data entries
are explicitly marked as application-validated artifacts without a new public
wire contract.

The public example manifest contains **18 synthetic machine-readable examples**
covering:

```text
Actor roots
duplicate consolidation
conflated-person splitting
Contact Points
Actor-to-Student Relationships
Actor–Roster Student Collisions
lifecycle transition
lifecycle-history correction
amendment
representation migration
exceptional removal
Integrity Finding v2
Operation Journal v2
Operation Lock v2
Quarantine Record v2
source snapshot
derived generation metadata
derived current selection
```

No real student, family, staff, or contact data is included.

## Structural versus application validation

JSON Schema establishes:

```text
closed envelopes and discriminated unions
identifier and exact-reference syntax
contract-version representation
Actor, Contact Point, Relationship, and Collision local shape
bounded source, review, verification, category, status, and reason vocabularies
typed amendment paths and present/absent states
lifecycle and history-correction evidence shape
migration and removal certificate shape
Actor-aware operation, lock, finding, and Quarantine targets
privacy-reducing omission of prohibited fields
```

Application validation remains responsible for:

```text
canonical path and persisted-identity agreement
Actor-root ownership and child containment
Core class and roster resolution
current-use and contextual authority eligibility
creation, review, verification, effective-period, and update chronology
lifecycle transition legality, chain linearity, branch selection, and reconciliation
duplicate-candidate review and confirmed consolidation topology
conflated-person split completeness
roster-collision evidence and coordinated Actor invalidation
incoming-reference discovery completeness
no silent successor following or reference retargeting
amendment before/after and fingerprint truth
migration semantic equivalence and canonical-path preservation
exceptional-removal ground, authorization, incoming-reference review, and ordering
operation intent, deterministic locks, write order, commit, replay, and recovery
Quarantine applicability and release
derived source completeness, authorization coverage, digest truth, freshness, and installation
privacy-safe operational facts, diagnostics, certificates, and projections
```

Schema-valid does not mean identity-confirmed, authorized, current, complete, or
safe to execute.

## Compatibility record

Issue #14 preserves unchanged:

```text
portia_actor_id@1
actor_ref@1
person_display_snapshot@1
Event v2
Event Participant v3
Event Participant Role v3
Work Relationship v2
Issue #12 class/work-scoped lifecycle, correction, migration, and removal schemas
Issue #13 version-1 operational, finding-administration, and derived-state schemas
```

Roster-student identity remains the exact Core `class_id + student_id` pair.
Portia does not create a suite-wide person reference, infer cross-roster
identity, or make Actor identity portable across teachers or workspaces.

## Final cross-repository drift check

| Repository | Immutable anchor | Classification | Result |
| --- | --- | --- | --- |
| `pds-core` | `6c507213618b68a6dd3ea096e1a898201ff029e6` | no immediate implication | Core remains authoritative for workspace, class, roster, and class-qualified student identity. No Actor contract change or Core expansion is required. |
| `pds-portia` `main` | `d60966f8486bf93fb0185e3662b76d3b79ce9dcb` | implementation baseline | Issue #14 remains based on the accepted Issue #13 implementation with zero branch divergence. |
| `pds-portia` Issue #14 pre-final checkpoint | `92621e1d765583c6dcc46d5d92bb9bd199fdc2bf` | required Actor contract implementation and documentation reconciliation | Fifteen commits ahead of `main`, zero behind; Actor contracts, operations, derived compatibility, and complete schema tests are present before this final integration record. |

No sibling repository introduced a concrete public contract requiring Actor
identity, privacy, or consumer-eligibility changes during the final checkpoint.
Sibling consumption therefore remains a future integration concern rather than
a blocking contract change.

## Acceptance record

[`issue-14-acceptance-matrix.json`](issue-14-acceptance-matrix.json) maps
**41 completed criteria** to concrete schemas, examples, design decisions,
validation artifacts, and tests.

The matrix covers the issue goals for semantic unit, eligibility, roster
exclusion, canonical storage, display and contact boundaries, relationships,
lifecycle, amendment, material correction, duplicate consolidation, splitting,
roster collision, historical references, derived discovery, operational
targeting, migration, removal, privacy, documentation, drift checks, and
production handoff.

## Production and consuming-domain handoff

Issue #14 defines architecture, public contracts, examples, and validation. It
does not implement:

```text
Python Actor repositories
filesystem path services and strict writers
operation execution and recovery services
projection builders and integrity scanners
teacher-facing Actor creation, selection, correction, consolidation, or split UI
contact delivery or verification services
automatic imports or person matching
institutional authorization or identity providers
```

A later executable milestone owns those services.

Later Account, Communication, Support, Follow-Up, Determination, and other
consumer-domain issues may compose exact Actor references. Each consuming record
must retain its own contextual role, authority, purpose, authorization, and
historical display evidence. Actor category or Relationship type must never
supply those consequential claims automatically.

## Repository acceptance commands

From the repository root:

```powershell
python -m unittest `
  tests.schema_validation.test_issue_14_final_integration

python -m unittest `
  tests.schema_validation.test_issue_14_actor_directory_primitives `
  tests.schema_validation.test_issue_14_actor_contract `
  tests.schema_validation.test_issue_14_actor_contact_point_contract `
  tests.schema_validation.test_issue_14_actor_student_relationship_contract `
  tests.schema_validation.test_issue_14_actor_roster_student_collision_contract `
  tests.schema_validation.test_issue_14_actor_directory_history_contracts `
  tests.schema_validation.test_issue_14_actor_directory_migration_removal_contracts `
  tests.schema_validation.test_issue_14_actor_aware_operational_contracts `
  tests.schema_validation.test_issue_14_actor_derived_state_compatibility `
  tests.schema_validation.test_issue_14_final_integration

python -m unittest discover `
  -s tests/schema_validation `
  -p "test_*.py"

git diff --check
git status --short
```

Acceptance requires the complete offline schema suite to pass with no unresolved
`$ref`, duplicate `$id`, catalog mismatch, invalid public example, fixture-matrix
gap, acceptance-matrix gap, privacy leak, stale Issue #14 documentation, broken
relative link, or unexpected schema modification.
