# ADR 0021: Reconcile Classroom Observation Paper Capture with the Released Runtime

- **Status:** Accepted
- **Date:** 2026-10-11
- **Decision owners:** Portia maintainers
- **Related issue:** `#56 — Reconcile accepted paper/import contracts with the released v0.2 runtime`
- **Umbrella:** `#55 — C. v0.3.0 — Add reviewed paper/import intake and privacy-minimized downstream publication`
- **Builds on:** ADR 0005, ADR 0011, ADR 0016
- **Preserves:** immutable published v1 capture schemas; neutral Event semantics; Event/Support Process ownership of canonical Observation; Core ownership of PDS2 routing/retained source

## Context

Issue #20 and ADR 0016 accepted the generic paper-capture architecture before
Portia had an executable released runtime. Portia v0.2.0 later made the domain
ownership boundary executable:

```text
Observation@2
→ Event
or
→ Support Process
```

and explicitly preserved:

```text
portia.observation.no_fake_event_requirement
```

The first concrete v0.3 paper workflow is now a **Daily Classroom Observation**
form used once per class/session. The teacher may write:

```text
lesson objective
lesson steps / activities
bounded session context
positive observations
general / neutral observations
concerning observations
```

One returned sheet may mention several students and may contain several
unrelated occurrences.

The accepted `page_target@1` purpose vocabulary does not name this workflow,
focused monitoring, or communication capture. Its permanent `other` escape
hatch is not a suitable primary representation for core v0.3 forms.

The question is therefore how to add honest page semantics without:

```text
creating a class-day Event container
creating a standalone behavior dossier
making routine notes canonical before review
pre-entering lesson context digitally merely to print the form
or widening Observation ownership without evidence that the domain model needs it
```

## Decision

### 1. Keep `capture_batch@1`

Issue #56 does not version Capture Batch merely to hold lesson objective or
lesson steps.

Capture Batch remains:

```text
a non-domain operational work root
```

It exists to group and route bounded paper work and to satisfy Core's required
module `work_id`.

It does not become a class-session record, lesson plan, Event, Support Process,
or student dossier.

The teacher may write lesson/session context on the returned paper. Portia does
not require that content to be entered digitally before printing.

### 2. Publish additive `page_target@2`

`page_target@1` remains immutable historical/support authority.

Version 2 preserves all accepted v1 page-target semantics and adds first-class
purposes for the initial v0.3 form surface:

```text
classroom_observation_capture
focused_monitoring_capture
communication_capture
```

Version 2 also adds optional:

```text
entry_layout.context_entry_key
```

`context_entry_key` identifies one page-local entry whose fields provide
page/session source context rather than a student/domain-record identity.

It is a layout locator only.

It does not itself contain:

```text
lesson objective
lesson steps
student identity
behavior classification
severity
risk
```

The exact historical capture specification continues to define the fields
inside that entry.

### 3. Classroom Observation is a multi-entry source page

A `classroom_observation_capture` Page Target requires:

```text
entry_layout.mode = multi_entry
entry_layout.context_entry_key = <declared page-local entry key>
```

and must not prebind an existing Event or Support Process.

A typical logical layout is:

```text
session_context
observation_01
observation_02
...
```

The context entry may contain source fields such as:

```text
session_date
lesson_objective
lesson_steps
context_notes
```

The observation entries remain independently reviewable.

The context entry does not identify a student and does not establish an Event.

### 4. Session-context values are returned-page source context

The values written in the classroom-session context area are not stored in
Capture Batch or Page Target.

They enter the retained-source pipeline with the physical page:

```text
Core retained source
→ Page Record
→ Paper Interpretation source/context candidate
```

`paper_interpretation@1` already supports a declared page-local entry whose
`mapped_record_kind` is omitted. That is sufficient to preserve non-domain
context candidates without pretending they map to a canonical domain family.

Issue #56 does not create a standalone canonical `ClassroomSession`,
`LessonContext`, or `ClassroomObservation` record family.

Unreviewed OCR/handwriting interpretation of session context must not be used as
canonical domain truth. A later Issue #56 slice must reconcile the exact human
confirmation/correction seam for page-level source context before any runtime
workflow relies on those interpreted values for structured analysis.

The raw retained page remains authoritative source provenance regardless.

### 5. Keep `observation@2` ownership unchanged

Issue #56 does not publish `observation@3` merely to make daily notes easier to
store.

A classroom-observation entry is capture-stage source material until the teacher
deliberately chooses a legitimate domain operation.

A reviewed entry may later:

```text
remain source-only / noncanonical

map to an Observation under an existing Event

map to an Observation under an existing Support Process

support creation of a new legitimate neutral Event
and related Event child evidence
```

