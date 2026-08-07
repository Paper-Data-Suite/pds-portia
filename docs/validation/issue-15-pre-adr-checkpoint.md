# Issue #15 Pre-ADR Checkpoint and ADR 0011 Acceptance

**Issue:** `#15 — Define Account and Observation domain models`
**Date:** 2026-08-07
**Branch:** `15-account-observation-domain-models`
**Checkpoint type:** Pre-ADR drift review and decision freeze

## Branch state

The initial design checkpoint was committed as:

```text
ce6a7eeca18cde3abf7154896838f519c9b2a43c
docs: establish account observation design checkpoint
```

At this checkpoint the Issue #15 branch is one commit ahead of `main` and zero
behind.

The merge base remains:

```text
pds-portia/main
ed09e6779281a23be05124afdb266579d2d560de
```

## Core drift check

Current Core remains:

```text
pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6
```

No Core public-contract drift affects Issue #15.

Classification:

```text
Core workspace/class/roster identity: unchanged governing boundary
Core PDS2 routing/provenance: unchanged governing boundary
Portia source/observation semantics: Portia-owned
Core change required: no
```

## Portia drift check

`main` has not advanced since the Issue #15 branch was created.

No new Portia public contract conflicts with the Account/Observation design.

Published Event Participant Role v3 remains the relevant consuming contract and
continues to require `account_ref` for active/superseded `reported_involved`.

## Frozen decisions

The seven open questions from Slice 1 are resolved:

```text
1. represented_human_attribution@1
2. source_artifact_ref@1
3. evidence_time@1
4. nested Observation measurements
5. nested Account relations
6. no Account/Observation v1 Amendment paths
7. bounded lifecycle reason vocabularies
```

Additional accepted integration decisions:

```text
active reported_involved Account target must identify the same Participant
    or a Participant set containing that Participant

Event-wide Account does not qualify for participant-specific reported_involved

Account retraction requires a same-source retraction Account plus coordinated
    predecessor lifecycle transition

paper/import evidence begins proposed and requires local review

Observation has no canonical valence/severity/finding field

Account and Observation do not automatically create findings
```

## Shared-contract decision

New shared primitives are limited to concepts with at least two immediate
consumers:

```text
represented_human_attribution@1
    -> Account.source
    -> human Observation.observer

evidence_time@1
    -> Account.provided_time
    -> Observation.observation_time

source_artifact_ref@1
    -> Account.source_artifacts
    -> Observation.source_artifacts
```

The following remain nested because they have one immediate semantic owner:

```text
Observation measurement
Account-to-Account relation
```

This avoids premature suite-wide abstraction.

## Amendment review

Existing `amendment@1` can structurally target generic local records but its
application contract requires the target family to declare amendable paths.

Account and Observation v1 intentionally declare none.

This is compatible with the shared Amendment architecture: application
validation rejects Account/Observation Amendments rather than creating a new
history family.

## ADR result

ADR 0011 is accepted.

The design is now sufficiently frozen to begin public schema publication.

Expected first schema slice:

```text
portia_account_id@1
portia_observation_id@1
represented_human_attribution@1
evidence_time@1
source_artifact_ref@1
```

Account and Observation root schemas should follow only after those primitives
validate cleanly.

## Remaining checkpoints

Immediately before Issue #15 closes:

1. re-check `pds-portia/main`;
2. re-check `pds-core/main`;
3. inspect any sibling public contract that newly affects source attribution,
   observer identity, provenance, attachments, or consuming eligibility;
4. classify drift;
5. reconcile final documentation and validation evidence.
