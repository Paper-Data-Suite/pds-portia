# Portia Paper/Import Operational Failure, Recovery, and Integrity Boundaries

Status: Issue #20 Slice 10 consolidation

## Governing rule

Failure in routing, printing, interpretation, mapping, proposal construction,
human review, or canonical persistence must not rewrite source history into a
fiction of success. Conversely, ordinary uncertainty or recoverable processing
failure must not be escalated into exceptional integrity isolation merely because
manual attention is required.

The operational categories are distinct:

```text
ordinary review/retry
≠ Integrity Finding
≠ Quarantine
```

- **Ordinary review/retry** handles expected uncertainty, human rejection,
  unresolved values, malformed individual source units where bounded processing
  may continue, missing optional processing resources, and recoverable execution
  failures whose authoritative lineage remains coherent.
- **Integrity Finding** diagnoses a broken or suspicious invariant: provenance,
  exact-reference, route/work, target/entry, mapping-version, or materialization
  consistency. A finding is diagnostic and does not mutate the affected history.
- **Quarantine** is exceptional isolation used only when an integrity condition
  makes continued ordinary use unsafe. It is not the review queue and is not a
  substitute for unresolved/rejected proposal state. Quarantine is exceptional isolation, not ordinary review state.

Core retained-source history, Portia Page Records, Import Batches, Import Source
Records, interpretation/proposal/review generations, Operation Journal history,
and completed materialization receipts remain historical evidence even when a
later stage fails.

## Required failure/recovery matrix

| Scenario | Durable history that survives | Immediate handling | Integrity Finding? | Quarantine? | Safe recovery / prohibition |
|---|---|---|---|---|---|
| Page Target created; Core registration fails | Capture Batch + Page Target | ordinary retry or retire target | only if contradictory route state is observed | no | do not render/print locator until an exact active registration is verified |
| Core registration succeeds; print fails | Page Target + Core registration | retry printing or retire route/target for future use | no, absent contradictory state | no | registration history remains; failed printing does not imply a returned page |
| Page printed; Page Target later invalidated | printed historical target + Core route history | stop new use; preserve historical target | finding if returned page cannot be reconciled to the historical target | only if unsafe linkage cannot be isolated otherwise | never rewrite the printed page to a newer target/template |
| Returned page resolves to missing/wrong target | Core retained source + route resolution | stop Portia semantic processing | yes | possible if record could otherwise be used unsafely | preserve Core source; diagnose exact module/class/work/target mismatch |
| Historical template/layout version unavailable | Page Record + exact target/layout identity | unresolved processing; require restoration/manual review | yes when the exact declared layout cannot be resolved | normally no | do not interpret with the current/latest template as a substitute |
| Core retains source; Portia dispatch crashes | Core retained source | retry dispatch against the same retained source | no if lineage is coherent | no | create/reconcile one Page Record for the same route + retained source; no source deletion |
| Page Record persists; interpretation/proposal creation crashes | Page Record | retry exact generation/proposal work | no if references remain coherent | no | same profile/generation replay is idempotent; do not create duplicate proposals |
| Human review rejects or leaves unresolved | exact proposal + immutable review history | ordinary review state | no | no | rejection/unresolved is not corruption and produces no automatic canonical record |
| Human review accepted; canonical materialization partially fails | review + Operation Journal partial state | recover same `op_` operation | finding if observed durability contradicts journal/readback | only if indeterminate unsafe canonical state requires isolation | reconcile durable steps; never blindly create the record again |
| Canonical write accepted; receipt write crashes | canonical record + Operation Journal | post-commit recovery | no if readback agrees | no | write/reconcile missing materialization receipt; do not repeat canonical creation |
| Duplicate canonical materialization observed for one accepted proposal/review identity | both canonical representations + lineage | stop further materialization | yes | usually yes until duplicate disposition is resolved | do not silently delete/collapse; use explicit correction/removal/consolidation semantics |
| Same paper route returns a second retained source | both Core retained sources | create a distinct Page Record | no | no | same route does not collapse distinct physical returns |
| Same paper bytes/hash arrive again | both Core retained sources | surface possible duplicate for review | no solely because hashes match | no | content hash is evidence, not automatic source equivalence |
| Import source cannot be read as a bounded source snapshot | attempted import metadata if persisted | fail/close Import Batch without source records | no unless stored snapshot metadata contradicts bytes | no | do not invent rows or source identities |
| Mapping profile/version unavailable | Import Batch/source history | unresolved/failed mapping; restore exact mapping or create later explicit mapping attempt | yes if a persisted proposal claims an unknown mapping version | normally no | never fall forward to `latest` mapping silently |
| One malformed import source record among valid records | exact Import Batch + valid source records + malformed-source evidence | isolate the row/source unit in ordinary import processing | no unless identity/provenance invariants are broken | no | mixed success allowed; valid rows continue independently |
| Ambiguous identity mapping | Import Source Record + proposal candidate | human resolution required | no | no | no fuzzy name/email/row-position identity manufacture |
| Proposal fails domain validation | exact source + proposal attempt/history as applicable | ordinary correction/review | no unless target-contract identity itself is inconsistent | no | source-system assertion remains source data; no canonical record |
| Import review accepted; canonical write fails | exact batch/source/proposal/review + Operation Journal | recover same operation | finding if durability becomes indeterminate or contradictory | only if unsafe state requires isolation | do not duplicate canonical record on retry |
| Unchanged import replay | prior batch/source/proposal/materialization history | reconcile as replay | no | no | no duplicate proposal or canonical record |
| Same source key, changed source content | old and new exact source histories | new explicit history/proposal generation | no | no | never mutate the previously accepted Portia record silently |
| Same source snapshot, changed mapping | old and new mapping histories | new explicit mapping/proposal history | no | no | old review/materialization remains historical |
| Source record absent from a later import snapshot | earlier source/history remains | no action by absence alone | no | no | absence is not deletion, retraction, correction, or supersession |
| Accepted proposal points to wrong page entry / import source record | underlying source history + proposal/review history | stop materialization | yes | possible | repair by explicit later review/proposal/correction history; never rewrite the old source |
| Unknown interpreter/mapping version on persisted history | existing source + staging history | stop semantic use of affected staging record | yes | possible if unsafe downstream use exists | do not substitute a nearby/current version |

