# Issue #21 Future Sunset / Retention Adapter Scenario Matrix

**Status:** Slice 6 architecture scenarios
**Date:** 2026-08-14

| ID | Scenario | Required result |
| --- | --- | --- |
| `S01` | Future orchestrator asks Portia to enumerate one Event scope | Enumerate Portia-owned semantic custody; mark foreign references separately |
| `S02` | Orchestrator infers deletion from filename age | Prohibited; require Portia semantic candidate |
| `S03` | Portia advertises `delete_derived_cache` | Capability does not mean eligibility or authorization |
| `S04` | Policy says record eligible, Portia Operation Journal is in progress | Portia returns blocked |
| `S05` | Dry-run source changes before execution | `stale_candidate`; re-evaluate |
| `S06` | Authorization covers one Event only | Do not expand to all records for same student |
| `S07` | Portia record references Core retained scan | Portia owns its reference; Core owns scan action |
| `S08` | Portia action succeeds, Core action fails | Preserve per-module partial result |
| `S09` | Vitrine has sealed prior Portia projection | Portia action does not mutate Vitrine custody |
| `S10` | Local export bytes deleted, receipt retained | Verify bytes absent; provenance follows independent policy |
| `S11` | Plan interrupted after Portia delete commits | Reconcile operation; do not replay blindly |
| `S12` | Cross-module atomicity would require recreating deleted content | Do not resurrect; recover forward with partial state |
| `S13` | Hold release inferred from age | Reject inference; require authoritative release |
| `S14` | Unsupported Portia contract version | `unsupported` or `unresolved`; do not delete |
| `S15` | Correction graph incomplete | Block/unresolved |
| `S16` | Required disagreement remains tied to surviving contested record | Preserve dependency |
| `S17` | Coherent historical unit authorized for routine disposition | Validate module-local action if all conditions pass |
| `S18` | Generic Exceptional Removal requested for an old record | Reject generic path; Exceptional Removal stays narrow |
| `S19` | Authorized exceptional case satisfies existing invariants | Route through Portia Exceptional Removal semantics |
| `S20` | Stale derived substantive copy remains after source disposition | Cleanup/rebuild must prevent resurrection |
| `S21` | Dry-run plan generated | No mutation |
| `S22` | Scope/policy changes after evaluation | New immutable plan revision |
| `S23` | Portia succeeds but district backup unknown | Report local success plus outside-suite unresolved status |
| `S24` | Emailed/downloaded copy exists | `outside_suite_control` |
| `S25` | Module result already verified on restart | Idempotent completed result; do not replay |
| `S26` | File missing but no trustworthy operation evidence | Do not assume delete succeeded |
| `S27` | Orchestrator tries direct filesystem unlink in Portia tree | Prohibited; module-owned execution only |
| `S28` | Portia adapter returns retention class | Do not return hard-coded institutional duration as Portia truth |
| `S29` | Shared protocol needs discovery/version negotiation | Candidate for Core/shared layer, not Portia-only schema |
| `S30` | Future Sunset consumes institutional policy | Orchestrate; do not adjudicate legal validity |
| `S31` | Foreign owner reports verified completion | Orchestrator may record owner-verified status |
| `S32` | Required foreign action remains pending | Global plan remains partial/unresolved |
| `S33` | Non-required foreign reference survives Portia disposition | Stable historical reference may remain |
| `S34` | Planning report would include Account quote | Omit narrative; use privacy-minimal codes |
| `S35` | Runtime later needs new Portia operation kind | Later version/implementation work; do not mutate speculatively now |
| `S36` | `pds-sunset` package absent | No dependency/import; capability boundary only |
