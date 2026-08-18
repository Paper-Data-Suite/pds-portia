# Portia Foundation Architecture Audit

**Issue:** #23 — Conduct the final Portia foundations architecture audit
**Umbrella:** #10 — Complete the Portia foundations milestone
**Audit date:** 2026-08-17
**Starting Portia commit:** `523cfd6dd75eef9cb10930e328bb7d98b8924bdf`
**Current Slice 1 verdict:** `not_ready`

## Executive conclusion

The Portia foundation is architecturally coherent enough to proceed toward implementation **after one remaining closeout gate**: the actual post-audit branch must pass the complete repository validation and the final approval record must bind the exact audited commit.

The skeptical review found three genuine active-documentation blockers, and the first Windows full-suite run exposed a fourth blocker in exact-byte fixture portability:

1. the README's top-level foundation inventory still described a #16-era state even though #17–#22 were merged;
2. the README gave a future `pds-sunset` component stronger ownership language than ADR 0017 permits;
3. the README product-position sentence described Determinations as what "the institution decided," which is broader than Portia's accepted teacher-local and explicitly attributable authority model.

Slice 1 repairs the three documentation/authority contradictions. Slices 2–3 repair the cross-platform exact-byte portability blocker exposed by the first Windows full-suite run. Slice 4 reconciles the remaining historical README checkpoint strings without weakening the current foundation inventory.

No public schema defect, missing foundational record family, incompatible canonical-path rule, or new architecture decision was identified that requires ADR 0018.

The real-checkout validation sequence did exactly what this audit was meant to do. The first run exposed the LF/CRLF defect plus a README compatibility regression; the second confirmed the broad fingerprint cluster was gone but exposed repair-mechanics problems; the third executed 1,470 tests with only five historical README exact-string assertions remaining and no Issue #22 fixture-tree modifications. Slice 4 restores those historical checkpoint strings in explicit context. The remaining blocker is evidentiary rather than conceptual: the repaired repository state still needs a fresh complete schema/application-validation run and cannot yet be bound to an exact final audited commit. Therefore no `portia-foundation-approval.json` is created yet.

## Scope

The audit covers the completed architecture foundation:

```text
research
ADRs 0001–0017
active design documents
README
schemas and schema catalog
focused fixtures and validation matrices
Issue #22 representative graph corpus
Core integration boundary
ScoreForm / Quillan / Concord / Meridian / Vitrine boundary claims
future Sunset-like retention orchestration boundary
```

It explicitly does not treat absence of a working Portia application as a defect. Umbrella #10 defines the milestone as implementation-neutral architecture sufficient to begin typed runtime models, persistence services, application validation, and teacher-facing workflows.

## Audit method

The review used five evidence layers.

### 1. Current repository state

The audit started from the exact branch baseline:

```text
pds-portia
523cfd6dd75eef9cb10930e328bb7d98b8924bdf
```

The branch was confirmed to point at the merged Issue #22 state.

### 2. Current relevant suite baselines

The reviewed sibling/current-suite checkpoints were:

```text
pds-core
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-scoreform
047e47f60730b8a5540b5e1d92f008ffad37eede

pds-quillan
268fe0ab6f3d74848bf71f1aa1b939adbe242452

pds-concord
a742d7bb5e46f44d1fb0af3ff1bc77799427559e

pds-meridian
bdd652f699be303418375f71ab9c2179fefe2143

pds-vitrine
8e05250b04e8ed7b916e57637213a5875a55fd78

pds-paper-data-suite
8207d9f3db495913df5e42f1f6aa87734d8933c5
```

These are audit checkpoints, not permanent version pins.

### 3. Accepted architecture

ADRs 0001–0017 were reviewed as a connected system rather than independent essays. The audit specifically challenged:

```text
evidence vs judgment
teacher-local vs institutional authority
identity vs display
work ownership vs participant identity
exact historical refs vs current successors
correction vs erasure
operations vs domain truth
canonical state vs derived state
projection vs export
retention eligibility vs destruction authority
Portia custody vs foreign custody
```

### 4. Executable foundation evidence

Issue #22 supplies the principal integration corpus:

```text
15 positive graphs
37 schema-valid graph-invalid graphs
52 total scenarios
0 planned scenarios
```

Its coverage manifest reports dispositions for all 161 schema-catalog contract families.

