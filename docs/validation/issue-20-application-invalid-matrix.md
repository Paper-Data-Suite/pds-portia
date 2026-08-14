# Issue #20 Application-Invalid Matrix

Status: Slice 10 validation artifact

JSON Schema establishes local structure. The following cases require application
validation because they depend on cross-record resolution, Core state, exact
historical versions, authorization, operation history, or canonical readback.

| Area | Application-invalid condition | Required handling |
|---|---|---|
| Capture Batch | batch does not resolve under the expected class/module owner | reject use; do not synthesize another owner |
| Page Target | `work_id` does not resolve to the stated Capture Batch | reject target |
| Page Target / Core | no active Core RouteRegistration exactly targets `portia` + class + capture-batch work + `capture_page_target` + Page Target ID | do not render QR/PDS2 |
| Page Target / Core | route module, class, work, target kind, target ID, or exact contract version disagrees | reject route use; diagnose integrity if persisted history conflicts |
| Page Target | route target requires exact contract version but Core registration is null/unsupported | reject route use |
| Page Target | registered/printed target's template/layout/capture-spec identity is rewritten in place | reject mutation; preserve history/new target+route where required |
| Page Target | exact existing Event/Support Process/child context does not resolve as stated | reject semantic use; do not follow successor/current record silently |
| Page Target | route/fallback content exposes student/behavior details beyond privacy-minimized locator requirements | reject rendering |
| Page Record | route does not resolve to the exact referenced Page Target | reject semantic processing; preserve Core source; raise finding when persisted lineage is broken |
| Page Record | class/capture-batch ownership disagrees with target/route | reject semantic processing |
| Page Record | Core retained-source scan/page/fingerprint does not resolve exactly | reject semantic processing; preserve any independently retained Core history |
| Page Record | same route + same retained source is persisted as multiple logical Page Records without an explicit duplicate diagnosis | reject duplicate creation/reconcile existing record |
| Page Record | same route + different retained source is collapsed into one Page Record | reject collapse |
| Page Record | equal source hash is treated as proof two Core sources are identical and one history is deleted | reject collapse/deletion |
| Paper Interpretation | referenced Page Record does not resolve exactly | reject interpretation |
| Paper Interpretation | `entry_key`/`field_key` is not declared by the exact historical Page Target layout | reject candidate |
| Paper Interpretation | historical template/layout snapshot disagrees with exact Page Target | reject interpretation |
| Paper Interpretation | same Page Record + same interpreter/mapping profile creates duplicate equivalent generations instead of replay reconciliation | reject duplicate generation |
| Paper Interpretation | changed interpreter/mapping overwrites an earlier generation | reject mutation; preserve new generation |
| Paper Interpretation | blank/unmarked/unreadable/ambiguous is converted to false/no/declined/confirmed identity | reject semantic conversion |
| Capture Proposal | proposal points to a candidate outside its exact interpretation/entry | reject proposal |
| Capture Proposal | mapped record kind/contract is unsupported or disagrees with deterministic mapping | reject proposal |
| Capture Proposal | machine proposal infers Actor identity, firsthand status, fault, intent, severity, Classification, Hypothesis, Determination, Fidelity, Outcome, Reentry completion, Repair agreement/remorse/forgiveness, or similar judgment | reject proposal |
| Capture Review | reviewer is not an attributable eligible human for the required decision | reject review |
| Capture Review | accepted candidate does not exist in exact proposal/interpretation | reject review |
| Capture Review | correction overwrites/erases original machine candidate history | reject review persistence |
| Capture Review | review sequence/predecessor chain is non-linear or points to another proposal | reject review chain |
| Capture Materialization | latest/effective review is not `accepted` or `corrected_and_accepted` | do not materialize |
| Capture Materialization | operation intent is not deterministically bound to exact proposal/review and intended canonical outputs | reject operation start/recovery |
| Capture Materialization | lock/preflight coverage is insufficient for coordinated canonical writes | reject operation start |
| Capture Materialization | canonical result lacks `creation_source.type = paper_capture` with exact ingested route/Page Record provenance where the target contract supports creation source | reject acceptance/readback |
| Capture Materialization | Account/Observation paper source citation disagrees with exact Page Record provenance | reject acceptance/readback |
| Capture Materialization | retry creates a second canonical record for the same accepted proposal/review intent | raise integrity finding; stop ordinary materialization |
| Import Batch | stored source fingerprint does not match exact bytes read | reject batch processing |
| Import Batch | mapping profile/version cannot be resolved exactly | reject mapping; do not substitute latest |
| Import Batch | import identity digest does not recompute from the contract-defined source/profile/snapshot/mapping inputs | reject batch |
| Import Batch | previous-run relationship falsely labels changed source/mapping as unchanged replay | reject replay classification |
| Import Source Record | source record is identified by row number, array position, filename alone, display text, or fuzzy person match | reject identity |
| Import Source Record | source-record identity/content digests do not recompute | reject source record |
| Import Source Record | source key duplicates another logical source unit within an exact batch contrary to profile rules | reject/diagnose source identity |
| Import Proposal | `proposal_key` is duplicated for distinct proposals within the same exact source-record/mapping context | reject proposals |
| Import Proposal | proposal identity digest does not recompute | reject proposal |
| Import Proposal | source label/category is automatically converted into Portia Classification/Hypothesis/Determination or other judgment | reject mapping |
| Import Proposal | fuzzy name/email similarity silently creates or selects Actor identity | reject mapping; require human resolution |
| Import Review | reviewer is not an attributable eligible human where human review is required | reject review |
| Import Review | accepted transformed candidate is not the exact proposal candidate | reject review |
| Import Review | correction erases source value/mapping candidate history | reject review |
| Import Materialization | review disposition does not authorize materialization | do not materialize |
| Import Materialization | exact batch/source/proposal identity digests disagree with materialization receipt | reject receipt/recovery |
| Import Materialization | produced canonical record does not preserve `creation_source.type = import` as required by its owning contract | reject acceptance/readback |
| Import Materialization | unchanged replay starts a second canonical-creation intent instead of reconciling existing history | reject duplicate operation/materialization |
| Import Materialization | later import omission is interpreted as deletion/removal of prior canonical Portia record | reject action; explicit Portia removal/correction semantics are required |
| Operations | journal says a step is accepted/completed but canonical readback disagrees | enter recovery/integrity handling; do not continue blind writes |
| Operations | canonical write may be durable but state is indeterminate | recover/verify under existing journal rules; quarantine only if unsafe isolation is needed |
| Integrity | Integrity Finding is used to mutate source/canonical history directly | reject mutation; finding is diagnostic |
| Quarantine | unresolved/rejected/ambiguous ordinary data is quarantined merely because human attention is required | reject workflow classification |
| Derived state | absence from review/recovery/duplicate/current queues is treated as proof no authoritative underlying work exists | reject inference; rebuild from authoritative inputs |
| Exact references | any exact Page Target, domain context, proposal/review, canonical result, or operation reference silently follows successor/current/latest representation | reject resolution |
| Time | print/scan/import/processing/review time is substituted for unknown Event/evidence/Implementation/Outcome/etc. domain time | reject materialization |
| Binary/privacy | Portia JSON embeds scan/PDF/file bytes or temp absolute paths as provenance | reject persistence |

## Integrity severity guidance

Application-invalid does not automatically mean Quarantine. Structural or
cross-record validation failure first prevents the unsafe operation. An Integrity
Finding is appropriate when a persisted state violates or appears to violate an
integrity invariant and requires durable diagnosis. Quarantine is reserved for
cases where isolation is necessary to prevent unsafe use while the finding is
resolved.
