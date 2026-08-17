# Portia Representative Synthetic Graph Corpus

## Purpose

Issue #22 validates the completed Portia foundation as coherent record
graphs rather than as isolated JSON documents.

The corpus exists to prove three different properties separately:

```text
structurally valid record
  != resolvable and coherent combined record graph
  != approved production runtime behavior
```

A public Portia record remains governed by its cataloged JSON Schema.
Issue #22 adds a development-only graph harness that evaluates selected
cross-record application invariants against deterministic synthetic stories.

The harness is not a production Portia service and does not create a new
public interchange format.

## Corpus authority

The root descriptor uses:

```json
{
  "fixture_contract": "pds-portia.representative-contract-graph-corpus",
  "fixture_version": "1",
  "not_runtime_contract": true,
  "synthetic": true
}
```

A scenario descriptor similarly identifies itself as a test-only contract.

Fixture metadata may identify:

```text
public contract name and exact version
fixture path
logical fixture identity
canonical owner
intended canonical workspace path
foreign/test context
expected graph result
expected graph-finding IDs
derived/projection checks
```

Those fields are never injected into the public Portia records themselves.

## Authority layers

### Public Portia records

JSON beneath each scenario's `records/` directory is ordinary Portia public
record data. Each record is validated through the existing schema catalog by
exact:

```text
contract name + contract version
```

No "latest" schema selection is permitted.

### Synthetic Core context

Small test-only context may model the minimum Core-owned state needed to
resolve a Portia relationship.

Slice 1 uses one synthetic roster context solely to answer:

```text
does this exact class_id + student_id pair exist in the declared roster?
```

The context fixture is not a replacement for Core, is not cataloged as a
public schema, and is not treated as canonical Portia state.

### Expected derived state

Expected summaries/projections are test outputs. They are neither canonical
Portia records nor public serialization contracts.

Rebuilding or deleting them cannot change canonical record identity.

## Exact storage identity

The accepted Portia storage contract remains:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  work.json
  records/<record_kind>/<record_id>.json
  ...
```

Issue #22 scenario descriptors record the intended canonical path so the
graph harness can verify that persisted identity and declared location agree.

The path is evidence about ownership, not an alternate identifier.

## Graph findings

The test harness returns bounded findings such as:

```text
G22.STRUCTURAL.INVALID
G22.IDENTITY.DUPLICATE_LOGICAL_IDENTITY
G22.IDENTITY.ROSTER_STUDENT_UNRESOLVED
G22.OWNERSHIP.CLASS_MISMATCH
G22.OWNERSHIP.WORK_MISMATCH
G22.OWNERSHIP.CANONICAL_PATH_MISMATCH
G22.REFERENCE.PARENT_EVENT_MISSING
G22.REFERENCE.PARTICIPANT_TARGET_MISSING
```

These codes are fixture/test vocabulary only.

A graph-invalid fixture added later in Issue #22 must normally remain
structurally valid and fail for one declared application-level finding.

Keep:

```text
application invalid
  != Integrity Finding
  != Quarantine
```

unless the synthetic condition independently satisfies Portia's accepted
integrity/isolation threshold.

## Slice 1 positive graph

`P22-01` is deliberately small:

```text
Event@2
  -> Event Participant@3
      -> Event Participant Role@3 (present)
      -> Observation@2 (live direct)
```

The subject is one exact synthetic Core roster reference:

```text
eng10_p2_2026 + stu_p22_001
```

The graph contains no Classification, Hypothesis, Determination, Response,
Communication, Support, Follow-Up, or Outcome.

That absence is intentional.

The scenario proves:

```text
Event existence != misconduct
participant presence != responsibility
direct Observation != finding
positive/neutral classroom documentation is representable
```

The Observation records only directly observable behavior. It does not
calculate praise, compliance, proficiency, intent, or another judgment.

## Deterministic teacher-current view

Slice 1 also builds a small derived summary from the active canonical
records.

The summary is deterministic and contains sorted IDs only:

```text
work_id
participant_ids
role_ids
observation_ids
```

Rebuilding it from the same canonical graph must reproduce the same value.

This is a first proof of the wider Issue #22 rule:

```text
derived view != canonical authority
```

Later slices extend derived-state testing to reverse references, lifecycle
frontiers, dependencies, histories, and stale-source detection.

## Planned extension

The same corpus/harness is extended through the remaining positive stories:

```text
P22-02  multi-participant Event / conflicting Accounts
P22-03  cross-class participant
P22-04  correction / supersession / disagreement
P22-05  paper-derived proposal and review
P22-06  structured import
P22-07  Response and family Communication
P22-08  multi-Event Support Process / positive Outcome
P22-09  inconclusive and adverse Outcomes
P22-10  Reentry and Repair
P22-11  cross-year Support continuation
P22-12  privacy projection / deliberate export
P22-13  derived rebuild / retention-custody boundary
P22-14  coordinated operation / recovery
```

A substantial schema-valid/graph-invalid corpus is added alongside those
positive stories.

## No new public contract by default

Issue #22 must not create public contracts such as:

```text
representative_graph@1
scenario@1
graph_finding@1
student_history@1
dossier@1
```

If a required positive story genuinely cannot be represented by accepted
public contracts, the implementation must expose and reconcile that
architecture defect rather than weaken the fixture.

## Handoff to Issue #23

The final corpus, graph-invalid matrix, contract-coverage matrix, and
validation evidence become the principal representative evidence set for
the final Portia foundations audit.

Issue #22 itself does not declare the foundation approved or production
ready.
