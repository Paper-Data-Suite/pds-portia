# Portia development baseline

This document defines the executable-development baseline established by Issue #36.
It does not change Portia's accepted ADRs, schemas, ownership rules, or domain
semantics.

## Supported baseline

- Python: `>=3.11`
- Core compatibility: `pds-core>=0.6,<0.7`
- Distribution: `pds-portia`
- Import package: `portia`
- Console command: `portia`
- Development version line: `0.2.0`

`0.2.0` is the package identity for the active milestone. Its presence on a
development branch does not by itself mean that the v0.2.0 release has been
qualified, tagged, or published.

Issue #36 consumes no Core API introduced after Core 0.6.0, so Portia keeps the
established Core 0.6 floor rather than raising it speculatively. CI verifies the
Core 0.6.0 floor and separately qualifies against the current Core 0.6.3 release.
A later Portia issue must raise the floor if it begins to require a newer public
Core API.

## Create the local virtual environment

The repository-local development environment is `.venv/`. It is intentionally
ignored by Git and must never be committed.

### Interrupted pip upgrade recovery

`bootstrap_dev.ps1` and `bootstrap_dev.sh` repair pip's `~ip*` temporary rename
artifacts before invoking pip. These artifacts can be left behind if a pip
self-upgrade is interrupted. Re-running the bootstrap is therefore the supported
recovery path; a partially completed `.venv` does not need to be repaired by
hand.

### Windows PowerShell

The repository includes `scripts\bootstrap_dev.ps1` for a one-command setup:

```powershell
.\scripts\bootstrap_dev.ps1
.\.venv\Scripts\Activate.ps1
```

The equivalent manual setup is:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install an official supported Core 0.6 wheel before installing Portia. For the
current supported Core release:

```powershell
$coreWheel = Join-Path $HOME "Downloads\pds_core-0.6.3-py3-none-any.whl"
Invoke-WebRequest `
  -Uri "https://github.com/Paper-Data-Suite/pds-core/releases/download/v0.6.3/pds_core-0.6.3-py3-none-any.whl" `
  -OutFile $coreWheel
python scripts\verify_core_wheel.py $coreWheel
python -m pip install $coreWheel
python -m pip install -e ".[dev]"
python -m pip check
```

If the Core wheel is already present in `Downloads`, skip `Invoke-WebRequest`.
Do not install an unverified file merely because its filename looks correct.

### macOS / Linux

The repository includes `scripts/bootstrap_dev.sh`:

```bash
./scripts/bootstrap_dev.sh
source .venv/bin/activate
```

The equivalent manual setup is:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
curl -fL \
  -o /tmp/pds_core-0.6.3-py3-none-any.whl \
  https://github.com/Paper-Data-Suite/pds-core/releases/download/v0.6.3/pds_core-0.6.3-py3-none-any.whl
python scripts/verify_core_wheel.py /tmp/pds_core-0.6.3-py3-none-any.whl
python -m pip install /tmp/pds_core-0.6.3-py3-none-any.whl
python -m pip install -e ".[dev]"
python -m pip check
```

## Bootstrap CLI

The Issue #36 command surface is deliberately non-mutating:

```powershell
portia --help
portia --version
portia status
portia menu
python -m portia --version
```

`portia menu` is a bounded scaffold. It identifies the planned teacher tasks but
does not implement Event, Response, Communication, Support, Follow-Up, timeline,
correction, attention, or export workflows. Those remain assigned to later
v0.2.0 issues.

## Local validation

Run these gates from an activated `.venv` after installing Core and
`-e ".[dev]"`:

```powershell
python scripts\validate_portia_foundation.py
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

Ruff intentionally excludes `tests/schema_validation/` and
`scripts/validate_portia_foundation.py`. Those files are the accepted Phase 1
foundation validation corpus and predate the executable-package lint baseline;
they remain exercised by the foundation validator and full pytest suite. Ruff
continues to cover the executable `portia/` package, Issue #36 scripts, and the
new top-level package tests.

The consolidated validator performs the same repository checks and rebuilds the
distributions before the wheel smoke test:

```powershell
python scripts\validate_repository.py --core-wheel $coreWheel
```

The smoke test creates its own temporary virtual environment and verifies that
the wheel works independently of the source checkout.

## Build and release artifacts

Build artifacts are local/transient and are ignored by Git:

```powershell
Remove-Item -Recurse -Force build, dist, pds_portia.egg-info -ErrorAction SilentlyContinue
python -m build
python -m twine check dist\*
python scripts\check_package.py dist
```

The wheel intentionally contains only the runtime `portia` package and package
metadata. Repository ADRs, schemas, audit evidence, tests, and development tools
remain source-distribution/repository material; #36 does not turn those files
into runtime authority.

## Architecture and privacy boundary

Portia remains a teacher-local record and support tool. The bootstrap package
must not be described as an official discipline, SIS, case-management, IEP/504,
clinical, threat-assessment, legal, or mandated-reporting system. It must not
infer misconduct, culpability, risk, truth, intervention effectiveness, remorse,
resolution, or similar judgments.

All committed development/test data must comply with
[`synthetic-data-policy.md`](synthetic-data-policy.md).
