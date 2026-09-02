# Response and Communication Workflows

**Issue:** #43 — Implement Response and Communication workflows  
**Milestone:** Portia v0.2.0  
**Contracts:** `response@1`, `communication@1`

Issue #43 supplies the production application layer for the Response and
Communication contracts accepted by ADR 0013 and Issue #17. It does not change
those published wire contracts.

## Semantic boundary

A Response records one bounded action taken, attempted, initiated, or completed
in direct Event context. A Response is not evidence, a Determination, ongoing
Support, or an Outcome. Its execution state does not establish effectiveness,
appropriateness, fault, or resolution.

A Communication records one bounded human communication act or attempt. A
Communication is not an Account, Response, Determination, mutable message
thread, proof of delivery, proof of reading, proof of understanding, proof of
participation, or proof of legal notice.

These distinctions are operational requirements, not documentation caveats.

```text
Response != evidence
Communication != mutable message thread
```
The workflow services fail closed rather than infer authority or facts that the
canonical records do not establish.

## Public API

`portia.workflows` exports:

```text
ResponseWorkflowService
CommunicationWorkflowService
response_reference(...)
communication_reference(...)
ModuleCommunicationAttachmentAuthority
CommunicationAttachmentResolution
```

Both workflow services expose the established Portia application shape:

```text
create(...)
load_exact(...)
resolve_exact(...)
list(...)
require_current_use(...)
resolve_current(...)
transition_lifecycle(...)
correct(...)
```

with `list_responses(...)` and `list_communications(...)` aliases where useful.
Response and Communication v1 intentionally expose no Amendment operation.
Material correction uses successor/history semantics.

## Response ownership and targets

Response v1 is Event-local. New writes require an exact `event@2` owner, and
the selected Event, class, work ID, Response identity, and canonical path must
agree.

Response target uses the accepted `portia_target_ref@1` branches:

```text
event
event_participant
event_participants
```

Participant targets are resolved exactly. Current use requires current target
eligibility and applies Quarantine to the exact Event and Participant
representations. Duplicate logical Participant identities are rejected.

Provider attribution is represented-human attribution and remains distinct from
`created_by` / `updated_by`. Name similarity, recorder identity, Actor category,
or display text never substitutes for exact person authority.

## Response action and decision context

The frozen action families remain:

```text
classroom_management
environmental_or_instructional
support_access
de_escalation
safety_or_protective
referral_or_handoff
restorative_or_repair
consequence
other
```

A teacher-local consequence may exist without a Determination. A
`recorded_institutional` consequence requires an exact same-Event
`determination@1`, resolved through `DeterminationWorkflowService`. The link
records context only; it does not prove that the Determination was correct,
legally sufficient, proportionate, or effective.

Optional Review and Determination references remain exact historical context.
They never silently follow a later successor.

Immediate bounded Event-local action is Response. Planned, recurring,
scheduled, longitudinal, goal-directed, or implementation-tracked activity
belongs to Support / Intervention under Issue #44. A completed referral or
handoff Response does not prove downstream service delivery.

## Communication Event ownership and Support Process boundary

Communication v1 is Portia-work-local and its wire contract recognizes both
`event` and `support_process` ownership. Issue #43 implements the Communication
family and Event-owned authority.

Issue #44 now supplies the production `support_process@1` owner authority that
Issue #43 intentionally deferred. Support Process Communication creation,
current use, lifecycle, and correction delegate to that authoritative workflow
surface without changing `communication@1` or introducing `communication@2`.
Issue #43 still does not itself implement Support planning; it consumes the
owner authority supplied by Issue #44.

## Sender, recipients, and Contact Points

Sender and recipient people use represented-human authority. Sender is distinct
from recorder. A recipient is not automatically an Event Participant, guardian,
educational decision-maker, consent source, disclosure authorization, or
entitlement to Portia content.

Recipient `participation` is explicit. In particular:

```text
completed Communication != recipient participation
recipient_unavailable != delivery
listed recipient != read or understanding
```

