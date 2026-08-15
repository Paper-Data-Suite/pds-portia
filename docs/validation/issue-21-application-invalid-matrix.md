# Issue #21 Application-Invalid Matrix

**Status:** Slice 7 validation artifact
**Date:** 2026-08-14

JSON Schema establishes local structure for the public Issue #21 export
contracts. It cannot establish recipient entitlement, legal policy validity,
multi-record privacy meaning, cross-module custody, or runtime disposition
safety.

The following conditions are therefore **application-invalid** even when every
individual JSON value is structurally valid.

## Projection / policy

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Projection policy | policy ID/version/digest cannot be resolved exactly | fail closed; do not substitute latest/default policy |
| Projection policy | unknown source record kind or unsupported contract version would flow outward | `withheld`, `unavailable`, or `requires_manual_review` according to cause |
| Projection policy | consumer requests `include_private`, `include_all`, raw/native record pass-through, admin/debug bypass, or equivalent broadening | reject request; consumer may narrow but not broaden producer floor |
| Projection purpose | `student_facing`, `family_facing`, or `participant_specific` has no exact focal participant/subject | stop projection |
| Projection purpose | focal identity inferred from name, email, display snapshot, fuzzy Actor match, roster position, or filename | reject inference |
| Authorization | projection purpose/audience label is treated as proof of requester authorization | reject use |
| Authorization | Actor relationship is treated as proof of guardianship, custody, FERPA entitlement, or disclosure authority | reject use |
| Authorization | Communication `privacy_scope` is treated as authorization | reject use |
| Authorization | structurally valid authorization provenance does not actually cover exact purpose/scope/output | reject export/use |
| Projection state | `withheld` is serialized as absent, false, no, zero, empty string, or not-applicable | reject representation |
| Projection state | `unavailable` is serialized as absent or false | reject representation |
| Projection state | unresolved `requires_manual_review` is silently included | stop projection/export |
| Projection state | withheld record count/existence is revealed when policy does not authorize existence disclosure | reject outward representation |
| Currentness | superseded/invalidated predecessor is counted/presented as another current fact | reject projection |
| Currentness | exact historical reference silently follows current/latest successor | reject resolution |
| Currentness | Exceptional Removal is bypassed by stale derived cache that reconstructs removed payload | reject derived result and clean stale state |

## Multi-participant redaction

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Event | Event summary contains unresolved third-party identity/content | `requires_manual_review`; no automatic paraphrase |
| Event | exact time/location/context combination creates material indirect identification risk | coarsen only by explicit truth-preserving policy or require manual review |
| Event Participant | unrelated participant name removed but stable native participant ID remains | reject as unsafe redaction |
| Event Participant | hidden participant count is exposed and itself identifies the event/people | withhold count or require manual review |
| Event Participant | descriptive/unknown person is assumed non-identifying because no roster/Actor ref exists | reject assumption |
| Event Participant Role | `reported_involved` is transformed into responsible/offender/guilty | reject semantic transformation |
| Multi-target source | source originally targets A+B+C but focal projection implies native source concerned only A | reject false singularization |
| Multi-target source | removal of non-focal identities changes proposition/meaning | `requires_manual_review` |
| Account | focal student is source, so all Account text is assumed safe | reject assumption; inspect complete content segments |
| Account | focal student is target, so third-party source identity becomes automatically visible | withhold source identity unless exact policy permits |
| Account | `verbatim_quote` is edited/paraphrased and still represented as quote | reject transformation |
| Account | unsafe words are spliced from a sentence to manufacture safe evidence | require manual review; do not splice |
| Account | anonymous/withheld/uncertain/not-recorded source states are collapsed into one "unknown" meaning internally | reject normalization |
| Observation | narrative naming another person is included because focal measurement is safe | separate measurement/narrative decisions |
| Observation | visibility of Observation is treated as source-artifact authorization | reject artifact access |
| Communication | unrelated recipients are hidden by name but endpoint refs/participation states remain | reject leakage |
| Communication | `restricted` privacy scope is treated as ordinary | fail closed |
| Communication | `unknown` privacy scope is treated as ordinary | fail closed |
| Communication | summary narrative is automatically exposed without safe-content determination | manual review or withholding |
| Contact Point | email/phone is included because Actor is otherwise visible | reject exposure outside explicit authorized contact purpose |
| Foreign attachment | safe Communication automatically authorizes sibling/external attachment | reject access |

## Correction / disagreement

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Correction | current projection hides material correction and leaves obsolete representation looking current | reject misleading projection |
| Correction | correction history is exported as raw technical graph when bounded currentness context would suffice | narrow projection |
| Statement of Disagreement | contested content is included where applicable policy requires disagreement association, but active disagreement is silently omitted | reject combined projection |
| Statement of Disagreement | disagreement contains unresolved third-party content | manual review combined disclosure unit |
| Statement of Disagreement | quote/recorded-summary representation is changed in projection | reject semantic rewrite |
| Ownership/migration | moved/migrated record silently retargets historical exact ref | reject resolution |
| Exceptional Removal | certificate is interpreted as evidence that every child/foreign source was also destroyed | reject inference |

