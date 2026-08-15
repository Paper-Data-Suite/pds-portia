# Issue #21 Retention and Request Scenario Matrix

**Status:** Slice 5 application-policy scenarios
**Date:** 2026-08-14

| ID | Scenario | Required result |
| --- | --- | --- |
| `T01` | Event becomes inactive/closed | Trigger fact only; do not infer retention expiry |
| `T02` | Support Process completed | Completion is not destruction authorization |
| `T03` | Student removed from current roster | Do not infer institution departure or delete historical Portia records |
| `T04` | External policy requires school-year-end trigger but trusted school-year end is unavailable | `unresolved`; destructive action blocked |
| `T05` | Schedule says retention requirement satisfied but no destruction authorization exists | `eligible_pending_authorization` |
| `T06` | Exact authoritative disposition decision covers Portia custody and all module blockers clear | `authorized_for_module_action` |
| `T07` | Outstanding inspection request covers exact Event | Destructive disposition of covered Event/history blocked |
| `T08` | Access request is resolved but no explicit hold release is supplied by integration | Keep block/unresolved; do not infer release |
| `T09` | Delete request submitted by locally described family Actor without external entitlement decision | `needs_policy_review`; no deletion |
| `T10` | Actor Student Relationship says family/parent-like relationship | Does not prove request entitlement |
| `T11` | Approved nonmaterial correction request | Use Amendment architecture; no in-place historical rewrite |
| `T12` | Approved material correction | Use successor/supersession architecture; preserve predecessor |
| `T13` | Denied amendment with applicable active Statement of Disagreement | Preserve disagreement association while contested record is retained as policy requires |
| `T14` | Retention planner proposes contested record deletion but keeps required disagreement | Reject incoherent partial disposition unless exact policy explicitly permits truthful surviving state |
| `T15` | Retention planner proposes disagreement deletion while contested record remains and policy requires association | `blocked` |
| `T16` | Ordinary retention period expires for canonical Event | Do not create Exceptional Removal merely because period expired |
| `T17` | Authoritative privacy decision requires immediate exceptional erasure and Exceptional Removal invariants are satisfied | Exceptional Removal may be evaluated |
| `T18` | Exceptional Removal certificate exists | Certificate is separate retained evidence; ordinary Exceptional Removal cannot recursively target it |
| `T19` | Derived dashboard cache older than retention threshold but canonical source remains | Cache may be independently disposable if no recovery/hold dependency |
| `T20` | Canonical source lawfully disposed but stale derived cache contains substantive copy | Cache cleanup required; must not resurrect source |
| `T21` | Operation Journal still in progress | Operation/recovery custody blocked from ordinary cleanup |
| `T22` | Active Integrity Finding affects target custody | Destructive action blocked/unresolved pending integrity reconciliation |
| `T23` | Page Record references Core RetainedSourceScan | Portia disposition does not dispose Core scan |
| `T24` | Portia export artifact is eligible for local disposition | Export bytes may be disposed independently from export provenance when policy allows |
| `T25` | Export bytes removed but deliberate_export receipt retained | Receipt must not imply artifact still exists |
| `T26` | Local export was emailed/downloaded before local deletion | Portia must not claim external copy was destroyed |
| `T27` | Vitrine Snapshot contains prior authorized Portia projection | Portia disposition does not erase Vitrine custody |
| `T28` | Hold covers one Event | Do not automatically expand hold to every historical record for the same student |
| `T29` | Hold age exceeds ordinary retention period | Age does not release hold |
| `T30` | External policy version changes | Historical evaluations/exports remain tied to prior policy; new evaluation uses new version |
| `T31` | New Jersey schedule shows record series eligible but Artemis/required authorization not supplied | Eligibility only; do not destroy |
| `T32` | Entire workspace destruction requested | Requires explicit institution policy and cross-category/cross-module planning; no implicit wipe |
