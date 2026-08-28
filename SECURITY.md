# Security Policy

## Project Status and Scope

pds-portia is a pre-1.0, local-first Python module for teacher-managed behavior-support, response, and follow-up records. The current supported development line is 0.2.x and is classified Pre-Alpha. It is not a hosted service, identity provider, compliance certification, student-information system, or substitute for an institution's approved safeguarding, records-management, incident-response, or legal processes.

This policy covers the pds-portia source repository, its distributed artifacts, and Portia-managed local workspaces. Security guarantees depend on the host, filesystem permissions, operator practices, and the exact compatible pds-core artifact in use.

## Student Data / Privacy

Real student or staff data is prohibited in this repository and in every development, test, demonstration, fixture, issue, pull request, log, screenshot, export, sample workspace, generated artifact, and vulnerability report. Use synthetic data only. Pseudonymized, redacted, hashed, truncated, or otherwise transformed real data is still real data and is not acceptable.

For Portia, prohibited real data includes names and identifiers; rosters; behavior observations; incident narratives; allegations; interventions; support plans; responses; follow-up notes; participant roles; disability, health, disciplinary, family, demographic, or attendance information; attachments; free text; timestamps that can identify a person; and links or relationship graphs that could re-identify a person.

If real data is discovered, stop processing it, avoid copying it further, preserve only the minimum evidence needed for safe response, and follow the institution's approved privacy and incident-response process. Do not post it to a public issue.

## Local-First Workspace Security

Local-first means Portia does not itself provide hosted storage. It does not mean a workspace is encrypted, private, access-controlled, backed up, or safe from other local users, malware, device loss, search indexing, telemetry, or synchronized folders. Operators must use an approved device, restrict filesystem access, enable appropriate full-disk encryption, patch the host, and follow institutional retention and deletion rules.

Do not place a real-data workspace inside a source checkout. A repository `.gitignore` reduces accidental Git tracking; it is not a privacy boundary and does not protect files from backup agents, cloud synchronization, editors, shells, or other processes. Keep code repositories, synthetic test workspaces, and any separately authorized operational workspace physically and administratively separated.

## Portia Semantic and Security Boundaries

Portia's contract and application boundaries are security-relevant:

- Events, Event Participants, Participant Roles, Accounts, Observations, Support Processes, and Work Relationships remain distinct exact records; Portia must not infer, merge, or silently retarget their identities.
- A Participant is Event-local and is not a global person identity. Descriptive or unknown-person branches must not be upgraded into identity claims.
- Role labels are neutral structured assertions, not findings of guilt, diagnosis, threat assessment, discipline, or legal status.
- `reported_involved` means an attributable report exists; it does not mean the report is true or adjudicated.
- Work Relationships express exact contextual links only. They do not copy ownership, authorization, participants, facts, or lifecycle state between works, and ordinary resolution does not follow successors.
- Exact historical resolution and current-use eligibility are separate. A record that remains recoverable is not necessarily eligible for current operational use.
- Quarantine and lifecycle checks are mandatory use gates, not optional display hints.

Consumers must preserve these distinctions in user interfaces, exports, automation, search, summaries, and downstream decisions. Portia output must not be used as an automated disciplinary, diagnostic, eligibility, safety, or legal determination.

## Identity and Cross-Module Boundaries

## Identity and Cross-Module Boundaries

`pds-core` provides shared Paper Data Suite infrastructure and authority for workspace routing, Core class and roster identity, and accepted cross-module primitives. Portia owns its domain records, Portia-specific application validation, guarded persistence, lifecycle behavior, and domain semantics. Neither layer may silently assume authority assigned to the other.

Roster references are scoped to the exact Core class authority and must not be treated as global identifiers. Authoritative roster identity is the exact `class_id + student_id` pair. Actor Directory identity is separate from Core roster identity, and names or display snapshots are never identity.

