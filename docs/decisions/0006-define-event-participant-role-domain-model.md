# ADR 0006: Define the Initial Event Participant Role Domain Model

* **Status:** Accepted
* **Date:** 2026-07-24
* **Decision owners:** Portia maintainers
* **Related issue:** [#8 — Define the initial Event Participant Role domain model](https://github.com/Paper-Data-Suite/pds-portia/issues/8)
* **Related design:** [`docs/design/portia-event-and-participant-domain-model.md`](../design/portia-event-and-participant-domain-model.md)
* **Related schema:** [`schemas/event-participant-role.schema.json`](../../schemas/event-participant-role.schema.json)
* **Related examples:** [`docs/examples/portia-event-participant-role-examples.md`](../examples/portia-event-participant-role-examples.md)
* **Related decisions:**
  * [`0001-establish-portia-record-distinctions.md`](0001-establish-portia-record-distinctions.md)
  * [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)
  * [`0003-adopt-teacher-local-initial-deployment.md`](0003-adopt-teacher-local-initial-deployment.md)
  * [`0004-define-portia-identity-ownership-and-storage.md`](0004-define-portia-identity-ownership-and-storage.md)
  * [`0005-define-event-and-participant-domain-model.md`](0005-define-event-and-participant-domain-model.md)

## Context

ADR 0001 requires Portia to preserve distinctions among Events, Accounts, Observations, interpretations, Classifications, Hypotheses, Determinations, Responses, Supports, Follow-Ups, and Outcomes.

ADR 0002 establishes Portia as Paper Data Suite’s contextual behavior-support and response module. Portia may reference instructional and assessment context, but it does not evaluate academic work or calculate grades.

ADR 0003 establishes the initial deployment as teacher-local, classroom-focused, and based on one selected Paper Data Suite workspace.

ADR 0004 establishes:

* one owning Core class for each Event;
* one canonical class-scoped Event work root;
* roster-qualified student identity using `class_id + student_id`;
* explicit cross-class student participation within the teacher workspace;
* a limited workspace-scoped Actor Directory;
* one canonical direction for relationships;
* and derived rather than authoritative histories, indexes, reverse links, and projections.

ADR 0005 establishes:

* bounded Event roots;
* separate Event Participant records;
* explicit Event and participant lifecycles;
* participant identity variants;
* replacement-based identity correction;
* record-specific creation provenance;
* paper-assisted capture;
* and the requirement that Event Participant identity remain separate from Event-level role.

ADR 0005 intentionally deferred the Event Participant Role contract.

An Event Participant identifies:

```text
who is connected to the Event
```

An Event Participant Role identifies:

```text
how that participant is connected to the Event
```

Those are separate claims.

Embedding a Role in the Event Participant would make identity depend on an optional and correctable contextual assertion. Embedding all Roles in one Event root would make participant-specific lifecycle, provenance, basis, correction, and privacy projection difficult to preserve.

The Role model must support:

* zero, one, or several compatible Role assertions for one participant;
* direct reviewed digital entry;
* paper-derived proposals;
* imported proposals;
* explicit uncertainty;
* attributed reported involvement;
* correction without rewriting history;
* coordinated supersession;
* and low-friction teacher workflows.

Role terminology must remain neutral. A Role must not itself establish:

* blame;
* guilt;
* fault;
* intent;
* credibility;
* severity;
* policy violation;
* institutional responsibility;
* or a formal Determination.

## Decision

Portia will represent each Event Participant Role as a **separate canonical Event-local assertion with one participant, one role type, its own lifecycle, its own creation source, an optional or conditionally required structured basis, and replacement-based correction**.

The principal decisions are:

1. One Role record represents one Event-local assertion that one Event Participant has one role type.
2. Roles are separate canonical child records beneath the Event.
3. A Role references one Event Participant through `participant_id` and does not embed participant identity.
4. A participant may have no Role, one Role, or several compatible Roles.
5. No Role is required for Event or Event Participant validity.
6. The initial neutral vocabulary is `directly_involved`, `present`, `reported_involved`, and `contextual`.
7. Judgmental and workflow-specific relationships are excluded from the generic Role vocabulary.
8. Each Role has its own lifecycle, creation source, operator provenance, basis, correction lineage, and supersession relationships.
9. Role creation source is independent from the Event, Event Participant, basis, and prior Role.
10. A paper-derived Role uses only `paper_capture / ingested`.
11. Every paper-derived Role contains a matching paper basis entry.
12. Every active `reported_involved` Role references a same-Event attributed Account.
13. Top-level `detail` is permitted only for `contextual`.
14. A proposed `contextual` Role may omit detail; an active or superseded one retains valid detail.
15. Same-Event Account and Observation basis references use compact record references.
16. One successor may replace one or several prior Roles through structured `supersedes` entries.
17. Supersession becomes effective only when the successor becomes active.
18. Direct reviewed creation as active is permitted.
19. Role activation requires an active Event Participant and an Event whose status is `draft` or `active`.
20. Persisted `participant_id` is immutable.
21. Invalidated and superseded Roles are terminal under ordinary workflows.
22. Account and participant lifecycle changes coordinate dependent Role transitions.
23. Canonical Role records are not hard-deleted through ordinary workflows.
24. JSON Schema enforces local record shape.
25. Application validation enforces cross-record, lifecycle, path, chronology, compatibility, dependency, and transaction invariants.
26. Internal rigor must remain largely invisible during routine teacher use.

## Canonical Record and Storage

Each Role is stored beneath its owning Event:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  records/
    event_participant_role/
      <role_id>.json
```

The top-level `class_id` is the Event’s owning Core class.

It is not necessarily the source-roster class of a roster-student participant.

The Role record declares:

```text
schema_version
record_type
module_id
class_id
work_id
role_id
participant_id
status
role_type
creation_source
created_at
created_by
updated_at
updated_by
```

It may also contain:

```text
basis
detail
supersedes
```

Constants and identifier forms are:

```text
record_type = event_participant_role
module_id = portia
role_id = epr_<opaque-id>
work_id = owning Event ID
```

The Role must not contain authoritative embedded:

```text
event
event_id
participant
participant_identity
student_ref
actor_ref
subject
role
roles
participant_roles
superseded_by
replacement_reason
```

The Event scope is inherited from:

```text
class_id + work_id
```

The Role references the Event Participant only through:

```text
participant_id
```

## Semantic Unit and Cardinality

One Role record means:

```text
one Event
+ one Event Participant
+ one role type
+ one lifecycle
```

A Role record does not contain an array of role types.

Several Role types require several Role records.

Each Role therefore receives independent:

* identity;
* status;
* creation source;
* creation and update attribution;
* basis;
* contextual detail where permitted;
* amendment history;
* invalidation history;
* and supersession relationships.

One Event Participant may have:

```text
zero active Roles
one active Role
several compatible active Roles
```

The absence of a Role does not mean:

* unknown involvement;
* no involvement;
* responsibility;
* exoneration;
* or incomplete identity.

Role assignment remains optional.

## Initial Role Vocabulary

The initial Role vocabulary is:

```text
directly_involved
present
reported_involved
contextual
```

### `directly_involved`

The participant directly took part in the occurrence, interaction, or defined observation period.

This Role does not establish:

* fault;
* blame;
* intent;
* severity;
* policy violation;
* credibility;
* or institutional responsibility.

### `present`

The participant was present within the Event context.

This Role does not necessarily establish that the participant:

* directly participated;
* observed every relevant part;
* provided an Account;
* or was responsible for what occurred.

### `reported_involved`

One or more attributed sources described the participant as involved, but Portia is not presenting that relationship as independently established.

The Role must remain visibly qualified as:

```text
reported involved
```

It must not be displayed merely as:

```text
involved
```

A proposed `reported_involved` Role requires at least one source-oriented basis entry.

Before any `reported_involved` Role becomes active, its basis must include at least one same-Event:

```text
account_ref
```

that resolves to an attributed Account.

The Account preserves:

* who supplied the report;
* what was reported;
* and the attribution that makes the reported relationship meaningful.

A paper artifact, import record, free-text note, or teacher confirmation does not substitute for the Account.

### `contextual`

The participant has a legitimate Event-level connection not adequately represented by the other initial types.

Top-level:

```text
detail
```

is permitted only for `contextual`.

A proposed `contextual` Role may omit detail during review.

An active or superseded `contextual` Role must contain concise, neutral, nonempty detail.

An invalidated proposal may omit detail if it never became active.

A formerly active Role that is later invalidated retains its historical detail.

`contextual` must not become a generic fallback for unsupported labels.

## Excluded Labels and Relationships

The generic Role vocabulary must not include judgmental labels such as:

```text
offender
victim
aggressor
perpetrator
guilty
innocent
responsible
responsible_student
problem_student
credible
dishonest
at_fault
```

Those labels may:

* imply a conclusion not established by the Role;
* collapse interpretation into participant identity;
* create durable stigmatizing labels;
* depend on institutional policy;
* or belong in a later Classification, Hypothesis, Determination, or Response model.

Workflow-specific relationships also do not belong in the generic Role vocabulary:

```text
reporter
observer
account_source
response_recipient
response_provider
support_recipient
support_provider
follow_up_owner
decision_maker
```

Those relationships belong to the records whose workflows they describe.

For example:

* an Account identifies its source;
* an Observation identifies its observer or source;
* a Response identifies its recipient and provider;
* a Support record identifies its recipient and provider;
* a Follow-Up identifies its owner;
* and a Determination identifies its authorized decision context.

## Active-Role Compatibility

Portia permits these simultaneous active combinations for one participant in one Event:

```text
present + directly_involved
present + reported_involved
present + contextual
```

Portia prohibits these simultaneous active combinations:

```text
directly_involved + reported_involved
directly_involved + contextual
reported_involved + contextual
```

More than one active Role with the same `role_type` for the same participant and Event is prohibited.

Under the initial vocabulary, one participant can therefore have no more than two active Roles.

Compatibility is evaluated against the intended post-operation active set:

```text
current active Roles
- Roles being effectively superseded
+ successor Role
```

A proposed successor may temporarily conflict with a currently active prior Role while under review.

The conflict becomes invalid only if the successor would be activated without the coordinated supersession operation.

Compatibility is an application-level invariant across separate Role records.

There is no warning-only override.

## Basis

`basis` is an unordered array of structured entries supporting one Role assertion.

Several basis entries do not create several Role assertions.

Array order and entry count do not establish:

* credibility;
* evidentiary weight;
* agreement;
* majority;
* hierarchy;
* or a formal Determination.

The initial basis kinds are:

```text
account_ref
observation_ref
paper_capture
import_source
```

No generic:

```text
teacher_entry
```

basis kind is defined.

A directly reviewed teacher assignment may omit `basis` when no conditional basis requirement applies.

Teacher action remains represented through:

```text
creation_source
created_by
updated_by
lifecycle history
```

Creation provenance is not assertion basis.

### Same-Event Account and Observation References

Account and Observation references are compact:

```json
{
  "kind": "account_ref",
  "record_id": "acct_example"
}
```

```json
{
  "kind": "observation_ref",
  "record_id": "obs_example"
}
```

Their Event scope is inherited from the Role’s:

```text
class_id + work_id
```

They must not repeat:

```text
class_id
work_id
module_id
event_id
```

Application validation confirms that the referenced record:

* exists;
* has the expected record type;
* belongs to the same Event;
* has a lifecycle state eligible for the intended use;
* and satisfies any record-specific attribution requirement.

Cross-Event Account and Observation basis references are prohibited.

### Paper Basis

A paper basis contains:

```text
kind = paper_capture
route_id
page_record_id
```

Every paper-derived Role must contain at least one paper basis entry whose:

```text
route_id
page_record_id
```

exactly match the corresponding Role creation-source fields.

The duplication is intentional:

```text
creation_source
= how the Role entered Portia

paper basis
= which returned artifact supports the assertion
```

The matching entry remains attached while the Role is:

```text
proposed
active
invalidated
superseded
```

Additional valid basis entries may be added, but they do not replace the required matching paper entry.

### Import Basis

An import basis preserves a meaningful source label and may preserve a source-record identifier.

An import basis may support a proposed `reported_involved` Role while attributed Account review is incomplete.

It cannot replace the Account required for activation.

### Basis Mutation

A proposed Role may have its basis edited during review, subject to all conditional requirements.

A paper-derived proposed Role must retain its matching paper basis.

An active Role may receive genuinely additive, non-meaning-changing corroborating basis in place only when:

* participant identity does not change;
* role type does not change;
* substantive meaning does not change;
* existing basis interpretation does not change;
* and append-only amendment history is preserved.

Removing, replacing, or materially changing active basis requires a successor Role and supersession.

When amendment history cannot be preserved reliably, even an additive change uses a successor.

Invalidated and superseded Role basis remains historical and is not edited through ordinary workflows.

## Independent Creation Source

Every Role has its own structured:

```text
creation_source
```

The initial creation-source types are:

```text
digital_entry
paper_capture
import
```

The Role source is independent from:

* the parent Event source;
* the Event Participant source;
* sibling Role sources;
* basis entries;
* the source of a prior Role;
* and the operator who later confirms or edits the Role.

Portia must not infer:

```text
Role source = Event source
Role source = participant source
Role source = first basis kind
Role source = current editor
Role source = prior Role source
```

Creation-source fields are populated by the workflow rather than manually by the teacher.

### Digital Entry

Use:

```json
{
  "creation_source": {
    "type": "digital_entry"
  }
}
```

when the Role is created through Portia’s digital interface.

A digitally created Role remains `digital_entry` even when its Event or participant originated through paper capture or import.

### Paper Capture

A paper-derived Role uses:

```json
{
  "creation_source": {
    "type": "paper_capture",
    "stage": "ingested",
    "route_id": "rt_example",
    "page_record_id": "pg_example"
  }
}
```

For Roles:

```text
paper_capture
→ stage must equal ingested
```

A Role must never use:

```text
stage = preallocated
```

A Role assertion does not exist merely because:

* an Event was preallocated;
* a page was rendered;
* the page contained blank role marks;
* or a participant placeholder existed.

The Role comes into existence only after returned-page processing produces a specific proposed or reviewed assertion.

Pre-render role configuration belongs in the page template, page record, or another generated-paper record—not in a blank canonical Role file.

### Import

Use:

```json
{
  "creation_source": {
    "type": "import",
    "source_label": "Legacy teacher record",
    "external_reference": "import-batch-2026-09-01"
  }
}
```

when the Role originates outside the ordinary digital or generated-paper workflows.

Review does not rewrite an imported Role as `digital_entry`.

### Immutability

The following are ordinarily immutable:

```text
creation_source
created_at
created_by
participant_id
```

Review, confirmation, basis addition, invalidation, and supersession do not rewrite the original creation source.

A successor Role receives its own creation source.

For example:

```text
prior Role:
paper_capture / ingested

corrected successor:
digital_entry
```

The `supersedes` relationship preserves correction lineage.

The successor’s creation source preserves how the corrected assertion entered Portia.

## Role Lifecycle

The initial statuses are:

```text
proposed
active
invalidated
superseded
```

### `proposed`

The Role exists but has not been accepted as a current canonical Event-level relationship.

Roles commonly begin proposed when they arise from:

* paper interpretation;
* automated extraction;
* imported data awaiting review;
* ambiguous participant or role matching;
* incomplete digital entry;
* a participant that is not yet active;
* missing contextual detail;
* or missing attributed Account support.

A proposed successor may contain prospective `supersedes` references.

Those references do not change prior Role status while the successor remains proposed.

### `active`

The Role is currently accepted as a valid neutral Event-level relationship.

Active does not mean:

* substantiated;
* severe;
* disciplinary;
* formally determined;
* or institutionally verified.

A Role may become active through:

```text
direct reviewed creation as active
```

or:

```text
proposed → active
```

Direct active creation is permitted when the complete assertion has already been explicitly reviewed and accepted before persistence.

Portia must not fabricate a proposed lifecycle transition that never occurred.

### `invalidated`

The Role was incorrect, unsupported, duplicated, abandoned during review, or otherwise must not be treated as valid.

Invalidating a Role does not erase the period during which it may previously have been accepted.

`invalidated` is terminal under ordinary workflows.

### `superseded`

A later Role became active and replaced or materially refined the prior Role through a completed supersession operation.

A prior Role does not become superseded merely because:

* a successor file was created;
* a proposed successor references it;
* review began;
* or replacement validation was attempted.

`superseded` is terminal under ordinary workflows.

## Parent-State Requirements

At the moment a Role becomes active:

```text
Event Participant status = active
Event status = draft or active
```

An active Role may therefore exist beneath a draft Event while the teacher completes Event assembly.

Such a Role appears in:

* draft review;
* validation;
* and activation-preparation views.

It does not appear in ordinary accepted Event histories until the Event becomes active.

A proposed Event Participant cannot own an active Role.

An active Role continuously requires an active Event Participant.

Event activation does not require a Role.

## Allowed and Prohibited Transitions

The initial allowed transitions are:

| From | To | Meaning |
| --- | --- | --- |
| `proposed` | `active` | Reviewed and accepted |
| `proposed` | `invalidated` | Rejected without replacement |
| `proposed` | `superseded` | An active successor replaced the proposal |
| `active` | `invalidated` | Later rejected without replacement |
| `active` | `superseded` | An active successor replaced it |

Direct reviewed creation as active remains permitted.

The following ordinary transitions are prohibited:

```text
active → proposed

invalidated → proposed
invalidated → active
invalidated → superseded

superseded → proposed
superseded → active
superseded → invalidated
```

Invalidated and superseded Roles are terminal.

A mistaken terminal transition requires:

* an explicit append-only amendment;
* or a new Role record representing the corrected assertion.

It does not use reactivation.

Every transition requires append-only lifecycle history containing at least:

```text
role_id
from_status
to_status
reason
changed_at
changed_by
```

The exact transition-record schema remains a follow-up decision.

## Corrections and Supersession

### Proposed-State Correction

A proposed Role may be corrected in place during review when the correction does not change persisted participant identity.

Reviewable proposed values include:

* `role_type`;
* `basis`;
* `contextual` detail;
* and other nonidentity proposed values.

Once persisted:

```text
participant_id
```

is immutable.

A proposed Role attached to the wrong participant is invalidated or replaced by a new Role.

Uncommitted interface state may be corrected before canonical persistence.

### Active-State Correction

Changing any of the following on an active Role is material:

* participant;
* role type;
* substantive meaning;
* required contextual detail;
* removal or replacement of basis;
* or relationship to a supporting Account.

Material correction creates a successor Role.

### Structured Supersession

A successor Role may contain:

```json
{
  "supersedes": [
    {
      "role_id": "epr_prior",
      "reason": "role_type_corrected"
    }
  ]
}
```

The controlled reasons are:

```text
participant_corrected
role_type_corrected
basis_corrected
detail_corrected
duplicate_consolidated
role_relationship_corrected
other
```

`other` requires concise nonempty nested detail.

One successor may replace several prior Roles, including duplicate consolidation.

The array is unordered.

Every prior Role must belong to the same Event.

Self-reference, duplicate references, cycles, and inconsistent reasons are prohibited.

The prior Role remains active while the successor is proposed.

Supersession becomes effective exactly when the successor becomes active.

The coordinated operation must:

1. validate the successor;
2. validate every referenced prior Role;
3. validate parent state and compatibility;
4. activate the successor;
5. supersede every effectively replaced prior Role;
6. append lifecycle and correction history;
7. and commit atomically or through a recoverable staged-write process.

The durable system must not expose a completed state in which the successor is active while an effectively replaced prior Role remains active.

Canonical reverse:

```text
superseded_by
```

is not stored.

Reverse successor views are derived.

## Supporting Account Dependency

An Account referenced by a Role remains a separate canonical record with its own lifecycle.

Portia never silently retargets:

```text
account_ref
```

when an Account is corrected, superseded, or invalidated.

A proposed Role may correct its Account basis in place during review.

Replacing or removing an Account basis from an active Role is material.

When a corrected Account replaces the original:

```text
preserve prior Account
→ create or activate corrected Account
→ create successor Role referencing corrected Account
→ activate successor Role
→ supersede prior Role
→ complete Account transition
```

When an Account is invalidated without replacement, each dependent active `reported_involved` Role must be:

```text
invalidated
```

or replaced by a successor supported by another qualifying attributed Account.

An Account lifecycle operation must not leave an active `reported_involved` Role without a qualifying same-Event attributed Account.

Account and dependent-Role transitions must be atomic or recoverable.

Prior Accounts and Roles remain historically inspectable.

## Event Participant Dependency

Portia must resolve dependent Roles before an active Event Participant becomes invalidated or superseded.

### Participant Invalidation

Invalidating a participant without replacement requires coordinated invalidation of every dependent active Role.

The operation must not durably leave:

```text
participant = invalidated
Role = active
```

### Participant Supersession

When a participant is superseded, each dependent active Role is handled explicitly.

A relationship that should carry forward receives a successor Role referencing the replacement participant.

A relationship that should not carry forward is invalidated.

Existing Role records are never retargeted to another `participant_id`.

Participant and dependent-Role transitions must be atomic or recoverable.

A proposed Role referencing a participant that becomes invalidated or superseded cannot later activate unchanged.

## Event Lifecycle Effects

Role status is not cascade-rewritten merely because the Event changes lifecycle state.

### Closure

Closing an Event leaves child Role status unchanged.

Accepted Roles remain historical relationships within the closed Event.

A new Role must not activate beneath a closed Event until the Event is reopened.

### Reopening

Reopening does not reactivate, invalidate, or otherwise rewrite child Roles.

### Cancellation, Invalidation, or Supersession

Cancelling, invalidating, or superseding an Event excludes its Roles from ordinary current views.

Portia does not cascade every Role to another stored status.

The child records remain available in explicit audit, correction, provenance, and supersession views.

A replacement Event receives new Event Participant and Role records.

Roles are not moved or retargeted across Event roots.

## Derived Views

Ordinary current Role visibility requires:

```text
Role status = active
Event Participant status = active
Event status = active
```

Stored active status is therefore necessary but not sufficient for ordinary current visibility.

An active Role beneath a draft Event appears only in draft-review contexts.

A Role beneath a cancelled, invalidated, or superseded Event is not current even when its stored status remains active.

A Role referencing an invalidated or superseded participant is not current.

Terminal and noncurrent records remain available in explicit historical and audit views.

A role-free active participant remains visible.

The absence of a Role must not be presented as unknown involvement unless that meaning is represented explicitly elsewhere.

## Canonical Retention

After canonical persistence, a Role file is not hard-deleted through ordinary workflows.

This applies to:

```text
proposed
active
invalidated
superseded
```

Roles created in error use invalidation.

Replaced Roles use supersession.

Abandoned proposed Roles use invalidation.

The following are not canonical Role records and may be cleaned up:

* failed writes that never committed;
* temporary parsing artifacts;
* transaction staging files;
* and other explicitly noncanonical implementation debris.

Retention preserves:

* provenance;
* review history;
* correction lineage;
* participant dependency history;
* Account dependency history;
* and auditability.

## Paper-Assisted Workflow

Paper-assisted Role entry converges on the same canonical Role schema as digital entry.

Before scanning, printed role marks are capture affordances only.

They do not create:

* Role IDs;
* blank Role records;
* proposed Role records;
* or Role creation provenance.

After returned-page interpretation:

* a recognized mark may create a proposed Role;
* every paper-derived Role uses `paper_capture / ingested`;
* every paper-derived Role receives a matching paper basis;
* ambiguous marks remain unresolved review items;
* an unmarked role area creates no Role;
* and automated interpretation never activates the Role.

A paper-derived `reported_involved` Role may initially remain proposed with only its matching paper basis.

Before activation, Portia must create or select a same-Event attributed Account and add an `account_ref`.

The review workflow may prefill that Account from captured content so the teacher does not re-enter the same information.

The Account remains a separate canonical record.

Teacher-facing paper review should use concise actions such as:

```text
Confirm
Correct
Dismiss
```

The teacher does not manually manage:

* lifecycle terminology;
* opaque IDs;
* provenance objects;
* basis reference mechanics;
* supersession links;
* filesystem paths;
* route IDs;
* page-record IDs;
* timestamps;
* or transaction staging.

## Digital and Import Workflows

An explicit, unambiguous, reviewed digital Role may be created directly as active.

The `proposed` state ordinarily supports:

* paper interpretation;
* imports;
* automated suggestions;
* incomplete entry;
* and ambiguity.

An imported Role retains:

```text
creation_source.type = import
```

after digital review.

An imported `reported_involved` proposal may preserve an import-source basis while attributed Account review is incomplete.

Before activation, Portia creates or selects the same-Event attributed Account and links it through `account_ref`.

Role assignment remains optional during rapid Event capture.

## Teacher-Workflow Constraint

Portia’s internal lifecycle, provenance, dependency, and transaction model may be rigorous, but routine teacher interaction must remain:

* quick;
* comprehensible;
* proportionate;
* batchable where appropriate;
* keyboard-accessible;
* compatible with paper capture;
* free from duplicate data entry;
* and based on progressive disclosure.

Teachers should not ordinarily manage:

* technical lifecycle-state names;
* compatibility matrices;
* canonical relationship direction;
* immutable field rules;
* dependency graphs;
* amendment records;
* filesystem paths;
* or rollback mechanics.

Portia derives the necessary canonical operations from plain-language teacher actions.

For example:

```text
Wrong participant—change this Role to Jordan Lee.
```

may internally:

1. create a replacement Role;
2. validate the active replacement participant;
3. preserve or rebuild valid basis;
4. activate the successor;
5. supersede or invalidate the prior Role;
6. append lifecycle and correction history;
7. and refresh derived views.

The teacher experiences one correction action.

A field or workflow step that creates burden without a clear documentation, support, correction, privacy, or decision benefit should be omitted or deferred.

## Validation Boundary

The Role schema uses JSON Schema Draft 2020-12.

JSON Schema enforces local record structure, including:

* required fields;
* constants;
* enums;
* identifier syntax;
* structured creation-source variants;
* structured attribution-agent variants;
* structured basis variants;
* top-level detail restrictions;
* conditional contextual detail;
* conditional paper basis;
* conditional Account basis for active and superseded `reported_involved`;
* structured supersession references;
* controlled supersession reasons;
* nonempty `other` explanation;
* timezone-aware timestamp syntax;
* unique array entries;
* and rejection of unknown or misplaced properties.

Application validation enforces conditions requiring paths, external records, lifecycle history, or several canonical files, including:

* canonical path agreement;
* Event existence;
* Event Participant existence;
* active participant state before Role activation;
* Event status of `draft` or `active` before Role activation;
* same-Event Account and Observation scope;
* Account attribution;
* exact paper creation-source and basis route/page equality;
* role-type compatibility;
* duplicate active role detection;
* intended post-operation active-set validation;
* persisted participant immutability;
* timestamp chronology;
* lifecycle-transition legality;
* lifecycle-history existence;
* supersession existence and same-Event scope;
* self-reference, duplicate reference, and cycle prevention;
* successor activation and prior supersession coordination;
* supporting Account dependency resolution;
* Event Participant dependency resolution;
* Event lifecycle visibility effects;
* canonical no-hard-delete enforcement;
* creation-source immutability;
* and atomic or recoverable multi-record writes.

The schema does not embed Event, Event Participant, Account, Observation, or lifecycle-transition records.

## Consequences

### Positive Consequences

* Participant identity remains valid independently from optional Role assertions.
* One participant may hold several compatible neutral relationships without an embedded role list.
* Role correction does not rewrite participant identity.
* Direct involvement remains distinct from reported involvement.
* Every active reported relationship identifies a canonical attributed Account.
* Paper and import proposals can preserve uncertainty until attribution is reviewed.
* Paper artifacts remain linked both as creation provenance and assertion support.
* Role creation source remains historically accurate after confirmation.
* Contextual explanation has a narrow, controlled location.
* Judgmental labels do not become durable generic identity-adjacent fields.
* Workflow-specific source and recipient relationships remain in their proper records.
* Corrections preserve prior Roles, Accounts, participants, and provenance.
* Supersession becomes effective only when the successor becomes active.
* Compatibility is evaluated against the intended post-operation state.
* Active Roles cannot point to inactive participants.
* Event draft assembly can complete before Event activation.
* Event closure does not require rewriting accepted child relationships.
* Canonical records remain auditable and recoverable.
* Paper, digital, and import workflows converge on one schema.
* JSON Schema and application validation have an explicit boundary.
* Teacher interaction can remain simple despite rigorous internal operations.
* No blocking `pds-core` change is required.

### Costs and Tradeoffs

* Role storage creates additional canonical child files.
* Compatibility requires cross-record application validation.
* Active `reported_involved` requires an Account record, even when the source began as paper or import data.
* Paper-derived Roles intentionally repeat route and page references in creation source and basis.
* Replacement-based correction creates more records than unrestricted mutation.
* Active Role basis correction may require successor creation.
* Account correction may require coordinated successor Roles.
* Participant correction may require coordinated replacement of dependent Roles.
* Current visibility requires evaluation of Event, participant, and Role state.
* Terminal-state preservation requires explicit audit and correction views.
* Reverse supersession views require derived indexing.
* Atomic or recoverable multi-record operations require transaction and recovery design.
* Lifecycle history requires additional append-only records.
* Teacher-local attribution remains weaker than authenticated institutional audit.
* Future institutional or multi-user deployment will require broader authorization, audit, and records-governance architecture.

## Alternatives Considered

### Alternative A: Embed Roles in Event Participant Records

Under this alternative, an Event Participant contains one role or a role array.

Rejected.

Roles require independent lifecycle, provenance, basis, correction, compatibility, and supersession. Identity must remain valid with no Role.

### Alternative B: Store One Aggregate Role Record per Participant

Under this alternative, one Role record contains several role types.

Rejected.

Changing one role would rewrite the lifecycle and provenance of unrelated role assertions. Independent correction and supersession would become ambiguous.

### Alternative C: Require Exactly One Role

Under this alternative, every participant has one mandatory Role.

Rejected.

Role assignment is optional, and `present` may legitimately coexist with one other initial Role type.

### Alternative D: Allow Every Role Combination

Under this alternative, any distinct active role types may coexist.

Rejected.

`directly_involved`, `reported_involved`, and `contextual` are competing primary descriptions under the initial vocabulary. Allowing all combinations would create ambiguous current state.

### Alternative E: Use Judgmental Role Vocabulary

Under this alternative, the generic Role list includes labels such as offender, victim, aggressor, responsible, guilty, or credible.

Rejected.

Those labels imply findings, credibility judgments, policy conclusions, or durable stigma that the generic Event-level relationship does not establish.

### Alternative F: Include Workflow Relationships as Generic Roles

Under this alternative, reporter, observer, response recipient, support provider, and decision maker become Event Participant Roles.

Rejected.

Those relationships belong to Accounts, Observations, Responses, Supports, Follow-Ups, and Determinations.

### Alternative G: Treat Creation Source as Assertion Basis

Under this alternative, digital entry, paper capture, or import provenance automatically explains what supports the Role.

Rejected.

How a record entered Portia and what supports its assertion are distinct relationships.

### Alternative H: Add a `teacher_entry` Basis

Under this alternative, every direct teacher assignment includes a generic `teacher_entry` basis.

Rejected.

Teacher action is already preserved through creation source, operator attribution, and lifecycle history. A generic entry marker is not a separate evidentiary source.

### Alternative I: Inherit Role Source From the Event or Participant

Under this alternative, the Role source is copied or inferred from its parent.

Rejected.

Events, participants, and Roles may enter Portia through different workflows at different times.

### Alternative J: Permit Preallocated Paper Roles

Under this alternative, blank Role records are created before page rendering.

Rejected.

No Role assertion exists until a returned artifact produces a specific interpreted or reviewed participant-role relationship.

### Alternative K: Let Paper Basis Alone Activate `reported_involved`

Under this alternative, a paper checkbox or mark is sufficient for active reported involvement.

Rejected.

The artifact identifies the capture source but does not structurally preserve who supplied the report and what was attributed.

### Alternative L: Require Accounts Only for Paper-Derived Reported Roles

Under this alternative, digital or imported active `reported_involved` Roles may use weaker attribution structures.

Rejected.

One active role type should have one attribution guarantee regardless of creation path.

### Alternative M: Store Contextual Detail on Every Role Type

Under this alternative, every Role may carry unrestricted top-level explanation.

Rejected.

This would duplicate Accounts, Observations, and Event summaries and invite unsupported narrative labels.

### Alternative N: Silently Retarget Account References

Under this alternative, correcting an Account automatically rewrites every dependent Role to reference the replacement.

Rejected.

The prior Role must continue to identify the Account that actually supported it during its accepted period.

### Alternative O: Retarget Roles When a Participant Is Corrected

Under this alternative, existing Role files change `participant_id`.

Rejected.

This would rewrite the subject of the original assertion and erase correction lineage.

### Alternative P: Keep Active Roles Beneath Inactive Participants

Under this alternative, participant invalidation merely hides dependent active Roles in views.

Rejected.

An active Role must not point to a participant relationship that is no longer valid.

### Alternative Q: Cascade Event Lifecycle Changes Into Every Role

Under this alternative, closing, cancelling, invalidating, or superseding an Event rewrites all child Role statuses.

Rejected.

Role status represents the Role assertion’s own lifecycle. Event state governs effective visibility without rewriting every child record.

### Alternative R: Permit Reactivation of Terminal Roles

Under this alternative, invalidated or superseded Roles may return to active.

Rejected.

Terminal records preserve accepted correction history. A corrected assertion receives a new Role or an explicit append-only amendment.

### Alternative S: Hard-Delete Proposed or Invalidated Roles

Under this alternative, erroneous or abandoned Role files are removed.

Rejected.

Canonical persistence creates provenance and review history that must remain auditable.

### Alternative T: Warning-Only Compatibility Conflicts

Under this alternative, Portia warns about incompatible active Roles but permits the teacher to save them.

Rejected.

The initial vocabulary has a defined semantic contract. Conflicting active primary descriptions create unreliable current state.

## Implementation Constraints

Portia implementations must preserve these invariants:

1. One Role represents one participant and one role type within one Event.
2. Roles are separate canonical child records.
3. A Role never embeds Event or participant identity records.
4. Role assignment is optional.
5. Event activation does not require a Role.
6. The initial types are `directly_involved`, `present`, `reported_involved`, and `contextual`.
7. Generic Roles do not establish blame, fault, guilt, credibility, severity, or formal determination.
8. Workflow-specific relationships remain in their owning record types.
9. One participant may hold only compatible active Role types.
10. Duplicate active Role type assignments are prohibited.
11. Compatibility is evaluated against the intended post-operation active set.
12. Every Role records its own creation source.
13. Role source is independent from Event, participant, basis, and prior Role source.
14. Role creation source is ordinarily immutable.
15. Every paper-derived Role uses `paper_capture / ingested`.
16. Roles never use `paper_capture / preallocated`.
17. Blank printed role marks do not create canonical Roles.
18. Every paper-derived Role retains a matching paper basis.
19. Matching paper route and page references are equal across creation source and basis.
20. `basis` is unordered and does not imply credibility or weight.
21. No `teacher_entry` basis kind exists.
22. Account and Observation references resolve only within the owning Event.
23. Cross-Event Account and Observation basis references are prohibited.
24. Proposed `reported_involved` requires source-oriented basis.
25. Every active `reported_involved` requires a same-Event attributed Account reference.
26. Paper and import basis do not replace the activation-required Account.
27. Top-level detail is permitted only for `contextual`.
28. Active and superseded `contextual` Roles retain valid detail.
29. Persisted `participant_id` is immutable.
30. Direct reviewed creation as active is permitted.
31. Role activation requires an active Event Participant.
32. Role activation requires Event status `draft` or `active`.
33. Ordinary current visibility requires active Role, participant, and Event.
34. Invalidated and superseded Roles are terminal under ordinary workflows.
35. Active Roles do not return to proposed.
36. Every lifecycle transition preserves append-only history.
37. Structured forward `supersedes` references belong to the successor.
38. Reverse successor views are derived.
39. Prior Roles remain unchanged while a successor is proposed.
40. Effective supersession occurs only when the successor activates.
41. Successor and prior transitions are atomic or recoverable.
42. Active basis removal or replacement requires successor correction.
43. Account correction never silently retargets active Role references.
44. Account lifecycle operations never leave active reported Roles without qualifying Accounts.
45. Participant invalidation resolves dependent active Roles.
46. Participant supersession creates successor Roles or invalidates relationships that do not carry forward.
47. Existing Roles are never retargeted to replacement participants.
48. Event closure and reopening do not rewrite child Role status.
49. Event cancellation, invalidation, or supersession changes effective visibility without cascade rewriting.
50. Roles are never moved between Event roots.
51. Canonical Role files are not hard-deleted through ordinary workflows.
52. JSON Schema enforces local shape.
53. Application validation enforces cross-record and lifecycle invariants.
54. Unknown and misplaced properties are rejected.
55. Technical provenance and dependency operations are workflow-generated.
56. Routine teacher interaction remains concise and proportionate.

## Follow-Up Decisions

Separate ADRs, schemas, or specifications should define:

* Event and Event Participant lifecycle-transition schemas;
* Event Participant Role lifecycle-transition schema;
* general append-only amendment records;
* Account schema, attribution model, and lifecycle;
* Observation schema and observer attribution;
* common cross-record dependency-resolution patterns;
* staged-write, rollback, and recovery behavior;
* transaction journals or equivalent recoverable commit mechanics;
* duplicate-detection and consolidation workflow;
* privacy projections for multi-student Events;
* redacted participant-specific exports;
* Actor Directory schema and lifecycle;
* typed external-module references;
* Support Process schema;
* Classification, Hypothesis, and Determination schemas;
* Response, Support, Communication, Follow-Up, and Outcome schemas;
* owning-class migration when Event storage ownership is incorrect;
* PDS2 page-record and route schemas;
* possible capture-batch routing for multi-entry paper sheets;
* retention and archival integration with Sunset;
* authenticated multi-user provenance for future institutional deployment;
* and performance targets for classroom capture and batch review.

## Notes

This decision defines a neutral Event-level relationship model.

It does not define:

* what factually occurred;
* who should be believed;
* whether a rule was violated;
* who was responsible;
* what institutional finding was made;
* what response was appropriate;
* or what support should follow.

Those concepts remain in separate Portia records.

The Role model is intentionally more rigorous than the routine interface.

That rigor exists to preserve:

* uncertainty;
* attribution;
* correction;
* provenance;
* participant identity;
* and historical meaning.

It must not become an excuse to require teachers to perform technical records administration during instruction.
