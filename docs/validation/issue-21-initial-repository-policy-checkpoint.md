# Issue #21 Initial Repository and Policy Checkpoint

**Status:** Initial remote checkpoint complete; local baseline pending exact branch run
**Issue:** `#21 — Define privacy projections, redaction, export, retention, and Sunset boundaries`
**Date:** 2026-08-14

## Exact starting anchors

```text
pds-portia/main
2ec841ffdf9c20850cbaef5811ca20720dc5954b

pds-portia/21-privacy-projections-redaction-export-retention-sunset-boundaries
2ec841ffdf9c20850cbaef5811ca20720dc5954b

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-quillan/main
3ae37eaaf89cf913020a5afc75bc11a68df0d5cc

pds-scoreform/main
047e47f60730b8a5540b5e1d92f008ffad37eede

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c

pds-vitrine/main
16317d8764a2e79018aa2bc7082faf66759c13b6

pds-concord/main
e6db668f0f8729b058f34cdda86a4cb443ca068d
```

No `pds-sunset` repository/package exists at this checkpoint.

## Portia branch point

Remote `main` and the Issue #21 feature branch both resolve to:

```text
2ec841ffdf9c20850cbaef5811ca20720dc5954b
20 paper assisted capture PDS2 routing import contracts (#33)
```

The branch is an exact remote branch point from reconciled Portia main.

## Test baseline context

The final observed Issue #20 schema-validation run was:

```text
1020 tests
OK
```

Issue #21 must still record an authoritative run on the exact local checkout.

Slice 1 adds documentation only, so no test-count change is expected. Run:

```powershell
python -m unittest discover -s tests/schema_validation
git diff --check
git status --short
```

The actual local output is authoritative.

## ADR availability

Current Portia main includes accepted ADR 0016.

This path does not exist on current main:

```text
docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md
```

ADR 0017 is therefore available at this checkpoint. Recheck immediately before
acceptance.

## Downstream milestone boundary

Issue #22 requires combined synthetic graphs including a privacy-redacted
participant projection and rebuildable derived views.

Issue #23 will audit privacy/redaction feasibility, retention boundaries, and
teacher-local authority limits.

Issue #21 must therefore finish with explicit enough semantics for those issues
to validate rather than redesign.

## Existing Portia boundary

Current Portia already establishes:

- teacher-local scope and no authoritative student dossier;
- append-preserving correction/supersession;
- Statement of Disagreement;
- Exceptional Removal;
- Operation Journal/Lock recovery;
- Quarantine and Integrity Finding;
- derived Source Snapshot / derived-index metadata;
- Actor/Contact Point privacy boundaries;
- Account/Observation source semantics;
- Communication `privacy_scope`;
- Support/Follow-Up/Outcome/Reentry/Repair semantics;
- paper/import provenance without raw-payload duplication.

Issue #21 must compose these meanings rather than add a generic
`private: true|false` switch.

## Existing derived-source compatibility finding

`source_snapshot@1` describes exact source representations for one derived
projection generation, but its `projection_kind` enum is closed to Issue #13.

`derived_index_metadata@1` uses the same closed vocabulary and specifically
describes derived index generations.

Issue #21 participant/student/family/export projection kinds are not valid v1
values. The published v1 schemas must not be silently widened.

## Initial architecture conclusion

```text
Portia:
    canonical domain meaning
    privacy projection floor
    source/field sensitivity semantics
    module-owned custody classification
    exact source/correction lineage
    module-local safe disposition capabilities

application/deployment/institution:
    requester identity
    authorization
    legal/policy basis
    retention schedule
    hold decision
    disclosure entitlement
    destruction authorization

future Sunset:
    cross-module planning/orchestration
    module capability discovery
    dry-run disposition plans
    safe ordering
    recovery
    bounded result verification

Core:
    shared workspace/class/roster identity
    PDS2 retained-source ownership
    shared routing/publication infrastructure
    possible future suite capability registry
    not institutional retention-policy authority
```

No public schema is added by Slice 1.

## Drift policy

Before ADR acceptance:

1. reverify all listed repository anchors;
2. compare the feature branch with current Portia main;
3. rerun the authoritative local schema-validation suite;
4. recheck ADR 0017 availability;
5. reconcile material Portia/Core/sibling privacy/export/custody drift;
6. recheck policy guidance where a changed rule would materially affect design.

Repeat the same audit before final Issue #21 acceptance.
