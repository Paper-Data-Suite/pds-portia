# ADR 0004: Define Portia Identity, Ownership, and Storage

* **Status:** Accepted
* **Date:** 2026-07-16
* **Decision owners:** Portia maintainers
* **Related issue:** [#4 — Portia identity, ownership scope, and workspace storage](https://github.com/Paper-Data-Suite/pds-portia/issues/4)
* **Related design:** [`docs/design/portia-identity-and-storage.md`](../design/portia-identity-and-storage.md)
* **Related decisions:**

  * [`0002-define-portia-module-boundaries.md`](0002-define-portia-module-boundaries.md)
  * [`0003-adopt-teacher-local-initial-deployment.md`](0003-adopt-teacher-local-initial-deployment.md)

## Context

ADR 0003 establishes Portia’s initial deployment as teacher-local, classroom-focused, and based on the existing Paper Data Suite workspace.

It also defers the exact identity and storage rules for:

* cross-class Events;
* multi-student Events;
* supports spanning several Events or classes;
* non-classroom contexts;
* recurring non-roster participants;
* and records continuing across school years.

Portia must resolve those questions before finalizing its Event, Account, Support, Intervention, Follow-Up, Outcome, and related schemas.

Paper Data Suite currently provides class-qualified module work storage:

```text
classes/<class_id>/modules/<module_id>/work/<work_id>/
```

Core also provides:

* workspace resolution;
* class discovery;
* class metadata;
* roster loading;
* roster-local student identifiers;
* active school-year state;
* shared identifier validation;
* module-qualified work references;
* PDS2 routing;
* route-registration storage;
* and safe class-scoped module paths.

Core does not currently provide:

* a durable workspace identifier;
* workspace-wide student identity;
* automatic reconciliation of students across rosters;
* a workspace-scoped module-work contract;
* cross-teacher identity;
* organization identity;
* or institution-wide person records.

Portia must therefore use the existing Core contracts without fabricating identity or ownership.

At the same time, Portia cannot treat every behavior-support record as merely one class-student file.

A Portia workflow may involve:

* several students in one class;
* students from several classes taught by the same teacher;
* a parent or guardian;
* a counselor;
* an administrator;
* another recurring collaborator;
* several Events connected to one Support Process;
* or an Event occurring outside the physical classroom while the teacher remains responsible for one scheduled class activity.

The design must distinguish:

* canonical storage ownership;
* instructional context;
* Event participants;
* roster identity;
* recurring non-roster identity;
* workflow relationships;
* and derived navigation or reporting views.

## Decision

Portia will use a **class-owned workflow model with explicit cross-class references and one limited teacher-workspace Actor Directory**.

The principal decisions are:

1. Core remains authoritative for workspace selection, classes, rosters, and roster-local student identity.
2. A Portia student reference is the pair `class_id + student_id`.
3. Portia does not automatically merge students across rosters.
4. One Portia `work_id` identifies one independently managed, explicitly typed top-level workflow object.
5. Initial Portia work kinds are Event and Support Process.
6. Every Event and Support Process has exactly one owning class and one canonical class-scoped work root.
7. Event ownership normally follows the Event’s temporal and instructional context.
8. An Event may link students from other classes taught by the same teacher.
9. Cross-class links never duplicate or relocate canonical work.
10. Recurring non-roster people may receive Portia-owned Actor IDs in a workspace-scoped Actor Directory.
11. Incidental or unidentified people may remain descriptive without receiving Actor IDs.
12. Each relationship has one canonical record; reverse links and histories are derived.
13. Cross-year continuation uses linked successor work rather than moving or indefinitely extending one class-owned record.
14. No blocking change to `pds-core` is required for Portia v1.

## Core Identity Authority

Core remains authoritative for:

```text
workspace selection
class_id
class metadata
roster contents
student_id within one roster
active school-year context
module-qualified work paths
PDS2 routing
route registrations
```

Portia must not create competing canonical:

* class records;
* rosters;
* student records;
* school-year settings;
* or route registries.

A Core `student_id` is canonical only within its source roster unless a future Core contract explicitly establishes a broader scope.

The same textual `student_id` appearing in two rosters must not be assumed to represent the same person.

## Student References

A durable Portia student reference consists of:

```text
class_id + student_id
```

For example:

```json
{
  "class_id": "english10_p2",
  "student_id": "1001"
}
```

The `class_id` identifies the authoritative source roster.

The `student_id` identifies the student within that roster.

Persisted Portia references should also include a nonauthoritative display snapshot for historical readability:

```json
{
  "student_ref": {
    "class_id": "english10_p2",
    "student_id": "1001"
  },
  "display_snapshot": {
    "display_name": "Jane Doe"
  }
}
```

The roster-qualified reference is identity.

The display snapshot is not identity and must not be used to:

* locate a student;
* merge roster entries;
* repair a reference;
* or reassign historical work.

Roster changes do not silently rewrite historical display snapshots.

## Cross-Roster Student Identity

Portia v1 does not introduce a workspace-wide student registry.

When one real-world student appears in several rosters, each roster entry remains a separate Core identity:

```text
english10_p2 + 1001
journalism_p5 + 1001
```

Portia may display histories involving several explicitly selected roster references, but those references do not become one new canonical identity.

Portia must not merge roster identities automatically based on:

* matching student IDs;
* matching names;
* matching email addresses;
* similar metadata;
* or teacher inference not explicitly recorded through a later reviewed identity-linking contract.

The initial design therefore preserves source identity while permitting explicit cross-class participation.

## Portia Work Identity

One Portia `work_id` identifies one independently managed, explicitly typed top-level workflow object.

The initial work kinds are:

```text
event
support_process
```

The `work_id` is also the durable identifier of the root Event or Support Process.

Recommended formats are:

```text
evt_<opaque-random-id>
sup_<opaque-random-id>
```

A `work_id` must be:

* opaque;
* stable;
* generated by Portia;
* validated before use in a path;
* unique within the Portia module’s applicable scope;
* and free of student names, behavior labels, or other sensitive semantics.

A Portia work root must explicitly declare its work kind.

Portia `work_id` does not identify:

* one student;
* one class year;
* one student dossier;
* one behavior category;
* one printed page;
* one Account;
* one Follow-Up;
* or one generated report.

Child records receive their own durable identifiers.

Examples include:

```text
ep_<opaque-id>      Event Participant
acct_<opaque-id>    Account
obs_<opaque-id>     Observation
resp_<opaque-id>    Response
fu_<opaque-id>      Follow-Up
out_<opaque-id>     Outcome
comm_<opaque-id>    Communication
rel_<opaque-id>     Work relationship
actr_<opaque-id>    Actor
chg_<opaque-id>     History entry
```

## Canonical Class-Owned Work Storage

Events and Support Processes are stored beneath the Core class-qualified module-work root:

```text
classes/<class_id>/modules/portia/work/<work_id>/
```

For example:

```text
classes/english10_p2/modules/portia/work/evt_7f3a9c.../
classes/english10_p2/modules/portia/work/sup_16b85d.../
```

Each work root contains one canonical root manifest:

```text
work.json
```

A representative work layout is:

```text
classes/<class_id>/modules/portia/work/<work_id>/
  work.json

  records/
    <record_kind>/
      <record_id>.json

  attachments/
    <attachment_id>/
      attachment.json
      content.<extension>

  pages/
    <page_id>.json

  routes/
    <route_id>.json

  history/
    <change_id>.json

  derived/
    <rebuildable views>

  exports/
    <generated artifacts>
```

Directories may be created only when required.

Each canonical record has exactly one authoritative location.

Portia must not copy canonical records into:

* another class;
* another student directory;
* another work root;
* a dashboard;
* a timeline;
* an index;
* or an export

merely to make the record discoverable.

## Event Ownership

Every Event has exactly one owning class.

The owning class establishes:

* canonical storage;
* the Event’s Core `ModuleWorkRef`;
* its PDS2 routing context;
* its primary instructional context;
* and its original class and school-year provenance.

Ownership normally follows the real temporal and instructional context of the Event.

The presumptive rule is:

> When an Event occurs during a scheduled class period, the class being taught at that time owns the Event.

For example, an Event occurring during English 10 Period 2 belongs to that English 10 class even when one participant is linked from another roster.

The presence of cross-class participants does not divide or transfer ownership.

Legitimate instructional ownership may also arise from:

* a class field trip;
* a class assembly;
* an online class meeting;
* a class-specific activity;
* or another teacher-supervised activity clearly conducted on behalf of one class.

For a PDS2-routed paper artifact, the owning class is the class encoded in the validated route.

For a digitally created Event, the teacher selects or confirms the owning class.

Portia may use an Event timestamp and an available teacher schedule to suggest or validate the selection.

Schedule-based assistance must not replace teacher confirmation.

When no scheduled class matches, the teacher must select a class only when the Event honestly belongs to that instructional relationship.

An Event without a legitimate teacher-class context falls outside the normal Portia v1 model.

Portia must not solve that case by inventing a synthetic class or assigning ownership solely for storage convenience.

## Cross-Class Event Participants

One Event may include students from several Core rosters in the same teacher’s workspace.

The Event remains stored beneath one owning class.

Each student participant uses a complete roster-qualified reference:

```json
{
  "participant_id": "ep_a18c...",
  "student_ref": {
    "class_id": "english10_p5",
    "student_id": "2047"
  }
}
```

For example:

```text
Owning class:
english10_p2

Participants:
english10_p2 + 1001
english10_p2 + 1014
english10_p5 + 2047
```

The canonical Event remains:

```text
classes/english10_p2/modules/portia/work/<event_id>/
```

Portia must not:

* create another Event under `english10_p5`;
* copy the Event Participant into a second canonical Event;
* move the Event because another roster contributes a participant;
* select an arbitrary “primary student”;
* or create a synthetic cross-class roster.

Cross-class participant linking must be an explicit teacher-reviewed operation.

The menu and CLI should permit the teacher to:

1. select another class;
2. select a student from that class’s valid roster;
3. review the roster-qualified identity;
4. select or confirm the participant relationship;
5. and confirm the link.

Portia must validate the referenced class and roster before writing.

## Support Process Ownership

Every Support Process also has exactly one owning class and one canonical work root.

A Support Process may:

* exist independently of one specific Event;
* link to several Events;
* reference Events owned by another class in the same teacher workspace;
* reference students through roster-qualified identities;
* and involve recurring non-roster Actors.

The owning class represents the principal instructional context in which the teacher is managing the support.

A cross-class Event link does not move either work item.

Each side retains its original class ownership and storage location.

## Recurring Non-Roster Actors

Recurring non-roster people may receive durable Portia Actor records.

Examples include:

* parents and guardians;
* counselors;
* administrators;
* case managers;
* paraprofessionals;
* school psychologists;
* social workers;
* nurses;
* coaches;
* and other recurring collaborators.

Actor identity uses an opaque Portia-owned identifier:

```text
actr_<opaque-random-id>
```

An Actor record may contain:

```json
{
  "record_type": "portia_actor",
  "actor_id": "actr_8f31...",
  "display_name": "Maria Smith",
  "actor_type": "family_member",
  "role_labels": [
    "parent"
  ],
  "status": "active"
}
```

An Actor identifies the reusable person.

It does not permanently define that person’s role in every workflow.

Work-specific roles remain contextual relationship data, such as:

```text
Account source
family contact
consulted counselor
Support participant
Communication recipient
Follow-Up assignee
```

Relationships such as `parent_of`, `counselor_for`, or `administrator_reviewing` must be explicit.

Portia must not infer them from:

* matching last names;
* prior communications;
* email addresses;
* titles;
* or repeated appearances.

Roster students continue to use roster-qualified student references and must not be duplicated as Actors.

## Actor Directory Storage

Because the same Actor may participate in work across several classes, Portia will maintain one limited workspace-scoped Actor Directory:

```text
<PDS workspace>/
  portia/
    actors/
      <actor_id>.json

    history/
      actors/
        <change_id>.json

    derived/
      <rebuildable actor indexes>
```

This directory is:

* Portia-owned;
* local to one selected teacher workspace;
* limited to reusable non-roster people;
* and separate from class-owned Events and Support Processes.

It is not:

* a school directory;
* a district directory;
* an employee directory;
* a student-information system;
* an authenticated user directory;
* or an institutionally authoritative identity service.

Portia must implement focused safe-path helpers for this directory using the resolved Core workspace root and shared identifier validation.

Core does not need to introduce a generic workspace-module root solely for Portia v1.

## Incidental and Unidentified People

Not every person mentioned in Portia requires a durable Actor record.

Incidental, unidentified, anonymous, or one-time people may remain descriptive:

```json
{
  "source_type": "external_person",
  "source_role": "student_from_another_teacher",
  "display_label": "Unidentified student",
  "actor_id": null
}
```

Portia must not create:

* a fabricated student;
* a temporary roster entry;
* an invented `student_id`;
* a synthetic class;
* or an automatic Actor record

merely to satisfy a schema.

Creating an Actor from a descriptive person requires a deliberate reviewed operation.

## Canonical Relationships

Each relationship has one canonical record.

A relationship should normally be stored with the work item that creates, manages, or gives meaning to that relationship.

For example, when a Support Process is created in response to two Events, the Support Process owns the canonical links:

```text
Support Process S -> Event A
Support Process S -> Event B
```

The Event work roots do not store independently editable reverse copies.

A relationship record identifies the complete source and target work identities:

```json
{
  "record_kind": "work_relationship",
  "record_id": "rel_72a1...",
  "source": {
    "module_id": "portia",
    "class_id": "english10_p2",
    "work_id": "sup_16b85d...",
    "work_kind": "support_process"
  },
  "target": {
    "module_id": "portia",
    "class_id": "english10_p5",
    "work_id": "evt_7f3a9c...",
    "work_kind": "event"
  },
  "relationship": "supported_by_event",
  "status": "active"
}
```

Portia must not infer a relationship merely because records:

* concern the same student;
* occurred near the same time;
* contain similar text;
* or share a Classification.

Relationships require explicit teacher-reviewed creation.

## Derived Views and Indexes

Reverse links, student histories, timelines, dashboards, work queues, summaries, and reports are derived views.

Portia will not create one authoritative student-history file or student dossier.

A student history is generated by locating canonical records associated with one or more explicitly selected roster-qualified references.

A dashboard entry is not an independently editable copy of an Event, Support Process, Follow-Up, or Outcome.

Editing through a dashboard must modify the underlying canonical record through an approved operation.

Portia v1 may build indexes in memory by scanning validated work roots.

Persisted indexes may later be introduced for performance, but they must remain:

* nonauthoritative;
* disposable;
* rebuildable;
* versioned;
* and traceable to canonical records.

A missing or corrupt index must not invalidate otherwise valid work.

## Historical References

Historical student and Actor references include display snapshots.

Updating a current roster or Actor record must not rewrite historical snapshots.

Portia may display both recorded and current values when they differ:

```text
Recorded display: Maria Smith
Current Actor display: Maria Rodriguez
```

The durable reference establishes continuity.

The snapshot preserves what was displayed or known when the record was created.

Unresolved historical references must be reported rather than silently repaired.

## Cross-Year Continuity

An Event retains its original class, occurrence time, and school-year context.

Portia must not move an Event into a later class or school year merely because the student’s current roster changes.

A Support Process should not become one indefinitely mutable record spanning unrelated class and school-year contexts.

When a support continues into a new school year, Portia should create a successor Support Process under the new legitimate owning class and link it explicitly to its predecessor:

```text
sup_<prior-year-id>
  -> succeeded_by
sup_<new-year-id>
```

The prior work remains historically intact.

The successor may reference relevant prior Events and Supports through durable class-qualified work references.

Cross-year history is therefore represented through linked records rather than one permanent student dossier.

Detailed archival, retention, and Sunset behavior remain separate decisions.

## Canonical and Derived Storage

The following are canonical:

* Event `work.json`;
* Support Process `work.json`;
* records beneath `records/`;
* Event Participant records;
* work-relationship records;
* Actor records;
* attachment metadata and retained content;
* Portia page records;
* Core route registrations;
* and append-oriented history records.

The following are derived:

* reverse relationship views;
* student histories;
* timelines;
* dashboards;
* search indexes;
* summaries;
* reports;
* and exports.

Derived data must never become the sole surviving source of a relationship or domain fact.

## Write Integrity

Portia must use staged creation and atomic replacement where supported by the local filesystem.

A new work root must not appear valid until its required root manifest has been completely written and validated.

Portia should:

1. construct and validate the complete record;
2. write through a temporary or staged path;
3. flush and close the staged content;
4. atomically replace the intended file where possible;
5. and record applicable history only as part of a successful operation.

Invalid or incomplete work roots must be reported clearly.

Portia must not silently fabricate missing canonical records from derived views.

## Core Impact

No blocking `pds-core` change is required for Portia v1.

Portia can use existing Core behavior for:

* workspace resolution;
* class discovery;
* class metadata;
* roster loading;
* student-reference validation;
* identifier validation;
* class-qualified module work paths;
* safe work descendants;
* PDS2 routing;
* and route-registration persistence.

Portia owns:

* Event and Support Process identity;
* child-record identity;
* Actor identity;
* canonical domain schemas;
* class-owned work-root validation;
* cross-class participant lookup;
* cross-work relationships;
* the workspace Actor Directory;
* append-oriented change history;
* derived indexes;
* and Portia-specific recovery diagnostics.

A future Core enhancement may define a generic workspace-level module path if several modules independently require one.

Portia should not broaden Core solely to generalize one limited Actor Directory prematurely.

Portia v1 does not require Core to add:

* a workspace ID;
* a school or organization ID;
* workspace-wide student identity;
* cross-roster identity reconciliation;
* institution-wide person records;
* cross-teacher authorization;
* or organization-scoped work roots.

## Supported Portia v1 Cases

Portia v1 supports:

* one-student, one-class Events;
* same-class multi-student Events;
* cross-class Events involving students from the teacher’s own rosters;
* Events outside the physical classroom when one legitimate instructional class owns the activity;
* Events created through validated PDS2 routes;
* independent Support Processes;
* Support Processes linked to several Events;
* cross-class work relationships within one teacher workspace;
* recurring non-roster Actors;
* descriptive one-time or unidentified people;
* historical records after roster changes;
* derived cross-class histories selected by the teacher;
* and linked successor Supports across school years.

## Unsupported Portia v1 Cases

Portia v1 does not support:

* cross-teacher participant lookup;
* schoolwide or district-wide Event ownership;
* institution-wide student dossiers;
* automatic student merging across rosters;
* institution-wide Actor identity;
* synthetic schoolwide classes;
* fabricated students;
* work owned by several classes simultaneously;
* canonical Event duplication across classes;
* independently editable reverse relationships;
* arbitrary class ownership without legitimate instructional context;
* merging independently created teacher workspaces;
* or multi-user institutional case management.

Unsupported cases must fail clearly.

Portia must not silently coerce them into inaccurate class-scoped records.

## Consequences

### Positive Consequences

* Portia can represent multi-student and cross-class Events without duplicating canonical work.
* Class ownership remains grounded in the teacher’s real temporal and instructional context.
* Existing Core work and routing contracts remain usable.
* The design preserves source roster identity rather than inventing workspace-wide student identity.
* Repeated parents, counselors, administrators, and collaborators can be reused efficiently.
* Events, Supports, participant identities, and contextual roles remain distinct.
* Student histories and dashboards remain reconstructable from canonical records.
* Cross-year continuity does not require an indefinite student dossier.
* Files remain locally inspectable and suitable for backup and archive workflows.
* No major Core redesign blocks the initial Portia implementation.
* The design remains consistent with the teacher-local deployment established by ADR 0003.

### Costs and Tradeoffs

* Cross-class lookup requires explicit class selection and validation.
* The teacher may see the same real-world student represented by several roster-qualified references.
* Portia cannot automatically provide one unified longitudinal student identity.
* The Actor Directory introduces one workspace-scoped Portia storage convention outside Core’s class-qualified work helpers.
* Derived histories may require scanning several class work collections.
* Cross-class and cross-year references require more complete identifiers than simple local IDs.
* Moving work to another owning class requires a deliberate provenance-preserving migration rather than editing one field.
* Workspace merge and synchronization remain unsupported.
* Some unsupported Events cannot be recorded honestly within Portia v1.
* A future institutional deployment will require a distinct identity, authorization, and migration architecture.

## Alternatives Considered

### Alternative A: Strictly Class-Scoped Participants

Under this alternative, every Event Participant would have to belong to the Event’s owning class.

Rejected.

This would prevent honest representation of Events involving students from several classes taught by the same teacher.

It would encourage:

* duplicate Events;
* omitted participants;
* synthetic roster entries;
* or inaccurate contextual-only representations.

One owning class is retained, but participant scope may cross the teacher’s rosters.

### Alternative B: Workspace-Scoped Events and Supports

Under this alternative, all canonical Portia work would live beneath one workspace-level Portia root.

Rejected for Portia v1.

This would abandon Core’s established class-qualified module-work contract and require Portia to recreate:

* work discovery;
* class indexing;
* route context;
* school-year context;
* and ownership rules.

Only the limited Actor Directory is workspace-scoped.

### Alternative C: Hybrid Workspace-Canonical and Class-Indexed Work

Under this alternative, Events and Supports would live in a workspace Portia root while class directories contained projections or indexes.

Rejected.

Although this would support cross-class work naturally, it would introduce two navigation layers and a broader workspace-level identity model before Portia requires one.

The selected design obtains cross-class representability through durable references while preserving class-owned canonical work.

### Alternative D: Core-Owned Workspace or Organization Identity

Under this alternative, Core would add workspace-wide students, organization identity, and workspace-scoped module roots before Portia implementation.

Rejected for Portia v1.

The teacher-local product does not require schoolwide or district identity.

Adding these contracts would broaden the entire suite and delay Portia’s foundational domain work.

### Alternative E: One Work Root Per Student

Under this alternative, one `work_id` would represent a student dossier or school-year student record.

Rejected.

This would:

* force unrelated Events into one mutable aggregate;
* complicate multi-student Events;
* obscure shared Event context;
* make correction and audit boundaries unclear;
* encourage permanent behavior profiles;
* and conflict with the support-oriented model established in ADR 0001.

### Alternative F: One Work Root Per Child Record

Under this alternative, every Account, Response, Follow-Up, or Outcome would receive an independent Core work root.

Rejected.

This would fragment one workflow across many directories and make lifecycle, routing, reporting, and provenance unnecessarily difficult.

Child records retain independent IDs within one Event or Support Process work root.

### Alternative G: Store Relationships in Both Directions

Under this alternative, both source and target work would store editable copies of each relationship.

Rejected.

Duplicated links could drift out of sync.

The selected design stores one canonical relationship and derives reverse views.

### Alternative H: Descriptive Non-Roster People Only

Under this alternative, all parents, counselors, administrators, and other non-roster people would be re-entered as free text.

Rejected.

Portia workflows will repeatedly involve the same collaborators.

A limited Actor Directory improves:

* selection;
* consistency;
* attribution;
* reporting;
* and teacher efficiency

without claiming to be an institutional people directory.

### Alternative I: Automatic Cross-Roster Student Merging

Under this alternative, Portia would combine roster entries based on matching IDs, names, or metadata.

Rejected.

Core does not establish workspace-wide student identity, and imported identifiers may collide.

Automatic merging would create unsupported identity claims and unreliable histories.

## Implementation Constraints

Portia implementations must preserve these invariants:

1. Core remains authoritative for class and roster identity.
2. Student identity is always roster-qualified as `class_id + student_id`.
3. Display names never function as durable identifiers.
4. Historical references preserve nonauthoritative display snapshots.
5. Portia does not automatically merge students across rosters.
6. Each Event and Support Process has exactly one owning class.
7. Event ownership normally follows temporal and instructional context.
8. Cross-class participants do not change Event ownership.
9. Cross-class linking is explicit and teacher-reviewed.
10. Every Portia work item has one canonical work root.
11. One `work_id` identifies one typed Event or Support Process.
12. Child records have independent durable IDs.
13. Canonical work is never duplicated merely for lookup or reporting.
14. Recurring non-roster people may use workspace-scoped Actor IDs.
15. Roster students are not duplicated as Actors.
16. Actor identity remains distinct from contextual workflow role.
17. Incidental or unidentified people may remain descriptive.
18. Relationships have one canonical source.
19. Reverse links, student histories, dashboards, and reports are derived.
20. Derived indexes are disposable and rebuildable.
21. Cross-year continuation uses explicit predecessor and successor relationships.
22. Names and sensitive behavior semantics do not appear in identity-bearing paths.
23. Unsupported scopes are rejected rather than silently coerced.
24. No institution-wide identity or authorization is implied.
25. No blocking Core change is required for Portia v1.

## Follow-Up Decisions

Separate ADRs or specifications should define:

* the initial Event and Event Participant schemas;
* the initial Support Process schema;
* Account, Observation, Classification, Response, Follow-Up, and Outcome schemas;
* Actor Directory schema and lifecycle;
* controlled relationship vocabularies;
* local author attribution;
* record amendment and supersession behavior;
* detailed staged-write and recovery behavior;
* teacher schedule representation and ownership suggestions;
* privacy projections for multi-student Events;
* redacted student-specific exports;
* PDS2 page and route contracts;
* typed external-module references;
* Support successor workflows across school years;
* and Sunset archival integration.

## Notes

This decision does not create institution-wide identity.

It defines what Portia can represent honestly inside one teacher-controlled Paper Data Suite workspace.

The design deliberately separates:

```text
where work is stored
whom the work concerns
which class supplied the instructional context
which roster supplied student identity
who participated in the workflow
and where the work can be found
```

Those concepts may coincide in simple Events, but Portia must not collapse them into one `class_id`.

Class-owned canonical work, explicit roster-qualified references, and a limited Actor Directory provide sufficient identity and storage for Portia v1 without forcing a broader Paper Data Suite redesign.
