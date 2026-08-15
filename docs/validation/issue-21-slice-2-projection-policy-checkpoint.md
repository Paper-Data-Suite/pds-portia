# Issue #21 Slice 2 Projection Policy Checkpoint

**Status:** Passed
**Date:** 2026-08-14

Slice 2 introduced:

```text
docs/design/portia-privacy-projection-policy.md
docs/design/portia-record-sensitivity-and-projection-matrix.md
docs/validation/issue-21-slice-1-architecture-policy-checkpoint.md
tests/schema_validation/test_issue_21_privacy_projection_documentation.py
```

A first full-suite run exposed three brittle assertions in the new documentation
test. The assertions were corrected without changing the accepted projection
architecture.

The corrected Issue #21 test module was then run independently:

```text
Ran 5 tests in 0.003s

OK
Exit code: 0
```

The authoritative corrected full-suite run was:

```text
Ran 1025 tests in 205.944s

OK
Exit code: 0
```

The direct PowerShell console did not display unittest's footer on repeated full
runs, but redirecting the verbose full-suite output to a log captured the normal
footer and confirmed exit code 0.

This was a PowerShell/console stream-display observation, not a unittest or
Portia test-runner change.

`git diff --check` was clean in the preceding combined command, and the working
tree contained only the expected cumulative Issue #21 Slice 1–2 files.

Therefore **1025 tests / OK** is the authoritative Slice 2 checkpoint.
