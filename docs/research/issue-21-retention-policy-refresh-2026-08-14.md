# Issue #21 Retention Policy Refresh — 2026-08-14

**Scope:** Current official policy check supporting Slice 5
**Status:** Product-architecture input; not legal advice

## FERPA

Current U.S. Department of Education FERPA material confirms:

- access/inspection requests must be handled within the applicable legal period;
- education records must not be destroyed while an applicable inspection/review
  request is outstanding;
- FERPA itself does not impose one universal requirement that every school
  education record be retained indefinitely;
- an applicable Statement of Disagreement must remain associated with the
  contested portion for as long as that record is maintained and accompany
  disclosure of the related portion when the rule applies.

Official sources reviewed:

```text
https://studentprivacy.ed.gov/ferpa
https://studentprivacy.ed.gov/faq/does-educational-agency-or-institution-have-discretion-over-what-education-records-it-decides
https://studentprivacy.ed.gov/faq/what-rights-does-parent-or-eligible-student-have-if-result-hearing-school-decides-information
```

### Architecture consequence

Portia needs scoped preservation/request blockers and correction/disagreement
dependency support.

It does not need a universal FERPA retention duration.

## New Jersey

Current New Jersey Records Management Services material states that approved
retention schedules provide minimum legal/fiscal retention periods for public
records and continues to list:

```text
School District Retention Schedule: Active Records - Student Records
M700106-001
```

The published schedule page directs agencies to Artemis for more current
information.

Current disposition guidance states that public agencies require prior written
authorization for public-record destruction and that Artemis is the State system
used for records-disposition requests/authorization.

Official sources reviewed:

```text
https://www.nj.gov/treasury/revenue/rms/retention.shtml
https://www.nj.gov/treasury/revenue/rms/artemis.shtml
https://www.nj.gov/treasury/revenue/rms/retentiondisposition.shtml
```

### Architecture consequence

For New Jersey deployments:

```text
schedule eligibility != destruction authorization
```

Portia must not treat a computed date as authority to destroy.

The product should consume district/records-management decisions rather than
hard-code Artemis workflow or a specific schedule duration.

## Existing Portia Exceptional Removal

`exceptional_removal@1` is already narrowly defined as a certificate that one
exact accepted Portia representation had its canonical payload intentionally
removed under exceptional authorization.

Its application invariants require, among other things:

```text
narrow exceptional grounds
valid authorization
no unresolved governance block
dependency review
derived-payload purge
recoverable execution
```

### Architecture consequence

Routine schedule-based disposition must remain distinct.

Do not overload Exceptional Removal into a general retention-expiry mechanism.
