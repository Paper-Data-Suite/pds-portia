# Portia v0.2.0 Release Audit

## Status

Issue #54 is the final ethical, privacy, architecture, usability, package, and release gate for Portia v0.2.0.

Phase: **Phase 1 — audit and release preparation**  
Final verdict: **PENDING**

`RELEASED — VERIFIED` is not available until publication and fresh-download verification are complete.

## Starting authority

The audit begins from the reconciled Issue #53 handoff:

```text
Portia commit:
d2cca3b7d8eb59087016d4da60e623960758a729

Portia tree:
33067ffdd35047d2c6ac575cc7d21969c2a3862b
```

Before Slice 1 changed repository bytes, the applying operator ran the complete authoritative Issue #53 repository validator against that exact commit/tree and obtained:

```text
Portia Issue #53 repository qualification passed
```

Captured baseline execution:

```text
captured at UTC: 2026-10-06T23:47:24+00:00
Python:          3.11.9
host platform:   Windows-10-10.0.26200-SP0
```

The baseline evidence is deliberately pre-change evidence. Later Issue #54 qualification must validate the release-preparation state independently.

## Exact Core qualification authority

Current release qualification uses the exact released Core 0.6.4 artifact:

```text
pds_core-0.6.4-py3-none-any.whl
SHA-256: 48cea9317f2967bdc0f2d4c14349a56677c7c3f8211f0f33978ccb1a1c75859b
release source: 152d1c65064c4f8fe55249ff2ca3379d7c4d6ccb
```

Historical compatibility evidence retains the exact released Core 0.6.3 artifact:

```text
pds_core-0.6.3-py3-none-any.whl
SHA-256: 98d7596ce0eed26e4d56a17bbbbd644db3014259b56a45783a173fe8237af5e5
```

These facts remain distinct:

```text
minimum supported Core: pds-core>=0.6.3,<0.7
current final qualification authority: exact Core 0.6.4 release artifact
```

## Release contract frozen for audit

Slice 1 mechanically protects the following candidate identity:

```text
distribution: pds-portia
version: 0.2.0
Requires-Python: >=3.11
runtime Core: pds-core>=0.6.3,<0.7
console script: portia = portia.cli:main
module operations: portia = portia.pds_operations:get_module_operations_profile
sibling PDS runtime dependency: none
publication-producer capability: none
```

This is an audit boundary, not release approval.

## Audit domains

The machine-readable audit state keeps the following domains explicitly pending until evidence is reviewed:

1. ethical neutrality and epistemic distinctions;
2. teacher-local authority;
3. sensitive-data minimization and privacy;
4. record distinction and identity;
5. architecture and ownership;
6. storage, path, history, and compatibility;
7. recovery, failure, and Integrity behavior;
8. teacher usability and workload;
9. menu and terminology;
10. read-only surfaces;
11. packaging and public surfaces;
12. documentation reconciliation;
13. release contract and mechanical qualification;
14. cumulative repository qualification;
15. Python/platform qualification.

A pending domain is not a pass and is not a defect classification. Concrete defects discovered during review are recorded separately in the findings register.

## Foundation-audit handoff

The release audit explicitly reopens the implementation questions inherited from the foundation audit without rewriting their historical disposition. The machine-readable state carries PF-AUD-005 through PF-AUD-012 as re-audit obligations, including:

- append-preserving recovery;
- privacy-safe teacher review workload;
- production application validation;
- institutional policy dependencies;
- unimplemented future retention/publication capabilities;
- reconciliation of the historical no-runtime scope boundary;
- legal/regulatory non-certification.

Historical Issue #23 evidence remains historical evidence.

## Finding model

Concrete Issue #54 findings use IDs of the form `P54-AUD-###` and preserve, at minimum:

```text
finding ID
audit domain
classification
summary
exact evidence
affected files/contracts
expected behavior
observed problem
risk/consequence
required disposition
resolution
validation evidence
follow-up issue if any
status
```

Allowed classifications are:

```text
BLOCKER
MAJOR
MINOR
ACCEPTED LIMITATION
DEFERRED / FUTURE
```

Release preparation cannot finish with an unresolved BLOCKER or MAJOR finding.

## Legal and authority boundary

Portia v0.2.0 release approval is not FERPA certification, state-law certification, district-policy approval, clinical approval, special-education compliance certification, legal advice, records-management certification, or institutional authorization to use Portia for regulated case management.

Portia remains teacher-local. A recorded teacher decision is not silently upgraded into an institutional, district, legal, clinical, or disciplinary decision.

## Synthetic-data boundary

Issue #54 qualification uses synthetic evidence only. It must never be run against or populated from a real teacher workspace.

## Slice 1 conclusion

Slice 1 creates durable audit state and a focused mechanical validator. It intentionally makes no production runtime changes and records no substantive audit-domain PASS result yet.

Final verdict: **PENDING**

## Slice 2 — Ethical neutrality and epistemic distinctions

Domain result: **PASS**

Slice 2 reviewed the accepted semantic authority in ADRs 0011–0015 together with the corresponding executable workflow and teacher-facing surfaces. The audit specifically checked the release-gate distinctions across:

```text
Account != Observation
Review != Classification != Hypothesis != Determination
Response recorded != effective Response
Communication act/attempt != delivery != reading != understanding != agreement
Need != diagnosis
Goal != achieved Outcome
Support/Intervention plan != Implementation
Implementation != Fidelity
Fidelity != Outcome/effectiveness
Follow-Up completion != success/resolution/effectiveness/Outcome
attention count/order != severity/risk/urgency/priority/recommendation
```

Reviewed authority and implementation evidence includes:

