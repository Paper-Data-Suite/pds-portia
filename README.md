# Portia

Portia is the behavior-support and response module for [Paper Data Suite](https://github.com/Paper-Data-Suite).

Portia is intended to help teachers document behavior-related events, preserve multiple perspectives, coordinate supports and interventions, track follow-up, and evaluate outcomes without reducing students to incident counts or encouraging automatic punitive escalation.

## Current Status

Portia is in its initial research and architecture phase.

The repository currently contains:

* evidence-based research on responsible K–12 behavior documentation and management;
* design analyses defining Portia’s role, identity model, ownership rules, canonical storage, and initial Event and Event Participant domain model;
* foundational Architecture Decision Records establishing Portia’s record distinctions, module boundaries, deployment scope, identity model, storage architecture, and initial Event and Event Participant contracts;
* Draft 2020-12 JSON Schemas for Event and Event Participant records;
* and validated synthetic examples covering digital capture, paper capture, cross-class participation, uncertainty, identity resolution, and supersession.

Portia does not yet contain an executable application. The initial Event and Event Participant domain model is defined, while later records and workflows remain architectural work.

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
* integrated with shared classes and rosters from `pds-core`;
* capable of explicitly linking students from several classes taught by the same teacher;
* and limited to records that can be represented honestly within a teacher-local workspace.

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
* Event Participants;
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
* communications;
* amendments and statements of disagreement;
* explicit relationships among Portia work items;
* a limited teacher-local Actor Directory for recurring non-roster collaborators;
* Portia-specific terminology, privacy classification, and reporting.

### Core Owns

`pds-core` owns shared suite infrastructure such as:

* workspace resolution;
* classes and class metadata;
* rosters;
* student identifiers within their source rosters;
* identifier validation;
* active school-year state;
* standards libraries and profiles;
* module-qualified work identity;
* PDS2 routing;
* retained-source scan provenance;
* shared navigation;
* and safe local path handling.

Core does not own Portia’s behavior categories, support plans, interventions, determinations, reports, Actor records, or retention semantics.

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

## Identity and Storage Model

Portia uses a class-owned workflow model with explicit cross-class references and one limited workspace-scoped Actor Directory.

### Student Identity

A durable Portia student reference consists of:

```text
class_id + student_id
```

The `class_id` identifies the authoritative source roster.

Portia does not assume that:

* a `student_id` is globally unique across the workspace;
* matching IDs in different rosters identify the same student;
* or matching names establish identity.

Historical student references may retain nonauthoritative display snapshots for readability, but names do not function as identifiers.

### Portia Work Identity

One Portia `work_id` identifies one independently managed, explicitly typed top-level workflow object.

The initial work kinds are:

```text
event
support_process
```

Recommended identifier forms are:

```text
evt_<opaque-id>
sup_<opaque-id>
```

Child records such as Event Participants, Accounts, Responses, Follow-Ups, Outcomes, Communications, and work relationships receive their own durable identifiers.

A Portia `work_id` does not represent:

* one student;
* one student dossier;
* one class year;
* one behavior category;
* one printed page;
* or one generated report.

### Canonical Work Storage

Events and Support Processes are stored beneath the Core class-qualified work root:

```text
classes/<class_id>/modules/portia/work/<work_id>/
```

A representative work root is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  work.json
  records/
  attachments/
  pages/
  routes/
  history/
  derived/
  exports/
```

Each canonical record has one authoritative location.

Canonical records are not duplicated into other classes, student folders, histories, dashboards, indexes, or exports merely to support navigation.

### Event Ownership

Every Event has exactly one owning class.

Ownership normally follows the Event’s temporal and instructional context.

When an Event occurs during a scheduled class period, the class being taught at that time is the presumptive owner.

The owning class establishes:

* canonical storage;
* the Core work reference;
* the PDS2 routing context;
* and the primary instructional context.

An Event may nevertheless include students from other valid rosters in the same teacher’s workspace.

Cross-class participants do not transfer or divide ownership.

### Cross-Class Participants

Students from another class taught by the same teacher may be linked explicitly through complete roster-qualified references.

For example:

```text
Owning class:
english10_p2

Participants:
english10_p2 + 1001
english10_p2 + 1014
english10_p5 + 2047
```

The Event remains stored only beneath the owning class.

Portia must not:

* duplicate the Event beneath another class;
* create synthetic roster entries;
* select an arbitrary primary student;
* or merge students automatically across rosters.

### Recurring Non-Roster Actors

Recurring non-roster people may receive opaque Portia Actor identifiers.

Examples include:

* parents and guardians;
* counselors;
* administrators;
* case managers;
* paraprofessionals;
* psychologists;
* social workers;
* nurses;
* coaches;
* and other recurring collaborators.

Actor records are stored in a limited workspace-scoped directory:

```text
<PDS workspace>/
  portia/
    actors/
      <actor_id>.json
```

The Actor Directory is local to one teacher’s workspace.

It is not a school directory, district directory, student-information system, authenticated user directory, or institutionally authoritative identity service.

Roster students continue to use Core roster-qualified references and are not duplicated as Actor records.

Incidental, unidentified, or one-time people may remain descriptive without receiving Actor IDs.

### Relationships and Derived Views

Each Portia relationship has one canonical record.

Reverse links, student histories, timelines, dashboards, work queues, reports, and indexes are derived views.

Portia does not maintain an authoritative student dossier.

Derived data must be:

* nonauthoritative;
* rebuildable;
* and replaceable from canonical records.

A missing or corrupt derived index must not invalidate otherwise valid Portia work.

### Cross-Year Continuity

Events retain their original class, occurrence time, and school-year context.

A Support Process continuing into a new school year should normally receive a successor work item under the new legitimate owning class.

The predecessor and successor are linked explicitly.

Portia represents longitudinal continuity through linked records rather than one indefinitely mutable student dossier.

### Core Impact

No blocking `pds-core` change is required for Portia v1.

Portia will use existing Core class, roster, work-path, and routing contracts while implementing its own:

* Event and Support Process identifiers;
* child-record identifiers;
* Actor identifiers;
* canonical schemas;
* cross-class participant lookup;
* work relationships;
* Actor Directory paths;
* append-oriented history;
* derived indexes;
* and recovery diagnostics.

A broader Core workspace-module path should be considered only if several Paper Data Suite modules independently require one.

## Initial Event and Event Participant Model

Portia now defines an initial canonical model for Events and Event Participants.

### Event Meaning

One Event represents one coherent, time-bounded occurrence, interaction, observation period, or reported occurrence.

An Event may represent:

* one instantaneous occurrence;
* one connected interaction;
* a short sequence of related actions;
* a defined observation period;
* or an occurrence reported after it happened.

An Event must not become:

* a permanent student narrative;
* a general pattern record;
* an ongoing Support Process;
* an unattributed Account;
* or a container for every later development involving the same participant.

Positive, neutral, and concerning Events are all first-class.

### Event Root

Each Event is stored at:

```text
classes/<class_id>/modules/portia/work/<event_id>/work.json
```

The Event root stores shared Event context such as:

* owning class and school year;
* current lifecycle status;
* occurrence precision;
* concise neutral summary;
* optional location;
* optional instructional context;
* creation source;
* local creation and update attribution;
* and canonical supersession relationships.

Participant-specific identity, roles, Accounts, judgments, Responses, Follow-Ups, and Outcomes remain separate records.

### Event Occurrence

Occurrence uses one explicit precision variant:

```text
exact
approximate
date_only
range
unknown
```

Portia must preserve uncertainty honestly and must not fabricate occurrence time from record creation, scan return, file modification, default midnight values, or unconfirmed schedule inference.

### Event Participants

Event Participants are stored separately at:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/event_participant/<participant_id>.json
```

Supported participant subject types are:

```text
roster_student
actor
descriptive_person
unknown_person
```

An active Event requires at least one active Event Participant, but it does not specifically require a roster student.

Roster students use complete roster-qualified identity:

```text
class_id + student_id
```

An Event Participant’s identity remains separate from the person’s Event-level role.

Participant roles will be separate canonical records rather than embedded role fields.

### Lifecycle

Event statuses are:

```text
draft
active
closed
cancelled
invalidated
superseded
```

Event Participant statuses are:

```text
proposed
active
invalidated
superseded
```

Corrections preserve history.

A proposed participant may become active in place when the teacher confirms the same identity.

A material identity correction creates a replacement participant that canonically supersedes the prior record.

Cancelled, invalidated, and superseded records remain preserved rather than being silently deleted or rewritten.

### Paper and Digital Capture

Paper and digital workflows converge on the same canonical Event and Event Participant schemas.

Paper capture uses:

```text
creation_source.type = paper_capture
```

with one stage:

```text
preallocated
ingested
```

A preallocated paper Event begins as a draft before printing.

Returned-page interpretation may create proposed participants or other proposed records, but scanning or automated recognition never constitutes teacher confirmation.

Routine teacher-facing actions should remain concise, such as:

```text
Confirm
Correct
Dismiss
Activate
Close
```

Internal lifecycle, provenance, and supersession operations should be generated automatically.

### Validation Boundary

The Event and Event Participant schemas use JSON Schema Draft 2020-12.

JSON Schema validates local record shape, including discriminated unions, constants, enums, identifier formats, timestamp syntax, and rejection of unknown properties.

Application validation remains responsible for cross-record and contextual invariants such as:

* path and persisted identity agreement;
* owning-class and school-year validity;
* roster and Actor reference validity;
* route and page-record existence;
* timestamp chronology;
* lifecycle-transition legality;
* Event activation requiring an active participant;
* duplicate participant detection;
* replacement ordering;
* and supersession consistency.

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

* [Portia Identity, Ownership, and Storage](docs/design/portia-identity-and-storage.md)

  Defines Portia’s required identity layers, work identity, canonical workspace layout, Event ownership, cross-class participants, recurring non-roster Actors, relationship ownership, derived views, representable cases, and Core implications.

* [Portia Event and Event Participant Domain Model](docs/design/portia-event-and-participant-domain-model.md)

  Defines Event meaning and boundaries, Event root fields, occurrence precision, location and instructional context, participant identity variants, participant roles, lifecycle transitions, correction and supersession, creation source, local provenance, paper capture, validation boundaries, and teacher-workflow constraints.

### Schemas

* [Event Schema](schemas/event.schema.json)

  Draft 2020-12 JSON Schema for canonical Event `work.json` records.

* [Event Participant Schema](schemas/event-participant.schema.json)

  Draft 2020-12 JSON Schema for canonical Event Participant records.

### Examples

* [Portia Event and Event Participant Examples](docs/examples/portia-event-and-participant-examples.md)

  Validated synthetic examples covering digital entry, paper preallocation and confirmation, cross-class participation, unresolved identity, participant identity resolution, and Event supersession.

### Architecture Decisions

* [ADR 0001: Separate Observations, Interpretations, Classifications, and Determinations](docs/decisions/0001-separate-observations-interpretations-and-determinations.md)

  Establishes distinct linked records for Events, Accounts, Classifications, Hypotheses, Determinations, Responses, Supports, and Outcomes.

* [ADR 0002: Define Portia’s Role and Module Boundaries](docs/decisions/0002-define-portia-module-boundaries.md)

  Establishes Portia as a peer Paper Data Suite domain module, defines ownership boundaries, and governs cross-module relationships.

* [ADR 0003: Adopt a Teacher-Local Initial Deployment for Portia](docs/decisions/0003-adopt-teacher-local-initial-deployment.md)

  Establishes a local-first, teacher-controlled, classroom-focused initial implementation while deferring institution-wide platform requirements.

* [ADR 0004: Define Portia Identity, Ownership, and Storage](docs/decisions/0004-define-portia-identity-ownership-and-storage.md)

  Establishes roster-qualified student identity, typed Event and Support Process work items, temporal and instructional class ownership, cross-class participants, the workspace-scoped Actor Directory, canonical relationship ownership, derived indexes, cross-year continuity, and the absence of blocking Core changes.

* [ADR 0005: Define the Initial Event and Event Participant Domain Model](docs/decisions/0005-define-event-and-participant-domain-model.md)

  Establishes bounded Events, separate Event Participant records, explicit occurrence precision, participant subject variants, separate participant roles, Event and participant lifecycles, provenance, paper capture, correction and supersession, validation boundaries, and the requirement that internal rigor not become routine teacher workload.

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

Portia must also not:

* fabricate students or classes;
* merge students automatically across rosters;
* duplicate canonical Events across classes;
* present local Actor records as an institutional directory;
* or represent teacher-local records as schoolwide disciplinary authority.

## Student Data

Real student data must not be committed to this repository.

Development examples, fixtures, screenshots, exports, and tests should use synthetic:

* students;
* classes;
* Events;
* Accounts;
* interventions;
* family communications;
* Actors;
* and outcomes.

Local-first storage does not make student records inherently non-sensitive. Portia workspace data, exports, synchronized folders, and backups must be handled according to applicable school, district, state, and federal requirements.

## Next Architecture Work

Likely next work includes:

* defining the Event Participant Role schema and lifecycle;
* defining Event and Event Participant lifecycle-transition schemas;
* defining the initial Support Process schema;
* defining Account, Observation, Classification, Hypothesis, Determination, Response, Follow-Up, Outcome, and Communication schemas;
* defining the Actor Directory schema and Actor lifecycle;
* defining participant-targeting contracts for later records;
* specifying general amendment, correction, and owning-class migration behavior;
* defining staged-write, atomic-replacement, rollback, validation, and recovery behavior;
* defining how teacher schedules assist Event ownership selection;
* implementing and performance-testing the minimum viable teacher workflow;
* establishing privacy projections and redaction for multi-student Events;
* defining deliberate student-specific exports;
* specifying PDS2 page-record and route schemas;
* evaluating a capture-batch routing contract for multi-entry paper sheets;
* specifying typed cross-module references;
* defining cross-year Support successor workflows;
* and defining Portia archival integration with Sunset.

## License

Licensing information will be documented before an initial software release.
