# Portia Foundation Audit Findings

**Issue:** #23 — Conduct the final Portia foundations architecture audit
**Audit date:** 2026-08-17
**Starting Portia commit:** `523cfd6dd75eef9cb10930e328bb7d98b8924bdf`

This register is permanent. Resolved findings remain listed with their original evidence and resolution.

The machine-readable source of finding identity, classification, status, and disposition is `docs/audits/portia-foundation-audit.json`.

## Summary

| Classification | Count |
| --- | ---: |
| `milestone_blocker` | 5 |
| `implementation_concern` | 3 |
| `future_enhancement` | 2 |
| `institutional_policy_dependency` | 1 |
| `deliberately_out_of_scope` | 2 |

Four repairable milestone blockers have now been found and resolved across Slices 1–2: three active-documentation/authority contradictions from the skeptical review and one cross-platform exact-byte fixture portability defect exposed by the first Windows full-suite run. One blocker remains intentionally open: authoritative post-repair validation and exact final-commit binding must occur in the real branch checkout before the foundation can be approved.

## PF-AUD-001 — README top-level status inventory is stale relative to the merged #17–#22 foundation.

- **Audit domain:** documentation consistency / foundation inventory
- **Classification:** `milestone_blocker`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Affected surfaces:** `README.md`
- **Follow-up:** None

### Evidence

- README.md Current Status lists accepted ADRs only through ADR 0012 and application-invalid matrices only through Issue #16.
- The same README later contains Issue #17–#21 implementation sections, creating an internally inconsistent active status description.
- Issue #22 is absent from the README even though its 52-scenario representative corpus is merged on the audit baseline.

### Expected architecture

Active status documentation must describe the complete accepted foundation through ADR 0017 and the Issue #22 integration corpus without implying that the foundation stops at Issue #16.

### Observed problem

The README contains both an older top-level foundation inventory and newer issue-specific sections.

### Risk / consequence

An implementation agent could incorrectly treat later record families as provisional or overlook the representative graph corpus when planning runtime work.

### Required disposition

Reconcile the README status inventory with the merged foundation and add an Issue #22 current-implementation section.

### Resolution

Slice 1 updates README Current Status to cover ADRs 0001–0017, contract families through Issue #21, and the Issue #22 15-positive/37-negative integration corpus. Slice 2 preserves the legacy Issue #16 exact compatibility phrase (`Review v1, Classification v1, Hypothesis v1, and Determination v1`) while retaining the reconciled status.

### Validation evidence

- Guarded README patch in apply_slice.py
- Slice 2 repairs the Issue #16 exact-wording regression found by the first full run.
- Issue #23 foundation validator checks required audit artifacts and traceability.

## PF-AUD-002 — README assigns future pds-sunset suite-wide archival ownership more broadly than ADR 0017 permits.

- **Audit domain:** suite authority / retention boundary
- **Classification:** `milestone_blocker`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Affected surfaces:** `README.md`, `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`, `docs/design/portia-future-sunset-retention-adapter-boundary.md`
- **Follow-up:** None

### Evidence

- README.md sibling-module list says `pds-sunset` will own suite-wide archival orchestration.
- ADR 0017 says no pds-sunset repository exists, a future Sunset-like component is orchestration-only, Portia retains semantic authority, and Portia performs/verifies mutations of Portia-owned custody.

### Expected architecture

A future retention/disposition orchestrator coordinates policy-fed cross-module planning and fan-out; each module retains semantic and mutation authority over its own custody.

### Observed problem

The README verb `own` can be read as transferring archival/destruction authority to a future module.

### Risk / consequence

A later implementation could centralize destructive authority contrary to the accepted fail-closed module-side contract.

### Required disposition

Narrow README language to orchestration-only and preserve the absence of a current runtime dependency.

### Resolution

Slice 1 replaces the ownership statement with the ADR 0017 orchestration-only boundary.

### Validation evidence

