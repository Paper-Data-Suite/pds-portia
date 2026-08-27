# Issue #38 canonical storage and guarded persistence validation

**Issue:** `#38 — Implement canonical Portia storage and guarded persistence`  
**Milestone:** Portia `v0.2.0`  
**Status:** developer-checkout qualification passed; PR CI pending

## Scope

Issue #38 translates ADR 0004/0009 and the accepted persistence/recovery/derived
contracts into production Python storage services without changing published
schema IDs or claiming filesystem-wide transactionality.

The qualification boundary includes:

- deterministic Core-backed and Portia-owned paths;
- exact typed loads;
- exclusive create and expected-fingerprint replacement;
- private technical preservation of replaced bytes;
- target-adjacent staging and runtime containment;
- operation journal/current-pointer persistence;
- deterministic locks and partial-success preservation;
- explicit recovery;
- Quarantine and finding administration;
- immutable derived generations and source-snapshot freshness;
- Issue #22 persistence parity accounting;
- Windows and Ubuntu behavior; and
- installed-wheel persistence smoke testing.

## Qualification evidence

The final Windows developer-checkout qualification completed successfully on
2026-08-26 against Python 3.11.9 and the authenticated official Core 0.6.3
wheel. The accepted evidence is:

```text
focused closeout tests: 3 passed
Portia Issue #38 storage validator: passed
full repository pytest: 1559 passed
Ruff: passed
MyPy: passed (43 source files)
pip check: passed
git diff --check: passed
wheel build: passed
sdist build: passed
Twine checks: passed
package-boundary checks: passed
installed-wheel Issue #38 persistence smoke: passed
consolidated Issue #38 repository qualification: passed
```

The installed-wheel smoke ran in an isolated temporary environment rather than
through the source checkout. It initialized a synthetic workspace through Core's
public API, exercised typed Event persistence/readback/guarded replacement, and
verified stale-write rejection before the repository validator reported success.

Cross-platform GitHub Actions remains the PR gate. This record therefore does
not claim Windows/Ubuntu CI success before the branch is actually pushed and the
workflow completes.

## Required final qualification

With an authenticated supported Core wheel installed, run:

```powershell
python scripts\validate_portia_foundation.py
python scripts\validate_runtime_models.py
python scripts\validate_storage.py
python -m pytest
python -m ruff check .
python -m mypy
python -m pip check
python -m build
python -m twine check dist\*
python scripts\check_package.py dist
python scripts\smoke_test_wheel.py `
  dist\pds_portia-0.2.0-py3-none-any.whl `
  $coreWheel
git diff --check
```

The consolidated equivalent is:

```powershell
python scripts\validate_repository.py --core-wheel $coreWheel
```

`validate_repository.py` authenticates both the supplied Core wheel and the
installed Core version before running the qualification chain.

## Minimum Core floor

CI retains the declared dependency floor:

```text
pds-core>=0.6,<0.7
```

The minimum-Core job runs against official Core `0.6.0`; the primary Windows and
Ubuntu qualification jobs run against the current supported Core `0.6.3` wheel.
Issue #38 uses public Core path/workspace APIs already available at the 0.6.0
floor and therefore does not raise the dependency speculatively.

## Installed-wheel acceptance

The wheel smoke must run outside the source checkout and verify:

1. the compiled runtime contract bundle is present;
2. the `portia.storage` package is present;
3. exact runtime-model parsing still works without repository schemas;
4. a synthetic Core workspace can be initialized through Core's public API;
5. a typed Event can be exclusively persisted and exact-read;
6. guarded work-root replacement succeeds with the exact prior fingerprint;
7. the replaced representation receives a different exact fingerprint;
8. stale expected-state replacement is rejected; and
9. bootstrap CLI commands remain non-mutating after the persistence smoke.

## Architecture assertions

The validator additionally fixes these non-negotiable boundaries in executable
checks:

- canonical work paths remain Core-backed;
- Portia does not manufacture a durable `workspace_id` from the filesystem root;
- lock-key derivation remains identical to the accepted Issue #13 fixture;
- the storage package does not import sibling-private runtime code or
  `pds_core._*` implementation modules;
- `PortiaRepository` exposes guarded create/load/replace methods for work and
  Actor aggregates; and
- every Issue #22 scenario outside #37 receives exactly one #38/later-boundary
  disposition.

## Final acceptance rule

The developer-checkout half of this rule is satisfied: the final consolidated
qualification passed. Issue #38 is ready to commit and open as a PR. Final merge
acceptance still requires the resulting CI to pass on both Windows and Ubuntu; a
passing focused or local-only test is not sufficient.