Actor recipients may reference an exact Actor Contact Point. Endpoint ownership
must match the exact recipient Actor before Contact Point I/O. Active current
use requires current Actor and Contact Point authority plus Quarantine. Proposed
historical records may pin an exact historical Contact Point.

Contact Point preference or local confirmation is not consent, delivery proof,
exclusive control, or institutional verification.

## Exact Communication relations

Communication relations resolve exact Portia work-record references and never
follow successors silently. Typed relations enforce their target family:

```text
responds_to                 -> Communication
conveys_determination       -> Determination
documents_handoff_for       -> Response
relates_to_response         -> Response
account_from_communication  -> Account
```

`responds_to` is same-work and cannot target the Communication itself. Broader
relation verbs preserve exact context without inventing a universal semantic
taxonomy. A relation never changes the semantic authority of its target.

## Attachments

Communication v1 supports:

```text
workspace_file
portia_record
module_record
external_record
```

Binary payloads are never embedded in Communication JSON.

Workspace files are rechecked for workspace containment, byte length, and
fingerprint. Exact Portia attachments remain historical and do not follow
successors. Sibling-module records resolve only through an explicit public
`ModuleCommunicationAttachmentAuthority`; Portia does not import private
sibling internals or guess their storage. External records remain inert
metadata unless a future explicit authority is supplied.

Attachments establish linkage only. They do not import foreign authority or
turn Communication into evidence.

## Current-use qualification

Exact historical reads stay exact. `require_current_use()` is stronger and
requires the applicable combination of:

```text
canonical exact representation
active lifecycle reconciliation
digital-entry materialization provenance
current Event authority
current provider / sender / recipient authority
current Actor Contact Point authority
exact target / relation / attachment resolution
Quarantine on owning and referenced authority
family-specific Response / Communication rules
```

A superseded historical dependency may remain a valid exact historical context
when the contract permits it; the active Response or Communication itself must
be the current canonical representation.

## Lifecycle and correction

Ordinary lifecycle transitions preserve the exact record identity. Material
correction creates a successor and coordinates persistence of successor history
with predecessor supersession through the shared operation-journal / recovery
boundary.

Supersession topology rejects self-supersession (except the accepted contract
migration exception), duplicate predecessor identities, mixed reasons, invalid
ordinary cross-work correction, invalid work-root correction, invalid duplicate
consolidation cardinality, forks, cycles, disconnected history, and lifecycle
status disagreement.

Exact predecessor reads remain pinned. Current resolution does not rewrite or
hide history, and exact historical references never silently follow successors.

A later communication attempt is not a correction merely because it occurs
later. A failed attempt followed by a successful attempt remains two separate
canonical Communications unless a genuine material-recording correction is
explicitly performed.

## Accepted runtime parity

Issue #43 locks production behavior to two existing acceptance sources:

1. Issue #17 frozen Response/Communication fixtures and application-invalid
   matrices. The workflow parity guard accounts for all 76 runtime scenarios:
   29 Response and 47 Communication scenarios.
2. Issue #22 scenario P22-07, “Immediate Response and family Communication.”
   The production acceptance test persists Actor, Contact Point,
   Actor-to-Student Relationship, Event, Participant, Response, and
   Communication through their real services, then proves that Review,
   Classification, Hypothesis, Determination, Support, Intervention, and Outcome
   are not fabricated.

Structural-invalid Issue #17 fixtures remain model/schema validation concerns;
workflow services consume already-valid runtime models.

## Deferred scope

Issue #43 does not implement:

```text
Support Process planning
Support / Intervention workflows
transport or messaging delivery
consent / authorization inference
legal-notice determination
automatic discipline selection
risk / engagement / remorse inference
Response or Communication Amendment v1
```

Issue #44 owns Support Process and ongoing Support/Intervention production
workflows. Later package and installed-wheel qualification must preserve this
Issue #43 surface without widening these boundaries.
