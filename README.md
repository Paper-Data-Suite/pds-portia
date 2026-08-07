# Portia

Portia is the behavior-support and response module for [Paper Data Suite](https://github.com/Paper-Data-Suite).

Portia is intended to help teachers document behavior-related events, preserve multiple perspectives, coordinate supports and interventions, track follow-up, and evaluate outcomes without reducing students to incident counts or encouraging automatic punitive escalation.

## Current Status

Portia is in its initial research and architecture phase.

The repository currently contains:

* evidence-based research on responsible K–12 behavior documentation and management;
* accepted design analyses defining Portia’s role, identity model, ownership rules, canonical storage, references, lifecycle, correction, migration, removal, integrity diagnostics, coordinated persistence, recovery, Quarantine, finding administration, derived rebuilding, the initial Event family, the teacher-local Actor Directory, and the Account/Observation source-evidence layer;
* Architecture Decision Records through ADR 0009, plus accepted ADR 0010 for the Actor Directory and ADR 0011 for Accounts and Observations;
* independently versioned Draft 2020-12 identifier, reference, target, Actor, Account, Observation, attribution, provenance, lifecycle, correction, disagreement, dependency, migration, ownership-correction, removal, relationship, operational, and derived-projection schemas;
* retained historical Event-family version-1 schemas, Event version 2, Event Participant and Role version 3, Work Relationship version 2, Actor Directory version-1 contracts, Account and Observation version-1 contracts, and Actor-aware operational version-2 contracts;
* validated synthetic examples, migration fixtures, and comprehensive Issue #12, Issue #13, Issue #14, and Issue #15 application-invalid matrices;
* and automated offline schema-validation, state-machine, compatibility, privacy, example, and documentation-consistency tests.

Portia does not yet contain an executable application. The current domain implementation targets are Event v2, Event Participant v3, Event Participant Role v3, Work Relationship v2, the Actor Directory version-1 record family, Account v1, and Observation v1. Issue #14 completes the public teacher-local Actor identity family. Issue #15 completes attributed Account and direct/instrumented Observation identity, targeting, attribution, provenance, lifecycle, correction, retraction, migration/removal compatibility, operational/derived reuse, and privacy contracts. Production filesystem services and teacher-facing workflows remain assigned to a later executable milestone.

## Product Position

Portia is designed as:

> **Paper Data Suite’s contextual behavior-support and response module. It records what was observed, who said what, what the institution decided, what support was provided, and what happened afterward. It may reference instructional and assessment context from other modules, but it neither evaluates academic work nor calculates grades.**

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
* Event Participant Roles;
* Accounts and Observations, including positive, neutral, and potentially concerning observable information through one neutral Observation model;
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
* `pds-meridian` owns academic evidence policy, proficiency, Grade calculation, and formal academic reporting;
* `pds-vitrine` owns student-work curation, portfolio composition, presentation, and regulated portfolio workflows;
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

Child records such as Event Participants, Event Participant Roles, Accounts, Observations, Responses, Follow-Ups, Outcomes, Communications, and work relationships receive their own durable identifiers.

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
      <actor_id>/
        actor.json
        records/
          actor_contact_point/
          actor_student_relationship/
          actor_roster_student_collision/
          actor_directory_lifecycle_transition/
          actor_directory_lifecycle_history_correction/
          actor_directory_amendment/
          actor_directory_record_migration/
```

The canonical root record is `portia/actors/<actor_id>/actor.json`.

Exceptional-removal certificates survive outside Actor roots:

```text
<PDS workspace>/portia/actor-directory-removals/<removal_id>.json
```

One Actor represents one recurring non-roster human person. Contact Points and Actor-to-Student Relationships are separate canonical child records; work-specific roles remain on their containing records.

The Actor Directory is local to one teacher’s workspace. It is not a school directory, district directory, student-information system, employee directory, authenticated user directory, legal guardianship registry, contact-management platform, or institutionally authoritative identity service.

Roster students continue to use exact Core roster-qualified references and are never duplicated as Actors. A reviewed Actor–Roster Student Collision invalidates the Actor without converting its Contact Points into roster data or creating a workspace-wide student identity.

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
* Account and Observation identifiers;
* canonical schemas;
* cross-class participant lookup;
* work relationships;
* Actor Directory paths;
* append-oriented history;
* derived indexes;
* and recovery diagnostics.

A broader Core workspace-module path should be considered only if several Paper Data Suite modules independently require one.

## Accepted Shared Reference and Relationship Contracts

ADR 0007 defines a small family of scope-specific public contracts rather than one universal reference object.

The initial families are:

```text
roster_student_ref
actor_ref
local_record_ref
portia_work_ref
portia_work_record_ref
module_work_record_ref
person_display_snapshot
portia_target_ref
support_process_target_ref
work_relationship
```

References resolve exactly. Portia does not repair references through name matching, search other work roots for bare IDs, infer the newest contract version, or silently follow supersession.

Cross-module references compose Core work and record identity while leaving the originating module authoritative. Historical display snapshots remain outside identity.

Work Relationships have one canonical source-owned direction. Reverse views are derived. The initial type `draws_context_from` is contextual and noncausal.

Historical Event-family version-1 schemas remain readable. Event v2, Event Participant v3, Event Participant Role v3, and Work Relationship v2 are the current implementation targets.

## Accepted Lifecycle, Correction, and Migration Contracts

ADR 0008 establishes shared infrastructure without imposing one universal state machine.

The principal public contracts are:

```text
lifecycle_transition
lifecycle_history_correction
amendment
statement_of_disagreement
dependency
record_migration
ownership_correction
exceptional_removal
integrity_finding
```

Current status remains practical to load directly, while append-only transition records preserve history. A status/history mismatch is an integrity finding rather than an invitation to silently rewrite either source.

Nonmaterial amendments preserve explicit before-and-after values. Material correction creates a successor. Invalidation differs from supersession, disagreement does not rewrite its target, migration preserves meaning and logical identity, and ownership correction is not filesystem relocation.

Dependencies require explicit record-family evaluation and never create one automatic cascade. Exact references do not silently follow successors or retarget after migration, consolidation, ownership correction, or removal.

Ordinary workflows do not hard-delete accepted canonical records. Narrow exceptional cases retain an authorization-bearing removal certificate and minimal content evidence without retaining prohibited substantive payload.

Integrity findings are deterministic rebuildable projections. They have no canonical record identity or lifecycle and clear only when reevaluation no longer detects the violation or limitation.

## Accepted Coordinated Persistence, Recovery, and Derived-Index Contracts

ADR 0009 establishes Portia’s implementation-neutral protocol for recoverable multi-record operations without claiming filesystem-wide atomicity.

The principal public contracts are:

```text
operation_journal
operation_current_pointer
operation_lock
quarantine_record
quarantine_current_pointer
finding_acknowledgement
finding_suppression
finding_suppression_current_pointer
source_snapshot
derived_index_metadata
derived_current_pointer
```

Operations use opaque identity, immutable journal revisions, explicit current pointers, complete preflight observations, ordered write sets, exact prior-state fingerprints, deterministic lock ordering, and structured partial state. Canonical acceptance remains distinct from operation completion. Accepted canonical records are not erased merely to simulate rollback.

Quarantine is revisioned operational protection rather than lifecycle. Acknowledgement records review without resolving or suppressing a finding. Suppression is narrowly limited to exact advisory or warning evaluations with presentation-only effects and explicit expiry conditions.

Derived generations are immutable, complete, nonauthoritative, source-snapshot-bound replacements. A current pointer selects one generation explicitly but does not prove freshness, authorization compatibility, or absence. Reads do not silently rebuild derived state, and a missing index never proves an empty graph.

JSON Schema validates local wire shape. Application validation remains responsible for exact filesystem containment, digest truth, journal linearity, replay, lock conflicts and clearing, operation-specific ordering, authorization, recovery safety, snapshot freshness, complete installation, and current-use eligibility.

## Accepted Actor Directory Contracts

ADR 0010 defines the teacher-local Actor Directory for recurring non-roster human collaborators.

One Actor represents one recurring person, not a household, organization, role, contact method, authenticated user, or roster student. Identity remains the opaque stable `actr_` identifier. Current display data, category, organization, title, contact information, relationship assertions, and workflow roles do not participate in Actor equality.

The principal canonical contracts are:

```text
actor
actor_contact_point
actor_student_relationship
actor_roster_student_collision
actor_directory_lifecycle_transition
actor_directory_lifecycle_history_correction
actor_directory_amendment
actor_directory_record_migration
actor_directory_exceptional_removal
```

Exact Actor Directory references include the expected public contract version and never silently follow migration, correction, consolidation, splitting, or supersession.

Contact Points are privacy-sensitive child records with explicit source, local verification state, use preference, lifecycle, and replacement lineage. Actor-to-Student Relationships use exact `class_id + student_id` targets, explicit basis, local review, optional effective dates, and no implied guardianship, consent, custody, disclosure permission, employment, or decision authority.

Duplicate detection remains a derived Integrity Finding. Human-confirmed consolidation creates one new successor Actor from several predecessors. Correction of a conflated person creates several new successor Actors from one predecessor. Historical references remain exact and are not silently retargeted.

Actor lifecycle uses:

```text
proposed
active
inactive
invalidated
superseded
```

Inactive, invalidated, and superseded records remain historically resolvable. Quarantine remains operational protection rather than lifecycle, and exceptional removal remains a narrow authorized mechanism rather than ordinary retention behavior.

Actor-aware version-2 operational contracts add exact Actor record, Actor set, and Actor Directory collection targets to Integrity Findings, Operation Journals, Operation Locks, and Quarantine while preserving their version-1 schemas unchanged.

Actor-derived incoming-reference, replacement-frontier, and lifecycle projections reuse the existing version-1 source-snapshot, generation-metadata, and current-pointer contracts. Derived state is nonauthoritative, privacy-minimized, authorization-scoped, rebuildable, and unable to prove absence when discovery coverage is incomplete.

JSON Schema validates local wire shape. Application validation remains responsible for exact storage and owner agreement, Core roster resolution, current-use eligibility, lifecycle history, duplicate review, correction topology, operation ordering, incoming-reference completeness, privacy, authorization, digest truth, recovery, and derived freshness.

## Accepted Account and Observation Contracts

ADR 0011 defines the Event-local source-evidence layer without collapsing evidence into interpretation or formal judgment.

The principal public contracts are:

```text
account
observation
portia_account_id
portia_observation_id
represented_human_attribution
evidence_time
source_artifact_ref
```

One Account preserves one coherent attributed statement, report, response, recollection, or perspective from one represented human source. One Observation preserves one coherent human or instrumented record of directly observable, counted, timed, recorded, or measured information. Neither contract establishes credibility, corroboration, intent, severity, policy violation, diagnosis, behavioral function, risk, Classification, Hypothesis, Determination, or another finding.

Accounts use opaque `acct_` identifiers and Observations use opaque `obs_` identifiers. Both are canonical children of one Event and reuse `portia_target_ref` to target the Event, one Event Participant, or an explicit Participant set. Source or observer attribution remains separate from target and from persistence-operation `created_by` / `updated_by` attribution.

Account content distinguishes `verbatim_quote` from `recorded_summary`, preserves `firsthand`, `secondhand`, `mixed`, or `unknown` information origin, and may preserve source-expressed uncertainty without treating it as credibility. Conflicting Accounts may coexist. Source retraction is source-evidenced through a later same-source Account plus a coordinated transition of the predecessor to `retracted`; teacher disbelief is not retraction.

Observations use one neutral model for positive, neutral, and potentially concerning observable information. Human and instrument observers remain explicit. Narrative observations stay observable rather than interpretive, and structured measurement supports count, duration, latency, percentage, and bounded other numeric measurements.

Account lifecycle is:

```text
proposed
active
retracted
invalidated
superseded
```

Observation lifecycle is:

```text
proposed
active
invalidated
superseded
```

Account and Observation v1 expose no in-place Amendment surface. Material evidence correction creates an explicit successor and preserves exact historical references. Paper- and import-derived evidence begins proposed and requires accepted local review before activation.

An active `reported_involved` Event Participant Role requires a qualifying active same-Event Account whose target is the Role Participant or a Participant set containing that Participant. An Event-wide Account is insufficient for that participant-specific assertion. Observation, paper provenance, import provenance, free text, or teacher confirmation alone does not replace the Account requirement already present in Role v3.

Accounts and Observations reuse the existing lifecycle-history, disagreement, dependency, migration, exceptional-removal, Operation Journal, Operation Lock, Quarantine, Integrity Finding, source-snapshot, generation-metadata, and current-pointer contracts through exact generic work-record references. No Account- or Observation-specific copies of those shared contracts are required. Operational and derived records remain privacy-minimized and must not copy substantive Account or Observation prose merely for diagnostics or coordination.

JSON Schema validates local wire shape. Application validation remains responsible for Event and target resolution, represented-source and observer resolution, review gates, chronology, measurement/method compatibility, source-evidenced retraction, Role-basis eligibility and target alignment, lifecycle history, replacement topology, exact-reference behavior, provenance truth, authorization, privacy, operational recovery, and derived freshness.

## Initial Event, Event Participant, and Role Model

Portia now defines an initial canonical model for Events, Event Participants, and Event Participant Roles.

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

Event Participant Roles are separate canonical records rather than embedded role fields.

### Event Participant Roles

Event Participant Roles are stored beneath the owning Event at:

```text
classes/<class_id>/modules/portia/work/<event_id>/
  records/event_participant_role/<role_id>.json
```

One Role record represents one Event-local assertion that one Event Participant has one role type.

The initial neutral role vocabulary is:

```text
directly_involved
present
reported_involved
contextual
```

Role assignment remains optional. One Event Participant may have no Role, one Role, or several compatible Roles.

The initial compatible active combinations are:

```text
present + directly_involved
present + reported_involved
present + contextual
```

The application must reject duplicate active Role types and incompatible active combinations.

A Role does not itself establish blame, guilt, fault, intent, credibility, severity, policy violation, institutional responsibility, or a formal Determination.

Every active `reported_involved` Role must reference a qualifying active same-Event attributed Account whose target is that Participant or a Participant set containing that Participant.

Top-level Role `detail` is permitted only for `contextual`. An active or superseded contextual Role must retain concise, neutral, nonempty detail.

Each Role has its own:

* durable `role_id`;
* lifecycle;
* creation source;
* local creation and update attribution;
* optional or conditionally required structured basis;
* correction history;
* and forward supersession relationships.

A persisted Role v2 `target` is immutable. Material participant correction creates a successor Role rather than retargeting the existing record.

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

Event Participant Role statuses are:

```text
proposed
active
invalidated
superseded
```

Corrections preserve history.

A proposed participant may become active in place when the teacher confirms the same identity.

A material identity correction creates a replacement participant that canonically supersedes the prior record.

A Role may be created directly as active when an explicit digital assignment has already been reviewed. Otherwise, paper interpretation, imports, automation, ambiguity, and incomplete entry ordinarily begin as proposed.

Role activation requires:

```text
Event Participant status = active
Event status = draft or active
```

Invalidated and superseded Roles are terminal under ordinary workflows. Material Role correction creates a successor whose activation is coordinated with supersession of the prior Role.

Cancelled, invalidated, and superseded canonical records remain preserved rather than being silently deleted or rewritten. Canonical Role files are not hard-deleted through ordinary workflows.

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

Returned-page interpretation may create proposed participants, proposed Roles, or other proposed records, but scanning or automated recognition never constitutes teacher confirmation.

Event Participant Roles never use paper stage `preallocated`. A paper-derived Role exists only after returned-page processing creates a specific assertion and therefore uses:

```text
creation_source.type = paper_capture
creation_source.stage = ingested
```

Every paper-derived Role retains a matching paper basis entry. A paper-derived `reported_involved` Role may remain proposed with paper basis alone, but activation additionally requires a same-Event attributed Account reference.

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

The Event, Event Participant, and Event Participant Role schemas use JSON Schema Draft 2020-12.

JSON Schema validates local record shape, including discriminated unions, constants, enums, identifier formats, timestamp syntax, and rejection of unknown properties.

Application validation remains responsible for cross-record and contextual invariants such as:

* path and persisted identity agreement;
* owning-class and school-year validity;
* roster and Actor reference validity;
* route and page-record existence;
* exact matching paper provenance and basis references;
* Account and Observation existence, Event scope, and lifecycle eligibility;
* Account attribution, lifecycle eligibility, and Participant-target alignment for active `reported_involved`;
* timestamp chronology;
* lifecycle-transition legality;
* Event activation requiring an active participant;
* Role activation requiring an active participant and eligible Event state;
* duplicate participant and duplicate active Role detection;
* active-role compatibility;
* immutable persisted Role v2 `target`;
* replacement ordering;
* Account and participant dependency resolution;
* coordinated successor activation and supersession;
* canonical no-hard-delete rules;
* and atomic or recoverable multi-record writes.

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

Original Accounts, Observations, and historical values should remain auditable. Account and Observation v1 corrections use explicit successor/supersession workflows rather than in-place Amendment of substantive evidence.

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

* [Portia Event, Event Participant, and Event Participant Role Domain Model](docs/design/portia-event-and-participant-domain-model.md)

  Defines Event meaning and boundaries, Event root fields, occurrence precision, location and instructional context, participant identity variants, separate Event Participant Roles, neutral Role vocabulary, Role compatibility, basis, creation source, lifecycle transitions, dependency resolution, correction and supersession, paper capture, validation boundaries, and teacher-workflow constraints.

* [Portia Reference, Targeting, and Relationship Contracts](docs/design/portia-reference-targeting-and-relationship-contracts.md)

  Defines scope-specific identity and record references, target families, bounded display snapshots, exact resolution, schema versioning, Work Relationship ownership and lifecycle, and Event-family v2 reconciliation.

* [Portia Lifecycle, Amendment, Correction, and Migration Contracts](docs/design/portia-lifecycle-amendment-correction-and-migration-contracts.md)

  Defines current status and append-only history, lifecycle transitions, amendment, disagreement, replacement, dependencies, migration, ownership correction, exceptional removal, integrity findings, record-family upgrades, schema organization, and the Issue #13 persistence boundary.

* [Portia Coordinated Persistence, Recovery, and Derived-Index Contracts](docs/design/portia-coordinated-persistence-recovery-and-derived-index-contracts.md)

  Defines operation identity and journaling, preflight, exact write sets, locks, recoverable commit, partial success, compensation, repair, Quarantine, finding administration, deterministic source snapshots, immutable derived generations, current pointers, unavailable-state behavior, and the production implementation boundary.

* [Portia Actor Directory Domain Model and Lifecycle](docs/design/portia-actor-directory-domain-model-and-lifecycle.md)

  Defines the semantic unit of one Actor, eligibility and roster boundaries, canonical storage, Actor roots, Contact Points, Actor-to-Student Relationships, Actor–Roster Student Collisions, lifecycle and history, amendment, consolidation, splitting, migration, exceptional removal, operational targeting, derived views, privacy, and the production implementation boundary.

* [Portia Account and Observation Domain Models](docs/design/portia-account-and-observation-domain-models.md)

  Defines attributed Accounts, direct and instrumented Observations, Event-local targeting, source and observer attribution, quote/summary representation, information origin, measurement, lifecycle, source-evidenced retraction, correction, provenance, Role integration, shared infrastructure reuse, and privacy boundaries.

### Schemas

* [Schema Guide and Catalog](schemas/README.md)

  Documents immutable schema identity, offline resolution, shared references, lifecycle, correction, migration, removal, coordinated-operation records, Quarantine, finding administration, deterministic source snapshots, immutable derived generations, explicit current pointers, and structural-versus-application validation.

* [Actor Schema](schemas/v1/actors/actor.schema.json)

  Canonical teacher-local Actor root for one recurring non-roster human person.

* [Actor Contact Point Schema](schemas/v1/actors/actor-contact-point.schema.json)

  Privacy-sensitive email and phone child records with source, local verification, use preference, lifecycle, and exact replacement lineage.

* [Actor-to-Student Relationship Schema](schemas/v1/actors/actor-student-relationship.schema.json)

  Explicit locally reviewed relationship assertions to exact Core roster-qualified students without implied authority.

* [Actor–Roster Student Collision Schema](schemas/v1/actors/actor-roster-student-collision.schema.json)

  Immutable reviewed evidence that an Actor duplicates one exact roster student, linked to coordinated Actor invalidation.

* [Actor-Aware Operation Journal v2](schemas/v2/operations/operation-journal.schema.json)

  Version-2 coordinated-operation journal with exact Actor record, Actor set, and Actor Directory collection targets.

* [Account v1 Schema](schemas/v1/accounts/account.schema.json)

  Canonical Event-local attributed source contribution with explicit quote/summary representation, information origin, lifecycle, source lineage, provenance, and replacement semantics.

* [Observation v1 Schema](schemas/v1/observations/observation.schema.json)

  Canonical Event-local human or instrumented observation with neutral observable narrative, structured measurements, timing, provenance, lifecycle, and replacement semantics.

* [Represented Human Attribution Schema](schemas/v1/attribution/represented-human-attribution.schema.json)

  Shared represented-source/observer attribution for roster students, Actors, local operators, descriptive people, and unidentified people, distinct from persistence-operation attribution.

* [Evidence Time Schema](schemas/v1/common/evidence-time.schema.json)

  Shared evidence-time precision for exact, approximate, date-only, bounded-range, and unknown times.

* [Source Artifact Reference Schema](schemas/v1/provenance/source-artifact-ref.schema.json)

  Typed references to paper captures, workspace files, exact Portia records, sibling-module records, and inert external records without embedding source binaries.

* [Event v2 Schema](schemas/v2/event.schema.json)

  Current implementation-target Event `work.json` contract.

* [Event Participant v3 Schema](schemas/v3/event-participant.schema.json)

  Current implementation-target Participant contract with exact cross-work predecessor references for ownership correction and migration.

* [Event Participant Role v3 Schema](schemas/v3/event-participant-role.schema.json)

  Current implementation-target Role contract with exact cross-work predecessor references while preserving Role version-2 domain semantics.

* [Work Relationship v2 Schema](schemas/v2/work-relationship.schema.json)

  Current source-owned relationship contract with exact predecessor versions 1 and 2 plus ownership-correction and migration reasons.

* [Lifecycle Transition Schema](schemas/v1/lifecycle/lifecycle-transition.schema.json)

  Append-only status-transition history for Portia works and records.

* [Amendment Schema](schemas/v1/corrections/amendment.schema.json)

  Append-only nonmaterial before-and-after correction evidence.

* [Integrity-Finding Projection Schema](schemas/v1/projections/integrity-finding.schema.json)

  Deterministic rebuildable diagnostics that are explicitly noncanonical.

* [Operation Journal Schema](schemas/v1/operations/operation-journal.schema.json)

  Immutable complete operational snapshots for bounded coordinated operations.

* [Quarantine Record Schema](schemas/v1/operations/quarantine-record.schema.json)

  Revisioned operational protection that remains distinct from canonical lifecycle.

* [Derived Index Metadata Schema](schemas/v1/projections/derived-index-metadata.schema.json)

  Immutable complete generation metadata bound to deterministic source snapshots and exact output fingerprints.

* [Historical Event-family v1 Schemas](schemas/event.schema.json)

  The unversioned-path Event, Event Participant, and Event Participant Role schemas remain historical version-1 contracts and are not the current implementation target.

### Examples

* [Portia Account and Observation Examples](docs/examples/portia-account-and-observation-examples.md)

  Accepted synthetic and machine-validated examples for source attribution, quotation and summary, conflicting Accounts, retraction, correction, paper/import provenance, neutral Observation content, structured measurement, Role integration, source artifacts, disagreement, migration/removal, and operational compatibility.

* [Portia Actor Directory Examples](docs/examples/portia-actor-directory-examples.md)

  Accepted synthetic and machine-validated examples for Actor roots, Contact Points, Relationships, roster collisions, lifecycle, correction, amendment, migration, exceptional removal, Actor-aware operations, and derived compatibility.

* [Portia Coordinated Persistence, Recovery, and Derived-Index Examples](docs/examples/portia-coordinated-persistence-recovery-and-derived-index-examples.md)

  Accepted synthetic and machine-validated examples for journals, pointers, locks, Quarantine, finding administration, source snapshots, immutable generations, and derived current selection.

* [Portia Lifecycle, Amendment, Correction, and Migration Examples](docs/examples/portia-lifecycle-amendment-correction-and-migration-examples.md)

  Accepted synthetic and machine-validated examples for lifecycle history, amendment, disagreement, dependency, migration, ownership correction, exceptional removal, upgraded record contracts, and integrity findings.

* [Portia Reference, Targeting, and Relationship Examples](docs/examples/portia-reference-targeting-and-relationship-examples.md)

  Accepted synthetic examples for every shared reference and target family, Event-family v2 reconciliation, Work Relationship, layered resolution, and explicit migration.

* [Portia Event and Event Participant Examples](docs/examples/portia-event-and-participant-examples.md)

  Historical validated examples covering digital entry, paper preallocation and confirmation, cross-class participation, unresolved identity, identity resolution, and Event supersession.

* [Portia Event Participant Role Examples](docs/examples/portia-event-participant-role-examples.md)

  Historical validated examples covering direct digital Role creation, compatible Role assignments, contextual detail, paper-derived and imported reported involvement, basis correction, and supersession.

### Validation

* [Issue #15 Validation: Account and Observation Domain Models](docs/validation/issue-15-account-observation-validation.md)

  Records the Account/Observation public-contract inventory, 245 manifest scenarios, complete 76-case application-invalid matrix, 32-criterion acceptance matrix, representative examples, final Core and Portia drift anchors, validation boundary, and repository acceptance commands.

* [Issue #14 Validation: Actor Directory Domain Model and Lifecycle](docs/validation/issue-14-actor-directory-validation.md)

  Records the Actor Directory public-contract inventory, fixture totals, complete application-invalid matrix, acceptance matrix, final Core and Portia drift anchors, validation boundary, examples, and repository acceptance commands.

* [Issue #13 Validation: Coordinated Persistence, Recovery, and Derived-Index Contracts](docs/validation/issue-13-coordinated-persistence-recovery-and-derived-index-validation.md)

  Records the 25 public Issue #13 contracts, examples, fixture totals, comprehensive application-invalid matrix, final sibling-repository drift check, validation boundary, and repository acceptance commands.

* [Issue #12 Validation: Lifecycle, Amendment, Correction, and Migration Contracts](docs/validation/issue-12-lifecycle-amendment-correction-and-migration-validation.md)

  Records the public-contract inventory, validation boundary, executable examples, comprehensive application-invalid matrix, documentation checks, and repository acceptance commands.

* [Issue #8 Validation: Event Participant Role Domain Model](docs/validation/issue-8-event-participant-role-validation.md)

  Records Draft 2020-12 schema meta-validation, 12 accepted valid Role fixtures, 18 rejected invalid Role fixtures, seven passing automated tests, and the boundary between schema-enforced and application-level invariants.

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

* [ADR 0006: Define the Initial Event Participant Role Domain Model](docs/decisions/0006-define-event-participant-role-domain-model.md)

  Establishes separate canonical Event Participant Role records, neutral Role vocabulary, compatible active Role combinations, structured basis, independent creation provenance, attributed Account requirements for reported involvement, Role lifecycle, replacement-based correction, dependency resolution, no-hard-delete retention, and schema/application validation boundaries.

* [ADR 0007: Define Shared Reference, Targeting, and Relationship Contracts](docs/decisions/0007-define-shared-reference-targeting-and-relationship-contracts.md)

  Establishes the public reference and target families, bounded historical snapshots, exact layered resolution, Work Relationship ownership and lifecycle, stable schema identity, and current Event-family v2 implementation target.

* [ADR 0008: Define Shared Lifecycle, Correction, and Migration Contracts](docs/decisions/0008-define-lifecycle-correction-and-migration-contracts.md)

  Establishes current status plus append-only history, amendment and replacement boundaries, disagreement, dependency handling, migration, ownership correction, exceptional removal, record-family upgrades, integrity findings, immutable public schema organization, and the Issue #13 persistence boundary.

* [ADR 0009: Define Coordinated Persistence, Recovery, and Derived-Index Contracts](docs/decisions/0009-define-coordinated-persistence-recovery-and-derived-index-contracts.md)

  Establishes durable state categories, immutable operation journals, exact preflight and write sets, lock identity and conservative clearing, recoverable multi-record completion, structured partial success, repair and Quarantine, finding acknowledgement and suppression, deterministic source snapshots, immutable derived generations, and explicit current selection.

* [ADR 0010: Define the Actor Directory Domain Model and Lifecycle](docs/decisions/0010-define-actor-directory-domain-model-and-lifecycle.md)

  Establishes one recurring non-roster person per Actor, workspace-scoped canonical storage, separate Contact Points and Relationships, roster-student collision handling, lifecycle and correction, reviewed consolidation and splitting, migration and removal, Actor-aware operational targeting, derived compatibility, and privacy boundaries.

* [ADR 0011: Define Account and Observation Domain Models](docs/decisions/0011-define-account-and-observation-domain-models.md)

  Establishes Event-local Account and Observation evidence records, source and observer attribution, quote/summary and firsthand/secondhand semantics, observable measurement, lifecycle and source-evidenced retraction, replacement-based correction, paper/import review gates, `reported_involved` Account alignment, shared infrastructure reuse, and no-automatic-finding semantics.

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
* Event Participants;
* Event Participant Roles;
* Accounts;
* interventions;
* family communications;
* Actors;
* and outcomes.

Local-first storage does not make student records inherently non-sensitive. Portia workspace data, exports, synchronized folders, and backups must be handled according to applicable school, district, state, and federal requirements.

## Next Architecture Work

Likely next work includes:

* implementing the accepted ADR 0009, ADR 0010, and ADR 0011 persistence, Actor Directory, Account/Observation evidence, recovery, Quarantine, integrity, and derived-generation contracts as strictly typed production services in a later executable milestone;
* building teacher-facing Actor selection plus Account/Observation capture, review, correction, retraction, and privacy-maintenance workflows;
* defining the minimal Support Process root and status contract, followed by the broader Support, Intervention, implementation, and fidelity model;
* defining Classification, Hypothesis, Determination, Response, Follow-Up, Outcome, and Communication schemas that consume Account/Observation evidence and exact Actor references while preserving their own contextual roles, review, and authority evidence;
* defining how teacher schedules assist Event ownership selection;
* implementing and performance-testing the minimum viable teacher workflow;
* establishing privacy projections and redaction for multi-student Events;
* defining deliberate student-specific exports;
* specifying PDS2 page-record and route schemas;
* evaluating a capture-batch routing contract for multi-entry paper sheets;
* defining the Portia intervention producer profile, immutable manifest contract, privacy projection, and Core v0.6 fixture;
* defining cross-year Support successor workflows;
* and defining Portia archival integration with Sunset.

## License

Licensing information will be documented before an initial software release.