## Deliberate export

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Export | `pexp_` path does not agree with exact export identity | reject acceptance/recovery |
| Export | output path contains student/person/class/behavior labels or other unnecessary PII | reject artifact path |
| Export | output digest/byte length disagree with read-back bytes | reject acceptance/recover |
| Export | source inventory representation digest/length disagrees with exact consumed source | reject export |
| Export | source inventory silently follows newer source successor | reject export/replay |
| Export | foreign source `contract_version` is null or substituted with latest | reject source |
| Export | exact withheld/unavailable identities are copied into receipt merely to explain omissions | reject privacy-minimal provenance |
| Export | projection decision digest cannot be verified | reject acceptance/recovery |
| Export | manual review says resolved but reviewed digest differs from export decision digest | reject export |
| Export | focal-purpose export lacks exact focal subject or scope alignment | reject export |
| Export | request attribution is not deliberate local-operator request | reject accepted deliberate-export workflow |
| Export | `generated_at` precedes request/review/source acceptance chronology | reject record |
| Export | generation is logged as disclosure/delivery/read/consent | reject semantic classification |
| Export | changed source/policy overwrites historical export bytes/receipt | reject mutation; create new export |
| Export | new export supersedes old one and application deletes old bytes merely because supersession exists | retention/disposition evaluation required |
| Export | output artifact accepted but receipt write interrupted, retry generates second artifact | recover exact accepted artifact and create only missing receipt |
| Export | identical bytes are used as proof two deliberate export actions are same business identity | reject identity collapse |

## Aggregate / de-identification

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Aggregate | stable native Portia IDs are retained and called de-identified | reject claim/output |
| Aggregate | name removal is treated as sufficient de-identification despite rare time/location/free-text combinations | review contextual re-identification risk |
| Aggregate | raw Account/Communication free text is used as grouping/output field | reject default aggregate projection |
| Aggregate | small/rare cell permits practical re-identification | suppress/coarsen/manual-review under exact policy |
| Aggregate | missing/withheld/unavailable data is treated as zero | reject aggregate semantics |
| Aggregate | superseded predecessor and successor are both counted as current | reconcile currentness |
| Aggregate | protected attribute is surfaced merely because an equity report exists | require exact authorized policy and minimum necessary output |
| Aggregate | repeated queries/cross-table linkage defeats one-query suppression | treat as re-identification risk; policy/manual controls required |

## Retention / request / hold

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Retention | Portia retention class is interpreted as a legal duration | reject policy evaluation |
| Retention | record age alone is treated as trigger fact | require exact policy trigger |
| Retention | missing external trigger is guessed from inactive/closed status | `unresolved` |
| Retention | schedule says eligible but required destruction authorization is absent | `eligible_pending_authorization`; no destructive execution |
| Retention | delete/destroy request is treated as approval | `needs_policy_review`; block destruction |
| Retention | local Actor relationship is used to approve request entitlement | reject decision |
| Retention | outstanding access/inspection hold covers item but disposition proceeds | block |
| Retention | hold release inferred from age/inactivity | block/unresolved until explicit authoritative release |
| Retention | active/in-progress Operation Journal or recovery evidence is cleaned by age | block |
| Retention | relevant Integrity Finding/Quarantine uncertainty is ignored | block/unresolved |
| Retention | Statement of Disagreement dependency is broken while contested record survives | reject partial disposition |
| Retention | "preserve history" is interpreted as universal retain-forever rule | apply external policy to coherent historical unit |
| Retention | ordinary schedule expiry is routed through Exceptional Removal | reject workflow |
| Retention | derived cache survives lawful source disposition and resurrects substantive content | cleanup/rebuild required |
| Retention | cache deletion is treated as canonical deletion | reject inference |
| Retention | export-byte deletion is treated as export-provenance deletion | evaluate independently |
| Retention | retained export receipt implies disposed bytes still exist | outward availability must be truthful through future disposition state |
| Retention | local Portia deletion is reported as deletion of email/download/backup/external copy | reject global claim |

## Cross-module / future Sunset

| Area | Application-invalid condition | Required handling |
| --- | --- | --- |
| Adapter | orchestrator derives Portia semantics from filesystem paths/age/extension | reject plan |
| Adapter | Portia capability is treated as eligibility/authorization | reject plan |
| Adapter | dry-run plan mutates custody | reject implementation |
| Adapter | candidate changed after plan but execution uses stale validation | `stale_candidate`; re-evaluate |
| Adapter | external policy overrides Portia recovery/integrity blocker | block |
| Adapter | Sunset directly unlinks Portia canonical files | reject architecture; module-owned execution only |
| Adapter | Portia Page Record disposition is treated as Core retained-scan disposition | foreign owner action required |
| Adapter | Portia disposition is treated as Vitrine sealed-copy deletion | foreign/separate custody remains |
| Adapter | required foreign action fails but global plan reports completed | preserve partial/unresolved result |
| Adapter | successful destructive Portia action is "rolled back" by reconstructing deleted canonical content | reject compensating resurrection |
| Adapter | missing file after restart is treated as proof prior deletion committed | reconcile Operation Journal/current evidence |
| Adapter | Portia claims foreign owner completion without owner/orchestrator verification | reject status |
| Adapter | outside-suite copies are reported destroyed without authoritative external verification | `outside_suite_control` / unresolved |
| Adapter | Portia publishes provisional adapter vocabulary as permanent suite protocol | defer shared wire contract to future Core/Sunset architecture |

## Structural validation is intentionally insufficient

JSON Schema cannot prove:

```text
requester identity or entitlement
guardian/custody status
legitimate educational interest
legal disclosure exception
legal-hold applicability
institution policy validity
redaction preserves meaning
contextual re-identification risk
exact cross-record resolution
source currentness
correction graph completeness
cross-module custody ownership
external destruction completion
```

These remain application/institution/runtime validation responsibilities.

## Integrity severity guidance

Application-invalid does not automatically mean Integrity Finding or Quarantine.

Use this order:

```text
prevent unsafe operation
-> determine whether persisted state violates an integrity invariant
-> create Integrity Finding only when durable diagnosis is warranted
-> Quarantine only when isolation is required to prevent unsafe use
```

Ordinary privacy uncertainty and human-review need remain distinct from integrity
failure.
