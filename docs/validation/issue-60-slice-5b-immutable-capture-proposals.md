# Portia #60 — Slice 5B: Immutable Capture Proposal persistence

**Baseline:** `f03eb49b1f09f131a83098e4bf6c1f6e1cfcbcea` (passing Slice 5A), branch `60-paper-interpretation-candidates-capture-proposals`.

## Scope

This increment persists exact schema-backed `capture_proposal@1` records only for **proposable** entries from the already verified and pinned Slice 5A mapping plan. Current automatic eligibility remains narrow: the explicitly manually transcribed Event Information or Multi-Event Information summary, under `event@1` `/summary`, with `new_work` context and review flags. All other historical forms, context-only slots, blank/unreadable entries, and ambiguous Observation-or-Event target choices produce **zero proposals** in this increment and retain explicit Needs Attention in the returned summary.

A proposal is an independently reviewable mapping request, **not** accepted source truth. No student matching, Event creation, authorship determination, Capture Review, materialization, Page Record transition, source re-retention, or canonical domain write occurs. Original literal content and uncertain mark alternatives remain only in immutable Paper Interpretation.

## Authority and storage

1. Require trusted class authorization before protected reads. Select a persisted Page Record plus exact `interpretation_id` and positive `generation`; no caller-provided mapping or record JSON is accepted.
2. Slice 5A planner performs Core retained-source custody revalidation, route/Page Target checking, restart-safe saved history inspection and exact historical mapping. Repeat the planner and reread the selected generation **inside the existing Capture Batch lifecycle lock**, then require identical mapping outcomes before write.
3. Use `CaptureProposalV1`, canonical UTF-8 JSON and exclusive-create plus exact model readback. Store only in the canonical Capture Batch work subtree `records/capture_proposal/cprp_<40 lowercase hex>.json`, protected by the existing storage path guard.
4. Deterministic `cprp_` ID hashes the Page Record, pinned interpretation ID and generation, entry key, exact target, exact field bindings and review flags; it contains no candidate literal, class-sensitive path, or copied PDF bytes. Same exact replay **reuses** the prior proposal and returns its original provenance; any ID collision with divergent data refuses to write. A changed interpretation generation or mapping is a distinct proposal; prior records remain immutable.
5. Every inventory read validates bounded filenames and count, saved schema, class/work owner, deterministic record identity, and unexpected/corrupt children. Creation preflights all pending records before the first file is written. A crash after one exclusive create is recoverable via identical replay: already written exact records are reused, while missing records can be created. Stale Capture Batch locks require deliberate recovery; never steal them.
6. Ordinary summaries contain only IDs, counts, status and a human-review requirement; no detected text, personal identity or local scan path. Explicit authorized callers can inspect schema-backed proposal records, but those remain noncanonical staging.

## Gates and deferred scope

- Targeted Ruff check/fix/format/check, strict mypy of the new production module, and one focused pytest command covering #60 Slices 5A and 5B.
- Synthetic acceptance includes real retained source + Page Record + immutable manual interpretation -> Event proposal; restart/replay; zero proposals for ambiguous/unqualified form; authorization denial; source tampering; corrupted proposal identity; missing selected generation.
- Remaining #60 work: qualify additional source-to-target mapping paths; historical context resolution, richer attention/manual workflow, source-page batch orchestration, recovery and integrated teacher menu, real paper/scanner acceptance, and closeout. #61 is responsible for **attributable Capture Review**; #62 for canonical materialization.