```text
docs/decisions/0011-define-account-and-observation-domain-models.md
docs/decisions/0012-define-review-classification-hypothesis-and-determination-domain-models.md
docs/decisions/0013-define-response-and-communication-domain-models.md
docs/decisions/0014-define-support-process-support-intervention-implementation-and-fidelity-contracts.md
docs/decisions/0015-define-follow-up-outcome-reentry-and-repair-domain-models.md
portia/menu/judgment.py
portia/menu/response_communication.py
portia/menu/support.py
portia/menu/support_delivery.py
portia/menu/follow_up.py
portia/attention/taxonomy.py
portia/menu/attention.py
portia/workflows/responses.py
portia/workflows/support_needs.py
portia/workflows/support_goals.py
```

The executable surfaces preserve explicit human selection/attribution and do not silently promote one semantic stage into a later stage. The judgment menu writes only the record family explicitly selected by the teacher. Response and Communication wording separates action/communication facts from effectiveness, receipt, understanding, and agreement. Support planning separates Need/Goal from diagnosis, eligibility, attainment, and Outcome. Implementation and Fidelity remain separate from effectiveness and Outcome. Follow-Up completion remains a bounded workflow fact. Native attention is defined as workflow/recovery/integrity state with deterministic presentation order rather than a student score, severity/risk measure, urgency ranking, priority ranking, or recommendation system.

The review found no evidence in these audited surfaces of automatic misconduct adjudication, culpability inference, truthfulness inference, intent inference, dangerousness/risk scoring, diagnosis, intervention selection, effectiveness inference, Outcome inference, or institutional discipline generation.

No `P54-AUD-*` defect was identified in this domain.

No production runtime code changed in Slice 2. The new focused validator protects the accepted semantic markers and the one-record-at-a-time judgment menu behavior against release-preparation drift.

Final verdict remains **PENDING** because the remaining Issue #54 audit domains, cumulative qualification, artifact freeze, publication, and fresh-download verification are not complete.

## Slice 3 — Teacher-local authority and external authority boundaries

Domain result: **PASS**

Slice 3 reviewed Portia's authority boundaries across accepted architecture, production validation, teacher-facing language, deliberate export, external policy dependencies, and the Core/Suite integration surface.

The reviewed authority model preserves:

```text
teacher-local decision != institutional decision
represented human identity != authenticated authority
Actor relationship != legal guardianship or institutional authority
recorded institutional provenance != PDS authentication of authority
policy/process source reference != proof of applicability or correct application
teacher-reference export generation != disclosure/delivery/official institutional filing
projection scope != recipient entitlement or disclosure authorization
retention class != retention duration
retention eligibility != destruction authorization
Portia/Core local evidence != legal-hold adjudication
Core/Suite discovery/readiness/attention != permission to reinterpret or mutate Portia domain state
```

Reviewed authority and implementation evidence includes:

```text
docs/decisions/0010-define-actor-directory-domain-model-and-lifecycle.md
docs/decisions/0012-define-review-classification-hypothesis-and-determination-domain-models.md
docs/decisions/0017-define-privacy-projections-redaction-export-retention-and-sunset-boundaries.md
portia/workflows/determinations.py
portia/workflows/response_common.py
portia/menu/judgment.py
portia/exports/preparation.py
portia/pds_operations.py
portia/attention_provider.py
portia/readiness_provider.py
SECURITY.md
tests/test_workflow_determinations.py
tests/test_workflow_response_decision_context.py
tests/test_identity_actors.py
tests/test_teacher_reference_export_preparation.py
tests/test_issue52_operations_profile.py
tests/test_issue52_attention_provider.py
tests/test_issue52_readiness_provider.py
```

Production Determination validation requires teacher-local decisions to use a local-operator decision-maker. Recorded-institutional records preserve a separate authority context and may retain asserted, documented, or historically unknown authority provenance without claiming that PDS authenticated the person or proved the authority legally sufficient. An active representation of an unidentified historical institutional decision remains an uncertain historical representation; it does not authenticate current institutional authority.

Actor-to-student relationships remain explicit teacher-local assertions with provenance and lifecycle. A parent/guardian/counselor/administrator relationship label does not independently prove legal or institutional authority and does not propagate automatically across rosters.

Recorded-institutional Response consequence context remains coupled to an exact Determination and an eligible represented provider. The routine teacher judgment menu authors teacher-local Determinations and explicitly labels local-operator identity as provenance rather than authentication.

Teacher-reference export remains deliberately local and warns that the generated artifact is neither a disclosure nor an official institutional record. Participant-specific scope does not establish recipient or disclosure authorization.

ADR 0017 continues to leave requester entitlement, retention durations, legal/preservation holds, disclosure authority, and destruction authorization with institution/deployment authority. Portia does not claim current Suite-wide retention orchestration. The installed Core module-operations profile remains bounded to readiness and attention providers and does not expose mutation, disclosure, discipline, retention, or domain-adjudication authority.

The Security policy and this release audit continue to state that Portia is not a compliance certification or substitute for approved institutional/legal processes.

PF-AUD-008 and PF-AUD-012 are reconciled by this slice. Their historical foundation-audit dispositions are not rewritten; the release-audit state records that the executable v0.2.0 implementation still preserves the required external-policy and legal-noncertification boundaries.

No `P54-AUD-*` defect was identified in this domain.

No production runtime code changed in Slice 3. The focused authority validator protects the audited boundaries against release-preparation drift.

Final verdict remains **PENDING** because the remaining Issue #54 audit domains, cumulative qualification, artifact freeze, publication, and fresh-download verification are not complete.
