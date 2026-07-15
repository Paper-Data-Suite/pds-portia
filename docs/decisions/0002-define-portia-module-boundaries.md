# ADR 0002: Define Portia’s Role and Module Boundaries

* **Status:** Accepted
* **Date:** 2026-07-14
* **Decision owners:** Portia maintainers
* **Related issue:** [#2 — Define Portia’s role and integration boundaries within Paper Data Suite](https://github.com/Paper-Data-Suite/pds-portia/issues/2)
* **Related research:** [`docs/research/student-behavior-tracking-best-practices.md`](../research/student-behavior-tracking-best-practices.md)
* **Related design:** [`docs/design/portia-role-within-paper-data-suite.md`](../design/portia-role-within-paper-data-suite.md)

## Context

Portia is one module within Paper Data Suite. Its purpose is to support the documentation, interpretation, management, and evaluation of student behavior and related supports.

Paper Data Suite already assigns distinct responsibilities to existing modules:

* `pds-core` owns shared workspace, class, roster, identity, standards, routing, scan-provenance, navigation, and module-integration contracts.
* `pds-scoreform` owns machine-readable selected-response and optical-mark-recognition workflows.
* `pds-quillan` owns written-response evidence, teacher review, standards-based judgment, feedback, and assignment-local reporting.
* `pds-concord` owns collaborative Activities, Sessions, Groups, Artifacts, evidence Review and Moderation, and criterion-level collaborative Scoring.

Additional modules have been conceived for:

* school-year archival and lifecycle transitions;
* academic grading and reporting;
* student portfolios; and
* unit, lesson, and assignment planning.

Portia’s domain is inherently cross-cutting. A behavior-related Event may occur during:

* a lesson;
* an assessment;
* an individual writing task;
* a collaborative Activity;
* a class transition;
* transportation;
* a schoolwide setting;
* or another educational context.

Portia may therefore need to reference records owned by several modules. Without explicit boundaries, Portia could:

* duplicate Core infrastructure;
* recreate ScoreForm, Quillan, or Concord workflows;
* become a general student-information or integration system;
* treat behavior records as academic Scores or Grades;
* expose sensitive information to planning or portfolio workflows;
* assume ownership of archival responsibilities;
* or create direct runtime dependencies among sibling modules.

The Issue #1 research also established that Portia must not become a simple incident counter or digital punishment ledger. Its central responsibility is to preserve the complete behavior-support lifecycle:

```text
Event
→ Accounts and Observations
→ Review and Classification
→ Determination
→ Immediate Responses
→ Supports and Interventions
→ Follow-Up and Outcomes
```

Portia therefore requires a clear domain boundary that is consistent with the modular architecture of Paper Data Suite.

## Decision

Portia will be a **peer Paper Data Suite domain module built on shared contracts and infrastructure provided by `pds-core`**.

The intended dependency direction is:

```text
pds-portia -> pds-core
```

Core will not depend on Portia.

Portia may reference records owned by sibling or future modules, but it will not require those modules as mandatory runtime dependencies for foundational Portia workflows.

Portia is defined as:

> **Paper Data Suite’s contextual behavior-support and response module. It records what was observed, who provided each account, what an authorized person or institution determined, what response or support was provided, and what happened afterward.**

## Portia Ownership

Portia owns the domain concepts and workflows required to document and manage behavior-related support processes.

### Events

Portia owns neutral records of behavior-related or support-related occurrences.

An Event may involve:

* one student;
* several students;
* staff or other participants;
* one class;
* several classes;
* a schoolwide context;
* an instructional context;
* or an external context referenced from another system.

Creating an Event does not itself establish misconduct, responsibility, behavioral function, or a policy violation.

### Accounts and Observations

Portia owns author-attributed records of:

* direct observations;
* reported accounts;
* quotations;
* student statements;
* family statements;
* positive observations;
* contextual information;
* and corrections or amendments to those records.

Portia must preserve the distinction between direct observation, reported information, interpretation, hypothesis, and institutional determination.

### Concerns and Referrals

Portia owns:

* classroom concerns;
* requests for support;
* referrals for review;
* routing status;
* assigned responsibility;
* due dates;
* and follow-up requirements.

A referral is a request for review or service, not proof that misconduct occurred.

### Classifications

Portia owns behavior-related classifications used for routing, local reporting, or policy workflows.

Portia must preserve distinctions among:

* reporter-selected classifications;
* reviewer-confirmed classifications;
* changed classifications;
* unresolved classifications;
* and formal determinations.

A classification must not silently replace the underlying observable account.

### Hypotheses

Portia owns tentative behavior-related hypotheses where they are needed for support planning or formal assessment processes.

A hypothesis:

* must be identified explicitly as tentative;
* must retain its author and supporting evidence;
* may coexist with competing hypotheses;
* must not be displayed as a permanent student trait;
* and must not automatically trigger discipline, tier placement, or intervention escalation.

### Determinations

Portia may own formal institutional determinations when Portia is authorized to maintain those records under local policy.

A Determination must identify:

* the authorized decision-maker;
* the question or allegation reviewed;
* the applicable policy and version;
* the finding;
* the factual basis;
* required notice or review;
* and appeal, reconsideration, or supersession status.

An Account, Referral, or preliminary Classification must never be represented as a formal Determination.

### Immediate Responses

Portia owns records of actions taken during or immediately after an Event, including:

* redirection;
* reteaching;
* environmental changes;
* de-escalation;
* support access;
* family contact;
* administrative assistance;
* removal;
* and other locally authorized responses.

The response taken does not define what occurred and must remain distinct from the Event, Account, and Determination.

### Supports and Interventions

Portia owns behavior-related support and intervention records, including:

* prevention strategies;
* environmental or instructional supports;
* replacement skills;
* teaching strategies;
* responsible staff;
* dosage;
* implementation schedules;
* fidelity measures;
* outcome measures;
* student and family participation;
* and review dates.

Portia must not permit a support plan to consist solely of punitive consequences.

### Follow-Up and Outcomes

Portia owns records of:

* assigned follow-up;
* student check-ins;
* family communication;
* reentry;
* repair;
* intervention fidelity;
* outcomes;
* adverse or unintended effects;
* continuation;
* modification;
* fading;
* intensification;
* and closure rationale.

Portia should evaluate whether support was implemented and whether it helped, rather than merely whether another incident was recorded.

### Amendments and Disagreement

Portia owns behavior-record correction and amendment workflows, including:

* correction requests;
* authorized review;
* current corrected values;
* preserved audit history;
* statements of disagreement;
* supersession;
* and disclosure-ready views.

Append-only audit history must not prevent an inaccurate active record from being corrected.

### Portia-Specific Configuration and Reporting

Portia owns:

* behavior terminology;
* category definitions;
* examples and nonexamples;
* behavior-specific workflow configuration;
* Portia record sensitivity;
* Portia retention classifications;
* behavior-support reports;
* data-quality reports;
* intervention reports;
* and authorized equity analysis.

## Core Ownership

`pds-core` owns shared suite-level infrastructure.

Portia must consume rather than duplicate Core capabilities for:

* workspace-root resolution;
* shared class identity;
* roster loading and validation;
* canonical student identifiers within shared rosters;
* student display helpers;
* durable identifier validation;
* active school-year state;
* shared standards libraries and profiles;
* module-qualified work identity;
* safe path construction;
* PDS2 payload construction and parsing;
* route registrations;
* module-profile discovery and dispatch;
* retained-source scan provenance;
* generic routing-failure and resolution records;
* shared menu navigation behavior;
* and opening local files or directories.

Core must not own or define:

* Portia Events;
* behavior categories;
* behavior classifications;
* behavioral hypotheses;
* support or intervention plans;
* disciplinary Determinations;
* Portia-specific reports;
* behavior-specific privacy levels;
* or Portia retention rules.

Core should remain UI-neutral and domain-neutral. Portia will provide its own teacher-facing workflows over Core APIs.

## ScoreForm Boundary

`pds-scoreform` owns:

* optical-mark recognition;
* answer-sheet layouts;
* bubble and structured-mark detection;
* answer keys;
* selected-response scoring;
* blank and ambiguous-mark handling;
* attempts;
* ScoreForm result records;
* ScoreForm scan diagnostics;
* and ScoreForm-specific exports.

Portia must not:

* generate competing ScoreForm answer sheets;
* detect or interpret OMR marks;
* apply ScoreForm answer keys;
* create ScoreForm attempt records;
* or copy ScoreForm result data into Portia-owned equivalents.

Portia may reference a ScoreForm record when it is relevant to a behavior-support process.

Possible uses include:

* structured self-monitoring;
* check-in/check-out instruments;
* support-preference forms;
* classroom observation checklists;
* or another machine-readable instrument.

A ScoreForm result must not automatically become:

* a Portia behavior Score;
* a behavior Classification;
* a Determination;
* a support-tier placement;
* an intervention decision;
* or proof of behavioral function.

The teacher or authorized reviewer must determine deliberately whether and how the referenced record is relevant within Portia.

## Quillan Boundary

`pds-quillan` owns:

* writing assignments;
* printable writing-response pages;
* submission assembly;
* written evidence;
* review units;
* standards-based observations;
* teacher-entered ratings;
* written feedback;
* and assignment-local writing reports.

Portia must not:

* recreate Quillan writing assignments;
* assemble Quillan submissions;
* copy Quillan reviews;
* generate Quillan feedback;
* or interpret a Quillan rating as a behavioral finding.

Portia may natively store concise student or family statements needed for a behavior record.

Portia may reference a Quillan record when the writing is a substantial independent artifact, such as:

* an extended student reflection;
* a reentry narrative;
* a detailed account of a conflict;
* a written self-assessment;
* or a family-submitted statement.

A Quillan submission or rating must not be treated automatically as evidence of:

* honesty;
* remorse;
* compliance;
* behavioral improvement;
* responsibility;
* or guilt.

## Concord Boundary

`pds-concord` owns:

* collaborative Activities;
* Sessions;
* Groups;
* Group Memberships;
* Roles;
* Responsibilities;
* Concord packet and Artifact records;
* Artifact Authors and Subjects;
* collaborative evidence Review;
* evidence Moderation;
* Concord Criteria;
* Scoring Scales;
* Score Records;
* and evidence-to-Score relationships.

Portia must not:

* recreate Concord Activities or Groups;
* duplicate Concord Artifacts;
* perform Concord Moderation;
* copy Concord Scores;
* or treat collaborative-performance judgments as behavior Determinations.

The owning module should be selected according to the purpose of the record.

A record belongs primarily to Concord when it exists to understand or evaluate collaborative performance, such as:

* role fulfillment;
* coordination;
* contribution to a shared product;
* evidence supporting a collaborative Criterion;
* or authorship of a collaborative Artifact.

A record belongs primarily to Portia when it exists to document or address:

* behavior;
* safety;
* participation access;
* harm;
* support;
* intervention;
* reentry;
* or institutional response.

Portia may reference Concord records as context for a Portia Event or support process.

For example, Portia may reference:

* a Concord Activity;
* Session;
* Group;
* Artifact;
* or Score.

The Concord record remains authoritative for collaborative context. Portia remains authoritative for the behavior-related Event, Account, Response, Support, or Determination.

A Concord Group Score must not automatically generate a Portia behavior record, and a Portia Event must not automatically alter a Concord Score.

## Future Grading and Reporting Boundary

A future grading and reporting module may own:

* academic score aggregation;
* attempt-selection policy;
* weighting;
* marking-period calculations;
* course grades;
* grade reports;
* and formal academic reporting.

Portia does not calculate academic Grades.

The following Portia information must not automatically increase, reduce, or otherwise determine an academic Grade:

* behavior Events;
* Referrals;
* incident counts;
* support tiers;
* intervention participation;
* compliance-related data;
* family communication;
* removals;
* reentry status;
* or support outcomes.

A future reporting module may present an authorized behavior-support summary separately from academic scores and Grades.

Any use of Portia information in formal reporting must preserve the distinction between:

* academic performance;
* behavior-support information;
* disciplinary information;
* and institutional response.

## Future Portfolio Boundary

A future portfolio module may own:

* student work collections;
* selected evidence;
* presentation;
* reflection;
* longitudinal curation;
* and student-facing portfolio workflows.

The portfolio module must not receive unrestricted access to Portia records.

Portia may eventually expose an explicitly authorized portfolio-safe projection containing selected material such as:

* a student-selected reflection;
* a documented strength;
* progress toward a self-selected goal;
* successful self-advocacy;
* use of a replacement skill;
* or a voluntary restorative or reparative artifact.

The following must not enter a portfolio automatically:

* Referrals;
* allegations;
* incident histories;
* Determinations;
* intervention plans;
* family communications;
* disability-related information;
* safety records;
* disputed Accounts;
* or unrelated behavior history.

Portfolio inclusion must be deliberate, purpose-specific, and privacy-conscious.

## Future Planning Module Boundary

A future instructional planning module may own:

* Units;
* Lessons;
* Assignments;
* objectives;
* instructional sequencing;
* timing;
* materials;
* differentiation;
* planned grouping;
* and instructional supports.

Portia may reference planning records to preserve instructional context, including:

* the Lesson;
* Assignment;
* Activity;
* instructional phase;
* grouping structure;
* task type;
* transition;
* or scheduled support associated with an Event.

The planning module remains authoritative for instructional intent.

Portia remains authoritative for:

* what was observed;
* what response occurred;
* whether a support was implemented;
* and what outcome followed.

The planning module must not receive unrestricted Portia history merely to generate or recommend instruction.

## Sunset Boundary

`pds-sunset` is intended to own suite-wide archival and school-year lifecycle orchestration.

Sunset may coordinate:

* year-end archival;
* movement to archival storage;
* validation of archive completeness;
* cross-module lifecycle transitions;
* and approved destruction workflows.

Portia remains responsible for determining the Portia-specific eligibility and restrictions of its records.

Portia must expose or derive information such as:

* record class;
* school-year scope;
* active or closed status;
* continuing intervention status;
* archive eligibility;
* retention trigger;
* retention deadline;
* legal or records hold;
* destruction eligibility;
* and cross-year continuation references.

Closing the active school year in Core must not itself:

* archive Portia data;
* close active interventions;
* destroy Portia records;
* move Portia files;
* or remove legal holds.

Sunset orchestrates lifecycle actions. Portia governs the meaning and eligibility of Portia records.

## Cross-Module References

Portia will use durable, typed, module-qualified references for relationships with external module records.

A conceptual external reference must identify:

```text
owning module
+ record type
+ durable record identifier
+ applicable contract version
+ relationship purpose
```

A reference may also include:

* a descriptive display label;
* the related Portia Event, Support, Intervention, or Outcome;
* availability status;
* the date last validated;
* and correction or supersession history.

The originating module remains authoritative for the referenced record.

Portia remains authoritative for:

* why the record is related to Portia;
* the permitted use of that record within Portia;
* any Portia-specific contextual statement;
* any Portia-specific classification;
* and any Portia-owned decision.

Portia must not copy an entire sibling-module record merely to create a relationship.

A missing, unavailable, or incompatible external record must be represented explicitly. Portia must not fabricate substitute data.

## Dependency Direction

Paper Data Suite domain modules should consume shared infrastructure from Core:

```text
pds-scoreform -> pds-core
pds-quillan   -> pds-core
pds-concord   -> pds-core
pds-portia    -> pds-core
```

Portia must not depend directly on ScoreForm, Quillan, Concord, Sunset, or future sibling modules merely to obtain:

* workspace resolution;
* class identity;
* roster identity;
* student identity;
* identifier validation;
* standards;
* PDS2 parsing;
* route registration;
* scan retention;
* safe path construction;
* shared navigation;
* or local file opening.

Foundational Portia workflows must remain usable without sibling modules being installed.

Optional adapters may later provide conveniences such as:

* validating an external record;
* displaying a supported label;
* opening module-owned evidence;
* reading a documented public export;
* or checking contract compatibility.

An adapter must:

* use a documented public contract;
* remain optional;
* preserve the owning module;
* avoid mutating the external record;
* and handle absence or incompatibility explicitly.

## PDS2 and Paper Workflows

Portia does not require PDS2 for ordinary digital records.

A digitally entered Event, Account, Referral, Support, Intervention, or Outcome does not receive a route registration merely because it is a Portia record.

PDS2 applies only when Portia generates a physical page expected to return through scanning.

Possible future Portia paper records may include:

* student reflection pages;
* check-in/check-out forms;
* support-plan data sheets;
* classroom observation forms;
* family response forms;
* restorative preparation forms;
* or student self-monitoring pages.

For each returned physical page, Portia must follow the shared Core model:

```text
Portia-owned page record
→ immutable Core route registration
→ canonical PDS2 locator
→ rendered physical page
→ retained source scan
→ Core dispatch
→ Portia-owned routed record
```

The Portia-owned page record must exist before the PDS2 QR is rendered.

The QR payload must not directly encode:

* student identity;
* behavior category;
* policy allegation;
* Determination;
* support tier;
* intervention status;
* disability information;
* family information;
* or other sensitive semantic data.

Those meanings remain in the Portia-owned authoritative record resolved through the route registration.

## Data-Flow Prohibitions

Portia must not automatically:

* convert behavior records into academic Scores or Grades;
* change ScoreForm attempts or results;
* change Quillan ratings or feedback;
* change Concord Scores;
* add records to a student portfolio;
* alter lesson or unit plans;
* archive or destroy sibling-module records;
* infer intent, remorse, honesty, diagnosis, trauma, or behavioral function;
* create punishment recommendations;
* escalate discipline solely from record counts;
* or expose protected Portia history to another module without an explicit authorized purpose.

## Consequences

### Positive Consequences

* Portia has a clear purpose within Paper Data Suite.
* Shared infrastructure retains one owner.
* Portia can focus on behavior-support workflows rather than duplicating workspace, roster, standards, or routing code.
* ScoreForm, Quillan, and Concord retain their established domains.
* Future modules can integrate with Portia without absorbing sensitive behavior records indiscriminately.
* Academic grading remains separate from behavior documentation.
* Portfolio inclusion becomes deliberate rather than automatic.
* Planning context can be linked without sharing unnecessary behavior history.
* Sunset can orchestrate archival without becoming responsible for interpreting Portia records.
* PDS2 remains a page-routing contract rather than a container for sensitive behavior semantics.
* Cross-module references preserve provenance and ownership.
* Optional sibling integrations do not make foundational Portia workflows fragile.

### Costs and Tradeoffs

* Some teacher workflows may span several modules.
* Durable external references require documented public record identities and compatibility contracts.
* Portia must handle unavailable or incompatible external records.
* The boundary between collaborative performance and behavior support may require explicit user guidance.
* Portfolio and reporting integrations require purpose-specific projections rather than unrestricted access.
* Sunset integration requires a future Portia archival contract.
* Portia cannot rely on sibling internal APIs for implementation convenience.
* Shared infrastructure gaps may require future Core decisions before some Portia capabilities can be implemented.
* Organization-wide and cross-class behavior records may exceed the current class-scoped Core workspace model.

## Alternatives Considered

### Alternative A: Implement Portia inside Core

Rejected.

Core should own shared infrastructure, not behavior-specific domain workflows.

Placing Portia inside Core would make Core responsible for:

* Events;
* Accounts;
* behavior Classifications;
* Determinations;
* support plans;
* interventions;
* follow-up;
* behavior privacy;
* and behavior reporting.

This would weaken Core’s module-neutral role and make every PDS installation carry Portia-specific assumptions.

### Alternative B: Make Portia a standalone application without Core

Rejected.

Portia would need to recreate:

* workspace configuration;
* class and roster management;
* identifier validation;
* student display identity;
* active school-year state;
* safe paths;
* standards references;
* PDS2 routing;
* scan retention;
* and shared navigation.

That would duplicate infrastructure and create incompatible suite conventions.

### Alternative C: Make Portia depend directly on ScoreForm, Quillan, or Concord

Rejected.

Sibling modules are domain applications, not shared infrastructure providers.

Direct dependencies would:

* increase installation and testing complexity;
* encourage access through private implementation code;
* transfer ownership ambiguously;
* and make foundational Portia workflows depend on unrelated modules.

### Alternative D: Make Portia the general Paper Data Suite integration hub

Rejected.

Portia’s cross-cutting context does not make it the owner of:

* academic results;
* written submissions;
* collaborative Activities;
* planning;
* portfolios;
* Grades;
* or archival.

A general integration hub would broaden Portia beyond behavior support and expose sensitive records unnecessarily.

### Alternative E: Copy sibling-module records into Portia

Rejected.

Copying would create:

* conflicting authoritative versions;
* stale data;
* unclear correction responsibility;
* duplicated sensitive information;
* and weak provenance.

Portia should retain typed references and Portia-specific relationship records instead.

### Alternative F: Allow behavior records to feed academic Grades automatically

Rejected.

Behavior-support data and academic-performance evidence answer different questions.

Automatic conversion would:

* conflate conduct with learning;
* amplify bias;
* undermine grading validity;
* and violate the established separation of evidence, scoring, grading, and reporting across the suite.

### Alternative G: Place all Portia records automatically in the student portfolio

Rejected.

A portfolio is a curated presentation context. Portia contains records that may be disputed, sensitive, temporary, restricted, or inappropriate for educational presentation.

Only an explicit portfolio-safe projection may be shared.

## Implementation Constraints

This ADR establishes ownership and integration boundaries. It does not define the final Portia schema, database model, CLI, menu, or deployment architecture.

Future implementation must nevertheless preserve these invariants:

1. Portia depends on Core for shared suite infrastructure.
2. Core does not depend on Portia.
3. Portia owns the behavior-support lifecycle.
4. Accounts, Classifications, Hypotheses, Determinations, Responses, Supports, and Outcomes remain distinguishable.
5. ScoreForm, Quillan, and Concord records remain owned by their originating modules.
6. Cross-module relationships use durable typed references.
7. Sibling modules are not mandatory runtime dependencies.
8. External records are not copied merely to create a relationship.
9. Portia data do not automatically become academic Scores or Grades.
10. Portfolio inclusion requires an explicit authorized projection.
11. Planning context may be referenced without granting unrestricted behavior-history access.
12. Sunset orchestrates archival while Portia determines Portia-record eligibility.
13. Digital Portia records do not receive PDS2 routes unless they correspond to expected returned paper pages.
14. Sensitive Portia semantics are never encoded directly in PDS2 payloads.
15. Automated educational, behavioral, moral, diagnostic, or disciplinary judgment remains prohibited.

## Follow-Up Decisions

Separate decisions or specifications should address:

* the initial teacher-local versus institution-wide Portia deployment boundary;
* class-scoped versus organization-scoped student identity;
* storage of cross-class and schoolwide Portia records;
* the initial Portia domain model;
* the serialized typed external-reference contract;
* local permissions and privacy controls;
* multi-student Event storage and redaction;
* Portia archival and retention integration with Sunset;
* portfolio-safe projections;
* reporting-module behavior-summary contracts;
* instructional-planning context references;
* and Portia paper-page and PDS2 requirements.

## Notes

This ADR establishes Portia’s suite role and ownership boundaries.

It does not decide whether Portia’s first implementation will be:

* teacher-local and classroom-focused; or
* institution-wide and multi-user.

That deployment decision must be addressed separately because it affects identity, storage, authentication, authorization, audit, concurrency, privacy, and operational infrastructure.
