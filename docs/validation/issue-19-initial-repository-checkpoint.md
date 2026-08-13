# Issue #19 Initial Repository Checkpoint

**Status:** Initial repository audit complete
**Issue:** `#19 — Define Follow-Up, Outcome, Reentry, and Repair domain models`
**Date:** 2026-08-12

## Exact Repository Anchors

```text
pds-portia/main
0d08495557721681b11d081e91c8b416a556df8a

pds-portia/19-follow-up-outcome-reentry-repair-domain-models
0d08495557721681b11d081e91c8b416a556df8a

pds-core/main
6c507213618b68a6dd3ea096e1a898201ff029e6

pds-meridian/main
9e5f9217ff2a935a98a12f7fc76ae2e74774159c
```

Meridian is recorded only as downstream consumer context. Portia does not take a
Meridian dependency.

## Branch Comparison

At Issue #19 start:

```text
base: main
head: 19-follow-up-outcome-reentry-repair-domain-models
status: identical
ahead: 0
behind: 0
merge base:
0d08495557721681b11d081e91c8b416a556df8a
```

The feature branch therefore begins exactly from the reconciled Issue #18 merge.

## Authoritative Local Test Baseline

Command:

```powershell
python -m unittest discover -s tests/schema_validation
```

Observed on the exact Issue #19 checkout:

```text
762 tests
93.403 seconds
OK
```

This value is filled by the Slice 1 helper after a successful local run. It is
not inferred from the pre-merge Issue #18 count.

## Live Issue Check

The live Issue #19 description is the expanded implementation ticket defining:

```text
Follow-Up
Outcome
Reentry
Repair
```

with explicit separation of:

```text
scheduled vs completed Follow-Up
source evidence vs Outcome
Implementation vs Outcome
Fidelity vs Outcome
workflow completion vs effectiveness
recurrence vs causal failure
Reentry vs clearance
Repair completion vs remorse/forgiveness
record linkage vs causation
```

## ADR Number Check

At initial audit:

```text
docs/decisions/0015-define-follow-up-outcome-reentry-and-repair-domain-models.md
```

does not exist.

ADR 0015 is therefore available at the initial checkpoint. Recheck immediately
before ADR publication.

## Post-#18 Contract Baseline

Merged Issue #18 provides:

```text
support_process@1
support_process_participant@1
support_need@1
support_goal@1
support@1
intervention@1
planned_schedule@1
implementation@1
fidelity@1
```

with IDs:

```text
sup_
spp_
spn_
spg_
spt_
int_
imp_
fid_
```

Accepted boundaries include:

```text
planned Support / Intervention
≠ actual Implementation

Implementation
≠ Fidelity

Fidelity
≠ Outcome

workflow / plan / execution completion
≠ effectiveness / resolution
```

Support Process-owned `communication@1` is current-use eligible without a wire
version change.

## Target Contract Audit

`portia_target_ref@1` is the existing closed Event-local target family:

```text
event
event_participant
event_participants
```

`support_process_target_ref@1` is the existing closed Support Process-local
target family:

```text
support_process
support_process_participant
support_process_participants
```

The initial #19 design therefore does not authorize a new generic target family.

## Exact Reference Audit

`exact_portia_work_record_ref@1` already combines:

```text
exact_portia_work_ref@1
+
exact_local_record_ref@1
```

and preserves exact contract version/history.

It must not silently follow:

```text
correction
supersession
plan adaptation
migration
duplicate consolidation
ownership correction
cross-year continuation
```

The initial #19 design therefore does not authorize another generic exact child
reference family.

## Dual Work-Owner Precedent

`communication@1` already uses a Portia-work-local envelope supporting:

```text
work_kind = event | support_process
work_id
class_id
```

with application-level owner resolution.

This is the leading precedent for Follow-Up, Outcome, Reentry, and Repair.

## Account Audit

`account@1` is currently Event-local:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

