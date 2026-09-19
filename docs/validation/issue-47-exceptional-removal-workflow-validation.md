# Issue #47 Corrective Slice 33.1 — Exceptional Removal validation

This corrective slice adds the bounded production
`ExceptionalRemovalWorkflowService` without changing either public removal
schema, `operation_journal@3`, ADR 0018, or the Core dependency floor.

The service supports exact Portia `work` and `work_record` targets and all four
published Actor Directory branches: Actor, contact point, student relationship,
and reviewed roster-student collision. It does not expose filesystem paths or a
generic delete API.

Removal authority is application-local. It requires an enabled capability, a
known-clear governance state, a local-operator attribution, a bounded external
decision reference, and a recognized exceptional ground. Test-data and
unrecoverable-corruption grounds require their additional positive evidence.
This authority does not claim that Portia has adjudicated legal sufficiency or
institutional policy.

The production order is:

1. exact identity/path/version/bytes/fingerprint preflight;
2. bounded canonical incoming-reference and Dependency review;
3. complete root-child inventory and explicit dispositions;
4. `operation_journal@3` creation and deterministic locks;
5. active Quarantine creation and verification;
6. immutable certificate creation and readback;
7. capability-guarded `CanonicalRemovalStore` mutation;
8. verified absence journaling;
9. exact staged-copy purge and derived-generation invalidation where needed;
10. completed journal publication while protective Quarantine remains active.

Every removed work child receives its own certificate with the exact parent
removal reference. Actor-root removal requires every owned current child to be
independently exceptionally removed. No directory is recursively deleted.

Exact resolution distinguishes present, exceptionally removed, ordinary
absence, duplicate-certificate corruption, and certificate/payload
contradiction. A valid certificate is never deleted and removed content is
never reconstructed. `RecoveryWorkflowService.resume_exceptional_removal`
reuses `OperationRecovery` classification and resumes only the certificate-
backed specialized absence path. Replays are idempotent.

Emergency destruction before a durable certificate remains intentionally
unsupported. Quarantine release remains a separate Slice 32 evidence-backed
repair decision; successful physical absence alone does not release it.

Focused validation covers authorization failures, exact salted-byte evidence,
work-record execution, root/child certificates, interruption and recovery,
Actor privacy, all published Actor target branches, and installed-wheel use of
the real public workflow and storage primitive.

