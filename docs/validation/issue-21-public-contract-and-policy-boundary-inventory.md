# Issue #21 Public Contract and Policy Boundary Inventory

**Status:** ADR-acceptance inventory
**Date:** 2026-08-14

## New public contracts

Issue #21 introduces exactly three public contracts:

| Contract | Version | Purpose |
| --- | --- | --- |
| `portia_deliberate_export_id` | `1` | opaque identity for one immutable deliberate-export provenance record |
| `export_source_inventory` | `1` | privacy-minimized exact contributing-source representation inventory |
| `deliberate_export` | `1` | immutable provenance for one accepted deliberate output artifact |

New identifier prefix:

```text
pexp_
```

## Existing contracts intentionally reused

Issue #21 reuses, among others:

```text
operation_journal_ref@1
attribution_agent@1
exact_portia_work_ref@1
exact_portia_work_record_ref@1
module_work_record_ref@1
source_artifact_ref@1
workspace_relative_path@1
sha256_digest@1
explicit_offset_timestamp@1
statement_of_disagreement@1
exceptional_removal@1
source_snapshot@1
derived_index_metadata@1
```

## Existing contracts intentionally not widened

```text
source_snapshot@1
derived_index_metadata@1
communication@1
actor@1
actor_contact_point@1
actor_student_relationship@1
statement_of_disagreement@1
exceptional_removal@1
operation_journal@1
```

Issue #21 adds policy/application rules around those contracts without changing
their published `$id` meanings.

## Concepts deliberately not made Portia public contracts

```text
privacy projection record
student profile
family profile
canonical student history
Portia privacy request case
Portia legal hold
Portia retention policy
institution destruction authorization
routine disposition certificate
Sunset adapter protocol
Sunset plan
Sunset cross-module result
disclosure record
delivery/receipt/read record
```

These are either derived, externally authoritative, future suite-shared, or not
yet justified as durable Portia records.

## Stable Portia retention classes

```text
canonical_behavior_support
source_evidence
actor_identity
actor_contact
lifecycle_correction_disagreement
paper_import_provenance
operation_recovery_integrity
derived_cache
export_bytes
export_provenance
exceptional_removal_certificate
```

These are semantic policy-mapping keys, not legal durations.

## Unresolved institutional-policy dependencies

Portia intentionally requires authoritative external inputs for:

```text
requester authentication
recipient authorization
parent/guardian/custody/eligible-student determination
legitimate educational interest
FERPA/state/district legal interpretation
retention schedule/profile selection
record-series mapping
external trigger dates owned by the institution
legal/litigation/preservation holds and releases
destruction approval
disclosure-log requirements
special-education/civil-rights process holds
backup/archive purge requirements
external-copy destruction verification
secure-media destruction requirements
```

Portia must not guess these.

## Future suite-protocol dependencies

The final shared retention/disposition adapter protocol remains unresolved.

Likely shared concepts include:

```text
adapter protocol version
module capability negotiation
custody item envelope
external policy/authorization reference
hold/preservation input
candidate action
candidate validation result
dry-run plan item
module execution result
foreign-custody result
cross-module recovery state
minimal disposition evidence
```

These should be decided by future Core/Sunset suite architecture rather than
published prematurely under Portia.

## Responsibility summary

```text
Portia:
  semantic meaning
  projection/redaction floor
  deliberate export provenance
  semantic retention classes
  module-owned custody/dependencies/blockers
  module mutation + verification

Core/shared:
  workspace/class/roster identity
  module-qualified references
  PDS2/retained-source infrastructure
  possible future shared adapter mechanics

Institution/deployment:
  legal/policy interpretation
  authentication/authorization
  holds
  retention schedule mapping
  destruction approval
  disclosure-log/external-copy policy

Future Sunset:
  cross-module dry-run planning
  safe ordering
  module fan-out
  progress/recovery coordination
  bounded cross-module results
```
