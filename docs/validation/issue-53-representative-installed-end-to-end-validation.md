# Issue #53 Representative Installed End-to-End Validation

## Scope

Issue #53 proves representative coherence of the installed Portia v0.2 application in one continuous synthetic workspace. It combines the previously accepted v0.2 runtime surfaces into one installed story without changing their domain authority or semantic contracts.

The representative story is:

```text
Core classroom / rosters
-> workspace Actors
-> cross-class identity
-> Event / Participants / Roles
-> Account / Observation
-> Review / bounded judgment
-> material correction / exact history
-> Response / Communication
-> Support Process / Need / Goal / Support
-> Implementation / Fidelity
-> Follow-Up / attention transition
-> stale-write conflict
-> interrupted coordinated operation
-> recovery
-> fresh-process durable reload
-> student-view privacy
-> teacher-reference export
-> Core readiness / attention provider
-> Integrity verification
```

This is an integration and qualification boundary. It is not a new public Portia record contract and is not a replacement for focused subsystem tests.

> Issue #53 proves representative coherence of the installed v0.2 application. It does not assert that every possible Portia workflow combination has been exhaustively explored.

> The acceptance story uses only synthetic records and must never be run against or populated from a real teacher workspace.

## Installed artifact boundary

The authoritative Issue #53 execution uses:

```text
Portia candidate:
    distribution: pds-portia
    version:      0.2.0
    source:       committed repository HEAD being qualified
    wheel:        exact candidate wheel supplied to the smoke
    SHA-256:      computed from that supplied wheel

Core authority:
    filename:     pds_core-0.6.4-py3-none-any.whl
    SHA-256:      48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b
    version:      0.6.4
```

Portia retains its declared runtime dependency:

```text
pds-core>=0.6.3,<0.7
```

The exact Core 0.6.4 artifact is the current installed acceptance authority; it is not a reason by itself to raise Portia's minimum Core version.

Historical installed smokes that were accepted against authenticated Core 0.6.3 remain historical evidence and are not rewritten to use the newer artifact.

## Final execution record

The authoritative closeout run must retain enough output for Issue #54 to identify the exact candidate that was exercised. Immediately before the final cumulative qualification, record:

```text
candidate Portia source commit:
    git rev-parse HEAD

candidate Portia wheel filename:
    emitted as candidate_portia_wheel

candidate Portia wheel SHA-256:
    emitted as candidate_portia_sha256

Core wheel filename:
    emitted as core_wheel

Core wheel SHA-256:
    emitted as core_sha256

Python version:
    interpreter used by the cumulative qualification

host platform:
    CI / local qualification platform

deep workspace geometry:
    emitted workspace_length / deep_workspace_length evidence
```

`scripts/smoke_test_issue53_end_to_end_wheel.py` computes the candidate Portia wheel digest from the exact wheel passed on the command line and authenticates the exact released Core wheel before installation.

Do not substitute a rebuilt or differently sourced candidate after qualification. Issue #54 must audit the same candidate artifact represented by this evidence.

## Isolation and launcher boundary

The smoke creates a fresh virtual environment and an empty working directory outside the source checkout, workspace, and artifact directories.

It removes inherited authority such as:

```text
PYTHONPATH
PDS_WORKSPACE_ROOT
```

and isolates ordinary user configuration roots where practical.

The installed environment must contain Core plus Portia, apart from ordinary Python/build tooling. No sibling PDS application is a Portia runtime dependency.

The installed wheel must expose:

```text
portia = portia.cli:main
```

The acceptance verifies the installed console-script metadata, `portia --version`, `portia status`, and a real `portia menu` render followed by a clean `Q` exit. The semantic story remains service-driven rather than encoding dozens of interactive prompt positions as an integration contract.

## One continuous deep workspace

The complete story uses one fresh synthetic workspace beneath the Issue #92 representative deep-root geometry:

```text
target absolute workspace length: at least 119 characters
```

The scenario does not create a shallow semantic workspace and a separate deep-path workspace.

Realistic story operations exercise the Issue #92 path-hardening surfaces where naturally reached:

```text
guarded replacement
technical storage history
coordinated staging
recovery staging
derived / Integrity state
teacher-reference export
```

New writes use the accepted bounded layouts. Existing legacy path layouts remain reader compatibility surfaces and are not migrated merely because Issue #53 runs.

The acceptance does not inspect, require, or mutate Windows `LongPathsEnabled`.

## Identity and record coherence

Core remains authoritative for school-year, class, roster, and class-qualified student identity.

The synthetic workspace contains two exact classes with deliberately colliding local student/display values. Qualification proves that:

```text
(class A, student X) != (class B, student X)
```

unless an independent accepted authority says otherwise.

Workspace Actors are created through `ActorDirectoryService`. Actor reuse across class-owned Portia contexts remains valid while:

```text
Actor identity != roster student identity
Actor relationship != institutional / legal authority
display text != identity key
```

The primary Event and its Participants, Roles, Account, Observation, Review/judgment, Response, Communication, Support Process, planning records, Implementation, Fidelity, and Follow-Up are created through their production services.

The story does not infer responsibility, misconduct, diagnosis, risk, causation, effectiveness, legal authority, Outcome, Support Process completion, or workspace-global student identity merely from record presence.

## Correction, conflict, and recovery

The representative correction is a real material correction through the accepted family service.

