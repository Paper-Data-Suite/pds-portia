# Portia runtime models and application validation

Issue #37 translates the accepted Portia foundation into executable Python
without changing the published JSON contracts. The runtime layer is deliberately
separate from persistence and teacher workflows.

## Layering

The executable boundary is:

```text
public JSON wire value
  -> exact contract/version parser
  -> immutable Portia runtime record
  -> in-memory application validation
  -> later storage/workflow services
```

JSON Schema and application validation remain distinct. A record can satisfy its
public schema and still be application-invalid because an exact reference does
not resolve, resolves in another work, requests another historical version, or
violates an accepted cross-record rule.

`portia.models` performs local wire/model validation. `portia.validation`
performs cross-record checks. Neither layer reads a workspace or accesses the
network.

## Immutable representation

Every modeled public record has a version-explicit frozen/slot-based runtime
class such as `EventV2`, `EventParticipantV3`, `AccountV2`, or
`OperationJournalV2`. `parse_portia_record(contract, version, value)` dispatches
only to the exact requested class.

A record retains the complete public JSON object as deeply immutable data:

- objects become read-only mappings;
- arrays become tuples internally;
- scalar lexical content is not normalized;
- `to_dict()` returns a fresh JSON-native copy;
- an explicit JSON `null` remains different from an absent property;
- parsing never follows a successor or performs a migration.

The version-specific class is part of runtime identity. Historical Event,
Participant, Role, Work Relationship, Account, Observation, and operational
representations therefore remain historical when read.

Reusable high-value values are separately typed, including class-qualified
roster references, Actor references, exact historical Actor/Contact Point/Actor-
Student Relationship references, local and exact-local record references, Portia
work and exact work/work-record references, Core module work/record references,
Event and Support Process target unions, judgment-evidence references,
`PlannedSchedule`, attribution, creation provenance, display snapshots,
identifiers, and explicit-offset timestamps. `PlannedSchedule` is planning-only:
constructing or reading one never creates an Implementation record.

## Current implementation targets

The primary version transitions relevant to v0.2 are:

| Contract | Runtime target | Retained historical reads |
| --- | --- | --- |
| Event | v2 | v1 |
| Event Participant | v3 | v1, v2 |
| Event Participant Role | v3 | v1, v2 |
| Work Relationship | v2 | v1 |
| Account | v2 | v1 |
| Observation | v2 | v1 |
| Actor Directory families | v1 | — |
| Review / Classification / Hypothesis / Determination | v1 | — |
| Response / Communication | v1 | — |
| Support Process through Fidelity | v1 | — |
| Follow-Up / Outcome / Reentry / Repair | v1 | — |

The complete machine-readable disposition is
`portia/runtime-coverage.json`. It distinguishes:

```text
current_v0_2
historical_read
supporting_v0_2
deferred_v0_3
noncanonical_not_modeled
core_owned
```

`validate_runtime_models.py` checks that every catalog-required entry still
exists in `schemas/schema-catalog.json` and that modeled entries exactly match
the public Python registry.

## Runtime schema bundle

The source repository keeps the accepted schemas as the structural authority,
but the installed wheel does not ship the repository schema tree and does not
require `jsonschema` at runtime.

During a wheel build, `setup.py` uses the stdlib-only
`portia._bundle_builder` to:

1. read the explicit runtime coverage matrix;
2. select only modeled contract/version roots plus the explicitly published
   reusable-value schemas exposed by `portia.models`;
3. follow their transitive Portia `$ref` closure;
4. preserve each canonical `$id` and schema unchanged; and
5. write one deterministic `portia/_runtime_contract_bundle.json` resource.

The production validator implements the Draft 2020-12 keywords used by that
accepted closure with the standard library. In an editable source checkout, the
same bundle is compiled in memory from repository schemas when the built
resource is absent. Structural semantics are therefore shared between source
and installed-wheel use without making repository paths runtime authority.

`jsonschema` remains a development/test dependency and continues to be the
independent foundation oracle. The Issue #37 round-trip tests serialize typed
records back to their exact JSON-native form while the existing Phase 1 suite
continues to validate the public schemas independently.

## Core-owned values

Portia does not publish competing versions of Core-owned shared identities.
`ModuleWorkRecordRef` composes Core's public `ModuleWorkRef` and
`ModuleRecordRef` runtime classes and converters. Local structural validation
never claims that a Core class, work, roster student, route, or record exists.