- Guarded README patch in apply_slice.py
- ADR disposition/traceability records ADR 0017 as controlling.

## PF-AUD-003 — README product-position language overstates Portia as recording what 'the institution decided'.

- **Audit domain:** teacher-local authority / terminology neutrality
- **Classification:** `milestone_blocker`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Affected surfaces:** `README.md`, `docs/decisions/0003-adopt-teacher-local-initial-deployment.md`, `docs/decisions/0012-define-review-classification-hypothesis-and-determination-domain-models.md`
- **Follow-up:** None

### Evidence

- README Product Position describes Portia as recording 'what the institution decided'.
- The accepted teacher-local architecture requires explicit decision authority and prohibits teacher-local judgments from masquerading as institution-wide findings.

### Expected architecture

Portia records attributable decisions and the authority/scope under which they were made; it does not upgrade a teacher-local record into institutional truth.

### Observed problem

The unqualified product-position phrase is broader than the accepted authority model.

### Risk / consequence

Downstream UI/reporting could present local Determinations as institutionally authoritative.

### Required disposition

Use authority-bounded wording in the product position.

### Resolution

Slice 1 changes the sentence to record 'what an attributable human decided within documented authority'.

### Validation evidence

- Guarded README patch in apply_slice.py
- Audit report teacher-local authority conclusion.

## PF-AUD-004 — Final post-audit repository validation and final audited commit binding are not yet available.

- **Audit domain:** final validation / approval binding
- **Classification:** `milestone_blocker`
- **Status:** `open`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `docs/audits/portia-foundation-audit.json`, `docs/audits/portia-foundation-approval.json`, `docs/validation/issue-23-portia-foundation-validation.md`
- **Follow-up:** #23 closeout slice

### Evidence

- The #22 handoff reports 1451/1451 complete schema-validation tests on the pre-#23 baseline.
- Issue #23 changes audit documentation, tests, validator code, README language, and schema documentation; the final suite must therefore be rerun in the actual checkout.
- The explicit ready approval record must bind the exact final audited commit, which does not exist until the repaired worktree is validated and committed.

### Expected architecture

A ready verdict is issued only after the actual post-audit checkout passes the full suite and the approval record can bind the exact audited commit.

### Observed problem

At Slice 1 authoring time only the merged #22 baseline is available as complete-suite evidence.

### Risk / consequence

Issuing approval now would make the approval record self-inconsistent and would inherit test evidence across an untested diff.

### Required disposition

Run the full current suite, Issue #22 regression, audit validator, and git diff --check in the user's checkout; then resolve this finding and create the approval record in a closeout slice.

### Resolution

Open. See required disposition.

### Validation evidence

- Pending user-local confirmation after Slice 1 application.

## PF-AUD-013 — Issue #22 exact-byte fixture evidence is not checkout-portable without an LF policy.

- **Audit domain:** cross-platform checkout / exact-byte fixture integrity
- **Classification:** `milestone_blocker`
- **Status:** `resolved`
- **Disposition:** `fixed_in_audit`
- **Affected surfaces:** `.gitattributes`, `tests/fixtures/issue_22`, Issue #22 exact-byte validation tests
- **Follow-up:** None

### Evidence

The first complete post-audit run on the Windows checkout reported:

```text
Ran 1466 tests in 248.967s

FAILED (failures=24)
```

One failure was a Slice 1 README exact-wording compatibility regression. The remaining failure cluster was exact-byte provenance/recovery evidence. Representative expected/observed byte-length pairs were:

```text
1051 -> 1089
581  -> 600
1825 -> 1897
558  -> 577
```

Each delta is consistent with one extra carriage-return byte per line when an LF file is materialized as CRLF.

The affected tests span:

```text
P22-06  structured import source/mapping provenance
P22-12  privacy projection / deliberate export provenance
P22-13  source snapshots / derived output metadata
P22-14  preflight, lock, accepted-successor, and restart fingerprints
G22-032/G22-033 privacy/export negative cases
```

