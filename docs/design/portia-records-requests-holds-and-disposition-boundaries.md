# Portia Records Requests, Holds, and Disposition Boundaries

**Status:** Issue #21 Slice 5 architecture
**Date:** 2026-08-14
**Wire-contract status:** No Portia legal-case/request/hold schema is introduced.

## 1. Decision

Portia must react safely to records/privacy requests and preservation decisions
without becoming the institution's authoritative records-request system.

Issue #21 therefore defines:

```text
request intent vocabulary
request-processing boundary
preservation/hold inputs
destruction blockers
institution handoff rules
```

but deliberately does **not** add canonical:

```text
portia_privacy_request
portia_legal_hold
portia_records_case
portia_retention_policy
```

records.

## 2. Why no Portia request case record

A durable institutional records-request case may need facts Portia cannot
authoritatively establish:

```text
requester legal identity
parent/guardian status
eligible-student status
date legally received by institution
scope of legal request
service/notice obligations
hearing rights
legal deadline extensions
legal counsel decisions
records-officer disposition
appeal/complaint state
```

Persisting those as Portia canonical facts would exceed teacher-local authority.

A future institutional integration may provide exact request/case references.

## 3. Request intent vocabulary

Portia must at least distinguish:

```text
inspect_access
export_copy
amend_correct
statement_of_disagreement
restrict_withhold
delete_destroy
other
```

These are expressed user/request intents, not automatically granted rights.

## 4. Local request handling

When a teacher records or receives a request relevant to Portia, the product may
collect only enough local operational state to:

1. identify the bounded Portia scope potentially affected;
2. avoid destructive action while policy review is unresolved;
3. direct the user to the institution's authoritative process;
4. preserve an external case/decision reference when supplied;
5. execute only later module-local action covered by an authoritative decision.

The foundation does not require Portia to persist the requester's sensitive legal
identity or complaint narrative.

## 5. Request-processing states

The integration boundary should be able to represent:

```text
received
needs_policy_review
approved
partially_approved
denied
unresolved
completed
```

These states describe the external/integration workflow.

They do not rewrite the target record.

## 6. Access/inspection request preservation

When an authoritative institution input establishes that an access/inspection
request is outstanding for exact education-record scope:

```text
destructive disposition of covered records = blocked
```

Portia need not determine whether FERPA applies; it consumes the institution's
authoritative scope/decision.

The block remains until an explicit authoritative release/resolution is supplied.

## 7. Amendment/correction requests

A request to correct Portia content does not authorize in-place historical
rewrite.

When approved, use the existing Portia correction architecture:

```text
nonmaterial Amendment
material successor/supersession
Lifecycle Transition
Ownership Correction
Record Migration
Statement of Disagreement
```

as semantically appropriate.

A denied amendment request can lead to an applicable Statement of Disagreement
workflow when institution policy requires/allows it.

The request case itself does not become the disagreement.

## 8. Statement of Disagreement retention dependency

An applicable Statement of Disagreement can be substantively tied to the
contested record.

Portia must support a policy constraint equivalent to:

```text
while contested record is maintained
-> applicable required disagreement must remain associated
```

and, when governing policy requires it:

```text
disclose contested portion
-> evaluate/include applicable disagreement relationship
```

Routine disposition planning must therefore treat the contested record and
required disagreement as a dependency unit.

## 9. Delete/destroy requests

A delete/destroy request produces:

```text
needs_policy_review
```

unless an authoritative decision already covers the exact requested action.

It never directly invokes:

```text
unlink
rmtree
exceptional_removal
routine disposition
foreign-module deletion
```

## 10. Exceptional privacy/legal erasure

`exceptional_removal@1` is available only when its existing narrow semantics are
actually met.

Examples may include an authoritative decision involving:

```text
unlawful collection
prohibited retention
privacy requirement
legal requirement
security containment
```

as allowed by the accepted contract.

It must not be used merely because:

```text
retention period expired
student left class
school year ended
teacher wants cleanup
export is old
record is superseded
```

## 11. Routine retention disposition

Routine schedule-based disposition is conceptually:

```text
classification
-> exact trigger
-> external policy evaluation
-> preservation/hold review
-> dependency/correction review
-> external destruction authorization
-> module-owned action
-> module-local verification
```

It is not Exceptional Removal.

No routine canonical-destruction wire contract is published in Slice 5 because
the cross-module orchestration boundary is not accepted until Slice 6.

