# Portia Future Sunset Retention-Adapter Boundary

**Status:** Issue #21 Slice 6 architecture
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Date:** 2026-08-14
**Wire-contract status:** No Portia-only suite adapter schema is published by this slice.

## 1. Decision

Portia defines the **capabilities it must expose** to a future suite-level
retention/disposition orchestrator.

It does not define the final suite protocol, does not import a nonexistent
`pds-sunset` package, and does not grant an orchestrator semantic authority over
Portia records.

The conceptual boundary is:

```text
institution-approved policy/decision
        |
        v
future Sunset-like orchestrator
        |
        +--> asks each module for owned custody + safe capabilities
        +--> builds dry-run plan
        +--> asks each module to validate exact candidate action
        +--> asks each module to execute only its own custody
        +--> records bounded verification / unresolved external state
```

## 2. Sunset does not exist yet

As of the Issue #21 checkpoint, there is no `pds-sunset` repository in the
Paper Data Suite organization.

Therefore Issue #21 must not create:

```text
from pds_sunset import ...
sunset_client
sunset_database
sunset_config
```

or make Portia depend on an API that has not been accepted.

## 3. Portia semantic authority remains local

Only Portia can authoritatively explain:

```text
what a Portia record kind means
which records are canonical
which state is derived
which state is recovery/integrity evidence
which correction/supersession relationships matter
which retained source is foreign custody
which module-local actions are technically supported
which module-local conditions make an action unsafe
```

A future orchestrator must not infer those facts from directory names, file
extensions, path prefixes, timestamps, record age, filename patterns, guessed
JSON fields, or human-readable labels.

## 4. Institution policy remains external

Neither Portia nor Sunset should decide:

```text
legal retention duration
whether a legal hold exists
whether a requester is entitled
whether a district approved destruction
whether a backup must be purged
whether external disclosure copies must be recalled
```

Those decisions arrive as externally authoritative policy/decision inputs.

## 5. Conceptual adapter identity

A future Portia retention adapter should identify:

```text
module_id = portia
adapter_protocol_version
module_adapter_version
supported_capabilities
```

The distinction matters:

```text
shared protocol version != Portia adapter implementation version
```

The shared protocol may later belong in Core or another suite-shared package.

## 6. Required Portia capability families

Portia must eventually be able to provide capabilities equivalent to:

```text
enumerate_owned_custody
classify_owned_custody
describe_dependencies
describe_trigger_facts
describe_supported_actions
evaluate_module_blockers
validate_candidate_action
execute_module_action
verify_module_action
describe_unresolved_foreign_custody
```

These are conceptual capabilities, not accepted Python method names.

## 7. `enumerate_owned_custody`

For an exact bounded scope, Portia should be able to enumerate custody it owns.

Categories include canonical domain records, source evidence, Actor identity and
contact data, correction/disagreement history, paper/import provenance,
operation/recovery/integrity state, derived caches, deliberate export bytes and
provenance, Exceptional Removal certificates, and transient staging when still
present.

The result must distinguish owned custody from referenced foreign custody.

## 8. Custody item identity

Each enumerated owned item needs an exact semantic identity sufficient for later
validation.

Conceptually:

```text
module_id
custody_kind
retention_class
semantic_ref
contract/version where applicable
current representation identity
owned artifact identity/path where applicable
```

Path alone is never semantic identity.

A digest alone is never semantic identity.

## 9. `classify_owned_custody`

Portia maps owned items to:

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

The adapter must not return an institution-specific duration as though it were
Portia domain truth.

## 10. `describe_dependencies`

Portia must expose disposition-relevant relationships such as supersession,
invalidation, Amendment, Statement of Disagreement, Ownership Correction,
Record Migration, Dependency records, Exceptional Removal certificate
relationships, operation/recovery requirements, export receipt-to-bytes
relationships, derived-cache-to-source relationships, and paper/import
provenance-to-canonical-result relationships.

Dependency descriptions must be able to distinguish concepts equivalent to:

```text
must_preserve_together
must_order_before
must_order_after
reference_only
foreign_owner
rebuildable_dependency
recovery_blocker
```

The final shared vocabulary is deferred.

## 11. `describe_trigger_facts`

Portia may expose exact observable facts accepted in Slice 5:

```text
record_created
record_updated
work_closed
support_process_completed
actor_inactivated
contact_point_inactivated
operation_terminal
export_generated
export_superseded
exceptional_removal_effective
```

The adapter must not fabricate externally owned facts such as graduation or
institution departure.

## 12. `describe_supported_actions`

An adapter can advertise technical support for actions such as:

```text
no_action
delete_derived_cache
delete_export_bytes
delete_transient_staging
archive_to_historical_custody
routine_dispose_operational_payload
routine_dispose_canonical_payload
```

Advertising support means Portia knows how to perform the action safely when
authorized. It does not establish eligibility, authorization, or legal
correctness.

## 13. Exceptional Removal is not a generic adapter action

`exceptional_removal@1` remains its own narrow semantic workflow.

A future shared adapter must not advertise a generic
`exceptionally_remove_anything` capability.

Routine records disposition and Exceptional Removal remain separate paths.

## 14. `evaluate_module_blockers`

Portia must independently surface blockers such as:

```text
in-progress operation
required recovery evidence
unresolved quarantine
relevant active integrity finding
unknown current representation
incomplete correction/dependency graph
required disagreement dependency
foreign custody needed for safe plan
missing source representation
partial prior disposition
unsupported contract version
```

