# Issue #41 Account and Observation workflow validation

Issue #41 converts the accepted Account/Observation architecture into production
application services without changing published wire contracts. The implementation
is intentionally digital-entry and teacher-local; executable paper/OCR/import and
interpretive judgment remain outside this issue.

## Implemented validation surface

Focused workflow tests cover:

- mixed v1/v2 exact reads and deterministic enumeration of shared Account and
  Observation collections;
- v2 Account and Observation creation under exact Event and Support Process
  ownership;
- represented roster/Actor/local/descriptive source and human/instrument observer
  authority;
- Observation method/measurement compatibility and `artifact_review` authority;
- exact current-use versus historical-read behavior;
- persisted `lifecycle_transition@1` chains and legal ordinary transitions;
- coordinated lifecycle persistence, stale-fingerprint rejection, technical
  storage history, and partial durable commit behavior;
- Account `reports_from` / `clarifies` lineage and source-evidenced retraction;
- material Account/Observation correction by v2 successor plus predecessor
  supersession;
- exact v1 predecessor correction without rewriting v1 into v2;
- source-artifact containment/reference/fingerprint checks and fail-closed
  unsupported current-use branches;
- `reported_involved` Role revalidation through Account current-use authority;
- zero-write rejection for invalid prerequisites and no silent successor following.

The regression suite also proves that the reserved Issue #38 `.portia-staging/`
directory can coexist with strict canonical collection enumeration during recovery,
while arbitrary unexpected files/directories remain corruption.

## Issue #22 production accounting

`portia.workflows.issue22_parity` now records Issue #41 ownership or shared
production responsibility for representative evidence scenarios including P22-01,
P22-02, P22-04, P22-10, G22-010, G22-011, G22-017, and G22-035. The accounting
preserves #39 identity consumption and #37/#38 exact-validation/persistence
boundaries rather than duplicating those layers.

Important parity claims are behavioral rather than merely structural:

- conflicting Accounts remain separate evidence;
- direct Observation remains distinct from reported Account evidence;
- material correction keeps the exact predecessor and successor distinct;
- supersession cycles are rejected;
- historical exact references do not follow successors;
- reported-involvement Role authority depends on the exact Account remaining
  current-use eligible;
- no evidence workflow automatically creates a judgment.

## Mechanical workflow validator

`scripts/validate_workflows.py` checks the combined Issue #40/#41 production
workflow boundary. It verifies the required Account/Observation modules and public
service methods, v2-writer/v1+v2-reader constants, strict mixed-version repository
reads, Issue #22 accounting, and required production documentation. Its AST/source
checks continue to reject private Core imports, direct Core roster parsing,
name/fuzzy identity resolution, Actor repository bypass, direct canonical writer
calls, and workflow-local transaction/lock/journal implementations. It also guards
against importing later judgment or paper/import execution into the Account /
Observation workflow modules.

## Qualification state

All implementation slices through Role Account-authority integration have passed
their proportional focused pytest/Ruff/MyPy/`git diff --check` gates in the
implementation workflow. The final repository qualification is intentionally not
claimed here yet.

The closeout gate must run the consolidated repository qualifier against the
authenticated Core 0.6.3 wheel. That gate is responsible for the full pytest,
Ruff, MyPy, `pip check`, distribution build, Twine/package checks, isolated
installed-wheel smoke, and `git diff --check` result. The validation record should
only be updated to state final qualification success after that consolidated gate
actually passes.
