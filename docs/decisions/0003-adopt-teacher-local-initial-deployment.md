# ADR 0003: Adopt a Teacher-Local Initial Deployment for Portia

* **Status:** Accepted
* **Date:** 2026-07-14
* **Decision owners:** Portia maintainers
* **Related issue:** [#2 — Define Portia’s role and integration boundaries within Paper Data Suite](https://github.com/Paper-Data-Suite/pds-portia/issues/2)
* **Related research:** [`docs/research/student-behavior-tracking-best-practices.md`](../research/student-behavior-tracking-best-practices.md)
* **Related design:** [`docs/design/portia-role-within-paper-data-suite.md`](../design/portia-role-within-paper-data-suite.md)
* **Related decision:** [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)

## Context

The research completed in Issue #1 describes a comprehensive behavior-support system that may involve:

* classroom educators;
* administrators;
* counselors;
* case managers;
* special educators;
* restorative facilitators;
* data analysts;
* records officers;
* students;
* parents and guardians;
* auditors;
* and technical administrators.

A complete institution-wide implementation would also require:

* authenticated user identity;
* organization and school identity;
* role-based and attribute-based authorization;
* field-level access control;
* concurrent access;
* centralized audit logging;
* controlled disclosure;
* records-access and amendment workflows;
* legal holds;
* retention enforcement;
* secure student and family access;
* tenant configuration;
* backup and disaster recovery;
* security monitoring;
* and institutional deployment governance.

The current Paper Data Suite architecture is substantially narrower.

Paper Data Suite is presently:

* local-first;
* teacher-controlled;
* filesystem-oriented;
* organized around a selected local workspace;
* structured primarily by class rosters and module-owned work;
* operated through module-specific command-line and terminal-menu workflows;
* and designed to preserve human judgment without hosted collaboration or automated educational decision-making.

Existing modules use `pds-core` for:

* workspace resolution;
* class and roster identity;
* active school-year state;
* standards;
* module-qualified work paths;
* PDS2 routing;
* scan provenance;
* shared navigation;
* and related local infrastructure.

The suite does not currently provide a general platform for:

* institutional user accounts;
* authentication;
* schoolwide authorization;
* multi-user transactions;
* centralized access auditing;
* student or family portals;
* or district-level tenant administration.

Attempting to implement the complete institutional vision inside Portia’s first release would therefore require Portia to create substantial platform infrastructure that does not belong solely to the behavior-support domain.

It would also prevent early validation of Portia’s foundational domain model and teacher workflow.

The initial product boundary must distinguish:

1. what Portia should ultimately support as a responsible behavior-management system; and
2. what Portia can honestly and safely implement within the present Paper Data Suite architecture.

## Decision

Portia’s first implementation will be a **teacher-local, classroom-focused Paper Data Suite module**.

The initial release will use the existing local PDS workspace and shared Core class and roster infrastructure.

It will be designed primarily for one teacher documenting and managing behavior-support information for students in that teacher’s current classes.

The initial release will not represent itself as:

* a schoolwide discipline system;
* a district behavior-management platform;
* an institutional case-management system;
* a student-information system;
* an IEP or special-education system of record;
* a counseling or clinical record system;
* a threat-assessment platform;
* a mandated-reporting system;
* a formal FERPA request-management platform;
* or a multi-user administrative application.

The broader institutional requirements identified through research remain valid long-term requirements. They are deferred until Paper Data Suite has an explicitly designed shared institutional platform capable of supporting them.

## Initial User Model

The initial Portia user is one teacher operating a local Paper Data Suite workspace.

The teacher:

* controls access to the local workspace;
* selects or configures the workspace through Core;
* uses Core-managed classes and rosters;
* creates and reviews Portia-owned records;
* manages teacher-owned supports and follow-up;
* exports information deliberately;
* and remains responsible for local handling under applicable school and district policy.

Portia v1 will not include separately authenticated Portia users.

It will not attempt to infer roles such as:

* administrator;
* counselor;
* parent;
* student;
* records officer;
* or auditor

from local operating-system access or from a shared folder.

A local user having filesystem access must not be represented as equivalent to a formally authorized institutional role.

## Initial Functional Scope

Portia’s initial teacher-local scope may include the following capabilities.

### Class and Student Selection

Portia may:

* load classes through Core;
* load shared class rosters;
* use durable `class_id` and `student_id` references;
* display student names through Core helpers;
* preserve optional roster metadata only when explicitly needed;
* and avoid duplicating canonical roster files.

### Objective Event and Observation Records

Portia may support:

* classroom behavior Events;
* direct observations;
* reported Accounts;
* quotations;
* contextual information;
* approximate or exact time;
* location;
* instructional context;
* immediate safety status;
* and immediate teacher response.

Portia must preserve distinctions among:

* observation;
* reported information;
* interpretation;
* preliminary Classification;
* Hypothesis;
* and Determination.

### Positive Observations and Growth

Portia may support records of:

* successful use of a replacement skill;
* self-advocacy;
* help-seeking;
* conflict resolution;
* reengagement;
* repair;
* progress toward a goal;
* effective classroom supports;
* and student strengths.

The initial release must not be a negative-only incident ledger.

### Classroom-Managed Responses

Portia may record teacher-managed actions such as:

* redirection;
* reteaching;
* clarification;
* environmental adjustment;
* regulation support;
* check-in;
* change of task;
* family contact;
* support request;
* and planned follow-up.

These actions must remain separate from the observation itself.

### Teacher-Owned Supports and Interventions

Portia may support teacher-owned plans containing:

* a clearly defined concern or target;
* baseline information;
* prevention strategies;
* replacement skills;
* teaching strategies;
* expected implementation;
* responsible person;
* review date;
* fidelity information;
* outcome measures;
* student input;
* family input where appropriate;
* and continuation, modification, fading, or closure decisions.

Portia v1 must not describe these plans as formal IEP, FBA, BIP, clinical, or district-authorized records unless an external authorized process establishes that status.

### Student and Family Statements

Portia may store concise statements provided directly to the teacher when necessary for the classroom record.

Such statements must:

* remain attributed to their author;
* remain distinguishable from the teacher’s account;
* preserve disagreement or missing context;
* and not be silently rewritten into an institutional narrative.

The initial release will not provide a student or family login portal.

### Follow-Up and Work Queues

Portia may support local teacher work queues such as:

* drafts;
* follow-ups due;
* supports due for review;
* incomplete outcomes;
* student or family statements awaiting response;
* and records needing correction.

These are local workflow aids, not institution-wide assignment or escalation systems.

### Local Reports

Portia may produce privacy-conscious teacher-facing reports such as:

* documented Events by date or context;
* positive observations;
* classroom responses;
* active supports;
* overdue follow-up;
* intervention fidelity;
* outcomes;
* instructional time lost;
* missing data;
* and teacher-local trends.

Reports must describe documented records and teacher actions. They must not claim to measure a student’s character, intent, total behavior, or future risk.

## Deferred Institutional Capabilities

The following capabilities are outside the initial teacher-local release.

### Multi-User Authentication

Portia v1 will not provide:

* application user accounts;
* single sign-on;
* multifactor authentication;
* organization provisioning;
* role assignment;
* delegated access;
* or user deprovisioning.

### Institutional Authorization

Portia v1 will not claim to enforce:

* schoolwide role-based access;
* attribute-based authorization;
* field-level permissions by professional role;
* case assignments;
* break-glass access;
* or institution-wide legitimate-educational-interest rules.

Local filesystem permissions are not a substitute for these controls.

### Concurrent Case Management

Portia v1 will not support:

* several authenticated users editing the same case;
* cross-user assignment queues;
* centralized administrative review;
* institutional referrals;
* administrator Determinations;
* multi-user conflict resolution;
* or transactional collaboration.

### Student and Family Portals

Portia v1 will not include:

* student authentication;
* parent or guardian authentication;
* portal-based record review;
* online amendment requests;
* online statements of disagreement;
* notification delivery tracking;
* or direct portal communication.

### Formal Records Administration

Portia v1 will not claim to administer:

* FERPA access requests;
* institutional amendment hearings;
* disclosure logs for all organizational disclosures;
* legal holds across systems;
* records-officer workflows;
* or formal retention enforcement.

Portia should nevertheless preserve records in a way that does not obstruct future lawful access, correction, or export.

### Schoolwide Discipline

Portia v1 will not be the authoritative system for:

* office discipline referrals;
* suspension;
* expulsion;
* formal policy adjudication;
* district discipline reporting;
* or administrator-assigned consequences.

The teacher may record that a matter was referred externally and may store a minimal authorized outcome reference. Portia should not copy an entire external discipline file by default.

### Specialized Safety and Legal Workflows

Portia v1 will not serve as the authoritative workflow for:

* suspected abuse or neglect;
* self-harm or suicide concerns;
* threat assessment;
* Title IX matters;
* sexual harassment or sexual violence;
* bullying investigations governed by special law or policy;
* restraint and seclusion reporting;
* law-enforcement investigations;
* discrimination complaints;
* or clinical emergencies.

When such a concern arises, Portia may record only the minimum necessary linkage or routing status permitted by policy.

For example:

```text
Referred to the district safety process at 10:24 a.m.
```

Sensitive details should remain in the authorized external system or process.

### District Equity Analytics

Portia v1 will not claim to provide valid district-level disproportionality reporting.

Teacher-local data may be incomplete because it reflects:

* one teacher’s classes;
* one observer;
* selected documentation practices;
* limited denominators;
* and incomplete institutional outcomes.

Local summaries must not be represented as schoolwide equity conclusions.

## Formal Determinations in the Initial Release

ADR 0002 permits Portia to own formal Determinations when Portia is authorized to maintain them.

Under the teacher-local initial deployment, Portia will ordinarily not create institution-level disciplinary Determinations.

Portia may support a local teacher decision record such as:

* classroom concern resolved;
* support requested;
* support continued;
* account corrected;
* no further classroom follow-up needed;
* or referred to an external authorized process.

Such a record must not be presented as:

* an administrator’s policy finding;
* a formal discipline adjudication;
* an official special-education decision;
* or an institutional legal determination.

Formal institutional Determinations remain a future capability or an external-system reference until Portia has the required authority, access model, and governance.

## Storage Boundary

The initial release will use local module-owned records beneath the existing Paper Data Suite workspace.

Where a Portia record belongs to one class, the intended class-scoped structure should be compatible with:

```text
classes/<class_id>/modules/portia/work/<work_id>/
```

The exact meaning of Portia `work_id` and the final internal structure require a separate identity and storage decision.

This ADR does not resolve how to store:

* events involving students from several classes;
* schoolwide events;
* transportation events;
* cafeteria or hallway events;
* support plans spanning several classes;
* or records continuing across school years.

Portia must not solve these cases by fabricating:

* a `schoolwide` class;
* a synthetic student;
* duplicate student identities;
* or arbitrary ownership by one selected class.

Until a cross-class storage contract is accepted, the initial implementation should limit writable workflows to cases that can be represented honestly within the approved class-scoped model.

## Privacy Model

The initial release must remain privacy-conscious despite lacking an institutional authorization platform.

At minimum, Portia should:

* store data only in the selected local workspace;
* avoid committing student data to the source repository;
* minimize sensitive collection;
* avoid clinical and legal details;
* provide deliberate export rather than automatic sharing;
* avoid unrestricted bulk export;
* warn before exporting identifiable records;
* avoid displaying unnecessary negative history during new observation entry;
* preserve correction history;
* distinguish active records from superseded values;
* document local backup and synchronization risks;
* and explain that shared-folder access may expose student records.

Portia must not claim that local-first storage is inherently private or compliant.

A workspace synchronized through OneDrive, another cloud folder, network storage, or backup software may copy Portia data beyond the local computer. The user and adopting organization remain responsible for ensuring that the selected location is authorized.

## Audit Model

The initial release should preserve an append-oriented history of material record changes, including:

* record creation;
* substantive edits;
* correction;
* supersession;
* Classification changes;
* status changes;
* support-plan changes;
* and outcome changes.

The initial audit model may identify the local application user or configured teacher identity where available.

It must not claim to establish a complete institutional access audit because Portia v1 cannot reliably determine every person who viewed files through the operating system, synchronization provider, backup system, or external editor.

The distinction must be explicit:

* **Portia record-change history** may be supported locally.
* **Institutional access auditing** is deferred.

## Export Model

Exports are derived artifacts, not canonical Portia records.

Portia v1 exports should:

* be initiated deliberately;
* identify the source record and export date;
* preserve relevant status and correction information;
* minimize unrelated information;
* support redaction where feasible;
* warn when multiple students are involved;
* avoid silently overwriting an existing export;
* and remain separate from the canonical record.

Portia should not automatically send exports by email, publish them, or copy them into other modules.

## Relationship to Institutional Requirements

The long-term institutional requirements identified in the research remain authoritative design considerations.

The teacher-local release should avoid choices that would prevent later support for:

* authenticated authorship;
* role- and attribute-based authorization;
* field-level sensitivity;
* multi-user review;
* centralized audit;
* student and family access;
* amendment workflows;
* retention enforcement;
* legal holds;
* de-identified aggregate reporting;
* organization-level identity;
* and institutional deployment.

However, Portia v1 must not pretend to implement these capabilities through labels, configuration fields, or incomplete local substitutes.

For example:

* a `role` string in a JSON file is not institutional authorization;
* an `author_name` field is not authenticated authorship;
* a hidden menu option is not access control;
* a local change log is not a complete disclosure log;
* and a password-protected export is not a student portal.

## Migration Principle

A future institution-wide Portia must be treated as a distinct deployment architecture, not merely as a configuration switch applied to local files.

Migration may require:

* organization-scoped identity;
* stable user identities;
* a shared service or database;
* transactional writes;
* authorization policy;
* audit infrastructure;
* secure APIs;
* tenant configuration;
* centralized retention;
* and migration of local Portia records into governed institutional storage.

Any migration must:

* preserve record provenance;
* preserve author attribution;
* preserve correction and supersession history;
* distinguish authenticated from unauthenticated historical authorship;
* avoid fabricating access history;
* and require deliberate import and validation.

## Consequences

### Positive Consequences

* Portia can be implemented within the present Paper Data Suite architecture.
* Development can focus on the behavior-support domain rather than building an institutional platform first.
* Teacher workflows can validate the Event, Account, Response, Support, and Outcome model early.
* Portia remains consistent with the local-first operation of Core, ScoreForm, and Quillan.
* Product claims remain honest about authorization and institutional scope.
* Sensitive formal workflows remain in systems equipped to govern them.
* The initial implementation can remain comparatively small and testable.
* Future institutional requirements remain documented rather than being discarded.
* Architectural gaps in identity, storage, authorization, and auditing remain visible for later deliberate decisions.
* The module avoids creating insecure imitations of institutional controls.

### Costs and Tradeoffs

* Portia v1 will not support several roles collaborating in one case.
* Administrators and support teams cannot use Portia as a shared institutional workflow.
* Student and family participation will require teacher-entered or imported statements rather than direct portal access.
* Formal discipline and specialized safety processes must remain external.
* Teacher-local data will not support complete district analytics.
* Local files may be exposed through shared storage or weak device controls outside Portia’s direct control.
* The teacher may need to enter limited outcome references from external processes.
* Cross-class and schoolwide records remain unresolved until a later identity and storage decision.
* Some Issue #1 product requirements must remain deferred.
* A future institutional deployment may require significant migration and shared-platform work.

## Alternatives Considered

### Alternative A: Build Institution-Wide Portia First

Rejected for the initial release.

This approach would require substantial shared platform infrastructure before Portia’s foundational domain model and teacher workflows had been validated.

It would create pressure to place authentication, authorization, organization identity, auditing, portals, and concurrent storage inside Portia even though those capabilities should serve the broader suite.

### Alternative B: Treat a Shared Local Folder as a Multi-User Platform

Rejected.

A shared OneDrive, network, or cloud-synchronized folder does not provide:

* authenticated record authorship;
* reliable field-level authorization;
* transactional concurrency;
* legitimate-interest enforcement;
* complete access auditing;
* or safe conflict resolution.

Shared storage may be used only where authorized and must not be represented as equivalent to institutional case management.

### Alternative C: Implement Both Local and Institutional Modes Simultaneously

Rejected for the initial release.

Parallel modes would multiply:

* storage models;
* identity models;
* permission models;
* testing requirements;
* migration paths;
* support burden;
* and product ambiguity.

The local model should be validated first. Institutional architecture should be designed separately when shared platform requirements are ready.

### Alternative D: Reduce Portia to a Simple Incident Log

Rejected.

A narrow incident counter would be easier to implement locally but would conflict with the completed research.

It would likely:

* privilege negative records;
* omit supports and outcomes;
* encourage count-based escalation;
* flatten observation and judgment;
* and create a durable punitive profile without adequate educational value.

Even the teacher-local release must support the broader behavior-support lifecycle.

### Alternative E: Defer Portia Until Institutional Infrastructure Exists

Rejected.

Portia’s classroom-focused behavior-support workflows can provide value within the present suite and can help validate the domain before institutional expansion.

Deferral would prevent practical testing of:

* objective observation entry;
* positive records;
* support planning;
* follow-up;
* intervention fidelity;
* outcomes;
* and correction workflows.

## Implementation Constraints

Future Portia v1 implementation must preserve these invariants:

1. The initial deployment is teacher-local and classroom-focused.
2. Portia uses the existing local PDS workspace.
3. Shared class and roster identity come from Core.
4. Portia does not claim to provide institutional authentication or authorization.
5. Local filesystem access is not represented as a formal professional role.
6. Portia v1 does not become the authoritative school discipline system.
7. Specialized safety, clinical, legal, and special-education systems remain external.
8. Formal institutional Determinations are not fabricated through teacher-local records.
9. Portia supports positive behavior, supports, follow-up, and outcomes—not only incidents.
10. Exports are deliberate derived artifacts.
11. Local change history is not described as complete institutional access auditing.
12. Cross-class or schoolwide cases are not forced into fabricated class identity.
13. Teacher-local reports are not represented as complete schoolwide equity analytics.
14. Deferred institutional requirements remain documented.
15. Future institutional migration must preserve provenance without fabricating historical authentication or access data.

## Follow-Up Decisions

Separate ADRs or specifications should address:

* class-scoped, cross-class, and organization-scoped Portia identity;
* the canonical Portia storage layout;
* the initial Portia domain model;
* local author identity and record-change history;
* the minimum viable teacher-facing workflow;
* local export and redaction behavior;
* sensitive-event routing and minimal external references;
* the future institutional platform boundary;
* migration from teacher-local to institutional Portia;
* and Portia archival integration with Sunset.

## Notes

This decision establishes the initial deployment scope, not Portia’s permanent maximum scope.

The long-term vision may include an institution-wide Portia or a shared Paper Data Suite institutional platform. That future work must be based on explicit contracts for identity, authorization, storage, audit, privacy, and governance.

Portia v1 should be useful within its actual boundary and precise about what it does not provide.