A new Event is legitimate only when the teacher is actually accepting a bounded
occurrence/interaction/observation period as an Event.

It must never be created merely because:

```text
Core requires a work_id
the page was printed
the page was scanned
an OCR candidate exists
a daily class sheet needs somewhere to put notes
```

### 6. No class-day Event container

Portia will not create one Event for the whole class meeting merely to own all
notes from the Daily Classroom Observation form.

ADR 0005 requires unrelated bounded occurrences to remain distinct even when
they share:

```text
class
participant
category
support need
or perceived pattern
```

A class-day Event container would therefore corrupt Event semantics.

Capture Batch and Page Target are the correct operational containers for the
physical form.

### 7. Event neutrality remains important

ADR 0005 explicitly permits:

```text
positive Events
neutral Events
concerning Events
```

Therefore a positive classroom note may legitimately contribute to a new Event
when the teacher chooses to preserve that bounded occurrence canonically.

That does not make every positive note an Event.

The teacher may keep most routine notes at the capture/source layer and
materialize only information with continuing instructional/support value.

### 8. Positive / general / concern cues are capture aids only

A Classroom Observation form may use teacher-facing cues such as:

```text
positive
general
concern
```

Those cues are capture/review aids defined by the form/capture specification.

They are not canonical Observation fields and do not mean:

```text
Classification
severity
risk
misconduct
culpability
Outcome
student trait
```

Portia retains one neutral Observation family.

### 9. Focused monitoring and communication are first-class page purposes

`focused_monitoring_capture` identifies a page intended for bounded observable
measurement/tally information.

It may be tied to an existing Support Process or Event when that context already
exists legitimately.

`communication_capture` identifies a page intended to record communication acts
or attempts.

It may likewise carry exact existing work context when appropriate.

Neither purpose creates or proves the corresponding canonical record.

### 10. Existing interpretation contracts remain usable at this seam

Slice 2 does not version:

```text
paper_interpretation@1
capture_proposal@1
capture_review@1
capture_materialization@1
```

merely because `page_target@2` exists.

`paper_interpretation@1` can already preserve:

```text
exact layout snapshot
entry keys
field keys
candidate / blank / unreadable / ambiguous states
optional mapped record kind
```

The newly distinguished context entry intentionally has no required mapped
record kind.

Later Issue #56 slices must separately determine whether proposal/review or
materialization contracts need additive successors for:

```text
page-context confirmation
split/defer/rescan workflow actions
multi-record coordinated materialization
new Event + child evidence choreography
```

No conclusion about those later seams is smuggled into this ADR.

## Compatibility

Published contracts remain immutable:

```text
capture_batch@1
page_target@1
observation@2
paper_interpretation@1
capture_proposal@1
capture_review@1
capture_materialization@1
```

Issue #56 publishes:

```text
page_target@2
```

using the existing:

```text
ptgt_
```

identifier family.

No new opaque identifier is required.

At this slice, `page_target@2` is catalogued and explicitly remains
`deferred_v0_3 / modelled=false` until a later Issue #56 runtime-promotion slice
adds the executable model and validation surface.

## Rejected alternatives

### Put lesson objective and lesson steps in Capture Batch

Rejected because the teacher's intended workflow is to write those values on
paper. Requiring digital pre-entry adds friction and confuses operational batch
identity with returned source content.

### Use `page_purpose = other` permanently

Rejected because Daily Classroom Observation, focused monitoring, and
communication capture are core v0.3 workflows and deserve stable mechanical
purpose identity.

### Create one Event per class meeting

Rejected because unrelated observations would be collapsed into one Event
solely because they share a class/time block.

### Make every handwritten note a canonical Observation

Rejected because paper source collection is intentionally broader than
canonical domain materialization.

### Add standalone Observation ownership immediately

Rejected because existing Event/Support Process ownership remains coherent when
capture-stage notes are allowed to remain noncanonical and only selected notes
are deliberately materialized.

### Add positive/negative Observation domain families

Rejected because ADR 0011 deliberately uses one neutral Observation model and
forbids valence from becoming finding/severity/risk semantics.

## Consequences

### Positive

- the central Daily Classroom Observation workflow has first-class page meaning;
- teachers can write lesson context on paper rather than pre-enter it;
- unrelated class-day notes are not forced into one Event;
- `Observation@2` remains semantically stable;
- positive observations remain first-class without creating a valence ontology;
- Capture Batch stays a clean non-domain routing root;
- Page Target v1 history remains immutable;
- later review/materialization work begins from explicit source/domain boundaries.

### Costs

- page-level session context needs an explicit later human-confirmation decision;
- some classroom notes may remain source-only rather than canonical;
- new Event + child-evidence materialization still requires later coordinated
  choreography;
- Page Target v2 requires runtime promotion before executable form generation.