The graph-invalid corpus is particularly important because it proves that structural JSON Schema validity is deliberately weaker than Portia application validity.

### 5. Historical versus current checkpoints

Earlier issues recorded exact repository SHAs used to construct their contracts. Those checkpoints remain historical evidence. They are not rewritten merely because sibling repositories have advanced.

The audit distinguishes:

```text
historical construction baseline
!= current audit baseline
```

This prevents later maintainers from "updating" history and accidentally destroying provenance about the contracts that were actually reviewed.

## Evidence hierarchy

Where two active surfaces disagree, the audit uses the following reasoning order:

1. an accepted later ADR controls an earlier conflicting design decision;
2. public schema wire shape controls structural validation of that published contract;
3. schema catalog maps exact contract name/version to exact public schema identity;
4. active design explains application-level semantics not expressible in JSON Schema;
5. representative and focused fixtures prove intended examples and rejection cases;
6. README summarizes the architecture but must not contradict controlling ADRs/contracts;
7. historical checkpoints describe what was true at their recorded point and are not silently modernized.

A fixture never supersedes an ADR merely because a test passes. A README sentence never broadens module authority beyond the accepted architecture.

## ADR dispositions

All current ADRs remain accepted. Three carry explicit nonblocking implementation concerns.

| ADR | Audit disposition | Conclusion |
| --- | --- | --- |
| 0001 | `accepted` | Evidence, interpretation, and determination remain correctly separated. |
| 0002 | `accepted` | Portia's module boundary remains distinct from academic grading, portfolio, clinical, and institutional discipline systems. |
| 0003 | `accepted` | Teacher-local initial deployment remains the governing authority limit. |
| 0004 | `accepted` | Class-owned work, exact roster identity, and canonical work paths remain coherent. |
| 0005 | `accepted` | Event and participant semantics compose with later records. |
| 0006 | `accepted` | Participant roles remain relationship evidence, not fault/guilt claims. |
| 0007 | `accepted` | Exact references, targets, and source-owned relationship direction remain coherent. |
| 0008 | `accepted` | Lifecycle, correction, invalidation, supersession, disagreement, migration, and removal distinctions remain coherent. |
| 0009 | `accepted_with_nonblocking_implementation_concern` | Runtime recovery must preserve accepted writes and cannot pretend multi-file operations are magically atomic. |
| 0010 | `accepted` | Actor Directory remains teacher-local and does not replace roster identity or institutional identity authority. |
| 0011 | `accepted` | Account and Observation remain source-evidence records rather than findings. |
| 0012 | `accepted` | Classification, Hypothesis, and Determination remain attributable human judgments with bounded authority. |
| 0013 | `accepted` | Response and Communication remain distinct from truth/finding/support semantics. |
| 0014 | `accepted` | Plan, Implementation, Fidelity, and Outcome remain separate. |
| 0015 | `accepted` | Follow-Up, Outcome, Reentry, and Repair avoid causal/rehabilitation/remorse overclaim. |
| 0016 | `accepted_with_nonblocking_implementation_concern` | Paper/import paths require exact provenance, replay safety, and human review at runtime. |
| 0017 | `accepted_with_nonblocking_implementation_concern` | Privacy free text can require manual review; legal/retention decisions remain external; future Sunset is orchestration-only. |

No accepted ADR is superseded, deprecated, rejected, or found to require a new decision.

## Domain conclusions

### Identity, ownership, and canonical paths

**Conclusion: coherent.**

Portia preserves four critical distinctions:

```text
class-qualified roster identity
!= participant identity
!= work identity
!= display snapshot
```

A student reference is `class_id + student_id`. Matching local IDs across rosters do not merge students. Matching names do not establish identity. Actor identity does not replace roster identity.

An Event has one owning class even when participants come from another class taught by the same teacher. Cross-class participation does not duplicate or transfer ownership.

The initial top-level work kinds remain:

```text
event
support_process
```

with class-qualified canonical work roots:

```text
classes/<class_id>/modules/portia/work/<work_id>/
```

Issue #22 negative scenarios directly challenge wrong work, wrong class, path/owner mismatch, cross-class ID merge, display-name merge, Actor substitution, and exact historical reference drift.

No competing active canonical-path rule was found.

### References, targets, and relationships

**Conclusion: coherent.**

ADR 0007's exact-reference model remains compatible with later families.

Key rules survive composition:

