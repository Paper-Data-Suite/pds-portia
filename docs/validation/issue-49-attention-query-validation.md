# Issue #49 Validation: Due Follow-Up and Native Attention Queries

**Issue:** #49 — Implement due follow-up and attention queries
**Runtime dependency:** `pds-core>=0.6.3,<0.7`
**Branch:** `49-due-follow-up-attention-queries`

## Evidence policy

This record contains only results observed during the Issue #49 working
session. It does not infer build, packaging, installed-wheel, or remote CI
success from source-level tests. Final closeout evidence is added only after the
corresponding command actually completes.

## Frozen implementation checkpoints

The accepted implementation checkpoints before Slice 6 are:

```text
Slice 1  03050374e00924b42595793636d5df011134a441
Slice 2  4e5dab1a486a6255b08cf3867add46be88964cf2
Slice 3  24dff07064949679055c306b70d015c1562d28d0
Slice 4  ad5169a4512038cf28deb70d78bab2175c4d4aff
Slice 5  52b7c291cb6915ebf16348e3d232cc9abacfbb82
```

Observed local results include:

```text
Slice 4 focused attention gate: 72 passed
Slice 4 affected authority regressions: 43 passed
Slice 4 full repository gate: 3548 passed, 7385 subtests passed

Slice 5 focused attention gate: 85 passed
Slice 5 affected authority regressions: 46 passed
Slice 5 full repository gate: 3561 passed, 7385 subtests passed
Slice 5 Ruff: passed
Slice 5 strict MyPy: passed (169 source files in the full repository gate)
Slice 5 pip check: no broken requirements
Slice 5 git diff --check: passed
```

Slice 4 remote GitHub Actions CI was observed completed successfully before
Slice 5 work began. Slice 5 was pushed at
`52b7c291cb6915ebf16348e3d232cc9abacfbb82`; this record does not claim the
result of that remote run until it is explicitly observed.

## Slice 6 closeout surface

Slice 6 adds:

```text
scripts/validate_attention_queries.py
scripts/check_issue49_package.py
scripts/smoke_test_issue49_wheel.py

tests/test_attention_privacy.py
tests/test_attention_acceptance_matrix.py
tests/test_issue49_package_checker.py
tests/test_issue49_wheel_smoke_script.py
tests/test_issue49_closeout_validation.py
tests/test_issue49_repository_qualification.py

docs/due-follow-up-and-attention-queries.md
docs/validation/issue-49-attention-query-validation.md
```

The source validator is non-importing with respect to Portia runtime modules.
It checks the public native services, explicit `as_of`, stable taxonomy, no
implicit timing wall clock, absence of fuzzy/name resolution, absence of
behavior/risk/urgency/priority APIs, no canonical attention schema, no
query-side recovery/rebuild calls, no sibling runtime dependency, no premature
Issue #52 provider registration, and documentation/taxonomy agreement.

The package checker verifies the complete `portia/attention` runtime surface in
the wheel and the Issue #49 closeout docs/tooling in the sdist.

The installed-wheel smoke is designed to run from an isolated virtual
environment with the authenticated Core 0.6.3 wheel and no source-checkout
imports. Its synthetic scenario covers separate schedule/attention semantics,
an incomplete Review, Support Process review/dependency attention, active
Quarantine, acknowledged current conflict, permitted presentation suppression,
fresh/stale derived state, recovery-required operation state,
workspace/class/work filtering, deterministic ordering, privacy minimization,
and before/after workspace fingerprints.

## Platform path

The durable repository CI matrix already covers:

```text
ubuntu-latest / Python 3.11 / Core 0.6.3
windows-latest / Python 3.11 / Core 0.6.3
```

Slice 6 integrates the Issue #49 validator, package checker, and installed-wheel
smoke into the existing cumulative `scripts/validate_repository.py` path, so
successful future CI exercises the same closeout sequence on both platforms.

## Final Slice 6 cumulative qualification

Observed locally on Windows after the installed-wheel fixture repairs:

```text
corrected wheel + sdist build: passed
Twine wheel check: passed
Twine sdist check: passed
Issue #49 package inventory: passed
Issue #49 isolated installed-wheel attention smoke: passed
cumulative scripts/validate_repository.py qualification: passed
final git diff --check within cumulative qualification: passed
```

The cumulative repository validator also completed the retained package and
installed-wheel qualification chain through Issues #41, #42, #43, #44, #45,
#46, #48, and #49 before emitting its terminal Issue #49 success marker.

The supplied cumulative terminal excerpt begins during the build phase, so it
does not preserve the exact pytest/Ruff/MyPy/pip-check line counts from that
run. Those gates are part of `scripts/validate_repository.py`, and the
terminal repository-qualification success marker was observed, but no exact
cumulative pytest count is invented here. The latest separately observed full
repository pytest count remains the Slice 5 gate: 3561 passed, 7385 subtests
passed.

Remote CI for the final Slice 6 commit is not claimed in this record until it
is observed after push.
