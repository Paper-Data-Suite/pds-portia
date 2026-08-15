# Issue #21 Privacy and Records Policy Research Checkpoint

**Date reviewed:** 2026-08-14
**Scope:** Architecture inputs for Portia Issue #21
**Status:** Product-policy research checkpoint; not legal advice

This note records current official policy inputs used to constrain Issue #21.
It does not convert those sources into automatic Portia legal decisions.

## 1. FERPA: multi-student records

U.S. Department of Education FERPA guidance for 34 C.F.R. § 99.12 states that
when an education record contains information on more than one student, a
parent or eligible student may inspect/review or be informed of only the
specific information about the student in question.

Official source:

```text
https://studentprivacy.ed.gov/faq/may-parents-or-eligible-students-be-provided-access-education-records-contain-information-more
```

The Department's multi-student video guidance adds a product-design constraint:
when information about other students can reasonably be redacted or segregated
without destroying the record's meaning, that approach may be appropriate or
required. When meaningful segregation cannot reasonably be accomplished, the
legal access analysis differs.

Official source:

```text
https://studentprivacy.ed.gov/faq/if-video-education-record-multiple-students-can-parent-one-students-or-eligible-student-view
```

### Architecture consequence

Portia should not encode either:

```text
redaction impossible -> automatically deny
redaction impossible -> automatically expose full record
```

Automatic projection should instead support:

```text
requires_manual_review
```

while preserving exact source and focal-student context.

## 2. FERPA: inspection requests and destruction

34 C.F.R. § 99.10(e) states that an educational agency/institution or applicable
SEA component must not destroy education records while an outstanding request
to inspect/review those records exists.

Official source:

```text
https://studentprivacy.ed.gov/ferpa
```

### Architecture consequence

A retention/disposition planner needs a preservation/hold input for an
outstanding inspection request. Portia must not infer the legal existence or
scope of that hold itself.

## 3. FERPA: amendment and Statement of Disagreement

34 C.F.R. §§ 99.20–99.22 provide the amendment/hearing process. When an
institution maintains a statement with contested information after that
process, the statement must remain associated with the contested part while the
record is maintained and accompany disclosure of the contested portion when the
rule applies.

Official source:

```text
https://studentprivacy.ed.gov/ferpa
```

### Architecture consequence

Portia's existing `statement_of_disagreement@1` is compatible with this need,
but Issue #21 must ensure projection/export and retention logic can preserve the
association when governing policy requires it.

## 4. FERPA: disclosure records

34 C.F.R. § 99.32 generally requires educational agencies/institutions to
maintain records of many requests for access to and disclosures of personally
identifiable information, including parties and legitimate interests, subject
to listed exceptions.

Official source:

```text
https://studentprivacy.ed.gov/ferpa
```

### Architecture consequence

Issue #21 must preserve:

```text
export generated != disclosure occurred
```

Portia may need a disclosure-record integration hook or bounded local record,
but an Export record must not automatically be claimed as complete
institutional § 99.32 compliance.

## 5. Authentication and de-identification

FERPA requires reasonable methods to identify/authenticate parties when
personally identifiable information is disclosed. Its de-identification rules
also require a reasonable determination that a student is not personally
identifiable directly or indirectly considering reasonably available
information.

Official source:

```text
https://studentprivacy.ed.gov/ferpa
```

### Architecture consequence

Portia must not equate:

```text
audience = family
```

with authenticated requester identity, or:

```text
remove name
```

with de-identification.

## 6. New Jersey retention/disposition structure

New Jersey Records Management Services publishes retention schedules with
minimum legal/fiscal retention periods for state/local governmental and
educational agencies. Current listings include:

```text
School District Retention Schedule: Active Records - Student Records
M700106-001
```

The State site directs agencies to Artemis for more current schedule
information and separates retention expiration from the agency
records-disposition process.

Official sources:

```text
https://www.nj.gov/treasury/revenue/rms/retention.shtml
https://www.nj.gov/treasury/revenue/rms/artemis.shtml
https://www.nj.gov/treasury/revenue/rms/retentiondisposition.shtml
```

### Architecture consequence

Portia must not hard-code one behavior-record retention period, one school-year
cleanup rule, or one automatic destruction date.

The safe architecture is:

```text
stable Portia retention class
+ exact observable trigger facts
+ versioned external/institution policy
+ preservation/hold decisions
+ explicit disposition authorization
```

## 7. NIST Privacy Framework

At this checkpoint:

- NIST Privacy Framework 1.0 remains the finalized framework;
- Privacy Framework 1.1 remains an Initial Public Draft / development effort;
- NIST privacy-risk guidance treats privacy across the data lifecycle through
  disposal/decommissioning;
- NIST continues work on a Data Governance and Management Profile.

Official sources:

```text
https://www.nist.gov/privacy-framework
https://www.nist.gov/privacy-framework/getting-started-0
https://www.nist.gov/privacy-framework/new-projects/privacy-framework-version-11
https://www.nist.gov/privacy-framework/using-privacy-framework-11
https://www.nist.gov/privacy-framework/new-projects/data-governance-and-management-profile
```

### Architecture consequence

NIST is privacy-risk/data-lifecycle guidance, not a jurisdiction-specific
retention schedule.

Issue #21 should make controls visible across collection, storage, use,
projection, export, disclosure, retention, disposition, and decommissioning.

## 8. Existing Portia research synthesis

Current Portia research already recommends privacy by design, least privilege,
field-level sensitivity, multi-student redaction, configurable retention, secure
destruction, auditability, student/family participation, and rejection of a
single behavior/risk profile.

Source:

```text
docs/research/student-behavior-tracking-best-practices.md
```

It also cautions that federal law is only part of the governing framework and
that state law, district policy, special-education procedures, civil-rights
obligations, records schedules, and local protocols may add requirements.

## 9. Slice 1 conclusion

The reviewed policy inputs support:

```text
Portia:
    privacy-safe semantic projection
    source/correction lineage
    retention classification
    safe module-owned technical actions

institution/deployment:
    identity and authorization
    disclosure entitlement
    legal/policy interpretation
    retention schedule selection
    hold/destruction approval

future Sunset:
    cross-module orchestration
```

No reviewed source supports making Portia an automatic legal-decision engine.

No reviewed source supports one universal Portia retention duration.

No reviewed source supports treating a participant/student/family audience label
as proof of requester authorization.
