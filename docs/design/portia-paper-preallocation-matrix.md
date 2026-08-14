# Portia Paper Preallocation Matrix

Status: Issue #20 working design, pre-ADR. ADR 0016 remains the final authority for accepted contract names and lifecycle policy.

## Governing rule

Printing may render an already legitimate canonical Portia record or may render a non-domain Capture Batch/Page Target prepared for later capture. Printing alone must never manufacture a behavior-domain fact.

```text
blank printed form ≠ canonical record
registered route ≠ returned page
returned page ≠ interpreted value
machine candidate ≠ human-confirmed value
```

For blank/new-record workflows, the Portia Capture Batch supplies Core-compatible `work_id`; the Page Target supplies the exact pre-print Portia target. Existing Event or Support Process context, when known, is preserved separately through exact historical references rather than replacing the Capture Batch work identity.

## Registration-before-render sequence

A printable PDS2 page must follow this order:

1. create or resolve a legitimate Capture Batch;
2. create the Page Target with exact purpose, template/layout/capture identity, page-local entry keys, and any exact existing context;
3. create the Core `RouteRegistration` targeting the exact Page Target;
4. verify active route module/class/work/target agreement and supported exact target contract version;
5. verify that the render template/layout fingerprint matches the Page Target;
6. render privacy-minimized PDS2 QR/fallback text;
7. print.

Failure before step 6 means no QR may be rendered. Failure after route registration does not justify deleting or rewriting Core route history; the route/target may be retired or invalidated under the accepted lifecycle policy while history is preserved.

## Template/layout immutability

The Page Target records the exact historical:

```text
template_id
template_version
layout_version
capture_spec_version
layout_fingerprint
page_role
page_ordinal
entry keys
capture mode
```

After route registration or printing, these are historical interpretation semantics. A later template release must not reinterpret an old returned page. Material correction requires preserved history and, where the correction changes the printable/interpretive meaning, a new Page Target and route.

`entry_key` is page-local. It identifies a stable expected entry/slot location; it is not a student ID, Event ID, or canonical record ID, and a configured slot does not mean returned content exists in that slot.

## Page purpose vocabulary

Version 1 uses the closed descriptive vocabulary:

```text
new_event_capture
event_evidence_capture
support_process_evidence_capture
follow_up_capture
implementation_capture
fidelity_capture
reentry_capture
repair_capture
multi_entry_event_capture
other
```

`other` requires bounded explanatory detail. Purpose is routing/interpretation intent only:

```text
new_event_capture ≠ Event occurred
implementation_capture ≠ Implementation occurred
fidelity_capture ≠ as_planned
repair_capture ≠ Repair completed
```

## Per-family preallocation and materialization matrix

Legend:

- **Render existing**: an independently legitimate existing record may be rendered when authorization/privacy rules permit.
- **Preallocate for printing**: whether a canonical record of that family may be created solely so a blank form can be printed. The answer is **No** for every domain family.
- **Proposal after interpretation**: whether reviewed page interpretation may draft/propose that family when the page actually contains relevant source material.
- **Review before active use**: paper-derived substantive current-use data must pass the human-review gate required by that family; judgment-bearing families remain human-attributed.

