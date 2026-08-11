# Issue #17 Pre-ADR Repository Checkpoint

**Issue:** `#17 — Define Response and Communication domain models`
**Date:** 2026-08-09
**Branch:** `17-response-communication-domain-models`
**Checkpoint:** immediately before accepting ADR 0013

## Verified branch state

Remote Slice 1 commit:

```text
2a0eff3557ac8f2466a20c27e45da940f806c3fb
docs: begin response communication design
```

Current comparison:

```text
base: main
head: 17-response-communication-domain-models
status: ahead
ahead_by: 1
behind_by: 0
merge_base:
34d8100a1775effc43737409f86ad0486c01fb34
```

Portia `main` therefore remains unchanged from the Issue #17 initial
checkpoint.

## Core state

Current `pds-core/main` remains:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

No Core drift requires a Response/Communication contract change.

## ADR number

The expected path:

```text
docs/decisions/0013-define-response-and-communication-domain-models.md
```

does not exist on the branch before this slice.

ADR number `0013` is therefore available.

## Contract checks performed

### ADR 0012

ADR 0012 remains the active authority for the judgment layer.

It explicitly keeps:

```text
Determination != Response
Determination != consequence
```

and defers production Response/Communication to Issue #17.

No conflict was found.

### ADR 0001

ADR 0001 remains the research-era conceptual precursor.

Its important surviving constraint is:

```text
Response
Support
Outcome
```

must remain separately queryable rather than collapsing consequence/action into
the meaning of what occurred.

ADR 0013 preserves that boundary.

### ADR 0002

ADR 0002 assigns Immediate Responses and family communication to Portia.

Its older bullet list treated `family contact` as one possible Immediate
Response.

ADR 0013 refines that shorthand:

```text
Communication
= canonical communication act

Response
= separate Event-local action only when the contact act is deliberately tracked
  as an immediate Response
```

This is documentation reconciliation, not a contradiction in module ownership.

### Work Relationship

`work_relationship@2` remains intentionally limited to:

```text
draws_context_from
```

between exact Portia work roots.

It is not suitable as a generic record-to-record Communication relation.

ADR 0013 therefore uses exact work-record references inside Communication for
typed related-record semantics and leaves Work Relationship unchanged.

### Portia work identity

Existing exact Portia work references already recognize:

```text
event
support_process
```

and `portia_support_process_id@1` already defines `sup_` identity.

Communication can therefore be Portia-work-local in v1 without fabricating the
Support Process domain model.

Current-use eligibility still requires the owning work to resolve; until #18
publishes `support_process@1`, active current-use Communication is effectively
Event-backed.

### Actor Contact Point

`actor_contact_point@1` explicitly defines:

```text
preferred != consent
locally_confirmed != delivery
locally_confirmed != institutional verification
locally_confirmed != exclusive control
```

ADR 0013 preserves those semantics.

Exact Actor Contact Point references may record the historical endpoint used,
but they do not establish delivery or authorization.

### Source Artifact Reference

`source_artifact_ref@1` is explicitly a closed reference family for material
associated with Account or Observation.

Communication attachment reuse would broaden its published semantic scope.

ADR 0013 therefore keeps Communication attachment branches local to
`communication@1` and does not modify `source_artifact_ref@1`.

### Amendment

`amendment@1` is generic but application validation must approve
record-family-specific nonmaterial paths.

No clearly safe v1 Response or Communication field was identified.

ADR 0013 therefore permits no Amendment paths for either family.

## Sibling-module implications

No reviewed sibling public contract requires modification.

Portia may reference sibling module records through existing module-qualified
references while the originating module remains authoritative.

No ScoreForm, Quillan, Concord, Meridian, Vitrine, or other sibling change is
required by ADR 0013.

## Drift classification

```text
pds-portia main:
no drift

pds-core main:
no drift

ADR numbering:
0013 available

published Portia shared contracts:
reuse sufficient; no version bump identified

ADR 0002 family-contact wording:
documentation reconciliation required

sibling modules:
no required contract change

Support Process:
future semantic implementation remains #18; shared identity already anticipates it
```

## Decision

No pre-ADR repository drift or contract contradiction blocks the Issue #17
architecture.

ADR 0013 may be accepted with:

```text
Response:
Event-local
rsp_ identity
portia_target_ref@1
represented-human provider
typed action family
explicit consequence context
exact Review/Determination context
execution state separate from Outcome
no v1 Amendment paths

Communication:
Portia-work-local
comm_ identity
human sender/recipients
exact Actor Contact Point when applicable
closed method/purpose/act-state vocabularies
summary-oriented content
schema-local attachments
typed exact record relations
required privacy scope
no v1 Amendment paths
```
