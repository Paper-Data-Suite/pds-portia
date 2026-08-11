# Portia Response and Communication Examples

**Issue:** `#17 — Define Response and Communication domain models`

All named people, classes, identifiers, contact points, records, and situations in this document are synthetic.

These examples illustrate semantic boundaries and point to the synthetic fixture or focused test that carries the executable proof.

| # | Scenario | Record boundary | Expected meaning | Evidence |
|---:|---|---|---|---|
| 1 | Event-level classroom redirection | Response | Event-targeted `classroom_management`; no Determination required. | `tests/schema_validation/fixtures/issue-17/response/valid/event-classroom-management.json` |
| 2 | Participant-specific redirection | Response | Participant target scopes the action without global student history. | `tests/schema_validation/fixtures/issue-17/response/valid/participant-redirection.json` |
| 3 | Existing break option offered | Response | `support_access` during one Event remains Response, not longitudinal Support. | `tests/schema_validation/fixtures/issue-17/response/valid/support-access.json` |
| 4 | Immediate protective action | Response | `safety_or_protective` records bounded action without creating a crisis workflow. | `tests/schema_validation/fixtures/issue-17/response/valid/event-safety-protective.json` |
| 5 | Teacher-local consequence | Response | Records the action without proving misconduct, proportionality, or effectiveness. | `tests/schema_validation/fixtures/issue-17/response/valid/teacher-local-consequence.json` |
| 6 | Recorded institutional consequence | Response | Exact same-Event Determination context is retained rather than duplicated. | `tests/schema_validation/fixtures/issue-17/response/valid/recorded-institutional-consequence.json` |
| 7 | Counselor handoff attempted | Response | `referral_or_handoff` can be attempted without implying service delivery. | `tests/schema_validation/fixtures/issue-17/response/valid/referral-attempted.json` |
| 8 | Review-context action | Response | Exact Review may provide context without turning Response into a finding. | `tests/schema_validation/fixtures/issue-17/response/valid/review-context.json` |
| 9 | Imported historical Response | Response | Proposed record can preserve unknown execution honestly. | `tests/schema_validation/fixtures/issue-17/response/valid/import-unknown-proposed.json` |
| 10 | Material Response correction | Response | Successor preserves the earlier Response and exact predecessor identity. | `tests/schema_validation/fixtures/issue-17/response/valid/successor-correction.json` |
| 11 | Completed family phone call | Communication | One bounded human contact act with exact Actor Contact Point. | `tests/schema_validation/fixtures/issue-17/communication/valid/completed-family-phone.json` |
| 12 | Recipient unavailable | Communication | Attempt is preserved without implying participation. | `tests/schema_validation/fixtures/issue-17/communication/valid/recipient-unavailable-phone.json` |
| 13 | Student in-person conversation | Communication | Roster student may be a recipient; contact act remains distinct from Account evidence. | `tests/schema_validation/fixtures/issue-17/communication/valid/student-in-person.json` |
| 14 | Incoming family call | Communication | Human sender can be descriptively represented without fabricating an Actor. | `tests/schema_validation/fixtures/issue-17/communication/valid/incoming-family-phone.json` |
| 15 | Multi-recipient email | Communication | Recipients are explicit and ordering is nonsemantic. | `tests/schema_validation/fixtures/issue-17/communication/valid/multi-recipient-email.json` |
| 16 | Determination notice | Communication | Typed exact relation conveys a Determination without becoming one. | `tests/schema_validation/fixtures/issue-17/communication/valid/determination-notice.json` |
| 17 | Response coordination | Communication | Typed relation points to exact Response without copying action payload. | `tests/schema_validation/fixtures/issue-17/communication/valid/response-relation.json` |
| 18 | Account from communication | Communication + Account | Contact act is Communication; substantive source assertion remains separately preservable as Account. | `tests/schema_validation/fixtures/issue-17/communication/valid/account-relation.json` |
| 19 | Workspace-file attachment | Communication | Path + fingerprint references bytes without embedding them. | `tests/schema_validation/fixtures/issue-17/communication/valid/workspace-file-attachment.json` |
| 20 | Sibling-module attachment | Communication | ModuleWorkRecordRef preserves sibling PDS identity without broadening source-artifact semantics. | `tests/schema_validation/fixtures/issue-17/communication/valid/module-record-attachment.json` |
| 21 | External attachment | Communication | External locator is inert and proves neither delivery nor authenticity. | `tests/schema_validation/fixtures/issue-17/communication/valid/external-record-attachment.json` |
| 22 | Portia-record attachment | Communication | Exact Portia work-record reference associates material without making it evidence automatically. | `tests/schema_validation/fixtures/issue-17/communication/valid/portia-record-attachment.json` |
| 23 | Imported historical Communication | Communication | Unknown sender/method/purpose/state/privacy can remain honest in proposed import. | `tests/schema_validation/fixtures/issue-17/communication/valid/import-unknown-proposed.json` |
| 24 | Material Communication correction | Communication | Successor history preserves the original communication record. | `tests/schema_validation/fixtures/issue-17/communication/valid/successor-correction.json` |
| 25 | Failed then completed family contact | Communication | 3:10 unavailable and 4:25 completed remain two records, not one mutable thread state. | `tests/schema_validation/fixtures/issue-17/cross-record/failed-then-completed-contact.json` |
| 26 | Response linked to Communication | Response + Communication | Action and contact remain distinct despite one workflow. | `tests/schema_validation/fixtures/issue-17/cross-record/response-and-communication-distinct.json` |
| 27 | Determination → notice → implementation | Determination + Communication + Response | Exact Determination is shared as context while notice and action remain separate. | `tests/schema_validation/fixtures/issue-17/cross-record/determination-communication-response.json` |
| 28 | Communication → Account boundary | Communication + Account | A family source assertion is represented by Account, not silently by Communication summary. | `tests/schema_validation/fixtures/issue-17/cross-record/communication-account-boundary.json` |
| 29 | Draft/paper artifact is not communication | Boundary | Preallocated paper and draft generation cannot fabricate an attempted/completed Communication. | `tests/schema_validation/fixtures/issue-17/communication/invalid/paper-preallocated.json` |
| 30 | Contact endpoint ownership mismatch | Invalid Communication | Exact Contact Point must belong to the represented Actor recipient. | `tests/schema_validation/fixtures/issue-17/communication/application-invalid/endpoint-actor-mismatch.json` |
| 31 | Statement of Disagreement | Shared infrastructure | Disagreement may target exact Response/Communication without erasing or adjudicating it. | `tests/schema_validation/test_issue_17_shared_infrastructure_compatibility.py` |
| 32 | Operational/derived privacy minimization | Shared infrastructure | Operations, Quarantine, Integrity Finding, source snapshots, and derived metadata do not copy substantive action/summary text. | `tests/schema_validation/test_issue_17_shared_infrastructure_compatibility.py` |

## Boundary reminders

- Response records an action; it does not establish what occurred, fault, policy violation, justification, proportionality, or effectiveness.
- Communication records a bounded human communication act or attempt; recipient listing is not proof of participation, and `completed` is not proof of delivery/read/legal notice.
- When substantive source assertions matter as evidence, preserve them separately as Account rather than treating Communication metadata as evidence.
- Immediate Event action remains Response; planned/recurring/longitudinal support belongs to Issue #18.
- Replies and later attempts are separate Communication records; a thread may be derived.
- Exact references preserve historical identity and never silently follow successors.
