# Portia v0.2.0 Release Notes

Status: **release candidate; publication pending Issue #54 Phase 2 verification**

Portia v0.2.0 is the first executable release line for Portia, Paper Data Suite's
teacher-local behavior-support, response, support, and follow-up module. These
notes describe the v0.2.0 candidate scope. They do not claim that publication,
tagging, fresh-download verification, or the final `RELEASED — VERIFIED` gate has
already occurred.

## Runtime and compatibility

- Python >=3.11.
- Runtime dependency: `pds-core>=0.6.3,<0.7`.
- Current final qualification authority is the exact released Core 0.6.4 wheel.
- Frozen historical installed-wheel compatibility checks retain the exact released
  Core 0.6.3 wheel.
- No sibling PDS runtime dependency is required.
- Console entry point: `portia = portia.cli:main`.
- Core module-operations entry point:
  `portia = portia.pds_operations:get_module_operations_profile`.
- No publication-producer capability is advertised in v0.2.0.

## What v0.2.0 provides

Portia v0.2.0 provides a local-first, teacher-local executable workflow covering:

- Core class/roster identity plus Portia's separate Actor Directory;
- Event, participant, role, relationship, Account, and Observation records;
- Review, Classification, Hypothesis, and bounded Determination records;
- Response and Communication records without inferring effectiveness, delivery,
  understanding, agreement, or truth;
- Support Process, Need, Goal, Support, Implementation, and Fidelity records;
- Follow-Up, Outcome, Reentry, and Repair records with distinct semantics;
- guarded canonical persistence, correction/history, Quarantine, Integrity, and
  evidence-preserving recovery;
- privacy-minimized Timeline and Attention surfaces;
- task-oriented teacher menus with explicit preview/confirmation boundaries;
- deliberate local Teacher Reference export with closed privacy projection,
  manual include-exact/omit review, exact preview, confirmation, immutable history,
  and recovery;
- Core readiness/attention module-operations providers;
- bounded generated paths and deep-workspace qualification; and
- installed-wheel acceptance in an isolated Core+Portia environment.

## Privacy, authority, and records boundaries

Portia remains teacher-local. A teacher-local record is not silently upgraded into
district, institutional, legal, clinical, disciplinary, or safeguarding authority.

A Teacher Reference export is a local derived artifact, not an official institutional record.
Generating one does not establish disclosure, delivery, receipt, filing,
requester entitlement, or authorization to disclose.

Portia defines semantic retention classes and local hooks, but it does not define legal retention periods.
It does not decide legal holds, approve destruction, authenticate requesters, or
prove that deleting a local copy removed backups, synchronized copies,
sibling-module records, or external custody.

Portia v0.2.0 is not a schoolwide discipline system, institutional case-management
platform, student-information system, IEP/clinical system of record, threat-
assessment platform, mandated-reporting platform, or multi-user administrative
system.

The release is not a FERPA, COPPA, GDPR, HIPAA, state-law, records-management,
accessibility, collective-agreement, or district-policy certification.

## Packaging boundary

The wheel is runtime-only: Portia Python modules, typing marker, runtime coverage,
and the compiled runtime contract bundle. Raw repository schemas, tests, scripts,
and documentation are not runtime-wheel content.

The source distribution retains the auditable source materials, including
documentation, raw schemas, validation scripts/tests, security policy, changelog,
and these release notes.

## Deliberately deferred beyond v0.2.0

v0.2.0 does not claim:

- future privacy-minimized Core intervention publication;
- future Suite-wide retention/disposition orchestration such as a Sunset-like
  module;
- paper/import operationalization beyond the v0.2.0 digital/local runtime;
- cross-year Support successor workflow;
- or institution-wide identity, authorization, concurrency, records administration,
  and tenant governance.

## Release verification

Issue #54 remains open until exact release artifacts are built and qualified,
their hashes are recorded, the release commit/tag is fixed, publication occurs,
and freshly downloaded artifacts are independently verified.

Only after those steps may the release audit use the final verdict
`RELEASED — VERIFIED`.