Sibling-module records remain owned by their producing module. Possession of an exact reference, successful parsing, or filesystem readability does not authorize disclosure or mutation. Portia must use accepted public Core and sibling-module boundaries and must not directly mutate sibling-module canonical records.

## Canonical Persistence and Recovery

Canonical writes must use Portia's guarded repository and coordinated persistence paths, including exact expected-state checks, canonical bytes, locks, operation journals, and quarantine gates where applicable. Bypassing those paths can create unvalidated, partially committed, or falsely current state.

Issue #38 recovery artifacts and operation journals may contain sensitive structure even when canonical writes did not complete. Treat staging areas, locks, journals, quarantine findings, recovery output, and forensic copies as protected workspace data. Resolve partial commits through the documented recovery flow; do not hand-edit canonical files to make an error disappear.

Path containment checks are security controls. Do not weaken them or follow untrusted symlinks/reparse points outside the selected workspace. Hard deletion is not guaranteed: filesystem snapshots, backups, synchronized copies, prior revisions, exports, and recovery artifacts may survive. Quarantine blocks defined operations; it is not encryption, erasure, or a substitute for incident response.

## Privacy, Exports, and Derived Views

Exports, reports, logs, caches, indexes, screenshots, printouts, and derived views can be more revealing than a single canonical record. Minimize fields, audience, lifetime, and copies. Preserve uncertainty, attribution, exact context, lifecycle status, and quarantine restrictions. Do not present hashes or fingerprints as anonymization. A SHA-256 content fingerprint provides integrity evidence; it does not encrypt or conceal the underlying data.

## Backups and Synchronized Storage

Back up only under an approved policy that covers access, encryption, retention, restoration testing, and deletion. Consumer cloud-sync folders may replicate Portia data across accounts, jurisdictions, devices, and retention systems. Do not use them unless explicitly approved for the data involved. Deleting the primary workspace may not delete replicas.

## Dependencies and Release Artifacts

Install Portia and pds-core from trusted, expected artifacts. Verify the exact Core wheel supplied to repository validation and review package origin, filename, version, and cryptographic digest through an independently trusted channel when artifacts cross a trust boundary. Lock or constrain dependencies as the deployment requires, scan them under local policy, and do not install packages merely because a similarly named project exists. A successful package or checksum check establishes limited integrity and compatibility evidence, not publisher identity or absence of vulnerabilities.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability or include real data in any report. Use the repository host's private vulnerability-reporting channel when enabled. If private vulnerability reporting is unavailable, open only a non-sensitive public issue stating that a private security-reporting channel is needed. Do not include vulnerability details, real data, credentials, or production workspace information.

Include the affected Portia and Core versions, operating system, a minimal synthetic reproduction, observed impact, and any relevant artifact digests. Do not attach a real workspace. Maintainers will acknowledge, triage, coordinate remediation, and publish appropriate release guidance as project capacity permits; pre-1.0 status means no fixed service-level response time is promised.

## Good-Faith Security Research

Good-faith research should use synthetic data, stay within systems and workspaces the researcher owns or is authorized to test, minimize access and retention, avoid persistence or service disruption, and report privately. Do not test against third-party schools, staff, students, devices, accounts, repositories, or data. These guidelines do not grant authorization, waive law or policy, or promise a bug bounty.

## Supported Versions

Only the current pre-1.0 development line receives security corrections. There is no long-term-support branch.

| Version | Supported |
| --- | --- |
| 0.2.x | Yes |
| < 0.2 | No |

Users should upgrade to the newest compatible 0.2.x release and use the pds-core range declared by that release. Security-relevant behavior can change before 1.0 and is documented in release notes and accepted ADRs.

## Compliance Disclaimer

This project does not itself establish compliance with FERPA, COPPA, GDPR, HIPAA, state student-privacy laws, records-retention rules, accessibility requirements, collective agreements, or institutional policy. Compliance depends on deployment, configuration, authorization, contracts, training, governance, and use. Obtain qualified institutional, legal, privacy, and security review before any operational use.
