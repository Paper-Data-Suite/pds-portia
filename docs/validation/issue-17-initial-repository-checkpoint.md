# Issue #17 Initial Repository Checkpoint

**Issue:** `#17 — Define Response and Communication domain models`
**Date:** 2026-08-09
**Branch:** `17-response-communication-domain-models`
**Checkpoint:** initial repository and dependency review

## Portia branch baseline

GitHub comparison at the start of Issue #17:

```text
base: main
head: 17-response-communication-domain-models
status: identical
ahead_by: 0
behind_by: 0
```

Both resolve to:

```text
34d8100a1775effc43737409f86ad0486c01fb34
16 review classification hypothesis determination domain models (#29)
```

Issue #17 therefore starts from the fully merged Issue #16 architecture.

## Core baseline

Current reviewed Core main:

```text
6c507213618b68a6dd3ea096e1a898201ff029e6
Document Core integration contract and prepare v0.6.0 (#176)
```

Core remains authoritative for workspace/class/roster identity,
module-qualified work identity, PDS2 routing, retained-source provenance, and
safe shared infrastructure.

No Core change is required by the initial Issue #17 design.

## Relevant Portia contracts reviewed

The initial review covered the current semantics of:

```text
represented_human_attribution@1
actor_contact_point@1
exact_actor_contact_point_ref@1
exact_portia_work_ref@1
portia_target_ref@1
support_process_target_ref@1
portia_local_work_target@1
work_relationship@2
determination@1
amendment@1
source_artifact_ref@1
creation_source@1
```

and the merged Issue #16 design/ADR boundary.

## Initial findings

### Response

Existing `portia_target_ref@1` is sufficient for Event, one Event Participant,
or explicit Event Participant-set Response targeting.

`represented_human_attribution@1` is sufficient for provider identity while
preserving the existing rule that represented-human identity does not establish
authority.

Determination already explicitly excludes Response/consequence from decision
semantics. Issue #17 can therefore link institutional consequence implementation
to an exact Determination without adding Response fields to Determination.

### Communication ownership

Existing exact Portia work identity already supports:

```text
event
support_process
```

and `portia_support_process_id@1` is already published.

Communication can therefore be designed as Portia-work-local without requiring
an immediate v2 contract when #18 publishes Support Process.

Current active use remains constrained by owner resolution: until
`support_process@1` exists, an active current-use Communication can be backed by
an Event only.

### Work Relationship

`work_relationship@2` is intentionally narrow:

```text
relationship_type = draws_context_from
```

between exact Portia work roots.

It should not be broadened into a generic record-to-record relationship
mechanism for Communication.

Communication should own typed exact record relations using existing exact
work-record references.

### Actor Contact Point

Actor Contact Point already states that:

```text
preferred != communication consent
verification != delivery assurance
verification != institutional verification
```

Communication must preserve those semantics and may retain an exact historical
Contact Point when appropriate.

### Amendment

The generic Amendment contract permits only record-family-approved nonmaterial
paths.

Initial Issue #17 design finds no clearly safe Response or Communication v1
field that should be edited in place after activation.

Pre-ADR recommendation is therefore no v1 Amendment paths for either family.

### Attachments

`source_artifact_ref@1` is explicitly described as material associated with an
Account or Observation.

Using it directly for Communication would broaden a published contract's
semantic meaning.

Initial recommendation is to keep Communication attachment variants local to
`communication@1` rather than creating or broadening a public shared artifact
contract prematurely.

### Paper/import

`creation_source@1` supports digital entry, paper capture, and import.

Response/Communication must prohibit preallocated paper capture from fabricating
an action. Ingested paper/import material may preserve only proposed
representations pending future #20 review rules.

## Initial drift classification

```text
pds-portia main:
no drift; Issue #17 branch starts identical

pds-core main:
no change requiring adaptation

shared Portia contracts:
reusable; no version bump identified

sibling modules:
no required public-contract change identified

future Support Process:
anticipated by existing shared work identity; semantics remain #18
```

## Next checkpoint

Before accepting ADR 0013:

1. re-fetch current Portia main;
2. re-fetch current Core main;
3. compare the Issue #17 branch to Portia main;
4. classify any drift as:
   - required contract change;
   - documentation reconciliation;
   - future concern; or
   - no implication.

No schemas should be created until the ADR decisions have been reconciled
against that pre-ADR checkpoint.
