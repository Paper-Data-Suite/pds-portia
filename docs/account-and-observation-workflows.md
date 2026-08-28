# Account and Observation workflows

Issue #41 provides the production application-service layer for Portia source
evidence. It turns the accepted Account/Observation contracts from ADR 0011 into
guarded Event- and Support-Process-owned workflows while preserving the central
domain boundary:

```text
Account
= one coherent attributed statement, report, response, recollection, or perspective

Observation
= one coherent attributed or instrumented record of directly observable,
  counted, timed, recorded, or measured information
```

Neither record is a finding, credibility judgment, Classification, Hypothesis,
Determination, policy violation, severity judgment, diagnosis, intent claim,
behavioral-function claim, guilt judgment, risk score, or Outcome.

## Public API and version policy

`AccountWorkflowService` provides guarded `create`, exact `load_exact` /
`resolve_exact`, bounded `list`, `require_current_use` / `resolve_current`,
coordinated `transition_lifecycle`, material `correct`, and source-evidenced
`retract` operations. `account_reference()` constructs exact Account references.

`ObservationWorkflowService` provides guarded `create`, exact `load_exact` /
`resolve_exact`, bounded `list`, `require_current_use` / `resolve_current`,
coordinated `transition_lifecycle`, and material `correct` operations.
`observation_reference()` constructs exact Observation references.

The writer/reader policy is deliberately asymmetric:

```text
new Account writer      -> account@2
new Observation writer  -> observation@2
exact Account reader     -> account@1 or account@2
exact Observation reader -> observation@1 or observation@2
```

Version 1 remains immutable Event-local history. Version 2 is required for new
digital-entry records and supports either `event@2` or `support_process@1`
ownership. No read or write silently migrates v1 to v2, guesses a latest version,
or follows a successor.

## Ownership and targets

Every evidence operation starts from one exact owner. Event evidence must agree
with the selected `event@2` class/work identity and use the Event target family.
Support Process evidence must agree with the selected `support_process@1`
class/work identity and use the Support Process target family. Participant targets
resolve exactly inside the owner:

```text
Event            -> event_participant@3
Support Process  -> support_process_participant@1
```

Account/Observation v1 is Event-local and cannot be reinterpreted as Support
Process evidence. A Support Process does not require a fabricated Event.

The source, observer, target, recorder, and owner remain separate facts. Exact
Core roster identity uses `class_id + student_id` through `CoreRosterResolver`.
Actor-backed attribution resolves through `ActorDirectoryService`. Display
snapshots are historical display data, not identity, and name/fuzzy matching is
not an authority path.

## Exact history versus current use

Exact reads return the requested persisted representation even when it is no
longer eligible for current use. They do not normalize, migrate, repair, select a
successor, or mutate storage.

Current-use checks are stricter. They require an eligible lifecycle state,
eligible exact owner and targets, current represented-source/observer authority
where applicable, source-artifact authority where applicable, and Quarantine
permission. A historical v1 representation can remain current-use eligible when
its exact persisted authority still satisfies the accepted rules; it is not
upgraded merely to make that possible.

## Mixed-version enumeration

Account and Observation versions share their canonical collections:

```text
records/account/<account_id>.json
records/observation/<observation_id>.json
```

`PortiaRepository` therefore enumerates these collections by inspecting each
record's declared contract/version rather than parsing the entire directory as a
caller-selected version. Supported v1/v2 representations are parsed exactly and
validated against filename, logical identity, owner, and canonical path.
Malformed records, wrong contracts, unsupported versions, and ownership/path
mismatches are corruption or ownership errors rather than skipped entries.

Issue #38 recovery state is target-adjacent. The exact reserved
`.portia-staging/` directory is excluded from canonical enumeration while an
operation requires recovery; every other unexpected collection artifact remains
an error. A `.portia-staging` file or symlink is not treated as reserved recovery
state.

## Lifecycle history and ordinary transitions

Account and Observation domain lifecycle changes are not naked JSON status
replacements. `transition_lifecycle` persists an exact `lifecycle_transition@1`
record and the evidence status update coherently through Issue #38 coordinated
persistence. The transition uses the public same-work `local_record` target and
links to the unique exact persisted previous lifecycle head.

The canonical evidence representation, domain lifecycle history, and private
technical storage history remain distinct. Prior exact bytes are retained for
storage/recovery evidence, while `lifecycle_transition@1` is the domain history.
Partial durable commits retain accepted bytes and operation locks and surface
`PortiaOperationPartialCommitError`; Portia does not delete accepted effects to
simulate rollback.

Ordinary transitions are limited to the accepted lifecycle matrix. Primary
evidence fields cannot be edited in place. Creation provenance remains immutable,
and terminal records are not resurrected.

## Account relations and retraction

