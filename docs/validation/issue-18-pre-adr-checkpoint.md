# Issue #18 Pre-ADR Repository Checkpoint

**Issue:** `#18 — Define Support Process, Support, Intervention, implementation, and fidelity contracts`
**Date:** 2026-08-10
**Branch:** `18-support-process-support-intervention-implementation-fidelity`
**Checkpoint:** required pre-ADR drift review

## Exact Portia anchors

At the required pre-ADR checkpoint, GitHub reports:

```text
pds-portia/main:
5898ad79a7d405dc1e23b94753a0eeba793c8e72

Issue #18 branch:
654516259048c516e0572d777ac7a5810897fe09

comparison:
ahead
1 commit ahead
0 behind
merge base:
5898ad79a7d405dc1e23b94753a0eeba793c8e72
```

The one branch commit is:

```text
654516259048c516e0572d777ac7a5810897fe09
docs: begin support process design
```

Portia `main` has not moved since the Issue #18 initial checkpoint. The branch
contains only the two Slice 1 documentation additions.

## Exact Core anchor

The ticket/start checkpoint remains exactly equal to current Core `main`:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

Comparison:

```text
identical
0 commits ahead
0 behind
```

No Core drift requires an Issue #18 contract change.

Core remains authoritative for workspace/class/roster identity,
module-qualified work identity, safe shared paths, PDS2 routing/retained-source
provenance, and the v0.6 publication envelope. Producer-native intervention and
outcome semantics remain producer-owned. `intervention_record_set` remains a
future projection concern, not a requirement to implement publication here.

## ADR number availability

The expected ADR path:

```text
docs/decisions/0014-define-support-process-support-intervention-implementation-and-fidelity-contracts.md
```

does not exist on the branch before this checkpoint. ADR 0014 is therefore
available for Issue #18.

## Contract drift review

The pre-ADR review reconfirms these accepted existing boundaries:

```text
portia_support_process_id@1
support_process_target_ref@1
portia_work_ref@1
exact_portia_work_ref@1
exact_portia_work_record_ref@1
exact_local_record_ref@1
portia_local_work_target@1
work_relationship@2
represented_human_attribution@1
response@1
communication@1
hypothesis@1
shared lifecycle/correction/migration/operation/derived contracts
```

No existing published schema requires a version bump for the accepted Issue #18
direction.

### Work identity and targeting

Existing `sup_` identity and exact Portia work references already support
Support Process work. `support_process_target_ref@1` already names the intended
Support Process Participant record kind and can become operational once that
child family is published.

### Event context

`work_relationship@2` remains exactly `draws_context_from` with an exact Event
target. It is sufficient for Support Process → Event context and must not be
broadened into Support Process continuity or generic child-record relations.

### Response / Communication

ADR 0013 remains compatible. Response continues to own bounded Event-local
action. Support/Intervention owns planned or longitudinal support activity.

`communication@1` already accepts `support_process` structurally. Its Issue #17
application validator contains a temporary unconditional rejection only because
the owner did not yet exist. Issue #18 can replace that temporary gate with
owner/class/work/lifecycle resolution without changing `communication@1`.

### Hypothesis / FBA

Event-local `hypothesis@1` remains valid. Making Support Process concrete does
not itself create an honest formal FBA or team-hypothesis authority model. Exact
Event-local Hypotheses may be referenced as context; automatic aggregation,
function inference, and Intervention selection remain prohibited.

### Outcome boundary

Issue #19 remains open and owns Follow-Up, Outcome, Reentry, Repair, recurrence
interpretation, goal attainment as Outcome, and effectiveness/causal claims.
Issue #18 therefore must keep process completion, plan completion,
Implementation, and Fidelity non-outcome semantics.

## Public contract decision after drift review

The pre-ADR review supports the additive inventory proposed by Slice 1:

```text
support_process@1

portia_support_process_participant_id@1
support_process_participant@1

portia_support_need_id@1
support_need@1

portia_support_goal_id@1
support_goal@1

portia_support_id@1
support@1

portia_intervention_id@1
intervention@1

planned_schedule@1

portia_implementation_id@1
implementation@1

portia_fidelity_id@1
fidelity@1
```

Existing `portia_support_process_id@1` is reused.

No public `adaptation@1`, `support_process_hypothesis@1`, generic `plan@1`,
`party@1`, `provider@1`, `recipient@1`, `case@1`, or `service@1` is justified.

## Repository hygiene finding

The Slice 1 staged `git diff --cached --check` output reported trailing spaces on
Markdown metadata lines. PowerShell continued to the commit/push despite that
nonzero check.

This is a formatting-only finding with no architectural implication. The ADR
slice normalizes both Slice 1 Markdown files to LF content with no trailing
whitespace. The final acceptance check remains authoritative.

## Drift classification

```text
pds-portia main:
no drift

pds-core main:
no drift

Issue #18 branch:
expected Slice 1 documentation only

shared Portia contracts:
reusable; no version bump required

ADR 0014:
available

architecture implication:
none; Slice 1 design can be accepted with the decisions recorded by ADR 0014
```

## Pre-ADR conclusion

No repository or dependency drift requires reopening the proposed semantic
model. ADR 0014 may be accepted before any Issue #18 schema `$id` is published.
