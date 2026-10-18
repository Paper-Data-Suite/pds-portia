# Portia #60 Slice 5A - Exact Capture Proposal Readiness (no persistence)

## Baseline and authority

- Parent commit: `2d2ac7ca82f67f302fc0d5f0424dd831b19fbd0a` on `60-paper-interpretation-candidates-capture-proposals`, with merged #59 on `main` at `2bf30bba4daca0dd523824b3bf4aef5e72478f14`.
- Consumes only an **explicitly selected** immutable `paper_interpretation@1` ID **and generation**, after trusted class authorization, Page Record source/route verification and exact historical entry validation from `FilePaperInterpretationHistoryService`.
- A caller-supplied JSON entry map may be passed to the *pure unit-testable planner*, but this is **never persistence authority**. The production service always derives its maps from the validated saved interpretation and rechecks history before returning.

## Precise, deliberately narrow v1 crosswalk

The first qualified mapping is to the exact **Event v1** `/summary` string field, subject to a runtime contract assertion:

| Historical form | Source entry role | Source field | Target | Context |
| --- | --- | --- | --- | --- |
| Event Information | `event_information` | `observed_description` | `event@1 /summary` | `new_work` |
| Multi-Event Information | `event_information` (each separate entry) | `what_happened` | `event@1 /summary` | `new_work` |

This **only** creates a nonpersistent *mapping-readiness plan* if the exact source field already contains a version-qualified, explicit **manual-transcription candidate**. It never copies the candidate text into its mapping; the prospective binding is `{target_path: /summary, source_field: {field_key, value_source: candidate_literal}}`.

These summary candidates are **not** verified Events. Other canonical required fields, student/person references, times, dates, certainty, identities, and work identifiers are not synthesized. A ready mapping always carries `human_review_required`, `missing_required_canonical_details`, and `other_source_fields_unmapped` review flags.

For every other form or entry:

- Context entries yield `context_only`, never a standalone proposal.
- Blank entries yield `blank`, not `false` or an adverse observation.
- Unreadable entries yield `needs_attention`, not an inferred negative.
- An Observation slot with permissible Event **or** Observation mapping yields `target_family_choice_required`, never an arbitrarily chosen family.
- A single-family source without an independently verified exact target field path yields `target_mapping_not_qualified`; the system does not confuse an eligible family with an eligible writable field.
- Event entries whose summary field remains unreadable/unavailable yield `summary_candidate_unavailable` even if other fields have candidates.

## Safety and implementation scope

- No persistence, locks, Page Record changes, Core re-retention, image bytes, OCR, Capture Review, Capture Materialization or canonical domain record writes.
- No source text, student name, privacy-sensitive diagnostic, actor information or local paths in ordinary `summary()` or plan `repr`.
- The pure planner is intentionally nonauthoritative; the production method revalidates authorization, exact selected history and current immutable interpretation, with an after-read guard.
- Later Slice 5B will allocate stable IDs, write validated immutable `CaptureProposalV1` records, re-check same-batch locking/replay and preserve older plans. Broadening the field mapping registry to other target families requires independent exact-target schema qualification, not a broad guess.

## On-machine focused acceptance

Run one targeted Ruff + strict mypy gate for `capture_proposal_planning.py` and one focused pytest invocation covering this Slice and the #60 4B recovery source. Tests are synthetic; real returned-paper qualification remains outstanding under #60.