It preserves attributed substantive perspective and does not establish
credibility, truth, finding, or policy conclusion.

It cannot currently be stored directly under Support Process.

## Observation Audit

`observation@1` is currently Event-local:

```text
work_id -> portia_event_id@1
target  -> portia_target_ref@1
```

It already supports bounded direct/instrumented measurement with explicit
measurement semantics.

It cannot currently be stored directly under Support Process.

This creates the primary pre-ADR #19 architecture question:

> How should Support Process-owned Follow-Up/Outcome reference substantive
> perspective and direct measurement without duplicating Account/Observation
> payloads or silently broadening their published Event-local ownership?

The initial design keeps Account/Observation unchanged until examples
demonstrate whether a new version is genuinely required.

## Review Audit

`review@1` remains Event-local and belongs to the interpretation/judgment layer.

The leading #19 design represents Support Process review through:

```text
Follow-Up + Outcome
```

rather than broadening `review@1`.

## Communication Audit

`communication@1` is a bounded contact act/attempt.

Support Process ownership is now resolvable/current-use eligible.

Communication remains distinct from:

```text
substantive Account
Implementation
participation proof
consent
Outcome
Repair completion
```

## Core v0.6 Boundary

Core v0.6 provides:

```text
intervention_record_set
```

with capabilities including:

```text
intervention_history
intervention_status
intervention_outcomes
```

Producing modules own native intervention/outcome semantics.

Issue #19 may stabilize Portia-native Outcome identity for later projection, but
does not implement producer profiles, manifests, Publication Records, Meridian
adapters, Academic Work Registration, academic results, Scores, standards
ratings, or Grades.

## Meridian Boundary

Current Meridian preserves producer-native meaning through explicit,
authorization-gated consumer adapters.

Meridian currently has no Portia adapter and is not a Portia dependency.

Issue #19 does not add one.

## Candidate Identifier Collision Check

Repository code search returned no existing uses of:

```text
fup_
out_
ren_
rpr_
```

Leading candidates are therefore:

```text
portia_follow_up_id@1  fup_
portia_outcome_id@1    out_
portia_reentry_id@1    ren_
portia_repair_id@1     rpr_
```

Recheck at ADR/schema publication time.

## Shared Infrastructure Reuse

Issue #19 is expected to reuse:

```text
represented_human_attribution@1
attribution_agent@1

lifecycle_transition@1
lifecycle_history_correction@1
statement_of_disagreement@1
dependency@1
record_migration@1
ownership_correction@1
exceptional_removal@1

operation_journal@2
operation_lock@2
quarantine_record@2
integrity_finding@2
source_snapshot@1
derived_index_metadata@1
derived_current_pointer@1
```

No family-specific fork is authorized by this checkpoint.

## Paper / Privacy / Automation Boundary

Issue #20 remains authoritative for paper/PDS2/import activation and human review.

Issue #21 remains authoritative for complete redaction/export/retention/Sunset
policy.

Issue #19 native contracts must nevertheless minimize sensitive content and
must not automate:

```text
progress judgments
recurrence conclusions
effectiveness
causation
Goal status
support closure/adaptation
Reentry completion
Repair participation/completion
compliance
engagement
remorse
forgiveness
provider competence
```

## Synthetic Data Boundary

All Issue #19 fixtures/examples must use synthetic people, classes, Events,
supports, communications, measurements, reentry situations, and repair
processes.

No real student/family/staff/support data may be committed.

## Initial Checkpoint Conclusion

No upstream drift or published-contract conflict blocks Issue #19 design work.

The initial architecture can proceed toward ADR 0015 with:

```text
four separate work-local canonical child families
Event or Support Process ownership
existing target families
existing exact reference infrastructure
existing lifecycle/correction/operation/derived infrastructure
```

The main unresolved pre-ADR question is the Event-local Account/Observation
boundary for Support Process-owned downstream evidence.

No public #19 schema is authorized until ADR 0015 resolves the outstanding
semantic decisions.
