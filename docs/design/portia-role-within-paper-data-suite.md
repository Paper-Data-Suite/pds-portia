# Portia's Role Within Paper Data Suite
## Overall assessment

Portia should be a **peer domain module**, not the suite’s central student database and not an extension of Core.

Its distinctive responsibility is:

> **Documenting behavior-related events, perspectives, institutional decisions, supports, interventions, follow-up, and outcomes while preserving context, provenance, privacy, and human judgment.**

That places it alongside the existing evidence-producing modules, but on a different axis:

| Module                              | Primary domain                                                                                        |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Core**                            | Shared workspace, identity, roster, standards, routing, scan provenance, and module infrastructure    |
| **ScoreForm**                       | Machine-readable selected-response evidence and scoring                                               |
| **Quillan**                         | Written-response evidence, teacher review, standards-based feedback, and assignment-local reporting   |
| **Concord**                         | Collaborative activities, groups, artifacts, evidence review, moderation, and criterion-level scoring |
| **Portia**                          | Behavior and support events, accounts, referrals, determinations, interventions, and outcomes         |
| **Future grading/reporting module** | Academic score aggregation, weighting, grade calculation, and formal academic reporting               |
| **Future portfolio module**         | Curated longitudinal student work, feedback, and approved evidence                                    |
| **Future planning module**          | Units, lessons, assignments, objectives, sequencing, and instructional context                        |
| **Sunset**                          | Year-to-year archival, lifecycle transition, and preservation of module-owned data                    |

Portia should be **cross-cutting without becoming an integration hub**. It may reference classes, lessons, assignments, activities, work samples, and records from other modules, but those modules remain authoritative for their own data.

---

# 1. What Paper Data Suite currently is

The repositories establish a consistent architectural identity for Paper Data Suite:

* local-first;
* teacher-controlled;
* file- and contract-oriented;
* modular;
* human-reviewed;
* conservative about overwriting or deleting records;
* explicit about source evidence versus later judgment;
* and opposed to automated educational judgment.

Core provides the common substrate. It owns identifier validation, PDS2 routing, module-qualified work paths, module profiles and dispatch, scan-source retention, failure and resolution records, workspace conventions, shared rosters, standards, and related infrastructure. It expressly leaves scoring, tagging, PDF layout, reporting, and other domain logic in the modules.

The shared workspace is a local filesystem root, commonly `~/Paper Data Suite` or a user-selected location such as OneDrive. Core creates shared baseline locations but does not create module-owned records until a module explicitly does so.

The shared class structure is now:

```text
classes/<class_id>/
  roster.csv
  class.json
  modules/
    <module_id>/
      work/
        <work_id>/
          routes/
          <module-owned records>
```

Core owns the class, module, work, and route-registration paths; each module owns the meaning of its `work_id` and everything else beneath that work root. Core intentionally does not define a universal assignment or student-submission structure.

That distinction is critical for Portia: it should use Core infrastructure, but its event, account, intervention, and determination schemas must remain Portia-owned.

---

# 2. Current module workflows

## Core

Core is the suite’s infrastructure and configuration module rather than a classroom-production workflow.

The current teacher-facing `core` menu primarily exposes:

* standards management;
* workspace status and configuration;
* validation and setup;
* shared navigation conventions.

Core also owns shared roster APIs, class folders, student display identity, active school-year state, PDS2 routing, retained scans, and immutable failure/append-only resolution records. Modules are expected to wrap those APIs in their own branded workflows.

Core’s active school-year state is deliberately modest. Opening or closing a year does not archive, move, summarize, or rewrite module data. That is the natural opening for Sunset.

### Core’s role for Portia

Core should provide Portia with:

* workspace resolution;
* active school year;
* class and roster loading;
* student display identity;
* identifier validation;
* module-qualified paths;
* shared navigation;
* standards references where appropriate;
* local file opening;
* PDS2 routing if Portia eventually produces scannable paper;
* retained-source and scan-review infrastructure for such pages.

Core should **not** own:

* behavior categories;
* event records;
* support plans;
* referrals;
* determinations;
* intervention data;
* privacy classifications specific to behavior records;
* Portia reports;
* Portia retention rules.

---

## ScoreForm

ScoreForm is the suite’s OMR and selected-response module. Its implemented workflow includes:

1. Create or manage a roster.
2. Create an assignment and answer key.
3. Optionally align questions to Core standards.
4. Generate personalized or class-packet answer sheets.
5. Scan or manually enter responses.
6. Score attempts.
7. route and retain scan evidence;
8. review scan failures;
9. inspect assignment-local results.

Its menu is organized around Assignment Management, Roster Management, Workspace Settings, and Help. Assignment Management includes creation, editing, sheet generation, scan scoring, plain-paper result entry, result viewing, QR decoding, and scan review.

ScoreForm treats each attempt as a module-owned record and deliberately does not decide which attempt becomes the official grade. Its assignment result viewer is read-only and reports attempts without making gradebook policy decisions.

ScoreForm is currently in a significant Core 0.5/PDS2 transition. Its active umbrella issue replaces QR payloads that directly encode student and assignment semantics with durable answer-sheet-page records and Core route registrations.

### ScoreForm’s relationship to Portia

Portia must not implement bubble detection, machine-readable checklists, answer keys, or OMR scoring.

There are nevertheless plausible integrations. A future teacher could use ScoreForm for:

* a structured self-monitoring form;
* a check-in/check-out instrument;
* a brief classroom-environment survey;
* a structured observation checklist;
* a student-selected support preference form.

The resulting ScoreForm record would remain a ScoreForm record. Portia could create a typed reference to it and, after human review, use it as one data source in an intervention or support review.

It must **not** automatically convert a ScoreForm total into:

* a behavior score;
* a discipline finding;
* a tier placement;
* a function determination;
* an intervention escalation.

That follows the same ownership pattern Concord has already accepted: an external module record may become referenced evidence, but a separate teacher judgment remains necessary.

---

## Quillan

Quillan is a local-first written-response review system. Its canonical workflow is:

```text
student evidence
→ review unit
→ Focus Standard
→ teacher judgment
→ feedback and assignment-local reporting
```

It explicitly does not read student writing, infer scores, calculate grades, or generate feedback.

The teacher workflow is:

1. Create a writing assignment.
2. Select a Core standards profile and Focus Standards.
3. Generate printable response pages.
4. Route scanned paper responses or create a plain-paper submission.
5. Assemble evidence into a student submission.
6. Review minimum requirements.
7. Review units and Focus Standard observations.
8. Enter overall ratings.
9. Compose feedback.
10. Export student feedback and assignment summaries.

Quillan stores teacher-entered observations, ratings, rationales, and feedback rather than inferring them.

Like ScoreForm, Quillan still has a pending PDS2 and module-qualified-storage migration. Its current routing assumes a student-oriented PDS1 page; issue #329 will introduce response-page records and PDS2 routing.

### Quillan’s relationship to Portia

Portia should natively support concise student and family statements. A student should not need a separate module simply to write:

> I left because I thought I was being sent to the office.

Quillan becomes appropriate when the writing itself is a substantial instructional or review artifact, such as:

* an extended student reflection;
* a reentry narrative;
* a written account of a conflict;
* a detailed self-assessment;
* a longer family-submitted statement;
* a reflective assignment associated with a support process.

Portia could reference that Quillan submission as a student-authored statement or related reflection. It should not copy Quillan’s review record or use a Quillan writing rating as proof of remorse, honesty, compliance, or behavioral improvement.

The Portia research explicitly warns against turning reflection into forced confession or treating refusal or silence as evidence of guilt.

---

## Concord

Concord is currently a design and architecture repository rather than an executable module. Its initial architecture, thirteen ADRs, representative packet models, domain model, and Core integration specification are complete; the next phase is conceptual contracts and serialized examples.

Its intended domain is paper-first evidence generated during collaborative classroom activities:

* Activities and Sessions;
* Groups and memberships;
* roles and responsibilities;
* packets, artifacts, and pages;
* authors and subjects;
* evidence review;
* moderation;
* criteria and scoring scales;
* criterion-level teacher-approved scores.

Concord deliberately separates evidence, review, moderation, scoring, grading, and reporting. Grading and reporting remain outside Concord.

### Concord’s relationship to Portia

This will require a particularly careful boundary because both modules may record observations about students.

The decisive question should be:

> **What is the record for?**