| Portia family | Render existing? | Preallocate canonical record only for printing? | Proposal after returned-page interpretation? | Human review before active/current use? | Automation must never infer |
|---|---|---|---|---|---|
| Event | Yes | No | Yes | Yes | occurrence, participants, fault, severity, policy meaning |
| Event Participant / Role | Yes | No | Yes | Yes | person identity from position/name proximity; participation, role, responsibility, fault |
| Account | Yes | No | Yes | Yes | source identity, verbatim certainty, firsthand status, credibility, truth |
| Observation | Yes | No | Yes | Yes | observer identity, directness, behavioral interpretation, finding, risk/severity |
| Review | Yes | No | Only as a proposal preserving a human-completed review source | Yes; reviewer attribution required | review conclusion, credibility, sufficiency, judgment from machine confidence |
| Classification | Yes | No | Only as a proposal preserving an explicit human classification source | Yes; classifier attribution required | classification from marks/text, fault, intent, severity |
| Hypothesis | Yes | No | Only as a proposal preserving an explicit human hypothesis source | Yes; human attribution required | behavioral function, diagnosis, causal explanation, “winning” hypothesis |
| Determination | Yes | No | Only as a proposal preserving an explicit human/authority-source assertion | Yes; authority and reviewer rules still apply | finding, policy conclusion, fault, sanction basis, institutional authority |
| Response | Yes | No | Yes, if the source documents an action/attempt | Yes | action occurred from a printed plan, appropriateness, effectiveness, punishment choice |
| Communication | Yes | No | Yes, if the source documents a communication act/attempt | Yes | draft/generated message as sent, delivery/read status, consent, participation, engagement |
| Support Process / Participant | Yes | No | Yes | Yes | process existence from a template, membership, provider/recipient status, legal authority |
| Support Need / Goal | Yes | No | Yes | Yes | diagnosis, deficit, eligibility, goal attainment, compliance target, progress |
| Support | Yes | No | Yes | Yes | support delivery, authorization, likely effectiveness, recipient participation |
| Intervention | Yes | No | Yes | Yes | implementation, fidelity, effectiveness, tier/diagnosis, automatic recommendation |
| Implementation | Yes | No | Yes, only when returned source documents an actual bounded occurrence/attempt | Yes | implementation from schedule/checklist existence, completion, success/effectiveness |
| Fidelity | Yes | No | Only as a proposal preserving a human evaluator’s source/marks | Yes; evaluator attribution required | fidelity judgment from detected marks, provider competence, effectiveness |
| Follow-Up | Yes | No | Yes, when returned source documents a follow-up action/check | Yes | completion from schedule/date passage, favorable result, closure |
| Outcome | Yes | No | Only as a proposal preserving an attributable human evaluation | Yes; evaluator attribution required | improvement, effectiveness, recurrence failure, causation, goal status from counts alone |
| Reentry | Yes | No | Yes | Yes | readiness/safety/clearance, return/completion from date passage, compliance/rehabilitation |
| Repair | Yes | No | Yes | Yes | participation/agreement from contact, remorse, forgiveness, relationship restoration, fault |

## Existing-work pages

An existing Event or Support Process page does not use that domain work as the Core PDS2 `work_id` for the capture operation. The capture route remains owned by the Capture Batch. The Page Target separately preserves exact historical Portia context:

```text
existing_work_context
or
existing_record_context
```

Exact context never silently follows a later corrected Event, adapted plan, successor Support Process, migrated work root, ownership correction, or other successor representation. A human may later choose to use returned information in relation to a successor, but the print-time context remains historical source truth.

## Multi-entry sheets

A multi-entry Page Target declares stable page-local `entry_keys`. Returned content remains 0..N independently reviewable entries:

- blank slot: no domain record;
- unreadable slot: unresolved/unreadable state, not blank;
- ambiguous mark/text: candidate uncertainty, not a domain value;
- accepted entry: preserves exact Page Record + entry key provenance;
- one rejected/unresolved entry does not invalidate other entries on the same physical page;
- reprocessing an already accepted page/entry must not create duplicate canonical records.

The Page Target defines expected slots, not detected content. Returned-entry state belongs to later interpretation/proposal/review contracts.

## Boundaries preserved

Core continues to own PDS2 locator, route registration/resolution, retained-source identity/history, and generic dispatch. Portia owns Page Target semantics and downstream interpretation/review. Raw scan bytes are not duplicated into Portia JSON.

Quillan remains the long-form writing authority, ScoreForm remains the academic OMR/scoring authority, Meridian receives no automatic academic result from behavior capture, and Vitrine receives no automatic publication. Full privacy/redaction/export/retention policy remains Issue #21.
