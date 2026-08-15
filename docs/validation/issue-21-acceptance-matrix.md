# Issue #21 Acceptance Matrix

**Status:** Complete
**Date:** 2026-08-14

Issue #21 acceptance is reconciled below. All criteria are satisfied.

| Area | Acceptance criterion | Status | Evidence |
| --- | --- | --- | --- |
| Projection and redaction | Canonical records remain authoritative; projections/exports remain derived. | `PASS` | Projection policy + ADR 0017 §1 |
| Projection and redaction | No canonical student dossier/profile/history is introduced. | `PASS` | ADR 0017 §1 |
| Projection and redaction | Projection policy is closed/allowlist-oriented and versioned. | `PASS` | Projection policy + ADR 0017 §2–3 |
| Projection and redaction | Unknown future fields fail closed. | `PASS` | ADR 0017 §3 |
| Projection and redaction | Purpose/audience does not itself authorize disclosure. | `PASS` | ADR 0017 §2, §34 |
| Projection and redaction | Multi-participant information can be focalized without false singularization. | `PASS` | ADR 0017 §5–6 |
| Projection and redaction | Third-party identity/source/contact information receives separate handling. | `PASS` | ADR 0017 §5–7 |
| Projection and redaction | Free-text redaction can require manual review and is not auto-paraphrased. | `PASS` | ADR 0017 §5, §7 |
| Projection and redaction | absent/withheld/unavailable/included/manual-review meanings remain distinct. | `PASS` | ADR 0017 §4 |
| Projection and redaction | Source artifact/retained scan access is independently authorized. | `PASS` | ADR 0017 §8 |
| Projection and redaction | De-identification is not equated with name removal. | `PASS` | ADR 0017 §5, §10 |
| Projection and redaction | Dashboards/histories remain rebuildable and nonauthoritative. | `PASS` | ADR 0017 §1 |
| Projection and redaction | Statement of Disagreement/correction currentness remains truthful. | `PASS` | ADR 0017 §9 |
| Projection and redaction | Communication privacy_scope remains handling classification, not authorization. | `PASS` | ADR 0017 §7 |
| Export | Export is deliberate and never a view/search side effect. | `PASS` | ADR 0017 §11 |
| Export | Export binds exact source scope and exact policy/profile version. | `PASS` | ADR 0017 §11–13 |
| Export | Export provenance is privacy-minimized. | `PASS` | ADR 0017 §12–13 |
| Export | Export bytes remain outside canonical JSON. | `PASS` | ADR 0017 §13 |
| Export | Corrected source/policy creates successor/new export instead of rewriting history. | `PASS` | ADR 0017 §15 |
| Export | Export generation remains distinct from disclosure/delivery. | `PASS` | ADR 0017 §14 |
| Export | Disclosure-log integration boundary is explicit. | `PASS` | ADR 0017 §14, §34 |
| Export | Old unsafe exports can be restricted/withdrawn/disposed without rewriting source history. | `PASS` | ADR 0017 §15, §25 |
| Export | One export identity represents one accepted artifact. | `PASS` | ADR 0017 §11 |
| Export | source_snapshot@1 is not repurposed for outward export. | `PASS` | ADR 0017 §12 |
| Export | Export creation/recovery reuses Operation Journal/Lock. | `PASS` | ADR 0017 §16 |
| Retention and requests | No universal Portia retention period is hard-coded. | `PASS` | ADR 0017 §17 |
| Retention and requests | Retention classes and explicit trigger facts are defined. | `PASS` | ADR 0017 §17–18 |
| Retention and requests | Policy profile/reference provenance is defined. | `PASS` | ADR 0017 §18 |
| Retention and requests | Missing/unresolved policy fails closed for automatic destruction. | `PASS` | ADR 0017 §19 |
| Retention and requests | Local deletion request is distinct from authorization/approval. | `PASS` | ADR 0017 §20 |
| Retention and requests | Exceptional Removal remains distinct from ordinary retention disposition. | `PASS` | ADR 0017 §23 |
| Retention and requests | Derived caches do not extend or resurrect canonical retention. | `PASS` | ADR 0017 §24 |
| Retention and requests | Destruction claims are scoped to custody actually verified. | `PASS` | ADR 0017 §26 |
| Retention and requests | Outstanding preservation/inspection/hold state blocks destruction. | `PASS` | ADR 0017 §21 |
| Retention and requests | Correction/disagreement history is evaluated as a coherent dependency unit. | `PASS` | ADR 0017 §22 |
| Retention and requests | Export bytes and export provenance have independent retention. | `PASS` | ADR 0017 §25 |
| PDS / Sunset boundary | Portia cannot delete Core/sibling-owned custody by following a reference. | `PASS` | ADR 0017 §27 |
| PDS / Sunset boundary | Future Sunset role is capability-oriented and orchestration-only. | `PASS` | ADR 0017 §28 |
| PDS / Sunset boundary | Portia defines module-side retention/disposition capabilities Sunset will need. | `PASS` | ADR 0017 §29 |
| PDS / Sunset boundary | No dependency/import on nonexistent pds-sunset is added. | `PASS` | ADR 0017 §28 |
| PDS / Sunset boundary | Core remains shared identity/workspace/provenance infrastructure, not retention-policy authority. | `PASS` | ADR 0017 §33 |
| PDS / Sunset boundary | Cross-module planning accounts for dependencies and copied/exported custody. | `PASS` | ADR 0017 §27–32 |
| PDS / Sunset boundary | Partial multi-module disposition failure is recoverable/reportable. | `PASS` | ADR 0017 §32 |
| PDS / Sunset boundary | External/backup copies outside verified control remain explicitly unresolved. | `PASS` | ADR 0017 §26, §32 |
| PDS / Sunset boundary | Dry-run planning is non-destructive and stale candidates are revalidated. | `PASS` | ADR 0017 §30 |
| PDS / Sunset boundary | Module owns mutation/verification; orchestrator does not delete by path. | `PASS` | ADR 0017 §31 |
| Validation and closeout | Any new public schema uses Draft 2020-12, immutable $id, closed shape, and catalog registration. | `PASS` | 3 Slice 4 public contracts |
| Validation and closeout | Valid and structural-invalid fixtures exist for every new public contract. | `PASS` | Issue #21 schema-validation fixture families |
| Validation and closeout | Application-invalid coverage tests cross-record/policy boundaries. | `PASS` | Slice 7 application-invalid matrix/tests |
| Validation and closeout | Required privacy/retention synthetic examples validate. | `PASS` | 24 Slice 7 machine-checked scenarios |
| Validation and closeout | No real student/family/staff data is committed. | `PASS` | All Issue #21 fixtures explicitly synthetic |
| Validation and closeout | ADR 0017 is accepted if available. | `PASS` | ADR 0017 accepted in Slice 8 |
| Validation and closeout | Pre-ADR drift check is recorded. | `PASS` | issue-21-pre-adr-drift-checkpoint.md |
| Validation and closeout | README/schema guide/design docs are reconciled. | `PASS` | Slice 8 idempotent README/schema-guide reconciliation |
| Validation and closeout | Full schema-validation suite passes. | `PASS` | 1077 tests before ADR; rerun required after Slice 8 |
| Validation and closeout | git diff --check passes. | `PASS` | Clean before ADR; rerun required after Slice 8 |
| Validation and closeout | Institutional-policy dependencies are explicitly listed rather than guessed. | `PASS` | Public contract/policy boundary inventory + ADR §34–35 |
| Validation and closeout | Final drift check is recorded. | `PASS` | issue-21-final-drift-checkpoint.md |

## Summary

```text
criteria: 58
PASS: 58
PENDING: 0
```

The post-ADR full local suite passed at 1087 tests, README/schema-guide reconciliation is applied, and the final repository drift check is clean.
