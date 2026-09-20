# Issue #47 lifecycle, correction, and recovery services validation

**Status:** final closeout authority  
**Starting checkpoint:** `f61b98fe261cba0c5998ed976bca2ff010cd486a`  
**Scope:** public services, exact-history behavior, recovery/removal authority,
package inventory, and installed-wheel acceptance

This document is the authoritative final responsibility audit for Issue #47.
It does not replace the accepted schemas, ADRs 0008, 0009, 0018, or 0019, or
the focused validation records for Ownership Correction and Exceptional
Removal. No item below is unclassified.

## Version and write authority

- `ownership_correction@1` is immutable historical-read authority.
- `ownership_correction@2` is current write authority.
- `operation_journal@2` remains the authority for ordinary byte-present
  operations, including Ownership Correction.
- `operation_journal@3` is required for verified canonical-absence write sets,
  including `exceptionally_remove`; it does not replace v2 for ordinary work.
- Historical v1/v2 records are never automatically upgraded. Exact references
  remain exact and never imply `resolve_latest()` behavior.

## Final responsibility matrix

| Responsibility | Public production service/API | Implementation module | Storage/runtime authority | Principal evidence | Issue #22 anchor | Installed-wheel evidence | Status | Boundary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Lifecycle and corrected lifecycle history | `LifecycleWorkflowService` | `portia.workflows.lifecycle`, `lifecycle_history` | repository + lifecycle transition/history records + journal v2 | `test_workflow_lifecycle.py`, `test_workflow_lifecycle_history_correction.py` | G22-011/G22-012 | compact disagreement transition in generic wheel smoke | implemented + tested + installed-smoked | exact registered contracts only |
| Nonmaterial amendment | `AmendmentWorkflowService.apply_amendment` | `portia.workflows.amendments` | append-only Amendment + target replacement + journal v2 | `test_workflow_amendments.py` | P22-04 distinction | valid Event summary amendment | implemented + tested + installed-smoked | allowlisted nonmaterial paths only |
| Statement of Disagreement | `StatementOfDisagreementWorkflowService` | `portia.workflows.disagreements` | exact separate canonical record + lifecycle/supersession | `test_workflow_disagreements.py` | P22-04, G22-013 | create and lifecycle-select separate statement | implemented + tested + installed-smoked | no finding or target mutation implied |
| Dependency declaration and gates | `DependencyWorkflowService` | `portia.workflows.dependencies` | exact dependency records + reconciled graph | `test_workflow_dependencies.py`, current-use/completion gate tests | G22-014 | required current-use gate | implemented + tested + installed-smoked | no automatic cascade |
| Record migration | `RecordMigrationWorkflowService` | `portia.workflows.migrations`, `migration_commit` | registered transformer + migration record + journal v2 | `test_workflow_migrations.py`, `test_workflow_record_migration_commit.py` | G22-015/G22-016 | public installed import; compact material path uses correction authority | implemented + tested | no retargeting of historical refs |
| Material correction/supersession | family services, including `AccountWorkflowService.correct` | family workflow + supersession modules | explicit successor, predecessor transition, journal v2 | `test_p22_04_account_correction_preserves_review_exact_historical_evidence` | P22-04, G22-010/011/012 | Ownership Correction provides compact material successor path | implemented + tested + installed-smoked | no silent frontier following |
| Ownership Correction | `OwnershipCorrectionWorkflowService` | `portia.workflows.ownership_correction`; internal `action_reownership` coordinator | `ownership_correction@2`, lifecycle evidence, journal v2 | `test_workflow_ownership_correction.py` | ownership variants of G22-002/003/014/034 | Event Follow-Up to Support Process correction | implemented + tested + installed-smoked | closed six-family registry; Event class-ownership unsupported |
| Exceptional Removal | `ExceptionalRemovalWorkflowService` | `portia.workflows.exceptional_removal` | certificate-first canonical removal + journal v3 | `test_workflow_exceptional_removal.py`, `test_operation_journal_v3.py` | G22-028/029/037 analogues | compact real work removal and removed resolution | implemented + tested + installed-smoked | configured local authority; no generic delete |
| Recovery | `RecoveryWorkflowService` | `portia.workflows.recovery` | recovery assessment, exact journal pointer, staging, locks | `test_workflow_recovery.py`, `test_workflow_recovery_p22_14.py` | P22-14, G22-028/G22-029 | nonmutating completed-operation assessment | implemented + tested + installed-smoked | ambiguous/branched evidence remains manual |
| Integrity projection and guard | `IntegrityWorkflowService`, `IntegrityGuard` | `portia.workflows.integrity`, `integrity_authority` | deterministic derived generation, exact operator series | `test_workflow_integrity.py`, `test_workflow_integrity_operators.py` | G22-028/029/034/036/037 | missing required current projection fails closed | implemented + tested + installed-smoked | authorization-limited results remain conservative |
| Quarantine | `QuarantineWorkflowService` | `portia.workflows.quarantine` | explicit revision/current-pointer series + guard | `test_workflow_quarantine.py` | graph-invalid containment | installed active block through `QuarantineGuard` | implemented + tested + installed-smoked | operational state, never lifecycle state |
| Actor Directory maintenance | `ActorDirectoryService` | `portia.identity.actors`, `portia.storage.actor_directory` | exact actor/child records and Actor removal certificates | identity, quarantine, and removal tests | G22-006/G22-007 | Actor creation/resolution in generic wheel smoke | implemented + tested + installed-smoked | roster identity stays Core-owned; not re-owned |
| Teacher-local unresolved-attention presentation | none in Issue #47 | none | underlying exact authority only | this audit | not applicable | not applicable | deferred by explicit issue boundary | Issue #49 owns query/presentation |
| Branched recovery, unverifiable lock clearing, unsupported compensation | explicit assessment only | recovery and quarantine guards | evidence retained without mutation | recovery negative tests | G22-028/G22-029 | not suitable for compact smoke | manual-review-only by accepted architecture | no generic repair authority |
| Pre-certificate emergency destruction | no production operation | none | absence is not removal without certificate evidence | journal v3/removal negative tests | G22-037 | absent target resolves differently from removed | manual-review-only by accepted architecture | unsupported; external investigation required |

