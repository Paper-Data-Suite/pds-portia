# Issue #21 Slice 7 Failure / Synthetic Example Checkpoint

**Status:** Passed
**Date:** 2026-08-14

Authoritative maintainer-run validation:

```text
Ran 1077 tests in 305.924s

OK
```

`git diff --check` produced no content errors.

Slice 7 established:

```text
application-invalid matrix
36 runtime failure/recovery cases
24 machine-checked synthetic cross-cutting scenarios
no new public schema
```

Accepted Slice 7 baseline:

```text
1077 tests
OK
clean git diff --check
```