Application validation may receive a bounded `ValidationContext`. The default
context reports external existence as unknown. `KnownValidationContext` is a
deterministic in-memory implementation for callers that have already obtained
authoritative Core facts. Validation itself performs no I/O.

Issue #39 provides that production bridge without changing this boundary.
Issue #40 composes it with the I/O-free validator and guarded storage through
`portia.workflows`; validation itself still performs no I/O.
`CoreRosterResolver` performs exact Core 0.6.3 roster I/O outside
`portia.validation`; `ResolvedIdentityValidationContext` carries successful exact
student resolutions as positive facts, while `RosterSnapshotValidationContext`
may report absence only inside classes whose complete rosters were successfully
loaded. Unchecked classes remain unknown. This preserves the distinction between
"not resolved" and "authoritatively absent" while keeping
`validate_record_graph()` deterministic and I/O-free.

## Application findings

`validate_record_graph()` returns immutable `ApplicationFinding` values instead
of requiring callers to parse exception text. Finding codes describe record
integrity only. They do not classify behavior, infer culpability, score risk,
make credibility determinations, infer effectiveness, or elevate a teacher-local
record into institutional truth.

The first production rules include:

- duplicate exact canonical identities;
- duplicate work roots;
- absent containing work roots in complete-graph validation;
- exact child references that are unresolved, point to another work, or request
  another contract version;
- exact Portia work references that are unresolved, cross class boundaries, or
  request another version;
- duplicate canonical participant identity in selected-target collections;
- timestamp chronology;
- Core module-work/module-record producer mismatch;
- optional authoritative roster/Core-work existence checks;
- Actor/Contact Point/Communication resolution and active-state checks;
- active judgment dependency on a completed Review where required; and
- self/cyclic supersession.

The validator operates on an in-memory sequence of immutable records. Filesystem
placement, expected revisions, durable fingerprints, current pointers, locking,
journaling, replay, and recovery belong to Issue #38.

## Issue #22 parity

`portia.validation.issue22_parity` classifies every one of the 52 accepted
Issue #22 scenarios exactly once. The matrix deliberately distinguishes three
cases:

- `covered_by_37`: the scenario's principal invariant is observable from the
  in-memory v0.2 record graph;
- `deferred_to_v0_3`: paper/import behavior explicitly deferred by the v0.2
  milestone;
- `outside_37_runtime_boundary`: a later service must supply information that is
  not present in the public record graph, such as canonical filesystem
  placement, an actual resolver result, a rejected write attempt, durable
  readback/fingerprint state, privacy-projection output, or foreign-custody
  verification.

The latter category is not a waiver of the foundation invariant. It prevents
Issue #37 from fabricating storage/resolver/policy facts that only later owning
services can know. Each entry carries a rationale, and covered graph-invalid
entries map their foundation finding to one or more production finding codes.

Tests additionally round-trip every Issue #22 public record whose exact
contract/version is modeled by #37. No production module imports the Issue #22
test-only graph validator.

## Explicit v0.3 deferral

The following operational families remain intentionally unmodeled in #37:

```text
Capture Batch
Page Target
Page Record
Paper Interpretation
Capture Proposal
Capture Review
Capture Materialization
Import Batch
Import Source Record
Import Proposal
Import Review
Import Materialization
```

Their accepted schemas remain frozen foundation inputs. They will receive
production runtime/workflow treatment with Portia v0.3 paper and structured
import work.

## Issue #38 persistence boundary

Issue #37 does model the public operation, integrity, quarantine, source
snapshot, derived-state pointer/metadata, and related supporting contracts that
canonical persistence needs. Issue #38 now executes that persistence boundary
without changing those contracts. The accepted catalog does not define a
standalone persisted `derived_generation` record; generation identity is
represented through the accepted generation references, source snapshots,
metadata, and current-pointer contracts. #37 does not invent an additional
record family.

`portia.storage` consumes the immutable models while implementing deterministic
workspace paths, immutable operational revisions, explicit current pointers,
expected-fingerprint checks, append-preserving coordinated writes, exact
readback, explicit recovery, Quarantine controls, and rebuildable derived-state
generation storage. Canonical repository methods parse through the exact runtime
model registry rather than treating anonymous dictionaries as domain authority.

Storage-level Issue #22 parity is tracked separately in
`portia.storage.issue22_parity`: persistence-owned cases are executed here while
resolver, privacy/export, projection-builder, domain-intent, and foreign-custody
cases remain with their owning later services. See `storage.md` for the detailed
filesystem and recovery contract.