Account v2 supports exact same-work `reports_from`, `clarifies`, and `retracts`
relations. Ordinary creation may author `reports_from` and `clarifies` after exact
lineage checks. `reports_from` is compatible with secondhand/mixed origin;
`clarifies` requires the same represented source. Relation ancestry is bounded,
exact, and cycle-checked. Relations do not mean corroboration, truth, credibility,
or adjudication.

`retracts` is reserved for `AccountWorkflowService.retract()`. Retraction is
source-evidenced, not a teacher lifecycle toggle. The operation creates a new
active v2 Account from the same represented source containing the exact retraction
relation and coordinates the active predecessor to `retracted` with reason
`source_retracted`. Retraction means that the represented source no longer stands
behind the prior Account; it does not mean the prior Account was false. The prior
Account remains exactly readable, and reaffirmation would be new evidence rather
than reactivation.

## Material correction and supersession

Material evidence correction creates a new v2 successor and coordinates the
exact predecessor to `superseded`. It never overwrites the predecessor's evidence
payload. Account correction covers source/attribution, target, statement content
or representation, information origin, evidence timing, and source provenance.
Observation correction covers observer/instrument, target, observable content,
measurement, timing, method, and source provenance.

A correction must actually change material evidence and use a reason consistent
with that changed dimension. Supersession ancestry is exact, bounded, and
acyclic. Historical consumers stay pinned to the predecessor, and later current
consumers must explicitly name the successor rather than relying on implicit
retargeting.

## Source artifacts and `artifact_review`

`source_artifact_ref@1` is provenance/location context, not authenticity,
accuracy, authorization, credibility, or proof. Binary source material is not
embedded in Account or Observation JSON.

Issue #41 can establish current-use authority for two source-artifact branches:

- `workspace_file`: the path must resolve inside the selected workspace and its
  SHA-256/byte-length fingerprint must match the current bytes;
- `portia_work_record`: the exact Portia work-record reference must resolve
  exactly.

Workspace-file authority is rechecked on current use. Later byte drift therefore
makes dependent evidence ineligible for current use without erasing the exact
record. Losing source-artifact authority does not prevent an already-active record
from being invalidated.

`paper_capture`, `module_work_record`, and `external_record` may remain
structurally preserved in proposed/historical records, but Issue #41 cannot use
them as current-use authority. It does not implement PDS2 review/materialization,
a private sibling-module record reader, or automatic external dereferencing.

An Observation whose method is `artifact_review` must name at least one source
artifact. Artifact review means the observer directly examined the artifact; it
does not imply presence at the original Event or authenticate the artifact.

## `reported_involved` Role integration

Issue #40 owns Role records; Issue #41 owns Account authority. An active
`reported_involved` Role still requires an exact same-Event Account that is
attributable, target-aligned to the Role Participant, and otherwise qualifying.
Role current-use now delegates candidate Account eligibility to
`AccountWorkflowService.require_current_use()`.

Consequently, retraction, invalidation, supersession, lifecycle-history mismatch,
Quarantine, stale targets, Actor/roster authority loss, or source-artifact drift
can make an exact basis Account nonqualifying. The Role itself is not silently
mutated, invalidated, superseded, or retargeted. If another exact basis Account
independently qualifies, it may satisfy the Role. Observation-only evidence never
satisfies the `reported_involved` Account prerequisite.

## Quarantine, recovery, and write boundary

All canonical writes remain behind `PortiaRepository` or the existing Issue #38
coordinated persistence machinery. Issue #41 adds no transaction, journal, lock,
or staging subsystem. `block_work_writes` applies to mutation; `block_current_use`
applies to current-use authority. Quarantine is operational state, not lifecycle,
and never makes historical bytes disappear.

Conflict, corruption, identity-resolution, Quarantine, and recovery-required
errors retain their typed lower-layer meaning. Workflow validation/ownership/
prerequisite errors are used only for application-service failures introduced at
this boundary.

## Digital-entry and privacy boundary

Executable #41 authoring is `digital_entry` only. Published paper/import wire
representations remain immutable and historically readable, but OCR, structured
import, capture review/materialization, and paper/import activation belong to the
later executable paper/import workflow. #41 fails closed rather than pretending
schema-valid provenance has been reviewed.

Account and Observation remain source evidence. The workflows do not infer or
create Review, Classification, Hypothesis, Determination, Response, Support,
Outcome, responsibility, credibility, corroboration, or culpability. Conflicting
Accounts coexist. Sensitive source text is not copied into operation journals,
locks, derived summaries, or diagnostics merely to describe a storage operation.

## Downstream handoff

Issue #42 and later interpretation workflows may consume exact historical or
current Account/Observation references subject to their own authority rules. They
must not reinterpret source evidence as an automatic finding and must preserve the
same exact-reference/no-silent-successor boundary established here.
