# Portia

Portia is the behavior-support and response module for [Paper Data Suite](https://github.com/Paper-Data-Suite).

Portia is intended to help teachers document behavior-related events, preserve multiple perspectives, coordinate supports and interventions, track follow-up, and evaluate outcomes without reducing students to incident counts or encouraging automatic punitive escalation.

## Current Status

Portia is in its initial research and architecture phase.

The repository currently contains:

* evidence-based research on responsible K–12 behavior documentation and management;
* a design analysis defining Portia’s role within Paper Data Suite;
* foundational Architecture Decision Records establishing Portia’s record distinctions, module boundaries, and initial deployment scope.

Portia does not yet contain an executable application or a finalized data model.

## Product Position

Portia is designed as:

> **Paper Data Suite’s contextual behavior-support and response module. It records what was observed, who provided each account, what an authorized person or institution determined, what response or support was provided, and what happened afterward.**

Portia should function as a student-support and decision-documentation system, not as a digital punishment ledger.

The recommended conceptual workflow is:

```text
Event
→ Accounts and Observations
→ Review and Classification
→ Determination
→ Immediate Responses
→ Supports and Interventions
→ Follow-Up and Outcomes
```

These stages represent distinct records and forms of human judgment. A reported concern is not automatically a confirmed finding, a hypothesis is not a fact, and a response or consequence does not define what occurred.

## Initial Deployment Scope

The first Portia implementation will be:

* local-first;
* teacher-controlled;
* classroom-focused;
* built on the existing Paper Data Suite workspace;
* integrated with shared classes and rosters from `pds-core`.

The initial release will not claim to be:

* a schoolwide discipline system;
* an institutional case-management platform;
* a student-information system;
* an IEP or clinical system of record;
* a threat-assessment or mandated-reporting platform;
* a student or family portal;
* or a multi-user administrative application.

Institution-wide identity, authentication, authorization, audit, concurrency, records administration, and tenant governance remain future platform concerns.

## Paper Data Suite Boundaries

Portia is a peer domain module built on shared infrastructure from `pds-core`.

The intended dependency direction is:

```text
pds-portia -> pds-core
```

### Portia Owns

Portia owns behavior-support concepts and workflows such as:

* Events;
* Accounts and Observations;
* Positive Observations;
* Concerns and Referrals;
* Classifications;
* Hypotheses;
* authorized Determinations;
* Immediate Responses;
* Supports and Interventions;
* implementation and fidelity records;
* Follow-Ups and Outcomes;
* Reentry and Repair;
* student and family statements;
* amendments and statements of disagreement;
* Portia-specific terminology, privacy classification, and reporting.

### Core Owns

`pds-core` owns shared suite infrastructure such as:

* workspace resolution;
* classes and rosters;
* shared student identifiers;
* identifier validation;
* active school-year state;
* standards libraries and profiles;
* module-qualified work identity;
* PDS2 routing;
* retained-source scan provenance;
* shared navigation;
* and safe local path handling.

Core does not own Portia’s behavior categories, support plans, interventions, determinations, reports, or retention semantics.

### Sibling Modules

Portia does not duplicate sibling-module workflows:

* `pds-scoreform` owns optical-mark recognition and selected-response processing.
* `pds-quillan` owns written-response review and feedback workflows.
* `pds-concord` owns collaborative Activities, Groups, Artifacts, evidence Review and Moderation, and collaborative Scoring.
* a future grading and reporting module will own academic grade calculation and formal academic reporting;
* a future portfolio module will own student-work curation and presentation;
* a future planning module will own Units, Lessons, Assignments, objectives, and instructional sequencing;
* `pds-sunset` will own suite-wide archival orchestration.

Portia may reference records from other modules through durable, typed, module-qualified references. The originating module remains authoritative for its record.

Portia records must not automatically:

* become academic Scores or Grades;
* alter ScoreForm, Quillan, or Concord judgments;
* enter a student portfolio;
* change instructional plans;
* or trigger archival or destruction in another module.

## Design Principles

Portia development should preserve the following principles:

### Support-oriented

Portia should connect documentation to prevention, instruction, support, follow-up, and outcomes rather than merely counting incidents.

### Objective and attributable

Records should describe observable actions and relevant context. Each Account should retain its author and source status.

### Multiple-perspective

Conflicting or incomplete Accounts may coexist. Portia should not force one canonical narrative before appropriate review.

### Human-reviewed

Portia should preserve human responsibility for classifications, determinations, intervention decisions, and outcomes.

It should not infer:

* intent;
* remorse;
* honesty;
* diagnosis;
* trauma;
* behavioral function;
* or future risk.

### Privacy-conscious

Portia should minimize sensitive collection, preserve correction history, support deliberate exports, and avoid representing local filesystem access as formal institutional authorization.

### Equity-aware

Portia should expose data quality, denominators, missingness, and institutional decision points without creating student behavior Scores or predictive disciplinary profiles.

### Source-preserving

Original Accounts and historical values should remain auditable while inaccurate active records can be corrected through explicit amendment and supersession workflows.

### Modular

Portia should use Core infrastructure and public cross-module contracts rather than duplicating shared behavior or importing private sibling-module implementation code.

## Documentation

### Research

* [Best Practices for Tracking and Managing Student Behavior](docs/research/student-behavior-tracking-best-practices.md)

  Research into behavior documentation, intervention frameworks, equity, privacy, student and family participation, workflow design, accessibility, reporting, and ethical safeguards.

### Design

* [Portia’s Role Within Paper Data Suite](docs/design/portia-role-within-paper-data-suite.md)

  Analysis of the current Paper Data Suite modules, their workflows, Portia’s suite role, future-module relationships, deployment implications, and unresolved architectural questions.

### Architecture Decisions

* [ADR 0001: Separate Observations, Interpretations, Classifications, and Determinations](docs/decisions/0001-separate-observations-interpretations-and-determinations.md)

  Establishes distinct linked records for Events, Accounts, Classifications, Hypotheses, Determinations, Responses, Supports, and Outcomes.

* [ADR 0002: Define Portia’s Role and Module Boundaries](docs/decisions/0002-define-portia-module-boundaries.md)

  Establishes Portia as a peer Paper Data Suite domain module, defines ownership boundaries, and governs cross-module relationships.

* [ADR 0003: Adopt a Teacher-Local Initial Deployment for Portia](docs/decisions/0003-adopt-teacher-local-initial-deployment.md)

  Establishes a local-first, teacher-controlled, classroom-focused initial implementation while deferring institution-wide platform requirements.

## Explicit Product Prohibitions

Portia must not provide:

* a public student behavior leaderboard;
* a single behavior, character, or compliance Score;
* predictive discipline, violence, or recidivism scoring;
* automated punishment recommendations;
* automatic escalation based only on record count;
* emotion, deception, remorse, or intent inference;
* diagnostic or trauma inference;
* facial recognition;
* passive audio surveillance;
* social-media scraping;
* or indefinite retention by default.

## Student Data

Real student data must not be committed to this repository.

Development examples, fixtures, screenshots, exports, and tests should use synthetic:

* students;
* classes;
* Events;
* Accounts;
* interventions;
* family communications;
* and outcomes.

Local-first storage does not make student records inherently non-sensitive. Portia workspace data, exports, synchronized folders, and backups must be handled according to applicable school, district, state, and federal requirements.

## Next Architecture Work

Likely next work includes:

* defining class-scoped, cross-class, and organization-scoped identity;
* selecting the canonical Portia storage model;
* defining the initial Portia domain model;
* specifying typed cross-module references;
* defining the minimum viable teacher workflow;
* establishing local privacy, change-history, export, and redaction behavior;
* defining Portia archival integration with Sunset;
* and determining whether Portia’s initial release needs any paper-generation or PDS2 routing workflow.

## License

Licensing information will be documented before an initial software release.