Git still reports the fixture tree clean because checkout line-ending conversion does not require an indexed semantic change.

The repository had no `.gitattributes` policy on the Issue #22 baseline.

### Expected architecture

The same committed synthetic byte fixture must materialize with the same bytes on supported developer platforms when its SHA-256 and byte length are architectural evidence.

### Observed problem

A Windows checkout may convert LF text fixtures to CRLF. JSON/text semantics remain equivalent, but exact byte fingerprints become false. Positive graphs then acquire integrity findings and negative graphs acquire unrelated fingerprint findings.

### Risk / consequence

The foundation's strongest provenance, export, derived-state, import, and operation-recovery assertions become platform-dependent while `git status` remains clean. That can both block legitimate Windows development and conceal actual integrity regressions behind checkout noise.

### Required disposition

1. Pin repository text checkout to LF.
2. Re-materialize the Issue #22 fixture tree from the accepted `HEAD` blobs after the LF policy is installed, so the working tree matches the canonical LF bytes without introducing content changes.
3. Make the Issue #23 validator fail if the LF policy disappears or CRLF reappears in Issue #22 text fixtures.

### Resolution

Slices 2–3:

- add `.gitattributes` with `* text=auto eol=lf`;
- explicitly mark common binary artifact types as binary;
- re-materialize `tests/fixtures/issue_22` from the accepted `HEAD` blobs after the policy is present, rather than editing the historical corpus;
- extend `scripts/validate_portia_foundation.py` to enforce the policy and fixture bytes;
- make the Issue #23 temporary-repository writer emit LF explicitly on every platform;
- and add focused regression tests for both checkout policy and deterministic test-fixture writing.

This does not change any accepted fixture semantics or expected fingerprints. It restores deterministic materialization of the already-accepted LF bytes.

### Validation evidence

The first post-Slice-2 rerun removed the broad Issue #22 fingerprint failure cluster but exposed two repair-mechanics defects: Slice 2 had rewritten the full historical fixture working tree, and the Issue #23 temporary test writer itself emitted CRLF on Windows. Slice 3 corrects both without changing accepted Issue #22 content or fingerprints.

The post-Slice-3 Windows rerun executed **1,470 tests** and left **no `tests/fixtures/issue_22` paths modified**. The five remaining failures are historical README exact-string compatibility assertions rather than exact-byte, schema, graph, or persistence failures. This confirms PF-AUD-013 remains resolved. Slice 4 restores the historical strings in context while preserving the current ADR 0001–0017 inventory. PF-AUD-004 remains open until the repaired branch passes the complete suite.

## PF-AUD-005 — The executable milestone must implement append-preserving recovery without pretending multi-file or cross-module actions are magically atomic.

- **Audit domain:** coordinated persistence / recovery
- **Classification:** `implementation_concern`
- **Status:** `accepted`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `docs/decisions/0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md`, `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`
- **Follow-up:** Executable Portia persistence/recovery milestone

### Evidence

- ADR 0009 uses immutable journals, pointers, exact fingerprints, ordered writes, locks, and reconciliation.
- ADR 0017 explicitly allows partial cross-module success and rejects reconstruction of deleted content as rollback.

### Expected architecture

Runtime services reconcile exact durable state and preserve accepted history.

### Observed problem

No executable persistence layer exists yet, so this correctness property is architectural rather than runtime-proven.

### Risk / consequence

Naive rollback/retry logic could duplicate accepted records or erase accepted history.

### Required disposition

Carry the invariant directly into production persistence/recovery acceptance tests.

### Resolution

Accepted as implementation guidance; no foundation change required.

### Validation evidence

- Issue #22 P22-14 and G22-028..G22-029
- Existing Issue #13 focused suites.

## PF-AUD-006 — Privacy-safe handling of free text and multi-party records requires fail-closed/manual-review paths that must not become routine technical administration for teachers.

