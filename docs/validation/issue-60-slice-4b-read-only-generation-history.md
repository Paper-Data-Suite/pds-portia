# Portia #60 Slice 4B - Read-only Interpretation History and Restart Recovery

## Scope and exact baseline

Pinned prerequisite: Issue #60 Slice 4A commit `496af0816b1c7599c05a1d11d7c50d7fe230e5a2`. This is an **additive** read service. It does not rewrite `interpretation_generations.py`, revise public schemas, change Page Records, or create Captures, Reviews, canonical Event/Observation records, or an approval/current pointer.

## Read contract

`FilePaperInterpretationHistoryService.history(class_id, work_id, page_record_id, authorization=...)`:

1. Requires trusted class authorization **before** class-related file reads.
2. Reopens the exact persisted Page Record, live Capture Batch and active Core route; checks historical Page Target and Core-retained source SHA/physical-page custody through Slice 2's `FileHistoricalPageRegionService`.
3. Reads the existing immutable `paper_interpretation@1` inventory with its bounded file/identity/profile parser. There is no guessed filename, rescan, new retention or regeneration from detected content.
4. Enforces positive **contiguous** generations for this Page Record, unique pinned profiles and exact historical layout. Every declared entry is present; eligible candidate entries expose exactly the declared field keys, region IDs, valid methods/states and choice tokens. A source context entry cannot gain a domain mapping, and ambiguous mappings cannot be silently selected.
5. Reads the inventory again, revalidates Core and Page Record authority, and refuses stale/drifting history. It never acquires a mutating lock merely to list records.

`InterpretationHistory.records` is an explicitly authorized, source-sensitive object. Its `repr` omits the records and its `summary()` returns only Page Record ID, physical source page number, generation counts, current-generation number, status and needs-attention flag. No candidate literals, roster entries, QR strings, actor details, scanner paths or raw source bytes appear in summaries.

## Recovery/integrity boundaries

- An absent interpretation collection means **not interpreted**; it is not a blank page, negative fact or completed review.
- Corrupt JSON, duplicate keys, foreign ownership, unknown interpreter profiles, invalid deterministic identifiers, unsafe paths, generation gaps/duplicates, undeclared fields, forged mark tokens and incompatible manual profiles fail shut with stable diagnostics.
- Historical interpretation entries preserve `blank`, `unreadable`, `candidate` and their lawful field states; `candidate_detected` means only an unconfirmed staging candidate.
- Existing immutable interpretation files are never rewritten or repaired implicitly. A damaged generation requires an explicit recovery decision in a later slice.
- The reader is intentionally Page Record-scoped; source-wide teacher presentation, immutable proposal generation and UI integration remain later #60 slices.

## Focused validation

`tests/test_issue60_slice4b_interpretation_history.py` covers no-history behavior, two-profile restart history, changed Core original, generation gaps, foreign context mapping, undeclared entries, denied authorization before reads, source-inventory immutability and concurrent history drift. Preserve independent Slice 4A generation-writer tests in the focused gate.

## Limitations and later work

This read layer does not itself implement paper registration, OCR, automatic handwriting interpretation, manual multi-field aggregation, teacher review or proposal materialization. It expects Slice 4A's schema-backed generation records and exact historical profile identity. Synthetic regression success is not a claim of real-scanner qualification.
