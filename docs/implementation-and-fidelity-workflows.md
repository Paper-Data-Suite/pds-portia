# Implementation and Fidelity Workflows

**Issue:** #45 — Implement Implementation and Fidelity workflows  
**Milestone:** Portia v0.2.0  
**Contract authority:** ADR 0014 / Issue #18

Issue #45 supplies the production application/workflow layer for the accepted
Support Process execution and implementation-quality contracts without changing
their published wire formats:

```text
implementation@1
fidelity@1
```

The planning authority remains Issue #44-owned. Follow-Up, Outcome, Reentry, and
Repair remain Issue #46-owned.

## Semantic boundary

Portia preserves the distinctions that make these records usable without turning
them into institutional service logs, compliance judgments, or causal claims:

```text
planned Support / Intervention != actual Implementation
Implementation != Fidelity
Fidelity != Outcome
Fidelity != effectiveness

execution_state=completed != successful
execution_state=completed != effective
execution_state=completed != goal achieved
execution_state=completed != student compliant

result=as_planned != effective
result=as_planned != successful
result=not_as_planned != ineffective
result=not_as_planned != provider incompetence
```

Implementation provider identity does not establish authorization, licensure,
assignment, competence, or employment. Actual target identity does not establish
consent, engagement, compliance, fault, or Outcome. A Fidelity evaluator is an
attributed evaluator for the bounded record, not an institutional credentialing
or staff-evaluation authority.

## Public API

`portia.workflows` exports the two production services and exact reference
builders:

```text
ImplementationWorkflowService
FidelityWorkflowService

implementation_reference(...)
fidelity_reference(...)
```

Both services provide guarded creation, exact historical reads, exact listing,
current-use qualification, canonical lifecycle transition, material correction,
work-root correction, duplicate consolidation, and current resolution.

Implementation additionally exposes:

```text
transition_execution_state(...)
```

for the frozen ordinary progression of one continuing in-progress occurrence.
Fidelity has no separate mutable operational-state dimension in v1. Neither
family exposes Amendment.

## Canonical ownership

Both families are canonical children of exactly one Support Process:

```text
classes/<class_id>/modules/portia/work/<support_process_id>/
  records/
    implementation/<implementation_id>.json
    fidelity/<fidelity_id>.json
```

They do not create a second work root, duplicate occurrences beneath Events, or
store records beneath Support/Intervention plan IDs. Current-use validation
reuses the authoritative Issue #44 Support Process root and Quarantine boundary.

## Exact plan authority

Every Implementation and Fidelity record names one exact historical
`support@1` or `intervention@1` through `plan_ref`.

Exact resolution remains exact across correction, plan adaptation, duplicate
consolidation, ownership correction, migration, and cross-year continuation. A
later current plan representation does not silently retarget an already recorded
occurrence or Fidelity evaluation.

This preserves the distinction between:

```text
current plan representation
plan_state
canonical lifecycle
historical exact plan identity
```

## Implementation semantic unit

One `implementation@1` is one bounded actual occurrence, attempt, or explicitly
delimited implementation interval for one exact Support or Intervention.
Repeated occurrences are separate canonical identities. A planned schedule never
creates Implementation records merely because time passes or a planned cadence
exists.

The occurrence records its actual target, actual implementation provider,
execution state, `started_at`, and optional `ended_at`, variation, and summary.
Chronology is explicit and offset-aware; planned duration is never converted into
actual duration automatically.

### Actual target and provider

Participant-backed actual targets and providers must resolve exactly inside the
owning Support Process and remain logically unique. Provider identity is never
inferred from `created_by`, plan author, coordinator, Actor title, or the first
planned provider.

When actual target or provider materially differs from the exact plan
expectation, the occurrence must preserve the corresponding variation kind:

```text
target
provider
```

Variation records what differed in that occurrence. It does not itself mean
approved deviation, poor Fidelity, ineffectiveness, provider error, or student
noncompliance.

### Execution state

The frozen execution vocabulary is:

```text
attempted
in_progress
completed
partially_completed
unable_to_complete
unknown
```

`unknown` is historical/import-only. Ordinary execution progression is limited
to:

```text
in_progress -> completed
in_progress -> partially_completed
in_progress -> unable_to_complete
```

That progression keeps the same Implementation identity and is revision-aware.
It cannot rewrite unrelated occurrence facts. A material correction to an
already recorded terminal factual state uses successor-based correction instead.

