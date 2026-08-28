# Event, Participant, Role, and Work Relationship workflows

Issue #40 provides the application-service layer in `portia.workflows`. The
services accept immutable runtime records and exact typed references, assemble
authoritative facts outside validation, validate an in-memory graph, apply
Quarantine prerequisites, and persist through `PortiaRepository` or the Issue #38
coordinated canonical gate.

## Domain meaning

An Event is a bounded occurrence or context. Creating or activating one does
not establish truth, misconduct, cause, responsibility, credibility, risk,
discipline, or outcome.

A Participant has Event-local identity. Participant identity is not person
identity: the same person in two Events has two Participant records, and two
records are never merged because they share a name, display snapshot, Actor, or
roster student. The accepted subject branches remain separate:

- `roster_student`, resolved only by exact `(class_id, student_id)` through
  `CoreRosterResolver`;
- `actor`, resolved exactly through `ActorDirectoryService`;
- `descriptive_person`, retained without directory lookup or promotion;
- `unknown_person`, retained without identity inference.

Display snapshots are historical display data, not identity.

A Role is optional, separate, and neutral. It does not express a finding,
accusation, credibility decision, severity, discipline, or classification.
`reported_involved` remains explicitly qualified as reported.

A Work Relationship is an explicit source-owned canonical record.
`draws_context_from` means only that the source draws context from the exact
target. It does not mean causation, corroboration, evidentiary support,
agreement, ownership, truth, or supersession. Relationships are never inferred
and neither endpoint is mutated.

## Public API

`EventWorkflowService` provides `create`, `load_exact`, `resolve_exact`,
`replace`/`revise`, bounded `list`, and `require_current_use`/
`resolve_current`.

`ParticipantWorkflowService` provides the same guarded persistence and exact
resolution split, Event-bounded listing, `resolve_person`, and
`require_current_use`. `ParticipantPersonResolution` exposes the exact
Participant, its explicit subject kind, and the resolved roster/Actor authority
when that branch has one.

`RoleWorkflowService` provides guarded create/revision, exact load, Event and
Participant-bounded listing, and current-use evaluation.

`WorkRelationshipService` provides guarded create/revision, source-bounded
listing, exact endpoint resolution, exact historical resolution, and current
use evaluation.

Reference helpers (`event_reference`, `participant_reference`,
`role_reference`, and `relationship_reference`) construct exact public
references without filesystem knowledge.

## Lifecycle and immutable creation facts

Ordinary `replace`/`revise` calls use the accepted ADR lifecycle transitions;
schema-valid state changes are not automatically legal application changes.
Cancelled, invalidated, and superseded records cannot be resurrected. Event
draft, active, and closed transitions follow ADR 0005, while Participant, Role,
and Work Relationship proposed/active/terminal transitions follow their
accepted child lifecycle. The repository's existing revision history remains
the canonical storage mechanism; the workflow layer does not create a second
lifecycle store.

Persisted identity plus `creation_source`, `created_at`, and `created_by` are
immutable under ordinary replacement. A Role's Participant target is also
immutable, and material corrections to an active Role's type, basis, or detail
require a successor. Work Relationship type, exact source, and exact target are
immutable; endpoint or provenance correction requires a successor rather than
in-place retargeting. Rejections occur before canonical mutation.

## Event and Role activation prerequisites

A draft Event may be created without Participants. A standalone active or
closed Event cannot be created because that write cannot simultaneously supply
the minimum Participant state. Activation and coordinated bundle publication
evaluate the intended post-operation set and require at least one valid active
Participant for an active or closed Event. An active Event cannot lose its
final active Participant, and an active Participant cannot transition away
while an active Role still depends on it.

ADR 0006 permits an active Role beneath a draft or active Event when its exact
Participant is active and its other prerequisites are satisfied. This supports
assembly and review: the Role is not eligible for ordinary current-use
visibility until the Event is active. `require_current_use` therefore remains
stricter than activation and requires active Role, Participant, and Event
representations.

## Work Relationship endpoint eligibility