A record belongs primarily to **Concord** when it exists to evaluate or understand collaborative work:

* whether a student fulfilled a project role;
* whether a group coordinated dependencies;
* who contributed to a product;
* whether peer evidence may support a criterion score;
* whether a collaborative artifact is correctly attributed.

A record belongs primarily to **Portia** when it exists to document or address behavior, safety, access, participation, harm, support, or intervention:

* a classroom concern;
* repeated leaving of an assigned area;
* a conflict requiring support or repair;
* implementation of a break plan;
* a request for assistance;
* a behavior-related referral;
* a reentry process;
* intervention fidelity or outcome.

A Concord Activity, Session, Group, or Artifact may provide context for a Portia event. Portia should link to that record using a durable typed external reference rather than duplicate Concord’s activity or group model.

For example:

```text
Portia event:
Student left the laboratory at 10:24 after the group reassigned testing roles.

Context reference:
concord / session / lab_session_03

Related group:
concord / group / testing_team_b
```

The Portia event does not become a Concord score, and Concord’s group score does not become a Portia determination.

This mirrors Concord’s existing rule that sibling-module records remain authoritative and may be linked without transferring ownership.

---

## Portia

Portia currently consists of foundational research and one proposed ADR. Its README describes it only as behavior management and tracking for Paper Data Suite.

The research gives it a much more precise role:

> Portia should be a student-support and decision-documentation system, not a digital punishment ledger.

Its recommended record progression is:

```text
Event
→ Accounts and Observations
→ Review and Classification
→ Determination
→ Immediate Responses
→ Supports and Interventions
→ Follow-Up and Outcomes
```

ADR 0001 is strongly consistent with the rest of the suite. It keeps:

* events separate from findings;
* accounts separate by author;
* classifications separate from determinations;
* hypotheses explicitly tentative;
* immediate responses separate from supports;
* supports separate from outcomes;
* audit history append-only while allowing the active record to be corrected.

That is not merely a Portia-specific preference. It continues an existing PDS design philosophy:

* Core retains immutable source scans and appends resolution events.
* ScoreForm preserves attempts and source provenance.
* Quillan distinguishes evidence from teacher-entered judgment and treats exports as derived artifacts.
* Concord distinguishes evidence, review, moderation, scores, grades, and reports.
* Portia distinguishes observations, interpretations, findings, actions, and outcomes.

Portia therefore fits the suite unusually well at the conceptual level.

---

# 3. Portia’s proper boundary

## Portia should own

Portia should own the complete behavior-support lifecycle:

* neutral events;
* direct observations and reported accounts;
* positive observations;
* referrals and support requests;
* preliminary and reviewed classifications;
* formal determinations where Portia is authorized to hold them;
* immediate responses;
* classroom-managed concerns;
* administrative referrals;
* support and intervention plans;
* implementation and fidelity records;
* outcomes and follow-up;
* reentry and repair;
* student and family statements;
* communication records;
* amendment and disagreement records;
* behavior-specific terminology and local definitions;
* Portia-specific equity and data-quality reports;
* Portia record sensitivity;
* Portia-specific retention classifications.

## Portia should not own

Portia should not become responsible for:

* shared roster parsing;
* workspace configuration;
* standards libraries;
* academic assignments;
* academic grading;
* OMR processing;
* written-response evaluation;
* collaborative-performance scoring;
* lesson planning;
* portfolio curation;
* universal archival;
* SIS discipline records unless that is an explicit future scope decision;
* IEP evaluation records;
* clinical or counseling notes;
* threat assessment;
* mandated reporting;
* Title IX investigations;
* continuous surveillance;
* predictive behavior scoring.

The research already identifies formal discipline adjudication, special-education FBA/BIP ownership, crisis workflows, threat assessment, bullying, and mandated reporting as unresolved product-boundary questions.

---

# 4. How Portia should fit the planned modules

## Sunset

Sunset and Portia need a stronger relationship than Sunset will have with most ordinary assessment data.

Closing the Core school year currently changes only the shared state file; it does not archive or move any module records. That means Sunset should be the lifecycle orchestrator, while each module supplies module-specific archival rules.

For Portia, Sunset must not simply move an entire folder because a school year ended. Portia records may include:

