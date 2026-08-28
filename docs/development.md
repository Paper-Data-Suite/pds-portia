# Portia development baseline

This document defines the executable-development baseline established by Issue #36,
extended with immutable runtime models/application validation in Issue #37,
canonical storage/guarded persistence in Issue #38, and production Core-roster /
Actor Directory identity services in Issue #39 and the Event-family workflow
services in Issue #40. It does not change Portia's
accepted ADRs, schemas, ownership rules, or domain semantics.

## Supported baseline

- Python: `>=3.11`
- Core compatibility: `pds-core>=0.6.3,<0.7`
- Distribution: `pds-portia`
- Import package: `portia`
- Console command: `portia`
- Development version line: `0.2.0`

`0.2.0` is the package identity for the active milestone. Its presence on a
development branch does not by itself mean that the v0.2.0 release has been
qualified, tagged, or published.

Issue #39 intentionally raises the Core floor to 0.6.3 because the production
identity layer now consumes the current public Core roster surface. Core 0.6.0
is no longer an active Portia qualification target. CI qualifies the supported
Ubuntu/Python 3.11 and Windows/Python 3.11 combinations against the authenticated
Core 0.6.3 release wheel.

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

Install the official Core 0.6.3 wheel before installing Portia:

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

The Issue #36 command surface remains deliberately non-mutating:

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

Issues #38 and #39 add reusable persistence and identity APIs; neither wires
teacher data access into the bootstrap CLI or creates teacher data merely because
Portia is imported or a status/menu command is run.

## Local validation

Run these gates from an activated `.venv` after installing Core 0.6.3 and
`-e ".[dev]"`:

```powershell
python scripts\validate_portia_foundation.py
python scripts\validate_runtime_models.py
python scripts\validate_storage.py
python scripts\validate_identity.py
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
continues to cover the executable `portia/` package, executable scripts, and the
top-level package/storage/identity tests.

The consolidated validator performs the same repository checks and rebuilds the
distributions before the wheel smoke test:

```powershell
python scripts\validate_repository.py --core-wheel $coreWheel
```

The smoke test creates its own temporary virtual environment. It retains the
Issue #37 immutable-model and Issue #38 guarded-storage checks, then initializes
a synthetic Core roster, proves an exact roster lookup has no Portia write side
effect, builds an I/O-free identity validation context, creates an Actor and
explicit Actor–Student Relationship through guarded storage, and resolves that
Relationship back to the exact class-qualified Core student.

## Build and release artifacts

Build artifacts are local/transient and are ignored by Git:

```powershell
Remove-Item -Recurse -Force build, dist, pds_portia.egg-info -ErrorAction SilentlyContinue
python -m build
python -m twine check dist\*
python scripts\check_package.py dist
```

The wheel contains the runtime `portia` package, including `portia.identity`,
`portia.storage`, the explicit runtime-coverage matrix, and one compact generated
closure of the accepted schemas required by the modeled contract surface. It
does not ship the repository schema tree. `jsonschema` remains a development/test
dependency; installed model conversion and validation use the standard-library
runtime validator.

Repository ADRs, audit evidence, tests, validation records, and development tools
remain source-distribution/repository material rather than runtime authority. See
[`runtime-models.md`](runtime-models.md), [`storage.md`](storage.md), and
[`identity-and-actor-directory.md`](identity-and-actor-directory.md).

## Storage development boundary

Later Portia domain services should consume `PortiaRepository`,
`ActorDirectoryRepository`, the typed operation/recovery stores,
`QuarantineGuard`, and `DerivedStore` rather than writing canonical JSON directly.

Important implementation constraints include:

- canonical work paths remain Core-backed;
- Actor Directory state remains workspace-scoped under Portia's accepted root;
- workspace-derived state does not invent a logical workspace ID from a path;
- normal reads never repair pointers or rebuild derived state;
- new identities use exclusive creation;
- replacement requires an exact expected fingerprint;
- accepted canonical bytes are never deleted to simulate graph-wide rollback;
- lock age alone never proves staleness; and
- missing derived state never proves an empty canonical graph.

Private technical storage history is recovery evidence only. It is not a new
public lifecycle, Amendment, correction, migration, or supersession contract.

## Identity development boundary

Event-family and later teacher workflows should consume `CoreRosterResolver` and
`ActorDirectoryService` rather than parsing Core roster files, matching students
by name, or inspecting Actor Directory paths directly.

Important identity constraints include:

- `class_id + student_id` is the complete Core roster identity;
- the same local student ID in different classes remains different identity;
- names and preferred names are display data only;
- Actor identity never substitutes for roster identity;
- Actor–student association requires an explicit accepted Relationship record;
- roster reads never create Portia canonical records;
- current-use Quarantine does not erase historical exact readability;
- exceptional removal remains distinct from historical nonexistence; and
- graph validation remains I/O-free and receives bounded authoritative facts
  through a validation context.

## Architecture and privacy boundary

Portia remains a teacher-local record and support tool. The bootstrap package
must not be described as an official discipline, SIS, case-management, IEP/504,
clinical, threat-assessment, legal, or mandated-reporting system. It must not
infer misconduct, culpability, risk, truth, intervention effectiveness, remorse,
resolution, or similar judgments.

All committed development/test data must comply with
[`synthetic-data-policy.md`](synthetic-data-policy.md).