Qualification proves:

```text
predecessor remains exact historical evidence
successor becomes current
historical references remain pinned
technical storage history preserves accepted prior bytes
```

A deliberate stale-fingerprint update must fail closed with zero unintended mutation.

A separate coordinated operation is interrupted through the accepted FaultHook seam. The resulting partial state is inspected without mutation, then recovery resumes only the exact safe remaining writes.

Qualification proves:

```text
accepted writes are not replayed
staged intent remains exact
terminal operation state reaches completed
second recovery is idempotent
```

A fresh process then reloads the workspace independently of the original in-memory service objects and verifies current and historical state from durable bytes.

## Privacy and read-only surfaces

Student-view projection remains bounded by the accepted Issue #48 privacy policy. Actor contact data and unrelated operational state do not become student-view output.

Core module-operations readiness/attention discovery remains read-only and privacy-minimal. Shared results do not widen into private student narrative, contact data, or workspace internals.

Teacher-reference export remains one exact deliberate local export under the accepted Issue #51 policy. Export discovery/projection does not use live Actor/Core enrichment to widen the reviewed scope, and verified export history remains immutable.

A deterministic byte snapshot proves zero workspace mutation across the read-only phase covering:

```text
student timeline/view queries
attention queries
Core readiness/attention provider invocation
teacher-reference export history verification
exact historical loads
```

Failure reporting is intentionally bounded and must not dump canonical record bodies, arbitrary filesystem inventories, environment variables, or contact values.

## Integrity and path integration

The interrupted operation produces explicit integrity/recovery evidence rather than silently hiding inconsistent state.

After safe recovery, the representative operation has no unexpected blocking Integrity Finding. The selected Integrity projection uses the bounded Issue #92 `derived-v2` namespace.

The deep-path integration stage also proves that the realistic correction/recovery/export story reaches bounded technical-history, staging, derived-state, and export locations without manufacturing old writer layouts.

## No fixture bypass

Issue #22 remains a semantic reference and regression oracle only.

The Issue #53 installed story must not:

```text
read Issue #22 fixture JSON
-> copy it into canonical Portia storage
-> call load-only services
-> present that as end-to-end acceptance
```

The smoke self-audits its embedded runtime probes and rejects:

```text
Issue #22 / source-fixture reads as canonical authority
direct filesystem canonical writes
direct storage/staging writer imports
direct PortiaRepository canonical mutation
```

`parse_portia_record(...)` remains appropriate for deliberate synthetic inputs that are then submitted through the owning production workflow service.

Direct filesystem setup is limited to test-owned environment scaffolding and explicit fault/corruption seams owned by the acceptance.

## Distribution qualification

The dedicated package checker is:

```text
python scripts/check_issue53_package.py dist
```

It verifies, at minimum:

```text
Portia 0.2.0 metadata
pds-core>=0.6.3,<0.7 compatibility floor
exact console and module-operations entry points
Event / evidence / judgment runtime
Response / Communication runtime
Support / Implementation / Fidelity / Follow-Up runtime
Actor Directory runtime
recovery / Integrity runtime
student-view runtime
attention / readiness provider runtime
teacher-reference export runtime
Issue #92 path-hardening runtime
Issue #53 smoke / qualification / validation evidence in the sdist
no source/repository fixture content in the runtime wheel
```

The generic package inventory and cumulative repository validator are updated only at final Issue #53 closeout so the authoritative gate remains one cumulative path.

## Authoritative repository qualification

The final closeout command is:

```text
python scripts/validate_repository.py \
  --core-wheel <pds_core-0.6.4-py3-none-any.whl> \
  --historical-core-wheel <pds_core-0.6.3-py3-none-any.whl>
```

At final wiring, the cumulative order is:

```text
historical source validators
-> full pytest
-> Ruff
-> strict mypy
-> pip check
-> clean build
-> Twine
-> generic and historical package checks
-> Issue #53 package check
-> historical installed smokes
-> Issue #52 Core 0.6.4 provider smoke
-> Issue #92 deep-workspace smoke
-> Issue #53 representative installed end-to-end smoke
-> git diff --check
```

The final terminal success boundary becomes:

```text
Portia Issue #53 repository qualification passed
```

Observed test counts are intentionally not hard-coded as acceptance authority. The committed validator output, committed source HEAD, and exact candidate artifact identity are the execution evidence.

Until the final repository wiring and cumulative run have actually passed from committed HEAD, this document describes the required Issue #53 evidence contract; it does not claim final repository qualification.

## Backward compatibility

Issue #53 requires no workspace migration and does not automatically:

```text
rewrite existing Portia records
rewrite Actor identity
retarget exact references
convert old technical history
rewrite legacy derived state
rewrite old staging evidence
change Core roster identity
change accepted v0.2 schema meaning
```

Any defect exposed by the representative story must be repaired narrowly while preserving accepted historical readers and exact-reference semantics.

## Issue #54 handoff

Issue #53 produces integrated installed-runtime evidence for the final v0.2.0 audit.

Passing Issue #53 means:

```text
representative installed runtime coherence proven
```

It does not mean:

```text
v0.2.0 release approved
```

Issue #54 remains responsible for the final review of ethical neutrality, teacher authority, privacy/data minimization, record distinctions, recovery/error behavior, usability, architecture, release artifacts, and the release decision.
