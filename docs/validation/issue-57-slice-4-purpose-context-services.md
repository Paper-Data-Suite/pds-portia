# Issue #57 — Slice 4: Page purpose and exact domain-context resolution

**Branch:** `57-capture-batch-page-target-services`
**Starting commit:** `ddba5fa864b9cb39b57457d83fd65ad5f0ffab7b`
**Contract authority:** `capture_batch@1`, `page_target@2`, historical `page_target@1`, ADR 0016, ADR 0021, and Issue #56 closeout.

## Scope

`portia.capture.purposes` adds application-level checks for current Page Target
v2 preparation, while `FilePageTargetService.create_or_load` calls the verifier
**under the existing Capture Batch lifecycle lock and before the new page is
exclusively persisted**. This prevents an invalid new page from becoming durable.
Existing immutable Page Target v1/v2 reads and exact retries are not rewritten
or rebound to a successor when the referenced domain work later changes.

The two distinct APIs are:

- `validate_page_purpose(target)` — read-free source/layout/purpose check.
- `resolve_existing_capture_context(target, repository=..., path_guard=...)` —
  exact historical/current existing-work and optional child-record resolution,
  returning `VerifiedExistingCaptureContext` or `None`.

## Accepted purpose behavior

| Purpose | Context | Rule |
| --- | --- | --- |
| `classroom_observation_capture` | None | Multi-entry, declared context entry and a separate observation slot; session values stay on returned paper |
| `focused_monitoring_capture` | Optional Event or Support Process | No inferred score, finding, outcome, or identity |
| `communication_capture` | Optional Event or Support Process | No inferred communication act, recipient, agreement, or receipt |
| `new_event_capture`, `multi_entry_event_capture` | None | Never manufacture an Event simply to route paper |
| `event_evidence_capture` | Required exact Event | Reject Support Process substitution |
| `support_process_evidence_capture` | Required exact Support Process | Reject Event substitution |
| Other accepted v2 purposes | Optional exact reference | Resolve if provided; do not invent a domain record |

All purpose-specific rules are additive *application checks*. Accepted JSON
schemas remain byte-for-byte unchanged. Presentation cues such as positive,
general, and concern are not domain judgments. Page Target fields must never
contain invented lesson/session values.

## Existing context fidelity

Exact `existing_work_context` and the work reference nested in
`existing_record_context` must agree, including the exact contract version.
The context must belong to the page's Core class. The verifier rejects absent,
wrong-version, wrong-kind, or malformed authoritative representations via
`PortiaRepository.load_work`/`load_work_record`. It checks path safety using
Portia's existing managed-root link guard before each read.

There is no migration-following, predecessor substitution, opportunistic
version upgrade, Event fabrication, or write to referenced work. The Capture
Batch remains the PDS2 `work_id`; an Event/Support Process is never silently
substituted as the routing work root. A previously persisted Page Target is a
historical representation, even if the domain work later changes.

## Qualification and boundaries

The focused gate runs changed-file Ruff and mypy before one bounded pytest
set covering Slice 4 plus the affected Slice 3 persistence regression. Avoid
running the full suite until #57's final qualification. An exact-base guarded
apply script and the provided PowerShell block commit and push only after
passing qualification and `git diff --cached --check`.

No Core route registration, QR/PDF rendering, scanning, student matching,
canonical domain materialization, or viewer aliasing is introduced here.
Race-resistant openat-like filesystem protection is reserved for the Issue #57
failure/security slice; existing lexical and observed-link guards are preserved.