* active interventions continuing into the next year;
* unresolved amendment requests;
* pending access requests;
* legal or investigation holds;
* retention dates based on record class;
* multi-year support plans;
* records requiring secure destruction at different times;
* audit records with longer retention than ordinary observations.

Portia should eventually expose an archival contract containing at least:

```text
record identifier
record class
school-year scope
operational status
archive eligibility
retention trigger
retention deadline
legal-hold status
destruction eligibility
cross-year continuation reference
```

Sunset should orchestrate archival; Portia should determine the semantic eligibility and restrictions for its records.

---

## Grading and reporting module

The future grading module should consume academic scores from:

* ScoreForm;
* Quillan;
* Concord;
* teacher-entered academic records.

It should **not** treat Portia data as grade inputs by default.

Portia records such as:

* number of referrals;
* tier;
* support participation;
* compliance;
* removals;
* family response;
* incident count;
* intervention status

must not become grade penalties or academic score modifiers.

A formal reporting system may consume authorized Portia summaries for a separate behavior, intervention, attendance-impact, or support report. That is categorically different from grade calculation.

Concord has already articulated this distinction: grades may combine scores from several modules, but grading and reporting remain separate from evidence review and scoring.

The future reporting module will therefore need typed input classes:

```text
academic score
academic grade
feedback
portfolio artifact
behavior-support summary
discipline report
equity aggregate
```

It should not flatten all of them into generic “student results.”

---

## Portfolio module

The portfolio module is the greatest risk for accidental overexposure of Portia data.

A student portfolio may appropriately contain:

* a student-selected reflection;
* a documented strength;
* progress toward a self-selected goal;
* successful use of a replacement skill;
* a restorative or reparative artifact voluntarily chosen for inclusion;
* a teacher-approved growth statement;
* evidence of self-advocacy.

It should not automatically contain:

* referrals;
* allegations;
* incident histories;
* disputed accounts;
* discipline determinations;
* FBA hypotheses;
* sensitive intervention plans;
* family communications;
* disability-related information;
* safety records;
* demographic equity data.

Portia should eventually offer an explicitly curated **portfolio-safe projection**, not grant the portfolio module general access to Portia records.

That projection should be:

* opt-in;
* purpose-specific;
* separately permissioned;
* student-reviewable;
* revocable where policy permits;
* free of unrelated incident history.

The portfolio module should store a durable reference or approved snapshot rather than copy an entire Portia record graph.

---

## Unit, lesson, and assignment planning module

The planning module and Portia can provide useful context to one another without exchanging judgment.

The planning module should own:

* instructional sequence;
* lesson and assignment IDs;
* activity descriptions;
* timing;
* grouping plans;
* materials;
* instructional supports;
* differentiation;
* intended routines and expectations.

Portia may reference those records to capture context:

```text
lesson
assignment
activity
grouping structure
instructional phase
task type
scheduled support
```

That would help answer legitimate questions such as:

* Do concerns cluster during one type of transition?
* Was the assigned accommodation or support available?
* Are referrals concentrated during a particular task structure?
* Did a change in lesson design reduce the recorded difficulty?
* Was a student removed during core instruction or independent practice?

The research emphasizes that activity, instructional conditions, antecedents, location, and adult response are necessary context, and that analytics should examine system behavior as well as student behavior.

The planning module should not receive individual Portia history merely to suggest lesson plans. Portia should provide only the minimum authorized support information or aggregate patterns required for planning.

---

# 5. A likely Portia teacher workflow

To match existing PDS interaction patterns, an initial Portia menu might eventually be conceptually organized as:

```text
Portia

1. Record and Review Events
2. Student Supports
3. Follow-Up and Work Queues
4. Reports and Patterns
5. Roster Management
6. Workspace Settings
7. Help
Q. Quit
```

The actual Portia workflow should resemble:

## Classroom-managed concern

```text
Select class/student
→ record objective account
→ record immediate response
→ view authorized active support instructions
→ add optional follow-up or request support
→ review outcome
→ close or continue
```

## Office- or team-managed referral

```text
Create event and account
→ create referral
→ gather additional accounts
→ review preliminary classification
→ record authorized determination
→ link immediate response
→ assign support/reentry/follow-up
→ document outcome and closure rationale
```

## Intervention workflow