## Fidelity semantic unit

One `fidelity@1` is one bounded attributed judgment about how implementation
matched one exact Support or Intervention plan. It remains separate from both the
underlying Implementation facts and any later Outcome judgment.

Fidelity can evaluate:

```text
one Implementation
an explicit Implementation set
a bounded exact-plan interval
```

Implementation references inside Fidelity scope must resolve under the same
Support Process and name the same exact plan as the Fidelity record.

### Evaluator and basis

The evaluator is one exact Support Process Participant. Basis records remain
exact Support-Process-local references. Direct observation, record review,
checklist/instrument use, combined bases, and bounded `other` detail retain their
source-defined meaning rather than being collapsed into a universal score.

When an instrument supplies a scale and value, Portia preserves that declared
scale and validates that the value falls inside it. It does not normalize the
value into a cross-instrument Fidelity score.

### Result boundary

The accepted Fidelity result vocabulary describes only the bounded
implementation-quality judgment. It cannot establish:

```text
effectiveness
success
goal attainment
appropriateness of the plan
provider competence
student compliance
Outcome
```

A completed Implementation plus `result=as_planned` therefore still does not
create or imply an Outcome.

## Lifecycle, correction, consolidation, and ownership correction

Implementation and Fidelity both use the accepted canonical lifecycle and
successor-history infrastructure. Exact historical reads never follow a
successor silently.

Recording-error correction is successor-based. Duplicate consolidation requires
multiple legitimate predecessors. Work-root correction preserves the family
identity while moving the corrected representation to the true Support Process
root and preserving the factual occurrence/evaluation fields required by the
accepted contracts.

No ordinary lifecycle or execution operation is a loophole for rewriting
material historical facts.

## Cross-family integration

Production integration proves the directional authority chain:

```text
Support Process
-> exact Support / Intervention plan
-> separate Implementation occurrence(s)
-> optional bounded Fidelity evaluation
```

Creating or completing those records does not fabricate:

```text
Follow-Up
Outcome
Reentry
Repair
```

Those remain Issue #46 concerns.

## Frozen Issue #18 runtime parity

Issue #45 mechanically accounts for every schema-valid frozen Issue #18
Implementation/Fidelity runtime scenario:

```text
Implementation valid:                         10
Implementation schema-valid/application-invalid: 22
Fidelity valid:                                9
Fidelity schema-valid/application-invalid:    21
                                               --
62 schema-valid runtime scenarios
```

The combined parity guard reads the two per-family coverage maps and verifies the
frozen manifests mechanically. The 17 Implementation and 21 Fidelity
structural-invalid fixtures remain schema/model validation cases and are not
misclassified as workflow runtime cases.

Every application-invalid manifest entry must retain a nonempty frozen rejecting
invariant through `expected_error`.

## Issue #22 representative acceptance

Representative production acceptance covers the two frozen graphs called out by
the Issue #45 ticket:

* **P22-08** records separate actual Implementation occurrences from the exact
  Support Process plan, then records Fidelity over their exact history. Completed
  Implementation plus `as_planned` Fidelity does not imply or fabricate Outcome.
* **P22-11** preserves separate 2026 and 2027 Support Process roots and separate
  Implementation identities under each exact yearly plan. Exact downstream
  references remain pinned to the correct year, and Issue #45 fabricates no
  continuation, migration, Follow-Up, Outcome, Reentry, or Repair record.

## Documentation reconciliation

Issue #44 remains the authoritative planning layer. Its guide is updated only to
state that Issue #45 now supplies the downstream Implementation/Fidelity runtime
layer; its own planning semantics do not change.

The README also removes the stale pre-Issue #44 statement that active/current
Support-Process-owned Communication still fails closed waiting for Support
Process authority.

## Qualification

`scripts/validate_issue45_workflows.py` is the fast repository-local mechanical
drift detector for this surface. It imports no Portia runtime module. It checks
public exports, expected workflow surfaces, the exact 62-scenario oracle,
structural-invalid separation, representative acceptance presence, and required
documentation boundaries.

It does not replace pytest, Ruff, MyPy, package inventory, isolated
installed-wheel smoke against authenticated Core 0.6.3, or the cumulative
`scripts/validate_repository.py` qualification path.

Validation evidence is recorded in
`docs/validation/issue-45-implementation-and-fidelity-workflows-validation.md`.