- **Audit domain:** privacy / teacher workload
- **Classification:** `implementation_concern`
- **Status:** `accepted`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`
- **Follow-up:** Teacher-facing privacy/export workflow implementation

### Evidence

- ADR 0017 requires manual review when mechanical redaction would alter proposition, attribution, evidence basis, or practical meaning.
- The foundation separately requires proportionate teacher workload.

### Expected architecture

The runtime automates safe structural handling and surfaces concise, semantic review decisions only when required.

### Observed problem

The architecture deliberately leaves UI/workflow implementation to the next milestone.

### Risk / consequence

A literal low-level implementation could force teachers to manage field policies, identifiers, provenance, or redaction mechanics directly.

### Required disposition

Design later workflows around concise review decisions while keeping low-level policy/provenance generation automatic.

### Resolution

Accepted as implementation guidance.

### Validation evidence

- Issue #22 P22-12 and G22-030..G22-033
- ADR 0017 fail-closed rules.

## PF-AUD-007 — Issue #22 proves application invariants through a test-only graph validator; production runtime validation still has to be implemented.

- **Audit domain:** application validation
- **Classification:** `implementation_concern`
- **Status:** `accepted`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `tests/schema_validation/issue_22_graph_validation.py`, `tests/fixtures/issue_22/corpus.json`
- **Follow-up:** Executable application-validation milestone

### Evidence

- tests/schema_validation/issue_22_graph_validation.py is explicitly a test-only integration validator.
- 37 individually schema-valid graphs are intentionally rejected only at application-validation level.

### Expected architecture

The executable milestone must enforce the same exact-reference, ownership, lifecycle, provenance, recovery, privacy, and custody invariants at runtime boundaries.

### Observed problem

There is intentionally no executable Portia application in the foundation milestone.

### Risk / consequence

Treating JSON Schema as sufficient would admit graphs the foundation has already defined as invalid.

### Required disposition

Translate the stable graph invariants into production validation/services without making the test helper a runtime API by accident.

### Resolution

Accepted as implementation guidance.

### Validation evidence

- Issue #22 37 graph-invalid scenarios
- Schema/application separation documented throughout the foundation.

## PF-AUD-008 — Retention periods, legal holds, requester entitlement, disclosure authorization, and destruction approval remain external policy decisions.

- **Audit domain:** retention / disclosure / institutional authority
- **Classification:** `institutional_policy_dependency`
- **Status:** `accepted`
- **Disposition:** `accepted_policy_dependency`
- **Affected surfaces:** `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`
- **Follow-up:** Institution/deployment policy integration

### Evidence

- ADR 0017 deliberately defines semantic retention classes and policy hooks rather than legal durations.
- Portia cannot prove guardianship, entitlement, legal-hold state, institution destruction approval, or purge of external copies.

### Expected architecture

Portia accepts bounded externally authoritative inputs and fails closed when required policy facts are unavailable.

### Observed problem

No generic local-first module can infer institution- and jurisdiction-specific policy truth from the record graph alone.

### Risk / consequence

Hard-coded legal assumptions would create false authority and unsafe deletion/disclosure behavior.

### Required disposition

Preserve external policy provenance and blocked/unresolved states in future runtime work.

### Resolution

Accepted policy dependency; not a Portia foundation defect.

### Validation evidence

- Issue #21 retention/privacy matrices
- Issue #22 P22-13 and G22-037.

## PF-AUD-009 — The shared Sunset-like adapter protocol remains intentionally undefined.

- **Audit domain:** future suite retention orchestration
- **Classification:** `future_enhancement`
- **Status:** `accepted`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `docs/design/portia-future-sunset-retention-adapter-boundary.md`, `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`
- **Follow-up:** Future suite retention/disposition orchestration milestone

### Evidence

- ADR 0017 defines conceptual Portia capabilities but publishes no premature shared protocol.
- At the audited checkpoint no pds-sunset repository is required by Portia.

### Expected architecture

A future suite-level protocol can negotiate capabilities while preserving module-local semantics and mutation authority.

### Observed problem

There is no accepted suite protocol yet.

### Risk / consequence

Premature Portia-only wire contracts would likely create cross-module coupling and protocol drift.

### Required disposition

Define the shared protocol only when the suite is ready to design the orchestrator.

### Resolution

Accepted future enhancement.

### Validation evidence

- ADR 0017 sections 28–33.

## PF-AUD-010 — A privacy-minimized Core intervention publication projection remains future integration work.

- **Audit domain:** Core publication / downstream consumers
- **Classification:** `future_enhancement`
- **Status:** `accepted`
- **Disposition:** `deferred_with_issue`
- **Affected surfaces:** `docs/decisions/0014-define-support-process-support-intervention-implementation-and-fidelity-contracts.md`, `README.md`
- **Follow-up:** Future Core intervention publication integration issue

### Evidence

- ADR 0014/README preserve Portia-native support/intervention authority and identify Core v0.6 intervention_record_set only as a future projection.
- Issue #18 explicitly does not create academic registration, results, Grades, automatic Meridian publication, or automatic portfolio publication.

### Expected architecture

Any future publication remains consumer-neutral and privacy-minimized while Portia stays authoritative for native records.

### Observed problem

No live producer projection is required by the foundation milestone.

### Risk / consequence

Implementing publication prematurely could leak behavior/support detail or conflate behavior support with academic evidence.

### Required disposition

Defer until an explicit integration issue defines the projection and authorization policy.

### Resolution

Accepted future enhancement.

### Validation evidence

- ADR 0014 and README Issue #18 boundary.

## PF-AUD-011 — A working Portia application, production persistence services, GUI/CLI workflows, and live sibling adapters are deliberately outside the foundations milestone.

- **Audit domain:** runtime scope
- **Classification:** `deliberately_out_of_scope`
- **Status:** `accepted`
- **Disposition:** `accepted_out_of_scope`
- **Affected surfaces:** `README.md`, #10
- **Follow-up:** Next executable Portia milestone

### Evidence

- Umbrella #10 explicitly states that the completed foundation does not require a working Portia application.
- Current README likewise identifies production filesystem services and teacher-facing workflows as later executable work.

### Expected architecture

The foundation must constrain later implementation without pretending the runtime already exists.

### Observed problem

No runtime exists by design.

### Risk / consequence

Treating runtime absence as a blocker would expand #23 into a different milestone; treating architecture as runtime proof would be equally incorrect.

### Required disposition

Preserve the non-goal while carrying audit constraints into the executable milestone.

### Resolution

Accepted deliberate scope boundary.

### Validation evidence

- #10 milestone outcome
- Issue #23 audit scope.

## PF-AUD-012 — The foundation audit does not certify FERPA, state-law, district-policy, clinical, special-education, or records-management compliance.

- **Audit domain:** legal/regulatory claims
- **Classification:** `deliberately_out_of_scope`
- **Status:** `accepted`
- **Disposition:** `accepted_out_of_scope`
- **Affected surfaces:** `docs/decisions/0002-define-portia-module-boundaries.md`, `docs/decisions/0003-adopt-teacher-local-initial-deployment.md`, `docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md`
- **Follow-up:** None

### Evidence

- ADR 0017 treats legal entitlement, policy interpretation, legal holds, and destruction authorization as institution/deployment responsibilities.
- Portia explicitly rejects institutional discipline, clinical, IEP, threat-assessment, and district case-management scope.

### Expected architecture

Portia exposes truthful boundaries and policy hooks without claiming legal conclusions it cannot establish.

### Observed problem

Compliance depends on deployment context and institutional policy beyond the repository.

### Risk / consequence

A foundation-approval record could be misread as legal certification if the non-claim is not explicit.

### Required disposition

State the non-claim prominently in audit and approval documentation.

### Resolution

Accepted deliberate scope boundary.

### Validation evidence

- Audit report scope/non-claims.