```text
same-work compact ref -> inherits one legitimate work scope
cross-work ref -> states work explicitly
cross-module ref -> preserves producer module identity
display snapshot -> never participates in resolution
historical exact ref -> never follows successor automatically
```

A target of an Event is not equivalent to targeting every participant. A selected participant set is not a synthetic group identity.

Canonical forward relationship ownership remains the source of truth; reverse links remain derived.

### Lifecycle, correction, and supersession

**Conclusion: coherent.**

The foundation consistently preserves:

```text
amendment != replacement
material correction != erasure
invalidation != supersession
disagreement != adjudication
migration != semantic correction
ownership correction != filesystem move
exceptional removal != routine cleanup
```

Material corrections preserve predecessors. Exact historical refs remain bound to historical representations. Cross-year Support continuation creates new work with an explicit relationship rather than migrating the old work into a new year.

No foundation-wide hard-delete path was found for ordinary teacher workflows.

### Dependencies

**Conclusion: coherent.**

Dependency records do not create a universal cascade. Effects depend on the consuming record family and application rule.

A successor does not silently retarget exact dependency endpoints. Broken required dependencies are validation findings, not guessed repair opportunities.

### Coordinated persistence and recovery

**Conclusion: architecturally coherent; runtime-sensitive.**

ADR 0009 provides enough implementation constraints to build production persistence:

```text
complete preflight
exclusive creation
revision-aware updates
exact fingerprints
ordered write sets
deterministic lock ordering
immutable journal revisions
explicit current pointers
structured partial-state evidence
reconciliation before replay
```

Accepted canonical records are not erased to simulate rollback.

Issue #22 P22-14 and G22-028/G22-029 provide integration evidence for committed-state reconciliation and duplicate-replay prevention.

The architecture correctly does not claim filesystem-wide or cross-module magic atomicity. This is retained as PF-AUD-005, an implementation concern.

### Integrity Finding, Quarantine, acknowledgement, and suppression

**Conclusion: coherent.**

Integrity Finding remains deterministic diagnostic state, not a behavior judgment.

Quarantine remains operational protection, not lifecycle state.

Acknowledgement does not resolve a finding. Suppression is narrow and bounded. Ordinary uncertainty belongs in review/retry state and must not create exceptional administrative artifacts.

### Derived state

**Conclusion: coherent.**

The foundation consistently treats histories, reverse indexes, current views, dashboards, privacy projections, and other indexes as rebuildable/noncanonical.

Critical invariant:

```text
missing derived state != empty canonical graph
```

Issue #22 directly rejects current views that select superseded predecessors, incoming indexes that disagree with canonical forward refs, and source snapshots that no longer represent the derived generation's source state.

### Actor Directory

**Conclusion: coherent.**

Actor records provide durable local identity for recurring non-roster people only.

They do not prove:

```text
guardianship
custody
employment
licensure
institutional authority
disclosure authorization
```

Contact Point verification is endpoint-history evidence, not successful delivery.

Actor-to-Student Relationship is a local reviewed relationship assertion, not legal authority.

### Account and Observation

**Conclusion: coherent.**

Account preserves what an attributed source said or reported. Observation preserves attributable/instrumented observable information.

Neither automatically becomes:

```text
Classification
Hypothesis
Determination
fault
credibility
proof
```

Reported involvement requires its report/evidence basis; repeated reports do not become truth by count.

### Review, Classification, Hypothesis, and Determination

**Conclusion: coherent after README authority wording repair.**

The canonical architecture already preserves these boundaries correctly. The audit found the README product-position sentence too broad, not the underlying contracts.

Determinations remain explicitly attributable and authority-scoped. A teacher-local system does not silently elevate a local judgment into institution-wide truth.

PF-AUD-003 repairs the summary wording.

### Response and Communication

**Conclusion: coherent.**

A Response records bounded action and does not prove misconduct or effectiveness.

Communication records a bounded communication act or attempt and does not prove delivery, receipt, read state, consent, legal notice, or truth of content.

Communication can belong to Event or Support Process context without becoming Implementation.

### Support Process, Support, Intervention, Implementation, and Fidelity

**Conclusion: coherent.**

The accepted planning/execution distinction remains intact:

```text
Support / Intervention plan
!= Implementation
!= Fidelity
!= Outcome
```

A planned schedule does not create an occurrence. An Implementation does not imply fidelity. Fidelity does not prove effectiveness.