```text
Define target and baseline
→ define prevention and replacement skill
→ assign implementation responsibilities
→ collect fidelity and outcome data
→ review student/family perspective
→ continue, modify, fade, intensify, or end
```

These flows come directly from the research recommendations.

As with ScoreForm and Quillan, Portia should likely have:

* a guided teacher menu;
* a stable direct CLI for scripting and diagnostics;
* safe staged edits;
* explicit confirmation before consequential writes;
* read-only status commands;
* derived reports rather than report files acting as canonical data.

---

# 6. The largest architectural issue Portia exposes

Portia’s research scope is substantially more institutional than the current suite architecture.

The existing modules are primarily local, teacher-controlled applications. Quillan explicitly excludes cloud sync and hosted collaboration, and Core resolves a local workspace.

Portia’s research, however, calls for:

* reporters;

* classroom educators;

* administrators;

* support-team members;

* special educators;

* counselors;

* restorative facilitators;

* family liaisons;

* data analysts;

* records officers;

* students and guardians;

* auditors;

* vendor support;

* role-, attribute-, and field-level authorization;

* SSO and MFA;

* tenant isolation;

* access auditing;

* break-glass access;

* disclosure and amendment processes.

Those are not simply new Portia menu items. They imply a different operational platform:

* multiple authenticated users;
* concurrent access;
* authorization enforcement;
* centralized audit;
* secure data sharing;
* records-request workflows;
* possibly a server or database;
* organizational rather than single-teacher control.

## The necessary scope decision

Before implementation, Portia needs a formal decision between two initial product models.

### Model A: Teacher-local Portia

Portia begins as a classroom behavior and student-support tracker for one teacher using the existing local PDS workspace.

It could support:

* current classes and rosters;
* objective observations;
* positive behavior;
* classroom responses;
* teacher-owned support plans;
* follow-ups;
* student statements;
* local reports;
* privacy-conscious exports.

It would not claim to be:

* the school’s formal discipline system;
* a multi-user administrative workflow;
* a family portal;
* a district equity platform;
* an IEP/FBA system of record;
* a FERPA request-management system.

This is the most natural fit with current PDS architecture.

### Model B: Institutional Portia

Portia becomes a school- or district-level behavior management platform.

That would require significant new shared infrastructure, likely extending beyond Portia:

* organization and school identity;
* user and staff identity;
* authentication;
* role and scope authorization;
* concurrent storage;
* transaction and conflict handling;
* centralized audit;
* secure disclosure;
* student/family access;
* tenant configuration;
* data-retention enforcement;
* institutional deployment and backup.

That infrastructure belongs either in an expanded Core/platform layer or in a separately defined PDS service layer—not duplicated privately inside Portia.

My recommendation is to define **Teacher-local Portia as the first implementation boundary**, while retaining the institutional requirements as the long-range architecture. Otherwise Portia risks forcing a wholesale platform rewrite before its foundational behavior model has been tested.

---

# 7. A second major gap: student identity and storage scope

Core’s canonical student identity currently exists within a class roster. The shared contract states that `student_id` is canonical within a `Roster`, while module data is normally organized beneath a class.

Portia records, however, may be:

* schoolwide;
* cross-class;
* hallway or cafeteria events;
* transportation events;
* multi-student events involving several classes;
* support plans used by several teachers;
* longitudinal across school years.

This means Portia cannot safely assume that every meaningful record belongs to exactly one class work root.

Using a fabricated class such as `schoolwide` would obscure the real domain and repeat the sort of synthetic-identity problem that Concord rejected for groups and multi-subject evidence.

Before the full data model is fixed, the suite needs to decide whether:

1. Portia v1 is strictly class-scoped;
2. Core gains a durable school- or organization-level student identity;
3. Portia owns a cross-roster identity-resolution layer;
4. Core gains organization-scoped module work roots in addition to class-scoped work roots.

This should be treated as a foundational cross-repository decision, not hidden inside Portia path helpers.

---

# 8. PDS2 and paper workflows

Portia does not need QR routing merely because it is a PDS module.

PDS2 identifies an expected physical page route. It does not identify a student, assignment, author, subject, or final semantic record.

A digital observation or intervention entered directly into Portia should not receive a route registration.

PDS2 becomes relevant only if Portia produces returned paper such as:

* student reflection pages;
* check-in/check-out cards;
* family response forms;
* classroom observation forms;
* behavior-plan data sheets;
* restorative preparation forms;
* self-monitoring sheets.

For every such returned page, Portia should follow the current Core contract:

```text
create Portia page record
→ create immutable Core route registration
→ render PDS2 locator
→ retain source scan
→ dispatch to Portia
→ link routed page to the relevant Portia record
```

It should not encode student behavior, category, intervention, or sensitive information directly in the QR.

---

# 9. Final placement

I would describe Portia’s position in the suite this way:

> **Portia is Paper Data Suite’s contextual behavior-support and response module. It records what was observed, who said what, what the institution decided, what support was provided, and what happened afterward. It may reference instructional and assessment context from other modules, but it neither evaluates academic work nor calculates grades.**

The module relationships should be:

```text
                         pds-core
        shared identity, workspace, standards, routing
                              │
       ┌──────────────┬───────┼────────┬───────────────┐
       │              │       │        │               │
  ScoreForm       Quillan  Concord   Portia       Planning
 selected         written  collaborative behavior/ instructional
 response         work     evidence      support     intent
       │              │       │        │               │
       └──────────────┴───────┴────────┴───────────────┘
                              │
                    typed public references
                              │
             ┌────────────────┴───────────────┐
             │                                │
      Grading/Reporting                  Portfolio
      academic aggregation              curated evidence

                              │
                           Sunset
                 archival and lifecycle orchestration
```

Portia’s records may illuminate the conditions in which learning occurs, but they should never silently become academic scores, portfolio content, planning judgments, or permanent student labels.

The most appropriate next foundational issue is not yet the complete Portia data model. It is a **scope and deployment decision** establishing whether the first Portia release is teacher-local/classroom-focused or institution-wide. That decision determines identity, storage, permissions, reporting, and nearly every subsequent architecture choice.

## Recommended Follow-Up Issues

The following issues should carry Portia from suite-level positioning into explicit domain contracts and an implementable first release.

They are listed in a recommended dependency order. Issue numbers and branch names should be assigned when each ticket is created.

### 1. Define Portia Identity and Storage Scope

**Suggested title:** Define Portia identity, ownership scope, and workspace storage

**Purpose:** Determine how Portia records are identified and stored within the Paper Data Suite workspace.

This issue should decide:

* whether Portia’s initial writable records are strictly class-scoped;
* the meaning of Portia `work_id`;
* the canonical class-scoped Portia work root;
* how one student is referenced across several class rosters;
* how multi-student Events are represented;
* whether one Event may involve students from several classes;
* how cross-class, hallway, cafeteria, transportation, extracurricular, and schoolwide Events are represented;
* whether Core eventually requires school- or organization-scoped student identity;
* whether Core requires module work roots outside a class;
* and how records continue across school years.

The design must not use fabricated identities such as:

* a synthetic `schoolwide` class;
* a Group identifier stored as a student identifier;
* duplicate student records created solely for Portia;
* or an arbitrary class selected to own a cross-class Event.

**Expected deliverables:**

* identity and storage design document;
* one or more ADRs;
* canonical path examples;
* identifier and ownership invariants;
* Core follow-up requirements, if any.

This issue should precede the serialized Portia domain model because storage and reference scope affect nearly every domain record.

---

### 2. Define the Initial Portia Domain Model

**Suggested title:** Define Portia’s initial behavior-support domain model

**Purpose:** Convert the research and foundational ADRs into a coherent conceptual model.

The model should include at least:

* Event;
* Event Participant;
* Account or Observation;
* Quotation;
* Concern;
* Referral;
* Classification;
* Hypothesis;
* Determination;
* Immediate Response;
* Support;
* Intervention;
* Implementation Record;
* Fidelity Record;
* Follow-Up;
* Outcome;
* Communication;
* Reentry;
* Repair;
* Amendment;
* Statement of Disagreement;
* External Reference;
* and relevant status, correction, and supersession relationships.

The issue should define:

* ownership;
* identifiers;
* required and optional fields;
* cardinalities;
* lifecycle states;
* provenance;
* author attribution;
* correction and supersession;
* multi-student behavior;
* privacy considerations;
* and major invariants.

