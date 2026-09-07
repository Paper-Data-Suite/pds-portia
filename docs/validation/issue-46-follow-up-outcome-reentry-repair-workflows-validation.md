# Issue #46 Validation: Follow-Up, Outcome, Reentry, and Repair Workflows

**Status:** source/runtime, distribution, and cumulative repository qualification observed  
**Issue:** #46 — Implement Follow-Up, Outcome, Reentry, and Repair workflows  
**Contract authority:** ADR 0015 / Issue #19  
**Runtime dependency:** `pds-core>=0.6.3,<0.7`

## Evidence policy

This record contains only qualification evidence actually observed during the
Issue #46 working session. Source/runtime, distribution, and cumulative
repository evidence below has been observed. Numeric results are stated only
when the supplied terminal capture preserves them; no missing count is inferred.

The feature branch is:

```text
46-follow-up-outcome-reentry-repair-workflows
```

The branch was created from the accepted Issue #45 baseline. The Issue #46 work
has intentionally been qualified in small slices before final repository
integration.

## Implemented production surface

Issue #46 now supplies:

```text
FollowUpWorkflowService
OutcomeWorkflowService
ReentryWorkflowService
RepairWorkflowService

follow_up_reference(...)
outcome_reference(...)
reentry_reference(...)
repair_reference(...)
```

for the frozen contracts:

```text
follow_up@1
outcome@1
reentry@1
repair@1
```

Shared downstream authority is factored through:

```text
portia/workflows/downstream_common.py
portia/workflows/downstream_lifecycle.py
portia/workflows/downstream_supersession.py
portia/workflows/action_reownership.py
```

The four families use exact Event/Support Process ownership, exact historical
reads, current-use qualification, Quarantine, canonical lifecycle, correction,
duplicate consolidation, and work-root correction. Follow-Up, Reentry, and
Repair also implement bounded ordinary workflow-state progression. Outcome has
no invented mutable workflow-state dimension. None exposes v1 Amendment.

## Frozen Issue #19 runtime oracle

The frozen manifests are mechanically accounted as:

```text
Follow-Up: 10 valid + 14 application-invalid = 24 runtime
Outcome:   13 valid + 17 application-invalid = 30 runtime
Reentry:   11 valid + 14 application-invalid = 25 runtime
Repair:    12 valid + 19 application-invalid = 31 runtime

Total:     46 valid + 64 application-invalid = 110 runtime
Structural-invalid, separate: 72
```

Structural-invalid fixtures remain schema/model cases and do not masquerade as
workflow runtime cases. Each application-invalid fixture has explicit frozen
error evidence in its family parity map.

## Observed Slice 6a checkpoint

After the corrected combined-parity guard was applied, the user executed the
full Issue #46 targeted checkpoint. Observed results were:

```text
328 passed in 28.58s
62 Issue #19 contract tests passed in 8.57s
170 regression tests passed in 76.49s
Ruff: All checks passed!
MyPy: Success: no issues found in 119 source files
git diff --check: no whitespace error
```

The two CRLF-to-LF notices for `portia/workflows/action_common.py` and
`portia/workflows/action_reownership.py` were Git line-ending warnings, not
`git diff --check` errors.

The 328-test targeted selection included all four workflow suites, shared
downstream authority/lineage tests, action reownership, all four family parity
guards, the combined 110/72 ledger, and P22-08 through P22-11 representative
integration.

## Representative Issue #22 acceptance

`tests/test_issue46_representative_integration.py` executes P22-08 through P22-11
through production current-use services after seeding the frozen synthetic graph
into a temporary canonical workspace.

The acceptance path preserves the core non-inference rules:

```text
Follow-Up completion != Outcome/resolution
Implementation/Fidelity != effectiveness/Outcome
Outcome linkage/time != causation
later Event != automatic recurrence/failure
Reentry completion != clearance/compliance/rehabilitation
Repair participation/completion != admission/remorse/forgiveness/restoration
```

P22-11 also preserves exact cross-year ownership instead of treating normal
continuation as migration, correction, supersession, or automatic identity reuse.

## Documentation and source mechanical validation

Slice 7 introduces:

```text
docs/follow-up-outcome-reentry-repair-workflows.md
docs/validation/issue-46-follow-up-outcome-reentry-repair-workflows-validation.md
scripts/validate_issue46_workflows.py
tests/test_issue46_closeout_validation.py
```

