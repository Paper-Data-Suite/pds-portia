# Task-Oriented Teacher Menu

Issue #50 replaces Portia's bootstrap menu scaffold with the production
teacher-facing application surface for v0.2.0. The application layer is
task-oriented, but it continues to delegate identity, lifecycle, persistence,
student-view, attention, integrity, and recovery semantics to the existing
production authorities.

## Eight teacher tasks

The routine teacher model is:

1. **Record Event** — record neutral Event context and explicit participation.
2. **Add Information** — add Account, Observation, Review, Classification,
   Hypothesis, or Determination information without collapsing their epistemic
   distinctions.
3. **Record Response / Communication** — record a bounded Response or
   Communication without inferring effectiveness, delivery, reading,
   understanding, or agreement.
4. **Manage Support** — manage Support Process participants, Needs, Goals,
   Support, Intervention, Implementation, and Fidelity while keeping planning,
   delivery, fidelity, and Outcome separate.
5. **Complete Follow-Up** — review current scheduled/due/overdue Follow-Ups and
   complete one exact Follow-Up without automatically creating Outcome,
   Reentry, or Repair.
6. **View Timeline** — use Issue #48's privacy-minimized
   `StudentTimelineService`; current view is the default and history is
   deliberate.
7. **Correct / Retract** — route to family-specific correction, Amendment,
   retraction, or lifecycle authority. There is no generic edit/delete path.
8. **Attention Needed** — use Issue #49's native `AttentionQueryService` with
   an explicit offset-aware `as_of`.

**Advanced Portia tools** remains the bounded expert escape hatch for exact
record-family inventory and diagnostic inspection.

## Navigation

The main menu exposes `H` and `Q`. Submenus use the shared Portia navigation
adapter over Core-owned `B`, `M`, and `Q`, plus Portia-local `H`.

`Ctrl+C` and EOF unwind cleanly. Back/Main/Quit before an explicit write
confirmation do not create canonical Portia state.

## Session-local context

`MenuSessionContext` is process-local navigation convenience only. It may
remember the resolved workspace, exact class, exact Event/Support Process, and
local operator provenance. It is not a canonical task record, dossier, alert,
or institutional identity store.

Core remains authoritative for workspace resolution, classes, rosters, and
Core navigation semantics. A workspace change clears stale selected
class/work context.

## Opaque IDs and explicit time

Teachers are not asked to invent internal Portia IDs. `PortiaIdGenerator`
creates family-prefixed opaque IDs from cryptographically random nonsemantic
tokens; tests may inject deterministic tokens.

`MenuClock` is the application wall-clock seam. It always yields an
offset-aware `ExplicitOffsetTimestamp`. Issue #49 Attention receives that exact
explicit `as_of`; domain workflow candidates receive explicit timestamps from
the same application seam.

## Teacher-first presentation

Routine screens present recognizable teacher context first and exact technical
identity only where needed. Selectors retain exact canonical references behind
their numbered choices; display names and labels are presentation only.

Long selections page through shared UI helpers. Routine screens do not dump raw
record JSON, absolute filesystem paths, raw Integrity evidence, private Contact
Point values, or removed payload.

## Technical Details / Provenance

Advanced views may expose bounded technical identity needed for expert
inspection, including exact class/work/record IDs, contract versions,
fingerprints, operation IDs, lifecycle state, or recovery disposition.

Technical Details / Provenance does not authorize disclosure of secrets,
unrelated student information, raw Contact Point values, raw sibling-module
bodies, removed payload, or private narrative outside the selected view.

## Deliberate writes and stale-state handling

Every consequential teacher write has an action-specific preview and explicit
confirmation. One confirmation authorizes only that write.

Workflow services retain expected-fingerprint/revision guards. A stale
canonical state fails rather than force-overwriting or silently reapplying an
old teacher intent. Partial durable commits are reported as recovery/inspection
situations rather than blindly retried.

## family-specific correction

Correction is not a generic editor. Nonmaterial Amendment is restricted to the
registered Amendment policy. Material correction uses the exact family's
successor authority and preserves predecessor history. Account retraction
requires same-source retraction evidence. Ownership Correction and Exceptional
Removal remain advanced expert authorities.

Exceptional Removal is not ordinary deletion and is never represented as a
routine delete shortcut.

## Timeline and Attention boundaries

Timeline delegates to Issue #48. The menu does not bypass its privacy
projection with raw canonical reads.

Attention delegates to Issue #49. Stable native codes are mapped only for
teacher presentation and deterministic routing. Unknown future codes fail
closed. Partial and unavailable evaluations remain explicit. Viewing Attention
does not acknowledge/suppress Integrity findings, release Quarantine, resume
recovery, repair pointers, or rebuild derived state.

No behavior/risk/urgency/priority scoring is introduced. Portia does not rank
students or recommend discipline/support actions from Attention.

## Advanced Portia tools

Advanced mode provides exact record-family inventory, exact Actor lookup,
lifecycle/Amendment/disagreement/Dependency history, correction authority
registry visibility, and read-only Integrity/Quarantine/Recovery inspection.

Advanced mode does not provide raw filesystem mutation, arbitrary JSON editing,
generic pointer rewriting, generic lock clearing, generic Quarantine release,
generic canonical deletion, or private Core/sibling internals. Production
workflow/storage authorities remain the only mutation authority.

## Direct CLI boundary

The supported direct CLI remains:

```text
portia
portia menu
portia status
portia --help
portia --version
```

Default `portia` and `portia menu` launch the same production teacher menu.
`portia status` remains bounded package/Core status and does not bulk-read
teacher data.

Issue #50 does not add eight parallel noninteractive command families.

## zero-write navigation

Opening the application, opening Help, traversing a task surface, viewing
Timeline, viewing Attention, opening Technical Details / Provenance, backing
out, or returning to the main menu is navigation/read behavior only.

A write occurs only through an existing production service after the specific
write confirmation for that action.

## Privacy and authority language

Portia remains teacher-local support/response tooling. The menu does not claim
to determine truth, misconduct, culpability, dangerousness, risk, punishment,
support effectiveness, remorse, rehabilitation, or institutional status.

The interface is not an IEP/504/FBA/BIP system, clinical system,
threat-assessment system, schoolwide discipline system, or legal/compliance
authority.

## Issue boundaries

**Issue #49** owns native Portia attention semantics. Issue #50 only presents
and routes those results.

**Issue #51** owns deliberate local export/report generation. Issue #50 does
not implement general Event, Timeline, Support, CSV, PDF, or disclosure
exports.

**Issue #52** owns Suite readiness and Core module-operations provider
integration. Issue #50 does not register that provider.

**Issue #53** owns the complete representative installed Event-to-Follow-Up
milestone acceptance story. Issue #50's installed-wheel smoke is intentionally
smaller: real menu routing, zero-write traversal, representative Event creation,
and installed delegation checks.

See
`docs/validation/issue-50-task-oriented-teacher-menu-validation.md`
for qualification evidence.