Portia support documentation does not claim to be an IEP, clinical plan, diagnosis, or institutionally guaranteed service record.

### Follow-Up, Outcome, Reentry, and Repair

**Conclusion: coherent.**

The foundation avoids outcome overclaim:

```text
completed Follow-Up != favorable Outcome
Outcome linkage != causation
Reentry completion != safety clearance / rehabilitation
Repair completion != admission / remorse / forgiveness / restored relationship
```

Positive, inconclusive, and adverse outcomes are all representable.

### Paper-assisted capture and PDS2

**Conclusion: coherent; runtime-sensitive.**

The accepted path remains:

```text
Capture Batch
-> Page Target
-> Core RouteRegistration / PDS2
-> Core retained-source intake
-> Page Record
-> Paper Interpretation candidate
-> Capture Proposal
-> Capture Review
-> coordinated materialization
```

Core owns generic routing and retained-source identity/bytes. Portia owns behavior-domain interpretation/review/materialization semantics.

Machine interpretation remains candidate state. Blank/unreadable marks cannot be silently coerced into false/no. Materialization requires the accepted human-review boundary.

### Structured import

**Conclusion: coherent; runtime-sensitive.**

Import replay uses stable source/mapping identity rather than filename, row position, display text, or fuzzy person matching.

A source assertion is not a Portia Determination. A later missing source row does not delete existing Portia history. Changed source content or mapping preserves explicit new history.

### Privacy projection and redaction

**Conclusion: coherent; teacher-workload concern retained.**

The privacy model correctly distinguishes:

```text
included
absent
withheld
unavailable
requires_manual_review
```

Record eligibility does not imply field eligibility. Multi-party records are not rewritten as though they were natively singular.

Stable IDs are still identifiers.

Free text that cannot be safely mechanically redacted without changing meaning requires manual review. This is correct privacy behavior but must be implemented without exposing teachers to low-level policy mechanics; see PF-AUD-006.

### Deliberate export

**Conclusion: coherent.**

A deliberate export is one immutable output artifact with exact source inventory, policy identity, authorization provenance, decision digest, output digest/length, and operation evidence.

It remains distinct from:

```text
disclosure
delivery
receipt
read
consent
external acceptance
```

Export output paths must not encode unnecessary PII.

### Retention and future Sunset-like orchestration

**Conclusion: coherent after README repair.**

ADR 0017 is explicit:

```text
retention class != legal duration
eligibility != authorization
Portia disposition != destruction of foreign custody
```

Portia can classify semantic custody and expose bounded capabilities. Institution/deployment policy supplies legal/authorization decisions.

A future Sunset-like component may coordinate cross-module planning, ordering, recovery, and bounded results, but it does not become semantic authority over Portia records and must not directly unlink Portia canonical files.

PF-AUD-002 repairs the README sentence that previously used the broader phrase "`pds-sunset` will own suite-wide archival orchestration."

### Schema catalog and versioning

**Conclusion: semantically coherent; checkout-portability defect found and repaired; final confirmation pending.**

The catalog uses explicit contract name/version mappings and exact `$id` values.

The schema guidance correctly rejects mutable `latest` or `current` schema identities.

Issue #22 reports 161/161 contract-family coverage with no `planned` dispositions.

Issue #23 Slice 1 adds no new public runtime schema and therefore does not require a schema-catalog entry.

The schema README itself had one maintenance weakness: its opening summary and prefix list reflected earlier families while later sections documented Issue #20/#21 additions. Slice 1 updates the top-level catalog description and includes `pexp_` in the identifier prefix list. This is documentation reconciliation, not a wire-contract change.

### Representative graph corpus

**Conclusion: strong integration evidence; not inherited as final #23 proof.**

The positive corpus covers:

```text
neutral Event
conflicting Accounts
cross-class participant identity
correction/supersession/disagreement
paper capture
structured import
Response/family Communication
Support Process and positive Outcome
inconclusive/adverse Outcome
Reentry/Repair
cross-year continuation
privacy/export
derived/retention/custody
operation/recovery
Classification/Hypothesis/Intervention
```

The 37 negative graphs are intentionally schema-valid but application-invalid.

High-value negative clusters:

```text
G22-001..010 identity / exact references
G22-011..016 correction / migration / derived current
G22-017..020 provenance / evidence / human judgment
G22-021..025 support / fidelity / outcome ownership
G22-026..029 paper/import acceptance / replay
G22-030..037 privacy / export / derived state / foreign custody
```