The domain model must preserve ADR 0001’s distinction among observation, interpretation, classification, hypothesis, determination, response, support, and outcome.

**Expected deliverables:**

* conceptual domain-model document;
* relationship diagrams or structured relationship tables;
* representative record lifecycles;
* explicit invariants;
* unresolved contract questions.

This issue should define concepts before final JSON schemas or Python models are implemented.

---

### 3. Specify Typed Cross-Module References

**Suggested title:** Define Portia’s typed cross-module reference contract

**Purpose:** Establish how Portia references records owned by Core, ScoreForm, Quillan, Concord, Sunset, and future modules without copying or assuming ownership of those records.

The contract should define a module-qualified external reference containing, as applicable:

```text
owning module
record type
durable record identifier
contract version
relationship purpose
availability status
display label
creation provenance
last validation time
correction or supersession history
```

It should address references to:

* Core classes, students, standards, and school-year state;
* ScoreForm assignments and results;
* Quillan assignments, submissions, reviews, and reflections;
* Concord Activities, Sessions, Groups, Artifacts, and Scores;
* future Units, Lessons, and Assignments;
* future portfolio projections;
* future grading or report records;
* and Sunset archive operations.

The issue should define behavior when:

* the sibling module is not installed;
* the record no longer exists;
* the record has been superseded;
* its contract version is unsupported;
* access to the record is not authorized;
* or the reference cannot be validated.

Portia must not fabricate substitute content or copy an entire sibling record merely to preserve a link.

**Expected deliverables:**

* conceptual external-reference contract;
* relationship-purpose vocabulary;
* valid and invalid examples;
* compatibility and availability behavior;
* ADR if the contract establishes suite-wide precedent.

---

### 4. Define Teacher-Local Privacy, Authorship, and Record History

**Suggested title:** Define Portia’s teacher-local privacy and record-history model

**Purpose:** Specify the safeguards that can be implemented honestly within ADR 0003’s teacher-local deployment boundary.

This issue should distinguish among:

* configured teacher identity;
* unauthenticated local authorship;
* attributed student and family statements;
* Portia record-change history;
* institutional authentication;
* institutional access auditing;
* and formal disclosure logging.

It should define:

* how authors are represented;
* what can and cannot be claimed about author identity;
* append-oriented change history;
* authorized correction;
* supersession;
* statements of disagreement;
* sensitive-field minimization;
* local filesystem and synchronized-folder risks;
* deliberate export;
* redaction;
* multi-student export behavior;
* overwrite protection;
* and derived-export provenance.

The resulting design must not imply that:

* a name typed into configuration is authenticated identity;
* filesystem access establishes a professional role;
* hiding a menu option is authorization;
* or a local edit log records every person who viewed a file.

**Expected deliverables:**

* local privacy and authorship specification;
* record-history and correction rules;
* export and redaction requirements;
* user-facing limitation language;
* candidate acceptance tests.

---

### 5. Define Portia’s Minimum Viable Teacher Workflow

**Suggested title:** Define the minimum viable teacher workflow for Portia

**Purpose:** Select a first end-to-end workflow that delivers support-oriented value without becoming a negative-only incident log.

The minimum viable workflow should likely include:

```text
select class and student
→ create objective or positive observation
→ record immediate response
→ add or reference a classroom support
→ assign optional follow-up
→ record outcome
→ close, continue, or modify
```

The issue should decide:

* the initial menu structure;
* rapid-capture requirements;
* draft and autosave expectations;
* required versus optional fields;
* positive-observation workflow;
* active-support display;
* follow-up queues;
* closure requirements;
* teacher-local reports;
* and direct CLI versus guided-menu responsibilities.

The first workflow must not:

* foreground lifetime negative history during entry;
* require a guessed motive;
* automatically escalate from count;
* treat unknown values as zero;
* allow support plans containing only punishments;
* or permit closure when required follow-up remains incomplete.

**Expected deliverables:**

* workflow specification;
* menu or interaction map;
* minimum record set;
* error and cancellation behavior;
* acceptance scenarios;
* explicit exclusions from the first implementation.

This issue should produce an implementation-ready vertical slice rather than a complete Portia application plan.

---

### 6. Define Portia and Sunset Archival Responsibilities

**Suggested title:** Define the Portia–Sunset archival and retention contract

