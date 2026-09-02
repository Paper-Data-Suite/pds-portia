# Issue #44 Validation: Support Process, Support, and Intervention Workflows

**Status:** final repository qualification passed  
**Issue:** #44 — Implement Support Process, Support, and Intervention planning  
**Contract authority:** ADR 0014 / Issue #18  
**Runtime dependency:** `pds-core>=0.6.3,<0.7`

## Implemented production surface

Issue #44 adds the production planning application layer for:

```text
support_process@1
support_process_participant@1
support_need@1
support_goal@1
support@1
intervention@1
planned_schedule@1
```

through:

```text
SupportProcessWorkflowService
SupportProcessParticipantWorkflowService
SupportNeedWorkflowService
SupportGoalWorkflowService
SupportWorkflowService
InterventionWorkflowService
```

No accepted schema `$id` was changed. No replacement generic Plan contract was
introduced. No v1 Amendment operation was added.

Issue #45 remains the owner of Implementation/Fidelity. Issue #46 remains the
owner of Follow-Up/Outcome/Reentry/Repair.

## Qualified implementation sequence

The branch was developed in small production and acceptance slices covering:

```text
Support Process bootstrap/current-use authority
Participant creation, identity, lifecycle, correction
Need creation/current-use/lifecycle/correction
Goal creation/current-use/lifecycle/correction
Support creation, lifecycle, plan state, correction, adaptation
Intervention creation, lifecycle, plan state, correction, adaptation
Support Process root lifecycle, workflow state, correction
initiation authority
cross-year continuation
Support-Process-owned Communication integration
Support Process -> Event relationship authority
Support-Process-owned Account/Observation integration
P22-08 planning runtime parity
P22-11 cross-year planning runtime parity
Issue #18 planning runtime-parity guard
active Intervention and cross-class Participant acceptance
documentation + mechanical validation
```

Observed focused checkpoints in the working checkout include:

```text
P22-08 planning checkpoint:                     199 passed
P22-11 continuation checkpoint:                  13 passed
Issue #18 parity guard:                           5 passed
final Intervention/cross-class acceptance:       92 passed
```

Ruff, MyPy, and `git diff --check` were clean at the latest observed runtime
checkpoint. Final repository-wide output remains authoritative and is not
predicted here.

## Frozen Issue #18 runtime parity

`tests/test_workflow_issue18_planning_runtime_parity_guard.py` explicitly pins
the accepted planning oracle:

```text
valid planning scenarios:                  53
schema-valid/application-invalid:          82
total #44 planning runtime scenarios:     135
```

Covered families are Support Process, Support Process Participant, Support Need,
Support Goal, Support, Intervention, and Planned Schedule.

The guard fails if a valid or application-invalid planning fixture is added,
removed, or renamed without an explicit runtime test-module mapping. Every
application-invalid scenario must retain a nonempty frozen rejecting invariant.

Structural-invalid fixtures remain schema/model concerns. Entire
Implementation/Fidelity families are explicitly classified as Issue #45-owned.

## Issue #22 parity

`tests/test_workflow_issue22_support_planning_runtime_parity.py` executes the
frozen P22-08 planning subset through production services. It preserves exact
Event/Need/Goal/provider context and proves #44 planning does not fabricate
Implementation, Fidelity, Follow-Up, or Outcome.

`tests/test_workflow_support_process_continuation.py` strengthens P22-11 to exact
two-year planning parity. The predecessor reaches its frozen completed workflow
state; the successor reaches its frozen active state; each year's Participants,
Needs, Goals, and Supports remain distinct; `continues_from` stays exact; and
ordinary continuation does not create migration, ownership correction, or
supersession.

## Representative active Intervention

`tests/test_workflow_issue44_final_runtime_acceptance.py` loads the exact frozen
Issue #18 `active-recurring-assigned` Intervention fixture and executes it
through `InterventionWorkflowService` with real active root, supported person,
provider, Need, Goal, recurring schedule, and monitoring authority.

This proves the required structured active Intervention path without treating
the plan as Implementation or effectiveness evidence.

## Cross-class Support Process participation

The same acceptance module loads the exact frozen cross-class Participant
fixture against real Core roster files.