## 12. Preservation/hold inputs

A disposition planner must be capable of receiving exact scoped constraints for:

```text
outstanding_access_request
outstanding_amendment_process
statement_of_disagreement_dependency
legal_or_litigation_hold
subpoena_or_court_process
special_education_process
civil_rights_process
records_audit
integrity_or_recovery_uncertainty
pending_export_or_disclosure_obligation
local_policy_hold
other
```

Portia does not decide whether a legal category actually applies.

It consumes a scoped authoritative decision/reference or remains `unresolved`.

## 13. Hold scope

A preservation decision must identify its exact covered scope.

Possible scopes include:

```text
one exact work
one exact work record
one exact Actor/Contact Point
one exact export
one bounded class scope
one externally identified source set
```

Do not automatically expand:

```text
hold on one Event
-> hold every Portia record ever associated with the student
```

Such expansion would itself create dossier-like semantics.

## 14. Hold release

A hold remains effective until an explicit authoritative release or replacement
is supplied.

Do not infer release from:

```text
age
case inactivity
record supersession
school-year end
student departure
teacher belief
```

## 15. Integrity/recovery blocks

Portia-owned safety conditions independently block disposition.

Examples:

```text
in-progress Operation Journal
unresolved Quarantine
active Integrity Finding relevant to custody
unverified source/target identity
incomplete dependency graph
partial prior disposition
unknown artifact state
```

An external destruction authorization cannot force Portia to claim safe
completion when the module cannot establish its own integrity preconditions.

The correct result is:

```text
blocked
or
unresolved
```

until repair/reconciliation.

## 16. Correction graph preservation

Disposition planning must traverse applicable:

```text
supersession
invalidation
amendment
Statement of Disagreement
ownership correction
migration
dependency
Exceptional Removal certificate
```

relationships.

It must reject partial deletion that would leave a surviving record falsely
presented as complete/current unless the exact policy authorizes that result and
the surviving representation truthfully records the absence.

## 17. "Preserve history" is not "retain forever"

Portia's append-preserving correction architecture means ordinary correction does
not erase history.

It does **not** mean every representation must remain forever regardless of
institution policy.

A later authorized routine disposition may remove an entire coherent historical
unit when:

- governing retention policy permits it;
- required retention period is satisfied;
- no hold/request block applies;
- dependency graph is coherent;
- external disposition authorization exists;
- each owning module executes only its own custody.

## 18. Derived data must not extend substantive retention accidentally

A derived cache must not become a hidden long-lived copy of source content after
the authoritative source is lawfully disposed.

After source disposition, rebuild/cleanup must ensure:

```text
old projection cache removed
old dashboard cache removed
old search index removed
old source snapshot removed when appropriate
staging/recovery copy removed when no longer required
```

unless a separate policy explicitly requires preservation.

Derived deletion must be ordered so it cannot destroy required recovery evidence
before the canonical disposition is verified.

## 19. Export request and export-byte disposition

An `export_copy` request creates a deliberate-export workflow only after
authorization.

Later destruction of local export bytes is a separate retention/disposition
action.

Preserve:

```text
export generation != disclosure
export-byte deletion != disclosure-history deletion
export-byte deletion != external recall
```

`deliberate_export@1` may survive after local bytes are removed if policy
requires provenance.

A future disposition record must then represent artifact unavailability honestly.

## 20. Foreign-module deletion requests

If a request covers data referenced by Portia but owned by Core/Vitrine/
Meridian/Quillan/ScoreForm/Concord or another producer:

```text
Portia must not delete foreign custody
```

The request must be decomposed into module-owned actions by a future suite
orchestrator or institutional process.

Portia may report:

```text
foreign custody unresolved
```

until that owner supplies a verifiable result.

## 21. Local workspace destruction

Destruction of an entire Portia workspace/class is stronger than deleting one
record.

It requires explicit institution policy and must account for:

```text
canonical domain records
correction/disagreement history
Actor Directory custody
paper/import provenance
operation/recovery evidence
derived state
export bytes/provenance
Exceptional Removal certificates
foreign references
```

Issue #21 does not add a one-command workspace wipe.

## 22. Non-goals

This boundary does not implement:

```text
FERPA case management
OPRA case management
subpoena workflow
legal-hold adjudication
records-officer approval
Artemis submission
district retention schedule selection
backup purge
remote recall
secure media destruction
```
