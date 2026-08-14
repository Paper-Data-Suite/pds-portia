# Import Materialization and Recovery

Issue #20 Slice 9 closes the structured-import path from attributable review to crash-safe canonical Portia persistence.

The governing sequence is:

```text
exact Import Batch
→ exact Import Source Record
→ exact Import Proposal
→ attributable accepted Import Review
→ stable coordinated Operation Journal intent
→ deterministic locks / preflight / staged writes
→ canonical acceptance
→ immutable Import Materialization receipt
```

The receipt is operational lineage. It is not a domain record, a review decision, a transaction engine, or a second canonical source of truth.

## Reuse existing persistence infrastructure

Portia already owns the coordinated persistence machinery needed here:

- `operation_journal@1` / supported operation-journal contract;
- `operation_lock@1` / supported lock contract;
- stable `op_` operation identity;
- deterministic preflight and expected-prior-state checks;
- canonical-gate acceptance;
- durable write fingerprints;
- recovery, compensation, reconciliation, and exceptional Quarantine rules.

Import materialization does not add an `imat_` identifier or a parallel transaction system. The logical materialization identity is the exact import lineage plus the stable coordinated operation intent.

## Public receipt

Slice 9 adds:

```text
import_materialization@1
```

The receipt preserves:

- exact class scope;
- exact Import Batch ID and import identity digest;
- exact Import Source Record ID and source-record identity digest;
- exact Import Proposal ID and proposal identity digest;
- exact Import Review ID and review sequence;
- exact Operation Journal revision;
- exact canonical outputs/affected representations;
- materialization and receipt-attribution timestamps.

It intentionally does **not** copy:

- source rows or source fields;
- source-record keys;
- imported file/API bytes;
- transformed candidate values;
- human-corrected field values;
- canonical record payloads;
- temporary paths.

That information already lives in the appropriate source/proposal/review/domain records.

## Accepted review is a gate, not a domain judgment

Only `accepted` or `corrected_and_accepted` Import Review can enter materialization. A later applicable review sequence supersedes the earlier staging decision before preflight.

Even an accepted Import Review means only that a human accepted the source mapping for the next workflow gate. It does not replace domain-specific human semantics. In particular it cannot itself originate or prove:

- Classification or Hypothesis;
- Determination, fault, severity, or causation;
- Response appropriateness;
- Support recommendation;
- Fidelity;
- Outcome/effectiveness;
- recurrence failure;
- Reentry clearance/completion meaning;
- Repair admission, remorse, forgiveness, or restoration.

Those meanings remain governed by their canonical contracts and human-attribution rules.

## Import provenance in canonical records

Slice 9 does not mutate published `creation_source@1`.

A newly produced canonical record from the import path must use its existing import branch:

```json
{
  "type": "import",
  "source_label": "<source-system/profile label>"
}
```

`external_reference` remains optional. If local policy retains it, it must be an intentional source-record locator and never row order, filename alone, display text, or fuzzy person identity.

The exact provenance is stronger than that coarse canonical marker and remains in the immutable materialization lineage:

```text
Import Batch identity digest
+ Import Source Record identity digest
+ Import Proposal identity digest
+ exact Import Review sequence
+ exact Operation Journal revision
```

Where a canonical evidence contract supports `source_artifact_ref@1`, an import artifact locator may additionally identify the exact workspace snapshot or inert external source record as appropriate. Such a locator remains provenance only; it does not establish truth, authority, authenticity, credibility, or authorization.

## Crash-safe recovery

The critical recovery case is:

```text
accepted Import Review
→ operation preflight succeeds
→ canonical write becomes durable and accepted
→ process crashes before Import Materialization receipt is written
```

On restart Portia must:

1. resolve the same exact Import Batch / Source Record / Proposal / Review lineage;
2. derive the same stable materialization intent;
3. resolve the existing `op_` operation and exact journal chain;
4. inspect durable write/readback evidence;
5. reconcile already accepted canonical targets;
6. complete any safe remaining post-commit steps;
7. write the missing receipt;
8. **not** create another Event, Account, Observation, Support Process, Implementation, Outcome, or other canonical record.

Receipt absence after canonical acceptance is therefore a missing post-commit artifact, not permission to rerun creation.

## Replay behavior

### Same source + same mapping + same reviewed proposal

Replay is idempotent. Stable batch/source/proposal identity evidence and the accepted review lineage reconcile the existing materialization outcome.

### Same source key, changed source content

The later Import Source Record is preserved as new source history. It does not mutate the prior source record or prior canonical record. If human review determines the canonical record requires correction, correction proceeds through the applicable Portia domain mechanism.

### Same source, changed mapping

The newer mapping may produce a new proposal/review lineage. Older proposals, reviews, receipts, and canonical history remain preserved. Mapping change alone is not authority to overwrite a canonical record.

### Missing source record in a later batch

Absence is not deletion. It has no implicit lifecycle effect on earlier Portia records or receipts.

## Produced and affected results

`canonical_results` reuses exact Portia work/work-record targeting.

- `produced`: this operation created and canonically accepted the exact representation.
- `affected`: an exact existing representation was materially involved under a valid operation.

`affected` is not an in-place mutation escape hatch. Existing correction, successor, lifecycle, migration, and ownership-correction rules still apply.

## Import time is not domain time

These are provenance/operation timestamps:

- source snapshot observation;
- Import Source Record observation;
- proposal time;
- Import Review time;
- Operation Journal time;
- materialization receipt time.

None may be substituted for unknown Event, evidence, Implementation, Communication, Follow-Up, Outcome, Reentry, Repair, or other domain time.

## Quarantine boundary

Routine crash/retry or a missing receipt uses Operation Journal recovery. Ordinary rejected/unresolved import proposals remain in review history.

Quarantine remains exceptional integrity isolation, for example when:

- an exact identity digest resolves contradictory history;
- the referenced mapping profile/version cannot be resolved;
- source/proposal/review lineage contradicts itself;
- operation durability cannot be safely reconciled;
- replay would otherwise create an irreconcilable duplicate canonical target.

## Slice boundary

With Slice 9, the safe structured-import path is contract-complete through canonical persistence:

```text
source snapshot
→ Import Batch
→ Import Source Record
→ Import Proposal
→ attributable Import Review
→ coordinated materialization
→ canonical Portia record when allowed
```

Later Issue #20 slices should focus on cross-path failure/application-invalid matrices, Integrity Finding boundaries, lifecycle/correction documentation, synthetic fixture/example expansion, ADR 0016, schema-guide/README reconciliation, and final drift/acceptance closeout rather than adding another import transaction layer.