## Retain-first and retry invariants

### Paper

Core owns retained-source history. Portia may fail after Core retention without
altering Core's source identity or route history. Retry uses the same exact Core
retained-source identity and route resolution. The same route plus a different
retained source remains a different Page Record. The same route/source/profile
replay must not create a duplicate Page Record, interpretation generation,
proposal, accepted review, or canonical record.

### Import

An Import Batch is one bounded attempt against one exact source snapshot and
mapping configuration. An Import Source Record is one source-side unit, not a
Portia Event. Reprocessing uses the stored source/mapping identity digests to
recognize unchanged replay. Changed content or changed mapping creates new
history. A later snapshot's omission of a source key has no deletion semantics.

## Integrity Finding examples

An Integrity Finding is appropriate for conditions such as:

- Page Record references a missing Page Target;
- Core retained-source provenance required by a Page Record cannot be resolved;
- route module/class/work/target disagrees with the Portia Page Record/Target;
- Page Target declares a template/layout identity that cannot be resolved exactly;
- accepted Capture Proposal/Review points to the wrong `entry_key` or interpretation generation;
- Import Proposal/Review references a missing or mismatched Import Source Record;
- persisted interpretation or import proposal names an unsupported/unknown interpreter or mapping version;
- a materialization receipt disagrees with the exact Operation Journal or canonical readback;
- the same accepted proposal/review identity appears to have produced duplicate canonical materializations;
- a supposedly exact historical reference resolves only by following successor/current/latest state.

A finding does not establish the cause, authorize mutation, delete source
history, or select the correction. It records diagnosis for explicit follow-up.

## Ordinary review/retry examples

Do **not** create an Integrity Finding merely because:

- handwriting is unreadable;
- a mark is ambiguous;
- a field is blank/unmarked;
- a reviewer rejects or leaves a proposal unresolved;
- an import identity candidate is ambiguous and human resolution is required;
- one import row is malformed while its source provenance is still coherent;
- a proposal fails ordinary domain validation;
- a recoverable process crashes before any contradictory durable state exists;
- a template/mapping resource is temporarily unavailable before any persisted
  contract claims an inconsistent version.

## Quarantine threshold

Quarantine is justified only when ordinary processing must be isolated because
using the affected record could violate integrity or provenance guarantees. A
broken exact-reference chain, duplicate canonical materialization with unsafe
current-state ambiguity, or indeterminate partial canonical write may justify
Quarantine. Uncertainty, rejection, missing human confirmation, or ordinary
retry does not.

Quarantine does not erase history. Clearing Quarantine requires externally
verified resolution under existing Portia operation/integrity rules; age alone
is never sufficient.

## Derived queues and current state

Review queues, recovery queues, duplicate-candidate lists, and current-decision
views are derived and rebuildable. Missing or stale derived state does not prove
there is no unresolved review, pending recovery, Integrity Finding, or source
history. Canonical/staging source records and immutable operation history remain
the authoritative inputs.

## Lifecycle and correction matrix

| Persistent family | Ordinary lifecycle/correction rule | Historical rule |
|---|---|---|
| Capture Batch | may open/close/cancel under authorization; correction cannot turn it into Event/Support Process | retain operational batch identity and prior use |
| Page Target before route registration/print | defective metadata may be corrected/replaced before use if no historical route/print depends on it | preserve any prior persisted representation required by local correction policy |
| Page Target after registration/print | material semantic correction requires preserved history and, where needed, a new Page Target + Core route | never rewrite historical page purpose/template/context to make old paper look current |
| Page Record | processing state may progress; duplicate detection is review/diagnostic, not destructive collapse | one returned physical source intake remains represented independently |
| Paper Interpretation | immutable generation; same exact profile replay idempotent; changed interpreter/mapping creates a new generation | old candidate generations remain available to explain review/materialization history |
| Capture Proposal | immutable proposal; correction is a later proposal/review path, not in-place candidate rewrite | original interpretation binding remains exact |
| Capture Review | immutable sequenced review history; later review may supersede operational decision | accepted/rejected/unresolved/corrected history remains attributable |
| Capture Materialization | immutable completed/reconciled receipt | later review/correction does not rewrite the receipt or original canonical lineage |
| Import Batch | bounded attempt may complete/fail/cancel; changed source/mapping is a new historical attempt | old exact source snapshot/mapping identity remains preserved |
| Import Source Record | immutable source-side observation within exact batch; changed content is new history | later absence does not delete or retract earlier source history |
| Import Proposal | immutable mapping proposal keyed within exact mapping profile | changed mapping/content creates new proposal history |
| Import Review | immutable sequenced human decision | later decision does not erase prior review attribution |
| Import Materialization | immutable completed/reconciled receipt | later source/mapping/review changes do not silently mutate the canonical result or receipt |

## Correction versus invalidation

Invalidation means a representation should no longer be used for the purpose it
claimed; it does not mean the historical source never existed. Correction
creates preserved later history according to the owning contract. Neither
operation may delete Core route/retained-source history, rewrite a returned Page
Record into a different physical source, mutate old interpretation/import source
bytes. Portia must never silently retarget exact references to successors.
