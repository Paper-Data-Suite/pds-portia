# Teacher-Reference Exports

Portia v0.2 supports one bounded deliberate local export: an HTML teacher-reference artifact for one exact current `event@2` or `support_process@1` work item.

## Purpose and scope

The supported projection purposes are:

- `teacher_current`: one exact current work item for local teacher reference;
- `participant_specific`: the exact focal participant's applicable view of that same work.

Neither purpose creates a student-global dossier. Related work is not recursively folded into the export. A participant-specific export remains teacher-reference output; it is not student-facing delivery.

## What an export means

An export is a local teacher reference. Generation does not mean that the artifact was disclosed, delivered, received, filed, accepted by a school system, or promoted to an official institutional record. Portia does not add recipient selection, email, upload, LMS/SIS delivery, or disclosure logging in Issue #51.

## Closed privacy projection

The export policy is versioned and fail-closed. Exact contract/version and field rules decide whether content is included, withheld, unavailable, absent, or requires manual review. Unknown or unsupported contracts do not silently migrate or widen the surface.

Free text or other content whose safe inclusion cannot be established mechanically is presented for explicit manual review. The only resolutions are:

- include the exact reviewed source content;
- omit it.

Portia does not automatically paraphrase, summarize, sanitize, or rewrite manual-review content.

## Identity and enrichment boundaries

Roster identity remains `class_id + student_id`. Display names are presentation aids only. Participant display snapshots embedded in canonical Portia records may be projected when the policy allows them, but the export path does not live-dereference Core rosters for hidden enrichment.

The Actor Directory and Contact Point records are not generic export-enrichment sources. Issue #51 does not turn recurring actor/contact data into ordinary teacher-reference output.

## Source inventory

Every materially contributing Portia source is represented by an exact canonical identity, source role, SHA-256 digest, and byte length in `export_source_inventory@1`. Fully withheld sources do not enter the inventory merely because they were considered. Correction and disagreement context retain truthful context roles.

## Deterministic HTML

The first production representation is HTML only:

- renderer identity: `portia_deliberate_export_artifact_v1`;
- format: `html`;
- media type: `text/html`;
- UTF-8 bytes with deterministic line endings;
- no JavaScript;
- no remote/network asset dependency;
- no hidden raw canonical JSON dump.

The artifact includes a teacher-reference disclaimer and does not expose absolute workspace paths or operation internals.

## Preview and confirmation

Preparation is read-only. It freezes the exact scope, policy, authorization, projection/manual-review decisions, source inventory, rendered artifact bytes, export identity, operation identity, output paths, `deliberate_export@1` candidate, `operation_journal@4` plan, and `operation_lock@3` candidate into one deterministic preparation fingerprint.

The teacher reviews the actual outgoing HTML. Export requires the explicit uppercase confirmation `EXPORT`. Pressing Enter, Back, Main Menu, Quit, or cancelling before confirmation does not authorize or create the export.

## Final revalidation

Execution never silently calls preparation again and substitutes current state. Immediately before the first durable write, Portia revalidates the exact reviewed state, including source bytes/currentness, policy, authorization, manual-review binding, inventory, renderer output, candidate provenance, operation plan, and output-path preflight.

A material change returns a stale-preparation failure and requires a new preview.

## Persistence and recovery

Confirmed exports use the accepted Issue #88 coordinated-operation path only:

1. `operation_journal@4` for `generate_deliberate_export`;
2. exact `operation_lock@3` with deliberate-export scope;
3. exclusive creation of `artifact.html`;
4. exclusive creation of `export.json`;
5. exact reserved committed journal revision;
6. completed finalization without rewriting provenance.

Issue #51 does not add a second export writer.

If execution stops after the artifact becomes durable, recovery uses the preserved exact staged provenance candidate. It never regenerates provenance from current live work merely because the process restarted. Contradictory or missing recovery evidence fails closed.

## Immutable history

Each new export receives a new opaque `pexp_` identity. Ordinary UI has no overwrite action and does not infer the newest export to be current, official, active, or best.

History is read-only and work-scoped. It verifies the artifact path is workspace-contained, the artifact exists, byte length and SHA-256 agree with provenance, and the exact committed journal reference remains valid. History distinguishes:

- available and verified;
- artifact missing;
- artifact mismatch;
- operation recovery required;
- provenance invalid.

A failed history verification never silently regenerates historical bytes.

## Teacher-menu entry point

Issue #51 preserves the Issue #50 eight-task top-level menu. Export is contextual:

```text
View Timeline
-> choose exact roster student
-> open exact current Event / Support Process
-> Export this work for teacher reference
   or Export this student's view of this work
-> resolve manual review if required
-> preview exact outgoing HTML
-> EXPORT
-> verified result / history
```

Prior export history is available from the same selected-work context.
