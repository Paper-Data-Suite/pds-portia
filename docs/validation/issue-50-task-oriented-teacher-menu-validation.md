# Issue #50 Validation: Task-Oriented Teacher Menu

**Issue:** #50 — Implement the task-oriented Portia teacher menu  
**Runtime dependency:** `pds-core>=0.6.3,<0.7`  
**Branch:** `50-task-oriented-portia-teacher-menu`

## Evidence policy

This record contains only qualification actually observed during Issue #50
development. It does not infer final repository, build, package, installed
wheel, or CI success before those commands complete.

## Development checkpoints observed

The task-oriented menu was built in bounded slices. The most recent observed
focused qualifications before closeout include:

```text
View Timeline:      77 passed; Ruff clean; strict MyPy clean
Correct / Retract:  93 passed; Ruff clean; strict MyPy clean
Attention Needed:  115 passed; Ruff clean; strict MyPy clean
Advanced tools:     92 passed; Ruff clean; strict MyPy clean
```

Earlier task slices also received focused qualification before their checkpoint
commits. Issue #50 does not use these focused results as a substitute for the
final repository-wide gate.

## Closeout surface

Closeout adds:

```text
docs/task-oriented-teacher-menu.md
docs/validation/issue-50-task-oriented-teacher-menu-validation.md
scripts/validate_teacher_menu.py
scripts/check_issue50_package.py
scripts/smoke_test_issue50_teacher_menu_wheel.py
tests/test_issue50_teacher_menu_validation.py
```

The production `portia`/`portia menu` path launches the real teacher menu.
`portia status` remains bounded and nonmutating.

The mechanical validator checks the nine-surface menu taxonomy, Core navigation
reuse, process-local context, opaque ID/time seams, Issue #48 Timeline
delegation, Issue #49 Attention delegation, absence of the old foundation
fallback, absence of direct canonical filesystem/repository writes from menu
modules, no scoring/fuzzy APIs, no sibling runtime dependency, and the
#51/#52 boundary.

The package checker requires all Issue #50 menu runtime modules in the wheel and
the Issue #50 documentation/tooling/tests in the sdist.

The installed-wheel smoke is designed to install the exact Portia wheel with
the authenticated Core 0.6.3 wheel in an isolated virtual environment. It
checks that all nine menu surfaces are reachable without writes, creates one
synthetic Event through the installed menu application layer, verifies that no
Account/Observation/Determination/Response/Follow-Up is inferred, and verifies
installed Timeline, Follow-Up scheduling, and Attention delegation.

## Final qualification — local Windows evidence

The committed Issue #50 closeout source was qualified locally on Windows with
the authenticated Core 0.6.3 wheel.

Observed terminal evidence:

```text
Successfully built pds_portia-0.2.0.tar.gz and
pds_portia-0.2.0-py3-none-any.whl

Twine wheel: PASSED
Twine sdist: PASSED

Portia Issue #50 package inventory validation passed

Portia installed-wheel Issue #50 teacher-menu smoke test passed

git diff --check: passed

Portia Issue #50 repository qualification passed
```

The captured console excerpt begins during the build/package phase rather than
at the start of `validate_repository.py`. Therefore this record does not invent
an exact full-pytest test count or repeat unobserved Ruff/MyPy/pip-check output.
The terminal `Portia Issue #50 repository qualification passed` result was
observed from the cumulative validator, whose earlier stages include repository
pytest, Ruff, strict MyPy, and `pip check`.

The cumulative run also observed successful installed-wheel smoke checks for
Issues #41, #42, #43, #44, #45, #46, #47, #48, and #49 before the Issue #50
teacher-menu smoke.

### CI evidence — pending

```text
Windows CI:
Ubuntu CI:
```

Do not claim durable CI success here until the branch has been pushed and both
matrix jobs have completed successfully.
