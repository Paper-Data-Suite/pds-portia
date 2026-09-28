# Issue #88 Deliberate Export Coordinated Operations Validation

## Scope

Issue #88 extends Portia coordinated-operation infrastructure for one exact
deliberate-export identity while leaving renderer, source selection, preview,
confirmation, teacher workflow, and export-history UX to Issue #51.

The accepted implementation adds `deliberate-export-ref@1`,
`deliberate-export-target@1`, `operation_journal@4`,
`operation_lock@3`, bounded artifact/provenance persistence, read-only recovery
classification, evidence-preserving recovery mutation, post-commit
finalization, and adversarial replay/conflict hardening.

## Invariants qualified

Qualification requires exact export identity, exclusive final writes, immutable
committed provenance references, no artifact regeneration during artifact-only
recovery, exact reserved committed-revision recovery, fail-closed mismatches,
idempotent exact replay, exact lock contention/release, explicit student-view
exclusion, and workspace path-containment protection.

Before this qualification slice, the repository completed a full regression
gate with 3,727 tests and 7,389 subtests passing, Ruff clean, and strict MyPy
clean. The adversarial Slice 7 focused gate completed with 74 passed and one
environmental Windows symlink skip.

## Distribution qualification

The dedicated package checker requires all Issue #88 runtime modules in the
wheel and Issue #88 contracts, validation scripts, documentation, and
acceptance tests in the source distribution.

The isolated wheel smoke verifies runtime journal v4 / lock v3 registration,
student-view exclusion, recovery API availability, traversal rejection, Core
0.6.3 compatibility, source-isolated imports, and absence of sibling-module
runtime dependencies.

## Authoritative command

```text
python scripts/validate_repository.py --core-wheel <pds_core-0.6.3-py3-none-any.whl>
```

Repository qualification reruns the complete pytest, Ruff, MyPy, pip-check,
build, Twine, package-inventory, historical wheel-smoke, and Issue #88
installed-wheel gates.
