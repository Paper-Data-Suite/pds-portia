# Portia Cross-Module Disposition Planning and Recovery

**Status:** Issue #21 Slice 6 architecture
**Date:** 2026-08-14

## 1. Plan lifecycle

Conceptual suite-orchestration states:

```text
draft
evaluated
blocked
ready
executing
partially_completed
completed
completed_with_unresolved_external_custody
failed_recoverable
abandoned
```

These are not Portia canonical domain states.

## 2. Plan revisions are immutable

A material change to scope, policy version, authorization decision, hold set,
candidate set, requested action, or ordering creates a new plan revision.

Do not edit an already evaluated/executing plan in place and reuse stale
validation.

## 3. Candidate snapshot

Every candidate validated for execution must bind enough current-state evidence
to detect drift:

```text
semantic identity
contract/revision identity
representation digest or equivalent current-state token
dependency snapshot identity
validated action
validated_at
```

If current state no longer matches, return `stale_candidate` and require
re-evaluation.

## 4. Safe execution gate

A Portia candidate enters execution only when all are true:

```text
exact custody resolved
retention class known
required trigger established
external policy resolved
external authorization covers exact action
no applicable preservation hold
correction/dependency graph coherent
Portia integrity/recovery blockers cleared
candidate snapshot still current
action supported by Portia
```

Failure does not become best-effort deletion.

## 5. Ordering rules

1. Never delete recovery evidence before the mutation it protects is verified.
2. Never delete correction/disagreement context while surviving content still
   requires it.
3. Remove stale derived substantive copies as part of source disposition.
4. Retain required disposition/removal evidence according to policy.
5. Do not infer foreign success from local success.

## 6. Derived-state order

A safe conceptual pattern is:

```text
validate authoritative source disposition
-> prepare cleanup set
-> execute authoritative mutation under Portia recovery controls
-> verify mutation
-> remove derived substantive copies no longer permitted
-> rebuild/adjust surviving indexes/pointers
-> verify removed content is not resurrected
```

## 7. Export disposition order

A possible authorized pattern:

```text
verify export identity
-> delete exact export bytes
-> verify bytes absent
-> rebuild availability views
-> retain/dispose export provenance under its own rule
```

The immutable historical `deliberate_export@1` record is not rewritten in place.

A later durable "bytes disposed" statement should be a separate
disposition-evidence contract.

## 8. Correction-history unit

Disposition planning must evaluate predecessor/successor, Amendment, Statement
of Disagreement, Ownership Correction, Record Migration, Dependency, and
Exceptional Removal certificate relationships as a coherent unit.

## 9. Interrupted execution

After interruption, Portia must distinguish:

```text
not_started
started_not_verified
committed_verified
blocked_after_restart
unresolved_after_restart
```

Missing bytes alone cannot distinguish these states.

## 10. No compensating resurrection

After a destructive action was validly committed, do not recreate deleted
canonical content merely to make a cross-module plan appear atomic.

Cross-module orchestration is recoverable, not magically transactional.

## 11. Partial success example

A plan covering Portia Event custody, Portia export bytes, a Core retained scan,
and Vitrine immutable custody may legitimately end with:

```text
Portia Event disposition: committed_verified
Portia export bytes: committed_verified
Core scan: blocked
Vitrine Snapshot: no_action / separately governed
```

Overall status remains partial or completed-with-unresolved-external-custody,
depending on whether the remaining foreign action was required.

## 12. Outside-suite copies

Email, downloads, printouts, backups, external archives, and third-party
submission systems are `outside_suite_control` unless an authoritative external
system provides bounded verification.

## 13. Dry-run output must be non-destructive

Generating, reviewing, exporting, or approving a dry-run report must not itself
delete, archive, Exceptional Remove, rewrite lifecycle, withdraw an export, or
rebuild canonical data.

Planning and execution remain separate operations.

## 14. Idempotent restart goal

```text
same plan item + already verified Portia result
-> report already completed

same plan item + ambiguous state
-> reconcile, do not replay blindly

same plan item + stale source
-> require replan/revalidation
```

## 15. Audit/privacy minimization

Cross-module reports should prefer opaque semantic references, module,
retention class, action, status, blocker code, and decision/policy references.

They should avoid domain narratives merely to explain retention mechanics.

## 16. Final boundary

Portia participates in cross-module disposition by exposing semantic truth and
safe module-owned actions.

Portia does not become the orchestrator.

Sunset does not become Portia.