A suite orchestrator cannot override these merely because an external policy
says the record is eligible.

## 15. Candidate evaluation

For each proposed action, the orchestrator conceptually supplies:

```text
candidate identity
requested module action
external policy identity/version/digest
external authorization identity/version/digest
applicable hold/preservation decisions
trigger facts relied upon
plan identity
```

Portia returns a result equivalent to:

```text
valid_for_execution
blocked
unresolved
unsupported
stale_candidate
```

A candidate is stale if current custody or required source state changed after
the dry-run plan was built.

## 16. Dry-run plan

A future Sunset-like orchestrator must support dry-run planning before mutation.

A dry-run plan should distinguish:

```text
candidate
not_yet_eligible
eligible_pending_authorization
blocked
unresolved
unsupported
foreign_owner_action_required
```

A plan is not itself execution authorization unless the authoritative external
decision explicitly makes it so and the exact candidate remains valid.

## 17. No path-driven deletion

Sunset must never execute logic equivalent to deleting files because a path is
old enough or because a filename happens to match a student identifier.

All destructive work must flow through module semantic identity and module-owned
validation/execution.

## 18. Execution ownership

The orchestrator coordinates.

The module mutates.

```text
Sunset selects candidate
-> Portia validates exact current state
-> Portia acquires required operation/recovery controls
-> Portia performs its own action
-> Portia verifies its own result
-> Sunset records bounded cross-module outcome
```

Sunset should not directly unlink Portia canonical files.

## 19. Portia Operation Journal reuse

Where a Portia disposition action changes durable Portia custody, Portia should
reuse its accepted operation/recovery architecture.

Conceptually:

```text
preflight
-> exact expected state
-> Operation Journal
-> locks where needed
-> staged mutation
-> read-back/absence verification
-> derived cleanup
-> commit
```

The exact new operation kinds, if needed, belong to later implementation work.

Issue #21 does not mutate the current Operation Journal schema merely to predict
future runtime operation kinds.

## 20. Cross-module ordering

A Portia Page Record never authorizes deletion of a Core retained scan.

A Portia disposition never rewrites or removes a sealed Vitrine copy.

Export bytes may be disposed before export provenance if policy permits, but
surviving provenance must truthfully reflect later artifact unavailability
through a future disposition-evidence mechanism rather than by rewriting the
historical export receipt.

## 21. Foreign custody result

For referenced custody outside Portia, a future orchestration result needs
concepts equivalent to:

```text
owner_module
exact foreign reference when safely available
required action or confirmation
status
```

Status must distinguish:

```text
not_requested
action_required
pending
completed_verified_by_owner
unresolved
outside_suite_control
```

Portia itself must not assert `completed_verified_by_owner`.

## 22. Partial cross-module success

Cross-module disposition cannot be assumed atomic.

If Portia local deletion succeeds while a required Core action fails, the plan
must preserve both results separately.

Do not reconstruct successfully deleted Portia content merely to simulate
rollback across modules.

## 23. Recovery after interruption

A future orchestrator must be restartable.

On restart it must reload the exact plan revision, ask each module to reconcile
its own prior action, distinguish not-started/committed/partial/blocked/
unresolved states, revalidate remaining candidates, never infer success from a
missing file, and never blindly replay a destructive action.

## 24. Verification semantics

Portia may verify only Portia-owned custody.

It cannot verify district backups, email attachments, downloaded copies,
Core-owned files without Core results, Vitrine copies without Vitrine results,
or external submissions.

## 25. Minimal disposition evidence

Future shared evidence should prefer:

```text
module
semantic custody identity
action
plan/decision identity
result
verification status
time
operation reference where applicable
```

It should avoid student names, Account quotes, Communication summaries, Contact
Point values, source file contents, and hidden privacy-decision payloads.

Whether Portia persists a routine disposition receipt is deferred until the
suite-level protocol is accepted.

## 26. Shared-protocol candidates

Likely suite-shared concepts include:

```text
adapter protocol version
custody item envelope
retention class mapping interface
external policy/decision reference envelope
hold/preservation input envelope
candidate action envelope
candidate validation result
dry-run plan item
module execution result
foreign-custody status
cross-module plan/recovery state
minimal disposition evidence
```

Issue #21 intentionally does not publish these under Portia's schema namespace.

## 27. Likely Core boundary

Core may eventually own shared mechanics such as module identity,
adapter discovery/registration, capability version negotiation, and shared
reference envelopes.

Core should not become institution retention-policy authority, legal-hold
adjudicator, destruction-approval authority, or module-domain semantic
interpreter.

## 28. Likely Sunset boundary

A future `pds-sunset` would own orchestration concerns such as:

```text
policy-fed cross-module inventory
dry-run planning
plan revision
safe ordering
fan-out to module adapters
cross-module progress
restart/recovery coordination
bounded results
reporting unresolved/outside-control custody
```

It would not own Portia record semantics.

## 29. Portia boundary

Portia owns custody enumeration, retention classification, correction/dependency
truth, supported actions, blocker evaluation, exact-state validation, mutation,
verification, and operation/recovery evidence for Portia-owned custody.

## 30. Slice 6 decision summary

No `pds-sunset` dependency is added.

No existing Portia public schema is widened.

No suite-standard adapter schema is prematurely published in the Portia
namespace.