**Purpose:** Establish how Portia records participate in school-year archival without making Sunset responsible for interpreting behavior-support semantics.

The contract should distinguish:

* operational closure;
* school-year closure;
* archive eligibility;
* continued active support;
* retention;
* destruction eligibility;
* legal or records hold;
* amendment or access-request hold;
* and cross-year continuation.

Portia should expose or derive:

* record class;
* school-year scope;
* operational status;
* archive eligibility;
* retention trigger;
* retention deadline;
* hold status;
* destruction eligibility;
* and successor or continuation references.

Sunset should orchestrate approved lifecycle actions. Portia should govern the semantic eligibility of Portia records.

The issue should also address:

* active interventions spanning school years;
* unresolved follow-ups;
* multi-year support histories;
* archived corrections;
* retained audit history;
* backup expiration;
* and validation after archival.

**Expected deliverables:**

* Portia archival contract;
* lifecycle-state mapping;
* Portia/Sunset ownership matrix;
* archival and continuation examples;
* candidate acceptance tests.

This work may begin before Sunset is implemented, but it should avoid prescribing Sunset’s complete internal architecture.

---

### 7. Decide Portia’s Initial Paper and PDS2 Scope

**Suggested title:** Decide whether Portia v1 includes returned-paper and PDS2 workflows

**Purpose:** Determine whether the first Portia release needs to generate or route any physical paper pages.

Candidate Portia paper artifacts include:

* student reflection pages;
* check-in/check-out forms;
* self-monitoring pages;
* classroom observation forms;
* support-plan data sheets;
* family response forms;
* and restorative preparation forms.

The issue should determine whether each candidate belongs in:

* Portia;
* ScoreForm;
* Quillan;
* another module;
* or outside the initial release.

For any Portia-owned returned page, the design must require:

```text
Portia page record
→ Core route registration
→ canonical PDS2 locator
→ rendered page
→ retained source scan
→ Core dispatch
→ Portia-owned routed evidence
```

The QR must not encode behavior categories, determinations, disability information, family details, support status, or other sensitive semantic information.

**Expected deliverables:**

* include/defer decision for paper workflows;
* ownership analysis for each proposed form;
* Portia page-record requirements if included;
* PDS2 integration requirements;
* non-goals and privacy constraints.

If paper is deferred, the issue should record that clearly so the first implementation does not carry unnecessary routing complexity.

---

### 8. Define the Future Institutional Platform Boundary

**Suggested title:** Define requirements for a future institution-wide Portia platform

**Purpose:** Preserve the long-term requirements identified in Issue #1 without placing incomplete imitations of institutional controls into the teacher-local implementation.

The issue should define shared platform requirements for:

* organization and school identity;
* authenticated users;
* role- and attribute-based authorization;
* field-level sensitivity;
* concurrent records;
* centralized audit;
* secure APIs;
* student and family access;
* amendment and disclosure workflows;
* tenant configuration;
* retention enforcement;
* legal holds;
* de-identification;
* institutional reporting;
* backup and disaster recovery;
* and migration from teacher-local workspaces.

It should determine which capabilities belong in:

* an expanded `pds-core`;
* a separate Paper Data Suite service or platform layer;
* Portia itself;
* or external institutional systems.

**Expected deliverables:**

* institutional platform requirements document;
* ownership and dependency analysis;
* local-to-institutional migration principles;
* explicit non-equivalences between local and institutional controls;
* recommended future ADRs.

This issue should not block the teacher-local Portia release, but local implementation choices should remain compatible with its eventual requirements where practical.

## Recommended Sequence

The recommended order is:

1. identity and storage scope;
2. initial domain model;
3. typed cross-module references;
4. teacher-local privacy and record history;
5. minimum viable teacher workflow;
6. Portia–Sunset archival contract;
7. paper and PDS2 scope;
8. future institutional platform boundary.

Some design work may overlap, but implementation should not begin until identity/storage and the initial domain model are sufficiently settled.

## Scope of Issue #2

Issue #2 establishes Portia’s role within Paper Data Suite and identifies the next architecture work.

It does not require all follow-up issues to be created or completed before Issue #2 closes. The list above provides focused, traceable next work that can be converted into GitHub issues as development proceeds.
