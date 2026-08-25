# Synthetic-data policy

Portia stores and processes potentially sensitive teacher-local records. The
repository therefore uses **synthetic data only** for committed tests, fixtures,
examples, screenshots, smoke tests, demonstrations, and documentation samples.

## Prohibited committed data

Do not commit real or anonymized-from-real school records, including real:

- student, family, guardian, staff, or collaborator names;
- student IDs, local IDs, email addresses, phone numbers, or contact points;
- class rosters or schedules derived from an actual class;
- Event narratives or incident descriptions;
- Accounts, Observations, Reviews, Classifications, Hypotheses, or Determinations;
- Responses, communications, supports, interventions, implementations, or fidelity records;
- Follow-Ups, Outcomes, Reentry, or Repair records;
- attachments, imported source rows, scanned pages, OCR output, screenshots, or exports;
- workspace paths or metadata that disclose a real person's identity or school record.

Replacing a real name with a pseudonym is not sufficient if the underlying record
or narrative came from a real student or real school event.

## Required fixture characteristics

Committed fixtures must be deliberately fictional and should make that status
obvious. Prefer invented classes, opaque IDs, neutral scenarios, and minimal
content required to exercise the contract under test.

Synthetic fixtures must not be written in a way that implies a reported concern
is proven misconduct, that an intervention caused an outcome, or that Portia has
institutional authority it does not possess.

## Local manual testing

A developer may point a local, uncommitted build at their own authorized teacher
workspace only when the relevant Portia workflow explicitly supports that use.
Such data must remain outside the repository, test artifacts, CI logs, screenshots,
and issue/PR attachments unless separately reviewed and deliberately sanitized.

Issue #36 itself does not read or write teacher data. Its CLI, package tests, CI,
and wheel smoke tests are intentionally data-free apart from synthetic package
metadata and temporary filesystem paths.
