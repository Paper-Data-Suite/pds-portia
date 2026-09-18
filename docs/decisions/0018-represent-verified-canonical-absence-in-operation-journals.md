# ADR 0018: Represent Verified Canonical Absence in Operation Journals

- **Status:** Accepted
- **Date:** 2026-09-17
- **Decision owners:** Portia maintainers
- **Related issue:** `#47 — Implement lifecycle, amendment, disagreement, correction, and exceptional recovery services`
- **Builds on:** ADR 0008 and ADR 0009
- **Preserves:** immutable published schemas; complete bounded write sets; evidence-first recovery; no generic hard-delete authority

## Context

`operation_journal@2` assumes that every durable, verified, or accepted write
step has an observed result containing a fingerprint of bytes that remain at the
destination. Exceptional Removal instead has a canonical gate whose truthful
postcondition is that one exact, previously accepted canonical path is absent.
Using `remove_transient`, an old fingerprint as a fake post-state, a tombstone,
or an unjournaled filesystem mutation would make the durable record false.

A separate absence sidecar was considered and rejected. It would either omit
the destructive canonical step from the operation write set or duplicate
commit/recovery authority outside the journal. Mutating version 2 was also
rejected because published schemas are immutable.

## Decision

Publish `operation_journal@3` as an additive version. Version 2 remains the
current write authority for existing non-removal operation families. Version 3
is required when an operation write set contains verified canonical absence.
Version 3 may represent ordinary present-byte writes for recovery and
orchestration parity. One immutable operation revision series uses exactly one
journal contract version; v2 and v3 series may coexist in a workspace.

Version 3 adds the action `exceptional_remove`. It means only: make one exact,
already accepted canonical representation unavailable under an
`exceptionally_remove` operation. It is a `canonical_gate` for the
`canonical_domain`, requires a `must_match` precondition with exact prior
contract version and fingerprint, and is never dispatched by the ordinary byte
writer or `remove_transient` path.

Version 3 discriminates results:

```text
present intended result
  kind, contract_version, fingerprint, selected_state

absent intended result
  kind, prior_contract_version, prior_fingerprint,
  removal_certificate { ref, workspace_relative_path, fingerprint },
  selected_state

present observed result
  kind, workspace_relative_path, fingerprint, observed_at

absent observed result
  kind, workspace_relative_path, observed_at
```

The absence branch contains no removed payload and no digest of nonexistent
bytes. The prior fingerprint must equal the step precondition. The exact
certificate link must equal a preceding certificate-creation write in the same
bounded write set. The reference supports the existing class-scoped removal
reference and a minimal Actor-directory removal reference branch.

An absence step can be durable only after the exact destination was observed
absent. Verification additionally requires the exact certificate bytes,
identity, target, operation linkage where applicable, and prior-content
evidence to agree. Acceptance requires those checks plus the operation-specific
canonical acceptance gates. A committed or completed journal still requires
every canonical gate to be accepted, so payload presence or unverified absence
cannot reach the commit point.

Integrity and recovery evaluate absence inversely from byte-present writes:

- matching certificate plus absent target is valid evidence according to the
  journal disposition;
- retained prior bytes, changed bytes, missing/mismatched certificate, and
  unexplained absence are distinct fail-closed conditions;
- certificate-present/payload-absent journal lag is durable-unverified and can
  be reconciled without repeating destruction;
- recovery never reconstructs removed content and never selects state by time,
  filename order, or highest schema version.

The current pointer remains `operation_current_pointer@1`; its exact revision
selects a journal whose body declares its version. Existing operation reference
shapes already carry `contract_version` and require no new version.

## Consequences

Readers and recovery paths must parse v2 or v3 from the selected revision's
explicit `schema_version`. New Exceptional Removal execution still requires a
separate specialized primitive, authorization, Quarantine, and application
workflow. This ADR does not add any generic deletion API.

The following alternatives remain prohibited: `remove_transient` for accepted
canonical payload, fake fingerprints, tombstone replacements, unjournaled
deletion, and a sidecar that hides the mutation from the operation write set.
