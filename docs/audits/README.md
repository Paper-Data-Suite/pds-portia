# Portia Audits

This directory contains durable architecture- and release-audit evidence for Portia.

The Issue #23 audit is intentionally separate from Portia runtime contracts. Audit JSON and approval JSON are governance metadata; they are not public Portia schemas and must not be added to `schemas/schema-catalog.json`.

Current Issue #23 artifacts:

- `portia-foundation-audit.md` — human-readable skeptical architecture audit.
- `portia-foundation-findings.md` — permanent findings register.
- `portia-foundation-traceability.md` — foundation-to-evidence and exit-condition traceability.
- `portia-foundation-audit.json` — machine-readable audit state used by the offline validator.
- `portia-foundation-approval.json` — final `ready_for_implementation` governance attestation binding exact audited substantive commit `834c2e00a07bccfbccf18ecca1ca926af4275b94`.

The repository-level validator is:

```powershell
python scripts\validate_portia_foundation.py
```

A `not_ready` audit is valid without an approval record. A `ready_for_implementation` audit is invalid without one. The final Issue #23 state is `ready_for_implementation`; its approval target is `834c2e00a07bccfbccf18ecca1ca926af4275b94`.

The approval uses a post-commit governance attestation: the approval file necessarily lives in a later governance-only commit because a Git commit cannot contain its own final SHA. The later commit does not move the approved substantive target.

Historical construction checkpoints remain historical evidence. They are not rewritten merely because sibling repositories later advance.

## Portia v0.2.0 release audit

Issue #54 is the final executable-milestone release gate. Its durable evidence is separate from the historical Issue #23 foundation audit:

- `portia-v0.2.0-release-audit.md` — human-readable skeptical release-audit record;
- `portia-v0.2.0-release-audit.json` — machine-readable release-audit state;
- `portia-v0.2.0-release-findings.md` — durable Issue #54 findings register.

The focused validator is:

```powershell
python scripts\validate_issue54_release_audit.py
```

During Phase 1, `PENDING` is the expected audit verdict. `RELEASED — VERIFIED` is reserved for the post-publication state after exact published bytes have passed fresh-download verification.