The audit accepts the corpus design. The final branch must rerun it after Slice 1 is applied.


### Exact-byte fixture checkout portability

**Conclusion: blocker found by the first Windows post-audit run and repaired in Slice 2.**

Issue #22 deliberately treats exact bytes as evidence in import provenance, deliberate export, source snapshots, derived outputs, and coordinated-operation recovery. That means repository checkout behavior is part of the executable evidence boundary.

The first post-audit Windows run produced byte-length deltas such as:

```text
1051 -> 1089
581  -> 600
1825 -> 1897
558  -> 577
```

Those deltas are the LF-to-CRLF signature. The committed blobs remained semantically unchanged and Git considered the files clean, but the working-tree bytes no longer matched their accepted SHA-256/length evidence.

PF-AUD-013 therefore adds a repository LF policy and makes Issue #23 validate both the policy and the materialized Issue #22 fixture bytes. The fix does not recompute expected fingerprints to match Windows conversion; it preserves the already-accepted canonical LF representations consistently across platforms. Slice 3 refines the repair mechanics: the historical Issue #22 tree is re-materialized from the accepted `HEAD` blobs after `.gitattributes` is installed, and the Issue #23 temporary test writer itself emits LF explicitly, so the repair does not create a corpus-wide content diff.

The first rerun after the initial LF repair reached 1,469 tests and reduced the failure count from 24 to 6, eliminating the broad Issue #22 fingerprint cluster. The remaining visible portability failure was in the new Issue #23 temporary-repository writer, not in an Issue #22 production generator; Slice 3 corrected that test harness and replaced the corpus rewrite with raw-`HEAD` blob re-materialization. The subsequent Windows run reached 1,470 tests with five documentation-only historical compatibility failures and no Issue #22 fixture-tree modifications, confirming the exact-byte portability finding remains resolved.


## Documentation audit findings

### README status drift

The opening Current Status inventory lists architecture only through ADR 0012 / Issue #16 even though the same file later describes #17–#21 and the repository contains merged #22 integration evidence.

This is PF-AUD-001 and is repaired in Slice 1.

### Sunset ownership overclaim

The sibling-module summary says "`pds-sunset` will own suite-wide archival orchestration." The controlling ADR says no such dependency exists and a future component is orchestration-only while modules retain semantic/mutation authority.

This is PF-AUD-002 and is repaired in Slice 1.

### Institutional-decision overclaim

The product-position sentence says Portia records "what the institution decided." That is too broad for a teacher-local system whose Determinations are explicitly attributable and authority-scoped.

This is PF-AUD-003 and is repaired in Slice 1.

## Teacher workload conclusion

The architecture is technically rigorous but does not require teachers to manually manage:

```text
opaque IDs
schema versions
digests
canonical paths
operation journals
locks
migration records
dependency graphs
derived generations
provenance objects
supersession chains
```

Those are implementation responsibilities.

The teacher-facing runtime should surface only semantic decisions that actually require human judgment: what was observed/reported, what classification/hypothesis/determination is being recorded, what response/support occurred, what follow-up/outcome was evaluated, and when privacy/manual review is required.

## Synthetic-data conclusion

The representative corpus identifies itself as synthetic. Issue #23 adds only governance/audit metadata and synthetic test fixtures.

No real student record is required by the audit.

The final local closeout should still include repository-level secret/PII hygiene checks appropriate to the project before approval.

## Sibling-boundary conclusions

### Core

Current Core remains the shared authority for workspace/class/roster identity, module-qualified work identity, PDS2 routing, retained-source custody, and related common infrastructure.

Portia remains authoritative for Portia domain semantics.

### ScoreForm, Quillan, and Concord

These modules own their academic/collaborative producer semantics. Portia may reference them but does not alter their judgments or convert them into behavior facts.

### Meridian

Meridian owns academic evidence policy, proficiency/Grade/reporting work. Portia does not calculate Grades and the foundation does not require a live Meridian adapter.

### Vitrine

Vitrine owns portfolio curation/composition/snapshot/export semantics. Portia records do not automatically enter portfolios.

Vitrine's completed foundation audit is a useful process precedent, not a runtime dependency.

### pds-paper-data-suite

The suite repository supplies planning/sequence context. It does not become runtime authority over Portia domain records.

## Findings summary

