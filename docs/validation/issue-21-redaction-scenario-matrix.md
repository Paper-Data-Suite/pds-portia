# Issue #21 Redaction Scenario Matrix

**Status:** Slice 3 application-policy scenarios
**Date:** 2026-08-14

These are application-level privacy examples. They are not new public JSON
contracts.

| ID | Scenario | Required result |
| --- | --- | --- |
| `R01` | Three-student Event; focal student A; participant B/C exact identities present | Include focal identity conditionally; withhold B/C identities and native IDs |
| `R02` | Event summary names student B | `requires_manual_review` for automatic student/family summary projection |
| `R03` | Exact Event time creates unnecessary identification risk | Policy may truthfully coarsen display precision; native precision remains provenance |
| `R04` | Event location type safe, free-text detail names specialized program/person | Include type if truthful; withhold/review detail |
| `R05` | Focal role `reported_involved` based on third-party Account | Role may be conditional; Account source/content not automatically disclosed |
| `R06` | Native Account target is students A+B; focal A | Do not rewrite native source as singular; represent focal applicability without exposing B |
| `R07` | Focal A is Account source; quote names B | Source identity may be focal; quote requires manual review |
| `R08` | Focal A is Account target; source B | Source identity withheld by default; content requires manual review unless safe |
| `R09` | Account source identity status is `withheld` | Preserve internal `withheld`; do not normalize to anonymous/not-known |
| `R10` | Safe Account segment plus unsafe second segment | Safe complete segment may be included; unsafe complete segment withheld/manual-reviewed without splicing text |
| `R11` | Observation has focal measurement and narrative naming B | Measurement may be conditional; narrative requires manual review |
| `R12` | Observation uses source artifact | Observation visibility does not authorize artifact locator/bytes |
| `R13` | Communication focal A plus unrelated recipient B | A recipient facts conditional; B person/participation/endpoint withheld |
| `R14` | Communication has `privacy_scope=restricted` | Fail closed outward unless explicit policy/manual review permits |
| `R15` | Communication has `privacy_scope=unknown` | Fail closed; do not treat as ordinary |
| `R16` | Communication summary references another family | Summary requires manual review |
| `R17` | Communication focal recipient endpoint points to Actor Contact Point | `endpoint_ref` and email/phone withheld in ordinary outward projection |
| `R18` | Family-facing request where Actor relationship says `parent`/family relation but authorization is absent | Relationship does not establish entitlement; projection cannot proceed on relationship alone |
| `R19` | Contested target has active Statement of Disagreement required by policy; statement contains third-party content | Combined disclosure unit requires manual review; do not omit disagreement |
| `R20` | Superseded predecessor and current successor both in source graph | Present current semantics; do not count predecessor as second current fact |
| `R21` | Exceptional Removal removed source; stale derived cache still has old content | Do not resurrect; source is unavailable/removed according to policy |
| `R22` | Multi-party source where even saying "other students were involved" identifies a rare event | Do not reveal hidden count/existence; manual review if meaning depends on it |
| `R23` | Foreign module attachment referenced by safe Communication | Portia projection does not authorize foreign record |
| `R24` | Student-facing vs family-facing policies differ | Apply exact selected policy independently; neither purpose is automatically broader |
| `R25` | Withheld Account exists but outward policy should not reveal source existence | Recipient-facing projection may use privacy-minimal omission; restricted provenance keeps `withheld` |
| `R26` | Unavailable referenced artifact | Preserve `unavailable`; do not report artifact as absent |
| `R27` | Native role is `present` | Do not transform to witness/bystander or another inferred role |
| `R28` | Repair is completed | Do not project completion as remorse, forgiveness, admission, or restored relationship |