The validator is non-importing with respect to Portia runtime code. Its source
stage mechanically checks required runtime modules/public exports, service
operations, absence of v1 Amendment, accepted downstream state/reason tokens,
exact 24/30/25/31 family runtime parity, the aggregate 110 runtime / 72
structural accounting, explicit application-invalid error evidence, P22-08
through P22-11 acceptance presence, and documentation reconciliation.

The validator is stage-aware:

```text
--stage source        # Slice 7 source/runtime/docs authority
--stage distribution  # additionally requires package checker + wheel smoke
--stage repository    # additionally requires cumulative repository integration
```

`repository` is the default final mode. All three stages are now populated and
qualified. They remain fail-closed mechanical gates: removing or drifting a
required source, distribution, or cumulative repository artifact causes the
corresponding stage to fail.

The Slice 7 source validator command is:

```powershell
python scripts/validate_issue46_workflows.py --stage source
```

After Slice 7a, the user reported:

```text
Portia Issue #46 source workflow validation passed
331 passed in 33.88s
62 Issue #19 contract tests passed in 10.76s
170 regression tests passed in 121.83s
Ruff: All checks passed!
MyPy: Success: no issues found in 119 source files
git diff --check: no whitespace error
```

The same two CRLF-to-LF notices remained informational line-ending warnings.
The 331-test targeted selection includes the three Slice 7 closeout-validation
tests in addition to the accepted Slice 6a targeted set.

## Documentation reconciliation

README gains an Issue #46 current-implementation section. The Issue #44 and #45
workflow guides are reconciled so they no longer describe
Follow-Up/Outcome/Reentry/Repair production work as pending while preserving
their own planning and Implementation/Fidelity authority boundaries.

## Distribution qualification

Slice 8 adds:

```text
scripts/check_issue46_package.py
tests/test_issue46_package_checker.py
scripts/smoke_test_issue46_wheel.py
tests/test_issue46_wheel_smoke_script.py
```

The user then built the real distributions and reported the following observed
qualification:

```text
Successfully built pds_portia-0.2.0.tar.gz and pds_portia-0.2.0-py3-none-any.whl
Checking dist\pds_portia-0.2.0-py3-none-any.whl: PASSED
Checking dist\pds_portia-0.2.0.tar.gz: PASSED
Portia Issue #46 package inventory validation passed
Portia installed-wheel Issue #46 downstream workflow smoke test passed
```

The package checker verified that the wheel physically contains the four
downstream services plus shared downstream runtime helpers and that the sdist
contains the Issue #46 documentation and validation/distribution tooling. The
installed-wheel smoke used the authenticated Core 0.6.3 wheel in an isolated
virtual environment, rejected source-checkout import leakage, and exercised real
P22-08/P22-10 current-use paths through Follow-Up, Outcome, Reentry, and Repair.

The pasted Slice 8 log begins during the build, so it does not preserve the
earlier focused pytest/Ruff/MyPy output from that command block. Those results
are therefore not restated or inferred here.

## Final repository integration

Slice 9 extended `scripts/validate_repository.py` through Issue #46 while
preserving the durable CI entrypoint and authenticated Core 0.6.3 requirement.
Slice 9a then restored the accepted Issue #45 source-level closeout markers as
inert compatibility text and added a regression guard that executes the Issue
#45 validator against the cumulative Issue #46 path.

The user then executed the authoritative cumulative command:

```powershell
python scripts/validate_repository.py `
  --core-wheel "$HOME\Downloads\pds_core-0.6.3-py3-none-any.whl"
```

The supplied terminal capture preserves the final distribution and closeout
portion of that successful run. Observed evidence includes:

```text
Successfully built pds_portia-0.2.0.tar.gz and pds_portia-0.2.0-py3-none-any.whl
Twine: wheel PASSED
Twine: sdist PASSED
Portia Issue #46 package inventory validation passed
Portia installed-wheel Issue #46 downstream workflow smoke test passed
git diff --check: no whitespace error
Portia Issue #46 repository qualification passed
```

The cumulative validator reaches that terminal success line only after the
foundation, runtime-model, storage, identity, workflow validators through Issue
#46, full repository pytest, full Ruff, full MyPy, `pip check`, build, Twine,
package inventory checks through Issue #46, installed-wheel smoke tests through
Issue #46, and `git diff --check` all return successfully.

The terminal capture supplied for this final run begins during the distribution
build, so the full-repository pytest summary count is not preserved in the
provided evidence. The full pytest gate passed as part of the successful
cumulative qualifier, but no numeric full-repository pytest count is invented
or back-calculated here.

The two CRLF-to-LF notices for `portia/workflows/action_common.py` and
`portia/workflows/action_reownership.py` remained informational line-ending
warnings rather than `git diff --check` failures.