The permanent findings register contains:

```text
5 milestone blockers
  4 resolved across Slices 1–2
  1 open pending final local validation/commit binding

3 implementation concerns
2 future enhancements
1 institutional-policy dependency
2 deliberately out-of-scope findings
```

No unresolved conceptual architecture blocker is known after the Slice 2 repairs.

## Institutional-policy dependencies

Portia cannot independently decide:

```text
legal retention duration
legal hold applicability/release
requester legal entitlement
guardian/custody legal status
district destruction approval
disclosure exception sufficiency
backup/external-copy purge requirements
```

The correct architecture is to consume bounded externally authoritative inputs and fail closed when required facts are absent.

## Deliberately out of scope

The foundation audit does not require:

```text
working Portia CLI/GUI
production persistence implementation
live OCR
live imports
live sibling adapters
institutional authentication/authorization
district case management
IEP/clinical system behavior
threat assessment
grade calculation
portfolio curation
legal/regulatory certification
live Sunset orchestration
```

These non-goals do not weaken the foundation because their boundaries are explicit.

## Downstream implementation constraints

The executable milestone should treat the following as non-negotiable inherited constraints:

1. exact identity beats convenience matching;
2. display text never repairs identity;
3. exact historical refs never silently follow successors;
4. evidence and human judgment remain separate;
5. response/support/implementation/fidelity/outcome remain separate;
6. material correction preserves history;
7. operation evidence is not domain truth;
8. missing derived state is not empty truth;
9. paper/import candidates do not manufacture human judgments;
10. privacy fails closed and free-text semantic redaction can require review;
11. retention classification does not create legal duration or destruction authority;
12. module-local custody remains module-local authority;
13. the Issue #22 application-invalid invariants must move into production validation rather than being lost behind JSON Schema.

## Exit-condition evaluation

Seventeen of eighteen Issue #23 closeout conditions are structurally or architecturally satisfied after Slice 1.

Two entries are represented as blocked in the machine-readable audit because they are one coupled final gate:

```text
EC-17 complete post-audit validation passes
EC-18 ready approval binds exact audited commit
```

They remain blocked by PF-AUD-004.

The approval record is intentionally absent while the verdict is `not_ready`.

## Validation status

Real-checkout post-audit validation progression:

```text
Run 1: 1466 tests — FAILED (failures=24)
Run 2: 1469 tests — FAILED (failures=6)
Run 3: 1470 tests — FAILED (failures=5)
```

Run 1 exposed one README compatibility regression plus the PF-AUD-013 LF/CRLF exact-byte portability defect affecting P22-06, P22-12, P22-13, P22-14, G22-032, and G22-033 evidence.

Run 2 confirmed the broad Issue #22 fingerprint cluster was removed, while exposing a corpus-wide working-tree rewrite and a platform-native temporary Issue #23 fixture writer.

Run 3 confirmed the Slice-3 portability mechanics: no Issue #22 fixture paths remained modified. Its five failures are entirely historical README exact-string assertions from Issues #12–#16. Slice 4 restores the required phrases as explicitly historical checkpoint language while keeping ADRs 0001–0017 and the current catalog authoritative.

All failed results are retained as audit evidence rather than overwritten or described as a pass.

Historical Issue #22 evidence:

```text
11 / 11 focused closeout tests
356 / 356 Issue #22 regression tests
1451 / 1451 complete schema-validation tests
git diff --check clean
```

These numbers are not inherited as final Issue #23 evidence.

After applying Slice 1, run:

```powershell
python -m unittest discover -s tests\schema_validation -p "test_*.py"
python scripts\validate_portia_foundation.py
git diff --check
```

The Issue #22 regression/corpus suite should also be rerun in its repository-supported form.

## Final verdict

```text
not_ready
```

Reason:

All identified repairable architecture/documentation/checkout-portability blockers are repaired across Slices 1–2, but the audit cannot issue `ready_for_implementation` until the repaired branch passes the complete validation gates and the approval record can bind the exact final audited commit.

If those gates pass without exposing a new blocker, the expected closeout action is narrow:

1. resolve PF-AUD-004;
2. record the observed final test counts;
3. record the exact audited commit;
4. switch the audit verdict to `ready_for_implementation`;
5. add `docs/audits/portia-foundation-approval.json`;
6. rerun the audit validator;
7. confirm `git diff --check`.

No additional domain redesign is currently indicated.