Active relationship use is consumer-specific rather than a blanket
`status == active` check. An Event source may be draft, active, or closed; a
Support Process source may be proposed or active. The exact contextual Event
target may be active or closed, because a valid closed Event remains usable as
historical context. Draft, cancelled, invalidated, or superseded targets and
terminal/unusable sources are rejected. Exact historical resolution remains
available independently and never follows a successor.

## Validation context and authority

`WorkflowContextAssembler` discovers every distinct roster reference in the
complete bounded graph and resolves all of them before constructing a
`KnownValidationContext`. It never supplies an incomplete closed known set.
Consequently, unqueried authority remains unknown rather than becoming false.
Core/sibling work existence remains `None` unless a comprehensive public
authority was actually queried.

Actor-backed records use exact Actor Directory reads. Historical resolution
does not require current lifecycle eligibility; current use additionally
requires the Actor's accepted active/current-use path. No successor is followed,
no Actor is substituted, and no Actor is auto-created.

`validate_record_graph()` remains I/O-free. The direction is always resolver
and repository reads, authoritative in-memory context, graph validation, then
guarded persistence.

## `reported_involved` Account prerequisite

Issue #40 only reads Account authority. An active `reported_involved` Role must
reference an exact Account contract representation in the same Event. At least
one referenced Account must be active, have a qualifying represented source
(`roster_student`, `actor`, `local_operator`, or `descriptive_person`), and
target the Role's exact Participant or a Participant set containing it. An
Event-wide, retracted, invalidated, superseded, unidentified-source,
wrong-version, wrong-Event, or target-misaligned Account does not qualify.
Account Quarantine current-use effects also apply.

The Role workflow never creates, edits, activates, retracts, reviews, or
silently retargets an Account.

## Exact history, current use, and Quarantine

Every exact load requests a contract version and returns that representation
without following successors. Superseded or inactive records may remain
historically readable. Current-use APIs separately require the production
contract version, active lifecycle state, eligible exact dependencies, and the
`block_current_use` Quarantine check.

Writes apply `block_work_writes`. Quarantine is not lifecycle: it never changes
status and never makes historical data appear absent. Corruption and
recovery-required conditions retain their storage-layer error types.

Workflow-specific failures are limited to `WorkflowValidationError` (which
retains all application findings), `WorkflowOwnershipError`, and
`WorkflowPrerequisiteError`. Repository conflicts, absence, Quarantine,
corruption, identity resolution, and recovery errors are not flattened.

## Bounded reads and persistence

`PortiaRepository` strictly enumerates Events within one class, Participants or
Roles within one Event, Roles filtered to one Participant, and Relationships
within one exact source work. Enumeration is deterministic, non-recursive, and
rejects malformed records, filename/identity disagreement, wrong ownership, and
unexpected collection artifacts.

Single-record changes use repository create/replace methods and expected
fingerprints. `EventBundleWorkflowService` validates a complete typed `EventBundle`
before staging or canonical publication, then reuses Issue #38 target-adjacent
staging, canonical target verification, deterministic operation/work locks,
candidate fingerprints, publication, and partial-commit error behavior. It
does not define another transaction, lock, staging, or journal subsystem.

## Issue #22 ownership

The workflow parity table records that #40 owns the production portion of
P22-01, consumes #39 for P22-03, assembles authority for G22-009, and guarantees
no successor following for G22-010. G22-017 is shared with #41 because #40
validates existing Account authority while #41 owns Account mutation.

## Issue #41 handoff

Issue #41 should use `EventWorkflowService.load_exact`/`require_current_use`,
`ParticipantWorkflowService.load_exact`/`require_current_use`, and the exact
reference helpers to enforce Event ownership. It may reuse
`WorkflowContextAssembler` when validating complete Account/Observation graphs.
After creating a qualifying Account, it should call
`RoleWorkflowService.require_current_use` (or submit a guarded coordinated
proposal) to revalidate `reported_involved`.

Issue #41 must use `PortiaRepository` and the existing coordinated persistence
machinery rather than creating another Event identity, transaction, lock,
staging, or journal layer. Issue #41 owns Account creation, editing/revision,
review/retraction workflows, and Observation creation/editing. Issue #40 owns
the Event, Participant, Role, and Work Relationship services those workflows
consume.
