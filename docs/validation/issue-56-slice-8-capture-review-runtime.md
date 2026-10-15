# Issue #56 Slice 8 — Capture Review Runtime Promotion

Slice 8 promotes the accepted `capture_review@1` contract unchanged to
`current_v0_3 / modelled=true`.

Capture Review is immutable attributable human confirmation over one exact
Capture Proposal and Paper Interpretation generation. It is not source truth,
institutional authority, behavior-domain Review, Quarantine, or canonical
materialization.

Accepted v1 vocabulary remains:

```text
disposition: accepted | corrected_and_accepted | rejected | unresolved
field decision: accept_candidate | correct | select_alternative |
                mark_unreadable | leave_unresolved
```

Higher-level product actions remain workflow choreography rather than new schema
semantics in this slice: revise may become corrected-and-accepted, defer remains
unresolved/current-decision workflow, split belongs to proposal choreography,
and rescan belongs to source/page recovery.

Review correction/reversal creates later immutable review sequences. Sequence 1
has no predecessor; later sequences require predecessor identity. Cross-record
lineage, reviewer eligibility, cycle/fork policy, current-decision derivation,
materialization, and imports remain later application/service responsibilities.

Expected modeled runtime count after this slice: `78`.

The installed-wheel smoke preflights the candidate wheel payload before
installation so stale `dist` output fails explicitly.
