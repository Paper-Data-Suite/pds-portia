# Issue #39 validation record — Actor Directory and Core roster linking

Issue #39 adds the production identity/application-service bridge required by
the Event workflow beginning in #40.

## Qualified implementation boundary

The implementation provides:

- `CoreRosterResolver` over public Core v0.6.3 roster APIs;
- distinct typed roster-resolution failures;
- exact class-qualified identity using `class_id + student_id`;
- `ActorDirectoryService` over Issue #38 guarded persistence;
- `ActorDirectoryRepository` for bounded strict Actor child/removal inventory;
- explicit Actor–Student Relationship resolution;
- Quarantine-aware write and current-use checks;
- certificate-backed exceptional-removal resolution;
- I/O-free validation-context adapters; and
- machine-readable Issue #22 identity parity accounting.

No Event, Participant, Role, Account, Response, Support, Follow-Up, paper/import,
roster-editing, fuzzy matching, cross-class person merge, or teacher UI workflow
is introduced here.

## Regression coverage

Focused synthetic tests cover:

- exact Core roster and student resolution;
- absent roster versus absent student;
- malformed roster versus access failure;
- requested/returned class mismatch;
- invalid identifier input;
- same local student ID in different classes;
- same names/preferred names without identity merging;
- name changes with stable class-qualified identity;
- zero Portia writes during roster lookup;
- Actor create/load/guarded replacement;
- explicit Relationship resolution;
- multiple explicit class relationships without global-person inference;
- Actor/display values not substituting for roster identity;
- child owner mismatch;
- directly knowable current-use status/review/effective-period checks while
  preserving cross-record lifecycle-history validation as a separate boundary;
- exact superseded Relationship reads without successor following;
- Quarantine blocking writes/current use without lifecycle mutation;
- exceptional removal distinct from never-existing identity;
- positive-only validation context; and
- class-scoped authoritative roster-snapshot context.

Issue #22 accounting covers `G22-005`, `G22-006`, `G22-007`, and the bounded
resolver-owned portion of `G22-009`.

## Repository gates

The complete qualification sequence is:

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

or the consolidated gate:

```powershell
python scripts\validate_repository.py --core-wheel $coreWheel
```

The consolidated validator requires an authenticated
`pds_core-0.6.3-py3-none-any.whl` and rejects an older Core floor.

## Installed-wheel acceptance

The installed-wheel smoke runs outside the source checkout and verifies that:

1. Core 0.6.3 and the built Portia wheel install together cleanly;
2. the installed wheel contains `portia.identity` and Actor inventory storage;
3. an exact synthetic Core roster student resolves by class + student ID;
4. the lookup creates no Portia canonical state;
5. the successful resolution supplies the validation context;
6. an Actor and explicit Actor–Student Relationship persist through guarded
   storage; and
7. the Relationship resolves back to the exact class-qualified Core student.

The smoke also retains the immutable-model, guarded-storage, CLI, and package
checks established by Issues #37 and #38.