## P22-04 production parity

`test_p22_04_account_correction_preserves_review_exact_historical_evidence`
executes the real Account correction service. The original Account remains
byte/fingerprint-addressable and becomes explicitly superseded; a distinct
active successor names the predecessor with an exact `work_record_ref`; and
the existing Review remains byte-identical and pinned to the original.

The schema corpus independently proves the separate Statement of Disagreement,
the selected active frontier, and the two independent lifecycle histories.
Production Amendment tests prove that a nonmaterial allowlisted edit appends
Amendment evidence without creating a material successor. Together these
tests establish that Amendment, disagreement, and correction are distinct,
that the current frontier is selected deliberately, and that historical reads
do not follow successors.

## P22-14 production parity

`test_p22_14_production_recovery_preserves_successor_and_finishes_predecessor`
materializes the accepted fixture's real journal, staged bytes, canonical
partial state, and locks, then calls `RecoveryWorkflowService.assess` and
`resume_incomplete`. Preflight evidence precedes canonical mutation; the
already accepted successor survives byte-for-byte; restart does not create it
again; only the remaining safe predecessor write is completed; revision 6 is
explicitly selected; and locks are released only after terminal consistency.
Recovery tests separately reject ambiguous/orphan/changed evidence, so
ambiguity remains blocked rather than guessed.

## Ownership Correction final anchor

The public service owns a closed registry for Account, Observation, Response,
Communication, Follow-Up, and Outcome. It delegates candidate semantics to the
registered family, persists `ownership_correction@2`, transitions the source
to `superseded` with `work_root_corrected`, and uses `operation_journal@2`.
Incoming references remain unchanged exact history; every incoming reference
and Dependency requires an explicit disposition; there is no cascade.

The public integration tests prove complete dispositions, six-family and
work-kind-pair closure, certificate persistence, deterministic idempotent
recovery, and preservation of accepted destination/certificate bytes during
partial-state recovery. `ActionOwnershipCorrectionCoordinator` remains an
internal implementation detail. Actor Directory and Core roster identities
are outside this operation. Event class-ownership correction remains outside
the public service boundary.

## Exceptional Removal final anchor

The service requires an exact target, configured local authority, an external
decision reference, complete incoming-reference/Dependency/child review, and
Integrity clearance. It establishes operational Quarantine, writes the
certificate before payload absence, uses the specialized
`operation_journal@3` `exceptional_remove` action, verifies absence, and keeps
salted exact content evidence without copying removed payload.

`removed`, `not_found`, and contradiction are distinct resolutions. Certificate
plus payload is a contradiction; absence plus a matching certificate is
`exceptionally_removed`; absence without a certificate is not removed. Root
and Actor-root child dispositions are complete, incoming refs remain exact,
managed staged/derived copies are purged, recovery is deterministic, and no
ordinary workflow restores or reconstructs removed bytes.

## Graph-invalid traceability

| Fixture/finding ID | Production invariant and principal test | Fail-closed disposition |
| --- | --- | --- |
| G22-010 / G22-025 | exact historical refs; P22-04 and cross-year reference tests | exact predecessor loads; no successor substitution |
| G22-011 | successor topology validation | cycle/ambiguous frontier rejected |
| G22-012 | selected current frontier and lifecycle reconciliation | stale predecessor selection rejected |
| lifecycle/current mismatch | lifecycle family reconciliation tests | current use and transition reject mismatch |
| G22-013 | disagreement exact target validation | mismatched target rejected before persistence |
| G22-014 | required Dependency resolution/gate tests | required mismatch blocks the selected gate |
| G22-015 / G22-016 | migration planning/commit tests | retargeting or continuation-as-migration rejected |
| ownership ambiguity/retargeting | ownership assessment and disposition tests | unsupported pair, changed source, or incomplete review rejects zero-write |
| G22-028 | operation persistence evaluation | committed operation missing a durable result becomes blocking recovery evidence |
| G22-029 | recovery idempotency and P22-14 | accepted write is preserved and not replayed |
| G22-034 | forward/incoming-reference reconciliation | disagreement becomes blocking Integrity evidence; no auto-repair |
| G22-036 | derived-store freshness and integrity projection tests | stale source snapshot/install rejected |
| G22-037 | foreign-destruction and removal authority | unverified destruction is not accepted as removal |
| Quarantine/current-use disagreement | Quarantine guard tests | exact read remains available; current use fails with Quarantine error |
| removal certificate + payload contradiction | `test_accepted_absence_with_retained_or_changed_payload_fails_closed` | corruption/contradiction, never removed |
| canonical absence without removal evidence | removal-state and journal v3 negative tests | ordinary not-found or recovery-required, never removed |