The supported person's roster authority may come from another class while the
canonical Participant and Support Process remain stored under the owning Support
Process class. The test proves that foreign roster lookup does not split
ownership, move the work root, or create workspace-global student identity.

## Communication and evidence integration

Issue #44 activates the already-published Support Process owner branch of
`communication@1`. Creation, current use, lifecycle transition, and correction
delegate to authoritative Support Process ownership rather than a shallow status
check. No `communication@2` is introduced.

Support-Process-owned Account and Observation production integration is also
qualified without fabricating Need, Goal, Implementation, Fidelity, Follow-Up,
or Outcome.

## Work Relationship authority

`WorkRelationshipService` now delegates `support_process@1` source qualification
to `SupportProcessWorkflowService`. The accepted
`draws_context_from` Support Process -> Event relationship remains work-level
context only and is not widened into a generic child-record relationship.

## Semantic invariants retained

```text
planned != implemented
Implementation != Fidelity
Fidelity != Outcome
Participant != provider authorization
Need != diagnosis
Goal != attainment
Support/Intervention != delivery
plan completion != effectiveness
workflow completion != resolution
cross-year continuation != migration
exact historical reference != current successor
```

No automatic causation, risk, diagnosis, legal authority, institutional
authorization, effectiveness, or publication conclusion is introduced.

## Mechanical validator

`scripts/validate_issue44_workflows.py` provides a source-tree drift detector. It
checks:

* all Issue #44 runtime modules are present;
* all six services and six exact reference builders remain public exports;
* the service source retains creation/current-use/correction and family-specific
  workflow/plan-state/adaptation surfaces;
* no Issue #44 service exposes Amendment;
* the Issue #18 parity guard, P22-08/P22-11 parity, evidence integration, and
  final active-Intervention/cross-class acceptance modules remain present;
* the workflow guide and validation record retain required semantic boundaries;
* README identifies Issue #44 as the executable Support planning layer; and
* Issue #43 documentation no longer claims Support Process Communication is
  waiting for Issue #44.

The validator intentionally imports no Portia runtime module.

## Slice 15b observed distribution qualification

The candidate distribution build produced:

```text
dist/pds_portia-0.2.0-py3-none-any.whl
dist/pds_portia-0.2.0.tar.gz
```

Observed qualification passed:

```text
Twine check: PASSED for wheel and sdist
Portia Issue #44 package inventory validation passed
Portia installed-wheel Issue #44 Support-planning smoke test passed
```

The isolated smoke used the authenticated Core 0.6.3 wheel, rejected source-tree
import leakage, exercised installed Support Process/Participant/Need/Goal/Support
and Intervention production services, and confirmed that planning did not
fabricate Implementation or Fidelity.

## Final repository integration

`scripts/validate_repository.py` remains the single authoritative repository
checkpoint. Issue #44 is appended to the existing cumulative path:

```text
validate_issue44_workflows.py
full pytest
full Ruff
full MyPy
pip check
build + Twine
base + Issue #41/#42/#43/#44 package inventories
base + Issue #41/#42/#43/#44 installed-wheel smoke tests
git diff --check
```

CI invokes that same command under the durable step label
`Run complete repository qualification`.

The authoritative local closeout command is:

```powershell
python scripts/validate_repository.py --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

## Final observed repository qualification

The authoritative cumulative repository checkpoint completed successfully
against the authenticated Core 0.6.3 wheel.

The full suite contains **2,492 tests**. The first cumulative run collected
2,492 and exposed three stale pre-authority/documentation guards; Slice 15c2
changed only those existing tests and did not add or remove tests. The final
cumulative rerun then completed all repository gates and ended with:

```text
Portia Issue #44 repository qualification passed
```

The same successful run rebuilt `pds_portia-0.2.0-py3-none-any.whl` and
`pds_portia-0.2.0.tar.gz`, passed Twine, passed the base and Issue #41/#42/#43/#44
package inventories, passed the base and Issue #41/#42/#43/#44 installed-wheel
smokes, and passed `git diff --check`.

This is the final local Issue #44 closeout evidence. CI remains responsible for
repeating the same cumulative `validate_repository.py` path on its configured
Windows and Linux runners.