## No-silent-successor audit

Lifecycle history, material family correction, disagreement targets,
Dependency endpoints, migration source references, Ownership Correction
incoming references, Exceptional Removal certificates, current-use gates, and
recovery steps all use exact work/record references. Current selection is an
explicit family reconciliation operation. No public service exposes
`resolve_latest`, generic move, arbitrary mutation, or generic delete semantics.

## Current-use fail-closed audit

The public boundaries keep distinct errors/dispositions for lifecycle-history
mismatch, ambiguous replacement frontier, required Dependency failure, active
Quarantine, blocking Integrity Finding, recovery-required state, missing/stale/
corrupt Integrity projection, exceptional removal, ordinary not-found, and
authorization-limited evaluation. Exact historical reads remain available
where the accepted architecture permits them; none of these conditions is
collapsed into an inactive or missing record.

## Integrity, acknowledgement, suppression, recovery, and Quarantine

Integrity projection tests prove deterministic `integrity_finding@2` keys and
ordering, privacy-minimized closed diagnostics, explicit current generations,
valid zero-finding generations, and stale/missing/corrupt projection rejection.
Acknowledgement is append-only historical review evidence. Suppression is
presentation-only; blocking findings are unsuppressible and suppression never
changes `IntegrityGuard` or completion-gate results. Neither operator changes
Quarantine state or hides ownership/removal contradictions.

Recovery assessment is nonmutating. Mutation requires evidence-proven exact
state, one exact orphan where supported, and expected-pointer concurrency.
Conflicting bytes are never overwritten; accepted evidence is preserved;
replay is idempotent; lock age alone proves nothing. Quarantine is operational,
release is evidence-based, and acknowledgement, suppression, or elapsed time
cannot release it. Canonical-absence and ownership partial-state recovery are
deterministic; removed payload is never reconstructed, and ownership
destination/certificate evidence is never deleted as rollback.

## Privacy audit

Journal v2/v3 records, Integrity Findings, acknowledgements, suppressions,
Quarantines, recovery observations, ownership dispositions/certificates,
removal certificates, Actor removal certificates, and derived metadata were
reviewed as operational evidence. They retain opaque identity, bounded reason,
digests, exact workspace-relative paths, state facts, and authority references.
They do not needlessly duplicate student/person/Event narrative, disagreement
text, removed payload, credentials, secrets, absolute host paths, or unrelated
record bodies. Salted removal evidence is a digest, not retained content.

## Manual and deferred boundaries

Manual review remains required for branched/ambiguous recovery, lock clearing
without external verification, unsupported compensation, repair without exact
authority, and pre-certificate emergency destruction. There is no automatic
Dependency cascade, incoming-reference repair, payload restoration,
institutional/legal decision engine, or unsupported ownership-family/work-kind
coercion. Quarantine release requires accepted evidence. Actor/roster identity
mutation is outside Ownership Correction.

Issue #47 owns the underlying authority and semantics. Issue #49 owns the
teacher-facing unresolved-attention query and presentation layer; this closeout
does not pull that interface forward.

## Package and qualification evidence

`scripts/check_package.py` is the package inventory authority. The wheel must
contain all service/storage modules above, the runtime bundle, runtime coverage,
and `py.typed`, without the source schema tree or a sibling runtime dependency.
The sdist must contain the source schemas, modules, this document, ADRs 0018 and
0019, the validator, package checker, smoke, and tests.

`scripts/smoke_test_wheel.py` creates a new venv, removes `PYTHONPATH`, installs
authenticated Core 0.6.3 and the fresh Portia wheel with `--no-deps`, runs
`pip check`, verifies import outside the checkout and version 0.2.0, checks the
runtime bundle/`py.typed`, imports every final service, and executes compact
behavioral anchors. Full P22-04 and P22-14 remain source integration tests.

The final mechanical gate is:

```text
python scripts/validate_issue47_workflows.py --stage source
python scripts/validate_issue47_workflows.py --stage distribution
python scripts/validate_issue47_workflows.py --stage repository
```

The final observed command counts, artifact filenames, and runtimes belong in
the Slice 33 completion report so this authority document does not encode a
brittle expected repository total.
